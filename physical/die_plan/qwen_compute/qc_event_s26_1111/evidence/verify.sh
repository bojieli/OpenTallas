#!/bin/bash
# bind_verify (fixed read-set tool, bind-verify-readset dfe657faff in the gate tree) on s25 and s26, same tools
set -uo pipefail; cd /
W=/srv/opentallas-scratch2/claude/qc-event-s26/gate; RT=physical/die_plan/qwen_compute/qc_start_1106/runtime
for P in s25 plan_qc99_s26; do
  S=$W/src_s26; [ $P = s25 ] && S=$W/src_s26_s25sc
  O=$W/bind_$P; L=$W/verify_$P.log
  ( echo "verify start $(date) plan=$(sha256sum $W/planq/$P.json|cut -c1-12)" > $L
    s=$(date +%s); cd $S && timeout -s ABRT 43200 nice -n 19 python3 -I -X faulthandler tools/die_plan/bind.py verify $W/planq/$P.json --out $O --asbuilt $S/$RT/asbuilt_sw2_pv.json --strict --mem 96 >> $L 2>&1
    echo "VERIFY_RC=$? wall=$(( $(date +%s)-s )) s end $(date)" >> $L ) &
done
wait
