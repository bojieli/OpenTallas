"""A/10.8guard dense clock + paired START/reset wave, analytic feasibility only."""
import json,math,sys,types
from pathlib import Path
R=Path(__file__).parent;sys.path.insert(0,str(R/'tool_snapshot/tools/die_plan'));import die_trial as T
P=json.load(open(R/'input.json'));F=json.load(open(R/'old_feed.json'));C=json.load(open(R/'cal_g03b_refit.json'));O=json.load(open(R/'old_model.json'));E=json.load(open(R/'clock_reset_estimate.json'));N=json.load(open(R/'dme_startsafe_estimate.json'));L=json.load(open(R/'start_lib.json'))['corners']
from die_clock_128 import _bilin
T.load_stage_cal(R/'cal_g03b_refit.json');T.EVEN_LEGS=True;T.DME_ACTUAL_MAX_UM=150.;T.CHAIN_HOP_MAX_UM=150.
parts={p['name']:p for p in P['partitions']};tree=json.load(open(R/'tree_startsafe_lk_ES0_63.64.json'));out=tree['out'];root=tree['root'];rootxy=[out[root]['x'],out[root]['y']]
def glob(p,xy):return [p['origin_um'][0]+2885.76-xy[0],p['origin_um'][1]+xy[1]]
domains=[]
for v in E['variants']:
 if v['phy_guard_um']==10.8 and v['macro_origin_um'][0]==63.64:
  a,b=glob(parts[v['part']],v['guard_rect_um'][:2]),glob(parts[v['part']],v['guard_rect_um'][2:]);domains.append(dict(nets=['VDDPHY','VSS'],rect_um=[min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])]))
