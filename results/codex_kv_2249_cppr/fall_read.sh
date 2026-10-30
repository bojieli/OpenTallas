#!/bin/bash
set -eu
R=/srv/opentallas-scratch2/claude/codex-kv-2249
C=$1
mkdir -p "$R/edges_$C"
docker run --rm --name codex-kv-2249-fall-$C --cpus 4 -e CORNER="$C" -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v "$R:/w" -v "$R/edges_$C:/out" -v /srv/opentallas-scratch2/claude/die-kv-42-1029/stgrt:/n:ro -v /srv/opentallas-scratch2/claude/die-kv-40-1029/clk_w243/kit:/work:ro openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 4 -exit /w/clock_fall_read.tcl > /out/read.log 2>&1; r=$?; chown -R 1000:1000 /out; exit $r'
