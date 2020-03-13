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
    self._setupDefaultBranchNodes()
    self._placeWidget = nodePlaceWidget
    self._currentTreeItem = None
    self._treeDrawer = treeDrawer

    self._tree.connect("itemClicked(QTreeWidgetItem *, int)", self.onItemClicked)
    self._tree.connect("currentItemChanged(QTreeWidgetItem *), QTreeWidgetItem *)",
                       lambda current, previous: self.onItemClicked(current, 0))
    self._tree.keyPressed.connect(self.onKeyPressed)
    self._node.pointAdded.connect(self.onMarkupPointAdded)
    self._placeWidget.placeModeChanged.connect(self._onNodePlaceModeChanged)

    # Emitted when interaction mode changes
    self.interactionChanged = Signal()
    self._interactionStatus = InteractionStatus.STOPPED

  def _onNodePlaceModeChanged(self):
    if not self._placeWidget.placeModeEnabled:
      self.onStopInteraction()

  def _setupDefaultBranchNodes(self):
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

  def onInsertAfterNode(self):
    raise NotImplementedError()

  def onEditNode(self):
    raise NotImplementedError()

  def onStopInteraction(self):
    self._deactivatePreviousItem()
    self._placeWidget.setPlaceModeEnabled(False)
    self._updateCurrentInteraction(InteractionStatus.STOPPED)

  def _deactivatePreviousItem(self):
    if self._currentTreeItem is not None and self._currentTreeItem.status == PlaceStatus.PLACING:
      self._currentTreeItem.status = PlaceStatus.NOT_PLACED

  def onItemClicked(self, treeItem, column):
    self._deactivatePreviousItem()

    self._currentTreeItem = treeItem
    if column == 1:
      self._onDeleteItem(treeItem)
    else:
      if treeItem.status == PlaceStatus.NOT_PLACED:
        self._updateCurrentInteraction(InteractionStatus.PLACING)
        treeItem.status = PlaceStatus.PLACING
        self._placeWidget.setPlaceModeEnabled(True)

    self._treeDrawer.updateTreeLines()

  def _updateCurrentInteraction(self, interaction):
    if self._interactionStatus != interaction:
      self._interactionStatus = interaction
      self.interactionChanged.emit()

  def onKeyPressed(self, treeItem, key):
    if key == qt.Qt.Key_Delete:
      self._onDeleteItem(treeItem)

  def _onDeleteItem(self, treeItem):
    self._tree.removeNode(treeItem.nodeId)
    self.updateNodeVisibility()
    if self._currentTreeItem == treeItem:
      self._currentTreeItem = None

  def updateNodeVisibility(self):
    for i in range(self._node.GetNumberOfFiducials()):
      self._node.SetNthFiducialVisibility(i, self._tree.isInTree(self._node.GetNthFiducialLabel(i)))

    self._treeDrawer.updateTreeLines()

  def onMarkupPointAdded(self):
    if self._currentTreeItem is not None:
      self._currentTreeItem.status = PlaceStatus.PLACED
      self._node.SetNthFiducialLabel(self._node.GetLastFiducialId(), self._currentTreeItem.nodeId)
      self._currentTreeItem = self._tree.getNextUnplacedItem(self._currentTreeItem.nodeId)
      if self._currentTreeItem is not None:
        self._tree.clickItem(self._currentTreeItem)
      else:
        self._placeWidget.setPlaceModeEnabled(False)

    self._treeDrawer.updateTreeLines()

  def setVisibleInScene(self, isVisible):
    self._treeDrawer.setVisible(isVisible)


class PlaceStatus(object):
  NOT_PLACED = 0
  PLACING = 1
  PLACED = 2
