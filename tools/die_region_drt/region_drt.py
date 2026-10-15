#!/usr/bin/env python3
"""Die-region detailed route: the GRT-vs-DRT error bar of a die-level global route (any die; README.md).

A die is closed at the die level by a full-die GLOBAL route (GRT) plus STA on GRT parasitics; no flat full-die detailed
route is run (academic validation).  This tool measures how far that global route is from a real detailed route on
representative windows cut from the die's own GRT checkpoint:

  pick     (host)       windows from the die GRT itself: worst congestion, longest relay link, IO edge, dense column
  stage    (host)       one run dir per window: cut -> DRT on the clipped die guides -> RCX -> STA GRT / RCX
  cut      (container)  openroad -python: keep instances fully inside the window as FIXED real abstracts; an intruding
                        instance becomes its OBS obstructions plus its in-window pins as fixed terminals (no region
                        growth); every die net that leaves the window gets a terminal where ITS die guide crosses the
                        edge, on that guide's layer, on a free track; guides clipped and kept; PDN clipped
  spef     (host)       the die GRT SPEF filtered to the window's internal nets (STA on GRT parasitics of record)
  compare  (host)       DRC classes, wire length / vias / per-layer length GRT vs DRT, layer-contract audit,
                        relay-path STA slack GRT vs RCX -> compare.json

Layer contract (owner, hierarchy contract 2026-10-11): die nets route M4-M9; hard blocks are abstracts whose OBS own
M1-M7 (tile signals <= M6, tile PG M7), so over a block body only M8/M9 carry die nets.  Pin keepout is ABOVE ONLY:
the tool adds nothing on the layer below any block pin; it audits that the layer above every in-window face pin is
reachable (pin_access audit in cut.json).  Clock / reset nets are built by the die clock tree (special nets in the
die GRT checkpoint) and are not routed here.
"""
import json
import os
import re

from pathlib import Path

PITCH = {'M4': 0.048, 'M5': 0.048, 'M6': 0.064, 'M7': 0.064, 'M8': 0.080, 'M9': 0.080}
ADJ = {'M4': 0.30, 'M5': 0.30, 'M6': 0.05, 'M7': 0.05, 'M8': 0.05, 'M9': 0.05}   # die GRT layer adjustments
HDIR = {'M4': True, 'M5': False, 'M6': True, 'M7': False, 'M8': True, 'M9': False}  # ASAP7 preferred directions
LV = {f'M{k}': k for k in range(1, 10)}


# ----------------------------------------------------------------------------------------------------------- host
def parse_lef(paths):
    ms = {}
    for p in paths:
        t = Path(p).read_text()
        for m in re.finditer(r'\nMACRO (\S+)(.*?)\nEND \1', t, re.S):
            b = m.group(2)
            w, h = (float(v) for v in re.search(r'SIZE (\S+) BY (\S+)', b).groups())
            obs = b.split('\n  OBS')[-1] if '\n  OBS' in b else ''
            ms[m.group(1)] = dict(w=w, h=h, obs=sorted({l for l in re.findall(r'LAYER (\S+)', obs) if l in LV},
                                                       key=LV.get))
    return ms


def parse_def_components(path):
    units, die, comps = 1000, None, []
    with open(path) as f:
        for ln in f:
            if ln.startswith('UNITS'):
                units = int(ln.split()[3])
            elif ln.startswith('DIEAREA'):
                v = [int(x) for x in re.findall(r'-?\d+', ln)]
                die = [v[0] / units, v[1] / units, v[2] / units, v[3] / units]
            elif ln.startswith('COMPONENTS'):
                break
        for ln in f:
            if ln.startswith('END COMPONENTS'):
                break
            m = re.match(r'\s*- (\S+) (\S+) .*?(?:FIXED|PLACED) \( (-?\d+) (-?\d+) \) (\S+)', ln)
            if m:
                comps.append((m.group(1), m.group(2), int(m.group(3)) / units, int(m.group(4)) / units, m.group(5)))
    return units, die, comps


def parse_guides(path, units):
    """yield (net, [(layer, x0, y0, x1, y1) um])"""
    net, boxes = None, []
    with open(path) as f:
        for ln in f:
            s = ln.split()
            if not s:
                continue
            if len(s) == 5:
                boxes.append((s[4], int(s[0]) / units, int(s[1]) / units, int(s[2]) / units, int(s[3]) / units))
            elif s[0] == '(':
                boxes = []
            elif s[0] == ')':
                yield net, boxes
            else:
                net = s[0]


