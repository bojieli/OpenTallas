from pathlib import Path
import json,collections,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path(__file__).resolve().parent
mp=json.load(open(r/'mp.json'));est=json.load(open(r/'mp.est.json'));pins=json.load(open(r/'pins.json'));sl=json.load(open(r/'slice.json'));W,H=mp['outline_um'];fig,ax=plt.subplots(figsize=(12,9))
ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=2,color='black'))
for m in mp['macro_placement']:
 x,y=m['origin_um'];z=est['masters'][m['macro']];w,h=z['w'],z['h'];ha=est['halo_um'];ax.add_patch(Rectangle((x-ha,y-ha),w+2*ha,h+2*ha,color='lightgrey',alpha=.5));ax.add_patch(Rectangle((x,y),w,h,color='#a8c5e2',ec='#284b63'));ax.text(x+w/2,y+h/2,m['k'],fontsize=8,ha='center')
for q in sl['islands']:
 x0,y0,x1,y1=q['rect_um'];ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,color='#ffbe55',ec='#9b5700'));ax.text((x0+x1)/2,(y0+y1)/2,q['name'].replace('tree_leaf','L'),fontsize=6,ha='center')
faces=collections.defaultdict(list)
for p in pins:
 f=min([(p['x'],'W'),(W-p['x'],'E'),(p['y'],'S'),(H-p['y'],'N')])[1];faces[f].append(p)
colors={'W':'#177245','E':'#aa2233','N':'#674ea7','S':'#007da3'}
for f,ps in faces.items():ax.scatter([p['x'] for p in ps],[p['y'] for p in ps],s=3,c=colors[f],label=f'{f}: {len(ps)} pins')
ax.set_aspect('equal');ax.set_xlim(-15,W+15);ax.set_ylim(-15,H+15);ax.set_xlabel('um');ax.set_ylabel('um');ax.legend(loc='upper center',bbox_to_anchor=(.5,-.08),ncol=4);ax.set_title('TOPK current C25b pins + 8 SRAMs + 17 macro-clear clock islands\nTree standard logic ~15,520 um2 historical mapping; no placement claim')
fig.tight_layout();fig.savefig(r/'topk_c25b_plan.png',dpi=150)
# Conservative full-pin upper bound, not a claim that all SRAM pins carry dynamic data.
tracks=48.6;pin_demand=sum(x['pins'] for x in est['escape']);macrocols=2*(171.288+2*est['halo_um']);minw=macrocols+pin_demand/tracks+8.64
out={'pins_by_face':{f:len(v) for f,v in faces.items()},'clock_islands':len(sl['islands']),'current_outline_um':[W,H],'macro_halo_area_um2':est['area_um2']['macros_with_halo'],'tree_historical_logic_area_um2':15519.65,'historical_free_area_fill':15519.65/est['area_um2']['free'],'minimum_width_full_pin_escape_at_util1_um':minw,'minimum_width_full_pin_escape_at_util06_um':macrocols+pin_demand/tracks/.6+8.64,'minimum_height_2col_macro_array_um':4*77.784+4*8.64+8.64,'escape_upper_bound':est['escape'],'note':'Full-pin bound includes fixed mask/repair pins; actual dynamic routing demand is lower. Do not shrink width from low logic fill. Review placement/clock/data reach and GRT before any route.'};(r/'estimate.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
