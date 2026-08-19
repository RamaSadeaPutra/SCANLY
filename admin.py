import sys
import csv
import os
import shutil
import re
import subprocess
from pathlib import Path
from datetime import datetime

from main import ScanlyWindow

from PySide6.QtCore import (
    Qt,
    QProcess,
    QDate,
    QTime,
)

from PySide6.QtGui import (
    QPixmap,
    QImage,
    QPainter,
    QFont,
)

try:
    from PySide6.QtSvg import QSvgRenderer
except Exception:
    QSvgRenderer = None

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QStackedWidget,
    QDialog,
    QMessageBox,
    QFileDialog,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QAbstractItemView,
    QSizePolicy,
    QFormLayout,
    QDateEdit,
    QTimeEdit,
)

# ============================================================
# PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

ATTENDANCE_FILE = BASE_DIR / "attendance.csv"
PEOPLE_FILE = BASE_DIR / "people.csv"

FACES_DIR = BASE_DIR / "faces"
MODEL_DIR = BASE_DIR / "face_model"

REGISTER_SCRIPT = BASE_DIR / "register_face.py"

REPORT_DIR = BASE_DIR / "reports"

MODEL_FILE = MODEL_DIR / "scanly_faces.yml"

# ============================================================
# ADMIN LOGIN
# ============================================================

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


# ============================================================
# STYLE
# ============================================================

STYLE = """
* {
    font-family: "Segoe UI";
}

QMainWindow {
    background: #f7f8fa;
}

QWidget {
    color: #172033;
}

QFrame#Sidebar {
    background: #ffffff;
    border-right: 1px solid #e8edf2;
}

QFrame#Topbar {
    background: #ffffff;
    border-bottom: 1px solid #e8edf2;
}

QLabel#Logo {
    font-size: 22px;
    font-weight: 800;
    color: #0f1724;
}

/* Sidebar title/subtitle */
QLabel#SidebarTitle {
    font-size: 16px;
    font-weight: 700;
    color: #0f1724;
}

QLabel#SidebarSubtitle {
    color: #6b7280;
    font-size: 12px;
}

QLabel#PageTitle {
    font-size: 30px;
    font-weight: 800;
    color: #0f1724;
}

QLabel#PageSubtitle {
    color: #6b7280;
    font-size: 13px;
}

QPushButton#NavButton {
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 10px 12px;
    text-align: left;
    font-size: 14px;
    font-weight: 700;
    color: #65707a;
}
QPushButton#NavButton:hover {
    background: #f4f7fb;
    color: #0f1724;
}
QPushButton#NavButton[active="true"] {
    background: transparent;
    color: #0f1724;
}

QPushButton#NavButton:hover {
    background: #f4f7fb;
    color: #0f1724;
}

QPushButton#NavButton[active="true"] {
    /* Match hover: subtle gray */
    background: #f4f7fb;
    color: #0f1724;
    border-left: 4px solid transparent;
}

QPushButton#Primary {
    background: #0f1724;
    color: white;
    border: none;
    border-radius: 10px;
    padding: 10px 16px;
    font-weight: 700;
}

QPushButton#Primary:hover {
    /* Align hover with sidebar subtle gray */
    background: #f4f7fb;
    color: #0f1724;
}

QPushButton#Secondary {
    background: #f3f6f9;
    color: #192029;
    border: none;
    border-radius: 10px;
    padding: 10px 16px;
    font-weight: 700;
}

QPushButton#Secondary:hover {
    background: #e9eef4;
}

QPushButton#Danger {
    background: #fff6f6;
    color: #b3261e;
    border: none;
    border-radius: 8px;
    padding: 8px 12px;
    font-weight: 700;
}

QPushButton#Danger:hover {
    background: #ffeaea;
}

QPushButton#Blue {
    background: #eef3ff;
    color: #2451d6;
    border: none;
    border-radius: 8px;
    padding: 8px 12px;
    font-weight: 700;
}

QPushButton#Blue:hover {
    background: #dfe8ff;
}

QLineEdit,
QComboBox,
QSpinBox {
    background: #f8fafc;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 10px 12px;
    min-height: 28px;
}

QLineEdit:focus,
QComboBox:focus,
QSpinBox:focus {
    background: white;
    border: 1px solid #c9d2df;
}

QFrame#Card {
    background: #ffffff;
    border: 1px solid #eef2f6;
    border-radius: 12px;
}

QFrame#Panel {
    background: #ffffff;
    border: 1px solid #eef2f6;
    border-radius: 12px;
}

/* Make QMessageBox / notifications use white background and match app theme */
QMessageBox {
    background: #ffffff;
    border: 1px solid #e6e9ee;
    border-radius: 8px;
}
QMessageBox QLabel, QMessageBox QLabel#qt_msgbox_label {
    color: #172033;
    font-size: 13px;
}
QMessageBox QPushButton {
    border-radius: 8px;
    padding: 6px 10px;
    min-width: 64px;
}
QMessageBox QPushButton#Primary {
    background: #0f1724;
    color: white;
}
QMessageBox QPushButton#Secondary {
    background: #f3f6f9;
    color: #192029;
}

QLabel#CardTitle {
    color: #6b7280;
    font-size: 12px;
    font-weight: 700;
}

QLabel#CardNumber {
    font-size: 30px;
    font-weight: 800;
    color: #0f1724;
}

/* Tables */
QTableWidget {
    background: white;
    border: none;
    gridline-color: #f3f6f9;
    selection-background-color: #e6efff;
    selection-color: #0f1724;
    alternate-background-color: #fbfdff;
}

QTableWidget::item {
    padding: 6px 10px;
    border-bottom: 1px solid #f7f9fb;
}

QTableWidget::item:selected {
    background: #e6efff;
    color: #0f1724;
}

QHeaderView::section {
    background: #fafbfc;
    border: none;
    border-bottom: 1px solid #e9eef4;
    padding: 14px 10px;
    color: #50606c;
    font-size: 11px;
    font-weight: 800;
}

QHeaderView::section:hover {
    background: #f1f5fb;
}

QTableCornerButton::section {
    background: transparent;
}

QCheckBox {
    font-size: 13px;
}

QLabel#StatusHadir {
    color: #0f7a3f;
    background: #eaf7ee;
    padding: 6px 10px;
    border-radius: 10px;
}

QLabel#StatusUnknown {
    color: #b3261e;
    background: #fff6f6;
    padding: 6px 10px;
    border-radius: 10px;
}

QPushButton#AttendanceButton {
    background: #111827;
    color: white;
    border: none;
    border-radius: 9px;
    padding: 12px 14px;
    font-size: 13px;
    font-weight: 700;
}

QPushButton#AttendanceButton:hover {
    background: #1f2937;
}

QPushButton#AttendanceButton:pressed {
    background: #374151;
}

QPushButton#Primary {
    background: #111827;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    font-weight: 700;
}

QPushButton#Primary:hover {
    background: #1f2937;
}

QPushButton#Primary:pressed {
    background: #374151;
}

QPushButton#Secondary {
    background: #f3f4f6;
    color: #374151;
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    font-weight: 600;
}

QPushButton#AttendanceManualButton {
    background: #f3f4f6;
    color: #111827;
    border: 1px solid #e5e7eb;
    border-radius: 9px;
    padding: 12px 14px;
    font-size: 13px;
    font-weight: 700;
    text-align: center;
}

QPushButton#AttendanceManualButton:hover {
    background: #e5e7eb;
}

QPushButton#AttendanceManualButton:pressed {
    background: #d1d5db;
}

"""


# ============================================================
# HELPERS
# ============================================================

def safe_folder_name(name):
    """
    Nama aman untuk folder dataset.
    """

    value = name.strip()

    value = re.sub(
        r'[<>:"/\\|?*]',
        "_",
        value
    )

    value = re.sub(
        r"\s+",
        "_",
        value
    )

    return value.strip(" ._")


# Helper to robustly load image into QPixmap, with Pillow fallback when available
try:
    from PIL import Image
except Exception:
    Image = None


def load_image_pixmap(path, width=None, height=None):
    """Try to load image at path into QPixmap. Handles high-DPI by rendering at devicePixelRatio.

    Returns QPixmap or None on failure.
    """

    p = Path(path)

    if not p.exists():
        return None

    # determine device pixel ratio (DPR) for high-DPI screens
    try:
        from PySide6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        dpr = screen.devicePixelRatio() if screen is not None else 1
    except Exception:
        dpr = 1

    # compute target physical pixel size
    target_w = int((width or 120) * dpr)
    target_h = int((height or 120) * dpr)

    # If SVG and QSvgRenderer available, render SVG to requested size for crisp output
    try:
        suffix = p.suffix.lower()
    except Exception:
        suffix = ''

    if suffix == '.svg' and QSvgRenderer is not None:
        try:
            renderer = QSvgRenderer(str(p))
            if not renderer.isValid():
                raise RuntimeError('invalid svg')
            pix = QPixmap(target_w, target_h)
            pix.fill(Qt.transparent)
            painter = QPainter(pix)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
            renderer.render(painter)
            painter.end()
            # set logical DPR so Qt will draw at correct size
            pix.setDevicePixelRatio(dpr)
            return pix
        except Exception as e:
            print('[DEBUG] SVG render failed for', p, '->', e)

    # First try with QPixmap native loader
    try:
        pix0 = QPixmap(str(p))
        if pix0 and not pix0.isNull():
            # scale the pixmap in physical pixels
            if width and height:
                pix = pix0.scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                pix.setDevicePixelRatio(dpr)
                return pix
            else:
                pix0.setDevicePixelRatio(dpr)
                return pix0
    except Exception:
        pass

    # Fallback using Pillow if available — use high-quality resize (LANCZOS)
    if Image is not None:
        try:
            img = Image.open(str(p)).convert('RGBA')
            orig_w, orig_h = img.size

            if width and height:
                # compute target size while preserving aspect ratio in logical pixels
                img_ratio = orig_w / orig_h
                target_ratio = float(width) / float(height)
                if img_ratio > target_ratio:
                    # image is wider; limit by width
                    logical_w = width
                    logical_h = int(round(width / img_ratio))
                else:
                    logical_h = height
                    logical_w = int(round(height * img_ratio))

                # convert to physical pixels for high-DPI
                phys_w = int(logical_w * dpr)
                phys_h = int(logical_h * dpr)

                # use LANCZOS for high-quality resampling
                img = img.resize((phys_w, phys_h), resample=Image.LANCZOS)
            else:
                phys_w, phys_h = img.size

            data = img.tobytes('raw', 'RGBA')
            qimg = QImage(data, img.width, img.height, QImage.Format_RGBA8888)
            pix = QPixmap.fromImage(qimg)
            pix.setDevicePixelRatio(dpr)
            return pix
        except Exception as e:
            print('[DEBUG] Pillow fallback failed for', p, '->', e)

    print('[DEBUG] Failed to load image as QPixmap:', p)
    return None


def load_people():
    """
    Membaca people.csv.
    """

    if not PEOPLE_FILE.exists():
        return []

    rows = []

    try:

        with open(
            PEOPLE_FILE,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:

                rows.append({
                    "ID": row.get("ID", "").strip(),
                    "Nama": row.get("Nama", "").strip(),
                    "Folder": row.get("Folder", "").strip(),
                    "Status": row.get("Status", "Aktif").strip(),
                })

    except Exception as error:

        print(
            "[ERROR] people.csv:",
            error
        )

    return rows


def save_people(rows):
    """
    Menulis people.csv.
    """

    with open(
        PEOPLE_FILE,
        "w",
        encoding="utf-8",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "ID",
                "Nama",
                "Folder",
                "Status"
            ]
        )

        writer.writeheader()

        writer.writerows(rows)


def ensure_people_file():

    if not PEOPLE_FILE.exists():

        save_people([])


