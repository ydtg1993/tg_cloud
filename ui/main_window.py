import os
import asyncio
import tempfile
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from core.config_manager import ConfigManager
from core.db_manager import DBManager
from ui.directory_tree import DirectoryTreeModel
from ui.file_table_model import FileTableModel
from ui.upload_task import UploadTask, UploadSignals
from ui.settings_dialog import SettingsDialog

# ---------- 下载任务 ----------
class DownloadSignals(QObject):
    finished = Signal(str)   # 保存路径
    error = Signal(str)

class DownloadTask(QRunnable):
    def __init__(self, token, file_id, save_path):
        super().__init__()
        self.token = token
        self.file_id = file_id
        self.save_path = save_path
        self.signals = DownloadSignals()

    def run(self):
        try:
            from telegram import Bot
            import aiohttp
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
                                    if not chunk:
                                        break
                                    f.write(chunk)
            loop.run_until_complete(_download())
            self.signals.finished.emit(self.save_path)
        except Exception as e:
            self.signals.error.emit(str(e))

# ---------- 删除消息任务 ----------
class DeleteMessageSignals(QObject):
    finished = Signal()
    error = Signal(str)

class DeleteMessageTask(QRunnable):
    def __init__(self, token, chat_id, message_id):
        super().__init__()
        self.token = token
        self.chat_id = chat_id
        self.message_id = message_id
        self.signals = DeleteMessageSignals()

    def run(self):
        try:
            from telegram import Bot
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

