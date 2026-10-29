#!/bin/bash
set -euo pipefail
K=/srv/opentallas-scratch2/claude/codex-kv-kits-1029c/astk_place_trial/kv3_astk__190.08x181.44
O=/srv/opentallas-scratch2/claude/codex-kv-kits-1029c/geom/astk_native
S=/srv/opentallas-scratch2/claude/codex-kv-kits-1029c/clock/scripts
DK=docker;docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --cpus 2 --memory 8g --memory-swap 8g -v "$K":/work:ro -v "$O":/out -v "$S":/scripts:ro -e ODB=/work/run/results/asap7/hc_kv3_astk__190_08x181_44/base/3_place.odb -e OUT=/out/sites.txt openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /scripts/fixed_sites.tcl' > "$O/sites.log" 2>&1
