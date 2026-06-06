# AURALIS Mobile — Full Revamp Agent Instructions

> **Your mission**: Completely revamp and redesign the AURALIS React Native mobile app into a polished, production-quality safety application. The result must feel like a $50M startup's flagship product — not AI slop. Every screen must be intentionally designed, every animation purposeful, every interaction smooth. Read this entire document before writing a single line of code.

---

## 1. UNDERSTAND THE PRODUCT FIRST

AURALIS is a **women's safety app**. It protects people through:
- **IMU sensor fusion**: Accelerometer + gyroscope at 50Hz detect falls, struggles, grabs
- **Audio distress analysis**: Microphone metering extracts energy/pitch features to detect screams and distress
- **Continuous GPS tracking**: Live location shared with backend during active monitoring
- **One-tap SOS**: Instantly notifies all emergency contacts with GPS coordinates
- **AI chatbot**: Safety assistant that monitors threat status and provides guidance
- **Safe places map**: Finds nearby hospitals, police stations, public spaces within 5km

The **emotional context** matters: This app's user is potentially in danger. The UI must feel **protective, calm, and trustworthy** — not flashy for the sake of flashy. Think Calm app meets Apple Health meets emergency dispatch software.

---

## 2. CURRENT CODEBASE MAP

```
mobile/
├── App.tsx                           # Root: GestureHandler → SafeArea → AuthProvider → Navigator
├── index.ts                          # AppRegistry.registerComponent entry point
├── package.json                      # React 18.3.1, RN 0.76.9 (Pure RN CLI)
├── tsconfig.json                     # strict mode, RN CLI compiler settings
├── .env                              # GOOGLE_CLIENT_ID, API_URL (reads via react-native-dotenv)
├── metro.config.js                   # Standard RN CLI Metro configuration
├── babel.config.js                   # Babel config with module:@react-native/babel-preset and dotenv
├── android/                          # Native Android workspace (gradle, properties, sources)
└── src/
    ├── config.ts                     # getApiUrl(), getGoogleClientId() from dotenv
    ├── theme.ts                      # colors (dark neon palette), spacing, radius tokens
    ├── api/
    │   ├── client.ts                 # api<T>() fetch wrapper, Keychain token management, AsyncStorage URL, ApiError class
    │   └── types.ts                  # User, AuthResponse, OnboardingStatus, ContactInput, SensorSample, ThreatStatus
    ├── store/
    │   └── AuthContext.tsx           # AuthProvider with signInWithGoogle, signOut, refreshOnboarding, bootstrap
    ├── navigation/
    │   └── RootNavigator.tsx         # Auth-aware stack: Login → OnboardingContacts → OnboardingWalk → Home+Settings
    ├── hooks/
    │   ├── useMotionSampler.ts       # collectFor(durationMs) — calibration with react-native-sensors
    │   └── useMonitoring.ts          # useMonitoring(active) — react-native-sensors + geolocation + sound-level
    ├── components/
    │   ├── Screen.tsx                # SafeAreaView + optional ScrollView wrapper
    │   ├── Button.tsx                # primary/secondary/ghost/danger variants with loading state
    │   ├── Card.tsx                  # Bordered container with optional title
    │   ├── Haptics.ts                # Compatibility wrapper for react-native-haptic-feedback
    │   ├── Ionicons.tsx              # Compatibility wrapper for react-native-vector-icons
    │   └── StepHeader.tsx            # 4-step progress dots for onboarding ("You", "People", "Your walk", "Ready")
    └── screens/
        ├── LoginScreen.tsx           # Native Google Sign-In + server URL config
        ├── OnboardingContactsScreen.tsx  # 4 emergency contacts with relationship chips
        ├── OnboardingWalkScreen.tsx   # 2-phase walk calibration (30s normal + 15s brisk)
        ├── HomeScreen.tsx            # Threat badge, SOS button, monitoring toggle
        └── SettingsScreen.tsx        # Server URL editor (bare minimum)
```

---

## 3. BACKEND API CONTRACT

The Flask backend runs at the URL in `.env` (`EXPO_PUBLIC_API_URL`). All authenticated requests use `Authorization: Bearer <token>` header. The `api<T>()` helper in `client.ts` handles this automatically.

