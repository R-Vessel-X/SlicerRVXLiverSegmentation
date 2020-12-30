import ctk
import qt
import slicer
import vtk

from .RVesselXUtils import createInputNodeSelector, addInCollapsibleLayout, WidgetUtils, createButton, createDisplayNodeIfNecessary
from .VerticalLayoutWidget import VerticalLayoutWidget


def wrapInQTimer(func):
  def inner(*args, **kwargs):
    qt.QTimer.singleShot(0, lambda *x: func(*args, **kwargs))

  return inner


class DataWidget(VerticalLayoutWidget):
  """
  Object responsible for loading and showing the input volume to the user.
  Provides buttons to load DICOM and other data.
  Enables listeners to be notified when the input volume has been changed by the user.
  """

  def __init__(self):
    """
    Configure DataTab with load DICOM and Load Data buttons, Input volume selection, Volume 2D and 3D rendering
    """

    VerticalLayoutWidget.__init__(self, "Data Tab")

    # Create input layout
    inputLayout = qt.QHBoxLayout()
    inputLabel = qt.QLabel("Volume: ")
    inputLayout.addWidget(inputLabel)

    # Create input volume selector and connect callback to selection changed signal
    self._volumeDisplayNode = None
    self._sceneObserver = None
    self._newNodeObserver = None
    self.inputSelector = createInputNodeSelector("vtkMRMLScalarVolumeNode", toolTip="Pick the input.",
                                                 callBack=self.onInputSelectorNodeChanged)

    # Add load DICOM and load DATA button to the layout
    inputLayout.addWidget(self.inputSelector)
    inputLayout.addWidget(createButton("Load DICOM", lambda *x: self.onLoadDICOMClicked()))
    inputLayout.addWidget(createButton("Load Data", lambda *x: self.onLoadDataClicked()))
    self._verticalLayout.addLayout(inputLayout)

    # Add Volume information
    volumesWidget = slicer.util.getNewModuleGui(slicer.modules.volumes)
    addInCollapsibleLayout(volumesWidget, self._verticalLayout, "Volume")

    # Hide Volumes Selector and its label
    WidgetUtils.hideChildrenContainingName(volumesWidget, "activeVolume")
    self.volumesModuleSelector = WidgetUtils.getFirstChildContainingName(volumesWidget, "ActiveVolumeNodeSelector")

    # Add Volume Rendering information
    self.volumeRenderingWidget = slicer.util.getNewModuleGui(slicer.modules.volumerendering)
    addInCollapsibleLayout(self.volumeRenderingWidget, self._verticalLayout, "Volume Rendering")

    # Hide Volume Rendering Selector and its label
    self.volumeRenderingModuleVisibility = WidgetUtils.hideFirstChildContainingName(self.volumeRenderingWidget,
                                                                                    "VisibilityCheckBox")
    self.volumeRenderingModuleSelector = WidgetUtils.hideFirstChildContainingName(self.volumeRenderingWidget,
                                                                                  "VolumeNodeComboBox")

    # Add stretch
    self._verticalLayout.addStretch(1)

    # Connect volume changed callback
    self._inputNodeChangedCallbacks = [self.setVolumeNode]
    self._previousNode = None

    # Connect node added to node selection when widget is Visible
    # Enables switching to new loaded node automatically
    self._addNewNodeObserver()

  def _addNewNodeObserver(self):
    if self._newNodeObserver is not None:
      self._removeNewNodeObserver()

    self._newNodeObserver = slicer.mrmlScene.AddObserver(slicer.vtkMRMLScene.NodeAddedEvent,
                                                         self._selectNewNodeAsInputNode)

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def _selectNewNodeAsInputNode(self, caller, event, newNode):
    if isinstance(newNode, slicer.vtkMRMLVolumeNode) and self.visible:
      self.inputSelector.setCurrentNode(newNode)

  @wrapInQTimer
  def _synchronizeVolumeRendering(self):
    synchronizeButton = [b for b in self.volumeRenderingWidget.findChildren(ctk.ctkCheckablePushButton) if
                         b.name == "SynchronizeScalarDisplayNodeButton"]
    synchronizeButton = synchronizeButton[0] if synchronizeButton else None
    if synchronizeButton is not None:
      synchronizeButton.clicked.emit(True)
      synchronizeButton.checkBoxToggled.emit(True)
      synchronizeButton.toggled.emit(True)

  def addInputNodeChangedCallback(self, callback):
    """Adds new callback to list of callbacks triggered when data tab input node is changed. When the node is changed to
    a valid value, the callback will be called.

    Parameters
    ----------
    callback: Callable[[vtkMRMLNode], None] function to call with new input node when changed
    """
    self._inputNodeChangedCallbacks.append(callback)

  @wrapInQTimer
  def onInputSelectorNodeChanged(self, node):
    """On input changed and with a valid input node, notifies all callbacks of new node value

    Parameters
    ----------
    node: vtkMRMLNode
    """
    # Early return if invalid node
    if not node or node == self._previousNode:
      return

    self._previousNode = node
    self._removePreviousNodeAddedObserverFromScene()

    # If node not yet properly initialized, attach observer to image change.
    # Else notify image changed and save node as new input volume
    if node.GetImageData() is None:
      self._attachNodeAddedObserverToScene(node)
    else:
      self._notifyInputChanged(node)

      # Volume rendering synchronisation needs to be called in QTimer for signals to be correctly processed by Slicer
      self._synchronizeVolumeRendering()

  def _removePreviousNodeAddedObserverFromScene(self):
    if self._sceneObserver is not None:
      slicer.mrmlScene.RemoveObserver(self._sceneObserver)
      self._sceneObserver = None

  def _removeNewNodeObserver(self):
    if self._newNodeObserver is not None:
      slicer.mrmlScene.RemoveObserver(self._newNodeObserver)
      self._newNodeObserver = None

  def _attachNodeAddedObserverToScene(self, node):
    self._sceneObserver = slicer.mrmlScene.AddObserver(slicer.vtkMRMLScene.NodeAddedEvent,
                                                       lambda *x: self.onInputSelectorNodeChanged(node))

  @wrapInQTimer
  def _notifyInputChanged(self, node):
    for callback in self._inputNodeChangedCallbacks:
      callback(node)

  @wrapInQTimer
  def onLoadDICOMClicked(self):
    """Show DICOM Widget as popup
    """
    try:
      dicomWidget = slicer.modules.DICOMWidget
    except AttributeError:
      dicomWidget = slicer.modules.dicom.widgetRepresentation().self()

    if dicomWidget is not None:
      dicomWidget.detailsPopup.open()

  def onLoadDataClicked(self):
    slicer.app.ioManager().openAddDataDialog()

  @wrapInQTimer
  def setVolumeNode(self, node):
    """
    Set input selector and volume rendering nodes as input node.
    Show the new input node in 3D rendering.

    Parameters
    ----------
    node: vtkMRMLVolumeNode
    """
    # Change node in input selector and volume rendering widgets
    self.inputSelector.setCurrentNode(node)

    if self.volumesModuleSelector:
      self.volumesModuleSelector.setCurrentNode(node)

    if self.volumeRenderingModuleSelector:
      self.volumeRenderingModuleSelector.setCurrentNode(node)

    # Show node in 2D view
    slicer.util.setSliceViewerLayers(node)

    # Show node in 3D view
    self.showVolumeRendering(node)

  @wrapInQTimer
  def showVolumeRendering(self, volumeNode):
    """Show input volumeNode in 3D View

    Parameters
    ----------
    volumeNode: vtkMRMLVolumeNode
    """
    # Early return if invalid volume node
    if volumeNode is None:
      return

    # hide previous node if necessary
    if self._volumeDisplayNode:
      self._volumeDisplayNode.SetVisibility(False)

    # Create new display node for input volume
    self._volumeDisplayNode = createDisplayNodeIfNecessary(volumeNode, 'MR-Default')
    self._volumeDisplayNode.SetFollowVolumeDisplayNode(True)

    slicer.util.resetThreeDViews()
    slicer.util.resetSliceViews()

  def getInputNode(self):
    """
    Returns
    -------
    vtkMRMLVolumeNode
      Current vtkMRMLVolumeNode selected by user in the DataWidget
    """
    return self.inputSelector.currentNode()

  def setTestingMode(self, isTesting):
    self._removeNewNodeObserver()
    self._removePreviousNodeAddedObserverFromScene()
    if not isTesting:
      self._addNewNodeObserver()
