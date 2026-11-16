#!/bin/bash
set -euo pipefail
WORK=${1:?fresh scratch directory required}
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
REPO=$(cd "$HERE/../../../.." && pwd)
mkdir "$WORK"
tar -xzf "$REPO/results/rtl/qc_xhead_native_1116/source_capsule.tar.gz" -C "$WORK"
cp "$HERE"/{tb.sv,gen_packets.py,replay_selected.py,lower_candidate.py,replay_lowered.py,build_actual.sh,calibrated.json,tb_go_conduit.sv} "$WORK/"
cd "$WORK"
export QW_REPO="$REPO"
bash build_actual.sh
python3 gen_packets.py
python3 replay_selected.py
cp qkv_s0.hex input.hex
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --binary --timing --top-module tb -j 2 -Wno-fatal -Wno-lint -Wno-style -Wno-PINMISSING --Mdir obj_go tb_go_conduit.sv tap.sv tap_helpers.sv head.sv rst.sv >build_go.log 2>&1
./obj_go/Vtb >go_conduit.log 2>&1
python3 lower_candidate.py
python3 replay_lowered.py
python3 - <<'END'
import json
assert json.load(open('lowered_replay.json'))['pass']
END
