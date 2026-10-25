"""Plan fixed FT station bands along Manhattan legs, including every knee.

Soft station-only types lack hard-core corridors. Fractional arclength siting of
each pin bit bends an entire bank into a diagonal. Here one common rectilinear
spine fixes each bank's target, then a row allocator gives every bit a legal
explicit site. Existing stage depth is never reduced. Extra depth is returned
in the ledger for the plan/compiler owner to price before adoption.
"""
import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import schema as S
from gen_phys import type_pins
from tools.die_trial.legal_sites import RowAllocator


def spine(a, b, in_face, out_face, collapse=True):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if collapse and np.min(np.abs(a - b)) < 1e-6:
        return [a, b]
    if (in_face in 'EW') != (out_face in 'EW'):
        knee = np.array([b[0], a[1]]) if in_face in 'EW' else np.array([a[0], b[1]])
        return [a, knee, b]
    if in_face in 'EW':
        mid = (a[0] + b[0]) / 2
        return [a, np.array([mid, a[1]]), np.array([mid, b[1]]), b]
    mid = (a[1] + b[1]) / 2
    return [a, np.array([a[0], mid]), np.array([b[0], mid]), b]


def targets(polyline, depth, pitch=403.):
    out = [polyline[0]]
    for a, b in zip(polyline, polyline[1:]):
        n = max(1, math.ceil(np.abs(b-a).sum()/pitch))
        out.extend(a+(b-a)*i/n for i in range(1, n+1))
    while len(out)-1 < depth:
        j = max(range(len(out)-1), key=lambda i: np.abs(out[i+1]-out[i]).sum())
        out.insert(j+1, (out[j]+out[j+1])/2)
    return out


def targets_arclength(polyline, depth, pitch=403.):
    """Stations at uniform arclength along the whole Manhattan spine (no forced bank at the knee).
    A short first/last leg otherwise costs a whole bank at its knee (slice_station t23: +1 cycle on 3 slots)."""
    segs = list(zip(polyline, polyline[1:]))
    lens = [float(np.abs(b-a).sum()) for a, b in segs]
    total = sum(lens)
    n = max(depth, math.ceil(total/pitch))
    out = [polyline[0]]
    for k in range(1, n):
        s = total*k/n
        for (a, b), l in zip(segs, lens):
            if s <= l+1e-9:
                out.append(a+(b-a)*(s/l if l else 0.))
                break
            s -= l
    out.append(polyline[-1])
    return out


def _allocate_candidate(allocator, a, b, in_face, out_face, depth, reach, radius, end_anchor, tfun=targets):
    common_spine = spine(a.mean(axis=0), end_anchor, in_face, out_face)
    path = tfun(common_spine, depth)
    # per-bit spines keep the common spine shape (a bit aligned with its out pin would collapse to 2 points
    # while the common spine has a knee -> IndexError in requested())
    bits = [spine(x,y,in_face,out_face,collapse=False) for x,y in zip(a,b)]
    if len(common_spine)==2:bits=[[x,y] for x,y in zip(a,b)]
    def requested(target):
        choices=[]
        for j,(left,right) in enumerate(zip(common_spine,common_spine[1:])):
            length=float(np.abs(right-left).sum())
            frac=0. if length<1e-8 else float(np.abs(target-left).sum()/length)
            if frac<=1+1e-7 and np.abs(left+(right-left)*frac-target).sum()<1e-6:
                choices.append((j,frac))
        if not choices:raise ValueError('station target left the shared Manhattan spine')
        segment,frac=choices[0]
        pts=np.array([p[segment]+(p[segment+1]-p[segment])*frac for p in bits])
        along=int(np.argmax(np.abs(common_spine[segment+1]-common_spine[segment])))
        pts[:,along]=target[along]
        return pts,segment,frac
    used = set(allocator.used)
    for _ in range(30):
        allocator.used = set(used)
        banks, stats = [], []
        for target in path[1:-1]:
            desired,segment,frac=requested(target)
            points=[];max_shift=0.
            for xy in desired:
                point,stat=allocator.allocate(xy,1,max_radius_um=radius)
                points.append(point[0]);max_shift=max(max_shift,stat['max_distance_um'])
            points=np.asarray(points);banks.append(points)
            stats.append(dict(count=len(points),max_distance_um=max_shift,
                              span_um=np.ptp(points,axis=0).tolist(),spine_segment=segment,fraction=frac))
        chain = [a, *banks, b]
        hops = [float(np.abs(q-p).sum(axis=1).max()) for p,q in zip(chain, chain[1:])]
        # the die plan (check.py lane_geometry) measures bank-centroid to pin-window hops: keep those in reach too
        cent = [c.mean(axis=0) for c in chain]
        hops = [max(h, float(np.abs(q-p).sum())) for h,p,q in zip(hops, cent, cent[1:])]
        if max(hops, default=0) <= reach-2.0:
            return path, banks, stats, hops
        j = max(range(len(hops)), key=hops.__getitem__)
        path.insert(j+1, (path[j]+path[j+1])/2)
    raise ValueError('paired pin-bit reach cannot fit after 30 spine refinements')


