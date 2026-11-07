import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as p
from matplotlib.patches import Rectangle
fig,ax=p.subplots(figsize=(12,6))
for name,x0,y0,x1,y1 in [('CHN',967.68,317.568,1244.16,455.808),('DMEM',1258.848,365.052,1437.48,446.052),('CMEM',1448.928,365.052,1626.696,446.052),('PMA RX',319.272,952.56,2565.672,1082.16),('PMA TX',319.272,1092.96,2565.672,1222.56)]:
 ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor='#ddd',edgecolor='#777'));ax.text((x0+x1)/2,(y0+y1)/2,name,ha='center',va='center')
for name,x0,y0,x1,y1,c in [('Measured ENC span',1646,336,2482,875,'#ffbf72'),('Proposed ENC',2065,466,2265,666,'#32a875'),('Proposed BIN',2770,105,2874,265,'#458ddd')]:
 ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor=c,alpha=.28,edgecolor=c,ls='--' if name.startswith('Measured') else '-'));ax.text((x0+x1)/2,y0+12,name,ha='center',fontsize=9)
ax.scatter([2164.832,2868.96],[566.048,17.312],c=['green','blue'],marker='x',s=70)
ax.text(2868,25,'clk32',ha='right');ax.text(2165,575,'clk34',ha='center')
# Conservative corner trajectories illustrate relay count, not measured new placement.
for a,b,n,c in [((2865,250),(2065,650),3,'#256fbc'),((2265,650),(338.856,1093.056),7,'#ce4e68')]:
 pts=[(a[0]+(b[0]-a[0])*j/(n+1),min(a[1]+(b[1]-a[1])*j/(n+1),945.24)) for j in range(n+1)]+[b]
 ax.plot(*zip(*pts),c=c,lw=1);ax.scatter(*zip(*pts[1:-1]),c=c,s=18)
ax.axhline(945.24,color='#777',ls=':',lw=1);ax.text(50,934,'soft-cell ceiling 945.24 um',fontsize=9)
ax.text(1450,1050,'M6/M7 overpass legal: RX OBS M1–M5',ha='center',fontsize=9)
ax.set(xlim=(0,3000),ylim=(1250,-30),xlabel='x (um)',ylabel='y (um)',title='RCK t16 TX redesign — planned geometry, not new placement\n3 coherent input stages; TXL 2 → 7; ENC measured cone 10,564.5 um² / 40,000 um² = 26.4%')
ax.set_aspect('equal');fig.tight_layout();fig.savefig('/tmp/codex-rck-redesign-1107/rck_tx_planned_geometry.png',dpi=160)
