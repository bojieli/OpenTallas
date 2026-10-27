#!/bin/bash
# HBM-EP-CAL-1 hfd_ep_static: CTS only (do-cts, no upstream remake; plan-built sized tree) + post-CTS FF hold gate + insertion TT/FF (placement RC).
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd)
docker run --rm --name epcal1-cts-$$ --cpus=8 --memory=8g --memory-swap=8g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; M=\"make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8\"; \$M do-cts; rc=\$?; \
 C=\$(ls /work/run/results/asap7/*/base/4_cts.odb 2>/dev/null | head -1); if [ \$rc = 0 ] && [ -n \"\$C\" ]; then S=\$(ls /work/run/results/asap7/*/base/4_cts.sdc | head -1); \
 PLIBS=\"\$(\$M print-BC_LIB_FILES 2>/dev/null | sed -n \"s/^BC_LIB_FILES *[:=] *//p\")\" ODB=\$C SDC=\$S PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7 OT_VCLK_TT=250 OT_VCLK_FF=202.5 LAYER_PARASITICS_FILE=/work/setRC_rcx.tcl openroad -exit /work/hold_gate.tcl > /work/hold_gate.log 2>&1; grep OT_HOLD_GATE /work/hold_gate.log; \
 for c in TT FF; do OT_CORNER=\$c ODB=\$C SDC=\$S PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7 LAYER_PARASITICS_FILE=/work/setRC_rcx.tcl openroad -exit /work/measure_ins_r5.tcl > /work/ins_\$c.log 2>&1; grep OT_R5_INS /work/ins_\$c.log; done; fi; \
 chown -R $(id -u):$(id -g) /work; exit \$rc" > "$K/cts_r5.log" 2>&1
rc=$?; grep -h "OT_HOLD_GATE\|OT_R5_INS\|OT_MS\|Error\|ERROR" $K/cts_r5.log | tail -20; exit $rc
