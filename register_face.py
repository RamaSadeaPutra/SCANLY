import csv
import json
from pathlib import Path

import cv2
import numpy as np


# =========================================================
# SCANLY - MULTI USER LBPH TRAINING
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

FACES_DIR = BASE_DIR / "faces"
MODEL_DIR = BASE_DIR / "face_model"

MODEL_PATH = MODEL_DIR / "scanly_faces.yml"
LABEL_MAP_PATH = MODEL_DIR / "label_map.json"

PEOPLE_FILE = BASE_DIR / "people.csv"

# =========================================================
# HAAR CASCADE
# =========================================================

CASCADE_PATH = (
    MODEL_DIR
    / "haarcascade_frontalface_default.xml"
)

# =========================================================
# FACE SETTINGS
# =========================================================

FACE_SIZE = (
    200,
    200
)

# Harus sama dengan main.py
LBPH_RADIUS = 1
LBPH_NEIGHBORS = 8
LBPH_GRID_X = 8
LBPH_GRID_Y = 8

USE_AUGMENTATION = True

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".jpe",
    ".png",
    ".bmp",
    ".webp",
}


# =========================================================
# PREPROCESSING
# =========================================================

def preprocess_face(image):

    if (
        image is None
        or image.size == 0
    ):
        return None

    # -----------------------------------------------------
    # BGR -> GRAYSCALE
    # -----------------------------------------------------

    try:

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

    except Exception as error:

        print(
            "[ERROR] Gagal grayscale:",
            error
        )

        return None

    # -----------------------------------------------------
    # RESIZE
    # -----------------------------------------------------

    gray = cv2.resize(
        gray,
        FACE_SIZE,
        interpolation=cv2.INTER_AREA
    )

    # -----------------------------------------------------
    # CLAHE
    # -----------------------------------------------------

    clahe = cv2.createCLAHE(
        clipLimit=1.5,
        tileGridSize=(
            8,
            8
        )
    )

    gray = clahe.apply(
        gray
    )

    # -----------------------------------------------------
    # GAUSSIAN BLUR
    # -----------------------------------------------------

    gray = cv2.GaussianBlur(
        gray,
        (
            3,
            3
        ),
        0
    )

    return gray


# =========================================================
# AUGMENTASI
# =========================================================

def augment(gray):

    samples = [
        gray
    ]

    if not USE_AUGMENTATION:

        return samples

    # -----------------------------------------------------
    # FLIP
    # -----------------------------------------------------

    samples.append(
        cv2.flip(
            gray,
            1
        )
    )

    # -----------------------------------------------------
    # LEBIH TERANG
    # -----------------------------------------------------

    samples.append(
        cv2.convertScaleAbs(
            gray,
            alpha=1.0,
            beta=10
        )
    )

    # -----------------------------------------------------
    # LEBIH GELAP
    # -----------------------------------------------------

    samples.append(
        cv2.convertScaleAbs(
            gray,
            alpha=1.0,
            beta=-10
        )
    )

    return samples


# =========================================================
# LOAD PEOPLE.CSV
# =========================================================

