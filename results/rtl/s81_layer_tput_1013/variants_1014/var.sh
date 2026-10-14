#!/bin/bash
# var.sh <name> <LVM> <NTREE 0|1> <SU 0|1> <modes> : S81 production layer (tb_s81_die_layer NG 256, HCH 1, FP dpi, nom,
# --coef-split --h-stream, PIPE 1 HST 1 HTX 2 PGAP 600) L0 / L2 / L14 (Engram) -- T3 rom-layer-tput-s81 10-14
set -u
B=/srv/opentallas-scratch/claude/s81-layer-var-1014; N=$1; LV=$2; NT=$3; SU=$4; M=$5
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; export PATH=$(dirname $V):$PATH
cd $B/src
XG="-GPIPE=1 -GHST=1 -GHTX=2 -GPGAP=600 -GLVM=$LV"; [ $NT = 1 ] && XG="$XG -GNTREE=1 -GNT_K=67"
SX="--coef-split --h-stream"; [ $SU = 1 ] && SX="$SX --dur attn.q_rope=123 --dur ffn.bias=108 --dur ffn.softplus_sqrt=210"
CASES=/srv/opentallas-scratch/claude/s81-suhc/su_cases_v2_ildr.pkl CHAINS=/srv/opentallas-scratch/claude/s81-suhc/hc_chain_%L.pkl \
 NG=256 FP=dpi HCH=1 STIMX="$SX" LAYERS="L0 L2 L14" J=16 VL=$V XG="$XG" \
  bash rtl/dsrom_sys/s81_ctrl/test/run_die_layer.sh $B/src $B/$N "$M" > $B/$N.log 2>&1
echo "VAR $N rc=$?"; cat $B/$N/verdicts.log
rm -rf $B/$N/obj_*/*.o $B/$N/obj_*/*.d 2>/dev/null; exit 0
