import os

import slicer
from slicer.ScriptedLoadableModule import *


class RVesselXLiverSegmentationEffect(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "SegmentEditorLiver"
    self.parent.categories = ["Segmentation"]
    self.parent.dependencies = ["Segmentations"]
    self.parent.contributors = ["Camille Huet - Kitware SAS", "Thibault Pelletier - Kitware SAS"]
    self.parent.hidden = True
    self.parent.helpText = "This hidden module registers the segment editor effect"
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = "Initially developed during the RVesselX research project. " \
                                      "See https://anr.fr/Projet-ANR-18-CE45-0018 for details."
    slicer.app.connect("startupCompleted()", self.registerEditorEffect)

  def registerEditorEffect(self):
    import qSlicerSegmentationsEditorEffectsPythonQt as qSlicerSegmentationsEditorEffects

    if not DependencyChecker.areDependenciesSatisfied():
      return

    instance = qSlicerSegmentationsEditorEffects.qSlicerSegmentEditorScriptedEffect(None)
    effectFilename = os.path.join(os.path.dirname(__file__), self.__class__.__name__ + 'Lib/SegmentEditorEffect.py')
    instance.setPythonSource(effectFilename.replace('\\', '/'))
    instance.self().register()


class DependencyChecker(object):
  """
  Class responsible for installing the Modules dependencies
  """

  @classmethod
  def areDependenciesSatisfied(cls):
    try:
      import monai
      import itk
      import torch
      import skimage
      import gdown
      import nibabel
      return True
    except ImportError:
      return False

  @classmethod
  def installDependenciesIfNeeded(cls, progressDialog=None):
    if cls.areDependenciesSatisfied():
      return

    progressDialog = progressDialog or slicer.util.createProgressDialog(maximum=0)
    progressDialog.labelText = "Installing PyTorch"
    slicer.util.pip_install("https://download.pytorch.org/whl/cu101/torch-1.8.1%2Bcu101-cp36-cp36m-win_amd64.whl")

    for dep in ["itk", "nibabel", "scikit-image", "gdown", "monai"]:
      progressDialog.labelText = dep
      slicer.util.pip_install(dep)
