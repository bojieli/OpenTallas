#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-kv-kits-1355/dpl_probe
sudo docker run --rm --name codex-kv-dpl-probe-1355 --memory 24g --memory-swap 24g --cpus 4 -v "$R":/work -v /srv/opentallas-scratch2/claude/die-kv-32-kits-1029/kits_gen5:/input:ro -w /work openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit /work/probe.py" > "$R/probe.log" 2>&1
