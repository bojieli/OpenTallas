#!/usr/bin/env python3
"""S81 die c5 diagnosis (2026-10-13): where the GRT overflow sits and which nets make it.

Inputs (one die-iter case directory, read-only):
  grt/route.guide, grt/wirelength_grt.csv, grt/*.lef, a_real/floorplan_placed.def
  --ov       per-gcell overflow dump (tools/s81/c5diag_gcell_ov_dump.tcl on grt/ckpt_grt.odb)
  --regions  generator region geometry (tools/s81/c5diag_regions.py), classified like dsrom_s81_fulldie.where()

Method
  overflow    per gcell, layers M6..M9 (M4 = 0 and M5 = 74 in the GRT log, not mapped): the checkpoint's GCell grid holds
              capacity = raw tracks and usage = (net usage + reductions) mod 256; the net usage is rebuilt from the
              guides (edge e of a box belongs to gcell e) and the stored usage unwrapped with it; overflow =
              max(0, unwrapped usage - raw tracks).  The per-layer sums are compared with the GRT log by the caller
  regions     where()-name of the gcell centre; covering die instance (instances >= 0.25 mm2 by name, smaller by kind)
  attribution a net is booked on an overflowed gcell of layer L when one of its guide boxes on L uses that gcell's edge;
              the gcell's overflow is split equally over the nets booked on it (so a family's share is its share of
              the wires in the overflowed gcells, not a causal claim)
  lengths     manh = driver pin -> farthest sink pin Manhattan (LEF pin centres, DEF placement); wl = GRT wirelength
  families    family = net base name with every digit run -> '#'; bus = family without the relay-hop suffix
              (_g#_..., _d#, _y#); pair = driver kind -> sink kind; ep = hop-lint endpoint pattern (inst.pin -> inst.pin)

usage: c5diag_congestion.py --case DIR --ov gcell_ov.txt --regions regions.json --out out.json [--cache DIR]
                            [--focus NAME=REGEX ...]
"""
import argparse
import glob
import json
import os
import pickle
import re
import sys
import time
from array import array
from collections import Counter

import numpy as np

LAYERS = ['M4', 'M5', 'M6', 'M7', 'M8', 'M9']
HORIZ = {'M4': 1, 'M5': 0, 'M6': 1, 'M7': 0, 'M8': 1, 'M9': 0}
MAPPED = ('M6', 'M7', 'M8', 'M9')
T0 = time.time()


def log(*a):
    print('[%6.0f s]' % (time.time() - T0), *a, flush=True)


KIND_PREFIX = (('dsfd_rly_', 'rly'), ('dsfd_stnh', 'stn'), ('dsfd_stnv', 'stn'), ('dsfd_hstn', 'hstn'), ('dsfd_sstn', 'sstn'),
               ('dsfd_rstg', 'rstg'), ('dsfd_node_', 'node'), ('dsfd_xstg', 'xstg'), ('ot_rom_', 'rom'),
               ('dsfd_qbank', 'qbank'), ('ot_v41_rom_elem_q', 'q_elem'))
RELAY_KINDS = ('rly', 'stn', 'hstn', 'sstn', 'rstg', 'xstg')
OUT_NAMES = ('o', 'do0', 'fo0', 'dq')


def kind(master):
    for p, k in KIND_PREFIX:
        if master.startswith(p):
            return k
    return re.sub(r'\d+', '#', master.split('__')[0].replace('dsfd_', ''))


def read_lefs(paths):
    size, pins = {}, {}
    for lef in paths:
        m = pin = d = None
        for line in open(lef):
            s = line.split()
            if not s:
                continue
            k = s[0]
            if k == 'MACRO':
                m = s[1]
                pins[m] = {}
            elif m is None:
                continue
            elif k == 'SIZE':
                size[m] = (float(s[1]), float(s[3]))
            elif k == 'PIN':
                pin, d = s[1], '?'
            elif k == 'DIRECTION' and pin is not None:
                d = s[1][0]
            elif k == 'RECT' and pin is not None and pin not in pins[m]:
                pins[m][pin] = ((float(s[1]) + float(s[3])) / 2, (float(s[2]) + float(s[4])) / 2, d)
            elif k == 'OBS':
                pin = None
            elif k == 'END' and len(s) > 1:
                if s[1] == pin:
                    pin = None
                elif s[1] == m:
                    m = None
    return size, pins


class Intern:
    def __init__(self):
        self.d, self.l = {}, []

    def __call__(self, s):
        i = self.d.get(s)
        if i is None:
            i = self.d[s] = len(self.l)
            self.l.append(s)
        return i


def bus_of(fam):
    b = re.sub(r'_g#_.*$', '', fam)
    return re.sub(r'(_[dy]#)+$', '', b)


