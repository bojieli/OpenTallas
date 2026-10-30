import json,re
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
b=Path(__file__).parent;d=json.load(open(b/'turn_b_generated_geometry.json'));c=d['type']['clock'];r=[float(x) for x in re.search(r'export DIE_AREA = (.*)',d['config']).group(1).split()]
f,a=plt.subplots(figsize=(5,11));a.set(xlim=(-12,r[2]+12),ylim=(-12,r[3]+12),aspect='equal',xlabel='um',ylabel='um',title='hd_turn_b actual generated kit; N band fill_axis=x')
a.add_patch(Rectangle((0,0),r[2],r[3],fill=False,ec='k'));p=d['pins'];a.scatter([q['x'] for q in p],[q['y'] for q in p],s=2,c='grey')
for key,row in c['landing_contract']['bands'].items():
 x,y,x1,y1=row['rect_um'];a.add_patch(Rectangle((x,y),x1-x,y1-y,fc='lightblue',ec='blue',alpha=.5));a.text(x,y-12,key+' columns scan y then x',fontsize=6)
for q in c['landing_contract']['pins']:
 if q['kind']=='clock' or 'fstart' in q['name'] or 'tstart' in q['name']:
  a.scatter(*q['xy_um'],s=18,c='green');a.annotate(q['name'],q['xy_um'],fontsize=5)
a.scatter(*c['tap_um'],c='brown',marker='*',s=80,label='core entry');a.scatter(*c['start_capture_um'],c='purple',s=22,label='START capture');a.grid(alpha=.15);a.legend(fontsize=6,loc='center right');f.tight_layout();f.savefig(b/'turn_b_generated_geometry.png',dpi=140)
