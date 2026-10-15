#!/usr/bin/env python3
"""Systematic orientation / same-master permutation search on the CURRENT generated Qwen compute-die pin graph.

Topology (wide27 + adopted Band0/Band1 MX) is frozen: only legal in-place orientations (R0/MX/MY/R180, same
footprint) and swaps of identical masters between their own slots are proposed, so no rectangle can overlap.
Metric per data bus: per-bit pin-centre HPWL (bit-um), longest per-bit pin pair, relay stages at the die
per-hop reach.  Every candidate reports TOTAL incident cost and its regressions, clock/reset pin movement and
unknowns.  Assignment-pin geometry only: never a route, cut, clock phi-R, or timing qualification.
"""
import argparse, collections, gzip, hashlib, itertools, json, math
from pathlib import Path
import numpy as np

ORIENTS = ('R0', 'MX', 'MY', 'R180')
# Bump/PHY-facing or die-edge macros keep their orientation (bump map / package side fixed).
FIXED_PREFIX = ('io_', 'ucie_kv', 'ckb_rom', 'rs_bump', 'up4_sel_')


def load(path):
    raw = path.read_bytes()
    raw = gzip.decompress(raw) if path.suffix == '.gz' else raw
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


class Graph:
    def __init__(self, d, reach):
        self.d = d; self.reach = reach
        self.inst = {i['n']: dict(i) for i in d['insts']}
        pins = {}
        for m, info in d['masters'].items():
            g = collections.defaultdict(list)
            for p in info['pins']:
                n = p['name']; stem = n.split('[')[0]
                k = int(n.split('[')[1].split(']')[0]) if '[' in n else 0
                r = p['rect']; g[stem].append((k, ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)))
            pins[m] = {s: np.array([q for _, q in sorted(v)], dtype=float) for s, v in g.items()}
        self.pins = pins
        self.data = []; self.ctrl = []; self.missing = []
        for b in d['buses']:
            ends = []; ok = True
            for n, p in b['e']:
                loc = pins[self.inst[n]['m']].get(p)
                if loc is None or len(loc) != b['n']:
                    ok = False; break
                ends.append((n, loc))
            rec = dict(b=b['b'], c=b['c'], n=b['n'], ends=ends)
            if not ok:
                self.missing.append(b['b']); continue
            (self.ctrl if b['c'] in ('clock_trunk', 'reset') else self.data).append(rec)
        self.inc = collections.defaultdict(list)
        for k, r in enumerate(self.data):
            for n in {n for n, _ in r['ends']}:
                self.inc[n].append(k)

    def place(self, n, loc, model):
        i = model[n]; o = i['o']; x = loc[:, 0].copy(); y = loc[:, 1].copy()
        if o in ('MY', 'R180'): x = i['w'] - x
        if o in ('MX', 'R180'): y = i['h'] - y
        return np.stack([i['x'] + x, i['y'] + y], 1)

    def bus(self, r, model):
        pts = np.stack([self.place(n, loc, model) for n, loc in r['ends']])  # E x bits x 2
        hp = (pts.max(0) - pts.min(0)).sum(1)
        u = pts[..., 0] + pts[..., 1]; v = pts[..., 0] - pts[..., 1]
        far = np.maximum(u.max(0) - u.min(0), v.max(0) - v.min(0))
        longest = float(far.max())
        return float(hp.sum()), longest, max(0, math.ceil(longest / self.reach) - 1)

    def evaluate(self, model):
        return [self.bus(r, model) for r in self.data]


def totals(g, ev):
    return dict(bit_um=round(sum(e[0] for e in ev), 3), worst_pair_um=round(max(e[1] for e in ev), 3),
                relay_bit_stages=int(sum(e[2] * g.data[k]['n'] for k, e in enumerate(ev))),
                max_bus_relay_stages=max(e[2] for e in ev))


def descend(g, model, ev, movable, guard, sweeps=6):
    """Greedy orientation coordinate descent; guard=True forbids any incident bus gaining a relay stage
    or lengthening its longest pair beyond the current die worst leg."""
    worst = max(e[1] for e in ev); moves = []
    for _ in range(sweeps):
        changed = 0
        for n in movable:
            ks = g.inc.get(n)
            if not ks: continue
            cur = model[n]['o']; best = (0.0, cur, None)
            base = sum(ev[k][0] for k in ks)
            for o in ORIENTS:
                if o == cur: continue
                model[n]['o'] = o
                new = {k: g.bus(g.data[k], model) for k in ks}
                if guard and any(new[k][2] > ev[k][2] or (new[k][1] > ev[k][1] and new[k][1] > worst) for k in ks):
                    continue
                gain = sum(new[k][0] for k in ks) - base
                if gain < best[0] - 1e-6: best = (gain, o, new)
            model[n]['o'] = cur
            if best[2] is not None:
                model[n]['o'] = best[1]
                for k, v in best[2].items(): ev[k] = v
                moves.append(dict(instance=n, master=model[n]['m'], frm=cur, to=best[1], delta_bit_um=round(best[0], 3)))
                changed += 1
        if not changed: break
    return moves


