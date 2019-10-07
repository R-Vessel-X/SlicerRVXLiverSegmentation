import logging

import qt
import slicer


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


class Vessel(object):
  """ Object responsible for holding vessel information and representation in the scene

  Interface for manipulation the vessel through the vessel tree
  """

  _createdCount = 0

  def __init__(self, name=None):
    if name is None:
      name = self.defaultName()

    self.startPoint = None
    self.endPoint = None
    self.vesselnessVolume = None
    self.segmentationSeeds = None
    self.segmentedModel = None
    self.segmentedVolume = None
    self.segmentedCenterline = None
    self.segmentedVoronoiModel = None
    self.name = name
    self.isVisible = True
    Vessel._createdCount += 1

  @staticmethod
  def defaultName():
    return "Vessel_" + str(Vessel._createdCount)

  def toggleVisibility(self):
    self.isVisible = not self.isVisible
    if self._wasSegmented():
      self.segmentedVolume.SetDisplayVisibility(self.isVisible)
      self.segmentedModel.SetDisplayVisibility(self.isVisible)
      self.segmentedCenterline.SetDisplayVisibility(self.isVisible)

  @property
  def name(self):
    return self._name

  @name.setter
  def name(self, name):
    self._name = name
    self._renameSegmentation()

  def _renameSegmentation(self):
    if self._wasSegmented():
      self.segmentedVolume.SetName(self._name)
      self.segmentedModel.SetName(self._name + "_Surface")
      self.segmentedCenterline.SetName(self._name + "_Centerline")

  def _wasSegmented(self):
    return self.segmentedVolume is not None and self.segmentedCenterline is not None

  def setExtremities(self, startPoint, endPoint):
    self.startPoint = startPoint
    self.endPoint = endPoint

    self.startPoint.SetLocked(True)
    self.endPoint.SetLocked(True)

  def setVesselnessVolume(self, vesselnessVolume):
    self.vesselnessVolume = vesselnessVolume
    self._hideFromUser(self.vesselnessVolume)

  def setSegmentation(self, seeds, volume, model):
    self.segmentationSeeds = seeds
    self.segmentedVolume = volume
    self.segmentedModel = model
    self._renameSegmentation()
    self._removeFromScene(self.segmentationSeeds)

  def setCenterline(self, centerline, voronoiModel):
    self.segmentedCenterline = centerline
    self.segmentedVoronoiModel = voronoiModel
    self._renameSegmentation()
    self._removeFromScene(self.segmentedVoronoiModel)

  def _hideFromUser(self, modelsToHide, hideFromEditor=True):
    for model in self._removeNoneList(modelsToHide):
      model.SetDisplayVisibility(False)
      if hideFromEditor:
        model.SetHideFromEditors(True)

  def _removeFromScene(self, nodesToRemove):
    nodesInScene = [node for node in self._removeNoneList(nodesToRemove) if slicer.mrmlScene.IsNodePresent(node)]
    for node in nodesInScene:
      slicer.mrmlScene.RemoveNode(node)

  @staticmethod
  def _removeNoneList(elements):
    if not isinstance(elements, list):
      elements = [elements]
    return [elt for elt in elements if elt is not None]

  def removeFromScene(self):
    """
    removes all the associated models of the vessel from mrml scene except for start and end points
    """
    self._removeFromScene([self.segmentedCenterline, self.segmentedModel, self.segmentedVolume, self.segmentationSeeds,
                           self.segmentedVoronoiModel, self.vesselnessVolume])


class NoEditDelegate(qt.QStyledItemDelegate):
  """
  Helper class to avoid being able to edit columns aside from name in VesselTree
  """

  def __init__(self, parent):
    super(NoEditDelegate, self).__init__(parent)

  def createEditor(self, parent, option, index):
    return None


