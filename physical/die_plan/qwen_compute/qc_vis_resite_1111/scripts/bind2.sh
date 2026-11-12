#!/bin/bash
# QC-VIS-RESITE strict bind, recipe = epyc9 qc-event-s25/gate/runfix.sh (branch tree src_s25fix incl bind-strict-src). Usage: bind.sh NAME
set -uo pipefail; cd /
W=/srv/opentallas-scratch2/claude/qc-vis-resite; RT=physical/die_plan/qwen_compute/qc_start_1106/runtime; G=/srv/opentallas-scratch2/claude/dq97/taps1111/bind_gr
S=${SRC:-/srv/opentallas-scratch2/claude/qc-event-s25/gate/src_s25fix}
P=$1; PL=$W/planq/$P.json; O=$W/bind_$P; L=$W/bind_$P.log
echo "bind start $(date) plan=$(sha256sum $PL|cut -c1-12) sidecar=$(sha256sum $S/$RT/sidecar_pv.json|cut -c1-12) bind.py=$(sha256sum $S/tools/die_plan/bind.py|cut -c1-12)" > $L
rm -rf $O; mkdir -p $O; for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json provenance_elab.json; do cp -a $G/$f $O/$f; done
s=$(date +%s); cd $S && timeout -s ABRT 5400 nice -n 19 python3 -I -X faulthandler tools/die_plan/bind.py bind $PL --out $O --asbuilt $S/$RT/asbuilt_sw2_pv.json --strict >> $L 2>&1
echo "BIND_RC=$? wall=$(( $(date +%s)-s )) s end $(date)" >> $L
