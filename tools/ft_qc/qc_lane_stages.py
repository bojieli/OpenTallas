#!/usr/bin/env python3
"""FT-QC (FT-PLAN 10-23): per-lane pin-to-pin geometry, block crossings and static-schedule stage counts for the Qwen
compute die at a given relay reach (default 1000 um = REACH-M89 one-cycle M8/M9 hop for Qwen).

Inputs (from a die case + coordinator dump): insts.tsv (name master x y w h orient), elements.lef, relay_stages.json.
Stage rule (FT-PLAN item 3): a lane of pin-to-pin Manhattan length L on M8/M9 needs ceil(L / reach) wire segments,
i.e. ceil(L / reach) - 1 relay flops plus the destination landing flop = ceil(L / reach) stages (>= 1 for any lane
that has a stage today; 0-stage lanes stay 0).  The current stage count is relay_stages.json 'stages'.
Output JSON: per lane {id, width, domain, src, dst, L_um, stages_now, stages_new, crosses: {block: um}} + totals,
and per big block the ft bits a straight (L-shaped, x first) path would carry through it.
"""
import argparse, collections, json, math, re


def lef_pins(path, want):
    txt = open(path).read()
    out = {}
    for m in re.finditer(r'MACRO (\S+)\n(.*?)END \1\n', txt, re.S):
        name, body = m.group(1), m.group(2)
        if name not in want:
            continue
        w, h = map(float, re.search(r'SIZE ([\d.]+) BY ([\d.]+)', body).groups())
        pins = collections.defaultdict(list)
        for pm in re.finditer(r'  PIN (\S+)\n(.*?)  END \1\n', body, re.S):
            r = re.search(r'RECT ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+)', pm.group(2))
            if r:
                x0, y0, x1, y1 = map(float, r.groups())
                pins[re.sub(r'\[\d+\]$', '', pm.group(1))].append(((x0 + x1) / 2, (y0 + y1) / 2))
        out[name] = (w, h, {k: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v)) for k, v in pins.items()})
    return out


def xform(px, py, w, h, o):
    return {'R0': (px, py), 'MX': (px, h - py), 'MY': (w - px, py), 'R180': (w - px, h - py)}[o]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--insts', required=True)
    ap.add_argument('--lef', required=True)
    ap.add_argument('--relay-stages', required=True)
    ap.add_argument('--reach-um', type=float, default=1000.0)
    ap.add_argument('--big', default='qfd_c_b16_dv,qfd_dv_slice2_e,qfd_dv_slice2_w')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    big_masters = set(a.big.split(','))
    inst = {}
    for ln in open(a.insts):
        n, m, x, y, w, h, o = ln.rstrip('\n').split('\t')
        inst[n] = (m, float(x), float(y), float(w), float(h), o)
    buses = json.load(open(a.relay_stages))['buses']
    want = {b[k]['master'] for b in buses for k in ('src', 'dst')}
    pins = lef_pins(a.lef, want)
    bigs = {n: v for n, v in inst.items() if v[0] in big_masters}

    def pin_xy(e):
        m, x, y, w, h, o = inst[e['inst']]
        pw, ph, pp = pins[m]
        px, py = pp.get(e['port'], (pw / 2, ph / 2))
        dx, dy = xform(px, py, pw, ph, o)
        return x + dx, y + dy

    def cross(p, q):
        res = {}
        for n, (m, x, y, w, h, o) in bigs.items():
            L = 0.0
            for (ax, ay), (bx, by) in ((p, (q[0], p[1])), ((q[0], p[1]), q)):
                if ay == by and y < ay < y + h:
                    L += max(0.0, min(max(ax, bx), x + w) - max(min(ax, bx), x))
                elif ax == bx and x < ax < x + w:
                    L += max(0.0, min(max(ay, by), y + h) - max(min(ay, by), y))
            if L > 20:
                res[n] = round(L, 1)
        return res

    lanes, per_block = [], collections.defaultdict(lambda: collections.Counter())
    tot = collections.Counter()
    for b in buses:
        if b['src']['inst'] not in inst or b['dst']['inst'] not in inst:
            continue
        p, q = pin_xy(b['src']), pin_xy(b['dst'])
        L = abs(p[0] - q[0]) + abs(p[1] - q[1])
        s0 = b['stages']
        geo405 = max(1, math.ceil(L / 405.0))
        padded = s0 > geo405 + 1          # age-equalised (pads beyond geometry): keep the padding offset, owner re-derives
        s1 = 0 if s0 == 0 else max(1, math.ceil(L / a.reach_um))
        if padded:
            s1 = s0 - max(0, geo405 - s1)
        cr = {k: v for k, v in cross(p, q).items() if k not in (b['src']['inst'], b['dst']['inst'])}
        for k in cr:
            per_block[k]['ft_bits'] += b['width']
            per_block[k]['ft_lanes'] += 1
        lanes.append(dict(id=b['id'], width=b['width'], domain=b['domain'], src=b['src']['inst'], dst=b['dst']['inst'],
                          L_um=round(L, 1), stages_now=s0, padded=padded, stages_new=min(s0, s1) if s0 else 0, crosses=cr))
        tot['lanes'] += 1
        tot['padded_lanes'] += padded
        tot['bit_stages_now'] += b['width'] * s0
        tot['bit_stages_new'] += b['width'] * (min(s0, s1) if s0 else 0)
    crit = sorted(lanes, key=lambda r: -r['stages_now'])[:40]
    json.dump(dict(schema='opentallas.ft_qc.lane_stages.v1', reach_um=a.reach_um,
                   rule='stages_new = min(stages_now, max(1, ceil(L_pin_to_pin / reach))) for lanes with stages_now > 0; padded lanes (stages_now > ceil(L/405)+1, age-equalised) keep their padding: stages_now - (ceil(L/405) - ceil(L/reach))',
                   totals=dict(tot), per_block={k: dict(v) for k, v in sorted(per_block.items())},
                   longest_now=[(r['id'], r['L_um'], r['stages_now'], r['stages_new']) for r in crit], lanes=lanes),
              open(a.out, 'w'), indent=1)
    print(json.dumps(dict(tot)), 'blocks with ft:', len(per_block))
    for r in crit[:25]:
        print(f"  {r['id']:<48} {r['width']:>5}b L={r['L_um']:>8.0f} now {r['stages_now']:>2} -> {r['stages_new']:>2} {'PAD' if r['padded'] else ''} {r['crosses']}")


if __name__ == '__main__':
    main()
