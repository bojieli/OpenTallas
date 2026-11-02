import json,re
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path(__file__).parent
fig,ax=plt.subplots(figsize=(10,13))
ax.add_patch(Rectangle((0,0),1036.8,1520.64,fill=False,lw=2))
colors=['#dbeafe','#dcfce7','#fef3c7','#f3e8ff']
for i,(x,y) in enumerate([(86.4,198.72),(552.96,198.72),(552.96,959.04),(86.4,959.04)]):
 ax.add_patch(Rectangle((x,y),397.44,362.88,facecolor=colors[i],edgecolor='#555',ls='--'))
 ax.text(x+198.72,y+310,f'PC{i}: soft GPL guide',ha='center',fontsize=9)
for m in re.finditer(r'g_pc\\\[(\d)\\\].*?-location \{([\d.]+) ([\d.]+)\} -orientation (\w+)',(p/'macro_place.tcl').read_text()):
 i,x,y,o=m.groups();x=float(x);y=float(y)
 ax.add_patch(Rectangle((x,y),94.824,41.064,facecolor='#2563eb',edgecolor='black'))
 ax.text(x+47.412,y+50,f'SRAM{i} {o}',ha='center',fontsize=8)
# Every actual generated driver-island rectangle, no inferred clock islands.
s=(p/'die_islands.tcl').read_text()
pat=r'set di_x0 \[expr \{round\(([\d.]+)\*\$di_u\)\}\]; set di_y0 \[expr \{round\(([\d.]+)\*\$di_u\)\}\]\nset di_x1 \[expr \{round\(([\d.]+)\*\$di_u\)\}\]; set di_y1 \[expr \{round\(([\d.]+)\*\$di_u\)\}\]'
rects=[]
for m in re.finditer(pat,s):
 x,y,a,b=map(float,m.groups());rects.append([x,y,a,b]);ax.add_patch(Rectangle((x,y),a-x,b-y,facecolor='#dc2626',alpha=.5))
pins=json.load(open(p/'pins.json'))
ax.scatter([v['x'] for v in pins],[v['y'] for v in pins],s=.3,c='#64748b',alpha=.15)
clks=[v for v in pins if v['bus'].startswith('clk')]
ax.scatter([v['x'] for v in clks],[v['y'] for v in clks],marker='+',s=50,c='#dc2626',label='clock tap pins (when present in pins.json)')
rel=json.load(open('/home/ubuntu/coord/tmp/codex-pickup-kv/hhp/relay_sites.json'))
for n,(x,y) in rel.items():
 ax.scatter([x],[y],s=25,c='#059669');ax.annotate(n.split('/')[-1],(x,y),xytext=(5,4),textcoords='offset points',fontsize=7)
ax.set_aspect('equal');ax.set_xlim(-25,1062);ax.set_ylim(-25,1546);ax.set_xlabel('um');ax.set_ylabel('um');ax.legend(loc='upper right',fontsize=8)
ax.set_title('HHP corrected actual KIT: four SRAMs + soft PC lot guides\nRetained synthesis; PLACE only. Dashed lots are guides, not hard cores.')
fig.tight_layout();fig.savefig(p/'actual_corrected_layout.png',dpi=160)
json.dump({'sram_count':4,'actual_clock_island_rectangles':len(rects),'pin_count':len(pins),'clock_pins':len(clks),'relay_sites':rel},open(p/'render_inputs.json','w'),indent=2)
print('clock rectangles',len(rects),'clock pins',len(clks))
