import qt
import logging


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
  """

  _createdCount = 0

  def __init__(self):
    self._startPoint = None
    self._endPoint = None
    self._vesselnessVolume = None
    self._segmentationSeeds = None
    self._segmentedModel = None
    self._segmentedVolume = None
    self._centerline = None
    self._name = self.defaultName()
    Vessel._createdCount += 1

  @staticmethod
  def defaultName():
    return "Vessel_" + str(Vessel._createdCount)

  @property
  def name(self):
    return self._name

  @name.setter
  def name(self, name):
    self._name = name
    if self._wasSegmented:
      # TODO Rename all volumes and models associated with segmentation
      pass

  def _wasSegmented(self):
    return self._segmentedVolume is not None

  def centerline(self):
    return self._centerline

  def segmentedModel(self):
    return self._segmentedModel

  def segmentedVolume(self):
    return self._segmentedVolume

  def setExtremities(self, startPoint, endPoint):
    self._startPoint = startPoint
    self._endPoint = endPoint

  def setVesselnessVolume(self, vesselnessVolume):
    self._vesselnessVolume = vesselnessVolume

  def setSegmentation(self, seeds, volume, model):
    self._segmentationSeeds = seeds
    self._segmentedVolume = volume
    self._segmentedModel = model

  def setCenterline(self, centerline, voronoiModel):
    self._centerline = centerline
    self._centerlineVoronoi = voronoiModel


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
    self._tree.connect("itemClicked(QTreeWidgetItem*, int)", self._triggerVesselButton)
    self._tree.connect("itemChanged(QTreeWidgetItem*, int)", self._renameVessel)

  def _renameVessel(self, item, column):
    if column == 0 and item in self._itemDict:
      self._itemDict[item].name = item.text(column)

  def getWidget(self):
    return self._tree

  def _triggerVesselButton(self, item, column):
    # TODO Call vessel buttons
    logging.info("Clicked item %s on column %s" % (self._itemDict[item].name, column))
    if column == 0:
      self._tree.editItem(item, 0)

  def _setWidgetItemIcon(self, item, iconList):
    for i in range(self._columnCount):
      icon = iconList[i]
      if icon is not None:
        item.setIcon(i, icon)

  def addVessel(self, vessel):
    item = qt.QTreeWidgetItem(self._tree)
    item.setText(0, vessel.name)
    item.setFlags(item.flags() | qt.Qt.ItemIsEditable)  # set item as editable to be able to rename vessel

    self._setWidgetItemIcon(item, self._itemIcons)
    self._itemDict[item] = vessel
