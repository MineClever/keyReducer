"""Run with mayapy tests/test_maya_ui.py /absolute/path/to/keyReducer.mll."""
from __future__ import print_function
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'python'))
from tcKeyReducer import tcKeyReducer as ui

# Create QApplication before standalone creates its QCoreApplication.
app = ui.QtWidgets.QApplication.instance() or ui.QtWidgets.QApplication([])
import maya.standalone
maya.standalone.initialize(name='python')
from maya import cmds
cmds.loadPlugin(os.path.abspath(sys.argv.pop(1)), quiet=True)


class KeyReducerUiTests(unittest.TestCase):
    def setUp(self):
        cmds.file(new=True, force=True)
        cmds.undoInfo(state=True)
        self.obj = cmds.createNode('transform', name='reduceMe')
        for frame in range(1, 11):
            cmds.setKeyframe(self.obj, attribute='translateX', time=frame, value=frame)
        cmds.select(self.obj)
        cmds.flushUndo()
        self.controls = ui.KeyReducerControls()

    def tearDown(self):
        self.controls.close()
        self.controls.deleteLater()

    def count(self):
        return cmds.keyframe(self.obj, attribute='translateX', query=True, keyframeCount=True)

    def drag(self, value):
        self.controls._value_slider_pressed()
        self.controls._value_slider.setValue(value)
        self.controls._value_slider_released()

    def test_manual_changes_do_not_execute(self):
        self.assertFalse(self.controls._auto_execute.isChecked())
        self.drag(7000)
        self.controls._value_line_edit.setText('0.3')
        self.controls._value_line_edit_finished()
        self.controls._value_slider.setValue(4000)
        self.assertEqual(self.controls._value_line_edit.text(), '0.4')
        self.assertEqual(self.count(), 10)
        self.assertTrue(cmds.undoInfo(query=True, undoQueueEmpty=True))

    def test_execute_undo_redo(self):
        self.controls._execute_button.click()
        self.assertEqual(self.count(), 2)
        self.controls._undo_button.click()
        self.assertEqual(self.count(), 10)
        cmds.redo()
        self.assertEqual(self.count(), 2)

    def test_auto_drag_is_one_undo(self):
        self.controls._auto_execute.setChecked(True)
        self.assertEqual(self.count(), 10)
        self.drag(6000)
        self.assertEqual(self.count(), 2)
        self.controls._undo_button.click()
        self.assertEqual(self.count(), 10)
        self.assertTrue(cmds.undoInfo(query=True, undoQueueEmpty=True))
        cmds.redo()
        self.assertEqual(self.count(), 2)

    def test_auto_text_executes(self):
        self.controls._auto_execute.setChecked(True)
        self.controls._value_line_edit.setText('0.2')
        self.controls._value_line_edit_finished()
        self.assertEqual(self.count(), 2)
        self.controls._undo_button.click()
        self.assertEqual(self.count(), 10)

    def test_empty_selection(self):
        cmds.select(clear=True)
        cmds.flushUndo()
        self.controls._auto_execute.setChecked(True)
        self.drag(5000)
        self.controls._execute_button.click()
        self.controls._undo_button.click()
        self.assertEqual(self.count(), 10)
        self.assertTrue(cmds.undoInfo(query=True, undoQueueEmpty=True))

    def test_restore_command_preserves_tangents(self):
        cmds.keyTangent(self.obj, attribute='translateX', weightedTangents=True)
        cmds.keyTangent(self.obj, attribute='translateX', inTangentType='fixed', outTangentType='fixed', inAngle=15, outAngle=25)
        before = cmds.keyTangent(self.obj, attribute='translateX', query=True, inAngle=True)
        self.controls._auto_execute.setChecked(True)
        self.drag(6000)
        self.controls._undo_button.click()
        self.assertEqual(self.count(), 10)
        after = cmds.keyTangent(self.obj, attribute='translateX', query=True, inAngle=True)
        for expected, actual in zip(before, after):
            self.assertAlmostEqual(expected, actual, places=5)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(KeyReducerUiTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    maya.standalone.uninitialize()
    sys.exit(0 if result.wasSuccessful() else 1)
