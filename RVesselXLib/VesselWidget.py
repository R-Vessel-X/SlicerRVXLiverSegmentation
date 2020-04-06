import logging

import ctk
import qt
import slicer

from .RVesselXModuleLogic import VesselnessFilterParameters
from .RVesselXUtils import GeometryExporter, removeFromMRMLScene, createDisplayNode
from .VerticalLayoutWidget import VerticalLayoutWidget
from .VesselBranchTree import VesselBranchWidget
from .ExtractVesselStrategies import ExtractOneVesselPerBranch


class VesselWidget(VerticalLayoutWidget):
  """ Vessels Widget interfaces the Vessels Modelisation ToolKit in one aggregated view.

  Integration includes :
      Vesselness filtering : visualization help to extract vessels
      Level set segmentation : segmentation tool for the vessels
      Center line computation : Extraction of the vessels endpoints from 3D vessels and start point
      Vessels Branch Node Tree : View tree to select, add, show / hide vessels intersection to extract them in one go
  """

  def __init__(self, logic):
    """
    Parameters
    ----------
    logic: RVesselXModuleLogic
    """
    VerticalLayoutWidget.__init__(self, "Vessel Tab")

    self._vesselStartSelector = None
    self._vesselEndSelector = None
    self._vesselnessVolume = None
    self._vesselVolumeNode = None
    self._vesselModelNode = None
    self._inputVolume = None
    self._vesselnessDisplay = None
    self._logic = logic
    self._vesselBranchWidget = VesselBranchWidget()
    self._vesselBranchWidget.extractVesselsButton.connect("clicked(bool)", self._extractVessel)
    self._vesselBranchWidget.treeValidityChanged.connect(self._updateButtonStatusAndFilterParameters)

    # Visualisation tree for Vessels nodes
    self._verticalLayout.addWidget(self._vesselBranchWidget)
    self._verticalLayout.addWidget(self._createAdvancedVesselnessFilterOptionWidget())

    # Connect vessel tree edit change to update add button status
    self._updateButtonStatusAndFilterParameters()

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

    # Reset, preview and apply buttons
    restoreDefaultButton = qt.QPushButton("Restore")
    restoreDefaultButton.toolTip = "Click to reset all input elements to default."
    restoreDefaultButton.connect("clicked()", self._restoreDefaultVesselnessFilterParameters)
    advancedFormLayout.addRow("Restore default filter parameters :", restoreDefaultButton)
    self._restoreDefaultVesselnessFilterParameters()

    # Show/hide vesselness volume
    showVesselnessCheckbox = qt.QCheckBox()
    showVesselnessCheckbox.connect("stateChanged(int)", self._showVesselnessVolumeChanged)
    advancedFormLayout.addRow("Show vesselness volume :", showVesselnessCheckbox)
    self._showVesselness = False

    return filterOptionCollapsibleButton

  def _showVesselnessVolumeChanged(self, state):
    self._showVesselness = state == qt.Qt.Checked
    self._updateVesselnessVisibility()

  def _updateVesselnessVisibility(self):
    vesselness = self._logic.getCurrentVesselnessVolume()
    if vesselness is None:
      return

    vesselnessDisplayNode = self._getVesselnessDisplayNode(vesselness)
    vesselnessDisplayNode.SetVisibility(self._showVesselness)

  def _getVesselnessDisplayNode(self, vesselness):
    if self._vesselnessDisplay is not None:
      self._vesselnessDisplay.SetVisibility(False)
      slicer.mrmlScene.RemoveNode(self._vesselnessDisplay)

    self._vesselnessDisplay = createDisplayNode(vesselness, "Vesselness")
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
    strategy = ExtractOneVesselPerBranch()
    progressDialog = slicer.util.createProgressDialog(parent=self, windowTitle="Extracting vessels",
                                                      labelText="Extracting vessels volume from branch nodes."
                                                                "\nThis may take a minute...")
    progressDialog.show()

    # Trigger process events to properly show progress dialog
    slicer.app.processEvents()
    try:
      self._updateVesselnessVolume()
      self._vesselVolumeNode, self._vesselModelNode = strategy.extractVesselVolumeFromVesselBranchTree(branchTree,
                                                                                                       branchMarkupNode,
                                                                                                       self._logic)
    except Exception as e:
      logging.warn(str(e))
      qt.QMessageBox.warning(self, "Failed to extract vessels", "An error happened while extracting vessels."
                                                                "\nMake sure there are at least two nodes"
                                                                " in the branch tree")

    progressDialog.hide()
    self._updateVesselnessVisibility()

  def _removePreviouslyExtractedVessels(self):
    """Remove previous nodes from mrmlScene if necessary.
    """
    removeFromMRMLScene([self._vesselVolumeNode, self._vesselModelNode])

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
    self._logic.vesselnessFilterParameters = parameters

    # Explicitly call vesselness filter update
    self._logic.updateVesselnessVolume()

  def _restoreDefaultVesselnessFilterParameters(self):
    """Apply default vesselness filter parameters to the UI
    """
    defaultParams = VesselnessFilterParameters()
    self._updateVesselnessFilterParameters(defaultParams)

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
    return [GeometryExporter(vesselsVolume=self._vesselVolumeNode, vesselsOuterMesh=self._vesselModelNode)]

  def _setExtractedVolumeVisible(self, isVisible):
    if self._vesselVolumeNode is None or self._vesselModelNode is None:
      return

    self._vesselVolumeNode.SetDisplayVisibility(isVisible)
    self._vesselModelNode.SetDisplayVisibility(isVisible)

  def showEvent(self, event):
    self._vesselBranchWidget.enableShortcuts(True)
    self._vesselBranchWidget.setVisibleInScene(True)
    self._setExtractedVolumeVisible(True)
    super(VesselWidget, self).showEvent(event)

  def hideEvent(self, event):
    self._vesselBranchWidget.enableShortcuts(False)
    self._vesselBranchWidget.setVisibleInScene(False)
    self._setExtractedVolumeVisible(False)
    super(VesselWidget, self).hideEvent(event)
