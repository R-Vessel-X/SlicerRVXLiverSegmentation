import slicer
import vtk
from slicer.ScriptedLoadableModule import ScriptedLoadableModuleLogic

from RVesselXLib.RVesselXUtils import raiseValueErrorIfInvalidType
from Vessel import Vessel


class VMTKModule(object):
  """Helper class for loading VMTK module and accessing VMTK Module logic from RVessel module
  """

  @staticmethod
  def tryToLoad():
    """Try to load every VMTK widgets in slicer.

    Returns
    -------
      list of VMTK modules where loading failed. Empty list if success
    """
    notFound = []
    for moduleName in ["VesselnessFiltering", "LevelSetSegmentation", "CenterlineComputation"]:
      try:
        slicer.util.getModule(moduleName).widgetRepresentation()
      except AttributeError:
        notFound.append(moduleName)

    return notFound

  @staticmethod
  def getVesselnessFilteringLogic():
    return slicer.modules.VesselnessFilteringWidget.logic

  @staticmethod
  def getLevelSetSegmentationLogic():
    return VMTKModule.getLevelSetSegmentationWidget().logic

  @staticmethod
  def getLevelSetSegmentationWidget():
    return slicer.modules.LevelSetSegmentationWidget

  @staticmethod
  def getCenterlineComputationLogic():
    return slicer.modules.CenterlineComputationWidget.logic


class VesselnessFilterParameters(object):
  """Object holding the parameters for the vesselness filter algorithm. Init constructs vesselness filter with default
  parameters
  """

  def __init__(self):
    self.minimumDiameter = 1
    self.maximumDiameter = 7
    self.suppressPlatesPercent = 10
    self.suppressBlobsPercent = 10
    self.vesselContrast = 100


class IRVesselXModuleLogic(object):
  """
  Interface definition for Logic module.
  """

  def __init__(self):
    self._vesselnessFilterParam = VesselnessFilterParameters()

  def setInputVolume(self, inputVolume):
    pass

  def extractVessel(self, startPoint, endPoint):
    return None

  def updateVesselnessFilter(self, startPoint):
    pass

  @property
  def vesselnessFilterParameters(self):
    return self._vesselnessFilterParam

  @vesselnessFilterParameters.setter
  def vesselnessFilterParameters(self, value):
    self._vesselnessFilterParam = value


