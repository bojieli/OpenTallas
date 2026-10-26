#!/bin/bash
# ab.sh KIT OUT MODE(A|B) [IO_HOLD_TCL]: post-CTS FF hold gate + census on KIT's 4_cts.odb, kit mounted read-only.
set -uo pipefail
K=$1; O=$2; MODE=$3; IOH=${4:-}
mkdir -p $O; cp /srv/opentallas-scratch2/claude/io-hold/probe/census.tcl $O/
cp /srv/opentallas-scratch2/claude/wt/io-hold-1025/tools/die_plan/hold_gate.tcl $O/hold_gate.tcl
cp $K/vclk_corner.tcl $O/; [ -f $K/setRC_rcx.tcl ] && cp $K/setRC_rcx.tcl $O/
rm -f $O/io_hold.tcl; [ "$MODE" = B ] && cp $IOH $O/io_hold.tcl
docker run --rm --name iohold-ab-$(basename $K)-$MODE-$$ --cpus=4 --memory=12g --memory-swap=12g -v $K:/work:ro -v $O:/probe \
  -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/tmp/run FLOW_VARIANT=base'; \
  C=\$(ls /work/run/results/asap7/*/base/4_cts.odb | head -1); S=\$(ls /work/run/results/asap7/*/base/4_cts.sdc | head -1); \
  PLIBS=\"\$(\$M print-BC_LIB_FILES 2>/dev/null | sed -n 's/^BC_LIB_FILES *[:=] *//p')\" ODB=\$C SDC=\$S PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7 \
  OT_VCLK_FF=\$(sed -n 's/^export OT_VCLK_FF = //p' /work/config.mk) \
  OT_HOLD_IN_MIN=\$(sed -n 's/^export OT_HOLD_IN_MIN = //p' /work/config.mk) OT_HOLD_OUT_MIN=\$(sed -n 's/^export OT_HOLD_OUT_MIN = //p' /work/config.mk) \
  LAYER_PARASITICS_FILE=\$( [ -f /probe/setRC_rcx.tcl ] && echo /probe/setRC_rcx.tcl ) \
  openroad -exit /probe/census.tcl" > $O/probe.log 2>&1
rc=$?; grep -E "OT_HOLD_GATE|OT_IO_HOLD|CENSUS|GATE_ERROR" $O/probe.log; echo "AB_DONE $MODE rc=$rc"
