import json,sys
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R.parents[1]/'tools/die_plan'))
import schema as S,gen_phys as G
types=sys.argv[1].split(',') if len(sys.argv)>1 else ['kv3_hgi_v5','kv3_hgi_v7','kv3_hgi_v8']
plan=sys.argv[2] if len(sys.argv)>2 else 'hm_r26q6_hgi128.json'
output=sys.argv[3] if len(sys.argv)>3 else 'hgi128_review.png'
P=S.Plan(S.load(R/'pd'/plan))
fig,axes=plt.subplots(1,len(types),figsize=(6*len(types),9),squeeze=False)
for ax,tn in zip(axes.flat,types):
 t=P.types[tn];w,h=t['outline_um'];pins={(n,b):(x,y) for n,b,l,x,y,f in G.type_pins(P,tn)}
 for c in t.get('hard_cores',[]):
  x,y=c['origin_um'];cw,ch=c['outline_um'];ax.add_patch(Rectangle((x,y),cw,ch,facecolor='.86',edgecolor='.5',lw=.4))
 for i,s in enumerate(t['ft_slots']):
  col=plt.cm.tab20(i%20);width=s['width']+1
  try:a=np.array([pins[(s['name']+'_i',b)] for b in range(width)]);z=np.array([pins[(s['name']+'_o',b)] for b in range(width)])
  except KeyError:continue
  chains=[a]+[np.asarray(q)+np.array(s.get('bit_site_cell_um',[1.404,.27]))/2 for q in s.get('bit_sites_um',[])]+[z]
  centres=np.array([q.mean(axis=0) for q in chains]);ax.plot(centres[:,0],centres[:,1],'-',color=col,lw=.5,alpha=.6)
  for q in chains[1:-1]:ax.scatter(q[::max(1,len(q)//50),0],q[::max(1,len(q)//50),1],s=1,color=[col])
  if width>500:
   ax.plot(a[:,0],a[:,1],color=col,lw=3);ax.annotate(s['name'],centres[len(centres)//2],fontsize=7)
 ax.set_xlim(-10,w+10);ax.set_ylim(-10,h+10);ax.set_aspect('equal');ax.set_title(tn+' q6 128um entry / planned FT sites');ax.grid(alpha=.1)
fig.tight_layout();fig.savefig(R/output,dpi=130)
if len(sys.argv)>1:sys.exit(0)
P=S.Plan(S.load(R/'pd/hm_r26q6_windows.json'));tn='kv3_sys_c';t=P.types[tn];fig,ax=plt.subplots(figsize=(12,6))
for c in list(t.get('hard_cores',[]))+[x for x in t.get('contents',[]) if x.get('lef')]:
 x,y=c['origin_um'];w,h=c['outline_um'];ax.add_patch(Rectangle((x,y),w,h,fc='.85',ec='.4'))
for n,x,y in S.tap_grid(P,tn):ax.plot(x,y,'ro',ms=4);ax.text(x+8,y+8,n,fontsize=7)
ax.set_xlim(0,t['outline_um'][0]);ax.set_ylim(0,t['outline_um'][1]);ax.set_aspect('equal');ax.set_title('sys_c q6: 18 structured taps, keepouts pruned / recentered');fig.tight_layout();fig.savefig(R/'sys_c_taps_review.png',dpi=130)
