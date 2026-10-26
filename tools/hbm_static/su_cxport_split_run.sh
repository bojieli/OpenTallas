#!/bin/bash
# HBM-SU3 10-17: cxport split (4 dl + ij + rc leaves) lockstep vs the hub. usage: OUT [QID B39 MUT MUTONE]
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1"); q=${2:-2}; b=${3:-0}; mut=${4:-0}; one=${5:-0}; mkdir -p "$out"
C=rtl/hbm_accel/generic/adapters/static_su/collport
T=tb_hbm_su_cxport_split
iverilog -g2012 -s $T -P$T.QID=$q -P$T.B39=$b -P$T.MUT=$mut -P$T.MUTONE=$one -o "$out/cx.vvp" \
 $C/ot_hbm_su_static_cxport.sv $C/ot_hbm_su_static_cxport_split.sv $C/tb_hbm_su_cxport_split.sv
vvp -n "$out/cx.vvp" | tee "$out/bench.log" | tail -8
