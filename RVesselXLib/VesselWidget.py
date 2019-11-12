import logging
import vtk
import ctk
import qt
import slicer

from RVesselXLib import VesselTree, VesselnessFilterParameters, createSingleMarkupFiducial, \
  createMultipleMarkupFiducial, jumpSlicesToNthMarkupPosition, GeometryExporter, getMarkupIdPositionDictionary
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
    self._clickEventCallbacks = []
    self._keyEventCallbacks = []
    self.connect("itemClicked(QTreeWidgetItem*, int)", self._notifyItemClicked)

    self.setDragEnabled(True)
    self.setDropIndicatorShown(True)
    self.setDragDropMode(qt.QAbstractItemView.InternalMove)

  def keyPressEvent(self, event):
    """Overridden from qt.QTreeWidget to notify listeners of key event

    Parameters
    ----------
    event: qt.QKeyEvent
    """
    currentNodeId = self.currentItem().nodeId
    for callback in self._keyEventCallbacks:
      callback(currentNodeId, event)

    qt.QTreeWidget.keyPressEvent(self, event)

  def _notifyItemClicked(self, item, column):
    item.setExpanded(True)
    for callback in self._clickEventCallbacks:
      callback(item.nodeId, qt.QGuiApplication.keyboardModifiers())

  def addClickObserver(self, callback):
    self._clickEventCallbacks.append(callback)

  def addKeyObserver(self, callback):
    self._keyEventCallbacks.append(callback)

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
    """Remove given node from tree.

    If node is root, only remove if it has exactly one direct child and replace root by child. Else does nothing.
    If intermediate item, move each child of node to node parent.

    Parameters
    ----------
    nodeId: str
      Id of the node to remove from tree

    Returns
    -------
    bool - True if node was removed, False otherwise
    """
    nodeItem = self._branchDict[nodeId]
    if nodeItem.parent() is None:
      return self._removeRootItem(nodeItem, nodeId)
    else:
      self._removeIntermediateItem(nodeItem, nodeId)
      return True

  def _removeRootItem(self, nodeItem, nodeId):
    """Only remove if it has exactly one direct child and replace root by child. Else does nothing.

    Returns
    -------
    bool - True if root item was removed, False otherwise
    """
    if nodeItem.childCount() == 1:
      self.takeTopLevelItem(0)
      child = nodeItem.takeChild(0)
      self.insertTopLevelItem(0, child)
      child.setExpanded(True)
      del self._branchDict[nodeId]
      return True
    return False

  def _removeIntermediateItem(self, nodeItem, nodeId):
    """Move each child of node to node parent and remove item.
    """
    parentItem = nodeItem.parent()
    parentItem.takeChild(parentItem.indexOfChild(nodeItem))
    for child in nodeItem.takeChildren():
      parentItem.addChild(child)
    del self._branchDict[nodeId]

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


