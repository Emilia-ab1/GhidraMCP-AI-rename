import sys
import json
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon, QIntValidator
from PyQt6.QtWidgets import (
    QApplication,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QWidget,
    QSpinBox,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QComboBox,
    QInputDialog,
    QMessageBox,
    QDialog,
    QListWidget,
    QDialogButtonBox,
)
import threading
import os

from startup_checker import check_connection_and_count
try:
    from ai_rename import run_rename
except Exception:
    run_rename = None

# 资源路径与配置路径定义
APP_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = getattr(sys, "_MEIPASS", APP_DIR) # PyInstaller临时路径
APP_ICON = os.path.join(BASE_PATH, "res", "logo.ico")

# 方案二：将配置文件保存在用户的AppData目录
APP_NAME = "GhidraAiRename"
APP_DATA_DIR = os.path.join(os.environ['LOCALAPPDATA'], APP_NAME)
os.makedirs(APP_DATA_DIR, exist_ok=True) # 确保目录存在
CONFIG_FILE = os.path.join(APP_DATA_DIR, "api_config.json")


class ConfigManager:
    """API配置(Profile)管理器"""

    def __init__(self, config_file: str = CONFIG_FILE):
        self.config_file = config_file

    def load_config(self) -> dict:
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if "profiles" in config and "last_selected_profile" in config:
                        return config
        except Exception:
            pass
        return {
            "last_selected_profile": "Default",
            "profiles": {
                "Default": {
                    "api_key": "",
                    "api_base": "https://api.siliconflow.cn/",
                    "model_name": "Qwen/Qwen2.5-72B-Instruct",
                    "batch_size": 50,
                    "delay_ms": 1000
                }
            }
        }

    def save_config(self, config: dict) -> None:
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_profile_names(self) -> list[str]:
        config = self.load_config()
        return list(config.get("profiles", {}).keys())

    def get_profile(self, name: str) -> dict | None:
        config = self.load_config()
        return config.get("profiles", {}).get(name)

    def save_profile(self, name: str, api_key: str, api_base: str, model_name: str, batch_size: int, delay_ms: int) -> None:
        if not name or not name.strip():
            return
        config = self.load_config()
        if "profiles" not in config:
            config["profiles"] = {}
        config["profiles"][name] = {
            "api_key": api_key,
            "api_base": api_base,
            "model_name": model_name,
            "batch_size": batch_size,
            "delay_ms": delay_ms
        }
        self.save_config(config)

    def delete_profile(self, name: str) -> bool:
        config = self.load_config()
        if name in config.get("profiles", {}) and len(config["profiles"]) > 1:
            del config["profiles"][name]
            if config.get("last_selected_profile") == name:
                config["last_selected_profile"] = list(config["profiles"].keys())[0]
            self.save_config(config)
            return True
        return False

    def get_last_selected_profile_name(self) -> str:
        config = self.load_config()
        return config.get("last_selected_profile")

    def set_last_selected_profile(self, name: str) -> None:
        config = self.load_config()
        if name in config.get("profiles", {}):
            config["last_selected_profile"] = name
            self.save_config(config)


class ProfileSelectorDialog(QDialog):
    """一个用于选择和管理配置的弹窗"""
    def __init__(self, profiles: list[str], current: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择配置")
        self.setMinimumWidth(350)
        self.resize(350, 220)

        layout = QVBoxLayout(self)
        
        self.list_widget = QListWidget()
        self.list_widget.addItems(profiles)
        if current in profiles:
            items = self.list_widget.findItems(current, Qt.MatchFlag.MatchExactly)
            if items:
                self.list_widget.setCurrentItem(items[0])
        
        self.list_widget.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.list_widget)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("确定")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        layout.addWidget(button_box)
        
        self.selected_profile = None

    def accept(self):
        current_item = self.list_widget.currentItem()
        if current_item:
            self.selected_profile = current_item.text()
        super().accept()

    @staticmethod
    def get_profile(profiles: list[str], current: str, parent=None) -> str | None:
        dialog = ProfileSelectorDialog(profiles, current, parent)
        if dialog.exec():
            return dialog.selected_profile
        return None


