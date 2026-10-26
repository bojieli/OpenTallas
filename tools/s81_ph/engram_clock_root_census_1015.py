#!/usr/bin/env python3
"""Actual source-expanded FF clock census. No clock, area or route qualification."""
import collections,json,sys
from pathlib import Path
state={'$dff','$dffe','$adff','$adffe','$sdff','$sdffe','$sdffce','$aldff','$aldffe','$dffsr','$dffsre'}
modules=json.loads(Path(sys.argv[1]).read_text())['modules']
selected=[(n,m) for n,m in modules.items() if m.get('attributes',{}).get('top') not in (None,'0','00000000000000000000000000000000')]
assert len(selected)==1, 'Expected exactly one actual elaborated top'
actual_top,m=selected[0]
assert 'dsfd_engram_lkp_clock_roots' in actual_top, actual_top
roots={}
for name,width in [('ck',1),('ck_hash',6),('ck_rows',6)]:
 p=m['ports'][name];assert p['direction']=='input' and len(p['bits'])==width
 for i,bit in enumerate(p['bits']):
  assert isinstance(bit,int) and bit not in roots
  roots[bit]=name if width==1 else f'{name}[{i}]'
counts=collections.Counter();types=collections.Counter()
for name,c in m['cells'].items():
 t=c['type'];types[t]+=1
 if t in state:
  ck=c['connections']['CLK'];assert len(ck)==1 and ck[0] in roots,(name,ck)
  counts[roots[ck[0]]]+=len(c['connections']['Q'])
 else:
  assert t.startswith('$') and not any(k in t.lower() for k in ('latch','mem','dff','ffsr')) and t not in ('$ff','$sr','$fsm'),(name,t)
assert set(counts)==set(roots.values()),counts
record={'schema':'opentallas.s81.engram_clock_root_census.v1','scope':'Actual flattened generic source FF ownership; not mapped area/CTS/IO/physical/production qualification','top':actual_top,'clock_flop_bits':dict(sorted(counts.items())),'roots':len(counts),'total_flop_bits':sum(counts.values()),'maximum_root_bits':max(counts.values()),'cells_by_type':dict(types),'all_roots_at_most15000':max(counts.values())<=15000}
Path(sys.argv[2]).write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
assert record['all_roots_at_most15000'], 'Actual root split is insufficient'