### Auth & Onboarding
| Method | Endpoint | Request Body | Response |
|--------|----------|-------------|----------|
| POST | `/api/google-auth` | `{ credential: "<google_id_token>" }` | `{ success, access_token, needs_onboarding, user: {email,name,picture}, redirect }` |
| GET | `/api/mobile/me` | — | `{ email, name, picture?, needs_onboarding }` |
| GET | `/api/onboarding/status` | — | `{ needs_onboarding, contacts_saved, has_baseline, step: "contacts"|"calibration"|"complete", user_name? }` |
| POST | `/api/onboarding/contacts` | `{ contacts: [{name, phone, relationship, order}] }` | `{ success }` |
| POST | `/api/motion_baseline` | `{ normal_readings: SensorSample[], elevated_readings: SensorSample[] }` | `{ success, profile }` |
| POST | `/api/onboarding/finish` | `{}` | `{ success }` |

### Monitoring & Sensors
| Method | Endpoint | Request Body | Response |
|--------|----------|-------------|----------|
| POST | `/api/start_monitoring` | `{}` | `{ status: "monitoring_started" }` |
| POST | `/api/stop_monitoring` | `{}` | `{ status: "monitoring_stopped" }` |
| POST | `/api/motion_data` | `{ sensor_window: SensorSample[] }` | `{ status, motion_score, events[] }` |
| POST | `/api/audio_data` | `{ audio_features: {energy, zcr_mean, pitch, ...mfccs} }` | `{ status, audio_score, environment_class }` |
| POST | `/api/update_location` | `{ lat, lng }` | `{ status }` |
| GET | `/api/threat_status` | — | `{ state: "LOW"|"MEDIUM"|"HIGH"|"CRITICAL", score: 0-1, monitoring_active, explanation?: {summary} }` |

### Safety Features
| Method | Endpoint | Request Body | Response |
|--------|----------|-------------|----------|
| POST | `/api/trigger_sos` | `{}` | `{ status, contacts_notified }` |
| POST | `/api/false_alert` | `{}` | `{ status, incident_id }` |
| GET | `/api/safe_places?lat=X&lng=Y` | — | `{ places: [{name, type, lat, lng, distance, rating}] }` |
| POST | `/api/chatbot` | `{ message: "..." }` | `{ response, threat_context? }` |
| POST | `/api/chatbot/auto_alert` | `{}` | `{ alerted, contacts }` |
| GET | `/api/incidents` | — | `{ incidents: [{id, timestamp, type, threat_level, score}] }` |
| POST | `/api/incidents/<id>/feedback` | `{ is_false_alarm: bool }` | `{ status }` |

### SensorSample Type
```typescript
{ ax: number, ay: number, az: number, gx: number, gy: number, gz: number, timestamp: number }
```

---

## 4. USER FLOW — THE COMPLETE JOURNEY

Design for this exact path. Each transition should feel intentional and guided.

