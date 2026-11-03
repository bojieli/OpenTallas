#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-ds-native-r8-0200
BASE=/srv/opentallas-scratch2/claude/codex-ds-native-ring-0140/retry2
GOOD=/srv/opentallas-scratch2/claude/codex-ds-native-ring-0140/retry3_early_preload
cd "$R"
unset OT_XS_GB_PROVIDER_UNDER_TEST
ln -s "$BASE/src" src
ln -s "$GOOD/programme" programme
ln -s "$GOOD/independent_gold.json" independent_gold.json
cp "$BASE/sources.f" sources.f
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
/usr/bin/time -v -o frontend.time "$V" --cc --exe --main --timing -O1 --output-split 10000 --output-split-cfuncs 1000 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-lint -Wno-style -Wno-PINMISSING -Wno-MULTIDRIVEN --top-module tb_native_go_pair -Mdir "$R/obj" -f sources.f > frontend.log 2>&1
python3 - <<'PY'
from pathlib import Path
import json
r=Path('.');p=list((r/'obj').glob('*.cpp'));d=dict(status='DISABLED_R8_COMPONENT_FRONTEND_PASS',CXX_files=len(p),CXX_bytes=sum(v.stat().st_size for v in p),largest_CXX_bytes=max(v.stat().st_size for v in p),production_enabled=False,native_provider_qualified=False,wholeframe=False);(r/'frontend_size.json').write_text(json.dumps(d,indent=2)+'\n');print(d)
PY
