#!/usr/bin/env python3
"""KV-HROOT10: anneal the qkd_hr_cluster child placement on the 43.2 lattice (closed-view pin centroids per port,
stand-ins pinned by the parent = nearest boundary point), cost = bits x (len + 6 x max(0, len - REACH)).
    hr_anneal.py OUT.json W H [seed] [iters] [--fix inst=x,y,o ...]
"""
import collections
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hr_parent as HP  # noqa: E402

LAT = 43.2
REACH = 380.0
import os as _os
GAP = float(_os.environ.get("OT_GAP", "21.6"))
ORS = ('R0', 'MX', 'MY', 'R180')


def build():
    V = {'place': {}}
    blocks = {}
    for inst, (vd, cell) in HP.CLOSED.items():
        W, H, pins = HP.lef_pins(HP.gshow(f'{vd}/{cell}.lef'))
        blocks[inst] = dict(w=W, h=H, pins=pins, standin=False)
    for inst, (cell, w, h, cks, rtl) in HP.STANDIN.items():
        blocks[inst] = dict(w=w, h=h, pins={}, standin=True)
    # port centroids (local) for closed blocks
    cen = {}
    for inst, b in blocks.items():
        if b['standin']:
            continue
        acc = collections.defaultdict(lambda: [0.0, 0.0, 0])
        for nm, (x, y) in b['pins'].items():
            p = nm.split('[')[0]
            a = acc[p]
            a[0] += x; a[1] += y; a[2] += 1
        cen[inst] = {p: (a[0] / a[2], a[1] / a[2]) for p, a in acc.items()}
    # edges (instA, portA, instB, portB) -> bits ; ports to the parent boundary: (inst, port, 'PORT') -> bits
    nets = collections.defaultdict(list)
    for inst, ports in HP.NB['inst'].items():
        for p, bits in ports.items():
            if p in HP.CLOCKS:
                continue
            for n in bits:
                nets[n].append((inst, p))
    tops = collections.defaultdict(set)
    for p, bits in HP.NB['ports'].items():
        for n in bits:
            tops[n].add(p)
    E = collections.Counter()
    for n, mem in nets.items():
        if len(mem) >= 4:
            continue    # broadcasts (resets / straps): relayed / landed, not lanes
        for i in range(len(mem)):
            for j in range(i + 1, len(mem)):
                if mem[i][0] != mem[j][0]:
                    E[(mem[i], mem[j])] += 1
        if tops.get(n):
            for m in mem[:1]:
                E[(m, ('PORT', next(iter(tops[n]))))] += 1
    return blocks, cen, E


def pt(blocks, cen, pos, inst, port, toward):
    b = blocks[inst]
    x0, y0, o = pos[inst]
    w, h = b['w'], b['h']
    if not b['standin']:
        lx, ly = cen[inst].get(port, (w / 2, h / 2))
        lx, ly = HP.orient_xy(lx, ly, w, h, o)
        return x0 + lx, y0 + ly
    tx, ty = toward
    # nearest boundary point toward the target (stand-in pins are parent-assigned)
    cx, cy = min(max(tx, x0), x0 + w), min(max(ty, y0), y0 + h)
    if x0 < cx < x0 + w and y0 < cy < y0 + h:
        cx, cy = x0 + w / 2, y0 + h / 2
    return cx, cy


def centre(blocks, pos, inst):
    x, y, _ = pos[inst]
    return x + blocks[inst]['w'] / 2, y + blocks[inst]['h'] / 2


PF = {}       # top port -> required parent face


def fdist(x, y, w, h, PW, PH, f):
    # distance from a block rectangle (x, y, w, h) or a point (w = h = 0) to parent face f
    return {'W': x, 'E': PW - x - w, 'S': y, 'N': PH - y - h}[f]


