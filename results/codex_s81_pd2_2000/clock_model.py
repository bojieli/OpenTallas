import pathlib,sys,json,time
O=pathlib.Path('/srv/opentallas-scratch2/claude/codex-s81-pd2-2000');R=O/'modelsrc';sys.path.insert(0,str(R/'tools/die_plan'))
import schema as S,die_trial as D
base=pathlib.Path('/srv/opentallas-scratch2/claude/wt/codex-s81-pd2-2000')
for f in (O/'lef_refs.txt').read_text().splitlines():
 src=base/f; dst=R/f
 if src.is_file():dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(src.read_bytes())
f='/srv/opentallas-scratch2/claude/path-s81-taps-1026/src/physical/die_plan/s81/die_plan_phyfit_g0fix.json';P=S.Plan(S.load(f),f);reg=json.load(open(O/'regions/regions.json'))['part_region']
# Model-only legality and root path census. No OpenROAD, routing or STA.
try:
 nodes,segs,legs,meta=D.clock_kit(P,O/'clock_model',300,405,full_depth=True,site_slide=True,regions=reg,tap_rep_um=405)
 paths={};levels={}
 def walk(i):
  if i in paths:return paths[i]
  n=nodes[i];p=n['parent']
  paths[i]=0 if p is None else walk(p)+abs(n['x']-nodes[p]['x'])+abs(n['y']-nodes[p]['y'])
  levels[i]=0 if p is None else levels[p]+1
  return paths[i]
 for i in nodes:walk(i)
 roots=[dict(region=n['region_root'],path_um=paths[i],levels=levels[i],xy=[n['x'],n['y']]) for i,n in nodes.items() if 'region_root' in n]
 result=dict(status='MODEL_ONLY',source='60e920f87',meta=meta,roots=roots,root_path_spread_um=max(r['path_um'] for r in roots)-min(r['path_um'] for r in roots),root_level_min=min(r['levels'] for r in roots),root_level_max=max(r['levels'] for r in roots))
except Exception as e:
 result=dict(status='FAIL_PREBUILD',source='60e920f87',error=repr(e))
json.dump(result,open(O/'clock_model_result.json','w'),indent=1);print(json.dumps({k:v for k,v in result.items() if k!='roots'}))
