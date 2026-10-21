#!/usr/bin/env python3
"""S81-MUCAL140B (10-20): re-deal the routed experts over the SAME 140 TP4 stages (same dies, same dense-stage order,
same copy-B layers) so the multi-user bound -- the dense stage hold window -- is as small as the exact ROM capacity
admits.  ROM contents / compiler only: no stage, die or RTL change.

Why: on the physical calendar (dv_mu_calendar_phys.py) a dense stage holds, for one user, the previous layer's tail
experts (+ the partial add + the combine), the attention + pre-expert of its own layer, and its own layer's head
experts.  Every side costs a full static reservation E x min(6, N) / 6 once N >= 6, so a two-sided dense stage pays
2 E + C on top of A + D.  The base map (xs_stage_map balanced on ROM load) puts two sides on R003 (L1, single copy):
the MU bound.

Capacity (exact, pinned PAIR_ROTATE=0, QPAIRS 12, 122 frames): the worst q pair fill is EXACTLY linear in the stage's
experts -- q = dense intercept (dense_L*_n0 probe: L0-class 480, L1 1024, L2/L8/L20/L24-class 576, L14 1120) + 72 N
(all 44 + 42 exact f122_140 / f122_148 specs fit it with 0 error) -- so N_max = floor((8191 - q0) / 72):
107 / 99 / 105 / 98, expert-only 113.  Calendar rows: rows(dense L) + rows(L - 1) if the stage holds L - 1's tail,
<= 4096.  The exact allocator run (xs_capacity) is still the verdict: this tool only proposes the map + specs.

Search: binary search on the bound B; per bound a DP over layers (state = tail experts of layer L carried onto dense
L + 1) finds the fewest expert-only stages; feasible iff <= the 100 the chain has.  Window model (cycles, from the
calendar's per-layer segments): dense L = A + D + [t > 0] (E min(6, t) / 6 + ADD + C) + E min(6, h) / 6; effective
= window / copies.  Unused expert-only stages are filled by splitting the fullest ones (lower fill, same count).

  mucal_stage_rebalance.py --base MAP --segments CAL_AR.json --out NEWMAP --specs SPECS
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

NL, NE = 40, 384
DEPTH = 8192
SLOPE = 72
CAL_ROWS = 4096
EXP_CAP = (DEPTH - 1) // SLOPE                    # 113
Q0 = {'L0': 480, 'L1': 1024, 'L2': 576, 'L14': 1120, 'L20': 576, 'L24': 576}
DUP = (2, 8, 14, 20, 24, 28, 32, 36)
ADD = 82.0


def cls_of(L, idx_src):
    return 'L14' if L == 14 else 'L1' if L == 1 else 'L20' if L == 20 else 'L2' if L in (2, 8) else \
        'L24' if L in idx_src else 'L0'


def side(E, n):
    return E * min(6, n) / 6.0


def window(seg, L, t, h, E, C):
    return seg[L]['A'] + seg[L]['D'] + ((side(E, t) + ADD + C) if t else 0.0) + side(E, h)


def plan(seg, cap, rows, copies, B):
    """fewest expert-only stages with every dense effective window <= B; returns (stages, choice list) or None"""
    E, C = seg[0]['E'], seg[0]['C']
    INF = 10 ** 9
    f = {0: (0, [])}                            # t carried into dense L -> (stages used, [(h, t, n)...])
    for L in range(NL):
        g = {}
        nxt_cap = cap[L + 1] if L + 1 < NL else 0
        for tp, (used, ch) in f.items():
            if tp and rows[L] + rows[L - 1] > CAL_ROWS:
                continue
            for h in range(0, cap[L] - tp + 1):
                if window(seg, L, tp, h, E, C) / copies[L] > B:
                    continue
                for t in range(0, min(NE - h, nxt_cap) + 1):
                    rem = NE - h - t
                    n = -(-rem // EXP_CAP)
                    u = used + n
                    if u < g.get(t, (INF,))[0]:
                        g[t] = (u, ch + [(h, t, n)])
        f = g
        if not f:
            return None
    return f.get(0)


def build(base, seg, B, choice, total_exp_stages):
    idx_src = base.get('_idx_src', ())
    dense_by_L = {s['dense_layer']: s for s in base['stages'] if s['dense_layer'] is not None}
    # expert-only stage counts: fill up to the chain's count by splitting the fullest layer runs
    ns = [n for _, _, n in choice]
    while sum(ns) < total_exp_stages:
        L = max(range(NL), key=lambda k: ((NE - choice[k][0] - choice[k][1]) / ns[k] if ns[k] else -1))
        ns[L] += 1
    assert sum(ns) == total_exp_stages, (sum(ns), total_exp_stages)
    stages = []
    tprev = 0
    for L in range(NL):
        h, t, _ = choice[L]
        d = dense_by_L[L]
        runs = ([[L - 1, NE - tprev, NE - 1]] if tprev else []) + ([[L, 0, h - 1]] if h else [])
        stages.append(dict(dense_layer=L, experts=runs, rowsL=[L - 1, L] if tprev else [L], dense=d['dense'],
                           copy_b=d['copy_b']))
        rem = NE - h - t
        n = ns[L]
        e = h
        for k in range(n):
            m = rem // n + (1 if k < rem % n else 0)
            stages.append(dict(dense_layer=None, experts=[[L, e, e + m - 1]] if m else [], rowsL=[L], dense=None,
                               copy_b=False))
            e += m
        tprev = t
    out = []
    for k, s in enumerate(stages):
        n = sum(b - a + 1 for _, a, b in s['experts'])
        dl = s['dense_layer']
        lay = sorted({l for l, _, _ in s['experts']} | ({dl} if dl is not None else set()))
        q = (Q0[cls_of(dl, idx_src)] if dl is not None else 0) + SLOPE * n
        out.append(dict(stage=f'R{k:03d}', dies=[f'R{k:03d}.r{r}' for r in range(4)], layers=lay, dense_layer=dl,
                        dense=s['dense'], experts=s['experts'], n_experts=n, model_load=float(q),
                        model_fill_pct=round(100 * q / DEPTH, 2), calendar_rows=None, copy_b=s['copy_b'],
                        spec=f'{"exp" if dl is None else "L%d" % dl}_n{n}'))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--base', required=True)
    ap.add_argument('--segments', required=True, help='calendar_*_ar.json with layer_segments')
    ap.add_argument('--out', required=True)
    ap.add_argument('--specs', required=True)
    ap.add_argument('--qmax', type=int, default=EXP_CAP * SLOPE,
                    help='worst q pair fill limit a dense stage (default 8136 = the expert-only stages of the base map)')
    ap.add_argument('--copyb-div', type=float, default=2.0, help='copy-B window divisor in the bound (< 2 = colouring margin)')
    a = ap.parse_args(argv)
    bb = Path(a.base).read_bytes()
    base = json.loads(bb)
    seg = {int(k[1:]): v for k, v in json.loads(Path(a.segments).read_text())['layer_segments'].items()}
    # per-layer calendar rows, recovered exactly from the base map's one-layer stages (rows depend on the layer only)
    rows = {}
    for s in base['stages']:
        if len(s['layers']) == 1:
            rows[s['layers'][0]] = s['calendar_rows']
    for s in base['stages']:
        if len(s['layers']) == 2:
            a0, a1 = s['layers']
            assert rows[a0] + rows[a1] == s['calendar_rows'], s['stage']
    assert sorted(rows) == list(range(NL))
    # the L24 class (index source layers) from the base map's dense intercept: q0 = fill - 72 N
    idx_src = tuple(s['dense_layer'] for s in base['stages'] if s['dense_layer'] is not None and
                    s['capacity']['q_max_fill'] - SLOPE * s['n_experts'] == 576 and s['dense_layer'] not in (2, 8, 20))
    base['_idx_src'] = idx_src
    for s in base['stages']:                                  # the linear capacity law reproduces every base stage
        q0 = Q0[cls_of(s['dense_layer'], idx_src)] if s['dense_layer'] is not None else 0
        assert s['capacity']['q_max_fill'] == q0 + SLOPE * s['n_experts'], (s['stage'], s['capacity']['q_max_fill'])
    cap = [(a.qmax - Q0[cls_of(L, idx_src)]) // SLOPE for L in range(NL)]
    copies = [a.copyb_div if L in DUP else 1 for L in range(NL)]
    nexp = sum(1 for s in base['stages'] if s['dense_layer'] is None)
    E, C = seg[0]['E'], seg[0]['C']
    cand = sorted({window(seg, L, t, h, E, C) / copies[L] for L in range(NL) for t in range(0, 8) for h in range(0, 8)}
                  | {window(seg, L, t, h, E, C) / copies[L] for L in range(NL) for t in (0, 6) for h in (0, 6)})
    lo, hi = 0, len(cand) - 1
    best = None
    while lo <= hi:
        mid = (lo + hi) // 2
        r = plan(seg, cap, rows, copies, cand[mid])
        if r and r[0] <= nexp:
            best = (cand[mid], r)
            hi = mid - 1
        else:
            lo = mid + 1
    B, (used, choice) = best
    st = build(base, seg, B, choice, nexp)
    for s in st:
        s['calendar_rows'] = sum(rows[l] for l in s['layers'])
    assert sum(s['n_experts'] for s in st) == NL * NE and len(st) == len(base['stages'])
    assert [s['dense_layer'] for s in st if s['dense_layer'] is not None] == list(range(NL))
    assert all(s['model_load'] <= DEPTH - 1 and s['calendar_rows'] <= CAL_ROWS for s in st)
    m = copy.deepcopy({k: v for k, v in base.items() if k not in ('stages', 'verdict', '_idx_src')})
    m['plan'] = (f'S81-MUCAL140B rebalance of {Path(a.base).name} (sha {hashlib.sha256(bb).hexdigest()[:12]}): same '
                 f'{len(st)} stages / dense order / copy-B; experts re-dealt for MU dense window bound '
                 f'{B:.0f} cyc/copy (model), linear capacity law q0 + 72 N')
    m['rebalance'] = dict(base_sha256=hashlib.sha256(bb).hexdigest(), bound_model=round(B, 1), expert_stages_min=used,
                          per_layer=[dict(layer=L, head=choice[L][0], tail_on_next_dense=choice[L][1],
                                          dense_window=round(window(seg, L, choice[L - 1][1] if L else 0, choice[L][0],
                                                                    E, C), 1), copies=2 if L in DUP else 1) for L in range(NL)],
                          copyb_div=a.copyb_div, qmax=a.qmax, caps=dict(dense=cap, expert_only=EXP_CAP, q0=Q0, slope=SLOPE, idx_src=list(idx_src)))
    m['stages'] = st
    m['stages_count'] = len(st)
    Path(a.out).write_text(json.dumps(m, indent=1) + '\n')
    seen = {}
    for s in st:
        x = seen.setdefault(s['spec'], dict(id=s['spec'], dense_layer=s['dense_layer'], experts=s['n_experts'],
                                            calendar_rows=s['calendar_rows']))
        x['calendar_rows'] = max(x['calendar_rows'], s['calendar_rows'])
    Path(a.specs).write_text(json.dumps(list(seen.values()), indent=1) + '\n')
    two = sum(1 for p in m['rebalance']['per_layer'] if p['layer'] and choice[p['layer'] - 1][1] and p['head'])
    print(f'REBALANCE bound {B:.0f} cyc/copy; expert-only stages needed {used}/{nexp}; two-sided dense {two}; '
          f'{len(seen)} distinct specs; max fill {max(s["model_fill_pct"] for s in st)} %')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
