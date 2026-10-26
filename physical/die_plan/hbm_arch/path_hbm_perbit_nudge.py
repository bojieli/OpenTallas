#!/usr/bin/env python3
"""Per-bit FT site nudge (PATH-HBM, 2026-10-26): after a hard-core move (e.g. the G0C-FIX lattice snap), move ONLY the
per-bit relay cells that now overlap a core halo to the nearest legal, free row site; every other bit site stays put.

Same legality model as path_hbm_perbit_m5.py / the B1 census: cell 1.404 x 0.27 um, columns 4.32 + k*2.16, rows
4.32 + k*0.27, halo 8.64 um around every placed hard core, 4.32-um outline inset, unique sites per type, every
paired-bit leg (pin -> site -> ... -> pin) <= 403 um. Station counts never change (0 cycles); regs_um[1:] are
refreshed to the per-stage bit-site centroids exactly as path_hbm_perbit_m5.py writes them.
Geometry proposal only, never a route receipt.
Usage: path_hbm_perbit_nudge.py --src <plan dir> --out <new plan dir> --types q_b100[,..]
"""
import argparse, json, shutil, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools/die_plan')]
import schema as S
from gen_phys import type_pins
from tools.die_trial.legal_sites import RowAllocator
CELL = np.array([1.404, .27]); HALO = 8.64; LEG = 403.0; RADIUS = 300.0  # 2-column channels after the lattice snap (was 3): the free rows lie further along the channel


def hits(ll, boxes):
    x, y = ll
    return any(x < x1 - 1e-6 and x + CELL[0] > x0 + 1e-6 and y < y1 - 1e-6 and y + CELL[1] > y0 + 1e-6 for x0, y0, x1, y1 in boxes)


