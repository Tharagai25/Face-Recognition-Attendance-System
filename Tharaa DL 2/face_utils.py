"""
Webcam/image helpers, face detection (OpenCV), and face matching (face_recognition).
"""

from __future__ import annotations

import io
from typing import Any

import cv2
import face_recognition
import numpy as np
from PIL import Image

# Default tolerance for face_recognition.compare_faces (lower = stricter).
MATCH_TOLERANCE = 0.5


def image_bytes_to_bgr(image_bytes: bytes) -> np.ndarray:
    """Decode uploaded or captured image bytes to OpenCV BGR array."""
    pil = Image.open(io.BytesIO(image_bytes))
    if pil.mode != "RGB":
        pil = pil.convert("RGB")
    rgb = np.array(pil)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def bgr_to_rgb(bgr: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def encode_image_to_jpeg_bytes(bgr: np.ndarray, quality: int = 85) -> bytes:
    rgb = bgr_to_rgb(bgr)
    pil = Image.fromarray(rgb)
    buf = io.BytesIO()
    pil.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def detect_faces_opencv(bgr: np.ndarray) -> list[tuple[int, int, int, int]]:
    """
    Return face bounding boxes (top, right, bottom, left) using OpenCV Haar cascade.
    Used for drawing boxes; matching uses face_recognition encodings.
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(cascade_path)
    if detector.empty():
        return []
    faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    boxes: list[tuple[int, int, int, int]] = []
    for x, y, w, h in faces:
        boxes.append((y, x + w, y + h, x))  # top, right, bottom, left
    return boxes


def draw_face_boxes(bgr: np.ndarray, boxes: list[tuple[int, int, int, int]]) -> np.ndarray:
    out = bgr.copy()
    for top, right, bottom, left in boxes:
        cv2.rectangle(out, (left, top), (right, bottom), (0, 200, 0), 2)
    return out


def get_single_face_encoding(rgb: np.ndarray) -> np.ndarray:
    """
    Compute a 128-D face encoding. Requires exactly one face in the image.
    Raises ValueError with a beginner-friendly message on failure.
    """
    locations = face_recognition.face_locations(rgb, model="hog")
    if len(locations) == 0:
        raise ValueError(
            "No face detected. Face the camera in good lighting, or try a clearer photo."
        )
    if len(locations) > 1:
        raise ValueError(
            "Multiple faces detected. Only one person should be in the frame for registration."
        )
    encodings = face_recognition.face_encodings(rgb, known_face_locations=locations)
    if not encodings:
        raise ValueError(
            "Could not compute a face encoding. Try a front-facing photo with better lighting."
        )
    return encodings[0]


def encoding_to_bytes(encoding: np.ndarray) -> bytes:
    return encoding.astype(np.float64).tobytes()


def bytes_to_encoding(data: bytes) -> np.ndarray:
    return np.frombuffer(data, dtype=np.float64)


def crop_largest_face_jpeg(bgr: np.ndarray, rgb: np.ndarray) -> bytes:
    """Store a small thumbnail of the registered face for display in the app."""
    boxes = detect_faces_opencv(bgr)
    if not boxes:
        return encode_image_to_jpeg_bytes(bgr)
    top, right, bottom, left = max(boxes, key=lambda b: (b[2] - b[0]) * (b[1] - b[3]))
    pad = 20
    h, w = bgr.shape[:2]
    top = max(0, top - pad)
    left = max(0, left - pad)
    bottom = min(h, bottom + pad)
    right = min(w, right + pad)
    crop = bgr[top:bottom, left:right]
    return encode_image_to_jpeg_bytes(crop)


def match_face_against_registered(
    rgb: np.ndarray,
    registered: list[tuple[str, str, bytes]],
    tolerance: float = MATCH_TOLERANCE,
) -> dict[str, Any]:
    """
    Try to identify a registered student from a webcam frame.
    Returns dict with keys: matched (bool), student_id, name, distance (optional), message.
    Does not identify people who are not registered.
    """
    if not registered:
        return {
            "matched": False,
            "student_id": None,
            "name": None,
            "message": "No students registered yet. Register students before marking attendance.",
        }

    locations = face_recognition.face_locations(rgb, model="hog")
    if len(locations) == 0:
        return {
            "matched": False,
            "student_id": None,
            "name": None,
            "message": "No face detected in the image. Adjust lighting or move closer to the camera.",
        }
    if len(locations) > 1:
        return {
            "matched": False,
            "student_id": None,
            "name": None,
            "message": "Multiple faces detected. Only one person should be in frame for automatic check-in.",
        }

    unknown_encodings = face_recognition.face_encodings(rgb, known_face_locations=locations)
    if not unknown_encodings:
        return {
            "matched": False,
            "student_id": None,
            "name": None,
            "message": "Could not read facial features. Try again or use manual attendance.",
        }

    unknown = unknown_encodings[0]
    known_encodings = [bytes_to_encoding(item[2]) for item in registered]
    distances = face_recognition.face_distance(known_encodings, unknown)
    best_idx = int(np.argmin(distances))
    best_distance = float(distances[best_idx])

    if best_distance <= tolerance:
        sid, name, _ = registered[best_idx]
        return {
            "matched": True,
            "student_id": sid,
            "name": name,
            "distance": best_distance,
            "message": f"Recognized: {name} ({sid}).",
        }

    return {
        "matched": False,
        "student_id": None,
        "name": None,
        "distance": best_distance,
        "message": (
            "Face not matched to any registered student. "
            "Use manual attendance if this person is enrolled, or register them first."
        ),
    }


def process_registration_image(image_bytes: bytes) -> tuple[np.ndarray, bytes, bytes]:
    """
    Validate image, return (encoding_bytes, thumbnail_jpeg_bytes, annotated_preview_jpeg).
    """
    bgr = image_bytes_to_bgr(image_bytes)
    rgb = bgr_to_rgb(bgr)
    encoding = get_single_face_encoding(rgb)
    thumb = crop_largest_face_jpeg(bgr, rgb)
    boxes = detect_faces_opencv(bgr)
    preview = draw_face_boxes(bgr, boxes) if boxes else bgr
    preview_bytes = encode_image_to_jpeg_bytes(preview)
    return encoding_to_bytes(encoding), thumb, preview_bytes
