import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import traceback

from RVesselXModuleLogic import RVesselXModuleLogic
from Vessel import VesselTree, Vessel

_info = logging.info
_warn = logging.warn


def _lineSep(isWarning=False):
  log = _info if not isWarning else _warn
  log('*************************************')


def _warnLineSep():
  _lineSep(isWarning=True)


class WidgetUtils(object):
  @staticmethod
  def getChildrenContainingName(widget, childString):
    return [child for child in widget.children() if childString.lower() in child.name.lower()]

  @staticmethod
  def getChildContainingName(widget, childString):
    children = WidgetUtils.getChildrenContainingName(widget, childString)
    return children[0] if children else None

  @staticmethod
  def hideChildrenContainingName(widget, childString):
    hiddenChildren = WidgetUtils.getChildrenContainingName(widget, childString)
    for child in WidgetUtils.getChildrenContainingName(widget, childString):
      child.visible = False
    return hiddenChildren

  @staticmethod
  def hideChildContainingName(widget, childString):
    hiddenChild = WidgetUtils.getChildContainingName(widget, childString)
    if hiddenChild:
      hiddenChild.visible = False
    return hiddenChild


class TabAction(object):
  """
  Helper class to trigger enter and exit actions when switching tabs in plugin
  """

  def __init__(self, enterAction=None, exitAction=None):
    self._enterAction = enterAction
    self._exitAction = exitAction

  def enterAction(self):
    if self._enterAction:
      self._enterAction()

  def exitAction(self):
    if self._exitAction:
      self._exitAction()

  @staticmethod
  def noAction():
    return TabAction()


