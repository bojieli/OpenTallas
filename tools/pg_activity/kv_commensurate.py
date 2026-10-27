#!/usr/bin/env python3
"""KV canonical PG coupon with exact die-to-window stripe phase translation.

Uses the existing BUMP-SURVEY / HEAD-5 generator unchanged. The generated
window PDN is translated from the declared global grid, including its first
net, rather than silently starting a new lattice at the coupon origin.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys


def local_stripe(row, origin):
    period = row['pitch_um']
    phase = (row['offset_um'] - origin) % period
    if math.isclose(phase, period, abs_tol=1e-8):
        phase = 0.0
    first = 'POWER'
    if phase >= period / 2 - 1e-8:
        phase -= period / 2
        first = 'GROUND'
    return round(phase, 6), first


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('src', type=Path)
    ap.add_argument('plan', type=Path)
    ap.add_argument('power', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--width9', type=float, default=12.96)
    ap.add_argument('--pitch9', type=float, default=39.96)
    ap.add_argument('--offset9', type=float, default=13.77)
    ap.add_argument('--width8', type=float, default=.48)
    ap.add_argument('--pitch8', type=float, default=4.32)
    args = ap.parse_args()
    sys.path.insert(0, str(args.src / 'tools/die_plan'))
    import infra_pg as G
    import schema as S
    raw = json.loads(args.plan.read_text())
    raw['die']['pg'].pop('domains', None)
    # A coupon directory is immutable once generated or submitted.
    args.out.mkdir(parents=True, exist_ok=False)
    nd = args.out / 'plan_nodomains.json'
    nd.write_text(json.dumps(raw))
    plan = S.Plan(S.load(str(nd)), nd)
    grid = [dict(layer='M8', width_um=args.width8, pitch_um=args.pitch8,
                 offset_um=args.pitch8 / 2, nets=['VDD', 'VSS']),
            dict(layer='M9', width_um=args.width9, pitch_um=args.pitch9,
                 offset_um=args.offset9, nets=['VDD', 'VSS'])]
    n = 319.68 / args.pitch9
    if not math.isclose(n, round(n), abs_tol=1e-8):
        raise ValueError('M9 pitch must divide the fixed 319.68um clock lattice')
    distances = []
    for k in range(32):
        x = 583.2 + 319.68 * k
        d = (x - args.offset9) % (args.pitch9 / 2)
        distances.append(min(d, args.pitch9 / 2 - d))
    half_gap = (args.pitch9 / 2 - args.width9) / 2
    if min(distances) < args.pitch9 / 4 - 1e-6 or half_gap <= 0:
        raise ValueError('clock columns must be exactly in the PG gap centres')
    # Same requested interior hot region as PG-ACTIVITY-KVHBM. Its exact
    # snapped bounds and resulting power are retained, not relabelled.
    rect = [6462.72, 6462.72, 9434.88, 9434.88]
    pg = dict(grid=grid, regions=[], core_w_mm2=None, bump_pitch_um=150.,
              vdd=.7, budget_mv=35.)
    meta = G.window_kit(plan, nd.parent, pg, args.out, args.out.name,
                        rect, tile=43.2, power=json.loads(args.power.read_text()),
                        pad_um=70., nets=('VDD', 'VSS'))
    pdn = args.out / 'psm/pdn.tcl'
    text = pdn.read_text()
    phases = []
    for row, origin in zip(grid, [meta['window_um'][1], meta['window_um'][0]]):
        offset, first = local_stripe(row, origin)
        pattern = rf'(^add_pdn_stripe .*?-layer {row["layer"]} .*?-offset )\S+( .*?-starts_with )\S+'
        text, count = re.subn(pattern, lambda m: f'{m[1]}{offset:.6f}{m[2]}{first}', text, flags=re.M)
        if count != 1:
            raise ValueError(f'expected exactly one {row["layer"]} stripe declaration')
        phases.append(dict(layer=row['layer'], global_offset_um=row['offset_um'],
                           window_origin_um=origin, local_offset_um=offset,
                           starts_with=first))
    pdn.write_text(text)
    meta.update(plan_src=str(args.plan.resolve()), power_src=str(args.power.resolve()),
                plan_sha256=hashlib.sha256(args.plan.read_bytes()).hexdigest(),
                power_sha256=hashlib.sha256(args.power.read_bytes()).hexdigest(),
                tracks=G.tracks_of(plan, grid), stripe_phase=phases,
                clock_columns_um=[583.2 + 319.68*k for k in range(32)],
                clock_centre_to_pg_edge_um=round(min(distances)-args.width9/2, 6),
                clock_phase_basis='ideal583.2+319.68k lattice; actual validated driver axes may differ by up to0.68um',
                actual_axis_offset_bound_um=.68,
                actual_axis_to_pg_edge_lower_bound_um=round(min(distances)-args.width9/2-.68, 6),
                below_m7_mv=6.05,
                below_m7_basis='PG-ACTIVITY-KVHBM e1 slice; inherited conservative full-power result, not a new measurement',
                scope='canonical 150um bumps/70um pads, co-located VDD drop + VSS bounce, measured type map; independent grid candidate, no plan adoption')
    (args.out / 'irwin.json').write_text(json.dumps(meta, indent=2)+'\n')
    print(json.dumps({k: meta[k] for k in ('window_um', 'power_w', 'bumps', 'grid', 'stripe_phase', 'clock_centre_to_pg_edge_um')}, indent=2))


if __name__ == '__main__':
    main()
