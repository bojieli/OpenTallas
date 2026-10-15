#!/usr/bin/env python3
"""Registered reset tree plan for a Qwen die case (owner 2026-10-13: register -> wire <= 500 um -> register).

Reads a generated case (elements.lef, place.tcl, die.v) exactly as tools/hier_contract/pinreg_audit.py does (pin = centroid
of the pin's rectangles; a net's length = half perimeter of its pin bounding box) and, for every reset net longer than the
reach, builds a tree of reset repeaters on a lattice: one leaf repeater per lattice cell that holds sinks, trunks x-first
from the driver's cell, collinear single-child nodes removed while every net stays within the reach, and a node whose
children do not fit one net gets a second registered output (the repeater master has two output flops).  Every net of the
result is checked against the reach.  PLAN ONLY: sites are lattice points, not legalised against the placement.
"""
import argparse, collections, json, re
from pathlib import Path


def load(case):
    D = Path(case)
    size, pins, cur, pin = {}, collections.defaultdict(dict), None, None
    for lef in sorted(D.glob('*.lef')):
        for ln in open(lef):
            s = ln.strip()
            if s.startswith('MACRO '):
                cur, pin = s.split()[1], None
            elif s.startswith('SIZE') and cur not in size:
                t = s.split(); size[cur] = (float(t[1]), float(t[3]))
            elif s.startswith('PIN '):
                pin = s.split()[1]
            elif pin and s.startswith('RECT'):
                t = s.split()
                d = pins[cur].setdefault(re.sub(r'\[\d+\]$', '', pin), [0.0, 0.0, 0])
                d[0] += (float(t[1]) + float(t[3])) / 2; d[1] += (float(t[2]) + float(t[4])) / 2; d[2] += 1
                pin = None
    pos = {}
    for ln in open(D / 'place.tcl'):
        m = re.search(r'findInst (\S+)\]\s+([\d.]+)\s+([\d.]+)\s+(\w+)', ln)
        if m:
            pos[m.group(1)] = (float(m.group(2)), float(m.group(3)), m.group(4))
    txt = (D / 'die.v').read_text()
    inst, netpins = {}, collections.defaultdict(list)
    for m in re.finditer(r'^\s+(\w+) (\S+) \((.*?)\);', txt, re.M):
        mst, nm, body = m.groups(); inst[nm] = mst
        for p in re.finditer(r'\.(\w+)\((\S+?)\)', body):
            netpins[p.group(2)].append((nm, p.group(1)))

    def xy(i, p):
        x0, y0, o = pos[i]; w, h = size[inst[i]]; d = pins[inst[i]][p]; px, py = d[0] / d[2], d[1] / d[2]
        return {'R0': (x0 + px, y0 + py), 'MX': (x0 + px, y0 + h - py), 'MY': (x0 + w - px, y0 + py),
                'R180': (x0 + w - px, y0 + h - py)}[o]
    return inst, netpins, xy


def hp(pts):
    return max(p[0] for p in pts) - min(p[0] for p in pts) + max(p[1] for p in pts) - min(p[1] for p in pts)


