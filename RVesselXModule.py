import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging

#
# RVesselXModule
#

class RVesselXModule(ScriptedLoadableModule):
  """
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "R Vessel X"
    self.parent.categories = ["Examples"]
    self.parent.dependencies = []
    self.parent.contributors = ["Lucie Macron - Kitware SAS"]
    self.parent.helpText = """
    """
    self.parent.acknowledgementText = """
    """

#
# RVesselXModuleWidget
#

class RVesselXModuleWidget(ScriptedLoadableModuleWidget):
  """
  """
  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    self.inputSelector = None
    self.volumesModuleSelector = None
    self.volumeRenderingModuleSelector = None
    self.volumeRenderingModuleVisibility = None

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

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # Define module interface #
    self.moduleCollapsibleButton = ctk.ctkCollapsibleButton()
    self.moduleCollapsibleButton.text = "R Vessel X"

    self.layout.addWidget(self.moduleCollapsibleButton)

    # Define main tabulations #
    self.moduleLayout = qt.QVBoxLayout(self.moduleCollapsibleButton)

    self.tabWidget = qt.QTabWidget()
    self.moduleLayout.addWidget(self.tabWidget)

    self.dataTab = qt.QWidget()
    self.tabWidget.addTab(self.dataTab, "Data")
    self.liverTab = qt.QWidget()
    self.tabWidget.addTab(self.liverTab, "Liver")
    self.vesselsTab = qt.QWidget()
    self.tabWidget.addTab(self.vesselsTab, "Vessels")

    self.defineDataTab()
    self.defineLiverTab()

    slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeAddedEvent, self.onNodeAdded)

  def setCurrentTab(self, tabWidget):
    print('TEST SET TAB')
    self.tabWidget.setCurrentWidget(tabWidget)

  def defineDataTab(self):
    dataTabLayout = qt.QVBoxLayout(self.dataTab)

    # Add load MRI button #

    inputLayout = qt.QHBoxLayout()

    inputLabel = qt.QLabel("Volume: ")
    inputLayout.addWidget(inputLabel)
    self.inputSelector = slicer.qMRMLNodeComboBox()
    self.inputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.inputSelector.selectNodeUponCreation = False
    self.inputSelector.addEnabled = False
    self.inputSelector.removeEnabled = False
    self.inputSelector.noneEnabled = False
    self.inputSelector.showHidden = False
    self.inputSelector.showChildNodeTypes = False
    self.inputSelector.setMRMLScene( slicer.mrmlScene )
    self.inputSelector.setToolTip( "Pick the input." )
    self.inputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onInputSelectorNodeChanged)

    inputLayout.addWidget(self.inputSelector)

    loadDicomButton = qt.QPushButton("Load MRI")
    loadDicomButton.connect("clicked(bool)", self.onLoadDMRIClicked)
    inputLayout.addWidget(loadDicomButton)

    dataTabLayout.addLayout(inputLayout)

    # Add Volume information #

    volumeCollapsibleButton = ctk.ctkCollapsibleButton()
    volumeCollapsibleButton.text = "Volume"
    volumeCollapsibleButton.collapsed = True
    dataTabLayout.addWidget(volumeCollapsibleButton)
    volumesGroupBoxLayout = qt.QVBoxLayout(volumeCollapsibleButton)

    volumesWidget = slicer.util.getNewModuleGui(slicer.modules.volumes)
    volumesGroupBoxLayout.addWidget(volumesWidget)

    ## Hide Volumes Selector and its label ##
    children = volumesWidget.children()

    activeVolumeNodeSelectorName = "ActiveVolumeNodeSelector"
    WidgetToRemoveNames = ["ActiveVolumeLabel", activeVolumeNodeSelectorName]

    for child in children:
      if child.name in WidgetToRemoveNames:
        child.visible = False

      if child.name == activeVolumeNodeSelectorName:
        self.volumesModuleSelector = child

    # Add Volume Rendering information #

    volumeRenderingCollapsibleButton = ctk.ctkCollapsibleButton()
    volumeRenderingCollapsibleButton.text = "Volume Rendering"
    volumeRenderingCollapsibleButton.collapsed = True
    dataTabLayout.addWidget(volumeRenderingCollapsibleButton)
    volumeRenderingGroupBoxLayout = qt.QVBoxLayout(volumeRenderingCollapsibleButton)

    volumeRenderingWidget = slicer.util.getNewModuleGui(slicer.modules.volumerendering)
    volumeRenderingGroupBoxLayout.addWidget(volumeRenderingWidget)

    children = volumeRenderingWidget.children()

    ## Hide Volume Rendering Selector and its label ##

    visibilityCheckboxName = "VisibilityCheckBox"
    volumeNodeSelectorName = "VolumeNodeComboBox"

    for child in children:
      if child.name == visibilityCheckboxName:
        child.visible = False
        self.volumeRenderingModuleVisibility = child
      if child.name == volumeNodeSelectorName:
        child.visible = False
        self.volumeRenderingModuleSelector = child

    # Add stretch

    dataTabLayout.addStretch(1)

    # Add Next/Previous arrow
    previousButton = qt.QPushButton()
    previousButton.enabled = False
    previousIcon = qt.QApplication.style().standardIcon(qt.QStyle.SP_ArrowLeft)
    previousButton.setIcon(previousIcon)

    nextButton = qt.QPushButton()
    nextIcon = qt.QApplication.style().standardIcon(qt.QStyle.SP_ArrowRight)
    nextButton.setIcon(nextIcon)
    nextButton.connect('clicked()', lambda tab=self.liverTab: self.setCurrentTab(tab))

    buttonHBoxLayout = qt.QHBoxLayout()
    buttonHBoxLayout.addWidget(previousButton)
    # buttonHBoxLayout.addStretch(1)
    buttonHBoxLayout.addWidget(nextButton)
    dataTabLayout.addLayout(buttonHBoxLayout)

  def defineLiverTab(self):
    liverTabLayout = qt.QVBoxLayout(self.liverTab)
    segmentationUI = slicer.util.getNewModuleGui(slicer.modules.segmenteditor)
    liverTabLayout.addWidget(segmentationUI)

    # Add Next/Previous arrow
    previousButton = qt.QPushButton()
    previousIcon = qt.QApplication.style().standardIcon(qt.QStyle.SP_ArrowLeft)
    previousButton.setIcon(previousIcon)
    previousButton.connect('clicked()', lambda tab=self.dataTab: self.setCurrentTab(tab))

    nextButton = qt.QPushButton()
    nextIcon = qt.QApplication.style().standardIcon(qt.QStyle.SP_ArrowRight)
    nextButton.setIcon(nextIcon)
    nextButton.connect('clicked()', lambda tab=self.vesselsTab: self.setCurrentTab(tab))

    buttonHBoxLayout = qt.QHBoxLayout()
    buttonHBoxLayout.addWidget(previousButton)
    # buttonHBoxLayout.addStretch(1)
    buttonHBoxLayout.addWidget(nextButton)
    liverTabLayout.addLayout(buttonHBoxLayout)

  def onLoadDMRIClicked(self):
    # Show DICOM Widget #
    modules = slicer.modules
    DICOMWidget = None

    try:
      DICOMWidget = slicer.modules.DICOMWidget
    except:
      DICOMWidget = slicer.modules.dicom.widgetRepresentation().self()

    if DICOMWidget is not None:
      DICOMWidget.detailsPopup.open()

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def onNodeAdded(self, caller, event, calldata):
    if isinstance(calldata, slicer.vtkMRMLVolumeNode):
      layoutNode = slicer.util.getNode('*LayoutNode*')
      layoutNode.SetViewArrangement(layoutNode.SlicerLayoutUserView)
      self.setCurrentNode(calldata)

  def onInputSelectorNodeChanged(self):
    print('onInputSelectorNodeChanged')
    node = self.inputSelector.currentNode()
    # Update current node on volume and volumeRendering modules
    self.setCurrentNode(node)

    # Show volume
    slicer.util.setSliceViewerLayers(node)
    self.showVolumeRendering(node)

  def setCurrentNode(self, node):
    logic = RVesselXModuleLogic()
    logic.setCurrentNode(node)

    self.inputSelector.setCurrentNode(node)

    if self.volumesModuleSelector:
      self.volumesModuleSelector.setCurrentNode(node)

    if self.volumeRenderingModuleSelector:
      self.volumeRenderingModuleSelector.setCurrentNode(node)

  def showVolumeRendering(self, volumeNode):
    print("Show volume rendering of node " + volumeNode.GetName())
    print('Volume Node', volumeNode)
    volRenLogic = slicer.modules.volumerendering.logic()
    displayNode = volRenLogic.CreateDefaultVolumeRenderingNodes(volumeNode)
    displayNode.SetVisibility(True)
    self.reset3DRendererCamera()

  def reset3DRendererCamera(self):
    print('test reset focal point')
    threeDWidget = slicer.app.layoutManager().threeDWidget(0)
    threeDWidget.threeDView().resetFocalPoint()
    threeDWidget.threeDView().renderWindow().GetRenderers().GetFirstRenderer().ResetCamera()

#
# RVesselXModuleLogic
#

class RVesselXModuleLogic(ScriptedLoadableModuleLogic):
  """
  """
  def __init__(self):
    ScriptedLoadableModuleLogic.__init__(self)
    print('LOGIC -- INIT')
    self.currentNode = None

  def setCurrentNode(self, node):
    print('LOGIC -- SET CURRENT NODE')
    self.currentNode = node

  def getCurrentNode(self):
    print('LOGIC -- GET CURRENT NODE')
    return self.currentNode
