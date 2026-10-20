#!/usr/bin/env python3
"""DIE-CLOCK: picture of a physical die clock (look at it every step).

  plot.py MANIFEST ARRIVALS.tsv BLOCKS.tsv OUT.png [--window x0,y0,x1,y1] [--trees a,b] [--title T]
Hard blocks grey; tree edges (parent -> child, straight segments between cell sites) coloured per tree; sinks
coloured by measured flop arrival (pin arrival + R) relative to their tree's target; pads orange.
BLOCKS.tsv = tools/s81/die_clock_geom_dump.py blocks.tsv (inst, master, x0, y0, x1, y1).
"""
import argparse, json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('manifest'); ap.add_argument('arrivals'); ap.add_argument('blocks'); ap.add_argument('out')
    ap.add_argument('--window'); ap.add_argument('--trees'); ap.add_argument('--title', default='')
    a = ap.parse_args()
    rec = json.load(open(a.manifest))
    arr = {}
    for ln in open(a.arrivals):
        f = ln.rstrip('\n').split('\t')
        try:
            arr[f[0]] = float(f[1])
        except ValueError:
            pass
    keep = set(a.trees.split(',')) if a.trees else None
    W = [float(v) for v in a.window.split(',')] if a.window else None
    xy = {c[0]: (c[2], c[3]) for c in rec['cells']}
    for p, s in rec['sinks'].items():
        xy[p] = (s['x'], s['y'])
    for t in rec['trees'].values():
        if 'root_xy' in t:
            xy[t['root']] = tuple(t['root_xy'])
    tree_of = dict(rec.get('cell_tree', {}))
    fig, ax = plt.subplots(figsize=(16, 16 * ((W[3] - W[1]) / (W[2] - W[0]) if W else 26 / 33)))
    polys = []
    for ln in open(a.blocks):
        f = ln.split('\t')
        x0, y0, x1, y1 = map(float, f[2:6])
        if W and (x1 < W[0] or x0 > W[2] or y1 < W[1] or y0 > W[3]):
            continue
        polys.append([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    ax.add_collection(PolyCollection(polys, facecolors='#d9d9d9', edgecolors='#999999', linewidths=0.1))
    cmap = plt.get_cmap('tab10')
    names = sorted(set(tree_of.values()))
    col = {n: cmap(i % 10) for i, n in enumerate(names)}
    segs, cols = [], []
    for ch, pa in rec['parent'].items():
        tn = tree_of.get(ch) or rec['sinks'].get(ch, {}).get('tree')
        if keep and tn not in keep and not any(tn and tn.startswith(k) for k in keep):
            continue
        if ch in xy and pa in xy:
            segs.append([xy[pa], xy[ch]]); cols.append(col.get(tree_of.get(pa, tn), 'k'))
    ax.add_collection(LineCollection(segs, colors=cols, linewidths=0.5))
    pads = [xy[c[0]] for c in rec['cells'] if '_tp' in c[0] or c[1].startswith('BUFx12f')]
    if pads:
        ax.plot([p[0] for p in pads], [p[1] for p in pads], '.', color='orange', ms=1.5)
    T = {}
    for p, s in rec['sinks'].items():
        if p in arr:
            T[s['tree']] = max(T.get(s['tree'], -1e9), arr[p] + s['R'][2])
    xs, ys, cs = [], [], []
    for p, s in rec['sinks'].items():
        if p in arr and (not keep or s['tree'] in keep or any(s['tree'].startswith(k) for k in keep)):
            xs.append(s['x']); ys.append(s['y']); cs.append(arr[p] + s['R'][2] - T[s['tree']])
    sc = ax.scatter(xs, ys, c=cs, cmap='jet', s=8, zorder=5)
    plt.colorbar(sc, ax=ax, fraction=0.03, label='flop arrival - tree target (ps)')
    if W:
        ax.set_xlim(W[0], W[2]); ax.set_ylim(W[1], W[3])
    else:
        ax.autoscale()
    ax.set_aspect('equal')
    ax.set_title(a.title or a.manifest)
    plt.tight_layout(); plt.savefig(a.out, dpi=80)


if __name__ == '__main__':
    main()
