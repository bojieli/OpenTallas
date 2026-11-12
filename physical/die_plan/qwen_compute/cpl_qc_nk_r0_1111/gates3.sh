#!/bin/bash
# CPL-QC-NK-R0 s23 gates on epyc9, CURRENT main tools (origin/main 868623a0bb, srcm2): s22 base, s23_nkl candidate and
# the t22 trial (G0/schema only).  Same helper tree / sidecar d26ec11a2a5f / asbuilt as gates.sh.
set -uo pipefail; cd /
W=/srv/opentallas-scratch2/claude/cpl-qc-nk-r0; S=$W/srcm2; RT=physical/die_plan/qwen_compute/qc_start_1106/runtime
G=/srv/opentallas-scratch2/claude/dq97/taps1111/bind_gr
echo "gates3 start $(date) sidecar=$(sha256sum $S/$RT/sidecar_pv.json|cut -c1-12) bind.py=$(sha256sum $S/tools/die_plan/bind.py|cut -c1-12) check.py=$(sha256sum $S/tools/die_plan/check.py|cut -c1-12)"
for P in plan_qc99_s22_nkr0 plan_qc99_s23_nkl plan_qc99_s23_trial_t22; do
  PL=$W/planq/$P.json
  ( cd $S && nice -n 19 python3 -I -c "import sys; sys.path.insert(0, 'tools/die_plan'); import schema; sys.exit(schema.main(['schema.py', 'validate', '$PL']))" > $W/m2_schema_$P.log 2>&1; echo "rc=$?" >> $W/m2_schema_$P.log ) &
  ( mkdir -p $W/m2_g0_$P; cd $S && nice -n 19 python3 -I tools/die_plan/check.py $PL --out $W/m2_g0_$P --quiet > $W/m2_g0_$P.log 2>&1; echo "rc=$?" >> $W/m2_g0_$P.log ) &
  ( cd $S && nice -n 19 python3 -I tools/die_plan/station_lint.py $PL --tsv $W/m2_station_lint_$P.tsv > $W/m2_station_lint_$P.log 2>&1; echo "rc=$?" >> $W/m2_station_lint_$P.log ) &
done
for P in plan_qc99_s22_nkr0 plan_qc99_s23_nkl; do
  PL=$W/planq/$P.json
  ( O=$W/m2_bind_$P; rm -rf $O; mkdir -p $O; for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json provenance_elab.json; do cp -a $G/$f $O/$f; done
    s=$(date +%s); cd $S && timeout -s ABRT 5400 nice -n 19 python3 -I -X faulthandler tools/die_plan/bind.py bind $PL --out $O --asbuilt $S/$RT/asbuilt_sw2_pv.json --strict > $W/m2_bind_$P.log 2>&1
    echo "BIND_RC=$? wall=$(( $(date +%s)-s )) s end $(date)" >> $W/m2_bind_$P.log ) &
done
wait
echo "gates3 end $(date)"