def allocate_bank_chain(allocator, a, b, in_face, out_face, depth, reach=405., radius=40.):
    # A turn bank can sit anywhere across the outgoing pin window. Test its
    # centre and both edges before adding a cycle; wide bit windows often fit
    # the existing depth when the shared knee is moved toward one edge.
    anchors=[b.mean(axis=0)]
    if (in_face in 'EW') != (out_face in 'EW'):
        axis=1 if out_face in 'EW' else 0
        for edge in (float(b[:,axis].min()),float(b[:,axis].max())):
            for offset in (-8.64,0.,8.64):
                p=b.mean(axis=0)
                p[axis]=min(max(edge+offset,allocator.bounds[axis]+4.32),allocator.bounds[axis+2]-4.32)
                anchors.append(p)
    used=set(allocator.used);candidates=[]
    for anchor,tfun in [(an,tf) for tf in (targets,targets_arclength) for an in anchors]:
        allocator.used=set(used)
        try:
            result=_allocate_candidate(allocator,a,b,in_face,out_face,depth,reach,radius,anchor,tfun)
        except ValueError:
            continue
        candidates.append((result,set(allocator.used)))
    if not candidates:
        allocator.used=used
        raise ValueError('no rowlegal shared-knee candidate fits the actual bit reach')
    result,occupied=min(candidates,key=lambda v:(len(v[0][1]),max(v[0][3]),
                                                 sum(x['max_distance_um'] for x in v[0][2])))
    allocator.used=occupied
    return result


def place(raw, names):
    model = S.Plan(raw)
    ledger = []
    for name in names:
        ty = raw['partition_types'][name]
        if ty.get('hard_cores'):
            raise ValueError(f'{name}: use core corridor allocator for types with hard cores')
        w,h = ty['outline_um']
        pins = {(bus,bit):(x,y) for bus,bit,_,x,y,_ in type_pins(model,name)}
        allocator = RowAllocator((4.32,4.32,w-4.32,h-4.32), cell_size=(1.404,.27),
                                 column_pitch=2.16,row_pitch=.27,origin=(4.32,4.32))
        for slot in sorted(ty['ft_slots'], key=lambda x:-x['width']):
            a = np.array([pins[(slot['name']+'_i',i)] for i in range(slot['width']+1)])
            b = np.array([pins[(slot['name']+'_o',i)] for i in range(slot['width']+1)])
            old = slot['stations']
            path,banks,stats,hops = allocate_bank_chain(allocator,a,b,slot['in_face'],slot['out_face'],old)
            slot['stations'] = len(banks)+1
            # station 0 at the in-pin centroid, then each bank at its ALLOCATED centroid (the die plan measures hops
            # between these; the spine target can sit a half bank-width off the bits when the knee anchor is moved)
            slot['regs_um'] = [v.round(6).tolist() for v in [path[0], *[bk.mean(axis=0) for bk in banks]]]
            slot['bit_site_cell_um'] = [1.404,.27]
            slot['bit_sites_um'] = [(p-np.array([.702,.135])).round(6).tolist() for p in banks]
            ledger.append(dict(type=name,slot=slot['name'],old_stations=old,new_stations=slot['stations'],
                               added_cycles=slot['stations']-old,worst_paired_bit_um=max(hops),
                               targets_um=[v.tolist() for v in path],bank_stats=stats,
                               added_flops=(slot['stations']-old)*(slot['width']+1)))
    return ledger


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan');ap.add_argument('--types',required=True)
    ap.add_argument('--out',required=True);ap.add_argument('--ledger',required=True)
    args=ap.parse_args()
    raw=json.loads(Path(args.plan).read_text())
    ledger=place(raw,args.types.split(','))
    Path(args.out).write_text(json.dumps(raw,indent=0)+'\n')
    Path(args.ledger).write_text(json.dumps(ledger,indent=1)+'\n')
    print(f"{len(ledger)} slots: max hop {max(v['worst_paired_bit_um'] for v in ledger):.3f}um, "
          f"+{sum(v['added_flops'] for v in ledger)} flops; per-slot cycles in {args.ledger}")


if __name__ == '__main__':
    main()
