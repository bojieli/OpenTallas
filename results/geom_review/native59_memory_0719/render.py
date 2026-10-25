import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
j=json.load(open(HERE/'native59_type.json'));w,h=j['outline_um']
fig,ax=plt.subplots(figsize=(11,8),dpi=150)
ax.add_patch(Rectangle((0,0),w,h,fill=False,lw=2))
for c in j['contents']:
 if c.get('module')!='ot_sram_1r1w_32x512_m1':continue
 x,y=c['origin_um'];mw,mh=c['outline_um'];i=c['inst'].split('g_writer[')[1].split(']')[0]
 ax.add_patch(Rectangle((x,y),mw,mh,facecolor='#c4d8ed',edgecolor='#31577c'))
 ax.text(x+mw/2,y+mh/2,f'bank {i}\n32 × 512',ha='center',va='center',fontsize=9)
 rd=x+mw if c['orient']=='R0' else x
 ax.plot([rd,rd],[y+3,y+mh-3],color='#d64f27',lw=4)
 ax.annotate('',xy=(388.8,y+mh/2),xytext=(rd,y+mh/2),arrowprops=dict(arrowstyle='->',color='#d64f27'))
for b in j['buses']:
 if 'face' not in b:continue
 lo,hi=b['window_um'];f=b['face'];p=([0,0],[lo,hi]) if f=='W' else ([w,w],[lo,hi]) if f=='E' else ([lo,hi],[0,0]) if f=='S' else ([lo,hi],[h,h])
 ax.plot(*p,color='#269b67' if b['dir']=='in' else '#8d52a5',lw=3)
ax.axvspan(247.4,530,alpha=.08,color='#edab1a');ax.text(388.7,475,'Read mux / logic / clock corridor\n282.6 µm',ha='center',fontsize=10)
ax.scatter([388.8],[259.2],marker='+',s=160,c='black');ax.text(393,265,'clock corridor',fontsize=8)
ax.set(xlim=(-25,w+25),ylim=(-25,h+25),aspect='equal',xlabel='µm',ylabel='µm',title='Native59 existing writer SRAMs: physical view plan\n8 actual synthesized macros, 0 added cycles; PLACEMENT REVIEW ONLY')
ax.grid(alpha=.15);fig.tight_layout();fig.savefig(HERE/'native59_memory_views0719.png')
