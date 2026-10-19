# -*- coding: utf-8 -*-
import os
import sys
import traceback

try:
    from PySide6 import QtGui, QtCore, QtWidgets
    import shiboken6 as shiboken
except ImportError:
    try:
        from PySide2 import QtGui, QtCore, QtWidgets
        import shiboken2 as shiboken
    except ImportError:
        from PySide import QtGui, QtCore
        import PySide.QtGui as QtWidgets
        import shiboken

from maya import cmds
from maya import OpenMayaUI as omui
from .help_text import HELP_HTML, TOOLTIPS

GRAPH_EDITOR_NAME = 'graphEditor1GraphEd'
CHANNEL_BOX_NAME = 'mainChannelBox'


def _maya_main_window():
    pointer = omui.MQtUtil.mainWindow()
    if pointer:
        return shiboken.wrapInstance(int(pointer), QtWidgets.QWidget)
    return None


def _ensure_plugin_loaded():
    try:
        loaded = cmds.pluginInfo('keyReducer', q=True, loaded=True)
    except RuntimeError:
        loaded = False
    if not loaded:
        cmds.loadPlugin('keyReducer.mll', quiet=True)


def _build_layout(horizontal):
    # type: (bool)-> QtWidgets.QHBoxLayout|QtWidgets.QVBoxLayout
    if (horizontal):
        layout = QtWidgets.QHBoxLayout()
    else:
        layout = QtWidgets.QVBoxLayout()
    layout.setContentsMargins(QtCore.QMargins(2, 2, 2, 2))
    return layout

class LineWidget(QtWidgets.QWidget):
    def __init__(self, label, widget, width=90, parent=None):
        # type: (str, QtWidgets.QWidget, int, QtWidgets.QWidget) -> None
        super(LineWidget, self).__init__(parent=parent)

        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

        self._main_layout = _build_layout(True)
        self.setLayout(self._main_layout)

        label = QtWidgets.QLabel(label)
        label.setFixedWidth(width)
        self._main_layout.addWidget(label, 0)
        self._main_layout.addWidget(widget, 0)

def _create_separator(vertical=False):
    separator = QtWidgets.QFrame()
    if vertical:
        separator.setFrameShape(QtWidgets.QFrame.VLine)
    else:
        separator.setFrameShape(QtWidgets.QFrame.HLine)
    separator.setFrameShadow(QtWidgets.QFrame.Sunken)
    return separator

def _get_icons_path():
    tokens = __file__.split(os.path.sep)
    return os.path.sep.join(tokens[:-1] + ['icons']) + os.path.sep


