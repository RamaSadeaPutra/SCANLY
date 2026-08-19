import sys
import math
import time
import csv
import os

import cv2
import mediapipe as mp

from datetime import datetime

from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView
)

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap


# =========================================================
# KONFIGURASI
# =========================================================

MODEL_PATH = "face_model/scanly_faces.yml"
LANDMARKER_PATH = "models/face_landmarker.task"

NAME = "Rama Sadea Putra As"

# ---------------------------------------------------------
# FACE RECOGNITION
# ---------------------------------------------------------

CONFIDENCE_THRESHOLD = 65

# ---------------------------------------------------------
# JARAK WAJAH
# ---------------------------------------------------------

MIN_FACE_WIDTH = 120
MIN_FACE_HEIGHT = 120

# ---------------------------------------------------------
# UKURAN FACE LBPH
# ---------------------------------------------------------

FACE_SIZE = (200, 200)

# ---------------------------------------------------------
# LIVENESS
# ---------------------------------------------------------

LIVENESS_DURATION = 2.5

# ---------------------------------------------------------
# COOLDOWN
# ---------------------------------------------------------

RESULT_COOLDOWN = 2.0

# ---------------------------------------------------------
# MATA
# ---------------------------------------------------------

EYE_OPEN_THRESHOLD = 0.24
EYE_CLOSED_THRESHOLD = 0.20

# ---------------------------------------------------------
# FILE ABSENSI
# ---------------------------------------------------------

ATTENDANCE_FILE = "attendance.csv"


# =========================================================
# PREPROCESSING WAJAH - SAMA DENGAN register_face.py
# =========================================================

def preprocess_face(face_bgr, face_size=FACE_SIZE):
    """
    Preprocessing yang sama untuk training dan recognition:
    grayscale -> resize -> CLAHE ringan -> blur ringan.
    """

    if face_bgr is None or face_bgr.size == 0:
        return None

    gray = cv2.cvtColor(
        face_bgr,
        cv2.COLOR_BGR2GRAY
    )

    gray = cv2.resize(
        gray,
        face_size,
        interpolation=cv2.INTER_AREA
    )

    clahe = cv2.createCLAHE(
        clipLimit=1.5,
        tileGridSize=(8, 8)
    )

    gray = clahe.apply(gray)

    gray = cv2.GaussianBlur(
        gray,
        (3, 3),
        0
    )

    return gray



# =========================================================
# HITUNG EAR
# =========================================================

def calculate_ear(landmarks, indices):

    points = []

    for index in indices:

        point = landmarks[index]

        points.append(
            (
                point.x,
                point.y
            )
        )

    vertical_1 = math.dist(
        points[1],
        points[5]
    )

    vertical_2 = math.dist(
        points[2],
        points[4]
    )

    horizontal = math.dist(
        points[0],
        points[3]
    )

    if horizontal == 0:
        return 0.0

    return (
        vertical_1 + vertical_2
    ) / (
        2.0 * horizontal
    )


# =========================================================
# MAIN WINDOW
# =========================================================

class ScanlyWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "Scanly - Face Recognition & Attendance"
        )

        self.setMinimumSize(
            1100,
            850
        )

        # =================================================
        # STATE
        # =================================================
        self.blink_state = 0

        # Landmark mata MediaPipe
        self.left_eye = [
            33, 160, 158, 133, 153, 144
        ]

        self.right_eye = [
            362, 385, 387, 263, 373, 380
        ]

        self.liveness_start = None
        self.liveness_finished = False
        self.recognized_name = "Unknown"

        self.recognition_score = 0.0

        # None
        # success
        # failure

        self.result_state = None

        # =================================================
        # SUCCESS STATE
        # =================================================

        self.attendance_recorded = False

        self.attendance_time = None

        self.success_cooldown_start = None

        self.waiting_for_face_exit = False

        # =================================================
        # FAILURE STATE
        # =================================================

        self.failure_cooldown_start = None

        # Cooldown untuk orang yang sudah absen hari ini
        self.duplicate_cooldown_start = None

        # =================================================
        # UI
        # =================================================

        self.create_ui()

        # =================================================
        # MEDIAPIPE
        # =================================================

        self.create_landmarker()

        # =================================================
        # FACE RECOGNIZER
        # =================================================

        self.create_recognizer()

        # =================================================
        # CAMERA
        # =================================================

        self.camera = cv2.VideoCapture(0)

        if not self.camera.isOpened():

            self.status_label.setText(
                "ERROR: Kamera tidak dapat dibuka."
            )

            return

        # =================================================
        # TIMER CAMERA
        # =================================================

        self.timer = QTimer()

        self.timer.timeout.connect(
            self.update_camera
        )

        self.timer.start(30)

    # =====================================================
    # CREATE UI
    # =====================================================

    def create_ui(self):

        central_widget = QWidget()

        self.setCentralWidget(
            central_widget
        )

        main_layout = QVBoxLayout()

        central_widget.setLayout(
            main_layout
        )

        # -------------------------------------------------
        # TITLE
        # -------------------------------------------------

        title = QLabel(
            "SCANLY"
        )

        title.setAlignment(
            Qt.AlignCenter
        )

        title.setStyleSheet(
            """
            font-size: 28px;
            font-weight: bold;
            """
        )

        subtitle = QLabel(
            "Face Recognition & Liveness Detection"
        )

        subtitle.setAlignment(
            Qt.AlignCenter
        )

        subtitle.setStyleSheet(
            """
            font-size: 15px;
            """
        )

        main_layout.addWidget(
            title
        )

        main_layout.addWidget(
            subtitle
        )

        # -------------------------------------------------
        # CAMERA
        # -------------------------------------------------

        self.camera_label = QLabel()

        self.camera_label.setAlignment(
            Qt.AlignCenter
        )

        self.camera_label.setMinimumHeight(
            450
        )

        self.camera_label.setStyleSheet(
            """
            background-color: black;
            """
        )

        main_layout.addWidget(
            self.camera_label
        )

        # -------------------------------------------------
        # STATUS
        # -------------------------------------------------

        self.status_label = QLabel(
            "Menunggu wajah..."
        )

        self.status_label.setAlignment(
            Qt.AlignCenter
        )

        self.status_label.setStyleSheet(
            """
            font-size: 18px;
            font-weight: bold;
            padding: 8px;
            """
        )

        main_layout.addWidget(
            self.status_label
        )

        # -------------------------------------------------
        # INFO
        # -------------------------------------------------

        info_layout = QHBoxLayout()

        self.name_info = QLabel(
            "Nama: -"
        )

        self.score_info = QLabel(
            "Score: -"
        )

        self.time_info = QLabel(
            "Waktu: -"
        )

        info_layout.addWidget(
            self.name_info
        )

        info_layout.addWidget(
            self.score_info
        )

        info_layout.addWidget(
            self.time_info
        )

        main_layout.addLayout(
            info_layout
        )

        # -------------------------------------------------
        # HISTORY TITLE
        # -------------------------------------------------

        history_title = QLabel(
            "Riwayat Absensi"
        )

        history_title.setStyleSheet(
            """
            font-size: 18px;
            font-weight: bold;
            margin-top: 8px;
            """
        )

        main_layout.addWidget(
            history_title
        )

        # -------------------------------------------------
        # TABLE
        # -------------------------------------------------

        self.attendance_table = QTableWidget()

        self.attendance_table.setColumnCount(
            5
        )

        self.attendance_table.setHorizontalHeaderLabels(
            [
                "Nama",
                "Tanggal",
                "Jam",
                "Score",
                "Status"
            ]
        )

        self.attendance_table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )

        self.attendance_table.setSelectionBehavior(
            QTableWidget.SelectRows
        )

        self.attendance_table.setAlternatingRowColors(
            True
        )

        header = (
            self.attendance_table.horizontalHeader()
        )

        header.setSectionResizeMode(
            QHeaderView.Stretch
        )

        self.attendance_table.setMaximumHeight(
            220
        )

        main_layout.addWidget(
            self.attendance_table
        )

        # -------------------------------------------------
        # LOAD HISTORY
        # -------------------------------------------------

        self.load_attendance_history()

    # =====================================================
    # CREATE LANDMARKER
    # =====================================================

    def create_landmarker(self):

        BaseOptions = (
            mp.tasks.BaseOptions
        )

        FaceLandmarker = (
            mp.tasks.vision.FaceLandmarker
        )

        FaceLandmarkerOptions = (
            mp.tasks.vision.FaceLandmarkerOptions
        )

        options = FaceLandmarkerOptions(
            base_options=BaseOptions(
                model_asset_path=LANDMARKER_PATH
            ),
            num_faces=1
        )

        self.landmarker = (
            FaceLandmarker.create_from_options(
                options
            )
        )

    # =====================================================
    # CREATE RECOGNIZER
    # =====================================================

    def create_recognizer(self):

        self.recognizer = (
            cv2.face.LBPHFaceRecognizer_create()
        )

        self.recognizer.read(
            MODEL_PATH
        )

    # =====================================================
    # RESET LIVENESS
    # =====================================================

    def reset_liveness(self):

        self.blink_state = 0

        self.liveness_start = None

        self.liveness_finished = False

    # =====================================================
    # START NEW SCAN
    # =====================================================

    def start_new_scan(self):

        self.reset_liveness()

        self.recognized_name = "Unknown"

        self.recognition_score = 0.0

        self.result_state = None

        self.success_cooldown_start = None

        self.failure_cooldown_start = None
        self.duplicate_cooldown_start = None

        self.attendance_recorded = False

        self.attendance_time = None

        self.waiting_for_face_exit = False

        self.name_info.setText(
            "Nama: -"
        )

        self.score_info.setText(
            "Score: -"
        )

        self.time_info.setText(
            "Waktu: -"
        )

        self.status_label.setText(
            "Silakan berkedip"
        )

    # =====================================================
    # RECOGNIZE FACE
    # =====================================================

    def recognize_face(
        self,
        frame,
        landmarks
    ):

        height, width, _ = frame.shape

        xs = [
            point.x
            for point in landmarks
        ]

        ys = [
            point.y
            for point in landmarks
        ]

        min_x = max(
            0,
            int(min(xs) * width)
        )

        max_x = min(
            width,
            int(max(xs) * width)
        )

        min_y = max(
            0,
            int(min(ys) * height)
        )

        max_y = min(
            height,
            int(max(ys) * height)
        )

        face_width = max_x - min_x

        face_height = max_y - min_y

        box = (
            min_x,
            min_y,
            max_x,
            max_y
        )

        # -------------------------------------------------
        # TERLALU JAUH
        # -------------------------------------------------

        if (
            face_width < MIN_FACE_WIDTH
            or
            face_height < MIN_FACE_HEIGHT
        ):

            return (
                "TOO_FAR",
                0.0,
                box
            )

        # -------------------------------------------------
        # MARGIN
        # -------------------------------------------------

        margin_x = int(
            face_width * 0.15
        )

        margin_y = int(
            face_height * 0.15
        )

        crop_x1 = max(
            0,
            min_x - margin_x
        )

        crop_x2 = min(
            width,
            max_x + margin_x
        )

        crop_y1 = max(
            0,
            min_y - margin_y
        )

        crop_y2 = min(
            height,
            max_y + margin_y
        )

        # -------------------------------------------------
        # CROP
        # -------------------------------------------------

        face = frame[
            crop_y1:crop_y2,
            crop_x1:crop_x2
        ]

        if face.size == 0:

            return (
                "Unknown",
                999.0,
                box
            )

        # -------------------------------------------------
        # PREPROCESSING YANG SAMA DENGAN TRAINING
        # -------------------------------------------------

        face_gray = preprocess_face(
            face
        )

        if face_gray is None:

            return (
                "Unknown",
                999.0,
                box
            )

        # -------------------------------------------------
        # RECOGNITION
        # -------------------------------------------------

        label, score = (
            self.recognizer.predict(
                face_gray
            )
        )

        # -------------------------------------------------
        # KEPUTUSAN
        # -------------------------------------------------

        if (
            label == 0
            and
            score < CONFIDENCE_THRESHOLD
        ):

            name = NAME

        else:

            name = "Unknown"

        return (
            name,
            score,
            box
        )

    # =====================================================
    # CEK ABSEN HARI INI
    # =====================================================

    def already_attended_today(self, name):

        if not os.path.exists(ATTENDANCE_FILE):
            return False

        today = datetime.now().strftime("%Y-%m-%d")

        try:
            with open(
                ATTENDANCE_FILE,
                "r",
                encoding="utf-8-sig"
            ) as file:

                reader = csv.DictReader(file)

                for row in reader:
                    if (
                        row.get("Nama", "").strip() == name
                        and row.get("Tanggal", "").strip() == today
                        and row.get("Status", "").strip().lower() == "hadir"
                    ):
                        return True

        except Exception as error:

            print(
                f"[ERROR] Gagal mengecek absensi hari ini: {error}"
            )

        return False

    # =====================================================
    # SAVE ATTENDANCE
    # =====================================================

    def save_attendance(
        self,
        name,
        score
    ):

        file_exists = os.path.exists(
            ATTENDANCE_FILE
        )

        now = datetime.now()

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

                # -----------------------------------------
                # HEADER
                # -----------------------------------------

                if not file_exists:

                    writer.writerow(
                        [
                            "Nama",
                            "Tanggal",
                            "Jam",
                            "Score",
                            "Status"
                        ]
                    )

                # -----------------------------------------
                # DATA
                # -----------------------------------------

                writer.writerow(
                    [
                        name,
                        now.strftime(
                            "%Y-%m-%d"
                        ),
                        now.strftime(
                            "%H:%M:%S"
                        ),
                        f"{score:.2f}",
                        "Hadir"
                    ]
                )

            print(
                f"[OK] Absensi tersimpan: {name}"
            )

            return True

        except Exception as error:

            print(
                f"[ERROR] Gagal menyimpan absensi: {error}"
            )

            return False

    # =====================================================
    # LOAD ATTENDANCE HISTORY
    # =====================================================

    def load_attendance_history(self):

        if not os.path.exists(
            ATTENDANCE_FILE
        ):

            return

        try:

            with open(
                ATTENDANCE_FILE,
                "r",
                encoding="utf-8-sig"
            ) as file:

                reader = csv.reader(
                    file
                )

                rows = list(
                    reader
                )

            # ---------------------------------------------
            # Tidak ada data
            # ---------------------------------------------

            if len(rows) <= 1:

                return

            # ---------------------------------------------
            # Masukkan data
            # ---------------------------------------------

            data_rows = rows[1:]

            self.attendance_table.setRowCount(
                0
            )

            for row in data_rows:

                if len(row) < 5:
                    continue

                row_position = (
                    self.attendance_table.rowCount()
                )

                self.attendance_table.insertRow(
                    row_position
                )

                for column, value in enumerate(
                    row[:5]
                ):

                    item = QTableWidgetItem(
                        value
                    )

                    item.setTextAlignment(
                        Qt.AlignCenter
                    )

                    self.attendance_table.setItem(
                        row_position,
                        column,
                        item
                    )

            # Tampilkan data terbaru di atas
            self.attendance_table.sortItems(
                1,
                Qt.DescendingOrder
            )

        except Exception as error:

            print(
                f"[ERROR] Gagal membaca attendance.csv: {error}"
            )

    # =====================================================
    # ADD HISTORY ROW
    # =====================================================

    def add_attendance_to_table(
        self,
        name,
        date,
        jam,
        score,
        status
    ):

        row_position = 0

        self.attendance_table.insertRow(
            row_position
        )

        values = [
            name,
            date,
            jam,
            f"{score:.2f}",
            status
        ]

        for column, value in enumerate(
            values
        ):

            item = QTableWidgetItem(
                value
            )

            item.setTextAlignment(
                Qt.AlignCenter
            )

            self.attendance_table.setItem(
                row_position,
                column,
                item
            )

    # =====================================================
    # UPDATE CAMERA
    # =====================================================

    def update_camera(self):

        ret, frame = (
            self.camera.read()
        )

        if not ret:

            return

        # =================================================
        # MIRROR
        # =================================================

        frame = cv2.flip(
            frame,
            1
        )

        # =================================================
        # RGB
        # =================================================

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb
        )

        # =================================================
        # DETEKSI
        # =================================================

        result = self.landmarker.detect(
            mp_image
        )

        # =================================================
        # TIDAK ADA WAJAH
        # =================================================

        if not result.face_landmarks:

            # ---------------------------------------------
            # Setelah berhasil:
            # tunggu wajah keluar
            # ---------------------------------------------

            if self.waiting_for_face_exit:

                self.start_new_scan()

                self.status_label.setText(
                    "Menunggu wajah..."
                )

            else:

                if self.result_state is None:

                    self.status_label.setText(
                        "Menunggu wajah..."
                    )

                    self.reset_liveness()

            self.show_frame(
                frame
            )

            return

        # =================================================
        # LANDMARK
        # =================================================

        landmarks = (
            result.face_landmarks[0]
        )

        height, width, _ = frame.shape

        xs = [
            point.x
            for point in landmarks
        ]

        ys = [
            point.y
            for point in landmarks
        ]

        min_x = max(
            0,
            int(min(xs) * width)
        )

        max_x = min(
            width,
            int(max(xs) * width)
        )

        min_y = max(
            0,
            int(min(ys) * height)
        )

        max_y = min(
            height,
            int(max(ys) * height)
        )

        face_width = (
            max_x - min_x
        )

        face_height = (
            max_y - min_y
        )

        # =================================================
        # SUCCESS RESULT
        # =================================================

        if self.result_state == "success":

            if (
                self.success_cooldown_start
                is None
            ):

                self.success_cooldown_start = (
                    time.time()
                )

            elapsed = (
                time.time()
                -
                self.success_cooldown_start
            )

            remaining = max(
                0,
                RESULT_COOLDOWN - elapsed
            )

            waktu = (
                self.attendance_time.strftime(
                    "%H:%M:%S"
                )
            )

            # ---------------------------------------------
            # BOX
            # ---------------------------------------------

            cv2.rectangle(
                frame,
                (min_x, min_y),
                (max_x, max_y),
                (0, 255, 0),
                2
            )

            # ---------------------------------------------
            # TEXT
            # ---------------------------------------------

            cv2.putText(
                frame,
                "ABSENSI BERHASIL",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                NAME,
                (20, 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                f"Waktu: {waktu}",
                (20, 110),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

            cv2.putText(
                frame,
                f"Jeda: {remaining:.1f}s",
                (20, 145),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

            # ---------------------------------------------
            # INFO UI
            # ---------------------------------------------

            self.status_label.setText(
                "ABSENSI BERHASIL ✓  |  "
                f"{NAME}  |  "
                f"{remaining:.1f}s"
            )

            self.name_info.setText(
                f"Nama: {NAME}"
            )

            self.score_info.setText(
                f"Score: {self.recognition_score:.2f}"
            )

            self.time_info.setText(
                f"Waktu: {waktu}"
            )

            # ---------------------------------------------
            # SELESAI COOLDOWN
            # ---------------------------------------------

            if elapsed >= RESULT_COOLDOWN:

                self.waiting_for_face_exit = True

                self.status_label.setText(
                    "ABSENSI BERHASIL ✓  |  "
                    "Silakan keluar dari kamera"
                )

            self.show_frame(
                frame
            )

            return

        # =================================================
        # SUDAH ABSEN HARI INI
        # =================================================

        if self.result_state == "duplicate":

            if self.duplicate_cooldown_start is None:

                self.duplicate_cooldown_start = time.time()

            elapsed = (
                time.time()
                -
                self.duplicate_cooldown_start
            )

            remaining = max(
                0,
                RESULT_COOLDOWN - elapsed
            )

            cv2.rectangle(
                frame,
                (min_x, min_y),
                (max_x, max_y),
                (0, 165, 255),
                2
            )

            cv2.putText(
                frame,
                "SUDAH ABSEN HARI INI",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (0, 165, 255),
                2
            )

            cv2.putText(
                frame,
                NAME,
                (20, 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 165, 255),
                2
            )

            cv2.putText(
                frame,
                f"Scan lagi: {remaining:.1f}s",
                (20, 110),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

            self.status_label.setText(
                "SUDAH ABSEN HARI INI  |  "
                f"Scan lagi {remaining:.1f}s"
            )

            self.name_info.setText(
                f"Nama: {NAME}"
            )

            self.score_info.setText(
                f"Score: {self.recognition_score:.2f}"
            )

            self.time_info.setText(
                "Status: Sudah absen"
            )

            if elapsed >= RESULT_COOLDOWN:

                self.start_new_scan()

            self.show_frame(frame)

            return

        # =================================================
        # FAILURE RESULT
        # =================================================

        if self.result_state == "failure":

            if (
                self.failure_cooldown_start
                is None
            ):

                self.failure_cooldown_start = (
                    time.time()
                )

            elapsed = (
                time.time()
                -
                self.failure_cooldown_start
            )

            remaining = max(
                0,
                RESULT_COOLDOWN - elapsed
            )

            # ---------------------------------------------
            # BOX MERAH
            # ---------------------------------------------

            cv2.rectangle(
                frame,
                (min_x, min_y),
                (max_x, max_y),
                (0, 0, 255),
                2
            )

            # ---------------------------------------------
            # TEXT
            # ---------------------------------------------

            cv2.putText(
                frame,
                "ABSENSI GAGAL",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2
            )

            cv2.putText(
                frame,
                "Unknown",
                (20, 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )

            cv2.putText(
                frame,
                f"Score: {self.recognition_score:.1f}",
                (20, 110),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

            cv2.putText(
                frame,
                f"Coba lagi: {remaining:.1f}s",
                (20, 145),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

            # ---------------------------------------------
            # UI
            # ---------------------------------------------

            self.status_label.setText(
                "ABSENSI GAGAL ✗  |  "
                f"Unknown  |  "
                f"Coba lagi {remaining:.1f}s"
            )

            self.name_info.setText(
                "Nama: Unknown"
            )

            self.score_info.setText(
                f"Score: {self.recognition_score:.2f}"
            )

            self.time_info.setText(
                "Waktu: -"
            )

            # ---------------------------------------------
            # SETELAH 2 DETIK
            # LANGSUNG SCAN LAGI
            # ---------------------------------------------

            if elapsed >= RESULT_COOLDOWN:

                self.start_new_scan()

            self.show_frame(
                frame
            )

            return

        # =================================================
        # WAJAH TERLALU JAUH
        # =================================================

        if (
            face_width < MIN_FACE_WIDTH
            or
            face_height < MIN_FACE_HEIGHT
        ):

            cv2.rectangle(
                frame,
                (min_x, min_y),
                (max_x, max_y),
                (0, 165, 255),
                2
            )

            cv2.putText(
                frame,
                "Silakan mendekat",
                (
                    max(20, min_x),
                    max(40, min_y - 10)
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 165, 255),
                2
            )

            cv2.putText(
                frame,
                f"Face: {face_width} x {face_height}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

            self.status_label.setText(
                "Silakan mendekat"
            )

            self.reset_liveness()

            self.show_frame(
                frame
            )

            return

        # =================================================
        # LIVENESS BERHASIL
        # =================================================

        if self.liveness_finished:

            (
                name,
                score,
                box
            ) = self.recognize_face(
                frame,
                landmarks
            )

            self.recognized_name = name

            self.recognition_score = score

            x1, y1, x2, y2 = box

            # =============================================
            # BERHASIL
            # =============================================

            if name == NAME:

                # -----------------------------------------
                # CEGAH ABSEN GANDA PADA HARI YANG SAMA
                # -----------------------------------------

                if self.already_attended_today(NAME):

                    self.result_state = "duplicate"
                    self.duplicate_cooldown_start = time.time()
                    self.recognized_name = NAME
                    self.recognition_score = score

                    print(
                        f"[INFO] {NAME} sudah absen hari ini. Tidak disimpan lagi."
                    )

                    self.status_label.setText(
                        "SUDAH ABSEN HARI INI"
                    )

                    self.show_frame(frame)

                    return

                self.attendance_recorded = True

                self.attendance_time = (
                    datetime.now()
                )

                self.result_state = (
                    "success"
                )

                self.success_cooldown_start = (
                    time.time()
                )

                waktu = (
                    self.attendance_time.strftime(
                        "%H:%M:%S"
                    )
                )

                # -----------------------------------------
                # SIMPAN CSV
                # -----------------------------------------

                saved = self.save_attendance(
                    NAME,
                    score
                )

                # -----------------------------------------
                # UPDATE TABLE
                # -----------------------------------------

                if saved:

                    self.add_attendance_to_table(
                        NAME,
                        self.attendance_time.strftime(
                            "%Y-%m-%d"
                        ),
                        waktu,
                        score,
                        "Hadir"
                    )

                # -----------------------------------------
                # TERMINAL
                # -----------------------------------------

                print(
                    "================================"
                )

                print(
                    "ABSENSI BERHASIL"
                )

                print(
                    f"Nama  : {NAME}"
                )

                print(
                    f"Score : {score:.2f}"
                )

                print(
                    f"Waktu : {waktu}"
                )

                print(
                    "================================"
                )

                # -----------------------------------------
                # BOX
                # -----------------------------------------

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    frame,
                    NAME,
                    (
                        max(20, x1),
                        max(40, y1 - 30)
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    frame,
                    f"Score: {score:.1f}",
                    (
                        max(20, x1),
                        max(65, y1 - 5)
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 255, 0),
                    2
                )

                self.status_label.setText(
                    "ABSENSI BERHASIL ✓  |  "
                    f"{NAME}"
                )

            # =============================================
            # UNKNOWN
            # =============================================

            else:

                self.result_state = (
                    "failure"
                )

                self.failure_cooldown_start = (
                    time.time()
                )

                self.recognized_name = (
                    "Unknown"
                )

                self.recognition_score = (
                    score
                )

                # -----------------------------------------
                # BOX
                # -----------------------------------------

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (0, 0, 255),
                    2
                )

                cv2.putText(
                    frame,
                    "Unknown",
                    (
                        max(20, x1),
                        max(40, y1 - 30)
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2
                )

                cv2.putText(
                    frame,
                    f"Score: {score:.1f}",
                    (
                        max(20, x1),
                        max(65, y1 - 5)
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 0, 255),
                    2
                )

                self.status_label.setText(
                    "ABSENSI GAGAL ✗  |  "
                    "Unknown"
                )

            self.show_frame(
                frame
            )

            return

        # =================================================
        # LIVENESS
        # =================================================

        left_ear = calculate_ear(
            landmarks,
            self.left_eye
        )

        right_ear = calculate_ear(
            landmarks,
            self.right_eye
        )

        ear = (
            left_ear + right_ear
        ) / 2.0

        # =================================================
        # START LIVENESS TIMER
        # =================================================

        if self.liveness_start is None:

            self.liveness_start = (
                time.time()
            )

            self.blink_state = 0

        elapsed = (
            time.time()
            -
            self.liveness_start
        )

        remaining = max(
            0,
            LIVENESS_DURATION - elapsed
        )

        # =================================================
        # BLINK DETECTION
        # =================================================

        # Mata terbuka
        if (
            self.blink_state == 0
            and
            ear > EYE_OPEN_THRESHOLD
        ):

            self.blink_state = 1

        # Mata tertutup
        elif (
            self.blink_state == 1
            and
            ear < EYE_CLOSED_THRESHOLD
        ):

            self.blink_state = 2

        # Mata terbuka kembali
        elif (
            self.blink_state == 2
            and
            ear > EYE_OPEN_THRESHOLD
        ):

            self.blink_state = 3

            self.liveness_finished = True

            self.status_label.setText(
                "LIVENESS BERHASIL ✓"
            )

        # =================================================
        # LIVENESS TIMEOUT
        # =================================================

        if not self.liveness_finished:

            if elapsed < LIVENESS_DURATION:

                self.status_label.setText(
                    "Silakan berkedip "
                    f"({remaining:.1f}s)"
                )

            else:

                # -----------------------------------------
                # LIVENESS GAGAL
                # -----------------------------------------

                self.result_state = (
                    "failure"
                )

                self.failure_cooldown_start = (
                    time.time()
                )

                self.recognized_name = (
                    "Unknown"
                )

                self.recognition_score = (
                    0.0
                )

                self.status_label.setText(
                    "LIVENESS GAGAL ✗  |  "
                    "Coba lagi 2.0s"
                )

        # =================================================
        # DRAW LIVENESS BOX
        # =================================================

        cv2.rectangle(
            frame,
            (min_x, min_y),
            (max_x, max_y),
            (255, 255, 0),
            2
        )

        # =================================================
        # EAR
        # =================================================

        cv2.putText(
            frame,
            f"EAR: {ear:.2f}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )

        # =================================================
        # FACE SIZE
        # =================================================

        cv2.putText(
            frame,
            f"Face: {face_width} x {face_height}",
            (20, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )

        self.show_frame(
            frame
        )

    # =====================================================
    # SHOW FRAME
    # =====================================================

    def show_frame(self, frame):

        display_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        height, width, channel = (
            display_frame.shape
        )

        bytes_per_line = (
            channel * width
        )

        image = QImage(
            display_frame.data,
            width,
            height,
            bytes_per_line,
            QImage.Format_RGB888
        )

        pixmap = QPixmap.fromImage(
            image
        )

        pixmap = pixmap.scaled(
            self.camera_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.camera_label.setPixmap(
            pixmap
        )

    # =====================================================
    # CLOSE EVENT
    # =====================================================

    def closeEvent(self, event):

        if self.camera.isOpened():

            self.camera.release()

        self.landmarker.close()

        event.accept()


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":

    app = QApplication(
        sys.argv
    )

    window = ScanlyWindow()

    window.show()

    sys.exit(
        app.exec()
    )