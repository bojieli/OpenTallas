#!/bin/bash
# VL2QC-SC: strict bind of a private sc plan on the s25 wave src (read-only, python3 -I -B); asbuilt cache copied from out_s25fix
set -uo pipefail; cd /
K=/srv/opentallas-scratch2/claude/kw45; S=$K/src_qc_s25_4e2764d237; RT=physical/die_plan/qwen_compute/qc_start_1106/runtime
W=/srv/opentallas-scratch2/claude/vislayout2-qc; PL=$1; O=$2; G=$K/qcbind/out_s25fix
rm -rf $O; mkdir -p $O; for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json provenance_elab.json; do [ -e $G/$f ] && cp -a $G/$f $O/$f; done
echo "bind start $(date) plan=$(sha256sum $PL|cut -c1-12)"
s=$(date +%s)
cd $S && timeout -s ABRT 5400 python3 -I -B -X faulthandler tools/die_plan/bind.py bind $PL --out $O --asbuilt $S/$RT/asbuilt_sw2_pv.json --strict
echo "BIND_RC=$? wall=$(( $(date +%s)-s )) s end $(date)"
