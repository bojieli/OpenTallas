#!/bin/bash
set -eu
D=$(cd "$(dirname "$0")" && pwd)
OR=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad
run() { docker run --rm -v "$D:/work" openroad/orfs:latest "$OR" -python -exit "$@"; }
run /work/infra_replay.py --source /work/source.odb --target /work/target.odb --nets /work/nets.txt --out /work/final.odb > "$D/final_import.log" 2>&1
run /work/infra_replay.py --verify /work/replayed_after.odb --against /work/final.replay.json > "$D/final_verify.log" 2>&1
run /work/mutate.py > "$D/mutant_build.log" 2>&1
if run /work/infra_replay.py --verify /work/mutant_missing_clock_wire.odb --against /work/final.replay.json > "$D/mutant_verify.log" 2>&1; then echo MUTANT_NOT_CAUGHT; exit 1; fi
echo ACTUAL_IMPORT_PRESERVE_AND_MUTANT_PASS
