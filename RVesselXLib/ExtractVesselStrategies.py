import slicer

from RVesselXModuleLogic import RVesselXModuleLogic
from RVesselXUtils import getMarkupIdPositionDictionary, createLabelMapVolumeNodeBasedOnModel


class IExtractVesselStrategy(object):
  """Interface object for vessel volume extraction from source vessel branch tree and associated markup.
  """

  def extractVesselVolumeFromVesselBranchTree(self, vesselBranchTree, vesselBranchMarkup, logic):
    """Extract vessel volume and model from input data.
    The data are expected to be unchanged when the algorithm has run.

    Parameters
    ----------
    vesselBranchTree: VesselBranchTree
      Tree containing the hierarchy of the markups
    vesselBranchMarkup: vtkMRMLMarkupsFiducialNode
      Markup containing all the vessel branches
    logic: RVesselXModuleLogic

    Returns
    -------
    Tuple[vtkMRMLScalarVolume, vtkMRMLModel]
      Tuple containing extracted volume information and associated poly data model
    """
    pass


def mergeVolumes(volumes, volName):
  """Merges volumes nodes into a single volume node with volName label. Also returns extracted volume surface mesh.

  Parameters
  ----------
  volumes: List[vtkMRMLVolumeNode]
  volName: str

  Returns
  -------
  Tuple[vtkMRMLVolumeNode, vtkMRMLModelNode]
  """
  # Extract list of volumes as list of np arrays
  npVolumes = [slicer.util.arrayFromVolume(volume).astype(int) for volume in volumes]

  # Merge all volumes in one
  mergedVol = npVolumes[0]
  for i in range(1, len(npVolumes)):
    mergedVol |= npVolumes[i]

  # Create output volume in slicer
  outVol = createLabelMapVolumeNodeBasedOnModel(volumes[0], volName)
  slicer.util.updateVolumeFromArray(outVol, mergedVol)
  return outVol, RVesselXModuleLogic.createVolumeBoundaryModel(outVol, volName + "Model", threshold=1)


class ExtractAllVesselsInOneGoStrategy(IExtractVesselStrategy):
  """Strategy uses VMTK on all markup points at once to extract data.
  """

  def extractVesselVolumeFromVesselBranchTree(self, vesselBranchTree, vesselBranchMarkup, logic):
    """Extract vessel volume and model from input data.
    The data are expected to be unchanged when the algorithm has run.

    Parameters
    ----------
    vesselBranchTree: VesselBranchTree
      Tree containing the hierarchy of the markups
    vesselBranchMarkup: vtkMRMLMarkupsFiducialNode
      Markup containing all the vessel branches
    logic: RVesselXModuleLogic

    Returns
    -------
    Tuple[vtkMRMLScalarVolume, vtkMRMLModel]
      Tuple containing extracted volume information and associated poly data model
    """
    # Extract all the node ids in the tree and group them by either seed or end id
    # End Ids regroup all the ids which are tree leaves
    nodeList = vesselBranchTree.getNodeList()
    seedIds = []
    endIds = []
    for node in nodeList:
      if vesselBranchTree.isLeaf(node):
        endIds.append(node)
      else:
        seedIds.append(node)

    # Convert seed id list and end id list to position lists
    idPositionDict = getMarkupIdPositionDictionary(vesselBranchMarkup)
    seedsPositions = [idPositionDict[nodeId] for nodeId in seedIds]
    endPositions = [idPositionDict[nodeId] for nodeId in endIds]

    # Call VMTK level set segmentation algorithm and return values
    seedsNodes, stoppersNodes, outVolume, outModel = logic.extractVesselVolumeFromPosition(seedsPositions, endPositions)
    slicer.mrmlScene.RemoveNode(seedsNodes)
    slicer.mrmlScene.RemoveNode(stoppersNodes)
    return outVolume, outModel


