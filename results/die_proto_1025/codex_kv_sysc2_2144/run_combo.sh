#!/bin/bash
set -euo pipefail
C=$1
D=/srv/opentallas-scratch2/claude/codex-kv-die-2144
sudo docker run --rm --name codex-kvdie2144-$C-$$ --cpus=16 --memory=40g --memory-swap=40g -e CORNER=$C -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $D/kit:/work:ro -v $D/out:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 16 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; r=\$?; echo EXIT \$r >> /out/combo_$C.log; chown -R 1000:1000 /out; exit \$r"
