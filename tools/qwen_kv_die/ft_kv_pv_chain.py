#!/usr/bin/env python3
"""FT-KV 10-23 (coordinator: PV broadcast redesign): the V-port -> PV-slice broadcast as a registered chain THROUGH the
PV pair arrays, re-driven locally per block row, instead of one wide bus per sink over the top.  Census rewrite for
tools/die_feedthrough/plan.py, so the track demand before/after is measured with the same tool.

The RTL fan-out (rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv): V port k's word = eight 128-b chunks + 16-b epoch per
head; column s (head H = s/8, dim group GS = s%8) takes chunk GS of every port into banks l = k and l = k^4.  On the die
column s sits in block row 2*GS + (s//16) of its pair (left block s < 8 or 16 <= s < 24, right block otherwise): group GS = block rows
2GS, 2GS+1, so chunk g of a port is needed only in rows 2g, 2g+1 (4 columns x 2 banks = 8 slices).

PV-CHAIN structure per port (static, neighbour-only hops, no hub, no backpressure):
  entry   vport.vo -> the station tile of the port's sub-column in the block row level with the vport (CHUNK*8 + E bits)
  chain   station(row r) -> station(row r +- 1): registered ft through the array (one station per block row, 734-um hop
          <= the 1.2-mm reach); a hop carries the chunks of the groups still ahead (128 b each) + the 64-b epoch word
  tap     station(row r) -> the 4 slices of that row taking this port (banks lane, lane ^ 4 of its 2 columns; RTL
          ot_qwen_tp8_pv_col: 128-b chunk + 16-b e each; local re-drive, < 1 mm)
Ports spread over the 6 sub-columns of the pair (W ports on the left block's 3, E ports on the right block's 3), so
the vertical ft load is shared by every tile column of the array.  The old broadcast groups (src_bus vo -> a pv slice)
are dropped; every other census group is kept as is.  Stages of the new groups are reported by plan.py (stages_new);
'stages' (old) is set to 0 for them.
"""
import argparse
import collections
import gzip
import json
import math
import re
from pathlib import Path

CHUNK, EBITS, TAPBITS = 128, 64, 128 + 16
SLICE_RE = re.compile(r'^(pvw_[01])__u_s(\d+)_(b\d|j)$')


def load_insts(dump):
    blocks = {}
    for ln in Path(dump, 'blocks.tsv').read_text().splitlines():
        f = ln.split('\t')
        if len(f) < 6 or f[0] in ('inst', 'name'):
            continue
        try:
            blocks[f[0]] = (f[1], float(f[2]), float(f[3]), float(f[4]), float(f[5]))
        except ValueError:
            continue
    return blocks


def centre(b):
    _, x, y, w, h = b
    return (round(x + w / 2, 3), round(y + h / 2, 3))


