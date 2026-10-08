#!/usr/bin/env python3
"""Qwen ROM die KV landing fabric: reachability and cycle model driven by the MEASURED landing trace.

Input: the KVTRACE landing trace of the STREAM4 CDC service bench (tb_qwen_rt_kv_stream4_cdc.sv, `KVTRACE`,
claude/qwen-kvc-xbar-20261006 e798f4f3a; ISO_P8191, RSEL 1, SYNC 2, RNG 10): one line per accepted landed beat
`cycle first_offered pc n tile0 tile1` (n = 1: a K sector -> one tile; n = 2: a V sector -> two tiles, one 128 b half
each; n = 0: a dropped V beat).  PC p is stack p // 32, pseudo-channel p % 32 (ot_qwen_hbm_stream4_ack genvar stk).

Binding (the die generator's ME tree, tools/qwen_rom_fulldie.py buses()): logical tile i sits in tree block i // 16;
blocks are enumerated column-group outer (c0 = 4 * (nb // 6)), row-group inner (r0 = 4 * (nb % 6)), and the 16 tiles of
a block in morton order.  Stacks 0, 1 land on the west strip (WS, WN), 2, 3 on the east strip (ES, EN).

Modes
  reach  : which stacks every tile needs, and the share of slice writes that a per-stack landing crossbar feeding only
           its own quadrant (die r19: qfd_kvc 12 rows of one half) can deliver.
  sim    : cycle model of a candidate fabric (per-side crossbar over all 24 rows, full-width row buses in one or both
           directions, a FIFO per row, registered one hop a tile plus spine stations).  MODELLED, not RTL: it sizes the
           fabric before the RTL is written (AGENTS design method 1); the RTL bench measures the selected one.
"""
import argparse
import gzip
import json
import math
from collections import Counter, defaultdict, deque
from pathlib import Path

COLS, ROWS, NT = 64, 24, 1536
K_BITS = 256 + 6 + 6 + 2 + 1 + 10      # data + tile column + slice word + quarter + tail + SECDED(271) = 281
V_BITS = 128 + 6 + 6 + 2 + 1 + 9       # 128 b half + the same control + SECDED(143) = 152


def morton(c, r):
    z = 0
    for i in range(4):
        z |= ((c >> i) & 1) << (2 * i) | ((r >> i) & 1) << (2 * i + 1)
    return z


def placement():
    pos, nb = {}, 0
    for c0 in range(0, COLS, 4):
        for r0 in range(0, ROWS, 4):
            tiles = sorted(((c, r) for c in range(c0, c0 + 4) for r in range(r0, r0 + 4)),
                           key=lambda t: morton(t[0] - c0, t[1] - r0))
            for k, t in enumerate(tiles):
                pos[nb * 16 + k] = t
            nb += 1
    return pos


# option M binding: each quadrant (8 block columns x 3 bands) hosts one V block pair-set (V halves of a sector land in
# blocks nb and nb + 8 of one 16-block set) and 8 K-only blocks: WS {0-15, 64-71}, WN {16-31, 72-79},
# ES {32-47, 80-87}, EN {48-63, 88-95}; inside a quadrant the blocks fill its slots column-group outer, band inner.
QUAD_BLOCKS = dict(WS=list(range(0, 16)) + list(range(64, 72)), WN=list(range(16, 32)) + list(range(72, 80)),
                   ES=list(range(32, 48)) + list(range(80, 88)), EN=list(range(48, 64)) + list(range(88, 96)))


def placement_m():
    pos = {}
    for qd, blocks in QUAD_BLOCKS.items():
        cg0 = 0 if qd[0] == 'W' else 8
        b0 = 0 if qd[1] == 'S' else 3
        slots = [(cg0 + cg, b0 + band) for cg in range(8) for band in range(3)]
        for nb, (cg, band) in zip(blocks, slots):
            c0, r0 = 4 * cg, 4 * band
            tiles = sorted(((c, r) for c in range(c0, c0 + 4) for r in range(r0, r0 + 4)),
                           key=lambda t: morton(t[0] - c0, t[1] - r0))
            for k, t in enumerate(tiles):
                pos[nb * 16 + k] = t
    assert len(pos) == NT
    return pos


