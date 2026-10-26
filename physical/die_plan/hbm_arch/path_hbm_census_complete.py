#!/usr/bin/env python3
"""Per-bit FT census completion (PATH-HBM-R2/PLAN/CENSUS, 2026-10-26).

Adds explicit per-bit relay FF sites (bit_sites_um + bit_site_cell_um) to EVERY ft slot with stations > 1 that has
no bit_sites_um yet. Already-sited slots, cores, ports, windows and station counts are never changed (0 cycles), so
the pass can be chained after any other plan pass.

Method = the existing sited slots' model (path_hbm_perbit_m5.py / path_hbm_perbit_nudge.py / B1 census):
  * cell 1.404 x 0.27 um on legal rows (RowAllocator, columns 4.32 + k*2.16, rows 4.32 + k*0.27, 4.32-um inset);
  * obstacles = schema.placed_macro_boxes(halo 8.64) (hard cores + LEF contents); every existing FT bit site,
    internal-station register and clock branch buffer / leg repeater (+ check.CLOCK_BUF_HALO_UM) is reserved,
    so all FF xy stay unique per type;
  * nominal station j of bit b (j = 1..k-1): the slot's regs_um[j] shifted by the bit's own ribbon offset when the
    slot has regs_um (stations stay clustered at the planned station), else check.py's own interpolation point on
    the bit's zroute (L_b*j/k) -- exactly the station point check.py judges for an unsited slot;
  * a nominal station inside a halo is first snapped across the closest halo side (cells line the corridor edge);
    a chain that still hits a halo or has a leg > budget is re-sited per bit by ft_sites_unblock.layered()
    (exact L1 reachability, same station count); every paired-bit leg pin_i -> s1 .. -> pin_o <= 403 um
    (plan reach 405, METHODOLOGY 12.1e) after legalisation, else the slot fails closed (left unsited, reported).
  * regs_um is never rewritten (the planned station points keep the die-level reach / G0C hop scan unchanged; a
    centroid refresh moved q_b101 L139x8 into a new G0C 370-um WARN); the report gives each slot's max drift
    between bit-site centroid and planned station (centroid_vs_regs_um).
Geometry proposal only, never a route receipt.
Usage: path_hbm_census_complete.py --src <plan dir> --out <new plan dir> [--types a,b] [--jobs N]
"""
import argparse, json, shutil, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools/die_plan')]
import schema as S, check as C
import ft_sites_unblock as U
from gen_phys import type_pins
from tools.die_trial.legal_sites import RowAllocator

CELL = np.array([1.404, .27]); HALO = 8.64; LEG = 403.0
BUDGETS = (400.0, 392.0, 380.0)      # layered() target budgets; legalisation keeps the rest of LEG
RADII = (6.0, 20.0, 60.0)
OFFSET_SCALES = (1.0, .5, 0.0)
INSET = {'E': (-1, 0), 'W': (1, 0), 'N': (0, -1), 'S': (0, 1)}


def man(a, b): return float(abs(a[0] - b[0]) + abs(a[1] - b[1]))


