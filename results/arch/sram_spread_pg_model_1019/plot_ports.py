import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=Path(__file__).resolve().parent;m=json.loads((P/'model.json').read_text());v=json.loads((P/'verification.json').read_text());fig,axs=plt.subplots(2,2,figsize=(11,9),layout='constrained')
for row,(f,d) in enumerate(m['families'].items()):
 c=d['upper_cut_corridor_M4_V4_M5_nm'];h=d['outline_nm'][1]
 for col,face in enumerate(['S','N']):
  ax=axs[row,col]
  for t in d['new_actual_supply_metal']:
   if t['role']!='full_height_internal_supply_trunk':continue
   r=t['rect_nm'];ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],color='red' if t['net']=='VDD' else 'blue',alpha=.25))
  for t in v[f]['external_PG_ports']:
   if not t['identity'].startswith(face):continue
   r=t['rect_nm'];ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fill=False,edgecolor='red' if t['net']=='VDD' else 'blue',linewidth=2));ax.text((r[0]+r[2])/2,(r[1]+r[3])/2,t['net'],ha='center',fontsize=8,rotation=90)
  ax.axvline(c[0],ls='--',color='grey');ax.axvline(c[2],ls='--',color='grey');ax.set_xlim(c[0]-15,c[2]+15);ax.set_ylim((-15,110) if face=='S' else (h-110,h+15));ax.set_aspect('equal');ax.set_title(f.upper()+' '+face+' real M5 port subsets\n192 nm centers; 168 nm metal gap; 5.208/µm');ax.set_xlabel('X nm');ax.set_ylabel('Y nm');ax.grid(alpha=.2)
fig.suptitle('Proposed complete M5 trunk shift: VDD −48 nm, VSS +48 nm\nRetained corridor boundaries dashed; 24×84 nm external subsets. No native AP claim.')
fig.savefig(P/'EXTERNAL_PG_PORTS.png',dpi=160)
