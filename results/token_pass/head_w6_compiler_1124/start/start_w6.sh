#!/usr/bin/env bash
# HEAD-R18 11-24 (COORD ruling): fresh START tree on the W6 bind. Inputs: W6 plan b3507e628de6, the NF15f START stage
# geometry of provider_e1br (1389 stages = the W6 sidecar's 1389 st: regions, die_clock unchanged since 11-21),
# re-sited on the W6 type raw exports with the HEAD-START-R16 recipe (start_reset.py + relay_over.py), tools c0b6e2d03408.
set -euo pipefail
D=/srv/opentallas-scratch2/claude/head-r18
W=$D/start_w6_1124
C=$D/trees/rt_tools_launch/s81_head_w6_ctl@c0b6e2d03408
X=$D/trees/s81_head_w6_ctl/physical/die_plan/s81_head/prep/NF15f
PLAN=$X/prep_r18w6/source_plan.json
test "$(sha256sum "$PLAN" | cut -c1-12)" = b3507e628de6
test ! -e "$W/canon"
cd "$C"
python3 -I -B "$W/unpatch.py" "$X/provider_e1br" "$C" "$W/canon"
set +e
python3 -I -B "$W/start_reset.py" "$C" "$PLAN" "$W/canon" "$W/sited" --bench-allow-over
rc=$?
set -e
echo "START_RESET_RC $rc"
test -f "$W/sited/start_stages.json"
if python3 -I -c "import json,sys;sys.exit(0 if json.load(open('$W/sited/exports.json'))['summary'].get('over_hop_open') else 1)"; then
  python3 -I -B "$W/relay_over.py" "$W/sited" "$W/provider_w6" "$W/sited/exports.json"
else
  mkdir "$W/provider_w6"; cp "$W/sited/"{start_stages.json,start_stages.sv,ctree.v,ctree.tcl} "$W/provider_w6/"
fi
grep -c "ot_dp_landing_root #(.SETTLE(" "$W/provider_w6/start_stages.sv"
grep -o "ot_dp_landing_root #(.SETTLE([0-9]*))" "$W/provider_w6/start_stages.sv"
sha256sum "$W/provider_w6/"start_stages.*
echo START_W6_DONE
