import logging
import vtk
import ctk
import qt
import slicer

from RVesselXLib import VesselTree, VesselnessFilterParameters, createSingleMarkupFiducial, \
  createMultipleMarkupFiducial, jumpSlicesToNthMarkupPosition
from VerticalLayoutWidget import VerticalLayoutWidget


class VesselBranchTreeItem(qt.QTreeWidgetItem):
  def __init__(self, nodeId, nodeName):
    qt.QTreeWidgetItem.__init__(self)
    self.setText(0, nodeName)
    self.nodeId = nodeId
    self.nodeName = nodeName


class VesselBranchTree(qt.QTreeWidget):
  """Tree representation of vessel branch nodes.

  Class enables inserting new vessel node branches after or before existing nodes.
  Class signals when modified or user interacts with the UI.
  """

  def __init__(self, parent=None):
    qt.QTreeWidget.__init__(self, parent)
    self.setHeaderLabel("Branch Node Name")
    self._branchDict = {}
    self._callbacks = []
    self.connect("itemClicked(QTreeWidgetItem*, int)", self._notifyItemClicked)

    self.setDragEnabled(True)
    self.setDropIndicatorShown(True)
    self.setDragDropMode(qt.QAbstractItemView.InternalMove)

  def _notifyItemClicked(self, item, column):
    item.setExpanded(True)
    for callback in self._callbacks:
      callback(item.nodeId, qt.QGuiApplication.keyboardModifiers())

  def addClickObserver(self, callback):
    self._callbacks.append(callback)

  def _takeItem(self, nodeId, nodeName=None):
    if nodeId is None:
      return None
    elif nodeId in self._branchDict:
      nodeItem = self._branchDict[nodeId]
      self._removeFromParent(nodeItem)
      return nodeItem
    else:
      return VesselBranchTreeItem(nodeId, nodeName)

  def _removeFromParent(self, nodeItem):
    parent = nodeItem.parent()
    if parent is not None:
      parent.removeChild(nodeItem)
    else:
      self.takeTopLevelItem(self.indexOfTopLevelItem(nodeItem))

  def _insertNode(self, nodeId, nodeName, parentId):
    nodeItem = self._takeItem(nodeId, nodeName)
    if parentId is None:
      self.addTopLevelItem(nodeItem)
    else:
      self._branchDict[parentId].addChild(nodeItem)

    self._branchDict[nodeId] = nodeItem
    return nodeItem

  def insertAfterNode(self, nodeId, nodeName, parentNodeId):
    """Insert given node after the input parent Id. Inserts new node as root if parentNodeId is None.
    If root is already present in the tree and insert after None is used, new node will become the parent of existing
    root node.

    Parameters
    ----------
    nodeId: str
      Unique ID of the node to insert in the tree
    nodeName: str
      Representation label of the node
    parentNodeId: str or None
      Unique ID of the parent node. If None, new node will be inserted as root.

    Raises
    ------
      ValueError
        If parentNodeId is not None and doesn't exist in the tree
    """
    self._insertNode(nodeId, nodeName, parentNodeId)
    self.expandAll()

  def insertBeforeNode(self, nodeId, nodeName, childNodeId):
    """Insert given node brefore the input parent Id. Inserts new node as root if childNodeId is None and tree is
    empty. If root is already present in the tree and child = None is used will raise an error.

    Parameters
    ----------
    nodeId: str
      Unique ID of the node to insert in the tree
    nodeName: str
      Representation label of the node
    childNodeId: str or None
      Unique ID of the child node before which the new node will be inserted.

    Raises
    ------
      ValueError
        If childNodeId is not None and doesn't exist in the tree
      ValueError
        If childNodeId is None and tree is not empty
    """
    if childNodeId is None and self.topLevelItemCount == 0:
      self._insertNode(nodeId, nodeName, None)
    else:
      parentNodeId = self.getParentNodeId(childNodeId)
      childItem = self._takeItem(childNodeId)
      nodeItem = self._insertNode(nodeId, nodeName, parentNodeId)
      nodeItem.addChild(childItem)

    self.expandAll()

  def removeNode(self, nodeId):
    nodeItem = self._branchDict[nodeId]
    parentItem = nodeItem.parent()
    parentItem.takeChild(parentItem.indexOfChild(nodeItem))
    for child in nodeItem.takeChildren():
      parentItem.addChild(child)

  def getParentNodeId(self, childNodeId):
    parentItem = self._branchDict[childNodeId].parent()
    return parentItem.nodeId if parentItem is not None else None

  def getChildrenNodeId(self, parentNodeId):
    parent = self._branchDict[parentNodeId]
    return [parent.child(i).nodeId for i in range(parent.childCount())]

  def _getSibling(self, nodeId, nextIncrement):
    nodeItem = self._branchDict[nodeId]
    parent = nodeItem.parent()
    if parent is None:
      return None
    else:
      iSibling = parent.indexOfChild(nodeItem) + nextIncrement
      return parent.child(iSibling).nodeId if (0 <= iSibling < parent.childCount()) else None

  def getNextSiblingNodeId(self, nodeId):
    return self._getSibling(nodeId, nextIncrement=1)

  def getPreviousSiblingNodeId(self, nodeId):
    return self._getSibling(nodeId, nextIncrement=-1)

  def getRootNodeId(self):
    return self.topLevelItem(0).nodeId if self.topLevelItemCount > 0 else None

  def getTreeParentList(self):
    """Returns tree as adjacent list in the format [[parentId, childId_1], [parentId, childId_2], ...].
    Root adjacent list is listed as [None, RootId]. List is constructed in breadth first manner from root to leaf.

    Returns
    -------
    List[List[str]] Representing adjacent list of the tree. List is empty if tree is emtpy.
    """
    roots = [self.topLevelItem(i) for i in range(self.topLevelItemCount)]
    treeParentList = [[None, root.nodeId] for root in roots]
    for root in roots:
      treeParentList += self._getChildrenAdjacentLists(root)

    return treeParentList

  def getNodeList(self):
    return self._branchDict.keys()

  def isLeaf(self, nodeId):
    return len(self.getChildrenNodeId(nodeId)) == 0

  def _getChildrenAdjacentLists(self, nodeItem):
    children = [nodeItem.child(i) for i in range(nodeItem.childCount())]
    nodeList = [[nodeItem.nodeId, child.nodeId] for child in children]
    for child in children:
      nodeList += self._getChildrenAdjacentLists(child)
    return nodeList


