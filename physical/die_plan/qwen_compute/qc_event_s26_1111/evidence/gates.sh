#!/bin/bash
# QC-EVENT-S26 gates on epyc9: tools = s26 branch (origin/main 40e22dd + s25 stack + ring-bond + hc1-strip + POST_MIN)
# + bind-verify-readset dfe657faff + bind-strict-src 1028559501 merged (gate-only tree, src_s26).  s25 and s26 both
# gated with the SAME tools.  Bind sidecar: s25 9f6e6f721b61 / s26 2b526c0f8849; r8 table 571c5b26bb1f (s25).
set -uo pipefail; cd /
W=/srv/opentallas-scratch2/claude/qc-event-s26/gate; RT=physical/die_plan/qwen_compute/qc_start_1106/runtime
G=/srv/opentallas-scratch2/claude/dq97/taps1111/bind_gr
S=$W/src_s26
echo "gates start $(date) tools=e09c339bafa0 bind.py=$(sha256sum $S/tools/die_plan/bind.py|cut -c1-12)"
for P in s25 plan_qc99_s26; do
  PL=$W/planq/$P.json
  ( cd $S && nice -n 19 python3 -I -c "import sys; sys.path.insert(0, 'tools/die_plan'); import schema; sys.exit(schema.main(['schema.py', 'validate', '$PL']))" > $W/schema_$P.log 2>&1; echo "rc=$?" >> $W/schema_$P.log ) &
  ( mkdir -p $W/g0_$P; cd $S && nice -n 19 python3 -I tools/die_plan/check.py $PL --out $W/g0_$P --quiet > $W/g0_$P.log 2>&1; echo "rc=$?" >> $W/g0_$P.log ) &
  ( cd $S && nice -n 19 python3 -I tools/die_plan/station_lint.py $PL --tsv $W/station_lint_$P.tsv > $W/station_lint_$P.log 2>&1; echo "rc=$?" >> $W/station_lint_$P.log ) &
done
wait
echo "light gates end $(date)"
