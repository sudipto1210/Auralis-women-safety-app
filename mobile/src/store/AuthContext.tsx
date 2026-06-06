import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  api,
  setToken,
  getToken,
  clearAllSecureStorage,
  registerUnauthorizedHandler,
} from "../api/client";
import type { AuthResponse, OnboardingStatus, User } from "../api/types";

type AuthState = {
  ready: boolean;
  user: User | null;
  onboardingStep: "contacts" | "calibration" | "complete" | null;
  signInWithGoogle: (idToken: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshOnboarding: () => Promise<OnboardingStatus | null>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [onboardingStep, setOnboardingStep] =
    useState<AuthState["onboardingStep"]>(null);

  // ── Shared signout logic ─────────────────────────────────────────────
  const performSignOut = useCallback(async () => {
    // clearAllSecureStorage wipes token + timestamp + API URL from Keychain
    await clearAllSecureStorage();
    setUser(null);
    setOnboardingStep(null);
  }, []);

  // ── Register 401 auto-signout handler ────────────────────────────────
  // Any API call that receives a 401 Unauthorized will invoke this handler,
  // automatically signing out the user without any extra code in each screen.
  useEffect(() => {
    registerUnauthorizedHandler(performSignOut);
  }, [performSignOut]);

  const refreshOnboarding = useCallback(async () => {
    try {
      const status = await api<OnboardingStatus>("/api/onboarding/status");
      if (status.needs_onboarding) {
        setOnboardingStep(
          status.step === "calibration" ? "calibration" : "contacts",
        );
      } else {
        setOnboardingStep("complete");
      }
      if (status.user_name && user) {
        setUser((u) => (u ? { ...u, name: status.user_name || u.name } : u));
      }
      return status;
    } catch {
      setOnboardingStep(null);
      return null;
    }
  }, [user]);

  const bootstrap = useCallback(async () => {
    const token = await getToken();
    if (!token) {
      setReady(true);
      return;
    }
    try {
      const me = await api<{
        email: string;
        name: string;
        picture?: string;
        needs_onboarding: boolean;
      }>("/api/mobile/me");
      setUser({ email: me.email, name: me.name, picture: me.picture });
      if (me.needs_onboarding) {
        const status = await refreshOnboarding();
        if (!status) setOnboardingStep("contacts");
      } else {
        setOnboardingStep("complete");
      }
    } catch {
      // Token is invalid/expired — wipe all stored credentials
      await clearAllSecureStorage();
      setUser(null);
      setOnboardingStep(null);
    } finally {
      setReady(true);
    }
  }, [refreshOnboarding]);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  const signInWithGoogle = useCallback(async (idToken: string) => {
    const res = await api<AuthResponse>(
      "/api/google-auth",
      {
        method: "POST",
        body: JSON.stringify({ credential: idToken }),
      },
      false,
    );
    await setToken(res.access_token);
    setUser(res.user);
    if (res.needs_onboarding) {
      const status = await api<OnboardingStatus>("/api/onboarding/status");
      setOnboardingStep(
        status.step === "calibration" ? "calibration" : "contacts",
      );
    } else {
      setOnboardingStep("complete");
    }
  }, []);

  // ── signOut: full credential wipe ────────────────────────────────────
  const signOut = useCallback(async () => {
    await performSignOut();
  }, [performSignOut]);

  const value = useMemo(
    () => ({
      ready,
      user,
      onboardingStep,
      signInWithGoogle,
      signOut,
      refreshOnboarding,
    }),
    [ready, user, onboardingStep, signInWithGoogle, signOut, refreshOnboarding],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside provider");
  return ctx;
}
