import numpy as np
import slicer
from slicer.ScriptedLoadableModule import ScriptedLoadableModuleLogic
import vtk

from .RVXLiverSegmentationUtils import raiseValueErrorIfInvalidType, createLabelMapVolumeNodeBasedOnModel, \
  createFiducialNode, createModelNode, createVolumeNodeBasedOnModel, removeNodeFromMRMLScene, cropSourceVolume, \
  cloneSourceVolume, getVolumeIJKToRASDirectionMatrixAsNumpyArray

try:
  from LevelSetSegmentation import LevelSetSegmentationWidget, LevelSetSegmentationLogic
  from VesselnessFiltering import VesselnessFilteringLogic
  from ExtractCenterline import ExtractCenterlineLogic

  VMTK_FOUND = True
except ImportError:
  VMTK_FOUND = False


class VMTKModule(object):
  """
  Helper class for accessing VMTK Module logic from RVessel module
  """

  @staticmethod
  def getVesselnessFilteringLogic():
    return VesselnessFilteringLogic()

  @staticmethod
  def getLevelSetSegmentationLogic():
    return LevelSetSegmentationLogic()

  @staticmethod
  def getCenterlineExtractionLogic():
    return ExtractCenterlineLogic()


class VesselnessFilterParameters(object):
  """Object holding the parameters for the vesselness filter algorithm. Init constructs vesselness filter with default
  parameters
  """

  def __init__(self):
    self.useROI = True
    self.roiGrowthFactor = 1.2
    self.minROIExtent = 20
    self.minimumDiameter = 1
    self.maximumDiameter = 7
    self.suppressPlatesPercent = 50
    self.suppressBlobsPercent = 50
    self.vesselContrast = 5
    self.satoSigma = 2
    self.satoAlpha1 = 0.5
    self.satoAlpha2 = 2
    self.useVmtkFilter = False


class LevelSetParameters(object):
  """
  Object holding the parameters for level set segmentation algorithm. Init construct level set with default parameters
  """

  def __init__(self):
    self.inflation = 0
    self.curvature = 70
    self.attraction = 50
    self.iterationNumber = 10
    self.initializationMethod = "collidingfronts"
    self.levelSetMethod = "geodesic"


class IRVXLiverSegmentationLogic(object):
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


