import unittest

from RVesselXLib import VesselBranchTree


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
