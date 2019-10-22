import qt
import slicer

from RVesselXUtils import WidgetUtils, GeometryExporter
from VerticalLayoutWidget import VerticalLayoutWidget


class SegmentWidget(VerticalLayoutWidget):
  """
  Object responsible for segmenting the liver volume as well as tumor volumes and exporting the results as NIFTI.
  Presents direct interface to segmentation tools.
  Can be configured with named segmentation node and prepared segments
  """

  def __init__(self, segmentNodeName, segmentNames=None):
    VerticalLayoutWidget.__init__(self)

    if segmentNames is None:
      segmentNames = []

    self._inputNode = None

    # Get segmentation UI (segmentation UI contains singletons so only one instance can really exist in Slicer)
    self._segmentUi = slicer.util.getModuleGui(slicer.modules.segmenteditor)

    # Extract segmentation Widget from segmentation UI
    self._segmentationWidget = WidgetUtils.getChildContainingName(self._segmentUi, "EditorWidget")

    # Extract show 3d button and surface smoothing from segmentation widget
    # by default liver 3D will be shown and surface smoothing disabled on entering the tab
    self._segmentationShow3dButton = WidgetUtils.getChildContainingName(self._segmentationWidget, "show3d")

    # Extract smoothing button from QMenu attached to show3d button
    self._segmentationSmooth3d = [action for action in self._segmentationShow3dButton.children()[0].actions()  #
                                  if "surface" in action.text.lower()][0]

    # Hide segmentation node and master volume node
    self._segmentationWidget.setMasterVolumeNodeSelectorVisible(False)
    self._segmentationWidget.setSegmentationNodeSelectorVisible(False)

    # Add segmentation volume for the widget
    self._segmentNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
    self._segmentNode.SetName(segmentNodeName)

    # Add as many segments as names in input segmentNames
    for segmentName in segmentNames:
      self._segmentNode.GetSegmentation().AddEmptySegment(segmentName)

    self._verticalLayout.addWidget(self._segmentUi)
    self._layoutList = []

  def setInputNode(self, node):
    """
    Modify input to given input node and update segmentation master volume

    :param node: vtkMRMLNode
    """
    self._inputNode = node
    self._updateSegmentationMasterVolumeNode()

  def _updateSegmentationMasterVolumeNode(self):
    """
    Updates segmentation widget master volume to be the one previously set using setInputNode.
    Update is called multiple times to avoid problems when switching to segmentation widget. (problem may come from
    implementation detail in SegmentationEditor module)
    """
    if self._inputNode:
      # Wrap update in QTimer for better reliability on set event (otherwise set can fail somehow)
      qt.QTimer.singleShot(0, lambda: self._segmentationWidget.setMasterVolumeNode(self._inputNode))

  def getGeometryExporters(self):
    """
    Converts liver segment to label volume and returns the GeometryExporter associated with create volume.
    If the segment was not initialized, nothing is exported

    :return: GeometryExporter containing liver volume or None
    """
    segmentName = self._segmentNode.GetName()

    # Create Label map from visible segments
    labelMapName = segmentName + "VolumeLabel"
    labelMap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", labelMapName)
    slicer.vtkSlicerSegmentationsModuleLogic().ExportVisibleSegmentsToLabelmapNode(self._segmentNode, labelMap)

    # Create volume node from label map
    volumeName = segmentName + "Volume"
    volume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", volumeName)
    slicer.modules.volumes.logic().CreateScalarVolumeFromVolume(slicer.mrmlScene, volume, labelMap)

    # Return geometry exporter with created volumes
    geometryExporter = GeometryExporter()
    geometryExporter[segmentName] = volume
    return [geometryExporter]

  def addLayout(self, layout):
    """
    Override of base addLayout to save all the different layouts added to the widget and their order.
    They will be removed and re added during show events.

    :param layout: QLayout
    """
    self._layoutList.append(layout)
    self._verticalLayout.addLayout(layout)

  def _resetLayout(self):
    """
    Removes all the layouts from the widget and reconstruct them in order.
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
    """
    On show events, reset layout to have proper showing of only instance of segmentation UI.
    Sets the segmentation UI segmentNode linked to current instance of widget and show node 3D

    :param event: QEvent
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

    # Call superclass showEvent
    qt.QWidget.showEvent(self, event)

  def hideEvent(self, event):
    """
    On hide event, hide the segmentNode 3D

    :param event: QEvent
    """
    self._segmentationShow3dButton.setChecked(False)

    # Call superclass hideEvent
    qt.QWidget.hideEvent(self, event)
