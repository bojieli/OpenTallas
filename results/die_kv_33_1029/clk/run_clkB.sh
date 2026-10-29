#!/bin/bash
# DIE-KV-33: KV-006 clock check readout, one corner. Diagnostic docker (capped), intel1.
C=$1; W=/srv/opentallas-scratch2/claude/die-kv-33-1029/clk; mkdir -p $W/outB_$C
docker run --rm --name dkv33-clkB-$C --memory=32g --memory-swap=32g --cpus=8 -e CORNER=$C -v /srv/opentallas-scratch2/claude/die-kv-32-1029/src_phy:/n:ro -v $W:/w -v $W/outB_$C:/out openroad/orfs:latest \
 bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /w/clkB.tcl > /out/clkB_$C.log 2>&1; echo EXIT \$? >> /out/clkB_$C.log; chown -R 1000:1000 /out"
tail -2 $W/outB_$C/clkB_$C.log
