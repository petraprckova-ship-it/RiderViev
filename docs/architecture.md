# Architektura systému

## Přehled

Person Tracker je distribuovaný systém s:
- **Desktop aplikací** (řídicí stanice) - výkonný notebook s GPU
- **Robot service** (Raspberry Pi CM4) - embedded systém na robotu
- **Nízkolatentní síťová komunikace** - ZeroMQ pro real-time control

```
┌─────────────────────────────────────────────────────────────┐
│                    DESKTOP APLIKACE                         │
│                 (Python 3.11 + PyQt6)                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  UI Layer    │  │  ML Pipeline │  │  Control     │      │
│  │              │  │              │  │  System      │      │
│  │  PyQt6       │  │  YOLO11      │  │  PID         │      │
│  │  QML         │  │  ByteTrack   │  │  Navigation  │      │
│  │  Charts      │  │  Depth Est.  │  │  Safety      │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │               │
│         └─────────────────┴─────────────────┘               │
│                           │                                 │
│                    ┌──────┴───────┐                         │
│                    │   Network    │                         │
│                    │   Client     │                         │
│                    │   (ZeroMQ)   │                         │
│                    └──────┬───────┘                         │
└───────────────────────────┼─────────────────────────────────┘
                            │
                     WiFi / Ethernet
                     (TCP/IP)
                            │
┌───────────────────────────┼─────────────────────────────────┐
│                    ┌──────┴───────┐                         │
│                    │   Network    │                         │
│                    │   Server     │                         │
│                    │   (ZeroMQ)   │                         │
│                    └──────┬───────┘                         │
│                           │                                 │
│         ┌─────────────────┴─────────────────┐               │
│         │                                   │               │
│  ┌──────┴───────┐                  ┌────────┴─────┐        │
│  │   Hardware   │                  │    Video     │        │
│  │   Interface  │                  │   Streamer   │        │
│  │              │                  │              │        │
│  │  Motors      │                  │  GStreamer   │        │
│  │  IMU         │                  │  RTSP        │        │
│  │  Sensors     │                  │  H.264       │        │
│  └──────────────┘                  └──────────────┘        │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                  ROBOT SERVICE                              │
│             (Python 3.9 + Raspberry Pi)                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Komponenty

### Desktop aplikace

#### 1. **UI Layer** (`src/ui/`)

**Technologie:**
- PyQt6 - Core framework
- QML - Deklarativní UI
- QtCharts - Grafy
- OpenGL - Video rendering

**Komponenty:**
- `main_window.py` - Hlavní okno
- `control_panel.py` - Levý panel s ovládáním
- `video_display.py` - Střední panel s videem
- `telemetry_panel.py` - Pravý panel s telemetrií
- `dialogs/` - Dialogy (nastavení, about, atd.)
- `widgets/` - Custom widgety

**Odpovědnosti:**
- Zobrazení video streamu s overlays
- Real-time telemetrie a grafy
- Uživatelská interakce
- Konfigurace systému

#### 2. **ML Pipeline** (`src/ml/`)

**Komponenty:**

**`detector.py`** - YOLO11 person detection
- GPU-akcelerovaná inference (TensorRT/ONNX)
- Adaptivní přepínání modelů podle výkonu
- FP16 precision pro 2x speedup
- Batch processing support

**`tracker.py`** - ByteTrack multi-object tracking
- Kalman filter pro predikci
- Hungarian algorithm pro matching
- Track state machine (tentative/confirmed/lost)
- Target selection logic

**`distance.py`** - Distance estimation
- BBox-based estimation (pinhole model)
- Depth map estimation (Depth-Anything-V2)
- Sensor fusion
- Kalman filtering pro smoothing

**Datový tok:**
```
Frame → YOLO11 → Detections → ByteTrack → Tracks
                                              ↓
                                         Target Selection
                                              ↓
                                    Distance Estimation
                                              ↓
                                    Control Decision