def load_attendance():

    if not ATTENDANCE_FILE.exists():

        return []

    rows = []

    try:

        with open(
            ATTENDANCE_FILE,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:

                rows.append({
                    "Nama": row.get("Nama", "").strip(),
                    "Tanggal": row.get("Tanggal", "").strip(),
                    "Jam": row.get("Jam", "").strip(),
                    "Score": row.get("Score", "").strip(),
                    "Status": row.get("Status", "").strip(),
                })

    except Exception as error:

        print(
            "[ERROR] attendance.csv:",
            error
        )

    return rows


# ============================================================
# LOGIN
# ============================================================

# ============================================================
# LOGIN
# ============================================================

class LoginDialog(QDialog):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "Scanly - Admin Login"
        )

        self.setFixedSize(
            520,
            700
        )

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout(self)

        # Background putih
        self.setStyleSheet(
            "background: white;"
        )

        layout.setContentsMargins(
            45,
            40,
            45,
            35
        )

        layout.setSpacing(10)

        layout.addStretch()

        # ====================================================
        # LOGO
        # ====================================================

        candidates = [
            BASE_DIR / "logo@2x.png",
            BASE_DIR / "logo@2x.jpg",
            BASE_DIR / "logo@2x.jpeg",

            BASE_DIR / "logo.png",
            BASE_DIR / "logo.jpg",
            BASE_DIR / "logo.jpeg",

            BASE_DIR / "bahan" / "logo@2x.png",
            BASE_DIR / "bahan" / "logo@2x.jpg",
            BASE_DIR / "bahan" / "logo@2x.jpeg",

            BASE_DIR / "bahan" / "logo.png",
            BASE_DIR / "bahan" / "logo.jpg",
            BASE_DIR / "bahan" / "logo.jpeg",
        ]

        logo = None

        # Coba cari logo dari daftar file
        for p in candidates:

            if p.exists():

                pix = load_image_pixmap(
                    p,
                    170,
                    150
                )

                if pix is not None:

                    logo = QLabel()

                    logo.setPixmap(
                        pix
                    )

                    logo.setScaledContents(
                        False
                    )

                    logo.setSizePolicy(
                        QSizePolicy.Fixed,
                        QSizePolicy.Fixed
                    )

                    logo.setFixedSize(
                        190,
                        150
                    )

                    logo.setAlignment(
                         Qt.AlignLeft |
                        Qt.AlignCenter
                    )

                    break

        # ====================================================
        # FALLBACK LOGO
        # ====================================================

        if logo is None:

            search_dirs = [
                BASE_DIR,
                BASE_DIR / "bahan",
                BASE_DIR / "Bahan"
            ]

            found = None

            for directory in search_dirs:

                try:

                    if directory.exists():

                        for ext in (
                            "*.png",
                            "*.jpg",
                            "*.jpeg",
                            "*.jpe",
                            "*.bmp",
                            "*.svg"
                        ):

                            items = list(
                                directory.glob(ext)
                            )

                            if items:

                                found = items[0]

                                break

                except Exception:
                    pass

                if found:
                    break

            if found:

                pix = load_image_pixmap(
                    found,
                    170,
                    150
                )

                if pix is not None:

                    logo = QLabel()

                    logo.setPixmap(
                        pix
                    )

                    logo.setScaledContents(
                        False
                    )

                    logo.setSizePolicy(
                        QSizePolicy.Fixed,
                        QSizePolicy.Fixed
                    )

                    logo.setFixedSize(
                        170,
                        150
                    )

                    logo.setAlignment(
                        Qt.AlignCenter
                    )

                else:

                    print(
                        "[DEBUG] Found image but failed to load:",
                        found
                    )

        # ====================================================
        # JIKA LOGO TIDAK DITEMUKAN
        # ====================================================

        if logo is None:

            logo = QLabel("S")

            logo.setFixedSize(
                170,
                150
            )

            logo.setAlignment(
                Qt.AlignCenter
            )

            logo.setStyleSheet("""
                background: #0f1724;
                color: white;
                border-radius: 75px;
                font-size: 56px;
                font-weight: 800;
            """)

        # ====================================================
        # HEADER: logo above the title and subtitle (vertical layout)
        # ====================================================

        header_col = QVBoxLayout()
        header_col.setContentsMargins(0, 0, 0, 0)
        # keep small spacing between logo and title, and minimal between title and subtitle
        header_col.setSpacing(6)
        header_col.setAlignment(Qt.AlignHCenter)

        try:
            # Ensure logo widget uses its fixed size and no extra margins
            logo.setContentsMargins(0, 0, 0, 0)
            logo.setFixedSize(170, 150)
            logo.setAlignment(Qt.AlignCenter)
        except Exception:
            pass

        # Title centered under logo
        title_label = QLabel("SCANLY")
        # Use QFont to set absolute letter spacing (3 px) and font size/bold
        try:
            font = QFont()
            font.setPointSize(22)
            font.setBold(True)
            # AbsoluteSpacing uses pixels for spacing
            font.setLetterSpacing(QFont.AbsoluteSpacing, 5)
            title_label.setFont(font)
        except Exception:
            # Fallback to stylesheet if QFont methods are unavailable
            title_label.setStyleSheet("font-size:22px; font-weight:800; color:#0f1724; margin:0px; padding:0px;")

        title_label.setStyleSheet("color:#0f1724; margin:0px; padding:0px;")
        title_label.setAlignment(Qt.AlignCenter)
        try:
            title_label.setContentsMargins(0, 0, 0, 0)
        except Exception:
            pass

        # Use two separate labels to guarantee exactly two lines for subtitle
        subtitle_line1 = QLabel("Admin Portal Authentication ")
        subtitle_line1.setStyleSheet("color:#6b7280; font-size:13px; margin:0px; padding:0px;")
        subtitle_line1.setAlignment(Qt.AlignCenter)
        subtitle_line1.setWordWrap(False)
        subtitle_line1.setMaximumWidth(480)

        subtitle_line2 = QLabel("Aplikasi Absensi berbasis Face Recognition dan Liveness Detection")
        subtitle_line2.setStyleSheet("color:#6b7280; font-size:13px; margin:0px; padding:0px;")
        subtitle_line2.setAlignment(Qt.AlignCenter)
        subtitle_line2.setWordWrap(False)
        subtitle_line2.setMaximumWidth(480)

        header_col.addWidget(logo, 0, Qt.AlignCenter)
        header_col.addWidget(title_label, 0, Qt.AlignCenter)
        # small spacer between title and subtitle lines
        header_col.addWidget(subtitle_line1, 0, Qt.AlignCenter)
        header_col.addWidget(subtitle_line2, 0, Qt.AlignCenter)

        layout.addLayout(header_col)

        # ====================================================
        # JARAK HEADER KE USERNAME
        # ====================================================

        layout.addSpacing(
            22
        )

        # ====================================================
        # USERNAME
        # ====================================================

        label = QLabel(
            "USERNAME"
        )

        label.setStyleSheet("""
            color:#687083;
            font-size:10px;
            font-weight:700;
        """)

        layout.addWidget(
            label
        )

        self.username = QLineEdit()

        self.username.setPlaceholderText(
            "Enter your username"
        )

        self.username.setStyleSheet("""
            QLineEdit {
                border:1px solid #000;
                border-radius:6px;
                padding:8px;
                background:white;
                font-size:14px;
                color:#172033;
            }

            QLineEdit:focus {
                border:1px solid #000;
                background:white;
            }
        """)

        layout.addWidget(
            self.username
        )

        # ====================================================
        # PASSWORD
        # ====================================================

        label = QLabel(
            "PASSWORD"
        )

        label.setStyleSheet("""
            color:#687083;
            font-size:10px;
            font-weight:700;
        """)

        layout.addWidget(
            label
        )

        self.password = QLineEdit()

        self.password.setPlaceholderText(
            "Enter your password"
        )

        self.password.setEchoMode(
            QLineEdit.Password
        )

        self.password.returnPressed.connect(
            self.login
        )

        self.password.setStyleSheet("""
            QLineEdit {
                border:1px solid #000;
                border-radius:6px;
                padding:8px;
                background:white;
                font-size:14px;
                color:#172033;
            }

            QLineEdit:focus {
                border:1px solid #000;
                background:white;
            }
        """)

        layout.addWidget(
            self.password
        )

        # ====================================================
        # REMEMBER DEVICE
        # ====================================================

        layout.addSpacing(
            8
        )

        remember = QCheckBox(
            "Remember this device"
        )

        remember.setStyleSheet("""
            QCheckBox {
                color:#172033;
                font-size:13px;
            }

            QCheckBox::indicator {
                width:16px;
                height:16px;
                border:1px solid #000;
                border-radius:3px;
                background:white;
            }

            QCheckBox::indicator:checked {
                background:#0f1724;
            }
        """)

        layout.addWidget(
            remember
        )

        # ====================================================
        # LOGIN BUTTON
        # ====================================================

        layout.addSpacing(
            10
        )

        login_button = QPushButton(
            "LOGIN   →"
        )

        login_button.setObjectName(
            "Primary"
        )

        login_button.setStyleSheet("""
            QPushButton {
                background:#0f1724;
                color:white;
                border-radius:8px;
                min-height:36px;
                padding:6px 10px;
                font-weight:700;
                font-size:14px;
            }

            QPushButton:hover {
                background:#f4f7fb;
                color:#0f1724;
            }
        """)

        login_button.setMinimumHeight(
            36
        )

        login_button.clicked.connect(
            self.login
        )

        layout.addWidget(
            login_button
        )

        # ====================================================
        # SECURE SESSION
        # ====================================================

        secure = QLabel(
            "✓  Secure admin session"
        )

        secure.setAlignment(
            Qt.AlignCenter
        )

        secure.setStyleSheet("""
            color:#8a929f;
            font-size:11px;
        """)

        layout.addSpacing(
            12
        )

        layout.addWidget(
            secure
        )

        layout.addStretch()

    # ========================================================
    # LOGIN FUNCTION
    # ========================================================

    def login(self):

        if (
            self.username.text().strip()
            == ADMIN_USERNAME
            and
            self.password.text()
            == ADMIN_PASSWORD
        ):

            self.accept()

        else:

            QMessageBox.warning(
                self,
                "Login Failed",
                "Username atau password salah."
            )

            self.password.clear()
# ============================================================
# ADD PERSON
# ============================================================

