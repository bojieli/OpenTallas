import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
s=json.load(open('body_plan.json'));fig,ax=plt.subplots(figsize=(10,10));W,H=s['outline_um'];ax.add_patch(Rectangle((0,0),W,H,fill=False,color='black'))
for name,(x0,y0,x1,y1) in s['regions_um'].items():
 ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor='#d7eeda',edgecolor='#5a9661',hatch='///',lw=.4))
 if name=='body':ax.text((x0+x1)/2,(y0+y1)/2,'BODY ROW RESERVATION\n22,534.848 um² actual sites\nNo placed-cell occupancy claim',ha='center',va='center',fontsize=10)
for j,m in enumerate(s['macros']):
 x0,y0,x1,y1=m['box_um'];ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor='#bad2ef',edgecolor='navy'))
 ax.text((x0+x1)/2,(y0+y1)/2,f'{"map" if j<3 else "dispatch"}\nbank{j%3}\n51.408 ×39.96',ha='center',va='center',fontsize=8)
for name,t in s['native_bterms'].items():
 if name=='ck_core':continue
 for _,x0,y0,x1,y1 in t['boxes']:
  if name in ('VDD','VSS'):continue
  ax.plot([(x0+x1)/2000],[(y0+y1)/2000],marker='.',color='#4d4d4d',markersize=1)
clock=s['clock_pin_move']['new']['boxes'][0];cx=(clock[1]+clock[3])/2000;cy=(clock[2]+clock[4])/2000
ax.annotate('proposed ck_core\nM5 x151.116',xy=(cx,cy),xytext=(cx,cy+23),ha='center',arrowprops={'arrowstyle':'->','color':'crimson'},color='crimson')
ax.text(W/2,110,'Routing / PG access space\nNot standard-cell body rows\nExternal SRAM patch / via / DRC OPEN',ha='center',fontsize=10)
ax.set(xlim=(-12,W+12),ylim=(-18,H+47),aspect='equal',xlabel='X (um)',ylabel='Y (um)',title='KV ORDER S2: actual native macro / pin and pruned-row diagnostic\n302.4 ×267.84 um — 46.71% raw mapped area / retained sites')
fig.text(.5,.015,'No placement, tap / PG regeneration, routed reach, native TT / FF clock, CTS, parent fit or physical qualification.',ha='center',fontsize=9)
fig.tight_layout(rect=[0,.03,1,.98]);fig.savefig('body_plan.png',dpi=160);fig.savefig('body_plan.svg')
