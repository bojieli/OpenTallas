#!/bin/bash
# CLOCK-KV-R15 real-view die STA + HB4 count + reset-net STA on any KV die clock proof dir.
# usage: run_kv_realview.sh TAPDIR OUT [PLAN]
#   TAPDIR = die_clock_mesh proof dir with tap_arrivals_{TT,FF}.json + mesh.json (e.g. .../clock-kv-r14-1026/r14)
#   PLAN   = KV plan whose dir holds cores/*_pins*.json (default intel1 clock-kv-r12-1026/pd/hm_r12.json, sha 96e6d1cb)
# Runs on a fleet host (intel1/intel2), docker for the OpenSTA register characterisation (4g cap). ~1 min.
set -euo pipefail
T=$1; O=$2; PLAN=${3:-/srv/opentallas-scratch2/claude/clock-kv-r12-1026/pd/hm_r12.json}
H=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$H/../.." && pwd)
export PYTHONPATH=${OT_KV_PYLIB:-/srv/opentallas-scratch2/claude/codex-kv-mesh-1026/pylib}:$H
M=$ROOT/results/kv_realview_r15/kv_realview_manifest.json
mkdir -p "$O"
python3 "$H/kv_realview_sta.py" "$T" --plan "$PLAN" --manifest "$M" --accept signed --out "$O/sta_signed" | tee "$O/sta_signed.log"
python3 "$H/kv_realview_sta.py" "$T" --plan "$PLAN" --manifest "$M" --accept any --out "$O/sta_any_WHATIF" | tee "$O/sta_any_WHATIF.log"
python3 "$H/kv_hb_count.py" "$H" "$PLAN" "$T" "$O/sta_signed/declared" "$O/hb_count.json" | tee "$O/hb_count.log"
python3 "$H/kv_reset_sta.py" "$T" --plan "$PLAN" --out "$O/reset_sta" | tee "$O/reset_sta.log"