def parse_def(path, size, pins):
    comp = {}
    sec, buf = None, ''
    names = {}
    fam_i, pair_i, ep_i = Intern(), Intern(), Intern()
    a_fam, a_pair, a_ep, a_manh, a_np, a_relay = array('i'), array('i'), array('i'), array('f'), array('B'), array('B')
    base_fam = {}
    strip = re.compile(r'\d+')
    conn_re = re.compile(r'\(\s*(\S+)\s+(\S+)\s*\)')
    comp_re = re.compile(r'\s*-\s+(\S+)\s+(\S+).*?(?:PLACED|FIXED)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*(\S+)', re.S)
    dbu = 1000.0

    def loc(c, pin):
        mm, x, y, o, w, h, _ = c
        p = pins.get(mm, {}).get(pin)
        px, py, d = p if p else (w / 2, h / 2, '?')
        if o == 'S':
            px, py = w - px, h - py
        elif o == 'FN':
            px = w - px
        elif o == 'FS':
            py = h - py
        return x + px, y + py, d

    for line in open(path):
        if sec is None:
            if line.startswith('UNITS DISTANCE MICRONS'):
                dbu = float(line.split()[3])
            elif line.startswith('COMPONENTS'):
                sec = 'C'
            elif line.startswith('NETS'):
                sec = 'N'
                log('components', len(comp))
            continue
        if sec == 'C':
            if line.startswith('END COMPONENTS'):
                sec = None
                continue
            buf += line
            if ';' in line:
                mt = comp_re.match(buf)
                if mt:
                    mm = mt.group(2)
                    w, h = size.get(mm, (0.0, 0.0))
                    o = mt.group(5)
                    if o in ('E', 'W', 'FE', 'FW'):
                        w, h = h, w
                    comp[mt.group(1)] = (mm, int(mt.group(3)) / dbu, int(mt.group(4)) / dbu, o, w, h, kind(mm))
                buf = ''
            continue
        if line.startswith('END NETS'):
            break
        buf += line
        if not line.rstrip().endswith(';'):
            continue
        mt = re.match(r'\s*-\s+(\S+)', buf)
        conns = conn_re.findall(buf.split('+')[0])
        buf = ''
        if not mt:
            continue
        name = mt.group(1)
        base = name.split('[')[0]
        f = base_fam.get(base)
        if f is None:
            f = base_fam[base] = fam_i(strip.sub('#', base))
        pts = []
        for inst, pin in conns:
            c = comp.get(inst)
            if c is None:
                continue
            x, y, d = loc(c, pin)
            pts.append((d, x, y, inst, pin, c[6]))
        # the generated LEFs declare every pin INOUT: a 2-pin net needs no direction; on a multi-pin net the driver is
        # the single pin with an output name (o / do0 / fo0 / dq), else the hop is the largest pin-to-pin distance
        drv = next((p for p in pts if p[0] == 'O'), None)
        unk = 0
        if drv is None and pts:
            cand = [p for p in pts if p[4].split('[')[0] in OUT_NAMES]
            drv = cand[0] if len(cand) == 1 else None
        L, far = 0.0, None
        if drv is None and len(pts) == 2:
            drv = pts[0]
        if drv is None and len(pts) > 2:
            unk = 4
            if len(pts) <= 12:
                for n_, p in enumerate(pts):
                    for q in pts[n_ + 1:]:
                        dd = abs(p[1] - q[1]) + abs(p[2] - q[2])
                        if far is None or dd > L:
                            L, drv, far = dd, p, q
            else:
                xs, ys = [p[1] for p in pts], [p[2] for p in pts]
                L = max(xs) - min(xs) + max(ys) - min(ys)
                drv, far = pts[0], pts[-1]
        elif drv is not None:
            for p in pts:
                if p is drv:
                    continue
                dd = abs(p[1] - drv[1]) + abs(p[2] - drv[2])
                if far is None or dd > L:
                    L, far = dd, p
        if far is not None:
            pr = pair_i(drv[5] + ' -> ' + far[5])
            ep = ep_i(strip.sub('#', drv[3]) + '.' + drv[4].split('[')[0] + ' -> ' + strip.sub('#', far[3]) + '.' + far[4].split('[')[0])
            rel = (drv[5] in RELAY_KINDS) + 2 * (far[5] in RELAY_KINDS) + unk
        else:
            pr = pair_i((drv[5] if drv else 'port') + ' -> (none)')
            ep = ep_i((strip.sub('#', drv[3]) + '.' + drv[4].split('[')[0]) if drv else 'port')
            rel = 0
        names[name] = len(a_fam)
        a_fam.append(f)
        a_pair.append(pr)
        a_ep.append(ep)
        a_manh.append(L)
        a_np.append(min(255, len(pts)))
        a_relay.append(rel)
    log('nets', len(a_fam), 'families', len(fam_i.l), 'bases', len(base_fam))
    nb = Counter(base_fam.values())
    return dict(comp=comp, names=names, fams=fam_i.l, pairs=pair_i.l, eps=ep_i.l, fam=np.frombuffer(a_fam, dtype=np.int32).copy(),
                pair=np.frombuffer(a_pair, dtype=np.int32).copy(), ep=np.frombuffer(a_ep, dtype=np.int32).copy(),
                manh=np.frombuffer(a_manh, dtype=np.float32).copy(), npin=np.frombuffer(a_np, dtype=np.uint8).copy(),
                relay=np.frombuffer(a_relay, dtype=np.uint8).copy(),
                fam_bases=np.array([nb.get(i, 0) for i in range(len(fam_i.l))], dtype=np.int64))


