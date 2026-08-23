import sys
import csv
import os
import shutil
import re
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import calendar

from main import ScanlyWindow

from PySide6.QtCore import (
    QTimer,
    Qt,
    QProcess,
    QDate,
    QTime,
)

from PySide6.QtGui import (
    QColor,
    QPixmap,
    QImage,
    QPainter,
    QFont,
)

from PySide6.QtWidgets import QDateEdit, QAbstractButton, QWidget

try:
    from PySide6.QtSvg import QSvgRenderer
except Exception:
    QSvgRenderer = None




class ScanlyDateEdit(QDateEdit):
    """
    Date field memakai bentuk yang sama dengan ScanlySelectBox:
    putih, teks tanggal hitam, separator abu-abu, dan ▼ tetap abu-abu.
    Klik di seluruh field membuka kalender.
    """

    BUTTON_WIDTH = 92

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setCursor(Qt.PointingHandCursor)
        self.setReadOnly(True)
        self.setCalendarPopup(True)

        line_edit = self.lineEdit()
        if line_edit is not None:
            line_edit.setReadOnly(True)
            line_edit.setReadOnly(True)
            line_edit.setStyleSheet(
                "background: transparent; border: none; color: transparent;"
                "selection-color: transparent; selection-background-color: transparent;"
            )
            line_edit.setAttribute(
                Qt.WA_TransparentForMouseEvents,
                True,
            )
            line_edit.hide()

        self.dateChanged.connect(self.update)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect()

        painter.setPen(QColor("#b8c0ca"))
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(
            rect.adjusted(0, 0, -1, -1),
            8,
            8,
        )

        text_rect = rect.adjusted(
            12,
            0,
            -(self.BUTTON_WIDTH + 8),
            0,
        )

        # Hanya isi/date text yang diubah menjadi hitam.
        painter.setPen(QColor("#111827"))
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)

        value = self.date().toString("dd/MM/yyyy")
        painter.drawText(
            text_rect,
            Qt.AlignVCenter | Qt.AlignLeft,
            value,
        )

        # Divider tetap warna lama.
        divider_x = rect.right() - self.BUTTON_WIDTH
        painter.setPen(QColor("#b8c0ca"))
        painter.drawLine(
            divider_x,
            rect.top() + 1,
            divider_x,
            rect.bottom() - 1,
        )

        # ▼ tetap warna lama.
        button_rect = rect.adjusted(
            divider_x - rect.left() + 1,
            0,
            0,
            0,
        )

        painter.setPen(QColor("#b8c0ca"))
        button_font = painter.font()
        button_font.setBold(False)
        painter.setFont(button_font)
        painter.drawText(
            button_rect,
            Qt.AlignCenter,
            "▼",
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.open_calendar_popup()
            event.accept()
            return

        super().mousePressEvent(event)

    def open_calendar_popup(self):
        self.setCalendarPopup(True)

        calendar = self.calendarWidget()
        if calendar is None:
            return

        calendar.setSelectedDate(self.date())

        popup = calendar.window()

        if popup.width() < 250 or popup.height() < 180:
            popup.resize(360, 300)

        global_pos = self.mapToGlobal(
            self.rect().bottomLeft()
        )

        popup.move(
            global_pos.x(),
            global_pos.y() + 4,
        )

        popup.show()
        popup.raise_()
        popup.activateWindow()
        calendar.setFocus(Qt.OtherFocusReason)


def setup_white_date_picker(date_edit):
    """Apply consistent white styling to the field and calendar popup."""
    date_edit.setStyleSheet("""
        QDateEdit {
            background-color: #ffffff;
            color: #111827;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            padding: 9px 34px 9px 12px;
            min-height: 22px;
        }
        QDateEdit:hover {
            border-color: #9ca3af;
        }
        QDateEdit:focus {
            background-color: #ffffff;
            color: #111827;
            border: 1px solid #2563eb;
        }
        QDateEdit::drop-down {
            width: 0px;
            border: none;
            background: transparent;
        }
    """)

    date_edit.setReadOnly(True)
    date_edit.setCalendarPopup(True)
    date_edit.setCursor(Qt.PointingHandCursor)

    calendar = date_edit.calendarWidget()
    calendar.setStyleSheet("""
        QCalendarWidget {
            background: #ffffff;
            color: #111827;
            border: 1px solid #d1d5db;
        }
        QWidget#qt_calendar_navigationbar {
            background: #ffffff;
            color: #111827;
        }
        QToolButton#qt_calendar_prevmonth,
        QToolButton#qt_calendar_nextmonth,
        QToolButton#qt_calendar_monthbutton,
        QToolButton#qt_calendar_yearbutton {
            background: #ffffff;
            color: #111827;
            border: none;
            padding: 6px;
        }
        QToolButton#qt_calendar_prevmonth:hover,
        QToolButton#qt_calendar_nextmonth:hover,
        QToolButton#qt_calendar_monthbutton:hover,
        QToolButton#qt_calendar_yearbutton:hover {
            background: #f3f4f6;
            color: #111827;
        }
        QSpinBox#qt_calendar_yearedit {
            background: #ffffff;
            color: #111827;
            border: 1px solid #d1d5db;
        }
        QAbstractItemView#qt_calendar_calendarview {
            background: #ffffff;
            color: #111827;
            selection-background-color: #2563eb;
            selection-color: #ffffff;
            alternate-background-color: #f9fafb;
            outline: none;
        }
        QAbstractItemView#qt_calendar_calendarview::item {
            background: #ffffff;
            color: #111827;
            padding: 4px;
        }
        QAbstractItemView#qt_calendar_calendarview::item:hover {
            background: #e5e7eb;
            color: #111827;
        }
        QAbstractItemView#qt_calendar_calendarview::item:selected {
            background: #2563eb;
            color: #ffffff;
        }
    """)

    def force_white(widget):
        palette = widget.palette()
        role = palette.ColorRole
        palette.setColor(role.Window, QColor("#ffffff"))
        palette.setColor(role.Base, QColor("#ffffff"))
        palette.setColor(role.AlternateBase, QColor("#f9fafb"))
        palette.setColor(role.Text, QColor("#111827"))
        palette.setColor(role.WindowText, QColor("#111827"))
        palette.setColor(role.Button, QColor("#ffffff"))
        palette.setColor(role.ButtonText, QColor("#111827"))
        palette.setColor(role.Highlight, QColor("#2563eb"))
        palette.setColor(role.HighlightedText, QColor("#ffffff"))
        widget.setPalette(palette)
        widget.setAutoFillBackground(True)

    force_white(calendar)

    for child in calendar.findChildren(QWidget):
        force_white(child)

    popup = calendar.window()
    if popup is not calendar:
        popup.setStyleSheet("QWidget { background: #ffffff; color: #111827; }")
        force_white(popup)

    return date_edit



COMBO_LIGHT_STYLE = """
QComboBox {
    background-color: #ffffff;
    color: #111827;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    padding: 9px 34px 9px 12px;
    min-height: 22px;
}
QComboBox:hover { border-color: #9ca3af; }
QComboBox:focus {
    background-color: #ffffff;
    color: #111827;
    border: 1px solid #2563eb;
}
QComboBox::drop-down { width: 0px; border: none; background: transparent; }
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #111827;
    border: 1px solid #d1d5db;
    selection-background-color: #e5edff;
    selection-color: #111827;
    outline: none;
}
QComboBox QAbstractItemView::item {
    background-color: #ffffff;
    color: #111827;
    padding: 8px 10px;
    min-height: 28px;
}
QComboBox QAbstractItemView::item:hover {
    background-color: #f3f4f6;
    color: #111827;
}
QComboBox QAbstractItemView::item:selected {
    background-color: #e5edff;
    color: #111827;
}
"""


DATE_FIELD_STYLE = """
QDateEdit {
    background-color: #ffffff;
    color: #111827;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    padding: 9px 34px 9px 12px;
    min-height: 22px;
}
QDateEdit:hover { border-color: #9ca3af; }
QDateEdit:focus {
    background-color: #ffffff;
    color: #111827;
    border: 1px solid #2563eb;
}
QDateEdit::drop-down {
    width: 0px;
    border: none;
    background: transparent;
}
"""

from PySide6.QtWidgets import (
    QGridLayout,
    QAbstractButton,
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


class ScanlySelectBox(QComboBox):
    """
    Dropdown bergaya input + tombol:
    [ nilai terpilih                              |  Pilih ]
    Background putih, teks hitam, divider hitam.
    Klik seluruh field tetap membuka popup QComboBox standar.
    """

    BUTTON_WIDTH = 92

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(40)
        self.setStyleSheet("""
            QComboBox {
                background: #ffffff;
                color: #111827;
                border: 1px solid #b8c0ca;
                border-radius: 8px;
                padding: 0px;
                min-height: 40px;
            }
            QComboBox:focus {
                border: 1px solid #111827;
                background: #ffffff;
            }
            QComboBox::drop-down { width: 0px; border: none; background: transparent; }
            QComboBox QAbstractItemView {
                background: #ffffff;
                color: #111827;
                border: 1px solid #b8c0ca;
                selection-background-color: #eef2f7;
                selection-color: #111827;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                background: #ffffff;
                color: #111827;
                padding: 9px 12px;
                min-height: 28px;
            }
            QComboBox QAbstractItemView::item:hover {
                background: #f3f4f6;
                color: #111827;
            }
            QComboBox QAbstractItemView::item:selected {
                background: #e5e7eb;
                color: #111827;
            }
        """)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect()
        painter.setPen(QColor("#b8c0ca"))
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(
            rect.adjusted(0, 0, -1, -1),
            8,
            8,
        )

        # Current selected text.
        text_rect = rect.adjusted(
            12,
            0,
            -(self.BUTTON_WIDTH + 8),
            0,
        )
        painter.setPen(QColor("#111827"))
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)

        current = self.currentText().strip()
        if not current:
            current = "Pilih Jenis"

        painter.drawText(
            text_rect,
            Qt.AlignVCenter | Qt.AlignLeft,
            current,
        )

        # Button separator.
        divider_x = rect.right() - self.BUTTON_WIDTH
        painter.setPen(QColor("#b8c0ca"))
        painter.drawLine(
            divider_x,
            rect.top() + 1,
            divider_x,
            rect.bottom() - 1,
        )

        # Button label.
        button_rect = rect.adjusted(
            divider_x - rect.left() + 1,
            0,
            0,
            0,
        )
        painter.setPen(QColor("#b8c0ca"))
        button_font = painter.font()
        button_font.setBold(False)
        painter.setFont(button_font)
        painter.drawText(
            button_rect,
            Qt.AlignCenter,
            "▼",
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.showPopup()
            event.accept()
            return
        super().mousePressEvent(event)

# ============================================================
# PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

ATTENDANCE_FILE = BASE_DIR / "attendance.csv"
PEOPLE_FILE = BASE_DIR / "people.csv"
HOLIDAYS_FILE = BASE_DIR / "holidays.csv"

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
# UNIFIED FORM / FIELD STYLE
# ============================================================

FORM_FIELD_STYLE = """
QLineEdit, QComboBox, QDateEdit, QSpinBox, QTimeEdit {
    background: #ffffff;
    color: #172033;
    border: 1px solid #d9e0e7;
    border-radius: 8px;
    min-height: 40px;
    padding: 0 12px;
    font-size: 13px;
}
QLineEdit:hover, QComboBox:hover, QDateEdit:hover,
QSpinBox:hover, QTimeEdit:hover { border-color: #aeb9c6; }
QLineEdit:focus, QComboBox:focus, QDateEdit:focus,
QSpinBox:focus, QTimeEdit:focus {
    border: 1px solid #2563eb;
    background: #ffffff;
}
QComboBox::drop-down, QDateEdit::drop-down {
    width: 30px;
    border: none;
    background: transparent;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    color: #172033;
    border: 1px solid #d9e0e7;
    selection-background-color: #eaf1ff;
    selection-color: #1d4ed8;
    outline: none;
}
QComboBox QAbstractItemView::item {
    background: #ffffff;
    color: #172033;
    padding: 8px 10px;
    min-height: 28px;
}
QComboBox QAbstractItemView::item:hover {
    background: #f3f6fa;
    color: #172033;
}
QComboBox QAbstractItemView::item:selected {
    background: #eaf1ff;
    color: #1d4ed8;
}
"""

def normalize_form(form):
    form.setHorizontalSpacing(14)
    form.setVerticalSpacing(14)
    form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    form.setFormAlignment(Qt.AlignTop)
    form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
    return form

def normalize_field(widget, minimum_width=220, height=40):
    widget.setMinimumHeight(height)
    widget.setMinimumWidth(minimum_width)
    widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    if not widget.styleSheet().strip():
        widget.setStyleSheet(FORM_FIELD_STYLE)
    return widget


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


QPushButton#LogoutButton {
    background: #f8fafc;
    color: #374151;
    border: 1px solid #e5e7eb;
    border-radius: 9px;
    padding: 8px 12px;
    font-size: 13px;
    font-weight: 700;
    text-align: center;
}

QPushButton#LogoutButton:hover {
    background: #fff1f2;
    color: #b42318;
    border-color: #fecdd3;
}

