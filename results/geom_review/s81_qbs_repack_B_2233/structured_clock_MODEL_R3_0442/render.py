from pathlib import Path
import json
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path(__file__).parent;P=R/'inputs';ns=json.load(open(R/'nodes.json'));model=json.load(open(R/'model.json'));pins=json.load(open(P/'actual_clock_pins.json'));snap=json.load(open(P/'post_place_snapshot.json'));groups=json.load(open(R/'FF_region_assignments.json'));by={n['name']:n for n in ns};fig,(ax,b)=plt.subplots(1,2,figsize=(15,8),gridspec_kw={'width_ratios':[1.4,1]})
for m in snap['macros']:
 x,y,x1,y1=[v/1000 for v in m['bbox_dbu']];ax.add_patch(Rectangle((x,y),x1-x,y1-y,fc='#d8bc8b',ec='#775a2f',lw=.5))
ff=[p for p in pins if not p['macro']];ax.scatter([p['xy_dbu'][0]/1000 for p in ff],[p['xy_dbu'][1]/1000 for p in ff],s=.2,c='#8ca4b7',alpha=.45,rasterized=True)
for g in groups:
 x,y,x1,y1=g['rect'];ax.add_patch(Rectangle((x,y),x1-x,y1-y,fill=False,ec='#6d9cb6',lw=.4,alpha=.5))
for n in ns:
 if n['parent']in by:
  p=by[n['parent']]['xy_sized'];q=n['xy_sized'];ax.plot([p[0],q[0]],[p[1],q[1]],c='#2c7f52',lw=.6,alpha=.6)
 ax.plot(*n['xy_sized'],'o',ms=1.7,c='#1d653d')
mp=[p for p in pins if p['macro']];ax.scatter([p['xy_dbu'][0]/1000 for p in mp],[p['xy_dbu'][1]/1000 for p in mp],s=15,marker='s',c='black',label='32 actual macro CLK pins')
ax.plot(324.012,331.212,'r+',ms=10,label='unchanged centre M5 ck');ax.set(xlim=(0,648),ylim=(0,648),xlabel='µm',ylabel='µm');ax.set_aspect('equal');ax.legend(fontsize=7);ax.set_title(f"{len(groups)} FF domains / {len(ns)} proposed buffers\nLines show feed connectivity, not physical clock routes")
for c,col in [('TT','#186ba4'),('FF','#c77726')]:
 rows=model['corners'][c]['leaves'];b.errorbar(range(len(rows)),[x['mean_ps'] for x in rows],yerr=[[x['mean_ps']-x['min_ps']for x in rows],[x['max_ps']-x['mean_ps']for x in rows]],fmt='.',ms=2,lw=.4,label=c,c=col)
b.axhline(250,c='#186ba4',ls=':',lw=1);b.axhline(202.5,c='#c77726',ls=':',lw=1);b.set(xlabel='FF domains, then 32 macro PIN leaves',ylabel='model arrival ps');b.legend();b.set_title('Native directional M6/M7 RC, saved-SDC input 0 ps\nRegional calibration unchanged; no child internal insertion')
fig.suptitle('DISABLED hist R3 equal-structure SOURCE MODEL — NO CLOCK INSTALLATION\nSame 31,847 FF + 32 macros/pins/source/833 ps; actual data congestion and qualification holds remain',fontsize=11);fig.tight_layout();fig.savefig(R/'clock_model_R3_LOOK.png',dpi=160)