```
┌─────────────────────────────────────────────────────────────┐
│  APP LAUNCH                                                  │
│  ├── Has stored token? → Bootstrap (GET /api/mobile/me)      │
│  │   ├── Token valid, onboarding complete → HOME             │
│  │   ├── Token valid, needs onboarding → ONBOARDING          │
│  │   └── Token invalid → clear token → LOGIN                 │
│  └── No token → LOGIN                                        │
├─────────────────────────────────────────────────────────────┤
│  SCREEN 1: LOGIN                                             │
│  • Beautiful branded splash/hero area                        │
│  • Server URL field (for dev/LAN config)                     │
│  • "Continue with Google" button                             │
│  • Error handling with clear messaging                       │
├─────────────────────────────────────────────────────────────┤
│  SCREEN 2: ONBOARDING — EMERGENCY CONTACTS                   │
│  • Step indicator: [1] Contacts → [2] Walk → [3] Ready       │
│  • Personal greeting: "Hi {name}"                            │
│  • 4 contact cards: name, 10-digit phone, relationship chip  │
│  • Relationship options: family, friend, partner, colleague,  │
│    neighbor, other                                           │
│  • Validation: all 4 required before "Continue"              │
│  • POST /api/onboarding/contacts → refreshOnboarding()       │
├─────────────────────────────────────────────────────────────┤
│  SCREEN 3: ONBOARDING — WALK CALIBRATION                     │
│  • Step indicator shows step 2 active                        │
│  • Phase 1: "Walk normally" — 30 seconds of IMU recording    │
│  • Phase 2: "Walk briskly" — 15 seconds of IMU recording     │
│  • Live progress bar + countdown timer                       │
│  • Pulsing animation during recording                        │
│  • POST /api/motion_baseline with both readings              │
│  • POST /api/onboarding/finish                               │
│  • "You're ready" confirmation → navigates to HOME           │
├─────────────────────────────────────────────────────────────┤
│  SCREEN 4: HOME (Main Dashboard)                             │
│  • Greeting: "Hello, {firstName}"                            │
│  • Threat status badge (LOW/MEDIUM/HIGH/CRITICAL + score)    │
│  • SOS button — large, prominent, unmissable                 │
│  • Monitoring toggle (Start/Stop)                            │
│  │   When active, the useMonitoring hook:                    │
│  │   ├── POSTs /api/start_monitoring                         │
│  │   ├── Starts Geolocation.watchPosition (every 15s)        │
│  │   ├── Starts Accelerometer + Gyroscope at 50Hz            │
│  │   ├── Flushes motion buffer every 5s to /api/motion_data  │
│  │   ├── Starts SoundLevel monitoring                        │
│  │   └── Sends audio features every 2s to /api/audio_data    │
│  • Status summary card (from threat_status.explanation)       │
│  • Settings gear → SETTINGS                                  │
│  • Sign out button                                           │
├─────────────────────────────────────────────────────────────┤
│  SCREEN 5: SETTINGS                                          │
│  • Server URL editor                                         │
│  • (Currently very bare — expand this)                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. WHAT IS WRONG WITH THE CURRENT APP (FIX ALL OF THESE)

### Design Problems
1. **Screens feel like placeholder prototypes** — minimal layout, no visual hierarchy, no breathing room
2. **No loading states during bootstrap** — just a centered spinner, feels broken
3. **HomeScreen is a vertical stack of random elements** — no information architecture
4. **SOS button doesn't feel urgent enough** — needs to be the dominant element, always reachable
5. **Threat badge is just a colored rectangle** — needs visual gravitas, perhaps animated
6. **OnboardingContactsScreen has no visual warmth** — it's cold form fields
7. **OnboardingWalkScreen's "footsteps emoji" animation is amateur** — replace with proper animated visuals
8. **SettingsScreen is a single text field** — embarrassingly sparse
9. **No empty states, no illustrations, no visual feedback on actions**
10. **StepHeader dots are tiny and unclear** — users won't understand where they are

### UX Problems
1. **No way to access Safe Places map from the app** — the API exists but there's no screen for it
2. **No chatbot screen** — the AI safety assistant API exists but has no UI
3. **No incident history** — `/api/incidents` exists but isn't displayed
4. **No false alarm button** — `/api/false_alert` exists but there's no way to trigger it
5. **Monitoring state isn't visually clear** — user can't tell what sensors are active
6. **No confirmation dialog for SOS** — accidental taps could spam contacts
7. **Walk calibration gives no feedback about data quality**
8. **Contact form doesn't clearly show which fields are invalid**

### Technical Problems
1. **Android colors.xml and styles.xml splash/status bar colors should match dark theme (`#100C10`)**
2. **No Animated API usage for threat level transitions**
3. **No error boundaries** — crashes show white screen
4. **Phone number validation is US-centric (10 digits)** — make it flexible

---

## 6. DESIGN SYSTEM REQUIREMENTS

### Color Philosophy
The current dark palette in `theme.ts` is a starting point. Refine it:
- **Background**: Deep dark with subtle warm undertones (not pure black — feels dead)
- **Cards/Surfaces**: Slightly elevated with subtle border glow
- **Accent (Rose/Pink)**: Use for CTAs, active states, brand identity
- **Success (Cyan/Teal)**: LOW threat, safe states, positive confirmations
- **Warning (Amber)**: MEDIUM threat, calibration, pending states
- **Danger (Red)**: HIGH/CRITICAL threat, SOS, errors
- **Text hierarchy**: Bright white → muted lavender → dim purple-grey

