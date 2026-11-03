#!/usr/bin/env bash
# DIE-S81-51/RF-D 11-03: run_bk_g_rf.sh <out> [mut 0|1] [seed]  (from the source root; exit 0 = expected verdict)
set -u
OUT=$1; MUT=${2:-0}; SEED=${3:-1}; mkdir -p "$OUT"
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
D=""; [ "$MUT" = 1 ] && D="+define+OT_RFD_MUT_BKG"
B=rtl/dsrom_sys/s81_dv/unit
$V --binary --timing -j "${JOBS:-8}" -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD $D --top-module tb_dsdv_bk_g_rf -Mdir "$OUT/obj$MUT" \
  physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
  $B/ot_dsdv_vstop.sv $B/bk/dsdv_bk_v.sv $B/bk/dsdv_bk_g.sv $B/bk/test/tb_dsdv_bk_g_rf.sv > "$OUT/build$MUT.log" 2>&1 \
  || { echo "BKG_RF FAIL build"; tail -8 "$OUT/build$MUT.log"; exit 2; }
"$OUT/obj$MUT/Vtb_dsdv_bk_g_rf" +seed=$SEED +ncyc=${NCYC:-200000} > "$OUT/run$MUT.log" 2>&1
R=$(grep -m1 "^BKG_RF" "$OUT/run$MUT.log"); echo "$R mut=$MUT seed=$SEED"; grep -m3 MISMATCH "$OUT/run$MUT.log"
if [ "$MUT" = 0 ]; then echo "$R" | grep -q " PASS "; else echo "$R" | grep -q " FAIL "; fi
