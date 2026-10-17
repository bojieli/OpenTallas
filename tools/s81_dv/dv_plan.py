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
LAYOUT = 'p1'                     # p1/p2: 1.30-mm columns; p3 (cancelled 10-17): 0.95-mm columns
ROW0_MX = False                   # p1b: row-0 frames placed MX so their cfifo x tap faces their slice
SVC_W = 4250.0
LANES, LANE_DX = 1, 6.0           # p4c-lanes: 1,104-b links as LANES x 276-b lanes
TIER_W = 0                        # p4c: per-column tier-exchange width (0 = p4b end-column ring)
UNIT_W, UNIT_WE = 980.0, 680.0         # void unit width (end columns narrower: ring end link)
HOP_UM = 405.0                    # plan hop (0.9 x measured S81 reach 455 um, rounded down to the 405 plan rule)
XB = 1104                         # x stream beat: 64 FP8 codes + 2 exps (566 b) + second lane (538 b), as c26l cx+x2
RET = 68                          # frame return lane (dsfd_m2l_vr_68x1x)
CTL = 96                          # slice command (85 b) + done (9 b) + 2 status
COLL_LANE = 512


def chain(pts, hop=None):
    """Manhattan polyline through pts, cut by ARC LENGTH into n = ceil(L / hop) equal hops -> (hops, relays, length).
    Stations sit on straight segments: a cut that lands within 30 um of a corner is moved 30 um back along the
    straight (the die wire, with its repeaters, makes the turn between stations; no corner relay needed)."""
    hop = hop or HOP_UM
    legs = []
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        for a, b in (((x1, y1), (x2, y1)), ((x2, y1), (x2, y2))):
            d = abs(b[0] - a[0]) + abs(b[1] - a[1])
            if d > 0:
                legs.append((a, b, d))
    L = sum(d for _, _, d in legs)
    if not legs:
        return [], 0, 0.0
    n = max(1, math.ceil(L / hop))
    corners = []
    acc = 0.0
    for _, _, d in legs[:-1]:
        acc += d; corners.append(acc)
    cuts = []
    for k in range(1, n):
        t = k * L / n
        for c in corners:
            if abs(t - c) < 30.0:
                t = c - 30.0 if t <= c else c + 30.0
        cuts.append(t)
    # build segments (straight pieces) between consecutive cut points, splitting at corners
    def at(t):
        acc = 0.0
        for a, b, d in legs:
            if t <= acc + d + 1e-9:
                f = (t - acc) / d
                return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            acc += d
        return legs[-1][1]
    marks = sorted(set([0.0] + cuts + corners + [L]))
    segs = []
    for t0, t1 in zip(marks, marks[1:]):
        if t1 - t0 > 1e-6:
            p0, p1 = at(t0), at(t1)
            segs.append((p0[0], p0[1], p1[0], p1[1], t1 in cuts or t1 == L))
    # hops = groups of segments between stations; record each straight piece, stations = cuts
    out = [(x1, y1, x2, y2) for x1, y1, x2, y2, _ in segs]
    chain.stations = [at(t) for t in cuts]
    return out, len(cuts), L


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
        """src/dst = (block, port, (x, y)); pts = routed waypoints from src pin to dst pin.  With LANES > 1 a 1,104-b
        link becomes LANES parallel lanes of 1104/LANES bits (own station chain + forwarded clock each, cycle
        aligned; p4c-lanes, coordinator 10-17), offset LANE_DX um across the route."""
        if LANES > 1 and bits == XB:
            for k in range(LANES):
                d = (k - (LANES - 1) / 2) * LANE_DX
                sh = lambda q: (q[0] + d, q[1] + d)
                self._link(f'{lid}_l{k}', cls, bits // LANES, (src[0], src[1], sh(src[2])), (dst[0], dst[1], sh(dst[2])),
                           [sh(q) for q in pts], note)
            return
        self._link(lid, cls, bits, src, dst, pts, note)

    def _link(self, lid, cls, bits, src, dst, pts, note=None):
        segs, s, L = chain(pts)
        self.links.append(dict(i=lid, c=cls, b=bits, d=1, s=s, L=round(L, 1),
                               sp=[[round(x, 1), round(y, 1)] for x, y in chain.stations],
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


def place_units_p3(P, facts, colx, streets):
    """p3: shared units 0.9 mm wide in the slice columns, one per column segment side, each linked to the nearest
    slice of its column (lower unit -> S slice, upper unit -> N slice); x-chain lanes end within ~1.1 mm of a slice."""
    U = 900.0
    segs = {}
    for c in range(NCOL):
        S, N = P.blocks[P.idx[f's_{c}S']], P.blocks[P.idx[f's_{c}N']]
        segs[c] = dict(bot=(BAND + 120, S['y'] - 1100), void=(S['y'] + S['h'] + 1100, N['y'] - 1100),
                       top=(N['y'] + N['h'] + 1100, DIE_H - 250))
    # (name, master, area mm2, column, segment, link-to tier, width)
    # bk (index select / collect: HBM-side) in the bottom ends next to the PHY; G-unit, seq/host, collective edge
    # engines and Engram mix in the inter-tier voids (central / edge-adjacent); collector split in three <=3:1 pieces
    plan = [('coll_WS', 'dsdv_coll_edge', 0.84, 0, 'void', 'S', 560), ('coll_WN', 'dsdv_coll_edge', 0.84, 0, 'void', 'N', 560),
            ('coll_ES', 'dsdv_coll_edge', 0.84, 7, 'void', 'S', 560), ('coll_EN', 'dsdv_coll_edge', 0.84, 7, 'void', 'N', 560),
            ('gunit_r', 'dsdv_gunit_router', 1.40, 3, 'void', 'S', U), ('gunit_h', 'dsdv_gunit_hc', 1.35, 3, 'void', 'N', U),
            ('seqhost', 'dsdv_seq_host', 2.20, 4, 'void', 'S', U),
            ('mix4_w0', 'dsfd_engram_mix4_quarter', 1.30, 2, 'void', 'S', U), ('mix4_w1', 'dsfd_engram_mix4_quarter', 1.30, 2, 'void', 'N', U),
            ('mix4_e0', 'dsfd_engram_mix4_quarter', 1.30, 5, 'void', 'S', U), ('mix4_e1', 'dsfd_engram_mix4_quarter', 1.30, 5, 'void', 'N', U),
            ('bk_sel', 'dsfd_bk_selector', 1.70, 3, 'bot', 'S', U), ('bk_col0', 'dsfd_bk_collector_third', 1.55, 2, 'bot', 'S', U),
            ('bk_col1', 'dsfd_bk_collector_third', 1.55, 4, 'bot', 'S', U), ('bk_col2', 'dsfd_bk_collector_third', 1.55, 5, 'bot', 'S', U)]
    used = {}
    vpair = {}
    for nm, master, a, c, sg, t, w in plan:
        h = a * 1e6 / w
        lo, hi = segs[c][sg]
        k = used.get((c, sg), [])
        y = (lo if t == 'S' else hi - h) if sg == 'void' else hi - h    # ends: hug the slice side of the segment
        for (ya, yb) in k:
            assert y + h <= ya - 100 or y >= yb + 100, (nm, c, sg)
        assert lo <= y and y + h <= hi, (nm, c, sg, lo, hi, h)
        assert max(w, h) / min(w, h) <= 3.05 or nm.startswith('coll'), (nm, w, h)
        P.block(nm, master, 'unit', 'void', colx(c) + 25, y, w, h)
        k.append((y, y + h)); used[(c, sg)] = k
        vpair[nm] = (f's_{c}{t}', t)
    facts['_vpair'] = vpair
    facts['p3_segments_um'] = {c: {k: round(v[1] - v[0]) for k, v in sg.items()} for c, sg in segs.items()}


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
                    mst = ('col_h9' if h == H9 else 'col_h10') + ('_MX' if (ROW0_MX or LAYOUT == 'p3') and r == 0 else '')
                    P.block(f'f_{c}{side}{t}{r}', mst, 'frame', f'cl{c}{"SN"[t]}', fx, y, FRAME_W, h)
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
    svh = 13430000.0 / 2 / SVC_W        # service half area kept (13.43 mm2 total), height follows the width
    P.block('svc_W', 'dsfd_svc_half', 'svc', 'south', phy_x - SVC_W - 10, 20, SVC_W, svh)
    P.block('svc_E', 'dsfd_svc_half', 'svc', 'south', phy_x + 8510, 20, SVC_W, svh)
    assert svh <= BAND - 20, svh
    for k in range(4):
        P.block(f'sm_W{k}', 'ot_s81_su_sm', 'unit', 'south', phy_x - SVC_W - 20 - (k + 1) * 1235, 20, 1231, 1058)
        P.block(f'sm_E{k}', 'ot_s81_su_sm', 'unit', 'south', phy_x + 8520 + SVC_W + k * 1235, 20, 1231, 1058)
    assert P.blocks[P.idx['sm_W3']]['x'] >= 0 and P.blocks[P.idx['sm_E3']]['x'] + 1231 <= DIE_W
    # ---------------------------------------------------------------- inter-tier void: global / edge units
    # the S tier's x chains use the void's lower part and the N tier's its upper part; the middle holds the small
    # global units (white space reused), 1.0 mm wide on the column's left; the right 270 um stay a channel
    # frame lanes run at the column edges (L: window 0, R: window 4), so units own the middle over the full void
    def chain_top_S(c):
        return P.blocks[P.idx[f's_{c}S']]['y'] + SLICE_H + 150
    def chain_bot_N(c):
        return P.blocks[P.idx[f's_{c}N']]['y'] - 150
    if LAYOUT == 'p3':
        place_units_p3(P, facts, colx, streets)
    else:
      units = {0: [('coll_WS', 'dsdv_coll_edge', 1200), ('coll_WN', 'dsdv_coll_edge', 1200)],
             7: [('coll_ES', 'dsdv_coll_edge', 1200), ('coll_EN', 'dsdv_coll_edge', 1200)],
             1: [('bk_sel', 'dsfd_bk_selector', 2000)], 6: [('bk_col', 'dsfd_bk_collector', 2900)],
             2: [('mix4_w', 'dsfd_engram_mix4_half', 2600)], 5: [('mix4_e', 'dsfd_engram_mix4_half', 2600)],
             3: [('gunit', 'dsdv_gunit', 2800)], 4: [('seqhost', 'dsdv_seq_host', 2200)]}
      if LAYOUT == 'p4':
          # p4b (slice-master variants, S81-SLICE 10-17): one void-side (V) or band-side (B) use per slice ->
          # bk to the column-2/5 S slices (the column-1/6 S slices keep only the attention B port)
          units.pop(1); units.pop(6)
          units[2] = [('bk_sel', 'dsfd_bk_selector', 2000), ('mix4_w', 'dsfd_engram_mix4_half', 2600)]
          units[5] = [('bk_col', 'dsfd_bk_collector', 2900), ('mix4_e', 'dsfd_engram_mix4_half', 2600)]
      facts['void_free_um'] = {}
      for c, us in units.items():
          lo_, hi_ = chain_top_S(c), chain_bot_N(c)
          facts['void_free_um'][c] = round(hi_ - lo_)
          need = sum(h for _, _, h in us) + 100 * (len(us) - 1)
          assert need <= hi_ - lo_, (c, need, hi_ - lo_)
          # each unit hugs the slice it talks to (no empty area on a link path); the G-unit (ctl to both tiers) and
          # stacked pairs keep the centre / their ends
          tier = {'coll_WS': 'S', 'coll_ES': 'S', 'bk_sel': 'S', 'bk_col': 'S', 'coll_WN': 'N', 'coll_EN': 'N',
                  'mix4_w': 'N', 'mix4_e': 'N', 'seqhost': 'N'}
          if len(us) == 1 and us[0][0] in tier:
              y = lo_ if tier[us[0][0]] == 'S' else hi_ - us[0][2]
          elif len(us) == 2:
              y = None
          else:
              y = (lo_ + hi_ - need) / 2
          for j, (nm, master, h) in enumerate(us):
              wu = UNIT_WE if c in (0, NCOL - 1) else UNIT_W    # end columns leave room to the ring end link
              hh = h * (980.0 if c not in (0, NCOL - 1) else 680.0) / wu   # keep the unit area at the narrower width
              yy = y if y is not None else (lo_ if j == 0 else hi_ - hh)
              if y is not None and tier.get(nm) == 'N' and len(us) == 1:
                  yy = hi_ - hh
              P.block(nm, master, 'unit', 'void', colx(c) + (160 if LAYOUT != 'p4' else 75), yy, wu, hh)
              if y is not None:
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
    for c in ((0, NCOL - 1) if LAYOUT != 'p4' else ()):
        a, b = f's_{c}S', f's_{c}N'
        xr = colx(c) + {'p3': 690, 'p4': 680}.get(LAYOUT, 900)
        for d, (u, v, dx) in (('N', (a, b, -30)), ('S', (b, a, 30))):
            p0, p1 = pin(u, 'N' if d == 'N' else 'S'), pin(v, 'S' if d == 'N' else 'N')
            P.link(f'xv{d}_{c}', 'xring', XB, (u, 'xv' + d, (xr + dx, p0[1])), (v, 'xv' + d, (xr + dx, p1[1])),
                   [(xr + dx, p0[1]), (xr + dx, p1[1])], 'ring end column link')
    if LAYOUT == 'p4' and TIER_W:
        # p4c (owner question 10-17): per-column tier exchange -- every column links its S and N slice through the
        # column's void units (units become ring stops), width TIER_W bits per direction, instead of two fat end links
        vunits = sorted((b for b in P.blocks if b['kind'] == 'unit' and b['group'] in ('void', 'centre', 'edge')),
                        key=lambda b: b['y'])
        for c in range(NCOL):
            x0c, x1c = colx(c), colx(c) + SCOL_W
            us = [b['name'] for b in vunits if x0c <= b['x'] + b['w'] / 2 <= x1c]
            chainv = [f's_{c}S'] + us + [f's_{c}N']
            x = colx(c) + SCOL_W / 2      # column centre: chain segments start / end on the unit faces
            for u, v in zip(chainv, chainv[1:]):
                U, V = P.blocks[P.idx[u]], P.blocks[P.idx[v]]
                y0, y1 = U['y'] + U['h'], V['y']
                P.link(f'tvN_{u}', 'xtier', TIER_W, (u, 'vN', (x - 12, y0)), (v, 'vS', (x - 12, y1)), [(x - 12, y0), (x - 12, y1)], 'per-column tier exchange (through the column units)')
                P.link(f'tvS_{v}', 'xtier', TIER_W, (v, 'vS', (x + 12, y1)), (u, 'vN', (x + 12, y0)), [(x + 12, y1), (x + 12, y0)], 'per-column tier exchange (through the column units)')
        facts['tier_w'] = TIER_W
    elif LAYOUT == 'p4':
        # p4b: the end-column vertical ring segment runs THROUGH the collective edge engines (ring stops):
        # s_cS V -> coll_xS -> coll_xN -> s_cN V and back; the engines fold / inject collective traffic on it
        for c, side in ((0, 'W'), (NCOL - 1, 'E')):
            chainv = [f's_{c}S', f'coll_{side}S', f'coll_{side}N', f's_{c}N']
            for u, v in zip(chainv, chainv[1:]):
                U, V = P.blocks[P.idx[u]], P.blocks[P.idx[v]]
                x = colx(c) + 330
                y0, y1 = U['y'] + U['h'], V['y']
                P.link(f'xvN_{u}', 'xring', XB, (u, 'vN', (x - 30, y0)), (v, 'vS', (x - 30, y1)), [(x - 30, y0), (x - 30, y1)], 'end-column ring (through the collective engines)')
                P.link(f'xvS_{v}', 'xring', XB, (v, 'vS', (x + 30, y1)), (u, 'vN', (x + 30, y0)), [(x + 30, y1), (x + 30, y0)], 'end-column ring (through the collective engines)')
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
                    fy = F['y'] + F['h'] - 400 if ((LAYOUT == 'p3' or ROW0_MX) and r == 0) else F['y'] + 400   # p3: row 0 MX
                    sxp = S['x'] if side == 'L' else S['x'] + S['w']
                    vx = colx(c) + {'p3': (8 + 9 * r if side == 'L' else SCOL_W - 78 + 9 * r),
                                    'p4': (10 + 10 * r if side == 'L' else SCOL_W - 95 + 10 * r)}.get(
                                    LAYOUT, 20 + 15 * r if side == 'L' else SCOL_W - 125 + 15 * r)
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
                        if (LAYOUT == 'p3' or ROW0_MX) and r == 0:
                            pfy = PF['y'] + 400 - 120   # chain forward leaves row 1 toward row 0's MX tap
                        P.link(f'x_{fn}', 'x_frame', XB, (pn, 'xo', (pfx, pfy)), (fn, 'x', (fx, fy)), [(pfx, pfy), (vx, pfy), (vx, fy), (fx, fy)], 'x chain forward (frame -> next frame)')
                    P.link(f'r_{fn}', 'ret', RET, (fn, 'ret', (fx, fy + 60)), (sn, 'ret', (vx + 30, sy)), [(fx, fy + 60), (vx + 30, fy + 60), (vx + 30, sy)], 'finished rows')
    # void units <-> their column's slices (vertical in the column's right-hand lanes, offsets 900-1100)
    if LAYOUT == 'p4' and TIER_W:
        facts['_vpair'] = {}
    elif LAYOUT == 'p4':
        facts['_vpair'] = {'bk_sel': ('s_2S', 'S'), 'bk_col': ('s_5S', 'S'), 'mix4_w': ('s_2N', 'N'), 'mix4_e': ('s_5N', 'N'),
                           'seqhost': ('s_4N', 'N')}
    vpair = facts.pop('_vpair') if '_vpair' in facts else {'coll_WS': ('s_0S', 'S'), 'coll_WN': ('s_0N', 'N'), 'coll_ES': ('s_7S', 'S'), 'coll_EN': ('s_7N', 'N'),
             'bk_sel': ('s_1S', 'S'), 'bk_col': ('s_6S', 'S'), 'mix4_w': ('s_2N', 'N'), 'mix4_e': ('s_5N', 'N'),
             'seqhost': ('s_4N', 'N')}
    for u, (sn, t) in vpair.items():
        U, S = P.blocks[P.idx[u]], P.blocks[P.idx[sn]]
        c = int(sn[2]); xa = colx(c) + 640 if c not in (0, NCOL - 1) else colx(c) + 520
        if LAYOUT == 'p3':
            xa = colx(c) + (300 if c in (0, NCOL - 1) else 420)
        if LAYOUT == 'p4':
            xa = colx(c) + (330 if c in (0, NCOL - 1) else 500)
        uy = U['y'] if t == 'S' else U['y'] + U['h']
        sy = S['y'] + S['h'] if t == 'S' else S['y']
        bits = 2 * COLL_LANE if u.startswith('coll') else XB
        P.link(f'u_{u}', 'coll' if u.startswith('coll') else 'unit', bits, (u, 'o', (xa, uy)), (sn, 'i', (xa, sy)), [(xa, uy), (xa, sy)], 'unit -> slice ring stop')
        P.link(f'v_{u}', 'coll' if u.startswith('coll') else 'unit', bits, (sn, 'o', (xa + 60, sy)), (u, 'i', (xa + 60, uy)), [(xa + 60, sy), (xa + 60, uy)], 'slice ring stop -> unit')
    # G-unit: commands, expert ids, HC coefficients to s_3S / s_3N, then along the streets through the ring stops
    gname = 'gunit' if 'gunit' in P.idx else 'gunit_r'
    G = P.blocks[P.idx[gname]]
    for c in range(NCOL):
        for t in 'SN':
            sn = f's_{c}{t}'
            S = P.blocks[P.idx[sn]]
            gx = colx(3) + (470 if LAYOUT != 'p3' else 250) + 10 * c
            g = (gx, G['y'] if t == 'S' else G['y'] + G['h'])
            st_y = S['y'] + SLICE_H / 2 + (150 if t == 'S' else -150)
            p = (S['x'] + S['w'] / 2, st_y)
            P.link(f'ctl_{sn}', 'ctl', CTL, (gname, 'ctl', g), (sn, 'ctl', p), [g, (gx, st_y), p], 'ctl tree (column + street, via ring stops)')
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
        qx, px = {'p3': (colx(c) + 400, colx(c) + 470), 'p4': (colx(c) + 460, colx(c) + 530)}.get(LAYOUT, (colx(c) + 620, colx(c) + 690))
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


def draw(P, facts, out, tag=None):
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
    ax.set_title(f"S81-DV {tag or LAYOUT}: 16 slices x 8 frames, slice ring (hop <= {HOP_UM:.0f} um), {facts['die_um'][0]/1000:.2f} x {facts['die_um'][1]/1000:.2f} mm. "
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
    ap.add_argument('--layout', default='p1', choices=('p1', 'p3', 'p4'))
    ap.add_argument('--row0-mx', action='store_true', help='p1b: row-0 frames MX (tap toward the slice)')
    ap.add_argument('--tier-w', type=int, default=0, help='p4c: per-column tier exchange width (bits per direction)')
    ap.add_argument('--lanes', type=int, default=1, help='p4c-lanes: split every 1,104-b link into N cycle-aligned lanes')
    ap.add_argument('--frame-w', type=float, default=None, help='p4: frame width override (S-ELEM bf_col 604.8 -> 1,436.832)')
    a = ap.parse_args()
    HOP_UM = a.hop_um
    global ROW0_MX, TIER_W, LANES
    ROW0_MX = a.row0_mx
    TIER_W = a.tier_w
    LANES = a.lanes
    global LAYOUT, SCOL_W, SLICE_W, SLICE_H, PITCH, DIE_W, SVC_W, FRAME_W, FRAME_PITCH, UNIT_W, UNIT_WE
    if a.layout == 'p4':
        # coordinator decision 10-17: bf_col 583.2 um widens the frames to 1,393.632 um; 1.00-mm slice columns; the
        # slice is a CLUSTER of 5 near-square hardened leaves (0.95 x 0.92 mm, one 64-lane beat each, own regional root)
        LAYOUT, FRAME_W, SCOL_W, SLICE_W, SLICE_H = 'p4', a.frame_w or 1393.632, 1000.0, 950.0, 4600.0
        FRAME_PITCH = FRAME_W + 8.7
        UNIT_W, UNIT_WE = 820.0, 545.0
        PITCH = 2 * FRAME_PITCH + SCOL_W
        DIE_W = 2 * EDGE + NCOL * PITCH
    if a.layout == 'p3':
        LAYOUT, SCOL_W, SLICE_W, SLICE_H, SVC_W = 'p3', 950.0, 900.0, 4900.0, 4000.0
        PITCH = 2 * FRAME_PITCH + SCOL_W
        DIE_W = 2 * EDGE + NCOL * PITCH
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
    if LAYOUT == 'p4':
        facts.update(slice_leaves=5, leaf_um=[SLICE_W, SLICE_H / 5])
    facts.update(worst_cut=m['worst_cut'], over_reach_bits=m['over_reach_bits'], relays=m['relays'],
                 relay_bit_stages=m['relay_bit_stages'], bit_mm=round(m['sum_bit_um_hops'] / 1000),
                 cut_windows_over_limit=m['cut_windows_over_limit'],
                 slice_area_mm2=SLICE_W * SLICE_H / 1e6, n_frames=sum(b['kind'] == 'frame' for b in P.blocks))
    (out / 'plan.json').write_text(json.dumps(dict(facts=facts, blocks=P.blocks, links=P.links), indent=0))
    (out / 'dv_links_record.json').write_text(json.dumps(record(P, facts, a)))
    draw(P, facts, out / 'dv_flow.png', a.revision.replace('dv-', ''))
    print(json.dumps(facts, indent=1))


if __name__ == '__main__':
    main()
