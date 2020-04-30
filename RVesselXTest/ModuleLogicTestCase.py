import os
import unittest

import slicer

from RVesselXLib import RVesselXModuleLogic, GeometryExporter, cropSourceVolume
from .TestUtils import TemporaryDir, createNonEmptyVolume, createNonEmptyModel
import numpy as np


def prepareEndToEndTest():
  import SampleData
  sampleDataLogic = SampleData.SampleDataLogic()
  sourceVolume = sampleDataLogic.downloadCTACardio()

  # Create start point and end point for the vessel extraction
  startPosition = [176.9, -17.4, 52.7]
  endPosition = [174.704, -23.046, 76.908]

  return sourceVolume, startPosition, endPosition


class RVesselXModuleTestCase(unittest.TestCase):
  def setUp(self):
    """ Clear scene before each tests
    """
    slicer.mrmlScene.Clear(0)

  def testVesselSegmentationLogic(self):
    # Prepare source volume, start position and end position
    sourceVolume, startPosition, endPosition = prepareEndToEndTest()

    # Run vessel extraction and expect non empty values and data
    logic = RVesselXModuleLogic()
    logic.setInputVolume(sourceVolume)
    logic.updateVesselnessVolume([startPosition, endPosition])
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
      logic.centerLineFilter(None, None, None)

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

  def testGivenNoMinExtentRoiExtentReachesExtremeNodePositions(self):
    node_positions = [[1, 0, 0], [1, 0, 0], [1, 0, 0], [40, 0, 0], [-1, 0, 0]]

    roi_center, roi_radius = RVesselXModuleLogic.calculateRoiExtent(node_positions, minExtent=0, growthFactor=1)
    np.testing.assert_array_almost_equal([19.5, 0, 0], roi_center)
    np.testing.assert_array_almost_equal([20.5, 0, 0], roi_radius)

  def testGivenNoMinExtentAndGrowthFactorRadiusIsMultipliedByGrowthFactor(self):
    node_positions = [[1, 0, 0], [1, 0, 0], [1, 0, 0], [40, 0, 0], [-1, 0, 0]]

    _, roi_radius_x1 = RVesselXModuleLogic.calculateRoiExtent(node_positions, minExtent=0, growthFactor=1)
    _, roi_radius_x2 = RVesselXModuleLogic.calculateRoiExtent(node_positions, minExtent=0, growthFactor=2)

    np.testing.assert_array_almost_equal(roi_radius_x1 * 2, roi_radius_x2)

  def testGivenMinExtentROIRadiusIsAdjusted(self):
    node_positions = [[0, 1, 0], [40, 0, 0], [-1, 0, 0]]
    roi_center, roi_radius = RVesselXModuleLogic.calculateRoiExtent(node_positions, minExtent=10, growthFactor=1)
    np.testing.assert_array_almost_equal([19.5, 0.5, 0], roi_center)
    np.testing.assert_array_almost_equal([20.5, 5, 5], roi_radius)

  def testGivenMinExtentWithGrowthFactorROIRadiusIsAdjustedForMinSizeOnly(self):
    node_positions = [[0, 1, 0], [40, 0, 0], [-1, 0, 0]]
    roi_center, roi_radius = RVesselXModuleLogic.calculateRoiExtent(node_positions, minExtent=10, growthFactor=2)
    np.testing.assert_array_almost_equal([19.5, 0.5, 0], roi_center)
    np.testing.assert_array_almost_equal([41., 5, 5], roi_radius)

  def testGivenNegativeNodePositionsROICenterIsCorrect(self):
    node_positions = [[-46, -24, -28], [-45, -22, -54]]

    roi_center, roi_radius = RVesselXModuleLogic.calculateRoiExtent(node_positions, minExtent=0, growthFactor=1)
    np.testing.assert_array_almost_equal([-45.5, -23, -41], roi_center)
    np.testing.assert_array_almost_equal([0.5, 1., 13.], roi_radius)