def cost(blocks, cen, E, pos, PW, PH, detail=False):
    c = 0.0
    over = 0
    rows = collections.Counter()
    for ((ia, pa), (ib, pb)), n in E.items():
        if ia == 'PORT' or ib == 'PORT':
            inst, port = (ia, pa) if ib == 'PORT' else (ib, pb)
            top = pb if ib == 'PORT' else pa
            faces = [PF[top]] if top in PF else 'NSEW'
            x, y = pt(blocks, cen, pos, inst, port, centre(blocks, pos, inst))
            if blocks[inst]['standin']:
                x0, y0, _ = pos[inst]
                d = min(fdist(x0, y0, blocks[inst]['w'], blocks[inst]['h'], PW, PH, f) for f in faces)
            else:
                d = min(fdist(x, y, 0, 0, PW, PH, f) for f in faces)
        else:
            a = pt(blocks, cen, pos, ia, pa, centre(blocks, pos, ib))
            bpt = pt(blocks, cen, pos, ib, pb, a)
            a = pt(blocks, cen, pos, ia, pa, bpt)
            d = abs(a[0] - bpt[0]) + abs(a[1] - bpt[1])
        ex = max(0.0, d - REACH)
        c += n * (d + 6 * ex)
        if d > 405:
            over += n
            if detail:
                rows[(ia, ib, round(d))] += n
    # overlap / spacing / outline
    L = list(pos)
    for i in range(len(L)):
        a = L[i]; xa, ya, _ = pos[a]; wa, ha = blocks[a]['w'], blocks[a]['h']
        if xa < GAP or ya < GAP or xa + wa > PW - GAP or ya + ha > PH - GAP:
            c += 1e7
        for j in range(i + 1, len(L)):
            b = L[j]; xb, yb, _ = pos[b]; wb, hb = blocks[b]['w'], blocks[b]['h']
            ox = min(xa + wa + GAP, xb + wb + GAP) - max(xa, xb)
            oy = min(ya + ha + GAP, yb + hb + GAP) - max(ya, yb)
            if ox > 1e-6 and oy > 1e-6:
                c += 1e5 * (ox * oy) ** 0.5 + 1e6
    if detail:
        return c, over, rows
    return c, over


def snap(v):
    return round(round(v / LAT) * LAT, 3)


def main():
    out, PW, PH = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    iters = int(sys.argv[5]) if len(sys.argv) > 5 else 60000
    init = json.load(open(sys.argv[6]))['place'] if len(sys.argv) > 6 and sys.argv[6] != '-' else None
    if len(sys.argv) > 7:
        PF.update(json.loads(sys.argv[7]))
    rnd = random.Random(seed)
    blocks, cen, E = build()
    import os
    if os.environ.get('OVERLAP_ONLY'):
        E = collections.Counter()
    pos = {}
    for inst, b in blocks.items():
        if init and inst in init:
            x, y, o = init[inst]
            pos[inst] = (snap(x), snap(y), o)
        else:
            pos[inst] = (snap(rnd.uniform(LAT, PW - b['w'] - LAT)), snap(rnd.uniform(LAT, PH - b['h'] - LAT)), 'R0')
    cur, ov = cost(blocks, cen, E, pos, PW, PH)
    best, bpos = cur, dict(pos)
    names = list(pos)
    T0 = 2e5
    for k in range(iters):
        T = T0 * (1 - k / iters) ** 3 + 1.0
        np_ = dict(pos)
        r = rnd.random()
        a = rnd.choice(names)
        x, y, o = np_[a]
        if r < 0.6:
            s = max(1, int(8 * (1 - k / iters)))
            np_[a] = (snap(x + LAT * rnd.randint(-s, s)), snap(y + LAT * rnd.randint(-s, s)), o)
        elif r < 0.8:
            np_[a] = (x, y, rnd.choice(ORS))
        else:
            b = rnd.choice(names)
            xb, yb, ob = np_[b]
            np_[a] = (xb, yb, o)
            np_[b] = (x, y, ob)
        c, _ = cost(blocks, cen, E, np_, PW, PH)
        if init and c >= 1e6 and cur < 1e6:
            continue          # legal start: keep it legal
        if c < cur or rnd.random() < math.exp((cur - c) / T):
            pos, cur = np_, c
            if c < best:
                best, bpos = c, dict(np_)
    c, over, rows = cost(blocks, cen, E, bpos, PW, PH, detail=True)
    print(f'seed {seed} W {PW} H {PH} cost {c:.0f} bits>405 {over}')
    agg = collections.Counter()
    for (ia, ib, d), n in rows.items():
        agg[(ia, ib)] = max(agg[(ia, ib)], d)
    for (ia, ib), d in agg.most_common(12):
        print('   ', d, ia, ib)
    json.dump({'outline': [PW, PH], 'cost': c, 'port_face': PF, 'over405_bits': over,
               'place': {k: list(v) for k, v in bpos.items()}}, open(out, 'w'), indent=1)


if __name__ == '__main__':
    main()
