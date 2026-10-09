#!/usr/bin/env python3
"""Contract pin plans for S81-PH views whose die ports change (CLAUDE S81-PH, 2026-10-06).

When a kind's contract adds/widens die ports (results/rtl/s81_ph_20261006/<kind>/contract.json generator_changes),
the generator has no pin positions for it yet.  This tool writes the view's own pin plan in the generator's
conventions (on-track: M4 horizontal / M5 vertical, offset 0.012, pitch 0.048; pin 0.024 x 0.192 at the face),
as physical/s81_ph_views/ports/contract/<master>/{ports.json, io_place.tcl, ports.svh}, the same format as
tools/s81_ph/s81_ph_views.py ports, so route_view.sh and `check --die contract` work unchanged.  The generator
then binds the view as a REAL abstract (its LEF pins), as it does for the q element.

  python3 tools/s81_ph/s81_ph_pinplan.py <spec.json>
spec: {"master", "w_um", "h_um", "domain", "ports": [[name, bits, dir, face, layer, pitch_tracks, frac_center], ...]}
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P, OFF = 0.048, 0.012


def main():
    spec = json.loads(Path(sys.argv[1]).read_text())
    W, H = spec['w_um'], spec['h_um']
    ports, used = {}, {}
    # Handwritten masters can declare scalar pins. Retain the historical
    # one-bit-vector convention unless the contract explicitly marks a scalar.
    scalars = set(spec.get('scalar_ports', []))
    for name, bits, d, face, layer, pt, fc in spec['ports']:
        assert name not in scalars or bits == 1, (name, 'scalar width must be 1')
        horiz = face in 'NS'
        span = W if horiz else H
        n_tr = int((span - 2 * OFF) / P)
        need = (bits - 1) * pt + 1
        c = int(fc * n_tr)
        t0 = max(2, min(c - need // 2, n_tr - need - 2))
        pins = []
        for i in range(bits):
            t = t0 + i * pt
            key = (face, layer, t)
            assert key not in used, (name, i, used.get(key))
            used[key] = name
            pos = OFF + t * P
            if face == 'S': r = (pos - 0.012, 0.0, pos + 0.012, 0.192)
            elif face == 'N': r = (pos - 0.012, H - 0.192, pos + 0.012, H)
            elif face == 'W': r = (0.0, pos - 0.012, 0.192, pos + 0.012)
            else: r = (W - 0.192, pos - 0.012, W, pos + 0.012)
            pins.append([name if name in scalars else f'{name}[{i}]', layer] + [round(v, 4) for v in r])
        assert t0 + need < n_tr, (name, 'does not fit')
        ports[name] = dict(bits=bits, layer=layer, pins=pins, direction=d, face=face)
    rec = dict(master=spec['master'], die='contract', w_um=W, h_um=H, obs_top=7, domain=spec.get('domain'), instances=None,
               orients=['R0'], ports=ports, generator=dict(file='tools/s81_ph/s81_ph_pinplan.py', spec=spec))
    d = ROOT / 'physical/s81_ph_views/ports/contract' / spec['master']
    d.mkdir(parents=True, exist_ok=True)
    (d / 'ports.json').write_text(json.dumps(rec, indent=0) + '\n')
    L = [f"# {spec['master']} (contract pin plan, tools/s81_ph/s81_ph_pinplan.py)"]
    for p in sorted(ports):
        for nm, ly, x0, y0, x1, y1 in ports[p]['pins']:
            L.append(f'place_pin -pin_name {{{nm}}} -layer {ly} -location {{{(x0 + x1) / 2:.4f} {(y0 + y1) / 2:.4f}}} '
                     f'-pin_size {{{x1 - x0:.4f} {y1 - y0:.4f}}}')
    (d / 'io_place.tcl').write_text('\n'.join(L) + '\n')
    (d / 'ports.svh').write_text(',\n'.join(
        f"    {ports[p]['direction']} wire " + ('' if p in scalars else f"[{ports[p]['bits'] - 1}:0] ") + p
        for p in sorted(ports)) + '\n')
    print(d, {p: (v['bits'], v['face']) for p, v in ports.items()})


if __name__ == '__main__':
    main()
