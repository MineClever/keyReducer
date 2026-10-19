# -*- coding: utf-8 -*-
"""Run with mayapy tests/test_maya_ui.py /absolute/path/to/keyReducer.mll."""
from __future__ import print_function
import os
import sys
import math
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
        cmds.keyTangent(self.obj + '.translateX', inTangentType='linear', outTangentType='linear')
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
        self.assertFalse(self.controls._align_keys.isChecked())
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

    def test_alignment_checkbox_execute_preview_and_undo(self):
        for frame in range(1, 11):
            cmds.setKeyframe(self.obj, attribute='translateY', time=frame,
                             value=5 if frame == 7 else 0)
        cmds.flushUndo()
        self.controls._align_keys.setChecked(True)
        self.assertEqual(self.count(), 10)
        self.controls._execute_button.click()
        times = lambda attr: cmds.keyframe(self.obj, attribute=attr, query=True, timeChange=True)
        self.assertEqual(times('translateX'), times('translateY'))
        self.controls._undo_button.click()
        self.assertEqual(len(times('translateX')), 10)
        self.assertEqual(len(times('translateY')), 10)
        self.controls._auto_execute.setChecked(True)
        self.drag(6000)
        self.assertEqual(times('translateX'), times('translateY'))
        self.controls._undo_button.click()
        self.assertEqual(len(times('translateX')), 10)
        self.assertEqual(len(times('translateY')), 10)

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

    def test_dialog_is_parented_to_maya_main_window(self):
        main_window = ui.QtWidgets.QMainWindow()
        pointer = ui.shiboken.getCppPointer(main_window)[0]
        class QtUtil(object):
            @staticmethod
            def mainWindow():
                return pointer
        class FakeMayaUI(object):
            MQtUtil = QtUtil
        original = ui.omui
        ui.omui = FakeMayaUI()
        window = None
        try:
            window = ui.KeyReducerWidget()
            self.assertIs(window.parentWidget(), main_window)
            self.assertFalse(window.windowFlags() & ui.QtCore.Qt.WindowStaysOnTopHint)
            window._show_help()
            self.assertIs(window._help_dialog.parentWidget(), window)
        finally:
            if window is not None:
                window.close()
            ui.omui = original
            main_window.close()
            main_window.deleteLater()

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


class CurveTestCase(unittest.TestCase):
    def setUp(self):
        self.original_unit = cmds.currentUnit(query=True, time=True)
        cmds.file(new=True, force=True)
        cmds.currentUnit(time='film', updateAnimation=False)
        cmds.undoInfo(state=True)
        self.node = cmds.createNode('transform', name='alignmentTest')

    def tearDown(self):
        cmds.currentUnit(time=self.original_unit, updateAnimation=False)

    def curve(self, attr, times, values):
        for time, value in zip(times, values):
            cmds.setKeyframe(self.node, attribute=attr, time=time, value=value)
        cmds.keyTangent(self.node, attribute=attr, inTangentType='linear', outTangentType='linear')
        return self.node + '.' + attr

    def times(self, attr):
        return cmds.keyframe(attr, query=True, timeChange=True) or []

    def values(self, attr, samples):
        return [cmds.getAttr(attr, time=time) for time in samples]


