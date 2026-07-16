import os
import pickle
import json
from datetime import datetime
import numpy as np

# Load motion features extraction logic
from motion_features import extract_features, FEATURE_COLUMNS

# Try to import legacy detector for heuristic fallback
try:
    from src.motion_detection.sensor_fusion import MotionAnomalyDetector as LegacyMotionAnomalyDetector
except ImportError:
    LegacyMotionAnomalyDetector = None

class MotionAnomalyDetector:
    """SVM-based motion threat and anomaly detector with heuristic fallback."""
    
    def __init__(self, baseline=None):
        self.baseline = baseline
        self._method = "heuristic"
        self._legacy_detector = None
        
        # Paths to model assets
        self.models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
        svm_path = os.path.join(self.models_dir, "motion_svm.pkl")
        scaler_path = os.path.join(self.models_dir, "motion_scaler.pkl")
        encoder_path = os.path.join(self.models_dir, "motion_label_encoder.pkl")
        meta_path = os.path.join(self.models_dir, "motion_model_meta.json")
        
        # Check if all files exist
        if all(os.path.exists(p) for p in [svm_path, scaler_path, encoder_path, meta_path]):
            try:
                with open(svm_path, "rb") as f:
                    self.clf = pickle.load(f)
                with open(scaler_path, "rb") as f:
                    self.scaler = pickle.load(f)
                with open(encoder_path, "rb") as f:
                    self.le = pickle.load(f)
                with open(meta_path, "r") as f:
                    self.meta = json.load(f)
                
                self._method = "svm"
                print(f"[MotionAnomalyDetector] SVM model loaded successfully from {self.models_dir}. Method: svm")
            except Exception as e:
                print(f"[MotionAnomalyDetector] Failed to load SVM model artifacts: {e}. Falling back to heuristic.")
        else:
            print(f"[MotionAnomalyDetector] SVM model files not found in {self.models_dir}. Falling back to heuristic.")
            
        if self._method == "heuristic":
            if LegacyMotionAnomalyDetector is not None:
                self._legacy_detector = LegacyMotionAnomalyDetector(baseline)
                print("[MotionAnomalyDetector] Legacy heuristic detector initialized.")
            else:
                print("[MotionAnomalyDetector] ERROR: Legacy heuristic detector could not be imported!")
                
    def update_baseline(self, baseline):
        self.baseline = baseline
        if self._legacy_detector is not None:
            self._legacy_detector.update_baseline(baseline)
            
    def predict(self, sensor_window):
        """
        Runs SVM inference on the given sensor window.
        
        Returns:
            dict: {threat_classifications, probabilities, predicted_label}
        """
        if self._method == "heuristic":
            # Return empty/default or mock values if in heuristic mode
            return {
                "threat_classifications": {},
                "probabilities": {},
                "predicted_label": "unknown"
            }
            
        features_dict = extract_features(sensor_window)
        if features_dict is None:
            return {
                "threat_classifications": {},
                "probabilities": {},
                "predicted_label": "unknown"
            }
            
        # Build feature vector in exact column order
        try:
            feat_vector = np.array([[features_dict[col] for col in FEATURE_COLUMNS]], dtype=np.float64)
            # Scale features
            feat_scaled = self.scaler.transform(feat_vector)
            # Predict probabilities
            probs = self.clf.predict_proba(feat_scaled)[0]
            # Predict label index
            pred_idx = self.clf.predict(feat_scaled)[0]
            predicted_label = str(self.le.inverse_transform([pred_idx])[0])
            
            # Map probabilities to classes
            class_probs = {self.le.classes_[i]: float(probs[i]) for i in range(len(self.le.classes_))}
            
            # Extract threat classifications
            threat_labels = self.meta.get("threat_labels", ["grab", "fall", "panic_run"])
            threat_classifications = {label: class_probs.get(label, 0.0) for label in threat_labels}
            
            return {
                "threat_classifications": threat_classifications,
                "probabilities": class_probs,
                "predicted_label": predicted_label
            }
        except Exception as e:
            print(f"[MotionAnomalyDetector] Error during prediction: {e}")
            return {
                "threat_classifications": {},
                "probabilities": {},
                "predicted_label": "unknown"
            }
            
    def analyze_window(self, sensor_window):
        """
        Analyze a 5-second rolling window of sensor readings.
        
        Args:
            sensor_window: list of dicts {ax, ay, az, gx, gy, gz, timestamp}
            
        Returns:
            dict: {anomaly_score, event_type, confidence, timestamp, z_scores, features}
        """
        if self._method == "heuristic":
            if self._legacy_detector is not None:
                return self._legacy_detector.analyze_window(sensor_window)
            else:
                return {
                    "anomaly_score": 0.0,
                    "event_type": "NONE",
                    "confidence": 0.0,
                    "timestamp": datetime.now().isoformat(),
                    "z_scores": {},
                    "features": {}
                }
                
        # SVM Mode
        if not sensor_window or len(sensor_window) < 20: # Minimum sample threshold
            return {
                "anomaly_score": 0.0,
                "event_type": "NONE",
                "confidence": 0.0,
                "timestamp": datetime.now().isoformat(),
                "z_scores": {},
                "features": {}
            }
            
        pred_res = self.predict(sensor_window)
        predicted_label = pred_res["predicted_label"]
        class_probs = pred_res["probabilities"]
        
        if not class_probs or predicted_label == "unknown":
            return {
                "anomaly_score": 0.0,
                "event_type": "NONE",
                "confidence": 0.0,
                "timestamp": datetime.now().isoformat(),
                "z_scores": {},
                "features": {}
            }
            
        # anomaly_score = 1.0 - prob(normal_walk)
        normal_walk_prob = class_probs.get("normal_walk", 1.0)
        anomaly_score = 1.0 - normal_walk_prob
        
        # Map normal_walk -> NONE, grab -> GRAB, fall -> FALL, panic_run -> PANIC_RUN
        event_mapping = {
            "normal_walk": "NONE",
            "grab": "GRAB",
            "fall": "FALL",
            "panic_run": "PANIC_RUN"
        }
        event_type = event_mapping.get(predicted_label, "NONE")
        
        # confidence
        if event_type != "NONE":
            # Probability of the predicted threat class
            confidence = class_probs.get(predicted_label, anomaly_score)
        else:
            confidence = anomaly_score
            
        # Extract features for returns
        features = extract_features(sensor_window) or {}
        
        return {
            "anomaly_score": round(float(anomaly_score), 4),
            "event_type": event_type,
            "confidence": round(float(confidence), 4),
            "timestamp": datetime.now().isoformat(),
            "z_scores": {},
            "features": {k: round(v, 4) for k, v in features.items() if isinstance(v, (int, float))}
        }
