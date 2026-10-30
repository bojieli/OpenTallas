#!/bin/bash
set -uo pipefail
K=/srv/opentallas-scratch2/claude/codex-ectl-1030/q2_flow6b
D=/srv/opentallas-scratch2/claude/codex-ectl-1030/q2_qual50
pids=()
for c in TT FF; do
 docker run --rm --name codex-q2qual-$c-1030 --cpus=4 --memory=12g --memory-swap=12g -e OT_C=$c -e OMP_NUM_THREADS=4 -v "$K":/work:ro -v "$D":/deck:ro -v "$D/${c}2":/out -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; M="make -s DESIGN_CONFIG=/work/config.mk WORK_HOME=/tmp/q2qual FLOW_VARIANT=base"; pv(){ $M print-$1 2>/dev/null | sed "s/^[A-Z_]*: //"; }; field=TC_LIB_FILES; [ "$OT_C" = FF ] && field=BC_LIB_FILES; export OT_LIBS="$(pv $field)" OT_DMIN="$(pv MIN_ROUTING_LAYER)" OT_DMAX="$(pv MAX_ROUTING_LAYER)" OT_CMIN="$(pv MIN_CLK_ROUTING_LAYER)" OT_CMAX="$(pv MAX_CLK_ROUTING_LAYER)" OT_ADJ="$(pv ROUTING_LAYER_ADJUSTMENT)"; openroad -exit /deck/q2_qual.tcl' > "$D/${c}2/qual.log" 2>&1 &
 pids+=($!)
done
rc=0
for p in "${pids[@]}"; do wait "$p" || rc=1; done
docker run --rm -v "$D":/out openroad/orfs:asap7lock chown -R 1000:1000 /out
exit "$rc"
