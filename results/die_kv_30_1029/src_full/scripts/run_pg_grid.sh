#!/bin/bash
# DIE-KV-30-SRC: PG helper canonical regional top grid (codex/kv-pg-0834 grid3 recipe) on the rebuilt source.
# Same tools (prepare_grid.py, pdn_top3.tcl with paths only changed, readback_grid.py) and same 13,073
# die_trial.pg_stripes reservations; the array-expanding export step is NOT run.
set -euo pipefail
P=/srv/opentallas-scratch2/claude/codex-kv-pg-0834
N=/srv/opentallas-scratch2/claude/die-kv-30-1029/src_full
mkdir -p "$N/pg_grid"
docker run --rm --name dkv30-src-pggrid --memory=96g --cpus=16 -v "$P:/p:ro" -v "$N:/n" openroad/orfs:latest bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -no_init -exit /p/src/prepare_grid.py --odb /n/imported/provider.odb --grid /p/grid/source_pg_reservations.json --out /n/pg_grid > /n/pg_grid/prepare.log 2>&1 && openroad -no_init -threads 16 -exit /n/pg_grid/pdn_top.tcl > /n/pg_grid/grid.log 2>&1 && openroad -python -no_init -exit /p/src/readback_grid.py --source /n/imported/provider.odb --target /n/pg_grid/native_grid.odb --out /n/pg_grid/readback.json > /n/pg_grid/readback.log 2>&1; chown -R 1000:1000 /n/pg_grid'
