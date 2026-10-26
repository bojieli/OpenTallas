#!/bin/bash
set -euo pipefail
WT=$(git rev-parse --show-toplevel);cd "$WT"
[ -z "$(git status --porcelain --untracked-files=no)" ] || { echo 'DIRTY refuse';exit 2; }
FACE_SOURCES=${FACE_SOURCES:?exact emitted physical face source directory}
D=${1:?fresh output};[ ! -e "$D" ] || { echo 'OUTPUT EXISTS refuse';exit 2; };mkdir -p "$D"
git rev-parse HEAD > "$D/source_commit.txt"
CARGS=(--write "${WRITE_INSTR:-602}")
python3 tools/hbm_b2/q3stageb/topk_rows.py "$D/prog" --done "${DONE_INSTR:-609}" "${CARGS[@]}"
python3 tools/hbm_b2/q3sync/q3_sync_profile.py --root . --files tools/hbm_b2/q3sync/q3b.files --out "$D/gen" --census "$D/census.json" > "$D/gen.log" 2>&1
ASM=rtl/hbm_accel/cores_split/ot_hfd_coll_q3_hard_v8x/ot_hbm_q3_producer_native.sv
python3 tools/hbm_b2/q3prog/q3_asm_alias_loops.py "$ASM" "$D/asm.sv" "$D/alias.json"
python3 tools/hbm_b2/q3sync/q3_assembly_sync.py --asm "$D/asm.sv" --census tools/hbm_b2/q3sync/cohort.json --gen "$D/gen" --out "$D/asm_sync.sv" --report "$D/asm_sync.json"
python3 tools/hbm_b2/q3sync/face_native_adapter.py --face-dir "$FACE_SOURCES" --adapter-dir results/clock/q3_common_clock_2144 --assembly "$D/asm_sync.sv" --out "$D/faces" > "$D/face_adapter.log"
python3 - "$D" > "$D/qsrc.files" <<'PY'
import sys,json
c=json.load(open('tools/hbm_b2/q3sync/cohort.json'));fs=[]
for k in c['core_filelists']:
 for f in c['core_filelists'][k]['files']:
  p=sys.argv[1]+'/gen/'+f
  if p not in fs:fs.append(p)
 for f in c['core_filelists'][k]['macros']:
  if f not in fs:fs.append(f)
print('\n'.join(fs))
PY
mapfile -t QSRC < "$D/qsrc.files"
python3 - "$FACE_SOURCES/ot_hbm_face_reg.sv" > "$D/tsrc.files" <<'PY'
import json,hashlib,sys
for e in json.load(open('tools/hbm_b2/q3stageb/tkm_faces_sources.json')):
 p=e['path'];assert hashlib.sha256(open(p,'rb').read()).hexdigest()==e['sha256']
 if p.endswith('ot_hbm_face_reg.sv'):
  assert open(p,'rb').read()==open(sys.argv[1],'rb').read(), 'different physical face-register cells'
 elif not p.endswith('tb_hbm_tkm_bound_tkx_ft21.sv'):print(p)
PY
mapfile -t TSRC < "$D/tsrc.files"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
/usr/bin/time -v "$V" --binary --timing --hierarchical --verilate-jobs 2 --build-jobs "${JOBS:-8}" -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT +define+ROOT_CB=21 +define+ROOT_CLRB=0 +define+TILE_FT +define+TKM_DELIVERED_ROOT_VIEW +define+TKM_NOID_VIEW +define+TKM_PR_ENDPOINTS +define+DUT=ot_hbm_q3_producer_native__q3sync --top-module tb_q3stageb --Mdir "$D/obj" tools/hbm_b2/q3stageb/tb_q3stageb.sv "$D/faces/asm_faces.sv" "$D/faces/native_face_adapters.sv" "$FACE_SOURCES"/*.sv "${QSRC[@]}" "${TSRC[@]}" > "$D/build.log" 2>&1
NR=$(python3 -c "import json;print(json.load(open('$D/prog/manifest.json'))['rows'])")
set +e
"$D/obj/Vtb_q3stageb" +DIR="$D/prog" +NR="$NR" > "$D/sim.log" 2>&1
RC=$?;set -e
echo "$RC" > "$D/exit.txt";cat "$D/sim.log"
[ "$RC" -eq 0 ] || exit "$RC"
grep -qx 'Q3STAGEB PASS' "$D/sim.log" || { echo 'STAGEB TERMINAL PASS MARKER MISSING';exit 1; }
! grep -qE 'FIRST_FAULT|Q3STAGEB FAIL' "$D/sim.log" || { echo 'STAGEB FAILURE IN LOG';exit 1; }
echo Q3STAGEB_RUN_PASS