class KeyAlignmentTests(CurveTestCase):
    def check_union_and_shape(self, weighted):
        times = list(range(1, 10))
        y_times = [time + 0.125 if weighted and 1 < time < 9 else time for time in times]
        x = self.curve('translateX', times, [5 if time == 3 else 0 for time in times])
        y = self.curve('translateY', y_times, [5 if time == 7 else 0 for time in times])
        for attr in (x, y):
            cmds.keyTangent(attr, weightedTangents=weighted)
            if weighted:
                cmds.keyTangent(attr, inTangentType='fixed', outTangentType='fixed',
                                inAngle=15, outAngle=-20, inWeight=0.5, outWeight=0.7)
        cmds.flushUndo()
        cmds.tcKeyReducer(x, y, value=0.1)
        self.assertNotEqual(self.times(x), self.times(y))
        union = sorted(set(self.times(x) + self.times(y)))
        samples = [1 + index / 16.0 for index in range(129)]
        before_x = self.values(x, samples)
        before_y = self.values(y, samples)
        cmds.undo()
        cmds.tcKeyReducer(x, y, value=0.1, alignKeys=True)
        self.assertEqual(self.times(x), union)
        self.assertEqual(self.times(y), union)
        for attr, expected in ((x, before_x), (y, before_y)):
            for actual, value in zip(self.values(attr, samples), expected):
                self.assertAlmostEqual(actual, value, places=5)
        self.assertFalse(cmds.listConnections(self.node + '.translateZ', source=True, type='animCurve'))
        cmds.undo()
        self.assertEqual(self.times(x), times)
        self.assertEqual(self.times(y), y_times)
        cmds.redo()
        self.assertEqual(self.times(x), union)
        self.assertEqual(self.times(y), union)

    def test_union_shape_and_undo(self):
        self.check_union_and_shape(False)

    def test_weighted_union_shape_and_undo(self):
        self.check_union_and_shape(True)

    def test_negative_subframes_and_different_extents(self):
        x = self.curve('translateX', [-2.25, 0.75], [-2, 2])
        y = self.curve('translateY', [-1.5, 2.5], [0, 3])
        cmds.flushUndo()
        cmds.tcKeyReducer(x, y, alignKeys=True)
        union = [-2.25, -1.5, 0.75, 2.5]
        self.assertEqual(self.times(x), union)
        self.assertEqual(self.times(y), union)
        cmds.undo()
        self.assertEqual(self.times(x), [-2.25, 0.75])
        self.assertEqual(self.times(y), [-1.5, 2.5])

    def test_single_key_and_duplicate_channel(self):
        x = self.curve('translateX', [2], [3])
        y = self.curve('translateY', [1, 3], [5, 6])
        cmds.tcKeyReducer(x, x, y, alignKeys=True)
        self.assertEqual(self.times(x), [1, 2, 3])
        self.assertEqual(self.times(y), [1, 2, 3])

    def test_alignment_respects_range(self):
        x = self.curve('translateX', [-2, 0, 2, 4, 8], [-2, 0, 2, 4, 8])
        y = self.curve('translateY', [-1, 1, 3, 5, 9], [-1, 1, 3, 5, 9])
        cmds.flushUndo()
        cmds.tcKeyReducer(x, y, startTime=0, endTime=5, alignKeys=True)
        inside = lambda attr: [time for time in self.times(attr) if 0 <= time <= 5]
        self.assertEqual(inside(x), [0, 1, 4, 5])
        self.assertEqual(inside(y), [0, 1, 4, 5])
        self.assertEqual([time for time in self.times(x) if time < 0 or time > 5], [-2, 8])
        self.assertEqual([time for time in self.times(y) if time < 0 or time > 5], [-1, 9])

    def test_pre_bake_uses_scene_frame_rate(self):
        for unit in ('pal', 'ntsc', 'ntscf'):
            cmds.file(new=True, force=True)
            cmds.currentUnit(time=unit, updateAnimation=False)
            self.node = cmds.createNode('transform', name='alignmentTest')
            x = self.curve('translateX', [1, 4, 10], [0, 8, -1])
            y = self.curve('translateY', [1, 6, 10], [2, -4, 7])
            cmds.tcKeyReducer(x, y, value=0, preBake=True, alignKeys=True)
            self.assertEqual(self.times(x), self.times(y))
            self.assertEqual(self.times(x)[0], 1)
            self.assertEqual(self.times(x)[-1], 10)
            for attr in (x, y):
                for time in self.times(attr):
                    self.assertAlmostEqual(time, round(time), places=6)
            # Retained input knots must be sampled in the actual scene unit.
            # Intermediate curve interpolation is allowed to change in reduction.
            for attr, knots in ((x, [(1, 0), (4, 8), (10, -1)]),
                                (y, [(1, 2), (6, -4), (10, 7)])):
                for time, value in knots:
                    self.assertAlmostEqual(cmds.getAttr(attr, time=time), value, places=5)


