#!/usr/bin/env python3
"""DS-ROM microarchitecture recovery (2026-10-04): the S81 full-die physical check re-run with the adopted levers.

The S81 full-die method (tools/dsrom_s81_fulldie.py, results/rtl/dsrom_s81_fulldie_20261004) is reused unchanged:
this tool imports it, builds a recovery variant of its floorplan, and writes the same OpenROAD cases (a: real
abstracts, legality, on-track assert, pin access; b: bundled k = 16 GRT with the per-layer 4 x 4 GCell windows; c:
PSM IR on a window).  The S81 tool and its records stay byte-identical.

Variants (--die):
  head    the recovery head die.  The S81 head die (1 of 12) carried 1,682 content pairs: embed + lm-head + norm +
          the 7.93 GB DSpark drafter, 211 of them lm-head pairs with the REJECTED NV5 draft extension.  Recovery:
          the drafter moves to the DP1-EP5 draft dies (levers/draft.json) and the lm-head moves to the head lever's
          element (levers/head.json): ot_dsrom_head_elem (2 x ot_rom_4096x274_m8, 16 BF16 multipliers a macro) in
          bundles of 4 A (K 0..4095, 32 rows) + 1 B (K 4096..5119, 128 rows) elements.  Per die: the 1/12 share of
          the 2,526 non-lm-head global pairs (embed + norm, 211 pairs at the layer die's BF share) and 85 bundles
          (1,010 bundles = 4 ranks x 252.5, over 12 dies = 84.2, rounded up) = 425 head elements, one bundle at
          the bottom of each of 85 frames (3 slots: A0 A1 A2 / A3 B), its compare node in the frame's node strip.
          Die-level nets of a bundle: the skewed 256-bit xa (to the 4 A) and xb (to the B) from the region FIFO,
          20 bits of go/row0/clk/rst, B's 33-bit root stream to the four A (JOIN), each A's 83-bit argmax result
          (done, row, bits, key, fault) to the bundle compare node, the bundle's 82-bit result to the region FIFO
          (compared there) and up the tier trunk to the gather as one 82-bit running max a tier (the rank compare
          levels).  xa / xb share the trunk's two lane-x channels (the head die streams one hidden vector).
  layer   the S81 layer die + one ot_hdc_select_tree (levers/router.json) as a spine slab between the SU (south)
          and the gather: 31,944 um2 of cells at the 0.5 logic density of the head-die sizing = 63,889 um2.  The
          router scores (64 lanes x 32 bits + 64 lane-valid + last = 2,113 bits a beat) come from the gather (the
          return roots land there), the 6 selected ids (64 bits) go to the SU.
  draft   the layer variant + the DP1-EP5 primary draft die's 15 extra board links (levers/draft.json: a star of
          15 replica links per primary die) at the S81 endpoint footprint (the real ot_pdie_serdes LEF, 1,024-bit
          bus from the collective through a hub FIFO slot and channel waypoints, exactly as the S81 stage links).
          Seven more SerDes in each edge link column (11 macros a side) and one in the SW corner: the S81 column
          holds at most 10 SerDes + the UCIe in the 26 mm edge.  Until hop_closed lands the endpoint is the S81
          footprint; the endpoint's own logic is not priced here.

Modes:  plan | check | real --work W | grt --work W --k K --iters N [--empty] | ir --work W --window NAME | record
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import dsrom_s81_fulldie as S  # noqa: E402
import qwen_rom_fulldie as Q  # noqa: E402

OUT = 'results/rtl/dsrom_recovery_20261004/physcost'
HEAD_PHYS = 'results/physical_abi3/asap7/chip/dsrom_recovery_head_20261004/r4_{}/physical.json'
HEAD_LEF = OUT + '/abstracts/ot_dsrom_head_elem_{}.lef.gz'     # write_abstract_lef of the reproduced r4 routes
ROUTER = 'results/rtl/dsrom_recovery_20261004/router/screen.json'
DRAFT = 'results/rtl/dsrom_recovery_20261004/levers/draft.json'

GX, GY, SHAVE = S.GX, S.GY, S.SHAVE
# ---- head
GLOBAL_PAIRS, LM_HEAD_PAIRS, HEAD_DIES = 5051, 2525, 12
RANKS, BUNDLES_PER_RANK = 4, 252.5
BUNDLES = math.ceil(RANKS * BUNDLES_PER_RANK / HEAD_DIES)          # 85 a die
OTHER_PAIRS = math.ceil((GLOBAL_PAIRS - LM_HEAD_PAIRS) / HEAD_DIES)  # 211 embed + norm pairs a die
HX, HK, HB, HRES, HROOT = 256, 20, 33, 83, 82
HCMP = (86.4, 77.76)                                               # bundle compare node (2 levels of 81-bit compare)
# ---- router
SEL_DENSITY = 0.5
SEL_IN, SEL_OUT = 64 * 32 + 64 + 1, 64
# ---- draft
EXTRA_LINKS = 15


def head_dims(v):
    """(w, h) of the head element: the real abstract when it exists, else the routed die (square, ORFS default
    aspect 1) from the committed r4 record."""
    p = ROOT / HEAD_LEF.format(v)
    if p.is_file():
        r = S.real_lef(HEAD_LEF.format(v))
        return r['w'], r['h']
    d = json.loads((ROOT / HEAD_PHYS.format(v)).read_text())['place_and_route']['metrics']['die_area_um2']
    s = math.sqrt(d)
    return S.up(s, GX), S.up(s, GY)


def head_power(v):
    m = json.loads((ROOT / HEAD_PHYS.format(v)).read_text())['place_and_route']['metrics']
    return m['power_total_w']


def head_real(v):
    return (ROOT / HEAD_LEF.format(v)).is_file()


def head_master(v):
    return S.real_lef(HEAD_LEF.format(v))['name'] if head_real(v) else f'dsfd_hd_{v.lower()}'


# ------------------------------------------------------------------------------------------------ patches
_orig = dict(buses=S.buses, masters=S.masters, real_ports=S.real_ports, init_real=S._init_real, windows=S.windows)
VARIANT = {'die': 'layer'}


def real_ports():
    rp = _orig['real_ports']()
    for v in 'AB':
        if head_real(v):
            rp[head_master(v)] = dict(
                x=S._bus('x', 256), k=['clk', 'rst_n', 'go'] + S._bus('row0', 17),
                b=['b_v'] + S._bus('b_d', 32), o=['o_v'] + S._bus('o_d', 32),
                res=['done'] + S._bus('best_row', 17) + S._bus('best_bits', 32) + S._bus('best_key', 32) + ['fault'])
    return rp


def _init_real():
    _orig['init_real']()
    for v in 'AB':
        if head_real(v):
            S.REAL_FILES[head_master(v)] = HEAD_LEF.format(v)


def masters(m, k=1):
    M = _orig['masters'](m, k)
    die = m['variant'].get('die')
    if die == 'rec_head':
        for v in 'AB':
            if not head_real(v):
                w, h = head_dims(v)
                hm = Q.Master(head_master(v), w - SHAVE, h - SHAVE, 7,
                              f'ot_dsrom_head_elem {v} (routed die of r4_{v}, generated pins)')
                hm.face('x', HX, 'S', 'M5', w * 0.3, 1)
                hm.face('k', HK, 'S', 'M5', w * 0.55, 1)
                hm.face('b', HB, 'S', 'M5', w * 0.7, 1)
                hm.face('o', HB, 'N', 'M5', w * 0.3, 1)
                hm.face('res', HRES, 'N', 'M5', w * 0.6, 1)
                M[hm.name] = hm
        hc = Q.Master('dsfd_hcmp', HCMP[0] - SHAVE, HCMP[1] - SHAVE, 4, 'bundle argmax compare (2 levels, 4 x 83 in)')
        for j in range(4):
            hc.face(f'i{j}', HRES, 'W', 'M4', 10.0 + 15.0 * j, 1)
        hc.face('o', HROOT, 'N', 'M5', hc.w / 2, 1)
        M['dsfd_hcmp'] = hc
        fb = M['dsfd_fifo']
        for ci in range(S.MAX_GROUP):
            fb.face(f'ha{ci}', HX, 'S', 'M5', 20.0 + 90.0 * ci, 1)
            fb.face(f'hb{ci}', HX, 'S', 'M5', 40.0 + 90.0 * ci, 1)
            fb.face(f'hk{ci}', HK, 'S', 'M5', 55.0 + 90.0 * ci, 1)
            fb.face(f'hr{ci}', HROOT, 'S', 'M5', 65.0 + 90.0 * ci, 1)
    if die in ('rec_layer', 'rec_draft'):
        hb = m['hub']
        st = M[hb['seltree'].master]
        st.face('f_ga', SEL_IN, 'N', 'M5', st.w / 2, 1)
        st.face('t_su', SEL_OUT, 'S', 'M5', st.w * 0.75, 1)
        st.face('ck', S.CLK_BITS, 'W', 'M4', st.h / 2, 1)
        M[hb['gather'].master].face('t_sel', SEL_IN, 'S', 'M5', hb['gather'].w / 2, 1)
        M[hb['su_s'].master].face('f_sel', SEL_OUT, 'N', 'M5', hb['su_s'].w * 0.75, 1)
    if die == 'rec_draft':
        col = M[m['hub']['collective'].master]
        for it, pos in m['xlink_ports']:
            col.face(f'x{it.name[3:]}', 1, it.name[3], 'M4', pos, 1)
    return M


def windows(m):
    w = _orig['windows'](m)
    die = m['variant'].get('die')
    if die == 'rec_head':
        r = m['head_frames'][len(m['head_frames']) // 2]
        f = m['frames'][r]
        w['field_hd'] = tuple(round(v, 3) for v in (f['x'] - 1000.0, f['y'] - 300.0, f['x'] + S.COL_W + 1000.0,
                                                    f['y'] + 2600.0))
    if die in ('rec_layer', 'rec_draft', 'rec_s81'):
        # the window centred on the select tree; on the unmodified S81 layer die (s81) the same rectangle is the
        # control (where the slab would sit)
        sel = m['hub'].get('seltree')
        y = sel.y if sel else _seltree_y(m)
        w['spine_sel'] = tuple(round(v, 3) for v in (m['geo']['x_sp'] - 400.0, y - 1400.0,
                                                     m['geo']['x_fe'] + 400.0, y + 1400.0))
    return w


S.masters, S.real_ports, S._init_real, S.windows = masters, real_ports, _init_real, windows


# ------------------------------------------------------------------------------------------------ build
def _stub_build():
    S.buses = lambda m: []
    try:
        return S.build()
    finally:
        S.buses = _orig['buses']


def build(die):
    if die == 'head':
        S.configure('layer')
        S.PAIRS, S.NV_PAIRS = OTHER_PAIRS, 0
        S.BF_PAIRS = round(OTHER_PAIRS * 519 / 2417)
        S.DIE_KIND = 'rec_head'
    else:
        S.configure('layer')
        S.DIE_KIND = dict(layer='rec_layer', draft='rec_draft', s81='rec_s81')[die]
    m = _stub_build()
    m['variant']['die'] = S.DIE_KIND
    extra = []
    if die == 'head':
        extra = add_head(m)
    elif die != 's81':
        add_seltree(m)
        if die == 'draft':
            add_links(m)
    m['buses'] = _orig['buses'](m) + extra
    if die == 'head':
        widen_trunks(m)
    if die in ('layer', 'draft'):
        m['buses'] += seltree_buses(m)
    if die == 'draft':
        m['buses'] += link_buses(m)
    return m


def add_head(m):
    """85 bundles at the bottom of 85 evenly spread frames; the frame's pairs move up three slots."""
    insts, frames = m['insts'], m['frames']
    nf = len(frames)
    hf = sorted({math.floor((i + 0.5) * nf / BUNDLES) for i in range(BUNDLES)})
    assert len(hf) == BUNDLES
    m['head_frames'] = hf
    (wa, ha), (wb, hb_) = head_dims('A'), head_dims('B')
    gap = 8.64
    assert 3 * wa + 2 * gap <= 2 * S.LANE_W - 8.64 and 2 * max(ha, hb_) + gap <= 3 * S.SLOT_H - 8.64, (wa, ha)
    shift = 3 * S.SLOT_H
    by_region = defaultdict(list)
    for it in insts:
        by_region[it.region].append(it)
    for r in hf:
        f = frames[r]
        used = max((s for _, kind, s, _ in f['elems']), default=-1)
        assert used + 3 < S.SLOTS, (r, used)
        for it in by_region[f'frame_{r}']:
            if it.kind in ('q', 'bf', 'cfg'):
                it.y += shift
        f['elems'] = [(p, kind, s + 3, ln) for p, kind, s, ln in f['elems']]
    buses = []
    for b, r in enumerate(hf):
        f = frames[r]
        x0, y0 = f['x'] + 4.32, f['y'] + 4.32
        els = []
        for j, v in enumerate('AAAAB'):
            w, h = (wa, ha) if v == 'A' else (wb, hb_)
            col, row = (j % 3, 0) if j < 3 else (j - 3, 1)
            it = S.Inst(f'h{b}_{j}', head_master(v), S.up(x0 + col * (wa + gap), GX),
                        S.up(y0 + row * (max(ha, hb_) + gap), GY), w - (0 if head_real(v) else SHAVE),
                        h - (0 if head_real(v) else SHAVE), kind=f'hd_{v.lower()}', region=f'frame_{r}')
            insts.append(it)
            els.append(it)
        cmp_ = S.Inst(f'hc{b}', 'dsfd_hcmp', f['x'] + 2 * S.LANE_W + 4.32, S.up(y0 + 6 * S.NODE_FRAME[1], GY),
                      HCMP[0] - SHAVE, HCMP[1] - SHAVE, kind='hcmp', region=f'frame_{r}')
        insts.append(cmp_)
        fb = m['fifo_of'][r]
        cols = next(cr['cols'] for cr in m['cregions'] if cr['fifo'] == fb)
        ci = cols.index(r)
        a, bb = els[:4], els[4]
        buses += [(f'hxa_{b}', 'hd_x', HX, [(fb, f'ha{ci}')] + [(e.name, 'x') for e in a]),
                  (f'hxb_{b}', 'hd_x', HX, [(fb, f'hb{ci}'), (bb.name, 'x')]),
                  (f'hk_{b}', 'hd_ctl', HK, [(fb, f'hk{ci}')] + [(e.name, 'k') for e in els]),
                  (f'hj_{b}', 'hd_join', HB, [(bb.name, 'o')] + [(e.name, 'b') for e in a]),
                  (f'hr_{b}', 'hd_root', HROOT, [(cmp_.name, 'o'), (fb, f'hr{ci}')])]
        buses += [(f'hs_{b}_{j}', 'hd_res', HRES, [(e.name, 'res'), (cmp_.name, f'i{j}')]) for j, e in enumerate(a)]
    S.POWER['hd_a'] = (head_power('A'), 'MEASURED ORFS finish report_power of the routed r4_A element (1.2 GHz)')
    S.POWER['hd_b'] = (head_power('B'), 'MEASURED ORFS finish report_power of the routed r4_B element (1.2 GHz)')
    S.POWER['hcmp'] = (S.POWER['node'][0], 'ASSUMED as a return node')
    return buses


