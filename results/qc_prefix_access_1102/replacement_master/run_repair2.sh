#!/bin/bash
set -euo pipefail
R=$(cd "$(dirname "$0")" && pwd)
I=/srv/opentallas-scratch2/claude/codex-qc-nl-prefix-1101/prefix
docker run --rm --cpus 8 --memory 64g --memory-swap 64g -v "$I":/input:ro -v "$R":/work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 8 -python -exit /work/repair_newmasters.py --input /input/native/clock_native.odb --tree /input/inputs/tree.json --plan /input/source/physical/die_plan/qwen_compute/plan_of_record/plan_qc52.json --tools /input/source/tools/die_plan --out /work/native' > "$R/repair.log" 2>&1
docker run --rm --cpus 8 --memory 64g --memory-swap 64g -v "$R":/work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 8 -python -exit /work/verify_reload.py' > "$R/reload.log" 2>&1
docker run --rm --cpus 8 --memory 64g --memory-swap 64g -v "$I":/input:ro -v "$R":/work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 8 -python -exit /work/census.py --odb /work/native/clock_native.odb --tree /input/inputs/tree.json --ctree /input/inputs/ctree.v --out /work/native/census.json' > "$R/census.log" 2>&1
