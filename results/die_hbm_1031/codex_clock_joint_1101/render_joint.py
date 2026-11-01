from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import json,re
r=Path(__file__).resolve().parent
fig,axs=plt.subplots(2,2,figsize=(15,8),gridspec_kw={'width_ratios':[3,1]})
for row,v in enumerate(['north','east']):
 d=r/f'joint_NE_B_{v}';j=json.load(open(d/'scope.json'));p=j['positions'];s=(d/'pilot.def').read_text()
 for col in range(2):
  ax=axs[row,col]
  for c in j['cores']:
   x,y,xx,yy=c['rect_um'];ax.add_patch(Rectangle((x,y),xx-x,yy-y,color='salmon',alpha=.35));ax.add_patch(Rectangle((x-4.32,y-4.32),xx-x+8.64,yy-y+8.64,fill=False,edgecolor='red',ls='--',lw=.6));ax.text(x,y,c['inst'].split('/')[-1],fontsize=5)
  for m in re.finditer(r'M([89]) (\d+) \+ SHAPE STRIPE \( (\d+) (\d+) \) \( (\d+) (\d+) \)',s):
   _,w,x,y,xx,yy=map(int,m.groups());ax.plot([x/1000,xx/1000],[y/1000,yy/1000],color='grey',alpha=.16,lw=.5)
  for ln in re.search(r'(?ms)^NETS.*?END NETS',s)[0].splitlines():
   pairs=re.findall(r'\( (\S+) (\S+) \)',ln);drv=[n for n,pin in pairs if pin=='Y']
   if not drv:continue
   x,y=p[drv[0]]
   for n,pin in pairs:
    if pin not in ['A','CLK']:continue
    xx,yy=p[n];ax.plot([x,xx],[y,yy],color='royalblue',lw=1)
  for n,(x,y) in p.items():
   ax.scatter(x,y,s=30 if n.startswith('start_') else 15,color='green' if n.startswith('start_') else 'black');ax.text(x,y+2,n,fontsize=6)
  ax.set_aspect('equal');ax.grid(alpha=.15)
  if col==0:ax.set_xlim(3675,4750);ax.set_ylim(545,735);ax.set_title(f'{v}: actual B feed + R/P1/P2 + three native START CLK loads; longest leg {max(z["length_um"] for z in j["legs"]):.2f}um')
  else:
   x,y=p['P2'];ax.set_xlim(x-8,x+13);ax.set_ylim(y-6,y+6);ax.set_title('P2 / native START island; M4 pin-access windows')
fig.tight_layout();fig.savefig(r/'joint_NE_B_review.png',dpi=160)
