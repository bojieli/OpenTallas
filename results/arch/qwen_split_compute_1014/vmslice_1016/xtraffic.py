#!/usr/bin/env python3
"""Slice-external traffic per variant: every non-clock/reset leg with a slice endpoint (vm_s*, su_s*), excluding the
port-local rb_k legs and slice-local VM<->SU legs (C).  Base: VM-external legs.  Bits = sum of leg widths (wires);
centroid Manhattan mm (metrics.py) and box gap mm."""
import json, sys, collections
def run(f, pref):
    d = json.load(open(f)); I = {i['n']: i for i in d['insts']}
    c = lambda n: (I[n]['x'] + I[n]['w'] / 2, I[n]['y'] + I[n]['h'] / 2)
    def box(p, q):
        return max(0.0, q['x'] - (p['x'] + p['w']), p['x'] - (q['x'] + q['w'])) + max(0.0, q['y'] - (p['y'] + p['h']), p['y'] - (q['y'] + q['h']))
    tot = collections.Counter(); per = collections.defaultdict(lambda: [0, 0.0, 0.0, 0.0])
    for b, cl, w, eps in d['buses']:
        if cl in ('clock_trunk', 'reset'): continue
        a = eps[0]
        for q in eps[1:]:
            ends = (a, q)
            if not any(e.startswith(pref) for e in ends): continue
            if b.startswith('b2_rb_'): key = 'rb (port-local)'
            elif all(e.startswith(('vm_s', 'su_s')) for e in ends): key = 'slice-local VM<->SU'
            else:
                o = [e for e in ends if not e.startswith(pref)][0] if not all(e.startswith(pref) for e in ends) else 'slice'
                key = 'to ' + o
            pa, pq = c(a), c(q); L = (abs(pa[0] - pq[0]) + abs(pa[1] - pq[1])) / 1000; B = box(I[a], I[q]) / 1000
            r = per[key]; r[0] += w; r[1] += w * L; r[2] = max(r[2], L); r[3] += w * B
    out = {k: dict(bits=v[0], bit_mm=round(v[1]), mean_mm=round(v[1] / v[0], 2), max_mm=round(v[2], 2), box_bit_mm=round(v[3])) for k, v in sorted(per.items(), key=lambda kv: -kv[1][1])}
    ext = [v for k, v in per.items() if k.startswith('to ')]
    out['TOTAL slice/VM-external (excl rb, local)'] = dict(bits=sum(v[0] for v in ext), bit_mm=round(sum(v[1] for v in ext)), mean_mm=round(sum(v[1] for v in ext) / max(1, sum(v[0] for v in ext)), 2), box_bit_mm=round(sum(v[3] for v in ext)))
    return out
if __name__ == '__main__':
    for f, pref in zip(sys.argv[1::2], sys.argv[2::2]):
        print('==', f); r = run(f, tuple(pref.split(',')))
        for k, v in r.items(): print(f'  {k:42s} {v}')
