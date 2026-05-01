import os
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from core.config_manager import ConfigManager
from core.db_manager import DBManager
from model.directory_tree_model import DirectoryTreeModel
from model.file_table_model import FileTableModel
from ui.upload_task import UploadTask
from ui.settings_dialog import SettingsDialog
from ui.directory_tree import DirTreeView
from ui.file_table import FileTableView
from ui.file_icon import FileIconView
from ui.upload_dialog import UploadQueueDialog

# ---------- 下载任务 ----------
class DownloadTask(QRunnable):
    class Signals(QObject):
        finished = Signal(str)
        error = Signal(str)
    def __init__(self, token, file_id, save_path):
        super().__init__()
        self.token = token
        self.file_id = file_id
        self.save_path = save_path
        self.signals = self.Signals()
    def run(self):
        try:
            import asyncio, aiohttp
            from telegram import Bot
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            async def _download():
                bot = Bot(token=self.token)
                async with bot:
                    file = await bot.get_file(self.file_id)
                    url = file.file_path
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url) as resp:
                            with open(self.save_path, 'wb') as f:
                                while True:
                                    chunk = await resp.content.read(8192)
                                    if not chunk: break
                                    f.write(chunk)
            loop.run_until_complete(_download())
            self.signals.finished.emit(self.save_path)
        except Exception as e:
            self.signals.error.emit(str(e))

# ---------- 删除任务 ----------
class DeleteMessageTask(QRunnable):
    class Signals(QObject):
        finished = Signal()
        error = Signal(str)
    def __init__(self, token, chat_id, message_id):
        super().__init__()
        self.token = token
        self.chat_id = chat_id
        self.message_id = message_id
        self.signals = self.Signals()
    def run(self):
        try:
            from telegram import Bot
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            async def _delete():
                bot = Bot(token=self.token)
                async with bot:
                    await bot.delete_message(chat_id=self.chat_id, message_id=self.message_id)
            loop.run_until_complete(_delete())
            self.signals.finished.emit()
        except Exception as e:
            self.signals.error.emit(str(e))

