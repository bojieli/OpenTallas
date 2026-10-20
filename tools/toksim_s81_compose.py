#!/usr/bin/env python3
"""TOKSIM-S81 (owner 2026-10-19 18:18): DeepSeek-V4.1 decode rate on the S81 p4l-MU release die from MEASURED RTL cycles.

The S81 schedule is static, so a token's cycles are deterministic.  This tool composes the token as

    T = sum over critical DAG nodes of cycles(node)  +  the inter-die exchange terms  +  the p4l / scan / residual terms

and replaces cycles(node) by the measured start->retire cycles of its op type wherever an element record measured that op
on the release RTL (or on the newest bench-passing RTL of an element not yet in the release source, labelled).  Nothing is
re-priced: a node without a new measurement keeps its committed number and its committed grade.

Inputs (all committed):
  base   results/arch/token_path_1018/ds_rom.json   token_compose_xdie output (xdie terms from xdie_s81_1019 co-sim,
                                                    p4l DV deltas, scan option D, L20 split, price residual)
  dag    results/arch/token_path_20261009/ds_rom.json / ds_rom_mtp.json   the static DAG (nodes, edges, critical path)
  elems  results/token_pass/measured_s81_1019/elements/*.json   per-op measurements (schema: see README.md)

Two compositions are reported:
  fixed   the committed critical path, node cycles replaced (the owner's formula: measured cycles per type x count)
  solved  the DAG re-solved (longest path) with the replaced node cycles: catches a measured change that moves the path

  python3 tools/toksim_s81_compose.py            # write results/token_pass/measured_s81_1019/cycles.json
  python3 tools/toksim_s81_compose.py --check    # recompute and compare with the committed cycles.json
  python3 tools/toksim_s81_compose.py --selftest # with no element records the fixed composition reproduces the base
"""
import argparse
import collections
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/token_pass/measured_s81_1019'
BASE = ROOT / 'results/arch/token_path_1018/ds_rom.json'
DAGS = {'ar': ROOT / 'results/arch/token_path_20261009/ds_rom.json',
        'mtp': ROOT / 'results/arch/token_path_20261009/ds_rom_mtp.json'}
F_CLK = 1.2e9
MEASURED = ('measured-release-RTL', 'measured-newest-element-RTL', 'measured-current-RTL')
SCHEMA = 'opentallas.toksim_s81.v1'
GROUP_KINDS = ('head', 'embed', 'hops', 'draft', 'wave', 'accept')


def admitted(o, exact_ops):
    """Strict admission (TOKSIM-S81B 10-19): a measured op folds only when its record says bit_exact true.  Two
    exceptions, both carrying no cycles of their own: a 0-cycle op merged into a covering op, and a curation mapping
    (zz_curation.json) of an op that another element record measured bit-exact."""
    if o.get('grade') not in MEASURED:
        return False
    if o.get('bit_exact') is True:
        return True
    if o.get('bit_exact') is None and o.get('cycles') == 0 and not o.get('by_old') and not o.get('per_layer'):
        return True
    return o.get('bit_exact') is None and o.get('_curation') and o['op'] in exact_ops


def load_elements(d):
    """op key (dag_cls, op) -> override; slot -> override (for base layer/adjust terms); xdie part -> ratio."""
    ops, slots, xparts, files, excluded = {}, {}, {}, [], []
    recs = []
    for f in sorted(glob.glob(str(d / '*.json'))):
        e = json.load(open(f))
        rel = str(Path(f).relative_to(ROOT))
        files.append(dict(file=rel, cls=e.get('cls'), written=e.get('written'), branch=e.get('agent_branch')))
        cur = Path(f).name.startswith('zz_curation')
        recs += [dict(o, file=rel, _curation=cur) for o in e.get('ops', [])]
    exact_ops = {o['op'] for o in recs if not o['_curation'] and o.get('bit_exact') is True}
    for o in recs:
        if not admitted(o, exact_ops):
            if o.get('grade') in MEASURED:
                excluded.append(dict(op=o['op'], file=o['file'], grade=o['grade'], bit_exact=o.get('bit_exact'),
                                     cycles=o.get('cycles')))
            continue
        if o.get('xdie_part'):
            # an on-die leg / crossing part of the base xdie terms, measured: scale every term of that part
            xparts[o['xdie_part']] = dict(ratio=float(o['cycles']) / float(o['old_cycles_per_instance']),
                                          grade=o['grade'], file=o['file'])
        elif o.get('slot'):
            slots[o['slot']] = o
        elif o.get('cycles') is not None or o.get('by_old') or o.get('per_layer'):
            ops[(o.get('dag_cls'), o['op'])] = o
    return ops, slots, xparts, files, excluded


