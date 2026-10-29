from pathlib import Path
import json,re,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path(__file__).parent;p=json.load(open(r.parent/'leaf_profiles.json'))
models=[]
for role,w,h in [('ep',328.32,362.88),('credit',112.32,207.36)]:
 macros=[]
 if role=='ep':
  cols=[17.28,64.8,112.32,181.44,228.96,276.48]
  for m in p['ep']['macro_inventory']:
   bank,depth=map(int,re.search(r'g_bank\[(\d+)\].g_depth\[(\d+)\]',m['inst']).groups())
   col=bank//3+(0 if 'g_fifo' in m['inst'] else 3);row=(bank%3)*2+depth
   macros.append(dict(inst='u_ep.'+m['inst'],module=m['module'],origin_um=[cols[col],round(17.28+56.16*row,4)],orient='MY' if col<3 else 'R0',size_um=[34.584,41.352]))
 else:
  for bank,m in enumerate(p['ingress']['macro_inventory']):
   col=bank//5;row=bank%5
   macros.append(dict(inst='u_ski.'+m['inst'],module=m['module'],origin_um=[17.28+47.52*col,round(17.28+34.56*row,4)],orient='MY' if col==0 else 'R0',size_um=[31.992,17.304]))
 model=dict(module=f'ot_s81hd_{role}_native',outline_um=[w,h],macro_placement=macros,core_margin_um=4.32,macro_halo_um=4.32,clock_root_um=[w/2,h/2],status='PREP HOLD: boundary register assignment, channel census, clock taps and parent composition required; no P&R/STA',whole_outline_reach_bound_um=w+h-17.28)
 assert all(x['origin_um'][0]>=8.64 and x['origin_um'][1]>=8.64 and x['origin_um'][0]+x['size_um'][0]<=w-8.64 and x['origin_um'][1]+x['size_um'][1]<=h-8.64 for x in macros)
 for i,a in enumerate(macros):
  for b in macros[i+1:]:
   ax,ay=a['origin_um'];aw,ah=a['size_um'];bx,by=b['origin_um'];bw,bh=b['size_um']
   assert ax+aw+8.64<=bx or bx+bw+8.64<=ax or ay+ah+8.64<=by or by+bh+8.64<=ay
 (r/f'{role}_model.json').write_text(json.dumps(model,indent=1)+'\n');models.append(model)
fig,axs=plt.subplots(1,2,figsize=(12,8))
for ax,m in zip(axs,models):
 w,h=m['outline_um'];ax.add_patch(Rectangle((0,0),w,h,fill=False,lw=2))
 for x in m['macro_placement']:
  a,b=x['origin_um'];cw,ch=x['size_um'];ax.add_patch(Rectangle((a-4.32,b-4.32),cw+8.64,ch+8.64,facecolor='#eee',edgecolor='#bbb'));ax.add_patch(Rectangle((a,b),cw,ch,facecolor='#adc7dd',edgecolor='#345'));ax.text(a+cw/2,b+ch/2,x['inst'].split('g_bank[')[1].split(']')[0]+('F' if 'fifo' in x['inst'] else ''),ha='center',va='center',fontsize=7)
 pf=r/(('ep' if 'ep_native' in m['module'] else 'credit')+'_pins.json')
 if pf.exists():
  pins=json.load(open(pf))
  for lay,col in [('M4','#a44'),('M5','#8822aa'),('M6','#e4a300')]:
   ps=[p for p in pins if p['layer']==lay];ax.scatter([p['x'] for p in ps],[p['y'] for p in ps],s=2,c=col)
 ax.plot(*m['clock_root_um'],'r+',ms=12);ax.set_aspect('equal');ax.set_xlim(-8,w+8);ax.set_ylim(-8,h+8);ax.set_title(f"{m['module']}\n{w} × {h} µm, {len(m['macro_placement'])} SRAMs");ax.set_xlabel('µm');ax.set_ylabel('µm')
fig.suptitle('Native HEAD cut geometry PREP: SRAM halos clear; no route admission\nEP requires exact dataflow reach and channel model; credit is pin limited; clock taps/register bands pending');fig.tight_layout();fig.savefig(r/'native_geometry.png',dpi=140)
