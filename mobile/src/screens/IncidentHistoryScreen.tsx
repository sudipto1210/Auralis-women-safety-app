import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Haptics } from "../components/Haptics";
import { Ionicons } from "../components/Ionicons";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { Screen } from "../components/Screen";
import { Button } from "../components/Button";
import type { RootStackParamList } from "../navigation/RootNavigator";
import { api } from "../api/client";
import { colors, radius, shadow, spacing } from "../theme";

type Incident = {
  id: string | number;
  severity?: string;
  level?: string;
  summary?: string;
  description?: string;
  created_at?: string;
  timestamp?: string;
  false_alarm?: boolean;
};

const severityColor = (severity?: string) => {
  const value = (severity || "").toUpperCase();
  if (value === "CRITICAL" || value === "HIGH") return colors.danger;
  if (value === "MEDIUM") return colors.warning;
  return colors.success;
};

const toIncidents = (data: unknown): Incident[] => {
  if (Array.isArray(data)) return data as Incident[];
  if (
    data &&
    typeof data === "object" &&
    Array.isArray((data as { incidents?: unknown }).incidents)
  ) {
    return (data as { incidents: Incident[] }).incidents;
  }
  return [];
};

const formatDate = (value?: string) => {
  if (!value) return "Recent";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

export function IncidentHistoryScreen() {
  const navigation =
    useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [feedbackId, setFeedbackId] = useState<string | number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api<unknown>("/api/incidents");
      setIncidents(toIncidents(data));
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not load incident history.",
      );
      setIncidents([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const markFalseAlarm = async (incident: Incident) => {
    setFeedbackId(incident.id);
    try {
      await api(`/api/incidents/${incident.id}/feedback`, {
        method: "POST",
        body: JSON.stringify({ feedback: "false_alarm", false_alarm: true }),
      });
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      setIncidents((prev) =>
        prev.map((item) =>
          item.id === incident.id ? { ...item, false_alarm: true } : item,
        ),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save feedback.");
    } finally {
      setFeedbackId(null);
    }
  };

  return (
    <Screen scroll>
      <View style={styles.header}>
        <Pressable style={styles.back} onPress={() => navigation.goBack()}>
          <Ionicons name="chevron-back" size={24} color={colors.text} />
        </Pressable>
        <Text style={styles.title}>Incident History</Text>
        <Pressable style={styles.back} onPress={load}>
          <Ionicons name="refresh" size={21} color={colors.textSoft} />
        </Pressable>
      </View>

      {loading ? (
        <View style={styles.state}>
          <ActivityIndicator color={colors.rose} />
          <Text style={styles.stateText}>Loading incident timeline...</Text>
        </View>
      ) : error ? (
        <View style={styles.state}>
          <Ionicons
            name="alert-circle-outline"
            size={32}
            color={colors.warning}
          />
          <Text style={styles.stateText}>{error}</Text>
          <Button label="Try again" onPress={load} style={styles.stateButton} />
        </View>
      ) : incidents.length === 0 ? (
        <View style={styles.state}>
          <Ionicons
            name="shield-checkmark-outline"
            size={36}
            color={colors.success}
          />
          <Text style={styles.emptyTitle}>No incidents recorded</Text>
          <Text style={styles.stateText}>Your timeline is clear.</Text>
        </View>
      ) : (
        <View style={styles.timeline}>
          {incidents.map((incident, index) => {
            const severity = (
              incident.severity ||
              incident.level ||
              "LOW"
            ).toUpperCase();
            const color = severityColor(severity);
            return (
              <View key={incident.id || index} style={styles.timelineRow}>
                <View style={styles.markerColumn}>
                  <View style={[styles.marker, { backgroundColor: color }]} />
                  {index < incidents.length - 1 ? (
                    <View style={styles.line} />
                  ) : null}
                </View>
                <View style={styles.incidentCard}>
                  <View style={styles.incidentTop}>
                    <View style={[styles.severity, { backgroundColor: color }]}>
                      <Text style={styles.severityText}>{severity}</Text>
                    </View>
                    <Text style={styles.date}>
                      {formatDate(incident.created_at || incident.timestamp)}
                    </Text>
                  </View>
                  <Text style={styles.summary}>
                    {incident.summary ||
                      incident.description ||
                      "Threat event recorded."}
                  </Text>
                  {incident.false_alarm ? (
                    <Text style={styles.falseAlarm}>Marked as false alarm</Text>
                  ) : (
                    <Pressable
                      style={styles.falseButton}
                      onPress={() => markFalseAlarm(incident)}
                      disabled={feedbackId === incident.id}
                    >
                      <Ionicons
                        name="flag-outline"
                        size={16}
                        color={colors.warning}
                      />
                      <Text style={styles.falseButtonText}>
                        {feedbackId === incident.id
                          ? "Saving..."
                          : "False alarm"}
                      </Text>
                    </Pressable>
                  )}
                </View>
              </View>
            );
          })}
        </View>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing.lg,
  },
  back: {
    width: 42,
    height: 42,
    borderRadius: 21,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
  },
  title: { color: colors.text, fontSize: 22, fontWeight: "900" },
  state: {
    minHeight: 320,
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.md,
  },
  stateText: { color: colors.textSoft, textAlign: "center", lineHeight: 21 },
  emptyTitle: { color: colors.text, fontSize: 18, fontWeight: "900" },
  stateButton: { width: 180 },
  timeline: { paddingBottom: spacing.lg },
  timelineRow: { flexDirection: "row", gap: spacing.md },
  markerColumn: { width: 22, alignItems: "center" },
  marker: { width: 14, height: 14, borderRadius: 7, marginTop: spacing.md },
  line: { flex: 1, width: 2, backgroundColor: colors.border, marginTop: 5 },
  incidentCard: {
    flex: 1,
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.md,
    ...shadow.card,
  },
  incidentTop: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: spacing.sm,
  },
  severity: {
    borderRadius: radius.full,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  severityText: { color: "#fff", fontSize: 11, fontWeight: "900" },
  date: { color: colors.textMuted, fontSize: 12, fontWeight: "700" },
  summary: { color: colors.textSoft, lineHeight: 21, marginTop: spacing.md },
  falseButton: {
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
    borderRadius: radius.full,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: 10,
    paddingVertical: 7,
    marginTop: spacing.md,
  },
  falseButtonText: { color: colors.textSoft, fontWeight: "800", fontSize: 12 },
  falseAlarm: {
    color: colors.success,
    fontSize: 12,
    fontWeight: "800",
    marginTop: spacing.md,
  },
});