site=T.SiteMap(types.SimpleNamespace(W=40000,H=30000,parts={},types={},die=dict(channels=[dict(rect_um=[0,0,40000,30000])],pg=dict(domains=domains))))
local=T.SiteMap(types.SimpleNamespace(W=2885.76,H=1226.88,parts={},types={},die=dict(channels=[dict(rect_um=[0,0,2885.76,1226.88])],pg=dict(domains=[dict(nets=['VDDPHY','VSS'],rect_um=[52.84,75.6,2682.92,1021.68])]))))
legs=[];paths=[]
def addleg(a,b,points,sites,label):
 leg=T.physical_leg(sites,tuple(a),tuple(b),150.,points=points);chain=leg['chain'];lens=[abs(x[0]-y[0])+abs(x[1]-y[1]) for x,y in zip(chain,chain[1:])]
 assert len(lens)%2==0,(label,len(lens))
 z=dict(label=label,chain=chain,lens=lens,relay_pairs=len(lens)//2,corners={})
 for c in ['TT','FF']:
  d0,k1,k2,kf=C['leg' if c=='TT' else 'leg_FF'];z['corners'][c]=sum(d0+k1*l+k2*l*l for l in lens)
 legs.append(z);return z
feed_old={c:0 for c in ['TT','FF']};feed_new={c:0 for c in ['TT','FF']};feed_pairs=0;feed_ends={}
overrides={(F[pn]['nodes'][0]['x'],F[pn]['nodes'][0]['y']):glob(parts[pn],rootxy) for pn in parts}
def place(x):
 q=overrides.get(tuple(x),x);return T.round_legal(site,q if site.legal(q) else site.nearest(q))
for pn in ['lk_ES0','lk_ES1']:
 for n in reversed(F[pn]['nodes'][:-1]):
  old=n['physical_leg']['chain'];new=[place(x) for x in old];z=addleg(new[0],new[-1],None,site,'feed_'+str(n['id']));feed_pairs+=z['relay_pairs']
  for c in ['TT','FF']:
   d0,k1,k2,kf=C['leg' if c=='TT' else 'leg_FF'];feed_old[c]+=sum(d0+k1*(abs(a[0]-b[0])+abs(a[1]-b[1]))+k2*(abs(a[0]-b[0])+abs(a[1]-b[1]))**2 for a,b in zip(old,old[1:]));feed_new[c]+=z['corners'][c]
 feed_ends[pn]=dict(pairs=feed_pairs,old=feed_old.copy(),new=feed_new.copy())
localpaths=[]
def visit(i,depth,arrival):
 n=out[i]
 for tap in n['taps']:localpaths.append(dict(tap=tap[1],local_pairs=depth,arrival=arrival.copy()))
 for j in n['kids']:
  m=out[j];pts=n.get('snakes',{}).get(j,n.get('snakes',{}).get(str(j)));z=addleg([n['x'],n['y']],[m['x'],m['y']],([(n['x'],n['y'])]+pts+[(m['x'],m['y'])]) if pts is not None else None,local,'dme_'+str(j))
  visit(j,depth+z['relay_pairs'],{c:arrival[c]+z['corners'][c]+(C['leg' if c=='TT' else 'leg_FF'][3] if len(n['kids'])>1 else 0) for c in ['TT','FF']})
visit(root,0,{c:0 for c in ['TT','FF']})
# Marginal clock load for a standard BUF8 isolation input at each relay node.
loadpen={}
for c in ['TT','FF']:
 lib=L[c]['cells'];ck=lib['CKINVDCx16_ASAP7_75t_R'];extra=lib['BUFx8_ASAP7_75t_R']['cap_ff'];loadpen[c]=max(_bilin(ck['cell_'+p],s,ld+extra)-_bilin(ck['cell_'+p],s,ld) for s in [20,80] for p in ['rise','fall'] for ld in [10,20,40,60])
summary={}
for pn,f in feed_ends.items():
 rows=[]
 for t in localpaths:
  pairs=f['pairs']+t['local_pairs'];a=8+3*pairs;corners={}
  for c in ['TT','FF']:
   delta=f['new'][c]-f['old'][c]+t['arrival'][c]-O[pn][c]['min'];corners[c]=dict(new_region_ps=t['arrival'][c],clock_delta_base_ps=delta,relay_load_upper_ps=(pairs+1)*loadpen[c],clock_delta_upper_ps=delta+(pairs+1)*loadpen[c])
  rows.append(dict(tap=t['tap'],relay_pairs_from_unchanged_b705=pairs,origin_cycles=a,reset_release_cycles_from_b705=2*pairs,reset_lead_cycles_if_rootlead64=64+pairs,corners=corners))
 summary[pn]=dict(rows=rows,origin_min=min(r['origin_cycles'] for r in rows),origin_max=max(r['origin_cycles'] for r in rows),corner_delta_hull={c:[min(r['corners'][c]['clock_delta_base_ps'] for r in rows),max(r['corners'][c]['clock_delta_upper_ps'] for r in rows)] for c in ['TT','FF']})
res=dict(scope='MODEL A PHYx63.64/y86.4 PGguard10.8. True-polarity pairedINV relay everyclockpair from unchanged STARTb705 origin8, clock-only graph roots co-located with denseDME geometricroots. Raw reset co-routed existing3FF relay; START existing4FF landing PAD0 falling. No RTL, plan,physical adoption.',parts=summary,max_individual_clock_hop_um=max(max(z['lens']) for z in legs),unique_relay_pairs=sum(z['relay_pairs'] for z in legs)+sum(z['relay_pairs'] for z in legs if z['label'].startswith('dme_')),clock_extra_load_ps_per_relay=loadpen,legs=legs,build_allowed=False,holds=['relay FF/driver physical site reservation not yet solved','fall-edge clock insertion NLDM endpoint model pending','full affected data CA repricing pending, old roots beyond changedsubgraph must remain fixed','release origin offsets contract must be adopted by owner; rawreset two cycles/hop, START three cycles/hop, so rootresetlead64 grows64+hopcount'])
json.dump(res,open(R/'start_graph_estimate.json','w'),indent=1)
print(json.dumps({k:v for k,v in res.items() if k not in ['legs','parts']}));print(json.dumps({pn:{k:v for k,v in s.items() if k!='rows'} for pn,s in summary.items()}))
