#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-hist-combplace-family-0121
docker run --rm --memory=8g --memory-swap=8g --cpus=2 -e HUID="$(id -u)" -e HGID="$(id -g)" -v "$R/kit":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash /work/run_place_inside.sh > "$R/place.container.log" 2>&1
