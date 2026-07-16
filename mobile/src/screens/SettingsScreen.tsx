import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { Haptics } from "../components/Haptics";
import { Ionicons } from "../components/Ionicons";
import { Screen } from "../components/Screen";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import type { RootStackParamList } from "../navigation/RootNavigator";
import { colors, radius, spacing } from "../theme";
import { useAuth } from "../store/AuthContext";

export function SettingsScreen() {
  const navigation =
    useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const { user, signOut } = useAuth();

  const rows = [
    {
      label: "Emergency contacts",
      icon: "people-outline" as const,
      onPress: () => navigation.navigate("OnboardingContacts"),
    },
    {
      label: "Recalibrate walk",
      icon: "walk-outline" as const,
      onPress: () => navigation.navigate("OnboardingWalk"),
    },
    {
      label: "Incident history",
      icon: "time-outline" as const,
      onPress: () => navigation.navigate("IncidentHistory"),
    },
    {
      label: "Data collection (ML)",
      icon: "clipboard-outline" as const,
      onPress: () => navigation.navigate("DataCollection"),
    },
  ];

  return (
    <Screen scroll>
      <View style={styles.header}>
        <Pressable style={styles.back} onPress={() => navigation.goBack()}>
          <Ionicons name="chevron-back" size={24} color={colors.text} />
        </Pressable>
        <Text style={styles.title}>Settings</Text>
        <View style={styles.backPlaceholder} />
      </View>

      <Card>
        <View style={styles.profileRow}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>
              {(user?.name || "A").charAt(0).toUpperCase()}
            </Text>
          </View>
          <View style={styles.profileCopy}>
            <Text style={styles.name}>{user?.name || "AURALIS user"}</Text>
            <Text style={styles.email}>
              {user?.email || "Signed in securely"}
            </Text>
          </View>
        </View>
      </Card>

      <View style={styles.menu}>
        {rows.map((row) => (
          <Pressable
            key={row.label}
            style={styles.menuRow}
            onPress={async () => {
              await Haptics.selectionAsync();
              row.onPress();
            }}
          >
            <View style={styles.menuIcon}>
              <Ionicons name={row.icon} size={20} color={colors.rose} />
            </View>
            <Text style={styles.menuLabel}>{row.label}</Text>
            <Ionicons
              name="chevron-forward"
              size={19}
              color={colors.textMuted}
            />
          </Pressable>
        ))}
      </View>

      <Card>
        <View style={styles.versionRow}>
          <Text style={styles.versionLabel}>App version</Text>
          <Text style={styles.versionValue}>1.0.0</Text>
        </View>
      </Card>

      <Button
        label="Sign out"
        variant="danger"
        onPress={async () => {
          await Haptics.notificationAsync(
            Haptics.NotificationFeedbackType.Warning,
          );
          await signOut();
        }}
      />
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
  backPlaceholder: { width: 42 },
  title: { fontSize: 24, fontWeight: "800", color: colors.text },
  profileRow: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.roseSoft,
    borderWidth: 1,
    borderColor: colors.roseBorder,
  },
  avatarText: { color: colors.text, fontSize: 22, fontWeight: "900" },
  profileCopy: { flex: 1 },
  name: { color: colors.text, fontSize: 17, fontWeight: "800" },
  email: { color: colors.textMuted, fontSize: 13, marginTop: 3 },
  menu: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    overflow: "hidden",
    marginBottom: spacing.md,
  },
  menuRow: {
    minHeight: 62,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    paddingHorizontal: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  menuIcon: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.roseSoft,
  },
  menuLabel: { flex: 1, color: colors.text, fontSize: 15, fontWeight: "700" },
  versionRow: { flexDirection: "row", justifyContent: "space-between" },
  versionLabel: { color: colors.textSoft, fontWeight: "700" },
  versionValue: { color: colors.textMuted, fontWeight: "700" },
});
