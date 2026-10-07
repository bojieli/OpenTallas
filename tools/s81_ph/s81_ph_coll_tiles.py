#!/usr/bin/env python3
"""CLAUDE S81-PH coll v2: pin plans of the collective tiles + the slab composition.

dsfd_sp_collective (1015.176 x 1369.416) -> 4 x dsfd_coll_lane_w (W column, lanes 0..3), 4 x dsfd_coll_lane_e
(E column, lanes 4..7), dsfd_coll_core (centre column) inside the slab outline; dsfd_coll_ck (PLL + reset
sequencer) is a separate small hard block placed by the die next to the slab.  Lane <-> core pins face each other
at the same y (pin-to-pin hops across a 0.192-um gap); lane die pins (rx / tx / tf) on the slab's W / E edges.
Generator conventions (on-track: M4 horizontal / M5 vertical, offset 0.012, pitch 0.048; pin 0.024 x 0.192).
Writes physical/s81_ph_views/ports/contract/<tile>/{ports.json, io_place.tcl, ports.svh} and
physical/s81_ph_views/collective/composition.json."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P, OFF = 0.048, 0.012
SW, SH = 1015.176, 1369.416
LW, LH = 253.8, 340.2              # lane tile (10 x 512x128 SRAM macros in one column: 10 x 29.736 + halos)
CW, CH = 507.384, 1360.8           # core tile (24 x 256x256 SRAM macros + ~90k flops)
KW, KH = 216.0, 216.0              # clock tile (PLL 172.8 x 172.8)
CONTRACT = "contract"
COMPOSITION = "composition.json"
Y_DIE, Y_CORE = 60.0, 150.0        # lane die-pin group / lane-core group start (lane-relative)


def r4(v):
    return round(v + 1e-9, 4)


class Plan:
    def __init__(self, master, w, h):
        self.m, self.w, self.h, self.pins, self.dirs, self.used = master, w, h, [], {}, set()

    def put(self, port, bit, face, layer, coord):
        t = round((coord - OFF) / P)
        pos = OFF + t * P
        key = (face, layer, t)
        assert key not in self.used, (self.m, port, bit, face, coord)
        self.used.add(key)
        if face == 'S': r = (pos - 0.012, 0.0, pos + 0.012, 0.192)
        elif face == 'N': r = (pos - 0.012, self.h - 0.192, pos + 0.012, self.h)
        elif face == 'W': r = (0.0, pos - 0.012, 0.192, pos + 0.012)
        else: r = (self.w - 0.192, pos - 0.012, self.w, pos + 0.012)
        assert 0.3 < pos < (self.h if face in 'WE' else self.w) - 0.3, (self.m, port, pos)
        self.pins.append((f'{port}[{bit}]', layer) + tuple(r4(v) for v in r))

    def bus(self, port, bits, d, face, layer, start, step=2, lo=0, n=None):
        """bits lo .. lo + n - 1 of port at tracks start, start + step * P, ...; returns the next free coordinate"""
        n = bits if n is None else n
        self.dirs[port] = (d, bits)
        for i in range(n):
            self.put(port, lo + i, face, layer, start + i * step * P)
        return start + n * step * P + 2 * P

    def emit(self, note):
        d = ROOT / 'physical/s81_ph_views/ports' / CONTRACT / self.m
        d.mkdir(parents=True, exist_ok=True)
        ports = {}
        for nm, ly, *r in self.pins:
            ports.setdefault(nm.split('[')[0], dict(layer=ly, pins=[]))['pins'].append([nm, ly] + list(r))
        for b, p in ports.items():
            p['bits'] = self.dirs[b][1]
            p['direction'] = self.dirs[b][0]
            assert len(p['pins']) == p['bits'], (self.m, b)
        rec = dict(master=self.m, die=CONTRACT, w_um=self.w, h_um=self.h, obs_top=7, domain='stream_1p2', instances=None,
                   orients=['R0'], ports=ports, generator=dict(file='tools/s81_ph/s81_ph_coll_tiles.py', note=note))
        (d / 'ports.json').write_text(json.dumps(rec, indent=0) + '\n')
        L = [f'# {self.m} (contract pin plan, tools/s81_ph/s81_ph_coll_tiles.py)']
        for nm, ly, x0, y0, x1, y1 in self.pins:
            L.append(f'place_pin -pin_name {{{nm}}} -layer {ly} -location {{{(x0 + x1) / 2:.4f} {(y0 + y1) / 2:.4f}}} '
                     f'-pin_size {{{x1 - x0:.4f} {y1 - y0:.4f}}}')
        (d / 'io_place.tcl').write_text('\n'.join(L) + '\n')
        (d / 'ports.svh').write_text(',\n'.join(f'    {self.dirs[p][0]} wire [{self.dirs[p][1] - 1}:0] {p}' for p in sorted(self.dirs)) + '\n')


def lane_core_group(pl, face, y0, k=None):
    """the lane <-> core interface in one fixed order; k = lane index on the core (packed buses), None on a lane"""
    y = y0
    if k is None:
        spec = [('lo_v', 1, 'input', 0), ('lo_r', 1, 'output', 0), ('lo_d', 553, 'input', 0), ('li_v', 1, 'output', 0),
                ('li_r', 1, 'input', 0), ('li_d', 553, 'output', 0), ('flt', 3, 'output', 0)]
        for p, b, d, lo in spec:
            y = pl.bus(p, b, d, face, 'M4', y)
    else:
        spec = [('lo_v', 8, 'output', k, 1), ('lo_r', 8, 'input', k, 1), ('lo_d', 8 * 553, 'output', 553 * k, 553),
                ('li_v', 8, 'input', k, 1), ('li_r', 8, 'output', k, 1), ('li_d', 8 * 553, 'input', 553 * k, 553),
                ('flt', 24, 'input', 3 * k, 3)]
        for p, b, d, lo, n in spec:
            y = pl.bus(p, b, d, face, 'M4', y, lo=lo, n=n)
    return y


def main():
    global LW, SW, CONTRACT, COMPOSITION
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--lane-width', type=float, default=LW)
    ap.add_argument('--contract', default=CONTRACT)
    ap.add_argument('--composition', default=COMPOSITION)
    args = ap.parse_args()
    assert args.lane_width >= 253.8
    assert '/' not in args.contract and '/' not in args.composition
    LW = args.lane_width
    SW = r4(2 * LW + CW + 0.192)
    CONTRACT, COMPOSITION = args.contract, args.composition
    comp = []
    for side, die_face, core_face, x0 in (('w', 'W', 'E', 0.0), ('e', 'E', 'W', SW - LW)):
        pl = Plan(f'dsfd_coll_lane_{side}', LW, LH)
        y = pl.bus('rx', 515, 'input', die_face, 'M4', Y_DIE)
        y = pl.bus('tx', 512, 'output', die_face, 'M4', y)
        pl.bus('tf', 1, 'output', die_face, 'M4', y)
        yc = lane_core_group(pl, core_face, Y_CORE)
        assert yc < LH - 1
        for i, p in enumerate(('ck', 'rs', 'chb')):
            pl.bus(p, 1, 'input', 'N', 'M5', LW / 2 + 4.8 * (i - 1))
        pl.emit(f'collective lane tile ({"W" if side == "w" else "E"} column): die lane pins on the {die_face} face, core '
                f'interface on the {core_face} face at y {Y_CORE}+ (registered 2-slot skids); 4 instances R0')
        for k in range(4):
            lane = k if side == 'w' else 4 + k
            comp.append(dict(inst=f'g_lane[{lane}].g_{side}.u_l', master=pl.m, xy=[r4(x0), r4(k * LH)], orient='R0',
                             lane=['W0', 'W1', 'W2', 'W3', 'E0', 'E1', 'E2', 'E3'][lane], ch_b=int(lane not in (0, 4))))
    pc = Plan('dsfd_coll_core', CW, CH)
    for k in range(8):
        lane_core_group(pc, 'W' if k < 4 else 'E', (k % 4) * LH + Y_CORE, k=k)
    x = pc.bus('f_vm', 592, 'input', 'S', 'M5', 4.8)
    x = pc.bus('ts', 3, 'input', 'S', 'M5', x)
    x = pc.bus('t_vm', 2100, 'output', 'S', 'M5', x, step=1)
    assert x < CW - 1, x
    for i, p in enumerate(('ck', 'rs')):
        pc.bus(p, 1, 'input', 'N', 'M5', CW / 2 + 4.8 * i)
    pc.emit('collective core tile (engine, VM queues, packer), centre column of the slab; lane interfaces W (lanes 0..3) '
            'and E (4..7) at the lane tiles\' y; VM interface on the S face')
    comp.append(dict(inst='u_core', master='dsfd_coll_core', xy=[LW, 0.0], orient='R0'))
    pk = Plan('dsfd_coll_ck', KW, KH)
    pk.bus('refclk', 1, 'input', 'W', 'M4', 100.8); pk.bus('por', 1, 'input', 'W', 'M4', 105.6)
    for i, p in enumerate(('pll_stream', 'pll_serial', 'pll_hbm', 'rst_stream', 'rst_serial', 'rst_hbm')):
        pk.bus(p, 1, 'output', 'E', 'M4', 96.0 + 2.4 * i)
    pk.emit('collective clock tile: die PLL (ot_s81_pll_bb hard macro) + reset sequencer; placed by the die next to the slab')
    rec = dict(schema='opentallas.s81_ph.composition.v1', slab='dsfd_sp_collective', slab_um=[SW, SH],
               source='rtl/dsrom_sys/s81_ph/dsfd_sp_collective.sv (default = tiled: the exact composition netlist; bench '
                      'rtl/dsrom_sys/s81_ph/coll/run_coll_bench.sh)',
               instances=comp, outside_slab=[dict(inst='u_ck', master='dsfd_coll_ck', um=[KW, KH],
                                                  note='die places it next to the slab (any free site); its pll_stream '
                                                       'output is the die stream clock tree root')],
               nets=dict(clocks='pll_stream (u_ck) -> ck of every lane tile and of u_core (die clock tree); rst_stream -> rs of every tile (async assert, synchronised in each tile)',
                         lanes='lane tile lo_* / li_* / flt <-> u_core lo_* / li_* / flt bits of that lane: abutting faces at the same y (0.192-um gap)',
                         die='lane tile rx / tx / tf = the slab rX / tdX / tfX of its lane; u_core f_vm / ts / t_vm (S face) = the slab VM interface; '
                             'chb pin tied 0 on lanes W0 / E0 (UCIe ACK timeout), 1 elsewhere'),
               timing='every tile pin a flop (skid main / skid-valid flops, pin registers), forwarded clocks kept buffers')
    (ROOT / 'physical/s81_ph_views/collective' / COMPOSITION).write_text(json.dumps(rec, indent=1) + '\n')
    print('ok', len(pc.pins), 'core pins')


if __name__ == '__main__':
    main()
