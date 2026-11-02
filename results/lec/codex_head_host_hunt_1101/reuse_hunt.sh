#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-head-lec-hunt-1101
S=/srv/opentallas-scratch2/claude/dh53-hostlec
docker run --rm --name codex-head-host-hunt-1101 --memory=32g --memory-swap=32g --cpus=16 -v "$S/kit":/work:ro -v "$S/contract":/c:ro -v "$D/tools":/m:ro -v "$D/out":/out -v "$D/hyp_hints.json":/work/lec_hints.json:ro -e OT_LEC_RESET_CONTRACT=/c/reset_contract.json -e OT_LEC_HINTS_PRESEED=1 -e OT_LEC_EARLY_COMPARE=1 openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /m/lec.py /work --out /out --reuse --jobs 16' > "$D/reuse.log" 2>&1
