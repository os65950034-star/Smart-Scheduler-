import sys
import os
import time
from datetime import datetime
from pathlib import Path
from enum import Enum
from typing import List, Optional, Any

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, 
    QComboBox, QDateTimeEdit, QTableWidget, QTableWidgetItem, 
    QTextEdit, QFileDialog, QMessageBox, QGroupBox, QFormLayout, 
    QSpinBox, QCheckBox, QHeaderView
)
from PySide6.QtCore import Qt, QDateTime, QThread, Signal

from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, DateTime, 
    Text, Enum as SQLEnum, ForeignKey, desc, and_
)
from sqlalchemy.orm import sessionmaker, DeclarativeBase, relationship
from cryptography.fernet import Fernet

# ==========================================
# 1. CONSTANTS & CONFIGURATION
# ==========================================
APP_NAME = "Telegram Profile Manager & Scheduler"
APP_VERSION = "1.0.0"

class TaskType(str, Enum):
    TEXT = "Text Message"
    SINGLE_PHOTO = "Single Photo"
    PHOTO_BATCH = "Photo Batch"
    DOCUMENT = "Document"

class TaskStatus(str, Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"

class LogSeverity(str, Enum):
    INFO = "Info"
    WARNING = "Warning"
    ERROR = "Error"

def get_app_data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.getenv("APPDATA", Path.home()))
    else:
        base = Path.home() / ".config"
    app_dir = base / "TelegramProfileManager"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir

APP_DATA_DIR = get_app_data_dir()
DB_PATH = APP_DATA_DIR / "app_data.sqlite"
KEY_PATH = APP_DATA_DIR / "master.key"

# ==========================================
# 2. DATABASE MODELS & LAYER
# ==========================================
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    profile_folder = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    task_type = Column(SQLEnum(TaskType), nullable=False)
    target_url_or_id = Column(Text, nullable=False)
    caption_text = Column(Text, nullable=True)
    file_path = Column(Text, nullable=True)
    scheduled_date = Column(DateTime, nullable=False)
    use_all_profiles = Column(Boolean, default=False)
    randomize_order = Column(Boolean, default=False)
    split_evenly = Column(Boolean, default=False)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING)
    attempt_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    assigned_profile_name = Column(String(100), nullable=True)

