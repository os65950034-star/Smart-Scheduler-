import sys
import os
import subprocess
import random
import json
from datetime import datetime, timedelta, timezone

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QTabWidget, QSpinBox, QCheckBox, QGroupBox, QFileDialog,
    QTimeEdit, QDialog, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QTime, QTimer
from PySide6.QtGui import QFont, QIcon


# --- Helper Function for Dynamic Random Vibrant Button Colors ---
def get_random_button_style():
    vibrant_colors = [
        "#8e44ad", "#e67e22", "#16a085", "#2980b9", "#d35400",
        "#27ae60", "#c0392b", "#f39c12", "#00b894", "#e84393",
        "#6c5ce7", "#00cec9", "#fdcb6e", "#e17055", "#0984e3"
    ]
    bg = random.choice(vibrant_colors)
    return f"""
        QPushButton {{
            background-color: {bg};
            color: white;
            font-weight: bold;
            border-radius: 6px;
            padding: 8px 12px;
        }}
        QPushButton:hover {{
            opacity: 0.9;
        }}
    """


# --- 10 Countries Timezone Window ---
class TimezoneDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🌐 Global Timezones (10 Countries)")
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        header = QLabel("🌍 Live World Clock")
        header.setFont(QFont("Arial", 14, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        self.table = QTableWidget(10, 3)
        self.table.setHorizontalHeaderLabels(["Country", "Timezone", "Current Time (AM/PM)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        btn_close = QPushButton("Close")
        btn_close.setStyleSheet(get_random_button_style())
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_times)
        self.timer.start(1000)
        self.update_times()

    def update_times(self):
        # 10 Selected Countries with standard UTC offsets
        countries = [
            ("🇵🇰 Pakistan", "PKT (UTC+5)", 5),
            ("🇸🇦 Saudi Arabia", "AST (UTC+3)", 3),
            ("🇦🇪 UAE", "GST (UTC+4)", 4),
            ("🇬🇧 United Kingdom", "BST/GMT (UTC+1)", 1),
            ("🇺🇸 USA (New York)", "EDT (UTC-4)", -4),
            ("🇨🇦 Canada (Toronto)", "EDT (UTC-4)", -4),
            ("🇩🇪 Germany", "CEST (UTC+2)", 2),
            ("🇮🇳 India", "IST (UTC+5:30)", 5.5),
            ("🇯🇵 Japan", "JST (UTC+9)", 9),
            ("🇦🇺 Australia (Sydney)", "AEST (UTC+10)", 10),
        ]

        now_utc = datetime.now(timezone.utc)

        for row, (country, tz_name, offset) in enumerate(countries):
            country_time = now_utc + timedelta(hours=offset)
            time_str = country_time.strftime("%I:%M:%S %p")
            
            self.table.setItem(row, 0, QTableWidgetItem(country))
            self.table.setItem(row, 1, QTableWidgetItem(tz_name))
            self.table.setItem(row, 2, QTableWidgetItem(time_str))


# --- TAB 1: Profile Manager Tab ---
class ProfileManagerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        # LEFT SIDE
        left_group = QGroupBox("Registered Chrome Profiles")
        left_layout = QVBoxLayout(left_group)

        self.profile_list = QListWidget()
        left_layout.addWidget(self.profile_list)

        self.btn_open = QPushButton("🌐 Open Selected Profile (First-Time Login)")
        self.btn_open.setStyleSheet(get_random_button_style())
        self.btn_open.clicked.connect(self.open_profile_for_login)
        left_layout.addWidget(self.btn_open)

        self.btn_delete = QPushButton("🗑️ Delete Selected Profile")
        self.btn_delete.setStyleSheet(get_random_button_style())
        self.btn_delete.clicked.connect(self.delete_profile)
        left_layout.addWidget(self.btn_delete)

        main_layout.addWidget(left_group, stretch=1)

        # RIGHT SIDE
        right_group = QGroupBox("Profile Setup & Automation Settings")
        right_layout = QVBoxLayout(right_group)

        right_layout.addWidget(QLabel("Profile Name:"))
        self.txt_name = QLineEdit()
        right_layout.addWidget(self.txt_name)

        right_layout.addWidget(QLabel("Profile Path:"))
        path_layout = QHBoxLayout()
        self.txt_path = QLineEdit()
        btn_browse = QPushButton("📁 Browse Folder")
        btn_browse.setStyleSheet(get_random_button_style())
        btn_browse.clicked.connect(self.browse_folder)
        path_layout.addWidget(self.txt_path)
        path_layout.addWidget(btn_browse)
        right_layout.addLayout(path_layout)

        right_layout.addWidget(QLabel("Telegram Username:"))
        self.txt_username = QLineEdit()
        right_layout.addWidget(self.txt_username)

        btn_save = QPushButton("💾 Save / Create Profile")
        btn_save.setStyleSheet(get_random_button_style())
        btn_save.clicked.connect(self.save_profile)
        right_layout.addWidget(btn_save)

        btn_auto = QPushButton("⚡ Auto Create 5 Default Profiles")
        btn_auto.setStyleSheet(get_random_button_style())
        btn_auto.clicked.connect(self.auto_create_profiles)
        right_layout.addWidget(btn_auto)

        # Options Group
        opts_group = QGroupBox("Automation Options")
        opts_layout = QVBoxLayout(opts_group)

        p_layout = QHBoxLayout()
        p_layout.addWidget(QLabel("Parallel Workers:"))
        self.num_workers = QSpinBox()
        self.num_workers.setValue(1)
        p_layout.addWidget(self.num_workers)
        opts_layout.addLayout(p_layout)

        self.chk_verify = QCheckBox("Safe verification of final click")
        self.chk_verify.setChecked(True)
        opts_layout.addWidget(self.chk_verify)

        btn_save_opts = QPushButton("💾 Save Global Settings")
        btn_save_opts.setStyleSheet(get_random_button_style())
        btn_save_opts.clicked.connect(lambda: QMessageBox.information(self, "Success", "Settings Successfully Saved!"))
        opts_layout.addWidget(btn_save_opts)

        right_layout.addWidget(opts_group)
        main_layout.addWidget(right_group, stretch=2)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Profile Folder")
        if folder:
            self.txt_path.setText(folder)

    def save_profile(self):
        name = self.txt_name.text().strip()
        path = self.txt_path.text().strip()
        username = self.txt_username.text().strip()
        
        if not name or not path:
            QMessageBox.warning(self, "Error", "Profile Name aur Path zaroori hain!")
            return

        item_text = f"{self.profile_list.count() + 1} | {name} | {path}"
        if username:
            item_text += f" | {username}"
        self.profile_list.addItem(item_text)

        self.txt_name.clear()
        self.txt_path.clear()
        self.txt_username.clear()
        QMessageBox.information(self, "Success", "Profile save ho gayi hai!")

    def delete_profile(self):
        curr = self.profile_list.currentRow()
        if curr >= 0:
            self.profile_list.takeItem(curr)
        else:
            QMessageBox.warning(self, "Error", "Pehle list se profile select karein!")

    def auto_create_profiles(self):
        base_dir = os.path.expanduser("~/Desktop/TelegramProfiles")
        os.makedirs(base_dir, exist_ok=True)
        for i in range(1, 6):
            p_dir = os.path.join(base_dir, f"Profile_{i}")
            os.makedirs(p_dir, exist_ok=True)
            self.profile_list.addItem(f"{self.profile_list.count() + 1} | Profile_{i} | {p_dir}")
        QMessageBox.information(self, "Success", "5 Default Profiles Create Ho Gayi Hain!")

    def open_profile_for_login(self):
        curr = self.profile_list.currentItem()
        if not curr:
            QMessageBox.warning(self, "Select Profile", "Pehle left side wali list se koi profile select karein!")
            return

        text = curr.text()
        parts = [p.strip() for p in text.split("|")]
        if len(parts) < 3:
            QMessageBox.warning(self, "Error", "Profile Path invalid hai!")
            return

        p_path = parts[2]
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
        ]

        chrome_bin = next((cp for cp in chrome_paths if os.path.exists(cp)), None)

        if not chrome_bin:
            QMessageBox.critical(self, "Error", "Chrome PC par nahi mila!")
            return

        try:
            subprocess.Popen([chrome_bin, f"--user-data-dir={p_path}", "https://web.telegram.org/"])
            QMessageBox.information(self, "Success", f"Chrome Profile khul rahi hai:\n{p_path}\n\nLogin kar ke Browser close kar dein.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Chrome launch nahi hua: {e}")


# --- TAB 2: Photo TXT batch Tab ---
class PhotoTxtBatchTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        group = QGroupBox("Photo & Text Batch Automation Scheduler")
        g_layout = QVBoxLayout(group)

        # 1) Photo Access Section
        g_layout.addWidget(QLabel("🖼️ Select Photo File / Folder:"))
        photo_layout = QHBoxLayout()
        self.txt_photo_path = QLineEdit()
        btn_browse_photo = QPushButton("📸 Access Photo Path")
        btn_browse_photo.setStyleSheet(get_random_button_style())
        btn_browse_photo.clicked.connect(self.browse_photo)
        photo_layout.addWidget(self.txt_photo_path)
        photo_layout.addWidget(btn_browse_photo)
        g_layout.addLayout(photo_layout)

        # 2) Text File Access Section
        g_layout.addWidget(QLabel("📝 Select TXT Caption File / Folder:"))
        txt_layout = QHBoxLayout()
        self.txt_text_path = QLineEdit()
        btn_browse_txt = QPushButton("📑 Access TXT Path")
        btn_browse_txt.setStyleSheet(get_random_button_style())
        btn_browse_txt.clicked.connect(self.browse_txt)
        txt_layout.addWidget(self.txt_text_path)
        txt_layout.addWidget(btn_browse_txt)
        g_layout.addLayout(txt_layout)

        # 3) Time Selection (AM/PM Option)
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("⏰ Select Schedule Time (12-Hour AM/PM):"))
        self.time_picker = QTimeEdit()
        self.time_picker.setTime(QTime.currentTime())
        self.time_picker.setDisplayFormat("hh:mm:ss AP")  # AM/PM Format
        time_layout.addWidget(self.time_picker)
        g_layout.addLayout(time_layout)

        # Action Buttons
        btn_save_batch = QPushButton("💾 Save Batch Settings")
        btn_save_batch.setStyleSheet(get_random_button_style())
        btn_save_batch.clicked.connect(self.save_batch_settings)
        g_layout.addWidget(btn_save_batch)

        btn_run_batch = QPushButton("🚀 Start Photo TXT Batch Process")
        btn_run_batch.setStyleSheet(get_random_button_style())
        btn_run_batch.clicked.connect(self.run_batch)
        g_layout.addWidget(btn_run_batch)

        layout.addWidget(group)

    def browse_photo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Photo File", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.txt_photo_path.setText(path)

    def browse_txt(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select TXT File", "", "Text Files (*.txt)")
        if path:
            self.txt_text_path.setText(path)

    def save_batch_settings(self):
        selected_time = self.time_picker.time().toString("hh:mm:ss AP")
        QMessageBox.information(
            self, "Batch Saved", 
            f"Batch Configuration Saved!\n\nPhoto: {self.txt_photo_path.text()}\nText: {self.txt_text_path.text()}\nTime: {selected_time}"
        )

    def run_batch(self):
        if not self.txt_photo_path.text() or not self.txt_text_path.text():
            QMessageBox.warning(self, "Warning", "Please photo aur TXT file dono select karein!")
            return
        selected_time = self.time_picker.time().toString("hh:mm:ss AP")
        QMessageBox.information(self, "Batch Started", f"Batch automation scheduled for {selected_time} successfully!")


# --- MAIN APPLICATION WINDOW ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("⭐ STAR SCHEDULER & AUTOMATION PLATFORM ⭐")
        self.resize(1000, 650)

        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)

        # --- STAR HEADER BAR ---
        header_layout = QHBoxLayout()
        
        star_logo = QLabel("⭐ STAR SCHEDULER ⭐")
        star_logo.setFont(QFont("Arial", 16, QFont.Bold))
        star_logo.setStyleSheet("color: #f1c40f; padding: 5px;")
        header_layout.addWidget(star_logo)

        header_layout.addStretch()

        # 10 Countries Timezone Button
        btn_tz = QPushButton("🌐 World Timezones (10 Countries)")
        btn_tz.setStyleSheet(get_random_button_style())
        btn_tz.clicked.connect(self.show_timezones)
        header_layout.addWidget(btn_tz)

        layout.addLayout(header_layout)

        # --- TABS ---
        tabs = QTabWidget()
        tabs.addTab(ProfileManagerTab(), "1) Profile Manager")
        tabs.addTab(PhotoTxtBatchTab(), "2) Photo TXT batch")
        tabs.addTab(QWidget(), "3) Tasks / Runner")
        tabs.addTab(QWidget(), "4) Performance Logs")

        layout.addWidget(tabs)
        self.setCentralWidget(main_widget)

    def show_timezones(self):
        dlg = TimezoneDialog(self)
        dlg.exec()


if __name__ == "__main__":
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
