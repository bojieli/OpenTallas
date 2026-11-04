#!/usr/bin/env bash
# DIE-S81-51/RF-D 11-03: run.sh <repo root> <out> [mut 0|1] [mode 0|1] [seed] [RA] [RB]  (mut 2 = OT_RFD_MUT_L0R2)  -> L0R_RF PASS / FAIL (exit 0 = expected)
set -u
R=$1; O=$2; M=${3:-0}; MO=${4:-0}; S=${5:-1}; RA=${6:-0}; RB=${7:-1}; mkdir -p "$O"
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
D=""; [ "$M" = 1 ] && D="+define+OT_RFD_MUT_L0R"; [ "$M" = 2 ] && D="+define+OT_RFD_MUT_L0R2"; [ "$M" = 3 ] && D="+define+OT_RFD_MUT_L0R3"
$V --binary --timing -j "${JOBS:-8}" -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD $D -GRA=$RA -GRB=$RB --top-module tb_l0r_rf -Mdir "$O/obj$M.$RA$RB" \
  $R/rtl/lib/ot_rst_relay.sv $R/rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l0r.sv $R/results/rfd_1103/l0r/tb_l0r_rf.sv > "$O/build$M.log" 2>&1 \
  || { echo "L0R_RF FAIL build"; tail -8 "$O/build$M.log"; exit 2; }
"$O/obj$M.$RA$RB/Vtb_l0r_rf" +mode=$MO +seed=$S +ncyc=${NCYC:-200000} > "$O/run${M}_$MO.log" 2>&1
r=$(grep -m1 "^L0R_RF" "$O/run${M}_$MO.log"); echo "$r mut=$M seed=$S"; grep -m3 MISMATCH "$O/run${M}_$MO.log"
if [ "$M" = 0 ]; then echo "$r" | grep -q " PASS "; else echo "$r" | grep -q " FAIL "; fi