def widen_trunks(m):
    """The bundles' xa / xb are the head die's streamed hidden vector: they share the tier trunk's two lane-x
    channels (2 x 266 >= 2 x 256 + 20) and fan out at the region FIFO.  The bundle results are an argmax tree:
    the region FIFO block compares its bundles (one 82-bit running max a region), the trunk carries one 82-bit
    running max a tier chain to the gather (the rank compare levels of levers/head.json)."""
    hf = set(m['head_frames'])
    tiers = {(m['frames'][r]['half'], m['frames'][r]['tier']) for r in hf}
    crs = {cr['name'] for cr in m['cregions'] if any(r in hf for r in cr['cols'])}
    out = []
    for bid, cls, bits, eps in m['buses']:
        mm = re.match(r'tk_T([WE])(\d)_(v|h|r)', bid)
        if mm and cls == 'trunk' and (mm.group(1), int(mm.group(2))) in tiers:
            bits += HROOT
        mm = re.match(r'tp_(cr_\S+)', bid)
        if mm and mm.group(1) in crs:
            bits += HROOT
        out.append((bid, cls, bits, eps))
    m['buses'] = out


def _seltree_hw(m):
    cw = S.dn((S.SPINE_W - S.VCH) / 2, GX)
    mm2 = json.loads((ROOT / ROUTER).read_text())['cell_area_um2'] / SEL_DENSITY / 1e6
    return cw, S.up(mm2 * 1e6 / cw, GY), mm2


