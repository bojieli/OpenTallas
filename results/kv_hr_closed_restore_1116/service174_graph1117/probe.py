import sys,json,copy,importlib.util,gc
from pathlib import Path
H=Path('/srv/opentallas-scratch2/claude/fable-fix-kv-pvhub/hg1');K=H/'kvr_c3/tree';O=H/'kvr_c4/service174_graph_v2';O.mkdir(exist_ok=False)
sys.path.insert(0,str(K/'tools/die_plan'))
spec=importlib.util.spec_from_file_location('bind_elab',H/'kvr_c3/bind_elab_dc6.py');mod=importlib.util.module_from_spec(spec);sys.modules['bind_elab']=mod;spec.loader.exec_module(mod);mod.REPO=K;mod.__file__=str(K/'tools/die_plan/bind_elab.py')
import bind as B
B.E.REPO=K
P=K/'physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json';A=K/'physical/die_plan/qwen_kvsys/bind/ctx_hr_1116_v2/asbuilt_ctx_hr.json'
yjs=json.load(open(H/'kvr_c3/gate/bind/asbuilt.json'));out=[]
for label,plan in [('original',P),('service174',H/'kvr_c4/service174_preview/plan_c_service174.json')]:
 raw=json.load(open(plan));raw['asbuilt']=json.load(open(A));raw['asbuilt']['map_file']=str(A.parent/raw['asbuilt']['map_file'])
 b=B.Binder(raw,yjs,P.parent,str(K))
 if b.ab.get('clock_landing_table'):
  import clock_landings as CL
  b._clock_landing_table=json.load(open(K/b.ab['clock_landing_table']))
  CL.expand_station_types(b,b._clock_landing_table)
  b.clock_landings=CL.Landings(raw,b._clock_landing_table,plan_path=P)
 b.map_cells();b.analyse();b.build_buses()
 links=[]
 for L in b.links:
  if L.get('lane')=='L2416':links.append(dict(lane=L['lane'],width=L['width'],cycles=L['cycles'],src=L['src'],dst=L['dst'],sources=[dict(cell=b.F.cells[it[1]].path,port=it[2],bit=it[3]) for it in L['items'] if it[0]=='leaf']))
 r=dict(label=label,unplanned={str(k):v for k,v in b.unplanned.items()},unplanned_bits=b.unplanned_bits,unplanned_errors=[e for e in b.errors if e.startswith('UNPLANNED')],other_constructor_errors=[e for e in b.errors if not e.startswith('UNPLANNED')],service_links=links,scope='constructor/map_cells/analyse/build_buses only; no R8,clock,type emission or physical readiness')
 out.append(r);print(json.dumps(r),flush=True);del b;gc.collect()
(O/'result.json').write_text(json.dumps(out,indent=2)+'\n')
assert len(out[0]['unplanned'])==3,out[0]['unplanned']
assert not out[1]['unplanned'],out[1]['unplanned']
assert len(out[1]['service_links'])==1
l=out[1]['service_links'][0];assert l['width']==174 and len(l['sources'])==174
assert {x['cell'] for x in l['sources']}=={'kvs_emb'} and {x['port'] for x in l['sources']}=={'o_ctx_svc'}
assert sorted(x['bit'] for x in l['sources'])==list(range(174))
print('PASS original3UNPLANNED; dedicatedALL174 clearsALL3 withoutPHYroutes; no physical qualification',flush=True)
