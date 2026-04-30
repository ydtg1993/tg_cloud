import asyncio
from PySide6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QListWidget, QComboBox, QDialogButtonBox,
    QFileDialog, QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt
from core.config_manager import ConfigManager
from core.pyro_login import login_pyrogram, finish_login

class BotDetailDialog(QDialog):
    def __init__(self, parent, title, bot=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(350, 200)
        layout = QFormLayout(self)
        self.name_edit = QLineEdit()
        self.token_edit = QLineEdit()
        self.chat_id_edit = QLineEdit()
        self.desc_edit = QLineEdit()
        layout.addRow("名称:", self.name_edit)
        layout.addRow("Token:", self.token_edit)
        layout.addRow("Chat ID:", self.chat_id_edit)
        layout.addRow("备注:", self.desc_edit)
        if bot:
            self.name_edit.setText(bot.get("name", ""))
            self.token_edit.setText(bot.get("token", ""))
            self.chat_id_edit.setText(str(bot.get("chat_id", "")))
            self.desc_edit.setText(bot.get("description", ""))
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def values(self):
        return (
            self.name_edit.text().strip(),
            self.token_edit.text().strip(),
            self.chat_id_edit.text().strip(),
            self.desc_edit.text().strip()
        )

class SettingsDialog(QDialog):
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.config = config_manager.config
        self.setWindowTitle("应用设置")
        self.resize(650, 450)

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # --- Bot 管理 ---
        self.bot_tab = QWidget()
        bot_layout = QVBoxLayout(self.bot_tab)
        bot_layout.addWidget(QLabel("已配置的 Bot（右侧按钮操作）："))
        self.bot_list = QListWidget()
        self.bot_list.setAlternatingRowColors(True)
        bot_layout.addWidget(self.bot_list)
        btn_group = QHBoxLayout()
        self.add_btn = QPushButton("➕ 添加")
        self.edit_btn = QPushButton("✏️ 编辑")
        self.remove_btn = QPushButton("🗑 删除")
        self.set_current_btn = QPushButton("✅ 设为当前")
        btn_group.addWidget(self.add_btn)
        btn_group.addWidget(self.edit_btn)
        btn_group.addWidget(self.remove_btn)
        btn_group.addWidget(self.set_current_btn)
        bot_layout.addLayout(btn_group)
        self.tabs.addTab(self.bot_tab, "Bot 管理")

        # --- Pyrogram ---
        self.pyro_tab = QWidget()
        pyro_layout = QFormLayout(self.pyro_tab)
        self.api_id_edit = QLineEdit()
        self.api_hash_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        self.pyro_status = QLabel("未登录")
        self.pyro_status.setStyleSheet("color: orange; font-weight: bold;")
        pyro_layout.addRow("API ID:", self.api_id_edit)
        pyro_layout.addRow("API Hash:", self.api_hash_edit)
        pyro_layout.addRow("手机号 (含国家码):", self.phone_edit)
        pyro_layout.addRow("状态:", self.pyro_status)
        self.login_btn = QPushButton("🔑 登录 Pyrogram")
        pyro_layout.addRow(self.login_btn)
        self.tabs.addTab(self.pyro_tab, "Pyrogram")

        # --- 常规 ---
        self.general_tab = QWidget()
        general_layout = QFormLayout(self.general_tab)
        self.download_path_edit = QLineEdit()
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.select_download_path)
        dl_layout = QHBoxLayout()
        dl_layout.addWidget(self.download_path_edit)
        dl_layout.addWidget(browse_btn)
        general_layout.addRow("默认下载路径:", dl_layout)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        general_layout.addRow("主题:", self.theme_combo)
        self.clipboard_check = QComboBox()
        self.clipboard_check.addItems(["开启", "关闭"])
        general_layout.addRow("剪贴板监听:", self.clipboard_check)
        self.tabs.addTab(self.general_tab, "常规")

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_and_close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._connect_signals()
        self._load_to_ui()

    def _load_to_ui(self):
        self.bot_list.clear()
        for key, bot in self.config.get("bots", {}).items():
            item_text = f"{bot['name']} ({key})"
            self.bot_list.addItem(item_text)
            if key == self.config.get("current_bot"):
                # 高亮但不用 currentItem，直接设置最后添加的项
                self.bot_list.item(self.bot_list.count()-1).setText(item_text + " ★")

        pyro = self.config.get("pyrogram", {})
        self.api_id_edit.setText(str(pyro.get("api_id", "")))
        self.api_hash_edit.setText(pyro.get("api_hash", ""))
        self.phone_edit.setText(pyro.get("phone", ""))
        if pyro.get("session_string"):
            self.pyro_status.setText("已登录 ✅")
            self.pyro_status.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.pyro_status.setText("未登录 ❌")
            self.pyro_status.setStyleSheet("color: orange; font-weight: bold;")

        self.download_path_edit.setText(self.config.get("download_path", ""))
        self.theme_combo.setCurrentText(self.config.get("theme", "dark"))
        self.clipboard_check.setCurrentText("开启" if self.config.get("clipboard_enabled", True) else "关闭")

    def _connect_signals(self):
        self.add_btn.clicked.connect(self._add_bot)
        self.edit_btn.clicked.connect(self._edit_bot)
        self.remove_btn.clicked.connect(self._remove_bot)
        self.set_current_btn.clicked.connect(self._set_current)
        self.login_btn.clicked.connect(self._login_pyrogram)

    def _add_bot(self):
        dialog = BotDetailDialog(self, "添加 Bot")
        if dialog.exec():
            name, token, chat_id, desc = dialog.values()
            if not all([name, token, chat_id]):
                QMessageBox.warning(self, "提示", "名称、Token 和 Chat ID 为必填项")
                return
            key = f"bot_{len(self.config['bots']) + 1:03d}"
            self.config["bots"][key] = {
                "name": name,
                "token": token,
                "chat_id": int(chat_id),
                "description": desc
            }
            self.config_manager.save()
            self._load_to_ui()

    def _edit_bot(self):
        row = self.bot_list.currentRow()
        if row < 0:
            return
        key = list(self.config["bots"].keys())[row]
        bot = self.config["bots"][key]
        dialog = BotDetailDialog(self, "编辑 Bot", bot)
        if dialog.exec():
            name, token, chat_id, desc = dialog.values()
            if not all([name, token, chat_id]):
                QMessageBox.warning(self, "提示", "名称、Token 和 Chat ID 为必填项")
                return
            self.config["bots"][key] = {
                "name": name,
                "token": token,
                "chat_id": int(chat_id),
                "description": desc
            }
            self.config_manager.save()
            self._load_to_ui()

    def _remove_bot(self):
        row = self.bot_list.currentRow()
        if row < 0:
            return
        key = list(self.config["bots"].keys())[row]
        name = self.config["bots"][key]["name"]
        if QMessageBox.question(self, "确认删除", f"确定删除 Bot “{name}”吗？") == QMessageBox.Yes:
            del self.config["bots"][key]
            if self.config["current_bot"] == key:
                self.config["current_bot"] = ""
            self.config_manager.save()
            self._load_to_ui()

    def _set_current(self):
        row = self.bot_list.currentRow()
        if row < 0:
            return
        key = list(self.config["bots"].keys())[row]
        self.config["current_bot"] = key
        self.config_manager.save()
        self._load_to_ui()
        QMessageBox.information(self, "提示", f"当前 Bot 已切换为: {self.config['bots'][key]['name']}")

    def _login_pyrogram(self):
        api_id = self.api_id_edit.text().strip()
        api_hash = self.api_hash_edit.text().strip()
        phone = self.phone_edit.text().strip()
        if not (api_id and api_hash and phone):
            QMessageBox.warning(self, "提示", "请填写完整的 Pyrogram 登录信息")
            return
        try:
            api_id_int = int(api_id)
        except ValueError:
            QMessageBox.warning(self, "提示", "API ID 必须是整数")
            return

        self.login_btn.setEnabled(False)
        self.pyro_status.setText("正在连接...")
        self.pyro_status.setStyleSheet("color: blue; font-weight: bold;")
        QApplication.processEvents()

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            client, phone_code_hash = loop.run_until_complete(
                login_pyrogram(api_id_int, api_hash, phone)
            )
            # 主线程弹出验证码输入框（安全）
            code, ok = QInputDialog.getText(self, "验证码", "请输入 Telegram 验证码:")
            if not ok or not code:
                loop.run_until_complete(client.disconnect())
                raise Exception("取消登录")

            session = loop.run_until_complete(
                finish_login(client, phone, phone_code_hash, code)
            )
            self.config["pyrogram"] = {
                "api_id": api_id_int,
                "api_hash": api_hash,
                "phone": phone,
                "session_string": session
            }
            self.config_manager.save()
            self.pyro_status.setText("已登录 ✅")
            self.pyro_status.setStyleSheet("color: green; font-weight: bold;")
        except Exception as e:
            self.pyro_status.setText(f"登录失败: {str(e)}")
            self.pyro_status.setStyleSheet("color: red; font-weight: bold;")
        finally:
            self.login_btn.setEnabled(True)

    def select_download_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择下载目录")
        if path:
            self.download_path_edit.setText(path)

    def save_and_close(self):
        self.config["download_path"] = self.download_path_edit.text()
        self.config["theme"] = self.theme_combo.currentText()
        self.config["clipboard_enabled"] = self.clipboard_check.currentText() == "开启"
        self.config_manager.save()
        self.accept()