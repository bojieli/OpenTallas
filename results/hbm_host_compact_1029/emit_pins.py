#!/usr/bin/env python3
"""Emit conditional HOST pin-template proposal; does not mutate a die plan."""
import json,sys,collections
from pathlib import Path
P=Path(__file__).parent
old=json.load(open(sys.argv[1]));faces=collections.defaultdict(list);out=[]
for p in old:
 if p['name']=='clk':q=dict(p);q.update(x=207.384,y=116.64);out.append(q);continue
 f='W' if p['x']<1 else 'E' if p['x']>433 else 'N' if p['y']>479 else 'S';faces[f].append(p)
for f,ps in faces.items():
 axis='x' if f in 'NS' else 'y';ps.sort(key=lambda p:p[axis]);lo=2.184;hi=(414.72 if f in 'NS' else 233.28)-2.184
 for i,p in enumerate(ps):
  q=dict(p);a=lo+(hi-lo)*i/max(1,len(ps)-1);a=round(round((a-.024)/.048)*.048+.024,3)
  q.update(x=a if f in 'NS' else .096 if f=='W' else 414.624,y=a if f in 'EW' else .096 if f=='S' else 233.184);out.append(q)
assert len(out)==len(old)==1368 and {p['name']for p in out}=={p['name']for p in old}
(P/'pins_candidate.json').write_text(json.dumps(out,indent=2)+'\n')
print('PROPOSAL ONLY',len(out),'pins; preserved exactname set',dict((f,len(ps))for f,ps in faces.items()))