class VesselBranchInteractor(object):
  """
  Object responsible for handling interaction with the branch tree and the markup in the 3D and 2D views.
  Triggers slicer move to markup and selects the current parent node when markups are clicked with or without key
  modifiers
  """

  class SelectionMode(object):
    insertAfter = 1
    insertBefore = 2

  def __init__(self, tree, markupNode):
    """
    Parameters
    ----------
    tree: VesselBranchTree
    markupNode: slicer.vtkMRMLMarkupsFiducialNode
    """
    # Connect tree and markup events to interactor
    self._markupNode = markupNode
    self._markupNode.AddObserver(slicer.vtkMRMLMarkupsNode.MarkupAddedEvent, self._onVesselBranchAdded)
    self._markupNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointClickedEvent, self._onVesselBranchClicked)

    self._tree = tree
    self._tree.addClickObserver(self._onTreeClickEvent)
    self._insertMode = VesselBranchInteractor.SelectionMode.insertAfter
    self._lastNode = None

  def getSelectedNode(self):
    """
    Returns
    -------
    str or None - Currently selected node Id
    """
    return self._lastNode

  def getInsertionMode(self):
    """
    Returns
    -------
    VesselBranchInteractor.SelectionMode - Node insertion mode (insert after selected node or before)
    """
    return self._insertMode

  def _onTreeClickEvent(self, nodeId, keyboardModifier):
    self._selectCurrentNode(nodeId, keyboardModifier)

  @vtk.calldata_type(vtk.VTK_INT)
  def _onVesselBranchClicked(self, caller, eventId, callData):
    nodeId = self._markupNode.GetNthFiducialAssociatedNodeID(callData)
    self._selectCurrentNode(nodeId, qt.QGuiApplication.keyboardModifiers())

  def _selectCurrentNode(self, nodeId, keyboardModifier):
    """Select node for insertion after or before of next branch. Click will insert after node, shift + click will insert
    before node

    Parameters
    ----------
    nodeId: str
      Id of the node on which the user has clicked
    keyboardModifier: qt.Qt.KeyboardModifiers
      Keys held by user when clicking on the node
    """
    self._insertMode = VesselBranchInteractor.SelectionMode.insertAfter if not keyboardModifier & qt.Qt.ShiftModifier else VesselBranchInteractor.SelectionMode.insertBefore
    self._lastNode = nodeId
    self._jumpSlicesToNode(nodeId)

  def _jumpSlicesToNode(self, nodeId):
    """Center all slices to input node position

    Parameters
    ----------
    nodeId: str
      Id of the node we want to center on
    """
    jumpSlicesToNthMarkupPosition(self._markupNode, self._nodeIndex(nodeId))

  def _nodeIndex(self, nodeId):
    """
    Parameters
    ----------
    nodeId: str
      Id of the node for which we want the index in the vessel branch node

    Returns
    -------
    int or None
      Markup index associated with id if found else None
    """
    for i in range(self._markupNode.GetNumberOfFiducials()):
      if self._markupNode.GetNthFiducialLabel(i) == nodeId:
        return i
    return None

  def _onVesselBranchAdded(self, *args):
    iNode = self._markupNode.GetNumberOfFiducials() - 1
    nodeName = self._markupNode.GetNthFiducialLabel(iNode)
    if self._insertMode == VesselBranchInteractor.SelectionMode.insertAfter:
      self._tree.insertAfterNode(nodeName, nodeName, self._lastNode)
    else:
      self._tree.insertBeforeNode(nodeName, nodeName, self._lastNode)
    self._lastNode = nodeName


