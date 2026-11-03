#!/bin/bash
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
python3 - "$D" <<'PY'
from pathlib import Path
import json,sys
D=Path(sys.argv[1]);outlines={'hd_spn_eshim_tx':'95.04x1036.8','hd_st_n3_turn':'1304.64x604.8','hd_st_n3_transit':'1442.88x475.2'}
for n,o in outlines.items():
 p=D/n;p.mkdir(exist_ok=True)
 (p/'dump.tcl').write_text(f'read_db /input/{n}/4_cts.odb\nsource /tools/geom_dump.tcl\n')
PY
docker run --rm --cpus 2 --memory 8g --memory-swap 8g -v "$D/input":/input:ro -v "$D/tools":/tools:ro -v "$D":/out openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; set -e; for n in hd_spn_eshim_tx hd_st_n3_turn hd_st_n3_transit; do OT_GEOM_OUT=/out/$n/geom.tsv openroad -threads 2 -exit /out/$n/dump.tcl > /out/$n/dump.log 2>&1; done'
python3 - "$D" <<'PY'
import subprocess,json,sys
from pathlib import Path
D=Path(sys.argv[1]);rows=[]
for n,o in {'hd_spn_eshim_tx':'95.04x1036.8','hd_st_n3_turn':'1304.64x604.8','hd_st_n3_transit':'1442.88x475.2'}.items():
 p=D/n
 with (p/'rules.log').open('w') as f:
  x=subprocess.run([sys.executable,str(D/'tools/geom_rules.py'),str(p/'geom.tsv'),'--json',str(p/'auto_geom.json'),'--max-layer','M7','--all-kits','--outline',o,'--title',n+' actual4CTS readonly collection'],stdout=f,stderr=subprocess.STDOUT)
 with (p/'png.log').open('w') as f:
  y=subprocess.run([sys.executable,str(D/'tools/geom_png.py'),str(p/'geom.tsv'),str(p/'auto_geom.json'),str(p/'auto_geom.png')],stdout=f,stderr=subprocess.STDOUT)
 rows.append(dict(type=n,native_dump_rc=0,geometry_rc=x.returncode,png_rc=y.returncode,geometry_json=str(p/'auto_geom.json'),scope='read-only existing4CTS; no placement/GRT/STA/physicalPASS'))
(D/'COLLECT_RESULT.json').write_text(json.dumps(rows,indent=1)+'\n')
assert all(x['png_rc']==0 and Path(x['geometry_json']).exists()for x in rows)
print('COLLECTION COMPLETE ONLY; originalnativeverdicts/stops retained, no source/clock/timing/route credit')
PY
