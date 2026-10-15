#!/usr/bin/env python3
"""Embed the fixed ordered ME reduction tree in its physical 4x4 tile block.

Only internal-node hosts change. Leaf identities, A/B ordering, reduction levels
and arithmetic are immutable. The dynamic program permits each internal node
to use the one unused tile of either child subtree, so every tile has at most
one node and the existing one-node tile interface remains sufficient.

The distance model is a placement lower bound, not routed qualification. A
candidate still needs real pin planning, relay allocation, cut<=0.60, exact RTL
and TT/FF/DRC gates before its latency can enter the production compiler.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Embedding:
    root: str
    unused: str
    cycles: int
    wire_um: float
    hosts: tuple


def optimize(leaves, xy, sink, pitch=490.0):
    """Return minimum maximum leaf-to-sink stages for the identical ordered AST.

State (root, unused) retains the fastest subtree; root is essential because
the parent route depends on it. Equal-cycle states minimize total wire demand.
Leaves have zero compute latency; uniform node arithmetic latency has no effect
on the host choice because every leaf traverses the same number of levels.
"""
    def dist(a, b):
        return abs(xy[a][0] - xy[b][0]) + abs(xy[a][1] - xy[b][1])

    def hops(a, b):
        return max(1, math.ceil(dist(a, b) / pitch))

    def build(ts, level, index):
        if len(ts) == 1:
            t = ts[0]
            return {(t, t): Embedding(t, t, 0, 0.0, ())}
        left = build(ts[:len(ts)//2], level - 1, index * 2)
        right = build(ts[len(ts)//2:], level - 1, index * 2 + 1)
        options = {}
        for a in left.values():
            for b in right.values():
                for root, unused in ((a.unused, b.unused), (b.unused, a.unused)):
                    cycles = max(a.cycles + hops(a.root, root), b.cycles + hops(b.root, root))
                    wire = a.wire_um + b.wire_um + dist(a.root, root) + dist(b.root, root)
                    candidate = Embedding(root, unused, cycles, wire,
                                          a.hosts + b.hosts + ((level, index, root),))
                    key = (root, unused)
                    prev = options.get(key)
                    if prev is None or (cycles, wire, candidate.hosts) < (prev.cycles, prev.wire_um, prev.hosts):
                        options[key] = candidate
        return options

    assert len(leaves) > 1 and len(leaves) & (len(leaves) - 1) == 0
    options = build(tuple(leaves), int(math.log2(len(leaves))) - 1, 0)
    return min(options.values(), key=lambda x: (x.cycles + hops(x.root, sink),
                                              x.wire_um + dist(x.root, sink), x.hosts))


def blocks(buses):
    out = {}
    for bid, cls, bits, eps in buses:
        mm = re.fullmatch(r'tree_(\d+)_(\d+)_(\d+)([ab])', bid)
        if mm:
            b, lv, idx = map(int, mm.groups()[:3])
            out.setdefault(b, {}).setdefault((lv, idx//2), {})[mm[4]] = (bid, cls, bits, eps)
    return out


def ordered_leaves(nodes):
    return [nodes[k][s][3][0] for k in sorted(nodes) if k[0] == 0 for s in 'ab']


def score(nodes, xy, sink, pitch=490.0):
    def h(a, b):
        return max(1, math.ceil((abs(xy[a][0]-xy[b][0])+abs(xy[a][1]-xy[b][1]))/pitch))
    arrivals = {}
    wire = 0.0
    for k, ab in sorted(nodes.items()):
        root = ab['a'][3][1]
        times = []
        for side in 'ab':
            src = ab[side][3][0]
            times.append((arrivals.get(src, 0) if k[0] else 0) + h(src, root))
            wire += abs(xy[src][0]-xy[root][0])+abs(xy[src][1]-xy[root][1])
        arrivals[root] = max(times)
    return dict(tree_stages=arrivals[root], tree_to_slab_stages=arrivals[root]+h(root,sink),
                tree_wire_um=round(wire,3), root=root)


def candidate(d, pitch=490.0):
    xy = {i['n']: (i['x'] + i['w']/2, i['y'] + i['h']/2) for i in d['insts']}
    trees = blocks(d['buses'])
    sinks = {int(b.split('_')[1]): eps[-1] for b,c,n,eps in d['buses'] if re.fullmatch(r'bword_\d+', b)}
    records, replace = [], {}
    for b, nodes in sorted(trees.items()):
        if len(nodes) != 15 or any(set(ab) != set('ab') for ab in nodes.values()):
            raise ValueError('requires pre-relay 16-leaf trees')
        leaves = ordered_leaves(nodes)
        if any(not s.startswith('t_') for s in leaves):
            raise ValueError('input must be a pre-relay placement')
        best = optimize(leaves, xy, sinks[b], pitch)
        hosts = {(lv,idx): host for lv,idx,host in best.hosts}
        new = {}
        for (lv,idx), ab in nodes.items():
            new[(lv,idx)] = {}
            for side in 'ab':
                bus, cls, bits, eps = ab[side]
                src = eps[0] if lv == 0 else hosts[(lv-1,2*idx+(side=='b'))]
                target = hosts[(lv,idx)]
                replace[bus] = [src,target]
                new[(lv,idx)][side] = (bus,cls,bits,[src,target])
        replace[f'bword_{b}'] = [best.root,sinks[b]]
        records.append(dict(block=b, baseline=score(nodes,xy,sinks[b],pitch),
                            candidate=score(new,xy,sinks[b],pitch), hosts=[list(x) for x in best.hosts],
                            unused=best.unused, ordered_leaves=leaves))
    nd = dict(d, buses=[(b,c,n,replace.get(b,eps)) for b,c,n,eps in d['buses']])
    report = dict(schema='opentallas.qwen.exact-order-tree-hosts.v1',pitch_um=pitch,blocks=records,
                  baseline_max=max(x['baseline']['tree_to_slab_stages'] for x in records),
                  candidate_max=max(x['candidate']['tree_to_slab_stages'] for x in records),
                  claim='placement lower bound only; no routed pin/relay/cut/timing qualification')
    return nd, report


def apply(v, m, pitch=490.0):
    """Die-generator hook, before any relay, pin freeze, straps or clock trees.

    Real endpoint port names survive the host remap. ROM tile_id is deliberately
    untouched. The unused physical tile changes to the existing node-less master;
    it still produces its leaf t_out. The manifest is the compiler/array mapping.
    """
    d = dict(insts=[dict(n=i.name,m=i.master,x=i.x,y=i.y,w=i.w,h=i.h) for i in m['insts']],
             buses=[(b,c,n,[i for i,p in eps]) for b,c,n,eps in m['buses']])
    _, report = candidate(d,pitch)
    original = blocks(m['buses'])
    replacements, used, unused = {}, set(), set()
    for rec in report['blocks']:
        b=rec['block'];nodes=original[b]
        hosts={(lv,idx):host for lv,idx,host in rec['hosts']}
        used.update(hosts.values());unused.add(rec['unused'])
        for (lv,idx),ab in nodes.items():
            for side in 'ab':
                bid,cls,n,eps=ab[side]
                src=eps[0] if lv==0 else (hosts[(lv-1,2*idx+(side=='b'))],'n_y')
                replacements[bid]=[src,(hosts[(lv,idx)],'n_'+side)]
        bw=f'bword_{b}'
        old=next(eps for bid,c,n,eps in m['buses'] if bid==bw)
        replacements[bw]=[(hosts[(3,0)],'n_y'),old[-1]]
    m['buses']=[(b,c,n,replacements.get(b,eps)) for b,c,n,eps in m['buses']]
    for i in m['insts']:
        if i.name in used: i.master='qfd_tile_nk'
        elif i.name in unused: i.master='qfd_tile_nl'
    m['tree_host_manifest']=report
    return report


def main():
    ap=argparse.ArgumentParser();ap.add_argument('placement',type=Path);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--pitch',type=float,default=490.0);a=ap.parse_args()
    d=json.loads(a.placement.read_text());nd,report=candidate(d,a.pitch)
    report['source_sha256']=hashlib.sha256(a.placement.read_bytes()).hexdigest()
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'tree_hosts.json').write_text(json.dumps(report,indent=2)+'\n')
    (a.out/'placement.json').write_text(json.dumps(nd)+'\n')
    print(json.dumps({k:report[k] for k in ('baseline_max','candidate_max','claim')}))


if __name__=='__main__': main()
