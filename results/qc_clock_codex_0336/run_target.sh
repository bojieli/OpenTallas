#!/bin/bash
set -eu
R=/srv/opentallas-scratch2/claude/codex-qc-clock-0336
docker run --rm --name codexqcclock-target-0336 --memory=128g --memory-swap=128g --cpus=8 -v "$R/nativekit:/work" openroad/orfs:asap7lock bash -c "set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 8 -exit /work/grt/grt.tcl > /work/prepare_target.log 2>&1; chown -R 1000:1000 /work"
