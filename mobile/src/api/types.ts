export type User = {
  email: string;
  name: string;
  picture?: string;
};

export type AuthResponse = {
  success: boolean;
  access_token: string;
  needs_onboarding: boolean;
  user: User;
  redirect: string;
};

export type OnboardingStatus = {
  needs_onboarding: boolean;
  contacts_saved: boolean;
  has_baseline: boolean;
  step: "contacts" | "calibration" | "complete";
  user_name?: string;
};

export type ContactInput = {
  name: string;
  phone: string;
  relationship: string;
  email?: string | null;
  order: number;
};

export type SensorSample = {
  ax: number;
  ay: number;
  az: number;
  gx: number;
  gy: number;
  gz: number;
  timestamp: number;
};

export type ThreatStatus = {
  state: string;
  score: number;
  monitoring_active: boolean;
  explanation?: { summary?: string };
};
