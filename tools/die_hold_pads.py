#!/usr/bin/env python3
"""die-evidence-2 (2026-10-09): rule-H1 die hold pads derived from a RAW FF hold report.

Input: paths_ff_nopad.txt written by tools/hbm_die_relay_sta.py (one failing FF hold endpoint a line:
"<startpoint> <endpoint> <slack ns>").  Every reported path is a die-level path (the hardened views are black boxes),
so each failing endpoint pin gets a pad = -slack + margin, capped.  Output: {load pin: FF pad ps}, the format
tools/hbm_die_relay_sta.py --hold-pads applies (ideal wire-arc delay, x PAD_SCALE at TT / SS: disclosed there).

An endpoint whose deficit exceeds the cap is NOT padded to the cap silently: it is listed under 'over_cap' in the
summary (a hold fix that needs more than one pad stage = a die finding, not a pad).

usage: die_hold_pads.py <paths_ff_nopad.txt> --out pads.json [--margin-ps 10] [--cap-ps 150] [--summary s.json]
"""
import argparse
import json
from collections import Counter
from pathlib import Path


def derive(lines, margin, cap):
    pads, over, cls = {}, [], Counter()
    for ln in lines:
        p = ln.split()
        if len(p) != 3:
            continue
        start, end, s = p[0], p[1], float(p[2]) * 1000.0
        if s >= 0:
            continue
        need = -s + margin
        cls[end.split('/')[0].split('_')[0]] += 1
        if need > cap:
            over.append(dict(start=start, end=end, slack_ps=round(s, 1)))
            need = cap
        pads[end] = round(max(pads.get(end, 0.0), need), 1)
    return pads, over, cls


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('paths')
    ap.add_argument('--out', required=True)
    ap.add_argument('--margin-ps', type=float, default=10.0)
    ap.add_argument('--cap-ps', type=float, default=150.0)
    ap.add_argument('--summary')
    a = ap.parse_args()
    pads, over, cls = derive(Path(a.paths).read_text().splitlines(), a.margin_ps, a.cap_ps)
    Path(a.out).write_text(json.dumps(pads, indent=0) + '\n')
    s = dict(source=a.paths, margin_ps=a.margin_ps, cap_ps=a.cap_ps, pins=len(pads), over_cap=len(over),
             over_cap_examples=over[:20], endpoints_by_instance_prefix=dict(cls.most_common(30)))
    if a.summary:
        Path(a.summary).write_text(json.dumps(s, indent=1) + '\n')
    print(json.dumps({k: v for k, v in s.items() if k != 'over_cap_examples'}))


if __name__ == '__main__':
    main()
