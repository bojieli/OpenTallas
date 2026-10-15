#!/usr/bin/env python3
"""Construct a count-preserving R0/MX SM packing probe against actual die masters.

Reports all obstructing native blocks; never drops, moves, or substitutes them.
The old fixed-field R90 fit cannot prove a 32-SM die infeasible. This probe is
an explicit relocation work list, not a pin/cut/clock or die closure receipt.
"""
import argparse
import hashlib
import json
import math
import pickle
from pathlib import Path


def run(model, compact, clearance=21.6):
    raw = model.read_bytes()
    insts = pickle.loads(raw)['insts']
    sm = json.loads(compact.read_text())['sm']
    w, h = sm['compact_frame_um']
    gx, gy = .864, 2.16
    up = lambda x, g: round(math.ceil((x-1e-7)/g)*g, 4)
    dn = lambda x, g: round(math.floor((x+1e-7)/g)*g, 4)
    px, py = up(w+clearance, gx), up(h+clearance, gy)
    blocks = {n: v for n, v in insts.items() if v[1] not in ('waypoint', 'sm')}
    # Shoreline PHY/service and host strip stay fixed. Two columns x four rows
    # per quadrant replace the old 3+3+2 field. No cell or SM is rotated 90deg.
    west = up(clearance, gx)
    east_edge = min(v[2] for v in blocks.values() if v[1] == 'host_slab')-clearance
    east = dn(east_edge-w-px, gx)
    south_edge = max(v[3]+v[5] for v in blocks.values() if v[1]=='svc' and v[3]<10000)
    north_edge = min(v[3] for v in blocks.values() if v[1]=='svc' and v[3]>20000)
    south = up(south_edge+clearance, gy)
    north = dn(north_edge-clearance-h-3*py, gy)
    proposed, conflicts = [], {}
    for q, base, x0, y0, orient in [('SW',0,west,south,'MY'),('SE',8,east,south,'R0'),
                                   ('NW',16,west,north,'R180'),('NE',24,east,north,'MX')]:
        for row in range(4):
            for col in range(2):
                name = f'sm{base+2*row+col}'
                x, y = round(x0+col*px,4), round(y0+row*py,4)
                hit=[]
                for n, v in blocks.items():
                    _, kind, bx, by, bw, bh, _ = v
                    if x-clearance < bx+bw and bx < x+w+clearance and y-clearance < by+bh and by < y+h+clearance:
                        hit.append(n)
                        conflicts[n] = dict(kind=kind, box_um=[bx,by,bw,bh])
                proposed.append(dict(name=name, quadrant=q, box_um=[x,y,w,h], orient=orient, conflicts=hit))
    sm_overlaps = []
    for i, p in enumerate(proposed):
        x, y, _, _ = p['box_um']
        for q in proposed[i+1:]:
            bx, by, _, _ = q['box_um']
            if x < bx+w and bx < x+w and y < by+h and by < y+h:
                sm_overlaps.append([p['name'],q['name']])
    return dict(schema='opentallas.hbm.sm32_repack_probe.v1',status='RELOCATION_REQUIRED_NOT_QUALIFIED',
                model_sha256=hashlib.sha256(raw).hexdigest(),compact_sha256=hashlib.sha256(compact.read_bytes()).hexdigest(),
                sm_count=32, sm_outline_um=[w,h], clearance_um=clearance,
                outline_limit_um=[32984.288,25980.528], total_sm_mm2=32*w*h/1e6,
                retained_non_sm_count=len(blocks), dropped_non_sm_count=0,
                rotated_90_count=0, sm_overlap_count=len(sm_overlaps), sm_overlaps=sm_overlaps,
                outside=[p['name'] for p in proposed if p['box_um'][0]<0 or p['box_um'][1]<0 or
                         p['box_um'][0]+w>32984.288 or p['box_um'][1]+h>25980.528],
                unique_obstructions=conflicts, proposed_sms=proposed,
                required_gates=['relocate every obstruction without new overlap','pin geometry and source ABI',
                                'static cycle schedule including all transport','cut capacity and GRT overflow0',
                                'real-view die TT setup/FF hold and DRC0'])


if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--model',type=Path,required=True)
    ap.add_argument('--compact',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    result=run(args.model,args.compact)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=1)+'\n')
    print(json.dumps({k:result[k] for k in ('sm_count','total_sm_mm2','outside')}))
    print('Obstructions:',', '.join(result['unique_obstructions']))