def rewrite(cen, blocks):
    groups = cen['groups']
    old = [g for g in groups if g['src_bus'] == 'vo' and SLICE_RE.match(g['dst'])]
    keep = [g for g in groups if not (g['src_bus'] == 'vo' and SLICE_RE.match(g['dst']))]
    # array geometry from the tiles: per pair, column s -> (row, block side, sub-column x list)
    tiles = {n: b for n, b in blocks.items() if SLICE_RE.match(n)}
    pair_rows = collections.defaultdict(dict)     # pair -> row y centre -> list of tiles
    col_of = {}
    for n, b in tiles.items():
        p, s, t = SLICE_RE.match(n).groups()
        col_of[n] = (p, int(s), t)
    cols = collections.defaultdict(list)
    for n, (p, s, t) in col_of.items():
        cols[(p, s)].append(n)
    colc = {k: (sum(centre(tiles[n])[0] for n in v) / len(v), sum(centre(tiles[n])[1] for n in v) / len(v))
            for k, v in cols.items()}
    rows = {}
    for p in ('pvw_0', 'pvw_1'):
        ys = sorted({round(colc[(p, s)][1]) for s in range(32) if (p, s) in colc})
        rows[p] = ys                                  # 16 block-row centres, bottom -> top
    def row_of(p, s):
        return rows[p].index(round(colc[(p, s)][1]))
    def group_of_row(p, r):
        gs = {s % 8 for s in range(32) if (p, s) in colc and row_of(p, s) == r}
        assert len(gs) == 1, (p, r, gs)
        return gs.pop()
    # station tile of (pair, row, side, sub-column j): the tile in that block's middle tile row at sub-column j
    def station(p, r, side, j):
        cand = [n for n, (pp, s, t) in col_of.items() if pp == p and row_of(p, s) == r and ((s % 16) < 8) == (side == 'L')]
        xs = sorted({centre(tiles[n])[0] for n in cand})
        ys = sorted({centre(tiles[n])[1] for n in cand})
        x, y = xs[j], ys[len(ys) // 2]
        return min(cand, key=lambda n: abs(centre(tiles[n])[0] - x) + abs(centre(tiles[n])[1] - y))

    by_port = collections.defaultdict(list)
    for g in old:
        by_port[g['src']].append(g)
    new = []
    stats = dict(ports=len(by_port), old_groups=len(old), old_bits=sum(g['bits'] for g in old))
    for vp in sorted(by_port):
        gs_ = by_port[vp]
        pairs = collections.Counter(col_of[g['dst']][0] for g in gs_)
        p = pairs.most_common(1)[0][0]
        side = 'L' if '_W' in vp else 'R'
        k = int(vp.rsplit('_', 1)[1])
        j = k % 3
        sp = tuple(gs_[0]['src_pt'])
        sinks_by_row = collections.defaultdict(set)
        lane = k % 4                                   # RTL: port lane k feeds banks k and k ^ 4 of every column
        for n, (pp, s, t) in col_of.items():
            if pp == p and t in (f'b{lane}', f'b{lane + 4}'):
                sinks_by_row[row_of(p, s)].add(n)
        r0 = min(range(16), key=lambda r: abs(rows[p][r] - sp[1]))
        need = sorted(sinks_by_row)
        st = {r: station(p, r, side, j) for r in range(16)}

        def grp(src, sbus, dst, dbus, bits, spt, dpt):
            L = abs(spt[0] - dpt[0]) + abs(spt[1] - dpt[1])
            new.append(dict(src=src, src_bus=sbus, dst=dst, dst_bus=dbus, kind='data', bits=int(bits), chains=1,
                            stages=0, stages_min=0, lands=0, nbuf_max=0, cur_um=round(L, 1), straight_um=round(L, 1),
                            detour=1.0, ideal_stages=max(0, math.ceil(L / 1200.0) - 1), route='HV',
                            src_pt=[round(spt[0], 3), round(spt[1], 3)], dst_pt=[round(dpt[0], 3), round(dpt[1], 3)],
                            crosses=[], pv_chain=True))
        grp(vp, 'vo', st[r0], f'ft_{vp}_i', 8 * CHUNK + EBITS, sp, centre(tiles[st[r0]]))
        for direction in (+1, -1):
            r = r0
            while 0 <= r + direction < 16 and any((rr - r) * direction > 0 for rr in need):
                nxt = r + direction
                ahead = {group_of_row(p, rr) for rr in need if (rr - r) * direction > 0}
                grp(st[r], f'ft_{vp}_o', st[nxt], f'ft_{vp}_i', CHUNK * len(ahead) + EBITS,
                    centre(tiles[st[r]]), centre(tiles[st[nxt]]))
                r = nxt
        for r in need:
            for dst in sorted(sinks_by_row[r]):
                if dst != st[r]:
                    grp(st[r], f'ft_{vp}_t', dst, 'pv2', TAPBITS, centre(tiles[st[r]]), centre(tiles[dst]))
    stats.update(new_groups=len(new), new_bits=sum(g['bits'] for g in new))
    cen = dict(cen)
    cen['groups'] = keep + new
    cen.setdefault('summary', {})
    cen['summary'] = dict(cen['summary'], pv_chain=stats)
    return cen, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--census', required=True)
    ap.add_argument('--dump', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    op = gzip.open if a.census.endswith('.gz') else open
    with op(a.census, 'rt') as f:
        cen = json.load(f)
    out, stats = rewrite(cen, load_insts(a.dump))
    with (gzip.open if a.out.endswith('.gz') else open)(a.out, 'wt') as f:
        json.dump(out, f)
    print(json.dumps(stats))


if __name__ == '__main__':
    main()
