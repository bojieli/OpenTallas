#!/bin/bash
# S81-CTRL 10-17 exact gate of the regional controller dsfd_ctrl_rg2: tb_dsfd_ctrl (the S81-PH controller bench:
# per-PC request sequence at the PHY, per-PC response order, response set vs a reference PHY, write-done counts,
# credits, status, mid-run reset) on 16 x dsfd_ctrl_rg2 (bench composition dsfd_ctrl_rg2x16, define S81CTRL_RG2).
# Run from the repo root.
# Build cost (S81-SAFE-FIX/CTRL 10-19): under Verilator 5.050 (the daemon's) the -O1 build of 5-6 MB root .cpp files ran
# > 1 h per file on a loaded host: the C++ is now split (--output-split 20000, --output-split-cfuncs 2000) and compiled at -O0.
# Earlier (S81-CTRL3 10-18): the 16-instance composition verilates to ~270 MB of C++; at the default -Os/-O2 g++
# levels with -j 4 on a loaded host one build took 6.5 h and cc1plus was then terminated (job s81ctrl_rg2-c1-6e188c155
# read that as "mutant rc=2").  The C++ is now compiled at -O1 (slow paths -O0) with -j T: build ~1 min, exact ~20 s, MUT_RD ~10 min (two 400k-cycle phase timeouts), and a
# build or sim killed by a signal / OOM exits 137 (a crash the loop retries), never 2 (bench error) or 1 (detected).
#   run_rg2_bench.sh <out> <mutant-define|none> <ckh_ps> <seed> [n] [threads]
set -u
command -v verilator >/dev/null || { echo "NO_VERILATOR on $(hostname)"; exit 3; }
O=$1; M=$2; H=$3; SEED=$4; N=${5:-48}; T=${6:-4}
mkdir -p $O
D="+define+S81CTRL_RG2"; [ "$M" != none ] && D="$D +define+$M"
[ "${S81CTRL_FIFO_IMPL:-flop}" != sram ] || D="$D +define+S81CTRL_SRAM_FIFO"
[ "${S81CTRL_FIFO_IMPL:-flop}" != sram_p192 ] || D="$D +define+S81CTRL_SRAM_FIFO +define+S81CTRL_SRAM_P192"
verilator --binary --timing -j $T --top-module tb_dsfd_ctrl -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -O2 $D -GCKH_PS=$H \
  --output-split 20000 --output-split-cfuncs 2000 -MAKEFLAGS "OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0" \
  --Mdir $O/obj rtl/dsrom_sys/s81_ph/test/tb_dsfd_ctrl.sv rtl/dsrom_sys/s81_ph/test/ot_s81ph_phy_on_bus.sv \
  rtl/dsrom_sys/s81_ph/test/dsfd_ctrl_rg2x16.sv rtl/dsrom_sys/s81_ph/ctrl/dsfd_ctrl_rg2.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv \
  rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_afifo_g_sram.sv physical/asap7_memory_macros/ot_sram_1r1w2c_16x546_m1/ot_sram_1r1w2c_16x546_m1.v physical/asap7_memory_macros/ot_sram_1r1w2c_16x340_p192/ot_sram_1r1w2c_16x340_p192.v \
  rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_ctrl_pcr.sv rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_afifo_g.sv rtl/dsrom_sys/s81_ph/ot_s81ph_afifo.sv \
  rtl/chip/ot_chip_v41x_hbm3e_phy.sv rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv rtl/hdc/kv/ot_hdc_hbm_model.sv > $O/build.log 2>&1 || {
  if grep -qE "signal terminated program|Killed signal|Terminated|Cannot allocate memory|virtual memory exhausted" $O/build.log; then
    echo BUILD_CRASHED; tail -5 $O/build.log; exit 137; fi
  echo BUILD_FAILED; tail -5 $O/build.log; exit 2; }
$O/obj/Vtb_dsfd_ctrl +seed=$SEED +n=$N > $O/run.log 2>&1
rc=$?
[ $rc -ge 124 ] && { echo "SIM_CRASHED rc=$rc"; tail -3 $O/run.log; exit $rc; }
grep -E "TB_DSFD_CTRL|latency" $O/run.log | tail -4
grep -q "TB_DSFD_CTRL PASS" $O/run.log && [ $rc -eq 0 ] && exit 0
exit 1