def node_cycles(n, ov):
    """New cycles for a DAG node under an override; None when the override does not cover this node's shape."""
    old = float(n['cycles'])
    L = n.get('layer')
    lk = f'L{L}' if isinstance(L, int) else None
    if lk and ov.get('per_layer') and lk in ov['per_layer']:
        return float(ov['per_layer'][lk]), 'exact'
    for k, v in (ov.get('by_old') or {}).items():
        if abs(float(k) - old) <= 0.6:
            return float(v), 'exact'
    if ov.get('cycles') is None:
        return None, None
    ref = ov.get('old_cycles_per_instance')
    refs = ref if isinstance(ref, list) else [ref]
    if ref is None or any(r is not None and abs(float(r) - old) <= 0.6 for r in refs):
        return float(ov['cycles']), 'exact'
    return None, None   # a different shape than the one measured: keep the committed number (never re-price)


def lkey(n, gk):
    k = gk.get(n.get('group'))
    if k in GROUP_KINDS:
        return k
    L = n.get('layer')
    return f'L{L}' if isinstance(L, int) and L >= 0 else (k or 'other')


def solve(dag, cyc):
    N = {n['id']: n for n in dag['nodes']}
    pred, succ, indeg = collections.defaultdict(list), collections.defaultdict(list), collections.Counter()
    for e in dag['edges']:
        pred[e['dst']].append((e['src'], float(e.get('cycles') or 0)))
        succ[e['src']].append(e['dst'])
        indeg[e['dst']] += 1
    order, q = [], [i for i in N if indeg[i] == 0]
    while q:
        i = q.pop()
        order.append(i)
        for j in succ[i]:
            indeg[j] -= 1
            if indeg[j] == 0:
                q.append(j)
    end, arg = {}, {}
    for i in order:
        s, a = 0.0, None
        for p, c in pred[i]:
            if end[p] + c > s:
                s, a = end[p] + c, p
        end[i], arg[i] = s + cyc[i], a
    last = max(end, key=end.get)
    path, i = [], last
    while i is not None:
        path.append(i)
        i = arg[i]
    return end[last], path[::-1]


def xdie_part(p, xparts):
    """(cycles, grade) of one base xdie term, with a measured part override applied."""
    x = xparts.get(p.get('part'))
    if x and p['grade'] == 'priced':
        return p['total'] * x['ratio'], x['grade']
    return p['total'], p['grade']


