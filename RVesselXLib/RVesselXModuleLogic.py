import math

import numpy as np
import slicer
from slicer.ScriptedLoadableModule import ScriptedLoadableModuleLogic
import vtk

from .RVesselXUtils import raiseValueErrorIfInvalidType, createLabelMapVolumeNodeBasedOnModel, createFiducialNode, \
  createModelNode, getFiducialPositions, createVolumeNodeBasedOnModel, removeNodeFromMRMLScene, cropSourceVolume, \
  cloneSourceVolume


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
    self.suppressPlatesPercent = 50
    self.suppressBlobsPercent = 50
    self.vesselContrast = 5
    self.roiGrowthFactor = 1.2
    self.useROI = True
    self.minROIExtent = 20

  def asTuple(self):
    return (self.minimumDiameter, self.maximumDiameter, self.suppressPlatesPercent, self.suppressBlobsPercent,
            self.vesselContrast, self.roiGrowthFactor, self.useROI)


class LevelSetParameters(object):
  """
  Object holding the parameters for level set segmentation algorithm. Init construct level set with default parameters
  """

  def __init__(self):
    self.inflation = 0
    self.curvature = 70
    self.attraction = 50
    self.iterationNumber = 10


class IRVesselXModuleLogic(object):
  """Interface definition for Logic module.
  """

  def __init__(self):
    self._vesselnessFilterParam = VesselnessFilterParameters()

  def setInputVolume(self, inputVolume):
    pass

  def updateVesselnessVolume(self, nodePositions):
    pass

  @property
  def vesselnessFilterParameters(self):
    return self._vesselnessFilterParam

  @vesselnessFilterParameters.setter
  def vesselnessFilterParameters(self, value):
    self._vesselnessFilterParam = value


