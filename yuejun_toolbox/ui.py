# -*- coding: utf-8 -*-
"""maya.cmds UI and exception boundary. Core logic lives in core.py."""
import logging
from functools import partial

from maya import cmds, mel

from . import config, core, project, eyes, preview, gn

WINDOW = "yuejunToolboxWindow"
_instance = None
GAP = 8
BUTTON_HEIGHT = 34
ACCENT = (0.23, 0.39, 0.43)
_LOG = logging.getLogger("yuejun_toolbox")


class ToolboxWindow(object):
    def __init__(self):
        self.buttons = {}
        self.busy = False
        self.path_field = None
        self.status = None
        self.vray_mode = False
        self.delete_blend_source = None

    def build(self):
        config.migrate_preferences()
        window = cmds.window(WINDOW, title="Yuejun Toolbox 3.7.14",
                             widthHeight=(540, 770), sizeable=True)
        root = cmds.formLayout(parent=window)
        header = cmds.columnLayout(parent=root, adjustableColumn=True, rowSpacing=GAP)
        self.section(header, *config.PROJECT_GROUP, prominent=True)
        mode = cmds.columnLayout(parent=header, adjustableColumn=True, rowSpacing=4)
        cmds.checkBox(parent=mode, label="使用 V-Ray（默认 Arnold）", height=24,
                      value=False, changeCommand=self.switch_renderer)
        cmds.text(parent=mode, label="打开预设 / 切换 VFace：未设置项目时自动使用默认工程", align="left", height=20)
        settings = cmds.frameLayout(parent=header, label="资源与工具设置", collapsable=True,
                                    collapse=True, marginWidth=GAP, marginHeight=GAP)
        settings_column = cmds.columnLayout(parent=settings, adjustableColumn=True, rowSpacing=GAP)
        self.path_field = cmds.textFieldButtonGrp(
            parent=settings_column, label="资源目录", text=config.resource_root(),
            buttonLabel="选择…", adjustableColumn=2, columnWidth3=(60, 300, 60),
            buttonCommand=self.choose_root, changeCommand=self.save_root)
        row = cmds.formLayout(parent=settings_column, height=BUTTON_HEIGHT)
        refresh = cmds.button(parent=row, label="刷新资源", command=self.refresh)
        reload_button = cmds.button(parent=row, label="重载工具", command=self.reload)
        self.equal_columns(row, [refresh, reload_button])
        # GN stays visible while the remaining tools scroll.
        gn = self.section(root, *config.GROUPS[0], prominent=True)
        scroll = cmds.scrollLayout(parent=root, childResizable=True)
        self.body = cmds.columnLayout(parent=scroll, adjustableColumn=True, rowSpacing=8)
        self.render_body()
        self.status = cmds.text(parent=root, label="就绪", align="left", wordWrap=True, height=40)
        cmds.formLayout(root, edit=True,
                        attachForm=[(header, "top", 8), (header, "left", 12), (header, "right", 12),
                                    (gn, "left", 12), (gn, "right", 12),
                                    (scroll, "left", 12), (scroll, "right", 12),
                                    (self.status, "left", 12), (self.status, "right", 12),
                                    (self.status, "bottom", 8)],
                        attachControl=[(gn, "top", GAP, header), (scroll, "top", 8, gn),
                                       (scroll, "bottom", 8, self.status)])
        self.refresh()
        cmds.showWindow(window)
        return window

    def render_body(self):
        for child in cmds.columnLayout(self.body, query=True, childArray=True) or []:
            cmds.deleteUI(child)
        pinned = {tool.key for tool in config.PROJECT_GROUP[1]} | {tool.key for tool in config.GROUPS[0][1]}
        self.buttons = {key: button for key, button in self.buttons.items() if key in pinned}
        for title, tools in config.visible_groups(self.vray_mode)[1:]:
            self.section(self.body, title, tools)

    def switch_renderer(self, value, *_):
        self.vray_mode = bool(value)
        self.render_body()
        self.refresh()

    @staticmethod
    def equal_columns(row, controls, columns=None):
        """Percentage attachments keep every button in the row equally wide."""
        positions = []
        edges = []
        count = columns or len(controls)
        for index, control in enumerate(controls):
            edges.extend([(control, "top", 0), (control, "bottom", 0)])
            positions.extend([(control, "left", 0 if index == 0 else GAP // 2, index * 100 // count),
                              (control, "right", 0 if index == count - 1 else GAP // 2, (index + 1) * 100 // count)])
        cmds.formLayout(row, edit=True, attachForm=edges, attachPosition=positions)

    def section(self, parent, title, tools, prominent=False):
        frame = cmds.frameLayout(parent=parent, label=title, collapsable=not prominent,
                                 marginWidth=GAP, marginHeight=GAP)
        column = cmds.columnLayout(parent=frame, adjustableColumn=True, rowSpacing=GAP)
        if title == "素材" and not self.vray_mode:
            row = cmds.formLayout(parent=column, height=BUTTON_HEIGHT)
            self.eye_color = cmds.optionMenu(parent=row, label="眼球颜色")
            for label, value in eyes.COLORS:
                cmds.menuItem(parent=self.eye_color, label=label)
            self.eye_resolution = cmds.optionMenu(parent=row, label="眼球贴图精度")
            for value in eyes.RESOLUTIONS:
                cmds.menuItem(parent=self.eye_resolution, label=value)
            cmds.optionMenu(self.eye_resolution, edit=True, value="2k")
            self.equal_columns(row, [self.eye_color, self.eye_resolution])
        mh_tools = [tool for tool in tools if tool.key.startswith("mh_")]
        tools = [tool for tool in tools if not tool.key.startswith("mh_")]
        columns = config.GROUP_COLUMNS.get(title, 2)
        for start in range(0, len(tools), columns):
            row = cmds.formLayout(parent=column, height=BUTTON_HEIGHT)
            controls = []
            for tool in tools[start:start + columns]:
                options = {"backgroundColor": ACCENT} if prominent else {}
                button = cmds.button(parent=row, label=tool.label, annotation=tool.help,
                                     command=partial(self.run, tool.key), **options)
                self.buttons[tool.key] = button
                controls.append(button)
            self.equal_columns(row, controls, columns if len(tools) > columns else len(controls))
        if title == "素材" and not self.vray_mode:
            cmds.button(parent=column, label="将上方设置应用到所选 Arnold 眼球", height=BUTTON_HEIGHT,
                        command=self.apply_eye_settings)
            cmds.text(parent=column, align="left", wordWrap=True, height=34,
                      label="眼球设置只影响 Arnold 眼球，共用材质的眼球会一起更新。\n"
                            "VFace 素材目录在 VFace 浏览器窗口里选择。")
        if mh_tools:
            cmds.separator(parent=column, style="in", height=8)
            cmds.text(parent=column, label="MetaHuman", align="left", height=20)
            self.mh_reference = cmds.optionMenu(parent=column, label="配件 / 编号参考")
            cmds.menuItem(parent=self.mh_reference, label="女 Female")
            cmds.menuItem(parent=self.mh_reference, label="男 Male")
            for start in range(0, len(mh_tools), 2):
                row = cmds.formLayout(parent=column, height=BUTTON_HEIGHT)
                controls = []
                for tool in mh_tools[start:start + 2]:
                    button = cmds.button(parent=row, label=tool.label, annotation=tool.help,
                                         command=partial(self.run, tool.key))
                    self.buttons[tool.key] = button
                    controls.append(button)
                self.equal_columns(row, controls)
            cmds.text(parent=column, label="观察贴图再次点击还原；切 UV 请选头部网格，再次点击恢复。",
                      align="left", wordWrap=True, height=26)
        if title == "目标与生长体":
            self.delete_blend_source = cmds.checkBox(
                parent=column, label="BS切换后删除新形状模型", value=True, height=22)
            cmds.text(parent=column, align="left", wordWrap=True, height=34,
                      label="BS 不再要求 MetaHuman 命名：同时选中新形状和被修改模型即可，\n"
                            "或先用“BS先点我”标记新形状。两者拓扑必须完全一致。")
        return frame

    def delete_source_enabled(self):
        if self.delete_blend_source and cmds.checkBox(self.delete_blend_source, exists=True):
            return bool(cmds.checkBox(self.delete_blend_source, query=True, value=True))
        return True

    def eye_settings(self):
        color = dict(eyes.COLORS)[cmds.optionMenu(self.eye_color, query=True, value=True)]
        resolution = cmds.optionMenu(self.eye_resolution, query=True, value=True)
        return color, resolution

    def apply_eye_settings(self, *_):
        if self.busy:
            return
        self.busy = True
        try:
            result = self.guarded(lambda: eyes.apply(*self.eye_settings()))
            if result:
                self.message(result)
        finally:
            self.busy = False

    def message(self, text, error=False):
        if self.status and cmds.text(self.status, exists=True):
            cmds.text(self.status, edit=True, label=text)
        if error:
            cmds.warning(text)
        else:
            print("[Yuejun Toolbox] " + text)

    def guarded(self, action):
        try:
            return action()
        except (core.ToolError, project.ProjectError, gn.GnError, ValueError, OSError) as error:
            self.message(str(error), error=True)
        except Exception as error:
            _LOG.exception("Yuejun Toolbox operation failed")
            self.message("操作失败：{}。详细信息见 Script Editor。".format(error), error=True)
        return None

    def choose_root(self, *_):
        def choose():
            folders = cmds.fileDialog2(fileMode=3, dialogStyle=2, caption="选择工具箱资源根目录")
            if folders:
                config.set_resource_root(folders[0])
                self.refresh()
        return self.guarded(choose)

    def save_root(self, *_):
        def save():
            config.set_resource_root(cmds.textFieldButtonGrp(self.path_field, query=True, text=True))
            self.refresh()
        return self.guarded(save)

    def refresh(self, *_):
        def update():
            cmds.textFieldButtonGrp(self.path_field, edit=True, text=config.resource_root())
            missing = []
            for key, button in self.buttons.items():
                available, hint = core.availability(config.TOOLS[key])
                cmds.button(button, edit=True, enable=available, annotation=hint)
                if not available:
                    missing.append(config.TOOLS[key].label)
            self.message("缺少资源，相关按钮已禁用：" + "、".join(missing) if missing else
                         "资源检查通过。GN / 渲染器依赖在执行时检查。")
        return self.guarded(update)

    def run(self, key, *_):
        if self.busy:
            return
        if key == "vface_browser":
            from . import vface_ui
            return self.guarded(vface_ui.show)
        if key == "expression_notes":
            from . import notes
            return self.guarded(notes.show)
        if key == "project_window":
            return self.guarded(lambda: mel.eval("projectWindow;"))
        if key == "set_project":
            return self.guarded(self.set_project)
        if key == "check_project":
            return self.guarded(self.check_project)
        if key == "gn_check":
            return self.guarded(self.check_gn)
        if key == "gn_install":
            if self.busy:
                return
            self.busy = True
            try:
                result = self.guarded(self.install_gn)
                if result:
                    self.message(result)
            finally:
                self.busy = False
            return
        if config.TOOLS[key].kind == "legacy_mel":
            self.busy = True
            def schedule():
                cmds.evalDeferred(partial(self.run_deferred_legacy, key))
                return True
            if not self.guarded(schedule):
                self.busy = False
            return
        self.busy = True
        try:
            if config.TOOLS[key].kind in ("open", "import", "legacy_import", "copy"):
                self.message("正在同步到当前项目，首次复制大贴图可能需要一些时间…")
                cmds.refresh()
            if key == "import_eye_arnold":
                action = lambda _: eyes.import_eye(*self.eye_settings())
            elif config.TOOLS[key].kind == "mh_fit":
                sex = "Male" if cmds.optionMenu(self.mh_reference, query=True, select=True) == 2 else "Female"
                action = partial(core.execute, sex=sex)
            elif key == "blend_target":
                action = partial(core.execute, delete_source=self.delete_source_enabled())
            else:
                action = self.open_preset if config.TOOLS[key].kind == "open" else core.execute
            result = self.guarded(partial(action, key))
            if result:
                self.message(result)
        finally:
            self.busy = False

    def run_deferred_legacy(self, key):
        try:
            # A queued callback from a closed/reloaded window must not edit a scene.
            if _instance is not self or not cmds.window(WINDOW, exists=True):
                return
            result = self.guarded(partial(core.execute, key))
            if result:
                self.message(result)
        finally:
            self.busy = False

    def open_preset(self, key):
        tool = config.TOOLS[key]
        # Resolve prerequisites before asking the user to save or discard anything.
        core.require_renderer(core.require_file(tool.path))
        discard = False
        if core.scene_modified():
            choice = cmds.confirmDialog(
                title="打开场景预设", message="打开预设将替换当前场景。是否保存当前修改？",
                button=["保存并打开", "不保存并打开", "取消"],
                defaultButton="保存并打开", cancelButton="取消", dismissString="取消")
            if choice == "取消":
                return "已取消打开预设。"
            if choice == "保存并打开":
                if cmds.file(query=True, sceneName=True):
                    core.save_scene()
                else:
                    paths = cmds.fileDialog2(fileMode=0, dialogStyle=2, caption="保存当前场景",
                                             fileFilter="Maya ASCII (*.ma);;Maya Binary (*.mb)")
                    if not paths:
                        return "已取消保存，未打开预设。"
                    core.save_scene(paths[0])
            elif choice == "不保存并打开":
                discard = True
            else:
                return "已取消打开预设。"
        return core.open_scene_preset(tool.path, discard_changes=discard)

    def set_project(self):
        mel.eval('setProject "";')
        if preview.STATE.active:
            try:
                project.require_project()
            except project.ProjectError:
                return self.message("仍处于预览模式：尚未设置有效项目。")
            result = preview.promote()
            self.message("已设置项目。" + (result or "") + "现在可将场景保存在项目内。")
        else:
            self.message("当前项目：" + project.root_directory())

    def report_window(self, name, title, report):
        if cmds.window(name, exists=True):
            cmds.deleteUI(name)
        window = cmds.window(name, title=title, widthHeight=(780, 500))
        layout = cmds.formLayout(parent=window)
        field = cmds.scrollField(parent=layout, text=report, editable=False, wordWrap=False)
        cmds.formLayout(layout, edit=True, attachForm=[(field, edge, 10) for edge in ("top", "left", "right", "bottom")])
        cmds.showWindow(window)
        print(report)
        return report

    def check_project(self):
        return self.report_window("yuejunProjectReport", "当前 Maya 项目检查", project.audit())

    def check_gn(self):
        return self.report_window("yuejunGnReport", "GN 插件安装检查", gn.status())

    def install_gn(self):
        root = gn.package_root()
        targets = gn.zbrush_plugin_dirs()
        message = "将安装 GN v{}：\n\nMaya：{}\nZBrush：{}\n\n会覆盖同名的 GN 文件，并在 userSetup.mel 追加自启动（原文件先备份）。".format(
            gn.package_version(root), gn.maya_scripts_dir(),
            "、".join(targets) if targets else "未找到，将跳过")
        if cmds.confirmDialog(title="安装 GN 插件", message=message, button=["安装", "取消"],
                              defaultButton="安装", cancelButton="取消",
                              dismissString="取消") != "安装":
            return "已取消安装。"
        self.message("正在复制 GN 插件文件…")
        cmds.refresh()
        result = gn.install()
        self.report_window("yuejunGnReport", "GN 插件安装检查", result + "\n\n" + gn.status())
        return result

    def reload(self, *_):
        def reload_now():
            from . import reload_toolbox
            return reload_toolbox()
        return self.guarded(reload_now)


def close():
    global _instance
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW, window=True)
    _instance = None
    from . import notes, vface_ui
    notes.close()
    vface_ui.close()
    if cmds.window("yuejunProjectReport", exists=True):
        cmds.deleteUI("yuejunProjectReport")
    if cmds.window("yuejunGnReport", exists=True):
        cmds.deleteUI("yuejunGnReport")


def show():
    global _instance
    close()
    _instance = ToolboxWindow()
    try:
        return _instance.build()
    except Exception as error:
        close()
        _LOG.exception("Unable to create Yuejun Toolbox")
        cmds.warning("工具箱界面创建失败：{}".format(error))
        return None
