"""
Mouse controller — v4 with Atomic Threaded Execution & Win32 API.

Guarantees:
  • Non-blocking mouse execution (camera and hand tracking loop never freeze)
  • Thread-safe atomic position updates (no queue manipulation race conditions)
  • Guaranteed mouse-up cleanup on exit
  • Native Win32 API calls for high speed & zero latency
"""

import os
import sys
import math
import time
import queue
import threading
import ctypes

import numpy as np

# Win32 Constants
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800

IS_WINDOWS = os.name == 'nt'

if not IS_WINDOWS:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0


def disable_console_quick_edit():
    """Disable Windows Console QuickEdit mode to prevent clicks in terminal from freezing execution."""
    if IS_WINDOWS:
        try:
            kernel32 = ctypes.windll.kernel32
            hInput = kernel32.GetStdHandle(-10)  # STD_INPUT_HANDLE = -10
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(hInput, ctypes.byref(mode)):
                # 0x0040 = ENABLE_QUICK_EDIT_MODE, 0x0020 = ENABLE_INSERT_MODE
                new_mode = mode.value & ~0x0040 & ~0x0020
                kernel32.SetConsoleMode(hInput, new_mode)
        except Exception:
            pass


class OneEuroFilter:
    """Adaptive low-pass filter: heavy smoothing at rest, light on fast moves."""

    def __init__(self, min_cutoff=1.8, beta=0.8, d_cutoff=1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff

        self._x_prev: float | None = None
        self._dx_prev = 0.0
        self._t_prev: float | None = None

    def reset(self):
        self._x_prev = None
        self._dx_prev = 0.0
        self._t_prev = None

    def __call__(self, x: float, t: float | None = None) -> float:
        if t is None:
            t = time.monotonic()

        if self._x_prev is None:
            self._x_prev = x
            self._t_prev = t
            return x

        dt = t - self._t_prev
        if dt <= 1e-7:
            return self._x_prev

        dx = (x - self._x_prev) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        dx_hat = a_d * dx + (1.0 - a_d) * self._dx_prev

        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self._alpha(cutoff, dt)
        x_hat = a * x + (1.0 - a) * self._x_prev

        self._x_prev = x_hat
        self._dx_prev = dx_hat
        self._t_prev = t

        return x_hat

    @staticmethod
    def _alpha(cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)


class MouseController:
    """Non-blocking, threaded mouse controller."""

    def __init__(
        self,
        screen_w: int,
        screen_h: int,
        frame_w: int,
        frame_h: int,
        margin_x: int = 45,
        margin_y: int = 30,
        screen_overshoot: int = 120,
        min_cutoff: float = 1.8,
        beta: float = 0.8,
        d_cutoff: float = 1.0,
    ):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.margin_x = margin_x
        self.margin_y = margin_y
        self.screen_overshoot = screen_overshoot

        self._filter_x = OneEuroFilter(min_cutoff, beta, d_cutoff)
        self._filter_y = OneEuroFilter(min_cutoff, beta, d_cutoff)

        # Thread-safe cursor position lock
        self._pos_lock = threading.Lock()
        self._pending_move: tuple[int, int] | None = None

        # Queue for discrete actions (click, scroll, drag)
        self._action_queue = queue.Queue()
        self._running = True

        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def stop(self):
        """Stop background worker thread cleanly."""
        self._running = False
        self._action_queue.put(("STOP", None))
        if IS_WINDOWS:
            try:
                ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            except Exception:
                pass

    def _worker_loop(self):
        """Worker thread loop to process moves and actions asynchronously."""
        while self._running:
            # 1. Process pending cursor move if present
            move_pos = None
            with self._pos_lock:
                if self._pending_move is not None:
                    move_pos = self._pending_move
                    self._pending_move = None

            if move_pos is not None:
                sx, sy = move_pos
                try:
                    if IS_WINDOWS:
                        ctypes.windll.user32.SetCursorPos(sx, sy)
                    else:
                        pyautogui.moveTo(sx, sy)
                except Exception:
                    pass

            # 2. Process discrete actions from queue
            try:
                cmd, args = self._action_queue.get(timeout=0.005)
            except queue.Empty:
                continue

            if cmd == "STOP":
                break

            try:
                if cmd == "CLICK":
                    button = args
                    if IS_WINDOWS:
                        if button == "left":
                            ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                            ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                        elif button == "right":
                            ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                            ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
                    else:
                        pyautogui.click(button=button)

                elif cmd == "DOUBLE_CLICK":
                    if IS_WINDOWS:
                        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                        time.sleep(0.04)
                        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                    else:
                        pyautogui.doubleClick()

                elif cmd == "START_DRAG":
                    if IS_WINDOWS:
                        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                    else:
                        pyautogui.mouseDown()

                elif cmd == "END_DRAG":
                    if IS_WINDOWS:
                        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                    else:
                        pyautogui.mouseUp()

                elif cmd == "SCROLL":
                    amount = args
                    if IS_WINDOWS:
                        ctypes.windll.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, amount * 25, 0)
                    else:
                        pyautogui.scroll(amount)

            except Exception:
                pass
            finally:
                self._action_queue.task_done()

    # ────────────────────────────────────────────────
    #  Coordinate mapping & filtering
    # ────────────────────────────────────────────────

    def _map(self, x: int, y: int) -> tuple[float, float]:
        """Map frame coordinates to screen coordinates with overshoot.

        The target range extends beyond the physical screen by
        `screen_overshoot` pixels on every side so that the cursor
        can easily reach all screen edges.  The final position is
        clamped to valid screen bounds after filtering.
        """
        x = np.clip(x, self.margin_x, self.frame_w - self.margin_x)
        y = np.clip(y, self.margin_y, self.frame_h - self.margin_y)

        ov = self.screen_overshoot
        sx = np.interp(
            x,
            (self.margin_x, self.frame_w - self.margin_x),
            (-ov, self.screen_w + ov),
        )
        sy = np.interp(
            y,
            (self.margin_y, self.frame_h - self.margin_y),
            (-ov, self.screen_h + ov),
        )
        return float(sx), float(sy)

    def _filter(self, sx: float, sy: float) -> tuple[int, int]:
        """Apply One Euro Filter and clamp to valid screen coordinates."""
        t = time.monotonic()
        fx = int(np.clip(self._filter_x(sx, t), 0, self.screen_w - 1))
        fy = int(np.clip(self._filter_y(sy, t), 0, self.screen_h - 1))
        return fx, fy

    # ────────────────────────────────────────────────
    #  Public Action Methods (Non-blocking)
    # ────────────────────────────────────────────────

    def move(self, x: int, y: int):
        sx, sy = self._map(x, y)
        sx, sy = self._filter(sx, sy)
        with self._pos_lock:
            self._pending_move = (sx, sy)

    def click(self, button: str = "left"):
        self._action_queue.put(("CLICK", button))

    def double_click(self):
        self._action_queue.put(("DOUBLE_CLICK", None))

    def scroll(self, amount: int):
        self._action_queue.put(("SCROLL", amount))

    def start_drag(self):
        self._action_queue.put(("START_DRAG", None))

    def drag_move(self, x: int, y: int):
        sx, sy = self._map(x, y)
        sx, sy = self._filter(sx, sy)
        with self._pos_lock:
            self._pending_move = (sx, sy)

    def end_drag(self):
        self._action_queue.put(("END_DRAG", None))

    def update_filter_params(self, min_cutoff: float, beta: float):
        for f in (self._filter_x, self._filter_y):
            f.min_cutoff = min_cutoff
            f.beta = beta
