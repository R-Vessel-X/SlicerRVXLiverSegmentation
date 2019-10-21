import logging
import os

import ctk
import qt
import slicer

info = logging.info
warn = logging.warn


def lineSep(isWarning=False):
  log = info if not isWarning else warn
  log('*************************************')


def warnLineSep():
  lineSep(isWarning=True)


def createInputNodeSelector(nodeType, toolTip, callBack=None):
  """Creates node selector with given input node type, tooltip and callback when currentNodeChanged signal is emitted

  Parameters
  ----------
  nodeType: vtkMRML type compatible with qMRMLNodeComboBox
    Node type which will be displayed in the combo box
  toolTip: str
    Input selector hover text
  callBack: (optional) function
    Function called when qMRMLNodeComboBox currentNodeChanged is triggered.
    Function must accept a vtkMRMLNode input parameter

  Returns
  -------
  inputSelector : qMRMLNodeComboBox
    configured input selector
  """
  inputSelector = slicer.qMRMLNodeComboBox()
  inputSelector.nodeTypes = [nodeType]
  inputSelector.selectNodeUponCreation = False
  inputSelector.addEnabled = False
  inputSelector.removeEnabled = False
  inputSelector.noneEnabled = False
  inputSelector.showHidden = False
  inputSelector.showChildNodeTypes = False
  inputSelector.setMRMLScene(slicer.mrmlScene)
  inputSelector.setToolTip(toolTip)
  if callBack is not None:
    inputSelector.connect("currentNodeChanged(vtkMRMLNode*)", callBack)
  return inputSelector


def createSingleMarkupFiducial(toolTip, markupName, markupColor=qt.QColor("red")):
  """Creates node selector for vtkMarkupFiducial type containing only one point.

  Parameters
  ----------
  toolTip: str
    Input selector hover text
  markupName: str
    Default name for the created markups when new markup is selected
  markupColor: (option) QColor
    Default color for the newly created markups (default = red)

  Returns
  -------
  qSlicerSimpleMarkupsWidget
  """
  seedFiducialsNodeSelector = slicer.qSlicerSimpleMarkupsWidget()
  seedFiducialsNodeSelector.objectName = markupName + 'NodeSelector'
  seedFiducialsNodeSelector.toolTip = toolTip
  seedFiducialsNodeSelector.setNodeBaseName(markupName)
  seedFiducialsNodeSelector.tableWidget().hide()
  seedFiducialsNodeSelector.defaultNodeColor = markupColor
  seedFiducialsNodeSelector.markupsSelectorComboBox().noneEnabled = False
  seedFiducialsNodeSelector.markupsPlaceWidget().placeMultipleMarkups = slicer.qSlicerMarkupsPlaceWidget.ForcePlaceSingleMarkup
  seedFiducialsNodeSelector.setMRMLScene(slicer.mrmlScene)
  slicer.app.connect('mrmlSceneChanged(vtkMRMLScene*)', seedFiducialsNodeSelector, 'setMRMLScene(vtkMRMLScene*)')
  return seedFiducialsNodeSelector


def addInCollapsibleLayout(childWidget, parentLayout, collapsibleText, isCollapsed=True):
  """Wraps input childWidget into a collapsible button attached to input parentLayout.
  collapsibleText is writen next to collapsible button. Initial collapsed status is customizable
  (collapsed by default)
  """
  collapsibleButton = ctk.ctkCollapsibleButton()
  collapsibleButton.text = collapsibleText
  collapsibleButton.collapsed = isCollapsed
  parentLayout.addWidget(collapsibleButton)
  collapsibleButtonLayout = qt.QVBoxLayout()
  collapsibleButtonLayout.addWidget(childWidget)
  collapsibleButton.setLayout(collapsibleButtonLayout)


class WidgetUtils(object):
  """
  Helper class to extract widgets linked to an existing widget representation
  """

  @staticmethod
  def getChildrenContainingName(widget, childString):
    return [child for child in widget.children() if childString.lower() in child.name.lower()]

  @staticmethod
  def getChildContainingName(widget, childString):
    children = WidgetUtils.getChildrenContainingName(widget, childString)
    return children[0] if children else None

  @staticmethod
  def hideChildrenContainingName(widget, childString):
    hiddenChildren = WidgetUtils.getChildrenContainingName(widget, childString)
    for child in WidgetUtils.getChildrenContainingName(widget, childString):
      child.visible = False
    return hiddenChildren

  @staticmethod
  def hideChildContainingName(widget, childString):
    hiddenChild = WidgetUtils.getChildContainingName(widget, childString)
    if hiddenChild:
      hiddenChild.visible = False
    return hiddenChild


class Settings(object):
  """
  Helper class to get and set settings in Slicer with RVesselX tag
  """

  @staticmethod
  def _withPrefix(key):
    return "RVesselX/" + key

  @staticmethod
  def value(key, defaultValue=None):
    return slicer.app.settings().value(Settings._withPrefix(key), defaultValue)

  @staticmethod
  def setValue(key, value):
    slicer.app.settings().setValue(Settings._withPrefix(key), value)

  @staticmethod
  def _exportDirectoryKey():
    return "ExportDirectory"

  @staticmethod
  def exportDirectory():
    return Settings.value(Settings._exportDirectoryKey(), "")

  @staticmethod
  def setExportDirectory(value):
    Settings.setValue(Settings._exportDirectoryKey(), value)


class GeometryExporter(object):
  """
  Helper object to export mrml types to given output directory
  """

  def __init__(self, **elementsToExport):
    """
    Class can be instantiated with dictionary of elements to export. Key represents the export name of the element and
    value the slicer MRML Node to export
    :param elementsToExport: keyword args of elements to export
    """
    self._elementsToExport = elementsToExport

  def exportToDirectory(self, selectedDir):
    """
    Export all stored elements to selected directory.
    :param selectedDir: str. Path to export directory
    """
    for elementName, elementNode in self._elementsToExport.items():
      # Select format depending on node type
      formatExtension = self._elementExportExtension(elementNode)

      if formatExtension is not None:
        outputPath = os.path.join(selectedDir, elementName + formatExtension)
        exportSuccessful = slicer.util.saveNode(elementNode, outputPath)
        if not exportSuccessful:
          warn("Failed to export file : %s at location %s" % (elementName, outputPath))

  @staticmethod
  def _elementExportExtension(elementNode):
    """
    Extracts export extension for input node given its class. Volumes will be exported as NIFTI files, Models as VTK
    files. Other nodes are not supported and function will return None.
    :param elementNode: slicer.vtkMRMLNode type
    :return: str or None
    """
    if isinstance(elementNode, slicer.vtkMRMLVolumeNode):  # Export volumes as NIFTI files
      return ".nii"
    elif isinstance(elementNode, slicer.vtkMRMLModelNode):  # Export meshes as vtk types
      return ".vtk"
    else:  # Other types are not supported for export
      return None

  def __setitem__(self, key, value):
    self._elementsToExport[key] = value

  def __getitem__(self, key):
    return self._elementsToExport[key]

  def keys(self):
    return self._elementsToExport.keys()
