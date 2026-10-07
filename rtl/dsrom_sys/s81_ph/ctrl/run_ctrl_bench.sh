#!/bin/bash
# CLAUDE S81-PH ctrl v2 exact gate: tb_dsfd_ctrl (transaction-level: per-PC request sequence, per-PC response order,
# response set vs a reference PHY, write-done counts, credits, status) on the tiled dsfd_ctrl (32 dsfd_ctrl_pc +
# dsfd_ctrl_ctr).  Run from the repo root.
#   run_ctrl_bench.sh <out> <mutant-define|none> <ckh_ps> <seed> [n] [threads]
set -u
O=$1; M=$2; H=$3; SEED=$4; N=${5:-48}; T=${6:-4}
mkdir -p $O
D=""; [ "$M" != none ] && D="+define+$M"
verilator --binary --timing -j $T --top-module tb_dsfd_ctrl -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -O2 $D -GCKH_PS=$H \
  --Mdir $O/obj rtl/dsrom_sys/s81_ph/test/tb_dsfd_ctrl.sv rtl/dsrom_sys/s81_ph/test/ot_s81ph_phy_on_bus.sv \
  rtl/dsrom_sys/s81_ph/dsfd_ctrl.sv rtl/dsrom_sys/s81_ph/ctrl/dsfd_ctrl_pc.sv rtl/dsrom_sys/s81_ph/ctrl/dsfd_ctrl_ctr.sv \
  rtl/dsrom_sys/s81_ph/ot_s81ph_ctrl_pc.sv rtl/dsrom_sys/s81_ph/ot_s81ph_afifo.sv \
  rtl/chip/ot_chip_v41x_hbm3e_phy.sv rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv rtl/hdc/kv/ot_hdc_hbm_model.sv > $O/build.log 2>&1 || { echo BUILD_FAILED; tail -5 $O/build.log; exit 2; }
$O/obj/Vtb_dsfd_ctrl +seed=$SEED +n=$N > $O/run.log 2>&1
rc=$?
grep -E "TB_DSFD_CTRL|latency" $O/run.log | tail -4
grep -q "TB_DSFD_CTRL PASS" $O/run.log && [ $rc -eq 0 ] && exit 0
exit 1
