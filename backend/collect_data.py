import os
import csv
from flask import Blueprint, request, jsonify
from motion_features import extract_features, FEATURE_COLUMNS

collect_bp = Blueprint("collect_data", __name__)

VALID_LABELS = {"normal_walk", "grab", "fall", "panic_run"}
REQUIRED_KEYS = {"ax", "ay", "az", "gx", "gy", "gz"}

# Set up data collection directory
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
TRAINING_DIR = os.path.join(BACKEND_DIR, "data", "training")
os.makedirs(TRAINING_DIR, exist_ok=True)


def get_dataset_counts():
    """Reads CSV files to count current samples per label."""
    counts = {}
    for label in VALID_LABELS:
        filepath = os.path.join(TRAINING_DIR, f"{label}.csv")
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", newline="") as f:
                    # Counting lines and subtracting 1 for header
                    line_count = sum(1 for _ in f)
                    counts[label] = max(0, line_count - 1)
            except Exception:
                counts[label] = 0
        else:
            counts[label] = 0
    return counts


@collect_bp.route("/api/collect_data", methods=["POST"])
def collect_data():
    """
    Accepts a labeled IMU sensor window, validates it, extracts features,
    and appends a new row to the corresponding training CSV file.
    """
    try:
        data = request.get_json() or {}
        label = data.get("label")
        sensor_window = data.get("sensor_window")

        # 1. Validation
        if label not in VALID_LABELS:
            return jsonify({
                "status": "error",
                "message": f"Invalid label. Must be one of: {', '.join(VALID_LABELS)}"
            }), 400

        if not sensor_window or not isinstance(sensor_window, list):
            return jsonify({
                "status": "error",
                "message": "sensor_window must be a non-empty JSON array."
            }), 400

        if len(sensor_window) < 50:
            return jsonify({
                "status": "error",
                "message": f"Insufficient samples in window. Got {len(sensor_window)}, expected >= 50."
            }), 400

        # Validate that each sample has all required keys
        for idx, sample in enumerate(sensor_window):
            if not isinstance(sample, dict) or not REQUIRED_KEYS.issubset(sample.keys()):
                return jsonify({
                    "status": "error",
                    "message": f"Sample at index {idx} is missing one or more required keys: {REQUIRED_KEYS}"
                }), 400

        # 2. Feature Extraction
        features = extract_features(sensor_window)
        if features is None:
            return jsonify({
                "status": "error",
                "message": "Failed to extract features from the provided window."
            }), 400

        # 3. CSV Append (write header if file is new)
        filepath = os.path.join(TRAINING_DIR, f"{label}.csv")
        file_exists = os.path.exists(filepath)

        with open(filepath, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FEATURE_COLUMNS)
            if not file_exists:
                writer.writeheader()
            writer.writerow(features)

        # 4. Return stats
        counts = get_dataset_counts()
        return jsonify({
            "status": "success",
            "label": label,
            "samples_in_window": len(sensor_window),
            "dataset_counts": counts
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to process and collect data: {str(e)}"
        }), 500


@collect_bp.route("/api/collect_data/stats", methods=["GET"])
def collect_data_stats():
    """Returns the current sample count per label."""
    try:
        counts = get_dataset_counts()
        return jsonify(counts)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve stats: {str(e)}"
        }), 500
