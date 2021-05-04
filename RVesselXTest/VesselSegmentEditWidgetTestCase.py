import unittest

import qt
import slicer

from RVesselXLib import RVesselXModuleLogic, VesselSegmentEditWidget, NodeBranches
from .ModuleLogicTestCase import prepareEndToEndTest


class FakeTreeWizard(object):
  def setVisibleInScene(self, isVisible):
    """Necessary interface in the tests"""
    pass


class VesselSegmentEditWidgetTestCase(unittest.TestCase):
  def setUp(self):
    """ Clear scene before each tests
    """
    slicer.mrmlScene.Clear(0)
    self.logic = RVesselXModuleLogic()
    self.vesselEdit = VesselSegmentEditWidget(logic=self.logic, treeWizard=FakeTreeWizard(), widgetName="")

  def testExportWhenNoSegmentationDoneDoesntRaise(self):
    tmpDir = qt.QTemporaryDir()
    exporters = self.vesselEdit.getGeometryExporters()
    for exporter in exporters:
      exporter.exportToDirectory(tmpDir.path())

  def testVesselSegmentEditExtractsOneCenterlineFromInputBranch(self):
    # Prepare source volume, start position and end position
    sourceVolume, startPosition, endPosition = prepareEndToEndTest()

    # Run vessel extraction
    self.logic.setInputVolume(sourceVolume)
    self.logic.updateVesselnessVolume([startPosition, endPosition])
    seedsNodes, stoppersNodes, outVolume, outModel = self.logic.extractVesselVolumeFromPosition([startPosition],
                                                                                                [endPosition])

    # Call vessel edit with output segmentation and node
    vesselBranches = NodeBranches()
    vesselBranches.addBranch("vessel name")
    vesselBranches.addStartPoint(startPosition)
    vesselBranches.addEndPoint(endPosition)
    self.assertEqual(1, len(vesselBranches.names()))
    self.assertEqual(1, len(vesselBranches.startPoints()))
    self.assertEqual(1, len(vesselBranches.endPoints()))

    self.vesselEdit.onVesselSegmentationChanged(outVolume, vesselBranches)

    # Compute center lines and verify no throw
    self.vesselEdit.proceedToVesselSplitting()

    # Verify centerline volume was extracted
    self.assertIsNotNone(self.vesselEdit.getCenterLineVolume())
