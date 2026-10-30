#!/bin/bash
set -euo pipefail
Q=/srv/opentallas-scratch2/claude
R=$Q/codex-qc-2249
I=$Q/codex-qc-import-0824
C=$R/pg_full_context
O=$R/pg_full_netaware
mkdir -p "$C" "$O"
for f in geometry.json power_terms.json endpoints.json pg_rects.json probe_census.json; do ln -sf "$R/readback/$f" "$C/$f"; done
ln -sf "$R/reservation/joint_reserved.json" "$C/joint_reserved.json"
docker run --rm --name codexqc2249-pgfullnet-$$ --memory=96g --memory-swap=96g --cpus=4 -v "$Q:$Q" -e PYTHONPATH="$I/pydeps" python:3.12 bash -c "set -e; trap 'chown -R 1000:1000 $O' EXIT; python $R/src/pg_shield_supply_context.py $C $O/input > $O/context.log 2>&1; python $Q/die-qc36/pg_access_plan_b7a872287.py --input $O/input --clock-seed $O/input/clock_seed.json --joint-clock-reserved $O/input/joint_reserved.json --m9-select cover --m8-landing fallback --out $O/plan > $O/run.log 2>&1"
