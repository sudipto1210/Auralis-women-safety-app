# AURALIS - Women Safety Assistant

## Tech Stack Report

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Backend Technologies](#backend-technologies)
3. [Frontend Technologies](#frontend-technologies)
4. [Database & Storage](#database--storage)
5. [Machine Learning & AI](#machine-learning--ai)
6. [Authentication & Security](#authentication--security)
7. [APIs & External Services](#apis--external-services)
8. [Development & Deployment](#development--deployment)
9. [Project Structure](#project-structure)
10. [Key Dependencies](#key-dependencies)

---

## Project Overview

**AURALIS** is a comprehensive, real-time women safety application with threat monitoring, emergency SOS, AI-powered safety guidance, and trusted contact management. Built with modern web technologies for reliability and ease of use.

### Core Features
- **Real-time Threat Monitoring** - Continuous assessment combining motion and audio analysis
- **One-Click SOS Emergency** - Instant alert system with location sharing to all emergency contacts
- **AI Safety Chatbot** - Intelligent assistant providing safety recommendations and emergency guidance
- **Trusted Contact Management** - Securely store and manage up to 10 emergency contacts
- **Dual-Camera Support** - Server-rendered stream for desktop, dual camera for mobile
- **Interactive Safe Places Map** - Find nearby police stations, hospitals, and safe zones
- **Real-time Analytics** - Live threat visualization with historical charts

---

## Backend Technologies

### Core Framework

| Technology | Version | Purpose |
|------------|---------|---------|
| **Flask** | 3.0.0 | Lightweight web application framework |
| **Python** | 3.11.9 | Core programming language |

### Web Server

| Technology | Purpose |
|------------|---------|
| **Gunicorn** (23.0.0) | WSGI HTTP Server for production deployment |
| **Werkzeug** (3.0.1) | WSGI utility library, password hashing, security |

### Database

| Technology | Purpose |
|------------|---------|
| **Supabase** (2.6.0) | Cloud-based PostgreSQL database with REST API |
| **PostgreSQL** | Underlying database engine (hosted on Supabase) |

### Key Flask Modules
- `Flask` - Main application class
- `render_template` - HTML template rendering
- `Response` - Video streaming responses
- `jsonify` - JSON API responses
- `session` - Server-side session management
- `request` - HTTP request handling
- `redirect`, `url_for` - URL routing

---

## Frontend Technologies

### Markup & Styling

| Technology | Purpose |
|------------|---------|
| **HTML5** | Semantic markup structure |
| **CSS3** | Modern responsive styling |
| **Font Awesome** (6.4.0) | Icon library for UI elements |

### CSS Framework/Features
- Custom responsive design
- Dark/Light theme support
- Loading animations
- Status indicators
- Mobile-first approach

### JavaScript Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| **Chart.js** | Latest | Real-time threat visualization charts |
| **MapLibre GL JS** | 3.0.1 | Interactive maps (OpenSource alternative to Mapbox) |
| **Vanilla JavaScript** | ES6+ | Core application logic (no heavy frameworks) |

### Frontend Components
- **Real-time Threat Chart** - Line chart showing threat score over time
- **Interactive Map** - MapLibre GL with custom markers for safe places
- **Dual Camera Feed** - Front and back camera support
- **Chatbot Interface** - AI safety assistant conversation UI
- **SOS Button** - One-click emergency activation
- **Status Indicators** - Color-coded threat level display

---

## Database & Storage

### Primary Database: Supabase

**Supabase** is an open-source Firebase alternative providing:
- **PostgreSQL Database** - Full SQL capabilities
- **REST API** - Auto-generated CRUD endpoints
- **Row Level Security (RLS)** - Data access control
- **Real-time Subscriptions** - Live data updates

### Database Tables

| Table | Purpose |
|-------|---------|
| `users` | User accounts, authentication, profiles |
| `emergency_contacts` | Trusted contact management |
| `activity_logs` | System activity and audit trail |
| `threat_history` | Historical threat assessment data |
| `emergency_config` | Emergency services configuration |
| `chatbot_training` | Chatbot intent patterns and responses |
| `safe_places_config` | Safe places search configuration |

### Database Operations (via `Database/database.py`)

**UserDB Class:**
- `get_by_email()` - Retrieve user by email
- `get_by_username()` - Retrieve user by username
- `get_all_users()` - Get all registered users
- `create()` - Create new user account
- `update()` - Update user profile
- `verify_password()` - Authenticate admin users
- `get_or_create_oauth_user()` - Handle OAuth user creation

**EmergencyContactsDB Class:**
- `get_by_user()` - Get contacts for a user
- `create()` - Add emergency contact
- `delete()` - Remove contact
- `delete_by_user()` - Remove all user contacts

**ActivityLogsDB Class:**
- `log()` - Record activity events
- `get_recent()` - Fetch recent logs
- `get_by_username()` - Filter by user

**ConfigDB Class:**
- `get_emergency_config()` - Emergency services settings
- `get_chatbot_config()` - Chatbot training data
- `get_safe_places_config()` - Safe places search radius

---

## Machine Learning & AI

### Speech & Audio Analysis

| Component | File | Purpose |
|-----------|------|---------|
| **SpeechDetector** | `src/speech_analysis/speech_detector.py` | MFCC feature extraction and emotion detection |
| **AudioRecorder** | `src/audio_capture/audio_recorder.py` | Audio capture and processing |

#### MFCC Feature Extraction Pipeline
1. **DC Offset Removal** - Center audio signal
2. **Pre-emphasis** - Boost high frequencies
3. **Framing** - 25ms frames with 10ms overlap
4. **Windowing** - Hamming window application
5. **FFT** - Fast Fourier Transform
6. **Mel Filterbank** - 26 Mel-scale filters
7. **Log Energy** - Logarithm of filterbank energies
8. **DCT-II** - Discrete Cosine Transform for MFCC coefficients

### Emotion Detection Model

| Component | File | Purpose |
|-----------|------|---------|
| **LSTMEmotionModel** | `src/ml_models/emotion_model.py` | Keras-based LSTM neural network |

#### Model Architecture
```
LSTMEmotionModel
├── Input: (SEQ_LEN=40, N_MFCC=13)
├── LSTM(64, return_sequences=True)
├── Dropout(0.3)
├── LSTM(32)
├── Dropout(0.3)
├── Dense(32, activation="relu")
└── Dense(6, activation="softmax")  # 6 emotion classes
```

#### Emotion Classes
- `neutral`
- `happiness`
- `sadness`
- `anger`
- `fear`
- `situational_arousal`

#### Model Files
- `models/emotion_model.keras` - Trained Keras model
- `models/emotion_model_scaler.pkl` - StandardScaler for MFCC normalization

### Motion Detection

| Component | File | Purpose |
|-----------|------|---------|
| **MotionDetector** | `src/motion_detection/motion_detector.py` | OpenCV background subtraction |

#### Motion Detection Algorithm
1. **Background Subtraction** - MOG2 (Mixture of Gaussians)
2. **Shadow Detection** - Distinguish shadows from actual motion
3. **Morphological Operations** - Noise reduction via opening
4. **Area Calculation** - Motion pixel count
5. **Adaptive Scoring** - Convert motion area to 0-1 score

#### Parameters
| Parameter | Value | Description |
|-----------|-------|-------------|
| `history` | 200 | Number of frames for background model |
| `var_threshold` | 48 | Variance threshold for foreground detection |
| `learning_rate` | 0.003 | Background model adaptation rate |
| `min_area_ratio` | 0.001 | Minimum motion area threshold |
| `smoothing_window` | 4 | Temporal smoothing window size |

### Threat Assessment

| Component | File | Purpose |
|-----------|------|---------|
| **ThreatFusion** | `src/threat_assessment/threat_fusion.py` | Multi-signal fusion |

#### Threat Score Formula
```
threat_score = (speech_weight × speech_score) + 
               (motion_weight × motion_score) + 
               (emotion_weight × emotion_score)

Where:
- speech_weight = 0.4
- motion_weight = 0.3
- emotion_weight = 0.3
```

#### Emotion Weights
| Emotion | Weight |
|---------|--------|
| `scream` | 0.8 |
| `panic` | 0.7 |
| `distress` | 0.6 |
| `fear` | 0.4 |
| `anger` | 0.3 |
| `neutral` | 0.0 |

#### Threat States
| State | Score Range |
|-------|-------------|
| `SAFE` | < 0.3 |
| `MEDIUM` | 0.3 - 0.6 |
| `HIGH` | 0.6 - 0.8 |
| `CRITICAL` | ≥ 0.8 |

---

## Authentication & Security

### Google OAuth 2.0

| Component | File | Purpose |
|-----------|------|---------|
| **Google OAuth** | `Backend/google_oauth.py` | Google Sign-In integration |

#### OAuth Flow
1. User clicks "Login with Google"
2. Google Identity Services returns ID token
3. Server verifies token using `google.oauth2.id_token`
4. User created/updated in Supabase
5. Session established

#### OAuth Libraries
```python
google-auth==2.23.4
google-auth-oauthlib==1.2.0
google-auth-httpx2==0.1.6
```

### Password Security

| Feature | Implementation |
|---------|----------------|
| **Hashing** | Werkzeug `generate_password_hash()` (bcrypt) |
| **Verification** | Werkzeug `check_password_hash()` |
| **Session Security** | Encrypted cookies, HttpOnly, SameSite |

### Security Configuration
```python
app.secret_key = os.environ.get("SECRET_KEY")
app.config["SESSION_COOKIE_SECURE"] = PRODUCTION
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
```

### Environment Variables Required
| Variable | Purpose |
|----------|---------|
| `GOOGLE_CLIENT_ID` | OAuth client identifier |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret |
| `GOOGLE_REDIRECT_URI` | OAuth callback URL |
| `SECRET_KEY` | Flask session encryption key |

---

## APIs & External Services

### REST API Endpoints

#### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/login` | Admin login |
| GET | `/user-login` | User login page |
| GET/POST | `/api/google-auth` | Google OAuth authentication |
| GET | `/logout` | End session |

#### Threat Monitoring
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/start_monitoring` | Start threat monitoring |
| POST | `/api/stop_monitoring` | Stop monitoring |
| GET | `/api/threat_status` | Get current threat status |

#### Emergency
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/trigger_sos` | Trigger SOS emergency |
| POST | `/api/update_location` | Update user location |

#### Safe Places
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/safe_places` | Get nearby safe places |

#### Chatbot
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chatbot` | Send message to chatbot |
| POST | `/api/chatbot/auto_alert` | Auto-alert emergency contacts |

#### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin` | Admin dashboard |
| POST | `/api/admin/delete_user` | Delete user |
| GET | `/api/admin/activity_logs` | Get activity logs |
| GET | `/api/admin/user_threat_status` | Get all users' threat status |
| GET | `/api/admin/user_details/<username>` | Get user details |

#### Utilities
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Main dashboard |
| GET | `/about` | About page |
| GET | `/onboarding` | User onboarding |
| GET | `/video_feed` | MJPEG video stream |

### External APIs

| Service | Purpose |
|---------|---------|
| **Google OAuth** | User authentication |
| **MapLibre/MapTiler** | Interactive maps (OpenStreetMap tiles) |
| **OpenStreetMap Directions** | Turn-by-turn navigation to safe places |

### Configuration Files

| File | Purpose |
|------|---------|
| `config/emergency_config.json` | Emergency numbers, SOS settings, threat thresholds |
| `config/chatbot_training.json` | Chatbot intents, patterns, responses |
| `config/safe_places_config.json` | Safe places search radius, place types |

---

## Development & Deployment

### Development Tools

| Tool | Purpose |
|------|---------|
| **Python Virtual Environment** | Isolated Python environment |
| **Flask Debug Mode** | Development debugging |
| **Chrome DevTools** | Frontend debugging |

### Production Deployment

| Tool | Purpose |
|------|---------|
| **Gunicorn** | WSGI server |
| **Render** | Cloud hosting platform |
| **Environment Variables** | Configuration management |

### Build & Run Scripts

| File | Purpose |
|------|---------|
| `build.sh` | Build script for deployment |
| `run.sh` | Development server startup |
| `requirements.txt` | Python dependencies |

### Python Runtime
```
Python 3.11.9
```

---

## Project Structure

```
AURALIS/
├── Backend/
│   ├── __init__.py
│   ├── server_backend.py         # Main Flask application
│   ├── google_oauth.py           # Google OAuth integration
│   ├── clear_user_data.py        # User data management
│   ├── reset_admin_password.py   # Admin password reset
│   └── wsgi.py                   # WSGI entry point
├── Database/
│   ├── __init__.py
│   ├── database.py               # Supabase database operations
│   └── setup_admin.py            # Admin user setup
├── Frontend/
│   ├── templates/
│   │   ├── index.html            # Main dashboard
│   │   ├── login.html            # Admin login
│   │   ├── user_login.html       # User login page
│   │   ├── onboarding.html       # Contact setup
│   │   ├── admin.html            # Admin dashboard
│   │   ├── about.html            # About page
│   │   └── loading.html          # Loading screen
│   └── static/
│       ├── css/
│       │   ├── style.css         # Main styles
│       │   ├── admin.css         # Admin panel styles
│       │   ├── loading.css       # Loading animations
│       │   ├── onboarding.css    # Onboarding styles
│       │   ├── about.css         # About page styles
│       │   └── theme.js          # Theme management
│       └── js/
│           ├── app.js            # Main application logic
│           ├── admin.js          # Admin panel logic
│           ├── onboarding.js     # Onboarding flow
│           └── theme.js          # Theme toggling
├── src/
│   ├── audio_capture/
│   │   ├── __init__.py
│   │   └── audio_recorder.py     # Audio capture module
│   ├── context_engine/
│   │   └── context_engine.py     # Context awareness
│   ├── map_integration/
│   │   ├── __init__.py
│   │   └── safe_places.py        # Safe places integration
│   ├── ml_models/
│   │   ├── __init__.py
│   │   ├── emotion_model.py      # LSTM emotion classifier
│   │   └── data_processing/      # Data processing utilities
│   ├── motion_detection/
│   │   ├── __init__.py
│   │   └── motion_detector.py    # Motion detection
│   ├── notifications/
│   │   ├── __init__.py
│   │   └── push_notifier.py      # Push notifications
│   ├── speech_analysis/
│   │   ├── __init__.py
│   │   └── speech_detector.py    # Speech analysis & MFCC
│   └── threat_assessment/
│       ├── __init__.py
│       └── threat_fusion.py      # Multi-signal fusion
├── models/
│   ├── emotion_model.keras       # Trained LSTM model
│   ├── emotion_model.pkl         # Model artifacts
│   └── emotion_model_scaler.pkl  # StandardScaler
├── config/
│   ├── emergency_config.json     # Emergency settings
│   ├── chatbot_training.json     # Chatbot training data
│   └── safe_places_config.json   # Safe places config
├── data/
│   └── activity_logs.json        # Activity log storage
├── dataset/
│   └── ravdess/                  # RAVDESS emotional speech dataset
├── requirements.txt              # Python dependencies
├── runtime.txt                   # Python runtime version
├── build.sh                      # Build script
├── run.sh                        # Run script
├── .gitignore                    # Git ignore rules
└── README.md                     # Project documentation
```

---

## Key Dependencies

### Core Python Packages

```txt
# Core Flask & Production Server
Flask==3.0.0 
gunicorn==23.0.0
Werkzeug==3.0.1

# Database & Auth
supabase==2.6.0
google-auth==2.23.4 
google-auth-oauthlib==1.2.0 
python-dotenv==1.0.0 

# ML & Audio
numpy==2.1.3 
opencv-python-headless==4.10.0.84
scipy==1.14.1
soundfile==0.12.1 

# HTTP Client
httpx[http2]>=0.26.0,<0.29.0

# Utilities
markupsafe==3.0.2
```

### TensorFlow/Keras Components

```python
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.callbacks import EarlyStopping
```

### OpenCV Components

```python
import cv2
from cv2 import createBackgroundSubtractorMOG2
```

### Scientific Computing

```python
import numpy as np
from scipy.io import wavfile
```

### Data Processing

```python
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
```

---

## Summary

AURALIS is a comprehensive women safety application built with a modern, scalable tech stack:

- **Backend**: Flask (Python) with Gunicorn for production
- **Database**: Supabase (PostgreSQL) for reliable data storage
- **Frontend**: Vanilla JavaScript with Chart.js and MapLibre GL
- **ML/AI**: TensorFlow/Keras LSTM for emotion recognition
- **Computer Vision**: OpenCV for motion detection
- **Audio Processing**: Custom MFCC feature extraction
- **Authentication**: Google OAuth 2.0
- **Maps**: MapLibre GL with OpenStreetMap tiles

The application provides real-time threat assessment by fusing multiple signals:
- Speech analysis with emotion detection
- Motion detection via background subtraction
- User location for safe places mapping
- AI-powered safety chatbot

---

*Report generated for AURALIS Women Safety Assistant*