def pick(a):
    import numpy as np
    ms = parse_lef(a.lef)
    units, die, comps = parse_def_components(a.def_)
    B = a.bin_um
    nx, ny = int((die[2] - die[0]) / B) + 1, int((die[3] - die[1]) / B) + 1
    lays = list(PITCH)
    dem = {l: np.zeros((nx, ny)) for l in lays}
    cap = {l: np.full((nx, ny), B / PITCH[l] * (1 - ADJ[l])) for l in lays}
    bodies = []
    for name, mst, x, y, o in comps:
        m = ms.get(mst)
        if m is None:
            continue
        w, h = (m['h'], m['w']) if o in ('E', 'W', 'FE', 'FW') else (m['w'], m['h'])
        bodies.append((name, mst, x, y, x + w, y + h))
        for l in m['obs']:
            if l in cap:
                i0, i1, j0, j1 = int(x / B), int((x + w) / B), int(y / B), int((y + h) / B)
                for i in range(i0, min(i1, nx - 1) + 1):
                    fx = (min(x + w, (i + 1) * B) - max(x, i * B)) / B
                    for j in range(j0, min(j1, ny - 1) + 1):
                        fy = (min(y + h, (j + 1) * B) - max(y, j * B)) / B
                        cap[l][i, j] *= max(0.0, 1 - fx * fy)
    gcell, relay, longest = None, [], []
    nn = 0
    for net, boxes in parse_guides(a.guide, units):
        nn += 1
        if not boxes:
            continue
        if gcell is None:
            gcell = min(min(b[3] - b[1], b[4] - b[2]) for b in boxes)
        bx = (min(b[1] for b in boxes), min(b[2] for b in boxes), max(b[3] for b in boxes), max(b[4] for b in boxes))
        hp = bx[2] - bx[0] + bx[3] - bx[1]
        (relay if '__r' in net else longest).append((hp, net, bx))
        if len(relay) > 4000:
            relay = sorted(relay, reverse=True)[:200]
        if len(longest) > 4000:
            longest = sorted(longest, reverse=True)[:200]
        for l, x0, y0, x1, y1 in boxes:
            if l not in dem:
                continue
            d = dem[l]
            for i in range(int(x0 / B), min(int(x1 / B), nx - 1) + 1):
                ox = min(x1, (i + 1) * B) - max(x0, i * B)
                if ox <= 0:
                    continue
                for j in range(int(y0 / B), min(int(y1 / B), ny - 1) + 1):
                    oy = min(y1, (j + 1) * B) - max(y0, j * B)
                    if oy > 0:
                        d[i, j] += ox * oy / (B * gcell)
    util = np.zeros((nx, ny))
    for l in lays:
        u = np.where(cap[l] >= 1.0, dem[l] / np.maximum(cap[l], 1.0), 0.0)
        util = np.maximum(util, u)
    tot = sum(dem[l] for l in lays)
    k = max(1, int(round(a.win_um / B)))

    def wsum(arr):
        S = np.zeros((nx + 1, ny + 1))
        S[1:, 1:] = arr.cumsum(0).cumsum(1)
        return S[k:, k:] - S[:-k, k:] - S[k:, :-k] + S[:-k, :-k]
    chosen = []

    def free(w):
        return all(w[2] <= c['win'][0] or w[0] >= c['win'][2] or w[3] <= c['win'][1] or w[1] >= c['win'][3]
                   for c in chosen)

    def best(score, why, extra=None):
        order = np.dstack(np.unravel_index(np.argsort(-score, axis=None), score.shape))[0]
        for i, j in order[:200000]:
            w = [die[0] + i * B, die[1] + j * B, min(die[2], die[0] + (i + k) * B), min(die[3], die[1] + (j + k) * B)]
            if free(w):
                chosen.append(dict(name=why, win=[round(v, 3) for v in w], score=float(score[i, j]), **(extra or {})))
                return
    ov = np.zeros((nx, ny))
    # r5 2026-10-14: global_route writes -congestion_report_file only when it leaves congestion; an absent report after a
    # GRT with total overflow 0 means no overflow gcells (c8p REGION_PICK_FAIL was this FileNotFoundError)
    if a.congestion_rpt and Path(a.congestion_rpt).exists():
        for m in re.finditer(r'bbox = \(([-\d.]+), ([-\d.]+)\) - \(([-\d.]+), ([-\d.]+)\)',
                             Path(a.congestion_rpt).read_text()):
            cx, cy = (float(m.group(1)) + float(m.group(3))) / 2, (float(m.group(2)) + float(m.group(4))) / 2
            ov[min(nx - 1, int(cx / B)), min(ny - 1, int(cy / B))] += 1
    if ov.sum() > 0:
        # the die GRT's own overflow gcells decide; guide utilisation breaks ties
        best(wsum(ov) + 1e-3 * wsum(util) / (k * k), 'cong',
             dict(metric='GRT overflow gcells in the window (congestion report) + 1e-3 x mean guide utilisation',
                  grt_overflow_gcells_total=int(ov.sum())))
    else:
        best(wsum(util) / (k * k), 'cong', dict(metric='mean max-layer guide utilisation over the window'))
    if chosen and ov.sum() > 0:
        w = chosen[-1]['win']
        chosen[-1]['grt_overflow_gcells_in_window'] = int(ov[int(w[0] / B):int(w[0] / B) + k,
                                                            int(w[1] / B):int(w[1] / B) + k].sum())
    clk = re.compile(a.skip_net_re)
    rl = [r for r in sorted(relay or longest, reverse=True) if not clk.search(r[1]) and
          max(r[2][2] - r[2][0], r[2][3] - r[2][1]) <= a.max_win_um]
    for hp, net, bx in rl:
        cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
        half = max(a.win_um, bx[2] - bx[0] + 2 * a.margin_um, bx[3] - bx[1] + 2 * a.margin_um) / 2
        w = [max(die[0], cx - half), max(die[1], cy - half), min(die[2], cx + half), min(die[3], cy + half)]
        if free(w):
            chosen.append(dict(name='relay', win=[round(v, 3) for v in w], score=hp, net=net,
                               metric='longest relay-hop net by guide HPWL (um)'))
            break
    phys = [b for b in bodies if re.search(a.io_master_re, b[1], re.I)]
    cands = []
    for name, mst, x0, y0, x1, y1 in phys:
        dl, dr, db, dt = x0 - die[0], die[2] - x1, y0 - die[1], die[3] - y1
        side = min((dl, 'W'), (dr, 'E'), (db, 'S'), (dt, 'N'))[1]
        W = a.win_um
        if side in ('W', 'E'):
            depth = min(die[2] - die[0], (x1 - x0) + W / 2)
            cy = (y0 + y1) / 2
            w = [die[0], cy - W / 2, die[0] + depth, cy + W / 2] if side == 'W' else \
                [die[2] - depth, cy - W / 2, die[2], cy + W / 2]
        else:
            depth = min(die[3] - die[1], (y1 - y0) + W / 2)
            cx = (x0 + x1) / 2
            w = [cx - W / 2, die[1], cx + W / 2, die[1] + depth] if side == 'S' else \
                [cx - W / 2, die[3] - depth, cx + W / 2, die[3]]
        w = [max(die[0], w[0]), max(die[1], w[1]), min(die[2], w[2]), min(die[3], w[3])]
        i0, i1, j0, j1 = int(w[0] / B), int(w[2] / B), int(w[1] / B), int(w[3] / B)
        cands.append((float(tot[i0:i1 + 1, j0:j1 + 1].sum()), name, side, w))
    for sc, name, side, w in sorted(cands, reverse=True):
        if free(w):
            chosen.append(dict(name='ioedge', win=[round(v, 3) for v in w], score=sc, phy=name, side=side,
                               metric='guide demand (tracks x bins) of the PHY face window'))
            break
    col = tot.sum(1)
    cs = np.convolve(col, np.ones(k), 'valid')
    for i in np.argsort(-cs):
        sc = wsum(tot)[i]
        for j in np.argsort(-sc):
            w = [die[0] + i * B, die[1] + j * B, min(die[2], die[0] + (i + k) * B), min(die[3], die[1] + (j + k) * B)]
            if free(w):
                chosen.append(dict(name='column', win=[round(v, 3) for v in w], score=float(sc[j]),
                                   column_x_um=[w[0], w[2]], metric='densest full-height column, then its densest window'))
                break
        else:
            continue
        break
    out = dict(guide=str(a.guide), def_=str(a.def_), nets=nn, bin_um=B, win_um=a.win_um, gcell_um=gcell,
               die_um=die, util_max=float(util.max()), windows=chosen)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1))
    print(json.dumps(chosen, indent=1))