class ExtractVesselFromNodePairsStrategy(IExtractVesselStrategy):
  """Base class for strategies using VMTK on multiple start + end points and aggregating results as one volume.
  deriving classes must implement a function returning a list of node pairs constructed from vessel tree and node id
  position dictionary
  """

  def constructNodeBranchPairs(self, vesselBranchTree, idPositionDict):
    """
    Parameters
    ----------
    vesselBranchTree: VesselBranchTree
      Tree containing the hierarchy of the markups
    idPositionDict: Dict[str,List[float]]
      Dictionary with nodeId as key and node position as value

    Returns
    -------
    List[Tuple[List[float], list[float]]]
      List of (vessel start position, vessel end position) to extract using VMTK
    """
    pass

  def extractVesselVolumeFromVesselBranchTree(self, vesselBranchTree, vesselBranchMarkup, logic):
    """Extract vessel volume and model from input data.
    The data are expected to be unchanged when the algorithm has run.

    Parameters
    ----------
    vesselBranchTree: VesselBranchTree
      Tree containing the hierarchy of the markups
    vesselBranchMarkup: vtkMRMLMarkupsFiducialNode
      Markup containing all the vessel branches
    logic: RVesselXModuleLogic

    Returns
    -------
    Tuple[vtkMRMLScalarVolume, vtkMRMLModel]
      Tuple containing extracted volume information and associated poly data model
    """
    # Convert seed id list and end id list to position lists
    idPositionDict = getMarkupIdPositionDictionary(vesselBranchMarkup)

    # Extract all the branches in the tree.
    # Loop over all ids
    branchList = self.constructNodeBranchPairs(vesselBranchTree, idPositionDict)

    volumes = []
    elementsToRemoveFromScene = []
    for branch in branchList:
      seedsNodes, stoppersNodes, outVolume, outModel = logic.extractVesselVolumeFromPosition([branch[0]], [branch[1]])
      elementsToRemoveFromScene.append(seedsNodes)
      elementsToRemoveFromScene.append(stoppersNodes)
      elementsToRemoveFromScene.append(outModel)
      elementsToRemoveFromScene.append(outVolume)
      volumes.append(outVolume)

    outVolume, outModel = mergeVolumes(volumes, "levelSetSegmentation")
    for volume in elementsToRemoveFromScene:
      slicer.mrmlScene.RemoveNode(volume)

    return outVolume, outModel


class ExtractOneVesselPerBranch(ExtractVesselFromNodePairsStrategy):
  """Strategy uses VMTK on parent + child pair and merges the results as output.

  Example :
  node 0
    |_ node 1-0
    |_ node 1-1
        |_node 2-0
        |_node 2-1
            |_node 3-1

  Expected VMTK run :
    Branch [0 & 1-0]
    Branch [0 & 1-1]
    Branch [1-1 & 2-0]
    Branch [1-1 & 2-1]
    Branch [2-1 & 3-1]
  """

  def constructNodeBranchPairs(self, vesselBranchTree, idPositionDict):
    """
    Parameters
    ----------
    vesselBranchTree: VesselBranchTree
      Tree containing the hierarchy of the markups
    idPositionDict: Dict[str,List[float]]
      Dictionary with nodeId as key and node position as value

    Returns
    -------
    List[Tuple[List[float], list[float]]]
      List of (vessel start position, vessel end position) to extract using VMTK
    """

    # Extract all the branches in the tree and return as branch list
    nodeList = vesselBranchTree.getNodeList()
    branchList = []

    for node in nodeList:
      startPos = idPositionDict[node]
      for child in vesselBranchTree.getChildrenNodeId(node):
        endPos = idPositionDict[child]
        branchList.append((startPos, endPos))
    return branchList


class ExtractOneVesselPerParentAndSubChildNode(ExtractVesselFromNodePairsStrategy):
  """Strategy uses VMTK on parent + sub child pair and merges the results as output.

  Example :
  node 0
    |_ node 1-0
    |_ node 1-1
        |_node 2-0
        |_node 2-1
            |_node 3-1

  Expected VMTK run :
    Branch [0 & 1-0]
    Branch [0 & 2-0]
    Branch [0 & 2-1]
    Branch [1-1 & 3-1]
  """

  def constructNodeBranchPairs(self, vesselBranchTree, idPositionDict):
    """
    Parameters
    ----------
    vesselBranchTree: VesselBranchTree
      Tree containing the hierarchy of the markups
    idPositionDict: Dict[str,List[float]]
      Dictionary with nodeId as key and node position as value

    Returns
    -------
    List[Tuple[List[float], list[float]]]
      List of (vessel start position, vessel end position) to extract using VMTK
    """
    return self.parentSubChildBranchPairs(vesselBranchTree, idPositionDict)

  def parentSubChildBranchPairs(self, vesselBranchTree, idPositionDict, startNode=None):
    # Initialize branch list
    branchList = []

    # Initialize start node as tree root if startNode not provided
    isStartNodeRoot = False
    if startNode is None:
      startNode = vesselBranchTree.getRootNodeId()
      isStartNodeRoot = True

    startPos = idPositionDict[startNode]
    for child in vesselBranchTree.getChildrenNodeId(startNode):
      # Construct startNode + subChildren pairs
      subChildren = vesselBranchTree.getChildrenNodeId(child)
      for subChild in subChildren:
        branchList.append((startPos, idPositionDict[subChild]))

      # Special case if starting from root node and current node doesn't have children (to avoid missing the point)
      # otherwise, the node will be contained in a previous parent + subChild pair
      if len(subChildren) == 0 and isStartNodeRoot:
        branchList.append((startPos, idPositionDict[child]))

      # Call recursively for children
      branchList += self.parentSubChildBranchPairs(vesselBranchTree, idPositionDict, startNode=child)

    return branchList