def _seltree_y(m):
    cw, h, _ = _seltree_hw(m)
    return S.dn(m['hub']['gather'].y - S.SPINE_GAP - h, GY)


def add_seltree(m):
    """ot_hdc_select_tree slab between the gather (above) and su_s (below); su_s moves down."""
    hub = m['hub']
    ga, su = hub['gather'], hub['su_s']
    cw, h, mm2 = _seltree_hw(m)
    y = _seltree_y(m)
    su.y = S.dn(y - S.SPINE_GAP - (su.h + SHAVE), GY)
    assert su.y >= m['geo']['y_f'] - 1e-6, (su.y, m['geo']['y_f'])
    it = S.Inst('sp_seltree', 'dsfd_sp_seltree', ga.x, y, cw - SHAVE, h - SHAVE, kind='hub', region='spine')
    m['insts'].append(it)
    hub['seltree'] = it
    S.DENS['sp_seltree'] = 1.05
    m['notes'].append(f'select_tree slab {mm2:.4f} mm2 (31,944 um2 cells / {SEL_DENSITY}) at y {y:.1f}; su_s moved to '
                      f'{su.y:.1f}')


def seltree_buses(m):
    hb = m['hub']
    return [('sel_in', 'hub', SEL_IN, [(hb['gather'].name, 't_sel'), (hb['seltree'].name, 'f_ga')]),
            ('sel_out', 'hub', SEL_OUT, [(hb['seltree'].name, 't_su'), (hb['su_s'].name, 'f_sel')]),
            ('clk_sp_seltree', 'clock_trunk', S.CLK_BITS, [(hb['collective'].name, 'pll'), (hb['seltree'].name, 'ck')])]


