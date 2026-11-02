#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-zh-native-fp-prep-0705
docker run --rm --name "codex-zh-fp-read-$$" --memory=2g --memory-swap=2g --cpus=1 -v "$R/kit":/work:ro -v "$R":/case -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 1 -exit -python /case/read_fp_db.py'