class VesselTree(object):
  """Class responsible for creating the QTreeWidget in the module. Interacts with Vessel class by forwarding the click
  informations
  """

  class ColumnIndex(object):
    name = 0
    visibility = 1
    editPoint = 2
    editSegmentation = 3
    cut3d = 4
    delete = 5

  def __init__(self):
    c = VesselTree.ColumnIndex()
    self._itemIcons = {c.name: None, c.visibility: Icons.visibleOn, c.editPoint: Icons.editPoint,
                       c.editSegmentation: Icons.editSegmentation, c.cut3d: Icons.cut3d, c.delete: Icons.delete}
    self._headerIcons = dict(self._itemIcons)
    self._headerIcons[c.visibility] = Icons.toggleVisibility

    self._columnCount = max(self._headerIcons.keys()) + 1
    self._itemDict = {}
    self._initTreeWidget()

  def _initTreeWidget(self):
    self._tree = qt.QTreeWidget()
    self._tree.setColumnCount(self._columnCount)

    # Configure tree to have first section stretched and last sections to be at right of the layout
    # other columns will always be at minimum size fitting the icons
    self._tree.header().setSectionResizeMode(0, qt.QHeaderView.Stretch)
    self._tree.header().setStretchLastSection(False)

    for i in range(1, self._columnCount):
      self._tree.header().setSectionResizeMode(i, qt.QHeaderView.ResizeToContents)
      self._tree.setItemDelegateForColumn(i, NoEditDelegate(self._tree))

    # No header text except for first column (vessel name). Other columns have icons instead
    self._tree.setHeaderLabels(["" for _ in range(self._tree.columnCount)])
    self._tree.setHeaderLabel("Vessel Name")

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

  def _renameVessel(self, item, column):
    if column == 0 and item in self._itemDict:
      self._itemDict[item].name = item.text(column)

  def getWidget(self):
    return self._tree

  def _removeItem(self, item, vessel):
    """ Remove item and associated children from tree

    :param item: QTreeWidgetItem to remove from tree
    :param vessel: Vessel associated with QTreeWidgetItem
    """
    # remove vessel from scene
    vessel.removeFromScene()

    # Remove children from vessel
    for child in item.takeChildren():
      self._removeItem(child, self._itemDict[child])

    # Remove from parent
    parentItem = item.parent()
    if parentItem is not None:  # Case is leaf -> remove from parent
      parentItem.removeChild(item)
    else:  # Else remove from tree
      vesselIndex = self._tree.indexFromItem(item).row()
      self._tree.takeTopLevelItem(vesselIndex)

    # remove item from dictionary
    self._itemDict.pop(item)

  def triggerVesselButton(self, item, column):
    vessel = self._itemDict[item]

    if column == VesselTree.ColumnIndex.visibility:
      vessel.toggleVisibility()
      item.setIcon(VesselTree.ColumnIndex.visibility, Icons.visibleOn if vessel.isVisible else Icons.visibleOff)

    if column == VesselTree.ColumnIndex.delete:
      self._removeItem(item, vessel)

  def _setWidgetItemIcon(self, item, iconList):
    for i in range(self._columnCount):
      icon = iconList[i]
      if icon is not None:
        item.setIcon(i, icon)

  def _findParent(self, vessel):
    """ If one parent end point corresponds to vessel start point, returns this item as parent. Else returns None

    :param vessel: Vessel for which we are looking for parent
    :return: QItemWidget or None
    """
    for itemParent, vesselParent in self._itemDict.items():
      if vessel.startPoint == vesselParent.endPoint:
        return itemParent

    return None

  def addVessel(self, vessel):
    """
    Adds vessel in the vessel tree widget and returns created QTreeWidgetItem. This item can be used when adding leafs
    to the item.

    :param vessel: Vessel
    :return: qt.QTreeWidgetItem
    """
    item = qt.QTreeWidgetItem()
    item.setText(0, vessel.name)

    # set item as editable to be able to rename vessel and drop enabled to enable reordering the items in tree
    item.setFlags(item.flags() | qt.Qt.ItemIsEditable | qt.Qt.ItemIsDragEnabled | qt.Qt.ItemIsDropEnabled)
    itemParent = self._findParent(vessel)
    if itemParent is None:
      self._tree.addTopLevelItem(item)
    else:
      itemParent.addChild(item)
      itemParent.setExpanded(True)

    self._setWidgetItemIcon(item, self._itemIcons)
    self._itemDict[item] = vessel

    return item

  def containsItem(self, treeItem):
    """ Returns true if tree contains item, false otherwise
    """
    return treeItem in self._itemDict.keys()