def site_type(raw, tn):
    t = raw['partition_types'][tn]; W, H = t['outline_um']; U.FRAME[:] = [W, H]
    boxes = list(S.placed_macro_boxes(t, halo=HALO).values())
    alloc = RowAllocator((4.32, 4.32, W - 4.32, H - 4.32), blocked=boxes, cell_size=CELL, column_pitch=2.16,
                         row_pitch=.27, origin=(4.32, 4.32))
    res = lambda x, y, w, h, m=0.0: alloc.reserve_rectangle((x - m + .01, y - m + .01, x + w + m - .01, y + h + m - .01))
    for s in t.get('ft_slots', []):
        cw, ch = s.get('bit_site_cell_um') or CELL
        for st in s.get('bit_sites_um') or []:
            for x, y in st: res(x, y, cw, ch)
    for s in t.get('internal_stations', []) or []:
        for x, y in s.get('regs_um', []) or []: res(x, y, *CELL)
    hb = C.CLOCK_BUF_HALO_UM + .5
    for b in (t.get('clock') or {}).get('branch_buffers') or []:
        for q in [b] + list(b.get('leg_repeaters') or []):
            ll = q.get('cell_ll_um') or [q['xy'][0] - .702, q['xy'][1] - .135]; wh = q.get('cell_wh_um') or [1.404, .27]
            res(ll[0], ll[1], wh[0], wh[1], hb)
            res(q['xy'][0] - CELL[0], q['xy'][1] - CELL[1], 0, 0, hb + CELL[0])  # point-based halo check in check.py
    model = S.Plan(raw); pins = {}
    for bus, bit, _l, x, y, face in type_pins(model, tn): pins.setdefault(bus, {})[bit] = (x, y, face)

    def sid(q):
        ix = round((q[0] - alloc.cw / 2 - alloc.ox) / alloc.cp); iy = round((q[1] - alloc.ch / 2 - alloc.oy) / alloc.rp)
        return (iy - alloc.iy0) * alloc.nx + ix - alloc.ix0

    lo = np.array([4.32 + CELL[0], 4.32 + CELL[1]]); hi = np.array([W - 4.32 - CELL[0], H - 4.32 - CELL[1]])

    def snap(p, depth=3):
        """nearest point outside every halo box (exit across the closest box side, a few levels for abutting halos)."""
        p = np.clip(np.array(p, float), lo, hi)
        if not U.inside(p, boxes): return tuple(p)
        frontier = [p]; best = None
        for _ in range(depth):
            nxt = []
            for q in frontier:
                for x0, y0, x1, y1 in boxes:
                    if not (x0 < q[0] < x1 and y0 < q[1] < y1): continue
                    m = CELL[0] + .5
                    for c in ((x0 - m, q[1]), (x1 + m, q[1]), (q[0], y0 - m), (q[0], y1 + m)):
                        c = np.clip(np.array(c), lo, hi)
                        if U.inside(c, boxes): nxt.append(c)
                        elif best is None or man(c, p) < man(best, p): best = c
            if best is not None: return tuple(best)
            frontier = sorted(nxt, key=lambda c: man(c, p))[:16]
        return tuple(p)

    def legalise(ps, A, B):
        """sequential row-site legalisation of one bit's nominal chain; None if a leg would exceed LEG."""
        got = []
        for j, p in enumerate(ps):
            prev = A if j == 0 else got[-1]; nxt = B if j == len(ps) - 1 else ps[j + 1]
            q = None; rejected = []
            try:
                for rad in RADII:
                    for _ in range(64):
                        try: c = alloc.allocate(np.array(p), 1, max_radius_um=rad)[0][0]
                        except ValueError: break
                        if man(prev, c) <= LEG - 1e-3 and man(c, nxt) <= LEG - 1e-3 and (j < len(ps) - 1 or man(c, B) <= LEG - 1e-3):
                            q = c; break
                        rejected.append(sid(c))
                    if q is not None: break
            finally: alloc.used.difference_update(rejected)
            if q is None:
                alloc.used.difference_update(sid(g) for g in got); return None
            got.append(q)
        ch = [A, *got, B]
        if max(man(u, v) for u, v in zip(ch, ch[1:])) > LEG + 1e-6:
            alloc.used.difference_update(sid(g) for g in got); return None
        return got

    rep = {}
    for s in sorted(t.get('ft_slots', []), key=lambda s: -s['width']):
        k = int(s.get('stations', 1)); name = s['name']
        if s.get('bit_sites_um') or k < 2: continue
        t0 = time.time(); nb = s['width'] + 1; sites = []
        pi, po = pins.get(name + '_i', {}), pins.get(name + '_o', {})
        r = dict(bits=nb, stations=k, layered_bits=0, regs_based=bool(s.get('regs_um')))
        try:
            if len(pi) != nb or len(po) != nb: raise ValueError(f'pins {len(pi)}/{len(po)} != width+1 {nb}')
            regs = s.get('regs_um') if s.get('regs_um') and len(s['regs_um']) == k else None
            am = np.mean([pi[b][:2] for b in range(nb)], axis=0); bm = np.mean([po[b][:2] for b in range(nb)], axis=0)
            sites = [[None] * nb for _ in range(k - 1)]; worst = 0.0
            for b in range(nb):
                Ap, Bp = pi[b], po[b]; A = np.array(Ap[:2]); B = np.array(Bp[:2])
                ia = (Ap[0] + INSET[Ap[2]][0], Ap[1] + INSET[Ap[2]][1]); ib = (Bp[0] + INSET[Bp[2]][0], Bp[1] + INSET[Bp[2]][1])
                rt = C.zroute(ia, ib, Ap[2], Bp[2]); L = C.plen(rt)
                interp = [tuple(C.point_at(rt, L * j / k)) for j in range(1, k)]
                cands = []
                if regs:   # ribbon offset scaled down until the stations clear the halos (scale 0 = pure regs_um cluster)
                    for sc in OFFSET_SCALES:
                        cands.append([tuple(np.array(regs[j]) + sc * ((1 - j / k) * (A - am) + (j / k) * (B - bm))) for j in range(1, k)])
                cands.append(interp)
                got = None
                for ps in cands:
                    ps = [snap(p) for p in ps]; ch = [tuple(A), *ps, tuple(B)]
                    if not any(U.inside(p, boxes) for p in ps) and max(man(u, v) for u, v in zip(ch, ch[1:])) <= BUDGETS[0]:
                        got = legalise(ps, A, B)
                        if got is not None: break
                if got is None:
                    for bud in BUDGETS:
                        for ps in cands:
                            try: lp = U.layered(tuple(A), tuple(B), ps, k, boxes, bud + U.LAYER_SLACK, tn, name, b)
                            except SystemExit: continue
                            got = legalise(lp, A, B)
                            if got is not None: break
                        if got is not None: break
                    r['layered_bits'] += 1
                if b and b % 500 == 0: print(tn, name, 'bit', b, 'layered', r['layered_bits'], round(time.time() - t0, 1), flush=True)
                if got is None: raise ValueError(f'bit {b} {A.tolist()}->{B.tolist()}: no legal chain at {k} stations')
                ch = [A, *got, B]; worst = max(worst, max(man(u, v) for u, v in zip(ch, ch[1:])))
                for j, q in enumerate(got): sites[j][b] = [round(float(q[0] - CELL[0] / 2), 6), round(float(q[1] - CELL[1] / 2), 6)]
        except ValueError as e:
            r.update(verdict='FAIL', reason=str(e)); rep[name] = r; print(tn, name, 'FAIL', e, flush=True)
            # release this slot's partial sites
            for st in sites:
                alloc.used.difference_update(sid(np.array(p) + CELL / 2) for p in st if p is not None)
            continue
        s['bit_site_cell_um'] = CELL.tolist(); s['bit_sites_um'] = sites
        if s.get('regs_um') and len(s['regs_um']) == k:   # planned stations kept (die-level reach/G0C unchanged); report drift
            cen = (np.array(sites) + CELL / 2).mean(axis=1)
            r['centroid_vs_regs_um'] = round(float(np.abs(cen - np.array(s['regs_um'][1:])).sum(axis=1).max()), 3)
        s['note'] = (s.get('note', '') + f' | CENSUS-COMPLETE: {nb}x{k-1} per-bit FF sites added (stations unchanged)').lstrip(' |')
        r.update(verdict='PASS', ff_sites=nb * (k - 1), max_bit_hop_um=round(worst, 3), sec=round(time.time() - t0, 1))
        rep[name] = r; print(tn, name, 'PASS', r, flush=True)
    return t.get('ft_slots', []), rep


