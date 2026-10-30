import json,re
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
b=Path(__file__).parent;d=json.load(open(b/'st_str_generated_geometry.json'));c=d['type']['clock'];r=[float(x) for x in re.search(r'export DIE_AREA = (.*)',d['config']).group(1).split()]
f,a=plt.subplots(figsize=(15,6));a.set(xlim=(-15,r[2]+15),ylim=(-12,r[3]+12),aspect='equal',xlabel='um',ylabel='um',title='hd_st_str actual legal88 kit; existing FT first fraction .1725')
a.add_patch(Rectangle((0,0),r[2],r[3],fill=False,ec='k'));p=d['pins'];a.scatter([q['x'] for q in p],[q['y'] for q in p],s=1,c='grey')
for key,row in c['landing_contract']['bands'].items():
 x,y,x1,y1=row['rect_um'];a.add_patch(Rectangle((x,y),x1-x,y1-y,fc='lightblue',ec='blue',alpha=.5));a.text(x,y1+8,key,fontsize=7)
for key,xy in c['landing_status_anchors'].items():a.scatter(*xy,c='orange',s=25);a.annotate(key,xy,fontsize=5)
def walk(v,label):
 if isinstance(v,dict):
  if 'xy_um' in v:a.scatter(*v['xy_um'],c='purple',s=12)
  for k,q in v.items():walk(q,label)
 elif isinstance(v,list):
  if v and all(isinstance(q,dict) and 'xy_um' in q for q in v):a.plot(*zip(*(q['xy_um'] for q in v)),'.-',lw=.6)
  for q in v:walk(q,label)
for k in ('landing_reader_start','landing_writer_start','landing_status_input_stages'):walk(c.get(k,{}),k)
for q in c.get('landing_local_resets',[]): a.scatter(*q['xy_um'],c='red',s=18)
for slot in d['type']['ft_slots']:
 key=slot['name'];ys=[q['y'] for q in p if q['bus']==key+'_i'];y=sum(ys)/len(ys);xs=[r[2]*(.1725+j*(1-.1725)/3) for j in range(4)]
 if slot['in_face']=='E':xs=[r[2]-x for x in xs]
 a.plot(xs,[y]*4,'go--',lw=.8,label='existing '+key+' FT fractions');
a.scatter(*c['tap_um'],c='brown',marker='*',s=80,label='core entry');a.grid(alpha=.15);a.legend(fontsize=7,loc='upper center');f.tight_layout();f.savefig(b/'st_str_generated_geometry.png',dpi=140)
