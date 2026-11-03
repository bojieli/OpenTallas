import json,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
r=Path('/srv/opentallas-scratch/claude/wt/codex-kv-physical-2034/results/flow/kv_pc_geo80_birth_1102/result')
j=json.load(open('/home/ubuntu/coord/tmp/pc_geo80_checkpoint_points.json'));c=json.load(open(r/'CHECKPOINT_CENSUS.json'));a=np.array(j['real_cells'])
fig,ax=plt.subplots(figsize=(10,9));ax.hist2d(a[:,0],a[:,1],bins=(180,165),cmap='Blues',cmin=1)
for key,color,mark in [('new','red','o'),('changed','orange','x')]:
 b=np.array([[int(v.get('after',v)['pose'][1])/1000,int(v.get('after',v)['pose'][2])/1000] for v in c[key].values()]);ax.scatter(b[:,0],b[:,1],s=18,c=color,marker=mark,label=f'{len(b)} '+key+' cells')
ax.set(xlim=(0,397.44),ylim=(0,362.88),aspect='equal',xlabel='x (um)',ylabel='y (um)',title='Actual protected PC repair checkpoint before legalization')
ax.legend(loc='upper right');fig.text(.06,.025,'223,911 real cells / 1,312 rows / 0 unplaced; 63 created, 2 removed, 9 retained master changes.\nMultiple new buffers share sites: this is a repair checkpoint requiring DPL, not legal placement or fresh routed timing.\nClock: 4,261 nets and 48,012 clock-connected instances unchanged. Full in-process PG: 447,822 terminals / 0 opens.',fontsize=9)
fig.tight_layout(rect=(0,.09,1,1));fig.savefig(r/'actual_checkpoint.png',dpi=150)
