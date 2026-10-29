#!/usr/bin/env python3
"""Normalize actual both-edge HBM readout; fit tap wire coefficients on native routed taps.

N raw columns are maxrise,maxfall,minrise,minfall,slewA,slewY.
T raw columns are maxrise,minrise,maxfall,minfall,slewR,slewF.
Only source-rise logical node endpoints are consumed by the shared early-stage fitter.
"""
from pathlib import Path
import json
import numpy as np
HERE=Path(__file__).resolve().parent
raw=HERE/'raw';tree=json.loads((raw/'tree_frozen.json').read_text())
taps={};stats={}
for corner in ('TT','FF'):
    nodes={}
    for line in (raw/f'nodes_{corner}.txt').read_text().splitlines():
        p=line.split()
        if p and p[0]=='N':
            if len(p)!=8:raise ValueError(f'unexpected node columns {line}')
            nodes[p[1]]=tuple(map(float,p[2:]))
    out=HERE/f'actual_{corner}';out.mkdir(exist_ok=True)
    # Preserve actual early rise, not the old read_node_early mistaken max-fall column.
    (out/f'arr_{corner}.txt').write_text(''.join(f'N {name} {x[0]:.9f} {x[2]:.9f}\n' for name,x in nodes.items()))
    arrivals={}
    for line in (raw/f'arr_{corner}.txt').read_text().splitlines():
        p=line.split()
        if p and p[0]=='T':
            if len(p)!=8:raise ValueError(f'unexpected tap columns {line}')
            arrivals[p[1]]=tuple(map(float,p[2:]))
    rows=[]
    for t in tree['taps']:
        cell=tree['node_buf'][str(t['node'])];xy=tree['sites'][cell]
        length=abs(xy[0]-t['xy'][0])+abs(xy[1]-t['xy'][1])
        rows.append((length,arrivals[t['port']][1]-nodes[cell][2],t['port']))
    X=np.array([[length,length*length] for length,_,_ in rows]);y=np.array([delay for _,delay,_ in rows])
    coef,*_=np.linalg.lstsq(X,y,rcond=None);res=y-X@coef
    taps['tap' if corner=='TT' else 'tap_FF']=[float(x) for x in coef]
    stats[corner]=dict(taps=len(rows),length_min_um=min(r[0] for r in rows),length_max_um=max(r[0] for r in rows),rms_ps=float(np.sqrt(np.mean(res**2))),max_abs_resid_ps=float(np.max(np.abs(res))),rows=[dict(port=p,length_um=L,early_delay_ps=d) for L,d,p in rows])
(HERE/'tap_actual.json').write_text(json.dumps(dict(**taps,source='actual GRT NW_sm3 1x tap rise-early minus native logical-node rise-early; least squares no intercept',fit=stats),indent=1)+'\n')
print(json.dumps({c:{k:v for k,v in s.items() if k!='rows'} for c,s in stats.items()},indent=1))
