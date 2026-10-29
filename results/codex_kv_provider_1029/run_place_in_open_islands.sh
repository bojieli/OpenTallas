#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-kv-0822
P=/srv/opentallas-scratch2/claude/die-kv-29-1029/venv/bin/python3
python3 - "$R" <<'PY'
from pathlib import Path
import json,sys
r=Path(sys.argv[1]);d=json.load(open(r/'native_bound/constraints/constraints.json'));d['hard_forbidden'] += [['actual_soft_OBS_'+x[0]+'_'+x[1],*x[2:]] for x in d['actual_lower_OBS']];d['policy']='All existing physical OBS, native clocks, hard cores and PG immutable. Place only inside already-open islands.';(r/'native_bound/planning_constraints.json').write_text(json.dumps(d,separators=(',',':'))+'\n')
PY
$P "$R/imp/plan_place.py" --inventory "$R/provider_cells_kv6.json" --constraints "$R/native_bound/planning_constraints.json" --budget "$R/budget_kv6_node.json" --out "$R/proposal_open" > "$R/proposal_open.log" 2>&1
$P "$R/imp/preflight.py" --inventory "$R/provider_cells_kv6.json" --mapped "$R/provider_mapped_kv6.json" --placements "$R/proposal_open/placements.json" --proposal-constraints "$R/native_bound/planning_constraints.json" --fresh-constraints "$R/native_bound/constraints/constraints.json" --bindings "$R/native_bound/bindings_native.json" --out "$R/native_bound/preflight_open.json" > "$R/native_bound/preflight_open.log" 2>&1
