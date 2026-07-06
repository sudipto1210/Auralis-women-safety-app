import numpy as np

# Stable feature columns order as specified in requirements
FEATURE_COLUMNS = [
    "accel_mean",
    "accel_std",
    "accel_max",
    "accel_min",
    "accel_p25",
    "accel_p75",
    "accel_p95",
    "jerk_mean",
    "jerk_std",
    "jerk_max",
    "gyro_mean",
    "gyro_std",
    "gyro_max",
    "cadence_zcr",
    "impact_ratio",
    "freefall_ratio",
    "high_jerk_ratio",
    "signal_energy"
]

def extract_features(sensor_window):
    """
    Extracts 18 statistical features from a 5-second window (or at least 50 samples)
    of raw accelerometer and gyroscope readings.

    Args:
        sensor_window: list of dicts, each having keys: ax, ay, az, gx, gy, gz, timestamp

    Returns:
        dict: A dictionary mapping feature names to their extracted float values,
              or None if the input window is invalid.
    """
    if not sensor_window or len(sensor_window) < 2:
        return None

    try:
        # Convert values to numpy arrays
        ax = np.array([r["ax"] for r in sensor_window], dtype=np.float64)
        ay = np.array([r["ay"] for r in sensor_window], dtype=np.float64)
        az = np.array([r["az"] for r in sensor_window], dtype=np.float64)
        gx = np.array([r.get("gx", 0.0) for r in sensor_window], dtype=np.float64)
        gy = np.array([r.get("gy", 0.0) for r in sensor_window], dtype=np.float64)
        gz = np.array([r.get("gz", 0.0) for r in sensor_window], dtype=np.float64)

        # 1. Accelerometer Magnitude Features
        accel_mag = np.sqrt(ax**2 + ay**2 + az**2)
        accel_mean = float(np.mean(accel_mag))
        accel_std = float(np.std(accel_mag))
        accel_max = float(np.max(accel_mag))
        accel_min = float(np.min(accel_mag))
        accel_p25 = float(np.percentile(accel_mag, 25))
        accel_p75 = float(np.percentile(accel_mag, 75))
        accel_p95 = float(np.percentile(accel_mag, 95))

        # 2. Jerk Features (jerk = |accel_mag[i] - accel_mag[i-1]|)
        jerk = np.abs(np.diff(accel_mag))
        if len(jerk) > 0:
            jerk_mean = float(np.mean(jerk))
            jerk_std = float(np.std(jerk))
            jerk_max = float(np.max(jerk))
            high_jerk_ratio = float(np.mean(jerk > 2.0))
        else:
            jerk_mean, jerk_std, jerk_max, high_jerk_ratio = 0.0, 0.0, 0.0, 0.0

        # 3. Gyroscope Magnitude Features
        gyro_mag = np.sqrt(gx**2 + gy**2 + gz**2)
        gyro_mean = float(np.mean(gyro_mag))
        gyro_std = float(np.std(gyro_mag))
        gyro_max = float(np.max(gyro_mag))

        # 4. Cadence (zero-crossings of mean-centered accel magnitude)
        accel_centered = accel_mag - accel_mean
        cadence_zcr = int(np.sum(np.diff(np.sign(accel_centered)) != 0))

        # 5. Ratios
        impact_ratio = float(np.mean(accel_mag > 3.0))
        freefall_ratio = float(np.mean(accel_mag < 0.3))

        # 6. Signal Energy (mean of squared accel magnitudes)
        signal_energy = float(np.mean(accel_mag**2))

        return {
            "accel_mean": accel_mean,
            "accel_std": accel_std,
            "accel_max": accel_max,
            "accel_min": accel_min,
            "accel_p25": accel_p25,
            "accel_p75": accel_p75,
            "accel_p95": accel_p95,
            "jerk_mean": jerk_mean,
            "jerk_std": jerk_std,
            "jerk_max": jerk_max,
            "gyro_mean": gyro_mean,
            "gyro_std": gyro_std,
            "gyro_max": gyro_max,
            "cadence_zcr": cadence_zcr,
            "impact_ratio": impact_ratio,
            "freefall_ratio": freefall_ratio,
            "high_jerk_ratio": high_jerk_ratio,
            "signal_energy": signal_energy
        }
    except Exception as e:
        # Graceful error handling for feature extraction issues
        print(f"[Feature Extraction] Error: {e}")
        return None
