import json,sys
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection,PatchCollection
from matplotlib.patches import Rectangle
Q=Path("/srv/opentallas-scratch2/claude/die-qc20-1028");R=Path('/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028')
p=json.load(open(R/'../die-qc16-1028/ev/qc_k2b_p12_a0early.json'));j=json.load(open(Q/'trial13b/clock/tree.json'))
sys.path.insert(0,str(R/'source_tree/tools/die_plan'));import schema
P=schema.Plan(p);rects=[]
for name,pt in P.parts.items():
  for h in P.types[pt['type']].get('hard_cores',[]):
    x,y=h['origin_um'];w,hh=h['outline_um'];dx,dy=h.get('track_offset_um',[0,0]);a=P.to_die(name,(x+dx,y+dy));b=P.to_die(name,(x+dx+w,y+dy+hh))
    rects.append(Rectangle((min(a[0],b[0]),min(a[1],b[1])),abs(b[0]-a[0]),abs(b[1]-a[1])))
feeds=[];local=[];early=[];snk=[]
ek={(r['part'],r['port']) for v in j['meta']['site_legal']['balance']['region_dme'].values() for r in v.get('early_taps',[])}
for n in j['nodes'].values():
  if n['parent'] is None:continue
  a=j['nodes'][str(n['parent'])]
  seg=n.get("detour") or n.get("route") or [(a['x'],a['y']),(n['x'],a['y']),(n['x'],n['y'])]
  if n.get('snake'): seg=[q for a_,b_ in zip(seg,seg[1:]) for q in (a_,(b_[0],a_[1]),b_)]
  (snk if n.get('snake') else feeds if n.get('feed') else local).append(seg)
et=[t for t in j['taps'] if (t['part'],t['tap']) in ek]
for tag,lim in [("die",None),("E2arms",(21000,24200,0,26266)),("W5coll",(0,4000,0,14000))]:
  fig,ax=plt.subplots(figsize=(14,12));ax.add_collection(PatchCollection(rects,facecolor='#b8b8b8',edgecolor='#666',linewidth=.12))
  ax.add_collection(LineCollection(local,colors='#1d80aa',linewidth=.28 if not lim else .8));ax.add_collection(LineCollection(snk,colors='#1a9e3a',linewidth=1.6));ax.add_collection(LineCollection(feeds,colors='#bc3434',linewidth=.5 if not lim else 1.2))
  ax.scatter([t['xy'][0] for t in j['taps']],[t['xy'][1] for t in j['taps']],s=.4 if not lim else 8,color='#ef931c')
  ax.scatter([t['xy'][0] for t in et],[t['xy'][1] for t in et],s=3 if not lim else 40,color='#7a2bd1',marker='*')
  ax.autoscale();ax.set_aspect('equal');ax.set_title('QC trial13b (rt2 ladder feed): grey hard cores, blue local (DME in c_*/su_c), red feeds, orange taps, purple * early core taps, GREEN = plan-computed DME elongation (snake) legs')
  if lim:ax.set_xlim(lim[:2]);ax.set_ylim(lim[2:])
  fig.savefig(Q/('trial13b_plan_'+tag+'.png'),dpi=110,bbox_inches='tight');plt.close(fig)
print('rendered',len(rects),len(feeds),len(local),len(et))
