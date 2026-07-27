# 🖱️ Control Your Device With Your Hands — Gesture Control Engine

A high-performance, non-blocking Python application that provides full computer mouse control using a webcam and computer vision hand gestures.

Powered by the MediaPipe Tasks API, OpenCV, and a One Euro Filter adaptive smoothing algorithm, this tool offers precise cursor positioning, screen-edge reachability, and reliable gesture actions without cursor freeze or input latency.

---

## Features

- **Adaptive Cursor Smoothing**: Uses a One Euro Filter to eliminate hand jitter when still while staying responsive during fast movements.
- **Multithreaded Mouse Engine**: Mouse operations (clicks, drags, moves) run on a background worker thread. Uses native Win32 API on Windows and PyAutoGUI fallback on macOS/Linux so the camera feed never freezes.
- **Screen Overshoot & Edge Reachability**: Coordinate mapping extends beyond physical frame bounds, making it easy to reach taskbars, title bars, and screen corners.
- **Edge-Triggered Pinch Gestures**: Pinching fires a single clean click on contact, preventing click storms or cursor locks while holding fingers together.
- **Finger-Transition Freeze**: Cursor locks briefly when changing finger poses to prevent unintended cursor jumps.
- **Real-time HUD Overlay**: Visual feedback showing gesture status, FPS, finger detection states (`T I M R P`), and active tracking boundaries.
- **Live Filter Tuning**: Tune cursor smoothness and speed adaptation in real-time via keyboard shortcuts.

---

## ✋ Hand Gesture Controls

| Gesture | Finger Pose | Action | Details |
| :--- | :--- | :--- | :--- |
| ☝️ **Move Cursor** | Index finger extended | **Move** | Smooth cursor navigation across the full screen |
| ✌️ **Left Click** | Index + Middle tips **pinched together** | **Left Click** | Edge-triggered single left click |
| ✌️✌️ **Double Click** | Two quick index + middle pinches | **Double Click** | Double left-click within `0.40s` window |
| 🤟 **Right Click** | Index + Middle + Ring fingers extended | **Right Click** | Edge-triggered after 3 confirmation frames |
| ✌️ **Scroll** | Index + Middle extended **apart** | **Scroll** | Move hand up/down to scroll (tracked via wrist) |
| 👌 **Drag & Drop** | Index extended + **Thumb pinched to Index tip** | **Drag & Drop** | Holds left click down until pinch is released |

---

## Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Q` / `Esc` | Quit the application |
| `P` | Pause / Resume hand tracking |
| `W` / `Up Arrow` | Increase smoothing (`min_cutoff`) - reduces jitter |
| `S` / `Down Arrow` | Decrease smoothing (`min_cutoff`) - increases responsiveness |
| `D` / `Right Arrow` | Increase speed adaptation (`beta`) - reduces lag on fast moves |
| `A` / `Left Arrow` | Decrease speed adaptation (`beta`) - extra smoothing during movement |

---

## Installation & Setup

### System Requirements
- Python 3.10 or higher
- A working webcam

---

### Operating System Specific Setup

#### 1. Windows

1. Clone or navigate to the project directory:
   ```cmd
   cd virtual_mouse
   ```
2. Install Python dependencies:
   ```cmd
   python -m pip install -r requirements.txt
   ```
3. Run the application:
   ```cmd
   python main.py
   ```

*Note for Windows users: The application automatically disables Console QuickEdit mode to prevent terminal text selection from pausing execution on mouse clicks.*

---

#### 2. macOS

1. Navigate to the project directory:
   ```bash
   cd virtual_mouse
   ```
2. Install Python dependencies:
   ```bash
   python3 -m pip install -r requirements.txt
   ```
3. **Grant System Permissions**:
   PyAutoGUI requires Accessibility permissions to control the mouse cursor on macOS.
   - Go to **System Settings** -> **Privacy & Security** -> **Accessibility**.
   - Enable your terminal application (e.g., Terminal, iTerm2, or VS Code).
   - Go to **System Settings** -> **Privacy & Security** -> **Camera** and grant camera access to your terminal.
4. Run the application:
   ```bash
   python3 main.py
   ```

---

#### 3. Linux (Debian / Ubuntu / Fedora)

1. Install system dependencies required by OpenCV and PyAutoGUI:
   - **Debian / Ubuntu**:
     ```bash
     sudo apt update
     sudo apt install -y python3-pip python3-tk python3-dev libgl1-mesa-glx scrot xclip
     ```
   - **Fedora**:
     ```bash
     sudo dnf install -y python3-pip python3-tkinter python3-devel mesa-libGL scrot xclip
     ```
2. Navigate to the project directory:
   ```bash
   cd virtual_mouse
   ```
3. Install Python dependencies:
   ```bash
   python3 -m pip install -r requirements.txt
   ```
4. Run the application:
   ```bash
   python3 main.py
   ```

*Note for Linux users: Ensure you are running under an X11 session or an XWayland-compatible display server for PyAutoGUI cursor control.*

---

## Configuration & Tuning

All gesture thresholds and smoothing parameters can be adjusted in `config.py`:

```python
# Active Tracking Zone Margins (pixels)
FRAME_MARGIN_X = 45
FRAME_MARGIN_Y = 30

# Screen Overshoot (pixels) - allows easy reachability to all screen edges
SCREEN_OVERSHOOT = 120

# One Euro Filter parameters
FILTER_MIN_CUTOFF = 1.8   # Base cutoff frequency (lower = smoother)
FILTER_BETA = 0.8         # Speed coefficient (higher = less lag)

# Gesture Distance Thresholds (pixels)
CLICK_DISTANCE = 38
DRAG_PINCH_THRESHOLD = 32
```

---

## Project Structure

```
virtual_mouse/
├── main.py              # Main application loop, camera capture & HUD renderer
├── hand_tracker.py      # MediaPipe Tasks API hand landmarker tracking & model loader
├── gesture_engine.py    # State-machine gesture classifier (hysteresis & edge triggers)
├── mouse_controller.py  # Threaded mouse engine, Win32/PyAutoGUI wrapper & One Euro Filter
├── config.py            # Centralized settings and gesture thresholds
├── requirements.txt     # Dependency manifest
└── README.md            # Documentation
```

---

## Troubleshooting

- **Model Download Error**: On first launch, the app downloads `hand_landmarker.task` (~12 MB). If the download fails due to network issues, download it manually from Google MediaPipe storage and place it in the project root directory.
- **Webcam Access Issues**: Ensure no other application (Zoom, Teams, Skype) is currently capturing the camera.
- **Mac Cursor Not Moving**: Verify Accessibility permissions under System Settings -> Privacy & Security -> Accessibility for your Terminal app.

---

## 📜 License

MIT License — Feel free to modify and use in your own projects!
