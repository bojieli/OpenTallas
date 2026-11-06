import json
from pathlib import Path
r=Path(__file__).parent
class Q:
 def __init__(self,cap=None):self.a=self.b=self.la=self.lb=self.iss=0;self.cap=cap;self.peak=0;self.drops=0;self.total=[0,0]
 def step(self,rn,la,lb):
  if not rn:self.__init__(self.cap);return
  dec=int(not self.iss and bool(self.a or self.b));ta=int(dec and self.a!=0);tb=int(dec and self.a==0)
  wa=int(self.la and (self.cap is None or self.a-ta<self.cap));wb=int(self.lb and (self.cap is None or self.b-tb<self.cap));self.drops+=self.la+self.lb-wa-wb
  self.a+=wa-ta;self.b+=wb-tb;self.la,self.lb,self.iss=la,lb,dec;self.peak=max(self.peak,self.b+lb);self.total[0]+=la;self.total[1]+=lb
bounded=[Q(8),Q(8)];free=[Q(),Q()];errors=[];rows=0
for ln in open(r/"arrivals.log"):
 if not ln.startswith("ARR "):continue
 _,s,c,rn,la,lb,na,nb,iss=ln.split();s,c,rn,la,lb,na,nb,iss=map(int,[s,c,rn,la,lb,na,nb,iss]);rows+=1
 bounded[s].step(rn,la,lb);free[s].step(rn,la,lb)
 if (bounded[s].a,bounded[s].b,bounded[s].iss)!=(na,nb,iss):errors.append([s,c,[bounded[s].a,bounded[s].b,bounded[s].iss],[na,nb,iss]])
out=dict(schema="opentallas.mesh_copy_queue_bound.v1",actual_RBL=1,observed_BQ=8,edges=rows//2,bounded_model_mismatches=len(errors),first_mismatches=errors[:5],observed_bounded_peaks=[q.peak for q in bounded],bounded_drops=[q.drops for q in bounded],unbounded_peak=[q.peak for q in free],arrivals=[q.total for q in free],required_BQ=max(q.peak for q in free),scope="actual native bench input/CRC replay trace; unbounded copyqueue with identical registered landing/A-priority/2edge issue recurrence, not arbitrary-fault-duration guarantee")
(r/"queue_bound.json").write_text(json.dumps(out,indent=1)+"\n");print(json.dumps(out,indent=1));assert rows>=20000 and not errors
