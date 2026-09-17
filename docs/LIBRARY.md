# 素材库与扩展包

```text
Yuejun_ToolBox/
  RenderPresets/
    Arnold/                 Base_Arnold.ma 及预设自带资源
    VRay/                   Test_Vray.mb
  NodePresets/              Disp、Micro 等节点预设
  Models/                   独立眼球、生长体模型
  Scripts/                  MEL、Python 和单文件启动代码
  Textures/                 共用贴图
  Lights/                   灯光贴图
  Settings/
    toolbox.json            主要工具设置，包括 vface_root
    library_layout.json     本机迁移记录
    Backups/Before_3_7_4/    本次修改前的文本文件
  Projects/Default/         自动复用的 Maya 工作项目
```

主窗口“资源与工具设置”只选择工具箱素材库；VFace 扩展包路径统一在“VFace 素材”窗口选择。
素材库根路径是定位 Settings 的入口，保存在本机 Maya 偏好；VFace 路径保存在素材库 Settings/toolbox.json。
复制到另一台电脑后，按实际磁盘位置重新选择这两个目录。

VFace 无需搬入素材库。选择某个编号后，才复制该编号所需的头部、眼睛、眉毛、睫毛和贴图。
项目内路径使用 `sourceimages/Yuejun/VFace/061/01_head/maps/…`，配套眼睛使用同一编号下的 `03_extra/eyes/maps/sclera/…`。
几何源文件放在 `scenes/Yuejun/VFace/061/…`。没有用哈希值命名的编号文件夹。
不同来源的其他外部资源使用可读的来源目录层级。文件冲突时保留用户修改，必要时建立 `versions/Revision_001` 等版本目录。

## 默认工程

已有有效 Maya 项目时继续使用该项目。打开渲染预设或切换 VFace 时，如果当前项目未设置或不合规，自动创建并切换到素材库的 `Projects/Default`。
这是唯一允许位于素材库内部的工作项目位置；不能把整个素材库设为工作项目。
`workspace.mel` 已存在时不会重复创建，也不会覆盖其中的用户设置。

打开预设仍然是打开场景，有未保存修改时仍提示保存/放弃/取消。打开的是项目副本，原始预设不会被直接覆盖。
无效的工作项目设置不会被自动修复或覆盖；默认工程自身的规则如被改到目录外，会提示错误。

## 迁移与兼容

本机已将旧 Maya_shader_node 拆分为 RenderPresets 和 NodePresets，其他 Maya_* 文件夹改为上面的分类名。
文本场景里素材库的旧绝对路径已修改，修改前内容有备份；ma/mb 格式均保持不变。
二进制场景的旧路径由工具加载后的依赖解析和同步更新。旧资源键仍然受支持，以兼容脚本配置。
已有用户项目中的旧哈希资源目录不自动删除或改名，避免破坏已保存场景；新同步采用可读路径。

默认工程属于工作数据，VFace 原素材属于外部资源，均不进入代码仓库。