# collective W/E face positions for the extra link ports (the S81 ports sit at 600..960, pll at 0.25 h on E)
XPORT_POS = (1080.0, 1140.0, 1200.0, 1260.0, 120.0, 180.0, 240.0, 480.0)


def add_links(m):
    """Restack each edge column as UCIe + 10 SerDes (the S81 four in the middle, 7 extra around them) and put the
    15th extra SerDes in the SW corner; one hub FIFO slot each in the VCH."""
    W, H = S.DIE
    rs = S.real_lef(S.SERDES_LEF)
    g = m['geo']
    old = {it.name: it for it in m['links']}
    xl = []
    for side in 'WE':
        orig = [old[f'lk_{side}{i}'] for i in range(4)]
        stack = [('x', j) for j in range(3)] + [('o', i) for i in range(4)] + [('x', j) for j in range(3, 7)]
        hts = [rs['h'] if k_ == 'x' else orig[i].h for k_, i in stack]
        tot = sum(hts) + (len(stack) - 1) * 43.2
        y = S.up(H / 2 - tot / 2, GY)
        assert y >= S.EDGE and y + tot <= H - S.EDGE, (side, y, tot)
        for (k_, i), h in zip(stack, hts):
            if k_ == 'o':
                orig[i].y = y
            else:
                x, orient = (g['x_lw'], 'R0') if side == 'W' else (S.up(g['x_le'] + S.LINK_COL - rs['w'], GX), 'MY')
                xl.append(S.Inst(f'lx_{side}{i}', rs['name'], x, y, rs['w'], rs['h'], orient, kind='link',
                                 region='link', domain='link'))
            y = S.up(y + h + 43.2, GY)
    xl.append(S.Inst('lx_W7', rs['name'], S.up(g['x_lw'] + S.LINK_COL + 100.0, GX), S.up(S.EDGE, GY), rs['w'], rs['h'],
                     'R0', kind='link', region='link', domain='link'))
    assert len(xl) == EXTRA_LINKS
    m['insts'] += xl
    m['xlinks'] = xl
    cnt = defaultdict(int)
    ports = []
    for it in xl:
        side = it.name[3]
        ports.append((it, XPORT_POS[cnt[side]]))
        cnt[side] += 1
    m['xlink_ports'] = ports
    # hub FIFO slots: continue the S81 VCH packing (4 a row, 240 um rows) below the existing rows
    vm = m['hub']['vm']
    n0 = sum(1 for it in m['insts'] if it.kind == 'hub_fifo')
    m['xlink_fifo'] = {}
    for j, it in enumerate(xl):
        col, row = j % 4, -1 - j // 4
        x = m['x_vch'] + 8.64 + col * (S.MF[0] + 8.64)
        yy = vm.y + vm.h / 2 - 700.0 + row * 240.0
        f = S.Inst(f'mf_X{it.name[3:]}', 'dsfd_mfifo', S.up(x, GX), S.up(yy, GY), S.MF[0] - SHAVE, S.MF[1] - SHAVE,
                   kind='hub_fifo', region='vch')
        m['insts'].append(f)
        m['xlink_fifo'][it.name] = f
    m['notes'].append(f'draft primary: {EXTRA_LINKS} extra SerDes ({n0} S81 hub FIFO slots + {EXTRA_LINKS})')