def compose(wl, base, dag, ops, slots, xparts=None):
    xparts = xparts or {}
    gk = {g['id']: g['kind'] for g in dag['groups']}
    bterms = base['workloads'][wl]['terms']
    xd = {}
    for t in bterms:
        if t['kind'] == 'xdie':
            xd.setdefault(t['slot'], []).append(t)
    rows, cyc_new, cyc_old = [], {}, {}
    by_grade = collections.Counter()
    per_op = {}
    for n in dag['nodes']:
        L = lkey(n, gk)
        old = float(n['cycles'])
        cyc_old[n['id']] = old
        if n.get('cls') in ('coll', 'hop'):
            parts = xd.get(f'{L}.xdie.{n["id"]}', [])
            if parts:
                vals = [xdie_part(p, xparts) for p in parts]
                cyc_new[n['id']] = sum(c for c, _ in vals)
                if n.get('critical'):
                    for c, g in vals:
                        by_grade[g] += c
            else:
                cyc_new[n['id']] = old
                if n.get('critical'):
                    by_grade['priced'] += old
            continue
        g = {'measured': 'measured-old-RTL', 'measured+vendor': 'measured-old-RTL'}.get(
            (n.get('src') or {}).get('grade'), 'priced')
        new, how, tail = old, None, 0.0
        ov = ops.get((n.get('cls'), n.get('op'))) or ops.get((None, n.get('op')))
        if ov:
            c, how = node_cycles(n, ov)
            if c is not None:
                new = c
                g = ov['grade'] if how == 'exact' else 'measured-scaled'
                tail = float(ov.get('tail_priced') or 0.0)
        cyc_new[n['id']] = new + tail
        if n.get('critical'):
            by_grade[g] += new
            by_grade['priced'] += tail
            k = (n.get('cls'), n.get('op'))
            r = per_op.setdefault(k, dict(cls=k[0], op=k[1], n_crit=0, old_cycles=0.0, cycles=0.0, grades=collections.Counter()))
            r['n_crit'] += 1
            r['old_cycles'] += old
            r['cycles'] += new + tail
            r['grades'][g] += new
            if tail:
                r['grades']['priced'] += tail
    # base layer / adjust terms that are not DAG nodes (p4l DV deltas, scan option D, L20 split, residual)
    extra = []
    for t in bterms:
        if t['kind'] == 'xdie' or t['slot'].endswith('.die'):
            continue
        o = slots.get(t['slot'])
        c, g = (float(o['cycles']), o['grade']) if o else (t['total'], t['grade'])
        extra.append(dict(slot=t['slot'], kind=t['kind'], cycles=round(c, 1), grade=g, base_cycles=t['total'],
                          base_grade=t['grade'], evidence=(o or {}).get('evidence')))
        by_grade[g] += c
    # element records may add terms the DAG / base does not carry (e.g. an unmeasured tail of a measured op), by slot
    seen = {t['slot'] for t in bterms}
    for sl, o in sorted(slots.items()):
        if sl in seen or o.get('workloads', [wl]) and wl not in o.get('workloads', [wl]):
            continue
        c = float(o['cycles']) * float(o.get('n', 1))
        g = o.get('term_grade', o['grade'])
        extra.append(dict(slot=sl, kind='element', cycles=round(c, 1), grade=g, base_cycles=0.0, base_grade=None,
                          evidence=o.get('evidence')))
        by_grade[g] += c
    crit = [n['id'] for n in dag['nodes'] if n.get('critical')]
    fixed = sum(cyc_new[i] for i in crit) + sum(e['cycles'] for e in extra)
    T_solve, path = solve(dag, cyc_new)
    T_solve += sum(e['cycles'] for e in extra)
    tau = base['workloads'][wl].get('tau') or 1.0
    tot = sum(by_grade.values())
    meas = sum(v for k, v in by_grade.items() if k in MEASURED)
    phy = by_grade.get('modelled-PHY', 0.0)
    out = dict(
        workload=wl, tau=base['workloads'][wl].get('tau'),
        T_cycles_fixed=round(fixed, 1), T_cycles_solved=round(T_solve, 1),
        per_accepted_cycles=round(fixed / tau, 1),
        tok_s=round(F_CLK * tau / fixed, 1), tok_s_solved=round(F_CLK * tau / T_solve, 1),
        base_T_cycles=base['workloads'][wl]['T_token_cycles'], base_tok_s=base['workloads'][wl]['tok_s'],
        price_of_record=base['workloads'][wl]['price_of_record'],
        solved_path_changed=set(path) != set(crit),
        by_grade={k: round(v, 1) for k, v in sorted(by_grade.items())},
        pct_measured=round(100 * meas / tot, 2) if tot else 0.0,
        pct_measured_on_chip=round(100 * meas / (tot - phy), 2) if tot - phy else 0.0,
        pct_modelled_phy=round(100 * phy / tot, 2) if tot else 0.0,
        per_op=sorted(({**r, 'old_cycles': round(r['old_cycles'], 1), 'cycles': round(r['cycles'], 1),
                        'grades': {k: round(v, 1) for k, v in r['grades'].items()}} for r in per_op.values()),
                      key=lambda r: -r['cycles']),
        extra_terms=extra)
    return out


