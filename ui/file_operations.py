from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu, QMessageBox, QInputDialog

class FileOperationHandler:
    def __init__(self, db, task_manager, get_selected_file_ids_callback,
                 refresh_callback, show_status_callback,
                 start_download_callback, rename_file_callback,
                 move_file_callback, delete_file_callback,
                 show_properties_callback, create_directory_callback,
                 upload_files_callback, upload_folder_callback,
                 rename_directory_callback, delete_directory_callback):
        self.db = db
        self.task_manager = task_manager
        self.get_selected_file_ids = get_selected_file_ids_callback
        self.refresh = refresh_callback
        self.show_status = show_status_callback
        self.start_download = start_download_callback
        self.rename_file = rename_file_callback
        self.move_file = move_file_callback
        self.delete_file = delete_file_callback
        self.show_properties = show_properties_callback
        self.create_directory = create_directory_callback
        self.upload_files = upload_files_callback
        self.upload_folder = upload_folder_callback
        self.rename_directory = rename_directory_callback
        self.delete_directory = delete_directory_callback

    def build_table_context_menu(self, pos, table_view, file_model, selected_indexes):
        menu = QMenu()
        menu.addAction("📤 上传文件", lambda: self.upload_files())
        menu.addAction("📁 上传文件夹", lambda: self.upload_folder())
        menu.addAction("📁 新建目录", lambda: self.create_directory())

        idx = table_view.indexAt(pos)
        if idx.isValid():
            item = file_model.get_item(idx.row())
            if item and item.is_dir == 1:
                menu.addSeparator()
                menu.addAction("✏️ 重命名", lambda: self.rename_directory(item.id, item.name))
                menu.addAction("🗑 删除目录", lambda: self.delete_directory(item.id, item.name))

        file_ids = self.get_selected_file_ids()
        if file_ids:
            menu.addSeparator()
            if len(file_ids) == 1:
                fid = file_ids[0]
                info = self.db.get_file_by_id(fid)
                if info:
                    menu.addAction("⬇️ 下载", lambda: self.start_download(info))
                    menu.addAction("✏️ 重命名", lambda: self.rename_file(fid, info[4] or info[5]))
                    menu.addAction("📂 移动到...", lambda: self.move_file(fid, info[4] or info[5]))
                    menu.addAction("🗑 删除", lambda: self.delete_file(file_ids))
                    menu.addAction("📋 属性", lambda: self.show_properties(info))
            else:
                menu.addAction("📥 批量下载", lambda: self._batch_download(file_ids))
                menu.addAction("📂 批量移动到...", lambda: self._batch_move(file_ids))
                menu.addAction("🗑 批量删除", lambda: self.delete_file(file_ids))
        menu.exec(table_view.viewport().mapToGlobal(pos))

    def build_icon_context_menu(self, pos, icon_view, selected_items):
        menu = QMenu()
        menu.addAction("📤 上传文件", lambda: self.upload_files())
        menu.addAction("📁 上传文件夹", lambda: self.upload_folder())
        menu.addAction("📁 新建目录", lambda: self.create_directory())

        item = icon_view.itemAt(pos)
        if item:
            data = item.data(Qt.UserRole)
            if data and data[1] == 1:
                menu.addSeparator()
                menu.addAction("✏️ 重命名", lambda: self.rename_directory(data[0], item.text()))
                menu.addAction("🗑 删除目录", lambda: self.delete_directory(data[0], item.text()))

        file_ids = []
        for it in selected_items:
            data = it.data(Qt.UserRole)
            if data and data[1] == 0:
                file_ids.append(data[0])

        if file_ids:
            menu.addSeparator()
            if len(file_ids) == 1:
                fid = file_ids[0]
                info = self.db.get_file_by_id(fid)
                if info:
                    menu.addAction("⬇️ 下载", lambda: self.start_download(info))
                    menu.addAction("✏️ 重命名", lambda: self.rename_file(fid, info[4] or info[5]))
                    menu.addAction("📂 移动到...", lambda: self.move_file(fid, info[4] or info[5]))
                    menu.addAction("🗑 删除", lambda: self.delete_file(file_ids))
                    menu.addAction("📋 属性", lambda: self.show_properties(info))
            else:
                menu.addAction("📥 批量下载", lambda: self._batch_download(file_ids))
                menu.addAction("📂 批量移动到...", lambda: self._batch_move(file_ids))
                menu.addAction("🗑 批量删除", lambda: self.delete_file(file_ids))
        menu.exec(icon_view.viewport().mapToGlobal(pos))

    def _batch_download(self, file_ids):
        for fid in file_ids:
            info = self.db.get_file_by_id(fid)
            if info:
                self.start_download(info)

    def _batch_move(self, file_ids):
        dirs = self.db.get_directories()
        items = ["根目录 (ID: 0)"] + [f"{d[1]} (ID: {d[0]})" for d in dirs]
        target, ok = QInputDialog.getItem(None, "批量移动到",
                                          f"为 {len(file_ids)} 个文件选择目标文件夹：",
                                          items, 0, False)
        if ok and target:
            if target.startswith("根目录"):
                target_dir_id = 0
            else:
                target_dir_id = int(target.split("(ID: ")[-1].rstrip(")"))
            for fid in file_ids:
                self.db.move_file(fid, target_dir_id)
            self.refresh()
            self.show_status(f"{len(file_ids)} 个文件已移动")