def load_people():

    people = []

    if not PEOPLE_FILE.exists():

        print(
            "[WARNING] people.csv tidak ditemukan:"
        )

        print(
            PEOPLE_FILE
        )

        return people

    try:

        with open(
            PEOPLE_FILE,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.DictReader(
                file
            )

            for row in reader:

                name = str(
                    row.get(
                        "Nama",
                        ""
                    )
                ).strip()

                person_id = str(
                    row.get(
                        "ID",
                        ""
                    )
                ).strip()

                status = str(
                    row.get(
                        "Status",
                        "Aktif"
                    )
                ).strip()

                folder = str(
                    row.get(
                        "Folder",
                        ""
                    )
                ).strip()

                if not name:

                    continue

                # -------------------------------------------------
                # HANYA USER AKTIF
                # -------------------------------------------------

                if status.lower() not in (
                    "",
                    "aktif",
                    "active"
                ):

                    continue

                people.append({
                    "ID": person_id,
                    "Nama": name,
                    "Folder": folder,
                })

    except Exception as error:

        print(
            "[ERROR] Gagal membaca people.csv:"
        )

        print(
            error
        )

    return people


# =========================================================
# FOLDER PERSON
# =========================================================

def get_person_folder(person):

    folder = str(
        person.get(
            "Folder",
            ""
        )
    ).strip()

    name = str(
        person.get(
            "Nama",
            ""
        )
    ).strip()

    # -----------------------------------------------------
    # PAKAI FOLDER DARI CSV
    # -----------------------------------------------------

    if folder:

        folder = folder.replace(
            "\\",
            "/"
        )

        folder_path = (
            BASE_DIR
            / folder
        )

        return folder_path

    # -----------------------------------------------------
    # FALLBACK faces/Nama
    # -----------------------------------------------------

    safe_name = name

    for char in '<>:"/\\|?*':

        safe_name = safe_name.replace(
            char,
            "_"
        )

    return (
        FACES_DIR
        / safe_name
    )


# =========================================================
# GET IMAGE FILES
# =========================================================

def get_images(folder):

    if not folder.exists():

        return []

    result = []

    try:

        for path in folder.rglob("*"):

            if not path.is_file():

                continue

            if (
                path.suffix.lower()
                in IMAGE_EXTENSIONS
            ):

                result.append(
                    path
                )

    except Exception as error:

        print(
            "[ERROR] Gagal membaca folder:"
        )

        print(
            folder
        )

        print(
            error
        )

    return sorted(
        result
    )


# =========================================================
# LOAD HAAR CASCADE
# =========================================================

def load_face_cascade():

    print()
    print(
        "[INFO] Haar Cascade:"
    )

    print(
        CASCADE_PATH
    )

    if not CASCADE_PATH.exists():

        print()
        print(
            "[ERROR] Haar Cascade tidak ditemukan."
        )

        print(
            "File yang dibutuhkan:"
        )

        print(
            CASCADE_PATH
        )

        print()
        print(
            "Pastikan file:"
        )

        print(
            "haarcascade_frontalface_default.xml"
        )

        print(
            "berada di folder:"
        )

        print(
            "C:\\Scanly\\face_model"
        )

        return None

    cascade = cv2.CascadeClassifier(
        str(CASCADE_PATH)
    )

    if cascade.empty():

        print()
        print(
            "[ERROR] Haar Cascade gagal dimuat."
        )

        print(
            CASCADE_PATH
        )

        return None

    print(
        "[OK] Haar Cascade berhasil dimuat."
    )

    return cascade


# =========================================================
# DETEKSI WAJAH
# =========================================================

def detect_face(
    image,
    cascade
):

    if (
        image is None
        or image.size == 0
    ):

        return None

    if cascade is None:

        return None

    # -----------------------------------------------------
    # GRAYSCALE
    # -----------------------------------------------------

    try:

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

    except Exception as error:

        print(
            "[ERROR] Gagal grayscale:",
            error
        )

        return None

    # -----------------------------------------------------
    # DETEKSI
    # -----------------------------------------------------

    faces = cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=6,
        minSize=(
            70,
            70
        )
    )

    if len(faces) == 0:

        return None

    # -----------------------------------------------------
    # PILIH WAJAH TERBESAR
    # -----------------------------------------------------

    largest = max(
        faces,
        key=lambda r: (
            r[2] * r[3]
        )
    )

    x, y, w, h = largest

    # -----------------------------------------------------
    # MARGIN
    # -----------------------------------------------------

    margin_x = int(
        w * 0.15
    )

    margin_y = int(
        h * 0.15
    )

    x1 = max(
        0,
        x - margin_x
    )

    y1 = max(
        0,
        y - margin_y
    )

    x2 = min(
        image.shape[1],
        x + w + margin_x
    )

    y2 = min(
        image.shape[0],
        y + h + margin_y
    )

    # -----------------------------------------------------
    # CROP
    # -----------------------------------------------------

    face = image[
        y1:y2,
        x1:x2
    ]

    if (
        face is None
        or face.size == 0
    ):

        return None

    return face


