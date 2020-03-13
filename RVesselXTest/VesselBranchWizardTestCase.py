import qt
import slicer
import unittest

from RVesselXLib import VesselBranchTree, VesselBranchWizard, VeinId
from RVesselXLib.VesselBranchTree import MarkupNode, TreeDrawer, INodePlaceWidget
from RVesselXLib.VesselBranchWizard import InteractionStatus


class FakeNodePlaceWidget(INodePlaceWidget):
  def __init__(self, markupNode):
    INodePlaceWidget.__init__(self)
    self._isEnabled = False
    self._node = markupNode

  def setPlaceModeEnabled(self, isEnabled):
    if self._isEnabled != isEnabled:
      self._isEnabled = isEnabled
      self.placeModeChanged.emit()

  @property
  def placeModeEnabled(self):
    return self._isEnabled

  def placeNode(self):
    self._node.AddFiducial(0, 0, 0)


class Mock(object):
  def __init__(self):
    self.args = None
    self.kwargs = None
    self.call_count = 0

  def __call__(self, *args, **kwargs):
    self.call_count += 1
    self.args = args
    self.kwargs = kwargs


class VesselBranchWizardTestCase(unittest.TestCase):
  def setUp(self):
    """ Clear scene before each tests
    """
    slicer.mrmlScene.Clear(0)

    # Create tree widget
    self.tree = VesselBranchTree()

    # Create markup
    self.markupNode = MarkupNode(slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode'))
    self.nodePlace = FakeNodePlaceWidget(self.markupNode)
    self.treeDrawer = TreeDrawer(self.tree, self.markupNode)
    self.treeDrawer.updateTreeLines = Mock()

    # Create interactor with dependencies
    self.wizard = VesselBranchWizard(self.tree, self.markupNode, self.nodePlace, self.treeDrawer)

    self.status_update_listener = Mock()
    self.wizard.interactionChanged.connect(self.status_update_listener)

    self.placing_text = "*placing*"

  def click_first_element(self):
    self.tree.itemClicked.emit(self.tree.getTreeWidgetItem(VeinId.portalVein), 0)

  def get_first_element_text(self):
    return self.tree.getText(VeinId.portalVein)

  def test_given_construction_populates_tree_with_predefined_node_names(self):
    # Expect tree widget to be constructed with proper names
    expTree = [  #
      [None, VeinId.portalVein],  #
      [VeinId.portalVein, VeinId.rightPortalVein],  #
      [VeinId.portalVein, VeinId.leftPortalVein],  #
      [VeinId.rightPortalVein, VeinId.anteriorBranch],  #
      [VeinId.rightPortalVein, "PosteriorBranch"],  #
      [VeinId.leftPortalVein, "SegmentalBranch_3"],  #
      [VeinId.leftPortalVein, "SegmentalBranch_2"],  #
      [VeinId.leftPortalVein, "SegmentalBranch_4"],  #
      ["AnteriorBranch", "SegmentalBranch_8"],  #
      ["AnteriorBranch", "SegmentalBranch_5"],  #
      ["PosteriorBranch", "SegmentalBranch_7"],  #
      ["PosteriorBranch", VeinId.segmentalBranch_6],  #
    ]
    self.assertEqual(sorted(expTree), sorted(self.tree.getTreeParentList()))
    self.assertEqual(0, self.markupNode.GetNumberOfFiducials())
    self.assertIn('click to start placing', self.get_first_element_text())

  def test_given_not_placed_element_clicked_triggers_markup_place_mode_and_tree_name_as_placing(self):
    # Press on portal vein
    self.assertFalse(self.nodePlace.placeModeEnabled)
    self.click_first_element()

    # Verify markups is in placing mode
    self.assertTrue(self.nodePlace.placeModeEnabled)

    # expect name to contain placing information
    self.assertIn(self.placing_text, self.get_first_element_text())

  def test_given_not_placed_element_placed_creates_fiducial_and_sets_its_name_to_node_name(self):
    self.click_first_element()
    self.nodePlace.placeNode()
    self.assertEqual(1, self.markupNode.GetNumberOfFiducials())
    self.assertEqual(VeinId.portalVein, self.markupNode.GetNthFiducialLabel(0))

  def test_given_first_placed_element_second_element_is_selected_to_be_placed_in_tree(self):
    self.click_first_element()
    self.nodePlace.placeNode()

    self.assertIn(self.placing_text, self.tree.getText(VeinId.rightPortalVein))
    self.nodePlace.placeNode()

    self.assertIn(self.placing_text, self.tree.getText(VeinId.anteriorBranch))

  def test_given_next_element_already_placed_next_selects_one_after(self):
    self.tree.itemClicked.emit(self.tree.getTreeWidgetItem(VeinId.rightPortalVein), 0)
    self.nodePlace.placeNode()

    self.click_first_element()
    self.assertNotIn(self.placing_text, self.tree.getText(VeinId.anteriorBranch))
    self.nodePlace.placeNode()
    self.assertIn(self.placing_text, self.tree.getText(VeinId.anteriorBranch))

  def test_given_every_point_in_the_tree_has_been_placed_markup_placement_stops(self):
    self.click_first_element()
    for _ in range(100):
      self.nodePlace.placeNode()

    self.assertIsNone(self.tree.getNextUnplacedItem(VeinId.portalVein))
    self.assertFalse(self.nodePlace.placeModeEnabled)

  def test_given_deleted_node_the_associated_node_is_hidden_in_the_markup(self):
    self.click_first_element()
    self.nodePlace.placeNode()
    self.nodePlace.placeNode()
    self.tree.itemClicked.emit(self.tree.getTreeWidgetItem(VeinId.rightPortalVein), 1)
    self.assertFalse(self.tree.isInTree(VeinId.rightPortalVein))
    self.assertFalse(self.markupNode.GetNthFiducialVisibility(1))

  def test_elements_can_be_deleted_using_key_events(self):
    self.click_first_element()
    self.nodePlace.placeNode()
    self.nodePlace.placeNode()
    self.tree.setCurrentItem(self.tree.getTreeWidgetItem(VeinId.rightPortalVein))
    self.tree.keyPressEvent(qt.QKeyEvent(qt.QEvent.KeyPress, qt.Qt.Key_Delete, qt.Qt.KeyboardModifier()))

    self.assertFalse(self.tree.isInTree(VeinId.rightPortalVein))
    self.assertFalse(self.markupNode.GetNthFiducialVisibility(1))

  def test_given_segmental_branch_6_placed_placing_switch_to_left_portal_vein(self):
    self.tree.itemClicked.emit(self.tree.getTreeWidgetItem(VeinId.segmentalBranch_6), 0)
    self.nodePlace.placeNode()
    self.assertIn(self.placing_text, self.tree.getText(VeinId.leftPortalVein))

  def test_on_key_pressed_or_node_added_tree_is_updated(self):
    self.click_first_element()
    self.nodePlace.placeNode()

    self.tree.keyPressEvent(qt.QKeyEvent(qt.QEvent.KeyPress, qt.Qt.Key_Delete, qt.Qt.KeyboardModifier()))
    self.assertGreaterEqual(self.treeDrawer.updateTreeLines.call_count, 2)

  def test_on_interaction_stop_when_placing_to_not_placed(self):
    self.click_first_element()
    self.wizard.onStopInteraction()
    self.assertNotIn(self.placing_text, self.get_first_element_text())
    self.assertEqual(InteractionStatus.STOPPED, self.wizard.getInteractionStatus())

  def test_when_starting_node_placement_status_is_updated_to_placing(self):
    self.click_first_element()
    self.assertEqual(1, self.status_update_listener.call_count)
    self.assertEqual(InteractionStatus.PLACING, self.wizard.getInteractionStatus())

  def test_when_stopping_interaction_from_place_widget_status_switches_to_not_placed(self):
    self.click_first_element()
    self.nodePlace.setPlaceModeEnabled(False)
    self.assertNotIn(self.placing_text, self.get_first_element_text())
    self.assertEqual(InteractionStatus.STOPPED, self.wizard.getInteractionStatus())

  def test_editing_not_not_placed_yet_does_nothing(self):
    self.click_first_element()
    self.wizard.onEditNode()
    self.assertEqual(0, self.status_update_listener.call_count)
    self.assertEqual(InteractionStatus.PLACING, self.wizard.getInteractionStatus())

  def test_clicking_on_node_which_is_already_placed_and_without_any_other_action_sets_status_to_stopped(self):
    self.click_first_element()
    self.nodePlace.placeNode()
    self.click_first_element()
    self.assertEqual(1, self.status_update_listener.call_count)
    self.assertEqual(InteractionStatus.STOPPED, self.wizard.getInteractionStatus())

  def test_editing_when_node_is_placed_enables_changing_its_position_by_clicking(self):
    self.click_first_element()
    self.nodePlace.placeNode()
    self.click_first_element()

    self.wizard.onEditNode()
    self.assertEqual(InteractionStatus.EDIT, self.wizard.getInteractionStatus())
    self.assertFalse(self.markupNode.GetLocked())

  def test_stopping_interaction_after_edit_locks_markup(self):
    self.click_first_element()
    self.nodePlace.placeNode()
    self.click_first_element()
    self.wizard.onEditNode()
    self.wizard.onStopInteraction()
    self.assertTrue(self.markupNode.GetLocked())
    self.assertEqual(InteractionStatus.STOPPED, self.wizard.getInteractionStatus())

  def test_clicking_on_not_placed_markup_stops_edit_mode(self):
    self.click_first_element()
    self.nodePlace.placeNode()
    self.click_first_element()
    self.wizard.onEditNode()
    self.tree.itemClicked.emit(self.tree.getTreeWidgetItem(VeinId.segmentalBranch_6), 0)

    self.assertTrue(self.markupNode.GetLocked())
    self.assertEqual(InteractionStatus.PLACING, self.wizard.getInteractionStatus())

  def test_placing_node_before_does_nothing_if_current_nodes_are_not_placed(self):
    raise NotImplementedError()

  def test_placing_node_after_does_nothing_if_current_nodes_are_not_placed(self):
    raise NotImplementedError()

  def test_when_placing_node_inserts_node_name_of_next_node_when_placed(self):
    raise NotImplementedError()

  def test_when_placing_node_before_renames_nodes(self):
    raise NotImplementedError()
