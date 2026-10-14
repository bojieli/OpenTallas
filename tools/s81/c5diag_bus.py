#!/usr/bin/env python3
"""S81 die c5 diagnosis: slack / length of every net touching given instance bus pins.

  c5diag_bus.py <placed.def> <wirelength_grt.csv> <out.json> --pin 'sp_hc_s wq_d' --pin 'sp_hc_s y_d' \
      --end tt=end_tt.rpt --end ff=end_ff.rpt --lef a.lef ...
For each --pin (instance, pin base): the nets on that bus, the pin on the other side (class with indices
stripped), pin-to-pin Manhattan, GRT routed length, and the end-report slack of the bus pin itself (when it is
an endpoint) and of the far pin (when that is the endpoint).
"""
import argparse, collections, json, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from c5diag_paths import read_lef, read_def_components, pin_xy, kind, pbase, iter_end


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('deff'); ap.add_argument('wl'); ap.add_argument('out')
    ap.add_argument('--pin', action='append', default=[])
    ap.add_argument('--end', action='append', default=[])
    ap.add_argument('--lef', action='append', default=[])
    a = ap.parse_args()
    want = set(tuple(p.split()) for p in a.pin)
    lef = read_lef(a.lef)
    comp = read_def_components(a.deff)
    pr = re.compile(r'\(\s*(\S+)\s+(\S+)\s*\)')
    recs = []          # (bus key, net, near pin, far pin, manhattan)
    inside = False
    buf = ''
    with open(a.deff) as f:
        for ln in f:
            if not inside:
                inside = ln.startswith('NETS ')
                continue
            if ln.startswith('END NETS'):
                break
            buf += ln
            if ';' not in ln:
                continue
            rec, buf = buf, ''
            if not any(w[0] in rec for w in want):
                continue
            s = rec.split(None, 2)
            pins = pr.findall(s[2])
            near = [(i, p) for i, p in pins if (i, pbase(p)) in want]
            if not near:
                continue
            for n in near:
                for o in pins:
                    if o == n:
                        continue
                    x0 = pin_xy(comp, lef, *n); x1 = pin_xy(comp, lef, *o)
                    man = abs(x0[0] - x1[0]) + abs(x0[1] - x1[1]) if x0 and x1 else -1
                    recs.append((n[0] + ' ' + pbase(n[1]), s[1], n[0] + '/' + n[1], o[0] + '/' + o[1], man,
                                 '%s(%s).%s' % (kind(o[0]), comp[o[0]][0] if o[0] in comp else '?', pbase(o[1]))))
    nets = set(r[1] for r in recs)
    wl = {}
    with open(a.wl) as f:
        for ln in f:
            s = ln.split()
            if len(s) >= 4 and s[1] in nets:
                wl[s[1]] = float(s[2])
    pinset = set(r[2] for r in recs) | set(r[3] for r in recs)
    slk = {}
    for spec in a.end:
        name, path = spec.split('=', 1)
        d = slk[name] = {}
        for ep, s in iter_end(path):
            if ep in pinset:
                d[ep] = s
    out = {}
    agg = collections.defaultdict(list)
    for r in recs:
        agg[(r[0], r[5])].append(r)
    for (bus, far), rs in sorted(agg.items()):
        e = {'bits': len(rs), 'manhattan_um': [round(min(r[4] for r in rs), 1), round(max(r[4] for r in rs), 1)],
             'routed_um': [min(wl.get(r[1], -1) for r in rs), max(wl.get(r[1], -1) for r in rs)]}
        for name, d in slk.items():
            for tag, col in (('bus_pin', 2), ('far_pin', 3)):
                v = [d[r[col]] for r in rs if r[col] in d]
                if v:
                    e['%s_slack_at_%s' % (name, tag)] = {'endpoints': len(v), 'min': min(v), 'max': max(v),
                                                         'violating': sum(1 for x in v if x < 0)}
        out['%s <-> %s' % (bus, far)] = e
    json.dump(out, open(a.out, 'w'), indent=1)
    for k, v in out.items():
        print(k, json.dumps(v))


if __name__ == '__main__':
    main()
