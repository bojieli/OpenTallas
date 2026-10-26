#!/usr/bin/env python3
"""S81-P8-C: greedy top-down re-site of the small hard macros of one frame band (ROM / q-element / bf structure fixed)
to minimise the max register hop (then total bit-distance).  Legal = 8.64 lattice, inside outline, no overlap, every
facing macro-macro gap >= 13.8 um, off the boundary-flop strips of the port windows."""
import json, sys, copy
import numpy as np
import hops as H, netgraph as g

LAT, GAP, OUT = 8.64, 13.8, g.OUTLINE
FIXED_MODS = {'ot_rom_4096x72_m8', 'ot_v41_rom_elem_q_qxpq_w10', 'ot_v41_bf_col', 'dsfd_bf_front_roots'}
STRIP = 30.0

def keepouts(ptypes):
    ko = []
    for pt in ptypes:
        for b in pt['buses']:
            w0, w1 = b['window_um']
            f = b['face']
            ko.append({'N': (w0, OUT[1] - STRIP, w1, OUT[1]), 'S': (w0, 0, w1, STRIP), 'E': (OUT[0] - STRIP, w0, OUT[0], w1),
                       'W': (0, w0, STRIP, w1)}[f])
        for f in pt.get('ft_slots', []):
            for side, win in ((f['in_face'], f['in_window_um']), (f['out_face'], f['out_window_um'])):
                w0, w1 = win
                ko.append({'N': (w0, OUT[1] - STRIP, w1, OUT[1]), 'S': (w0, 0, w1, STRIP), 'E': (OUT[0] - STRIP, w0, OUT[0], w1),
                           'W': (0, w0, STRIP, w1)}[side])
    return ko

def legal_sites(models, n, ko):
    m = models[0]
    w, h = m.macros[n]['size_um']
    xs = np.arange(LAT, OUT[0] - w - LAT + 1e-6, LAT); ys = np.arange(LAT, OUT[1] - h - LAT + 1e-6, LAT)
    X, Y = np.meshgrid(xs, ys); X = X.ravel(); Y = Y.ravel()
    ok = np.ones(len(X), bool)
    for o, s in m.site.items():
        if o == n:
            continue
        ow, oh = m.macros[o]['size_um']
        x0, y0, x1, y1 = s[0], s[1], s[0] + ow, s[1] + oh
        yov = (Y <= y1 + 1e-6) & (Y + h >= y0 - 1e-6)      # overlap OR touch (frame_band_macros.gap_check semantics)
        xov = (X <= x1 + 1e-6) & (X + w >= x0 - 1e-6)
        bad = (yov & (X < x1 + GAP - 1e-6) & (X + w > x0 - GAP + 1e-6)) | (xov & (Y < y1 + GAP - 1e-6) & (Y + h > y0 - GAP + 1e-6))
        ok &= ~bad
    for x0, y0, x1, y1 in ko:
        ok &= ~((X < x1) & (X + w > x0) & (Y < y1) & (Y + h > y0))
    return np.stack([X[ok], Y[ok]], 1)

def local_cost(models, n, S):
    """vectorised over candidate origins S (k,2): max hop and sum bits*len of n's incident groups (soft neighbours at
    the minimax centre of their terminals with n moved)"""
    mx = np.zeros(len(S)); tot = np.zeros(len(S))
    for m in models:
        for i in m.inc[n]:
            gr = m.groups[i]
            if gr['a'] == n and gr['b'] == n:
                continue
            mine, oth, mo, oo = ('a', 'b', gr['ao'], gr['bo']) if gr['a'] == n else ('b', 'a', gr['bo'], gr['ao'])
            o = gr[oth]
            if m.nodes[o]['kind'] != 'S':
                P = m.base(o) + oo                                    # (bits,2)
                # max over bits |S + mo - P|_1 : bound with bbox in rotated coords (exact for L1)
                d = mo - P
                u = d[:, 0] + d[:, 1]; v = d[:, 0] - d[:, 1]
                su = S[:, 0] + S[:, 1]; sv = S[:, 0] - S[:, 1]
                h = np.maximum.reduce([np.abs(su + u.max()), np.abs(su + u.min()), np.abs(sv + v.max()), np.abs(sv + v.min())])
                mx = np.maximum(mx, h); tot += gr['bits'] * h
            else:
                # terminals of the soft node o other than n
                T = []
                for j in m.inc[o]:
                    g2 = m.groups[j]
                    if g2['a'] == o and g2['b'] != n:
                        T.append(m.base(g2['b']) + g2['bo'])
                    elif g2['b'] == o and g2['a'] != n:
                        T.append(m.base(g2['a']) + g2['ao'])
                su = S[:, 0] + S[:, 1]; sv = S[:, 0] - S[:, 1]
                umin = su + (mo[:, 0] + mo[:, 1]).min(); umax = su + (mo[:, 0] + mo[:, 1]).max()
                vmin = sv + (mo[:, 0] - mo[:, 1]).min(); vmax = sv + (mo[:, 0] - mo[:, 1]).max()
                if T:
                    T = np.vstack(T); tu = T[:, 0] + T[:, 1]; tv = T[:, 0] - T[:, 1]
                    umin = np.minimum(umin, tu.min()); umax = np.maximum(umax, tu.max())
                    vmin = np.minimum(vmin, tv.min()); vmax = np.maximum(vmax, tv.max())
                h = np.maximum(umax - umin, vmax - vmin) / 2
                mx = np.maximum(mx, h); tot += gr['bits'] * h
    return mx, tot

