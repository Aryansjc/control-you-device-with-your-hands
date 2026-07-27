"""
Virtual Mouse — v4 (Fully Optimized & Bug-Fixed).

All known runtime bugs fixed:
  • Edge-triggered clicks (pinching fires 1 clean click, holding won't freeze cursor or multi-click)
  • Guaranteed drag release on hand pose change or hand exit
  • Non-blocking Win32 execution engine (never freezes camera/OpenCV loop)
  • One Euro Filter for smooth cursor positioning
  • Multi-platform live filter tuning (Arrow keys OR W/A/S/D keys)
"""

import sys
import time

import cv2
import numpy as np
import pyautogui

import config
from hand_tracker import HandTracker
from gesture_engine import GestureEngine, Gesture
from mouse_controller import MouseController, disable_console_quick_edit


# ════════════════════════════════════════════════════════
#  Overlay / HUD
# ════════════════════════════════════════════════════════

GESTURE_COLORS = {
    "NONE":         (100, 100, 100),
    "MOVE":         (0, 230, 118),
    "LEFT_CLICK":   (0, 195, 255),
    "RIGHT_CLICK":  (90, 90, 255),
    "DOUBLE_CLICK": (0, 215, 255),
    "SCROLL":       (200, 140, 255),
    "DRAG":         (255, 160, 50),
    "DRAG_END":     (100, 100, 100),
}

FINGER_NAMES = ["T", "I", "M", "R", "P"]


