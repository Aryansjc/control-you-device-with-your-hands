"""
Configuration constants for the Virtual Mouse.
Tweak these values to adjust sensitivity, smoothing, and gesture thresholds.
"""

# ─── Camera ──────────────────────────────────────────────
CAMERA_INDEX = 0            # Default webcam
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# ─── Hand Detection (MediaPipe) ──────────────────────────
MAX_HANDS = 1
DETECTION_CONFIDENCE = 0.8
TRACKING_CONFIDENCE = 0.8

# ─── One Euro Filter (adaptive cursor smoothing) ────────
# min_cutoff: base smoothing. Lower = smoother at rest, higher = more responsive.
# beta:       speed adaptation. Higher = less lag on fast swipes.
# d_cutoff:   derivative filter cutoff.
FILTER_MIN_CUTOFF = 1.8
FILTER_BETA = 0.8
FILTER_D_CUTOFF = 1.0

# ─── Active Area Margins ────────────────────────────────
# Pixels inward from each frame edge.  Smaller = more sensitive / usable area.
FRAME_MARGIN_X = 45
FRAME_MARGIN_Y = 30

# ─── Screen Overshoot ───────────────────────────────────
# Extra pixels BEYOND the screen edges in the mapping target.
# This makes it easy to push the cursor all the way to the taskbar,
# title bars, and screen edges — the final position is clamped to
# valid screen coordinates.  Higher = easier to reach edges.
SCREEN_OVERSHOOT = 120

# ─── Gesture Thresholds ────────────────────────────────
CLICK_DISTANCE = 38         # Max distance (px) between index+middle tips for click
CLICK_COOLDOWN = 0.28       # Min seconds between separate click actions
DOUBLE_CLICK_WINDOW = 0.40  # Max seconds between two clicks to trigger double-click
DRAG_PINCH_THRESHOLD = 32   # Max thumb–index distance (px) to start drag

# ─── Hysteresis ─────────────────────────────────────────
# Prevents flickering between click and scroll when fingertip distance hovers near threshold.
HYSTERESIS_EXIT = 1.5
HYSTERESIS_ENTER_SCROLL = 1.15
HYSTERESIS_EXIT_SCROLL = 0.65

# ─── Finger Transition Freeze ───────────────────────────
# When any finger's up/down state changes, freeze cursor movement for
# this many frames to prevent cursor jumps caused by hand movement mechanics.
TRANSITION_FREEZE_FRAMES = 3

# ─── Scroll ─────────────────────────────────────────────
SCROLL_SENSITIVITY = 8      # Multiplier for scroll amount
SCROLL_COOLDOWN = 0.02      # Seconds between scroll updates
SCROLL_DEADZONE = 2         # Minimum pixel delta to register a scroll

# ─── Right-Click Stability ──────────────────────────────
# Require three-finger gesture for this many consecutive frames
# before firing a right-click.
RIGHT_CLICK_CONFIRM_FRAMES = 3

# ─── Display ─────────────────────────────────────────────
WINDOW_NAME = "Virtual Mouse"
SHOW_FPS = True
SHOW_HELP = True
SHOW_FINGER_STATE = True    # Show detected finger states on overlay
