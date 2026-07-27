# 🖱️ AI Virtual Mouse — Gesture Control Engine

A high-performance, non-blocking, Python-based virtual mouse application that allows complete, hands-free computer control using your webcam and computer vision hand gestures.

Powered by **MediaPipe Tasks API**, **OpenCV**, and a **One Euro Filter** adaptive smoothing algorithm, this tool offers precise cursor positioning, edge-to-edge screen reachability, and clean gesture actions without latency or cursor freeze.

---

## ✨ Features

- **🎯 Adaptive Cursor Smoothing (One Euro Filter)**: Eliminates hand jitter when staying still while remaining hyper-responsive during fast movements.
- **⚡ Non-Blocking Multithreaded Engine**: Mouse operations (clicks, drags, moves) run on a dedicated worker thread using native **Win32 API**, ensuring the camera feed and gesture recognition never freeze.
- **🖥️ Screen Overshoot & Full-Edge Reachability**: Smart coordinate mapping makes reaching screen corners, title bars, and the Windows Taskbar effortless.
- **🔒 Edge-Triggered Pinch Gestures**: Pinch-to-click triggers exactly *one* clean click on contact, preventing click storms or cursor freezes while holding fingers together.
- **🧊 Finger-Transition Freeze**: Cursor locks briefly when transitioning between finger poses to prevent unintended cursor jumps.
- **📊 Real-time Overlay HUD**: Live visual feedback showing active gesture status, FPS, finger detection state (`T I M R P`), and active tracking zones.
- **⌨️ Live Filter Tuning**: Tune cursor smoothness and speed adaptation in real-time using keyboard shortcuts.

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

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Q` / `Esc` | Quit the application |
| `P` | Pause / Resume hand tracking |
| `W` / `Up Arrow` | Increase smoothing (`min_cutoff`) — reduces jitter |
| `S` / `Down Arrow` | Decrease smoothing (`min_cutoff`) — increases responsiveness |
| `D` / `Right Arrow` | Increase speed adaptation (`beta`) — reduces lag on fast swipes |
| `A` / `Left Arrow` | Decrease speed adaptation (`beta`) — extra smoothing during movement |

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- A working webcam

### 2. Installation

Clone or navigate to the project directory:

```bash
cd virtual_mouse
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

> **Note**: On first launch, the application will automatically download the lightweight MediaPipe `hand_landmarker.task` model file (~12 MB).

### 3. Running the Application

```bash
python main.py
```

---

## ⚙️ Configuration & Tuning

All sensitive thresholds and parameters can be easily adjusted in [`config.py`](config.py):

```python
# Active Tracking Zone Margins (px)
FRAME_MARGIN_X = 45
FRAME_MARGIN_Y = 30

# Screen Overshoot (px) — allows easy taskbar and screen-edge reachability
SCREEN_OVERSHOOT = 120

# One Euro Filter parameters
FILTER_MIN_CUTOFF = 1.8   # Base cutoff frequency (lower = smoother)
FILTER_BETA = 0.8         # Speed coefficient (higher = less lag)

# Gesture Distance Thresholds (px)
CLICK_DISTANCE = 38
DRAG_PINCH_THRESHOLD = 32
```

---

## 📁 Project Architecture

```
virtual_mouse/
├── main.py              # Main application loop, camera capture & HUD renderer
├── hand_tracker.py      # MediaPipe Tasks API hand landmark tracking & model loader
├── gesture_engine.py    # State-machine gesture classifier (hysteresis & edge triggers)
├── mouse_controller.py  # Threaded mouse engine, Win32 API wrapper & One Euro Filter
├── config.py            # Centralized settings and gesture thresholds
├── requirements.txt     # Dependency manifest
└── README.md            # Documentation
```

---

## 🛠️ Technical Details & Solved Edge Cases

- **Windows Console QuickEdit Fix**: Automatically disables QuickEdit mode in Windows Terminal/PowerShell to prevent accidental mouse clicks in the console from pausing Python execution.
- **MediaPipe Monotonic Timestamps**: Guarantees strictly increasing timestamp inputs for MediaPipe VIDEO mode to eliminate `ValueError` runtime exceptions.
- **Thread Safety**: Uses atomic locking for position updates and a thread-safe queue for discrete mouse actions to guarantee zero input latency and no queue backlog.
- **Guaranteed Drag Termination**: Implements emergency mouse-up release hooks on hand-pose transition, hand exit, and application shutdown.

---

## 📜 License

MIT License — Feel free to modify and use in your own projects!
