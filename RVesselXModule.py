import os

import qt
import slicer
import vtk
from slicer.ScriptedLoadableModule import *

from RVesselXLib import RVesselXModuleLogic, info, warn, lineSep, warnLineSep, GeometryExporter, Settings, VesselTree, \
  Vessel, DataWidget, VesselWidget, addInCollapsibleLayout, SegmentWidget, IRVesselXModuleLogic, VesselTreeItem


class RVesselXModule(ScriptedLoadableModule):
  def __init__(self, parent=None):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "R Vessel X"
    self.parent.categories = [self.parent.title]
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

    self.logic = None
    self._tabWidget = None
    self._dataTab = None
    self._liverTab = None
    self._vesselsTab = None
    self._tumorTab = None
    self._tabList = []

  def _configureLayout(self):
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

  def _addTab(self, tab, tabName):
    self._tabWidget.addTab(tab, tabName)
    self._tabList.append(tab)

  def setup(self):
    """Setups widget in Slicer UI.
    """
    ScriptedLoadableModuleWidget.setup(self)
    # Reset tab list
    self._tabList = []

    # Configure layout and 3D view
    self._configureLayout()
    self._configure3DViewWithMaximumIntensityProjection()

    # Initialize Variables
    self.logic = RVesselXModuleLogic()
    self._dataTab = DataWidget()
    self._liverTab = SegmentWidget(segmentWidgetName="Liver Tab", segmentNodeName="Liver",
                                   segmentNames=["LiverIn", "LiverOut"])
    self._vesselsTab = VesselWidget(self.logic)
    self._tumorTab = SegmentWidget(segmentWidgetName="Tumor Tab", segmentNodeName="Tumors")

    # Create tab widget and add it to layout in collapsible layout
    self._tabWidget = qt.QTabWidget()
    addInCollapsibleLayout(self._tabWidget, self.layout, "R Vessel X", isCollapsed=False)

    # Add widgets to tab widget and connect data tab input change to the liver and vessels tab set input methods
    self._addTab(self._dataTab, "Data")
    self._addTab(self._liverTab, "Liver")
    self._addTab(self._vesselsTab, "Vessels")
    self._addTab(self._tumorTab, "Tumors")
    self._dataTab.addInputNodeChangedCallback(self._liverTab.setInputNode)
    self._dataTab.addInputNodeChangedCallback(self._vesselsTab.setInputNode)
    self._dataTab.addInputNodeChangedCallback(self._tumorTab.setInputNode)

    # Setup previous and next buttons for the different tabs
    self._configurePreviousNextTabButtons()

  def _configurePreviousNextTabButtons(self):
    """Adds previous and next buttons to tabs added to layout. If previous tab is not defined, button will be grayed out.
    If next tab is not defined, next button will be replaced by export button.
    """
    for i, tab in enumerate(self._tabList):
      prev_tab = self._tabList[i - 1] if i - 1 >= 0 else None
      next_tab = self._tabList[i + 1] if i + 1 < len(self._tabList) else None
      tab.insertLayout(0, self._createPreviousNextArrowsLayout(previous_tab=prev_tab, next_tab=next_tab))

  def _setCurrentTab(self, tab_widget):
    # Change tab to new widget
    self._tabWidget.setCurrentWidget(tab_widget)

  def _exportVolumes(self):
    """Export every volume of RVesselX to specified user directory.
    Does nothing if no user directory is selected.
    """
    # Query output directory from user and early return in case of cancel
    selectedDir = qt.QFileDialog.getExistingDirectory(None, "Select export directory", Settings.exportDirectory())

    if not selectedDir:
      return

    # Save user directory in settings
    Settings.setExportDirectory(selectedDir)

    # Export each volume to export to export directory
    for vol in self._volumesToExport():
      vol.exportToDirectory(selectedDir)

  def _volumesToExport(self):
    """Creates list of GeometryExporter associated with every element to export (ie Vessels, liver and tumors)

    Returns
    -------
      List[GeometryExporter]
    """
    # Aggregate every volume to export
    volumesToExport = []
    for tab in self._tabList:
      volumesToExport.extend(tab.getGeometryExporters())

    # return only not None elements
    return [vol for vol in volumesToExport if vol is not None]

  def _createTabButton(self, buttonIcon, nextTab=None):
    """Creates a button linking to a given input tab. If input tab is None, button will be disabled

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
      tabButton.setText(nextTab.name)
    else:
      tabButton.enabled = False
    return tabButton

  def _createPreviousNextArrowsLayout(self, previous_tab=None, next_tab=None):
    """Creates HBox layout with previous and next arrows pointing to previous Tab and Next tab given as input.

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

    # Create Next button if next tab is set.
    if next_tab:
      nextIcon = qt.QApplication.style().standardIcon(qt.QStyle.SP_ArrowRight)
      nextButton = self._createTabButton(nextIcon, next_tab)
    else:  # Else set next button as export button
      nextIcon = qt.QApplication.style().standardIcon(qt.QStyle.SP_DialogSaveButton)
      nextButton = qt.QPushButton("Export all segmented volumes")
      nextButton.connect('clicked(bool)', self._exportVolumes)
      nextButton.setIcon(nextIcon)

    # Add arrows to Horizontal layout and return layout
    buttonHBoxLayout = qt.QHBoxLayout()
    buttonHBoxLayout.addWidget(previousButton)
    buttonHBoxLayout.addWidget(nextButton)
    return buttonHBoxLayout


