#!/usr/bin/env python3
"""el1011-qseam 2026-10-12: Qwen ROM r22ko4 die SEAM table from the die-level netlist the die contract places.

Input: the die-chain case netlist die.v (tools/qwen_rom_fulldie_b3r2.py --recipe r22ko4 output, e.g. EPYC3
die-evidence-2/qwen_r22ko4_e7/case_r22k/die.v, src 22760e79f = hier_contract_1011/qwen_rom.json v4 placement).
Every die bus is one base net n_X plus its relay nets n_X__r1..__rK; relay k (qfd_rly_<bits>_<faces>_<frame>, the
ot_qwen_die_station TAP=0 family: one registered hop) takes .a = n_X__r{k} (n_X for k = 0) and drives .b.
Output (JSON): per bus {w, K, src, dst, relays[]} with the driver / sink resolved (relayed buses: base = driver,
last = sinks; unrelayed buses: by the slot master's port role), the class of every seam, and the corridor / tree
graph used by gen_bench.py.

    extract.py --die-v die.v --out seams.json
"""
from __future__ import annotations
import argparse, collections, json, re

# unrelayed-bus driver ports by slot master (the die's port direction for K = 0 abutted / in-tile nets)
OUTP = {'qfd_tile_nk': {'t_out', 'n_y'}, 'qfd_cst_s': {'b', 'tap'}, 'qfd_cst_n': {'a', 'tap'}}


def classify(b):
    if re.match(r'n_(clk|pll|rst_fwd$|rst_d2d$)', b) or b in ('n_clk_root',):
        return 'clock'
    if re.match(r'n_(head|cor|tap)_', b):
        return 'corridor'
    if b.startswith('n_tree_'):
        return 'tree'
    if re.match(r'n_(o4_cb_ctl|o4_cb_rdy|rs|rc|rk|seq_coll|seq_coll_x|coll_seq|coll_seq_x)(_\d+)?$', b):
        return 'credit'
    return 'p2p'


def parse(path):
    t = open(path).read()
    W = {m[2]: int(m[1]) + 1 for m in re.finditer(r'wire \[(\d+):0\] (\w+);', t)}
    for m in re.finditer(r'wire (\w+);', t):
        W.setdefault(m[1], 1)
    inst = {}
    for m in re.finditer(r'^\s+(\w+) (\w+) \((.*)\);$', t, re.M):
        inst[m[2]] = (m[1], dict(re.findall(r'\.(\w+)\((\w*)\)', m[3])))
    net = collections.defaultdict(list)
    for nm, (mst, pins) in inst.items():
        for k, v in pins.items():
            net[v].append((mst, nm, k))
    groups = collections.defaultdict(set)
    for n in W:
        groups[re.sub(r'__r\d+$', '', n)].add(n)
    buses = {}
    for b, nets in groups.items():
        K = max([int(x.rsplit('__r', 1)[1]) for x in nets if '__r' in x] or [0])
        last = f'{b}__r{K}' if K else b
        ends0 = [f'{x[1]}.{x[2]}' for x in net.get(b, []) if not x[0].startswith(('qfd_rly', 'qkd_rly'))]
        relays = []
        for k in range(K):
            r = [x for x in net[f'{b}__r{k}' if k else b] if x[0].startswith(('qfd_rly', 'qkd_rly')) and x[2] == 'a']
            assert len(r) == 1, (b, k, r)
            relays.append(dict(master=r[0][0], name=r[0][1]))
        if K:
            src = ends0
            dst = [f'{x[1]}.{x[2]}' for x in net.get(last, []) if not x[0].startswith(('qfd_rly', 'qkd_rly'))]
        else:
            src = [e for e in ends0 if e.split('.')[1] in OUTP.get(inst[e.split('.')[0]][0], set())]
            dst = [e for e in ends0 if e not in src]
            if not src and len(ends0) >= 1:          # other abutted words: the first listed endpoint drives
                src, dst = ends0[:1], ends0[1:]
        buses[b] = dict(w=W[b], K=K, src=src, dst=dst, relays=relays, cls=classify(b))
    return inst, buses


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--die-v', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--source', default='')
    a = ap.parse_args()
    inst, buses = parse(a.die_v)
    slots = {n: dict(master=m, pins=p) for n, (m, p) in inst.items() if not m.startswith(('qfd_rly', 'qkd_rly'))}
    cnt = collections.Counter(v['cls'] for v in buses.values())
    rel = collections.Counter(v['cls'] for v in buses.values() for _ in v['relays'])
    out = dict(schema='opentallas.qwen-die-seams.v1', source=a.source, buses=buses, slots=slots,
               census=dict(buses=len(buses), relays=sum(v['K'] for v in buses.values()), by_class=cnt, relays_by_class=rel))
    json.dump(out, open(a.out, 'w'))
    print(json.dumps(out['census']))


if __name__ == '__main__':
    main()
