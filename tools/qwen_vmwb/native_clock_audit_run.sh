#!/bin/bash
set -eu
yosys -Q -T -s tools/qwen_vmwb/native_clock_connected.ys > ../native-clock-connected.log 2>&1
python3 tools/qwen_vmwb/native_clock_audit.py ../native-clock-connected.json --out ../native-clock-audit.json
python3 - <<'PY'
from pathlib import Path
p=Path('tools/qwen_vmwb/native_clock_connected.ys')
s=p.read_text().replace('-set USE_NATIVE_CLOCKS 1','-set USE_NATIVE_CLOCKS 0').replace('native-clock-connected.json','native-clock-tied.json')
Path('../native-clock-tied.ys').write_text(s)
PY
yosys -Q -T -s ../native-clock-tied.ys > ../native-clock-tied.log 2>&1
python3 tools/qwen_vmwb/native_clock_audit.py ../native-clock-tied.json --expect fail --out ../native-clock-tied-audit.json