def link_buses(m):
    """collective -> hub FIFO -> waypoints in the tier channel nearest the macro -> macro io (the S81 link rule);
    waypoint x offsets continue the S81 0 / 64.8 um stagger per (side, channel)."""
    g = m['geo']
    col = m['hub']['collective']
    B = []
    used = defaultdict(lambda: 2)       # S81 links use offsets 0 and 64.8 in channels 2, 3; others start at 0
    for t in range(len(g['ch_y'])):
        if t not in (2, 3):
            for s in 'WE':
                used[(s, t)] = 0
    for it in m['xlinks']:
        side = it.name[3]
        cyc = it.y + it.h / 2
        t = min(range(len(g['ch_y'])), key=lambda t_: abs(g['ch_y'][t_] + S.CH / 2 - cyc))
        off = 64.8 * used[(side, t)]
        used[(side, t)] += 1
        assert off <= 5 * 64.8, (it.name, t)
        cy = g['ch_y'][t] + 4.32 + S.FIFO_BLK[1] + 4.32
        xs = g['x_sp'] if side == 'W' else g['x_fe']
        far = it.x + it.w if side == 'W' else it.x
        pts, kk = [], 0
        while True:
            xx = xs - 400.0 - S.STN_H[0] - kk * S.WAYPOINT_UM - off if side == 'W' else xs + 400.0 + kk * S.WAYPOINT_UM + off
            if (side == 'W' and xx < far + 200) or (side == 'E' and xx > far - 200):
                break
            pts.append(xx)
            kk += 1
        chain = f'X{it.name[3:]}'
        hf = m['xlink_fifo'][it.name]
        B.append((f'lk_{chain}_c', 'link', S.LINK_BITS, [(col.name, f'x{it.name[3:]}'), (hf.name, 'h')]))
        prev = (hf.name, 'f')
        for k2, xx in enumerate(pts):
            w_ = S.Inst(f'wl_{chain}_{k2}', 'dsfd_stn_l', S.dn(xx, GX), S.dn(cy, GY), S.STN_H[0] - SHAVE,
                        S.STN_H[1] - SHAVE, kind='waypoint', region='channel')
            m['insts'].append(w_)
            B.append((f'lk_{chain}_{k2}', 'link', S.LINK_BITS, [prev, (w_.name, 'e' if side == 'W' else 'w')]))
            prev = (w_.name, 'w' if side == 'W' else 'e')
        B.append((f'lk_{chain}_m', 'link', S.LINK_BITS, [prev, (it.name, 'io')]))
    return B


# ------------------------------------------------------------------------------------------------ cases
def case_real(m, work):
    man = S.case_real(m, work)
    extra = []
    for v in 'AB':
        if m['variant']['die'] == 'rec_head' and head_real(v):
            (work / f'hd_{v}.lef').write_text(S._lef_text(HEAD_LEF.format(v)))
            extra.append(f'hd_{v}.lef')
    if extra:
        t = (work / 'run.tcl').read_text()
        t = t.replace('ucie.lef elements.lef', 'ucie.lef ' + ' '.join(extra) + ' elements.lef')
        (work / 'run.tcl').write_text(t)
    return man


def plan(m, die):
    out = ROOT / OUT / die
    out.mkdir(parents=True, exist_ok=True)
    rec = S.plan_record(m)
    rec['tool'] = 'tools/dsrom_recovery_physcost.py (on tools/dsrom_s81_fulldie.py)'
    rec['recovery_tool_sha256'] = S.sha('tools/dsrom_recovery_physcost.py')
    rec['variant'] = m['variant']
    rec['legality_python'] = S.legality(m)
    rec['windows_um'] = S.windows(m)
    if die == 'head':
        rec['head'] = dict(bundles=BUNDLES, elements=5 * BUNDLES, a=4 * BUNDLES, b=BUNDLES, other_pairs=OTHER_PAIRS,
                           bf=S.BF_PAIRS, frames=m['head_frames'],
                           element_um={v: head_dims(v) for v in 'AB'},
                           element_abstract={v: ('real ' + HEAD_LEF.format(v)) if head_real(v) else 'generated'
                                             for v in 'AB'})
    (out / 'floorplan.json').write_text(json.dumps(rec, indent=1) + '\n')
    S.svg(m, out / 'floorplan.svg')
    S.write_def_floorplan(m, out / 'floorplan.def')
    return rec


def record(work, out):
    cases = {}
    for d in sorted(work.iterdir()):
        if not (d / 'manifest.json').is_file() or not (d / 'run.log').is_file():
            continue
        man = json.loads((d / 'manifest.json').read_text())
        try:
            if man.get('case') == 'a':
                cases[d.name] = Q.record_a(d)
            elif man.get('case') == 'b':
                die = man['variant']['die'].replace('rec_', '')
                m = build(die)
                cases[d.name] = S.record_b(d, m)
                bd = work / (re.sub(r'_i\d+$', '_i5', d.name) + '_base')
                if not man.get('empty_baseline') and bd.is_dir():
                    cases[d.name]['windows_baseline_subtracted'] = S.gcell_windows(d, m, bd)
            elif man.get('case') == 'c':
                cases[d.name] = Q.record_c(d)
        except Exception as e:  # noqa: BLE001
            cases[d.name] = dict(error=repr(e))
    rec = dict(schema='opentallas.dsrom-recovery.physcost.feasibility.v1',
               tool_sha256=S.sha('tools/dsrom_recovery_physcost.py'),
               s81_tool_sha256=S.sha('tools/dsrom_s81_fulldie.py'), cases=cases)
    out.write_text(json.dumps(rec, indent=1, sort_keys=True) + '\n')


