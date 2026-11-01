from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path(__file__).resolve().parent
fig,axes=plt.subplots(1,2,figsize=(11,9))
for ax,form in zip(axes,['near','east']):
 j=json.load(open(r/f'slid_mesh_contact_{form}/scope.json'))
 for c in j['cores']:
  x,y,xx,yy=c['rect'];ax.add_patch(Rectangle((x,y),xx-x,yy-y,color='salmon',alpha=.4))
 for k in range(24,105):ax.axhline(k*4.32,color='gray',alpha=.15,lw=2)
 for k in range(54,79):ax.axvline(k*4.32,color='gray',alpha=.15,lw=2)
 for a,b in j['graph']['edges']:
  if a[0]==b[0]:ax.plot([a[1],b[1]],[a[2],b[2]],color='blue' if a[0]=='M9' else 'purple',lw=1)
 for n,c in j['cells'].items():
  ax.add_patch(Rectangle((c['x'],c['y']),1.62,.27,color='black'));ax.text(c['x']+2,c['y']+3,n,fontsize=8)
 ax.set_xlim(230,340);ax.set_ylim(100,450);ax.set_aspect('equal');ax.set_title(form+': actual displaced drivers + fixed doglegs')
fig.suptitle('Pre-route review: preserved strap anchors / actual current union sites\nM8 horizontal + M9 vertical explicit conductors; PG retained. Physical contact diagnostic only.')
fig.tight_layout();fig.savefig(r/'slid_contacts_review.png',dpi=140)
