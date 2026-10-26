import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
HERE=Path(__file__).resolve().parent
c=json.loads((HERE/'source_child_slots.json').read_text())
ss=[s for s in c['slots'] if s['name'].startswith('sp_hc_s/comb/')]
fig,axs=plt.subplots(1,2,figsize=(13,9),constrained_layout=True)
for ax,new in zip(axs,[False,True]):
 for s in ss:
  x,y=s['origin']['x']-619.92,s['origin']['y']-7408.8
  w,h=s['outline']['w'],s['outline']['h'];name=s['name'].split('comb/')[1]
  color='lightgray'
  if s.get('kit')=='s81hc_ccrh2_ref':color='tomato';h=190.08 if new else h
  if s.get('kit')=='s81hc_cseqh2_ref':color='gold';w=h=190.08 if new else h
  if s.get('kit')=='s81hc_caq_ref':color='skyblue';w=h=114.48 if new else h
  ax.add_patch(Rectangle((x,y),w,h,edgecolor='black',facecolor=color,alpha=.8))
  ax.text(x+w/2,y+h/2,name.replace('u_pd.','').replace('u_cr.',''),ha='center',va='center',fontsize=6.5)
 pw,ph=(580.312,851.04) if new else (575.992,816.48)
 ax.add_patch(Rectangle((0,0),pw,ph,edgecolor='purple',fill=False,lw=2,linestyle='--'))
 ax.set(xlim=(-8,600),ylim=(-12,875),xlabel='Local comb X (um)',ylabel='Local comb Y (um)',aspect='equal')
 ax.set_title(('Granted candidate' if new else 'Published v19 child outlines')+f'\nparent {pw:g} x {ph:g} um',fontsize=10)
 ax.grid(alpha=.15)
fig.suptitle('S81 HC3 shoreline enlargement: fixed origins and pin faces, 0 added cycles\nGrant 6e712a1ab: leaf routing allowed; parent pins/cuts/incident hops remain unqualified',fontsize=12)
p=HERE/'shoreline_source_geometry.png';fig.savefig(p,dpi=160)