class TangentReductionTests(CurveTestCase):
    def check_fit(self, tangent, weighted=False, rotation=False, preview=False):
        attr = self.curve('rotateX' if rotation else 'translateX', list(range(41)),
                          [10 * math.sin(time * 0.23) + 2 * math.cos(time * 0.57)
                           for time in range(41)])
        cmds.keyTangent(attr, weightedTangents=weighted)
        cmds.keyTangent(attr, inTangentType=tangent, outTangentType=tangent)
        samples = [index / 64.0 for index in range(40 * 64 + 1)]
        reference = self.values(attr, samples)
        original_types = cmds.keyTangent(attr, query=True, outTangentType=True)
        original_times = self.times(attr)
        original_angles = cmds.keyTangent(attr, query=True, outAngle=True)
        original_weights = cmds.keyTangent(attr, query=True, outWeight=True)
        original_locks = cmds.keyTangent(attr, query=True, lock=True)
        original_weight_locks = cmds.keyTangent(attr, query=True, weightLock=True)
        tolerance = 0.05
        cmds.flushUndo()
        if preview:
            cmds.tcStoreKeys(attr)
            cmds.tcKeyReducer(attr, value=1.0)
            cmds.tcRestoreKeys()
            self.assertEqual(cmds.keyTangent(attr, query=True, outTangentType=True), original_types)
            for actual, expected in zip(self.values(attr, samples), reference):
                self.assertAlmostEqual(actual, expected, places=7)
        cmds.tcKeyReducer(attr, value=tolerance)
        self.assertLess(len(self.times(attr)), len(original_times))
        reduced_values = self.values(attr, samples)
        reduced_locks = cmds.keyTangent(attr, query=True, lock=True)
        reduced_weight_locks = cmds.keyTangent(attr, query=True, weightLock=True)
        error = max(abs(actual - expected)
                    for actual, expected in zip(reduced_values, reference))
        self.assertLessEqual(error, tolerance + 1.0e-6, 'dense curve error: {0}'.format(error))
        reduced_times = self.times(attr)
        cmds.undo()
        self.assertEqual(self.times(attr), original_times)
        self.assertEqual(cmds.keyTangent(attr, query=True, outTangentType=True), original_types)
        for actual, expected in zip(cmds.keyTangent(attr, query=True, outAngle=True), original_angles):
            self.assertAlmostEqual(actual, expected, places=6)
        for actual, expected in zip(cmds.keyTangent(attr, query=True, outWeight=True), original_weights):
            self.assertAlmostEqual(actual, expected, places=6)
        self.assertEqual(cmds.keyTangent(attr, query=True, lock=True), original_locks)
        self.assertEqual(cmds.keyTangent(attr, query=True, weightLock=True), original_weight_locks)
        for actual, expected in zip(self.values(attr, samples), reference):
            self.assertAlmostEqual(actual, expected, places=7)
        cmds.redo()
        self.assertEqual(self.times(attr), reduced_times)
        self.assertEqual(cmds.keyTangent(attr, query=True, lock=True), reduced_locks)
        self.assertEqual(cmds.keyTangent(attr, query=True, weightLock=True), reduced_weight_locks)
        self.assertLess(max(abs(a - b) for a, b in zip(self.values(attr, samples), reduced_values)), 1.0e-6)

    def test_auto_fit_and_undo_restores_types(self):
        self.check_fit('auto')

    def test_weighted_auto_fit(self):
        self.check_fit('auto', weighted=True)

    def test_weighted_handle_lengths_and_directions_are_fitted(self):
        attr = self.curve('translateX', list(range(41)),
                          [10 * math.sin(time * 0.23) + 2 * math.cos(time * 0.57)
                           for time in range(41)])
        cmds.keyTangent(attr, weightedTangents=True)
        cmds.keyTangent(attr, inTangentType='auto', outTangentType='auto')
        weights = dict(zip(self.times(attr), cmds.keyTangent(attr, query=True, outWeight=True)))
        samples = [index / 64.0 for index in range(40 * 64 + 1)]
        values = self.values(attr, samples)
        cmds.tcKeyReducer(attr, value=0.05)
        # Frozen original weighted handles needed 33 keys and type-preserving
        # removal needed 32. Refitting must improve on both without excess error.
        self.assertLess(len(self.times(attr)), 32)
        self.assertIn('fixed', cmds.keyTangent(attr, query=True, outTangentType=True))
        fitted = zip(self.times(attr), cmds.keyTangent(attr, query=True, outWeight=True))
        self.assertTrue(any(abs(weight - weights[time]) > 1.0e-4 for time, weight in fitted))
        self.assertLessEqual(max(abs(a - b) for a, b in zip(self.values(attr, samples), values)), 0.05)

    def test_frozen_candidate_reduces_more_than_type_preservation(self):
        attr = self.curve('translateX', list(range(201)),
                          [10 * math.sin(time * 0.04) + 2 * math.cos(time * 0.11)
                           for time in range(201)])
        cmds.keyTangent(attr, inTangentType='auto', outTangentType='auto')
        samples = [index / 16.0 for index in range(200 * 16 + 1)]
        values = self.values(attr, samples)
        cmds.flushUndo()
        cmds.tcKeyReducer(attr, value=0.05)
        # The evaluated frozen-handle baseline needs 14 keys; the old
        # type-preserving strategy needed 35 for this same reference.
        self.assertLessEqual(len(self.times(attr)), 14)
        self.assertIn('fixed', cmds.keyTangent(attr, query=True, outTangentType=True))
        self.assertLessEqual(max(abs(a - b) for a, b in zip(self.values(attr, samples), values)), 0.05)
        cmds.undo()
        self.assertEqual(len(self.times(attr)), 201)
        self.assertEqual(set(cmds.keyTangent(attr, query=True, outTangentType=True)), set(['auto']))

    def test_weighted_fixed_cache_restores_handles(self):
        attr = self.curve('translateX', list(range(9)),
                          [0, 0, 5, 0, -1, 0, 3, 0, 0])
        cmds.keyTangent(attr, weightedTangents=True)
        cmds.keyTangent(attr, inTangentType='fixed', outTangentType='fixed',
                        inAngle=15, outAngle=-20, inWeight=0.5, outWeight=0.7)
        samples = [index / 64.0 for index in range(8 * 64 + 1)]
        values = self.values(attr, samples)
        cmds.tcStoreKeys(attr)
        cmds.tcKeyReducer(attr, value=100)
        cmds.tcRestoreKeys()
        self.assertEqual(set(cmds.keyTangent(attr, query=True, outTangentType=True)), set(['fixed']))
        # Weighted Bezier root solving can differ at the last decimal places
        # after a vector round-trip even when the same handles are restored.
        self.assertLess(max(abs(a - b) for a, b in zip(self.values(attr, samples), values)), 1.0e-6)

    def test_spline_fit(self):
        self.check_fit('spline')

    def test_clamped_fit(self):
        self.check_fit('clamped')

    def test_plateau_fit(self):
        self.check_fit('plateau')

    def test_rotation_tolerance_is_in_degrees(self):
        self.check_fit('auto', rotation=True)

    def test_auto_preview_restore(self):
        self.check_fit('auto', preview=True)

    def test_step_and_stepnext_transitions(self):
        for tangent in ('step', 'stepnext'):
            attr = self.curve('translateX', [0, 1, 3, 4, 8], [0, 3, -2, 5, 1])
            cmds.keyTangent(attr, outTangentType=tangent)
            samples = [index / 64.0 for index in range(8 * 64 + 1)]
            values = self.values(attr, samples)
            cmds.tcKeyReducer(attr, value=100)
            self.assertEqual(self.times(attr), [0, 1, 3, 4, 8])
            self.assertEqual(self.values(attr, samples), values)
            cmds.cutKey(attr, clear=True)

    def test_range_keeps_outside_keys_and_checks_neighboring_spans(self):
        attr = self.curve('translateX', list(range(21)),
                          [math.sin(time * 0.4) for time in range(21)])
        cmds.keyTangent(attr, inTangentType='auto', outTangentType='auto')
        samples = [index / 64.0 for index in range(20 * 64 + 1)]
        values = self.values(attr, samples)
        cmds.tcKeyReducer(attr, value=0.05, startTime=4, endTime=15)
        self.assertEqual([time for time in self.times(attr) if time <= 4 or time >= 15],
                         list(range(5)) + list(range(15, 21)))
        self.assertLessEqual(max(abs(a - b) for a, b in zip(self.values(attr, samples), values)), 0.05)
        outside = [index for index, time in enumerate(samples) if time < 4 or time > 15]
        actual = self.values(attr, samples)
        self.assertLessEqual(max(abs(actual[index] - values[index]) for index in outside), 1.0e-6)


if __name__ == '__main__':
    suite = unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(KeyReducerUiTests),
        unittest.defaultTestLoader.loadTestsFromTestCase(KeyAlignmentTests),
        unittest.defaultTestLoader.loadTestsFromTestCase(TangentReductionTests),
    ])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    maya.standalone.uninitialize()
    sys.exit(0 if result.wasSuccessful() else 1)
