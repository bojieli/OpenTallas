"""Keep measured GU improvement distinct from a qualified eight-frame projection.

GU old/new both use spine-go0 -> frame-root RET. WQBP's existing fullsix record
uses first actual element capture -> RET. The eight-frame projection explicitly
uses the earlier spine-go origin1189 and retains existing transport195 + owed
source-age edges; it is not promoted to headline or used as a baseline override.
"""
import hashlib,importlib.util,json,sys
from pathlib import Path
R=Path.cwd();spec=importlib.util.spec_from_file_location('tc',R/'tools/toksim_s81_compose.py');tc=importlib.util.module_from_spec(spec);spec.loader.exec_module(tc)
O=Path('/srv/opentallas-scratch/codex/s81-rom12-1020/out/compose');O.mkdir(parents=True,exist_ok=False)
original=tc.node_cycles
cases=[('measured_baseline',None,False,False),('GU_same_origin_only',None,True,False),('calpipe_existing','calpipe',False,False),('calpipe_plus_GU_same_origin','calpipe',True,False),('compiled_eight_frame_qualified','calpipe',True,True)]
summary={}
for name,scenario,gu,wqb in cases:
 def nc(n,ov):
  c,how=original(n,ov)
  if c is not None and gu and n.get('op')=='ffn.experts_gu' and abs(c-3680)<0.01:return 2810,how
  if c is not None and wqb and n.get('op')=='attn.wq_b' and Path(ov.get('file','')).name=='WQBP.json' and abs(c-1987)<0.01:return 1189,how
  return c,how
 tc.node_cycles=nc
 r=tc.build(tc.OUT/'elements',scenario)
 r['rom12_qualification']={'release_adopted':False,'GU_same_origin':gu,'eight_frame_projection':wqb,'fixed_transport_unchanged':True,'wqb_start_boundary':('new spine-go0, old first-element-capture; conservative new prefix retained' if wqb else 'unchanged'), 'shape_limit':('one h9 64-row frame measured; assumes eight parallel frames for512 rows, requires max-geometry producer/consumer stage bench' if wqb else 'existing composition shapes retained')}
 (O/(name+'.json')).write_text(json.dumps(r,indent=1)+'\n')
 summary[name]={wl:{k:r['workloads'][wl][k] for k in ('T_cycles','tok_s')} for wl in ('ar','mtp')}
 print('COMPOSE_ROM12',name,summary[name],flush=True)
(O/'summary.json').write_text(json.dumps(summary,indent=1)+'\n')
# Hash all composition inputs: this report is tied to the actual source/ledger.
files=[R/'tools/toksim_s81_compose.py',tc.BASE,*tc.DAGS.values(),*(tc.OUT/'elements').glob('*.json'),*(tc.OUT/'scenarios/calpipe').glob('*.json')]
(O/'input_sources.json').write_text(json.dumps({str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=1)+'\n')
