import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1])/'tools/die_plan'))
import schema as S
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
old=S.Plan(json.load(open(sys.argv[2])));new=S.Plan(json.load(open(sys.argv[3])))
fig,axs=plt.subplots(2,2,figsize=(15,7),layout='constrained')
for row,(lab,p) in enumerate([('Frozen source',old),('Private B2 candidate',new)]):
 for col,n in enumerate(['lk_ES0','lk_ES1']):
  ax=axs[row,col];tx,ty,x1,y1=p.rect(n);w=x1-tx;h=y1-ty;t=p.ptype(n)
  ax.add_patch(Rectangle((0,0),w,h,fc='#f5f5f5',ec='black'))
  for c in t.get('contents',[]):
   if 'origin_um' not in c or 'outline_um' not in c:continue
   a=p.to_die(n,c['origin_um']);b=p.to_die(n,[c['origin_um'][i]+c['outline_um'][i] for i in range(2)])
   x,y=min(a[0],b[0])-tx,min(a[1],b[1])-ty;cw,ch=abs(a[0]-b[0]),abs(a[1]-b[1]);ax.add_patch(Rectangle((x,y),cw,ch,fc='#97c8ea',ec='#3877a2',alpha=.7));ax.text(x+cw/2,y+ch/2,c['inst'],ha='center')
  for z in p.die['pg']['domains']:
   if z['name']=='phy_'+n:
    a,b,c,d=z['rect_um'];ax.add_patch(Rectangle((a-tx,b-ty),c-a,d-b,fill=False,ec='#3b9948',lw=2,ls='--'))
  for pr in p.ports.values():
   if not any(pr[s]['part']==n for s in ('src','dst')):continue
   for side in ('src','dst'):
    if pr[side]['part']!=n:continue
    try:g=p.port_geom_from(pr,side)
    except Exception:continue
    if not g:continue
    face,win,_,order=g
    if side=='dst':face=S.OPP[face]
    color='#b92323' if 'coll' in pr['id'] else '#8463a9'
    if face in 'EW':x=0 if face=='W' else w;ax.plot([x,x],[win[0]-ty,win[1]-ty],c=color,lw=2)
  for slot in t.get('ft_slots',[]):
   for pt in slot.get('regs_um',[])[1:]:
    x,y=p.to_die(n,pt);ax.scatter(x-tx,y-ty,c='#d88422',s=6)
  for tap in t.get('clock',{}).get('taps',[]):
   x,y=p.to_die(n,tap['xy']);ax.scatter(x-tx,y-ty,marker='*',s=30,c='#167e78')
  ax.axhline(-ty,c='black',lw=1);ax.set_xlim(-50,w+50);ax.set_ylim(-ty-20,h+30);ax.set_aspect('equal');ax.set_title(f'{lab}: {n} {p.orient(n)}');ax.set_xlabel('Local die x (um)');ax.set_ylabel('Height above partition origin (um)');ax.grid(alpha=.15)
fig.suptitle('S81 south-edge PHY: blue actual typed macro, green PHY PG domain, red collective windows, orange FT stations\nB2: shoreline 406.08 -> 103.68 um; source data/cycles unchanged; clock and physical gates pending')
fig.savefig(sys.argv[4],dpi=140)
