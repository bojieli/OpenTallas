#!/usr/bin/env python3
"""Export classifier inputs from the current HBM generator without changing geometry.

This is diagnostic evidence only; it does not publish or approve a contract.
Use --case on hbm_die_sta_classes.py to classify the actual bound libraries.
"""
import argparse
import json
from pathlib import Path
import hbm_accel_die_fp as H

def plan_dump(m, out):
    """die-timing classification inputs (owner 2026-10-13: classify failing endpoints by cause before fixing; the S81
    pilot's tools/s81/sta_path_classes.py): <out>/plan.json.gz = {insts: [[name, master, kind, x, y, w, h, orient]],
    hops: [[bus, class, bits, driver inst, port, load inst, port, um]]} with um = the pin-to-pin Manhattan length of
    that driver -> load pair (None: a placeholder end without pins), and <out>/clock_delivery.json = {tiles: {master:
    {view: real | hard_macro | relay | placeholder}}} (real = a LEF the die binds from a closed view)."""
    import gzip
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    P = H.pin_points(m, 16)
    by = {it.name: it for it in m['insts']}
    hops = []
    for bid, cls, bits, eps in m['buses']:
        ends = [e for e in eps if e[0] in by]
        if len(ends) < 2:
            continue
        q0 = P(*ends[0])
        for e in ends[1:]:
            q1 = P(*e)
            um = round(abs(q0[0] - q1[0]) + abs(q0[1] - q1[1]), 1) if q0 and q1 else None
            hops.append([bid, cls, bits, ends[0][0], H.port_base(ends[0][1]), e[0], H.port_base(e[1]), um])
    json.dump(dict(insts=[[it.name, it.master, it.kind, round(it.x, 3), round(it.y, 3), round(it.w, 3), round(it.h, 3), it.orient]
                          for it in m['insts']], hops=hops), gzip.open(out / 'plan.json.gz', 'wt'))
    tiles = {}
    for it in m['insts']:
        if it.master not in tiles:
            tiles[it.master] = dict(view='hard_macro' if it.kind in ('phy', 'serdes_slab') and it.master in H.REAL else
                                    'real' if it.master in H.REAL else
                                    'relay' if it.kind == 'waypoint' else 'placeholder', kind=it.kind)
    (out / 'clock_delivery.json').write_text(json.dumps(dict(tiles=tiles), indent=1) + '\n')
    return dict(plan=str(out / 'plan.json.gz'), hops=len(hops), masters=len(tiles),
                real_masters=sum(1 for t in tiles.values() if t['view'] == 'real'))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ds-var', default='')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    variant = H.variant_arg(a.ds_var)
    model = H.build(variant, network_probe=bool(variant and variant.get('sm_physical_grid')))
    print(json.dumps(plan_dump(model, a.out)))

if __name__ == '__main__':
    main()
