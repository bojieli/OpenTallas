#!/bin/bash
# DIE-QC-36 PG access replan around the re-sited clock pin stacks + router-track backbone (bb1). Two variants (12.17(3)):
#  PA-A: Codex import-0824 plan_access.py (as fullpg) + native bridges reserved; joint reserved = endpoint landings + bb1 jogs/risers/M8 pads
#  PA-B: shared tools/die_plan/pg_access_plan.py @b7a872287 --m9-select cover --m8-landing fallback (KV-006 fixes), same reservations
#        except native bridges (tool has no --reserved-power) -> diagnostic for the M8/M9 landing form
# clock seed v2 = row-keyed shift (exactly the 8,156 moved pin stacks)
set -euo pipefail
V=$1; Q=/srv/opentallas-scratch2/claude; R=$Q/die-qc36; I=$Q/codex-qc-import-0824
mkdir -p $R/pa_$V
python3 -c "import json,sys; a=json.load(open(sys.argv[1])); b=json.load(open(sys.argv[2])); json.dump(a+b,open(sys.argv[3],'w'))" $I/clock_landing_reserved.json $R/backbone_bb1/joint_clock_reserved.json $R/pa_$V/joint_reserved.json
if [ $V = A ]; then CMD="python $I/src/plan_access.py --input $R/readback_resite --clock-seed $R/backbone_bb1/clock_base_resite_v2.json --joint-clock-reserved $R/pa_$V/joint_reserved.json --reserved-power $I/nativepg/bridges/reserved_bridges.json --out $R/pa_$V"
else CMD="python $R/pg_access_plan_b7a872287.py --input $R/readback_resite --clock-seed $R/backbone_bb1/clock_base_resite_v2.json --joint-clock-reserved $R/pa_$V/joint_reserved.json --m9-select cover --m8-landing fallback --out $R/pa_$V"; fi
docker run --rm --name dqc36-pa$V-$$ --memory=96g --memory-swap=96g --cpus=4 -v "$Q:$Q" -w "$R" -e PYTHONPATH="$I/pydeps" python:3.12 bash -c "trap 'chown -R 1000:1000 $R/pa_$V' EXIT; $CMD > $R/pa_$V/run.log 2>&1"
