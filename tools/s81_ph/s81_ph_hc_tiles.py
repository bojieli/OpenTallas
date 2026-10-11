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


class Plan(CT.Plan):
    """CT.Plan with 1-bit ports named as scalars (`name`, not `name[0]`): every 1-bit port of the HC tiles is declared
    scalar in the RTL, and the IO placer looks pins up by the exact port-bit name (PPL-0061 otherwise)."""
    def put(self, port, bit, face, layer, coord):
        super().put(port, bit, face, layer, coord)
        if self.dirs[port][1] == 1:
            nm, *rest = self.pins[-1]
            self.pins[-1] = (port,) + tuple(rest)
NCOL = 3
CW = round(SW / NCOL, 3)         # 575.992 (= 11,999.8 x 0.048: on the placement grid)
X0 = 40.0


def widths(ng=256, gs=8, s_rd=2, s_wr=8, s_rt=4):
    ns = ng // gs
    np_ = (ns + NCOL - 1) // NCOL
    fdd = max(s_rd * 512, np_ * gs * 32)
    od = 5 + s_rd * 16 + 20 + 6 + 8 + 32 + 1
    return dict(fv=s_rd + 5, fd=od + fdd, fsw=od + s_rd * 512, rv=s_rt + 4,
                rd=s_rt + 8 * s_rt + 16 * s_rt + 8 + 512 * s_rt, ng=ng, s_rd=s_rd, s_wr=s_wr, np=np_)


def chain_ports(w):
    """(sub-tile N-face name, sub-tile S-face name, bits, root S-face name, dir at the sub-tile N face)"""
    return [('fv_in', 'fv_out', w['fv'], 'ch_fv', 'input'), ('fd_in', 'fd_out', w['fd'], 'ch_fd', 'input'),
            ('rv_out', 'rv_in', w['rv'], 'ch_rv', 'output'), ('rd_out', 'rd_in', w['rd'], 'ch_rd', 'output'),
            ('rst_in', 'rst_out', 1, 'ch_rst', 'input')]


def sub_tile(w, h, contract, half=False):
    CT.CONTRACT = contract
    pl = Plan('ot_s81_hc_ctile', CW, h)
    x = X0
    # cy_in / cy_out: the ctile always has the chunk-carry ports (used at HALF=1, tied / unused at HALF=0)
    for n_in, n_out, b, _, d in chain_ports(w) + [('cy_in', 'cy_out', 128, None, 'input')]:
        pl.bus(n_in, b, d, 'N', 'M5', x)
        x = pl.bus(n_out, b, 'output' if d == 'input' else 'input', 'S', 'M5', x)
    assert x < CW - 20, x
    y = pl.bus('tid', 8, 'input', 'W', 'M4', 60.0)
    pl.bus('last', 1, 'input', 'W', 'M4', y + 4.8)
    pl.bus('clk', 1, 'input', 'W', 'M4', h / 2)
    what = ('half octet (HALF=1: 16 hc_post + 16 norm lanes; chunk carry cy_in / cy_out N-S)' if half else
            '1 octet: 32 hc_post + 32 norm lanes')
    pl.emit(f'HC column sub-tile ({what}, resident h, gain slice) {CW} x {h}; N face '
            f'root-side chain buses, S face the same at identical x toward the next sub-tile; W face tid / last straps, clk')
    return x


