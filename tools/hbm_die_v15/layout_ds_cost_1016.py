#!/usr/bin/env python3
"""DS tok/s proxy of a die-layout option (H-DIE-V790 10-16): H-MTP2's relay-latency method (tools/hgi_sim/
ds_relay_latency.py: per-record crossings x per-class relay-stage delta, re-run on the same S2 schedule) applied to the
v6_eval.py per-class stages of OPTION minus BASE.

One fix to the delta form for the parallel SM legs: ds_relay_latency takes max(delta fetch, delta x) per SM/ATT record,
which hides an SM_HBM saving whenever SM_X does not also drop.  Here both legs get the change of the ABSOLUTE leg
max(SM_HBM, SM_X) (bit-weighted stages of each eval), so a fetch saving counts until the x leg becomes critical.
Nominal schedule (weight fetch || x load).  Cases: AR (DS AR token) and MTP_design (verify P=6 of the 3,500 design).

    layout_ds_cost_1016.py BASE_eval.json NAME=OPTION_eval.json ... [--out FILE]      (run from the repo root)
"""
import argparse, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
os.environ.setdefault('OT_RELAY_STAGES', '/dev/null')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('base'); ap.add_argument('opts', nargs='+'); ap.add_argument('--out')
    a = ap.parse_args()
    from hgi_sim import ds_relay_latency as DR
    st = lambda p: {k: v['stages_bw'] for k, v in json.loads(Path(p).read_text())['per_class'].items()}
    b = st(a.base)
    DR._KNOB.update(dict(delta={}, upper=False, only=None)); DR._ctx()
    base = {c: DR.V.run(DR.compile_case(c), None)['cycles'] for c in ('AR', 'MTP_design')}
    rows = {}
    for spec in a.opts:
        name, p = spec.split('=', 1)
        o = st(p)
        d = {k: round(o.get(k, 0.0) - b.get(k, 0.0), 3) for k in b}
        leg = round(max(o['SM_HBM'], o['SM_X']) - max(b['SM_HBM'], b['SM_X']), 3)
        d2 = dict(d, SM_HBM=leg, SM_X=leg)
        DR._KNOB.update(dict(delta=d2, upper=False, only=None))
        r = dict(eval=p, delta_stages=d, sm_leg_delta=leg)
        for c in ('AR', 'MTP_design'):
            cyc = DR.V.run(DR.compile_case(c), None)['cycles']
            r[f'{c}_dcycles'] = round(cyc - base[c], 1); r[f'{c}_tok_pct'] = round((base[c] / cyc - 1) * 100, 3)
        rows[name] = r
        print(name, {k: v for k, v in r.items() if k.endswith(('pct', 'dcycles')) or k == 'sm_leg_delta'}, flush=True)
    out = dict(schema='opentallas.hbm.layout_ds_cost.v1', base=a.base, base_cycles=base, method=__doc__, rows=rows)
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1) + '\n')


if __name__ == '__main__':
    main()
