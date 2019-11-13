from collections import defaultdict
from itertools import count

import qt
import slicer
import vtk

from RVesselXLib import Icons, getMarkupIdPositionDictionary, jumpSlicesToNthMarkupPosition, \
  createMultipleMarkupFiducial, createButton


class VesselBranchTreeItem(qt.QTreeWidgetItem):
  """Helper class holding nodeId and nodeName in the VesselBranchTree
  """

  def __init__(self, nodeId, nodeName):
    qt.QTreeWidgetItem.__init__(self)
    self.setText(0, nodeName)
    self.nodeId = nodeId
    self.nodeName = nodeName
    self.setIcon(1, Icons.delete)


class VesselBranchTree(qt.QTreeWidget):
  """Tree representation of vessel branch nodes.

  Class enables inserting new vessel node branches after or before existing nodes.
  Class signals when modified or user interacts with the UI.
  """

  class Signal(object):
    """List of signals handled by VesselBranchTree. To add observer, see VesselBranchTree.addObserver method
    """
    _iSig = count(0, 1)
    clicked = next(_iSig)  # callback(nodeId, qt.QKeyModifiers)
    keyEvent = next(_iSig)  # callback(nodeId, qt.QKey)
    modified = next(_iSig)  # callback()

  def __init__(self, parent=None):
    qt.QTreeWidget.__init__(self, parent)

    self._branchDict = {}
    self._callbackDict = defaultdict(list)

    # Configure tree widget
    self.setColumnCount(2)
    self.setHeaderLabels(["Branch Node Name", ""])

    # Configure tree to have first section stretched and last sections to be at right of the layout
    # other columns will always be at minimum size fitting the icons
    self.header().setSectionResizeMode(0, qt.QHeaderView.Stretch)
    self.header().setStretchLastSection(False)
    self.header().setSectionResizeMode(1, qt.QHeaderView.ResizeToContents)
    self.headerItem().setIcon(1, Icons.delete)

    # Enable reordering by drag and drop
    self.setDragEnabled(True)
    self.setDropIndicatorShown(True)
    self.setDragDropMode(qt.QAbstractItemView.InternalMove)

    # Connect click event to notify signal
    self.connect("itemClicked(QTreeWidgetItem*, int)", self._notifyItemClicked)

  def dropEvent(self, event):
    """On drop event, enforce structure of the tree is not broken.
    """
    qt.QTreeWidget.dropEvent(self, event)
    self.enforceOneRoot()
    self._notifyModified()

  def keyPressEvent(self, event):
    """Overridden from qt.QTreeWidget to notify listeners of key event

    Parameters
    ----------
    event: qt.QKeyEvent
    """
    if self.currentItem():
      currentNodeId = self.currentItem().nodeId
      for callback in self._callbackDict[VesselBranchTree.Signal.keyEvent]:
        callback(currentNodeId, event.key())

    qt.QTreeWidget.keyPressEvent(self, event)

  def _notifyItemClicked(self, item, column):
    """Notify each VesselBranchTree.Signal.clicked observers of click event associated with nodeId which was clicked on
    and the keyboard modifiers at the time of the click
    """
    if column == 1:
      for callback in self._callbackDict[VesselBranchTree.Signal.keyEvent]:
        callback(item.nodeId, qt.Qt.Key_Delete)
    else:
      item.setExpanded(True)
      for callback in self._callbackDict[VesselBranchTree.Signal.clicked]:
        callback(item.nodeId, qt.QGuiApplication.keyboardModifiers())

  def _notifyModified(self):
    """Notify each VesselBranchTree.Signal.modified observers of modification event
    """
    for callback in self._callbackDict[VesselBranchTree.Signal.modified]:
      callback()

  def addObserver(self, signal, callback):
    """
    Parameters
    ----------
    signal: int
      Signal contained in VesselBranchTree.Signal
    callback: Callable
    """
    self._callbackDict[signal].append(callback)

  def _takeItem(self, nodeId, nodeName=None):
    """Remove item with given item id from the tree. Removes it from its parent if necessary
    """
    if nodeId is None:
      return None
    elif nodeId in self._branchDict:
      nodeItem = self._branchDict[nodeId]
      self._removeFromParent(nodeItem)
      return nodeItem
    else:
      return VesselBranchTreeItem(nodeId, nodeName)

  def _removeFromParent(self, nodeItem):
    """Remove input node item from its parent if it is attached to an item or from the TreeWidget if at the root
    """
    parent = nodeItem.parent()
    if parent is not None:
      parent.removeChild(nodeItem)
    else:
      self.takeTopLevelItem(self.indexOfTopLevelItem(nodeItem))

  def _insertNode(self, nodeId, nodeName, parentId):
    """Insert the nodeId with input node name as child of the item whose name is parentId. If parentId is None, the item
    will be added as a root of the tree

    Parameters
    ----------
    nodeId: str
      Unique id of the node to add to the tree
    nodeName: str
      Name which will be shown in the tree widget of the new node
    parentId: str or None
      Unique id of the parent node. If None or "" will add node as root
    """
    nodeItem = self._takeItem(nodeId, nodeName)
    if not parentId:
      hasRoot = self.topLevelItemCount > 0
      self.addTopLevelItem(nodeItem)
      if hasRoot:
        rootItem = self.takeTopLevelItem(0)
        nodeItem.addChild(rootItem)
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
    self._notifyModified()

  def insertBeforeNode(self, nodeId, nodeName, childNodeId):
    """Insert given node before the input parent Id. Inserts new node as root if childNodeId is None.

    Parameters
    ----------
    nodeId: str
      Unique ID of the node to insert in the tree
    nodeName: str
      Representation label of the node
    childNodeId: str or None
      Unique ID of the child node before which the new node will be inserted. If None or "" will insert node at root.

    Raises
    ------
      ValueError
        If childNodeId is not None and doesn't exist in the tree
    """
    if not childNodeId:
      self._insertNode(nodeId, nodeName, None)
    else:
      parentNodeId = self.getParentNodeId(childNodeId)
      childItem = self._takeItem(childNodeId)
      nodeItem = self._insertNode(nodeId, nodeName, parentNodeId)
      nodeItem.addChild(childItem)

    self.expandAll()
    self._notifyModified()

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
    if nodeItem.childCount() > 1:
      return False
    else:
      # Delete root item
      self.takeTopLevelItem(0)
      del self._branchDict[nodeId]

      # Set child as new root item if necessary
      if nodeItem.childCount() == 1:
        child = nodeItem.takeChild(0)
        self.insertTopLevelItem(0, child)
        child.setExpanded(True)
      return True

  def _removeIntermediateItem(self, nodeItem, nodeId):
    """Move each child of node to node parent and remove item.
    """
    parentItem = nodeItem.parent()
    parentItem.takeChild(parentItem.indexOfChild(nodeItem))
    for child in nodeItem.takeChildren():
      parentItem.addChild(child)
    del self._branchDict[nodeId]

  def getParentNodeId(self, childNodeId):
    """

    Parameters
    ----------
    childNodeId: str
      Node for which we want the parent id

    Returns
    -------
    str or None
      Id of the parent item or None if node has no parent
    """
    parentItem = self._branchDict[childNodeId].parent()
    return parentItem.nodeId if parentItem is not None else None

  def getChildrenNodeId(self, parentNodeId):
    """
    Returns
    -------
    List[str]
      List of nodeIds of every children associated with parentNodeId
    """
    parent = self._branchDict[parentNodeId]
    return [parent.child(i).nodeId for i in range(parent.childCount())]

  def _getSibling(self, nodeId, nextIncrement):
    """
    Returns
    -------
    str or None
      nodeId sibling at iNode + nextIncrement index. None if new index is out of bounds
    """
    nodeItem = self._branchDict[nodeId]
    parent = nodeItem.parent()
    if parent is None:
      return None
    else:
      iSibling = parent.indexOfChild(nodeItem) + nextIncrement
      return parent.child(iSibling).nodeId if (0 <= iSibling < parent.childCount()) else None

  def getNextSiblingNodeId(self, nodeId):
    """
    Returns
    -------
    str or None
      nodeId sibling at iNode + 1 index. None if new index is out of bounds
    """
    return self._getSibling(nodeId, nextIncrement=1)

  def getPreviousSiblingNodeId(self, nodeId):
    """
    Returns
    -------
    str or None
      nodeId sibling at iNode - 1 index. None if new index is out of bounds
    """
    return self._getSibling(nodeId, nextIncrement=-1)

  def getRootNodeId(self):
    """
    Returns
    -------
    str or None
      nodeId of the first root of the tree. None if tree has no root item
    """
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
    """
    Returns
    -------
    List[str]
      List of every nodeIds referenced in the tree
    """
    return self._branchDict.keys()

  def isLeaf(self, nodeId):
    """
    Returns
    -------
    bool
      True if nodeId has no children item, False otherwise
    """
    return len(self.getChildrenNodeId(nodeId)) == 0

  def _getChildrenAdjacentLists(self, nodeItem):
    """
    Returns
    -------
    List[List[str]]
      List of every [parentId, childId] pair starting from nodeItem in the tree.
    """
    children = [nodeItem.child(i) for i in range(nodeItem.childCount())]
    nodeList = [[nodeItem.nodeId, child.nodeId] for child in children]
    for child in children:
      nodeList += self._getChildrenAdjacentLists(child)
    return nodeList

  def enforceOneRoot(self):
    """Reorders tree to have only one root item. If elements are defined after root, they will be inserted before
    current root. Methods is called during drop events.
    """
    # Early return if tree has at most one root
    if self.topLevelItemCount <= 1:
      return

    # Set current root as second item child
    newRoot = self.takeTopLevelItem(1)
    currentRoot = self.takeTopLevelItem(0)
    newRoot.addChild(currentRoot)

    # Add the new root to the tree
    self.insertTopLevelItem(0, newRoot)

    # Expand both items
    newRoot.setExpanded(True)
    currentRoot.setExpanded(True)

    # Call recursively until the whole tree has only one root
    self.enforceOneRoot()

    self._notifyModified()


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

    # Early return if tree is empty
    if not parentId:
      return []

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
    self._markupNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointEndInteractionEvent, self._onVesselBranchClicked)
    self._markupNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent,
                                 lambda *args: self._treeLine.updateTreeLines())

    self._tree = tree
    self._tree.addObserver(VesselBranchTree.Signal.clicked, self._onTreeClickEvent)
    self._tree.addObserver(VesselBranchTree.Signal.keyEvent, self._onKeyEvent)
    self._tree.addObserver(VesselBranchTree.Signal.modified, self._treeLine.updateTreeLines)
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

  def _onKeyEvent(self, nodeId, key):
    if key == qt.Qt.Key_Delete:
      # Remove node from tree
      wasRemoved = self._tree.removeNode(nodeId)

      # If node was successfully removed, update markup and treeLine
      if wasRemoved:
        # Update last node if it was removed
        if self._lastNode == nodeId:
          self._lastNode = self._tree.getRootNodeId()

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
    nodeId = self._markupNode.GetNthFiducialLabel(callData)
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
    self._updateActiveNode()

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
    """Adds a new node in the markupNode and insert this node in the tree depending on the previous node id.
    Newly added node becomes new root for later node added to the tree.

    If previous insertion mode was insert before, it is changed back to insert after current node to ease adding
    missed intersection and iterating from it to new vessel branch.
    """
    iNode = self._markupNode.GetNumberOfFiducials() - 1
    nodeName = self._markupNode.GetNthFiducialLabel(iNode)
    if self._insertMode == VesselBranchInteractor.SelectionMode.insertAfter:
      self._tree.insertAfterNode(nodeName, nodeName, self._lastNode)
    else:
      self._tree.insertBeforeNode(nodeName, nodeName, self._lastNode)
      self._insertMode = VesselBranchInteractor.SelectionMode.insertAfter
    self._lastNode = nodeName
    self._updateActiveNode()
    self._treeLine.updateTreeLines()

  def _updateActiveNode(self):
    for i in range(self._markupNode.GetNumberOfFiducials()):
      self._markupNode.SetNthFiducialSelected(i, self._markupNode.GetNthFiducialLabel(i) == self._lastNode)

  def setVisibleInScene(self, isVisible):
    self._treeLine.setVisible(isVisible)


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
    self._stopInteractionAction = self._createStopInteractionAction()

  def enableShortcuts(self, isEnabled):
    """Enables/Disables the shortcuts for the widget. If enabled, add node and edit node can be disabled by pressing
    escape key.
    """
    if isEnabled:
      slicer.util.mainWindow().addAction(self._stopInteractionAction)
    else:
      slicer.util.mainWindow().removeAction(self._stopInteractionAction)

  def _createStopInteractionAction(self):
    """
    Returns
    -------
    QAction
      When triggered, action will stop add node and edit node interactions
    """
    action = qt.QAction("Stop branch interaction", self)
    action.connect("triggered()", self.stopInteraction)
    action.setShortcut(qt.QKeySequence("esc"))
    return action

  def stopInteraction(self):
    """Stops add node and edit node interactions
    """
    if self._addBranchNodeButton.isChecked():
      self._stopAddBranchNode()

    if self._editBranchNodeButton.isChecked():
      self._stopEditBranchNode()

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
    """Create layout with Extract vessels, Add Node button and an Edit Node button

    Returns
    -------
    QLayout
    """

    # Create add and edit layout
    addEditButtonLayout = qt.QHBoxLayout()
    self._addBranchNodeButton = createButton("Add branching node", self._toggleAddBranchNode, isCheckable=True)
    self._editBranchNodeButton = createButton("Edit branching node", self._toggleEditBranchNode, isCheckable=True)
    addEditButtonLayout.addWidget(self._addBranchNodeButton)
    addEditButtonLayout.addWidget(self._editBranchNodeButton)

    # Create vertical layout and add Add and edit buttons on top of extract button
    buttonLayout = qt.QVBoxLayout()
    buttonLayout.addLayout(addEditButtonLayout)
    self.extractVesselsButton = createButton("Extract Vessels from node tree")
    buttonLayout.addWidget(self.extractVesselsButton)
    return buttonLayout

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

  def setVisibleInScene(self, isVisible):
    """If isVisible, markups and tree will be shown in scene, else they will be hidden
    """
    for i in range(self._markupNode.GetNumberOfFiducials()):
      self._markupNode.SetNthMarkupVisibility(i, isVisible)

    self._interactor.setVisibleInScene(isVisible)
