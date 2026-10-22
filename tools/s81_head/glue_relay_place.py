#!/usr/bin/env python3
"""S81 HEAD ctl glue R7 (STW-S81c-COLLA2 10-22): relay-stage placement plan.

r5m (gate 3_place, 770 ps): 4,061 setup violators, WNS -1,045 ps, every one ONE logic level and 1.1-2.0 mm of wire:
the generator (glue_rg_gen.py) gave every zone-to-zone bus n = ceil((d + 100) / 380) kept relay stages, but the
wirelength-driven global placement is indifferent to WHERE a chain's stages sit on the line between its ends (the HPWL of
a collinear chain is the same for any spacing), so it collapses them: stage 1 at the face, stages 2..n at the centre
(u_acc_1 y 3883 -> u_acc_2 y 1930; u_sn_1 3884 -> u_sn_2 1953; reset u_zr_* the same).  This plan puts stage j of an
n-stage chain at j / (n + 1) of the straight line between its zone anchors (the anchors the stage counts were sized on,
relay_ledger.json, MAIN 'm' / FB 'f'), so every registered hop is <= d / (n + 1) <= ~380 um.  RTL, ports and latency
unchanged; the cells are FIRM through global placement and released before detailed placement
(physical/common_flow/relay_chain_place.tcl / relay_chain_release.tcl).

usage: glue_relay_place.py <ledger.json> <glue_r3.sv> <m|f> <out.txt>
out: one line per relay instance (hierarchy prefix under the core): "<inst> <x_um> <y_um> <chain>"
"""
import json, re, sys

led = json.load(open(sys.argv[1])); rtl = open(sys.argv[2]).read(); k = sys.argv[3]; out = sys.argv[4]
A = led['anchors'][k]
insts = re.findall(r'\b(?:ot_s81hd_rs32|ot_s81hd_rs8|ot_s81hd_kf|ot_s81hd_rv1|ot_s81hd_rr1)\s+(u_\w+)\s*\(\.ck\(ck\)', rtl)
pos = {}
def put(inst, a, b, j, n, chain):
    t = j / (n + 1.0)
    pos[inst] = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, chain)
for nm, r in led['relays'].items():
    a, b, n = A[r['src']], A[r['dst']], int(r['stages'])
    pats = [re.compile(rf'^u_{re.escape(nm)}_(\d+)_\d+$'), re.compile(rf'^u_{re.escape(nm)}_rr(\d+)$'),
            re.compile(rf'^u_{re.escape(nm)}_v\d+_(\d+)$')]
    hit = 0
    for i in insts:
        for p in pats:
            m = p.match(i)
            if m:
                j = int(m.group(1)); assert 1 <= j <= n, (i, n); put(i, a, b, j, n, nm); hit += 1; break
    assert hit, f'no relay instance for bus {nm}'
dr = int(led['reset_forest_hops'])
for i in insts:
    m = re.match(r'^u_zr_(\w+)_(\d+)$', i)
    if m and m.group(1) in A:
        put(i, A['RST'], A[m.group(1)], int(m.group(2)), dr, 'zr')
with open(out, 'w') as f:
    f.write(f'# glue_relay_place.py {k}: {len(pos)} relay instances\n')
    for i, (x, y, c) in sorted(pos.items()):
        f.write(f'{i} {x:.2f} {y:.2f} {c}\n')
print(len(pos), 'relay instances ->', out)
