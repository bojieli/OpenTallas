#!/bin/bash
# FLOW-TAG 2026-10-26 (COORD FLOW-FANOUT ruling 10-26 00:41 (2)): the KV core flow's standard post-route FF hold step.
# A routed KV core whose sign-off FF hold is < 0 gets the KV-CORES warm post-route hold ECO (mk_eco.sh variant b<MARGIN>:
# FF-only hold repair on the routed SPEF, incremental re-route, run_kit_kv.sh post = TT/FF sign-off), with the ECO's
# repair_design fanout cap = the kit's own max_fanout.tcl cap (64 since 9bca574fd; mk_eco's default 24 would undo it).
# The ECO sign-off lands in KIT/signoff_hold/signoff.json (newest signoff*/ = the canary's verdict); KIT/signoff/ keeps
# the plain-route sign-off. Used by the qwen_kvsys_core flow canary (tools/flow_canary/canaries.json) and by KV kits.
#   hold_step.sh KIT SO_ROOT [CPUS=8] [MEM_GB=32] [MARGIN_PS=3]     (SO_ROOT = checkout holding tools/die_plan/signoff.py)
set -uo pipefail
K=$(cd "$1" && pwd); SO=$(cd "$2" && pwd); CPUS=${3:-8}; MEM=${4:-32}; HM=${5:-3}
HERE=$(cd "$(dirname "$0")" && pwd)
SJ=$K/signoff/signoff.json
if [ ! -f "$SJ" ]; then echo "HOLD_STEP SKIP: no $SJ (route/sign-off did not complete)"; exit 0; fi
W=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["checks"]["hold_ff"]["wns_ps"])' "$SJ" 2>/dev/null)
if [ -z "$W" ] || [ "$W" = None ]; then echo "HOLD_STEP SKIP: no FF hold WNS in $SJ"; exit 0; fi
if ! python3 -I -c 'import sys; sys.exit(0 if float(sys.argv[1]) < 0 else 1)' "$W"; then
  echo "HOLD_STEP NOT NEEDED: FF hold WNS $W ps >= 0"; exit 0; fi
FO=$(sed -n 's/^set_max_fanout \([0-9][0-9]*\).*/\1/p' "$K/max_fanout.tcl" 2>/dev/null | head -n 1)
D=${K}_holdeco
echo "HOLD_STEP FF hold WNS $W ps < 0: ECO b$HM fanout cap ${FO:-0} -> $D"
bash "$HERE/mk_eco.sh" "$K" "$D" "b$HM" "$SO" || { echo "HOLD_STEP mk_eco FAILED"; exit 1; }
sed -i "s/^OT_MAX_FANOUT=.*/OT_MAX_FANOUT=${FO:-0}/" "$D/variant.env"
cp "$HERE/run_eco.sh" "$D/"
bash "$D/run_eco.sh" "$D" "$CPUS" "$MEM"; rc=$?
if [ -f "$D/signoff/signoff.json" ]; then
  mkdir -p "$K/signoff_hold"; cp "$D/signoff/signoff.json" "$K/signoff_hold/signoff.json"
  cp "$D/ECO.json" "$D/variant.env" "$K/signoff_hold/" 2>/dev/null
  echo "HOLD_STEP signoff -> $K/signoff_hold/signoff.json"
  grep -E "^SIGNOFF" "$D/signoff.log" 2>/dev/null | tail -n 1
fi
echo "HOLD_STEP rc=$rc"; exit $rc
