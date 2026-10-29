import json,pathlib,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle
R=pathlib.Path(__file__).resolve().parent;rec=json.load(open(R/'input/plan_d1.json'))[0];s=json.load(open(R/'slice/ot_v41_bf_col.json'))
fig,ax=plt.subplots(figsize=(12,6));paths=[p for w in rec['wire_paths'] for p in w['paths']];ax.add_collection(LineCollection(paths,colors='#3b86b5',linewidths=.35,alpha=.6))
pts=[list(map(float,l.split()[1:3])) for l in open(R/'input/geo_entry.txt') if l.startswith('SINK')];ax.scatter([p[0] for p in pts],[p[1] for p in pts],s=.08,color='#777777',alpha=.45,label='53852 clock sinks')
for l in open(R/'input/sites.txt'):
 f=l.split()
 if f and f[0]=='FIXED':
  a,b,c,d=map(float,f[-4:])
  if d-b>5:ax.add_patch(Rectangle((a,b),c-a,d-b,facecolor='#e9dac2',edgecolor='#886844',alpha=.8))
ns=s['core_tree']['nodes'];gs=s['core_tree']['gates'];ax.scatter([p['xy_um'][0] for p in ns],[p['xy_um'][1] for p in ns],s=.6,c='#174e72',label=f'{len(ns)} planned buffers')
ax.scatter([p['xy_um'][0] for p in gs],[p['xy_um'][1] for p in gs],s=1.7,c='#9e3063',label=f'{len(gs)} planned ICG stages')
ax.scatter([273.228],[95.58],marker='*',s=150,c='#ff6600',label='explicit M5 clock entry')
ax.set_xlim(0,450.168);ax.set_ylim(0,198.72);ax.set_aspect('equal');ax.set_xlabel('core x (um)');ax.set_ylabel('core y (um)');ax.legend(fontsize=7);ax.set_title('BF G2 restored native gap: planned ICG tree, TT39.25 / FF33.21ps window INFO\n450.168 x198.72 um; unchanged RTL/clock period/uncertainties; no route or signoff claim');fig.tight_layout();fig.savefig(R/'review/bf_icg_g2.png',dpi=160)
