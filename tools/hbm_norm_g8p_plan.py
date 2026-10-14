#!/usr/bin/env python3
"""conservative-1011 2026-10-11 (OWNER textbook audit, class 6): planned floorplan + pin plan of the split norm engine g8p.

gtile (ot_hbm_norm_gtile8, R0): outline and pin columns are READ FROM THE CLOSED VIEW (--lef; 365.04 x 365.04 at
hbm_norm_gtile8_ref-u52-0813c81c0, every pin on M5); without --lef the 10-11 planning outline 440 x 440 is used and
gtile_io.tcl is written for a new tile route.  OUTER face = S (in_x 1,024, wl_d 256, y_o 256: the die data next to the
tile), BAND face = N (control, partials, rstd, y_b copy for the act-quant, clk, rst_n).  Vertical-layer pins on the
asap7 tracks (M5 0.540 + 0.096k, M7 0.656 + 0.128k), spread evenly.
top (ot_hbm_norm_split_view_g8p): 2 rows x 4 tiles around a centre E-W band (180 um); row 0 R0 (outer face on the die
S edge), row 1 MX (outer face on the die N edge); planning form: tile x = 30.144 + 470.4 c (== 0 mod 0.192 keeps the
tile pins on track); closed-view form: x = 30.24 + 395.712 c, rows y 30.24 / 576.72 (x == 0 mod 0.864 = the 0.432 site
grid AND the 0.096 M5 pitch, y == 0 mod 2.16; MX moves no M5 pin column), parent 1,612.656 x 972.0, group g at column g // 2, row g % 2 (tree level-1 pairs are vertical neighbours; act-quant k reads columns
2k, 2k + 1).  Die pins: each tile's data slice on the die edge right next to its outer-face pin (same x), control on
the W edge within the band, results on the E edge within the band, the constant ro outputs on the E edge outside it.
"""
import argparse, json
from pathlib import Path

TW = TH = 440.0
X0, PITCH, EDGE, BAND = 30.144, 470.4, 30.24, 180.09
DW = round(X0 + 3 * PITCH + TW + X0, 3)
Y0 = EDGE
Y1 = round(EDGE + TH + BAND, 3)
DH = round(Y1 + TH + EDGE, 3)
GX, GY = 0.864, 2.16        # legal child origin lattice: lcm(0.432 site, 0.096 M5 pitch) / row pair


