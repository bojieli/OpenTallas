#!/bin/bash
# QC-S28-B gates (epyc9, DO_NOT_COUNT): gates.sh TAG PLAN SIDECAR
#   schema / G0 / G0C / station_lint with origin/main tools (srcM = s28 src28m copy), strict bind (bind-strict-src on)
#   from srcB (= s28 src28b copy), G0 diff vs the s28 base outputs, bus_groups sha vs the s28 bind.
set -uo pipefail; cd /
TAG=$1; PIN=$2; SIN=$3
W=/srv/opentallas-scratch2/claude/qc-s28b; S28=/srv/opentallas-scratch2/claude/qc-event-s28
RT=physical/die_plan/qwen_compute/qc_start_1106/runtime; POR=physical/die_plan/qwen_compute/plan_of_record
G=/srv/opentallas-scratch2/claude/qc-vis-resite/bind_plan_qc99_s27
P=plan_qc99_$TAG; O=$W/out/$P; rm -rf $O; mkdir -p $O
for X in M B; do [ -d $W/src${X}_$TAG ] || nice -n 19 cp -a $W/src$X $W/src${X}_$TAG; done
SM=$W/srcM_$TAG; SB=$W/srcB_$TAG
echo "gates $TAG start $(date) plan=$(sha256sum $PIN|cut -c1-12) sidecar=$(sha256sum $SIN|cut -c1-12)" > $O/gates.log
for S in $SM $SB; do
  cp $PIN $S/$POR/$P.json; cp $SIN $S/$RT/sidecar_pv.json
  [ -d $W/srcS/physical/die_plan/qwen_compute/street_rule_bins ] && rsync -a $W/srcS/physical/die_plan/qwen_compute/street_rule_bins/ $S/physical/die_plan/qwen_compute/street_rule_bins/
done
S=$SM; PL=$S/$POR/$P.json
( cd $S && nice -n 19 python3 -I -c "import sys; sys.path.insert(0, 'tools/die_plan'); import schema; sys.exit(schema.main(['schema.py', 'validate', '$PL']))" > $O/schema.log 2>&1; echo "rc=$?" >> $O/schema.log ) &
( mkdir -p $O/g0; cd $S && nice -n 19 python3 -I tools/die_plan/check.py $PL --out $O/g0 --quiet > $O/g0.log 2>&1; echo "rc=$?" >> $O/g0.log ) &
( mkdir -p $O/g0c; cd $S && nice -n 19 python3 -I tools/die_plan/check.py $PL --out $O/g0c --quiet --completeness > $O/g0c.log 2>&1; echo "rc=$?" >> $O/g0c.log ) &
( cd $S && nice -n 19 python3 -I tools/die_plan/station_lint.py $PL --tsv $O/station_lint.tsv > $O/station_lint.log 2>&1; echo "rc=$?" >> $O/station_lint.log ) &
( S=$SB; PL=$S/$POR/$P.json; B=$W/bind_$P; L=$W/bind_$P.log
  echo "bind start $(date) plan=$(sha256sum $PL|cut -c1-12) sidecar=$(sha256sum $S/$RT/sidecar_pv.json|cut -c1-12) bind.py=$(sha256sum $S/tools/die_plan/bind.py|cut -c1-12) r8=$(sha256sum $S/$RT/r8_sw2.json|cut -c1-12)" > $L
  rm -rf $B; mkdir -p $B; for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json provenance_elab.json; do [ -e $G/$f ] && cp -a $G/$f $B/$f; done
  s=$(date +%s); cd $S && timeout -s ABRT 5400 nice -n 19 python3 -I -B -X faulthandler tools/die_plan/bind.py bind $PL --out $B --asbuilt $S/$RT/asbuilt_sw2_pv.json --strict >> $L 2>&1
  echo "BIND_RC=$? wall=$(( $(date +%s)-s )) s end $(date)" >> $L ) &
wait
for k in g0 g0c; do python3 -I $S28/g0diff.py $S28/out/plan_qc99_s28/$k/g0_report.json $O/$k/g0_report.json > $O/${k}_diff.txt 2>&1; done
echo "gates $TAG end $(date)" >> $O/gates.log
