#!/usr/bin/env python3
import json
from pathlib import Path
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path(__file__).resolve().parent;j=json.loads((R/'contract.json').read_text());c=j['core_um'];h=j['row_height_um'];w=j['family_width_um'];stride=j['stride_rows']
rows=[l.split() for l in (R/'existing_cw_n1_sites.tsv').read_text().splitlines()];cols=defaultdict(list)
for row in rows:cols[float(row[2])].append(row)
reserved=[x['rect_um'] for x in j['reserved_groups']]
def hit(a,b):
 a=[round(x,6) for x in a];b=[round(x,6) for x in b] # remove floating arithmetic noise; model grid is 0.001um
 return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
new=[];boxes=[];skips=0
for x,items in sorted(cols.items()):
 level=0
 for row in sorted(items,key=lambda x:-float(x[3])):
  while True:
   top=c[3]-level*stride*h;box=[x,top-stride*h,x+w,top];level+=1
   if any(hit(box,b) for b in reserved):skips+=1;continue
   assert box[1]>=c[1] and box[0]>=c[0] and box[2]<=c[2]
   new.append({'instance':row[0],'bus':row[4],'x_um':x,'y_um':top-h,'old_y_um':float(row[3]),'family_box_um':box});boxes.append(box);break
assert len(new)==len(rows)==517
assert len({(x['x_um'],round(x['y_um'],6)) for x in new})==517
assert not any(hit(a,b) for i,a in enumerate(boxes) for b in boxes[i+1:])
summary={'cells':len(new),'columns':len(cols),'reserved_groups':j['reserved_groups'],'skipped_family_slots':skips,'family_envelope_area_um2':len(new)*w*stride*h,'min_ff_y_um':min(x['y_um'] for x in new),'max_additional_pin_offset_um':max(x['old_y_um']-x['y_um'] for x in new),'pin_cycles':0,'physical_launched':False}
(R/'candidate_sites.json').write_text(json.dumps({'summary':summary,'sites':new},indent=2));print(json.dumps(summary,indent=2))
fig,ax=plt.subplots(figsize=(12,4),layout='constrained')
ax.scatter([float(r[2]) for r in rows],[float(r[3]) for r in rows],s=8,label='Existing PRE_GLOBAL_PLACE sites')
ax.scatter([x['x_um'] for x in new],[x['y_um'] for x in new],s=8,label='Model: 3-row family slots, forward reservation')
for b in reserved:ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,color='purple',linestyle='--',label='Preserved FSTART typed group rectangle'))
ax.axhline(c[3],color='black',linestyle=':',label='Core north edge')
ax.set(xlabel='x (µm)',ylabel='y (µm)',title='HC1W forward-reservation model — unchanged RTL/pins, PIN CYCLES 0\nFamily envelopes reserve FF plus logic space; no runtime source or physical pilot changed')
ax.legend(loc='lower left',fontsize=8);fig.savefig(R/'model.png',dpi=150)
