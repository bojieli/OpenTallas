#!/usr/bin/env python3
"""QC-A0-KITS-13 (ICG B-hop): per clock entry of the A0 body, the minimum number of gated register stages s_c from the
ungated domain (input-face registers on UNGATED entries + top input ports) to any register of entry c.
Registers = yosys $dff/$adff/$dffe/$adffe/$sdff* cells, kept register submodules and hard children (romleaf/rawfault),
each clocked by the entry port reaching its clock pin.  Combinational cells propagate.  A gated register fed (through
logic only) by level-0 has s = 1 (needs the clock edge right after the face capture); s = 1 + min over gated predecessors.
A cluster's enable may then be relayed K <= s_c - 1 hops later than the tile enable without missing its first edge.
usage: entry_depth.py body.json TOP ungated_entry[,..] [cell_map.json]"""
import json, sys, collections, heapq
J = json.load(open(sys.argv[1])); STATIC_IN = set(sys.argv[4].split(',')) if len(sys.argv) > 4 else set(); top = sys.argv[2]; ungated = set(sys.argv[3].split(','))
mods = J['modules']; M = mods[top]
port_of_bit = {}
for pn, p in M['ports'].items():
    for i, b in enumerate(p['bits']):
        if isinstance(b, int): port_of_bit[b] = (pn, p['direction'])
REG_T = {'$dff', '$adff', '$dffe', '$adffe', '$sdff', '$sdffe', '$sdffce', '$dffsr', '$dffsre', '$aldff', '$aldffe'}
CLK_PIN = {'CLK', 'clk', 'ck', 'CK', 'clock'}
regs = {}; comb = {}
for cn, c in M['cells'].items():
    t = c['type']; conns = c['connections']
    prim = t.startswith('$') and not t.startswith('$paramod')
    if not prim and t in mods:
        dirs = {pn: p['direction'] for pn, p in mods[t]['ports'].items()}
    elif not prim:
        dirs = {pn: ('output' if pn in ('Y', 'Q', 'QN', 'GCLK', 'CON', 'SN') else 'input') for pn in conns}   # ASAP7 std cells
    else:
        dirs = c.get('port_directions', {})
    ck = [p for p in conns if p in CLK_PIN and not prim and dirs.get(p) == 'input']
    ins = [b for p, bs in conns.items() if dirs.get(p) == 'input' and p not in ck for b in bs if isinstance(b, int)]
    outs = [b for p, bs in conns.items() if dirs.get(p) == 'output' for b in bs if isinstance(b, int)]
    if t in REG_T:
        ins = [b for p in ('D', 'EN', 'SRST', 'AD', 'ALOAD', 'CE') if p in conns for b in conns[p] if isinstance(b, int)]
        outs = [b for b in conns.get('Q', []) if isinstance(b, int)]
        regs[cn] = (conns['CLK'][0], ins, outs, t)
    elif ck:
        regs[cn] = (conns[ck[0]][0], ins, outs, t)
    else:
        comb[cn] = (ins, outs, t)
# clock bit -> entry name (top input port bits; assigns of ck_g etc. resolved by yosys to the same bit)
def entry(b):
    return port_of_bit.get(b, ('?%s' % b, ''))[0]
drv = {}
for cn, (ins, outs, t) in comb.items():
    for b in outs: drv[b] = ('c', cn)
for rn, (ckb, ins, outs, t) in regs.items():
    for b in outs: drv[b] = ('r', rn)
# memoised: for a bit, the set of register sources (or 'IN' for a top input) through combinational logic
memo = {}
sys.setrecursionlimit(1000000)
def srcs(b):
    if b in memo: return memo[b]
    memo[b] = frozenset()
    d = drv.get(b)
    if d is None:
        r = frozenset(['IN']) if (b in port_of_bit and port_of_bit[b][0] not in STATIC_IN) else frozenset()
    elif d[0] == 'r':
        r = frozenset([d[1]])
    else:
        s = set()
        for x in comb[d[1]][0]: s |= srcs(x)
        r = frozenset(s)
    memo[b] = r; return r
pred = {}
for rn, (ckb, ins, outs, t) in regs.items():
    s = set()
    for b in ins: s |= srcs(b)
    pred[rn] = s
lvl = {}
INF = 10**9
# Dijkstra-like (unit weights) on registers
level0 = {rn for rn, v in regs.items() if entry(v[0]) in ungated}
dist = {rn: (0 if rn in level0 else INF) for rn in regs}
succ = collections.defaultdict(list)
for rn, s in pred.items():
    for p in s:
        succ[p].append(rn)
q = collections.deque()
for rn in regs:
    if rn in level0: continue
    if 'IN' in pred[rn] or any(p in level0 for p in pred[rn]):
        dist[rn] = 1; q.append(rn)
while q:
    u = q.popleft()
    for v in succ.get(u, []):
        if v in level0: continue
        if dist[v] > dist[u] + 1:
            dist[v] = dist[u] + 1; q.append(v)
by = collections.defaultdict(list)
for rn, v in regs.items():
    by[entry(v[0])].append((dist[rn], rn, v[3], len(v[2])))
out = {}
for e, L in sorted(by.items()):
    L.sort()
    h = collections.Counter()
    for x in L: h[x[0] if x[0] < INF else -1] += x[3]
    out[e] = dict(regs=len(L), bits=sum(x[3] for x in L), s_min=L[0][0] if L[0][0] < INF else None, s_hist=dict(sorted(h.items())),
                  shallow=[(x[0], x[1][-80:], x[3]) for x in L if x[0] <= 2],
                  first=[(x[0] if x[0] < INF else None, x[1][-90:], x[2]) for x in L[:3]])
json.dump(out, sys.stdout, indent=1)
