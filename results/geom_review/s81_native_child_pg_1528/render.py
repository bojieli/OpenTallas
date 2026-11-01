import re,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path(__file__).parent
text=(r/'macro_place.tcl').read_text().split('} {\n',1)[0]
places=[]
for m,raw in re.findall(r'(\w+) \{\{(.*?)\}\}',text):
 for xy in re.split(r'\}\s*\{',raw):
  x,y,o=xy.split();places.append((m,float(x),float(y),o))
assert len(places)==32,len(places)
fig,axs=plt.subplots(1,2,figsize=(16,8))
ax=axs[0]
for y in [4.32+1.968+4.32*k for k in range(149)]:
 for d,col in ((0,'firebrick'),(.384,'navy')):ax.add_patch(Rectangle((4.32,y+d-.144),639.36,.288,color=col,alpha=.22))
for m,x,y,o in places:
 lef=(r/'macros'/(m+'.lef')).read_text();w,h=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',lef).groups())
 ax.add_patch(Rectangle((x,y),w,h,facecolor='lightgray' if 'sram' in m else 'gold',edgecolor='black',alpha=.7))
 ax.text(x+w/2,y+h/2,'SRAM\nM4' if 'sram' in m else 'SIGNED\nhist M5',ha='center',va='center',fontsize=6)
ax.set(xlim=(0,648),ylim=(0,648),aspect='equal',title='Prepared parent PG adapter: 16 M4 SRAM + 16 M5 hist\nM6 transverse top-PG stripes; signal ceiling stays M5',xlabel='um',ylabel='um')
ax=axs[1];m='ot_s81ph_native_sel_hist_bank';lef=(r/'macros'/(m+'.lef')).read_text();ox=oy=43.2
ax.add_patch(Rectangle((0,0),64.8,54,facecolor='lightgray',alpha=.5))
for pin,col in (('VDD','firebrick'),('VSS','navy')):
 b=re.search(r'\bPIN\s+'+pin+r'\b(.*?)\bEND\s+'+pin+r'\b',lef,re.S)[1]
 for a,b,c,d in re.findall(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',b):
  a,b,c,d=map(float,(a,b,c,d));ax.add_patch(Rectangle((a,b),c-a,d-b,facecolor=col,alpha=.65))
for y in [4.32+1.968+4.32*k-oy for k in range(149)]:
 for d,col in ((0,'firebrick'),(.384,'navy')):
  if -4<y+d<58:ax.add_patch(Rectangle((-3,y+d-.144),70.8,.288,facecolor=col,alpha=.35))
ax.set(xlim=(-4,69),ylim=(-4,58),aspect='equal',title='Actual child LEF: M5 VDD/VSS pins, M1–M5 OBS\nProposed M6 crosses above OBS; matching-net M5↔M6 vias required',xlabel='child-local um',ylabel='um')
fig.suptitle('PREPARED PG geometry only — no PDN connectivity/IR claim; existing M7 envelope; eventual abstract must expose M6',fontsize=10)
fig.tight_layout(rect=(0,0,1,.94));fig.savefig(r/'pg_candidate.png',dpi=145)
(r/'placement.json').write_text(json.dumps(places,indent=1)+'\n')
