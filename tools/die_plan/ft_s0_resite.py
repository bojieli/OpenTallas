#!/usr/bin/env python3
"""DIE-HBM-58/G0C 11-02: class re-site of normal FT station chains whose REAL first hop (S0 at the input pin) is long.

Why: Codex 54687a1ee (11-01, "normal FT S0 probe and reach model parity") made check.py / g2 use the site face_flops
really builds S0 at: the input pin (1 um inset), not the slot's regs_um[0] hint.  Plans sited before that (HBM d44c)
kept S1..S(k-1) where they had been planned against a moved-in S0, so the real S0->S1 hop is 400-950 um on about 60
slots per die side (G0 stations/hops, G0C reach 0.9 x 405, street_die_leg).  This is a plan fix, not a gate change.

Per normal FT slot (die_hop_scan.normal_slot; exact native full-stage and registered landing inputs are skipped) with
>= 2 stations whose per-bit chain [input site, S1 .. S(k-1), output pin] has a hop > --limit (default 0.9 x 405 =
364.5 um, the G0C die reach), the k-1 internal stations are re-sited by ft_corridor.place_slot (DP along the in->out
Manhattan path among positions where the whole bit band is in free space; obstacles = placement_obstacles
.placement_boxes, the same union the G0 geometry gate uses, + 1.08-um keep-off; one bit per legal row site; every other
slot's explicit bit sites stay reserved).  The station count is kept when a chain fits; otherwise +1..+--max-add
stations are tried and every added cycle is listed in the ledger (re-run gen.py latency --inplace after).  A slot
no count fits is left unchanged and listed.  Windows, pins, outlines, cores and other slots never change.

regs_um[1:] = per-stage medoid bit site (a real free site, never a centroid inside a core).

    python3 tools/die_plan/ft_s0_resite.py PLAN.json OUT_PLAN.json LEDGER.json [--types a,b] [--slots T/S,..] [--limit 364.5]
    python3 tools/die_plan/ft_s0_resite.py --medoid-fix PLAN.json OUT_PLAN.json T/S,...   (re-derive regs_um only)
"""
import argparse, json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import schema as S  # noqa: E402
import ft_corridor as FC  # noqa: E402
from die_hop_scan import pin_table, normal_slot, station_site, input_site, md  # noqa: E402
from placement_obstacles import placement_boxes  # noqa: E402
from tools.die_trial.legal_sites import RowAllocator  # noqa: E402


def chain_hops(slot, pi, po):
    """max per-bit hop of [input site, S1..S(k-1), output pin] with the check.py / g2 normal-S0 convention."""
    k = int(slot.get('stations', 1)); worst = 0.0
    for bit in sorted(set(pi) | set(po)):
        ap = pi.get(bit) or po[bit]; bp = po.get(bit) or pi[bit]
        pts = [station_site(slot, j, bit, ap, bp, normal=True) for j in range(k)] + [bp[:2]]
        worst = max(worst, max(md(p, q) for p, q in zip(pts, pts[1:])))
    return worst


def stage_medoids(slot):
    """per internal stage, the centre of the real bit site nearest the band centroid (die lane geometry / street
    checks read regs_um[j] as the stage position; a centroid of a band split around a core can fall inside it)."""
    cw, ch = slot['bit_site_cell_um']; out = []
    for st in slot['bit_sites_um']:
        c = np.asarray(st, float) + (cw / 2, ch / 2)
        out.append(c[int(np.argmin(np.abs(c - c.mean(axis=0)).sum(axis=1)))].round(4).tolist())
    return out