def quadrant(c, r):
    return ('W' if c < 32 else 'E') + ('S' if r < 12 else 'N')


def load(path):
    op = gzip.open if str(path).endswith('.gz') else open
    beats = []
    with op(path, 'rt') as f:
        for ln in f:
            cy, fo, p, n, t0, t1 = map(int, ln.split())
            beats.append((cy, fo, p, n, [t0, t1][:max(n, 0)]))
    return beats


def stack_side(s):
    return 'W' if s < 2 else 'E'


def reach(beats, pos):
    need = defaultdict(Counter)
    loc = Counter()
    bits_side = Counter()
    rowhalf = Counter()
    for cy, fo, p, n, ts in beats:
        s = p // 32
        for t in ts:
            c, r = pos[t]
            side = 'W' if c < 32 else 'E'
            half = 'S' if r < 12 else 'N'
            need[t][s] += 1
            ss = stack_side(s)
            hs = 'S' if s % 2 == 0 else 'N'
            loc['same_quadrant' if (ss, hs) == (side, half) else 'same_side' if ss == side else 'cross_side'] += 1
            b = K_BITS if n == 1 else V_BITS
            bits_side[side] += b
            rowhalf[(side, r)] += b
    tot = sum(loc.values())
    span = max(b[0] for b in beats) - min(b[0] for b in beats) + 1
    return dict(
        slice_writes=tot,
        stacks_per_tile=dict(Counter(len(v) for v in need.values())),
        stack_sets=dict(Counter(','.join(map(str, sorted(v))) for v in need.values())),
        tiles_per_stack={s: sum(1 for v in need.values() if s in v) for s in range(4)},
        locality={k: round(v / tot, 4) for k, v in loc.items()},
        per_stack_quadrant_crossbar_deliverable=round(loc['same_quadrant'] / tot, 4),
        side_bit_share={k: round(v / sum(bits_side.values()), 4) for k, v in bits_side.items()},
        landing_span_cycles=span,
        row_half_bits_max=max(rowhalf.values()), row_half_bits_min=min(rowhalf.values()),
        row_half_cycles_at_768_max=round(max(rowhalf.values()) / 768, 1),
    )


