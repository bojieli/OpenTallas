#!/usr/bin/env bash
# Source-pinned ORFS mapped census only. No initialize_floorplan/placement/CTS/route executes.
set -euo pipefail
mkdir -p census
python3 tools/ref_tile/ref_tile.py gen tools/ref_tile/specs_qw2_slice2_native/qfd_dv_slice2_w8.json > census/gen_kit.log 2>&1
cat > tools/qwen_dv/slice8_census_only.tcl <<'TCL'
source /src/tools/ref_tile/native_census.tcl
puts "SLICE8_CENSUS_ONLY_STOP_BEFORE_INITIALIZE_FLOORPLAN"
exit
TCL
# Keep exact ORFS synthesis/settings; change only the PRE_FLOORPLAN stop hook.
python3 - <<'PYCODE'
from pathlib import Path
s=Path('tools/ref_tile/ref_route.sh').read_text()
a='PRE_FLOORPLAN=tools/ref_tile/native_census.tcl'
assert s.count(a)==1
Path('census/source_route.sh').write_text(s.replace(a,'PRE_FLOORPLAN=tools/qwen_dv/slice8_census_only.tcl'))
PYCODE
export SRC=$PWD OT_ORFS_CORNER_OVERRIDE=TC HM=0.03
set +e
bash census/source_route.sh physical/ref_tile/qfd_dv_slice2_w8/kit.env census "$PWD/census/run" floorplan --native-census > census/driver.log 2>&1
rc=$?
set -e
echo "SOURCE_DRIVER_RC=$rc (no physical verdict: census-only stop omits layout outputs)"
python3 - <<'PYCODE'
import pathlib,json
p=pathlib.Path('census/run/census/work/orfs/native_census.json')
d=json.loads(p.read_text());print('PARENT_NATIVE_CENSUS',d['status'],'max',d.get('max_dynamic_loads'),'violations',len(d.get('violations',[])))
raise SystemExit(0 if d['status']=='PASS' else 1)
PYCODE