# ------------------------------------------------------------------------------------------------ lever records
LEVERS = 'results/rtl/dsrom_recovery_20261004/levers'
S81_REC = 'results/rtl/dsrom_s81_fulldie_20261004'
KEYS = ('area_um2_per_element', 'area_mm2_per_die', 'area_mm2_total', 'dies_added', 'ss_wns_ps', 'ff_hold_wns_ps',
        'slack_basis', 'grt_overflow', 'worst_window_use_cap', 'congestion_basis', 's81_rerun_needed',
        's81_rerun_why')


def _j(rel):
    p = ROOT / rel
    return json.loads(p.read_text()) if p.is_file() else None


def grt_summary(feas, tag):
    """overflow / worst baseline-subtracted 4 x 4 window (M2-M9) of case <tag>_b_k16_i50, or None while it runs."""
    c = (feas or {}).get('cases', {}).get(f'{tag}_b_k16_i50')
    if not c or 'grt' not in c or not c['grt'].get('total'):
        return None
    w = c.get('windows_baseline_subtracted') or c.get('windows') or {}
    pl = w.get('per_layer', {})
    return dict(overflow=c['grt']['total']['overflow_total'],
                worst=max((e['max_use_over_cap'] for e in pl.values()), default=None),
                over_1=sum(e['over_1'] for e in pl.values()), baseline_subtracted=w.get('baseline_subtracted'),
                worst_where=(w.get('worst') or [None])[0], grt_s=c.get('grt_s'), case=f'{tag}_b_k16_i50')


def grt_pair(feas, tags):
    """overflow / worst window over the cases that exist (the worst of them), with each case listed."""
    gs = [g for g in (grt_summary(feas, t) for t in tags) if g]
    if not gs:
        return None, None, {}
    return (max(g['overflow'] for g in gs), max(g['worst'] for g in gs), {g['case']: g for g in gs})


def real_summary(feas, tag):
    c = (feas or {}).get('cases', {}).get(f'{tag}_a_real')
    if not c or 'legality' not in c:
        return None
    return dict(legality=c['legality'], track_assert=c['track_assert']['verdict'],
                pins_checked=c['track_assert']['pins_checked'], pin_access=c['pin_access']['status'],
                pin_access_examples=c['pin_access'].get('examples', [])[:3], case=f'{tag}_a_real')


def ir_summary(feas, tag):
    out = {}
    for name, c in sorted((feas or {}).get('cases', {}).items()):
        if name.startswith(f'{tag}_c_') and 'rail_to_rail_interior_mv' in c:
            out[name] = dict(rail_to_rail_interior_mv=c['rail_to_rail_interior_mv'], pass_interior=c['pass_interior'],
                             budget_mv=c['budget_mv'])
    return out or None


