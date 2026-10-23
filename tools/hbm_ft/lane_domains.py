#!/usr/bin/env python3
"""FT-HBM-SU: clock domain of every die lane source bus (input to su_ft_spec.py).

A feedthrough station must run on the clock of the die relays it replaces.  The HBM die relays (hbfd_*) are clocked
from three die clock families: n_dks_* (stream, 833.333 ps), n_dkr_* (serial, 1111.111 ps), n_dkh_* (hbm, 1024 ps).
For every lane source bus named in the FT-TOOL ftspecs (src = "<inst>/<bus>") this reads die.v once and takes the
clock family of the hbfd relay whose .i carries the source port's first net, else of the first clocked instance
(.ck/.clk pin) that reads that net.  Unresolved buses are '?'.

    lane_domains.py --die-v case_b/die.v --ftspec-dir PLAN/ftspec --glob 'su_*.json' --out lane_domains.json
"""
import argparse, glob, json, re

FAM = {'n_dks': 'stream', 'n_dkr': 'serial', 'n_dkh': 'hbm'}
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--die-v', required=True); ap.add_argument('--ftspec-dir', required=True)
ap.add_argument('--glob', default='su_*.json'); ap.add_argument('--out', required=True)
a = ap.parse_args()
srcs = sorted({p['src'] for f in glob.glob(f'{a.ftspec_dir}/{a.glob}') for p in json.load(open(f))['paths']})
want_port = {tuple(s.split('/', 1)) for s in srcs}
inst_re = re.compile(r'^\s*(\S+)\s+(\S+)\s*\($')
port_net, relay_in, cons = {}, {}, {}
cur = master = None; buf = ''
for line in open(a.die_v):
    if cur is None:
        m = inst_re.match(line)
        if m and not line.lstrip().startswith(('module', 'input', 'output', 'wire', 'assign')):
            master, cur, buf = m.group(1), m.group(2), ''
        continue
    buf += line
    if line.strip() != ');':
        continue
    ck = re.search(r'\.(ck|clk|ck_i|clk_i)\(([^)\s]+)\)', buf)
    fam = re.sub(r'_L\d+.*', '', ck.group(2)) if ck else None
    if master.startswith('hbfd_'):
        im = re.search(r'\.i\(\{?([^)]*)\)', buf)
        if im and fam:
            for n in re.findall(r'[\w\[\]]+', im.group(1)):
                relay_in.setdefault(n, fam)
    else:
        for p, n in re.findall(r'\.(\w+)\(\{?\s*([^,}\)\s]+)', buf):
            if (cur, p) in want_port:
                port_net[(cur, p)] = n
    if fam:
        for n in set(re.findall(r'\bn\d+\b', buf)):
            cons.setdefault(n, fam)
    cur = None
out = {}
for s in srcs:
    n = port_net.get(tuple(s.split('/', 1)))
    f = relay_in.get(n) or cons.get(n) if n else None
    out[s] = FAM.get(f, '?')
json.dump(dict(schema='opentallas.hbm_ft.lane_domains.v1', die_v=a.die_v,
               rule='relay (hbfd_*) on the source port net, else its first clocked consumer; ' +
                    ', '.join(f'{k}={v}' for k, v in FAM.items()), domains=out), open(a.out, 'w'), indent=1)
print(a.out, len(out))
