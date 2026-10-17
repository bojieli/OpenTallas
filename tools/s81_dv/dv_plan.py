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

RETICLE_W, RETICLE_H = 33000.0, 26000.0
RETICLE_MARGIN = 500.0           # every die edge >= 0.5 mm inside the reticle (HBM die practice)
SCOL_W = 1300.0                   # slice column: the slice width + 50 um (all vertical die wires end at the slice)
N9 = 6                            # 9-slot frames per 8-frame column (rest 10-slot): column 22.16 mm
EDGE = 300.0                      # link PHY strip on the W/E edges
NCOL = 8                          # cluster columns
PITCH = 2 * 1148.3 + SCOL_W
DIE_W = 2 * EDGE + NCOL * PITCH   # 29.38 mm
DIE_H = 25000.0                   # >= 0.5 mm per side under the reticle height
FRAME_W, FRAME_PITCH = 1139.6, 1148.3   # c26l column frame width / column pitch
H9, H10A, H10B = 2695.68, 2985.12, 3000.24   # c26l frame heights (9-slot, 10-slot a/b)
BAND = 1700.0                     # south band: HBM PHY + ctrl + service strip (svc 1.58 mm)
STREET = 380.0                    # horizontal ring street at each tier middle
SLICE_W, SLICE_H = 1250.0, 3500.0   # 2.8:1, 4.375 mm2
HOP_UM = 405.0                    # plan hop (0.9 x measured S81 reach 455 um, rounded down to the 405 plan rule)
XB = 1104                         # x stream beat: 64 FP8 codes + 2 exps (566 b) + second lane (538 b), as c26l cx+x2
RET = 68                          # frame return lane (dsfd_m2l_vr_68x1x)
CTL = 96                          # slice command (85 b) + done (9 b) + 2 status
COLL_LANE = 512


def chain(pts, hop=None):
    """Manhattan polyline through pts, cut into <= hop segments -> (hops, relays, length)"""
    hop = hop or HOP_UM
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
    """16 frame columns x 8 frames: N9 x H9 + (8 - N9) x H10 (H10A/H10B alternating) -> column 22.46 mm"""
    cols = []
    for k in range(16):
        rest = [H10A if (k + j) % 2 == 0 else H10B for j in range(8 - N9)]
        hs = sorted([H9] * N9 + rest)
        cols.append([hs[0], hs[7], hs[2], hs[5], hs[1], hs[6], hs[3], hs[4]])
    return cols


SLOTS = lambda h: 9 if h == H9 else 10