```

#### 3. **Control System** (`src/control/`)

**`pid.py`** - PID regulátory
- Dual PID (lineární + angulární)
- Anti-windup
- Derivative filtering
- Velocity profiling (trapezoidal)
- Speed limiting

**`tracking.py`** - Tracking controller
- State machine (idle/searching/locked/lost)
- Zone-based safety (red/yellow/green)
- Obstacle avoidance
- Emergency stop handling

**Control loop:**
```
Target → Distance Error → PID → Velocity Profile → Speed Limit → Motors
         Position Error → PID ↗
```

**Frekvence:** 50 Hz (20ms update rate)

#### 4. **Network Layer** (`src/network/`)

**`client.py`** - ZeroMQ client
- REQ/REP pattern pro příkazy
- SUB pattern pro telemetrii
- Automatic reconnection
- Latency tracking
- Keepalive mechanism

**Protokoly:**
- Command port: 5555 (REQ/REP)
- Telemetry port: 5556 (PUB/SUB)

**Latence:** <5ms typicky, <10ms worst case

#### 5. **Configuration** (`src/config.py`)

- Pydantic models pro validaci
- YAML configuration files
- User overrides
- Profile management (robot connections)

---

### Robot Service

#### 1. **Hardware Interface** (`robot/robot_service.py`)

**Odpovědnosti:**
- Ovládání motorů (PWM)
- Čtení IMU (gyro, accelerometer)
- Ultrazvukové senzory
- Baterie monitoring
- Teplota monitoring

**Yahboom Rider Pi CM4 specifika:**
- Diferenciální řízení (2 motory)
- I2C komunikace s IMU
- GPIO pro senzory
- Hardware PWM pro motory

#### 2. **Network Server** (`robot/robot_service.py`)

**ZeroMQ patterns:**
- REP socket (command_port) - přijímá příkazy
- PUB socket (telemetry_port) - vysílá telemetrii

**Watchdog:**
- 500ms timeout
- Auto-stop při ztrátě spojení

**Telemetrie frequency:** 20 Hz

#### 3. **Video Streamer**

**GStreamer pipeline:**
```bash
libcamera-src → h264enc → rtspsink
```

**Parametry:**
- Codec: H.264
- Resolution: 640x480 @ 30 FPS
- Bitrate: 2-4 Mbps adaptive
- Latency: ~30-50ms glass-to-glass

---

## Komunikační protokoly

### Command Protocol (REQ/REP)

**Motion Command:**
```json
{
  "type": "motion_command",
  "linear_velocity": 0.5,
  "angular_velocity": 0.0,
  "timestamp": 1234567890,
  "command_id": "uuid"
}
```

**Response:**
```json
{
  "status": "ok",
  "timestamp": 1234567891
}
```

**Emergency Stop:**
```json
{
  "type": "emergency_stop",
  "reason": "User request",
  "timestamp": 1234567890
}
```

### Telemetry Protocol (PUB/SUB)

**Telemetry Message:**
```json
{
  "type": "telemetry",
  "timestamp": 1234567890,
  "linear_velocity": 0.5,
  "angular_velocity": 0.0,
  "pitch": 0.1,
  "roll": -0.05,
  "yaw": 1.57,
  "ultrasonic_front": 100.0,
  "ultrasonic_left": 80.0,
  "ultrasonic_right": 85.0,
  "ultrasonic_back": 120.0,
  "battery_percentage": 85.0,
  "battery_voltage": 12.0,
  "cpu_temperature": 45.0,
  "robot_state": "moving"
}
```

---

## Performance charakteristiky

### Latence breakdown

| Komponenta | Latence |
|------------|---------|
| Frame capture | 5-10ms |
| YOLO inference | 10-15ms (TensorRT) |
| Tracking update | 2ms |
| Control compute | 1ms |
| Network (command) | 1-5ms |
| Motor response | 10-20ms |
| **Total** | **30-53ms** |

**Target:** <100ms end-to-end ✓

### Propustnost

| Metrika | Hodnota |
|---------|---------|
| Video FPS | 30 |
| Detection FPS | 25-30 (adaptivní) |
| Control loop | 50 Hz |
| Telemetry | 20 Hz |
| Network bandwidth | 2-4 Mbps |

### GPU využití

| Model | Inference time | FPS | VRAM |
|-------|---------------|-----|------|
| YOLO11-nano | 5ms | 200 | 1GB |
| YOLO11-small | 10ms | 100 | 2GB |
| YOLO11-medium | 20ms | 50 | 4GB |

**Doporučeno:** YOLO11-small na RTX 3060

---

## Bezpečnostní mechanismy

### 1. Watchdog Timer
- **Timeout:** 500ms
- **Akce:** Emergency stop motorů
- **Reset:** Každý příkaz resetuje timer

### 2. Safety Zones
- **Red (<30cm):** Okamžité zastavení
- **Yellow (30-60cm):** Zpomalení
- **Green (>60cm):** Normální provoz

### 3. Emergency Stop
- **Trigger:** Space, Obstacle, Connection lost
- **Akce:** Motors = 0, State = EMERGENCY_STOP
- **Recovery:** Manuální resume

### 4. Network Redundancy
- **Auto-reconnect:** Exponential backoff (5s, 10s, 20s, 30s max)
- **Connection monitor:** Ping každou sekundu
- **Timeout detection:** No telemetry >3s

### 5. Battery Protection
- **Low battery (<20%):** Warning
- **Critical battery (<10%):** Auto-return-home (TBD)

---

## Rozšiřitelnost

### Custom ML modely

1. Train YOLO11-compatible model
2. Export to TensorRT/ONNX
3. Replace model in `models/`
4. Update config

### Custom Control algoritmy

```python
from src.control.tracking import PersonTrackingController

