import slicer

from RVesselXLib import removeNodeFromMRMLScene
from .RVesselXModuleLogic import RVesselXModuleLogic
from .RVesselXUtils import getMarkupIdPositionDictionary, createLabelMapVolumeNodeBasedOnModel


class VesselSeedPoints(object):
  """Helper class containing the different seed points to use for vessel VMTK extraction.
  """

  def __init__(self, idPositionDict, pointIdList=None):
    """
    Parameters
    ----------
    idPositionDict: Dict[str, List[Float]]
      Dictionary with nodeId as key and node position as value
    pointIdList: List[str] or None
      List of points to add to the vessel seed points
    """
    self._idPositionDict = idPositionDict
    self._pointList = []
    self._pointIdList = []

    if pointIdList is not None:
      for pointId in pointIdList:
        self.appendPoint(pointId)

  def appendPoint(self, pointId):
    """Adds input point id to the current seed list.

    Parameters
    ----------
    pointId: str - Id of the point to add to list
    """
    self._pointIdList.append(pointId)
    self._pointList.append(self._idPositionDict[pointId])

  def isValid(self):
    return len(self._pointList) > 1

  def getSeedPositions(self):
    """
    Returns
    -------
    List[List[float]] - List containing all the nodes before last in the seed list if valid else empty list.
    """
    return self._pointList[:-1] if self.isValid() else []

  def getStopperPositions(self):
    """
    Returns
    -------
    List[List[float]] - List containing last node position in the seed list if valid else empty list.
    """
    return [self._pointList[-1]] if self.isValid() else []

  def copy(self):
    """
    Returns
    -------
    VesselSeedPoints - Deep copy of current object
    """
    copy = VesselSeedPoints(self._idPositionDict.copy())
    copy._pointIdList = list(self._pointIdList)
    copy._pointList = list(self._pointList)
    return copy

  @staticmethod
  def combine(first, second):
    """Combine two VesselSeedPoints into one VesselSeedPoints. Second vessel seed points will be added to first list.
    To be correctly combined, first last id must correspond to second first id. Else method will raise a ValueError.

    Parameters
    ----------
    first: VesselSeedPoints
      First list of vessel points
    second: VesselSeedPoints
      Second list of vessel points. List will be added after first list.

    Returns
    -------
    VesselSeedPoints combining both lists.

    Raises
    ------
    ValueError if either first or second is Invalid or if first last point doesn't correspond to second first point.
    """
    if not isinstance(first, VesselSeedPoints) or not isinstance(second, VesselSeedPoints):
      raise ValueError("Combine expects %s types. Got %s and %s types" % (
        VesselSeedPoints.__name__, type(first).__name__, type(second).__name__))

    if not first.isValid() or not second.isValid() or first.lastPointId() != second.firstPointId():
      raise ValueError("Cannot combine vessel seed points %s and %s" % (first, second))

    combined = first.copy()
    combined._pointList += second._pointList[1:]
    combined._pointIdList += second._pointIdList[1:]
    return combined

  def firstPointId(self):
    """
    Returns
    -------
    str or None
      First point id in the vessel seeds
    """
    return self._pointIdList[0] if self.isValid() else None

  def lastPointId(self):
    """
    Returns
    -------
    str or None
      Last point is in the vessel seeds
    """
    return self._pointIdList[-1] if self.isValid() else None

  def __repr__(self):
    return str(self._pointIdList)

  def __eq__(self, other):
    if not isinstance(other, VesselSeedPoints):
      return False
    else:
      return (self._pointIdList, self._pointList) == (other._pointIdList, other._pointList)

  def __ne__(self, other):
    return not self == other

  def __le__(self, other):
    return self.getSeedPositions() + self.getStopperPositions() <= other.getSeedPositions() + other.getStopperPositions()

  def __lt__(self, other):
    return self.getSeedPositions() + self.getStopperPositions() < other.getSeedPositions() + other.getStopperPositions()

  def __ge__(self, other):
    return not self.__lt__(other)

  def __gt__(self, other):
    return not self.__le__(other)


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
    removeNodeFromMRMLScene(seedsNodes)
    removeNodeFromMRMLScene(stoppersNodes)
    return outVolume, outModel


