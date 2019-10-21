import slicer

from RVesselXUtils import WidgetUtils, GeometryExporter
from VerticalLayoutWidget import VerticalLayoutWidget


class LiverWidget(VerticalLayoutWidget):
  """
  Object responsible for segmenting the liver volume and exporting the segment result as NIFTI volume.
  """

  def __init__(self):
    VerticalLayoutWidget.__init__(self)

    segmentationUi = slicer.util.getNewModuleGui(slicer.modules.segmenteditor)
    self._verticalLayout.addWidget(segmentationUi)

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

  def setInputNode(self, node):
    """
    Modify input to given input node if node is valid

    :param node: vtkMRMLNode
    """
    if self._segmentationWidget and node:
      self._segmentationWidget.setMasterVolumeNode(node)

  def getGeometryExporter(self):
    """
    Converts liver segment to label volume and returns the GeometryExporter associated with create volume.
    If the segment was not initialized, nothing is exported

    :return: GeometryExporter containing liver volume or None
    """
    liverNodes = list(slicer.mrmlScene.GetNodesByName("Liver"))
    liverNode = liverNodes[0] if len(liverNodes) > 0 else None
    liverSegmentIn = liverNode.GetSegmentation().GetSegment("LiverIn") if liverNode else None

    if liverSegmentIn is not None:
      liverVolumeLabel = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "LiverVolumeLabel")
      slicer.vtkSlicerSegmentationsModuleLogic().ExportVisibleSegmentsToLabelmapNode(liverNode, liverVolumeLabel)
      liverVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", "LiverVolume")
      slicer.modules.volumes.logic().CreateScalarVolumeFromVolume(slicer.mrmlScene, liverVolume, liverVolumeLabel)

      return GeometryExporter(Liver=liverVolume)
    else:
      return None

  def enterAction(self):
    """
    Show liver 3D view and deactivate surface smoothing
    """
    self._segmentationShow3dButton.setChecked(True)
    self._segmentationSmooth3d.setChecked(False)

  def exitAction(self):
    """
    Hide liver 3D view
    """
    self._segmentationShow3dButton.setChecked(False)
