#!/bin/bash
# CORE-HBM: run_core_sta.sh KITDIR CORNER(TC|BC) -- post-route STA probe of a core kit, docker memory cap (diagnostic,
# owner 10-23 checks rule).  Output KITDIR/sta_<CORNER>/run.log (CORE_STA line).
K=$(readlink -f $1); C=$2; S=$(dirname $(readlink -f $0)); O=$K/sta_$C; mkdir -p $O
docker run --rm --name corehbm-sta-$(basename $K | tr -c 'A-Za-z0-9_\n' '_' | cut -c1-40)-$C --cpus=4 --memory=24g --memory-swap=24g \
 -v $K:/work -v $S:/s -v $O:/out -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
 make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base CORNER=$C OUTD=/out LOG_DIR=/out REPORTS_DIR=/out RUN_SCRIPT=/s/core_sta.tcl RUN_LOG_NAME_STEM=sta run; chown -R $(id -u):$(id -g) /out" > $O/run.log 2>&1
echo "rc=$? $K $C"; grep -E "CORE_STA|Error" $O/run.log | head -3
