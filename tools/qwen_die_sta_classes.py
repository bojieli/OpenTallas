#!/usr/bin/env python3
"""Qwen die STA: classify a `report_checks -format end` endpoint report (one line per endpoint: endpoint, required,
arrival, slack) by endpoint element master family and by whether the element view is a bound ETM or an ASSUMED
constant view (views.json), so die slack is reported per path class with the assumed-view paths separated.

    python3 tools/qwen_die_sta_classes.py ENDS.rpt DIE.v VIEWS.json [--out summary.json]"""
import argparse
import collections
import json
import re
from pathlib import Path


def family(master):
    m = re.match(r'(qfd_rlyf?|qfd_cst|qfd_chead|qfd_port_tiles|qfd_lst|qfd_tile|qfd_kvc|qfd_sp_\w+?|qfd_io_\w+?|qfd_\w+?)(_|$)', master)
    return m.group(1) if m else master


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('ends', type=Path)
    ap.add_argument('netlist', type=Path, help='die.v (instance -> master)')
    ap.add_argument('views', type=Path)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args(argv)
    master = {}
    for ln in a.netlist.read_text().splitlines():
        mm = re.match(r'\s*(\w+)\s+(\\?\S+)\s*\(', ln)
        if mm and mm.group(1) not in ('module', 'input', 'output', 'wire', 'inout', 'assign'):
            master[mm.group(2).lstrip('\\')] = mm.group(1)
    v = json.loads(a.views.read_text())
    bound = set(v['etm_bound']) | {'ot_hbm3e_phy'}
    cls = collections.defaultdict(lambda: dict(n=0, viol=0, worst=1e9))
    tot = dict(n=0, viol=0, worst=1e9)
    for ln in a.ends.read_text().splitlines():
        f = ln.replace('(VIOLATED)', '').replace('(MET)', '').split()
        if len(f) < 4 or '/' not in f[0]:
            continue
        try:
            slack = float(f[-1])
        except ValueError:
            continue
        inst = f[0].rsplit('/', 1)[0]
        mst = f[1].strip('()') if f[1].startswith('(') else master.get(inst, '?')
        view = 'etm' if mst in bound else 'assumed'
        for c in (cls[(family(mst), view)], tot):
            c['n'] += 1
            c['viol'] += slack < 0
            c['worst'] = min(c['worst'], slack)
    res = dict(total=tot, by_class={f'{k[0]}|{k[1]}': x for k, x in sorted(cls.items(), key=lambda t: t[1]['worst'])})
    s = json.dumps(res, indent=1)
    if a.out:
        a.out.write_text(s + '\n')
    print(s)


if __name__ == '__main__':
    main()
