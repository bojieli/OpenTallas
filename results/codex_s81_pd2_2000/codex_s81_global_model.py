import pathlib,sys,json,math
O=pathlib.Path('/srv/opentallas-scratch2/claude/codex-s81-pd2-2000');R=O/'modelsrc';sys.path.insert(0,str(R/'tools/die_plan'))
import schema as S,die_trial as D
f=str(O/'b2_candidate/die_plan_phy_density.json');P=S.Plan(S.load(f),f)
try:
 nodes,segs,legs,meta=D.clock_kit(P,O/'clock_global_model',300,405,full_depth=True,site_slide=True,tap_rep_um=405)
 cache={}
 def path(i):
  if i in cache:return cache[i]
  n=nodes[i];p=n['parent'];v=[0.,1] if p is None else list(path(p))
  if p is not None:
   ll=abs(n['x']-nodes[p]['x'])+abs(n['y']-nodes[p]['y']);v[0]+=ll;v[1]+=max(1,math.ceil(ll/405))
  cache[i]=v;return v
 rows=[]
 for i,n in nodes.items():
  pp=path(i)
  for part,port,x,y in n['taps']:
   leg=abs(x-n['x'])+abs(y-n['y']);rows.append(dict(part=part,tap=port,path_um=pp[0]+leg,stages=pp[1]+max(0,math.ceil(leg/405)-1)))
 result=dict(status='MODEL_ONLY',source='3073aee6c plus PHY --density a1b14e314 and exact-bank schema0765b6c59',base='12a0c04f0',meta=meta,clock_regions='data landing regions retained; clock globalfull-depth, CPPR actualLCA',tap_stages_min=min(x['stages'] for x in rows),tap_stages_max=max(x['stages'] for x in rows),tap_path_min_um=min(x['path_um'] for x in rows),tap_path_max_um=max(x['path_um'] for x in rows))
except Exception as e:result=dict(status='FAIL_PREBUILD',base='12a0c04f0',error=repr(e))
json.dump(result,open(O/'clock_global_model_result.json','w'),indent=1);print(json.dumps(result))
