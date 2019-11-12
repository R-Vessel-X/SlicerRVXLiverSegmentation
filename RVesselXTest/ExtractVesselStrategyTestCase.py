import unittest

from RVesselXLib import ExtractOneVesselPerParentAndSubChildNode, ExtractOneVesselPerBranch, VesselBranchTree


class ExtractVesselStrategyTestCase(unittest.TestCase):
  def fakePosDictWithIdAsPosition(self, *args):
    return {arg: arg for arg in args}

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

    posDict = self.fakePosDictWithIdAsPosition("n0", "n10", "n11", "n20", "n21")

    # Create strategy
    strategy = ExtractOneVesselPerBranch()

    # Verify each pair was created
    actPairs = strategy.constructNodeBranchPairs(branchWidget, posDict)
    expBranchPairs = [("n0", "n10"), ("n0", "n11"), ("n10", "n20"), ("n10", "n21")]
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
    actPairs = strategy.constructNodeBranchPairs(branchWidget, posDict)
    expBranchPairs = [("n0", "n10"), ("n0", "n11")]
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
    actPairs = strategy.constructNodeBranchPairs(branchWidget, posDict)
    expBranchPairs = [([1, 1, 1], [2, 2, 2])]
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

    posDict = self.fakePosDictWithIdAsPosition("n0", "n10", "n11", "n20", "n21", "n31")

    # Create strategy
    strategy = ExtractOneVesselPerParentAndSubChildNode()

    # Verify produced branches
    actPairs = strategy.constructNodeBranchPairs(branchWidget, posDict)
    expBranchPairs = [("n0", "n10"), ("n0", "n20"), ("n0", "n21"), ("n11", "n31")]
    self.assertEqual(sorted(expBranchPairs), sorted(actPairs))