class CustomController(PersonTrackingController):
    def _compute_tracking_commands(self, target, distance, dt):
        # Custom logic
        return linear_cmd, angular_cmd
```

### Plugins (TBD)

- Gesture recognition
- Voice commands
- Path recording/replay
- Multi-robot coordination

---

## Deployment

### Desktop

```
Desktop App Package:
├── main.py (entry point)
├── src/ (Python modules)
├── config/ (YAML configs)
├── models/ (ML models)
├── venv/ (Python environment)
└── docs/ (Documentation)
```

**Distribution:** PyInstaller bundle (TBD)

### Robot

```
Robot Service:
├── /opt/person-tracker/
│   ├── robot_service.py
│   └── venv/
├── /etc/systemd/system/
│   └── person-tracker.service
└── /var/log/person-tracker/
    └── robot_*.log
```

**Distribution:** Debian package (TBD)

---

## Monitoring & Debugging

### Logging

**Desktop:**
- Console: INFO level, colored
- File: ~/.person_tracker/logs/person_tracker_YYYY-MM-DD.log
- Rotation: Daily, 7 days retention

**Robot:**
- Console: INFO level
- File: /var/log/person-tracker/robot_YYYY-MM-DD.log
- systemd journal: `journalctl -u person-tracker -f`

### Metrics

**Desktop UI:**
- FPS counter
- Latency graph
- Network quality
- GPU utilization

**Telemetry:**
- Battery level
- CPU temperature
- Motor RPM
- Sensor readings

### Profiling

```bash
# CPU profiling
python -m cProfile -o profile.stats main.py
snakeviz profile.stats

# GPU profiling
nvprof python main.py

# Memory profiling
mprof run main.py
mprof plot
```

---

## Budoucí vylepšení

### Krátké období (1-3 měsíce)

- [ ] Complete UI implementation (widgets)
- [ ] Video streaming (GStreamer integration)
- [ ] Real Yahboom hardware support
- [ ] Calibration tools
- [ ] Recording/playback

### Střední období (3-6 měsíců)

- [ ] Depth estimation integration
- [ ] Obstacle avoidance (VFH)
- [ ] Geofencing
- [ ] Multi-person tracking
- [ ] Gesture recognition

### Dlouhé období (6-12 měsíců)

- [ ] Multi-robot support
- [ ] Cloud telemetry
- [ ] Mobile app (iOS/Android)
- [ ] AI voice commands
- [ ] SLAM/mapping

---

## Reference

- [Ultralytics YOLO11](https://docs.ultralytics.com/)
- [ByteTrack paper](https://arxiv.org/abs/2110.06864)
- [Depth-Anything-V2](https://github.com/DepthAnything/Depth-Anything-V2)
- [ZeroMQ Guide](https://zguide.zeromq.org/)
- [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [Yahboom Rider Pi](https://www.yahboom.net/)
