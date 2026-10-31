#!/usr/bin/env bash
# Run a local Home Assistant (no Docker) with this repo's integration loaded.
#
#   pip install homeassistant           # Python 3.13+/3.14, once
#   dev/run-local.sh                    # starts Home Assistant on :8123
#   python3 dev/seed.py                 # in a second terminal
#
# Home Assistant only loads integrations that live in its config directory, so this
# builds dev/.local-config containing links to the repo (edits apply after a restart).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CFG="${HA_CONFIG:-$ROOT/dev/.local-config}"

if ! command -v hass >/dev/null 2>&1; then
  echo "hass not found. Install Home Assistant first, e.g.: pip install homeassistant" >&2
  exit 1
fi

mkdir -p "$CFG/custom_components"
ln -sfn "$ROOT/dev/config/configuration.yaml" "$CFG/configuration.yaml"
ln -sfn "$ROOT/dev/config/dashboards" "$CFG/dashboards"
ln -sfn "$ROOT/custom_components/vehicle" "$CFG/custom_components/vehicle"
ln -sfn "$ROOT/dev/config/custom_components/fake_ai_task" "$CFG/custom_components/fake_ai_task"

echo "Config directory: $CFG"
echo "Next: python3 dev/seed.py   (login dev / dev, dashboard at /dashboard-vehicle)"
exec hass -c "$CFG"