def read_ov(path, nx_hint=None):
    """gcell dump: grid, 480-um aggregates (raw odb values) and the full M6..M9 capacity / usage rows"""
    gx = gy = None
    C, U = {}, {}
    for ln in open(path):
        k = ln[0]
        if k in 'CU' and ln[1] == ' ':
            f = ln.split()
            (C if k == 'C' else U).setdefault(f[1], {})[int(f[2])] = np.array(f[3:], dtype=np.int16)
        elif ln.startswith('GRIDX'):
            gx = [int(v) for v in ln.split()[1].split(',')]
        elif ln.startswith('GRIDY'):
            gy = [int(v) for v in ln.split()[1].split(',')]
    full = {l: (np.stack([C[l][j] for j in range(len(gy))]), np.stack([U[l][j] for j in range(len(gy))])) for l in C}
    return gx, gy, full


def read_guides(path, names, step):
    lidx = {l: n for n, l in enumerate(LAYERS)}
    bn, bl, x0, y0, x1, y1 = array('i'), array('b'), array('h'), array('h'), array('h'), array('h')
    net = -1
    nnet = miss = 0
    for line in open(path):
        c = line[0]
        if c == '(' or c == ')':
            continue
        f = line.split()
        if len(f) == 1:
            net = names.get(f[0], -1)
            miss += net < 0
            nnet += 1
            continue
        li = lidx.get(f[4])
        if li is None or net < 0:
            continue
        bn.append(net)
        bl.append(li)
        x0.append(int(f[0]) // step)
        y0.append(int(f[1]) // step)
        x1.append(-(-int(f[2]) // step))
        y1.append(-(-int(f[3]) // step))
    log('guide nets', nnet, 'boxes', len(bn), 'guide nets not in DEF', miss)
    g = lambda a_, t: np.frombuffer(a_, dtype=t).copy()
    return dict(net=g(bn, np.int32), layer=g(bl, np.int8), i0=g(x0, np.int16), j0=g(y0, np.int16), i1=g(x1, np.int16), j1=g(y1, np.int16),
                stats=dict(guide_nets=nnet, guide_boxes=len(bn), guide_nets_not_in_def=int(miss)))


def edge_usage(G, li, nx, ny):
    """nets per gcell edge of layer li from the guide boxes: a box spanning gcells a..b (inclusive) along the layer's
    direction books the edges a..b-1, edge e belonging to gcell e (FastRoute h_edges[y][x] / v_edges[y][x])"""
    m = G['layer'] == li
    i0, j0, i1, j1 = (G[k][m].astype(np.int64) for k in ('i0', 'j0', 'i1', 'j1'))
    horiz = HORIZ[LAYERS[li]]
    d = np.zeros((ny + 1) * (nx + 1), dtype=np.int64)
    if horiz:
        ok = i1 - i0 >= 2
        hmax = int((j1 - j0)[ok].max()) if ok.any() else 0
        for r in range(hmax):
            s_ = ok & (j1 - j0 > r)
            d += np.bincount((j0[s_] + r) * (nx + 1) + i0[s_], minlength=len(d))
            d -= np.bincount((j0[s_] + r) * (nx + 1) + i1[s_] - 1, minlength=len(d))
        return d.reshape(ny + 1, nx + 1).cumsum(1)[:ny, :nx]
    ok = j1 - j0 >= 2
    wmax = int((i1 - i0)[ok].max()) if ok.any() else 0
    for r in range(wmax):
        s_ = ok & (i1 - i0 > r)
        d += np.bincount(j0[s_] * (nx + 1) + i0[s_] + r, minlength=len(d))
        d -= np.bincount((j1[s_] - 1) * (nx + 1) + i0[s_] + r, minlength=len(d))
    return d.reshape(ny + 1, nx + 1).cumsum(0)[:ny, :nx]


def unwrap(cap, raw, ug, slack=20):
    """odb usage = (net usage + reductions) mod 256 with 0 <= reductions <= cap: the unique value in
    [ug - slack, ug + cap + slack] congruent to raw.  Returns (unwrapped usage, wrapped cells, ambiguous cells)."""
    raw = raw.astype(np.int64) & 255
    cap = cap.astype(np.int64)
    k = np.maximum(0, -(-(ug - slack - raw) // 256))
    val = raw + 256 * k
    return val, int((k > 0).sum()), int((val > ug + cap + slack).sum())


def entries(G, li, O, nx, ny):
    """(cell index, net index) for every guide box of layer li whose booked edges include an overflowed gcell"""
    sel = np.nonzero(O[:, 0] == li)[0]
    ind = np.zeros((ny + 1, nx + 1), dtype=np.int32)
    ind[O[sel, 1] + 1, O[sel, 2] + 1] = 1
    P = ind.cumsum(0).cumsum(1)
    cell_of = {(int(O[n, 1]), int(O[n, 2])): int(n) for n in sel}
    m = np.nonzero(G['layer'] == li)[0]
    i0, j0, i1, j1 = (G[k][m].astype(np.int64) for k in ('i0', 'j0', 'i1', 'j1'))
    if HORIZ[LAYERS[li]]:
        i1 = i1 - 1
    else:
        j1 = j1 - 1
    ok = (i1 > i0) & (j1 > j0)
    hit = np.zeros(len(m), dtype=bool)
    hit[ok] = (P[j1[ok], i1[ok]] - P[j0[ok], i1[ok]] - P[j1[ok], i0[ok]] + P[j0[ok], i0[ok]]) > 0
    ec, en = [], []
    net = G['net'][m]
    for b in np.nonzero(hit)[0].tolist():
        nn = int(net[b])
        for j in range(int(j0[b]), int(j1[b])):
            for i in range(int(i0[b]), int(i1[b])):
                n = cell_of.get((j, i))
                if n is not None:
                    ec.append(n)
                    en.append(nn)
    return ec, en


def where_fn(R):
    g = R['geo']
    regs = [(r['name'], r['rect']) for r in R['regions']]

    def where(x, y):
        if g['x_sp'] <= x < g['x_fe'] and g['y_f'] <= y < g['y_top']:
            return 'vch' if R['x_vch'] <= x < R['x_vch'] + R['VCH'] else 'spine'
        for t, c in enumerate(g['ch_y']):
            if c <= y < c + R['chh'][t] and g['x_fw'] <= x < g['x_le']:
                return 'channel%d' % t
        for n, (a, b, c, e) in regs:
            if a <= x < c and b <= y < e:
                return n
        if y < g['y_f'] or y >= g['y_top']:
            return 'band'
        return 'other'
    return where


def top(d, n=None):
    return sorted(d.items(), key=lambda kv: -kv[1])[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--case', required=True)
    ap.add_argument('--ov', required=True)
    ap.add_argument('--regions')
    ap.add_argument('--out', required=True)
    ap.add_argument('--cache')
    ap.add_argument('--focus', action='append', default=[], help='NAME=REGEX on the family name')
    ap.add_argument('--hop', type=float, default=500.0)
    ap.add_argument('--rect', action='append', default=[], help='NAME=x0,y0,x1,y1 (um)')
    a = ap.parse_args()
    gx, gy, full = read_ov(a.ov)
    nx, ny, step = len(gx), len(gy), gx[1] - gx[0]
    um = step / 1000.0
    cf = os.path.join(a.cache, 'phase1.pkl') if a.cache else None
    if cf and os.path.exists(cf):
        D = pickle.load(open(cf, 'rb'))
        log('cache loaded')
    else:
        size, pins = read_lefs(sorted(glob.glob(os.path.join(a.case, 'grt', '*.lef'))))
        log('lef macros', len(size))
        D = parse_def(os.path.join(a.case, 'a_real', 'floorplan_placed.def'), size, pins)
        wl = np.zeros(len(D['fam']), dtype=np.float32)
        names = D['names']
        for line in open(os.path.join(a.case, 'grt', 'wirelength_grt.csv')):
            f = line.split()
            if len(f) >= 3 and f[0] == 'grt:':
                n = names.get(f[1])
                if n is not None:
                    wl[n] = float(f[2])
        D['wl'] = wl
        log('wirelength rows > 0:', int((wl > 0).sum()), 'sum um', float(wl.sum(dtype=np.float64)))
        D['G'] = read_guides(os.path.join(a.case, 'grt', 'route.guide'), names, step)
        del D['names']
        if cf:
            pickle.dump(D, open(cf, 'wb'), protocol=4)
    G = D['G']
    # ---- per-gcell overflow, M6..M9: guide edge usage + unwrapped odb reductions
    Ol, Al, chk, UG, CE = [], [], {}, {}, {}
    B = 50
    for ln in MAPPED:
        li = LAYERS.index(ln)
        cap, raw = full[ln]
        ug = edge_usage(G, li, nx, ny)
        val, wrapped, amb = unwrap(cap, raw, ug)
        red = val - ug
        ovl = np.maximum(0, val - cap)
        jj, ii = np.nonzero(ovl)
        Ol.append(np.stack([np.full(len(jj), li), jj, ii, (cap - red)[jj, ii], ug[jj, ii]], axis=1))
        naive = np.maximum(0, raw.astype(np.int64) - cap)
        chk[ln] = dict(overflow=int(ovl.sum()), overflow_odb_as_stored=int(naive.sum()), gcells_wrapped=wrapped, gcells_ambiguous=amb,
                       reductions_negative_gcells=int((red < 0).sum()), reductions_over_cap_gcells=int((red > cap).sum()),
                       guide_usage_total=int(ug.sum()), max_overflow=int(ovl.max()), raw_tracks=int(cap.max()))
        ce = np.maximum(0, cap - red)
        UG[ln], CE[ln] = ug, ce
        for J in range(0, ny, B):
            cs = np.add.reduceat(ce[J:J + B].sum(0), np.arange(0, nx, B))
            us = np.add.reduceat(ug[J:J + B].sum(0), np.arange(0, nx, B))
            Al.append(np.stack([np.full(len(cs), li), np.full(len(cs), J // B), np.arange(len(cs)), cs, us], axis=1))
        log(ln, chk[ln])
    O = np.concatenate(Ol).astype(np.int64)
    A = np.concatenate(Al).astype(np.int64)
    ov = (O[:, 4] - O[:, 3]).astype(np.float64)
    log('overflow gcells', len(O), 'total', int(ov.sum()), 'grid', nx, ny, 'gcell um', um)
    fam, pair, ep, manh, wl, npin = D['fam'], D['pair'], D['ep'], D['manh'], D['wl'].astype(np.float64), D['npin']
    fams, pairs, eps = D['fams'], D['pairs'], D['eps']
    NN, NF = len(fam), len(fams)
    busl, busd = [], {}
    fam_bus = np.zeros(NF, dtype=np.int64)
    for i, f in enumerate(fams):
        b = bus_of(f)
        if b not in busd:
            busd[b] = len(busl)
            busl.append(b)
        fam_bus[i] = busd[b]
    total = float(ov.sum())
    out = dict(case=os.path.abspath(a.case), gcell_um=um, grid=[nx, ny], overflow_total=int(total), overflow_gcells=int(len(O)),
               method=__doc__.split('Method')[1].split('usage:')[0].strip(), guide=G['stats'], nets_def=int(NN), unwrap_check=chk,
               wirelength_total_um=float(wl.sum()))
    # ---- a) layer / region / instance / grid
    out['by_layer'] = {LAYERS[l]: dict(overflow=int(ov[O[:, 0] == l].sum()), gcells=int((O[:, 0] == l).sum()),
                                       max=int(ov[O[:, 0] == l].max()) if (O[:, 0] == l).any() else 0) for l in range(6)}
    cx, cy = (O[:, 2] + 0.5) * um, (O[:, 1] + 0.5) * um
    comp = D['comp']
    ras = np.full((ny, nx), -1, dtype=np.int32)
    lab = []
    for name, c in sorted(comp.items(), key=lambda kv: -kv[1][4] * kv[1][5]):
        mm, x, y, o, w, h, kd = c
        if w * h <= 0:
            continue
        lab.append(name if w * h >= 0.25e6 else kd)
        ras[int(y / um + 0.5):max(int(y / um + 0.5) + 1, int((y + h) / um + 0.5)), int(x / um + 0.5):max(int(x / um + 0.5) + 1, int((x + w) / um + 0.5))] = len(lab) - 1
    cinst = ras[O[:, 1], O[:, 2]]
    by_inst = Counter()
    by_inst_l = {}
    for n, (ci, v, l) in enumerate(zip(cinst.tolist(), ov.tolist(), O[:, 0].tolist())):
        k = lab[ci] if ci >= 0 else '(no instance)'
        by_inst[k] += v
        by_inst_l.setdefault(k, Counter())[LAYERS[l]] += v
    out['by_covering_instance'] = [dict(name=k, overflow=int(v), share=round(v / total, 4), layers={l: int(x) for l, x in top(by_inst_l[k])})
                                   for k, v in top(by_inst, 60)]
    out['big_instances'] = {n: dict(master=c[0], rect=[round(c[1], 3), round(c[2], 3), round(c[1] + c[4], 3), round(c[2] + c[5], 3)])
                            for n, c in comp.items() if c[4] * c[5] >= 0.25e6}
    creg = None
    if a.regions:
        R = json.load(open(a.regions))
        wf = where_fn(R)
        memo = {}
        creg = []
        for x, y in zip(cx.tolist(), cy.tolist()):
            k = (x, y)
            if k not in memo:
                memo[k] = wf(x, y)
            creg.append(memo[k])
        by_reg, by_reg_l = Counter(), {}
        for r, v, l in zip(creg, ov.tolist(), O[:, 0].tolist()):
            by_reg[r] += v
            by_reg_l.setdefault(r, Counter())[LAYERS[l]] += v
        rect = {r['name']: r['rect'] for r in R['regions']}
        out['by_region'] = [dict(name=k, overflow=int(v), share=round(v / total, 4), rect=rect.get(k),
                                 layers={l: int(x) for l, x in top(by_reg_l[k])}) for k, v in top(by_reg)]
        g = R['geo']
        out['region_geo'] = dict(x_sp=g['x_sp'], x_fe=g['x_fe'], y_f=g['y_f'], y_top=g['y_top'], ch_y=g['ch_y'], chh=R['chh'],
                                 x_fw=g['x_fw'], x_le=g['x_le'], x_vch=R['x_vch'], VCH=R['VCH'],
                                 regions={r['name']: dict(kind=r['kind'], rect=r['rect']) for r in R['regions']})
    # ---- attribution
    NC = len(O)
    ecl, enl = [], []
    for ln in MAPPED:
        c_, n_ = entries(G, LAYERS.index(ln), O, nx, ny)
        ecl += c_
        enl += n_
    pe = np.unique(np.array(ecl, dtype=np.int64) * NN + np.array(enl, dtype=np.int64))
    ec, en = pe // NN, pe % NN
    cnt = np.bincount(ec, minlength=NC).astype(np.float64)
    out['attribution_check'] = dict(entries=int(len(ec)), booked_nets_over_guide_usage=round(float(cnt.sum() / O[:, 4].sum()), 4),
                                    overflow_in_gcells_without_any_booked_net=int(ov[cnt == 0].sum()))
    log('attribution', out['attribution_check'])
    w = ov[ec] / cnt[ec]
    net_ov = np.bincount(en, weights=w, minlength=NN)
    net_cross = np.bincount(en, minlength=NN)
    out['attributed_total'] = round(float(net_ov.sum()), 1)

    def table(key, labels, nkeys, extra=None, n=None):
        bits = np.bincount(key, minlength=nkeys)
        o = np.bincount(key, weights=net_ov, minlength=nkeys)
        xb = np.bincount(key, weights=(net_cross > 0), minlength=nkeys)
        swl = np.bincount(key, weights=wl, minlength=nkeys)
        smh = np.bincount(key, weights=manh, minlength=nkeys)
        mwl = np.zeros(nkeys)
        np.maximum.at(mwl, key, wl)
        mmh = np.zeros(nkeys)
        np.maximum.at(mmh, key, manh)
        # dominant driver->sink pair per key
        comb = key.astype(np.int64) * len(pairs) + pair
        u, c = np.unique(comb, return_counts=True)
        best = {}
        for uu, cc in zip(u.tolist(), c.tolist()):
            k, p = divmod(uu, len(pairs))
            if cc > best.get(k, (0, 0))[0]:
                best[k] = (cc, p)
        rows = []
        for k in np.argsort(-o)[:n]:
            if bits[k] == 0:
                continue
            r = dict(name=labels[k], bits=int(bits[k]), overflow=round(float(o[k]), 1), share=round(float(o[k] / total), 4),
                     bits_on_overflowed_gcells=int(xb[k]), wl_mean=round(float(swl[k] / bits[k]), 1), wl_max=round(float(mwl[k]), 1),
                     manh_mean=round(float(smh[k] / bits[k]), 1), manh_max=round(float(mmh[k]), 1), pair=pairs[best[k][1]])
            if extra:
                r.update(extra(k, bits[k]))
            rows.append(r)
        return rows

    fb = D['fam_bases']
    out['families'] = table(fam, fams, NF, lambda k, b: dict(bus_instances=int(fb[k]), width=round(float(b / max(1, fb[k])), 1)), 200)
    bus = fam_bus[fam]
    bb = np.bincount(fam_bus, weights=fb, minlength=len(busl))
    out['buses'] = table(bus, busl, len(busl), lambda k, b: dict(bus_instances=int(bb[k])), 100)
    out['pairs'] = [dict(name=r['name'], bits=r['bits'], overflow=r['overflow'], share=r['share'], wl_mean=r['wl_mean'], wl_max=r['wl_max'])
                    for r in table(pair, pairs, len(pairs), None, 40)]
    # ---- coarse grid (50 x 50 gcells = 480 um) and hot windows
    wkey = (O[:, 1] // B) * 1000 + O[:, 2] // B
    wov = Counter()
    wl_ = {}
    for k, v, l in zip(wkey.tolist(), ov.tolist(), O[:, 0].tolist()):
        wov[k] += v
        wl_.setdefault(k, Counter())[LAYERS[l]] += v
    acap = {(int(l), int(j), int(i)): (int(c), int(u)) for l, j, i, c, u in A.tolist()}
    ent_w = wkey[ec]
    hot = []
    for k, v in top(wov, 20):
        J, I = divmod(k, 1000)
        m = ent_w == k
        fo = np.bincount(bus[en[m]], weights=w[m], minlength=len(busl))
        sel = wkey == k
        reg = Counter()
        ins = Counter()
        for n in np.nonzero(sel)[0].tolist():
            if creg:
                reg[creg[n]] += ov[n]
            ins[lab[cinst[n]] if cinst[n] >= 0 else '(no instance)'] += ov[n]
        hot.append(dict(x=[round(I * B * um, 1), round((I + 1) * B * um, 1)], y=[round(J * B * um, 1), round((J + 1) * B * um, 1)],
                        overflow=int(v), share=round(v / total, 4), layers={l: int(x) for l, x in top(wl_[k])},
                        cap_use={LAYERS[l]: acap.get((l, J, I)) for l in range(6)},
                        regions={r: int(x) for r, x in top(reg, 3)}, instances={r: int(x) for r, x in top(ins, 3)},
                        buses=[[busl[b], int(fo[b])] for b in np.argsort(-fo)[:4] if fo[b] > 0]))
    out['hot_windows_480um'] = hot
    out['grid_480um'] = {'%d,%d' % (k % 1000, k // 1000): int(v) for k, v in sorted(wov.items())}
    out['grid_480um_layers'] = {'%d,%d' % (k % 1000, k // 1000): {l: int(x) for l, x in d.items()} for k, d in sorted(wl_.items())}
    cum = np.cumsum(sorted(wov.values(), reverse=True))
    out['concentration'] = dict(windows_with_overflow=len(wov), top10_share=round(float(cum[min(9, len(cum) - 1)] / total), 4),
                                top20_share=round(float(cum[min(19, len(cum) - 1)] / total), 4),
                                top50_share=round(float(cum[min(49, len(cum) - 1)] / total), 4))
    # worst utilisation blocks per layer (use/cap over the 480 um block, all gcells)
    ut = {}
    for l in range(6):
        s = A[(A[:, 0] == l) & (A[:, 3] > 0)]
        r = s[:, 4] / s[:, 3]
        o = np.argsort(-r)[:8]
        ut[LAYERS[l]] = [dict(x=round(float(s[n, 2] * B * um), 1), y=round(float(s[n, 1] * B * um), 1), cap=int(s[n, 3]), use=int(s[n, 4]),
                              util=round(float(r[n]), 3)) for n in o]
    out['worst_util_480um'] = ut
    # ---- fixed rectangles: overflow, M6..M9 demand / effective capacity, top buses
    rects = {}
    for spec in a.rect:
        nm, v = spec.split('=', 1)
        x0, y0, x1, y1 = (float(t) for t in v.split(','))
        selc = (cx >= x0) & (cx < x1) & (cy >= y0) & (cy < y1)
        i0_, i1_, j0_, j1_ = int(x0 / um), int(-(-x1 // um)), int(y0 / um), int(-(-y1 // um))
        fo = np.bincount(bus[en[selc[ec]]], weights=w[selc[ec]], minlength=len(busl))
        rects[nm] = dict(rect=[x0, y0, x1, y1], overflow=int(ov[selc].sum()), share=round(float(ov[selc].sum() / total), 4),
                         layers={LAYERS[l]: int(ov[selc & (O[:, 0] == l)].sum()) for l in range(2, 6)},
                         demand_over_capacity={ln: [int(UG[ln][j0_:j1_, i0_:i1_].sum()), int(CE[ln][j0_:j1_, i0_:i1_].sum())] for ln in MAPPED},
                         buses=[[busl[b], int(fo[b])] for b in np.argsort(-fo)[:6] if fo[b] > 0])
    out['rects'] = rects
    if creg:
        R_ = {r['name']: r['rect'] for r in json.load(open(a.regions))['regions']}
        isf = np.array([r.startswith('frame_') for r in creg])
        fx0 = np.array([R_[r][0] if r.startswith('frame_') else 0.0 for r in creg])
        fy0 = np.array([R_[r][1] if r.startswith('frame_') else 0.0 for r in creg])
        lx, ly = (cx - fx0)[isf], (cy - fy0)[isf]
        fl = {}
        for l in (2, 4):
            ml = O[isf, 0] == l
            hy = np.bincount((ly[ml] // 96).astype(int), weights=ov[isf][ml], minlength=28)
            hx = np.bincount((lx[ml] // 48).astype(int), weights=ov[isf][ml], minlength=25)
            fl[LAYERS[l]] = dict(by_local_y_96um=[int(v) for v in hy], by_local_x_48um=[int(v) for v in hx])
        fi = Counter()
        for n in np.nonzero(isf)[0].tolist():
            fi[lab[cinst[n]] if cinst[n] >= 0 else '(no instance)'] += ov[n]
        fo = np.bincount(bus[en[isf[ec]]], weights=w[isf[ec]], minlength=len(busl))
        per = sorted(v['overflow'] for v in out['by_region'] if v['name'].startswith('frame_'))
        out['frames'] = dict(overflow=int(ov[isf].sum()), share=round(float(ov[isf].sum() / total), 4), frames=len(per), per_frame_min=per[0],
                             per_frame_median=per[len(per) // 2], per_frame_max=per[-1], local_profile=fl,
                             covering={k: int(v) for k, v in top(fi, 8)}, buses=[[busl[b], int(fo[b])] for b in np.argsort(-fo)[:6] if fo[b] > 0])
    # ---- c) focus families: their own share and the overflow of the gcells they are booked on
    foc = {}
    for spec in a.focus:
        nm, rx = spec.split('=', 1)
        if rx.startswith('ep:'):
            fsel = np.array([bool(re.search(rx[3:], f)) for f in eps])
            nsel = fsel[ep]
        else:
            fsel = np.array([bool(re.search(rx, f)) for f in fams])
            nsel = fsel[fam]
        cells = np.unique(ec[nsel[en]])
        on = np.zeros(NC, dtype=bool)
        on[cells] = True
        mm = nsel & (npin >= 2)
        rel = D['relay'][mm]
        foc[nm] = dict(regex=rx, bits=int(nsel.sum()), families=int(fsel.sum()), own_overflow=round(float(net_ov[nsel].sum()), 1),
                       own_share=round(float(net_ov[nsel].sum() / total), 4), gcells_booked=int(len(cells)),
                       overflow_of_those_gcells=int(ov[on].sum()), share_of_those_gcells=round(float(ov[on].sum() / total), 4),
                       wl_quantiles=[round(float(q), 1) for q in np.quantile(wl[mm], [0, .5, .9, .99, 1])] if mm.any() else None,
                       manh_quantiles=[round(float(q), 1) for q in np.quantile(manh[mm], [0, .5, .9, .99, 1])] if mm.any() else None,
                       bits_over_hop_manh=int((manh[mm] > a.hop).sum()), bits_over_hop_wl=int((wl[mm] > a.hop).sum()),
                       driver_is_relay_bits=int((rel & 1).astype(bool).sum()), sink_is_relay_bits=int((rel & 2).astype(bool).sum()),
                       both_ends_relay_bits=int(((rel & 3) == 3).sum()), no_relay_end_bits=int(((rel & 3) == 0).sum()),
                       wl_sum_um=round(float(wl[mm].sum()), 0), top_families=[[fams[k], int(c)] for k, c in Counter(fam[mm].tolist()).most_common(10)],
                       top_eps=[[eps[k], int(c)] for k, c in Counter(ep[mm].tolist()).most_common(12)],
                       top_pairs=[[pairs[k], int(c)] for k, c in Counter(pair[mm].tolist()).most_common(8)])
    out['focus'] = foc
    # ---- d) hops longer than the limit
    two = npin >= 2
    # clock / reset / forwarded-clock classes by name (pins ck*, cw, rs*, rst, pll*, por, and the stations' fi / fo)
    exempt = re.compile(r'(?:^|[._])(?:ck[a-z]?|cw|rs[a-z]?|pll|por|fi0?|fo0?)(?:$|[._ ])|clk|rst')

    def hop_list(metric, by, labels, sel=None):
        m = two & (metric > a.hop)
        if sel is not None:
            m &= sel
        keys = by[m]
        nk = len(labels)
        bits = np.bincount(keys, minlength=nk)
        s = np.bincount(keys, weights=metric[m], minlength=nk)
        mx = np.zeros(nk)
        np.maximum.at(mx, keys, metric[m])
        swl = np.bincount(keys, weights=wl[m], minlength=nk)
        smh = np.bincount(keys, weights=manh[m], minlength=nk)
        du = np.bincount(keys, weights=((D['relay'][m] & 4) > 0), minlength=nk)
        nr = np.bincount(keys, weights=((D['relay'][m] & 3) == 0), minlength=nk)
        o = np.bincount(keys, weights=net_ov[m], minlength=nk)
        tot = np.bincount(by, minlength=nk)
        pc_ = {}
        for k, p in zip(keys.tolist(), pair[m].tolist()):
            pc_.setdefault(k, Counter())[p] += 1
        pr = {k: c.most_common(1)[0][0] for k, c in pc_.items()}
        rows = [dict(name=labels[k], bits_over=int(bits[k]), bits_total=int(tot[k]), mean_um=round(float(s[k] / bits[k]), 1), max_um=round(float(mx[k]), 1),
                     bits_x_um=round(float(s[k]), 0), wl_mean=round(float(swl[k] / bits[k]), 1),
                     manh_mean=round(float(smh[k] / bits[k]), 1), driver_unidentified_bits=int(du[k]),
                     no_relay_end_bits=int(nr[k]), overflow=round(float(o[k]), 1),
                     pair=pairs[pr[k]], clock_or_reset_name=bool(exempt.search(labels[k])))
                for k in np.nonzero(bits)[0].tolist()]
        rows.sort(key=lambda r: -r['bits_x_um'])
        return rows

    mh = manh.astype(np.float64)
    p2, pm = npin == 2, npin > 2
    out['hops_over_limit'] = dict(
        limit_um=a.hop,
        note='2-pin nets: one hop.  Multi-sink nets: manh = driver -> farthest sink (largest pin-to-pin distance when the driver is '
             'not identified), wl = the whole routed tree, not a hop',
        pin_manhattan=dict(bits_2pin=int((p2 & (manh > a.hop)).sum()), bits_multi_sink=int((pm & (manh > a.hop)).sum()),
                           two_pin_by_endpoint=hop_list(mh, ep, eps, p2), multi_sink_by_endpoint=hop_list(mh, ep, eps, pm)),
        routed_wl=dict(bits_2pin=int((p2 & (wl > a.hop)).sum()), bits_multi_sink_tree=int((pm & (wl > a.hop)).sum()),
                       two_pin_by_bus=hop_list(wl, bus, busl, p2), two_pin_by_endpoint=hop_list(wl, ep, eps, p2),
                       multi_sink_tree_by_bus=hop_list(wl, bus, busl, pm)))
    out['length_census'] = dict(two_plus_pin_nets=int(two.sum()),
                                manh_quantiles=[round(float(q), 1) for q in np.quantile(manh[two], [.5, .9, .99, .999, 1])],
                                wl_quantiles=[round(float(q), 1) for q in np.quantile(wl[two], [.5, .9, .99, .999, 1])],
                                detour_over_1p5x_bits=int((two & (wl > 1.5 * manh + 2 * um * 3)).sum()))
    json.dump(out, open(a.out, 'w'), indent=1)
    log('wrote', a.out)
    print('TOTAL', int(total), out['by_layer'])
    print('CHECK', chk, 'attributed', out['attributed_total'])


if __name__ == '__main__':
    sys.exit(main())