# ========== 主窗口 ==========
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.db = DBManager()
        self.threadpool = QThreadPool()
        self.upload_counter = 0
        self.current_dir_id = 0
        self.dir_stack = [0]
        self.icon_provider = QFileIconProvider()

        self.setWindowTitle("Telegram 文件管家 Pro")
        self.resize(1000, 650)
        self.setAcceptDrops(True)
        self._setup_ui()
        self._load_current_directory()
        self._update_breadcrumb()

    def _setup_ui(self):
        menubar = self.menuBar()
        settings_menu = menubar.addMenu("设置")
        settings_menu.addAction("全局设置", self.open_settings)

        view_menu = menubar.addMenu("视图")
        self.list_action = view_menu.addAction("列表")
        self.icon_action = view_menu.addAction("图标")
        self.list_action.triggered.connect(lambda: self.switch_view(0))
        self.icon_action.triggered.connect(lambda: self.switch_view(1))

        self.status_label = QLabel("未选择 Bot")
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

        # 面包屑
        nav_layout = QHBoxLayout()
        self.up_btn = QPushButton("⬆️ 向上")
        self.up_btn.clicked.connect(self.go_up)
        nav_layout.addWidget(self.up_btn)

        # 面包屑容器 - 直接创建固定布局
        self.breadcrumb_widget = QWidget()
        self.breadcrumb_layout = QHBoxLayout(self.breadcrumb_widget)  # 布局直接挂在 widget 上
        self.breadcrumb_layout.setContentsMargins(0, 0, 0, 0)
        self.breadcrumb_layout.setSpacing(2)
        self.breadcrumb_layout.setAlignment(Qt.AlignLeft)
        nav_layout.addWidget(self.breadcrumb_widget, 1)

        right_layout.addLayout(nav_layout)

        # 视图栈
        self.view_stack = QStackedWidget()

        # 列表视图
        self.file_table = FileTableView()
        self.file_model = FileTableModel()
        self.file_table.setModel(self.file_model)
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.file_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_table.customContextMenuRequested.connect(self.table_context_menu)
        self.file_table.doubleClicked.connect(self.on_item_double_clicked)
        self.file_table.move_file_callback = self.on_file_moved_to_dir
        self.file_table.setColumnWidth(0, 300)
        self.file_table.setColumnWidth(1, 100)
        self.file_table.setColumnWidth(2, 150)
        self.view_stack.addWidget(self.file_table)

        # 图标视图
        self.icon_view = FileIconView()
        self.icon_view.setViewMode(QListView.IconMode)
        self.icon_view.setIconSize(QSize(48, 48))
        self.icon_view.setGridSize(QSize(120, 100))
        self.icon_view.setResizeMode(QListView.Adjust)
        self.icon_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.icon_view.customContextMenuRequested.connect(self.icon_context_menu)
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

    # ===== 视图切换 =====
    def switch_view(self, index):
        self.view_stack.setCurrentIndex(index)
        self._load_current_directory()

    # ===== 目录加载 =====
    def _load_current_directory(self):
        items = self.db.get_items_in_directory(self.current_dir_id)
        self.file_model.load_items(items)
        self.icon_view.clear()
        style = QApplication.style()
        for item in items:
            is_dir = item[2]
            name = item[1] if is_dir else (item[5] or item[4])
            if is_dir:
                icon = style.standardIcon(QStyle.StandardPixmap.SP_DirIcon)
            else:
                icon = self._get_system_icon(name)
            list_item = QListWidgetItem(icon, name)
            size_str = ""
            if not is_dir and item[6]:
                try:
                    s = float(item[6])
                    for u in ['B','KB','MB','GB']:
                        if s < 1024:
                            size_str = f"{s:.1f} {u}"
                            break
                        s /= 1024
                except: pass
            type_str = "文件夹" if is_dir else (item[8] or "")
            list_item.setToolTip(f"名称: {name}\n大小: {size_str}\n类型: {type_str}")
            list_item.setData(Qt.UserRole, (item[0], is_dir))
            self.icon_view.addItem(list_item)

    def _get_system_icon(self, filename):
        if not filename:
            return QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        suffix = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        temp_path = f"temp.{suffix}" if suffix else "temp"
        icon = self.icon_provider.icon(QFileInfo(temp_path))
        if icon.isNull():
            return QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        return icon

    def go_up(self):
        if len(self.dir_stack) <= 1:  # 栈中只有根目录
            return
        parent_id = self.dir_stack[-2]
        self.set_current_directory(parent_id)

    def set_current_directory(self, dir_id):
        """跳转到指定目录，并更新栈与界面"""
        path = self.db.get_path_to_directory(dir_id)
        self.dir_stack = [item[0] for item in path]  # 用完整路径 id 列表替换栈
        self.current_dir_id = dir_id
        self._load_current_directory()
        self._update_breadcrumb()

    def _update_breadcrumb(self):
        """根据当前路径重新构建面包屑（仅清空控件，保留布局）"""
        layout = self.breadcrumb_layout

        # 清空布局中所有控件（保留 Spacer 等，后面会统一清理）
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # 重新添加面包屑项
        path = self.db.get_path_to_directory(self.current_dir_id)
        for i, (dir_id, name) in enumerate(path):
            if i > 0:  # 分隔符
                sep = QLabel(">")
                sep.setStyleSheet("color: #888;")
                layout.addWidget(sep)

            btn = QPushButton(name)
            btn.setFlat(True)
            btn.setCursor(Qt.PointingHandCursor)
            if dir_id == self.current_dir_id:
                btn.setStyleSheet(
                    "font-weight: bold; color: #fff; border: none; background: transparent; padding: 2px 6px;")
            else:
                btn.setStyleSheet("color: #ccc; border: none; background: transparent; padding: 2px 6px;")
            # 点击跳转
            btn.clicked.connect(lambda checked, d=dir_id: self.set_current_directory(d))
            layout.addWidget(btn)

        layout.addStretch()
        self.up_btn.setEnabled(self.current_dir_id != 0)

    def on_dir_clicked(self, index):
        dir_id = index.data(Qt.UserRole)
        self.set_current_directory(dir_id)

    def on_item_double_clicked(self, index):
        item = self.file_model.get_item(index.row())
        if item and item[2] == 1:
            self.set_current_directory(item[0])

    def icon_double_clicked(self, idx):
        item = self.icon_view.currentItem()
        if item:
            data = item.data(Qt.UserRole)
            if data and data[1] == 1:
                self.set_current_directory(data[0])

    # ===== 批量上传 =====
    def start_bulk_upload(self, file_paths):
        if not self._check_current_bot(): return
        if not file_paths: return
        bot = self.config.get_current_bot()
        token = bot["token"]
        chat_id = bot["chat_id"]

        upload_list = []
        for fp in file_paths:
            uid = f"upload_{self.upload_counter}"
            self.upload_counter += 1
            upload_list.append((fp, uid))

        dialog = UploadQueueDialog(upload_list, self)
        for fp, uid in upload_list:
            task = UploadTask(token, chat_id, fp, self.config.config, uid)
            task.signals.progress.connect(dialog.task_started)
            task.signals.finished.connect(self.on_bulk_upload_finished)
            task.signals.error.connect(self.on_bulk_upload_error)
            task.signals.finished.connect(dialog.task_finished)
            task.signals.error.connect(dialog.task_error)
            self.threadpool.start(task)
            dialog.task_started(uid)
        dialog.exec()

    def on_bulk_upload_finished(self, upload_id, file_id, msg_id, original_name, file_size):
        bot = self.config.get_current_bot()
        ext = os.path.splitext(original_name)[1].lower()
        self.db.add_file(file_id, msg_id, bot["chat_id"], original_name, original_name,
                         self.current_dir_id, file_size, ext)
        self._load_current_directory()
        self.show_status_message(f"上传成功: {original_name}")

    def on_bulk_upload_error(self, upload_id, error_msg):
        self.show_status_message(f"上传失败: {error_msg}", error=True)

    # ===== 右键菜单 =====
    def table_context_menu(self, pos):
        menu = QMenu()
        menu.addAction("📤 上传文件", self.upload_files)
        menu.addAction("📁 上传文件夹", self.upload_folder)
        menu.addAction("📁 新建目录", self.create_directory)
        idx = self.file_table.indexAt(pos)
        if idx.isValid():
            item = self.file_model.get_item(idx.row())
            if item and item[2] == 0:
                menu.addSeparator()
                menu.addAction("⬇️ 下载", lambda: self.download_file(idx))
                menu.addAction("✏️ 重命名", lambda: self.rename_file_from_table(idx))
                menu.addAction("📂 移动到...", lambda: self.move_file_from_table(idx))
                menu.addAction("🗑 删除", lambda: self.delete_files([idx]))
                menu.addAction("📋 属性", lambda: self.show_file_properties(idx))
            elif item and item[2] == 1:
                menu.addSeparator()
                menu.addAction("✏️ 重命名", lambda: self.rename_directory_from_table(idx))
                menu.addAction("🗑 删除目录", lambda: self.delete_directory(idx))
        menu.exec(self.file_table.viewport().mapToGlobal(pos))

    def icon_context_menu(self, pos):
        menu = QMenu()
        menu.addAction("📤 上传文件", self.upload_files)
        menu.addAction("📁 上传文件夹", self.upload_folder)
        menu.addAction("📁 新建目录", self.create_directory)
        item = self.icon_view.itemAt(pos)
        if item:
            data = item.data(Qt.UserRole)
            if data and data[1] == 0:
                menu.addSeparator()
                menu.addAction("⬇️ 下载", lambda: self.download_icon_file(item))
                menu.addAction("✏️ 重命名", lambda: self.rename_file_from_icon(item))
                menu.addAction("📂 移动到...", lambda: self.move_file_from_icon(item))
                menu.addAction("🗑 删除", lambda: self.delete_icon_files([item]))
                menu.addAction("📋 属性", lambda: self.show_icon_properties(item))
            elif data and data[1] == 1:
                menu.addSeparator()
                menu.addAction("✏️ 重命名", lambda: self.rename_directory_from_icon(item))
                menu.addAction("🗑 删除目录", lambda: self.delete_icon_directory(item))
        menu.exec(self.icon_view.viewport().mapToGlobal(pos))

    # ===== 上传文件/文件夹 =====
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
    def rename_file_from_table(self, index):
        item = self.file_model.get_item(index.row())
        if item and item[2] == 0:
            self._rename_file(item[0], item[5] or item[4])

    def rename_file_from_icon(self, list_item):
        data = list_item.data(Qt.UserRole)
        if data and data[1] == 0:
            self._rename_file(data[0], list_item.text())

    def _rename_file(self, local_id, old_name):
        new_name, ok = QInputDialog.getText(self, "重命名", "新名称:", text=old_name)
        if ok and new_name:
            self.db.update_display_name(local_id, new_name)
            self._load_current_directory()

    def rename_directory_from_table(self, index):
        item = self.file_model.get_item(index.row())
        if item and item[2] == 1:
            self._rename_dir(item[0], item[1])

    def rename_directory_from_icon(self, list_item):
        data = list_item.data(Qt.UserRole)
        if data and data[1] == 1:
            self._rename_dir(data[0], list_item.text())

    def _rename_dir(self, dir_id, old_name):
        new_name, ok = QInputDialog.getText(self, "重命名目录", "新名称:", text=old_name)
        if ok and new_name:
            self.db.rename_directory(dir_id, new_name)
            self.dir_model.refresh()
            self._load_current_directory()

    # ===== 移动文件（右键“移动到...”） =====
    def move_file_from_table(self, index):
        item = self.file_model.get_item(index.row())
        if item and item[2] == 0:
            self._move_file_dialog(item[0], item[5] or item[4])

    def move_file_from_icon(self, list_item):
        data = list_item.data(Qt.UserRole)
        if data and data[1] == 0:
            self._move_file_dialog(data[0], list_item.text())

    def _move_file_dialog(self, local_id, file_name):
        # 构建目录列表：包括“根目录”和所有子目录
        dirs = self.db.get_directories()   # 返回所有目录 (id, name)
        items = ["根目录 (ID: 0)"] + [f"{d[1]} (ID: {d[0]})" for d in dirs]
        target, ok = QInputDialog.getItem(self, "移动到", f"选择目标文件夹：\n文件: {file_name}",
                                          items, 0, False)
        if ok and target:
            if target.startswith("根目录"):
                target_dir_id = 0
            else:
                # 从类似 "目录名 (ID: 123)" 中提取ID
                target_dir_id = int(target.split("(ID: ")[-1].rstrip(")"))
            self.db.move_file(local_id, target_dir_id)
            self._load_current_directory()
            self.show_status_message(f"文件已移动到 {target}")

    # ===== 删除（同步 Telegram） =====
    def _delete_file_with_telegram(self, local_id):
        file_info = self.db.get_file_by_id(local_id)
        if not file_info: return
        message_id = file_info[2]
        self.db.delete_file(local_id)
        if message_id is not None:
            bot = self.config.get_current_bot()
            if bot:
                task = DeleteMessageTask(bot["token"], bot["chat_id"], message_id)
                task.signals.error.connect(lambda e: self.show_status_message(f"远程删除失败: {e}", error=True))
                self.threadpool.start(task)

    def delete_files(self, indexes):
        res = QMessageBox.question(self, "确认删除", "确定要删除选中的文件吗？\n（将同步删除 Telegram 中的对应消息）")
        if res == QMessageBox.Yes:
            for idx in indexes:
                item = self.file_model.get_item(idx.row())
                if item and item[2] == 0:
                    self._delete_file_with_telegram(item[0])
            self._load_current_directory()

    def delete_icon_files(self, items):
        res = QMessageBox.question(self, "确认删除", "确定要删除选中的文件吗？\n（将同步删除 Telegram 中的对应消息）")
        if res == QMessageBox.Yes:
            for item in items:
                data = item.data(Qt.UserRole)
                if data and data[1] == 0:
                    self._delete_file_with_telegram(data[0])
            self._load_current_directory()

    # ===== 目录删除 =====
    def delete_directory(self, index):
        item = self.file_model.get_item(index.row())
        if item and item[2] == 1:
            self._delete_dir(item[0], item[1])

    def delete_icon_directory(self, item):
        data = item.data(Qt.UserRole)
        if data and data[1] == 1:
            self._delete_dir(data[0], item.text())

    def _delete_dir(self, dir_id, name):
        confirm = QMessageBox.question(self, "确认删除", f"删除目录 “{name}” 及其内部文件将移至根目录，确认？")
        if confirm == QMessageBox.Yes:
            self.db.delete_directory(dir_id)
            self.dir_model.refresh()
            self._load_current_directory()

    # ===== 下载 =====
    def download_file(self, index):
        item = self.file_model.get_item(index.row())
        if item and item[2] == 0:
            self._start_download(item)

    def download_icon_file(self, list_item):
        data = list_item.data(Qt.UserRole)
        if data and data[1] == 0:
            file_info = self.db.get_file_by_id(data[0])
            self._start_download_from_info(file_info)

    def _start_download(self, item):
        file_info = self.db.get_file_by_id(item[0])
        self._start_download_from_info(file_info)

    def _start_download_from_info(self, file_info):
        if not file_info: return
        file_id = file_info[1]
        default_name = file_info[4] if file_info[4] else "file"
        save_path, _ = QFileDialog.getSaveFileName(self, "保存文件",
                                                   os.path.join(self.config.config.get("download_path", ""), default_name))
        if not save_path: return
        bot = self.config.get_current_bot()
        task = DownloadTask(bot["token"], file_id, save_path)
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
    def show_file_properties(self, index):
        item = self.file_model.get_item(index.row())
        if item and item[2] == 0:
            self._show_properties_dialog(item)

    def show_icon_properties(self, list_item):
        data = list_item.data(Qt.UserRole)
        if data and data[1] == 0:
            file_info = self.db.get_file_by_id(data[0])
            if file_info:
                self._show_properties_from_db(file_info)

    def _show_properties_dialog(self, item):
        file_info = self.db.get_file_by_id(item[0])
        self._show_properties_from_db(file_info)

    def _show_properties_from_db(self, file_info):
        if not file_info: return
        msg = f"""文件名称: {file_info[4] or file_info[5]}
大小: {self._format_size(file_info[7])}
类型: {file_info[8] or '未知'}
上传时间: {file_info[9]}
Telegram File ID: {file_info[1]}
Message ID: {file_info[2]}
Chat ID: {file_info[3]}
本地数据库 ID: {file_info[0]}"""
        QMessageBox.information(self, "文件属性", msg)

    def _format_size(self, size):
        if size is None: return "未知"
        try: size = float(size)
        except: return str(size)
        for unit in ['B','KB','MB','GB']:
            if size < 1024: return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    # ===== 文件移动（拖拽回调） =====
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
            menu.addAction("重命名", lambda: self._rename_dir_from_tree(idx))
            menu.addAction("删除", lambda: self._delete_dir_from_tree(idx))
        menu.exec(self.dir_tree_view.viewport().mapToGlobal(pos))

    def _rename_dir_from_tree(self, idx):
        dir_id = idx.data(Qt.UserRole)
        self._rename_dir(dir_id, idx.data())

    def _delete_dir_from_tree(self, idx):
        dir_id = idx.data(Qt.UserRole)
        self._delete_dir(dir_id, idx.data())

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
        if error:
            self.status_text.setStyleSheet("color: red;")
        else:
            self.status_text.setStyleSheet("color: #ccc;")
        if not progress:
            self.progress_bar.setVisible(False)

    def open_settings(self):
        dlg = SettingsDialog(self.config, self)
        if dlg.exec():
            self._update_status()
            self.dir_model.refresh()

    def _check_current_bot(self):
        bot = self.config.get_current_bot()
        if not bot:
            QMessageBox.warning(self, "提示", "请先在设置中配置并选择 Bot")
            return False
        return True

    def _update_status(self):
        bot = self.config.get_current_bot()
        if bot:
            self.status_label.setText(f"当前 Bot: {bot['name']}")
        else:
            self.status_label.setText("未选择 Bot")