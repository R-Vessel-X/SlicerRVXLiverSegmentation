import slicer

from RVesselXLib import SegmentWidget


class VesselSegmentEditWidget(SegmentWidget):
  """
  Class responsible for editing the vessel automatic segmentation
  """

  def __init__(self):
    super(VesselSegmentEditWidget, self).__init__("Vessel Segmentation Edit Tab", "VesselTree")
    self._vesselSegmentName = "VesselTree"
    self._segmentationObj = self._segmentNode.GetSegmentation()

  def onVesselSegmentationChanged(self, vesselLabelMap, vesselNodeList):
    self._removeAllSegmentationNodes()
    self._importLabelMap(vesselLabelMap)
    self._addSegmentationNodes(vesselNodeList)

  def _removeAllSegmentationNodes(self):
    for i in range(self._segmentationObj.GetNumberOfSegments()):
      self._segmentationObj.RemoveSegment(self._segmentationObj.GetNthSegment(i).GetName())

  def _importLabelMap(self, vesselLabelMap):
    segmentation_logic = slicer.modules.segmentations.logic()
    segmentation_logic.ImportLabelmapToSegmentationNode(vesselLabelMap, self._segmentNode)

    # Rename imported segment
    self._segmentationObj.GetNthSegment(0).SetName(self._vesselSegmentName)
