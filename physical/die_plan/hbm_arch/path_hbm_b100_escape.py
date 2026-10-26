#!/usr/bin/env python3
"""q_b100 east-escape re-lattice (PATH-HBM, 2026-10-26): chainable pass after path_hbm_g0c_fix.py + path_hbm_perbit_nudge.py.

Problem (b1n4): the lattice snap put the third hard-core column at x=509.76, so its east edge sits 6.05 um from the
q_b100 E face (17.4 um before the snap) and the L5x2 M4/M6 E-face pins (out window y 366..862, all in front of that
column) have a 6-um escape.

Why a 3-column re-lattice: three 218.592-um columns in a 734.4-um outline leave 78.624 um for W strip + C01 + C12 + E
strip; on the 8.64-um lattice every gap is 6.048 + k*8.64 (core-core >= 8.64 halo). E >= 17 forces col2 <= 492.48
(E 23.328); with col0 kept at 17.28 that leaves C01 + C12 = 38.016 = 23.328 + 14.688 and a 14.688 channel has no
FF site (8.64 FF halo both sides), so either C01 or C12 dies and the L5x2 per-bit hop C01 -> E (~474 um) or W -> C12
(~474) breaks 403. col2 -> 501.12 alone gives E 14.688 and kills C12 (col1 east 486.432). The only lattice triple with
E >= 17 and FF columns in both core channels is 8.64 / 250.56 / 492.48 (gaps W 8.64, C01 = C12 = E = 23.328). The
enumeration is recorded in the report.

RESULT (b1n4 -> b1n4_b100): the 17-um target is not reachable without losing the W strip (L123x1 then has no legal
chain, see report why_not_E_ge_17), so the default is the best W-strip-keeping triple 17.28 / 259.2 / 501.12:
E escape 6.048 -> 14.688 um, W 2 / C01 3 / C12 3 FF columns. L5x2 (4 stations, 3 per-bit stages; b1n4 stacked stages
1+2 in C01) is re-staged one stage per channel W strip -> C01 -> C12 (--stages W,C01,C12; legs ~32/260/252/254 um).
Every other per-bit site that now hits a core halo is moved by path_hbm_perbit_nudge.nudge_type (L70x1 / L123x1 leave
the W strip, which has no FF column at col0 = 8.64). Hard-core tied coordinates (core clock taps, internal-station
launch points and core-edge capture landings) move with their core; internal-station registers that now sit on a core
are pulled to the nearest macro-free point and re-sited with the SAME station count if a hop breaks. Station counts never
change (0 cycles; lane latency delta recorded). Geometry proposal only, never a route receipt.
Usage: path_hbm_b100_escape.py --src <plan dir> --out <new plan dir> [--type q_b100] [--cols 8.64,250.56,492.48]

b1n6 (2026-10-26) generalisation for q_b101 / q_b101_nw: --slot none skips the W->E re-stage; --recentre SLOT moves that
unsited slot's planned station points regs_um[1:] (census_complete sites the bits around them) to the centre x of the
nearest FF-bearing core channel (C01/C12), y unchanged. q_b101 L12x1 (E->W, 2,997 bits, 3 stations) had no legal chain
because the idx columns 8.64/241.92/475.2 leave C01 = C12 = 14.688 um (no FF column inside the two 8.64 halos); cols
8.64/250.56/492.48 give C01 = C12 = 23.328 um (2 FF columns each), E strip 31.968 -> 14.688 um (no per-bit site uses the
E strip beside the cores; the E face pin escape stays 14.688 um, as q_b100 after its escape pass).
"""
import argparse, json, math, shutil, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools/die_plan'), str(HERE)]
import schema as S, check as C
from gen_phys import type_pins
from tools.die_trial.legal_sites import RowAllocator
from cores_b2 import RelayRouter, free_point
import path_hbm_perbit_nudge as NU
G = 8.64; HALO = 8.64; CELL = np.array([1.404, .27]); LEG = 403.0; LIM = 364.0; INSET = 4.32; CP = 2.16; ESC_MIN = 17.0  # brief target; unreachable with the W strip kept (see report why_not_E_ge_17)


