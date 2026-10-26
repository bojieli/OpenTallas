#!/usr/bin/env python3
"""HBM die case clock-pin audit (hbmdie-v10-sta, 2026-10-12): every register-stage instance of a die STA case (die
relays / wire stages hfd_rly_*, stations hfd_stn_*, attention->SU relays hfd_att_su_relay) must have its clock pin
connected, or the die STA cannot time its hops (the kv_die relays had none: main 758ccc84c).  A station with no ck
whose a/b nets belong to a forwarded-clock bus (clock_classes.json 'fclk', written by tools/hbm_die_views.py die
--relays) or that is a forwarded station ('fwd_dom') is source-synchronous: its clock arrives on the forwarded bits
of its a port; it is counted separately (FORWARDED), not as a failure.
usage: hbm_die_clock_pins.py <case dir>   -> prints one JSON line; exit 1 if any common-clock stage is unclocked."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

case = Path(sys.argv[1])
cc = json.loads((case / 'clock_classes.json').read_text()) if (case / 'clock_classes.json').exists() else {}
fclk, fwd = set(cc.get('fclk', [])), set(cc.get('fwd_dom', []))
REG = re.compile(r'\s*(hfd_(?:stn|rly)_\w+|hfd_att_su_relay)\s+(\S+)\s*\((.*)\);')
tot, unck, fwdn = Counter(), Counter(), Counter()
bad = []


def isf(net):
    b = net[2:] if net.startswith('n_') else net
    while b:
        if b in fclk:
            return True
        if '_' not in b:
            return False
        b = b.rsplit('_', 1)[0]
    return False


for ln in open(case / 'die.v'):
    m = REG.match(ln)
    if not m:
        continue
    fam = re.sub(r'\d.*$', '', m.group(1)).rstrip('_') or m.group(1)
    tot[fam] += 1
    con = dict(re.findall(r'\.(\w+)\(([^)]*)\)', m.group(3)))
    if any(k in con and con[k] for k in ('ck', 'clk')) or any(re.fullmatch(r'ck\d+', k) for k in con):
        continue
    if m.group(2) in fwd or any(isf(con.get(p, '')) for p in ('a', 'b', 'i', 'o')):
        fwdn[fam] += 1
        continue
    unck[fam] += 1
    if len(bad) < 20:
        bad.append((m.group(1), m.group(2)))
print(json.dumps(dict(stages=sum(tot.values()), by_family=dict(tot), forwarded_clock=sum(fwdn.values()),
                      forwarded_by_family=dict(fwdn), UNCLOCKED=sum(unck.values()), unclocked_by_family=dict(unck),
                      examples=bad)))
sys.exit(1 if unck else 0)
