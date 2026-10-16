from pathlib import Path
import gzip,json
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path(__file__).parent;j=json.load(gzip.open('/home/ubuntu/artifacts/s81-connected-0305/first_pass_plan_17b.json.gz','rt'));base={i['name']:i for i in j['insts']};fig,axs=plt.subplots(2,3,figsize=(19,11));alts=['A_south_aprons_rd_north','B_east_aprons_rd_south_plus1']
for row,alt in enumerate(alts):
 d=json.load(gzip.open(r/(alt+'.json.gz'),'rt'));homes=d['homes']
 for col,cn in enumerate(['cf10','cf72','cf106']):
  ax=axs[row,col];cf=homes[cn];ri=int(cn[2:]);selected={cn}
  selected.update(n for n in homes if n.startswith(f'f_cx{ri}_'))
  if cn=='cf72':selected.add('f_KW3r_22')
  if cn=='cf106':selected.add('f_KW3r_25')
  edges=[b for b in j['buses'] if b[1] in ['lane','col_ret'] and any(n in selected for n,p in b[3])]
  peers={n for b in edges for n,p in b[3]};allnames=selected|peers
  pts=[homes.get(n,base[n]) for n in allnames if n in base];x0=min(a['x'] for a in pts)-35;x1=max(a['x']+a['w'] for a in pts)+35;y0=min(a['y'] for a in pts)-35;y1=max(a['y']+a['h'] for a in pts)+35
  for n,a0 in base.items():
   a=homes.get(n,a0)
   if a['x']>x1 or a['x']+a['w']<x0 or a['y']>y1 or a['y']+a['h']<y0:continue
   c='#d7d7d7';z=1
   if n==cn:c='#dbe9ff';z=3
   elif n in selected:c='#ffe1ae';z=3
   elif n in peers:c='#d5efda';z=2
   ax.add_patch(Rectangle((a['x'],a['y']),a['w'],a['h'],fc=c,ec='black',lw=.5,zorder=z))
   if n in allnames:ax.text(a['x'],a['y']+a['h']+2,n,fontsize=6,zorder=5)
  for b in edges:
   aa=homes.get(b[3][0][0],base[b[3][0][0]])
   for nn,pp in b[3][1:]:
    bb=homes.get(nn,base[nn]);ax.plot([aa['x']+aa['w']/2,bb['x']+bb['w']/2],[aa['y']+aa['h']/2,bb['y']+bb['h']/2],color='#8b537b',alpha=.6,lw=.7,zorder=4)
  ax.set_xlim(x0,x1);ax.set_ylim(y0,y1);ax.set_aspect('equal');ax.set_title(f'{alt.split("_")[0]}: {cn} connected peer homes');ax.set_xlabel('Die x (um)');ax.set_ylabel('Die y (um)');ax.grid(alpha=.15)
fig.suptitle('Actual first-pass source17b peer graph with candidate homes; not final pins or routed wires',fontsize=15)
fig.text(.04,.015,'Boxes use actual first-pass instance outlines/orientations. Orange: relocated group stations; green: actual incident peers. Lines are graph connectors ONLY, not pin-to-pin routes.\nA:192 collisions/11 outside. B:0 rectangle collisions/outside, but16 incoming lane edges have >500um lower bounds and require structural relay repair. Final cuts/clock/native proof absent.',fontsize=11)
fig.tight_layout(rect=[0,.065,1,.95]);fig.savefig(r/'connected_group_alternatives.png',dpi=140)
