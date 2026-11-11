#!/usr/bin/env python3
"""landing_ca_select.py -- which S81 landings become count-aligned (CA, +1 cycle), and the per-lane cycle deltas.

COORD 11-10 (owner: "adding cycles is not a problem but a lever"): the phase sign on today's rebuilt die clock is not
stable, so every landing whose margin is NEAR or EDGE in EITHER model becomes the CA form (ot_dp_clk_landing_ca, fixed
latency K + 1 for every static phase in its window; METHODOLOGY 12.16) with ONE extra cycle over the bind's count, and
the schedule absorbs it.  LEAD / LAG landings with clear margin in both models keep their measured count.

Models, per landing and corner (TT, FF; a corner disagreement is NEAR, as landing_phase_sign):
  raw      d = t_local - t_fwd unwrapped, [lo, hi] = [d - p_dn, d + p_up]: LEAD hi <= -M, LAG lo >= M, else NEAR
  wrapped  d folded into (-P/2, P/2] (the ring sees the phase mod P); EDGE if [lo, hi] crosses +-P/2; else as raw
Decision:
  CA       raw NEAR, or wrapped NEAR / EDGE, or raw and wrapped clear but of opposite sign (the sign itself is unstable)
  LEAD     LEAD in both            -> measured count 3 (= bind)
  LAG      LAG in both             -> measured count 2 (bind 3 - 1)
Counts relative to the bind (bind_clock_landings added_cycles_per_crossing, 3): CA 3 + 1 = 4 (K = 3), LEAD 3, LAG 2.
Lane delta = sum over the lane's landings of (new - bind); the compiler adds it to the lane's bound depth.

Inputs: a landing_phase_sign result (lps.json: rows[] with corners{TT,FF}{d_ps,lo_ps,hi_ps}) and the bind dir
(bind_latency.json for the lanes' current bound_stages).  Outputs: <out>/landings.tsv, lanes.tsv, ca_select.json.
DO_NOT_COUNT: a plan / compiler input, not sign-off evidence.
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def wrap(x, P):
    return x - P * round(x / P)


def raw_cls(c, M):
    return 'LEAD' if c['hi_ps'] <= -M else 'LAG' if c['lo_ps'] >= M else 'NEAR'


def wrapped_cls(c, P, M):
    d = wrap(c['d_ps'], P)
    hi, lo = d + (c['hi_ps'] - c['d_ps']), d - (c['d_ps'] - c['lo_ps'])
    if hi > P / 2 or lo < -P / 2:
        return 'EDGE'
    return 'LEAD' if hi <= -M else 'LAG' if lo >= M else 'NEAR'


def combine(cs):
    if 'EDGE' in cs.values():
        return 'EDGE'
    v = set(cs.values())
    return v.pop() if len(v) == 1 else 'NEAR'


def decide(raw, wr):
    if raw == 'NEAR' or wr in ('NEAR', 'EDGE'):
        return 'CA'
    if raw != wr:
        return 'CA'          # LEAD in one model, LAG in the other: the sign is not a stable thing to count on
    return raw


def run(lps, bind_latency, P=833.0, M=100.0, bind_cycles=3):
    rows = []
    for r in (lps['rows'] if 'rows' in lps else lps['landings']):
        cs = r['corners']
        raw = combine({k: raw_cls(cs[k], M) for k in cs})
        wr = combine({k: wrapped_cls(cs[k], P, M) for k in cs})
        dec = decide(raw, wr)
        new = {'CA': bind_cycles + 1, 'LEAD': bind_cycles, 'LAG': bind_cycles - 1}[dec]
        clear = min(max(-cs[k]['hi_ps'], cs[k]['lo_ps']) for k in cs)
        rows.append(dict(port=r['port'], lane=r['lane'], src=r['src'], dst=r['dst'], dst_bus=r.get('dst_bus'),
                         kind=r.get('kind'), wneg=r.get('wneg'), raw=raw, wrapped=wr, ds85_cls=r.get('cls'),
                         decision=dec, bind_cycles=r.get('bind_cycles', bind_cycles), new_cycles=new,
                         delta=new - r.get('bind_cycles', bind_cycles), raw_clearance_ps=round(clear, 1),
                         TT_d_ps=cs['TT']['d_ps'], FF_d_ps=cs['FF']['d_ps']))
    lat = {b['lane']: b for b in bind_latency['buses']}
    by = defaultdict(list)
    for x in rows:
        by[x['lane']].append(x)
    lanes = []
    for ln, xs in sorted(by.items()):
        c = Counter(x['decision'] for x in xs)
        b = lat.get(ln, {})
        dl = sum(x['delta'] for x in xs)
        lanes.append(dict(lane=ln, src=b.get('src'), dst=b.get('dst'), landings=len(xs), CA=c['CA'], LEAD=c['LEAD'],
                          LAG=c['LAG'], delta=dl, bound_stages=b.get('bound_stages'),
                          new_bound_stages=(b['bound_stages'] + dl) if 'bound_stages' in b else None,
                          ports=','.join(x['port'] for x in xs)))
    return rows, lanes


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--lps', type=Path, required=True)
    ap.add_argument('--bind', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--period-ps', type=float, default=833.0)
    ap.add_argument('--margin-ps', type=float, default=100.0)
    ap.add_argument('--ctl-lanes', default=None, help='comma list of control lanes to flag (S1 set)')
    a = ap.parse_args()
    lps = json.loads(a.lps.read_text())
    bl = json.loads((a.bind / 'bind_latency.json').read_text())
    rows, lanes = run(lps, bl, a.period_ps, a.margin_ps)
    a.out.mkdir(parents=True, exist_ok=True)
    ctl = set((a.ctl_lanes or '').split(',')) - {''}
    cols = list(rows[0])
    (a.out / 'landings.tsv').write_text('\t'.join(cols) + '\n' + ''.join(
        '\t'.join(str(x[k]) for k in cols) + '\n' for x in rows))
    lc = list(lanes[0]) + ['s1_ctl']
    (a.out / 'lanes.tsv').write_text('\t'.join(lc) + '\n' + ''.join(
        '\t'.join(str(x.get(k, '')) for k in lc[:-1]) + f"\t{int(x['lane'] in ctl)}\n" for x in lanes))
    summ = dict(schema='tok-verify-1.landing_ca_select.v1', status='DO_NOT_COUNT', lps=str(a.lps), bind=str(a.bind),
                period_ps=a.period_ps, margin_ps=a.margin_ps, landings=len(rows),
                decision=dict(Counter(x['decision'] for x in rows)),
                raw=dict(Counter(x['raw'] for x in rows)), wrapped=dict(Counter(x['wrapped'] for x in rows)),
                ca_reason=dict(Counter(('raw NEAR' if x['raw'] == 'NEAR' else f"wrapped {x['wrapped']}"
                                        if x['wrapped'] in ('NEAR', 'EDGE') else 'sign flips between models')
                                       for x in rows if x['decision'] == 'CA')),
                lanes=len(lanes), lanes_changed=sum(1 for x in lanes if x['delta']),
                lane_delta_hist=dict(sorted(Counter(x['delta'] for x in lanes).items())),
                total_added_cycles=sum(x['delta'] for x in rows if x['delta'] > 0),
                total_removed_cycles=-sum(x['delta'] for x in rows if x['delta'] < 0),
                s1_ctl={x['lane']: dict(delta=x['delta'], CA=x['CA'], LAG=x['LAG'], LEAD=x['LEAD'],
                                        bound=x['bound_stages'], new=x['new_bound_stages']) for x in lanes if x['lane'] in ctl})
    (a.out / 'ca_select.json').write_text(json.dumps(dict(summ, lanes_detail=lanes, landings_detail=rows), indent=1) + '\n')
    print(json.dumps(summ, indent=1))


if __name__ == '__main__':
    main()
