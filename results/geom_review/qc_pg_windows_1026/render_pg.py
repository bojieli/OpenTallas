from pathlib import Path
import json,re
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path(__file__).parent
fig,axes=plt.subplots(2,2,figsize=(13,11),layout='constrained')
for row,n in enumerate(['core_centre','io_ucie_kv_u_ucie_kv']):
 d=R/'psm'/n;m=json.loads((d/'irwin.json').read_text());x0,y0,x1,y1=m['window_um'];w,h=x1-x0,y1-y0
 t=(d/'psm/bumps.tcl').read_text();b=[(float(a),float(b)) for a,b in re.findall(r'set bx \[expr \{([\d.]+)\*\$bump_dbu\}\]; set by \[expr \{([\d.]+)\*\$bump_dbu\}\]',t)]
 for j,ax in enumerate(axes[row]):
  lim=[0,w,0,h] if j==0 else [max(0,w/2-70),w/2+70,max(0,h/2-70),h/2+70]
  for g in m['grid']:
   p=g['pitch_um'];off=g['offset_um'];horizontal=g['layer']=='M8'
   span=h if horizontal else w
   for z in np.arange(off,span,p/2):
    if horizontal:
     if lim[2]<=z<=lim[3]:ax.plot([lim[0],lim[1]],[z,z],color='#24658c',lw=.3 if j==0 else 1,alpha=.32)
    else:
     if lim[0]<=z<=lim[1]:ax.plot([z,z],[lim[2],lim[3]],color='#bf6838',lw=.3 if j==0 else 1,alpha=.32)
  for k,(x,y) in enumerate(b):ax.scatter(x,y,s=16 if j==0 else 50,c='#b60000' if k%2==0 else '#111',marker='s',zorder=4)
  if row==1:
   ax.add_patch(Rectangle((0,9244.8-y0),777.6,777.6,fill=False,ec='#990099',lw=2,zorder=5))
  ax.set(xlim=lim[:2],ylim=lim[2:],aspect='equal',xlabel='Local x (um)',ylabel='Local y (um)',title=f'{n}: '+('whole window' if j==0 else '140 um detail'))
 axes[row,0].text(.01,.99,f'{m["power_w"]} W; {m["bumps_vdd"]} VDD sources\nmodel max {m["est_worst_mv"]} mV; budget 35 mV',transform=axes[row,0].transAxes,va='top',bbox=dict(fc='white',alpha=.9))
fig.suptitle('QC infrastructure-first PG window review: M8 0.48/2.88 um, M9 0.48/1.728 um\nBlue horizontal=M8; orange vertical=M9; squares=supply-source sites; purple=UCIe window')
fig.savefig(R/'qc_pg_window_review.png',dpi=160)