class AddPersonDialog(QDialog):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle(
            "Scanly - Add Person"
        )

        self.setFixedSize(
            520,
            620
        )

        self.build_ui()

    def build_ui(self):

        # Outer layout holds a white panel so dialog background matches the app theme
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)

        panel = QFrame(self)
        panel.setObjectName("Panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(22, 22, 22, 22)
        panel_layout.setSpacing(10)

        title = QLabel("Add Person")
        title.setStyleSheet("""
            font-size:20px;
            font-weight:800;
        """)
        panel_layout.addWidget(title)

        subtitle = QLabel("Create a person record before registering the face.")
        subtitle.setStyleSheet("color:#6b7280; font-size:12px;")
        panel_layout.addWidget(subtitle)

        panel_layout.addSpacing(8)

        panel_layout.addWidget(QLabel("ID / NIM / Employee ID"))

        self.person_id = QLineEdit()
        self.person_id.setPlaceholderText("Contoh: EMP-001")
        self.person_id.setFixedHeight(34)
        panel_layout.addWidget(self.person_id)

        panel_layout.addWidget(QLabel("Nama Lengkap"))
        self.person_name = QLineEdit()
        self.person_name.setPlaceholderText("Contoh: Rama")
        self.person_name.setFixedHeight(34)
        panel_layout.addWidget(self.person_name)

        panel_layout.addWidget(QLabel("Folder Dataset"))
        folder_row = QHBoxLayout()
        self.folder_name = QLineEdit()
        self.folder_name.setPlaceholderText("Otomatis dari nama")
        self.folder_name.setFixedHeight(34)
        folder_row.addWidget(self.folder_name, 1)

        auto_button = QPushButton("AUTO")
        auto_button.setObjectName("Secondary")
        auto_button.setFixedWidth(80)
        auto_button.setFixedHeight(34)
        auto_button.clicked.connect(self.auto_folder)
        folder_row.addWidget(auto_button)

        panel_layout.addLayout(folder_row)

        note = QLabel("Foto wajah akan ditempatkan di folder faces/<nama>.")
        note.setStyleSheet("color:#6b7280; font-size:11px;")
        panel_layout.addWidget(note)

        # Photo preview and controls: upload file or capture from camera
        panel_layout.addSpacing(8)
        panel_layout.addWidget(QLabel("Foto (Upload atau Kamera)"))

        photo_row = QHBoxLayout()

        self.photo_preview = QLabel()
        self.photo_preview.setFixedSize(120, 120)
        self.photo_preview.setStyleSheet("background:#f3f5f8; border:1px dashed #d1d5db; border-radius:6px;")
        self.photo_preview.setAlignment(Qt.AlignCenter)
        photo_row.addWidget(self.photo_preview)

        photo_controls = QVBoxLayout()
        photo_controls.setSpacing(8)
        photo_controls.setContentsMargins(12, 0, 0, 0)

        upload_btn = QPushButton("UPLOAD FOTO")
        upload_btn.setObjectName("Secondary")
        upload_btn.setFixedHeight(30)
        upload_btn.setFixedWidth(180)
        upload_btn.clicked.connect(self.upload_photo)
        photo_controls.addWidget(upload_btn)

        cam_btn = QPushButton("AMBIL DARI KAMERA")
        cam_btn.setObjectName("Secondary")
        cam_btn.setFixedHeight(30)
        cam_btn.setFixedWidth(180)
        cam_btn.clicked.connect(self.capture_camera)
        photo_controls.addWidget(cam_btn)

        # small instruction under buttons
        instr = QLabel("Tekan SPACE untuk mengambil foto dari kamera, ESC untuk batal.")
        instr.setStyleSheet("color:#6b7280; font-size:11px;")
        photo_controls.addWidget(instr)

        photo_controls.addStretch()
        photo_row.addLayout(photo_controls)

        panel_layout.addLayout(photo_row)

        # extra spacing so the buttons sit lower and don't overlap photo controls
        panel_layout.addSpacing(12)
        panel_layout.addStretch()

        buttons = QHBoxLayout()
        cancel = QPushButton("BATAL")
        cancel.setObjectName("Secondary")
        cancel.setFixedWidth(90)
        cancel.setFixedHeight(34)
        cancel.clicked.connect(self.reject)

        save = QPushButton("TAMBAH ORANG")
        save.setObjectName("Primary")
        save.setFixedWidth(150)
        save.setFixedHeight(34)
        save.clicked.connect(self.save)

        buttons.addWidget(cancel)
        buttons.addStretch()
        buttons.addWidget(save)

        panel_layout.addLayout(buttons)

        outer.addWidget(panel)

    def auto_folder(self):

        name = (
            self.person_name
            .text()
            .strip()
        )

        if name:

            self.folder_name.setText(
                safe_folder_name(name)
            )

    def upload_photo(self):

        fname, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih Foto",
            str(BASE_DIR),
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )

        if not fname:
            return

        self.photo_path = fname

        pix = load_image_pixmap(fname, 140, 140)
        if pix is not None:
            self.photo_preview.setPixmap(pix)
            self.photo_preview.setScaledContents(True)

    def capture_camera(self):

        try:
            import cv2
        except Exception:
            QMessageBox.warning(
                self,
                "Kamera Tidak Tersedia",
                "OpenCV tidak terpasang. Install dengan: pip install opencv-python"
            )
            return

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            QMessageBox.warning(self, "Kamera Tidak Tersedia", "Tidak dapat membuka kamera.")
            return

        QMessageBox.information(self, "Instruksi", "Tekan SPACE untuk mengambil foto, ESC untuk batal.\n\nJendela kamera akan muncul.")

        captured = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            # mirror the frame so camera behaves like a selfie (mirrored preview)
            display = cv2.flip(frame, 1)
            cv2.imshow("Camera - Tekan SPACE untuk ambil", display)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                break
            if key == 32:  # SPACE -> start 3-shot capture
                # brief countdown / capture sequence
                for i in range(3):
                    # show countdown overlay
                    try:
                        overlay = display.copy()
                        cv2.putText(overlay, f"Mengambil {i+1}/3", (10,40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255,255,255), 2, cv2.LINE_AA)
                        cv2.imshow("Camera - Tekan SPACE untuk ambil", overlay)
                    except Exception:
                        pass
                    # wait a short moment to let camera update
                    cv2.waitKey(400)
                    ret2, frame2 = cap.read()
                    if not ret2:
                        continue
                    img_shot = cv2.flip(frame2, 1)
                    captured.append(img_shot.copy())
                break

        cap.release()
        cv2.destroyAllWindows()

        if not captured:
            return

        # keep captured images in memory (do not write temp files to project dir)
        self.captured_images = captured
        try:
            # convert first captured image to QPixmap for preview without saving to disk
            img = self.captured_images[0]
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pix = QPixmap.fromImage(qimg).scaled(140, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.photo_preview.setPixmap(pix)
            self.photo_preview.setScaledContents(True)
        except Exception as e:
            QMessageBox.warning(self, "Kamera Error", str(e))

    def save(self):

        person_id = (
            self.person_id
            .text()
            .strip()
        )

        name = (
            self.person_name
            .text()
            .strip()
        )

        folder = (
            self.folder_name
            .text()
            .strip()
        )

        if not person_id:

            QMessageBox.warning(
                self,
                "Data Belum Lengkap",
                "ID wajib diisi."
            )

            return

        if not name:

            QMessageBox.warning(
                self,
                "Data Belum Lengkap",
                "Nama wajib diisi."
            )

            return

        if not folder:

            folder = safe_folder_name(
                name
            )

        folder = safe_folder_name(
            folder
        )

        if not folder:

            QMessageBox.warning(
                self,
                "Folder Tidak Valid",
                "Nama folder tidak valid."
            )

            return

        ensure_people_file()

        people = load_people()

        for row in people:

            if (
                row["ID"].lower()
                == person_id.lower()
            ):

                QMessageBox.warning(
                    self,
                    "ID Sudah Ada",
                    "ID tersebut sudah terdaftar."
                )

                return

            if (
                row["Nama"].lower()
                == name.lower()
            ):

                QMessageBox.warning(
                    self,
                    "Nama Sudah Ada",
                    "Nama tersebut sudah terdaftar."
                )

                return

        dataset_folder = (
            FACES_DIR
            / folder
        )

        dataset_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        # copy provided photo(s) into dataset folder as "1.jpg", "2.jpg", ...
        try:
            # try to import cv2 and PIL.Image for robust saving
            try:
                import cv2 as _cv2
            except Exception:
                _cv2 = None
            try:
                from PIL import Image as _PILImage
            except Exception:
                _PILImage = None

            def _save_with_cv2(path, arr):
                try:
                    return _cv2.imwrite(str(path), arr)
                except Exception:
                    return False

            def _save_with_pil(path, arr):
                # arr expected BGR or RGB uint8
                try:
                    if arr.ndim == 3 and arr.shape[2] == 3:
                        # convert BGR->RGB
                        rgb = arr[..., ::-1]
                    elif arr.ndim == 3 and arr.shape[2] == 4:
                        # BGRA -> RGBA -> convert to RGB
                        rgb = arr[..., :3][..., ::-1]
                    else:
                        rgb = arr
                    img = _PILImage.fromarray(rgb)
                    img.save(str(path), format='JPEG', quality=90)
                    return True
                except Exception:
                    return False

            if hasattr(self, "captured_images") and self.captured_images:
                for i, img in enumerate(self.captured_images, start=1):
                    dest = dataset_folder / f"{i}.jpg"
                    arr = img
                    # ensure uint8
                    try:
                        import numpy as _np
                        if not isinstance(arr, _np.ndarray):
                            raise TypeError("captured image is not ndarray")
                        if arr.dtype != _np.uint8:
                            if _np.issubdtype(arr.dtype, _np.floating):
                                arr = (arr * 255).astype(_np.uint8)
                            else:
                                arr = arr.astype(_np.uint8)
                    except Exception:
                        pass

                    saved = False
                    if _cv2 is not None:
                        # if image has 3 or 4 channels and looks like RGB but in BGR order from camera
                        saved = _save_with_cv2(dest, arr)
                    if not saved and _PILImage is not None:
                        saved = _save_with_pil(dest, arr)
                    if not saved:
                        raise RuntimeError(f"Gagal menyimpan frame {i} ke {dest}")

            elif hasattr(self, "photo_paths") and self.photo_paths:
                for i, src_path in enumerate(self.photo_paths, start=1):
                    src = Path(src_path)
                    if src.exists():
                        dest = dataset_folder / f"{i}.jpg"
                        shutil.copy(str(src), str(dest))
                # cleanup temporary files we created in temp dir
                try:
                    for p in getattr(self, 'photo_paths', []):
                        try:
                            Path(p).unlink()
                        except Exception:
                            pass
                except Exception:
                    pass
            elif hasattr(self, "photo_path") and self.photo_path:
                src = Path(self.photo_path)
                if src.exists():
                    dest = dataset_folder / "1.jpg"
                    shutil.copy(str(src), str(dest))
        except Exception as e:
            # non-fatal: inform user but continue
            QMessageBox.warning(self, "Foto Tidak Tersimpan", f"Gagal menyimpan foto ke dataset: {e}")

        people.append({
            "ID": person_id,
            "Nama": name,
            "Folder": f"faces/{folder}",
            "Status": "Aktif"
        })

        save_people(
            people
        )

        QMessageBox.information(
            self,
            "Berhasil",
            f"Data {name} berhasil ditambahkan.\n\n"
            f"Dataset:\n{dataset_folder}"
        )

        self.accept()



# ============================================================
# CARD
# ============================================================

def create_card(
    title,
    number,
    icon,
    badge=""
):

    card = QFrame()

    card.setObjectName(
        "Card"
    )

    layout = QVBoxLayout(card)

    layout.setContentsMargins(
        20,
        18,
        20,
        18
    )

    top = QHBoxLayout()

    icon_label = QLabel(
        icon
    )

    icon_label.setFixedSize(
        40,
        40
    )

    icon_label.setAlignment(
        Qt.AlignCenter
    )

    icon_label.setStyleSheet("""
        background:#f3f5f8;
        border-radius:8px;
        font-size:17px;
        font-weight:700;
    """)

    top.addWidget(
        icon_label
    )

    top.addStretch()

    if badge:

        badge_label = QLabel(
            badge
        )

        badge_label.setStyleSheet("""
            background:#f2f4f7;
            color:#6c7481;
            padding:4px 7px;
            border-radius:7px;
            font-size:10px;
        """)

        top.addWidget(
            badge_label
        )

    layout.addLayout(
        top
    )

    title_label = QLabel(
        title.upper()
    )

    title_label.setObjectName(
        "CardTitle"
    )

    layout.addWidget(
        title_label
    )

    number_label = QLabel(
        str(number)
    )

    number_label.setObjectName(
        "CardNumber"
    )

    layout.addWidget(
        number_label
    )

    return card

# ============================================================
# MANUAL ATTENDANCE DIALOG
# ============================================================

class ManualAttendanceDialog(QDialog):
    def __init__(self, parent=None, people=None):

        super().__init__(parent)

        self.people = people or []

        self.setWindowTitle(
            "Scanly - Tambah Absensi Manual"
        )

        self.setFixedWidth(560)
        self.setMinimumHeight(500)

        self.setObjectName(
            "ManualAttendanceDialog"
        )

        self.setStyleSheet(
            """
            QDialog#ManualAttendanceDialog {
                background-color: #f8fafc;
                color: #111827;
            }

            QDialog#ManualAttendanceDialog QLabel {
                color: #111827;
                background-color: transparent;
            }

            QDialog#ManualAttendanceDialog QLabel#DialogTitle {
                color: #0f172a;
                font-size: 24px;
                font-weight: 700;
            }

            QDialog#ManualAttendanceDialog QLabel#DialogSubtitle {
                color: #64748b;
                font-size: 13px;
            }

            QDialog#ManualAttendanceDialog QComboBox {
                background-color: #ffffff;
                color: #1e293b;
                border: 1px solid #dbe1e8;
                border-radius: 8px;
                padding: 8px 12px;
                min-height: 42px;
                font-size: 13px;
            }

            QDialog#ManualAttendanceDialog QComboBox:hover {
                border: 1px solid #94a3b8;
            }

            QDialog#ManualAttendanceDialog QComboBox:focus {
                border: 2px solid #2563eb;
            }
            

            QDialog#ManualAttendanceDialog QLabel#DateTimeLabel {
                background-color: #ffffff;
                color: #334155;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 8px 12px;
                min-height: 42px;
                font-size: 13px;
                font-weight: 600;
            }

            QDialog#ManualAttendanceDialog QLabel#StatusPreview {
                background-color: #f1f5f9;
                color: #334155;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                padding: 12px;
                font-size: 14px;
                font-weight: 600;
            }

            QDialog#ManualAttendanceDialog QPushButton#Secondary {
                background-color: #ffffff;
                color: #334155;
                border: 1px solid #dbe1e8;
                border-radius: 8px;
                padding: 10px 20px;
                min-height: 42px;
                font-size: 13px;
                font-weight: 600;
            }

            QDialog#ManualAttendanceDialog QPushButton#Secondary:hover {
                background-color: #f1f5f9;
            }

            QDialog#ManualAttendanceDialog QPushButton#Primary {
                background-color: #111827;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 10px 22px;
                min-height: 42px;
                font-size: 13px;
                font-weight: 700;
            }

            QDialog#ManualAttendanceDialog QPushButton#Primary:hover {
                background-color: #1f2937;
            }
            """
        )

        self.build_ui()

    def build_ui(self):

        # ============================================================
        # MAIN LAYOUT
        # ============================================================

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            30,
            25,
            30,
            25
        )

        layout.setSpacing(16)

        # ============================================================
        # TITLE
        # ============================================================

        title = QLabel(
            "Tambah Absensi Manual"
        )

        title.setObjectName(
            "DialogTitle"
        )

        layout.addWidget(
            title
        )

        # ============================================================
        # SUBTITLE
        # ============================================================

        subtitle = QLabel(
            "Catat absensi tanpa menggunakan kamera."
        )

        subtitle.setObjectName(
            "DialogSubtitle"
        )

        layout.addWidget(
            subtitle
        )

        # ============================================================
        # FORM
        # ============================================================

        form = QFormLayout()

        form.setLabelAlignment(
            Qt.AlignLeft | Qt.AlignVCenter
        )

        form.setFormAlignment(
            Qt.AlignTop
        )

        form.setHorizontalSpacing(
            14
        )

        form.setVerticalSpacing(
            14
        )

        # ============================================================
        # PENGGUNA
        # ============================================================

        self.person_combo = QComboBox()

        self.person_combo.setMinimumHeight(
            44
        )

        self.person_combo.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed
        )

        self.person_combo.setMaxVisibleItems(
            6
        )

        self.person_combo.setStyleSheet(
            """
            QComboBox {
                background-color: #ffffff;
                color: #172033;
                border: 1px solid #d9e0e7;
                border-radius: 9px;
                padding: 0px 42px 0px 14px;
                min-height: 44px;
                font-size: 14px;
            }

            QComboBox:hover {
                border: 1px solid #aeb9c6;
                background-color: #ffffff;
            }

            QComboBox:focus {
                border: 2px solid #2563eb;
                background-color: #ffffff;
            }

            QComboBox::drop-down {
                width: 40px;
                border: none;
                background-color: transparent;
            }

            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #172033;
                border: 1px solid #d9e0e7;
                outline: none;
                padding: 5px;
                selection-background-color: #eaf1ff;
                selection-color: #1d4ed8;
            }

            QComboBox QAbstractItemView::item {
                background-color: #ffffff;
                color: #172033;
                border: none;
                border-radius: 7px;
                padding: 10px 12px;
                min-height: 34px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #f3f6fa;
                color: #172033;
            }

            QComboBox QAbstractItemView::item:selected {
                background-color: #eaf1ff;
                color: #1d4ed8;
            }
            """
        )

        # ============================================================
        # ISI DATA PENGGUNA
        # ============================================================

        for person in self.people:

            name = str(
                person.get(
                    "Nama",
                    ""
                )
            ).strip()

            person_id = str(
                person.get(
                    "ID",
                    ""
                )
            ).strip()

            if not name:
                continue

            if person_id:

                display_name = (
                    f"{name} ({person_id})"
                )

            else:

                display_name = name

            self.person_combo.addItem(
                display_name,
                person
            )

        form.addRow(
            "Pengguna",
            self.person_combo
        )

        # ============================================================
        # WAKTU ABSENSI
        # OTOMATIS - TIDAK BISA DIEDIT
        # ============================================================

        self.attendance_datetime = datetime.now()

        self.datetime_label = QLabel(
            self.attendance_datetime.strftime(
                "%d-%m-%Y %H:%M:%S"
            )
        )

        self.datetime_label.setObjectName(
            "DateTimeLabel"
        )

        self.datetime_label.setAlignment(
            Qt.AlignVCenter | Qt.AlignLeft
        )

        self.datetime_label.setMinimumHeight(
            44
        )

        self.datetime_label.setStyleSheet(
            """
            QLabel {
                background-color: #ffffff;
                color: #172033;
                border: 1px solid #d9e0e7;
                border-radius: 9px;
                padding: 0px 14px;
                min-height: 44px;
                font-size: 14px;
            }
            """
        )

        form.addRow(
            "Waktu Absensi",
            self.datetime_label
        )

        # ============================================================
        # JENIS ABSENSI
        # ============================================================

        self.type_combo = QComboBox()

        self.type_combo.setMinimumHeight(
            44
        )

        self.type_combo.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed
        )

        self.type_combo.setMaxVisibleItems(
            2
        )

        self.type_combo.setStyleSheet(
            """
            QComboBox {
                background-color: #ffffff;
                color: #172033;
                border: 1px solid #d9e0e7;
                border-radius: 9px;
                padding: 0px 42px 0px 14px;
                min-height: 44px;
                font-size: 14px;
            }

            QComboBox:hover {
                border: 1px solid #aeb9c6;
                background-color: #ffffff;
            }

            QComboBox:focus {
                border: 2px solid #2563eb;
                background-color: #ffffff;
            }

            QComboBox::drop-down {
                width: 40px;
                border: none;
                background-color: transparent;
            }

            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #172033;
                border: 1px solid #d9e0e7;
                outline: none;
                padding: 5px;
                selection-background-color: #eaf1ff;
                selection-color: #1d4ed8;
            }

            QComboBox QAbstractItemView::item {
                background-color: #ffffff;
                color: #172033;
                border: none;
                border-radius: 7px;
                padding: 10px 12px;
                min-height: 34px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #f3f6fa;
                color: #172033;
            }

            QComboBox QAbstractItemView::item:selected {
                background-color: #eaf1ff;
                color: #1d4ed8;
            }
            """
        )

        self.type_combo.addItem(
            "Masuk"
        )

        self.type_combo.addItem(
            "Pulang"
        )

        self.type_combo.currentIndexChanged.connect(
            self.update_status_preview
        )

        form.addRow(
            "Jenis",
            self.type_combo
        )

        # ============================================================
        # MASUKKAN FORM KE MAIN LAYOUT
        #
        # INI PENTING.
        # Jangan membuat QFormLayout baru setelah bagian ini.
        # ============================================================

        layout.addLayout(
            form
        )

        # ============================================================
        # STATUS PREVIEW
        # ============================================================

        self.status_preview = QLabel(
            ""
        )

        self.status_preview.setObjectName(
            "StatusPreview"
        )

        self.status_preview.setMinimumHeight(
            66
        )

        self.status_preview.setAlignment(
            Qt.AlignVCenter | Qt.AlignLeft
        )

        self.status_preview.setWordWrap(
            True
        )

        layout.addWidget(
            self.status_preview
        )

        # ============================================================
        # SPACER
        # ============================================================

        layout.addStretch(
            1
        )

        # ============================================================
        # BUTTONS
        # ============================================================

        buttons = QHBoxLayout()

        buttons.setSpacing(
            12
        )

        buttons.addStretch(
            1
        )

        # ------------------------------------------------------------
        # BATAL
        # ------------------------------------------------------------

        cancel_button = QPushButton(
            "BATAL"
        )

        cancel_button.setObjectName(
            "Secondary"
        )

        cancel_button.setMinimumSize(
            100,
            48
        )

        cancel_button.setCursor(
            Qt.PointingHandCursor
        )

        cancel_button.clicked.connect(
            self.reject
        )

        buttons.addWidget(
            cancel_button
        )

        # ------------------------------------------------------------
        # SIMPAN
        # ------------------------------------------------------------

        save_button = QPushButton(
            "SIMPAN ABSENSI"
        )

        save_button.setObjectName(
            "Primary"
        )

        save_button.setMinimumSize(
            190,
            48
        )

        save_button.setCursor(
            Qt.PointingHandCursor
        )

        save_button.clicked.connect(
            self.save_manual
        )

        buttons.addWidget(
            save_button
        )

        layout.addLayout(
            buttons
        )

        # ============================================================
        # UPDATE STATUS AWAL
        # ============================================================

        self.update_status_preview()

       # ========================================================
    # HITUNG STATUS
    # ========================================================

    def update_status_preview(self):

        now = self.attendance_datetime

        attendance_type = (
            self.type_combo.currentText()
        )

        if attendance_type == "Masuk":

            current_time = now.time()

            start_time = datetime.strptime(
                "08:00",
                "%H:%M"
            ).time()

            late_time = datetime.strptime(
                "08:30",
                "%H:%M"
            ).time()

            if current_time < start_time:

                status = (
                    "⚠  Belum masuk waktu absensi"
                )

                self.status_preview.setStyleSheet(
                    """
                    background-color: #fff7ed;
                    color: #c2410c;
                    border: 1px solid #fed7aa;
                    border-radius: 10px;
                    padding: 14px;
                    font-size: 14px;
                    font-weight: 600;
                    """
                )

            elif current_time <= late_time:

                status = (
                    "✓  Tepat Waktu"
                )

                self.status_preview.setStyleSheet(
                    """
                    background-color: #ecfdf5;
                    color: #047857;
                    border: 1px solid #a7f3d0;
                    border-radius: 10px;
                    padding: 14px;
                    font-size: 14px;
                    font-weight: 600;
                    """
                )

            else:

                status = (
                    "⚠  Terlambat"
                )

                self.status_preview.setStyleSheet(
                    """
                    background-color: #fffbeb;
                    color: #b45309;
                    border: 1px solid #fde68a;
                    border-radius: 10px;
                    padding: 14px;
                    font-size: 14px;
                    font-weight: 600;
                    """
                )

        else:

            start_time = datetime.strptime(
                "16:00",
                "%H:%M"
            ).time()

            end_time = datetime.strptime(
                "18:00",
                "%H:%M"
            ).time()

            current_time = now.time()

            if current_time < start_time:

                status = (
                    "⚠  Belum waktunya absen pulang"
                )

                self.status_preview.setStyleSheet(
                    """
                    background-color: #fff7ed;
                    color: #c2410c;
                    border: 1px solid #fed7aa;
                    border-radius: 10px;
                    padding: 14px;
                    font-size: 14px;
                    font-weight: 600;
                    """
                )

            elif current_time <= end_time:

                status = (
                    "✓  Absen Pulang"
                )

                self.status_preview.setStyleSheet(
                    """
                    background-color: #ecfdf5;
                    color: #047857;
                    border: 1px solid #a7f3d0;
                    border-radius: 10px;
                    padding: 14px;
                    font-size: 14px;
                    font-weight: 600;
                    """
                )

            else:

                status = (
                    "⚠  Waktu absen pulang telah berakhir"
                )

                self.status_preview.setStyleSheet(
                    """
                    background-color: #fef2f2;
                    color: #b91c1c;
                    border: 1px solid #fecaca;
                    border-radius: 10px;
                    padding: 14px;
                    font-size: 14px;
                    font-weight: 600;
                    """
                )

        self.status_preview.setText(
            status
        )
    # ========================================================
    # SIMPAN ABSENSI
    # ========================================================

    def save_manual(self):

        # ====================================================
        # CEK PENGGUNA
        # ====================================================

        if (
            self.person_combo.currentIndex()
            < 0
        ):

            QMessageBox.warning(
                self,
                "Data Tidak Lengkap",
                "Pilih pengguna terlebih dahulu."
            )

            return

        person = (
            self.person_combo.currentData()
        )

        if not person:

            QMessageBox.warning(
                self,
                "Data Tidak Valid",
                "Data pengguna tidak ditemukan."
            )

            return

        # ====================================================
        # DATA DASAR
        # ====================================================

        name = str(
            person.get(
                "Nama",
                ""
            )
        ).strip()

        if not name:

            QMessageBox.warning(
                self,
                "Data Tidak Valid",
                "Nama pengguna kosong."
            )

            return

        attendance_type = (
            self.type_combo.currentText()
        )

        # ====================================================
        # WAKTU OTOMATIS
        # ====================================================

        attendance_datetime = (
            self.attendance_datetime
        )

        date = (
            attendance_datetime.strftime(
                "%Y-%m-%d"
            )
        )

        jam = (
            attendance_datetime.strftime(
                "%H:%M:%S"
            )
        )

        hour = (
            attendance_datetime.hour
        )

        minute = (
            attendance_datetime.minute
        )

        second = (
            attendance_datetime.second
        )

        current_seconds = (
            hour * 3600
            + minute * 60
            + second
        )

        # ====================================================
        # BATAS WAKTU
        # ====================================================

        start_in = (
            8 * 3600
        )

        on_time_end = (
            8 * 3600
            + 30 * 60
        )

        return_start = (
            16 * 3600
        )

        return_end = (
            18 * 3600
        )

        # ====================================================
        # TENTUKAN STATUS
        # ====================================================

        if attendance_type == "Masuk":

            # -----------------------------------------------
            # SEBELUM 08:00
            # -----------------------------------------------

            if current_seconds < start_in:

                QMessageBox.warning(
                    self,
                    "Belum Dibuka",
                    (
                        "Absen masuk belum dibuka.\n\n"
                        "Absen masuk mulai pukul 08:00."
                    )
                )

                return

            # -----------------------------------------------
            # 08:00 - 08:30
            # -----------------------------------------------

            elif current_seconds <= on_time_end:

                status = "Tepat Waktu"

            # -----------------------------------------------
            # 08:31 - 15:59
            # -----------------------------------------------

            elif current_seconds < return_start:

                status = "Terlambat"

            # -----------------------------------------------
            # 16:00+
            # -----------------------------------------------

            else:

                QMessageBox.warning(
                    self,
                    "Absen Masuk Ditutup",
                    (
                        "Waktu absen masuk sudah ditutup."
                    )
                )

                return

        else:

            # -----------------------------------------------
            # SEBELUM 16:00
            # -----------------------------------------------

            if current_seconds < return_start:

                QMessageBox.warning(
                    self,
                    "Belum Bisa Pulang",
                    (
                        "Absen pulang belum dibuka.\n\n"
                        "Absen pulang mulai pukul 16:00."
                    )
                )

                return

            # -----------------------------------------------
            # 16:00 - 18:00
            # -----------------------------------------------

            elif current_seconds <= return_end:

                status = "Pulang"

            # -----------------------------------------------
            # SETELAH 18:00
            # -----------------------------------------------

            else:

                QMessageBox.warning(
                    self,
                    "Absen Pulang Ditutup",
                    (
                        "Waktu absen pulang sudah ditutup.\n\n"
                        "Batas absen pulang adalah pukul 18:00."
                    )
                )

                return

        # ====================================================
        # BACA ATTENDANCE CSV
        # ====================================================

        existing_rows = []

        try:

            if ATTENDANCE_FILE.exists():

                with open(
                    ATTENDANCE_FILE,
                    "r",
                    encoding="utf-8-sig",
                    newline=""
                ) as file:

                    reader = csv.DictReader(
                        file
                    )

                    existing_rows = list(
                        reader
                    )

        except Exception as error:

            QMessageBox.critical(
                self,
                "Gagal Membaca Data",
                (
                    "File attendance.csv tidak dapat "
                    "dibaca.\n\n"
                    f"Error:\n{error}"
                )
            )

            return

        # ====================================================
        # CEK ABSENSI HARI INI
        # ====================================================

        has_entry = False

        has_exit = False

        for row in existing_rows:

            row_name = str(
                row.get(
                    "Nama",
                    ""
                )
            ).strip()

            row_date = str(
                row.get(
                    "Tanggal",
                    ""
                )
            ).strip()

            row_status = str(
                row.get(
                    "Status",
                    ""
                )
            ).strip()

            if (
                row_name == name
                and row_date == date
            ):

                if row_status in (
                    "Tepat Waktu",
                    "Terlambat",
                    "Hadir"
                ):

                    has_entry = True

                if row_status == "Pulang":

                    has_exit = True

        # ====================================================
        # CEK DUPLIKAT MASUK
        # ====================================================

        if attendance_type == "Masuk":

            if has_entry:

                QMessageBox.warning(
                    self,
                    "Sudah Absen",
                    (
                        f"{name} sudah memiliki "
                        f"absen masuk pada {date}."
                    )
                )

                return

        # ====================================================
        # CEK PULANG
        # ====================================================

        if attendance_type == "Pulang":

            if not has_entry:

                QMessageBox.warning(
                    self,
                    "Belum Absen Masuk",
                    (
                        f"{name} belum memiliki "
                        f"absen masuk pada {date}.\n\n"
                        "Absen pulang hanya dapat dilakukan "
                        "setelah absen masuk."
                    )
                )

                return

            if has_exit:

                QMessageBox.warning(
                    self,
                    "Sudah Absen Pulang",
                    (
                        f"{name} sudah memiliki "
                        f"absen pulang pada {date}."
                    )
                )

                return

        # ====================================================
        # KONFIRMASI
        # ====================================================

        confirmation = QMessageBox.question(
            self,
            "Konfirmasi Absensi",
            (
                "Simpan absensi manual?\n\n"
                f"Nama     : {name}\n"
                f"Tanggal  : {date}\n"
                f"Jam      : {jam}\n"
                f"Jenis    : {attendance_type}\n"
                f"Status   : {status}\n\n"
                "Tanggal dan jam menggunakan waktu "
                "sistem saat dialog dibuka."
            ),
            QMessageBox.Yes
            | QMessageBox.No
        )

        if (
            confirmation
            != QMessageBox.Yes
        ):

            return

        # ====================================================
        # SIMPAN
        # ====================================================

        file_exists = (
            ATTENDANCE_FILE.exists()
        )

        try:

            with open(
                ATTENDANCE_FILE,
                "a",
                newline="",
                encoding="utf-8-sig"
            ) as file:

                writer = csv.writer(
                    file
                )

                if not file_exists:

                    writer.writerow([
                        "Nama",
                        "Tanggal",
                        "Jam",
                        "Score",
                        "Status"
                    ])

                writer.writerow([
                    name,
                    date,
                    jam,
                    "Manual",
                    status
                ])

        except Exception as error:

            QMessageBox.critical(
                self,
                "Gagal Menyimpan",
                (
                    "Absensi manual gagal disimpan.\n\n"
                    f"Error:\n{error}"
                )
            )

            return

        # ====================================================
        # BERHASIL
        # ====================================================

        QMessageBox.information(
            self,
            "Absensi Berhasil",
            (
                "Absensi manual berhasil disimpan.\n\n"
                f"Nama   : {name}\n"
                f"Waktu  : {date} {jam}\n"
                f"Status : {status}"
            )
        )

        self.accept()
