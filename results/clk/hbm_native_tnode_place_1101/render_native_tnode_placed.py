from pathlib import Path
import csv,json,collections
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
r=Path(__file__).resolve().parent/'tnode_native_place';rows=list(csv.DictReader((r/'placed.csv').open()))
for row in rows:
 for key in ['x','y','w','h']:row[key]=float(row[key])
fig,ax=plt.subplots(figsize=(10,10));colors={'std':'#777777','ff':'#2469a0','buf':'#389458','tap':'#c6b277','macro':'#bcc5ce'}
counts=collections.Counter(row['kind']for row in rows)
for kind,color in colors.items():
 selected=[row for row in rows if row['kind']==kind]
 patches=[Rectangle((row['x'],row['y']),row['w'],row['h'])for row in selected]
 if patches:ax.add_collection(PatchCollection(patches,facecolor=color,edgecolor='none',alpha=.65 if kind!='macro'else.95,label=kind))
for row in rows:
 if row['kind']=='macro':
  ax.add_patch(Rectangle((row['x']-2,row['y']-2),row['w']+4,row['h']+4,fill=False,ls='--',ec='#555555',lw=.8));ax.text(row['x']+row['w']/2,row['y']+row['h']/2,row['name'],ha='center',fontsize=8)
pins=[row for row in rows if row['kind']=='pin'];ax.scatter([p['x']for p in pins],[p['y']for p in pins],s=1.4,c='black',alpha=.7)
clock=next(row for row in rows if row['kind']=='pin'and row['name']=='clk')
assert abs(clock['x']-86.376)<1e-6 and abs(clock['y']-86.4)<1e-6,clock
ax.scatter([clock['x']],[clock['y']],s=100,marker='*',c='red',zorder=5);ax.annotate('actual native clk M5',(86.376,86.4),xytext=(100,92),arrowprops={'arrowstyle':'->'},fontsize=9,color='red')
ax.add_patch(Rectangle((0,0),172.8,172.8,fill=False,ec='black',lw=1.2));ax.set_xlim(-4,176.8);ax.set_ylim(-4,176.8);ax.set_aspect('equal');ax.set_xlabel('µm');ax.set_ylabel('µm')
ax.set_title('Current native Tnode — actual ordinary PLACE output\nExact G/source4730 reset4; all pad inputs free. No CTS/GRT/STA qualification.',fontsize=12)
ax.text(.01,-.075,'Actual cells: '+', '.join(f'{k} {v}'for k,v in counts.items())+'\nMacro halos shown: input2µm; clock point from exact frozen native pin contract. PG/routes not drawn.',transform=ax.transAxes,fontsize=8)
fig.tight_layout();fig.savefig(r/'native_actual_placed.png',dpi=170);(r/'placed_counts.json').write_text(json.dumps(dict(counts=counts,scope='Actual placed CSV only; no inferred dataflow/timing/PG continuity verdict'),indent=2));print(counts)