class ExtractVesselFromVesselSeedPointsStrategy(IExtractVesselStrategy):
  """Base class for strategies using VMTK on multiple start + end points and aggregating results as one volume.
  deriving classes must implement a function returning a list of node pairs constructed from vessel tree and node id
  position dictionary
  """

  def constructVesselSeedList(self, vesselBranchTree, idPositionDict):
    """
    Parameters
    ----------
    vesselBranchTree: VesselBranchTree
      Tree containing the hierarchy of the markups
    idPositionDict: Dict[str,List[float]]
      Dictionary with nodeId as key and node position as value

    Returns
    -------
    List[VesselSeedPoints] - List of VesselSeedPoints to extract using VMTK
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
    vesselSeedList = self.constructVesselSeedList(vesselBranchTree, idPositionDict)

    volumes = []
    elementsToRemoveFromScene = []
    for vesselSeeds in vesselSeedList:
      seedsNodes, stoppersNodes, outVolume, outModel = logic.extractVesselVolumeFromPosition(
        vesselSeeds.getSeedPositions(), vesselSeeds.getStopperPositions())
      elementsToRemoveFromScene.append(seedsNodes)
      elementsToRemoveFromScene.append(stoppersNodes)
      elementsToRemoveFromScene.append(outModel)
      elementsToRemoveFromScene.append(outVolume)
      volumes.append(outVolume)

    outVolume, outModel = mergeVolumes(volumes, "levelSetSegmentation")
    for volume in elementsToRemoveFromScene:
      removeNodeFromMRMLScene(volume)

    return outVolume, outModel


class ExtractOneVesselPerParentChildNode(ExtractVesselFromVesselSeedPointsStrategy):
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

  def constructVesselSeedList(self, vesselBranchTree, idPositionDict):
    """
    Parameters
    ----------
    vesselBranchTree: VesselBranchTree
      Tree containing the hierarchy of the markups
    idPositionDict: Dict[str,List[float]]
      Dictionary with nodeId as key and node position as value

    Returns
    -------
    List[VesselSeedPoints] - List of VesselSeedPoints to extract using VMTK
    """

    # Extract all the branches in the tree and return as branch list
    nodeList = vesselBranchTree.getNodeList()
    vesselSeedList = []

    for node in nodeList:
      for child in vesselBranchTree.getChildrenNodeId(node):
        vesselSeedList.append(VesselSeedPoints(idPositionDict, [node, child]))
    return vesselSeedList


class ExtractOneVesselPerParentAndSubChildNode(ExtractVesselFromVesselSeedPointsStrategy):
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

  def constructVesselSeedList(self, vesselBranchTree, idPositionDict):
    """
    Parameters
    ----------
    vesselBranchTree: VesselBranchTree
      Tree containing the hierarchy of the markups
    idPositionDict: Dict[str,List[float]]
      Dictionary with nodeId as key and node position as value

    Returns
    -------
    List[VesselSeedPoints] - List of VesselSeedPoints to extract using VMTK
    """
    return self.parentSubChildBranchPairs(vesselBranchTree, idPositionDict)

  def parentSubChildBranchPairs(self, vesselBranchTree, idPositionDict, startNode=None):
    # Initialize vessel seed list
    vesselSeedList = []

    # Initialize start node as tree root if startNode not provided
    isStartNodeRoot = False
    if startNode is None:
      startNode = vesselBranchTree.getRootNodeId()
      isStartNodeRoot = True

    for child in vesselBranchTree.getChildrenNodeId(startNode):
      # Construct startNode + subChildren pairs
      subChildren = vesselBranchTree.getChildrenNodeId(child)
      for subChild in subChildren:
        vesselSeedList.append(VesselSeedPoints(idPositionDict, [startNode, subChild]))

      # Special case if starting from root node and current node doesn't have children (to avoid missing the point)
      # otherwise, the node will be contained in a previous parent + subChild pair
      if len(subChildren) == 0 and isStartNodeRoot:
        vesselSeedList.append(VesselSeedPoints(idPositionDict, [startNode, child]))

      # Call recursively for children
      vesselSeedList += self.parentSubChildBranchPairs(vesselBranchTree, idPositionDict, startNode=child)

    return vesselSeedList


class ExtractOneVesselPerBranch(ExtractVesselFromVesselSeedPointsStrategy):
  """Strategy uses continuous nodes without parents to extract VMTK runs

  Example :
    n0
      |_ n10
          |_ n20
              |_n30
              |_n31
                  |_ n40
                        |_ n50
              |_n32

  Exp VMTK runs :
    [n0, n10, n20]
    [n20, n30]
    [n20, n31, n40, n50]
    [n20, n32]
  """

  def constructVesselSeedList(self, vesselBranchTree, idPositionDict):
    """
    Parameters
    ----------
    vesselBranchTree: VesselBranchTree
      Tree containing the hierarchy of the markups
    idPositionDict: Dict[str,List[float]]
      Dictionary with nodeId as key and node position as value

    Returns
    -------
    List[VesselSeedPoints] - List of VesselSeedPoints to extract using VMTK
    """
    return self.constructBranchFromRoot(vesselBranchTree, idPositionDict)

  def constructBranchFromRoot(self, vesselBranchTree, idPositionDict, startNode=None):
    # Initialize vessel seed list
    vesselSeedList = []

    # Initialize start node as tree root if startNode not provided
    if startNode is None:
      startNode = vesselBranchTree.getRootNodeId()

    for child in vesselBranchTree.getChildrenNodeId(startNode):
      seedPoints = VesselSeedPoints(idPositionDict)
      seedPoints.appendPoint(startNode)
      seedPoints.appendPoint(child)

      # Append children until child reaches leaf or a child with more than one sub child
      subChild = child
      while len(vesselBranchTree.getChildrenNodeId(subChild)) == 1:
        subChild = vesselBranchTree.getChildrenNodeId(subChild)[0]
        seedPoints.appendPoint(subChild)

      # Call recursively for reached leafs
      vesselSeedList.append(seedPoints)
      vesselSeedList += self.constructBranchFromRoot(vesselBranchTree, idPositionDict, startNode=subChild)

    return vesselSeedList
