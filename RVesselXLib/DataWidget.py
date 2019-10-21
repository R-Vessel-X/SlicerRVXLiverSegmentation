import qt
import slicer

from RVesselXUtils import createInputNodeSelector, addInCollapsibleLayout, WidgetUtils
from VerticalLayoutWidget import VerticalLayoutWidget


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

    VerticalLayoutWidget.__init__(self)

    # Add load MRI button #
    inputLayout = qt.QHBoxLayout()

    inputLabel = qt.QLabel("Volume: ")
    inputLayout.addWidget(inputLabel)

    # Wrap input selector changed method in a timer call so that the volume can be correctly set first
    def inputChangedCallback(node):
      qt.QTimer.singleShot(0, lambda: self.onInputSelectorNodeChanged(node))

    self.inputSelector = createInputNodeSelector("vtkMRMLScalarVolumeNode", toolTip="Pick the input.",
                                                 callBack=inputChangedCallback)

    inputLayout.addWidget(self.inputSelector)

    loadDicomButton = qt.QPushButton("Load DICOM")
    loadDicomButton.connect("clicked(bool)", self.onLoadDICOMClicked)
    inputLayout.addWidget(loadDicomButton)

    loadDataButton = qt.QPushButton("Load Data")
    loadDataButton.connect("clicked(bool)", self.onLoadDataClicked)
    inputLayout.addWidget(loadDataButton)

    self._verticalLayout.addLayout(inputLayout)

    # Add Volume information
    volumesWidget = slicer.util.getNewModuleGui(slicer.modules.volumes)
    addInCollapsibleLayout(volumesWidget, self._verticalLayout, "Volume")

    # Hide Volumes Selector and its label
    WidgetUtils.hideChildrenContainingName(volumesWidget, "activeVolume")
    self.volumesModuleSelector = WidgetUtils.getChildContainingName(volumesWidget, "ActiveVolumeNodeSelector")

    # Add Volume Rendering information
    volumeRenderingWidget = slicer.util.getNewModuleGui(slicer.modules.volumerendering)
    addInCollapsibleLayout(volumeRenderingWidget, self._verticalLayout, "Volume Rendering")

    # Hide Volume Rendering Selector and its label
    self.volumeRenderingModuleVisibility = WidgetUtils.hideChildContainingName(volumeRenderingWidget,
                                                                               "VisibilityCheckBox")
    self.volumeRenderingModuleSelector = WidgetUtils.hideChildContainingName(volumeRenderingWidget,
                                                                             "VolumeNodeComboBox")

    # Add stretch
    self._verticalLayout.addStretch(1)

    # Connect volume changed callback
    self._inputNodeChangedCallbacks = [self.setVolumeNode]

  def addInputNodeChangedCallback(self, callback):
    """
    Adds new callback to list of callbacks triggered when data tab input node is changed. When the node is changed to a
    valid value, the callback will be called.

    :param callback: Callable[[vtkMRMLNode], None] function to call with new input node when changed
    """
    self._inputNodeChangedCallbacks.append(callback)

  def onInputSelectorNodeChanged(self, node):
    """
    On input changed and with a valid input node, notifies all callbacks of new node value

    :param node: vtkMRMLNode
    """
    if node is not None:
      for callback in self._inputNodeChangedCallbacks:
        callback(node)

  def onLoadDICOMClicked(self):
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

  def setVolumeNode(self, node):
    """
    Set input selector and volume rendering nodes as input node.
    Show the new input node in 3D rendering.

    :param node: vtkMRMLVolumeNode
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

  def getInputNode(self):
    """
    :return: Current vtkMRMLVolumeNode selected by user in the DataWidget
    """
    return self.inputSelector.currentNode()