class KeyReducerControls(QtWidgets.QWidget):
    def __init__(self,parent=None):
        super(KeyReducerControls, self).__init__(parent)
        self.setWindowTitle('Key Reducer')
        self.setObjectName('Key Reducer')

        self._main_layout = _build_layout(False)
        self.setLayout(self._main_layout)

        self._script_jobs = []

        self._slider_drag_active = False

        self._create_widgets()
        self._connect_signals()

    def _create_value_layout(self):
        layout = _build_layout(True)
        self._main_layout.addLayout(layout)

        v_layout = _build_layout(False)
        self._value_line_edit = QtWidgets.QLineEdit()
        self._value_line_edit.setFixedWidth(80)
        self._value_validator = QtGui.QDoubleValidator()
        self._value_line_edit.setText("0.5")
        self._value_line_edit.setValidator(self._value_validator)

        l = LineWidget("Value:", self._value_line_edit, 40)
        l.setFixedWidth(130)
        v_layout.addWidget(l, 0, QtCore.Qt.AlignTop)

        self._pre_bake = QtWidgets.QCheckBox("Pre Bake")
        l = LineWidget("", self._pre_bake, 40)
        v_layout.addWidget(l)

        self._align_keys = QtWidgets.QCheckBox("Align Keys")
        self._align_keys.setChecked(False)
        l = LineWidget("", self._align_keys, 40)
        v_layout.addWidget(l)

        layout.addLayout(v_layout)

        v_layout = _build_layout(False)
        layout.addLayout(v_layout)
        self._value_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self._value_slider.setMinimum(0)
        self._value_slider.setMaximum(10000)
        self._value_slider.setValue(5000)
        self._value_slider.setTickPosition(QtWidgets.QSlider.TicksAbove)
        self._value_slider.setTickInterval(1000)
        v_layout.addWidget(self._value_slider)

        h_layout = _build_layout(True)
        v_layout.addLayout(h_layout)

        self._min_value = QtWidgets.QDoubleSpinBox()
        self._min_value.setValue(0.0)
        self._min_value.setFixedWidth(80)
        self._min_value.setSingleStep(0.1)
        self._min_value.setMaximum(0.4)

        l = LineWidget("Min:", self._min_value, 24)
        l.setFixedWidth(115)
        h_layout.addWidget(l, 0, QtCore.Qt.AlignLeft)

        self._max_value = QtWidgets.QDoubleSpinBox()
        self._max_value.setValue(1.0)
        self._max_value.setFixedWidth(80)
        self._max_value.setSingleStep(0.1)
        self._max_value.setMinimum(1.0)
        self._max_value.setMaximum(1000000)
        self._max_value.setMinimum(0.6)

        l = LineWidget("Max:", self._max_value, 24)
        l.setFixedWidth(115)
        h_layout.addWidget(l, 0, QtCore.Qt.AlignRight)

    def _create_time_layout(self):
        group = QtWidgets.QGroupBox("Range: ")
        group.setToolTip(TOOLTIPS['range'])
        layout = _build_layout(False)
        group.setLayout(layout)
        self._main_layout.addWidget(group)

        h_layout = _build_layout(True)
        buttonGroup = QtWidgets.QButtonGroup(self)
        self._entire_button = QtWidgets.QRadioButton("Entire Curve")
        self._entire_button.setChecked(1)
        self._entire_button.setFixedWidth(120)
        self._time_slider_button = QtWidgets.QRadioButton("Time Slider")
        self._time_slider_button.setFixedWidth(120)
        self._custom_range_button = QtWidgets.QRadioButton("Custom")
        h_layout.addWidget(self._entire_button)
        h_layout.addWidget(self._time_slider_button)
        h_layout.addWidget(self._custom_range_button)

        layout.addLayout(h_layout)

        buttonGroup.addButton(self._entire_button)
        buttonGroup.addButton(self._time_slider_button)
        buttonGroup.addButton(self._custom_range_button)

        h_layout = _build_layout(True)
        self._parent_custom_range = QtWidgets.QWidget()
        self._parent_custom_range.setFixedWidth(290)
        self._parent_custom_range.setLayout(h_layout)
        l = QtWidgets.QLabel("Custom: ")
        l.setFixedWidth(60)
        h_layout.addWidget(l)
        self._custom_range_begin = QtWidgets.QSpinBox()
        self._custom_range_begin.setFixedWidth(100)
        min = cmds.playbackOptions(q=True, minTime=True)
        self._custom_range_begin.setValue(int(min))
        h_layout.addWidget(self._custom_range_begin)
        l = QtWidgets.QLabel("-")
        l.setFixedWidth(10)
        h_layout.addWidget(l)
        self._custom_range_end = QtWidgets.QSpinBox()
        self._custom_range_end.setFixedWidth(100)
        max = cmds.playbackOptions(q=True, maxTime=True)
        self._custom_range_end.setValue(int(max))
        h_layout.addWidget(self._custom_range_end)

        self._parent_custom_range.setEnabled(False)

        layout.addWidget(self._parent_custom_range)

    def _create_attrs_layout(self):
        group = QtWidgets.QGroupBox("Attributes: ")
        group.setToolTip(TOOLTIPS['attributes'])
        layout = _build_layout(True)
        group.setLayout(layout)
        self._main_layout.addWidget(group)

        buttonGroup = QtWidgets.QButtonGroup(self)
        self._all_attrs_button = QtWidgets.QRadioButton("All")
        self._all_attrs_button.setChecked(1)
        self._all_attrs_button.setFixedWidth(120)

        self._graph_editor_selection = QtWidgets.QRadioButton("Graph Editor Selection")
        self._graph_editor_selection.setFixedWidth(140)

        self._channel_box_selection = QtWidgets.QRadioButton("Channel Box Selection")
        self._channel_box_selection.setFixedWidth(140)

        layout.addWidget(self._all_attrs_button)
        layout.addWidget(self._graph_editor_selection)
        layout.addWidget(self._channel_box_selection)
        layout.addWidget(QtWidgets.QWidget(), 1)

        buttonGroup.addButton(self._all_attrs_button)
        buttonGroup.addButton(self._graph_editor_selection)
        buttonGroup.addButton(self._channel_box_selection)

    def _create_widgets(self):
        self._main_layout.addWidget(_create_separator())
        self._create_value_layout()
        self._main_layout.addWidget(_create_separator())
        self._create_attrs_layout()
        self._main_layout.addWidget(_create_separator())
        self._create_time_layout()

        self._main_layout.addWidget(_create_separator())
        actions = _build_layout(True)
        self._auto_execute = QtWidgets.QCheckBox("Auto Execute")
        self._auto_execute.setChecked(False)
        self._auto_execute.setToolTip("Preview reduction while dragging or after entering a value.")
        self._refresh_button = QtWidgets.QPushButton("Refresh")
        self._execute_button = QtWidgets.QPushButton("Execute")
        self._undo_button = QtWidgets.QPushButton("Undo")
        self._undo_button.setToolTip("Undo the latest Maya operation, including a reduction or preview drag.")
        actions.addWidget(self._auto_execute)
        actions.addStretch(1)
        actions.addWidget(self._refresh_button)
        actions.addWidget(self._execute_button)
        actions.addWidget(self._undo_button)
        self._main_layout.addLayout(actions)
        self._main_layout.addWidget(QtWidgets.QWidget(), 1)
        for name, tip in TOOLTIPS.items():
            if not name.startswith('_'):
                continue
            widget = getattr(self, name)
            widget.setToolTip(tip)
            if isinstance(widget.parentWidget(), LineWidget):
                widget.parentWidget().setToolTip(tip)

    def _set_selection_enabled(self, enabled):
        # Refresh must remain clickable when a lost callback leaves the UI stale.
        for name in TOOLTIPS:
            if name.startswith('_') and name != '_refresh_button':
                getattr(self, name).setEnabled(enabled)

    def _connect_signals(self):
        self._min_value.valueChanged.connect(self._min_value_changed)
        self._max_value.valueChanged.connect(self._max_value_changed)

        self._value_slider.sliderPressed.connect(self._value_slider_pressed)
        self._value_slider.valueChanged.connect(self._value_slider_moved)
        self._value_slider.sliderReleased.connect(self._value_slider_released)

        self._value_line_edit.returnPressed.connect(self._value_line_edit_finished)

        self._execute_button.clicked.connect(self._execute)
        self._undo_button.clicked.connect(self._undo)

        self._custom_range_button.toggled.connect(self._custom_range_button_toggled)

    def _custom_range_button_toggled(self):
        self._parent_custom_range.setEnabled(self._custom_range_button.isChecked())

    def _value_line_edit_finished(self):
        try:
            value = float(self._value_line_edit.text())
        except ValueError:
            self._sync_slider_value()
            return
        value = max(self._min_value.value(), min(value, self._max_value.value()))
        self._value_slider.setValue(int(round(value * 10000)))
        self._sync_slider_value()
        if self._auto_execute.isChecked():
            self._execute()

    def _sync_slider_value(self):
        self._value_line_edit.setText(str(self._value_slider.value() / 10000.0))

    def _execute(self):
        try:
            self._run_command()
        except Exception:
            traceback.print_exc(file=sys.stdout)

    def _undo(self):
        try:
            if not cmds.undoInfo(query=True, undoQueueEmpty=True):
                cmds.undo()
        except Exception:
            traceback.print_exc(file=sys.stdout)

    def _value_slider_pressed(self):
        self._sync_slider_value()
        if not self._auto_execute.isChecked():
            return
        attrs = self._get_attributes()
        if not attrs:
            return
        cmds.undoInfo(openChunk=True, chunkName='tcKeyReducerDragging')
        try:
            cmds.tcStoreKeys(*attrs)
            self._slider_drag_active = True
            self._run_command()
        except Exception:
            self._slider_drag_active = False
            cmds.undoInfo(closeChunk=True)
            traceback.print_exc(file=sys.stdout)

    def _value_slider_moved(self, value=None):
        self._sync_slider_value()
        if not self._slider_drag_active:
            return
        try:
            cmds.tcRestoreKeys()
            self._run_command()
        except Exception:
            traceback.print_exc(file=sys.stdout)

    def _value_slider_released(self):
        self._sync_slider_value()
        if not self._slider_drag_active:
            return
        try:
            cmds.tcRestoreKeys()
            self._run_command()
        except Exception:
            traceback.print_exc(file=sys.stdout)
        finally:
            self._slider_drag_active = False
            cmds.undoInfo(closeChunk=True)

    def _min_value_changed(self, value):
        self._value_slider.setMinimum(int(round(value * 10000)))
        self._value_slider.setTickInterval(max(1, int(round((self._max_value.value() - self._min_value.value()) * 1000))))

    def _get_attribute_names_from_graph_editor(self):
        if not cmds.animCurveEditor(GRAPH_EDITOR_NAME, exists=True):
            return []
        animCurves = cmds.animCurveEditor(GRAPH_EDITOR_NAME, q=True, cs=True)
        channels = set()
        for a in animCurves or []:
            connections = cmds.listConnections("%s.output" % a, s=False, d=True, plugs=True)
            if not connections:
                continue
            tokens = connections[0].split(".")
            channels.add(str(tokens[len(tokens) - 1]))
        return list(channels)

    def _get_attribute_names_from_channel_box(self):
        channels = set()
        queried_channels =  ([] +
                            (cmds.channelBox(CHANNEL_BOX_NAME, selectedMainAttributes=True, q=True) or []) +
                            (cmds.channelBox(CHANNEL_BOX_NAME, selectedShapeAttributes=True, q=True) or []) +
                            (cmds.channelBox(CHANNEL_BOX_NAME, selectedHistoryAttributes=True, q=True) or []) +
                            (cmds.channelBox(CHANNEL_BOX_NAME, selectedOutputAttributes=True, q=True) or []))

        for c in queried_channels:
            channels.add(str(c))
        return list(channels)

    def _get_all_attributes(self):
        selection = cmds.ls(sl=True, l=True)
        if not selection:
            return []
        return [str(c) for c in (cmds.listAttr(selection, keyable=True) or [])]

    def _get_attributes(self):

        if self._graph_editor_selection.isChecked():
            channels = self._get_attribute_names_from_graph_editor()
        elif self._channel_box_selection.isChecked():
            channels = self._get_attribute_names_from_channel_box()
            if not channels:
                channels = self._get_all_attributes()
        else:
            channels =  self._get_all_attributes()

        ret = [] # type: list[str]
        for selection in cmds.ls(sl=True, l=True):
            for channel in channels:
                attr_name = "{}.{}".format(selection, channel)
                ret.append(attr_name)
        return ret

    def _run_command(self):
        attrs = self._get_attributes()

        if not attrs:
            cmds.warning('Select objects with keyable attributes to reduce.')
            return

        kwargs = {'value': float(self._value_line_edit.text())}
        if (self._pre_bake.isChecked()):
            kwargs['preBake'] = True
        if self._align_keys.isChecked():
            kwargs['alignKeys'] = True

        if self._time_slider_button.isChecked():
            kwargs['startTime'] = cmds.playbackOptions(q=True, minTime=True)
            kwargs['endTime'] = cmds.playbackOptions(q=True, maxTime=True)
        elif self._custom_range_button.isChecked():
            kwargs['startTime'] = self._custom_range_begin.value()
            kwargs['endTime'] = self._custom_range_end.value()

        cmds.tcKeyReducer(*attrs, **kwargs)

    def _max_value_changed(self, value):
        self._value_slider.setMaximum(int(round(value * 10000)))
        self._value_slider.setTickInterval(max(1, int(round((self._max_value.value() - self._min_value.value()) * 1000))))


class KeyReducerHelpDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(KeyReducerHelpDialog, self).__init__(parent)
        self.setWindowTitle(u'KeyReducer Help / 使用说明')
        self.resize(740, 640)
        layout = QtWidgets.QVBoxLayout(self)
        self._browser = QtWidgets.QTextBrowser()
        self._browser.setReadOnly(True)
        self._browser.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self._browser.setHtml(HELP_HTML)
        layout.addWidget(self._browser)
        close_button = QtWidgets.QPushButton(u'Close / 关闭')
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button, 0, QtCore.Qt.AlignRight)


class KeyReducerWidget(QtWidgets.QDialog):
    def __init__(self,parent=None):
        if parent is None:
            parent = _maya_main_window()
        super(KeyReducerWidget, self).__init__(parent)
        self.setWindowTitle('Key Reducer')
        self.setObjectName('Key Reducer')

        self._main_layout = _build_layout(False)
        self.setLayout(self._main_layout)

        self._help_dialog = None
        self._menu_bar = QtWidgets.QMenuBar(self)
        self._menu_bar.setNativeMenuBar(False)
        self._help_action = self._menu_bar.addAction(u'Help / 帮助')
        self._help_action.setToolTip(TOOLTIPS['help'])
        self._help_action.triggered.connect(self._show_help)
        self._main_layout.setMenuBar(self._menu_bar)

        about = QtWidgets.QLabel()
        about.setPixmap(QtGui.QPixmap(_get_icons_path()+'abouts.png'))
        self._main_layout.addWidget(about)

        self._controls = KeyReducerControls()
        self._controls._refresh_button.clicked.connect(self._refresh)
        self._main_layout.addWidget(self._controls)

        self._script_jobs = []

    def _show_help(self):
        if self._help_dialog is None:
            self._help_dialog = KeyReducerHelpDialog(self)
        self._help_dialog.show()
        self._help_dialog.raise_()
        self._help_dialog.activateWindow()

    def _selection_changed(self):
        selection = cmds.ls(sl=True, l=True)
        self._controls._set_selection_enabled(bool(selection))

    def _refresh(self):
        _ensure_plugin_loaded()
        # Keep the visible result and discard the previous drag session. Never
        # restore cached curves here: they may belong to a scene already closed.
        if self._controls._slider_drag_active:
            self._controls._slider_drag_active = False
            cmds.undoInfo(closeChunk=True)
        self._start_script_jobs()
        self._selection_changed()
        attrs = [attr for attr in self._controls._get_attributes() if cmds.objExists(attr)]
        if attrs:
            cmds.tcStoreKeys(*attrs)

    def _start_script_jobs(self):
        self._stop_script_jobs()
        id = cmds.scriptJob(event=["SelectionChanged", self._selection_changed])
        # Batch/standalone Maya may return None instead of creating a UI job.
        if id is not None:
            self._script_jobs.append(id)

    def _stop_script_jobs(self):
        for id in self._script_jobs:
            if cmds.scriptJob(exists=id):
                cmds.scriptJob(kill=id)

        self._script_jobs = []

    def closeEvent(self, event):
        self._stop_script_jobs()
        if self._help_dialog is not None:
            self._help_dialog.close()
        super(KeyReducerWidget, self).closeEvent(event)

key_reducer_widget = None
def get_key_reducer_widget():
    global key_reducer_widget
    if key_reducer_widget is None:
        key_reducer_widget = KeyReducerWidget()
    return key_reducer_widget


def run():
    _ensure_plugin_loaded()

    w = get_key_reducer_widget()
    w._start_script_jobs()
    w._selection_changed()
    w.resize(500, 200)
    w.show()
    w.raise_()
    return w
