#!/usr/bin/env python3
"""Contract pin plan + tile placement of the gather slab dsfd_sp_gather with ROOT_BLK 2 (CLAUDE S81-PH, 2026-10-06).

128 ot_s81ph_root_tile chain tiles (contract pin plan physical/s81_ph_views/ports/contract/ot_s81ph_root_tile) in
4 columns x 32 rows, all R0; columns 0, 1 take the west trunk lanes (rW*: column 0 at li_w, column 1 at lt_wi),
columns 3, 2 the east ones (rE*: column 3 at li_e, column 2 at lt_ei).
Root (column c, row k) = 32 c + k (rtl/dsrom_sys/s81_ph/ot_s81ph_gather.sv ROOT_BLK 2).  Each lane's 69 pins sit at
the y of the tile pins it feeds (own lane at li, the lane passed through to the inner column at lti); the north face
carries t_capture with the capture's f_gather spec (same x: abutting views), f_vm/ckv/rsv and ck/rst.
Grid: macro x on the 0.432-um lcm of the M5 track (0.048) and site (0.054) grid, y on the 2.16-um lcm of the M4
track and row (0.27) grid, so every tile pin lands on a top-level track; x also on the 10.8-um M7 PG stripe pitch
of the view PDN contract (pdn_view.tcl), so the tiles' M7 stripes coincide with the slab's.

  python3 tools/s81_ph/s81_ph_gather_plan.py      -> ports/contract/dsfd_sp_gather/{ports.json, io_place.tcl,
                                                     ports.svh}, physical/s81_ph_views/gather/place_tiles.tcl
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P, OFF = 0.048, 0.012
W = 1015.176
NCOL, NROW = 4, 32
X0, XP = 21.6, 237.6            # column origin / pitch (multiples of 21.6 = lcm(0.432, 10.8))
Y0, YP = 10.8, 125.28           # row origin / pitch (multiples of 2.16)
TOP = 43.2                      # north strip: output registers, control crossing
H = round(Y0 + NROW * YP + TOP, 4)


def r4(v):
    return round(v, 4)


def main():
    tile = json.loads((ROOT / 'physical/s81_ph_views/ports/contract/ot_s81ph_root_tile/ports.json').read_text())
    TW, TH = tile['w_um'], tile['h_um']
    assert abs((X0 / 0.432) - round(X0 / 0.432)) < 1e-6 and abs((XP / 0.432) - round(XP / 0.432)) < 1e-6
    assert XP > TW and YP > TH and abs(X0 / 10.8 - round(X0 / 10.8)) < 1e-6 and abs(XP / 10.8 - round(XP / 10.8)) < 1e-6
    assert X0 + (NCOL - 1) * XP + TW < W
    ly = {n: [(q[3] + q[5]) / 2 for q in tile['ports'][n]['pins']] for n in ('li_w', 'lt_wi', 'li_e', 'lt_ei')}
    # lane table from the RTL: lv[R] <= rXt[B] (B = 69 j), status tst[..] <= rXt[B +: 2]
    src = (ROOT / 'rtl/dsrom_sys/s81_ph/dsfd_sp_gather.sv').read_text()
    lanes = {}
    for m in re.finditer(r'lv\[(\d+)\] <= (r[WE]\d)\[(\d+)\]', src):
        lanes[int(m.group(1))] = (m.group(2), int(m.group(3)))
    stat = [(m.group(1), int(m.group(2))) for m in re.finditer(r'tst\[\d+ \+: 2\] <= (r[WE]\d)\[(\d+) \+: 2\]', src)]
    assert len(lanes) == 128 and len(stat) == 12
    widths = {}
    for m in re.finditer(r'input wire \[(\d+):0\] (r[WE]\d),', src):
        widths[m.group(2)] = int(m.group(1)) + 1
    pins = {}

    def put(port, bit, face, y=None, x=None, layer='M4'):
        if face == 'W':
            rect = (0.0, y - 0.012, 0.192, y + 0.012)
        elif face == 'E':
            rect = (W - 0.192, y - 0.012, W, y + 0.012)
        elif face == 'N':
            rect = (x - 0.012, H - 0.192, x + 0.012, H)
        else:
            rect = (x - 0.012, 0.0, x + 0.012, 0.192)
        pins.setdefault(port, {})[bit] = [f'{port}[{bit}]', layer] + [r4(v) for v in rect]

    for r, (port, b0) in lanes.items():
        c, k = divmod(r, NROW)
        face = 'W' if c < 2 else 'E'
        key = {0: 'li_w', 1: 'lt_wi', 2: 'lt_ei', 3: 'li_e'}[c]
        for b in range(69):
            put(port, b0 + b, face, y=Y0 + k * YP + ly[key][b])
    used = {}
    for port, bit in [(p, b) for p in pins for b in pins[p]]:
        q = pins[port][bit]
        key = (q[2], round((q[3] + q[5]) / 2, 4))
        assert key not in used, (port, bit, used.get(key))
        used[key] = (port, bit)
    # trunk status pairs: bottom margin, W / E face, one track pitch 2
    for i, (port, b0) in enumerate(stat):
        face = 'W' if port[1] == 'W' else 'E'
        for b in range(2):
            y = OFF + (8 + 4 * i + 2 * b) * P
            assert y < Y0 - 0.5
            put(port, b0 + b, face, y=y)
    # north face (s81_ph_pinplan conventions)
    n_tr = int((W - 2 * OFF) / P)

    def north(name, bits, pt, fc, layer='M5'):
        need = (bits - 1) * pt + 1
        c = int(fc * n_tr)
        t0 = max(2, min(c - need // 2, n_tr - need - 2))
        for i in range(bits):
            put(name, i, 'N', x=OFF + (t0 + i * pt) * P, layer=layer)
        return t0, t0 + need
    spans = [north('t_capture', 6947, 2, 0.5), north('f_vm', 512, 1, 0.955), north('ckv', 1, 1, 0.99),
             north('rsv', 1, 1, 0.991), north('ck', 1, 1, 0.02), north('rst', 1, 1, 0.03)]
    spans.sort()
    for a, b in zip(spans, spans[1:]):
        assert a[1] <= b[0], (a, b)
    dirs = dict(t_capture='output')
    ports = {}
    for p, bits in pins.items():
        n = max(bits) + 1
        assert sorted(bits) == list(range(n)), (p, n, len(bits))
        if p in widths:
            assert n == widths[p], (p, n, widths[p])
        faces = sorted({('W' if q[2] == 0.0 else 'E' if q[4] == W else 'N' if q[5] == H else 'S') for q in bits.values()})
        ports[p] = dict(bits=n, layer=bits[0][1], pins=[bits[i] for i in range(n)], direction=dirs.get(p, 'input'),
                        face=''.join(faces))
    spec = dict(file='tools/s81_ph/s81_ph_gather_plan.py', tile=dict(w=TW, h=TH), grid=dict(x0=X0, xp=XP, y0=Y0, yp=YP),
                ncol=NCOL, nrow=NROW)
    rec = dict(master='dsfd_sp_gather', die='contract', w_um=W, h_um=H, obs_top=7, domain='stream_1p2+serial_0p9',
               instances=None, orients=['R0'], ports=ports, generator=spec)
    d = ROOT / 'physical/s81_ph_views/ports/contract/dsfd_sp_gather'
    d.mkdir(parents=True, exist_ok=True)
    (d / 'ports.json').write_text(json.dumps(rec, indent=0) + '\n')
    L = ['# dsfd_sp_gather ROOT_BLK 2 (contract pin plan, tools/s81_ph/s81_ph_gather_plan.py)']
    for p in sorted(ports):
        for nm, lyr, x0, y0, x1, y1 in ports[p]['pins']:
            L.append(f'place_pin -pin_name {{{nm}}} -layer {lyr} -location {{{(x0 + x1) / 2:.4f} {(y0 + y1) / 2:.4f}}} '
                     f'-pin_size {{{x1 - x0:.4f} {y1 - y0:.4f}}}')
    (d / 'io_place.tcl').write_text('\n'.join(L) + '\n')
    (d / 'ports.svh').write_text(',\n'.join(f"    {ports[p]['direction']} wire [{ports[p]['bits'] - 1}:0] {p}"
                                           for p in sorted(ports)) + '\n')
    # tile placement (MACRO_PLACEMENT_TCL): instance names end in g_c[c].g_k[k].u_t
    T = ['# CLAUDE S81-PH gather: 128 root chain tiles, abutted columns (tools/s81_ph/s81_ph_gather_plan.py)',
         'set ot_n 0',
         'foreach ot_i [[ord::get_db_block] getInsts] {',
         '  set ot_nm [$ot_i getName]',
         '  if {![regexp {g_c\\\\?\\[(\\d+)\\\\?\\]\\.g_k\\\\?\\[(\\d+)\\\\?\\]\\.u_t$} $ot_nm -> ot_c ot_k]} { continue }',
         f'  set ot_x [expr {{{X0} + $ot_c * {XP}}}]',
         f'  set ot_y [expr {{{Y0} + $ot_k * {YP}}}]',
         '  place_macro -macro_name $ot_nm -location [list $ot_x $ot_y] -orientation R0',
         '  incr ot_n',
         '}',
         f'if {{$ot_n != {NCOL * NROW}}} {{ error "place_tiles: placed $ot_n tiles, expected {NCOL * NROW}" }}',
         'puts "place_tiles: $ot_n tiles placed"']
    g = ROOT / 'physical/s81_ph_views/gather'
    g.mkdir(parents=True, exist_ok=True)
    (g / 'place_tiles.tcl').write_text('\n'.join(T) + '\n')
    print(d, H, {p: (v['bits'], v['face']) for p, v in sorted(ports.items())})


if __name__ == '__main__':
    main()
