#!/bin/bash
set -euo pipefail
B=/srv/opentallas-scratch2/claude/codex-collft-clock-0336
K=/srv/opentallas-scratch2/claude/codex-collft-ff5-0336/gen/coll_ft__cla4a25d77/coll_ft__cla4a25d77/run/results/asap7/dp_coll_ft__cla4a25d77/base
sudo docker run --rm --name codex-collft-clock-census-0336 --cpus=1 --memory=8g --memory-swap=8g -v "$B":/work -v "$K":/odb:ro -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/census/dump.tcl > /work/census/dump.log 2>&1'
