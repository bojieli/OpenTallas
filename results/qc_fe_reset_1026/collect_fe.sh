#!/bin/bash
set -euo pipefail
R=$(pwd)
while IFS='|' read -r T D B; do
 docker run --rm --cpus=2 --memory=8g --memory-swap=8g -v "$R":/out -v "$D":/src:ro -e ODB="/src/$B" -e OUT="/out/conn_${T}.tsv" openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /out/conn.tcl' > "$R/dump_${T}.log" 2>&1
 echo "$T $D/$B" >> "$R/sources.txt"
done <<'DATA'
sle_fe_v1|/srv/opentallas-scratch2/claude/codex-geom-2219/fe_cts_checkpoint_v2/run/results/asap7/dp_sle_fe_v1/base|4_cts.odb
sle_fe_v2|/srv/opentallas-scratch2/claude/kits-wave2/gen/qwen_compute/sle_fe_v2/sle_fe_v2/run/results/asap7/dp_sle_fe_v2/base|3_place.odb
sle_fe_v3|/srv/opentallas-scratch2/claude/kits-wave2/gen/qwen_compute/sle_fe_v3/sle_fe_v3/run/results/asap7/dp_sle_fe_v3/base|3_place.odb
DATA
