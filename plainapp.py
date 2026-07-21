import sys
import os
import subprocess
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QTabWidget, QSpinBox, QCheckBox, QGroupBox, QFileDialog
)
from PySide6.QtCore import Qt

class ProfileManagerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        # ----------------- LEFT SIDE: Profile List & Action Buttons -----------------
        left_group = QGroupBox("Registered Chrome Profiles")
        left_layout = QVBoxLayout(left_group)

        self.profile_list = QListWidget()
        left_layout.addWidget(self.profile_list)

        # BUTTON 1: Open Selected Profile for First-Time Login
        self.btn_open = QPushButton("🌐 Open Selected Profile (First-Time Login)")
        self.btn_open.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        self.btn_open.clicked.connect(self.open_profile_for_login)
        left_layout.addWidget(self.btn_open)

        # BUTTON 2: Delete Selected Profile
        self.btn_delete = QPushButton("Delete Selected Profile")
        self.btn_delete.setStyleSheet("background-color: #c0392b; color: white; padding: 6px; border-radius: 4px;")
        self.btn_delete.clicked.connect(self.delete_profile)
        left_layout.addWidget(self.btn_delete)

        main_layout.addWidget(left_group, stretch=1)

        # ----------------- RIGHT SIDE: Setup Form & Settings -----------------
        right_group = QGroupBox("Profile Setup & Automation Settings")
        right_layout = QVBoxLayout(right_group)

        # Input Fields
        right_layout.addWidget(QLabel("Profile Name:"))
        self.txt_name = QLineEdit()
        right_layout.addWidget(self.txt_name)

        right_layout.addWidget(QLabel("Profile Path:"))
        path_layout = QHBoxLayout()
        self.txt_path = QLineEdit()
        btn_browse = QPushButton("Browse Folder")
        btn_browse.clicked.connect(self.browse_folder)
        path_layout.addWidget(self.txt_path)
        path_layout.addWidget(btn_browse)
        right_layout.addLayout(path_layout)

        right_layout.addWidget(QLabel("Telegram Username:"))
        self.txt_username = QLineEdit()
        right_layout.addWidget(self.txt_username)

        right_layout.addWidget(QLabel("Telegram Password:"))
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.txt_password.setPlaceholderText("Optional (Encrypted)")
        right_layout.addWidget(self.txt_password)

        # Action Buttons
        btn_save = QPushButton("Save / Create Profile")
        btn_save.setStyleSheet("background-color: #2980b9; color: white; padding: 8px; font-weight: bold;")
        btn_save.clicked.connect(self.save_profile)
        right_layout.addWidget(btn_save)

        btn_auto = QPushButton("Auto Create 5 Default Profiles")
        btn_auto.setStyleSheet("background-color: #2ecc71; color: white; padding: 8px;")
        btn_auto.clicked.connect(self.auto_create_profiles)
        right_layout.addWidget(btn_auto)

        # Automation Options Group
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

        self.chk_upload = QCheckBox("Upload guard active")
        self.chk_upload.setChecked(True)
        opts_layout.addWidget(self.chk_upload)

        w_layout = QHBoxLayout()
        w_layout.addWidget(QLabel("Max Wait Element (sec):"))
        self.num_wait = QSpinBox()
        self.num_wait.setValue(5)
        w_layout.addWidget(self.num_wait)
        opts_layout.addLayout(w_layout)

        btn_save_opts = QPushButton("Save Settings")
        btn_save_opts.clicked.connect(lambda: QMessageBox.information(self, "Saved", "Settings updated!"))
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
        self.txt_password.clear()
        QMessageBox.information(self, "Success", "Profile list mein add ho gayi hai!")

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

    # --- CHROME PROFILE OPEN / FIRST-TIME LOGIN FUNCTION ---
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

        # Windows Standard Chrome Locations Check
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
        ]

        chrome_bin = None
        for cp in chrome_paths:
            if os.path.exists(cp):
                chrome_bin = cp
                break

        if not chrome_bin:
            QMessageBox.critical(self, "Chrome Not Found", "Google Chrome PC par nahi mila! Baraye meherbani Chrome install karein.")
            return

        try:
            subprocess.Popen([
                chrome_bin,
                f"--user-data-dir={p_path}",
                "https://web.telegram.org/"
            ])
            QMessageBox.information(
                self,
                "Profile Opening...",
                f"Chrome Profile khul rahi hai!\n\nPath: {p_path}\n\n1) Web Telegram par QR Scan / Login karein.\n2) Login ke baad Browser Close kar dein.\n\nSession permanently save ho jaye ga!"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Chrome Open karne mein masla aaya: {e}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Telegram Profile Manager & Scheduler v1.0.0")
        self.resize(950, 600)

        tabs = QTabWidget()
        tabs.addTab(ProfileManagerTab(), "1) Profile Manager")
        tabs.addTab(QWidget(), "2) Universal Scheduler")
        tabs.addTab(QWidget(), "3) Tasks / Runner")
        tabs.addTab(QWidget(), "4) Performance Logs")

        self.setCentralWidget(tabs)


if __name__ == "__main__":
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
