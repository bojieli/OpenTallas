from pathlib import Path
import re,json,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
root=Path('/home/ubuntu/coord/tmp/codex-q6-geometry-0215')
def parse(p):
 shapes={};current=None
 for line in p.read_text().splitlines():
  m=re.match(r'place_pin -pin_name \{([^}]+)\} -layer (M\d+) -location \{([\d.]+) ([\d.]+)\} -pin_size \{([\d.]+) ([\d.]+)\}',line)
  if m:
   n,l,x,y,w,h=m.groups();x,y,w,h=map(float,(x,y,w,h));shapes[n]={'layer':l,'rectangles':[[round(x-w/2,6),round(y-h/2,6),round(x+w/2,6),round(y+h/2,6)]]}
  m=re.match(r'set nt \[\$nb findBTerm \{([^}]+)\}\]',line)
  if m:current=m[1]
  if line.startswith('odb::dbBox_create'):
   r=list(map(float,re.findall(r'round\(([-\d.]+) \* \$nu',line)));assert len(r)==4;shapes[current]['rectangles'].append(r)
 return shapes
for n in ['recip','zh']:
 a=parse(root/(n+'_corrected')/'io.tcl');b=json.load(open(root/(n+'_corrected')/'actual_generated_shapes.json'));assert a==b
fig,axs=plt.subplots(2,2,figsize=(13,10))
for col,(n,title,h) in enumerate([('recip','RECIP actual old compact IO: stale secondary outside',138.24),('recip_corrected','RECIP corrected generated IO: all native access retained',138.24)]):
 ax=axs[0,col];sh=parse(root/n/'io.tcl');ax.add_patch(Rectangle((0,0),216,h,fill=False,color='black',lw=1.2))
 for name,v in sh.items():
  for x0,y0,x1,y1 in v['rectangles']:
   ax.plot([(x0+x1)/2],[(y0+y1)/2],marker='|' if v['layer']=='M5' else '_',ms=6,color='crimson' if y1>h else 'tab:blue')
 ax.set(xlim=(-4,220),ylim=(-4,222),title=title,xlabel='μm',ylabel='μm');ax.set_aspect('equal');ax.grid(alpha=.15)
 if col==0:ax.annotate('x[31] stale secondary\ny=215.845..215.952',xy=(13.404,215.9),xytext=(45,180),arrowprops={'arrowstyle':'->'},fontsize=9)
 else:
  ax.text(20,180,'x[31] north-relative access:\nprimary138.156..138.240\nsecondary138.085..138.192\noverlap0.036 μm; same physical pin',fontsize=9)
  ax.annotate('69 signal pins, zero macros',xy=(13.4,138.2),xytext=(50,150),arrowprops={'arrowstyle':'->'},fontsize=9)
for col,n in enumerate(['zh','zh_corrected']):
 ax=axs[1,col];sh=parse(root/n/'io.tcl');ax.add_patch(Rectangle((0,0),151.2,151.2,fill=False,color='black'))
 for name,v in sh.items():
  r=v['rectangles'][0];x,y=(r[0]+r[2])/2,(r[1]+r[3])/2
  ax.plot(x,y,marker='|' if v['layer']=='M5' else '_',ms=7,color='tab:green' if y<1 else 'tab:orange' if name in ('clk','rst_n') else 'tab:blue')
 ax.set(xlim=(-5,156),ylim=(-5,156),title='ZH actual original IO' if col==0 else 'ZH corrected generated IO: full south spread',xlabel='μm',ylabel='μm');ax.set_aspect('equal');ax.grid(alpha=.15)
 ax.text(8,12,'268 S inputs: x32.220..95.868\nactual extent42.1% of face' if col==0 else '268 S inputs: x2.172..149.004\n97.1% of face; native0.048 μm tracks\nminimum pin pitch0.528 μm',fontsize=9)
 ax.text(8,134,'Clock/reset W unchanged; 68 N outputs unchanged',fontsize=8)
fig.suptitle('Q6 geometry PREP — rendered from actual emitted IO Tcl; no CAD or new macro views',fontsize=13);fig.tight_layout(rect=[0,0,1,.96]);fig.savefig(root/'q6_corrected_generated_geometry.png',dpi=160)
print('TCL_SHAPE_JOIN_PASS407pins, all secondary boxes retained')
