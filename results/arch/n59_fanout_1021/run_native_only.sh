#!/bin/bash
set -euo pipefail
TASK_ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$TASK_ROOT"
: "${N59_NATIVE_OUT:?absolute output directory required}"
mkdir -p "$N59_NATIVE_OUT"
python3 - <<'PY'
from pathlib import Path
p=Path('tools/ref_tile/ref_route.sh');s=p.read_text();old='PRE_FLOORPLAN=tools/ref_tile/native_census.tcl';assert s.count(old)==1
Path('tools/ref_tile/n59_native_only_route.sh').write_text(s.replace(old,'PRE_FLOORPLAN=tools/ref_tile/n59_native_only.tcl'))
Path('tools/ref_tile/n59_native_only.tcl').write_text('source /src/tools/ref_tile/native_census.tcl\nputs "N59_NATIVE_ONLY_PASS before initialize_floorplan"\nexit 0\n')
PY
export SRC="$TASK_ROOT" SYNTH_TIMEOUT=unlimited OT_ORFS_CORNER_OVERRIDE=TC HM=0.03 OT_ROUTE_HOLD_CORNERS=mm
bash tools/ref_tile/n59_native_only_route.sh physical/ref_tile/qfd_n59_svc5/kit.env census "$N59_NATIVE_OUT" floorplan --native-census