# ------------------------------------------------------------------------------------------------------ container
def cut():
    import bisect
    import odb
    reg = json.loads(Path(os.environ['DRD_REGION_JSON']).read_text())
    db = odb.dbDatabase.create()          # Design.readDb segfaults on multi-GB GRT checkpoints (OpenROAD 26Q3-1510)
    odb.read_db(db, os.environ['DRD_IN'])
    block = db.getChip().getBlock()
    dbu = block.getDbUnitsPerMicron()
    um = lambda v: int(round(v * dbu))  # noqa: E731
    x0, y0, x1, y1 = (um(v) for v in reg['win'])
    die = block.getDieArea()
    x0, y0, x1, y1 = max(x0, die.xMin()), max(y0, die.yMin()), min(x1, die.xMax()), min(y1, die.yMax())
    tech = db.getTech()
    layers = {l.getName(): l for l in tech.getLayers() if l.getType() == 'ROUTING'}
    hdir = {n: l.getDirection() == 'HORIZONTAL' for n, l in layers.items()}
    lvl = {n: l.getRoutingLevel() for n, l in layers.items()}
    MIN_LVL, MAX_LVL = lvl['M4'], lvl['M9']

    def inside(r):
        return r.xMin() >= x0 and r.xMax() <= x1 and r.yMin() >= y0 and r.yMax() <= y1

    def overlaps(r):
        return r.xMin() < x1 and r.xMax() > x0 and r.yMin() < y1 and r.yMax() > y0

    def place(inst, g):
        """master-local pin box -> die coordinates (dbTransform.apply(Rect) has no python overload in 26Q3)"""
        b = inst.getBBox()
        m = inst.getMaster()
        w, h = m.getWidth(), m.getHeight()
        o = str(inst.getOrient())

        def f(x, y):
            return {'R0': (x, y), 'MY': (w - x, y), 'MX': (x, h - y), 'R180': (w - x, h - y), 'R90': (h - y, x),
                    'R270': (y, w - x), 'MXR90': (y, x), 'MYR90': (h - y, w - x)}[o]
        ax, ay = f(g.xMin(), g.yMin())
        bx, by = f(g.xMax(), g.yMax())
        return odb.Rect(b.xMin() + min(ax, bx), b.yMin() + min(ay, by), b.xMin() + max(ax, bx), b.yMin() + max(ay, by))
    insts = list(block.getInsts())
    keep, intr, drop = set(), [], []
    for i in insts:
        b = i.getBBox()
        if inside(b):
            keep.add(i.getName())
        elif overlaps(b):
            intr.append(i)
        else:
            drop.append(i)
    # an intruder (a block crossing the window edge -- e.g. a 12 mm tall KV column) keeps its in-window pins as fixed
    # terminals and its in-window body as obstructions on its OBS layers (the qwen guided cut grew the region to the
    # whole instance, which for a die-height column is the whole die height)
    stats = dict(guided=0, projected=0, nets=0, special_skipped=0, guides_kept=0, guides_clipped=0, guides_dropped=0,
                 no_track=0, track_blocked=0, guides_floating=0, nets_bbox_guide=0, guides_lifted=0,
                 intruder_pins=0, internal_nets=0, boundary_nets=0)
    nobs, ipins = 0, {}       # ipins: net name -> [(layer, rect)]
    bodies = []
    for i in insts:
        if i.getName() not in keep and i not in intr:
            continue
        m = i.getMaster()
        obsl = sorted({ob.getTechLayer().getName() for ob in m.getObstructions()
                       if ob.getTechLayer() is not None and ob.getTechLayer().getType() == 'ROUTING'}, key=lvl.get)
        b = i.getBBox()
        if any(lvl[l] >= MIN_LVL for l in obsl):
            bodies.append(dict(inst=i.getName(), master=m.getName(), kept=i.getName() in keep, obs=obsl,
                               bbox_um=[b.xMin() / dbu, b.yMin() / dbu, b.xMax() / dbu, b.yMax() / dbu]))
    # intruder body: the master's own OBS boxes (exact abstract, placed + clipped), not one full-bbox box per layer.
    # A die-level obstruction has no same-instance exemption, so on a pin layer the OBS is pulled back from every face
    # that carries in-window pins to just past the deepest pin (+0.1 um): DRT gives an instance's own pins that
    # exemption, the region cut must too (2026-10-12: full-bbox OBS over 7.8k face pins = ioedge's flat 17.6k DRC).
    intr_names = [i.getName() for i in intr]
    for i in intr:
        b = i.getBBox()
        myp = []
        for it in i.getITerms():
            net = it.getNet()
            if net is None or net.getSigType() in ('POWER', 'GROUND') or net.isSpecial():
                continue
            for mp in it.getMTerm().getMPins():
                for g in mp.getGeometry():
                    if g.getTechLayer() is None:
                        continue
                    r = place(i, g)
                    if inside(r):
                        myp.append((g.getTechLayer().getName(), r))
                        ipins.setdefault(net.getName(), []).append((g.getTechLayer().getName(), r, i.getName()))
        pull = {}
        mg = int(0.1 * dbu)
        for ln, r in myp:
            d = pull.setdefault(ln, [b.xMin(), b.yMin(), b.xMax(), b.yMax()])
            dx0, dy0, dx1, dy1 = r.xMin() - b.xMin(), r.yMin() - b.yMin(), b.xMax() - r.xMax(), b.yMax() - r.yMax()
            k = min((dx0, 0), (dy0, 1), (dx1, 2), (dy1, 3))[1]      # the face this pin sits on
            if k == 0: d[0] = max(d[0], r.xMax() + mg)
            if k == 1: d[1] = max(d[1], r.yMax() + mg)
            if k == 2: d[2] = min(d[2], r.xMin() - mg)
            if k == 3: d[3] = min(d[3], r.yMin() - mg)
        for ob in i.getMaster().getObstructions():
            L = ob.getTechLayer()
            if L is None or L.getType() != 'ROUTING' or L.getName() not in layers:
                continue
            ln = L.getName()
            r = place(i, ob)
            lx0, ly0, lx1, ly1 = pull.get(ln, [b.xMin(), b.yMin(), b.xMax(), b.yMax()])
            ox0, oy0 = max(r.xMin(), x0, lx0), max(r.yMin(), y0, ly0)
            ox1, oy1 = min(r.xMax(), x1, lx1), min(r.yMax(), y1, ly1)
            if ox1 > ox0 and oy1 > oy0:
                odb.dbObstruction_create(block, layers[ln], ox0, oy0, ox1, oy1)
                nobs += 1
    print(f'DRD window dbu=[{x0} {y0} {x1} {y1}] keep={len(keep)} intruders={len(intr)} drop={len(drop)} obs={nobs}'
          f' intruder_pin_nets={len(ipins)}', flush=True)
    grids = {}
    for n in ('M4', 'M5', 'M6', 'M7', 'M8', 'M9'):
        tg = block.findTrackGrid(layers[n])
        grids[n] = sorted(tg.getGridY() if hdir[n] else tg.getGridX())
    used = {}
    ACC = um(1.0)
    strips = {'W': (x0, y0, x0 + ACC, y1), 'E': (x1 - ACC, y0, x1, y1), 'S': (x0, y0, x1, y0 + ACC),
              'N': (x0, y1 - ACC, x1, y1)}
    blk = {}

    def add_blocker(ln, bx0, by0, bx1, by1):
        if ln not in grids:
            return
        for edge, (sx0, sy0, sx1, sy1) in strips.items():
            if hdir[ln] != (edge in ('W', 'E')) or bx0 >= sx1 or bx1 <= sx0 or by0 >= sy1 or by1 <= sy0:
                continue
            blk.setdefault((edge, ln), []).append((by0, by1) if edge in ('W', 'E') else (bx0, bx1))
    for i in insts:
        if i.getName() not in keep:
            continue
        m = i.getMaster()
        lays = {ob.getTechLayer().getName() for ob in m.getObstructions() if ob.getTechLayer() is not None}
        for mt in m.getMTerms():
            for mp in mt.getMPins():
                lays |= {g.getTechLayer().getName() for g in mp.getGeometry() if g.getTechLayer() is not None}
        b = i.getBBox()
        for ln in lays:
            add_blocker(ln, b.xMin(), b.yMin(), b.xMax(), b.yMax())
    for ob in block.getObstructions():
        b = ob.getBBox()
        add_blocker(b.getTechLayer().getName(), b.xMin(), b.yMin(), b.xMax(), b.yMax())
    for _, prs in ipins.items():
        for ln, r, _i in prs:
            add_blocker(ln, r.xMin(), r.yMin(), r.xMax(), r.yMax())
    pdn = []
    for n in block.getNets():
        if not n.isSpecial() or n.getSigType() not in ('POWER', 'GROUND'):
            continue
        for sw in n.getSWires():
            for sb in sw.getWires():
                if sb.isVia() or sb.xMax() <= x0 or sb.xMin() >= x1 or sb.yMax() <= y0 or sb.yMin() >= y1:
                    continue
                add_blocker(sb.getTechLayer().getName(), sb.xMin(), sb.yMin(), sb.xMax(), sb.yMax())
                pdn.append((sb.getTechLayer().getName(), sb.xMin(), sb.yMin(), sb.xMax(), sb.yMax()))
    blk_iv = {}
    for key, iv in blk.items():
        lay = layers[key[1]]
        g = lay.getWidth() // 2 + max(lay.getSpacing(), 0)
        merged = []
        for a_, b_ in sorted((a_ - g, b_ + g) for a_, b_ in iv):
            if merged and a_ <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], b_)
            else:
                merged.append([a_, b_])
        blk_iv[key] = ([a_ for a_, _ in merged], [b_ for _, b_ in merged])

    def blocked(edge, ln, t):
        iv = blk_iv.get((edge, ln))
        if not iv:
            return False
        k = bisect.bisect_right(iv[0], t) - 1
        return k >= 0 and t <= iv[1][k]

    def free_track(edge, ln, coord, lo, hi):
        g = grids[ln]
        s = used.setdefault((edge, ln), set())
        k = bisect.bisect_left(g, coord)
        for d in range(0, len(g)):
            hit = False
            for j in (k - d, k + d):
                if 0 <= j < len(g):
                    hit = True
                    if lo <= g[j] <= hi and j not in s:
                        if blocked(edge, ln, g[j]):
                            stats['track_blocked'] += 1
                            continue
                        s.add(j)
                        return g[j]
            if not hit:
                break
        return None

    def make_pin(net, edge, ln, t, k):
        lay = layers[ln]
        w = lay.getWidth()
        ln_len = max(4 * w, um(0.2))
        bt = odb.dbBTerm.create(net, f'{net.getName()}__drd{k}')
        bt.setIoType('INOUT')
        bp = odb.dbBPin.create(bt)
        r = {'W': (x0, t - w // 2, x0 + ln_len, t + w // 2), 'E': (x1 - ln_len, t - w // 2, x1, t + w // 2),
             'N': (t - w // 2, y1 - ln_len, t + w // 2, y1), 'S': (t - w // 2, y0, t + w // 2, y0 + ln_len)}[edge]
        odb.dbBox.create(bp, lay, *r)
        bp.setPlacementStatus('FIRM')
        return (ln, *r)

    def low_same_dir(ln):
        return 'M4' if hdir[ln] == hdir['M4'] else 'M5'
    TOUCH = um(2.0)

    def connected_guides(net, boxes, pins):
        if not boxes:
            return boxes
        n = len(boxes)
        par = list(range(n))

        def find(a_):
            while par[a_] != a_:
                par[a_] = par[par[a_]]
                a_ = par[a_]
            return a_

        def touch(p, q, g=0):
            return p[1] <= q[3] + g and q[1] <= p[3] + g and p[2] <= q[4] + g and q[2] <= p[4] + g
        for a_ in range(n):
            for b_ in range(a_ + 1, n):
                p, q = boxes[a_], boxes[b_]
                if abs(lvl.get(p[0], 0) - lvl.get(q[0], 0)) <= 1 and touch(p, q):
                    par[find(a_)] = find(b_)
        its = [it.getBBox() for it in net.getITerms() if it.getInst().getName() in keep]
        its = [('', r.xMin(), r.yMin(), r.xMax(), r.yMax()) for r in its]
        its += [('', r.xMin(), r.yMin(), r.xMax(), r.yMax()) for _, r, _i in ipins.get(net.getName(), [])]
        live = set()
        for a_ in range(n):
            if any(pn[0] == boxes[a_][0] and touch(pn, boxes[a_]) for pn in pins) or \
                    any(touch(it, boxes[a_], TOUCH) for it in its):
                live.add(find(a_))
        stats['guides_floating'] += sum(1 for a_ in range(n) if find(a_) not in live)
        boxes = [boxes[a_] for a_ in range(n) if find(a_) in live]
        if len(live) <= 1:
            return boxes
        stats['nets_bbox_guide'] += 1
        allr = [b[1:] for b in boxes] + [p[1:] for p in pins] + [i[1:] for i in its]
        bx0 = max(x0, min(r[0] for r in allr) - TOUCH)
        by0 = max(y0, min(r[1] for r in allr) - TOUCH)
        bx1 = min(x1, max(r[2] for r in allr) + TOUCH)
        by1 = min(y1, max(r[3] for r in allr) + TOUCH)
        return [(ln, bx0, by0, bx1, by1) for ln in sorted(layers, key=lambda v: lvl[v]) if MIN_LVL <= lvl[ln] <= MAX_LVL]

    gwrite, internal, keep_bt = [], [], set()
    nets_seen = set()
    region_nets = [n for n in block.getNets() if n.getSigType() not in ('POWER', 'GROUND')]
    for net in region_nets:
        nm = net.getName()
        inn = [it for it in net.getITerms() if it.getInst().getName() in keep]
        if not inn and nm not in ipins:
            continue
        if net.isSpecial():
            stats['special_skipped'] += 1
            continue
        nets_seen.add(nm)
        stats['nets'] += 1
        # outside endpoints: ITerms of instances not kept (an intruder whose pin of this net lies in the window is
        # inside: that pin is a fixed terminal) and die IO BTerms outside the window (in-window ones are kept)
        ip_insts = {iname for _, _, iname in ipins.get(nm, [])}
        outside = [ot for ot in net.getITerms()
                   if ot.getInst().getName() not in keep and ot.getInst().getName() not in ip_insts]
        for bt in net.getBTerms():
            bb = bt.getBBox()
            if inside(bb) and bt.getBPins():
                keep_bt.add(bt.getName())
            else:
                outside.append(bt)
        if not outside:
            internal.append(nm)
            stats['internal_nets'] += 1
        else:
            stats['boundary_nets'] += 1
        kept_boxes, pins, k = [], [], 0
        for ln, r, _i in ipins.get(nm, []):
            k += 1
            bt = odb.dbBTerm.create(net, f'{nm}__drdp{k}')
            bt.setIoType('INOUT')
            bp = odb.dbBPin.create(bt)
            odb.dbBox.create(bp, layers[ln], r.xMin(), r.yMin(), r.xMax(), r.yMax())
            bp.setPlacementStatus('FIRM')
            pins.append((ln, r.xMin(), r.yMin(), r.xMax(), r.yMax()))
            stats['intruder_pins'] += 1
        nguided = 0
        guides = list(net.getGuides())
        for g in guides:
            r = g.getBox()
            ln = g.getLayer().getName()
            if lvl.get(ln, 99) < MIN_LVL:
                ln = low_same_dir(ln)
                stats['guides_lifted'] += 1
                if ln != 'M4' and overlaps(r):
                    kept_boxes.append(('M4', max(r.xMin(), x0), max(r.yMin(), y0), min(r.xMax(), x1), min(r.yMax(), y1)))
            elif lvl.get(ln, 0) > MAX_LVL:
                ln = 'M9'
                stats['guides_lifted'] += 1
            if inside(r):
                kept_boxes.append((ln, r.xMin(), r.yMin(), r.xMax(), r.yMax()))
                stats['guides_kept'] += 1
                continue
            if not overlaps(r) or ln not in grids:
                stats['guides_dropped'] += 1
                continue
            cr = (max(r.xMin(), x0), max(r.yMin(), y0), min(r.xMax(), x1), min(r.yMax(), y1))
            kept_boxes.append((ln, *cr))
            stats['guides_clipped'] += 1
            if not outside:
                continue
            for edge, crossed in (('W', r.xMin() < x0), ('E', r.xMax() > x1), ('S', r.yMin() < y0),
                                  ('N', r.yMax() > y1)):
                if not crossed or hdir[ln] != (edge in ('W', 'E')):
                    continue
                lo, hi = (cr[1], cr[3]) if edge in ('W', 'E') else (cr[0], cr[2])
                w = layers[ln].getWidth()
                t = free_track(edge, ln, (lo + hi) // 2, lo + w, hi - w)
                if t is None:
                    stats['no_track'] += 1
                    continue
                k += 1
                pins.append(make_pin(net, edge, ln, t, k))
                stats['guided'] += 1
                nguided += 1
        if outside and nguided == 0:
            b = outside[0].getBBox()
            if b is not None:
                px, py = (b.xMin() + b.xMax()) // 2, (b.yMin() + b.yMax()) // 2
                dx = (x0 - px) if px < x0 else (px - x1) if px > x1 else 0
                dy = (y0 - py) if py < y0 else (py - y1) if py > y1 else 0
                edge = ('W' if px < x0 else 'E') if dx >= dy else ('S' if py < y0 else 'N')
                ln = 'M8' if edge in ('W', 'E') else 'M9'
                w = layers[ln].getWidth()
                c = min(max(py, y0 + 2 * w), y1 - 2 * w) if edge in ('W', 'E') else min(max(px, x0 + 2 * w), x1 - 2 * w)
                t = free_track(edge, ln, c, (y0 if edge in ('W', 'E') else x0) + 2 * w,
                               (y1 if edge in ('W', 'E') else x1) - 2 * w)
                if t is not None:
                    pins.append(make_pin(net, edge, ln, t, k + 1))
                    stats['projected'] += 1
        for g in guides:
            odb.dbGuide_destroy(g)
        kept_boxes = connected_guides(net, kept_boxes, pins)
        for ln, a_, b_, c, d in kept_boxes:
            gwrite.append((nm, ln, a_, b_, c, d))
    print('DRD pins/guides', json.dumps(stats), flush=True)
    # pin-access audit (ABOVE-ONLY keepout): every kept block's signal pin on layer L must have L+1 free of the
    # die's own shapes (PDN, intruder obstructions) over the pin; the tool itself never obstructs L-1.
    pa = dict(pins=0, above_blocked_pdn=0, above_blocked_obs=0, examples=[],
              intruder_pins=0, intruder_above_blocked_pdn=0, intruder_above_blocked_obs=0,
              intruder_examples=[])
    pdn_by = {}
    for ln, a_, b_, c, d in pdn:
        pdn_by.setdefault(ln, []).append((a_, b_, c, d))
    obs_by = {}
    for ob in block.getObstructions():
        bb = ob.getBBox()
        obs_by.setdefault(bb.getTechLayer().getName(), []).append((bb.xMin(), bb.yMin(), bb.xMax(), bb.yMax()))
    up = {f'M{k}': f'M{k + 1}' for k in range(1, 9)}
    for i in insts:
        if i.getName() not in keep:
            continue
        for it in i.getITerms():
            if it.getNet() is None or it.getNet().getSigType() in ('POWER', 'GROUND') or it.getNet().isSpecial():
                continue
            for mp in it.getMTerm().getMPins():
                for g in mp.getGeometry():
                    if g.getTechLayer() is None or g.getTechLayer().getName() not in up:
                        continue
                    r = place(i, g)
                    pa['pins'] += 1
                    L1 = up[g.getTechLayer().getName()]
                    for key, src in (('above_blocked_pdn', pdn_by), ('above_blocked_obs', obs_by)):
                        if any(q[0] <= r.xMin() and q[2] >= r.xMax() and q[1] <= r.yMin() and q[3] >= r.yMax()
                               for q in src.get(L1, [])):
                            pa[key] += 1
                            if len(pa['examples']) < 10:
                                pa['examples'].append([it.getInst().getName() + '/' + it.getMTerm().getName(), L1, key])
                    break
    # Intruder pins become BTerms below, so they cannot be audited as kept
    # instance ITerms. Include their original exact geometry explicitly.
    # This changes diagnostics only: never clear actual abstract OBS here.
    for nm, shapes in ipins.items():
        for ln, r, owner in shapes:
            if ln not in up:
                continue
            pa['intruder_pins'] += 1
            L1 = up[ln]
            for key, src in (('intruder_above_blocked_pdn', pdn_by),
                             ('intruder_above_blocked_obs', obs_by)):
                if any(q[0] <= r.xMin() and q[2] >= r.xMax() and
                       q[1] <= r.yMin() and q[3] >= r.yMax()
                       for q in src.get(L1, [])):
                    pa[key] += 1
                    if len(pa['intruder_examples']) < 10:
                        pa['intruder_examples'].append([owner, nm, L1, key])
    for i in drop + intr:
        odb.dbInst.destroy(i)
    for bt in list(block.getBTerms()):
        if '__drd' not in bt.getName() and bt.getName() not in keep_bt:
            odb.dbBTerm.destroy(bt)
    ndel = 0
    for n in list(block.getNets()):
        if n.getITermCount() == 0 and n.getBTermCount() == 0 and not n.isSpecial():
            odb.dbNet.destroy(n)
            ndel += 1
    psb = dict(kept=0, clipped=0, removed=0)
    for n in block.getNets():
        if not n.isSpecial():
            continue
        for sw in n.getSWires():
            for sb in list(sw.getWires()):
                r = odb.Rect(sb.xMin(), sb.yMin(), sb.xMax(), sb.yMax())
                if inside(r):
                    psb['kept'] += 1
                    continue
                if sb.isVia() or not overlaps(r):
                    odb.dbSBox_destroy(sb)
                    psb['removed'] += 1
                    continue
                lay, st = sb.getTechLayer(), sb.getWireShapeType()
                cx0, cy0, cx1, cy1 = max(r.xMin(), x0), max(r.yMin(), y0), min(r.xMax(), x1), min(r.yMax(), y1)
                odb.dbSBox_destroy(sb)
                odb.dbSBox_create(sw, lay, cx0, cy0, cx1, cy1, st)
                psb['clipped'] += 1
    rows = [(r.getName(), r.getSite(), r.getOrigin(), r.getOrient(), r.getDirection(), r.getSiteCount(), r.getSpacing())
            for r in block.getRows()]
    for r in list(block.getRows()):
        odb.dbRow.destroy(r)
    for name, site, (ox, oy), orient, direc, cnt, sp in rows:
        if oy < y0 or oy + site.getHeight() > y1:
            continue
        sx = ox + -(-(x0 - ox) // sp) * sp if x0 > ox else ox
        n = (min(x1, ox + cnt * sp) - sx) // sp
        if n > 0:
            odb.dbRow.create(block, name, site, sx, oy, orient, direc, n, sp)
    for tg in list(block.getTrackGrids()):
        lay = tg.getTechLayer()
        px = [tg.getGridPatternX(k) for k in range(tg.getNumGridPatternsX())]
        py = [tg.getGridPatternY(k) for k in range(tg.getNumGridPatternsY())]
        odb.dbTrackGrid.destroy(tg)
        ng = odb.dbTrackGrid.create(block, lay)
        for pats, lo, hi, add in ((px, x0, x1, ng.addGridPatternX), (py, y0, y1, ng.addGridPatternY)):
            for o, c, s in pats:
                no = o + -(-(lo - o) // s) * s if lo > o else o
                cnt = (hi - no) // s + 1
                if cnt > 0:
                    add(no, cnt, s)
    block.setDieArea(odb.Rect(x0, y0, x1, y1))
    block.setCoreArea(odb.Rect(x0, y0, x1, y1))
    out_dir = Path(os.environ['DRD_OUT']).parent
    with open(out_dir / 'route.guide', 'w') as f:
        cur = None
        for nn, ln, a_, b_, c, d in sorted(gwrite, key=lambda t: t[0]):
            if nn != cur:
                if cur is not None:
                    f.write(')\n')
                f.write(f'{nn}\n(\n')
                cur = nn
            f.write(f'{a_} {b_} {c} {d} {ln}\n')
        if cur is not None:
            f.write(')\n')
    (out_dir / 'internal_nets.txt').write_text('\n'.join(sorted(internal)) + '\n')
    out = {'win_um': reg['win'], 'region_um': [x0 / dbu, y0 / dbu, x1 / dbu, y1 / dbu], 'dbu': dbu,
           'area_mm2': (x1 - x0) * (y1 - y0) / dbu / dbu / 1e6, 'kept_instances': len(keep),
           'intruders': intr_names[:200], 'n_intruders': len(intr), 'obstructions': nobs,
           'pins_guides': stats, 'pdn_clip': psb, 'nets_removed': ndel, 'region_nets': len(nets_seen),
           'pin_access_above_only': pa, 'hard_bodies': bodies, 'kept_masters': {}}
    for i in block.getInsts():
        m = i.getMaster().getName()
        out['kept_masters'][m] = out['kept_masters'].get(m, 0) + 1
    Path(os.environ['DRD_OUT'] + '.json').write_text(json.dumps(out, indent=1))
    odb.write_db(block.getDataBase(), os.environ['DRD_OUT'])
    print('DRD_CUT_DONE', json.dumps({k: v for k, v in out.items() if k not in ('hard_bodies', 'intruders')}))


# -------------------------------------------------------------------------------------------------- tcl templates
HEAD = r"""proc mem {tag} { set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {VmRSS:\s+(\d+)} $s -> r; regexp {VmHWM:\s+(\d+)} $s -> h
  puts "OTMEM $tag rss_mb=[expr {$r/1024}] hwm_mb=[expr {$h/1024}] t=[clock seconds]"; flush stdout }
proc step {name body} { set t0 [clock milliseconds]
  if {[catch {uplevel 1 $body} err]} { puts "OT_STEP_FAIL $name $err"; flush stdout }
  puts "OT_TIME step=$name s=[format %.1f [expr {([clock milliseconds]-$t0)/1000.0}]]"; mem $name }
"""
NLDM = '/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM'
CELL_LIBS = ['AO_RVT_{C}_nldm_211120.lib.gz', 'INVBUF_RVT_{C}_nldm_220122.lib.gz', 'OA_RVT_{C}_nldm_211120.lib.gz',
             'SEQ_RVT_{C}_nldm_220123.lib', 'SIMPLE_RVT_{C}_nldm_211120.lib.gz']


def drt_tcl(threads, iters):
    return HEAD + f"""set_thread_count {threads}
step load {{ read_db /work/region.odb }}
read_liberty {NLDM}/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
# layer contract: die nets on M4-M9 (block OBS own M1-M7 over every body, so only M8/M9 cross a block)
set_routing_layers -signal M4-M9 -clock M4-M9
step guides {{ read_guides /work/route.guide }}
step wl_grt {{ report_wire_length -net * -global_route -file /work/wl_grt.csv }}
step drt {{ detailed_route -output_drc /work/drt_drc.rpt -verbose 1 -droute_end_iter {iters} -drc_report_iter_step 1 }}
step write_odb {{ write_db /work/routed.odb }}
step write_def {{ write_def /work/routed.def }}
step wl_drt {{ report_wire_length -net * -detailed_route -file /work/wl_drt.csv }}
step rcx {{ define_process_corner -ext_model_index 0 X
  extract_parasitics -ext_model_file /OpenROAD-flow-scripts/flow/platforms/asap7/rcx_patterns.rules }}
step write_spef {{ write_spef /work/routed.spef }}
puts OT_FLOW_DONE
"""


def sta_tcl(corner, para):
    """TT setup / FF hold on the window's internal nets: GRT side = the die GRT SPEF of record filtered to them,
    RCX side = extraction of the detailed route.  Clocks: the die clock plan's per-sink latencies (clock_lat_<c>.tcl
    of the die STA), each sink pin a clock source with that latency (the die clock tree is not in the window)."""
    c, C = corner, corner.upper()
    chk = 'max' if c in ('ss', 'tt') else 'min'
    libs = '\n'.join(f'read_liberty {NLDM}/asap7sc7p5t_{f.format(C=C)}' for f in CELL_LIBS)
    load = 'step load { read_db /work/region.odb }\nstep spef { read_spef /work/grt_internal.spef }\n' if para == 'grt' \
        else 'step load { read_db /work/routed.odb }\nstep spef { read_spef /work/routed.spef }\n'
    return HEAD + f"""step libs {{
foreach f [lsort [glob -nocomplain /work/libs/*_{c}.lib]] {{ read_liberty $f }}
{libs}
}}
{load}source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set lat {{}}
set fh [open /work/clock_lat_{c}.tcl]
while {{[gets $fh line] >= 0}} {{
  if {{[regexp {{get_pins -quiet \\{{([^\\}}]+)\\}}.*set_clock_latency ([-0-9.]+)}} $line -> pn v]}} {{ lappend lat $pn $v }}
  if {{[regexp {{^set_clock_latency ([-0-9.]+) \\[get_pins -quiet \\{{([^\\}}]+)\\}}}} $line -> v pn]}} {{ lappend lat $pn $v }}
}}
close $fh
set sp {{}}; set hp {{}}
foreach {{pn v}} $lat {{ set p [get_pins -quiet $pn]; if {{[llength $p]}} {{
  if {{[regexp {{/hclk$|pll_hbm}} $pn]}} {{ lappend hp $p }} else {{ lappend sp $p }} }} }}
# sinks the die clock plan does not list (kept relay macros, whose clock comes from the die tree that is not in the
# window): ideal stream clock, the same on the GRT and RCX side, so the RCX-GRT delta stays a wire-only delta
set have {{}}; foreach p [concat $sp $hp] {{ dict set have [get_full_name $p] 1 }}
set ip 0
foreach p [get_pins -quiet -hierarchical {{*/ck */ck\\[0\\] */clk */CLK */clk_i}}] {{
  if {{![dict exists $have [get_full_name $p]]}} {{ lappend sp $p; incr ip }} }}
puts "OT_CLOCK_SINKS stream=[llength $sp] hclk=[llength $hp] ideal_unplanned=$ip"
if {{[llength $sp]}} {{ create_clock -name stream -period 833.333 $sp }}
if {{[llength $hp]}} {{ create_clock -name hclk -period 1024 $hp; set_clock_groups -asynchronous -group stream -group hclk }}
foreach {{pn v}} $lat {{ set p [get_pins -quiet $pn]; if {{[llength $p]}} {{ set_clock_latency -source $v $p }} }}
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
step sta {{
  report_checks -path_delay {chk} -group_path_count 1000000 -endpoint_path_count 1 -unique_paths_to_endpoint -format end > /work/sta_{para}_{c}_ends.rpt
  report_checks -path_delay {chk} -group_path_count 3 -fields {{slew cap input_pins nets}} -digits 1 > /work/sta_{para}_{c}_paths.rpt
  report_worst_slack -{chk}; report_tns
}}
puts OT_STA_DONE
"""


def stage(a):
    a.out.mkdir(parents=True, exist_ok=True)
    win = [float(v) for v in a.win.split(',')]
    (a.out / 'region.json').write_text(json.dumps({'win': win, 'name': a.out.name, 'ckpt': a.ckpt,
                                                   'spef': a.spef, 'libs': a.libs, 'clock_lat': a.clock_lat}))
    (a.out / 'region_drt.py').write_text(Path(__file__).read_text())
    (a.out / 'drt.tcl').write_text(drt_tcl(a.threads, a.drt_iters))
    corners = ('tt', 'ff')
    for c in corners:
        for p in ('grt', 'rcx'):
            (a.out / f'sta_{p}_{c}.tcl').write_text(sta_tcl(c, p))
    img = '${IMAGE:-openroad/orfs:asap7lock}'
    run = lambda tag, cmd, mem, cpus: (  # noqa: E731
        f'docker run --rm --name drd_${{N}}_{tag} --cpus={cpus} --memory={mem}g -v $(pwd):/work -w /work {img} '
        f'bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v {cmd} > /work/{tag}.log 2>&1;'
        f' rc=\\$?; chmod -R a+rwX /work; exit \\$rc"; echo $? > {tag}.exit; S {tag} rc=$(cat {tag}.exit)')
    # --clock-lat: a dir holding clock_lat_<c>.tcl, or a path pattern with {c} (e.g. kit/latency_{c}.tcl)
    lat = ' '.join(f'cp -f {a.clock_lat.format(c=c) if "{c}" in a.clock_lat else Path(a.clock_lat) / f"clock_lat_{c}.tcl"}'
                   f' clock_lat_{c}.tcl;' for c in corners) if a.clock_lat else ''
    # --libs: a dir of *_<c>.lib, or a lib-list pattern with {c} (one path per line; '/kit/' = the list's own dir)
    if '{c}' in a.libs:
        libcp = []
        for c in corners:
            lf = Path(a.libs.format(c=c))
            for ln in lf.read_text().split():
                src = str(lf.parent / ln[5:]) if ln.startswith('/kit/') else ln
                libcp.append(f'cp -f {src} libs/{Path(src).name.replace(".lib", "")}__{c}_{c}.lib;'
                             if not src.endswith(f'_{c}.lib') else f'cp -f {src} libs/;')
        libs_sh = ' '.join(libcp)
    else:
        libs_sh = f'cp -f {a.libs}/*_tt.lib {a.libs}/*_ff.lib libs/ 2>/dev/null;' if a.libs else ''
    (a.out / 'start_region.sh').write_text(f"""#!/bin/bash
# die-region DRT: cut from the die GRT checkpoint -> DRT on the clipped die guides -> RCX -> STA GRT / RCX -> compare
set -u
cd $(dirname $(readlink -f $0))
N=$(basename $(dirname $(pwd)))_$(basename $(pwd))
S() {{ echo "$(date '+%F %T %Z') $*" >> STATUS.log; }}
S start
mkdir -p libs; {libs_sh} {lat}
ln -f {a.ckpt} ckpt_grt.odb 2>/dev/null || cp -f {a.ckpt} ckpt_grt.odb
[ -s region.odb ] || {{ {run('cut', 'openroad -python -exit /work/region_drt.py', a.mem, 8).replace('docker run', 'docker run -e DRD_IN=/work/ckpt_grt.odb -e DRD_OUT=/work/region.odb -e DRD_REGION_JSON=/work/region.json')}; }}
rm -f ckpt_grt.odb
[ -s region.odb ] || {{ S cut FAILED; exit 1; }}
{'python3 region_drt.py spef --spef ' + a.spef + ' --nets internal_nets.txt --out grt_internal.spef; S spef rc=$?' if a.spef else ''}
[ -s routed.odb ] || {{ {run('drt', f'openroad -threads {a.threads} -no_init -exit /work/drt.tcl', a.mem, a.threads)}; }}
for t in {' '.join(f'sta_grt_{c} sta_rcx_{c}' for c in corners)}; do
  {run('$t', 'openroad -threads 8 -no_init -exit /work/$t.tcl', 120, 8).replace('{tag}', '$t')}
done
python3 region_drt.py compare --dir . > compare.log 2>&1; S compare rc=$?
S done
""")
    os.chmod(a.out / 'start_region.sh', 0o755)
    print(a.out)


# ------------------------------------------------------------------------------------------------------ host post
def spef_filter(a):
    """keep the header, the name map and the *D_NET sections of the listed nets (names unescaped)"""
    keep = set(Path(a.nets).read_text().split())
    nm, buf, keepit, kept, tot = {}, None, False, 0, 0
    with open(a.spef) as f, open(a.out, 'w') as out:
        for ln in f:
            if ln.startswith('*D_NET'):
                if buf is not None and keepit:
                    out.writelines(buf)
                    kept += 1
                tot += 1
                tok = ln.split()[1]
                keepit = nm.get(tok, tok).replace('\\', '') in keep
                buf = [ln]
            elif buf is not None:
                buf.append(ln)
            else:
                s = ln.split(None, 1)
                if len(s) == 2 and s[0].startswith('*') and s[0][1:].isdigit():
                    nm[s[0]] = s[1].strip()
                out.write(ln)
        if buf is not None and keepit:
            out.writelines(buf)
            kept += 1
    print(f'DRD spef kept {kept} / {tot} nets (internal list {len(keep)})')


def parse_def_routes(path):
    """per net: {layer: length um}, vias; from a routed DEF NETS section"""
    units, nets, cur = 1000, {}, None
    lay = None
    last = None
    in_nets = False
    with open(path) as f:
        for ln in f:
            if ln.startswith('UNITS'):
                units = int(ln.split()[3])
            if ln.startswith('NETS'):
                in_nets = True
                continue
            if not in_nets:
                continue
            if ln.startswith('END NETS'):
                break
            s = ln.strip()
            if s.startswith('- '):
                cur = s.split()[1].replace('\\', '')
                nets[cur] = {'wl': {}, 'vias': 0, 'segs': []}
                continue
            if cur is None:
                continue
            m = re.search(r'(?:ROUTED|NEW)\s+(M\d+)\s+(.*)', s)
            if not m:
                continue
            lay, rest = m.group(1), m.group(2)
            pts = re.findall(r'\(\s*(-?\d+|\*)\s+(-?\d+|\*)(?:\s+-?\d+)?\s*\)', rest)
            last = None
            seq = []
            for px, py in pts:
                x = last[0] if px == '*' else int(px)
                y = last[1] if py == '*' else int(py)
                seq.append((x, y))
                last = (x, y)
            for p, q in zip(seq, seq[1:]):
                L = (abs(p[0] - q[0]) + abs(p[1] - q[1])) / units
                nets[cur]['wl'][lay] = nets[cur]['wl'].get(lay, 0) + L
                nets[cur]['segs'].append((lay, min(p[0], q[0]) / units, min(p[1], q[1]) / units,
                                          max(p[0], q[0]) / units, max(p[1], q[1]) / units))
            tail = rest.split(')')[-1].strip()
            if tail and not tail.startswith('RECT') and re.match(r'[A-Za-z]', tail):
                nets[cur]['vias'] += 1
    return nets


def compare(a):
    import statistics as st
    d = Path(a.dir)
    cutj = json.loads((d / 'region.odb.json').read_text())
    out = {'window': cutj['win_um'], 'kept_instances': cutj['kept_instances'], 'region_nets': cutj['region_nets'],
           'pins_guides': cutj['pins_guides'], 'pin_access_above_only': {k: v for k, v in
                                                                         cutj['pin_access_above_only'].items()}}
    # DRC
    drc = {}
    if (d / 'drt_drc.rpt').exists():
        t = (d / 'drt_drc.rpt').read_text()
        for m in re.finditer(r'violation type: (.*?)\n.*?on Layer (\S+)', t, re.S):
            k = f'{m.group(1).strip()}@{m.group(2)}'
            drc[k] = drc.get(k, 0) + 1
    out['drc_total'] = sum(drc.values())
    out['drc_classes'] = dict(sorted(drc.items(), key=lambda kv: -kv[1]))
    log = (d / 'drt.log').read_text(errors='replace') if (d / 'drt.log').exists() else ''
    out['drt_iterations'] = [int(v) for v in re.findall(r'Number of violations = (\d+)', log)]
    # GRT side from the clipped guides
    units = cutj.get('dbu', 1000)
    grt = {}
    for net, boxes in parse_guides(d / 'route.guide', units):
        wl, vias = {}, 0
        for l, x0, y0, x1, y1 in boxes:
            wl[l] = wl.get(l, 0) + (x1 - x0 if HDIR.get(l, True) else y1 - y0)
        for i, p in enumerate(boxes):
            for q in boxes[i + 1:]:
                if abs(LV.get(p[0], 0) - LV.get(q[0], 0)) == 1 and p[1] <= q[3] and q[1] <= p[3] and p[2] <= q[4] \
                        and q[2] <= p[4]:
                    vias += 1
        grt[net] = {'wl': wl, 'vias': vias}
    drt = parse_def_routes(d / 'routed.def') if (d / 'routed.def').exists() else {}
    # per-net totals from OpenROAD's own reports (report_wire_length) when present
    def rwl(p):
        r = {}
        if p.exists():
            for ln in p.read_text().splitlines()[1:]:
                s = ln.split()
                if len(s) >= 3:
                    try:
                        r[s[1]] = float(s[2])
                    except ValueError:
                        pass
        return r
    g_tot, d_tot = rwl(d / 'wl_grt.csv'), rwl(d / 'wl_drt.csv')
    common = [n for n in g_tot if n in d_tot and g_tot[n] > 0]
    rel = [(d_tot[n] - g_tot[n]) / g_tot[n] for n in common if g_tot[n] >= 20]
    out['wirelength'] = {
        'nets_compared': len(common), 'grt_um': round(sum(g_tot[n] for n in common), 1),
        'drt_um': round(sum(d_tot[n] for n in common), 1),
        'ratio_total': round(sum(d_tot[n] for n in common) / max(1e-9, sum(g_tot[n] for n in common)), 4),
        'per_net_rel_median': round(st.median(rel), 4) if rel else None,
        'per_net_rel_p95_abs': round(sorted(abs(v) for v in rel)[int(0.95 * (len(rel) - 1))], 4) if rel else None,
        'per_net_rel_max': round(max(rel), 4) if rel else None,
        'note': 'nets with GRT length >= 20 um for the per-net statistics; GRT = report_wire_length -global_route on '
                'the clipped die guides'}
    lay_g, lay_d = {}, {}
    for n in grt:
        for l, v in grt[n]['wl'].items():
            lay_g[l] = lay_g.get(l, 0) + v
    for n in drt:
        for l, v in drt[n]['wl'].items():
            lay_d[l] = lay_d.get(l, 0) + v
    out['per_layer_um'] = {l: {'grt_guides': round(lay_g.get(l, 0), 1), 'drt': round(lay_d.get(l, 0), 1)}
                           for l in sorted(set(lay_g) | set(lay_d), key=lambda v: LV.get(v, 0))}
    vg = sum(grt[n]['vias'] for n in grt if n in drt)
    vd = sum(drt[n]['vias'] for n in drt if n in grt)
    out['vias'] = {'grt_layer_changes': vg, 'drt_vias': vd, 'ratio': round(vd / vg, 3) if vg else None,
                   'note': 'GRT = touching adjacent-layer guide pairs (one per layer change); DRT = via instances in '
                           'the routed DEF (each via of a stack counted)'}
    # layer contract: die-net metal on M4-M7 inside a hard-block body that owns that layer
    viol, over = [], {}
    bodies = cutj.get('hard_bodies', [])
    for n, v in drt.items():
        for l, sx0, sy0, sx1, sy1 in v['segs']:
            for b in bodies:
                bx = b['bbox_um']
                if sx0 >= bx[0] and sx1 <= bx[2] and sy0 >= bx[1] and sy1 <= bx[3] and sx1 > sx0 - 1 and \
                        (sx1 - sx0 + sy1 - sy0) > 0:
                    if l in b['obs']:
                        viol.append([n, l, b['inst']])
                    over[l] = over.get(l, 0) + (sx1 - sx0 + sy1 - sy0)
                    break
    out['layer_contract'] = {'die_metal_inside_block_obs_layers': len(viol), 'examples': viol[:10],
                             'die_metal_over_blocks_um': {k: round(v, 1) for k, v in sorted(over.items())},
                             'rule': 'die nets M4-M9; over a hard block only layers above its OBS (M8/M9)'}
    # STA error bar
    def ends(p):
        r = {}
        if not p.exists():
            return r
        for ln in p.read_text().splitlines():
            s = ln.split()
            if len(s) >= 4 and '/' in s[0]:
                try:
                    r[s[0]] = float(s[-2])
                except ValueError:
                    pass
        return r
    relay_pat = re.compile(a.relay_re)
    sta = {}
    for c in ('tt', 'ff'):
        g, r = ends(d / f'sta_grt_{c}_ends.rpt'), ends(d / f'sta_rcx_{c}_ends.rpt')
        com = [e for e in g if e in r]
        rl = [e for e in com if relay_pat.search(e.split('/')[0])]
        dl = [r[e] - g[e] for e in com]
        dr = [r[e] - g[e] for e in rl]
        sta[c] = {'check': 'setup' if c == 'tt' else 'hold', 'endpoints_grt': len(g), 'endpoints_rcx': len(r),
                  'common': len(com), 'wns_grt': min(g.values()) if g else None,
                  'wns_rcx': min(r.values()) if r else None,
                  'delta_rcx_minus_grt_ps': {'mean': round(st.mean(dl), 2) if dl else None,
                                             'min': round(min(dl), 2) if dl else None,
                                             'max': round(max(dl), 2) if dl else None},
                  'relay_endpoints': len(rl),
                  'relay_delta_ps': {'mean': round(st.mean(dr), 2) if dr else None,
                                     'min': round(min(dr), 2) if dr else None,
                                     'max': round(max(dr), 2) if dr else None}}
    out['sta'] = sta
    # wire-only parasitic error bar (works when the window has no clocked sinks, e.g. clockless relay abstracts):
    # total net capacitance, die GRT SPEF of record vs RCX of the detailed route, internal nets
    def spef_caps(p):
        caps, nm = {}, {}
        if not p.exists():
            return caps
        sc = 1.0
        for ln in open(p, errors='replace'):
            if ln.startswith('*C_UNIT'):
                f = ln.split(); sc = float(f[1]) * {'PF': 1000.0, 'FF': 1.0}.get(f[2].upper(), 1.0)
            elif ln.startswith('*') and ln[1:2].isdigit():
                k, v = ln.split(None, 1); nm[k] = v.strip()
            elif ln.startswith('*D_NET'):
                f = ln.split(); caps[nm.get(f[1], f[1])] = float(f[2]) * sc
        return caps
    cg, cr = spef_caps(d / 'grt_internal.spef'), spef_caps(d / 'routed.spef')
    rel = sorted((cr[n] - cg[n]) / cg[n] for n in cg if n in cr and cg[n] > 0.5)
    out['net_cap'] = {'nets': len(rel), 'grt_total_ff': round(sum(cg[n] for n in cg if n in cr), 1),
                      'rcx_total_ff': round(sum(cr[n] for n in cg if n in cr), 1),
                      'rel_median': round(rel[len(rel) // 2], 4) if rel else None,
                      'rel_p05': round(rel[len(rel) // 20], 4) if rel else None,
                      'rel_p95': round(rel[(len(rel) * 19) // 20], 4) if rel else None,
                      'note': 'internal nets with GRT cap > 0.5 fF; (RCX - GRT) / GRT'}
    (d / 'compare.json').write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ('drc_total', 'drt_iterations', 'wirelength', 'vias', 'layer_contract', 'sta', 'net_cap')}, indent=1))


def main():
    if os.environ.get('DRD_IN'):
        cut()
        return
    import argparse
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('pick')
    p.add_argument('--guide', required=True)
    p.add_argument('--def', dest='def_', required=True, help='placed die DEF (COMPONENTS + DIEAREA)')
    p.add_argument('--lef', nargs='+', required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--win-um', type=float, default=600)
    p.add_argument('--bin-um', type=float, default=50)
    p.add_argument('--margin-um', type=float, default=30)
    p.add_argument('--max-win-um', type=float, default=1500, help='relay window: skip nets longer than this')
    p.add_argument('--skip-net-re', default=r'(^|_)(clk|ck|rst|refclk|reset)', help='nets never picked as links')
    p.add_argument('--congestion-rpt', default='', help='die GRT congestion report (overflow gcells)')
    p.add_argument('--io-master-re', default=r'phy|serdes|ucie', help='IO-edge masters')
    s = sub.add_parser('stage')
    s.add_argument('--ckpt', required=True, help='die GRT checkpoint on the host (ckpt_grt.odb)')
    s.add_argument('--spef', default='', help='die GRT SPEF of record (STA on GRT parasitics)')
    s.add_argument('--libs', default='', help='dir with the die STA element libs (*_tt.lib / *_ff.lib)')
    s.add_argument('--clock-lat', default='', help='dir with the die STA clock_lat_<c>.tcl')
    s.add_argument('--out', type=Path, required=True)
    s.add_argument('--win', required=True, help='x_lo,y_lo,x_hi,y_hi (um)')
    s.add_argument('--threads', type=int, default=24)
    s.add_argument('--mem', type=int, default=200)
    s.add_argument('--drt-iters', type=int, default=64)
    f = sub.add_parser('spef')
    f.add_argument('--spef', required=True)
    f.add_argument('--nets', required=True)
    f.add_argument('--out', required=True)
    c = sub.add_parser('compare')
    c.add_argument('--dir', required=True)
    c.add_argument('--relay-re', default=r'(^|_)rly|relay|__r\d')
    a = ap.parse_args()
    {'pick': pick, 'stage': stage, 'spef': spef_filter, 'compare': compare}[a.cmd](a)


if __name__ == '__main__':
    main()