def nudge_type(raw, tn):
    t = raw['partition_types'][tn]; w, h = t['outline_um']
    boxes = list(S.placed_macro_boxes(t, halo=HALO).values())
    alloc = RowAllocator((4.32, 4.32, w - 4.32, h - 4.32), blocked=boxes, cell_size=CELL, column_pitch=2.16, row_pitch=.27, origin=(4.32, 4.32))
    slots = [s for s in t.get('ft_slots', []) if s.get('bit_sites_um')]
    bad = []
    for s in slots:                                   # keep every legal site: reserve it first
        for k, st in enumerate(s['bit_sites_um']):
            for i, ll in enumerate(st):
                if hits(ll, boxes): bad.append((s, k, i))
                else: alloc.reserve_rectangle((ll[0] + .01, ll[1] + .01, ll[0] + CELL[0] - .01, ll[1] + CELL[1] - .01))  # shrunk: no float bleed into the neighbour row
    model = S.Plan(raw); pins = {(b, i): np.array([x, y]) for b, i, _, x, y, _ in type_pins(model, tn)}
    rep = {}

    def sid(q):
        ix = round((q[0] - alloc.cw / 2 - alloc.ox) / alloc.cp); iy = round((q[1] - alloc.ch / 2 - alloc.oy) / alloc.rp)
        return (iy - alloc.iy0) * alloc.nx + ix - alloc.ix0

    def place(tgt, prev, nxt):
        """nearest free legal site to tgt with both legs <= LEG (prev/nxt may be None = unchecked)."""
        rejected = []
        try:
            for _ in range(256):
                try: q = alloc.allocate(tgt, 1, max_radius_um=RADIUS)[0][0]
                except ValueError: return None
                if all(o is None or np.abs(q - o).sum() <= LEG + 1e-6 for o in (prev, nxt)): return q
                rejected.append(sid(q))
        finally: alloc.used.difference_update(rejected)
        return None

    def L_points(a, b, n, vfirst):
        seg = [a, np.array([a[0], b[1]]) if vfirst else np.array([b[0], a[1]]), b]
        ln = [float(np.abs(seg[j + 1] - seg[j]).sum()) for j in (0, 1)]; tot = sum(ln); out = []
        for j in range(1, n + 1):
            d = tot * j / (n + 1); k = 0 if d <= ln[0] or ln[1] == 0 else 1; d -= 0 if k == 0 else ln[0]
            u = seg[k + 1] - seg[k]; out.append(seg[k] + (u / max(np.abs(u).sum(), 1e-9)) * d)
        return out

    work = {}
    for s, k, i in bad: work.setdefault((id(s), i), (s, i, []))[2].append(k)
    order = sorted(work.values(), key=lambda v: (v[0]['width'], v[0]['name'], v[1]))   # narrow slots first: they have the fewest alternatives
    for s, i, ks in order:
        nm = s['name']; st = s['bit_sites_um']; n = len(st)
        a, b = pins[nm + '_i', i], pins[nm + '_o', i]
        cen = lambda k: np.array(st[k][i]) + CELL / 2
        old = {k: cen(k) for k in range(n)}
        got = {}; ok = True
        for k in ks:                                  # 1) per-stage nudge of the colliding stages only
            prev = a if k == 0 else (got.get(k - 1, old[k - 1]))
            nxt = b if k == n - 1 else old[k + 1]
            q = place(old[k], prev, None if (k + 1) in ks else nxt)
            if q is None: q = place((prev + nxt) / 2, prev, None if (k + 1) in ks else nxt)
            if q is None: ok = False; break
            got[k] = q
        if ok:                                        # legs between consecutive re-sited stages
            ch = [a, *[got.get(k, old[k]) for k in range(n)], b]
            ok = max(float(np.abs(ch[j + 1] - ch[j]).sum()) for j in range(n + 1)) <= LEG + 1e-6
        mode = 'nudge'
        if not ok:                                    # 2) re-site this bit's whole chain along an L route (same station count)
            alloc.used.difference_update(sid(q) for q in got.values())
            alloc.used.difference_update(sid(old[k]) for k in range(n) if k not in ks)
            for vfirst in (True, False):
                got = {}
                for k, tgt in enumerate(L_points(a, b, n, vfirst)):
                    q = place(tgt, a if k == 0 else got[k - 1], b if k == n - 1 else None)
                    if q is None: break
                    got[k] = q
                if len(got) == n: mode = 'reroute'; break
                alloc.used.difference_update(sid(q) for q in got.values())
            else: raise ValueError(f'{tn}/{nm}[{i}]: no legal per-bit chain with legs <= {LEG} at {n} stations')
        r = rep.setdefault(nm, dict(moved=0, rerouted_bits=0, max_move_um=0.0))
        for k, q in got.items():
            r['moved'] += 1; r['max_move_um'] = max(r['max_move_um'], round(float(np.abs(q - old[k]).sum()), 4))
            st[k][i] = [round(float(v), 6) for v in q - CELL / 2]
        r['rerouted_bits'] += mode == 'reroute'
    for s in slots:
        if s['name'] not in rep: continue
        nb = s['width'] + 1; sites = np.array(s['bit_sites_um']) + CELL / 2
        a = np.array([pins[s['name'] + '_i', i] for i in range(nb)]); b = np.array([pins[s['name'] + '_o', i] for i in range(nb)])
        chain = [a, *sites, b]; rep[s['name']]['max_leg_um'] = round(max(float(np.abs(q - p).sum(axis=1).max()) for p, q in zip(chain, chain[1:])), 4)
        rep[s['name']]['stations'] = s['stations']
        s['regs_um'] = [a.mean(axis=0).round(4).tolist(), *sites.mean(axis=1).round(4).tolist()]
        s['note'] = (s.get('note', '') + f" | PERBIT-NUDGE: {rep[s['name']]['moved']} halo-colliding bit sites moved to the nearest "
                     f"legal free site (<= {rep[s['name']]['max_move_um']} um), stations unchanged").lstrip(' |')
    return rep


def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('--src', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path); ap.add_argument('--types', required=True); a = ap.parse_args()
    if a.out.exists(): raise SystemExit('output must be new')
    raw = json.loads((a.src / 'die_plan.json').read_text()); before = S.Plan(json.loads(json.dumps(raw)))
    rep = {tn: nudge_type(raw, tn) for tn in a.types.split(',')}
    after = S.Plan(json.loads(json.dumps(raw)))
    delta = {lid: after.lane_latency(lid)['cycles'] - before.lane_latency(lid)['cycles'] for lid in after.lanes
             if after.lane_latency(lid)['cycles'] != before.lane_latency(lid)['cycles']}
    shutil.copytree(a.src, a.out)
    (a.out / 'die_plan.json').write_text(json.dumps(raw, indent=1) + '\n')
    (a.out / 'perbit_nudge_report.json').write_text(json.dumps(dict(src=str(a.src / 'die_plan.json'), types=rep, lane_cycle_delta=delta,
                                                                   scope='geometry proposal; not a route receipt'), indent=1) + '\n')
    print('COMPLETE', json.dumps(rep), 'cycle_delta', json.dumps(delta), flush=True)


if __name__ == '__main__': main()
