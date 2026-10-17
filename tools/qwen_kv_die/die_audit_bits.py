#!/usr/bin/env python3
"""KVPLAN 1815 (2026-10-16): PER-BIT die-top reach audit of a KV/system die case (the die_audit.py class-4 measure averaged
every bus pin of a port into one point, so a broadcast word or a word spread along a face was under-measured).

Reads <case>/elements.lef (every PIN bit's shape), place.tcl (origin + orient) and die.v (every instance connection,
concatenations included, LSB first) and measures EVERY DIE NET BIT on its own pins:
  bbox    = half-perimeter of the bit's pin bounding box (the brief's 'per-bit bbox');
  radius  = max Manhattan distance driver pin -> load pin (driver = the pin whose LEF DIRECTION is OUTPUT; else bbox).
A net = all bits of one die wire; its figure is the worst bit.  Constant nets (assign 1'bx) and clock nets are skipped.
Each over-reach net is classed:
  phy      -- touches a hard PHY macro pin (qkd_hbm3e_phy_pc, ot_qfd_serdes_112g_x12_phy, ot_qkvd_ucie_x64_phy): PHY analog /
              abutted boundary, reported apart (declared, not a relay hop);
  relayed  -- one end is a relay standard / relay frame / reset-region stage (a planned hop that is too long);
  unrelayed-- neither end is a relay (a frame-internal or direct die wire).
usage: die_audit_bits.py CASE [--reach 401] [--metric bbox|radius] [--out audit.json]
"""
import argparse
import collections
import json
import re

PHY = ('qkd_hbm3e_phy_pc', 'ot_qfd_serdes_112g_x12_phy', 'ot_qkvd_ucie_x64_phy', 'ot_hbm3e_phy')
RELAY = re.compile(r'^(qkd_rlys?_|qkd_rly_|qkd_rst_region)')
CLK = re.compile(r'^n_(clk|fck|pll)|_clk_|^n_ck')


def lef(path):
    size, pins, dirs = {}, {}, {}
    cur = pin = None
    for ln in open(path):
        s = ln.strip()
        if s.startswith('MACRO '):
            cur, pin = s.split()[1], None
            pins.setdefault(cur, {})
            dirs.setdefault(cur, {})
        elif cur and s.startswith('SIZE') and cur not in size:
            t = s.split()
            size[cur] = (float(t[1]), float(t[3]))
        elif cur and s.startswith('PIN '):
            pin = s.split()[1]
        elif pin and s.startswith('DIRECTION'):
            dirs[cur][pin] = s.split()[1]
        elif pin and s.startswith('RECT') and pin not in pins[cur]:
            t = s.split()
            pins[cur][pin] = ((float(t[1]) + float(t[3])) / 2, (float(t[2]) + float(t[4])) / 2)
        elif pin and s.startswith('END ') and s.split()[1] == pin:
            pin = None
    return size, pins, dirs