def swap_search(g, model, ev, groups, guard, sweeps=4):
    worst = max(e[1] for e in ev); moves = []
    for _ in range(sweeps):
        changed = 0
        for names in groups:
            for a, b in itertools.combinations(names, 2):
                ks = sorted(set(g.inc.get(a, [])) | set(g.inc.get(b, [])))
                if not ks: continue
                base = sum(ev[k][0] for k in ks); best = (0.0, None, None)
                A = dict(model[a]); B = dict(model[b])
                for oa, ob in itertools.product(ORIENTS, ORIENTS):
                    for key in ('x', 'y'): model[a][key], model[b][key] = B[key], A[key]
                    model[a]['o'], model[b]['o'] = oa, ob
                    new = {k: g.bus(g.data[k], model) for k in ks}
                    if guard and any(new[k][2] > ev[k][2] or (new[k][1] > ev[k][1] and new[k][1] > worst) for k in ks):
                        continue
                    gain = sum(new[k][0] for k in ks) - base
                    if gain < best[0] - 1e-6: best = (gain, (oa, ob), new)
                model[a].update(A); model[b].update(B)
                if best[1] is not None:
                    for key in ('x', 'y'): model[a][key], model[b][key] = B[key], A[key]
                    model[a]['o'], model[b]['o'] = best[1]
                    for k, v in best[2].items(): ev[k] = v
                    moves.append(dict(swap=[a, b], orient=list(best[1]), delta_bit_um=round(best[0], 3)))
                    changed += 1
        if not changed: break
    return moves


def ctrl_movement(g, base, model):
    rows = []
    for r in g.ctrl:
        b0 = g.bus(r, base); b1 = g.bus(r, model)
        if abs(b1[0] - b0[0]) > 1e-6 or abs(b1[1] - b0[1]) > 1e-6:
            rows.append(dict(bus=r['b'], family=r['c'], bits=r['n'], hpwl_before=round(b0[0], 3), hpwl_after=round(b1[0], 3),
                             longest_before=round(b0[1], 3), longest_after=round(b1[1], 3)))
    return rows


def regressions(g, ev0, ev1, n=12):
    rows = []
    for k, (a, b) in enumerate(zip(ev0, ev1)):
        if abs(b[0] - a[0]) > 1e-6 or b[1] != a[1]:
            rows.append(dict(bus=g.data[k]['b'], family=g.data[k]['c'], bits=g.data[k]['n'], delta_bit_um=round(b[0] - a[0], 3),
                             longest_before=round(a[1], 3), longest_after=round(b[1], 3), stages_before=a[2], stages_after=b[2]))
    rows.sort(key=lambda r: r['delta_bit_um'])
    return dict(changed_buses=len(rows), improvements=rows[:n], regressions=[r for r in rows[::-1] if r['delta_bit_um'] > 0][:n],
                longest_increases=sorted([r for r in rows if r['longest_after'] > r['longest_before']], key=lambda r: r['longest_before'] - r['longest_after'])[:n],
                stage_increases=[r for r in rows if r['stages_after'] > r['stages_before']])