def multi_user(base, res):
    mu = {}
    for wl, r in res.items():
        b = base.get('multi_user', {}).get(wl)
        if not b:
            continue
        users = b['users']
        period = b['period_cycles']
        T_user = r['per_accepted_cycles'] if wl == 'mtp' else r['T_cycles_fixed']
        # each user emits a token (AR) / a verify step (MTP) every max(own token cycles, calendar period)
        step = r['T_cycles_fixed'] if wl == 'mtp' else T_user
        eff = max(step, period)
        tau = r['tau'] or 1.0
        mu[wl] = dict(users=users, calendar_period_cycles=period, calendar_record=b['record'],
                      calendar_grade='slot issue measured on release seq_host/fixed_issue RTL (HEADMU run_mu_mtp.sh: every user at shift+360, 0 collisions, 0 interference); slot length itself from the stage model; cross-die MU co-sim u_ar46r/u_mtp10r not run',
                      per_user_tok_s=round(F_CLK * tau / eff, 1), aggregate_tok_s=round(users * F_CLK * tau / eff, 0),
                      bound='calendar period' if period >= step else 'per-user token',
                      base_aggregate_tok_s=b['aggregate_tok_s'], pct_measured_per_user=r['pct_measured'])
    return mu


def build(elem_dir):
    base = json.load(open(BASE))
    ops, slots, xparts, files, excluded = load_elements(elem_dir)
    res = {wl: compose(wl, base, json.load(open(p)), ops, slots, xparts) for wl, p in DAGS.items()}
    return dict(schema=SCHEMA, design='ds_rom', die='S81 p4l-MU (release source GEN mu4c 19bf4121e)', clock_hz=F_CLK,
                inputs=dict(base=str(BASE.relative_to(ROOT)), dags={k: str(v.relative_to(ROOT)) for k, v in DAGS.items()},
                            elements=files),
                admission='measured grade AND bit_exact true (0-cycle merged ops and curation maps of bit-exact ops admitted)',
                excluded_not_bit_exact=excluded,
                xdie_parts_measured={k: dict(v, ratio=round(v['ratio'], 6)) for k, v in xparts.items()},
                workloads=res, multi_user=multi_user(base, res))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        r = build(OUT / '__none__')
        ok = True
        for wl, w in r['workloads'].items():
            d = abs(w['T_cycles_fixed'] - w['base_T_cycles'])
            print(f'{wl}: fixed {w["T_cycles_fixed"]} vs base {w["base_T_cycles"]} (diff {d:.1f}); solved {w["T_cycles_solved"]}')
            ok &= d < 1.0
        print('SELFTEST', 'PASS' if ok else 'FAIL')
        sys.exit(0 if ok else 1)
    r = build(OUT / 'elements')
    s = json.dumps(r, indent=1, sort_keys=True) + '\n'
    p = OUT / 'cycles.json'
    if a.check:
        same = p.exists() and p.read_text() == s
        print('CHECK', 'PASS' if same else 'FAIL (rerun without --check)')
        sys.exit(0 if same else 1)
    OUT.mkdir(parents=True, exist_ok=True)
    p.write_text(s)
    for wl, w in r['workloads'].items():
        print(f'{wl}: T {w["T_cycles_fixed"]:,} cyc (solved {w["T_cycles_solved"]:,}) -> {w["tok_s"]:,} tok/s; measured '
              f'{w["pct_measured"]}% (on-chip {w["pct_measured_on_chip"]}%, PHY {w["pct_modelled_phy"]}%)')
    for wl, m in r['multi_user'].items():
        print(f'MU {wl}: {m["users"]} users -> {m["aggregate_tok_s"]:,.0f} agg ({m["per_user_tok_s"]} per user, {m["bound"]})')


if __name__ == '__main__':
    main()
