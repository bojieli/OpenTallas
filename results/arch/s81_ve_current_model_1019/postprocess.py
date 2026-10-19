import json,gzip,collections,math
from pathlib import Path
p=Path(__file__).parent
rows=json.loads(gzip.decompress((p/'endpoint_roots.json.gz').read_bytes()))
inv={r['driver']['pin'].rsplit('/',1)[0]:r for r in rows if (r['driver']['master'] or '').startswith('CKINV')}
for r in rows:
 ends={}
 for s in r['sinks']:
  i=s['pin'].rsplit('/',1)[0]
  for e in inv[i]['sinks'] if i in inv else [s]:ends[e['pin']]=e
 r['sinks']=list(ends.values());r['count']=len(ends)
 r['reach_um']=max((abs(r['driver']['xy'][0]-e['xy'][0])+abs(r['driver']['xy'][1]-e['xy'][1]) for e in ends.values()),default=0)
 if (r['driver']['master'] or '').startswith('TIE'):r['driver']['role']='tie'
rows=[r for r in rows if r['driver']['pin'].rsplit('/',1)[0] not in inv]
signal=[r for r in rows if r['driver']['signal']!='CLOCK' and r['driver']['pin']!='PORT/clk']
bad=[r for r in signal if r['count']>32]
reach=[r for r in signal if r['reach_um']>405]
inputs=[r for r in signal if r['driver']['role']=='input' and r['driver']['pin']!='PORT/rst_n']
outputs=[(r['driver'],s) for r in signal for s in r['sinks'] if s['role']=='output']
floors=collections.Counter()
for r in bad:floors[r['driver']['role']]+=math.ceil(r['count']/32)-1
out=dict(roots=len(rows),roles=dict(collections.Counter(r['driver']['role'] for r in rows)),unsafe_roots=len(bad),unsafe_by_role=dict(collections.Counter(r['driver']['role'] for r in bad)),max_by_role={role:max(r['count'] for r in signal if r['driver']['role']==role) for role in set(r['driver']['role'] for r in signal)},over405=[dict(driver=r['driver'],count=r['count'],reach_um=r['reach_um']) for r in reach],copy_lower_bound_by_role=dict(floors),copy_lower_bound_scope='ceil(loads/32)-1 per unsafe root; excludes extra D/copy-enable/reset loads, fixed-point effects and geometry; not a legal source design',signal_input_bits=len(inputs),input_first_sink_nonff=[dict(driver=r['driver'],sinks=r['sinks']) for r in inputs if any(s['role']!='ff' for s in r['sinks'])],output_bits=len(outputs),outputs_nonff=[dict(driver=d,sink=s) for d,s in outputs if d['role']!='ff'],unsafe=sorted([dict(driver=r['driver'],count=r['count'],reach_um=r['reach_um']) for r in bad],key=lambda r:-r['count']),transparent_correction='Raw extraction traverses BUF/INV; this pass additionally traverses the sole native CKINVDCx12 inverter, preserving reset provenance. Clock PORT/clk excluded from signal32/reach checks.')
(p/'native_corrected.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ('unsafe','input_first_sink_nonff','outputs_nonff')}))
