#!/bin/bash
# plan-only OpenSTA dmp_ceff_elmore check of a core_infra_htree model dir (no CTS/GRT)
set -euo pipefail
D=$(readlink -f "$1")
for corner in TT FF; do
  docker run --rm --name r6sta-$(basename $D)-$corner-$$ --cpus=2 --memory=8g --memory-swap=8g -e CORNER=$corner -v "$D":/work openroad/orfs:asap7lock \
    /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/model.tcl > "$D/model_$corner.log" 2>&1 || echo "FAIL $corner"
done
docker run --rm -v "$D":/work openroad/orfs:asap7lock chown -R "$(id -u):$(id -g)" /work
python3 - "$D" <<'PY'
import json,sys,collections
d=sys.argv[1];lo=json.load(open(d+'/leafof.json'));out={}
for c in ('TT','FF'):
  g=collections.defaultdict(list)
  for l in open(f'{d}/arrivals_{c}.tsv'):
    p,v=l.split('\t');g[lo[p.split('/')[0]]].append(float(v))
  m={k:sum(v)/len(v) for k,v in g.items()};allv=[x for v in g.values() for x in v]
  out[c]=dict(n=len(allv),mean=round(sum(allv)/len(allv),2),min=round(min(allv),2),max=round(max(allv),2),leaf_mean_min=round(min(m.values()),2),leaf_mean_max=round(max(m.values()),2),window=round(max(m.values())-min(m.values()),2))
print(json.dumps(out));json.dump(out,open(d+'/sta_summary.json','w'),indent=1)
PY
