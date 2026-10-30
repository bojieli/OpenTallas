import json,sys,copy,subprocess
from pathlib import Path
from types import SimpleNamespace
R=Path(__file__).resolve().parents[3];P=R/'results/hbm_die_codex_1030/su_structural_bridges'
sys.path.insert(0,str(R/'tools/die_plan'));import bind_elab as E,bind as B,structural_bridge as H
abi=json.load(open(P/'native_cut_abi.json'))
def make():
 F=E.Flat();loaded=[]
 for a in abi:
  ports={}
  for n,w in a['ports'].items():
   b=F.new(w);ports[n]=list(range(b,b+w))
  ports['lane_lane_id']=[str((a['ids']['lane_lane_id']['value']>>i)&1)for i in range(a['ports']['lane_lane_id'])]
  F.cells.append(E.Cell(a['path'],a['module'],{},ports,dict(a['port_directions']),'leaf'))
  for n,bs in ports.items():F.top_ports[a['path']+'.'+n]=(a['port_directions'][n],list(bs))
  if'plain4'in a['module']:loaded+=ports['lane_coll']
 F.cells.append(E.Cell('loaded192','consumer',{},dict(D=loaded),dict(D='input'),'leaf'))
 return SimpleNamespace(F=F,extra_lib=[])
manifest=json.load(open(P/'manifest_PREP.json'))['structural_bridges'];results=[]
b=make();top=copy.deepcopy(b.F.top_ports);rr=H.apply(b,manifest,R);G=B.Graph(b.F,B.Rules({}),[]);sink=next(c for c in b.F.cells if c.path=='loaded192');assert len(rr)==48 and all(G.source(n)[:2]==('const','0')for n in sink.ports['D']);assert top==b.F.top_ports and len(b.extra_lib)==3
results.append(dict(case='frozen_actual3fragments_48cuts',pass_=True,constant_loaded_bits=192,physical_RTL_files=3))
for mode in ['wrong_JSON_hash','wrong_source_hash','late_unmatched_path','duplicate_path']:
 b=make();old=b.F;top=copy.deepcopy(old.top_ports);m=copy.deepcopy(manifest)
 if mode=='wrong_JSON_hash':m[0]['json_sha256']='0'*64
 if mode=='wrong_source_hash':m[0]['source_files_sha256'][next(iter(m[0]['source_files_sha256']))]='0'*64
 if mode=='late_unmatched_path':m[-1]['instances'][-1]['path']='missing.actual.native.path'
 if mode=='duplicate_path':m[-1]['instances'][-1]['path']=m[0]['instances'][0]['path']
 try:H.apply(b,m,R)
 except H.StructuralBridgeError as exc:err=str(exc)
 else:raise AssertionError(mode)
 assert b.F is old and old.top_ports==top and b.extra_lib==[] and len(old.cells)==113
 results.append(dict(case=mode,rejected=True,atomic=True,reason=err))
b=make();old=b.F;assert H.apply(b,[],R)==[]and b.F is old
results.append(dict(case='optional_absent',unchanged=True))
(P/'loader_receipt.json').write_text(json.dumps(dict(scope='Actual fragments in exact112ABI constructed context, not fullcurrentnativebind',cases=results),indent=2)+'\n')
print('PASS loader6cases/full48atomic/192loadedconstants')