class VesselBranchWidget(qt.QWidget):
  def __init__(self, parent=None):
    qt.QWidget.__init__(self, parent)

    # Create Markups interactors
    self._createVesselsIBranchMarkup()

    # Create layout for the widget
    widgetLayout = qt.QVBoxLayout()
    self._branchTree = VesselBranchTree()
    widgetLayout.addLayout(self._createButtonLayout())
    widgetLayout.addWidget(self._branchTree)
    self.setLayout(widgetLayout)
    self._interactor = VesselBranchInteractor(self._branchTree, self._markupNode)

  def _createVesselsIBranchMarkup(self):
    self._markupNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
    self._markupNode.SetName("node")

    # Markup node selector will not be shown sor tooltip and markup names are unnecessary
    self._markupNodeSelector = createMultipleMarkupFiducial(toolTip="", markupName="")
    self._markupNodeSelector.markupsPlaceWidget().connect("activeMarkupsPlaceModeChanged(bool)",
                                                          self._placeMarkupChanged)

  def _placeMarkupChanged(self, enabled):
    if self._markupNodeSelector.currentNode() == self._markupNode:
      self._markupNode.SetLocked(enabled)

  def _createButtonLayout(self):
    buttonLayout = qt.QHBoxLayout()
    buttonLayout.addWidget(self._createButton("Add Intersections", self._addBranchNode))
    buttonLayout.addWidget(self._createButton("Edit Intersections", self._editBranchNode))
    return buttonLayout

  def _createButton(self, name, callback):
    button = qt.QPushButton(name)
    button.connect("clicked(bool)", callback)
    return button

  def _addBranchNode(self):
    # Activate vessel node and set markups place to true
    self._markupNodeSelector.setCurrentNode(self._markupNode)
    self._markupNodeSelector.markupsPlaceWidget().setPlaceModeEnabled(True)

  def _editBranchNode(self):
    # Deactivate vessel intersection add and enable markup node displacement
    self._markupNodeSelector.markupsPlaceWidget().setPlaceModeEnabled(False)
    self._markupNode.SetLocked(False)

  def getBranchTree(self):
    return self._branchTree

  def getBranchMarkupNode(self):
    return self._markupNode


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
    self._vesselIntersectionWidget = VesselBranchWidget()

    # Visualisation tree for Vessels
    self._vesselTree = VesselTree(self._logic)
    self._createUpdateVesselsButton()

    self._verticalLayout.addWidget(self._vesselIntersectionWidget)
    self._verticalLayout.addWidget(self._createExtractVesselButton())
    self._verticalLayout.addWidget(self._createAdvancedVesselnessFilterOptionWidget())

    # Connect vessel tree edit change to update add button status
    self._updateButtonStatusAndFilterParameters()
    self._vesselTree.addEditChangedCallback(self._updateButtonStatusAndFilterParameters)

  def _createExtractVesselButton(self):
    """Creates add vessel button responsible for adding new row in the tree.

    Returns
    ------
    QPushButton
    """
    # Add Vessel Button
    self._addVesselButton = qt.QPushButton("Extract Vessel")
    self._addVesselButton.connect("clicked(bool)", self._extractVessel)
    return self._addVesselButton

  def _extractVessel(self):
    from ExtractVesselStrategies import ExtractAllVesselsInOneGoStrategy, ExtractOneVesselPerBranch
    branchTree = self._vesselIntersectionWidget.getBranchTree()
    branchMarkupNode = self._vesselIntersectionWidget.getBranchMarkupNode()
    strategy = ExtractOneVesselPerBranch()
    strategy.extractVesselVolumeFromVesselBranchTree(branchTree, branchMarkupNode, self._logic)

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
    if self._vesselTree.vesselCount() > 0:
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