def ff_cols(lo, hi):
    """FF columns (x = 4.32 + k*2.16, width 1.404) fully inside [lo + halo, hi - halo]."""
    a, b = lo + HALO, hi - HALO
    return [round(INSET + k * CP, 4) for k in range(400) if INSET + k * CP >= a - 1e-6 and INSET + k * CP + CELL[0] <= b + 1e-6]


def strips(cols, cw, W):
    """W strip, C01, C12, E strip: (gap um, FF column x list)."""
    xs = sorted(cols); out = {}
    out['W'] = (xs[0], [c for c in ff_cols(-HALO + INSET, xs[0]) if c >= INSET])
    out['C01'] = (round(xs[1] - xs[0] - cw, 4), ff_cols(xs[0] + cw, xs[1]))
    out['C12'] = (round(xs[2] - xs[1] - cw, 4), ff_cols(xs[1] + cw, xs[2]))
    out['E'] = (round(W - xs[2] - cw, 4), [c for c in ff_cols(xs[2] + cw, W - INSET + HALO) if c + CELL[0] <= W - INSET + 1e-6])
    return out


def enumerate_cols(cw, W):
    rows = []
    for i0 in range(0, 4):
        for i1 in range(20, 40):
            for i2 in range(40, 70):
                xs = [i0 * G, i1 * G, i2 * G]
                if xs[0] < 0 or xs[2] + cw > W or xs[1] - xs[0] - cw < HALO - 1e-6 or xs[2] - xs[1] - cw < HALO - 1e-6: continue
                st = strips(xs, cw, W)
                rows.append(dict(cols=[round(v, 3) for v in xs], gaps={k: v[0] for k, v in st.items()},
                                 ff_cols={k: len(v[1]) for k, v in st.items()}))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--src', required=True, type=Path); ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--type', default='q_b100'); ap.add_argument('--cols', default='17.28,259.2,501.12')
    ap.add_argument('--stages', default='W,C01,C12', help='channel per per-bit stage of --slot')
    ap.add_argument('--slot', default='L5x2', help='W->E per-bit slot re-staged one stage per channel (C01, C12, E); none = skip')
    ap.add_argument('--recentre', default='', help='comma list of unsited slots whose regs_um[1:] move to the nearest opened channel centre')
    a = ap.parse_args()
    if a.out.exists(): raise SystemExit('output must be new')
    raw = json.loads((a.src / 'die_plan.json').read_text()); before = S.Plan(json.loads(json.dumps(raw)))
    tn = a.type; t = raw['partition_types'][tn]; W, H = t['outline_um']
    hcs = t['hard_cores']; cw = hcs[0]['outline_um'][0]
    assert all(abs(h['outline_um'][0] - cw) < 1e-6 and not any(h.get('track_offset_um', [0, 0])) for h in hcs)
    old_cols = sorted({round(h['origin_um'][0], 4) for h in hcs}); new_cols = [float(v) for v in a.cols.split(',')]
    assert len(old_cols) == 3 == len(new_cols), (old_cols, new_cols)
    for v in new_cols:
        if abs(v / G - round(v / G)) > 1e-6: raise SystemExit(f'column {v} off the {G}-um lattice')
    cmap = dict(zip(old_cols, new_cols))
    st_old, st_new = strips(old_cols, cw, W), strips(new_cols, cw, W)
    enum = enumerate_cols(cw, W)
    keep_w = [r for r in enum if r['ff_cols']['W'] >= 2 and r['ff_cols']['C01'] >= 2 and r['ff_cols']['C12'] >= 2]
    keep_w.sort(key=lambda r: (-r['gaps']['E'], -min(r['ff_cols']['C01'], r['ff_cols']['C12'])))
    e17 = [r for r in enum if r['gaps']['E'] >= ESC_MIN and r['ff_cols']['C01'] >= 2 and r['ff_cols']['C12'] >= 2]
    if len(st_new['W'][1]) < min(2, len(st_old['W'][1])) or len(st_new['C01'][1]) < 2 or len(st_new['C12'][1]) < 2:
        raise SystemExit(f'--cols {new_cols}: W {st_new["W"][1]} / C01 {st_new["C01"][1]} / C12 {st_new["C12"][1]} not legal')
    rep = dict(type=tn, src=str(a.src / 'die_plan.json'), cols_before=old_cols, cols_after=new_cols,
               east_escape_um=dict(before=st_old['E'][0], after=st_new['E'][0]),
               strips_before={k: dict(gap_um=v[0], ff_columns=len(v[1])) for k, v in st_old.items()},
               strips_after={k: dict(gap_um=v[0], ff_columns=len(v[1])) for k, v in st_new.items()},
               triples_keeping_W_C01_C12_ff_best_E_first=keep_w[:6],
               triples_with_E_ge_17_and_ff_in_C01_C12=e17,
               why_not_E_ge_17=('every triple with E >= 17 and FF columns in C01 and C12 has col0 = 8.64 (W strip 0 FF columns); '
                                'L123x1 (S x 0.5..9.1 -> N x 8.64..17.28, 5 stations, 4 per-bit stages) then needs '
                                '(238.3 - x_s) + 1555.2 + (238.3 - x_n) ~ 2022 um > 5 x 403 = 2015 um for its low bits via C01: '
                                'proven by path_hbm_perbit_nudge (no legal chain) on cols 8.64/250.56/492.48'),
               alternatives=dict(col2_501_12_only=dict(cols=[old_cols[0], old_cols[1], 501.12],
                                 **{k: dict(gap_um=v[0], ff_columns=len(v[1])) for k, v in strips([old_cols[0], old_cols[1], 501.12], cw, W).items()}),
                                 col1_259_2_col2_492_48=dict(cols=[old_cols[0], 259.2, 492.48],
                                 **{k: dict(gap_um=v[0], ff_columns=len(v[1])) for k, v in strips([old_cols[0], 259.2, 492.48], cw, W).items()})),
               moved_cores=[], internal_stations=dict(endpoints_moved=0, regs_pulled=0, restationed=[], fails=[]), taps_moved=0)

    # ---- 1) cores + tied coordinates
    oldbox = {}; dxs = {}
    for h in hcs:
        ox, oy = h['origin_um']; nx = cmap[round(ox, 4)]; dx = nx - ox
        oldbox[h['inst']] = (ox, oy, ox + h['outline_um'][0], oy + h['outline_um'][1]); dxs[h['inst']] = dx
        if abs(dx) > 1e-9:
            h['origin_um'] = [round(nx, 4), oy]
            h['note'] = (h.get('note', '') + f' | B100-ESCAPE column re-lattice x {ox:g} -> {nx:g} (E escape {st_old["E"][0]:g} -> {st_new["E"][0]:g} um)').lstrip(' |')
            rep['moved_cores'].append(dict(core=h['inst'], before=[ox, oy], after=[nx, oy]))
    def near(p, b, m): return b[0] - m <= p[0] <= b[2] + m and b[1] - m <= p[1] <= b[3] + m
    for tp in t.get('clock', {}).get('taps', []):
        ci = tp['name'].split('.')[0]
        if tp.get('kind') == 'core' and ci in dxs and dxs[ci]:
            tp['xy'] = [round(tp['xy'][0] + dxs[ci], 4), tp['xy'][1]]; rep['taps_moved'] += 1
    newboxes = [(h['origin_um'][0], h['origin_um'][1], *h['outline_um']) for h in hcs]
    ist = rep['internal_stations']
    for e in t.get('internal_stations', []):
        for key, who, m in (('from_um', str(e.get('launch', '')), 1.0), ('to_um', str(e.get('capture', '')), 12.0)):
            ci = who.split('.')[0].replace('core:', '')
            if ci in dxs and dxs[ci] and near(e[key], oldbox[ci], m):
                e[key] = [round(e[key][0] + dxs[ci], 4), e[key][1]]; ist['endpoints_moved'] += 1
        n0 = len(e['regs_um']); regs = []
        for r in e['regs_um']:
            q = free_point(r, newboxes, W, H)
            if abs(q[0] - r[0]) + abs(q[1] - r[1]) > 1e-6: ist['regs_pulled'] += 1
            regs.append([round(q[0], 3), round(q[1], 3)])
        e['regs_um'] = regs
        if not C._hops_ok(e['from_um'], regs, e['to_um'], LIM):
            A, B = tuple(e['from_um']), tuple(e['to_um']); done = False
            for seg in ([A, (B[0], A[1]), B], [A, (A[0], B[1]), B]):
                Lr = C.plen(seg); cand = [list(free_point(C.point_at(seg, Lr * j / (n0 + 1)), newboxes, W, H)) for j in range(1, n0 + 1)]
                if C._hops_ok(A, cand, B, LIM): e['regs_um'] = [[round(v, 3) for v in p] for p in cand]; done = True; break
            if not done:
                try:
                    rr = RelayRouter(newboxes, W, H, 360.0)(A, free_point(B, newboxes, W, H))
                    if len(rr) <= n0:
                        rr = list(rr) + [rr[-1]] * (n0 - len(rr)); done = C._hops_ok(A, rr, B, LIM)
                        if done: e['regs_um'] = [[round(v, 3) for v in p] for p in rr]
                except ValueError: pass
            if done:
                e['note'] = (e.get('note', '') + f' | B100-ESCAPE: {n0} station(s) re-sited after the column re-lattice').lstrip(' |')
                ist['restationed'].append(e.get('conn'))
            else: ist['fails'].append(e.get('conn'))

    # ---- 2a) recentre planned station points of unsited slots onto the opened channels
    boxes = list(S.placed_macro_boxes(t, halo=HALO).values())
    chc = {k: float(np.mean(st_new[k][1]) + CELL[0] / 2) for k in ('C01', 'C12') if st_new[k][1]}
    rep['recentred'] = []
    for nm in [v for v in a.recentre.split(',') if v]:
        s = [s for s in t['ft_slots'] if s['name'] == nm][0]; assert not s.get('bit_sites_um'), nm
        before_r = [list(r) for r in s['regs_um']]
        for j in range(1, len(s['regs_um'])):
            r = s['regs_um'][j]; k = min(chc, key=lambda k: abs(chc[k] - r[0])); s['regs_um'][j] = [round(chc[k], 4), r[1]]
        s['note'] = (s.get('note', '') + f' | B1N6 CHANNEL-OPEN: planned stations recentred to opened channels {before_r[1:]} -> {s["regs_um"][1:]}').lstrip(' |')
        rep['recentred'].append(dict(slot=nm, before=before_r, after=s['regs_um']))
    if a.slot == 'none': rep['restaged_slot'] = None
    else: _restage(a, t, tn, raw, boxes, st_new, rep)
    _finish(a, t, tn, raw, before, hcs, cw, ist, rep)


