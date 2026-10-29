# usage: unmapped_census.py WT RUN PLAN ASBUILT_MANIFEST ELAB_ASBUILT OUT
import sys,json,collections
from pathlib import Path
w,run,plan,abm,elab,out=sys.argv[1:7]
sys.path.insert(0,str(Path(w)/'tools'));sys.path.insert(0,str(Path(w)/'tools/die_plan')); import bind as B
p=json.loads(Path(plan).read_text()); a=json.loads(Path(abm).read_text()); p['asbuilt']=a
b=B.Binder(p,json.loads(Path(elab).read_text()),Path(plan).parent,a['base']); b.map_cells()
g=collections.defaultdict(lambda: dict(cells=0,seq=0,qbits=0,mods=collections.Counter()))
rows=[]
for i,c in enumerate(b.F.cells):
    if i in b.cpart or b.G.kind[i] not in ('glue','leaf'): continue
    parts=c.path.split('.')
    pre='.'.join(parts[:2]) if len(parts)>2 else parts[0]
    d=g[pre]; d['cells']+=1; d['mods'][c.module]+=1
    if any(x in c.module.lower() for x in ('dff','latch')): d['seq']+=1; d['qbits']+=len(c.ports.get('Q',[]))
    rows.append([c.path,c.module,b.G.kind[i]])
res=dict(total=b.n_unmapped,groups={k:dict(v,mods=dict(v['mods'].most_common(8))) for k,v in sorted(g.items(),key=lambda x:-x[1]['cells'])})
Path(out).write_text(json.dumps(dict(res,cells=rows)))
print(json.dumps(dict(total=res['total'],groups={k:{kk:vv for kk,vv in v.items()} for k,v in list(res['groups'].items())[:40]}),indent=0)[:6000])
