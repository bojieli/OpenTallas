#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-ds-service-hier-0340
cd "$R"
python3 prepare.py
/usr/bin/time -v "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" -f candidate_args.f > frontend.log 2> frontend.err
python3 - <<'PY'
from pathlib import Path
import json
r=Path('.');a=list((r/'out').glob('*.cpp'))
refs=[]
for p in a:
 n=p.read_text().count('ot_s81c_attn_hcore_5_protectlib')
 if n:refs.append(dict(file=p.name,references=n))
h=list((r/'out').glob('*root.h'))
out=dict(cpp_count=len(a),cpp_bytes=sum(p.stat().st_size for p in a),hcore_protectlib_references=refs,header_inline_hcore_fields=sum(p.read_text().count('g_h_0_u_c__DOT__') for p in h))
(r/'check.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if not refs:raise SystemExit('NO_HCORE_SUBSTITUTION')
PY
