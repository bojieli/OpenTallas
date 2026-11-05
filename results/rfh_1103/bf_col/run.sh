#!/usr/bin/env bash
# DIE-S81-51/RF-H 11-03 bf_col RNE-cut lockstep: run.sh <repo root> <out> [mut 0|1] [seed]
#   mut 1 = +define+RFH_MUTANT_RNECUT (retained LSB flipped in the added stage) -> must FAIL.  Exit 0 = expected verdict.
set -u
R=$1; O=$2; M=${3:-0}; S=${4:-1}; mkdir -p "$O"
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
D=""; [ "$M" = 1 ] && D="+define+RFH_MUTANT_RNECUT"
L=$R/rtl/v41rom
$V --binary --timing -j "${JOBS:-8}" -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD $D --top-module tb -Mdir "$O/obj$M" \
  $R/rtl/common/ot_prefix.sv $R/rtl/hdc/ot_hdc_cg.sv $R/rtl/hdc/ot_hdc_delay.sv $R/rtl/proto/ot_fp32_add_rne_pipe.sv \
  $L/ot_v41_bmul_subnormal_rne_prepare.sv $L/ot_v41_bmul2_rne_prepare.sv $L/ot_v41_kreg.sv $L/ot_v41_tile_clk.sv \
  $L/ot_v41_fadd.sv $L/ot_v41_fadd2.sv $L/ot_v41_chain2.sv $L/ot_v41_chain2u2.sv $L/ot_v41_chain3.sv $L/ot_v41_chain4.sv \
  $L/ot_v41_bf16_lanes3.sv $R/results/rfh_1103/bf_col/tb_rnecut.sv > "$O/build$M.log" 2>&1 \
  || { echo "RNECUT FAIL build"; tail -8 "$O/build$M.log"; exit 2; }
"$O/obj$M/Vtb" +seed=$S +cycles=${NCYC:-200000} > "$O/run${M}_$S.log" 2>&1
r=$(grep -m1 "^RNECUT" "$O/run${M}_$S.log"); echo "$r mut=$M seed=$S"; grep -m3 MISMATCH "$O/run${M}_$S.log"
if [ "$M" = 0 ]; then echo "$r" | grep -q " PASS "; else echo "$r" | grep -q " FAIL "; fi
