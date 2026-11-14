#!/bin/bash
# QC-S28-E strict bind of plan_qc99_s28e on the src28b tools (copy src28e = cp -al src28b + glue bins + s28e sidecar)
set -u; cd /
W=/srv/opentallas-scratch2/claude/qc-s28e; POR=physical/die_plan/qwen_compute/plan_of_record; RT=physical/die_plan/qwen_compute/qc_start_1106/runtime
G=/srv/opentallas-scratch2/claude/qc-event-s28/bind_plan_qc99_s28
S=$W/src28e; P=plan_qc99_s28e; PL=$S/$POR/$P.json
rm -f $PL; cp $W/planq/$P.json $PL
rm -f $S/$RT/sidecar_pv.json; cp $W/sidecar_s28e.json $S/$RT/sidecar_pv.json
O=$W/bind_$P; L=$W/bind_$P.log
echo "bind start $(date) plan=$(sha256sum $PL|cut -c1-12) sidecar=$(sha256sum $S/$RT/sidecar_pv.json|cut -c1-12) bind.py=$(sha256sum $S/tools/die_plan/bind.py|cut -c1-12) r8=$(sha256sum $S/$RT/r8_sw2.json|cut -c1-12)" > $L
rm -rf $O; mkdir -p $O; for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json provenance_elab.json; do [ -e $G/$f ] && cp -a $G/$f $O/$f; done
s=$(date +%s); cd $S && timeout -s ABRT 5400 nice -n 19 python3 -I -B -X faulthandler tools/die_plan/bind.py bind $PL --out $O --asbuilt $S/$RT/asbuilt_sw2_pv.json --strict >> $L 2>&1
echo "BIND_RC=$? wall=$(( $(date +%s)-s )) s end $(date)" >> $L
