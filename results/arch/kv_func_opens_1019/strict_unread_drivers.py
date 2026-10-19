#!/usr/bin/env python3
"""Evidence: exact strict GEN7 unread bits -> (driver master, instance, port, port bit), reproducing the binder count.
Uses the pinned GEN7 binder (tools/die_port_bind.py of the GEN7 worktree) and the final pad file the strict run consumed."""
import collections, gzip, hashlib, importlib.util, json, pathlib, sys
P = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '/srv/opentallas-scratch/claude/kv-exact-padgap-1019/gen7_strict')
W = pathlib.Path('/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14r-4db097403-codexmub')
OUT = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else '.')
spec = importlib.util.spec_from_file_location('bind', W / 'tools/die_port_bind.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
sha = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
pb = json.loads((P / 'port_bind_v2.json').read_text()); die = P / 'die_bound.v'
padf = P / 'output_pads.pv.json'
pads = b.load_pads(json.loads(padf.read_text()))
mods = {}; srcs = {}
for mst, rec in pb['masters'].items():
    if not rec.get('rtl'): continue
    p = pathlib.Path(rec['rtl']); p = p if p.is_absolute() else W / p
    if p not in srcs: srcs[p] = b.parse_modules(p.read_text(), str(p))
    mods[mst] = next(m for m in srcs[p] if m.name == mst)
nets, tin, tout, insts = b.parse_die(str(die))
rd = collections.defaultdict(set); drv = collections.defaultdict(list); spare = set()
for mst, inst, params, cm in insts:
    m = mods.get(mst)
    if m is None: continue
    env = m.env(params)
    for pn, e in cm.items():
        if pn not in m.ports or not e: continue
        d = m.ports[pn][0]; bits = b.expr_bits(e, nets) or []
        w = m.width(pn, env); key = (mst, pn, inst) if (mst, pn, inst) in pads else (mst, pn)
        pset = b.pad_bits(pads[key], w if w is not None else len(bits)) if key in pads else set()
        for k, bt in enumerate(bits):
            if bt[0] in ('CONST', 'Z', 'UNDECL'): continue
            pbit = len(bits) - 1 - k
            if d == 'output':
                drv[tuple(bt)].append((mst, inst, pn, pbit))
                if pbit in pset: spare.add(tuple(bt))
            else:
                rd[bt[0]].add(bt[1])
for n in tout:
    w, lo = nets[n]; rd[n].update(range(lo, lo + w))
rows = []
for bt, ds in drv.items():
    n, i = bt
    if i in rd.get(n, ()) or n in tin or bt in spare: continue
    for (mst, inst, pn, pbit) in ds: rows.append(dict(net=n, bit=i, master=mst, instance=inst, port=pn, port_bit=pbit))
by = collections.Counter((r['master'], r['port']) for r in rows)
byi = collections.defaultdict(set)
for r in rows: byi[(r['master'], r['port'])].add(r['instance'])
summ = dict(die_sha256=sha(die), pad_file=str(padf), pad_sha256=sha(padf), strict_unread_expected=pb['summary']['unread_net_bits'],
            reproduced_unread_bits=len(rows),
            by_master_port=[dict(master=m, port=p, bits=c, instances=len(byi[(m, p)])) for (m, p), c in by.most_common()])
(OUT / 'strict_unread_summary.json').write_text(json.dumps(summ, indent=1) + '\n')
with gzip.open(OUT / 'strict_unread_bits.json.gz', 'wt') as f: json.dump(rows, f)
print(json.dumps(dict(reproduced=len(rows), expected=summ['strict_unread_expected'], master_ports=len(by))))
