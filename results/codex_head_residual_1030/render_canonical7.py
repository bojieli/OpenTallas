import re,json
from pathlib import Path
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path(__file__).parent;k=p/'canonical7_meta';f,a=plt.subplots(figsize=(9,12))
size={}
for typ in ['A','B']:
 s=(k/f'ot_s81hd_elem{typ}_cv.lef').read_text();m=re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',s);size[typ]=tuple(map(float,m.groups()))
for nm,x,y,ori in re.findall(r'place_macro -macro_name \{([^}]+)\} -location \{([\d.]+) ([\d.]+)\} -orientation (\w+)',(k/'macro_place.tcl').read_text()):
 typ='A' if 'eA' in nm else 'B';w,h=size[typ];x=float(x);y=float(y)
 a.add_patch(Rectangle((x,y),w,h,fc='lightgray',ec='black',hatch='//'));a.text(x+5,y+10,nm.split('.')[-1]+' '+ori,fontsize=8)
pins=json.load(open(k/'plan_pins.json'))['pins'];clks=[v for v in pins if v['name'].startswith('clk_t')]
for v in clks:a.plot(v['x'],v['y'],'*',color='gold',mec='black',ms=8)
# Actual generated control windows, including R1 local-reset copies and R2 status stages.
for nm,vals,tag in re.findall(r'\{(u_cland_[^ {}]+) \{([\d. ]+)\} ([^{}]+)\}',(k/'landing_placement.tcl').read_text()):
 r=list(map(float,vals.split()));
 if len(r)!=4:continue
 x,y,X,Y=r;c='darkorange' if 'reset' in tag else 'blue' if 'reader' in tag else 'purple' if 'writer' in tag else 'green'
 a.add_patch(Rectangle((x,y),X-x,Y-y,fill=False,ec=c,lw=1.3))
for k0,c in [('a_early_skew','royalblue'),('b_skew','teal'),('merge_pipeline','orange')]:
 r=json.load(open(p/'tile5_groups.json'))['rects'][k0];x,y,X,Y=r;a.add_patch(Rectangle((x,y),X-x,Y-y,fill=True,fc=c,ec=c,alpha=.09))
# Actual generated R3/W3 routes in the current legal source.
a.plot([518.4,510,180,90],[862.944,714,714,858],'-o',color='blue',ms=3,label='R3 START (existing cycles)')
a.plot([518.4,560,610,660,706.336],[862.944,862,862,862,867.232],'-o',color='purple',ms=3,label='W3 START (existing cycles)')
a.plot([85,190,520,706.336],[858,714,714,862.944],'-o',color='green',ms=3,label='R2 status tree')
a.add_patch(Rectangle((20.52,742),27,248,fill=False,ec='red',lw=1.2,label='private write logic in remaining FF gaps'))
a.plot([351,355,355,252.18],[185,490,714,714],color='darkred',lw=1,label='A0/A1 existing fault pipelines, bounded V/H')
a.set(xlim=(0,708.48),ylim=(0,1036.8),aspect='equal',xlabel='x (um)',ylabel='y (um)',title=f'Canonical HEAD tile, ROOT88 R3/W3 R1/R2\nMeasured native7 + bit-major core, {len(clks)} generated clock entries; no added data cycles')
a.legend(loc='upper left',fontsize=7);f.savefig(p/'canonical7_trial.png',dpi=170,bbox_inches='tight')
print('clock_entries',len(clks),'macros',size)