class AppleStyle:
    @staticmethod
    def apply(widget: QWidget) -> None:
        app = QApplication.instance()
        if app is None: return
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(245, 245, 247))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Text, QColor(28, 28, 30))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(28, 28, 30))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(28, 28, 30))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 122, 255))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        app.setPalette(palette)
        app.setStyle("Fusion")
        font = QFont()
        font.setFamily("Segoe UI" if sys.platform.startswith("win") else font.family())
        font.setPointSize(10)
        app.setFont(font)
        widget.setStyleSheet(
            """
            QWidget { background-color: #F5F5F7; }
            QGroupBox { border: 1px solid #E5E5EA; border-radius: 8px; margin-top: 12px; padding: 12px; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; color: #1C1C1E; }
            QLabel { color: #1C1C1E; }
            QLineEdit { background: #FFFFFF; border: 1px solid #E5E5EA; border-radius: 8px; padding: 6px 10px; }
            QLineEdit:focus { border: 1px solid #007AFF; }
            QSpinBox { background: #FFFFFF; border: 1px solid #E5E5EA; border-radius: 8px; padding: 6px 10px; }
            QSpinBox:focus { border: 1px solid #007AFF; }
            QComboBox { background: #FFFFFF; border: 1px solid #E5E5EA; border-radius: 8px; padding: 6px 10px; min-width: 60px; }
            QComboBox:focus { border: 1px solid #007AFF; }
            QProgressBar { border: 1px solid #E5E5EA; border-radius: 8px; background: #FFFFFF; text-align: center; }
            QProgressBar::chunk { background-color: #0A84FF; border-radius: 8px; }
            QPushButton { background: #FFFFFF; border: 1px solid #E5E5EA; border-radius: 8px; padding: 6px 12px; }
            QPushButton:hover { border: 1px solid #007AFF; }
            QTextEdit { background: #FFFFFF; border: 1px solid #E5E5EA; border-radius: 8px; padding: 8px; }
            """
        )


