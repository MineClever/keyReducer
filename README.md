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
* Pre Bake mode converts weighted curves into non-weighted, it fixes all your broken tangents too.

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

Add `python` to Maya's Python path, then run:

```python
from tcKeyReducer import tcKeyReducer
tcKeyReducer.run()
```

Startup automatically reuses a loaded KeyReducer plugin or loads the MLL for the
current Maya version from `plug-ins/<year>` in this checkout, or
`maya_<year>/Plug-ins` when the package is deployed under `pluginLoader/scripts`.
It also tries `keyReducer` and `tcKeyReducer` through Maya's plugin search path.
Loading failures report the attempts and reasons before opening the UI.

- **Auto Execute** is off by default. Slider changes and entering a value only
  update the reduction parameter.
- **Execute** reduces the selected attributes using the current value, range,
  and Pre Bake settings.
- **Undo** invokes Maya's normal undo for the latest operation. A reduction is
  undoable, and an automatic preview drag is grouped into one undo operation.
  If other scene edits are made afterward, Undo follows Maya's usual order.
- With **Auto Execute** enabled, dragging previews from the cached original
  curves; entering a value and pressing Return also executes.

Every option has a Chinese/English tooltip. The main window's **Help / 帮助**
action opens a scrollable bilingual guide covering the algorithm, settings,
workflow, previews, undo and automatic plugin loading. Help remains available
when no objects are selected.

The UI uses Python 2/3 compatible syntax and Unicode text, with imports for
PySide6, PySide2, and legacy PySide.

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
automatic loading after unloading the plugin, the deployed version-directory
layout, plugin-path fallback, failure reporting and repeated UI opening.
For Python 2 on Maya 2022, run the same command using `mayapy2.exe` with
`MAYA_PYTHON_VERSION=2` and a separate `MAYA_APP_DIR`.

## License

This project is licensed under [the LGPL license](http://www.gnu.org/licenses/).

## Contact us

Please feel free to contact us at support@toolchefs.com in case you would like contribute or simply have questions.

### ENJOY!
