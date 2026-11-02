#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-hist-centre-fp-2307
K="$R/kit"
docker run --rm --memory=8g --memory-swap=8g --cpus=2 -e HUID="$(id -u)" -e HGID="$(id -g)" -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash /work/run_fp_inside.sh > "$R/fp.container.log" 2>&1
