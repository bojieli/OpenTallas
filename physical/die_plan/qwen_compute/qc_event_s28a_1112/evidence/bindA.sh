#!/bin/bash
# QC-S28-A bind: s28 plan + substituted manifest (ad39 = 5ef1 + st_b substitute_inst) in src28a; ARG1 = out name
set -uo pipefail; cd /
W=/srv/opentallas-scratch2/claude/qc-s28a; S=$W/src28a; RT=physical/die_plan/qwen_compute/qc_start_1106/runtime
POR=physical/die_plan/qwen_compute/plan_of_record; PL=$S/$POR/${PLAN:-plan_qc99_s28}.json
G=/srv/opentallas-scratch2/claude/qc-vis-resite/bind_plan_qc99_s27
N=$1; O=$W/$N; L=$W/$N.log
echo "bind start $(date) plan=$(sha256sum $PL|cut -c1-12) manifest=$(sha256sum $S/$RT/asbuilt_sw2_pv.json|cut -c1-12) sidecar=$(sha256sum $S/$RT/sidecar_pv.json|cut -c1-12) r8=$(sha256sum $S/$RT/r8_sw2.json|cut -c1-12) bind.py=$(sha256sum $S/tools/die_plan/bind.py|cut -c1-12)" > $L
rm -rf $O; mkdir -p $O; for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json provenance_elab.json; do [ -e $G/$f ] && cp -a $G/$f $O/$f; done
s=$(date +%s); cd $S && timeout -s ABRT 5400 nice -n 19 python3 -I -B -X faulthandler tools/die_plan/bind.py bind $PL --out $O --asbuilt $S/$RT/asbuilt_sw2_pv.json --strict >> $L 2>&1
echo "BIND_RC=$? wall=$(( $(date +%s)-s )) s end $(date)" >> $L
