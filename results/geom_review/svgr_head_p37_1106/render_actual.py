from pathlib import Path
import json,hashlib,re,collections
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parent
kit=next((root/'kits').glob('ot_svgr_own*'));fz=json.loads((kit/'freeze.json').read_text()); pp=json.loads((kit/'plan_pins.json').read_text());pins=pp['pins'];w,h=fz['outline_um']
fig,(ax,bx)=plt.subplots(1,2,figsize=(9,10),gridspec_kw={'width_ratios':[1,1.4]})
ax.add_patch(plt.Rectangle((0,0),w,h,fill=False));ax.add_patch(plt.Rectangle((4.32,4.32),w-8.64,h-8.64,fill=False,ls='--',color='gray'))
for layer in sorted({x['layer'] for x in pins}):
 v=[x for x in pins if x['layer']==layer];ax.scatter([x['x'] for x in v],[x['y'] for x in v],s=2,label=f'{layer} {len(v)}')
clocks=[]
for p in pins:
 if p['name'] in fz['clocks']:
  clocks.append(p);ax.scatter(p['x'],p['y'],s=30,color='black',marker='x');ax.annotate(p['name'],(p['x'],p['y']),fontsize=7)
ax.set_aspect('equal');ax.set_xlim(-15,w+15);ax.set_ylim(-10,h+10);ax.legend(fontsize=7);ax.set_title('Actual generated pin centres')
bx.axis('off');text=f"{fz['view']}\nKit {fz['kit_hash']}\nRecipe {fz['recipe_key']}\nOutline {w} x {h} um\n{len(pins)} actual pin centres\nMacros {len(fz.get('macros',[]))}\nSource {fz.get('source_commit')}\n\nFace stages {fz.get('face_shell')}\n\nClock ports:\n"+'\n'.join(f"{x['name']}: {x['x']:.3f}, {x['y']:.3f}" for x in clocks)
bx.text(0,0.97,text,va='top',fontsize=9,wrap=True);fig.tight_layout();fig.savefig(root/'actual_kit.png',dpi=160)
j=dict(kit=str(kit),kit_hash=fz['kit_hash'],view=fz['view'],outline_um=[w,h],pins=len(pins),clocks=clocks,macros=fz.get('macros',[]),source_commit=fz.get('source_commit'),recipe=fz['recipe_key'],plan_pins_source_sha256=fz['plan_pins_source_sha256'],io_tcl_sha256=hashlib.sha256((kit/'io.tcl').read_bytes()).hexdigest(),generation_only=True,physical_route_run=False)
(root/'actual_kit.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j,indent=2))
