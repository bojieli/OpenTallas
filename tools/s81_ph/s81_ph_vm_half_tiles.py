#!/usr/bin/env python3
"""CLAUDE s81-blocks 2026-10-07: pin plan of the BIT-SLICED VM bank-group tile dsfd_vm_bgh (rtl/dsrom_sys/s81_ph/vm/
dsfd_vm_bg.sv) in die variant contract_vmh.  The 1015.176 x 500.04 dsfd_vm_bg (32 macros, vm_bg 37f7479aa congested
in global route for 17 h at 1.02 M instances) becomes two 507.588 x 500.04 tiles side by side (W: row bits [0, 256),
E: [256, 512)), 16 macros each; each half is its own abutted chain of 4 (same N -> S order and hop latency as the
v2 chain), the request word (v, we, row) goes to both, data and mask split.  Same slab outline, zero added cycles."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s81_ph_coll_tiles as T   # noqa: E402

T.CONTRACT = 'contract_vmh'
W, H, NT = 1015.176 / 2, 500.04, 4
NP, RA, OW = 8, 14, 3


def tile(master, ns):
    w = 1015.176 / ns
    pl = T.Plan(master, w, H)
    pairs = [('i_v', 'f_v', NP), ('i_we', 'f_we', NP), ('i_row', 'f_row', NP * RA), ('i_mask', 'f_mask', NP * 16 // ns),
             ('i_d', 'f_d', NP * 512 // ns), ('r_v', 'o_v', NP), ('r_d', 'o_d', NP * 512 // ns), ('r_f', 'o_f', 4), ('r_o', 'o_o', OW)]
    x = 2.4
    for i_n, o_n, b in pairs:
        pl.bus(i_n, b, 'input', 'N', 'M5', x)
        x = pl.bus(o_n, b, 'output', 'S', 'M5', x)
    assert x < w - 1, (master, x)
    pl.bus('ck', 1, 'input', 'W', 'M4', H / 2); pl.bus('rs', 1, 'input', 'W', 'M4', H / 2 + 4.8)
    pl.bus('grp', 2, 'input', 'W', 'M4', H / 2 + 9.6)
    pl.emit(f'VM bit-sliced bank-group tile (8 banks x {512 // ns} b = {32 // ns} SRAM macros); N face = request / read-data '
            f'chain in, S face = the same signals out at identical x ({ns} abutted chains of 4, slice h = row bits '
            f'[{512 // ns}h, {512 // ns}(h+1)) from W to E)')
    return x


def main():
    x = tile('dsfd_vm_bgh', 2)
    print('bgh last x', round(x, 2), 'bgq last x', round(tile('dsfd_vm_bgq', 4), 2))
    comp = dict(schema='opentallas.s81_ph.composition.v1', slab='VM memory sub-macro, bit-sliced (contract_vmh)',
                slab_um=[2 * W, H * NT],
                source='rtl/dsrom_sys/s81_ph/vm/dsfd_vm_bg.sv module dsfd_vm_mem_h (bench run_vm_bench.sh +define+TILED +define+TILED_HALF)',
                instances=[dict(inst=f'g_h[{h}].g_t[{t}].u_bg', master='dsfd_vm_bgh', xy=[T.r4(h * W), T.r4((NT - 1 - t) * H)],
                                orient='R0', grp=t, slice=h) for h in range(2) for t in range(NT)],
                nets=dict(chain='per half: g_t[t].f_* -> g_t[t+1].i_*, g_t[t].o_* -> g_t[t+1].r_* by abutment; i_v / i_we / i_row '
                                'of both halves from the same VM request ports; i_mask / i_d bits [8h, 8h+8) / [256h, 256h+256) '
                                'of each port; read data = {E, W} halves; o_v / o_f / o_o from either half (identical)'),
                latency='read latency L + 8 = 18 serial cycles, unchanged from vm v2')
    (T.ROOT / 'physical/s81_ph_views/vm_mem/composition_vmh.json').write_text(json.dumps(comp, indent=1) + '\n')
    print('ok')


if __name__ == '__main__':
    main()
