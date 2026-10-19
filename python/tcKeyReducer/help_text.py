# -*- coding: utf-8 -*-
"""Bilingual UI copy shared by the tooltips and the local help panel."""

TOOLTIPS = {
    '_value_line_edit': u'减键容差；通常数值越大，保留的关键帧越少。不是百分比，也不保证最终曲线的最大误差。\nReduction tolerance. Higher values usually keep fewer keys. Not a percentage or a bound on final curve error.',
    '_value_slider': u'调整 Value。默认只改参数；勾选 Auto Execute 后拖动会实时预览减键。\nAdjust Value. Changes parameters only by default; enable Auto Execute for live drag previews.',
    '_min_value': u'滑块可调整的最小 Value，不是动画的起始帧。\nMinimum Value available on the slider, not the animation start frame.',
    '_max_value': u'滑块可调整的最大 Value，不是动画的结束帧。\nMaximum Value available on the slider, not the animation end frame.',
    '_pre_bake': u'先在处理范围内按整帧采样，并将曲线改为非加权切线，再执行减键；可能改变原有切线与子帧细节。\nSample at whole frames in the processing range and make the curve non-weighted before reduction. May change tangents and subframe details.',
    '_align_keys': u'默认关闭。减键后取所有处理曲线保留时间点的并集，给其他曲线补键，使各属性在处理范围内的关键帧时间一致。保留小数帧；不为静态属性创建动画。键数会增加，补键可能影响插值。\nOff by default. After reduction, insert missing keys at the union of retained times so animated channels share key times within the range. Preserves subframes; does not animate static channels. Adds keys and may affect interpolation.',
    '_all_attrs_button': u'处理选中对象的所有可设置关键帧的属性；没有动画的属性不会产生减键结果。\nProcess all keyable attributes on selected objects. Attributes without animation have no keys to reduce.',
    '_graph_editor_selection': u'从默认 Graph Editor 当前显示的曲线获取连接属性名，再应用到选中对象；不是只处理高亮的关键帧。\nUse connected channel names from curves shown in the default Graph Editor on selected objects, not just highlighted keys.',
    '_channel_box_selection': u'处理 Channel Box 选中的属性；没有选中属性时回退为 All。\nProcess channels selected in the Channel Box. Falls back to All when no channels are selected.',
    '_entire_button': u'处理整条动画曲线。\nProcess the entire animation curve.',
    '_time_slider_button': u'使用 Maya 播放范围的起止帧，不是时间轴上高亮的临时选区。\nUse the Maya playback start/end range, not a highlighted time-slider selection.',
    '_custom_range_button': u'只处理自定义起止帧内的关键帧（包含边界）。\nProcess keys within the custom start/end frames, including both boundaries.',
    '_custom_range_begin': u'自定义处理范围的起始帧；应小于或等于结束帧。\nFirst frame of the custom range; must not exceed the end frame.',
    '_custom_range_end': u'自定义处理范围的结束帧；应大于或等于起始帧。\nLast frame of the custom range; must not precede the start frame.',
    '_auto_execute': u'默认关闭。开启后拖动滑块或输入 Value 并按 Enter 会执行减键；仅勾选此项不会执行。一次拖动可一次撤销。\nOff by default. Drag the slider or enter Value and press Return to reduce. Toggling alone does not execute. One drag is one undo step.',
    '_refresh_button': u'重新读取当前选择并缓存曲线，重建选择变化回调。新建场景后或界面状态未更新时可点击；不执行减键，也不恢复旧场景曲线。\nRe-read the current selection, cache its curves and rebuild selection callbacks. Use after creating a scene or when the UI is stale. Does not reduce keys or restore old-scene curves.',
    '_execute_button': u'按当前 Value、属性、时间范围和 Pre Bake 设置执行一次减键。重复执行会继续处理当前结果。\nReduce once using the current Value, channels, range and Pre Bake settings. Repeated executions work on the current result.',
    '_undo_button': u'撤销 Maya 最近的一步操作，包括减键或一次预览拖动；如果之后做了其他编辑，会先撤销那些编辑。\nUndo the latest Maya operation, including reduction or a preview drag. Later scene edits are undone first.',
    'attributes': u'选择要处理的属性，作用对象来自 Maya 当前的对象选择。\nChoose channels to process on the currently selected Maya objects.',
    'range': u'选择整条曲线、播放范围或自定义范围。\nChoose the entire curve, playback range or a custom frame range.',
    'help': u'打开中英双语说明，了解工作原理、参数与常见操作流程。\nOpen bilingual help covering the algorithm, settings and typical workflow.',
}

