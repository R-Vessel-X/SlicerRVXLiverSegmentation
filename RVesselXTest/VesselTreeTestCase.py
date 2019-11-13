import logging
import unittest

import slicer

from RVesselXLib import VesselTree, Vessel, VesselBranchTree
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


class VesselBranchTreeTestCase(unittest.TestCase):
  def testWhenTreeIsEmptyInsertAfterNoneCreatesRoot(self):
    branchWidget = VesselBranchTree()
    branchWidget.insertAfterNode("NodeId", "NodeName", None)
    self.assertEqual("NodeId", branchWidget.getRootNodeId())

  def testInsertAfterEmptyIsEquivalentToInsertAfterNone(self):
    branchWidget1 = VesselBranchTree()
    branchWidget1.insertAfterNode("NodeId", "NodeId", None)
    branchWidget1.insertAfterNode("NodeId2", "NodeId2", None)

    branchWidget2 = VesselBranchTree()
    branchWidget2.insertAfterNode("NodeId", "NodeId", "")
    branchWidget2.insertAfterNode("NodeId2", "NodeId2", "")
    self.assertEqual(branchWidget1.getTreeParentList(), branchWidget2.getTreeParentList())

  def testWhenTreeIsEmptyInsertBeforeNoneCreatesRoot(self):
    branchWidget = VesselBranchTree()
    branchWidget.insertBeforeNode("NodeId", "NodeName", None)
    self.assertEqual("NodeId", branchWidget.getRootNodeId())

  def testWhenTreeIsNotEmptyInsertBeforeNoneReplacesRoot(self):
    branchWidget = VesselBranchTree()
    branchWidget.insertBeforeNode("NodeId", "NodeId", None)
    branchWidget.insertBeforeNode("NodeId2", "NodeId2", None)
    self.assertEqual("NodeId2", branchWidget.getRootNodeId())

  def testInsertBeforeEmptyIsEquivalentToInsertBeforeNone(self):
    branchWidget1 = VesselBranchTree()
    branchWidget1.insertBeforeNode("NodeId", "NodeId", None)
    branchWidget1.insertBeforeNode("NodeId2", "NodeId2", None)

    branchWidget2 = VesselBranchTree()
    branchWidget2.insertBeforeNode("NodeId", "NodeId", "")
    branchWidget2.insertBeforeNode("NodeId2", "NodeId2", "")
    self.assertEqual(branchWidget1.getTreeParentList(), branchWidget2.getTreeParentList())

  def testWhenInsertAfterNoneAndRootExistsSetsNewNodeAsNewRoot(self):
    branchWidget = VesselBranchTree()
    branchWidget.insertAfterNode("PrevRootId", "PrevRootName", None)
    branchWidget.insertAfterNode("NewRootId", "NewRootName", None)

    self.assertEqual(sorted([[None, "NewRootId"], ["NewRootId", "PrevRootId"]]),
                     sorted(branchWidget.getTreeParentList()))

  def testWhenInsertAfterNodeNewNodeIsAddedAsChild(self):
    # ParentId
    #     |_ Child1Id
    #     |_ Child2Id
    #             |_ SubChild1Id
    branchWidget = VesselBranchTree()
    branchWidget.insertAfterNode("ParentId", "Parent", None)
    branchWidget.insertAfterNode("Child1Id", "Child1", "ParentId")
    branchWidget.insertAfterNode("Child2Id", "Child2", "ParentId")
    branchWidget.insertAfterNode("SubChild1Id", "SubChild1", "Child2Id")

    expTree = [  #
      [None, "ParentId"],  #
      ["ParentId", "Child1Id"],  #
      ["ParentId", "Child2Id"],  #
      ["Child2Id", "SubChild1Id"]  #
    ]

    self.assertEqual(expTree, branchWidget.getTreeParentList())

  def testWhenInsertBeforeNodeNewNodeIsInsertedBetweenNodeParentAndNode(self):
    # Before Tree
    # ParentId
    #     |_ Child1Id
    #             |_ SubChild1Id
    #     |_ Child2Id
    #
    # After Tree
    # ParentId
    #     |_ InsertedId
    #             |_ Child1Id
    #                     |_ SubChild1Id
    #     |_ Child2Id

    # Create before tree
    branchWidget = VesselBranchTree()
    branchWidget.insertAfterNode("ParentId", "Parent", None)
    branchWidget.insertAfterNode("Child1Id", "Child1", "ParentId")
    branchWidget.insertAfterNode("Child2Id", "Child2", "ParentId")
    branchWidget.insertAfterNode("SubChild1Id", "SubChild1", "Child1Id")

    # Insert child
    branchWidget.insertBeforeNode("InsertedId", "Inserted", "Child1Id")

    # Verify tree is as after tree
    expTree = [  #
      [None, "ParentId"],  #
      ["ParentId", "Child2Id"],  #
      ["ParentId", "InsertedId"],  #
      ["InsertedId", "Child1Id"],  #
      ["Child1Id", "SubChild1Id"],  #
    ]

    self.assertEqual(sorted(expTree), sorted(branchWidget.getTreeParentList()))

  def testWhenInsertBeforeNodeAndParentIsNoneNewNodeIsAddedAsRootItem(self):
    # Before Tree
    # ParentId
    #     |_ Child1Id
    #
    # After Tree
    # InsertedId
    #     |_ ParentId
    #         |_ ChildId

    # Create before tree
    branchWidget = VesselBranchTree()
    branchWidget.insertAfterNode("ParentId", "ParentId", None)
    branchWidget.insertAfterNode("ChildId", "ChildId", "ParentId")

    # Insert child
    branchWidget.insertBeforeNode("InsertedId", "InsertedId", None)

    # Verify tree is as after tree
    expTree = [  #
      [None, "InsertedId"],  #
      ["InsertedId", "ParentId"],  #
      ["ParentId", "ChildId"],  #
    ]

    self.assertEqual(sorted(expTree), sorted(branchWidget.getTreeParentList()))

  def testWhenInsertBeforeRootNewNodeIsAddedAsRootItem(self):
    # Before Tree
    # ParentId
    #     |_ ChildId
    #
    # After Tree
    # InsertedId
    #     |_ ParentId
    #         |_ ChildId

    # Create before tree
    branchWidget = VesselBranchTree()
    branchWidget.insertAfterNode("ParentId", "ParentId", None)
    branchWidget.insertAfterNode("ChildId", "ChildId", "ParentId")

    # Insert child
    branchWidget.insertBeforeNode("InsertedId", "InsertedId", "ParentId")

    # Verify tree is as after tree
    expTree = [  #
      [None, "InsertedId"],  #
      ["InsertedId", "ParentId"],  #
      ["ParentId", "ChildId"],  #
    ]

    self.assertEqual(sorted(expTree), sorted(branchWidget.getTreeParentList()))

  def testWhenRemovingIntermediateNodeConnectsChildrenNodesToParentNode(self):
    # Before Tree
    # ParentId
    #     |_ childToDeleteId
    #             |_ SubChild1Id
    #             |_ SubChild2Id
    #     |_ Child2Id
    #
    # After Tree
    # ParentId
    #     |_ SubChild1Id
    #     |_ SubChild2Id
    #     |_ Child2Id

    # Create before tree
    branchWidget = VesselBranchTree()
    branchWidget.insertAfterNode("ParentId", "Parent", None)
    branchWidget.insertAfterNode("childToDeleteId", "childToDelete", "ParentId")
    branchWidget.insertAfterNode("Child2Id", "Child2", "ParentId")
    branchWidget.insertAfterNode("SubChild1Id", "SubChild1", "childToDeleteId")
    branchWidget.insertAfterNode("SubChild2Id", "SubChild2", "childToDeleteId")

    # Remove child
    wasRemoved = branchWidget.removeNode("childToDeleteId")

    # Verify tree is as after tree
    expTree = [  #
      [None, "ParentId"],  #
      ["ParentId", "SubChild1Id"],  #
      ["ParentId", "SubChild2Id"],  #
      ["ParentId", "Child2Id"],  #
    ]

    self.assertTrue(wasRemoved)
    self.assertEqual(sorted(expTree), sorted(branchWidget.getTreeParentList()))

  def testWhenRemovingRootAndHasMultipleChildrenDoesNothing(self):
    # Before Tree and after tree
    # ParentId
    #     |_ Child1Id
    #             |_ SubChild1Id
    #             |_ SubChild2Id
    #     |_ Child2Id
    #

    # Create before tree
    branchWidget = VesselBranchTree()
    branchWidget.insertAfterNode("ParentId", "Parent", None)
    branchWidget.insertAfterNode("Child1Id", "Child1", "ParentId")
    branchWidget.insertAfterNode("Child2Id", "Child2", "ParentId")
    branchWidget.insertAfterNode("SubChild1Id", "SubChild1", "Child1Id")
    branchWidget.insertAfterNode("SubChild2Id", "SubChild2", "Child1Id")

    expTree = branchWidget.getTreeParentList()

    # Remove root
    wasRemoved = branchWidget.removeNode("ParentId")

    # Verify tree hasn't changed
    self.assertFalse(wasRemoved)
    self.assertEqual(sorted(expTree), sorted(branchWidget.getTreeParentList()))

  def testWhenRemovingRootWhenLastRemainingRemovesRoot(self):
    # Create tree with one root
    branchWidget = VesselBranchTree()
    branchWidget.insertAfterNode("ParentId", "Parent", None)

    # Remove root and expect success
    wasRemoved = branchWidget.removeNode("ParentId")

    # Verify tree is empty
    self.assertTrue(wasRemoved)
    self.assertEqual([], branchWidget.getTreeParentList())

  def testWhenRemovingRootAndHasOneDirectChildSelectsChildAsRoot(self):
    # Before Tree
    # ParentId
    #     |_ Child1Id
    #             |_ SubChild1Id
    #             |_ SubChild2Id
    #             |_ SubChild3Id
    #
    # After Tree
    # |_ Child1Id
    #         |_ SubChild1Id
    #         |_ SubChild2Id
    #         |_ SubChild3Id
    #

    # Create before tree
    branchWidget = VesselBranchTree()
    branchWidget.insertAfterNode("ParentId", "Parent", None)
    branchWidget.insertAfterNode("Child1Id", "Child1", "ParentId")
    branchWidget.insertAfterNode("SubChild1Id", "SubChild1", "Child1Id")
    branchWidget.insertAfterNode("SubChild2Id", "SubChild2", "Child1Id")
    branchWidget.insertAfterNode("SubChild3Id", "SubChild3", "Child1Id")

    # Remove root
    wasRemoved = branchWidget.removeNode("ParentId")

    # Verify tree is as after tree
    expTree = [  #
      [None, "Child1Id"],  #
      ["Child1Id", "SubChild1Id"],  #
      ["Child1Id", "SubChild2Id"],  #
      ["Child1Id", "SubChild3Id"],  #
    ]

    self.assertTrue(wasRemoved)
    self.assertEqual(sorted(expTree), sorted(branchWidget.getTreeParentList()))

  def _createArbitraryTree(self):
    # Tree
    # ParentId
    #     |_ Child1Id
    #             |_ SubChild1Id
    #             |_ SubChild2Id
    #     |_ Child2Id
    #             |_ SubChild3Id

    # Create tree
    branchWidget = VesselBranchTree()
    branchWidget.insertAfterNode("ParentId", "Parent", None)
    branchWidget.insertAfterNode("Child1Id", "Child1", "ParentId")
    branchWidget.insertAfterNode("Child2Id", "Child2", "ParentId")
    branchWidget.insertAfterNode("SubChild1Id", "SubChild1", "Child1Id")
    branchWidget.insertAfterNode("SubChild2Id", "SubChild2", "Child1Id")
    branchWidget.insertAfterNode("SubChild3Id", "SubChild3", "Child2Id")
    return branchWidget

  def testParentNodeCanBeAccessedViaGetter(self):
    # Tree
    # ParentId
    #     |_ Child1Id
    #             |_ SubChild1Id
    #             |_ SubChild2Id
    #     |_ Child2Id
    #             |_ SubChild3Id

    branchWidget = self._createArbitraryTree()

    # Verify getters
    self.assertEqual("Child1Id", branchWidget.getParentNodeId("SubChild2Id"))
    self.assertEqual("ParentId", branchWidget.getParentNodeId("Child1Id"))
    self.assertEqual(None, branchWidget.getParentNodeId("ParentId"))

  def testWhenAccessingLastSiblingGetNextSiblingNodeReturnsNone(self):
    # Tree
    # ParentId
    #     |_ Child1Id
    #             |_ SubChild1Id
    #             |_ SubChild2Id
    #     |_ Child2Id
    #             |_ SubChild3Id

    branchWidget = self._createArbitraryTree()
    self.assertEqual("SubChild2Id", branchWidget.getNextSiblingNodeId("SubChild1Id"))
    self.assertEqual(None, branchWidget.getNextSiblingNodeId("SubChild2Id"))

  def testWhenAccessingFirstSiblingGetPreviousSiblingNodeReturnsNone(self):
    # Tree
    # ParentId
    #     |_ Child1Id
    #             |_ SubChild1Id
    #             |_ SubChild2Id
    #     |_ Child2Id
    #             |_ SubChild3Id

    branchWidget = self._createArbitraryTree()
    self.assertEqual("SubChild1Id", branchWidget.getPreviousSiblingNodeId("SubChild2Id"))
    self.assertEqual(None, branchWidget.getPreviousSiblingNodeId("SubChild1Id"))

  def testWhenGettingChildrenReturnsListOfDirectChildren(self):
    # Tree
    # ParentId
    #     |_ Child1Id
    #             |_ SubChild1Id
    #             |_ SubChild2Id
    #     |_ Child2Id
    #             |_ SubChild3Id

    branchWidget = self._createArbitraryTree()

    # Verify getters
    self.assertEqual(["Child1Id", "Child2Id"], branchWidget.getChildrenNodeId("ParentId"))
    self.assertEqual([], branchWidget.getChildrenNodeId("SubChild3Id"))

  def testWhenReorderingTreeWhenThereExistAnotherRootNodeRootsTreeOnObect(self):
    # Before Tree
    # ParentId
    #     |_ Child1Id
    # ParentId2
    #     |_ Child2Id
    #
    # After Tree
    # ParentId2
    #     |_ ParentId
    #           |_Child1Id
    #     |_ Child2Id

    # Create before tree
    branchWidget = VesselBranchTree()
    branchWidget.insertAfterNode("ParentId", "ParentId", None)
    branchWidget.insertAfterNode("Child1Id", "Child1Id", "ParentId")
    branchWidget.insertAfterNode("ParentId2", "ParentId2", None)
    branchWidget.insertAfterNode("Child2Id", "Child2Id", "ParentId2")

    # Enforce one root
    branchWidget.enforceOneRoot()

    # Verify tree is as after tree
    expTree = [  #
      [None, "ParentId2"],  #
      ["ParentId2", "ParentId"],  #
      ["ParentId", "Child1Id"],  #
      ["ParentId2", "Child2Id"],  #
    ]

    self.assertEqual(sorted(expTree), sorted(branchWidget.getTreeParentList()))

  def testWhenReorderingTreeReorderingStopsWhenOnlyOneItemIsLeftAsRoot(self):
    # Before Tree
    # ParentId1
    # ParentId2
    # ParentId3
    #
    # After Tree
    # ParentId3
    #     |_ ParentId2
    #           |_ParentId1

    # Create before tree
    branchWidget = VesselBranchTree()
    branchWidget.insertAfterNode("ParentId1", "ParentId1", None)
    branchWidget.insertAfterNode("ParentId2", "ParentId2", None)
    branchWidget.insertAfterNode("ParentId3", "ParentId3", None)

    # Enforce one root
    branchWidget.enforceOneRoot()

    # Verify tree is as after tree
    expTree = [  #
      [None, "ParentId3"],  #
      ["ParentId3", "ParentId2"],  #
      ["ParentId2", "ParentId1"],  #
    ]

    self.assertEqual(sorted(expTree), sorted(branchWidget.getTreeParentList()))

  def testWhenReorderingEmptyTreeDoesNothing(self):
    # Create empty tree
    branchWidget = VesselBranchTree()

    # Enforce one root and expect no error
    branchWidget.enforceOneRoot()