class RVXLiverSegmentationLogic(ScriptedLoadableModuleLogic, IRVXLiverSegmentationLogic):
  """Class regrouping the logic methods for the plugin. Uses the VMTK algorithm for most of its functionality.
  Holds a map of previously calculated vesselness volumes to avoid reprocessing it when extracting liver vessels.
  """

  def __init__(self, parent=None):
    ScriptedLoadableModuleLogic.__init__(self, parent)
    IRVXLiverSegmentationLogic.__init__(self)

    self._inputVolume = None
    self._croppedInputVolume = None
    self._vesselnessVolume = None
    self._inputRoi = None
    self.levelSetParameters = LevelSetParameters()

  @staticmethod
  def isVmtkFound():
    return VMTK_FOUND

  def setInputVolume(self, inputVolume):
    """
    Parameters
    ----------
    inputVolume: vtkMRMLScalarVolumeNode, Volume on which segmentation will be done
    """
    raiseValueErrorIfInvalidType(inputVolume=(inputVolume, "vtkMRMLScalarVolumeNode"))

    if self._inputVolume != inputVolume:
      self._inputVolume = inputVolume

  def _applyVmtkVesselnessFilter(self, sourceVolume):
    """Apply VMTK VesselnessFilter to source volume given start point. Returns ouput volume with vesselness information

    Parameters
    ----------
    sourceVolume: vtkMRMLScalarVolumeNode
      Volume which will be labeled with vesselness information

    Returns
    -------
    outputVolume : vtkMRMLLabelMapVolumeNode
      Volume with vesselness information
    """
    # Type checking
    raiseValueErrorIfInvalidType(sourceVolume=(sourceVolume, "vtkMRMLScalarVolumeNode"))

    # Get module logic from VMTK Vesselness Filtering module
    vesselnessLogic = VMTKModule.getVesselnessFilteringLogic()

    # Create output node
    vesselnessFiltered = createVolumeNodeBasedOnModel(sourceVolume, "VesselnessFiltered", "vtkMRMLScalarVolumeNode")

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

  def _applySatoVesselnessFilter(self, sourceVolume):
    """Apply SATO VesselnessFilter to source volume. Returns output volume with vesselness information.

    Implementation is based on the following documentation :
    https://itk.org/ITKExamples/src/Filtering/ImageFeature/SegmentBloodVessels/Documentation.html

    Parameters
    ----------
    sourceVolume: vtkMRMLScalarVolumeNode
      Volume which will be labeled with vesselness information

    Returns
    -------
    outputVolume : vtkMRMLLabelMapVolumeNode
      Volume with vesselness information
    """
    import itk

    # Type checking
    raiseValueErrorIfInvalidType(sourceVolume=(sourceVolume, "vtkMRMLScalarVolumeNode"))

    # Convert input volume to ITK
    np_array = slicer.util.arrayFromVolume(sourceVolume)
    itk_image = itk.image_view_from_array(np_array)
    hessian_image = itk.hessian_recursive_gaussian_image_filter(itk_image.astype(itk.F),
                                                                sigma=self._vesselnessFilterParam.satoSigma)

    vesselness_filter = itk.Hessian3DToVesselnessMeasureImageFilter[itk.F].New()
    vesselness_filter.SetInput(hessian_image)
    vesselness_filter.SetAlpha1(self._vesselnessFilterParam.satoAlpha1)
    vesselness_filter.SetAlpha2(self._vesselnessFilterParam.satoAlpha2)

    # Convert output back to Slicer format
    vesselness_filter.Update()
    filtered_image = vesselness_filter.GetOutput()

    # Normalize output between 0 and 1
    output_array = itk.array_view_from_image(filtered_image)
    output_array = (output_array - np.min(output_array)) / (np.max(output_array) - np.min(output_array))

    # Initialize output volume from input volume
    vesselnessFiltered = createVolumeNodeBasedOnModel(sourceVolume, "VesselnessFiltered", "vtkMRMLScalarVolumeNode")
    slicer.util.updateVolumeFromArray(vesselnessFiltered, output_array)

    return vesselnessFiltered

  @classmethod
  def _applyLevelSetSegmentationFromNodePositions(cls, sourceVolume, croppedSourceVolume, vesselnessVolume,
                                                  seedsPositions, endPositions, levelSetParameters):
    """ Apply VMTK LevelSetSegmentation to vesselnessVolume given input seed positions and end positions

    Returns label Map Volume with segmentation information and model containing marching cubes iso surface extraction

    Parameters
    ----------
    sourceVolume : vtkMRMLScalarVolumeNode
      Original volume (before vesselness filter or cropping)
    croppedSourceVolume : vtkMRMLScalarVolumeNode
      Cropped original volume. This volume is expected to have the same size as the vesselness volume)
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
                                 croppedSourceVolume=(croppedSourceVolume, "vtkMRMLScalarVolumeNode"),
                                 vesselnessVolume=(vesselnessVolume, "vtkMRMLScalarVolumeNode"))

    # Get module logic from VMTK LevelSetSegmentation
    segmentationLogic = VMTKModule.getLevelSetSegmentationLogic()

    # Create output volume node
    tmpVolume = createLabelMapVolumeNodeBasedOnModel(croppedSourceVolume, "LevelSetSegmentation")

    # Copy paste code from LevelSetSegmentation start method
    # https://github.com/vmtk/SlicerExtension-VMTK/blob/master/LevelSetSegmentation/LevelSetSegmentation.py

    # Aggregate start point and end point as seeds for vessel extraction
    allSeedsPositions = seedsPositions + endPositions

    # now we need to convert the fiducials to vtkIdLists
    seedsNodes = createFiducialNode("LevelSetSegmentationSeeds", *allSeedsPositions)
    stoppersNodes = createFiducialNode("LevelSetSegmentationStoppers", *endPositions)
    seeds = LevelSetSegmentationWidget.convertFiducialHierarchyToVtkIdList(seedsNodes, vesselnessVolume)
    stoppers = LevelSetSegmentationWidget.convertFiducialHierarchyToVtkIdList(stoppersNodes,
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
                                              levelSetParameters.initializationMethod))

    if not initImageData.GetPointData().GetScalars():
      # something went wrong, the image is empty
      raise ValueError("Segmentation failed - the output was empty...")

    # no preview, run the whole thing! we never use the vesselness node here, just the original one
    evolImageData.DeepCopy(
      segmentationLogic.performEvolution(sourceVolume.GetImageData(), initImageData, levelSetParameters.iterationNumber,
                                         levelSetParameters.inflation, levelSetParameters.curvature,
                                         levelSetParameters.attraction, levelSetParameters.levelSetMethod))

    # create segmentation labelMap
    labelMap = vtk.vtkImageData()
    labelMap.DeepCopy(segmentationLogic.buildSimpleLabelMap(evolImageData, 5, 0))

    # propagate the label map to the node
    tmpVolume.SetAndObserveImageData(labelMap)

    # Resample output volume to be the same size and orientation as non cropped volume
    outVolume = cls.resampleLabelMap(newVolumeTemplate=sourceVolume, labelMapToResample=tmpVolume,
                                     labelMapName="LevelSetSegmentation")

    # Remove tmp volume
    slicer.mrmlScene.RemoveNode(tmpVolume)

    # Construct model boundary mesh
    outModel = RVXLiverSegmentationLogic.createVolumeBoundaryModel(outVolume, "LevelSetSegmentationModel", evolImageData)

    return seedsNodes, stoppersNodes, outVolume, outModel

  @classmethod
  def resampleLabelMap(cls, newVolumeTemplate, labelMapToResample, labelMapName):
    import SimpleITK as sitk

    def volume_itk_direction(v):
      """Returns volume IJK to RAS direction matrix in ITK compliant format"""
      m = getVolumeIJKToRASDirectionMatrixAsNumpyArray(v)
      return m[0:3, 0:3].flatten()

    to_resample_array = slicer.util.arrayFromVolume(labelMapToResample)

    to_resample_itk_im = sitk.GetImageFromArray(to_resample_array)
    to_resample_itk_im.SetOrigin(labelMapToResample.GetOrigin())
    to_resample_itk_im.SetSpacing(labelMapToResample.GetSpacing())
    to_resample_itk_im.SetDirection(volume_itk_direction(labelMapToResample))

    resample_filter = sitk.ResampleImageFilter()
    resample_filter.SetInterpolator(sitk.sitkNearestNeighbor)
    resample_filter.SetOutputOrigin(newVolumeTemplate.GetOrigin())
    resample_filter.SetOutputSpacing(newVolumeTemplate.GetSpacing())
    resample_filter.SetOutputDirection(volume_itk_direction(newVolumeTemplate))
    resample_filter.SetSize(newVolumeTemplate.GetImageData().GetDimensions())
    resample_filter.SetTransform(sitk.Transform())
    resample_filter.SetDefaultPixelValue(0)
    resampled_itk_im = resample_filter.Execute(to_resample_itk_im)
    resampled_array = sitk.GetArrayFromImage(resampled_itk_im)

    resampled_label_map = createLabelMapVolumeNodeBasedOnModel(newVolumeTemplate, labelMapName)
    slicer.util.updateVolumeFromArray(resampled_label_map, resampled_array)
    return resampled_label_map

  @staticmethod
  def createVolumeBoundaryModel(sourceVolume, modelName, imageData=None, threshold=0.0):
    raiseValueErrorIfInvalidType(sourceVolume=(sourceVolume, "vtkMRMLScalarVolumeNode"))
    if imageData is None:
      imageData = sourceVolume.GetImageData()

    if imageData is None:
      return None

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
  def openSurfaceAtPoint(polyData, seed):
    """
    Copied from https://github.com/vmtk/SlicerExtension-VMTK/blob/master/CenterlineComputation/CenterlineComputation.py

    Interface has changed between versions of the VMTK module and module logic cannot be used as is for all users.
    """
    pointLocator = vtk.vtkPointLocator()
    pointLocator.SetDataSet(polyData)
    pointLocator.BuildLocator()

    # find the closest point next to the seed on the surface
    pointId = pointLocator.FindClosestPoint(seed)

    if pointId < 0:
      # Calling GetPoint(-1) would crash the application
      raise ValueError("openSurfaceAtPoint failed: empty input polydata")

    # Tell the polydata to build 'upward' links from points to cells
    polyData.BuildLinks()
    # Mark cells as deleted
    cellIds = vtk.vtkIdList()
    polyData.GetPointCells(pointId, cellIds)
    for cellIdIndex in range(cellIds.GetNumberOfIds()):
      polyData.DeleteCell(cellIds.GetId(cellIdIndex))

    # Remove the marked cells
    polyData.RemoveDeletedCells()

  @staticmethod
  def centerLineFilter(levelSetSegmentationModel, endPoints):
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
                                 endPoint=(endPoints, "vtkMRMLMarkupsFiducialNode"))

    # Create output node
    centerLineModel = createModelNode("CenterLineModel")

    logic = VMTKModule.getCenterlineExtractionLogic()

    # Preprocess poly data
    targetNumberOfPoints = 5000
    decimationAggressiveness = 4.0
    subdivideInputSurface = False
    inputSurfacePolyData = logic.polyDataFromNode(levelSetSegmentationModel, None)
    preprocessedPolyData = logic.preprocess(inputSurfacePolyData, targetNumberOfPoints, decimationAggressiveness,
                                            subdivideInputSurface)

    # grab the current coordinates
    centerlinePolyData, _ = logic.extractCenterline(preprocessedPolyData, endPoints, 1.0)

    centerLineModel.SetAndObservePolyData(centerlinePolyData)
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
    endPoints = createFiducialNode("endPoint", *(startPoints + endPoints))

    # Call centerline extraction
    centerLineModel = RVXLiverSegmentationLogic.centerLineFilter(levelSetSegmentationModel, endPoints)

    # remove end point from slicer
    removeNodeFromMRMLScene(endPoints)

    # Return centerLineModel
    return centerLineModel

  @staticmethod
  def _isPointValid(point):
    return (point is not None) and (isinstance(point, slicer.vtkMRMLMarkupsFiducialNode)) and (
        point.GetNumberOfFiducials() > 0)

  @staticmethod
  def _areExtremitiesValid(startPoint, endPoint):
    return RVXLiverSegmentationLogic._isPointValid(startPoint) and RVXLiverSegmentationLogic._isPointValid(endPoint)

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

    if self._vesselnessFilterParam.useVmtkFilter:
      self._vesselnessVolume = self._applyVmtkVesselnessFilter(self._croppedInputVolume)
    else:
      self._vesselnessVolume = self._applySatoVesselnessFilter(self._croppedInputVolume)

    time.sleep(1)  # Short sleep for this thread to enable volume to be updated
    return True

  @staticmethod
  def calculateRoiExtent(nodePositions, minExtent, growthFactor):
    nodePositions = list(nodePositions)

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
    return self._applyLevelSetSegmentationFromNodePositions(sourceVolume=self._inputVolume,
                                                            croppedSourceVolume=self._croppedInputVolume,
                                                            vesselnessVolume=self.getCurrentVesselnessVolume(),
                                                            seedsPositions=seedsPositions, endPositions=endPositions,
                                                            levelSetParameters=self.levelSetParameters)
