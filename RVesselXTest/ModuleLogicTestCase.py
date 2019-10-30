import os
import unittest

import slicer

from RVesselXLib import RVesselXModuleLogic, GeometryExporter
from RVesselXTest import TemporaryDir, cropSourceVolume, createNonEmptyVolume, createNonEmptyModel


class RVesselXModuleTestCase(unittest.TestCase):
  def setUp(self):
    """ Clear scene before each tests
    """
    slicer.mrmlScene.Clear(0)

  def testVesselSegmentationLogic(self):
    import SampleData
    sampleDataLogic = SampleData.SampleDataLogic()
    sourceVolume = sampleDataLogic.downloadCTACardio()

    # Create start point and end point for the vessel extraction
    startPosition = [176.9, -17.4, 52.7]
    endPosition = [174.704, -23.046, 76.908]

    startPoint = RVesselXModuleLogic._createFiducialNode("startPoint", startPosition)
    endPoint = RVesselXModuleLogic._createFiducialNode("endPoint", endPosition)

    # Crop volume
    roi = slicer.vtkMRMLAnnotationROINode()
    roi.Initialize(slicer.mrmlScene)
    roi.SetName("VolumeCropROI")
    roi.SetXYZ(startPosition[0], startPosition[1], startPosition[2])
    radius = max(abs(a - b) for a, b in zip(startPosition, endPosition)) * 2
    roi.SetRadiusXYZ(radius, radius, radius)

    sourceVolume = cropSourceVolume(sourceVolume, roi)

    # Run vessel extraction and expect non empty values and data
    logic = RVesselXModuleLogic()
    logic.setInputVolume(sourceVolume)
    vessel = logic.extractVessel(startPoint, endPoint)

    self.assertIsNotNone(vessel.segmentedVolume)
    self.assertIsNotNone(vessel.segmentedModel)
    self.assertNotEqual(0, vessel.segmentedModel.GetPolyData().GetNumberOfCells())
    self.assertIsNotNone(vessel.segmentedCenterline)
    self.assertNotEqual(0, vessel.segmentedCenterline.GetPolyData().GetNumberOfCells())

  def testLogicRaisesErrorWhenCalledWithNoneInputs(self):
    logic = RVesselXModuleLogic()

    with self.assertRaises(ValueError):
      logic._applyLevelSetSegmentation(None, None, None, None)

    with self.assertRaises(ValueError):
      logic._applyVesselnessFilter(None, None)

    with self.assertRaises(ValueError):
      logic._applyCenterlineFilter(None, None, None)

  def testGeometryExporterSavesVolumesAsNiftiAndModelsAsVtkFiles(self):
    # Create non empty model and volume nodes (empty nodes are not exported)
    model = createNonEmptyModel()
    volume = createNonEmptyVolume()

    # Create geometry exporter and add the two nodes to it
    exporter = GeometryExporter()
    exporter["ModelFileName"] = model
    exporter["VolumeFileName"] = volume

    # Create temporary dir to export the data
    with TemporaryDir() as outputDir:
      # Export nodes in the exporter
      exporter.exportToDirectory(outputDir)

      # Expect the nodes have been correctly exported
      expModelPath = os.path.join(outputDir, "ModelFileName.vtk")
      expVolumePath = os.path.join(outputDir, "VolumeFileName.nii")
      self.assertTrue(os.path.isfile(expModelPath))
      self.assertTrue(os.path.isfile(expVolumePath))
