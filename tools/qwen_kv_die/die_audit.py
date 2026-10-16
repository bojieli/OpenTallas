#!/usr/bin/env python3
"""Textbook die-level audit of a generated Qwen ROM die case (qwendie-1011, OWNER 10-11 textbook audit).

Reads <case>/elements.lef, place.tcl, die.v and reports, for the DIE TOP only (hardened elements are black boxes):
  class 1  clock nets: sinks and centre bounding box per net (a region net > REGION_MAX um in either dimension fails);
  class 2  max fanout of non-clock nets;
  class 4  pin-to-pin span (bus pins averaged) of every non-clock net; nets over the 504 um SS reach fail;
  class 6  placed macro area / die area.
usage: die_audit.py <case dir> [--die-w 23484.384 --die-h 32801.76] [--out audit.json] [--reach 504] [--region-max 5250]
"""
import argparse
import collections
import json
import re


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('case')
    ap.add_argument('--die-w', type=float, default=23484.384)
    ap.add_argument('--die-h', type=float, default=32801.76)
    ap.add_argument('--reach', type=float, default=504.0)
    ap.add_argument('--region-max', type=float, default=5250.0)
    ap.add_argument('--out')
    ap.add_argument('--all-hops', help='qwen-tp8: write every hop over reach (um, net, bits, pins) to this JSON')
    a = ap.parse_args()
    D = a.case
    size, pins, cur, pin, lay, shapes = {}, collections.defaultdict(dict), None, None, None, {}
    for ln in open(D + '/elements.lef'):
        s = ln.strip()
        if s.startswith('MACRO '):
            cur, pin = s.split()[1], None
        elif s.startswith('SIZE') and cur not in size:
            t = s.split()
            size[cur] = (float(t[1]), float(t[3]))
        elif s.startswith('PIN '):
            pin = s.split()[1]
        elif pin and s.startswith('LAYER'):
            lay = s.split()[1]
        elif pin and s.startswith('RECT'):
            t = s.split()
            shapes.setdefault(cur, []).append((lay, float(t[1]), float(t[2]), float(t[3]), float(t[4]), pin))
            x, y = (float(t[1]) + float(t[3])) / 2, (float(t[2]) + float(t[4])) / 2
            d = pins[cur].setdefault(re.sub(r'\[\d+\]$', '', pin), [0.0, 0.0, 0])
            d[0] += x; d[1] += y; d[2] += 1
            pin = None
    pos = {}
    for ln in open(D + '/place.tcl'):
        mm = re.search(r'findInst (\S+)\]\s+([\d.]+)\s+([\d.]+)\s+(\w+)', ln)
        if mm:
            pos[mm.group(1)] = (float(mm.group(2)), float(mm.group(3)), mm.group(4))
    inst, netpins, width = {}, collections.defaultdict(list), {}
    txt = open(D + '/die.v').read()
    for mm in re.finditer(r'wire \[(\d+):0\] (\S+);', txt):
        width[mm.group(2)] = int(mm.group(1)) + 1
    for mm in re.finditer(r'^\s+(\w+) (\S+) \((.*?)\);', txt, re.M):
        mst, nm, body = mm.groups()
        inst[nm] = mst
        for p in re.finditer(r'\.(\w+)\((\S+?)\)', body):
            netpins[p.group(2)].append((nm, p.group(1)))

    def pinxy(i, p):
        if i not in pos or inst[i] not in size:
            return None
        x0, y0, o = pos[i]
        w, h = size[inst[i]]
        d = pins[inst[i]].get(p)
        if not d or not d[2]:
            return None
        px, py = d[0] / d[2], d[1] / d[2]
        return {'R0': (x0 + px, y0 + py), 'MX': (x0 + px, y0 + h - py), 'MY': (x0 + w - px, y0 + py),
                'R180': (x0 + w - px, y0 + h - py)}.get(o)

    def ctr(i):
        x, y, _ = pos[i]
        w, h = size[inst[i]]
        return x + w / 2, y + h / 2

    def is_clk(n):
        return n.startswith(('n_clk', 'n_fck', 'n_pll')) or '_clk_' in n

    hops, nopin = [], 0
    for n, ps in netpins.items():
        if is_clk(n) or len(ps) < 2:
            continue
        pts = [pinxy(i, p) for i, p in ps]
        if any(q is None for q in pts):
            nopin += 1
            continue
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        hops.append((round(max(xs) - min(xs) + max(ys) - min(ys), 1), n, width.get(n, 1), len(ps)))
    hops.sort(reverse=True)
    clk = []
    for n, ps in netpins.items():
        if not is_clk(n):
            continue
        # the root (a pll_* output) is excluded from the sink box; its distance to the sink centroid = trunk length
        root = [ctr(i) for i, p in ps if p.startswith('pll_') and i in pos and inst[i] in size]
        pts = [ctr(i) for i, p in ps if not p.startswith('pll_') and i in pos and inst[i] in size]
        if not pts:
            continue
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        tr = round(abs(root[0][0] - cx) + abs(root[0][1] - cy)) if root else 0
        clk.append((round(max(xs) - min(xs)), round(max(ys) - min(ys)), n, len(pts), tr))
    clk.sort(key=lambda c: -max(c[0], c[1]))
    region = [c for c in clk if c[2].startswith('n_clk_r')]
    # pin shapes of DIFFERENT ports overlapping on one layer inside a master (r22ko4 VM rb3-5 clamped to one face end)
    used = set(inst.values())
    pin_ovl = []
    for mst, sh in shapes.items():
        if mst not in used:
            continue
        for ly in {s_[0] for s_ in sh}:
            L = sorted((s_ for s_ in sh if s_[0] == ly), key=lambda s_: s_[1])
            act = []
            for s_ in L:
                act = [a_ for a_ in act if a_[3] > s_[1] + 1e-4]
                for a_ in act:
                    if a_[5] != s_[5] and min(a_[4], s_[4]) - max(a_[2], s_[2]) > 1e-4 and \
                            re.sub(r'\[\d+\]$', '', a_[5]) != re.sub(r'\[\d+\]$', '', s_[5]):
                        pin_ovl.append((mst, ly, a_[5], s_[5]))
                act.append(s_)
    area = sum(size[inst[i]][0] * size[inst[i]][1] for i in inst if inst[i] in size)
    fo = max(((len(p), n) for n, p in netpins.items() if not is_clk(n)), default=(0, ''))
    over = [h for h in hops if h[0] > a.reach]
    if a.all_hops:
        open(a.all_hops, 'w').write(json.dumps(over) + '\n')
    out = dict(case=D, insts=len(inst), nets=len(netpins), nopin_nets=nopin,
               pin_overlaps=len(pin_ovl), pin_overlap_examples=pin_ovl[:10],
               pin_overlaps_by_master=dict(collections.Counter(o_[0] for o_ in pin_ovl)),
               util=round(area / (a.die_w * a.die_h), 4), placed_mm2=round(area / 1e6, 2),
               max_fanout_nonclk=dict(net=fo[1], pins=fo[0]),
               hops_over_reach=dict(reach_um=a.reach, nets=len(over), bits=sum(h[2] for h in over),
                                    worst=[dict(um=h[0], net=h[1], bits=h[2], pins=h[3]) for h in over[:30]]),
               region_nets=len(region),
               region_over_max=sum(max(c[0], c[1]) > a.region_max for c in region),
               region_worst=[dict(net=c[2], bbox_um=[c[0], c[1]], sinks=c[3], trunk_um=c[4]) for c in region[:8]],
               region_trunk_max_um=max((c[4] for c in region), default=0),
               clock_worst=[dict(net=c[2], bbox_um=[c[0], c[1]], sinks=c[3], trunk_um=c[4]) for c in clk[:8]])
    s = json.dumps(out, indent=1)
    if a.out:
        open(a.out, 'w').write(s)
    print(json.dumps({k: out[k] for k in ('util', 'pin_overlaps', 'max_fanout_nonclk', 'region_nets', 'region_over_max', 'region_trunk_max_um')} |
                     dict(hops_over=out['hops_over_reach']['nets'], hop_bits=out['hops_over_reach']['bits'],
                          worst_hops=[(w['um'], w['net']) for w in out['hops_over_reach']['worst'][:8]],
                          worst_region=out['region_worst'][:3], worst_clock=out['clock_worst'][:4])))


if __name__ == '__main__':
    main()
