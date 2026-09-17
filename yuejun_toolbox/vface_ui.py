# -*- coding: utf-8 -*-
"""VFace library browser; scene operations live in vface.py."""
import logging
from maya import cmds
from . import vface, config

WINDOW = "yuejunVFaceWindow"


class Browser(object):
    def __init__(self):
        self.entries = []
        self.busy = False

    def show(self):
        close()
        window = cmds.window(WINDOW, title="VFace 素材 · Arnold", widthHeight=(520, 285))
        column = cmds.columnLayout(parent=window, adjustableColumn=True, rowSpacing=8,
                                   columnAttach=("both", 12))
        saved = config.vface_root()
        self.path = cmds.textFieldButtonGrp(parent=column, label="素材目录", text=saved,
                                            buttonLabel="选择…", adjustableColumn=2,
                                            columnWidth3=(60, 330, 65), buttonCommand=self.choose)
        cmds.button(parent=column, label="刷新编号列表", height=30, command=self.refresh)
        self.menu = cmds.optionMenu(parent=column, label="头部编号")
        self.button = cmds.button(parent=column, label="切换头部与贴图", height=36, command=self.apply)
        cmds.text(parent=column, align="left", wordWrap=True,
                  label="先打开配套 Arnold 预设。共用 ID 遮罩、灯光及采样设置保留。\n同步切换眼睛、泪线、眉毛和睫毛；带历史或 XGen 连接的模型不会替换。\n撤销可恢复上一次切换；已导入的隐藏网格缓存会保留。")
        self.status = cmds.text(parent=column, label="请选择 VFace 总目录或单个编号目录。",
                                align="left", wordWrap=True)
        cmds.showWindow(window)
        if saved:
            self.refresh()
        else:
            cmds.button(self.button, edit=True, enable=False)
        return window

    def guarded(self, action):
        try:
            return action()
        except Exception as error:
            logging.getLogger("yuejun_toolbox").exception("VFace operation failed")
            cmds.text(self.status, edit=True, label=str(error))
            cmds.warning(str(error))

    def choose(self, *_):
        folders = cmds.fileDialog2(fileMode=3, caption="选择 VFace 素材目录", dialogStyle=2)
        if folders:
            cmds.textFieldButtonGrp(self.path, edit=True, text=folders[0])
            self.refresh()

    def refresh(self, *_):
        if self.busy:
            return
        self.entries = []
        for item in cmds.optionMenu(self.menu, query=True, itemListLong=True) or []:
            cmds.deleteUI(item)
        cmds.button(self.button, edit=True, enable=False)
        def scan():
            root = cmds.textFieldButtonGrp(self.path, query=True, text=True).strip()
            self.entries = vface.discover(root)
            for label, folder in self.entries:
                cmds.menuItem(parent=self.menu, label=label)
            config.set_vface_root(root)
            cmds.button(self.button, edit=True, enable=bool(self.entries))
            cmds.text(self.status, edit=True, label="找到 {} 套完整素材（不完整目录不会列出）。".format(len(self.entries)))
        self.guarded(scan)

    def apply(self, *_):
        if self.busy or not self.entries:
            return
        self.busy = True
        cmds.button(self.button, edit=True, enable=False)
        try:
            index = cmds.optionMenu(self.menu, query=True, select=True) - 1
            cmds.text(self.status, edit=True, label="正在同步，首次复制 16K 贴图可能需要一些时间…")
            cmds.refresh()
            result = self.guarded(lambda: vface.apply(self.entries[index][1]))
            if result:
                cmds.text(self.status, edit=True, label=result)
        finally:
            self.busy = False
            cmds.button(self.button, edit=True, enable=True)


def close():
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)


def show():
    return Browser().show()
