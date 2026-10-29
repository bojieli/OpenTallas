#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-kv-0822
PG=/srv/opentallas-scratch2/claude/codex-kv-pg-0834/grid3/native_grid.odb
mkdir -p "$R/full_source"
docker run --rm --name codex-kv0822-full-abstracts --memory=40g --cpus=8 -v "$R:/r" -v "$PG:/pg_source.odb:ro" openroad/orfs:latest bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -no_init -exit /r/apply_abstracts.py --source /pg_source.odb --abstracts /r/full_abstracts --tech-lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef --out /r/full_source > /r/full_source/apply.log 2>&1; chown -R 1000:1000 /r/full_source'
