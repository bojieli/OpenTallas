#!/bin/bash
# leaf_eng_bench.sh <outdir> [MUT 0|7|8] [SEED]  (cwd = repo root): RTL-BUILD-S81 Engram mix through ONE ot_s81sl_leaf
# (vp + vn + vq + vs op 14 ENG + ve; tb_s81sl_leaf_eng) on tools/s81_dv/ve_golden.py fixtures (hdc_golden_v41 chunk8).
# MUT 0 must PASS; MUT 7 / 8 (vs ENG negative controls) must FAIL.  Exit 0 = the expected verdict; RAW=1: exit 0 only on
# PASS (the closure loop's expect=fail form).
# S81-PLAN R3: S81SL_CST="-GCS_HI_D=2 ... +define+OT_S81SL_CST_MUT_*" = leaf station depths / station mutants
set -u; O=$1; M=${2:-0}; S=${3:-7}; mkdir -p $O/fx
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
python3 tools/s81_dv/ve_golden.py $O/fx --seed $S > $O/gold.log 2>&1 || { echo "BENCH_SETUP_FAILED gold"; tail -5 $O/gold.log; exit 4; }
MACV="physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v"
srcs="${S81_VS_EXTRA_SOURCES:-} rtl/lib/ot_rst_relay_tree3.sv $(cat physical/hbm_norm_split_20261008/sources.f rtl/dsrom_sys/s81_dv/slice/test/leaf_bench.f | sort -u | tr '\n' ' ') $MACV
 rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve_fp.sv rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve.sv
 rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_leaf_eng.sv"
$V ${S81_VS_DEFS:-} --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD ${S81SL_CST:-} -GMUT=$M --top-module tb_s81sl_leaf_eng -Mdir $O/obj $srcs \
  --build-jobs ${J:-4} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 || { echo "BUILD_FAILED"; tail -n 12 $O/build.log; exit 3; }
grep -E "PINMISSING|PINCONNECTEMPTY|PINNOCONNECT" $O/build.log | grep -i "s81sl_leaf\|s81sl_vs\|s81sl_ve" | head -5
$O/obj/Vtb_s81sl_leaf_eng +dir=$O/fx > $O/run.log 2>&1
grep -E "^LEAFENG|MISMATCH|TIMEOUT|^PASS|^FAIL" $O/run.log | head -20
if [ "$M" = 0 ] || [ -n "${RAW:-}" ]; then grep -q '^PASS' $O/run.log && { echo "PASS leaf_eng MUT=$M seed=$S"; exit 0; }; echo "FAIL leaf_eng MUT=$M"; exit 1; fi
grep -q '^FAIL' $O/run.log && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED MUT=$M"; exit 0; }; echo "NEGATIVE_CONTROL_PASSED MUT=$M (bench blind)"; exit 1
