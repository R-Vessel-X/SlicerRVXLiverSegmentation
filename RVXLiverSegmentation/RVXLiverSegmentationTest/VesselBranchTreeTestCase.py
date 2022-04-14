import unittest

from RVXLiverSegmentationLib import VesselBranchTree, PlaceStatus, VesselAdjacencyMatrixExporter, VesselHelpWidget, \
  VesselHelpType
from .TestUtils import FakeMarkupNode, treeSort


class VesselBranchTreeTestCase(unittest.TestCase):
  def testWhenTreeIsEmptyInsertAfterNoneCreatesRoot(self):
    branchWidget = VesselBranchTree(VesselHelpWidget(VesselHelpType.Portal))
    branchWidget.insertAfterNode("NodeId", None)
    self.assertEqual("NodeId", branchWidget.getRootNodeId())

  def testInsertAfterEmptyIsEquivalentToInsertAfterNone(self):
    branchWidget1 = VesselBranchTree(VesselHelpWidget(VesselHelpType.Portal))
    branchWidget1.insertAfterNode("NodeId", None)
    branchWidget1.insertAfterNode("NodeId2", None)

    branchWidget2 = VesselBranchTree(VesselHelpWidget(VesselHelpType.Portal))
    branchWidget2.insertAfterNode("NodeId", "")
    branchWidget2.insertAfterNode("NodeId2", "")
    self.assertEqual(branchWidget1.getTreeParentList(), branchWidget2.getTreeParentList())

  def testWhenTreeIsEmptyInsertBeforeNoneCreatesRoot(self):
    branchWidget = VesselBranchTree(VesselHelpWidget(VesselHelpType.Portal))
    branchWidget.insertBeforeNode("NodeId", None)
    self.assertEqual("NodeId", branchWidget.getRootNodeId())

  def testWhenTreeIsNotEmptyInsertBeforeNoneReplacesRoot(self):
    branchWidget = VesselBranchTree(VesselHelpWidget(VesselHelpType.Portal))
    branchWidget.insertBeforeNode("NodeId", None)
    branchWidget.insertBeforeNode("NodeId2", None)
    self.assertEqual("NodeId2", branchWidget.getRootNodeId())

  def testInsertBeforeEmptyIsEquivalentToInsertBeforeNone(self):
    branchWidget1 = VesselBranchTree(VesselHelpWidget(VesselHelpType.Portal))
    branchWidget1.insertBeforeNode("NodeId", None)
    branchWidget1.insertBeforeNode("NodeId2", None)

    branchWidget2 = VesselBranchTree(VesselHelpWidget(VesselHelpType.Portal))
    branchWidget2.insertBeforeNode("NodeId", "")
    branchWidget2.insertBeforeNode("NodeId2", "")
    self.assertEqual(branchWidget1.getTreeParentList(), branchWidget2.getTreeParentList())

  def testWhenInsertAfterNoneAndRootExistsSetsNewNodeAsNewRoot(self):
    branchWidget = VesselBranchTree(VesselHelpWidget(VesselHelpType.Portal))
    branchWidget.insertAfterNode("PrevRootId", None)
    branchWidget.insertAfterNode("NewRootId", None)

    self.assertEqual(treeSort([[None, "NewRootId"], ["NewRootId", "PrevRootId"]]),
                     treeSort(branchWidget.getTreeParentList()))

  def testWhenInsertAfterNodeNewNodeIsAddedAsChild(self):
    # ParentId
    #     |_ Child1Id
    #     |_ Child2Id
    #             |_ SubChild1Id
    branchWidget = VesselBranchTree(VesselHelpWidget(VesselHelpType.Portal))
    branchWidget.insertAfterNode("ParentId", None)
    branchWidget.insertAfterNode("Child1Id", "ParentId")
    branchWidget.insertAfterNode("Child2Id", "ParentId")
    branchWidget.insertAfterNode("SubChild1Id", "Child2Id")

    expTree = [  #
      [None, "ParentId"],  #
      ["ParentId", "Child1Id"],  #
      ["ParentId", "Child2Id"],  #
      ["Child2Id", "SubChild1Id"]  #
    ]

    self.assertEqual(expTree, branchWidget.getTreeParentList())

  def testGetNodeListReturnsListOfNodesWhichHaveBeenPlaced(self):
    # ParentId
    #     |_ Child1Id
    #     |_ Child2Id
    #             |_ SubChild1Id
    branchWidget = VesselBranchTree(VesselHelpWidget(VesselHelpType.Portal))
    branchWidget.insertAfterNode("ParentId", None)
    branchWidget.insertAfterNode("Child1Id", "ParentId")
    branchWidget.insertAfterNode("Child2Id", "ParentId")
    branchWidget.insertAfterNode("SubChild1Id", "Child2Id")

    branchWidget.getTreeWidgetItem("ParentId").status = PlaceStatus.PLACED
    branchWidget.getTreeWidgetItem("Child1Id").status = PlaceStatus.PLACING
    branchWidget.getTreeWidgetItem("Child2Id").status = PlaceStatus.PLACED
    branchWidget.getTreeWidgetItem("SubChild1Id").status = PlaceStatus.NOT_PLACED

    nodeList = branchWidget.getPlacedNodeList()
    self.assertNotIn("Child1Id", nodeList)
    self.assertNotIn("SubChild1Id", nodeList)
    self.assertIn("ParentId", nodeList)
    self.assertIn("Child2Id", nodeList)

  def testGetNodeListReturnsListOfEveryNodeInTree(self):
    # ParentId
    #     |_ Child1Id
    #     |_ Child2Id
    #             |_ SubChild1Id
    branchWidget = VesselBranchTree(VesselHelpWidget(VesselHelpType.Portal))
    branchWidget.insertAfterNode("ParentId", None)
    branchWidget.insertAfterNode("Child1Id", "ParentId")
    branchWidget.insertAfterNode("Child2Id", "ParentId")
    branchWidget.insertAfterNode("SubChild1Id", "Child2Id")

    branchWidget.getTreeWidgetItem("ParentId").status = PlaceStatus.PLACED
    branchWidget.getTreeWidgetItem("Child1Id").status = PlaceStatus.PLACING
    branchWidget.getTreeWidgetItem("Child2Id").status = PlaceStatus.PLACED
    branchWidget.getTreeWidgetItem("SubChild1Id").status = PlaceStatus.NOT_PLACED

    nodeList = branchWidget.getNodeList()
    self.assertIn("Child1Id", nodeList)
    self.assertIn("SubChild1Id", nodeList)
    self.assertIn("ParentId", nodeList)
    self.assertIn("Child2Id", nodeList)

  def testBranchTreeCanBeExportedAsAdjacencyMatrix(self):
    # ParentId
    #     |_ Child1Id
    #     |_ Child2Id
    #             |_ SubChild1Id
    #                     |_ SubSubChild1Id
    branchWidget = VesselBranchTree(VesselHelpWidget(VesselHelpType.Portal))
    branchWidget.insertAfterNode("N00", None)
    branchWidget.insertAfterNode("N10", "N00")
    branchWidget.insertAfterNode("N11", "N00")
    branchWidget.insertAfterNode("N20", "N11")
    branchWidget.insertAfterNode("N30", "N20")

    exp_nodes = ["N00", "N10", "N11", "N20", "N30"]
    exp_matrix = [  #
      [0, 1, 1, 0, 0],  #
      [1, 0, 0, 0, 0],  #
      [1, 0, 0, 1, 0],  #
      [0, 0, 1, 0, 1],  #
      [0, 0, 0, 1, 0],  #
    ]

    nodes, matrix = VesselAdjacencyMatrixExporter.toAdjacencyMatrix(branchWidget)
    self.assertEqual(exp_nodes, nodes)
    self.assertEqual(exp_matrix, matrix)

  def testBranchTreeAndNodesCanBeExportedInDgtalFormat(self):
    # ParentId
    #     |_ Child1Id
    #     |_ Child2Id
    #             |_ SubChild1Id
    #                     |_ SubSubChild1Id

    branchWidget = VesselBranchTree(VesselHelpWidget(VesselHelpType.Portal))
    branchWidget.insertAfterNode("N00", None)
    branchWidget.insertAfterNode("N10", "N00")
    branchWidget.insertAfterNode("N11", "N00")
    branchWidget.insertAfterNode("N20", "N11")
    branchWidget.insertAfterNode("N30", "N20")

    markup = FakeMarkupNode()
    markup.add_node("N00", [0] * 3)
    markup.add_node("N10", [1] * 3)
    markup.add_node("N11", [2] * 3)
    markup.add_node("N20", [3] * 3)
    markup.add_node("N30", [4] * 3)

    edges, vertex = VesselAdjacencyMatrixExporter.toDgtal(markup, branchWidget)

    exp_edges = [  #
      [0, 1],  #
      [0, 2],  #
      [2, 3],  #
      [3, 4],  #
    ]

    exp_vertex = [  #
      [0] * 3,  #
      [1] * 3,  #
      [2] * 3,  #
      [3] * 3,  #
      [4] * 3,  #
    ]

    self.assertEqual(exp_edges, edges)
    self.assertEqual(exp_vertex, vertex)

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
    branchWidget = VesselBranchTree(VesselHelpWidget(VesselHelpType.Portal))
    branchWidget.insertAfterNode("ParentId", None)
    branchWidget.insertAfterNode("Child1Id", "ParentId")
    branchWidget.insertAfterNode("Child2Id", "ParentId")
    branchWidget.insertAfterNode("SubChild1Id", "Child1Id")

    # Insert child
    branchWidget.insertBeforeNode("InsertedId", "Child1Id")

    # Verify tree is as after tree
    expTree = [  #
      [None, "ParentId"],  #
      ["ParentId", "Child2Id"],  #
      ["ParentId", "InsertedId"],  #
      ["InsertedId", "Child1Id"],  #
      ["Child1Id", "SubChild1Id"],  #
    ]

    self.assertEqual(treeSort(expTree), treeSort(branchWidget.getTreeParentList()))

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
    branchWidget = VesselBranchTree(VesselHelpWidget(VesselHelpType.Portal))
    branchWidget.insertAfterNode("ParentId", None)
    branchWidget.insertAfterNode("ChildId", "ParentId")

    # Insert child
    branchWidget.insertBeforeNode("InsertedId", None)

    # Verify tree is as after tree
    expTree = [  #
      [None, "InsertedId"],  #
      ["InsertedId", "ParentId"],  #
      ["ParentId", "ChildId"],  #
    ]

    self.assertEqual(treeSort(expTree), treeSort(branchWidget.getTreeParentList()))

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
    branchWidget = VesselBranchTree(VesselHelpWidget(VesselHelpType.Portal))
    branchWidget.insertAfterNode("ParentId", None)
    branchWidget.insertAfterNode("ChildId", "ParentId")

    # Insert child
    branchWidget.insertBeforeNode("InsertedId", "ParentId")

    # Verify tree is as after tree
    expTree = [  #
      [None, "InsertedId"],  #
      ["InsertedId", "ParentId"],  #
      ["ParentId", "ChildId"],  #
    ]

    self.assertEqual(treeSort(expTree), treeSort(branchWidget.getTreeParentList()))

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
    branchWidget = VesselBranchTree(VesselHelpWidget(VesselHelpType.Portal))
    branchWidget.insertAfterNode("ParentId", None)
    branchWidget.insertAfterNode("childToDeleteId", "ParentId")
    branchWidget.insertAfterNode("Child2Id", "ParentId")
    branchWidget.insertAfterNode("SubChild1Id", "childToDeleteId")
    branchWidget.insertAfterNode("SubChild2Id", "childToDeleteId")

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
    self.assertEqual(treeSort(expTree), treeSort(branchWidget.getTreeParentList()))

  def testWhenRemovingRootAndHasMultipleChildrenDoesNothing(self):
    # Before Tree and after tree
    # ParentId
    #     |_ Child1Id
    #             |_ SubChild1Id
    #             |_ SubChild2Id
    #     |_ Child2Id
    #

    # Create before tree
    branchWidget = VesselBranchTree(VesselHelpWidget(VesselHelpType.Portal))
    branchWidget.insertAfterNode("ParentId", None)
    branchWidget.insertAfterNode("Child1Id", "ParentId")
    branchWidget.insertAfterNode("Child2Id", "ParentId")
    branchWidget.insertAfterNode("SubChild1Id", "Child1Id")
    branchWidget.insertAfterNode("SubChild2Id", "Child1Id")

    expTree = branchWidget.getTreeParentList()

    # Remove root
    wasRemoved = branchWidget.removeNode("ParentId")

    # Verify tree hasn't changed
    self.assertFalse(wasRemoved)
    self.assertEqual(treeSort(expTree), treeSort(branchWidget.getTreeParentList()))

  def testWhenRemovingRootWhenLastRemainingRemovesRoot(self):
    # Create tree with one root
    branchWidget = VesselBranchTree(VesselHelpWidget(VesselHelpType.Portal))
    branchWidget.insertAfterNode("ParentId", None)

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
    branchWidget = VesselBranchTree(VesselHelpWidget(VesselHelpType.Portal))
    branchWidget.insertAfterNode("ParentId", None)
    branchWidget.insertAfterNode("Child1Id", "ParentId")
    branchWidget.insertAfterNode("SubChild1Id", "Child1Id")
    branchWidget.insertAfterNode("SubChild2Id", "Child1Id")
    branchWidget.insertAfterNode("SubChild3Id", "Child1Id")

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
    self.assertEqual(treeSort(expTree), treeSort(branchWidget.getTreeParentList()))

  def _createArbitraryTree(self):
    # Tree
    # ParentId
    #     |_ Child1Id
    #             |_ SubChild1Id
    #             |_ SubChild2Id
    #     |_ Child2Id
    #             |_ SubChild3Id

    # Create tree
    branchWidget = VesselBranchTree(VesselHelpWidget(VesselHelpType.Portal))
    branchWidget.insertAfterNode("ParentId", None)
    branchWidget.insertAfterNode("Child1Id", "ParentId")
    branchWidget.insertAfterNode("Child2Id", "ParentId")
    branchWidget.insertAfterNode("SubChild1Id", "Child1Id")
    branchWidget.insertAfterNode("SubChild2Id", "Child1Id")
    branchWidget.insertAfterNode("SubChild3Id", "Child2Id")
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
    branchWidget = VesselBranchTree(VesselHelpWidget(VesselHelpType.Portal))
    branchWidget.insertAfterNode("ParentId", None)
    branchWidget.insertAfterNode("Child1Id", "ParentId")
    branchWidget.insertAfterNode("ParentId2", None)
    branchWidget.insertAfterNode("Child2Id", "ParentId2")

    # Enforce one root
    branchWidget.enforceOneRoot()

    # Verify tree is as after tree
    expTree = [  #
      [None, "ParentId2"],  #
      ["ParentId2", "ParentId"],  #
      ["ParentId", "Child1Id"],  #
      ["ParentId2", "Child2Id"],  #
    ]

    self.assertEqual(treeSort(expTree), treeSort(branchWidget.getTreeParentList()))

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
    branchWidget = VesselBranchTree(VesselHelpWidget(VesselHelpType.Portal))
    branchWidget.insertAfterNode("ParentId1", None)
    branchWidget.insertAfterNode("ParentId2", None)
    branchWidget.insertAfterNode("ParentId3", None)

    # Enforce one root
    branchWidget.enforceOneRoot()

    # Verify tree is as after tree
    expTree = [  #
      [None, "ParentId3"],  #
      ["ParentId3", "ParentId2"],  #
      ["ParentId2", "ParentId1"],  #
    ]

    self.assertEqual(treeSort(expTree), treeSort(branchWidget.getTreeParentList()))

  def testWhenReorderingEmptyTreeDoesNothing(self):
    # Create empty tree
    branchWidget = VesselBranchTree(VesselHelpWidget(VesselHelpType.Portal))

    # Enforce one root and expect no error
    branchWidget.enforceOneRoot()

  def testGetNextUnplaced(self):
    # Tree
    # id01
    #   |_ id11
    #     |_ id21
    #     |_ id22
    #       |_ id31
    #   |_ id12
    #     |_ id23
    #     |_ id24

    # Create before tree
    branchWidget = VesselBranchTree(VesselHelpWidget(VesselHelpType.Portal))
    branchWidget.insertAfterNode("id01", None)
    branchWidget.insertAfterNode("id11", "id01")
    branchWidget.insertAfterNode("id21", "id11")
    branchWidget.insertAfterNode("id22", "id11")
    branchWidget.insertAfterNode("id31", "id22")
    branchWidget.insertAfterNode("id12", "id01")
    branchWidget.insertAfterNode("id23", "id12")
    branchWidget.insertAfterNode("id24", "id12")

    def getItem(nodeId): return branchWidget.getTreeWidgetItem(nodeId)

    getItem("id01").status = PlaceStatus.PLACED
    self.assertEqual(getItem("id11"), branchWidget.getNextUnplacedItem("id01"))

    getItem("id11").status = PlaceStatus.PLACED
    self.assertEqual(getItem("id21"), branchWidget.getNextUnplacedItem("id11"))

    getItem("id31").status = PlaceStatus.PLACED
    self.assertEqual(getItem("id12"), branchWidget.getNextUnplacedItem("id31"))
