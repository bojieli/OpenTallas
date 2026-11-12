#!/bin/bash
# CPL-QC-NK-R0 11-11 S2 gates on epyc9: src = origin/main 65ef7507d2 tools + the s21 schema key (branch merge 00c9af7728);
# srcmain = pure origin/main tools (schema only).  Same helper tree / sidecar d26ec11a2a5f / asbuilt as CPL-QC-NK-OUT.
set -uo pipefail; cd /
W=/srv/opentallas-scratch2/claude/cpl-qc-nk-r0; S=$W/src; SM=$W/srcmain; RT=physical/die_plan/qwen_compute/qc_start_1106/runtime
G=/srv/opentallas-scratch2/claude/dq97/taps1111/bind_gr
echo "gates start $(date) sidecar=$(sha256sum $S/$RT/sidecar_pv.json|cut -c1-12) bind.py=$(sha256sum $S/tools/die_plan/bind.py|cut -c1-12) check.py=$(sha256sum $S/tools/die_plan/check.py|cut -c1-12)"
for P in plan_qc99_s21_nkout plan_qc99_s22_nkr0; do
  PL=$W/planq/$P.json
  ( cd $S && nice -n 19 python3 -I tools/die_plan/schema.py validate $PL > $W/schema_$P.log 2>&1; echo "rc=$?" >> $W/schema_$P.log ) &
  ( cd $SM && nice -n 19 python3 -I tools/die_plan/schema.py validate $PL > $W/schema_main_$P.log 2>&1; echo "rc=$?" >> $W/schema_main_$P.log ) &
  ( cd $S && nice -n 19 python3 -I tools/die_plan/station_lint.py $PL --tsv $W/station_lint_$P.tsv > $W/station_lint_$P.log 2>&1; echo "rc=$?" >> $W/station_lint_$P.log ) &
  ( mkdir -p $W/g0_$P; cd $S && nice -n 19 python3 -I tools/die_plan/check.py $PL --out $W/g0_$P --quiet > $W/g0_$P.log 2>&1; echo "rc=$?" >> $W/g0_$P.log ) &
  ( O=$W/bind_$P; mkdir -p $O; for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json provenance_elab.json; do cp -a $G/$f $O/$f; done
    s=$(date +%s); cd $S && timeout -s ABRT 5400 nice -n 19 python3 -I -X faulthandler tools/die_plan/bind.py bind $PL --out $O --asbuilt $S/$RT/asbuilt_sw2_pv.json --strict > $W/bind_$P.log 2>&1
    echo "BIND_RC=$? wall=$(( $(date +%s)-s )) s end $(date)" >> $W/bind_$P.log ) &
done
wait
echo "gates end $(date)"
