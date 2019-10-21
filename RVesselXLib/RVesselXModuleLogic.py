import slicer
import vtk
from slicer.ScriptedLoadableModule import ScriptedLoadableModuleLogic

from Vessel import Vessel


class VMTKModule(object):
  """Helper class for loading VMTK module and accessing VMTK Module logic from RVessel module
  """

  @staticmethod
  def tryToLoad():
    """Try to load every VMTK widgets in slicer.

    :return: list of VMTK modules where loading failed. Empty list if success
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


class RVesselXModuleLogic(ScriptedLoadableModuleLogic):
  def __init__(self, parent=None):
    ScriptedLoadableModuleLogic.__init__(self, parent)

    notFound = VMTKModule.tryToLoad()
    if notFound:
      errorMsg = "Failed to load the following VMTK Modules : %s\nPlease make sure VMTK is installed." % notFound
      slicer.util.errorDisplay(errorMsg)

  @staticmethod
  def _raiseValueErrorIfInvalidType(**kwargs):
    """Verify input type satisfies the expected type and raise in case it doesn't.

    Expected input dictionary : "valueName":(value, "expectedType").
    If value is None or value is not an instance of expectedType, method will raise ValueError with text indicating
    valueName, value and expected type
    """

    for valueName, values in kwargs.items():
      # Get value and expect type from dictionary
      value, expType = values

      # Get type from slicer in case of string input
      if isinstance(expType, str):
        expType = getattr(slicer, expType)

      # Verify value is of correct instance
      if not isinstance(value, expType):
        raise ValueError("%s Type error.\nExpected : %s but got %s." % (valueName, expType, type(value)))

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
  def _createLabelMapVolumeNodeBasedOnModel(modelVolume, volumeName):
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

  def _getFiducialPositions(self, fiducialNode):
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
    startPoint: vtkMRMLMarkupsFiducialNode
      Start point of the vessel. Gives indication on the target diameter of the vessel which will be
      filtered by the method.

    Returns
    -------
    outputVolume : vtkMRMLLabelMapVolumeNode
      Volume with vesselness information
    """
    # Type checking
    self._raiseValueErrorIfInvalidType(sourceVolume=(sourceVolume, "vtkMRMLScalarVolumeNode"),
                                       startPoint=(startPoint, "vtkMRMLMarkupsFiducialNode"))

    # Get module logic from VMTK Vesselness Filtering module
    vesselnessLogic = VMTKModule.getVesselnessFilteringLogic()

    # Create output node
    vesselnessFiltered = self._createLabelMapVolumeNodeBasedOnModel(sourceVolume, "VesselnessFiltered")

    # Extract diameter size from start point position
    vesselPositionRas = [0, 0, 0]
    startPoint.GetNthFiducialPosition(0, vesselPositionRas)
    vesselPositionIJK = vesselnessLogic.getIJKFromRAS(sourceVolume, vesselPositionRas)
    maximumDetectedDiameter = vesselnessLogic.getDiameter(sourceVolume.GetImageData(), vesselPositionIJK)
    minimumDiameterDefaultValue = 1

    # Extract contrast from seed
    contrastMeasure = vesselnessLogic.calculateContrastMeasure(sourceVolume.GetImageData(), vesselPositionIJK,
                                                               maximumDetectedDiameter)

    # Calculate alpha and beta parameters from suppressPlates and suppressBlobs parameters
    # For now = default VMTK Values (may be made available to user)
    suppressPlatesDefaultValue = 10
    suppresBlobsDefaultValue = 10
    alpha = vesselnessLogic.alphaFromSuppressPlatesPercentage(suppressPlatesDefaultValue)
    beta = vesselnessLogic.betaFromSuppressBlobsPercentage(suppresBlobsDefaultValue)

    # Scale minimum and maximum diameters with volume spacing
    minimumDiameter = minimumDiameterDefaultValue * min(sourceVolume.GetSpacing())
    maximumDiameter = maximumDetectedDiameter * min(sourceVolume.GetSpacing())

    # Compute vesselness volume
    vesselnessLogic.computeVesselnessVolume(sourceVolume, vesselnessFiltered, maximumDiameterMm=maximumDiameter,
                                            minimumDiameterMm=minimumDiameter, alpha=alpha, beta=beta,
                                            contrastMeasure=contrastMeasure)

    return vesselnessFiltered

  def _applyLevelSetSegmentation(self, sourceVolume, vesselnessVolume, startPoint, endPoint):
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
    self._raiseValueErrorIfInvalidType(sourceVolume=(sourceVolume, "vtkMRMLScalarVolumeNode"),
                                       vesselnessVolume=(vesselnessVolume, "vtkMRMLLabelMapVolumeNode"),
                                       startPoint=(startPoint, "vtkMRMLMarkupsFiducialNode"),
                                       endPoint=(endPoint, "vtkMRMLMarkupsFiducialNode"))

    # Get module logic from VMTK LevelSetSegmentation
    segmentationWidget = VMTKModule.getLevelSetSegmentationWidget()
    segmentationLogic = VMTKModule.getLevelSetSegmentationLogic()

    # Create output volume node
    outputVolume = self._createLabelMapVolumeNodeBasedOnModel(sourceVolume, "LevelSetSegmentation")
    outputModel = self._createModelNode("LevelSetSegmentationModel")

    # Copy paste code from LevelSetSegmentation start method
    # https://github.com/vmtk/SlicerExtension-VMTK/blob/master/LevelSetSegmentation/LevelSetSegmentation.py

    # Aggregate start point and end point as seeds for vessel extraction
    seedsPositions = self._getFiducialPositions(startPoint) + self._getFiducialPositions(endPoint)

    # now we need to convert the fiducials to vtkIdLists
    seedsNodes = self._createFiducialNode("LevelSetSegmentationSeeds", *seedsPositions)
    seeds = segmentationWidget.convertFiducialHierarchyToVtkIdList(seedsNodes, vesselnessVolume)
    stoppers = segmentationWidget.convertFiducialHierarchyToVtkIdList(endPoint,
                                                                      vesselnessVolume) if endPoint else vtk.vtkIdList()

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
    outputVolume.SetAndObserveImageData(labelMap)

    # currentVesselnessNode
    slicer.util.setSliceViewerLayers(background=sourceVolume, foreground=vesselnessVolume, label=outputVolume,
                                     foregroundOpacity=0.1)

    # generate 3D model
    model = vtk.vtkPolyData()

    # we need the ijkToRas transform for the marching cubes call
    ijkToRasMatrix = vtk.vtkMatrix4x4()
    outputVolume.GetIJKToRASMatrix(ijkToRasMatrix)

    # call marching cubes
    model.DeepCopy(segmentationLogic.marchingCubes(evolImageData, ijkToRasMatrix, 0.0))

    # propagate model to nodes
    outputModel.SetAndObservePolyData(model)
    outputModel.CreateDefaultDisplayNodes()

    return seedsNodes, outputVolume, outputModel

  def _closestPointOnSurfaceAsIdList(self, surface, point):
    pointList = vtk.vtkIdList()

    pointLocator = vtk.vtkPointLocator()
    pointLocator.SetDataSet(surface)
    pointLocator.BuildLocator()

    sourceId = pointLocator.FindClosestPoint(point)
    pointList.InsertNextId(sourceId)
    return pointList

  def _applyCenterlineFilter(self, levelSetSegmentationModel, startPoint, endPoint):
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
    self._raiseValueErrorIfInvalidType(levelSetSegmentationModel=(levelSetSegmentationModel, "vtkMRMLModelNode"),
                                       startPoint=(startPoint, "vtkMRMLMarkupsFiducialNode"),
                                       endPoint=(endPoint, "vtkMRMLMarkupsFiducialNode"))

    # Get logic from VMTK center line computation module
    centerLineLogic = VMTKModule.getCenterlineComputationLogic()

    # Extract mesh and source and target point lists from input data
    segmentationMesh = levelSetSegmentationModel.GetPolyData()
    sourceIdList = self._closestPointOnSurfaceAsIdList(segmentationMesh, self._getFiducialPositions(startPoint)[0])
    targetIdList = self._closestPointOnSurfaceAsIdList(segmentationMesh, self._getFiducialPositions(endPoint)[0])

    # Calculate center line poly data
    centerLinePolyData, voronoiPolyData = centerLineLogic.computeCenterlines(segmentationMesh, sourceIdList,
                                                                             targetIdList)

    # Create output voronoi model and centerline model
    centerLineModel = self._createModelNode("CenterLineModel")
    voronoiModel = self._createModelNode("VoronoiModel")

    centerLineModel.SetAndObservePolyData(centerLinePolyData)
    voronoiModel.SetAndObservePolyData(voronoiPolyData)

    return centerLineModel, voronoiModel

  def extractVessel(self, sourceVolume, startPoint, endPoint, vesselnessVolume=None):
    """ Extracts vessel from source volume, given start point and end point

    Parameters
    ----------
    sourceVolume: vtkMRMLScalarVolumeNode
      Volume on which segmentation will be done
    startPoint: vtkMRMLMarkupsFiducialNode
      Start point for the vessel
    endPoint: vtkMRMLMarkupsFiducialNode
      End point for the vessel
    vesselnessVolume: vtkMRMLLabelMapVolumeNode
      optional filtered vesselness volume to use when extracting vessel
      if None, volume will be calculated using VMTK vesselness filter.
      Note that calculating this volume can be time demanding.

    Returns
    -------
    vessel : Vessel
      extracted vessel with associated informations
    """
    # Type checking
    self._raiseValueErrorIfInvalidType(sourceVolume=(sourceVolume, "vtkMRMLScalarVolumeNode"),
                                       startPoint=(startPoint, "vtkMRMLMarkupsFiducialNode"),
                                       endPoint=(endPoint, "vtkMRMLMarkupsFiducialNode"))

    # Create vessel which will hold every information of the vessel extracted in logic module
    vessel = Vessel()
    vessel.setExtremities(startPoint, endPoint)

    # Apply vesselness filter
    if vesselnessVolume is None:
      vesselnessVolume = self._applyVesselnessFilter(sourceVolume, startPoint)
    vessel.setVesselnessVolume(vesselnessVolume)

    # Call levelSetSegmentation
    levelSetSeeds, levelSetVolume, levelSetModel = self._applyLevelSetSegmentation(sourceVolume, vesselnessVolume,
                                                                                   startPoint, endPoint)
    vessel.setSegmentation(seeds=levelSetSeeds, volume=levelSetVolume, model=levelSetModel)

    # Extract centerpoint
    centerline, voronoiModel = self._applyCenterlineFilter(levelSetModel, startPoint, endPoint)
    vessel.setCenterline(centerline=centerline, voronoiModel=voronoiModel)

    return vessel
