#!/bin/bash
# DIE-QC-36 PG access replan around the re-sited clock pin stacks + router-track backbone (bb1). Two variants (12.17(3)):
#  PA-A: Codex import-0824 plan_access.py (as fullpg) + native bridges reserved; joint reserved = endpoint landings + bb1 jogs/risers/M8 pads
#  PA-B: shared tools/die_plan/pg_access_plan.py @b7a872287 --m9-select cover --m8-landing fallback (KV-006 fixes), same reservations
#        except native bridges (tool has no --reserved-power) -> diagnostic for the M8/M9 landing form
set -euo pipefail
V=$1; Q=/srv/opentallas-scratch2/claude; R=$Q/die-qc36; I=$Q/codex-qc-import-0824
mkdir -p $R/pa_$V
docker run --rm --name dqc36-pa$V-$$ --memory=96g --memory-swap=96g --cpus=4 -v "$Q:$Q" -w "$R" -e PYTHONPATH="$I/pydeps" python:3.12 bash -c "set -e; trap \"chown -R 1000:1000 $R/pa_$V\" EXIT;
python -c \"import json; a=json.load(open(/clock_landing_reserved.json)); b=json.load(open(/backbone_bb1/joint_clock_reserved.json)); json.dump(a+b,open(/pa_/joint_reserved.json,w))\";
if [ $V = A ]; then python $I/src/plan_access.py --input $R/readback_resite --clock-seed $R/backbone_bb1/clock_base_resite.json --joint-clock-reserved $R/pa_$V/joint_reserved.json --reserved-power $I/nativepg/bridges/reserved_bridges.json --out $R/pa_$V;
else python $R/pg_access_plan_b7a872287.py --input $R/readback_resite --clock-seed $R/backbone_bb1/clock_base_resite.json --joint-clock-reserved $R/pa_$V/joint_reserved.json --m9-select cover --m8-landing fallback --out $R/pa_$V; fi > $R/pa_$V/run.log 2>&1"
