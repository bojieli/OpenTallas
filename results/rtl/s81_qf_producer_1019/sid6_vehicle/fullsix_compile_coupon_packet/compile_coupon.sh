#!/bin/bash
set -euo pipefail
if [ -e pch_time.log ] || [ -e coupon_time.log ];then echo REFUSE_EXISTING_COMPILE_RECEIPT >&2;exit 2;fi
python3 - <<'PY'
from pathlib import Path
import json,hashlib
for r in json.load(open('frontend_inventory.json'))['files']:
 assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256'],r['path']
assert not list(Path('obj').glob('*.o'))
assert not list(Path('obj').glob('*.gch'))
PY
g++ --version > compiler.version
sha256sum /usr/bin/g++ /usr/bin/make "$HOME/.local/opentallas-tools/verilator-5.050/share/verilator/include/verilated.mk" > compile_tool.sha256
# Both targets are real reusable products of the unchanged full-six make graph.
/usr/bin/time -v -o pch_time.log make -C obj -f Vtb_fullsix_trace.mk -j1 Vtb_fullsix_trace__pch.h.slow.gch \
 OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0 > pch_compile.log 2>&1
/usr/bin/time -v -o coupon_time.log make -C obj -f Vtb_fullsix_trace.mk -j1 Vtb_fullsix_trace___024root__131__Slow.o \
 OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0 > coupon_compile.log 2>&1
python3 - <<'PY'
from pathlib import Path
import json,hashlib
for r in json.load(open('frontend_inventory.json'))['files']:
 assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256'],r['path']
files=[dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(Path('obj').iterdir()) if p.suffix in ['.o','.gch','.d']]
Path('compile_coupon_outputs.json').write_text(json.dumps(dict(scope='One actual full-model PCH and largest-TU object only; no link/simulation/numericPASS',files=files),indent=2)+'\n')
PY
echo FULLSIX_REAL_PCH_LARGEST_TU_ONLY_NO_LINK_OR_SIM
