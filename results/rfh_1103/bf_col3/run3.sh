#!/usr/bin/env bash
# DIE-S81-51/RF-H 11-03 3-core bf_col lockstep: run3.sh <repo root> <out> [mut 0|1|2] [seed] [free 1|0]
#   mut 1 = RFH3_MUTANT_EQ (FP partial data one cycle early vs its valid), mut 2 = RFH3_MUTANT_FACE (half drops slot-1 valids),
#   mut 3 = RFH3_MUTANT_ZE=${ZEMUT:-8} (half gate enable late; run with free 0: words hit a closed gate)
set -u
R=$1; O=$2; M=${3:-0}; S=${4:-1}; F=${5:-1}; mkdir -p "$O/rom$S"
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
D=""; [ "$M" = 1 ] && D="+define+RFH3_MUTANT_EQ"; [ "$M" = 2 ] && D="+define+RFH3_MUTANT_FACE"; [ "$M" = 3 ] && D="+define+RFH3_MUTANT_ZE=${ZEMUT:-8}"
python3 $R/results/rfh_1103/bf_col3/mkrom.py "$O/rom$S" $S
L=$R/rtl/v41rom
SRC=$(python3 -c "import json;print(' '.join('$R/'+s for s in json.load(open('$R/physical/die_plan/s81/cores/legacy/specs/ot_v41_bf_col/spec.json'))['sources'] if not s.endswith('_bb.v')))")
if [ ! -x "$O/obj$M/Vtb" ]; then
$V --binary --timing -j "${JOBS:-16}" -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD $D --top-module tb -Mdir "$O/obj$M" \
  $SRC $R/physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v $L/ot_v41_bf16_half.sv $L/ot_v41_bf_col3_c.sv $L/ot_v41_bf_col3.sv \
  $R/results/rfh_1103/bf_col3/tb_col3.sv > "$O/build$M.log" 2>&1 || { echo "COL3 FAIL build"; tail -15 "$O/build$M.log"; exit 2; }
fi
"$O/obj$M/Vtb" +seed=$S +cycles=${NCYC:-100000} +free=$F +OT_ROM_DIR=$O/rom$S > "$O/run${M}_${S}_$F.log" 2>&1
r=$(grep -m1 "^COL3" "$O/run${M}_${S}_$F.log"); echo "$r mut=$M seed=$S"; grep -m3 "MISMATCH\|LATENCY\|EXTRA\|COUNT\|QY_BKF" "$O/run${M}_${S}_$F.log"
if [ "$M" = 0 ]; then echo "$r" | grep -q " PASS "; else echo "$r" | grep -q " FAIL "; fi
