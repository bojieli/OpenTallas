#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-qc-import-0824
Q=/srv/opentallas-scratch2/claude
F=$R/reachfix
mkdir -p "$F/incremental_pg"
docker run --rm --name codex-qci-incrpg-$$ --memory=32g --memory-swap=32g --cpus=4 -v "$Q:$Q" -w "$R" -e PYTHONPATH="$R/pydeps" python:3.12 bash -c "set -e; trap 'chown -R 1000:1000 $F/incremental_pg' EXIT; python $R/src/pg_incremental_context.py > $F/incremental_pg/context.log 2>&1; python $R/src/plan_access_fallback.py --input $F/incremental_pg --clock-seed $F/incremental_pg/clock_seed.json --joint-clock-reserved $F/incremental_pg/joint_clock_reserved.json --reserved-power $F/incremental_pg/reserved_power.json --out $F/incremental_pg/out > $F/incremental_pg/plan.log 2>&1"
cat "$F/incremental_pg/context.log"; tail -1 "$F/incremental_pg/plan.log"
