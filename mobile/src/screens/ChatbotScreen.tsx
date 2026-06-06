import React, { useRef, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Haptics } from "../components/Haptics";
import { Ionicons } from "../components/Ionicons";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { Screen } from "../components/Screen";
import type { RootStackParamList } from "../navigation/RootNavigator";
import { api } from "../api/client";
import { colors, radius, spacing } from "../theme";

type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
  threatContext?: string;
};

type ChatResponse = {
  reply?: string;
  message?: string;
  response?: string;
  threat_context?: string | { summary?: string; state?: string };
};

const prompts = ["I feel unsafe", "Find a safe route", "What should I do now?"];

const responseText = (data: ChatResponse) =>
  data.reply ||
  data.message ||
  data.response ||
  "I am here. Move toward light, stay visible, and use SOS if danger feels immediate.";

const contextText = (data: ChatResponse) => {
  const context = data.threat_context;
  if (!context) return undefined;
  if (typeof context === "string") return context;
  return context.summary || context.state;
};

export function ChatbotScreen() {
  const navigation =
    useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const scrollRef = useRef<ScrollView>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;
    setInput("");
    setError("");
    const userMessage: Message = {
      id: `${Date.now()}-user`,
      role: "user",
      text: trimmed,
    };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);
    await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    try {
      const data = await api<ChatResponse>("/api/chatbot", {
        method: "POST",
        body: JSON.stringify({ message: trimmed }),
      });
      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}-assistant`,
          role: "assistant",
          text: responseText(data),
          threatContext: contextText(data),
        },
      ]);
      requestAnimationFrame(() =>
        scrollRef.current?.scrollToEnd({ animated: true }),
      );
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not reach AURALIS assistant.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <Screen>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={styles.flex}
      >
        <View style={styles.header}>
          <Pressable style={styles.back} onPress={() => navigation.goBack()}>
            <Ionicons name="chevron-back" size={24} color={colors.text} />
          </Pressable>
          <View>
            <Text style={styles.title}>Safety Chat</Text>
            <Text style={styles.subtitle}>Steady guidance, fast choices.</Text>
          </View>
          <View style={styles.backPlaceholder} />
        </View>

        <ScrollView
          ref={scrollRef}
          style={styles.chat}
          contentContainerStyle={styles.chatContent}
          showsVerticalScrollIndicator={false}
        >
          {messages.length === 0 ? (
            <View style={styles.empty}>
              <Ionicons
                name="chatbubbles-outline"
                size={36}
                color={colors.rose}
              />
              <Text style={styles.emptyTitle}>
                Ask for help in plain language.
              </Text>
              <Text style={styles.emptyText}>
                The assistant can suggest next steps and include current threat
                context when available.
              </Text>
            </View>
          ) : (
            messages.map((message) => (
              <View
                key={message.id}
                style={[
                  styles.bubble,
                  message.role === "user"
                    ? styles.userBubble
                    : styles.assistantBubble,
                ]}
              >
                <Text
                  style={[
                    styles.bubbleText,
                    message.role === "user" && styles.userText,
                  ]}
                >
                  {message.text}
                </Text>
                {message.threatContext ? (
                  <View style={styles.contextBox}>
                    <Ionicons
                      name="shield-checkmark-outline"
                      size={15}
                      color={colors.success}
                    />
                    <Text style={styles.contextText}>
                      {message.threatContext}
                    </Text>
                  </View>
                ) : null}
              </View>
            ))
          )}
          {loading ? (
            <View style={[styles.bubble, styles.assistantBubble]}>
              <ActivityIndicator color={colors.rose} />
            </View>
          ) : null}
          {error ? (
            <View style={styles.errorBox}>
              <Ionicons
                name="alert-circle-outline"
                size={18}
                color={colors.danger}
              />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          ) : null}
        </ScrollView>

        <View style={styles.prompts}>
          {prompts.map((prompt) => (
            <Pressable
              key={prompt}
              style={styles.prompt}
              onPress={() => send(prompt)}
            >
              <Text style={styles.promptText}>{prompt}</Text>
            </Pressable>
          ))}
        </View>

        <View style={styles.composer}>
          <TextInput
            value={input}
            onChangeText={setInput}
            placeholder="Message AURALIS"
            placeholderTextColor={colors.textFaint}
            style={styles.input}
            multiline
          />
          <Pressable
            style={[styles.send, !input.trim() && styles.sendDisabled]}
            onPress={() => send(input)}
            disabled={!input.trim() || loading}
          >
            <Ionicons name="send" size={19} color={colors.text} />
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing.md,
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
  title: {
    color: colors.text,
    fontSize: 22,
    fontWeight: "900",
    textAlign: "center",
  },
  subtitle: {
    color: colors.textMuted,
    fontSize: 12,
    textAlign: "center",
    marginTop: 2,
  },
  chat: { flex: 1 },
  chatContent: { paddingVertical: spacing.md, gap: spacing.sm },
  empty: {
    minHeight: 320,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing.lg,
  },
  emptyTitle: {
    color: colors.text,
    fontSize: 18,
    fontWeight: "900",
    textAlign: "center",
    marginTop: spacing.md,
  },
  emptyText: {
    color: colors.textSoft,
    textAlign: "center",
    lineHeight: 21,
    marginTop: spacing.sm,
  },
  bubble: { maxWidth: "84%", borderRadius: radius.lg, padding: spacing.md },
  userBubble: { alignSelf: "flex-end", backgroundColor: colors.rose },
  assistantBubble: {
    alignSelf: "flex-start",
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
  },
  bubbleText: { color: colors.text, lineHeight: 21 },
  userText: { color: "#fff", fontWeight: "600" },
  contextBox: {
    flexDirection: "row",
    gap: 7,
    marginTop: spacing.sm,
    paddingTop: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  contextText: {
    flex: 1,
    color: colors.textSoft,
    fontSize: 12,
    lineHeight: 17,
  },
  errorBox: {
    flexDirection: "row",
    alignSelf: "center",
    gap: 8,
    backgroundColor: colors.dangerSoft,
    borderRadius: radius.md,
    padding: spacing.sm,
    marginTop: spacing.sm,
  },
  errorText: { color: colors.text, flex: 1, fontSize: 13 },
  prompts: { flexDirection: "row", gap: 8, marginBottom: spacing.sm },
  prompt: {
    flex: 1,
    borderRadius: radius.full,
    borderWidth: 1,
    borderColor: colors.border,
    paddingVertical: 8,
    paddingHorizontal: 10,
  },
  promptText: {
    color: colors.textSoft,
    fontSize: 11,
    fontWeight: "800",
    textAlign: "center",
  },
  composer: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: spacing.sm,
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.sm,
  },
  input: {
    flex: 1,
    minHeight: 38,
    maxHeight: 110,
    color: colors.text,
    paddingHorizontal: spacing.sm,
    paddingTop: 9,
  },
  send: {
    width: 42,
    height: 42,
    borderRadius: 21,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.rose,
  },
  sendDisabled: { opacity: 0.45 },
});
