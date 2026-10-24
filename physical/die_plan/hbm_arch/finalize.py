#!/usr/bin/env python3
"""HBM-ARCH: after gen_arch.py -- plan the die IO windows (die_io.py) and mark the host UCIe (host_N) as the host link."""
import json, subprocess, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
plan = sys.argv[1]
subprocess.run([sys.executable, os.path.join(HERE, '..', '..', '..', 'tools', 'die_plan', 'die_io.py'), 'plan', plan, '--inplace'],
               check=True, stdout=subprocess.DEVNULL)
P = json.load(open(plan))
# Reserve real bump fields at the partition shoreline, containing the digital PHY footprint.
# A 600-um digital SerDes core does not imply that its 26 off-die signals fit in a 4x4 C4 field.
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'tools', 'die_plan'))
import schema as S
import math
Q = S.Plan(P)
for window in P['die'].get('io', []):
    r = list(window['rect_um']); pitch = window['pitch_um']; pr = Q.rect(window['part'])
    edge = min(('W','E','S','N'), key=lambda e: {'W':pr[0], 'E':Q.W-pr[2], 'S':pr[1], 'N':Q.H-pr[3]}[e])
    if edge == 'W': r[0] = pr[0]
    elif edge == 'E': r[2] = pr[2]
    elif edge == 'S': r[1] = pr[1]
    else: r[3] = pr[3]
    sites = lambda z: math.floor((z[2]-z[0])/pitch+1e-8)*math.floor((z[3]-z[1])/pitch+1e-8)
    if sites(r) < window['signals']:
        opts=[]
        for nx in range(math.ceil((r[2]-r[0])/pitch-1e-8), math.floor((pr[2]-pr[0])/pitch+1e-8)+1):
            ny=max(math.ceil((r[3]-r[1])/pitch-1e-8),math.ceil(window['signals']/nx))
            if ny*pitch <= pr[3]-pr[1]+1e-6:opts.append((nx*ny,abs(nx*pitch-(r[2]-r[0]))+abs(ny*pitch-(r[3]-r[1])),nx,ny))
        if not opts:raise ValueError(f"no shoreline bump field fits {window['name']}")
        _,_,nx,ny=min(opts);w,h=nx*pitch,ny*pitch
        x=max(pr[0],min((r[0]+r[2]-w)/2,pr[2]-w));y=max(pr[1],min((r[1]+r[3]-h)/2,pr[3]-h))
        if edge=='W':x=pr[0]
        elif edge=='E':x=pr[2]-w
        elif edge=='S':y=pr[1]
        else:y=pr[3]-h
        r=[x,y,x+w,y+h]
    window['rect_um']=[round(v,4) for v in r]
    window['sites']=sites(r)
    window['basis'] += '; allocated shoreline bump field contains PHY footprint; sites recomputed at declared pitch'

for w in P['die'].get('io', []):
    w.pop('host', None)
    if w.get('iface') == 'ucie':
        w['host'] = True
        w['note'] = (w.get('note', '') + ' HBM-ARCH: as-built host link = host_N UCIe x64 (ot_pdie_ucie_col)').strip()
json.dump(P, open(plan, 'w'), indent=0)
print('io windows', [(w['name'], w.get('iface'), w['sites'], w['signals'], w.get('host', False)) for w in P['die']['io']])
