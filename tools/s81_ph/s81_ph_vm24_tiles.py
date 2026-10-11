#!/usr/bin/env python3
"""s81-vm-1011 (2026-10-11): pin plan of the VM master v2 hard tile dsfd_vm_bgq24 (rtl/dsrom_sys/s81_ph/vm/dsfd_vm_bgq_sys.sv:
dsfd_vm_bgq at NP 24 / NPR 8, NSTG 2, one 128-b bit slice, 8 banks = 8 x ot_sram_1r1w_512x128_m4_r2c2) and the master
composition record.

Tile 460.8 x 500.04 um: the 24-port request bus (3,552 b) + 8-lane read return (1,039 b) enter the N face and leave the
S face at identical x (abutted chain of 4 tiles per slice), all on M5 at 2 tracks (10.4 pins/um < the 12 pins/um/layer
lint limit); the macro column sits at the W edge (place_macros_vm24.tcl), the E channel carries the bus.  The master
(dsfd_sp_vm_m) = FE (N) + 4 slices x 4 tiles + BE (S); slab = 4 x 460.8 wide.

Writes physical/s81_ph_views/ports/contract_vm24/dsfd_vm_bgq24/{ports.json, io_place.tcl, ports.svh} and
physical/s81_ph_views/vm_master/composition.json."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s81_ph_coll_tiles as T   # noqa: E402

T.CONTRACT = 'contract_vm24'
W, H, NT, NS = 460.8, 500.04, 4, 4
NP, NPR, RA, DW = 24, 8, 14, 128
FE_H, BE_H = 216.0, 108.0          # FE / BE outline heights (first estimate: FE ~125k flops + 16.8k die pins; BE ~10k)


def tile():
    pl = T.Plan('dsfd_vm_bgq24', W, H)
    pairs = [('i_v', 'f_v', NP), ('i_we', 'f_we', NP), ('i_row', 'f_row', NP * RA), ('i_mask', 'f_mask', NP * DW // 32),
             ('i_d', 'f_d', NP * DW), ('r_v', 'o_v', NPR), ('r_d', 'o_d', NPR * DW), ('r_f', 'o_f', 4), ('r_o', 'o_o', 3)]
    x = 2.4
    for i_n, o_n, b in pairs:
        pl.bus(i_n, b, 'input', 'N', 'M5', x)
        x = pl.bus(o_n, b, 'output', 'S', 'M5', x)
    assert x < W - 1, x
    pl.bus('ck', 1, 'input', 'W', 'M4', H / 2); pl.bus('rs', 1, 'input', 'W', 'M4', H / 2 + 4.8)
    pl.bus('grp', 2, 'input', 'W', 'M4', H / 2 + 9.6)
    pl.emit('VM master v2 tile (dsfd_vm_bgq NP 24 / NPR 8, 8 banks x 128 b = 8 SRAM macros); N face = request / read-data chain '
            'in, S face = the same signals out at identical x (4 abutted tiles a slice, 4 slices W -> E)')
    return x


def main():
    x = tile()
    comp = dict(
        schema='opentallas.s81_ph.composition.v1', slab='dsfd_sp_vm v2 (VM master, s81-vm-1011)',
        slab_um=[NS * W, FE_H + NT * H + BE_H],
        source='rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm.sv module dsfd_sp_vm_m (the exact composition netlist; gate '
               'tools/s81_vm/s81_vm_gate.py)',
        instances=[dict(inst='u_fe', master='dsfd_vm_fe', xy=[0.0, T.r4(BE_H + NT * H)], orient='R0', um=[NS * W, FE_H])]
        + [dict(inst=f'g_h[{h}].g_t[{t}].u_bg', master='dsfd_vm_bgq24', xy=[T.r4(h * W), T.r4(BE_H + (NT - 1 - t) * H)],
                orient='R0', grp=t, slice=h) for h in range(NS) for t in range(NT)]
        + [dict(inst='u_be', master='dsfd_vm_be', xy=[0.0, 0.0], orient='R0', um=[NS * W, BE_H])],
        nets=dict(chain='per slice h: g_t[t].f_* -> g_t[t+1].i_*, g_t[t].o_* -> g_t[t+1].r_* by abutment; FE m_* slice h -> '
                        'g_t[0].i_* (FE S face at the tile x); g_t[0].r_v / r_d / r_o = chain head (0), r_f = FE status; '
                        'g_t[3].o_* -> BE (BE N face at the tile x); slice 0 g_t[3].f_v[5] / f_we[5] / f_d[5*128 +: 92] -> BE '
                        '(P2 metadata); FE fe_flt[16] -> BE (sticky status, multicycle); BE t_p2c -> FE f_p2c (credit)',
                  clock='ck = serial 0.9 GHz to FE, every tile and BE; cks = stream 1.2 GHz to FE / BE (dsfd_sp_ctrl side: '
                        'engine adapter, ratio CDC FIFOs)'),
        ports='NP 24: p0 / p1 WFC kit (dsfd_vm_wfc_ep RD2), p2 X2, p3 / p4 dsfd_sp_ctrl VM lanes A / B, p5 P2 reader, p6 / p7 '
              'X0 / X1, p8 .. p23 capture lanes 0 .. 15 (write only)',
        latency='fixed read latency 24 serial cycles from the client pins (ports 0, 1, 2, 6, 7); ctrl reads via CDC (vrv)')
    (T.ROOT / 'physical/s81_ph_views/vm_master').mkdir(parents=True, exist_ok=True)
    (T.ROOT / 'physical/s81_ph_views/vm_master/composition.json').write_text(json.dumps(comp, indent=1) + '\n')
    print('ok last x', round(x, 2), 'slab', comp['slab_um'])


if __name__ == '__main__':
    main()
