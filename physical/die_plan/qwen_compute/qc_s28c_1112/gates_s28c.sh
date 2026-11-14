#!/bin/bash
# QC-S28-C gates on epyc9 (DO_NOT_COUNT): schema/G0/G0C/station_lint (src28m), strict bind (src28b), explorer + route_supply after.
set -uo pipefail; cd /
W=/srv/opentallas-scratch2/claude/qc-s28c; E=/srv/opentallas-scratch2/claude/qc-event-s28
POR=physical/die_plan/qwen_compute/plan_of_record; RT=physical/die_plan/qwen_compute/qc_start_1106/runtime
G=/srv/opentallas-scratch2/claude/qc-vis-resite/bind_plan_qc99_s27
echo "gates start $(date)"
for S in $E/src28m $E/src28b; do cp $W/plan_qc99_s28c.json $S/$POR/plan_qc99_s28c.json; done
S=$E/src28m; PL=$S/$POR/plan_qc99_s28c.json; O=$W/out; mkdir -p $O/g0 $O/g0c
( cd $S && nice -n 19 python3 -I -c "import sys; sys.path.insert(0, 'tools/die_plan'); import schema; sys.exit(schema.main(['schema.py', 'validate', '$PL']))" > $O/schema.log 2>&1; echo "rc=$?" >> $O/schema.log ) &
( cd $S && nice -n 19 python3 -I tools/die_plan/check.py $PL --out $O/g0 --quiet > $O/g0.log 2>&1; echo "rc=$?" >> $O/g0.log ) &
( cd $S && nice -n 19 python3 -I tools/die_plan/check.py $PL --out $O/g0c --quiet --completeness > $O/g0c.log 2>&1; echo "rc=$?" >> $O/g0c.log ) &
( cd $S && nice -n 19 python3 -I tools/die_plan/station_lint.py $PL --tsv $O/station_lint.tsv > $O/station_lint.log 2>&1; echo "rc=$?" >> $O/station_lint.log ) &
( cd $S && for t in cbx_q10__cl94a12200 cbx_q10__cl89936551; do nice -n 19 python3 -I tools/fleet_viz/explorer_render.py type --plan $E/planq/plan_qc99_s28.json --type $t --repo . --die qwen_compute --delta $W/delta_s28c.json --supply --out $W/after/$t > $W/after_$t.log 2>&1; echo "rc=$?" >> $W/after_$t.log; done ) &
( cd $S && nice -n 19 python3 -I tools/die_plan/route_supply.py $PL --die qwen_compute --repo . --match "^cbx_q" --core-conns $W/core_conns_cbx.json --calib-1112 --out $W/rs_after > $W/rs_after.log 2>&1; echo "rc=$?" >> $W/rs_after.log
  nice -n 19 python3 -I tools/die_plan/route_supply.py $PL --die qwen_compute --repo . --match "^cbx_q" --out $W/rs_after_noconns > $W/rs_after_noconns.log 2>&1 ) &
( S=$E/src28b; PL=$S/$POR/plan_qc99_s28c.json; O=$W/bind_plan_qc99_s28c; L=$W/bind.log
  echo "bind start $(date) plan=$(sha256sum $PL|cut -c1-12) sidecar=$(sha256sum $S/$RT/sidecar_pv.json|cut -c1-12) bind.py=$(sha256sum $S/tools/die_plan/bind.py|cut -c1-12) r8=$(sha256sum $S/$RT/r8_sw2.json|cut -c1-12)" > $L
  rm -rf $O; mkdir -p $O; for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json provenance_elab.json; do [ -e $G/$f ] && cp -a $G/$f $O/$f; done
  s=$(date +%s); cd $S && timeout -s ABRT 5400 nice -n 19 python3 -I -B -X faulthandler tools/die_plan/bind.py bind $PL --out $O --asbuilt $S/$RT/asbuilt_sw2_pv.json --strict >> $L 2>&1
  echo "BIND_RC=$? wall=$(( $(date +%s)-s )) s end $(date)" >> $L ) &
wait; echo "gates end $(date)"
