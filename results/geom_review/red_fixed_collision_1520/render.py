import csv,json
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle
P=Path(__file__).parent
fixed=list(csv.DictReader((P/'fixed.tsv').open(),delimiter='\t'))
nodes=json.loads((P/'snapped_nodes.json').read_text())
f,ax=plt.subplots(figsize=(10,10))
for typ,color,alpha in [('CORE_WELLTAP','#333333',.8),('CORE','#efb36b',.4)]:
 rr=[Rectangle((float(r['x0']),float(r['y0'])),float(r['x1'])-float(r['x0']),float(r['y1'])-float(r['y0'])) for r in fixed if r['type']==typ]
 ax.add_collection(PatchCollection(rr,facecolors=color,edgecolors='none',alpha=alpha,label=typ))
rr=[Rectangle((r['rect'][0],r['rect'][1]),r['rect'][2]-r['rect'][0],r['rect'][3]-r['rect'][1]) for r in nodes]
ax.add_collection(PatchCollection(rr,facecolors='#175dba',edgecolors='none'))
ax.set(xlim=(0,276.48),ylim=(0,276.48),aspect='equal',xlabel='um',ylabel='um',title='RED proposed snapped BUFx8 bodies (blue) vs actual locked taps (black)\nOrange old649 clock seeds removed; no new placement/CTS run')
f.savefig(P/'fixed_collision_review.png',dpi=180,bbox_inches='tight')
