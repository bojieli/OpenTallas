#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-recip-native-fp-0640
python3 "$R/guard.py" post
docker run --rm --name "codex-recip-fp-read-$$" --memory=2g --memory-swap=2g --cpus=1 -v "$R/kit":/work:ro -v "$R":/case -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 1 -exit -python /case/read_fp_db.py'