# ============================================================
# ADMIN WINDOW
# ============================================================


class AdminWindow(QMainWindow):

        # ========================================================
    # TAMBAH ABSENSI MANUAL
    # ========================================================

    def add_manual_attendance(self):

        self.people = load_people()

        if not self.people:

            QMessageBox.warning(
                self,
                "Tidak Ada Pengguna",
                (
                    "Belum ada pengguna terdaftar.\n\n"
                    "Tambahkan pengguna terlebih dahulu "
                    "di halaman People."
                )
            )

            return

        dialog = ManualAttendanceDialog(
            self,
            self.people
        )

        if (
            dialog.exec()
            == QDialog.Accepted
        ):

            self.refresh_all()

            # Pastikan halaman Attendance menampilkan
            # data terbaru.
            self.stack.setCurrentIndex(
                2
            )

            self.fill_attendance_table(
                self.attendance
            )

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "Scanly - Admin Dashboard"
        )

        self.resize(
            1350,
            820
        )

        self.setMinimumSize(
            1100,
            700
        )

        self.people = []
        self.attendance = []

        self.build_ui()

        self.refresh_all()

        # ========================================================
    # MULAI ABSENSI
    # ========================================================

    def open_attendance_scanner(self):

        try:

            # Kalau window absensi masih terbuka,
            # jangan membuat kamera kedua.
            if hasattr(
                self,
                "attendance_window"
            ):

                if (
                    self.attendance_window
                    is not None
                    and self.attendance_window.isVisible()
                ):

                    self.attendance_window.raise_()
                    self.attendance_window.activateWindow()

                    return

            # Buat window Scanly
            self.attendance_window = ScanlyWindow()

            # Saat window ditutup,
            # refresh dashboard otomatis.
            self.attendance_window.destroyed.connect(
                self.refresh_after_attendance
            )

            self.attendance_window.show()

            self.attendance_window.raise_()

            self.attendance_window.activateWindow()

        except Exception as error:

            QMessageBox.critical(
                self,
                "Gagal Membuka Absensi",
                (
                    "Kamera absensi tidak dapat dibuka.\n\n"
                    f"Detail error:\n{error}"
                )
            )

    # ========================================================
    # REFRESH SETELAH ABSENSI
    # ========================================================

    def refresh_after_attendance(self):

        self.people = load_people()

        self.attendance = load_attendance()

        self.update_dashboard_cards()

        self.fill_attendance_table(
            self.attendance
        )

        self.load_people_table()

    # ========================================================
    # BUILD
    # ========================================================

    def build_ui(self):

        central = QWidget()

        self.setCentralWidget(
            central
        )

        main_layout = QHBoxLayout(
            central
        )

        main_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        main_layout.setSpacing(
            0
        )

        main_layout.addWidget(
            self.create_sidebar()
        )

        right = QWidget()

        right_layout = QVBoxLayout(
            right
        )

        right_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        right_layout.setSpacing(
            0
        )

        right_layout.addWidget(
            self.create_topbar()
        )

        self.stack = QStackedWidget()

        self.stack.addWidget(
            self.create_dashboard()
        )

        self.stack.addWidget(
            self.create_people()
        )

        self.stack.addWidget(
            self.create_attendance()
        )

        self.stack.addWidget(
            self.create_reports()
        )

        self.stack.addWidget(
            self.create_settings()
        )

        right_layout.addWidget(
            self.stack
        )

        main_layout.addWidget(
            right,
            1
        )

    # ========================================================
    # SIDEBAR
    # ========================================================

    def create_sidebar(self):

        sidebar = QFrame()

        sidebar.setObjectName(
            "Sidebar"
        )

        sidebar.setFixedWidth(
            250
        )

        layout = QVBoxLayout(
            sidebar
        )

        # Slightly tighter padding inside the sidebar
        layout.setContentsMargins(
            12,
            18,
            12,
            18
        )

        # Logo

        logo_row = QHBoxLayout()

        # Search for a small logo image in several locations including 'bahan' (case-insensitive common names)
        # Prefer @2x assets if present (for HiDPI)
        candidates = [
            BASE_DIR / "logo_small@2x.png",
            BASE_DIR / "logo_small@2x.jpg",
            BASE_DIR / "logo@2x.png",
            BASE_DIR / "logo@2x.jpg",
            BASE_DIR / "logo_small.png",
            BASE_DIR / "logo_small.jpg",
            BASE_DIR / "logo_small.jpeg",
            BASE_DIR / "bahan" / "logo_small@2x.png",
            BASE_DIR / "bahan" / "logo_small@2x.jpg",
            BASE_DIR / "bahan" / "logo_small.png",
            BASE_DIR / "bahan" / "logo_small.jpg",
            BASE_DIR / "bahan" / "logo_small.jpeg",
            BASE_DIR / "bahan" / "logo.png",
            BASE_DIR / "bahan" / "logo.jpg",
            BASE_DIR / "bahan" / "LOGO.jpe",
            BASE_DIR / "Bahan" / "logo_small.png",
            BASE_DIR / "Bahan" / "LOGO.jpe",
        ]

        logo_icon = None
        for p in candidates:
            if p.exists():
                pix = load_image_pixmap(p, 88, 72)
                if pix is not None:
                    logo_icon = QLabel()
                    logo_icon.setPixmap(pix)
                    logo_icon.setScaledContents(False)
                    logo_icon.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                    logo_icon.setFixedSize(100, 80)
                    logo_icon.setAlignment(Qt.AlignCenter)
                    break

        if logo_icon is None:
            # fallback: scan bahan folder for any image
            found = None
            for d in (BASE_DIR, BASE_DIR / 'bahan', BASE_DIR / 'Bahan'):
                try:
                    if d.exists():
                        for ext in ('*.png','*.jpg','*.jpeg','*.jpe','*.bmp','*.svg'):
                            items = list(d.glob(ext))
                            if items:
                                found = items[0]
                                break
                except Exception:
                    pass
                if found:
                    break

            if found:
                pix = load_image_pixmap(found, 100, 80)
                if pix is not None:
                    logo_icon = QLabel()
                    logo_icon.setPixmap(pix)
                    logo_icon.setScaledContents(False)
                    logo_icon.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                    logo_icon.setFixedSize(100, 80)
                    logo_icon.setAlignment(Qt.AlignCenter)
                else:
                    print('[DEBUG] Found sidebar image but failed to load as pixmap:', found)

        if logo_icon is None:
            logo_icon = QLabel("S")
            logo_icon.setFixedSize(100, 80)
            logo_icon.setAlignment(Qt.AlignCenter)
            logo_icon.setStyleSheet("""
                background:#0f1724;
                color:white;
                border-radius:14px;
                font-size:26px;
                font-weight:800;
            """)

        # Title + subtitle column placed to the right of the logo
        title_col = QVBoxLayout()
        # tighten spacing so title/subtitle sit closer together and to the logo
        title_col.setSpacing(1)
        title_col.setContentsMargins(0, 0, 0, 0)
        title_label = QLabel("SCANLY")

        # Use object names so the global QSS can style these consistently
        title_label.setObjectName("SidebarTitle")
        # ensure no extra widget margins
        title_label.setStyleSheet("margin:0px; padding:0px;")
        # set letter spacing (absolute pixels) to 5 for the sidebar title
        try:
            f = title_label.font()
            f.setLetterSpacing(QFont.AbsoluteSpacing, 3)
            title_label.setFont(f)
        except Exception:
            pass
        # keep font weight strong but allow QSS to set color/size
        subtitle_label = QLabel("Dashboard Admin")
        subtitle_label.setObjectName("SidebarSubtitle")
        subtitle_label.setStyleSheet("margin:0px; padding:0px;")
        title_col.addWidget(title_label)
        title_col.addWidget(subtitle_label)

        # compose row: logo on the left, text column on the right
        # zero spacing so text sits tight next to the logo
        logo_row.setSpacing(0)
        logo_row.setContentsMargins(0, 0, 0, 0)
        logo_row.addWidget(logo_icon)
        logo_row.addLayout(title_col)
        # vertically center the title column relative to the logo
        title_col.setAlignment(Qt.AlignVCenter)
        logo_row.addStretch()

        layout.addLayout(logo_row)

        layout.addSpacing(28)

        navigation = [
            ("▦", "Dashboard"),
            ("●", "People"),
            ("▤", "Attendance Records"),
            ("▥", "Reports"),
            ("⚙", "Settings"),

                
        ]

                # ========================================================
        # MULAI ABSENSI
        # ========================================================

              # ========================================================
        # MULAI ABSENSI
        # ========================================================

        layout.addSpacing(15)

        attendance_button = QPushButton(
            "MULAI ABSENSI"
        )

        attendance_button.setObjectName(
            "AttendanceButton"
        )

        attendance_button.setCursor(
            Qt.PointingHandCursor
        )

        attendance_button.clicked.connect(
            self.open_attendance_scanner
        )

        layout.addWidget(
            attendance_button
        )

        # ========================================================
        # ABSENSI MANUAL
        # ========================================================

        manual_button = QPushButton(
            "ABSENSI MANUAL"
        )

        manual_button.setObjectName(
            "AttendanceManualButton"
        )

        manual_button.setCursor(
            Qt.PointingHandCursor
        )

        manual_button.clicked.connect(
            self.add_manual_attendance
        )

        layout.addWidget(
            manual_button
        )

        # ========================================================
        # NAVIGATION BUTTONS
        # ========================================================

        self.nav_buttons = []

        for index, (
            icon,
            text
        ) in enumerate(
            navigation
        ):

            button = QPushButton(
                f"{icon}  {text}"
            )

            button.setObjectName(
                "NavButton"
            )

            button.setProperty(
                "nav_index",
                index
            )

            button.clicked.connect(
                lambda checked=False,
                i=index:
                self.change_page(i)
            )

            self.nav_buttons.append(
                button
            )

            layout.addWidget(
                button
            )

        layout.addStretch()

        line = QFrame()

        line.setFrameShape(
            QFrame.HLine
        )

        line.setStyleSheet(
            "color:#e3e6eb;"
        )

        layout.addWidget(
            line
        )

        user_row = QHBoxLayout()

        avatar = QLabel(
            "A"
        )

        avatar.setFixedSize(
            40,
            40
        )

        avatar.setAlignment(
            Qt.AlignCenter
        )

        avatar.setStyleSheet("""
            background:#eef0f3;
            border-radius:20px;
            font-weight:700;
        """)

        user_info = QVBoxLayout()

        name = QLabel(
            "Admin User"
        )

        name.setStyleSheet(
            "font-weight:600;"
        )

        email = QLabel(
            "admin@scanly.ai"
        )

        email.setStyleSheet("""
            color:#7b8492;
            font-size:11px;
        """)

        user_info.addWidget(
            name
        )

        user_info.addWidget(
            email
        )

        user_row.addWidget(
            avatar
        )

        user_row.addLayout(
            user_info
        )

        layout.addLayout(
            user_row
        )

        return sidebar

    # ========================================================
    # TOPBAR
    # ========================================================

    def create_topbar(self):

        bar = QFrame()

        bar.setObjectName(
            "Topbar"
        )

        bar.setFixedHeight(
            64
        )

        layout = QHBoxLayout(
            bar
        )

        layout.setContentsMargins(
            22,
            0,
            22,
            0
        )

        menu = QLabel(
            "☰"
        )

        menu.setStyleSheet(
            "font-size:20px;color:#77808e;"
        )

        layout.addWidget(
            menu
        )

        self.global_search = QLineEdit()

        self.global_search.setPlaceholderText(
            "Search records..."
        )

        self.global_search.setFixedWidth(
            320
        )

        self.global_search.textChanged.connect(
            self.global_search_changed
        )

        layout.addWidget(
            self.global_search
        )

        layout.addStretch()

        status = QLabel(
            "●  SYSTEM ONLINE"
        )

        status.setStyleSheet("""
            color:#16803c;
            font-size:11px;
            font-weight:700;
        """)

        layout.addWidget(
            status
        )

        layout.addSpacing(
            15
        )

        avatar = QLabel(
            "A"
        )

        avatar.setFixedSize(
            34,
            34
        )

        avatar.setAlignment(
            Qt.AlignCenter
        )

        avatar.setStyleSheet("""
            background:#eef0f3;
            border-radius:17px;
            font-weight:700;
        """)

        layout.addWidget(
            avatar
        )

        return bar

    # ========================================================
    # PAGE HEADER
    # ========================================================

    def page_header(
        self,
        title,
        subtitle
    ):

        layout = QHBoxLayout()

        text = QVBoxLayout()

        title_label = QLabel(
            title
        )

        title_label.setObjectName(
            "PageTitle"
        )

        subtitle_label = QLabel(
            subtitle
        )

        subtitle_label.setObjectName(
            "PageSubtitle"
        )

        text.addWidget(
            title_label
        )

        text.addWidget(
            subtitle_label
        )

        layout.addLayout(
            text
        )

        layout.addStretch()

        return layout

    # ========================================================
    # DASHBOARD
    # ========================================================

    def create_dashboard(self):

        page = QWidget()

        layout = QVBoxLayout(
            page
        )

        layout.setContentsMargins(
            30,
            25,
            30,
            30
        )

        layout.setSpacing(
            18
        )

        header = self.page_header(
            "Dashboard Overview",
            "Real-time attendance monitoring and analytics."
        )

        refresh = QPushButton(
            "↻  Refresh"
        )

        refresh.setObjectName(
            "Secondary"
        )

        refresh.clicked.connect(
            self.refresh_all
        )

        export = QPushButton(
            "▣  Export PDF"
        )

        export.setObjectName(
            "Primary"
        )

        export.clicked.connect(
            self.export_pdf
        )

        header.addWidget(
            refresh
        )

        header.addWidget(
            export
        )

        layout.addLayout(
            header
        )

        self.cards_layout = QHBoxLayout()

        self.cards_layout.setSpacing(
            15
        )

        layout.addLayout(
            self.cards_layout
        )

        recent = QLabel(
            "Recent Scans"
        )

        recent.setStyleSheet("""
            font-size:18px;
            font-weight:600;
        """)

        layout.addWidget(
            recent
        )

        panel = QFrame()

        panel.setObjectName(
            "Panel"
        )

        panel_layout = QVBoxLayout(
            panel
        )

        panel_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        self.dashboard_table = (
            self.create_attendance_table()
        )

        panel_layout.addWidget(
            self.dashboard_table
        )

        layout.addWidget(
            panel,
            1
        )

        return page

    # ========================================================
    # PEOPLE
    # ========================================================

    def create_people(self):

        page = QWidget()

        layout = QVBoxLayout(
            page
        )

        layout.setContentsMargins(
            30,
            25,
            30,
            30
        )

        layout.setSpacing(
            18
        )

        header = self.page_header(
            "People",
            "Manage registered people and face datasets."
        )

        add_button = QPushButton(
            "+  ADD PERSON"
        )

        add_button.setObjectName(
            "Primary"
        )

        add_button.clicked.connect(
            self.add_person
        )

        header.addWidget(
            add_button
        )

        layout.addLayout(
            header
        )

        info = QFrame()

        info.setObjectName(
            "Card"
        )

        info_layout = QHBoxLayout(
            info
        )

        info_layout.setContentsMargins(
            18,
            10,
            18,
            10
        )

        info_text = QLabel(
            "Face Dataset"
        )

        info_text.setStyleSheet(
            "font-weight:700;"
        )

        info_layout.addWidget(
            info_text
        )

        info_layout.addStretch()

        self.people_count_label = QLabel(
            "0 people"
        )

        self.people_count_label.setStyleSheet(
            "color:#687083;"
        )

        info_layout.addWidget(
            self.people_count_label
        )

        layout.addWidget(
            info
        )

        panel = QFrame()

        panel.setObjectName(
            "Panel"
        )

        panel_layout = QVBoxLayout(
            panel
        )

        panel_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        self.people_table = QTableWidget()

        self.people_table.setColumnCount(
            6
        )

        self.people_table.setHorizontalHeaderLabels([
            "ID",
            "NAMA",
            "DATASET",
            "FOTO",
            "STATUS",
            "ACTION"
        ])

        self.people_table.verticalHeader().setVisible(
            False
        )

        self.people_table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )

        self.people_table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )

        self.people_table.setShowGrid(
            False
        )

        # Ruang vertikal ekstra untuk cell yang berisi tombol ACTION.
        self.people_table.verticalHeader().setDefaultSectionSize(58)
        self.people_table.verticalHeader().setMinimumSectionSize(58)

        # Improve table visuals & interactivity
        self.people_table.setAlternatingRowColors(True)
        self.people_table.setSortingEnabled(True)
        self.people_table.horizontalHeader().setHighlightSections(False)

        # Layout tabel: gunakan kombinasi mode resize untuk menjaga ACTION tetap terlihat
        header = self.people_table.horizontalHeader()
        try:
            # Kolom utama (ID, NAMA, DATASET) stretch
            header.setSectionResizeMode(0, QHeaderView.Stretch)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.Stretch)
            # Kolom FOTO dan STATUS set fixed kecil supaya ACTION punya ruang
            header.setSectionResizeMode(3, QHeaderView.Fixed)
            header.setSectionResizeMode(4, QHeaderView.Fixed)
            # Kolom ACTION ukur secara konten agar lebarnya menyesuaikan widget di dalamnya
            header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

            header.setDefaultAlignment(Qt.AlignCenter)

            # Set lebar kecil untuk FOTO dan STATUS, dan lebar awal untuk ACTION
            try:
                self.people_table.setColumnWidth(3, 70)   # FOTO
                self.people_table.setColumnWidth(4, 90)   # STATUS
                self.people_table.setColumnWidth(5, 320)  # ACTION initial
            except Exception:
                pass

            self.people_table.setHorizontalScrollBarPolicy(
                Qt.ScrollBarAsNeeded
            )
            self.people_table.setHorizontalScrollMode(
                QAbstractItemView.ScrollPerPixel
            )
        except Exception:
            header.setSectionResizeMode(QHeaderView.Stretch)

        panel_layout.addWidget(
            self.people_table
        )

        layout.addWidget(
            panel,
            1
        )

        return page

    # ========================================================
    # ATTENDANCE
    # ========================================================

    def create_attendance(self):

        page = QWidget()

        layout = QVBoxLayout(
            page
        )

        layout.setContentsMargins(
            30,
            25,
            30,
            30
        )

        layout.setSpacing(
            18
        )

        layout.addLayout(
            self.page_header(
                "Attendance Records",
                "Review, filter, and manage attendance records."
            )
        )

        filters = QHBoxLayout()

        self.attendance_date_filter = QLineEdit()

        self.attendance_date_filter.setPlaceholderText(
            "YYYY-MM-DD"
        )

        self.attendance_name_filter = QLineEdit()

        self.attendance_name_filter.setPlaceholderText(
            "Search employee / name..."
        )

        filter_button = QPushButton(
            "FILTER"
        )

        filter_button.setObjectName(
            "Primary"
        )

        filter_button.clicked.connect(
            self.apply_attendance_filter
        )

        reset_button = QPushButton(
            "RESET"
        )

        reset_button.setObjectName(
            "Secondary"
        )

        reset_button.clicked.connect(
            self.reset_attendance_filter
        )

        filters.addWidget(
            QLabel("Date")
        )

        filters.addWidget(
            self.attendance_date_filter
        )

        filters.addWidget(
            QLabel("Employee")
        )

        filters.addWidget(
            self.attendance_name_filter
        )

        filters.addWidget(
            filter_button
        )

        filters.addWidget(
            reset_button
        )

        layout.addLayout(
            filters
        )
                # ====================================================
        # MANUAL ATTENDANCE
        # ====================================================

        manual_row = QHBoxLayout()

        manual_button = QPushButton(
            "✎  TAMBAH ABSENSI MANUAL"
        )

        manual_button.setObjectName(
            "Primary"
        )

        manual_button.clicked.connect(
            self.add_manual_attendance
        )

        manual_row.addWidget(
            manual_button
        )

        manual_row.addStretch()

        layout.addLayout(
            manual_row
        )

        panel = QFrame()

        panel.setObjectName(
            "Panel"
        )

        panel_layout = QVBoxLayout(
            panel
        )

        panel_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        self.attendance_table = (
            self.create_attendance_table()
        )

        panel_layout.addWidget(
            self.attendance_table
        )

        layout.addWidget(
            panel,
            1
        )

        return page

    # ========================================================
    # REPORTS
    # ========================================================

    def create_reports(self):

        page = QWidget()

        layout = QVBoxLayout(
            page
        )

        layout.setContentsMargins(
            30,
            25,
            30,
            30
        )

        layout.setSpacing(
            18
        )

        header = self.page_header(
            "Reports",
            "Generate and export attendance reports."
        )

        export = QPushButton(
            "▣  EXPORT PDF"
        )

        export.setObjectName(
            "Primary"
        )

        export.clicked.connect(
            self.export_pdf
        )

        header.addWidget(
            export
        )

        layout.addLayout(
            header
        )

        panel = QFrame()

        panel.setObjectName(
            "Panel"
        )

        panel_layout = QVBoxLayout(
            panel
        )

        panel_layout.setContentsMargins(
            25,
            25,
            25,
            25
        )

        title = QLabel(
            "Attendance PDF Report"
        )

        title.setStyleSheet("""
            font-size:19px;
            font-weight:700;
        """)

        panel_layout.addWidget(
            title
        )

        panel_layout.addSpacing(
            10
        )

        form = QHBoxLayout()

        self.report_date = QLineEdit()

        self.report_date.setPlaceholderText(
            "YYYY-MM-DD"
        )

        self.report_person = QLineEdit()

        self.report_person.setPlaceholderText(
            "All people"
        )

        form.addWidget(
            QLabel("Date")
        )

        form.addWidget(
            self.report_date
        )

        form.addWidget(
            QLabel("Name")
        )

        form.addWidget(
            self.report_person
        )

        panel_layout.addLayout(
            form
        )

        panel_layout.addSpacing(
            18
        )

        export2 = QPushButton(
            "EXPORT PDF"
        )

        export2.setObjectName(
            "Primary"
        )

        export2.clicked.connect(
            self.export_pdf
        )

        panel_layout.addWidget(
            export2,
            0,
            Qt.AlignLeft
        )

        layout.addWidget(
            panel
        )

        layout.addStretch()

        return page

    # ========================================================
    # SETTINGS
    # ========================================================

    def create_settings(self):

        page = QWidget()

        layout = QVBoxLayout(
            page
        )

        layout.setContentsMargins(
            30,
            25,
            30,
            30
        )

        layout.setSpacing(
            18
        )

        layout.addLayout(
            self.page_header(
                "Settings",
                "Configure Scanly recognition preferences."
            )
        )

        panel = QFrame()

        panel.setObjectName(
            "Panel"
        )

        panel_layout = QVBoxLayout(
            panel
        )

        panel_layout.setContentsMargins(
            25,
            25,
            25,
            25
        )

        threshold_row = QHBoxLayout()

        threshold_row.addWidget(
            QLabel(
                "Recognition Threshold"
            )
        )

        threshold_row.addStretch()

        self.threshold = QSpinBox()

        self.threshold.setRange(
            1,
            200
        )

        self.threshold.setValue(
            65
        )

        threshold_row.addWidget(
            self.threshold
        )

        panel_layout.addLayout(
            threshold_row
        )

        voting_row = QHBoxLayout()

        voting_row.addWidget(
            QLabel(
                "Multi-frame Voting"
            )
        )

        voting_row.addStretch()

        self.voting = QSpinBox()

        self.voting.setRange(
            1,
            5
        )

        self.voting.setValue(
            4
        )

        voting_row.addWidget(
            self.voting
        )

        voting_row.addWidget(
            QLabel(
                "dari 5 frame"
            )
        )

        panel_layout.addLayout(
            voting_row
        )

        cooldown_row = QHBoxLayout()

        cooldown_row.addWidget(
            QLabel(
                "Result Cooldown"
            )
        )

        cooldown_row.addStretch()

        self.cooldown = QSpinBox()

        self.cooldown.setRange(
            0,
            60
        )

        self.cooldown.setValue(
            2
        )

        cooldown_row.addWidget(
            self.cooldown
        )

        cooldown_row.addWidget(
            QLabel(
                "seconds"
            )
        )

        panel_layout.addLayout(
            cooldown_row
        )

        self.liveness = QCheckBox(
            "Liveness detection aktif"
        )

        self.liveness.setChecked(
            True
        )

        panel_layout.addWidget(
            self.liveness
        )

        panel_layout.addSpacing(
            10
        )

        save = QPushButton(
            "SAVE SETTINGS"
        )

        save.setObjectName(
            "Primary"
        )

        save.clicked.connect(
            self.save_settings
        )

        panel_layout.addWidget(
            save,
            0,
            Qt.AlignLeft
        )

        layout.addWidget(
            panel
        )

        layout.addStretch()

        return page

    # ========================================================
    # TABLE
    # ========================================================

    def create_attendance_table(self):

        table = QTableWidget()

        table.setColumnCount(
            5
        )

        table.setHorizontalHeaderLabels([
            "NAMA",
            "TANGGAL",
            "JAM",
            "SCORE",
            "STATUS"
        ])

        table.verticalHeader().setVisible(
            False
        )

        table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )

        table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )

        table.setShowGrid(
            False
        )

        # Improve table visuals & interactivity
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        table.horizontalHeader().setHighlightSections(False)

        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        return table

    # ========================================================
    # CHANGE PAGE
    # ========================================================

    def change_page(
        self,
        index
    ):

        self.stack.setCurrentIndex(
            index
        )

        for i, button in enumerate(
            self.nav_buttons
        ):

            button.setProperty(
                "active",
                i == index
            )

            button.style().unpolish(
                button
            )

            button.style().polish(
                button
            )

        if index == 1:

            self.load_people_table()

        elif index == 2:

            self.fill_attendance_table(
                self.attendance
            )

    # ========================================================
    # REFRESH
    # ========================================================

    def refresh_all(self):

        self.people = load_people()

        self.attendance = load_attendance()

        self.update_dashboard_cards()

        self.fill_attendance_table(
            self.attendance
        )

        self.load_people_table()

    # ========================================================
    # DASHBOARD CARDS
    # ========================================================

    def update_dashboard_cards(self):

        while self.cards_layout.count():

            item = (
                self.cards_layout
                .takeAt(0)
            )

            if item.widget():

                item.widget().deleteLater()

        today = datetime.now().strftime(
            "%Y-%m-%d"
        )

        today_rows = [
            row
            for row in self.attendance
            if row["Tanggal"] == today
        ]

        hadir = [
            row
            for row in today_rows
            if row["Status"].lower()
            == "hadir"
        ]

        unique_hadir = len(
            set(
                row["Nama"]
                for row in hadir
                if row["Nama"]
            )
        )

        cards = [

            create_card(
                "Total Data",
                len(self.people),
                "◉",
                "All Time"
            ),

            create_card(
                "Total Hari Ini",
                len(today_rows),
                "◷",
                "Today"
            ),

            create_card(
                "Total Hadir",
                unique_hadir,
                "✓",
                "Live"
            ),

        ]

        for card in cards:

            self.cards_layout.addWidget(
                card
            )

        recent = sorted(
            self.attendance,
            key=lambda row: (
                row["Tanggal"],
                row["Jam"]
            ),
            reverse=True
        )

        self.fill_attendance_table(
            recent[:10],
            self.dashboard_table
        )

    # ========================================================
    # FILL ATTENDANCE
    # ========================================================

    def fill_attendance_table(
        self,
        rows,
        table=None
    ):

        if table is None:

            table = self.attendance_table

        table.setRowCount(
            0
        )

        for row in rows:

            index = table.rowCount()

            table.insertRow(
                index
            )

            values = [
                row["Nama"],
                row["Tanggal"],
                row["Jam"],
                row["Score"],
                row["Status"]
            ]

            for column, value in enumerate(
                values
            ):

                item = QTableWidgetItem(
                    value
                )

                if column >= 2:

                    item.setTextAlignment(
                        Qt.AlignCenter
                    )

                table.setItem(
                    index,
                    column,
                    item
                )

    # ========================================================
    # PEOPLE TABLE
    # ========================================================

    def load_people_table(self):

        self.people = load_people()

        self.people_table.setRowCount(
            0
        )

        self.people_count_label.setText(
            f"{len(self.people)} people"
        )

        for person in self.people:

            index = (
                self.people_table.rowCount()
            )

            self.people_table.insertRow(
                index
            )
            # ensure row has enough height for buttons to display
            try:
                self.people_table.setRowHeight(index, 58)
            except Exception:
                pass

            id_item = QTableWidgetItem(person["ID"])
            id_item.setTextAlignment(Qt.AlignCenter)
            self.people_table.setItem(index, 0, id_item)

            name_item = QTableWidgetItem(person["Nama"])
            name_item.setTextAlignment(Qt.AlignCenter)
            self.people_table.setItem(index, 1, name_item)

            folder_item = QTableWidgetItem(person["Folder"])
            folder_item.setTextAlignment(Qt.AlignCenter)
            self.people_table.setItem(index, 2, folder_item)

            folder = self.get_person_folder(person)

            photo_count = 0

            if folder.exists():
                photo_count = len([
                    file for file in folder.iterdir()
                    if file.suffix.lower() in [
                        ".jpg",
                        ".jpeg",
                        ".png",
                        ".bmp"
                    ]
                ])

            photo_item = QTableWidgetItem(str(photo_count))
            photo_item.setTextAlignment(Qt.AlignCenter)
            self.people_table.setItem(index, 3, photo_item)

            status_item = QTableWidgetItem(person["Status"])
            status_item.setTextAlignment(Qt.AlignCenter)
            self.people_table.setItem(index, 4, status_item)

            action_widget = QWidget()

            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(6, 6, 6, 6)
            action_layout.setSpacing(0)

            # container that holds the two buttons with compact sizing
            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.setSpacing(8)

            # Smaller, compact buttons so ACTION column doesn't overflow
            register = QPushButton("REGISTER")
            register.setObjectName("Blue")
            register.setFont(QFont("Segoe UI", 8, QFont.Bold))
            register.setFixedHeight(22)
            register.setFixedWidth(72)
            register.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            register.setStyleSheet(
                "QPushButton{ color:#0f1724; background:#eef3ff; border:1px solid rgba(36,81,214,0.08); border-radius:4px; padding:2px 4px; font-size:11px; }"
                "QPushButton:pressed{ background:#dfe8ff; }"
            )
            register.setToolTip("REGISTER FACE")
            register.clicked.connect(lambda checked=False, p=person: self.register_face(p))

            delete = QPushButton("HAPUS")
            delete.setObjectName("Danger")
            delete.setFont(QFont("Segoe UI", 8, QFont.Bold))
            delete.setFixedHeight(22)
            delete.setFixedWidth(56)
            delete.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            delete.setStyleSheet(
                "QPushButton{ color:#7a0f12; background:#fff6f6; border:1px solid rgba(179,38,30,0.06); border-radius:4px; padding:2px 4px; font-size:11px; }"
                "QPushButton:pressed{ background:#ffeaea; }"
            )
            delete.setToolTip("HAPUS")
            delete.clicked.connect(lambda checked=False, p=person: self.delete_person(p))

            btn_layout.addWidget(register)
            btn_layout.addWidget(delete)

            # allow container to size naturally but cap maximum to avoid excessive width
            total_btn_w = (register.width() if register.width() else 72) + (delete.width() if delete.width() else 56) + 8
            btn_container.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            btn_container.setMaximumWidth(total_btn_w)

            # place the container to the left within the cell (then allow stretch to fill remaining space)
            action_layout.addWidget(btn_container)
            action_layout.addStretch()

            # make sure the cell is tall enough
            action_widget.setMinimumHeight(50)
            action_widget.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            action_widget.setStyleSheet("background: transparent; border: none; padding: 0px;")
            action_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            self.people_table.setCellWidget(index, 5, action_widget)

        # Lebar kolom dikelola otomatis oleh QHeaderView.Stretch.
        # Tidak ada ukuran pixel tetap agar responsif terhadap layar.
        try:
            header = self.people_table.horizontalHeader()
            for column in range(6):
                header.setSectionResizeMode(
                    column,
                    QHeaderView.Stretch
                )
            header.setMinimumSectionSize(40)
        except Exception:
            pass

    # ========================================================
    # PERSON FOLDER
    # ========================================================
    
    def get_person_folder(
        self,
        person
    ): 

        folder = person["Folder"]

        if folder.startswith(
            "faces/"
        ):

            relative = folder[
                len("faces/"):
            ]

            return (
                FACES_DIR
                / relative
            )

        return (
            BASE_DIR
            / folder
        )

    # ========================================================
    # ADD PERSON
    # ========================================================

    def add_person(self):

        dialog = AddPersonDialog(
            self
        )

        if (
            dialog.exec()
            == QDialog.Accepted
        ):

            self.refresh_all()

    # ========================================================
    # REGISTER FACE
    # ========================================================

    def register_face(
        self,
        person
    ):

        folder = self.get_person_folder(
            person
        )

        folder.mkdir(
            parents=True,
            exist_ok=True
        )

        reply = QMessageBox.question(
            self,
            "Register Face",
            (
                f"Register wajah untuk:\n\n"
                f"Nama : {person['Nama']}\n"
                f"ID   : {person['ID']}\n\n"
                f"Dataset:\n{folder}\n\n"
                f"Setelah ini register_face.py akan "
                f"dijalankan untuk proses training.\n\n"
                f"Lanjutkan?"
            ),
            QMessageBox.Yes
            | QMessageBox.No
        )

        if reply != QMessageBox.Yes:

            return

        if not REGISTER_SCRIPT.exists():

            QMessageBox.critical(
                self,
                "register_face.py Tidak Ditemukan",
                (
                    "File register_face.py tidak ditemukan.\n\n"
                    f"Seharusnya berada di:\n"
                    f"{REGISTER_SCRIPT}"
                )
            )

            return

        # ====================================================
        # SIMPAN INFO TARGET REGISTER
        # ====================================================

        target_file = (
            BASE_DIR
            / "register_target.txt"
        )

        try:

            target_file.write_text(
                (
                    f"ID={person['ID']}\n"
                    f"Nama={person['Nama']}\n"
                    f"Folder={folder}\n"
                ),
                encoding="utf-8"
            )

        except Exception as error:

            print(
                "[WARNING] target file:",
                error
            )

        # ====================================================
        # JALANKAN REGISTER SCRIPT
        # ====================================================

        self.register_process = QProcess(
            self
        )

        self.register_process.setWorkingDirectory(
            str(BASE_DIR)
        )

        self.register_process.readyReadStandardOutput.connect(
            self.read_register_output
        )

        self.register_process.readyReadStandardError.connect(
            self.read_register_error
        )

        self.register_process.finished.connect(
            self.register_finished
        )

        self.register_process.start(
            sys.executable,
            [
                str(REGISTER_SCRIPT)
            ]
        )

        if not self.register_process.waitForStarted(
            3000
        ):

            QMessageBox.critical(
                self,
                "Gagal",
                "Tidak dapat menjalankan register_face.py."
            )

            return

        QMessageBox.information(
            self,
            "Register Face",
            (
                "register_face.py sedang dijalankan.\n\n"
                "Setelah proses selesai, kembali ke People "
                "dan jumlah foto/model akan diperbarui."
            )
        )

    def read_register_output(self):

        if not hasattr(
            self,
            "register_process"
        ):

            return

        data = self.register_process.readAllStandardOutput()

        text = bytes(
            data
        ).decode(
            "utf-8",
            errors="ignore"
        )

        if text.strip():

            print(
                "[REGISTER]",
                text
            )

    def read_register_error(self):

        if not hasattr(
            self,
            "register_process"
        ):

            return

        data = self.register_process.readAllStandardError()

        text = bytes(
            data
        ).decode(
            "utf-8",
            errors="ignore"
        )

        if text.strip():

            print(
                "[REGISTER ERROR]",
                text
            )

    def register_finished(
        self,
        exit_code,
        exit_status
    ):

        self.refresh_all()

        if exit_code == 0:

            QMessageBox.information(
                self,
                "Register Selesai",
                (
                    "Proses register_face.py selesai.\n\n"
                    "Silakan cek folder faces dan model "
                    "face_model/scanly_faces.yml."
                )
            )

        else:

            QMessageBox.warning(
                self,
                "Register Selesai dengan Error",
                (
                    f"register_face.py berhenti dengan "
                    f"exit code {exit_code}.\n\n"
                    "Cek terminal untuk detail error."
                )
            )

    # ========================================================
    # DELETE PERSON
    # ========================================================

    def delete_person(
        self,
        person
    ):

        folder = self.get_person_folder(
            person
        )

        reply = QMessageBox.question(
            self,
            "Hapus Person",
            (
                f"Yakin menghapus:\n\n"
                f"{person['Nama']} "
                f"({person['ID']})?\n\n"
                f"Folder dataset:\n{folder}\n\n"
                f"Data orang akan dihapus dari people.csv."
            ),
            QMessageBox.Yes
            | QMessageBox.No
        )

        if reply != QMessageBox.Yes:

            return

        people = [
            row
            for row in self.people
            if row["ID"] != person["ID"]
        ]

        save_people(
            people
        )

        # Attempt to delete the dataset folder and its contents as well.
        # Only delete if the folder is inside known project data directories for safety.
        deleted_dataset = False
        try:
            # Resolve paths for safety check
            folder_resolved = Path(folder).resolve()
            safe_roots = [Path(FACES_DIR).resolve(), Path(BASE_DIR).resolve()]
            if any(str(folder_resolved).startswith(str(root)) for root in safe_roots):
                if folder_resolved.exists():
                    if folder_resolved.is_dir():
                        shutil.rmtree(str(folder_resolved))
                        deleted_dataset = True
                    else:
                        try:
                            folder_resolved.unlink()
                            deleted_dataset = True
                        except Exception:
                            pass
        except Exception as e:
            # Non-fatal; record failure in variable and continue
            deleted_dataset = False


        # ====================================================
        # TRAINING ULANG SETELAH USER DIHAPUS
        # ====================================================

        training_ok = False

        try:

            if REGISTER_SCRIPT.exists():

                result = subprocess.run(
                    [
                        sys.executable,
                        str(REGISTER_SCRIPT)
                    ],
                    cwd=str(BASE_DIR),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore"
                )

                print(
                    "[DELETE] TRAINING OUTPUT:"
                )

                print(
                    result.stdout
                )

                if result.stderr:

                    print(
                        "[DELETE] TRAINING ERROR:"
                    )

                    print(
                        result.stderr
                    )

                training_ok = (
                    result.returncode == 0
                )

        except Exception as error:

            print(
                "[DELETE] Gagal training ulang:",
                error
            )

        self.refresh_all()

        if deleted_dataset:
            QMessageBox.information(
                self,
                "Berhasil",
                (
                    f"{person['Nama']} telah dihapus dari daftar People.\n\n"
                    f"Dataset juga dihapus: \n{folder}"
                )
            )
        else:
            QMessageBox.information(
                self,
                "Berhasil",
                (
                    f"{person['Nama']} telah dihapus dari daftar People.\n\n"
                    f"Dataset tetap disimpan di (atau penghapusan gagal):\n{folder}"
                )
            )

    # ========================================================
    # FILTER ATTENDANCE
    # ========================================================

    def apply_attendance_filter(self):

        date = (
            self.attendance_date_filter
            .text()
            .strip()
        )

        name = (
            self.attendance_name_filter
            .text()
            .strip()
            .lower()
        )

        result = []

        for row in self.attendance:

            date_ok = (
                not date
                or row["Tanggal"] == date
            )

            name_ok = (
                not name
                or name in row["Nama"].lower()
            )

            if date_ok and name_ok:

                result.append(
                    row
                )

        self.fill_attendance_table(
            result
        )

    def reset_attendance_filter(self):

        self.attendance_date_filter.clear()

        self.attendance_name_filter.clear()

        self.fill_attendance_table(
            self.attendance
        )

    # ========================================================
    # GLOBAL SEARCH
    # ========================================================

    def global_search_changed(
        self,
        text
    ):

        query = (
            text
            .strip()
            .lower()
        )

        if not query:

            self.fill_attendance_table(
                self.attendance[:10],
                self.dashboard_table
            )

            return

        result = []

        for row in self.attendance:

            joined = " ".join(
                row.values()
            ).lower()

            if query in joined:

                result.append(
                    row
                )

        self.fill_attendance_table(
            result[:20],
            self.dashboard_table
        )

    # ========================================================
    # SETTINGS
    # ========================================================

    def save_settings(self):

        settings_file = (
            BASE_DIR
            / "admin_settings.csv"
        )

        try:

            with open(
                settings_file,
                "w",
                encoding="utf-8",
                newline=""
            ) as file:

                writer = csv.writer(
                    file
                )

                writer.writerow([
                    "RecognitionThreshold",
                    "Voting",
                    "Cooldown",
                    "Liveness"
                ])

                writer.writerow([
                    self.threshold.value(),
                    self.voting.value(),
                    self.cooldown.value(),
                    int(
                        self.liveness.isChecked()
                    )
                ])

            QMessageBox.information(
                self,
                "Settings",
                (
                    "Pengaturan berhasil disimpan.\n\n"
                    "Catatan: register_face.py/main.py "
                    "perlu membaca file ini jika ingin "
                    "setting diterapkan otomatis."
                )
            )

        except Exception as error:

            QMessageBox.warning(
                self,
                "Gagal",
                str(error)
            )

    # ========================================================
    # EXPORT PDF
    # ========================================================

    def export_pdf(self):

        try:

            from reportlab.lib import colors

            from reportlab.lib.pagesizes import A4

            from reportlab.lib.styles import (
                getSampleStyleSheet
            )

            from reportlab.lib.units import mm

            from reportlab.platypus import (
                SimpleDocTemplate,
                Paragraph,
                Spacer,
                Table,
                TableStyle
            )

        except ImportError:

            QMessageBox.critical(
                self,
                "ReportLab Belum Terinstall",
                (
                    "Install dengan:\n\n"
                    "pip install reportlab"
                )
            )

            return

        date = ""

        name = ""

        if hasattr(
            self,
            "report_date"
        ):

            date = (
                self.report_date
                .text()
                .strip()
            )

        if hasattr(
            self,
            "report_person"
        ):

            name = (
                self.report_person
                .text()
                .strip()
                .lower()
            )

        rows = []

        for row in self.attendance:

            if date:

                if row["Tanggal"] != date:

                    continue

            if name:

                if name not in row["Nama"].lower():

                    continue

            rows.append(
                row
            )

        if not rows:

            QMessageBox.information(
                self,
                "Tidak Ada Data",
                "Tidak ada data attendance untuk filter tersebut."
            )

            return

        REPORT_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        filename = (
            "scanly_attendance_"
            + datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
            + ".pdf"
        )

        output = (
            REPORT_DIR
            / filename
        )

        styles = (
            getSampleStyleSheet()
        )

        document = SimpleDocTemplate(
            str(output),
            pagesize=A4,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
            topMargin=15 * mm,
            bottomMargin=15 * mm,
            title="Scanly Attendance Report"
        )

        story = []

        story.append(
            Paragraph(
                "<b>SCANLY</b>",
                styles["Title"]
            )
        )

        story.append(
            Paragraph(
                "Attendance Report",
                styles["Heading2"]
            )
        )

        story.append(
            Spacer(
                1,
                4 * mm
            )
        )

        story.append(
            Paragraph(
                "Generated: "
                + datetime.now().strftime(
                    "%d-%m-%Y %H:%M:%S"
                ),
                styles["Normal"]
            )
        )

        story.append(
            Paragraph(
                "Date filter: "
                + (
                    date
                    if date
                    else "All dates"
                ),
                styles["Normal"]
            )
        )

        story.append(
            Paragraph(
                "Name filter: "
                + (
                    name
                    if name
                    else "All people"
                ),
                styles["Normal"]
            )
        )

        story.append(
            Spacer(
                1,
                6 * mm
            )
        )

        table_data = [
            [
                "Nama",
                "Tanggal",
                "Jam",
                "Score",
                "Status"
            ]
        ]

        for row in rows:

            table_data.append([
                row["Nama"],
                row["Tanggal"],
                row["Jam"],
                row["Score"],
                row["Status"]
            ])

        table = Table(
            table_data,
            repeatRows=1,
            colWidths=[
                50 * mm,
                30 * mm,
                28 * mm,
                25 * mm,
                25 * mm
            ]
        )

        table.setStyle(
            TableStyle([
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        "#eef0f3"
                    )
                ),

                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold"
                ),

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor(
                        "#d5d9df"
                    )
                ),

                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),

                (
                    "ALIGN",
                    (1, 1),
                    (-1, -1),
                    "CENTER"
                ),
            ])
        )

        story.append(
            table
        )

        story.append(
            Spacer(
                1,
                6 * mm
            )
        )

        story.append(
            Paragraph(
                f"<b>Total records:</b> {len(rows)}",
                styles["Normal"]
            )
        )

        document.build(
            story
        )

        QMessageBox.information(
            self,
            "Export Berhasil",
            (
                "PDF berhasil dibuat:\n\n"
                f"{output}"
            )
        )

    # ========================================================
    # CLOSE
    # ========================================================

    def closeEvent(
        self,
        event
    ):

        if hasattr(
            self,
            "register_process"
        ):

            if (
                self.register_process
                and
                self.register_process.state()
                != QProcess.NotRunning
            ):

                reply = QMessageBox.question(
                    self,
                    "Register Sedang Berjalan",
                    (
                        "register_face.py masih berjalan.\n\n"
                        "Tutup admin?"
                    ),
                    QMessageBox.Yes
                    | QMessageBox.No
                )

                if reply != QMessageBox.Yes:

                    event.ignore()

                    return

        event.accept()


# ============================================================
# MAIN
# ============================================================

def main():

    # Enable High-DPI scaling and high-DPI pixmaps before creating the QApplication.
    # Use environment variables for broad Qt compatibility and the newer QGuiApplication
    # API for rounding/policy when available to avoid deprecated attributes.
    try:
        import os
        # Prefer env vars which are supported across Qt versions and avoid deprecated attributes
        os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
        os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

        # If available, set the High DPI rounding policy via the newer API
        from PySide6.QtGui import QGuiApplication
        if hasattr(QGuiApplication, "setHighDpiScaleFactorRoundingPolicy"):
            QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
            )
    except Exception:
        pass

    app = QApplication(
        sys.argv
    )

    app.setStyle(
        "Fusion"
    )

    app.setStyleSheet(
        STYLE
    )

    login = LoginDialog()

    if (
        login.exec()
        != QDialog.Accepted
    ):

        sys.exit(0)

    window = AdminWindow()

    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":

    main()