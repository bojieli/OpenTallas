#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-qc-kits-1847/variantB
K=$D/kit
docker run --rm --memory=24g --cpus=8 -v "$K":/work -v "$D":/eco -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 PRE_DETAIL_ROUTE_TCL=/eco/pre_drt.tcl POST_DETAIL_ROUTE_TCL=/work/f4g_post_drt.tcl do-5_2_route' > "$D/route.log" 2>&1
docker run --rm -v "$D":/eco openroad/orfs:asap7lock chown -R "$(id -u):$(id -g)" /eco
bash /srv/opentallas-scratch2/claude/codex-qc-kits-1847/tail.sh "$D"
