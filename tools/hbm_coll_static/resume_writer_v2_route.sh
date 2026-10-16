#!/usr/bin/env bash
# Resume the source-exact v2 pin-capture CTS checkpoint, preserving its gate run.
set -euo pipefail
gate=$1
out=$2
image=$3
[ ! -e "$out" ]
python3 - "$gate" <<'PY'
import hashlib,json,sys
from pathlib import Path
r=Path(sys.argv[1]); m=json.loads(Path(str(r)+'.source_snapshot.json').read_text())
checked=0
for item in m['files']:
 if item['kind']!='file': continue
 p=r/'src'/item['path']
 assert p.is_file(), str(p)
 assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'],str(p)
 checked+=1
print('FROZEN_SOURCE_VERIFIED files='+str(checked))
PY
mkdir -p "$out/work"
cp -a "$gate/routes/gate/work/orfs" "$out/work/orfs"
cp "$gate.source_snapshot.json" "$out/source_snapshot.json"
cp "$gate/ck.json" "$out/cts_insertion.json"
C=$out/work/orfs
S=$gate/src
base=$(find "$C/results/asap7" -mindepth 2 -maxdepth 2 -type d -name base -print -quit)
[ -f "$base/4_cts.odb" ]
python3 - "$C" "$out/checkpoint_before.json" <<'PY'
import hashlib,json,sys
from pathlib import Path
c=Path(sys.argv[1]); paths=[]
for top in ('results','logs','reports'):
 for p in (c/top).rglob('*'):
  if p.is_file() and p.name[:2] in ('1_','2_','3_','4_'):
   paths.append({'path':str(p.relative_to(c)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mtime_ns':p.stat().st_mtime_ns})
Path(sys.argv[2]).write_text(json.dumps(paths,indent=1)+'\n')
PY
bash "$S/tools/closure_loop/resume_check.sh" "$C" "$S" 5_1_grt > "$out/resume_check.log" 2>&1
/usr/bin/docker run --rm -e LEC_CHECK=0 -v "$S:/src:ro" -v "$C:/work" -w /OpenROAD-flow-scripts/flow "$image" bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts && python3 /src/tools/orfs_allcorner_spef.py /OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=8 finish metadata-generate' > "$out/route.log" 2>&1
python3 - "$C" "$out/checkpoint_before.json" <<'PY'
import hashlib,json,sys
from pathlib import Path
c=Path(sys.argv[1]); rows=json.loads(Path(sys.argv[2]).read_text())
for row in rows:
 p=c/row['path']
 assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],str(p)
 assert p.stat().st_mtime_ns==row['mtime_ns'],str(p)+' unexpectedly regenerated'
print('CTS_CHECKPOINT_UNCHANGED files='+str(len(rows)))
PY
printf 'flow_rc=0\n' > "$out/status"
cp "$S/physical/ref_tile/hcoll_vmwrite_static_v2/signoff.sdc" "$out/signoff.sdc"
cd "$S"
python3 tools/w18/corner_sta_ref.py --orfs-dir "$C" --extra-sdc "$out/signoff.sdc" --output "$out/corner_sta.json" > "$out/sta.log" 2>&1
printf 'corner_rc=0\n' >> "$out/status"
echo 'SOURCE_EXACT_WRITER_ROUTE_COMPLETE'
