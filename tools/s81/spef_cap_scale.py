#!/usr/bin/env python3
"""Scale every capacitance in a SPEF by a factor (s81-die-iter 2026-10-12).

GRT-vs-DRT error bar (results/physical/die_region_drt_1012/README.md, KV column window, 3,189 nets): routed net cap is
+40 % median / +144 % p95 over the die GRT SPEF while wire length agrees within 3 %, so the error is per-unit-length
capacitance. This writes a SPEF with *D_NET totals and every *CAP entry (ground and coupling) multiplied by --factor;
resistances are unchanged.  usage: spef_cap_scale.py IN OUT --factor 1.40
"""
import argparse, gzip, re

def opn(p, m):
    return gzip.open(p, m + 't') if p.endswith('.gz') else open(p, m)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inp'); ap.add_argument('out'); ap.add_argument('--factor', type=float, required=True)
    a = ap.parse_args(); f = a.factor
    sec = None; n_net = n_cap = 0
    num = re.compile(r'^[-+0-9.eE]+$')
    with opn(a.inp, 'r') as fi, opn(a.out, 'w') as fo:
        for ln in fi:
            t = ln.split()
            if t and t[0].startswith('*'):
                k = t[0]
                if k == '*D_NET' and len(t) >= 3 and num.match(t[2]):
                    t[2] = '%.6g' % (float(t[2]) * f); ln = ' '.join(t) + '\n'; n_net += 1; sec = None
                elif k in ('*CAP', '*RES', '*CONN', '*END', '*INDUC'):
                    sec = k
            elif sec == '*CAP' and len(t) in (3, 4) and num.match(t[-1]):
                t[-1] = '%.6g' % (float(t[-1]) * f); ln = ' '.join(t) + '\n'; n_cap += 1
            fo.write(ln)
    print('OT_SPEF_SCALE factor=%.3f d_nets=%d cap_entries=%d' % (f, n_net, n_cap))

if __name__ == '__main__':
    main()
