#!/usr/bin/env python3
"""s81-suhc-hier-1011: pin plan of the HC row-group tile ot_s81_hc_tile (hierarchical HC slab ot_s81_hc_hier).

The tile column runs along the HC slab (1,727.976 um wide; hc_s 8,184 + hc_n 2,415 um tall, contracts_1011/
su_hc.layer1suhc.json): the root at the VM / collective pin end, then tiles 0 .. KT-1.  Every tile's N face carries
the root-side buses (forward bus in fv_in / fd_in, return packet out rv_out / rd_out, rst_in) and its S face the same
buses toward the next tile at IDENTICAL x (fv_out / fd_out, rv_in / rd_in, rst_out), so a hop is a straight vertical
run through the >= 20 um seam channel, where the slab's RS relay registers sit.  The y slice (G x 32 b) and the tile
index strap enter on the W face (y relays run in the W channel beside the column); the clock on the W face.
Generator conventions (tools/s81_ph/s81_ph_coll_tiles.py Plan: M4 horizontal / M5 vertical, pitch 0.048, step 2).
Defaults: NG 256, KT 8 (G 32), S_RD 2, S_WR 8 -> fd 1,120 b, rd 5,336 b.

    python3 tools/s81_ph/s81_ph_hc_tiles.py [--h 1200] [--contract contract_hch]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s81_ph_coll_tiles as CT   # noqa: E402

W = 1727.976


def widths(ng=256, kt=8, s_rd=2, s_wr=8):
    fdw = 5 + s_rd * 16 + s_rd * 512 + 12 + 6 + 8 + 32 + 1
    rdw = 2 * s_wr + 8 * s_wr + 16 * s_wr + 512 * s_wr + 8 + kt * 128
    g = ng // kt
    nu = 4 * g // min(g, 32)
    return dict(fv=s_rd + 5, fd=fdw, rv=s_wr + 4, rd=rdw, y=g * 32, pm=nu * 32)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--h', type=float, default=1200.0)
    ap.add_argument('--contract', default='contract_hch')
    ap.add_argument('--kt', type=int, default=8)
    a = ap.parse_args()
    CT.CONTRACT = a.contract
    w = widths(kt=a.kt)
    pl = CT.Plan('ot_s81_hc_tile', W, a.h)
    x = 60.0
    for i_n, o_n, b, di in (('fv_in', 'fv_out', w['fv'], 'f'), ('fd_in', 'fd_out', w['fd'], 'f'),
                            ('rv_out', 'rv_in', w['rv'], 'r'), ('rd_out', 'rd_in', w['rd'], 'r'),
                            ('rst_in', 'rst_out', 1, 'f'), ('pm_in_n', 'pm_out_s', w['pm'], 'f'),
                            ('pm_out_n', 'pm_in_s', w['pm'], 'r')):
        # N face = root side; the forward buses come in there, the return buses go out there
        pl.bus(i_n, b, 'input' if di == 'f' else 'output', 'N', 'M5', x)
        x = pl.bus(o_n, b, 'output' if di == 'f' else 'input', 'S', 'M5', x)
    assert x < W - 60, x
    y = 60.0
    y = pl.bus('y_in', w['y'], 'input', 'W', 'M4', y)
    y = pl.bus('tid', 8, 'input', 'W', 'M4', y + 4.8)
    pl.bus('clk', 1, 'input', 'W', 'M4', a.h / 2)
    assert y < a.h / 2 - 5
    g = 256 // a.kt
    pl.emit(f'HC row-group tile (KT {a.kt}, G {g} groups: {4 * g} hc_post lanes + {4 * g} norm lanes, resident h, gain slice); N face root-side '
            f'buses, S face the same at identical x toward the next tile; W face y slice + tid strap + clk; {W} x {a.h}')
    print('ok', len(pl.pins), 'pins; N/S span to x', round(x, 1))


if __name__ == '__main__':
    main()
