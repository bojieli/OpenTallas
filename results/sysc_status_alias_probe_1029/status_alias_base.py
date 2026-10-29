import json,pickle,re
from pathlib import Path
import lec as E
w=Path('.')
with (w/'state_candidate.pkl').open('rb') as f:L=pickle.load(f)
hints=json.loads((w/'status_alias_hints.json').read_text());pairs=[(h[2][2],h[1]) for h in hints]
raw=[];keymaps=[];reset={}
for sd,d,cp,points,col in [('gold',L.gold,L.gc,L.gp,0),('gate',L.gate,L.tc,L.tp,1)]:
 levels={};R=E.reset_vars(d,points,levels=levels,declared=L.kit_reset_ports);reset[sd]=levels
 a=E.Aig();a.ni=d['I']+d['L'];v={0:0}
 for i in range(1,a.ni+1):v[i]=R.get(i,2*i)
 def val(l):return v[l>>1]^(l&1)
 for j,(u,z) in enumerate(zip(d['ands'][::2],d['ands'][1::2])):v[d['I']+d['L']+1+j]=a.AND(val(u),val(z))
 rd=dict(d);rd['ands']=a.ands;rd['A']=len(a.ands)//2;rd['latches']=[val(x) for x in d['latches']]
 r=E.raw_prefix_miter(rd,[val(cp[pair[col]]) for pair in pairs],4);raw.append(r)
 keys={}
 for k in sorted(L.matched):
  if k in points and 0<points[k]>>1<=d['I']:
   keys[points[k]>>1]=(k,points[k]&1)
 keymaps.append(keys)
m=E.Aig();inputs={};maps=[]
# Shared original PIs at the same frame are correlated; independent initial
# latch states and unbound/X sources remain independent across the two sides.
for side,r,keys in zip(['gold','gate'],raw,keymaps):
 vm={0:0}
 for i,name in enumerate(r.inames,1):
  frame,var=map(int,re.fullmatch(r'raw_t(\d+)_v(\d+)',name).groups())
  if var in keys:
   key,inv=keys[var];key=f't{frame}:{key}'
  else:key=f'{side}:{name}';inv=0
  if key not in inputs:inputs[key]=m.add_input(key)
  vm[i]=inputs[key]^inv
 maps.append(vm)
for r,vm in zip(raw,maps):
 def v(l):return vm[l>>1]^(l&1)
 for j,(a,b) in enumerate(zip(r.ands[::2],r.ands[1::2])):vm[r.ni+1+j]=m.AND(v(a),v(b))
for i,(g,t) in enumerate(pairs):
 a=raw[0].outs[i];b=raw[1].outs[i];m.outs.append(m.XOR(maps[0][a>>1]^(a&1),maps[1][b>>1]^(b&1)));m.onames.append(f'base4:{g}={t}')
log=[];status=E.prove(m,w,1000,log,tag='status_alias_reset_base4')
(w/'status_alias_reset_base4.log').write_text('\n'.join(log));(w/'status_alias_reset_base4.json').write_text(json.dumps({'reset':reset,'status':status},indent=2)+'\n');print({s:list(status.values()).count(s) for s in set(status.values())},flush=True)
