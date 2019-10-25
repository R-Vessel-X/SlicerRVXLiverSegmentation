import ctk
import qt

from RVesselXLib import VesselTree, VesselnessFilterParameters, createSingleMarkupFiducial
from VerticalLayoutWidget import VerticalLayoutWidget


class VesselWidget(VerticalLayoutWidget):
  """ Vessels Widget interfaces the Vessels Modelisation ToolKit in one aggregated view.

  Integration includes :
      Vesselness filtering : visualization help to extract vessels
      Level set segmentation : segmentation tool for the vessels
      Center line computation : Extraction of the vessels endpoints from 3D vessels and start point
      Vessels tree : View tree to select, add, show / hide vessels
  """

  def __init__(self, logic):
    """
    Parameters
    ----------
    logic: RVesselXModuleLogic
    """
    VerticalLayoutWidget.__init__(self, "Vessel Tab")

    self._vesselStartSelector = None
    self._vesselEndSelector = None
    self._vesselTree = None
    self._vesselnessVolume = None
    self._inputVolume = None
    self._logic = logic

    # Visualisation tree for Vessels
    self._vesselTree = VesselTree(self._logic)
    self._verticalLayout.addWidget(self._createAddVesselButton())
    self._verticalLayout.addWidget(self._vesselTree.getWidget())
    self._verticalLayout.addWidget(self._createUpdateVesselsButton())
    self._verticalLayout.addWidget(self._createAdvancedVesselnessFilterOptionWidget())

    # Connect vessel tree edit change to update add button status
    self._updateButtonStatusAndFilterParameters()
    self._vesselTree.addEditChangedCallback(self._updateButtonStatusAndFilterParameters)

  def _createAddVesselButton(self):
    """Creates add vessel button responsible for adding new row in the tree.

    Returns
    ------
    QPushButton
    """
    # Add Vessel Button
    self._addVesselButton = qt.QPushButton("Add Vessel")
    self._addVesselButton.connect("clicked(bool)", self._vesselTree.addNewVessel)
    return self._addVesselButton

  def _createAdvancedVesselnessFilterOptionWidget(self):
    filterOptionCollapsibleButton = ctk.ctkCollapsibleButton()
    filterOptionCollapsibleButton.text = "Vesselness Filter Options"
    filterOptionCollapsibleButton.collapsed = True
    advancedFormLayout = qt.QFormLayout(filterOptionCollapsibleButton)

    # Add markups selector
    self._vesselnessAutoContrastPoint = createSingleMarkupFiducial(
      "Selected point will enable calculating max vessel diameter and contrast", markupName="vesselnessPoint",
      markupColor=qt.QColor("green"))
    advancedFormLayout.addRow("Auto contrast source (optional)", self._vesselnessAutoContrastPoint)

    self._minimumDiameterSpinBox = qt.QSpinBox()
    self._minimumDiameterSpinBox.minimum = 1
    self._minimumDiameterSpinBox.maximum = 1000
    self._minimumDiameterSpinBox.singleStep = 1
    self._minimumDiameterSpinBox.suffix = " voxels"
    self._minimumDiameterSpinBox.toolTip = "Tubular structures that have minimum this diameter will be enhanced."
    advancedFormLayout.addRow("Minimum vessel diameter:", self._minimumDiameterSpinBox)

    self._maximumDiameterSpinBox = qt.QSpinBox()
    self._maximumDiameterSpinBox.minimum = 0
    self._maximumDiameterSpinBox.maximum = 1000
    self._maximumDiameterSpinBox.singleStep = 1
    self._maximumDiameterSpinBox.suffix = " voxels"
    self._maximumDiameterSpinBox.toolTip = "Tubular structures that have maximum this diameter will be enhanced."
    advancedFormLayout.addRow("Maximum vessel diameter:", self._maximumDiameterSpinBox)

    self._contrastSlider = ctk.ctkSliderWidget()
    self._contrastSlider.decimals = 0
    self._contrastSlider.minimum = 0
    self._contrastSlider.maximum = 500
    self._contrastSlider.singleStep = 10
    self._contrastSlider.toolTip = "If the intensity contrast in the input image between vessel and background is high, choose a high value else choose a low value."
    advancedFormLayout.addRow("Vessel contrast:", self._contrastSlider)

    self._suppressPlatesSlider = ctk.ctkSliderWidget()
    self._suppressPlatesSlider.decimals = 0
    self._suppressPlatesSlider.minimum = 0
    self._suppressPlatesSlider.maximum = 100
    self._suppressPlatesSlider.singleStep = 1
    self._suppressPlatesSlider.suffix = " %"
    self._suppressPlatesSlider.toolTip = "A higher value filters out more plate-like structures."
    advancedFormLayout.addRow("Suppress plates:", self._suppressPlatesSlider)

    self._suppressBlobsSlider = ctk.ctkSliderWidget()
    self._suppressBlobsSlider.decimals = 0
    self._suppressBlobsSlider.minimum = 0
    self._suppressBlobsSlider.maximum = 100
    self._suppressBlobsSlider.singleStep = 1
    self._suppressBlobsSlider.suffix = " %"
    self._suppressBlobsSlider.toolTip = "A higher value filters out more blob-like structures."
    advancedFormLayout.addRow("Suppress blobs:", self._suppressBlobsSlider)

    # Reset, preview and apply buttons
    restoreDefaultButton = qt.QPushButton("Restore")
    restoreDefaultButton.toolTip = "Click to reset all input elements to default."
    restoreDefaultButton.connect("clicked()", self._restoreDefaultVesselnessFilterParameters)
    advancedFormLayout.addRow("Restore default filter parameters :", restoreDefaultButton)
    self._restoreDefaultVesselnessFilterParameters()

    return filterOptionCollapsibleButton

  def _createUpdateVesselsButton(self):
    self._updateVesselsButton = qt.QPushButton()
    self._updateVesselsButton.text = "Update extracted vessels"
    self._updateVesselsButton.enabled = False
    self._updateVesselsButton.connect("clicked()", self._updateAllVessels)
    return self._updateVesselsButton

  def _restoreDefaultVesselnessFilterParameters(self):
    """Apply default vesselness filter parameters to the UI
    """
    defaultParams = VesselnessFilterParameters()
    self._updateVesselnessFilterParameters(defaultParams)

  def _updateVesselnessFilterParameters(self, params):
    """Updates UI vessel filter parameters with the input VesselnessFilterParameters

    Parameters
    ----------
    params: VesselnessFilterParameters
    """
    self._minimumDiameterSpinBox.value = params.minimumDiameter
    self._maximumDiameterSpinBox.value = params.maximumDiameter
    self._suppressPlatesSlider.value = params.suppressPlatesPercent
    self._suppressBlobsSlider.value = params.suppressBlobsPercent
    self._contrastSlider.value = params.vesselContrast

  def _updateAllVessels(self):
    """Sets UI Vessel filter parameters to the logic and trigger an update for all vessels in tree. Method is disabled
    if no vessel is in the tree.
    """
    if self._vesselTree.vesselCount() > 0 :
      # Get parameters from current advanced option parameters
      parameters = VesselnessFilterParameters()
      parameters.minimumDiameter = self._minimumDiameterSpinBox.value
      parameters.maximumDiameter = self._maximumDiameterSpinBox.value
      parameters.suppressPlatesPercent = self._suppressPlatesSlider.value
      parameters.suppressBlobsPercent = self._suppressBlobsSlider.value
      parameters.vesselContrast = self._contrastSlider.value
      self._logic.vesselnessFilterParameters = parameters

      # Explicitly call vesselness filter update
      startPoint = self._vesselnessAutoContrastPoint.getCurrentNode()
      self._logic.updateVesselnessFilter(startPoint)

      # Update vessels in tree
      self._vesselTree.updateItemVessels()

      # Update parameters
      self._updateVesselnessFilterParameters(self._logic.vesselnessFilterParameters)

  def _updateButtonStatusAndFilterParameters(self):
    """Enable buttons if input volume was selected by user and Tree is not in edit mode. When tree is done with editing
    and vessels populate the tree, vessels can be updated using new filter parameters.
    """
    isEnabled = self._inputVolume is not None and not self._vesselTree.isEditing()
    self._addVesselButton.setEnabled(isEnabled)
    self._updateVesselsButton.setEnabled(isEnabled and self._vesselTree.vesselCount() > 0)
    self._updateVesselnessFilterParameters(self._logic.vesselnessFilterParameters)

  def setInputNode(self, node):
    """
    On input changed and valid, change current input node and reset vesselness volume used in VMTK algorithms.

    Parameters
    ----------
    node: vtkMRMLNode
    """
    if node and node != self._inputVolume:
      self._vesselnessVolume = None
      self._inputVolume = node
      self._logic.setInputVolume(node)
      self._updateButtonStatusAndFilterParameters()

  def getGeometryExporters(self):
    return self._vesselTree.getVesselGeometryExporters()
