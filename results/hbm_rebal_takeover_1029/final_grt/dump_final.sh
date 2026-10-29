#!/bin/bash
set -eu
K=/srv/opentallas-scratch2/claude/codex-hbm-rebal-0310/kit
docker run --rm --cpus 2 --memory 8g -v "$K":/work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /work/dump_final.tcl' >"$K/dump_final.log" 2>&1
