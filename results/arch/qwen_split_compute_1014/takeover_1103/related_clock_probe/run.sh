#!/bin/bash
set -euo pipefail
docker run --rm --cpus=1 --memory=2g -v /srv/opentallas-scratch/codex/qwen-clock-contract-probe-1103/attempt2:/work -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 1 -no_init -exit /work/probe.tcl > /work/probe.log 2>&1'
