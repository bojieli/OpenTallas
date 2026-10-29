import json
import re
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

root = Path(__file__).resolve().parent
kits = sorted(p for p in (root/'core_plans').iterdir() if (p/'freeze.json').exists())
fig, axes = plt.subplots(2,3,figsize=(15,10))
for ax,k in zip(axes.flat,kits):
    freeze=json.loads((k/'freeze.json').read_text())
    w,h=freeze['outline_um'];pins=json.loads((k/'pins.json').read_text())
    ax.add_patch(Rectangle((0,0),w,h,fill=False,lw=2))
    for p in pins:
        name=p.get('bus',p.get('name','')); color='darkorange' if name.split('[')[0] in ('clk','ck') else 'red' if 'rst' in name else 'royalblue'
        ax.plot(p['x'],p['y'],'.',color=color,ms=3)
        if color!='royalblue':ax.annotate(name,(p['x'],p['y']),xytext=(5,8),textcoords='offset points',fontsize=8,color=color)
    mp=k/'macro_place.tcl'
    if mp.exists():
        text=mp.read_text()
        for master,x,y,orient in re.findall(r'(\w+)\s+\{\{([\d.]+) ([\d.]+) (\w+)\}',text):
            files=list((k/'macros').glob(master+'*.lef'))
            if not files:continue
            size=re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',files[0].read_text())
            if size:
                mw,mh=map(float,size.groups());ax.add_patch(Rectangle((float(x),float(y)),mw,mh,color='grey',alpha=.4));ax.text(float(x)+mw/2,float(y)+mh/2,'SRAM\n'+orient,ha='center',va='center',fontsize=8)
    ax.set_title(f"{freeze['module']}\n{w:g} × {h:g} µm, {len(pins)} pins")
    ax.set_xlim(-8,w+8);ax.set_ylim(-8,h+8);ax.set_aspect('equal');ax.grid(alpha=.2)
fig.suptitle('S81 six core plans: declared data pins (blue), clock (orange), reset (red)\nPlacement trial only; actual placed geometry/clock/PG remain to be reviewed')
fig.tight_layout();fig.savefig(root/'core_plan_review.png',dpi=160)