def _restage(a, t, tn, raw, boxes, st_new, rep):
    # ---- 2) re-stage the wide W->E slot: one stage per channel (C01, C12, E)
    alloc = RowAllocator((INSET, INSET, W - INSET, H - INSET), blocked=boxes, cell_size=CELL, column_pitch=CP, row_pitch=.27, origin=(INSET, INSET))
    s5 = [s for s in t['ft_slots'] if s['name'] == a.slot][0]
    assert s5['in_face'] == 'W' and s5['out_face'] == 'E' and len(s5['bit_sites_um']) == 3
    for s in t['ft_slots']:
        if s is s5 or not s.get('bit_sites_um'): continue
        for stg in s['bit_sites_um']:
            for ll in stg:
                if not NU.hits(ll, boxes): alloc.reserve_rectangle((ll[0] + .01, ll[1] + .01, ll[0] + CELL[0] - .01, ll[1] + CELL[1] - .01))
    model = S.Plan(raw); pins = {(b, i): np.array([x, y]) for b, i, _, x, y, _ in type_pins(model, tn)}
    nb = s5['width'] + 1; chs = a.stages.split(','); chx = [np.mean(st_new[k][1]) + CELL[0] / 2 for k in chs]
    A = np.array([pins[a.slot + '_i', i] for i in range(nb)]); B = np.array([pins[a.slot + '_o', i] for i in range(nb)])
    old5 = np.array(s5['bit_sites_um']) + CELL / 2; new5 = np.zeros_like(old5)
    for i in np.argsort(A[:, 1] + B[:, 1], kind='stable'):
        prev = A[i]
        for k in range(3):
            fy = (chx[k] - A[i][0]) / max(B[i][0] - A[i][0], 1e-9); tgt = (chx[k], A[i][1] + fy * (B[i][1] - A[i][1]))
            q = None; rej = []
            for _ in range(512):
                try: c = alloc.allocate(tgt, 1, max_radius_um=400.0)[0][0]
                except ValueError: break
                if np.abs(c - prev).sum() <= LEG and (k < 2 or np.abs(c - B[i]).sum() <= LEG): q = c; break
                rej.append(c)
            for c in rej:
                ix = round((c[0] - alloc.cw / 2 - alloc.ox) / alloc.cp); iy = round((c[1] - alloc.ch / 2 - alloc.oy) / alloc.rp)
                alloc.used.discard((iy - alloc.iy0) * alloc.nx + ix - alloc.ix0)
            if q is None:
                ys = sorted(float(c[1]) for c in rej[:5]); raise SystemExit(f'{a.slot}[{i}] stage {k}: no legal site near {tgt} prev {prev} pin {B[i]} A {A[i]} tried {len(rej)} first {[list(map(float, c)) for c in rej[:3]]}')
            new5[k, i] = q; prev = q
    s5['bit_sites_um'] = [[[round(float(v), 6) for v in q - CELL / 2] for q in stg] for stg in new5]
    s5['regs_um'] = [A.mean(axis=0).round(4).tolist(), *new5.mean(axis=1).round(4).tolist()]
    chain = [A, *new5, B]; legs = [float(np.abs(q - p).sum(axis=1).max()) for p, q in zip(chain, chain[1:])]
    s5['note'] = (s5.get('note', '') + f' | B100-ESCAPE: per-bit stages re-staged to channels {"/".join(chs)} '
                  f'(x ~{chx[0]:.1f}/{chx[1]:.1f}/{chx[2]:.1f}), max leg {max(legs):.1f} um, stations unchanged').lstrip(' |')
    rep['restaged_slot'] = dict(slot=a.slot, channels=chs, stations=s5['stations'], channel_x=[round(v, 3) for v in chx],
                                stage_x_before=[round(float(old5[k][:, 0].mean()), 3) for k in range(3)],
                                stage_x_after=[round(float(new5[k][:, 0].mean()), 3) for k in range(3)],
                                max_leg_um_per_hop=[round(v, 3) for v in legs],
                                stage_sites_per_channel=[{k: int(sum(1 for q in stg if any(abs(q[0] - CELL[0] / 2 - c) < 1e-3 for c in st_new[k][1])))
                                                          for k in st_new} for stg in new5])



