import { useCallback, useRef } from "react";
import {
  accelerometer,
  gyroscope,
  setUpdateIntervalForType,
  SensorTypes,
} from "react-native-sensors";
import type { SensorSample } from "../api/types";

const INTERVAL_MS = 20;
const GRAVITY = 9.80665;

export function useMotionSampler() {
  const bufferRef = useRef<SensorSample[]>([]);
  const accelSub = useRef<any>(null);
  const gyroSub = useRef<any>(null);
  const gyroRef = useRef({ x: 0, y: 0, z: 0 });

  const stop = useCallback(() => {
    if (accelSub.current) {
      accelSub.current.unsubscribe();
      accelSub.current = null;
    }
    if (gyroSub.current) {
      gyroSub.current.unsubscribe();
      gyroSub.current = null;
    }
  }, []);

  const start = useCallback(async (): Promise<() => void> => {
    stop();
    bufferRef.current = [];

    setUpdateIntervalForType(SensorTypes.accelerometer, INTERVAL_MS);
    setUpdateIntervalForType(SensorTypes.gyroscope, INTERVAL_MS);

    gyroSub.current = gyroscope.subscribe({
      next: (g) => {
        gyroRef.current = { x: g.x, y: g.y, z: g.z };
      },
      error: (e) => {
        console.warn("Gyroscope error", e);
      },
    });

    accelSub.current = accelerometer.subscribe({
      next: (a) => {
        const g = gyroRef.current;
        bufferRef.current.push({
          ax: a.x / GRAVITY,
          ay: a.y / GRAVITY,
          az: a.z / GRAVITY,
          gx: g.x,
          gy: g.y,
          gz: g.z,
          timestamp: Date.now() / 1000,
        });
        if (bufferRef.current.length > 500) {
          bufferRef.current = bufferRef.current.slice(-250);
        }
      },
      error: (e) => {
        console.warn("Accelerometer error", e);
      },
    });

    return () => {
      stop();
    };
  }, [stop]);

  const collectFor = useCallback(
    (
      durationMs: number,
      onProgress?: (pct: number) => void,
    ): Promise<SensorSample[]> => {
      return new Promise(async (resolve, reject) => {
        let cleanup: (() => void) | undefined;
        try {
          cleanup = await start();
        } catch (e) {
          reject(e);
          return;
        }
        const startAt = Date.now();
        const tick = setInterval(() => {
          const pct = Math.min(
            100,
            ((Date.now() - startAt) / durationMs) * 100,
          );
          onProgress?.(pct);
        }, 200);

        setTimeout(() => {
          clearInterval(tick);
          const data = [...bufferRef.current];
          stop();
          cleanup?.();
          resolve(data);
        }, durationMs);
      });
    },
    [start, stop],
  );

  return { collectFor, start, stop };
}
