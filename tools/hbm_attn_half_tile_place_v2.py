#!/usr/bin/env python3
"""hbm-phys-1010 [att] (2026-10-10): ACCESS-AWARE floorplans of the two half attention tiles (hfd_attn_half_lo / _hi,
rtl/hdc/v41x/ot_hdc_v41x_attn_die_half_b.sv), PS variant (lo carries the svc PS entry port ks / ldk), replacing the
v1 placer's bank arrangement (tools/hbm_attn_half_tile_place.py, outlines / seam / face pins unchanged).

Why (measured): every half route (021f55db2 x6, half_ps 4922f86b0 / 11c7e95b3) sat 11-36 h in global routing; the hi
half's congestion report (11c7e95b3 hm10) put 55 % of the overflow in the SE merge corner.  Three floorplan defects:
  1. the parallel chunks of a wide stage were STACKED vertically 14 um apart (2.1 um gaps): an SN bank's d / q pins are
     on its S / N faces, so the middle chunks' 544 pins could only be reached through a 2-um slot (~125 tracks);
  2. orientation ignored the flow: SN banks on a DOWNWARD hop (hi res11 / xr1 corner chains, lo mid / rf) had q on the
     top face and the next d on the bottom face of a lower bank, i.e. every wire wrapped around a bank;
  3. 136-bit result pipes in 544-bit banks (fixed in RTL: ot_attn_bank_{sn,ew}136) and off-grid side EW banks.
Rules here (every bank, both halves):
  A. access zones: no macro within ACC um of an SN bank's S / N faces or an EW bank's W / E faces (the zone carries
     the bank's own bus turning into its pins); side-by-side neighbours along the pin face stay 1.5 um apart.
  B. a stage's SN chunks sit SIDE BY SIDE when the flow is vertical (straight columns), stacked with access zones when
     it is horizontal; EW chunks stack vertically.
  C. orientation follows the flow: SN R0 when the sink is above the bank, MX when below; EW R0 when the sink is east,
     MY when west (d faces the source).
  D. the quad rows' input banks are EW (q facing the quad's input edge, straight M4), every result bank 136 bits.

    python3 tools/hbm_attn_half_tile_place_v2.py [--out physical/hbm_attn_tile_r/half_v2] [--acc 20]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hbm_attn_die_tile_place as T
import hbm_attn_half_tile_place as V1

TW = V1.TW
H_LO = V1.H_LO
H_HI = round(V1.H_HI + 2.16 * 7, 3)          # the half_ps hi outline (7 rows wider strip, coordinator 2026-10-09)
QY_LO, QY_HI = V1.QY_LO, round(V1.QY_HI + 2.16 * 7, 3)
QSHIFT = V1.QSHIFT
CH = V1.CH
DIM = {('sn', 544): (105.84, 11.88), ('ew', 544): (11.88, 105.84), ('sn', 136): (28.08, 11.88), ('ew', 136): (11.88, 28.08)}
PARAMS = V1.PARAMS
grid = V1.grid
trk = T.trk


def ov(a, b, gap=0.0):
    return not (a[2] + gap <= b[0] or b[2] + gap <= a[0] or a[3] + gap <= b[1] or b[3] + gap <= a[1])


class APlan:
    """macro plan with pin-face access zones (rule A)"""

    def __init__(self, w, h, acc, quads):
        self.cw, self.ch = int(w / 0.054) * 0.054, int(h / 0.27) * 0.27
        self.acc = acc
        self.items = []                    # (real box, zone box)
        self.banks = []                    # (name, orient, x, y, w, h)
        for (x0, y0) in quads:
            b = (x0 - T.HALO, y0 - T.HALO, x0 + T.QW + T.HALO, y0 + T.QH + T.HALO)
            self.items.append((b, b))

    def zone(self, kind, b):
        a = self.acc
        return (b[0], b[1] - a, b[2], b[3] + a) if kind == 'sn' else (b[0] - a, b[1], b[2] + a, b[3])

    def free(self, kind, b, zones=True):
        if b[0] < -1e-6 or b[1] < -1e-6 or b[2] > self.cw + 1e-6 or b[3] > self.ch + 1e-6:
            return False
        z = self.zone(kind, b)
        for r, zz in self.items:
            if ov(b, r, 1.5) or (zones and (ov(b, zz, 0.0) or ov(z, r, 0.0))):
                return False
        return True

    def put(self, name, kind, bits, orient, x, y, force=False, pin=False):
        """pin: a face pin bank (its outer face is the die edge): only the real box is checked"""
        w, h = DIM[(kind, bits)]
        b = (x, y, x + w, y + h)
        if not force and not self.free(kind, b, zones=not pin):
            raise SystemExit(f'{name}: ({x:.3f}, {y:.3f}) {w} x {h} not free')
        self.items.append((b, self.zone(kind, b)))
        self.banks.append((name, orient, round(x, 3), round(y, 3), w, h))
        return (x + w / 2, y + h / 2)

    def snap(self, name, kind, bits, orient, cx, cy):
        """the free slot nearest the ideal centre (cx, cy), on the pin track grid (SN x = 0 mod 0.048, EW y = 0)"""
        w, h = DIM[(kind, bits)]
        best = None
        for r in range(0, 500):
            for dx in range(-r, r + 1):
                for dy in ((-r, r) if abs(dx) != r else range(-r, r + 1)):
                    x = trk(cx - w / 2 + dx * 2.16)
                    y = trk(cy - h / 2 + dy * 2.16, 0.0 if kind == 'ew' else 0.024)
                    if kind == 'ew':
                        y = grid(y)
                    if self.free(kind, (x, y, x + w, y + h)):
                        d = abs(x + w / 2 - cx) + abs(y + h / 2 - cy)
                        if best is None or d < best[0]:
                            best = (d, x, y)
            if best is not None and r > 3:
                break
        if best is None:
            raise SystemExit(f'{name}: no free slot near ({cx:.1f}, {cy:.1f})')
        return self.put(name, kind, bits, orient, best[1], best[2])


def orient(kind, src, sink):
    """rule C: d faces the source, q the sink"""
    if kind == 'sn':
        return 'R0' if sink[1] >= src[1] else 'MX'
    return 'R0' if sink[0] >= src[0] else 'MY'


def cen(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def make_pipe(P, hops):
    def pipe(name, src_pts, n_mid, nb, first, path, sink, tag, bits=544, ew_mask=0):
        """n_mid stages of nb chunks along src -> path -> sink (rule B / C); ew_mask bit k: stage k EW"""
        src = cen(src_pts)
        pts = [src] + path + [sink]
        prev = src
        out = []
        tgt = [T.along(pts, (k + 1) / (n_mid + 1)) for k in range(n_mid)] + [sink]
        for k in range(n_mid):
            cx, cy = tgt[k]
            nxt = tgt[k + 1]
            kind = 'ew' if (ew_mask >> k) & 1 else 'sn'
            o = orient(kind, prev, nxt)
            vertical = abs(nxt[1] - prev[1]) >= abs(nxt[0] - prev[0])
            w, h = DIM[(kind, bits)]
            cs = []
            for c in range(nb):
                off = c - (nb - 1) / 2
                if kind == 'sn' and vertical:
                    px, py = cx + off * (w + 1.68), cy
                elif kind == 'sn':
                    px, py = cx, cy + off * (h + P.acc + 2.0)
                else:
                    px, py = cx, cy + off * (h + 1.68)
                cs.append(P.snap(T.bname(name, first + k, c, kind == 'ew'), kind, bits, o, px, py))
            cc = cen(cs)
            hops.append((f'{tag} {k}', round(abs(cc[0] - prev[0]) + abs(cc[1] - prev[1]), 1)))
            prev = cc
            out.append(cs)
        hops.append((f'{tag} ->', round(abs(sink[0] - prev[0]) + abs(sink[1] - prev[1]), 1)))
        return out
    return pipe


def rows(P, name_fmt, QL_X, QR_X, q_in_y):
    """rule D: each quad's ROW stage = 3 EW chunks stacked on the quad's input edge (q -> the quad's M4 input pins)"""
    w, h = DIM[('ew', 544)]
    out = []
    for x in (0, 1):
        qx = QL_X + T.QW + T.HALO + P.acc + 1.6 if x == 0 else QR_X - T.HALO - P.acc - 1.6 - w
        o = 'MY' if x == 0 else 'R0'                      # quad0 (MY) inputs on its E edge: q on the W face
        cs = [P.put(T.bname(name_fmt.format(x=x), 0, c, True), 'ew', 544, o, trk(qx), grid(q_in_y + (c - 1) * (h + 1.68) - h / 2))
              for c in range(3)]
        out.append(cen(cs))
    return out


def row_hops(hops, rcs, mc, tag):
    for x, cc in enumerate(rcs):
        hops.append((f'{tag}{x}', round(abs(cc[0] - mc[0]) + abs(cc[1] - mc[1]), 1)))


def side_res(P, hops, nm, x, QL_X, QR_X, sy, up, tag):
    """the two side-channel result stages (EWM 3): e0 beside the quad's output edge (d facing it), e1 one bank-height
    toward the flow with the opposite orientation (its d faces e0's q on the outer side)"""
    w, h = DIM[('ew', 136)]
    if x == 0:
        xs, o0, o1, qe = QL_X - T.HALO - P.acc - 1.6 - w, 'MY', 'R0', QL_X
    else:
        xs, o0, o1, qe = QR_X + T.QW + T.HALO + P.acc + 1.6, 'R0', 'MY', QR_X + T.QW
    xs = trk(xs)
    e0 = P.put(T.bname(nm, 0, 0, True), 'ew', 136, o0, xs, grid(sy - h / 2))
    y1 = sy + (h + 6.0) * (1 if up else -1)
    e1 = P.put(T.bname(nm, 1, 0, True), 'ew', 136, o1, xs, grid(y1 - h / 2), force=False)
    hops.append((f'{tag} quad->bank', round(abs(qe - (xs + w / 2)), 1)))
    hops.append((f'{tag} 0->1', round(abs(e1[1] - e0[1]), 1)))
    return e1


def place_lo(a):
    QL_X, QR_X = round(43.230 + QSHIFT, 3), round(788.4 + (TW - 1349.112) - QSHIFT, 3)
    P, hops = APlan(TW, H_LO, a.acc, [(QL_X, QY_LO), (QR_X, QY_LO)]), []
    pipe = make_pipe(P, hops)
    pins = V1.Pins(TW, H_LO)
    cw, chh = P.cw, P.ch
    SNW, SNH = DIM[('sn', 544)]
    EWW, EWH = DIM[('ew', 544)]
    yN = trk(chh - SNH, 0.024, True)
    kx = V1.chunks(518.496, 2)
    cix = V1.chunks(733.536, 3)
    ksx = [1056.096, 1163.616]
    pin = {}
    pin['k'] = [P.put(T.bname('u_pk', 0, c, False), 'sn', 544, 'R0', x, 0.024, pin=True) for c, x in enumerate(kx)]
    pins.run('k', 'S', kx, 1041)
    pin['ci'] = [P.put(T.bname('u_pc', 0, c, False), 'sn', 544, 'R0', x, 0.024, pin=True) for c, x in enumerate(cix)]
    pins.run('ci', 'S', cix, 1618)
    pin['ks'] = [P.put(T.bname('u_pks', 0, c, False), 'sn', 544, 'R0', x, 0.024, pin=True) for c, x in enumerate(ksx)]
    qy = grid(2.0)
    ry = [grid(115.2 + c * CH) for c in range(3)]
    pin['ri'] = [P.put(T.bname('u_pr', 0, c, True), 'ew', 544, 'MY', trk(cw - EWW, 0.0, True), y, pin=True) for c, y in enumerate(ry)]
    pins.run('ri', 'E', ry, 1618)
    pin['rf'] = [P.put(T.bname('u_fr', a.NFR, c, True), 'ew', 544, 'MY', 0.0, y, pin=True) for c, y in enumerate(ry)]
    pins.run('rf', 'W', ry, 1618)
    pin['q'] = [P.put(T.bname('u_pq', 0, 0, True), 'ew', 544, 'MY', trk(cw - EWW, 0.0, True), qy, pin=True)]
    pins.run('q', 'E', [qy], 544)
    pins.p['q'] += [(b, 'M4', round(TW - 0.096, 3), round(qy + 0.396 + V1.PITCH * b, 3)) for b in range(544, 582)]
    pins.single('rst', 'E', round(qy + 0.396 + V1.PITCH * 582, 3))
    pins.single('ck', 'E', grid(600.0) + 0.012)
    root = [P.put(T.bname('u_root', 0, c, False), 'sn', 544, 'R0', x, yN, pin=True) for c, x in enumerate(cix)]
    pins.run('xp', 'N', cix, 1619)
    # the seam result pin banks sit in the side channels (136-bit banks): v1's E bank (x TW - 140) sat over quad1's top
    # edge, its d pins 4 um above the quad halo; die seam nets follow the half records (ports.json)
    xr_x = [grid(30.0), grid(TW - 60.0)]
    xr_pin = [P.put(T.bname(f'g_y0.g_x\\[{x}\\].u_res', a.NLL - 1, 0, False), 'sn', 136, 'R0', xr_x[x], yN, pin=True) for x in (0, 1)]
    pins.p['xr'] = []
    for x in (0, 1):
        pins.run('xr', 'N', [xr_x[x]], 136 * (x + 1), first_bit=136 * x)
    rc = cen(root)
    cc_x = (QL_X + T.QW + QR_X) / 2
    top = rc[1] - 60.0
    q_in_y = QY_LO + (203 + 360) / 2
    rcs = rows(P, 'g_y0.g_x\\[{x}\\].u_row', QL_X, QR_X, q_in_y)
    sy = QY_LO + 281.5
    e1s = [side_res(P, hops, f'g_y0.g_x\\[{x}\\].u_res', x, QL_X, QR_X, sy, True, f'res0{x}') for x in (0, 1)]
    # flows into ROOT (up the central channel): straight columns where the pins allow
    pipe('u_pc', pin['ci'], a.NC, 3, 1, [], rc, 'ci')
    pipe('u_pk', pin['k'], a.NK, 2, 1, [(cc_x - 200, 60.0), (cc_x - 200, top)], rc, 'k')
    pipe('u_pks', pin['ks'], a.NK, 2, 1, [(cc_x + 200, 60.0), (cc_x + 200, top)], rc, 'ks')
    # E-face q / ri: west along the bottom strip (stacked chunks with access zones), then up
    pipe('u_pq', pin['q'], a.NK, 1, 1, [(TW - 60.0, 60.0), (cc_x + 120, 60.0), (cc_x + 120, top)], rc, 'q')
    pipe('u_pr', pin['ri'], a.NR, 3, 1, [(TW - 200.0, 150.0), (cc_x + 60, 150.0), (cc_x + 60, top)], rc, 'ri')
    rfc = cen(pin['rf'])
    pipe('u_fr', root, a.NFR, 3, 0, [(cc_x - 60, top), (cc_x - 60, 150.0), (200.0, 150.0)], rfc, 'rf')
    mid = pipe('g_y0.u_mid', root, a.PMID, 3, 0, [(cc_x, q_in_y)], (cc_x, q_in_y - 60), 'mid0')
    row_hops(hops, rcs, cen(mid[-1]), 'row0')
    for x in (0, 1):
        nm = f'g_y0.g_x\\[{x}\\].u_res'
        e1 = e1s[x]
        pipe(nm, [e1], a.NLL - 3, 1, 2, [], (xr_x[x] + 14.04, yN), f'res0{x}', bits=136)
    quads = {'g_y0.g_x\\[0\\].u_q': (QL_X, QY_LO, 'MY'), 'g_y0.g_x\\[1\\].u_q': (QR_X, QY_LO, 'R0')}
    # PS entry port ks / ldk pins (as tools/hbm_forks_attn_half_ps.py)
    X0, PITCH = 1062.0, 0.192
    x1 = round(X0 + 1101 * PITCH, 3)
    pins.p['ks'] = [(i, 'M5', round(X0 + i * PITCH, 4), 0.096) for i in range(1102)]
    pins.p['ldk'] = [(0, 'M5', round(x1 + 2.016, 4), 0.096)]
    return P, hops, pins, quads, dict(cix=cix, xr_x=xr_x)


def place_hi(a, lo_geo):
    QL_X, QR_X = round(43.230 + QSHIFT, 3), round(788.4 + (TW - 1349.112) - QSHIFT, 3)
    P, hops = APlan(TW, H_HI, a.acc, [(QL_X, QY_HI), (QR_X, QY_HI)]), []
    pipe = make_pipe(P, hops)
    pins = V1.Pins(TW, H_HI)
    cw, chh = P.cw, P.ch
    SNW, SNH = DIM[('sn', 544)]
    EWW, EWH = DIM[('ew', 544)]
    yN = trk(chh - SNH, 0.024, True)
    cix, xr_x = lo_geo['cix'], lo_geo['xr_x']
    xin = [P.put(T.bname('u_xin', 0, c, False), 'sn', 544, 'R0', x, 0.024, pin=True) for c, x in enumerate(cix)]
    pins.run('xp', 'S', cix, 1619)
    xrin = [P.put(T.bname(f'g_y1.g_x\\[{x}\\].u_xr', 0, 0, False), 'sn', 136, 'R0', xr_x[x], 0.024, pin=True) for x in (0, 1)]
    pins.p['xr'] = []
    for x in (0, 1):
        pins.run('xr', 'S', [xr_x[x]], 136 * (x + 1), first_bit=136 * x)
    cf = [P.put(T.bname('u_fc', a.NFC - 1, c, False), 'sn', 544, 'R0', x, yN, pin=True) for c, x in enumerate(cix)]
    pins.run('cf', 'N', cix, 1618)
    yio = grid(2.0)
    pin_i = P.put(T.bname('u_pi', 0, 0, True), 'ew', 544, 'R0', 0.0, yio, pin=True)
    pins.run('i', 'W', [yio], 529)
    pin_o = P.put(T.bname('u_oo', 0, 0, True), 'ew', 544, 'R0', trk(cw - EWW, 0.0, True), yio, pin=True)
    pins.run('o', 'E', [yio], 529)
    pins.single('ck', 'E', grid(400.0) + 0.012)
    xc = cen(xin)
    cc_x = (QL_X + T.QW + QR_X) / 2
    cfc = cen(cf)
    q_in_y = QY_HI + (203 + 360) / 2
    rcs = rows(P, 'g_y1.g_x\\[{x}\\].u_row', QL_X, QR_X, q_in_y)
    sy = QY_HI + 281.5
    e1s = [side_res(P, hops, f'g_y1.g_x\\[{x}\\].u_res', x, QL_X, QR_X, sy, False, f'res1{x}') for x in (0, 1)]
    # cf: straight columns xin -> fc0 -> cf pins
    pipe('u_fc', xin, a.NFC - 1, 3, 0, [], cfc, 'cf')
    # xp -> mid -> the two EW row stacks: mid in the free band right above xin (its columns), fanning out sideways
    mid = pipe('g_y1.u_mid', xin, a.PMID - 1, 3, 0, [], (xc[0], 494.0), 'mid1')       # mid at y ~250: <= 400 um to both rows
    row_hops(hops, rcs, cen(mid[-1]) if mid else xc, 'row1')
    merge = (pin_o[0] - 60, pin_o[1])
    for x in (0, 1):
        nm = f'g_y1.g_x\\[{x}\\].u_res'
        e1 = e1s[x]
        if x == 0:
            path = [(e1[0], 60.0)]
        else:
            path = [(e1[0], 70.0)]
        pipe(nm, [e1], a.NL - 2, 1, 2, path, merge, f'res1{x}', bits=136)
        pipe(f'g_y1.g_x\\[{x}\\].u_xr', [xrin[x]], a.NL - a.NLL - 1, 1, 1, [(xrin[x][0], 40.0)], merge, f'xr{x}', bits=136)
    pipe('u_pi', [pin_i], a.NI, 1, 1, [(60.0, 50.0)], merge, 'chain')
    quads = {'g_y1.g_x\\[0\\].u_q': (QL_X, QY_HI, 'MY'), 'g_y1.g_x\\[1\\].u_q': (QR_X, QY_HI, 'R0')}
    return P, hops, pins, quads


def write(out, master, a, P, hops, pins, quads, half, dirs, head, H):
    os.makedirs(f'{out}/{master}', exist_ok=True)
    L = [f'# {master} floorplan v2 (tools/hbm_attn_half_tile_place_v2.py, access zones {a.acc} um): '
         + ' '.join(f'{k}={getattr(a, k)}' for k in PARAMS)]
    for n, (x0, y0, o) in quads.items():
        L.append(f'place_macro -macro_name {{{n}}} -location {{{x0:.3f} {y0:.3f}}} -orientation {o} -exact')
    for n, o, x, y, w, h in P.banks:
        L.append(f'place_macro -macro_name {{{n}}} -location {{{x:.3f} {y:.3f}}} -orientation {o} -exact')
    L += ['foreach ot_i [[ord::get_db_block] getInsts] {',
          '  if {[[$ot_i getMaster] isBlock]} { $ot_i setPlacementStatus FIRM }', '}',
          f'puts "OT_ATTN_HALF_PLACED {master} banks={len(P.banks)}"']
    open(f'{out}/{master}/macro_placement.tcl', 'w').write('\n'.join(L) + '\n')
    open(f'{out}/{master}/io_place.tcl', 'w').write(pins.tcl(head))
    rec = pins.record(master, half, dirs)
    rec['generator'] = 'tools/hbm_attn_half_tile_place_v2.py'
    open(f'{out}/{master}/ports.json', 'w').write(json.dumps(rec, indent=1) + '\n')
    bad = [h for h in hops if h[1] > a.max_hop]
    fp = dict(master=master, w_um=TW, h_um=H, params={k: getattr(a, k) for k in PARAMS}, banks=len(P.banks), acc_um=a.acc,
              orient={o: sum(1 for b in P.banks if b[1] == o) for o in ('R0', 'MX', 'MY')},
              hops=hops, max_hop_um=max(h[1] for h in hops), over=bad)
    open(f'{out}/{master}/floorplan.json', 'w').write(json.dumps(fp, indent=1) + '\n')
    return fp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='physical/hbm_attn_tile_r/half_v2')
    ap.add_argument('--max-hop', type=float, default=450.0)
    ap.add_argument('--acc', type=float, default=20.0)
    for k, v in PARAMS.items():
        ap.add_argument(f'--{k}', type=int, default=v)
    a = ap.parse_args()
    P, hops, pins, quads, geo = place_lo(a)
    V1.check_pins(P, pins)
    rl = write(a.out, 'hfd_attn_half_lo', a, P, hops, pins, quads, 'lo',
               dict(k='input', ci='input', ri='input', q='input', rst='input', ck='input', rf='output', xp='output', xr='output',
                    ks='input', ldk='input'),
               f'# hfd_attn_half_lo pins (v2): outline {TW} x {H_LO}; every pin on its pin bank', H_LO)
    Ph, hh, pinh, qh = place_hi(a, geo)
    V1.check_pins(Ph, pinh)
    rh = write(a.out, 'hfd_attn_half_hi', a, Ph, hh, pinh, qh, 'hi',
               dict(xp='input', xr='input', i='input', ck='input', cf='output', o='output'),
               f'# hfd_attn_half_hi pins (v2): outline {TW} x {H_HI}; every pin on its pin bank', H_HI)
    for p in ('xp', 'xr'):
        assert sorted((b, x) for b, _, x, _ in pins.p[p]) == sorted((b, x) for b, _, x, _ in pinh.p[p]), p
    print(json.dumps(dict(lo=dict(banks=rl['banks'], max_hop=rl['max_hop_um'], over=rl['over'], orient=rl['orient']),
                          hi=dict(banks=rh['banks'], max_hop=rh['max_hop_um'], over=rh['over'], orient=rh['orient']))))
    return 1 if rl['over'] or rh['over'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
