#!/bin/bash
# after bind.sh: bus_groups compare s25 vs s26 (same tools), r8 pads for both, compare with the s25 runtime r8 571c5b26bb1f
set -uo pipefail; cd /
W=/srv/opentallas-scratch2/claude/qc-event-s26/gate; S=$W/src_s26
for P in s25 plan_qc99_s26; do
  mkdir -p $W/r8_$P
  ( cd $S && nice -n 19 python3 -I tools/die_plan/r8.py pads $W/planq/$P.json $W/bind_$P/bus_groups.json --out $W/r8_$P > $W/r8_$P.log 2>&1; echo "rc=$?" >> $W/r8_$P.log )
done
sha256sum $W/bind_s25/bus_groups.json $W/bind_plan_qc99_s26/bus_groups.json /srv/opentallas-scratch2/claude/kw45/qcbind/out_s25fix/bus_groups.json $W/r8_*/qwen_compute_r8_landing.json $S/physical/die_plan/qwen_compute/qc_start_1106/runtime/r8_sw2.json 2>&1 | sed "s/  / /"
