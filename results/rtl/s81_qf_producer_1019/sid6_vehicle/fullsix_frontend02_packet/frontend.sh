#!/bin/bash
set -euo pipefail
if [ -e obj ] || [ -e frontend.log ];then echo REFUSE_EXISTING_FRONTEND >&2;exit 2;fi
python3 - <<'PY'
from pathlib import Path
import json,hashlib
for r in json.load(open('frozen_inputs.json'))['files']:
 assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256'],r['path']
PY
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$v" --version > verilator.version
sha256sum "$v" "${v}_bin" > tool.sha256
/usr/bin/time -v -o frontend_time.log "$v" --cc --main --exe --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD +define+DSFD_PQ_STATIC_X2 \
 --top-module tb_fullsix_trace --Mdir obj -f source_files.f cells_used.v selected_fullsix_cone.sv tb_fullsix_trace.sv > frontend.log 2>&1
python3 - <<'PY'
from pathlib import Path
import json,hashlib
files=[dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(Path('obj').rglob('*')) if p.is_file()]
Path('frontend_inventory.json').write_text(json.dumps(dict(files=files,CPP_files=sum(r['path'].endswith('.cpp') for r in files),generated_bytes=sum(r['bytes'] for r in files),stage='FRONTEND_ONLY_NO_NUMERIC_PASS'),indent=2)+'\n')
PY
echo FULLSIX_FRONTEND_ONLY_TERMINAL_NO_COMPILE_OR_SIM
