#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-ds-hier-default-0300/retry3_force_params_file
cd "$R"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
for mode in bare explicit; do
 defs=();[ "$mode" = bare ] || defs=(+define+EXPLICIT_DEFAULTS)
 "$V" --binary --timing --hierarchical --hierarchical-params-file "$R/empty_types.sv" -O1 -j 1 -Wno-fatal --top-module tb "${defs[@]}" hier.vlt leaf.sv parent.sv tb.sv -Mdir "$R/$mode" > "$mode.build.log" 2>&1
 "$R/$mode/Vtb" > "$mode.run.log" 2>&1
done
python3 - <<'PY'
from pathlib import Path
import json
r=Path('.');out={}
for mode in ['bare','explicit']:
 p=r/mode;args=list(p.glob('*__hierMkArgs.f'));maps=[]
 for a in args:
  for line in a.read_text().splitlines():
   if line.startswith('--hierarchical-block'):maps.append(dict(file=a.name,line=line))
 calls=[]
 for f in p.rglob('*.cpp'):
  if 'parent' in f.name:
   n=f.read_text().count('ot_s81c_attn_hcore')
   if n:calls.append(dict(file=str(f),references=n))
 out[mode]=dict(mapping=maps,parent_CPP_hcore_references=calls,run=(r/(mode+'.run.log')).read_text())
(r/'check.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
PY
