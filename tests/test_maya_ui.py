# -*- coding: utf-8 -*-
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
PLUGIN_PATH = os.path.abspath(sys.argv.pop(1))
os.environ['MAYA_PLUG_IN_PATH'] = os.pathsep.join(
    [os.path.dirname(PLUGIN_PATH), os.environ.get('MAYA_PLUG_IN_PATH', '')])
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
            self.assertFalse(window._controls._execute_button.isEnabled())
            self.assertTrue(window._controls._refresh_button.isEnabled())
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
        self.assertFalse(cmds.pluginInfo(PLUGIN_NAME, q=True, loaded=True))
        window = ui.run()
        try:
            self.assertTrue(cmds.pluginInfo(PLUGIN_NAME, q=True, loaded=True))
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

    def test_refresh_keeps_curves_and_finishes_preview_chunk(self):
        window = ui.KeyReducerWidget()
        try:
            controls = window._controls
            controls._refresh_button.click()
            self.assertEqual(self.count(), 10)
            self.assertTrue(cmds.undoInfo(query=True, undoQueueEmpty=True))
            controls._auto_execute.setChecked(True)
            controls._value_slider_pressed()
            self.assertTrue(controls._slider_drag_active)
            self.assertEqual(self.count(), 2)
            controls._refresh_button.click()
            self.assertFalse(controls._slider_drag_active)
            self.assertEqual(self.count(), 2)
            controls._value_slider.setValue(8000)
            self.assertEqual(self.count(), 2)
            controls._undo_button.click()
            self.assertEqual(self.count(), 10)
        finally:
            window.close()
            window.deleteLater()

    def test_refresh_recovers_lost_callback_after_new_scene(self):
        # Standalone does not create UI scriptJobs; proxy just that API while
        # leaving all selection, scene, curve and cache operations in real Maya.
        class CallbackProxy(object):
            def __init__(self):
                self.jobs = {}
                self.next_id = 1

            def __getattr__(self, name):
                return getattr(cmds, name)

            def scriptJob(self, **kwargs):
                if 'exists' in kwargs:
                    return kwargs['exists'] in self.jobs
                if 'kill' in kwargs:
                    del self.jobs[kwargs['kill']]
                    return
                job = self.next_id
                self.next_id += 1
                self.jobs[job] = kwargs['event'][1]
                return job

        original = ui.cmds
        proxy = CallbackProxy()
        ui.cmds = proxy
        window = ui.KeyReducerWidget()
        try:
            window._refresh()
            self.assertEqual(len(proxy.jobs), 1)
            cmds.file(new=True, force=True)
            proxy.jobs.clear()  # Simulate scene change removing the callback.
            window._selection_changed()
            self.assertFalse(window._controls._execute_button.isEnabled())
            self.assertTrue(window._controls._refresh_button.isEnabled())
            window._controls._refresh_button.click()
            self.assertEqual(len(proxy.jobs), 1)
            self.assertFalse(window._controls._execute_button.isEnabled())

            node = cmds.createNode('transform', name='newSceneCurve')
            for frame in range(1, 5):
                cmds.setKeyframe(node, attribute='translateX', time=frame, value=100 + frame)
            cmds.select(node)
            cmds.flushUndo()
            # Simulate another missed callback: Refresh must enable Execute.
            window._controls._refresh_button.click()
            self.assertTrue(window._controls._execute_button.isEnabled())
            self.assertEqual(len(proxy.jobs), 1)
            self.assertTrue(cmds.undoInfo(query=True, undoQueueEmpty=True))
            self.assertEqual(cmds.keyframe(node + '.translateX', query=True, keyframeCount=True), 4)
            cmds.tcKeyReducer(node + '.translateX', value=0.5)
            cmds.tcRestoreKeys()
            self.assertEqual(cmds.keyframe(node + '.translateX', query=True, valueChange=True),
                             [101.0, 102.0, 103.0, 104.0])
            # The replacement callback follows selection changes again.
            cmds.select(clear=True)
            list(proxy.jobs.values())[0]()
            self.assertFalse(window._controls._execute_button.isEnabled())
            self.assertTrue(window._controls._refresh_button.isEnabled())
        finally:
            window.close()
            window.deleteLater()
            ui.cmds = original
        self.assertEqual(proxy.jobs, {})

    def test_plugin_name_loading_and_failure(self):
        class FakeCommands(object):
            def __init__(self):
                self.loaded = False
                self.attempts = []
                self.fail_load = False

            def pluginInfo(self, plugin, **kwargs):
                if not self.loaded:
                    raise RuntimeError('Plugin is not registered')
                return True

            def loadPlugin(self, candidate, **kwargs):
                self.attempts.append(candidate)
                if self.fail_load:
                    raise RuntimeError('test load failure')
                self.loaded = True

        original = ui.cmds
        fake = FakeCommands()
        ui.cmds = fake
        try:
            ui._ensure_plugin_loaded()
            self.assertEqual(fake.attempts, ['keyReducer.mll'])
            fake.attempts = []
            ui._ensure_plugin_loaded()
            self.assertEqual(fake.attempts, [])
            fake.loaded = False
            fake.fail_load = True
            with self.assertRaises(RuntimeError) as raised:
                ui._ensure_plugin_loaded()
            self.assertEqual(raised.exception.args[0], 'test load failure')
        finally:
            ui.cmds = original


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(KeyReducerUiTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    maya.standalone.uninitialize()
    sys.exit(0 if result.wasSuccessful() else 1)
