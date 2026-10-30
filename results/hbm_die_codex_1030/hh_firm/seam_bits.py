#!/usr/bin/env python3
import sys,json
from pathlib import Path
sys.path.insert(0,sys.argv[1]+'/tools/die_plan')
import schema as S
import die_hop_scan as D
P=S.Plan(S.load(sys.argv[2]),Path(sys.argv[2]));tabs={};out=[]
def tab(t):
 if t not in tabs:tabs[t]=D.type_tables(P,t)
 return tabs[t]
for pid,pr in P.ports.items():
 if not pid.startswith(('L700_','L701_')):continue
 A,B=pr['src']['part'],pr['dst']['part'];ba,bb=pr['src']['bus'],pr['dst']['bus']
 (pa,ca),(pb,cb)=tab(P.parts[A]['type']),tab(P.parts[B]['type']);sa,sb=P.buses(A)[ba].get('slot'),P.buses(B)[bb].get('slot')
 rows=[]
 for bit in range(S.port_pins_count(pr)):
  qa,qb=P.to_die(A,pa[ba][bit][:2]),P.to_die(B,pb[bb][bit][:2])
  ra=P.to_die(A,ca[sa][bit][-1]) if sa else qa;rb=P.to_die(B,cb[sb][bit][0]) if sb else qb
  ds=(D.md(ra,qa),D.md(qa,qb),D.md(qb,rb));rows.append(dict(bit=bit,hop_um=sum(ds),segments_um=ds))
 out.append(dict(port=pid,a=A+'.'+ba,b=B+'.'+bb,bits=len(rows),over405=sum(r['hop_um']>405+1e-6 for r in rows),worst=max(rows,key=lambda r:r['hop_um'])))
r=dict(scope='Actual new HH per-bit FF->outputpin->inputpin->FF seams, same pin tables/bit indices/orientation as native hardening',ports=out)
Path(sys.argv[3]).write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r),flush=True)
