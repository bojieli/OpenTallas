#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-recip-native-fp-0640
python3 "$R/guard.py" pre
MODE=${1:-run}
if [ "$MODE" != dry ]; then
  test -f "$R/DRY_GUARD.json"
  python3 -c 'import json,hashlib;from pathlib import Path; r=Path("/srv/opentallas-scratch2/claude/codex-recip-native-fp-0640"); d=json.loads((r/"DRY_GUARD.json").read_text()); assert d["status"]=="PASS"; assert hashlib.sha256((r/"inside_fp.sh").read_bytes()).hexdigest()==d["inside_fp_sha256"]; assert hashlib.sha256((r/"EXPECTED.json").read_bytes()).hexdigest()==d["expected_inputs_sha256"]'
fi
docker run --rm --name "codex-recip-fp-${MODE}-$$" --memory=4g --memory-swap=4g --cpus=1 -v "$R/kit":/work -v "$R":/case:ro -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash /case/inside_fp.sh "$MODE"
if [ "$MODE" != dry ]; then
  python3 "$R/guard.py" post
fi
