import os
import unittest

import qt
import slicer
from slicer.ScriptedLoadableModule import *

from RVesselXLib import RVesselXLogic, Settings, DataWidget, addInCollapsibleLayout, SegmentWidget, PortalVesselWidget, \
  IVCVesselWidget, PortalVesselEditWidget, IVCVesselEditWidget, createButton
from RVesselXLiverSegmentationEffect import PythonDependencyChecker
from RVesselXTest import RVesselXTestCase, VesselBranchTreeTestCase, ExtractVesselStrategyTestCase, \
  VesselBranchWizardTestCase, VesselSegmentEditWidgetTestCase


class RVesselX(ScriptedLoadableModule):
  def __init__(self, parent=None):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "R Vessel X"
    self.parent.categories = ["Liver Anatomy Annotation"]
    self.parent.dependencies = []
    self.parent.contributors = ["Lucie Macron - Kitware SAS", "Thibault Pelletier - Kitware SAS",
                                "Camille Huet - Kitware SAS"]
    self.parent.helpText = "Liver and hepatic vessels annotation plugin."
    self.parent.acknowledgementText = "Initially developed during the RVesselX research project. " \
                                      "See https://anr.fr/Projet-ANR-18-CE45-0018 for details."


class RVesselXWidget(ScriptedLoadableModuleWidget):
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
    self._portalVesselsTab = None
    self._ivcVesselsTab = None
    self._portalVesselsEditTab = None
    self._ivcEditTab = None

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
    if RVesselXWidget.enableReloadOnSceneClear:
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

  @staticmethod
  def areDependenciesSatisfied():
    # Find extra segment editor effects
    try:
      import SegmentEditorLocalThresholdLib
    except ImportError:
      return False

    return PythonDependencyChecker.areDependenciesSatisfied() and RVesselXLogic.isVmtkFound()

  @staticmethod
  def downloadDependenciesAndRestart():
    progressDialog = slicer.util.createProgressDialog(maximum=0)

    # Install Slicer extensions
    for slicerExt in ["SlicerVMTK", "MarkupsToModel", "SegmentEditorExtraEffects", "PyTorch"]:
      meta_data = slicer.app.extensionsManagerModel().retrieveExtensionMetadataByName(slicerExt)
      if meta_data:
        progressDialog.labelText = f"Installing the {slicerExt}\nSlicer extension"
        slicer.app.extensionsManagerModel().downloadAndInstallExtension(meta_data["extension_id"])

    # Install PIP dependencies
    PythonDependencyChecker.installDependenciesIfNeeded(progressDialog)

    # Restart
    slicer.app.restart()

  def setup(self):
    """Setups widget in Slicer UI.
    """
    ScriptedLoadableModuleWidget.setup(self)

    # Verify Slicer version compatibility
    if not (slicer.app.majorVersion, slicer.app.minorVersion, float(slicer.app.revision)) >= (4, 11, 29738):
      error_msg = "The RVesselX plugin is only compatible from Slicer 4.11 2021.02.26 onwards.\n" \
                  "Please download the latest Slicer version to use this plugin."
      self.layout.addWidget(qt.QLabel(error_msg))
      self.layout.addStretch()
      slicer.util.errorDisplay(error_msg)
      return

    if not self.areDependenciesSatisfied():
      error_msg = "Slicer VMTK, MarkupsToModel, SegmentEditorExtraEffects and MONAI are required by this plugin.\n" \
                  "Please click on the Download button to download and install these dependencies."
      self.layout.addWidget(qt.QLabel(error_msg))
      downloadDependenciesButton = createButton("Download dependencies and restart",
                                                self.downloadDependenciesAndRestart)
      self.layout.addWidget(downloadDependenciesButton)
      self.layout.addStretch()
      return

    # Reset tab list
    self._tabList = []

    # Configure layout and 3D view
    self._configureLayout()
    self._configure3DViewWithMaximumIntensityProjection()

    # Initialize Variables
    self.logic = RVesselXLogic()
    self._dataTab = DataWidget()
    self._liverTab = SegmentWidget(segmentWidgetName="Liver Tab", segmentNodeName="Liver",
                                   segmentNames=["Liver In", "Liver Out"])
    self._portalVesselsTab = PortalVesselWidget(self.logic)
    self._ivcVesselsTab = IVCVesselWidget(self.logic)

    self._portalVesselsEditTab = PortalVesselEditWidget(self.logic, self._portalVesselsTab.getVesselWizard())
    self._ivcEditTab = IVCVesselEditWidget(self.logic, self._ivcVesselsTab.getVesselWizard())
    self._tumorTab = SegmentWidget(segmentWidgetName="Tumor Tab", segmentNodeName="Tumors",
                                   segmentNames=["Tumor", "Not Tumor"])

    # Connect vessels tab to vessels edit tab
    self._portalVesselsTab.vesselSegmentationChanged.connect(self._portalVesselsEditTab.onVesselSegmentationChanged)
    self._ivcVesselsTab.vesselSegmentationChanged.connect(self._ivcEditTab.onVesselSegmentationChanged)

    # Create tab widget and add it to layout in collapsible layout
    self._tabWidget = qt.QTabWidget()
    self._tabWidget.connect("currentChanged(int)", self._adjustTabSizeToContent)
    self.layout.addWidget(self._tabWidget)

    # Add widgets to tab widget and connect data tab input change to the liver and vessels tab set input methods
    self._addTab(self._dataTab, "Data")
    self._addTab(self._liverTab, "Liver")
    self._addTab(self._portalVesselsTab, "Portal Veins")
    self._addTab(self._portalVesselsEditTab, "Portal Veins Edit")
    self._addTab(self._ivcVesselsTab, "IVC Veins")
    self._addTab(self._ivcEditTab, "IVC Veins Edit")
    self._addTab(self._tumorTab, "Tumors")
    self._dataTab.addInputNodeChangedCallback(lambda *x: self._clearTabs())
    self._dataTab.addInputNodeChangedCallback(self._liverTab.setInputNode)
    self._dataTab.addInputNodeChangedCallback(self._portalVesselsTab.setInputNode)
    self._dataTab.addInputNodeChangedCallback(self._portalVesselsEditTab.setInputNode)
    self._dataTab.addInputNodeChangedCallback(self._ivcVesselsTab.setInputNode)
    self._dataTab.addInputNodeChangedCallback(self._ivcEditTab.setInputNode)
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

    # Save scene as MRB
    slicer.util.saveScene(os.path.join(selectedDir, "Scene.mrb"))
    qt.QMessageBox.information(None, "Export Done", "Exported all results to {}".format(selectedDir))

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


class RVesselXTest(ScriptedLoadableModuleTest):
  def runTest(self):
    # Disable module reloading between tests
    RVesselXWidget.enableReloadOnSceneClear = False
    slicer.modules.RVesselXWidget.setTestingMode(True)

    # Gather tests for the plugin and run them in a test suite
    testCases = [RVesselXTestCase, VesselBranchTreeTestCase, VesselBranchWizardTestCase, ExtractVesselStrategyTestCase,
                 VesselSegmentEditWidgetTestCase]

    suite = unittest.TestSuite([unittest.TestLoader().loadTestsFromTestCase(case) for case in testCases])
    unittest.TextTestRunner(verbosity=3).run(suite)

    # Reactivate module reloading and cleanup slicer scene
    RVesselXWidget.enableReloadOnSceneClear = True
    slicer.modules.RVesselXWidget.setTestingMode(False)
    slicer.mrmlScene.Clear()
