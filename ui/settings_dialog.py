import asyncio
from PySide6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QDialogButtonBox,
    QFileDialog, QMessageBox, QInputDialog, QApplication
)
from PySide6.QtCore import Qt
from core.config_manager import ConfigManager
from core.pyro_login import login_pyrogram, finish_login

class SettingsDialog(QDialog):
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.config = config_manager.config
        self.setWindowTitle("应用设置")
        self.resize(500, 350)

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # ========== Pyrogram 选项卡 ==========
        self.pyro_tab = QWidget()
        pyro_layout = QFormLayout(self.pyro_tab)

        self.api_id_edit = QLineEdit()
        self.api_hash_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("+8613800000000 国际格式")
        self.chat_id_edit = QLineEdit()          # 新增：目标 Chat ID
        self.chat_id_edit.setPlaceholderText("例如：-1001234567890")
        self.pyro_status = QLabel("未登录")
        self.pyro_status.setStyleSheet("color: orange; font-weight: bold;")

        pyro_layout.addRow("API ID:", self.api_id_edit)
        pyro_layout.addRow("API Hash:", self.api_hash_edit)
        pyro_layout.addRow("手机号 (含国家码):", self.phone_edit)
        pyro_layout.addRow("目标 Chat ID:", self.chat_id_edit)
        pyro_layout.addRow("状态:", self.pyro_status)

        self.login_btn = QPushButton("🔑 登录 Pyrogram")
        pyro_layout.addRow(self.login_btn)

        self.tabs.addTab(self.pyro_tab, "Pyrogram")

        # ========== 常规选项卡 ==========
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
        self.tabs.addTab(self.general_tab, "常规")

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_and_close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._connect_signals()
        self._load_to_ui()

    def _load_to_ui(self):
        pyro = self.config.get("pyrogram", {})
        self.api_id_edit.setText(str(pyro.get("api_id", "")))
        self.api_hash_edit.setText(pyro.get("api_hash", ""))
        self.phone_edit.setText(pyro.get("phone", ""))
        self.chat_id_edit.setText(pyro.get("chat_id", ""))
        if pyro.get("session_string"):
            self.pyro_status.setText("已登录 ✅")
            self.pyro_status.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.pyro_status.setText("未登录 ❌")
            self.pyro_status.setStyleSheet("color: orange; font-weight: bold;")

        self.download_path_edit.setText(self.config.get("download_path", ""))
        self.theme_combo.setCurrentText(self.config.get("theme", "dark"))

    def _connect_signals(self):
        self.login_btn.clicked.connect(self._login_pyrogram)

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
                "session_string": session,
                "chat_id": self.chat_id_edit.text().strip()   # 保留已有的 Chat ID
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
        # 保存 Chat ID（即使用户没点登录也要保存）
        self.config.setdefault("pyrogram", {})
        self.config["pyrogram"]["chat_id"] = self.chat_id_edit.text().strip()
        self.config_manager.save()
        self.accept()