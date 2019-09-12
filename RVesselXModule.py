import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import traceback

from RVesselXModuleLogic import RVesselXModuleLogic
from Vessel import VesselTree

_info = logging.info
_warn = logging.warn


def _lineSep(isWarning=False):
  log = _info if not isWarning else _warn
  log('*************************************')


def _warnLineSep():
  _lineSep(isWarning=True)


class RVesselXModule(ScriptedLoadableModule):
  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "R Vessel X"
    self.parent.categories = ["Examples"]
    self.parent.dependencies = []
    self.parent.contributors = ["Lucie Macron - Kitware SAS", "Thibault Pelletier - Kitware SAS"]
    self.parent.helpText = """
        """
    self.parent.acknowledgementText = """
        """


class RVesselXModuleWidget(ScriptedLoadableModuleWidget):
  """Class responsible for the UI of the RVesselX project.

  For more information on the R-Vessel-X project, please visit :
  https://anr.fr/Projet-ANR-18-CE45-0018

  Module is composed of 3 tabs :
    Data Tab : Responsible for loading DICOM data in Slicer
    Liver Tab : Responsible for Liver segmentation
    Vessel Tab : Responsible for vessel segmentation
  """

  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    self.inputSelector = None
    self.volumesModuleSelector = None
    self.volumeRenderingModuleSelector = None
    self.volumeRenderingModuleVisibility = None

    self._vesselVolumeSelector = None
    self._vesselStartSelector = None
    self._vesselEndSelector = None
    self._tabWidget = None
    self._liverTab = None
    self._dataTab = None
    self._vesselsTab = None
    self._vesselTree = None
    self._logic = RVesselXModuleLogic()

    # Define layout #
    layoutDescription = """
          <layout type=\"horizontal\" split=\"true\" >
            <item splitSize=\"500\">
              <view class=\"vtkMRMLSliceNode\" singletontag=\"Red\">
              <property name=\"orientation\" action=\"default\">Axial</property>
              <property name=\"viewlabel\" action=\"default\">R</property>
              <property name=\"viewcolor\" action=\"default\">#F34A33</property>
              </view>
            </item>
            <item splitSize=\"500\">
              <view class=\"vtkMRMLViewNode\" singletontag=\"1\">
              <property name=\"viewlabel\" action=\"default\">1</property>
              </view>
            </item>
          </layout>
        """

    layoutNode = slicer.util.getNode('*LayoutNode*')
    if layoutNode.IsLayoutDescription(layoutNode.SlicerLayoutUserView):
      layoutNode.SetLayoutDescription(layoutNode.SlicerLayoutUserView, layoutDescription)
    else:
      layoutNode.AddLayoutDescription(layoutNode.SlicerLayoutUserView, layoutDescription)
    layoutNode.SetViewArrangement(layoutNode.SlicerLayoutUserView)

  def _createTab(self, tab_name):
    tab = qt.QWidget()
    self._tabWidget.addTab(tab, tab_name)
    return tab

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # Define module interface #
    moduleCollapsibleButton = ctk.ctkCollapsibleButton()
    moduleCollapsibleButton.text = "R Vessel X"

    self.layout.addWidget(moduleCollapsibleButton)

    # Define main tabulations #
    moduleLayout = qt.QVBoxLayout(moduleCollapsibleButton)

    self._tabWidget = qt.QTabWidget()
    moduleLayout.addWidget(self._tabWidget)

    self._dataTab = self._createTab("Data")
    self._liverTab = self._createTab("Liver")
    self._vesselsTab = self._createTab("Vessels")

    self._configureDataTab()
    self._configureLiverTab()
    self._configureVesselsTab()

    slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeAddedEvent, self.onNodeAdded)

  def _setCurrentTab(self, tab_widget):
    self._tabWidget.setCurrentWidget(tab_widget)

  def _addInCollapsibleLayout(self, childLayout, parentLayout, collapsibleText, isCollapsed=True):
    """Wraps input childLayout into a collapsible button attached to input parentLayout.
    collapsibleText is writen next to collapsible button. Initial collapsed status is customizable
    (collapsed by default)
    """
    collapsibleButton = ctk.ctkCollapsibleButton()
    collapsibleButton.text = collapsibleText
    collapsibleButton.collapsed = isCollapsed
    parentLayout.addWidget(collapsibleButton)
    qt.QVBoxLayout(collapsibleButton).addWidget(childLayout)

  def _createSingleMarkupFiducial(self, toolTip, markupName, markupColor=qt.QColor(255, 0, 0)):
    seedFiducialsNodeSelector = slicer.qSlicerSimpleMarkupsWidget()
    seedFiducialsNodeSelector.objectName = markupName + 'NodeSelector'
    seedFiducialsNodeSelector.toolTip = toolTip
    seedFiducialsNodeSelector.setNodeBaseName(markupName)
    seedFiducialsNodeSelector.tableWidget().hide()
    seedFiducialsNodeSelector.defaultNodeColor = markupColor
    seedFiducialsNodeSelector.markupsSelectorComboBox().noneEnabled = False
    seedFiducialsNodeSelector.markupsPlaceWidget().placeMultipleMarkups = slicer.qSlicerMarkupsPlaceWidget.ForcePlaceSingleMarkup
    seedFiducialsNodeSelector.setMRMLScene(slicer.mrmlScene)
    self.parent.connect('mrmlSceneChanged(vtkMRMLScene*)', seedFiducialsNodeSelector, 'setMRMLScene(vtkMRMLScene*)')
    return seedFiducialsNodeSelector

  def _extractVessel(self):
    sourceVolume = self._vesselVolumeSelector.currentNode()
    startPoint = self._vesselStartSelector.currentNode()
    endPoint = self._vesselEndSelector.currentNode()

    self._logic.extractVessel(sourceVolume=sourceVolume, startPoint=startPoint, endPoint=endPoint)

  def _createExtractVesselLayout(self):
    formLayout = qt.QFormLayout()

    # Volume selection input
    self._vesselVolumeSelector = self._createInputNodeSelector("vtkMRMLScalarVolumeNode", toolTip="Select input volume")
    formLayout.addRow("Input Volume:", self._vesselVolumeSelector)

    # Start point fiducial
    self._vesselStartSelector = self._createSingleMarkupFiducial("Select vessel start position", "startPoint",
                                                                 markupColor=qt.QColor("red"))
    formLayout.addRow("Vessel Start:", self._vesselStartSelector)

    # End point fiducial
    self._vesselEndSelector = self._createSingleMarkupFiducial("Select vessel end position", "endPoint",
                                                               markupColor=qt.QColor("blue"))
    formLayout.addRow("Vessel End:", self._vesselEndSelector)

    # Extract Vessel Button
    extractVesselButton = qt.QPushButton("Extract Vessel")
    extractVesselButton.connect("clicked(bool)", self._extractVessel)
    extractVesselButton.setToolTip(
      "Select vessel start point, vessel end point, and volume then press Extract button to extract vessel")
    formLayout.addRow("", extractVesselButton)

    # Enable extract button when all selector nodes are correctly set
    def updateExtractButtonStatus():
      def getNode(node):
        return node.currentNode()

      def fiducialSelected(seedSelector):
        return getNode(seedSelector) and getNode(seedSelector).GetNumberOfFiducials() > 0

      isButtonEnabled = getNode(self._vesselVolumeSelector) and fiducialSelected(
        self._vesselStartSelector) and fiducialSelected(self._vesselEndSelector)
      extractVesselButton.setEnabled(isButtonEnabled)

    self._vesselVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", updateExtractButtonStatus)
    self._vesselStartSelector.connect("updateFinished()", updateExtractButtonStatus)
    self._vesselEndSelector.connect("updateFinished()", updateExtractButtonStatus)

    return formLayout

  def _createInputNodeSelector(self, nodeType, toolTip, callBack=None):
    inputSelector = slicer.qMRMLNodeComboBox()
    inputSelector.nodeTypes = [nodeType]
    inputSelector.selectNodeUponCreation = False
    inputSelector.addEnabled = False
    inputSelector.removeEnabled = False
    inputSelector.noneEnabled = False
    inputSelector.showHidden = False
    inputSelector.showChildNodeTypes = False
    inputSelector.setMRMLScene(slicer.mrmlScene)
    inputSelector.setToolTip(toolTip)
    if callBack is not None:
      inputSelector.connect("currentNodeChanged(vtkMRMLNode*)", callBack)
    return inputSelector

  def _configureDataTab(self):
    dataTabLayout = qt.QVBoxLayout(self._dataTab)

    # Add load MRI button #
    inputLayout = qt.QHBoxLayout()

    inputLabel = qt.QLabel("Volume: ")
    inputLayout.addWidget(inputLabel)
    self.inputSelector = self._createInputNodeSelector("vtkMRMLScalarVolumeNode", toolTip="Pick the input.",
                                                       callBack=self.onInputSelectorNodeChanged)

    inputLayout.addWidget(self.inputSelector)

    loadDicomButton = qt.QPushButton("Load MRI")
    loadDicomButton.connect("clicked(bool)", self.onLoadDMRIClicked)
    inputLayout.addWidget(loadDicomButton)

    dataTabLayout.addLayout(inputLayout)

    # Add Volume information
    volumesWidget = slicer.util.getNewModuleGui(slicer.modules.volumes)
    self._addInCollapsibleLayout(volumesWidget, dataTabLayout, "Volume")

    # Hide Volumes Selector and its label
    activeVolumeNodeSelectorName = "ActiveVolumeNodeSelector"
    widgetToRemoveNames = ["ActiveVolumeLabel", activeVolumeNodeSelectorName]

    for child in volumesWidget.children():
      if child.name in widgetToRemoveNames:
        child.visible = False

      if child.name == activeVolumeNodeSelectorName:
        self.volumesModuleSelector = child

    # Add Volume Rendering information
    volumeRenderingWidget = slicer.util.getNewModuleGui(slicer.modules.volumerendering)
    self._addInCollapsibleLayout(volumeRenderingWidget, dataTabLayout, "Volume Rendering")

    # Hide Volume Rendering Selector and its label
    visibilityCheckboxName = "VisibilityCheckBox"
    volumeNodeSelectorName = "VolumeNodeComboBox"

    for child in volumeRenderingWidget.children():
      if child.name == visibilityCheckboxName:
        child.visible = False
        self.volumeRenderingModuleVisibility = child
      if child.name == volumeNodeSelectorName:
        child.visible = False
        self.volumeRenderingModuleSelector = child

    # Add stretch
    dataTabLayout.addStretch(1)

    # Add Next/Previous arrow
    dataTabLayout.addLayout(self._createPreviousNextArrowsLayout(next_tab=self._liverTab))

  def _configureLiverTab(self):
    """ Liver tab contains segmentation utils for extracting the liver in the input DICOM.

    Direct include of Segmentation Editor is done.
    """
    liverTabLayout = qt.QVBoxLayout(self._liverTab)
    segmentationUi = slicer.util.getNewModuleGui(slicer.modules.segmenteditor)
    liverTabLayout.addWidget(segmentationUi)

    liverTabLayout.addLayout(
      self._createPreviousNextArrowsLayout(previous_tab=self._dataTab, next_tab=self._vesselsTab))

  def _configureVesselsTab(self):
    """ Vessels Tab interfaces the Vessels Modelisation ToolKit in one aggregated view.

    Integration includes :
        Vesselness filtering : visualization help to extract vessels
        Level set segmentation : segmentation tool for the vessels
        Center line computation : Extraction of the vessels endpoints from 3D vessels and start point
        Vessels tree : View tree to select, add, show / hide vessels
    """
    # Visualisation tree for Vessels
    vesselsTabLayout = qt.QVBoxLayout(self._vesselsTab)

    self._vesselTree = VesselTree()
    self._vesselTree.addRow()
    self._vesselTree.addRow()
    self._vesselTree.addRow()
    self._vesselTree.addRow()
    vesselsTabLayout.addWidget(self._vesselTree.getWidget())

    vesselsTabLayout.addLayout(self._createExtractVesselLayout())

    # Add vessel previous and next button (next button will be disabled)
    vesselsTabLayout.addLayout(self._createPreviousNextArrowsLayout(previous_tab=self._liverTab))

  def _createTabButton(self, buttonIcon, nextTab=None):
    """
    Creates a button linking to a given input tab. If input tab is None, button will be disabled
    
    Parameters 
    ----------
    buttonIcon
      Icon for the button
    nextTab
      Next tab which will be set when button is clicked
    
    Returns 
    -------
      QPushButton
    """
    tabButton = qt.QPushButton()
    tabButton.setIcon(buttonIcon)
    if nextTab is not None:
      tabButton.connect('clicked()', lambda tab=nextTab: self._setCurrentTab(tab))
    else:
      tabButton.enabled = False
    return tabButton

  def _createPreviousNextArrowsLayout(self, previous_tab=None, next_tab=None):
    """ Creates HBox layout with previous and next arrows pointing to previous Tab and Next tab given as input.

    If input tabs are None, button will be present but disabled.

    Parameters
    ----------
    previous_tab
      Tab set when clicking on left arrow
    next_tab
      Tab set when clicking on right arrow

    Returns
    -------
    QHBoxLayout
      Layout with previous and next arrows pointing to input tabs
    """
    # Create previous / next arrows
    previousIcon = qt.QApplication.style().standardIcon(qt.QStyle.SP_ArrowLeft)
    previousButton = self._createTabButton(previousIcon, previous_tab)

    nextIcon = qt.QApplication.style().standardIcon(qt.QStyle.SP_ArrowRight)
    nextButton = self._createTabButton(nextIcon, next_tab)

    # Add arrows to Horizontal layout and return layout
    buttonHBoxLayout = qt.QHBoxLayout()
    buttonHBoxLayout.addWidget(previousButton)
    buttonHBoxLayout.addWidget(nextButton)
    return buttonHBoxLayout

  def onLoadDMRIClicked(self):
    # Show DICOM Widget #
    try:
      dicomWidget = slicer.modules.DICOMWidget
    except:
      dicomWidget = slicer.modules.dicom.widgetRepresentation().self()

    if dicomWidget is not None:
      dicomWidget.detailsPopup.open()

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def onNodeAdded(self, caller, event, calldata):
    if isinstance(calldata, slicer.vtkMRMLVolumeNode):
      layoutNode = slicer.util.getNode('*LayoutNode*')
      layoutNode.SetViewArrangement(layoutNode.SlicerLayoutUserView)
      self.setCurrentNode(calldata)

  def onInputSelectorNodeChanged(self):
    node = self.inputSelector.currentNode()

    if node is not None:
      # Update current node on volume and volumeRendering modules
      self.setCurrentNode(node)

      # Show volume
      slicer.util.setSliceViewerLayers(node)
      self.showVolumeRendering(node)

  def setCurrentNode(self, node):
    self.inputSelector.setCurrentNode(node)

    if self.volumesModuleSelector:
      self.volumesModuleSelector.setCurrentNode(node)

    if self.volumeRenderingModuleSelector:
      self.volumeRenderingModuleSelector.setCurrentNode(node)

  def showVolumeRendering(self, volumeNode):
    volRenLogic = slicer.modules.volumerendering.logic()
    displayNode = volRenLogic.CreateDefaultVolumeRenderingNodes(volumeNode)
    displayNode.SetVisibility(True)
    self.reset3DRendererCamera()

  def reset3DRendererCamera(self):
    threeDWidget = slicer.app.layoutManager().threeDWidget(0)
    threeDWidget.threeDView().resetFocalPoint()
    threeDWidget.threeDView().renderWindow().GetRenderers().GetFirstRenderer().ResetCamera()


