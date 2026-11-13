import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path(__file__).parent
rows=list(csv.DictReader(open(p/'bank_sites.tsv'),delimiter='\t'));bank=list(csv.DictReader(open(p/'bank_rects.tsv'),delimiter='\t'));row=next(x for x in rows if x['bit']=='78');macs=[[float(x)for x in l.split()]for l in open(p/'macros.tsv')]
fig,ax=plt.subplots(figsize=(11,8));pt=lambda pre:(float(row[pre+'_x']),float(row[pre+'_y']))
for x,y,x1,y1 in macs:ax.add_patch(Rectangle((x,y),x1-x,y1-y,facecolor='#eee',edgecolor='#777'))
colors=['#1b9e77','#7570b3','#d95f02','#e7298a']
for b,col in zip(bank,colors):
 x,y,x1,y1=[float(b[z]) for z in ['x0','y0','x1','y1']];ax.add_patch(Rectangle((x,y),x1-x,y1-y,fill=False,edgecolor=col,lw=2))
 label=b['bank'].rsplit(':',1)[1];ax.annotate(f"{label}: {b['cells']}cells /{b['rows']}rows\noccupancy{float(b['occupancy']):.1%}",(x1,y1),xytext=(8,8),textcoords='offset points',fontsize=9,color=col)
for pre,col in zip(['new1','new2','new3','count'],colors):
 ax.scatter([float(r[pre+'_x']) for r in rows],[float(r[pre+'_y']) for r in rows],s=1.5,color=col)
first=pt('first');pc=pt('pc');mid=pt('new3');ny=pt('new1')[1]
route=[first,(first[0],ny),(mid[0],ny),(mid[0],pc[1]),pc]
ax.plot(*zip(*route),color='#4d9221',lw=1,alpha=.5,label='example bit78 corridor skeleton')
ax.scatter(*first,c='red',marker='*',s=100);ax.annotate('hard output/fixed0',first,xytext=(-130,-15),textcoords='offset points')
ax.scatter(*pc,c='blue',marker='s',s=45);ax.annotate('fixed input PC',pc,xytext=(5,-15),textcoords='offset points')
ax.text(930,1190,'u_t12 (MY)');ax.text(490,1190,'u_t02 (MY)',rotation=90)
ax.set_xlim(480,1210);ax.set_ylim(800,1320);ax.set_aspect('equal');ax.set_xlabel('type x (um)');ax.set_ylabel('type y (um)');ax.legend(loc='lower right')
ax.set_title('CBF coherent fixed4: full514-bit bank area in real macro streets\nN banks20rows/35.1%; combined count+mux77rows/16.1%; exact worst per-bit hop387.27um\nCandidate only: actual masters/mux, proposed fourth FF, no ODB saved or PLACE result')
fig.tight_layout();fig.savefig(p/'cbf_bank_area_review.png',dpi=160)
