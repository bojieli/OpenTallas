#!/bin/bash
# LAND-KV-1: combined die GRT (signals M4-M7 kit adjustments + region clock trees M8-M9) TT+FF, 50 it, critical_nets 0
O=/srv/opentallas-scratch2/claude/land-kv-1027
for C in TT FF; do
docker run -d --name landkv-grt-$C --memory=48g --memory-swap=48g --cpus=8 -e CORNER=$C -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $O/trialL:/work:ro -v $O/out_$C:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \$? >> /out/combo_$C.log; chown -R $(id -u):$(id -g) /out"
done
for C in TT FF; do docker wait landkv-grt-$C; docker rm landkv-grt-$C >/dev/null; done
echo GRT_DONE $(date -Is)
