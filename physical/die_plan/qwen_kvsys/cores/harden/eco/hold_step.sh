#!/bin/bash
# FLOW-TAG 2026-10-26 (COORD FLOW-FANOUT ruling 10-26 00:41 (2)): the KV core flow's standard post-route FF hold step.
# A routed KV core whose sign-off FF hold is < 0 gets the KV-CORES warm post-route hold ECO (mk_eco.sh variant b<MARGIN>:
# FF-only hold repair on the routed SPEF, incremental re-route, run_kit_kv.sh post = TT/FF sign-off), with the ECO's
# repair_design fanout cap = the kit's own max_fanout.tcl cap (64 since 9bca574fd; mk_eco's default 24 would undo it).
# The ECO sign-off lands in KIT/signoff_hold/signoff.json (newest signoff*/ = the canary's verdict); KIT/signoff/ keeps
# the plain-route sign-off. Used by the qwen_kvsys_core flow canary (tools/flow_canary/canaries.json) and by KV kits.
#   hold_step.sh KIT SO_ROOT [CPUS=8] [MEM_GB=32] [MARGIN_PS=3]     (SO_ROOT = checkout holding tools/die_plan/signoff.py)
# FLOW-SHARED-9 2026-10-27: KIT/hold_step.json records the step (NOT_NEEDED / SKIP / PASS / FAILED + rc + first ERROR);
# a FAILED step removes any older KIT/signoff_hold, prints HOLD_STEP FAILED and is a canary stage FAIL (never silently
# judged as the plain route).
# FLOW-SHARED-10 2026-10-27 (COORD 20:53 DRT-1231 ruling): OT_HOLD_FORM=pre_drt (opt-in) = the same b<MARGIN> hold
# repair on the routed RC, applied to the kit's PRE-DRT 5_1_grt.odb (mk_eco OT_ECO_FROM=grt), then ONE detailed route
# (no re-route of a routed DB); post_route = the old warm ECO on 5_2_route.odb.  The ECO sign-off stays the verdict.
set -uo pipefail
FORM=${OT_HOLD_FORM:-post_route}
case $FORM in pre_drt) ECO_FROM=grt ;; post_route) ECO_FROM=route ;; *) echo "HOLD_STEP FAILED: OT_HOLD_FORM=$FORM (want pre_drt|post_route)"; exit 2 ;; esac
K=$(cd "$1" && pwd); SO=$(cd "$2" && pwd); CPUS=${3:-8}; MEM=${4:-32}; HM=${5:-3}
HERE=$(cd "$(dirname "$0")" && pwd)
rec() { python3 -I -c 'import json,sys; json.dump(dict(status=sys.argv[2], rc=int(sys.argv[3]), error=sys.argv[4], eco_dir=sys.argv[5], form=sys.argv[6]), open(sys.argv[1], "w"), indent=1)' "$K/hold_step.json" "$@" "$FORM"; }
rm -f "$K/hold_step.json"
SJ=$K/signoff/signoff.json
if [ ! -f "$SJ" ]; then echo "HOLD_STEP SKIP: no $SJ (route/sign-off did not complete)"; rec SKIP 0 "no plain sign-off" ""; exit 0; fi
W=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["checks"]["hold_ff"]["wns_ps"])' "$SJ" 2>/dev/null)
if [ -z "$W" ] || [ "$W" = None ]; then echo "HOLD_STEP SKIP: no FF hold WNS in $SJ"; rec SKIP 0 "no FF hold WNS" ""; exit 0; fi
if ! python3 -I -c 'import sys; sys.exit(0 if float(sys.argv[1]) < 0 else 1)' "$W"; then
  echo "HOLD_STEP NOT NEEDED: FF hold WNS $W ps >= 0"; rec NOT_NEEDED 0 "" ""; exit 0; fi
FO=$(sed -n 's/^set_max_fanout \([0-9][0-9]*\).*/\1/p' "$K/max_fanout.tcl" 2>/dev/null | head -n 1)
D=${K}_holdeco
echo "HOLD_STEP FF hold WNS $W ps < 0: ECO b$HM form $FORM fanout cap ${FO:-0} -> $D"
rm -rf "$K/signoff_hold"
OT_ECO_FROM=$ECO_FROM bash "$HERE/mk_eco.sh" "$K" "$D" "b$HM" "$SO" || { echo "HOLD_STEP FAILED: mk_eco"; rec FAILED 1 "mk_eco failed" "$D"; exit 1; }
sed -i "s/^OT_MAX_FANOUT=.*/OT_MAX_FANOUT=${FO:-0}/" "$D/variant.env"
cp "$HERE/run_eco.sh" "$D/"
bash "$D/run_eco.sh" "$D" "$CPUS" "$MEM"; rc=$?
if [ -f "$D/signoff/signoff.json" ]; then
  mkdir -p "$K/signoff_hold"; cp "$D/signoff/signoff.json" "$K/signoff_hold/signoff.json"
  cp "$D/ECO.json" "$D/variant.env" "$K/signoff_hold/" 2>/dev/null
  echo "HOLD_STEP signoff -> $K/signoff_hold/signoff.json"
  grep -E "^SIGNOFF" "$D/signoff.log" 2>/dev/null | tail -n 1
fi
# the ECO reached its own sign-off (SIGNED or not: a measured hold-step result) -> PASS / SIGNOFF_RC; no ECO sign-off -> FAILED
if [ -f "$K/signoff_hold/signoff.json" ]; then rec $([ $rc = 0 ] && echo PASS || echo SIGNOFF_RC) $rc "" "$D"; else
  [ $rc = 0 ] && rc=3
  ERR=$(grep -h -m1 -E '^\[ERROR|^Error' "$D/run_eco.log" "$D"/run/logs/asap7/*/base/*.log 2>/dev/null | head -n 1)
  rec FAILED $rc "${ERR:-no hold sign-off (rc.txt: $(tr '\n' ' ' < "$D/rc.txt" 2>/dev/null))}" "$D"
  rm -rf "$K/signoff_hold"
  echo "HOLD_STEP FAILED rc=$rc: ${ERR:-no hold sign-off} -- the plain route is NOT a hold-step result"
fi
echo "HOLD_STEP rc=$rc"; exit $rc
