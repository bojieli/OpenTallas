#!/usr/bin/env python3
"""el1011-ds-coll 2026-10-11: the PARENT of the hardened cb tiles (dsfd_coll_cbh, physical spec in el1011-ds-coll.log).
Places the closed child macros (contract_cbh pin plans) in a row with >= 5.4-um gaps and 10.8 / 21.6-um outer channels,
snapped so every child pin lands on the parent's track grid, and puts each parent pin exactly opposite the child pin it
feeds (straight channel hops).  Writes
    physical/s81_ph_views/ports/contract_cbh/dsfd_coll_cbh/{ports.json, io_place.tcl, ports.svh}
    physical/redesign_ds/coll_split/place_macros_cbh.tcl
and prints the outline."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
C = ROOT / 'physical/s81_ph_views/ports/contract_cbh'
XQ, YQ = 0.432, 2.16                     # x: site 0.054 x M5 track 0.048; y: row 0.27 x M4 track 0.048
GAP, CW_, CH_ = 30.0, 40.0, 40.0          # >= 20-um channels, ~55% (FLOORPLAN_MARGIN 81.4% at 5.4 / 10.8 / 21.6)


def up(v, q):
    return round(math.ceil(v / q - 1e-9) * q, 4)


def child(m):
    return json.loads((C / m / 'ports.json').read_text())


def main():
    order = [('u_rw', 'dsfd_coll_cbr', 'R0'), ('u_f', 'dsfd_coll_cbf', 'R0'), ('u_q0', 'dsfd_coll_cbq0', 'R0')] + \
            [(f'g_q[{k}].u_q', 'dsfd_coll_cbq', 'R0') for k in range(1, 5)] + [('u_re', 'dsfd_coll_cbr', 'MY')]
    ch = {m: child(m) for _, m, _ in order}
    x = up(CW_, XQ)
    place = []
    for inst, m, o in order:
        place.append((inst, m, o, x))
        x = up(x + ch[m]['w_um'] + GAP, XQ)
    W = up(x - GAP + CW_, XQ)
    y0 = up(CH_, YQ)
    H = up(y0 + 340.2 + CH_, YQ)
    pins = []                                  # (name, layer, x0, y0, x1, y1)
    dirs = {}

    def put(name, layer, cx, cy, face):
        if face in 'NS':
            yb = 0.0 if face == 'S' else H - 0.192
            pins.append((name, layer, round(cx - 0.012, 4), round(yb, 4), round(cx + 0.012, 4), round(yb + 0.192, 4)))
        else:
            xb = 0.0 if face == 'W' else W - 0.192
            pins.append((name, layer, round(xb, 4), round(cy - 0.012, 4), round(xb + 0.192, 4), round(cy + 0.012, 4)))

    def bit(nm):
        return (nm.split('[')[0], int(nm.split('[')[1][:-1]) if '[' in nm else None)

    def pname(p, b):
        return p if b is None else f'{p}[{b}]'

    # child pin -> parent pin name (None = internal seam / per-child copy handled separately)
    def mapping(inst, m, p, b):
        if m == 'dsfd_coll_cbr':
            pre = {'u_rw': ('w', '0', 0), 'u_re': ('e', '4', 3)}[inst]
            if p.startswith('x_'):
                q = p[2:]
                return (pre[0] + q, b)
            if p.startswith('n_'):
                q = p[2:]
                if q == 'flt':
                    return ('flt_u', b + pre[2])
                return (q[:2] + pre[1] + q[2:], b)
            return None
        if m == 'dsfd_coll_cbf':
            return (p, b) if p in ('f_vm', 'fvm_u') else None
        k = 0 if m == 'dsfd_coll_cbq0' else int(inst.split('[')[1].split(']')[0])
        if p == 't_vm':
            return ('t_vm', 420 * k + b)
        if p == 'bw_d':
            return ('bw_d', b + 1) if k == 0 else ('bw_d', 420 * k + b)
        if p in ('bw_cr', 'bw_flt'):
            return (p, 0)
        if k == 0 and p in ('ts', 'bw_v'):
            return (p, 0)                      # one parent pin, opposite slice 0's; fans out to every slice
        return None

    used = set()
    for inst, m, o, x in place:
        w = ch[m]['w_um']
        for p, rec in ch[m]['ports'].items():
            for nm, ly, x0, yy0, x1, yy1 in rec['pins']:
                pp, b = bit(nm)
                mp = mapping(inst, m, pp, b)
                if mp is None:
                    continue
                cx, cy = (x0 + x1) / 2, (yy0 + yy1) / 2
                face = 'S' if yy0 == 0.0 and ly == 'M5' else 'N' if ly == 'M5' else ('W' if x0 == 0.0 else 'E')
                if o == 'MY':
                    cx = w - cx
                    face = {'W': 'E', 'E': 'W'}.get(face, face)
                px, py = x + cx, y0 + cy
                name = pname(*mp)
                assert name not in used, name
                used.add(name)
                put(name, ly, px, py, face)
    # wflt / eflt are 3-bit lane fault inputs: named x_flt in the child -> 'wflt' / 'eflt' above
    # parent-only pins: ts[1], ts[2] (unused), ck, rs on the S face in the cbf column's free stretch
    sx = round((place[1][3] + 62.0 - 0.012) / 0.048) * 0.048 + 0.012
    for nm in ('ts[1]', 'ts[2]', 'ck', 'rs'):
        put(nm, 'M5', sx, 0, 'S'); sx += 0.96
    # ports.json
    ports = {}
    for nm, ly, *r in pins:
        ports.setdefault(nm.split('[')[0], dict(layer=ly, pins=[]))['pins'].append([nm, ly] + list(r))
    io = {'f_vm': 'input', 'ts': 'input', 't_vm': 'output', 'wlo_v': 'output', 'wlo_r': 'input', 'wlo_d': 'output',
          'wli_v': 'input', 'wli_r': 'output', 'wli_d': 'input', 'wflt': 'input', 'elo_v': 'output', 'elo_r': 'input',
          'elo_d': 'output', 'eli_v': 'input', 'eli_r': 'output', 'eli_d': 'input', 'eflt': 'input', 'fvm_u': 'output',
          'flt_u': 'output', 'lo0_v': 'input', 'lo0_r': 'output', 'lo0_d': 'input', 'li0_v': 'output', 'li0_r': 'input',
          'li0_d': 'output', 'lo4_v': 'input', 'lo4_r': 'output', 'lo4_d': 'input', 'li4_v': 'output', 'li4_r': 'input',
          'li4_d': 'output', 'bw_v': 'input', 'bw_d': 'input', 'bw_cr': 'output', 'bw_flt': 'output', 'ck': 'input',
          'rs': 'input'}
    for b, p in ports.items():
        p['bits'] = len(p['pins']); p['direction'] = io[b]
    assert set(io) == set(ports), (set(io) ^ set(ports))
    d = C / 'dsfd_coll_cbh'
    d.mkdir(parents=True, exist_ok=True)
    rec = dict(master='dsfd_coll_cbh', die='contract_cbh', w_um=W, h_um=H, obs_top=9, domain='stream_1p2', instances=None,
               orients=['R0'], ports=ports,
               generator=dict(file='tools/s81_ph/s81_ph_coll_cbh_parent.py', note='cb parent of the hardened tiles'))
    (d / 'ports.json').write_text(json.dumps(rec, indent=0) + '\n')
    (d / 'io_place.tcl').write_text('\n'.join(
        [f'# dsfd_coll_cbh parent pin plan (tools/s81_ph/s81_ph_coll_cbh_parent.py)'] +
        [f'place_pin -pin_name {{{nm}}} -layer {ly} -location {{{(x0 + x1) / 2:.4f} {(y0 + y1) / 2:.4f}}} '
         f'-pin_size {{{x1 - x0:.4f} {y1 - y0:.4f}}}' for nm, ly, x0, y0, x1, y1 in pins]) + '\n')
    (d / 'ports.svh').write_text(',\n'.join(f'    {ports[p]["direction"]} wire [{ports[p]["bits"] - 1}:0] {p}'
                                            for p in sorted(ports)) + '\n')
    # generate-block children are named with escaped brackets after synthesis (g_q\\[1\\].u_q): match on the name with the
    # backslashes removed
    t = ['# el1011-ds-coll: child placement of the cb parent (tools/s81_ph/s81_ph_coll_cbh_parent.py)',
         'set ot_at [dict create]']
    for inst, m, o, x in place:
        t.append(f'dict set ot_at {{{inst}}} [list {x:.4f} {y0:.4f} {o}]')
    t += ['set ot_n 0',
          'foreach ot_i [[ord::get_db_block] getInsts] {',
          '  set ot_nm [$ot_i getName]; set ot_k [string map {"\\\\" ""} $ot_nm]',
          '  if {![dict exists $ot_at $ot_k]} continue',
          '  lassign [dict get $ot_at $ot_k] ot_x ot_y ot_o',
          '  place_macro -macro_name $ot_nm -location [list $ot_x $ot_y] -orientation $ot_o; incr ot_n',
          '}',
          f'if {{$ot_n != {len(place)}}} {{ error "place_macros_cbh: placed $ot_n children (expected {len(place)})" }}',
          'puts "place_macros_cbh: $ot_n children placed"']
    (ROOT / 'physical/redesign_ds/coll_split/place_macros_cbh.tcl').write_text('\n'.join(t) + '\n')
    print(f'dsfd_coll_cbh parent {W} x {H}; children at', [(i, x) for i, _, _, x in place], f'{len(pins)} pins')


if __name__ == '__main__':
    main()
