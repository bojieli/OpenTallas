#!/usr/bin/env python3
"""el1011-ds-vm/be (2026-10-11): pin plans of the BIT-SLICED VM back end v3 (ds-1010 decision).

dsfd_vm_be (1,520.064 x 136.08, contract_vm28) = 4 identical hardened slice tiles dsfd_vm_be_sl (TW x TH) + a thin parent.
Tile s sits under bgq column s at x = s * 345.6 + OX, y = YB (21.6-um S channel: die-pin stubs; 21.6-um N channel: the
parent's horizontal relays; outline 1,520.064 x 136.08).  Tile N face = the column's tile-3 S pins (o_v / o_d / o_f / o_o, same x and layer
as the BE die pins above it); tile S face = this slice's bits of every response; tile W face = clocks, synchronous resets,
the relayed control (xc / pm) and the status back; tile E face = the P2 credit.

BE S-FACE CONTRACT v3: every response bit leaves at the x of the tile that produces it (slice s -> tile s range);
pin names and widths are unchanged.  Writes physical/s81_ph_views/ports/contract_vm28/{dsfd_vm_be, dsfd_vm_be_sl}/ and
physical/s81_ph_views/vm_master/place_macros_be_v3.tcl."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s81_ph_coll_tiles as T          # noqa: E402
import s81_ph_vm_master_tiles as V     # noqa: E402

T.CONTRACT = 'contract_vm28'
SLAB_W, COL, NS = V.SLAB_W, V.W, V.NS
PX = V.PX                              # s81die-1011 contract v3: bgq column pitch 388.8 (345.6 tile + 43.2 channel)
# BE v3 outline (ds-1010 FLOORPLAN_MARGIN 2026-10-11: 4 tiles = 112,348 um2 were 69.4% of the 1,520 x 108 core):
# 136.08 tall (504 rows) -> 21.6-um N / S channels around the tiles.
BE_H = 136.08
TW, TH = 302.4, 92.88                  # tile outline (28 x the 10.8-um M7 PG pitch; 344 rows)
OX, YB = 43.2, 21.6                    # tile origin in its column; S channel height (N channel = BE_H - YB - TH = 21.6)
CL0R_X = (PX + OX + TW + 2 * PX + OX) / 2   # die c_l0r pin: middle of the channel between slice tiles 1 and 2 (<= ~530 um to any tile pin)


def tile_plan(bg):
    pl = V.Plan2('dsfd_vm_be_sl', TW, TH)
    for port, n in (('o_v', 10), ('o_d', 1280), ('o_f', 4), ('o_o', 3)):
        pl.dirs[port] = ('input', n)
        for b in range(n):
            ly, x = bg[f'{port}[{b}]']
            pl.put(port, b, 'N', ly, x - OX)
    # S face: c_l0r / c_l0v / c_l0d at the middle of the face (the only unregistered slab-wide input fans in there)
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
                        ('xc', 25, 'input'), ('pm', 24, 'input'), ('sflt', 5, 'output'), ('sst', 17, 'output')):
        y = pl.bus(nm, bits, d, 'W', 'M4', y, step=8)
    pl.bus('t_p2c', 1, 'output', 'E', 'M4', 40.0)
    pl.emit('VM back end v3 slice tile (el1011-ds-vm/be): N = this column\'s tile-3 S pins; S = this slice\'s 128-b bits of '
            't_srq / vrq / 16 bus lanes / P2 (+23 metadata) with c_l0r centred; W = clocks, resets, relayed control, status')
    return {nm: (ly, (x0 + x1) / 2) for nm, ly, x0, y0, x1, y1 in pl.pins}


def be_plan(bg, tp):
    pl = V.Plan2('dsfd_vm_be', SLAB_W, BE_H)
    # N face: unchanged (the 4 columns' tile-3 S pins + slice-0 forward metadata), exactly as s81_ph_vm_master_tiles.be()
    for port, tport, per in (('o_v', 'o_v', 1), ('o_d', 'o_d', V.DW)):
        pl.dirs[port] = ('input', NS * V.NPR * per)
        for h in range(NS):
            for b in range(V.NPR * per):
                V.put_t(pl, port, h * V.NPR * per + b, 'N', h, bg, f'{tport}[{b}]')
    for port, n in (('o_f', 4), ('o_o', 3)):
        pl.dirs[port] = ('input', NS * n)
        for h in range(NS):
            for b in range(n):
                V.put_t(pl, port, h * n + b, 'N', h, bg, f'{port}[{b}]')
    pl.dirs['f_v5'] = ('input', 1); V.put_t(pl, 'f_v5', 0, 'N', 0, bg, 'f_v[5]')
    pl.dirs['f_we5'] = ('input', 1); V.put_t(pl, 'f_we5', 0, 'N', 0, bg, 'f_we[5]')
    pl.dirs['f_m5'] = ('input', 92)
    for b in range(92):
        V.put_t(pl, 'f_m5', b, 'N', 0, bg, f'f_d[{5 * V.DW + b}]')
    xp = (6, 7, 2, 8, 9)
    for nm, tpn in (('f_vx', 'f_v'), ('f_wex', 'f_we')):
        pl.dirs[nm] = ('input', 5)
        for i, q in enumerate(xp):
            V.put_t(pl, nm, i, 'N', 0, bg, f'{tpn}[{q}]')
    pl.dirs['f_mx'] = ('input', 20)
    for i, q in enumerate(xp):
        for b in range(4):
            V.put_t(pl, 'f_mx', 4 * i + b, 'N', 0, bg, f'f_d[{q * V.DW + b}]')
    # S face v3: every response bit at the x of its slice tile's S pin
    def sp(port, bit, s, tname):
        ly, x = tp[tname]
        pl.put(port, bit, 'S', ly, s * PX + OX + x)
    for p, n in (('t_srq', 1026), ('vrq', 512), ('t_bl', 16 * 513), ('c_l0d', 604)):
        pl.dirs[p] = ('output', n)
    for s in range(NS):
        for b in range(128):
            sp('t_srq', 128 * s + b, s, f'srq_d[{b}]')
            sp('t_srq', 513 + 128 * s + b, s, f'srq_d[{128 + b}]')
            sp('vrq', 128 * s + b, s, f'vrq[{b}]')
            sp('c_l0d', 128 * s + b, s, f'c_l0d[{b}]')
            for l in range(16):
                sp('t_bl', 513 * l + 1 + 128 * s + b, s, f'bl_d[{128 * l + b}]')
        for b in range(23):
            sp('c_l0d', 512 + 23 * s + b, s, f'c_l0d[{128 + b}]')
    sp('t_srq', 512, 0, 'srq_v[0]'); sp('t_srq', 1025, 0, 'srq_v[1]')
    pl.dirs['vrv'] = ('output', 1); sp('vrv', 0, 0, 'vrv[0]')
    for l in range(16):
        sp('t_bl', 513 * l, 0, f'bl_v[{l}]')
    pl.dirs['c_l0v'] = ('output', 1); sp('c_l0v', 0, 1, 'c_l0v[0]')
    pl.dirs['c_l0r'] = ('input', 1); pl.put('c_l0r', 0, 'S', 'M5', CL0R_X)
    # status: S face of the channel between slice tiles 2 and 3 (contract v3: columns + channels fill the slab, no E strip)
    tr = [t for t in V.tracks(SLAB_W) if t[0] == 'M5' and 2 * PX + OX + TW + 8.0 < t[1] < 3 * PX + OX - 8.0]
    k = 0
    for nm, bits in (('t_err', 1), ('flt', 1), ('fvec', 32), ('max_occ', 3)):
        pl.dirs[nm] = ('output', bits)
        for b in range(bits):
            ly, x = tr[k]; k += 2
            pl.put(nm, b, 'S', ly, x)
    pl.bus('fe_flt', 16, 'input', 'E', 'M4', 20.0); pl.bus('t_p2c', 1, 'output', 'E', 'M4', 40.0)
    pl.bus('ck', 1, 'input', 'W', 'M4', BE_H / 2); pl.bus('rst', 1, 'input', 'W', 'M4', BE_H / 2 + 4.8)
    pl.bus('cks', 1, 'input', 'W', 'M4', BE_H / 2 + 9.6); pl.bus('rss', 1, 'input', 'W', 'M4', BE_H / 2 + 14.4)
    pl.emit('VM master back end v3 (BIT-SLICED, el1011-ds-vm/be): N face unchanged; S face CONTRACT v3 = every response '
            'bit at its slice tile (slice s bits in x [388.8 s + 43.2, + 302.4]); c_l0r at x %.3f; status in the slice 2 / 3 channel' % CL0R_X)


def macro_tcl():
    L = ['# el1011-ds-vm/be 2026-10-11 (tools/s81_ph/s81_ph_vm_be_v3.py): the 4 BE v3 slice tiles dsfd_vm_be_sl, tile s at',
         f'# x = s * {PX} + {OX}, y = {YB} (R0, fixed); channels: {PX - TW:.1f} um between tiles, {BE_H - YB - TH:.2f} um N, {YB} um S.',
         'set ot_blk [ord::get_db_block]', 'set ot_u [$ot_blk getDbUnitsPerMicron]',
         'foreach ot_i [$ot_blk getInsts] {',
         '  set ot_nm [$ot_i getName]',
         '  if {![regexp {g_s\\\\?\\[(\\d+)\\\\?\\]\\.u_sl$} $ot_nm -> ot_s]} { continue }',
         f'  set ot_x [expr {{round(($ot_s * {PX} + {OX}) * $ot_u)}}]',
         f'  set ot_y [expr {{round({YB} * $ot_u)}}]',
         '  $ot_i setOrient R0', '  $ot_i setLocation $ot_x $ot_y', '  $ot_i setPlacementStatus FIRM',
         '  puts "OT_BE_V3 placed $ot_nm at [expr {$ot_x / double($ot_u)}] [expr {$ot_y / double($ot_u)}]"',
         '}']
    (T.ROOT / 'physical/s81_ph_views/vm_master/place_macros_be_v3.tcl').write_text('\n'.join(L) + '\n')


def main():
    bg = V.tile_x()
    tp = tile_plan(bg)
    be_plan(bg, tp)
    macro_tcl()


if __name__ == '__main__':
    main()
