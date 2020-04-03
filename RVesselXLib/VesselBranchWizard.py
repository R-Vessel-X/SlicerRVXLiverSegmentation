import qt

from RVesselXLib import Signal


class VeinId(object):
  portalVein = "PortalVein"
  rightPortalVein = "RightPortalVein"
  leftPortalVein = "LeftPortalVein"
  anteriorBranch = "AnteriorBranch"
  posteriorBranch = "PosteriorBranch"
  segmentalBranch_2 = "SegmentalBranch_2"
  segmentalBranch_3 = "SegmentalBranch_3"
  segmentalBranch_4 = "SegmentalBranch_4"
  segmentalBranch_5 = "SegmentalBranch_5"
  segmentalBranch_6 = "SegmentalBranch_6"
  segmentalBranch_7 = "SegmentalBranch_7"
  segmentalBranch_8 = "SegmentalBranch_8"


class InteractionStatus(object):
  STOPPED = "Stopped"
  INSERT_BEFORE = "Insert Before Node"
  INSERT_AFTER = "Insert After Node"
  EDIT = "Edit"
  PLACING = "Placing"


class VesselBranchWizard(object):
  """
  Object responsible for handling interaction with the branch tree and the markup in the 3D and 2D views.
  Triggers slicer move to markup and selects the current parent node when markups are clicked with or without key
  modifiers
  """

  def __init__(self, tree, markupNode, nodePlaceWidget, treeDrawer):
    """
    Parameters
    ----------
    tree: VesselBranchTree
    markupNode: MarkupNode
    nodePlaceWidget: INodePlaceWidget
    treeDrawer: TreeDrawer
    """
    self._tree = tree
    self._node = markupNode
    self._node.SetLocked(True)
    self._setupDefaultBranchNodes()
    self._placeWidget = nodePlaceWidget
    self._currentTreeItem = None
    self._treeDrawer = treeDrawer

    self._tree.connect("itemClicked(QTreeWidgetItem *, int)", self.onItemClicked)
    self._tree.connect("currentItemChanged(QTreeWidgetItem *), QTreeWidgetItem *)",
                       lambda current, previous: self.onItemClicked(current, 0))
    self._tree.keyPressed.connect(self.onKeyPressed)
    self._node.pointAdded.connect(self.onMarkupPointAdded)
    self._node.pointModified.connect(lambda *x: self._treeDrawer.updateTreeLines())
    self._node.pointInteractionEnded.connect(lambda *x: self._treeDrawer.updateTreeLines())
    self._placeWidget.placeModeChanged.connect(self._onNodePlaceModeChanged)

    # Emitted when interaction mode changes
    self._interactionStatus = InteractionStatus.STOPPED
    self.interactionChanged = Signal()

    # Emitted when all nodes have been placed in the wizard
    self._placingFinished = False
    self.placingFinished = Signal()

  def _currentItemPlaceStatus(self):
    """
    :return: Current item place status if it's valid, else PlaceStatus.NONE
    """
    return self._currentTreeItem.status if self._currentTreeItem is not None else PlaceStatus.NONE

  def _onNodePlaceModeChanged(self):
    """
    Disables current wizard placing when markup place widget is disabled from the UI
    """
    if not self._placeWidget.placeModeEnabled:
      self.onStopInteraction()

  def _setupDefaultBranchNodes(self):
    """
    Prepares tree with the different hepatic vessel node names
    """
    self._tree.insertAfterNode(VeinId.portalVein, None)
    self._tree.insertAfterNode(VeinId.rightPortalVein, VeinId.portalVein)
    self._tree.insertAfterNode(VeinId.leftPortalVein, VeinId.portalVein)
    self._tree.insertAfterNode(VeinId.anteriorBranch, VeinId.rightPortalVein)
    self._tree.insertAfterNode(VeinId.posteriorBranch, VeinId.rightPortalVein)
    self._tree.insertAfterNode(VeinId.segmentalBranch_3, VeinId.leftPortalVein)
    self._tree.insertAfterNode(VeinId.segmentalBranch_2, VeinId.leftPortalVein)
    self._tree.insertAfterNode(VeinId.segmentalBranch_4, VeinId.leftPortalVein)
    self._tree.insertAfterNode(VeinId.segmentalBranch_8, VeinId.anteriorBranch)
    self._tree.insertAfterNode(VeinId.segmentalBranch_5, VeinId.anteriorBranch)
    self._tree.insertAfterNode(VeinId.segmentalBranch_7, VeinId.posteriorBranch)
    self._tree.insertAfterNode(VeinId.segmentalBranch_6, VeinId.posteriorBranch)

  def getInteractionStatus(self):
    return self._interactionStatus

  def onInsertBeforeNode(self):
    raise NotImplementedError()

  def onEditNode(self, editEnabled):
    self.onStopInteraction()

    if editEnabled:
      self._node.SetLocked(False)
      self._updateCurrentInteraction(InteractionStatus.EDIT)

  def onStartPlacing(self):
    if self._currentItemPlaceStatus() == PlaceStatus.NOT_PLACED:
      self.onStopInteraction()
      self._currentTreeItem.status = PlaceStatus.PLACING
      self._placeWidget.setPlaceModeEnabled(True)
      self._updateCurrentInteraction(InteractionStatus.PLACING)

  def onStopInteraction(self):
    self._deactivatePreviousItem()
    self._placeWidget.setPlaceModeEnabled(False)
    self._node.SetLocked(True)
    self._updateCurrentInteraction(InteractionStatus.STOPPED)

  def _deactivatePreviousItem(self):
    if self._currentItemPlaceStatus() == PlaceStatus.PLACING:
      self._currentTreeItem.status = PlaceStatus.NOT_PLACED

  def onItemClicked(self, treeItem, column):
    """
    On item clicked, start placing item if necessary.
    Delete item if delete column was selected
    """
    self._deactivatePreviousItem()

    self._currentTreeItem = treeItem
    if column == 1:
      self._onDeleteItem(treeItem)
    elif treeItem.status == PlaceStatus.NOT_PLACED:
      self.onStartPlacing()
    elif self._interactionStatus == InteractionStatus.PLACING and treeItem.status == PlaceStatus.PLACED:
      self.onStopInteraction()

    self._treeDrawer.updateTreeLines()

  def _updateCurrentInteraction(self, interaction):
    if self._interactionStatus != interaction:
      self._interactionStatus = interaction
      self.interactionChanged.emit()

  def onKeyPressed(self, treeItem, key):
    """
    On delete key pressed, delete the current item if any selected
    """
    if key == qt.Qt.Key_Delete:
      self._onDeleteItem(treeItem)

  def _onDeleteItem(self, treeItem):
    """
    Remove the item from the tree and hide the associated markup
    """
    self._tree.removeNode(treeItem.nodeId)
    self.updateNodeVisibility()
    if self._currentTreeItem == treeItem:
      self._currentTreeItem = None
    self._updatePlacingFinished()

  def updateNodeVisibility(self):
    """
    Hides markup nodes which may have been deleted
    """
    for i in range(self._node.GetNumberOfFiducials()):
      self._node.SetNthFiducialVisibility(i, self._tree.isInTree(self._node.GetNthFiducialLabel(i)))

    self._treeDrawer.updateTreeLines()

  def onMarkupPointAdded(self):
    """
    On markup added, modify its status to placed and select the next unplaced node in the tree
    """
    if self._currentTreeItem is not None:
      self._currentTreeItem.status = PlaceStatus.PLACED
      self._node.SetNthFiducialLabel(self._node.GetLastFiducialId(), self._currentTreeItem.nodeId)
      self._currentTreeItem = self._tree.getNextUnplacedItem(self._currentTreeItem.nodeId)
      if self._currentTreeItem is not None:
        self._tree.clickItem(self._currentTreeItem)
      else:
        self._placeWidget.setPlaceModeEnabled(False)

    self._treeDrawer.updateTreeLines()
    self._updatePlacingFinished()

  def setVisibleInScene(self, isVisible):
    self._treeDrawer.setVisible(isVisible)

  def _updatePlacingFinished(self):
    """
    Emit placing finished when placing is done the first time.
    """
    if not self._placingFinished:
      self._placingFinished = self._tree.areAllNodesPlaced()
      if self._placingFinished:
        self.placingFinished.emit()

  def isPlacingFinished(self):
    return self._placingFinished


class PlaceStatus(object):
  NOT_PLACED = 0
  PLACING = 1
  PLACED = 2
  NONE = 3
