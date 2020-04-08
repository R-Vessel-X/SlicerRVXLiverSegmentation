import slicer
import qt
import vtk

from RVesselXLib import SegmentWidget, createButton, GeometryExporter, NodeBranches


class VesselSegmentEditWidget(SegmentWidget):
  """
  Class responsible for editing the vessel automatic segmentation
  """

  def __init__(self, logic, treeWizard):
    super(VesselSegmentEditWidget, self).__init__("Vessel Segmentation Edit Tab", "VesselTree")
    self._vesselSegmentName = "VesselTree"
    self._segmentationObj = self._segmentNode.GetSegmentation()
    self._vesselBranches = NodeBranches()
    self._logic = logic
    self._centerLineVolume = None
    self._setupProceedWithVesselSplittingLayout()
    self._segmentationLogic = slicer.modules.segmentations.logic()
    self._proceedButton.setEnabled(False)
    self._treeWizard = treeWizard

  def getCenterLineVolume(self):
    return self._centerLineVolume

  def _setupProceedWithVesselSplittingLayout(self):
    self._proceedButton = createButton("Proceed to vessel splitting", self.proceedToVesselSplitting)
    layout = qt.QHBoxLayout()
    layout.addWidget(self._proceedButton)
    self.insertLayout(0, layout)

  def proceedToVesselSplitting(self):
    self._removePreviousCenterLineVolume()
    self._extractCenterLine()
    self._addSegmentationNodes(self._vesselBranches.names())
    self._proceedButton.setEnabled(False)

  def _extractCenterLine(self):
    branchVolume = self._getSegmentClosedModel(self._vesselSegmentName)
    if self._hasInvalidVolume(branchVolume):
      return

    startPoints, endPoints = self._vesselBranches.startPoints(), self._vesselBranches.endPoints()
    self._centerLineVolume = self._logic.centerLineFilterFromNodePositions(branchVolume, startPoints, endPoints)
    self._centerLineVolume.SetName(self._vesselSegmentName + "CenterLine")

  def _getSegmentClosedModel(self, segmentName):
    modelName = "{}Model".format(segmentName)
    self._removeNode(modelName)

    polyData = vtk.vtkPolyData()
    segmentId = self._segmentationObj.GetNthSegmentID(0)
    self._segmentationLogic.GetSegmentClosedSurfaceRepresentation(self._segmentNode, segmentId, polyData)

    model = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
    model.SetAndObservePolyData(polyData)
    model.SetName(modelName)
    return model

  def _hasInvalidVolume(self, volume):
    return volume.GetPolyData().GetNumberOfPolys() == 0

  def _removePreviousCenterLineVolume(self):
    self._removeNode(self._centerLineVolume)

  def onVesselSegmentationChanged(self, vesselLabelMap, vesselBranches):
    self._removeAllSegmentationNodes()
    self._importLabelMap(vesselLabelMap)
    self._vesselBranches = vesselBranches
    self._proceedButton.setEnabled(True)

  def _removeAllSegmentationNodes(self):
    for i in range(self._segmentationObj.GetNumberOfSegments()):
      self._segmentationObj.RemoveSegment(self._segmentationObj.GetNthSegment(i).GetName())

  def _importLabelMap(self, vesselLabelMap):
    self._segmentationLogic.ImportLabelmapToSegmentationNode(vesselLabelMap, self._segmentNode)

    # Rename imported segment
    self._segmentationObj.GetNthSegment(0).SetName(self._vesselSegmentName)

  def getGeometryExporters(self):
    exporters = super(VesselSegmentEditWidget, self).getGeometryExporters()
    if self._centerLineVolume is not None:
      exporters.append(GeometryExporter(**{self._centerLineVolume.GetName(): self._centerLineVolume}))
      return exporters

  def setVisibleInScene(self, isVisible):
    """If isVisible, markups and tree will be shown in scene, else they will be hidden
    """
    for i in range(self._treeNodes.GetNumberOfFiducials()):
      isNodeVisible = isVisible and self._branchTree.isInTree(self._markupNode.GetNthFiducialLabel(i))
      self._treeNodes.SetNthFiducialVisibility(i, isNodeVisible)

  def hideEvent(self, event):
    self._treeWizard.setVisibleInScene(False)
    super(VesselSegmentEditWidget, self).hideEvent(event)

  def showEvent(self, event):
    self._treeWizard.setVisibleInScene(True)
    super(VesselSegmentEditWidget, self).showEvent(event)
