#!/bin/bash
set -eu
k=/srv/opentallas-scratch2/claude/codex-qca0/nk-b3z
sudo docker run --rm --cpus 2 --memory 8g --memory-swap 8g -v "$k":/work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/baseline_setup.tcl' > "$k/baseline_setup.log" 2>&1
