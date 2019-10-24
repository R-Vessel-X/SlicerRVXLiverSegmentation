import qt

from RVesselXUtils import createSingleMarkupFiducial
from VerticalLayoutWidget import VerticalLayoutWidget
from RVesselXLib import VesselTree


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
    VerticalLayoutWidget.__init__(self)

    self._vesselStartSelector = None
    self._vesselEndSelector = None
    self._vesselTree = None
    self._vesselnessVolume = None
    self._inputVolume = None
    self._logic = logic

    # Visualisation tree for Vessels
    self._vesselTree = VesselTree(self._logic)
    self._verticalLayout.addWidget(self._vesselTree.getWidget())
    self._verticalLayout.addLayout(self._createExtractVesselLayout())

    # Connect vessel tree edit change to update add button status
    self._vesselTree.addEditChangedCallback(self._updateAddButtonStatus)

  def _createExtractVesselLayout(self):
    """Creates Layout with vessel start point selector, end point selector and extract vessel button. Button is set to
    be active only when input volume, start and end points are valid.

    Returns
    ------
    QFormLayout
    """
    formLayout = qt.QFormLayout()

    # Add Vessel Button
    self._addVesselButton = qt.QPushButton("Add Vessel")
    self._addVesselButton.connect("clicked(bool)", self._vesselTree.addNewVessel)
    formLayout.addRow("", self._addVesselButton)
    self._updateAddButtonStatus()

    return formLayout

  def _updateAddButtonStatus(self):
    self._addVesselButton.setEnabled(self._inputVolume is not None and not self._vesselTree.isEditing())

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
      self._updateAddButtonStatus()

  def getGeometryExporters(self):
    return self._vesselTree.getVesselGeometryExporters()
