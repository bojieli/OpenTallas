#!/usr/bin/env python3
"""die chain: rule-H1 hold pads from a report_checks -format end report (qwen-relaunch-1011, 2026-10-11).

Every reported VIOLATED line names one die-level endpoint (an element view's abstract pin: the hardened element is a
black box at die level), so the fix is a delay on the die net into that pin.  Same rule-H1 method as
tools/hbm_die_relay_sta.py --hold-pads + tools/die_hold_pads.py (an ideal wire-arc delay, PAD_SCALE per corner,
disclosed), but sourced from the die chain's own `-format end` report instead of a 3-column paths file.

usage: pad_from_ends.py <grt_XX_ends.rpt> --out pads.json [--margin-ps 12] [--cap-ps 120] [--summary s.json]
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

# OpenSTA -format end prints the endpoint's cell after a die-level abstract pin: `t_0_0/a[3] (qfd_tile_nk)  38.06 ...`
# (qwendie-1011: the cell-less pattern matched none of r22ks_e2's 402,276 violators -> an empty pads file)
LINE = re.compile(r'^\s*(\S+)(?:\s+\(\S+\))?\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*\((VIOLATED|MET)\)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ends')
    ap.add_argument('--out', required=True)
    ap.add_argument('--margin-ps', type=float, default=12.0)
    ap.add_argument('--cap-ps', type=float, default=120.0)
    ap.add_argument('--summary')
    a = ap.parse_args()

    pads, over, cls = {}, [], Counter()
    n = 0
    for ln in Path(a.ends).read_text().splitlines():
        m = LINE.match(ln)
        if not m or m.group(5) != 'VIOLATED':
            continue
        end, slack = m.group(1), float(m.group(4))
        n += 1
        need = -slack + a.margin_ps
        blk = end.split('/')[0]
        cls[blk] += 1
        if need > a.cap_ps:
            over.append(dict(end=end, slack_ps=round(slack, 2)))
            need = a.cap_ps
        pads[end] = round(max(pads.get(end, 0.0), need), 2)

    Path(a.out).write_text(json.dumps(pads, indent=0, sort_keys=True))
    s = dict(endpoints_violated=n, pads=len(pads), margin_ps=a.margin_ps, cap_ps=a.cap_ps,
             per_block=dict(cls.most_common()), over_cap=over[:20], over_cap_n=len(over))
    if a.summary:
        Path(a.summary).write_text(json.dumps(s, indent=0))
    print(json.dumps({k: v for k, v in s.items() if k != 'over_cap'}, indent=0))


if __name__ == '__main__':
    main()
