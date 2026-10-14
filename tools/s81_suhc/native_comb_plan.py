#!/usr/bin/env python3
"""Construct a dimension-exact HC child packing request, never a timing waiver.

The die lead owns allocation and pins. This proposal preserves all closed leaf
outlines, uses no rotations, and gives every instance its own clock entry.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def construct(bill):
    classes = {r['instance']: r for r in bill['instances']}
    placements = []

    def add(key, x, y, instance=None):
        r = classes[key]
        view = ROOT / r['view'] / r['cell']
        ins = json.loads((view / 'insertion.json').read_text())
        w, h = r['outline_um']
        clocks = {}
        for corner in ('tt', 'ss', 'ff'):
            boundary = ins[corner]['boundary']
            clocks[corner] = {'entry_relative_to_phi_ps': -boundary['mean'],
                             'boundary_spread_ps': boundary['max']-boundary['min']}
        placements.append(dict(instance=instance or key, cell=r['cell'], kit=r['kit'],
                               params=r['params'], origin_um=[x, y], outline_um=[w, h],
                               orient='R0', clock_port=f"ck_leaf[{len(placements)}]",
                               clock_delivery=clocks, view=r['view']+'/'+r['cell'],
                               insertion_sha256=hashlib.sha256((view/'insertion.json').read_bytes()).hexdigest()))

    add('u_cf', 0, 0)
    y = 0.0
    # Flow order is deliberately preserved where possible, but this shelf is
    # only a packing witness. Pin distances and delays must be checked next.
    for key in ('u_pd.u_f5r1', 'u_pd.u_f8', 'u_seq', 'u_cr.u_core',
                'u_pd.u_r6', 'u_pd.u_r5', 'u_rx', 'u_cr.g_meta.u_m'):
        add(key, 420.12, round(y, 5))
        y += classes[key]['outline_um'][1] + 8.64
    add('u_nt', 0, 550.8)
    for i in range(4):
        add('g_aq[*].u_caq', 190.08+(i%2)*118.8, 550.8+(i//2)*118.8,
            f'g_aq[{i}].u_caq')
    outline = [575.992, 816.48]
    errors = []
    for i, a in enumerate(placements):
        x, y = a['origin_um']; w, h = a['outline_um']
        if x < 0 or y < 0 or x+w > outline[0]+1e-6 or y+h > outline[1]+1e-6:
            errors.append({'outside': a['instance']})
        for b in placements[:i]:
            bx, by = b['origin_um']; bw, bh = b['outline_um']
            if min(x+w,bx+bw) > max(x,bx)+1e-6 and min(y+h,by+bh) > max(y,by)+1e-6:
                errors.append({'overlap': [a['instance'], b['instance']]})
    assert len(placements) == sum(r['count'] for r in classes.values()) == 14
    assert not errors, errors
    return dict(schema='opentallas.s81.hc.native_comb_packing_request.v1',
                bill_source_commit=bill['source_commit'], production_params=bill['production_params'],
                parent='sp_hc_s/comb', existing_outline_um=[575.992,640],
                requested_outline_um=outline, added_height_um=176.48,
                routed_leaf_area_um2=bill['routed_tile_area_um2'],
                fill=bill['routed_tile_area_um2']/(outline[0]*outline[1]),
                instances=placements, dimension_errors=errors,
                status='PACKING_WITNESS_ONLY: die allocation and pins not assigned; no timing qualification',
                remaining=['die legal allocation and assigned child pins',
                           'actual per-bit setup/hold and face alignment over the wired comb netlist',
                           'relay/cycle repair of every failing pair and exact flat-reference plus mutants',
                           'wired independent child clocks including pad/meta hierarchy (current RTL shares sk)',
                           'PIPE control RTL reroute and exact full production composition',
                           'die real-view binding and release timing gates'])


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('bill', type=Path)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    plan = construct(json.loads(args.bill.read_text()))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(plan, indent=2)+'\n')
    print(f"{len(plan['instances'])} real children; packing {plan['requested_outline_um']}; fill {plan['fill']:.4f}")
