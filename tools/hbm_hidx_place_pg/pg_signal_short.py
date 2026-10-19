"""All actual signal/clock native pin rectangles vs every native PG conductor."""
import gzip,json,collections
from pathlib import Path
o=Path('/work/output');j=json.load(gzip.open(o/'metal.json.gz','rt'));p=json.load(gzip.open(o/'native_pin_geometry.json.gz','rt'))
targets=[]
for pin in p['pins']+p['ports']:
 if pin['role'] not in ['POWER','GROUND']:
  for layer,box in pin['shapes']:targets.append((layer,box,pin.get('cell',pin.get('port')),pin.get('pin'),pin['net']))
grid=collections.defaultdict(list);step=1000
for idx,(layer,box,*rest) in enumerate(targets):
 for x in range(box[0]//step,box[2]//step+1):
  for y in range(box[1]//step,box[3]//step+1):grid[layer,x,y].append(idx)
shorts=[];checked=0
for layer,box,role,owner in j['shapes']:
 if j['layers'][layer]['type']!='ROUTING':continue
 seen=set()
 for x in range(box[0]//step,box[2]//step+1):
  for y in range(box[1]//step,box[3]//step+1):
   for idx in grid.get((layer,x,y),[]):
    if idx in seen:continue
    seen.add(idx);checked+=1;z=targets[idx][1]
    if max(box[0],z[0])<min(box[2],z[2]) and max(box[1],z[1])<min(box[3],z[3]):shorts.append([owner,targets[idx]])
r=dict(scope='Every actual native signal/clock pin rectangle vs every actual native PG routing-metal rectangle; no routed signal wires exist',signal_pin_rectangles=len(targets),PG_shapes=len(j['shapes']),overlap_comparisons=checked,signal_pg_shorts=shorts,verdict='PASS' if not shorts else 'FAIL')
(o/'pg_signal_short.json').write_text(json.dumps(r,indent=2)+'\n');assert not shorts,'SIGNAL_PG_SHORT';print(json.dumps(r))