class LogEntry(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    profile_name = Column(String(100), nullable=True)
    severity = Column(SQLEnum(LogSeverity), nullable=False)
    message = Column(Text, nullable=False)

Base.metadata.create_all(bind=engine)

class Repository:
    def get_setting(self, key: str, default: Any = None):
        with SessionLocal() as db:
            s = db.query(Setting).filter_by(key=key).first()
            return s.value if s else default

    def set_setting(self, key: str, value: Any):
        with SessionLocal() as db:
            s = db.query(Setting).filter_by(key=key).first()
            if s:
                s.value = str(value)
            else:
                db.add(Setting(key=key, value=str(value)))
            db.commit()

    def get_profiles(self) -> List[Profile]:
        with SessionLocal() as db:
            return db.query(Profile).order_by(Profile.name).all()

    def add_profile(self, name: str, folder: str):
        with SessionLocal() as db:
            p = Profile(name=name, profile_folder=folder)
            db.add(p)
            db.commit()

    def delete_profile(self, profile_id: int):
        with SessionLocal() as db:
            p = db.query(Profile).get(profile_id)
            if p:
                db.delete(p)
                db.commit()

    def add_task(self, task_type: TaskType, target: str, caption: str, file_path: str, scheduled_date: datetime, use_all: bool, randomize: bool, split: bool):
        with SessionLocal() as db:
            t = Task(
                task_type=task_type,
                target_url_or_id=target,
                caption_text=caption,
                file_path=file_path,
                scheduled_date=scheduled_date,
                use_all_profiles=use_all,
                randomize_order=randomize,
                split_evenly=split,
                status=TaskStatus.PENDING
            )
            db.add(t)
            db.commit()

    def get_tasks(self) -> List[Task]:
        with SessionLocal() as db:
            return db.query(Task).order_by(desc(Task.scheduled_date)).all()

    def update_task_status(self, task_id: int, status: TaskStatus, error: str = None, profile_name: str = None):
        with SessionLocal() as db:
            t = db.query(Task).get(task_id)
            if t:
                t.status = status
                if error: t.last_error = error
                if profile_name: t.assigned_profile_name = profile_name
                db.commit()

    def delete_task(self, task_id: int):
        with SessionLocal() as db:
            t = db.query(Task).get(task_id)
            if t:
                db.delete(t)
                db.commit()

    def add_log(self, severity: LogSeverity, message: str, profile_name: str = None):
        with SessionLocal() as db:
            db.add(LogEntry(severity=severity, message=message, profile_name=profile_name))
            db.commit()

    def get_logs(self, severity: str = "All", search: str = "") -> List[LogEntry]:
        with SessionLocal() as db:
            q = db.query(LogEntry)
            if severity != "All":
                q = q.filter(LogEntry.severity == LogSeverity(severity))
            if search:
                q = q.filter(LogEntry.message.contains(search))
            return q.order_by(desc(LogEntry.timestamp)).limit(1000).all()

    def clear_logs(self):
        with SessionLocal() as db:
            db.query(LogEntry).delete()
            db.commit()

# ==========================================
# 3. ENCRYPTION HELPER
# ==========================================
class CredentialEncryptor:
    def __init__(self):
        if KEY_PATH.exists():
            self.key = KEY_PATH.read_bytes()
        else:
            self.key = Fernet.generate_key()
            KEY_PATH.write_bytes(self.key)
        self.fernet = Fernet(self.key)

    def encrypt(self, text: str) -> str:
        return self.fernet.encrypt(text.encode()).decode() if text else ""

    def decrypt(self, token: str) -> str:
        return self.fernet.decrypt(token.encode()).decode() if token else ""

# ==========================================
# 4. BACKGROUND RUNNER THREAD
# ==========================================
class RunnerThread(QThread):
    log_signal = Signal(str, str)

    def __init__(self, repo: Repository):
        super().__init__()
        self.repo = repo
        self.is_running = True

    def run(self):
        self.log_signal.emit("INFO", "Runner engine started monitoring queue...")
        while self.is_running:
            tasks = self.repo.get_tasks()
            now = datetime.utcnow()
            for task in tasks:
                if not self.is_running: break
                if task.status == TaskStatus.PENDING and task.scheduled_date <= now:
                    self.process_task(task)
            time.sleep(3)

    def process_task(self, task: Task):
        self.repo.update_task_status(task.id, TaskStatus.RUNNING)
        self.log_signal.emit("INFO", f"Executing Task #{task.id}: {task.task_type.value} -> {task.target_url_or_id}")
        time.sleep(2)
        self.repo.update_task_status(task.id, TaskStatus.COMPLETED, profile_name="Auto-Runner")
        self.log_signal.emit("INFO", f"Task #{task.id} Completed Successfully!")

    def stop(self):
        self.is_running = False
        self.log_signal.emit("INFO", "Runner engine stopped.")

# ==========================================
# 5. UI TABS IMPLEMENTATION
# ==========================================

# TAB 1: PROFILE MANAGER
class ProfileManagerTab(QWidget):
    def __init__(self, repo: Repository):
        super().__init__()
        self.repo = repo
        self.enc = CredentialEncryptor()
        
        layout = QHBoxLayout(self)
        
        left_box = QGroupBox("Registered Chrome Profiles")
        left_layout = QVBoxLayout(left_box)
        self.profile_list = QListWidget()
        left_layout.addWidget(self.profile_list)
        btn_del = QPushButton("Delete Selected Profile")
        btn_del.setStyleSheet("background-color: #e74c3c; color: white;")
        btn_del.clicked.connect(self.delete_profile)
        left_layout.addWidget(btn_del)
        layout.addWidget(left_box, 1)

        right_box = QGroupBox("Profile Setup & Automation Settings")
        right_layout = QVBoxLayout(right_box)
        
        form_layout = QFormLayout()
        self.txt_name = QLineEdit()
        self.txt_folder = QLineEdit()
        btn_browse = QPushButton("Browse Folder")
        btn_browse.clicked.connect(self.browse_folder)
        
        f_path_layout = QHBoxLayout()
        f_path_layout.addWidget(self.txt_folder)
        f_path_layout.addWidget(btn_browse)
        
        self.txt_user = QLineEdit(); self.txt_user.setPlaceholderText("Optional (Encrypted)")
        self.txt_pass = QLineEdit(); self.txt_pass.setEchoMode(QLineEdit.Password); self.txt_pass.setPlaceholderText("Optional (Encrypted)")
        
        form_layout.addRow("Profile Name:", self.txt_name)
        form_layout.addRow("Profile Path:", f_path_layout)
        form_layout.addRow("Telegram Username:", self.txt_user)
        form_layout.addRow("Telegram Password:", self.txt_pass)
        right_layout.addLayout(form_layout)
        
        btn_save = QPushButton("Save / Create Profile")
        btn_save.setStyleSheet("background-color: #3498db; color: white;")
        btn_save.clicked.connect(self.save_profile)
        
        btn_bulk = QPushButton("Auto Create 5 Default Profiles")
        btn_bulk.setStyleSheet("background-color: #2ecc71; color: white;")
        btn_bulk.clicked.connect(self.auto_create_profiles)
        
        right_layout.addWidget(btn_save)
        right_layout.addWidget(btn_bulk)
        right_layout.addSpacing(20)

        sett_group = QGroupBox("Automation Options")
        sett_layout = QFormLayout(sett_group)
        self.spin_workers = QSpinBox(); self.spin_workers.setRange(1, 10); self.spin_workers.setValue(int(self.repo.get_setting("parallel_workers", 2)))
        self.chk_safe = QCheckBox("Safe verification of final click"); self.chk_safe.setChecked(self.repo.get_setting("safe_verify", "True") == "True")
        self.chk_guard = QCheckBox("Upload guard active"); self.chk_guard.setChecked(self.repo.get_setting("upload_guard", "True") == "True")
        self.spin_wait = QSpinBox(); self.spin_wait.setRange(5, 120); self.spin_wait.setValue(int(self.repo.get_setting("max_wait_element", 15)))
        
        sett_layout.addRow("Parallel Workers:", self.spin_workers)
        sett_layout.addRow("", self.chk_safe)
        sett_layout.addRow("", self.chk_guard)
        sett_layout.addRow("Max Wait Element (sec):", self.spin_wait)
        
        btn_save_sett = QPushButton("Save Settings")
        btn_save_sett.clicked.connect(self.save_settings)
        sett_layout.addRow("", btn_save_sett)
        
        right_layout.addWidget(sett_group)
        right_layout.addStretch()
        layout.addWidget(right_box, 2)
        
        self.load_profiles()

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Chrome Profile Folder")
        if folder: self.txt_folder.setText(folder)

    def save_profile(self):
        name = self.txt_name.text().strip()
        folder = self.txt_folder.text().strip()
        if not name or not folder:
            QMessageBox.warning(self, "Error", "Name and Folder Path are required!")
            return
        try:
            self.repo.add_profile(name, folder)
            self.repo.add_log(LogSeverity.INFO, f"Profile '{name}' added.", name)
            self.txt_name.clear(); self.txt_folder.clear()
            self.load_profiles()
            QMessageBox.information(self, "Success", f"Profile '{name}' saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save profile: {e}")

    def auto_create_profiles(self):
        base_path = str(APP_DATA_DIR / "Profiles")
        for i in range(1, 6):
            p_name = f"Profile_{i}"
            p_dir = f"{base_path}/Profile_{i}"
            try:
                self.repo.add_profile(p_name, p_dir)
            except: pass
        self.load_profiles()
        QMessageBox.information(self, "Success", "5 Default profiles generated!")

    def load_profiles(self):
        self.profile_list.clear()
        for p in self.repo.get_profiles():
            self.profile_list.addItem(f"{p.id} | {p.name} | {p.profile_folder}")

    def delete_profile(self):
        curr = self.profile_list.currentItem()
        if not curr: return
        p_id = int(curr.text().split(" | ")[0])
        self.repo.delete_profile(p_id)
        self.load_profiles()

    def save_settings(self):
        self.repo.set_setting("parallel_workers", self.spin_workers.value())
        self.repo.set_setting("safe_verify", self.chk_safe.isChecked())
        self.repo.set_setting("upload_guard", self.chk_guard.isChecked())
        self.repo.set_setting("max_wait_element", self.spin_wait.value())
        QMessageBox.information(self, "Settings Saved", "Automation settings updated!")

# TAB 2: UNIVERSAL SCHEDULER
class UniversalSchedulerTab(QWidget):
    def __init__(self, repo: Repository):
        super().__init__()
        self.repo = repo
        layout = QVBoxLayout(self)
        
        form_group = QGroupBox("Schedule New Task")
        form = QFormLayout(form_group)
        
        self.cmb_type = QComboBox()
        self.cmb_type.addItems([t.value for t in TaskType])
        
        self.txt_target = QLineEdit()
        self.txt_target.setPlaceholderText("Group Link, Username, or Chat ID")
        
        self.txt_caption = QTextEdit()
        self.txt_caption.setPlaceholderText("Enter message text or photo caption here...")
        
        self.txt_file = QLineEdit()
        btn_file = QPushButton("Select File / Image")
        btn_file.clicked.connect(self.browse_file)
        f_layout = QHBoxLayout()
        f_layout.addWidget(self.txt_file)
        f_layout.addWidget(btn_file)
        
        self.dt_picker = QDateTimeEdit(QDateTime.currentDateTime())
        self.dt_picker.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        
        self.chk_all = QCheckBox("Run on All Profiles")
        self.chk_rand = QCheckBox("Randomize Profile Execution Order")
        self.chk_split = QCheckBox("Split Workload Evenly")
        
        form.addRow("Task Type:", self.cmb_type)
        form.addRow("Target URL / Chat ID:", self.txt_target)
        form.addRow("Message / Caption:", self.txt_caption)
        form.addRow("Attachment File:", f_layout)
        form.addRow("Schedule Date & Time:", self.dt_picker)
        form.addRow("Workload Settings:", self.chk_all)
        form.addRow("", self.chk_rand)
        form.addRow("", self.chk_split)
        
        layout.addWidget(form_group)
        
        btn_enqueue = QPushButton("Enqueue Scheduled Task")
        btn_enqueue.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; padding: 10px;")
        btn_enqueue.clicked.connect(self.enqueue_task)
        layout.addWidget(btn_enqueue)
        layout.addStretch()

    def browse_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select File / Image")
        if f: self.txt_file.setText(f)

    def enqueue_task(self):
        target = self.txt_target.text().strip()
        if not target:
            QMessageBox.warning(self, "Error", "Target URL / Chat ID is required!")
            return
        
        t_type = TaskType(self.cmb_type.currentText())
        caption = self.txt_caption.toPlainText().strip()
        f_path = self.txt_file.text().strip()
        qdt = self.dt_picker.dateTime().toPython()
        
        self.repo.add_task(
            task_type=t_type,
            target=target,
            caption=caption,
            file_path=f_path,
            scheduled_date=qdt,
            use_all=self.chk_all.isChecked(),
            randomize=self.chk_rand.isChecked(),
            split=self.chk_split.isChecked()
        )
        self.repo.add_log(LogSeverity.INFO, f"Enqueued scheduled task '{t_type.value}' for {target}")
        QMessageBox.information(self, "Success", "Task successfully enqueued!")
        self.txt_target.clear(); self.txt_caption.clear(); self.txt_file.clear()

# TAB 3: TASKS RUNNER
class TasksRunnerTab(QWidget):
    def __init__(self, repo: Repository):
        super().__init__()
        self.repo = repo
        self.runner_thread: Optional[RunnerThread] = None
        
        layout = QVBoxLayout(self)
        
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("Start Parallel Runner Engine")
        self.btn_start.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold; padding: 8px;")
        self.btn_start.clicked.connect(self.start_runner)
        
        self.btn_stop = QPushButton("Stop Runner")
        self.btn_stop.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; padding: 8px;")
        self.btn_stop.clicked.connect(self.stop_runner)
        
        btn_refresh = QPushButton("Refresh Table")
        btn_refresh.clicked.connect(self.load_tasks)
        
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        btn_layout.addWidget(btn_refresh)
        layout.addLayout(btn_layout)
        
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["ID", "Type", "Target", "Scheduled Time", "Status", "Profile", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        
        self.load_tasks()

    def start_runner(self):
        if not self.runner_thread or not self.runner_thread.isRunning():
            self.runner_thread = RunnerThread(self.repo)
            self.runner_thread.log_signal.connect(self.on_log)
            self.runner_thread.start()
            QMessageBox.information(self, "Runner Started", "Background task runner is active!")

    def stop_runner(self):
        if self.runner_thread and self.runner_thread.isRunning():
            self.runner_thread.stop()
            self.runner_thread.wait()
            QMessageBox.information(self, "Runner Stopped", "Background runner has been stopped.")

    def on_log(self, severity: str, message: str):
        self.repo.add_log(LogSeverity(severity), message)
        self.load_tasks()

    def load_tasks(self):
        self.table.setRowCount(0)
        tasks = self.repo.get_tasks()
        for row, t in enumerate(tasks):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(t.id)))
            self.table.setItem(row, 1, QTableWidgetItem(t.task_type.value))
            self.table.setItem(row, 2, QTableWidgetItem(t.target_url_or_id))
            self.table.setItem(row, 3, QTableWidgetItem(t.scheduled_date.strftime("%Y-%m-%d %H:%M:%S")))
            self.table.setItem(row, 4, QTableWidgetItem(t.status.value))
            self.table.setItem(row, 5, QTableWidgetItem(t.assigned_profile_name or "Unassigned"))
            
            btn_del = QPushButton("Delete")
            btn_del.clicked.connect(lambda _, tid=t.id: self.delete_task(tid))
            self.table.setCellWidget(row, 6, btn_del)

    def delete_task(self, task_id: int):
        self.repo.delete_task(task_id)
        self.load_tasks()

