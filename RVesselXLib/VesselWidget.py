from collections import OrderedDict
import os

import ctk
import qt
import slicer

from RVesselXLib import setup_portal_vein_default_branch, setup_inferior_cava_vein_default_branch
from .ExtractVesselStrategies import ExtractOneVesselPerBranch, ExtractOneVesselPerParentAndSubChildNode, \
  ExtractOneVesselPerParentChildNode, ExtractAllVesselsInOneGoStrategy
from .RVesselXModuleLogic import VesselnessFilterParameters, LevelSetParameters
from .RVesselXUtils import GeometryExporter, removeNodesFromMRMLScene, createDisplayNodeIfNecessary, Signal, \
  getMarkupIdPositionDictionary
from .VerticalLayoutWidget import VerticalLayoutWidget
from .VesselBranchTree import VesselBranchWidget, VesselBranchTree


class VesselAdjacencyMatrixExporter(GeometryExporter):
  def __init__(self, **elementsToExport):
    GeometryExporter.__init__(self, **elementsToExport)

  def exportToDirectory(self, selectedDir):
    for treeName, (markup, tree) in self._elementsToExport.items():
      base_path = os.path.join(selectedDir, treeName)
      self._exportTreeAsAdjacencyCSV(tree, base_path + "AdjacencyMatrix.csv")
      self._exportTreeAndMarkupAsDgtalFormat(markup, tree, base_path)

  def _exportTreeAsAdjacencyCSV(self, tree, output_file):
    tree_nodes, adjacency_matrix = self.toAdjacencyMatrix(tree)
    with open(output_file, "w") as f:
      sep = ";"
      f.write(sep.join([""] + tree_nodes) + "\n")

      for i_node, node_name in enumerate(tree_nodes):
        f.write(sep.join([node_name] + map(str, adjacency_matrix[i_node])) + "\n")

  def _exportTreeAndMarkupAsDgtalFormat(self, markup, tree, basePath):
    edges, vertices = self.toDgtal(markup, tree)
    self._toSpaceSepFile(edges, basePath + "_edges.bat")
    self._toSpaceSepFile(vertices, basePath + "_vertex.sdp")

  @classmethod
  def _toSpaceSepFile(cls, matrix, filePath):
    with open(filePath, "w") as f:
      for r in matrix:
        r_str = " ".join([str(c) for c in r])
        f.write(r_str + "\n")

  @classmethod
  def toAdjacencyMatrix(cls, tree):
    """
    :type tree: VesselBranchTree
    :return: Tuple[List[str], List[List[int]]]
    """
    node_list = sorted(tree.getNodeList())
    matrix = []
    for node_name_1 in node_list:
      row = []
      for node_name_2 in node_list:
        if tree.getParentNodeId(node_name_2) == node_name_1 or node_name_1 in tree.getChildrenNodeId(node_name_2):
          row.append(1)
        else:
          row.append(0)
      matrix.append(row)

    return node_list, matrix

  @classmethod
  def toDgtal(cls, markup, tree):
    """
    Convert the input markup node and associated tree to dgtal output format.
    https://github.com/DGtal-team/DGtalTools-contrib/tree/master/Samples

    Parameters
    ----------
      markup: Slicer MarkupFiducialNode
      tree: VesselBranchTree

    Returns
    -------
      Edges, Vertices
      Tuple[List[List[int]], List[List[int]]]
    """

    node_list, matrix = cls.toAdjacencyMatrix(tree)

    vertices = []
    edges = []
    for i_n, node_name in enumerate(node_list):
      node_position = [0] * 3
      markup.GetNthFiducialPosition(i_n, node_position)
      vertices.append(node_position)

    l_matrix = len(matrix)
    for row in range(l_matrix):
      for col in range(row, l_matrix):
        if matrix[row][col]:
          edges.append([row, col])

    return edges, vertices


