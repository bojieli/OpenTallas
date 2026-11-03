#!/bin/bash
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
for n in hd_spn_eshim_tx hd_st_n3_turn; do
  mkdir -p "$D/$n/geom5"
  docker run --rm --cpus 2 --memory 8g --memory-swap 8g -v "$D/$n":/work -v "$D/$n/native":/work/native:ro -v "$D/tools":/tools:ro openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; OT_GEOM_OUT=/work/geom5/geom.tsv openroad -threads 2 -exit /work/dump5.tcl > /work/geom5/dump.log 2>&1'
done
python3 - "$D" <<'PY'
from pathlib import Path
import json,subprocess,sys
D=Path(sys.argv[1]);rows=[]
for n,o in {'hd_spn_eshim_tx':'95.04x1036.8','hd_st_n3_turn':'1304.64x604.8'}.items():
 k=D/n;p=k/'geom5'
 with (p/'rules.log').open('w') as f:
  x=subprocess.run([sys.executable,str(D/'tools/geom_rules.py'),str(p/'geom.tsv'),'--json',str(p/'auto_geom.json'),'--max-layer','M7','--all-kits','--outline',o,'--land-slots',str(k/'land_slots.json'),'--face-guard',str(k/'face_guard.json'),'--title',n+' actual saved5GRT before readonly pathquery'],stdout=f,stderr=subprocess.STDOUT)
 with(p/'png.log').open('w')as f:subprocess.run([sys.executable,str(D/'tools/geom_png.py'),str(p/'geom.tsv'),str(p/'auto_geom.json'),str(p/'auto_geom.png')],stdout=f,stderr=subprocess.STDOUT,check=True)
 rows.append(dict(type=n,geometry_rc=x.returncode,odb_sha256=json.load(open(D/'SOURCE.json'))[n]['native/5_1_grt.odb']))
(D/'LOOK_READY.json').write_text(json.dumps(rows,indent=1)+'\n')
PY
# Own reviewer checks these exact saved5GRT images before allowing this SAME
# bounded job to perform read-only timing. This never waits for an owner answer.
for attempt in $(seq 1 120); do
  [ ! -f "$D/LOOK_RELEASE.json" ] || break
  sleep 5
done
test -f "$D/LOOK_RELEASE.json" || { echo 'NOT RUN STA: saved5GRT LOOK absent'; exit 75; }
python3 - "$D" <<'PY'
import json,sys,hashlib
from pathlib import Path
D=Path(sys.argv[1]);s=json.load(open(D/'SOURCE.json'));v=json.load(open(D/'LOOK_RELEASE.json'))
assert v.get('personally_viewed') is True
assert v.get('source')==s
for n,files in s.items():
 for f,sha in files.items():assert hashlib.sha256((D/n/f).read_bytes()).hexdigest()==sha,(n,f)
PY
for n in hd_spn_eshim_tx hd_st_n3_turn; do
  for c in TT FF; do
    docker run --rm --cpus 2 --memory 8g --memory-swap 8g -v "$D/$n":/work -v "$D/$n/native":/work/native:ro -e OT_POSTCTS_GRT=1 -e OT_CORNER="$c" -e ODB=/work/native/5_1_grt.odb openroad/orfs:asap7lock bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /work/verify_context.py; openroad -threads 2 -exit /work/path_query.tcl' > "$D/$n/query_$c.log" 2>&1
  done
done
echo 'EXACT READONLY PATH QUERY COMPLETE; no gate reinterpretation, repair, route or adoption'
