import qt


class VerticalLayoutWidget(qt.QWidget):
  """Widget with default QVBoxLayout and access to it.
  """

  def __init__(self, widgetName):
    qt.QWidget.__init__(self)
    self._verticalLayout = qt.QVBoxLayout()
    self.setLayout(self._verticalLayout)
    self._name = widgetName

  def insertLayout(self, index, layout):
    self._verticalLayout.insertLayout(index, layout)

  def addLayout(self, layout):
    self._verticalLayout.addLayout(layout)

  def getGeometryExporters(self):
    return [None]

  @property
  def name(self):
    return self._name

  def showEvent(self, event):
    """Overridden for easier use in deriving classes.
    """
    qt.QWidget.showEvent(self, event)

  def hideEvent(self, event):
    """Overridden for easier use in deriving classes.
    """
    qt.QWidget.hideEvent(self, event)

  def clear(self):
    pass
