#!/usr/bin/env python3
"""DeepSeek-V4.1 ROM S81 scan die: full-die physical composition and die-level feasibility (2026-10-04).

Decision: results/uarch/dsrom_c_recheck_20261004/DECISION.md (S81: 81 stages, 2,417 pairs per rank die of which
519 BF-capable, ragged RD64 return sized to the active pairs = 2*2417-128 = 4,706 nodes, per-rank indexer
projections).  Floorplan -> hardened element -> replicate (AGENTS.md design method 2), on the Qwen full-die flow
(tools/qwen_rom_fulldie.py): every element is an abstract with real ASAP7 signal pins, placed through the
orientation-aware snap library, connected by every die-level net.

Die (33,000 x 26,000 um, the 26 x 33 mm outline of the physical contract), scan die = four HBM3E stacks:

  field        128 root regions = 128 column frames (64 per half, 13 columns x 5 tiers), one frame per ragged
               return root.  A frame is 12 slots of 239.76 um; a slot holds two q pairs side by side (two x
               lanes) or one BF pair, each over its row of 7 cfg ROMs (ot_rom_4096x72_m8, real LEF); the q pair
               is the REAL routed abstract ot_v41_rom_elem_q_qp_w10 (510.84 x 126.9, 734 M5 pins; R_cap0 readback,
               results/uarch/dsrom_c_w4_20261003/s82_combined_r1/routed_q).  The frame's east strip holds its
               ragged return tree (2P-1 nodes of the unchanged ot_v41_retn_w17w10, in-order along the strip).
  channels     a 259.2 um channel under every tier: the clock-region (option C) FIFO blocks of its regions and the
               forwarded-link waypoints of its trunk (x broadcast out, return roots back).
  spine        2,635.2 um at the die centre: W column SU (split around) VM / gather / capture / collective,
               E column HC; a 302.4 um vertical channel between them (waypoints, hub-side FIFO slots).
  bands        S and N: two e8p5 HBM3E PHYs each (real LEF, pins on the core face), the streaming controller and
               the per-stack scan service (quarter of the attention tiles + pooled indexer ring reader); the
               selector (S) and banked collector (N) between the two stacks.
  links        W and E edges: one UCIe + three board SerDes each (real pdie_v2 LEFs).

Modes:  plan | real --work W | grt --work W --k K --iters N | ir --work W --window NAME | record --work ROOT
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import qwen_rom_fulldie as Q  # noqa: E402  (Master, lef_text, pin_rects, esc, records)

OUT = 'results/rtl/dsrom_s81_fulldie_20261004'
DECISION = 'results/uarch/dsrom_c_recheck_20261004/model.json'
# OT_S81_Q_LEF (default unset = the R_cap0 abstract below): an alternative routed q abstract for the die-level
# pin-access check of a successor element (e.g. the QX q-element), same port names, height <= the 157.68 frame.
Q_LEF = os.environ.get('OT_S81_Q_LEF', 'results/uarch/dsrom_c_w4_20261003/s82_combined_r1/routed_q/routed_element.lef.gz')
CFG_LEF = 'results/uarch/dsrom_c_w4_20261003/s82_inputs/cfg.lef'
FIXED = 'results/uarch/dsrom_c_w4_20261003/inputs/fixed.json'
CONTRACT = 'results/uarch/dsrom_c_w4_20261003/s82_inputs/physical_contract.json'
PHY_LEF = 'physical/asap7_memory_macros_v2/ot_hbm3e_phy_v41x_aw30_e8p5/ot_hbm3e_phy_v41x_aw30_e8p5.lef'
SERDES_LEF = 'physical/asap7_v41x_pdie_macros_v2/ot_pdie_serdes/ot_pdie_serdes.lef'
UCIE_LEF = 'physical/asap7_v41x_pdie_macros_v2/ot_pdie_ucie/ot_pdie_ucie.lef'
MESO = 'results/uarch/meso_fifo_20261004/physical/meso_d4_v3/physical.json'
SNAP_LIB = 'physical/common/ot_macro_track_snap.tcl'
PLAT = '/OpenROAD-flow-scripts/flow/platforms/asap7'

GX, GY = 0.432, 2.16
SHAVE = 0.024
DIE = (33000.0, 26000.0)
EDGE = 20.0
PAIRS, BF_PAIRS, ROOTS = 2417, 519, 128
NV_PAIRS = 0
HEAD_REC = 'results/uarch/dsrom_l2_head_mac_20261004/model.json'
NVX_UM2 = 115775.5            # NV5 batched-draft-head delta per lm-head pair, placed (HEAD_REC variants NV=5)
NV_BITS = 4 * 266             # the four extra x vectors handed from the pair to its NV extension
DIE_KIND = 'layer'


def configure(die):
    """'layer': the S81 layer die (L20 scan die = the hottest).  'head': one of the 12 head dies (coordinator
    decision 2026-10-04, main 57e041e74): 1,682 content pairs (embed + lm-head + norm + DSpark drafter), of which the
    210 lm-head pairs carry the NV5 batched draft head; the drafter/embed pairs keep the layer die's BF share."""
    global PAIRS, BF_PAIRS, NV_PAIRS, DIE_KIND
    DIE_KIND = die
    if die == 'layer':
        PAIRS, BF_PAIRS, NV_PAIRS = 2417, 519, 0
    else:
        h = json.loads((ROOT / HEAD_REC).read_text())
        v = next(x for x in h['variants'] if x['NV'] == 5)['head_groups']['12']
        PAIRS, NV_PAIRS = math.ceil(v['content_pairs_per_die']), math.ceil(v['lm_head_pairs_per_die'])
        BF_PAIRS = round((PAIRS - NV_PAIRS) * 519 / 2417)


def nv_sites():
    return {round((i + 0.5) * PAIRS / NV_PAIRS) for i in range(NV_PAIRS)} if NV_PAIRS else set()
CFG_PER_PAIR = 7
# field geometry
LANE_W = 520.128              # q frame 510.84 + 2 x 4.32 halo, up to the 0.432 lattice
SLOT_H = 239.76               # cfg row 62.91 + element frame 157.68 + halos (111 x 2.16)
SLOTS = 12
CFG_DY, ELEM_DY = 4.32, 77.76  # in-slot offsets: cfg row, element (frame top = 235.44 = SLOT_H - 4.32)
CFG_PITCH = 46.656
NODE_FRAME = (86.4, 77.76)    # ragged-return node slot (6,718.5 um2 >= decision 31.548 mm2 / 4,706 = 6,703.8)
NS_W = 95.04                  # node strip: node + 2 x 4.32
COL_W = 2 * LANE_W + NS_W     # 1,135.296
COL_PITCH = COL_W + 8.64      # 1,143.936
TIER_COLS = (8, 11, 13, 13, 11, 8)   # frames per tier and half: a Manhattan 'diamond' around the VM x root
COLS, TIERS = max(TIER_COLS), len(TIER_COLS)
CH = 259.2                    # tier channel
MAX_GROUP = 4                 # columns per clock region (4 x 1,143.9 um <= 5.25 mm)


def colgroups(n):
    out = []
    while n > MAX_GROUP:
        out.append(3)
        n -= 3
    return out + [n]
SPINE_GAP = 172.8                # routing channel between stacked spine slabs (80 rows of 2.16)
SPINE_W, VCH = 2635.2, 604.8     # VCH widened 302.4 -> 604.8 (r3: GRT overflow at the VM / hub FIFOs)
LINK_COL = 261.36
# bands
PHY_W, PHY_H = 8500.056, 1177.2
CTRL_D, SVC_D = 248.4, 1576.8
FIFO_BLK = (380.16, 129.6)    # 3 meso FIFO slots (W512 D4: 15,693 um2 die each, MESO)
STN_H = (51.84, 86.4)         # horizontal-chain waypoint (pins W/E, tap S)
STN_V = (86.4, 34.56)         # vertical-chain waypoint (pins N/S)
MF = (125.28, 125.28)         # one meso / async FIFO slot (hub side)
LINK_STAGE_UM = 430.56
WAYPOINT_UM = 4 * LINK_STAGE_UM
# element interfaces (physical contract + real q pins)
XI, XO, CFGB, RET, XCTL = 266, 266, 54, 126, 17   # chained x in/out, cfg word, return word, lane control
NODE_W = 66
LANE_X = XI + XCTL + 3       # one lane's bits from its region FIFO (chained x + lane control)
SVC_HUB_BITS = dict(q=512, ao=512, ix=512)
HBM_RD_BITS = 8192 + 544 + 128   # controller -> scan service: kr_data + kr_tag + kr_beat (the PHY's read side)
LINK_BITS = 1024
CLK_BITS = 3

# spine slabs (mm2): fixed.json source service rectangles (S82 W4 reservations) and the R49 / C9 capture homes
HUB_MM2 = dict(collective=1.38967, vm=0.89234, gather=1.38823, su=12.80594, hc=18.31349, capture=0.10868,
               selector=1.68488, collector=4.64447, indexer=7.52245, attention=45.86549, ctrl_cut=0.08264)


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def up(v, q):
    return round(math.ceil(v / q - 1e-9) * q, 6)


def dn(v, q):
    return round(math.floor(v / q + 1e-9) * q, 6)


class Inst:
    __slots__ = ('name', 'master', 'x', 'y', 'w', 'h', 'orient', 'kind', 'region', 'domain', 'power_w')

    def __init__(self, name, master, x, y, w, h, orient='R0', kind='', region='', domain='stream_1p2', power_w=0.0):
        self.name, self.master, self.x, self.y, self.w, self.h = name, master, x, y, w, h
        self.orient, self.kind, self.region, self.domain, self.power_w = orient, kind, region, domain, power_w

    def box(self):
        return (self.x, self.y, self.x + self.w, self.y + self.h)

    def d(self):
        return dict(name=self.name, master=self.master, x=round(self.x, 3), y=round(self.y, 3), w=round(self.w, 3),
                    h=round(self.h, 3), orient=self.orient, kind=self.kind, region=self.region, domain=self.domain)


# ------------------------------------------------------------------------------------------------ real LEFs
def _lef_text(rel):
    p = ROOT / rel
    if rel.endswith('.gz'):
        import gzip
        return gzip.decompress(p.read_bytes()).decode()
    return p.read_text()


_REAL = {}


