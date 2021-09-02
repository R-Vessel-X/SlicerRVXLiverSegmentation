import gc
import os.path

from SegmentEditorEffects import *
import monai
from monai.inferers.utils import sliding_window_inference
from monai.networks.layers import Norm
from monai.networks.nets.unet import UNet
from monai.transforms import (AddChanneld, Compose, Orientationd, ScaleIntensityRanged, Spacingd, ToTensord)
from monai.transforms.compose import MapTransform
from monai.transforms.post.array import AsDiscrete, KeepLargestConnectedComponent
import numpy as np
import qt
import slicer
from slicer.ScriptedLoadableModule import *
import slicer.modules
from slicer.util import VTKObservationMixin
import torch
import vtk


class SegmentEditorEffect(AbstractScriptedSegmentEditorEffect):
  """This effect segments the liver in the input volume using a UNet model"""

  def __init__(self, scriptedEffect):
    self.device = qt.QComboBox()
    scriptedEffect.name = 'Segment CT Liver'
    scriptedEffect.perSegment = True  # this effect operates on a single selected segment
    AbstractScriptedSegmentEditorEffect.__init__(self, scriptedEffect)
    self.logic = SegmentEditorEffectLogic()
    self.clippedMasterImageData = None
    self.lastRoiNodeId = ""
    self.lastRoiNodeModifiedTime = 0
    self.roiSelector = slicer.qMRMLNodeComboBox()

  def clone(self):
    # It should not be necessary to modify this method
    import qSlicerSegmentationsEditorEffectsPythonQt as effects
    clonedEffect = effects.qSlicerSegmentEditorScriptedEffect(None)
    clonedEffect.setPythonSource(__file__.replace('\\', '/'))
    return clonedEffect

  def icon(self):
    # It should not be necessary to modify this method
    iconPath = os.path.join(os.path.dirname(__file__), 'SegmentEditorEffect.png')
    if os.path.exists(iconPath):
      return qt.QIcon(iconPath)
    return qt.QIcon()

  def helpText(self):
    return "<html>Segments the liver using a UNet model in CT modality Volumes<br><br>" \
           "A ROI may be necessary to limit memory consumption.</html>"

  def setupOptionsFrame(self):
    """
    Setup the ROI selection comboBox and the apply segmentation button
    """

    # CPU / CUDA options
    self.device.addItems(["cuda", "cpu"])
    self.scriptedEffect.addLabeledOptionsWidget("Device:", self.device)

    # Add ROI options
    self.roiSelector.nodeTypes = ['vtkMRMLAnnotationROINode']
    self.roiSelector.noneEnabled = True
    self.roiSelector.setMRMLScene(slicer.mrmlScene)
    self.scriptedEffect.addLabeledOptionsWidget("ROI: ", self.roiSelector)

    # Toggle ROI visibility button
    toggleROIVisibilityButton = qt.QPushButton("Toggle ROI Visibility")
    toggleROIVisibilityButton.objectName = self.__class__.__name__ + 'ToggleROIVisibility'
    toggleROIVisibilityButton.setToolTip("Toggle selected ROI visibility")
    toggleROIVisibilityButton.connect('clicked()', self.toggleROIVisibility)
    self.scriptedEffect.addOptionsWidget(toggleROIVisibilityButton)

    # Apply button
    applyButton = qt.QPushButton("Apply")
    applyButton.objectName = self.__class__.__name__ + 'Apply'
    applyButton.setToolTip("Extract liver from input volume")
    applyButton.connect('clicked()', self.onApply)
    self.scriptedEffect.addOptionsWidget(applyButton)

  def activate(self):
    """
    When activated, disable effect in the view and reset the clipped image data.
    """
    self.scriptedEffect.showEffectCursorInSliceView = False
    self.clippedMasterImageData = None

  def onApply(self):
    """
    When applied, crop the input volume if necessary and run the UNet segmentation model on the cropped volume.
    Overwrites the selected segment labelMap when done.
    """
    qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)
    masterVolumeNode = slicer.vtkMRMLScalarVolumeNode()
    slicer.mrmlScene.AddNode(masterVolumeNode)
    slicer.vtkSlicerSegmentationsModuleLogic.CopyOrientedImageDataToVolumeNode(self.getClippedMasterImageData(),
                                                                               masterVolumeNode)
    try:
      self.logic.launchLiverSegmentation(masterVolumeNode, use_cuda=self.device.currentText == "cuda")

      self.scriptedEffect.saveStateForUndo()
      self.scriptedEffect.modifySelectedSegmentByLabelmap(
        slicer.vtkSlicerSegmentationsModuleLogic.CreateOrientedImageDataFromVolumeNode(masterVolumeNode),
        slicer.qSlicerSegmentEditorAbstractEffect.ModificationModeSet)

    except Exception as e:
      qt.QApplication.restoreOverrideCursor()
      slicer.util.errorDisplay(str(e))

    finally:
      qt.QApplication.restoreOverrideCursor()
      slicer.mrmlScene.RemoveNode(masterVolumeNode)

  def getClippedMasterImageData(self):
    """
    Crops the master volume node if a ROI Node is selected in the parameter comboBox. Otherwise returns the full extent
    of the volume.
    """
    # Return masterImageData unchanged if there is no ROI
    masterImageData = self.scriptedEffect.masterVolumeImageData()
    roiNode = self.roiSelector.currentNode()
    if roiNode is None or masterImageData is None:
      self.clippedMasterImageData = None
      self.lastRoiNodeId = ""
      self.lastRoiNodeModifiedTime = 0
      return masterImageData

    # Return last clipped image data if there was no change
    if (
        self.clippedMasterImageData is not None and roiNode.GetID() == self.lastRoiNodeId and roiNode.GetMTime() == self.lastRoiNodeModifiedTime):
      # Use cached clipped master image data
      return self.clippedMasterImageData

    # Compute clipped master image
    import SegmentEditorLocalThresholdLib
    self.clippedMasterImageData = SegmentEditorLocalThresholdLib.SegmentEditorEffect.cropOrientedImage(masterImageData,
                                                                                                       roiNode)
    self.lastRoiNodeId = roiNode.GetID()
    self.lastRoiNodeModifiedTime = roiNode.GetMTime()
    return self.clippedMasterImageData

  def toggleROIVisibility(self):
    """
    Toggles the visibility of the currently selected ROI.
    """
    roiNode = self.roiSelector.currentNode()
    if roiNode is None:
      return

    roiNode.SetDisplayVisibility(not roiNode.GetDisplayVisibility())