class TemporaryDir(object):
  """Helper context manager for creating and removing temporary directory for testing purposes
  """

  def __init__(self, dirSuffix="RVesselX"):
    self._dirSuffix = dirSuffix
    self._dir = None

  def __enter__(self):
    import tempfile
    self._dir = tempfile.mkdtemp(suffix=self._dirSuffix)
    return self._dir

  def __exit__(self, *args):
    import shutil
    shutil.rmtree(self._dir)
    pass


class FakeLogic(IRVesselXModuleLogic):
  """Fake logic for faster tests of vessel tree
  """

  def __init__(self, returnedVessel=None):
    self.returnedVessel = returnedVessel
    self._input = None

  def setReturnedVessel(self, vessel):
    self._vessel = vessel

  @property
  def returnedVessel(self):
    return self._vessel

  @returnedVessel.setter
  def returnedVessel(self, value):
    self._vessel = value

  def extractVessel(self, startPoint, endPoint):
    return self._vessel


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
    import traceback

    className = type(self).__name__
    info('Running Tests %s' % className)
    lineSep()

    testList = self._listTests()

    success_count = 0
    failed_name = []
    nTest = len(testList)
    info("Discovered tests : %s" % testList)
    lineSep()
    for iTest, testName in enumerate(testList):
      self.setUp()
      test = getattr(self, testName)
      debugTestName = '%s/%s' % (className, testName)
      try:
        info('Test Start (%d/%d) : %s' % (iTest + 1, nTest, debugTestName))
        test()
        success_count += 1
        info('Test OK!')
        lineSep()
      except Exception:
        warn('Test NOK!')
        warn(traceback.format_exc())
        failed_name.append(debugTestName)
        warnLineSep()

    success_count_str = 'Succeeded %d/%d tests' % (success_count, len(testList))
    if success_count != len(testList):
      warnLineSep()
      warn('Testing Failed!')
      warn(success_count_str)
      warn('Failed tests names : %s' % failed_name)
      warnLineSep()
    else:
      lineSep()
      info('Testing OK!')
      info(success_count_str)
      lineSep()

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

  def _nonEmptyVolume(self, volumeName="VolumeName"):
    import numpy as np

    arbitraryGenerativeFunction = np.fromfunction(lambda x, y, z: 0.5 * x * x + 0.3 * y * y + 0.5 * z * z, (30, 20, 15))
    volumeNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLScalarVolumeNode')
    volumeNode.CreateDefaultDisplayNodes()
    volumeNode.SetName(volumeName)
    slicer.util.updateVolumeFromArray(volumeNode, arbitraryGenerativeFunction)
    return volumeNode

  def _nonEmptyModel(self, modelName="ModelName"):
    sphere = vtk.vtkSphereSource()
    sphere.SetRadius(30.0)
    sphere.Update()
    modelNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode')
    modelNode.SetAndObservePolyData(sphere.GetOutput())
    modelNode.SetName(modelName)
    return modelNode

  def testVesselSegmentationLogic(self):
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
    logic.setInputVolume(sourceVolume)
    vessel = logic.extractVessel(startPoint, endPoint)

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
    tree = VesselTree(FakeLogic())
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
    tree = VesselTree(FakeLogic())
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
    tree = VesselTree(FakeLogic())
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
    tree = VesselTree(FakeLogic())
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

  def testGeometryExporterSavesVolumesAsNiftiAndModelsAsVtkFiles(self):
    # Create non empty model and volume nodes (empty nodes are not exported)
    model = self._nonEmptyModel()
    volume = self._nonEmptyVolume()

    # Create geometry exporter and add the two nodes to it
    exporter = GeometryExporter()
    exporter["ModelFileName"] = model
    exporter["VolumeFileName"] = volume

    # Create temporary dir to export the data
    with TemporaryDir() as outputDir:
      # Export nodes in the exporter
      exporter.exportToDirectory(outputDir)

      # Expect the nodes have been correctly exported
      expModelPath = os.path.join(outputDir, "ModelFileName.vtk")
      expVolumePath = os.path.join(outputDir, "VolumeFileName.nii")
      self.assertTrue(os.path.isfile(expModelPath))
      self.assertTrue(os.path.isfile(expVolumePath))

  def testVesselsReturnGeometryExporterContainingCenterlineAndVolume(self):
    vesselName = "AVesselName"
    vessel = self._createVesselWithArbitraryData(vesselName)

    expCenterline = self._nonEmptyModel()
    expVolume = self._nonEmptyVolume()

    self.assertNotEqual(vessel.segmentedCenterline, expCenterline)
    self.assertNotEqual(vessel.segmentedCenterline, expVolume)
    vessel.setCenterline(expCenterline, vessel.segmentedVoronoiModel)
    vessel.setSegmentation(vessel.segmentationSeeds, expVolume, vessel.segmentedModel)

    exporter = vessel.getGeometryExporter()
    self.assertEqual(expCenterline, exporter[vesselName + "CenterLine"])
    self.assertEqual(expVolume, exporter[vesselName])

  def testAfterEditingIsFinishedItemHasVesselStartAndEndPointNodes(self):
    # Create vessel
    vesselName = "AVesselName"
    vessel = self._createVesselWithArbitraryData(vesselName)
    vessel.startPoint.SetName("Start")
    vessel.endPoint.SetName("End")

    # Populate vessel in tree (will trigger edit stop)
    tree = VesselTree(FakeLogic())
    item = tree.addVessel(vessel)

    # Verify start and end are correctly set to vessel values
    self.assertEqual(vessel.startPoint, item.startPoint)
    self.assertEqual(vessel.endPoint, item.endPoint)

  def testAfterStopEditIfFirstEditOrderVesselInTree(self):
    # Create vessels
    vesselParent = self._createVesselWithArbitraryData("parent")
    vesselChild = self._createVesselWithArbitraryData("child")
    vesselChild.startPoint = vesselParent.endPoint

    # Create tree and add vessels to the tree
    logic = FakeLogic()
    tree = VesselTree(logic)

    # Add parent
    logic.setReturnedVessel(vesselParent)
    treeItemParent = tree.addNewVessel()
    tree.stopEditMode(treeItemParent)

    # Add child
    logic.setReturnedVessel(vesselChild)
    treeItemChild = tree.addNewVessel()
    tree.stopEditMode(treeItemChild)

    # Assert child parent has been set to parent vessel
    self.assertEqual(treeItemParent, treeItemChild.parent())

  def testAfterEditingVesselRemoveOldOneFromScene(self):
    class FakeVessel(Vessel):
      def __init__(self):
        Vessel.__init__(self)
        self.wasRemovedFromScene = False

      @staticmethod
      def copyFrom(other):
        fake = FakeVessel()
        for key in other.__dict__.keys():
          setattr(fake, key, getattr(other, key))
        return fake

      def removeFromScene(self):
        self.wasRemovedFromScene = True

    oldVessel = FakeVessel.copyFrom(self._createVesselWithArbitraryData())
    tree = VesselTree(FakeLogic())
    item = tree.addVessel(oldVessel)

    tree.stopEditMode(item)
    self.assertTrue(oldVessel.wasRemovedFromScene)