def use_view(lef):
    """Take the tile outline and its pin columns from a closed view LEF and re-derive the parent frame on the lattice."""
    global TW, TH, X0, PITCH, BAND, DW, Y0, Y1, DH
    W = H = None; pins = {}; cur = ly = None; use = 'SIGNAL'
    for ln in Path(lef).read_text().splitlines():
        t = ln.split()
        if not t: continue
        if t[0] == 'SIZE': W, H = float(t[1]), float(t[3])
        elif t[0] == 'PIN': cur, ly, use = t[1], None, 'SIGNAL'
        elif t[0] == 'USE' and cur: use = t[1]
        elif t[0] == 'LAYER' and cur: ly = t[1]
        elif t[0] == 'RECT' and cur and cur not in pins and use == 'SIGNAL':
            x0, y0, x1, y1 = map(float, t[1:5]); pins[cur] = (ly, round((x0 + x1) / 2, 4), round((y0 + y1) / 2, 4))
        elif t[0] == 'OBS' or (t[0] == 'END' and len(t) > 1 and t[1] == cur): cur = None
    want = set(bits(OUTER)) | set(bits(BANDP))
    assert set(pins) == want, sorted(set(pins) ^ want)[:8]
    for n in bits(OUTER): assert pins[n][2] < 1.0, (n, pins[n])            # outer face = S
    for n in bits(BANDP): assert pins[n][2] > H - 1.0, (n, pins[n])        # band face = N
    assert abs(H / GY - round(H / GY)) < 1e-6, H
    TW, TH = W, H
    X0 = EDGE
    PITCH = round(-(-(TW + 30.4) // GX) * GX, 3)
    BAND = round(-(-180.09 // GY) * GY, 3)
    DW = round(X0 + 3 * PITCH + TW + X0, 3)
    Y0 = EDGE
    Y1 = round(EDGE + TH + BAND, 3)
    DH = round(Y1 + TH + EDGE, 3)
    for v, g in ((X0, GX), (PITCH, GX), (Y0, GY), (Y1, GY), (DW, 0.432), (DH, GY)):
        assert abs(v / g - round(v / g)) < 1e-6, (v, g)
    return ([(n, pins[n][0], pins[n][1]) for n in bits(OUTER)], [(n, pins[n][0], pins[n][1]) for n in bits(BANDP)])
OUTER = [('in_x', 1024), ('wl_d', 256), ('y_o', 256)]
BANDP = [('clk', 1), ('rst_n', 1), ('go', 1), ('in_v', 1), ('pre', 128), ('wl_v', 1), ('wl_i', 8), ('rb_v', 1),
         ('rb_d', 32), ('s_v', 1), ('s_i', 8), ('s', 32), ('y_v', 1), ('y_i', 8), ('y_b', 256), ('gf', 1)]


def bits(lst):
    return [f'{n}[{b}]' if w > 1 else n for n, w in lst for b in range(w)]


def slots(w, lo=1.0):
    full = sorted([('M5', round(0.540 + 0.096 * k, 4)) for k in range(int((w - 0.540 - lo) / 0.096) + 1)] +
                  [('M7', round(0.656 + 0.128 * k, 4)) for k in range(int((w - 0.656 - lo) / 0.128) + 1)], key=lambda t: t[1])
    return full


def spread(names, w):
    f = slots(w)
    assert len(f) >= len(names), (len(f), len(names))
    return [(n,) + f[(i * len(f)) // len(names)] for i, n in enumerate(names)]


def vpin(n, ly, x, y):
    sz = '0.0240 0.1920' if ly == 'M5' else '0.0320 0.1920'
    return f'place_pin -pin_name {{{n}}} -layer {ly} -location {{{x:.4f} {y:.4f}}} -pin_size {{{sz}}}'


def hpins(names, y_lo, y_hi, x):
    tr = sorted([('M4', round(0.012 + 0.048 * k, 4)) for k in range(int(y_lo / 0.048) + 2, int(y_hi / 0.048) - 1, 2)] +
                [('M6', round(0.016 + 0.064 * k, 4)) for k in range(int(y_lo / 0.064) + 2, int(y_hi / 0.064) - 1, 2)], key=lambda t: t[1])
    tr = [t for t in tr if y_lo + 1 < t[1] < y_hi - 1]
    assert len(tr) >= len(names), (len(tr), len(names))
    out = []
    for i, n in enumerate(names):
        ly, y = tr[(i * len(tr)) // len(names)]
        sz = '0.1920 0.0240' if ly == 'M4' else '0.1920 0.0320'
        out.append(f'place_pin -pin_name {{{n}}} -layer {ly} -location {{{x:.4f} {y:.4f}}} -pin_size {{{sz}}}')
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True)
    ap.add_argument('--lef', help='closed ot_hbm_norm_gtile8 view LEF: outline + pin columns come from it')
    ap.add_argument('--view-job', default='', help='closed job the LEF comes from (recorded in the hand-off)')
    ap.add_argument('--origins', help='write the child-origin hand-off JSON for the die lead here')
    a = ap.parse_args()
    o = Path(a.out); o.mkdir(parents=True, exist_ok=True)
    if a.lef:
        so, sb = use_view(a.lef)
    else:
        so = spread(bits(OUTER), TW); sb = spread(bits(BANDP), TW)
        L = ['# tools/hbm_norm_g8p_plan.py: ot_hbm_norm_gtile8 pins (S = outer data face, N = band face)']
        L += [vpin(n, ly, x, 0.096) for n, ly, x in so] + [vpin(n, ly, x, TH - 0.096) for n, ly, x in sb]
        (o / 'gtile_io.tcl').write_text('\n'.join(L) + '\n')
    xo = {n: (ly, x) for n, ly, x in so}
    M, P = ['# tools/hbm_norm_g8p_plan.py: 8 x ot_hbm_norm_gtile8'], ['# tools/hbm_norm_g8p_plan.py: ot_hbm_norm_split_view_g8p die pins']
    for g in range(8):
        c, r = g // 2, g % 2
        x = round(X0 + PITCH * c, 3)
        M.append(f'place_macro -macro_name {{u.g_grp\\[{g}\\].u_g}} -location {{{x:.3f} {Y0 if r == 0 else Y1:.3f}}} -orientation {"R0" if r == 0 else "MX"} -exact')
        ye = 0.096 if r == 0 else round(DH - 0.096, 4)
        for b in range(1024):
            k, rem = divmod(b, 256); ly, px = xo[f'in_x[{b}]']; P.append(vpin(f'in_x[{(k * 64 + g * 8) * 32 + rem}]', ly, x + px, ye))
        for b in range(256):
            ly, px = xo[f'wl_d[{b}]']; P.append(vpin(f'wl_d[{g * 256 + b}]', ly, x + px, ye))
            ly, px = xo[f'y_o[{b}]']; P.append(vpin(f'y[{g * 256 + b}]', ly, x + px, ye))
    blo, bhi = Y0 + TH, Y1
    west = bits([('clk', 1), ('rst_n', 1), ('go', 1), ('in_v', 1), ('pre', 128), ('n_f', 32), ('eps', 32), ('wl_v', 1),
                 ('wl_i', 8), ('cos_t', 32), ('sin_t', 32)])
    east = bits([('y_v', 1), ('y_i', 8), ('r_v', 1), ('r', 32), ('q_v', 1), ('q_i', 8), ('q_codes', 512), ('q_e', 20),
                 ('q_y', 1024), ('fault', 1), ('ro_v', 1)])
    P += hpins(west, blo, bhi, 0.096) + hpins(east, blo, bhi, round(DW - 0.096, 4))
    ro = bits([('ro', 2048)])
    P += hpins(ro[:1024], 2.0, blo - 2.0, round(DW - 0.096, 4)) + hpins(ro[1024:], bhi + 2.0, DH - 2.0, round(DW - 0.096, 4))
    (o / 'top_macro.tcl').write_text('\n'.join(M) + '\n'); (o / 'top_io.tcl').write_text('\n'.join(P) + '\n')
    if a.origins:
        Path(a.origins).write_text(json.dumps(dict(
            schema='opentallas.child_origins.v1', parent_cell='ot_hbm_norm_split_view_g8p', parent_outline_um=[DW, DH],
            origin_lattice_um=[GX, GY], child_cell='ot_hbm_norm_gtile8', child_outline_um=[TW, TH],
            child_view=str(Path(a.lef).parent) if a.lef else None, view_job=a.view_job,
            band_um=[round(Y0 + TH, 3), Y1],
            children=[dict(name=f'u.g_grp[{g}].u_g', x=round(X0 + PITCH * (g // 2), 3), y=Y0 if g % 2 == 0 else Y1,
                           orient='R0' if g % 2 == 0 else 'MX', outer_face='S' if g % 2 == 0 else 'N') for g in range(8)],
            parent_pins='S / N edge: each tile data bit at the x of its tile pin (0 um of x run); W / E edge inside the band',
            parent_pin_tcl=str(o / 'top_io.tcl'),
            mx_note='row 1 is MX: the M5 pin columns do not move; the M6 PG stripe mirror was not audited (all-R0 fallback: one row of 8 at the same pitch, outer faces S)'), indent=1) + '\n')
    (o / 'plan.json').write_text(json.dumps(dict(gtile=[TW, TH], die=[DW, DH], rows_y=[Y0, Y1], band=[blo, bhi], x0=X0, pitch=PITCH,
                                                 group_at={g: [g // 2, g % 2] for g in range(8)}, gtile_pins=len(so) + len(sb),
                                                 die_pins=len(P) - 1), indent=1) + '\n')
    print(DW, DH, len(so) + len(sb), len(P) - 1)


if __name__ == '__main__':
    main()
