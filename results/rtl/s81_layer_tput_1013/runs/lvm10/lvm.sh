#!/bin/bash
# lvm.sh <LVM> <modes> : production-shape S81 layer (NG 256, hierarchical HC, nominal link, --coef-split) at VM read latency LVM
set -u
S=/srv/opentallas-scratch/claude/rom-layer-tput-s81/su_main; L=$1; M=$2
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
export PATH=$(dirname $V):$PATH
cd $S/src
CASES=/srv/opentallas-scratch/claude/s81-suhc/su_cases_v2_ildr.pkl NG=256 FP=dpi HCH=1 STIMX=--coef-split LAYERS="L0 L2" J=16 VL="$V -GLVM=$L" \
  bash rtl/dsrom_sys/s81_ctrl/test/run_die_layer.sh $S/src $S/lvm$L "$M" > $S/lvm$L.log 2>&1
echo "LVM $L rc=$?"; cat $S/lvm$L/verdicts.log
rm -rf $S/lvm$L/obj_*/*.o $S/lvm$L/obj_*/*.d 2>/dev/null; exit 0