def tree_exports(ns, np_):
    """exported sum-tree nodes per chain (ot_s81_hc_stree ownership)"""
    nl = 4 * ns
    lt = nl.bit_length() - 1
    L = [np_, max(ns - 2 * np_, 0), np_]
    B = [0, np_, np_ + L[1]]
    def lev(n): return lt - (n.bit_length() - 1)
    def owner(n):
        k = lev(n); sz = 1 << k; s0 = ((n << k) - nl) % ns
        if sz <= ns:
            for c in range(3):
                if L[c] and B[c] <= s0 and s0 + sz <= B[c] + L[c]: return c
        return 3
    def expd(n, c): return owner(n) == c and c != 3 and (n == 1 or owner(n // 2) != c)
    return [sum(expd(n, c) for n in range(1, 2 * nl)) for c in range(3)], L


def seam_ports(w, ne):
    """outer column root <-> combine tile seam (outer-root view: dir)"""
    return [('s_fv', 'w', w['fv'], 'input'), ('s_fd', 'w', w['fsw'], 'input'), ('s_w', 'w', 4 * 543, 'input'),
            ('s_rv', 'w', w['rv'], 'output'), ('s_rd', 'w', w['rd'], 'output'), ('s_ex', 'w', max(ne, 1) * 32, 'output'),
            ('s_flt', 'w', 1, 'output')]


def pin_seam(w, ys1):
    """centre pin tile <-> combine tile seam (pin-tile S-face names, combine N-face names, bits, dir at the pin tile)"""
    s_rd = w['s_rd']
    return [('n_cmd_v', 1, 'output'), ('n_cmd_d', 84, 'output'), ('n_done_v', 1, 'input'), ('n_done_tag', 8, 'input'),
            ('n_inp', 1, 'output'), ('n_rq_v', s_rd, 'input'), ('n_rq_row', s_rd * 14, 'input'), ('n_rs_v', s_rd, 'output'),
            ('n_rs_d', s_rd * 512, 'output'), ('n_flt', 1, 'input'), ('n_online', 1, 'input'), ('n_fcode', 4, 'input'),
            ('n_yacc', 1, 'output'), ('n_y', ys1, 'output'), ('n_ypop', 1, 'input')]


def flip(d):
    return 'output' if d == 'input' else 'input'


def root_tiles(w, hr, hc, contract):
    """outer column roots (west C 0, east C 2: CW x (hr + hc)), centre pin tile (CW x hr), combine tile (CW x hc)"""
    CT.CONTRACT = contract
    ns, np_ = w['ng'] // 8, w['np']
    ne, L = tree_exports(ns, np_)
    ys = [l * 8 * 32 for l in L]
    hro = hr + hc
    seams = {}
    for c, cn, inner in ((0, contract, 'E'), (2, contract + '_e', 'W')):     # one module, C 0 / 2 (--param C=2)
        CT.CONTRACT = cn
        m = 'ot_s81_hc_croot'
        pl = Plan(m, CW, hro)
        x = X0
        for n, b, d in (('y_s', ys[c], 'input'), ('wq_v', 4, 'output'), ('wq_row', 56, 'output'),
                        ('wq_mask', 64, 'output'), ('wq_d', 2048, 'output')):
            x = pl.bus(n, b, d, 'N', 'M5', x)
        assert x < CW - 10, (m, x)
        y = 20.0
        for n, _, b, d in seam_ports(w, ne[c]):
            y = pl.bus(n, b, d, inner, 'M4', y)
        assert y < hc - 10, (m, y)
        seams[c] = y
        pl.bus('yacc', 1, 'input', inner, 'M4', hc + 100.0)
        x = X0
        for n_in, _, b, rn, d in chain_ports(w):
            x = pl.bus(rn.replace('ch_', 'ch_'), b, 'output' if d == 'input' else 'input', 'S', 'M5', x)
        outer = 'W' if inner == 'E' else 'E'
        pl.bus('sk', 1, 'input', outer, 'M4', hro / 2); pl.bus('srs', 1, 'input', outer, 'M4', hro / 2 + 4.8)
        pl.emit(f'HC outer column root (chain {c}) {CW} x {hro}: N face y slice + VM write slots {"0..3" if c == 0 else "4..7"}; '
                f'{inner} face: combine seam (lower {hc}) + y accept (upper); S face chain {c} ports at the sub-tile x')
    # combine tile
    CT.CONTRACT = contract
    pl = Plan('ot_s81_hc_comb', CW, hc)
    for face, pre, c in (('W', 'w_', 0), ('E', 'e_', 2)):
        y = 20.0
        for n, _, b, d in seam_ports(w, ne[c]):
            y = pl.bus(pre + n[2:], b, flip(d), face, 'M4', y)
    x = X0
    for n, b, d in pin_seam(w, max(ys[1], 1)):
        x = pl.bus(n, b, flip(d), 'N', 'M5', x)
    for i, n in enumerate(('cck', 'crs', 'sk', 'srs')):
        x = pl.bus(n, 1, 'input', 'N', 'M5', x + 2.0)
    assert x < CW - 10, x
    x = X0
    for n_in, _, b, rn, d in chain_ports(w):
        x = pl.bus(rn, b, 'output' if d == 'input' else 'input', 'S', 'M5', x)
    pl.emit(f'HC combine tile {CW} x {hc}: W / E faces the outer roots\' seams (identical y), N face the centre pin tile '
            f'seam, S face the centre chain ports at the sub-tile x')
    # centre pin tile
    pl = Plan('ot_s81_hc_cpin', CW, hr)
    x = X0
    for n, b, d in pin_seam(w, max(ys[1], 1)):
        x = pl.bus(n, b, d, 'S', 'M5', x)
    x = X0
    sr = w['s_rd']
    for n, b, d in (('c_cmd_v', 1, 'input'), ('c_cmd_d', 84, 'input'), ('c_done_v', 1, 'output'), ('c_done_tag', 8, 'output'),
                    ('inp', 1, 'input'), ('rq_v', sr, 'output'), ('rq_row', sr * 14, 'output'), ('rs_v', sr, 'input'),
                    ('rs_d', sr * 512, 'input'), ('flt', 1, 'output'), ('online', 1, 'output'), ('fcode', 4, 'output'),
                    ('y_v', 1, 'input'), ('y_rdy', 1, 'output'), ('y_s', max(ys[1], 1), 'input')):
        x = pl.bus(n, b, d, 'N', 'M5', x)
    for n in ('cck', 'crs', 'sk', 'srs'):
        x = pl.bus(n, 1, 'input', 'N', 'M5', x + 2.0)
    assert x < CW - 10, x
    pl.bus('yacc_w', 1, 'output', 'W', 'M4', 100.0)
    pl.bus('yacc_e', 1, 'output', 'E', 'M4', 100.0)
    pl.emit(f'HC centre pin tile {CW} x {hr}: N face the centre third of the slab pins (adapter command / done, VM reads, '
            f'status, y handshake + centre y slice), S face the combine seam at identical x, W / E the y accept to the outer roots')
    return seams


def split_roots(w, hy, hr, contract):
    """structural variant: each outer column root split N-S into ot_s81_hc_crooty (CW x hy: y slice + VM write pins,
    the y FIFO) over ot_s81_hc_crootr (CW x hr: chain root beside the combine tile)"""
    ns, np_ = w['ng'] // 8, w['np']
    ne, L = tree_exports(ns, np_)
    ys = [l * 8 * 32 for l in L]
    for c, cn, inner in ((0, contract, 'E'), (2, contract + '_e', 'W')):
        CT.CONTRACT = cn
        outer = 'W' if inner == 'E' else 'E'
        py = [('p_req', 1, 'input'), ('p_w', 4 * 543, 'input'), ('p_y', ys[c], 'output'), ('p_flt', 1, 'output')]
        pl = Plan('ot_s81_hc_crooty', CW, hy)
        x = X0
        for n, b, d in (('y_s', ys[c], 'input'), ('wq_v', 4, 'output'), ('wq_row', 56, 'output'),
                        ('wq_mask', 64, 'output'), ('wq_d', 2048, 'output')):
            x = pl.bus(n, b, d, 'N', 'M5', x)
        assert x < CW - 10, x
        x = X0
        for n, b, d in py:
            x = pl.bus(n, b, d, 'S', 'M5', x)
        assert x < CW - 10, x
        pl.bus('yacc', 1, 'input', inner, 'M4', 100.0)
        pl.bus('sk', 1, 'input', outer, 'M4', hy / 2); pl.bus('srs', 1, 'input', outer, 'M4', hy / 2 + 4.8)
        pl.emit(f'HC split column root, pin / y FIFO half (chain {c}) {CW} x {hy}: N face y slice + VM write slots; '
                f'S face the chain-root half below at identical x; {inner} face the y accept')
        pl = Plan('ot_s81_hc_crootr', CW, hr)
        x = X0
        for n, b, d in py:
            x = pl.bus(n, b, flip(d), 'N', 'M5', x)
        y = 20.0
        for n, _, b, d in seam_ports(w, ne[c]):
            y = pl.bus(n, b, d, inner, 'M4', y)
        assert y < hr - 10, y
        x = X0
        for n_in, _, b, rn, d in chain_ports(w):
            x = pl.bus(rn, b, 'output' if d == 'input' else 'input', 'S', 'M5', x)
        pl.bus('sk', 1, 'input', outer, 'M4', hr / 2); pl.bus('srs', 1, 'input', outer, 'M4', hr / 2 + 4.8)
        pl.emit(f'HC split column root, chain-root half (chain {c}) {CW} x {hr}: N face the pin half, {inner} face the '
                f'combine seam (identical y), S face chain {c} ports at the sub-tile x')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--sub-h', type=float, default=800.0)
    ap.add_argument('--root-h', type=float, default=200.0, help='centre pin tile height')
    ap.add_argument('--comb-h', type=float, default=640.0, help='combine tile height (outer roots: root-h + comb-h)')
    ap.add_argument('--contract', default='contract_hcc')
    ap.add_argument('--roots', action='store_true', help='also the root-side tiles')
    ap.add_argument('--half', action='store_true', help='the sub-tile is a half octet (HALF=1)')
    ap.add_argument('--split-roots', action='store_true', help='the split column roots (crooty 200 / crootr 640)')
    a = ap.parse_args()
    w = widths()
    xs = sub_tile(w, a.sub_h, a.contract, a.half)
    ms = ['ot_s81_hc_ctile']
    if a.split_roots:
        split_roots(w, a.root_h, a.comb_h, a.contract)
        ms += ['ot_s81_hc_crooty', 'ot_s81_hc_crootr', '_e/ot_s81_hc_crooty', '_e/ot_s81_hc_crootr']
    if a.roots:
        print('seam extents', root_tiles(w, a.root_h, a.comb_h, a.contract))
        ms += ['ot_s81_hc_croot', 'ot_s81_hc_comb', 'ot_s81_hc_cpin', '_e/ot_s81_hc_croot']
    for m in ms:
        f = CT.ROOT / 'physical/s81_ph_views/ports' / (a.contract + m if m.startswith('_') else f'{a.contract}/{m}') / 'io_place.tcl'
        f.write_text(f.read_text().replace('tools/s81_ph/s81_ph_coll_tiles.py)', 'tools/s81_ph/s81_ph_hc_tiles.py via Plan)'))
    print('ok sub-tile N/S span to', round(xs, 1))


if __name__ == '__main__':
    main()
