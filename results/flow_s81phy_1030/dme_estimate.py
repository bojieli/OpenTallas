"""Shared S81 cal-g03 regional DME model only, no P&R or plan mutation."""
import json,sys,types,math
from pathlib import Path
R=Path(__file__).parent;sys.path.insert(0,str(R/'tool_snapshot/tools/die_plan'))
import die_trial as T
P=json.load(open(R/'input.json'));OLD=json.load(open(R/'old_regional.json'));E=json.load(open(R/'clock_reset_estimate.json'));C=json.load(open(R/'cal_g03b_refit.json'))
T.load_stage_cal(R/'cal_g03b_refit.json');T.EVEN_LEGS=True;T.DME_ACTUAL_MAX_UM=405.;T.CHAIN_HOP_MAX_UM=405.

def evaluate(out,root,site,corner):
 coef=C['leg' if corner=='TT' else 'leg_FF'];tc=C['tap' if corner=='TT' else 'tap_FF'];d0,k1,k2,kf=coef
 paths=[];maxhop=0.;bad=0;nn=0
 def visit(i,arrival):
  nonlocal maxhop,bad,nn
  n=out[i];nn+=1
  for tp in n['taps']:
   dist=abs(n['x']-tp[2])+abs(n['y']-tp[3]);paths.append(arrival+tc[0]*dist+tc[1]*dist*dist)
  for j in n['kids']:
   m=out[j];pts=n.get('snakes',{}).get(j,n.get('snakes',{}).get(str(j)))
   leg=T.physical_leg(site,(n['x'],n['y']),(m['x'],m['y']),250.,points=([(n['x'],n['y'])]+pts+[(m['x'],m['y'])]) if pts is not None else None)
   lens=[abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(leg['chain'],leg['chain'][1:])]
   maxhop=max([maxhop]+lens);bad+=sum(not site.legal(p) for p in leg['chain'])
   delay=sum(d0+k1*l+k2*l*l for l in lens)+(kf if len(n['kids'])>1 else 0)
   visit(j,arrival+delay)
 visit(root,0.)
 return dict(min_ps=min(paths),max_ps=max(paths),mean_ps=sum(paths)/len(paths),window_ps=max(paths)-min(paths),sinks=len(paths),nodes=nn,max_hop_um=maxhop,illegal_chain_points=bad)

res=[]
for v in E['variants']:
 if v['phy_guard_um']!=10.8:continue
 pn=v['part'];part=next(p for p in P['partitions'] if p['name']==pn);ty=P['partition_types'][part['type']];w,h=ty['outline_um'];g=v['guard_rect_um']
 # Local R0 frame: geometry is invariant under the part's MY reflection.
 p=types.SimpleNamespace(W=w,H=h,parts={pn:dict(type=part['type'],origin_um=[0.,0.])},types={part['type']:dict(outline_um=[w,h])},die=dict(pg=dict(domains=[dict(nets=['VDDPHY','VSS'],rect_um=g)])),to_die=lambda n,xy:xy)
 site=T.SiteMap(p);taps=[(pn,('clk' if r['tap']=='rst_n_t0' else r['tap'].replace('rst_n','clk')),r['new_xy'][0],r['new_xy'][1]) for r in v['tap_map'] if r['tap']!='rst_n_t32']
 cache=R/f'tree_{pn}_{v["macro_origin_um"][0]}.json'
 if cache.exists():
  saved=json.load(open(cache));out,root=saved['out'],saved['root'];st=dict(reused_geometry=True)
 else:
  out,root,st=T.dme_region_tree(site,taps,rep_um=250.,delay_rep_um=250.,snake=True,early_mode='merge')
  json.dump(dict(out=out,root=root),open(cache,'w'))
 row=dict(part=pn,macro_origin_um=v['macro_origin_um'],guard_um=10.8,root_xy=[out[root]['x'],out[root]['y']],stats=st,corners={c:evaluate(out,root,site,c) for c in ['TT','FF']},build_allowed=False)
 res.append(row);json.dump(dict(stage_model='cal_g03b_refit existing routed-stage model; regional geometry estimate only',variants=res),open(R/'dme_estimate.json','w'),indent=1);print(json.dumps(row),flush=True)
