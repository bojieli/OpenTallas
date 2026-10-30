#!/bin/bash
set -euo pipefail
r=/srv/opentallas-scratch2/claude/codex-start-source-assembly-1030/attempt_833
cd "$r"
printf 'START %s SOURCE-only fullvirtual START/RAW map\n' "$(date -Is)" >>status
docker run --rm --name codex_start_source_map833_1030 --cpus=2 --memory=16g --memory-swap=16g -v "$r/kit:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=2 /work/run/results/asap7/codex_start_source/base/1_2_yosys.v' >map.log 2>&1
printf 'MAP_RC 0 %s\n' "$(date -Is)" >>status
