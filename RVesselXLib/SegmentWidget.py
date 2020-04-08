import qt
import slicer

from .RVesselXUtils import WidgetUtils, GeometryExporter, removeNodeFromScene
from .VerticalLayoutWidget import VerticalLayoutWidget


class SegmentWidget(VerticalLayoutWidget):
  """Object responsible for segmenting the liver volume as well as tumor volumes and exporting the results as NIFTI.
  Presents direct interface to segmentation tools.
  Can be configured with named segmentation node and prepared segments
  """

  def __init__(self, segmentWidgetName, segmentNodeName, segmentNames=None):
    VerticalLayoutWidget.__init__(self, segmentWidgetName)

    if segmentNames is None:
      segmentNames = []

    self._inputNode = None
    self._labelMap = None
    self._scalarVolume = None

    # Get segmentation UI (segmentation UI contains singletons so only one instance can really exist in Slicer)
    self._segmentUi = slicer.util.getModuleGui(slicer.modules.segmenteditor)

    # Extract segmentation Widget from segmentation UI
    self._segmentationWidget = WidgetUtils.getFirstChildContainingName(self._segmentUi, "EditorWidget")

    # Extract show 3d button and surface smoothing from segmentation widget
    # by default liver 3D will be shown and surface smoothing disabled on entering the tab
    self._segmentationShow3dButton = WidgetUtils.getFirstChildContainingName(self._segmentationWidget, "show3d")

    # Extract smoothing button from QMenu attached to show3d button
    self._segmentationSmooth3d = [action for action in self._segmentationShow3dButton.children()[0].actions()  #
                                  if "surface" in action.text.lower()][0]

    # Hide segmentation node and master volume node
    self._setNodeSelectorVisible(False)

    self._verticalLayout.addWidget(self._segmentUi)
    self._layoutList = []

    # Add segmentation volume for the widget
    self._segmentNodeName = segmentNodeName
    self._segmentNames = segmentNames
    self._setupSegmentNode()

  def clear(self):
    removeNodeFromScene(self._segmentNode)
    removeNodeFromScene(self._labelMap)
    removeNodeFromScene(self._scalarVolume)
    self._setupSegmentNode()

  def _setupSegmentNode(self):
    # Add segmentation volume for the widget
    self._segmentNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
    self._segmentNode.SetName(self._segmentNodeName)

    # Add as many segments as names in input segmentNames
    self._addSegmentationNodes(self._segmentNames)

  def _addSegmentationNodes(self, segmentNames):
    for segmentName in segmentNames:
      self._segmentNode.GetSegmentation().AddEmptySegment(segmentName)

  def _setNodeSelectorVisible(self, isVisible):
    """Changes visibility for master volume selector and segmentation node selector. Both selectors need to be hidden
    when integrated in the RVesselX plugin but shown otherwise.
    """
    self._segmentationWidget.setMasterVolumeNodeSelectorVisible(isVisible)
    self._segmentationWidget.setSegmentationNodeSelectorVisible(isVisible)

  def setInputNode(self, node):
    """Modify input to given input node and update segmentation master volume

    Parameters
    ----------
    node: vtkMRMLNode
    """
    self._inputNode = node
    self._updateSegmentationMasterVolumeNode()

  def _updateSegmentationMasterVolumeNode(self):
    """Updates segmentation widget master volume to be the one previously set using setInputNode.
    Update is called multiple times to avoid problems when switching to segmentation widget. (problem may come from
    implementation detail in SegmentationEditor module)
    """
    if self._inputNode:
      # Wrap update in QTimer for better reliability on set event (otherwise set can fail somehow)
      qt.QTimer.singleShot(0, lambda: self._segmentationWidget.setMasterVolumeNode(self._inputNode))

  def getGeometryExporters(self):
    """Converts liver segment to label volume and returns the GeometryExporter associated with create volume.
    If the segment was not initialized, nothing is exported

    Returns
    -------
      GeometryExporter containing liver volume or None
    """
    segmentName = self._segmentNode.GetName()

    # Create Label map from visible segments
    labelMap = self._createLabelMapVolumeNode()

    # Create volume node from label map
    volume = self._createScalarVolumeNode(labelMap)

    # Return geometry exporter with created volumes
    geometryExporter = GeometryExporter()
    geometryExporter[segmentName] = volume
    return [geometryExporter]

  def _createScalarVolumeNode(self, labelMap):
    removeNodeFromScene(self._scalarVolume)
    volumeName = self._segmentNode.GetName() + "Volume"
    self._scalarVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", volumeName)
    slicer.modules.volumes.logic().CreateScalarVolumeFromVolume(slicer.mrmlScene, self._scalarVolume, labelMap)

    return self._scalarVolume

  def _createLabelMapVolumeNode(self):
    removeNodeFromScene(self._labelMap)

    segmentName = self._segmentNode.GetName()
    labelMapName = segmentName + "VolumeLabel"

    self._labelMap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", labelMapName)
    slicer.vtkSlicerSegmentationsModuleLogic().ExportVisibleSegmentsToLabelmapNode(self._segmentNode, self._labelMap)
    return self._labelMap

  def addLayout(self, layout):
    """Override of base addLayout to save all the different layouts added to the widget and their order.
    They will be removed and re added during show events.

    Parameters
    ----------
    layout: QLayout
    """
    self._layoutList.append(layout)
    self._verticalLayout.addLayout(layout)

  def _resetLayout(self):
    """Removes all the layouts from the widget and reconstruct them in order.
    Done in order to have proper showing of only instance of segmentation UI.
    This method is called during show events of the Widget.
    """
    # Clear layout
    self._verticalLayout.removeWidget(self._segmentUi)
    for layout in self._layoutList:
      self._verticalLayout.removeItem(layout)

    # Set layout
    self._verticalLayout.addWidget(self._segmentUi)
    for layout in self._layoutList:
      self._verticalLayout.addLayout(layout)
    self._segmentUi.show()

  def showEvent(self, event):
    """On show events, reset layout to have proper showing of only instance of segmentation UI.
    Sets the segmentation UI segmentNode linked to current instance of widget and show node 3D.
    Also hides the node selection as the selection node should be set to instantiated segment node only.

    Parameters
    ----------
    event: QEvent
    """
    # Reset layout
    self._resetLayout()

    # Update input node in case it was not properly updated yet
    self._updateSegmentationMasterVolumeNode()

    # Make sure we are set to our segment node and not another instances
    self._segmentationWidget.setSegmentationNode(self._segmentNode)

    # Activate 3D and deactivate smoothing
    self._segmentationShow3dButton.setChecked(True)
    self._segmentationSmooth3d.setChecked(False)

    # Hide node selectors
    self._setNodeSelectorVisible(False)

    # Show segment node
    self._segmentNode.SetDisplayVisibility(True)

    # Call superclass showEvent
    super(SegmentWidget, self).showEvent(event)

  def hideEvent(self, event):
    """On hide event, hide the segmentNode 3D.
    Also shows the node selection as the widget instance is shared for all of slicer app. User may need to access
    segmentation widget for other purposes.

    Parameters
    ----------
    event: QEvent
    """
    self._segmentationShow3dButton.setChecked(False)

    # Show node selectors
    self._setNodeSelectorVisible(True)

    # Hide segment node
    self._segmentNode.SetDisplayVisibility(False)

    # Call superclass hideEvent
    super(SegmentWidget, self).hideEvent(event)
