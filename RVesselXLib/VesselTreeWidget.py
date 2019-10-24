import ctk
import qt

from RVesselXLib import createSingleMarkupFiducial, Vessel, WidgetUtils
from RVesselXLib.RVesselXUtils import raiseValueErrorIfInvalidType


class Icons(object):
  """ Object responsible for the different icons in the module. The module doesn't have any icons internally but pulls
  icons from slicer and the other modules.
  """

  toggleVisibility = qt.QIcon(":/Icons/VisibleOrInvisible.png")
  visibleOn = qt.QIcon(":/Icons/VisibleOn.png")
  visibleOff = qt.QIcon(":/Icons/VisibleOff.png")
  editSegmentation = qt.QIcon(":/Icons/Paint.png")
  editPoint = qt.QIcon(":/Icons/AnnotationEditPoint.png")
  delete = qt.QIcon(":/Icons/SnapshotDelete.png")
  cut3d = qt.QIcon(":/Icons/Medium/SlicerEditCut.png")


class NoEditDelegate(qt.QStyledItemDelegate):
  """Helper class to avoid being able to edit columns aside from name in VesselTree
  """

  def __init__(self, parent):
    super(NoEditDelegate, self).__init__(parent)

  def createEditor(self, parent, option, index):
    return None


class VesselTreeItem(qt.QTreeWidgetItem):
  """TreeItem containing the selected vessel start point, end point and vessel object.
  """

  def __init__(self):
    qt.QTreeWidgetItem.__init__(self)
    self._vessel = None
    self.startPoint = None
    self.endPoint = None
    self._areExtremitiesLocked = False

  @property
  def vessel(self):
    """
    Returns
    -------
    Vessel or None
    """
    return self._vessel

  def lockExtremities(self, isLocked):
    """Lock start and end points markups for scene edition depending on parameters.

    Parameters
    ----------
    isLocked: bool. If True, will lock extremities. Else will unlock them
    """
    self._areExtremitiesLocked = isLocked
    self._updateLock()

  def _updateLock(self):
    """Update lock status for start point, end point and associated vessel.
    """
    if self.startPoint:
      self.startPoint.SetLocked(self._areExtremitiesLocked)
    if self.endPoint:
      self.endPoint.SetLocked(self._areExtremitiesLocked)
    if self.hasVessel():
      self.vessel.lockExtremities(self._areExtremitiesLocked)

  @vessel.setter
  def vessel(self, value):
    """On set, saves vessel start and end points as WidgetItem start and end point. T

    Parameters
    ----------
    value: Vessel or None
    """
    self._vessel = value
    if self._vessel is not None:
      self.startPoint = self._vessel.startPoint
      self.endPoint = self._vessel.endPoint

  def hasVessel(self):
    """
    Returns
    -------
    True if vessel is not None. Contained vessel may be uninitialized
    """
    return self.vessel is not None

  def setStartPoint(self, startPoint):
    """Set start markup as current item start point and lock previous start point regardless of previous status.

    Parameters
    ----------
    startPoint: vtkMRMLMarkupsFiducialNode
    """
    if self.startPoint:
      self.startPoint.SetLocked(True)
    self.startPoint = startPoint
    self._updateLock()

  def setEndPoint(self, endPoint):
    """Set end markup as current item end point and lock previous end point regardless of previous status.

    Parameters
    ----------
    endPoint: vtkMRMLMarkupsFiducialNode
    """
    if self.endPoint:
      self.endPoint.SetLocked(True)
    self.endPoint = endPoint
    self._updateLock()

  def startPointName(self):
    return self._pointName(self.startPoint)

  def endPointName(self):
    return self._pointName(self.endPoint)

  def _pointName(self, point):
    return point.GetName() if point else ""


