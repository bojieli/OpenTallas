#!/bin/bash
# QC-S28-D gates on epyc9 (DO_NOT_COUNT): schema/G0/G0C/station_lint (src28m tools) on s28 vs s28d, strict bind of s28d
# from src28b (bind-strict-src tools, same recipe as qc-event-s28/s28gates.sh), bus_groups compare, relay_sites Tcl smoke.
set -uo pipefail; cd /
W=/srv/opentallas-scratch2/claude/qc-event-s28; M=/srv/opentallas-scratch2/claude/qc-s28d
RT=physical/die_plan/qwen_compute/qc_start_1106/runtime; POR=physical/die_plan/qwen_compute/plan_of_record
G=/srv/opentallas-scratch2/claude/qc-vis-resite/bind_plan_qc99_s27
echo "gates start $(date)"
for S in $W/src28m $W/src28b; do cp $M/plan_qc99_s28d.json $S/$POR/; done
S=$W/src28m
for P in plan_qc99_s28 plan_qc99_s28d; do
  PL=$S/$POR/$P.json; O=$M/out/$P; mkdir -p $O
  ( cd $S && nice -n 19 python3 -I -c "import sys; sys.path.insert(0, 'tools/die_plan'); import schema; sys.exit(schema.main(['schema.py', 'validate', '$PL']))" > $O/schema.log 2>&1; echo "rc=$?" >> $O/schema.log ) &
  ( mkdir -p $O/g0; cd $S && nice -n 19 python3 -I tools/die_plan/check.py $PL --out $O/g0 --quiet > $O/g0.log 2>&1; echo "rc=$?" >> $O/g0.log ) &
  ( mkdir -p $O/g0c; cd $S && nice -n 19 python3 -I tools/die_plan/check.py $PL --out $O/g0c --quiet --completeness > $O/g0c.log 2>&1; echo "rc=$?" >> $O/g0c.log ) &
  ( cd $S && nice -n 19 python3 -I tools/die_plan/station_lint.py $PL --tsv $O/station_lint.tsv > $O/station_lint.log 2>&1; echo "rc=$?" >> $O/station_lint.log ) &
done
( cd $S && nice -n 19 python3 -I -c "
import json, sys; sys.path.insert(0, 'tools/die_plan'); import kit_istations as K
P = json.load(open('$POR/plan_qc99_s28d.json'))
for tn in json.load(open('$M/delta_s28d.json'))['changes']:
    L = K.relay_sites_lines(tn, P['partition_types'][tn]); post = K.relay_sites_post_tcl(tn, P['partition_types'][tn])
    print(tn, 'relay_sites tcl lines', len(L), 'keys', len(P['partition_types'][tn]['relay_sites']), 'ring_post', post is not None)
" > $M/out/relay_tcl_smoke.log 2>&1; echo "rc=$?" >> $M/out/relay_tcl_smoke.log ) &
( P=plan_qc99_s28d; S=$W/src28b; PL=$S/$POR/$P.json; O=$M/bind_$P; L=$M/bind_$P.log
  echo "bind start $(date) plan=$(sha256sum $PL|cut -c1-12) sidecar=$(sha256sum $S/$RT/sidecar_pv.json|cut -c1-12) bind.py=$(sha256sum $S/tools/die_plan/bind.py|cut -c1-12) r8=$(sha256sum $S/$RT/r8_sw2.json|cut -c1-12)" > $L
  rm -rf $O; mkdir -p $O; for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json provenance_elab.json; do [ -e $G/$f ] && cp -a $G/$f $O/$f; done
  s=$(date +%s); cd $S && timeout -s ABRT 5400 nice -n 19 systemd-run --user --scope -q -p MemoryMax=48G python3 -I -B -X faulthandler tools/die_plan/bind.py bind $PL --out $O --asbuilt $S/$RT/asbuilt_sw2_pv.json --strict >> $L 2>&1
  echo "BIND_RC=$? wall=$(( $(date +%s)-s )) s end $(date)" >> $L ) &
wait; echo "gates end $(date)"
