import importlib.util,sys,json,re
from pathlib import Path
base=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('lec_probe',base/'lec.py');m=importlib.util.module_from_spec(sp);sys.modules[sp.name]=m;sp.loader.exec_module(m)
g=m.read_aig(base/'failed_pre/gold.aig');t=m.read_aig(base/'failed_pre/gate.aig')
_,gc,*_=m.key_points(g,m.read_map(base/'failed_pre/gold.map'));_,tc,*_=m.key_points(t,m.read_map(base/'failed_pre/gate.map'))
rels=[]
for k in gc:
 if k in tc:continue
 mm=re.match(r'(ff:.*\.a_s\.g6\.u\.u\.u_k5\.g_r\.r)\[(\d+)\]$',k)
 if mm:
  p,b=mm[1],int(mm[2])
  if b==66:rels.append((k,None,0))
  elif 33<=b<=64:
   bit=(0x3fc00000>>(b-33))&1
   rels.append((k,p+'[62]' if bit else None,0))
 elif '.u_eps.g6.u.u.u_k5.g_r.r[66]' in k:rels.append((k,None,0))
roots=[]
for k,p,c in rels:
 roots.append(gc[k])
 if p:roots.append(gc[p])
a=m.raw_prefix_miter(g,roots,8)
lits=list(a.outs);a.outs=[];a.onames=[];i=0
for k,p,c in rels:
 v=lits[i];i+=1
 if p:v=a.XOR(v,lits[i]);i+=1
 a.outs.append(v^c);a.onames.append(k+('=='+p if p else '==0'))
work=base/'prefix_proof';work.mkdir(exist_ok=True)
log=[];st=m.prove(a,work,10000,log,tag='prefix8')
(work/'proof.log').write_text('\n'.join(log))
print(json.dumps({'steps':8,'relations':len(rels),'ands':len(a.ands)//2,'result':st},indent=1),flush=True)
(work/'result.json').write_text(json.dumps(st,indent=1)+'\n')
a.outs=[a.outs[0]^1];a.onames=['mutant_wrong_constant']
mut=m.prove(a,work,10000,log,tag='mutant_wrong_constant')
print('MUTANT',mut,flush=True)
(work/'mutant.json').write_text(json.dumps(mut)+'\n')
assert len(st)==len(rels) and all(s=='proved' for s in st.values())
assert mut['mutant_wrong_constant']=='differs'
