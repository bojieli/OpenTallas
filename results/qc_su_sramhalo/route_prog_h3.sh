#!/bin/bash
set -euo pipefail
K=$1
# Geometry reviewed on this exact inherited-placement/new-GRT checkpoint; continue it without a new place/CTS.
docker run --rm --name codex-prog-h3-route --cpus 8 --memory 20g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; for t in do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc do-6_1_fill do-6_1_fill.sdc do-6_report do-generate_abstract; do make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 "$t" || exit $?; done' > "$K/route_h3.log" 2>&1
echo "PROG_H3_ROUTE_DONE $(date -Is)" > "$K/h3_chain.txt"
# The normal AP chain owns native signoff/routed LEC/publication after this physical runner.
