import sys
import os
import shutil
import logging
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QFileDialog, QDialog, QListWidget, QListWidgetItem, QMessageBox, QSplashScreen, QCheckBox)
from PyQt5.QtCore import Qt, QTimer, QEasingCurve, QPropertyAnimation, QEvent
from PyQt5.QtGui import QIcon, QPixmap, QFont
import pickle
import ctypes

# Resource path function for PyInstaller
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Constants
DATA_DIR = os.path.join(os.path.dirname(sys.executable), "data")
print(sys.executable) 
PIN_FILE = os.path.join(DATA_DIR, "pin.pkl")
PROTECTED_FILES_DB = os.path.join(DATA_DIR, "protected_files.pkl")
PROTECTED_DIR = os.path.join(DATA_DIR, ".protected_files")
WINDOW_SIZE = (780, 500)
LOG_FILE = os.path.join(DATA_DIR, "onelock.log")
SPLASH_DURATION = 2000
SPLASH_SIZE = (400, 250)

# Ensure DATA_DIR exists before logging
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Setup logging
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Log startup
logging.info("Starting OneLock application")

class LoginDialog(QDialog):
    def __init__(self, correct_pin, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OneLock - Login")
        self.setFixedSize(300, 200)
        self.setModal(True)
        self.correct_pin = correct_pin
        self.setup_ui()
        # Install event filter to detect clicks outside the dialog
        self.installEventFilter(self)

    def setup_ui(self):
        self.setStyleSheet("""
            QDialog { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2d2d2d, stop:1 #1e1e1e); border: 1px solid #444; }
            QPushButton { background-color: #1e90ff; color: white; border-radius: 15px; padding: 10px; font-family: Segoe UI; font-size: 14px; }
            QPushButton:hover { background-color: #4682b4; }
            QLineEdit { background-color: #3c3c3c; color: #e0e0e0; border: 1px solid #555; border-radius: 10px; padding: 8px; font-size: 14px; }
            QLineEdit:focus { border: 1px solid #1e90ff; }
            QLabel { font-size: 16px; font-family: Segoe UI; color: #e0e0e0; min-height: 30px; }
            QCheckBox { color: #ffffff; font-family: Segoe UI; font-size: 14px; }
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        self.instruction_label = QLabel("Enter your 6-digit PIN to login:\n(Use numbers only)")
        self.instruction_label.setAlignment(Qt.AlignCenter)
        self.instruction_label.setWordWrap(True)
        self.pin_input = QLineEdit()
        self.pin_input.setMaxLength(6)
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setPlaceholderText("Enter 6-digit PIN")
        self.pin_input.setToolTip("Enter the 6-digit PIN you set up to access OneLock.")
        self.show_pin_checkbox = QCheckBox("Show PIN")
        self.show_pin_checkbox.setToolTip("Check to view your PIN while typing.")
        self.show_pin_checkbox.stateChanged.connect(self.toggle_pin_visibility)
        self.login_button = QPushButton("Login")
        self.login_button.setToolTip("Click to log in with your PIN.")
        self.login_button.clicked.connect(self.verify_pin)
        layout.addWidget(self.instruction_label)
        layout.addWidget(self.pin_input)
        layout.addWidget(self.show_pin_checkbox)
        layout.addWidget(self.login_button)

        self.opacity_effect = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_effect.setDuration(500)
        self.opacity_effect.setStartValue(0.0)
        self.opacity_effect.setEndValue(1.0)
        self.opacity_effect.setEasingCurve(QEasingCurve.InOutQuad)
        self.opacity_effect.start()

    def toggle_pin_visibility(self):
        if self.show_pin_checkbox.isChecked():
            self.pin_input.setEchoMode(QLineEdit.Normal)
        else:
            self.pin_input.setEchoMode(QLineEdit.Password)

    def verify_pin(self):
        entered_pin = self.pin_input.text()
        if entered_pin == self.correct_pin:
            self.accept()
        else:
            self.instruction_label.setText("Incorrect PIN! Try again:\n(Use numbers only)")
            self.pin_input.clear()

    def eventFilter(self, obj, event):
        # Detect mouse button press events
        if event.type() == QEvent.MouseButtonPress:
            # Check if the click is outside the dialog
            if not self.rect().contains(self.mapFromGlobal(event.globalPos())):
                self.reject()  # Close the dialog if clicked outside
                return True  # Consume the event
        return super().eventFilter(obj, event)

class UnlockDialog(QDialog):
    def __init__(self, filename, correct_pin, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OneLock - Unlock")
        self.setFixedSize(300, 220)
        self.setModal(True)
        self.correct_pin = correct_pin
        self.filename = filename
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("""
            QDialog { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2d2d2d, stop:1 #1e1e1e); border: 1px solid #444; }
            QPushButton { background-color: #1e90ff; color: white; border-radius: 15px; padding: 10px; font-family: Segoe UI; font-size: 14px; }
            QPushButton:hover { background-color: #4682b4; }
            QLineEdit { background-color: #3c3c3c; color: #e0e0e0; border: 1px solid #555; border-radius: 10px; padding: 8px; font-size: 14px; }
            QLineEdit:focus { border: 1px solid #1e90ff; }
            QLabel { font-size: 16px; font-family: Segoe UI; color: #e0e0e0; min-height: 40px; }
            QCheckBox { color: #ffffff; font-family: Segoe UI; font-size: 14px; }
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        self.instruction_label = QLabel(f"Enter PIN to unlock\n{self.filename}:\n(Use the same 6-digit PIN)")
        self.instruction_label.setAlignment(Qt.AlignCenter)
        self.instruction_label.setWordWrap(True)
        self.pin_input = QLineEdit()
        self.pin_input.setMaxLength(6)
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setPlaceholderText("Enter 6-digit PIN")
        self.pin_input.setToolTip("Enter your 6-digit PIN to unlock the selected file(s).")
        self.show_pin_checkbox = QCheckBox("Show PIN")
        self.show_pin_checkbox.setToolTip("Check to view your PIN while typing.")
        self.show_pin_checkbox.stateChanged.connect(self.toggle_pin_visibility)
        self.unlock_button = QPushButton("Unlock")
        self.unlock_button.setToolTip("Click to unlock the selected file(s) with your PIN.")
        self.unlock_button.clicked.connect(self.verify_pin)
        layout.addWidget(self.instruction_label)
        layout.addWidget(self.pin_input)
        layout.addWidget(self.show_pin_checkbox)
        layout.addWidget(self.unlock_button)

        self.opacity_effect = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_effect.setDuration(500)
        self.opacity_effect.setStartValue(0.0)
        self.opacity_effect.setEndValue(1.0)
        self.opacity_effect.setEasingCurve(QEasingCurve.InOutQuad)
        self.opacity_effect.start()

    def toggle_pin_visibility(self):
        if self.show_pin_checkbox.isChecked():
            self.pin_input.setEchoMode(QLineEdit.Normal)
        else:
            self.pin_input.setEchoMode(QLineEdit.Password)

    def verify_pin(self):
        entered_pin = self.pin_input.text()
        if entered_pin == self.correct_pin:
            self.accept()
        else:
            self.instruction_label.setText(f"Incorrect PIN!\nEnter PIN to unlock {self.filename}:\n(Use the same 6-digit PIN)")
            self.pin_input.clear()

class OneLock(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OneLock")
        self.setGeometry(100, 100, *WINDOW_SIZE)
        self.setFixedSize(*WINDOW_SIZE)
        self.setAcceptDrops(True)
        self.protected_files = {}
        self.pending_files = []
        self.pin = None
        self.notification_label = None
        self.locked_list = QListWidget()
        icon_path = resource_path("lock.ico")
        if not os.path.exists(icon_path):
            logging.error(f"Icon file not found at: {icon_path}")
        self.setWindowIcon(QIcon(icon_path))
        self.setup_protected_dir()
        self.setup_ui()
        self.load_data()
        self.clean_missing_files()

    def setup_protected_dir(self):
        if not os.path.exists(PROTECTED_DIR):
            os.makedirs(PROTECTED_DIR)
            ctypes.windll.kernel32.SetFileAttributesW(PROTECTED_DIR, 2)

    def setup_ui(self):
        self.setStyleSheet("""
            QMainWindow { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2d2d2d, stop:1 #1e1e1e); border: 1px solid #444; }
            QPushButton { background-color: #1e90ff; color: white; border-radius: 15px; padding: 10px; font-family: Segoe UI; font-size: 14px; }
            QPushButton:hover { background-color: #4682b4; }
            QLineEdit { background-color: #3c3c3c; color: #e0e0e0; border: 1px solid #555; border-radius: 10px; padding: 8px; font-size: 14px; }
            QLineEdit:focus { border: 1px solid #1e90ff; }
            QLabel { font-size: 16px; font-family: Segoe UI; color: #e0e0e0; }
        """)
        
        if not os.path.exists(PIN_FILE):
            self.show_pin_setup()
        else:
            self.show_login_dialog()

    def show_pin_setup(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(50, 50, 50, 50)

        self.title_label = QLabel("Create Your OneLock PIN")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("""
            font-size: 24px; font-family: Segoe UI; color: #e0e0e0; font-weight: bold;
        """)

        self.instruction_label = QLabel("Set a 6-digit PIN to secure your files:\n(Use numbers only, e.g., 123456)")
        self.instruction_label.setAlignment(Qt.AlignCenter)
        self.instruction_label.setWordWrap(True)
        self.instruction_label.setStyleSheet("font-size: 14px; color: #b0b0b0;")

        self.pin_input = QLineEdit()
        self.pin_input.setMaxLength(6)
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setPlaceholderText("Enter 6-digit PIN")
        self.pin_input.setToolTip("Enter a 6-digit PIN (numbers only) to secure your files.")
        self.pin_input.setFixedHeight(50)
        self.pin_input.setFont(QFont("Segoe UI", 14))
        self.pin_input.setStyleSheet("""
            background-color: #3c3c3c; color: #e0e0e0; border: 1px solid #555; border-radius: 15px; padding: 10px;
        """)
        self.pin_input.setFocus()

        self.confirm_input = QLineEdit()
        self.confirm_input.setMaxLength(6)
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setPlaceholderText("Confirm 6-digit PIN")
        self.confirm_input.setToolTip("Re-enter the same 6-digit PIN to confirm.")
        self.confirm_input.setFixedHeight(50)
        self.confirm_input.setFont(QFont("Segoe UI", 14))
        self.confirm_input.setStyleSheet("""
            background-color: #3c3c3c; color: #e0e0e0; border: 1px solid #555; border-radius: 15px; padding: 10px;
        """)

        self.show_pin_checkbox = QCheckBox("Show PIN")
        self.show_pin_checkbox.setToolTip("Check to view your PIN while typing.")
        self.show_pin_checkbox.setStyleSheet("""
            color: #ffffff; font-family: Segoe UI; font-size: 14px;
        """)
        self.show_pin_checkbox.stateChanged.connect(self.toggle_pin_setup_visibility)

        self.submit_button = QPushButton("Create PIN")
        self.submit_button.setToolTip("Click to create your PIN and start using OneLock.")
        self.submit_button.setFixedSize(150, 50)
        self.submit_button.setStyleSheet("""
            QPushButton { background-color: #1e90ff; color: white; border-radius: 25px; font-family: Segoe UI; font-size: 16px; font-weight: bold; }
            QPushButton:hover { background-color: #4682b4; }
            QPushButton:pressed { background-color: #1c78d1; }
        """)
        self.submit_button.clicked.connect(self.save_pin)

        self.button_animation = QPropertyAnimation(self.submit_button, b"geometry")
        self.submit_button.enterEvent = lambda e: self.animate_button(self.submit_button, 1.1)
        self.submit_button.leaveEvent = lambda e: self.animate_button(self.submit_button, 1.0)
        self.submit_button.clicked.connect(lambda: self.animate_button(self.submit_button, 0.95))

        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("""
            color: #ff4d4d; font-family: Segoe UI; font-size: 14px; min-height: 30px;
        """)

        layout.addWidget(self.title_label)
        layout.addWidget(self.instruction_label)
        layout.addWidget(self.pin_input)
        layout.addWidget(self.confirm_input)
        layout.addWidget(self.show_pin_checkbox)
        layout.addWidget(self.error_label)
        layout.addWidget(self.submit_button, alignment=Qt.AlignCenter)

        self.opacity_effect = QPropertyAnimation(self.central_widget, b"windowOpacity")
        self.opacity_effect.setDuration(500)
        self.opacity_effect.setStartValue(0.0)
        self.opacity_effect.setEndValue(1.0)
        self.opacity_effect.setEasingCurve(QEasingCurve.InOutQuad)
        self.opacity_effect.start()

        self.pin_input.textChanged.connect(self.check_pin_length)

    def check_pin_length(self):
        if len(self.pin_input.text()) == 6:
            self.confirm_input.setFocus()

    def animate_button(self, button, scale_factor, event=None):
        rect = button.geometry()
        new_size = rect.size() * scale_factor
        new_rect = rect.adjusted(0, 0, new_size.width() - rect.width(), new_size.height() - rect.height())
        new_rect.moveCenter(rect.center())
        animation = QPropertyAnimation(button, b"geometry")
        animation.setDuration(200)
        animation.setStartValue(rect)
        animation.setEndValue(new_rect)
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        animation.start()

    def toggle_pin_setup_visibility(self):
        if self.show_pin_checkbox.isChecked():
            self.pin_input.setEchoMode(QLineEdit.Normal)
            self.confirm_input.setEchoMode(QLineEdit.Normal)
        else:
            self.pin_input.setEchoMode(QLineEdit.Password)
            self.confirm_input.setEchoMode(QLineEdit.Password)

    def save_pin(self):
        pin = self.pin_input.text()
        confirm_pin = self.confirm_input.text()

        if len(pin) != 6 or not pin.isdigit():
            self.error_label.setText("PIN must be 6 digits!")
            self.error_label.show()
            return
        if pin != confirm_pin:
            self.error_label.setText("PINs do not match!")
            self.error_label.show()
            return

        self.pin = pin
        with open(PIN_FILE, "wb") as f:
            pickle.dump(pin, f)
        logging.info("PIN created successfully")
        self.error_label.hide()
        self.show_main_ui()

    def show_login_dialog(self):
        if not self.pin:
            self.load_data()
        dialog = LoginDialog(self.pin, self)
        if dialog.exec_() == QDialog.Accepted:
            self.show_main_ui()
        else:
            self.close()  # Close the application if login fails

    def show_main_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        self.title_label = QLabel("OneLock")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("""
            font-size: 24px; font-family: Segoe UI; color: #e0e0e0; font-weight: bold; 
            min-height: 40px; margin-bottom: 10px;
        """)

        self.instruction_label = QLabel("Hide your files with a PIN!\nDrag and drop files here or use the button below.")
        self.instruction_label.setAlignment(Qt.AlignCenter)
        self.instruction_label.setWordWrap(True)
        self.instruction_label.setStyleSheet("font-size: 14px; color: #b0b0b0;")

        self.notification_label = QLabel("")
        self.notification_label.setAlignment(Qt.AlignCenter)
        self.notification_label.setStyleSheet("""
            background-color: #3c3c3c; color: #ffffff; font-size: 14px; font-family: Segoe UI; 
            padding: 8px; border-radius: 5px; border: 1px solid #555; min-height: 30px; margin-bottom: 10px;
        """)
        self.notification_label.hide()

        self.status_label = QLabel("Welcome to OneLock")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            font-size: 16px; font-family: Segoe UI; color: #e0e0e0; background-color: rgba(255, 255, 255, 0.05); 
            padding: 8px; border-radius: 5px; min-height: 30px; margin-bottom: 15px;
        """)
        self.status_label.setWordWrap(True)

        self.locked_list_label = QLabel("Locked Files")
        self.locked_list_label.setAlignment(Qt.AlignCenter)
        self.locked_list_label.setStyleSheet("""
            font-size: 18px; font-family: Segoe UI; color: #ffffff; font-weight: bold; 
            min-height: 30px; margin-bottom: 10px;
        """)
        self.locked_list.setStyleSheet("""
            background-color: #2d2d2d; color: #e0e0e0; border: 1px solid #555; border-radius: 10px; 
            padding: 5px; font-size: 14px; font-family: Segoe UI; max-height: 200px;
        """)
        self.locked_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.choose_button = QPushButton("Choose File to Lock 🔒")
        self.choose_button.setToolTip("Click to select files to hide with OneLock.")
        self.choose_button.setFixedHeight(40)
        self.choose_button.setStyleSheet("""
            QPushButton { background-color: #1e90ff; color: white; border-radius: 15px; font-family: Segoe UI; 
                          font-size: 14px; padding: 8px; }
            QPushButton:hover { background-color: #4682b4; }
        """)
        self.choose_button.clicked.connect(self.choose_files)

        self.unlock_button = QPushButton("Unlock Selected Files 🔓")
        self.unlock_button.setToolTip("Click to restore selected hidden files with your PIN.")
        self.unlock_button.setFixedHeight(40)
        self.unlock_button.setStyleSheet("""
            QPushButton { background-color: #1e90ff; color: white; border-radius: 15px; font-family: Segoe UI; 
                          font-size: 14px; padding: 8px; }
            QPushButton:hover { background-color: #4682b4; }
        """)
        self.unlock_button.clicked.connect(self.unlock_selected_files)

        layout.addWidget(self.title_label)
        layout.addWidget(self.instruction_label)
        layout.addWidget(self.notification_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.locked_list_label)
        layout.addWidget(self.locked_list)
        layout.addWidget(self.choose_button)
        layout.addWidget(self.unlock_button, alignment=Qt.AlignCenter)

        self.opacity_effect = QPropertyAnimation(self.central_widget, b"windowOpacity")
        self.opacity_effect.setDuration(300)
        self.opacity_effect.setStartValue(0.0)
        self.opacity_effect.setEndValue(1.0)
        self.opacity_effect.setEasingCurve(QEasingCurve.InOutQuad)
        self.opacity_effect.start()

        self.show()
        self.update_locked_list()

    def update_locked_list(self):
        self.locked_list.clear()
        for placeholder_path in self.protected_files.keys():
            original_path = placeholder_path.replace(".locked", "")
            item = QListWidgetItem(os.path.basename(original_path))
            item.setData(Qt.UserRole, placeholder_path)
            self.locked_list.addItem(item)

    def clean_missing_files(self):
        keys_to_remove = []
        for placeholder_path, protected_path in self.protected_files.items():
            if not os.path.exists(placeholder_path) or not os.path.exists(protected_path):
                keys_to_remove.append(placeholder_path)
        for key in keys_to_remove:
            del self.protected_files[key]
        self.save_protected_files()
        self.update_locked_list()

    def show_locking_notification(self):
        self.notification_label.setText("The file is locked and hidden. Press Unlock button to restore it.")
        self.notification_label.show()

        self.fade_in = QPropertyAnimation(self.notification_label, b"windowOpacity")
        self.fade_in.setDuration(300)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)
        self.fade_in.setEasingCurve(QEasingCurve.InOutQuad)
        self.fade_in.start()

        QTimer.singleShot(2000, self.hide_locking_notification)

    def hide_locking_notification(self):
        self.fade_out = QPropertyAnimation(self.notification_label, b"windowOpacity")
        self.fade_out.setDuration(300)
        self.fade_out.setStartValue(1.0)
        self.fade_out.setEndValue(0.0)
        self.fade_out.setEasingCurve(QEasingCurve.InOutQuad)
        self.fade_out.finished.connect(self.notification_label.hide)
        self.fade_out.start()

    def reset_application(self):
        reply = QMessageBox.question(self, "Reset Application",
                                     "Are you sure you want to reset the application? This will delete your PIN and all locked files.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                if os.path.exists(PIN_FILE):
                    os.remove(PIN_FILE)
                    logging.info("Deleted PIN file: pin.pkl")
                if os.path.exists(PROTECTED_FILES_DB):
                    os.remove(PROTECTED_FILES_DB)
                    logging.info("Deleted protected files database: protected_files.pkl")
                if os.path.exists(PROTECTED_DIR):
                    shutil.rmtree(PROTECTED_DIR)
                    logging.info("Deleted protected files directory: .protected_files")
                self.protected_files = {}
                self.pending_files = []
                self.pin = None
                QMessageBox.information(self, "Reset Complete", "Application has been reset. You will need to set a new PIN.")
                self.show_pin_setup()
            except Exception as e:
                logging.error(f"Error resetting application: {e}")
                QMessageBox.critical(self, "Error", f"Failed to reset application: {str(e)}")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        self.pending_files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.choose_button.setText("Lock Files")
        self.lock_files()

    def choose_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files to Lock", "", "All Files (*.*)")
        if files:
            self.pending_files = files
            self.choose_button.setText("Choose More Files to Lock 🔒")
            self.lock_files()

            self.status_animation = QPropertyAnimation(self.status_label, b"text")
            self.status_animation.setDuration(300)
            self.status_animation.setStartValue(self.status_label.text())
            self.status_animation.setEndValue(f"Selected {len(files)} file(s) to lock")
            self.status_animation.setEasingCurve(QEasingCurve.Linear)
            self.status_animation.start()

    def lock_files(self):
        if not self.pending_files:
            return

        locked_count = 0
        for file_path in self.pending_files:
            is_already_locked = any(placeholder_path.replace(".locked", "") == file_path for placeholder_path in self.protected_files.keys())
            if os.path.exists(file_path) and not is_already_locked:
                self.show_locking_notification()
                try:
                    protected_path = os.path.join(PROTECTED_DIR, os.path.basename(file_path))
                    shutil.move(file_path, protected_path)
                    placeholder_path = file_path + ".locked"
                    with open(placeholder_path, "w") as f:
                        f.write("Locked by OneLock. Use the app to unlock.")
                    ctypes.windll.kernel32.SetFileAttributesW(placeholder_path, 2)
                    self.protected_files[placeholder_path] = protected_path
                    logging.info(f"Locked file: {file_path}")
                    locked_count += 1
                    QApplication.processEvents()
                    QTimer.singleShot(1300, lambda: None)
                except Exception as e:
                    logging.error(f"Error locking {file_path}: {e}")
                    QMessageBox.critical(self, "Error", f"Failed to lock {os.path.basename(file_path)}: {str(e)}")
            elif is_already_locked:
                logging.warning(f"File {file_path} is already locked, skipping.")
        self.save_protected_files()
        self.pending_files = []
        self.update_locked_list()
        if locked_count > 0:
            self.status_label.setText(f"Locked {locked_count} file(s) successfully!")
            self.status_animation = QPropertyAnimation(self.status_label, b"text")
            self.status_animation.setDuration(300)
            self.status_animation.setStartValue(self.status_label.text())
            self.status_animation.setEndValue(f"Locked {locked_count} file(s) successfully!")
            self.status_animation.setEasingCurve(QEasingCurve.Linear)
            self.status_animation.start()
        else:
            self.status_label.setText("No new files locked (some may be already locked).")

    def unlock_selected_files(self):
        selected_items = self.locked_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select files to unlock!")
            return

        filenames = ", ".join([item.text() for item in selected_items])
        dialog = UnlockDialog(filenames, self.pin, self)
        if dialog.exec_() == QDialog.Accepted:
            unlocked_count = 0
            for item in selected_items:
                placeholder_path = item.data(Qt.UserRole)
                protected_path = self.protected_files[placeholder_path]
                try:
                    original_path = placeholder_path.replace(".locked", "")
                    shutil.move(protected_path, original_path)
                    os.remove(placeholder_path)
                    del self.protected_files[placeholder_path]
                    logging.info(f"Unlocked file: {original_path}")
                    unlocked_count += 1
                except Exception as e:
                    logging.error(f"Error unlocking {placeholder_path}: {e}")
                    QMessageBox.critical(self, "Error", f"Failed to unlock {os.path.basename(placeholder_path)}: {str(e)}")
            self.save_protected_files()
            self.update_locked_list()
            self.status_label.setText(f"Unlocked {unlocked_count} file(s) successfully!")
            self.status_animation = QPropertyAnimation(self.status_label, b"text")
            self.status_animation.setDuration(300)
            self.status_animation.setStartValue(self.status_label.text())
            self.status_animation.setEndValue(f"Unlocked {unlocked_count} file(s) successfully!")
            self.status_animation.setEasingCurve(QEasingCurve.Linear)
            self.status_animation.start()
        else:
            self.status_label.setText("Unlock canceled - incorrect PIN")

    def load_data(self):
        try:
            if os.path.exists(PIN_FILE):
                with open(PIN_FILE, "rb") as f:
                    self.pin = pickle.load(f)
            if os.path.exists(PROTECTED_FILES_DB):
                with open(PROTECTED_FILES_DB, "rb") as f:
                    self.protected_files = pickle.load(f)
        except Exception as e:
            logging.error(f"Error loading data: {e}")
            QMessageBox.critical(self, "Error", "Failed to load locker data. Starting fresh.")

    def save_protected_files(self):
        try:
            with open(PROTECTED_FILES_DB, "wb") as f:
                pickle.dump(self.protected_files, f)
        except Exception as e:
            logging.error(f"Error saving protected files: {e}")
            QMessageBox.critical(self, "Error", "Failed to save locker data!")

    def closeEvent(self, event):
        # Save protected files before exiting
        self.save_protected_files()
        logging.info("Application closed. Protected files saved.")
        event.accept()  # Accept the close event to exit the application
        QApplication.quit()

    def quit_application(self):
        # Save protected files before quitting
        self.save_protected_files()
        logging.info("Application quit. Protected files saved.")
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Show splash screen with resource path
    try:
        logo_path = resource_path("logo.png")
        if not os.path.exists(logo_path):
            logging.error(f"Logo file not found at: {logo_path}")
            raise FileNotFoundError("logo.png not found")
        splash_pix = QPixmap(logo_path)
        if splash_pix.isNull():
            logging.error("Failed to load logo.png for splash screen")
            raise FileNotFoundError("logo.png is invalid")
        splash_pix = splash_pix.scaled(SPLASH_SIZE[0], SPLASH_SIZE[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
        splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
        splash.setFixedSize(SPLASH_SIZE[0], SPLASH_SIZE[1])
        splash.show()
        logging.info("Splash screen loaded successfully")
    except Exception as e:
        logging.error(f"Error loading splash screen: {e}")
        QMessageBox.critical(None, "Error", "Failed to load splash screen image.")

    app.processEvents()

    window = OneLock()

    def show_main_window():
        splash.close()
        window.show()

    QTimer.singleShot(SPLASH_DURATION, show_main_window)
    
    sys.exit(app.exec_())