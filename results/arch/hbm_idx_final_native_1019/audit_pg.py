#!/usr/bin/env python3
"""Read-only audit of every raw native PG MTerm; no ignored cell classes."""
import collections, gzip, json
from pathlib import Path
p=Path(__file__).resolve().parent
raw=json.load(gzip.open(p/'raw.json.gz','rt'))
m=raw['modules']['ot_hbm_static_cfg_collar_idx256']; counts=collections.Counter(); bad=[]
for n,c in m['cells'].items():
 for pin,role in c['pin_signal_types'].items():
  native=raw['native_master_pins'][c['type']][pin]
  assert native['signal_type']==role
  if role not in ('POWER','GROUND'): continue
  counts[role]+=1; nets=c['connections'][pin]
  if len(nets)!=1 or m['net_metadata'][str(nets[0])]['signal_type']!=role:
   bad.append([n,pin,role,nets])
expected=json.loads((p/'pg_connectivity_summary.json').read_text())
assert dict(counts)==expected['pins'] and bad==expected['bad']
print('PG_ADOPTION_HOLD missing_or_wrong_role_pins='+str(len(bad)))
