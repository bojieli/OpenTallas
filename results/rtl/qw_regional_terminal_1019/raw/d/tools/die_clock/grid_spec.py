#!/usr/bin/env python3
"""DIE-CLOCK: neighbour-relative region spec for build.py (owner 2026-10-16) from a grid of region cuts.

  grid_spec.py --die-w W --die-h H --xcuts 14970,18831 --ycuts 6300,12600,18900 \\
      --family core=hb_ckgen/pll_serial:1111.111,hb_ckgen/pll_stream:833.333 --family hbm=hb_ckgen/pll_hbm:1024 \\
      [--clknets geom/clknets.tsv] [--exclude-master-prefix hbfd_rly] [--unclaimed disconnect_diagnostic] \\
      [--budget 60] [--die NAME] --out spec.json

Regions are the grid cells (named <family>_<col><row>, col W..E as c0.., row S..N as r0..).
- A region holds one tree per root of its family, with sinks inside the cell, all in one balance_group, i.e. matched
  inside the region.
- Neighbours are the 8-connected grid cells of the same family. Each communicating neighbour pair is held within the
  budget by build.py.
- Families never constrain each other: async / CDC / meso.
- With --clknets (die_clock_geom_dump.py output), only the (root, cell) trees that actually have sinks are emitted.
  Neighbour pairs are kept only between cells that both have sinks.
"""
import argparse, json
from collections import defaultdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--die-w', type=float, required=True)
    ap.add_argument('--die-h', type=float, required=True)
    ap.add_argument('--xcuts', default='')
    ap.add_argument('--ycuts', default='')
    ap.add_argument('--family', action='append', required=True, help='name=root:period,root:period')
    ap.add_argument('--clknets')
    ap.add_argument('--exclude-master-prefix', action='append', default=[])
    ap.add_argument('--unclaimed')
    ap.add_argument('--budget', type=float, default=60.0)
    ap.add_argument('--die', default='die')
    ap.add_argument('--rc-layer', default='M8')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    xs = [0.0] + [float(v) for v in a.xcuts.split(',') if v] + [a.die_w + 1]
    ys = [0.0] + [float(v) for v in a.ycuts.split(',') if v] + [a.die_h + 1]
    cell = lambda x, y: (max(i for i in range(len(xs) - 1) if x >= xs[i]), max(j for j in range(len(ys) - 1) if y >= ys[j]))
    fams = {}
    for f in a.family:
        name, rs = f.split('=', 1)
        fams[name] = [(r.rsplit(':', 1)[0], float(r.rsplit(':', 1)[1])) for r in rs.split(',')]
    have = None
    if a.clknets:
        have = defaultdict(int)
        for ln in open(a.clknets):
            f = ln.rstrip('\n').split('\t')
            if len(f) < 5 or any(f[2].startswith(p) for p in a.exclude_master_prefix):
                continue
            have[(f[0], cell(float(f[3]), float(f[4])))] += 1
    trees, occupied = [], defaultdict(set)
    for fam, roots in fams.items():
        for i in range(len(xs) - 1):
            for j in range(len(ys) - 1):
                reg = f'{fam}_c{i}r{j}'
                for root, per in roots:
                    if have is not None and not have.get((root, (i, j))) and not have.get((root + '[0]', (i, j))):
                        continue
                    sel = {'bbox': [xs[i], ys[j], xs[i + 1], ys[j + 1]]}
                    if a.exclude_master_prefix:
                        sel['exclude_master_prefix'] = a.exclude_master_prefix
                    trees.append({'name': f'{reg}_{root.split("/")[-1].replace("[0]", "")}', 'root': root,
                                  'period': per, 'select': sel, 'balance_group': reg})
                    occupied[fam].add((i, j))
    nb = []
    for fam, cells in occupied.items():
        for (i, j) in sorted(cells):
            for di, dj in ((1, 0), (0, 1), (1, 1), (1, -1)):
                o = (i + di, j + dj)
                if o in cells:
                    nb.append([f'{fam}_c{i}r{j}', f'{fam}_c{o[0]}r{o[1]}'])
    spec = dict(die=a.die, rc_layer=a.rc_layer, leaf_um=60, leaf_max=12, trees=trees, neighbours=nb,
                neighbour_budget_ps=a.budget)
    if a.unclaimed:
        spec['unclaimed'] = a.unclaimed
    json.dump(spec, open(a.out, 'w'), indent=1)
    print(len(trees), 'trees', sum(len(c) for c in occupied.values()), 'regions', len(nb), 'neighbour pairs')


if __name__ == '__main__':
    main()
