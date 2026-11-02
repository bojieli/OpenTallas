#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-zh-native-fp-prep-0705
python3 "$R/guard.py" "$R"
docker run --rm --name "codex-zh-fp-dry-$$" --memory=4g --memory-swap=4g --cpus=1 -v "$R/kit":/work -v "$R":/case:ro -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash /case/inside_fp.sh dry
python3 "$R/guard.py" "$R"
