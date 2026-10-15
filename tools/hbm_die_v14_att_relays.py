#!/usr/bin/env python3
"""HBM die contract v14 (2026-10-14): the attention -> SU relay chains tr_SW0 / tr_SW1 re-placed around the SW quadrant
COLL slot (hfd_coll_q3: x 8,699.6-10,954.6 / y 7,948.8-10,657.4), which sits on the old rows y 9,143 / 10,311.
Both chains keep their source pin (attention root o, first relay abutting it) and their SU a-face pin rows (last relay
abutting the SU W face at the same y: the SU master and its other three quadrants do not change).  New route: north along
the attention face (x 8,448.96), east in the band between the slot and the SW HC quarter (y 10,700 / 10,850), south in
the slot | SU channel (x 11,070 for tr_SW0) to the pin row.  Relays every <= 480 um (rule step of the r25gq file), hop
<= 504 um.  Latency: tr_SW0 7 -> 13 added cycles, tr_SW1 8 -> 8 (recorded, not priced: one attention output stream
of one quadrant).

    python3 tools/hbm_die_v14_att_relays.py   (writes physical/hbm_accel_die_views/att_su_relay/relays_r25gq_v14.json)
"""
import json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'physical/hbm_accel_die_views/att_su_relay/relays_r25gq.json'
DST = ROOT / 'physical/hbm_accel_die_views/att_su_relay/relays_r25gq_v14.json'
STEP = 480.0


def place(poly):
    """relay origins every <= STEP um along a rectilinear polyline, first and last at its ends"""
    L = sum(abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip(poly, poly[1:]))
    n = math.ceil(L / STEP)
    out = []
    for k in range(n + 1):
        t = L * k / n
        for a, b in zip(poly, poly[1:]):
            s = abs(b[0] - a[0]) + abs(b[1] - a[1])
            if t <= s + 1e-9:
                f = t / s if s else 0.0
                out.append((round(a[0] + (b[0] - a[0]) * f, 3), round(a[1] + (b[1] - a[1]) * f, 3)))
                break
            t -= s
    return out, L / n


def main():
    d = json.loads(SRC.read_text())
    by = {r['name']: r for r in d['relays']}
    routes = {('SW', 0): [(8448.96, 9143.28), (8448.96, 10700.0), (11070.0, 10700.0), (11070.0, 9143.28), (11130.048, 9143.28)],
              ('SW', 1): [(8448.96, 10992.24), (8448.96, 10850.0), (11130.048, 10850.0), (11130.048, 10311.172)]}
    keep = [r for r in d['relays'] if not any(r['name'].startswith(f'rly_{q}_{ln}_') for q, ln in routes)]
    new = []
    for (q, ln), poly in routes.items():
        pts, seg = place(poly)
        proto = by[f'rly_{q}_{ln}_0']
        for k, (x, y) in enumerate(pts):
            new.append(dict(proto, name=f'rly_{q}_{ln}_{k}', x=x, y=y))
        b = next(b for b in d['buses'] if b['bus'] == f'tr_{q}{ln}')
        b.update(relays=len(pts), segments_um=[round(seg, 3)] * (len(pts) - 1), max_segment_um=round(seg, 3),
                 path_um=round(seg * (len(pts) - 1), 3), added_cycles=len(pts),
                 v14_reroute='around the SW quadrant COLL slot (contract v14)')
    d['relays'] = keep + new
    d['relay_count'] = len(d['relays'])
    d['v14'] = 'tr_SW0 / tr_SW1 re-placed around hb_coll_SW (tools/hbm_die_v14_att_relays.py)'
    DST.write_text(json.dumps(d, indent=1) + '\n')
    print(json.dumps({b['bus']: (b['relays'], b['max_segment_um']) for b in d['buses'] if b['bus'].startswith('tr_SW')}))


if __name__ == '__main__':
    main()
