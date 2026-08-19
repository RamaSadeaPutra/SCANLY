import cv2
import os

# ==========================================
# KONFIGURASI
# ==========================================

FACE_DATA_DIR = "face_data"
MODEL_DIR = "face_model"

os.makedirs(
    MODEL_DIR,
    exist_ok=True
)

# ==========================================
# CARI DATA WAJAH
# ==========================================

face_files = []

for filename in os.listdir(FACE_DATA_DIR):

    if filename.lower().endswith(
        (".jpg", ".jpeg", ".png", ".bmp")
    ):

        face_files.append(
            os.path.join(
                FACE_DATA_DIR,
                filename
            )
        )

if not face_files:

    print(
        "ERROR: Tidak ada data wajah."
    )

    raise SystemExit

print(
    f"Data wajah ditemukan: {len(face_files)}"
)

# ==========================================
# SIAPKAN DATA TRAINING
# ==========================================

faces = []
labels = []

# Untuk sekarang:
# 0 = Rama

for face_file in face_files:

    image = cv2.imread(
        face_file,
        cv2.IMREAD_GRAYSCALE
    )

    if image is None:

        print(
            "Gagal membaca:",
            face_file
        )

        continue

    faces.append(image)

    labels.append(0)

    print(
        "Training:",
        face_file
    )

if not faces:

    print(
        "ERROR: Tidak ada wajah yang bisa dilatih."
    )

    raise SystemExit

# ==========================================
# BUAT MODEL LBPH
# ==========================================

recognizer = (
    cv2.face.LBPHFaceRecognizer_create()
)

recognizer.train(
    faces,
    __import__("numpy").array(
        labels
    )
)

# ==========================================
# SIMPAN MODEL
# ==========================================

model_path = (
    "face_model/scanly_faces.yml"
)

recognizer.write(
    model_path
)

print()
print(
    "========================================"
)

print(
    "Training berhasil."
)

print(
    "Model:"
)

print(
    model_path
)

print(
    "========================================"
)