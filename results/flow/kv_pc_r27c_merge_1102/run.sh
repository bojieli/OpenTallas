#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-pc-r27c-replay-0155
S=/srv/opentallas-scratch2/claude/kv60-pcx/r27c/resign_mkv
docker run --rm --name codex-pc-r27c-replay-0155 --cpus=2 --memory=8g --memory-swap=8g -v "$S":/subject:ro -v "$D":/out openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /out/replay.py' > "$D/run.log" 2>&1
