#!/bin/bash
set -euo pipefail
exec docker run --rm --cpus 1 --memory 8g --memory-swap 8g -v "$PWD":/work -v /srv/opentallas-scratch2/claude/codex-qc-l1-lvt-route2-0015:/input:ro -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit /work/audit.py' > audit.log 2>&1
