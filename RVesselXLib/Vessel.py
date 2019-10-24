import slicer

from RVesselXUtils import GeometryExporter


class Vessel(object):
  """ Object responsible for holding vessel information and representation in the scene

  Interface for manipulation the vessel through the vessel tree
  """

  _createdCount = 0

  def __init__(self, name=None):
    if name is None:
      name = self.defaultName()

    self.startPoint = None
    self.endPoint = None
    self.vesselnessVolume = None
    self.segmentationSeeds = None
    self.segmentedModel = None
    self.segmentedVolume = None
    self.segmentedCenterline = None
    self.segmentedVoronoiModel = None
    self.name = name
    self.isVisible = True
    self._inputSource = None

  @staticmethod
  def defaultName():
    name = "Vessel_" + str(Vessel._createdCount)
    Vessel._createdCount += 1
    return name

  def toggleVisibility(self):
    """Shows/Hides segmented volume, model and center line in the scene.
    """
    self.isVisible = not self.isVisible
    if self._wasSegmented():
      self.segmentedVolume.SetDisplayVisibility(self.isVisible)
      self.segmentedModel.SetDisplayVisibility(self.isVisible)
      self.segmentedCenterline.SetDisplayVisibility(self.isVisible)

  @property
  def name(self):
    return self._name

  @name.setter
  def name(self, name):
    """Renames vessel segmented volume, model and center line
    """
    self._name = name
    self._renameSegmentation()

  def _renameSegmentation(self):
    """Renames vessel segmented volume, model and center line if vessel was properly segmented.
    """
    if self._wasSegmented():
      self.segmentedVolume.SetName(self._name)
      self.segmentedModel.SetName(self._name + "_Surface")
      self.segmentedCenterline.SetName(self._name + "_Centerline")

  def _wasSegmented(self):
    """True if vessel contains a segmented volume and center line (Creation of volumes is handled by RVesselXModuleLogic
    object
    """
    return self.segmentedVolume is not None and self.segmentedCenterline is not None

  def lockExtremities(self, isLocked):
    """Lock start and end point markups in the scene to avoid unwanted user edition

    Parameters
    ----------
    isLocked: If true, locks markups else frees them
    """
    if self.startPoint is not None:
      self.startPoint.SetLocked(isLocked)
    if self.endPoint is not None:
      self.endPoint.SetLocked(isLocked)

  def setExtremities(self, startPoint, endPoint):
    """Adds start and end points of the vessel to the structure. The points will be locked in the UI to avoid accidental
    user manipulation of the points.
    """
    self.startPoint = startPoint
    self.endPoint = endPoint
    self.lockExtremities(True)

  def setVesselnessVolume(self, vesselnessVolume):
    """Adds preprocessed vesselness input volume to the vessel. The vesselness volume corresponds to the output of
    the VMTK VesselnessFiltering module. It adds information to the input volume of where the vessels may be.

    This volume is hidden from the user in the UI.
    """
    self.vesselnessVolume = vesselnessVolume
    self._hideFromUser(self.vesselnessVolume)

  def setSegmentation(self, seeds, volume, model):
    """Adds segmentation seed points, volume and model to the vessel. Segmentation seeds are hidden to the user as they
    correspond to the start and end points selected by the user in the vessel tab.

    Segmentation volume and model correspond to the output of the VMTK LevelSetSegmentation module.
    """
    self.segmentationSeeds = seeds
    self.segmentedVolume = volume
    self.segmentedModel = model
    self._renameSegmentation()
    self._removeFromScene(self.segmentationSeeds)

  def setCenterline(self, centerline, voronoiModel):
    """Adds centerline model and voronoi model to the vessel. Voronoi model is removed from the scene as it is not
    directly interesting to the user

    Center line and voronoi model correspond to the output of the VMTK CenterlineComputation module.
    """
    self.segmentedCenterline = centerline
    self.segmentedVoronoiModel = voronoiModel
    self._renameSegmentation()
    self._removeFromScene(self.segmentedVoronoiModel)

  def _hideFromUser(self, modelsToHide, hideFromEditor=True):
    """Hides the input models from the user and from the editor if option is set.

    Parameters
    ----------
    modelsToHide: List[vtkMRMLNode] or vtkMRMLNode
      Objects to hide from the user
    hideFromEditor: (option) bool
      If set to true, will hide the nodes from both views and the editor. Else they will be only hidden from views.
      default = True
    """
    for model in self._removeNoneList(modelsToHide):
      model.SetDisplayVisibility(False)
      if hideFromEditor:
        model.SetHideFromEditors(True)

  def _removeFromScene(self, nodesToRemove):
    """Removes the input nodes from the scene. Nodes will no longer be accessible from the mrmlScene or from the UI.

    Parameters
    ----------
    nodesToRemove: List[vtkMRMLNode] or vtkMRMLNode
      Objects to remove from the scene
    """
    nodesInScene = [node for node in self._removeNoneList(nodesToRemove) if slicer.mrmlScene.IsNodePresent(node)]
    for node in nodesInScene:
      slicer.mrmlScene.RemoveNode(node)

  @staticmethod
  def _removeNoneList(elements):
    """
    Parameters
    ----------
    elements: object or List[object]

    Returns
    -------
    List[object] with no None values
    """
    if not isinstance(elements, list):
      elements = [elements]
    return [elt for elt in elements if elt is not None]

  def setInputSource(self, inputSource):
    self._inputSource = inputSource

  def removeFromScene(self):
    """Removes all the associated models of the vessel from mrml scene except for start and end points
    """
    self._removeFromScene([self.segmentedCenterline, self.segmentedModel, self.segmentedVolume, self.segmentationSeeds,
                           self.segmentedVoronoiModel, self.vesselnessVolume])

  def getGeometryExporter(self):
    """
    Returns
    -------
      Returns GeometryExporter object containing vessel volume and center line for user export.
    """
    exporter = GeometryExporter()
    exporter[self.name] = self.segmentedVolume
    exporter[self.name + "CenterLine"] = self.segmentedCenterline
    return exporter
