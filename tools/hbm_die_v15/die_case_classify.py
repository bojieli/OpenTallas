#!/usr/bin/env python3
"""Classify a die_case.py run by path class and owner (H-DIE 2026-10-15).
    die_case_classify.py CASE_OUT_DIR [--json OUT]
Reads paths_{tt_max,ff_min}.txt (startpoint endpoint slack, one per endpoint), maps each instance to its master class
(phy / ctl / svg / sm / clock repeater / port) and reports per (start class -> end class, corner): endpoints, failing,
worst, TNS, the owner that fixes it and the structural action."""
import argparse, json, re, gzip
from collections import defaultdict
from pathlib import Path

CLS = [(r'^phy_', 'phy'), (r'^ctl_', 'ctl'), (r'^svg_', 'svg'), (r'^sm_', 'sm'), (r'^dk[hs]_', 'clktree')]
OWN = {('ctl', 'phy'): ('H-DIE', 'PHY command path (leaf output flops, OREG)'),
       ('phy', 'ctl'): ('H-DIE', 'PHY read return into the controller'),
       ('ctl', 'svg'): ('H-DIE', 'K port response/ready controller -> group'),
       ('svg', 'ctl'): ('H-DIE', 'K port request group -> controller'),
       ('ctl', 'ctl'): ('H-DIE', 'K handshake round trip through the group (combinational kr_v->kr_rdy)'),
       ('svg', 'svg'): ('H-DIE', 'group internal / round trip'),
       ('svg', 'sm'): ('H-DIE + H-SM', 'SM_HBM link group -> SM (packet/command): needs die relay stations sized to the hop'),
       ('sm', 'sm'): ('H-SM', 'SM internal (SYNTH ETM)')}


def cls(name):
    inst = name.split('/')[0]
    for r, c in CLS:
        if re.match(r, inst):
            return c
    return 'port'


def load(p):
    op = gzip.open if str(p).endswith('.gz') else open
    with op(p, 'rt') as f:
        for line in f:
            a = line.split()
            if len(a) == 3:
                yield a[0], a[1], float(a[2])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('--json')
    a = ap.parse_args()
    res = {}
    for corner, fn in (('tt_setup', 'paths_tt_max.txt'), ('ff_hold', 'paths_ff_min.txt')):
        p = Path(a.out) / fn
        if not p.exists():
            p = Path(str(p) + '.gz')
        g = defaultdict(lambda: dict(endpoints=0, failing=0, worst=1e9, tns=0.0, example=''))
        for s, e, sl in load(p):
            k = (cls(s), cls(e)); r = g[k]
            r['endpoints'] += 1
            if sl < 0:
                r['failing'] += 1; r['tns'] += sl
            if sl < r['worst']:
                r['worst'] = sl; r['example'] = f'{s} -> {e}'
        res[corner] = {f'{k[0]}->{k[1]}': dict(v, worst=round(v['worst'], 2), tns=round(v['tns'], 1),
                                               owner=OWN.get(k, ('H-DIE', ''))[0], action=OWN.get(k, ('', ''))[1])
                       for k, v in sorted(g.items(), key=lambda t: t[1]['worst'])}
    txt = json.dumps(res, indent=1)
    if a.json:
        Path(a.json).write_text(txt + '\n')
    print(txt)


if __name__ == '__main__':
    main()
