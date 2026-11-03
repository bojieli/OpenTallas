#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-recip-place-canary-prep-0810
python3 "$R/guard_canary.py" "$R" run
docker run --rm --name "codex-recip-cts-static-$$" --memory=4g --memory-swap=4g --cpus=1 -v "$R/kit":/work:ro -v "$R/cts_prep":/case -w /OpenROAD-flow-scripts/flow sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/orfs_hold_mm.py scripts > /case/STATIC_MM_PATCH.log; make -pn DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=1 do-4_1_cts do-4_cts | gzip > /case/CTS_MAKE_DATABASE.txt.gz; make -n DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=1 do-4_1_cts do-4_cts > /case/CTS_DRY_TARGETS.log; openroad -no_init -threads 1 -exit -python /case/read_static.py'