def sim(beats, pos, width, dirs, ins, spine, depth, per_tile_beat=64, quad=False):
    """Cycle model.  dirs = 'both': the west crossbar drives row buses W->E over all 64 tiles, the east crossbar
    E->W; 'own': a crossbar drives only its own side's rows (cross-side words impossible -> counted).  A PC's beats
    are offered in order from their measured first-offered cycle; a beat is admitted when every half finds room in its
    row FIFO (depth words) and the row has insert slots left this cycle (ins words / row / cycle).  A row bus takes
    words from its FIFO head while they fit in `width` bits, at most per_tile_beat words for one tile.  Arrival =
    issue + hops (one per tile column, + spine stations when crossing the spine); each tile then writes its KV slice
    one word a cycle in arrival order (no merging of halves: pessimistic against the land merge)."""
    t0 = min(b[0] for b in beats)
    pcq = defaultdict(deque)
    for cy, fo, p, n, ts in beats:
        if n == 0:
            continue
        b = K_BITS if n == 1 else V_BITS
        halves = []
        qs = {quadrant(*pos[t]) for t in ts}
        if quad:
            # option M: the sector is striped to the stack of its destination quadrant (PC = p % 32 there)
            assert len(qs) == 1, 'a V sector straddles two quadrants'
            p = 32 * ['WS', 'WN', 'ES', 'EN'].index(qs.pop()) + p % 32
        for t in ts:
            c, r = pos[t]
            side_of_stack = stack_side(p // 32)
            halves.append((side_of_stack, r, c, b))
        pcq[p].append((fo - t0, halves))
    for p in pcq:
        pcq[p] = deque(sorted(pcq[p], key=lambda x: x[0]))
    fifo = defaultdict(deque)
    pend = sum(len(q) for q in pcq.values())
    cyc, last_deliv, maxocc, stalls = 0, 0, Counter(), 0
    bus_bits = Counter()
    unreach = 0
    tq = defaultdict(list)
    while pend or any(fifo.values()):
        used = Counter()
        room = {}
        for p, q in pcq.items():
            if not q or q[0][0] > cyc:
                continue
            halves = q[0][1]
            want = Counter((h[0], h[1]) for h in halves)
            ok = all(len(fifo[k]) + used[k] + w <= depth and used[k] + w <= ins for k, w in want.items())
            if dirs == 'own' and any((h[2] < 32) != (h[0] == 'W') for h in halves):
                unreach += 1
                q.popleft()
                pend -= 1
                continue
            if ok:
                for h in halves:
                    k = (h[0], h[1])
                    fifo[k].append((h[2], h[3]))
                    used[k] += 1
                q.popleft()
                pend -= 1
            else:
                stalls += 1
        for k, f in fifo.items():
            maxocc[k] = max(maxocc[k], len(f))
            bits, seen = 0, Counter()
            while f and bits + f[0][1] <= width and seen[f[0][0]] < per_tile_beat:
                c, b = f.popleft()
                bits += b
                seen[c] += 1
                side = k[0]
                hops = (c + 1) if side == 'W' else (COLS - c)
                cross = (side == 'W' and c >= 32) or (side == 'E' and c < 32)
                arr = cyc + hops + (spine if cross else 0)
                tq[(k[1], c)].append(arr)
            bus_bits[k] += bits
        cyc += 1
        if cyc > 200000:
            raise RuntimeError('no progress')
    for t, arrs in tq.items():
        w = -1
        for x in sorted(arrs):
            w = max(w + 1, x)
        last_deliv = max(last_deliv, w)
    span = max(b[0] for b in beats) - t0 + 1
    busiest = max(bus_bits.values())
    return dict(binding='option_M' if quad else 'natural', width=width, dirs=dirs, inserts_per_row=ins, fifo_depth=depth, spine_stations=spine,
                measured_landing_span=span, admit_end=cyc, fill_end=last_deliv + 1,
                added_cycles=last_deliv + 1 - span, pc_stall_cycles=stalls,
                max_fifo_occupancy=max(maxocc.values()), unreachable_beats=unreach,
                busiest_row_bus_util=round(busiest / width / cyc, 3))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['reach', 'sim', 'sweep'])
    ap.add_argument('--quad', action='store_true', help='option M: quadrant-local stripe + QUAD_BLOCKS binding')
    ap.add_argument('--trace', type=Path, required=True)
    ap.add_argument('--width', type=int, default=768)
    ap.add_argument('--dirs', default='both', choices=['both', 'own'])
    ap.add_argument('--ins', type=int, default=4)
    ap.add_argument('--depth', type=int, default=64)
    ap.add_argument('--spine', type=int, default=5)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args(argv)
    beats, pos = load(a.trace), placement()
    if a.mode == 'reach':
        rec = reach(beats, pos)
    elif a.mode == 'sim':
        rec = sim(beats, placement_m() if a.quad else pos, a.width, 'own' if a.quad else a.dirs, a.ins, a.spine,
                  a.depth, quad=a.quad)
    else:
        rec = dict(reach=reach(beats, pos), sweep=[sim(beats, pos, w, 'both', i, a.spine, d)
                                                    for w in (512, 768, 1024) for i in (2, 4) for d in (16, 64)])
    rec = dict(schema='opentallas.qwen_kv_landing_fabric.v1', trace=str(a.trace), mode=a.mode,
               k_bits=K_BITS, v_half_bits=V_BITS, result=rec)
    if a.out:
        a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(rec, indent=1))


if __name__ == '__main__':
    main()
