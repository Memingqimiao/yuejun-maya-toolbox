# -*- coding: utf-8 -*-
"""User-supplied reference notes. Expressions are text, never executed by the tool."""
NOTES = [
    dict(title='Width · 贴图控制宽度', language='XGen',
         usage='在 Width 创建 Mask，再打开表达式编辑器。保留 Maya 为你生成的 map 路径，将下方 longhair_width_mask 替换为实际名称。\n\n遮罩值为 0～1 时，乘以 0.02 得到 0～0.02 的宽度。若贴图超出此范围，乘法本身不会强制钳制上限。',
         code="$a=map('${DESC}/paintmaps/longhair_width_mask');#3dpaint,20.0\n$a*0.02"),
    dict(title='Noise · 随机百分比 13%', language='XGen',
         usage='粘贴到需要随机黑白遮罩的表达式栏，例如 Noise 的 Mask。percentStray 的范围注释会提供 0～100 的滑块。\n\n输出为 0 或 1；百分比代表概率，小量毛发的实际比例不一定精确等于设定值。',
         code='$percentStray=13.0000;#0.00,100\nrand() < $percentStray/100.0 ? 1 : 0'),
    dict(title='Noise · 随机百分比 80%', language='XGen',
         usage='与 13% 条目相同，这里将初始比例设为 80%。可按需要修改数值。',
         code='$percentStray=80; #0,100\nrand() < $percentStray/100.0 ? 1 : 0'),
    dict(title='Cut · 按长度随机修剪', language='XGen',
         usage='用于 Cut 修改器的 Amount（修剪长度）表达式栏。虽然原笔记标题写作 Cut Mask，但该式输出的是长度，不是单纯的 0～1 遮罩。\n\n随机比例乘以 $cLength：同一比例下，越长的毛发切掉的绝对长度越大。',
         code='$cut=rand(0,1);\n$cut*$cLength'),
    dict(title='Coil · 百分比与随机种子', language='XGen',
         usage='用于 Coil 的遮罩表达式。percentage 控制随机选中的比例，percentageSeed 控制随机分布；修改种子可换一组毛发。',
         code='$percentage=10;#0,100\n$percentageSeed=5;#0,20\n$randvalue=rand(0,1,$percentageSeed);\n$randvalue<$percentage/100? 1 : 0'),
    dict(title='Mask · 绘制遮罩叠加百分比', language='XGen · 追加片段',
         usage='先创建并绘制 Mask，保留编辑器原有的 $a=map(...) 那一行，再追加下方代码。\n\n代码故意不包含 map 行，不要删除已有定义。如果原来的变量不叫 $a，请同步修改代码中的 $a。白色区域使用完整设定比例，灰色按比例降低，黑色不选中。',
         code='$percentStray=100.0000; #0.00,100\nrand() < ($percentStray*$a) /100.0? 1:0'),
    dict(title='Color · Salt and Pepper', language='XGen',
         usage='新建名为 random 的颜色自定义参数，将 MAPNAME 替换为你绘制的颜色贴图名称；保留实际 map 路径。\n\n可在基本体颜色中查看效果。Arnold 材质使用 aiUserDataColor 时，将其 Attribute 对应到导出的 random 颜色属性。还需确认该参数实际随 XGen 导出。\n\n此条保留原笔记算法，包括 $noise2 的加法。结果可能超出 0～1，亮度和随机比例的视觉效果请在实际材质中检查。',
         code="$hairMap = map('${DESC}/paintmaps/custom_color_MAPNAME');#3dpaint,50.0\n$percentStrand = 75; #0,100\n$colour = [1,1,1]; #colour\n\n$percentRand=rand() < $percentStrand/100 ? 0:1;\n$noise=$percentRand*$colour;\n$white = $noise + $hairMap;\n\n$percentStrand2 = 20; #0,100\n$colour2 = [0.027451,0.0196078,0.00392157]; #colour\n$percentRand2=rand() < $percentStrand2/100 ? 0:1;\n$noise2=$percentRand2+$colour2;\n\n$white * $noise2"),
    dict(title='stray · 偏离毛发条件', language='XGen',
         usage='先设置 Description 的 Stray 百分比，再使用条件表达式。stray()? X : Y 表示：偏离毛发返回 X，其余返回 Y。\n\n下面使用可直接复制的数值示例：偏离毛发为 1，其余为 0。可用于 Noise 等需要区分两类毛发的参数。\n\n原笔记参考链接（未对网页内容作验证）：\nhttps://www.bilibili.com/read/cv12015260/',
         code='stray()? 1 : 0'),
    dict(title='rand · 最小值与最大值', language='XGen',
         usage='rand(最小值, 最大值) 返回范围内的随机数。下面示例为 0～1。',
         code='rand(0,1)'),
    dict(title='Length · 长度比例', language='XGen',
         usage='用毛发长度乘以比例。Maya 2022 自带 XGen 提示使用 $cLength，L 必须大写；已修正原笔记中的 $clength。',
         code='$cLength*0.001'),
    dict(title='clamp · 限制长度范围', language='XGen',
         usage='clamp(x, min, max) 将结果限制到最小值与最大值之间。下面把长度乘以 0.001 后限制在 0.005～0.1。\n\n$cLength 的 L 为大写。',
         code='clamp($cLength*0.001,0.005,0.1)'),
    dict(title='MEL · 清理未知节点（原笔记）', language='MEL · 会删除节点',
         usage='这是 MEL，不是 XGen 表达式。若手动执行，应粘贴到 Script Editor 的 MEL 页签。\n\n原笔记会解锁并删除所有 unknown 节点，还会移除未知插件记录；包含缺失插件的数据也可能被删除。一般优先使用工具箱现有的“清理无效节点”，它会跳过引用和锁定节点。这里仅提供查看和复制，不自动执行。',
         code='string $unknownNodes[] = `ls -type "unknown"`;\n\nfor($node in $unknownNodes) {\n    print("Deleting " + $node + "\\n");\n    lockNode -lock 0 $node;\n    delete $node;\n}\n\nstring $plugin;\nstring $unknownPlugins[] = `unknownPlugin -query -list`;\nfor ($plugin in $unknownPlugins) {\n    unknownPlugin -remove $plugin;\n}')
]


def search(query):
    query = query.strip().lower()
    return [item for item in NOTES if query in (item['title'] + ' ' + item['usage']).lower()]
