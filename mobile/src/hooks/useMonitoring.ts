import { useCallback, useEffect, useRef, useState } from "react";
import {
  accelerometer,
  gyroscope,
  setUpdateIntervalForType,
  SensorTypes,
} from "react-native-sensors";
import Geolocation from "react-native-geolocation-service";
import RNSoundLevel from "react-native-sound-level";
import { PermissionsAndroid } from "react-native";
import { secureApi as api } from "../api/secureClient";
import type { SensorSample } from "../api/types";
import { warn } from "../utils/logger";

const INTERVAL_MS = 20;
const GRAVITY = 9.80665;

export function useMonitoring(active: boolean) {
  const motionBuffer = useRef<SensorSample[]>([]);
  const gyroRef = useRef({ x: 0, y: 0, z: 0 });
  const lastMeteringRef = useRef<number>(-160);

  const flushMotion = useCallback(async () => {
    if (motionBuffer.current.length < 10) return;
    const window = motionBuffer.current.slice(-250);
    motionBuffer.current = motionBuffer.current.slice(-120);
    try {
      await api("/api/motion_data", {
        method: "POST",
        body: JSON.stringify({ sensor_window: window }),
      });
    } catch (e) {
      warn("useMonitoring", "motion upload failed", e);
    }
  }, []);

  const sendAudio = useCallback(async () => {
    try {
      const metering = lastMeteringRef.current;
      const energy = Math.max(0, Math.min(1, (metering + 160) / 160));
      await api("/api/audio_data", {
        method: "POST",
        body: JSON.stringify({
          audio_features: {
            energy,
            zcr_mean: energy * 0.3,
            pitch: energy > 0.05 ? 180 : 0,
            pitch_confidence: energy > 0.05 ? 0.75 : 0,
            pitch_variance: energy > 0.05 ? 8 : 0,
            spectral_contrast_mean: energy * 35,
            mfccs: Array.from(
              { length: 13 },
              (_, i) => energy * 8 - 4 + i * 0.1,
            ),
            mfcc_delta_mean: energy > 0.05 ? 4 : 1,
          },
        }),
      });
    } catch (e) {
      warn("useMonitoring", "audio upload failed", e);
    }
  }, []);

  useEffect(() => {
    if (!active) return;

    let motionTimer: ReturnType<typeof setInterval>;
    let audioTimer: ReturnType<typeof setInterval>;
    let gyroSub: any = null;
    let accelSub: any = null;
    let watchId: number | null = null;

    (async () => {
      try {
        await api("/api/start_monitoring", { method: "POST" });
      } catch (e) {
        warn("useMonitoring", "start_monitoring error", e);
      }

      const hasLocPerm =
        (await PermissionsAndroid.request(
          PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
        )) === PermissionsAndroid.RESULTS.GRANTED;

      if (hasLocPerm) {
        try {
          watchId = Geolocation.watchPosition(
            async (pos) => {
              try {
                await api("/api/update_location", {
                  method: "POST",
                  body: JSON.stringify({
                    lat: pos.coords.latitude,
                    lng: pos.coords.longitude,
                  }),
                });
              } catch (e) {
                warn("useMonitoring", "location update failed", e);
              }
            },
            (err) => {
              warn("useMonitoring", "location watch error", err);
            },
            {
              enableHighAccuracy: true,
              distanceFilter: 10,
              interval: 15000,
              fastestInterval: 10000,
            },
          );
        } catch (e) {
          warn("useMonitoring", "location watch init failed", e);
        }
      }

      setUpdateIntervalForType(SensorTypes.accelerometer, INTERVAL_MS);
      setUpdateIntervalForType(SensorTypes.gyroscope, INTERVAL_MS);

      gyroSub = gyroscope.subscribe({
        next: (g) => {
          gyroRef.current = { x: g.x, y: g.y, z: g.z };
        },
        error: (err) => {
          warn("useMonitoring", "gyroscope error", err);
        },
      });

      accelSub = accelerometer.subscribe({
        next: (a) => {
          const g = gyroRef.current;
          motionBuffer.current.push({
            ax: a.x / GRAVITY,
            ay: a.y / GRAVITY,
            az: a.z / GRAVITY,
            gx: g.x,
            gy: g.y,
            gz: g.z,
            timestamp: Date.now() / 1000,
          });
        },
        error: (err) => {
          warn("useMonitoring", "accelerometer error", err);
        },
      });

      motionTimer = setInterval(flushMotion, 5000);

      const hasAudioPerm =
        (await PermissionsAndroid.request(
          PermissionsAndroid.PERMISSIONS.RECORD_AUDIO,
        )) === PermissionsAndroid.RESULTS.GRANTED;

      if (hasAudioPerm) {
        try {
          RNSoundLevel.start();
          RNSoundLevel.onNewFrame = (data) => {
            lastMeteringRef.current = data.value;
          };
          audioTimer = setInterval(sendAudio, 2000);
        } catch (e) {
          warn("useMonitoring", "audio recording start failed", e);
        }
      }
    })();

    return () => {
      if (motionTimer) clearInterval(motionTimer);
      if (audioTimer) clearInterval(audioTimer);
      accelSub?.unsubscribe();
      gyroSub?.unsubscribe();
      if (watchId !== null) {
        Geolocation.clearWatch(watchId);
      }
      try {
        RNSoundLevel.stop();
      } catch {
        // ignore stop errors
      }
      api("/api/stop_monitoring", { method: "POST" }).catch(() => {});
    };
  }, [active, flushMotion, sendAudio]);
}

export function useThreatStatus(pollMs = 2000) {
  const [status, setStatus] = useState<{
    state: string;
    score: number;
    monitoring_active: boolean;
    summary?: string;
  } | null>(null);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const data = await api<{
          state: string;
          score: number;
          monitoring_active: boolean;
          explanation?: { summary?: string };
        }>("/api/threat_status");
        if (mounted) {
          setStatus({
            state: data.state,
            score: data.score,
            monitoring_active: data.monitoring_active,
            summary: data.explanation?.summary,
          });
        }
      } catch {
        /* ignore when logged out */
      }
    };
    load();
    const id = setInterval(load, pollMs);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, [pollMs]);

  return status;
}