QPushButton#LogoutButton:pressed {
    background: #ffe4e6;
    color: #991b1b;
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
                    "Skor": row.get("Skor", "").strip(),
                    "Status": row.get("Status", "").strip(),
                    "Keterangan": row.get("Keterangan", "").strip(),
                })

    except Exception as error:

        print(
            "[ERROR] attendance.csv:",
            error
        )

    return rows



# ============================================================
# HOLIDAY + MONTHLY ATTENDANCE HELPERS
# ============================================================

def load_holidays():
    holidays = {}
    if not HOLIDAYS_FILE.exists():
        return holidays

    try:
        with open(
            HOLIDAYS_FILE,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:
            reader = csv.DictReader(file)
            for row in reader:
                date_text = str(row.get("Tanggal", "")).strip()
                note = str(row.get("Keterangan", "")).strip()
                if date_text:
                    holidays[date_text] = note
    except Exception as error:
        print("[ERROR] holidays.csv:", error)

    return holidays


def save_holidays(holidays):
    HOLIDAYS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(
        HOLIDAYS_FILE,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        writer = csv.writer(file)
        writer.writerow(["Tanggal", "Keterangan"])
        for date_text in sorted(holidays):
            writer.writerow([date_text, holidays[date_text]])


def is_working_day(day, holidays=None):
    holidays = holidays if holidays is not None else load_holidays()
    return day.weekday() < 5 and day.strftime("%Y-%m-%d") not in holidays


def working_days_in_month(year, month, holidays=None):
    holidays = holidays if holidays is not None else load_holidays()
    total = 0
    last_day = calendar.monthrange(year, month)[1]
    for day_number in range(1, last_day + 1):
        day = datetime(year, month, day_number).date()
        if is_working_day(day, holidays):
            total += 1
    return total


def attendance_status_is_present(status):
    value = str(status or "").strip().lower()
    return value in {
        "hadir",
        "tepat waktu",
        "terlambat",
        "pulang",
    }


def monthly_person_summary(name, year, month, attendance, holidays=None):
    holidays = holidays if holidays is not None else load_holidays()
    working = working_days_in_month(year, month, holidays)

    month_prefix = f"{year:04d}-{month:02d}-"
    rows = [
        row for row in attendance
        if row.get("Nama", "").strip() == name
        and row.get("Tanggal", "").startswith(month_prefix)
    ]

    # One calendar date counts at most once for each status bucket.
    by_date = {}
    for row in rows:
        date_text = row.get("Tanggal", "").strip()
        status = row.get("Status", "").strip()
        if date_text:
            by_date[date_text] = status

    hadir = sum(
        1 for status in by_date.values()
        if attendance_status_is_present(status)
    )
    izin = sum(
        1 for status in by_date.values()
        if status.lower() == "izin"
    )
    sakit = sum(
        1 for status in by_date.values()
        if status.lower() == "sakit"
    )
    tanpa = sum(
        1 for status in by_date.values()
        if status.lower() in {
            "tanpa keterangan",
            "tanpa_keterangan",
            "alpha",
            "alpa",
        }
    )

    percentage = (
        (hadir / working) * 100.0
        if working > 0
        else 0.0
    )

    return {
        "hadir": hadir,
        "izin": izin,
        "sakit": sakit,
        "tanpa_keterangan": tanpa,
        "hari_kerja": working,
        "percentage": min(100.0, max(0.0, percentage)),
    }



# =========================================================
# DATE PICKER STYLE
# =========================================================
DATE_PICKER_STYLE = """
QDateEdit {
    background: #ffffff;
    color: #111827;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 6px 8px;
}

QDateEdit::drop-down {
    background: #ffffff;
    border-left: 1px solid #d1d5db;
    width: 28px;
}

QDateEdit::down-arrow {
    width: 10px;
    height: 10px;
}

QCalendarWidget {
    background: #ffffff;
    color: #111827;
}

QCalendarWidget QWidget {
    background: #ffffff;
    color: #111827;
}

QCalendarWidget QToolButton {
    background: #ffffff;
    color: #111827;
    border: none;
    padding: 5px;
}

QCalendarWidget QToolButton:hover {
    background: #f3f4f6;
}

QCalendarWidget QSpinBox {
    background: #ffffff;
    color: #111827;
    border: 1px solid #d1d5db;
}

QCalendarWidget QAbstractItemView {
    background: #ffffff;
    color: #111827;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    alternate-background-color: #f9fafb;
}

QCalendarWidget QAbstractItemView:disabled {
    color: #9ca3af;
}
"""


class HolidayDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kelola Hari Libur")
        self.resize(760, 620)
        self.setModal(True)

        # Force this dialog to stay light even when the application/system
        # palette is dark.
        self.setStyleSheet("""
            QDialog {
                background: #ffffff;
                color: #172033;
            }

            QLabel {
                background: transparent;
                color: #172033;
            }

            QLineEdit {
                background: #ffffff;
                color: #172033;
                border: 1px solid #d9e0e7;
                border-radius: 8px;
                padding: 0 12px;
                min-height: 40px;
            }

            QLineEdit:focus {
                border: 1px solid #2563eb;
                background: #ffffff;
                color: #172033;
            }

            QTableWidget {
                background: #ffffff;
                color: #172033;
                border: 1px solid #e1e6ec;
                border-radius: 8px;
                gridline-color: #edf1f5;
                selection-background-color: #eaf1ff;
                selection-color: #172033;
                alternate-background-color: #fbfcfe;
            }

            QTableWidget::item {
                background: #ffffff;
                color: #172033;
                padding: 9px 12px;
                border-bottom: 1px solid #edf1f5;
            }

            QTableWidget::item:selected {
                background: #eaf1ff;
                color: #172033;
            }

            QHeaderView::section {
                background: #f8fafc;
                color: #364152;
                border: none;
                border-bottom: 1px solid #e1e6ec;
                padding: 11px 12px;
                font-weight: 700;
            }

            QPushButton {
                min-height: 40px;
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 700;
            }

            QPushButton#Primary {
                background: #111827;
                color: #ffffff;
                border: none;
            }

            QPushButton#Primary:hover {
                background: #1f2937;
                color: #ffffff;
            }

            QPushButton#Danger {
                background: #fff1f2;
                color: #b42318;
                border: 1px solid #fecdd3;
            }

            QPushButton#Danger:hover {
                background: #ffe4e6;
                color: #9f1239;
            }

            QPushButton#Secondary {
                background: #f3f4f6;
                color: #374151;
                border: 1px solid #e5e7eb;
            }

            QPushButton#Secondary:hover {
                background: #e5e7eb;
                color: #111827;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(16)

        title = QLabel("Hari Libur / Tanggal Merah")
        title.setStyleSheet(
            "font-size:21px; font-weight:700; color:#0f1724;"
        )
        layout.addWidget(title)

        subtitle = QLabel(
            "Sabtu dan Minggu otomatis bukan hari kerja. "
            "Tambahkan tanggal merah/libur khusus di sini."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#687083; font-size:13px;")
        layout.addWidget(subtitle)

        # ------------------------------
        # Input row
        # ------------------------------
        form_card = QFrame()
        form_card.setStyleSheet("""
            QFrame {
                background: #f8fafc;
                border: 1px solid #e8edf2;
                border-radius: 10px;
            }
            QLabel {
                color: #364152;
                font-weight: 600;
            }
        """)

        form = QGridLayout(form_card)
        form.setContentsMargins(16, 16, 16, 16)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        date_label = QLabel("Tanggal")
        date_label.setFixedWidth(75)

        self.date_edit = ScanlyDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        setup_white_date_picker(self.date_edit)
        normalize_field(self.date_edit, 180, 40)

        note_label = QLabel("Keterangan")
        note_label.setFixedWidth(85)

        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("Contoh: Idul Fitri")
        normalize_field(self.note_edit, 280, 40)

        add = QPushButton("TAMBAH")
        add.setObjectName("Primary")
        add.setFixedSize(105, 40)
        add.clicked.connect(self.add_holiday)

        form.addWidget(date_label, 0, 0)
        form.addWidget(self.date_edit, 0, 1, 1, 2)
        form.addWidget(note_label, 1, 0)
        form.addWidget(self.note_edit, 1, 1)
        form.addWidget(add, 1, 2)
        form.setColumnStretch(1, 1)

        layout.addWidget(form_card)

        # ------------------------------
        # Table
        # ------------------------------
        table_title = QLabel("Daftar Hari Libur")
        table_title.setStyleSheet(
            "font-size:14px; font-weight:700; color:#172033;"
        )
        layout.addWidget(table_title)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Tanggal", "Keterangan"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setMinimumHeight(280)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

        layout.addWidget(self.table, 1)

        # ------------------------------
        # Bottom actions
        # ------------------------------
        buttons = QHBoxLayout()
        buttons.setSpacing(10)

        remove = QPushButton("HAPUS TANGGAL TERPILIH")
        remove.setObjectName("Danger")
        remove.clicked.connect(self.remove_selected)

        close = QPushButton("TUTUP")
        close.setObjectName("Secondary")
        close.setFixedWidth(100)
        close.clicked.connect(self.accept)

        buttons.addWidget(remove)
        buttons.addStretch(1)
        buttons.addWidget(close)
        layout.addLayout(buttons)

        self.refresh()

    def refresh(self):
        self.holidays = load_holidays()
        self.table.setRowCount(0)

        for date_text, note in sorted(self.holidays.items()):
            row = self.table.rowCount()
            self.table.insertRow(row)

            date_item = QTableWidgetItem(date_text)
            note_item = QTableWidgetItem(note)

            date_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            note_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

            self.table.setItem(row, 0, date_item)
            self.table.setItem(row, 1, note_item)

        self.table.resizeRowsToContents()

    def add_holiday(self):
        date_text = (
            self.date_edit.date()
            .toPython()
            .strftime("%Y-%m-%d")
        )
        note = self.note_edit.text().strip()

        holidays = load_holidays()
        holidays[date_text] = note
        save_holidays(holidays)

        self.note_edit.clear()
        self.refresh()

    def remove_selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(
                self,
                "Hari Libur",
                "Pilih tanggal yang ingin dihapus terlebih dahulu."
            )
            return

        date_item = self.table.item(row, 0)
        if date_item is None:
            return

        date_text = date_item.text().strip()

        holidays = load_holidays()
        holidays.pop(date_text, None)
        save_holidays(holidays)
        self.refresh()

class ManualStatusDialog(QDialog):
    """
    Presensi manual mengikuti jam kerja Scanly.

    08:00-08:30  : Hadir
    08:31-14:30  : Terlambat / Izin / Sakit
    14:31-15:59  : ditutup
    16:00-19:00  : hanya Pulang untuk pengguna yang sudah absen masuk
    >19:00       : ditutup
    """

    def __init__(self, parent, people):
        super().__init__(parent)

        self.people = people
        self.setWindowTitle("Presensi Manual")
        self.resize(700, 600)
        self.setMinimumSize(660, 560)
        self.setModal(True)

        self.setStyleSheet("""
            QDialog {
                background: #ffffff;
                color: #172033;
            }
            QLabel {
                background: transparent;
                color: #172033;
            }
            QLabel#DialogTitle {
                color: #0f1724;
                font-size: 22px;
                font-weight: 800;
            }
            QLabel#DialogSubtitle {
                color: #6b7280;
                font-size: 13px;
            }
            QLabel#AutoLabel {
                color: #374151;
                font-size: 12px;
                font-weight: 700;
            }
            QLabel#AutoDateTime {
                color: #111827;
                font-size: 15px;
                font-weight: 700;
            }
            QLabel#AutoBadge {
                background: #e8f5ec;
                color: #16703a;
                border-radius: 8px;
                padding: 5px 9px;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel#ModeLabel {
                color: #374151;
                font-size: 12px;
                font-weight: 700;
            }
            QLabel#ModePreview {
                background: #f3f6f9;
                color: #374151;
                border: 1px solid #e5e7eb;
                border-radius: 9px;
                padding: 10px 12px;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#InfoBox {
                background: #f3f6f9;
                color: #4b5563;
                border: 1px solid #e5e7eb;
                border-radius: 9px;
                padding: 11px 13px;
            }
            QLineEdit {
                background: #ffffff;
                color: #172033;
                border: 1px solid #d9e0e7;
                border-radius: 8px;
                padding: 0 12px;
                min-height: 40px;
            }
            QLineEdit:focus {
                border: 1px solid #2563eb;
            }
            QPushButton#Primary {
                background: #111827;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                min-height: 42px;
                padding: 0 20px;
                font-weight: 700;
            }
            QPushButton#Primary:hover {
                background: #1f2937;
            }
            QPushButton#Secondary {
                background: #f3f4f6;
                color: #374151;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                min-height: 42px;
                padding: 0 20px;
                font-weight: 600;
            }
            QPushButton#Secondary:hover {
                background: #e5e7eb;
                color: #111827;
            }
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 30, 28, 24)
        outer.setSpacing(16)

        title = QLabel("Tambah Presensi Manual")
        title.setObjectName("DialogTitle")
        outer.addWidget(title)

        subtitle = QLabel(
            "Pilih pengguna. Jenis presensi mengikuti jam kerja secara otomatis."
        )
        subtitle.setObjectName("DialogSubtitle")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        # ========================================================
        # WAKTU OTOMATIS
        # ========================================================
        auto_card = QFrame()
        auto_card.setObjectName("AutoTimeCard")

        auto_layout = QHBoxLayout(auto_card)
        auto_layout.setContentsMargins(14, 12, 14, 12)
        auto_layout.setSpacing(12)

        auto_left = QVBoxLayout()
        auto_left.setSpacing(2)

        auto_label = QLabel("Tanggal & Waktu Presensi")
        auto_label.setObjectName("AutoLabel")
        auto_left.addWidget(auto_label)

        self.auto_datetime = QLabel()
        self.auto_datetime.setObjectName("AutoDateTime")
        auto_left.addWidget(self.auto_datetime)

        auto_layout.addLayout(auto_left, 1)

        auto_badge = QLabel("OTOMATIS")
        auto_badge.setObjectName("AutoBadge")
        auto_badge.setAlignment(Qt.AlignCenter)
        auto_badge.setFixedWidth(92)
        auto_layout.addWidget(auto_badge)

        outer.addWidget(auto_card)

        # ========================================================
        # FORM
        # ========================================================
        form_card = QFrame()
        form_card.setObjectName("AutoTimeCard")

        form = QGridLayout(form_card)
        form.setContentsMargins(16, 16, 16, 16)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)

        name_label = QLabel("Nama")
        name_label.setFixedWidth(90)

        self.person_combo = ScanlySelectBox()
        self.person_combo.setStyleSheet(COMBO_LIGHT_STYLE)

        for person in people:
            name = str(person.get("Nama", "")).strip()
            if name:
                self.person_combo.addItem(
                    f"{name} ({person.get('ID', '')})",
                    person,
                )

        self.person_combo.currentIndexChanged.connect(
            self.update_time_rules
        )

        status_label = QLabel("Jenis")
        status_label.setFixedWidth(90)

        self.status_combo = ScanlySelectBox()
        self.status_combo.setStyleSheet(COMBO_LIGHT_STYLE)

        note_label = QLabel("Keterangan")
        note_label.setFixedWidth(90)

        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText(
            "Isi keterangan untuk Izin/Sakit (wajib)"
        )

        normalize_field(self.person_combo, 360, 42)
        normalize_field(self.status_combo, 230, 42)
        normalize_field(self.note_edit, 360, 42)

        form.addWidget(name_label, 0, 0)
        form.addWidget(self.person_combo, 0, 1, 1, 2)

        form.addWidget(status_label, 1, 0)
        form.addWidget(self.status_combo, 1, 1, 1, 2)

        form.addWidget(note_label, 2, 0)
        form.addWidget(self.note_edit, 2, 1, 1, 2)

        form.setColumnStretch(1, 1)
        form.setColumnStretch(2, 1)

        outer.addWidget(form_card)

        # ========================================================
        # MODE / INFORMASI WAKTU
        # ========================================================
        self.mode_preview = QLabel()
        self.mode_preview.setObjectName("ModePreview")
        self.mode_preview.setWordWrap(True)
        outer.addWidget(self.mode_preview)

        info = QLabel(
            "Presensi manual tidak mengubah mesin pengenalan wajah dan liveness."
        )
        info.setObjectName("InfoBox")
        info.setWordWrap(True)
        outer.addWidget(info)

        # ========================================================
        # BUTTON
        # ========================================================
        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        buttons.addStretch(1)

        cancel = QPushButton("BATAL")
        cancel.setObjectName("Secondary")
        cancel.setFixedWidth(110)
        cancel.clicked.connect(self.reject)

        self.save_button = QPushButton("SIMPAN")
        self.save_button.setObjectName("Primary")
        self.save_button.setFixedWidth(120)
        self.save_button.clicked.connect(self.save)

        buttons.addWidget(cancel)
        buttons.addWidget(self.save_button)
        outer.addLayout(buttons)

        # Jam harus dievaluasi terus-menerus selama dialog terbuka.
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self.update_clock_and_rules)
        self._clock_timer.start(1000)

        self.update_clock_and_rules()

    def _today_rows_for_person(self, person):
        name = str(person.get("Nama", "")).strip()
        today = datetime.now().strftime("%Y-%m-%d")

        try:
            rows = load_attendance()
        except Exception:
            rows = []

        return [
            row for row in rows
            if str(row.get("Nama", "")).strip() == name
            and str(row.get("Tanggal", "")).strip() == today
        ]

    def _has_entry_today(self, person):
        present_statuses = {
            "tepat waktu",
            "terlambat",
            "hadir",
        }
        return any(
            str(row.get("Status", "")).strip().lower() in present_statuses
            for row in self._today_rows_for_person(person)
        )

    def _has_exit_today(self, person):
        return any(
            str(row.get("Status", "")).strip().lower() == "pulang"
            for row in self._today_rows_for_person(person)
        )

    def update_clock_and_rules(self):
        now = datetime.now()
        self.auto_datetime.setText(
            now.strftime("%d/%m/%Y  •  %H:%M:%S")
        )
        self.update_time_rules()

    def update_time_rules(self):
        selected = self.person_combo.currentData()

        old_status = self.status_combo.currentText().strip()
        self.status_combo.blockSignals(True)
        self.status_combo.clear()

        seconds = (
            datetime.now().hour * 3600
            + datetime.now().minute * 60
            + datetime.now().second
        )

        start_in = 8 * 3600
        on_time_end = 8 * 3600 + 30 * 60
        late_end = 14 * 3600 + 30 * 60
        return_start = 16 * 3600
        return_end = 19 * 3600

        enabled = True
        mode_text = ""

        if seconds < start_in:
            enabled = False
            mode_text = (
                "Presensi masuk belum dibuka. "
                "Waktu masuk dimulai pukul 08:00."
            )

        elif seconds <= on_time_end:
            self.status_combo.addItem("Hadir")
            self.status_combo.addItem("Izin")
            self.status_combo.addItem("Sakit")
            mode_text = (
                "Mode masuk: 08:00–08:30 = Tepat Waktu."
            )

        elif seconds <= late_end:
            self.status_combo.addItem("Terlambat")
            self.status_combo.addItem("Izin")
            self.status_combo.addItem("Sakit")
            mode_text = (
                "Mode masuk: 08:31–14:30 = Terlambat "
                "(tetap dihitung sebagai hadir)."
            )

        elif seconds < return_start:
            enabled = False
            mode_text = (
                "Presensi masuk sudah ditutup. "
                "Absen pulang baru dibuka pukul 16:00."
            )

        elif seconds <= return_end:
            if selected and self._has_entry_today(selected):
                if not self._has_exit_today(selected):
                    self.status_combo.addItem("Pulang")
                    mode_text = (
                        "Mode pulang: 16:00–19:00. "
                        "Hanya pengguna yang sudah absen masuk yang dapat absen pulang."
                    )
                else:
                    enabled = False
                    mode_text = (
                        "Pengguna ini sudah memiliki absen pulang hari ini."
                    )
            else:
                enabled = False
                mode_text = (
                    "Mode pulang aktif, tetapi pengguna yang dipilih "
                    "belum memiliki absen masuk hari ini."
                )

        else:
            enabled = False
            mode_text = (
                "Semua presensi sudah ditutup. "
                "Absen masuk berakhir 14:30 dan absen pulang berakhir 19:00."
            )

        # Pertahankan pilihan bila masih valid.
        if old_status:
            index = self.status_combo.findText(old_status)
            if index >= 0:
                self.status_combo.setCurrentIndex(index)
        elif self.status_combo.count() > 0:
            self.status_combo.setCurrentIndex(0)

        self.status_combo.blockSignals(False)

        self.status_combo.setEnabled(enabled and self.status_combo.count() > 0)
        self.save_button.setEnabled(enabled and self.status_combo.count() > 0)
        self.mode_preview.setText(mode_text)

        if self.status_combo.currentText().strip() in {"Izin", "Sakit"}:
            self.note_edit.setPlaceholderText(
                "Isi keterangan untuk Izin/Sakit (wajib)"
            )
        else:
            self.note_edit.setPlaceholderText(
                "Keterangan (opsional)"
            )

    def save(self):
        person = self.person_combo.currentData()

        if not person:
            QMessageBox.warning(
                self,
                "Presensi",
                "Pilih nama terlebih dahulu.",
            )
            return

        # Wajib memakai waktu terbaru, bukan waktu saat dialog pertama dibuka.
        now = datetime.now()
        seconds = now.hour * 3600 + now.minute * 60 + now.second

        start_in = 8 * 3600
        on_time_end = 8 * 3600 + 30 * 60
        late_end = 14 * 3600 + 30 * 60
        return_start = 16 * 3600
        return_end = 19 * 3600

        existing_rows = self._today_rows_for_person(person)
        has_entry = any(
            str(row.get("Status", "")).strip().lower()
            in {"tepat waktu", "terlambat", "hadir"}
            for row in existing_rows
        )
        has_exit = any(
            str(row.get("Status", "")).strip().lower() == "pulang"
            for row in existing_rows
        )

        requested = self.status_combo.currentText().strip()

        if seconds < start_in:
            QMessageBox.warning(
                self,
                "Belum Waktunya",
                "Presensi masuk baru dibuka pukul 08:00.",
            )
            return

        if seconds <= on_time_end:
            allowed = {"Hadir", "Izin", "Sakit"}
            expected_status = requested

        elif seconds <= late_end:
            allowed = {"Terlambat", "Izin", "Sakit"}
            expected_status = requested

        elif seconds < return_start:
            QMessageBox.warning(
                self,
                "Absen Masuk Ditutup",
                (
                    "Presensi masuk sudah ditutup.\n\n"
                    "Batas absen masuk adalah pukul 14:30.\n"
                    "Absen pulang mulai pukul 16:00."
                ),
            )
            return

        elif seconds <= return_end:
            if not has_entry:
                QMessageBox.warning(
                    self,
                    "Belum Absen Masuk",
                    (
                        f"{person.get('Nama', '')} belum memiliki "
                        "absen masuk hari ini.\n\n"
                        "Absen pulang hanya dapat dilakukan untuk "
                        "pengguna yang sudah absen masuk."
                    ),
                )
                return

            if has_exit:
                QMessageBox.warning(
                    self,
                    "Sudah Absen Pulang",
                    "Pengguna tersebut sudah memiliki absen pulang hari ini.",
                )
                return

            allowed = {"Pulang"}
            expected_status = requested

        else:
            QMessageBox.warning(
                self,
                "Presensi Ditutup",
                (
                    "Semua presensi sudah ditutup.\n\n"
                    "Absen masuk: 08:00–14:30\n"
                    "Absen pulang: 16:00–19:00"
                ),
            )
            return

        if expected_status not in allowed:
            QMessageBox.warning(
                self,
                "Jenis Presensi Tidak Valid",
                "Jenis presensi yang dipilih tidak sesuai dengan jam saat ini.",
            )
            self.update_time_rules()
            return

        if expected_status in {"Hadir", "Terlambat", "Izin", "Sakit"} and has_entry:
            QMessageBox.warning(
                self,
                "Sudah Absen Masuk",
                (
                    f"{person.get('Nama', '')} sudah memiliki "
                    "absen masuk hari ini."
                ),
            )
            return

        note = self.note_edit.text().strip()

        if expected_status in {"Izin", "Sakit"} and not note:
            QMessageBox.warning(
                self,
                "Keterangan wajib",
                "Keterangan wajib diisi untuk Izin/Sakit.",
            )
            self.note_edit.setFocus()
            return

        self.result = {
            "person": person,
            "status": expected_status,
            "note": note,
        }

        self.accept()