def family_split(g, ev0, ev1):
    f = collections.defaultdict(lambda: [0.0, 0.0])
    for k, (a, b) in enumerate(zip(ev0, ev1)):
        f[g.data[k]['c']][0] += a[0]; f[g.data[k]['c']][1] += b[0]
    return {k: dict(before=round(v[0], 3), after=round(v[1], 3), delta_pct=round(100 * (v[1] - v[0]) / v[0], 3) if v[0] else None) for k, v in sorted(f.items())}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('input', type=Path); ap.add_argument('out', type=Path)
    ap.add_argument('--reach', type=float, default=None); a = ap.parse_args()
    d, sha = load(a.input); reach = a.reach or d['constraints']['per_hop_um']
    g = Graph(d, reach); base = {n: dict(i) for n, i in g.inst.items()}; ev0 = g.evaluate(base); t0 = totals(g, ev0)
    fixed = [n for n in base if n.startswith(FIXED_PREFIX)]
    movable = [n for n in base if n not in fixed]
    singles = [n for n in movable if base[n]['m'] not in ('qfd_tile_nk', 'qfd_xcst_s', 'qfd_xcst_n', 'qfd_xcol_w', 'qfd_xcol_e')]
    arrays = [n for n in movable if n not in singles]
    by_master = collections.defaultdict(list)
    for n in singles: by_master[base[n]['m']].append(n)
    groups = [v for v in by_master.values() if len(v) > 1]
    out = dict(schema='opentallas.qwen.orientation-search.v1', input=str(a.input), input_sha256=sha, source_commit=d.get('source_commit'),
               die=d['die'], reach_um=reach, coverage=dict(instances=len(base), data_buses=len(g.data), ctrl_buses=len(g.ctrl),
               missing_or_width_mismatch_buses=len(g.missing), missing=g.missing, fixed_orientation=fixed),
               baseline=t0, candidates=[], qualification=False)

    def record(name, desc, model, moves):
        ev = g.evaluate(model); t = totals(g, ev)
        out['candidates'].append(dict(name=name, description=desc, totals=t,
            delta=dict(bit_um=round(t['bit_um'] - t0['bit_um'], 3), pct=round(100 * (t['bit_um'] - t0['bit_um']) / t0['bit_um'], 4),
                       relay_bit_stages=t['relay_bit_stages'] - t0['relay_bit_stages'], worst_pair_um=round(t['worst_pair_um'] - t0['worst_pair_um'], 3)),
            moves=moves, families=family_split(g, ev0, ev), buses=regressions(g, ev0, ev), clock_reset_moves=ctrl_movement(g, base, model),
            qualification=False))
        return ev

    # 1) Explicit historical Band2 east-port MX candidate, re-scored on the current graph.
    m = {n: dict(i) for n, i in base.items()}; m['sp_port_tiles_2_f1']['o'] = 'MX'
    record('band2_f1_MX', 'Historical best (old graph 3.84%): sp_port_tiles_2_f1 R0->MX, re-scored on the current graph', m,
           [dict(instance='sp_port_tiles_2_f1', frm='R0', to='MX')])
    # 1b) Band2 coherent flip (mirror of adopted Band0/Band1 pattern: west port + res_ser + lanes MX)
    m = {n: dict(i) for n, i in base.items()}
    for n in ('sp_port_tiles_2', 'sp_res_ser_2', 'sp_band_lanes_2'): m[n]['o'] = 'MX'
    record('band2_coherent_MX', 'Band2 group follows Band0/Band1: sp_port_tiles_2, sp_res_ser_2, sp_band_lanes_2 R0->MX', m,
           [dict(instance=n, frm='R0', to='MX') for n in ('sp_port_tiles_2', 'sp_res_ser_2', 'sp_band_lanes_2')])
    # 2) Exhaustive single-instance orientation sweep (each instance alone), singles only.
    single_rows = []
    for n in singles:
        ks = g.inc.get(n)
        if not ks: continue
        for o in ORIENTS:
            if o == base[n]['o']: continue
            m = {k: dict(v) for k, v in base.items()} if False else base
            cur = base[n]['o']; base[n]['o'] = o
            new = [g.bus(g.data[k], base) for k in ks]; base[n]['o'] = cur
            dbit = sum(x[0] for x in new) - sum(ev0[k][0] for k in ks)
            dstage = sum((x[2] - ev0[k][2]) * g.data[k]['n'] for x, k in zip(new, ks))
            dlong = max(x[1] - ev0[k][1] for x, k in zip(new, ks))
            single_rows.append(dict(instance=n, master=base[n]['m'], frm=cur, to=o, incident_buses=len(ks),
                                    incident_bit_um_before=round(sum(ev0[k][0] for k in ks), 3), delta_bit_um=round(dbit, 3),
                                    delta_relay_bit_stages=dstage, max_leg_increase_um=round(dlong, 3)))
    single_rows.sort(key=lambda r: r['delta_bit_um'])
    out['single_flip_table'] = single_rows[:60]
    # 3) Coordinate descent, guarded and unguarded, singles then arrays.
    for guard in (True, False):
        m = {n: dict(i) for n, i in base.items()}; ev = list(ev0)
        mv = descend(g, m, ev, singles, guard)
        record(f'singles_descent_{"guarded" if guard else "free"}', 'Greedy orientation descent over non-array masters' +
               (' (no incident bus gains a relay stage or exceeds the die worst leg)' if guard else ' (bit-um only)'), m, mv)
        mv2 = swap_search(g, m, ev, groups, guard)
        record(f'singles_descent_swaps_{"guarded" if guard else "free"}', 'Above + identical-master slot swaps (cbuf_g, crom_g, band_upper, res_ser, band_lanes)', m, mv + mv2)
        mv3 = descend(g, m, ev, arrays, guard, sweeps=3)
        record(f'all_descent_{"guarded" if guard else "free"}', 'Above + per-instance orientation of array masters (tile_nk, xcst, xcol)', m, mv + mv2 + mv3)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'orientation_search.json').write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(dict(baseline=t0, cands=[dict(name=c['name'], delta=c['delta'], moves=len(c['moves']),
          stage_incr=len(c['buses']['stage_increases']), clock_moves=len(c['clock_reset_moves'])) for c in out['candidates']],
          top_single=single_rows[:12]), indent=1))


if __name__ == '__main__':
    main()