class VesselWidget(VerticalLayoutWidget):
  """ Vessels Widget interfaces the Vessels Modelisation ToolKit in one aggregated view.

  Integration includes :
      Vesselness filtering : visualization help to extract vessels
      Level set segmentation : segmentation tool for the vessels
      Center line computation : Extraction of the vessels endpoints from 3D vessels and start point
      Vessels Branch Node Tree : View tree to select, add, show / hide vessels intersection to extract them in one go
  """

  def __init__(self, logic, widgetName, setupBranchF):
    """
    Parameters
    ----------
    logic: RVesselXModuleLogic
    """
    VerticalLayoutWidget.__init__(self, widgetName + " Tab")

    self.vesselSegmentationChanged = Signal("vtkMRMLLabelMapVolumeNode", "List[str]")

    self._widgetName = widgetName
    self._vesselStartSelector = None
    self._vesselEndSelector = None
    self._vesselnessVolume = None
    self._vesselVolumeNode = None
    self._vesselModelNode = None
    self._inputVolume = None
    self._vesselnessDisplay = None
    self._logic = logic
    self._segmentationOpacity = 0.7  # Initial segmentation opacity set to 70% to still view the vessel tree
    self._vesselBranchWidget = VesselBranchWidget(setupBranchF)
    self._vesselBranchWidget.extractVesselsButton.connect("clicked(bool)", self._extractVessel)
    self._vesselBranchWidget.treeValidityChanged.connect(self._updateButtonStatusAndFilterParameters)

    # Extraction strategies
    self._strategies = OrderedDict()
    self._strategies["One vessel per branch"] = ExtractOneVesselPerBranch()
    self._strategies["One vessel per parent child"] = ExtractOneVesselPerParentChildNode()
    self._strategies["One vessel per parent and sub child"] = ExtractOneVesselPerParentAndSubChildNode()
    self._strategies["One vessel for whole tree"] = ExtractAllVesselsInOneGoStrategy()
    self._defaultStrategy = "One vessel per branch"

    # Visualisation tree for Vessels nodes
    self._verticalLayout.addWidget(self._vesselBranchWidget)
    self._verticalLayout.addWidget(self._createDisplayOptionWidget())
    self._verticalLayout.addWidget(self._createAdvancedVesselnessFilterOptionWidget())
    self._verticalLayout.addWidget(self._createAdvancedLevelSetOptionWidget())

    # Connect vessel tree edit change to update add button status
    self._updateButtonStatusAndFilterParameters()

  def clear(self):
    self._removePreviouslyExtractedVessels()
    self._vesselBranchWidget.clear()

  def _createDisplayOptionWidget(self):
    filterOptionCollapsibleButton = ctk.ctkCollapsibleButton()
    filterOptionCollapsibleButton.text = "Display Options"
    filterOptionCollapsibleButton.collapsed = True
    advancedFormLayout = qt.QFormLayout(filterOptionCollapsibleButton)

    markupDisplay = self._vesselBranchWidget.getMarkupDisplayNode()

    # Node display
    textScaleSlider = ctk.ctkSliderWidget()
    textScaleSlider.decimals = 1
    textScaleSlider.minimum = 0
    textScaleSlider.maximum = 20
    textScaleSlider.singleStep = 0.1
    textScaleSlider.value = markupDisplay.GetTextScale()
    valueChangedSig = "valueChanged(double)"
    textScaleSlider.connect(valueChangedSig, markupDisplay.SetTextScale)
    advancedFormLayout.addRow("Node text scale:", textScaleSlider)

    glyphScale = ctk.ctkSliderWidget()
    glyphScale.decimals = 1
    glyphScale.minimum = 0
    glyphScale.maximum = 20
    glyphScale.singleStep = 0.1
    glyphScale.value = markupDisplay.GetGlyphScale()
    glyphScale.connect(valueChangedSig, markupDisplay.SetGlyphScale)
    advancedFormLayout.addRow("Node glyph scale:", glyphScale)

    nodeOpacity = ctk.ctkSliderWidget()
    nodeOpacity.decimals = 1
    nodeOpacity.minimum = 0
    nodeOpacity.maximum = 1
    nodeOpacity.singleStep = 0.1
    nodeOpacity.value = markupDisplay.GetOpacity()
    nodeOpacity.connect(valueChangedSig, markupDisplay.SetOpacity)
    advancedFormLayout.addRow("Node opacity:", nodeOpacity)

    # Tree display
    tree = self._vesselBranchWidget.getTreeDrawer()
    treeLineSizeSlider = ctk.ctkSliderWidget()
    treeLineSizeSlider.decimals = 1
    treeLineSizeSlider.minimum = 0
    treeLineSizeSlider.maximum = 20
    treeLineSizeSlider.singleStep = 0.1
    treeLineSizeSlider.value = tree.getLineWidth()
    treeLineSizeSlider.connect(valueChangedSig, tree.setLineWidth)
    advancedFormLayout.addRow("Line width:", treeLineSizeSlider)

    treeLineOpacitySlider = ctk.ctkSliderWidget()
    treeLineOpacitySlider.decimals = 1
    treeLineOpacitySlider.minimum = 0
    treeLineOpacitySlider.maximum = 1
    treeLineOpacitySlider.singleStep = 0.1
    treeLineOpacitySlider.value = tree.getOpacity()
    treeLineOpacitySlider.connect(valueChangedSig, tree.setOpacity)
    advancedFormLayout.addRow("Line opacity:", treeLineOpacitySlider)

    # Segmented volume display
    segmentationOpacity = ctk.ctkSliderWidget()
    segmentationOpacity.decimals = 1
    segmentationOpacity.minimum = 0
    segmentationOpacity.maximum = 1
    segmentationOpacity.singleStep = 0.1
    segmentationOpacity.value = self._segmentationOpacity
    segmentationOpacity.connect(valueChangedSig, self._setSegmentationOpacity)
    advancedFormLayout.addRow("Segmentation opacity:", segmentationOpacity)

    return filterOptionCollapsibleButton

  def _setSegmentationOpacity(self, opacity):
    self._segmentationOpacity = opacity
    if self._vesselModelNode is not None:
      displayNode = self._vesselModelNode.GetDisplayNode()
      if displayNode is not None:
        displayNode.SetOpacity(opacity)

  def _createAdvancedVesselnessFilterOptionWidget(self):
    filterOptionCollapsibleButton = ctk.ctkCollapsibleButton()
    filterOptionCollapsibleButton.text = "Vesselness Filter Options"
    filterOptionCollapsibleButton.collapsed = True
    advancedFormLayout = qt.QFormLayout(filterOptionCollapsibleButton)

    # Add markups selector
    self._minimumDiameterSpinBox = qt.QSpinBox()
    self._minimumDiameterSpinBox.minimum = 1
    self._minimumDiameterSpinBox.maximum = 1000
    self._minimumDiameterSpinBox.singleStep = 1
    self._minimumDiameterSpinBox.suffix = " voxels"
    self._minimumDiameterSpinBox.toolTip = "Tubular structures that have minimum this diameter will be enhanced."
    advancedFormLayout.addRow("Minimum vessel diameter:", self._minimumDiameterSpinBox)

    self._maximumDiameterSpinBox = qt.QSpinBox()
    self._maximumDiameterSpinBox.minimum = 0
    self._maximumDiameterSpinBox.maximum = 1000
    self._maximumDiameterSpinBox.singleStep = 1
    self._maximumDiameterSpinBox.suffix = " voxels"
    self._maximumDiameterSpinBox.toolTip = "Tubular structures that have maximum this diameter will be enhanced."
    advancedFormLayout.addRow("Maximum vessel diameter:", self._maximumDiameterSpinBox)

    self._contrastSlider = ctk.ctkSliderWidget()
    self._contrastSlider.decimals = 0
    self._contrastSlider.minimum = 0
    self._contrastSlider.maximum = 500
    self._contrastSlider.singleStep = 10
    self._contrastSlider.toolTip = "If the intensity contrast in the input image between vessel and background is high, choose a high value else choose a low value."
    advancedFormLayout.addRow("Vessel contrast:", self._contrastSlider)

    self._suppressPlatesSlider = ctk.ctkSliderWidget()
    self._suppressPlatesSlider.decimals = 0
    self._suppressPlatesSlider.minimum = 0
    self._suppressPlatesSlider.maximum = 100
    self._suppressPlatesSlider.singleStep = 1
    self._suppressPlatesSlider.suffix = " %"
    self._suppressPlatesSlider.toolTip = "A higher value filters out more plate-like structures."
    advancedFormLayout.addRow("Suppress plates:", self._suppressPlatesSlider)

    self._suppressBlobsSlider = ctk.ctkSliderWidget()
    self._suppressBlobsSlider.decimals = 0
    self._suppressBlobsSlider.minimum = 0
    self._suppressBlobsSlider.maximum = 100
    self._suppressBlobsSlider.singleStep = 1
    self._suppressBlobsSlider.suffix = " %"
    self._suppressBlobsSlider.toolTip = "A higher value filters out more blob-like structures."
    advancedFormLayout.addRow("Suppress blobs:", self._suppressBlobsSlider)

    self._useROI = qt.QCheckBox()
    self._useROI.toolTip = "If true will limit vesselness filter and vessel extraction to placed nodes extent."
    advancedFormLayout.addRow("Use bounding box:", self._useROI)

    self._roiSlider = ctk.ctkSliderWidget()
    self._roiSlider.decimals = 1
    self._roiSlider.minimum = 1
    self._roiSlider.maximum = 5
    self._roiSlider.singleStep = 0.1
    self._roiSlider.toolTip = "Growth factor of the bounding box around defined nodes."
    advancedFormLayout.addRow("Bounding box growth factor:", self._roiSlider)

    self._minRoiSlider = ctk.ctkSliderWidget()
    self._minRoiSlider.decimals = 0
    self._minRoiSlider.minimum = 0
    self._minRoiSlider.maximum = 100
    self._minRoiSlider.singleStep = 1
    self._minRoiSlider.toolTip = "Minimum thickness of the bounding box in pixels."
    advancedFormLayout.addRow("Min Bounding Box extent:", self._minRoiSlider)

    # Reset default button
    restoreDefaultButton = qt.QPushButton("Restore")
    restoreDefaultButton.toolTip = "Click to reset all input elements to default."
    restoreDefaultButton.connect("clicked()", self._restoreDefaultVesselnessFilterParameters)
    advancedFormLayout.addRow("Restore default filter parameters:", restoreDefaultButton)
    self._restoreDefaultVesselnessFilterParameters()

    # Show/hide vesselness volume
    showVesselnessCheckbox = qt.QCheckBox()
    showVesselnessCheckbox.connect("stateChanged(int)", self._showVesselnessVolumeChanged)
    advancedFormLayout.addRow("Show vesselness volume:", showVesselnessCheckbox)
    self._showVesselness = False

    return filterOptionCollapsibleButton

  def _createAdvancedLevelSetOptionWidget(self):
    collapsibleButton = ctk.ctkCollapsibleButton()
    collapsibleButton.text = "LevelSet Segmentation Options"
    collapsibleButton.collapsed = True
    segmentationAdvancedFormLayout = qt.QFormLayout(collapsibleButton)

    # inflation slider
    inflationLabel = qt.QLabel()
    inflationLabel.text = "Inflation:"
    inflationLabel.toolTip = "Define how fast the segmentation expands."

    self._inflationSlider = ctk.ctkSliderWidget()
    self._inflationSlider.decimals = 0
    self._inflationSlider.minimum = -100
    self._inflationSlider.maximum = 100
    self._inflationSlider.singleStep = 10
    self._inflationSlider.toolTip = inflationLabel.toolTip
    segmentationAdvancedFormLayout.addRow(inflationLabel, self._inflationSlider)

    # curvature slider
    curvatureLabel = qt.QLabel()
    curvatureLabel.text = "Curvature:"
    curvatureLabel.toolTip = "Choose a high curvature to generate a smooth segmentation."

    self._curvatureSlider = ctk.ctkSliderWidget()
    self._curvatureSlider.decimals = 0
    self._curvatureSlider.minimum = -100
    self._curvatureSlider.maximum = 100
    self._curvatureSlider.singleStep = 10
    self._curvatureSlider.toolTip = curvatureLabel.toolTip
    segmentationAdvancedFormLayout.addRow(curvatureLabel, self._curvatureSlider)

    # attraction slider
    attractionLabel = qt.QLabel()
    attractionLabel.text = "Attraction to gradient:"
    attractionLabel.toolTip = "Configure how the segmentation travels towards gradient ridges (vessel lumen wall)."

    self._attractionSlider = ctk.ctkSliderWidget()
    self._attractionSlider.decimals = 0
    self._attractionSlider.minimum = -100
    self._attractionSlider.maximum = 100
    self._attractionSlider.singleStep = 10
    self._attractionSlider.toolTip = attractionLabel.toolTip
    segmentationAdvancedFormLayout.addRow(attractionLabel, self._attractionSlider)

    # iteration spinbox
    self._iterationSpinBox = qt.QSpinBox()
    self._iterationSpinBox.minimum = 0
    self._iterationSpinBox.maximum = 5000
    self._iterationSpinBox.singleStep = 10
    self._iterationSpinBox.toolTip = "Choose the number of evolution iterations."
    segmentationAdvancedFormLayout.addRow("Iterations:", self._iterationSpinBox)

    # Strategy combo box
    self._strategyChoice = qt.QComboBox()
    self._strategyChoice.addItems(list(self._strategies.keys()))
    self._strategyChoice.toolTip = "Choose the strategy for vessel tree segmentation"
    segmentationAdvancedFormLayout.addRow("Segmentation strategy:", self._strategyChoice)

    # Reset default button
    restoreDefaultButton = qt.QPushButton("Restore")
    restoreDefaultButton.toolTip = "Click to reset all input elements to default."
    restoreDefaultButton.connect("clicked()", self._restoreDefaultLevelSetParameters)
    segmentationAdvancedFormLayout.addRow("Restore default parameters:", restoreDefaultButton)
    self._restoreDefaultLevelSetParameters()

    return collapsibleButton

  def _showVesselnessVolumeChanged(self, state):
    self._showVesselness = state == qt.Qt.Checked
    self._updateVesselnessVisibility()

  def _updateVesselnessVisibility(self):
    self._setVesselnessVisible(self._showVesselness)

  def _setVesselnessVisible(self, isVisible):
    vesselness = self._logic.getCurrentVesselnessVolume()
    if vesselness is None:
      return

    vesselnessDisplayNode = self._getVesselnessDisplayNode(vesselness)
    vesselnessDisplayNode.SetVisibility(isVisible)

    if self._vesselVolumeNode:
      foregroundOpacity = 0.1 if isVisible else 0
      slicer.util.setSliceViewerLayers(background=self._inputVolume, foreground=vesselness,
                                       label=self._vesselVolumeNode, foregroundOpacity=foregroundOpacity)
    else:
      slicer.util.setSliceViewerLayers(background=self._inputVolume)

  def _getVesselnessDisplayNode(self, vesselness):
    if self._vesselnessDisplay is not None:
      self._vesselnessDisplay.SetVisibility(False)

    self._vesselnessDisplay = createDisplayNodeIfNecessary(vesselness, "Vesselness")
    return self._vesselnessDisplay

  def _extractVessel(self):
    """Extract vessels from vessel branch tree. Disable tree interaction and inform user of algorithm processing.
    """
    # Stop branch vessel widget interaction when extracting vessels
    self._vesselBranchWidget.stopInteraction()

    # Remove previous vessels
    self._removePreviouslyExtractedVessels()

    # Call vessel extraction strategy and inform user of vessel extraction
    branchTree = self._vesselBranchWidget.getBranchTree()
    branchMarkupNode = self._vesselBranchWidget.getBranchMarkupNode()

    progressText = "Extracting vessels volume from branch nodes.\nThis may take a minute..."
    progressDialog = slicer.util.createProgressDialog(parent=self, windowTitle="Extracting vessels",
                                                      labelText=progressText)
    progressDialog.setRange(0, 0)
    progressDialog.setModal(True)
    progressDialog.show()

    # Trigger process events to properly show progress dialog
    slicer.app.processEvents()
    try:
      self._updateLevelSetParameters()
      progressDialog.setLabelText(progressText + "\n\nExtracting Vesselness Volume...")
      progressDialog.repaint()
      self._updateVesselnessVolume()
      strategy = self._strategies[self._strategyChoice.currentText]
      progressDialog.setLabelText(progressText + "\n\nSegmenting Vessels...")
      progressDialog.repaint()
      self._vesselVolumeNode, self._vesselModelNode = strategy.extractVesselVolumeFromVesselBranchTree(branchTree,
                                                                                                       branchMarkupNode,
                                                                                                       self._logic)
      self.vesselSegmentationChanged.emit(self._vesselVolumeNode, self._vesselBranchWidget.getBranchNames())
      self._setSegmentationOpacity(self._segmentationOpacity)

    except Exception as e:
      import traceback
      info = traceback.format_exc()
      warning_message = "An error happened while extracting vessels."
      warning_message += "Please try to adjust vesselness or levelset parameters.\n{}\n\n{}".format(str(e), info)
      qt.QMessageBox.warning(self, "Failed to extract vessels", warning_message)

    progressDialog.hide()
    self._updateVisibility()

  def _removePreviouslyExtractedVessels(self):
    """Remove previous nodes from mrmlScene if necessary.
    """
    removeNodesFromMRMLScene([self._vesselVolumeNode, self._vesselModelNode])

  def _updateLevelSetParameters(self):
    """
    Update logic levelset parameters with UI Values
    """
    parameters = LevelSetParameters()
    parameters.iterationNumber = self._iterationSpinBox.value
    parameters.inflation = self._inflationSlider.value
    parameters.attraction = self._attractionSlider.value
    parameters.curvature = self._curvatureSlider.value
    self._logic.levelSetParameters = parameters

  def _updateVesselnessVolume(self):
    """Update vesselness volume with current vesselness filter parameters present in the UI
    """
    # Get parameters from current advanced option parameters
    parameters = VesselnessFilterParameters()
    parameters.minimumDiameter = self._minimumDiameterSpinBox.value
    parameters.maximumDiameter = self._maximumDiameterSpinBox.value
    parameters.suppressPlatesPercent = self._suppressPlatesSlider.value
    parameters.suppressBlobsPercent = self._suppressBlobsSlider.value
    parameters.vesselContrast = self._contrastSlider.value
    parameters.roiGrowthFactor = self._roiSlider.value
    parameters.minROIExtent = self._minRoiSlider.value
    parameters.useROI = self._useROI.checked
    self._logic.vesselnessFilterParameters = parameters

    idPositionDict = getMarkupIdPositionDictionary(self._vesselBranchWidget.getBranchMarkupNode())
    self._logic.updateVesselnessVolume(idPositionDict.values())

  def _restoreDefaultVesselnessFilterParameters(self):
    """Apply default vesselness filter parameters to the UI
    """
    self._updateVesselnessFilterParameters(VesselnessFilterParameters())

  def _restoreDefaultLevelSetParameters(self):
    p = LevelSetParameters()
    self._curvatureSlider.value = p.curvature
    self._attractionSlider.value = p.attraction
    self._inflationSlider.value = p.inflation
    self._iterationSpinBox.value = p.iterationNumber
    self._strategyChoice.setCurrentIndex(self._strategyChoice.findText(self._defaultStrategy))

  def _updateVesselnessFilterParameters(self, params):
    """Updates UI vessel filter parameters with the input VesselnessFilterParameters

    Parameters
    ----------
    params: VesselnessFilterParameters
    """
    self._minimumDiameterSpinBox.value = params.minimumDiameter
    self._maximumDiameterSpinBox.value = params.maximumDiameter
    self._suppressPlatesSlider.value = params.suppressPlatesPercent
    self._suppressBlobsSlider.value = params.suppressBlobsPercent
    self._contrastSlider.value = params.vesselContrast
    self._roiSlider.value = params.roiGrowthFactor
    self._minRoiSlider.value = params.minROIExtent
    self._useROI.setChecked(params.useROI)

  def _updateButtonStatusAndFilterParameters(self):
    """Enable buttons if input volume was selected by user and Tree is not in edit mode. When tree is done with editing
    and vessels populate the tree, vessels can be updated using new filter parameters.
    """
    isEnabled = self._inputVolume is not None and self._vesselBranchWidget.isVesselTreeValid()
    self._vesselBranchWidget.extractVesselsButton.setEnabled(isEnabled)
    self._updateVesselnessFilterParameters(self._logic.vesselnessFilterParameters)

  def setInputNode(self, node):
    """
    On input changed and valid, change current input node and reset vesselness volume used in VMTK algorithms.

    Parameters
    ----------
    node: vtkMRMLNode
    """
    if node and node != self._inputVolume:
      self._vesselnessVolume = None
      self._inputVolume = node
      self._logic.setInputVolume(node)
      self._updateButtonStatusAndFilterParameters()

  def getGeometryExporters(self):
    name = self._widgetName.replace(" ", "")
    node = self._vesselBranchWidget.getBranchMarkupNode()
    return [GeometryExporter(**{name + "Node": node}),
            VesselAdjacencyMatrixExporter(**{name: (node, self._vesselBranchWidget.getBranchTree())})]

  def _setExtractedVolumeVisible(self, isVisible):
    if self._vesselVolumeNode is None or self._vesselModelNode is None:
      return

    self._vesselVolumeNode.SetDisplayVisibility(isVisible)
    self._vesselModelNode.SetDisplayVisibility(isVisible)

    def show_label_in_2d_views():
      slicer.util.setSliceViewerLayers(label=self._vesselVolumeNode if isVisible else None)

    qt.QTimer.singleShot(0, show_label_in_2d_views)

  def showEvent(self, event):
    super(VesselWidget, self).showEvent(event)
    self._updateVisibility()

  def hideEvent(self, event):
    super(VesselWidget, self).hideEvent(event)
    self._updateVisibility()

  def _updateVisibility(self):
    self._vesselBranchWidget.enableShortcuts(self.visible)
    self._vesselBranchWidget.setVisibleInScene(self.visible)
    self._setExtractedVolumeVisible(self.visible)
    self._setVesselnessVisible(self._showVesselness if self.visible else False)

  def getVesselWizard(self):
    return self._vesselBranchWidget.getVesselWizard()


class PortalVesselWidget(VesselWidget):
  def __init__(self, logic):
    super(PortalVesselWidget, self).__init__(logic, "Portal Vessels", setup_portal_vein_default_branch)


class IVCVesselWidget(VesselWidget):
  def __init__(self, logic):
    super(IVCVesselWidget, self).__init__(logic, "IVC Vessels", setup_inferior_cava_vein_default_branch)
