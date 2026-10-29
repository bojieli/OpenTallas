#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-qcore-m7-1029
docker run --rm --name codex-qcore-pg-audit --cpus=2 --memory=8g --memory-swap=8g -v "$PWD":/work -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/pg_audit.tcl > /work/pg_audit.log 2>&1'
