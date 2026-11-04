#!/usr/bin/env python3
"""RF-EG follow-up (DIE-S81-53 11-04): ADDED taps inside the 8.64 um halo of the new egn/egg boxes move to the nearest halo edge.  Text edit, JSON equality asserted."""
import json,re,sys
sys.path.insert(0,"tools/die_plan")
from placement_obstacles import placement_boxes
import schema
F="physical/die_plan/s81/plan_h2_2249.json"
s=open(F).read(); p=json.loads(s); clear=schema.TAP_CLEAR_UM; mv=[]
for n,t in p["partition_types"].items():
    boxes=placement_boxes(t,halo=clear)
    if not any(c.get("module")=="ot_s81sl_egn" for c in t.get("hard_cores",[])): continue
    grid=[]
    for a in t["clock"].get("added_taps",[]):
        x,y=a["xy"]
        for k,(x0,y0,x1,y1) in boxes.items():
            if x0<x<x1 and y0<y<y1:
                c=sorted([(x-x0,round(x0-.01,3),y),(x1-x,round(x1+.01,3),y),(y-y0,x,round(y0-.01,3)),(y1-y,x,round(y1+.01,3))])
                for _,nx,ny in c:
                    if not any(b[0]<nx<b[2] and b[1]<ny<b[3] for b in boxes.values()) and not any(o is not a and abs(nx-o["xy"][0])<clear and abs(ny-o["xy"][1])<clear for o in t["clock"]["added_taps"]):
                        break
                else: raise SystemExit(("no site",n,a))
                mv.append((n,a["name"],[x,y],[nx,ny])); a["xy"]=[nx,ny]; break
for n,tp,o,nw in mv:
    i=s.index('"%s"'%n, s.index('"partition_types"')); j=s.index('"added_taps"',i)
    m=re.compile(r'("name":\s*"%s",\s*"xy":\s*\[\s*)%s(,\s*)%s(\s*\])'%(tp,re.escape(repr(o[0])),re.escape(repr(o[1])))).search(s,j)
    assert m,(n,tp,o)
    s=s[:m.start()]+m.group(1)+repr(nw[0])+m.group(2)+repr(nw[1])+m.group(3)+s[m.end():]
    print(n,tp,o,nw)
assert json.loads(s)==p
open(F,"w").write(s)
