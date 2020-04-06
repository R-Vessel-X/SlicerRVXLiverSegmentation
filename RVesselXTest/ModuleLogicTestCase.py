import os
import unittest

import slicer

from RVesselXLib import RVesselXModuleLogic, GeometryExporter
from .TestUtils import TemporaryDir, cropSourceVolume, createNonEmptyVolume, createNonEmptyModel


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
    seedsNodes, stoppersNodes, outVolume, outModel = logic.extractVesselVolumeFromPosition([startPosition],
                                                                                           [endPosition])

    self.assertIsNotNone(outVolume)
    self.assertIsNotNone(outModel)
    self.assertNotEqual(0, outModel.GetPolyData().GetNumberOfCells())

  def testLogicRaisesErrorWhenCalledWithNoneInputs(self):
    logic = RVesselXModuleLogic()

    with self.assertRaises(ValueError):
      logic._applyLevelSetSegmentation(None, None, None, None, None)

    with self.assertRaises(ValueError):
      logic._applyVesselnessFilter(None, None)

    with self.assertRaises(ValueError):
      logic._applyCenterlineFilter(None, None, None)

  def testGeometryExporterSavesVolumesAsNiftiAndModelsAsVtkFiles(self):
    # Create non empty model and volume nodes (empty nodes are not exported)
    model = createNonEmptyModel()
    volume = createNonEmptyVolume()
    markup = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
    markup.AddFiducial(0, 0, 0)

    # Create geometry exporter and add the two nodes to it
    exporter = GeometryExporter()
    exporter["ModelFileName"] = model
    exporter["VolumeFileName"] = volume
    exporter["MarkupFileName"] = markup

    # Create temporary dir to export the data
    with TemporaryDir() as outputDir:
      # Export nodes in the exporter
      exporter.exportToDirectory(outputDir)

      # Expect the nodes have been correctly exported
      expModelPath = os.path.join(outputDir, "ModelFileName.vtk")
      expVolumePath = os.path.join(outputDir, "VolumeFileName.nii")
      expMarkupPath = os.path.join(outputDir, "MarkupFileName.fcsv")
      self.assertTrue(os.path.isfile(expModelPath))
      self.assertTrue(os.path.isfile(expVolumePath))
      self.assertTrue(os.path.isfile(expMarkupPath))

  def testVesselnessFilterIsUpdatedOncePerVolume(self):
    vol1 = createNonEmptyVolume("vol1")
    vol2 = createNonEmptyVolume("vol2")
    logic = RVesselXModuleLogic()
    logic.setInputVolume(vol1)
    self.assertTrue(logic.updateVesselnessVolume())
    self.assertFalse(logic.updateVesselnessVolume())

    logic.setInputVolume(vol2)
    self.assertTrue(logic.updateVesselnessVolume())
    self.assertFalse(logic.updateVesselnessVolume())

  def testVesselnessFilterIsUpdatedOncePerParameter(self):
    vol = createNonEmptyVolume("vol")
    logic = RVesselXModuleLogic()
    logic.setInputVolume(vol)

    self.assertTrue(logic.updateVesselnessVolume())
    self.assertFalse(logic.updateVesselnessVolume())

    p = logic.vesselnessFilterParameters
    p.vesselContrast += 100
    logic.vesselnessFilterParameters = p
    self.assertTrue(logic.updateVesselnessVolume())
    self.assertFalse(logic.updateVesselnessVolume())
