#!/usr/bin/env bash
# Source-pinned ORFS mapped census only. No initialize_floorplan/placement/CTS/route executes.
set -euo pipefail
KIT=qfd_sys_face_f16_main
python3 - <<'PYCHECK'
import json
from pathlib import Path
assert json.loads(Path('bound_construct/emitter_audit.json').read_text())['status']=='PASS'
for p in ['fourstate_sat.log','reset_valid_sat.log']:
 assert 'SUCCESS!' in Path('bound_construct',p).read_text(),p
PYCHECK
cp bound_construct/qfd_sys_face_lctx4_bounded_f16.sv rtl/qwen_split/f16/
cp bound_construct/qfd_sys_face_lctx4_f16_helpers.sv rtl/qwen_split/f16/
# ROOT-authorized ONE historical-image diagnostic; no floorplan/production qualification.
mkdir -p census tools/qwen_split
phase=kit_generation
finish() {
 rc=$?
 python3 - "$rc" "$phase" <<'PYEND'
import json,sys,pathlib,datetime
p=pathlib.Path('census/run/census/work/orfs/native_census.json')
r=dict(rc=int(sys.argv[1]),phase=sys.argv[2],native_census_exists=p.exists(),finished_at=datetime.datetime.now().astimezone().isoformat(),scope='source census only; no layout')
pathlib.Path('census/terminal.json').write_text(json.dumps(r,indent=2)+'\n')
print('SYSFACE_LCTX_TERMINAL '+json.dumps(r))
PYEND
}
trap finish EXIT
python3 tools/ref_tile/ref_tile.py gen tools/ref_tile/specs/${KIT}.json > census/gen_kit.log 2>&1
cat > tools/qwen_split/sys_face_lctx_census_only.tcl <<'TCL'
source /src/tools/ref_tile/native_census.tcl
puts "SYSFACE_LCTX_CENSUS_ONLY_STOP_BEFORE_INITIALIZE_FLOORPLAN"
exit
TCL
# Keep exact ORFS synthesis/settings; change only the PRE_FLOORPLAN stop hook.
python3 - <<'PYCODE'
from pathlib import Path
s=Path('tools/ref_tile/ref_route.sh').read_text()
a='PRE_FLOORPLAN=tools/ref_tile/native_census.tcl'
assert s.count(a)==1
Path('census/source_route.sh').write_text(s.replace(a,'PRE_FLOORPLAN=tools/qwen_split/sys_face_lctx_census_only.tcl'))
PYCODE
phase=mapped_native_census
export SRC=$PWD OT_ORFS_CORNER_OVERRIDE=TC HM=0.03
set +e
bash census/source_route.sh physical/ref_tile/${KIT}/kit.env census "$PWD/census/run" floorplan --native-census > census/driver.log 2>&1
rc=$?
set -e
echo "SOURCE_DRIVER_RC=$rc (no physical verdict: census-only stop omits layout outputs)"
python3 - <<'PYCODE'
import pathlib,json
p=pathlib.Path('census/run/census/work/orfs/native_census.json')
d=json.loads(p.read_text());print('SYSFACE_LCTX_NATIVE_CENSUS',d['status'],'max',d.get('max_dynamic_loads'),'violations',len(d.get('violations',[])))
raise SystemExit(0 if d['status']=='PASS' else 1)
PYCODE
