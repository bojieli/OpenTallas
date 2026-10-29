#!/usr/bin/env python3
"""DIE-KV-31-SRC: die map of PG access ok/failed rail groups over die M7 BLOCK OBS (ft-band share stripes) + zoom."""
import json,sys
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ov,pl,out=sys.argv[1:4];ov=json.load(open(ov));pl=json.load(open(pl+'/access_plan.json'));D=pl['dbu']
m7=[o[2:] for o in ov['obstructions'] if o[0]=='BLOCK' and o[1]=='M7']
ok=[q['rail'] for q in pl['paths']];bad=[q['rail'] for q in pl['failed']]
fig,aa=plt.subplots(1,2,figsize=(16,11),constrained_layout=True)
zx,zy=(1000,1250),(5250,5450)
for a,zoom in zip(aa,[False,True]):
  for r in m7:
    if zoom and (r[2]/D<zx[0] or r[0]/D>zx[1]):continue
    a.add_patch(Rectangle((r[0]/D,r[1]/D),(r[2]-r[0])/D,(r[3]-r[1])/D,color='#f4c27a',alpha=.5,lw=0))
  for rr,c,l in [(ok,'#2a9d4b','ok'),(bad,'#d62728','failed')]:
    xs=[(r[0]+r[2])/2/D for r in rr];ys=[(r[1]+r[3])/2/D for r in rr]
    a.scatter(xs,ys,s=(4 if zoom else .3),color=c,label=f'{l} {len(rr):,}',rasterized=True)
  if zoom:a.set_xlim(*zx);a.set_ylim(*zy);a.set_title('zoom: rails vs M7 band-share BLOCK OBS (orange)')
  else:a.set_xlim(0,11076.48);a.set_ylim(0,27043.2);a.set_title(f"KV std-cell PG access: ok {len(ok):,} / failed {len(bad):,} groups; orange = die M7 BLOCK OBS");a.legend(loc='upper right',markerscale=10)
  a.set_aspect('equal' if not zoom else 'auto');a.set_xlabel('um');a.set_ylabel('um')
fig.savefig(out,dpi=110)
