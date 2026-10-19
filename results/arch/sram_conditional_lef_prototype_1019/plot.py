import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=Path(__file__).resolve().parent;j=json.loads((P/'prototype.json').read_text())
fig,axs=plt.subplots(2,2,figsize=(16,10));colors={'VDD':'#d62728','VSS':'#2454ba'}
for row,(fam,f) in enumerate(j['families'].items()):
 w,h=f['outline_nm']
 for col,ax in enumerate(axs[row]):
  for b in f['obs']:
   r=b['rect_nm'];ax.add_patch(Rectangle((r[0]/1000,r[1]/1000),(r[2]-r[0])/1000,(r[3]-r[1])/1000,facecolor='#aaa' if b['kind'].startswith('original') else '#b681c2',alpha=.05 if b['kind'].startswith('original') else .22,edgecolor='none'))
  for pin in f['pins']:
   for p in pin['ports']:
    r=p['rect_nm'];ax.add_patch(Rectangle((r[0]/1000,r[1]/1000),(r[2]-r[0])/1000,(r[3]-r[1])/1000,color=colors.get(pin['name'],'#238b45'),alpha=.85))
  ax.add_patch(Rectangle((0,0),w/1000,h/1000,fill=False,color='black',lw=1));ax.set_xlabel('µm');ax.set_ylabel('µm');ax.set_aspect('equal');ax.grid(alpha=.15)
  if col==0:
   ax.set_xlim(-w*.02/1000,w*1.02/1000);ax.set_ylim(-h*.05/1000,h*1.05/1000);ax.set_title(f'{fam}: {f["signal_count"]} signal PINs + VDD/VSS; retained OBS/exclusions')
  else:
   x=f['pins'][-2]['ports'][1]['rect_nm'][0]/1000
   ax.set_xlim(x-.65,x+.75);ax.set_ylim(-.03,.7);ax.set_title(f'{fam}: south PG ports; lower exclusions retained (purple)')
fig.suptitle('CONDITIONAL ANALYTICAL LEF PROTOTYPE — AP/PDN/core fit HOLD\nDistinct masters; exact terminal subsets; R0 origin 0 mod 144 nm; no native B run',fontsize=14)
fig.tight_layout(rect=[0,0,1,.92]);fig.savefig(P/'CONDITIONAL_LEF_PROTOTYPE.png',dpi=160)
