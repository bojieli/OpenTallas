#!/bin/bash
# PATH-QC-A0N59: the kit's own post-CTS FF structural hold gate (run_kit.sh lines 44-50), rerun read-only
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /OpenROAD-flow-scripts/flow
M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base'
C=$(ls /work/run/results/asap7/*/base/4_cts.odb | head -1); S=$(ls /work/run/results/asap7/*/base/4_cts.sdc | head -1)
g() { sed -n "s/^export $1 = //p" /work/config.mk; }
PLIBS="$($M print-BC_LIB_FILES 2>/dev/null | sed -n 's/^BC_LIB_FILES *[:=] *//p')" ODB="$C" SDC="$S" PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7 \
 OT_VCLK_TT=$(g OT_VCLK_TT) OT_VCLK_FF=$(g OT_VCLK_FF) OT_HOLD_IN_MIN=$(g OT_HOLD_IN_MIN) OT_HOLD_OUT_MIN=$(g OT_HOLD_OUT_MIN) \
 LAYER_PARASITICS_FILE=$(g LAYER_PARASITICS_FILE) openroad -exit /hclass.tcl > /tmp/h.log 2>&1; rc=$?; grep -E "HCLASS|WORST|Error" /tmp/h.log | head -30