class RVesselXModuleTest(ScriptedLoadableModuleTest):
  def setUp(self):
    """ Clear scene before each tests
    """
    slicer.mrmlScene.Clear(0)

  def _listTests(self):
    """
    Returns
    -------
    List of every test in test class
    """
    return [func for func in dir(self) if func.startswith('test') and callable(getattr(self, func))]

  def runTest(self):
    """ Runs each test and aggregates results in a list
    """

    className = type(self).__name__
    _info('Running Tests %s' % className)
    _lineSep()

    testList = self._listTests()

    success_count = 0
    failed_name = []
    nTest = len(testList)
    _info("Discovered tests : %s" % testList)
    _lineSep()
    for iTest, testName in enumerate(testList):
      self.setUp()
      test = getattr(self, testName)
      debugTestName = '%s/%s' % (className, testName)
      try:
        _info('Test Start (%d/%d) : %s' % (iTest + 1, nTest, debugTestName))
        test()
        success_count += 1
        _info('Test OK!')
        _lineSep()
      except Exception:
        _warn('Test NOK!')
        _warn(traceback.format_exc())
        failed_name.append(debugTestName)
        _warnLineSep()

    success_count_str = 'Succeeded %d/%d tests' % (success_count, len(testList))
    if success_count != len(testList):
      _warnLineSep()
      _warn('Testing Failed!')
      _warn(success_count_str)
      _warn('Failed tests names : %s' % failed_name)
      _warnLineSep()
    else:
      _lineSep()
      _info('Testing OK!')
      _info(success_count_str)
      _lineSep()

  def _cropSourceVolume(self, sourceVolume, roi):
    cropVolumeNode = slicer.vtkMRMLCropVolumeParametersNode()
    cropVolumeNode.SetScene(slicer.mrmlScene)
    cropVolumeNode.SetName(sourceVolume.GetName() + "Cropped")
    cropVolumeNode.SetIsotropicResampling(True)
    cropVolumeNode.SetSpacingScalingConst(0.5)
    slicer.mrmlScene.AddNode(cropVolumeNode)

    cropVolumeNode.SetInputVolumeNodeID(sourceVolume.GetID())
    cropVolumeNode.SetROINodeID(roi.GetID())

    cropVolumeLogic = slicer.modules.cropvolume.logic()
    cropVolumeLogic.Apply(cropVolumeNode)

    return cropVolumeNode.GetOutputVolumeNode()

  def testVesselSegmentationLogic(self):
    # load test data
    import SampleData
    sampleDataLogic = SampleData.SampleDataLogic()
    sourceVolume = sampleDataLogic.downloadCTACardio()

    # Create start point and end point for the vessel extraction
    startPosition = [176.9, -17.4, 52.7]
    endPosition = [174.704, -23.046, 76.908]

    startPoint = RVesselXModuleLogic._createFiducialNode("startPoint", startPosition)
    endPoint = RVesselXModuleLogic._createFiducialNode("endPoint", endPosition)

    # Crop volume
    roi = slicer.vtkMRMLAnnotationROINode()
    roi.Initialize(slicer.mrmlScene)
    roi.SetName("VolumeCropROI")
    roi.SetXYZ(startPosition[0], startPosition[1], startPosition[2])
    radius = max(abs(a - b) for a, b in zip(startPosition, endPosition)) * 2
    roi.SetRadiusXYZ(radius, radius, radius)

    sourceVolume = self._cropSourceVolume(sourceVolume, roi)

    # Run vessel extraction and expect non empty values and data
    logic = RVesselXModuleLogic()
    vessel = logic.extractVessel(sourceVolume, startPoint, endPoint)

    self.assertIsNotNone(vessel.segmentedVolume())
    self.assertIsNotNone(vessel.segmentedModel())
    self.assertNotEqual(0, vessel.segmentedModel().GetPolyData().GetNumberOfCells())
    self.assertIsNotNone(vessel.centerline())
    self.assertNotEqual(0, vessel.centerline().GetPolyData().GetNumberOfCells())

  def testSetupModule(self):
    """ Setups the module in new window
    """
    module = RVesselXModuleWidget(None)
    module.setup()
    module.cleanup()
    module.parent.close()
