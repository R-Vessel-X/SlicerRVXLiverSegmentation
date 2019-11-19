import logging
import unittest

from RVesselXLib import ExtractOneVesselPerParentAndSubChildNode, ExtractOneVesselPerParentChildNode, VesselBranchTree, \
  VesselSeedPoints, ExtractOneVesselPerBranch


class ExtractVesselStrategyTestCase(unittest.TestCase):
  def fakePosDictWithIdAsPosition(self, *args):
    return {arg: arg for arg in args}

  def testVesselSeedPointsReturnsAllButLastNodePositionAsSeedPositions(self):
    posDict = {str(i): [i] * 3 for i in range(5)}
    vesselSeed = VesselSeedPoints(posDict)
    vesselSeed.appendPoint("2")
    vesselSeed.appendPoint("1")
    vesselSeed.appendPoint("4")

    self.assertEqual([[2, 2, 2], [1, 1, 1]], vesselSeed.getSeedPositions())
    self.assertEqual([[4, 4, 4]], vesselSeed.getStopperPositions())

  def testVesselSeedPointsCanBeConstructedWithIdList(self):
    posDict = {str(i): [i] * 3 for i in range(5)}
    v1 = VesselSeedPoints(posDict)
    v1.appendPoint("2")
    v1.appendPoint("1")
    v1.appendPoint("4")

    v2 = VesselSeedPoints(posDict, ["2", "1", "4"])
    self.assertEqual(v1, v2)

  def testExtractOneVesselConstructsBranchListForEachParentChildNodePair(self):
    # Create tree
    # n0
    #     |_ n10
    #             |_ n20
    #             |_ n21
    #     |_ n11
    branchWidget = VesselBranchTree()
    branchWidget.insertAfterNode("n0", "n0", None)
    branchWidget.insertAfterNode("n10", "n10", "n0")
    branchWidget.insertAfterNode("n11", "n11", "n0")
    branchWidget.insertAfterNode("n20", "n20", "n10")
    branchWidget.insertAfterNode("n21", "n21", "n10")

    posDict = self.fakePosDictWithIdAsPosition(*branchWidget.getNodeList())

    # Create strategy
    strategy = ExtractOneVesselPerParentChildNode()

    # Verify each pair was created
    actPairs = strategy.constructVesselSeedList(branchWidget, posDict)
    expBranchPairs = [  #
      VesselSeedPoints(posDict, ("n0", "n10")),  #
      VesselSeedPoints(posDict, ("n0", "n11")),  #
      VesselSeedPoints(posDict, ("n10", "n20")),  #
      VesselSeedPoints(posDict, ("n10", "n21"))]
    self.assertEqual(sorted(expBranchPairs), sorted(actPairs))

  def testExtractOneVesselPerParentSubChildConstructsBranchListWithOneLevelChildWhenUnderRoot(self):
    # Create tree
    # n0
    #     |_ n10
    #     |_ n11
    branchWidget = VesselBranchTree()
    branchWidget.insertAfterNode("n0", "n0", None)
    branchWidget.insertAfterNode("n10", "n10", "n0")
    branchWidget.insertAfterNode("n11", "n11", "n0")

    posDict = self.fakePosDictWithIdAsPosition("n0", "n10", "n11")

    # Create strategy
    strategy = ExtractOneVesselPerParentAndSubChildNode()

    # Verify direct children were not omitted
    actPairs = strategy.constructVesselSeedList(branchWidget, posDict)
    expBranchPairs = [  #
      VesselSeedPoints(posDict, ("n0", "n10")),  #
      VesselSeedPoints(posDict, ("n0", "n11"))]
    self.assertEqual(sorted(expBranchPairs), sorted(actPairs))

  def testExtractOneVesselPerParentSubChildConstructsOnePairWhenOnlyOneParentChild(self):
    # Create tree
    # n0
    #     |_ n10
    branchWidget = VesselBranchTree()
    branchWidget.insertAfterNode("n0", "n0", None)
    branchWidget.insertAfterNode("n10", "n10", "n0")

    posDict = {"n0": [1, 1, 1], "n10": [2, 2, 2]}

    # Create strategy
    strategy = ExtractOneVesselPerParentAndSubChildNode()

    # Verify only one branch pair is generated
    actPairs = strategy.constructVesselSeedList(branchWidget, posDict)
    expBranchPairs = [VesselSeedPoints(posDict, ("n0", "n10"))]
    self.assertEqual(sorted(expBranchPairs), sorted(actPairs))

  def testExtractOneVesselPerParentSubChildExcludesDirectParentChildPairsForNonRoot(self):
    # Create tree
    # n0
    #   |_ n10
    #   |_ n11
    #       |_n20
    #       |_n21
    #           |_n31
    branchWidget = VesselBranchTree()
    branchWidget.insertAfterNode("n0", "n0", None)
    branchWidget.insertAfterNode("n10", "n10", "n0")
    branchWidget.insertAfterNode("n11", "n11", "n0")
    branchWidget.insertAfterNode("n20", "n20", "n11")
    branchWidget.insertAfterNode("n21", "n21", "n11")
    branchWidget.insertAfterNode("n31", "n31", "n21")

    posDict = self.fakePosDictWithIdAsPosition(*branchWidget.getNodeList())

    # Create strategy
    strategy = ExtractOneVesselPerParentAndSubChildNode()

    # Verify produced branches
    actPairs = strategy.constructVesselSeedList(branchWidget, posDict)
    expBranchPairs = [  #
      VesselSeedPoints(posDict, ("n0", "n10")),  #
      VesselSeedPoints(posDict, ("n0", "n20")),  #
      VesselSeedPoints(posDict, ("n0", "n21")),  #
      VesselSeedPoints(posDict, ("n11", "n31"))]
    self.assertEqual(sorted(expBranchPairs), sorted(actPairs))

  def testExtractOneVesselSeedPerBranchExtractContinuousNodesWithoutChildren(self):
    # Create Tree
    # n0
    #   |_ n10
    #       |_ n20
    #           |_n30
    #           |_n31
    #               |_ n40
    #                     |_ n50
    #           |_n32
    #
    # Exp branches
    # [n0, n10, n20]
    # [n20, n30]
    # [n20, n31, n40, n50]
    # [n20, n32]

    branchWidget = VesselBranchTree()
    branchWidget.insertAfterNode("n0", "n0", None)
    branchWidget.insertAfterNode("n10", "n10", "n0")
    branchWidget.insertAfterNode("n20", "n20", "n10")
    branchWidget.insertAfterNode("n30", "n30", "n20")
    branchWidget.insertAfterNode("n31", "n31", "n20")
    branchWidget.insertAfterNode("n32", "n32", "n20")
    branchWidget.insertAfterNode("n40", "n40", "n31")
    branchWidget.insertAfterNode("n50", "n50", "n40")

    posDict = self.fakePosDictWithIdAsPosition(*branchWidget.getNodeList())

    # Create strategy
    strategy = ExtractOneVesselPerBranch()

    # Verify produced branches
    actPairs = strategy.constructVesselSeedList(branchWidget, posDict)
    expBranchPairs = [  #
      VesselSeedPoints(posDict, ("n0", "n10", "n20")),  #
      VesselSeedPoints(posDict, ("n20", "n30")),  #
      VesselSeedPoints(posDict, ("n20", "n31", "n40", "n50")),  #
      VesselSeedPoints(posDict, ("n20", "n32"))]

    self.assertEqual(sorted(expBranchPairs), sorted(actPairs))
