#!/bin/bash
set -eu
k=/srv/opentallas-scratch2/claude/codex-qca0/nk-b3z
for v in 0 1; do
  sudo docker run --rm --cpus 4 --memory 16g --memory-swap 16g -e SWAP=$v -v "$k":/work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/zprobe.tcl' > "$k/z$v.log" 2>&1
  sudo docker run --rm --cpus 4 --memory 16g --memory-swap 16g -e SWAP=$v -v "$k":/work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/ffprobe.tcl' > "$k/z"$v"ff.log" 2>&1
done
