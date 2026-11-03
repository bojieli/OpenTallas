#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-ds-native-ring-0140
OLD=/srv/opentallas-scratch2/claude/codex-ds-native-go-pair-2355/retry2
MIX=/srv/opentallas-scratch2/claude/codex-ds-native-mixed-0130
B=/srv/opentallas-scratch2/claude/codex-ds-bf-1131/source
cd "$R"
unset OT_XS_GB_PROVIDER_UNDER_TEST
ln -s "$OLD/src" src
ln -s "$OLD/independent_gold.json" independent_gold.json
cp "$OLD/sources.f" sources.f
printf 'ot_s81sl_rstop.sv\n' >> sources.f
for label in programme wrong_class_programme; do
 cp -a "$MIX/$label" "$R/$label"
 python3 prepare_native_ring_fixture.py --programme "$R/$label" --fixture "$OLD/fixture" --source "$B"
done
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
/usr/bin/time -v -o frontend.time "$V" --cc --exe --main --timing -O1 --output-split 10000 --output-split-cfuncs 1000 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-lint -Wno-style -Wno-PINMISSING -Wno-MULTIDRIVEN --top-module tb_native_go_pair -Mdir "$R/obj" -f sources.f > frontend.log 2>&1
python3 - <<'PY'
from pathlib import Path
import json
r=Path('.');paths=list((r/'obj').glob('*.cpp'))
d=dict(status='ACTUAL_RING_COMPONENT_FRONTEND_PASS',CXX_files=len(paths),CXX_bytes=sum(p.stat().st_size for p in paths),largest_CXX_bytes=max(p.stat().st_size for p in paths),wholeframe_compile=False,production_enabled=False,native_provider_qualified=False)
(r/'frontend_size.json').write_text(json.dumps(d,indent=2)+'\n');print(d)
PY
