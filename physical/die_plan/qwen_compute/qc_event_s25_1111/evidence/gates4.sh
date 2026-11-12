#!/bin/bash
# QC-EVENT-S25 gates on epyc9: CURRENT main tools (origin/main 9446d18f5d + the s25 schema key), base s24_views vs s25.
# Same recipe as QC-BIND-VIEWS gates.sh / CPL-QC-NK-R0 gates3.sh. Base binds with sidecar d26ec11a2a5f (src_base),
# s25 binds with its qreg sidecar (src_s25: d26ec + item 5 marks).
set -uo pipefail; cd /
W=/srv/opentallas-scratch2/claude/qc-event-s25/gate; RT=physical/die_plan/qwen_compute/qc_start_1106/runtime
G=/srv/opentallas-scratch2/claude/dq97/taps1111/bind_gr
echo "gates4 (s25 v4) start $(date) base_sidecar=$(sha256sum $W/src_base/$RT/sidecar_pv.json|cut -c1-12) s25_sidecar=$(sha256sum $W/src_s25/$RT/sidecar_pv.json|cut -c1-12) bind.py=$(sha256sum $W/src_base/tools/die_plan/bind.py|cut -c1-12) check.py=$(sha256sum $W/src_base/tools/die_plan/check.py|cut -c1-12)"
for P in plan_qc99_s25; do
  S=$W/src_base; [ $P = plan_qc99_s25 ] && S=$W/src_s25
  PL=$W/planq/$P.json
  ( cd $S && nice -n 19 python3 -I -c "import sys; sys.path.insert(0, 'tools/die_plan'); import schema; sys.exit(schema.main(['schema.py', 'validate', '$PL']))" > $W/schema_$P.log 2>&1; echo "rc=$?" >> $W/schema_$P.log ) &
  ( mkdir -p $W/g0_$P; cd $S && nice -n 19 python3 -I tools/die_plan/check.py $PL --out $W/g0_$P --quiet > $W/g0_$P.log 2>&1; echo "rc=$?" >> $W/g0_$P.log ) &
  ( cd $S && nice -n 19 python3 -I tools/die_plan/station_lint.py $PL --tsv $W/station_lint_$P.tsv > $W/station_lint_$P.log 2>&1; echo "rc=$?" >> $W/station_lint_$P.log ) &
  ( O=$W/bind_$P; rm -rf $O; mkdir -p $O; for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json provenance_elab.json; do cp -a $G/$f $O/$f; done
    s=$(date +%s); cd $S && timeout -s ABRT 5400 nice -n 19 python3 -I -X faulthandler tools/die_plan/bind.py bind $PL --out $O --asbuilt $S/$RT/asbuilt_sw2_pv.json --strict > $W/bind_$P.log 2>&1
    echo "BIND_RC=$? wall=$(( $(date +%s)-s )) s end $(date)" >> $W/bind_$P.log ) &
done
wait
echo "gates4 end $(date)"
