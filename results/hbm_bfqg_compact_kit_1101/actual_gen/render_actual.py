from pathlib import Path
import argparse,json,re,hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ap=argparse.ArgumentParser();ap.add_argument('inputs',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
pins=json.loads((a.inputs/'pins.json').read_text());pins=pins.get('pins',[]) if isinstance(pins,dict) else pins
f=json.loads((a.inputs/'freeze.json').read_text());w,h=f['outline_um'];macros=[]
for inst,master,x,y,ori in re.findall(r'\{([^{}]+)\}\s+(\w+)\s+([\d.]+)\s+([\d.]+)\s+(R0|MX|MY|R180)',(a.inputs/'macro_placement.tcl').read_text()):
 t=(a.inputs/'macros'/(master+'.lef')).read_text();mw,mh=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',t).groups());macros.append({'instance':inst,'master':master,'origin':[float(x),float(y)],'size':[mw,mh],'orient':ori,'lef_sha256':hashlib.sha256(t.encode()).hexdigest()})
clk=[p for p in pins if p.get('bus',p.get('name','')).startswith('clk')];counts={}
for p in pins:counts[p.get('side',p.get('face','I'))]=counts.get(p.get('side',p.get('face','I')),0)+1
r={'status':'ACTUAL_GENERATED_INPUT_GEOMETRY_ONLY','outline_um':[w,h],'pins':len(pins),'pin_faces':counts,'clocks':clk,'macros':macros,'freeze':f,'placement':'NOT RUN','clock_tree':'NOT RUN','PDN':'GEN_RECIPE_ONLY_NO_PHYSICAL_CLAIM','source_scope':'exact frozen2files/native no external shell, previoussource8650EQ/reset4 component evidence; newphysical proof not yet run','parent_scope':'approved693e/planefe8899a/pin69d23342; snapped16instance tap/data changes still need actualparenttiming'}
(a.out/'actual_gen_model.json').write_text(json.dumps(r,indent=2)+'\n')
fig,ax=plt.subplots(figsize=(10,8));ax.add_patch(Rectangle((0,0),w,h,fill=False,lw=1.4,color='black'))
for m in macros:
 x,y=m['origin'];mw,mh=m['size'];ax.add_patch(Rectangle((x-4.32,y-4.32),mw+8.64,mh+8.64,fill=False,ls='--',edgecolor='gray'));ax.add_patch(Rectangle((x,y),mw,mh,facecolor='#d5dce1',edgecolor='#405060'));ax.text(x+mw/2,y+mh/2,m['instance']+'\n'+str(mw)+'×'+str(mh),ha='center',va='center',fontsize=6)
for name,color in [(n,'#2266aa') for n in sorted({p.get('bus',p.get('name','').split('[')[0]) for p in pins}) if not n.startswith('clk')]:
 ps=[p for p in pins if p.get('bus',p.get('name','').split('[')[0])==name]
 if ps:ax.scatter([p['x'] for p in ps],[p['y'] for p in ps],s=6,c=color,label=name+' '+str(len(ps)),zorder=3)
for p in clk:ax.scatter([p['x']],[p['y']],marker='*',s=130,c='red',label='actual native '+p.get('bus',p.get('name','clk')),zorder=5);ax.annotate(p.get('bus',p.get('name','clk')),(p['x'],p['y']),xytext=(p['x']+8,p['y']+8),arrowprops={'arrowstyle':'->'},fontsize=9,color='red')
ax.set(xlim=(-5,w+5),ylim=(-5,h+5),aspect='equal',xlabel='um',ylabel='um',title='Compact native BFQG actual GEN pins + SRAM LEF geometry\n259.2×220.32, all1340 native pins and20nativeclocks; no placed cells/PG/routes yet')
ax.legend(loc='upper center',bbox_to_anchor=(.5,-.1),ncol=5,fontsize=8);fig.tight_layout();fig.savefig(a.out/'actual_gen_geometry.png',dpi=160,bbox_inches='tight');print('pins',len(pins),'macros',len(macros),'clk',clk)
