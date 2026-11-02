#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-ds-native-go-pair-2355/retry2
B=/srv/opentallas-scratch2/claude/codex-ds-bf-1131
cd "$R"
unset OT_XS_GB_PROVIDER_UNDER_TEST
python3 - <<'PY'
from pathlib import Path
import json,hashlib
r=Path('.');m=json.loads((r/'programme/programme.json').read_text());p=r/'fixture/ops/attn.norm.scale.bin';assert hashlib.sha256(p.read_bytes()).hexdigest()==m['fixture_sha256'],'cannot reuse a different producer input'
PY
python3 prepare_native_go_pair_gold.py --source "$B/source" --field "$R/field" --fixture "$R/fixture" --out "$R/independent_gold.json"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
/usr/bin/time -v -o "$R/frontend.time" "$V" --cc --exe --main --timing -O1 --output-split 10000 --output-split-cfuncs 1000 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-lint -Wno-style -Wno-PINMISSING -Wno-MULTIDRIVEN --top-module tb_native_go_pair -Mdir "$R/obj" -f sources.f > frontend.log 2>&1
python3 - <<'PY'
from pathlib import Path
import json,re
r=Path('.');paths=list((r/'obj').glob('*.cpp'));text=(r/'frontend.time').read_text();rss=re.search(r'Maximum resident set size \(kbytes\): (\d+)',text)
d=dict(status='PREPARED_FULL_NB2_PAIR_FRONTEND_ONLY',CXX_files=len(paths),CXX_bytes=sum(p.stat().st_size for p in paths),largest_CXX_bytes=max(p.stat().st_size for p in paths),frontend_max_RSS_kbytes=int(rss[1])if rss else None,arithmetic_model_copies=2,actual_native_pairs_selected=1,whole_frames=0,backend_or_native_runs_started=False,mem_request_GB=8,threads=2,production_enabled=False,native_provider_qualified=False)
(r/'frontend_size.json').write_text(json.dumps(d,indent=2)+'\n');print(d,flush=True)
PY