def net_bits(expr, width):
    expr = expr.strip()
    parts = [x.strip() for x in expr[1:-1].split(',') if x.strip()] if expr.startswith('{') else [expr]
    out = []
    for p in reversed(parts):
        b = re.fullmatch(r'(\S+)\[(\d+)(?::(\d+))?\]', p)
        if b:
            hi = int(b.group(2))
            lo = int(b.group(3)) if b.group(3) is not None else hi
            out += [f'{b.group(1)}[{i}]' for i in range(lo, hi + 1)]
        elif re.fullmatch(r"\d+'[bh][0-9a-fA-F_]+", p):
            out += ['CONST'] * int(p.split("'")[0])
        else:
            out += [f'{p}[{i}]' for i in range(width.get(p, 1))]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('case')
    ap.add_argument('--reach', type=float, default=401.0)
    ap.add_argument('--metric', choices=('bbox', 'radius'), default='bbox')
    ap.add_argument('--out')
    ap.add_argument('--top', type=int, default=40)
    ap.add_argument('--explain', default='', help='comma list of nets: print the worst bit\'s pins (inst, master, pin, x, y)')
    a = ap.parse_args()
    D = a.case
    size, pins, dirs = lef(D + '/elements.lef')
    pos = {}
    for ln in open(D + '/place.tcl'):
        mm = re.search(r'findInst (\S+)\]\s+([\d.]+)\s+([\d.]+)\s+(\w+)', ln)
        if mm:
            pos[mm.group(1)] = (float(mm.group(2)), float(mm.group(3)), mm.group(4))
    txt = open(D + '/die.v').read()
    width = {mm.group(2): int(mm.group(1)) + 1 for mm in re.finditer(r'wire \[(\d+):0\] (\S+);', txt)}
    for mm in re.finditer(r'^\s*wire (\S+);', txt, re.M):
        width.setdefault(mm.group(1), 1)
    const = set(re.findall(r"^\s*assign (\S+) = \d+'b[01];", txt, re.M))
    inst = {}
    bitpins = collections.defaultdict(list)          # net bit -> [(inst, pin bit)]
    unplaced = set()
    for mm in re.finditer(r'^\s+(\w+) (\S+) \((.*)\);\s*$', txt, re.M):
        mst, nm, body = mm.groups()
        if mst in ('wire', 'assign', 'module'):
            continue
        inst[nm] = mst
        for c in re.finditer(r'\.(\\?\S+?)\((\{[^}]*\}|[^)]*)\)', body):
            p, e = c.group(1), c.group(2)
            bits = net_bits(e, width)
            for i, b in enumerate(bits):
                if b == 'CONST':
                    continue
                pb = f'{p}[{i}]' if f'{p}[{i}]' in pins.get(mst, {}) else (p if len(bits) == 1 else f'{p}[{i}]')
                bitpins[b].append((nm, pb))

    def xy(i, pb):
        if i not in pos or inst[i] not in size:
            return None
        q = pins[inst[i]].get(pb)
        if q is None:
            return None
        x0, y0, o = pos[i]
        w, h = size[inst[i]]
        px, py = q
        return {'R0': (x0 + px, y0 + py), 'MX': (x0 + px, y0 + h - py), 'MY': (x0 + w - px, y0 + py),
                'R180': (x0 + w - px, y0 + h - py), 'N': (x0 + px, y0 + py), 'FS': (x0 + px, y0 + h - py),
                'FN': (x0 + w - px, y0 + py), 'S': (x0 + w - px, y0 + h - py)}.get(o)
    per_net = {}
    nopin = 0
    for b, ps in bitpins.items():
        net = b.rsplit('[', 1)[0]
        if net in const or CLK.search(net) or len(ps) < 2:
            continue
        pts = [(xy(i, p), i, p) for i, p in ps]
        if any(q[0] is None for q in pts):
            nopin += 1
            continue
        xs = [q[0][0] for q in pts]
        ys = [q[0][1] for q in pts]
        bbox = max(xs) - min(xs) + max(ys) - min(ys)
        drv = [q for q in pts if dirs.get(inst[q[1]], {}).get(q[2], dirs.get(inst[q[1]], {}).get(q[2].split('[')[0])) == 'OUTPUT']
        if len(drv) == 1:
            d0 = drv[0][0]
            rad = max(abs(q[0][0] - d0[0]) + abs(q[0][1] - d0[1]) for q in pts)
        else:
            rad = bbox
        v = bbox if a.metric == 'bbox' else rad
        r = per_net.get(net)
        if r is None or v > r['um']:
            masters = sorted({inst[q[1]] for q in pts})
            per_net[net] = dict(um=round(v, 1), bbox=round(bbox, 1), radius=round(rad, 1), loads=len(pts) - 1,
                                worst_bit=b, masters=masters, bits=width.get(net, 1))
    over = {n: r for n, r in per_net.items() if r['um'] > a.reach}
    for n in [x for x in a.explain.split(',') if x]:
        r = per_net.get(n)
        if not r:
            print('explain', n, 'not measured')
            continue
        print('explain', n, {k: r[k] for k in ('um', 'bbox', 'radius', 'loads', 'worst_bit')})
        for i, p in bitpins[r['worst_bit']]:
            q = xy(i, p)
            print('   ', i, inst[i], p, dirs.get(inst[i], {}).get(p, dirs.get(inst[i], {}).get(p.split('[')[0])),
                  q and (round(q[0], 1), round(q[1], 1)), pos.get(i))

    def cls(r):
        if any(m in PHY for m in r['masters']):
            return 'phy'
        if any(RELAY.match(m) for m in r['masters']):
            return 'relayed'
        return 'unrelayed'
    by = collections.defaultdict(list)
    for n, r in over.items():
        r['class'] = cls(r)
        by[r['class']].append((r['um'], n))
    fam = collections.Counter()
    for n, r in over.items():
        fam[(r['class'], re.sub(r'\d+', '#', n))] += 1
    out = dict(case=D, metric=a.metric, reach_um=a.reach, nets_measured=len(per_net), bits_without_pin=nopin,
               nets_over=len(over), bits_over=sum(r['bits'] for r in over.values()),
               by_class={k: len(v) for k, v in by.items()},
               bands={f'{lo}-{hi}': sum(lo < r['um'] <= hi for r in over.values())
                      for lo, hi in ((a.reach, 445), (445, 480), (480, 600), (600, 1000), (1000, 1e9))},
               worst={k: [dict(um=u, net=n, **{x: over[n][x] for x in ('bbox', 'radius', 'loads', 'masters')})
                          for u, n in sorted(v, reverse=True)[:a.top]] for k, v in by.items()},
               families=[dict(cls=k[0], family=k[1], nets=c) for k, c in fam.most_common(80)])
    if a.out:
        with open(a.out, 'w') as f:
            json.dump(dict(out, nets={n: r for n, r in sorted(over.items())}), f, indent=1)
    print(json.dumps({k: out[k] for k in ('metric', 'reach_um', 'nets_measured', 'bits_without_pin', 'nets_over',
                                          'bits_over', 'by_class', 'bands')}))
    for f_ in out['families'][:40]:
        print(f'  {f_["cls"]:9s} {f_["nets"]:6d}  {f_["family"]}')
    for k, v in out['worst'].items():
        print(k, [(w['um'], w['net'], w['loads']) for w in v[:8]])


if __name__ == '__main__':
    main()