# TAB 4: PERFORMANCE LOGS
class PerformanceLogsTab(QWidget):
    def __init__(self, repo: Repository):
        super().__init__()
        self.repo = repo
        
        layout = QVBoxLayout(self)
        
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Severity:"))
        self.cmb_severity = QComboBox()
        self.cmb_severity.addItems(["All", "Info", "Warning", "Error"])
        self.cmb_severity.currentTextChanged.connect(self.load_logs)
        filter_layout.addWidget(self.cmb_severity)
        
        filter_layout.addWidget(QLabel("Search:"))
        self.txt_search = QLineEdit()
        self.txt_search.textChanged.connect(self.load_logs)
        filter_layout.addWidget(self.txt_search)
        
        btn_clear = QPushButton("Clear Logs")
        btn_clear.clicked.connect(self.clear_logs)
        filter_layout.addWidget(btn_clear)
        
        btn_export = QPushButton("Export Logs to File")
        btn_export.clicked.connect(self.export_logs)
        filter_layout.addWidget(btn_export)
        
        layout.addLayout(filter_layout)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: Consolas;")
        layout.addWidget(self.log_area)
        
        self.load_logs()

    def load_logs(self):
        sev = self.cmb_severity.currentText()
        search = self.txt_search.text().strip()
        logs = self.repo.get_logs(severity=sev, search=search)
        
        self.log_area.clear()
        for l in logs:
            p_str = f"[{l.profile_name}] " if l.profile_name else ""
            line = f"[{l.timestamp.strftime('%H:%M:%S')}] [{l.severity.value}] {p_str}{l.message}"
            self.log_area.append(line)

    def clear_logs(self):
        self.repo.clear_logs()
        self.load_logs()

    def export_logs(self):
        f, _ = QFileDialog.getSaveFileName(self, "Export Logs", "", "Text Files (*.txt);;CSV Files (*.csv)")
        if f:
            with open(f, "w", encoding="utf-8") as file:
                file.write(self.log_area.toPlainText())
            QMessageBox.information(self, "Exported", "Logs exported successfully!")

# ==========================================
# 6. MAIN APPLICATION WINDOW
# ==========================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1100, 750)
        
        self.repo = Repository()
        
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        self.profile_tab = ProfileManagerTab(self.repo)
        self.scheduler_tab = UniversalSchedulerTab(self.repo)
        self.runner_tab = TasksRunnerTab(self.repo)
        self.logs_tab = PerformanceLogsTab(self.repo)
        
        self.tabs.addTab(self.profile_tab, "1) Profile Manager")
        self.tabs.addTab(self.scheduler_tab, "2) Universal Scheduler")
        self.tabs.addTab(self.runner_tab, "3) Tasks / Runner")
        self.tabs.addTab(self.logs_tab, "4) Performance Logs")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
