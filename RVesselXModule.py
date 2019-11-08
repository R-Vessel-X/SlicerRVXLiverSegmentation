import qt
import slicer
import unittest
from slicer.ScriptedLoadableModule import *

from RVesselXLib import RVesselXModuleLogic, Settings, DataWidget, VesselWidget, addInCollapsibleLayout, SegmentWidget
from RVesselXTest import RVesselXModuleTestCase, VesselTreeTestCase, VesselBranchTreeTestCase, \
  ExtractVesselStrategyTestCase


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


class RVesselXModuleTest(ScriptedLoadableModuleTest):
  def runTest(self):
    testCases = [RVesselXModuleTestCase, VesselTreeTestCase, VesselBranchTreeTestCase, ExtractVesselStrategyTestCase]
    suite = unittest.TestSuite([unittest.TestLoader().loadTestsFromTestCase(case) for case in testCases])
    unittest.TextTestRunner(verbosity=3).run(suite)