# ---------- 主窗口 ----------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.db = DBManager()
        self.threadpool = QThreadPool()
        self.temp_id_counter = 0
        self.temp_files = {}          # local_temp_id -> path 用于清理

        self.setWindowTitle("Telegram 文件管家 Pro")
        self.resize(900, 600)
        self.setAcceptDrops(True)

        self._setup_ui()
        self._load_initial_data()
        self._setup_clipboard_monitor()

    def _setup_ui(self):
        menubar = self.menuBar()
        settings_menu = menubar.addMenu("设置")
        settings_menu.addAction("全局设置", self.open_settings)
        self.status_label = QLabel("未选择 Bot")
        self.statusBar().addPermanentWidget(self.status_label)
        self._update_status()

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        self.dir_tree_view = QTreeView()
        self.dir_model = DirectoryTreeModel(self.db)
        self.dir_tree_view.setModel(self.dir_model)
        self.dir_tree_view.clicked.connect(self.on_dir_clicked)
        self.dir_tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.dir_tree_view.customContextMenuRequested.connect(self.dir_tree_menu)
        main_layout.addWidget(self.dir_tree_view, 1)

        right_layout = QVBoxLayout()
        self.file_table = QTableView()
        # 调整模型显示列：id, file_id, message_id, orig_name, disp_name, size, time, mime
        self.file_model = FileTableModel()
        self.file_table.setModel(self.file_model)
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.file_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_table.customContextMenuRequested.connect(self.file_table_menu)
        right_layout.addWidget(self.file_table)

        btn_layout = QHBoxLayout()
        self.upload_btn = QPushButton("📤 上传文件")
        self.upload_btn.clicked.connect(self.upload_files)
        btn_layout.addWidget(self.upload_btn)
        self.new_dir_btn = QPushButton("📁 新建目录")
        self.new_dir_btn.clicked.connect(lambda: self.create_directory(0))
        btn_layout.addWidget(self.new_dir_btn)
        self.paste_btn = QPushButton("📋 上传剪贴板")
        self.paste_btn.clicked.connect(self.upload_clipboard)
        btn_layout.addWidget(self.paste_btn)
        self.progress_bar = QProgressBar()
        right_layout.addLayout(btn_layout)
        right_layout.addWidget(self.progress_bar)
        main_layout.addLayout(right_layout, 3)

    def _load_initial_data(self):
        self.dir_model.refresh()
        self._load_files_from_dir(0)

    def _load_files_from_dir(self, dir_id):
        files = self.db.get_files_in_directory(dir_id)
        self.file_model.load_files(files)  # files 现在包含 message_id 列

    def on_dir_clicked(self, index):
        dir_id = index.data(Qt.UserRole)
        self._load_files_from_dir(dir_id)

    # ---------- 上传 ----------
    def upload_files(self):
        if not self._check_current_bot():
            return
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件")
        for f in files:
            self._schedule_upload(f, is_temp=False)

    def _schedule_upload(self, file_path, is_temp=False):
        bot = self.config.get_current_bot()
        if not bot:
            QMessageBox.warning(self, "提示", "请先配置并选择 Bot")
            return
        token = bot["token"]
        chat_id = bot["chat_id"]
        local_id = f"temp_{self.temp_id_counter}"
        self.temp_id_counter += 1
        task = UploadTask(token, chat_id, file_path, self.config.config, local_id, is_temp)
        task.signals.finished.connect(self.on_upload_finished)
        task.signals.error.connect(self.on_upload_error)
        if is_temp:
            self.temp_files[local_id] = file_path
        self.threadpool.start(task)

    def on_upload_finished(self, local_id, file_id, msg_id, original_name, file_size):
        bot = self.config.get_current_bot()
        self.db.add_file(
            file_id, msg_id, bot["chat_id"], original_name,
            original_name, self._current_dir_id(), file_size, ""
        )
        self._refresh_current_dir()
        self.progress_bar.setValue(100)
        # 清理临时文件
        if local_id in self.temp_files:
            try:
                os.remove(self.temp_files[local_id])
            except Exception:
                pass
            del self.temp_files[local_id]

    def on_upload_error(self, local_id, error_msg):
        QMessageBox.critical(self, "上传失败", f"文件上传出错：{error_msg}")
        self.progress_bar.reset()
        # 清理临时文件
        if local_id in self.temp_files:
            try:
                os.remove(self.temp_files[local_id])
            except Exception:
                pass
            del self.temp_files[local_id]

    def _current_dir_id(self):
        idx = self.dir_tree_view.currentIndex()
        if idx.isValid():
            return idx.data(Qt.UserRole)
        return 0

    # ---------- 右键菜单 ----------
    def file_table_menu(self, pos):
        menu = QMenu()
        rows = self.file_table.selectionModel().selectedRows()
        if not rows:
            return
        if len(rows) == 1:
            menu.addAction("下载", lambda: self.download_file(rows[0]))
            menu.addAction("重命名", lambda: self.rename_file(rows[0]))
            menu.addAction("移动到...", lambda: self.move_file(rows[0]))
            menu.addSeparator()
        menu.addAction("删除", lambda: self.delete_files(rows))
        menu.exec(self.file_table.viewport().mapToGlobal(pos))

    def download_file(self, index):
        local_id = index.data(Qt.UserRole)
        file_info = self.db.get_file_by_id(local_id)
        if not file_info:
            return
        # file_info: (id, file_id, message_id, chat_id, orig_name, disp_name, dir_id, size, mime, upload_time)
        file_id = file_info[1]
        orig_name = file_info[4] or file_info[5] or "file"
        save_path, _ = QFileDialog.getSaveFileName(self, "保存文件",
                                                   os.path.join(self.config.config.get("download_path", ""), orig_name))
        if not save_path:
            return
        bot = self.config.get_current_bot()
        if not bot:
            QMessageBox.warning(self, "提示", "未设置 Bot")
            return
        task = DownloadTask(bot["token"], file_id, save_path)
        task.signals.finished.connect(lambda p: QMessageBox.information(self, "下载完成", f"已保存至：{p}"))
        task.signals.error.connect(lambda e: QMessageBox.critical(self, "下载失败", e))
        self.threadpool.start(task)

    def rename_file(self, index):
        local_id = index.data(Qt.UserRole)
        new_name, ok = QInputDialog.getText(self, "重命名", "新名称:")
        if ok and new_name:
            self.db.update_display_name(local_id, new_name)
            self._refresh_current_dir()

    def move_file(self, index):
        local_id = index.data(Qt.UserRole)
        dirs = self.db.get_directories()
        items = [d[1] for d in dirs]
        item, ok = QInputDialog.getItem(self, "移动到", "选择目录:", items, 0, False)
        if ok:
            for d in dirs:
                if d[1] == item:
                    self.db.move_file(local_id, d[0])
                    self._refresh_current_dir()
                    break

    def delete_files(self, indexes):
        res = QMessageBox.question(self, "确认删除", "确定要删除选中的文件吗？\n（此操作会同时删除 Telegram 上的对应消息）")
        if res != QMessageBox.Yes:
            return
        bot = self.config.get_current_bot()
        if not bot:
            return
        token = bot["token"]
        chat_id = bot["chat_id"]
        for idx in indexes:
            local_id = idx.data(Qt.UserRole)
            file_info = self.db.get_file_by_id(local_id)
            if not file_info:
                continue
            message_id = file_info[2]   # message_id 字段
            # 删除本地数据库记录
            self.db.delete_file(local_id)
            # 如果 message_id 有效，尝试删除 Telegram 消息
            if message_id is not None:
                task = DeleteMessageTask(token, chat_id, message_id)
                task.signals.error.connect(lambda e: print(f"Delete msg error: {e}"))
                self.threadpool.start(task)
        self._refresh_current_dir()

    def dir_tree_menu(self, pos):
        menu = QMenu()
        index = self.dir_tree_view.indexAt(pos)
        if index.isValid():
            menu.addAction("新建子目录", lambda: self.create_directory(index.data(Qt.UserRole)))
            menu.addAction("重命名", lambda: self.rename_directory(index))
            menu.addAction("删除", lambda: self.delete_directory(index))
        else:
            menu.addAction("新建根目录", lambda: self.create_directory(0))
        menu.exec(self.dir_tree_view.viewport().mapToGlobal(pos))

    def rename_directory(self, index):
        dir_id = index.data(Qt.UserRole)
        new_name, ok = QInputDialog.getText(self, "重命名目录", "新名称:")
        if ok and new_name:
            self.db.rename_directory(dir_id, new_name)
            self.dir_model.refresh()

    def delete_directory(self, index):
        dir_id = index.data(Qt.UserRole)
        confirm = QMessageBox.question(self, "确认删除", "删除目录将同时移动内部文件到根目录，确认？")
        if confirm == QMessageBox.Yes:
            self.db.delete_directory(dir_id)
            self.dir_model.refresh()
            self._load_files_from_dir(0)

    def create_directory(self, parent_id=0):
        name, ok = QInputDialog.getText(self, "新建目录", "目录名:")
        if ok and name:
            self.db.add_directory(name, parent_id)
            self.dir_model.refresh()

    # ---------- 拖拽 ----------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                self._schedule_upload(file_path, is_temp=False)

    # ---------- 剪贴板 ----------
    def _setup_clipboard_monitor(self):
        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self.on_clipboard_changed)
        self.last_clipboard_image = None

    def on_clipboard_changed(self):
        if not self.config.config.get("clipboard_enabled", True):
            return
        mime = self.clipboard.mimeData()
        if mime.hasImage():
            image = self.clipboard.image()
            if image.cacheKey() == self.last_clipboard_image:
                return
            self.last_clipboard_image = image.cacheKey()
            reply = QMessageBox.question(self, "剪贴板检测", "检测到截图，是否上传？",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.upload_clipboard_image(image)

    def upload_clipboard(self):
        mime = self.clipboard.mimeData()
        if mime.hasImage():
            self.upload_clipboard_image(self.clipboard.image())

    def upload_clipboard_image(self, image):
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            f.close()
            image.save(f.name)
            self._schedule_upload(f.name, is_temp=True)

    # ---------- 设置 ----------
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

    def _refresh_current_dir(self):
        self._load_files_from_dir(self._current_dir_id())
        self.progress_bar.reset()