"""
Hand tracking module using MediaPipe Tasks API (HandLandmarker).

Works with mediapipe >= 0.10.x.
Automatically downloads the hand_landmarker.task model safely on first run.
Enforces strictly increasing timestamps to prevent MediaPipe runtime errors.
"""

import os
import time
import urllib.request

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# Hand skeleton connections for visualization
HAND_CONNECTIONS = [
    # Thumb
    (0, 1), (1, 2), (2, 3), (3, 4),
    # Index finger
    (0, 5), (5, 6), (6, 7), (7, 8),
    # Middle finger
    (0, 9), (9, 10), (10, 11), (11, 12),
    # Ring finger
    (0, 13), (13, 14), (14, 15), (15, 16),
    # Pinky
    (0, 17), (17, 18), (18, 19), (19, 20),
    # Palm base
    (5, 9), (9, 13), (13, 17),
]


class HandTracker:
    """Wraps MediaPipe HandLandmarker (Tasks API) for robust real-time detection."""

    TIP_IDS = [4, 8, 12, 16, 20]   # thumb, index, middle, ring, pinky
    PIP_IDS = [3, 6, 10, 14, 18]   # corresponding PIP/IP joints

    MODEL_URL = (
        "https://storage.googleapis.com/mediapipe-models/"
        "hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
    )
    MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hand_landmarker.task")

    def __init__(self, max_hands=1, detection_conf=0.8, tracking_conf=0.8):
        self._ensure_model()

        base_options = python.BaseOptions(model_asset_path=self.MODEL_PATH)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=max_hands,
            min_hand_detection_confidence=detection_conf,
            min_hand_presence_confidence=detection_conf,
            min_tracking_confidence=tracking_conf,
            running_mode=vision.RunningMode.VIDEO,
        )
        self.detector = vision.HandLandmarker.create_from_options(options)

        # Monotonic clock & timestamp tracking for VIDEO mode
        self._start_time = time.monotonic()
        self._last_timestamp_ms = -1

    # ────────────────────────────────────────────────────
    #  Model management
    # ────────────────────────────────────────────────────

    @classmethod
    def _ensure_model(cls):
        """Download model to .tmp first and atomically rename to prevent corrupt downloads."""
        if os.path.exists(cls.MODEL_PATH) and os.path.getsize(cls.MODEL_PATH) > 1000000:
            return

        tmp_path = cls.MODEL_PATH + ".tmp"
        print("  Downloading hand landmarker model (~12 MB)...")
        try:
            urllib.request.urlretrieve(cls.MODEL_URL, tmp_path)
            if os.path.exists(cls.MODEL_PATH):
                os.remove(cls.MODEL_PATH)
            os.rename(tmp_path, cls.MODEL_PATH)
            print("  ✓ Model downloaded successfully.")
        except Exception as exc:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            raise RuntimeError(
                f"Could not download model from {cls.MODEL_URL}.\n"
                f"Download it manually and place it at:\n  {cls.MODEL_PATH}"
            ) from exc

    # ────────────────────────────────────────────────────
    #  Detection
    # ────────────────────────────────────────────────────

    def find_hand(self, frame):
        """
        Detect hand in BGR frame.

        Returns
        -------
        landmarks : list[NormalizedLandmark] or None
        handedness : object or None
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        # Ensure timestamp_ms is strictly monotonically increasing
        timestamp_ms = int((time.monotonic() - self._start_time) * 1000)
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1
        self._last_timestamp_ms = timestamp_ms

        result = self.detector.detect_for_video(mp_image, timestamp_ms)

        if result.hand_landmarks and result.handedness:
            return result.hand_landmarks[0], result.handedness[0]
        return None, None

    # ────────────────────────────────────────────────────
    #  Landmark helpers
    # ────────────────────────────────────────────────────

    def get_positions(self, landmarks, frame_shape):
        """Convert normalized landmarks to dict {id: (x_px, y_px)}."""
        h, w = frame_shape[:2]
        return {
            idx: (int(lm.x * w), int(lm.y * h))
            for idx, lm in enumerate(landmarks)
        }

    def get_fingers_up(self, positions, handedness):
        """
        Determine which 5 fingers are extended [thumb, index, middle, ring, pinky].
        """
        fingers = []

        # Safe extraction of handedness label ("Left" or "Right") across MediaPipe versions
        label = "Right"
        try:
            if hasattr(handedness, 'categories') and handedness.categories:
                label = handedness.categories[0].category_name
            elif isinstance(handedness, list) and len(handedness) > 0:
                first = handedness[0]
                if hasattr(first, 'category_name'):
                    label = first.category_name
                elif hasattr(first, 'categories') and first.categories:
                    label = first.categories[0].category_name
        except Exception:
            label = "Right"

        # Thumb (x-axis comparison considering selfie mirror)
        if label == "Right":
            fingers.append(positions[4][0] < positions[3][0])
        else:
            fingers.append(positions[4][0] > positions[3][0])

        # Index, Middle, Ring, Pinky (y-axis comparison: tip above PIP)
        for tip_id, pip_id in zip(self.TIP_IDS[1:], self.PIP_IDS[1:]):
            fingers.append(positions[tip_id][1] < positions[pip_id][1])

        return fingers

    @staticmethod
    def distance(positions, id1, id2):
        """Euclidean distance between two landmark IDs."""
        x1, y1 = positions[id1]
        x2, y2 = positions[id2]
        return float(np.hypot(x2 - x1, y2 - y1)), ((x1 + x2) // 2, (y1 + y2) // 2)

    # ────────────────────────────────────────────────────
    #  Drawing
    # ────────────────────────────────────────────────────

    def draw(self, frame, landmarks):
        """Render hand skeleton overlay."""
        h, w = frame.shape[:2]
        points = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]

        # Draw bones
        for start_idx, end_idx in HAND_CONNECTIONS:
            cv2.line(
                frame, points[start_idx], points[end_idx],
                (0, 200, 100), 2, cv2.LINE_AA,
            )

        # Draw landmark dots
        for i, pt in enumerate(points):
            is_tip = i in self.TIP_IDS
            color = (50, 50, 255) if is_tip else (0, 230, 120)
            radius = 7 if is_tip else 4
            cv2.circle(frame, pt, radius, color, -1, cv2.LINE_AA)
            cv2.circle(frame, pt, radius, (220, 220, 220), 1, cv2.LINE_AA)
