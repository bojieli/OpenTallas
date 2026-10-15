#!/usr/bin/env python3
"""Die-bus audit, ME array arrival model (compute-die lead r2, 2026-10-14): the reference ot_qwen_me_array_w12 runs every
tile in lockstep (one BD for all tiles, one NWS per tree level, one TWS for all block words).  On the die each tile
sees go after its own head + corridor stages, and each tree leg / block word has its own relay stage count.  This tool
reads a build's rom_tp8b.json (relay chains = bus base name + '__r<k>' hops) and reports, per node, the arrival skew of
its two legs (leg a = own / near, leg b = the other: the reference node takes valid from leg a only, so any skew is a
wrong sum unless padded) and the block-word arrival spread at the slabs (BW FIFO depth 4).

    python3 tools/qwen_split/tree_skew.py OUT/rom_tp8b.json [--json OUT.json]
"""
import argparse, collections, json, re


def arrival_pads(S, ends, bword_slab=True):
    """S: bus base name -> register stages (hops); ends: bus -> (source inst, sink inst) of the ORIGINAL bus.
    -> (pads {bus: extra stages at the sink end}, report).  Node legs are padded so both legs of every node arrive on
    the same cycle (level by level, padding moves the node output); block words to the same slab are padded to that
    slab's latest arrival (the slab's 4-deep BW FIFO then sees no skew)."""
    head = {}
    hb = sorted((k for k in S if re.fullmatch(r'head_\d+', k)), key=lambda k: int(k.split('_')[1]))
    cols = len(hb); half = cols // 2
    for c in range(cols):
        rng = range(half - 1, c - 1, -1) if c < half else range(half, c + 1)
        head[c] = sum(S.get(f'head_{q}', 1) for q in rng)
    rows = 1 + max(int(k.split('_')[2]) for k in S if re.fullmatch(r'cor_\d+_\d+', k))
    G = {}
    for c in range(cols):
        for r in range(rows):
            rng = range(rows // 2 - 1, r - 1, -1) if r < rows // 2 else range(rows // 2, r + 1)
            G[(c, r)] = head[c] + sum(S.get(f'cor_{c}_{q}', 1) for q in rng) + S.get(f'tap_{c}_{r}', 1)
    tile = lambda n: tuple(int(q) for q in n.split('_')[1:3])
    legs = collections.defaultdict(dict)
    for k in S:
        mm = re.fullmatch(r'tree_(\d+)_(\d)_(\d+)([ab])', k)
        if mm:
            legs[(int(mm.group(1)), int(mm.group(2)), int(mm.group(3)))][mm.group(4)] = k
    pads, out_t, skews = {}, {}, []
    for lvl in range(0, 8):
        for (blk, l, idx), ab in sorted(legs.items()):
            if l != lvl:
                continue
            arr = {}
            for side, bus in ab.items():
                src, dst = tile(ends[bus][0]), tile(ends[bus][1])
                t0 = G[src] if l == 0 else out_t.get((blk, l - 1, src), G[src])
                arr[side] = (t0 + S[bus], dst, bus)
            t_max = max(q[0] for q in arr.values())
            if len(arr) == 2:
                skews.append(abs(arr['a'][0] - arr['b'][0]))
            for side, (t_, dst, bus) in arr.items():
                if t_ < t_max:
                    pads[bus] = t_max - t_
            out_t[(blk, l, next(iter(arr.values()))[1])] = t_max
    bw = {}
    for k in S:
        if re.fullmatch(r'bword_\d+', k):
            src = tile(ends[k][0])
            lv = max((l for (blk, l, h) in out_t if h == src), default=None)
            t0 = max((t for (blk, l, h), t in out_t.items() if h == src and l == lv), default=G[src])
            bw[k] = (t0 + S[k], ends[k][1])
    slab = collections.defaultdict(list)
    for k, (t_, sl) in bw.items():
        slab[sl].append(t_)
    if bword_slab:
        for k, (t_, sl) in bw.items():
            if t_ < max(slab[sl]):
                pads[k] = max(slab[sl]) - t_
    rep = dict(tiles=len(G), go_min=min(G.values()), go_max=max(G.values()), nodes=len(skews),
               misaligned_nodes=sum(1 for q in skews if q), node_pad_cycles=sum(skews), max_leg_skew=max(skews or [0]),
               bword_spread_per_slab={k: max(v) - min(v) for k, v in slab.items()},
               bword_pad_cycles=sum(max(slab[sl]) - t_ for t_, sl in bw.values()) if bword_slab else 0,
               bword_arrival_max=max(t_ for t_, _ in bw.values()) if bw else None)
    return pads, rep



def from_rom(path):
    """stages and ends of every bus base of a build's rom_tp8b.json (relayed hops: '<base>__r<k>')"""
    d = json.load(open(path))
    S, ends = collections.Counter(), {}
    for b, c, bits, eps in d['buses']:
        base = b.split('__')[0]
        if base.endswith('_rdy'):
            continue
        S[base] += 1
        e = ends.setdefault(base, [None, None])
        if not eps[0].startswith('rly_'):
            e[0] = eps[0]
        if not eps[-1].startswith('rly_'):
            e[1] = eps[-1]
    return S, ends


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('rom'); ap.add_argument('--json'); a = ap.parse_args()
    S, ends = from_rom(a.rom)
    pads, rep = arrival_pads(S, ends)
    rep = dict(source=a.rom, **rep, pads_needed=len(pads), pad_relays=sum(pads.values()))
    print(json.dumps(rep, indent=1))
    if a.json:
        json.dump(dict(rep, pads=pads), open(a.json, 'w'), indent=1)


if __name__ == '__main__':
    main()