class RVesselXModuleLogic(ScriptedLoadableModuleLogic, IRVesselXModuleLogic):
  """Class regrouping the logic methods for the plugin. Uses the VMTK algorithm for most of its functionality.
  Holds a map of previously calculated vesselness volumes to avoid reprocessing it when extracting liver vessels.
  """

  def __init__(self, parent=None):
    ScriptedLoadableModuleLogic.__init__(self, parent)
    IRVesselXModuleLogic.__init__(self)

    notFound = VMTKModule.tryToLoad()
    if notFound:
      errorMsg = "Failed to load the following VMTK Modules : %s\nPlease make sure VMTK is installed." % notFound
      slicer.util.errorDisplay(errorMsg)

    self._inputVolume = None
    self._croppedInputVolume = None
    self._vesselnessVolume = None
    self._inputRoi = None
    self.levelSetParameters = LevelSetParameters()

  def setInputVolume(self, inputVolume):
    """
    Parameters
    ----------
    inputVolume: vtkMRMLScalarVolumeNode, Volume on which segmentation will be done
    """
    raiseValueErrorIfInvalidType(inputVolume=(inputVolume, "vtkMRMLScalarVolumeNode"))

    if self._inputVolume != inputVolume:
      self._inputVolume = inputVolume

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
    vesselnessFiltered = createVolumeNodeBasedOnModel(sourceVolume, "VesselnessFiltered", "vtkMRMLScalarVolumeNode")

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
  def _applyLevelSetSegmentationFromNodePositions(sourceVolume, vesselnessVolume, seedsPositions, endPositions,
                                                  levelSetParameters):
    """ Apply VMTK LevelSetSegmentation to vesselnessVolume given input seed positions and end positions

    Returns label Map Volume with segmentation information and model containing marching cubes iso surface extraction

    Parameters
    ----------
    sourceVolume : vtkMRMLScalarVolumeNode
      Original volume (before vesselness filter
    vesselnessVolume : vtkMRMLScalarVolumeNode
      Volume after filtering by vesselness filter
    seedsPositions : List[List[float]]
      Seed positions for the vessel
    endPositions : List[List[float]]
      End positions for the vessel
    levelSetParameters : LevelSetParameters

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
                                 vesselnessVolume=(vesselnessVolume, "vtkMRMLScalarVolumeNode"))

    # Get module logic from VMTK LevelSetSegmentation
    segmentationWidget = VMTKModule.getLevelSetSegmentationWidget()
    segmentationLogic = VMTKModule.getLevelSetSegmentationLogic()

    # Create output volume node
    outVolume = createLabelMapVolumeNodeBasedOnModel(sourceVolume, "LevelSetSegmentation")

    # Copy paste code from LevelSetSegmentation start method
    # https://github.com/vmtk/SlicerExtension-VMTK/blob/master/LevelSetSegmentation/LevelSetSegmentation.py

    # Aggregate start point and end point as seeds for vessel extraction
    allSeedsPositions = seedsPositions + endPositions

    # now we need to convert the fiducials to vtkIdLists
    seedsNodes = createFiducialNode("LevelSetSegmentationSeeds", *allSeedsPositions)
    stoppersNodes = createFiducialNode("LevelSetSegmentationStoppers", *endPositions)
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
    evolImageData.DeepCopy(
      segmentationLogic.performEvolution(sourceVolume.GetImageData(), initImageData, levelSetParameters.iterationNumber,
                                         levelSetParameters.inflation, levelSetParameters.curvature,
                                         levelSetParameters.attraction, 'geodesic'))

    # create segmentation labelMap
    labelMap = vtk.vtkImageData()
    labelMap.DeepCopy(segmentationLogic.buildSimpleLabelMap(evolImageData, 5, 0))

    # propagate the label map to the node
    outVolume.SetAndObserveImageData(labelMap)

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
    modelNode = createModelNode(modelName)
    modelNode.SetAndObservePolyData(modelPolyData)
    modelNode.CreateDefaultDisplayNodes()

    return modelNode

  @staticmethod
  def _applyLevelSetSegmentation(sourceVolume, vesselnessVolume, startPoint, endPoint, levelSetParameters):
    """ Apply VMTK LevelSetSegmentation to vesselnessVolume given input startPoint and endPoint.

    Returns label Map Volume with segmentation information and model containing marching cubes iso surface extraction

    Parameters
    ----------
    sourceVolume : vtkMRMLScalarVolumeNode
      Original volume (before vesselness filter
    vesselnessVolume : vtkMRMLScalarVolumeNode
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
                                 vesselnessVolume=(vesselnessVolume, "vtkMRMLScalarVolumeNode"),
                                 startPoint=(startPoint, "vtkMRMLMarkupsFiducialNode"),
                                 endPoint=(endPoint, "vtkMRMLMarkupsFiducialNode"))

    startPos = getFiducialPositions(startPoint)
    endPos = getFiducialPositions(endPoint)
    seedsNodes, stoppersNodes, outVolume, outModel = RVesselXModuleLogic._applyLevelSetSegmentationFromNodePositions(
      sourceVolume, vesselnessVolume, startPos, endPos, levelSetParameters)
    return seedsNodes, outVolume, outModel

  @staticmethod
  def centerLineFilter(levelSetSegmentationModel, startPoint, endPoints):
    """
    Extracts center line from input level set segmentation model (ie : vessel polyData) and start and end points
    Implementation copied from :
    https://github.com/vmtk/SlicerExtension-VMTK/blob/master/CenterlineComputation/CenterlineComputation.py

    Reimplemented to strip logic from input selection

    Parameters
    ----------
    levelSetSegmentationModel : vtkMRMLModelNode
      Result from LevelSetSegmentation representing outer vessel mesh
    startPoint : vtkMRMLMarkupsFiducialNode
      Start point for the vessel
    endPoints : vtkMRMLMarkupsFiducialNode
      End points for the vessel

    Returns
    -------
    centerLineModel : vtkMRMLModelNode
      Contains center line vtkPolyData extracted from input vessel model
    """
    # Type checking
    raiseValueErrorIfInvalidType(levelSetSegmentationModel=(levelSetSegmentationModel, "vtkMRMLModelNode"),
                                 startPoint=(startPoint, "vtkMRMLMarkupsFiducialNode"),
                                 endPoint=(endPoints, "vtkMRMLMarkupsFiducialNode"))

    # Create output node
    centerLineModel = createModelNode("CenterLineModel")

    # the output models
    preparedModel = vtk.vtkPolyData()
    model = vtk.vtkPolyData()
    network = vtk.vtkPolyData()

    logic = VMTKModule.getCenterlineComputationLogic()

    # grab the current coordinates
    currentCoordinatesRAS = [0, 0, 0]
    startPoint.GetNthFiducialPosition(0, currentCoordinatesRAS)

    # prepare the model
    preparedModel.DeepCopy(logic.prepareModel(levelSetSegmentationModel.GetPolyData()))

    # decimate the model (only for network extraction)
    model.DeepCopy(logic.decimateSurface(preparedModel))

    # open the model at the seed (only for network extraction)
    model.DeepCopy(logic.openSurfaceAtPoint(model, currentCoordinatesRAS))

    # extract Network
    network.DeepCopy(logic.extractNetwork(model))

    # here we start the actual centerline computation which is mathematically more robust and accurate but takes longer
    # than the network extraction
    # clip surface at endpoints identified by the network extraction
    tupel = logic.clipSurfaceAtEndPoints(network, levelSetSegmentationModel.GetPolyData())
    endpoints = tupel[1]

    # now find the one endpoint which is closest to the seed and use it as the source point for centerline computation
    # all other endpoints are the target points
    # the following arrays have the same indexes and are synchronized at all times
    distancesToSeed = []
    targetPoints = []

    # we now need to loop through the endpoints two times

    # first loop is to detect the endpoint resulting in the tiny hole we poked in the surface
    # this is very close to our seed but not the correct sourcePoint
    for i in range(endpoints.GetNumberOfPoints()):
      currentPoint = endpoints.GetPoint(i)
      # get the euclidean distance
      currentDistanceToSeed = math.sqrt(math.pow((currentPoint[0] - currentCoordinatesRAS[0]), 2) + math.pow(
        (currentPoint[1] - currentCoordinatesRAS[1]), 2) + math.pow((currentPoint[2] - currentCoordinatesRAS[2]), 2))

      targetPoints.append(currentPoint)
      distancesToSeed.append(currentDistanceToSeed)

    # now we have a list of distances with the corresponding points
    # the index with the most minimal distance is the holePoint, we want to ignore it
    # the index with the second minimal distance is the point closest to the seed, we want to set it as sourcepoint
    # all other points are the targetpoints

    # get the index of the holePoint, which we want to remove from our endPoints
    holePointIndex = distancesToSeed.index(min(distancesToSeed))
    # .. and remove it
    distancesToSeed.pop(holePointIndex)
    targetPoints.pop(holePointIndex)

    # now find the sourcepoint
    sourcePointIndex = distancesToSeed.index(min(distancesToSeed))
    # .. and remove it after saving it as the sourcePoint
    sourcePoint = targetPoints[sourcePointIndex]
    distancesToSeed.pop(sourcePointIndex)
    targetPoints.pop(sourcePointIndex)

    # again, at this point we have a) the sourcePoint and b) a list of real targetPoints

    # now create the sourceIdList and targetIdList for the actual centerline computation
    sourceIdList = vtk.vtkIdList()
    targetIdList = vtk.vtkIdList()

    pointLocator = vtk.vtkPointLocator()
    pointLocator.SetDataSet(preparedModel)
    pointLocator.BuildLocator()

    # locate the source on the surface
    sourceId = pointLocator.FindClosestPoint(sourcePoint)
    sourceIdList.InsertNextId(sourceId)

    endPoints.GetDisplayNode().SetTextScale(0)
    endPoints.RemoveAllMarkups()

    endPoints.AddFiducialFromArray(sourcePoint)

    # locate the endpoints on the surface
    for p in targetPoints:
      fid = endPoints.AddFiducialFromArray(p)
      endPoints.SetNthFiducialSelected(fid, False)
      id = pointLocator.FindClosestPoint(p)
      targetIdList.InsertNextId(id)

    tupel = logic.computeCenterlines(preparedModel, sourceIdList, targetIdList)
    network.DeepCopy(tupel[0])

    centerLineModel.SetAndObservePolyData(network)
    return centerLineModel

  @staticmethod
  def centerLineFilterFromNodePositions(levelSetSegmentationModel, startPoints, endPoints):
    """ Extracts centerline from input level set segmentation model (ie : vessel polyData) and start and end points

    Parameters
    ----------
    levelSetSegmentationModel : vtkMRMLModelNode
      Result from LevelSetSegmentation representing outer vessel mesh
    startPoints : List[list[float]]
      Start position for the vessel
    endPoints : List[list[float]]
      End position for the vessel

    Returns
    -------
    centerLine : vtkMRMLModelNode
      Contains center line vtkPolyData extracted from input vessel model
    """
    # Create temporary fiducials for input nodes
    startPoints = createFiducialNode("startPoint", *startPoints)
    endPoints = createFiducialNode("endPoint", *endPoints)

    # Call centerline extraction
    centerLineModel = RVesselXModuleLogic.centerLineFilter(levelSetSegmentationModel, startPoints, endPoints)

    # remove start point and end point from slicer
    removeNodeFromMRMLScene(startPoints)
    removeNodeFromMRMLScene(endPoints)

    # Return centerLineModel
    return centerLineModel

  @staticmethod
  def _isPointValid(point):
    return (point is not None) and (isinstance(point, slicer.vtkMRMLMarkupsFiducialNode)) and (
        point.GetNumberOfFiducials() > 0)

  @staticmethod
  def _areExtremitiesValid(startPoint, endPoint):
    return RVesselXModuleLogic._isPointValid(startPoint) and RVesselXModuleLogic._isPointValid(endPoint)

  def _currentVesselnessKey(self):
    return self._inputVolume, self.vesselnessFilterParameters.asTuple()

  def updateVesselnessVolume(self, nodePositions):
    """Update vesselness volume node for current input volume and current filter parameters.

    If input node is not defined, no processing will be done. The method will return whether update was processed or
    not. Update can be cancelled either because of improper input node or if update for given input node + parameters
    has already been ran before.

    Returns
    -------
    bool
      True if update was done, False otherwise.
    """
    import time

    # Early return in case the inputs is not properly defined or processing already done for input
    if self._isInvalidVolumeInput():
      return False

    removeNodeFromMRMLScene(self._vesselnessVolume)
    removeNodeFromMRMLScene(self._croppedInputVolume)
    removeNodeFromMRMLScene(self._inputRoi)
    if self._vesselnessFilterParam.useROI:
      self._inputRoi = self._createROIFromNodePositions(nodePositions)
      self._croppedInputVolume = cropSourceVolume(self._inputVolume, self._inputRoi)
    else:
      self._croppedInputVolume = cloneSourceVolume(self._inputVolume)

    self._croppedInputVolume.GetDisplayNode().SetVisibility(False)
    self._vesselnessVolume = self._applyVesselnessFilter(self._croppedInputVolume, startPoint=None)

    time.sleep(1)  # Short sleep for this thread to enable volume to be updated
    return True

  @staticmethod
  def calculateRoiExtent(nodePositions, minExtent, growthFactor):
    minPosition = np.array(nodePositions[0])
    maxPosition = np.array(nodePositions[0])
    for pos in nodePositions:
      for i in range(3):
        minPosition[i] = min(minPosition[i], pos[i])
        maxPosition[i] = max(maxPosition[i], pos[i])

    center = (maxPosition + minPosition) / 2.
    radius = np.abs(maxPosition - minPosition) / 2.
    for i, r in enumerate(radius):
      radius[i] = max(minExtent / 2., r * growthFactor)

    return center, radius

  def _createROIFromNodePositions(self, nodePositions):
    roi = slicer.vtkMRMLAnnotationROINode()
    roi.Initialize(slicer.mrmlScene)
    roi.SetName(slicer.mrmlScene.GetUniqueNameByString("VolumeCropROI"))

    center, radius = self.calculateRoiExtent(nodePositions, self._vesselnessFilterParam.minROIExtent,
                                             self._vesselnessFilterParam.roiGrowthFactor)

    roi.SetXYZ(center)
    roi.SetRadiusXYZ(radius)
    roi.RemoveAllDisplayNodeIDs()

    return roi

  def _isInvalidVolumeInput(self):
    return self._inputVolume is None

  def getCurrentVesselnessVolume(self):
    return self._vesselnessVolume

  def extractVesselVolumeFromPosition(self, seedsPositions, endPositions):
    """Extract vessels volume and model given two input lists of markups positions and current loaded input volume.
    To be run, seeds positions and end positions must contain at least one position each.

    Parameters
    ----------
    seedsPositions: List[List[float]]
      List of points to use as seeds during VMTK level set segmentation algorithm
    endPositions: List[List[float]]
      List of points to use as stoppers during VMTK level set segmentation algorithm
    levelSetParameters: LevelSetParameters

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
    if self._vesselnessVolume is None:
      raise ValueError("Please extract vesselness volume before extracting vessels")
    return self._applyLevelSetSegmentationFromNodePositions(self._croppedInputVolume, self.getCurrentVesselnessVolume(),
                                                            seedsPositions, endPositions, self.levelSetParameters)
