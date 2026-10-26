#!/usr/bin/env python3
"""S81-DIE7/FRAME 10-18: landed-region sizing of the _l4 frame masters (col_h9_l4 / col_h10_l4) before any frame
cluster kit (landed-regions standard: a hardened parent > ~1 mm = local region trees + every region crossing LANDED).

Placement source: the only frame floorplan that exists, the c26l GEN column cluster (frame_wrap.py's vendored extract,
results/arch/s81_dv_1016/frame/src: box_um per child, 1,135 um wide = compact199 ot_v41_bf_col).  Frame-local names come
from frame_wrap.local_names; children frame_wrap / frame_l4 added (r1-skew relays, xo stations) take the mean y of
their netlist neighbours.  For every horizontal cut y the tool counts the signal bits of the _l4 RTL with child pins on
both sides (clock pins excluded), classified by the child masters a net touches, and picks the min-cut slot
boundaries for R regions (each <= --max-region-um tall).  Landing cost = bits x (D + 1) flops (ot_pl_land ring D slots +
read register) and +E+1 edges per landing on that path (LANDING-CONTRACT; D 4, E 2).
Pure netlist arithmetic (no sim / synth).  Writes --out JSON.

  frame_regions.py [--regions 3] [--max-region-um 1100] [--out results/arch/s81_dv_1016/frame_l4_cluster/regions.json]
"""
import argparse
import collections
import gzip
import hashlib
import itertools
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import frame_wrap as FW  # noqa: E402

CLOCK_PINS = {'ck', 'clk', 'cr', 'cr_s'}
D, E = 4, 2


def klass(masters):
    if any(m.startswith(('ot_s81_sstn', 'dsfd_rly_536', 'dsfd_rly_266', 'dsfd_rly_283', 'dsfd_dvrly_276')) for m in masters):
        return 'x_chain'
    if any(m.startswith(('dsfd_node', 'dsfd_rly_63')) for m in masters):
        return 'return_tree'
    if any(m.startswith(('ot_s81_cfg7', 'dsfd_rly_54', 'dsfd_rly_38', 'dsfd_rly_15')) for m in masters):
        return 'cfg'
    if any(m.startswith('dsfd_rstg') for m in masters):
        return 'reset'
    return 'other'


def frame(master, l4dir):
    fn, mod, slots, nq, nbf = FW.CLASSES[master]
    text = gzip.decompress((FW.SRC / fn).read_bytes()).decode()
    _, insts = FW.parse_column(text, mod)
    cl = json.loads(gzip.decompress((FW.SRC / 'c26l_sel_clusters.json.gz').read_bytes()))
    cluster = next(c for c in cl['clusters'] if c['master'] == mod)
    names, _ = FW.local_names(cluster['children'], insts)
    box = {c['instance']: c['box_um'] for c in cluster['children']}
    pos = {names[i['name']]: box[i['name']] for i in insts if i['name'] in box}
    rtl = l4dir / f'{master}_l4.sv'
    s = rtl.read_text()
    body = s[s.index(');') + 2:]
    inst_re = re.compile(r"^    ([a-z]\w*)\s*(?:#\((?:[^()]|\([^()]*\))*\))?\s*(u_\w+)\s*\((.*?)\);\s*$", re.M | re.S)
    nets, kids = collections.defaultdict(set), {}
    for m in inst_re.finditer(body):
        mst, inst, conns = m.groups()
        kids[inst] = mst
        for pin, expr in re.findall(r"\.(\w+)\s*\(((?:[^()]|\([^()]*\))*)\)", conns):
            if pin in CLOCK_PINS:
                continue
            for n in re.findall(r"\b(n\d+|(?:x|xo|ret|xk|xok|lk)\[\d+\]|rst_n)", expr):
                nets[n].add(inst)
    yc = {k: v[1] + v[3] / 2 for k, v in pos.items() if k in kids}
    nb = collections.defaultdict(set)
    for ks in nets.values():
        if len(ks) < 40:
            for a in ks:
                nb[a] |= ks - {a}
    added = [k for k in kids if k not in yc]
    for _ in range(6):
        for k in kids:
            if k not in yc:
                ys = [yc[o] for o in nb[k] if o in yc]
                if ys:
                    yc[k] = statistics.mean(ys)
    H = max(v[1] + v[3] for v in pos.values())
    span = {n: (min(yc[k] for k in ks), max(yc[k] for k in ks), klass({kids[k] for k in ks})) for n, ks in nets.items()}

    def cut(y):
        c = collections.Counter(cl for lo, hi, cl in span.values() if lo < y < hi)
        return dict(total=sum(c.values()), **dict(sorted(c.items())))
    elem_y = sorted(round(yc[k]) for k in kids if kids[k] == 'ot_v41_rom_elem_q_qxpq_w10')
    prof = {y: cut(y)['total'] for y in range(50, int(H), 25)}
    return dict(rtl=str(rtl.relative_to(ROOT)), rtl_sha256=hashlib.sha256(s.encode()).hexdigest(), insts=len(kids),
                masters=len(set(kids.values())), nets=len(nets), placed_c26l=len(pos), placed_by_neighbours=len(added),
                c26l_extent_um=[1135.3, round(H, 1)], elem_y_um=elem_y, cut_profile=prof), cut, H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--regions', type=int, default=3)
    ap.add_argument('--max-region-um', type=float, default=1100.0)
    ap.add_argument('--l4dir', default=str(ROOT / 'rtl/dsrom_sys/s81_dv/frame_l4'))
    ap.add_argument('--out', default=str(ROOT / 'results/arch/s81_dv_1016/frame_l4_cluster/regions.json'))
    a = ap.parse_args()
    rec = dict(schema='opentallas.s81_dv.frame_regions.v1', D=D, E=E,
               note='c26l GEN placement (1,135 um wide, compact199 bf_col); NOT the p4 plan width 1,436.832 (S-ELEM bf_col_cl)',
               masters={})
    for master in ('col_h9', 'col_h10'):
        r, cut, H = frame(master, Path(a.l4dir))
        ys = [y for y in r['cut_profile'] if 150 < y < H - 150]
        best = None
        for cuts in itertools.combinations(ys, a.regions - 1):
            edges = [0.0, *cuts, H]
            if max(b - t for t, b in zip(edges, edges[1:])) > a.max_region_um:
                continue
            bits = sum(r['cut_profile'][y] for y in cuts)
            if best is None or bits < best[0]:
                best = (bits, cuts)
        bits, cuts = best
        r['plan'] = dict(regions=a.regions, cuts_um=list(cuts), cut_bits=[cut(y) for y in cuts], landed_bits=bits,
                         landing_flops=bits * (D + 1), edges_per_landing=E + 1,
                         deepest_slot_added_edges_each_way=(E + 1) * (a.regions - 1))
        rec['masters'][master] = r
        print(master, r['insts'], 'children', r['nets'], 'nets; cuts', cuts, [c['total'] for c in r['plan']['cut_bits']],
              'landed bits', bits, 'flops', bits * (D + 1))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rec, indent=1) + '\n')


if __name__ == '__main__':
    main()
