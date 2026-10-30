from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
b=Path(__file__).parent;homes={}
for l in (b/'ff_homes.tsv').read_text().splitlines():
 a=l.split('\t')
 if a[0]=='CELL':homes[a[1].replace('\\','')]=[(int(a[3])+int(a[5]))/2000,(int(a[4])+int(a[6]))/2000]
fig,ax=plt.subplots(figsize=(14,8));ax.add_patch(Rectangle((0,0),293.76,155.52,fill=False,lw=2))
for x,y in [(17.28,17.28),(159.84,17.28),(17.28,90.72),(159.84,90.72)]:
 ax.add_patch(Rectangle((x,y),94.824,41.064,facecolor='#dedede',edgecolor='#555555'));ax.text(x+47,y+20,'SRAM',ha='center',color='#777777')
ax.scatter(*zip(*homes.values()),s=1.6,color='#2166ac',alpha=.3,label='actual final FF centres')
for r in json.load((b/'drv_measured_nets.json').open())['nets']:
 c=lambda e:((e['bbox'][0]+e['bbox'][2])/2,(e['bbox'][1]+e['bbox'][3])/2)
 if not r['drivers']:continue
 p=c(r['drivers'][0])
 for e in r['loads']:
  q=c(e);ax.plot([p[0],q[0]],[p[1],q[1]],color='#e08214',lw=.7,alpha=.45)
pairs=[('ptw_data[153]$_DFF_P_','u_twpd/q[153]$_DFF_P_',-2.5896),('ptw_data[145]$_DFF_P_','u_twpd/q[145]$_DFF_P_',-2.4310),('u_twpd/q[247]$_DFF_P_','g_btb[0].g_r.u_wd/q[247]$_DFF_P_',-1.5967)]
rows=[]
for a,z,s in pairs:
 p,q=homes[a],homes[z];ax.annotate('',q,p,arrowprops=dict(arrowstyle='->',color='#762a83',lw=2));rows.append(dict(source=a,sink=z,slack_ps=s,source_xy=p,sink_xy=q))
ax.plot([131.706,270.675],[91.935,90.855],'--',color='red',lw=1.3,label='net3486 endpoint proxy (not routed shape)');ax.scatter([160.51],[98.652],s=120,marker='x',lw=2.5,color='red',label='actual M4/V4 DRC3 window')
ax.scatter([256.77],[5.265],s=100,marker='*',color='#008837',label='proposed source output home = existing late clone');ax.annotate('fault face home / +1 source CLK load\nexisting physical late clone must be accounted',(256.77,5.265),(146,-18),arrowprops=dict(arrowstyle='->'),fontsize=9)
ax.set(xlim=(-5,300),ylim=(-28,162),xlabel='x (um)',ylabel='y (um)',title='BTAB C measured failures + proposed repair scope (no repair executed)\n73 bad data nets; three FF hold paths; fixed pins/outline/macros/clock trunk')
ax.set_aspect('equal');ax.legend(loc='upper left',fontsize=8);ax.grid(alpha=.15);fig.tight_layout();fig.savefig(b/'repair_scope.png',dpi=150)
(b/'hold_endpoints.json').write_text(json.dumps(rows,indent=2)+'\n')
