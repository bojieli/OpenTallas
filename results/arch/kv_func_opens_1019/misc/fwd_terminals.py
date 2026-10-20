#!/usr/bin/env python3
"""For every DRIVER-origin strict-unread relay bit (relay_origins.json.gz), list every terminal (non-relay) reader reached
from the SAME origin pin bit by forward same-index relay traversal (other branches). Evidence only."""
import collections, gzip, importlib.util, json, pathlib, re, sys
P = pathlib.Path('/srv/opentallas-scratch/claude/kv-exact-padgap-1019/gen7_strict')
W = pathlib.Path('/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14r-4db097403-codexmub')
IN = pathlib.Path(sys.argv[1]); OUT = pathlib.Path(sys.argv[2])
spec = importlib.util.spec_from_file_location('bind', W / 'tools/die_port_bind.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
pb = json.loads((P / 'port_bind_v2.json').read_text())
mods = {}; srcs = {}
for mst, rec in pb['masters'].items():
    if not rec.get('rtl'): continue
    p = pathlib.Path(rec['rtl']); p = p if p.is_absolute() else W / p
    if p not in srcs: srcs[p] = b.parse_modules(p.read_text(), str(p))
    mods[mst] = next(m for m in srcs[p] if m.name == mst)
nets, tin, tout, insts = b.parse_die(str(P / 'die_bound.v'))
RELAY = re.compile(r'^(qkd_rlys_\d+|qkd_astk_rly_\d+_fl|qkd_rlysh0?_\d+|qkd_landsh0?_\d+)$')
rd = collections.defaultdict(list); conn = {}; outpin = {}
for mst, inst, params, cm in insts:
    m = mods.get(mst)
    if m is None: continue
    conn[inst] = {}
    for pn, e in cm.items():
        if pn not in m.ports or not e: continue
        bits = b.expr_bits(e, nets) or []; conn[inst][pn] = bits
        d = m.ports[pn][0]
        for k, bt in enumerate(bits):
            if bt[0] in ('CONST', 'Z', 'UNDECL'): continue
            pbit = len(bits) - 1 - k
            if d == 'output': outpin[(inst, pn, pbit)] = tuple(bt)
            else: rd[tuple(bt)].append((mst, inst, pn, pbit))
def relay_out(inst, pbit):
    bits = conn[inst].get('b') or []
    return tuple(bits[len(bits) - 1 - pbit]) if pbit < len(bits) else None
cache = {}
def terminals(nb):
    if nb in cache: return cache[nb]
    out = set(); st = [nb]; seen = set()
    while st:
        x = st.pop()
        if x in seen: continue
        seen.add(x)
        for (mst, inst, pn, pbit) in rd.get(x, []):
            if RELAY.match(mst) and pn == 'a':
                y = relay_out(inst, pbit)
                if y and y[0] not in ('CONST', 'Z', 'UNDECL'): st.append(y)
            else: out.add((mst, inst, pn, pbit))
    cache[nb] = sorted(out); return cache[nb]
rows = json.load(gzip.open(IN))
res = []
for r in rows:
    o = r['origin']
    if o[0] != 'DRIVER': continue
    nb = outpin.get((o[2], o[3], o[4]))
    t = terminals(nb) if nb else []
    res.append(dict(net=r['net'], bit=r['bit'], instance=r['instance'], origin=o, terminals=[list(x) for x in t]))
with gzip.open(OUT / 'driver_terminals.json.gz', 'wt') as f: json.dump(res, f)
c = collections.Counter()
for x in res:
    c[(x['origin'][1], x['origin'][3], tuple(sorted({(t[0], t[2]) for t in x['terminals']})))] += 1
for k, v in c.most_common(): print(v, k)
