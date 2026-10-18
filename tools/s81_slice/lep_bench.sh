#!/bin/bash
# lep_bench.sh <outdir> [MUT none|swap|nopair|noovf] [SEED]  (cwd = repo root): RTL-BUILD-S81 end-slice link-port bench
# (tb_s81sl_lep: two dies, ot_s81sl_lep + 2 x dsfd_coll_lane_{w,e} + 2 x ot_pdie_ucie each, both directions).
# MUT none must PASS; swap / nopair / noovf must FAIL (^FAIL lep).  Exit 0 = PASS line only (raw verdict).
set -u; O=$1; M=${2:-none}; S=${3:-1}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
D=""; case $M in swap) D="+define+OT_S81SL_LEP_MUT_SWAP";; nopair) D="+define+OT_S81SL_LEP_MUT_NOPAIR";; noovf) D="+define+OT_S81SL_LEP_MUT_NOOVF";; esac
srcs="rtl/link/ot_link_crc32.sv rtl/common/ot_link_credit.sv rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv
 rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_skid2.sv
 rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane.sv rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v
 rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_lep.sv"
$V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN $D -GSEED=$S --top-module tb_s81sl_lep \
  -Mdir $O/obj_$M $srcs --build-jobs ${J:-4} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build_$M.log 2>&1 \
  || { echo "BUILD_FAILED"; grep -m8 -E "%Error" $O/build_$M.log; exit 3; }
$O/obj_$M/Vtb_s81sl_lep > $O/run_$M.log 2>&1
grep -E "^LEP_STATS|^MISMATCH|^PASS|^FAIL" $O/run_$M.log | head -12
# raw verdict (the loop's expect=pass / expect=fail decides): exit 0 only on the PASS line
grep -q '^PASS lep' $O/run_$M.log && { echo "BENCH_PASS lep MUT=$M seed $S"; exit 0; }; echo "BENCH_FAIL lep MUT=$M seed $S"; exit 1
