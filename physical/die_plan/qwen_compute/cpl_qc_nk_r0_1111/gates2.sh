#!/bin/bash
# CPL-QC-NK-R0 11-11: s22 gates (final selective delta) + schema validate run from tools/die_plan (python3 -I drops the
# script dir from sys.path, so the module imports need that cwd).  Same trees as gates.sh.
set -uo pipefail; cd /
W=/srv/opentallas-scratch2/claude/cpl-qc-nk-r0; S=$W/src; SM=$W/srcmain; RT=physical/die_plan/qwen_compute/qc_start_1106/runtime
G=/srv/opentallas-scratch2/claude/dq97/taps1111/bind_gr
echo "gates2 start $(date) plan22=$(sha256sum $W/planq/plan_qc99_s22_nkr0.json|cut -c1-12)"
for P in plan_qc99_s21_nkout plan_qc99_s22_nkr0; do
  PL=$W/planq/$P.json
  ( cd $S/tools/die_plan && nice -n 19 python3 -I schema.py validate $PL > $W/schema_$P.log 2>&1; echo "rc=$?" >> $W/schema_$P.log ) &
  ( cd $SM/tools/die_plan && nice -n 19 python3 -I schema.py validate $PL > $W/schema_main_$P.log 2>&1; echo "rc=$?" >> $W/schema_main_$P.log ) &
done
P=plan_qc99_s22_nkr0; PL=$W/planq/$P.json
( cd $S && nice -n 19 python3 -I tools/die_plan/station_lint.py $PL --tsv $W/station_lint_$P.tsv > $W/station_lint_$P.log 2>&1; echo "rc=$?" >> $W/station_lint_$P.log ) &
( mkdir -p $W/g0_$P; cd $S && nice -n 19 python3 -I tools/die_plan/check.py $PL --out $W/g0_$P --quiet > $W/g0_$P.log 2>&1; echo "rc=$?" >> $W/g0_$P.log ) &
( O=$W/bind_$P; mkdir -p $O; for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json provenance_elab.json; do cp -a $G/$f $O/$f; done
  s=$(date +%s); cd $S && timeout -s ABRT 5400 nice -n 19 python3 -I -X faulthandler tools/die_plan/bind.py bind $PL --out $O --asbuilt $S/$RT/asbuilt_sw2_pv.json --strict > $W/bind_$P.log 2>&1
  echo "BIND_RC=$? wall=$(( $(date +%s)-s )) s end $(date)" >> $W/bind_$P.log ) &
wait
echo "gates2 end $(date)"
