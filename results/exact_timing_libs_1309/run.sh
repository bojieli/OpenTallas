#!/bin/bash
set -e
R=$(cd "$(dirname "$0")" && pwd)
HEAD=/srv/opentallas-scratch2/claude/flow-canary/ab/runs/s81_head_1ae8ebeb0_1025_114536_038973/gen/hd_turn_a
docker run --rm --cpus=1 --memory=2g --memory-swap=2g -v "$HEAD":/work:ro -v "$R":/out openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /out/probe.tcl" > "$R/probe.log" 2>&1
