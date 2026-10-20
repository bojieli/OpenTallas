#!/usr/bin/env python3
"""Evidence: trace every strict-unread relay/landing payload bit upstream through same-index relay payload edges to its
non-relay origin (master, instance, port, bit) or a constant; and list the downstream readers of sibling bits on the same
final net (who consumes the chain end). Pure netlist walk on the pinned GEN7 bound die."""
import collections, gzip, importlib.util, json, pathlib, re, sys
P = pathlib.Path('/srv/opentallas-scratch/claude/kv-exact-padgap-1019/gen7_strict')
W = pathlib.Path('/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14r-4db097403-codexmub')
OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '.')
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
drv = {}; conn = {}; rd = collections.defaultdict(list)
for mst, inst, params, cm in insts:
    m = mods.get(mst)
    if m is None: continue
    conn[inst] = (mst, {})
    for pn, e in cm.items():
        if pn not in m.ports or not e: continue
        bits = b.expr_bits(e, nets) or []
        conn[inst][1][pn] = bits
        d = m.ports[pn][0]
        for k, bt in enumerate(bits):
            pbit = len(bits) - 1 - k
            if d == 'output' and bt[0] not in ('CONST', 'Z', 'UNDECL'): drv[tuple(bt)] = (mst, inst, pn, pbit)
            elif d != 'output' and bt[0] not in ('CONST', 'Z', 'UNDECL'): rd[bt[0]].append((bt[1], mst, inst, pn, pbit))
def inpin(inst, pn, pbit):
    bits = conn[inst][1].get(pn) or []
    return tuple(bits[len(bits) - 1 - pbit]) if pbit < len(bits) else None
rows = json.load(gzip.open(OUT / 'strict_unread_bits.json.gz'))
res = []
for r in rows:
    if not RELAY.match(r['master']) or r['port'] != 'b': continue
    hops = 0; inst, pbit = r['instance'], r['port_bit']; origin = None
    while True:
        src = inpin(inst, 'a', pbit)
        if src is None: origin = ('UNCONNECTED',); break
        if src[0] == 'CONST': origin = ('CONST', src[1]); break
        d = drv.get(src)
        if d is None: origin = ('TOPIN', src[0], src[1]); break
        if RELAY.match(d[0]) and d[2] == 'b': inst, pbit = d[1], d[3]; hops += 1; continue
        origin = ('DRIVER', d[0], d[1], d[2], d[3]); break
    readers = sorted({(x[1], x[3]) for x in rd.get(r['net'], [])})
    res.append(dict(r, hops=hops, origin=list(origin), net_readers=[list(x) for x in readers]))
with gzip.open(OUT / 'relay_origins.json.gz', 'wt') as f: json.dump(res, f)
c = collections.Counter(); ex = {}
for x in res:
    o = x['origin']; key = (re.sub(r'\d+', 'N', x['net']), o[0], o[1] if o[0] == 'DRIVER' else str(o[1:]) , o[3] if o[0] == 'DRIVER' else '', tuple(map(tuple, x['net_readers'])))
    c[key] += 1; ex.setdefault(key, (x['net'], x['bit'], o))
summ = [dict(net_class=k[0], origin_kind=k[1], origin_master=k[2], origin_port=k[3], net_readers=k[4], bits=v, example=ex[k]) for k, v in c.most_common()]
(OUT / 'relay_origins_summary.json').write_text(json.dumps(dict(relay_unread_bits=len(res), classes=summ), indent=1, default=list) + '\n')
print(len(res), len(summ))
