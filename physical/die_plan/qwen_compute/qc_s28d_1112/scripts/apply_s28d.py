#!/usr/bin/env python3
"""QC-S28-D 11-12: apply the cb* bc-column spine delta (delta_s28d.json) onto a QC plan.

    python3 -I apply_s28d.py apply PLAN_IN PLAN_OUT DELTA.json[.gz]
    python3 -I apply_s28d.py check PLAN DELTA.json        # exit 0 when PLAN carries exactly the delta

KEYS TOUCHED: partition_types[T].relay_sites (a NEW key) for T in delta.changes (cbn_q11 x2, cbn_q00 x3, cbf_q01,
cbf_q01_s2, cbf_q11).  Nothing else.  The from-value of every edit is 'key absent'; a plan where any of these
types already carries relay_sites is refused (not merged), so the delta re-applies onto any composer plan (s28,
s28a, s28b, s28c) that did not touch relay_sites of these types.

relay_sites = DIE-KV-59 FIRM sites of EXISTING RTL flops (kit_istations rs_place_all: FIRM before GPL, released to
DPL with the face flops): u_bin_<bc_i>, each xstn u_st (b_q + ctl at the column site, t_q/hold/cap at the tap
site), and every d<D> stage of the station->station chain.  0 added cycles, no netlist change, no position /
orient / outline / pin / bus / station / clock change: EQ by construction.
Serialisation: the input plan's (compact or indent=1) form is kept."""
import gzip, json, sys


def load(p):
    return json.load(gzip.open(p, 'rt') if str(p).endswith('.gz') else open(p))


def apply(P, D):
    n = 0
    for tn, ch in D['changes'].items():
        t = P['partition_types'].get(tn)
        if t is None:
            raise SystemExit(f'{tn}: not in plan')
        if 'relay_sites' in t:
            raise SystemExit(f'{tn}: plan already has relay_sites: refuse (from-value must be absent)')
        t['relay_sites'] = dict(ch['relay_sites']); n += len(ch['relay_sites'])
    return n


def main(a):
    if a[0] == 'apply':
        src, out, dl = a[1:4]
        text = open(src).read(); P = json.loads(text); D = load(dl)
        n = apply(P, D)
        open(out, 'w').write(json.dumps(P, indent=1 if text.startswith('{\n') else None) + '\n')
        print(f'applied relay_sites on {len(D["changes"])} types, {n} flop sites')
        return 0
    if a[0] == 'check':
        P = json.load(open(a[1])); D = load(a[2]); bad = 0
        for tn, ch in D['changes'].items():
            if P['partition_types'][tn].get('relay_sites') != ch['relay_sites']:
                print('MISMATCH', tn); bad += 1
        print('check', 'OK' if not bad else f'{bad} mismatches'); return 1 if bad else 0
    raise SystemExit(__doc__)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
