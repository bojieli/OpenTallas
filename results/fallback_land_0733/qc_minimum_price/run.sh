#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
BASE=/srv/opentallas-scratch2/claude/tok-qk-qce
AGES=/srv/opentallas-scratch2/claude/tok-qk-qcl/r1/die
mkdir -p compose
ln -sfn "$BASE/compose/src" compose/src
ln -sfn "$BASE/compose/tree" compose/tree
for stages in 2 3; do
 mkdir -p "case$stages"
 cp rederive_edges.py cb16_path.json "case$stages/"
 python3 - "$stages" <<'PY'
import json,gzip,sys
from pathlib import Path
n=int(sys.argv[1]);d=json.load(gzip.open('bus_groups.json.gz','rt'));rows=[]
for g in d['landing']:
 for m in g['members']:
  if m['lane']=='sl_E3_fe__l9_eo_l9_wi':
   rows.append(dict(sink=g['sink'],sink_port=m['sink_port'],source=m['source'],sink_bits=m['sink_bits'],before=m['landed_stages'],after=m['landed_stages']+n));m['landed_stages']+=n;m['bound_stages']+=n
assert len(rows)==1
p=Path('case'+str(n));(p/'edge_change.json').write_text(json.dumps(rows,indent=1))
with gzip.open(p/'bus_groups.json.gz','wt') as f:json.dump(d,f)
PY
 python3 "case$stages/rederive_edges.py" "case$stages/bus_groups.json.gz" v7 > "case$stages/rederive.log"
 python3 compose_edges.py "$PWD/compose" "edge_plus$stages" "$AGES/build/slice_ages.json" "$AGES/build/vec_ages.json" "$AGES/cal_mat/stn_ages.json" "$(cat "$AGES/vflags.txt")" --replace "$PWD/case$stages/edges_v7_rederived.json" "$PWD/case$stages/lane_ages_v7_rederived.json" > "case$stages/compose.log" 2>&1
 done
