#!/usr/bin/env bash
# DIE-S81-51/RF-D 11-03: run_bk_g_rf.sh <out> [mut 0|1|2] [seed] [RA] [RB]  (from the source root; exit 0 = expected verdict)
#   mut 1 = vstop FPIPE mutant (OT_RFD_MUT_BKG), mut 2 = vin LPIPE mutant (OT_RFD_MUT_VIN), mut 3 = RF 3 posedge out-face, mut 4 = RF 4 without its out-face, mut 5 = LPIPE 2 copy mutant, mut 6 = RF 5 posedge strap face; default forms RA 0 / RB 1
set -u
OUT=$1; MUT=${2:-0}; SEED=${3:-1}; RA=${4:-0}; RB=${5:-1}; mkdir -p "$OUT"
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
D=""; [ "$MUT" = 1 ] && D="+define+OT_RFD_MUT_BKG"; [ "$MUT" = 2 ] && D="+define+OT_RFD_MUT_VIN"; [ "$MUT" = 3 ] && D="+define+OT_RFD_MUT_OF3"; [ "$MUT" = 4 ] && D="+define+OT_RFD_MUT_OF4"; [ "$MUT" = 5 ] && D="+define+OT_RFD_MUT_LP2"; [ "$MUT" = 6 ] && D="+define+OT_RFD_MUT_SF5"
B=rtl/dsrom_sys/s81_dv/unit
$V --binary --timing -j "${JOBS:-8}" -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD $D -GRA=$RA -GRB=$RB --top-module tb_dsdv_bk_g_rf -Mdir "$OUT/obj$MUT.$RA$RB" \
  physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
  $B/ot_dsdv_vstop.sv $B/bk/dsdv_bk_v.sv $B/bk/dsdv_bk_g.sv $B/bk/test/tb_dsdv_bk_g_rf.sv > "$OUT/build$MUT.log" 2>&1 \
  || { echo "BKG_RF FAIL build"; tail -8 "$OUT/build$MUT.log"; exit 2; }
"$OUT/obj$MUT.$RA$RB/Vtb_dsdv_bk_g_rf" +seed=$SEED +ncyc=${NCYC:-200000} > "$OUT/run$MUT.log" 2>&1
R=$(grep -m1 "^BKG_RF" "$OUT/run$MUT.log"); echo "$R mut=$MUT seed=$SEED"; grep -m3 MISMATCH "$OUT/run$MUT.log"
if [ "$MUT" = 0 ]; then echo "$R" | grep -q " PASS "; else echo "$R" | grep -q " FAIL "; fi
