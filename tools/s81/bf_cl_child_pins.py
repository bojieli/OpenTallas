#!/usr/bin/env python3
"""Explicit full-face pin plans for the BF column cluster children (S-ELEM 2026-10-17, coordinator tile review).

Each group sits on the face that looks at its real neighbour inside dsfd_bf_col_cl (583.2 x 198.72 parent), spread
evenly over the whole face in bit order, <= 6 pins/um, on the routing grid (M4 W/E faces, M5 N/S faces):
  fp  (126.36 x 108, top-right of the parent, N face at the die edge, E face at the 5 um ci strip):
      W  ze_d v0 tag xq0 xe0 wq0 we0         (lane-0 operands from the parent FXST relays, W channel next to red)
      S  v1 xq1 xe1 wq1 we1 rst_pin  q_v q_val q_err q_tag fault0 fault1   (lane-1 operands + results to seg below)
      N  fclk (centre, under the parent leaf_ck[0] pin)
  lane4_cl (82.08 x 95.04, stacked N-S in pairs: no N/S pins):
      W  t_p v_s ze_d w_s rst_pin fclk x_s   (operands from the parent lanes3 relays; clock / reset mid-face)
      E  cv cf cfault cs_p ct_p              (results towards red)
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / 'physical/ref_tile_specs/s81_bf_native_1015'


def bits(name, w):
    return [name] if w == 0 else [f'{name}[{i}]' for i in range(w)]


def snap(v, org, pitch):
    return round(org + round((v - org) / pitch) * pitch, 3)


def face(names, face_, lo, hi, W, H, used):
    n = len(names)
    out = []
    for k, nm in enumerate(names):
        t = lo + (hi - lo) * (k + 0.5) / n
        if face_ in 'WE':
            y = snap(t, 0.036, 0.048)
            while (face_, y) in used:
                y = round(y + 0.048, 3)
            used.add((face_, y))
            x = 0.0 if face_ == 'W' else W
            out.append(f'place_pin -pin_name {{{nm}}} -layer M4 -location {{{x:.3f} {y:.3f}}} -pin_size {{0.192 0.024}} -force_to_die_boundary')
        else:
            x = snap(t, 0.012, 0.048)
            while (face_, x) in used:
                x = round(x + 0.048, 3)
            used.add((face_, x))
            y = 0.0 if face_ == 'S' else round(H - 0.042, 3)
            out.append(f'place_pin -pin_name {{{nm}}} -layer M5 -location {{{x:.3f} {y:.3f}}} -pin_size {{0.024 0.192}} -force_to_die_boundary')
    dens = n / (hi - lo)
    assert dens <= 6.0, (face_, dens)
    return out, dens


def fp():
    W, H = 126.36, 108.0
    used = set()
    w = ['fclk', 'ze_d', 'v0'] + bits('tag', 17) + bits('xq0', 256) + bits('xe0', 10) + bits('wq0', 256) + bits('we0', 10)
    s = (['v1'] + bits('xq1', 256) + bits('xe1', 10) + bits('wq1', 256) + bits('we1', 10) + ['rst_pin'] +
         ['q_v'] + bits('q_val', 32) + ['q_err'] + bits('q_tag', 8) + ['fault0', 'fault1'])
    a, dw = face(w, 'W', 1.0, H - 1.0, W, H, used)
    b, ds = face(s, 'S', 1.0, W - 1.0, W, H, used)
    return a + b, {'W': (len(w), round(dw, 2)), 'S': (len(s), round(ds, 2))}


def lane4():
    W, H = 82.08, 95.04
    used = set()
    w = bits('t_p', 13) + ['v_s', 'ze_d'] + bits('w_s', 64) + ['rst_pin', 'fclk'] + bits('x_s', 64)
    e = bits('cv', 4) + bits('cf', 4) + bits('cfault', 4) + bits('cs_p', 128) + bits('ct_p', 32)
    a, dw = face(w, 'W', 1.0, H - 1.0, W, H, used)
    b, de = face(e, 'E', 1.0, H - 1.0, W, H, used)
    return a + b, {'W': (len(w), round(dw, 2)), 'E': (len(e), round(de, 2))}


def lane16():
    W, H = 164.16, 194.4
    used = set()
    w, e = [], []
    for g in range(4):  # group g owns the g-th quarter of both faces (its root captures / launches only these pins)
        w += [f'rst_pin{g}', f'ze_d{g}', f'v_s{g}'] + bits(f't_p{g}', 13) + bits(f'w_s{g}', 32) + [f'fclk{g}'] + \
             [f'w_s{g}[{i}]' for i in range(32, 64)] + bits(f'x_s{g}', 64)
        e += bits(f'cv{g}', 4) + bits(f'cf{g}', 4) + bits(f'cfault{g}', 4) + bits(f'cs_p{g}', 128) + bits(f'ct_p{g}', 32)
    a, dw = face(w, 'W', 1.0, H - 1.0, W, H, used)
    b, de = face(e, 'E', 1.0, H - 1.0, W, H, used)
    return a + b, {'W': (len(w), round(dw, 2)), 'E': (len(e), round(de, 2))}


def lane4b():
    """lane4 band (LANE S81-B 10-17, successor of lane16 r4c): ONE hardened ot_v41_bf_lane4_cl as a full-width quarter
    band of the 164.16 x 194.4 lane slot, replicated x4 abutted N-S in the parent (no N/S pins).  Same pin order as the
    lane16 per-group quarter plan: W operands with fclk / rst mid-face, E results towards red."""
    W, H = 164.16, 48.6
    used = set()
    w = ['rst_pin', 'ze_d', 'v_s'] + bits('t_p', 13) + bits('w_s', 32) + ['fclk'] + \
        [f'w_s[{i}]' for i in range(32, 64)] + bits('x_s', 64)
    e = bits('cv', 4) + bits('cf', 4) + bits('cfault', 4) + bits('cs_p', 128) + bits('ct_p', 32)
    a, dw = face(w, 'W', 1.0, H - 1.0, W, H, used)
    b, de = face(e, 'E', 1.0, H - 1.0, W, H, used)
    return a + b, {'W': (len(w), round(dw, 2)), 'E': (len(e), round(de, 2))}


def lane4r():
    """lane4r band (BFCOL-3 10-17, successor of lane4b): ot_v41_bf_lane4r_cl, same 164.16 x 48.6 band and pin order as
    lane4b plus regional roots: fclk_i (W pin root: every input pin's capture register) and fclk (lane root) mid W face,
    fclk_o (E pin root: every output pin's launch register) mid E face."""
    W, H = 164.16, 48.6
    used = set()
    w = ['rst_pin', 'ze_d', 'v_s'] + bits('t_p', 13) + bits('w_s', 55) + ['fclk_i', 'fclk'] + \
        [f'w_s[{i}]' for i in range(55, 64)] + bits('x_s', 64)   # clocks at the face centre
    e = bits('cv', 4) + bits('cf', 4) + bits('cfault', 4) + bits('cs_p', 74) + ['fclk_o'] + \
        [f'cs_p[{i}]' for i in range(74, 128)] + bits('ct_p', 32)
    a, dw = face(w, 'W', 1.0, H - 1.0, W, H, used)
    b, de = face(e, 'E', 1.0, H - 1.0, W, H, used)
    return a + b, {'W': (len(w), round(dw, 2)), 'E': (len(e), round(de, 2))}


def red():
    W, H = 81.0, 194.4
    used = set()
    w = ['fclk', 'rst_pin', 'ze_d', 'iv'] + bits('values_in', 512) + bits('errors_in', 16) + bits('tag_in', 8)
    e = ['ov'] + bits('oval', 32) + ['oerr'] + bits('tag_out', 8)
    a, dw = face(w, 'W', 1.0, H - 1.0, W, H, used)
    b, de = face(e, 'E', 1.0, H - 1.0, W, H, used)
    return a + b, {'W': (len(w), round(dw, 2)), 'E': (len(e), round(de, 2))}


def seg():
    W, H = 108.0, 64.8
    used = set()
    w = (['fclk', 'rst_pin', 'ze_d', 'in_v'] + bits('in_tree', 4) + bits('in_pos', 3) + bits('in_val', 32) + ['in_final', 'in_err'] +
         bits('rows', 128) + bits('indices', 40) + bits('counts', 40))
    e = ['pv'] + bits('pval', 32) + bits('prow', 16) + bits('pseg', 5) + bits('pnseg', 5) + bits('ppos', 3) + ['perr', 'fault']
    a, dw = face(w, 'W', 1.0, H - 1.0, W, H, used)
    b, de = face(e, 'E', 1.0, H - 1.0, W, H, used)
    return a + b, {'W': (len(w), round(dw, 2)), 'E': (len(e), round(de, 2))}


def main():
    for k, fn in (('cl_fp', fp), ('cl_lane4', lane4), ('cl_lane16', lane16), ('cl_lane4b', lane4b), ('cl_lane4r', lane4r), ('cl_red', red), ('cl_seg', seg)):
        lines, st = fn()
        p = D / k / 'pins.tcl'
        p.write_text(f'# GENERATED by tools/s81/bf_cl_child_pins.py: {st} (pins, pins/um)\n' + '\n'.join(lines) + '\n')
        print(k, st)


if __name__ == '__main__':
    main()