def build():
    P = Plan()
    pitch, scol_w = PITCH, SCOL_W
    assert DIE_W <= RETICLE_W - 2 * RETICLE_MARGIN and DIE_H <= RETICLE_H - 2 * RETICLE_MARGIN, (DIE_W, DIE_H)
    heights = column_heights()
    colx = lambda c: EDGE + c * pitch + FRAME_PITCH          # slice column left edge
    facts = dict(cluster_pitch_um=pitch, slice_column_um=scol_w)
    # ---------------------------------------------------------------- frames: one die-wide street per tier
    lo = lambda hs, t: sum(hs[4 * t:4 * t + 2])
    hi = lambda hs, t: sum(hs[4 * t + 2:4 * t + 4])
    st0 = BAND + max(lo(h, 0) for h in heights)
    t1 = st0 + STREET + max(hi(h, 0) for h in heights)
    st1 = t1 + max(lo(h, 1) for h in heights)
    streets = (st0, st1)
    ymax = 0.0
    for c in range(NCOL):
        x0 = EDGE + c * pitch
        for side, fx in (('L', x0), ('R', colx(c) + scol_w + (FRAME_PITCH - FRAME_W))):
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
    facts['frame_top_um'] = ymax
    assert ymax <= DIE_H - 250, ymax
    facts.update(die_um=[round(DIE_W, 1), DIE_H], die_mm2=round(DIE_W * DIE_H / 1e6, 1),
                 reticle_margin_um=[round((RETICLE_W - DIE_W) / 2, 1), (RETICLE_H - DIE_H) / 2],
                 rom_slots=sum(SLOTS(b['h']) for b in P.blocks if b['kind'] == 'frame'), rom_slots_c26l=60 * 9 + 68 * 10)
    # ---------------------------------------------------------------- slices (centred on their street)
    for c in range(NCOL):
        for t in range(2):
            ym = streets[t] + STREET / 2
            P.block(f's_{c}{"SN"[t]}', 'dsdv_slice', 'slice', f'cl{c}{"SN"[t]}', colx(c) + (scol_w - SLICE_W) / 2, ym - SLICE_H / 2, SLICE_W, SLICE_H)
    # ---------------------------------------------------------------- south band: [SM_W x4][svc_W][PHY+ctrl][svc_E][SM_E x4]
    # the HBM service halves abut the PHY; each attention softmax group (SU SM tiles) abuts its service half, so the
    # 8 kb score / P interface is a face, not a die wire (attention = PHY-side unit, irregular operator)
    phy_x = DIE_W / 2 - 4250
    P.block('phy_hbm', 'ot_hbm3e_phy_v41x_aw30_e8p5', 'phy', 'south', phy_x, 20, 8500, 1177)
    P.block('hbm_ctrl', 'dsfd_ctrl', 'ctrl', 'south', phy_x, 1210, 8500, 250)
    P.block('svc_W', 'dsfd_svc_half', 'svc', 'south', phy_x - 4260, 20, 4250, 1580)
    P.block('svc_E', 'dsfd_svc_half', 'svc', 'south', phy_x + 8510, 20, 4250, 1580)
    for k in range(4):
        P.block(f'sm_W{k}', 'ot_s81_su_sm', 'unit', 'south', phy_x - 4270 - (k + 1) * 1235, 20, 1231, 1058)
        P.block(f'sm_E{k}', 'ot_s81_su_sm', 'unit', 'south', phy_x + 12770 + k * 1235, 20, 1231, 1058)
    assert P.blocks[P.idx['sm_W3']]['x'] >= 0 and P.blocks[P.idx['sm_E3']]['x'] + 1231 <= DIE_W
    # ---------------------------------------------------------------- inter-tier void: global / edge units
    # the S tier's x chains use the void's lower part and the N tier's its upper part; the middle holds the small
    # global units (white space reused), 1.0 mm wide on the column's left; the right 270 um stay a channel
    # frame lanes run at the column edges (L: window 0, R: window 4), so units own the middle over the full void
    def chain_top_S(c):
        return P.blocks[P.idx[f's_{c}S']]['y'] + SLICE_H + 150
    def chain_bot_N(c):
        return P.blocks[P.idx[f's_{c}N']]['y'] - 150
    units = {0: [('coll_WS', 'dsdv_coll_edge', 1200), ('coll_WN', 'dsdv_coll_edge', 1200)],
             7: [('coll_ES', 'dsdv_coll_edge', 1200), ('coll_EN', 'dsdv_coll_edge', 1200)],
             1: [('bk_sel', 'dsfd_bk_selector', 2000)], 6: [('bk_col', 'dsfd_bk_collector', 2900)],
             2: [('mix4_w', 'dsfd_engram_mix4_half', 2600)], 5: [('mix4_e', 'dsfd_engram_mix4_half', 2600)],
             3: [('gunit', 'dsdv_gunit', 2800)], 4: [('seqhost', 'dsdv_seq_host', 2200)]}
    facts['void_free_um'] = {}
    for c, us in units.items():
        lo_, hi_ = chain_top_S(c), chain_bot_N(c)
        facts['void_free_um'][c] = round(hi_ - lo_)
        need = sum(h for _, _, h in us) + 100 * (len(us) - 1)
        assert need <= hi_ - lo_, (c, need, hi_ - lo_)
        y = (lo_ + hi_ - need) / 2
        for nm, master, h in us:
            wu = 680 if c in (0, NCOL - 1) else 980          # end columns leave window 3 to the ring end link
            P.block(nm, master, 'unit', 'void', colx(c) + 160, y, wu, h)
            y += h + 100
    ys, yn = streets[0] + STREET / 2, streets[1] + STREET / 2
    for side, xl in (('W', 0.0), ('E', DIE_W - 260)):
        for t, yc in (('S', ys), ('N', yn)):
            P.block(f'lk_{side}{t}0', 'ot_pdie_ucie' if t == 'S' else 'ot_pdie_serdes', 'link', 'edge', xl, yc - 2300, 260, 2250)
            P.block(f'lk_{side}{t}1', 'ot_pdie_serdes', 'link', 'edge', xl, yc + 50, 260, 2250)

    # ---------------------------------------------------------------- links
    def pin(b, side):
        x, y = P.c(b); B = P.blocks[P.idx[b]]
        return {'W': (B['x'], y), 'E': (B['x'] + B['w'], y), 'N': (x, B['y'] + B['h']), 'S': (x, B['y'])}[side]
    # x all-gather ring: E-W along each tier street (both directions), N-S at the two end columns
    for t in 'SN':
        for c in range(NCOL - 1):
            a, b = f's_{c}{t}', f's_{c + 1}{t}'
            for d, (u, v, off) in (('E', (a, b, -80)), ('W', (b, a, 80))):
                p0, p1 = pin(u, 'E' if d == 'E' else 'W'), pin(v, 'W' if d == 'E' else 'E')
                P.link(f'xr{d}_{c}{t}', 'xring', XB, (u, 'xr' + d, (p0[0], p0[1] + off)), (v, 'xr' + d, (p1[0], p1[1] + off)),
                       [(p0[0], p0[1] + off), (p1[0], p1[1] + off)], 'x all-gather / collective / scalar exchange (TDM)')
    for c in (0, NCOL - 1):
        a, b = f's_{c}S', f's_{c}N'
        xr = colx(c) + 900
        for d, (u, v, dx) in (('N', (a, b, -30)), ('S', (b, a, 30))):
            p0, p1 = pin(u, 'N' if d == 'N' else 'S'), pin(v, 'S' if d == 'N' else 'N')
            P.link(f'xv{d}_{c}', 'xring', XB, (u, 'xv' + d, (xr + dx, p0[1])), (v, 'xv' + d, (xr + dx, p1[1])),
                   [(xr + dx, p0[1]), (xr + dx, p1[1])], 'ring end column link')
    # slice <-> its 8 frames: taps facing the slice body cross the 25-um gap; the others run in fixed column lanes
    # (L side x offsets 110-320, R side 560-770); x is daisy-chained per half-column -> 4 x-out ports per slice
    for c in range(NCOL):
        for t in range(2):
            sn = f's_{c}{"SN"[t]}'
            S = P.blocks[P.idx[sn]]
            for side in 'LR':
                for r in range(4):
                    fn = f'f_{c}{side}{t}{r}'
                    F = P.blocks[P.idx[fn]]
                    fx = F['x'] + F['w'] if side == 'L' else F['x']
                    fy = F['y'] + 400
                    sxp = S['x'] if side == 'L' else S['x'] + S['w']
                    vx = colx(c) + (20 + 15 * r if side == 'L' else SCOL_W - 125 + 15 * r)
                    sy = S['y'] if fy < S['y'] else S['y'] + S['h']
                    if r in (1, 2):
                        if S['y'] + 100 <= fy <= S['y'] + S['h'] - 100:
                            P.link(f'x_{fn}', 'x_frame', XB, (sn, 'xf', (sxp, fy)), (fn, 'x', (fx, fy)), [(sxp, fy), (fx, fy)], 'x chain head (facing)')
                            P.link(f'r_{fn}', 'ret', RET, (fn, 'ret', (fx, fy + 60)), (sn, 'ret', (sxp, fy + 60)), [(fx, fy + 60), (sxp, fy + 60)], 'finished rows')
                            continue
                        P.link(f'x_{fn}', 'x_frame', XB, (sn, 'xf', (vx, sy)), (fn, 'x', (fx, fy)), [(vx, sy), (vx, fy), (fx, fy)], 'x chain head')
                    else:
                        pn = f'f_{c}{side}{t}{1 if r == 0 else 2}'
                        PF = P.blocks[P.idx[pn]]
                        pfx, pfy = (PF['x'] + PF['w'] if side == 'L' else PF['x']), PF['y'] + 400 + 120
                        P.link(f'x_{fn}', 'x_frame', XB, (pn, 'xo', (pfx, pfy)), (fn, 'x', (fx, fy)), [(pfx, pfy), (vx, pfy), (vx, fy), (fx, fy)], 'x chain forward (frame -> next frame)')
                    P.link(f'r_{fn}', 'ret', RET, (fn, 'ret', (fx, fy + 60)), (sn, 'ret', (vx + 30, sy)), [(fx, fy + 60), (vx + 30, fy + 60), (vx + 30, sy)], 'finished rows')
    # void units <-> their column's slices (vertical in the column's right-hand lanes, offsets 900-1100)
    vpair = {'coll_WS': ('s_0S', 'S'), 'coll_WN': ('s_0N', 'N'), 'coll_ES': ('s_7S', 'S'), 'coll_EN': ('s_7N', 'N'),
             'bk_sel': ('s_1S', 'S'), 'bk_col': ('s_6S', 'S'), 'mix4_w': ('s_2N', 'N'), 'mix4_e': ('s_5N', 'N'),
             'seqhost': ('s_4N', 'N')}
    for u, (sn, t) in vpair.items():
        U, S = P.blocks[P.idx[u]], P.blocks[P.idx[sn]]
        c = int(sn[2]); xa = colx(c) + 640 if c not in (0, NCOL - 1) else colx(c) + 520
        uy = U['y'] if t == 'S' else U['y'] + U['h']
        sy = S['y'] + S['h'] if t == 'S' else S['y']
        bits = 2 * COLL_LANE if u.startswith('coll') else XB
        P.link(f'u_{u}', 'coll' if u.startswith('coll') else 'unit', bits, (u, 'o', (xa, uy)), (sn, 'i', (xa, sy)), [(xa, uy), (xa, sy)], 'unit -> slice ring stop')
        P.link(f'v_{u}', 'coll' if u.startswith('coll') else 'unit', bits, (sn, 'o', (xa + 60, sy)), (u, 'i', (xa + 60, uy)), [(xa + 60, sy), (xa + 60, uy)], 'slice ring stop -> unit')
    # G-unit: commands, expert ids, HC coefficients to s_3S / s_3N, then along the streets through the ring stops
    G = P.blocks[P.idx['gunit']]
    for c in range(NCOL):
        for t in 'SN':
            sn = f's_{c}{t}'
            S = P.blocks[P.idx[sn]]
            gx = colx(3) + 470 + 10 * c
            g = (gx, G['y'] if t == 'S' else G['y'] + G['h'])
            st_y = S['y'] + SLICE_H / 2 + (150 if t == 'S' else -150)
            p = (S['x'] + S['w'] / 2, st_y)
            P.link(f'ctl_{sn}', 'ctl', CTL, ('gunit', 'ctl', g), (sn, 'ctl', p), [g, (gx, st_y), p], 'ctl tree (column + street, via ring stops)')
    # attention: q from s_1S / s_6S down the column to the service half; P.V rows back up; abutted faces as lanes
    src_of, dst_of = {}, {}
    def face(nm, a, b, bits, lanes, cls, note):
        (x1, y1), (x2, y2) = a, b
        for k in range(lanes):
            t = (k + 0.5) / lanes
            p0 = (x1, y1 + (y2 - y1) * t); p1 = (x1 + 1, y1 + (y2 - y1) * t)
            P.link(f'{nm}_{k}', cls, bits // lanes, (src_of[nm], 'f', p0), (dst_of[nm], 'f', p1), [p0, p1], note)
    for side, svc, c in (('W', 'svc_W', 1), ('E', 'svc_E', NCOL - 2)):
        S = P.blocks[P.idx[svc]]
        fx = S['x'] + S['w'] if side == 'W' else S['x']
        src_of[f'hbm{side}'], dst_of[f'hbm{side}'] = svc, 'phy_hbm'
        face(f'hbm{side}', (fx, 40), (fx, 1150), (8192 + 10912) // 2, 24, 'hbm', 'HBM read+request half (abutted face)')
        src_of[f'sm{side}'], dst_of[f'sm{side}'] = svc, f'sm_{side}0'
        xs = S['x'] if side == 'W' else S['x'] + S['w']
        face(f'sm{side}', (xs, 60), (xs, 1000), 8192, 16, 'attn', 'scores / P (abutted face)')
        for k in range(1, 4):
            a_, b_ = f'sm_{side}{k - 1}', f'sm_{side}{k}'
            A = P.blocks[P.idx[a_]]
            src_of[f'smc{side}{k}'], dst_of[f'smc{side}{k}'] = a_, b_
            face(f'smc{side}{k}', (A['x'] if side == 'W' else A['x'] + A['w'], 60), (A['x'] if side == 'W' else A['x'] + A['w'], 1000), 4096, 8, 'attn', 'SM chain (abutted)')
        sn = f's_{c}S'; Sl = P.blocks[P.idx[sn]]
        top = S['y'] + S['h']
        qx, px = colx(c) + 620, colx(c) + 690
        sxq = min(max(qx, S['x'] + 50), S['x'] + S['w'] - 150)
        P.link(f'q_{side}', 'attn', XB, (sn, 'q', (qx, Sl['y'])), (svc, 'q', (sxq, top)), [(qx, Sl['y']), (qx, top + 100), (sxq, top + 100), (sxq, top)], 'q heads from the ring')
        P.link(f'pv_{side}', 'attn', XB, (svc, 'pv', (sxq + 70, top)), (sn, 'pv', (px, Sl['y'])), [(sxq + 70, top), (sxq + 70, top + 170), (px, top + 170), (px, Sl['y'])], 'P.V rows into the all-gather')
    # collective lanes: edge PHYs <-> end-slice outer face along the street (ring-stop feed-through to coll_edge)
    for side in 'WE':
        c = 0 if side == 'W' else NCOL - 1
        for t in 'SN':
            sn = f's_{c}{t}'; S = P.blocks[P.idx[sn]]
            sxf = S['x'] if side == 'W' else S['x'] + S['w']
            for k in '01':
                lk = f'lk_{side}{t}{k}'; LK = P.blocks[P.idx[lk]]
                yst = S['y'] + SLICE_H / 2 + (-140 if k == '0' else 140)
                lx = LK['x'] + LK['w'] if side == 'W' else LK['x']
                ly = min(max(yst, LK['y'] + 20), LK['y'] + LK['h'] - 20)
                P.link(f'lt_{lk}', 'coll', COLL_LANE, (sn, 'tx' + k, (sxf, yst)), (lk, 'tx', (lx, ly)), [(sxf, yst), (lx, yst), (lx, ly)], 'link lane tx (street)')
                P.link(f'lr_{lk}', 'coll', COLL_LANE, (lk, 'rx', (lx, ly + 10)), (sn, 'rx' + k, (sxf, yst + 10)), [(lx, ly + 10), (lx, yst + 10), (sxf, yst + 10)], 'link lane rx (street)')
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


def fill(P, facts, ws):
    """Fill every over-channel empty rectangle inside a slice column with a designated fill block (PDN decap for
    the slices' SU/HC lanes + relay / repeater site bank for the column and street die nets + ECO spares).  The
    block keeps 130 um clear on both column edges: those are the frame x-chain / return lanes (routing channel)."""
    colx = lambda c: EDGE + c * PITCH + FRAME_PITCH
    r = ws.analyse(dict(facts=facts, blocks=P.blocks))
    k = 0
    for e in r['over_channel']:
        for c in range(NCOL):
            x0, x1 = colx(c), colx(c) + SCOL_W
            if e['x'] >= x0 - 60 and e['x'] + e['w'] <= x1 + 60:
                fx0, fx1 = max(float(e['x']), x0 + 130), min(float(e['x'] + e['w']), x1 - 130)
                y0, y1 = max(float(e['y']) + 60, BAND + 300), float(e['y'] + e['h']) - 60   # band edge = channel
                # split at every vertical die-link segment crossing this y-span (lanes stay routing channel)
                cuts = sorted({h[0] for l in P.links for h in l['h'] if abs(h[0] - h[2]) < 1 and fx0 - 60 < h[0] < fx1 + 60
                               and min(h[1], h[3]) < y1 and max(h[1], h[3]) > y0})
                edges = [fx0] + [v for c_ in cuts for v in (c_ - 60, c_ + 60)] + [fx1]
                for a_, b_ in zip(edges[0::2], edges[1::2]):
                    if b_ - a_ > 300 and y1 - y0 > 300:
                        P.block(f'fill_{c}_{k}', 'dsdv_fill_dcap_rly', 'fill', 'fill', a_, y0, b_ - a_, y1 - y0)
                        k += 1
                break
        else:   # outside the slice columns (south band corners / above the SM tiles): PHY-side decap
            if e['w'] > 420 and e['h'] > 420 and e['y'] + e['h'] <= BAND + 60:
                P.block(f'fill_b_{k}', 'dsdv_fill_dcap_phy', 'fill', 'fill', float(e['x']) + 30, float(e['y']) + 30,
                        float(e['w']) - 60, float(e['h']) - 60)
                k += 1
    facts['fill_blocks'] = k
    facts['fill_mm2'] = round(sum(b['w'] * b['h'] for b in P.blocks if b['kind'] == 'fill') / 1e6, 1)
    facts['whitespace_after'] = {kk: v for kk, v in ws.analyse(dict(facts=facts, blocks=P.blocks)).items() if kk != 'over_channel'}


def record(P, facts, args):
    keys = ('name', 'master', 'kind', 'group', 'reg', 'x', 'y', 'w', 'h')
    blocks = {k: [b[k] for b in P.blocks] for k in keys}
    return dict(schema='opentallas.dataflow.links.v1', id=args.id, label=args.label, design='ds_rom', revision=args.revision,
                outline=[DIE_W, DIE_H],      # [W, H] in um (the Explorer's model.js reads W = outline[0], H = outline[1])
                reach_um=HOP_UM, stages_explicit=True, token_designs=['ds_rom'],
                pins='plan points (S81-DV dv_plan.py), not generated pins',
                direction='first end drives (plan order)',
                registers=f'relay flops explicit per link: hops cut at <= {HOP_UM:.0f} um, stages = hops - 1 (die-level repair_design repeaters between flops)',
                reach_source='405 um plan hop (0.9 x S81 measured reach 455 um, results/arch/die_reach_1016.json, rounded down)',
                blocks=blocks, links=P.links, facts=facts,
                provenance=dict(tool='tools/s81_dv/dv_plan.py', inputs=[]))


def draw(P, facts, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    col = dict(frame='#d9d9d9', slice='#2b7bba', unit='#e6a23c', phy='#8c564b', ctrl='#8c564b', svc='#c49c94', link='#7f7f7f', fill='#c7e9c0')
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
    ax.set_title(f"S81-DV p1: 16 slices x 8 frames, slice ring (hop <= {HOP_UM:.0f} um). "
                 f"worst cut {facts.get('worst_cut', '?')}, over-reach {facts.get('over_reach_bits', '?')} b, "
                 f"{facts.get('bit_mm', '?')} bit-mm", fontsize=9)
    ax.set_xlabel('mm'); ax.set_ylabel('mm')
    fig.tight_layout(); fig.savefig(out, dpi=150)


def main():
    global HOP_UM
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--id', default='s81_dv_p1')
    ap.add_argument('--label', default='S81-DV p1: 16 distributed vector slices, slice ring, narrow columns, 0.5 mm+ reticle margin (plan level)')
    ap.add_argument('--revision', default='dv-p1')
    ap.add_argument('--hop-um', type=float, default=HOP_UM, help='plan hop (sensitivity: H-REACH unbuffered 200 um)')
    ap.add_argument('--fill', action='store_true', help='owner rule no-empty-regions-1017: fill slice-column stretches')
    a = ap.parse_args()
    HOP_UM = a.hop_um
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    P, facts = build()
    geometry_facts(P, facts)
    import whitespace as ws
    facts['whitespace_before'] = {k: v for k, v in ws.analyse(dict(facts=facts, blocks=P.blocks)).items() if k != 'over_channel'}
    if a.fill:
        fill(P, facts, ws)
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fleet_viz'))
    import dataflow_links as dl
    links = [dict(l, mh=max(abs(h[2] - h[0]) + abs(h[3] - h[1]) for h in l['h']), bu=sum(abs(h[2] - h[0]) + abs(h[3] - h[1]) for h in l['h']) * l['b'])
             for l in P.links]
    m = dl.metrics(dict(outline=[0, 0, DIE_W, DIE_H], reach_um=HOP_UM, stages_explicit=True), links)
    facts['hop_um'] = HOP_UM
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
