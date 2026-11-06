from pathlib import Path
import re,json,hashlib,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path(__file__).resolve().parents[2];out=r/'physical/die_plan/hbm/over_cap_split/reform_1106/svgr_top_cache';import argparse
ap=argparse.ArgumentParser();ap.add_argument('--retained-top',type=Path,required=True);args=ap.parse_args();old=args.retained_top
masters=['ot_sram_1r1w_128x256_m1_r2c2','ot_sram_1r1w_128x256_m1_r0c0_g256','ot_sram_1r1w_1024x256_m2_r2c2'];db={}
for m in masters:
 path=r/'physical/asap7_memory_macros_v2'/m/(m+'.lef')
 if not path.exists():raise RuntimeError(path)
 text=path.read_text();w,h=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',text).groups());pins=[]
 for name,body in re.findall(r'\n\s*PIN\s+(\S+)\s*\n(.*?)\n\s*END\s+\1',text,re.S):
  if 'USE POWER' in body or 'USE GROUND' in body:continue
  rects=re.findall(r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)',body)
  if not rects:continue
  x1,y1,x2,y2=map(float,rects[0]);x=(x1+x2)/2;y=(y1+y2)/2
  face=min({'W':x,'E':w-x,'S':y,'N':h-y},key=lambda k:{'W':x,'E':w-x,'S':y,'N':h-y}[k]);pins.append(dict(name=name,x=x,y=y,face=face))
 db[m]=dict(width=w,height=h,pins=pins,lef_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
rows=[]
for inst,master,x,y,orient in re.findall(r'\{([^{}]+)\}\s+(ot_sram\S+)\s+([\d.]+)\s+([\d.]+)\s+(\S+)',(old/'macro_placement.tcl').read_text()):rows.append(dict(instance=inst.replace('\\',''),master=master,x=float(x),y=float(y),orient=orient))
external=json.loads((old/'pins.json').read_text());fig,axes=plt.subplots(1,3,figsize=(15,11),gridspec_kw={'width_ratios':[1,1,1.05]})
for idx,ax in enumerate(axes[:2]):
 ax.add_patch(Rectangle((0,0),302.4,639.36,fill=False));ax.axhspan(160,200,color='red',alpha=.10)
 for p in external:ax.plot(p['x'],p['y'],'.',color='#999999',ms=.35)
 for row in rows:
  master=row['master'];cache='.rows.' in row['instance'];x=row['x'];y=row['y']
  if idx and cache:master=masters[1];y=round(y/.048)*.048
  md=db[master];w=md['width'];h=md['height'];ax.add_patch(Rectangle((x,y),w,h,facecolor='#d5e8fa' if cache else '#ddd',edgecolor='black',lw=.6))
  for p in md['pins']:
   px=w-p['x'] if row['orient']=='MY' else p['x'];py=p['y'];color='#087f8c' if p['name'].startswith(('r_','rd_')) else '#c65b27'
   ax.plot(x+px,y+py,'.',color=color,ms=.45)
  label=row['instance'].split('.')[-2];ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=6)
 ax.set(xlim=(-8,311),ylim=(-8,648),aspect='equal',xlabel='um',ylabel='um');ax.set_title('Retained failed TOP B' if not idx else 'Proposed TOP: five approved RW macros\nsame outline, external pins and shell')
ax=axes[2];pr=json.loads((out/'profile.json').read_text());ax.add_patch(Rectangle((0,0),*pr['outline_um'],fill=False))
for row in pr['macros']:
 x,y=row['origin_um'];w,h=row['size_um'];ax.add_patch(Rectangle((x-4.32,y-4.32),w+8.64,h+8.64,fill=False,edgecolor='#999',linestyle='--',lw=.7));ax.add_patch(Rectangle((x,y),w,h,facecolor='#d5e8fa',edgecolor='black'));ax.text(x+w/2,y+h/2,row['instance'].split('.')[1],ha='center',fontsize=7)
ax.text(112,212,'Logic/clock/PG space\nMapped count pending',ha='center',fontsize=9);ax.set(xlim=(-8,233),ylim=(-8,259),aspect='equal',xlabel='um',ylabel='um');ax.set_title('Secondary native helper cut\n2 columns x 3 rows; no face cycles')
fig.suptitle('SVGR TOP successor: actual LEF pin rectangles and retained TOP external pins\nRed band = measured failed-route hot band y160..200; teal read pins, orange write/control pins');fig.tight_layout();fig.savefig(out/'macro_pin_review.png',dpi=180)
metrics={m:dict(width_um=d['width'],height_um=d['height'],signal_pins=len(d['pins']),pins_per_face={f:sum(p['face']==f for p in d['pins']) for f in 'WESN'},lef_sha256=d['lef_sha256']) for m,d in db.items()}
(out/'macro_pin_metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
proposal=[]
for row in rows:
 row=dict(row)
 if '.rows.' in row['instance']:
  row['master']=masters[1];row['instance']=row['instance'].replace('.u_payload','.g_rw.u_payload');row['y']=round(round(row['y']/.048)*.048,6)
 row['instance']=row['instance'].replace('u_fcore.','u_fcore.u_core.',1)
 proposal.append(row)
(out/'whole_top_macro_placement.json').write_text(json.dumps(proposal,indent=2)+'\n')
(out/'retained_external_pin_identity.json').write_text(json.dumps(dict(source='epyc6:ot_svgr_top_vB/pins.json',sha256=hashlib.sha256((old/'pins.json').read_bytes()).hexdigest(),pin_bits=len(external),clock=next(p for p in external if p['bus']=='stream_clk')),indent=2)+'\n')
print(json.dumps(metrics,indent=2))
