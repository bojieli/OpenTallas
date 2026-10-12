#!/usr/bin/env python3
"""CLAUDE s81die-1011/ctrl svch: pin plans of the hierarchical scan-service tiles dsfd_svc_quad (one contract per
quadrant position, contract_svchq<g>: the port widths and faces depend on QID) and dsfd_svc_idx (contract_svch).

dsfd_svc_quad  2,125.008 x 755.976 um (composition region of quadrant g).  S face: the 8 PC tiles' N-face pins
               (u_pc[8g + i] at local x = i * 265.584, abutted).  The other ports leave by the face toward their
               partner: score lanes toward the neighbouring quadrant (W / E), everything else (q, od / a0, index-reader
               A lanes, home lanes) on the N face to the relay stations in the slab's upper band, overflowing to W / E.
               All pins M5 (N / S) / M4 (W / E), every other track (0.096 um).
dsfd_svc_idx   1,500 x 300 um in the upper band: S face A lanes (32 PCs), N face q / x / a1 / ck / rst.
Writes physical/s81_ph_views/ports/contract_svchq{0..3}/dsfd_svc_quad/ and contract_svch/dsfd_svc_idx/."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s81_ph_coll_tiles as T   # noqa: E402
from s81_ph_coll_tiles import Plan, ROOT, P   # noqa: E402
import json

QW, QH = 2125.008, 755.976
PITCH = 265.584
NG = 13
EDGE = 3.0


def quad_ports(g):
    home = g == 2
    HB, HQ = (24, 3) if home else (1, 1)
    OB, OGQ, OGR, OGW, OWB, OFB, OPV = (1, 1, 1, 1, 1, 1, 1) if home else (8, 344, 276, NG, 4228, 607, 513)
    sow = 2132 if g != 2 else 1
    saw = 2132 if g in (1, 2) else 1
    sbw = 2132 if g == 2 else 1
    hw = 'W' if g == 3 else 'E'          # own lanes toward the home (quadrant 2)
    so_f = 'W' if g == 3 else 'E'
    L = [('q', 515, 'input', 'N'), ('od_v', 1, 'output', 'N'), ('od_d', 512, 'output', 'N'), ('od_r', 1, 'input', 'N'),
         ('a0_v', 1, 'output', 'N'), ('a0_d', 512, 'output', 'N'), ('a0_r', 1, 'input', 'N'), ('fo', 1, 'output', 'N'),
         ('aq_v', 8, 'input', 'N'), ('aq_d', 400, 'input', 'N'), ('aq_c', 8, 'output', 'N'),
         ('ar_v', 8, 'output', 'N'), ('ar_d', 8 * 276, 'output', 'N'), ('ar_c', 8, 'input', 'N'),
         ('bq_v', OB, 'input', hw), ('bq_d', OB * 46, 'input', hw), ('bq_c', OB, 'output', hw),
         ('br_v', OB, 'output', hw), ('br_d', OB * 272, 'output', hw), ('br_c', OB, 'input', hw),
         ('gq_v', 1, 'input', hw), ('gq_d', OGQ, 'input', hw), ('gq_c', 1, 'output', hw),
         ('gr_v', 1, 'output', hw), ('gr_d', OGR, 'output', hw), ('gr_c', 1, 'input', hw), ('gwd', OGW, 'output', hw),
         ('wb_v', 1, 'input', 'N'), ('wb_d', OWB, 'input', 'N'), ('wb_c', 1, 'output', 'N'),
         ('fb_v', 1, 'input', hw), ('fb_d', OFB, 'input', hw),
         ('so_v', 1, 'output', so_f), ('so_d', sow, 'output', so_f), ('so_c', 1, 'input', so_f),
         ('sa_v', 1, 'input', 'W'), ('sa_d', saw, 'input', 'W'), ('sa_c', 1, 'output', 'W'),
         ('sb_v', 1, 'input', 'E'), ('sb_d', sbw, 'input', 'E'), ('sb_c', 1, 'output', 'E'),
         ('po_v', 1, 'output', hw), ('po_d', OPV, 'output', hw), ('po_c', 1, 'input', hw)]
    hf = 'N'
    L += [('h_bq_v', HB, 'output', hf), ('h_bq_d', HB * 46, 'output', hf), ('h_bq_c', HB, 'input', hf),
          ('h_br_v', HB, 'input', hf), ('h_br_d', HB * 272, 'input', hf), ('h_br_c', HB, 'output', hf),
          ('h_gq_v', HQ, 'output', hf), ('h_gq_d', HQ * 344, 'output', hf), ('h_gq_c', HQ, 'input', hf),
          ('h_gr_v', HQ, 'input', hf), ('h_gr_d', HQ * 276, 'input', hf), ('h_gr_c', HQ, 'output', hf),
          ('h_gwd', HQ * NG, 'input', hf),
          ('h_wb_v', HQ, 'output', hf), ('h_wb_d', HQ * 4228, 'output', hf), ('h_wb_c', HQ, 'input', hf),
          ('h_fb_v', HQ, 'output', hf), ('h_fb_d', HQ * 607, 'output', hf),
          ('h_pv_v', HQ, 'input', hf), ('h_pv_d', HQ * 513, 'input', hf), ('h_pv_c', HQ, 'output', hf),
          ('h_flt', HQ, 'input', hf),
          ('h_hw_v', 1, 'input', 'N'), ('h_hw_d', 291 if home else 1, 'input', 'N'), ('h_hc', 9 if home else 1, 'output', 'N')]
    return L


def quad(g):
    T.CONTRACT = f'contract_svchq{g}'
    pc = json.loads((ROOT / 'physical/s81_ph_views/ports/contract/dsfd_svc_pc/ports.json').read_text())['ports']
    pl = Plan('dsfd_svc_quad', QW, QH)
    for nm, w in (('qrq', 341), ('qrk', 1), ('qwd', 1), ('qrv', 1), ('qr_data', 256), ('qr_tag', 17), ('qr_beat', 4)):
        d = 'output' if nm == 'qrq' else 'input'
        pl.dirs[nm] = (d, 8 * w)
        for pin in pc[nm]['pins']:
            b = int(pin[0].split('[')[1][:-1])
            for i in range(8):
                pl.put(nm, w * i + b, 'S', 'M5', i * PITCH + (pin[2] + pin[4]) / 2)
    pl.bus('ck', 1, 'input', 'N', 'M5', QW / 2)
    pl.bus('rst', 1, 'input', 'N', 'M5', QW / 2 + 4 * P)
    segs = [('N', 'M5', EDGE, QW / 2 - 2 * P), ('N', 'M5', QW / 2 + 8 * P, QW - EDGE),
            ('W', 'M4', EDGE, QH - EDGE), ('E', 'M4', EDGE, QH - EDGE)]
    cur = [s[2] for s in segs]

    def place(port, bits, d, pref):
        pl.dirs[port] = (d, bits)
        idx = [i for i, s in enumerate(segs) if s[0] == pref] + [i for i, s in enumerate(segs) if s[0] != pref]
        b = 0
        for i in idx:
            face, layer, lo, hi = segs[i]
            while b < bits and cur[i] + 2 * P <= hi:
                pl.put(port, b, face, layer, cur[i]); cur[i] += 2 * P; b += 1
            if b == bits:
                cur[i] += 2 * P
                return
        raise SystemExit(f'dsfd_svc_quad q{g}: out of pin room at {port} ({b}/{bits})')
    for port, bits, d, pref in quad_ports(g):
        place(port, bits, d, pref)
    used = [(s[0], round(cur[i] - s[2], 1), round(s[3] - s[2], 1)) for i, s in enumerate(segs)]
    pl.emit(f'svch quadrant {g} (tools/s81_ph/s81_ph_svch_tiles.py): S = PC tiles, score lanes W/E, rest N; used {used}')
    print(g, len(pl.pins), used)


def idx():
    T.CONTRACT = 'contract_svch'
    W, H = 1500.0, 300.0
    pl = Plan('dsfd_svc_idx', W, H)
    pl.bus('ck', 1, 'input', 'N', 'M5', W / 2)
    pl.bus('rst', 1, 'input', 'N', 'M5', W / 2 + 4 * P)
    y = EDGE
    for nm, b, d in (('q', 515, 'input'), ('a1_v', 1, 'output'), ('a1_d', 512, 'output'), ('a1_r', 1, 'input'),
                     ('x_v', 1, 'output'), ('x_d', 512, 'output'), ('x_r', 1, 'input'), ('fo', 1, 'output')):
        y = pl.bus(nm, b, d, 'E', 'M4', y)
    assert y < H, y
    x = EDGE
    for nm, b, d in (('aq_v', 32, 'output'), ('aq_c', 32, 'input'), ('ar_v', 32, 'input'), ('ar_c', 32, 'output'),
                     ('aq_d', 32 * 50, 'output'), ('ar_d', 32 * 276, 'input')):
        n = 0
        pl.dirs[nm] = (d, b)
        while n < b:
            face = 'S' if x < W - EDGE else 'N'
            xx = x if face == 'S' else x - (W - 2 * EDGE)
            pl.put(nm, n, face, 'M5', xx)
            x += 2 * P; n += 1
        x += 2 * P
    pl.emit('svch index reader tile (tools/s81_ph/s81_ph_svch_tiles.py): A lanes S (then N), q / x / a1 E')
    print('idx', len(pl.pins))


def pcs():
    """dsfd_svch_pcs 243.0 x 64.8 at u_pc's x: S face = the PC tile's N-face pins (abutted), N face = A / B / G lanes"""
    T.CONTRACT = 'contract_svch'
    W, H = 243.0, 64.8
    pc = json.loads((ROOT / 'physical/s81_ph_views/ports/contract/dsfd_svc_pc/ports.json').read_text())['ports']
    pl = Plan('dsfd_svch_pcs', W, H)
    for nm, w in (('qrq', 341), ('qrk', 1), ('qwd', 1), ('qrv', 1), ('qr_data', 256), ('qr_tag', 17), ('qr_beat', 4)):
        pl.dirs[nm] = ('output' if nm == 'qrq' else 'input', w)
        for pin in pc[nm]['pins']:
            pl.put(nm, int(pin[0].split('[')[1][:-1]), 'S', 'M5', (pin[2] + pin[4]) / 2)
    x = EDGE
    for nm, b, d in (('ck', 1, 'input'), ('rst', 1, 'input'), ('fo', 1, 'output'),
                     ('aq_v', 1, 'input'), ('aq_d', 50, 'input'), ('aq_c', 1, 'output'),
                     ('ar_v', 1, 'output'), ('ar_d', 276, 'output'), ('ar_c', 1, 'input'),
                     ('bq_v', 1, 'input'), ('bq_d', 46, 'input'), ('bq_c', 1, 'output'),
                     ('br_v', 1, 'output'), ('br_d', 272, 'output'), ('br_c', 1, 'input'),
                     ('gq_v', 1, 'input'), ('gq_d', 344, 'input'), ('gq_c', 1, 'output'),
                     ('gr_v', 1, 'output'), ('gr_d', 276, 'output'), ('gr_c', 1, 'input'), ('gwd', NG, 'output')):
        x = pl.bus(nm, b, d, 'N', 'M5', x)
    assert x < W - EDGE, x
    pl.emit('svch per-PC service slice (tools/s81_ph/s81_ph_svch_tiles.py): S = u_pc N face (abutted), N = lanes')
    print('pcs', len(pl.pins), round(x, 1))


def rly():
    """dsfd_svch_rly station, the widest seam (window-beat lane: W 4228, V 1, NR 1): W face in, E face out"""
    T.CONTRACT = 'contract_svch'
    W, H = 64.8, 432.0
    pl = Plan('dsfd_svch_rly', W, H)
    pl.bus('ck', 1, 'input', 'N', 'M5', W / 2)
    pl.bus('rst', 1, 'input', 'N', 'M5', W / 2 + 4 * P)
    y = EDGE
    for nm, b, d, f in (('i_v', 1, 'input', 'W'), ('i_d', 4228, 'input', 'W')):
        y = pl.bus(nm, b, d, f, 'M4', y, step=2)
    y2 = EDGE
    for nm, b, d, f in (('o_v', 1, 'output', 'E'), ('o_d', 4228, 'output', 'E')):
        y2 = pl.bus(nm, b, d, f, 'M4', y2, step=2)
    assert y < H - EDGE and y2 < H - EDGE, (y, y2)
    pl.emit('svch relay station, window-beat seam (W 4228): W face in, E face out')
    print('rly', len(pl.pins), round(y, 1))


if __name__ == '__main__':
    for g in range(4):
        quad(g)
    idx()
    pcs()
    rly()
