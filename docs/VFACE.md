# VFace 素材切换（Arnold）

先打开工具里的 Arnold 场景预设，再点击 **VFace 素材 → 选择 VFace 头部与贴图**。
选择包含各编号文件夹的素材总目录，也可以直接选择一个编号目录。选择编号并点击切换。
扩展包路径统一在“VFace 素材”窗口设置，保存到素材库 Settings/toolbox.json。新电脑需要按实际位置重新选择。

每套素材必须包含：

```text
115/
  01_head/geos/XYZ_headEyesOpen_GEO.obj
  01_head/maps/XYZ_albedo_lin_srgb.1001.exr
  01_head/maps/XYZ_dispCalibrated_mid0_raw.1001.exr
  01_head/maps/XYZ_utility_lin_srgb.1001.exr
  03_extra/eyes/geos/（8 个左右眼睛、泪线 OBJ）
  03_extra/eyes/maps/sclera/（左右 albedo 和校准置换 EXR）
  03_extra/groom/geos/（上下睫毛、两组眉毛 OBJ）
```

## 接线与保留内容

- 采用供应商针对原配网格校准的单通道置换：Raw、红通道、零中值、置换高度 1。它不是中值 0.5 的多通道置换，不能混用其解码方式。
- 线性 sRGB EXR albedo 使用线性 sRGB 输入空间，接原模板的皮肤 subsurfaceColor；原模板 subsurface 权重为 1。
- utility 作为数据贴图使用 Raw，保留原模板的蓝通道 cavity / 粗糙度处理网络。
- 共用 ID 遮罩、Skin_Mat 的艺术调节、灯光、相机、AOV 和渲染采样保持原模板设置。不会因为换一个人物就重写全部渲染设置。
- 新头部启用 Arnold Catclark 细分（4 级）、零中值置换、高度 1、边界 1、autobump。不会再叠加一张 normal 贴图造成重复细节。
- 更换整个 mesh shape，包括它自己的 UV；保留原 transform 及旧 shape。原模板名 `XYZ_headEyesOpen_GEO_Mesh` 和标准名 `XYZ_headEyesOpen_GEO` 都可识别。

依据 Texturing XYZ 官方资料：[校准置换](https://texturing.xyz/pages/introduction-vface-fully-calibrated-displacement)、[Albedo](https://texturing.xyz/pages/introduction-vface-albedo)、[Utility 通道](https://texturing.xyz/pages/vface-utility)。细分等级和采样属于本预设选择，不代表供应商规定的通用最终渲染参数。

## 项目与撤销

只同步所选编号的 13 个 OBJ 和 7 张贴图，不批量复制整个 VFace 库。
路径为 sourceimages/Yuejun/VFace/061/01_head/maps/... 和 03_extra/eyes/maps/sclera/...；OBJ 位于 scenes/Yuejun/VFace/061/...。
不同编号的同名贴图保存在不同项目子目录。重复使用复用已有文件；在项目里修改过的文件也不会被直接覆盖。
外部源素材变更使用已有同步版本策略。无有效项目时自动创建/复用素材库 Projects/Default。

一次撤销会恢复切换前的可见网格、材质分配及贴图。Maya 的文件导入本身不能撤销，因此首次导入的隐藏网格缓存仍会留在场景里，并随场景保存，以便再次切换时复用。
不是无限次切换都零增长：每个不同人物/几何版本首次使用都会增加一套隐藏网格。首次创建的眼白材质缓存也保留，以避免 Arnold AOV 回调破坏重做；可见状态和贴图切换仍可撤销。

## 支持范围与验证

这是配套 Arnold 预设的人物替换功能，不是任意角色的重拓扑或绑定迁移工具。
引用、实例、带建模/变形历史的头部，以及有 outMesh/worldMesh 下游连接的头部会被拒绝；不会迁移已有 XGen 毛发或绑定。
配套眼睛、泪线、眉毛和睫毛随编号切换，分组到 VFace_GRP 下的 Head、Eyes、Eyelashes、Eyebrows 子组。左右眼白接配套线性颜色图和 Raw 校准置换。源包没有虹膜配色贴图，虹膜保留原预设材质，不宣称获得完整真实虹膜着色。
不导入 groom/scalps 下的生长面，不迁移已有 XGen 毛发、牙齿或绑定；不包含闭眼、多 UDIM 变体。

已在 Maya 2022 独立测试进程验证本机 061、074 和 115：UV 数组及面角 UV 分配、来回切换、缓存复用、撤销/重做、锁定和下游连接拒绝、默认项目复用及编号目录。
115 已完成 512×512 CPU Arnold 技术预览。独立渲染授权不可用，预览带 Arnold 水印且仍有噪点；这不是最终成片质量验收。UI 尚未做真实 Maya 的视觉验收。
