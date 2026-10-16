#!/usr/bin/env python3
"""Per-sink die clock latency from view_case sink_paths_<corner>.rpt (report_checks -from <view> full_clock_expanded):
the launch clock-pin arrival of each view; writes {corner: {inst: ps}} and, with --pads, the leaf pad repeaters that
equalise every sink to the slowest one (skew feedback for die_clock_tree.build leaf_pads).

    sink_latency.py OUT_DIR [--pad-ps 18] [--pads pads.json] [--prev-pads pads.json]
"""
import argparse, json, re
from pathlib import Path


def parse(fn):
    lat = {}
    blk = Path(fn).read_text().split('Startpoint: ')[1:]
    for b in blk:
        inst = b.split()[0]
        for line in b.splitlines():
            m = re.search(r'\s([-\d.]+)\s+[\^v]\s+' + re.escape(inst) + r'/clk \(', line)
            if m:
                lat.setdefault(inst, float(m.group(1)))
                break
    return lat


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out', type=Path)
    ap.add_argument('--pad-ps', type=float, default=18.0)
    ap.add_argument('--pads', type=Path)
    ap.add_argument('--ff-ratio', type=float, default=0.7)
    ap.add_argument('--prev-pads', type=Path)
    a = ap.parse_args()
    L = {c: parse(a.out / f'sink_paths_{c}.rpt') for c in ('tt', 'ff')}
    res = {}
    for c, d in L.items():
        v = list(d.values())
        res[c] = dict(n=len(v), min=round(min(v), 2), max=round(max(v), 2), spread=round(max(v) - min(v), 2))
    print(json.dumps(res))
    (a.out / 'sink_latency.json').write_text(json.dumps(dict(summary=res, latency=L), indent=1))
    if a.pads:
        # two-level measured correction: quadrant pads (quadrant root input) equalise the quadrant maxima, leaf pads
        # equalise each sink to its quadrant maximum; one pad ~ pad_ps at TT and ~ff_ratio x at FF (corner mean)
        import re as _re
        prev = json.loads(a.prev_pads.read_text()) if a.prev_pads else {}
        pq, pl = dict(prev.get('quadrant', {})), dict(prev.get('leaf', {}))
        q = lambda i: _re.search(r'(SW|SE|NW|NE)', i).group(1)
        tt, ff = L['tt'], L['ff']
        def need(dt, df):
            return (dt / a.pad_ps + df / (a.pad_ps * a.ff_ratio)) / 2
        qmax = {c: {} for c in L}
        for c, d in L.items():
            for i, v in d.items():
                qmax[c][q(i)] = max(qmax[c].get(q(i), -1e9), v)
        topt, topf = max(qmax['tt'].values()), max(qmax['ff'].values())
        for k in qmax['tt']:
            pq[k] = pq.get(k, 0) + int(round(need(topt - qmax['tt'][k], topf - qmax['ff'][k])))
        for i in tt:
            pl[i] = pl.get(i, 0) + int(round(need(qmax['tt'][q(i)] - tt[i], qmax['ff'][q(i)] - ff.get(i, qmax['ff'][q(i)]))))
        base = min(pq.values())
        pq = {k: v - base for k, v in pq.items()}
        pl = {i: v for i, v in pl.items() if v > 0}
        a.pads.write_text(json.dumps(dict(quadrant=pq, leaf=pl), indent=1))
        print('pads quadrant', pq, 'leaf', sum(pl.values()), 'on', len(pl), 'sinks')


if __name__ == '__main__':
    main()