EXCL = set()      # (a, b) groups that need an RTL stage whatever the sites (reported separately, not optimised)

def excluded(gr):
    return (gr['a'], gr['b']) in EXCL

def glob(models):
    mx = 0.0; tot = 0.0; exc = 0.0
    for m in models:
        m.solve()
        for a, t, gr in m.hops():
            if excluded(gr):
                continue
            mx = max(mx, a); tot += t; exc += max(0.0, a - 750.0)
    return mx, tot, exc

def better(new, cur):
    kn = (round(new[0] / 2), round(new[2]))
    kc = (round(cur[0] / 2), round(cur[2]))
    return kn < kc or (kn == kc and new[1] < cur[1] * 0.995)

def worst_list(models, thr):
    out = {}
    for m in models:
        for a, t, gr in m.hops():
            if a > thr and not excluded(gr):
                for n in (gr['a'], gr['b']):
                    if m.nodes[n]['kind'] == 'M' and m.macros[n]['module'] not in FIXED_MODS:
                        out[n] = max(out.get(n, 0), a)
                    elif m.nodes[n]['kind'] == 'S':
                        # soft node: its macro terminals are the movers
                        for j in m.inc[n]:
                            g2 = m.groups[j]
                            for x in (g2['a'], g2['b']):
                                if x != n and m.nodes[x]['kind'] == 'M' and m.macros[x]['module'] not in FIXED_MODS:
                                    out[x] = max(out.get(x, 0), a)
    return sorted(out, key=lambda n: -out[n])

def set_site(models, n, s):
    for m in models:
        m.site[n] = (round(float(s[0]), 4), round(float(s[1]), 4))

def optimize(models, ptypes, log, rounds=40, thr=600.0):
    ko = keepouts(ptypes)
    cur = glob(models)
    log(f'  start max {cur[0]:.0f} exc750 {cur[2]:.0f} total {cur[1]:.3g}')
    tabu = set()
    for r in range(rounds):
        improved = False
        for n in worst_list(models, max(thr, cur[0] - 400)):
            S = legal_sites(models, n, ko)
            if not len(S):
                continue
            lmx, ltot = local_cost(models, n, S)
            order = np.lexsort((ltot, np.round(lmx / 5)))
            old = models[0].site[n]
            for idx in order[:6]:
                set_site(models, n, S[idx])
                new = glob(models)
                if better(new, cur):
                    log(f'  r{r} move {n} {old} -> {models[0].site[n]}  max {cur[0]:.0f}->{new[0]:.0f} exc750 {cur[2]:.0f}->{new[2]:.0f} total {cur[1]:.3g}->{new[1]:.3g}')
                    cur = new; improved = True
                    break
                set_site(models, n, old)
            else:
                glob(models)
            if improved:
                break
        if not improved:
            # pair move: re-site a macro neighbour of a worst macro first, then the worst macro itself
            for n in worst_list(models, max(thr, cur[0] - 50))[:4]:
                nb = set()
                for m in models:
                    for i in m.inc[n]:
                        gr = m.groups[i]
                        for x in (gr['a'], gr['b']):
                            if x != n and m.nodes[x]['kind'] == 'M' and m.macros[x]['module'] not in FIXED_MODS:
                                nb.add(x)
                for x in sorted(nb):
                    old = {y: models[0].site[y] for y in (n, x)}
                    Sx = legal_sites(models, x, ko)
                    if not len(Sx):
                        continue
                    lmx, ltot = local_cost(models, x, Sx)
                    for ix in np.lexsort((ltot, np.round(lmx / 5)))[:3]:
                        set_site(models, x, Sx[ix]); glob(models)
                        Sn = legal_sites(models, n, ko)
                        if not len(Sn):
                            set_site(models, x, old[x]); continue
                        lmx2, ltot2 = local_cost(models, n, Sn)
                        for inn in np.lexsort((ltot2, np.round(lmx2 / 5)))[:3]:
                            set_site(models, n, Sn[inn])
                            new = glob(models)
                            if better(new, cur):
                                log(f'  r{r} pair move {x} {old[x]} -> {models[0].site[x]}, {n} {old[n]} -> {models[0].site[n]}  max {cur[0]:.0f}->{new[0]:.0f} exc750 {cur[2]:.0f}->{new[2]:.0f}')
                                cur = new; improved = True
                                break
                            set_site(models, n, old[n])
                        if improved:
                            break
                        set_site(models, x, old[x])
                    glob(models)
                    if improved:
                        break
                if improved:
                    break
        if not improved:
            break
    return cur
