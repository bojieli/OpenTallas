from pathlib import Path
import json,re,numpy as np
import matplotlib.pyplot as plt
R=Path(__file__).parent;m=json.loads((R/'candidate100/irwin.json').read_text());x0,y0,x1,y1=m['window_um'];w,h=x1-x0,y1-y0
b=[(float(a),float(b))for a,b in re.findall(r'set bx \[expr \{([\d.]+)\*\$bump_dbu\}\]; set by \[expr \{([\d.]+)\*\$bump_dbu\}\]',(R/'candidate100/bumps.tcl').read_text())]
fig,ax=plt.subplots(figsize=(8,8),layout='constrained')
for g in m['grid']:
 horizontal=g['layer']=='M8'
 for z in np.arange(g['offset_um'],h if horizontal else w,g['pitch_um']/2):
  ax.plot([0,w]if horizontal else[z,z],[z,z]if horizontal else[0,h],c='#557688'if horizontal else'#b97a44',lw=.3,alpha=.25)
for x,y in b:ax.scatter(x,y,s=35,c='black',marker='s')
ax.set(xlim=(0,w),ylim=(0,h),aspect='equal',xlabel='Window x (um)',ylabel='Window y (um)',title=f'Core PG candidate:100um C4, unchanged M8/M9 grid\n{m["power_w"]}W;{m["bumps_vdd"]} VDD/{m["bumps"]-m["bumps_vdd"]} ground sources; budget35mV\nLowest published C4 pitch assumption; no adopted plan')
fig.savefig(R/'core100_review.png',dpi=155)