def ensure_attendance_schema():
    """Ensure attendance.csv has the optional Keterangan column.

    Existing 5-column files are migrated in-place without changing
    the existing attendance records.
    """
    if not ATTENDANCE_FILE.exists():
        return

    try:
        with open(
            ATTENDANCE_FILE,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:
            reader = csv.DictReader(file)
            fieldnames = reader.fieldnames or []
            rows = list(reader)

        if "Keterangan" in fieldnames:
            return

        target = [
            "Nama",
            "Tanggal",
            "Jam",
            "Skor",
            "Status",
            "Keterangan",
        ]

        with open(
            ATTENDANCE_FILE,
            "w",
            encoding="utf-8-sig",
            newline=""
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=target,
            )
            writer.writeheader()

            for row in rows:
                writer.writerow({
                    "Nama": row.get("Nama", ""),
                    "Tanggal": row.get("Tanggal", ""),
                    "Jam": row.get("Jam", ""),
                    "Skor": row.get("Skor", ""),
                    "Status": row.get("Status", ""),
                    "Keterangan": row.get("Keterangan", ""),
                })

        print("[DB] attendance.csv schema diperbarui: Keterangan")
    except Exception as error:
        print("[WARNING] Gagal memperbarui schema attendance.csv:", error)



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
            "Scanly - Masuk Admin"
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
            "MASUK   →"
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
                "Gagal Masuk",
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
            "Scanly - Tambah Pengguna"
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

        title = QLabel("Tambah Pengguna")
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

        self.person_combo = ScanlySelectBox()

        self.person_combo.setStyleSheet(COMBO_LIGHT_STYLE)
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

            QComboBox::drop-down { width: 0px; border: none; background: transparent; }

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

        self.type_combo = ScanlySelectBox()

        self.type_combo.setStyleSheet(COMBO_LIGHT_STYLE)
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

            QComboBox::drop-down { width: 0px; border: none; background: transparent; }

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
        attendance_type = self.type_combo.currentText()
        current_time = now.time()

        if attendance_type == "Masuk":

            start_time = datetime.strptime("08:00", "%H:%M").time()
            on_time_end = datetime.strptime("08:30", "%H:%M").time()
            late_end = datetime.strptime("14:30", "%H:%M").time()

            if current_time < start_time:
                status = "⚠  Belum masuk waktu absensi"
                self.status_preview.setStyleSheet("""
                    background-color: #fff7ed;
                    color: #c2410c;
                    border: 1px solid #fed7aa;
                    border-radius: 10px;
                    padding: 14px;
                    font-size: 14px;
                    font-weight: 600;
                """)

            elif current_time <= on_time_end:
                status = "✓  Tepat Waktu"
                self.status_preview.setStyleSheet("""
                    background-color: #ecfdf5;
                    color: #047857;
                    border: 1px solid #a7f3d0;
                    border-radius: 10px;
                    padding: 14px;
                    font-size: 14px;
                    font-weight: 600;
                """)

            elif current_time <= late_end:
                status = "⚠  Terlambat"
                self.status_preview.setStyleSheet("""
                    background-color: #fffbeb;
                    color: #b45309;
                    border: 1px solid #fde68a;
                    border-radius: 10px;
                    padding: 14px;
                    font-size: 14px;
                    font-weight: 600;
                """)

            else:
                status = "⛔  Absen Masuk Ditutup"
                self.status_preview.setStyleSheet("""
                    background-color: #fef2f2;
                    color: #b91c1c;
                    border: 1px solid #fecaca;
                    border-radius: 10px;
                    padding: 14px;
                    font-size: 14px;
                    font-weight: 600;
                """)

        else:

            start_time = datetime.strptime("16:00", "%H:%M").time()
            end_time = datetime.strptime("19:00", "%H:%M").time()

            if current_time < start_time:
                status = "⚠  Belum waktunya absen pulang"
                self.status_preview.setStyleSheet("""
                    background-color: #fff7ed;
                    color: #c2410c;
                    border: 1px solid #fed7aa;
                    border-radius: 10px;
                    padding: 14px;
                    font-size: 14px;
                    font-weight: 600;
                """)

            elif current_time <= end_time:
                status = "✓  Absen Pulang"
                self.status_preview.setStyleSheet("""
                    background-color: #ecfdf5;
                    color: #047857;
                    border: 1px solid #a7f3d0;
                    border-radius: 10px;
                    padding: 14px;
                    font-size: 14px;
                    font-weight: 600;
                """)

            else:
                status = "⛔  Waktu absen pulang telah berakhir"
                self.status_preview.setStyleSheet("""
                    background-color: #fef2f2;
                    color: #b91c1c;
                    border: 1px solid #fecaca;
                    border-radius: 10px;
                    padding: 14px;
                    font-size: 14px;
                    font-weight: 600;
                """)

        self.status_preview.setText(status)

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

        late_end = (
            14 * 3600
            + 30 * 60
        )

        return_start = (
            16 * 3600
        )

        return_end = (
            19 * 3600
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

            elif current_seconds <= late_end:

                status = "Terlambat"

            # -----------------------------------------------
            # 14:31 - 15:59
            # -----------------------------------------------

            elif current_seconds < return_start:

                QMessageBox.warning(
                    self,
                    "Absen Masuk Ditutup",
                    (
                        "Waktu absen masuk sudah ditutup.\n\n"
                        "Batas absen masuk adalah pukul 14:30."
                    )
                )

                return

            # -----------------------------------------------
            # 16:00+
            # -----------------------------------------------

            else:

                QMessageBox.warning(
                    self,
                    "Absen Masuk Ditutup",
                    (
                        "Absen masuk sudah ditutup.\n\n"
                        "Mulai pukul 16:00 hanya tersedia absen pulang."
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
                        "Batas absen pulang adalah pukul 19:00."
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
                        "Skor",
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
                "Belum ada pengguna terdaftar.",
            )
            return

        dialog = ManualStatusDialog(self, self.people)

        if dialog.exec() != QDialog.Accepted:
            return

        data = dialog.result
        person = data["person"]
        status = data["status"]
        note = data["note"]

        # Waktu final selalu diambil dari komputer saat tombol SIMPAN
        # benar-benar ditekan. Admin tidak dapat mengubah tanggal/jam.
        saved_at = datetime.now()

        # Guard kedua: aturan jam wajib dipatuhi saat data benar-benar disimpan.
        now_seconds = saved_at.hour * 3600 + saved_at.minute * 60 + saved_at.second
        entry_late_end = 14 * 3600 + 30 * 60
        return_start = 16 * 3600
        return_end = 19 * 3600

        if status == "Pulang":
            if not (return_start <= now_seconds <= return_end):
                QMessageBox.warning(
                    self,
                    "Absen Pulang Ditutup",
                    "Absen pulang hanya dapat dilakukan pukul 16:00–19:00.",
                )
                return
        else:
            if now_seconds > entry_late_end:
                QMessageBox.warning(
                    self,
                    "Absen Masuk Ditutup",
                    "Absen masuk sudah ditutup setelah pukul 14:30.",
                )
                return

        name = str(person.get("Nama", "")).strip()
        person_id = str(person.get("ID", "")).strip()
        date_text = saved_at.strftime("%Y-%m-%d")
        time_text = saved_at.strftime("%H:%M:%S")

        # Jangan membuat dua status pada tanggal yang sama untuk orang yang sama.
        existing = [
            row for row in self.attendance
            if row.get("Nama", "").strip() == name
            and row.get("Tanggal", "").strip() == date_text
        ]

        if existing:
            # Status otomatis Tanpa Keterangan boleh dikoreksi admin
            # menjadi Hadir/Izin/Sakit.
            auto_rows = [
                row for row in existing
                if str(row.get("Status", "")).strip().lower()
                in {"tanpa keterangan", "tanpa_keterangan", "alpha", "alpa"}
            ]

            if not auto_rows:
                QMessageBox.warning(
                    self,
                    "Tanggal Sudah Memiliki Data",
                    (
                        f"{name} sudah memiliki data presensi pada "
                        f"{date_text}.\n\n"
                        "Gunakan Riwayat Presensi untuk memeriksanya."
                    ),
                )
                return

            try:
                # Hapus baris otomatis pada tanggal tersebut, kemudian
                # simpan status manual penggantinya.
                rows = load_attendance()
                kept = [
                    row for row in rows
                    if not (
                        row.get("Nama", "").strip() == name
                        and row.get("Tanggal", "").strip() == date_text
                        and row.get("Status", "").strip().lower()
                        in {
                            "tanpa keterangan",
                            "tanpa_keterangan",
                            "alpha",
                            "alpa",
                        }
                    )
                ]

                with open(
                    ATTENDANCE_FILE,
                    "w",
                    newline="",
                    encoding="utf-8-sig",
                ) as file:
                    writer = csv.DictWriter(
                        file,
                        fieldnames=[
                            "Nama",
                            "Tanggal",
                            "Jam",
                            "Skor",
                            "Status",
                            "Keterangan",
                        ],
                    )
                    writer.writeheader()
                    writer.writerows(kept)

            except Exception as error:
                QMessageBox.critical(
                    self,
                    "Gagal Memperbarui",
                    f"Data Tanpa Keterangan tidak dapat dikoreksi.\n\n{error}",
                )
                return

        try:
            ensure_attendance_schema()
            file_exists = ATTENDANCE_FILE.exists()

            with open(
                ATTENDANCE_FILE,
                "a",
                newline="",
                encoding="utf-8-sig",
            ) as file:
                writer = csv.writer(file)

                if not file_exists:
                    writer.writerow([
                        "Nama",
                        "Tanggal",
                        "Jam",
                        "Skor",
                        "Status",
                        "Keterangan",
                    ])

                writer.writerow([
                    name,
                    date_text,
                    time_text,
                    "Manual",
                    status,
                    note,
                ])

        except Exception as error:
            QMessageBox.critical(
                self,
                "Gagal Menyimpan",
                f"Presensi manual gagal disimpan.\n\n{error}",
            )
            return

        self.refresh_all()
        self.stack.setCurrentIndex(2)
        self.fill_attendance_table(self.attendance)

        QMessageBox.information(
            self,
            "Berhasil",
            (
                f"Presensi manual tersimpan.\n\n"
                f"Nama: {name}\n"
                f"Tanggal: {date_text}\n"
                f"Jam: {time_text}\n"
                f"Status: {status}"
            ),
        )

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "Scanly - Portal Admin"
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

        # Cek status tanpa keterangan secara berkala. Kalau dashboard
        # tetap terbuka melewati jam 18:00, sistem akan menandai user
        # yang belum memiliki presensi pada hari kerja tersebut.
        self._absence_timer = QTimer(self)
        self._absence_timer.timeout.connect(self.check_auto_absence)
        self._absence_timer.start(60_000)

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
        subtitle_label = QLabel("Portal Admin")
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
            ("▦", "Halaman Utama"),
            ("●", "Pengguna"),
            ("▤", "Riwayat Presensi"),
            ("▥", "Laporan"),
            ("⚙", "Pengaturan"),

                
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
            "Admin"
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

        layout.addSpacing(12)

        logout_button = QPushButton("↪  KELUAR")
        logout_button.setObjectName("LogoutButton")
        logout_button.setCursor(Qt.PointingHandCursor)
        logout_button.setFixedHeight(40)
        logout_button.clicked.connect(self.logout)
        layout.addWidget(logout_button)

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
            "Cari data presensi..."
        )

        self.global_search.setFixedWidth(320)
        self.global_search.setMinimumHeight(38)

        self.global_search.textChanged.connect(
            self.global_search_changed
        )

        layout.addWidget(
            self.global_search
        )

        layout.addStretch()

        status = QLabel(
            "●  SISTEM AKTIF"
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
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 25, 30, 30)
        layout.setSpacing(16)

        header = self.page_header(
            "Halaman Utama",
            "Ringkasan absensi dan persentase kehadiran bulanan."
        )

        refresh = QPushButton("↻  Muat Ulang")
        refresh.setObjectName("Secondary")
        refresh.clicked.connect(self.refresh_all)

        holiday = QPushButton("▣  Kelola Hari Libur")
        holiday.setObjectName("Secondary")
        holiday.clicked.connect(self.open_holiday_manager)

        scan = QPushButton("▶  MULAI ABSENSI")
        scan.setObjectName("Primary")
        scan.clicked.connect(self.open_attendance_scanner)

        header.addWidget(refresh)
        header.addWidget(holiday)
        header.addWidget(scan)
        layout.addLayout(header)

        self.cards_layout = QHBoxLayout()
        self.cards_layout.setSpacing(15)
        layout.addLayout(self.cards_layout)

        month_bar = QHBoxLayout()
        month_bar.setContentsMargins(0, 0, 0, 0)
        month_bar.setSpacing(10)

        period_label = QLabel("Periode kehadiran")
        period_label.setFixedWidth(140)
        month_bar.addWidget(period_label)

        self.dashboard_month = ScanlySelectBox()
        normalize_field(self.dashboard_month, 220, 40)
        self.dashboard_month.setStyleSheet(COMBO_LIGHT_STYLE)
        self.populate_month_combo(self.dashboard_month)
        self.dashboard_month.currentIndexChanged.connect(
            self.update_monthly_dashboard
        )
        month_bar.addWidget(self.dashboard_month, 0)
        month_bar.addStretch()

        self.dashboard_month_info = QLabel("")
        self.dashboard_month_info.setStyleSheet(
            "color:#687083; font-size:12px;"
        )
        month_bar.addWidget(self.dashboard_month_info)

        layout.addLayout(month_bar)

        monthly_panel = QFrame()
        monthly_panel.setObjectName("Panel")
        monthly_layout = QVBoxLayout(monthly_panel)
        monthly_layout.setContentsMargins(0, 0, 0, 0)
        monthly_layout.setSpacing(0)

        monthly_title = QLabel("REKAP KEHADIRAN")
        monthly_title.setAlignment(Qt.AlignCenter)
        monthly_title.setStyleSheet(
            "font-size:18px; font-weight:700; padding:14px 16px 8px;"
        )
        monthly_layout.addWidget(monthly_title)

        self.monthly_table = QTableWidget()
        self.monthly_table.setColumnCount(8)
        self.monthly_table.setHorizontalHeaderLabels([
            "NAMA",
            "HADIR",
            "IZIN",
            "SAKIT",
            "TANPA KETERANGAN",
            "HARI KERJA",
            "KEHADIRAN",
            "STATUS",
        ])
        self.monthly_table.horizontalHeader().setMinimumSectionSize(90)
        self.monthly_table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        self.monthly_table.setSelectionMode(
            QAbstractItemView.SingleSelection
        )
        self.monthly_table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )
        self.monthly_table.setAlternatingRowColors(True)
        self.monthly_table.setShowGrid(False)
        self.monthly_table.verticalHeader().setVisible(False)
        self.monthly_table.verticalHeader().setDefaultSectionSize(42)
        self.monthly_table.horizontalHeader().setHighlightSections(False)
        self.monthly_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.monthly_table.setMinimumHeight(260)
        self.monthly_table.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        monthly_layout.addWidget(self.monthly_table, 1)

        layout.addWidget(monthly_panel, 1)

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
            "Pengguna",
            "Kelola pengguna terdaftar dan dataset wajah."
        )

        add_button = QPushButton(
            "+  TAMBAH PENGGUNA"
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
            "0 pengguna"
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
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 25, 30, 30)
        layout.setSpacing(16)

        layout.addLayout(
            self.page_header(
                "Riwayat Presensi",
                "Lihat dan filter seluruh riwayat presensi."
            )
        )

        filter_panel = QFrame()
        filter_panel.setObjectName("Panel")
        filter_layout = QGridLayout(filter_panel)
        filter_layout.setContentsMargins(18, 16, 18, 16)
        filter_layout.setHorizontalSpacing(10)
        filter_layout.setVerticalSpacing(10)

        date_label = QLabel("Tanggal")
        date_label.setFixedWidth(70)

        self.attendance_date_filter = ScanlyDateEdit(QDate.currentDate())
        self.attendance_date_filter.setCalendarPopup(True)
        self.attendance_date_filter.setDisplayFormat("dd/MM/yyyy")
        setup_white_date_picker(self.attendance_date_filter)
        self.attendance_date_filter.setSpecialValueText("Semua tanggal")
        normalize_field(self.attendance_date_filter, 180, 40)

        self.attendance_date_all = QCheckBox("Semua tanggal")
        self.attendance_date_all.setMinimumWidth(115)

        name_label = QLabel("Nama")
        name_label.setFixedWidth(50)

        self.attendance_name_filter = ScanlySelectBox()
        self.attendance_name_filter.setStyleSheet(COMBO_LIGHT_STYLE)
        self.attendance_name_filter.addItem("Semua orang", None)
        normalize_field(self.attendance_name_filter, 240, 40)

        filter_button = QPushButton("FILTER")
        filter_button.setObjectName("Primary")
        filter_button.setFixedSize(92, 40)
        filter_button.clicked.connect(self.apply_attendance_filter)

        reset_button = QPushButton("RESET")
        reset_button.setObjectName("Secondary")
        reset_button.setFixedSize(92, 40)
        reset_button.clicked.connect(self.reset_attendance_filter)

        filter_layout.addWidget(date_label, 0, 0)
        filter_layout.addWidget(self.attendance_date_filter, 0, 1)
        filter_layout.addWidget(self.attendance_date_all, 0, 2)
        filter_layout.addWidget(name_label, 0, 3)
        filter_layout.addWidget(self.attendance_name_filter, 0, 4)
        filter_layout.addWidget(filter_button, 0, 5)
        filter_layout.addWidget(reset_button, 0, 6)
        filter_layout.setColumnStretch(7, 1)

        layout.addWidget(filter_panel)

        manual_row = QHBoxLayout()
        manual_row.setSpacing(10)

        manual_button = QPushButton("✎  TAMBAH PRESENSI MANUAL")
        manual_button.setObjectName("Primary")
        manual_button.setFixedHeight(42)
        manual_button.setMinimumWidth(245)
        manual_button.clicked.connect(self.add_manual_attendance)

        holiday_button = QPushButton("▣  HARI LIBUR")
        holiday_button.setObjectName("Secondary")
        holiday_button.setFixedHeight(42)
        holiday_button.setMinimumWidth(135)
        holiday_button.clicked.connect(self.open_holiday_manager)

        manual_row.addWidget(manual_button)
        manual_row.addWidget(holiday_button)
        manual_row.addStretch(1)
        layout.addLayout(manual_row)

        panel = QFrame()
        panel.setObjectName("Panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)

        self.attendance_table = self.create_attendance_table()
        panel_layout.addWidget(self.attendance_table)

        layout.addWidget(panel, 1)
        return page

    # ========================================================
    # REPORTS
    # ========================================================

    def create_reports(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 25, 30, 30)
        layout.setSpacing(18)

        header = self.page_header(
            "Laporan",
            "Ekspor laporan harian atau bulanan dengan filter."
        )

        export_top = QPushButton("▣  EXPORT PDF")
        export_top.setObjectName("Primary")
        export_top.clicked.connect(self.export_pdf)
        header.addWidget(export_top)
        layout.addLayout(header)

        panel = QFrame()
        panel.setObjectName("Panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(25, 25, 25, 25)
        panel_layout.setSpacing(14)

        title = QLabel("Laporan PDF Presensi")
        title.setStyleSheet(
            "font-size:19px; font-weight:700;"
        )
        panel_layout.addWidget(title)

        info = QLabel(
            "Tanggal menggunakan kalender (tidak perlu mengetik). "
            "Nama menggunakan pilihan user yang terdaftar."
        )
        info.setStyleSheet("color:#687083;")
        info.setWordWrap(True)
        panel_layout.addWidget(info)

        form_panel = QFrame()
        form_layout = QGridLayout(form_panel)
        form_layout.setContentsMargins(0, 4, 0, 4)
        form_layout.setHorizontalSpacing(14)
        form_layout.setVerticalSpacing(12)

        self.report_date = ScanlyDateEdit(QDate.currentDate())
        self.report_date.setCalendarPopup(True)
        self.report_date.setDisplayFormat("dd/MM/yyyy")
        setup_white_date_picker(self.report_date)
        normalize_field(self.report_date, 220, 40)

        self.report_all_dates = QCheckBox("Semua tanggal")
        self.report_all_dates.setMinimumWidth(120)

        date_row = QHBoxLayout()
        date_row.setContentsMargins(0, 0, 0, 0)
        date_row.setSpacing(10)
        date_row.addWidget(self.report_date)
        date_row.addWidget(self.report_all_dates)
        date_row.addStretch(1)
        date_widget = QWidget()
        date_widget.setLayout(date_row)

        self.report_person = ScanlySelectBox()
        self.report_person.setStyleSheet(COMBO_LIGHT_STYLE)
        self.report_person.addItem("Semua orang", None)
        normalize_field(self.report_person, 300, 40)

        self.report_month = ScanlySelectBox()
        self.report_month.setStyleSheet(COMBO_LIGHT_STYLE)
        self.populate_month_combo(self.report_month)
        self.report_month.currentIndexChanged.connect(
            self.update_report_month_hint
        )
        normalize_field(self.report_month, 300, 40)

        for row, label_text, widget in (
            (0, "Tanggal", date_widget),
            (1, "Nama", self.report_person),
            (2, "Bulan", self.report_month),
        ):
            label = QLabel(label_text)
            label.setFixedWidth(80)
            form_layout.addWidget(label, row, 0)
            form_layout.addWidget(widget, row, 1)

        form_layout.setColumnStretch(2, 1)
        panel_layout.addWidget(form_panel)

        self.report_hint = QLabel("")
        self.report_hint.setWordWrap(True)
        self.report_hint.setStyleSheet(
            "background:#f3f6f9; padding:12px; border-radius:8px;"
            "color:#4b5563;"
        )
        panel_layout.addWidget(self.report_hint)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)

        monthly_pdf = QPushButton("EKSPOR PDF BULANAN")
        monthly_pdf.setObjectName("Primary")
        monthly_pdf.clicked.connect(
            lambda: self.export_pdf(monthly=True)
        )

        daily_pdf = QPushButton("EKSPOR PDF BERDASARKAN FILTER")
        daily_pdf.setObjectName("Secondary")
        daily_pdf.clicked.connect(
            lambda: self.export_pdf(monthly=False)
        )

        holiday_button = QPushButton("KELOLA HARI LIBUR")
        holiday_button.setObjectName("Secondary")
        holiday_button.clicked.connect(self.open_holiday_manager)

        monthly_pdf.setFixedHeight(42)
        daily_pdf.setFixedHeight(42)
        holiday_button.setFixedHeight(42)
        monthly_pdf.setMinimumWidth(190)
        daily_pdf.setMinimumWidth(180)
        holiday_button.setMinimumWidth(170)

        buttons.addWidget(monthly_pdf)
        buttons.addWidget(daily_pdf)
        buttons.addWidget(holiday_button)
        buttons.addStretch(1)

        panel_layout.addLayout(buttons)
        layout.addWidget(panel)
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
                "Pengaturan",
                "Atur preferensi pengenalan Scanly."
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

        settings_grid = QGridLayout()
        settings_grid.setHorizontalSpacing(16)
        settings_grid.setVerticalSpacing(14)

        threshold_label = QLabel("Recognition Threshold")
        threshold_label.setFixedWidth(200)

        self.threshold = QSpinBox()

        self.threshold.setRange(
            1,
            200
        )

        self.threshold.setValue(
            65
        )

        normalize_field(self.threshold, 110, 40)
        self.threshold.setFixedWidth(110)

        settings_grid.addWidget(threshold_label, 0, 0)
        settings_grid.addWidget(self.threshold, 0, 1)

        voting_label = QLabel("Multi-frame Voting")
        voting_label.setFixedWidth(200)

        self.voting = QSpinBox()

        self.voting.setRange(
            1,
            5
        )

        self.voting.setValue(
            4
        )

        normalize_field(self.voting, 110, 40)
        self.voting.setFixedWidth(110)

        voting_hint = QLabel("dari 5 frame")
        voting_hint.setStyleSheet("color:#687083;")

        voting_widget = QWidget()
        voting_layout = QHBoxLayout(voting_widget)
        voting_layout.setContentsMargins(0, 0, 0, 0)
        voting_layout.setSpacing(10)
        voting_layout.addWidget(self.voting)
        voting_layout.addWidget(voting_hint)
        voting_layout.addStretch(1)

        settings_grid.addWidget(voting_label, 1, 0)
        settings_grid.addWidget(voting_widget, 1, 1)

        cooldown_label = QLabel("Result Cooldown")
        cooldown_label.setFixedWidth(200)

        self.cooldown = QSpinBox()

        self.cooldown.setRange(
            0,
            60
        )

        self.cooldown.setValue(
            2
        )

        normalize_field(self.cooldown, 110, 40)
        self.cooldown.setFixedWidth(110)

        cooldown_hint = QLabel("detik")
        cooldown_hint.setStyleSheet("color:#687083;")

        cooldown_widget = QWidget()
        cooldown_layout = QHBoxLayout(cooldown_widget)
        cooldown_layout.setContentsMargins(0, 0, 0, 0)
        cooldown_layout.setSpacing(10)
        cooldown_layout.addWidget(self.cooldown)
        cooldown_layout.addWidget(cooldown_hint)
        cooldown_layout.addStretch(1)

        settings_grid.addWidget(cooldown_label, 2, 0)
        settings_grid.addWidget(cooldown_widget, 2, 1)

        settings_grid.setColumnStretch(2, 1)
        panel_layout.addLayout(settings_grid)

        self.liveness = QCheckBox(
            "Liveness detection aktif"
        )
        self.liveness.setMinimumHeight(36)

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
            "SIMPAN PENGATURAN"
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
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "NAMA",
            "TANGGAL",
            "JAM",
            "SKOR",
            "STATUS",
            "KETERANGAN",
        ])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setShowGrid(False)
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

    def auto_mark_unattended_today(self):
        """
        Setelah jam kerja selesai (19:00), setiap pengguna aktif yang
        belum memiliki catatan presensi untuk hari kerja hari ini
        otomatis diberi status "Tanpa Keterangan".

        Sabtu/Minggu dan hari libur tidak diproses.
        """
        now = datetime.now()
        today = now.date()

        # Hari non-kerja tidak boleh menghasilkan status alpha.
        if not is_working_day(today):
            return False

        # Sebelum akhir jam kerja, jangan menandai siapa pun.
        cutoff = datetime.strptime("19:00", "%H:%M").time()
        if now.time() < cutoff:
            return False

        existing_names = {
            str(row.get("Nama", "")).strip()
            for row in self.attendance
            if str(row.get("Tanggal", "")).strip()
            == today.strftime("%Y-%m-%d")
            and str(row.get("Nama", "")).strip()
        }

        missing = [
            person for person in self.people
            if str(person.get("Nama", "")).strip()
            and str(person.get("Status", "Aktif")).strip().lower()
                in {"aktif", "active", ""}
            and str(person.get("Nama", "")).strip()
                not in existing_names
        ]

        if not missing:
            return False

        date_text = today.strftime("%Y-%m-%d")
        changed = False

        try:
            ensure_attendance_schema()
            file_exists = ATTENDANCE_FILE.exists()

            with open(
                ATTENDANCE_FILE,
                "a",
                newline="",
                encoding="utf-8-sig",
            ) as file:
                writer = csv.writer(file)

                if not file_exists:
                    writer.writerow([
                        "Nama",
                        "Tanggal",
                        "Jam",
                        "Skor",
                        "Status",
                        "Keterangan",
                    ])

                for person in missing:
                    writer.writerow([
                        str(person.get("Nama", "")).strip(),
                        date_text,
                        "",
                        "AUTO",
                        "Tanpa Keterangan",
                        "",
                    ])
                    changed = True

        except Exception as error:
            print(
                "[WARNING] Gagal membuat status Tanpa Keterangan otomatis:",
                error,
            )

        return changed

    def check_auto_absence(self):
        self.people = load_people()
        self.attendance = load_attendance()

        if self.auto_mark_unattended_today():
            self.attendance = load_attendance()
            self.update_dashboard_cards()
            self.fill_attendance_table(self.attendance)
            self.populate_attendance_filters()
            self.update_monthly_dashboard()

    def refresh_all(self):
        self.people = load_people()
        self.attendance = load_attendance()

        # Jalankan setelah data dimuat, lalu reload agar rekap langsung
        # menampilkan status Tanpa Keterangan yang baru dibuat.
        if self.auto_mark_unattended_today():
            self.attendance = load_attendance()
        self.attendance = load_attendance()

        self.update_dashboard_cards()
        self.fill_attendance_table(
            self.attendance
        )
        self.load_people_table()
        self.populate_attendance_filters()
        self.populate_report_people()
        self.update_monthly_dashboard()
        self.update_report_month_hint()

    # ========================================================
    # DASHBOARD CARDS
    # ========================================================

    def populate_month_combo(self, combo):
        combo.blockSignals(True)
        combo.clear()

        now = datetime.now()
        for offset in range(-11, 2):
            year = now.year
            month = now.month + offset

            while month <= 0:
                year -= 1
                month += 12

            while month > 12:
                year += 1
                month -= 12

            label = f"{calendar.month_name[month]} {year}"
            combo.addItem(label, (year, month))

        # Current month is the last item.
        combo.setCurrentIndex(combo.count() - 1)
        combo.blockSignals(False)

    def populate_attendance_filters(self):
        if not hasattr(self, "attendance_name_filter"):
            return

        current = self.attendance_name_filter.currentData()
        self.attendance_name_filter.blockSignals(True)
        self.attendance_name_filter.clear()
        self.attendance_name_filter.addItem("Semua orang", None)

        names = sorted({
            row.get("Nama", "").strip()
            for row in self.people
            if row.get("Nama", "").strip()
        })

        for name in names:
            self.attendance_name_filter.addItem(name, name)

        if current:
            index = self.attendance_name_filter.findData(current)
            if index >= 0:
                self.attendance_name_filter.setCurrentIndex(index)

        self.attendance_name_filter.blockSignals(False)

    def populate_report_people(self):
        if not hasattr(self, "report_person"):
            return

        current = self.report_person.currentData()
        self.report_person.blockSignals(True)
        self.report_person.clear()
        self.report_person.addItem("Semua orang", None)

        for person in sorted(
            self.people,
            key=lambda row: row.get("Nama", "").lower()
        ):
            name = person.get("Nama", "").strip()
            if name:
                self.report_person.addItem(
                    name,
                    name,
                )

        if current:
            index = self.report_person.findData(current)
            if index >= 0:
                self.report_person.setCurrentIndex(index)

        self.report_person.blockSignals(False)

    def update_dashboard_cards(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        today = datetime.now().strftime("%Y-%m-%d")
        today_rows = [
            row for row in self.attendance
            if row.get("Tanggal", "") == today
        ]

        unique_hadir = len({
            row.get("Nama", "")
            for row in today_rows
            if attendance_status_is_present(row.get("Status", ""))
        })

        izin_today = len({
            row.get("Nama", "")
            for row in today_rows
            if row.get("Status", "").strip().lower() == "izin"
        })

        sakit_today = len({
            row.get("Nama", "")
            for row in today_rows
            if row.get("Status", "").strip().lower() == "sakit"
        })

        cards = [
            create_card(
                "Total Pengguna",
                len(self.people),
                "◉",
                "All Time"
            ),
            create_card(
                "Hadir Hari Ini",
                unique_hadir,
                "✓",
                "Hari Ini"
            ),
            create_card(
                "Izin Hari Ini",
                izin_today,
                "◷",
                "Hari Ini"
            ),
            create_card(
                "Sakit Hari Ini",
                sakit_today,
                "!",
                "Hari Ini"
            ),
        ]

        for card in cards:
            self.cards_layout.addWidget(card)

    def update_monthly_dashboard(self):
        if not hasattr(self, "dashboard_month"):
            return

        period = self.dashboard_month.currentData()
        if not period:
            return

        year, month = period
        holidays = load_holidays()
        workdays = working_days_in_month(
            year, month, holidays
        )

        self.monthly_table.setRowCount(0)

        for person in sorted(
            self.people,
            key=lambda row: row.get("Nama", "").lower()
        ):
            name = person.get("Nama", "").strip()
            if not name:
                continue

            item = monthly_person_summary(
                name,
                year,
                month,
                self.attendance,
                holidays,
            )

            row_index = self.monthly_table.rowCount()
            self.monthly_table.insertRow(row_index)

            values = [
                name,
                str(item["hadir"]),
                str(item["izin"]),
                str(item["sakit"]),
                str(item["tanpa_keterangan"]),
                str(item["hari_kerja"]),
                f"{item['percentage']:.2f}%",
                (
                    "100%" if item["percentage"] >= 99.999
                    else "Berjalan"
                ),
            ]

            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setTextAlignment(
                    Qt.AlignCenter
                    if col > 0
                    else Qt.AlignLeft | Qt.AlignVCenter
                )
                self.monthly_table.setItem(
                    row_index, col, cell
                )

        month_name = calendar.month_name[month]
        holiday_count = sum(
            1 for date_text in holidays
            if date_text.startswith(
                f"{year:04d}-{month:02d}-"
            )
        )

        self.dashboard_month_info.setText(
            f"{month_name} {year} • "
            f"{workdays} hari kerja • "
            f"{holiday_count} hari libur"
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

        table.setRowCount(0)

        for row in rows:
            index = table.rowCount()
            table.insertRow(index)

            values = [
                row.get("Nama", ""),
                row.get("Tanggal", ""),
                row.get("Jam", ""),
                row.get("Skor", ""),
                row.get("Status", ""),
                row.get("Keterangan", ""),
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column >= 1:
                    item.setTextAlignment(
                        Qt.AlignCenter
                    )
                table.setItem(index, column, item)

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
            register = QPushButton("DAFTAR")
            register.setObjectName("Blue")
            register.setFont(QFont("Segoe UI", 8, QFont.Bold))
            register.setFixedHeight(22)
            register.setFixedWidth(72)
            register.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            register.setStyleSheet(
                "QPushButton{ color:#0f1724; background:#eef3ff; border:1px solid rgba(36,81,214,0.08); border-radius:4px; padding:2px 4px; font-size:11px; }"
                "QPushButton:pressed{ background:#dfe8ff; }"
            )
            register.setToolTip("DAFTAR WAJAH")
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
        date = None
        if not self.attendance_date_all.isChecked():
            date = (
                self.attendance_date_filter
                .date()
                .toPython()
                .strftime("%Y-%m-%d")
            )

        name = self.attendance_name_filter.currentData()

        result = []
        for row in self.attendance:
            date_ok = (
                date is None
                or row.get("Tanggal", "") == date
            )
            name_ok = (
                name is None
                or row.get("Nama", "") == name
            )

            if date_ok and name_ok:
                result.append(row)

        self.fill_attendance_table(result)

    def reset_attendance_filter(self):
        self.attendance_date_all.setChecked(True)
        self.attendance_date_filter.setDate(QDate.currentDate())
        self.attendance_name_filter.setCurrentIndex(0)
        self.fill_attendance_table(self.attendance)

    def open_holiday_manager(self):
        dialog = HolidayDialog(self)
        dialog.exec()
        self.update_monthly_dashboard()
        self.update_report_month_hint()

    def update_report_month_hint(self):
        if not hasattr(self, "report_month"):
            return

        period = self.report_month.currentData()
        if not period:
            return

        year, month = period
        holidays = load_holidays()
        workdays = working_days_in_month(
            year, month, holidays
        )

        self.report_hint.setText(
            f"Periode: {calendar.month_name[month]} {year} • "
            f"Hari kerja: {workdays}. "
            "Persentase bulanan = hari hadir / total hari kerja "
            "Senin-Jumat dalam bulan tersebut, setelah dikurangi "
            "hari libur yang didaftarkan."
        )

    # ========================================================
    # GLOBAL SEARCH
    # ========================================================

    def global_search_changed(
        self,
        text
    ):
        """
        Pencarian global diarahkan ke halaman Riwayat Presensi.
        Dashboard tidak lagi memiliki tabel "Absensi Terbaru".
        """
        query = text.strip().lower()

        if not hasattr(self, "stack"):
            return

        self.stack.setCurrentIndex(2)

        if not query:
            self.fill_attendance_table(
                self.attendance,
                self.attendance_table
            )
            return

        result = []
        for row in self.attendance:
            joined = " ".join(
                str(value) for value in row.values()
            ).lower()

            if query in joined:
                result.append(row)

        self.fill_attendance_table(
            result,
            self.attendance_table
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
                    "AmbangPengenalan",
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
                "Pengaturan",
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

    def export_pdf(self, monthly=False):
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import mm
            from reportlab.platypus import (
                SimpleDocTemplate,
                Paragraph,
                Spacer,
                Table,
                TableStyle,
            )
        except ImportError:
            QMessageBox.critical(
                self,
                "ReportLab Belum Terinstall",
                "Install dengan:\n\npip install reportlab",
            )
            return

        name = (
            self.report_person.currentData()
            if hasattr(self, "report_person")
            else None
        )

        period = (
            self.report_month.currentData()
            if hasattr(self, "report_month")
            else None
        )

        if not period:
            now = datetime.now()
            period = (now.year, now.month)

        year, month = period
        holidays = load_holidays()

        rows = []

        if monthly:
            prefix = f"{year:04d}-{month:02d}-"
            for row in self.attendance:
                if not row.get("Tanggal", "").startswith(prefix):
                    continue
                if name and row.get("Nama", "") != name:
                    continue
                rows.append(row)
        else:
            date_text = None
            if hasattr(self, "report_all_dates"):
                if not self.report_all_dates.isChecked():
                    date_text = (
                        self.report_date
                        .date()
                        .toPython()
                        .strftime("%Y-%m-%d")
                    )

            for row in self.attendance:
                if date_text and row.get("Tanggal", "") != date_text:
                    continue
                if name and row.get("Nama", "") != name:
                    continue
                rows.append(row)

        if monthly:
            if not rows and name:
                # A monthly report can still be useful even with no rows.
                pass
        elif not rows:
            QMessageBox.information(
                self,
                "Tidak Ada Data",
                "Tidak ada data attendance untuk filter tersebut.",
            )
            return

        REPORT_DIR.mkdir(parents=True, exist_ok=True)

        suffix_name = (
            re.sub(r"[^a-zA-Z0-9_-]+", "_", name)
            if name
            else "semua_orang"
        )

        if monthly:
            filename = (
                f"scanly_bulanan_{year:04d}_{month:02d}_"
                f"{suffix_name}_{datetime.now():%Y%m%d_%H%M%S}.pdf"
            )
        else:
            filename = (
                f"scanly_harian_{suffix_name}_"
                f"{datetime.now():%Y%m%d_%H%M%S}.pdf"
            )

        output = REPORT_DIR / filename

        styles = getSampleStyleSheet()
        document = SimpleDocTemplate(
            str(output),
            pagesize=A4,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
            topMargin=15 * mm,
            bottomMargin=15 * mm,
            title="Laporan Presensi Scanly",
        )

        story = [
            Paragraph("<b>SCANLY</b>", styles["Title"]),
            Paragraph(
                (
                    "Laporan Presensi Bulanan"
                    if monthly
                    else "Laporan Presensi"
                ),
                styles["Heading2"],
            ),
            Spacer(1, 4 * mm),
        ]

        if monthly:
            month_label = f"{calendar.month_name[month]} {year}"
            workdays = working_days_in_month(
                year, month, holidays
            )

            story.append(
                Paragraph(
                    f"Periode: <b>{month_label}</b>",
                    styles["Normal"],
                )
            )
            story.append(
                Paragraph(
                    f"Hari kerja: <b>{workdays}</b> "
                    "(Senin-Jumat dikurangi hari libur)",
                    styles["Normal"],
                )
            )

            if name:
                summary = monthly_person_summary(
                    name,
                    year,
                    month,
                    self.attendance,
                    holidays,
                )
                story.append(
                    Paragraph(
                        (
                            f"Nama: <b>{name}</b> &nbsp;&nbsp; "
                            f"Kehadiran: <b>"
                            f"{summary['percentage']:.2f}%</b> &nbsp;&nbsp; "
                            f"Hadir: {summary['hadir']} &nbsp;&nbsp; "
                            f"Izin: {summary['izin']} &nbsp;&nbsp; "
                            f"Sakit: {summary['sakit']} &nbsp;&nbsp; "
                            f"Tanpa Keterangan: "
                            f"{summary['tanpa_keterangan']}"
                        ),
                        styles["Normal"],
                    )
                )
            else:
                story.append(
                    Paragraph(
                        "Nama: <b>Semua orang</b>",
                        styles["Normal"],
                    )
                )

            story.append(Spacer(1, 5 * mm))

            table_data = [[
                "Nama",
                "Hadir",
                "Izin",
                "Sakit",
                "Tanpa Ket.",
                "Hari Kerja",
                "Kehadiran",
            ]]

            people = (
                [p for p in self.people if p.get("Nama") == name]
                if name
                else self.people
            )

            for person in sorted(
                people,
                key=lambda p: p.get("Nama", "").lower()
            ):
                person_name = person.get("Nama", "").strip()
                if not person_name:
                    continue

                summary = monthly_person_summary(
                    person_name,
                    year,
                    month,
                    self.attendance,
                    holidays,
                )

                table_data.append([
                    person_name,
                    str(summary["hadir"]),
                    str(summary["izin"]),
                    str(summary["sakit"]),
                    str(summary["tanpa_keterangan"]),
                    str(summary["hari_kerja"]),
                    f"{summary['percentage']:.2f}%",
                ])

            table = Table(
                table_data,
                repeatRows=1,
                colWidths=[
                    42 * mm,
                    17 * mm,
                    17 * mm,
                    17 * mm,
                    28 * mm,
                    22 * mm,
                    25 * mm,
                ],
            )
        else:
            date_filter = (
                "Semua tanggal"
                if getattr(self, "report_all_dates", None)
                and self.report_all_dates.isChecked()
                else self.report_date.date().toPython().strftime("%Y-%m-%d")
            )

            story.append(
                Paragraph(
                    f"Tanggal: <b>{date_filter}</b>",
                    styles["Normal"],
                )
            )
            story.append(
                Paragraph(
                    f"Nama: <b>{name or 'Semua orang'}</b>",
                    styles["Normal"],
                )
            )
            story.append(Spacer(1, 5 * mm))

            table_data = [[
                "Nama",
                "Tanggal",
                "Jam",
                "Skor",
                "Status",
                "Keterangan",
            ]]

            for row in rows:
                table_data.append([
                    row.get("Nama", ""),
                    row.get("Tanggal", ""),
                    row.get("Jam", ""),
                    row.get("Skor", ""),
                    row.get("Status", ""),
                    row.get("Keterangan", ""),
                ])

            table = Table(
                table_data,
                repeatRows=1,
                colWidths=[
                    38 * mm,
                    28 * mm,
                    24 * mm,
                    22 * mm,
                    30 * mm,
                    38 * mm,
                ],
            )

        table.setStyle(
            TableStyle([
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#eef0f3"),
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor("#d5d9df"),
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "ALIGN",
                    (1, 1),
                    (-1, -1),
                    "CENTER",
                ),
            ])
        )

        story.append(table)
        story.append(Spacer(1, 5 * mm))
        story.append(
            Paragraph(
                (
                    f"Generated: "
                    f"{datetime.now():%d-%m-%Y %H:%M:%S} • "
                    f"Total data: {len(rows)}"
                ),
                styles["Normal"],
            )
        )

        try:
            document.build(story)
        except Exception as error:
            QMessageBox.critical(
                self,
                "Gagal Mengekspor PDF",
                str(error),
            )
            return

        QMessageBox.information(
            self,
            "Ekspor Berhasil",
            f"PDF berhasil dibuat:\n\n{output}",
        )

    # ========================================================
    # KELUAR DARI ADMIN
    # ========================================================

    def logout(self):
        reply = QMessageBox.question(
            self,
            "Keluar",
            "Yakin ingin keluar dari dashboard admin?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        self._logging_out = True
        self.close()

        login = LoginDialog()

        if login.exec() == QDialog.Accepted:
            new_window = AdminWindow()
            new_window.show()

            # Keep a Python reference so the new window remains alive.
            self._replacement_window = new_window
        else:
            QApplication.instance().quit()

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