class SlicerLoadImage(MapTransform):
  """
  Adapter from Slicer VolumeNode to MONAI volumes.
  """

  def __init__(self, keys, meta_key_postfix: str = "meta_dict") -> None:
    super().__init__(keys)
    self.meta_key_postfix = meta_key_postfix

  def __call__(self, volume_node):
    data = slicer.util.arrayFromVolume(volume_node)
    data = np.swapaxes(data, 0, 2)
    print("Load volume from Slicer : {}Mb\tshape {}\tdtype {}".format(data.nbytes * 0.000001, data.shape, data.dtype))
    spatial_shape = data.shape

    # apply spacing
    m = vtk.vtkMatrix4x4()
    volume_node.GetIJKToRASMatrix(m)
    affine = slicer.util.arrayFromVTKMatrix(m)
    meta_data = {"affine": affine, "original_affine": affine, "spacial_shape": spatial_shape,
                 'original_spacing': volume_node.GetSpacing()}

    return {self.keys[0]: data, '{}_{}'.format(self.keys[0], self.meta_key_postfix): meta_data}


class SegmentEditorEffectLogic(ScriptedLoadableModuleLogic):
  """
  Logic class responsible for instantiating the UNet model and running the segmentation on the input node.
  """

  def __init__(self):
    ScriptedLoadableModuleLogic.__init__(self)

  @classmethod
  def createUNetModel(cls, device):
    return UNet(dimensions=3, in_channels=1, out_channels=2, channels=(16, 32, 64, 128, 256), strides=(2, 2, 2, 2),
                num_res_units=2, norm=Norm.BATCH, ).to(device)

  @classmethod
  def getPreprocessingTransform(cls):
    """
    Preprocessing transform which converts the input volume to MONAI format and resamples and normalizes its inputs.
    The values in this transform are the same as in the training transform preprocessing.
    """
    trans = [SlicerLoadImage(keys=["volume"]), AddChanneld(keys=["volume"]),
             Spacingd(keys=['volume'], pixdim=(1.5, 1.5, 2.0), mode="bilinear"),
             Orientationd(keys=["volume"], axcodes="RAS"),
             ScaleIntensityRanged(keys=["volume"], a_min=-57, a_max=164, b_min=0.0, b_max=1.0, clip=True),
             AddChanneld(keys=["volume"]), ToTensord(keys=["volume"]), ]
    return Compose(trans)

  @classmethod
  def getPostProcessingTransform(cls, original_spacing):
    """
    Simple post processing transform to convert the volume back to its original spacing.
    """
    return Compose([AddChanneld(keys=["volume"]), Spacingd(keys=['volume'], pixdim=original_spacing, mode="nearest")])

  @classmethod
  def launchLiverSegmentation(cls, in_out_volume_node, use_cuda):
    """
    Runs the segmentation on the input volume and returns the segmentation in the same volume.
    """

    try:
      with torch.no_grad():
        device = torch.device("cpu") if not use_cuda or not torch.cuda.is_available() else torch.device("cuda:0")
        print("Start liver segmentation using device :", device)

        model_path = os.path.join(os.path.dirname(__file__), "liver_ct_model.pt")
        model = cls.createUNetModel(device=device)
        model.load_state_dict(torch.load(model_path, map_location=device))

        transform_output = cls.getPreprocessingTransform()(in_out_volume_node)
        model_input = transform_output['volume'].to(device)

        print("Run UNet model on input volume using sliding window inference")
        model_output = sliding_window_inference(model_input, (160, 160, 160), 4, model)

        print("Keep largest connected components and threshold UNet output")
        # Convert output to discrete

        monai_version = [int(v) for v in monai.__version__.split(".")][:3]
        # Keep largest connected components (expected shape changed after monai 0.6.0)
        if monai_version >= [0, 6, 0]:
          discrete_output = AsDiscrete(argmax=True)(model_output.reshape(model_output.shape[-4:]))
          post_processed = KeepLargestConnectedComponent(applied_labels=[1])(discrete_output)
          output_volume = post_processed.cpu().numpy()[0, :, :, :]
        else:
          discrete_output = AsDiscrete(argmax=True)(model_output)
          post_processed = KeepLargestConnectedComponent(applied_labels=[1])(discrete_output)
          output_volume = post_processed.cpu().numpy()[0, 0, :, :, :]

        del post_processed, model_output, discrete_output, model, model_input

        transform_output["volume"] = output_volume
        original_spacing = (transform_output["volume_meta_dict"]["original_spacing"])
        output_inverse_transform = cls.getPostProcessingTransform(original_spacing)(transform_output)
        label_map_input = output_inverse_transform["volume"][0, :, :, :]
        print("Output label map shape :", label_map_input.shape)

        output_affine_matrix = transform_output["volume_meta_dict"]["affine"]
        in_out_volume_node.SetIJKToRASMatrix(slicer.util.vtkMatrixFromArray(output_affine_matrix))
        slicer.util.updateVolumeFromArray(in_out_volume_node, np.swapaxes(label_map_input, 0, 2))
        del transform_output

    finally:
      # Cleanup any remaining memory
      def del_local(v):
        if v in locals():
          del locals()[v]

      for n in ["model_input", "model_output", "post_processed", "model", "transform_output"]:
        del_local(n)

      gc.collect()
      torch.cuda.empty_cache()
