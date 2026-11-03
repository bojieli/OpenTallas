import json,csv
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
O=Path(__file__).resolve().parent;p=json.load(open(O/'pricing_PREP.json'));d=json.load(open(O/'parent_delta_PREP.json'));sites=p['macro_inventory'];pins=json.load(open(O/'candidate_pins_PREP.json'));old=d['old'];new=d['new'];fig,axes=plt.subplots(1,3,figsize=(17,7))
ax=axes[0];ax.add_patch(Rectangle((0,0),2160,1676.16,fill=False,edgecolor='#30383e',lw=1.5));ax.add_patch(Rectangle((216,1045.44),604.8,440.64,facecolor='#bed0db',edgecolor='#587489'));ax.text(518.4,1265.76,'existing AHUB',ha='center',va='center',fontsize=9)
for c,color,style,label in [(old,'#999999','--','old371.52'),(new,'#0b78ae','-','PREP250.56x285.12')]:
 x,y=c['origin_um'];w,h=c['outline_um'];ax.add_patch(Rectangle((x,y),w,h,fill=False,edgecolor=color,lw=2,linestyle=style));ax.text(x,y-35,label,fontsize=8,color=color)
ax.plot(1084.296,324,'*',c='#c33231',ms=8);ax.set(xlim=(0,2160),ylim=(0,1676.16),title='Parent hard-core slots only (soft logic omitted)\nNew child is a strict subset of old slot',xlabel='parent x (um)',ylabel='parent y (um)');ax.set_aspect('equal')
ax=axes[1]
for c,color,style in [(old,'#999999','--'),(new,'#0b78ae','-')]:
 x,y=c['origin_um'];w,h=c['outline_um'];ax.add_patch(Rectangle((x,y),w,h,fill=False,edgecolor=color,lw=2,linestyle=style))
oldcells=list(csv.DictReader(open('/srv/opentallas-scratch/claude/codex-kv-ctl-rowfix-r2-0250/collector/placed.csv')))
for c in oldcells:
 if c['kind']=='macro':ax.add_patch(Rectangle((old['origin_um'][0]+float(c['x']),old['origin_um'][1]+float(c['y'])),float(c['w']),float(c['h']),fill=False,edgecolor='#aaaaaa',linestyle=':',lw=1))
for m in sites:
 x=new['origin_um'][0]+m['x'];y=new['origin_um'][1]+m['y'];ax.add_patch(Rectangle((x,y),m['width'],m['height'],facecolor='#7895ae',edgecolor='#143c5d'));ax.text(x+m['width']/2,y+m['height']/2,m['name'].split('.')[-1],ha='center',fontsize=5.5)
for q in p['parent_clock_reset_global_unchanged']:
 x,y=q['global_unchanged'];ax.plot(x,y,'*',c='#c33231',ms=9)
ax.annotate('GLOBAL ck/rst_n unchanged',(1084.5,324),xytext=(1020,285),arrowprops=dict(arrowstyle='->',color='#c33231'),fontsize=8,color='#a51e1e')
ax.set(xlim=(870,1300),ylim=(110,540),title='Centered child compaction\nParent origin +60.48X/+43.2Y; global roots fixed',xlabel='parent x (um)',ylabel='parent y (um)');ax.set_aspect('equal')
ax=axes[2]
from matplotlib.patches import Polygon
ax.add_patch(Polygon([(125.28-130,142.56),(125.28,142.56+130),(125.28+130,142.56),(125.28,142.56-130)],facecolor='#c9a8dc',edgecolor='#8b579d',alpha=.25,linestyle='--',zorder=0))
for q in pins:
 if q['face']=='interior':continue
 ax.plot(q['x'],q['y'],'.',c='#dd8a16',ms=.8,alpha=.6)
for m in sites:
 x,y,w,h=m['x'],m['y'],m['width'],m['height'];ax.add_patch(Rectangle((x-4.32,y-4.32),w+8.64,h+8.64,fill=False,edgecolor='#59a083',linestyle=':',lw=.8));ax.add_patch(Rectangle((x,y),w,h,facecolor='#7895ae',edgecolor='#143c5d'));ax.text(x+w/2,y+h/2,m['name'].split('.')[-1],ha='center',fontsize=5.5)
ax.add_patch(Rectangle((120.76,138.04),9.04,9.04,facecolor='#e69390',edgecolor='#c33231'));ax.text(125.28,138,'ck/rst bay',ha='center',va='top',fontsize=6,color='#a51e1e')
ax.text(125.28,16,'FF deconcentration/site assignment OPEN\nNo new PLACE or source change',ha='center',fontsize=7,color='#6c3061')
ax.set(xlim=(-8,259),ylim=(-8,294),title='Local250.56x285.12 PREP: same6SRAMs\nConservative4.32halos;6849current pins',xlabel='local x (um)',ylabel='local y (um)');ax.set_aspect('equal')
fig.suptitle('CTL COMPACTION PREP ONLY: native SYNTH logic9589.44um² + fixed SRAM12538.49um² ->16.28%logic-only fill\nM5 ceiling /833ps / current FF masters / cycles unchanged; face peaks W,E9.2,N5.8,S1.7 remain route-access budget',fontsize=11)
fig.tight_layout();fig.savefig(O/'compact250x285_parent_review.png',dpi=160)
