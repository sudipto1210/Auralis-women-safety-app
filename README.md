# AURALIS - Women Safety & Threat Monitoring Command Center

The system is built around two tightly coupled components:

1. **Hardened Android Mobile Client** (`mobile/`) — A native React Native CLI app that collects IMU sensor telemetry (accelerometer + gyroscope) and audio features in the background. The client is hardened against tampering, reverse engineering, and credential leakage.
2. **Threat Fusion API Server** (`backend/`) — A Flask + Supabase backend that runs gait anomaly detection against user-calibrated walking baselines, filters audio through a multi-layer distress pipeline, evaluates context risk, and triggers automated SOS notifications.

---

## Architecture

```
AURALIS/
├── backend/                        # Flask REST API and threat processing engine
│   ├── api/
│   │   ├── server_backend.py       # Main API — all routes and threat coordination
│   │   ├── google_oauth.py         # Google ID token verification
│   │   ├── mobile_auth.py          # JWT token creation and validation
│   │   └── wsgi.py                 # Production WSGI entry point (gunicorn)
│   ├── database/
│   │   └── database.py             # Supabase ORM layer for all tables
│   ├── src/
│   │   ├── motion_detection/       # Gait profiling and anomaly scoring
│   │   ├── speech_analysis/        # VAD and environment-adaptive audio engine
│   │   ├── threat_assessment/      # Sensor fusion and override logic
│   │   └── context_engine/         # Dynamic context weight adaptation
│   ├── data/                       # Runtime JSON files (gitignored)
│   ├── requirements.txt
│   └── run.sh                      # Dev server startup (creates venv automatically)
│
├── mobile/                           # Hardened React Native CLI Android App
│   ├── android/                      # Native Kotlin and Gradle settings
│   ├── src/                          # Secure UI screens, navigation, and state
│   ├── package.json                  # React Native dependencies
│   └── App.tsx                       # Root component with security check gates
│
├── run.sh                            # Root convenience launcher (delegates to backend)
├── README.md                         # Main command center documentation
```

---

## Features

### Security & Privacy
- **Device Integrity Gate** — Native Kotlin module checks for root access (`su` binaries, root app packages), attached debuggers, emulator fingerprints, and APK signature before any app logic runs.
- **Hardware-Backed Token Storage** — JWT session tokens and API endpoint URLs are stored exclusively in the Android Keystore via the Keychain API, not AsyncStorage.
- **HTTPS-Only Release Builds** — `network_security_config.xml` blocks all cleartext HTTP in release APKs and restricts trust to system CA roots (no user-installed CA certificates).
- **Logcat Sanitization** — All `console.*` calls are stripped at transpile time in production builds. `android.util.Log` calls are stripped by R8/ProGuard rules.
- **API Rate Limiting** — Flask-Limiter enforces per-IP limits on all telemetry and authentication endpoints.

### Threat Detection
- **Multi-Layer Audio Pipeline**
  - Layer 1: Ambient noise classification (Quiet / Street / Crowd / Transport)
  - Layer 2: Voice activity gating via autocorrelation in the 85–255 Hz human vocal range
  - Layer 3: Distress scoring from ZCR, pitch variance, spectral contrast, and 13-coefficient MFCC vectors
  - Layer 4: Adaptive threshold — higher sensitivity in quiet environments, reduced false positives in transit
- **Per-User Motion Baseline** — 30-second onboarding calibration builds a statistical walking profile (cadence, jerk, accelerometer variance). Anomalies are scored as z-score deviations from this personal baseline.
- **Sensor Fusion** — Motion and audio scores are weighted and fused into a single threat level (SAFE / LOW / MEDIUM / HIGH / CRITICAL) with context modifiers (time of day, location isolation).
- **Critical Override** — Coordinated high-confidence events (e.g. FALL event + vocal distress) bypass smoothing and immediately trigger CRITICAL state.

### Emergency Workflows
- SOS trigger notifies all registered emergency contacts with GPS coordinates and nearest safe places (police stations, hospitals within 5 km).
- Location is stored in memory only — written to incident records only when threat level reaches HIGH or CRITICAL.
- Audio features are never persisted — analyzed in-memory and discarded immediately after scoring.

---

## Getting Started

### Prerequisites

| Tool | Version |
|---|---|
| Node.js | 20 or higher |
| JDK | 17 or higher (`JAVA_HOME` set) |
| Android SDK | API 33+ (`ANDROID_HOME` set) |
| Python | 3.11 or higher |

---

### 1. Configure Environment Variables

```bash
# Backend
cp .env.example .env
# Fill in: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SECRET_KEY

# Mobile
cp mobile/.env.example mobile/.env
# Fill in: EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID, EXPO_PUBLIC_GOOGLE_CLIENT_ID, EXPO_PUBLIC_API_URL
```

---

### 2. Run the Backend Server

```bash
chmod +x run.sh
./run.sh
```

`run.sh` automatically creates a Python virtual environment at `./venv/`, installs all dependencies from `backend/requirements.txt`, and starts the Flask development server on port `5001`.

---

### 3. Build & Run the Android App

```bash
cd mobile
npm install

# Debug build (runs on connected device or emulator)
npx react-native run-android
```

For a **release build**:

```bash
cd mobile/android
./gradlew assembleRelease
# APK: mobile/android/app/build/outputs/apk/release/app-release.apk
```

> On a physical device, open the settings page in the app and set the server URL to your machine's LAN IP (e.g. `http://192.168.x.x:5001`). On an emulator, use `http://10.0.2.2:5001`.

---

### 4. Set Up the Database

Run the SQL in `backend/database/` against your Supabase project:

1. **Schema** — Create all tables (users, emergency_contacts, threat_history, etc.)
2. **RLS Policies** — Enable Row-Level Security so users can only access their own data

---

## API Reference

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/google-auth` | Exchange Google ID token for a JWT access token |
| GET | `/api/mobile/me` | Get authenticated user profile |
| GET | `/api/onboarding/status` | Check contacts and calibration progress |
| POST | `/api/onboarding/contacts` | Save emergency contacts |
| POST | `/api/onboarding/finish` | Complete onboarding after motion calibration |

### Telemetry
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/motion_data` | Submit accelerometer/gyroscope window for anomaly scoring |
| POST | `/api/audio_data` | Submit extracted audio feature vector for distress scoring |
| POST | `/api/motion_baseline` | Save walking baseline profile |
| POST | `/api/update_location` | Update current GPS coordinates |

### Safety
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/threat_status` | Get current threat level, scores, history |
| POST | `/api/start_monitoring` | Start server-side threat evaluation |
| POST | `/api/stop_monitoring` | Stop threat evaluation |
| POST | `/api/trigger_sos` | Trigger SOS and notify emergency contacts |
| GET | `/api/safe_places` | Get nearby police stations and hospitals |

### Research & Evaluation
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/research_metrics` | Precision, false alarm rate, signal breakdown |
| GET | `/api/research_report` | Full exportable JSON research report |
| POST | `/api/incidents/<id>/feedback` | Label an incident as confirmed / false alarm |

---

## License

This project is developed for educational and safety research purposes.
