#!/usr/bin/env python3
"""KV-CLOCK 10-18: core-tree crossing HOPS of a KV die netlist (any die.v stage).  A hop = a die net from a driver
element to a load element; domain of an element = its n_clk_core_* nets (relays: ck).  Crossing = both ends on core
trees and no common tree.  Grouped per (driver, load) element pair with bit count; relays labelled by chain prefix."""
import re, sys, json, collections
dv, out = sys.argv[1], sys.argv[2]
inst_re = re.compile(r'^\s+(\w+) (\S+) \((.*)\);\s*$')
conn_re = re.compile(r'\.(\w+)\(((?:[^()]|\([^()]*\))*)\)')
bit_re = re.compile(r'(n_[A-Za-z0-9_$]+)(?:\[(\d+)(?::(\d+))?\])?')
insts = {}
for ln in open(dv):
    m = inst_re.match(ln)
    if m and m.group(1) not in ('module', 'wire', 'input', 'output'):
        insts[m.group(2)] = (m.group(1), {p: v for p, v in conn_re.findall(m.group(3))})
users = collections.defaultdict(list)          # net -> [(inst, port, nbits)]
for nm, (mst, cs) in insts.items():
    for p, v in cs.items():
        for n, hi, lo in bit_re.findall(v):
            k = 1 if not hi else (abs(int(hi) - int(lo or hi)) + 1)
            users[n].append((nm, p, k))
def dom(nm):
    return frozenset(n[len('n_clk_core_'):] for p, v in insts[nm][1].items() for n, _, _ in bit_re.findall(v) if n.startswith('n_clk_core_'))
D = {nm: dom(nm) for nm in insts}
isr = lambda nm: insts[nm][0].startswith(('qkd_rly', 'qkd_rlys', 'qkd_rst_region'))
OUTP = {'b'}   # relay outputs
pairs = collections.Counter(); ex = {}
for n, us in users.items():
    if n.startswith(('n_clk_', 'n_tie')) or len(us) < 2 or len(us) > 40:
        continue
    ds = {u for u, _, _ in us}
    if len(ds) < 2:
        continue
    doms = {u: D[u] for u in ds if D[u]}
    for u in doms:
        for v in doms:
            if u < v and not (doms[u] & doms[v]):
                key = (tuple(sorted(doms[u])), tuple(sorted(doms[v])))
                a_, b_ = (u, v)
                kind = ('R' if isr(a_) else 'B') + ('R' if isr(b_) else 'B')
                pairs[(a_, b_)] += max(k for x, _, k in us if x in (a_, b_))
summ = collections.Counter(); bits = collections.Counter()
rec = []
for (a_, b_), k in pairs.items():
    da, db = '+'.join(sorted(D[a_])), '+'.join(sorted(D[b_]))
    kind = ('R' if isr(a_) else 'B') + ('R' if isr(b_) else 'B')
    pre = lambda x: re.sub(r'(_\d+)+(__s\d+)?$', '', re.sub(r'^(rly_|rrs_n_|rrs_)', '', x)) if isr(x) else insts[x][0]
    g = (kind, tuple(sorted((da, db))), pre(a_) if isr(a_) else pre(b_))
    summ[g] += 1; bits[g] += k
    rec.append(dict(a=a_, b=b_, ma=insts[a_][0], mb=insts[b_][0], da=da, db=db, bits=k))
for g, c in sorted(summ.items(), key=lambda t: -bits[t[0]]):
    print(f'{c:6d} hops {bits[g]:8d} b  {g}')
print('TOTAL', sum(summ.values()), 'hops', sum(bits.values()), 'bits')
json.dump(rec, open(out, 'w'), indent=0)
