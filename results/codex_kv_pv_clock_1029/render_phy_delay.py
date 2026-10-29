import json,sys
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle
from pathlib import Path
p=Path(sys.argv[1]);d=json.load(open(p));u=d['dbu'];fig,ax=plt.subplots(figsize=(8,8),layout='constrained');sh=[]
for i in d['original']:
 x0,y0,x1,y1=i['box'];sh.append(Rectangle((x0,y0),x1-x0,y1-y0))
ax.add_collection(PatchCollection(sh,facecolor='#8eb6cf',edgecolor='none',alpha=.5,rasterized=True))
for j,col in enumerate(('#d34835','#2c9859')):
 pts=[((r['cells'][j]['x']/u)+.135,(r['cells'][j]['y']/u)+.135)for r in d['records']];ax.scatter(*zip(*pts),s=3,color=col,label=f'delay stage{j+1} (1025 BUF)',alpha=.75)
ax.scatter([43.2],[47.52],marker='*',s=110,c='black',label='existing clock entry (unchanged)')
ax.set_xlim(0,86.4);ax.set_ylim(0,95.04);ax.set_aspect('equal');ax.grid(alpha=.15);ax.legend(loc='lower left',fontsize=8);ax.set_xlabel('um');ax.set_ylabel('um')
ax.set_title('PHY fixed input delay: 2 noninverting BUF per1024 data +1 valid\nExisting FF/capture/clock locations and connections preserved',fontsize=10)
fig.text(.03,.008,f"2050 legal row sites, added area149.445um²; maxdistance from originalfirst consumer31.50um. RawcaptureFFunchanged, 0cycles; actualTT/FF/RCX stillowed.",fontsize=7)
fig.savefig(p.with_suffix('.png'),dpi=150)
