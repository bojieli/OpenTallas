#!/usr/bin/env python3
"""s81-suhc-hier-1011: pin plans of the hierarchical S81 HC slab (dsfd_sp_hc HIER=1).

The slab (1,727.976 um wide, contracts_1011/su_hc.layer1suhc.json) = the root tile ot_s81_hc_rtile (full width, at
the slab end next to the c_cmd / VM / y pins) above NCOL = 3 column chains of identical sub-tiles ot_s81_hc_ctile
(575.992 um wide, abutted N-S).  A sub-tile's N face carries the root-side buses (forward in fv_in / fd_in, return
out rv_out / rd_out, rst_in) and its S face the same buses toward the next sub-tile at IDENTICAL x (fv_out / fd_out,
rv_in / rd_in, rst_out): every hop is a straight abutment.  The root tile's S face carries chain c's ports (ch_fv /
ch_fd / ch_rv / ch_rd / ch_rst slices) at exactly the x of a sub-tile N face shifted by c x 575.992; its N face the
die-side pins (y, VM slots, adapter command / done, status); clocks and straps on the W face.
Generator conventions (tools/s81_ph/s81_ph_coll_tiles.py Plan: M4 horizontal / M5 vertical, pitch 0.048, step 2 =
10.4 b/um, under the 12 b/um/layer floorplan lint).  Defaults NG 256, GS 8, S_RD 2, S_WR 8, S_RT 4.

    python3 tools/s81_ph/s81_ph_hc_tiles.py [--sub-h 800] [--root-h 600]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s81_ph_coll_tiles as CT   # noqa: E402

SW = 1727.976
NCOL = 3
CW = round(SW / NCOL, 3)         # 575.992 (= 11,999.8 x 0.048: on the placement grid)
X0 = 40.0


def widths(ng=256, gs=8, s_rd=2, s_wr=8, s_rt=4):
    ns = ng // gs
    np_ = (ns + NCOL - 1) // NCOL
    fdd = max(s_rd * 512, np_ * gs * 32)
    return dict(fv=s_rd + 5, fd=5 + s_rd * 16 + 12 + 6 + 8 + 32 + 1 + fdd, rv=s_rt + 4,
                rd=s_rt + 8 * s_rt + 16 * s_rt + 8 + 512 * s_rt, ng=ng, s_rd=s_rd, s_wr=s_wr)


def chain_ports(w):
    """(sub-tile N-face name, sub-tile S-face name, bits, root S-face name, dir at the sub-tile N face)"""
    return [('fv_in', 'fv_out', w['fv'], 'ch_fv', 'input'), ('fd_in', 'fd_out', w['fd'], 'ch_fd', 'input'),
            ('rv_out', 'rv_in', w['rv'], 'ch_rv', 'output'), ('rd_out', 'rd_in', w['rd'], 'ch_rd', 'output'),
            ('rst_in', 'rst_out', 1, 'ch_rst', 'input')]


def sub_tile(w, h, contract):
    CT.CONTRACT = contract
    pl = CT.Plan('ot_s81_hc_ctile', CW, h)
    x = X0
    for n_in, n_out, b, _, d in chain_ports(w):
        pl.bus(n_in, b, d, 'N', 'M5', x)
        x = pl.bus(n_out, b, 'output' if d == 'input' else 'input', 'S', 'M5', x)
    assert x < CW - 20, x
    y = pl.bus('tid', 8, 'input', 'W', 'M4', 60.0)
    pl.bus('last', 1, 'input', 'W', 'M4', y + 4.8)
    pl.bus('clk', 1, 'input', 'W', 'M4', h / 2)
    pl.emit(f'HC column sub-tile (1 octet: 32 hc_post + 32 norm lanes, resident h, gain slice) {CW} x {h}; N face '
            f'root-side chain buses, S face the same at identical x toward the next sub-tile; W face tid / last straps, clk')
    return x


def root_tile(w, h, contract):
    CT.CONTRACT = contract
    pl = CT.Plan('ot_s81_hc_rtile', SW, h)
    # S face: chain c's ports at the sub-tile N-face x + c * CW
    for c in range(NCOL):
        x = X0 + c * CW
        for n_in, _, b, rn, d in chain_ports(w):
            x = pl.bus(rn, b * NCOL, 'output' if d == 'input' else 'input', 'S', 'M5', x, lo=c * b, n=b)
    # N face: die-side pins
    ng, s_rd, s_wr = w['ng'], w['s_rd'], w['s_wr']
    x = X0
    for n, b, d in (('c_cmd_v', 1, 'input'), ('c_cmd_d', 84, 'input'), ('c_done_v', 1, 'output'),
                    ('c_done_tag', 8, 'output'), ('inp', 1, 'input'), ('flt', 1, 'output'), ('online', 1, 'output'),
                    ('fcode', 4, 'output'), ('y_v', 1, 'input'), ('y_rdy', 1, 'output'), ('y_d', ng * 32, 'input'),
                    ('rq_v', s_rd, 'output'), ('rq_row', s_rd * 14, 'output'), ('rs_v', s_rd, 'input'),
                    ('rs_d', s_rd * 512, 'input'), ('wq_v', s_wr, 'output'), ('wq_row', s_wr * 14, 'output'),
                    ('wq_mask', s_wr * 16, 'output'), ('wq_d', s_wr * 512, 'output')):
        x = pl.bus(n, b, d, 'N', 'M5', x)
    assert x < SW - 20, x
    for i, n in enumerate(('cck', 'crs', 'sk', 'srs')):
        pl.bus(n, 1, 'input', 'W', 'M4', h / 2 + 4.8 * (i - 2))
    pl.emit(f'HC root tile (adapter, pin flops, y skid, root sequencer / VM slots / norm tail / act-quant, chain relays) '
            f'{SW} x {h}; S face chain c ports at the sub-tile N-face x + c x {CW}; N face die-side pins; W face clocks')
    return x


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--sub-h', type=float, default=800.0)
    ap.add_argument('--root-h', type=float, default=600.0)
    ap.add_argument('--contract', default='contract_hcc')
    a = ap.parse_args()
    w = widths()
    xs = sub_tile(w, a.sub_h, a.contract)
    xr = root_tile(w, a.root_h, a.contract)
    for m in ('ot_s81_hc_ctile', 'ot_s81_hc_rtile'):
        f = CT.ROOT / 'physical/s81_ph_views/ports' / a.contract / m / 'io_place.tcl'
        f.write_text(f.read_text().replace('tools/s81_ph/s81_ph_coll_tiles.py)', 'tools/s81_ph/s81_ph_hc_tiles.py via Plan)'))
    print('ok sub-tile N/S span to', round(xs, 1), 'root N span to', round(xr, 1))


if __name__ == '__main__':
    main()