### Typography
- Use system fonts but with intentional weight hierarchy
- Headings: Bold 800, large sizes for impact
- Body: Regular 400, comfortable reading size (15-16px)
- Captions: Small, muted, 12px for hints
- Numbers (scores, timers): Use `fontVariant: ['tabular-nums']` for stability

### Spacing & Layout
- Use consistent spacing tokens from `theme.ts`
- Generous padding — this is a safety app, not a dense data dashboard
- Cards should breathe — don't stack elements without margin
- Use `SafeAreaView` properly on all screens

### Animation Principles
- **Meaningful, not decorative**: Animations should communicate state changes
- **Threat pulse**: The threat badge should subtly pulse when monitoring is active
- **SOS ripple**: SOS button should have a faint concentric ripple animation
- **Progress bars**: Smooth easing on calibration progress
- **Screen transitions**: Use `slide_from_right` for forward navigation, `slide_from_bottom` for modals
- **Haptics on key actions**: SOS trigger, monitoring toggle, calibration milestones

---

## 7. NEW SCREENS & FEATURES TO BUILD

### 7a. Safe Places Map Screen
- Access from HomeScreen via a "Safe Places" card or navigation button
- Uses `react-native-geolocation-service` to get current position
- Calls `GET /api/safe_places?lat=X&lng=Y`
- Display results as a scrollable list (map integration is optional — list-first is fine)
- Each place shows: name, type (hospital/police/etc), distance, rating
- Tapping a place should open native maps for directions

### 7b. AI Chatbot Screen
- Access from HomeScreen via a chat icon or card
- Full chat interface with message bubbles
- User messages on right (rose tint), bot responses on left (card background)
- Text input with send button at bottom
- POST `/api/chatbot` with `{ message }`, display `response`
- Show threat context from response if available
- Quick-action chips for common safety questions

### 7c. Incident History Screen
- Access from HomeScreen or Settings
- GET `/api/incidents` — display as a timeline/list
- Each incident shows: timestamp, type, threat level, score
- Allow user to mark false alarms: POST `/api/incidents/<id>/feedback`
- Color-coded by severity

### 7d. Enhanced Settings Screen
Expand beyond just server URL:
- **Account section**: User name, email, profile picture
- **Server URL**: Keep the existing config
- **Emergency contacts**: Quick link to edit/view contacts (or re-run contact onboarding)
- **Re-calibrate walk**: Button to re-run walk calibration
- **Incident history**: Link to incident history screen
- **About/Version**: App version, credits
- **Sign out**: Move sign-out here from HomeScreen (keep it on HomeScreen too as secondary)

---

## 8. HOMESCREEN REDESIGN SPEC

The HomeScreen is the heart of the app. It should be a **command center**, not a plain list.

```
┌──────────────────────────────────┐
│  Hello, {name}           ⚙ (gear) │
│  Your safety is our priority      │
│                                    │
│  ┌──────────────────────────────┐ │
│  │  THREAT LEVEL: LOW           │ │
│  │  ██████████░░░░  12% risk    │ │
│  │  "All systems normal"        │ │
│  └──────────────────────────────┘ │
│                                    │
│  ┌──────────────────────────────┐ │
│  │         🆘  S O S            │ │
│  │    Tap to alert contacts     │ │
│  └──────────────────────────────┘ │
│                                    │
│  ┌─ Monitoring ─────────────────┐ │
│  │  ● Sensors    ● Audio        │ │
│  │  ● GPS        ● Active 2m    │ │
│  │  [  Stop Monitoring  ]       │ │
│  └──────────────────────────────┘ │
│                                    │
│  ┌──────┐  ┌──────┐  ┌──────┐   │
│  │ Safe │  │ Chat │  │ Hist │   │
│  │Places│  │ Bot  │  │ ory  │   │
│  └──────┘  └──────┘  └──────┘   │
└──────────────────────────────────┘
```

Key elements:
- **Threat badge** at top — color-coded, shows score as progress bar, includes summary text
- **SOS button** — massive, impossible to miss, with confirmation dialog before triggering
- **Monitoring card** — shows what's active (sensors, audio, GPS), elapsed time, toggle button
- **Quick-access grid** — 3 cards linking to Safe Places, Chatbot, Incident History
- **Sign out** at bottom (ghost style) or in settings