class VesselTree(object):
  """Class responsible for creating Vessel QTreeWidget in the Vessel tab. Created tree contains all the segmented
  vessels in the UI and allows renaming, editing and ordering the vessels with each other.
  """

  class ColumnIndex(object):
    """Helper class holding the different indices of the vessel tree buttons
    """
    from itertools import count
    _iCol = count(0, 1)

    name = next(_iCol)
    startPoint = next(_iCol)
    endPoint = next(_iCol)
    editPoint = next(_iCol)
    visibility = next(_iCol)
    delete = next(_iCol)
    columnCount = next(_iCol)

  @property
  def _iCol(self):
    return VesselTree.ColumnIndex

  def __init__(self, logic):
    self._itemIcons = {self._iCol.name: None, self._iCol.visibility: Icons.visibleOn,
                       self._iCol.editPoint: Icons.editPoint, self._iCol.delete: Icons.delete,
                       self._iCol.startPoint: None, self._iCol.endPoint: None}
    self._headerIcons = dict(self._itemIcons)
    self._headerIcons[self._iCol.visibility] = Icons.toggleVisibility

    self._itemList = []
    self._itemEditSet = set()
    self._logic = logic
    self._initTreeWidget()
    self._onEditChangedCallback = []
    self._lastEndNode = None

  def addEditChangedCallback(self, callback):
    """Callback will be called when edition has changed. VesselTree is considered as editing when at least one of its
    items is in edit mode.

    Parameters
    ----------
    callback: Callable[[],None]
    """
    self._onEditChangedCallback.append(callback)

  def _triggerEditChanged(self):
    """Calls every callback registered by addEditChangedCallback method
    """
    for callback in self._onEditChangedCallback:
      callback()

  def _initTreeWidget(self):
    """Initializes the QTreeWidget and configures drag and drop behaviour as well as item button connections.
    """
    self._tree = qt.QTreeWidget()
    self._tree.setColumnCount(self._iCol.columnCount)

    # Configure tree to have first section stretched and last sections to be at right of the layout
    # other columns will always be at minimum size fitting the icons
    self._tree.header().setSectionResizeMode(0, qt.QHeaderView.Stretch)
    self._tree.header().setStretchLastSection(False)

    for i in range(1, self._iCol.columnCount):
      self._tree.header().setSectionResizeMode(i, qt.QHeaderView.ResizeToContents)
      self._tree.setItemDelegateForColumn(i, NoEditDelegate(self._tree))

    # No header text except for first column (vessel name). Other columns have icons instead
    headerLabels = {self._iCol.name: "Vessel Name", self._iCol.startPoint: "Start Point",
                    self._iCol.endPoint: "End Point"}
    self._tree.setHeaderLabels(
      [headerLabels[i] if i in headerLabels.keys() else "" for i in range(self._tree.columnCount)])

    # Set header columns icons
    self._setWidgetItemIcon(self._tree.headerItem(), self._headerIcons)

    # Connect click button to handler
    self._tree.connect("itemClicked(QTreeWidgetItem*, int)", self.triggerVesselButton)
    self._tree.connect("itemChanged(QTreeWidgetItem*, int)", self._renameVessel)

    # Enable reordering by drag and drop
    self._tree.setDragEnabled(True)
    self._tree.setDropIndicatorShown(True)
    self._tree.setDragDropMode(qt.QAbstractItemView.InternalMove)
    self._tree.viewport().setAcceptDrops(True)

  def getVesselGeometryExporters(self):
    """
    Returns
    -------
    List[GeometryExporter] list of exporters for vessels stored in vessel Tree
    """
    return [vesselItem.vessel.getGeometryExporter() for vesselItem in self._itemList if vesselItem.hasVessel()]

  def _renameVessel(self, item, column):
    """On tree edition, only allow the name of the vessel to be edited. Text in the button columns is locked to empty.
    """
    if column == 0 and item.hasVessel():
      item.vessel.name = item.text(column)

  def getWidget(self):
    """
    Returns
    -------
    QTreeWidget
    """
    return self._tree

  def _removeItem(self, item):
    """ Remove item and associated children from tree

    Parameters
    ----------
    item: VesselTreeItem
      Item to remove from tree
    """
    # remove vessel from scene
    if item.hasVessel():
      item.vessel.removeFromScene()

    # Remove children from vessel
    for child in item.takeChildren():
      self._removeItem(child)

    # Remove from parent
    parentItem = item.parent()
    if parentItem is not None:  # Case is leaf -> remove from parent
      parentItem.removeChild(item)
    else:  # Else remove from tree
      vesselIndex = self._tree.indexFromItem(item).row()
      self._tree.takeTopLevelItem(vesselIndex)

    # Remove item from list
    self._itemList.remove(item)

    # Make sure status in edit dictionary is set to not editing for removed item
    self._updateItemEditStatus(item, isEditing=False)

  def isEditing(self):
    return len(self._itemEditSet) > 0

  def _updateItemEditStatus(self, item, isEditing):
    oldIsEditing = self.isEditing()
    if isEditing:
      self._itemEditSet.add(item)
    elif item in self._itemEditSet:
      self._itemEditSet.remove(item)

    # Trigger edit change only if edit status changed
    if oldIsEditing != self.isEditing():
      self._triggerEditChanged()

  def triggerVesselButton(self, item, column):
    """Forwards QTreeWidget action to the associated Vessel object.

    Parameters
    ----------
    item: QTreeWidgetItem
      Item whose column was clicked
    column: int
      Index of the clicked column
    """

    vessel = item.vessel
    if column == self._iCol.visibility and item.hasVessel():
      vessel.toggleVisibility()
      item.setIcon(self._iCol.visibility, Icons.visibleOn if vessel.isVisible else Icons.visibleOff)
    elif column == self._iCol.editPoint:
      self._setEditingMode(item)
    elif column == self._iCol.delete:
      self._removeItem(item)

  def _setWidgetItemIcon(self, item, iconList):
    """Sets icon list ot the item. Length of iconList is expected to be greater or equal to the number of columns of
    the item.

    Parameters
    ----------
    item: QTreeWidgetItem
    iconList: List[QIcon]
    """
    for i in range(self._iCol.columnCount):
      icon = iconList[i]
      if icon is not None:
        item.setIcon(i, icon)

  def _findParent(self, vessel):
    """ If one parent end point corresponds to vessel start point, returns this item as parent. Else returns None

    Parameters
    ----------
    vessel: Vessel for which we are looking for parent

    Returns
    -------
    QItemWidget or None
    """
    if vessel is None:
      return None

    for itemParent in self._itemList:
      if itemParent.hasVessel() and vessel.startPoint == itemParent.vessel.endPoint:
        return itemParent

    return None

  def addVessel(self, vessel):
    """
    Adds vessel in the vessel tree widget and returns created QTreeWidgetItem. This item can be used when adding leafs
    to the item.

    Parameters
    ----------
    vessel: Vessel

    Returns
    -------
    qt.QTreeWidgetItem
    """
    raiseValueErrorIfInvalidType(vessel=(vessel, Vessel))

    item = self.addNewVessel()
    self.stopEditMode(item, vessel)
    return item

  def addNewVessel(self):
    item = VesselTreeItem()
    item.setText(VesselTree.ColumnIndex.name, Vessel.defaultName())
    self._setWidgetItemIcon(item, self._itemIcons)
    self._tree.addTopLevelItem(item)
    self._setEditingMode(item)
    self._itemList.append(item)
    return item

  def _createExtremityMarkupSelector(self, toolTip, nodeChangedCallback):
    # Create markup selector and only keep combo box
    extremitySelector = createSingleMarkupFiducial(toolTip=toolTip, markupName="vesselPoint")
    extremitySelector.tableWidget().hide()
    extremitySelector.markupsPlaceWidget().hide()

    # Adjust size of the markup combo box to improve readability of the tree
    markupCombo = WidgetUtils.getFirstChildContainingName(extremitySelector, "ComboBox")
    ctkCombo = WidgetUtils.getFirstChildOfType(markupCombo, ctk.ctkComboBox)
    if ctkCombo:
      ctkCombo.setMinimumContentsLength(20)
      ctkCombo.setSizeAdjustPolicy(qt.QComboBox.AdjustToMinimumContentsLength)

    # Connect node change signal to callback
    extremitySelector.connect("markupsFiducialNodeChanged()", nodeChangedCallback)
    return extremitySelector

  def _setEditingMode(self, item):
    """
    Set editing mode for given item. Adds markup selection combo box to the item as well as a finish edition button.

    Parameters
    ----------
    item: VesselTreeItem
    """
    # Disable editing for item and parents as editing will mess up the widgets added to item
    self._disableEditingForItemAndItsParents(item)

    # Unlock vessel extremities
    item.lockExtremities(False)

    # Create start point markup selector
    startPointSelector = self._createExtremityMarkupSelector(toolTip="Select vessel start position",
                                                             nodeChangedCallback=lambda: item.setStartPoint(
                                                               startPointSelector.currentNode()))
    # Create end point markup selector
    endPointSelector = self._createExtremityMarkupSelector(toolTip="Select vessel end position",
                                                           nodeChangedCallback=lambda: item.setEndPoint(
                                                             endPointSelector.currentNode()))

    self._setCurrentSelectorNode(startPointSelector, endPointSelector, item)

    # Create edit finished button
    editFinishPushButton = qt.QPushButton("OK")
    editFinishPushButton.setMaximumWidth(30)
    editFinishPushButton.connect("clicked(bool)", lambda: self.stopEditMode(item))

    # Add all created widgets to current item columns
    self._tree.setItemWidget(item, self._iCol.startPoint, startPointSelector)
    self._tree.setItemWidget(item, self._iCol.endPoint, endPointSelector)
    self._tree.setItemWidget(item, self._iCol.editPoint, editFinishPushButton)
    item.setIcon(self._iCol.editPoint, qt.QIcon())

    # Update editing status for item
    self._updateItemEditStatus(item, isEditing=True)

  def _setCurrentSelectorNode(self, startPointSelector, endPointSelector, item):
    if item.hasVessel():
      startPointSelector.setCurrentNode(item.vessel.startPoint)
      endPointSelector.setCurrentNode(item.vessel.endPoint)
    else:
      startPointSelector.setCurrentNode(self._lastEndNode)
      endPointSelector.setCurrentNode(None)

    # Make sure point selected are synchronized with item
    startPointSelector.markupsFiducialNodeChanged()
    endPointSelector.markupsFiducialNodeChanged()

  def _disableEditingForItemAndItsParents(self, item):
    if item is not None:
      # Set item as enabled only to avoid any modification to the item before it has finished being edited
      item.setFlags(qt.Qt.ItemIsEnabled)
      self._disableEditingForItemAndItsParents(item.parent())

  def _enableEditingForItemAndItsParents(self, item):
    if item is not None:
      # Enable editing and selection for item. Editing will enable renaming the item
      item.setFlags(
        item.flags() | qt.Qt.ItemIsEditable | qt.Qt.ItemIsDragEnabled | qt.Qt.ItemIsDropEnabled | qt.Qt.ItemIsSelectable)
      self._enableEditingForItemAndItsParents(item.parent())

  def stopEditMode(self, item, vessel=None):
    # Enable editing and drag and drop ofr item and its parents
    self._enableEditingForItemAndItsParents(item)
    isFirstEdit = item.vessel is None

    if not isFirstEdit:
      item.vessel.removeFromScene()

    if vessel is None:
      vessel = self._logic.extractVessel(item.startPoint, item.endPoint)

    # Set vessel
    item.vessel = vessel

    # Lock vessel extremities
    item.lockExtremities(True)

    # Save last used end node
    self._lastEndNode = item.endPoint

    # Remove edit widgets
    self._tree.removeItemWidget(item, self._iCol.startPoint)
    self._tree.removeItemWidget(item, self._iCol.endPoint)
    self._tree.removeItemWidget(item, self._iCol.editPoint)

    # Set vessel start and end points names
    item.setText(self._iCol.startPoint, item.startPointName())
    item.setText(self._iCol.endPoint, item.endPointName())
    item.setIcon(self._iCol.editPoint, self._itemIcons[self._iCol.editPoint])

    # Update the position of the item in the tree if the item is not already set in the tree
    if item.parent() is None and isFirstEdit:
      self._updateVesselHierarchy(item)

    # Update editing status for item
    self._updateItemEditStatus(item, isEditing=False)

  def _updateItemPoint(self, itemUpdateF, markupFiducial):
    node = markupFiducial.currentNode()
    itemUpdateF(node)

  def _updateVesselHierarchy(self, item):
    # reorder vessel in tree
    itemParent = self._findParent(item.vessel)
    if itemParent is not None:
      # remove from tree
      vesselIndex = self._tree.indexFromItem(item).row()

      # Add to parent as child item
      itemParent.addChild(self._tree.takeTopLevelItem(vesselIndex))
      itemParent.setExpanded(True)

  def containsItem(self, treeItem):
    """ Returns true if tree contains item, false otherwise
    """
    return treeItem in self._itemList