def draw_status_bar(frame, gesture_name, fps, paused, cursor_locked):
    """Semi-transparent top bar with gesture status, FPS, and lock icon."""
    h, w = frame.shape[:2]

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 52), (15, 15, 15), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    color = GESTURE_COLORS.get(gesture_name, (255, 255, 255))
    label = "PAUSED" if paused else gesture_name

    # Status dot
    cv2.circle(frame, (22, 26), 9, color, -1)
    cv2.circle(frame, (22, 26), 9, (200, 200, 200), 1, cv2.LINE_AA)

    # Gesture label
    cv2.putText(frame, label, (42, 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.62, (240, 240, 240), 1, cv2.LINE_AA)

    # Lock indicator
    if cursor_locked and not paused:
        cv2.putText(frame, "LOCKED", (42, 48),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 200), 1, cv2.LINE_AA)

    # Right side — FPS
    info = f"FPS {int(fps)}"
    ts = cv2.getTextSize(info, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)[0]
    cv2.putText(frame, info, (w - ts[0] - 14, 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (170, 230, 170), 1, cv2.LINE_AA)


def draw_finger_state(frame, fingers):
    """Show which fingers the system detects as UP (right side of frame)."""
    if fingers is None:
        return
    h, w = frame.shape[:2]
    x_start = w - 140
    y = 80

    overlay = frame.copy()
    cv2.rectangle(overlay, (x_start - 10, y - 20), (w - 5, y + 18), (15, 15, 15), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

    for i, (name, up) in enumerate(zip(FINGER_NAMES, fingers)):
        color = (0, 230, 118) if up else (70, 70, 70)
        cx = x_start + i * 26
        cv2.putText(frame, name, (cx, y + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
        if up:
            cv2.circle(frame, (cx + 5, y - 8), 4, color, -1, cv2.LINE_AA)


def draw_active_zone(frame, margin_x, margin_y):
    """Faint rectangle showing the active hand-tracking zone."""
    h, w = frame.shape[:2]
    cv2.rectangle(frame,
                  (margin_x, margin_y), (w - margin_x, h - margin_y),
                  (50, 50, 50), 1, cv2.LINE_AA)


def draw_gesture_feedback(frame, gesture, position, cursor_locked):
    """Visual ring / label on the hand for the active gesture."""
    if position is None or not isinstance(position, tuple):
        return
    x, y = position
    color = GESTURE_COLORS.get(gesture.name, (255, 255, 255))

    if cursor_locked:
        color = tuple(max(c // 2, 30) for c in color)

    if gesture == Gesture.MOVE:
        cv2.circle(frame, (x, y), 16, color, 2, cv2.LINE_AA)
        cv2.circle(frame, (x, y), 3, color, -1, cv2.LINE_AA)

    elif gesture == Gesture.LEFT_CLICK:
        cv2.circle(frame, (x, y), 26, color, 3, cv2.LINE_AA)
        cv2.putText(frame, "CLICK", (x + 32, y + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)

    elif gesture == Gesture.RIGHT_CLICK:
        cv2.circle(frame, (x, y), 26, color, 3, cv2.LINE_AA)
        cv2.putText(frame, "R-CLICK", (x + 32, y + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)

    elif gesture == Gesture.DOUBLE_CLICK:
        cv2.circle(frame, (x, y), 30, color, 3, cv2.LINE_AA)
        cv2.circle(frame, (x, y), 20, color, 2, cv2.LINE_AA)
        cv2.putText(frame, "DBL-CLICK", (x + 36, y + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)

    elif gesture == Gesture.SCROLL:
        cv2.arrowedLine(frame, (x, y + 22), (x, y - 22), color, 2, cv2.LINE_AA)
        cv2.putText(frame, "SCROLL", (x + 20, y + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

    elif gesture == Gesture.DRAG:
        cv2.circle(frame, (x, y), 22, color, -1, cv2.LINE_AA)
        cv2.circle(frame, (x, y), 22, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, "DRAG", (x + 28, y + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)


def draw_help_bar(frame):
    """Bottom bar with gesture cheat-sheet and keyboard shortcuts."""
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h - 72), (w, h), (15, 15, 15), -1)
    cv2.addWeighted(overlay, 0.72, frame, 0.28, 0, frame)

    lines = [
        "Index: MOVE  |  Idx+Mid pinch: CLICK  |  3 fingers: R-CLICK  |  Thumb+Idx pinch: DRAG",
        "Idx+Mid apart: SCROLL  |  Q: Quit  |  P: Pause  |  W/S/A/D: Tune filter",
    ]
    for i, line in enumerate(lines):
        cv2.putText(frame, line, (12, h - 46 + i * 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.36, (160, 160, 160), 1, cv2.LINE_AA)


# ════════════════════════════════════════════════════════
#  Main loop
# ════════════════════════════════════════════════════════

def main():
    # Disable Windows Console QuickEdit mode
    disable_console_quick_edit()

    # ── Banner ──────────────────────────────────────
    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║    VIRTUAL MOUSE v4 — Fully Optimized       ║")
    print("  ╠══════════════════════════════════════════════╣")
    print("  ║                                              ║")
    print("  ║  GESTURES                                    ║")
    print("  ║  ──────────────────────────────────────────  ║")
    print("  ║  ☝  Index only         → Move cursor         ║")
    print("  ║  ✌  Idx+Mid pinch      → Left click          ║")
    print("  ║  🤟 Idx+Mid+Ring (hold) → Right click        ║")
    print("  ║  ✌  Idx+Mid apart      → Scroll              ║")
    print("  ║  👌 Thumb+Idx pinch    → Drag & Drop         ║")
    print("  ║  ✌✌ Double pinch       → Double click        ║")
    print("  ║                                              ║")
    print("  ║  KEYS                                        ║")
    print("  ║  ──────────────────────────────────────────  ║")
    print("  ║  Q/Esc = Quit   P = Pause   W/S/A/D = Tune  ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()

    # ── Camera ──────────────────────────────────────
    print("  Starting camera...")
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)

    if not cap.isOpened():
        print("  ✗ ERROR: Could not open camera.")
        sys.exit(1)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    screen_w, screen_h = pyautogui.size()

    print(f"  Screen : {screen_w} × {screen_h}")
    print(f"  Camera : {actual_w} × {actual_h}")
    print()

    # ── Components ──────────────────────────────────
    tracker = HandTracker(
        max_hands=config.MAX_HANDS,
        detection_conf=config.DETECTION_CONFIDENCE,
        tracking_conf=config.TRACKING_CONFIDENCE,
    )

    gesture_engine = GestureEngine(
        click_distance=config.CLICK_DISTANCE,
        click_cooldown=config.CLICK_COOLDOWN,
        double_click_window=config.DOUBLE_CLICK_WINDOW,
        drag_threshold=config.DRAG_PINCH_THRESHOLD,
        scroll_cooldown=config.SCROLL_COOLDOWN,
        scroll_deadzone=config.SCROLL_DEADZONE,
        transition_freeze_frames=config.TRANSITION_FREEZE_FRAMES,
        right_click_confirm_frames=config.RIGHT_CLICK_CONFIRM_FRAMES,
        hysteresis_exit=config.HYSTERESIS_EXIT,
        hysteresis_enter_scroll=config.HYSTERESIS_ENTER_SCROLL,
        hysteresis_exit_scroll=config.HYSTERESIS_EXIT_SCROLL,
    )

    min_cutoff = config.FILTER_MIN_CUTOFF
    beta = config.FILTER_BETA
    mouse = MouseController(
        screen_w, screen_h,
        actual_w, actual_h,
        margin_x=config.FRAME_MARGIN_X,
        margin_y=config.FRAME_MARGIN_Y,
        screen_overshoot=config.SCREEN_OVERSHOOT,
        min_cutoff=min_cutoff,
        beta=beta,
        d_cutoff=config.FILTER_D_CUTOFF,
    )

    # ── State ───────────────────────────────────────
    paused = False
    drag_active = False
    prev_time = time.time()
    fps = 0.0
    current_fingers = None

    print("  ✓ Virtual Mouse v4 is ACTIVE!")
    print("  Move your hand in front of the camera.\n")

    # ── Loop ────────────────────────────────────────
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            frame = cv2.flip(frame, 1)  # Mirror frame

            # FPS
            now = time.time()
            fps = 1.0 / max(now - prev_time, 1e-6)
            prev_time = now

            gesture = Gesture.NONE
            gesture_pos = None
            cursor_locked = False

            if not paused:
                landmarks, handedness = tracker.find_hand(frame)

                if landmarks is not None:
                    tracker.draw(frame, landmarks)
                    positions = tracker.get_positions(landmarks, frame.shape)
                    fingers = tracker.get_fingers_up(positions, handedness)
                    current_fingers = fingers

                    gesture, data, cursor_locked = gesture_engine.recognize(
                        fingers, positions, tracker
                    )
                    gesture_pos = data

                    # ── Execute actions ────────────
                    if gesture == Gesture.MOVE:
                        if not cursor_locked:
                            mouse.move(*data)

                    elif gesture == Gesture.LEFT_CLICK:
                        mouse.click("left")

                    elif gesture == Gesture.RIGHT_CLICK:
                        mouse.click("right")

                    elif gesture == Gesture.DOUBLE_CLICK:
                        mouse.double_click()

                    elif gesture == Gesture.SCROLL:
                        if isinstance(data, (int, float)):
                            amt = int(data * config.SCROLL_SENSITIVITY / 10)
                            if abs(amt) > 0:
                                mouse.scroll(amt)

                    elif gesture == Gesture.DRAG:
                        if not drag_active:
                            mouse.start_drag()
                            drag_active = True
                        if not cursor_locked:
                            mouse.drag_move(*data)

                    elif gesture == Gesture.DRAG_END:
                        if drag_active:
                            mouse.end_drag()
                            drag_active = False

                else:
                    # No hand detected → end drag if active, reset finger state
                    current_fingers = None
                    if drag_active:
                        mouse.end_drag()
                        drag_active = False

            # ── Draw overlay ────────────────────────────
            draw_active_zone(frame, config.FRAME_MARGIN_X, config.FRAME_MARGIN_Y)
            draw_status_bar(frame, gesture.name, fps, paused, cursor_locked)
            draw_gesture_feedback(frame, gesture, gesture_pos, cursor_locked)
            if config.SHOW_FINGER_STATE:
                draw_finger_state(frame, current_fingers)
            if config.SHOW_HELP:
                draw_help_bar(frame)

            cv2.imshow(config.WINDOW_NAME, frame)

            # ── Key handling (supports ASCII + extended keycodes) ──
            raw_key = cv2.waitKeyEx(1)
            if raw_key == -1:
                continue

            key = raw_key & 0xFF
            char = chr(key).lower() if 0 <= key < 128 else ""

            if char in ("q", "\x1b"):  # Q or Esc
                break
            elif char == "p":
                paused = not paused
                print(f"  {'⏸ PAUSED' if paused else '▶ RESUMED'}")

            # Filter tuning via W/S/A/D or Arrow keys
            elif char == "w" or raw_key in (2490368, 0x260000, 38, 72):
                min_cutoff = min(min_cutoff + 0.2, 10.0)
                mouse.update_filter_params(min_cutoff, beta)
                print(f"  Filter: min_cutoff={min_cutoff:.1f}  beta={beta:.2f}")
            elif char == "s" or raw_key in (2621440, 0x280000, 40, 80):
                min_cutoff = max(min_cutoff - 0.2, 0.1)
                mouse.update_filter_params(min_cutoff, beta)
                print(f"  Filter: min_cutoff={min_cutoff:.1f}  beta={beta:.2f}")
            elif char == "d" or raw_key in (2555904, 0x270000, 39, 77):
                beta = min(beta + 0.1, 5.0)
                mouse.update_filter_params(min_cutoff, beta)
                print(f"  Filter: min_cutoff={min_cutoff:.1f}  beta={beta:.2f}")
            elif char == "a" or raw_key in (2424832, 0x250000, 37, 75):
                beta = max(beta - 0.1, 0.0)
                mouse.update_filter_params(min_cutoff, beta)
                print(f"  Filter: min_cutoff={min_cutoff:.1f}  beta={beta:.2f}")

    finally:
        # ── Cleanup ─────────────────────────────────────
        if drag_active:
            mouse.end_drag()
        mouse.stop()
        cap.release()
        cv2.destroyAllWindows()
        print("\n  Virtual Mouse stopped. Goodbye!\n")


if __name__ == "__main__":
    main()
