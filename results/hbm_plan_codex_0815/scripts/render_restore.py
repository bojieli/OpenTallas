import json,sys,pathlib,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
b=pathlib.Path(sys.argv[1]);d=json.loads((b/'base/die_plan.json').read_text());r=json.loads((b/'restore_native_probe.json').read_text());fig,axs=plt.subplots(2,1,figsize=(20,20));colors=['#2b83ba','#abdda4','#fdae61','#d7191c']
for ax,tn in zip(axs,['q_hub_nw','q_hub_ne']):
 t=d['partition_types'][tn];w,h=t['outline_um']
 for c in t['hard_cores']:
  if 'keybuf' in c['module']:continue
  x,y=c['origin_um'];cw,ch=c['outline_um'];is_svg=c['inst'].startswith('u_svg_');ax.add_patch(Rectangle((x,y),cw,ch,fc='#b7b7b7' if not is_svg else '#8571b1',ec='white',lw=.4))
  if is_svg:ax.text(x+cw/2,y+ch/2,c['inst'],ha='center',va='center',fontsize=8)
 for c in t.get('contents',[]):
  if 'keybuf' not in c['inst'] and 'origin_um' in c and 'outline_um' in c:
   x,y=c['origin_um'];cw,ch=c['outline_um'];ax.add_patch(Rectangle((x,y),cw,ch,fc='none',ec='#888888',lw=.4))
 lines={p['pc']:p for p in r[tn]['placements'] if p['kind']=='keybuf'}
 for p in r[tn]['placements']:
  x,y=p['origin_um'];cw,ch=p['outline_um'];col=colors[p.get('pc',0)];ax.add_patch(Rectangle((x,y),cw,ch,fc=col if p['kind']=='hcol' else '#ffe400',ec='black',lw=.4))
  if p['kind']=='keybuf':ax.text(x+cw/2,y+ch/2,f"KB{p['pc']}",ha='center',fontsize=8)
  if p['kind']=='hcol':
   k=lines[p['pc']];tx,ty=k['origin_um'];kw,kh=k['outline_um'];ax.plot([tx+kw/2,x+cw/2],[ty+kh/2,y+ch/2],color=col,lw=.5,alpha=.22)
 ax.set(xlim=(0,w),ylim=(0,h),aspect='equal',title=f'{tn}: native restore lot probe, 4 key lines +64 half-columns +2 tails; old stations to be re-sited');ax.grid(alpha=.1)
fig.suptitle('MODEL ONLY: exact native graph / station hops / channels / reset / clock / PG remain open',fontsize=15);fig.tight_layout();fig.savefig(b/'native_restore_lots.png',dpi=130)
