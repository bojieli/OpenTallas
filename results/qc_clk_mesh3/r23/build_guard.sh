#!/bin/bash
set -euo pipefail
P=/srv/opentallas-scratch2/claude/codex-qwen-1027/pkg
cd "$P"
python3 - <<'PY2'
import json
from pathlib import Path
p=Path('out/guard51');d=json.load(open(p/'dry_exact/place.json'))
s=[dict(name=k,xy_um=[v['x']+0.81,v['y']+0.135],kind='partition') for k,v in d.items() if v.get('part')]
(p/'island_sites.json').write_text(json.dumps(dict(schema='ot_clock_sites/1',sites=s)))
PY2
python3 die_plan/die_trial.py kit inputs/d51/plan_d43.json --out out/guard51/basekit --island-sites out/guard51/island_sites.json --island-margin-um 1.65 > out/guard51/kit.log 2>&1
python3 die_plan/die_clock_mesh.py combo out/guard51/dry_exact --kit "$P/out/guard51/basekit" --plan inputs/d51/plan_d43.json --routed-clock > out/guard51/combo.log 2>&1
CORNERS="TT FF" MEM=64 bash out/guard51/dry_exact/run_combo.sh
printf 'GUARD51_GRT_DONE\n'