class TreeDrawer(object):
  """
  Class responsible for drawing lines between the different vessel nodes
  """

  def __init__(self, vesselTree, markupFiducial):
    """
    Parameters
    ----------
    vesselTree: VesselBranchTree
    markupFiducial: vtkMRMLMarkupsFiducialNode
    """
    self._tree = vesselTree
    self._markupFiducial = markupFiducial

    self._polyLine = vtk.vtkPolyLineSource()
    self._polyLine.SetClosed(False)
    self._lineModel = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
    self._lineModel.SetAndObservePolyData(self._polyLine.GetOutput())
    self._lineModel.CreateDefaultDisplayNodes()
    self._lineModel.SetName("VesselBranchNodeTree")
    self._updateNodeCoordDict()

  def _updateNodeCoordDict(self):
    """Update node coordinates associated with node ID for the current tree

    Returns
    -------
    Dict[str, List[float]]
      Dictionary containing the node ids contained in the markup node and its associated positions
    """
    self._nodeCoordDict = getMarkupIdPositionDictionary(self._markupFiducial)

  def updateTreeLines(self):
    """Updates the lines between the different nodes of the tree. Uses the last set line width and color
    """
    # Update nodes coordinates
    self._updateNodeCoordDict()

    # Force modification by resetting number of points to 0 (other wise update will not be visible if only points
    # position has changed)
    self._polyLine.SetNumberOfPoints(0)
    coordList = self._extractTreeLinePointSequence()
    self._polyLine.SetNumberOfPoints(len(coordList))
    for i, coord in enumerate(coordList):
      self._polyLine.SetPoint(i, *coord)

    # Trigger poly line update
    self._polyLine.Update()

  def _extractTreeLinePointSequence(self, parentId=None):
    """Constructs a coordinate sequence starting from parentId node recursively.

    example :
    parent
      |_ child
            |_ sub child
      |_ child2

    Previous tree will generate coordinates : [parent, child, sub child, child, parent, child2, parent]
    This coordinate construction enables using only one poly line instead of multiple lines at the expense of
    constructed lines number

    Parameters
    ----------
    parentId: str or None
      Starting point of the recursion. If none, will start from tree root

    Returns
    -------
    List[List[float]]
      Coordinate sequence for polyLine construction
    """
    if parentId is None:
      parentId = self._tree.getRootNodeId()

    parentCoord = self._nodeCoordinate(parentId)
    pointSeq = [parentCoord]
    for childId in self._tree.getChildrenNodeId(parentId):
      pointSeq += self._extractTreeLinePointSequence(childId)
      pointSeq.append(parentCoord)
    return pointSeq

  def _nodeCoordinate(self, nodeId):
    return self._nodeCoordDict[nodeId]

  def setColor(self, lineColor):
    """
    Parameters
    ----------
    lineColor: qt.QColor
      New color for line. Call updateTreeLines to apply to tree.
    """
    self._lineModel.GetDisplayNode().SetColor(lineColor.red(), lineColor.green(), lineColor.blue())

  def setLineWidth(self, lineWidth):
    """
    Parameters
    ----------
    lineWidth: float
      New line width for lines of the tree.  Call updateTreeLines to apply to tree.
    """
    self._lineModel.GetDisplayNode().SetLineWidth(lineWidth)

  def setVisible(self, isVisible):
    """
    Parameters
    ----------
    isVisible: bool
      If true, will show tree in mrmlScene. Else will hide tree model
    """
    self._lineModel.SetDisplayVisibility(isVisible)


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
    # Representation of the tree
    self._treeLine = TreeDrawer(vesselTree=tree, markupFiducial=markupNode)
    self._treeLine.setColor(qt.QColor("red"))
    self._treeLine.setLineWidth(4.0)

    # Connect tree and markup events to interactor
    self._markupNode = markupNode
    self._markupNode.AddObserver(slicer.vtkMRMLMarkupsNode.MarkupAddedEvent, self._onVesselBranchAdded)
    self._markupNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointClickedEvent, self._onVesselBranchClicked)
    self._markupNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent,
                                 lambda *args: self._treeLine.updateTreeLines())

    self._tree = tree
    self._tree.addClickObserver(self._onTreeClickEvent)
    self._tree.addKeyObserver(self._onKeyEvent)
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

  def _onKeyEvent(self, nodeId, keyEvent):
    if keyEvent.key() == qt.Qt.Key_Delete:
      # Remove node from tree
      wasRemoved = self._tree.removeNode(nodeId)

      # If node was successfully removed, update markup and treeLine
      if wasRemoved:
        # Remove node from markup
        self._removeFromMarkup(nodeId)

        # Update showed lines
        self._treeLine.updateTreeLines()

  def _removeFromMarkup(self, nodeId):
    for i in range(self._markupNode.GetNumberOfFiducials()):
      if self._markupNode.GetNthFiducialLabel(i) == nodeId:
        self._markupNode.SetNthFiducialVisibility(i, False)

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
    self._treeLine.updateTreeLines()

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
    self._treeLine.updateTreeLines()