def _finish(a, t, tn, raw, before, hcs, cw, ist, rep):
    # ---- 3) every other halo-colliding per-bit site: nearest legal free site (path_hbm_perbit_nudge)
    rep['perbit_nudge'] = NU.nudge_type(raw, tn)

    # ---- 4) report: cycles + q_b100 census (same model as b1_verify)
    after = S.Plan(json.loads(json.dumps(raw)))
    rep['lane_cycle_delta'] = {lid: after.lane_latency(lid)['cycles'] - before.lane_latency(lid)['cycles'] for lid in after.lanes
                               if after.lane_latency(lid)['cycles'] != before.lane_latency(lid)['cycles']}
    st0 = {s['name']: s['stations'] for s in before.types[tn]['ft_slots']}; st1 = {s['name']: s['stations'] for s in t['ft_slots']}
    is0 = sum(len(e['regs_um']) for e in before.types[tn]['internal_stations']); is1 = sum(len(e['regs_um']) for e in t['internal_stations'])
    rep['stations_unchanged'] = dict(ft_slots=st0 == st1, internal_station_regs=[is0, is1], ok=st0 == st1 and is0 == is1)
    bx = list(S.placed_macro_boxes(t, halo=HALO).values()); seen = set(); worst = (0, None); ff = 0; fails = []
    pins = {(b, i): np.array([x, y]) for b, i, _, x, y, _ in type_pins(after, tn)}
    for s in t['ft_slots']:
        if not s.get('bit_sites_um'): continue
        n = s['width'] + 1; pts = np.array(s['bit_sites_um'])
        chain = [np.array([pins[s['name'] + '_i', i] for i in range(n)]), *[p + CELL / 2 for p in pts], np.array([pins[s['name'] + '_o', i] for i in range(n)])]
        for p, q in zip(chain, chain[1:]):
            hm = float(np.abs(p - q).sum(axis=1).max()); worst = max(worst, (hm, s['name']))
        for stg in pts:
            for x0, y0, x1, y1 in bx:
                k = int(((stg[:, 0] < x1 - 1e-6) & (stg[:, 0] + CELL[0] > x0 + 1e-6) & (stg[:, 1] < y1 - 1e-6) & (stg[:, 1] + CELL[1] > y0 + 1e-6)).sum())
                if k: fails.append((s['name'], 'halo collision', k))
            for x, y in stg:
                kk = (round(x, 3), round(y, 3))
                if kk in seen: fails.append((s['name'], 'FF collision', kk))
                seen.add(kk)
            ff += len(stg)
    if worst[0] > LEG + 1e-6: fails.append(('worst hop', worst))
    rep['census'] = dict(ff_sites=ff, max_bit_hop_um=round(worst[0], 3), worst_slot=worst[1], failures=fails[:10],
                         verdict='PASS' if not fails else 'FAIL')
    # core overlap / halo clear among cores
    ov = [(p['inst'], q['inst']) for i, p in enumerate(hcs) for q in hcs[i + 1:]
          if NU.hits is not None and p['origin_um'][0] < q['origin_um'][0] + cw + G - 1e-6 and q['origin_um'][0] < p['origin_um'][0] + cw + G - 1e-6
          and p['origin_um'][1] < q['origin_um'][1] + q['outline_um'][1] + G - 1e-6 and q['origin_um'][1] < p['origin_um'][1] + p['outline_um'][1] + G - 1e-6]
    rep['core_overlap_or_halo_clash'] = ov
    rep['lattice_ok'] = all(abs(v / G - round(v / G)) < 1e-6 for h in hcs for v in h['origin_um'])
    rep['scope'] = 'geometry proposal; not a route receipt'
    shutil.copytree(a.src, a.out)
    (a.out / 'die_plan.json').write_text(json.dumps(raw, indent=1) + '\n')
    (a.out / ('b100_escape_report.json' if tn == 'q_b100' else f'{tn}_escape_report.json')).write_text(json.dumps(rep, indent=1, default=str) + '\n')
    print('COMPLETE', json.dumps({k: rep[k] for k in ('cols_before', 'cols_after', 'east_escape_um', 'stations_unchanged', 'lane_cycle_delta',
                                                       'census', 'core_overlap_or_halo_clash', 'lattice_ok', 'restaged_slot')}, default=str))
    print('internal', json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in ist.items()}), 'fails', ist['fails'][:5])
    if fails or ist['fails'] or rep['lane_cycle_delta'] or not rep['stations_unchanged']['ok'] or ov: sys.exit(2)


if __name__ == '__main__': main()
