#!/usr/bin/env python3
"""TOK-FUNC-S81/MURATE (10-21): per-user / per-message verdicts of a tb_xdie_s81_2 run (reads the bench's LAND lines:
LAND inst src dst k issue land deadline).  No new check: it splits the bench's own verdict (bit-exact payload compare,
in-order landing, compiled deadlines, MU tags, faults, live lanes) by user and by stage-hop message and reports cycles.

  mu_stats.py <golden dir> <run.log[.gz]> --cal cal.json --out stats.json
  mu_stats.py --calibrate <cal_su run.log> <cal_mu1 run.log> --out cal.json
Classes by sender port (dp % 4): 0 / 1 = S (TP, s_0S / s_7S), 3 = N (TP, s_7N), 2 = H (stage-hop circuit, s_0N).
Calendar budget (dv_mu_calendar_phys REL241): stage-hop first-beat crossing x_flat 376 + RX_JIT 2; a message must have
fully landed by its receiver start = send + HOP 821 (the forward-x arrival the calendar schedules the next stage on).
"""
from __future__ import annotations

import argparse
import bisect
import gzip
import json
import re
from pathlib import Path

CLS = {0: 'S', 1: 'S', 2: 'H', 3: 'N'}
X_FLAT, RX_JIT, HOP = 376, 2, 821
H_ISSUE = 4 * 80 + 3 * 16          # one h message = 4 tag windows of NB 80 beats, 16 cycles apart


def lands(p):
    op = gzip.open if str(p).endswith('.gz') else open
    with op(p, 'rt', errors='replace') as f:
        for ln in f:
            if ln.startswith('LAND '):
                yield tuple(int(x) for x in ln.split()[1:])


def verdict_lines(p):
    op = gzip.open if str(p).endswith('.gz') else open
    out = {}
    with op(p, 'rt', errors='replace') as f:
        for ln in f:
            for k in ('XDIE2_CFG', 'XDIE_LINK', 'XDIE_MU', 'XDIE_STATS', 'PASS xdie_s81', 'FAIL'):
                if ln.startswith(k) and k not in out:
                    out[k] = ln.strip()
    return out


def calibrate(logs, out):
    mn = {}
    n = 0
    for p in logs:
        for inst, src, dst, k, iss, land, dl in lands(p):
            c = CLS[src % 4]
            mn[c] = min(mn.get(c, 10**9), land - iss)
            n += 1
    assert set(mn) == {'S', 'N', 'H'}, mn
    rec = dict(schema='opentallas.tokfunc_s81.mu_cal.v1', beats=n, logs=[str(p) for p in logs], crossing=mn,
               LAT={c: v + 1 for c, v in mn.items()}, rule='LAT = measured fixed crossing + 1 (the r_dc_x recalibration '
               'rule of tools/xdie_s81_2/gate_xl5.sh)', calendar=dict(x_flat_stage_hop=X_FLAT, rx_jit=RX_JIT,
               budget_H=X_FLAT + RX_JIT, H_within_budget=mn['H'] <= X_FLAT + RX_JIT))
    Path(out).write_text(json.dumps(rec, indent=1) + '\n')
    print(f"CAL crossing {mn} LAT {rec['LAT']} H budget {X_FLAT + RX_JIT}: {'OK' if rec['calendar']['H_within_budget'] else 'OVER'}")


def stats(gdir, log, out):
    g = json.loads((Path(gdir) / 'golden.json').read_text())
    insts = g['instances']
    ustart = {}
    for r in insts:
        u = r.get('user')
        if u is not None:
            ustart[u] = min(ustart.get(u, 10**12), r['start'])
    order = sorted(ustart.items(), key=lambda x: x[1])
    starts = [s for _, s in order]
    msgs = sorted((r['start'], r.get('user'), r.get('label'), r.get('msg')) for r in insts if r.get('kind') == 'MUH')
    mstarts = [m[0] for m in msgs]
    per = {}
    pm = {}
    n = 0
    for inst, src, dst, k, iss, land, dl in lands(log):
        n += 1
        u = order[bisect.bisect_right(starts, iss) - 1][0] if order else 'su'
        d = per.setdefault(u, dict(beats=0, late=0, max_late=None, cross_min=10**9, cross_max=0, first_issue=iss, last_land=0))
        d['beats'] += 1
        if dl:
            d['late'] += land > dl
            d['max_late'] = land - dl if d['max_late'] is None else max(d['max_late'], land - dl)
        d['cross_min'] = min(d['cross_min'], land - iss)
        d['cross_max'] = max(d['cross_max'], land - iss)
        d['first_issue'] = min(d['first_issue'], iss)
        d['last_land'] = max(d['last_land'], land)
        if src % 4 == 2 and msgs:
            j = bisect.bisect_right(mstarts, iss) - 1
            if j >= 0 and iss < mstarts[j] + H_ISSUE:
                m = pm.setdefault(j, dict(start=msgs[j][0], user=msgs[j][1], label=msgs[j][2], beats=0, last_land=0))
                m['beats'] += 1
                m['last_land'] = max(m['last_land'], land)
    for d in per.values():
        d['span_cycles'] = d['last_land'] - d['first_issue']
    mv = []
    for j, m in sorted(pm.items()):
        m['latency'] = m['last_land'] - m['start']
        m['within_HOP'] = m['latency'] <= HOP
        mv.append(m)
    v = verdict_lines(log)
    bench_pass = 'PASS xdie_s81' in v
    rec = dict(schema='opentallas.tokfunc_s81.mu_stats.v1', golden=str(gdir), log=str(log), bench=v, bench_pass=bench_pass,
               beats=n, users=len(per), per_user={str(u): d for u, d in per.items()},
               users_all_landed_ontime=all(d['late'] == 0 for d in per.values()))
    if mv:
        rec['messages'] = dict(count=len(mv), beats_each=sorted({m['beats'] for m in mv}),
                               latency_max=max(m['latency'] for m in mv), latency_min=min(m['latency'] for m in mv),
                               all_within_HOP=all(m['within_HOP'] for m in mv), HOP=HOP,
                               worst=max(mv, key=lambda m: m['latency']))
    Path(out).write_text(json.dumps(rec, indent=1) + '\n')
    lm = rec.get('messages', {})
    print(f"STATS {'BENCH_PASS' if bench_pass else 'BENCH_FAIL'} beats {n} users {len(per)} late "
          f"{sum(d['late'] for d in per.values())} max_late {max((d['max_late'] or -10**9) for d in per.values())}"
          + (f" msgs {lm['count']} lat {lm['latency_min']}..{lm['latency_max']} <=HOP {lm['all_within_HOP']}" if lm else ''))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('args', nargs='+')
    ap.add_argument('--calibrate', action='store_true')
    ap.add_argument('--cal')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    if a.calibrate:
        calibrate(a.args, a.out)
    else:
        stats(a.args[0], a.args[1], a.out)


if __name__ == '__main__':
    main()
