#!/usr/bin/env python3
"""QC-IMPORT-2: extract bound-boundary geometry from the bound source (OpenROAD python) for the GEOM render."""
import odb, json, sys
d = odb.dbDatabase.create(); odb.read_db(d, sys.argv[1]); b = d.getChip().getBlock(); D = b.getDbUnitsPerMicron()
bind = json.load(open(sys.argv[2]))['ports']
def bb(x): r = x.getBBox(); return [r.xMin()/D, r.yMin()/D, r.xMax()/D, r.yMax()/D]
out = dict(parts={i.getName(): [i.getMaster().getName(), bb(i)] for i in b.getInsts() if i.getMaster().isBlock()}, start={}, reset={}, clock={})
for p, q in bind.items():
    ep = q['native_endpoints'][0]; it = b.findInst(ep['inst']).findITerm(ep['pin'])
    out[{'start_output': 'start', 'reset': 'reset', 'clock': 'clock'}[q['role']]][p] = dict(net=q['net'], inst=ep['inst'], pin=ep['pin'], xy=bb(it))
json.dump(out, open(sys.argv[3], 'w'))
print({k: len(v) for k, v in out.items()})
