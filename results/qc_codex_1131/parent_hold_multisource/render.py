from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
b=Path(__file__).resolve().parent
fig,ax=plt.subplots(figsize=(12,6));ax.add_patch(Rectangle((0,0),120.96,60.48,fill=False,lw=2))
for inst,master,x in [('u_send','hold_tx',17.28),('u_r0.u_bs0','hold_rx',51.84),('u_other','hold_tx',86.4)]:
 ax.add_patch(Rectangle((x,17.28),17.28,17.28,facecolor='#d9e8ff',edgecolor='navy'));ax.text(x+8.64,26,inst+'\n'+master,ha='center',fontsize=10)
ax.annotate('a[1:0]',xy=(51.84,29),xytext=(34.56,29),arrowprops={'arrowstyle':'->'},ha='center')
ax.scatter([42],[45],marker='s',s=70,color='orange');ax.text(42,47,'parent glue FF b[1:0]',ha='center');ax.annotate('',xy=(51.84,31),xytext=(42,45),arrowprops={'arrowstyle':'->','color':'orange'})
for name,x,early,dests,color in [('clk_send',17.28,-35,[(25.92,17.28),(42,45)],'green'),('clk_recv',77.76,-85,[(60.48,17.28),(95.04,17.28)],'purple')]:
 ax.plot(x,.096,'o',color=color);ax.text(x,3,f'{name}\nearly {early}ps / late 0',ha='center',color=color)
 for dx,dy in dests:ax.annotate('',xy=(dx,dy),xytext=(x,.096),arrowprops={'arrowstyle':'->','linestyle':'--','color':color})
ax.text(60.48,57,'One 833ps clk domain, two exact source ports; TT setup 0ps / FF hold 25ps',ha='center');ax.text(60.48,53,'Existing actual routed child V/SPEF + TT/FF models; M7 child PG → M8 parent straps',ha='center',fontsize=10)
ax.set(xlim=(-5,126),ylim=(-3,64),aspect='equal',xlabel='µm',ylabel='µm');fig.tight_layout();fig.savefig(b/'planned_geometry.png',dpi=140)
