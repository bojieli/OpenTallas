#!/bin/bash
set -euo pipefail
Q=/srv/opentallas-scratch2/claude
R=$Q/codex-qc-2249
I=$Q/codex-qc-import-0824
O=$R/pg_prefix_netaware
mkdir -p "$O"
docker run --rm --name codexqc2249-pgprefixnet-$$ --memory=48g --memory-swap=48g --cpus=4 -v "$Q:$Q" -e PYTHONPATH="$I/pydeps" python:3.12 bash -c "set -e; trap 'chown -R 1000:1000 $O' EXIT; python $R/src/pg_shield_supply_context.py $R/pg_prefix $O > $O/context.log 2>&1; python $Q/die-qc36/pg_access_plan_b7a872287.py --input $O --clock-seed $O/clock_seed.json --joint-clock-reserved $O/joint_reserved.json --m9-select cover --m8-landing fallback --out $O/plan > $O/run.log 2>&1"
