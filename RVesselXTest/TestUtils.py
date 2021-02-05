from collections import OrderedDict

import slicer
import vtk

from RVesselXLib import IRVesselXModuleLogic


class TemporaryDir(object):
  """Helper context manager for creating and removing temporary directory for testing purposes
  """

  def __init__(self, dirSuffix="RVesselX"):
    self._dirSuffix = dirSuffix
    self._dir = None

  def __enter__(self):
    import tempfile
    self._dir = tempfile.mkdtemp(suffix=self._dirSuffix)
    return self._dir

  def __exit__(self, *args):
    import shutil
    shutil.rmtree(self._dir)
    pass


class FakeLogic(IRVesselXModuleLogic):
  """Fake logic for faster tests of vessel tree
  """

  def __init__(self, returnedVessel=None):
    self.returnedVessel = returnedVessel
    self._input = None

  def setReturnedVessel(self, vessel):
    self._vessel = vessel

  @property
  def returnedVessel(self):
    return self._vessel

  @returnedVessel.setter
  def returnedVessel(self, value):
    self._vessel = value


def createEmptyVolume(volumeName):
  emptyVolume = slicer.mrmlScene.CreateNodeByClass("vtkMRMLLabelMapVolumeNode")
  emptyVolume.UnRegister(None)
  emptyVolume.SetName(slicer.mrmlScene.GetUniqueNameByString(volumeName))
  return emptyVolume


def createNonEmptyVolume(volumeName="VolumeName"):
  import numpy as np

  arbitraryGenerativeFunction = np.fromfunction(lambda x, y, z: 0.5 * x * x + 0.3 * y * y + 0.5 * z * z, (30, 20, 15))
  volumeNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLScalarVolumeNode')
  volumeNode.CreateDefaultDisplayNodes()
  volumeNode.SetName(volumeName)
  slicer.util.updateVolumeFromArray(volumeNode, arbitraryGenerativeFunction)
  return volumeNode


def createNonEmptyModel(modelName="ModelName"):
  sphere = vtk.vtkSphereSource()
  sphere.SetRadius(30.0)
  sphere.Update()
  modelNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode')
  modelNode.SetAndObservePolyData(sphere.GetOutput())
  modelNode.SetName(modelName)
  return modelNode


class FakeMarkupNode(object):
  """Partial implementation of a markup with injection of positions and node IDs"""

  def __init__(self):
    self._nodes = OrderedDict()

  def add_node(self, label, position):
    self._nodes[label] = position

  def GetNumberOfFiducials(self):
    return len(self._nodes)

  def GetNthFiducialLabel(self, i_fiducial):
    return self._nodes.keys()[i_fiducial]

  def GetNthFiducialPosition(self, i_fiducial, out_position):
    node_pos = self._nodes.values()[i_fiducial]
    for i in range(len(out_position)):
      out_position[i] = node_pos[i]
