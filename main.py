import sys
import math
import time
import csv
import json
from collections import deque
from datetime import datetime, time as dt_time
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap


# =========================================================
# SCANLY
# FACE RECOGNITION + VOTING + ATTENDANCE
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

MODEL_DIR = BASE_DIR / "face_model"

# =========================================================
# FACE EMBEDDING MODEL - OpenCV SFace
# =========================================================
#
# File model:
#   face_model/face_recognition_sface_2021dec.onnx
#
# SFace menghasilkan embedding wajah sehingga sistem tidak
# lagi dipaksa memilih salah satu label seperti LBPH.
#
SFACE_MODEL_PATH = (
    MODEL_DIR / "face_recognition_sface_2021dec.onnx"
)

EMBEDDING_CACHE_PATH = (
    MODEL_DIR / "face_embeddings.json"
)

LANDMARKER_PATH = (
    BASE_DIR / "models" / "face_landmarker.task"
)

ATTENDANCE_FILE = BASE_DIR / "attendance.csv"


# =========================================================
# FACE RECOGNITION
# =========================================================

# =========================================================
# FACE EMBEDDING THRESHOLDS
# =========================================================
#
# SFace OpenCV Zoo memakai cosine similarity:
#   semakin BESAR = semakin mirip
#
# Threshold resmi contoh OpenCV:
#   cosine >= 0.363
#
# Untuk absensi kita sengaja memakai gate lebih ketat.
# Nilai awal 0.48 dapat dituning setelah pengujian kamera.
#
SFACE_COSINE_THRESHOLD = 0.50

# Untuk 1 user aktif, margin tidak tersedia. Karena itu gunakan
# verifikasi multi-reference: beberapa foto user harus sama-sama dekat.
SFACE_SINGLE_USER_THRESHOLD = 0.54
SFACE_TOP_K = 3

# Untuk banyak user, kandidat terbaik harus melewati absolute threshold
# dan margin terhadap kandidat kedua.
SFACE_MULTI_USER_THRESHOLD = 0.50

# Selisih similarity kandidat terbaik terhadap kandidat kedua.
# Semakin besar semakin aman.
SFACE_MARGIN = 0.040

# Setidaknya beberapa foto harus berhasil menghasilkan embedding.
MIN_EMBEDDINGS_PER_USER = 3

MIN_FACE_WIDTH = 120
MIN_FACE_HEIGHT = 120

FACE_SIZE = (200, 200)


# =========================================================
# LIVENESS
# =========================================================

LIVENESS_DURATION = 2.5

EYE_OPEN_THRESHOLD = 0.24
EYE_CLOSED_THRESHOLD = 0.20


# =========================================================
# VOTING
# =========================================================

VOTE_FRAMES = 5
VOTE_REQUIRED = 5

RESULT_COOLDOWN = 2.0


# =========================================================
# JAM ABSENSI
# =========================================================

# MASUK
#
# < 08:00
#   Belum dibuka
#
# 08:00 - 08:30
#   Tepat Waktu
#
# 08:31 - 15:59
#   Terlambat
#
# PULANG
#
# < 16:00
#   Belum bisa pulang
#
# 16:00 - 18:00
#   Bisa pulang
#
# > 18:00
#   Ditutup

ATTENDANCE_START = dt_time(8, 0)

ON_TIME_END = dt_time(8, 30)

RETURN_START = dt_time(16, 0)

RETURN_END = dt_time(18, 0)


# =========================================================
# PREPROCESSING
# =========================================================

def preprocess_face(
    face_bgr,
    face_size=FACE_SIZE,
):
    if face_bgr is None:
        return None

    if face_bgr.size == 0:
        return None

    gray = cv2.cvtColor(
        face_bgr,
        cv2.COLOR_BGR2GRAY,
    )

    gray = cv2.resize(
        gray,
        face_size,
        interpolation=cv2.INTER_AREA,
    )

    clahe = cv2.createCLAHE(
        clipLimit=1.5,
        tileGridSize=(8, 8),
    )

    gray = clahe.apply(gray)

    gray = cv2.GaussianBlur(
        gray,
        (3, 3),
        0,
    )

    return gray


# =========================================================
# EAR / BLINK
# =========================================================

def calculate_ear(
    landmarks,
    indices,
):
    points = []

    for index in indices:
        point = landmarks[index]

        points.append(
            (point.x, point.y)
        )

    vertical_1 = math.dist(
        points[1],
        points[5],
    )

    vertical_2 = math.dist(
        points[2],
        points[4],
    )

    horizontal = math.dist(
        points[0],
        points[3],
    )

    if horizontal == 0:
        return 0.0

    return (
        vertical_1 + vertical_2
    ) / (2.0 * horizontal)


# =========================================================
# JAM ABSEN
# =========================================================

def get_attendance_mode():
    """
    Mengembalikan:

    CLOSED
    IN_ON_TIME
    IN_LATE
    OUT
    """

    now = datetime.now().time()

    # Sebelum jam 08:00
    if now < ATTENDANCE_START:
        return "CLOSED"

    # 08:00 sampai 08:30
    if now <= ON_TIME_END:
        return "IN_ON_TIME"

    # Setelah 08:30 sampai sebelum 16:00
    if now < RETURN_START:
        return "IN_LATE"

    # 16:00 sampai 18:00
    if now <= RETURN_END:
        return "OUT"

    # Setelah 18:00
    return "CLOSED"


def get_schedule_message():
    mode = get_attendance_mode()

    if mode == "IN_ON_TIME":
        return (
            "Absen masuk dibuka - "
            "Tepat Waktu"
        )

    if mode == "IN_LATE":
        return (
            "Absen masuk dibuka - "
            "Terlambat"
        )

    if mode == "OUT":
        return (
            "Absen pulang dibuka "
            "16:00 - 18:00"
        )

    now = datetime.now().time()

    if now < ATTENDANCE_START:
        return (
            "Absen masuk belum dibuka "
            "(mulai 08:00)"
        )

    return (
        "Absen pulang sudah ditutup "
        "(maksimal 18:00)"
    )


# =========================================================
# MAIN WINDOW
# =========================================================

class ScanlyWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle(
            "Scanly - Face Recognition"
        )

        self.setMinimumSize(
            1100,
            850,
        )

        # =================================================
        # LIVENESS
        # =================================================

        self.left_eye = [
            33,
            160,
            158,
            133,
            153,
            144,
        ]

        self.right_eye = [
            362,
            385,
            387,
            263,
            373,
            380,
        ]

        self.blink_state = 0

        self.liveness_start = None

        self.liveness_finished = False

        # =================================================
        # VOTING
        # =================================================

        self.vote_results = deque(
            maxlen=VOTE_FRAMES
        )

        self.vote_scores = deque(
            maxlen=VOTE_FRAMES
        )

        self.vote_boxes = deque(
            maxlen=VOTE_FRAMES
        )

        # =================================================
        # RESULT
        # =================================================

        self.result_state = None

        self.recognized_name = "Unknown"

        self.recognition_score = 0.0

        self.attendance_status = None

        self.attendance_time = None

        self.result_start_time = None

        self.waiting_for_face_exit = False

        # =================================================
        # UI
        # =================================================

        self.create_ui()

        # =================================================
        # MODEL
        # =================================================

        self.active_people = {}

        self._model_file_state = None

        self.create_landmarker()

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

        self.timer = QTimer()

        self.timer.timeout.connect(
            self.update_camera
        )

        self.timer.start(30)

    # =====================================================
    # UI
    # =====================================================

    def create_ui(self):

        central = QWidget()

        self.setCentralWidget(
            central
        )

        layout = QVBoxLayout()

        central.setLayout(
            layout
        )

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

        layout.addWidget(
            title
        )

        subtitle = QLabel(
            "Face Recognition & Attendance"
        )

        subtitle.setAlignment(
            Qt.AlignCenter
        )

        subtitle.setStyleSheet(
            """
            font-size: 15px;
            """
        )

        layout.addWidget(
            subtitle
        )

        # =================================================
        # JADWAL
        # =================================================

        self.schedule_label = QLabel()

        self.schedule_label.setAlignment(
            Qt.AlignCenter
        )

        self.schedule_label.setStyleSheet(
            """
            font-size: 14px;
            font-weight: bold;
            padding: 8px;
            """
        )

        layout.addWidget(
            self.schedule_label
        )

        # =================================================
        # CAMERA
        # =================================================

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

        layout.addWidget(
            self.camera_label
        )

        # =================================================
        # STATUS
        # =================================================

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

        layout.addWidget(
            self.status_label
        )

        # =================================================
        # INFO
        # =================================================

        info = QHBoxLayout()

        self.name_info = QLabel(
            "Nama: -"
        )

        self.score_info = QLabel(
            "Similarity: -"
        )

        self.time_info = QLabel(
            "Waktu: -"
        )

        info.addWidget(
            self.name_info
        )

        info.addWidget(
            self.score_info
        )

        info.addWidget(
            self.time_info
        )

        layout.addLayout(
            info
        )

        # =================================================
        # TABLE
        # =================================================

        history = QLabel(
            "Riwayat Absensi"
        )

        history.setStyleSheet(
            """
            font-size: 18px;
            font-weight: bold;
            """
        )

        layout.addWidget(
            history
        )

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
                "Status",
            ]
        )

        self.attendance_table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )

        self.attendance_table.setSelectionBehavior(
            QTableWidget.SelectRows
        )

        header = (
            self.attendance_table
            .horizontalHeader()
        )

        header.setSectionResizeMode(
            QHeaderView.Stretch
        )

        self.attendance_table.setMaximumHeight(
            240
        )

        layout.addWidget(
            self.attendance_table
        )

        self.load_attendance_history()

    # =====================================================
    # MEDIAPIPE
    # =====================================================

    def create_landmarker(self):

        if not LANDMARKER_PATH.exists():

            raise FileNotFoundError(
                "File MediaPipe tidak ditemukan:\n"
                + str(LANDMARKER_PATH)
            )

        BaseOptions = (
            mp.tasks.BaseOptions
        )

        FaceLandmarker = (
            mp.tasks.vision.FaceLandmarker
        )

        FaceLandmarkerOptions = (
            mp.tasks
            .vision
            .FaceLandmarkerOptions
        )

        options = (
            FaceLandmarkerOptions(
                base_options=BaseOptions(
                    model_asset_path=str(
                        LANDMARKER_PATH
                    )
                ),
                num_faces=1,
            )
        )

        self.landmarker = (
            FaceLandmarker
            .create_from_options(
                options
            )
        )


    # =====================================================
    # USER AKTIF + SFACE GALLERY
    # =====================================================

    def load_active_people(self):

        people_file = (
            BASE_DIR / "people.csv"
        )

        active = {}

        if not people_file.exists():
            return active

        try:

            with open(
                people_file,
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as file:

                reader = csv.DictReader(file)

                for row in reader:

                    person_id = str(
                        row.get("ID", "")
                    ).strip()

                    name = str(
                        row.get("Nama", "")
                    ).strip()

                    status = str(
                        row.get("Status", "Aktif")
                    ).strip().lower()

                    if not person_id:
                        continue

                    if status not in (
                        "",
                        "aktif",
                        "active",
                    ):
                        continue

                    if not name:
                        continue

                    active[person_id] = name

        except Exception as error:

            print(
                "[ERROR] load_active_people:",
                error,
            )

            return {}

        return active

    def _get_model_state(self):
        """
        State recognition sekarang bergantung pada:
        - model SFace
        - people.csv
        - seluruh foto user aktif

        Jadi ketika admin register/hapus/edit user, cache embedding
        akan dibangun ulang otomatis.
        """
        people_file = BASE_DIR / "people.csv"

        latest_photo_ns = 0

        try:
            folders = self._get_person_folders()

            for folder in folders.values():
                if not folder.exists():
                    continue

                for path in folder.rglob("*"):
                    if (
                        path.is_file()
                        and path.suffix.lower()
                        in {
                            ".jpg",
                            ".jpeg",
                            ".jpe",
                            ".png",
                            ".bmp",
                            ".webp",
                        }
                    ):
                        try:
                            latest_photo_ns = max(
                                latest_photo_ns,
                                path.stat().st_mtime_ns,
                            )
                        except OSError:
                            pass

            return (
                SFACE_MODEL_PATH.stat().st_mtime_ns
                if SFACE_MODEL_PATH.exists()
                else 0,
                people_file.stat().st_mtime_ns
                if people_file.exists()
                else 0,
                latest_photo_ns,
            )

        except OSError:
            return None

    def _get_person_folders(self):
        """Ambil folder wajah hanya untuk user aktif dari people.csv."""
        people_file = BASE_DIR / "people.csv"
        folders = {}

        if not people_file.exists():
            return folders

        try:
            with open(
                people_file,
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as file:

                reader = csv.DictReader(file)

                for row in reader:
                    person_id = str(
                        row.get("ID", "")
                    ).strip()

                    status = str(
                        row.get("Status", "Aktif")
                    ).strip().lower()

                    folder = str(
                        row.get("Folder", "")
                    ).strip()

                    if not person_id:
                        continue

                    if status not in (
                        "",
                        "aktif",
                        "active",
                    ):
                        continue

                    if not folder:
                        continue

                    folder = folder.replace(
                        "\\",
                        "/",
                    )

                    folders[person_id] = (
                        BASE_DIR / folder
                    )

        except Exception as error:
            print(
                "[EMBED] Gagal membaca folder user:",
                error,
            )

        return folders

    def _create_sface(self):
        """Buat FaceRecognizerSF secara kompatibel dengan OpenCV."""
        if not SFACE_MODEL_PATH.exists():
            raise FileNotFoundError(
                "Model SFace tidak ditemukan:\n"
                + str(SFACE_MODEL_PATH)
            )

        creator = getattr(
            cv2,
            "FaceRecognizerSF_create",
            None,
        )

        if creator is not None:
            return creator(
                str(SFACE_MODEL_PATH),
                "",
            )

        face_recognizer_sf = getattr(
            cv2,
            "FaceRecognizerSF",
            None,
        )

        if face_recognizer_sf is not None:
            create_method = getattr(
                face_recognizer_sf,
                "create",
                None,
            )

            if create_method is not None:
                return create_method(
                    str(SFACE_MODEL_PATH),
                    "",
                )

        raise RuntimeError(
            "OpenCV tidak menyediakan FaceRecognizerSF. "
            "Pastikan opencv-contrib-python terpasang."
        )

    @staticmethod
    def _point_xy(point):
        return (
            float(point.x),
            float(point.y),
        )

    def _build_face_info(
        self,
        frame,
        landmarks,
    ):
        """
        Ubah 478 landmark MediaPipe menjadi format 5-point
        yang dibutuhkan SFace:

        x, y, w, h,
        right_eye,
        left_eye,
        nose,
        right_mouth,
        left_mouth
        """
        height, width = frame.shape[:2]

        xs = [
            float(point.x)
            for point in landmarks
        ]

        ys = [
            float(point.y)
            for point in landmarks
        ]

        min_x = max(
            0,
            int(min(xs) * width),
        )

        max_x = min(
            width - 1,
            int(max(xs) * width),
        )

        min_y = max(
            0,
            int(min(ys) * height),
        )

        max_y = min(
            height - 1,
            int(max(ys) * height),
        )

        box_w = max(
            1,
            max_x - min_x,
        )

        box_h = max(
            1,
            max_y - min_y,
        )

        def avg_point(indices):
            pts = [
                landmarks[index]
                for index in indices
            ]

            return (
                sum(
                    float(point.x) * width
                    for point in pts
                ) / len(pts),
                sum(
                    float(point.y) * height
                    for point in pts
                ) / len(pts),
            )

        # SFace/OpenCV expects:
        # right eye, left eye, nose, right mouth, left mouth.
        right_eye = avg_point(
            [263, 362]
        )

        left_eye = avg_point(
            [33, 133]
        )

        nose = avg_point(
            [1, 4]
        )

        right_mouth = avg_point(
            [291]
        )

        left_mouth = avg_point(
            [61]
        )

        return np.asarray(
            [[
                float(min_x),
                float(min_y),
                float(box_w),
                float(box_h),

                right_eye[0],
                right_eye[1],

                left_eye[0],
                left_eye[1],

                nose[0],
                nose[1],

                right_mouth[0],
                right_mouth[1],

                left_mouth[0],
                left_mouth[1],
            ]],
            dtype=np.float32,
        )

    def _embedding_from_image(
        self,
        image,
    ):
        """
        Buat embedding dari satu foto training menggunakan
        MediaPipe landmark + SFace.

        Tidak menggunakan LBPH.
        """
        if image is None or image.size == 0:
            return None

        try:
            rgb = cv2.cvtColor(
                image,
                cv2.COLOR_BGR2RGB,
            )

            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb,
            )

            result = self.landmarker.detect(
                mp_image
            )

            if not result.face_landmarks:
                return None

            landmarks = result.face_landmarks[0]

            face_info = self._build_face_info(
                image,
                landmarks,
            )

            aligned = self.sface.alignCrop(
                image,
                face_info,
            )

            feature = self.sface.feature(
                aligned
            )

            if feature is None:
                return None

            feature = np.asarray(
                feature,
                dtype=np.float32,
            ).reshape(-1)

            norm = np.linalg.norm(
                feature
            )

            if norm <= 1e-12:
                return None

            feature = feature / norm

            return feature.astype(
                np.float32
            )

        except Exception as error:
            print(
                "[EMBED] Gagal membuat embedding:",
                error,
            )
            return None

    def _load_embedding_cache(self):
        if not EMBEDDING_CACHE_PATH.exists():
            return {}

        try:
            with open(
                EMBEDDING_CACHE_PATH,
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            if not isinstance(data, dict):
                return {}

            return data

        except Exception as error:
            print(
                "[EMBED] Cache rusak, dibuat ulang:",
                error,
            )
            return {}

    def _save_embedding_cache(self):
        EMBEDDING_CACHE_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = {}

        for person_id, embeddings in (
            self.embeddings.items()
        ):
            payload[str(person_id)] = [
                [
                    float(value)
                    for value in embedding
                ]
                for embedding in embeddings
            ]

        temp_path = (
            EMBEDDING_CACHE_PATH.with_suffix(
                ".tmp"
            )
        )

        with open(
            temp_path,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                payload,
                file,
                ensure_ascii=False,
            )

        temp_path.replace(
            EMBEDDING_CACHE_PATH
        )

    def _build_embeddings(self):
        """
        Bangun gallery embedding dari foto user AKTIF.

        Setiap foto menghasilkan satu embedding.
        Cache hanya berisi user yang aktif saat ini.
        """
        self.embeddings = {}

        folders = self._get_person_folders()

        for person_id, folder in folders.items():

            if person_id not in self.active_people:
                continue

            if not folder.exists():
                continue

            vectors = []

            image_files = sorted(
                [
                    path
                    for path in folder.rglob("*")
                    if (
                        path.is_file()
                        and path.suffix.lower()
                        in {
                            ".jpg",
                            ".jpeg",
                            ".jpe",
                            ".png",
                            ".bmp",
                            ".webp",
                        }
                    )
                ]
            )

            for image_path in image_files:
                image = cv2.imread(
                    str(image_path)
                )

                if image is None:
                    print(
                        "[EMBED] Skip gambar:",
                        image_path,
                    )
                    continue

                feature = (
                    self._embedding_from_image(
                        image
                    )
                )

                if feature is not None:
                    vectors.append(feature)

                    # Tambahkan satu versi flip untuk
                    # meningkatkan toleransi terhadap
                    # kamera yang ditampilkan mirrored.
                    flipped = cv2.flip(
                        image,
                        1,
                    )

                    flipped_feature = (
                        self._embedding_from_image(
                            flipped
                        )
                    )

                    if (
                        flipped_feature
                        is not None
                    ):
                        vectors.append(
                            flipped_feature
                        )

            if len(vectors) >= MIN_EMBEDDINGS_PER_USER:
                self.embeddings[
                    person_id
                ] = vectors

                print(
                    "[EMBED] User siap:",
                    person_id,
                    "=",
                    self.active_people.get(
                        person_id,
                        "",
                    ),
                    "embeddings=",
                    len(vectors),
                )

            else:
                print(
                    "[EMBED] User tidak punya "
                    "embedding valid:",
                    person_id,
                )

        self._save_embedding_cache()

    def create_recognizer(self):
        """
        Inisialisasi SFace dan gallery embedding.

        Tidak membaca:
            scanly_faces.yml
            label_map.json

        Karena identitas ditentukan dari embedding foto
        user aktif di people.csv.
        """
        self.active_people = (
            self.load_active_people()
        )

        people_file = (
            BASE_DIR / "people.csv"
        )

        self.sface = self._create_sface()

        if (
            not people_file.exists()
            and not self.active_people
        ):
            print(
                "[ACTIVE USERS] Tidak ada people.csv "
                "dan tidak ada user aktif."
            )

        self._build_embeddings()

        self._model_file_state = (
            self._get_model_state()
        )

        print(
            "[ACTIVE USERS]",
            ", ".join(
                f"{pid}={name}"
                for pid, name
                in self.active_people.items()
            )
            or "(tidak ada)",
        )

        print(
            "[EMBEDDING] Gallery user aktif:",
            len(
                getattr(
                    self,
                    "embeddings",
                    {},
                )
            ),
        )

        missing = sorted(
            set(self.active_people.keys())
            - set(self.embeddings.keys())
        )

        if missing:
            print(
                "[EMBEDDING] WARNING user aktif tanpa embedding:",
                ", ".join(missing),
            )

    def reload_model_if_changed(self):
        current_state = (
            self._get_model_state()
        )

        if current_state is None:
            return

        old_state = getattr(
            self,
            "_model_file_state",
            None,
        )

        if old_state == current_state:
            return

        try:
            print(
                "[MODEL] Perubahan user/foto/model "
                "terdeteksi. Rebuild embedding..."
            )

            self.create_recognizer()

            print(
                "[MODEL] Reload embedding berhasil."
            )

        except Exception as error:
            print(
                "[MODEL] Reload ditunda:",
                error,
            )

    # =====================================================
    # RESET
    # =====================================================

    def reset_scan(self):

        self.blink_state = 0

        self.liveness_start = None

        self.liveness_finished = False

        self.vote_results.clear()

        self.vote_scores.clear()

        self.vote_boxes.clear()

        self.result_state = None

        self.recognized_name = "Unknown"

        self.recognition_score = 0.0

        self.attendance_status = None

        self.attendance_time = None

        self.result_start_time = None

        self.waiting_for_face_exit = False

        self.status_label.setText(
            "Menunggu wajah..."
        )

        self.name_info.setText(
            "Nama: -"
        )

        self.score_info.setText(
            "Similarity: -"
        )

        self.time_info.setText(
            "Waktu: -"
        )

    # =====================================================
    # RECOGNIZE FACE
    # =====================================================

    def recognize_face(
        self,
        frame,
        landmarks,
    ):
        """
        SFace recognition yang benar-benar independent dari LBPH.

        Prinsip keamanan:
        1. Gallery hanya berisi user AKTIF dari people.csv.
        2. Jika gallery kosong -> Unknown.
        3. Setiap user punya beberapa reference embedding.
        4. Skor user bukan MAX satu foto saja. Dipakai top-k median
           agar satu foto yang kebetulan mirip tidak langsung meloloskan.
        5. User tunggal memakai absolute threshold yang lebih ketat.
        6. Banyak user memakai absolute threshold + margin.
        7. Hasil tidak pernah dipaksa menjadi nama terdekat.
        """

        height, width = frame.shape[:2]

        xs = [float(point.x) for point in landmarks]
        ys = [float(point.y) for point in landmarks]

        min_x = max(0, int(min(xs) * width))
        max_x = min(width, int(max(xs) * width))
        min_y = max(0, int(min(ys) * height))
        max_y = min(height, int(max(ys) * height))

        face_width = max_x - min_x
        face_height = max_y - min_y

        box = (min_x, min_y, max_x, max_y)

        if (
            face_width < MIN_FACE_WIDTH
            or face_height < MIN_FACE_HEIGHT
        ):
            return ("TOO_FAR", 0.0, box)

        # Hard gate: tidak ada user aktif = tidak boleh mengenali siapa pun.
        embeddings = getattr(self, "embeddings", {})
        active_ids = set(self.active_people.keys())

        if not embeddings or not active_ids:
            print("[RECOGNITION] Gallery kosong -> Unknown")
            return ("Unknown", 0.0, box)

        try:
            face_info = self._build_face_info(frame, landmarks)

            aligned = self.sface.alignCrop(
                frame,
                face_info,
            )

            query_feature = self.sface.feature(
                aligned
            )

            if query_feature is None:
                return ("Unknown", 0.0, box)

            query_feature = np.asarray(
                query_feature,
                dtype=np.float32,
            ).reshape(-1)

            norm = float(np.linalg.norm(query_feature))

            if norm <= 1e-12:
                return ("Unknown", 0.0, box)

            query_feature = (
                query_feature / norm
            ).astype(np.float32)

        except Exception as error:
            print("[ERROR] SFace feature:", error)
            return ("Unknown", 0.0, box)

        # -------------------------------------------------
        # SCORE PER USER
        # -------------------------------------------------
        #
        # Jangan gunakan hanya satu reference terbaik.
        # Ambil top-K similarity setiap user lalu median.
        # Ini membuat keputusan lebih stabil dan mengurangi
        # kemungkinan orang asing cocok dengan satu foto saja.
        #
        ranked = []

        for person_id in sorted(active_ids):
            gallery = embeddings.get(person_id, [])

            if not gallery:
                continue

            scores = []

            for reference in gallery:
                try:
                    ref = np.asarray(
                        reference,
                        dtype=np.float32,
                    ).reshape(-1)

                    ref_norm = float(
                        np.linalg.norm(ref)
                    )

                    if ref_norm <= 1e-12:
                        continue

                    ref = ref / ref_norm

                    similarity = float(
                        np.dot(
                            query_feature,
                            ref,
                        )
                    )

                    # Clamp untuk menghindari noise numerik.
                    similarity = max(
                        -1.0,
                        min(1.0, similarity),
                    )

                    scores.append(similarity)

                except Exception:
                    continue

            if not scores:
                continue

            scores.sort(reverse=True)

            k = min(
                SFACE_TOP_K,
                len(scores),
            )

            top_scores = scores[:k]

            # Median top-K.
            user_score = float(
                np.median(
                    np.asarray(
                        top_scores,
                        dtype=np.float32,
                    )
                )
            )

            ranked.append(
                {
                    "id": person_id,
                    "score": user_score,
                    "best": float(scores[0]),
                    "top_scores": top_scores,
                }
            )

        if not ranked:
            return ("Unknown", 0.0, box)

        ranked.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        best = ranked[0]

        best_id = best["id"]
        best_score = best["score"]
        best_single = best["best"]

        second_score = (
            ranked[1]["score"]
            if len(ranked) > 1
            else None
        )

        margin = (
            best_score - second_score
            if second_score is not None
            else None
        )

        best_name = str(
            self.active_people.get(
                best_id,
                "",
            )
        ).strip()

        print(
            "[VERIFY]",
            f"Best={best_id}",
            f"Name={best_name}",
            f"UserScore={best_score:.4f}",
            f"BestRef={best_single:.4f}",
            (
                f"Second={second_score:.4f}"
                if second_score is not None
                else "Second=NONE"
            ),
            (
                f"Margin={margin:.4f}"
                if margin is not None
                else "Margin=NONE"
            ),
        )

        # -------------------------------------------------
        # ABSOLUTE REJECTION
        # -------------------------------------------------
        #
        # SATU USER:
        # Tidak ada kandidat kedua, jadi margin tidak bisa dipakai.
        # Gunakan threshold lebih ketat + multi-reference.
        #
        if len(ranked) == 1:
            if best_score < SFACE_SINGLE_USER_THRESHOLD:
                print(
                    "[VERIFY] REJECT single-user:",
                    f"score={best_score:.4f}",
                    f"< {SFACE_SINGLE_USER_THRESHOLD:.4f}",
                )
                return (
                    "Unknown",
                    best_score,
                    box,
                )

        # BANYAK USER:
        # Kandidat harus lolos absolute threshold.
        else:
            if best_score < SFACE_MULTI_USER_THRESHOLD:
                print(
                    "[VERIFY] REJECT:",
                    f"score={best_score:.4f}",
                    f"< {SFACE_MULTI_USER_THRESHOLD:.4f}",
                )
                return (
                    "Unknown",
                    best_score,
                    box,
                )

            # Kandidat kedua wajib cukup jauh.
            if margin is None or margin < SFACE_MARGIN:
                print(
                    "[VERIFY] REJECT:",
                    "candidate terlalu dekat",
                    (
                        f"margin={margin:.4f}"
                        if margin is not None
                        else "margin=NONE"
                    ),
                    f"< {SFACE_MARGIN:.4f}",
                )
                return (
                    "Unknown",
                    best_score,
                    box,
                )

        # -------------------------------------------------
        # FINAL ACTIVE USER GATE
        # -------------------------------------------------
        if best_id not in self.active_people:
            print(
                "[VERIFY] REJECT: ID tidak lagi aktif:",
                best_id,
            )
            return (
                "Unknown",
                best_score,
                box,
            )

        if not best_name:
            return (
                "Unknown",
                best_score,
                box,
            )

        print(
            "[RECOGNITION]",
            f"ID={best_id}",
            f"Name={best_name}",
            f"Similarity={best_score:.4f}",
            (
                f"Margin={margin:.4f}"
                if margin is not None
                else "Margin=NONE"
            ),
        )

        return (
            best_name,
            float(best_score),
            box,
        )

    # =====================================================
    # VOTING
    # =====================================================

    def add_vote(
        self,
        name,
        score,
        box,
    ):

        self.vote_results.append(
            name
        )

        self.vote_scores.append(
            float(score)
        )

        self.vote_boxes.append(
            box
        )

        if (
            len(self.vote_results)
            < VOTE_FRAMES
        ):
            return None

        counts = {}

        for item in self.vote_results:

            counts[item] = (
                counts.get(
                    item,
                    0,
                )
                + 1
            )

        known = {
            name: count
            for name, count
            in counts.items()
            if name != "Unknown"
        }

        if not known:

            return (
                "Unknown",
                float(
                    np.median(
                        list(
                            self.vote_scores
                        )
                    )
                ),
                self.vote_boxes[-1],
                0,
                counts.get(
                    "Unknown",
                    0,
                ),
            )

        final_name, final_votes = max(
            known.items(),
            key=lambda item: item[1],
        )

        if (
            final_votes
            < VOTE_REQUIRED
        ):

            return (
                "Unknown",
                float(
                    np.median(
                        list(
                            self.vote_scores
                        )
                    )
                ),
                self.vote_boxes[-1],
                final_votes,
                counts.get(
                    "Unknown",
                    0,
                ),
            )

        winning_scores = []

        for item, score in zip(
            self.vote_results,
            self.vote_scores,
        ):

            if item == final_name:

                winning_scores.append(
                    score
                )

        final_score = float(
            np.median(
                winning_scores
            )
        )

        return (
            final_name,
            final_score,
            self.vote_boxes[-1],
            final_votes,
            counts.get(
                "Unknown",
                0,
            ),
        )

    # =====================================================
    # CSV
    # =====================================================

    def read_attendance(self):

        if not ATTENDANCE_FILE.exists():
            return []

        try:

            with open(
                ATTENDANCE_FILE,
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as file:

                return list(
                    csv.DictReader(
                        file
                    )
                )

        except Exception as error:

            print(
                "[ERROR] attendance.csv:",
                error,
            )

            return []

    def save_attendance(
        self,
        name,
        score,
        status,
    ):

        exists = (
            ATTENDANCE_FILE.exists()
        )

        now = datetime.now()

        try:

            with open(
                ATTENDANCE_FILE,
                "a",
                newline="",
                encoding="utf-8-sig",
            ) as file:

                writer = csv.writer(
                    file
                )

                if not exists:

                    writer.writerow(
                        [
                            "Nama",
                            "Tanggal",
                            "Jam",
                            "Score",
                            "Status",
                        ]
                    )

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
                        status,
                    ]
                )

            return True

        except Exception as error:

            print(
                "[ERROR] save attendance:",
                error,
            )

            return False

    # =====================================================
    # CHECK TODAY
    # =====================================================

    def has_entry_today(
        self,
        name,
    ):

        today = datetime.now().strftime(
            "%Y-%m-%d"
        )

        for row in self.read_attendance():

            if (
                row.get(
                    "Nama",
                    ""
                ).strip()
                == name
                and
                row.get(
                    "Tanggal",
                    ""
                ).strip()
                == today
                and
                row.get(
                    "Status",
                    ""
                ).strip()
                in (
                    "Tepat Waktu",
                    "Terlambat",
                )
            ):

                return True

        return False

    def has_exit_today(
        self,
        name,
    ):

        today = datetime.now().strftime(
            "%Y-%m-%d"
        )

        for row in self.read_attendance():

            if (
                row.get(
                    "Nama",
                    ""
                ).strip()
                == name
                and
                row.get(
                    "Tanggal",
                    ""
                ).strip()
                == today
                and
                row.get(
                    "Status",
                    ""
                ).strip()
                == "Pulang"
            ):

                return True

        return False

    # =====================================================
    # ATTENDANCE DECISION
    # =====================================================

    def attendance_decision(
        self,
        name,
    ):

        mode = get_attendance_mode()

        # -----------------------------------------------
        # SEBELUM 08:00
        # -----------------------------------------------

        if mode == "CLOSED":

            now = datetime.now().time()

            if now < ATTENDANCE_START:

                return (
                    False,
                    "TIME",
                    "Absen masuk belum dibuka. "
                    "Mulai pukul 08:00.",
                    None,
                )

            return (
                False,
                "TIME",
                "Absen pulang sudah ditutup. "
                "Batas sampai pukul 18:00.",
                None,
            )

        # -----------------------------------------------
        # MASUK TEPAT WAKTU
        # -----------------------------------------------

        if mode == "IN_ON_TIME":

            if self.has_entry_today(
                name
            ):

                return (
                    False,
                    "DUPLICATE",
                    "Anda sudah absen masuk "
                    "hari ini.",
                    None,
                )

            return (
                True,
                "OK",
                "Absen masuk - Tepat Waktu.",
                "Tepat Waktu",
            )

        # -----------------------------------------------
        # MASUK TERLAMBAT
        # -----------------------------------------------

        if mode == "IN_LATE":

            if self.has_entry_today(
                name
            ):

                return (
                    False,
                    "DUPLICATE",
                    "Anda sudah absen masuk "
                    "hari ini.",
                    None,
                )

            return (
                True,
                "OK",
                "Absen masuk - Terlambat.",
                "Terlambat",
            )

        # -----------------------------------------------
        # PULANG
        # -----------------------------------------------

        if mode == "OUT":

            if not self.has_entry_today(
                name
            ):

                return (
                    False,
                    "NO_ENTRY",
                    "Belum ada absen masuk "
                    "hari ini.",
                    None,
                )

            if self.has_exit_today(
                name
            ):

                return (
                    False,
                    "DUPLICATE",
                    "Anda sudah absen pulang "
                    "hari ini.",
                    None,
                )

            return (
                True,
                "OK",
                "Absen pulang diterima.",
                "Pulang",
            )

        return (
            False,
            "TIME",
            "Absensi tidak tersedia.",
            None,
        )

    # =====================================================
    # HISTORY TABLE
    # =====================================================

    def load_attendance_history(
        self
    ):

        self.attendance_table.setRowCount(
            0
        )

        rows = self.read_attendance()

        for row in reversed(rows):

            self.add_table_row(
                row.get(
                    "Nama",
                    ""
                ),
                row.get(
                    "Tanggal",
                    ""
                ),
                row.get(
                    "Jam",
                    ""
                ),
                row.get(
                    "Score",
                    ""
                ),
                row.get(
                    "Status",
                    ""
                ),
            )

    def add_table_row(
        self,
        name,
        date,
        jam,
        score,
        status,
    ):

        row = (
            self.attendance_table.rowCount()
        )

        self.attendance_table.insertRow(
            row
        )

        values = [
            name,
            date,
            jam,
            str(score),
            status,
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
                row,
                column,
                item,
            )

    # =====================================================
    # CAMERA
    # =====================================================

    def update_camera(self):

        # Reload otomatis setelah register/delete/training.
        self.reload_model_if_changed()

        self.schedule_label.setText(
            get_schedule_message()
        )

        ret, frame = (
            self.camera.read()
        )

        if not ret:
            return

        frame = cv2.flip(
            frame,
            1,
        )

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB,
        )

        mp_image = mp.Image(
            image_format=(
                mp.ImageFormat.SRGB
            ),
            data=rgb,
        )

        try:

            result = (
                self.landmarker.detect(
                    mp_image
                )
            )

        except Exception as error:

            self.status_label.setText(
                f"MediaPipe error: {error}"
            )

            self.show_frame(
                frame
            )

            return

        # =================================================
        # TIDAK ADA WAJAH
        # =================================================

        if not result.face_landmarks:

            if self.waiting_for_face_exit:

                self.reset_scan()

            elif (
                self.result_state
                is None
            ):

                self.status_label.setText(
                    "Menunggu wajah..."
                )

                self.blink_state = 0
                self.liveness_start = None
                self.liveness_finished = False

            self.show_frame(
                frame
            )

            return

        landmarks = (
            result.face_landmarks[0]
        )

        height, width, _ = (
            frame.shape
        )

        xs = [
            p.x
            for p in landmarks
        ]

        ys = [
            p.y
            for p in landmarks
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
        # RESULT COOLDOWN
        # =================================================

        if self.result_state in (
            "success",
            "duplicate",
            "time_error",
            "failure",
        ):

            elapsed = (
                time.time()
                - (
                    self.result_start_time
                    or time.time()
                )
            )

            if elapsed >= RESULT_COOLDOWN:

                self.waiting_for_face_exit = True

            if self.result_state == "success":

                color = (
                    0,
                    255,
                    0,
                )

                text = (
                    "ABSENSI BERHASIL | "
                    f"{self.recognized_name} | "
                    f"{self.attendance_status}"
                )

            elif self.result_state == "failure":

                color = (
                    0,
                    0,
                    255,
                )

                text = (
                    "ABSENSI GAGAL | "
                    "Unknown"
                )

            else:

                color = (
                    0,
                    165,
                    255,
                )

                text = (
                    self.status_label.text()
                )

            cv2.rectangle(
                frame,
                (min_x, min_y),
                (max_x, max_y),
                color,
                2,
            )

            cv2.putText(
                frame,
                self.recognized_name,
                (
                    max(20, min_x),
                    max(
                        40,
                        min_y - 30,
                    ),
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                color,
                2,
            )

            self.status_label.setText(
                text
            )

            self.show_frame(
                frame
            )

            return

        # =================================================
        # WAJAH TERLALU JAUH
        # =================================================

        if (
            face_width
            < MIN_FACE_WIDTH
            or face_height
            < MIN_FACE_HEIGHT
        ):

            self.status_label.setText(
                "Silakan mendekat"
            )

            self.vote_results.clear()
            self.vote_scores.clear()
            self.vote_boxes.clear()

            self.show_frame(
                frame
            )

            return

        # =================================================
        # LIVENESS
        # =================================================

        left_ear = calculate_ear(
            landmarks,
            self.left_eye,
        )

        right_ear = calculate_ear(
            landmarks,
            self.right_eye,
        )

        ear = (
            left_ear
            + right_ear
        ) / 2.0

        if (
            self.liveness_start
            is None
        ):

            self.liveness_start = (
                time.time()
            )

        elapsed = (
            time.time()
            - self.liveness_start
        )

        remaining = max(
            0,
            LIVENESS_DURATION
            - elapsed,
        )

        if (
            self.blink_state == 0
            and ear > EYE_OPEN_THRESHOLD
        ):

            self.blink_state = 1

        elif (
            self.blink_state == 1
            and ear < EYE_CLOSED_THRESHOLD
        ):

            self.blink_state = 2

        elif (
            self.blink_state == 2
            and ear > EYE_OPEN_THRESHOLD
        ):

            self.blink_state = 3

            self.liveness_finished = True

            self.vote_results.clear()
            self.vote_scores.clear()
            self.vote_boxes.clear()

        if not self.liveness_finished:

            if (
                elapsed
                < LIVENESS_DURATION
            ):

                self.status_label.setText(
                    "Silakan berkedip "
                    f"({remaining:.1f}s)"
                )

            else:

                self.result_state = (
                    "failure"
                )

                self.result_start_time = (
                    time.time()
                )

                self.recognized_name = (
                    "Unknown"
                )

                self.status_label.setText(
                    "LIVENESS GAGAL | "
                    "Coba lagi"
                )

            cv2.rectangle(
                frame,
                (min_x, min_y),
                (max_x, max_y),
                (255, 255, 0),
                2,
            )

            cv2.putText(
                frame,
                f"EAR: {ear:.2f}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2,
            )

            self.show_frame(
                frame
            )

            return

        # =================================================
        # RECOGNITION
        # =================================================

        (
            current_name,
            current_score,
            current_box,
        ) = self.recognize_face(
            frame,
            landmarks,
        )

        if current_name == "TOO_FAR":

            self.status_label.setText(
                "Silakan mendekat"
            )

            self.vote_results.clear()
            self.vote_scores.clear()
            self.vote_boxes.clear()

            self.show_frame(
                frame
            )

            return

        vote = self.add_vote(
            current_name,
            current_score,
            current_box,
        )

        vote_count = len(
            self.vote_results
        )

        cv2.rectangle(
            frame,
            (min_x, min_y),
            (max_x, max_y),
            (0, 255, 255),
            2,
        )

        cv2.putText(
            frame,
            f"Voting {vote_count}/{VOTE_FRAMES}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
        )

        self.name_info.setText(
            f"Nama: {current_name}"
        )

        self.score_info.setText(
            f"Similarity: {current_score:.4f}"
        )

        if vote is None:

            self.status_label.setText(
                "Memverifikasi wajah..."
            )

            self.show_frame(
                frame
            )

            return

        # =================================================
        # HASIL VOTING
        # =================================================

        (
            final_name,
            final_score,
            final_box,
            final_votes,
            unknown_votes,
        ) = vote

        print(
            "[VOTING]",
            f"Name={final_name}",
            f"Votes={final_votes}/{VOTE_FRAMES}",
            f"Unknown={unknown_votes}/{VOTE_FRAMES}",
            f"Score={final_score:.2f}",
        )

        x1, y1, x2, y2 = (
            final_box
        )

        # =================================================
        # UNKNOWN
        # =================================================

        if (
            final_name == "Unknown"
            or final_votes
            < VOTE_REQUIRED
            or final_score
            < SFACE_COSINE_THRESHOLD
        ):

            self.result_state = (
                "failure"
            )

            self.result_start_time = (
                time.time()
            )

            self.recognized_name = (
                "Unknown"
            )

            self.recognition_score = (
                final_score
            )

            self.status_label.setText(
                "ABSENSI GAGAL | "
                "Wajah tidak dikenali"
            )

            self.name_info.setText(
                "Nama: Unknown"
            )

            self.score_info.setText(
                f"Similarity: {final_score:.4f}"
            )

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 0, 255),
                2,
            )

            cv2.putText(
                frame,
                "Unknown",
                (
                    max(20, x1),
                    max(
                        40,
                        y1 - 30,
                    ),
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2,
            )

            self.show_frame(
                frame
            )

            return

        # =================================================
        # USER DIKENALI
        # =================================================

        self.recognized_name = (
            final_name
        )

        self.recognition_score = (
            final_score
        )

        # FINAL ACTIVE USER GATE
        # Jangan pernah menyimpan absensi jika nama final
        # sudah tidak ada di people.csv sebagai user aktif.
        active_names = {
            str(name).strip()
            for name in self.active_people.values()
        }

        if final_name not in active_names:
            print(
                "[ATTENDANCE] Ditolak: user final "
                "tidak aktif lagi:",
                final_name,
            )

            self.result_state = "failure"
            self.result_start_time = time.time()
            self.recognized_name = "Unknown"
            self.recognition_score = final_score

            self.status_label.setText(
                "ABSENSI GAGAL | User tidak aktif"
            )

            self.name_info.setText(
                "Nama: Unknown"
            )

            self.score_info.setText(
                f"Similarity: {final_score:.4f}"
            )

            self.show_frame(frame)
            return

        (
            allowed,
            reason,
            message,
            attendance_status,
        ) = self.attendance_decision(
            final_name
        )

        # =================================================
        # DITOLAK OLEH ATURAN JAM
        # =================================================

        if not allowed:

            if reason == "DUPLICATE":

                self.result_state = (
                    "duplicate"
                )

            else:

                self.result_state = (
                    "time_error"
                )

            self.result_start_time = (
                time.time()
            )

            self.status_label.setText(
                message
            )

            self.name_info.setText(
                f"Nama: {final_name}"
            )

            self.score_info.setText(
                f"Score: {final_score:.2f}"
            )

            self.time_info.setText(
                "Waktu: "
                + datetime.now().strftime(
                    "%H:%M:%S"
                )
            )

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 165, 255),
                2,
            )

            cv2.putText(
                frame,
                final_name,
                (
                    max(20, x1),
                    max(
                        40,
                        y1 - 30,
                    ),
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 165, 255),
                2,
            )

            self.show_frame(
                frame
            )

            return

        # =================================================
        # SIMPAN ABSENSI
        # =================================================

        now = datetime.now()

        success = self.save_attendance(
            final_name,
            final_score,
            attendance_status,
        )

        if not success:

            self.result_state = (
                "failure"
            )

            self.result_start_time = (
                time.time()
            )

            self.status_label.setText(
                "Gagal menyimpan absensi."
            )

            self.show_frame(
                frame
            )

            return

        # =================================================
        # SUCCESS
        # =================================================

        self.result_state = (
            "success"
        )

        self.result_start_time = (
            time.time()
        )

        self.attendance_status = (
            attendance_status
        )

        self.attendance_time = now

        self.status_label.setText(
            "ABSENSI BERHASIL | "
            f"{final_name} | "
            f"{attendance_status}"
        )

        self.name_info.setText(
            f"Nama: {final_name}"
        )

        self.score_info.setText(
            f"Similarity: {final_score:.4f}"
        )

        self.time_info.setText(
            "Waktu: "
            + now.strftime(
                "%H:%M:%S"
            )
        )

        # =================================================
        # TABLE
        # =================================================

        self.add_table_row(
            final_name,
            now.strftime(
                "%Y-%m-%d"
            ),
            now.strftime(
                "%H:%M:%S"
            ),
            f"{final_score:.2f}",
            attendance_status,
        )

        # =================================================
        # CAMERA RESULT
        # =================================================

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2,
        )

        cv2.putText(
            frame,
            final_name,
            (
                max(20, x1),
                max(
                    40,
                    y1 - 30,
                ),
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
        )

        cv2.putText(
            frame,
            attendance_status,
            (
                max(20, x1),
                max(
                    70,
                    y1 - 5,
                ),
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 0),
            2,
        )

        self.show_frame(
            frame
        )

        print("=" * 50)
        print(
            "ABSENSI BERHASIL"
        )
        print(
            f"Nama   : {final_name}"
        )
        print(
            f"Score  : {final_score:.2f}"
        )
        print(
            f"Voting : "
            f"{final_votes}/{VOTE_FRAMES}"
        )
        print(
            f"Waktu  : "
            f"{now.strftime('%H:%M:%S')}"
        )
        print(
            f"Status : "
            f"{attendance_status}"
        )
        print("=" * 50)

    # =====================================================
    # SHOW FRAME
    # =====================================================

    def show_frame(
        self,
        frame,
    ):

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB,
        )

        height, width, channel = (
            rgb.shape
        )

        bytes_per_line = (
            channel * width
        )

        image = QImage(
            rgb.data,
            width,
            height,
            bytes_per_line,
            QImage.Format_RGB888,
        )

        pixmap = QPixmap.fromImage(
            image
        )

        pixmap = pixmap.scaled(
            self.camera_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        self.camera_label.setPixmap(
            pixmap
        )

    # =====================================================
    # CLOSE
    # =====================================================

    def closeEvent(
        self,
        event,
    ):

        if hasattr(
            self,
            "timer",
        ):

            self.timer.stop()

        if hasattr(
            self,
            "camera",
        ):

            if self.camera.isOpened():

                self.camera.release()

        if hasattr(
            self,
            "landmarker",
        ):

            try:

                self.landmarker.close()

            except Exception:
                pass

        event.accept()


# =========================================================
# MAIN
# =========================================================

def main():

    app = QApplication(
        sys.argv
    )

    app.setStyle(
        "Fusion"
    )

    window = ScanlyWindow()

    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()