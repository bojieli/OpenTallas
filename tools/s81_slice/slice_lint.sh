#!/bin/bash
# slice_lint.sh <outdir> [HB] (cwd = repo root): S81-TILES6 elaboration of the WHOLE slice ot_s81sl_slice (5 beat leaves
# ot_s81sl_leaf + xg (rstop + xs) + xr1/xr3 + cap + xfin + relays) under verilator --lint-only.  Exit 0 = no error and no
# PINMISSING / PINNOCONNECT / PINCONNECTEMPTY / PINNOTFOUND warning in the slice RTL (rtl/dsrom_sys/s81_dv); the closed
# arithmetic libraries' unused-output pins (ot_hdc_* vo etc.) are outside the slice and not counted; xs_ctl's two open
# ot_v41_inc carry OUTPUTS (co, production text) are unused outputs, not open inputs.
# S81SL_LINT_SYN=1: the hard-macro (kit) view instead -- +define+SYNTHESIS with the parameterless ROM black box
# ot_rom_4096x72_m8_bb.v (the xs ROMs then carry no INSTANCE parameter); TOP=<module> lints a sub-leaf (e.g. ot_s81sl_xg).
set -u; O=$1; HB=${2:-0}; mkdir -p $O; TOP=${TOP:-ot_s81sl_slice}; SYN=${S81SL_LINT_SYN:-0}; TAG=hb${HB}_${TOP}_syn$SYN
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
MACV="physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v"
DEF=""; GHB=""; [ $TOP = ot_s81sl_slice ] && GHB="-GHB=$HB"
srcs="$(cat physical/hbm_norm_split_20261008/sources.f rtl/dsrom_sys/s81_dv/slice/test/leaf_bench.f rtl/dsrom_sys/s81_dv/slice/test/slice_extra.f | awk '!s[$0]++' | tr '\n' ' ') $MACV rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv"
[ $SYN = 1 ] && { DEF="+define+SYNTHESIS"; srcs="${srcs//ot_rom_4096x72_m8\/ot_rom_4096x72_m8.v/ot_rom_4096x72_m8\/ot_rom_4096x72_m8_bb.v}"; }
$V --lint-only -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTITOP -Wwarn-PINCONNECTEMPTY -Wwarn-PINNOCONNECT \
  +define+DSFD_PQ_STATIC_X2 $DEF --top-module $TOP $GHB $srcs > $O/lint_$TAG.log 2>&1; rc=$?
{ grep -E "^%Error" $O/lint_$TAG.log | grep -v "Command Failed" | cut -c1-300; grep -E "PINMISSING|PINNOCONNECT|PINCONNECTEMPTY|PINNOTFOUND" $O/lint_$TAG.log | grep -E "s81_dv/|s81sl" | grep -v "ot_s81sl_xs_ctl.sv.*empty reference: 'co'" | cut -c1-300; } > $O/lint_$TAG.bad
echo "verilator rc=$rc errors/pin warnings=$(wc -l < $O/lint_$TAG.bad)"; head -30 $O/lint_$TAG.bad
[ $rc = 0 ] && [ ! -s $O/lint_$TAG.bad ] && { echo "SLICE_LINT PASS $TAG"; exit 0; }; echo "SLICE_LINT FAIL $TAG"; exit 1
