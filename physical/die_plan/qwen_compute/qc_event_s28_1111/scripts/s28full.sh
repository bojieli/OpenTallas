#!/bin/bash
# QC-EVENT-S28 full recipe (epyc9): compose (30 types) -> collector_reattach -> gates (main tools) + strict bind + hist
set -uo pipefail; cd /
W=/srv/opentallas-scratch2/claude/qc-event-s28; RT=physical/die_plan/qwen_compute/qc_start_1106/runtime
POR=physical/die_plan/qwen_compute/plan_of_record; G=/srv/opentallas-scratch2/claude/qc-vis-resite/bind_plan_qc99_s27
echo "s28full start $(date)"
python3 -I -c "import json;t=json.load(open('$W/t31.json'));t.remove('slw_su_c__cl19bb38ef');print(json.dumps(t))" > $W/t30.json
cd $W/src28b
nice -n 19 python3 -I -B $W/make_s28.py compose $POR/plan_qc99_s27.json $W/planq/s28_stage_a.json $W/t30.json $W/compose_report.json --sidecar $W/sidecar_s27.json $W/sidecar_s28_stage_a.json > $W/compose.log 2>&1 || { echo COMPOSE_FAIL; exit 1; }
nice -n 19 python3 -I -B tools/die_plan/collector_reattach.py $POR/plan_qc99_s27.json $W/planq/s28_stage_a.json $W/planq/plan_qc99_s28.json $W/reattach_s28.json --sidecar $W/sidecar_s28_stage_a.json $W/sidecar_s28.json > $W/reattach.log 2>&1 || { echo REATTACH_FAIL; exit 1; }
sha256sum $W/planq/plan_qc99_s28.json $W/sidecar_s28.json
for S in $W/src28m $W/src28b; do cp $W/planq/plan_qc99_s28.json $S/$POR/; cp $W/sidecar_s28.json $S/$RT/sidecar_pv.json; done
S=$W/src28m; P=plan_qc99_s28; PL=$S/$POR/$P.json; O=$W/out/$P; rm -rf $O; mkdir -p $O
( cd $S && nice -n 19 python3 -I -c "import sys; sys.path.insert(0, 'tools/die_plan'); import schema; sys.exit(schema.main(['schema.py', 'validate', '$PL']))" > $O/schema.log 2>&1; echo "rc=$?" >> $O/schema.log ) &
( mkdir -p $O/g0; cd $S && nice -n 19 python3 -I tools/die_plan/check.py $PL --out $O/g0 --quiet > $O/g0.log 2>&1; echo "rc=$?" >> $O/g0.log ) &
( mkdir -p $O/g0c; cd $S && nice -n 19 python3 -I tools/die_plan/check.py $PL --out $O/g0c --quiet --completeness > $O/g0c.log 2>&1; echo "rc=$?" >> $O/g0c.log ) &
( cd $S && nice -n 19 python3 -I tools/die_plan/station_lint.py $PL --tsv $O/station_lint.tsv > $O/station_lint.log 2>&1; echo "rc=$?" >> $O/station_lint.log ) &
( cd $W/src28b && nice -n 19 python3 -I -B $W/make_s28.py hist $POR/plan_qc99_s27.json $POR/plan_qc99_s28.json $W/t31.json $W/hist.json --dumps $W/dump > $W/hist.log 2>&1; echo "HIST_RC=$?" >> $W/hist.log ) &
( S=$W/src28b; PL=$S/$POR/$P.json; O=$W/bind_$P; L=$W/bind_$P.log
  echo "bind start $(date) plan=$(sha256sum $PL|cut -c1-12) sidecar=$(sha256sum $S/$RT/sidecar_pv.json|cut -c1-12) bind.py=$(sha256sum $S/tools/die_plan/bind.py|cut -c1-12) r8=$(sha256sum $S/$RT/r8_sw2.json|cut -c1-12)" > $L
  rm -rf $O; mkdir -p $O; for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json provenance_elab.json; do [ -e $G/$f ] && cp -a $G/$f $O/$f; done
  s=$(date +%s); cd $S && timeout -s ABRT 5400 nice -n 19 python3 -I -B -X faulthandler tools/die_plan/bind.py bind $PL --out $O --asbuilt $S/$RT/asbuilt_sw2_pv.json --strict >> $L 2>&1
  echo "BIND_RC=$? wall=$(( $(date +%s)-s )) s end $(date)" >> $L ) &
wait; echo "s28full end $(date)"
