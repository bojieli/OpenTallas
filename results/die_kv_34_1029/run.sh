#!/bin/bash
B=/srv/opentallas-scratch2/claude/die-kv-34-1029/edgesA; A=/srv/opentallas-scratch2/claude/codex-kv-1355/A
for C in TT FF; do mkdir -p $B/out_$C
docker run --rm --name dkv34-edgesA-$C --memory=32g --memory-swap=32g --cpus=8 -e CORNER=$C -v $A:/n:ro -v $B:/w -v $B/out_$C:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /w/read.tcl > /out/read_$C.log 2>&1; echo EXIT \$? >> /out/read_$C.log; chown -R 1000:1000 /out" &
done; wait; echo EDGES_DONE $(date)
