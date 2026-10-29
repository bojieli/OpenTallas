#!/bin/bash
set -euo pipefail
r=/srv/opentallas-scratch2/claude/codex-qc-a0-0830;k=$r/kits/qfd_tile_nl_a0c_a0nl14icg2r1
sudo docker run --rm --name codex-qca0-0830-nl-enable --cpus=2 --memory=8g --memory-swap=8g -v "$k":/work:ro -v "$r":/src:ro -v "$r/nl_enable":/out -w /out openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1;openroad -exit /out/probe.tcl > /out/probe.log 2>&1'
