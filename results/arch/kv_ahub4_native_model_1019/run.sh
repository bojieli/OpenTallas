#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")"
docker run --rm --memory=4g -v /srv/opentallas-scratch/claude/ref_gate/qkd_ahub_g2l-20261019-170552:/native:ro -v "$PWD":/out openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/census.tcl > census.log 2>&1
rc=$?;cat census.log;exit "$rc"
