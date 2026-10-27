import json,time,math,statistics,importlib.util
from pathlib import Path
from types import SimpleNamespace
p=Path(__file__).parent

def module(name):
 s=importlib.util.spec_from_file_location(name,p/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
O=module('index_old');N=module('index_new');DI=module('die_infra')
plan=json.loads((p/'plan.json').read_text());spec=json.loads((p/'clock_spec.json').read_text());W,H=plan['die']['outline_um'];P=SimpleNamespace(W=W,H=H,die=plan['die'],layers={'M8':dict(dir='H'),'M9':dict(dir='V')})
pgr=DI.pg_rects(P,DI.pg_grid(P));base=O.pg_shapes(pgr)
nd=dict(width=.32,space=.08,rf=.125,cf=1.6)
mesh=spec['mesh'];segs=[('M8',r['x0'],r['y'],r['x1'],r['y'],'ck_mesh_explicit','mesh') for r in mesh['M8']]+[('M9',r['x'],r['y0'],r['x'],r['y1'],'ck_mesh_explicit','mesh') for r in mesh['M9']]
base+=O.clock_shapes(segs,nd,'VSS')
rules={'4w':dict(width=.16,space=.08),'8w':dict(width=.32,space=.08),'16w':dict(width=.64,space=.5),'2x16w':dict(width=1.28,space=1.)}
groups={}
for nm,c in sorted(spec['cell_sites'].items()):groups.setdefault('g'+str(c['group']),c)
queries=[];pressure=[]
for i,e in enumerate(spec['nets']):
 a,b=groups[e['drv']],groups[e['load']];ax,ay=a['origin_um'];bx,by=b['origin_um'];la=e['layer'];nd=rules[e['ndr']]
 c=(ay+.135+.864) if la=='M8' else (ax+a['w']/2+.864);lo,hi=sorted((ax+a['w']/2,bx+b['w']/2) if la=='M8' else (ay+.135,by+.135))
 sh=O.seg_shapes(la,c,lo,hi,'declared_'+e['edge'],nd,'VSS')
 pressure+=sh
 if i%53==0:queries.extend((s,nd['space']) for s in sh)
queries=queries[:1800]

def build(cls,shapes):
 t=time.perf_counter();ix=cls(.08);ix.pairwise=True
 for s in shapes:
  w=s[4]-s[3];sp=1. if abs(w-1.28)<1e-6 else .5 if abs(w-.64)<1e-6 else .08 if abs(w-.32)<1e-6 or abs(w-.16)<1e-6 else .04
  ix.add(s,space=sp)
 return ix,time.perf_counter()-t

def probe(shapes):
 old,ot=build(O.MetalIndex,shapes);new,nt=build(N.MetalIndex,shapes)
 timings={};results={}
 for name,ix in [('old',old),('new',new)]:
  t=time.perf_counter();hits=[];first=[]
  for s,sp in queries:ix.space=sp;hits.append(sorted(ix.hits(s)));first.append(bool(ix.hits(s,first=True)))
  timings[name]=time.perf_counter()-t;results[name]=(hits,first)
 assert results['old']==results['new'],'hit equivalence mismatch'
 return dict(shapes=len(shapes),queries=len(queries),hit_set_mismatches=0,first_legality_mismatches=0,old_seconds=timings['old'],new_seconds=timings['new'],speedup=timings['old']/timings['new'],index_build_seconds=dict(old=ot,new=nt))
r=dict(verdict='PASS',old_source='99eaa6d63',new_source='975d1b2ee',input='actualR28c_dry11plan/clock_spec',pg_rectangles=len(pgr),fixed_pg_mesh=probe(base),declared_edge_interval_pressure=probe(base+pressure),pressure_scope='Declared physical edge intervals at actualsite+TREE_OFF; NOT routed reservations or dry-build success. Same pairwise geometry predicates in both indexes.')
(p/'result.json').write_text(json.dumps(r,indent=1));print(json.dumps(r,indent=1))
