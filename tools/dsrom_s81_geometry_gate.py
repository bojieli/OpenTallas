#!/usr/bin/env python3
"""S81 analytical geometry gate; emit fresh physical cases only after all checks pass.

This is a source/model qualification receipt, never a routed closure receipt.
Track math mirrors ot_macro_track_snap.tcl for the ASAP7 R0/MX/MY/R180 macros.
"""
import argparse
import copy
import hashlib
import json
import math
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

import dsrom_s81_fulldie as F


def snap_axis(target, step, constraints):
    """Integer-nm origin on site grid satisfying all preferred-direction tracks."""
    period = math.lcm(step, *(p for p, _ in constraints))
    legal = [x for x in range(0, period, step) if all(x % p in s for p, s in constraints)]
    if not legal:
        raise ValueError('site grid does not meet signal-pin track residues')
    q = target // period
    return min((r + t * period for r in legal for t in (q - 1, q, q + 1)),
               key=lambda x: (abs(x - target), x))


def master_rects(m, k):
    masters, widths = F.masters(m, k), F.port_widths(m, k)
    return masters, {name: F.pin_rects(master, k, {p: widths.get((name, p), 0) for p in master.order})
                     for name, master in masters.items()}


def snap_model(m, masters, rects):
    # Extracted from openroad/orfs:asap7lock ASAP7 make_tracks.tcl and site LEF.
    # M4/6/8 horizontal, M3/5/7/9 vertical; M2 uses its seven row-local tracks.
    grids = {'M2': (1, 270, {45, 81, 117, 153, 189, 225, 0}),
             'M3': (0, 36, {9}), 'M4': (1, 48, {12}), 'M5': (0, 48, {12}),
             'M6': (1, 64, {16}), 'M7': (0, 64, {16}),
             'M8': (1, 80, {36}), 'M9': (0, 80, {36})}
    shapes = dict(rects)
    dims = {n: (v.w, v.h) for n, v in masters.items()}
    for name, rel in F.REAL_FILES.items():
        r = F.real_lef(rel)
        dims[name] = (r['w'], r['h'])
        # Include every rectangle, not only the first rectangle of each real pin.
        shapes[name] = []
        for pm in re.finditer(r'\n  PIN (\S+)\n(.*?)\n  END \1', r['text'], re.S):
            if 'USE POWER' in pm[2] or 'USE GROUND' in pm[2]:
                continue
            for layer, body in re.findall(r'LAYER (\S+) ;(.*?)(?=LAYER |\Z)', pm[2], re.S):
                for box in re.findall(r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)', body):
                    shapes[name].append((pm[1], layer, tuple(map(float, box))))
    cache, moves, errors, mismatches = {}, [], [], []
    snapped = []
    for it in m['insts']:
        w, h = dims[it.master]
        if abs(w - it.w) > 1e-6 or abs(h - it.h) > 1e-6:
            mismatches.append(dict(instance=it.name, master=it.master, model=[it.w, it.h], lef=[w, h]))
        key = it.master, it.orient
        if key not in cache:
            cons = [defaultdict(lambda: None), defaultdict(lambda: None)]
            try:
                for _, layer, box in shapes[it.master]:
                    if layer not in grids:
                        raise ValueError(f'unsupported signal layer {layer}')
                    axis, period, residues = grids[layer]
                    c2 = round(box[axis] * 1000) + round(box[axis + 2] * 1000)
                    if (axis == 0 and it.orient in ('MY', 'R180')) or (axis == 1 and it.orient in ('MX', 'R180')):
                        c2 = 2 * round((w if axis == 0 else h) * 1000) - c2
                    if c2 % 2:
                        raise ValueError(f'half-nm signal pin centre on {layer}')
                    allowed = {(r - c2 // 2) % period for r in residues}
                    prior = cons[axis][period]
                    cons[axis][period] = allowed if prior is None else prior & allowed
                cache[key] = [list(c.items()) for c in cons]
            except ValueError as e:
                cache[key] = str(e)
        ni = copy.copy(it)
        ni.w, ni.h = w, h  # check the geometry OpenROAD will actually instantiate
        try:
            if isinstance(cache[key], str):
                raise ValueError(cache[key])
            ni.x = snap_axis(round(it.x * 1000), 54, cache[key][0]) / 1000
            ni.y = snap_axis(round(it.y * 1000), 270, cache[key][1]) / 1000
            if abs(ni.x - it.x) > 1e-6 or abs(ni.y - it.y) > 1e-6:
                moves.append((it.name, ni.x - it.x, ni.y - it.y))
        except ValueError as e:
            errors.append((it.name, str(e)))
        snapped.append(ni)
    return dict(legality=F.legality(dict(insts=snapped)), dimension_mismatches=mismatches,
                track_errors=errors, moves=len(moves), move_examples=moves[:20],
                max_move_um=max((max(abs(x), abs(y)) for _, x, y in moves), default=0))


def geometry_gate(m):
    masters, rects = master_rects(m, 1)
    snap = snap_model(m, masters, rects)
    pin_checks, bounds = {}, []
    for k in (1, 16):
        mk, rk = (masters, rects) if k == 1 else master_rects(m, k)
        pin_checks[str(k)] = F.pin_clashes(m, k, .024 * k - 1e-6)
        for name, rs in rk.items():
            w, h = mk[name].w, mk[name].h
            for pn, ly, (x0, y0, x1, y1) in rs:
                if min(x0, y0) < -1e-6 or x1 > w + 1e-6 or y1 > h + 1e-6:
                    bounds.append((k, name, pn, ly))
    # Slabs retain the existing M4/M5 edge policy and OBS through M7;
    # these capacity and layer checks do NOT substitute for congestion/DRC.
    hub_names = {it.master for it in m['insts'] if it.kind == 'hub' or it.region == 'hub'}
    layer_errors, faces = [], []
    for name in sorted(hub_names):
        if name not in masters:
            continue
        master = masters[name]
        for p, spec in master.ports.items():
            if spec[0] != 'face':
                layer_errors.append((name, p, 'non-face pin'))
                continue
            _, bits, face, layer, _, pitch = spec
            if layer != ('M4' if face in 'EW' else 'M5'):
                layer_errors.append((name, p, layer))
            faces.append(dict(master=name, port=p, bits_per_cycle=bits, bytes_per_cycle=bits / 8,
                              face=face, layer=layer, tracks=bits * pitch,
                              face_capacity_tracks=math.floor((master.h if face in 'EW' else master.w) / .048)))
    use = F.port_usage(m)
    missing = []
    for it in m['insts']:
        if it.kind == 'stn':
            ports = use.get(it.name, {})
            for p in tuple(ports):
                if p.startswith(('fi', 'di', 'fo', 'do')):
                    # A split half may intentionally leave its forwarded clock
                    # unused; the parallel half supplies the downstream clock.
                    for prefix in ('fi', 'di', 'do'):
                        if prefix + p[2:] not in ports:
                            missing.append((it.name, prefix + p[2:]))
    legal = F.legality(m)
    passed = not (legal['overlaps'] or legal['outside'] or snap['legality']['overlaps'] or
                  snap['legality']['outside'] or snap['dimension_mismatches'] or snap['track_errors'] or
                  any(pin_checks.values()) or bounds or layer_errors or missing)
    return dict(status='PASS' if passed else 'FAIL', model_legality=legal, emitted_snap=snap,
                pin_clashes=pin_checks, pin_bounds_errors=bounds, station_port_errors=sorted(set(missing)),
                hub_routing_layer_check=dict(status='PASS' if not layer_errors else 'FAIL', errors=layer_errors,
                    signal_layers='M2-M9 unchanged', pins='M4/M5 unchanged', faces=faces,
                    qualification='Analytical layer/face policy only; no routed congestion or DRC closure'),
                physical_closed=False, export_qualified=False, adopted=False)


def main():
    ap = F.die_options(argparse.ArgumentParser(description=__doc__))
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--emit-cases', action='store_true')
    ap.add_argument('--source-commit', help='pinned git-archive commit when the run has no .git directory')
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)  # immutable previous attempts
    F.apply_options(a)
    m = F.build()
    F.finalize_r8(m)
    gate = geometry_gate(m)
    gate['variant'] = m['variant']
    gate['source_commit'] = a.source_commit or subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=F.ROOT, text=True).strip()
    gate['source_sha256'] = {str(p.relative_to(F.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in (Path(__file__), F.ROOT / 'tools/dsrom_s81_fulldie.py')}
    (a.output / 'geometry.json').write_text(json.dumps(gate, indent=2) + '\n')
    rec = F.plan_record_r8(m)
    (a.output / 'model.json').write_text(json.dumps(rec, indent=2, default=str) + '\n')
    print(json.dumps({k: v for k, v in gate.items() if k not in ('hub_routing_layer_check', 'source_sha256')}, default=str), flush=True)
    if gate['status'] != 'PASS':
        return 1
    if a.emit_cases:
        F.case_real(m, a.output / 'a_real')
        F.case_grt(m, a.output / 'b_k16_i50', 16, 'v8_geometry', 50, dict(F.COV, field=.128, hub=.044))
        (a.output / 'dsfd_glue.sv').write_text(F.glue_rtl(m))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
