import cv2
import mediapipe as mp


# =========================================================
# KONFIGURASI   
# =========================================================

MODEL_PATH = "face_model/scanly_faces.yml"

# Hasil pengujian sebelumnya:
# Kamu     : 45-50
# Orang lain: 56-66
CONFIDENCE_THRESHOLD = 85.0

# Ukuran minimum wajah di kamera.
# Kalau lebih kecil dari ini, dianggap terlalu jauh.
MIN_FACE_WIDTH = 120
MIN_FACE_HEIGHT = 120

# Semua wajah yang masuk ke LBPH dibuat ukuran sama
FACE_SIZE = (200, 200)

NAME = "Rama Sadea Putra As"


# =========================================================
# LOAD LBPH
# =========================================================

recognizer = cv2.face.LBPHFaceRecognizer_create()

recognizer.read(MODEL_PATH)

print("Model berhasil dimuat.")


# =========================================================
# MEDIAPIPE FACE LANDMARKER
# =========================================================

BaseOptions = mp.tasks.BaseOptions

FaceLandmarker = (
    mp.tasks.vision.FaceLandmarker
)

FaceLandmarkerOptions = (
    mp.tasks.vision.FaceLandmarkerOptions
)

options = FaceLandmarkerOptions(
    base_options=BaseOptions(
        model_asset_path="models/face_landmarker.task"
    ),
    num_faces=1
)

landmarker = (
    FaceLandmarker.create_from_options(
        options
    )
)


# =========================================================
# CAMERA
# =========================================================

camera = cv2.VideoCapture(0)

if not camera.isOpened():

    print("ERROR: Kamera tidak dapat dibuka.")

    landmarker.close()

    raise SystemExit


print()
print("======================================")
print("SCANLY FACE RECOGNITION TEST")
print("======================================")
print("Target jarak: sekitar 0.5 - 1 meter")
print("Tekan Q untuk keluar.")
print()


# =========================================================
# LOOP
# =========================================================

while True:

    ret, frame = camera.read()

    if not ret:
        continue

    # =====================================================
    # MIRROR
    # =====================================================

    frame = cv2.flip(frame, 1)

    # =====================================================
    # MEDIAPIPE
    # =====================================================

    rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb
    )

    result = landmarker.detect(
        mp_image
    )

    # =====================================================
    # TIDAK ADA WAJAH
    # =====================================================

    if not result.face_landmarks:

        cv2.putText(
            frame,
            "Wajah tidak terdeteksi",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2
        )

        cv2.imshow(
            "Scanly - Distance Recognition Test",
            frame
        )

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

        continue

    # =====================================================
    # LANDMARK
    # =====================================================

    landmarks = result.face_landmarks[0]

    height, width, _ = frame.shape

    # =====================================================
    # BOUNDING BOX
    # =====================================================

    xs = [
        landmark.x
        for landmark in landmarks
    ]

    ys = [
        landmark.y
        for landmark in landmarks
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

    # =====================================================
    # UKURAN WAJAH
    # =====================================================

    face_width = max_x - min_x
    face_height = max_y - min_y

    # =====================================================
    # MARGIN
    # =====================================================

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

    # =====================================================
    # GAMBAR KOTAK WAJAH
    # =====================================================

    cv2.rectangle(
        frame,
        (min_x, min_y),
        (max_x, max_y),
        (255, 255, 0),
        2
    )

    # =====================================================
    # TERLALU JAUH
    # =====================================================

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
            (20, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )

    else:

        # =================================================
        # CROP WAJAH
        # =================================================

        face = frame[
            crop_y1:crop_y2,
            crop_x1:crop_x2
        ]

        if face.size != 0:

            # =============================================
            # GRAYSCALE
            # =============================================

            face_gray = cv2.cvtColor(
                face,
                cv2.COLOR_BGR2GRAY
            )

            # =============================================
            # NORMALISASI UKURAN
            # =============================================

            face_gray = cv2.resize(
                face_gray,
                FACE_SIZE,
                interpolation=cv2.INTER_AREA
            )

            # =============================================
            # LBPH
            # =============================================

            label, score = (
                recognizer.predict(
                    face_gray
                )
            )

            # =============================================
            # KEPUTUSAN
            # =============================================

            if (
                label == 0
                and
                score < CONFIDENCE_THRESHOLD
            ):

                result_name = NAME

                box_color = (
                    0,
                    255,
                    0
                )

            else:

                result_name = "Unknown"

                box_color = (
                    0,
                    0,
                    255
                )

            # =============================================
            # BOX
            # =============================================

            cv2.rectangle(
                frame,
                (min_x, min_y),
                (max_x, max_y),
                box_color,
                2
            )

            # =============================================
            # NAMA
            # =============================================

            cv2.putText(
                frame,
                result_name,
                (
                    max(20, min_x),
                    max(40, min_y - 30)
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                box_color,
                2
            )

            # =============================================
            # SCORE
            # =============================================

            cv2.putText(
                frame,
                f"Score: {score:.1f}",
                (
                    max(20, min_x),
                    max(65, min_y - 5)
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                box_color,
                2
            )

            # =============================================
            # FACE SIZE
            # =============================================

            cv2.putText(
                frame,
                f"Face: {face_width} x {face_height}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

    # =====================================================
    # DISPLAY
    # =====================================================

    cv2.imshow(
        "Scanly - Distance Recognition Test",
        frame
    )

    # =====================================================
    # EXIT
    # =====================================================

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break


# =========================================================
# CLEANUP
# =========================================================

camera.release()

cv2.destroyAllWindows()

landmarker.close()