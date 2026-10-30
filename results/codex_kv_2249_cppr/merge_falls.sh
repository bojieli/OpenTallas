#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/claude/codex-kv-2249
python3 - <<'PY'
from pathlib import Path
import shutil,json
p=Path('proof_core');p.mkdir()
for f in Path('proof_loaded').iterdir():
 if f.name.startswith('tap_arrivals_'):
  x=json.load(f.open());x['taps']=[t for t in x['taps'] if not t['port'].startswith('__st__')];x.pop('basis_start_stages',None);(p/f.name).write_text(json.dumps(x))
 elif f.is_file():shutil.copy2(f,p/f.name)
PY
for C in TT FF; do
 python3 src/tools/die_plan/tap_fall_merge.py proof_core "$C" edges_$C/arr_$C.txt --tree /srv/opentallas-scratch2/claude/die-kv-42-1029/stgrt/clkgrt_st/tree.json --out proof_core_fall >merge_$C.json
done
python3 src/tools/die_plan/start_stage_emit.py proof proof_core_fall --stages /srv/opentallas-scratch2/claude/die-kv-41-1029/start_wc/emitted/start_stages.json --arr TT=edges_TT/arr_TT.txt --arr FF=edges_FF/arr_FF.txt --out proof_loaded_fall
