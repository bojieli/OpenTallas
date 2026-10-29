import sys,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0,'tools/autopilot');import geom_rules as g
# Usage: render_final.py actual_geom.tsv [output.png]
D=g.Design(sys.argv[1])
targets={line.split('\t')[0] for line in open('results/head_tile_relays_1029/targets_copy_result.tsv')}
fig,ax=plt.subplots(figsize=(8,11))
for c in D.cells.values():
 if c[0]=='M':ax.add_patch(Rectangle(c[2:4],c[4]-c[2],c[5]-c[3],fc='#ddd',ec='#555',hatch='//'))
for selected,color,size,label in [(False,'#999',.2,'other sequential cells'),(True,'#0065a8',3,'2440 existing/copied stage targets')]:
 cs=[c for c in D.cells.values() if c[0]=='S' and (c[6] in targets)==selected]
 ax.scatter(*zip(*(g.ctr(c) for c in cs)),s=size,c=color,alpha=.4,label=label)
for prefix,label in [('u_cland_origin/s0$','START sampler'),('u_cland_rst_i/q$','raw reset'),('u_cland_origin/s1$','S1'),('u_cland_origin/s2$','original S2'),('u_cland_origin/g_export.g_copy[0].u_copy/q$','export copy'),('u_cland_fstart_o/q$','START output FF'),('u_core.o_row[','held result stage')]:
 c=next(c for c in D.cells.values() if c[6].replace('\\','').startswith(prefix));p=g.ctr(c);ax.scatter(*p,s=20,c='#d14900');ax.annotate(label,p,xytext=(-100 if p[0]>600 else 8,12),textcoords='offset points',fontsize=7)
ax.set(xlim=(0,708.48),ylim=(0,1036.8),xlabel='um',ylabel='um',title='HEAD tile actual fresh DPL: 0 captures >405um, max400.95um\nSource-integrated placement; no clock/route qualification')
ax.set_aspect('equal');ax.legend(loc='upper right',fontsize=7);fig.tight_layout();fig.savefig(sys.argv[2] if len(sys.argv)>2 else 'results/head_tile_relays_1029/final_place.png',dpi=150)
