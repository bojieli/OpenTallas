#!/bin/bash
# SC-REFLOOR-1: strict bind of a refloor plan on the s25 wave src (mirrors VISLAYOUT2-QC bind_e.sh / kw45 qcbind)
set -uo pipefail; cd /
R=/srv/opentallas-scratch2/claude/sc-refloor-1; S=/srv/opentallas-scratch2/claude/kw45/src_qc_s25_4e2764d237
RT=physical/die_plan/qwen_compute/qc_start_1106/runtime; G=/srv/opentallas-scratch2/claude/kw45/qcbind/out_s25fix
P=$1; PL=$R/planq/$P.json; O=$R/bind_$P
rm -rf $O; mkdir -p $O; for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json provenance_elab.json; do cp -a $G/$f $O/$f; done
echo "bind start $(date) plan=$(sha256sum $PL|cut -c1-12)"
s=$(date +%s)
cd $S && nice -n 5 python3 -I -B -X faulthandler tools/die_plan/bind.py bind $PL --out $O --asbuilt $S/$RT/asbuilt_sw2_pv.json --strict
echo "BIND_RC=$? wall=$(( $(date +%s)-s )) s end $(date)"
