#!/usr/bin/env python3
"""Split a generator die master into separately hardened views (CLAUDE HBM-ABSTRACTS spine, 2026-10-06).

A split spec (JSON) cuts the master's outline into horizontal bands, gives each band (a derived master) a subset of the
parent's die ports at their unchanged absolute positions, and adds new ports: cross buses between abutting bands
(pins at the same x on the shared edge, so the die joins them with a zero-length net) and per-band copies of clock /
reset.  Writes physical/.../split/<derived>/ports.json (+ io_place.tcl), which tools/hbm_die_views.py reads as the
derived master's record (ports / check) and tools/hbm_die_wrap.py builds the wrapper from, plus split.json (the
parent-port -> derived-port map the die generator needs to replace the parent instance by the bands).

    python3 tools/hbm_die_split.py --spec physical/hbm_accel_die_views/cmdproc/split_spec.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_die_views as V  # noqa: E402
import hbm_die_wrap as W  # noqa: E402

TRACK = 0.192   # M5 pin pitch on horizontal edges (the generator's face-pin step)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--spec', required=True)
    a = ap.parse_args()
    sp = json.loads(Path(a.spec).read_text())
    parent = sp['parent']
    rec = V.master_record(parent)
    fck = W.fclk_bits(parent)
    out = ROOT / sp['out']
    smap = dict(parent=parent, parent_size_um=[rec['w_um'], rec['h_um']], spec=a.spec, bands={}, cross=[])
    for b in sp['bands']:
        y0, h = b['y0'], b['h']
        ports, fc = {}, {}
        for p in b['ports']:
            v = json.loads(json.dumps(rec['ports'][p]))
            for pin in v['pins']:
                pin[3] = round(pin[3] - y0, 4)
                pin[5] = round(pin[5] - y0, 4)
                assert -1e-6 <= pin[3] and pin[5] <= h + 1e-6, (b['name'], pin)
            ports[p] = v
            if p in fck:
                fc[p] = {str(k): d for k, d in fck[p].items()}
        for x in b.get('new', []):
            # {port, bits, direction, edge top|bottom, x0 (um, first pin) | copy_x (parent port whose pin x is reused)}
            bits = x['bits']
            if 'copy_x' in x:
                xs = [(pin[2], pin[4]) for pin in rec['ports'][x['copy_x']]['pins']]
            else:
                xs = [(round(x['x0'] + k * TRACK, 4), round(x['x0'] + k * TRACK + 0.024, 4)) for k in range(bits)]
            ya, yb = (0.0, 0.192) if x['edge'] == 'bottom' else (round(h - 0.192, 4), h)
            pins = [[f"{x['port']}[{k}]", 'M5', xs[k][0], ya, xs[k][1], yb] for k in range(bits)]
            d = 'out' if x['direction'] == 'output' else 'in'
            ports[x['port']] = dict(bits=bits, layer='M5', pins=pins, face='S' if x['edge'] == 'bottom' else 'N',
                                    dir_segments=[[0, bits, d]], direction=x['direction'])
        r = dict(master=b['name'], kind=rec['kind'], w_um=rec['w_um'], h_um=h, obs_top=rec['obs_top'],
                 note=f"derived master: band y {y0} .. {round(y0 + h, 4)} um of {parent} (tools/hbm_die_split.py)",
                 instances=1, orients=['R0'], inst_names=[f"{rec['inst_names'][0]}_{b['name'][-1]}"], ports=ports,
                 generator=rec['generator'], fclk=fc, derived_from=dict(parent=parent, y0_um=y0, spec=a.spec, generator=rec['generator']))
        d = out / b['name']
        d.mkdir(parents=True, exist_ok=True)
        (d / 'ports.json').write_text(json.dumps(r, indent=0) + '\n')
        (d / 'io_place.tcl').write_text(V.io_tcl(r).replace("(tools/hbm_die_views.py ports",
                                                             "(tools/hbm_die_split.py, derived master; generator"))
        smap['bands'][b['name']] = dict(y0_um=y0, h_um=h, parent_ports=b['ports'],
                                        new_ports={x['port']: dict(bits=x['bits'], direction=x['direction'],
                                                                   edge=x['edge'], role=x.get('role', ''))
                                                   for x in b.get('new', [])})
    smap['cross'] = sp.get('cross', [])
    smap['die_nets'] = sp.get('die_nets', [])
    (out / 'split.json').write_text(json.dumps(smap, indent=1) + '\n')
    print(json.dumps({k: (v['h_um'], len(v['parent_ports']), list(v['new_ports'])) for k, v in smap['bands'].items()}))


if __name__ == '__main__':
    main()
