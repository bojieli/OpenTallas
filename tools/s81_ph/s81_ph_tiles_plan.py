#!/usr/bin/env python3
"""Tile pin plans + slab compositions of the S81 SELECTOR, COLLECTOR and CAPTURE slabs (CLAUDE S81-PH redesign pass,
2026-10-06; RTL rtl/dsrom_sys/s81_ph/ot_s81ph_{sel,col,cap}_tile.sv).

Each placeholder slab becomes hardened tiles (<= ~1 mm a side) joined by registered pin-to-pin hops:
  selector   4 x dsfd_selt_q (648 x 159.84; two stacked on each side of the control tile, the E pair MY) abutting
             dsfd_selt_c (129.6 x 319.68); the die lanes reach the quarter tiles through LSTG die stations
  collector  4 x dsfd_colt_lane (216 x 129.6; at the W / E faces, the E pair MY) + dsfd_colt_mrg (216 x 151.2, centre,
             S face under vd) joined by HOPS die stations per lane each way
  capture    8 x dsfd_capt_grp (118.8 x 324) + dsfd_capt_ctl (86.4 x 324) in one row above a 21.6-um channel (the ctl ->
             tile constant buses and tile -> ctl status run in the channel; f_row crosses it vertically)
Pins follow the generator conventions (tools/s81_ph/s81_ph_pinplan.py: M4 horizontal / M5 vertical, offset 0.012,
pitch 0.048, 0.024 x 0.192 at the face).  MY-mirrored tiles carry pins only on their W / E faces (M4: y unchanged by
the mirror).  Outlines: x on the 10.8-um PDN/track/site lcm, y on the 2.16-um M4/row lcm (as the gather tiles).
The control tile's W / E pins of the selector sit at exactly the y of the quarter tiles' E pins (abutment).

  python3 tools/s81_ph/s81_ph_tiles_plan.py   -> physical/s81_ph_views/ports/contract/<tile>/{ports.json,io_place.tcl,
                                                 ports.svh}, physical/s81_ph_views/specs/<tile>.json,
                                                 results/rtl/s81_ph_20261006/<kind>/tiles.json
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P, OFF = 0.048, 0.012
SB, CB, OB = 865, 66, 354          # selector status / command / beat bundles (ot_s81ph_sel_tile.sv)
KB = 99                            # capture constant bus (ot_s81ph_cap_tile.sv)
MIRROR = ('tiles placed R0 and MY (dsfd_selt_q, dsfd_colt_lane) carry pins only on their W / E faces (M4: y unchanged '
          'by MY) and the symmetric M7 PG grid of physical/s81_ph_views/tiles/pdn_tile_sym.tcl (VDD 5.256 / VSS 10.656 '
          'mod 10.8 on a width multiple of 10.8): place every instance, R0 or MY, at x0 = 6.544 (mod 10.8) so its '
          'stripes land on the die VDD 1.0 / VSS 6.4 (mod 10.8) grid; y0 on the 2.16 grid')


def r4(v):
    return round(v, 4)


def pin_rect(face, pos, W, H):
    if face == 'S': return (pos - 0.012, 0.0, pos + 0.012, 0.192)
    if face == 'N': return (pos - 0.012, H - 0.192, pos + 0.012, H)
    if face == 'W': return (0.0, pos - 0.012, 0.192, pos + 0.012)
    return (W - 0.192, pos - 0.012, W, pos + 0.012)


def plan(spec):
    """generic placement (as s81_ph_pinplan.py): each port a contiguous group at pitch_tracks around frac_center"""
    W, H = spec['w_um'], spec['h_um']
    ports, used = {}, {}
    for name, bits, d, face, layer, pt, fc in spec['ports']:
        span = W if face in 'NS' else H
        n_tr = int((span - 2 * OFF) / P)
        need = (bits - 1) * pt + 1
        c = int(fc * n_tr)
        t0 = max(2, min(c - need // 2, n_tr - need - 2))
        assert t0 + need < n_tr, (spec['master'], name, 'does not fit')
        pins = []
        for i in range(bits):
            t = t0 + i * pt
            key = (face, layer, t)
            assert key not in used, (spec['master'], name, i, used.get(key))
            used[key] = name
            pins.append([f'{name}[{i}]', layer] + [r4(v) for v in pin_rect(face, OFF + t * P, W, H)])
        ports[name] = dict(bits=bits, layer=layer, pins=pins, direction=d, face=face)
    return ports


def write(master, W, H, domain, ports, spec):
    rec = dict(master=master, die='contract', w_um=W, h_um=H, obs_top=7, domain=domain, instances=None,
               orients=spec.get('orients', ['R0']), ports=ports,
               generator=dict(file='tools/s81_ph/s81_ph_tiles_plan.py', spec=spec))
    d = ROOT / 'physical/s81_ph_views/ports/contract' / master
    d.mkdir(parents=True, exist_ok=True)
    (d / 'ports.json').write_text(json.dumps(rec, indent=0) + '\n')
    L = [f'# {master} (contract pin plan, tools/s81_ph/s81_ph_tiles_plan.py)']
    for p in sorted(ports):
        for nm, ly, x0, y0, x1, y1 in ports[p]['pins']:
            L.append(f'place_pin -pin_name {{{nm}}} -layer {ly} -location {{{(x0 + x1) / 2:.4f} {(y0 + y1) / 2:.4f}}} '
                     f'-pin_size {{{x1 - x0:.4f} {y1 - y0:.4f}}}')
    (d / 'io_place.tcl').write_text('\n'.join(L) + '\n')
    (d / 'ports.svh').write_text(',\n'.join(f"    {ports[p]['direction']} wire [{ports[p]['bits'] - 1}:0] {p}"
                                           for p in sorted(ports)) + '\n')
    (ROOT / 'physical/s81_ph_views/specs' / f'{master}.json').write_text(json.dumps(spec, indent=1) + '\n')
    return rec


def ycen(pin):
    return r4((pin[3] + pin[5]) / 2)


def main():
    out = {}
    # ------------------------------------------------------------------ selector
    QW, QH = 756.0, 159.84
    q_spec = {'master': 'dsfd_selt_q', 'w_um': QW, 'h_um': QH, 'domain': 'stream_1p2', 'orients': ['R0', 'MY'],
              'note': 'selector quarter tile; W face = die lane (+ ck/rst), E face = control tile (abutted); the three '
                      'SRAM macros along the S edge, x 21.6 .. 561.6 (tiles/place_macros_tile.tcl), E end free for the pins',
              'ports': [['lane', 515, 'input', 'W', 'M4', 2, 0.5], ['ck', 1, 'input', 'W', 'M4', 1, 0.05],
                        ['rst', 1, 'input', 'W', 'M4', 1, 0.07],
                        ['t_s', SB, 'output', 'E', 'M4', 2, 0.30], ['t_o', OB, 'output', 'E', 'M4', 2, 0.72],
                        ['f_c', CB, 'input', 'E', 'M4', 2, 0.90], ['f_cr', 1, 'input', 'E', 'M4', 1, 0.95]]}
    qp = plan(q_spec)
    write('dsfd_selt_q', QW, QH, 'stream_1p2', qp, q_spec)
    CW_, CH = 129.6, 2 * QH
    # control tile: W face = tiles 0 (SW, lower) / 2 (NW, upper); E face = tiles 1 (SE, lower) / 3 (NE, upper)
    cports = {}
    for cname, qname, bits, d in (('f_s', 't_s', SB, 'input'), ('f_o', 't_o', OB, 'input'), ('t_c', 'f_c', CB, 'output'),
                                  ('t_cr', 'f_cr', 1, 'output')):
        pins = [None] * (4 * bits)
        for g in range(4):
            face = 'W' if g in (0, 2) else 'E'
            dy = QH if g >= 2 else 0.0
            for i, qpin in enumerate(qp[qname]['pins']):
                y = r4(ycen(qpin) + dy)
                pins[g * bits + i] = [f'{cname}[{g * bits + i}]', 'M4'] + [r4(v) for v in pin_rect(face, y, CW_, CH)]
        cports[cname] = dict(bits=4 * bits, layer='M4', pins=pins, direction=d, face='W+E')
    c_n = plan({'master': 'dsfd_selt_c', 'w_um': CW_, 'h_um': CH,
                'ports': [['vd', 514, 'output', 'N', 'M5', 2, 0.5], ['vf', 1, 'output', 'N', 'M5', 1, 0.93],
                          ['ck', 1, 'input', 'N', 'M5', 1, 0.05], ['rst', 1, 'input', 'N', 'M5', 1, 0.07]]})
    cports.update(c_n)
    c_spec = {'master': 'dsfd_selt_c', 'w_um': CW_, 'h_um': CH, 'domain': 'stream_1p2',
              'note': 'selector control tile; W/E pins mirror the quarter tiles E pins (tiles 0/1 lower, 2/3 upper)',
              'ports': 'derived (f_s/f_o/t_c/t_cr from dsfd_selt_q E pins; vd/vf/ck/rst on N)'}
    write('dsfd_selt_c', CW_, CH, 'stream_1p2', cports, c_spec)
    XC = 2851.2                      # control tile x (vd pins of the slab at x ~2922)
    sel = {'slab': 'dsfd_bk_selector', 'outline_um': [5270.376, 321.816],
           'tiles': [{'inst': 'u_c', 'master': 'dsfd_selt_c', 'x': XC, 'y': 0.0, 'orient': 'R0'},
                     {'inst': 'u_q0 (SW)', 'master': 'dsfd_selt_q', 'x': r4(XC - QW - 4.256), 'y': 0.0, 'orient': 'R0'},
                     {'inst': 'u_q2 (NW)', 'master': 'dsfd_selt_q', 'x': r4(XC - QW - 4.256), 'y': QH, 'orient': 'R0'},
                     {'inst': 'u_q1 (SE)', 'master': 'dsfd_selt_q', 'x': r4(XC + CW_ + 6.544), 'y': 0.0, 'orient': 'MY'},
                     {'inst': 'u_q3 (NE)', 'master': 'dsfd_selt_q', 'x': r4(XC + CW_ + 6.544), 'y': QH, 'orient': 'MY'}],
           'hops': [{'what': 'die lane iSW/iNW -> u_q0/u_q2 lane (515 b)', 'length_um': r4(XC - QW),
                     'stations': 5, 'kind': 'common-clock register station (ot_fwd_link_stage class), <= 430 um a span'},
                    {'what': 'die lane iSE/iNE -> u_q1/u_q3 lane (515 b)', 'length_um': r4(5270.376 - XC - CW_ - QW),
                     'stations': 4, 'kind': 'as above'},
                    {'what': 'quarter <-> control (t_s/t_o/f_c/f_cr)', 'length_um': 6.544, 'stations': 0,
                     'kind': 'near-abutted pin-to-pin, straight M4 (flop at both pins); gap 4.256 W / 6.544 E'},
                    {'what': 'control vd/vf -> VM station chain', 'kind': 'unchanged (dsfd_bk_selector vd/vf)'}],
           'abutment': 'u_q* E (R0) / W (MY) pins at the y of dsfd_selt_c W / E pins (identical by construction)',
           'mirror_rule': MIRROR,
           'clock': 'one ck net, each tile its own CTS tree; tile IO budgets 0.2 T + 150 ps against the measured insertion'}
    out['selector'] = sel
    # ------------------------------------------------------------------ collector
    LW, LH = 432.0, 129.6
    l_spec = {'master': 'dsfd_colt_lane', 'w_um': LW, 'h_um': LH, 'domain': 'stream_1p2', 'orients': ['R0', 'MY'],
              'note': 'collector lane tile; W face = die lane, E face = stream to the merger (die stations); the two '
                      'SRAM macros along the S edge (tiles/place_macros_tile.tcl), pins above them',
              'ports': [['c_in', 515, 'input', 'W', 'M4', 2, 0.66], ['ck', 1, 'input', 'W', 'M4', 1, 0.95],
                        ['rst', 1, 'input', 'W', 'M4', 1, 0.97],
                        ['t_w', 513, 'output', 'E', 'M4', 2, 0.66], ['t_f', 4, 'output', 'E', 'M4', 2, 0.93],
                        ['f_cr', 1, 'input', 'E', 'M4', 1, 0.97]]}
    write('dsfd_colt_lane', LW, LH, 'stream_1p2', plan(l_spec), l_spec)
    MW, MH = 216.0, 151.2
    m_spec = {'master': 'dsfd_colt_mrg', 'w_um': MW, 'h_um': MH, 'domain': 'stream_1p2',
              'note': 'collector merger tile; W face lanes 0 (SW) / 2 (NW), E face lanes 1 (SE) / 3 (NE): f_w/f_f/t_cr '
                      'are per-lane vectors split over the faces by the derived pin list; vd/vf/ck/rst on S',
              'ports': 'derived'}
    mports = {}
    for cname, bits, d, f0 in (('f_w', 513, 'input', 0.03), ('f_f', 4, 'input', 0.0), ('t_cr', 1, 'output', 0.0)):
        mports[cname] = dict(bits=4 * bits, layer='M4', pins=[None] * (4 * bits), direction=d, face='W+E')
    # per face: lane A (lower half), lane B (upper half): f_w 513 at pitch 2, then f_f 4, t_cr 1
    n_tr = int((MH - 2 * OFF) / P)
    for face, lanes in (('W', (0, 2)), ('E', (1, 3))):
        t = 4
        for g in lanes:
            for cname, bits in (('f_w', 513), ('f_f', 4), ('t_cr', 1)):
                for i in range(bits):
                    mports[cname]['pins'][g * bits + i] = [f'{cname}[{g * bits + i}]', 'M4'] + \
                        [r4(v) for v in pin_rect(face, OFF + t * P, MW, MH)]
                    t += 2
            t += 20
        assert t < n_tr - 2, ('dsfd_colt_mrg', face, t, n_tr)
    mports.update(plan({'master': 'dsfd_colt_mrg', 'w_um': MW, 'h_um': MH,
                        'ports': [['vd', 514, 'output', 'S', 'M5', 2, 0.5], ['vf', 1, 'output', 'S', 'M5', 1, 0.9],
                                  ['ck', 1, 'input', 'S', 'M5', 1, 0.04], ['rst', 1, 'input', 'S', 'M5', 1, 0.06]]}))
    write('dsfd_colt_mrg', MW, MH, 'stream_1p2', mports, m_spec)
    XM = 2808.0
    col = {'slab': 'dsfd_bk_collector', 'outline_um': [5270.376, 881.256],
           'tiles': [{'inst': 'u_m', 'master': 'dsfd_colt_mrg', 'x': XM, 'y': 0.0, 'orient': 'R0'},
                     {'inst': 'u_l0 (SW)', 'master': 'dsfd_colt_lane', 'x': 6.544, 'y': 187.92, 'orient': 'R0'},
                     {'inst': 'u_l2 (NW)', 'master': 'dsfd_colt_lane', 'x': 6.544, 'y': 540.0, 'orient': 'R0'},
                     {'inst': 'u_l1 (SE)', 'master': 'dsfd_colt_lane', 'x': 4834.144, 'y': 187.92, 'orient': 'MY'},
                     {'inst': 'u_l3 (NE)', 'master': 'dsfd_colt_lane', 'x': 4834.144, 'y': 540.0, 'orient': 'MY'}],
           'hops': [{'what': 'lane tile t_w/t_f (517 b) -> merger f_w/f_f, and merger t_cr -> lane f_cr (1 b)',
                     'length_um_max': r4((XM - LW) + 540.0 + LH - 75.0), 'stations': 7,
                     'kind': 'common-clock register station, <= 430 um a span, each direction; HOPS 7 in the composition'},
                    {'what': 'merger vd/vf -> VM station chain', 'kind': 'unchanged (dsfd_bk_collector vd/vf)'}],
           'mirror_rule': MIRROR,
           'credits': 'DM 12 landing entries per lane (round trip 2 x 7 + 5 = 19 edges at 0.5 word/edge)'}
    out['collector'] = col
    # ------------------------------------------------------------------ capture
    GW, GH, CHAN = 118.8, 324.0, 21.6
    g_spec = {'master': 'dsfd_capt_grp', 'w_um': GW, 'h_um': GH, 'domain': 'stream_1p2+serial_0p9',
              'note': 'capture root-group tile (16 roots); S face = gather rows + ctl constant bus (channel), '
                      'N face = VM writes (serial)',
              'ports': [['f_row', 16 * 53, 'input', 'S', 'M5', 2, 0.5], ['f_k', KB, 'input', 'S', 'M5', 1, 0.9],
                        ['t_sb', 2, 'output', 'S', 'M5', 1, 0.96], ['ck', 1, 'input', 'S', 'M5', 1, 0.03],
                        ['rst', 1, 'input', 'S', 'M5', 1, 0.04],
                        ['t_vm', 16 * 104, 'output', 'N', 'M5', 1, 0.5], ['ckv', 1, 'input', 'N', 'M5', 1, 0.05],
                        ['rsv', 1, 'input', 'N', 'M5', 1, 0.06],
                        ['f_sn', 64, 'input', 'S', 'M5', 1, 0.12], ['t_st', 64, 'output', 'N', 'M5', 1, 0.92]]}
    write('dsfd_capt_grp', GW, GH, 'stream_1p2+serial_0p9', plan(g_spec), g_spec)
    CTW = 86.4
    k_spec = {'master': 'dsfd_capt_ctl', 'w_um': CTW, 'h_um': GH, 'domain': 'stream_1p2',
              'note': 'capture control tile; S face = gather control word + per-tile constant buses + tile status',
              'ports': [['f_ctl', 163, 'input', 'S', 'M5', 1, 0.3], ['t_k', 8 * KB, 'output', 'S', 'M5', 1, 0.65],
                        ['f_sb', 16, 'input', 'S', 'M5', 1, 0.95], ['ck', 1, 'input', 'S', 'M5', 1, 0.05],
                        ['rst', 1, 'input', 'S', 'M5', 1, 0.07],
                        ['t_sn', 64, 'output', 'S', 'M5', 1, 0.15]]}
    write('dsfd_capt_ctl', CTW, GH, 'stream_1p2', plan(k_spec), k_spec)
    xs = [0.0, 118.8, 237.6, 356.4, 561.6, 680.4, 799.2, 918.0]
    cap = {'slab': 'dsfd_sp_capture', 'outline_um': [1036.8, r4(GH + CHAN)],
           'generator_change': 'G6 again: 1015.176 x 302.4 -> 1036.8 x 345.6 (tiles + the 21.6-um channel); the '
                               'gather t_capture pins re-plan to the tiles f_row x (root r -> tile r // 16, bits '
                               '[53 (r % 16) +: 53] of its f_row)',
           'tiles': [{'inst': f'u_g{t}', 'master': 'dsfd_capt_grp', 'x': xs[t], 'y': CHAN, 'orient': 'R0',
                      'roots': [16 * t, 16 * t + 15]} for t in range(8)] +
                    [{'inst': 'u_ctl', 'master': 'dsfd_capt_ctl', 'x': 475.2, 'y': CHAN, 'orient': 'R0'}],
           'hops': [{'what': 'u_ctl t_k[99 t +: 99] -> u_g<t> f_k; u_g<t> t_sb -> u_ctl f_sb[2 t +: 2]',
                     'length_um_max': 562.0, 'stations': 0,
                     'kind': 'pin-to-pin in the S channel (flop at both pins; <= 504 um SS reach at 1.2 GHz)'},
                    {'what': 'gather t_capture -> tile f_row / ctl f_ctl', 'kind': 'abutment through the channel'},
                    {'what': 'u_ctl t_sn (64 b status, stream) -> u_g3 f_sn; u_g3 t_st (serial) -> VM status (t_vm[13312 +: 64])',
                     'kind': 'pin-to-pin in the S channel / abutment N face; f_sn of the other tiles tied 0, their t_st open'},
                    {'what': 'tile t_vm -> VM (serial)', 'kind': 'abutment (N face), as G3'}],
           'clock': 'ck and ckv per tile, own CTS trees'}
    # SAFE capture (owner SAFE variant): dsfd_capt_g2 (single clock) under dsfd_capt_x (the 17 crossings), abutted N/S
    G2H, XH = 162.0, 270.0
    g2_spec = {'master': 'dsfd_capt_g2', 'w_um': GW, 'h_um': G2H, 'domain': 'stream_1p2',
               'note': 'SAFE capture root-group tile (no crossings); N face abuts dsfd_capt_x',
               'ports': [['f_row', 16 * 53, 'input', 'S', 'M5', 2, 0.5], ['f_k', KB, 'input', 'S', 'M5', 1, 0.9],
                         ['t_sb', 2, 'output', 'S', 'M5', 1, 0.96], ['ck', 1, 'input', 'S', 'M5', 1, 0.03],
                         ['rst', 1, 'input', 'S', 'M5', 1, 0.04],
                         ['t_w', 16 * 52, 'output', 'N', 'M5', 1, 0.5], ['f_ho', 1, 'input', 'N', 'M5', 1, 0.9]]}
    write('dsfd_capt_g2', GW, G2H, 'stream_1p2', plan(g2_spec), g2_spec)
    x_spec = {'master': 'dsfd_capt_x', 'w_um': GW, 'h_um': XH, 'domain': 'stream_1p2+serial_0p9',
              'note': 'SAFE capture crossing tile (16 pair packers + ratio CDCs + status crossing); S face abuts dsfd_capt_g2',
              'ports': [['f_w', 16 * 52, 'input', 'S', 'M5', 1, 0.5], ['t_ho', 1, 'output', 'S', 'M5', 1, 0.9],
                        ['f_sn', 64, 'input', 'S', 'M5', 1, 0.12], ['ck', 1, 'input', 'S', 'M5', 1, 0.03],
                        ['rst', 1, 'input', 'S', 'M5', 1, 0.04],
                        ['t_vm', 16 * 104, 'output', 'N', 'M5', 1, 0.5], ['t_st', 64, 'output', 'N', 'M5', 1, 0.92],
                        ['ckv', 1, 'input', 'N', 'M5', 1, 0.05], ['rsv', 1, 'input', 'N', 'M5', 1, 0.06]]}
    write('dsfd_capt_x', GW, XH, 'stream_1p2+serial_0p9', plan(x_spec), x_spec)
    cap['safe_variant'] = {
        'composition': 'ot_s81ph_cap_t SAFE 1 (dsfd_sp_capture CORE 3)',
        'outline_um': [1036.8, r4(CHAN + G2H + XH)],
        'tiles': [{'inst': f'u_g{t}', 'master': 'dsfd_capt_g2', 'x': xs[t], 'y': CHAN, 'orient': 'R0'} for t in range(8)] +
                 [{'inst': f'u_x{t}', 'master': 'dsfd_capt_x', 'x': xs[t], 'y': r4(CHAN + G2H), 'orient': 'R0'} for t in range(8)] +
                 [{'inst': 'u_ctl', 'master': 'dsfd_capt_ctl', 'x': 475.2, 'y': CHAN, 'orient': 'R0'}],
        'hops': ['u_g<t> t_w -> u_x<t> f_w and u_x<t> t_ho -> u_g<t> f_ho: abutted (same x, flop at both pins)',
                 'u_ctl t_sn -> u_x3 f_sn (64 b; other tiles tie 0), u_x3 t_st -> VM status', 'others as the main variant'],
        'cycles': '+2 VM-write latency vs the main tiled variant (pin flops of the g2 / x hop); phase completion unchanged'}
    out['capture'] = cap
    for kind, rec in out.items():
        rec['schema'] = 'opentallas.s81_ph.tiles.v1'
        rec['generator'] = 'tools/s81_ph/s81_ph_tiles_plan.py'
        p = ROOT / 'results/rtl/s81_ph_20261006' / kind / 'tiles.json'
        old = json.loads(p.read_text()) if p.exists() else {}
        old.update(rec)
        p.write_text(json.dumps(old, indent=1) + '\n')
        print(p)


if __name__ == '__main__':
    main()
