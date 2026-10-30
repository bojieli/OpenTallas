"""Delta model of the existing feed chains after explicit PHY-domain relocation; no physical build."""
import json,math,sys,types
from pathlib import Path
R=Path(__file__).parent;sys.path.insert(0,str(R/'tool_snapshot/tools/die_plan'));import die_trial as T
P=json.load(open(R/'input.json'));F=json.load(open(R/'old_feed.json'));E=json.load(open(R/'clock_reset_estimate.json'));C=json.load(open(R/'cal_g03b_refit.json'));N=json.load(open(R/'dme_estimate.json'));O=json.load(open(R/'old_model.json'))
T.load_stage_cal(R/'cal_g03b_refit.json');T.EVEN_LEGS=True;T.DME_ACTUAL_MAX_UM=405.;T.CHAIN_HOP_MAX_UM=405.
parts={p['name']:p for p in P['partitions']}
def price(chain,c):
 d0,k1,k2,kf=C['leg' if c=='TT' else 'leg_FF'];return sum(d0+k1*(abs(a[0]-b[0])+abs(a[1]-b[1]))+k2*(abs(a[0]-b[0])+abs(a[1]-b[1]))**2 for a,b in zip(chain,chain[1:]))
def glob(p,xy):return [p['origin_um'][0]+2885.76-xy[0],p['origin_um'][1]+xy[1]]
answer=[]
for x in [63.64,138.24]:
 domains=[]
 for v in E['variants']:
  if v['phy_guard_um']!=10.8 or v['macro_origin_um'][0]!=x:continue
  p=parts[v['part']];g=v['guard_rect_um'];a,b=glob(p,g[:2]),glob(p,g[2:]);domains.append(dict(nets=['VDDPHY','VSS'],rect_um=[min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])]))
 fake=types.SimpleNamespace(W=40000,H=30000,parts={},types={},die=dict(channels=[dict(rect_um=[0,0,40000,30000])],pg=dict(domains=domains)))
 site=T.SiteMap(fake)
 def place(q):return T.round_legal(site,tuple(q) if site.legal(q) else site.nearest(q))
 shifts={};steps={};cum={c:0 for c in ['TT','FF']};maxhop=0.;rel={}
 for pn in ['lk_ES0','lk_ES1']:
  feed=F[pn]['nodes'];corners={c:dict(old=0.,new=0.) for c in ['TT','FF']};chains=[]
  for n in reversed(feed[:-1]):
   old=n['physical_leg']['chain'];new=[place(q) for q in old]
   with T.leg_parity((len(old)-1)%2):leg=T.physical_leg(site,new[0],new[-1],250.,points=new)
   chains.append(dict(node=n['id'],old_stages=len(old)-1,new_stages=len(leg['chain'])-1,old_wire_um=n['physical_leg']['wire_um'],new_wire_um=leg['wire_um'],endpoint_shift_um=abs(old[-1][0]-new[-1][0])+abs(old[-1][1]-new[-1][1])))
   maxhop=max([maxhop]+[abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(leg['chain'],leg['chain'][1:])])
   for c in ['TT','FF']:corners[c]['old']+=price(old,c);corners[c]['new']+=price(leg['chain'],c)
  for c in corners:
   corners[c]['delta']=corners[c]['new']-corners[c]['old'];cum[c]+=corners[c]['delta'];corners[c]['cumulative_feed_delta']=cum[c]
  model=next(v for v in N['variants'] if v['part']==pn and v['macro_origin_um'][0]==x)
  entry=place([feed[0]['x'],feed[0]['y']]);root=glob(parts[pn],model['root_xy']);leg=T.physical_leg(site,entry,root,250.)
  for c in corners:
   corners[c]['new_feed_to_dme']=price(leg['chain'],c)
   corners[c]['new_region_min']=corners[c]['new_feed_to_dme']+model['corners'][c]['min_ps']
   corners[c]['new_region_max']=corners[c]['new_feed_to_dme']+model['corners'][c]['max_ps']
   corners[c]['endpoint_delta_min']=cum[c]+corners[c]['new_region_min']-O[pn][c]['max']
   corners[c]['endpoint_delta_max']=cum[c]+corners[c]['new_region_max']-O[pn][c]['min']
  steps[pn]=dict(chains=chains,corners=corners,feed_entry_xy=entry,new_dme_root_xy=root)
 answer.append(dict(macro_x_um=x,parts=steps,max_feed_repeater_hop_um=maxhop,build_allowed=False,scope='Shared calibrated nominal-delay delta; unchanged old-clock input prefix before s_7S_x10. No new routed RC/IR or CA proof.'))
json.dump(dict(variants=answer),open(R/'feed_estimate.json','w'),indent=1)
for a in answer:
 for pn,v in a['parts'].items():print(a['macro_x_um'],pn,json.dumps(v['corners']))
