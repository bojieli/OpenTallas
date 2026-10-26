#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch/codex/kv-def-origins-1417
docker run --rm --memory=4g --cpus=1 -v "$PWD:/work" openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 1 -no_init -exit /work/run.tcl' > run.log 2>&1
