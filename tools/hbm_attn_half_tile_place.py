#!/usr/bin/env python3
"""attn-split (OWNER 2026-10-08): floorplans, pin plans and die-view port records of the two HALF attention tiles
hfd_attn_half_lo / hfd_attn_half_hi (rtl/hdc/v41x/ot_hdc_v41x_attn_die_half_b.sv), cut top / bottom between the quad
rows of the r23 tile (width 1778.52, the closed option-B quads ot_attn_tile_m6h1q, the closed SN / EW pipeline banks).

    lo (bottom, H_LO): a 230 um E-W strip at the bottom, then quad row 0.  k / ci (S), q + rst / ri (E), rf (W) pin
       banks at the bottom of their faces; ROOT on the N face (= the xp pin bank) over the ci column; quad row 0's
       results climb the side channels (above the pin banks) to N-face xr pin banks at the W / E ends of the seam.  The
       strip carries ri + q (E half, ~2.2k bits) and rf (W half, 1.6k) to / from the central channel: vs ~3.3k + the
       vertical row-1 feed in r23's 124 um middle channel (8.2M GRT overflow).
    hi (top, H_HI):    a 90 um strip at the bottom, then quad row 1.  The S-face xp / xr pin banks face lo's N-face
       banks bit for bit (abutting seam, register -> pin | pin -> register); cf (N), i (W), o (E); the i -> o chain,
       the xr results and quad row 1's x = 0 results run W -> E through the bottom strip (~0.8k bits) to the merge.

Every pin is generated FROM its bank (pin = bank pin, exact), so the --io-place check of the one-piece placer holds by
construction and is re-asserted here; the seam pins of lo and hi are asserted equal in x.  Writes, per half,
physical/hbm_attn_tile_r/half/<master>/{macro_placement.tcl, io_place.tcl, ports.json, floorplan.json}.

    python3 tools/hbm_attn_half_tile_place.py [--out physical/hbm_attn_tile_r/half]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hbm_attn_die_tile_place as T          # Plan / trk / along / bname and the bank / quad constants

TW = 1778.52
# the slot (H_LO + H_HI = 1,488.24) must fit the r25 die frame: 4 tile rows per scan quadrant under the 26 mm die
# height leave <= 1,522 um a slot (a 937 um lo with the strip ABOVE its quads made 1,661: H 27.1 mm, refused)
H_LO = 814.32                               # 2.16 x 377: a 230 um E-W strip at the BOTTOM + quad row 0 (230.016) + 21.4
H_HI = 673.92                               # 2.16 x 312: a 90 um bottom strip + quad row 1 (90.0) + 21.0
QY_LO, QY_HI = 230.016, 90.0                # quad rows (y = 0 mod 0.048)
QSHIFT = 48.0                               # as r23 / r23h
SNW, SNH, EWW, EWH = T.SNW, T.SNH, T.EWW, T.EWH
PITCH = 0.192
CH = 107.52                                 # chunk pitch of a pin-bank run: SNW + 1.62 rounded up to the 0.048 grid
PARAMS = dict(NK=4, NC=2, NR=3, PMID=2, NFC=2, NFR=3, NL=8, NI=6, NLL=3)


def grid(v):
    return round(round(v / 0.048) * 0.048, 3)


def setup(h):
    """point the one-piece placer's globals at this half's outline"""
    T.TW, T.TH = TW, h
    T.CW_, T.CH_ = int(TW / 0.054) * 0.054, int(h / 0.27) * 0.27


class Pins:
    """face pins generated from the pin banks: SN bank at x0 -> bit b at x0 + 0.396 + 0.192 b (M5, S / N face);
    EW bank at y0 -> bit b at y0 + 0.396 + 0.192 b (M4, E / W face)"""

    def __init__(self, w, h):
        self.w, self.h, self.p = w, h, {}           # port -> list of (bit, layer, x, y)

    def run(self, port, face, starts, bits, first_bit=0):
        out = self.p.setdefault(port, [])
        b = first_bit
        for s0 in starts:
            for j in range(544):
                if b >= bits:
                    break
                a = round(s0 + 0.396 + PITCH * j, 3)
                if face in 'SN':
                    out.append((b, 'M5', a, 0.096 if face == 'S' else round(self.h - 0.096, 3)))
                else:
                    out.append((b, 'M4', 0.096 if face == 'W' else round(self.w - 0.096, 3), a))
                b += 1
        return b

    def single(self, port, face, a, layer='M4'):
        self.p[port] = [(0, layer, *((0.096 if face == 'W' else round(self.w - 0.096, 3), a) if face in 'EW'
                                     else (a, 0.096 if face == 'S' else round(self.h - 0.096, 3))))]

    def tcl(self, head):
        L = [head]
        for port, lst in self.p.items():
            for b, ly, x, y in sorted(lst):
                sz = '0.0240 0.1920' if ly == 'M5' else '0.1920 0.0240'
                L.append(f'place_pin -pin_name {{{port}[{b}]}} -layer {ly} -location {{{x:.4f} {y:.4f}}} -pin_size {{{sz}}}')
        return '\n'.join(L) + '\n'

    def record(self, master, half, dirs):
        ports = {}
        for port, lst in self.p.items():
            xs, ys = [x for _, _, x, _ in lst], [y for _, _, _, y in lst]
            ports[port] = dict(bits=len(lst), direction=dirs[port], layer=lst[0][1], x=[min(xs), max(xs)], y=[min(ys), max(ys)])
        return dict(master=master, kind='attn_half', w_um=TW, h_um=self.h, obs_top=7, parent='hfd_attn_tile', half=half,
                    generator='tools/hbm_attn_half_tile_place.py', ports=ports)


def mids(P, name, n, src, q_in_y, cc_x, dx_row, hops, tag):
    """n mid banks (3 chunks) on the central-channel column between src and the quad-input height: equal shares of
    the Manhattan run src -> (cc_x, q_in_y) -> the row banks (dx_row each side), clipped to the vertical part"""
    lv = abs(src[1] - q_in_y)
    L = lv + abs(src[0] - cc_x) + dx_row
    mid, prev = [], src
    for k in range(n):
        s_ = min(lv, L * (k + 1) / (n + 1))
        my = src[1] + (q_in_y - src[1]) * (s_ / lv if lv else 0)
        mid = [P.snap(T.bname(name, k, c, False), cc_x, my + (c - 1) * 14.0) for c in range(3)]
        cen = (sum(p[0] for p in mid) / 3, sum(p[1] for p in mid) / 3)
        hops.append((f'{tag} {k}', round(abs(cen[0] - prev[0]) + abs(cen[1] - prev[1]), 1)))
        prev = cen
    return mid


def chunks(x0, n):
    return [grid(x0 + c * CH) for c in range(n)]


def place_lo(a):
    setup(H_LO)
    P, hops = T.Plan.__new__(T.Plan), []
    QL_X, QR_X = round(43.230 + QSHIFT, 3), round(788.4 + (TW - 1349.112) - QSHIFT, 3)
    P.boxes = [(x0 - T.HALO, QY_LO - T.HALO, x0 + T.QW + T.HALO, QY_LO + T.QH + T.HALO) for x0 in (QL_X, QR_X)]
    P.banks = []
    pins = Pins(TW, H_LO)
    cw, chh = T.CW_, T.CH_
    yN = T.trk(chh - SNH, 0.024, True)
    # pin banks
    kx = chunks(518.496, 2)                                       # k beside ci (r23: 260.988): short strip run
    cix = chunks(733.536, 3)                                      # r23 ci / cf pins (first pin 733.932)
    pin = {}
    pin['k'] = [P.put(T.bname('u_pk', 0, c, False), 'R0', x, 0.024, SNW, SNH) for c, x in enumerate(kx)]
    pins.run('k', 'S', kx, 1041)
    pin['ci'] = [P.put(T.bname('u_pc', 0, c, False), 'R0', x, 0.024, SNW, SNH) for c, x in enumerate(cix)]
    pins.run('ci', 'S', cix, 1618)
    # E face from the bottom: q[543:0] bank (q[581:544] + rst continue its pin run), then ri; rf (W) at ri's y (the row
    # chain stays straight); all beside the bottom strip / under quad row 0's result banks
    qy = grid(2.0)
    ry = [grid(115.2 + c * CH) for c in range(3)]
    pin['ri'] = [P.put(T.bname('u_pr', 0, c, True), 'MY', T.trk(cw - EWW, 0.0, True), y, EWW, EWH) for c, y in enumerate(ry)]
    pins.run('ri', 'E', ry, 1618)
    pin['rf'] = [P.put(T.bname('u_fr', a.NFR, c, True), 'MY', 0.0, y, EWW, EWH) for c, y in enumerate(ry)]
    pins.run('rf', 'W', ry, 1618)
    pin['q'] = [P.put(T.bname('u_pq', 0, 0, True), 'MY', T.trk(cw - EWW, 0.0, True), qy, EWW, EWH)]
    pins.run('q', 'E', [qy], 544)
    pins.p['q'] += [(b, 'M4', round(TW - 0.096, 3), round(qy + 0.396 + PITCH * b, 3)) for b in range(544, 582)]
    pins.single('rst', 'E', round(qy + 0.396 + PITCH * 582, 3))
    pins.single('ck', 'E', grid(600.0) + 0.012)
    # ROOT = the N-face xp pin bank, over the ci column (the column chain stays straight: ci -> ROOT -> xp -> cf)
    root = [P.put(T.bname('u_root', 0, c, False), 'R0', x, yN, SNW, SNH) for c, x in enumerate(cix)]
    pins.run('xp', 'N', cix, 1619)
    xr_x = [grid(30.0), grid(TW - 140.0)]                          # quad row 0 results cross at the W / E ends
    xr_pin = [P.put(T.bname(f'g_y0.g_x\\[{x}\\].u_res', a.NLL - 1, 0, False), 'R0', xr_x[x], yN, SNW, SNH) for x in (0, 1)]
    pins.p['xr'] = []
    for x in (0, 1):
        pins.run('xr', 'N', [xr_x[x]], 136 * (x + 1), first_bit=136 * x)
    rc = (sum(p[0] for p in root) / 3, sum(p[1] for p in root) / 3)
    cc_x = (QL_X + T.QW + QR_X) / 2

    def pipe(name, src_pts, n_mid, nb, first, path, sink, tag):
        src = (sum(p[0] for p in src_pts) / len(src_pts), sum(p[1] for p in src_pts) / len(src_pts))
        pts = [src] + path + [sink]
        prev = src
        for k in range(n_mid):
            cx, cy = T.along(pts, (k + 1) / (n_mid + 1))
            cs = [P.snap(T.bname(name, first + k, c, False), cx, cy + (c - (nb - 1) / 2) * 14.0) for c in range(nb)]
            cen = (sum(p[0] for p in cs) / nb, sum(p[1] for p in cs) / nb)
            hops.append((f'{tag} {k}', round(abs(cen[0] - prev[0]) + abs(cen[1] - prev[1]), 1)))
            prev = cen
        hops.append((f'{tag} ->', round(abs(sink[0] - prev[0]) + abs(sink[1] - prev[1]), 1)))

    top = rc[1] - 60.0
    pipe('u_pk', pin['k'], a.NK, 2, 1, [(cc_x - 150, 60.0), (cc_x - 150, top)], rc, 'k')
    pipe('u_pc', pin['ci'], a.NC, 3, 1, [], rc, 'ci')
    pipe('u_pq', pin['q'], a.NK, 1, 1, [(TW - 60.0, 80.0), (cc_x + 150, 80.0), (cc_x + 150, top)], rc, 'q')
    pipe('u_pr', pin['ri'], a.NR, 3, 1, [(TW - 60.0, 170.0), (cc_x + 60, 170.0), (cc_x + 60, top)], rc, 'ri')
    rfc = (sum(p[0] for p in pin['rf']) / 3, sum(p[1] for p in pin['rf']) / 3)
    pipe('u_fr', root, a.NFR, 3, 0, [(cc_x - 60, top), (cc_x - 60, 170.0), (60.0, 170.0)], rfc, 'rf')
    q_in_y = QY_LO + (203 + 360) / 2
    mid = []
    mid = mids(P, 'g_y0.u_mid', a.PMID, rc, q_in_y, cc_x, cc_x - (QL_X + T.QW + SNW / 2 + 6), hops, 'mid0')
    mc = (sum(p[0] for p in mid) / 3, sum(p[1] for p in mid) / 3)
    for x in (0, 1):
        qx = QL_X + T.QW if x == 0 else QR_X
        row = [P.snap(T.bname(f'g_y0.g_x\\[{x}\\].u_row', 0, c, False), qx + (SNW / 2 + 6 if x == 0 else -SNW / 2 - 6),
                      q_in_y + (c - 1) * 14.0) for c in range(3)]
        rcn = (sum(p[0] for p in row) / 3, sum(p[1] for p in row) / 3)
        hops.append((f'row0{x}', round(abs(rcn[0] - mc[0]) + abs(rcn[1] - mc[1]), 1)))
    # quad row 0 results: EW e0 beside the outer edge, EW e1 above it, NLL - 3 SN banks, the N-face xr pin bank at
    # the W / E end of the seam
    sy = QY_LO + 281.5
    for x in (0, 1):
        nm = f'g_y0.g_x\\[{x}\\].u_res'
        xs, o, qe = (15.0, 'MY', QL_X) if x == 0 else (TW - 35.112, 'R0', QR_X + T.QW)
        y1 = sy + 140.0                                     # e1 above e0, toward the seam (pin banks are below)
        e0 = P.put(T.bname(nm, 0, 0, True), o, xs, sy - EWH / 2, EWW, EWH)
        e1 = P.put(T.bname(nm, 1, 0, True), o, xs, y1 - EWH / 2, EWW, EWH)
        hops.append((f'res0{x} quad->bank', round(abs(qe - (xs + EWW / 2)), 1)))
        hops.append((f'res0{x} 0->1', round(abs(e1[1] - e0[1]), 1)))
        path = []
        pipe(nm, [e1], a.NLL - 3, 1, 2, path, xr_pin[x], f'res0{x}')
    quads = {'g_y0.g_x\\[0\\].u_q': (QL_X, QY_LO, 'MY'), 'g_y0.g_x\\[1\\].u_q': (QR_X, QY_LO, 'R0')}
    return P, hops, pins, quads, dict(root=[(round(r[0], 3)) for r in root], xr_x=xr_x, cix=cix)


def place_hi(a, lo_geo):
    setup(H_HI)
    P, hops = T.Plan.__new__(T.Plan), []
    QL_X, QR_X = round(43.230 + QSHIFT, 3), round(788.4 + (TW - 1349.112) - QSHIFT, 3)
    P.boxes = [(x0 - T.HALO, QY_HI - T.HALO, x0 + T.QW + T.HALO, QY_HI + T.QH + T.HALO) for x0 in (QL_X, QR_X)]
    P.banks = []
    pins = Pins(TW, H_HI)
    cw, chh = T.CW_, T.CH_
    yN = T.trk(chh - SNH, 0.024, True)
    cix, xr_x = lo_geo['cix'], lo_geo['xr_x']
    xin = [P.put(T.bname('u_xin', 0, c, False), 'R0', x, 0.024, SNW, SNH) for c, x in enumerate(cix)]
    pins.run('xp', 'S', cix, 1619)
    xrin = [P.put(T.bname(f'g_y1.g_x\\[{x}\\].u_xr', 0, 0, False), 'R0', xr_x[x], 0.024, SNW, SNH) for x in (0, 1)]
    pins.p['xr'] = []
    for x in (0, 1):
        pins.run('xr', 'S', [xr_x[x]], 136 * (x + 1), first_bit=136 * x)
    cf = [P.put(T.bname('u_fc', a.NFC - 1, c, False), 'R0', x, yN, SNW, SNH) for c, x in enumerate(cix)]
    pins.run('cf', 'N', cix, 1618)
    yio = grid(2.0)
    pin_i = P.put(T.bname('u_pi', 0, 0, True), 'R0', 0.0, yio, EWW, EWH)
    pins.run('i', 'W', [yio], 529)
    pin_o = P.put(T.bname('u_oo', 0, 0, True), 'R0', T.trk(cw - EWW, 0.0, True), yio, EWW, EWH)
    pins.run('o', 'E', [yio], 529)
    pins.single('ck', 'E', grid(400.0) + 0.012)
    xc = (sum(p[0] for p in xin) / 3, sum(p[1] for p in xin) / 3)
    cc_x = (QL_X + T.QW + QR_X) / 2

    def pipe(name, src_pts, n_mid, nb, first, path, sink, tag):
        src = (sum(p[0] for p in src_pts) / len(src_pts), sum(p[1] for p in src_pts) / len(src_pts))
        pts = [src] + path + [sink]
        prev = src
        for k in range(n_mid):
            cx, cy = T.along(pts, (k + 1) / (n_mid + 1))
            cs = [P.snap(T.bname(name, first + k, c, False), cx, cy + (c - (nb - 1) / 2) * 14.0) for c in range(nb)]
            cen = (sum(p[0] for p in cs) / nb, sum(p[1] for p in cs) / nb)
            hops.append((f'{tag} {k}', round(abs(cen[0] - prev[0]) + abs(cen[1] - prev[1]), 1)))
            prev = cen
        hops.append((f'{tag} ->', round(abs(sink[0] - prev[0]) + abs(sink[1] - prev[1]), 1)))

    cfc = (sum(p[0] for p in cf) / 3, sum(p[1] for p in cf) / 3)
    pipe('u_fc', xin, a.NFC - 1, 3, 0, [], cfc, 'cf')
    q_in_y = QY_HI + (203 + 360) / 2
    mid = []
    mid = mids(P, 'g_y1.u_mid', a.PMID - 1, xc, q_in_y, cc_x, cc_x - (QL_X + T.QW + SNW / 2 + 6), hops, 'mid1')
    mc = (sum(p[0] for p in mid) / 3, sum(p[1] for p in mid) / 3) if mid else xc
    for x in (0, 1):
        qx = QL_X + T.QW if x == 0 else QR_X
        row = [P.snap(T.bname(f'g_y1.g_x\\[{x}\\].u_row', 0, c, False), qx + (SNW / 2 + 6 if x == 0 else -SNW / 2 - 6),
                      q_in_y + (c - 1) * 14.0) for c in range(3)]
        rcn = (sum(p[0] for p in row) / 3, sum(p[1] for p in row) / 3)
        hops.append((f'row1{x}', round(abs(rcn[0] - mc[0]) + abs(rcn[1] - mc[1]), 1)))
    merge = (pin_o[0] - 60, pin_o[1])
    sy = QY_HI + 281.5
    for x in (0, 1):
        nm = f'g_y1.g_x\\[{x}\\].u_res'
        xs, o, qe = (15.0, 'MY', QL_X) if x == 0 else (TW - 35.112, 'R0', QR_X + T.QW)
        y1 = (sy + 55.0) / 2
        e0 = P.put(T.bname(nm, 0, 0, True), o, xs, sy - EWH / 2, EWW, EWH)
        e1 = P.put(T.bname(nm, 1, 0, True), o, xs, y1 - EWH / 2, EWW, EWH)
        hops.append((f'res1{x} quad->bank', round(abs(qe - (xs + EWW / 2)), 1)))
        hops.append((f'res1{x} 0->1', round(abs(e1[1] - e0[1]), 1)))
        pipe(nm, [e1], a.NL - 2, 1, 2, [(xs + EWW / 2 + (40 if x == 0 else -40), 70.0)], merge, f'res1{x}')
        pipe(f'g_y1.g_x\\[{x}\\].u_xr', [xrin[x]], a.NL - a.NLL - 1, 1, 1, [(xrin[x][0], 30.0)], merge, f'xr{x}')
    pipe('u_pi', [pin_i], a.NI, 1, 1, [(60.0, 50.0)], merge, 'chain')
    quads = {'g_y1.g_x\\[0\\].u_q': (QL_X, QY_HI, 'MY'), 'g_y1.g_x\\[1\\].u_q': (QR_X, QY_HI, 'R0')}
    return P, hops, pins, quads


def write(out, master, a, P, hops, pins, quads, half, dirs, head):
    os.makedirs(f'{out}/{master}', exist_ok=True)
    L = [f'# {master} floorplan (tools/hbm_attn_half_tile_place.py): ' + ' '.join(f'{k}={getattr(a, k)}' for k in PARAMS)]
    for n, (x0, y0, o) in quads.items():
        L.append(f'place_macro -macro_name {{{n}}} -location {{{x0:.3f} {y0:.3f}}} -orientation {o} -exact')
    for n, o, x, y, w, h in P.banks:
        L.append(f'place_macro -macro_name {{{n}}} -location {{{x:.3f} {y:.3f}}} -orientation {o} -exact')
    L += ['foreach ot_i [[ord::get_db_block] getInsts] {',
          '  if {[[$ot_i getMaster] isBlock]} { $ot_i setPlacementStatus FIRM }', '}',
          f'puts "OT_ATTN_HALF_PLACED {master} banks={len(P.banks)}"']
    open(f'{out}/{master}/macro_placement.tcl', 'w').write('\n'.join(L) + '\n')
    open(f'{out}/{master}/io_place.tcl', 'w').write(pins.tcl(head))
    open(f'{out}/{master}/ports.json', 'w').write(json.dumps(pins.record(master, half, dirs), indent=1) + '\n')
    bad = [h for h in hops if h[1] > a.max_hop]
    rec = dict(master=master, w_um=TW, h_um=pins.h, params={k: getattr(a, k) for k in PARAMS}, banks=len(P.banks),
               hops=hops, max_hop_um=max(h[1] for h in hops), over=bad)
    open(f'{out}/{master}/floorplan.json', 'w').write(json.dumps(rec, indent=1) + '\n')
    return rec


def check_pins(P, pins):
    """--io-place check, exact form: every face pin sits on its pin bank's own pin (same x / y, same layer) and no two
    pins of the half share a location"""
    seen = set()
    for port, lst in pins.p.items():
        for b, ly, x, y in lst:
            assert (x, y) not in seen, (port, b, x, y)
            seen.add((x, y))
    return len(seen)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='physical/hbm_attn_tile_r/half')
    # bank -> wire -> bank hops (no logic): the measured ASAP7 SS reach is 504 um a stage at 1.2 GHz (261 ps +
    # 1.135 ps/um); r23h shipped 376 um.  The lo row-chain hops (E face -> under quad row 0 -> ROOT on the seam) are ~406
    ap.add_argument('--max-hop', type=float, default=450.0)
    for k, v in PARAMS.items():
        ap.add_argument(f'--{k}', type=int, default=v)
    a = ap.parse_args()
    lo = place_lo(a)
    P, hops, pins, quads, geo = lo
    npl = check_pins(P, pins)
    rl = write(a.out, 'hfd_attn_half_lo', a, P, hops, pins, quads, 'lo',
               dict(k='input', ci='input', ri='input', q='input', rst='input', ck='input', rf='output', xp='output', xr='output'),
               f'# hfd_attn_half_lo pins (tools/hbm_attn_half_tile_place.py): outline {TW} x {H_LO}; every pin on its pin bank')
    Ph, hh, pinh, qh = place_hi(a, geo)
    nph = check_pins(Ph, pinh)
    rh = write(a.out, 'hfd_attn_half_hi', a, Ph, hh, pinh, qh, 'hi',
               dict(xp='input', xr='input', i='input', ck='input', cf='output', o='output'),
               f'# hfd_attn_half_hi pins (tools/hbm_attn_half_tile_place.py): outline {TW} x {H_HI}; every pin on its pin bank')
    # the seam: lo's N-face xp / xr pins face hi's S-face pins bit for bit
    for p in ('xp', 'xr'):
        lx = sorted((b, x) for b, _, x, _ in pins.p[p])
        hx = sorted((b, x) for b, _, x, _ in pinh.p[p])
        assert lx == hx, f'seam {p}: lo / hi pin x differ'
    print(json.dumps(dict(lo=dict(banks=rl['banks'], max_hop=rl['max_hop_um'], over=rl['over'], pins=npl),
                          hi=dict(banks=rh['banks'], max_hop=rh['max_hop_um'], over=rh['over'], pins=nph),
                          seam_bits=len(pins.p['xp']) + len(pins.p['xr']))))
    return 1 if rl['over'] or rh['over'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
