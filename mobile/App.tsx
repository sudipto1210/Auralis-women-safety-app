import "react-native-gesture-handler";
import { ActivityIndicator, StatusBar, View } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { AuthProvider } from "./src/store/AuthContext";
import { RootNavigator } from "./src/navigation/RootNavigator";
import { useSecurityCheck } from "./src/hooks/useSecurityCheck";
import { SecurityBlockScreen } from "./src/screens/SecurityBlockScreen";

/**
 * AppShell
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 * Wraps the real app in a security gate. On every cold start:
 *   1. Runs native integrity check (root, debugger, signature)
 *   2. Shows a loading spinner while checking
 *   3. Hard-blocks with SecurityBlockScreen if check fails
 *   4. Renders the normal app tree if check passes
 *
 * This runs BEFORE AuthProvider so a compromised device never
 * reaches any auth, sensor, or location logic.
 */
function AppShell() {
  const security = useSecurityCheck();

  // ── Loading ────────────────────────────────────────────────────────
  if (security.status === "checking") {
    return (
      <View
        style={{ flex: 1, backgroundColor: "#0d0a0e", alignItems: "center", justifyContent: "center" }}
      >
        <ActivityIndicator color="#c084fc" size="large" />
      </View>
    );
  }

  // ── Security failed (production: hard block, dev: show detail screen) ─
  if (security.status === "failed") {
    return <SecurityBlockScreen result={security.result} />;
  }

  // ── Passed or module unavailable → normal app ──────────────────────
  return (
    <>
      <AuthProvider>
        <RootNavigator />
        <StatusBar barStyle="light-content" backgroundColor="#100C10" />
      </AuthProvider>
    </>
  );
}

export default function App() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <AppShell />
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