---

## 9. IMPLEMENTATION RULES

### DO:
- Read every existing file before modifying it
- Keep the existing `api/client.ts` and `api/types.ts` — they work correctly (integrated with `react-native-keychain` and `AsyncStorage`)
- Keep the `store/AuthContext.tsx` — the auth flow is solid
- Keep the hooks (`useMonitoring.ts`, `useMotionSampler.ts`) — they handle real sensor work correctly (using `react-native-sensors`, `react-native-geolocation-service`, and `react-native-sound-level`)
- Extend `types.ts` if you need new API response types
- Use `React.Animated` or `LayoutAnimation` for animations (already available, no new deps needed)
- Use `react-native-haptic-feedback` for tactile feedback on critical actions (via `Haptics` component wrapper)
- Use `Ionicons` from `react-native-vector-icons/Ionicons` for all icons (via `Ionicons` component wrapper)
- Use `react-native-linear-gradient` for gradient backgrounds
- Add proper TypeScript types for all new code
- Test that `npx tsc --noEmit` passes after all changes

### DO NOT:
- Do NOT reinstall Expo packages or use Expo-specific runtime code
- Do NOT change the backend API — it's a separate Flask app, treat treat it as a black box
- Do NOT remove or break the Google Sign-In flow (integrated with `@react-native-google-signin/google-signin`)
- Do NOT change the sensor pipeline logic in `useMonitoring.ts` — the sensor math is correct (scaling accelerometer values by 1/9.80665)
- Do NOT change the walk calibration logic in `useMotionSampler.ts` — it matches what the backend expects (scaling accelerometer values by 1/9.80665)
- Do NOT use web-specific APIs — this runs on native Android/iOS
- Do NOT use placeholder images — use icons and gradients for visual elements
- Do NOT make generic "tech startup" UI — this is a safety product for women
- Do NOT create AI slop — every design decision should be intentional and justified

### Navigation Updates:
The `RootNavigator.tsx` currently has these screens: Login, OnboardingContacts, OnboardingWalk, Home, Settings. You will need to add: SafePlaces, Chatbot, IncidentHistory (accessible from Home, push-navigated).

### File Organization:
- New screens go in `src/screens/`
- New components go in `src/components/`
- New hooks go in `src/hooks/`
- Extend `types.ts` for new API response shapes
- Keep `theme.ts` as the single source of truth for design tokens

---

## 10. QUALITY BAR

Before you consider the revamp complete, verify:

- [x] `npx tsc --noEmit` passes with zero errors
- [x] Every screen handles loading, error, and empty states
- [x] SOS button has a confirmation dialog (e.g., "Are you sure? This will alert all contacts")
- [x] Walk calibration shows clear phase indicators and countdown
- [x] Contact form validates properly and shows inline errors
- [x] Threat badge animates between state changes
- [x] Monitoring state is clearly visible with active sensor indicators
- [x] Safe Places screen loads and displays results
- [x] Chatbot screen sends and receives messages
- [x] Incident History screen shows past events
- [x] Settings screen has meaningful options (not just server URL)
- [x] All hardcoded colors use theme tokens
- [x] Haptic feedback fires on SOS, monitoring toggle, calibration events
- [x] StatusBar style is "light" (dark background throughout)
- [x] Android splash/status bar configurations match the dark theme (`#100C10`)
- [x] No dead-end screens — every screen has navigation back or forward
- [x] Gesture-based back navigation works on all stack screens
- [x] React Native CLI native Android debug builds compile successfully (`./gradlew assembleDebug`)
- [x] React Native CLI native Android release builds compile successfully (`./gradlew assembleRelease`)

---

## 11. FINAL PHILOSOPHY

This app might be the last thing someone uses before an emergency. Design like it matters. Make the SOS button findable in 0.5 seconds. Make the monitoring state crystal clear at a glance. Make the onboarding fast but thorough. Make the threat status informative but not anxiety-inducing when things are safe.

**Premium ≠ overdesigned. Premium = every pixel earns its place.**

Build something you'd trust your sister to carry at night.
