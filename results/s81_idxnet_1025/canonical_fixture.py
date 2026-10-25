#!/usr/bin/env python3
"""Apply the canonical BK drain contract to the immutable 10-21 stimulus.

Only addressed UID 0x5b/op1 CTLs are consumed. All other golden data/edges stay
unchanged. Assert each removed legacy expected beat equals that exact input.
"""
import gzip, json, pathlib, shutil, sys
src, out = map(pathlib.Path, sys.argv[1:]); out.mkdir(parents=True, exist_ok=True)
x=json.loads((src/'exp.json').read_text()); changes=[]
with gzip.open(src/'stim.txt.gz','rt') as f:
 for line in f:
  e,d,p,b=line.split(); word=int(b,16); payload=word>>21
  if p=='n' and word&1 and (word>>1)&7==0 and payload&255==0x5b and (payload>>8)&7==1:
   edge=str(int(e)+2); expected=x['exp'][d]['vo']
   assert int(expected[edge],16)==word, (d,edge,expected.get(edge),b)
   changes.append(dict(die=int(d),input_edge=int(e),vo_edge=int(edge),legacy_beat=expected.pop(edge)))
assert len(changes)==x['summary']['k_dies']==3, changes
x['canonical_bk_drain_sink']=True
(out/'exp.json').write_text(json.dumps(x,indent=1)+'\n')
(out/'canonical_drain_changes.json').write_text(json.dumps(changes,indent=1)+'\n')
shutil.copy2(src/'args.txt',out/'args.txt');shutil.copy2(src/'stim.txt.gz',out/'stim.txt.gz')
print('canonical fixture: 3 addressed drains consumed; every other expected bit/edge preserved')
