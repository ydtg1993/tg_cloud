import os
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from core.config_manager import ConfigManager
from core.db_manager import DBManager
from model.directory_tree_model import DirectoryTreeModel
from model.file_table_model import FileTableModel
from ui.breadcrumb import BreadcrumbNavigator
from ui.upload_task import UploadTask
from ui.settings_dialog import SettingsDialog
from ui.directory_tree import DirTreeView
from ui.file_table import FileTableView
from ui.file_icon import FileIconView
from ui.upload_dialog import UploadQueueDialog
from ui.file_operations import FileOperationHandler
from core.tasks import DownloadTask, DeleteMessageTask
from ui.search_dialog import SearchResultDialog
from ui.date_range_picker import DateRangePickerDialog
from ui.icon_manager import IconManager
from core.utils import format_file_size

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.db = DBManager()
        self.threadpool = QThreadPool()
        self.upload_counter = 0
        self.current_dir_id = 0
        self.dir_stack = [0]
        self.setWindowTitle("Telegram 文件管家 Pro")
        self.resize(1000, 650)
        self.setAcceptDrops(True)
        self._setup_ui()
        self._load_current_directory()
        self.breadcrumb.update(0)
        self.up_btn.setEnabled(False)

    def _setup_ui(self):
        menubar = self.menuBar()
        settings_menu = menubar.addMenu("设置")
        settings_menu.addAction("全局设置", self.open_settings)

        view_menu = menubar.addMenu("视图")
        self.list_action = view_menu.addAction("列表")
        self.icon_action = view_menu.addAction("图标")
        self.list_action.triggered.connect(lambda: self.switch_view(0))
        self.icon_action.triggered.connect(lambda: self.switch_view(1))

        self.status_label = QLabel("Pyrogram 未登录")
        self.statusBar().addPermanentWidget(self.status_label)
        self._update_status()

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # 左侧目录树
        self.dir_tree_view = DirTreeView(self.db)
        self.dir_tree_view.file_moved_callback = self.on_file_moved_to_dir
        self.dir_model = DirectoryTreeModel(self.db)
        self.dir_tree_view.setModel(self.dir_model)
        self.dir_tree_view.setMaximumWidth(250)
        self.dir_tree_view.clicked.connect(self.on_dir_clicked)
        self.dir_tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.dir_tree_view.customContextMenuRequested.connect(self.dir_context_menu)
        main_layout.addWidget(self.dir_tree_view)

        right_layout = QVBoxLayout()

        # 搜索栏
        search_widget = QWidget()
        search_layout = QHBoxLayout(search_widget)
        search_layout.setContentsMargins(0, 0, 0, 8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索文件名...")
        self.search_input.returnPressed.connect(self._search_by_filename)
        self.search_btn = QPushButton("🔍 搜索")
        self.search_btn.clicked.connect(self._search_by_filename)
        self.date_search_btn = QPushButton("📅 按时间搜索")
        self.date_search_btn.clicked.connect(self._show_date_range_picker)
        self.search_input.setObjectName("search_input")
        self.search_btn.setObjectName("search_btn")
        self.date_search_btn.setObjectName("date_search_btn")
        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.search_btn)
        search_layout.addWidget(self.date_search_btn)
        right_layout.addWidget(search_widget)

        # 面包屑
        nav_layout = QHBoxLayout()
        self.up_btn = QPushButton("⬆️ 向上")
        self.up_btn.clicked.connect(self.go_up)
        nav_layout.addWidget(self.up_btn)
        self.breadcrumb_widget = QWidget()
        self.breadcrumb_layout = QHBoxLayout(self.breadcrumb_widget)
        self.breadcrumb_layout.setContentsMargins(0, 0, 0, 0)
        self.breadcrumb_layout.setSpacing(2)
        self.breadcrumb_layout.setAlignment(Qt.AlignLeft)
        nav_layout.addWidget(self.breadcrumb_widget, 1)
        right_layout.addLayout(nav_layout)
        self.breadcrumb = BreadcrumbNavigator(self.breadcrumb_layout, self.db, self.set_current_directory)

        # 视图栈
        self.view_stack = QStackedWidget()
        self.file_model = FileTableModel()
        self.file_table = FileTableView()
        self.file_table.setModel(self.file_model)
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.file_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_table.doubleClicked.connect(self.on_item_double_clicked)
        self.file_table.move_file_callback = self.on_file_moved_to_dir
        self.file_table.setColumnWidth(0, 300)
        self.file_table.setColumnWidth(1, 100)
        self.file_table.setColumnWidth(2, 150)
        self.view_stack.addWidget(self.file_table)

        self.icon_view = FileIconView()
        self.icon_view.setViewMode(QListView.IconMode)
        self.icon_view.setIconSize(QSize(48, 48))
        self.icon_view.setGridSize(QSize(120, 100))
        self.icon_view.setResizeMode(QListView.Adjust)
        self.icon_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.icon_view.doubleClicked.connect(self.icon_double_clicked)
        self.icon_view.move_file_callback = self.on_file_moved_to_dir
        self.view_stack.addWidget(self.icon_view)

        self.view_stack.setCurrentIndex(0)
        right_layout.addWidget(self.view_stack)

        # 底部状态
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_text = QLabel("就绪")
        status_layout.addWidget(self.progress_bar, 3)
        status_layout.addWidget(self.status_text, 1)
        right_layout.addWidget(status_widget)

        main_layout.addLayout(right_layout, 3)

        # 初始化 FileOperationHandler (解耦)
        self.file_ops = FileOperationHandler(
            db=self.db,
            task_manager=None,  # 暂未使用
            get_selected_file_ids_callback=self._get_selected_file_ids,
            refresh_callback=self._load_current_directory,
            show_status_callback=self.show_status_message,
            start_download_callback=self._start_download_from_info,
            rename_file_callback=self._rename_file,
            move_file_callback=self._move_file_dialog,
            delete_file_callback=self._delete_files,
            show_properties_callback=self._show_properties_from_db,
            create_directory_callback=self.create_directory,
            upload_files_callback=self.upload_files,
            upload_folder_callback=self.upload_folder,
            rename_directory_callback=self._rename_dir,
            delete_directory_callback=self._delete_dir
        )
        self.file_table.customContextMenuRequested.connect(
            lambda pos: self.file_ops.build_table_context_menu(
                pos, self.file_table, self.file_model, self.file_table.selectionModel().selectedRows()
            )
        )
        self.icon_view.customContextMenuRequested.connect(
            lambda pos: self.file_ops.build_icon_context_menu(
                pos, self.icon_view, self.icon_view.selectedItems()
            )
        )

    # ---------- 辅助方法 ----------
    def _get_selected_file_ids(self):
        if self.view_stack.currentIndex() == 0:
            indexes = self.file_table.selectionModel().selectedRows()
            ids = []
            for idx in indexes:
                item = self.file_model.get_item(idx.row())
                if item and item.is_dir == 0:
                    ids.append(item.id)
            return ids
        else:
            items = self.icon_view.selectedItems()
            ids = []
            for it in items:
                data = it.data(Qt.UserRole)
                if data and data[1] == 0:
                    ids.append(data[0])
            return ids

    def _delete_files(self, file_ids):
        res = QMessageBox.question(self, "确认删除",
                                   f"确定要删除这 {len(file_ids)} 个文件吗？\n（将同步删除 Telegram 中的对应消息）")
        if res == QMessageBox.Yes:
            for fid in file_ids:
                self._delete_file_with_telegram(fid)
            self._load_current_directory()

    def switch_view(self, index):
        self.view_stack.setCurrentIndex(index)
        self._load_current_directory()

    def _load_current_directory(self):
        items = self.db.get_items_in_directory(self.current_dir_id)
        self.file_model.load_items(items)
        self.icon_view.clear()
        for item in items:
            name = item.name if item.is_dir else (item.display_name or item.original_name)
            icon = IconManager.get_icon(name) if not item.is_dir else QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
            list_item = QListWidgetItem(icon, name)
            size_str = format_file_size(item.file_size) if not item.is_dir else ""
            type_str = "文件夹" if item.is_dir else (item.mime_type or "")
            list_item.setToolTip(f"名称: {name}\n大小: {size_str}\n类型: {type_str}")
            list_item.setData(Qt.UserRole, (item.id, item.is_dir))
            self.icon_view.addItem(list_item)

    def go_up(self):
        if len(self.dir_stack) <= 1:
            return
        parent_id = self.dir_stack[-2]
        self.set_current_directory(parent_id)

    def set_current_directory(self, dir_id):
        path = self.db.get_path_to_directory(dir_id)
        self.dir_stack = [item[0] for item in path]
        self.current_dir_id = dir_id
        self._load_current_directory()
        self.breadcrumb.update(dir_id)
        self.up_btn.setEnabled(dir_id != 0)

    def on_dir_clicked(self, index):
        dir_id = index.data(Qt.UserRole)
        self.set_current_directory(dir_id)

    def on_item_double_clicked(self, index):
        item = self.file_model.get_item(index.row())
        if item and item.is_dir == 1:
            self.set_current_directory(item.id)

    def icon_double_clicked(self, idx):
        item = self.icon_view.currentItem()
        if item:
            data = item.data(Qt.UserRole)
            if data and data[1] == 1:
                self.set_current_directory(data[0])

    # ===== 批量上传 =====
    def start_bulk_upload(self, file_paths):
        pyro = self._get_pyro_config()
        chat_id = self._get_chat_id()
        if not pyro or not chat_id:
            self.show_status_message("请先在设置中完成Pyrogram登录并填写目标 Chat ID", error=True)
            return
        upload_list = []
        for fp in file_paths:
            uid = f"upload_{self.upload_counter}"
            self.upload_counter += 1
            upload_list.append((fp, uid))
        dialog = UploadQueueDialog(upload_list, self)
        for fp, uid in upload_list:
            task = UploadTask(pyro["session"], pyro["api_id"], pyro["api_hash"], chat_id, fp, uid)
            task.signals.finished.connect(self.on_bulk_upload_finished)
            task.signals.error.connect(self.on_bulk_upload_error)
            task.signals.finished.connect(dialog.task_finished)
            task.signals.error.connect(dialog.task_error)
            self.threadpool.start(task)
            dialog.task_started(uid)
        dialog.exec()

    def on_bulk_upload_finished(self, upload_id, file_id, msg_id, original_name, file_size):
        chat_id = self._get_chat_id()
        ext = os.path.splitext(original_name)[1].lower()
        self.db.add_file(file_id, msg_id, chat_id, original_name, original_name,
                         self.current_dir_id, file_size, ext)
        self._load_current_directory()
        self.show_status_message(f"上传成功: {original_name}")

    def on_bulk_upload_error(self, upload_id, error_msg):
        self.show_status_message(f"上传失败: {error_msg}", error=True)

    def upload_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选择文件")
        if paths:
            self.start_bulk_upload(paths)

    def upload_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            all_files = []
            for root, dirs, files in os.walk(folder):
                for f in files:
                    all_files.append(os.path.join(root, f))
            if all_files:
                self.start_bulk_upload(all_files)

    # ===== 重命名 =====
    def _rename_file(self, local_id, old_name):
        new_name, ok = QInputDialog.getText(self, "重命名", "新名称:", text=old_name)
        if ok and new_name:
            self.db.update_display_name(local_id, new_name)
            self._load_current_directory()

    def _rename_dir(self, dir_id, old_name):
        new_name, ok = QInputDialog.getText(self, "重命名目录", "新名称:", text=old_name)
        if ok and new_name:
            self.db.rename_directory(dir_id, new_name)
            self.dir_model.refresh()
            self._load_current_directory()

    # ===== 移动文件 =====
    def _move_file_dialog(self, local_id, file_name):
        dirs = self.db.get_directories()
        items = ["根目录 (ID: 0)"] + [f"{d[1]} (ID: {d[0]})" for d in dirs]
        target, ok = QInputDialog.getItem(self, "移动到", f"选择目标文件夹：\n文件: {file_name}",
                                          items, 0, False)
        if ok and target:
            if target.startswith("根目录"):
                target_dir_id = 0
            else:
                target_dir_id = int(target.split("(ID: ")[-1].rstrip(")"))
            self.db.move_file(local_id, target_dir_id)
            self._load_current_directory()
            self.show_status_message(f"文件已移动到 {target}")

    # ===== 删除 =====
    def _delete_file_with_telegram(self, local_id):
        file_info = self.db.get_file_by_id(local_id)
        if not file_info: return
        message_id = file_info[2]
        chat_id = file_info[3]
        self.db.delete_file(local_id)
        if message_id is not None:
            pyro = self._get_pyro_config()
            if pyro:
                task = DeleteMessageTask(pyro["session"], pyro["api_id"], pyro["api_hash"], chat_id, message_id)
                task.signals.error.connect(lambda e: self.show_status_message(f"远程删除失败: {e}", error=True))
                self.threadpool.start(task)

    def _delete_dir(self, dir_id, name):
        files = self.db.get_all_files_recursive(dir_id)
        count = len(files)
        msg = f"确定要删除目录 “{name}” 吗？\n将递归删除 {count} 个文件及其子目录，且无法恢复。"
        if count > 0:
            msg += "\n（将同步删除 Telegram 中的对应消息）"
        confirm = QMessageBox.question(self, "确认删除", msg)
        if confirm == QMessageBox.Yes:
            if files:
                pyro = self._get_pyro_config()
                if pyro:
                    for fid, msg_id, chat_id in files:
                        if msg_id is not None:
                            task = DeleteMessageTask(pyro["session"], pyro["api_id"], pyro["api_hash"], chat_id, msg_id)
                            task.signals.error.connect(lambda e: self.show_status_message(f"远程删除失败: {e}", error=True))
                            self.threadpool.start(task)
            self.db.delete_directory_recursive(dir_id)
            self.dir_model.refresh()
            self._load_current_directory()
            self.show_status_message(f"目录 “{name}” 已删除")

    # ===== 下载 =====
    def _start_download_from_info(self, file_info):
        if not file_info: return
        file_id = file_info[1]
        default_name = file_info[4] or file_info[5] or "file"
        save_path, _ = QFileDialog.getSaveFileName(
            self, "保存文件",
            os.path.join(self.config.config.get("download_path", ""), default_name)
        )
        if not save_path: return
        pyro = self._get_pyro_config()
        if not pyro:
            self.show_status_message("请先完成Pyrogram登录", error=True)
            return
        task = DownloadTask(pyro["session"], pyro["api_id"], pyro["api_hash"], file_id, save_path)
        task.signals.finished.connect(lambda p: self.show_status_message(f"下载完成: {p}"))
        task.signals.error.connect(lambda e: self.show_status_message(f"下载失败: {e}", error=True))
        self.show_status_message("下载中...", progress=True)
        self.threadpool.start(task)

    # ===== 新建目录 =====
    def create_directory(self):
        name, ok = QInputDialog.getText(self, "新建目录", "目录名:")
        if ok and name:
            self.db.add_directory(name, self.current_dir_id)
            self.dir_model.refresh()
            self._load_current_directory()

    # ===== 属性 =====
    def _show_properties_from_db(self, file_info):
        if not file_info: return
        msg = f"""文件名称: {file_info[4] or file_info[5]}
大小: {format_file_size(file_info[7])}
类型: {file_info[8] or '未知'}
上传时间: {file_info[9]}
Telegram File ID: {file_info[1]}
Message ID: {file_info[2]}
Chat ID: {file_info[3]}
本地数据库 ID: {file_info[0]}"""
        QMessageBox.information(self, "文件属性", msg)

    # ===== 拖拽回调 =====
    def on_file_moved_to_dir(self, file_local_id, target_dir_id):
        self.db.move_file(file_local_id, target_dir_id)
        self._load_current_directory()
        self.show_status_message("文件已移动")

    # ===== 目录树右键 =====
    def dir_context_menu(self, pos):
        menu = QMenu()
        menu.addAction("新建根目录", lambda: self.create_directory())
        idx = self.dir_tree_view.indexAt(pos)
        if idx.isValid():
            dir_id = idx.data(Qt.UserRole)
            dir_name = idx.data()
            menu.addAction("重命名", lambda: self._rename_dir(dir_id, dir_name))
            menu.addAction("删除", lambda: self._delete_dir(dir_id, dir_name))
        menu.exec(self.dir_tree_view.viewport().mapToGlobal(pos))

    # ===== 拖拽外部文件 =====
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("QMainWindow { border: 2px solid #4d6e9f; }")

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")

    def dropEvent(self, event):
        self.setStyleSheet("")
        paths = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for f in files:
                        paths.append(os.path.join(root, f))
            elif os.path.isfile(path):
                paths.append(path)
        if paths:
            self.start_bulk_upload(paths)

    # ===== 状态 & 设置 =====
    def show_status_message(self, msg, error=False, progress=False):
        self.status_text.setText(msg)
        self.progress_bar.setVisible(progress)
        self.status_text.setStyleSheet("color: red;" if error else "color: #ccc;")
        if not progress:
            self.progress_bar.setVisible(False)

    def open_settings(self):
        dlg = SettingsDialog(self.config, self)
        if dlg.exec():
            self._update_status()
            self.dir_model.refresh()

    def _update_status(self):
        pyro = self.config.config.get("pyrogram", {})
        self.status_label.setText("Pyrogram 已登录" if pyro.get("session_string") else "Pyrogram 未登录")

    def _get_pyro_config(self):
        pyro = self.config.config.get("pyrogram", {})
        session = pyro.get("session_string")
        api_id = pyro.get("api_id")
        api_hash = pyro.get("api_hash")
        if not all([session, api_id, api_hash]):
            return None
        return {"session": session, "api_id": api_id, "api_hash": api_hash}

    def _get_chat_id(self):
        chat_id = self.config.config.get("pyrogram", {}).get("chat_id", "")
        try:
            return int(chat_id)
        except:
            return None

    # ===== 搜索 =====
    def _search_by_filename(self):
        keyword = self.search_input.text().strip()
        if not keyword:
            QMessageBox.information(self, "提示", "请输入搜索关键字")
            return
        self.show_status_message(f"正在搜索: {keyword}...")
        try:
            results = self.db.search_files_by_name(keyword)
            self._show_search_results(results, f"文件名: {keyword}")
        except Exception as e:
            self.show_status_message(f"搜索失败: {str(e)}", error=True)
            QMessageBox.warning(self, "搜索失败", str(e))
        finally:
            self.show_status_message("就绪")

    def _show_date_range_picker(self):
        picker = DateRangePickerDialog(self)
        picker.date_range_selected.connect(self._search_by_date_range)
        picker.exec()

    def _search_by_date_range(self, start_date, end_date):
        self.show_status_message(f"正在搜索 {start_date} 至 {end_date} 的文件...")
        try:
            results = self.db.search_files_by_date_range(start_date, end_date)
            self._show_search_results(results, f"时间段: {start_date} 至 {end_date}")
        except Exception as e:
            self.show_status_message(f"搜索失败: {str(e)}", error=True)
            QMessageBox.warning(self, "搜索失败", str(e))
        finally:
            self.show_status_message("就绪")

    def _show_search_results(self, results, search_type):
        if not results:
            QMessageBox.information(self, "搜索结果", f"未找到匹配的文件\n({search_type})")
            return
        dialog = SearchResultDialog(results, search_type, self)
        dialog.file_selected.connect(self._navigate_to_file)
        dialog.exec()

    def _navigate_to_file(self, file_id, dir_id):
        self.set_current_directory(dir_id)
        QTimer.singleShot(100, lambda: self._select_file_in_current_view(file_id))

    def _select_file_in_current_view(self, file_id):
        if self.view_stack.currentIndex() == 0:
            for row in range(self.file_model.rowCount()):
                item = self.file_model.get_item(row)
                if item and item.id == file_id and item.is_dir == 0:
                    index = self.file_model.index(row, 0)
                    self.file_table.setCurrentIndex(index)
                    self.file_table.scrollTo(index)
                    self.file_table.selectionModel().select(index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
                    break
        else:
            for i in range(self.icon_view.count()):
                item = self.icon_view.item(i)
                data = item.data(Qt.UserRole)
                if data and data[0] == file_id and data[1] == 0:
                    self.icon_view.setCurrentItem(item)
                    self.icon_view.scrollToItem(item)
                    break