#!/usr/bin/env python3
"""TOK-VERIFY-1 (2026-11-03): per-die RE-FORM batch re-baseline of the static schedule and the tok/s model.

OWNER 11-03: each die re-forms its two-strike items as ONE batch with ONE crossing latency table (the plan's
latency.lanes, written by tools/die_plan/gen.py latency = the compiler LAT ABI, METHODOLOGY 1.3).  This tool diffs the
base and batch tables and prices the delta on the die's tok/s model of record.  It never gates anything (OWNER 06:28:
checks run in parallel and report; a finding is a class fix in the next batch).  Tok/s loss is accepted (12.21).

Models (one per die, unchanged, only re-run):
  s81   tools/s81_dv/tokfunc/compose_tok_ds.py --plan (TOK-13/14 method: plan lanes -> composer lane terms -> AR/MTP).
  hbm   TOK-13d DS-native S2 model (tools/token_pass/hbm_price_d44t.py = TOK-HBM-3 029d548feed price_d44t.py verbatim, base 576702.4178 asserted).
        Bound only: the largest lane increase is charged on every per-token unit term (IDX SM COLL FUSED SFU); the
        per-term (expected) split needs the lane->term map, done by hand as in price_d44t.py.
  qc,kv Qwen ROM record composition 272,641 cycles = 4,403.2 tok/s (compose_tokfunc.py --base-only); head,
        s81_head DS AR 1,258.9 tok/s (TOK-14).  No plan-lane-driven model exists for these, so the price is a
        BOUND: every changed lane class is charged its largest increase, `per_token` times (36 Qwen3-8B layers for
        qc/kv, once a token for the head), serial (no overlap).
Lane class = lane name up to the first '__' or digit run, so one class = one crossing kind.

  python3 tools/token_pass/reform_rebaseline.py --die qc --base OLD.json[.gz] --batch NEW.json[.gz] --out OUT.json
  python3 tools/token_pass/reform_rebaseline.py --selftest
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
F_CLK = 1e12 / 833.0
MODELS = {
    'qc': dict(T=272641.0, tok=4403.2, per_token=36, src='compose_tokfunc.py record 94cd97b7a (Qwen ROM 1u AR)'),
    'kv': dict(T=272641.0, tok=4403.2, per_token=36, src='compose_tokfunc.py record 94cd97b7a (Qwen ROM 1u AR)'),
    'head': dict(T=F_CLK / 1258.9, tok=1258.9, per_token=1, src='TOK-14 DS AR 1258.9 (head once a token)'),
}
MODELS['s81_head'] = MODELS['head']


def load_lanes(path: Path) -> dict:
    raw = gzip.open(path, 'rt').read() if str(path).endswith('.gz') else Path(path).read_text()
    d = json.loads(raw)
    lanes = (d.get('latency') or {}).get('lanes') if 'latency' in d else d.get('lanes')
    if not isinstance(lanes, dict) or not lanes:
        raise SystemExit(f'{path}: no latency.lanes table')
    return {k: int(v['cycles']) for k, v in lanes.items()}


def lane_class(name: str) -> str:
    return re.split(r'__|\d', name, maxsplit=1)[0].rstrip('_') or name


def delta(base: dict, new: dict) -> dict:
    ch = {k: (base[k], new[k]) for k in new if k in base and base[k] != new[k]}
    cls: dict = {}
    for k, (o, n) in ch.items():
        c = cls.setdefault(lane_class(k), dict(lanes=0, sum=0, max_inc=0, max_lane=None, min=0))
        c['lanes'] += 1
        c['sum'] += n - o
        if n - o > c['max_inc']:
            c['max_inc'], c['max_lane'] = n - o, k
        c['min'] = min(c['min'], n - o)
    return dict(changed=len(ch), added=sorted(set(new) - set(base)), removed=sorted(set(base) - set(new)),
                lane_cycles=sum(n - o for o, n in ch.values()),
                max_inc=max([n - o for o, n in ch.values()] + [0]), classes=cls,
                lanes={k: dict(old=o, new=n) for k, (o, n) in sorted(ch.items())})


def price_bound(die: str, d: dict) -> dict:
    m = MODELS[die]
    # added lanes (new crossings) are charged their full cycles, once per class, as an increase
    dT = m['per_token'] * sum(max(c['max_inc'], 0) for c in d['classes'].values())
    T = m['T'] + dT
    return dict(model=m['src'], kind='BOUND (serial, every changed class on the critical path)', T_base=round(m['T'], 1),
                dT=dT, T_new=round(T, 1), tok_base=m['tok'], tok_new=round(m['tok'] * m['T'] / T, 2),
                pct=round(100 * (m['T'] / T - 1), 3))


def price_s81(base: Path, new: Path) -> dict:
    out = {}
    for tag, p in (('base', base), ('batch', new)):
        with tempfile.TemporaryDirectory() as td:
            if str(p).endswith('.gz'):
                (Path(td) / 'plan.json').write_text(gzip.open(p, 'rt').read())
                p = Path(td) / 'plan.json'
            # the compiler LAT ABI for this plan (gen.py latency), then the composer on plan + table
            r = subprocess.run([sys.executable, str(ROOT / 'tools/die_plan/gen.py'), 'latency', str(p), '--out', f'{td}/lat'],
                               cwd=ROOT, capture_output=True, text=True)
            lat = sorted(Path(td, 'lat').glob('*_latency.json')) if not r.returncode else []
            if not lat:
                return dict(model='gen.py latency', error=(r.stderr or r.stdout)[-800:])
            r = subprocess.run([sys.executable, str(ROOT / 'tools/s81_dv/tokfunc/compose_tok_ds.py'), '--plan', str(p),
                                '--lat', str(lat[0]), '--out', f'{td}/c'], cwd=ROOT, capture_output=True, text=True)
            if r.returncode:
                return dict(model='compose_tok_ds', error=r.stderr[-800:])
            c1 = json.loads((Path(td) / 'c/compose_1u.json').read_text())
            out[tag] = {wl: dict(T=w['T_cycles'], tok_s=w['tok_s']) for wl, w in c1['workloads'].items()}
    return dict(model='compose_tok_ds --plan (TOK-13/14 method)', kind='MODEL', **out,
                pct={wl: round(100 * (out['batch'][wl]['tok_s'] / out['base'][wl]['tok_s'] - 1), 3) for wl in out['base']})


def price_hbm(d: dict) -> dict:
    sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/throughput'), str(ROOT / 'src')]
    import importlib.util
    import io
    import contextlib
    spec = importlib.util.spec_from_file_location('p44', Path(__file__).with_name('hbm_price_d44t.py'))
    src = spec.loader.get_data(spec.origin).decode()
    src = src.split('CASES = {')[0]          # model + run() + A1 row only, no output
    g: dict = {'__name__': 'p44'}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(src, spec.origin, 'exec'), g)
    A1, run, tok, sfu = g['A1'], g['run'], g['tok'], g['sfu']
    k = d['max_inc']

    def t(dk):
        e = {'SU': 3, 'IDX': A1['extra']['IDX'] + dk, 'SM': A1['extra']['SM'] + dk, 'COLL': dk, 'FUSED': dk}
        return run(extra=e, south='exact', sfu=A1['sfu'] + dk, tnode=True)
    t0, t1 = t(0), t(k)
    return dict(model='TOK-13d DS native S2 (price_d44t.py)', kind=f'BOUND (+{k} on IDX/SM/COLL/FUSED/SFU)',
                T_base=round(t0, 2), T_new=round(t1, 2), tok_base=tok(t0), tok_new=tok(t1),
                pct=round(100 * (t0 / t1 - 1), 3))


def selftest() -> bool:
    b = {'x_E0_in': 3, 'xring__s_0N_C__s_1N_C': 5, 'L36m': 14, 'L36': 14}
    n = dict(b, x_E0_in=5, L36=18, L36m=17)
    d = delta(b, n)
    ok = d['changed'] == 3 and d['lane_cycles'] == 9 and d['classes']['L']['max_inc'] == 4 and d['classes']['x_E']['lanes'] == 1
    p = price_bound('qc', d)
    ok &= p['dT'] == 36 * (4 + 2) and p['tok_new'] < p['tok_base']
    print('selftest', 'PASS' if ok else 'FAIL', d['classes'], p['tok_new'])
    return ok


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--die', choices=['s81', 'head', 's81_head', 'qc', 'kv', 'hbm'])
    ap.add_argument('--base', type=Path)
    ap.add_argument('--batch', type=Path)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args(argv)
    if a.selftest:
        return 0 if selftest() else 1
    d = delta(load_lanes(a.base), load_lanes(a.batch))
    if a.die == 's81':
        pr = price_s81(a.base.resolve(), a.batch.resolve())
    elif a.die == 'hbm':
        pr = price_hbm(d)
    else:
        pr = price_bound(a.die, d)
    res = dict(tool='reform_rebaseline.py', die=a.die, base=str(a.base), batch=str(a.batch),
               delta={k: v for k, v in d.items() if k != 'lanes'}, price=pr, lanes=d['lanes'])
    if a.out:
        a.out.write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps(dict(die=a.die, changed=d['changed'], lane_cycles=d['lane_cycles'], max_inc=d['max_inc'],
                          added=len(d['added']), removed=len(d['removed']), price=pr))[:1500])
    return 0


if __name__ == '__main__':
    sys.exit(main())
