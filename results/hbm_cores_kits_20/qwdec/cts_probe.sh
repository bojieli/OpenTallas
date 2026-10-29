#!/bin/bash
# HBM-CORES-KITS-20 CTS-only what-if from the retained 3_place (mirrors run_kit_hbm.sh cts + hold_gate lines)
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /OpenROAD-flow-scripts/flow
M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8"
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1 || { echo MMFAIL; exit 9; }
touch /work/run/results/asap7/*/base/*
$M cts > /work/probe_cts.log 2>&1; echo "cts rc $?"
C=$(ls /work/run/results/asap7/*/base/4_cts.odb | head -1); S=$(ls /work/run/results/asap7/*/base/4_cts.sdc | head -1)
PLIBS="$($M print-BC_LIB_FILES 2>/dev/null | sed -n 's/^BC_LIB_FILES *[:=] *//p')" ODB=$C SDC=$S PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7 \
  OT_VCLK_TT=$(sed -n 's/^export OT_VCLK_TT = //p' /work/config.mk) OT_VCLK_FF=$(sed -n 's/^export OT_VCLK_FF = //p' /work/config.mk) \
  LAYER_PARASITICS_FILE=$(sed -n 's/^export LAYER_PARASITICS_FILE = //p' /work/config.mk) \
  openroad -exit /work/hold_gate.tcl > /work/hold_gate.log 2>&1
grep -h "OT_F4" /work/run/logs/asap7/*/base/4_1_cts.log; grep OT_HOLD_GATE /work/hold_gate.log
chown -R $HUID:$HGID /work