class MainWindow(QMainWindow):
    checkCompleted = pyqtSignal(dict)
    logAppended = pyqtSignal(str)
    progressUpdated = pyqtSignal(int, int)

    BUTTON_STYLES = {
        'blue': "QPushButton { background-color: #007AFF; color: white; border: none; border-radius: 8px; padding: 6px 12px; } QPushButton:hover { background-color: #0056b3; } QPushButton:disabled { background-color: #A0A0A0; color: #E0E0E0; }",
        'red': "QPushButton { background-color: #DC3545; color: white; border: none; border-radius: 8px; padding: 6px 12px; } QPushButton:hover { background-color: #C82333; } QPushButton:disabled { background-color: #A0A0A0; color: #E0E0E0; }",
        'yellow': "QPushButton { background-color: #FFC110; color: black; border: none; border-radius: 8px; padding: 6px 12px; } QPushButton:hover { background-color: #E0A800; } QPushButton:disabled { background-color: #A0A0A0; color: #E0E0E0; }",
    }

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Ghidra-AI重命名  by：GuanYue233")
        self.setMinimumSize(500, 550)
        self.resize(700, 600)
        self.setMaximumSize(1400, 1000)
        self.setWindowIcon(QIcon(APP_ICON))

        self._is_running = False
        self._stop_event = None
        self._need_total = 0
        self._processed = 0
        
        self.config_manager = ConfigManager()

        central = QWidget(self)
        self.setCentralWidget(central)

        root_hlayout = QHBoxLayout(central)
        root_hlayout.setContentsMargins(16, 16, 16, 16)
        root_hlayout.setSpacing(12)

        log_group = QGroupBox("日志", self)
        log_v = QVBoxLayout()
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("脚本输出将显示在此处…")
        self.log_view.setMinimumHeight(200)
        log_v.addWidget(self.log_view)
        log_group.setLayout(log_v)
        log_group.setMinimumWidth(320)

        right_widget = QWidget(self)
        root_layout = QVBoxLayout(right_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(12)

        api_group = QGroupBox("API 配置", self)
        api_form = QFormLayout()
        api_group.setLayout(api_form)

        profile_row_layout = QHBoxLayout()
        self.current_profile_display = QLineEdit()
        self.current_profile_display.setReadOnly(True)
        self.btn_select_profile = QPushButton("选择配置")
        self.btn_select_profile.setStyleSheet(self.BUTTON_STYLES['blue'])
        self.btn_select_profile.clicked.connect(self._open_profile_selector)
        profile_row_layout.addWidget(self.current_profile_display, 1)
        profile_row_layout.addWidget(self.btn_select_profile)
        api_form.addRow(QLabel("当前配置:"), profile_row_layout)

        self.input_apikey = QLineEdit()
        self.input_apikey.setPlaceholderText("请输入 API KEY")
        self.input_apibase = QLineEdit()
        self.input_apibase.setPlaceholderText("例如：https://api.siliconflow.cn/")
        self.input_model = QLineEdit()
        self.input_model.setPlaceholderText("例如：Qwen/Qwen2.5-72B-Instruct")
        api_form.addRow(QLabel("API密钥"), self.input_apikey)
        api_form.addRow(QLabel("API网址"), self.input_apibase)
        api_form.addRow(QLabel("MODEL名称"), self.input_model)

        profile_actions_layout = QHBoxLayout()
        profile_actions_layout.addStretch()
        self.btn_save_config = QPushButton("保存当前配置")
        self.btn_save_config.setStyleSheet(self.BUTTON_STYLES['blue'])
        self.btn_save_config.clicked.connect(self._save_profile)
        self.btn_delete_config = QPushButton("删除当前配置")
        self.btn_delete_config.setStyleSheet(self.BUTTON_STYLES['red'])
        self.btn_delete_config.clicked.connect(self._delete_profile)
        profile_actions_layout.addWidget(self.btn_save_config)
        profile_actions_layout.addWidget(self.btn_delete_config)
        api_form.addRow("", profile_actions_layout)

        opts_group = QGroupBox("处理参数", self)
        opts_layout = QVBoxLayout()
        opts_layout.setSpacing(8)
        keyword_layout = QHBoxLayout()
        keyword_layout.setSpacing(8)
        keyword_layout.addWidget(QLabel("关键词（区分大小写）:"))
        self.input_mode = QLineEdit()
        self.input_mode.setPlaceholderText("例如：FUN_")
        self.input_mode.setText("FUN_")
        keyword_layout.addWidget(self.input_mode)
        keyword_layout.addStretch(1)
        batch_delay_layout = QHBoxLayout()
        batch_delay_layout.setSpacing(8)
        # 每批大小
        batch_layout = QHBoxLayout()
        batch_layout.setSpacing(4)
        batch_layout.addWidget(QLabel("每批大小:"))
        self.input_batch = QLineEdit()
        self.input_batch.setValidator(QIntValidator(1, 10000, self))
        self.input_batch.setMinimumWidth(80)
        batch_layout.addWidget(self.input_batch)
        batch_layout.addStretch(1)
        
        # 处理延迟
        delay_layout = QHBoxLayout()
        delay_layout.setSpacing(4)
        delay_layout.addWidget(QLabel("处理延迟 (ms):"))
        self.input_delay_ms = QLineEdit()
        self.input_delay_ms.setValidator(QIntValidator(0, 60000, self))
        self.input_delay_ms.setMinimumWidth(80)
        delay_layout.addWidget(self.input_delay_ms)
        delay_layout.addStretch(1)
        batch_delay_layout.addLayout(batch_layout)
        batch_delay_layout.addLayout(delay_layout)
        opts_layout.addLayout(keyword_layout)
        opts_layout.addLayout(batch_delay_layout)
        opts_group.setLayout(opts_layout)

        progress_group = QGroupBox("进度", self)
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(8)
        row_top = QHBoxLayout()
        row_top.setSpacing(8)
        row_top.addWidget(QLabel("总函数量:"))
        self.label_total = QLabel("0")
        self.label_total.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.label_total.setMinimumWidth(40)
        row_top.addWidget(self.label_total)
        row_top.addWidget(QLabel("需处理数量:"))
        self.label_matched = QLabel("0")
        self.label_matched.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.label_matched.setMinimumWidth(40)
        row_top.addWidget(self.label_matched)
        row_top.addStretch(1)
        row_status = QHBoxLayout()
        row_status.setSpacing(8)
        row_status.addWidget(QLabel("连接状态:"))
        self.label_status = QLabel("未连接")
        self.label_status.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.label_status.setMinimumWidth(120)
        row_status.addWidget(self.label_status)
        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.setStyleSheet(self.BUTTON_STYLES['blue'])
        self.btn_refresh.setMinimumWidth(60)
        self.btn_refresh.clicked.connect(self._start_async_check)
        row_status.addWidget(self.btn_refresh)
        row_status.addStretch(1)
        row_ctrl = QHBoxLayout()
        row_ctrl.setSpacing(8)
        self.btn_start = QPushButton("开始重命名")
        self.btn_start.setStyleSheet(self.BUTTON_STYLES['blue'])
        self.btn_start.setMinimumWidth(80)
        self.btn_stop = QPushButton("停止")
        self.btn_stop.setStyleSheet(self.BUTTON_STYLES['yellow'])
        self.btn_stop.setMinimumWidth(60)
        self.btn_stop.setEnabled(False)
        self.btn_start.clicked.connect(self._start_rename)
        self.btn_stop.clicked.connect(self._stop_rename)
        row_ctrl.addWidget(self.btn_start)
        row_ctrl.addWidget(self.btn_stop)
        row_ctrl.addStretch(1)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setMinimumHeight(20)
        self.label_progress_detail = QLabel("0/0")
        self.label_progress_detail.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.label_progress_detail.setMinimumHeight(16)
        progress_layout.addLayout(row_top)
        progress_layout.addLayout(row_status)
        progress_layout.addLayout(row_ctrl)
        progress_layout.addWidget(self.progress)
        progress_layout.addWidget(self.label_progress_detail)
        progress_group.setLayout(progress_layout)

        root_layout.addWidget(api_group)
        root_layout.addWidget(opts_group)
        root_layout.addWidget(progress_group)
        root_layout.addStretch(1)

        root_hlayout.addWidget(log_group, 1)
        root_hlayout.addWidget(right_widget, 1)

        AppleStyle.apply(self)

        self.checkCompleted.connect(self._apply_check_result)
        self.logAppended.connect(self._append_log)
        self.progressUpdated.connect(self._apply_progress)

        self._mode_timer = QTimer(self)
        self._mode_timer.setSingleShot(True)
        self._mode_timer.timeout.connect(self._start_async_check)
        self.input_mode.textChanged.connect(lambda _: self._mode_timer.start(300))
        
        QTimer.singleShot(0, self._load_initial_profile)
        QTimer.singleShot(100, self._start_async_check)

    def _load_initial_profile(self):
        """加载初始配置"""
        last_profile = self.config_manager.get_last_selected_profile_name()
        names = self.config_manager.get_profile_names()
        profile_to_load = None
        if last_profile in names:
            profile_to_load = last_profile
        elif names:
            profile_to_load = names[0]
        
        if profile_to_load:
            self.current_profile_display.setText(profile_to_load)
            self._load_profile_data(profile_to_load)

    def _load_profile_data(self, name: str):
        if not name: return
        profile = self.config_manager.get_profile(name)
        if profile:
            self.input_apikey.setText(profile.get("api_key", ""))
            self.input_apibase.setText(profile.get("api_base", ""))
            self.input_model.setText(profile.get("model_name", ""))
            self.input_batch.setText(str(profile.get("batch_size", 50)))
            self.input_delay_ms.setText(str(profile.get("delay_ms", 1000)))
            self.config_manager.set_last_selected_profile(name)
            self.logAppended.emit(f"已加载配置: {name}")

    def _open_profile_selector(self):
        profiles = self.config_manager.get_profile_names()
        current = self.current_profile_display.text()
        selected = ProfileSelectorDialog.get_profile(profiles, current, self)
        if selected and selected != current:
            self.current_profile_display.setText(selected)
            self._load_profile_data(selected)

    def _save_profile(self):
        current_name = self.current_profile_display.text()
        
        dialog = QInputDialog(self)
        dialog.setWindowTitle("保存配置")
        dialog.setLabelText("输入配置名称:")
        dialog.setTextValue(current_name)
        dialog.setOkButtonText("确定")
        dialog.setCancelButtonText("取消")
        
        ok = dialog.exec()
        text = dialog.textValue()

        if ok and text:
            api_key = self.input_apikey.text().strip()
            api_base = self.input_apibase.text().strip()
            model_name = self.input_model.text().strip()
            batch_size = int(self.input_batch.text() or 50)
            delay_ms = int(self.input_delay_ms.text() or 1000)
            
            self.config_manager.save_profile(text, api_key, api_base, model_name, batch_size, delay_ms)
            self.logAppended.emit(f"配置已保存: {text}")
            self.current_profile_display.setText(text)
            self.config_manager.set_last_selected_profile(text)

    def _delete_profile(self):
        name = self.current_profile_display.text()
        if not name: return

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("删除配置")
        msg_box.setText(f"确定要删除配置 '{name}' 吗？")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        msg_box.button(QMessageBox.StandardButton.Yes).setText("确定")
        msg_box.button(QMessageBox.StandardButton.No).setText("取消")
        
        reply = msg_box.exec()

        if reply == QMessageBox.StandardButton.Yes:
            if self.config_manager.delete_profile(name):
                self.logAppended.emit(f"配置已删除: {name}")
                self._load_initial_profile()
            else:
                QMessageBox.warning(self, "无法删除", "不能删除最后一个配置。")

    def _classify_log_level(self, text: str) -> str:
        t = text.strip().lower()
        error_keys = ["error", "失败", "异常", "请求超时", "未连接", "请检查", "critical"]
        warn_keys = ["警告", "warning", "跳过", "超时", "失败或返回无效"]
        info_keys = ["成功", "开始", "处理完成", "启动重命名任务", "已加载", "已保存", "已删除"]
        if any(k in t for k in error_keys): return "error"
        if any(k in t for k in warn_keys): return "warn"
        if any(k in t for k in info_keys): return "info"
        return "info"

    def _append_log(self, text: str) -> None:
        level = self._classify_log_level(text)
        color = {"info": "#28A745", "warn": "#FFC107", "error": "#DC3545"}.get(level, "#28A745")
        safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.log_view.append(f"<span style='color:{color};'>{safe}</span>")

    def _apply_progress(self, processed: int, need_total: int) -> None:
        self._processed = max(0, processed)
        if need_total > 0: self._need_total = need_total
        if self._need_total <= 0:
            self.progress.setValue(0)
            self.label_progress_detail.setText("0/0")
            return
        pct = int(min(100, max(0, (self._processed * 100) // max(1, self._need_total))))
        self.progress.setValue(pct)
        self.label_progress_detail.setText(f"{self._processed}/{self._need_total}")
        self.label_matched.setText(str(self._need_total))

    def _start_async_check(self) -> None:
        if self._is_running: return
        def worker():
            result = check_connection_and_count(self.input_mode.text().strip())
            self.checkCompleted.emit(result)
        threading.Thread(target=worker, daemon=True).start()

    def _apply_check_result(self, result: dict) -> None:
        if not self._is_running:
            total, need = int(result.get("total", 0)), int(result.get("matched", 0))
            self.label_total.setText(str(total))
            self.label_matched.setText(str(need))
            self._need_total = need
            self._processed = 0
            self.progress.setValue(0)
            self.label_progress_detail.setText(f"0/{self._need_total}")
        if bool(result.get("connected", False)):
            self.label_status.setText("🟢 🟢 (已连接) ✅ 🚦")
            self.label_status.setStyleSheet("color: #28A745; font-weight: 600;")
        else:
            self.label_status.setText("🔴 🔴 (未连接) ⛔ 🛑")
            self.label_status.setStyleSheet("color: #DC3545; font-weight: 600;")

    def _start_rename(self) -> None:
        # 双重检查状态，确保不会重复启动
        if self._is_running: 
            self.logAppended.emit("任务已在运行中…")
            return
        if run_rename is None:
            self.logAppended.emit("未找到重命名入口(run_rename)。请确认脚本可导入。")
            # 重置按钮状态
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self._is_running = False
            return

        api_key = self.input_apikey.text().strip()
        api_base = self.input_apibase.text().strip()
        model_name = self.input_model.text().strip()
        pattern = self.input_mode.text().strip()
        batch_size = int(self.input_batch.text() or 50)
        delay_seconds = (int(self.input_delay_ms.text() or 1000)) / 1000.0

        self._is_running = True
        self._stop_event = threading.Event()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self._processed = 0
        self.progress.setValue(0)
        self.label_progress_detail.setText("0/0")
        self.log_view.clear()
        self.logAppended.emit("启动重命名任务…")

        def on_log(msg: str): self.logAppended.emit(msg)
        def on_progress(done: int, total_need: int): self.progressUpdated.emit(done, total_need)

        def worker():
            try:
                run_rename(
                    api_key=api_key, api_base=api_base, model_name=model_name,
                    function_pattern=pattern, batch_size=batch_size, delay_seconds=delay_seconds,
                    on_log=on_log, on_progress=on_progress, stop_event=self._stop_event,
                )
            except Exception as e:
                self.logAppended.emit(f"任务异常: {e}")
            finally:
                self._is_running = False
                self.btn_start.setEnabled(True)
                self.btn_stop.setEnabled(False)
        threading.Thread(target=worker, daemon=True).start()

    def _stop_rename(self) -> None:
        if not self._is_running or self._stop_event is None: return
        self._stop_event.set()
        self.logAppended.emit("已请求停止当前任务…")
        # 立即更新按钮状态，给用户视觉反馈
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        # 确保状态标志也被正确设置
        self._is_running = False


def main() -> None:
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(APP_ICON))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
