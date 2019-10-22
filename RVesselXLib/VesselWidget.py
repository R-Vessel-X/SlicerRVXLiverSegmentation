import qt

from RVesselXUtils import createSingleMarkupFiducial
from VerticalLayoutWidget import VerticalLayoutWidget
from Vessel import VesselTree


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
    :param logic: RVesselXModuleLogic
    """
    VerticalLayoutWidget.__init__(self)

    self._vesselStartSelector = None
    self._vesselEndSelector = None
    self._vesselTree = None
    self._vesselnessVolume = None
    self._inputVolume = None
    self._logic = logic

    # Visualisation tree for Vessels
    self._vesselTree = VesselTree()
    self._verticalLayout.addWidget(self._vesselTree.getWidget())
    self._verticalLayout.addLayout(self._createExtractVesselLayout())

  def _createExtractVesselLayout(self):
    """Creates Layout with vessel start point selector, end point selector and extract vessel button. Button is set to
    be active only when input volume, start and end points are valid.

    Returns
    ------
    QFormLayout
    """
    formLayout = qt.QFormLayout()

    # Start point fiducial
    vesselPointName = "vesselPoint"
    self._vesselStartSelector = createSingleMarkupFiducial("Select vessel start position", vesselPointName)
    formLayout.addRow("Vessel Start:", self._vesselStartSelector)

    # End point fiducial
    self._vesselEndSelector = createSingleMarkupFiducial("Select vessel end position", vesselPointName)
    formLayout.addRow("Vessel End:", self._vesselEndSelector)

    # Extract Vessel Button
    self._extractVesselButton = qt.QPushButton("Extract Vessel")
    self._extractVesselButton.connect("clicked(bool)", self._extractVessel)
    self._extractVesselButton.setToolTip(
      "Select vessel start point, vessel end point, and volume then press Extract button to extract vessel")
    formLayout.addRow("", self._extractVesselButton)

    self._vesselStartSelector.connect("updateFinished()", self._updateExtractButtonStatus)
    self._vesselEndSelector.connect("updateFinished()", self._updateExtractButtonStatus)

    return formLayout

  def _updateExtractButtonStatus(self):
    """
    Check whether the extract vessel button should be activated or not.
    """

    def getNode(node):
      return node.currentNode()

    def fiducialSelected(seedSelector):
      return getNode(seedSelector) and getNode(seedSelector).GetNumberOfFiducials() > 0

    isButtonEnabled = self._inputVolume and fiducialSelected(self._vesselStartSelector) and fiducialSelected(
      self._vesselEndSelector)
    self._extractVesselButton.setEnabled(isButtonEnabled)

  def setInputNode(self, node):
    """
    On input changed and valid, change current input node and reset vesselness volume used in VMTK algorithms.

    :param node: vtkMRMLNode
    """
    if node and node != self._inputVolume:
      self._vesselnessVolume = None
      self._inputVolume = node
      self._updateExtractButtonStatus()

  def _extractVessel(self):
    """Creates vessel from vessel tab start point, end point and selected data. Created vessel is added to VesselTree
    view in Vessel tab.
    """
    sourceVolume = self._inputVolume
    startPoint = self._vesselStartSelector.currentNode()
    endPoint = self._vesselEndSelector.currentNode()

    vessel = self._logic.extractVessel(sourceVolume=sourceVolume, startPoint=startPoint, endPoint=endPoint,
                                       vesselnessVolume=self._vesselnessVolume)
    self._vesselnessVolume = vessel.vesselnessVolume
    self._vesselTree.addVessel(vessel)

    # Set vessel start node as end node and remove end node selection for easier leaf selection for user
    self._vesselStartSelector.setCurrentNode(self._vesselEndSelector.currentNode())
    self._vesselEndSelector.setCurrentNode(None)

  def getGeometryExporters(self):
    return self._vesselTree.getVesselGeometryExporters()
