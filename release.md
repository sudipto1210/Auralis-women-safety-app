# Auralis v1.0.0 - Production Release

**Auralis** is a privacy-first, sensor-fusion threat monitoring and safety command center. It leverages on-device telemetry and in-memory audio feature processing alongside a cloud-hosted Threat Fusion engine to evaluate risk and automate emergency distress triggers. 

This release marks the transition of the application from local development to a secure, permanent production environment.

---

## Key Highlights

### Hardened Android Client (`mobile/`)
* **Integrity Gate**: On-device checking for root binaries (`su`), active debuggers, emulator footprints, and package signature integrity.
* **Hardware-Backed Keystore**: Securely stores JWT sessions and token configuration inside the Android KeyStore provider.
* **Network Security Policies**: Restricts all outbound telemetry to secure HTTPS endpoints, blocking cleartext HTTP and custom user CAs.
* **Log Sanitization**: Automated removal of console debug logs during production compilation.

### Threat Fusion Engine (`backend/`)
* **Multi-Layer Audio Pipeline**: Performs in-memory voice activity gating (85–255Hz) and distress scoring using MFCC features, pitch variance, and spectral contrast with adaptive environment thresholding.
* **Walking Gait Profiling**: Calibrates gait cadence and acceleration vectors to establish a personalized walking profile, classifying gait anomalies via Z-score deviations.
* **Sensor Fusion Modifiers**: Composes raw motion and audio distress scores with dynamic context modifiers (isolation risk, high-risk hours) to trigger progressive threat levels.
* **Automated SOS Triggering**: Securely notifies emergency contacts, sharing GPS coordinates and mapping nearby safety centers within 5km (police stations, hospitals).

---

## 🔧 What's New in v1.0.0
* **Production Render Setup**: Replaced local dev servers with a live, production-grade API service deployed on Render (`https://auralis-women-safety-app.onrender.com`).
* **Hardcoded Server Locking**: Removed developer-oriented local IP / URL configuration panels from both the **Login Screen** and the **Settings Screen** to prevent preference poisoning.
* **Gradle Build Optimization**: Configured automated output naming rules compiling the final product directly to `auralis.apk`.
* **Cleaned TypeScript Compliance**: Fixed pre-existing CSS properties (such as font weight constraints) to pass production lint gates.

---

## Installation Instructions

1. Download **`auralis.apk`** from the assets below.
2. Install the APK on your Android device (ensure "Install from Unknown Sources" is permitted if prompted).
3. Open the app, authenticate securely with Google Sign-in, and proceed to set up your emergency contacts and baseline walking calibration.