def tree(pts, P, reach):
    """pts[0] = driver.  Returns (nodes {cell: parent}, nets [(points)], depth of each leaf cell)."""
    c = lambda p: (int(p[0] // P), int(p[1] // P)); ctr = lambda k: ((k[0] + .5) * P, (k[1] + .5) * P)
    root = c(pts[0]); leaves = collections.defaultdict(list)
    for p in pts[1:]:
        leaves[c(p)].append(p)
    par = {root: None}
    for k in sorted(leaves, key=lambda k: abs(k[0] - root[0]) + abs(k[1] - root[1])):
        path, x, y = [], root[0], root[1]
        while x != k[0]:
            x += 1 if k[0] > x else -1; path.append((x, y))
        while y != k[1]:
            y += 1 if k[1] > y else -1; path.append((x, y))
        prev = root
        for q in path:
            par.setdefault(q, prev); prev = q
    kids = collections.defaultdict(list)
    for k, p in par.items():
        if p is not None:
            kids[p].append(k)
    for k in list(par):                     # drop collinear single-child pass-through nodes while the net still fits
        p = par.get(k)
        if p is None or k in leaves or len(kids[k]) != 1:
            continue
        ch = kids[k][0]
        if hp([ctr(p), ctr(ch)] + [ctr(o) for o in kids[p] if o != k]) <= reach - 20 and len(kids[p]) == 1:
            kids[p] = [ch]; par[ch] = p; del par[k]; del kids[k]
    nets, outs = [], collections.Counter()
    for k in par:
        src = ctr(k)                         # the root cell holds a repeater too: driver pin -> its cell centre is one net
        if k == root:
            nets.append([pts[0], src])
        grp = [[]]
        for ch in kids.get(k, []):
            for g in grp:
                if hp([src] + [ctr(o) for o in g] + [ctr(ch)]) <= reach - 20:
                    g.append(ch); break
            else:
                grp.append([ch])
        if k in leaves:
            for s in leaves[k]:
                for g in grp:
                    if hp([src] + [ctr(o) for o in g if isinstance(o[0], int)] + [o for o in g if not isinstance(o[0], int)] + [s]) <= reach - 20:
                        g.append(s); break
                else:
                    grp.append([s])
        for g in grp:
            if g:
                nets.append([src] + [ctr(o) if isinstance(o[0], int) else o for o in g]); outs[k] += 1
    dep = {}
    def d(k):
        if k not in dep:
            dep[k] = 1 if par[k] is None else d(par[k]) + 1
        return dep[k]
    return par, nets, {k: d(k) for k in leaves}, outs, root


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--case', required=True); ap.add_argument('--pitch', type=float, default=240.0)
    ap.add_argument('--reach', type=float, default=500.0); ap.add_argument('--out', required=True)
    ap.add_argument('--driver-ports', default=r'rso|hrst$|crst$', help='regex of the ports that drive a reset net')
    a = ap.parse_args()
    inst, netpins, xy = load(a.case)
    rows = []
    for n, ps in sorted(netpins.items()):
        if not re.match(r'n_rst|n_arst|.*_rst_', n) or len(ps) < 2:
            continue
        ps = sorted(ps, key=lambda e: not re.match(a.driver_ports, e[1]))    # the driver first (die.v lists pins in instance order)
        pts = [xy(i, p) for i, p in ps]
        if hp(pts) <= a.reach:
            continue
        par, nets, dep, outs, root = tree(pts, a.pitch, a.reach)
        rows.append(dict(net=n, driver='.'.join(ps[0]), driver_master=inst[ps[0][0]], sinks=len(ps) - 1,
                         sink_ports=dict(collections.Counter(f'{inst[i]}.{p}' for i, p in ps[1:])),
                         hpwl_um=round(hp(pts), 1), repeaters=len(par),
                         two_output_repeaters=sum(1 for v in outs.values() if v == 2), max_outputs=max(outs.values()),
                         nets=len(nets), max_net_um=round(max(hp(g) for g in nets), 1), min_leaf_depth=min(dep.values()),
                         depth_cycles=max(dep.values()),
                         sites=[[round((k[0] + .5) * a.pitch, 2), round((k[1] + .5) * a.pitch, 2)] for k in par]))
    out = dict(schema='qwen_tp8_reset_tree_plan_v1', case=a.case, pitch_um=a.pitch, reach_um=a.reach, status='PLAN_ONLY',
               nets=rows, total_repeaters=sum(r['repeaters'] for r in rows), max_depth_cycles=max(r['depth_cycles'] for r in rows),
               all_nets_within_reach=all(r['max_net_um'] <= a.reach for r in rows))
    Path(a.out).write_text(json.dumps(out, indent=1))
    for r in rows:
        print(r['net'], r['driver'], 'sinks', r['sinks'], 'hpwl', r['hpwl_um'], 'rep', r['repeaters'], 'nets', r['nets'], 'maxnet', r['max_net_um'],
              'depth', r['min_leaf_depth'], '-', r['depth_cycles'], 'maxouts', r['max_outputs'], r['sink_ports'])
    print('total', out['total_repeaters'], 'max depth', out['max_depth_cycles'], 'ok', out['all_nets_within_reach'])


if __name__ == '__main__':
    main()
