#!/usr/bin/env bash
# STW-S81c-COLLA3-LEP w14: lockstep equivalence bench (cwd = repo root).  run_eq.sh OUTDIR SEED [MUT] [NCYC]
# DUT = ot_s81sl_slice_lep.sv with NFACE/RSTHD/RPRLY/META4 + the w14 opt-ins (WRLY VQREP SELST PUSHREP FHLA);
# REF = the same file with every module renamed rf_* and the w14 opt-in names disabled (= the current RTL).
set -u
O=$(realpath -m "${1:?outdir}"); S=${2:-1}; M=${3:-none}; N=${4:-40000}; mkdir -p "$O"
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
SL=rtl/dsrom_sys/s81_dv/slice
sed -e 's/\bot_s81sl_/rf_s81sl_/g' -e 's/OT_S81SL_LEP_\(WRLY\|VQREP\|SELST\|PUSHREP\|FHLA\)\b/OT_REF_OFF_\1/g' \
    -e 's/OT_S81SL_LEP_MUT_/OT_REF_OFF_MUT_/g' $SL/ot_s81sl_slice_lep.sv > $O/ref_lep.sv
D="+define+OT_S81SL_LEP_NFACE +define+OT_S81SL_LEP_RSTHD +define+OT_S81SL_LEP_RPRLY +define+OT_S81SL_LEP_META4 +define+OT_S81SL_TX_GROUP_ASSERT"
D="$D ${W14_DEFS:-+define+OT_S81SL_LEP_WRLY +define+OT_S81SL_LEP_VQREP +define+OT_S81SL_LEP_SELST +define+OT_S81SL_LEP_PUSHREP +define+OT_S81SL_LEP_FHLA}"
[ "$M" != none ] && D="$D +define+OT_S81SL_LEP_MUT_$M"
SRCS="rtl/lib/ot_rst_relay_tree3.sv rtl/lib/ot_sram_oldread_wreg.sv rtl/lib/ot_sram_showahead_1r1w.sv rtl/lib/ot_rst_relay.sv
 rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v
 physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v
 $SL/ot_s81sl_slice_lep.sv $O/ref_lep.sv tools/s81_dv/lepmuh_w14_1022/tb_lepmuh_w14_eq.sv"
R=eq_${M}_$S
$V --version
$V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style $D -GSEED=$S -GNCYC=$N \
  --top-module tb_lepmuh_w14_eq -Mdir $O/obj_$R $SRCS --build-jobs ${J:-2} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" \
  > $O/build_$R.log 2>&1 || { grep -m10 %Error $O/build_$R.log; echo "BUILD_FAILED $R"; exit 3; }
$O/obj_$R/Vtb_lepmuh_w14_eq > $O/run_$R.log 2>&1
grep -E "^(LEPMUH_W14_EQ|MISMATCH|EQ_PASS|EQ_FAIL)|%Fatal" $O/run_$R.log | head -14
grep -q "^EQ_PASS" $O/run_$R.log && { echo "BENCH_PASS w14eq MUT=$M seed $S"; exit 0; }
echo "BENCH_FAIL w14eq MUT=$M seed $S"; exit 1