def real_lef(rel):
    """{name, w, h, obs_top, pins: {pin: (layer, (x0,y0,x1,y1))}} of a real LEF macro (signal pins only)."""
    if rel in _REAL:
        return _REAL[rel]
    t = _lef_text(rel)
    name = re.search(r'^MACRO (\S+)', t, re.M).group(1)
    w, h = map(float, re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', t).groups())
    pins = {}
    for pm in re.finditer(r'\n  PIN (\S+)\n(.*?)\n  END \1', t, re.S):
        body = pm.group(2)
        if 'USE POWER' in body or 'USE GROUND' in body:
            continue
        rm = re.search(r'LAYER (\S+) ;\s+RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)', body)
        pins[pm.group(1)] = (rm.group(1), tuple(float(v) for v in rm.groups()[1:]))
    obs = re.search(r'\n  OBS(.*?)\n  END', t, re.S)
    obs_top = max((int(x) for x in re.findall(r'LAYER M(\d)', obs.group(1))), default=0) if obs else 0
    _REAL[rel] = dict(name=name, w=w, h=h, obs_top=obs_top, pins=pins, text=t)
    return _REAL[rel]


def _bus(base, n):
    return [f'{base}[{i}]' for i in range(n)]


def real_ports():
    """master -> port -> ordered real pin names (the netlist binds port bit i to the i-th name)."""
    qp = dict(
        xi=_bus('xs_q0', 256) + _bus('xs_e0', 10),
        k=_bus('xs_b', 3) + _bus('xs_p', 8) + _bus('xs_pos', 3) + _bus('xs_sv', 2) + ['xs_v', 'clk', 'go', 'rst_n'],
        xo=_bus('xs_q1', 256) + _bus('xs_e1', 10),
        cfg=_bus('cfg_a', 5) + _bus('cfg_d', 48) + ['cfg_v'],
        r0=_bus('pval', 64)[:32] + _bus('prow', 32)[:16] + _bus('pseg', 10) + ['pv[0]', 'perr[0]'] + _bus('ppos', 6)[:3],
        r1=_bus('pval', 64)[32:] + _bus('prow', 32)[16:] + _bus('pnseg', 10) + ['pv[1]', 'perr[1]'] + _bus('ppos', 6)[3:],
        st=['busy', 'fault'])
    assert len(qp['xi']) == XI and len(qp['xo']) == XO and len(qp['cfg']) == CFGB and len(qp['k']) == XCTL + 3
    assert len(qp['r0']) == len(qp['r1']) == RET // 2 and len(set(qp['r0'] + qp['r1'])) == RET
    cfg = dict(rd=_bus('rd_out', CFGB), ctl=['clk', 'ce_in'] + _bus('addr_in', 12))
    phy = real_lef(PHY_LEF)
    dfi = sorted(phy['pins'], key=lambda p: (phy['pins'][p][1][0], p))
    sd = dict(io=_bus('tx', 512) + _bus('rx', 512), ck=['clk'])
    return {real_lef(Q_LEF)['name']: qp, real_lef(CFG_LEF)['name']: cfg, phy['name']: dict(dfi=dfi),
            real_lef(SERDES_LEF)['name']: sd, real_lef(UCIE_LEF)['name']: sd}


REAL_FILES = {}


def _init_real():
    if REAL_FILES:
        return
    for rel in (Q_LEF, CFG_LEF, PHY_LEF, SERDES_LEF, UCIE_LEF):
        REAL_FILES[real_lef(rel)['name']] = rel


# ------------------------------------------------------------------------------------------------ field map
def region_bounds():
    return [math.floor(r * PAIRS / ROOTS) for r in range(ROOTS + 1)]


def bf_sites():
    nv = nv_sites()
    rest = [p for p in range(PAIRS) if p not in nv]
    s = sorted({rest[round(i * len(rest) / BF_PAIRS)] for i in range(BF_PAIRS)})
    assert len(s) == BF_PAIRS
    return set(s)


def return_tree(leaves):
    """Balanced binary tree over leaves [0, n): nodes as (id, left, right) with children 'L<i>' / 'N<j>', in-order
    rank per node (position along the strip)."""
    nodes = []

    def rec(lo, hi):
        if hi - lo == 1:
            return f'L{lo}'
        mid = (lo + hi + 1) // 2 if (hi - lo) % 2 else (lo + hi) // 2
        # keep each element's two words under one node: split on an even leaf index when possible
        if mid % 2 and mid + 1 < hi:
            mid += 1
        a = rec(lo, mid)
        j = len(nodes)
        nodes.append(None)
        b = rec(mid, hi)
        nodes[j] = (f'N{j}', a, b)
        return f'N{j}'
    root = rec(0, leaves)
    return nodes, root


# ------------------------------------------------------------------------------------------------ build
def build(variant=None):
    variant = variant or {}
    W, H = DIE
    insts, regions, notes = [], [], []
    bounds, bfs, nvs = region_bounds(), bf_sites(), nv_sites()
    # ---- x layout
    x_lw = up(EDGE, GX)                                  # west link column
    x_fw = up(x_lw + LINK_COL + 0.5 * (W - 2 * x_lw - 2 * LINK_COL - 2 * COLS * COL_PITCH - SPINE_W), GX)
    x_sp = up(x_fw + COLS * COL_PITCH, GX)
    x_fe = up(x_sp + SPINE_W, GX)
    x_le = dn(W - EDGE - LINK_COL, GX)
    assert x_fe + COLS * COL_PITCH <= x_le + 1e-6, 'field does not fit in x'
    # ---- y layout
    band = up(EDGE, GY) + PHY_H + 8.64 + CTRL_D + 8.64 + SVC_D
    field_h = TIERS * SLOTS * SLOT_H + (TIERS + 1) * CH
    y_f = up((H - field_h) / 2, GY)
    ch_y = [y_f + t * (SLOTS * SLOT_H + CH) for t in range(TIERS + 1)]
    tier_y = [c + CH for c in ch_y[:TIERS]]
    y_top = ch_y[TIERS] + CH
    assert band <= y_f and y_top <= H - band, 'bands overlap field'
    geo = dict(x_lw=x_lw, x_fw=x_fw, x_sp=x_sp, x_fe=x_fe, x_le=x_le, y_f=y_f, y_top=y_top, ch_y=ch_y, tier_y=tier_y,
               band_depth=band, field_h=field_h, spine_cx=x_sp + SPINE_W / 2)

    def col_x(half, c):           # column c counted from the spine outward
        return x_sp - (c + 1) * COL_PITCH + 8.64 if half == 'W' else x_fe + c * COL_PITCH
    geo['col_x'] = col_x
    # ---- field: 128 frames
    frames = {}
    slot_of = {}
    k = 0
    order = [(h, t, c) for h in 'WE' for t in range(TIERS) for c in range(TIER_COLS[t])]
    used = order
    assert len(used) == ROOTS
    for r, (half, t, c) in enumerate(used):
        x0, y0 = col_x(half, c), tier_y[t]
        frames[r] = dict(half=half, tier=t, col=c, x=x0, y=y0)
        regions.append(dict(name=f'frame_{r}', kind='field', rect=[x0, y0, x0 + COL_W, y0 + SLOTS * SLOT_H]))
        pairs = list(range(bounds[r], bounds[r + 1]))
        slot, half_open = -1, None          # a q fills the R lane of the last half-open q slot, even past a BF
        elems = []
        for p in pairs:
            if p in nvs:
                slot += 2
                elems.append((p, 'NV', slot - 1, 'B'))
            elif p in bfs:
                slot += 1
                elems.append((p, 'BF', slot, 'B'))
            elif half_open is not None:
                elems.append((p, 'q', half_open, 'R'))
                half_open = None
            else:
                slot += 1
                half_open = slot
                elems.append((p, 'q', slot, 'L'))
        assert slot < SLOTS, (r, slot)
        frames[r]['elems'] = elems
        for p, kind, s, ln in elems:
            sy = y0 + s * SLOT_H
            ex = x0 + (LANE_W if ln == 'R' else 0) + 4.32
            if kind == 'NV':
                it = Inst(f'e{p}', 'dsfd_bf', ex, sy + ELEM_DY, 1002.888, 157.68 - SHAVE, kind='bf_nv',
                          region=f'frame_{r}')
                nh = up(NVX_UM2 / 1002.888, GY)
                insts.append(Inst(f'v{p}', 'dsfd_nvx', ex, sy + SLOT_H + CFG_DY, 1002.888, nh - SHAVE, kind='nvx',
                                  region=f'frame_{r}'))
            elif kind == 'BF':
                it = Inst(f'e{p}', 'dsfd_bf', ex, sy + ELEM_DY, 1002.888 - SHAVE + 0.024, 157.68 - SHAVE,
                          kind='bf', region=f'frame_{r}', power_w=0.0)
            else:
                rq = real_lef(Q_LEF)
                it = Inst(f'e{p}', rq['name'], ex, sy + ELEM_DY, rq['w'], rq['h'], kind='q', region=f'frame_{r}')
            insts.append(it)
            slot_of[p] = (r, s, ln)
            rc = real_lef(CFG_LEF)
            for j in range(CFG_PER_PAIR):
                cx = ex + j * CFG_PITCH if kind == 'q' else ex + j * 2 * CFG_PITCH
                insts.append(Inst(f'c{p}_{j}', rc['name'], cx, sy + CFG_DY, rc['w'], rc['h'], kind='cfg',
                                  region=f'frame_{r}'))
        # return tree in the strip
        nleaf = 2 * len(pairs)
        nodes, root = return_tree(nleaf)
        frames[r]['tree'] = (nodes, root)
        for j, (nid, a, b) in enumerate(nodes):
            rank = _inorder_rank(nodes, root)[nid]
            insts.append(Inst(f'n{r}_{j}', 'dsfd_node', x0 + 2 * LANE_W + 4.32, y0 + rank * NODE_FRAME[1],
                              NODE_FRAME[0] - SHAVE, NODE_FRAME[1] - SHAVE, kind='node', region=f'frame_{r}'))
    # ---- clock regions and FIFO blocks (option C): one block per (half, tier, colgroup), in the channel under the
    # tier at the region's spine-side end
    cregions = []
    fifo_of = {}
    for half in 'WE':
        for t in range(TIERS):
            c0 = 0
            for g, ncol in enumerate(colgroups(TIER_COLS[t])):
                cols = list(range(c0, c0 + ncol))
                c0 += ncol
                rs = [r for r, f in frames.items() if f['half'] == half and f['tier'] == t and f['col'] in cols]
                if not rs:
                    continue
                xs = [col_x(half, c) for c in cols]
                rect = [min(xs), ch_y[t], max(xs) + COL_W, tier_y[t] + SLOTS * SLOT_H]
                name = f'cr_{half}{t}{g}'
                cregions.append(dict(name=name, kind='field', rect=rect, frames=rs))
                fx = (rect[2] - FIFO_BLK[0] - 4.32) if half == 'W' else rect[0] + 4.32
                fb = Inst(f'fb_{half}{t}{g}', 'dsfd_fifo', up(fx, GX) if half == 'E' else dn(fx, GX),
                          ch_y[t] + 4.32, FIFO_BLK[0] - SHAVE, FIFO_BLK[1] - SHAVE,
                          orient='R0' if half == 'W' else 'MY', kind='fifo_blk', region=name)
                insts.append(fb)
                for r in rs:
                    fifo_of[r] = fb.name
                frames_in = sorted(rs, key=lambda r: frames[r]['col'])
                cregions[-1]['fifo'] = fb.name
                cregions[-1]['cols'] = frames_in
    # ---- spine
    x_vch = x_sp + (SPINE_W - VCH) / 2
    cw = dn((SPINE_W - VCH) / 2, GX)
    x_vch = x_sp + cw
    x_spe = x_vch + VCH
    regions.append(dict(name='spine', kind='hub', rect=[x_sp, y_f, x_fe, y_top]))
    regions.append(dict(name='vch', kind='channel', rect=[x_vch, y_f, x_vch + VCH, y_top]))
    mid = (y_f + y_top) / 2
    hub = {}

    def slab(name, mm2, x, y, w, dom='stream_1p2', kind='hub'):
        h = up(mm2 * 1e6 / w, GY)
        it = Inst(f'sp_{name}', f'dsfd_sp_{name}', x, y, w - SHAVE, h - SHAVE, kind=kind, region='spine', domain=dom)
        insts.append(it)
        hub[name] = it
        return it
    centre = ['gather', 'vm', 'capture', 'collective']
    # r4: a SPINE_GAP routing channel between every pair of stacked W-column slabs (b3 GRT: the abutted slab faces
    # carried the 1,024-bit VM <-> SU and the gather/capture buses with no escape room, M8 1.29 / M9 1.15 use/cap)
    ch = sum(up(HUB_MM2[n] * 1e6 / cw, GY) for n in centre) + (len(centre) - 1) * SPINE_GAP
    yc = dn(mid - ch / 2, GY)
    su_lo = HUB_MM2['su'] * (yc - y_f) / (yc - y_f + y_top - (yc + ch))
    s = slab('su_s', su_lo, x_sp, dn(yc - SPINE_GAP - up(su_lo * 1e6 / cw, GY), GY), cw, dom='serial_0p9')
    yy = yc
    for n in centre:
        it = slab(n, HUB_MM2[n], x_sp, yy, cw, dom='serial_0p9' if n == 'vm' else 'stream_1p2')
        yy += up(HUB_MM2[n] * 1e6 / cw, GY) + SPINE_GAP
    slab('su_n', HUB_MM2['su'] - su_lo, x_sp, yy, cw, dom='serial_0p9')
    hc_h = up(HUB_MM2['hc'] * 1e6 / cw, GY)
    slab('hc', HUB_MM2['hc'], x_spe, dn(mid - hc_h / 2, GY), cw, dom='serial_0p9')
    for it in insts:
        if it.region == 'spine':
            assert it.y >= y_f - 1e-6 and it.y + it.h <= y_top + 1e-6, (it.name, it.y, it.y + it.h, y_f, y_top)
    # ---- bands: PHY (edge), controller, scan service; selector (S) and collector (N) between the stacks
    rp = real_lef(PHY_LEF)
    phys, ctrls, svcs = {}, {}, {}
    xs_phy = [up(x_fw + (x_sp - x_fw) / 2 - PHY_W / 2, GX), up(x_fe + (x_le - x_fe) / 2 - PHY_W / 2, GX)]
    for side in 'SN':
        for i, xp in enumerate(xs_phy):
            st = f'{side}{"WE"[i]}'
            if side == 'S':
                yp = up(EDGE, GY)
                yc_ = up(yp + PHY_H + 8.64, GY)
                ys_ = up(yc_ + CTRL_D + 8.64, GY)
                orient = 'R0'
            else:
                yp = dn(H - EDGE - PHY_H, GY)
                yc_ = dn(yp - 8.64 - CTRL_D, GY)
                ys_ = dn(yc_ - 8.64 - SVC_D, GY)
                orient = 'MX'
            phys[st] = Inst(f'phy_{st}', rp['name'], xp, yp, rp['w'], rp['h'], orient, kind='phy', region='phy',
                            domain='hbm')
            ctrls[st] = Inst(f'ctrl_{st}', 'dsfd_ctrl', xp, yc_, PHY_W - SHAVE + 0.024 - 0.024, CTRL_D - SHAVE, orient,
                             kind='ctrl', region='ctrl', domain='hbm')
            svcs[st] = Inst(f'svc_{st}', 'dsfd_svc', xp, ys_, PHY_W - SHAVE + 0.024 - 0.024, SVC_D - SHAVE, orient,
                            kind='svc', region='svc')
            insts += [phys[st], ctrls[st], svcs[st]]
            regions.append(dict(name=f'svc_{st}', kind='svc', rect=[xp, min(yc_, ys_), xp + PHY_W, max(yc_ + CTRL_D, ys_ + SVC_D)]))
    gap_x0, gap_x1 = xs_phy[0] + PHY_W, xs_phy[1]
    for side, name in (('S', 'selector'), ('N', 'collector')):
        w = dn(min(gap_x1 - gap_x0 - 2 * 8.64, 2 * SPINE_W), GX)
        h = up(HUB_MM2[name] * 1e6 / w, GY)
        x = up((gap_x0 + gap_x1) / 2 - w / 2, GX)
        ref = svcs[f'{side}W']
        y = ref.y if side == 'S' else ref.y + ref.h + SHAVE - h
        it = Inst(f'bk_{name}', f'dsfd_bk_{name}', x, y, w - SHAVE, h - SHAVE, kind='band_blk', region='svc')
        insts.append(it)
        hub[name] = it
    # ---- links: W edge (R0 SerDes pins east; UCIe mirrored), E edge mirrored
    rs_, ru_ = real_lef(SERDES_LEF), real_lef(UCIE_LEF)
    links = []
    for side in 'WE':
        stack = [('ucie', ru_), ('serdes', rs_), ('serdes', rs_), ('serdes', rs_)]
        tot = sum(m_['h'] for _, m_ in stack) + 3 * 43.2
        y = up(mid - tot / 2, GY)
        for i, (kind, m_) in enumerate(stack):
            if side == 'W':
                x, orient = x_lw, ('R0' if kind == 'serdes' else 'MY')
            else:
                x, orient = up(x_le + LINK_COL - m_['w'], GX), ('MY' if kind == 'serdes' else 'R0')
            it = Inst(f'lk_{side}{i}', m_['name'], x, y, m_['w'], m_['h'], orient, kind='link', region='link',
                      domain='link')
            insts.append(it)
            links.append(it)
            y = up(y + m_['h'] + 43.2, GY)
    variant = dict(variant, die=DIE_KIND, pairs=PAIRS, bf=BF_PAIRS, nv=NV_PAIRS)
    model = dict(geo=geo, insts=insts, regions=regions, frames=frames, cregions=cregions, fifo_of=fifo_of,
                 hub=hub, phys=phys, ctrls=ctrls, svcs=svcs, links=links, notes=notes, slot_of=slot_of,
                 x_vch=x_vch, mid=mid, variant=variant)
    model['buses'] = buses(model)            # also adds waypoints / hub FIFO slots
    return model


_RANK = {}


def _inorder_rank(nodes, root):
    key = (len(nodes), root)
    if key in _RANK:
        return _RANK[key]
    by = {n[0]: n for n in nodes}
    out, k = {}, [0]

    def walk(x):
        if x.startswith('L'):
            return
        _, a, b = by[x]
        walk(a)
        out[x] = k[0]
        k[0] += 1
        walk(b)
    walk(root)
    _RANK[key] = out
    return out


# ------------------------------------------------------------------------------------------------ nets
def buses(m):
    """[(id, class, bits, [(inst, port)])]; adds forwarded-link waypoints and hub-side FIFO slots to m['insts']."""
    B = []
    insts = m['insts']
    by = {it.name: it for it in insts}
    g = m['geo']
    # ---- field (per frame)
    for r, f in m['frames'].items():
        fb = m['fifo_of'][r]
        cols = next(cr['cols'] for cr in m['cregions'] if cr['fifo'] == fb)
        ci = cols.index(r)
        lanes = {'L': [], 'R': []}
        for p, kind, s, ln in f['elems']:
            if kind == 'NV':
                B.append((f'nv_{p}', 'nv_local', NV_BITS, [(f'e{p}', 'nv'), (f'v{p}', 'nv')]))
            if kind in ('BF', 'NV'):
                lanes['L'].append((p, 'a'))
                lanes['R'].append((p, 'b'))
            else:
                lanes[ln].append((p, ''))
        for ln, seq in lanes.items():
            prev = (fb, f'x{ci}{ln}')
            for j, (p, sub) in enumerate(seq):
                xi = f'x{sub}i' if sub else 'xi'
                xo = f'x{sub}o' if sub else 'xo'
                if j == 0:
                    B.append((f'xe_{r}{ln}', 'x_entry', XI, [prev, (f'e{p}', xi)]))
                else:
                    B.append((f'xc_{p}{sub}', 'x_chain', XO, [prev, (f'e{p}', xi)]))
                prev = (f'e{p}', xo)
            # lane control (17 x bits of xi beyond the chained 266, plus clk/go/rst_n): one multi-pin bus
            B.append((f'xk_{r}{ln}', 'lane_ctl', XCTL + 3,
                      [(fb, f'k{ci}{ln}')] + [(f'e{p}', f'k{sub}' if sub else 'k') for p, sub in seq]))
        for p, kind, s, ln in f['elems']:
            B.append((f'cf_{p}', 'cfg', CFGB, [(f'e{p}', 'cfg')] + [(f'c{p}_{j}', 'rd') for j in range(CFG_PER_PAIR)]))
            B.append((f'ck_{p}', 'cfg_ctl', 14, [(f'c{p}_{j}', 'ctl') for j in range(CFG_PER_PAIR)]))
        # return tree
        nodes, root = f['tree']
        elist = [p for p, *_ in f['elems']]
        ids = {n[0]: j for j, n in enumerate(nodes)}

        def child_ep(cid):
            if cid.startswith('N'):
                return (f'n{r}_{ids[cid]}', 'o'), NODE_W
            li = int(cid[1:])
            return (f'e{elist[li // 2]}', f'r{li % 2}'), RET // 2
        for nid, a, b in nodes:
            for side, c in (('a', a), ('b', b)):
                ep, bits = child_ep(c)
                B.append((f'rt_{r}_{ids[nid]}{side}', 'ret_leaf' if c.startswith('L') else 'ret_tree', bits,
                          [ep, (f'n{r}_{ids[nid]}', side)]))
        B.append((f'rr_{r}', 'ret_root', NODE_W, [(f'n{r}_{ids[root]}', 'o'), (fb, f'r{ci}')]))
    # ---- tier trunks: hub VM -> vertical in VCH -> channel -> FIFO blocks (x out, roots back), waypoints
    vm = m['hub']['vm']
    x_vc = m['x_vch']
    wp_n = [0]

    def waypoint(kind, x, y, chain):
        wp_n[0] += 1
        if kind == 'h':
            it = Inst(f'wh_{chain}_{wp_n[0]}', 'dsfd_stn_h', dn(x, GX), dn(y, GY), STN_H[0] - SHAVE, STN_H[1] - SHAVE,
                      kind='waypoint', region='channel')
        else:
            it = Inst(f'wv_{chain}_{wp_n[0]}', 'dsfd_stn_v', dn(x, GX), dn(y, GY), STN_V[0] - SHAVE, STN_V[1] - SHAVE,
                      kind='waypoint', region='vch')
        insts.append(it)
        by[it.name] = it
        return it
    hub_fifo_y = [m['mid'] - 1800.0]
    hub_fifo_n = [0]

    def hub_fifo(chain):
        """hub-side receive FIFO slot of a chain, packed in the VCH around the VM block"""
        hub_fifo_n[0] += 1
        n = hub_fifo_n[0] - 1
        col, row = n % 4, n // 4
        x = x_vc + 8.64 + col * (MF[0] + 8.64)
        y = vm.y + vm.h / 2 - 700.0 + row * 240.0
        it = Inst(f'mf_{chain}', 'dsfd_mfifo', up(x, GX), up(y, GY), MF[0] - SHAVE, MF[1] - SHAVE, kind='hub_fifo',
                  region='vch')
        insts.append(it)
        by[it.name] = it
        return it
    vstagger = defaultdict(int)
    xroot = [(vm.name, 'xroot')]
    for half in 'WE':
        for t in range(TIERS):
            chain = f'T{half}{t}'
            crs = [cr for cr in m['cregions'] if cr['name'].startswith(f'cr_{half}{t}')]
            cy = g['ch_y'][t] + CH - 4.32 - STN_H[1]
            # vertical leg in the VCH from the VM's y to the channel
            y0 = vm.y + vm.h / 2
            y1 = cy
            legs = []
            dist = abs(y1 - y0)
            nv = int(dist // WAYPOINT_UM)
            vx = x_vc + VCH - 8.64 - STN_V[0] if half == 'E' else x_vc + VCH - 8.64 - STN_V[0]
            for kk in range(1, nv + 1):
                yy = y0 + (kk * WAYPOINT_UM if y1 > y0 else -kk * WAYPOINT_UM)
                vstagger[round(yy / 200)] += 1
                legs.append(waypoint('v', vx - (vstagger[round(yy / 200)] - 1) % 2 * 0, yy + (vstagger[round(yy / 200)] - 1) * 39.0, chain))
            hf = hub_fifo(chain)
            nroots = sum(len(cr['cols']) for cr in crs)
            bits = LANE_X * 2 * 1 + NODE_W * nroots     # one tier bus: 2 lanes of x + every root of the tier
            # x is one broadcast: a single VM x-root bus feeds every tier chain's hub FIFO; the return roots of the
            # tier land in the gather block (capture side), not in the VM
            xroot.append((hf.name, 'hx'))
            B.append((f'tk_{chain}_r', 'trunk', NODE_W * nroots, [(hf.name, 'hr'), (m['hub']['gather'].name, f'r{chain}')]))
            prev = (hf.name, 'f')
            for kk, wv in enumerate(legs):
                B.append((f'tk_{chain}_v{kk}', 'trunk', bits, [prev, (wv.name, 'a')]))
                prev = (wv.name, 'b')
            # horizontal leg in the channel, outward
            xs = g['x_sp'] if half == 'W' else g['x_fe']
            far = max(cr['rect'][2] for cr in crs) if half == 'E' else min(cr['rect'][0] for cr in crs)
            nh = int(abs(far - xs) // WAYPOINT_UM)
            hwps = []
            for kk in range(nh + 1):
                xx = xs + 60.0 + kk * WAYPOINT_UM if half == 'E' else xs - 60.0 - STN_H[0] - kk * WAYPOINT_UM
                if (half == 'E' and xx > far) or (half == 'W' and xx < far):
                    break
                hwps.append(waypoint('h', xx, cy, chain))
            for kk, wh in enumerate(hwps):
                B.append((f'tk_{chain}_h{kk}', 'trunk', bits, [prev, (wh.name, 'w' if half == 'E' else 'e')]))
                prev = (wh.name, 'e' if half == 'E' else 'w')
            # FIFO block taps: from the waypoint nearest each block
            for cr in crs:
                fbi = by[cr['fifo']]
                near = min(hwps, key=lambda w_: abs(w_.x - fbi.x))
                B.append((f'tp_{cr["name"]}', 'trunk_tap', LANE_X * 2 + NODE_W * len(cr['cols']),
                          [(near.name, 't'), (fbi.name, 'x')]))
    B.append(('xroot', 'x_root', 2 * LANE_X, xroot))
    # ---- PHY -> controller (every real PHY signal pin), controller -> scan service, service <-> hub
    npins = len(real_ports()[real_lef(PHY_LEF)['name']]['dfi'])
    for st, ph in m['phys'].items():
        B.append((f'dfi_{st}', 'phy_dfi', npins, [(ph.name, 'dfi'), (m['ctrls'][st].name, 'phy')]))
        B.append((f'rd_{st}', 'hbm_read', HBM_RD_BITS, [(m['ctrls'][st].name, 'rd'), (m['svcs'][st].name, 'rd')]))
    for st, sv in m['svcs'].items():
        side = st[0]
        chain = f'S{st}'
        bits = sum(SVC_HUB_BITS.values())
        # route: service core-facing edge -> band gap -> VCH (vertical) -> hub FIFO -> VM
        y_edge = sv.y + sv.h if side == 'S' else sv.y
        y_ent = g['y_f'] if side == 'S' else g['y_top']
        xk = x_vc + 8.64
        legs = []
        pts = []
        # horizontal along the band edge toward the spine
        x_from = sv.x + sv.w if sv.x < xk else sv.x
        dist_h = abs(xk - x_from)
        yh = y_edge + 60.0 if side == 'S' else y_edge - 60.0 - STN_H[1]
        for kk in range(1, int(dist_h // WAYPOINT_UM) + 1):
            xx = x_from + (kk * WAYPOINT_UM if xk > x_from else -kk * WAYPOINT_UM)
            pts.append(('h', xx, yh + (0 if st[1] == 'W' else 100.0)))
        dist_v = abs((vm.y + vm.h / 2) - y_edge)
        for kk in range(1, int(dist_v // WAYPOINT_UM) + 1):
            yy = y_edge + (kk * WAYPOINT_UM if side == 'S' else -kk * WAYPOINT_UM)
            if (side == 'S' and yy > vm.y - 1000) or (side == 'N' and yy < vm.y + vm.h + 1000):
                break
            vstagger[round(yy / 200)] += 1
            pts.append(('v', xk + 8.64 + 95.04 * (st[1] == 'E'), yy + (vstagger[round(yy / 200)] - 1) * 39.0))
        wps = [waypoint(k_, x_, y_, chain) for k_, x_, y_ in pts]
        hf = hub_fifo(chain)
        prev = (sv.name, 'hub')
        for kk, w_ in enumerate(wps):
            B.append((f'sv_{chain}_{kk}', 'svc_hub', bits, [prev, (w_.name, 'a' if w_.master.endswith('_v') else 'w')]))
            prev = (w_.name, 'b' if w_.master.endswith('_v') else 'e')
        B.append((f'sv_{chain}_f', 'svc_hub', bits, [prev, (hf.name, 'h')]))
        B.append((f'sv_{chain}_vm', 'svc_hub', bits, [(hf.name, 'f'), (vm.name, f's{st}')]))
        # indexer scores -> selector (S band), attention <-> collector (N band)
        B.append((f'ix_{st}', 'band', 512, [(sv.name, 'ix'), (m['hub']['selector'].name, f'i{st}')]))
        B.append((f'co_{st}', 'band', 512, [(sv.name, 'co'), (m['hub']['collector'].name, f'c{st}')]))
    B.append(('sel_vm', 'svc_hub', 512, [(m['hub']['selector'].name, 'vm'), (vm.name, 'sel')]))
    B.append(('col_vm', 'svc_hub', 512, [(m['hub']['collector'].name, 'vm'), (vm.name, 'col')]))
    # ---- hub internal
    hb = m['hub']
    for a_, b_, bits in (('vm', 'su_s', 1024), ('vm', 'su_n', 1024), ('vm', 'hc', 1024), ('vm', 'gather', 512),
                         ('gather', 'capture', 576), ('capture', 'vm', 512), ('collective', 'vm', 512),
                         ('su_s', 'hc', 512), ('su_n', 'hc', 512)):
        B.append((f'hb_{a_}_{b_}', 'hub', bits, [(hb[a_].name, f't_{b_}'), (hb[b_].name, f'f_{a_}')]))
    # ---- links: collective -> each link macro through channel waypoints (tier channels 2 and 3)
    col = hb['collective']
    for i, lk in enumerate(m['links']):
        side = lk.name[3]
        chain = f'K{lk.name[3:]}'
        t = 2 if int(lk.name[4]) < 2 else 3
        cy = g['ch_y'][t] + 4.32 + FIFO_BLK[1] + 4.32 - 0.0
        xs = g['x_sp'] if side == 'W' else g['x_fe']
        far = lk.x + lk.w if side == 'W' else lk.x
        pts = []
        kk = 0
        while True:
            xx = xs - 400.0 - STN_H[0] - kk * WAYPOINT_UM - 64.8 * (int(lk.name[4]) % 2) if side == 'W' \
                else xs + 400.0 + kk * WAYPOINT_UM + 64.8 * (int(lk.name[4]) % 2)
            if (side == 'W' and xx < far + 200) or (side == 'E' and xx > far - 200):
                break
            pts.append(xx)
            kk += 1
        hf = hub_fifo(chain)
        B.append((f'lk_{chain}_c', 'link', LINK_BITS, [(col.name, f'l{lk.name[3:]}'), (hf.name, 'h')]))
        prev = (hf.name, 'f')
        for kk, xx in enumerate(pts):
            w_ = waypoint('h', xx, cy - 0.0 + (0 if int(lk.name[4]) % 2 == 0 else 0), chain)
            w_.master = 'dsfd_stn_l'
            w_.y = dn(cy - 0.0, GY)
            w_.h = STN_H[1] * 1.0 - SHAVE
            B.append((f'lk_{chain}_{kk}', 'link', LINK_BITS, [prev, (w_.name, 'e' if side == 'W' else 'w')]))
            prev = (w_.name, 'w' if side == 'W' else 'e')
        B.append((f'lk_{chain}_m', 'link', LINK_BITS, [prev, (lk.name, 'io')]))
    # ---- clock trunk (option C): PLL (collective block) -> every clock-region root (shielded 3-track net)
    for cr in m['cregions']:
        B.append((f'clk_{cr["name"]}', 'clock_trunk', CLK_BITS, [(col.name, 'pll'), (cr['fifo'], 'ck')]))
    for nm_ in ('svc_SW', 'svc_SE', 'svc_NW', 'svc_NE', 'sp_hc', 'sp_su_s', 'sp_su_n', 'bk_selector', 'bk_collector'):
        B.append((f'clk_{nm_}', 'clock_trunk', CLK_BITS, [(col.name, 'pll'), (nm_, 'ck')]))
    return B


# ------------------------------------------------------------------------------------------------ abstracts
TRK = Q.TRK


def _real_master_bundled(rel, k, ports):
    """A real LEF macro re-expressed as a generated Master with each port's pins bundled k:1, on the real face
    and layer, centred on the real pins' centroid, spanning the real pins' extent."""
    r = real_lef(rel)
    M = Q.Master(r['name'], r['w'], r['h'], r['obs_top'], f'bundled view of real LEF {rel}')
    for port, names in ports.items():
        ls = [r['pins'][n] for n in names]
        layer = ls[0][0]
        xs = [(b[0] + b[2]) / 2 for _, b in ls]
        ys = [(b[1] + b[3]) / 2 for _, b in ls]
        x0, y0, x1, y1 = min(b[0] for _, b in ls), min(b[1] for _, b in ls), max(b[2] for _, b in ls), max(b[3] for _, b in ls)
        if y1 >= r['h'] - 0.5 and layer in ('M5', 'M7', 'M3'):
            face, along, span = 'N', sum(xs) / len(xs), max(xs) - min(xs)
        elif y0 <= 0.5 and layer in ('M5', 'M7', 'M3'):
            face, along, span = 'S', sum(xs) / len(xs), max(xs) - min(xs)
        elif x0 <= 0.5:
            face, along, span = 'W', sum(ys) / len(ys), max(ys) - min(ys)
        else:
            face, along, span = 'E', sum(ys) / len(ys), max(ys) - min(ys)
        nb = max(1, math.ceil(len(names) / k))
        p = TRK.get(layer, TRK['M4'])[1]
        pitch = max(1, int(span / max(1, nb) / (p * k))) if k > 1 else 1
        M.face(port, len(names), face, layer if layer in TRK else 'M4', along, pitch)
    return M


def masters(m, k=1):
    """Generated abstracts (and, for k > 1, bundled views of the real LEFs)."""
    M = {}

    def mk(name, w, h, obs, note):
        M[name] = Q.Master(name, w, h, obs, note)
        return M[name]
    rq = real_lef(Q_LEF)
    qx = {n: (rq['pins'][n][1][0] + rq['pins'][n][1][2]) / 2 for n in rq['pins']}
    bf = mk('dsfd_bf', 1002.888, 157.68 - SHAVE, 7, 'BF-capable pair (1002.89 x 157.68 mapped outline, W4 wake.json); '
            'two x lanes (q-element pin order per lane), cfg and return words as the q element')
    lane_c = sum(qx[n] for n in real_ports()[rq['name']]['xi']) / XI
    for sub, off in (('a', 0.0), ('b', LANE_W)):
        bf.face(f'x{sub}i', XI, 'S', 'M5', lane_c + off, 2)
        bf.face(f'x{sub}o', XO, 'N', 'M5', lane_c + off, 2)
        bf.face(f'k{sub}', XCTL + 3, 'S', 'M5', lane_c + off + 30.0, 2)
    bf.face('cfg', CFGB, 'S', 'M5', 400.0, 2)
    bf.face('r0', RET // 2, 'N', 'M5', 430.0, 2)
    bf.face('r1', RET // 2, 'N', 'M5', 460.0, 2)
    bf.face('nv', NV_BITS, 'N', 'M5', 620.0, 1)       # r5: 760 overlapped lane b's xbo (DRT-0073 on head dies)
    nx = mk('dsfd_nvx', 1002.888, up(NVX_UM2 / 1002.888, GY) - SHAVE, 7, 'NV5 batched draft head extension of an '
            'lm-head pair (+115,775.5 um2 placed, results/uarch/dsrom_l2_head_mac_20261004)')
    nx.face('nv', NV_BITS, 'S', 'M5', 620.0, 1)
    nd = mk('dsfd_node', NODE_FRAME[0] - SHAVE, NODE_FRAME[1] - SHAVE, 4, 'ragged RD64 return node '
            '(ot_v41_retn_w17w10, 2 x 66 in, 66 out; slot = decision storage area 6,704 um2)')
    nd.face('a', NODE_W, 'W', 'M4', 18.0, 2)
    nd.face('b', NODE_W, 'W', 'M4', 40.0, 2)
    nd.face('o', NODE_W, 'N', 'M5', nd.w / 2, 2)
    fb = mk('dsfd_fifo', FIFO_BLK[0] - SHAVE, FIFO_BLK[1] - SHAVE, 4, 'clock-region entry/exit FIFO block: '
            '3 meso FIFO slots (W512 D4) + fan-out to the region\'s column lanes')
    ncol = MAX_GROUP
    for ci in range(ncol):
        for ln in 'LR':
            fb.face(f'x{ci}{ln}', XI, 'N', 'M5', 30.0 + (2 * ci + (ln == 'R')) * 40.0, 1)
            fb.face(f'k{ci}{ln}', XCTL + 3, 'N', 'M5', 30.0 + (2 * ci + (ln == 'R')) * 40.0 + 16.0, 1)
        fb.face(f'r{ci}', NODE_W, 'N', 'M5', 345.0 + ci * 7.0, 1)   # r5: 350 - 8 ci put r3 on k3R (pin_clashes)
    fb.face('x', 2 * LANE_X + NODE_W * ncol, 'E', 'M4', fb.h / 2, 1)
    fb.face('ck', CLK_BITS, 'S', 'M5', fb.w / 2, 1)
    sh = mk('dsfd_stn_h', STN_H[0] - SHAVE, STN_H[1] - SHAVE, 3, 'forwarded-link waypoint (4 x 430.56 um stages), horizontal')
    sv = mk('dsfd_stn_v', STN_V[0] - SHAVE, STN_V[1] - SHAVE, 3, 'forwarded-link waypoint, vertical')
    sl = mk('dsfd_stn_l', STN_H[0] - SHAVE, STN_H[1] - SHAVE, 3, 'link waypoint (1,024-bit SerDes/UCIe bus), horizontal')
    mf = mk('dsfd_mfifo', MF[0] - SHAVE, MF[1] - SHAVE, 4, 'hub-side meso / async FIFO slot(s)')
    ct = mk('dsfd_ctrl', PHY_W - SHAVE, CTRL_D - SHAVE, 7, 'streaming HBM3E controller + async (HBM -> stream) FIFOs')
    sc = mk('dsfd_svc', PHY_W - SHAVE, SVC_D - SHAVE, 7, 'per-stack scan service: 16 attention tiles + pooled '
            'indexer ring reader (quarter of the W4 reservations)')
    ct.face('rd', HBM_RD_BITS, 'N', 'M5', ct.w / 2, 1)
    sc.face('rd', HBM_RD_BITS, 'S', 'M5', sc.w / 2, 1)
    sc.face('hub', sum(SVC_HUB_BITS.values()), 'N', 'M5', sc.w - 400.0, 2)
    sc.face('ix', 512, 'N', 'M5', sc.w - 1200.0, 2)
    sc.face('co', 512, 'N', 'M5', sc.w - 1500.0, 2)
    sc.face('ck', CLK_BITS, 'N', 'M5', 100.0, 1)
    # controller <- PHY: one controller pin above each PHY pin (same x), S face
    ph = real_lef(PHY_LEF)
    if k == 1:
        ct.ports['phy'] = ('xy', [(ph['pins'][n][1][0] + ph['pins'][n][1][2]) / 2 for n in real_ports()[ph['name']]['dfi']])
        ct.order.append('phy')
    else:
        dfi = real_ports()[ph['name']]['dfi']
        ct.face('phy', len(dfi), 'S', 'M5', ct.w / 2, 4)
    for name, it in m['hub'].items():
        b = mk(it.master, it.w, it.h, 7, f'hub reservation slab {name} (W4 source rectangle area)')
        b._slab = name
    _slab_pins(M, m)
    lk_ = [it for it in m['insts'] if it.kind == 'waypoint']
    sh.face('w', 1, 'W', 'M4', sh.h / 2, 1)
    sh.face('e', 1, 'E', 'M4', sh.h / 2, 1)
    sh.face('t', 1, 'S', 'M5', sh.w / 2, 1)
    sl.face('w', LINK_BITS, 'W', 'M4', sl.h / 2, 1)
    sl.face('e', LINK_BITS, 'E', 'M4', sl.h / 2, 1)
    sv.face('a', 1, 'S', 'M5', sv.w / 2, 1)
    sv.face('b', 1, 'N', 'M5', sv.w / 2, 1)
    sv.face('w', 1, 'W', 'M4', sv.h / 2, 1)
    sv.face('e', 1, 'E', 'M4', sv.h / 2, 1)
    mf.face('h', 1, 'E', 'M4', mf.h / 2, 1)
    mf.face('hx', 1, 'N', 'M5', mf.w / 2, 1)
    mf.face('hr', 1, 'S', 'M5', mf.w / 2, 1)
    mf.face('f', 1, 'W', 'M4', mf.h / 2, 1)
    if k > 1:
        _init_real()
        for name, ports in real_ports().items():
            M[name] = _real_master_bundled(REAL_FILES[name], k, ports)
    return M


def _slab_pins(M, m):
    """Faces of the hub slabs and band blocks, chosen by where their peers sit."""
    hb = m['hub']
    vm = M[hb['vm'].master]
    vm.face('xroot', 1, 'E', 'M4', 60.0, 1)
    ga = M[hb['gather'].master]
    for i, ch_ in enumerate(f'T{h}{t}' for h in 'WE' for t in range(TIERS)):
        ga.face(f'r{ch_}', 1, 'E', 'M4', 60.0 + 95.0 * i, 1)
    for i, st in enumerate(('SW', 'SE', 'NW', 'NE')):
        # r7: S-band services exit the lower E face, N-band ones the upper, the HC bus between (r5/r6 packed all
        # four next to t_hc: M4 escape overflow at the VM E face)
        vm.face(f's{st}', 1, 'E', 'M4', (120.0, 220.0, vm.h - 220.0, vm.h - 120.0)[i], 1)
    vm.face('sel', 512, 'S', 'M5', 200.0, 1)
    vm.face('col', 512, 'N', 'M5', 200.0, 1)
    vm.face('t_su_s', 1024, 'S', 'M5', 500.0, 1)
    vm.face('t_su_n', 1024, 'N', 'M5', 500.0, 1)
    vm.face('t_hc', 1024, 'E', 'M4', vm.h / 2, 1)
    vm.face('t_gather', 512, 'S', 'M5', 850.0, 1)
    vm.face('f_capture', 512, 'N', 'M5', 850.0, 1)
    vm.face('f_collective', 512, 'N', 'M5', 1000.0, 1)
    for nm_, faces in (('su_s', [('f_vm', 1024, 'N'), ('t_hc', 512, 'E'), ('ck', 3, 'W')]),
                       ('su_n', [('f_vm', 1024, 'S'), ('t_hc', 512, 'E'), ('ck', 3, 'W')]),
                       ('hc', [('f_vm', 1024, 'W'), ('f_su_s', 512, 'W'), ('f_su_n', 512, 'W'), ('ck', 3, 'E')]),
                       ('gather', [('f_vm', 512, 'N'), ('t_capture', 576, 'N')]),
                       ('capture', [('f_gather', 576, 'S'), ('t_vm', 512, 'S')]),
                       ('collective', [('t_vm', 512, 'S'), ('pll', 3, 'E')])):
        b = M[hb[nm_].master]
        cnt = defaultdict(int)
        for port, bits, face in faces:
            along = (b.h if face in 'EW' else b.w)
            centre = along * (0.25 + 0.25 * cnt[face])
            cnt[face] += 1
            b.face(port, bits, face, 'M4' if face in 'EW' else 'M5', centre, 1)
    col = M[hb['collective'].master]
    for i, lk in enumerate(m['links']):
        side = lk.name[3]
        col.face(f'l{lk.name[3:]}', 1, side, 'M4', 600.0 + 120.0 * (i % 4), 1)   # r5: clear of pll at 0.25 h (DRT-0073)
    for name, peer_face in (('selector', 'N'), ('collector', 'S')):
        b = M[hb[name].master]
        for i, st in enumerate(('SW', 'SE', 'NW', 'NE')):
            b.face(f'{"i" if name == "selector" else "c"}{st}', 512, 'W' if st[1] == 'W' else 'E', 'M4',
                   b.h * (0.3 + 0.4 * (i // 2)), 2)
        b.face('vm', 512, peer_face, 'M5', b.w / 2, 2)
        b.face('ck', 3, peer_face, 'M5', b.w / 2 + 300.0, 1)


def port_widths(m, k):
    w = {}
    by = {it.name: it for it in m['insts']}
    for bid, cls, bits, eps in m['buses']:
        n = bits if k == 1 else max(1, math.ceil(bits / k))
        for inst, port in eps:
            key = (by[inst].master, port)
            w[key] = max(w.get(key, 0), n)
    return w


def pin_rects(mst, k, wmap):
    out = []
    xy = {p: s for p, s in mst.ports.items() if s[0] == 'xy'}
    for port, spec in xy.items():
        n = wmap.get(port, len(spec[1]))
        for i, x in enumerate(spec[1][:n]):
            out.append((f'{port}[{i}]', 'M5', (x - 0.012, 0.0, x + 0.012, 0.192)))
    rest = Q.Master(mst.name, mst.w, mst.h, mst.obs_top, mst.note)
    rest.ports = {p: s for p, s in mst.ports.items() if s[0] != 'xy'}
    rest.order = [p for p in mst.order if p in rest.ports]
    return out + Q.pin_rects(rest, k, wmap)


def lef_text(mst, k, wmap):
    L = [f'# tools/dsrom_s81_fulldie.py abstract: {mst.note}', f'MACRO {mst.name}', '  CLASS BLOCK ;',
         f'  FOREIGN {mst.name} 0 0 ;', f'  SIZE {mst.w:.3f} BY {mst.h:.3f} ;', '  SYMMETRY X Y ;']
    pins = pin_rects(mst, k, wmap)
    for nm, layer, (a, b, c_, d) in pins:
        L += [f'  PIN {nm}', '    DIRECTION INOUT ;', '    USE SIGNAL ;', '    PORT', f'      LAYER {layer} ;',
              f'        RECT {a:.3f} {b:.3f} {c_:.3f} {d:.3f} ;', '    END', f'  END {nm}']
    L.append('  OBS')
    for i in range(1, mst.obs_top + 1):
        L += [f'    LAYER M{i} ;', f'      RECT 0 0 {mst.w:.3f} {mst.h:.3f} ;']
    L += ['  END', f'END {mst.name}', '']
    return '\n'.join(L), len(pins)


def pin_clashes(m, k=1, space=0.024 - 1e-6):
    """Generated pins of one master on one layer that overlap or sit closer than the min spacing (the r4 DRT-0073
    pin-access faults were two ports placed on the same face span)."""
    M, pw = masters(m, k), port_widths(m, k)
    _init_real()
    out = []
    for name, mst in M.items():
        if k == 1 and name in REAL_FILES:
            continue
        rects = sorted(pin_rects(mst, k, {p: pw.get((name, p), 0) for p in mst.order}), key=lambda r: (r[1], r[2][0]))
        by = defaultdict(list)
        for nm, ly, r in rects:
            by[ly].append((nm, r))
        for ly, rs in by.items():
            act = []
            for nm, r in rs:
                act = [a for a in act if a[1][2] + space > r[0]]
                for an, ar in act:
                    if ar[1] < r[3] + space and r[1] < ar[3] + space:
                        out.append((name, ly, an, nm))
                act.append((nm, r))
    return out


def write_lefs(m, k, path):
    M = masters(m, k)
    pw = port_widths(m, k)
    _init_real()
    txt, npins = [], 0
    for name, mst in M.items():
        if k == 1 and name in REAL_FILES:
            continue
        wmap = {p: pw.get((name, p), 0) for p in mst.order}
        for p in mst.order:
            if wmap[p] == 0:
                wmap[p] = 0
        t, n = lef_text(mst, k, wmap)
        txt.append(t)
        npins += n
    Path(path).write_text('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n' + '\n'.join(txt) + 'END LIBRARY\n')
    return npins


def write_netlist(m, k, path, top='dsfd_die', skip=()):
    rp = real_ports() if k == 1 else {}
    by = {it.name: it for it in m['insts']}
    conns = defaultdict(list)
    V = [f'// tools/dsrom_s81_fulldie.py: die-level nets only (k = {k})', f'module {top} ();']
    for bid, cls, bits, eps in m['buses']:
        if cls in skip:
            continue
        n = bits if k == 1 else max(1, math.ceil(bits / k))
        net = f'n_{bid}'
        V.append(f'  wire [{n - 1}:0] {net};')
        for inst, port in eps:
            mst = by[inst].master
            if mst in rp and port in rp[mst]:
                names = rp[mst][port][:n]
                conns[inst].append((names, net))
            else:
                conns[inst].append((port, net, n))
    for it in m['insts']:
        parts = []
        bus_bits = defaultdict(dict)
        for c in conns.get(it.name, []):
            if isinstance(c[0], list):
                names, net = c
                for i, pn in enumerate(names):
                    mm = re.match(r'^(.*)\[(\d+)\]$', pn)
                    if mm:
                        bus_bits[mm.group(1)][int(mm.group(2))] = f'{net}[{i}]'
                    else:
                        parts.append(f'.{Q.esc(pn)}({net}[{i}])')
            else:
                port, net, n = c
                parts.append(f'.{port}({net})')
        for base, bits_ in bus_bits.items():
            hi = max(bits_)
            cat = ', '.join(bits_.get(j, "1'bz") for j in range(hi, -1, -1))
            parts.append(f'.{Q.esc(base)}({{{cat}}})')
        V.append(f'  {it.master} {it.name} (' + ', '.join(parts) + ');')
    V.append('endmodule\n')
    Path(path).write_text('\n'.join(V))


# ------------------------------------------------------------------------------------------------ power model
PAIR_BUSY_W = 0.2296 * 1.2e9 / 1.087e9      # W18 measured busy pair (1.087 GHz, TT 0.7 V) scaled to 1.2 GHz
FLOP_CLK_W = (0.0270 + 0.0237) / 31000 * 1.2 / 1.087   # W18 pair: flop clock pins + clock tree over ~31k flops
POWER = dict(
    q=(PAIR_BUSY_W, 'MEASURED W18 routed pair busy 229.6 mW at 1.087 GHz, scaled to 1.2 GHz'),
    bf=(2 * PAIR_BUSY_W, 'ASSUMED 2 x q (two x lanes, BF16 datapath)'),
    bf_nv=(2 * PAIR_BUSY_W, 'ASSUMED as bf (the lm-head pair before its NV5 extension)'),
    nvx=(57887.7 * PAIR_BUSY_W / 63377.3, 'DERIVED NV5 delta cell area 57,887.7 um2 x the measured q pair W per cell '
         'um2 (0.2535 W / 63,377 um2 routed census)'),
    cfg=(0.005, 'ASSUMED 5 mW per cfg ROM read per cycle (weight-ROM macro clock 16 mW x 72/274 width)'),
    node=(9143 * FLOP_CLK_W * 1.5, 'DERIVED 9,143 flops x W18 per-flop clock (pins + tree) x 1.5 for data'),
    fifo_blk=(0.02, 'ASSUMED 3 meso FIFO slots + fan-out'),
    waypoint=(0.01, 'ASSUMED 4 forwarded stages of the chain width'),
    hub_fifo=(0.008, 'ASSUMED one FIFO slot'),
)
DENS = dict(   # W/mm2 for reservation slabs (peak in-phase)
    sp_su_s=1.05, sp_su_n=1.05, sp_hc=1.05, sp_vm=1.05, sp_gather=0.385, sp_capture=0.385, sp_collective=0.385,
    ctrl=3.924, svc=1.25, band_blk=1.05)
DENS_SRC = ('hub/selector/collector logic 1.05 and service 0.385 W/mm2: Qwen full-die REGION_W_PER_MM2 classes '
            '(ASSUMED); controller 3.924 W/mm2 (Qwen strip/ctrl class, ASSUMED); scan service 1.25 W/mm2 ASSUMED '
            '(logic 1.05 + indexer at the L20 scan rate: model idx MACs 49.4 uJ over the 4.97 us reader time = 9.9 W '
            'on 7.5 mm2); PHY and SerDes/UCIe on their own supplies (no core-grid load)')


def inst_power(it):
    if it.kind in POWER:
        return POWER[it.kind][0]
    key = it.name if it.name in DENS else it.kind
    if key in DENS:
        return DENS[key] * (it.w + SHAVE) * (it.h + SHAVE) / 1e6
    return 0.0


def scan_die_power():
    """Scan-die (L20 index scan) power: static ICG ledger + dynamic at the saturated AR point.  The 28-stage priced
    graph (uarch_model) gives the L20 stage's die energy; S81 spreads 40 layers over 81 stages, so the scan die
    holds the L20 index scan, its attention and about half of L20's field work."""
    dec = json.loads((ROOT / DECISION).read_text())
    s81 = dec['priced']['S81_ragged_RD64_replicated']
    sat = 80833.5
    layer_die_w = 50.196
    e_field_l20, e_scan = 0.4972e-3, (0.0494 + 0.1146 + 0.0069) * 1e-3      # J/token on one rank die (graph)
    dyn = (0.5 * e_field_l20 + e_scan) * sat
    peak_field = 1898 * PAIR_BUSY_W + 519 * 2 * PAIR_BUSY_W
    return dict(stages=s81['area']['stages'], pairs=s81['area']['pairs'], static_icg_w=layer_die_w,
                dynamic_saturated_w=round(dyn, 1), total_saturated_w=round(layer_die_w + dyn, 1),
                cooling_limit_w=474.56, fits_cooling=layer_die_w + dyn <= 474.56,
                all_pairs_busy_in_phase_w=round(peak_field, 1),
                basis='static: tools/ds_energy_silicon_authoritative.LAYER_DIE_W (ICG ledger, 30.6 W of it SerDes); '
                      'dynamic: uarch_model._v41_graph(proposal) L20 per-die energy (field 0.497, idx MAC 0.049, HBM IF '
                      '0.115, attention 0.007 mJ/token) x head-bound saturated 80,833.5 tok/s; '
                      'IR windows use the local peak in-phase densities below, not this average')


# ------------------------------------------------------------------------------------------------ writers
def legality(m):
    """Python overlap / containment screen (exact rectangles, 200 um bins)."""
    grid = defaultdict(list)
    ov, out = [], []
    W, H = DIE
    for i, it in enumerate(m['insts']):
        x0, y0, x1, y1 = it.box()
        if x0 < -1e-6 or y0 < -1e-6 or x1 > W + 1e-6 or y1 > H + 1e-6:
            out.append(it.name)
        keys = [(a, b) for a in range(int(x0 // 200), int(x1 // 200) + 1) for b in range(int(y0 // 200), int(y1 // 200) + 1)]
        seen = set()
        for kk in keys:
            for j in grid[kk]:
                if j in seen:
                    continue
                seen.add(j)
                o = m['insts'][j]
                a0, b0, a1, b1 = o.box()
                if a0 < x1 - 1e-6 and x0 < a1 - 1e-6 and b0 < y1 - 1e-6 and y0 < b1 - 1e-6:
                    ov.append((o.name, it.name))
            grid[kk].append(i)
    return dict(instances=len(m['insts']), overlaps=len(ov), overlap_examples=ov[:20], outside=len(out),
                outside_examples=out[:20])


def write_def_floorplan(m, path):
    W, H = DIE
    o = {'R0': 'N', 'MY': 'FN', 'MX': 'FS', 'R180': 'S'}
    d = ['VERSION 5.8 ;', 'DIVIDERCHAR "/" ;', 'BUSBITCHARS "[]" ;', 'DESIGN dsfd_die ;',
         'UNITS DISTANCE MICRONS 1000 ;', f'DIEAREA ( 0 0 ) ( {round(W * 1000)} {round(H * 1000)} ) ;']
    regs = [(cr['name'], cr['rect']) for cr in m['cregions']] + [(r['name'], r['rect']) for r in m['regions']
                                                                  if r['kind'] in ('hub', 'svc')]
    d.append(f'REGIONS {len(regs)} ;')
    for n, (a, b, c, e) in regs:
        d.append(f'- {n} ( {round(a * 1000)} {round(b * 1000)} ) ( {round(c * 1000)} {round(e * 1000)} ) + TYPE GUIDE ;')
    d.append('END REGIONS')
    d.append(f'COMPONENTS {len(m["insts"])} ;')
    for it in m['insts']:
        d.append(f'- {it.name} {it.master} + FIXED ( {round(it.x * 1000)} {round(it.y * 1000)} ) {o[it.orient]} ;')
    d.append('END COMPONENTS')
    d += ['END DESIGN', '']
    Path(path).write_text('\n'.join(d))


def svg(m, path, scale=0.03):
    W, H = DIE
    s = scale
    col = dict(q='#9ecae1', bf='#3182bd', cfg='#deebf7', node='#fd8d3c', fifo_blk='#e6550d', waypoint='#08519c',
               hub_fifo='#a63603', hub='#74c476', phy='#756bb1', ctrl='#9e9ac8', svc='#fdd0a2', band_blk='#c7e9c0',
               link='#fee391')
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W * s:.0f}" height="{H * s:.0f}" viewBox="0 0 {W * s:.1f} {H * s:.1f}">',
         f'<rect width="{W * s:.1f}" height="{H * s:.1f}" fill="#fff" stroke="#000"/>']
    for cr in m['cregions']:
        a, b, c, e = cr['rect']
        o.append(f'<rect x="{a * s:.1f}" y="{(H - e) * s:.1f}" width="{(c - a) * s:.1f}" height="{(e - b) * s:.1f}" '
                 f'fill="none" stroke="#e6550d" stroke-dasharray="4 2" stroke-width="0.6"/>')
    for it in m['insts']:
        if it.kind == 'cfg':
            continue
        o.append(f'<rect x="{it.x * s:.2f}" y="{(H - it.y - it.h) * s:.2f}" width="{max(it.w * s, 0.3):.2f}" '
                 f'height="{max(it.h * s, 0.3):.2f}" fill="{col.get(it.kind, "#ccc")}" stroke="#555" stroke-width="0.05"/>')
    o.append('</svg>\n')
    Path(path).write_text('\n'.join(o))


def plan_record(m):
    kinds, area = defaultdict(int), defaultdict(float)
    for it in m['insts']:
        kinds[it.kind] += 1
        area[it.kind] += (it.w + (SHAVE if it.kind not in ('q', 'cfg', 'phy', 'link') else 0)) * \
            (it.h + (SHAVE if it.kind not in ('q', 'cfg', 'phy', 'link') else 0)) / 1e6
    cls = defaultdict(lambda: dict(buses=0, wires=0))
    for bid, c, bits, eps in m['buses']:
        cls[c]['buses'] += 1
        cls[c]['wires'] += bits
    g = m['geo']
    frame_mm2 = ROOTS * COL_W * SLOTS * SLOT_H / 1e6
    dec = json.loads((ROOT / DECISION).read_text())['priced']['S81_ragged_RD64_replicated']['area']
    placed = sum(area.values())
    stg = trunk_stages(m)
    return dict(
        schema='opentallas.dsrom-s81-fulldie.floorplan.v1', tool='tools/dsrom_s81_fulldie.py',
        tool_sha256=sha('tools/dsrom_s81_fulldie.py'),
        sources_sha256={p: sha(p) for p in (DECISION, Q_LEF, CFG_LEF, FIXED, CONTRACT, PHY_LEF, SERDES_LEF, UCIE_LEF,
                                            MESO, SNAP_LIB, 'tools/qwen_rom_fulldie.py')},
        die=dict(w_um=DIE[0], h_um=DIE[1], mm2=round(DIE[0] * DIE[1] / 1e6, 3), reticle_mm2=858.0,
                 decision_priced_mm2=dec['die_mm2'], decision_terms_mm2=dec),
        instances=dict(kinds), area_mm2_by_kind={k: round(v, 3) for k, v in area.items()},
        placed_footprint_mm2=round(placed, 2),
        field=dict(frames=ROOTS, frame_um=[COL_W, SLOTS * SLOT_H], frames_mm2=round(frame_mm2, 2),
                   slot_um=[2 * LANE_W, SLOT_H], slots=SLOTS, columns_per_half=COLS, tiers=TIERS,
                   pairs=PAIRS, bf=BF_PAIRS, nv=NV_PAIRS, q=PAIRS - BF_PAIRS - NV_PAIRS, cfg_macros=PAIRS * CFG_PER_PAIR,
                   return_nodes=sum(len(f['tree'][0]) for f in m['frames'].values()),
                   decision_field_plus_return_mm2=round(dec['variable'] + dec['increments'] + dec['return_mm2'], 2),
                   frame_padding_note='every frame has 12 slots; frames with 18 pairs leave one slot empty'),
        geometry={k: (round(v, 3) if isinstance(v, float) else v) for k, v in g.items() if k != 'col_x'},
        clock_regions=dict(option='C (results/uarch/rom_die_clocking_decision_20261003)', count=len(m['cregions']) + 13,
                           field=len(m['cregions']), max_extent_um=round(max(max(c['rect'][2] - c['rect'][0], c['rect'][3] - c['rect'][1]) for c in m['cregions']), 1),
                           field_fifo_blocks=sum(1 for it in m['insts'] if it.kind == 'fifo_blk'),
                           hub_fifo_slots=sum(1 for it in m['insts'] if it.kind == 'hub_fifo'),
                           fifo_area_mm2=round(area['fifo_blk'] + area['hub_fifo'], 3),
                           other=['spine (3, <= 5.25 mm each, per-region CTS)', 'S/N service bands (2 per stack)',
                                  'HBM controllers (async, PHY clock)', 'link macros (own clocks)']),
        bus_classes=dict(cls), trunk_stages=stg, scan_die_power=scan_die_power(),
        power_model=dict(per_instance={k: dict(w=round(v[0], 5), basis=v[1]) for k, v in POWER.items()},
                         densities_w_mm2=DENS, densities_basis=DENS_SRC),
        notes=m['notes'])


def trunk_stages(m):
    """Forwarded-link lengths of the longest die-level paths (Manhattan along the built route: VM -> VCH -> tier
    channel -> region FIFO -> column base; the column chain itself is the element's own registered forward) at the
    corridor-gate closing pitch (430.56 um) and at the model's SS reach (504 um, uarch_model.SS_REACH_UM)."""
    by = {it.name: it for it in m['insts']}
    vm = m['hub']['vm']
    g = m['geo']
    vx, vy = m['x_vch'] + VCH / 2, vm.y + vm.h / 2
    rows = []
    for r, f in m['frames'].items():
        fb = by[m['fifo_of'][r]]
        cy = g['ch_y'][f['tier']] + CH / 2
        fx = fb.x + fb.w / 2
        trunk = abs(vm.x + vm.w - vx) + abs(cy - vy) + abs(fx - vx)
        inreg = abs((f['x'] + LANE_W) - fx) + abs(f['y'] - cy)
        rows.append((trunk + inreg, trunk, inreg, r))
    far = max(rows)
    sv = max(abs((s_.y + s_.h / 2) - vy) + abs((s_.x + s_.w / 2) - vx) for s_ in m['svcs'].values())
    col = m['hub']['collective']
    lk = max(abs((l_.x + l_.w / 2) - (col.x + col.w / 2)) + abs((l_.y + l_.h / 2) - (col.y + col.h / 2)) for l_ in m['links'])
    out = dict(farthest_frame=far[3], vm_to_farthest_column_base_um=round(far[0], 1),
               of_which_trunk_to_fifo_um=round(far[1], 1), of_which_in_region_um=round(far[2], 1),
               column_chain_um=round(SLOTS * SLOT_H, 1), service_to_vm_um=round(sv, 1), collective_to_link_um=round(lk, 1))
    for reach in (LINK_STAGE_UM, 504.0):
        tag = f'stages_at_{int(reach)}'
        out[tag] = dict(field_one_way=math.ceil(far[1] / reach) + math.ceil(far[2] / reach),
                        field_round_trip=2 * (math.ceil(far[1] / reach) + math.ceil(far[2] / reach)),
                        service_to_vm=math.ceil(sv / reach), collective_to_link=math.ceil(lk / reach))
    out['model_reference'] = dict(expert_wire_round_trip_at_504=76, collective_to_serdes=48, collective_to_ucie=37,
                                  index_keys=39, src='tools/uarch_model.DIE_OLD / W18B_EXPERT_WIRE (W18b measured, '
                                  'old 815 mm2 die organisation)')
    out['option_C_crossing_cycles'] = 'each field matvec pays one entry and one exit meso FIFO (2 periods each, ' \
        'results/uarch/meso_fifo_20261004 verdict: crossing delta mean 2.01 periods) -- the +661-cycle term of ' \
        'rom_die_clocking_decision_20261003, unchanged by this floorplan'
    return out


# ------------------------------------------------------------------------------------------------ case (a): real
def case_real(m, work):
    work.mkdir(parents=True, exist_ok=True)
    npins = write_lefs(m, 1, work / 'elements.lef')
    _init_real()
    import gzip
    (work / 'q_elem.lef').write_text(_lef_text(Q_LEF))
    for rel, nm in ((CFG_LEF, 'cfg.lef'), (PHY_LEF, 'phy.lef'), (SERDES_LEF, 'serdes.lef'), (UCIE_LEF, 'ucie.lef')):
        (work / nm).write_text(_lef_text(rel))
    (work / 'snap.tcl').write_text((ROOT / SNAP_LIB).read_text())
    write_netlist(m, 1, work / 'die.v')
    W, H = DIE
    # ot_mts::place rescans every placed macro per call (O(n^2): 8k of 24k instances in 31 min); the floorplan is
    # built on the snap lattice, so snap each origin (snap_origin, no neighbour scan) and let the one sweep-line
    # overlap check below prove the result legal; any snap move is logged as OT_MTS_PLACE as before.
    pl = ['set _blk [ord::get_db_block]', 'set _dbu [ot_mts::get_dbu]', 'set _sg [ot_mts::site_grid]',
          'proc fplace {nm x y o} { global _blk _dbu _sg; set i [$_blk findInst $nm]; set m [$i getMaster]',
          '  lassign $_sg gx gw gy gh; set r [ot_mts::rule $m $o]',
          '  lassign [dict get $r x] Px Sx; lassign [dict get $r y] Py Sy',
          '  set px [expr {double([ot_mts::snap_axis [expr {round($x*$_dbu)}] $gx $gw $Px $Sx "$nm x"])/$_dbu}]',
          '  set py [expr {double([ot_mts::snap_axis [expr {round($y*$_dbu)}] $gy $gh $Py $Sy "$nm y"])/$_dbu}]',
          '  $i setOrient $o; $i setLocation [expr {round($px*$_dbu)}] [expr {round($py*$_dbu)}]; $i setPlacementStatus FIRM',
          '  if {abs($px-$x) > 1e-6 || abs($py-$y) > 1e-6} { puts [format "OT_MTS_PLACE %s %s %s requested (%.3f, %.3f) '
          'placed (%.3f, %.3f)" $nm [$m getName] $o $x $y $px $py] } }']
    pl += [f'fplace {it.name} {it.x:.3f} {it.y:.3f} {it.orient}' for it in m['insts']]
    (work / 'place.tcl').write_text('\n'.join(pl) + '\n')
    tcl = f"""# case (a): real-technology S81 die floorplan, macro legality, on-track assert, pin access
proc mem {{tag}} {{ set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {{VmRSS:\\s+(\\d+)}} $s -> r; puts "OTMEM $tag [expr {{$r/1024}}] MB [clock seconds]" }}
read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f {{q_elem.lef cfg.lef phy.lef serdes.lef ucie.lef elements.lef}} {{ read_lef /work/$f }}
read_verilog /work/die.v
link_design dsfd_die
mem linked
initialize_floorplan -die_area {{0 0 {W:.3f} {H:.3f}}} -core_area {{0 0 {W:.3f} {H:.3f}}} -site asap7sc7p5t
source {PLAT}/openRoad/make_tracks.tcl
set ::env(MAKE_TRACKS) {PLAT}/openRoad/make_tracks.tcl
source /work/snap.tcl
mem floorplan
set t0 [clock seconds]
source /work/place.tcl
puts "OT_TIME place_s=[expr {{[clock seconds]-$t0}}]"
mem placed
set blk [ord::get_db_block]
set boxes {{}}
foreach inst [$blk getInsts] {{
  set bb [$inst getBBox]
  lappend boxes [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax] [$inst getName]]
}}
set boxes [lsort -integer -index 0 $boxes]
set n [llength $boxes]; set ov 0; set out 0
set dw [[$blk getDieArea] xMax]; set dh [[$blk getDieArea] yMax]
set active {{}}
foreach b $boxes {{
  lassign $b x0 y0 x1 y1 nm
  if {{$x0 < 0 || $y0 < 0 || $x1 > $dw || $y1 > $dh}} {{ incr out; if {{$out < 20}} {{ puts "OT_OUTSIDE $nm" }} }}
  set keep {{}}
  foreach a $active {{
    lassign $a ax0 ay0 ax1 ay1 an
    if {{$ax1 > $x0}} {{
      lappend keep $a
      if {{$ay0 < $y1 && $y0 < $ay1}} {{ incr ov; if {{$ov < 50}} {{ puts "OT_OVERLAP $an $nm" }} }}
    }}
  }}
  lappend keep $b
  set active $keep
}}
puts "OT_LEGAL instances=$n overlaps=$ov outside=$out"
write_def /work/floorplan_placed.def
mem def
if {{[catch {{ot_mts::assert_on_track -label s81fulldie}} err]}} {{ puts "OT_ASSERT FAIL $err" }} else {{ puts "OT_ASSERT PASS" }}
mem assert
set t0 [clock seconds]
set_routing_layers -signal M2-M9
if {{[catch {{pin_access -verbose 1}} err]}} {{ puts "OT_PA FAIL $err" }} else {{ puts "OT_PA DONE" }}
puts "OT_TIME pa_s=[expr {{[clock seconds]-$t0}}]"
mem pa
write_db /work/floorplan.odb
"""
    (work / 'run.tcl').write_text(tcl)
    man = dict(case='a', instances=len(m['insts']), generated_pins=npins, nets_bits=sum(b[2] for b in m['buses']),
               variant=m['variant'])
    (work / 'manifest.json').write_text(json.dumps(man, indent=1))
    return man


# ------------------------------------------------------------------------------------------------ case (b): GRT
VIA_OBS = 0.05


def case_grt(m, work, k, tag, iters, cov, empty=False):
    from chip_assembly import v41_die as VD
    work.mkdir(parents=True, exist_ok=True)
    npins = write_lefs(m, k, work / 'elements.lef')
    (work / 'tech.lef').write_text(VD.bundled_tech_lef(k))
    mm = dict(m)
    if empty:      # one short local bus only: GRT builds no GCell grid without a net
        mm['buses'] = [next(b_ for b_ in m['buses'] if b_[1] == 'cfg_ctl')]
    write_netlist(mm, k, work / 'die.v')
    W, H = DIE
    tracks = [f'make_tracks {n} -x_offset {off * k:.3f} -x_pitch {p * k:.3f} -y_offset {off * k:.3f} -y_pitch {p * k:.3f}'
              for n, d, p, wd, sp, off in VD.ASAP7_LAYERS]
    place = [f'place_inst -name {it.name} -location {{{it.x:.3f} {it.y:.3f}}} -orientation {it.orient} -status FIRM'
             for it in m['insts']]
    adj = []
    for ln in ('M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 'M9'):
        a = 1.0 if ln in ('M2', 'M3', 'M4', 'M5') else (VIA_OBS + 2 * cov['field'] if ln in ('M8', 'M9') else VIA_OBS)
        adj.append(f'set_global_routing_layer_adjustment {ln} {a:.4f}')
    for r in m['regions']:
        kind = r['kind']
        if kind in ('field', 'channel'):
            continue
        c = cov.get(kind)
        if c is None:
            continue
        x0, y0, x1, y1 = r['rect']
        for ln in ('M8', 'M9'):
            adj.append(f'set_global_routing_region_adjustment {{{x0:.3f} {y0:.3f} {x1:.3f} {y1:.3f}}} -layer {ln} '
                       f'-adjustment {VIA_OBS + 2 * c:.4f}')
    tcl = f"""# case (b): bundled (k = {k}) global route of every S81 die-level net{' (EMPTY baseline: no nets)' if empty else ''}
proc mem {{tag}} {{ set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {{VmRSS:\\s+(\\d+)}} $s -> r; puts "OTMEM $tag [expr {{$r/1024}}] MB [clock seconds]" }}
read_lef /work/tech.lef
read_lef /work/elements.lef
read_verilog /work/die.v
link_design dsfd_die
initialize_floorplan -die_area {{0 0 {W:.3f} {H:.3f}}} -core_area {{0 0 {W:.3f} {H:.3f}}} -site bsite
{chr(10).join(tracks)}
{chr(10).join(place)}
mem placed
{chr(10).join(adj)}
set_routing_layers -signal M2-M9
set t0 [clock seconds]
global_route -verbose -allow_congestion -congestion_iterations {iters} -congestion_report_file /work/grt_congestion.rpt
puts "OT_TIME grt_s=[expr {{[clock seconds]-$t0}}]"
mem grt
report_wire_length -net * -global_route -file /work/wirelength.csv
"""
    tcl += r"""
set blk [ord::get_db_block]
set out [open /work/gcell_usage.txt w]
set grid [$blk getGCellGrid]
set gx [$grid getGridX]; set gy [$grid getGridY]
puts $out "GRIDX [join $gx ,]"
puts $out "GRIDY [join $gy ,]"
set tech [ord::get_db_tech]
foreach ln {M2 M3 M4 M5 M6 M7 M8 M9} {
  set layer [$tech findLayer $ln]
  set nx [llength $gx]; set ny [llength $gy]
  for {set j 0} {$j < $ny} {incr j 4} {
    set row {}
    for {set i 0} {$i < $nx} {incr i 4} {
      set cap 0; set use 0
      for {set jj $j} {$jj < min($j+4,$ny)} {incr jj} {
        for {set ii $i} {$ii < min($i+4,$nx)} {incr ii} {
          set cap [expr {$cap + [$grid getCapacity $layer $ii $jj]}]
          set use [expr {$use + [$grid getUsage $layer $ii $jj]}]
        }
      }
      lappend row "$cap/$use"
    }
    puts $out "L $ln $j [join $row { }]"
  }
}
close $out
mem done
"""
    (work / 'run.tcl').write_text(tcl)
    man = dict(case='b', tag=tag, bundle_k=k, congestion_iterations=iters, empty_baseline=empty,
               instances=len(m['insts']), bundle_pins=npins,
               bundle_nets=0 if empty else sum(max(1, math.ceil(b[2] / k)) for b in m['buses']),
               wires=0 if empty else sum(b[2] for b in m['buses']), coverage=cov, variant=m['variant'],
               adjustment=dict(M2_M5=1.0, M6_M7=VIA_OBS, M8_M9_field=VIA_OBS + 2 * cov['field'],
                               regions={k_: VIA_OBS + 2 * v for k_, v in cov.items()}))
    (work / 'manifest.json').write_text(json.dumps(man, indent=1))
    return man


# ------------------------------------------------------------------------------------------------ case (c): IR
BUMP_PITCH, BUMP_SIZE, VDD_V = 45.0, 20.0, 0.7
COV = dict(field=0.0439, hub=0.025, svc=0.1639, channel=0.0439)    # per-net M8/M9 coverage (Qwen r2 classes)


def windows(m):
    g = m['geo']
    f = m['frames']
    # field: W half, tier 2, columns 3..5 (one clock region) with its channel and the next region's edge
    xa = g['col_x']('W', 5) - 300.0
    w = {
        'field': (xa, g['ch_y'][2] - 100.0, xa + 3 * COL_PITCH + 600.0, g['tier_y'][2] + 2700.0),
        'field_bf': None,
        'spine': (g['x_sp'] - 400.0, m['mid'] - 1400.0, g['x_fe'] + 400.0, m['mid'] + 1400.0),
        'band_s': (m['svcs']['SW'].x + 2500.0, 0.0, m['svcs']['SW'].x + 5500.0, m['svcs']['SW'].y + SVC_D + 900.0),
    }
    # the frame with the most BF pairs
    rb = max(f, key=lambda r: sum(1 for e in f[r]['elems'] if e[1] == 'BF'))
    fr = f[rb]
    w['field_bf'] = (fr['x'] - 1000.0, fr['y'] - 300.0, fr['x'] + COL_W + 1000.0, fr['y'] + 2600.0)
    if NV_PAIRS:
        rn = max(f, key=lambda r: sum(1 for e in f[r]['elems'] if e[1] == 'NV'))
        fr = f[rn]
        w['field_nv'] = (fr['x'] - 1000.0, fr['y'] - 300.0, fr['x'] + COL_W + 1000.0, fr['y'] + 2600.0)
    return {k: tuple(round(v, 3) for v in r) for k, r in w.items()}


def kind_at(m, x, y):
    for r in m['regions']:
        a, b, c, e = r['rect']
        if a <= x < c and b <= y < e:
            if r['kind'] == 'svc':
                return 'svc'
            if r['kind'] == 'hub':
                return 'hub'
    for it in m['phys'].values():
        if it.x <= x < it.x + it.w and it.y <= y < it.y + it.h:
            return 'phy'
    for it in m['links']:
        if it.x <= x < it.x + it.w and it.y <= y < it.y + it.h:
            return 'phy'
    return 'field'


def case_ir(m, work, window, cov, peak=True, vdd_pitch=None, align=True, signal_bumps_phy=True, scale=1.0):
    work.mkdir(parents=True, exist_ok=True)
    x0, y0, x1, y1 = windows(m)[window]
    x0, y0 = max(0.0, dn(x0, GX)), max(0.0, dn(y0, GY))
    x1, y1 = min(DIE[0], x1), min(DIE[1], y1)
    W, H = round(x1 - x0, 3), round(y1 - y0, 3)
    vp = vdd_pitch or BUMP_PITCH / math.sqrt(0.5)       # every core bump a power bump: VDD and VSS each 1/2

    def pitch(c):
        raw = dn(0.48 / c, 0.160)
        if not align:
            return raw
        n = math.ceil(vp / raw - 1e-9)
        n += (n % 2 == 0)
        return round(vp / n, 4)
    sites = {'VDD': [], 'VSS': []}
    for net, off in (('VDD', vp / 2), ('VSS', 0.0)):
        yy = off if off > 0 else vp
        while yy < H - 1.0:
            xx = off if off > 0 else vp
            while xx < W - 1.0:
                if not (signal_bumps_phy and kind_at(m, x0 + xx, y0 + yy) == 'phy'):
                    sites[net].append((round(xx, 3), round(yy, 3)))
                xx += vp
            yy += vp
    R = 5.0
    rx, ry = int(math.ceil(W / R)), int(math.ceil(H / R))
    kinds_r = [[kind_at(m, x0 + (i + 0.5) * R, y0 + (j + 0.5) * R) for i in range(rx)] for j in range(ry)]
    raster = [[pitch(cov.get(k_, cov['svc'])) for k_ in row] for row in kinds_r]
    pitches = sorted({v for row in raster for v in row})

    def pat(xx, yy):
        return raster[min(ry - 1, max(0, int(yy / R)))][min(rx - 1, max(0, int(xx / R)))]

    def lines(p, span):
        out = []
        v = ((vp / 2) % p) if align else 1.0
        while v < span - 0.5:
            out.append(('VDD', round(v, 3)))
            if v + p / 2 < span - 0.5:
                out.append(('VSS', round(v + p / 2, 3)))
            v += p
        return out

    def runs(fixed, axis, p):
        segs, start = [], None
        n = ry if axis == 'y' else rx
        for t in range(n + 1):
            ok = t < n and (pat(fixed, (t + 0.5) * R) if axis == 'y' else pat((t + 0.5) * R, fixed)) == p
            if ok and start is None:
                start = t * R
            if not ok and start is not None:
                segs.append((start, min(t * R, H if axis == 'y' else W)))
                start = None
        return segs
    s9, s8, vias = [], [], []
    for p in pitches:
        xl, yl = lines(p, W), lines(p, H)
        for net, xx in xl:
            for (a_, b_) in runs(xx, 'y', p):
                s9.append((net, 'M9', xx - 0.24, a_, xx + 0.24, b_))
        for net, yy in yl:
            for (a_, b_) in runs(yy, 'x', p):
                s8.append((net, 'M8', a_, yy - 0.24, b_, yy + 0.24))
        ys_by_net = {'VDD': [y for n_, y in yl if n_ == 'VDD'], 'VSS': [y for n_, y in yl if n_ == 'VSS']}
        for net, xx in xl:
            for yy in ys_by_net[net]:
                if pat(xx, yy) == p:
                    vias.append((net, xx, yy))
    # power raster: instance power spread over its footprint (peak in-phase), 20 um load cells
    cell = 20.0
    nx, ny = int(W // cell), int(H // cell)
    pw = [[0.0] * nx for _ in range(ny)]
    tot_by_kind = defaultdict(float)
    for it in m['insts']:
        p_ = inst_power(it) * (1.0 if peak else 0.25) * scale
        if p_ <= 0:
            continue
        a, b, c, e = it.x - x0, it.y - y0, it.x + it.w - x0, it.y + it.h - y0
        if c <= 0 or e <= 0 or a >= nx * cell or b >= ny * cell:
            continue
        dens = p_ / (it.w * it.h)
        for j in range(max(0, int(b // cell)), min(ny, int(e // cell) + 1)):
            for i in range(max(0, int(a // cell)), min(nx, int(c // cell) + 1)):
                ov = max(0.0, min(c, (i + 1) * cell) - max(a, i * cell)) * max(0.0, min(e, (j + 1) * cell) - max(b, j * cell))
                if ov > 0:
                    pw[j][i] += dens * ov
                    tot_by_kind[it.kind] += dens * ov
    by_net = {'VDD': {}, 'VSS': {}}
    for (nn, ly, a_, b_, c_, e_) in s8:
        by_net[nn].setdefault(round((b_ + e_) / 2, 3), []).append((a_, c_))
    ys_sorted = {nn: sorted(v) for nn, v in by_net.items()}
    comps, power, lefs, kinds = [], {}, {}, {}
    missing = 0
    for j in range(ny):
        for i in range(nx):
            cx0, cy0 = i * cell, j * cell
            pins = {}
            for nn in ('VDD', 'VSS'):
                ys = ys_sorted[nn]
                lo = bisect.bisect_left(ys, cy0 + 0.3)
                best = None
                for t in range(lo, len(ys)):
                    yy = ys[t]
                    if yy > cy0 + cell - 0.3:
                        break
                    if any(r0 <= cx0 + 0.6 and r1 >= cx0 + cell - 0.6 for r0, r1 in by_net[nn][yy]):
                        if best is None or abs(yy - (cy0 + cell / 2)) < abs(best - (cy0 + cell / 2)):
                            best = yy
                pins[nn] = best
            if pins['VDD'] is None or pins['VSS'] is None:
                missing += 1
                continue
            key = (round(pins['VDD'] - cy0, 3), round(pins['VSS'] - cy0, 3))
            mn = f'qir_load_{int(key[0] * 1000)}_{int(key[1] * 1000)}'
            if mn not in lefs:
                pv, ps_ = key
                lefs[mn] = '\n'.join([f'MACRO {mn}', '  CLASS BLOCK ;', f'  FOREIGN {mn} 0 0 ;', '  SYMMETRY X Y ;',
                                      f'  SIZE {cell:.3f} BY {cell:.3f} ;',
                                      '  PIN VDD', '    DIRECTION INOUT ;', '    USE POWER ;', '    PORT', '      LAYER M8 ;',
                                      f'        RECT 0.600 {pv - 0.24:.3f} {cell - 0.6:.3f} {pv + 0.24:.3f} ;', '    END', '  END VDD',
                                      '  PIN VSS', '    DIRECTION INOUT ;', '    USE GROUND ;', '    PORT', '      LAYER M8 ;',
                                      f'        RECT 0.600 {ps_ - 0.24:.3f} {cell - 0.6:.3f} {ps_ + 0.24:.3f} ;', '    END', '  END VSS',
                                      '  OBS'] + [f'    LAYER M{q} ;\n      RECT 0 0 {cell:.3f} {cell:.3f} ;' for q in range(2, 8)] +
                                     ['  END', f'END {mn}', ''])
            n = f'L_{i}_{j}'
            comps.append((n, mn, cx0, cy0))
            power[n] = pw[j][i]
            kinds[n] = kind_at(m, x0 + cx0 + cell / 2, y0 + cy0 + cell / 2)
    d = ['VERSION 5.8 ;', 'DIVIDERCHAR "/" ;', 'BUSBITCHARS "[]" ;', 'DESIGN qir ;', 'UNITS DISTANCE MICRONS 1000 ;',
         f'DIEAREA ( 0 0 ) ( {round(W * 1000)} {round(H * 1000)} ) ;',
         'VIAS 1 ;', '- via89 + RECT M8 ( -240 -240 ) ( 240 240 ) + RECT V8 ( -200 -200 ) ( 200 200 ) '
         '+ RECT M9 ( -240 -240 ) ( 240 240 ) ;', 'END VIAS', f'COMPONENTS {len(comps)} ;']
    d += [f'- {n} {mst} + FIXED ( {round(x * 1000)} {round(y * 1000)} ) N ;' for n, mst, x, y in comps]
    d += ['END COMPONENTS', 'SPECIALNETS 2 ;']
    for net in ('VDD', 'VSS'):
        L = [f'- {net} ( * {net} ) + USE ' + ('POWER' if net == 'VDD' else 'GROUND')]
        first = True
        for (nn, ly, a_, b_, c_, e_) in s9 + s8:
            if nn != net:
                continue
            if ly == 'M9':
                seg = f'{ly} 480 + SHAPE STRIPE ( {round((a_ + c_) / 2 * 1000)} {round(b_ * 1000)} ) ( * {round(e_ * 1000)} )'
            else:
                seg = f'{ly} 480 + SHAPE STRIPE ( {round(a_ * 1000)} {round((b_ + e_) / 2 * 1000)} ) ( {round(c_ * 1000)} * )'
            L.append(('  + ROUTED ' if first else '    NEW ') + seg)
            first = False
        for (nn, xx, yy) in vias:
            if nn == net:
                L.append(f'    NEW M8 0 ( {round(xx * 1000)} {round(yy * 1000)} ) via89')
        L[-1] += ' ;'
        d += L
    d += ['END SPECIALNETS', 'END DESIGN', '']
    (work / 'top.def').write_text('\n'.join(d))
    (work / 'loads.lef').write_text('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n' + '\n'.join(lefs.values()) + 'END LIBRARY\n')
    for net in ('VDD', 'VSS'):
        (work / f'vsrc_{net}.loc').write_text(''.join(f'{x:.3f}, {y:.3f}, {BUMP_SIZE:.1f}, {VDD_V if net == "VDD" else 0.0}\n'
                                                     for x, y in sites[net]))
    tcl = f"""
set t0 [clock seconds]
read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/loads.lef
read_def /work/top.def
set block [ord::get_db_block]
add_global_connection -net {{VDD}} -inst_pattern {{.*}} -pin_pattern {{^VDD$}} -power
add_global_connection -net {{VSS}} -inst_pattern {{.*}} -pin_pattern {{^VSS$}} -ground
global_connect
puts "OT_STAT insts=[llength [$block getInsts]]"
read_liberty {PLAT}/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
set_cmd_units -power W
source {PLAT}/setRC.tcl
set_pdnsim_source_settings -bump_dx {int(round(vp))} -bump_dy {int(round(vp))} -bump_size {int(BUMP_SIZE)} -bump_interval 1
{chr(10).join(f'set_pdnsim_inst_power -inst {n} -power {p:.9f}' for n, p in power.items() if p > 0)}
foreach net {{VDD VSS}} {{
  if {{[catch {{check_power_grid -net $net -error_file /work/pg_err_$net.rpt}} err]}} {{ puts "OT_PSM net=$net status=FAIL err=$err" }} else {{ puts "OT_PSM net=$net status=PASS" }}
}}
foreach net {{VDD VSS}} {{
  set_pdnsim_net_voltage -net $net -voltage [expr {{$net eq "VDD" ? {VDD_V} : 0.0}}]
  if {{[catch {{analyze_power_grid -net $net -vsrc /work/vsrc_$net.loc -voltage_file /work/ir_$net.rpt -error_file /work/ir_err_$net.rpt}} err]}} {{
    puts "OT_IR net=$net status=FAIL err=$err" }} else {{ puts "OT_IR net=$net status=PASS" }}
}}
puts "OT_TIME psm_s=[expr {{[clock seconds]-$t0}}]"
exit
"""
    (work / 'run.tcl').write_text(tcl)
    meta = dict(case='c', window=window, window_um=[x0, y0, x1, y1], size_um=[W, H], cell_um=cell, loads=len(comps),
                power_w=round(sum(power.values()), 4), power_w_by_kind={k_: round(v, 4) for k_, v in tot_by_kind.items()},
                power_w_per_mm2=round(sum(power.values()) / (W * H / 1e6), 4), cells_without_both_rails=missing,
                peak=peak, scale=scale, align=align, signal_bumps_phy=signal_bumps_phy, coverage=cov,
                bump_sites=len(sites['VDD']),
                stripes=dict(M9=len(s9), M8=len(s8), vias=len(vias), width_um=0.48,
                             pitch_by_kind={k_: pitch(v) for k_, v in cov.items()}),
                bumps=dict(array_pitch_um=BUMP_PITCH, vdd_pitch_um=round(vp, 2), size_um=BUMP_SIZE,
                           scheme='every core bump a power bump (VDD/VSS interleaved half a pitch); PHY/link regions '
                                  'carry signal bumps only' if signal_bumps_phy else 'power bumps everywhere'),
                vdd_v=VDD_V, budget_mv=35.0)
    (work / 'manifest.json').write_text(json.dumps(meta, indent=1))
    (work / 'kinds.json').write_text(json.dumps(kinds))
    return meta


def _pg_only_m7(text):
    """A real LEF with its PG pins reduced to their M7 shapes: the abstract carries the element's internal M1/M2/M6
    rails without the vias joining them, so PSM sees them as floating (the PSM-0069 VDD-connectivity fault of the
    S82 native-parent attempt).  The die grid connects to the M7 stripes; the element's internal grid is element
    sign-off."""
    def fix(mm):
        out, cur = [], None
        for line in mm.group(0).splitlines():
            st = line.strip()
            if st.startswith('LAYER'):
                cur = st.split()[1]
                if cur == 'M7':
                    out.append(line)
            elif st.startswith('RECT') or st.startswith('POLYGON'):
                if cur == 'M7':
                    out.append(line)
            else:
                cur = None if st in ('END', 'PORT') else cur
                out.append(line)
        return '\n'.join(out)
    return re.sub(r'  PIN (VDD|VSS)\n(.*?)\n  END \1', fix, text, flags=re.S)


def _gen_pg_lef(mst):
    """Generated abstract with M7 PG stripes (0.288 um, 10.8 um pitch, as the routed q element) for the PSM window."""
    L = [f'MACRO {mst.name}', '  CLASS BLOCK ;', f'  FOREIGN {mst.name} 0 0 ;', f'  SIZE {mst.w:.3f} BY {mst.h:.3f} ;',
         '  SYMMETRY X Y ;']
    for net, off in (('VDD', 1.0), ('VSS', 6.4)):
        L += [f'  PIN {net}', '    DIRECTION INOUT ;', f'    USE {"POWER" if net == "VDD" else "GROUND"} ;', '    PORT',
              '      LAYER M7 ;']
        x = off
        while x + 0.288 < mst.w - 0.2:
            L.append(f'        RECT {x:.3f} 0.300 {x + 0.288:.3f} {mst.h - 0.3:.3f} ;')
            x += 10.8
        L += ['    END', f'  END {net}']
    L += ['  OBS'] + [f'    LAYER M{i} ;\n      RECT 0 0 {mst.w:.3f} {mst.h:.3f} ;' for i in range(1, 7)] + ['  END',
                                                                                                  f'END {mst.name}', '']
    return '\n'.join(L)


def case_irm(m, work, window, cov, vdd_pitch=None, peak=True):
    """IR window with the REAL element abstracts: pdngen builds the bump-aligned M8/M9 die grid, connects it to the
    q element's and every generated abstract's M7 PG stripes (M7-M8 vias) and to the cfg ROMs' M4 rails through an
    M5 macro grid (M4-M5, M5-M8 via stacks); PSM solves the grid with each instance's power on its own pins."""
    work.mkdir(parents=True, exist_ok=True)
    x0, y0, x1, y1 = windows(m)[window]
    x0, y0 = max(0.0, dn(x0, GX)), max(0.0, dn(y0, GY))
    W, H = round(x1 - x0, 3), round(y1 - y0, 3)
    vp = vdd_pitch or BUMP_PITCH / math.sqrt(0.5)
    p = cov['field']
    raw = dn(0.48 / p, 0.160)
    n = math.ceil(vp / raw - 1e-9)
    n += (n % 2 == 0)
    pitch = round(vp / n, 4)
    _init_real()
    M = masters(m, 1)
    ins, clip_pw = [], {}
    for it in m['insts']:
        if it.kind in ('phy', 'link') or it.x >= x1 or it.y >= y1 or it.x + it.w <= x0 or it.y + it.h <= y0:
            continue
        if it.x >= x0 and it.y >= y0 and it.x + it.w <= x1 and it.y + it.h <= y1:
            ins.append(it)
        elif it.master not in REAL_FILES:
            # a generated slab crossing the window edge (spine SU / gather / collective, service blocks): its
            # in-window part as a clipped generated master carrying its area share of the instance power
            a, b = up(max(it.x, x0), GX), up(max(it.y, y0), GY)
            w_, h_ = dn(min(it.x + it.w, x1) - a, GX), dn(min(it.y + it.h, y1) - b, GY)
            if w_ < 20.0 or h_ < 20.0:
                continue
            nm = f'{it.master}_clip_{it.name}'
            M[nm] = Q.Master(nm, w_, h_, M[it.master].obs_top, 'window clip of ' + it.master)
            c = Inst(it.name, nm, a, b, w_, h_, 'R0', it.kind, it.region, it.domain)
            clip_pw[it.name] = inst_power(it) * (w_ * h_) / (it.w * it.h)
            ins.append(c)
    masters_used = sorted({it.master for it in ins})
    gen = [M[n_] for n_ in masters_used if n_ not in REAL_FILES]
    (work / 'gen_pg.lef').write_text('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n' +
                                     '\n'.join(_gen_pg_lef(g_) for g_ in gen) + 'END LIBRARY\n')
    (work / 'q_pg.lef').write_text(_pg_only_m7(_lef_text(Q_LEF)))
    (work / 'cfg.lef').write_text(_lef_text(CFG_LEF))
    o = {'R0': 'N', 'MY': 'FN', 'MX': 'FS'}
    d = ['VERSION 5.8 ;', 'DIVIDERCHAR "/" ;', 'BUSBITCHARS "[]" ;', 'DESIGN qirm ;', 'UNITS DISTANCE MICRONS 1000 ;',
         f'DIEAREA ( 0 0 ) ( {round(W * 1000)} {round(H * 1000)} ) ;', f'COMPONENTS {len(ins)} ;']
    d += [f'- {it.name} {it.master} + FIXED ( {round((it.x - x0) * 1000)} {round((it.y - y0) * 1000)} ) {o[it.orient]} ;'
          for it in ins]
    d += ['END COMPONENTS', 'END DESIGN', '']
    (work / 'win.def').write_text('\n'.join(d))
    sites = {'VDD': [], 'VSS': []}
    for net, off in (('VDD', vp / 2), ('VSS', 0.0)):
        yy = off if off > 0 else vp
        while yy < H - 1.0:
            xx = off if off > 0 else vp
            while xx < W - 1.0:
                sites[net].append((round(xx, 3), round(yy, 3)))
                xx += vp
            yy += vp
    for net in ('VDD', 'VSS'):
        (work / f'vsrc_{net}.loc').write_text(''.join(f'{x:.3f}, {y:.3f}, {BUMP_SIZE:.1f}, {VDD_V if net == "VDD" else 0.0}\n'
                                                     for x, y in sites[net]))
    off = round((vp / 2) % pitch, 4)
    cfgm = real_lef(CFG_LEF)['name']
    other = ' '.join(x for x in masters_used if x != cfgm)
    power = {it.name: (clip_pw[it.name] if it.name in clip_pw else inst_power(it)) * (1.0 if peak else 0.25) for it in ins}
    tcl = f"""
set t0 [clock seconds]
read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/q_pg.lef
read_lef /work/cfg.lef
read_lef /work/gen_pg.lef
read_def /work/win.def
add_global_connection -net {{VDD}} -inst_pattern {{.*}} -pin_pattern {{^VDD$}} -power
add_global_connection -net {{VSS}} -inst_pattern {{.*}} -pin_pattern {{^VSS$}} -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name top -voltage_domains CORE
add_pdn_stripe -grid top -layer M8 -width 0.48 -pitch {pitch} -spacing {pitch / 2 - 0.48:.4f} -offset {off}
add_pdn_stripe -grid top -layer M9 -width 0.48 -pitch {pitch} -spacing {pitch / 2 - 0.48:.4f} -offset {off}
add_pdn_connect -grid top -layers {{M8 M9}}
define_pdn_grid -macro -name m7 -cells {{{other}}} -halo {{0 0 0 0}} -voltage_domains CORE
add_pdn_connect -grid m7 -layers {{M7 M8}}
define_pdn_grid -macro -name mcfg -cells {{{cfgm}}} -halo {{0 0 0 0}} -voltage_domains CORE
add_pdn_stripe -grid mcfg -layer M5 -width 0.12 -pitch 2.4 -spacing 1.08 -offset 0.6
add_pdn_connect -grid mcfg -layers {{M4 M5}}
add_pdn_connect -grid mcfg -layers {{M5 M8}}
if {{[catch {{pdngen}} err]}} {{ puts "OT_PDN FAIL $err" }} else {{ puts "OT_PDN PASS" }}
puts "OT_TIME pdn_s=[expr {{[clock seconds]-$t0}}]"
read_liberty {PLAT}/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
set_cmd_units -power W
source {PLAT}/setRC.tcl
set_pdnsim_source_settings -bump_dx {int(round(vp))} -bump_dy {int(round(vp))} -bump_size {int(BUMP_SIZE)} -bump_interval 1
{chr(10).join(f'set_pdnsim_inst_power -inst {n_} -power {p_:.9f}' for n_, p_ in power.items() if p_ > 0)}
foreach net {{VDD VSS}} {{
  if {{[catch {{check_power_grid -net $net -error_file /work/pg_err_$net.rpt}} err]}} {{ puts "OT_PSM net=$net status=FAIL err=$err" }} else {{ puts "OT_PSM net=$net status=PASS" }}
}}
foreach net {{VDD VSS}} {{
  set_pdnsim_net_voltage -net $net -voltage [expr {{$net eq "VDD" ? {VDD_V} : 0.0}}]
  if {{[catch {{analyze_power_grid -net $net -vsrc /work/vsrc_$net.loc -voltage_file /work/ir_$net.rpt -error_file /work/ir_err_$net.rpt}} err]}} {{
    puts "OT_IR net=$net status=FAIL err=$err" }} else {{ puts "OT_IR net=$net status=PASS" }}
}}
puts "OT_TIME psm_s=[expr {{[clock seconds]-$t0}}]"
exit
"""
    (work / 'run.tcl').write_text(tcl)
    kinds = {it.name: it.kind for it in ins}
    (work / 'kinds.json').write_text(json.dumps(kinds))
    meta = dict(case='c', method='real element abstracts + pdngen + PSM', window=window, window_um=[x0, y0, x1, y1],
                size_um=[W, H], instances=len(ins), clipped=sorted(clip_pw), power_w=round(sum(power.values()), 4),
                power_w_per_mm2=round(sum(power.values()) / (W * H / 1e6), 4), coverage=cov,
                strap_pitch_um=pitch, strap_offset_um=off, masters=masters_used,
                bumps=dict(array_pitch_um=BUMP_PITCH, vdd_pitch_um=round(vp, 2), size_um=BUMP_SIZE),
                vdd_v=VDD_V, budget_mv=35.0)
    (work / 'manifest.json').write_text(json.dumps(meta, indent=1))
    return meta


def case_psmt(out, mode):
    """PSM macro-current control (why case c, not case irm, is the IR sign-off method): one 1,000 x 1,000 um block
    with M7 PG stripes at 1 W, versus the same power as 2,116 21.6 um cells with the same stripes, on the identical
    bump-aligned M8/M9 grid and bump array.  PSM puts a macro instance's whole current on few nodes, so a large
    abstract's worst drop is a solver artefact (measured 54.8 mV vs 2.4 mV)."""
    out.mkdir(parents=True, exist_ok=True)
    W = H = 1400.0; B0 = 200.0; S = 1000.0; P = 1.0
    def m7(name, w, h):
        L = [f'MACRO {name}', '  CLASS BLOCK ;', f'  FOREIGN {name} 0 0 ;', f'  SIZE {w:.3f} BY {h:.3f} ;', '  SYMMETRY X Y ;']
        for net, off in (('VDD', 1.0), ('VSS', 6.4)):
            L += [f'  PIN {net}', '    DIRECTION INOUT ;', f'    USE {"POWER" if net=="VDD" else "GROUND"} ;', '    PORT', '      LAYER M7 ;']
            x = off
            while x + 0.288 < w - 0.2:
                L.append(f'        RECT {x:.3f} 0.300 {x+0.288:.3f} {h-0.3:.3f} ;'); x += 10.8
            L += ['    END', f'  END {net}']
        L += ['  OBS'] + [f'    LAYER M{i} ;\n      RECT 0 0 {w:.3f} {h:.3f} ;' for i in range(1, 7)] + ['  END', f'END {name}', '']
        return '\n'.join(L)
    if mode == 'macro':
        lef = m7('blk', S, S); comps = [('b0', 'blk', B0, B0, P)]
    else:
        c = 21.6; n = int(S // c); lef = m7('cell', c, c)
        comps = [(f'c{i}_{j}', 'cell', B0 + i * c, B0 + j * c, P / (n * n)) for i in range(n) for j in range(n)]
    (out / 'x.lef').write_text('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n' + lef + 'END LIBRARY\n')
    d = ['VERSION 5.8 ;', 'DESIGN t ;', 'UNITS DISTANCE MICRONS 1000 ;', f'DIEAREA ( 0 0 ) ( {int(W*1000)} {int(H*1000)} ) ;', f'COMPONENTS {len(comps)} ;']
    d += [f'- {n} {m} + FIXED ( {round(x*1000)} {round(y*1000)} ) N ;' for n, m, x, y, _ in comps] + ['END COMPONENTS', 'END DESIGN', '']
    (out / 't.def').write_text('\n'.join(d))
    vp = 63.64
    for net, off in (('VDD', vp/2), ('VSS', vp)):
        s = []
        y = off
        while y < H - 1:
            x = off
            while x < W - 1:
                s.append(f'{x:.3f}, {y:.3f}, 20.0, {0.7 if net=="VDD" else 0.0}\n'); x += vp
            y += vp
        (out / f'vsrc_{net}.loc').write_text(''.join(s))
    pitch = 3.7435; PL = '/OpenROAD-flow-scripts/flow/platforms/asap7'
    t = f"""read_lef {PL}/lef/asap7_tech_1x_201209.lef
read_lef /work/x.lef
read_def /work/t.def
add_global_connection -net VDD -inst_pattern .* -pin_pattern ^VDD$ -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern ^VSS$ -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name top -voltage_domains CORE
add_pdn_stripe -grid top -layer M8 -width 0.48 -pitch {pitch} -spacing {pitch/2-0.48:.4f} -offset {(vp/2)%pitch:.4f}
add_pdn_stripe -grid top -layer M9 -width 0.48 -pitch {pitch} -spacing {pitch/2-0.48:.4f} -offset {(vp/2)%pitch:.4f}
add_pdn_connect -grid top -layers {{M8 M9}}
define_pdn_grid -macro -name m7 -cells {{{comps[0][1]}}} -halo {{0 0 0 0}} -voltage_domains CORE
add_pdn_connect -grid m7 -layers {{M7 M8}}
pdngen
read_liberty {PL}/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
source {PL}/setRC.tcl
set_pdnsim_source_settings -bump_dx 64 -bump_dy 64 -bump_size 20 -bump_interval 1
""" + ''.join(f'set_pdnsim_inst_power -inst {n} -power {p:.9f}\n' for n, _, _, _, p in comps) + """
set_pdnsim_net_voltage -net VDD -voltage 0.7
analyze_power_grid -net VDD -vsrc /work/vsrc_VDD.loc -voltage_file /work/ir_VDD.rpt
exit
"""
    (out / 'run.tcl').write_text(t)


# ------------------------------------------------------------------------------------------------ records
def record_b(work, m):
    from chip_assembly import v41_die as VD
    log = Q._log(work)
    rec = dict(case='b', exit=Q._exit(work), wall=Q._wall(log), peak_rss_mb=Q._rss_mb(log),
               manifest=json.loads((work / 'manifest.json').read_text()))
    p = VD.parse_log(log)
    rec['grt'] = {k_: v for k_, v in p.items() if k_ != 'mem'}
    mm_ = re.search(r'OT_TIME grt_s=(\d+)', log)
    rec['grt_s'] = int(mm_.group(1)) if mm_ else None
    k = rec['manifest']['bundle_k']
    cls_of = {f'n_{bid}': (c, bits) for bid, c, bits, _ in m['buses']}
    per = {}
    for net, um in VD.parse_wirelength(work / 'wirelength.csv').items():
        c, bits = cls_of.get(net.split('[')[0], ('?', 0))
        e = per.setdefault(c, dict(bundle_nets=0, bundle_um=0.0, max_um=0.0))
        e['bundle_nets'] += 1
        e['bundle_um'] += um
        e['max_um'] = max(e['max_um'], um)
    for c, e in per.items():
        e['wire_m'] = round(e['bundle_um'] * k / 1e6, 1)
        e['bundle_um'], e['max_um'] = round(e['bundle_um'], 1), round(e['max_um'], 1)
    rec['wire_by_class'] = per
    rec['windows'] = gcell_windows(work, m)
    rec['errors'] = re.findall(r'\[ERROR [^\]]+\].*|^Error: .*', log, re.M)[:10]
    return rec


def gcell_windows(work, m, base=None):
    """4 x 4 GCell windows from gcell_usage.txt ('L <layer> <row> cap/use ...', capacity FIRST).  Per layer: windows,
    max use/cap, count above 0.9 / 1.0, and the worst windows with their die location and floorplan kind; when an
    empty-net baseline exists (base), usage booked without nets (obstructions/adjustments) is subtracted."""
    f = work / 'gcell_usage.txt'
    if not f.is_file():
        return None
    lines = f.read_text().splitlines()
    gx = [float(v) for v in lines[0].split()[1].split(',')]
    gy = [float(v) for v in lines[1].split()[1].split(',')]
    dbu = 1000.0 if max(gx) > DIE[0] * 2 else 1.0
    gx, gy = [v / dbu for v in gx], [v / dbu for v in gy]
    bl = {}
    if base and (base / 'gcell_usage.txt').is_file():
        for line in (base / 'gcell_usage.txt').read_text().splitlines():
            if line.startswith('L '):
                fs = line.split()
                bl[(fs[1], int(fs[2]))] = [tuple(float(x) for x in c.split('/')) for c in fs[3:]]
    out = {}
    worst = []
    for line in lines:
        if not line.startswith('L '):
            continue
        fs = line.split()
        ln, j = fs[1], int(fs[2])
        e = out.setdefault(ln, dict(windows=0, over_0p9=0, over_1=0, max_use_over_cap=0.0))
        brow = bl.get((ln, j))
        for i, c in enumerate(fs[3:]):
            cap, use = (float(x) for x in c.split('/'))
            if brow:
                bcap, buse = brow[i]
                cap, use = cap - buse, use - buse
            if cap <= 0:
                continue
            r = use / cap
            e['windows'] += 1
            e['over_0p9'] += r > 0.9
            e['over_1'] += r > 1.0
            if r > e['max_use_over_cap']:
                e['max_use_over_cap'] = round(r, 3)
            if r > 0.9:
                x, y = gx[min(len(gx) - 1, 4 * i)], gy[min(len(gy) - 1, j)]
                worst.append((round(r, 3), ln, round(x), round(y), where(m, x + 2 * (gx[1] - gx[0]), y + 2 * (gy[1] - gy[0]))))
    worst.sort(reverse=True)
    return dict(per_layer=out, worst=worst[:40], baseline_subtracted=bool(bl))


def where(m, x, y):
    g = m['geo']
    if g['x_sp'] <= x < g['x_fe'] and g['y_f'] <= y < g['y_top']:
        return 'vch' if m['x_vch'] <= x < m['x_vch'] + VCH else 'spine'
    for t, c in enumerate(g['ch_y']):
        if c <= y < c + CH and g['x_fw'] <= x < g['x_le']:
            return f'channel{t}'
    for r in m['regions']:
        a, b, c, e = r['rect']
        if a <= x < c and b <= y < e:
            return r['name']
    if y < g['y_f'] or y >= g['y_top']:
        return 'band'
    return 'other'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['plan', 'real', 'grt', 'ir', 'irm', 'psmt', 'record', 'check'])
    ap.add_argument('--work', type=Path)
    ap.add_argument('--k', type=int, default=16)
    ap.add_argument('--tag', default='base')
    ap.add_argument('--iters', type=int, default=5)
    ap.add_argument('--empty', action='store_true', help='GRT baseline with no nets')
    ap.add_argument('--window', default='field')
    ap.add_argument('--cov', default='', help='coverage overrides kind=frac,...')
    ap.add_argument('--vdd-pitch', type=float)
    ap.add_argument('--no-align', action='store_true')
    ap.add_argument('--avg', action='store_true')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--psmt', type=Path, help='record: the PSM macro-current control directory (mode psmt)')
    ap.add_argument('--only', default='', help='record: case-name regex (cases built by the current floorplan)')
    ap.add_argument('--die', default='layer', choices=['layer', 'head'])
    a = ap.parse_args(argv)
    configure(a.die)
    m = build()
    cov = dict(COV)
    for kv in filter(None, a.cov.split(',')):
        k_, v = kv.split('=')
        cov[k_] = float(v)
    if a.mode == 'check':
        print(json.dumps(legality(m), indent=1))
        pc = pin_clashes(m)
        pc16 = pin_clashes(m, 16, 0.024 * 16 - 1e-6)
        print(json.dumps(dict(generated_pin_clashes=len(pc), examples=pc[:10], k16_clashes=len(pc16), k16_examples=pc16[:10])))
        print(json.dumps(trunk_stages(m), indent=1))
        return 0
    if a.mode == 'plan':
        out = ROOT / OUT / ('' if a.die == 'layer' else 'head_die')
        out.mkdir(parents=True, exist_ok=True)
        rec = plan_record(m)
        rec['legality_python'] = legality(m)
        rec['windows_um'] = windows(m)
        (out / 'floorplan.json').write_text(json.dumps(rec, indent=1) + '\n')
        svg(m, out / 'floorplan.svg')
        write_def_floorplan(m, out / 'floorplan.def')
        print(json.dumps({k_: rec[k_] for k_ in ('die', 'instances', 'area_mm2_by_kind', 'placed_footprint_mm2',
                                                  'legality_python', 'trunk_stages', 'scan_die_power')}, indent=1))
        return 0
    if a.mode == 'record':
        cases = {}
        for d in sorted(a.work.iterdir()):
            if not (d / 'manifest.json').is_file() or (a.only and not re.fullmatch(a.only, d.name)):
                continue
            man = json.loads((d / 'manifest.json').read_text())
            try:
                if man.get('case') == 'a':
                    cases[d.name] = Q.record_a(d)
                elif man.get('case') == 'b':
                    configure(man.get('variant', {}).get('die', 'layer'))
                    m = build()
                    cases[d.name] = record_b(d, m)
                    bd = a.work / (re.sub(r'_i\d+$', '_i5', d.name) + '_base')   # the empty baseline is iteration-free
                    if not man.get('empty_baseline') and bd.is_dir():
                        cases[d.name]['windows_baseline_subtracted'] = gcell_windows(d, m, bd)
                elif man.get('case') == 'c':
                    cases[d.name] = Q.record_c(d)
            except Exception as e:  # noqa: BLE001
                cases[d.name] = dict(error=repr(e))
        rec = dict(schema='opentallas.dsrom-s81-fulldie.feasibility.v1', tool_sha256=sha('tools/dsrom_s81_fulldie.py'),
                   cases=cases)
        if a.psmt:
            ctl = {}
            for mode in ('macro', 'cells'):
                log = (a.psmt / mode / 'run.log').read_text()
                ctl[mode] = dict(worst_mv=round(float(re.search(r'Worstcase IR drop: ([\d.e+-]+)', log).group(1)) * 1e3, 2),
                                 avg_mv=round(float(re.search(r'Average IR drop  : ([\d.e+-]+)', log).group(1)) * 1e3, 3))
            rec['psm_macro_current_control'] = dict(ctl, note=case_psmt.__doc__.split('.  PSM')[0].strip() + '.')

        out = a.out or ROOT / OUT / 'feasibility.json'
        out.write_text(json.dumps(rec, indent=1, sort_keys=True) + '\n')
        return 0
    if a.work is None:
        ap.error('--work required')
    work = a.work.resolve()
    if a.mode == 'real':
        print(json.dumps(case_real(m, work)))
    elif a.mode == 'grt':
        print(json.dumps(case_grt(m, work, a.k, a.tag, a.iters, cov, empty=a.empty)))  # variant carries die
    elif a.mode == 'psmt':
        case_psmt(work / 'macro', 'macro')
        case_psmt(work / 'cells', 'cells')
    elif a.mode == 'irm':
        meta = case_irm(m, work, a.window, cov, vdd_pitch=a.vdd_pitch, peak=not a.avg)
        meta['die'] = a.die
        (work / 'manifest.json').write_text(json.dumps(meta, indent=1))
        print(json.dumps(meta))
    elif a.mode == 'ir':
        meta = case_ir(m, work, a.window, cov, peak=not a.avg, vdd_pitch=a.vdd_pitch, align=not a.no_align)
        meta['die'] = a.die
        (work / 'manifest.json').write_text(json.dumps(meta, indent=1))
        print(json.dumps(meta))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
