from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu, QMessageBox, QInputDialog
from core.tasks import DeleteMessageTask, DownloadTask

class FileOperationHandler:
    def __init__(self, main_window):
        self.mw = main_window

    # ---------- 右键菜单构建 ----------
    def build_table_context_menu(self, pos):
        menu = QMenu()
        menu.addAction("📤 上传文件", self.mw.upload_files)
        menu.addAction("📁 上传文件夹", self.mw.upload_folder)
        menu.addAction("📁 新建目录", self.mw.create_directory)

        table = self.mw.file_table
        idx = table.indexAt(pos)
        if idx.isValid():
            item = self.mw.file_model.get_item(idx.row())
            if item and item[2] == 1:  # 目录
                menu.addSeparator()
                menu.addAction("✏️ 重命名", lambda: self.mw.rename_directory_from_table(idx))
                menu.addAction("🗑 删除目录", lambda: self.mw.delete_directory_recursive(idx))

        indexes = table.selectionModel().selectedRows()
        file_ids = self._get_selected_file_ids_from_table(indexes)

        if file_ids:
            menu.addSeparator()
            if len(file_ids) == 1:
                fid = file_ids[0]
                menu.addAction("⬇️ 下载", lambda: self.single_download(fid))
                menu.addAction("✏️ 重命名", lambda: self.single_rename(fid))
                menu.addAction("📂 移动到...", lambda: self.single_move(fid))
                menu.addAction("🗑 删除", lambda: self.delete_files(file_ids))
                menu.addAction("📋 属性", lambda: self.single_properties(fid))
            else:
                menu.addAction("📥 批量下载", lambda: self.batch_download(file_ids))
                menu.addAction("📂 批量移动到...", lambda: self.batch_move(file_ids))
                menu.addAction("🗑 批量删除", lambda: self.delete_files(file_ids))
        menu.exec(table.viewport().mapToGlobal(pos))

    def build_icon_context_menu(self, pos):
        menu = QMenu()
        menu.addAction("📤 上传文件", self.mw.upload_files)
        menu.addAction("📁 上传文件夹", self.mw.upload_folder)
        menu.addAction("📁 新建目录", self.mw.create_directory)

        icon_view = self.mw.icon_view
        item = icon_view.itemAt(pos)
        if item:
            data = item.data(Qt.UserRole)
            if data and data[1] == 1:  # 目录
                menu.addSeparator()
                menu.addAction("✏️ 重命名", lambda: self.mw.rename_directory_from_icon(item))
                menu.addAction("🗑 删除目录", lambda: self.mw.delete_icon_directory(item))

        selected_items = icon_view.selectedItems()
        file_ids = self._get_selected_file_ids_from_icon(selected_items)

        if file_ids:
            menu.addSeparator()
            if len(file_ids) == 1:
                fid = file_ids[0]
                menu.addAction("⬇️ 下载", lambda: self.single_download(fid))
                menu.addAction("✏️ 重命名", lambda: self.single_rename(fid))
                menu.addAction("📂 移动到...", lambda: self.single_move(fid))
                menu.addAction("🗑 删除", lambda: self.delete_files(file_ids))
                menu.addAction("📋 属性", lambda: self.single_properties(fid))
            else:
                menu.addAction("📥 批量下载", lambda: self.batch_download(file_ids))
                menu.addAction("📂 批量移动到...", lambda: self.batch_move(file_ids))
                menu.addAction("🗑 批量删除", lambda: self.delete_files(file_ids))
        menu.exec(icon_view.viewport().mapToGlobal(pos))

    # ---------- 辅助方法 ----------
    def _get_selected_file_ids_from_table(self, indexes):
        file_ids = []
        for idx in indexes:
            item = self.mw.file_model.get_item(idx.row())
            if item and item[2] == 0:
                file_ids.append(item[0])
        return file_ids

    def _get_selected_file_ids_from_icon(self, items):
        file_ids = []
        for item in items:
            data = item.data(Qt.UserRole)
            if data and data[1] == 0:
                file_ids.append(data[0])
        return file_ids

    # ---------- 单文件操作 ----------
    def single_download(self, file_id):
        self.mw._start_download_from_info(self.mw.db.get_file_by_id(file_id))

    def single_rename(self, file_id):
        info = self.mw.db.get_file_by_id(file_id)
        if info:
            self.mw._rename_file(file_id, info[4] or info[5])

    def single_move(self, file_id):
        info = self.mw.db.get_file_by_id(file_id)
        if info:
            self.mw._move_file_dialog(file_id, info[4] or info[5])

    def single_properties(self, file_id):
        info = self.mw.db.get_file_by_id(file_id)
        if info:
            self.mw._show_properties_from_db(info)

    # ---------- 批量操作 ----------
    def delete_files(self, file_ids):
        res = QMessageBox.question(self.mw, "确认删除",
                                   f"确定要删除这 {len(file_ids)} 个文件吗？\n（将同步删除 Telegram 中的对应消息）")
        if res == QMessageBox.Yes:
            for fid in file_ids:
                self.mw._delete_file_with_telegram(fid)
            self.mw._load_current_directory()

    def batch_download(self, file_ids):
        for fid in file_ids:
            info = self.mw.db.get_file_by_id(fid)
            self.mw._start_download_from_info(info)

    def batch_move(self, file_ids):
        dirs = self.mw.db.get_directories()
        items = ["根目录 (ID: 0)"] + [f"{d[1]} (ID: {d[0]})" for d in dirs]
        target, ok = QInputDialog.getItem(self.mw, "批量移动到",
                                          f"为 {len(file_ids)} 个文件选择目标文件夹：",
                                          items, 0, False)
        if ok and target:
            if target.startswith("根目录"):
                target_dir_id = 0
            else:
                target_dir_id = int(target.split("(ID: ")[-1].rstrip(")"))
            for fid in file_ids:
                self.mw.db.move_file(fid, target_dir_id)
            self.mw._load_current_directory()
            self.mw.show_status_message(f"{len(file_ids)} 个文件已移动")