class VesselBranchWidget(qt.QWidget):
  """Class holding the widgets for vessel branch node edition.

  Creates the node edition buttons, branch node tree and starts and connects the branch markup node.
  """

  def __init__(self, parent=None):
    qt.QWidget.__init__(self, parent)

    # Create Markups node
    self._createVesselsBranchMarkupNode()

    # Create layout for the widget
    widgetLayout = qt.QVBoxLayout()
    self._branchTree = VesselBranchTree()
    widgetLayout.addLayout(self._createButtonLayout())
    widgetLayout.addWidget(self._branchTree)
    self.setLayout(widgetLayout)
    self._interactor = VesselBranchInteractor(self._branchTree, self._markupNode)

  def _createVesselsBranchMarkupNode(self):
    """Creates markup node and node selector and connect the interaction node modified event to node status update.
    """
    self._markupNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
    self._markupNode.SetName("node")

    # Markup node selector will not be shown sor tooltip and markup names are unnecessary
    self._markupNodeSelector = createMultipleMarkupFiducial(toolTip="", markupName="")

    # Connect scene interaction node to add node update
    interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
    if interactionNode is not None:
      interactionNode.AddObserver(vtk.vtkCommand.ModifiedEvent, lambda *x: self._updateAddNodeStatus())

  def _createButtonLayout(self):
    """Create layout with and Add Node button and an Edit Node button

    Returns
    -------
    QHBoxLayout
    """
    buttonLayout = qt.QHBoxLayout()
    self._addBranchNodeButton = self._createButton("Add branching node", self._toggleAddBranchNode, isCheckable=True)
    self._editBranchNodeButton = self._createButton("Edit branching node", self._toggleEditBranchNode, isCheckable=True)
    buttonLayout.addWidget(self._addBranchNodeButton)
    buttonLayout.addWidget(self._editBranchNodeButton)
    return buttonLayout

  def _createButton(self, name, callback, isCheckable=False):
    """Helper method to create a button with a text, callback and checkable status

    Parameters
    ----------
    name: str
      Label of the button
    callback: Callable
      Called method when button is clicked
    isCheckable: bool
      If true, the button will be checkable

    Returns
    -------
    QPushButton
    """
    button = qt.QPushButton(name)
    button.connect("clicked(bool)", callback)
    button.setCheckable(isCheckable)
    return button

  def _updateAddNodeStatus(self):
    """Update add node button status. Call when the place mode has changed for the MRML scene
    """
    self._addBranchNodeButton.setChecked(self._markupNodeSelector.markupsPlaceWidget().placeModeEnabled)
    self._toggleAddBranchNode()

  def _toggleAddBranchNode(self):
    """Depending on the add branch node button checked states, either starts to add branch nodes or stop it
    """
    if self._addBranchNodeButton.isChecked():
      self._startAddBranchNode()
    else:
      self._stopAddBranchNode()

  def _startAddBranchNode(self):
    """Starts adding branch nodes in the scene by enabling markups selector place mode and stops branch node editing
    """
    self._stopEditBranchNode()
    self._markupNodeSelector.setCurrentNode(self._markupNode)
    self._markupNodeSelector.markupsPlaceWidget().setPlaceModeEnabled(True)
    self._addBranchNodeButton.setChecked(True)

  def _stopAddBranchNode(self):
    """Stops adding branch nodes in the scene
    """
    self._markupNodeSelector.markupsPlaceWidget().setPlaceModeEnabled(False)
    self._addBranchNodeButton.setChecked(False)

  def _toggleEditBranchNode(self):
    """Depending on the edit branch node button checked status, either starts branch node editing or stops it
    """
    if self._editBranchNodeButton.isChecked():
      self._startEditBranchNode()
    else:
      self._stopEditBranchNode()

  def _startEditBranchNode(self):
    """Starts node editing by unlocking markup node and stops node adding
    """
    self._stopAddBranchNode()
    self._markupNode.SetLocked(False)
    self._editBranchNodeButton.setChecked(True)

  def _stopEditBranchNode(self):
    """Stops node editing by locking markup node
    """
    self._markupNode.SetLocked(True)
    self._editBranchNodeButton.setChecked(False)

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
    self._vesselVolumeNode = None
    self._vesselModelNode = None
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
    from ExtractVesselStrategies import ExtractAllVesselsInOneGoStrategy, ExtractOneVesselPerBranch, \
      ExtractOneVesselPerParentAndSubChildNode
    branchTree = self._vesselIntersectionWidget.getBranchTree()
    branchMarkupNode = self._vesselIntersectionWidget.getBranchMarkupNode()
    strategy = ExtractOneVesselPerParentAndSubChildNode()
    self._vesselVolumeNode, self._vesselModelNode = strategy.extractVesselVolumeFromVesselBranchTree(branchTree,
                                                                                                     branchMarkupNode,
                                                                                                     self._logic)

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
    return [GeometryExporter(vesselsVolume=self._vesselVolumeNode, vesselsOuterMesh=self._vesselModelNode)]
