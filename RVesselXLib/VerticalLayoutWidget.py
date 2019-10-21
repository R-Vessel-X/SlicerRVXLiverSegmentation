import qt


class VerticalLayoutWidget(qt.QWidget):
  """
  Widget with default QVBoxLayout and access to it.
  """

  def __init__(self):
    qt.QWidget.__init__(self)
    self._verticalLayout = qt.QVBoxLayout()
    self.setLayout(self._verticalLayout)

  def addLayout(self, layout):
    self._verticalLayout.addLayout(layout)

  def addWidget(self, widget):
    self._verticalLayout.addWidget(widget)

  def exitAction(self):
    pass

  def enterAction(self):
    pass