import csv,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
rows=list(csv.DictReader(open(sys.argv[1]),delimiter='\t'))
fig,ax=plt.subplots(figsize=(14,6.5)); by={}
for r in rows:by.setdefault(r['bucket'],[]).append(r)
colors={'other':'#aaa','encoder_cone':'#9fcabb','encoder_ff':'#136e49','bin_ff':'#3479c4'}
for k,rr in by.items():
 if k=='macro':continue
 if k.startswith('pin_'):c=plt.cm.Blues(.5+.18*int(k[-1]))
 elif k.startswith('txl'):c=plt.cm.autumn(.1+.12*int(k[-1]))
 else:c=colors.get(k,'purple')
 ax.scatter([float(r['x'])+float(r['w'])/2 for r in rr],[float(r['y'])+float(r['h'])/2 for r in rr],s=.4 if k=='other' else 1.4,c=[c],alpha=.18 if k=='other' else .65,label=f'{k}: {len(rr)}',rasterized=True)
for r in by.get('macro',[]):
 x,y,w,h=[float(r[k]) for k in ('x','y','w','h')]
 ax.add_patch(Rectangle((x,y),w,h,fill=False,edgecolor='#333',lw=1))
 ax.text(x+w/2,y+h/2,r['name'].split('.')[-1],ha='center',fontsize=8)
ax.set(xlim=(0,2886),ylim=(1227,0),xlabel='x (um)',ylabel='y (um)',title='RCK t16 vH (S81-RCK-6) actual PLACE: whole-row tap groups, posed reset/valid chain\n3 input PIN rows + 7 TXL rows; counts from placed database; no CTS/GRT claim')
ax.set_aspect('equal');ax.legend(loc='center left',bbox_to_anchor=(1,0.5),markerscale=5,fontsize=8)
fig.tight_layout();fig.savefig(sys.argv[2],dpi=170)
