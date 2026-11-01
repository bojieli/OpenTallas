import json,pathlib,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
b=pathlib.Path(__file__).resolve().parent.parent;o=b/'overlay';t=json.load(open(o/'type_overlay.json'));p=json.load(open(o/'named_pin_locations.json'));q={}
f,a=plt.subplots(figsize=(8,13));a.add_patch(Rectangle((0,0),311.04,613.44,fill=False,lw=1.5));colors={'M4':'#8b55b5','M5':'#298849','M6':'#cc7b27','M7':'#3869bd'}
for layer,c in colors.items():
 z=[x for x in p if x['layer']==layer];a.scatter([x['x'] for x in z],[x['y'] for x in z],s=1,c=c,label=layer)
for h in t['hard_cores']:
 x,y=h['origin_um'];a.add_patch(Rectangle((x-4.32,y-4.32),130.488,71.592,fill=False,ec='red',ls='--'));a.add_patch(Rectangle((x,y),121.848,62.952,fc='#ddd',ec='black'));a.text(x+60,y+31,h['inst'].split('.')[-1],ha='center')
for n,z in t['clock']['landing_contract']['bands'].items():
 x,y,u,v=z['rect_um'];a.add_patch(Rectangle((x,y),u-x,v-y,fc='green',alpha=.08,ec='green'));a.text((x+u)/2,(y+v)/2,n,fontsize=6,ha='center')
for z in t['clock']['taps']:
 x,y=z['xy'];a.plot(x,y,'b.',ms=3);a.text(x+1,y+1,z['name'].replace('clk','t'),fontsize=5)
a.set(xlim=(-10,321),ylim=(-10,624),aspect='equal',xlabel='um',ylabel='um',title='PRIVATE canonical STM overlay: 311.04 × 613.44 um\nData PG-aware allocator; combined peak 67/10um (WARN); no CAD')
a.legend(loc='upper left',fontsize=7);f.tight_layout();f.savefig(o/'canonical_overlay.png',dpi=150)