class RVesselXModuleLogic(ScriptedLoadableModuleLogic, IRVesselXModuleLogic):
  def __init__(self, parent=None):
    ScriptedLoadableModuleLogic.__init__(self, parent)
    IRVesselXModuleLogic.__init__(self)

    notFound = VMTKModule.tryToLoad()
    if notFound:
      errorMsg = "Failed to load the following VMTK Modules : %s\nPlease make sure VMTK is installed." % notFound
      slicer.util.errorDisplay(errorMsg)

    self._inputVolume = None
    self._vesselnessVolumes = {}

  def setInputVolume(self, inputVolume):
    """
    Parameters
    ----------
    inputVolume: vtkMRMLScalarVolumeNode, Volume on which segmentation will be done
    """
    raiseValueErrorIfInvalidType(inputVolume=(inputVolume, "vtkMRMLScalarVolumeNode"))

    if self._inputVolume != inputVolume:
      self._inputVolume = inputVolume

  @staticmethod
  def _addToScene(node):
    """Add input node to scene and return node

    Parameters
    ----------
    node: vtkMRMLNode
      Node to add to scene

    Returns
    -------
    node after having added it to scene
    """
    outputNode = slicer.mrmlScene.AddNode(node)
    outputNode.CreateDefaultDisplayNodes()
    return outputNode

  @staticmethod
  def _createFiducialNode(name, *positions):
    """Creates a vtkMRMLMarkupsFiducialNode with one point at given position and with given name

    Parameters
    ----------
    positions : list of list of positions
      size 3 position list with positions for created fiducial point
    name : str
      Base for unique name given to the output node

    Returns
    -------
    vtkMRMLMarkupsFiducialNode with one point at given position
    """
    fiducialPoint = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
    fiducialPoint.UnRegister(None)
    fiducialPoint.SetName(slicer.mrmlScene.GetUniqueNameByString(name))
    for position in positions:
      fiducialPoint.AddFiducialFromArray(position)
    return slicer.mrmlScene.AddNode(fiducialPoint)

  @staticmethod
  def createLabelMapVolumeNodeBasedOnModel(modelVolume, volumeName):
    """Creates new LabelMapVolume node which reproduces the input node orientation, spacing, and origins

    Parameters
    ----------
    modelVolume : vtkMRMLLabelMapVolumeNode
      Volume from which orientation, spacing and origin will be deduced
    volumeName: str
      base name for the volume when it will be added to slicer scene. A unique name will be derived
      from this base name (ie : adding number indices in case the volume is already present in the scene)

    Returns
    -------
    vtkMRMLLabelMapVolumeNode
      New Label map volume added to the scene
    """
    newLabelMapNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLLabelMapVolumeNode")
    newLabelMapNode.UnRegister(None)
    newLabelMapNode.CopyOrientation(modelVolume)
    newLabelMapNode.SetName(slicer.mrmlScene.GetUniqueNameByString(volumeName))
    return RVesselXModuleLogic._addToScene(newLabelMapNode)

  @staticmethod
  def _createModelNode(modelName):
    """Creates new Model node with given input volume Name

    Parameters
    ----------
    modelName: str
      base name for the model when it will be added to slicer scene. A unique name will be derived
      from this base name (ie : adding number indices in case the model is already present in the scene)

    Returns
    -------
    vtkMRMLModelNode
      New model added to the scene
    """
    newModelNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
    newModelNode.UnRegister(None)
    newModelNode.SetName(slicer.mrmlScene.GetUniqueNameByString(modelName))
    return RVesselXModuleLogic._addToScene(newModelNode)

  @staticmethod
  def _getFiducialPositions(fiducialNode):
    """ Extracts positions from input fiducial node and returns it as array of positions

    Parameters
    ----------
    fiducialNode : vtkMRMLMarkupsFiducialNode
      FiducialNode from which we want the coordinates

    Returns
    -------
    List of arrays[3] of fiducial positions
    """
    positions = []
    for i in range(fiducialNode.GetNumberOfFiducials()):
      pos = [0, 0, 0]
      fiducialNode.GetNthFiducialPosition(i, pos)
      positions.append(pos)
    return positions

  def _applyVesselnessFilter(self, sourceVolume, startPoint):
    """Apply VMTK VesselnessFilter to source volume given start point. Returns ouput volume with vesselness information

    Parameters
    ----------
    sourceVolume: vtkMRMLScalarVolumeNode
      Volume which will be labeled with vesselness information
    startPoint: vtkMRMLMarkupsFiducialNode or None
      Start point of the vessel. Gives indication on the target diameter of the vessel which will be
      filtered by the method.
      If start point is None, vessel contrast and maximum diameters will be read from vesselness parameters.

    Returns
    -------
    outputVolume : vtkMRMLLabelMapVolumeNode
      Volume with vesselness information
    """
    # Type checking
    raiseValueErrorIfInvalidType(sourceVolume=(sourceVolume, "vtkMRMLScalarVolumeNode"))
    if startPoint is None:
      isContrastCalculated = False
    else:
      isContrastCalculated = True
      raiseValueErrorIfInvalidType(startPoint=(startPoint, "vtkMRMLMarkupsFiducialNode"))

    # Get module logic from VMTK Vesselness Filtering module
    vesselnessLogic = VMTKModule.getVesselnessFilteringLogic()

    # Create output node
    vesselnessFiltered = RVesselXModuleLogic.createLabelMapVolumeNodeBasedOnModel(sourceVolume, "VesselnessFiltered")

    if isContrastCalculated:
      # Extract diameter size from start point position
      vesselPositionRas = [0, 0, 0]
      startPoint.GetNthFiducialPosition(0, vesselPositionRas)
      vesselPositionIJK = vesselnessLogic.getIJKFromRAS(sourceVolume, vesselPositionRas)
      self._vesselnessFilterParam.maximumDiameter = vesselnessLogic.getDiameter(sourceVolume.GetImageData(),
                                                                                vesselPositionIJK)
      # Extract contrast from seed
      self._vesselnessFilterParam.vesselContrast = vesselnessLogic.calculateContrastMeasure(sourceVolume.GetImageData(),
                                                                                            vesselPositionIJK,
                                                                                            self._vesselnessFilterParam.maximumDiameter)
    maximumVesselDiameter = self._vesselnessFilterParam.maximumDiameter
    contrastMeasure = self._vesselnessFilterParam.vesselContrast

    # Calculate alpha and beta parameters from suppressPlates and suppressBlobs parameters
    alpha = vesselnessLogic.alphaFromSuppressPlatesPercentage(self._vesselnessFilterParam.suppressPlatesPercent)
    beta = vesselnessLogic.betaFromSuppressBlobsPercentage(self._vesselnessFilterParam.suppressBlobsPercent)

    # Scale minimum and maximum diameters with volume spacing
    minimumDiameter = self._vesselnessFilterParam.minimumDiameter * min(sourceVolume.GetSpacing())
    maximumDiameter = maximumVesselDiameter * min(sourceVolume.GetSpacing())

    # Compute vesselness volume
    vesselnessLogic.computeVesselnessVolume(sourceVolume, vesselnessFiltered, maximumDiameterMm=maximumDiameter,
                                            minimumDiameterMm=minimumDiameter, alpha=alpha, beta=beta,
                                            contrastMeasure=contrastMeasure)

    return vesselnessFiltered

  @staticmethod
  def _applyLevelSetSegmentationFromNodePositions(sourceVolume, vesselnessVolume, seedsPositions, endPositions):
    """ Apply VMTK LevelSetSegmentation to vesselnessVolume given input seed positions and end positions

    Returns label Map Volume with segmentation information and model containing marching cubes iso surface extraction

    Parameters
    ----------
    sourceVolume : vtkMRMLScalarVolumeNode
      Original volume (before vesselness filter
    vesselnessVolume : vtkMRMLLabelMapVolumeNode
      Volume after filtering by vesselness filter
    seedsPositions : List[List[float]]
      Seed positions for the vessel
    endPositions : List[List[float]]
      End positions for the vessel

    Returns
    -------
    LevelSetSeeds : vtkMRMLMarkupsFiducialNode
      Nodes used as seeds during level set segmentation (aggregate of seedsPositions and endPositions)
    LevelSetStoppers : vtkMRMLMarkupsFiducialNode
      Nodes used as stoppers during level set segmentation (aggregate of start point and end point)
    LevelSetSegmentation : vtkMRMLLabelMapVolumeNode
      segmentation volume output
    LevelSetModel : vtkMRMLModelNode
      Model after marching cubes on the segmentation data
    """
    # Type checking
    raiseValueErrorIfInvalidType(sourceVolume=(sourceVolume, "vtkMRMLScalarVolumeNode"),
                                 vesselnessVolume=(vesselnessVolume, "vtkMRMLLabelMapVolumeNode"))

    # Get module logic from VMTK LevelSetSegmentation
    segmentationWidget = VMTKModule.getLevelSetSegmentationWidget()
    segmentationLogic = VMTKModule.getLevelSetSegmentationLogic()

    # Create output volume node
    outVolume = RVesselXModuleLogic.createLabelMapVolumeNodeBasedOnModel(sourceVolume, "LevelSetSegmentation")

    # Copy paste code from LevelSetSegmentation start method
    # https://github.com/vmtk/SlicerExtension-VMTK/blob/master/LevelSetSegmentation/LevelSetSegmentation.py

    # Aggregate start point and end point as seeds for vessel extraction
    allSeedsPositions = seedsPositions + endPositions

    # now we need to convert the fiducials to vtkIdLists
    seedsNodes = RVesselXModuleLogic._createFiducialNode("LevelSetSegmentationSeeds", *allSeedsPositions)
    stoppersNodes = RVesselXModuleLogic._createFiducialNode("LevelSetSegmentationStoppers", *endPositions)
    seeds = segmentationWidget.convertFiducialHierarchyToVtkIdList(seedsNodes, vesselnessVolume)
    stoppers = segmentationWidget.convertFiducialHierarchyToVtkIdList(stoppersNodes,
                                                                      vesselnessVolume) if stoppersNodes else vtk.vtkIdList()

    # the input image for the initialization
    inputImage = vtk.vtkImageData()
    inputImage.DeepCopy(vesselnessVolume.GetImageData())

    # initialization
    initImageData = vtk.vtkImageData()

    # evolution
    evolImageData = vtk.vtkImageData()

    # perform the initialization
    currentScalarRange = inputImage.GetScalarRange()
    minimumScalarValue = round(currentScalarRange[0], 0)
    maximumScalarValue = round(currentScalarRange[1], 0)

    initImageData.DeepCopy(
      segmentationLogic.performInitialization(inputImage, minimumScalarValue, maximumScalarValue, seeds, stoppers,
                                              'collidingfronts'))

    if not initImageData.GetPointData().GetScalars():
      # something went wrong, the image is empty
      raise ValueError("Segmentation failed - the output was empty...")

    # no preview, run the whole thing! we never use the vesselness node here, just the original one
    inflationDefaultValue = 0
    curvatureDefaultValue = 70
    attractionDefaultValue = 50
    iterationDefaultValue = 10
    evolImageData.DeepCopy(
      segmentationLogic.performEvolution(sourceVolume.GetImageData(), initImageData, iterationDefaultValue,
                                         inflationDefaultValue, curvatureDefaultValue, attractionDefaultValue,
                                         'geodesic'))

    # create segmentation labelMap
    labelMap = vtk.vtkImageData()
    labelMap.DeepCopy(segmentationLogic.buildSimpleLabelMap(evolImageData, 5, 0))

    # propagate the label map to the node
    outVolume.SetAndObserveImageData(labelMap)

    # currentVesselnessNode
    slicer.util.setSliceViewerLayers(background=sourceVolume, foreground=vesselnessVolume, label=outVolume,
                                     foregroundOpacity=0.1)

    # Construct model boundary mesh
    outModel = RVesselXModuleLogic.createVolumeBoundaryModel(outVolume, "LevelSetSegmentationModel", evolImageData)

    return seedsNodes, stoppersNodes, outVolume, outModel

  @staticmethod
  def createVolumeBoundaryModel(sourceVolume, modelName, imageData=None, threshold=0.0):
    raiseValueErrorIfInvalidType(sourceVolume=(sourceVolume, "vtkMRMLScalarVolumeNode"))
    if imageData is None:
      imageData = sourceVolume.GetImageData()

    raiseValueErrorIfInvalidType(imageData=(imageData, vtk.vtkImageData))

    # we need the ijkToRas transform for the marching cubes call
    ijkToRasMatrix = vtk.vtkMatrix4x4()
    sourceVolume.GetIJKToRASMatrix(ijkToRasMatrix)

    # generate 3D model and call marching cubes
    modelPolyData = vtk.vtkPolyData()
    modelPolyData.DeepCopy(
      VMTKModule.getLevelSetSegmentationLogic().marchingCubes(imageData, ijkToRasMatrix, threshold))

    # Create model node and associate model poly data
    modelNode = RVesselXModuleLogic._createModelNode(modelName)
    modelNode.SetAndObservePolyData(modelPolyData)
    modelNode.CreateDefaultDisplayNodes()

    return modelNode

  @staticmethod
  def _applyLevelSetSegmentation(sourceVolume, vesselnessVolume, startPoint, endPoint):
    """ Apply VMTK LevelSetSegmentation to vesselnessVolume given input startPoint and endPoint.

    Returns label Map Volume with segmentation information and model containing marching cubes iso surface extraction

    Parameters
    ----------
    sourceVolume : vtkMRMLScalarVolumeNode
      Original volume (before vesselness filter
    vesselnessVolume : vtkMRMLLabelMapVolumeNode
      Volume after filtering by vesselness filter
    startPoint : vtkMRMLMarkupsFiducialNode
      Start point for the vessel
    endPoint : vtkMRMLMarkupsFiducialNode
      End point for the vessel

    Returns
    -------
    LevelSetSeeds : vtkMRMLMarkupsFiducialNode
      Nodes used as seeds during level set segmentation (aggregate of start point and end point)
    LevelSetSegmentation : vtkMRMLLabelMapVolumeNode
      segmentation volume output
    LevelSetModel : vtkMRMLModelNode
      Model after marching cubes on the segmentation data
    """
    # Type checking
    raiseValueErrorIfInvalidType(sourceVolume=(sourceVolume, "vtkMRMLScalarVolumeNode"),
                                 vesselnessVolume=(vesselnessVolume, "vtkMRMLLabelMapVolumeNode"),
                                 startPoint=(startPoint, "vtkMRMLMarkupsFiducialNode"),
                                 endPoint=(endPoint, "vtkMRMLMarkupsFiducialNode"))

    startPos = RVesselXModuleLogic._getFiducialPositions(startPoint)
    endPos = RVesselXModuleLogic._getFiducialPositions(endPoint)
    seedsNodes, stoppersNodes, outVolume, outModel = RVesselXModuleLogic._applyLevelSetSegmentationFromNodePositions(
      sourceVolume, vesselnessVolume, startPos, endPos)
    return seedsNodes, outVolume, outModel

  @staticmethod
  def _closestPointOnSurfaceAsIdList(surface, point):
    pointList = vtk.vtkIdList()

    pointLocator = vtk.vtkPointLocator()
    pointLocator.SetDataSet(surface)
    pointLocator.BuildLocator()

    sourceId = pointLocator.FindClosestPoint(point)
    pointList.InsertNextId(sourceId)
    return pointList

  @staticmethod
  def _applyCenterlineFilter(levelSetSegmentationModel, startPoint, endPoint):
    """ Extracts centerline from input level set segmentation model (ie : vessel polyData) and start and end points

    Parameters
    ----------
    levelSetSegmentationModel : vtkMRMLModelNode
      Result from LevelSetSegmentation representing outer vessel mesh
    startPoint : vtkMRMLMarkupsFiducialNode
      Start point for the vessel
    endPoint : vtkMRMLMarkupsFiducialNode
      End point for the vessel

    Returns
    -------
    centerline : vtkMRMLModelNode
      Contains center line vtkPolyData extracted from input vessel model
    centerlineVoronoi : vtkMRMLModelNode
      Contains voronoi model used when extracting center line
    """
    # Type checking
    raiseValueErrorIfInvalidType(levelSetSegmentationModel=(levelSetSegmentationModel, "vtkMRMLModelNode"),
                                 startPoint=(startPoint, "vtkMRMLMarkupsFiducialNode"),
                                 endPoint=(endPoint, "vtkMRMLMarkupsFiducialNode"))

    # Get logic from VMTK center line computation module
    centerLineLogic = VMTKModule.getCenterlineComputationLogic()

    # Extract mesh and source and target point lists from input data
    segmentationMesh = levelSetSegmentationModel.GetPolyData()
    sourceIdList = RVesselXModuleLogic._closestPointOnSurfaceAsIdList(segmentationMesh,
                                                                      RVesselXModuleLogic._getFiducialPositions(
                                                                        startPoint)[0])
    targetIdList = RVesselXModuleLogic._closestPointOnSurfaceAsIdList(segmentationMesh,
                                                                      RVesselXModuleLogic._getFiducialPositions(
                                                                        endPoint)[0])

    # Calculate center line poly data
    centerLinePolyData, voronoiPolyData = centerLineLogic.computeCenterlines(segmentationMesh, sourceIdList,
                                                                             targetIdList)

    # Create output voronoi model and centerline model
    centerLineModel = RVesselXModuleLogic._createModelNode("CenterLineModel")
    voronoiModel = RVesselXModuleLogic._createModelNode("VoronoiModel")

    centerLineModel.SetAndObservePolyData(centerLinePolyData)
    voronoiModel.SetAndObservePolyData(voronoiPolyData)

    return centerLineModel, voronoiModel

  @staticmethod
  def _isPointValid(point):
    return (point is not None) and (isinstance(point, slicer.vtkMRMLMarkupsFiducialNode)) and (
        point.GetNumberOfFiducials() > 0)

  @staticmethod
  def _areExtremitiesValid(startPoint, endPoint):
    return RVesselXModuleLogic._isPointValid(startPoint) and RVesselXModuleLogic._isPointValid(endPoint)

  def updateVesselnessFilter(self, startPoint):
    # Early return in case the inputs is not properly defined
    if self._inputVolume is None:
      return

    self._vesselnessVolumes[self._inputVolume] = self._applyVesselnessFilter(self._inputVolume, startPoint)

  def _hasVesselnessForInput(self):
    return self._inputVolume in self._vesselnessVolumes.keys()

  def _updateVesselnessVolume(self, startPoint):
    import time
    if not self._hasVesselnessForInput():
      self.updateVesselnessFilter(startPoint)
      time.sleep(1)  # Short sleep for this thread to enable volume to be updated

  def extractVesselVolumeFromPosition(self, seedsPositions, endPositions):
    self._updateVesselnessVolume(None)
    return self._applyLevelSetSegmentationFromNodePositions(self._inputVolume,
                                                            self._vesselnessVolumes[self._inputVolume], seedsPositions,
                                                            endPositions)

  def extractVessel(self, startPoint, endPoint):
    """ Extracts vessel from source volume, given start point and end point

    Parameters
    ----------
    startPoint: vtkMRMLMarkupsFiducialNode
      Start point for the vessel
    endPoint: vtkMRMLMarkupsFiducialNode
      End point for the vessel

    Returns
    -------
    vessel : Vessel or None
      extracted vessel with associated informations if inputs valid, else None
    """
    # Early return in case the inputs are not properly defined
    if self._inputVolume is None or not self._areExtremitiesValid(startPoint, endPoint):
      return None

    # Create vessel which will hold every information of the vessel extracted in logic module
    vessel = Vessel()
    vessel.setExtremities(startPoint, endPoint)

    # Update vesselness filter if it was never calculated for current input volume
    self._updateVesselnessVolume(startPoint)

    vesselnessVolume = self._vesselnessVolumes[self._inputVolume]
    vessel.setVesselnessVolume(vesselnessVolume)

    # Call levelSetSegmentation
    levelSetSeeds, levelSetVolume, levelSetModel = self._applyLevelSetSegmentation(self._inputVolume, vesselnessVolume,
                                                                                   startPoint, endPoint)
    vessel.setSegmentation(seeds=levelSetSeeds, volume=levelSetVolume, model=levelSetModel)

    # Extract centerpoint
    centerline, voronoiModel = self._applyCenterlineFilter(levelSetModel, startPoint, endPoint)
    vessel.setCenterline(centerline=centerline, voronoiModel=voronoiModel)

    return vessel
