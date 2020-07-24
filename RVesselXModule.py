import unittest

import qt
import slicer
from slicer.ScriptedLoadableModule import *

from RVesselXLib import RVesselXModuleLogic, Settings, DataWidget, VesselWidget, addInCollapsibleLayout, SegmentWidget, \
  VesselSegmentEditWidget
from RVesselXTest import RVesselXModuleTestCase, VesselBranchTreeTestCase, ExtractVesselStrategyTestCase, \
  VesselBranchWizardTestCase, VesselSegmentEditWidgetTestCase


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

  Module is composed of 4 tabs :
    Data Tab : Responsible for loading DICOM data in Slicer
    Liver Tab : Responsible for Liver segmentation
    Vessel Tab : Responsible for vessel segmentation
    Tumor Tab : Responsible for tumor segmentation
  """
  enableReloadOnSceneClear = True

  def __init__(self, parent=None):
    ScriptedLoadableModuleWidget.__init__(self, parent)

    self.logic = None
    self._tabWidget = None
    self._dataTab = None
    self._liverTab = None
    self._vesselsTab = None
    self._vesselsSegmentEditTab = None
    self._tumorTab = None
    self._tabList = []
    self._obs = slicer.mrmlScene.AddObserver(slicer.mrmlScene.EndCloseEvent, lambda *x: self.reloadModule())

  def setTestingMode(self, isTesting):
    for tab in self._tabList:
      tab.setTestingMode(isTesting)

  def cleanup(self):
    """Cleanup called before reloading module. Removes mrmlScene observer to avoid multiple setup of the module
    """
    slicer.mrmlScene.RemoveObserver(self._obs)
    ScriptedLoadableModuleWidget.cleanup(self)

  def reloadModule(self):
    """Reload module only if reloading is enabled (ie : not when testing module).

    Implementation closely resembles super class onReload method but without verbosity and with enabling handled.
    """
    if RVesselXModuleWidget.enableReloadOnSceneClear:
      slicer.util.reloadScriptedModule(self.moduleName)

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

    # Add button to layout selector toolbar for this custom layout
    viewToolBar = slicer.util.mainWindow().findChild('QToolBar', 'ViewToolBar')
    layoutMenu = viewToolBar.widgetForAction(viewToolBar.actions()[0]).menu()

    # Add layout button to menu
    rVesselXActionText = "RVesselX 2 Panel View"
    hasRVesselXButton = rVesselXActionText in [action.text for action in layoutMenu.actions()]
    if not hasRVesselXButton:
      layoutSwitchAction = layoutMenu.addAction(rVesselXActionText)
      layoutSwitchAction.setData(layoutNode.SlicerLayoutUserView)
      layoutSwitchAction.setIcon(qt.QIcon(':Icons/LayoutSideBySideView.png'))
      layoutSwitchAction.setToolTip(rVesselXActionText)
      layoutSwitchAction.connect('triggered()',
                                 lambda: slicer.app.layoutManager().setLayout(layoutNode.SlicerLayoutUserView))
      layoutMenu.setActiveAction(layoutSwitchAction)

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
                                   segmentNames=["Liver In", "Liver Out"])
    self._vesselsTab = VesselWidget(self.logic)
    self._vesselsSegmentEditTab = VesselSegmentEditWidget(self.logic, self._vesselsTab.getVesselWizard())
    self._tumorTab = SegmentWidget(segmentWidgetName="Tumor Tab", segmentNodeName="Tumors",
                                   segmentNames=["Tumor", "Not Tumor"])

    # Connect vessels tab to vessels edit tab
    self._vesselsTab.vesselSegmentationChanged.connect(self._vesselsSegmentEditTab.onVesselSegmentationChanged)

    # Create tab widget and add it to layout in collapsible layout
    self._tabWidget = qt.QTabWidget()
    self._tabWidget.connect("currentChanged(int)", self._adjustTabSizeToContent)
    addInCollapsibleLayout(self._tabWidget, self.layout, "R Vessel X", isCollapsed=False)

    # Add widgets to tab widget and connect data tab input change to the liver and vessels tab set input methods
    self._addTab(self._dataTab, "Data")
    self._addTab(self._liverTab, "Liver")
    self._addTab(self._vesselsTab, "Vessels")
    self._addTab(self._vesselsSegmentEditTab, "Vessels Segmentation Edit")
    self._addTab(self._tumorTab, "Tumors")
    self._dataTab.addInputNodeChangedCallback(lambda *x: self._clearTabs())
    self._dataTab.addInputNodeChangedCallback(self._liverTab.setInputNode)
    self._dataTab.addInputNodeChangedCallback(self._vesselsTab.setInputNode)
    self._dataTab.addInputNodeChangedCallback(self._vesselsSegmentEditTab.setInputNode)
    self._dataTab.addInputNodeChangedCallback(self._tumorTab.setInputNode)

    # Setup previous and next buttons for the different tabs
    self._configurePreviousNextTabButtons()

  def _clearTabs(self):
    """
    Clears all tabs from previous computations
    """
    for tab in self._tabList:
      tab.clear()

  def _configure3DViewWithMaximumIntensityProjection(self):
    """Configures 3D View to render volumes with ray casting maximum intensity projection configuration.
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
    """Add input tab to the tab widget and to the tab list.

    Parameters
    ----------
    tab: qt.QWidget
    tabName: str
      Display label of the tab
    """
    self._tabWidget.addTab(tab, tabName)
    self._tabList.append(tab)

  def _adjustTabSizeToContent(self, index):
    """Update current tab size to adjust to its content.

    Parameters
    ----------
    index: int
      Index of new widget to which the tab size will be adjusted
    """
    for i in range(self._tabWidget.count):
      self._tabWidget.widget(i).setSizePolicy(qt.QSizePolicy.Ignored, qt.QSizePolicy.Ignored)

    self._tabWidget.widget(index).setSizePolicy(qt.QSizePolicy.Preferred, qt.QSizePolicy.Preferred)
    self._tabWidget.widget(index).resize(self._tabWidget.widget(index).minimumSizeHint)
    self._tabWidget.widget(index).adjustSize()

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
      exporters = tab.getGeometryExporters()
      if exporters:
        volumesToExport.extend(exporters)

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
    # Disable module reloading between tests
    RVesselXModuleWidget.enableReloadOnSceneClear = False
    slicer.modules.RVesselXModuleWidget.setTestingMode(True)

    # Gather tests for the plugin and run them in a test suite
    testCases = [RVesselXModuleTestCase, VesselBranchTreeTestCase, VesselBranchWizardTestCase,
                 ExtractVesselStrategyTestCase, VesselSegmentEditWidgetTestCase]
    suite = unittest.TestSuite([unittest.TestLoader().loadTestsFromTestCase(case) for case in testCases])
    unittest.TextTestRunner(verbosity=3).run(suite)

    # Reactivate module reloading and cleanup slicer scene
    RVesselXModuleWidget.enableReloadOnSceneClear = True
    slicer.modules.RVesselXModuleWidget.setTestingMode(False)
    slicer.mrmlScene.Clear()
