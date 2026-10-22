#!/bin/bash
set -eu
cd "$(dirname "$0")"
mkdir out
iverilog -g2012 -s tb_s81_land -DTB_W=276 -DTB_D=32 -DTB_KW=6 -DTB_NMAX=8 -DTB_TOP=dsdv_pv_local_land_n32_source4_276 -o out/sim tb.sv dsdv_pv_local_n32*.sv ot_pl_land*.sv
for pair in 115:0 815:0 115:700; do
 d=${pair%:*};r=${pair#*:};vvp -n out/sim +N=0 +DH="$d" +LR="$r" +K=17 +R0=12 +G=12 +RL=0 +IR=4 +GS=4 +CYC=256 >out/p_${d}_${r}.log
done
vvp -n out/sim +N=0 +DH=115 +LR=0 +K=16 +R0=12 +G=12 +RL=0 +IR=4 +GS=4 +CYC=256 >out/invalid_k.log
iverilog -g2012 -s tb_s81_land -DTB_W=276 -DTB_D=32 -DTB_KW=6 -DTB_NMAX=8 -DTB_TOP=dsdv_pv_local_land_n32_276 -o out/mut tb.sv dsdv_pv_local_n32.sv ot_pl_land*.sv
vvp -n out/mut +N=0 +DH=115 +LR=0 +K=17 +R0=12 +G=12 +RL=0 +IR=4 +GS=4 +CYC=256 >out/missing_external_reset.log
python3 check.py
