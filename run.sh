#!/usr/bin/env bash
set -e
# Delegate execution directly to the restructured backend/run.sh script
exec "$(dirname "$0")/backend/run.sh" "$@"
