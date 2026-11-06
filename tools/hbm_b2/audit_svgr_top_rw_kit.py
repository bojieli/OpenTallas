from pathlib import Path
import re,json,hashlib,collections
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import argparse
root=Path(__file__).resolve().parents[2];ap=argparse.ArgumentParser();ap.add_argument('--kit',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();kit=a.kit;out=a.out;out.mkdir(parents=True,exist_ok=True);f=json.loads((kit/'freeze.json').read_text());pins=json.loads((kit/'pins.json').read_text());rows=[];db={}
for inst,master,x,y,o in re.findall(r'\{([^{}]+)\}\s+(ot_sram\S+)\s+([\d.]+)\s+([\d.]+)\s+(\S+)',(kit/'macro_placement.tcl').read_text()):
 t=(kit/'macros'/(master+'.lef')).read_text();w,h=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',t).groups());rects=[]
 for name,body in re.findall(r'\n\s*PIN\s+(\S+)\s*\n(.*?)\n\s*END\s+\1',t,re.S):
  if 'USE POWER' in body or 'USE GROUND' in body:continue
  layer=re.search(r'LAYER\s+(\S+)\s*;',body)[1]
  v=re.search(r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)',body)
  if v:
   x1,y1,x2,y2=map(float,v.groups());px=(x1+x2)/2;py=(y1+y2)/2;rects.append(dict(name=name,layer=layer,x=w-px if o=='MY' else px,y=py))
 row=dict(instance=inst.replace('\\',''),master=master,origin_um=[float(x),float(y)],size_um=[w,h],orient=o,pins=len(rects),macro_area_um2=w*h)
 off=[]
 for p in rects:
  if p['layer']=='M4':
   gy=float(y)+p['y'];err=abs((gy-.024)/.048-round((gy-.024)/.048))*.048
   if err>1e-6:off.append((p['name'],gy,err))
 row['off_track_M4_signal_pin_centres']=len(off);row['off_track_examples']=off[:2];rows.append(row);db[inst.replace('\\','')]=rects
assert len(rows)==9
cache=[x for x in rows if '.g_rw.' in x['instance']];assert len(cache)==5
assert all(x['size_um']==[91.8,27.576] for x in cache)
fig,ax=plt.subplots(figsize=(8,12));ax.add_patch(Rectangle((0,0),*f['outline_um'],fill=False));ax.axhspan(160,200,color='red',alpha=.09)
for p in pins:ax.plot(p['x'],p['y'],'.',color='#777',ms=.8)
for row in rows:
 x,y=row['origin_um'];w,h=row['size_um'];c='.g_rw.' in row['instance'];ax.add_patch(Rectangle((x-4.32,y-4.32),w+8.64,h+8.64,fill=False,linestyle='--',edgecolor='#888',lw=.6));ax.add_patch(Rectangle((x,y),w,h,facecolor='#c9e3f6' if c else '#ddd',edgecolor='black',lw=.8))
 for p in db[row['instance']]:ax.plot(x+p['x'],y+p['y'],'.',color='#087f8c' if p['name'].startswith(('rd_','r_')) else '#c65b27',ms=.8)
 label=re.search(r'g_cache\[\d\]',row['instance']);label=label[0] if label else row['instance'].split('.')[-1];ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=7)
clock=next(p for p in pins if p['bus']=='stream_clk');ax.plot(clock['x'],clock['y'],'*',color='purple',ms=10);ax.annotate('stream_clk M5\nM4 SRAM OBS ends below M5',(clock['x'],clock['y']),xytext=(240,330),fontsize=7,arrowprops={'arrowstyle':'->'},ha='right')
ax.set(xlim=(-8,311),ylim=(-8,648),aspect='equal',xlabel='um',ylabel='um');ax.set_title('Actual p37 private GEN kit '+f['kit_hash']+'\n9 actual SRAM homes; five approved RW caches (blue)\nActual signal pins: teal read / orange write-control; red prior hot band');fig.tight_layout();fig.savefig(out/'actual_p37_kit.png',dpi=180)
receipt=dict(kit=str(kit),kit_hash=f['kit_hash'],outline_um=f['outline_um'],pins=f['pins'],clocks=f['clocks'],resets=f['resets'],face_shell=f['face_shell'],actual_macro_placement=rows,actual_macro_area_um2=sum(x['macro_area_um2'] for x in rows),off_track_cache_M4=sum(x['off_track_M4_signal_pin_centres'] for x in cache),sizing_status='NOT_RUN',image='actual_p37_kit.png')
(out/'actual_p37_geometry.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k!='actual_macro_placement'},indent=2));print([(x['instance'],x['origin_um'],x['off_track_M4_signal_pin_centres']) for x in rows])
