# -*- coding: utf-8 -*-
"""Read/copy-only reference UI, separate from the note catalogue and scene logic."""
from maya import cmds
from . import notes_data

WINDOW = 'yuejunExpressionNotes'
_instance = None


class NotesWindow(object):
    def build(self):
        window = cmds.window(WINDOW, title='XGen 表达式速查', widthHeight=(900, 620), sizeable=True)
        root = cmds.formLayout(parent=window)
        self.search_field = cmds.textField(parent=root, placeholderText='搜索名称或用途…',
                                           height=28, changeCommand=self.filter)
        self.list = cmds.textScrollList(parent=root, allowMultiSelection=False,
                                        selectCommand=self.select)
        detail = cmds.formLayout(parent=root)
        self.title = cmds.text(parent=detail, label='', align='left', font='boldLabelFont', height=26)
        self.usage = cmds.scrollField(parent=detail, editable=False, wordWrap=True)
        hint = cmds.text(parent=detail, label='代码可临时修改；复制当前内容后，粘贴到对应的表达式栏。',
                         align='left', height=24)
        self.code = cmds.scrollField(parent=detail, editable=True, wordWrap=False, font='fixedWidthFont')
        buttons = cmds.formLayout(parent=detail, height=34)
        copy = cmds.button(parent=buttons, label='复制代码', command=self.copy,
                           backgroundColor=(0.23, 0.39, 0.43))
        reset = cmds.button(parent=buttons, label='恢复此条原文', command=self.select)
        cmds.formLayout(buttons, edit=True,
                        attachForm=[(copy, 'left', 0), (reset, 'right', 0)] +
                                   [(b, edge, 0) for b in (copy, reset) for edge in ('top', 'bottom')],
                        attachPosition=[(copy, 'right', 4, 50), (reset, 'left', 4, 50)])
        self.status = cmds.text(parent=detail, label='只查看和复制，不会自动修改场景。', align='left', height=24)
        cmds.formLayout(detail, edit=True,
                        attachForm=[(c, edge, 0) for c in (self.title, self.usage, hint, self.code, buttons, self.status)
                                    for edge in ('left', 'right')] + [(self.title, 'top', 0), (self.status, 'bottom', 0)],
                        attachPosition=[(self.usage, 'bottom', 0, 37)],
                        attachControl=[(self.usage, 'top', 8, self.title), (hint, 'top', 8, self.usage),
                                       (self.code, 'top', 8, hint), (self.code, 'bottom', 8, buttons),
                                       (buttons, 'bottom', 8, self.status)])
        cmds.formLayout(root, edit=True,
                        attachForm=[(self.search_field, 'left', 12), (self.search_field, 'top', 12),
                                    (self.list, 'left', 12), (self.list, 'bottom', 12),
                                    (detail, 'top', 12), (detail, 'right', 12), (detail, 'bottom', 12)],
                        attachPosition=[(self.search_field, 'right', 4, 30), (self.list, 'right', 4, 30)],
                        attachControl=[(self.list, 'top', 8, self.search_field), (detail, 'left', 8, self.list)])
        self.filter()
        cmds.showWindow(window)
        return window

    def filter(self, *_):
        self.items = notes_data.search(cmds.textField(self.search_field, query=True, text=True))
        cmds.textScrollList(self.list, edit=True, removeAll=True)
        if self.items:
            cmds.textScrollList(self.list, edit=True, append=[item['title'] for item in self.items], selectIndexedItem=1)
        self.select()

    def select(self, *_):
        selected = cmds.textScrollList(self.list, query=True, selectIndexedItem=True) or []
        item = self.items[selected[0] - 1] if selected else None
        cmds.text(self.title, edit=True, label=(item['title'] + '  |  ' + item['language']) if item else '没有匹配的笔记')
        cmds.scrollField(self.usage, edit=True, text=item['usage'] if item else '请修改搜索关键词。')
        cmds.scrollField(self.code, edit=True, text=item['code'] if item else '')
        cmds.text(self.status, edit=True, label='临时修改不会保存；切换条目会恢复原文。')

    def copy(self, *_):
        text = cmds.scrollField(self.code, query=True, text=True)
        if not text.strip():
            cmds.text(self.status, edit=True, label='没有可复制的代码。')
            return
        try:
            from PySide2.QtWidgets import QApplication
            app = QApplication.instance()
            if app is None:
                raise RuntimeError('Maya 界面尚未初始化')
            app.clipboard().setText(text)
            cmds.text(self.status, edit=True, label='已复制代码。请粘贴到对应位置；工具未执行代码。')
        except Exception as error:
            cmds.warning('无法访问剪贴板：{}。可在代码框中全选并按 Ctrl+C。'.format(error))


def close():
    global _instance
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW, window=True)
    _instance = None


def show():
    global _instance
    close()
    _instance = NotesWindow()
    try:
        return _instance.build()
    except Exception:
        close()
        raise
