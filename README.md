# AURALIS — Women Safety & Threat Monitoring Command Center

AURALIS is a comprehensive, real-time safety monitoring system that fuses speech distress, physical motion anomalies, and environmental context. It coordinates an **on-device/server-fusion pipeline** to estimate situational threat levels from SAFE to CRITICAL.

The system is structured as two key components:
1. **Hardened Android Mobile Client (`mobile/`)**: A native React Native CLI Android application that collects IMU sensor telemetry (accelerometer + gyroscope) and audio amplitude/pitch metrics in the background. It is hardened against tampering, reverse engineering, and data leaks.
2. **Dynamic Fusion API Server (`backend/`)**: A Flask + Supabase backend server that runs gait/motion anomaly detection against user-calibrated walking baselines, filters audio through a four-layer voice activity and distress pipeline, evaluates context risks, and triggers automated SOS notifications.

---

## Project Architecture

```
AURALIS/
├── backend/                          # REST API and threat processing engine
│   ├── api/                          # Flask endpoints and authentication routes
│   │   ├── server_backend.py         # Main Flask API coordinator
│   │   ├── google_oauth.py           # OAuth identity verification
│   │   └── wsgi.py                   # Production server entry point
│   ├── database/                     # Supabase database operations manager
│   │   └── database.py
│   ├── src/                          # Signal processing & analysis modules
│   │   ├── motion_detection/         # gait profiling and anomaly detection
│   │   ├── speech_analysis/          # VAD & environment-adaptive audio engine
│   │   ├── threat_assessment/        # stateful threat fusion & override logic
│   │   └── context_engine/           # dynamic context weight adaptation
│   ├── templates/                    # Server-rendered templates
│   │   └── admin.html                # Admin supervision dashboard
│   ├── static/                       # Admin console styling and scripts
│   └── run.sh                        # Backend environment startup utility
│
├── mobile/                           # Hardened React Native CLI Android App
│   ├── android/                      # Native Kotlin and Gradle settings
│   ├── src/                          # Secure UI screens, navigation, and state
│   ├── package.json                  # React Native dependencies
│   └── App.tsx                       # Root component with security check gates
│
├── run.sh                            # Root convenience launcher (delegates to backend)
├── README.md                         # Main command center documentation
├── Research_paper_Final.pdf          # Research paper (final PDF)
└── Research_paper_Final.txt          # Research paper (source text)
```

---

## Core Features

### 1. Hardened React Native Android App (`mobile/`)
* **Background Sensor Monitoring**: Collects accelerometer and gyroscope data at 50Hz and mic amplitude levels without battery-draining visual streams.
* **Onboarding & Calibration**: Guides users through a 30-second walking baseline calibration to adjust thresholds to their individual movement signatures.
* **Anti-Tampering & Integrity Module**: Runs a native Kotlin root trust validator before loading, checking for `su` binaries, root apps, emulators, active debuggers, and packaging signature pinning.
* **Hardware-Backed Cryptography**: Stores JWT session tokens, host API endpoints, and user credentials inside the encrypted Android Keystore via the Keychain API instead of plaintext storage.
* **Logcat Sanitization**: Strips console log buffers during production compilation to prevent leakage of coordinates, motion signatures, or tokens over USB debugging.

### 2. Multi-Layer Audio Distress Pipeline
* **Layer 1: Noise Classification**: Categorizes ambient noise (Quiet, Street, Crowd, Transport) to adjust the detection threshold.
* **Layer 2: Voice Activity Gate**: Autocorrelates pitch coordinates, filtering out ambient machine hums or wind noise, only analyzing sounds inside the human vocal frequency (85Hz-255Hz).
* **Layer 3: Distress Classifier**: Extracts ZCR, pitch variance, spectral contrast, and 13-coefficient MFCC vectors to estimate distress probabilities via SVM or YAMNet.
* **Layer 4: Adaptive Threshold**: Dynamically increases alerting requirements in noisy transits while maintaining high sensitivity in quiet environments.

### 3. Stateful Sensor Fusion & Override Logic
* **Dynamic Weight Context**: Adjusts sensor contribution based on situational risk (e.g. night hours, isolated locations, low crowd presence).
* **Critical Event Overrides**: Instantly bypasses temporal exponential moving average (EMA) smoothing when high-risk events coordinate (e.g. `FALL` + vocal distress immediately triggers `CRITICAL`).
* **Emergency Workflows**: Automatically alerts emergency contacts with live GPS coordinates, suggesting nearest safe locations (police stations, hospitals) within 5km on a customized map.

---

## Getting Started

### 1. Prerequisites
- **Node.js**: Version 20 or higher.
- **Java Development Kit (JDK)**: JDK 17 or higher (with `JAVA_HOME` set).
- **Android SDK**: With `ANDROID_HOME` environment variable configured.
- **Python**: Version 3.11 or higher.

---

### 2. Run the REST API Backend
```bash
# Clone the repository
git clone https://github.com/vulnerable4u/Auralis-women-safety-web-app.git AURALIS
cd AURALIS

# Launch the startup script (creates venv and installs dependencies automatically)
chmod +x run.sh
./run.sh
```
The server will start on port `5001`. Access the admin supervision dashboard by logging in at `/login`.

---

### 3. Build & Run the Android Client
```bash
# Navigate to the mobile folder
cd mobile

# Install JavaScript dependencies
npm install

# Connect a physical device (enable Developer Options → USB Debugging) or start an emulator
# Set up SDK path (e.g., echo "sdk.dir=$ANDROID_HOME" > android/local.properties)
# Then compile and launch the application:
npx react-native run-android
```
* **On physical devices**, tap the settings gear on the login page and point the server host to your computer's LAN IP (e.g., `http://192.168.x.x:5001`). Emulators can connect directly to the loopback interface default (`http://10.0.2.2:5001`).

Alternatively, open the `mobile/android/` project folder directly in **Android Studio** to sync Gradle and build, run, or profile the application.

---

## API Reference

### Telemetry Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/motion_data` | Post 5-second buffer of accelerometer/gyroscope readings. |
| POST | `/api/audio_data` | Post real-time client-side extracted audio feature vector. |
| POST | `/api/motion_baseline` | Save walking baseline readings for user profiling. |
| GET | `/api/onboarding/status` | Retrieve contact and motion calibration progress for the user. |

### Core Safety Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/threat_status` | Fetch current threat level, contributions, and explanations. |
| POST | `/api/start_monitoring` | Start server threat evaluation thread. |
| POST | `/api/stop_monitoring` | Stop server threat evaluation thread. |
| POST | `/api/trigger_sos` | Manually activate critical SOS status and notify contacts. |
| GET | `/api/safe_places` | Get nearby safe zones prioritizing police and hospitals. |

---

## 📄 License
This project is created for educational and safety research purposes.

