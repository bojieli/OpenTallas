import json,gzip
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=Path(__file__).resolve().parent;i=json.loads(gzip.decompress((P/'inventory.json.gz').read_bytes()));m=json.loads((P/'input/owned_model.json').read_text())
colors={'M1':'#e03e32','M2':'#eea21a','M3':'#36aa7c','M4':'#296ac4','M5':'#a141bc','V1':'black','V2':'#555555','V3':'black','V4':'black'}
fig,axs=plt.subplots(3,2,figsize=(18,14),constrained_layout=True)
for col,(fam,f) in enumerate(i['families'].items()):
 def draw(ax,zoom=None):
  for r in f['conditional_OBS']:
   x,y,X,Y=r['rect_nm'];ax.add_patch(Rectangle((x/1000,y/1000),(X-x)/1000,(Y-y)/1000,facecolor='none',edgecolor='#b6b6b6',linestyle=':',linewidth=.4))
  for r in f['core_exclusions']:
   x,y,X,Y=r['rect_nm'];ax.add_patch(Rectangle((x/1000,y/1000),(X-x)/1000,(Y-y)/1000,facecolor='#ddd',alpha=.45,edgecolor='#888',linewidth=.4,hatch='//'))
  for b in f['actual_boxes']:
   x,y,X,Y=b['rect_nm'];ax.add_patch(Rectangle((x/1000,y/1000),(X-x)/1000,(Y-y)/1000,facecolor=colors[b['layer']],edgecolor='none',alpha=.65 if b['layer'].startswith('M') else 1))
  for p in f['ports']:
   x,y,X,Y=p['rect_nm'];ax.add_patch(Rectangle((x/1000,y/1000),(X-x)/1000,(Y-y)/1000,facecolor='none',edgecolor='red',linewidth=1))
  w,h=f['outline_nm'];ax.add_patch(Rectangle((0,0),w/1000,h/1000,facecolor='none',edgecolor='black',linewidth=1))
  if zoom:ax.set_xlim(zoom[0]/1000,zoom[2]/1000);ax.set_ylim(zoom[1]/1000,zoom[3]/1000)
  else:ax.set_xlim(-.2,w/1000+.2);ax.set_ylim(-.2,h/1000+.2)
  ax.set_aspect('equal');ax.set_xlabel('X (um)');ax.set_ylabel('Y (um)')
 draw(axs[0,col]);axs[0,col].set_title(f"{fam.upper()} entire owned metal: {f['counts']['signal_nets']} signal nets, {f['counts']['supply_rails_and_M1_ports']} supply stacks")
 for row,c in [(1,m['families'][fam]['contact_ledger'][0]),(2,max(m['families'][fam]['contact_ledger'],key=lambda c:c['new_M1_core_port_center_nm'][1]))]:
  x,y=c['new_M1_core_port_center_nm'];trunk=next(p for p in f['ports'] if p['net']==c['net']);tx=trunk['rect_nm'][0]
  draw(axs[row,col],[min(x,tx)-160,y-180,max(x,tx)+160,y+180]);axs[row,col].set_title(c['id']+' complete M1/V1/M2/V2/M3/V3/M4/V4/M5 stack')
fig.suptitle('A4 PREENGINE - exact 5de283aad owned geometry; NO NATIVE ENGINE RUN\nBlue M4, violet M5, red M1, orange M2, green M3, black cuts. Dotted OBS / hatched core exclusions are reservations, never metal.',fontsize=13)
fig.savefig(P/'A4_WHOLE_OWNED_METAL_PREENGINE.png',dpi=150);plt.close(fig)
