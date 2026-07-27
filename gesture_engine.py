"""
Gesture recognition engine — v3 (Edge-triggered & bug-fixed).

Fixes:
  • Clicks are strictly EDGE-TRIGGERED: pinching fires 1 click on contact.
    Holding the pinch does NOT cause rapid multi-clicking or freeze cursor.
  • Drag termination is GUARANTEED whenever hand pose changes or leaves frame.
  • Right-click is edge-triggered after hold confirmation.
  • Transition freeze locks cursor during pose changes.
"""

import time
from enum import Enum, auto


class Gesture(Enum):
    NONE = auto()
    MOVE = auto()
    LEFT_CLICK = auto()
    RIGHT_CLICK = auto()
    DOUBLE_CLICK = auto()
    SCROLL = auto()
    DRAG = auto()
    DRAG_END = auto()


class GestureEngine:
    """Stateful gesture recogniser with edge-triggered actions and robust drag tracking."""

    def __init__(
        self,
        click_distance=38,
        click_cooldown=0.28,
        double_click_window=0.40,
        drag_threshold=32,
        scroll_cooldown=0.02,
        scroll_deadzone=2,
        transition_freeze_frames=3,
        right_click_confirm_frames=3,
        hysteresis_exit=1.5,
        hysteresis_enter_scroll=1.15,
        hysteresis_exit_scroll=0.65,
    ):
        self.click_distance = click_distance
        self.click_cooldown = click_cooldown
        self.double_click_window = double_click_window
        self.drag_threshold = drag_threshold
        self.scroll_cooldown = scroll_cooldown
        self.scroll_deadzone = scroll_deadzone
        self.transition_freeze_frames = transition_freeze_frames
        self.right_click_confirm_frames = right_click_confirm_frames
        self.hysteresis_exit = hysteresis_exit
        self.hysteresis_enter_scroll = hysteresis_enter_scroll
        self.hysteresis_exit_scroll = hysteresis_exit_scroll

        # State tracking
        self._last_click_time = 0.0
        self._last_rclick_time = 0.0
        self._last_scroll_time = 0.0
        self._prev_scroll_y = None
        self._is_dragging = False

        # Edge-trigger states (prevents holding pinch from re-triggering clicks)
        self._left_pinch_active = False
        self._right_pose_active = False

        # Transition freeze
        self._prev_finger_state = None
        self._freeze_countdown = 0

        # Sub-mode hysteresis for two-finger gesture
        self._two_finger_mode = None

        # Right-click counter
        self._rclick_consecutive = 0

        # Double-click tracker
        self._click_timestamps: list[float] = []

    def recognize(self, fingers, positions, tracker):
        """
        Recognise hand gesture.

        Returns
        -------
        (Gesture, data, cursor_locked : bool)
        """
        # ── 0. Transition freeze ─────────────────────
        finger_state = tuple(bool(f) for f in fingers)
        cursor_locked = False

        if self._prev_finger_state is not None and finger_state != self._prev_finger_state:
            self._freeze_countdown = self.transition_freeze_frames

        self._prev_finger_state = finger_state

        if self._freeze_countdown > 0:
            self._freeze_countdown -= 1
            cursor_locked = True

        thumb, index, middle, ring, pinky = fingers
        now = time.time()

        idx_mid_dist, _ = tracker.distance(positions, 8, 12)
        thumb_idx_dist, _ = tracker.distance(positions, 4, 8)

        # ── 1. MOVE / DRAG (index only up) ────────────
        if index and not middle and not ring and not pinky:
            self._two_finger_mode = None
            self._prev_scroll_y = None
            self._rclick_consecutive = 0
            self._left_pinch_active = False
            self._right_pose_active = False

            # Check DRAG (thumb-index pinch)
            if thumb_idx_dist < self.drag_threshold:
                if not self._is_dragging:
                    self._is_dragging = True
                return Gesture.DRAG, positions[8], cursor_locked

            # Released drag
            if self._is_dragging:
                self._is_dragging = False
                return Gesture.DRAG_END, positions[8], cursor_locked

            return Gesture.MOVE, positions[8], cursor_locked

        # If we were dragging and fingers changed to anything else, terminate drag first
        if self._is_dragging:
            self._is_dragging = False
            return Gesture.DRAG_END, positions[8], cursor_locked

        # ── 2. LEFT CLICK / SCROLL (index + middle) ────
        if index and middle and not ring and not pinky:
            self._right_pose_active = False
            self._rclick_consecutive = 0

            # Hysteresis mode decision
            if self._two_finger_mode == "click":
                if idx_mid_dist > self.click_distance * self.hysteresis_exit:
                    self._two_finger_mode = "scroll"
                    self._prev_scroll_y = None
            elif self._two_finger_mode == "scroll":
                if idx_mid_dist < self.click_distance * self.hysteresis_exit_scroll:
                    self._two_finger_mode = "click"
            else:
                if idx_mid_dist < self.click_distance:
                    self._two_finger_mode = "click"
                elif idx_mid_dist > self.click_distance * self.hysteresis_enter_scroll:
                    self._two_finger_mode = "scroll"
                else:
                    return Gesture.NONE, None, cursor_locked

            # LEFT CLICK (Edge-triggered)
            if self._two_finger_mode == "click":
                self._prev_scroll_y = None
                if not self._left_pinch_active:
                    self._left_pinch_active = True
                    if now - self._last_click_time > self.click_cooldown:
                        self._last_click_time = now

                        # Double-click check
                        self._click_timestamps = [
                            t for t in self._click_timestamps
                            if now - t < self.double_click_window
                        ]
                        self._click_timestamps.append(now)

                        if len(self._click_timestamps) >= 2:
                            self._click_timestamps.clear()
                            return Gesture.DOUBLE_CLICK, positions[8], cursor_locked

                        return Gesture.LEFT_CLICK, positions[8], cursor_locked
                # While holding pinch, continue moving/holding without re-clicking
                return Gesture.NONE, None, cursor_locked

            # Fingers opened up → reset pinch active
            self._left_pinch_active = False

            # SCROLL (uses wrist landmark 0)
            if self._two_finger_mode == "scroll":
                scroll_y = positions[0][1]
                if self._prev_scroll_y is not None:
                    if now - self._last_scroll_time > self.scroll_cooldown:
                        dy = self._prev_scroll_y - scroll_y  # up = positive
                        self._prev_scroll_y = scroll_y
                        if abs(dy) >= self.scroll_deadzone:
                            self._last_scroll_time = now
                            return Gesture.SCROLL, dy, cursor_locked
                else:
                    self._prev_scroll_y = scroll_y
                return Gesture.NONE, None, cursor_locked

        # Reset pinch active when leaving two-finger pose
        self._left_pinch_active = False
        self._two_finger_mode = None
        self._prev_scroll_y = None

        # ── 3. RIGHT CLICK (index + middle + ring) ────
        if index and middle and ring and not pinky:
            self._rclick_consecutive += 1
            if (
                self._rclick_consecutive >= self.right_click_confirm_frames
                and not self._right_pose_active
                and now - self._last_rclick_time > self.click_cooldown
            ):
                self._right_pose_active = True
                self._last_rclick_time = now
                self._rclick_consecutive = 0
                return Gesture.RIGHT_CLICK, positions[8], cursor_locked
            return Gesture.NONE, None, cursor_locked

        # Reset right click pose when leaving 3-finger pose
        self._right_pose_active = False
        self._rclick_consecutive = 0

        return Gesture.NONE, None, cursor_locked

    @property
    def is_dragging(self):
        return self._is_dragging