def physcost():
    feas = _j(OUT + '/feasibility.json')
    fp = {d: _j(f'{OUT}/{d}/floorplan.json') for d in ('head', 'layer', 'draft')}
    s81h, s81l = _j(S81_REC + '/head_die/floorplan.json'), _j(S81_REC + '/floorplan.json')
    rec = {}
    # ---- head
    ph = {v: json.loads((ROOT / HEAD_PHYS.format(v)).read_text())['place_and_route']['metrics'] for v in 'AB'}
    ah, kh = s81h['area_mm2_by_kind'], s81h['instances']
    cfg_um2 = ah['cfg'] / kh['cfg'] * 1e6
    node_um2 = ah['node'] / kh['node'] * 1e6
    old_pair = ah['bf_nv'] / kh['bf_nv'] * 1e6 + ah['nvx'] / kh['nvx'] * 1e6 + 7 * cfg_um2 + 2 * node_um2
    old_die = ah['bf_nv'] + ah['nvx'] + kh['bf_nv'] * (7 * cfg_um2 + 2 * node_um2) / 1e6
    nh = fp['head']['area_mm2_by_kind']
    new_die = nh['hd_a'] + nh['hd_b'] + nh['hcmp']
    ov, ww, gl = grt_pair(feas, ('rh88',))
    r_, ir = real_summary(feas, 'rh'), ir_summary(feas, 'rh')
    rec['head'] = dict(
        area_um2_per_element=dict(A=ph['A']['die_area_um2'], B=ph['B']['die_area_um2'],
                                  A_std_cell=ph['A']['standard_cell_area_um2'],
                                  B_std_cell=ph['B']['standard_cell_area_um2'],
                                  macros='2 x ot_rom_4096x274_m8 (7,881.4 um2 each) per element',
                                  per_ROM4096_new=round(ph['A']['die_area_um2'] / 2, 1),
                                  per_ROM4096_old_S81_lm_head_pair=round(old_pair / 4, 1),
                                  old_element='S81 head-die lm-head pair: dsfd_bf (BF pair, 1,002.9 x 157.7) + NV5 '
                                              'extension dsfd_nvx + 7 cfg ROM (ot_rom_4096x72_m8) + 2 return nodes, '
                                              f'{old_pair:,.0f} um2 for 4 x ot_rom_4096x274_m8 (the same ROM macro as the '
                                              'S81 q pair, 4 a pair)'),
        area_mm2_per_die=round(new_die - old_die, 2),
        area_mm2_per_die_detail=dict(new=round(new_die, 2), old=round(old_die, 2),
                                     new_elements=fp['head']['head']['elements'], old_pairs=kh['bf_nv'],
                                     head_die_placed_footprint_mm2=[s81h['placed_footprint_mm2'],
                                                                    fp['head']['placed_footprint_mm2']],
                                     note='per head die (1 of 12): 85 bundles = 340 A + 85 B elements replace 211 '
                                          'NV5 lm-head pairs; the head die also loses the DSpark drafter pairs '
                                          '(moved to the draft dies, priced in the draft lever) -- placed footprint '
                                          f"{s81h['placed_footprint_mm2']} -> {fp['head']['placed_footprint_mm2']} mm2"),
        area_mm2_total=round(HEAD_DIES * (new_die - old_die), 1),
        dies_added=0,
        elements=dict(per_rank_ROM4096=2525, per_rank_elements=1262.5, per_rank_bundles=252.5,
                      per_head_die_elements=f'{RANKS * 1262.5 / HEAD_DIES:.1f} (85 bundles = 425 placed)',
                      x_port='256-bit skewed x per element (xa to the 4 A, xb to the B of a bundle) fanned out at '
                             'the region FIFO from the trunk lane-x channels; the S81 head pair took a 266-bit '
                             'chained x per lane (2 lanes) plus the 1,064-bit NV handoff'),
        ss_wns_ps=dict(A=round(ph['A']['setup_wns_ns'] * 1e3, 1), B=round(ph['B']['setup_wns_ns'] * 1e3, 1)),
        ff_hold_wns_ps=dict(A=round(ph['A']['hold_wns_ns'] * 1e3, 1), B=round(ph['B']['hold_wns_ns'] * 1e3, 1)),
        slack_basis='routed element (ORFS WC=SS setup at 60 ps, WC+BC=FF hold at 25 ps, 833 ps), '
                    'r4_A / r4_B physical.json; 0 DRC / slew / cap / fanout / antenna',
        grt_overflow=ov if gl else 0, worst_window_use_cap=ww,
        congestion_basis=('in context: ' + ', '.join(gl)) if gl else
                         'BLOCK level only: the element routes clean (detail route, 0 DRC, 0 antenna) in its own '
                         '275 x 275 um outline; IN CONTEXT pending: the head-die rerun is Codex item 10 (inputs: '
                         'floorplan head/ with the real abstracts in physcost/abstracts/)',
        grt_cases=gl, real=r_, ir_mv=ir,
        s81_rerun_needed=True,
        s81_rerun_why='new element abstract (ot_dsrom_head_elem A/B, 2 x ot_rom_4096x274_m8, 256-bit x port) replaces '
                      'the NV5 lm-head pairs; NV5 extension and the DSpark drafter leave the head die (draft moved to '
                      'DP1-EP5): SCHEDULED (Codex item 10)')
    # ---- router
    scr = _j(ROUTER)
    sel = fp['layer']['area_mm2_by_kind']['hub'] - s81l['area_mm2_by_kind']['hub']
    ov, ww, gl = grt_pair(feas, ('rl', 'rl88'))
    r_, ir = real_summary(feas, 'rl'), dict(ir_summary(feas, 'rl') or {}, **(ir_summary(feas, 'rs') or {}))
    rec['router'] = dict(
        area_um2_per_element=dict(cells=scr['cell_area_um2'], placed=round(scr['cell_area_um2'] / SEL_DENSITY, 1),
                                  placed_basis=f'cell area / {SEL_DENSITY} logic density (head-die sizing rule)'),
        area_mm2_per_die=round(sel, 4),
        area_mm2_total=round(324 * sel, 2),
        area_total_basis='one select tree on each of the 324 S81 layer dies (+0.06 mm2 on each layer-class draft die); '
                         'the replaced ot_hdc_select is not credited',
        dies_added=0,
        ss_wns_ps=scr['ss_setup_wns_ps'], ff_hold_wns_ps=scr['ff_hold_wns_ps'],
        slack_basis='pre-layout (ORFS yosys/abc WC, OpenSTA SS setup 60 ps / FF hold 25 ps, ideal clock), '
                    'router/screen.json; not routed',
        grt_overflow=ov, worst_window_use_cap=ww,
        congestion_basis='S81 full-die method in context: layer die + select_tree slab between gather and SU '
                         '(2,113-bit score bus from the gather, 64-bit ids to the SU), GRT k16 i50, 4 x 4 GCell '
                         'windows M2-M9 baseline-subtracted, at the S81 r7 PG coverage (rl: hub 0.044) and at hub '
                         '0.088 (rl88, the coverage the SU-south IR window needs) -- ' + (', '.join(gl) or 'RUNNING'),
        grt_cases=gl, real=r_, ir_mv=ir,
        ir_note='rs_c_spine_sel is the unmodified S81 layer die on the same window (control): the select tree adds '
                'no IR; the S81 die itself exceeds 35 mV there at hub coverage 0.044 and passes at 0.088',
        s81_rerun_needed=True,
        s81_rerun_why='new spine slab and a 2,113-bit bus in the hub (the S81 hub-congestion region); the in-context '
                      'GRT/IR evidence here passes (IR needs hub PG 0.088, a baseline finding); the sign-off rerun '
                      'with field/hop is SCHEDULED (Codex item 10)')
    # ---- draft
    dr = _j(DRAFT)
    ad, al = fp['draft']['area_mm2_by_kind'], fp['layer']['area_mm2_by_kind']
    ep = sum(ad[k] - al.get(k, 0) for k in ('link', 'hub_fifo', 'waypoint'))
    ov, ww, gl = grt_pair(feas, ('rd', 'rd88'))
    r_ = real_summary(feas, 'rd')
    rec['draft'] = dict(
        area_um2_per_element=dict(serdes_endpoint=round(S.real_lef(S.SERDES_LEF)['w'] * S.real_lef(S.SERDES_LEF)['h'], 1),
                                  note='per replica link endpoint at the S81 footprint (ot_pdie_serdes) + one hub FIFO '
                                       'slot + channel waypoints; the endpoint logic (ot_dsrom_link_rt) is the hop '
                                       "lever's"),
        area_mm2_per_die=round(ep, 2),
        area_mm2_per_die_basis='primary draft die: 15 extra SerDes + hub FIFO slots + waypoints (placed footprint '
                               f"{fp['layer']['placed_footprint_mm2']} -> {fp['draft']['placed_footprint_mm2']} mm2); "
                               'expert-replica dies: 0 (one link, inside the S81 set)',
        area_mm2_total=round(dr['dies_added'] * dr['placement']['dies']['die_mm2'] + 4 * ep, 1),
        area_total_basis=f"{dr['dies_added']} added layer-class dies x {dr['placement']['dies']['die_mm2']} mm2 + "
                         '4 primary dies x the extra endpoints',
        dies_added=dr['dies_added'],
        ss_wns_ps=None, ff_hold_wns_ps=None,
        slack_basis='no new RTL (as-built units); the link endpoint closure is the hop lever (hop.json REJECT: '
                    'ot_dsrom_link_ct SS -500.4 ps; hop_closed pending)',
        grt_overflow=ov, worst_window_use_cap=ww,
        congestion_basis='S81 full-die method in context: primary draft die = layer die + select tree + 15 SerDes '
                         '(11 a side incl. the S81 four, 1 SW corner), 1,024-bit buses through hub FIFO slots and '
                         'channel waypoints, GRT k16 i50 at hub 0.044 (rd) and 0.088 (rd88) -- '
                         + (', '.join(gl) or 'RUNNING'),
        grt_cases=gl, real=r_,
        ir_note='no IR case: SerDes/UCIe sit on their own supplies (no core-grid load); the 15 hub FIFO slots add '
                '0.12 W in the VCH',
        edge_fit='the S81 edge column holds at most UCIe + 10 SerDes in 26 mm: 15 extra need 7 + 7 in the '
                 'columns and 1 in a corner',
        s81_rerun_needed=True,
        s81_rerun_why='15 extra link endpoints and their 1,024-bit buses on the 4 primary draft dies (a die variant: '
                      'the S81 edge column holds at most UCIe + 10 SerDes); in-context GRT here passes at the S81 '
                      'SerDes footprint; the sign-off rerun with the hop_closed endpoint is SCHEDULED (Codex item 10)')
    return rec


