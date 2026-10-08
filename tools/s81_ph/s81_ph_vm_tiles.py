#!/usr/bin/env python3
"""CLAUDE S81-PH vm v2: pin plan of the VM bank-group tile dsfd_vm_bg and the 4-tile chain composition.

The v1 VM memory sub-macro (ot_s81ph_vm_mem, 1015.176 x 2000.16 um, 128 SRAM macros) -> 4 x dsfd_vm_bg (1015.176 x
500.04, R0) stacked in the same outline: tile 0 on top (y 1500.12) .. tile 3 at the bottom (y 0).  Requests enter
tile 0's N face; every tile's S face outputs (forwarded requests f_*, merged read data o_*) sit at exactly the x of
the next tile's N face inputs (i_*, r_*), so every hop is a straight 0-um abutment.  Tile 3's S face = the VM
read port outputs.  Tools: tools/s81_ph/s81_ph_coll_tiles.py Plan (generator conventions)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from s81_ph_coll_tiles import Plan, ROOT, r4, P   # noqa: E402

W, H, NT = 1015.176, 500.04, 4
NP, RA, OW = 8, 14, 3


def main():
    pl = Plan('dsfd_vm_bg', W, H)
    pairs = [('i_v', 'f_v', NP), ('i_we', 'f_we', NP), ('i_row', 'f_row', NP * RA), ('i_mask', 'f_mask', NP * 16),
             ('i_d', 'f_d', NP * 512), ('r_v', 'o_v', NP), ('r_d', 'o_d', NP * 512), ('r_f', 'o_f', 4), ('r_o', 'o_o', OW)]
    x = 2.4
    for i_n, o_n, b in pairs:
        pl.bus(i_n, b, 'input', 'N', 'M5', x)
        x = pl.bus(o_n, b, 'output', 'S', 'M5', x)
    assert x < W - 1, x
    pl.bus('ck', 1, 'input', 'W', 'M4', H / 2); pl.bus('rs', 1, 'input', 'W', 'M4', H / 2 + 4.8)
    pl.bus('grp', 2, 'input', 'W', 'M4', H / 2 + 9.6)
    pl.emit('VM bank-group chain tile (8 banks = 32 SRAM macros); N face = request / read-data chain in, S face = the same '
            'signals out at identical x (abutted chain of 4, tile 0 on top)')
    comp = dict(schema='opentallas.s81_ph.composition.v1', slab='VM memory sub-macro (ot_s81ph_vm_mem v1 outline)',
                slab_um=[W, H * NT],
                source='rtl/dsrom_sys/s81_ph/vm/dsfd_vm_bg.sv module dsfd_vm_mem (the exact composition netlist; bench '
                       'rtl/dsrom_sys/s81_ph/vm/run_vm_bench.sh +define+TILED)',
                instances=[dict(inst=f'g_t[{t}].u_bg', master='dsfd_vm_bg', xy=[0.0, r4((NT - 1 - t) * H)], orient='R0',
                                grp=t) for t in range(NT)],
                nets=dict(chain='g_t[t].f_* -> g_t[t+1].i_*, g_t[t].o_* -> g_t[t+1].r_* by abutment (same x, S face of t on N face of t+1); '
                                'g_t[0].r_* tied 0; g_t[0].i_* = the VM request ports; g_t[3].o_* = read data (o_v, o_d), '
                                'status o_f = {fault, code[2:0]}, o_o = max_occ; g_t[3].f_* unused',
                          clock='ck = the serial clock (0.9 GHz) to every tile from the die clock tree; rs = async reset; grp = tile index (tie cells)'),
                latency='read latency L + 8 = 18 serial cycles (v1: 10), fixed; exact (issue cycle, port) order')
    (ROOT / 'physical/s81_ph_views/vm_mem/composition.json').write_text(json.dumps(comp, indent=1) + '\n')
    print('ok', len(pl.pins))


if __name__ == '__main__':
    main()
