"""DIE-KV-32-SRC independent check: no planned PG access M8/M9 shape (wires + via enclosures) touches or comes within
the M8/M9 min spacing (40 nm) of a die clock-leg reservation (BLOCK M8 0.40-um tall / BLOCK M9 0.40-um wide)."""
import json,sys
from shapely.geometry import box
from shapely.strtree import STRtree
ov=json.load(open(sys.argv[1]));P=sys.argv[2];D=1000
ck={"M8":[o[2:] for o in ov["obstructions"] if o[0]=="BLOCK" and o[1]=="M8" and o[5]-o[3]==400],"M9":[o[2:] for o in ov["obstructions"] if o[0]=="BLOCK" and o[1]=="M9" and o[4]-o[2]==400]}
T={k:STRtree([box(*r) for r in v]) for k,v in ck.items()};bad={"M8":0,"M9":0};n={"M8":0,"M9":0}
for net,ly,*r in json.load(open(P+"/reserved_access.json")):
  if ly not in T:continue
  r=[round(v*D) for v in r];n[ly]+=1;q=[r[0]-40,r[1]-40,r[2]+40,r[3]+40]
  for j in T[ly].query(box(*q)):
    b=ck[ly][j]
    if q[0]<b[2] and b[0]<q[2] and q[1]<b[3] and b[1]<q[3]:bad[ly]+=1;break
print(json.dumps(dict(clock_leg_reservations={k:len(v) for k,v in ck.items()},access_shapes_checked=n,violations_within_40nm=bad)))