HELP_HTML = u"""
<html><head><style>
body { font-family: sans-serif; line-height: 1.5; }
h1 { font-size: 20px; } h2 { font-size: 16px; margin-top: 22px; }
li { margin-bottom: 8px; } .en { color: #888; }
</style></head><body>
<h1>KeyReducer 使用说明 / User Guide</h1>
<p>用于清理烘焙后或过于密集的动画关键帧，在减少关键帧数量的同时尽量保留运动形状。
<br/>Clean up baked or densely keyed animation by removing redundant keys while trying to retain its shape.</p>

<h2>1. 工作原理 / How it works</h2>
<p>工具逐条处理选中对象的动画属性。在指定时间范围内，先保留首尾关键帧，再在
“时间—数值”平面中，比较原关键帧与相邻保留帧之间直线的距离。
若偏差大于 Value，就加入偏差最大的关键帧并重新检查，直到满足容差或所有帧已保留。
少于三个待处理关键帧时不会进行此简化。</p>
<p>Each selected animation channel is processed separately. The first and last keys in the
processing range are retained. In time/value space, original key positions are compared with
the straight lines between retained keys. The key with the largest distance is added when
that distance exceeds Value. Checks repeat until the tolerance is met or all keys are kept.
Fewer than three keys in the range need no such simplification.</p>
<p>随后根据保留帧重建曲线，并尽量恢复保留帧的切线、权重和锁定状态，也会对部分平台段补帧。
Value 是该简化过程的距离容差，通常越大减键越强；它不是减键百分比，也不是最终插值曲线的
最大误差保证。时间单位、属性量纲和曲线形状都会影响结果，应结合播放与曲线检查。</p>
<p>The curve is rebuilt from retained keys, restoring their tangent, weight and lock settings
where possible, with additional keys for some flat sections. Value is the simplification
distance tolerance: larger values usually reduce more keys. It is neither a removal percentage
nor a guaranteed maximum error of the final interpolated curve. Time units, channel units and
curve shape affect the result, so inspect both playback and the curves.</p>

<h2>2. 参数与属性 / Parameters and channels</h2>
<ul>
<li><b>Value / Slider：</b>容差及其滑块；Min / Max 仅改变滑块数值范围，不是动画帧范围。<br/>
Tolerance and its slider. Min / Max limit the slider values, not the animation frames.</li>
<li><b>Align Keys：</b>默认关闭。先分别减键，再取所有参与处理的动画属性的保留时间点并集，
在其他曲线上补上缺少的键，使处理范围内的键时间一致。此选项不移动现有时间点、不取整小数帧，
也不为静态属性创建动画；补键后总键数可能比单独减键更多。新键依据减键后的曲线插值，
旧版 Maya 的补键可能改变相邻插值，应检查播放结果。撤销会同时恢复减键和补键。<br/>
Off by default. Reduce channels separately, then insert missing keys at the union of retained
times across participating animated channels. Key times match within the processing range.
Existing times and subframes are preserved; static channels are not animated. This may retain
more keys than independent reduction. Insertions follow the reduced curve; older Maya versions
may change neighboring interpolation, so check playback. Undo restores reduction and alignment together.</li>
<li><b>Pre Bake：</b>先在处理范围内逐整帧采样，并将动画曲线改为非加权，再执行简化。
适合先统一烘焙密集动画；可能改变原有切线与子帧细节，非加权设置会影响整条曲线。<br/>
Sample whole frames within the processing range and make the curve non-weighted before reduction.
Useful for a uniform baked starting point, but may change tangents and subframe detail.
The non-weighted setting affects the whole curve.</li>
<li><b>All：</b>选中对象的所有可设置关键帧属性。<br/>All keyable channels on selected objects.</li>
<li><b>Graph Editor Selection：</b>使用默认 Graph Editor 当前显示曲线连接的属性名，
并应用到选中对象。该模式不是仅简化高亮的关键帧。<br/>
Use connected channel names from curves shown in the default Graph Editor on selected objects.
This does not limit reduction to highlighted keys.</li>
<li><b>Channel Box Selection：</b>使用 Channel Box 选中的属性；未选属性时回退为 All。<br/>
Use selected Channel Box channels; fall back to All if none are selected.</li>
</ul>

<h2>3. 时间范围 / Processing range</h2>
<ul>
<li><b>Entire Curve：</b>整条曲线。<br/>The entire curve.</li>
<li><b>Time Slider：</b>Maya 的播放起止范围，不是高亮的临时选区。<br/>
The playback start/end range, not a highlighted time-slider selection.</li>
<li><b>Custom：</b>自定义起止帧，包含边界，起始帧不应晚于结束帧。
范围外的关键帧不参与减键，但边界切线或 Pre Bake 可能影响相邻插值。<br/>
Custom start/end frames, inclusive; start must not exceed end.
Keys outside the range are not reduced, but boundary tangents or Pre Bake can affect adjacent interpolation.</li>
</ul>

<h2>4. 常用流程 / Typical workflow</h2>
<p><b>Refresh：</b>重新读取当前选择的曲线并建立新的缓存，同时重新注册选择变化回调。
新建场景后、切换对象后界面未更新或回调丢失时，点击 Execute 前面的 Refresh。
即使当前没有选择对象，此按钮仍可使用。刷新保留当前曲线，不执行减键，也不会恢复旧场景的缓存。
已有的 Value、属性模式、时间范围等设置会保留。</p>
<p><b>Refresh:</b> Re-read and cache the currently selected curves, and re-register selection callbacks.
Use the button before Execute after creating a scene, or if the UI stops following selection changes.
It remains available with no selection. Refresh keeps the current curves without reducing keys or
restoring an old scene's cache. Value, channel mode and range settings are preserved.</p>
<ol>
<li>选中需要处理的动画对象。<br/>Select the animated objects to process.</li>
<li>选择属性模式和时间范围；初次使用可保留 All 与 Entire Curve。<br/>
Choose channels and a range; All and Entire Curve are convenient starting settings.</li>
<li>保持 Auto Execute 不勾选，从较小 Value 开始；仅在需要重新采样时启用 Pre Bake。<br/>
Leave Auto Execute off and start with a small Value. Enable Pre Bake when resampling is needed.</li>
<li>点击 Execute，检查曲线、关键帧数量与播放效果。结果不合适时点击 Undo，
再调节 Value 并重新执行。<br/>
Click Execute and inspect curves, key count and playback. If the result is unsuitable, click
Undo, adjust Value and execute again.</li>
<li>需要交互调整时勾选 Auto Execute，再拖动滑块。按下时缓存原曲线，拖动中每次
先恢复该缓存再减键；一次拖动合并为一步撤销。下一次拖动以当时的曲线作为新的起点。<br/>
For interactive adjustment, enable Auto Execute and drag. Curves are cached on press;
each preview restores that cache before reducing. One drag is grouped into one undo step.
The next drag starts from the curves as they exist at that time.</li>
</ol>

<h2>5. 执行与撤销 / Execution and undo</h2>
<p>Auto Execute 默认关闭：滑块和 Value 输入只更新参数，点击 Execute 才执行。
开启时，拖动滑块或输入 Value 后按 Enter 会执行；仅切换勾选状态不会执行。
Execute 和后续新拖动都会基于当前结果继续处理，若要比较同一原始曲线，请先 Undo。</p>
<p>Auto Execute is off by default: slider changes and Value entry only update settings;
click Execute to apply them. When enabled, dragging or entering Value and pressing Return
executes; toggling the checkbox alone does not. Execute and subsequent new drags work on
the current result. Undo first when comparing settings against the same original curve.</p>
<p>Undo 使用 Maya 的正常撤销队列，并非独立备份。如果减键后进行了其他编辑，
会先撤销那些编辑；也可以使用 Maya 的 Redo 重做。</p>
<p>Undo uses Maya's normal undo queue, not a separate backup. Later scene edits are undone
first. Maya's Redo is also available.</p>

<h2>6. 启动与插件 / Startup and plugin loading</h2>
<p>打开 UI 时先检查 keyReducer 是否已经加载；未加载时直接调用
cmds.loadPlugin('keyReducer.mll', quiet=True)。请将当前 Maya 版本的 MLL 所在目录加入
MAYA_PLUG_IN_PATH，由 Maya 解析插件位置。加载失败时会直接报告 Maya 的错误，暂不打开 UI。</p>
<p>Opening the UI checks whether keyReducer is loaded. If needed, it directly calls
cmds.loadPlugin('keyReducer.mll', quiet=True). Add the directory containing the MLL for your
Maya version to MAYA_PLUG_IN_PATH so Maya can resolve it. Loading failures report Maya's
error before opening the UI.</p>
</body></html>
"""