# =========================================================
# VALIDASI WAJAH
# =========================================================

def validate_face(
    image,
    cascade
):

    face = detect_face(
        image,
        cascade
    )

    if face is None:

        return None

    processed = preprocess_face(
        face
    )

    if processed is None:

        return None

    return processed


# =========================================================
# MAIN
# =========================================================

def main():

    print(
        "=" * 60
    )

    print(
        "SCANLY - MULTI USER LBPH TRAINING"
    )

    print(
        "=" * 60
    )

    # =====================================================
    # BUAT FOLDER
    # =====================================================

    FACES_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # =====================================================
    # LOAD CASCADE
    # =====================================================

    cascade = load_face_cascade()

    if cascade is None:

        return 1

    # =====================================================
    # LOAD PEOPLE
    # =====================================================

    people = load_people()

    if not people:

        print()
        print(
            "[ERROR] Tidak ada pengguna aktif."
        )

        return 1

    # =====================================================
    # PREPARE PERSON LIST
    # =====================================================

    persons = []

    for person in people:

        folder = get_person_folder(
            person
        )

        persons.append({
            "ID": person["ID"],
            "Nama": person["Nama"],
            "Folder": folder,
        })

    # =====================================================
    # TRAINING DATA
    # =====================================================

    faces = []

    labels = []

    label_map = {}

    label = 0

    # =====================================================
    # LOOP USER
    # =====================================================

    for person in persons:

        person_id = person["ID"]

        name = person["Nama"]

        folder = person["Folder"]

        print()
        print(
            "-" * 60
        )

        print(
            f"ID     : {person_id}"
        )

        print(
            f"Nama   : {name}"
        )

        print(
            f"Folder : {folder}"
        )

        # -------------------------------------------------
        # CEK FOLDER
        # -------------------------------------------------

        if not folder.exists():

            print(
                "[SKIP] Folder tidak ditemukan."
            )

            continue

        # -------------------------------------------------
        # GET IMAGES
        # -------------------------------------------------

        files = get_images(
            folder
        )

        print(
            f"Foto   : {len(files)}"
        )

        if not files:

            print(
                "[SKIP] Tidak ada foto."
            )

            continue

        # -------------------------------------------------
        # TEMPORARY USER SAMPLES
        # -------------------------------------------------

        person_faces = []

        person_labels = []

        valid_images = 0

        sample_count = 0

        # =================================================
        # LOOP FOTO
        # =================================================

        for image_path in files:

            image = cv2.imread(
                str(image_path)
            )

            if image is None:

                print(
                    f"[SKIP] Gagal membaca "
                    f"{image_path.name}"
                )

                continue

            # -------------------------------------------------
            # DETEKSI WAJAH
            # -------------------------------------------------

            face = detect_face(
                image,
                cascade
            )

            # -------------------------------------------------
            # JANGAN TRAIN FOTO TANPA WAJAH
            # -------------------------------------------------

            if face is None:

                print(
                    f"[SKIP] Wajah tidak ditemukan "
                    f"pada {image_path.name}"
                )

                continue

            # -------------------------------------------------
            # PREPROCESS
            # -------------------------------------------------

            processed = preprocess_face(
                face
            )

            if processed is None:

                print(
                    f"[SKIP] Preprocessing gagal "
                    f"pada {image_path.name}"
                )

                continue

            # -------------------------------------------------
            # AUGMENTASI
            # -------------------------------------------------

            samples = augment(
                processed
            )

            if not samples:

                print(
                    f"[SKIP] Sample kosong "
                    f"pada {image_path.name}"
                )

                continue

            # -------------------------------------------------
            # SIMPAN SAMPLE SEMENTARA
            # -------------------------------------------------

            for sample in samples:

                person_faces.append(
                    sample
                )

                person_labels.append(
                    label
                )

                sample_count += 1

            valid_images += 1

            print(
                f"[OK] {image_path.name}"
                f" -> {len(samples)} sample"
            )

        # =================================================
        # HASIL USER
        # =================================================

        print(
            f"Valid foto : {valid_images}"
        )

        print(
            f"Training sample : {sample_count}"
        )

        # -------------------------------------------------
        # USER VALID
        # -------------------------------------------------

        if valid_images > 0:

            # Simpan label map hanya kalau
            # user benar-benar punya sample.

            label_map[
                str(label)
            ] = {
                "ID": person_id,
                "Nama": name,
            }

            faces.extend(
                person_faces
            )

            labels.extend(
                person_labels
            )

            label += 1

        else:

            print(
                "[SKIP] User tidak memiliki "
                "foto wajah valid."
            )

    # =====================================================
    # VALIDASI GLOBAL
    # =====================================================

    print()
    print(
        "=" * 60
    )

    print(
        f"Total sample : {len(faces)}"
    )

    print(
        f"Total user   : {len(label_map)}"
    )

    print(
        "=" * 60
    )

    if not faces:

        print()
        print(
            "[ERROR] Tidak ada sample training."
        )

        print()
        print(
            "Pastikan:"
        )

        print(
            "1. Foto berisi wajah."
        )

        print(
            "2. Haar Cascade tersedia."
        )

        print(
            "3. Folder pada people.csv benar."
        )

        return 1

    # =====================================================
    # CONVERT LABEL
    # =====================================================

    labels_np = np.asarray(
        labels,
        dtype=np.int32
    )

    # =====================================================
    # TRAIN LBPH
    # =====================================================

    print()
    print(
        "Training LBPH..."
    )

    try:

        recognizer = (
            cv2.face
            .LBPHFaceRecognizer_create(
                radius=LBPH_RADIUS,
                neighbors=LBPH_NEIGHBORS,
                grid_x=LBPH_GRID_X,
                grid_y=LBPH_GRID_Y
            )
        )

    except Exception as error:

        print()
        print(
            "[ERROR] LBPH tidak tersedia."
        )

        print(
            error
        )

        print()
        print(
            "Pastikan opencv-contrib-python "
            "terinstall."
        )

        return 1

    # -----------------------------------------------------
    # TRAIN
    # -----------------------------------------------------

    try:

        recognizer.train(
            faces,
            labels_np
        )

    except Exception as error:

        print()
        print(
            "[ERROR] Training gagal:"
        )

        print(
            error
        )

        return 1

    # =====================================================
    # SIMPAN MODEL
    # =====================================================

    try:

        recognizer.write(
            str(MODEL_PATH)
        )

    except Exception as error:

        print()
        print(
            "[ERROR] Gagal menyimpan model:"
        )

        print(
            error
        )

        return 1

    # =====================================================
    # SIMPAN LABEL MAP
    # =====================================================

    try:

        with open(
            LABEL_MAP_PATH,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                label_map,
                file,
                ensure_ascii=False,
                indent=2
            )

    except Exception as error:

        print()
        print(
            "[ERROR] Gagal menyimpan label map:"
        )

        print(
            error
        )

        return 1

    # =====================================================
    # SELESAI
    # =====================================================

    print()
    print(
        "=" * 60
    )

    print(
        "[SUCCESS] TRAINING SELESAI"
    )

    print(
        "=" * 60
    )

    print()

    print(
        f"Model     : {MODEL_PATH}"
    )

    print(
        f"Label map : {LABEL_MAP_PATH}"
    )

    print()

    print(
        "LABEL MAP:"
    )

    print(
        "-" * 60
    )

    for key, value in label_map.items():

        print(
            f"label {key}"
            f" -> {value['Nama']}"
            f" ({value['ID']})"
        )

    print()
    print(
        f"Total user   : {len(label_map)}"
    )

    print(
        f"Total sample : {len(faces)}"
    )

    print()
    print(
        "[SUCCESS] Model siap digunakan "
        "oleh Scanly."
    )

    return 0


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )