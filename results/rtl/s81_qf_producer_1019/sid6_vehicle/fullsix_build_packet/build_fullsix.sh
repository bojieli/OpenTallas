#!/bin/bash
set -euo pipefail
if [ -e fullbuild_time.log ];then echo REFUSE_EXISTING_FULLBUILD_RECEIPT >&2;exit 2;fi
python3 - <<'PY'
from pathlib import Path
import json,hashlib
for r in json.load(open('frontend_inventory.json'))['files']:
 assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256'],r['path']
for r in json.load(open('compile_coupon_outputs.json'))['files']:
 assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256'],r['path']
PY
# Incremental real generated make graph; reuses measured PCH and largest object.
/usr/bin/time -v -o fullbuild_time.log make -C obj -f Vtb_fullsix_trace.mk -j32 \
 OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0 > fullbuild.log 2>&1
python3 - <<'PY'
from pathlib import Path
import json,hashlib
for r in json.load(open('frontend_inventory.json'))['files']:
 assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256'],r['path']
for r in json.load(open('compile_coupon_outputs.json'))['files']:
 assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256'],r['path']
files=[dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(Path('obj').iterdir()) if p.suffix in ['.o','.gch','.a'] or p.name=='Vtb_fullsix_trace']
Path('fullbuild_outputs.json').write_text(json.dumps(dict(scope='Actual C++build/link only; executable never run here',files=files,simulation_run=False,numerical_PASS=None),indent=2)+'\n')
PY
echo FULLSIX_BUILD_LINK_TERMINAL_NO_EXECUTION_OR_NUMERIC_PASS
