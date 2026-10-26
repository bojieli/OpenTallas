#!/usr/bin/env python3
"""el1011-ds-vm/be-sl4 (2026-10-11, GLUE PLACEMENT rule): pin plan of the BE slice tile dsfd_vm_be_sl v4.

No dsfd_vm_be parent element: the die places the 4 slice tiles (x = s * 345.6 + 43.2 under bgq column s) and supplies
the die-top relays.  N face (o_* from the column's tile-3) and S face (this slice's response bits, c_l0r centred) are
exactly v3.  W face: ck / cks / rn_in / rns_in, the die-facing control on the tile's own pins (f_vx / f_wex / f_mx /
f_v5 / f_we5 / this slice's 23 bits f_m5s; pin flops + KX = 4 alignment relays inside; the die inserts exactly
DIE_D = 3 relay stages on every control seam, equal for all slices), fe_flt (die drives it on slice 0, 0 elsewhere) and
the status chain input st_i (40 b).  E face: st_o (40 b, same y as st_i: an abutting 43.2-um seam to the E neighbour,
no die relay) + the sticky status t_err / flt / fvec / max_occ (the die uses slice 3's) + t_p2c.
Writes physical/s81_ph_views/ports/contract_vm28/dsfd_vm_be_sl/."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s81_ph_coll_tiles as T          # noqa: E402
import s81_ph_vm_master_tiles as V     # noqa: E402
import s81_ph_vm_be_v3 as B3           # noqa: E402

T.CONTRACT = 'contract_vm28'
TW, TH, OX = B3.TW, B3.TH, B3.OX


def tile_plan(bg):
    pl = V.Plan2('dsfd_vm_be_sl', TW, TH)
    for port, n in (('o_v', 10), ('o_d', 1280), ('o_f', 4), ('o_o', 3)):
        pl.dirs[port] = ('input', n)
        for b in range(n):
            ly, x = bg[f'{port}[{b}]']
            pl.put(port, b, 'N', ly, x - OX)
    order = [('srq_d', 256, 'output'), ('srq_v', 2, 'output'), ('vrv', 1, 'output'), ('vrq', 128, 'output'),
             ('bl_d', 16 * 128, 'output', 0, 8 * 128), ('c_l0r', 1, 'input'), ('c_l0v', 1, 'output'), ('c_l0d', 151, 'output'),
             ('bl_d', 16 * 128, 'output', 8 * 128, 8 * 128), ('bl_v', 16, 'output')]
    tr = [t for t in V.tracks(TW) if t[0] == 'M5']
    k = 0
    for rec in order:
        nm, bits, d = rec[:3]
        lo, n = (rec[3], rec[4]) if len(rec) > 3 else (0, bits)
        pl.dirs[nm] = (d, bits)
        for b in range(lo, lo + n):
            ly, x = tr[k]; k += 1
            pl.put(nm, b, 'S', ly, x)
    y = 6.0
    for nm, bits, d in (('ck', 1, 'input'), ('cks', 1, 'input'), ('rn_in', 1, 'input'), ('rns_in', 1, 'input'),
                        ('f_vx', 5, 'input'), ('f_wex', 5, 'input'), ('f_mx', 20, 'input'), ('f_v5', 1, 'input'),
                        ('f_we5', 1, 'input'), ('f_m5s', 23, 'input'), ('fe_flt', 16, 'input')):
        y = pl.bus(nm, bits, d, 'W', 'M4', y, step=8)
    ys = y + 2.0
    pl.bus('st_i', 40, 'input', 'W', 'M4', ys, step=8)
    ye = pl.bus('st_o', 40, 'output', 'E', 'M4', ys, step=8)
    for nm, bits in (('t_err', 1), ('flt', 1), ('fvec', 32), ('max_occ', 3), ('t_p2c', 1)):
        ye = pl.bus(nm, bits, 'output', 'E', 'M4', ye, step=8)
    assert ye < TH - 2 and ys + 40 * 8 * T.P < TH - 2, (ye, TH)
    pl.emit('VM back end v4 slice tile (el1011-ds-vm/be-sl4): N = column tile-3 S pins; S = this slice\'s response bits '
            '(c_l0r centred); W = clocks, resets, die-facing control (DIE_D = 3 die relays), fe_flt, status chain in; '
            'E = status chain out (abutting seam), sticky status, t_p2c')


def main():
    tile_plan(V.tile_x())


if __name__ == '__main__':
    main()
