#!/bin/bash
set -euo pipefail
K=$(realpath "$1"); TOOLS=$(realpath "$2")
docker run --rm --name codex-caprt-policy-$(basename "$K")-$$ --cpus=2 --memory=8g --memory-swap=8g -v "$K":/work -v "$TOOLS":/m:ro -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
rc=0
python3 -I /m/legacy_gate.py /work grt > /work/grt_policy_codex1131.log 2>&1 || rc=$?
cat /work/grt_policy_codex1131.log
chown -R "$HUID:$HGID" /work
exit "$rc"
' > "$K/run_policy1131.log" 2>&1