def resite_type(P, raw, tn, limit, max_add, only=None):
    rt = raw['partition_types'][tn]; ty = P.types[tn]
    pins = pin_table(P, tn)
    w, h = ty['outline_um']
    todo = []
    for s in rt.get('ft_slots') or []:
        if int(s.get('stations', 1)) < 2 or (only and s['name'] not in only):
            continue
        if not normal_slot(P, tn, s['name']):
            continue
        pi, po = pins[s['name'] + '_i'], pins[s['name'] + '_o']
        if not pi and not po:
            continue
        hb = chain_hops(s, pi, po)
        if hb > limit + 1e-6:
            todo.append((s, hb))
    if not todo:
        return []
    boxes = list(placement_boxes(ty, halo=FC.KEEPOFF).values())
    alloc = RowAllocator((4.32, 4.32, w - 4.32, h - 4.32), blocked=boxes, cell_size=FC.CELL, column_pitch=2.16,
                         row_pitch=.27, origin=(4.32, 4.32))
    names = {s['name'] for s, _ in todo}
    for s in rt['ft_slots']:
        if s['name'] in names or not s.get('bit_sites_um'):
            continue
        cw, ch = s['bit_site_cell_um']
        for st in s['bit_sites_um']:
            for x, y in st:
                alloc.reserve_rectangle((x, y, x + cw, y + ch))
    ledger = []
    for s, before in sorted(todo, key=lambda t: -t[0]['width']):
        name = s['name']; wd = int(s['width']) + 1; k0 = int(s['stations'])
        pi, po = pins[name + '_i'], pins[name + '_o']
        # bit b of the bundle: input site (the real S0) .. output pin; an output-only epoch starts at its out pin
        a = np.array([input_site(pi.get(b) or po[b]) for b in range(wd)], float)
        bpt = np.array([(po.get(b) or pi[b])[:2] for b in range(wd)], float)
        rec = dict(type=tn, slot=name, width=s['width'], stations_before=k0, hop_before_um=round(before, 1))
        done = None; errs = []
        for k in range(k0, k0 + max_add + 1):
            trial = dict(s, stations=k)
            saved = set(alloc.used)
            try:
                sites, cents, path, led = FC.place_slot(trial, a, bpt, s['in_face'], s['out_face'], w, h, boxes, alloc,
                                                        limit)
                done = (k, sites, cents, led); break
            except ValueError as e:
                alloc.used = saved; errs.append(f'k={k}: {str(e)[:120]}')
        if not done:
            rec.update(kept='no chain within limit', tried=errs); ledger.append(rec)
            print(f'{tn}/{name}: KEPT ({errs[-1]})', flush=True); continue
        k, sites, cents, led = done
        s['stations'] = k
        s['bit_site_cell_um'] = list(FC.CELL)
        s['bit_sites_um'] = [(p - np.array([FC.CELL[0] / 2, FC.CELL[1] / 2])).round(6).tolist() for p in sites]
        s['regs_um'] = [a.mean(axis=0).round(4).tolist()] + stage_medoids(s)
        after = chain_hops(s, pi, po)
        rec.update(stations_after=k, added_cycles=k - k0, hop_after_um=round(after, 1), hops_um=led.get('hops_um'),
                   len_um=led.get('len_um'), max_alloc_disp_um=led.get('max_alloc_disp_um'))
        ledger.append(rec)
        print(f'{tn}/{name}: {s["width"]} b, k {k0}->{k}, hop {before:.0f}->{after:.0f} um', flush=True)
    return ledger


def medoid_fix(plan, out, slots):
    raw = json.loads(Path(plan).read_text()); n = 0
    for x in slots:
        t, sn = x.split('/', 1)
        s = next(s for s in raw['partition_types'][t]['ft_slots'] if s['name'] == sn)
        if s.get('bit_sites_um'):
            s['regs_um'] = s['regs_um'][:1] + stage_medoids(s); n += 1
    Path(out).write_text(json.dumps(raw, indent=1)); print(f'medoid regs_um on {n} slots')


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == '--medoid-fix':
        return medoid_fix(argv[1], argv[2], [x for x in argv[3].split(',') if x])
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('plan'); ap.add_argument('out'); ap.add_argument('ledger')
    ap.add_argument('--types', default='', help='comma list (default: every type)')
    ap.add_argument('--slots', default='', help='comma list of TYPE/SLOT to restrict to')
    ap.add_argument('--limit', type=float, default=0.9 * 405.0)
    ap.add_argument('--max-add', type=int, default=3)
    a = ap.parse_args(argv)
    raw = S.load(a.plan); P = S.Plan(raw, Path(a.plan))
    want = {t for t in a.types.split(',') if t}
    only = {}
    for x in filter(None, a.slots.split(',')):
        t, sn = x.split('/', 1); only.setdefault(t, set()).add(sn)
    ledger = []
    for tn in sorted(raw['partition_types']):
        if (want and tn not in want) or (only and tn not in only):
            continue
        ledger += resite_type(P, raw, tn, a.limit, a.max_add, only.get(tn))
    Path(a.out).write_text(json.dumps(raw, indent=1))
    summ = dict(slots=len(ledger), resited=sum(1 for r in ledger if 'stations_after' in r),
                kept=[f"{r['type']}/{r['slot']}" for r in ledger if 'kept' in r],
                added_cycles={f"{r['type']}/{r['slot']}": r['added_cycles'] for r in ledger if r.get('added_cycles')})
    Path(a.ledger).write_text(json.dumps(dict(summary=summ, limit_um=a.limit, slots=ledger), indent=1))
    print(json.dumps(summ, indent=1))


if __name__ == '__main__':
    main()
