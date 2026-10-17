#!/usr/bin/env python3
"""S81-DV: distributed-vector S81 layer die, plan-level floorplan + die-level dataflow (owner 0cj, 2026-10-16).

The central SU/VM/HC hub is replaced by G = 16 identical vector slices.  Each slice sits in the slice column of
its cluster column, at the middle of its tier, and owns:
  * the output rows y[a:b] its 8 frames produce (finished rows from the frames' region roots, local return),
  * a 1/16 VM partition, 1/16 of the SU lanes (QN/KV/QB/SW/RX/QR), 4 HC cth tiles (h-resident 4 x 320 BF16),
  * a ring stop of the die-level x all-gather mesh (E/W per tier, N/S per column), fixed time of flight.
Global scalars (RMS sum-of-squares partial roots, router scores, HC coefficients, MTP head items) travel on the
same mesh as tiny TDM payloads; attention softmax stays a dedicated unit beside the HBM service (irregular op).

Outputs (in --out): plan.json (blocks + links + geometry facts), dv_links_record.json (opentallas.dataflow.links.v1,
for `dataflow_links.py import`), dv_flow.png.  Every die-level link is a registered relay chain at <= HOP_UM.
"""
import argparse
import json
import math
from pathlib import Path

DIE_W, DIE_H = 33000.0, 26000.0
EDGE = 300.0                      # link PHY strip on the W/E edges
NCOL = 8                          # cluster columns
FRAME_W, FRAME_PITCH = 1139.6, 1148.3   # c26l column frame width / column pitch
H9, H10A, H10B = 2695.68, 2985.12, 3000.24   # c26l frame heights (9-slot, 10-slot a/b)
BAND = 1820.0                     # south band: HBM PHY + ctrl + service strip
STREET = 400.0                    # horizontal ring street at each tier middle
SLICE_W, SLICE_H = 1700.0, 2600.0
HOP_UM = 405.0                    # plan hop (0.9 x measured S81 reach 455 um, rounded down to the 405 plan rule)
XB = 1104                         # x stream beat: 64 FP8 codes + 2 exps (566 b) + second lane (538 b), as c26l cx+x2
RET = 68                          # frame return lane (dsfd_m2l_vr_68x1x)
CTL = 96                          # slice command (85 b) + done (9 b) + 2 status
COLL_LANE = 512


def chain(pts, hop=HOP_UM):
    """Manhattan polyline through pts, cut into <= hop segments -> (hops, relays, length)"""
    segs, L = [], 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        for a, b in (((x1, y1), (x2, y1)), ((x2, y1), (x2, y2))):
            d = abs(b[0] - a[0]) + abs(b[1] - a[1])
            if d <= 0:
                continue
            n = max(1, math.ceil(d / hop))
            for k in range(n):
                t0, t1 = k / n, (k + 1) / n
                segs.append((a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0,
                             a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1))
            L += d
    return segs, max(0, len(segs) - 1), L


class Plan:
    def __init__(self):
        self.blocks, self.links, self.idx = [], [], {}

    def block(self, name, master, kind, group, x, y, w, h, reg=False):
        self.idx[name] = len(self.blocks)
        self.blocks.append(dict(name=name, master=master, kind=kind, group=group, x=x, y=y, w=w, h=h, reg=reg))

    def c(self, name):
        b = self.blocks[self.idx[name]]
        return b['x'] + b['w'] / 2, b['y'] + b['h'] / 2

    def link(self, lid, cls, bits, src, dst, pts, note=None):
        """src/dst = (block, port, (x, y)); pts = routed waypoints from src pin to dst pin"""
        segs, s, L = chain(pts)
        self.links.append(dict(i=lid, c=cls, b=bits, d=1, s=s, L=round(L, 1),
                               e=[[self.idx[src[0]], src[1], round(src[2][0], 1), round(src[2][1], 1), 'box'],
                                  [self.idx[dst[0]], dst[1], round(dst[2][0], 1), round(dst[2][1], 1), 'box']],
                               h=[[round(a, 1), round(b, 1), round(c, 1), round(d, 1), bits] for a, b, c, d in segs],
                               n=note))


