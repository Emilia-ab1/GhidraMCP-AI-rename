import sys
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon
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
)
import threading

from startup_checker import check_connection_and_count
try:
    # 供GUI直接调用重命名逻辑
    from ai_rename import run_rename
except Exception:
    run_rename = None


class AppleStyle:
    @staticmethod
    def apply(widget: QWidget) -> None:
        # 近似 Apple 风格的浅色主题与圆角控件
        app = QApplication.instance()
        if app is None:
            return

        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(245, 245, 247))          # macOS 窗体背景灰白
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))            # 输入框底色
        palette.setColor(QPalette.ColorRole.Text, QColor(28, 28, 30))               # 主文本
        palette.setColor(QPalette.ColorRole.WindowText, QColor(28, 28, 30))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(28, 28, 30))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 122, 255))         # macOS 蓝色
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        app.setPalette(palette)

        app.setStyle("Fusion")

        # 统一字体（San Francisco 近似：使用系统无衬线）
        font = QFont()
        font.setFamily("Segoe UI" if sys.platform.startswith("win") else font.family())
        font.setPointSize(10)
        app.setFont(font)

        # 圆角与间距的样式表
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
            QProgressBar { border: 1px solid #E5E5EA; border-radius: 8px; background: #FFFFFF; text-align: center; }
            QProgressBar::chunk { background-color: #0A84FF; border-radius: 8px; }
            QPushButton { background: #FFFFFF; border: 1px solid #E5E5EA; border-radius: 8px; padding: 6px 12px; }
            QPushButton:hover { border: 1px solid #007AFF; }
            QTextEdit { background: #FFFFFF; border: 1px solid #E5E5EA; border-radius: 8px; padding: 8px; }
            """
        )


class MainWindow(QMainWindow):
    # 使用信号把结果投递回主线程
    checkCompleted = pyqtSignal(dict)
    logAppended = pyqtSignal(str)
    progressUpdated = pyqtSignal(int, int)  # processed, totalNeed

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Ghidra-AI重命名  by：GuanYue233")
        self.setMinimumSize(800, 520)
        self.setWindowIcon(QIcon("res/logo.ico"))

        self._is_running = False
        self._stop_event = None
        self._need_total = 0  # 需处理的函数总量
        self._processed = 0   # 已处理数量

        central = QWidget(self)
        self.setCentralWidget(central)

        # 顶层水平布局：左侧日志，右侧配置与状态
        root_hlayout = QHBoxLayout(central)
        root_hlayout.setContentsMargins(16, 16, 16, 16)
        root_hlayout.setSpacing(12)

        # 左侧：日志
        log_group = QGroupBox("日志", self)
        log_v = QVBoxLayout()
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("脚本输出将显示在此处…")
        log_v.addWidget(self.log_view)
        log_group.setLayout(log_v)
        log_group.setMinimumWidth(360)

        # 右侧：原有内容
        right_widget = QWidget(self)
        root_layout = QVBoxLayout(right_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(12)

        # API 配置
        api_group = QGroupBox("API 配置", self)
        api_form = QFormLayout()
        api_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        api_form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        api_form.setHorizontalSpacing(12)
        api_form.setVerticalSpacing(8)

        self.input_apikey = QLineEdit()
        self.input_apikey.setPlaceholderText("请输入 API KEY")
        self.input_apibase = QLineEdit()
        self.input_apibase.setPlaceholderText("例如：https://api.siliconflow.cn/")
        self.input_apibase.setText("https://api.siliconflow.cn/")
        self.input_model = QLineEdit()
        self.input_model.setPlaceholderText("例如：Qwen/Qwen2.5-72B-Instruct")
        self.input_model.setText("Qwen/Qwen2.5-72B-Instruct")

        api_form.addRow(QLabel("API密钥"), self.input_apikey)
        api_form.addRow(QLabel("API网址"), self.input_apibase)
        api_form.addRow(QLabel("MODEL名称"), self.input_model)
        api_group.setLayout(api_form)

        # 处理参数
        opts_group = QGroupBox("处理参数", self)
        opts_form = QFormLayout()
        opts_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        opts_form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        opts_form.setHorizontalSpacing(12)
        opts_form.setVerticalSpacing(8)

        self.input_mode = QLineEdit()
        self.input_mode.setPlaceholderText("例如：FUN_")
        self.input_mode.setText("FUN_")

        self.spin_batch = QSpinBox()
        self.spin_batch.setRange(1, 10000)
        self.spin_batch.setValue(50)
        self.spin_batch.setSingleStep(50)

        self.spin_delay_ms = QSpinBox()
        self.spin_delay_ms.setRange(0, 60000)
        self.spin_delay_ms.setValue(1000)
        self.spin_delay_ms.setSingleStep(100)

        opts_form.addRow(QLabel("关键词（区分大小写）"), self.input_mode)
        opts_form.addRow(QLabel("每批大小"), self.spin_batch)
        opts_form.addRow(QLabel("处理延迟 (ms)"), self.spin_delay_ms)
        opts_group.setLayout(opts_form)

        # 进度显示
        progress_group = QGroupBox("进度", self)
        progress_layout = QVBoxLayout()
        row_top = QHBoxLayout()
        row_top.addWidget(QLabel("总函数量:"))
        self.label_total = QLabel("0")
        self.label_total.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        row_top.addWidget(self.label_total, 1)
        row_top.addStretch(1)

        row_mid = QHBoxLayout()
        row_mid.addWidget(QLabel("需处理数量:"))
        self.label_matched = QLabel("0")
        self.label_matched.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        row_mid.addWidget(self.label_matched, 1)
        row_mid.addStretch(1)

        row_status = QHBoxLayout()
        row_status.addWidget(QLabel("连接状态:"))
        self.label_status = QLabel("未连接")
        self.label_status.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        row_status.addWidget(self.label_status, 1)
        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.clicked.connect(self._start_async_check)
        row_status.addWidget(self.btn_refresh)
        row_status.addStretch(1)

        # 控制按钮
        row_ctrl = QHBoxLayout()
        self.btn_start = QPushButton("开始重命名")
        self.btn_stop = QPushButton("停止")
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
        self.label_progress_detail = QLabel("0/0")
        self.label_progress_detail.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        progress_layout.addLayout(row_top)
        progress_layout.addLayout(row_mid)
        progress_layout.addLayout(row_status)
        progress_layout.addLayout(row_ctrl)
        progress_layout.addWidget(self.progress)
        progress_layout.addWidget(self.label_progress_detail)
        progress_group.setLayout(progress_layout)

        # 组装
        root_layout.addWidget(api_group)
        root_layout.addWidget(opts_group)
        root_layout.addWidget(progress_group)
        root_layout.addStretch(1)

        root_hlayout.addWidget(log_group, 1)
        root_hlayout.addWidget(right_widget, 1)

        # 应用样式
        AppleStyle.apply(self)

        # 连接信号
        self.checkCompleted.connect(self._apply_check_result)
        self.logAppended.connect(self._append_log)
        self.progressUpdated.connect(self._apply_progress)

        # 文本变化去抖刷新
        self._mode_timer = QTimer(self)
        self._mode_timer.setSingleShot(True)
        self._mode_timer.timeout.connect(self._start_async_check)
        self.input_mode.textChanged.connect(lambda _: self._mode_timer.start(300))

        # 启动后异步检查
        QTimer.singleShot(0, self._start_async_check)

    def _classify_log_level(self, text: str) -> str:
        t = text.strip().lower()
        # 高优先级错误关键词
        error_keys = ["error", "失败", "异常", "请求超时", "未连接", "请检查", "critical"]
        warn_keys = ["警告", "warning", "跳过", "超时", "失败或返回无效"]
        # 明确的成功/信息关键词
        info_keys = ["成功", "开始", "处理完成", "启动重命名任务"]
        if any(k in t for k in error_keys):
            return "error"
        if any(k in t for k in warn_keys):
            return "warn"
        if any(k in t for k in info_keys):
            return "info"
        # 默认按信息
        return "info"

    def _append_log(self, text: str) -> None:
        level = self._classify_log_level(text)
        color = "#28A745" if level == "info" else ("#FFC107" if level == "warn" else "#DC3545")
        safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.log_view.append(f"<span style='color:{color};'>{safe}</span>")

    def _apply_progress(self, processed: int, need_total: int) -> None:
        # 修复进度条：显示已处理/需处理（分母固定为需处理总量）
        self._processed = max(0, processed)
        if need_total > 0:
            self._need_total = need_total
        if self._need_total <= 0:
            self.progress.setValue(0)
            self.label_progress_detail.setText("0/0")
            return
        pct = int(min(100, max(0, (self._processed * 100) // max(1, self._need_total))))
        self.progress.setValue(pct)
        self.label_progress_detail.setText(f"{self._processed}/{self._need_total}")
        # 运行期间：总函数量保持不变；需处理数量保持为固定值，不随进度减少
        self.label_matched.setText(str(self._need_total))

    def _start_async_check(self) -> None:
        # 不打断正在运行的重命名，仅更新连接状态与数量
        if self._is_running:
            return

        def worker():
            pattern = self.input_mode.text().strip()
            result = check_connection_and_count(pattern)
            self.checkCompleted.emit(result)
        threading.Thread(target=worker, daemon=True).start()

    def _apply_check_result(self, result: dict) -> None:
        # 未运行任务时，刷新固定统计
        if not self._is_running:
            total = int(result.get("total", 0))
            need = int(result.get("matched", 0))
            self.label_total.setText(str(total))
            self.label_matched.setText(str(need))
            self._need_total = need
            self._processed = 0
            # 运行前进度固定为0
            self.progress.setValue(0)
            self.label_progress_detail.setText(f"0/{self._need_total}")
        connected = bool(result.get("connected", False))
        if connected:
            self.label_status.setText("🟢 🟢 🟢 (已连接) ✅ 🚦")
            self.label_status.setStyleSheet("color: #28A745; font-weight: 600;")
        else:
            self.label_status.setText("🔴 🔴 🔴 (未连接) ⛔ 🛑 🚨")
            self.label_status.setStyleSheet("color: #DC3545; font-weight: 600;")

    def _start_rename(self) -> None:
        if self._is_running:
            return
        if run_rename is None:
            self.logAppended.emit("未找到重命名入口(run_rename)。请确认脚本可导入。")
            return

        api_key = self.input_apikey.text().strip()
        api_base = self.input_apibase.text().strip()
        model_name = self.input_model.text().strip()
        pattern = self.input_mode.text().strip()
        batch_size = int(self.spin_batch.value())
        delay_seconds = int(self.spin_delay_ms.value()) / 1000.0

        self._is_running = True
        self._stop_event = threading.Event()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        # 运行开始时强制进度为0/需处理
        self._processed = 0
        # _need_total 将在首次 progress 回调中确认
        self.progress.setValue(0)
        self.label_progress_detail.setText("0/0")
        self.log_view.clear()
        self.logAppended.emit("启动重命名任务…")

        def on_log(msg: str):
            self.logAppended.emit(msg)

        def on_progress(done: int, total_need: int):
            self.progressUpdated.emit(done, total_need)

        def worker():
            try:
                run_rename(
                    api_key=api_key,
                    api_base=api_base,
                    model_name=model_name,
                    function_pattern=pattern,
                    batch_size=batch_size,
                    delay_seconds=delay_seconds,
                    on_log=on_log,
                    on_progress=on_progress,
                    stop_event=self._stop_event,
                )
            except Exception as e:
                self.logAppended.emit(f"任务异常: {e}")
            finally:
                self._is_running = False
                self.btn_start.setEnabled(True)
                self.btn_stop.setEnabled(False)
        threading.Thread(target=worker, daemon=True).start()

    def _stop_rename(self) -> None:
        if not self._is_running or self._stop_event is None:
            return
        self._stop_event.set()
        self.logAppended.emit("已请求停止当前任务…")



def main() -> None:
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("res/logo.ico"))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 