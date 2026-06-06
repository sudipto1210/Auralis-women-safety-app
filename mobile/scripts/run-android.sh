#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -z "${JAVA_HOME:-}" ] && [ -d "/home/v4u/Downloads/android-studio/jbr" ]; then
  export JAVA_HOME="/home/v4u/Downloads/android-studio/jbr"
fi

if [ ! -d "$ROOT/android" ]; then
  echo "Native android/ missing — running prebuild..."
  npm run prebuild -- --platform android
fi

if [ -n "${ANDROID_HOME:-}" ] && [ ! -f "$ROOT/android/local.properties" ]; then
  echo "sdk.dir=$ANDROID_HOME" > "$ROOT/android/local.properties"
fi

npm run android
