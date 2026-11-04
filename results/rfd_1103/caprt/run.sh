#!/usr/bin/env bash
# DIE-S81-51/RF-D 11-03 S81-044 cap_rt RF2: run.sh <out> [mut 0|1|2] [seed] [RA] [RB]  (from the source root; exit 0 = expected)
#   mut 1 = OT_RFD_MUT_CAP2 (h column misses the same-edge write), mut 2 = OT_RFD_MUT_CAP2B (A one-hot = B group)
set -u
OUT=$1; MUT=${2:-0}; SEED=${3:-1}; RA=${4:-1}; RB=${5:-2}; mkdir -p "$OUT"
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
D=""; [ "$MUT" = 1 ] && D="+define+OT_RFD_MUT_CAP2"; [ "$MUT" = 2 ] && D="+define+OT_RFD_MUT_CAP2B"
S=rtl/dsrom_sys/s81_dv/slice
$V --binary --timing -j "${JOBS:-8}" -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD +define+OT_S81_CAP_RT_RF1 +define+OT_S81_CAP_RT_FACE_REGS $D \
  -GRA=$RA -GRB=$RB -GSEED=$SEED -GN=${N:-200000} --top-module tb_ot_s81sl_cap_rt_rf1 -Mdir "$OUT/obj$MUT.$RA$RB.$SEED" \
  rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_delay.sv rtl/proto/ot_fp32_add_rne_pipe.sv \
  physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v \
  $S/ot_s81sl_cap_rt.sv $S/lp/tb_ot_s81sl_cap_rt_rf1.sv > "$OUT/build$MUT.$RA$RB.$SEED.log" 2>&1 \
  || { echo "RF1_LOCKSTEP FAIL build"; grep -m6 -i error "$OUT/build$MUT.$RA$RB.$SEED.log" | cut -c1-250; exit 2; }
"$OUT/obj$MUT.$RA$RB.$SEED/Vtb_ot_s81sl_cap_rt_rf1" > "$OUT/run$MUT.$RA$RB.$SEED.log" 2>&1
R=$(grep -m1 "^RF1_LOCKSTEP cycles" "$OUT/run$MUT.$RA$RB.$SEED.log"); V2=$(grep -m1 -E "^RF1_LOCKSTEP (PASS|FAIL)" "$OUT/run$MUT.$RA$RB.$SEED.log")
echo "$V2 | $R | ra=$RA rb=$RB mut=$MUT seed=$SEED"; grep -m3 MISMATCH "$OUT/run$MUT.$RA$RB.$SEED.log"
if [ "$MUT" = 0 ]; then echo "$V2" | grep -q PASS; else echo "$V2" | grep -q FAIL; fi
