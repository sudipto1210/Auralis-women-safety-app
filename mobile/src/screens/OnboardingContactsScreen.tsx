import React, { useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { Haptics } from "../components/Haptics";
import { Ionicons } from "../components/Ionicons";
import { Screen } from "../components/Screen";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { StepHeader } from "../components/StepHeader";
import { colors, radius, spacing } from "../theme";
import { api } from "../api/client";
import { useAuth } from "../store/AuthContext";
import type { ContactInput } from "../api/types";

const RELATIONSHIPS = [
  "family",
  "friend",
  "partner",
  "colleague",
  "neighbor",
  "other",
];

type ContactForm = { name: string; phone: string; relationship: string };

const empty = (): ContactForm => ({ name: "", phone: "", relationship: "" });
const digits = (value: string) => value.replace(/\D/g, "");
const isPhoneValid = (value: string) =>
  digits(value).length >= 10 && digits(value).length <= 15;

export function OnboardingContactsScreen() {
  const { user, refreshOnboarding } = useAuth();
  const [contacts, setContacts] = useState<ContactForm[]>([
    empty(),
    empty(),
    empty(),
    empty(),
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const firstName = user?.name?.split(" ")[0] || "there";

  const validCount = contacts.filter(
    (c) => c.name.trim().length >= 2 && isPhoneValid(c.phone) && c.relationship,
  ).length;

  const update = (i: number, field: keyof ContactForm, value: string) => {
    setContacts((prev) => {
      const next = [...prev];
      next[i] = {
        ...next[i],
        [field]: field === "phone" ? value.slice(0, 22) : value,
      };
      return next;
    });
  };

  const contactErrors = (contact: ContactForm) => {
    const touched = contact.name || contact.phone || contact.relationship;
    if (!touched) return [];
    const errors: string[] = [];
    if (contact.name.trim().length < 2) errors.push("Add a name.");
    if (!isPhoneValid(contact.phone)) errors.push("Use 10-15 phone digits.");
    if (!contact.relationship) errors.push("Choose a relationship.");
    return errors;
  };

  const submit = async () => {
    setError("");
    if (validCount < 4) {
      setError("Add four complete emergency contacts before continuing.");
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
      return;
    }
    setLoading(true);
    try {
      const payload: ContactInput[] = contacts
        .filter((c) => c.name && c.phone && c.relationship)
        .map((c, i) => ({
          name: c.name.trim(),
          phone: digits(c.phone),
          relationship: c.relationship,
          order: i + 1,
        }));
      await api("/api/onboarding/contacts", {
        method: "POST",
        body: JSON.stringify({ contacts: payload }),
      });
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      await refreshOnboarding();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save contacts");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Screen scroll>
      <StepHeader current={1} />
      <Text style={styles.greeting}>Hi {firstName}</Text>
      <Text style={styles.heading}>Who should we call if you need help?</Text>
      <Text style={styles.sub}>
        Add four trusted people. Keep numbers flexible: local, country code, or
        spaced formats are fine.
      </Text>
      <View style={styles.progressCard}>
        <View style={styles.progressTop}>
          <Text style={styles.progressText}>{validCount}/4 contacts ready</Text>
          <Ionicons
            name={validCount === 4 ? "checkmark-circle" : "people-outline"}
            size={20}
            color={validCount === 4 ? colors.success : colors.rose}
          />
        </View>
        <View style={styles.track}>
          <View
            style={[styles.fill, { width: `${(validCount / 4) * 100}%` }]}
          />
        </View>
      </View>

      {contacts.map((c, i) => (
        <Card key={i} title={`Emergency contact ${i + 1}`}>
          <TextInput
            style={styles.input}
            placeholder="Full name"
            placeholderTextColor={colors.textFaint}
            value={c.name}
            onChangeText={(v) => update(i, "name", v)}
          />
          <TextInput
            style={styles.input}
            placeholder="Phone number"
            placeholderTextColor={colors.textFaint}
            keyboardType="phone-pad"
            value={c.phone}
            onChangeText={(v) => update(i, "phone", v)}
          />
          <View style={styles.chips}>
            {RELATIONSHIPS.map((r) => (
              <Pressable
                key={r}
                onPress={() => {
                  Haptics.selectionAsync();
                  update(i, "relationship", r);
                }}
                style={[styles.chip, c.relationship === r && styles.chipOn]}
              >
                <Text
                  style={[
                    styles.chipText,
                    c.relationship === r && styles.chipTextOn,
                  ]}
                >
                  {r}
                </Text>
              </Pressable>
            ))}
          </View>
          {contactErrors(c).map((message) => (
            <Text key={message} style={styles.inlineError}>
              {message}
            </Text>
          ))}
        </Card>
      ))}

      {error ? (
        <View style={styles.errorBox}>
          <Ionicons
            name="alert-circle-outline"
            size={18}
            color={colors.danger}
          />
          <Text style={styles.error}>{error}</Text>
        </View>
      ) : null}
      <Button
        label={`Continue (${validCount}/4 ready)`}
        onPress={submit}
        disabled={validCount < 4}
        loading={loading}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  greeting: { fontSize: 14, color: colors.rose, fontWeight: "700" },
  heading: {
    fontSize: 24,
    fontWeight: "800",
    color: colors.text,
    marginTop: 4,
  },
  sub: {
    fontSize: 14,
    color: colors.textSoft,
    marginBottom: spacing.lg,
    lineHeight: 21,
  },
  progressCard: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  progressTop: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: spacing.sm,
  },
  progressText: { color: colors.text, fontWeight: "800" },
  track: {
    height: 8,
    backgroundColor: colors.bgDeep,
    borderRadius: radius.full,
    overflow: "hidden",
  },
  fill: {
    height: "100%",
    backgroundColor: colors.rose,
    borderRadius: radius.full,
  },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: 12,
    marginBottom: spacing.sm,
    fontSize: 15,
    backgroundColor: colors.bg,
    color: colors.text,
  },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  chipOn: { backgroundColor: colors.roseSoft, borderColor: colors.roseBorder },
  chipText: { fontSize: 12, color: colors.textSoft, fontWeight: "700" },
  chipTextOn: { color: colors.text },
  inlineError: { color: colors.warning, fontSize: 12, marginTop: spacing.xs },
  errorBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: colors.dangerSoft,
    borderRadius: radius.md,
    padding: spacing.sm,
    marginBottom: spacing.md,
  },
  error: { color: colors.text, flex: 1, fontSize: 13 },
});
