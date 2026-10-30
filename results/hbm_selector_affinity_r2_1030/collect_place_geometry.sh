#!/bin/bash
# Run only after native EQUIVALENT and actual PLACE. Read-only ODB collection,
# strict actual-Liberty memory endpoints, no GRT/CTS/route in this first screen.
set -eu
K=$1
OUT=$2
R=/srv/opentallas-scratch2/claude/codex-hbm-selector-1030/roles_fresh
test -f "$K/place.rc"
test "$(cat "$K/place.rc")" = 0
python3 "$K/check_logic_reuse.py" "$K"
mkdir -p "$OUT"
python3 - "$K" "$OUT" <<'PY'
import json,sys
from pathlib import Path
k,o=map(Path,sys.argv[1:]);odb=next((k/'run/results').glob('*/*/base/3_place.odb'))
with (o/'check.json').open('x') as f:
 json.dump(dict(odb=str(odb),image='openroad/orfs:asap7lock',id=k.name.replace('-','_')[-48:],mem_gb=24,grt=False,rules_args=[]),f,indent=2)
PY
OT_GEOM_MEMORY_REACH=1 bash "$R/geom_tools/geom_check.sh" "$OUT"
