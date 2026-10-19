#!/bin/bash
# Separate read-only fleet render after bounded CTS evidence. No new CTS run.
set -euo pipefail
: "${INT8_CTS_WORK:?isolated snapshot path}"
python3 - "$INT8_CTS_WORK" <<'PY'
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]);m=json.loads((p/'kit/manifest.json').read_text())
for n,d in m['files'].items():assert hashlib.sha256((p/n).read_bytes()).hexdigest()==d,n
assert json.loads((p/'output/signal_identity.json').read_text())['signal_identity_PASS']
PY
odb="$INT8_CTS_WORK/output/cts_only.odb"
sha256sum "$odb" > "$INT8_CTS_WORK/output/render_odb.before.sha"
python3 "$INT8_CTS_WORK/kit/render_density.py" "$INT8_CTS_WORK/output" "$INT8_CTS_WORK/input/native_libs"
sha256sum -c "$INT8_CTS_WORK/output/render_odb.before.sha"
