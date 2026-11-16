#!/bin/bash
set -euo pipefail
WORK=${1:?fresh scratch directory required}
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
REPO=$(cd "$HERE/../../../.." && pwd)
mkdir "$WORK"
tar -xzf "$REPO/results/rtl/qc_xhead_native_1116/source_capsule.tar.gz" -C "$WORK"
cp "$HERE"/{tb.sv,gen_packets.py,replay_selected.py,lower_candidate.py,replay_lowered.py,build_actual.sh,calibrated.json} "$WORK/"
cd "$WORK"
export QW_REPO="$REPO"
bash build_actual.sh
python3 gen_packets.py
python3 replay_selected.py
python3 lower_candidate.py
python3 replay_lowered.py
python3 - <<'END'
import json
assert json.load(open('lowered_replay.json'))['pass']
END
