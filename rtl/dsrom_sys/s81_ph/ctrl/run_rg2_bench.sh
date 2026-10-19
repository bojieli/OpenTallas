#!/bin/bash
# S81-CTRL 10-17 exact gate of the regional controller dsfd_ctrl_rg2: tb_dsfd_ctrl (the S81-PH controller bench:
# per-PC request sequence at the PHY, per-PC response order, response set vs a reference PHY, write-done counts,
# credits, status, mid-run reset) on 16 x dsfd_ctrl_rg2 (bench composition dsfd_ctrl_rg2x16, define S81CTRL_RG2).
# Run from the repo root.
#   run_rg2_bench.sh <out> <mutant-define|none> <ckh_ps> <seed> [n] [threads]
set -u
command -v verilator >/dev/null || { echo "NO_VERILATOR on $(hostname)"; exit 3; }
O=$1; M=$2; H=$3; SEED=$4; N=${5:-48}; T=${6:-4}
mkdir -p $O
D="+define+S81CTRL_RG2"; [ "$M" != none ] && D="$D +define+$M"
verilator --binary --timing -j $T --top-module tb_dsfd_ctrl -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -O2 $D -GCKH_PS=$H \
  --Mdir $O/obj rtl/dsrom_sys/s81_ph/test/tb_dsfd_ctrl.sv rtl/dsrom_sys/s81_ph/test/ot_s81ph_phy_on_bus.sv \
  rtl/dsrom_sys/s81_ph/test/dsfd_ctrl_rg2x16.sv rtl/dsrom_sys/s81_ph/ctrl/dsfd_ctrl_rg2.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv \
  rtl/dsrom_sys/s81_ph/ot_s81ph_ctrl_pc.sv rtl/dsrom_sys/s81_ph/ot_s81ph_afifo.sv \
  rtl/chip/ot_chip_v41x_hbm3e_phy.sv rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv rtl/hdc/kv/ot_hdc_hbm_model.sv > $O/build.log 2>&1 || { echo BUILD_FAILED; tail -5 $O/build.log; exit 2; }
$O/obj/Vtb_dsfd_ctrl +seed=$SEED +n=$N > $O/run.log 2>&1
rc=$?
grep -E "TB_DSFD_CTRL|latency" $O/run.log | tail -4
grep -q "TB_DSFD_CTRL PASS" $O/run.log && [ $rc -eq 0 ] && exit 0
exit 1
