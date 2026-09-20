# 素材库目录说明

当前版本 3.7.8。素材库独立于代码仓库，按用途组织：

- RenderPresets：渲染场景预设。
- NodePresets：材质与节点预设。
- Models：眼球、生长体等模型。
- Textures：配套贴图。
- Lights：灯光资源。
- Scripts：运行脚本，入口为 YuejunToolbox.py。
- Plugins：GN 等第三方安装包，不上传 Git。
- Settings：本机配置，不上传 Git。

VFace 为外部扩展包，在 VFace 浏览器内设置路径。不要复制进代码仓库。
默认预览工程位于 Maya 用户目录的 projects/Yuejun_Default，可通过 Settings/toolbox.json 的 default_project_root 指定素材库之外的目录。
_Backups 保存修改前的素材备份；确认不再需要后由用户自行处理。
Maya 场景保持原 ma/mb 格式。历史脚本不作为启动入口。
