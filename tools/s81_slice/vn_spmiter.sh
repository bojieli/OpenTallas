#!/bin/bash
# vn_spmiter.sh <outdir> [base|c1|hq] [CYC]  (cwd = repo root): S81/RTLSPLIT miter bench tb_s81sl_vn_spmiter -- the
# two-core split ot_s81sl_vn_sp (vn_a + vn_b) against the unsplit ot_s81sl_vn on random static-schedule stimulus:
# hq / y / fault on the same edge, p 2 edges later.  base must print "MITER PASS"; c1 / hq (split mutants) must print
# "MITER FAIL".  Exit 0 = the expected verdict.
set -u; O=$1; M=${2:-base}; N=${3:-40000}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
DEF=""; [ "$M" = c1 ] && DEF="+define+OT_S81SL_SPMUT_C1"; [ "$M" = hq ] && DEF="+define+OT_S81SL_SPMUT_HQ"
MACV=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
srcs="$(sort -u physical/hbm_norm_split_20261008/sources.f | tr '\n' ' ') $MACV rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vn.sv rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_vn_spmiter.sv"
$V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD $DEF -GCYC=$N --top-module tb_s81sl_vn_spmiter -Mdir $O/obj $srcs \
  --build-jobs ${J:-4} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 || { echo "BUILD_FAILED"; tail -n 8 $O/build.log; exit 3; }
$O/obj/Vtb_s81sl_vn_spmiter > $O/run.log 2>&1
grep -E "^MITER" $O/run.log | head -8
if [ "$M" = base ]; then grep -q '^MITER PASS' $O/run.log && { echo "PASS vn spmiter"; exit 0; }; echo "FAIL vn spmiter"; exit 1; fi
grep -q '^MITER FAIL' $O/run.log && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED $M"; exit 0; }; echo "NEGATIVE_CONTROL_PASSED $M (bench blind)"; exit 1
