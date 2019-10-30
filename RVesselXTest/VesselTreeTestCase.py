import unittest

import slicer

from RVesselXLib import VesselTree, Vessel
from RVesselXTest import createVesselWithArbitraryData, createNonEmptyModel, createNonEmptyVolume, FakeLogic


class VesselTreeTestCase(unittest.TestCase):
  def setUp(self):
    """ Clear scene before each tests
    """
    slicer.mrmlScene.Clear(0)

  def testVesselsReturnGeometryExporterContainingCenterlineAndVolume(self):
    vesselName = "AVesselName"
    vessel = createVesselWithArbitraryData(vesselName)

    expCenterline = createNonEmptyModel()
    expVolume = createNonEmptyVolume()

    self.assertNotEqual(vessel.segmentedCenterline, expCenterline)
    self.assertNotEqual(vessel.segmentedCenterline, expVolume)
    vessel.setCenterline(expCenterline, vessel.segmentedVoronoiModel)
    vessel.setSegmentation(vessel.segmentationSeeds, expVolume, vessel.segmentedModel)

    exporter = vessel.getGeometryExporter()
    self.assertEqual(expCenterline, exporter[vesselName + "CenterLine"])
    self.assertEqual(expVolume, exporter[vesselName])

  def testAfterEditingIsFinishedItemHasVesselStartAndEndPointNodes(self):
    # Create vessel
    vesselName = "AVesselName"
    vessel = createVesselWithArbitraryData(vesselName)
    vessel.startPoint.SetName("Start")
    vessel.endPoint.SetName("End")

    # Populate vessel in tree (will trigger edit stop)
    tree = VesselTree(FakeLogic())
    item = tree.addVessel(vessel)

    # Verify start and end are correctly set to vessel values
    self.assertEqual(vessel.startPoint, item.startPoint)
    self.assertEqual(vessel.endPoint, item.endPoint)

  def testAfterStopEditIfFirstEditOrderVesselInTree(self):
    # Create vessels
    vesselParent = createVesselWithArbitraryData("parent")
    vesselChild = createVesselWithArbitraryData("child")
    vesselChild.startPoint = vesselParent.endPoint

    # Create tree and add vessels to the tree
    logic = FakeLogic()
    tree = VesselTree(logic)

    # Add parent
    logic.setReturnedVessel(vesselParent)
    treeItemParent = tree.addNewVessel()
    tree.stopEditMode(treeItemParent)

    # Add child
    logic.setReturnedVessel(vesselChild)
    treeItemChild = tree.addNewVessel()
    tree.stopEditMode(treeItemChild)

    # Assert child parent has been set to parent vessel
    self.assertEqual(treeItemParent, treeItemChild.parent())

  def testAfterEditingVesselRemoveOldOneFromScene(self):
    class FakeVessel(Vessel):
      def __init__(self):
        Vessel.__init__(self)
        self.wasRemovedFromScene = False

      @staticmethod
      def copyFrom(other):
        fake = FakeVessel()
        for key in other.__dict__.keys():
          setattr(fake, key, getattr(other, key))
        return fake

      def removeFromScene(self):
        self.wasRemovedFromScene = True

    oldVessel = FakeVessel.copyFrom(createVesselWithArbitraryData())
    tree = VesselTree(FakeLogic())
    item = tree.addVessel(oldVessel)

    tree.stopEditMode(item)
    self.assertTrue(oldVessel.wasRemovedFromScene)

  def testVesselCreationNameIsInSegmentationName(self):
    v = createVesselWithArbitraryData()
    self.assertIn(v.name, v.segmentedVolume.GetName())
    self.assertIn(v.name, v.segmentedModel.GetName())
    self.assertIn(v.name, v.segmentedCenterline.GetName())

  def testOnRenameRenamesSegmentationName(self):
    v = createVesselWithArbitraryData()
    newName = "New Name"
    v.name = newName
    self.assertEqual(newName, v.name)
    self.assertIn(v.name, v.segmentedVolume.GetName())
    self.assertIn(v.name, v.segmentedModel.GetName())
    self.assertIn(v.name, v.segmentedCenterline.GetName())

  def testOnDeleteVesselRemovesAllAssociatedModelsFromSceneExceptStartAndEndPoints(self):
    # Create a vessel
    vessel = createVesselWithArbitraryData()

    # Add vessel to tree widget
    tree = VesselTree(FakeLogic())
    treeItem = tree.addVessel(vessel)

    # Remove vessel from scene using the delete button trigger
    tree.triggerVesselButton(treeItem, VesselTree.ColumnIndex.delete)

    # Assert the different models are no longer in the scene
    self.assertFalse(slicer.mrmlScene.IsNodePresent(vessel.vesselnessVolume))
    self.assertFalse(slicer.mrmlScene.IsNodePresent(vessel.segmentationSeeds))
    self.assertFalse(slicer.mrmlScene.IsNodePresent(vessel.segmentedVolume))
    self.assertFalse(slicer.mrmlScene.IsNodePresent(vessel.segmentedModel))
    self.assertFalse(slicer.mrmlScene.IsNodePresent(vessel.segmentedCenterline))
    self.assertFalse(slicer.mrmlScene.IsNodePresent(vessel.segmentedVoronoiModel))

    # Assert start and end points are still kept in the scene even after delete
    self.assertTrue(slicer.mrmlScene.IsNodePresent(vessel.startPoint))
    self.assertTrue(slicer.mrmlScene.IsNodePresent(vessel.endPoint))

  def testDeleteLeafVesselRemovesItemFromTree(self):
    # Create a vesselRoot and leaf
    vesselParent = createVesselWithArbitraryData("parent")
    vesselLeaf = createVesselWithArbitraryData("leaf")
    vesselLeaf.startPoint = vesselParent.endPoint

    # Add vessel to tree widget
    tree = VesselTree(FakeLogic())
    treeItem = tree.addVessel(vesselParent)
    treeLeafItem = tree.addVessel(vesselLeaf)

    # Remove vessel from scene using the delete button trigger
    tree.triggerVesselButton(treeLeafItem, VesselTree.ColumnIndex.delete)

    # Verify leaf is not associated with parent
    self.assertEqual(0, treeItem.childCount())

    # verify leaf is not part of the tree
    self.assertFalse(tree.containsItem(treeLeafItem))

  def testDeleteRootVesselRemovesAssociatedLeafs(self):
    # Create vessels and setup hierarchy
    vesselParent = createVesselWithArbitraryData("parent")
    vesselChild = createVesselWithArbitraryData("child")
    vesselChild.startPoint = vesselParent.endPoint

    vesselChild2 = createVesselWithArbitraryData("child 2")
    vesselChild2.startPoint = vesselParent.endPoint

    vesselChild3 = createVesselWithArbitraryData("child 3")
    vesselChild3.startPoint = vesselParent.endPoint

    vesselSubChild = createVesselWithArbitraryData("sub child")
    vesselSubChild.startPoint = vesselChild.endPoint

    vesselSubChild2 = createVesselWithArbitraryData("sub child 2")
    vesselSubChild2.startPoint = vesselChild3.endPoint

    # Create tree and add vessels to the tree
    tree = VesselTree(FakeLogic())
    treeItemParent = tree.addVessel(vesselParent)
    treeItemChild = tree.addVessel(vesselChild)
    treeItemChild2 = tree.addVessel(vesselChild2)
    treeItemChild3 = tree.addVessel(vesselChild3)
    treeItemSubChild = tree.addVessel(vesselSubChild)
    treeItemSubChild2 = tree.addVessel(vesselSubChild2)

    # Remove child 1 and expect child and sub to be deleted
    tree.triggerVesselButton(treeItemChild, VesselTree.ColumnIndex.delete)
    self.assertFalse(tree.containsItem(treeItemChild))
    self.assertFalse(tree.containsItem(treeItemSubChild))

    # Remove root and expect all to be deleted
    tree.triggerVesselButton(treeItemParent, VesselTree.ColumnIndex.delete)
    self.assertFalse(tree.containsItem(treeItemParent))
    self.assertFalse(tree.containsItem(treeItemChild2))
    self.assertFalse(tree.containsItem(treeItemChild3))
    self.assertFalse(tree.containsItem(treeItemSubChild2))

  def testOnAddingVesselWithStartPointIdenticalToOtherVesselEndPointAddsVesselAsChildOfOther(self):
    # Create vessels and setup hierarchy
    vesselParent = createVesselWithArbitraryData("parent")
    vesselChild = createVesselWithArbitraryData("child")
    vesselChild.startPoint = vesselParent.endPoint

    vesselChild2 = createVesselWithArbitraryData("child 2")
    vesselChild2.startPoint = vesselParent.endPoint

    vesselSubChild = createVesselWithArbitraryData("sub child")
    vesselSubChild.startPoint = vesselChild.endPoint

    # Create tree and add vessels to the tree
    tree = VesselTree(FakeLogic())
    treeItemParent = tree.addVessel(vesselParent)
    treeItemChild = tree.addVessel(vesselChild)
    treeItemChild2 = tree.addVessel(vesselChild2)
    treeItemSubChild = tree.addVessel(vesselSubChild)

    # Verify hierarchy
    self.assertEqual(2, treeItemParent.childCount())
    self.assertEqual(1, treeItemChild.childCount())

    self.assertEqual(treeItemParent, treeItemChild.parent())
    self.assertEqual(treeItemParent, treeItemChild2.parent())
    self.assertEqual(treeItemChild, treeItemSubChild.parent())