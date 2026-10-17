#!/usr/bin/env python3
"""Q-DIEPLAN3 (Q-COMPUTE-DIE helper, 2026-10-16): A0 ROM-leaf parent footprint DIAGNOSTIC of an owner-layout homes file.

usage: mk_dieplan_a0.py BASE_HOMES OUT_HOMES [--tile-h 1166.4] [--core-shift auto]

The chosen NK/NL structure (A0 ROM-leaf parent, Q-ROMPARENT / codex romleaf) grows the tile 457.92 x 950.4 ->
457.92 x 1166.4 (row channel 129.6 kept, die 32996.16 x 21215.52 = 700.03 mm2). This rewrites ONLY y positions of the
base homes (owner 5-column topology kept; masters, x, orientations unchanged):
  * tile rows: row k bottom moves by k * dH (dH = tile-h - 950.4); the head gap between rows 7/8 moves with row 7's top;
  * array stations (s_r_c) and DVM heads (h_*): by the row / gap their centre sits in (heads stay centred on the gap);
  * port stacks (sp_port_tiles_k, _f1, sp_band_lanes_k, sp_res_ser_k): by the row their port tile centre sits in
    (each port keeps feeding its own rows);
  * the centre core (VM, SU, seq_su, xs_tap, embed, native59, cbuf/crom, tt_ctlm, res_train_issue, up4 leaves/selectors,
    rstseq, clk_rx): one rigid shift (default: the head-gap shift), so every abutted seam and kit grant is unchanged;
  * bottom IO (io_*, package bumps): unchanged; top KV stack (d2d_rom, ucie_kv, KV bumps, rs/ck bumps): + 16 dH.
Pins of the tile proxy are y-kept (the A0 parent candidate keeps the g4t external data pins). DIAGNOSTIC ONLY: the
A0 parent clock set (27 entries) and its final pins are Q-ROMPARENT's; this measures die-level wire/relay/cut/GRT cost.
"""
import argparse, json, re

ap = argparse.ArgumentParser()
ap.add_argument('base'); ap.add_argument('out')
ap.add_argument('--tile-h', type=float, default=1166.4)
ap.add_argument('--core-shift', default='auto')
a = ap.parse_args()
B = json.load(open(a.base)); H = {k: dict(v) for k, v in B['homes'].items()}
P = B['params']; th0 = P['tile'][1]; dH = round(a.tile_h - th0, 3)
tiles = {n: h for n, h in H.items() if re.fullmatch(r't_\d+_\d+', n)}
rows = sorted(set(h['y'] for h in tiles.values()))
assert len(rows) == 16 and all(abs(h['h'] - th0) < 1e-3 for h in tiles.values())


def row_shift(yc):
    """shift for a point at old y: inside row k -> k dH; in the gap above row k -> (k + 1) dH"""
    s = 0.0
    for k, y0 in enumerate(rows):
        if yc >= y0 + th0 - 1e-6:
            s = (k + 1) * dH
        elif yc >= y0 - 1e-6:
            s = k * dH
    return s


gap_shift = 8 * dH                      # head gap (between rows 7 and 8) moves with row 7's top
core_shift = gap_shift if a.core_shift == 'auto' else float(a.core_shift)
CORE = re.compile(r'(sp_vector_memory|sp_su64_sfu|seq_su|xs_tap|embed_prov|native59|cbuf_g_\d+|crom_g_\d+|tt_ctlm|'
                  r'res_train_issue|tt_up4_leaf\d+|up4_sel_\w+|rstseq_rom|clk_rx|command_fork_\d+|selector_fork_\d+)$')
TOP = re.compile(r'(d2d_rom|ucie_kv|ckb_rom|rs_bump|bump_fwd_\w+)$')
BOTTOM = re.compile(r'(io_\w+|bump_pkg_\w+|bump_die_\w+)$')
STACK = re.compile(r'(sp_port_tiles|sp_band_lanes|sp_res_ser)_(\d)(_f1)?$')
port_shift = {}
for n, h in H.items():
    m = re.fullmatch(r'sp_port_tiles_(\d)', n)
    if m:
        port_shift[m.group(1)] = row_shift(h['y'] + h['h'] / 2)
moved = {}
for n, h in H.items():
    if n in tiles:
        s = rows.index(h['y']) * dH
    elif CORE.fullmatch(n):
        s = core_shift
    elif TOP.fullmatch(n):
        s = 16 * dH
    elif BOTTOM.fullmatch(n):
        s = 0.0
    elif STACK.fullmatch(n):
        s = port_shift[STACK.fullmatch(n).group(2)]
    elif re.fullmatch(r'(s_\d+_\d+|h_\d+)', n):
        s = row_shift(h['y'] + h['h'] / 2)
    else:
        raise SystemExit(f'unclassified home {n} ({h["m"]}): add it to a group')
    h['y'] = round(h['y'] + s, 3)
    moved[n] = s
top_tile = max(h['y'] + h['h'] for h in tiles.values()) + dH
die_h = round(B['die']['h'] + 16 * dH, 3)
for n in tiles:
    H[n]['h'] = a.tile_h
assert all(h['y'] + h['h'] <= die_h + 1e-3 for h in H.values()), 'a home leaves the die'
O = dict(B)
O['die'] = dict(B['die'], h=die_h)
O['candidate'] = (B.get('candidate') or 'base') + f'_a0t{a.tile_h:g}'
O['params'] = dict(P, tile=[P['tile'][0], a.tile_h], source='mk_dieplan_a0.py', base_a0=a.base, a0_dH=dH,
                   a0_core_shift=core_shift, a0_port_shift=port_shift,
                   sysface_xy=[P['sysface_xy'][0], round(P['sysface_xy'][1] + core_shift, 3)],
                   port_centres=[round(c + port_shift[str(i)], 3) for i, c in enumerate(P.get('port_centres', []))],
                   diagnostic='A0 ROM-leaf parent footprint, proxy pins y-kept; NOT the A0 clock set')
O['homes'] = H
json.dump(O, open(a.out, 'w'), indent=1)
print(f'die {B["die"]["w"]} x {die_h} = {B["die"]["w"] * die_h / 1e6:.3f} mm2; dH {dH}; core +{core_shift}; '
      f'ports {port_shift}; sysface_xy {O["params"]["sysface_xy"]}')