def _work(arg):
    raw, tn = arg
    return tn, *site_type(raw, tn)


def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('--src', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path); ap.add_argument('--types'); ap.add_argument('--jobs', type=int, default=8)
    a = ap.parse_args()
    if a.out.exists(): raise SystemExit('output must be new')
    raw = json.loads((a.src / 'die_plan.json').read_text()); before = S.Plan(json.loads(json.dumps(raw)))
    sel = a.types.split(',') if a.types else [tn for tn, t in raw['partition_types'].items()
                                              if any(int(s.get('stations', 1)) > 1 and not s.get('bit_sites_um') for s in t.get('ft_slots', []))]
    frozen = {tn: json.dumps({k: v for k, v in t.items() if k != 'ft_slots'}, sort_keys=True) for tn, t in raw['partition_types'].items()}
    sited = {(tn, s['name']): json.dumps(s, sort_keys=True) for tn, t in raw['partition_types'].items() for s in t.get('ft_slots', []) if s.get('bit_sites_um')}
    stations = {(tn, s['name']): s.get('stations', 1) for tn, t in raw['partition_types'].items() for s in t.get('ft_slots', [])}
    with Pool(min(a.jobs, len(sel)) or 1) as pool:
        out = pool.map(_work, [(raw, tn) for tn in sel], chunksize=1)
    rep = {}
    for tn, slots, r in out: raw['partition_types'][tn]['ft_slots'] = slots; rep[tn] = r
    # invariants: nothing but unsited slots changed
    for tn, t in raw['partition_types'].items():
        assert json.dumps({k: v for k, v in t.items() if k != 'ft_slots'}, sort_keys=True) == frozen[tn], tn
        for s in t.get('ft_slots', []):
            assert s.get('stations', 1) == stations[tn, s['name']], (tn, s['name'])
            if (tn, s['name']) in sited: assert json.dumps(s, sort_keys=True) == sited[tn, s['name']], (tn, s['name'])
    after = S.Plan(json.loads(json.dumps(raw)))
    delta = {lid: after.lane_latency(lid)['cycles'] - before.lane_latency(lid)['cycles'] for lid in after.lanes
             if after.lane_latency(lid)['cycles'] != before.lane_latency(lid)['cycles']}
    summ = {}
    for tn, r in rep.items():
        ok = [v for v in r.values() if v['verdict'] == 'PASS']
        w = max(ok, key=lambda v: v['max_bit_hop_um'], default=None)
        summ[tn] = dict(slots_sited=len(ok), ff_sites_added=sum(v['ff_sites'] for v in ok),
                        max_bit_hop_um=w and w['max_bit_hop_um'], worst_slot=w and next(n for n, v in r.items() if v is w),
                        failures={n: v['reason'] for n, v in r.items() if v['verdict'] != 'PASS'})
    shutil.copytree(a.src, a.out)
    (a.out / 'die_plan.json').write_text(json.dumps(raw, indent=1) + '\n')
    fails = {tn: v['failures'] for tn, v in summ.items() if v['failures']}
    (a.out / 'census_complete_report.json').write_text(json.dumps(dict(
        src=str(a.src / 'die_plan.json'), verdict='PASS' if not fails else 'FAIL', total_ff_sites_added=sum(v['ff_sites_added'] for v in summ.values()),
        types=summ, slots=rep, failures=fails, lane_cycle_delta=delta,
        scope='geometry proposal (per-bit FF sites only); not a route receipt'), indent=1) + '\n')
    print('COMPLETE', 'FAIL' if fails else 'PASS', json.dumps(fails), 'cycle_delta', json.dumps(delta), flush=True)
    if fails: sys.exit(2)


if __name__ == '__main__': main()
