#!/usr/bin/env python3
"""DIE-CLOCK: manifest + measured arrivals -> tools/die_clock_check.py dump (R / B / T rows, parent links, STA
arrivals), optionally carrying the P (data pair) rows of the die's own dump, so the shared check reports insertion,
flop-arrival spread and non-common path per region on the PHYSICAL tree.
  to_dump.py MANIFEST ARRIVALS_TT.tsv OUT.tsv [--pairs-from die_clock_dump.tsv]
"""
import argparse, json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('manifest'); ap.add_argument('arrivals'); ap.add_argument('out')
    ap.add_argument('--pairs-from')
    a = ap.parse_args()
    rec = json.load(open(a.manifest))
    arr = {}
    for ln in open(a.arrivals):
        f = ln.rstrip('\n').split('\t')
        arr[f[0]] = (f[1], f[2])
    cells = {c[0]: c for c in rec['cells']}
    par = rec['parent']
    with open(a.out, 'w') as fo:
        for name, t in rec['trees'].items():
            x, y = t.get('root_xy', (0.0, 0.0))
            fo.write(f"R\t{t['root']}\t{x}\t{y}\t-\t-\n")
        for n, c in cells.items():
            l_, e_ = arr.get(f'{n}/Y', ('-', '-'))
            fo.write(f"B\t{n}\t{c[1]}\t{c[2]}\t{c[3]}\t{par.get(n, '-')}\t{l_}\t{e_}\n")
        for p, s in rec['sinks'].items():
            l_, e_ = arr.get(p, ('-', '-'))
            fo.write(f"T\t{p}\t{s['master']}\t{s['x']}\t{s['y']}\t{par[p]}\t{l_}\t{e_}\n")
        if a.pairs_from:
            for ln in open(a.pairs_from):
                if ln.startswith('P\t'):
                    fo.write(ln)


if __name__ == '__main__':
    main()
