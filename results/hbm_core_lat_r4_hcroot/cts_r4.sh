#!/bin/bash
# HBM-CORE-LAT-R4 hcp_sys1: CTS only (plan-built tree, do-cts: no upstream remake) + post-CTS FF hold gate (kit hold_gate.tcl).
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd)
docker run --rm --name hcr4-cts-hcp_sys1-$$ --cpus=8 --memory=20g --memory-swap=20g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; M=\"make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8\"; \$M do-cts; rc=\$?; \
 C=\$(ls /work/run/results/asap7/*/base/4_cts.odb 2>/dev/null | head -1); if [ \$rc = 0 ] && [ -n \"\$C\" ]; then S=\$(ls /work/run/results/asap7/*/base/4_cts.sdc | head -1); \
 PLIBS=\"\$(\$M print-BC_LIB_FILES 2>/dev/null | sed -n \"s/^BC_LIB_FILES *[:=] *//p\")\" ODB=\$C SDC=\$S PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7 OT_VCLK_TT=251 OT_VCLK_FF=203.3 LAYER_PARASITICS_FILE=/work/setRC_rcx.tcl openroad -exit /work/hold_gate.tcl > /work/hold_gate.log 2>&1; grep OT_HOLD_GATE /work/hold_gate.log; fi; \
 chown -R $(id -u):$(id -g) /work; exit \$rc" > "$K/cts_r4.log" 2>&1
