/**
 * babel.config.js
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 * Production build: babel-plugin-transform-remove-console strips ALL
 * console.log / console.warn / console.error calls from the JS bundle
 * at transpile time. This means even third-party packages cannot leak
 * data to Android logcat in a release APK.
 *
 * Our own code uses src/utils/logger.ts which is already a no-op in
 * production — this plugin is a defence-in-depth safety net.
 */

const isProduction = process.env.NODE_ENV === "production";

module.exports = {
  presets: ["module:@react-native/babel-preset"],
  plugins: [
    // ── Environment variables (.env → @env imports) ─────────────────
    [
      "module:react-native-dotenv",
      {
        moduleName: "@env",
        path: ".env",
        blacklist: null,
        whitelist: null,
        safe: false,
        allowUndefined: true,
      },
    ],

    // ── Production: strip all console.* calls ────────────────────────
    // Applied ONLY in production builds (NODE_ENV=production).
    // In development (Metro dev server), console output is kept.
    ...(isProduction
      ? [
          [
            "transform-remove-console",
            {
              // Remove all console methods including warn, error, info
              exclude: [],
            },
          ],
        ]
      : []),
  ],
};
