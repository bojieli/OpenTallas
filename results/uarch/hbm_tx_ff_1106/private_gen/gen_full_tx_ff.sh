#!/usr/bin/env bash
# Prepared only: execute after root source/GEN authorization. No physical run.
set -euo pipefail
repo=${1:?clean approved generator checkout containing ot_pdie_serdes_tx__ff}
views=${2:?owner-provided views JSON for the approved same tall TX slot}
out=${3:?fresh private output directory on verified dedicated scratch}
if [[ -e "$out" ]]; then
  echo "Refusing existing output: use a fresh private GEN directory" >&2
  exit 2
fi
python3 "$repo/physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py" \
  --views "$views" --view 'ot_pdie_serdes_tx@c77a41179db8' \
  --recipe-key ot_pdie_serdes_tx__ff --out "$out" --tag FF \
  --corner TC --util 0.4 --sigmax M6 --pg-top-layer M5 \
  --clock-pin-entry on --io-tt-ps 250 --io-ff-ps 202.5 \
  --face-reset-relay 0