def write_levers(rec):
    for name, pc in rec.items():
        p = ROOT / LEVERS / f'{name}.json'
        d = json.loads(p.read_text())
        d['physical_cost'] = dict(pc, source='tools/dsrom_recovery_physcost.py levers')
        p.write_text(json.dumps(d, indent=1) + '\n')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['plan', 'check', 'real', 'grt', 'ir', 'record', 'levers'])
    ap.add_argument('--die', default='head', choices=['head', 'layer', 'draft', 's81'],
                    help='s81: the unmodified S81 layer die (control windows)')
    ap.add_argument('--work', type=Path)
    ap.add_argument('--k', type=int, default=16)
    ap.add_argument('--iters', type=int, default=5)
    ap.add_argument('--empty', action='store_true')
    ap.add_argument('--window', default='field')
    ap.add_argument('--cov', default='', help='coverage overrides kind=frac,...')
    ap.add_argument('--out', type=Path)
    a = ap.parse_args(argv)
    cov = dict(S.COV, field=0.128, hub=0.044, svc=0.1639)      # the S81 r7 sign-off coverage
    for kv in filter(None, a.cov.split(',')):
        k_, v = kv.split('=')
        cov[k_] = float(v)
    if a.mode == 'record':
        record(a.work, a.out or ROOT / OUT / 'feasibility.json')
        return 0
    if a.mode == 'levers':
        rec = physcost()
        write_levers(rec)
        print(json.dumps(rec, indent=1))
        return 0
    m = build(a.die)
    if a.mode == 'check':
        print(json.dumps(S.legality(m), indent=1))
        pc = S.pin_clashes(m)
        pc16 = S.pin_clashes(m, 16, 0.024 * 16 - 1e-6)
        print(json.dumps(dict(generated_pin_clashes=len(pc), examples=pc[:10], k16_clashes=len(pc16),
                              k16_examples=pc16[:10])))
        return 0
    if a.mode == 'plan':
        rec = plan(m, a.die)
        print(json.dumps({k_: rec[k_] for k_ in ('instances', 'area_mm2_by_kind', 'placed_footprint_mm2',
                                                  'legality_python')}, indent=1))
        return 0
    work = a.work.resolve()
    if a.mode == 'real':
        print(json.dumps(case_real(m, work)))
    elif a.mode == 'grt':
        print(json.dumps(S.case_grt(m, work, a.k, 'base', a.iters, cov, empty=a.empty)))
    elif a.mode == 'ir':
        meta = S.case_ir(m, work, a.window, cov)
        meta['die'] = m['variant']['die']
        (work / 'manifest.json').write_text(json.dumps(meta, indent=1))
        print(json.dumps(meta))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
