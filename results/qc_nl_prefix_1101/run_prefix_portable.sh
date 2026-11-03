#!/bin/bash
# STAGED FOR REVIEW ONLY. Execute only under the explicitly approved admission scope.
set -eu
R=$(cd "$(dirname "$0")" && pwd)
W="$R/source"
K="$R/completed_kit"
PLAN="$W/physical/die_plan/qwen_compute/plan_of_record/plan_qc52.json"
test ! -e "$R/target/native_target.odb"
test ! -e "$R/native/clock_native.odb"
python3 "$R/emitter.py" "$W/tools/die_plan" "$PLAN" "$K" "$R/target" > "$R/emit.log" 2>&1
docker run --rm --cpus=8 --memory=64g --memory-swap=64g -v "$R/target:/work" openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 8 -exit /work/grt/grt.tcl' > "$R/target.log" 2>&1
# Fresh graph only. --legalize-sites is deliberately absent; homes may not move.
docker run --rm --cpus=8 --memory=64g --memory-swap=64g -v "$R:/work" openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 8 -python -exit /work/producer.py --target /work/target/native_target.odb --netlist /work/inputs/ctree.v --tree /work/inputs/tree.json --out /work/native' > "$R/import.log" 2>&1
docker run --rm --cpus=8 --memory=64g --memory-swap=64g -v "$R:/work" openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 8 -python -exit /work/census.py --odb /work/native/clock_native.odb --tree /work/inputs/tree.json --ctree /work/inputs/ctree.v --out /work/native/census.json' > "$R/census.log" 2>&1
docker run --rm -v "$R:/work" openroad/orfs:asap7lock chown -R "$(id -u):$(id -g)" /work >/dev/null 2>&1
# Ends CONNECTED_UNROUTED. No PG qualification, GRT, RC/STA, provider or START import.
