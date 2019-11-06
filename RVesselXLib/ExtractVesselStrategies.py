import slicer

from RVesselXModuleLogic import RVesselXModuleLogic


class IExtractVesselStrategy(object):
  """
  Interface object for vessel volume extraction from source vessel branch tree and associated markup.
  """

  def displayName(self):
    """

    Returns
    -------
    str
      Name of the strategy displayed in the UI
    """
    return ""

  def extractVesselVolumeFromVesselBranchTree(self, vesselBranchTree, vesselBranchMarkup, logic):
    """
    Extract vessel volume and model from input data. The data are expected to be unchanged when the algorithm has run.

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


def getMarkupIdPositionDictionary(markup):
  """
  Parameters
  ----------
  markup : vtkMRMLMarkupsFiducialNode

  Returns
  -------
  Dict[str, List[float]]
    Dictionary containing the node ids contained in the markup node and its associated positions
  """
  markupDict = {}
  for i in range(markup.GetNumberOfFiducials()):
    nodeId = markup.GetNthFiducialLabel(i)
    nodePosition = [0] * 3
    markup.GetNthFiducialPosition(i, nodePosition)
    markupDict[nodeId] = nodePosition
  return markupDict


def mergeVolumes(volumes, volName):
  # Extract list of volumes as list of np arrays
  npVolumes = [slicer.util.arrayFromVolume(volume).astype(int) for volume in volumes]

  # Merge all volumes in one
  mergedVol = npVolumes[0]
  for i in range(1, len(npVolumes)):
    mergedVol |= npVolumes[i]

  # Create output volume in slicer
  outVol = RVesselXModuleLogic.createLabelMapVolumeNodeBasedOnModel(volumes[0], volName)
  slicer.util.updateVolumeFromArray(outVol, mergedVol)
  return outVol, RVesselXModuleLogic.createVolumeBoundaryModel(outVol, volName + "Model", threshold=1)


class ExtractAllVesselsInOneGoStrategy(IExtractVesselStrategy):
  def displayName(self):
    return "Extract volume in one go"

  def extractVesselVolumeFromVesselBranchTree(self, vesselBranchTree, vesselBranchMarkup, logic):
    """
    Extract vessel volume and model from input data. The data are expected to be unchanged when the algorithm has run.
    Strategy uses VMTK on all markup points at once to extract data.

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


class ExtractOneVesselPerBranch(IExtractVesselStrategy):
  def displayName(self):
    return "Extract one volume per branch"

  def extractVesselVolumeFromVesselBranchTree(self, vesselBranchTree, vesselBranchMarkup, logic):
    """
    Extract vessel volume and model from input data. The data are expected to be unchanged when the algorithm has run.
    Strategy uses VMTK on all markup points at once to extract data.

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
    nodeList = vesselBranchTree.getNodeList()
    branchList = []

    for node in nodeList:
      startPos = idPositionDict[node]
      for child in vesselBranchTree.getChildrenNodeId(node):
        endPos = idPositionDict[child]
        branchList.append((startPos, endPos))

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