def column_heights():
    """16 frame columns x 8 frames reproducing the c26l height mix exactly (60 x H9, 40 x H10A, 28 x H10B)"""
    cols = []
    a_left, b_left = 40, 28
    for k in range(16):
        n9 = 3 if k in (0, 5, 10, 15) else 4      # 4 columns of 3 x H9 and 12 of 4 x H9 = 60
        rest = []
        for _ in range(8 - n9):
            if a_left >= b_left:
                rest.append(H10A); a_left -= 1
            else:
                rest.append(H10B); b_left -= 1
        hs = [H9] * n9 + rest
        # interleave tall/short so each tier carries a similar height
        hs = sorted(hs)
        cols.append([hs[0], hs[7], hs[2], hs[5], hs[1], hs[6], hs[3], hs[4]])
    assert sum(h == H9 for c in cols for h in c) == 60
    return cols


def build():
    P = Plan()
    pitch = (DIE_W - 2 * EDGE) / NCOL
    scol_w = pitch - 2 * FRAME_PITCH
    heights = column_heights()
    facts = dict(cluster_pitch_um=pitch, slice_column_um=scol_w)
    # ---------------------------------------------------------------- frames, slices
    tier_mid = {}
    ymax = 0.0
    # one street y per tier, die-wide: rows 0,1 of every column end at or below it, rows 2,3 start above it
    lo = lambda hs, t: sum(hs[4 * t:4 * t + 2])
    full = lambda hs, t: sum(hs[4 * t:4 * t + 4])
    st0 = BAND + max(lo(h, 0) for h in heights)
    t1 = st0 + STREET + max(full(h, 0) - lo(h, 0) for h in heights)
    st1 = t1 + max(lo(h, 1) for h in heights)
    streets = (st0, st1)
    for c in range(NCOL):
        x0 = EDGE + c * pitch
        fcols = {'L': (x0, 'E'), 'R': (x0 + FRAME_PITCH + scol_w + (FRAME_PITCH - FRAME_W), 'W')}
        for side, (fx, face) in fcols.items():
            hs = heights[2 * c + (side == 'R')]
            for t in range(2):
                y = streets[t] - lo(hs, t)
                for r in range(4):
                    if r == 2:
                        y = streets[t] + STREET
                    h = hs[4 * t + r]
                    P.block(f'f_{c}{side}{t}{r}', 'col_h9' if h == H9 else 'col_h10', 'frame', f'cl{c}{"SN"[t]}', fx, y, FRAME_W, h)
                    y += h
                ymax = max(ymax, y)
            for t in range(2):
                tier_mid.setdefault((c, t), []).append(streets[t] + STREET / 2)
    facts['frame_top_um'] = ymax
    assert ymax <= DIE_H - 250, ymax
    for c in range(NCOL):
        x0 = EDGE + c * pitch + FRAME_PITCH
        for t in range(2):
            ym = sum(tier_mid[(c, t)]) / len(tier_mid[(c, t)])
            P.block(f's_{c}{"SN"[t]}', 'dsdv_slice', 'slice', f'cl{c}{"SN"[t]}', x0 + (scol_w - SLICE_W) / 2, ym - SLICE_H / 2, SLICE_W, SLICE_H)
    # ---------------------------------------------------------------- south band, edge links, global units
    # south band: [SM_W x4][svc_W][PHY + ctrl][svc_E][SM_E x4] -- the HBM service halves abut the PHY, and each
    # attention softmax group (SU SM tiles, 2 heads x 16 lanes each, 1.23 x 1.06 mm) abuts its service half, so the
    # 8 kb score/P interface is a face, not a die wire (attention = PHY-adjacent attention slices, irregular unit)
    phy_x = DIE_W / 2 - 4250
    P.block('phy_hbm', 'ot_hbm3e_phy_v41x_aw30_e8p5', 'phy', 'south', phy_x, 20, 8500, 1177)
    P.block('hbm_ctrl', 'dsfd_ctrl', 'ctrl', 'south', phy_x, 1210, 8500, 250)
    P.block('svc_W', 'dsfd_svc_half', 'svc', 'south', phy_x - 4260, 20, 4250, 1580)
    P.block('svc_E', 'dsfd_svc_half', 'svc', 'south', phy_x + 8510, 20, 4250, 1580)
    for k in range(4):
        P.block(f'sm_W{k}', 'ot_s81_su_sm', 'unit', 'south', phy_x - 4270 - (k + 1) * 1235, 20, 1231, 1058)
        P.block(f'sm_E{k}', 'ot_s81_su_sm', 'unit', 'south', phy_x + 12770 + k * 1235, 20, 1231, 1058)
    sx = lambda c: EDGE + c * pitch + FRAME_PITCH + 90      # side units hug the left of the slice column
    ys, yn = P.c('s_0S')[1], P.c('s_0N')[1]
    s_bot = ys - SLICE_H / 2
    h_free = min(4200.0, s_bot - BAND - 200)
    # index select/collect (bk, 6.3 mm2) above the PHY centre and Engram mix4 (5.2 mm2) in cols 2/5: every piece
    # <= 2.1:1 (no long thin blocks)
    for nm, c, h in (('bk_sel', 3, 2500.0), ('bk_col', 4, 2500.0), ('mix4_w', 2, 2100.0), ('mix4_e', 5, 2100.0)):
        P.block(nm, 'dsfd_bk_selcol' if nm.startswith('bk') else 'dsfd_engram_mix4_half', 'unit', 'south', sx(c), BAND + 300, 1250, h)
    gy = (P.blocks[P.idx['s_3S']]['y'] + SLICE_H + P.blocks[P.idx['s_3N']]['y']) / 2
    P.block('gunit', 'dsdv_gunit', 'unit', 'centre', sx(3), gy - 1100, 1100, 2200)    # norm/router/top6/HC coef+Sinkhorn
    P.block('seqhost', 'dsdv_seq_host', 'unit', 'centre', sx(4), gy - 900, 1100, 1800)  # stage seq, host, wfc
    for side, xl in (('W', 0.0), ('E', DIE_W - 260)):
        for t, yc in (('S', ys), ('N', yn)):
            P.block(f'lk_{side}{t}0', 'ot_pdie_ucie' if t == 'S' else 'ot_pdie_serdes', 'link', 'edge', xl, yc - 2300, 260, 2250)
            P.block(f'lk_{side}{t}1', 'ot_pdie_serdes', 'link', 'edge', xl, yc + 50, 260, 2250)
        c = 0 if side == 'W' else NCOL - 1
        for t in 'SN':
            s = P.blocks[P.idx[f's_{c}{t}']]
            cy = s['y'] + SLICE_H + 150 if t == 'S' else s['y'] - 1150
            P.block(f'coll_{side}{t}', 'dsdv_coll_edge', 'unit', 'edge', sx(c), cy, 1100, 1000)
    # ---------------------------------------------------------------- links
    def pin(b, side):
        x, y = P.c(b); B = P.blocks[P.idx[b]]
        return {'W': (B['x'], y), 'E': (B['x'] + B['w'], y), 'N': (x, B['y'] + B['h']), 'S': (x, B['y'])}[side]
    # x all-gather mesh: E-W per tier street (two directions, offset tracks), N-S per slice column
    for t in 'SN':
        for c in range(NCOL - 1):
            a, b = f's_{c}{t}', f's_{c + 1}{t}'
            for d, (u, v, off) in (('E', (a, b, -80)), ('W', (b, a, 80))):
                p0, p1 = pin(u, 'E' if d == 'E' else 'W'), pin(v, 'W' if d == 'E' else 'E')
                P.link(f'xr{d}_{c}{t}', 'xring', XB, (u, 'xr' + d, p0), (v, 'xr' + d, p1),
                       [(p0[0], p0[1] + off), (p1[0], p1[1] + off)], 'x all-gather / collective / scalar-tree TDM')
    for c in range(NCOL):
        a, b = f's_{c}S', f's_{c}N'
        xr = EDGE + c * pitch + FRAME_PITCH + scol_w - 230   # right side of the slice column
        for d, (u, v, dx) in (('N', (a, b, -110)), ('S', (b, a, 110))):
            p0, p1 = pin(u, 'N' if d == 'N' else 'S'), pin(v, 'S' if d == 'N' else 'N')
            P.link(f'xv{d}_{c}', 'xring', XB, (u, 'xv' + d, (xr + dx, p0[1])), (v, 'xv' + d, (xr + dx, p1[1])),
                   [(xr + dx, p0[1]), (xr + dx, p1[1])], 'mesh column link')
    # slice <-> its 8 frames (x tap at the frame face cfifo, finished-row return)
    for c in range(NCOL):
        for t in range(2):
            sn = f's_{c}{"SN"[t]}'
            S = P.blocks[P.idx[sn]]
            for side in 'LR':
                for r in range(4):
                    fn = f'f_{c}{side}{t}{r}'
                    F = P.blocks[P.idx[fn]]
                    fx = F['x'] + F['w'] if side == 'L' else F['x']
                    fy = F['y'] + 400   # cfifo x-tap pin, off the street windows
                    sxp = S['x'] if side == 'L' else S['x'] + S['w']
                    vx = sxp - 120 - 90 * r if side == 'L' else sxp + 120 + 90 * r
                    mid = S['y'] + SLICE_H / 2   # rows 2,3 above the street leave the upper half; 0,1 the lower
                    sy = mid + 400 + 350 * (r - 2) if r >= 2 else mid - 400 - 350 * (1 - r)
                    # x is daisy-chained per half-column: slice -> nearest frame -> next frame (cfifo tap + forward),
                    # so a slice has 4 x-out ports, not 8
                    if r in (1, 2):
                        P.link(f'x_{fn}', 'x_frame', XB, (sn, 'xf', (sxp, sy)), (fn, 'x', (fx, fy)),
                               [(sxp, sy), (vx, sy), (vx, fy), (fx, fy)], 'x chain head into the frame cfifo')
                    else:
                        pn = f'f_{c}{side}{t}{1 if r == 0 else 2}'
                        PF = P.blocks[P.idx[pn]]
                        pfx, pfy = (PF['x'] + PF['w'] if side == 'L' else PF['x']), PF['y'] + 400
                        P.link(f'x_{fn}', 'x_frame', XB, (pn, 'xo', (pfx, pfy + 80)), (fn, 'x', (fx, fy)),
                               [(pfx, pfy + 80), (vx, pfy + 80), (vx, fy), (fx, fy)], 'x chain forward (frame cfifo -> next frame)')
                    P.link(f'r_{fn}', 'ret', RET, (fn, 'ret', (fx, fy + 40)), (sn, 'ret', (sxp, sy + 40)),
                           [(fx, fy + 40), (vx + (25 if side == 'L' else -25), fy + 40), (vx + (25 if side == 'L' else -25), sy + 40), (sxp, sy + 40)],
                           'finished rows, local capture')
    # control / small global units: commands, expert ids, HC coefficients ride the slice column + tier streets
    G = P.blocks[P.idx['gunit']]
    for c in range(NCOL):
        for t in 'SN':
            sn = f's_{c}{t}'
            S = P.blocks[P.idx[sn]]
            g = (G['x'] + 300 + 60 * c, G['y'] if t == 'S' else G['y'] + G['h'])
            st_y = S['y'] + SLICE_H / 2 + (150 if t == 'S' else -150) + (12 if c % 2 else -12)
            p = (S['x'] + S['w'] / 2, st_y)
            P.link(f'ctl_{sn}', 'ctl', CTL, ('gunit', 'ctl', g), (sn, 'ctl', p),
                   [g, (g[0], st_y), p], 'commands/done + expert ids + HC coefs (tree on column + street)')
    # attention: q gathered on the mesh to s_1S / s_6S, down the slice column to the SM group; P.V rows from the
    # service half back up into the mesh; abutted faces are drawn as spread lanes
    def face(nm, a, b, bits, lanes, cls, note):
        (x1, y1), (x2, y2) = a, b
        for k in range(lanes):
            t = (k + 0.5) / lanes
            if abs(x1 - x2) < 1:   # vertical shared face at x: spread along y
                p0 = (x1, y1 + (y2 - y1) * t); p1 = (x1 + 1, y1 + (y2 - y1) * t)
            else:
                p0 = (x1 + (x2 - x1) * t, y1); p1 = (x1 + (x2 - x1) * t, y1 + 1)
            P.link(f'{nm}_{k}', cls, bits // lanes, (src_of[nm], 'f', p0), (dst_of[nm], 'f', p1), [p0, p1], note)
    src_of, dst_of = {}, {}
    for side, svc, c in (('W', 'svc_W', 1), ('E', 'svc_E', NCOL - 2)):
        S = P.blocks[P.idx[svc]]; Ph = P.blocks[P.idx['phy_hbm']]
        fx = S['x'] + S['w'] if side == 'W' else S['x']
        src_of[f'hbm{side}'], dst_of[f'hbm{side}'] = svc, 'phy_hbm'
        face(f'hbm{side}', (fx, 40), (fx, 1150), (8192 + 10912) // 2, 24, 'hbm', 'HBM read+request half (abutted face)')
        sm0 = f'sm_{side}0'; M = P.blocks[P.idx[sm0]]
        mx = M['x'] + M['w'] if side == 'W' else M['x']
        src_of[f'sm{side}'], dst_of[f'sm{side}'] = svc, sm0
        face(f'sm{side}', (S['x'] if side == 'W' else S['x'] + S['w'], 60), (S['x'] if side == 'W' else S['x'] + S['w'], 1000), 8192, 16, 'attn', 'scores / P (abutted face)')
        for k in range(1, 4):
            a_, b_ = f'sm_{side}{k - 1}', f'sm_{side}{k}'
            A = P.blocks[P.idx[a_]]
            xx = A['x'] if side == 'W' else A['x'] + A['w']
            src_of[f'smc{side}{k}'], dst_of[f'smc{side}{k}'] = a_, b_
            face(f'smc{side}{k}', (xx, 60), (xx, 1000), 4096, 8, 'attn', 'SM chain (abutted)')
        sn = f's_{c}S'; sp = pin(sn, 'S'); top = (S['x'] + S['w'] / 2, S['y'] + S['h'])
        P.link(f'q_{side}', 'attn', XB, (sn, 'q', sp), (svc, 'q', top), [(sp[0] - 200, sp[1]), (sp[0] - 200, top[1] + 120), (top[0] - 200, top[1] + 120), (top[0] - 200, top[1])], 'q heads from the mesh')
        P.link(f'pv_{side}', 'attn', XB, (svc, 'pv', top), (sn, 'pv', sp), [(top[0] + 200, top[1]), (top[0] + 200, top[1] + 60), (sp[0] + 200, top[1] + 60), (sp[0] + 200, sp[1])], 'P.V rows into the all-gather')
    for nm, c, src in (('bk_sel', 3, 'hbm_ctrl'), ('bk_col', 4, 'hbm_ctrl'), ('mix4_w', 2, 'svc_W'), ('mix4_e', 5, 'svc_E')):
        a, s_ = pin(nm, 'N'), pin(f's_{c}S', 'S')
        P.link(f'in_{nm}', 'attn', XB, (nm, 'o', a), (f's_{c}S', 'i', s_), [a, s_], 'into the mesh')
        b_ = pin(nm, 'S'); S = P.blocks[P.idx[src]]
        tgt = (b_[0] if S['x'] <= b_[0] <= S['x'] + S['w'] else S['x'] + S['w'] - 100, S['y'] + S['h'])
        P.link(f'h_{nm}', 'hbm', XB, (src, 'o', tgt), (nm, 'i', b_), [tgt, (tgt[0], b_[1] - 100), (b_[0], b_[1] - 100), b_], 'HBM rows')
    # collective edge engines: end slices <-> coll_edge <-> two link lanes each
    for side in 'WE':
        c = 0 if side == 'W' else NCOL - 1
        for t in 'SN':
            sn, ce = f's_{c}{t}', f'coll_{side}{t}'
            a, b = pin(sn, 'N' if t == 'S' else 'S'), pin(ce, 'S' if t == 'S' else 'N')
            P.link(f'cs_{side}{t}', 'coll', 2 * COLL_LANE, (sn, 'coll', a), (ce, 'coll', b), [a, b], 'slice ring stop <-> collective edge')
            P.link(f'sc_{side}{t}', 'coll', 2 * COLL_LANE, (ce, 'coll', b), (sn, 'coll', a), [(b[0] + 300, b[1]), (a[0] + 300, a[1])], '')
            for k in '01':
                lk = f'lk_{side}{t}{k}'
                LK = P.blocks[P.idx[lk]]
                S = P.blocks[P.idx[sn]]
                yst = S['y'] + SLICE_H / 2 + (-140 if k == '0' else 140)
                lx = LK['x'] + LK['w'] if side == 'W' else LK['x']
                ly = min(max(yst, LK['y'] + 20), LK['y'] + LK['h'] - 20)
                e = pin(ce, 'S' if t == 'N' else 'N')
                ex = e[0] - 300 if side == 'W' else e[0] + 300
                P.link(f'lt_{lk}', 'coll', COLL_LANE, (ce, 'tx' + k, (ex, e[1])), (lk, 'tx', (lx, ly)),
                       [(ex, e[1]), (ex, yst), (lx, yst), (lx, ly)], 'link lane tx (in the street)')
                P.link(f'lr_{lk}', 'coll', COLL_LANE, (lk, 'rx', (lx, ly + 10)), (ce, 'rx' + k, (ex + 60, e[1])),
                       [(lx, ly + 10), (lx, yst + 10), (ex + 60, yst + 10), (ex + 60, e[1])], 'link lane rx (in the street)')
    return P, facts


def geometry_facts(P, facts):
    """worst x-all-gather time of flight and local return, in um of Manhattan path"""
    slices = [b for b in P.blocks if b['kind'] == 'slice']
    frames = [b for b in P.blocks if b['kind'] == 'frame']
    fc = lambda b: (b['x'] + b['w'] / 2, b['y'] + b['h'] / 2)
    worst_ag = max(abs(fc(s)[0] - (f['x'] + (f['w'] if f['name'][-3] == 'L' else 0))) + abs(fc(s)[1] - (f['y'] + 150))
                   for s in slices for f in frames)
    ret = max(l['L'] for l in P.links if l['c'] == 'ret')
    ss = max(abs(fc(a)[0] - fc(b)[0]) + abs(fc(a)[1] - fc(b)[1]) for a in slices for b in slices)
    facts.update(worst_allgather_slice_to_frame_um=round(worst_ag), worst_local_return_um=round(ret),
                 worst_slice_to_slice_um=round(ss), phase_path_um=round(worst_ag + ret),
                 phase_path_stages=math.ceil(worst_ag / HOP_UM) + math.ceil(ret / HOP_UM),
                 scalar_exchange_stages=math.ceil(ss / HOP_UM))
    att = [P.blocks[P.idx[n]] for n in ('svc_W', 'svc_E')]
    facts['worst_slice_to_attention_um'] = round(max(min(abs(fc(s)[0] - fc(a)[0]) + abs(fc(s)[1] - fc(a)[1]) for a in att) for s in slices))
    facts['worst_attention_to_frame_um'] = round(max(min(abs(fc(a)[0] - fc(f)[0]) + abs(fc(a)[1] - fc(f)[1]) for a in att) for f in frames))
    return facts


def record(P, facts, args):
    keys = ('name', 'master', 'kind', 'group', 'reg', 'x', 'y', 'w', 'h')
    blocks = {k: [b[k] for b in P.blocks] for k in keys}
    return dict(schema='opentallas.dataflow.links.v1', id=args.id, label=args.label, design='ds_rom', revision=args.revision,
                outline=[0, 0, DIE_W, DIE_H], reach_um=HOP_UM, stages_explicit=True, token_designs=['ds_rom'],
                reach_source='405 um plan hop (0.9 x S81 measured reach 455 um, results/arch/die_reach_1016.json, rounded down)',
                blocks=blocks, links=P.links, facts=facts,
                provenance=dict(tool='tools/s81_dv/dv_plan.py', inputs=[]))


def draw(P, facts, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    col = dict(frame='#d9d9d9', slice='#2b7bba', unit='#e6a23c', phy='#8c564b', ctrl='#8c564b', svc='#c49c94', link='#7f7f7f')
    lc = dict(xring='#d62728', x_frame='#2ca02c', ret='#9467bd', ctl='#17becf', attn='#ff7f0e', hbm='#8c564b', coll='#e377c2')
    fig, ax = plt.subplots(figsize=(16.5, 13))
    for b in P.blocks:
        ax.add_patch(Rectangle((b['x'] / 1000, b['y'] / 1000), b['w'] / 1000, b['h'] / 1000, fc=col.get(b['kind'], '#ccc'),
                               ec='k', lw=0.4, alpha=0.9 if b['kind'] != 'frame' else 0.6))
        if b['kind'] in ('slice', 'unit', 'svc', 'phy'):
            ax.text((b['x'] + b['w'] / 2) / 1000, (b['y'] + b['h'] / 2) / 1000, b['name'], ha='center', va='center', fontsize=6,
                    color='w' if b['kind'] == 'slice' else 'k', rotation=90 if b['h'] > 2 * b['w'] else 0)
    for l in P.links:
        w = 0.3 + 2.2 * min(1.0, l['b'] / 4096)
        for h in l['h']:
            ax.plot([h[0] / 1000, h[2] / 1000], [h[1] / 1000, h[3] / 1000], color=lc.get(l['c'], 'k'), lw=w, alpha=0.75)
    for k, v in lc.items():
        ax.plot([], [], color=v, lw=2, label=k)
    ax.legend(loc='upper right', fontsize=7, ncol=7)
    ax.set_xlim(0, DIE_W / 1000); ax.set_ylim(0, DIE_H / 1000); ax.set_aspect('equal')
    ax.set_title(f"S81-DV candidate: 16 vector slices x 8 frames, mesh all-gather (hop <= {HOP_UM:.0f} um). "
                 f"worst cut {facts.get('worst_cut', '?')}, over-reach {facts.get('over_reach_bits', '?')} b, "
                 f"{facts.get('bit_mm', '?')} bit-mm", fontsize=9)
    ax.set_xlabel('mm'); ax.set_ylabel('mm')
    fig.tight_layout(); fig.savefig(out, dpi=150)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--id', default='s81_dv_p0')
    ap.add_argument('--label', default='S81-DV p0: 16 distributed vector slices, mesh all-gather (plan level)')
    ap.add_argument('--revision', default='dv-p0')
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    P, facts = build()
    geometry_facts(P, facts)
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fleet_viz'))
    import dataflow_links as dl
    links = [dict(l, mh=max(abs(h[2] - h[0]) + abs(h[3] - h[1]) for h in l['h']), bu=sum(abs(h[2] - h[0]) + abs(h[3] - h[1]) for h in l['h']) * l['b'])
             for l in P.links]
    m = dl.metrics(dict(outline=[0, 0, DIE_W, DIE_H], reach_um=HOP_UM, stages_explicit=True), links)
    facts.update(worst_cut=m['worst_cut'], over_reach_bits=m['over_reach_bits'], relays=m['relays'],
                 relay_bit_stages=m['relay_bit_stages'], bit_mm=round(m['sum_bit_um_hops'] / 1000),
                 cut_windows_over_limit=m['cut_windows_over_limit'],
                 slice_area_mm2=SLICE_W * SLICE_H / 1e6, n_frames=sum(b['kind'] == 'frame' for b in P.blocks))
    (out / 'plan.json').write_text(json.dumps(dict(facts=facts, blocks=P.blocks, links=P.links), indent=0))
    (out / 'dv_links_record.json').write_text(json.dumps(record(P, facts, a)))
    draw(P, facts, out / 'dv_flow.png')
    print(json.dumps(facts, indent=1))


if __name__ == '__main__':
    main()
