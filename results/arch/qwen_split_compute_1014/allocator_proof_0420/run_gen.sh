#!/usr/bin/env bash
set -uo pipefail
# GEN only. Source and physical content are immutable inputs; all outputs go outside src.
task_out="$(realpath -m "${1:-../out}")"
mkdir -p "$task_out"
python3 - "$task_out" <<'PYINNER'
import hashlib,json,pathlib,sys,datetime,socket
root=pathlib.Path.cwd(); files={}
for sub in ['tools','rtl','results','physical']:
 for p in (root/sub).rglob('*'):
  if not p.is_file() or p.suffix=='.pyc' or '__pycache__' in p.parts:continue
  h=hashlib.sha256()
  with p.open('rb') as f:
   for part in iter(lambda:f.read(1048576),b''):h.update(part)
  files[str(p.relative_to(root))]=h.hexdigest()
json.dump(dict(scope='EXACT_CONTENT_SNAPSHOT_BEFORE_GEN',source_commit=(root/'SOURCE_COMMIT').read_text().strip(),host=socket.gethostname(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files),open(pathlib.Path(sys.argv[1])/'source_manifest.json','w'),indent=2)
PYINNER
task_rc=0
task_design=results/arch/qwen_split_compute_1014
/usr/bin/time -v env OT_TP8_SPLIT=compute \
 OT_SPLIT_HOMES="$task_design/repack_0030/fpq_r2hs4-homes.json" OT_SPLIT_HOMES_REBASE=1 \
 OT_SPLIT_VM_WH=4872.024,3239.384 OT_SPLIT_PHY_NFACE=1 OT_SPLIT_SYSFACE_XY=18900,12420 \
 OT_SPLIT_TILE_GRANT="$task_design/repack_2210/qfd_tile_nk_rp2_45_a2.held_grant.json" \
 OT_SPLIT_PIN_GRANT="$task_design/repack_0030/su64_west_grant.json" \
 OT_SPLIT_BW_SPREAD=1 OT_SPLIT_TREE_HOSTS=dp OT_SPLIT_ALIGN_BAND_WORDS=0 \
 OT_RELAY_GATE=warn OT_RESET_GATE=warn OT_PIN_ALIGN_GATE=warn \
 OT_RELAY_DUMP="$task_out/allocator_dump.json" OT_RELAY_COLLISION_JSON="$task_out/collision.json" \
 python3 tools/qwen_tp8/relay_data_run.py "$task_out" --case > "$task_out/gen.log" 2>&1 || task_rc=$?
python3 - "$task_out" "$task_rc" <<'PYINNER'
import json,pathlib,sys,datetime
p=pathlib.Path(sys.argv[1]);json.dump(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),exit_code=int(sys.argv[2]),qualified=False,no_auto_chain=True),open(p/'terminal.json','w'),indent=2)
PYINNER
exit "$task_rc"
