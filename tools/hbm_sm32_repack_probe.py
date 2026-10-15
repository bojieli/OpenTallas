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


def repack(model, probe):
    """Construct the full count-preserving relocation, using only source outlines.

    Endpoint moves use existing empty core rows; the large SW collective moves
    above the north compute band. Four small attention rows move 43.2um inward.
    This changes placement and therefore requires complete pin/routing/timing
    regeneration; no old route or clock plan is transferable proof.
    """
    insts = pickle.loads(model.read_bytes())['insts']
    blocks = {n: list(v) for n, v in insts.items() if v[1] != 'waypoint'}
    for item in probe['proposed_sms']:
        blocks[item['name']][2:7] = item['box_um'] + [item['orient']]
    moves = {
        'ep_S0': (11175.84,7045.92), 'ep_S1': (18761.76,7045.92),
        'ep_S4': (16139.52,7045.92), 'ep_N0': (16665.408,20008.08),
        'ep_N1': (13262.4,19135.44), 'ep_N2': (15884.64,19135.44),
        'ep_N3': (18506.88,19135.44), 'hb_coll_NW': (11175.84,12474.72),
        'hb_coll_SE': (18932.544,12474.72), 'hb_coll_SW': (10986.912,18325.44),
    }
    for name, v in blocks.items():
        if name.startswith(('at_SW_0','at_SE_0')):
            moves[name] = (v[2], round(v[3]+43.2,4))
        if name.startswith(('at_NW_1','at_NE_1')):
            moves[name] = (v[2], round(v[3]-43.2,4))
    moves = {n: (round(round(x/.864)*.864,4),round(round(y/2.16)*2.16,4))
             for n,(x,y) in moves.items()}
    for name, xy in moves.items():
        blocks[name][2:4] = xy
    overlaps, outside = [], []
    names = sorted(blocks)
    for i, name in enumerate(names):
        _, _, x, y, w, h, _ = blocks[name]
        if x < 0 or y < 0 or x+w > 32984.288+1e-6 or y+h > 25980.528+1e-6:
            outside.append(name)
        for peer in names[i+1:]:
            _, _, bx, by, bw, bh, _ = blocks[peer]
            if x < bx+bw-1e-6 and bx < x+w-1e-6 and y < by+bh-1e-6 and by < y+h-1e-6:
                overlaps.append([name,peer])
    assert len([v for v in blocks.values() if v[1]=='sm']) == 32
    assert len(blocks) == probe['retained_non_sm_count']+32
    return dict(status='GEOMETRIC_CANDIDATE_NOT_PHYSICALLY_QUALIFIED',
                retained_master_instances=len(blocks), sm_count=32,
                non_sm_removed=[], non_sm_resized=[], orientation_90_count=0,
                moved_non_sm_count=len(moves), moved_non_sm={n: dict(old_xy_um=list(insts[n][2:4]),
                new_xy_um=list(xy)) for n,xy in moves.items()},
                overlaps=overlaps,outside=outside,instances=blocks,
                moved_origins_lattice_um=[.864,2.16],
                moved_origins_off_lattice=[n for n,(x,y) in moves.items() if
                    abs(x/.864-round(x/.864))>1e-4 or abs(y/2.16-round(y/2.16))>1e-4],
                limitations=['compact tile outline is a plan pending real route',
                             'all displaced endpoint/collective and attention paths need new static cycle prices',
                             'pin faces, PG, detailed cut capacity, clocks and timing are unverified',
                             'large SW collective moved to north core: logical quadrant reach must be repriced'])


if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--model',type=Path,required=True)
    ap.add_argument('--compact',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    result=run(args.model,args.compact)
    result['full_repack_candidate']=repack(args.model,result)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=1)+'\n')
    print(json.dumps({k:result[k] for k in ('sm_count','total_sm_mm2','outside')}))
    print('Repack:',{k:result['full_repack_candidate'][k] for k in ('retained_master_instances','sm_count','overlaps','outside')})
    print('Original obstructions:',', '.join(result['unique_obstructions']))
