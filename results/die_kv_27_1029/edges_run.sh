#!/bin/bash
# DIE-KV-27: Codex codex-clock-components-1028 edge readout (die_trial clock_edge_readout form, OT_EDGES v1) on the DIE-KV-26 e26a GRT (tree c, same ctree.v)
B=/srv/opentallas-scratch2/claude/die-kv-27-1029/edges; K=/srv/opentallas-scratch2/claude/die-kv-26-1029/kit_e26a
for C in TT FF; do
  docker run --rm --name dkv27-edges-$C --memory=32g --memory-swap=32g --cpus=4 -e CORNER=$C -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM \
    -v $K:/work:ro -v /srv/opentallas-scratch2/claude/die-kv-26-1029/out_e26a_$C:/input:ro -v $B:/out openroad/orfs:asap7lock \
    bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /out/read_$C.tcl; chown -R 1000:1000 /out" > $B/read_$C.log 2>&1 &
done; wait; echo EDGES_DONE $(date)
