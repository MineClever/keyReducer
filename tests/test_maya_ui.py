# -*- coding: utf-8 -*-
"""Run with mayapy tests/test_maya_ui.py /absolute/path/to/keyReducer.mll."""
from __future__ import print_function
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'python'))
from tcKeyReducer import tcKeyReducer as ui

# Create QApplication before standalone creates its QCoreApplication.
app = ui.QtWidgets.QApplication.instance() or ui.QtWidgets.QApplication([])
import maya.standalone
maya.standalone.initialize(name='python')
from maya import cmds
PLUGIN_PATH = os.path.abspath(sys.argv.pop(1))
PLUGIN_NAME = cmds.loadPlugin(PLUGIN_PATH, quiet=True)[0]


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

    def test_option_tooltips_are_bilingual(self):
        for name in ui.TOOLTIPS:
            if name.startswith('_'):
                tip = getattr(self.controls, name).toolTip()
                self.assertIn('\n', tip)
                self.assertTrue(any(ord(char) > 127 for char in tip), name)
                self.assertTrue(any('a' <= char.lower() <= 'z' for char in tip), name)

    def test_help_opens_without_selection_and_scrolls(self):
        window = ui.KeyReducerWidget()
        try:
            cmds.select(clear=True)
            window._selection_changed()
            self.assertFalse(window._controls.isEnabled())
            self.assertTrue(window._help_action.isEnabled())
            window._help_action.trigger()
            app.processEvents()
            help_panel = window._help_dialog
            self.assertTrue(help_panel.isVisible())
            self.assertTrue(help_panel._browser.isReadOnly())
            self.assertIn(u'工作原理', help_panel._browser.toPlainText())
            self.assertIn('Typical workflow', help_panel._browser.toPlainText())
            scroll = help_panel._browser.verticalScrollBar()
            self.assertGreater(scroll.maximum(), 0)
            scroll.setValue(scroll.maximum())
            self.assertEqual(scroll.value(), scroll.maximum())
            help_panel.close()
            window._help_action.trigger()
            self.assertIs(window._help_dialog, help_panel)
            self.assertTrue(help_panel.isVisible())
        finally:
            window.close()
            window.deleteLater()

    def test_startup_auto_loads_unloaded_plugin_and_reuses_jobs(self):
        cmds.flushUndo()
        cmds.unloadPlugin(PLUGIN_NAME)
        self.assertFalse(ui._provides_commands(PLUGIN_NAME))
        window = ui.run()
        try:
            self.assertTrue(ui._provides_commands(PLUGIN_NAME))
            self.assertTrue(window.isVisible())
            self.assertEqual(os.path.normcase(os.path.normpath(
                cmds.pluginInfo(PLUGIN_NAME, query=True, path=True))),
                os.path.normcase(os.path.normpath(PLUGIN_PATH)))
            first_jobs = list(window._script_jobs)
            self.assertIs(ui.run(), window)
            for job in first_jobs:
                self.assertFalse(cmds.scriptJob(exists=job))
            if not cmds.about(batch=True):
                self.assertEqual(len(window._script_jobs), 1)
            final_jobs = list(window._script_jobs)
        finally:
            window.close()
        for job in final_jobs:
            self.assertFalse(cmds.scriptJob(exists=job))

    def test_deployed_layout_uses_only_current_maya_version(self):
        root = tempfile.mkdtemp(prefix='loader-layout-', dir=os.path.join(ROOT, 'build'))
        version = ui.re.search(r'\d{4}', cmds.about(version=True)).group(0)
        expected = os.path.join(root, 'maya_' + version, 'Plug-ins', 'keyReducer.mll')
        wrong = os.path.join(root, 'maya_2099', 'Plug-ins', 'keyReducer.mll')
        for path in (expected, wrong):
            os.makedirs(os.path.dirname(path))
            with open(path, 'wb'):
                pass
        original = ui.__file__
        ui.__file__ = os.path.join(root, 'scripts', 'tcKeyReducer', 'tcKeyReducer.py')
        try:
            candidates = ui._plugin_candidates()
            self.assertIn(expected, candidates)
            self.assertNotIn(wrong, candidates)
        finally:
            ui.__file__ = original

    def test_plugin_path_fallback_and_load_failure(self):
        class FakeCommands(object):
            def __init__(self):
                self.loaded = False
                self.attempts = []
                self.fail_all = False

            def about(self, **kwargs):
                return '2099'

            def pluginInfo(self, plugin=None, **kwargs):
                if kwargs.get('listPlugins'):
                    return ['tcKeyReducer'] if self.loaded else []
                if kwargs.get('loaded'):
                    return self.loaded
                return list(ui.PLUGIN_COMMANDS)

            def loadPlugin(self, candidate, **kwargs):
                self.attempts.append(candidate)
                if self.fail_all or candidate != 'tcKeyReducer':
                    raise RuntimeError('test load failure')
                self.loaded = True
                return ['tcKeyReducer']

        original = ui.cmds
        fake = FakeCommands()
        ui.cmds = fake
        try:
            self.assertEqual(ui._ensure_plugin_loaded(), 'tcKeyReducer')
            self.assertEqual(fake.attempts, ['keyReducer', 'tcKeyReducer'])
            fake.attempts = []
            ui._ensure_plugin_loaded()
            self.assertEqual(fake.attempts, [])
            fake.loaded = False
            fake.fail_all = True
            with self.assertRaises(RuntimeError) as raised:
                ui._ensure_plugin_loaded()
            self.assertIn('test load failure', raised.exception.args[0])
            self.assertIn('MAYA_PLUG_IN_PATH', raised.exception.args[0])
        finally:
            ui.cmds = original


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(KeyReducerUiTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    maya.standalone.uninitialize()
    sys.exit(0 if result.wasSuccessful() else 1)
