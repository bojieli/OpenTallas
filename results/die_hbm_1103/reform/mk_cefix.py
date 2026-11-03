#!/usr/bin/env python3
"""DIE-HBM-61/PLAN d44v part 2 (3): move every plan centre clock entry whose island / point sits over a hard-core macro
(check.py clock_entry_macro, G0C) to the nearest free 4.32-lattice point of a std-cell region of that core (12.8a), then
re-point the parent type clock taps (kind core, name = inst) at origin + oriented entry.  Runs BEFORE clock_entry_pins.py
so the centre clock pins follow the moved entry.  python3 mk_cefix.py PLAN_DIR   (edits clock_entries.json + die_plan.json
in place, unlinking hard links first; writes cefix_event.json)"""
import json, sys, os
from pathlib import Path
d = Path(sys.argv[1]); G = 4.32; EPS = 1e-3
P = json.loads((d / 'die_plan.json').read_text()); C = json.loads((d / 'clock_entries.json').read_text())
M = json.loads((d / 'core_macros.json').read_text()); halo = float(M.get('halo_um', 0.0)); MC = M.get('cores', {})
hcs = {(tn, h['inst']): h for tn, t in P['partition_types'].items() for h in t.get('hard_cores') or []}


def ov(a, b):
    return min(a[2], b[2] + halo) - max(a[0], b[0] - halo) > EPS and min(a[3], b[3] + halo) - max(a[1], b[1] - halo) > EPS


def bad(xy, isl, mac):
    return any(ov(isl, m['rect_um']) or (m['rect_um'][0] - halo < xy[0] < m['rect_um'][2] + halo and
                                         m['rect_um'][1] - halo < xy[1] < m['rect_um'][3] + halo) for m in mac)


moved, memo = [], {}
for tn, ents in C.items():
    if not isinstance(ents, dict):
        continue
    for inst, e in ents.items():
        if not isinstance(e, dict) or (tn, inst) not in hcs:
            continue
        h = hcs[(tn, inst)]; m = h['module']; cm = MC.get(m) or {}
        if cm.get('status') != 'KNOWN':
            continue
        mac = cm['macros']; x, y = e['xy_um']; isl = e['island_um']
        hx, hy = x - isl[0], y - isl[1]; hw, hh = isl[2] - x, isl[3] - y
        if not bad(e['xy_um'], isl, mac):
            continue
        W, H = h['outline_um']; key = (m, x, y)
        if key not in memo:
            best = None
            for i in range(int(W / G) + 1):
                for j in range(int(H / G) + 1):
                    px, py = round(x + (i - round(x / G)) * G, 6), round(y + (j - round(y / G)) * G, 6)
                    I = [px - hx, py - hy, px + hw, py + hh]
                    if I[0] < 0 or I[1] < 0 or I[2] > W or I[3] > H or bad((px, py), I, mac):
                        continue
                    dd = abs(px - x) + abs(py - y)
                    if best is None or dd < best[0] - EPS:
                        best = (dd, px, py, I)
            memo[key] = best
        best = memo[key]
        if best is None:
            print('NO FREE POINT', tn, inst); continue
        _, px, py, I = best
        old = list(e['xy_um']); e['xy_um'] = [px, py]; e['island_um'] = [round(v, 6) for v in I]
        e['source'] = e.get('source', '') + ' | DIE-HBM-61 d44v p2: moved off macro to nearest std-cell lattice point'
        o = h.get('orient', 'R0'); ox, oy = h['origin_um']
        tx = ox + (W - px if o in ('MY', 'R180') else px); ty = oy + (H - py if o in ('MX', 'R180') else py)
        nt = 0
        for tp in P['partition_types'][tn].get('clock', {}).get('taps', []) or []:
            if tp.get('kind') == 'core' and tp.get('name') == inst:
                tp['xy'] = [round(tx, 6), round(ty, 6)]; nt += 1
        moved.append(dict(type=tn, inst=inst, module=m, old=old, new=[px, py], manhattan_um=round(best[0], 3), taps=nt))
for f, o in (('clock_entries.json', C), ('die_plan.json', P)):
    q = d / f; q.unlink(); q.write_text(json.dumps(o, indent=1) + '\n')
(d / 'cefix_event.json').write_text(json.dumps(dict(schema='opentallas.hbm_plan_event.v1', event='d44v-p2-centry-off-macro',
                                                    moved=moved), indent=1) + '\n')
print('moved', len(moved), sorted({(r['module'][-30:], tuple(r['new'])) for r in moved}))
