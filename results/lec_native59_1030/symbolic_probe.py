"""Exact cone bounded prefix, reset4 then release; no invariants or output waivers."""
import sys,json,collections
from pathlib import Path
from functools import lru_cache
sys.setrecursionlimit(20000)
sys.path.insert(0,str(Path(__file__).parent));import lec
p=Path(__file__).parent/'native59';N=12
L=lec.Lec(lec.read_aig(p/'gold.aig'),lec.read_map(p/'gold.map'),lec.read_aig(p/'gate.aig'),lec.read_map(p/'gate.map'))
m=lec.Aig();ds={'gold':L.gold,'gate':L.gate};ps={'gold':L.gp,'gate':L.tp}
logical={sd:{v>>1:(k,v&1) for k,v in ps[sd].items() if k.startswith(('pi:','bb:'))} for sd in ds}
allkeys=sorted({k for sd in ds for k,v in logical[sd].values() if k!='pi:arst_n[0]'})
shared={(k,t):m.add_input(f'{k}@{t}') for k in allkeys for t in range(N)}
gi={i:m.add_input('gateinit:'+str(i)) for i in range(L.gate['L'])}
gold_i={i:m.add_input('goldinit:'+str(i)) for i in range(L.gold['L'])}
gold_x={(v>>1,t):m.add_input(f'goldX{v>>1}@{t}') for v in L.gx for t in range(N)}
gate_x={(v>>1,t):m.add_input(f'gateX{v>>1}@{t}') for v in L.tx for t in range(N)}
OR=lambda a,b:m.AND(a^1,b^1)^1
@lru_cache(None)
def node(sd,v,t):
 d=ds[sd];I,NL=d['I'],d['L'];base=I+NL+1
 if v==0:return 0,0
 if v in logical[sd]:
  k,inv=logical[sd][v]
  return ((0 if t<4 else 1)^inv,0) if k=='pi:arst_n[0]' else (shared[k,t]^inv,0)
 if v<=I:return (gold_x[v,t],0) if sd=='gold' else (gate_x[v,t],0)
 if v<base:
  if t==0:return (gold_i[v-I-1],0) if sd=='gold' else (gi[v-I-1],0)
  return lit(sd,d['latches'][v-I-1],t-1)
 a,b=d['ands'][2*(v-base):2*(v-base)+2]
 av,ax=lit(sd,a,t)
 if av==ax==0:return 0,0
 bv,bx=lit(sd,b,t)
 if bv==bx==0:return 0,0
 val=m.AND(av,bv)
 if sd=='gate' or (not ax and not bx):return val,0
 nozero=m.AND(m.AND(av^1,ax^1)^1,m.AND(bv^1,bx^1)^1)
 return val,m.AND(nozero,m.AND(ax^1,bx^1)^1)
def lit(sd,x,t):
 a,b=node(sd,x>>1,t);return a^(x&1),b
print('all gate anonymous inputs quantified',len(L.tx),flush=True)
orig=json.load(open(p/'lec.json'))
points={e['point'] for e in orig['failing']}
points.update(k for k in L.gc if k.startswith('po:head_descriptor_tag') and k.endswith(tuple('['+str(i)+']' for i in range(37,43))))
points=sorted(points)
print('selected',len(points),'including',sum(k.startswith('po:') for k in points),'observable outputs',flush=True)
for k in points:
 for t in range(N):
  gv,gx=lit('gold',L.gc[k],t);tv,tx=lit('gate',L.tc[k],t)
  m.outs.append(m.AND(m.XOR(gv,tv),gx^1));m.onames.append(f'{k}@edge{t+1}')
  if t==N-1 and (k=='po:head_descriptor_tag[37]' or k=='ff:u_dut.u_bound.u_bout_head_descriptor_tag.q[37]'):
   m.outs.append(m.AND(m.XOR(gv,tv^1),gx^1));m.onames.append('wrongvalue-mutant:'+k)
print('prefix built',len(m.outs),'ands',len(m.ands)//2,'points',len(points),flush=True)
lec.abc_bin=lambda:'/home/ubuntu/.local/opentallas-tools/bin/yosys-abc'
log=[];st=lec.prove(m,p,1000,log,tag='symbolic4_release12')
(p/'symbolic4_release12.json').write_text(json.dumps(st,indent=1));(p/'symbolic4_release12.log').write_text('\n'.join(log));print(dict(collections.Counter(st.values())),flush=True)
