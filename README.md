## Maya Key Reducer

Have you ever had to deal with baked curves and spent way too much time in cleaning them? Or felt you were dealing with curves with too many unnecessary keyframes?
Now you can reduce the number of keys in your animation curves interactively and quickly!
Use Execute to reduce keys, or enable Auto Execute for interactive slider previews.

Features:

* Works on selected objects
* Reduce keys of your animation curves preserving their shapes
* Works on multiple curves at once
* Curves selection from Graph Editor and Channel Box
* Frame range selection for local control over keys reduction
* Pre Bake resamples curves at whole frames and converts them to non-weighted curves.

## Curve fitting

Reduction compares three strategies against immutable reference samples: native tangent
behavior, frozen original numerical tangents, and refitted handles. Non-weighted
segments fit Hermite slopes by least squares; weighted segments also search Bezier
handle time lengths and fit their vertical offsets. Actual Maya evaluation accepts
or rejects each candidate. The valid result with fewer keys wins, followed by
lower sampled error at equal key counts. This is a heuristic, not a proof of the
globally smallest key set.

Output tangent types are free: automatic/spline/clamped/plateau tangents may become
Fixed, with tangent/weight locks released for independent handle fitting. Weighting
mode, infinity settings, existing key values and times remain unchanged. Range
endpoints and stepped transition boundaries are retained, and out-of-range samples
are checked for changes beyond numerical round-off. Undo and preview cache restore
the original tangent types, weights and locks.

`Value` is sampled absolute curve-value error in scene display units (rotation
uses the scene angle unit, translation the scene length unit). Original key times
and 8-64 subdivisions per original span, plus near-boundary samples, are checked
with a small safety margin. Finite sampling is not an analytic maximum-error proof.
Pre Bake compares against its resampled reference. Align Keys is a separate
insertion step and may adjust neighboring tangent types to preserve curve shape.

The design follows the distinctions between neighbor-dependent automatic tangents,
weighted Bezier and non-weighted interpolation in
[Autodesk animx](https://github.com/Autodesk/animx/blob/master/src/animx.cpp).
Evaluation stays in Maya's native API to match the running Maya version; animx is
not a build or runtime dependency.

## Windows builds

Run `build_win_dynamic.bat` (the older `CmakeBuildWindows.bat` forwards to it).
Like boneDynamicsNode, the script lets you select an installed Maya from the
registry, or build all supported Devkits; then select Visual Studio and Release
or Debug. Install CMake and the corresponding Visual Studio C++ toolsets.

Set `DEVKIT_ROOT` to the parent of your extracted Devkits (default: `D:\MayaDev`):

```bat
set "DEVKIT_ROOT=D:\_Code_Here\Maya"
build_win_dynamic.bat
```

Expected layout: `Autodesk_Maya_<year>..._DEVKIT_Windows/devkitBase`.
Build folders are `build/win64_<year>`. Successful builds copy the selected
configuration to `plug-ins/<year>/keyReducer.mll`. Selecting an installed Maya
uses its `lib` directory with the matching Devkit headers; batch mode uses each
Devkit's libraries. Failed builds return a nonzero exit code and do not copy
stale artifacts. Unsupported Devkits are skipped.

Toolset mapping follows boneDynamicsNode: Maya 2019-2023 uses v142;
2024-2027 uses v143. Maya 2018 uses v141; its old SDK must also contain the
CMake plugin helpers. C++17 is used except C++14 for 2018 and C++20 for 2027.
These are build targets; availability of the matching SDK and toolset is required.
C++ compatibility branches read `MAYA_API_VERSION` from the selected SDK;
no manually defined Maya year macros are needed.

## Python UI

Add `python` to Maya's Python path and the matching `plug-ins/<year>` directory
to `MAYA_PLUG_IN_PATH`, then run:

```python
from tcKeyReducer import tcKeyReducer
tcKeyReducer.run()
```

Startup checks `cmds.pluginInfo('keyReducer', q=True, loaded=True)` and calls
`cmds.loadPlugin('keyReducer.mll', quiet=True)` when needed, matching the
MagicBoneDynamic backend's loading pattern. Maya resolves the MLL through its
plugin search path. Loading errors propagate before the UI opens.

- **Auto Execute** is off by default. Slider changes and entering a value only
  update the reduction parameter.
- **Execute** reduces the selected attributes using the current value, range,
  and Pre Bake settings.
- **Align Keys** is off by default. It inserts keys at the union of retained
  times across animated channels, making their key times match within the
  processing range. It preserves subframes and does not animate static channels.
  Alignment can add keys back after reduction; Undo restores both steps.
- **Refresh**, before Execute, re-reads and caches the selected curves and
  rebuilds selection callbacks after a new scene or a stale UI. It remains
  enabled with no selection and does not reduce keys or restore old curves.
- **Undo** invokes Maya's normal undo for the latest operation. A reduction is
  undoable, and an automatic preview drag is grouped into one undo operation.
  If other scene edits are made afterward, Undo follows Maya's usual order.
- With **Auto Execute** enabled, dragging previews from the cached original
  curves; entering a value and pressing Return also executes.

The dialog is parented to Maya's main window and does not use global always-on-top.
Every option has a Chinese/English tooltip. The main window's **Help / 帮助**
action opens a scrollable bilingual guide covering the algorithm, settings,
workflow, previews, undo and automatic plugin loading. Help remains available
when no objects are selected.

The UI uses Python 2/3 compatible syntax and Unicode text, with imports for
PySide6, PySide2, and legacy PySide.

The C++ command also exposes alignment directly:

```python
cmds.tcKeyReducer('pCube1.translateX', 'pCube1.translateY', value=0.5, alignKeys=True)
```

`-ak` / `-alignKeys` aligns times across channels, rather than snapping them to
whole frames. Newer SDKs use shape-preserving key insertion; Maya SDKs older than
2019.3 sample the reduced curve before adding keys, so neighboring interpolation
can change. Pre Bake explicitly uses the current scene time unit at all frame rates.

## Validation

To run the integration checks in an isolated Maya environment after building:

```bat
set "MAYA_APP_DIR=%CD%\build\maya-test-profile"
set "MAYA_SKIP_USERSETUP_PY=1"
set "PYTHONDONTWRITEBYTECODE=1"
set "QT_QPA_PLATFORM=offscreen"
"C:\Program Files\Autodesk\Maya2022\bin\mayapy.exe" tests\test_maya_ui.py "%CD%\plug-ins\2022\keyReducer.mll"
```

The checks load the exact supplied plugin and cover manual parameter changes,
Execute/Undo/Redo, automatic preview undo grouping, text entry, empty selection,
and tangent preservation. They also check bilingual tooltips, help scrolling,
automatic loading by filename after unloading the plugin, failure propagation
and repeated UI opening.
Alignment checks cover the retained-time union, subframes, negative times,
different curve extents, single-key curves, range boundaries, weighted curve
shape, preview undo and Pre Bake at 25/30/60 fps.
Fitting regressions check improved key counts against native/frozen baselines,
weighted handle adjustment, dense subframe error, out-of-range shape protection,
and restoration of original types, weights and locks on Undo/Redo.
For Python 2 on Maya 2022, run the same command using `mayapy2.exe` with
`MAYA_PYTHON_VERSION=2` and a separate `MAYA_APP_DIR`.

## License

This project is licensed under [the LGPL license](http://www.gnu.org/licenses/).

## Contact us

Please feel free to contact us at support@toolchefs.com in case you would like contribute or simply have questions.

### ENJOY!