class RVesselXModule(ScriptedLoadableModule):
  def __init__(self, parent=None):
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

  def __init__(self, parent=None):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    self.inputSelector = None
    self.volumesModuleSelector = None
    self.volumeRenderingModuleSelector = None
    self.volumeRenderingModuleVisibility = None

    self._vesselStartSelector = None
    self._vesselEndSelector = None
    self._tabWidget = None
    self._liverTab = None
    self._dataTab = None
    self._vesselsTab = None
    self._vesselTree = None
    self.logic = RVesselXModuleLogic()
    self._liverSegmentNode = None
    self._segmentationWidget = None
    self._tabChangeActions = {}
    self._vesselnessVolume = None
    self._currentTabWidget = None

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
    self._configure3DViewWithMaximumIntensityProjection()

  def _configure3DViewWithMaximumIntensityProjection(self):
    """Configures 3D View to render volumes with raycast maximum intensity projection configuration.
    Background is set to black color.

    This rendering allows to see the vessels and associated segmented areas making it possible to see if parts of the
    volumes have been missed during segmentation.
    """
    # Get 3D view Node
    view = slicer.mrmlScene.GetNodeByID('vtkMRMLViewNode1')

    # Set background color to black
    view.SetBackgroundColor2([0, 0, 0])
    view.SetBackgroundColor([0, 0, 0])

    # Set ray cast technique as maximum intensity projection
    # see https://github.com/Slicer/Slicer/blob/master/Libs/MRML/Core/vtkMRMLViewNode.h
    view.SetRaycastTechnique(2)

  def _createTab(self, tab_name):
    tab = qt.QWidget()
    self._tabWidget.addTab(tab, tab_name)
    return tab

  def setup(self):
    """Setups widget in Slicer UI.
    """
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

    self._tabChangeActions = {self._dataTab: TabAction.noAction(),  #
                              self._vesselsTab: TabAction.noAction(),  #
                              self._liverTab: TabAction(enterAction=self._onEnterLiverTab,
                                                        exitAction=self._onExitLiverTab)}
    self._currentTabWidget = self._dataTab

    self._tabWidget.connect("currentChanged(int)", self._onCurrentTabIndexChanged)

  def _setCurrentTab(self, tab_widget):
    # Change tab to new widget
    self._tabWidget.setCurrentWidget(tab_widget)

  def _onCurrentTabIndexChanged(self, tabIndex):
    # Trigger exit action for current widget
    self._tabChangeActions[self._currentTabWidget].exitAction()

    # Trigger enter action for new widget
    self._currentTabWidget = self._tabWidget.currentWidget()
    self._tabChangeActions[self._currentTabWidget].enterAction()

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

  def _createSingleMarkupFiducial(self, toolTip, markupName, markupColor=qt.QColor("red")):
    """Creates node selector for vtkMarkupFiducial type containing only one point.

    Parameters
    ----------
    toolTip: str
      Input selector hover text
    markupName: str
      Default name for the created markups when new markup is selected
    markupColor: (option) QColor
      Default color for the newly created markups (default = red)

    Returns
    -------
    qSlicerSimpleMarkupsWidget
    """
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
    """Creates vessel from vessel tab start point, end point and selected data. Created vessel is added to VesselTree
    view in Vessel tab.
    """
    sourceVolume = self.inputSelector.currentNode()
    startPoint = self._vesselStartSelector.currentNode()
    endPoint = self._vesselEndSelector.currentNode()

    vessel = self.logic.extractVessel(sourceVolume=sourceVolume, startPoint=startPoint, endPoint=endPoint,
                                      vesselnessVolume=self._vesselnessVolume)
    self._vesselnessVolume = vessel.vesselnessVolume
    self._vesselTree.addVessel(vessel)

    # Set vessel start node as end node and remove end node selection for easier leaf selection for user
    self._vesselStartSelector.setCurrentNode(self._vesselEndSelector.currentNode())
    self._vesselEndSelector.setCurrentNode(None)

    # Reselect source volume as volume input (running logic deselects volume somehow)
    self.inputSelector.setCurrentNode(sourceVolume)

  def _createExtractVesselLayout(self):
    """Creates Layout with vessel start point selector, end point selector and extract vessel button. Button is set to
    be active only when input volume, start and end points are valid.

    Returns
    ------
    QFormLayout
    """
    formLayout = qt.QFormLayout()

    # Start point fiducial
    vesselPointName = "vesselPoint"
    self._vesselStartSelector = self._createSingleMarkupFiducial("Select vessel start position", vesselPointName)
    formLayout.addRow("Vessel Start:", self._vesselStartSelector)

    # End point fiducial
    self._vesselEndSelector = self._createSingleMarkupFiducial("Select vessel end position", vesselPointName)
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

      isButtonEnabled = getNode(self.inputSelector) and fiducialSelected(
        self._vesselStartSelector) and fiducialSelected(self._vesselEndSelector)
      extractVesselButton.setEnabled(isButtonEnabled)

    self.inputSelector.connect("currentNodeChanged(vtkMRMLNode*)", updateExtractButtonStatus)
    self._vesselStartSelector.connect("updateFinished()", updateExtractButtonStatus)
    self._vesselEndSelector.connect("updateFinished()", updateExtractButtonStatus)

    return formLayout

  def _createInputNodeSelector(self, nodeType, toolTip, callBack=None):
    """Creates node selector with given input node type, tooltip and callback when currentNodeChanged signal is emitted

    Parameters
    ----------
    nodeType: vtkMRML type compatible with qMRMLNodeComboBox
      Node type which will be displayed in the combo box
    toolTip: str
      Input selector hover text
    callBack: (optional) function
      Function called when qMRMLNodeComboBox currentNodeChanged is triggered.
      Function must accept a vtkMRMLNode input parameter

    Returns
    -------
    inputSelector : qMRMLNodeComboBox
      configured input selector
    """
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
    """Configure DataTab with load DICOM and Load Data buttons, Input volume selection, Volume 2D and 3D rendering
    """
    dataTabLayout = qt.QVBoxLayout(self._dataTab)

    # Add load MRI button #
    inputLayout = qt.QHBoxLayout()

    inputLabel = qt.QLabel("Volume: ")
    inputLayout.addWidget(inputLabel)

    # Wrap input selector changed method in a timer call so that the volume can be correctly set first
    def inputChangedCallback(node):
      qt.QTimer.singleShot(0, lambda: self.onInputSelectorNodeChanged(node))

    self.inputSelector = self._createInputNodeSelector("vtkMRMLScalarVolumeNode", toolTip="Pick the input.",
                                                       callBack=inputChangedCallback)

    inputLayout.addWidget(self.inputSelector)

    loadDicomButton = qt.QPushButton("Load DICOM")
    loadDicomButton.connect("clicked(bool)", self.onLoadDMRIClicked)
    inputLayout.addWidget(loadDicomButton)

    loadDataButton = qt.QPushButton("Load Data")
    loadDataButton.connect("clicked(bool)", self.onLoadDataClicked)
    inputLayout.addWidget(loadDataButton)

    dataTabLayout.addLayout(inputLayout)

    # Add Volume information
    volumesWidget = slicer.util.getNewModuleGui(slicer.modules.volumes)
    self._addInCollapsibleLayout(volumesWidget, dataTabLayout, "Volume")

    # Hide Volumes Selector and its label
    WidgetUtils.hideChildrenContainingName(volumesWidget, "activeVolume")
    self.volumesModuleSelector = WidgetUtils.getChildContainingName(volumesWidget, "ActiveVolumeNodeSelector")

    # Add Volume Rendering information
    volumeRenderingWidget = slicer.util.getNewModuleGui(slicer.modules.volumerendering)
    self._addInCollapsibleLayout(volumeRenderingWidget, dataTabLayout, "Volume Rendering")

    # Hide Volume Rendering Selector and its label
    self.volumeRenderingModuleVisibility = WidgetUtils.hideChildContainingName(volumeRenderingWidget,
                                                                               "VisibilityCheckBox")
    self.volumeRenderingModuleSelector = WidgetUtils.hideChildContainingName(volumeRenderingWidget,
                                                                             "VolumeNodeComboBox")

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

    # Extract segmentation Widget from segmentation UI
    self._segmentationWidget = WidgetUtils.getChildContainingName(segmentationUi, "EditorWidget")

    # Extract show 3d button and surface smoothing from segmentation widget
    # by default liver 3D will be shown and surface smoothing disabled on entering the liver tab
    self._segmentationShow3dButton = WidgetUtils.getChildContainingName(self._segmentationWidget, "show3d")

    # Extract smoothing button from QMenu attached to show3d button
    self._segmentationSmooth3d = [action for action in self._segmentationShow3dButton.children()[0].actions()  #
                                  if "surface" in action.text.lower()][0]

    # Hide master volume and segmentation node selectors
    WidgetUtils.hideChildrenContainingName(self._segmentationWidget, "masterVolume")
    WidgetUtils.hideChildrenContainingName(self._segmentationWidget, "segmentationNode")

    # Add segmentation volume for the liver
    self._liverSegmentNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
    self._liverSegmentNode.SetName("Liver")

    # Add two segments to segmentation volume
    self._liverSegmentNode.GetSegmentation().AddEmptySegment("LiverIn")
    self._liverSegmentNode.GetSegmentation().AddEmptySegment("LiverOut")

    self._segmentationWidget.setSegmentationNode(self._liverSegmentNode)


    # Add previous and next buttons
    liverTabLayout.addLayout(
      self._createPreviousNextArrowsLayout(previous_tab=self._dataTab, next_tab=self._vesselsTab))

  def _onEnterLiverTab(self):
    # Show liver 3D view and deactivate surface smoothing
    self._segmentationShow3dButton.setChecked(True)
    self._segmentationSmooth3d.setChecked(False)

  def _onExitLiverTab(self):
    # Hide liver 3D view
    self._segmentationShow3dButton.setChecked(False)

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
    """Show DICOM Widget as popup
    """
    try:
      dicomWidget = slicer.modules.DICOMWidget
    except:
      dicomWidget = slicer.modules.dicom.widgetRepresentation().self()

    if dicomWidget is not None:
      dicomWidget.detailsPopup.open()

  def onLoadDataClicked(self):
    slicer.app.ioManager().openAddDataDialog()

  def onInputSelectorNodeChanged(self, node):
    """On volume changed sets input node as current volume and show volume in 2D and 3D view
    """

    if node is not None:
      # Reset vesselness volume
      self._vesselnessVolume = None

      # Update current node on volume and volumeRendering modules
      self.setCurrentNode(node)

      # Show node in 2D view
      slicer.util.setSliceViewerLayers(node)

      # Show node in 3D view
      self.showVolumeRendering(node)

  def setCurrentNode(self, node):
    """Sets inputNode as selected volume node for module. Volume will be used for liver, vessel and tumor segmentation

    :param node: vtkMRMLVolumeNode
    """
    self.inputSelector.setCurrentNode(node)

    if self.volumesModuleSelector:
      self.volumesModuleSelector.setCurrentNode(node)

    if self.volumeRenderingModuleSelector:
      self.volumeRenderingModuleSelector.setCurrentNode(node)

    if self._segmentationWidget:
      self._segmentationWidget.setMasterVolumeNode(node)

  def showVolumeRendering(self, volumeNode):
    """Show input volumeNode in 3D View

    :param volumeNode: vtkMRMLVolumeNode
    """
    if volumeNode is not None:
      volRenLogic = slicer.modules.volumerendering.logic()
      displayNode = volRenLogic.CreateDefaultVolumeRenderingNodes(volumeNode)
      displayNode.SetVisibility(True)
      slicer.util.resetThreeDViews()

      # Load preset
      # https://www.slicer.org/wiki/Documentation/Nightly/ScriptRepository#Show_volume_rendering_automatically_when_a_volume_is_loaded
      scalarRange = volumeNode.GetImageData().GetScalarRange()
      if scalarRange[1] - scalarRange[0] < 1500:
        # small dynamic range, probably MRI
        displayNode.GetVolumePropertyNode().Copy(volRenLogic.GetPresetByName('MR-Default'))
      else:
        # larger dynamic range, probably CT
        displayNode.GetVolumePropertyNode().Copy(volRenLogic.GetPresetByName('CT-Chest-Contrast-Enhanced'))


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

  def _emptyVolume(self, volumeName):
    emptyVolume = slicer.mrmlScene.CreateNodeByClass("vtkMRMLLabelMapVolumeNode")
    emptyVolume.UnRegister(None)
    emptyVolume.SetName(slicer.mrmlScene.GetUniqueNameByString(volumeName))
    return emptyVolume

  def _createVesselWithArbitraryData(self, vesselName=None):
    from itertools import count

    v = Vessel(vesselName)
    pt = ([i, 0, 0] for i in count(start=0, step=1))

    startPoint = RVesselXModuleLogic._createFiducialNode("startPoint", next(pt))
    endPoint = RVesselXModuleLogic._createFiducialNode("endPoint", next(pt))
    seedPoints = RVesselXModuleLogic._createFiducialNode("seedPoint", next(pt), next(pt))

    segmentationVol = self._emptyVolume("segVolume")
    vesselVol = self._emptyVolume("vesselVolume")
    segmentationModel = RVesselXModuleLogic._createModelNode("segModel")
    centerlineModel = RVesselXModuleLogic._createModelNode("centerlineModel")
    voronoiModel = RVesselXModuleLogic._createModelNode("voronoiModel")

    # Create volumes associated with vessel extraction
    v.setExtremities(startPoint=startPoint, endPoint=endPoint)
    v.setSegmentation(seeds=seedPoints, volume=segmentationVol, model=segmentationModel)
    v.setCenterline(centerline=centerlineModel, voronoiModel=voronoiModel)
    v.setVesselnessVolume(vesselnessVolume=vesselVol)
    return v

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

    self.assertIsNotNone(vessel.segmentedVolume)
    self.assertIsNotNone(vessel.segmentedModel)
    self.assertNotEqual(0, vessel.segmentedModel.GetPolyData().GetNumberOfCells())
    self.assertIsNotNone(vessel.segmentedCenterline)
    self.assertNotEqual(0, vessel.segmentedCenterline.GetPolyData().GetNumberOfCells())

  def testVesselCreationNameIsInSegmentationName(self):
    v = self._createVesselWithArbitraryData()
    self.assertIn(v.name, v.segmentedVolume.GetName())
    self.assertIn(v.name, v.segmentedModel.GetName())
    self.assertIn(v.name, v.segmentedCenterline.GetName())

  def testOnRenameRenamesSegmentationName(self):
    v = self._createVesselWithArbitraryData()
    newName = "New Name"
    v.name = newName
    self.assertEqual(newName, v.name)
    self.assertIn(v.name, v.segmentedVolume.GetName())
    self.assertIn(v.name, v.segmentedModel.GetName())
    self.assertIn(v.name, v.segmentedCenterline.GetName())

  def testOnDeleteVesselRemovesAllAssociatedModelsFromSceneExceptStartAndEndPoints(self):
    # Create a vessel
    vessel = self._createVesselWithArbitraryData()

    # Add vessel to tree widget
    tree = VesselTree()
    treeItem = tree.addVessel(vessel)

    # Remove vessel from scene using the delete button trigger
    tree.triggerVesselButton(treeItem, VesselTree.ColumnIndex.delete)

    # Assert the different models are no longer in the scene
    self.assertFalse(slicer.mrmlScene.IsNodePresent(vessel.vesselnessVolume))
    self.assertFalse(slicer.mrmlScene.IsNodePresent(vessel.segmentationSeeds))
    self.assertFalse(slicer.mrmlScene.IsNodePresent(vessel.segmentedVolume))
    self.assertFalse(slicer.mrmlScene.IsNodePresent(vessel.segmentedModel))
    self.assertFalse(slicer.mrmlScene.IsNodePresent(vessel.segmentedCenterline))
    self.assertFalse(slicer.mrmlScene.IsNodePresent(vessel.segmentedVoronoiModel))

    # Assert start and end points are still kept in the scene even after delete
    self.assertTrue(slicer.mrmlScene.IsNodePresent(vessel.startPoint))
    self.assertTrue(slicer.mrmlScene.IsNodePresent(vessel.endPoint))

  def testDeleteLeafVesselRemovesItemFromTree(self):
    # Create a vesselRoot and leaf
    vesselParent = self._createVesselWithArbitraryData("parent")
    vesselLeaf = self._createVesselWithArbitraryData("leaf")
    vesselLeaf.startPoint = vesselParent.endPoint

    # Add vessel to tree widget
    tree = VesselTree()
    treeItem = tree.addVessel(vesselParent)
    treeLeafItem = tree.addVessel(vesselLeaf)

    # Remove vessel from scene using the delete button trigger
    tree.triggerVesselButton(treeLeafItem, VesselTree.ColumnIndex.delete)

    # Verify leaf is not associated with parent
    self.assertEqual(0, treeItem.childCount())

    # verify leaf is not part of the tree
    self.assertFalse(tree.containsItem(treeLeafItem))

  def testDeleteRootVesselRemovesAssociatedLeafs(self):
    # Create vessels and setup hierarchy
    vesselParent = self._createVesselWithArbitraryData("parent")
    vesselChild = self._createVesselWithArbitraryData("child")
    vesselChild.startPoint = vesselParent.endPoint

    vesselChild2 = self._createVesselWithArbitraryData("child 2")
    vesselChild2.startPoint = vesselParent.endPoint

    vesselChild3 = self._createVesselWithArbitraryData("child 3")
    vesselChild3.startPoint = vesselParent.endPoint

    vesselSubChild = self._createVesselWithArbitraryData("sub child")
    vesselSubChild.startPoint = vesselChild.endPoint

    vesselSubChild2 = self._createVesselWithArbitraryData("sub child 2")
    vesselSubChild2.startPoint = vesselChild3.endPoint

    # Create tree and add vessels to the tree
    tree = VesselTree()
    treeItemParent = tree.addVessel(vesselParent)
    treeItemChild = tree.addVessel(vesselChild)
    treeItemChild2 = tree.addVessel(vesselChild2)
    treeItemChild3 = tree.addVessel(vesselChild3)
    treeItemSubChild = tree.addVessel(vesselSubChild)
    treeItemSubChild2 = tree.addVessel(vesselSubChild2)

    # Remove child 1 and expect child and sub to be deleted
    tree.triggerVesselButton(treeItemChild, VesselTree.ColumnIndex.delete)
    self.assertFalse(tree.containsItem(treeItemChild))
    self.assertFalse(tree.containsItem(treeItemSubChild))

    # Remove root and expect all to be deleted
    tree.triggerVesselButton(treeItemParent, VesselTree.ColumnIndex.delete)
    self.assertFalse(tree.containsItem(treeItemParent))
    self.assertFalse(tree.containsItem(treeItemChild2))
    self.assertFalse(tree.containsItem(treeItemChild3))
    self.assertFalse(tree.containsItem(treeItemSubChild2))

  def testOnAddingVesselWithStartPointIdenticalToOtherVesselEndPointAddsVesselAsChildOfOther(self):
    # Create vessels and setup hierarchy
    vesselParent = self._createVesselWithArbitraryData("parent")
    vesselChild = self._createVesselWithArbitraryData("child")
    vesselChild.startPoint = vesselParent.endPoint

    vesselChild2 = self._createVesselWithArbitraryData("child 2")
    vesselChild2.startPoint = vesselParent.endPoint

    vesselSubChild = self._createVesselWithArbitraryData("sub child")
    vesselSubChild.startPoint = vesselChild.endPoint

    # Create tree and add vessels to the tree
    tree = VesselTree()
    treeItemParent = tree.addVessel(vesselParent)
    treeItemChild = tree.addVessel(vesselChild)
    treeItemChild2 = tree.addVessel(vesselChild2)
    treeItemSubChild = tree.addVessel(vesselSubChild)

    # Verify hierarchy
    self.assertEqual(2, treeItemParent.childCount())
    self.assertEqual(1, treeItemChild.childCount())

    self.assertEqual(treeItemParent, treeItemChild.parent())
    self.assertEqual(treeItemParent, treeItemChild2.parent())
    self.assertEqual(treeItemChild, treeItemSubChild.parent())

  def testLogicRaisesErrorWhenCalledWithNoneInputs(self):
    logic = RVesselXModuleLogic()

    with self.assertRaises(ValueError):
      logic._applyLevelSetSegmentation(None, None, None, None)

    with self.assertRaises(ValueError):
      logic._applyVesselnessFilter(None, None)

    with self.assertRaises(ValueError):
      logic._applyCenterlineFilter(None, None, None)

    with self.assertRaises(ValueError):
      logic.extractVessel(None, None, None)
