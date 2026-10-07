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
CFG_LEF_V1 = 'results/uarch/dsrom_c_w4_20261003/s82_inputs/cfg.lef'
CFG_LEF_V2 = 'physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.lef'
CFG_LEF = CFG_LEF_V1
HEAD_BUNDLES = 0
HEAD_A_LEF = 'results/rtl/dsrom_recovery_20261004/physcost/abstracts/ot_dsrom_head_elem_A.lef.gz'
HEAD_B_LEF = 'results/rtl/dsrom_recovery_20261004/physcost/abstracts/ot_dsrom_head_elem_B.lef.gz'
HEAD_ELEM_W = dict(A=0.19837, B=0.185753)     # W, reproduced routes (physcost/abstracts/provenance.json)
MESO_V7 = 'results/uarch/meso_fifo_20261004/physical/meso_d4_v7/physical.json'   # closed slot (ROM inventory note 3)
MESO_V7_UM2 = 4842.0                          # per W512 D4 slot, results/uarch/meso_fifo_20261004/verdict.json
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
HEAD_DIES = 12                # head dies in the rack (S81-RERUN: 13-14 at the 192.24 um q frame)
REV = 'r8'          # r8 sub-revision: 'r8' (main 5841260ac, reproducible) | 'r9' (S81-RERUN: hub-bus stations,
                    # 425 um station step, q x1 from the S face when the q abstract has it there)
GEN = 'r7'          # 'r7': the 21fcf6469 floorplan/netlist (default, reproducible); 'r8': the wired die (S81-DIE, below)


def configure(die, gen='r7'):
    """'layer': the S81 layer die (L20 scan die = the hottest).  'head': one of the 12 head dies (coordinator
    decision 2026-10-04, main 57e041e74): 1,682 content pairs (embed + lm-head + norm + DSpark drafter), of which the
    210 lm-head pairs carry the NV5 batched draft head; the drafter/embed pairs keep the layer die's BF share."""
    global PAIRS, BF_PAIRS, NV_PAIRS, DIE_KIND, GEN, CFG_LEF, HEAD_BUNDLES, HOP_PLAN
    DIE_KIND, GEN = die, gen
    HOP_PLAN = None                  # --hop-fix plans are per die
    # r8 uses the mirror-legal v2 cfg ROM view (ROM inventory note 2); r7 keeps the v1 view it was run with
    CFG_LEF = CFG_LEF_V2 if gen == 'r8' else CFG_LEF_V1
    REAL_FILES.clear()
    HEAD_BUNDLES = 0
    if die in ('layer', 'layer1'):
        PAIRS, BF_PAIRS, NV_PAIRS = 2417, 519, 0
    else:
        h = json.loads((ROOT / HEAD_REC).read_text())
        v = next(x for x in h['variants'] if x['NV'] == 5)['head_groups']['12']
        PAIRS, NV_PAIRS = math.ceil(v['content_pairs_per_die']), math.ceil(v['lm_head_pairs_per_die'])
        BF_PAIRS = round((PAIRS - NV_PAIRS) * 519 / 2417)
        if gen == 'r8':
            # recovery lever head.json (ADOPT, closed r4_A/r4_B): the lm-head pairs (bf + NV5 nvx + cfg) are replaced
            # by ot_dsrom_head_bundle units (4 A + 1 B ot_dsrom_head_elem, 128 vocabulary rows each): 129,280 rows /
            # 128 = 1,010 bundles over the 12 head dies (ROM inventory note 1)
            PAIRS, NV_PAIRS = PAIRS - NV_PAIRS, 0
            HEAD_BUNDLES = math.ceil(129280 / 128 / HEAD_DIES)
            if HEAD_DIES != 12:
                # S81-RERUN: the same head content (12 x the 12-die share) spread over HEAD_DIES dies
                PAIRS = math.ceil(PAIRS * 12 / HEAD_DIES)
                BF_PAIRS = round(PAIRS * 519 / 2417)


# --bf-per-region N (bf-double 2026-10-07; default None = the decision's 519/2417 share, spread die-wide): exactly N
# BF pairs in every return region of a layer die, at the in-region positions tools/dsrom_bf_double_alloc.py binds
# (pair (2j+1)n/(2N) of the region's n, j < N); 0 = the q-only die flavour.
BF_PER_REGION = None


def set_pairs(n):
    """r8: pairs (elements) per die; BF / NV shares scaled as the decision's"""
    global PAIRS, BF_PAIRS, NV_PAIRS
    if DIE_KIND == 'layer' and BF_PER_REGION is not None:
        PAIRS, BF_PAIRS = n, BF_PER_REGION * ROOTS
    elif DIE_KIND == 'layer':
        PAIRS, BF_PAIRS = n, round(n * 519 / 2417)
    else:
        NV_PAIRS = round(NV_PAIRS * n / PAIRS)
        PAIRS, BF_PAIRS = n, round((n - NV_PAIRS) * 519 / 2417)


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
CHS = None                    # --ch-heights (S81-RERUN v9, OWNER rule 3): per-channel heights (TIERS + 1), default CH each


def chh(t):
    return CHS[t] if CHS else CH
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
FWD_REACH = LINK_STAGE_UM       # --fwd-pitch (S81-RERUN v6, OWNER 2026-10-06): forwarded station reach; 300 um gives the
                                #   routed stations clear SS margin (430 um pitch: dsfd_stn* SS -1.7..+2.8 ps)
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


def q_x1_south():
    """True when the q abstract has xs_q1 / xs_e1 on its S face (QELEM Z22+): the slot's own station drives them"""
    rq = real_lef(Q_LEF)
    ys = [rq['pins'][p_][1][1] for p_ in rq['pins'] if p_.startswith(('xs_q1[', 'xs_e1['))]
    return bool(ys) and max(ys) < rq['h'] / 2


def _bus(base, n):
    return [f'{base}[{i}]' for i in range(n)]


_PSL = re.compile(r'^(.+)\[(\d+):(\d+)\]$')


def pslice(port):
    """bus endpoint port spec: 'p' (the whole port) or 'p[lo:hi]' (bits lo..hi of port p, ascending; S81-RERUN
    2026-10-07 port slicing: one port served by several nets, e.g. a 512-b link tx by two 256-b final stations).
    Returns (base, lo, hi) with lo = hi = None for a whole port."""
    mm = _PSL.match(port)
    return (mm.group(1), int(mm.group(2)), int(mm.group(3))) if mm else (port, None, None)


def real_ports():
    """master -> port -> ordered real pin names (the netlist binds port bit i to the i-th name)."""
    if GEN == 'r8':
        return real_ports_r8()
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
    for rel in (Q_LEF, CFG_LEF, PHY_LEF, SERDES_LEF, UCIE_LEF) + ((HEAD_A_LEF, HEAD_B_LEF) if HEAD_BUNDLES else ()):
        REAL_FILES[real_lef(rel)['name']] = rel


# ------------------------------------------------------------------------------------------------ field map
def region_bounds():
    return [math.floor(r * PAIRS / ROOTS) for r in range(ROOTS + 1)]


def bf_sites():
    if BF_PER_REGION is not None and DIE_KIND == 'layer':
        b, s = region_bounds(), set()
        for r in range(ROOTS):
            ps = list(range(b[r], b[r + 1]))
            s.update(ps[(2 * j + 1) * len(ps) // (2 * BF_PER_REGION)] for j in range(BF_PER_REGION))
        assert len(s) == BF_PAIRS == BF_PER_REGION * ROOTS
        return s
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
    if GEN == 'r8':
        return build_r8(variant)
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
    wfc_rect = None
    centre_area = dict(HUB_MM2)
    if DIE_KIND == 'layer':
        centre.insert(2, 'wfc')
        centre_area.update(vm=2.659905216, wfc=0.45610905599999996)
    # r4: a SPINE_GAP routing channel between every pair of stacked W-column slabs (b3 GRT: the abutted slab faces
    # carried the 1,024-bit VM <-> SU and the gather/capture buses with no escape room, M8 1.29 / M9 1.15 use/cap)
    ch = sum(up(centre_area[n] * 1e6 / cw, GY) for n in centre) + (len(centre) - 1) * SPINE_GAP
    yc = dn(mid - ch / 2, GY)
    su_lo = HUB_MM2['su'] * (yc - y_f) / (yc - y_f + y_top - (yc + ch))
    s = slab('su_s', su_lo, x_sp, dn(yc - SPINE_GAP - up(su_lo * 1e6 / cw, GY), GY), cw, dom='serial_0p9')
    yy = yc
    for n in centre:
        if n == 'wfc':
            # Real source-sized soft reservation; NEVER a symbolic functional macro.
            wh = up(centre_area[n] * 1e6 / cw, GY)
            wfc_rect = [x_sp, yy, x_sp + cw, yy + wh]
        else:
            slab(n, centre_area[n], x_sp, yy, cw, dom='serial_0p9' if n == 'vm' else 'stream_1p2')
        yy += up(centre_area[n] * 1e6 / cw, GY) + SPINE_GAP
    slab('su_n', HUB_MM2['su'] - su_lo, x_sp, yy, cw, dom='serial_0p9')
    hc_h = up(HUB_MM2['hc'] * 1e6 / cw, GY)
    slab('hc', HUB_MM2['hc'], x_spe, dn(mid - hc_h / 2, GY), cw, dom='serial_0p9')
    for it in insts:
        if it.region == 'spine':
            if DIE_KIND == 'layer':
                assert it.y >= band + SPINE_GAP and it.y + it.h <= H - band - SPINE_GAP, (it.name, it.y, it.y + it.h, band)
            else:
                assert it.y >= y_f - 1e-6 and it.y + it.h <= y_top + 1e-6
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
    spine_y0 = min(it.y for it in insts if it.region == 'spine')
    spine_y1 = max(it.y + it.h for it in insts if it.region == 'spine')
    for reg in regions:
        if reg['name'] in ('spine', 'vch'):
            reg['rect'][1] = min(reg['rect'][1], spine_y0)
            reg['rect'][3] = max(reg['rect'][3], spine_y1)
    model['buses'] = buses(model)            # also adds waypoints / hub FIFO slots
    # Finite source-sized WFC reservation in the SAME selected S81 layer die.
    # This is a soft child slot, never a stand-in functional macro abstract.
    if DIE_KIND == 'layer':
        reservation_path = ROOT / 'results/uarch/dsrom_s81_wfc_parent_allocation_20261006/model.json'
        reservation = json.loads(reservation_path.read_text())
        x0, y0, x1, y1 = wfc_rect
        reservation['selected_WFC_gross_um'] = wfc_rect
        reservation['selected_WFC_core_um'] = [x0+17.28, y0+17.28, x1-17.28, y1-17.28]
        assert all(not (it.x < x1 and it.x + it.w > x0 and
                        it.y < y1 and it.y + it.h > y0) for it in insts), 'WFC overlaps an existing claim'
        model['child_reservations'] = {'wfc': reservation}
        regions.append(dict(name='wfc_selected_child', kind='soft_child_reservation', rect=[x0, y0, x1, y1]))
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
            cy = g['ch_y'][t] + chh(t) - 4.32 - STN_H[1]
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
    if m['variant'].get('gen') == 'r8':
        return masters_r8(m, k)
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
            if inst == 'TOP':
                continue
            port, lo, hi = pslice(port)
            nn = n if lo is None else ((hi + 1) if k == 1 else max(1, math.ceil((hi + 1) / k)))
            key = (by[inst].master, port)
            w[key] = max(w.get(key, 0), nn)
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
    rects = Q.pin_rects(rest, k, wmap)
    if k > 1 and GEOMETRY_FIX:
        # Bundling expands pin width/pitch, not the real macro outline. Keep
        # opposite-face access rectangles separated on thin glue banks too.
        # The k=1 physical pins and every routing-layer assignment are unchanged.
        bounded = []
        for nm, ly, (x0, y0, x1, y1) in rects:
            spec = rest.ports[nm.rsplit('[', 1)[0]]
            if spec[0] == 'face':
                face = spec[2]
                depth = min(0.192 * k, (mst.w if face in 'EW' else mst.h) / 3)
                if face == 'W':
                    x1 = depth
                elif face == 'E':
                    x0 = mst.w - depth
                elif face == 'S':
                    y1 = depth
                else:
                    y0 = mst.h - depth
            bounded.append((nm, ly, (x0, y0, x1, y1)))
        rects = bounded
    return out + rects


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
    tops = [b for b in m['buses'] if b[1] == 'top_in']        # r8: die top input ports (refclk, por_n)
    V = [f'// tools/dsrom_s81_fulldie.py: die-level nets only (k = {k})',
         f'module {top} (' + ', '.join(b[0] for b in tops) + ');']
    V += [f'  input {b[0]};' for b in tops]
    for bid, cls, bits, eps in m['buses']:
        if cls in skip:
            continue
        n = bits if k == 1 else max(1, math.ceil(bits / k))
        net = bid if cls == 'top_in' else f'n_{bid}'
        if cls != 'top_in':
            V.append(f'  wire [{n - 1}:0] {net};')
        for inst, port in eps:
            if inst == 'TOP':
                continue
            mst = by[inst].master
            base, lo, hi = pslice(port)
            if mst in rp and base in rp[mst]:
                names = rp[mst][base][:n] if lo is None else rp[mst][base][lo:hi + 1]
                conns[inst].append((names, net))
            elif lo is not None:
                conns[inst].append((base, net, n, lo if k == 1 else lo // k))
            else:
                conns[inst].append((port, net, n))
    for it in m['insts']:
        parts = []
        bus_bits = defaultdict(dict)
        sliced = defaultdict(list)
        for c in conns.get(it.name, []):
            if len(c) == 4:                      # a slice of a generated / bundled port
                sliced[c[0]].append((c[3], c[1], c[2]))
                continue
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
        for base, pcs in sliced.items():
            pcs.sort()
            assert all(pcs[i][0] + pcs[i][2] == pcs[i + 1][0] for i in range(len(pcs) - 1)) and pcs[0][0] == 0, \
                (it.name, base, pcs)
            parts.append(f'.{base}({{' + ', '.join(net for _, net, _ in reversed(pcs)) + '})')
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
    if GEN == 'r8' and it.kind in ('stn', 'hstn', 'rly', 'qbank', 'hend', 'hb_elem', 'hbglue', 'xstg'):
        return it.power_w
    if GEN == 'r8' and it.kind in POWER8:
        return POWER8[it.kind][0]
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
    col = dict(stn='#08306b', sstn='#6baed6', seq='#bcbddc', cfifo='#e6550d', hend='#a63603', rstg='#fd8d3c', q='#9ecae1', bf='#3182bd', cfg='#deebf7', node='#fd8d3c', fifo_blk='#e6550d', waypoint='#08519c',
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
        cy = g['ch_y'][f['tier']] + chh(f['tier']) / 2
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


def top_pins(m, k=1):
    """r8: die top input ports (refclk, por_n) on the W die edge at the collective's (PLL) height"""
    tops = [b[0] for b in m['buses'] if b[1] == 'top_in']
    if not tops:
        return ''
    y0 = dn(m['hub']['collective'].y + m['hub']['collective'].h / 2, GY)
    return '\n'.join(f'place_pin -pin_name {p} -layer M4 -location {{0.5 {y0 + 4.32 * i:.3f}}} '
                     f'-pin_size {{{1.0 * k:.3f} {max(0.072, 0.024 * k):.3f}}} '
                     f'-force_to_die_boundary' for i, p in enumerate(tops))


# ------------------------------------------------------------------------------------------------ case (a): real
def case_real(m, work):
    work.mkdir(parents=True, exist_ok=True)
    npins = write_lefs(m, 1, work / 'elements.lef')
    _init_real()
    import gzip
    (work / 'q_elem.lef').write_text(_lef_text(Q_LEF))
    for rel, nm in ((CFG_LEF, 'cfg.lef'), (PHY_LEF, 'phy.lef'), (SERDES_LEF, 'serdes.lef'), (UCIE_LEF, 'ucie.lef'),
                    (HEAD_A_LEF, 'head_a.lef'), (HEAD_B_LEF, 'head_b.lef')):
        if rel in (HEAD_A_LEF, HEAD_B_LEF) and not HEAD_BUNDLES:
            continue
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
foreach f {{q_elem.lef cfg.lef phy.lef serdes.lef ucie.lef {'head_a.lef head_b.lef ' if HEAD_BUNDLES else ''}elements.lef}} {{ read_lef /work/$f }}
read_verilog /work/die.v
link_design dsfd_die
mem linked
initialize_floorplan -die_area {{0 0 {W:.3f} {H:.3f}}} -core_area {{0 0 {W:.3f} {H:.3f}}} -site asap7sc7p5t
source {PLAT}/openRoad/make_tracks.tcl
set ::env(MAKE_TRACKS) {PLAT}/openRoad/make_tracks.tcl
source /work/snap.tcl
mem floorplan
{top_pins(m)}
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
        mm['buses'] = [next(b_ for b_ in m['buses'] if b_[1] in ('cfg_ctl', 'rom_ce'))]
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
{top_pins(mm, k)}
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
    cp, cw_ = g.get('col_pitch', COL_PITCH), g.get('col_w', COL_W)
    # field: W half, tier 2, columns 3..5 (one clock region) with its channel and the next region's edge
    xa = g['col_x']('W', 5) - 300.0
    w = {
        'field': (xa, g['ch_y'][2] - 100.0, xa + 3 * cp + 600.0, g['tier_y'][2] + 2700.0),
        'field_bf': None,
        'spine': (g['x_sp'] - 400.0, m['mid'] - 1400.0, g['x_fe'] + 400.0, m['mid'] + 1400.0),
        'band_s': (m['svcs']['SW'].x + 2500.0, 0.0, m['svcs']['SW'].x + 5500.0, m['svcs']['SW'].y + SVC_D + 900.0),
    }
    # the frame with the most BF pairs
    rb = max(f, key=lambda r: sum(1 for e in f[r]['elems'] if e[1] == 'BF'))
    fr = f[rb]
    w['field_bf'] = (fr['x'] - 1000.0, fr['y'] - 300.0, fr['x'] + cw_ + 1000.0, fr['y'] + 2600.0)
    hbf = [r for r in f if f[r].get('bundles')]
    if hbf:
        fr = f[hbf[len(hbf) // 2]]
        w['field_hb'] = (fr['x'] - 1000.0, fr['y'] - 300.0, fr['x'] + cw_ + 1000.0, fr['y'] + 2600.0)
    if NV_PAIRS:
        rn = max(f, key=lambda r: sum(1 for e in f[r]['elems'] if e[1] == 'NV'))
        fr = f[rn]
        w['field_nv'] = (fr['x'] - 1000.0, fr['y'] - 300.0, fr['x'] + cw_ + 1000.0, fr['y'] + 2600.0)
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
        if c <= y < c + chh(t) and g['x_fw'] <= x < g['x_le']:
            return f'channel{t}'
    for r in m['regions']:
        a, b, c, e = r['rect']
        if a <= x < c and b <= y < e:
            return r['name']
    if y < g['y_f'] or y >= g['y_top']:
        return 'band'
    return 'other'


# ================================================================================================ r8: the wired die
# CLAUDE S81-DIE (2026-10-06).  The r7 netlist (21fcf6469) was physically feasible but NOT wired (CLAUDE DIE-LINT,
# results/rtl/die_top_lint_20261006/findings.json S1-S17, TF1-TF7).  `--gen r8` builds the same die (same element
# masters, ROMs, PHYs, links, slabs, pair/BF/NV split, ragged return tree) with every die-level connection bound to a
# real port, and the forwarded links / clock-region crossings instantiated from their RTL:
#   x path      q-element x is two INPUT lanes (xs_q0 S face, xs_q1 N face): one 564-b lane stream per column
#               {x0 = q0,e0,ctl 283 | x1 = q1,e1 266 | cc = go,cfg_go,cfg_ph[10],cfg_np[3] 15} from the column's entry
#               meso FIFO (dsfd_cfifo, ot_meso_fifo W564) up a slot-station chain (dsfd_sstn_*, one registered stage per
#               slot, in the slot's cfg band); station k drives slot k's S-face pins; station k+1 re-buffers slot k's
#               q1/e1 to its N-face pins (qt) so both lanes arrive in the same cycle (S2, S6, S15a).
#   cfg         one ot_s81_cfg7_seq per pair (real RTL, exact gate rtl/v41die/test/tb_ot_s81_cfg7_seq.sv): shared
#               12-b row address, one ce per ROM, 7 x 48-b payload, registered bank select; drives the element cfg
#               port and gates go (S3a, S3b); the 7 cfg ROMs are mirrored (MY) so their pins face the sequencer (S15b).
#   return      leaf = the q lane's 63 b {pv, pval, prow, pseg, pnseg, perr, ppos}; every node is a generated wrapper
#               dsfd_node_<a><b>[f] of the REAL ot_v41_retn_w17w10 that packs a leaf exactly as ot_v41_field_w17w10
#               ({ppos, prow, pseg, 3'd0, pnseg}), with clk / rst_n from the column root and a registered fault chain
#               (S4a, S4b, S5); root -> column FIFO through dsfd_rstg register stages in a strip sub-column.
#   clocks      top ports refclk / por_n -> collective PLL / reset controller -> ONE net per domain (stream, serial,
#               hbm; TF1/S1) and per-domain reset nets (S8); each column FIFO is its column's clock/reset root (option C
#               region root): one column clock + reset net to every pair, ROM, sequencer, station, node (S6, S7).
#   forwarded   every die-level link is a chain of dsfd_stn_* stations, ONE ot_fwd_link_stage (W <= 512 slices) per
#               station, spaced <= 430.56 um, each lane with its own forwarded clock; bidirectional trunks split into
#               one chain per direction (S12b, S13); multi-lane return trunks carry one lane per column.
#   crossings   entry meso FIFO per column (dsfd_cfifo); hub-side end blocks: meso (lane -> local stream), ratio CDC
#               (lane -> serial VM) and start blocks (serial VM -> lane), all ot_meso_fifo / ot_ratio_cdc_fifo (S12a).
#   outputs     HC slab returns t_vm (S9, HC split around a crossing corridor at the VM's y so E-half chains cross
#               the spine column through stations); NV5 extension returns nvr to its pair (S10).
#   floorplan   TIER_COLS 9/11/12/12/11/9 (64 frames per half, unchanged) frees 2,288 um: a 259.2 um channel between
#               the spine and field column 0 on both halves (S14) that is the vertical corridor of the W/E chains, and
#               a 47.52 um return-stage sub-column per frame.
# Owner-block interfaces (VM, SU, HC, gather, capture, collective, selector, collector, scan service, controller, BF,
# NV5) stay placeholders with the port lists below; FINDINGS in results/rtl/dsrom_s81_fulldie_20261004/r8/.
TIER_COLS8 = (10, 11, 11, 11, 11, 10)
SPF = 518.4                         # spine <-> field column 0 channel (S14; 259.2 overflowed: W chains + VM pins)
RSC_W = 47.52                       # return-stage sub-column of the node strip
COL_W8 = 2 * LANE_W + NS_W + RSC_W  # 1,182.816
COL_PITCH8 = COL_W8 + 8.64
HC_CORR = 1209.6                    # HC split: E-half crossing corridor at the VM's y (604.8: GRT overflow, see r8 README)
VCH8 = 1209.6                       # r8 VCH (604.8 in r7; the r8 forwarded chains + hub CDC blocks overflowed it)
SPINE_W8 = SPINE_W + VCH8 - VCH
X0B, X1B, CCB = 283, 266, 15        # lane stream: x0 (q0 e0 + 17 ctl) | x1 (q1 e1) | cc (go cfg_go cfg_ph cfg_np)
LSW = X0B + X1B + CCB               # 564
LEAF, NODEB, STB = 63, 66, 2
CRET = NODEB + STB                  # column return payload: root word + {fault, busy}
STEP8 = 400.0                       # nominal forwarded-stage spacing (<= LINK_STAGE_UM after placement)
STEP9 = 425.0                       # r9: closer to the 430.56 um reach (the placement search still enforces it)
HSTN_DOM = dict(serial_0p9='serial', stream_1p2='stream')
SEQ_WH = (34.56, 60.48)
STACKS = dict(layer=('SW', 'SE', 'NW', 'NE'), head=('SW', 'SE', 'NW', 'NE'), layer1=('SW',))
HB_PITCH = (279.936, 280.8)                 # head element pitch (275.23 + halo, on the lattice)
HB_H = 2 * HB_PITCH[1]                      # one bundle: B + glue row, then 4 A row
HB_GLUE = (302.4, 151.2)                    # bundle glue: BST stages, lane skew, B demux, compare (RTL inside the bundle)
HB_GLUE_W = 14000 * FLOP_CLK_W * 1.5        # ~14k flops (2 x 512 BST + 16 lanes x up to 56-deep skew + compare)
SSTN_WH = (172.8, 30.24)            # wide and short: the 564-b stream pins spread at 3 tracks (r8 GRT: a 52 um station
                                    # piled the slot-to-slot stream into one M7 column over the element row)
CF_WH = (850.176, 47.52)
CF_WH_V2 = (432.0, 95.04)        # --cfifo-v2: same area, 2:1 squarer (the 850 x 47.5 slab had 671 ps CTS insertion)
CFIFO_V2 = False
RSTG_WH = (38.88, 34.56)
NVR = RET                           # NV5 draft-head result word back into its lm-head pair
SEQ_XL, SSTN_X, R_CFGX = 326.16, 365.04, 37.152
CF_X = 328.32                       # column FIFO x in the frame
GLUE_RTL = 'results/rtl/dsrom_s81_fulldie_20261004/r8/dsfd_glue.sv'
# Slot parameterisation (owner decision 2026-10-06: taller q-element slot, fewer elements per die, 55-60 % cell
# utilisation).  ELEM_FRAME_H = the element frame height in its slot (157.68 today: q / BF outline + halo); the slot is
# the cfg band (ELEM_DY) + the element frame + 4.32; SLOTS8 = the slots per column that fit the field height between
# the bands with a >= FIELD_MARGIN gap each side; PAIRS = pairs (elements) per die (configure(pairs=...)).
ELEM_FRAME_H = 157.68
FIELD_MARGIN = 216.0
SLOT_H8, SLOTS8 = SLOT_H, SLOTS


def slot_geometry(elem_frame_h=None, field_margin=None):
    global ELEM_FRAME_H, SLOT_H8, SLOTS8, FIELD_MARGIN
    if elem_frame_h:
        ELEM_FRAME_H = float(elem_frame_h)
    if field_margin is not None:
        FIELD_MARGIN = float(field_margin)
    SLOT_H8 = round(up(ELEM_DY + ELEM_FRAME_H + 4.32, GY), 3)
    band = up(EDGE, GY) + PHY_H + 8.64 + CTRL_D + 8.64 + SVC_D
    avail = DIE[1] - 2 * band - 2 * FIELD_MARGIN - sum(chh(t) for t in range(TIERS + 1))
    SLOTS8 = int(avail // (TIERS * SLOT_H8))
    return SLOT_H8, SLOTS8


def set_globals_pairs(p, b, n):
    global PAIRS, BF_PAIRS, NV_PAIRS
    PAIRS, BF_PAIRS, NV_PAIRS = p, b, n


def _frames_fit(slots, slot_h):
    """the r8 field packing (as build_r8) of the current PAIRS / BF / NV sets fits `slots` per column"""
    rng, hbf = frame_plan_r8()
    bfs, nvs = bf_sites(), nv_sites()
    for r in range(ROOTS):
        lo, hi = rng[r]
        slot, half_open, n = -1, None, hi - lo
        for p in range(lo, hi):
            if p in nvs:
                slot += 2
            elif p in bfs:
                slot += 1
            elif half_open is not None:
                half_open = None
            else:
                slot += 1
                half_open = slot
        if slot >= slots or 2 * n - 1 > int(slots * slot_h / NODE_FRAME[1] + 1e-6):
            return False
    return True


def frame_slots_needed(npairs_frame, bf_frac, nv_frac=0.0):
    nb = round(npairs_frame * bf_frac)
    nv = round(npairs_frame * nv_frac)
    q = npairs_frame - nb - nv
    return nb + 2 * nv + math.ceil(q / 2)


def capacity_report():
    """pairs per die that fit the r8 field at the current slot height, and the die count for the S81 deployment"""
    sh, sl = slot_geometry()
    keep = (PAIRS, BF_PAIRS, NV_PAIRS)
    best = 0
    for p in range(1000, 4000, 16):
        set_pairs(p)
        if _frames_fit(sl, sh):
            best = p
    for p in range(best, best + 16):
        set_pairs(p)
        if _frames_fit(sl, sh):
            best = p
    set_globals_pairs(*keep)
    flav = bf_flavour_capacity(sl, sh)
    inv = json.loads((ROOT / 'results/uarch/dsrom_c_w4_20261003/s82_inputs/inventory.json').read_text())
    total = 81 * 4 * 2417
    return dict(elem_frame_h_um=ELEM_FRAME_H, slot_h_um=sh, slots_per_column=sl, columns=ROOTS,
                max_pairs_per_layer_die=best, pairs_per_layer_die_now=2417,
                layer_field_pairs_total=total, layer_field_pairs_basis='81 stages x 4 ranks x 2,417 (S81 decision)',
                layer_dies_now=81 * 4, layer_dies_at_max=math.ceil(total / best) if best else None,
                extra_layer_dies=(math.ceil(total / best) - 81 * 4) if best else None,
                inventory_compiled_pairs_TP4=inv.get('compiled_pairs_TP4'),
                rack=dict(scan_dies_4stack=32, layer_dies_1stack=292, head_dies=12, table_dies=36, draft_dies=52,
                          total=424, layer_dies_total=324, head_bundles_per_head_die=math.ceil(129280 / 128 / 12),
                          source='results/arch/dsrom_s81_rack_20261006/rack.json (DS-RACK scenario C: 12 head + 36 '
                                 'table, 1-stack layer dies)'),
                meso_slot=dict(record=MESO_V7, um2_per_W512_slot=MESO_V7_UM2, cfifo_W564_slots=2,
                               cfifo_reservation_um2=round(CF_WH[0] * CF_WH[1], 1)),
                bf_per_region_flavours=flav)


def bf_flavour_capacity(sl, sh):
    """bf-double (2026-10-07): max pairs a layer die for the --bf-per-region flavours (4 = BF die, 0 = q-only die)"""
    global BF_PER_REGION
    keep, kb = (PAIRS, BF_PAIRS, NV_PAIRS), BF_PER_REGION
    out = {}
    for n in (4, 0):
        BF_PER_REGION, best = n, 0
        for p in range(ROOTS * max(n, 1), 4000):
            set_pairs(p)
            if not _frames_fit(sl, sh):
                break
            best = p
        out[str(n)] = dict(max_pairs=best, bf=n * ROOTS, slots_per_column=sl, slot_h_um=sh)
    BF_PER_REGION = kb
    set_globals_pairs(*keep)
    return out
CFG7_RTL = 'rtl/v41die/ot_s81_cfg7_seq.sv'
POWER8 = dict(
    seq=(80 * FLOP_CLK_W * 1.5, 'DERIVED ~80 loader flops x W18 per-flop clock x 1.5 (one cfg ROM read: in cfg)'),
    sstn=(LSW * FLOP_CLK_W * 1.5, 'DERIVED 564 stage flops x W18 per-flop clock x 1.5'),
    cfifo=(5 * LSW * FLOP_CLK_W * 1.5 + CRET * FLOP_CLK_W * 1.5,
           'DERIVED meso W564 D4 (4 ring + 1 output word) + return register x W18 per-flop clock x 1.5'),
    rstg=(NODEB * FLOP_CLK_W * 1.5, 'DERIVED 66 stage flops'),
    stn=(0.0, 'per station: lane bits x W18 per-flop clock x 1.5 (inst_power_r8)'),
    hend=(0.0, 'per end/start block: 5 x lane bits x W18 per-flop clock x 1.5 (inst_power_r8)'),
)


def real_ports_r8():
    qn = real_lef(Q_LEF)['name']
    ln = lambda m_: ['pv[%d]' % m_] + _bus('pval', 64)[32 * m_:32 * m_ + 32] + _bus('prow', 32)[16 * m_:16 * m_ + 16] \
        + _bus('pseg', 10)[5 * m_:5 * m_ + 5] + _bus('pnseg', 10)[5 * m_:5 * m_ + 5] + ['perr[%d]' % m_] \
        + _bus('ppos', 6)[3 * m_:3 * m_ + 3]
    qp = dict(x0=_bus('xs_q0', 256) + _bus('xs_e0', 10) + _bus('xs_b', 3) + _bus('xs_p', 8) + _bus('xs_pos', 3)
              + _bus('xs_sv', 2) + ['xs_v'],
              x1=_bus('xs_q1', 256) + _bus('xs_e1', 10), go=['go'], ck=['clk'], rs=['rst_n'],
              cfg=_bus('cfg_a', 5) + _bus('cfg_d', 48) + ['cfg_v'], r0=ln(0), r1=ln(1), st=['busy', 'fault'])
    assert len(qp['x0']) == X0B and len(qp['x1']) == X1B and len(qp['r0']) == LEAF
    assert len(set(qp['r0'] + qp['r1'])) == 2 * LEAF == RET
    cfg = dict(ck=['clk'], ce=['ce_in'], a=_bus('addr_in', 12), rd=_bus('rd_out', 48))
    phy = real_lef(PHY_LEF)
    dfi = sorted(phy['pins'], key=lambda p: (phy['pins'][p][1][0], p))
    sd = dict(tx=_bus('tx', 512), rx=_bus('rx', 512), ck=['clk'])
    out = {qn: qp, real_lef(CFG_LEF)['name']: cfg, phy['name']: dict(dfi=dfi), real_lef(SERDES_LEF)['name']: sd,
           real_lef(UCIE_LEF)['name']: sd}
    if HEAD_BUNDLES:
        he = dict(x=_bus('x', 256), go=['go'], ck=['clk'], rs=['rst_n'], row0=_bus('row0', 17), bv=['b_v'],
                  bd=_bus('b_d', 32), ov=['o_v'], od=_bus('o_d', 32), done=['done'], brow=_bus('best_row', 17),
                  bbits=_bus('best_bits', 32), bkey=_bus('best_key', 32), flt=['fault'])
        out[real_lef(HEAD_A_LEF)['name']] = he
        out[real_lef(HEAD_B_LEF)['name']] = he
    return out


# outputs no consumer reads in the RTL the die wiring follows (ot_dsrom_head_bundle): A root / logit streams, B logit
# stream and argmax (the B element is a root1024 producer only); cfg ROM spare columns rd_out[71:48]
UNUSED_BY_DESIGN = {('ot_dsrom_head_elem_A', p_) for p_ in ('o_v', 'o_d', 'l_v', 'l_d')} | \
    {('ot_dsrom_head_elem_B', p_) for p_ in ('l_v', 'l_d', 'done', 'best_row', 'best_bits', 'best_key', 'b_v', 'b_d')}


def HB_PER_FRAME():
    return int(SLOTS8 * SLOT_H8 / HB_H + 1e-6)


def frame_plan_r8():
    """frame -> (first pair, last pair + 1) and the head-bundle frames (head die r8: 5 bundles a frame, spread)"""
    hb = {}
    if HEAD_BUNDLES:
        nf = math.ceil(HEAD_BUNDLES / HB_PER_FRAME())
        fr = sorted({round((i + 0.5) * ROOTS / nf) for i in range(nf)})
        left = HEAD_BUNDLES
        for r in fr:
            hb[r] = min(HB_PER_FRAME(), left)
            left -= hb[r]
    rest = [r for r in range(ROOTS) if r not in hb]
    rng = {r: (0, 0) for r in hb}
    assert not hb or HB_PER_FRAME() >= 1
    for i, r in enumerate(rest):
        rng[r] = (math.floor(i * PAIRS / len(rest)), math.floor((i + 1) * PAIRS / len(rest)))
    return rng, hb


# ---------------------------------------------------------------------------------------- occupancy / placement
class Occ:
    """Spatial index of placed rectangles (200 um bins)."""

    def __init__(self, B=200.0):
        self.B, self.g = B, defaultdict(list)

    def _bins(self, x0, y0, x1, y1):
        B = self.B
        for a in range(int(x0 // B), int(x1 // B) + 1):
            for b in range(int(y0 // B), int(y1 // B) + 1):
                yield (a, b)

    def add(self, r):
        for k in self._bins(*r):
            self.g[k].append(r)

    def free(self, r, gap=0.0):
        x0, y0, x1, y1 = r
        for k in self._bins(x0 - gap, y0 - gap, x1 + gap, y1 + gap):
            for a0, b0, a1, b1 in self.g[k]:
                if a0 < x1 + gap - 1e-6 and x0 - gap < a1 - 1e-6 and b0 < y1 + gap - 1e-6 and y0 - gap < b1 - 1e-6:
                    return False
        return True


def _inside(r, rects):
    return any(r[0] >= a - 1e-6 and r[1] >= b - 1e-6 and r[2] <= c + 1e-6 and r[3] <= d + 1e-6 for a, b, c, d in rects)


def _mh(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


class Placer:
    def __init__(self, m):
        self.m, self.occ, self.n = m, Occ(), defaultdict(int)
        for it in m['insts']:
            self.occ.add(it.box())

    def add(self, it):
        self.m['insts'].append(it)
        self.occ.add(it.box())
        return it

    def near(self, cx, cy, w, h, allowed, prev=None, horiz=True, reach=None, span=72.0, rows=10):
        """Free lattice spot for a w x h block centred near (cx, cy) inside `allowed`, within `reach` of `prev`."""
        reach = reach or FWD_REACH
        al = [0.0]
        for i in range(1, int(span / 4.32) + 1):
            al += [-4.32 * i, 4.32 * i]
        cr = [0.0]
        step = (h if horiz else w) + 2.16
        for i in range(1, rows + 1):
            cr += [step * i, -step * i]
        cands = sorted(((a, c) for a in al for c in cr), key=lambda t_: abs(t_[0]) + 0.6 * abs(t_[1]))
        for a, c in cands:
            dx, dy = (a, c) if horiz else (c, a)
            x = dn(cx + dx - w / 2, GX)
            y = dn(cy + dy - h / 2, GY)
            r = (x, y, x + w, y + h)
            if not _inside(r, allowed) or not self.occ.free(r, 0.432):
                continue
            if prev is not None and _mh(prev, (x + w / 2, y + h / 2)) > reach:
                continue
            return x, y
        return None


def _poly_len(P):
    return sum(_mh(P[i], P[i + 1]) for i in range(len(P) - 1))


def _poly_at(P, s):
    """point and direction ('E','W','N','S') at path length s"""
    for i in range(len(P) - 1):
        L = _mh(P[i], P[i + 1])
        if s <= L + 1e-9 or i == len(P) - 2:
            a, b = P[i], P[i + 1]
            f = 0.0 if L == 0 else min(1.0, max(0.0, s / L))
            pt = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            d = ('E' if b[0] > a[0] else 'W') if abs(b[0] - a[0]) > abs(b[1] - a[1]) else ('N' if b[1] > a[1] else 'S')
            return pt, d
        s -= L
    return P[-1], 'E'


def face_need(bits):
    """face length for ports of these widths, at k = 1 (pitch 0.048) and in the k = 16 bundled GRT view"""
    k1 = sum(b * 0.048 for b in bits) + 0.144 * len(bits)
    k16 = sum(max(1, math.ceil(b / 16)) * 0.768 + 0.93 for b in bits)
    return max(k1, k16) + 2.0


def stn_dims(lanes, horiz):
    """station size: pins of every lane (fclk + data) on the input and the output face; ~0.7 um2 a stage bit"""
    pins = sum(w + 1 for w in lanes)
    bits = sum(lanes)
    face = face_need([b for w in lanes for b in (1, w)])
    if horiz:
        h = up(max(face, 17.28), GY)
        w = up(max(17.28, bits * 0.7 / h), GX)
    else:
        w = up(max(face, 17.28), GX)
        h = up(max(17.28, bits * 0.7 / w), GY)
    return w - SHAVE, h - SHAVE


def stn_master(lanes, horiz):
    sig = '_'.join(f'{w}x{n}' for w, n in _rle(lanes))
    return f'dsfd_stn{"h" if horiz else "v"}_{sig}'


def _rle(xs):
    out = []
    for x in xs:
        if out and out[-1][0] == x:
            out[-1][1] += 1
        else:
            out.append([x, 1])
    return out


class Chains:
    """forwarded-link chain builder: stations (one ot_fwd_link_stage per lane slice), nets, records"""

    def __init__(self, m, P):
        self.m, self.P, self.B = m, P, m['buses']
        self.rec = []          # (chain, stations, max_hop_um, length_um)

    def bus(self, bid, cls, bits, eps):
        self.B.append((bid, cls, bits, eps))

    def run(self, name, lanes, path, allowed, src, forced=(), first_prev=None, kind='stn', reach=None):
        """Place stations along polyline `path` for a chain of `lanes` (list of data widths).  `forced`: path lengths
        where a station MUST stand (taps / branches).  Returns [(inst, s_along)].  src: (x, y) of the source pin."""
        L = _poly_len(path)
        stops = sorted(set(round(s, 3) for s in forced if 0 < s <= L + 1e-6))
        out, pos, cur = [], 0.0, src
        end = path[-1]
        fi = 0
        while True:
            nxt = stops[fi] if fi < len(stops) else None
            R_ = reach or FWD_REACH
            if nxt is None and _mh(cur, end) <= R_ - 30.0 and L - pos <= R_ - 30.0:
                break
            step = STEP9 if REV == 'r9' else STEP8
            if FWD_REACH < LINK_STAGE_UM:
                step = min(step, FWD_REACH - 5.0)
            if reach:                        # common-clock chains (CC_REACH): station step inside the shorter reach
                step = min(step, reach - 5.0)
            if nxt is not None and nxt - pos <= step:
                target, must = nxt, True
                fi += 1
            else:
                target, must = min(pos + step, L), False
            placed = None
            t_ = target
            if must and target - pos <= 20.0 and out:
                continue                     # the previous station stands at this stop
            while placed is None and (t_ > pos + 20.0 or must):
                (cx, cy), d = _poly_at(path, t_)
                horiz = d in 'EW'
                w, h = stn_dims(lanes, horiz)
                placed = self.P.near(cx, cy, w, h, allowed, prev=cur, horiz=horiz, reach=reach)
                if placed is None:
                    if must:
                        placed = self.P.near(cx, cy, w, h, allowed, prev=None, horiz=horiz, span=200.0, rows=16)
                        break
                    t_ -= 25.0
            if placed is None:            # widen the search (still within reach of the previous station)
                t_ = max(pos + 20.0, target - 150.0)
                (cx, cy), d = _poly_at(path, t_)
                horiz = d in 'EW'
                w, h = stn_dims(lanes, horiz)
                placed = self.P.near(cx, cy, w, h, allowed, prev=cur, horiz=horiz, span=300.0, rows=24, reach=reach)
            if placed is None:
                raise RuntimeError(f'chain {name}: no station spot near s={target:.0f} of {L:.0f} ({cx:.0f}, {cy:.0f})')
            x, y = placed
            orient = {'E': 'R0', 'W': 'MY', 'N': 'R0', 'S': 'MX'}[d]
            self.P.n[name] += 1
            it = Inst(f'f_{name}_{self.P.n[name]}', stn_master(lanes, horiz), x, y, w, h, orient, kind='stn',
                      region='link', domain='fwd')
            it.power_w = sum(lanes) * FLOP_CLK_W * 1.5
            self.P.add(it)
            c = (x + w / 2, y + h / 2)
            out.append((it, max(t_, pos + 1.0), _mh(cur, c)))
            cur, pos = c, max(t_, pos + 1.0)
        self.rec.append(dict(chain=name, lanes=list(lanes), stations=len(out), length_um=round(L, 1),
                             max_hop_um=round(max([h_ for _, _, h_ in out] + [_mh(cur, end)]), 1),
                             last_hop_um=round(_mh(cur, end), 1)))
        return out


def MESO_P():
    # d8g1 (S81-RERUN fail-fast): GUARD_LO 1 gives the crossing arcs 1.5 T (meso / cfifo views SS -65..+14 at T/2)
    return ", .DEPTH(8), .OFFSET(4), .GUARD_LO(1), .GUARD_HI(7), .CREDITS(16)" if MESO_D8 else ''


HOP_FWD_CLS = ('lane',)
HOP_SKIP = ('clock_trunk', 'reset', 'reset_tree', 'clock', 'col_clock', 'col_reset', 'top_in', 'fclk', 'phy_dfi',
            'hbm_read')


def _anchor(Mx, it, port):
    """die coordinates of a port's anchor (generated face centre) on a placed instance; None for real macros"""
    p = Mx.ports.get(pslice(port)[0]) if Mx is not None else None
    if not p or p[0] != 'face':
        return None
    _, _, face, _, c, _ = p
    ax, ay = {'N': (c, Mx.h), 'S': (c, 0.0), 'E': (Mx.w, c), 'W': (0.0, c)}[face]
    if it.orient in ('MY', 'R180'):
        ax = it.w - ax
    if it.orient in ('MX', 'R180'):
        ay = it.h - ay
    return it.x + ax, it.y + ay


def hop_plan(m):
    """pass 1 of --hop-fix: every driver -> load hop (pin anchors) over its reach"""
    M = masters(m, 1)
    by = {it.name: it for it in m['insts']}
    plan = {}
    for bid, cls, bits, eps in m['buses']:
        if cls in HOP_SKIP or len(eps) < 2 or eps[0][0] == 'TOP':
            continue
        d = by[eps[0][0]]
        a = _anchor(M.get(d.master), d, eps[0][1]) or (d.x + d.w / 2, d.y + d.h / 2)
        R = HOP_R_FWD if cls in HOP_FWD_CLS else HOP_R_CC
        for e in eps[1:]:
            if e[0] == 'TOP':
                continue
            l_ = by[e[0]]
            b = _anchor(M.get(l_.master), l_, e[1]) or (l_.x + l_.w / 2, l_.y + l_.h / 2)
            L = _mh(a, b)
            hard = PIN_RELAY and not (is_glue(d.master) and is_glue(l_.master))
            if L > R or (hard and L > PIN_SEG):
                plan[(eps[0][0], eps[0][1], e[0], e[1])] = (round(L, 1), a, b, cls)
    return plan


def build_r8(variant=None):
    global HOP_PLAN
    if HOP_FIX and HOP_PLAN is None:
        HOP_PLAN = {}
        m0 = build_r8(variant)
        finalize_r8(m0)
        HOP_PLAN = hop_plan(m0)
        RLY_FACES.clear()
    variant = dict(variant or {})
    W, H = DIE
    insts, regions, notes = [], [], []
    bounds, bfs, nvs = region_bounds(), bf_sites(), nv_sites()
    COLS8 = max(TIER_COLS8)
    x_lw = up(EDGE, GX)
    slack = W - 2 * x_lw - 2 * LINK_COL - 2 * COLS8 * COL_PITCH8 - SPINE_W8 - 2 * SPF
    assert slack >= 0, slack
    x_fw = up(x_lw + LINK_COL + 0.5 * slack, GX)
    x_sp = up(x_fw + COLS8 * COL_PITCH8 - 8.64 + SPF, GX)       # spine W edge
    x_fe = up(x_sp + SPINE_W8, GX)                                # spine E edge
    x_le = dn(W - EDGE - LINK_COL, GX)
    assert x_fe + SPF + COLS8 * COL_PITCH8 <= x_le + 1e-6
    band = up(EDGE, GY) + PHY_H + 8.64 + CTRL_D + 8.64 + SVC_D
    SLOT_H, SLOTS = slot_geometry()
    field_h = TIERS * SLOTS * SLOT_H + sum(chh(t_) for t_ in range(TIERS + 1))
    y_f = up((H - field_h) / 2, GY)
    ch_y = [y_f + t * SLOTS * SLOT_H + sum(chh(t_) for t_ in range(t)) for t in range(TIERS + 1)]
    tier_y = [c + chh(t) for t, c in enumerate(ch_y[:TIERS])]
    y_top = ch_y[TIERS] + chh(TIERS)

    def col_x(half, c):
        return dn(x_sp - SPF - (c + 1) * COL_PITCH8 + 8.64, GX) if half == 'W' else up(x_fe + SPF + c * COL_PITCH8, GX)
    geo = dict(slot_h=SLOT_H, slots=SLOTS, x_lw=x_lw, x_fw=x_fw, x_sp=x_sp, x_fe=x_fe, x_le=x_le, y_f=y_f, y_top=y_top, ch_y=ch_y, tier_y=tier_y,
               band_depth=band, field_h=field_h, spine_cx=x_sp + SPINE_W8 / 2, col_x=col_x, col_pitch=COL_PITCH8,
               col_w=COL_W8, spf=SPF, tier_cols=list(TIER_COLS8))
    rq, rc = real_lef(Q_LEF), real_lef(CFG_LEF)
    frames, slot_of = {}, {}
    order = [(h, t, c) for h in 'WE' for t in range(TIERS) for c in range(TIER_COLS8[t])]
    assert len(order) == ROOTS
    rng, hbf = frame_plan_r8()
    for r, (half, t, c) in enumerate(order):
        x0, y0 = col_x(half, c), tier_y[t]
        frames[r] = dict(half=half, tier=t, col=c, x=x0, y=y0)
        regions.append(dict(name=f'frame_{r}', kind='field', rect=[x0, y0, x0 + COL_W8, y0 + SLOTS * SLOT_H]))
        if r in hbf:
            # head-bundle frame: per bundle a row (B element + glue) under a row of the 4 A elements
            ra_, rb_ = real_lef(HEAD_A_LEF), real_lef(HEAD_B_LEF)
            frames[r].update(elems=[], bundles=hbf[r], last_slot=hbf[r] - 1, ret_stages=0)
            for b in range(hbf[r]):
                yb = y0 + b * HB_H + 4.32
                g = f'g{r}_{b}'
                insts.append(Inst(f'{g}b', rb_['name'], x0 + 4.32, yb, rb_['w'], rb_['h'], kind='hb_elem',
                                  region=f'frame_{r}', power_w=HEAD_ELEM_W['B']))
                insts.append(Inst(g, 'dsfd_hbglue', x0 + 4.32 + HB_PITCH[0], yb + 64.8, HB_GLUE[0] - SHAVE,
                                  HB_GLUE[1] - SHAVE, kind='hbglue', region=f'frame_{r}', power_w=HB_GLUE_W))
                for q in range(4):
                    insts.append(Inst(f'{g}a{q}', ra_['name'], x0 + 4.32 + q * HB_PITCH[0], yb + HB_PITCH[1],
                                      ra_['w'], ra_['h'], kind='hb_elem', region=f'frame_{r}', power_w=HEAD_ELEM_W['A']))
            insts.append(Inst(f'cf{r}', 'dsfd_cfifo', x0 + CF_X, ch_y[t] + chh(t) - 4.32 - CF_WH[1], CF_WH[0] - SHAVE,
                              CF_WH[1] - SHAVE, kind='cfifo', region=f'frame_{r}'))
            continue
        pairs = list(range(*rng[r]))
        slot, half_open, elems = -1, None, []
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
        assert slot < SLOTS, f'frame {r}: {len(pairs)} pairs need {slot + 1} slots > {SLOTS} at slot height {SLOT_H}'
        assert 2 * len(pairs) - 1 <= int(SLOTS * SLOT_H / NODE_FRAME[1] + 1e-6), f'frame {r}: return strip overflow'
        frames[r]['elems'] = elems
        frames[r]['last_slot'] = slot
        for p, kind, s, ln in elems:
            sy = y0 + s * SLOT_H
            ex = x0 + (LANE_W if ln == 'R' else 0) + 4.32
            if kind == 'NV':
                it = Inst(f'e{p}', 'dsfd_bfnv', ex, sy + ELEM_DY, 1002.888, ELEM_FRAME_H - SHAVE, kind='bf_nv',
                          region=f'frame_{r}')
                nh = up(NVX_UM2 / 1002.888, GY)
                insts.append(Inst(f'v{p}', 'dsfd_nvx', ex, sy + SLOT_H + CFG_DY, 1002.888, nh - SHAVE, kind='nvx',
                                  region=f'frame_{r}'))
            elif kind == 'BF':
                it = Inst(f'e{p}', 'dsfd_bf', ex, sy + ELEM_DY, 1002.888, ELEM_FRAME_H - SHAVE, kind='bf', region=f'frame_{r}')
            else:
                assert rq['h'] <= ELEM_FRAME_H, (rq['h'], ELEM_FRAME_H)
                it = Inst(f'e{p}', rq['name'], ex, sy + ELEM_DY, rq['w'], rq['h'], kind='q', region=f'frame_{r}')
            insts.append(it)
            slot_of[p] = (r, s, ln)
            # L lane / BF: ROMs (mirrored, pins east) then the sequencer, east of them, toward the slot station;
            # R lane: the sequencer (mirrored) first, west of its ROMs (pins west), facing the station on its west
            if ln == 'R':
                sx = x0 + LANE_W + R_CFGX
                cx0, ro, so = sx + SEQ_WH[0] + 3.888, 'R0', 'MY'
            else:
                cx0, ro, so = x0 + 4.32, 'MY', 'R0'
                sx = cx0 + (CFG_PER_PAIR - 1) * CFG_PITCH + rc['w'] + 3.888
            for j in range(CFG_PER_PAIR):
                insts.append(Inst(f'c{p}_{j}', rc['name'], cx0 + j * CFG_PITCH, sy + CFG_DY, rc['w'], rc['h'], ro,
                                  kind='cfg', region=f'frame_{r}'))
            insts.append(Inst(f's{p}', 'ot_s81_cfg7_seq', sx, sy + CFG_DY, SEQ_WH[0] - SHAVE, SEQ_WH[1] - SHAVE, so,
                              kind='seq', region=f'frame_{r}'))
        # slot stations (one per used slot), above the NV extension in an NV slot
        nvslots = {s + 1 for p, kind, s, ln in elems if kind == 'NV'}
        if slot in nvslots:
            slot -= 1                  # a top slot holding only an NV extension needs no station
            frames[r]['last_slot'] = slot
            frames[r]['nv_top'] = True
        for s in range(slot + 1):
            sy = y0 + s * SLOT_H
            yy = sy + CFG_DY if s not in nvslots else sy + CFG_DY + up(NVX_UM2 / 1002.888, GY) + 4.32
            insts.append(Inst(f't{r}_{s}', 'dsfd_sstn', x0 + SSTN_X, yy, SSTN_WH[0] - SHAVE, SSTN_WH[1] - SHAVE,
                              kind='sstn', region=f'frame_{r}'))
        if REV == 'r9':
            for p, kind, s, ln in elems:
                if kind == 'q':
                    insts += _q_banks(p, x0 + (LANE_W if ln == 'R' else 0) + 4.32, y0 + s * SLOT_H + ELEM_DY, rq,
                                      f'frame_{r}')
        nodes, root = return_tree(2 * len(pairs))
        frames[r]['tree'] = (nodes, root)
        rank = _inorder_rank(nodes, root)
        for j, (nid, a, b) in enumerate(nodes):
            insts.append(Inst(f'n{r}_{j}', 'dsfd_node', x0 + 2 * LANE_W + 4.32, y0 + rank[nid] * NODE_FRAME[1],
                              NODE_FRAME[0] - SHAVE, NODE_FRAME[1] - SHAVE, kind='node', region=f'frame_{r}'))
        # column FIFO: entry meso + column clock / reset root + return register, top band of the channel below
        insts.append(Inst(f'cf{r}', 'dsfd_cfifo', x0 + CF_X, ch_y[t] + chh(t) - 4.32 - CF_WH[1], CF_WH[0] - SHAVE,
                          CF_WH[1] - SHAVE, kind='cfifo', region=f'frame_{r}'))
    # ---- spine: W column as r7 (SU split around the centre stack), E column HC split around a crossing corridor
    x_vch = x_sp + dn((SPINE_W8 - VCH8) / 2, GX)
    cw = dn((SPINE_W8 - VCH8) / 2, GX)
    x_spe = x_vch + VCH8
    regions.append(dict(name='spine', kind='hub', rect=[x_sp, y_f, x_fe, y_top]))
    regions.append(dict(name='vch', kind='channel', rect=[x_vch, y_f, x_vch + VCH8, y_top]))
    mid = (y_f + y_top) / 2
    hub = {}

    def slab(name, mm2, x, y, w, dom='stream_1p2', master=None):
        h = up(mm2 * 1e6 / w, GY)
        it = Inst(f'sp_{name}', master or f'dsfd_sp_{name}', x, y, w - SHAVE, h - SHAVE, kind='hub', region='spine',
                  domain=dom)
        insts.append(it)
        hub[name] = it
        return it
    centre = ['gather', 'vm', 'capture', 'collective']
    centre_area = dict(HUB_MM2)
    wfc_rect = None
    if DIE_KIND == 'layer':
        centre.insert(2, 'wfc')
        centre_area.update(vm=2.659905216, wfc=0.45610905599999996)
    ch_ = sum(up(centre_area[n] * 1e6 / cw, GY) for n in centre) + (len(centre) - 1) * SPINE_GAP
    yc = dn(mid - ch_ / 2, GY)
    su_lo = HUB_MM2['su'] * (yc - y_f) / (yc - y_f + y_top - (yc + ch_))
    slab('su_s', su_lo, x_sp, dn(yc - SPINE_GAP - up(su_lo * 1e6 / cw, GY), GY), cw, dom='serial_0p9')
    yy = yc
    for n in centre:
        if n == 'wfc':
            wh = up(centre_area[n] * 1e6 / cw, GY)
            wfc_rect = [x_sp, yy, x_sp + cw, yy + wh]
        else:
            slab(n, centre_area[n], x_sp, yy, cw, dom='serial_0p9' if n == 'vm' else 'stream_1p2')
        yy += up(centre_area[n] * 1e6 / cw, GY) + SPINE_GAP
    slab('su_n', HUB_MM2['su'] - su_lo, x_sp, yy, cw, dom='serial_0p9')
    vm = hub['vm']
    corr_c = vm.y - SPINE_GAP / 2          # corridor at the gather / VM boundary: the E-half returns exit it at gather
    c0, c1 = dn(corr_c - HC_CORR / 2, GY), up(corr_c + HC_CORR / 2, GY)
    lo_av, hi_av = c0 - (band + SPINE_GAP), (H - band - SPINE_GAP) - c1      # HC halves sized to the room each side
    fs = lo_av / (lo_av + hi_av)
    hs_ = up(HUB_MM2['hc'] * fs * 1e6 / cw, GY)
    slab('hc_s', HUB_MM2['hc'] * fs, x_spe, dn(c0 - hs_, GY), cw, dom='serial_0p9')
    slab('hc_n', HUB_MM2['hc'] * (1 - fs), x_spe, c1, cw, dom='serial_0p9')
    regions.append(dict(name='hc_corridor', kind='channel', rect=[x_spe, c0, x_fe, c1]))
    for it in insts:
        if it.region == 'spine':
            assert it.y >= band + SPINE_GAP and it.y + it.h <= H - band - SPINE_GAP, (it.name, it.y, it.y + it.h)
    # ---- bands (as r7)
    rp = real_lef(PHY_LEF)
    phys, ctrls, svcs = {}, {}, {}
    xs_phy = [up(x_fw + (x_sp - x_fw) / 2 - PHY_W / 2, GX), up(x_fe + (x_le - x_fe) / 2 - PHY_W / 2, GX)]
    band_ys = {}
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
            band_ys[side] = ys_
            if st not in STACKS[DIE_KIND]:
                continue           # 1-stack layer die (scenario C): only the SW stack is built
            phys[st] = Inst(f'phy_{st}', rp['name'], xp, yp, rp['w'], rp['h'], orient, kind='phy', region='phy',
                            domain='hbm')
            ctrls[st] = Inst(f'ctrl_{st}', 'dsfd_ctrl', xp, yc_, PHY_W - SHAVE, CTRL_D - SHAVE, orient, kind='ctrl',
                             region='ctrl', domain='hbm')
            svcs[st] = Inst(f'svc_{st}', 'dsfd_svc', xp, ys_, PHY_W - SHAVE, SVC_D - SHAVE, orient, kind='svc',
                            region='svc')
            insts += [phys[st], ctrls[st], svcs[st]]
            regions.append(dict(name=f'svc_{st}', kind='svc', rect=[xp, min(yc_, ys_), xp + PHY_W,
                                                                    max(yc_ + CTRL_D, ys_ + SVC_D)]))
    gap_x0, gap_x1 = xs_phy[0] + PHY_W, xs_phy[1]
    for side, name in (('S', 'selector'), ('N', 'collector')):
        w = dn(min(gap_x1 - gap_x0 - 2 * 8.64, 2 * SPINE_W), GX)
        h = up(HUB_MM2[name] * 1e6 / w, GY)
        x = up((gap_x0 + gap_x1) / 2 - w / 2, GX)
        y = band_ys[side] if side == 'S' else band_ys[side] + SVC_D - h
        it = Inst(f'bk_{name}', f'dsfd_bk_{name}', x, y, w - SHAVE, h - SHAVE, kind='band_blk', region='svc')
        insts.append(it)
        hub[name] = it
    rs_, ru_ = real_lef(SERDES_LEF), real_lef(UCIE_LEF)
    links = []
    for side in 'WE':
        stack = [('ucie', ru_), ('serdes', rs_), ('serdes', rs_), ('serdes', rs_)]
        tot = sum(m_['h'] for _, m_ in stack) + 3 * 43.2
        y = up(mid - tot / 2, GY)
        for i, (kind, m_) in enumerate(stack):
            if side == 'W':
                x, orient = x_lw, ('R0' if kind == 'serdes' else 'MY')
                if LINK_FIX and kind == 'serdes':       # ck on the die-edge face: the ck relay takes the edge side
                    x = dn(x_lw + LINK_COL - m_['w'], GX)
            else:
                x, orient = up(x_le + LINK_COL - m_['w'], GX), ('MY' if kind == 'serdes' else 'R0')
                if LINK_FIX and kind == 'serdes':
                    x = up(x_le, GX)
            it = Inst(f'lk_{side}{i}', m_['name'], x, y, m_['w'], m_['h'], orient, kind='link', region='link',
                      domain='link')
            insts.append(it)
            links.append(it)
            y = up(y + m_['h'] + 43.2, GY)
    variant.update(gen='r8', geometry_fix=GEOMETRY_FIX, cfifo_v2=CFIFO_V2, link_fix=LINK_FIX, link_split=LINK_SPLIT, sel_xstg=SEL_XSTG, pin_relay=PIN_RELAY, ch_heights=CHS, vch_w=VCH8, hc_corr=HC_CORR, hc_xface=HC_XFACE, hop_fix=HOP_FIX, meso_d8=MESO_D8, fwd_pitch=FWD_REACH, corr_interleave=CORR_INTERLEAVE, rev=REV, cc_reach_um=CC_REACH, vch_interleave=VCH_INTERLEAVE, q_lef=Q_LEF, head_dies=HEAD_DIES, die=DIE_KIND, role=dict(layer='scan die (4 HBM3E stacks; 32 of the rack)',
                                                    layer1='layer die, 1 HBM3E stack (292 of the rack)',
                                                    head='head die (4 stacks; 12 of the rack)')[DIE_KIND],
                   pairs=PAIRS, bf=BF_PAIRS, nv=NV_PAIRS, head_bundles=HEAD_BUNDLES, stacks=list(STACKS[DIE_KIND]),
                   elem_frame_h=ELEM_FRAME_H, slot_h=SLOT_H, slots=SLOTS)
    m = dict(geo=geo, insts=insts, regions=regions, frames=frames, cregions=[], fifo_of={}, hub=hub, phys=phys,
             ctrls=ctrls, svcs=svcs, links=links, notes=notes, slot_of=slot_of, x_vch=x_vch, x_spe=x_spe, mid=mid,
             corridor=(c0, c1), variant=variant, gap_x=(gap_x0, gap_x1))
    spine_y0 = min(it.y for it in insts if it.region == 'spine')
    spine_y1 = max(it.y + it.h for it in insts if it.region == 'spine')
    for reg in regions:
        if reg['name'] in ('spine', 'vch'):
            reg['rect'][1] = min(reg['rect'][1], spine_y0)
            reg['rect'][3] = max(reg['rect'][3], spine_y1)
    if DIE_KIND == 'layer':
        reservation = json.loads((ROOT / 'results/uarch/dsrom_s81_wfc_parent_allocation_20261006/model.json').read_text())
        x0, y0, x1, y1 = wfc_rect
        reservation['selected_WFC_gross_um'] = wfc_rect
        reservation['selected_WFC_core_um'] = [x0 + 17.28, y0 + 17.28, x1 - 17.28, y1 - 17.28]
        assert all(not (it.x < x1 and it.x + it.w > x0 and it.y < y1 and it.y + it.h > y0) for it in insts)
        m['child_reservations'] = {'wfc': reservation}
        regions.append(dict(name='wfc_selected_child', kind='soft_child_reservation', rect=[x0, y0, x1, y1]))
        m['wfc_rect'] = wfc_rect
    m['buses'] = []
    buses_r8(m)
    return m


# ---------------------------------------------------------------------------------------- r8 nets
def _corridors(m):
    g = m['geo']
    W, H = DIE
    b0, b1 = g['band_depth'] + 4.32, H - g['band_depth'] - 4.32
    cor = dict(
        s14W=(g['x_sp'] - SPF + 4.32, b0, g['x_sp'] - 4.32, b1),
        s14E=(g['x_fe'] + 4.32, b0, g['x_fe'] + SPF - 4.32, b1),
        vch=(m['x_vch'] + 4.32, b0, m['x_vch'] + VCH8 - 4.32, b1),
        hcc=(m['x_spe'] - 4.32, m['corridor'][0] + 4.32, g['x_fe'] + 4.32, m['corridor'][1] - 4.32),
        edgeW=(g['x_lw'] + LINK_COL + 4.32, g['y_f'], g['x_fw'] - 4.32, g['y_top']),
        edgeE=(g['x_le'] - (g['x_fw'] - g['x_lw'] - LINK_COL) + 4.32, g['y_f'], g['x_le'] - 4.32, g['y_top']),
        stripS=(g['x_lw'] + LINK_COL + 4.32, g['band_depth'] + 4.32, g['x_le'] - 4.32, g['y_f'] - 4.32),
        stripN=(g['x_lw'] + LINK_COL + 4.32, g['y_top'] + 4.32, g['x_le'] - 4.32, H - g['band_depth'] - 4.32),
        gapS=(m['gap_x'][0] + 4.32, 20.0, m['gap_x'][1] - 4.32, g['y_f'] - 4.32),
        gapN=(m['gap_x'][0] + 4.32, g['y_top'] + 4.32, m['gap_x'][1] - 4.32, H - 20.0))
    for t, c in enumerate(g['ch_y']):
        cor[f'ch{t}'] = (g['x_lw'] + LINK_COL + 4.32, c + 4.32, g['x_le'] - 4.32, c + chh(t) - 4.32 - CF_WH[1] - 2.16)
    return cor


def buses_r8(m):
    """All r8 nets (endpoint 0 = the driver) and the glue instances they need."""
    g, B = m['geo'], m['buses']
    P = Placer(m)
    CH8 = Chains(m, P)
    m['chains'] = CH8.rec
    by = {it.name: it for it in m['insts']}
    hub = m['hub']
    cor = _corridors(m)

    def bus(bid, cls, bits, eps):
        B.append((bid, cls, bits, eps))
    # ---------------- head-bundle frames (head die): column stream up a glue chain, result chain down
    for r, f in m['frames'].items():
        if not f.get('bundles'):
            continue
        cf = f'cf{r}'
        nb = f['bundles']
        col_ck, col_rs = [(cf, 'co')], [(cf, 'rs')]
        for b in range(nb):
            gn = f'g{r}_{b}'
            el = [f'{gn}b'] + [f'{gn}a{q}' for q in range(4)]
            col_ck += [(gn, 'ck')] + [(e, 'ck') for e in el]
            col_rs += [(gn, 'rs')] + [(e, 'rs') for e in el]
            src = cf if b == 0 else f'g{r}_{b - 1}'
            bus(f'hxa_{r}_{b}', 'x_lane', X0B, [(src, 'xa'), (gn, 'xai')])
            bus(f'hxb_{r}_{b}', 'x_lane', X1B, [(src, 'xb'), (gn, 'xbi')])
            bus(f'hcc_{r}_{b}', 'x_ctl', CCB, [(src, 'cc'), (gn, 'cci')])
            bus(f'hso_{r}_{b}', 'stat', STB, [(gn, 'so'), ((f'g{r}_{b - 1}', 'si') if b else (cf, 'st'))])
            bus(f'hro_{r}_{b}', 'col_ret', NODEB, [(gn, 'ro'), ((f'g{r}_{b - 1}', 'ri') if b else (cf, 'ri'))])
            # glue -> elements (skewed x lanes, go, row0, B root demux) and elements -> glue (argmax, B root, fault)
            bus(f'hex_{r}_{b}a', 'hb_x', 256, [(gn, 'xsa')] + [(f'{gn}a{q}', 'x') for q in range(4)])
            bus(f'hex_{r}_{b}b', 'hb_x', 256, [(gn, 'xsb'), (f'{gn}b', 'x')])
            bus(f'hgo_{r}_{b}', 'go', 1, [(gn, 'go')] + [(e, 'go') for e in el])
            bus(f'hbd_{r}_{b}', 'hb_root', 32, [(gn, 'bd')] + [(f'{gn}a{q}', 'bd') for q in range(4)])
            bus(f'hbov_{r}_{b}', 'hb_root', 1, [(f'{gn}b', 'ov'), (gn, 'bov')])
            bus(f'hbod_{r}_{b}', 'hb_root', 32, [(f'{gn}b', 'od'), (gn, 'bod')])
            bus(f'hr0b_{r}_{b}', 'hb_ctl', 17, [(gn, 'r0b'), (f'{gn}b', 'row0')])
            bus(f'hbf_{r}_{b}', 'stat', 1, [(f'{gn}b', 'flt'), (gn, 'bflt')])
            for q in range(4):
                a = f'{gn}a{q}'
                bus(f'hr0_{r}_{b}_{q}', 'hb_ctl', 17, [(gn, f'r0a{q}'), (a, 'row0')])
                bus(f'hbv_{r}_{b}_{q}', 'hb_root', 1, [(gn, f'bv{q}'), (a, 'bv')])
                for pt, w_ in (('done', 1), ('brow', 17), ('bbits', 32), ('bkey', 32), ('flt', 1)):
                    bus(f'h{pt}_{r}_{b}_{q}', 'hb_res', w_, [(a, pt), (gn, f'a{q}{pt}')])
        bus(f'ck_col_{r}', 'col_clock', 1, col_ck)
        bus(f'rs_col_{r}', 'col_reset', 1, col_rs)
    # ---------------- field, per frame
    for r, f in m['frames'].items():
        if f.get('bundles'):
            continue
        cf = f'cf{r}'
        elems = f['elems']
        last = f['last_slot']
        slot_elems = defaultdict(list)
        for p, kind, s, ln in elems:
            slot_elems[s].append((p, kind, ln))
        nvslots = {s + 1: p for p, kind, s, ln in elems if kind == 'NV'}
        col_ck = [(cf, 'co')]
        col_rs = [(cf, 'rs')]
        # stations
        for s in range(last + 1):
            t_ = f't{r}_{s}'
            col_ck.append((t_, 'ck'))
            col_rs.append((t_, 'rs'))
            if s == 0:
                bus(f'xa_{r}_0', 'x_lane', X0B, [(cf, 'xa'), (t_, 'xai')])
                bus(f'xb_{r}_0', 'x_lane', X1B, [(cf, 'xb'), (t_, 'xbi')])
                bus(f'cc_{r}_0', 'x_ctl', CCB, [(cf, 'cc'), (t_, 'cci')])
        # elements, sequencers, ROMs, status
        for s in range(last + 1):
            t_ = f't{r}_{s}'
            es = slot_elems.get(s, [])
            xa_eps, xb_eps, cc_eps = [], [], []
            for j, (p, kind, ln) in enumerate(es):
                e, sq = f'e{p}', f's{p}'
                xa_eps.append((e, 'x0'))
                if kind in ('BF', 'NV'):
                    xb_eps.append((e, 'x1'))
                cc_eps.append((sq, 'lc'))
                col_ck += [(e, 'ck'), (sq, 'clk')] + [(f'c{p}_{k}', 'ck') for k in range(CFG_PER_PAIR)]
                col_rs += [(e, 'rs'), (sq, 'rst_n')]
                bus(f'cfg_{p}', 'cfg', CFGB, [(sq, 'cfg'), (e, 'cfg')])
                bus(f'go_{p}', 'go', 1, [(sq, 'go_e'), (e, 'go')])
                bus(f'ra_{p}', 'rom_a', 12, [(sq, 'a')] + [(f'c{p}_{k}', 'a') for k in range(CFG_PER_PAIR)])
                for k in range(CFG_PER_PAIR):
                    bus(f'rc_{p}_{k}', 'rom_ce', 1, [(sq, f'ce{k}'), (f'c{p}_{k}', 'ce')])
                    bus(f'rq_{p}_{k}', 'rom_q', 48, [(f'c{p}_{k}', 'rd'), (sq, f'q{k}')])
                bus(f'es_{p}', 'stat', STB, [(e, 'st'), (t_, f'e{j}')])
                bus(f'ss_{p}', 'stat', STB, [(sq, 'st'), (t_, f'c{j}')])
                if kind == 'NV':
                    bus(f'nv_{p}', 'nv', NV_BITS, [(e, 'nv'), (f'v{p}', 'nv')])
                    bus(f'nvr_{p}', 'nvr', NVR, [(f'v{p}', 'nvr'), (e, 'nvr')])
            if s in nvslots:
                p = nvslots[s]
                col_ck.append((f'v{p}', 'ck'))
                col_rs.append((f'v{p}', 'rs'))
                bus(f'es_v{p}', 'stat', STB, [(f'v{p}', 'st'), (t_, 'e0')])
            if s == last and (s + 1) in nvslots:          # NV extension in the (station-less) top slot
                p = nvslots[s + 1]
                col_ck.append((f'v{p}', 'ck'))
                col_rs.append((f'v{p}', 'rs'))
                bus(f'es_v{p}', 'stat', STB, [(f'v{p}', 'st'), (t_, 'e1')])
            # x lanes of this slot: station s drives slot s's S-face pins; q x1 (N face) from station s+1's qt
            nxt = f't{r}_{s + 1}' if s < last else None
            qs = [(f'e{p}', 'x1') for p, kind, ln in es if kind == 'q']
            if qs and q_x1_south():
                xb_eps, qs = xb_eps + qs, []
            if nxt is not None:
                B.append((f'xa_{r}_{s + 1}', 'x_lane', X0B, [(t_, 'xa'), (nxt, 'xai')] + xa_eps))
                B.append((f'xb_{r}_{s + 1}', 'x_lane', X1B, [(t_, 'xb'), (nxt, 'xbi')] + xb_eps))
                B.append((f'cc_{r}_{s + 1}', 'x_ctl', CCB, [(t_, 'cc'), (nxt, 'cci')] + cc_eps))
                if qs:
                    bus(f'qt_{r}_{s}', 'x_lane', X1B, [(nxt, 'qt')] + qs)
            else:
                B.append((f'xa_{r}_{s + 1}', 'x_lane', X0B, [(t_, 'xa')] + xa_eps))
                B.append((f'xb_{r}_{s + 1}', 'x_lane', X1B, [(t_, 'xb')] + xb_eps + qs))
                B.append((f'cc_{r}_{s + 1}', 'x_ctl', CCB, [(t_, 'cc')] + cc_eps))
            # status chain down the column: station s -> station s-1 -> ... -> column FIFO
            bus(f'so_{r}_{s}', 'stat', STB, [(t_, 'so'), ((f't{r}_{s - 1}', 'si') if s else (cf, 'st'))])
        # return tree
        nodes, root = f['tree']
        elist = [p for p, *_ in elems]
        ids = {n[0]: j for j, n in enumerate(nodes)}
        rank = _inorder_rank(nodes, root)
        by_rank = sorted(nodes, key=lambda n_: rank[n_[0]])
        for nid, a, b in nodes:
            nn = f'n{r}_{ids[nid]}'
            col_ck.append((nn, 'clk'))
            col_rs.append((nn, 'rst_n'))
            for side, c in (('a', a), ('b', b)):
                if c.startswith('N'):
                    bus(f'rt_{r}_{ids[nid]}{side}', 'ret_tree', NODEB, [(f'n{r}_{ids[c]}', 'o'), (nn, side)])
                else:
                    li = int(c[1:])
                    bus(f'rt_{r}_{ids[nid]}{side}', 'ret_leaf', LEAF, [(f'e{elist[li // 2]}', f'r{li % 2}'), (nn, side)])
        for k_ in range(len(by_rank) - 1, 0, -1):
            bus(f'nf_{r}_{k_}', 'stat', 1, [(f'n{r}_{ids[by_rank[k_][0]]}', 'fo'), (f'n{r}_{ids[by_rank[k_ - 1][0]]}', 'fi')])
        bus(f'nf_{r}_0', 'stat', 1, [(f'n{r}_{ids[by_rank[0][0]]}', 'fo'), (f't{r}_0', 'nf')])
        # root -> column FIFO through register stages in the strip sub-column
        rootn = by[f'n{r}_{ids[root]}'] if f'n{r}_{ids[root]}' in by else next(i_ for i_ in m['insts'] if i_.name == f'n{r}_{ids[root]}')
        cfi = next(i_ for i_ in m['insts'] if i_.name == cf)
        sx = f['x'] + 2 * LANE_W + NS_W + 4.32
        ytop = rootn.y + rootn.h
        ybot = cfi.y + cfi.h
        prev, k_ = (f'n{r}_{ids[root]}', 'o'), 0
        d = ytop - ybot + abs(sx - (rootn.x + rootn.w / 2))
        nst = max(0, math.ceil(d / (FWD_REACH - 40.0)) - 1)
        for i_ in range(nst):
            yy = dn(ytop - (i_ + 1) * (ytop - ybot) / (nst + 1) - RSTG_WH[1] / 2, GY)
            it = P.add(Inst(f'rg{r}_{i_}', 'dsfd_rstg', sx, yy, RSTG_WH[0] - SHAVE, RSTG_WH[1] - SHAVE, kind='rstg',
                            region=f'frame_{r}'))
            col_ck.append((it.name, 'ck'))
            col_rs.append((it.name, 'rs'))
            bus(f'rr_{r}_{i_}', 'col_ret', NODEB, [prev, (it.name, 'i')])
            prev = (it.name, 'o')
        bus(f'rr_{r}_{nst}', 'col_ret', NODEB, [prev, (cf, 'ri')])
        f['ret_stages'] = nst
        bus(f'ck_col_{r}', 'col_clock', 1, col_ck)
        bus(f'rs_col_{r}', 'col_reset', 1, col_rs)
    if REV == 'r9':
        _bank_nets(m)
        _col_relays(m, P)
    by = {it.name: it for it in m['insts']}
    # ---------------- hub glue blocks next to the slabs
    vm, ga, coll = hub['vm'], hub['gather'], hub['collective']
    x_sp, x_fe, x_vch = g['x_sp'], g['x_fe'], m['x_vch']

    def hub_block(name, master, kind, w, h, face_x, y_c, side, allowed):
        """end/start block beside a slab face: side 'W' = in the S14 W channel, 'E' = in the VCH"""
        xx = face_x - w - 4.32 if side == 'W' else face_x + 4.32
        if name.startswith('hr_') and side == 'E':
            xx = face_x + 0.55 * VCH8           # E-half return ends mid-VCH: keep the VCH west lanes free (r8 GRT)
        if name.startswith('hr_') and side == 'W':
            xx = face_x - 0.55 * SPF - w
        pl = P.near(xx + w / 2, y_c, w, h, allowed, horiz=False, span=1600.0, rows=6)
        assert pl, name
        it = P.add(Inst(name, master, pl[0], pl[1], w, h, 'MY' if side == 'W' else 'R0', kind=kind, region='hub'))
        return it
    m['glue'] = {}          # master -> spec (for the RTL / LEF generators)
    G = m['glue']

    def end_spec(kind, lanes, fmt):
        """kind m2l (meso, lane -> local stream), r2l (ratio CDC, lane -> serial), l2r (serial -> lane)"""
        sig = '_'.join(f'{w}x{n}' for w, n in _rle(lanes))
        name = f'dsfd_{kind}_{fmt}_{sig}'
        G[name] = dict(kind=kind, lanes=list(lanes), fmt=fmt)
        pins_in = sum(w + 2 + 1 for w in lanes) if kind != 'l2r' else lanes[0] + 1
        pins_out = sum(w + 1 for w in lanes) + 2 if kind != 'l2r' else lanes[0] + 2 + 1
        bits = sum(lanes)
        ins = [b for w in lanes for b in (1, w + 2)] if kind != 'l2r' else [lanes[0] + 1]
        outs = [sum(w + 1 for w in lanes) + 2] if kind != 'l2r' else [1, lanes[0] + 2, 3]
        face = face_need(ins + outs + [1, 1, 1, 1])
        h = up(max(face, 30.24), GY)
        w = up(max(30.24, bits * 3.0 / h, face), GX)
        return name, w - SHAVE, h - SHAVE
    # x root: VM -> two serial->stream CDC start blocks (W channel / VCH)
    vmc = vm.y + vm.h / 2
    starts = {}
    for side in 'WE':
        nm, w, h = end_spec('l2r', [LSW], 'vr')
        it = hub_block(f'hx_{side}', nm, 'hend', w, h, x_sp if side == 'W' else x_vch + 0.0, vmc,
                       side, [cor['s14W'] if side == 'W' else cor['vch']])
        starts[side] = it
        bus(f'xr_{side}', 'local', LSW + 1, [(vm.name, f'x{side.lower()}'), (it.name, 'i')])
        bus(f'xrs_{side}', 'local', 3, [(it.name, 'st'), (vm.name, f'x{side.lower()}s')])
    # ---------------- x trunks: per half, a vertical spine (up / down) with a branch per tier channel
    rowx = 64.8          # x-trunk station row (offset in the channel)
    rowr = 8.64          # return-trunk row
    rowl = 118.8         # link row
    s14x = {'W': x_sp - SPF / 2, 'E': x_fe + SPF / 2}
    m['chain_paths'] = []

    def tap_x(half, c, off):
        return g['col_x'](half, c) + off

    for half in 'WE':
        st = starts[half]
        src_xy = (st.x + st.w / 2, st.y + st.h / 2)
        # path from the start block to the half's S14 channel at the VM's y
        for dirn, tiers in (('dn', [2, 1, 0]), ('up', [3, 4, 5])):
            sx_ = s14_x(m, half, f'x{dirn}')
            if half == 'W':
                p0 = [src_xy, (sx_, src_xy[1])]
            else:
                cy_ = corr_y(m, f'x{dirn}')
                p0 = [src_xy, (src_xy[0], cy_), (sx_, cy_)]
            ys = [g['ch_y'][t] + rowx + 15.0 for t in tiers]
            path = _dedup(p0 + [(sx_, y_) for y_ in ys])
            forced = [_poly_len(path[:path.index((sx_, y_)) + 1]) for y_ in ys]
            allowed = [cor['s14W'] if half == 'W' else cor['s14E'], cor['vch'], cor['hcc']] + \
                      [cor[f'ch{t}'] for t in tiers]
            sts = CH8.run(f'x{half}{dirn}', [LSW + 2], path, allowed, src_xy, forced=forced)
            br = {}
            chain_nets(CH8, f'x{half}{dirn}', (st.name, 'fo', 'od'), [it for it, _, _ in sts], [LSW + 2])
            for t, s_f in zip(tiers, forced):
                junc = min(sts, key=lambda q: abs(q[1] - s_f))[0]
                br[t] = junc
            # horizontal branch per tier
            for t in tiers:
                ncol = TIER_COLS8[t]
                y_ = g['ch_y'][t] + rowx + 15.0
                xs_ = [tap_x(half, c, SSTN_X + SSTN_WH[0] / 2) for c in range(ncol)]
                far = xs_[-1]
                hp = [(br[t].x + br[t].w / 2, br[t].y + br[t].h / 2), (sx_, y_), (far, y_)]
                hp = _dedup(hp)
                forced_h = [abs(x_ - sx_) + _mh(hp[0], hp[1]) for x_ in xs_]
                sts_h = CH8.run(f'x{half}{t}', [LSW + 2], hp, [cor[f'ch{t}'], cor['s14W'] if half == 'W' else cor['s14E']],
                                hp[0], forced=forced_h)
                chain_nets(CH8, f'x{half}{t}', (br[t].name, 'fo0', 'do0'), [it for it, _, _ in sts_h], [LSW + 2])
                kv = 1 + next(i_ for i_, q in enumerate(sts) if q[0] is br[t])
                for c in range(ncol):
                    r = _frame_of(m, half, t, c)
                    ih = min(range(len(sts_h)), key=lambda i_: abs((sts_h[i_][0].x + sts_h[i_][0].w / 2) - xs_[c]))
                    _add_tap(m, sts_h[ih][0], 0, (f'cf{r}', 'xf', 'xd'))
                    m.setdefault('x_stages', {})[r] = kv + ih + 1
    # ---------------- return trunks: per tier-half one multi-lane chain (one lane per column) -> gather end block
    for half in 'WE':
        for t in range(TIERS):
            ncol = TIER_COLS8[t]
            y_ = g['ch_y'][t] + rowr + 20.0
            xs_ = [tap_x(half, c, CF_X + CF_WH[0] - 30.0) for c in range(ncol)]
            sx_ = s14_x(m, half, f'r{t}')
            path = [(xs_[-1], y_), (sx_, y_)]
            gy = ga.y + ga.h * (0.15 + 0.7 * t / (TIERS - 1))
            if half == 'W':
                path += [(sx_, gy)]
            else:
                cy_, vx_ = corr_y(m, f'r{t}'), vch_x(m, f'r{t}')
                path += [(sx_, cy_), (vx_, cy_), (vx_, gy)]
            path = _dedup(path)
            forced = [abs(xs_[-1] - x_) for x_ in xs_[::-1]]
            lanes_at = []
            allowed = [cor[f'ch{t}'], cor['s14W'] if half == 'W' else cor['s14E'], cor['vch'], cor['hcc']]
            # lanes: column c joins at its tap; a station carries every lane that has joined so far
            sts = _run_multi(CH8, f'r{half}{t}', path, allowed, forced, ncol)
            nm, w, h = end_spec('m2l', [CRET] * ncol, 'vr')
            endb = hub_block(f'hr_{half}{t}', nm, 'hend', w, h, ga.x if half == 'W' else ga.x + ga.w, gy, half,
                             [cor['s14W'] if half == 'W' else cor['vch']])
            _multi_nets(m, CH8, f'r{half}{t}', sts, ncol, [_frame_of(m, half, t, c) for c in range(ncol)], endb)
            if REV == 'r9':
                _local_chain(m, CH8, [cor['s14W'] if half == 'W' else cor['vch']], endb, 'o', ga, f'r{half}{t}',
                             ncol * (CRET + 1) + 2, f'hr_{half}{t}_o', 'stream_1p2')
            else:
                bus(f'hr_{half}{t}_o', 'local', ncol * (CRET + 1) + 2, [(endb.name, 'o'), (ga.name, f'r{half}{t}')])
    # ---------------- scan services <-> VM, band links, selector / collector -> VM
    _svc_chains(m, CH8, P, cor, end_spec, hub_block)
    # ---------------- links: collective <-> link macros
    _link_chains(m, CH8, P, cor, end_spec, hub_block, rowl)
    # ---------------- hub-internal buses (adjacent slabs, direct)
    hb = hub
    for a_, b_, bits, pa, pb in (('vm', 'su_s', 1024, 't_su_s', 'f_vm'), ('vm', 'su_n', 1024, 't_su_n', 'f_vm'),
                                 ('vm', 'hc_s', 1024, 't_hc', 'f_vm'), ('hc_n', 'vm', 1024, 't_vm', 'f_hc'),
                                 ('vm', 'gather', 512, 't_gather', 'f_vm'), ('gather', 'capture', 576, 't_capture', 'f_gather'),
                                 ('capture', 'vm', 512, 't_vm', 'f_capture'), ('collective', 'vm', 512, 't_vm', 'f_collective'),
                                 ('su_s', 'hc_s', 512, 't_hc', 'f_su_s'), ('su_n', 'hc_n', 512, 't_hc', 'f_su_n'),
                                 ('hc_s', 'hc_n', 1024, 't_n', 'f_s'), ('hc_n', 'hc_s', 1024, 't_s', 'f_n')):
        if REV == 'r9':
            _hub_bus_chain(m, CH8, cor, a_, b_, bits, pa, pb)
        else:
            bus(f'hb_{a_}_{b_}', 'hub', bits, [(hb[a_].name, pa), (hb[b_].name, pb)])
    # ---------------- PHY / controller / service
    npins = len(real_ports_r8()[real_lef(PHY_LEF)['name']]['dfi'])
    for st, ph in m['phys'].items():
        bus(f'dfi_{st}', 'phy_dfi', npins, [(m['ctrls'][st].name, 'phy'), (ph.name, 'dfi')])
        bus(f'rd_{st}', 'hbm_read', HBM_RD_BITS, [(m['ctrls'][st].name, 'rd'), (m['svcs'][st].name, 'rd')])
    if HOP_FIX and HOP_PLAN:
        _hop_fix(m, P)
    # ---------------- clocks, resets, top ports
    col = coll.name
    bus('refclk', 'top_in', 1, [('TOP', 'refclk'), (col, 'refclk')])
    bus('por_n', 'top_in', 1, [('TOP', 'por_n'), (col, 'por')])
    by = {it.name: it for it in m['insts']}
    dom = defaultdict(list)
    rst = defaultdict(list)
    for it in m['insts']:
        if it.kind == 'cfifo':
            dom['stream'].append((it.name, 'ck'))
            rst['stream'].append((it.name, 'rst'))
        elif it.kind in ('hub', 'band_blk') and it.name != col:
            d_ = 'serial' if it.domain == 'serial_0p9' else 'stream'
            dom[d_].append((it.name, 'ck'))
            rst[d_].append((it.name, 'rst'))
        elif it.kind == 'hstn':
            dom[HSTN_DOM[it.domain]].append((it.name, 'ck'))
        elif it.kind == 'svc':
            dom['stream'].append((it.name, 'ck'))
            rst['stream'].append((it.name, 'rst'))
        elif it.kind == 'ctrl':
            dom['hbm'].append((it.name, 'ckh'))
            dom['stream'].append((it.name, 'cks'))
            rst['hbm'].append((it.name, 'rst'))
        elif it.kind == 'xstg':           # cw: write side (the end block's region), ck: the band block's
            d_ = 'serial' if it.domain == 'serial_0p9' else 'stream'
            dom[d_] += [(it.name, 'cw'), (it.name, 'ck')]
        elif it.kind == 'hend':
            spec = G[it.master]
            if spec['kind'] == 'l2r':
                dom['serial'].append((it.name, 'ck'))
                rst['serial'].append((it.name, 'rs'))
                dom['stream'].append((it.name, 'cks'))
                rst['stream'].append((it.name, 'rss'))
            else:
                d_ = 'serial' if spec['kind'] == 'r2l' else 'stream'
                dom[d_].append((it.name, 'ck'))
                rst[d_].append((it.name, 'rs'))
    for d_ in ('stream', 'serial', 'hbm'):
        bus(f'clk_{d_}', 'clock', 1, [(col, f'pll_{d_}')] + dom[d_])
        bus(f'rst_{d_}', 'reset', 1, [(col, f'rst_{d_}')] + rst[d_])
    # one net per driver port: chains that branch (x spines -> tier branches, the start block -> both spines) declared
    # one net per branch; merge them into the driver's single multi-load net
    merged, at = [], {}
    for b in m['buses']:
        k_ = b[3][0] if b[3][0][0] != 'TOP' else (b[0],)
        if k_ in at:
            i_ = at[k_]
            o = merged[i_]
            assert o[1] == b[1] and o[2] == b[2], (o[:3], b[:3])
            merged[i_] = (o[0], o[1], o[2], o[3] + [e for e in b[3][1:] if e not in o[3]])
        else:
            at[k_] = len(merged)
            merged.append(b)
    m['buses'] = merged
    return m


LANES_VCH, LANES_CORR = 26, 16
VCH_INTERLEAVE = False          # --vch-interleave (S81-RERUN, default off): strided VCH lane order
CORR_INTERLEAVE = False         # --corr-interleave (S81-RERUN v5, default off): strided HC-corridor lane order
CORR_LANE_STRIDE = 5            # coprime with LANES_CORR (16)
HOP_FIX = False                 # --hop-fix (S81-RERUN v6, default off): stations on every die hop over its reach,
                                #   measured pin anchor to pin anchor on a first build (budget sheets 2026-10-06)
HOP_PLAN = None                 # {(drv inst, drv port, load inst, load port): (L um, (dx, dy), (lx, ly))}
PIN_RELAY = False               # --pin-relay (OWNER rule 1, 2026-10-07): a relay station abutting every hardened-block pin
PIN_SEG = 100.0                 #   on die interfaces (last segment <= 100 um)
GEOMETRY_FIX = False            # --geometry-fix: canonical station outlines and bounded bundled pin depth
HOP_R_CC = 410.0                # common-clock reach (budget sheet reach 411-491 um at 833.333 ps SS)
HOP_R_FWD = 430.56              # forwarded hop = the station pitch (routed stations: SS +78..+84 at the 440 um hop budget)
MESO_D8 = False                 # --meso-d8 (v6, default off): meso FIFOs DEPTH 8 / OFFSET 3 / guards 0,6 / CREDITS 16
                                #   (campaign d8 config): stream-trunk drift 386 ps > 300 ps; +1 cycle per crossing
HC_XFACE = False                # --hc-xface (S81-RERUN v7, default off): hc_s <-> hc_n exchange face to face across
                                #   the corridor inside the HC column (out of the VCH-edge lane)
SEL_XSTG = False                # --sel-xstg (S81-RERUN v8, default off): d8g1 meso crossing stage (1.5 T arcs + low guard)
                                #   on the 8 end block -> selector / collector buses; +6 cycles
LINK_SPLIT = False              # --link-split (S81-RERUN v8, default off; needs --link-fix): SerDes tx / rx through two
                                #   256-b half-span stations (port slices), last hop <= 281 um; +1 cycle each way
LINK_FIX = False                # --link-fix (S81-RERUN, default off): link ck relay on the ck face, final tx / rx
                                #   station at the centre of its pin span
VCH_LANE_STRIDE = 11            # coprime with LANES_VCH (26)
HUB_LANE_PITCH = 72.0           # r9 hub-bus lane spacing in the VCH (was 12 um: v2 GRT overflow in the VCH west strip)

# ---------------------------------------------------------------- r9: q-element boundary banks and column relays
# The q element (QELEM Z20c ETM, write_timing_model on the routed odb/spef) has a ~650 ps (SS) internal clock
# insertion: input hold +122..+291 ps and outputs valid up to 1,046 ps after its clk pin.  It meets only neighbours that
# share that insertion and sit next to its pins.  r9 puts a register bank against each pin face (inputs x0 / x1 / cfg /
# go into the element, outputs r0 / r1 / busy-fault out of it; CTS balances the banks with the element's
# max_clock_tree_path), so every other column path is glue to glue.  +1 cycle on the way in, +1 on the way out.
BANK_H = 6.48
BANK_RULE_UM = 430.0           # common-clock glue reach used for relays (the 430.56 um stage less pin spread)
# MARGIN-FIRST (owner rule 2026-10-06): a common-clock (one CTS tree) hop does not close at 440 um (meso_fifo verdict
# fwd_hop2_synchronous_counterfactual: SS -330 ps); --cc-reach-um caps every common-clock hop (hub-bus stations, end
# block -> slab stations, column relays) below the forwarded 430.56 um reach.  Default = the r9 value (unchanged).
CC_REACH = LINK_STAGE_UM


def out_rev():
    """record directory of the revision: r9, or r9m<reach> for a MARGIN-FIRST common-clock reach"""
    r = REV if CC_REACH >= LINK_STAGE_UM else f'{REV}m{int(round(CC_REACH))}'
    return (r + ('k' if LINK_FIX else '') + ('h' if HOP_FIX else '') + ('d' if MESO_D8 else '')
            + (f'p{int(round(FWD_REACH))}' if FWD_REACH < LINK_STAGE_UM else '') + ('c' if CFIFO_V2 else '') + ('x' if HC_XFACE else '') + ('s' if LINK_SPLIT else '') + ('g' if SEL_XSTG else '') + ('j' if GEOMETRY_FIX else '') + ('p' if PIN_RELAY else '') + ('w' if (CHS or VCH8 != 1209.6 or HC_CORR != 1209.6) else ''))


def set_cc_reach(um):
    global CC_REACH, BANK_RULE_UM
    if um:
        CC_REACH = float(um)
        BANK_RULE_UM = min(430.0, CC_REACH - 0.56)
QBANK_IN = ('x0', 'x1', 'cfg', 'go')
QBANK_OUT = ('r0', 'r1', 'st')
BANK_PORTS = {}
RLY_FACES = {}


def _q_port_face(rq, port):
    """'S' or 'N': face of a q element port group (from the LEF pin y)"""
    nm = real_ports_r8()[rq['name']][port][0]
    return 'S' if rq['pins'][nm][1][1] < rq['h'] / 2 else 'N'


def _q_port_xc(rq, port):
    nms = real_ports_r8()[rq['name']][port]
    xs = [(rq['pins'][n][1][0] + rq['pins'][n][1][2]) / 2 for n in nms if n in rq['pins']]
    return sum(xs) / len(xs)


def _q_banks(p, ex, ey, rq, region):
    out = []
    for face in 'SN':
        ports = [q_ for q_ in QBANK_IN + QBANK_OUT if _q_port_face(rq, q_) == face]
        if not ports:
            continue
        xc = sum(_q_port_xc(rq, q_) for q_ in ports) / len(ports)
        w = 60.48
        x = dn(ex + xc - w / 2, GX)
        y = dn(ey - BANK_H - 2.0, GY) if face == 'S' else up(ey + rq['h'] + 1.08, GY)
        out.append(Inst(f'b{face.lower()}{p}', f'dsfd_qbank_{face}', x, y, w - SHAVE, BANK_H - SHAVE, kind='qbank',
                        region=region, power_w=0.0))
        BANK_PORTS[out[-1].name] = (face, ports)
    return out


def _bank_nets(m):
    """route every banked q-element port through its bank: die side <-> bank (i_/d_ ports), bank <-> element (o_/e_)"""
    by = {it.name: it for it in m['insts']}
    bank = {}
    for it in m['insts']:
        if it.kind == 'qbank':
            p = it.name[2:]
            for q_ in BANK_PORTS[it.name][1]:
                bank[(f'e{p}', q_)] = it
    B = m['buses']
    new = []
    for i, (bid, cls, bits, eps) in enumerate(B):
        eps2 = list(eps)
        for j, (inst, port) in enumerate(eps):
            bk = bank.get((inst, port))
            if bk is None:
                continue
            if port in QBANK_OUT:
                assert j == 0, (bid, eps)
                eps2[0] = (bk.name, f'd_{port}')
                new.append((f'{bid}_eb', cls, bits, [(inst, port), (bk.name, f'e_{port}')]))
            else:
                eps2[j] = (bk.name, f'i_{port}')
                new.append((f'{bid}_{inst}_eb', cls, bits, [(bk.name, f'o_{port}'), (inst, port)]))
        B[i] = (bid, cls, bits, eps2)
    B.extend(new)
    # clocks / resets: banks on their column root (the element's clk / rst_n nets)
    for i, (bid, cls, bits, eps) in enumerate(B):
        if cls in ('col_clock', 'col_reset'):
            add = []
            for inst, port in eps:
                if inst.startswith('e') and inst in by and by[inst].kind == 'q':
                    for f_ in 'sn':
                        if f'b{f_}{inst[1:]}' in by:
                            add.append((f'b{f_}{inst[1:]}', 'ck' if cls == 'col_clock' else 'rs'))
            B[i] = (bid, cls, bits, eps + add)


def _hop_fix(m, P):
    """pass 2 of --hop-fix: on every planned hop, stations at equal spacing on the anchor-to-anchor L path.
    Field (column) common-clock buses: column relays (dsfd_rly, column clock / reset); hub common-clock buses: hub
    stations (dsfd_hstn, the driver's domain clock); forwarded lanes: forwarded stations on the lane AND its fclk."""
    by = {it.name: it for it in m['insts']}
    B = m['buses']
    plan = HOP_PLAN
    cor = _corridors(m)
    fclk_of = {}
    for i, (bid, cls, bits, eps) in enumerate(B):
        if cls == 'fclk':
            for e in eps[1:]:
                fclk_of[(eps[0][0], e[0], e[1])] = i
    col_ck = {b[0]: i for i, b in enumerate(B) if b[1] in ('col_clock', 'col_reset')}
    W, H = DIE
    rec = defaultdict(lambda: dict(hops=0, stations=0, max_um=0.0, max_added=0))
    added_frame = defaultdict(lambda: defaultdict(int))
    fwd_add = defaultdict(int)
    new = []
    for i in range(len(B)):
        bid, cls, bits, eps = B[i]
        if cls in HOP_SKIP or len(eps) < 2:
            continue
        keep = [eps[0]]
        for e in eps[1:]:
            key = (eps[0][0], eps[0][1], e[0], e[1])
            if key not in plan:
                keep.append(e)
                continue
            L, a, b, _ = plan[key]
            fwd = cls in HOP_FWD_CLS
            R = HOP_R_FWD if fwd else HOP_R_CC
            n = math.ceil(L / (R - 20.0) - 1e-9) - 1
            d0, l0 = by[eps[0][0]], by[e[0]]
            reg = next((x.region for x in (d0, l0) if x.region and x.region.startswith('frame_')), None)
            if fwd:
                fport = 'fi' + e[1][2:] if e[1].startswith('di') else None
                fi_ = fclk_of.get((eps[0][0], e[0], fport)) if fport else None
                if fi_ is None:
                    keep.append(e)
                    rec[cls + ':no_fclk']['hops'] += 1
                    continue
                fdrv = B[fi_][3][0]
            path = [a, (b[0], a[1]), b]
            Lp = _poly_len(path)
            # OWNER rule 1 (2026-10-07, --pin-relay): a relay abutting every hardened-block pin (<= PIN_SEG um last
            # segment) at each non-glue end, the span between them at the reach as before
            pos = [Lp * (k + 1) / (n + 1) for k in range(n)]
            if PIN_RELAY:
                h0, h1 = not is_glue(d0.master), not is_glue(l0.master)
                if (h0 or h1) and Lp > PIN_SEG:
                    s0 = min(PIN_SEG - 10.0, Lp / 2) if h0 else 0.0
                    s1 = Lp - min(PIN_SEG - 10.0, Lp / 2) if h1 else Lp
                    mid = max(0, math.ceil((s1 - s0) / (R - 20.0) - 1e-9) - 1)
                    pos = ([s0] if h0 else []) + [s0 + (s1 - s0) * (k + 1) / (mid + 1) for k in range(mid)] \
                        + ([s1] if h1 and s1 > s0 + 1.0 else [])
                    n = len(pos)
            prev, cur = eps[0], a
            fprev = fdrv if fwd else None
            for k in range(n):
                (cx, cy), dch = _poly_at(path, pos[k])
                horiz = dch in 'EW'
                w_, h_ = stn_dims([bits], horiz)
                if not fwd and (reg is not None or not GEOMETRY_FIX):  # frame relay faces chosen later -> square
                    w_ = h_ = max(w_, h_)
                pl = None
                # v6b: stations only in the die's channels (v6 placed them anywhere on the die: 41-54 PA overlaps,
                # and the corridor / VCH crossing got denser); frame relays inside their frame
                if reg is not None and not fwd:
                    f_ = m['frames'][int(reg.split('_')[1])]
                    allowed = [(f_['x'], f_['y'] - 60.0, f_['x'] + COL_W8, f_['y'] + SLOTS8 * SLOT_H8)]
                else:
                    allowed = list(cor.values())
                # v6c: searched with a 2.16 um keep-out each side (the PA track snap moved v6b's tightly packed
                # stations into each other: 41 / 49 / 49 overlaps, all hop-fix stations)
                # v7: a station with no padded spot inside its frame (v6c: rt_63_26b in frame 63) falls back to a
                # 1.08 um, then no keep-out (counted in rec['pad_fallback'])
                for PAD in (2.16, 1.08, 0.0):
                    for span, rows in ((120.0, 12), (300.0, 30), (600.0, 60), (1200.0, 120)):
                        pl = P.near(cx, cy, w_ + 2 * PAD, h_ + 2 * PAD, allowed, prev=cur, horiz=horiz,
                                    reach=R - 10.0, span=span, rows=rows)
                        if pl:
                            pl = (up(pl[0] + PAD, GX), up(pl[1] + PAD, GY))
                            break
                    if pl:
                        if PAD < 2.16:
                            rec['pad_fallback'][f'{PAD:g}'] = rec['pad_fallback'].get(f'{PAD:g}', 0) + 1
                        break
                assert pl, (bid, e, k)
                nm = f'g_{bid}_{e[0]}_{k}'
                if fwd:
                    it = P.add(Inst(nm, stn_master([bits], horiz), pl[0], pl[1], w_, h_,
                                    {'E': 'R0', 'W': 'MY', 'N': 'R0', 'S': 'MX'}[dch], kind='stn', region='link',
                                    domain='fwd', power_w=bits * FLOP_CLK_W * 1.5))
                    new.append((f'{bid}_g{k}_{e[0]}', cls, bits, [prev, (it.name, 'di0')]))
                    new.append((f'{B[fi_][0]}_g{k}_{e[0]}', 'fclk', 1, [fprev, (it.name, 'fi0')]))
                    prev, fprev = (it.name, 'do0'), (it.name, 'fo0')
                elif reg is not None:
                    it = P.add(Inst(nm, f'dsfd_rly_{bits}', pl[0], pl[1], w_, h_, kind='rly', region=reg,
                                    power_w=bits * FLOP_CLK_W * 1.5))
                    r_ = reg.split('_')[1]
                    for cb, pn in ((f'ck_col_{r_}', 'ck'), (f'rs_col_{r_}', 'rs')):
                        j = col_ck[cb]
                        B[j] = (B[j][0], B[j][1], B[j][2], B[j][3] + [(it.name, pn)])
                    new.append((f'{bid}_g{k}_{e[0]}', cls, bits, [prev, (it.name, 'i')]))
                    prev = (it.name, 'o')
                else:
                    dom_ = d0.domain if d0.domain in HSTN_DOM else (l0.domain if l0.domain in HSTN_DOM else 'stream_1p2')
                    it = P.add(Inst(nm, 'dsfd_hstn%s_%d' % ('h' if horiz else 'v', bits), pl[0], pl[1], w_, h_,
                                    kind='hstn', region='hub', domain=dom_, power_w=bits * FLOP_CLK_W * 1.5))
                    new.append((f'{bid}_g{k}_{e[0]}', cls, bits, [prev, (it.name, 'di')]))
                    prev = (it.name, 'dq')
                cur = (it.x + it.w / 2, it.y + it.h / 2)
                by[it.name] = it
            new.append((f'{bid}_g{n}_{e[0]}', cls, bits, [prev, e]))
            if fwd:
                fl = [x for x in B[fi_][3][1:] if x != (e[0], fport)]
                B[fi_] = (B[fi_][0], 'fclk', 1, [B[fi_][3][0]] + fl)
                new.append((f'{B[fi_][0]}_g{n}_{e[0]}', 'fclk', 1, [fprev, (e[0], fport)]))
                fwd_add[bid[:1]] = max(fwd_add[bid[:1]], n)
            elif reg is not None:
                fr_ = int(reg.split('_')[1])
                xk = 'x' if cls in ('x_lane', 'x_ctl', 'go', 'cfg', 'hb_x', 'hb_ctl') else 'r'
                added_frame[fr_][(xk, cls)] = max(added_frame[fr_][(xk, cls)], n)
            q = rec[cls]
            q['hops'] += 1
            q['stations'] += n
            q['max_um'] = max(q['max_um'], L)
            q['max_added'] = max(q['max_added'], n)
        B[i] = (bid, cls, bits, keep)
    B[:] = [b for b in B if len(b[3]) > 1 or b[1] in ('col_clock', 'col_reset')] + new
    # inserted relays: faces toward their driver and load
    by = {it.name: it for it in m['insts']}
    nets_in, nets_out = {}, {}
    for bid, cls, bits, eps in B:
        for e in eps[1:]:
            nets_in[e] = eps[0]
        nets_out[eps[0]] = eps[1:]
    cen = lambda it: (it.x + it.w / 2, it.y + it.h / 2)
    for it in m['insts']:
        if it.kind != 'rly' or not it.name.startswith('g_'):
            continue
        a = by[nets_in[(it.name, 'i')][0]]
        b = by[nets_out[(it.name, 'o')][0][0]]

        def fc(q):
            dx, dy = q[0] - (it.x + it.w / 2), q[1] - (it.y + it.h / 2)
            return ('E' if dx > 0 else 'W') if abs(dx) * it.h > abs(dy) * it.w else ('N' if dy > 0 else 'S')
        fi, fo = fc(cen(a)), fc(cen(b))
        if fo == fi:
            fo = dict(N='S', S='N', E='W', W='E')[fi]
        bits = int(it.master.split('_')[2])
        it.master = f'dsfd_rly_{bits}_{fi}{fo}'
        RLY_FACES[it.master] = (fi, fo)
    for r, d in added_frame.items():
        f = m['frames'][r]
        f['relay_x'] = f.get('relay_x', 0) + max([v for (k, _), v in d.items() if k == 'x'] or [0])
        f['relay_ret'] = f.get('relay_ret', 0) + sum(v for (k, _), v in d.items() if k == 'r')
    m['hop_fix'] = dict(classes={k: dict(v, max_um=round(v['max_um'], 1)) for k, v in rec.items()},
                        planned_hops=len(plan), fwd_rt_add=fwd_add.get('r', 0) + fwd_add.get('x', 0),
                        reach_um=dict(common_clock=HOP_R_CC, forwarded=HOP_R_FWD))


def _col_relays(m, P):
    """common-clock column nets whose driver -> load centre distance exceeds BANK_RULE_UM get relay registers
    (one cycle each) at equal spacing on an L path, inside the frame.  Records per frame the relays on the worst x
    path and on the worst leaf -> root path."""
    by = {it.name: it for it in m['insts']}
    cen = lambda it: (it.x + it.w / 2, it.y + it.h / 2)
    RCLS = ('ret_leaf', 'ret_tree', 'x_lane', 'x_ctl', 'stat', 'cfg', 'go', 'col_ret')
    B = m['buses']
    out, added = [], defaultdict(int)       # (bus id) -> relays
    ck_add = defaultdict(list)
    for bid, cls, bits, eps in list(B):
        if cls not in RCLS or bid.endswith('_eb'):
            out.append((bid, cls, bits, eps))
            continue
        d0 = by.get(eps[0][0])
        if d0 is None or d0.region is None or not d0.region.startswith('frame_'):
            out.append((bid, cls, bits, eps))
            continue
        r = int(d0.region.split('_')[1])
        f = m['frames'][r]
        fr = (f['x'], f['y'] - 60.0, f['x'] + COL_W8, f['y'] + SLOTS8 * SLOT_H8)
        far = max((by[e[0]] for e in eps[1:] if e[0] in by), key=lambda it: _mh(cen(d0), cen(it)), default=None)
        if far is None:
            out.append((bid, cls, bits, eps))
            continue
        L = _mh(cen(d0), cen(far))
        n = math.ceil(L / BANK_RULE_UM - 1e-9) - 1
        if n <= 0:
            out.append((bid, cls, bits, eps))
            continue
        a, b = cen(d0), cen(far)
        path = [a, (b[0], a[1]), b] if cls != 'ret_tree' else [a, (a[0], b[1]), b]
        prev, cur = eps[0], a
        chain = [a]
        Lp = _poly_len(path)
        w_, h_ = stn_dims([bits], True)
        for k in range(n):
            (cx, cy), _ = _poly_at(path, Lp * (k + 1) / (n + 1))
            pl = P.near(cx, cy, w_, h_, [fr], prev=cur, horiz=True, reach=BANK_RULE_UM + 40.0, span=200.0, rows=20)
            if pl is None:
                pl = P.near(cx, cy, w_, h_, [fr], prev=None, horiz=True, span=400.0, rows=40)
            assert pl, (bid, k)
            it = P.add(Inst(f'y_{bid}_{k}', f'dsfd_rly_{bits}', pl[0], pl[1], w_, h_, kind='rly',
                            region=d0.region, power_w=bits * FLOP_CLK_W * 1.5))
            out.append((f'{bid}_y{k}', cls, bits, [prev, (it.name, 'i')]))
            prev, cur = (it.name, 'o'), cen(it)
            ck_add[r].append(it.name)
            chain.append(it)
        chain.append(b)
        for k in range(1, len(chain) - 1):
            it = chain[k]
            pa = chain[k - 1] if isinstance(chain[k - 1], tuple) else cen(chain[k - 1])
            pb = chain[k + 1] if isinstance(chain[k + 1], tuple) else cen(chain[k + 1])
            def fc(q):
                dx, dy = q[0] - (it.x + it.w / 2), q[1] - (it.y + it.h / 2)
                return ('E' if dx > 0 else 'W') if abs(dx) * it.h > abs(dy) * it.w else ('N' if dy > 0 else 'S')
            fi, fo = fc(pa), fc(pb)
            if fo == fi:
                fo = dict(N='S', S='N', E='W', W='E')[fi]
            it.master = f'dsfd_rly_{bits}_{fi}{fo}'
            RLY_FACES[it.master] = (fi, fo)
        out.append((bid, cls, bits, [prev] + list(eps[1:])))
        added[bid] = n
    B[:] = out
    for i, (bid, cls, bits, eps) in enumerate(B):
        if cls in ('col_clock', 'col_reset') and bid.rsplit('_', 1)[-1].isdigit():
            r = int(bid.rsplit('_', 1)[-1])
            if r in ck_add:
                B[i] = (bid, cls, bits, eps + [(nm, 'ck' if cls == 'col_clock' else 'rs') for nm in ck_add[r]])
    # per frame: bank stages (2 if any q element) + the worst relay count on an x path and on a leaf -> root path
    for r, f in m['frames'].items():
        if f.get('bundles'):
            continue
        nodes, root = f['tree']
        ids = {n_[0]: j for j, n_ in enumerate(nodes)}
        parent = {}
        for nid, a_, b_ in nodes:
            for side, c in (('a', a_), ('b', b_)):
                parent[c] = (nid, side)
        def up_relays(c):
            t_ = 0
            while c in parent:
                nid, side = parent[c]
                t_ += added.get(f'rt_{r}_{ids[nid]}{side}', 0)
                c = nid
            return t_
        leaves = [c for c in parent if not c.startswith('N')]
        f['relay_ret'] = max((up_relays(c) for c in leaves), default=0) + \
            sum(v for k_, v in added.items() if k_.startswith(f'rr_{r}_'))
        f['relay_x'] = max((v for k_, v in added.items() if k_.startswith((f'xa_{r}_', f'xb_{r}_', f'qt_{r}_', f'cc_{r}_'))),
                           default=0)
        f['bank_stages'] = 2 if any(k == 'q' for _, k, _, _ in f['elems']) else 0
    m['col_relays'] = dict(nets=len(added), relays=sum(added.values()),
                           by_class={c: sum(v for k_, v in added.items() if k_.startswith(c)) for c in
                                     ('rt_', 'xa_', 'xb_', 'cc_', 'qt_', 'es_', 'ss_', 'so_', 'nf_', 'cfg_', 'go_', 'rr_')})


def _local_chain(m, CH8, allowed, A, pa, Bk, pb, bits, name, dom):
    """r9: a local block-to-block bus (end block -> slab) staged by common-clock stations when it exceeds one hop"""
    a = (A.x + A.w / 2, A.y + A.h / 2)
    fx = Bk.x + Bk.w if a[0] > Bk.x + Bk.w else (Bk.x if a[0] < Bk.x else a[0])
    b = (fx, min(max(a[1], Bk.y + 6.0), Bk.y + Bk.h - 6.0))
    path = _dedup([a, (b[0], a[1]), b])
    L = _poly_len(path)
    if L <= CC_REACH - 60.0:
        CH8.bus(name, 'local', bits, [(A.name, pa), (Bk.name, pb)])
        m.setdefault('hub_stations', {})[name] = dict(path_um=round(L, 1), stations=0, floor_added=0)
        return
    sts = CH8.run(name, [bits], path, allowed, a, reach=CC_REACH if CC_REACH < LINK_STAGE_UM else None)
    prev = (A.name, pa)
    for k, (it, s_, hop) in enumerate(sts):
        it.kind, it.domain = 'hstn', dom
        it.master = 'dsfd_hstn%s_%d' % ('h' if it.master.startswith('dsfd_stnh') else 'v', bits)
        CH8.bus(f'{name}_d{k}', 'local', bits, [prev, (it.name, 'di')])
        prev = (it.name, 'dq')
    CH8.bus(f'{name}_d{len(sts)}', 'local', bits, [prev, (Bk.name, pb)])
    m.setdefault('hub_stations', {})[name] = dict(path_um=round(L, 1), stations=len(sts),
                                                  floor_added=max(0, math.ceil(L / LINK_STAGE_UM - 1e-9) - 1))


def _hub_bus_chain(m, CH8, cor, a_, b_, bits, pa, pb):
    """r9 (S81-RERUN): a hub slab-to-slab bus staged by common-clock stations (ot_fwd_link_stage clocked by the
    driver slab's domain clock, so no crossing and one cycle per station) every <= 430.56 um.  Spine-column slabs
    (VM, SU, gather, capture, collective) leave from their E face and HC slabs from their W face; the bus runs in its
    own VCH lane between them.  A bus whose path fits one hop stays a direct register-to-register wire."""
    hb = m['hub']
    A, Bk = hb[a_], hb[b_]
    hcA, hcB = A.name.startswith('sp_hc_'), Bk.name.startswith('sp_hc_')
    fx = lambda it: it.x if it.name.startswith('sp_hc_') else it.x + it.w
    lo, hi = max(A.y, Bk.y) + 20.0, min(A.y + A.h, Bk.y + Bk.h) - 20.0
    if hcA != hcB and hi - lo > 100.0:
        # across the VCH where the two slabs overlap in y: a straight horizontal bus
        lane = m.setdefault('_hb_lane', {}).setdefault('x', [0])
        y_ = lo + (hi - lo) * (0.25 + 0.5 * ((lane[0] * 0.37) % 1.0))
        lane[0] += 1
        path = [(fx(A), y_), (fx(Bk), y_)]
    elif hcA == hcB and max(A.y, Bk.y) - min(A.y + A.h, Bk.y + Bk.h) <= CC_REACH - 60.0:
        # stacked neighbours in one column: face to face across the gap, one hop
        g_ = max(A.y, Bk.y) - min(A.y + A.h, Bk.y + Bk.h)
        CH8.bus(f'hb_{a_}_{b_}', 'hub', bits, [(A.name, pa), (Bk.name, pb)])
        m.setdefault('hub_stations', {})[f'hb_{a_}_{b_}'] = dict(path_um=round(g_, 1), stations=0, floor_added=0)
        return
    else:
        cl = lambda v, it: min(max(v, it.y + 6.0), it.y + it.h - 6.0)
        ya = cl(Bk.y + Bk.h / 2, A)
        yb = cl(ya, Bk)
        ya = cl(yb, A)
        side = 'hc' if hcA and hcB else ('sp' if not (hcA or hcB) else 'mid')
        k_ = m.setdefault('_hb_lane', {}).setdefault(side, [0])
        # v2 GRT i50 (r9, 2fcb276fc): overflow 312 / 308 / 768 in the VCH west strip (x_vch + 0..410 um, M7 / M9 up
        # to 1.19) where the wide hub-bus lanes ran 12 um apart: lanes now HUB_LANE_PITCH apart
        if side == 'hc' and HC_XFACE:
            # S81-RERUN v7 (v6b GRT hotspot x 16.5-17.5 / y 10.5-12.0 mm): the hc_s <-> hc_n exchange crossed the
            # corridor in a VCH-edge lane, on top of the corridor chains' turns.  It now runs face to face, straight
            # across the corridor inside the HC column (hc_s N face -> hc_n S face), one x per direction, spread
            # over the column width; its common-clock stations stand in the corridor.
            xx = A.x + A.w * (0.3 if a_ == 'hc_s' else 0.7)
            path = [(xx, A.y + A.h), (xx, Bk.y)] if A.y < Bk.y else [(xx, A.y), (xx, Bk.y + Bk.h)]
            L = _poly_len(path)
            name = f'hb_{a_}_{b_}'
            sts = CH8.run(name, [bits], path, [cor['hcc']], path[0], reach=CC_REACH if CC_REACH < LINK_STAGE_UM else None)
            prev = (A.name, pa)
            for k, (it, s_, hop) in enumerate(sts):
                it.kind, it.domain = 'hstn', A.domain
                it.master = 'dsfd_hstn%s_%d' % ('h' if it.master.startswith('dsfd_stnh') else 'v', bits)
                CH8.bus(f'{name}_d{k}', 'hub', bits, [prev, (it.name, 'di')])
                prev = (it.name, 'dq')
            CH8.bus(f'{name}_d{len(sts)}', 'hub', bits, [prev, (Bk.name, pb)])
            m.setdefault('hub_stations', {})[name] = dict(path_um=round(L, 1), stations=len(sts),
                                                          floor_added=max(0, math.ceil(L / LINK_STAGE_UM - 1e-9) - 1))
            return
        if side == 'sp':
            vx = m['x_vch'] + 30.0 + HUB_LANE_PITCH * k_[0]
        elif side == 'hc':
            vx = m['x_spe'] - 30.0 - HUB_LANE_PITCH * k_[0]
        else:
            vx = m['x_vch'] + VCH8 / 2 + 70.0 * k_[0]
        k_[0] += 1
        path = _dedup([(fx(A), ya), (vx, ya), (vx, yb), (fx(Bk), yb)])
    name = f'hb_{a_}_{b_}'
    L = _poly_len(path)
    if L <= CC_REACH - 30.0:
        CH8.bus(name, 'hub', bits, [(A.name, pa), (Bk.name, pb)])
        m.setdefault('hub_stations', {})[name] = dict(path_um=round(L, 1), stations=0)
        return
    sts = CH8.run(name, [bits], path, [cor['vch']], path[0], reach=CC_REACH if CC_REACH < LINK_STAGE_UM else None)
    prev = (A.name, pa)
    for k, (it, s_, hop) in enumerate(sts):
        it.kind, it.domain = 'hstn', A.domain
        it.master = 'dsfd_hstn%s_%d' % ('h' if it.master.startswith('dsfd_stnh') else 'v', bits)
        CH8.bus(f'{name}_d{k}', 'hub', bits, [prev, (it.name, 'di')])
        prev = (it.name, 'dq')
    CH8.bus(f'{name}_d{len(sts)}', 'hub', bits, [prev, (Bk.name, pb)])
    m.setdefault('hub_stations', {})[name] = dict(path_um=round(L, 1), stations=len(sts),
                                                  floor_added=max(0, math.ceil(L / LINK_STAGE_UM - 1e-9) - 1))


def vch_x(m, tag):
    """per-chain x track inside the VCH (spreads the vertical chains over its width instead of one centre line)"""
    d = m.setdefault('_vch_lane', {})
    if tag not in d:
        d[tag] = len(d)
    i = d[tag] % LANES_VCH
    if VCH_INTERLEAVE:
        # S81-RERUN v3 GRT i50 (r9m215): the first ~14 chain tags filled lanes 0..13, i.e. the VCH WEST half only,
        # with the 'sp' hub lanes on top of them (scan overflow 2466, max window 1.37 on M9 at x_vch + 0..300 um):
        # stride the lane index so successive chains alternate across the whole VCH width
        i = (i * VCH_LANE_STRIDE) % LANES_VCH
    return m['x_vch'] + 60.0 + (VCH8 - 120.0) * (i + 0.5) / LANES_VCH


LANES_S14 = 8


def s14_x(m, half, tag):
    """per-chain x track inside the half's spine-to-field (S14) channel"""
    d = m.setdefault('_s14_lane_' + half, {})
    if tag not in d:
        d[tag] = len(d)
    i = d[tag] % LANES_S14
    g = m['geo']
    x0 = g['x_sp'] - SPF if half == 'W' else g['x_fe']
    return x0 + 50.0 + (SPF - 100.0) * (i + 0.5) / LANES_S14


def corr_y(m, tag):
    """per-chain y track inside the HC crossing corridor"""
    d = m.setdefault('_corr_lane', {})
    if tag not in d:
        d[tag] = len(d)
    i = d[tag] % LANES_CORR
    if CORR_INTERLEAVE:
        # S81-RERUN v4 GRT i50 (scan 1,212): 12 corridor tags took lanes 0..11 in order, so the heavy return / x chains
        # (r0..r5 ~770 b, xup / xdn 566 b) packed the corridor's LOWER half (y 10.64-11.12 mm) where they cross the
        # hc_s <-> hc_n hub lanes at the VCH east edge: 80 % of the overflow (x 16.5-17.5, y 10.5-11.0 mm).  Stride
        # the lane index so successive chains alternate over the whole corridor height.
        i = (i * CORR_LANE_STRIDE) % LANES_CORR
    c0, c1 = m['corridor']
    return c0 + 60.0 + (c1 - c0 - 120.0) * (i + 0.5) / LANES_CORR


def corr_c(m):
    return (m['corridor'][0] + m['corridor'][1]) / 2


def _dedup(P):
    out = []
    for p in P:
        if not out or _mh(out[-1], p) > 1e-6:
            out.append(p)
    return out


def _frame_of(m, half, t, c):
    for r, f in m['frames'].items():
        if f['half'] == half and f['tier'] == t and f['col'] == c:
            return r
    raise KeyError((half, t, c))


def chain_nets(CH8, name, src, stations, lanes):
    """single-lane chain nets: src (inst, fclk port, data port) -> station 1 lane 0 -> ... ; the last station's
    outputs are left for the caller (taps / sink)."""
    prev = src
    for k, it in enumerate(stations):
        CH8.bus(f'{name}_f{k}', 'fclk', 1, [(prev[0], prev[1]), (it.name, 'fi0')])
        CH8.bus(f'{name}_d{k}', 'lane', lanes[0], [(prev[0], prev[2]), (it.name, 'di0')])
        prev = (it.name, 'fo0', 'do0')
    CH8.m.setdefault('chain_tail', {})[name] = prev


def _add_tap(m, st_inst, lane, sink):
    """add a load (sink inst, fclk port, data port) to the nets driven by station st_inst's lane `lane`; if the
    station drives nothing yet, create the nets."""
    fo, do = f'fo{lane}', f'do{lane}'
    for i, (bid, cls, bits, eps) in enumerate(m['buses']):
        if eps[0] == (st_inst.name, fo):
            m['buses'][i] = (bid, cls, bits, eps + [(sink[0], sink[1])])
        elif eps[0] == (st_inst.name, do):
            m['buses'][i] = (bid, cls, bits, eps + [(sink[0], sink[2])])
            break
    else:
        lw = int(st_inst.master.split('_')[2].split('x')[0])
        m['buses'].append((f'{st_inst.name}_tf{lane}', 'fclk', 1, [(st_inst.name, fo), (sink[0], sink[1])]))
        m['buses'].append((f'{st_inst.name}_td{lane}', 'lane', lw, [(st_inst.name, do), (sink[0], sink[2])]))


def _run_multi(CH8, name, path, allowed, forced, ncol):
    """multi-lane trunk: the station count per position decides its lane count (lanes joined so far)."""
    L = _poly_len(path)
    # first pass with the widest signature (sizes), then per station the lanes joined so far
    sts = CH8.run(name, [CRET + 2] * ncol, path, allowed, path[0], forced=forced)
    out = []
    for it, s_, hop in sts:
        joined = sum(1 for f_ in forced if f_ <= s_ + 1e-6)
        n = max(1, joined)
        horiz = it.master.startswith('dsfd_stnh')
        it.master = stn_master([CRET + 2] * n, horiz)
        # The placer reserved the widest trunk. The emitted master is narrower
        # until all columns join; its model footprint must match that signature.
        # Shrink inside the reservation, retaining the conservative occupancy.
        if GEOMETRY_FIX:
            it.w, it.h = stn_dims([CRET + 2] * n, horiz)
        it.power_w = n * (CRET + 2) * FLOP_CLK_W * 1.5
        out.append((it, s_, n))
    return out


def _multi_nets(m, CH8, name, sts, ncol, frames_far_to_near, endb):
    """lanes: lane j of a station = the j-th column to have joined (the farthest first)."""
    B = m['buses']
    cur = {}      # lane j -> (inst, fport, dport) currently driving it
    fr = list(reversed(frames_far_to_near)) if False else frames_far_to_near[::-1]
    # frames_far_to_near is given near -> far by column index; joining order is far -> near
    order = [frames_far_to_near[c] for c in range(ncol - 1, -1, -1)]
    for j in range(ncol):
        m.setdefault('r_stages', {})[order[j]] = sum(1 for it, s_, n in sts if n > j)
    for k, (it, s_, n) in enumerate(sts):
        while len(cur) < n:
            j = len(cur)
            cur[j] = (f'cf{order[j]}', 'rf', 'rd')
        for j in range(n):
            src = cur[j]
            B.append((f'{name}_f{k}_{j}', 'fclk', 1, [(src[0], src[1]), (it.name, f'fi{j}')]))
            B.append((f'{name}_d{k}_{j}', 'lane', CRET + 2, [(src[0], src[2]), (it.name, f'di{j}')]))
            cur[j] = (it.name, f'fo{j}', f'do{j}')
    while len(cur) < ncol:
        j = len(cur)
        cur[j] = (f'cf{order[j]}', 'rf', 'rd')
    for j in range(ncol):
        src = cur[j]
        B.append((f'{name}_fe_{j}', 'fclk', 1, [(src[0], src[1]), (endb.name, f'fi{j}')]))
        B.append((f'{name}_de_{j}', 'lane', CRET + 2, [(src[0], src[2]), (endb.name, f'di{j}')]))


def _svc_chains(m, CH8, P, cor, end_spec, hub_block):
    g, hub = m['geo'], m['hub']
    vm, sel, colr = hub['vm'], hub['selector'], hub['collector']
    H = DIE[1]
    allc = list(cor.values())
    yS = (g['band_depth'] + g['y_f']) / 2
    yN = (g['y_top'] + H - g['band_depth']) / 2
    s14W = g['x_sp'] - SPF / 2
    vchx = m['x_vch'] + VCH8 / 2
    vmy = vm.y + vm.h / 2

    def vm_side(st):
        return 'W' if st[1] == 'W' else 'E'

    def spine_x(side):
        return s14_x(m, 'W', f'svc{len(m.get("_s14_lane_W", {}))}') if side == 'W' else \
            vch_x(m, f'svc{side}{len(m.get("_vch_lane", {}))}')

    def face_pt(sv, off):
        """(x, y) on the svc's field-facing edge, `off` from its east end"""
        x = sv.x + sv.w - off
        y = sv.y + sv.h if sv.orient == 'R0' else sv.y
        return x, y

    def strip_y(sv, tag=''):
        """per-chain y track in the band strip (spread over its height)"""
        d = m.setdefault('_strip_lane', {})
        k_ = (sv.orient, tag)
        if k_ not in d:
            d[k_] = sum(1 for o in d if o[0] == sv.orient)
        i = d[k_] % 6
        y0 = yS if sv.orient == 'R0' else yN
        return y0 + (i - 2.5) * 55.0

    def single(name, payload, fmt, src, src_xy, path, sink_end):
        """src: (inst, fclk port, data port); sink_end: (end inst) -> lane 0 ports fi0/di0"""
        lw = payload + (2 if fmt == 'vr' else 0)
        sts = CH8.run(name, [lw], _dedup(path), allc, src_xy)
        chain_nets(CH8, name, src, [it for it, _, _ in sts], [lw])
        tail = m['chain_tail'][name]
        CH8.bus(f'{name}_fe', 'fclk', 1, [(tail[0], tail[1]), (sink_end.name, 'fi0')])
        CH8.bus(f'{name}_de', 'lane', lw, [(tail[0], tail[2]), (sink_end.name, 'di0')])
        return sts

    def beside_svc(name, master, w, h, sv, off):
        x, y = face_pt(sv, off)
        yy = y + h / 2 + 6.0 if sv.orient == 'R0' else y - h / 2 - 6.0
        pl = P.near(x, yy, w, h, [cor['stripS'] if sv.orient == 'R0' else cor['stripN']], horiz=True, span=400.0)
        assert pl, name
        return P.add(Inst(name, master, pl[0], pl[1], w, h, 'R0', kind='hend', region='svc'))

    def beside_blk(name, master, w, h, blk, face, yfrac):
        y = blk.y + blk.h * yfrac
        x = blk.x - w / 2 - 6.0 if face == 'W' else blk.x + blk.w + w / 2 + 6.0
        gap = cor['gapS'] if blk.y < DIE[1] / 2 else cor['gapN']
        pl = P.near(x, y, w, h, [gap], horiz=False, span=300.0, rows=8)
        assert pl, name
        return P.add(Inst(name, master, pl[0], pl[1], w, h, 'R0' if face == 'E' else 'MY', kind='hend', region='svc'))
    for i, (st, sv) in enumerate(m['svcs'].items()):
        side = vm_side(st)
        sx = spine_x(side)
        sgn = -1 if st[0] == 'S' else 1          # end blocks spread over the VM face (r8 GRT: one pile at its centre)
        vy = vmy + sgn * (350.0 if st[1] == 'E' else 400.0)
        # VM -> svc: query vector (serial VM -> stream lane), entry meso at the service
        nm, w, h = end_spec('l2r', [512], 'vr')
        hs = P.add(_hub_at(P, f'hq_{st}', nm, w, h, vm, side, vy, cor))
        CH8.bus(f'hq_{st}_i', 'local', 513, [(vm.name, f'q{st}'), (hs.name, 'i')])
        CH8.bus(f'hq_{st}_s', 'local', 3, [(hs.name, 'st'), (vm.name, f'q{st}s')])
        nm, w, h = end_spec('m2l', [512], 'vr')
        he = beside_svc(f'hqe_{st}', nm, w, h, sv, 400.0)
        px, py = face_pt(sv, 400.0)
        single(f'q{st}', 512, 'vr', (hs.name, 'fo', 'od'), (hs.x + hs.w / 2, hs.y + hs.h / 2),
               [(hs.x + hs.w / 2, hs.y + hs.h / 2), (sx, vy), (sx, strip_y(sv, 'q' + st)), (px, strip_y(sv, 'q' + st)), (px, he.y + he.h / 2)], he)
        CH8.bus(f'hqe_{st}_o', 'local', 515, [(he.name, 'o'), (sv.name, 'q')])
        # svc -> VM: attention output + index (1,024 b), ratio CDC at the VM
        nm, w, h = end_spec('r2l', [1024], 'vr')
        ha = P.add(_hub_at(P, f'ha_{st}', nm, w, h, vm, side, vmy + sgn * (650.0 if st[1] == 'E' else 800.0), cor))
        px, py = face_pt(sv, 600.0)
        single(f'a{st}', 1024, 'vr', (sv.name, 'af', 'ad'), (px, py),
               [(px, py), (px, strip_y(sv, 'a' + st)), (sx, strip_y(sv, 'a' + st)), (sx, ha.y + ha.h / 2), (ha.x + ha.w / 2, ha.y + ha.h / 2)], ha)
        CH8.bus(f'ha_{st}_o', 'local', 1027, [(ha.name, 'o'), (vm.name, f'a{st}')])
        # svc -> selector (index scores) and -> collector (attention partials): meso entry beside the band block
        for tag, blk, port, off, pfx in (('ix', sel, 'i', 1200.0, 'x'), ('co', colr, 'c', 1500.0, 'o')):
            face = 'W' if st[1] == 'W' else 'E'
            nm, w, h = end_spec('m2l', [512], 'vr')
            he = beside_blk(f'h{tag}_{st}', nm, w, h, blk, face, 0.3 + 0.4 * (st[0] == 'N'))
            px, py = face_pt(sv, off)
            ex_ = he.x + he.w / 2
            if (blk.y < DIE[1] / 2) == (sv.orient == 'R0'):          # same band
                path = [(px, py), (px, strip_y(sv, tag + st)), (ex_, strip_y(sv, tag + st)), (ex_, he.y + he.h / 2)]
            else:                                                      # across the die through the VCH
                yo = yS if blk.y < DIE[1] / 2 else yN
                vx_ = vch_x(m, f'{tag}{st}')
                path = [(px, py), (px, strip_y(sv, tag + st)), (vx_, strip_y(sv, tag + st)), (vx_, yo), (ex_, yo), (ex_, he.y + he.h / 2)]
            single(f'{tag}{st}', 512, 'vr', (sv.name, f'{pfx}f', f'{pfx}d'), (px, py), path, he)
            if SEL_XSTG:
                # v8 (budget README: bk_selector <-> hix_* / bk_collector <-> hco_* 382-385 ps, regions not merged):
                # a crossing stage at the band block = the d8g1 meso FIFO (crossing arcs at 1.5 T - 60, low guard
                # flop at 1.5 T; a single register cannot hold a +-385 ps window on data that changes every cycle),
                # pins registered: +6 cycles (pin 1 + OFFSET 4 + out 1)
                xw, xh = stn_dims([515], True)     # W / E data faces (a horizontal station's outline)
                xs = beside_blk(f'xs{tag}_{st}', 'dsfd_xstg_515', xw, xh, blk, face, 0.3 + 0.4 * (st[0] == 'N'))
                xs.kind, xs.domain = 'xstg', blk.domain
                xs.power_w = 2 * 515 * FLOP_CLK_W * 1.5
                CH8.bus(f'h{tag}_{st}_x', 'local', 515, [(he.name, 'o'), (xs.name, 'i')])
                CH8.bus(f'h{tag}_{st}_o', 'local', 515, [(xs.name, 'o'), (blk.name, f'{port}{st}')])
            else:
                CH8.bus(f'h{tag}_{st}_o', 'local', 515, [(he.name, 'o'), (blk.name, f'{port}{st}')])
    # selector / collector -> VM (ratio CDC beside the VM, VCH side)
    for name, blk, yo in (('sel', sel, yS), ('col', colr, yN)):
        nm, w, h = end_spec('r2l', [512], 'vr')
        vy = vmy + (-1 if name == 'sel' else 1) * 950.0
        he = P.add(_hub_at(P, f'h{name}', nm, w, h, vm, 'E', vy, cor))
        bx = blk.x + blk.w / 2 + 300.0
        by_ = blk.y + blk.h if name == 'sel' else blk.y
        single(name, 512, 'vr', (blk.name, 'vf', 'vd'), (bx, by_),
               [(bx, by_), (bx, yo), (vch_x(m, name), yo), (vch_x(m, name), he.y + he.h / 2),
                (he.x + he.w / 2, he.y + he.h / 2)], he)
        CH8.bus(f'h{name}_o', 'local', 515, [(he.name, 'o'), (vm.name, name)])


def _hub_at(P, name, master, w, h, slab, side, y, cor):
    """an end / start block beside a hub slab: side 'W' in the S14 W channel, 'E' in the VCH"""
    x = slab.x - w / 2 - 6.0 if side == 'W' else slab.x + slab.w + w / 2 + 6.0
    pl = P.near(x, y, w, h, [cor['s14W'] if side == 'W' else cor['vch']], horiz=False, span=1800.0, rows=6)
    assert pl, name
    return Inst(name, master, pl[0], pl[1], w, h, 'MY' if side == 'W' else 'R0', kind='hend', region='hub')


LKCK_WH = (8.64, 8.64)        # LINK_FIX ck relay (one forwarded-clock buffer)


def _lk_pin_xy(lk, pin):
    """die coordinates of a real link-macro pin (orientations R0 / MY / MX / R180)"""
    r = real_lef(SERDES_LEF if lk.master == real_lef(SERDES_LEF)['name'] else UCIE_LEF)
    a, b, c, d = r['pins'][pin][1]
    x, y = (a + c) / 2, (b + d) / 2
    if lk.orient in ('MY', 'R180'):
        x = r['w'] - x
    if lk.orient in ('MX', 'R180'):
        y = r['h'] - y
    return lk.x + x, lk.y + y


def link_span_y(lk, port):
    """centre (die y) of a link macro's tx / rx pin span"""
    r = real_lef(SERDES_LEF if lk.master == real_lef(SERDES_LEF)['name'] else UCIE_LEF)
    ys = [_lk_pin_xy(lk, p_)[1] for p_ in r['pins'] if re.fullmatch(rf'{port}\[\d+\]', p_)]
    return (min(ys) + max(ys)) / 2


def link_half_y(lk, port, h, nh=2):
    """centre (die y) of slice h of nh of a link macro's tx / rx bits (pins ascend with the bit index)"""
    r = real_lef(SERDES_LEF if lk.master == real_lef(SERDES_LEF)['name'] else UCIE_LEF)
    n = sum(1 for p_ in r['pins'] if re.fullmatch(rf'{port}\[\d+\]', p_))
    lo, hi = h * n // nh, (h + 1) * n // nh - 1
    ys = [_lk_pin_xy(lk, f'{port}[{i}]')[1] for i in (lo, hi)]
    return (ys[0] + ys[1]) / 2, lo, hi


def _split_stations(P, CH8, lk, nm, port, allc, lx, side):
    """LINK_SPLIT: one 256-b station per half of the macro's tx / rx pin span, at the half's centre beside the macro face
    (a 1,122 um SerDes span from one centre station is a 561 um last hop > the 430.56 um reach; halves give <= 281 um)"""
    out = []
    for h in range(2):
        yc, lo, hi = link_half_y(lk, port, h)
        w, h_ = stn_dims([hi - lo + 1], False)
        x0 = lx + (8.0 if side == 'W' else -8.0 - w)
        pl = P.near(x0 + w / 2, yc, w, h_, allc, prev=None, horiz=False, span=200.0, rows=16)
        assert pl, (nm, port, h)
        P.n[f'{nm}{port}s'] += 1
        it = Inst(f'f_{nm}{port}s_{h}', stn_master([hi - lo + 1], False), pl[0], pl[1], w, h_, 'R0', kind='stn',
                  region='link', domain='fwd')
        it.power_w = (hi - lo + 1) * FLOP_CLK_W * 1.5
        out.append((P.add(it), lo, hi))
    return out


def _face_to(it, x, y):
    dx, dy = x - (it.x + it.w / 2), y - (it.y + it.h / 2)
    return ('E' if dx > 0 else 'W') if abs(dx) * it.h > abs(dy) * it.w else ('N' if dy > 0 else 'S')


def link_ck_relay(m, P, lk, cor, nm, drv):
    """LINK_FIX: the forwarded-clock relay of a link macro, outside its ck pin on the ck face (SerDes: the die-edge
    side of the link column, freed by moving the macro to the core side; UCIe: the edge corridor at the pin)"""
    w, h = LKCK_WH[0] - SHAVE, LKCK_WH[1] - SHAVE
    px, py = _lk_pin_xy(lk, 'clk')
    west = abs(px - lk.x) < 1.0
    if lk.master == real_lef(SERDES_LEF)['name']:
        x = dn(px - 1.296 - w, GX) if west else up(px + 1.296, GX)
        y = dn(py - h / 2, GY)
        assert P.occ.free((x, y, x + w, y + h), 0.432), (nm, x, y)
    else:
        pl = P.near(px + (-1 if west else 1) * (w / 2 + 6.0), py + h / 2, w, h,
                    [cor['edgeW'] if lk.name[3] == 'W' else cor['edgeE']], horiz=False, span=200.0, rows=8)
        assert pl, nm
        x, y = pl
    it = Inst(f'kc_{nm}', 'dsfd_lkck', x, y, w, h, 'R0', kind='lkck', region='link', domain='fwd')
    # faces fixed per instance by the master name: fi toward the driver (the tx chain tail), fo toward the ck pin
    it.master = f'dsfd_lkck_{_face_to(it, drv.x + drv.w / 2, drv.y + drv.h / 2)}{_face_to(it, px, py)}'
    return it


def _link_chains(m, CH8, P, cor, end_spec, hub_block, rowl):
    g, hub = m['geo'], m['hub']
    coll = hub['collective']
    allc = list(cor.values())
    s14 = {'W': g['x_sp'] - SPF / 2, 'E': g['x_fe'] + SPF / 2}
    vchx = m['x_vch'] + VCH8 / 2
    edge = {'W': (cor['edgeW'][0] + cor['edgeW'][2]) / 2, 'E': (cor['edgeE'][0] + cor['edgeE'][2]) / 2}
    cy = coll.y + coll.h / 2
    for lk in m['links']:
        side, i = lk.name[3], int(lk.name[4])
        t = 2 if i < 2 else 3
        ry = g['ch_y'][t] + rowl + 15.0 + 50.0 * (i % 2)
        ly = lk.y + lk.h / 2
        lx = lk.x + lk.w if side == 'W' else lk.x
        if LINK_FIX:
            ly_t, ly_r = link_span_y(lk, 'tx'), link_span_y(lk, 'rx')
        else:
            ly_t = ly_r = ly
        yy = cy + (i - 1.5) * 90.0
        cx = coll.x if side == 'W' else coll.x + coll.w
        nm = f'K{side}{i}'
        if side == 'W':
            sx_ = s14_x(m, 'W', nm)
            core = [(cx, yy), (sx_, yy), (sx_, ry)]
        else:
            vx_, cy_ = vch_x(m, nm), corr_y(m, nm)
            sx_ = s14_x(m, 'E', nm)
            core = [(cx, yy), (vx_, yy), (vx_, cy_), (sx_, cy_), (sx_, ry)]
        path = _dedup(core + [(edge[side], ry), (edge[side], ly_t), (lx, ly_t)])
        nm = f'K{side}{i}'
        # tx: collective -> macro tx (raw 512); the macro's parallel clock is the chain's forwarded clock
        # LINK_FIX: a station MUST stand at the path end = the centre of the macro's tx pin span
        sts = CH8.run(f'{nm}t', [512], path, allc, path[0], forced=(_poly_len(path),) if LINK_FIX else ())
        chain_nets(CH8, f'{nm}t', (coll.name, f'tf{side}{i}', f'td{side}{i}'), [it for it, _, _ in sts], [512])
        tail = m['chain_tail'][f'{nm}t']
        # rx: macro rx -> stations back -> hub meso end beside the collective
        endn, w, h = end_spec('m2l', [512], 'raw')
        he = P.add(_hub_at(P, f'hl_{side}{i}', endn, w, h, coll, side, yy, cor))
        if LINK_FIX:      # the rx chain starts with a station at the centre of the rx pin span
            rpath = _dedup([(lx, ly_r), (edge[side], ly_r)] + path[::-1][2:-1] + [(he.x + he.w / 2, he.y + he.h / 2)])
            rs = CH8.run(f'{nm}r', [512], rpath, allc, (lx, ly_r), forced=(1.0,))
        else:
            rpath = _dedup(path[::-1][:-1] + [(he.x + he.w / 2, he.y + he.h / 2)])
            rs = CH8.run(f'{nm}r', [512], rpath, allc, (lx, ly))
        rst = [it for it, _, _ in rs]
        ckd = (tail[0], tail[1])
        split = LINK_SPLIT and lk.master == real_lef(SERDES_LEF)['name']
        if split:         # tail -> two 256-b half-span stations -> macro tx halves; the macro ck follows the upper half
            txs = _split_stations(P, CH8, lk, nm, 'tx', allc, lx, side)
            CH8.bus(f'{nm}ts_f', 'fclk', 1, [ckd] + [(it.name, 'fi0') for it, _, _ in txs])
            for it, lo, hi in txs:
                CH8.bus(f'{nm}ts_d{lo}', 'lane', hi - lo + 1, [(tail[0], f'{tail[2]}[{lo}:{hi}]'), (it.name, 'di0')])
                CH8.bus(f'{nm}ts_o{lo}', 'lane', hi - lo + 1, [(it.name, 'do0'), (lk.name, f'tx[{lo}:{hi}]')])
            ckd = (txs[-1][0].name, 'fo0')
            rxs = _split_stations(P, CH8, lk, nm, 'rx', allc, lx, side)
        if LINK_FIX:      # the macro's clock source stands on its ck face: a forwarded-clock relay at the ck pin
            ck = P.add(link_ck_relay(m, P, lk, cor, nm, next(it for it in m['insts'] if it.name == ckd[0])))
            CH8.bus(f'{nm}_ckf', 'fclk', 1, [ckd, (ck.name, 'fi')])
            ckd = (ck.name, 'fo')
        if split:
            assert rst, nm
            CH8.bus(f'{nm}_clk', 'fclk', 1, [ckd, (lk.name, 'ck')] + [(it.name, 'fi0') for it, _, _ in rxs])
            for it, lo, hi in rxs:
                CH8.bus(f'{nm}rs_d{lo}', 'lane', hi - lo + 1, [(lk.name, f'rx[{lo}:{hi}]'), (it.name, 'di0')])
                CH8.bus(f'{nm}rs_o{lo}', 'lane', hi - lo + 1, [(it.name, 'do0'), (rst[0].name, f'di0[{lo}:{hi}]')])
            CH8.bus(f'{nm}rs_f', 'fclk', 1, [(rxs[-1][0].name, 'fo0'), (rst[0].name, 'fi0')])
        else:
            CH8.bus(f'{nm}_clk', 'fclk', 1, [ckd, (lk.name, 'ck')] + ([(rst[0].name, 'fi0')] if rst else
                                                                     [(he.name, 'fi0')]))
            CH8.bus(f'{nm}_tx', 'lane', 512, [(tail[0], tail[2]), (lk.name, 'tx')])
        if rst:
            # Split RX already drives the first station in two slices. Both
            # forms still need the rest of the chain and its hub termination.
            if not split:
                CH8.bus(f'{nm}r_d0', 'lane', 512, [(lk.name, 'rx'), (rst[0].name, 'di0')])
            prev = (rst[0].name, 'fo0', 'do0')
            for k, it in enumerate(rst[1:], 1):
                CH8.bus(f'{nm}r_f{k}', 'fclk', 1, [(prev[0], prev[1]), (it.name, 'fi0')])
                CH8.bus(f'{nm}r_d{k}', 'lane', 512, [(prev[0], prev[2]), (it.name, 'di0')])
                prev = (it.name, 'fo0', 'do0')
            CH8.bus(f'{nm}r_fe', 'fclk', 1, [(prev[0], prev[1]), (he.name, 'fi0')])
            CH8.bus(f'{nm}r_de', 'lane', 512, [(prev[0], prev[2]), (he.name, 'di0')])
        else:
            CH8.bus(f'{nm}r_de', 'lane', 512, [(lk.name, 'rx'), (he.name, 'di0')])
        CH8.bus(f'hl_{side}{i}_o', 'local', 515, [(he.name, 'o'), (coll.name, f'r{side}{i}')])


# ---------------------------------------------------------------------------------------- r8 ports / masters
GLUE_PREFIX = ('dsfd_xstg', 'dsfd_lkck', 'dsfd_stn', 'dsfd_hstn', 'dsfd_qbank', 'dsfd_rly', 'dsfd_m2l', 'dsfd_r2l', 'dsfd_l2r', 'dsfd_sstn', 'dsfd_node', 'dsfd_cfifo', 'dsfd_rstg')


def is_glue(master):
    return master.startswith(GLUE_PREFIX)


def port_usage(m):
    """inst -> port -> (dir, bits): endpoint 0 of a net drives it (r8 convention); top inputs drive their loads."""
    use = defaultdict(dict)
    for bid, cls, bits, eps in m['buses']:
        for j, (inst, port) in enumerate(eps):
            if inst == 'TOP':
                continue
            d = 'output' if j == 0 and cls != 'top_in' else 'input'
            if cls == 'phy_dfi':
                d = 'inout'
            port, lo, hi = pslice(port)
            if lo is not None:
                assert hi - lo + 1 == bits, (bid, inst, port, lo, hi, bits)
            old = use[inst].get(port)
            if old and old[0] != d:
                raise ValueError(f'{inst}.{port}: direction {old[0]} and {d}')
            use[inst][port] = (d, max(bits if lo is None else hi + 1, old[1] if old else 0))
    return use


def finalize_r8(m):
    """field glue masters by role (S13: one master per role and width): slot stations by their port set, return
    nodes by child kinds / fault chain; records m['pdir'][master][port] = (dir, bits)."""
    use = port_usage(m)
    by_ = {it.name: it for it in m['insts']}
    m['_nets_of_o'] = defaultdict(list)
    for b_ in m['buses']:
        if b_[3][0][1] == 'o':
            m['_nets_of_o'][b_[3][0][0]].append(b_)
    for it in m['insts']:
        u = use.get(it.name, {})
        if it.kind == 'hend' and '__' not in it.master:
            # one master per hub end/start block: its pin faces follow its own peers
            new = f'{it.master}__{it.name}'
            m['glue'][new] = m['glue'][it.master]
            it.master, it.orient = new, 'R0'
        if it.kind == 'sstn':
            code = ''.join(k for k in ('e0', 'e1', 'c0', 'c1', 'si', 'nf', 'qt') if k in u)
            it.master = f'dsfd_sstn_{code or "x"}'
        elif it.kind == 'node':
            par = [e for b_ in m['_nets_of_o'].get(it.name, []) for e in b_[3][1:]]
            py = max((by_[e[0]].y for e in par), default=0.0)
            it.master = 'dsfd_node_%s%s%s%s' % ('L' if u['a'][1] == LEAF else 'N', 'L' if u['b'][1] == LEAF else 'N',
                                                'f' if 'fi' in u else '', 'u' if py > it.y else 'd')
    pdir = defaultdict(dict)
    for it in m['insts']:
        for p_, (d, b) in use.get(it.name, {}).items():
            old = pdir[it.master].get(p_)
            if old and (old[0] != d or old[1] != b):
                raise ValueError(f'{it.master}.{p_}: {old} vs {(d, b)} on {it.name}')
            pdir[it.master][p_] = (d, b)
    m['pdir'] = pdir
    for it in m['insts']:
        if it.kind == 'hend':
            it.power_w = 5 * sum(b for d, b in pdir[it.master].values() if d == 'input') * FLOP_CLK_W * 1.5
    return pdir


def _lay(M, face, ports, layer, start=None, gap=0.96, length=None, pitch=1):
    """ports [(name, bits)] laid one after another along a face (pitch 1 track), centred on the face if start is None"""
    p = TRK[layer][1]
    K = _LAY_K[0]
    sp = lambda b: max(1, math.ceil(b / K)) * p * K * pitch
    gap = max(gap, 0.144, 1.2 * p * K)
    tot = sum(sp(b) for _, b in ports) + gap * (len(ports) - 1)
    L = length if length is not None else (M.h if face in 'EW' else M.w)
    pos = start if start is not None else max(2 * p * K + 0.2, (L - tot) / 2)
    for name, b in ports:
        M.face(name, b, face, layer, pos + sp(b) / 2, pitch)
        pos += sp(b) + gap


_LAY_K = [1]


def _peer_face(m, it, port):
    """face of `it` toward the other endpoints of the nets on (it, port) (nearest point of each peer's outline)"""
    by = m['_by']
    xs, ys = [], []
    cx_, cy_ = it.x + it.w / 2, it.y + it.h / 2
    for bid, cls, bits, eps in m['_nets_of'].get((it.name, port), []):
        for inst, p_ in eps:
            if inst != it.name and inst in by:
                o = by[inst]
                xs.append(min(max(cx_, o.x), o.x + o.w))
                ys.append(min(max(cy_, o.y), o.y + o.h))
    if not xs:
        return 'N'
    dx = sum(xs) / len(xs) - (it.x + it.w / 2)
    dy = sum(ys) / len(ys) - (it.y + it.h / 2)
    f = ('E' if dx > 0 else 'W') if abs(dx) * it.h > abs(dy) * it.w else ('N' if dy > 0 else 'S')
    if it.orient in ('MY', 'R180'):
        f = {'E': 'W', 'W': 'E'}.get(f, f)
    if it.orient in ('MX', 'R180'):
        f = {'N': 'S', 'S': 'N'}.get(f, f)
    return f


def masters_r8(m, k=1):
    pdir = m.get('pdir') or finalize_r8(m)
    if '_by' not in m:
        m['_by'] = {it.name: it for it in m['insts']}
        nets = defaultdict(list)
        for b in m['buses']:
            for inst, p_ in b[3]:
                nets[(inst, pslice(p_)[0])].append(b)
        m['_nets_of'] = nets
    first = {}
    for it in m['insts']:
        first.setdefault(it.master, it)
    _init_real()
    M = {}
    _LAY_K[0] = k
    for mst, it in first.items():
        if mst in REAL_FILES:
            continue
        ports = pdir.get(mst, {})
        Mx = Q.Master(mst, it.w, it.h, 3 if is_glue(mst) or mst == 'ot_s81_cfg7_seq' else 7, f'r8 {it.kind}')
        M[mst] = Mx
        _faces_r8(m, Mx, it, ports)
    if k > 1:
        for name, ports in real_ports_r8().items():
            M[name] = _spread_ports(_real_master_bundled(REAL_FILES[name], k, ports), k)
    return M


def _spread_ports(Mx, k):
    """bundled real view: ports on one face and layer pushed apart so their bundle pins never overlap"""
    groups = defaultdict(list)
    for p_ in Mx.order:
        s = Mx.ports[p_]
        if s[0] == 'face':
            groups[(s[2], s[3])].append(p_)
    for (face, layer), lst in groups.items():
        pk = TRK[layer][1] * k
        span = lambda p_: max(1, math.ceil(Mx.ports[p_][1] / k)) * pk * Mx.ports[p_][5]
        lst.sort(key=lambda p_: Mx.ports[p_][4])
        L = Mx.h if face in 'EW' else Mx.w
        lo = 2 * pk
        for p_ in lst:
            _, w, f, ly, c, pt = Mx.ports[p_]
            s0 = max(c - span(p_) / 2, lo)
            Mx.ports[p_] = ('face', w, f, ly, s0 + span(p_) / 2, pt)
            lo = s0 + span(p_) + 2 * pk
        if lo > L:                     # too many bundle pins at the real pitch: pack them at 1 bundle track
            lo = 2 * pk
            for p_ in lst:
                _, w, f, ly, c, pt = Mx.ports[p_]
                sp_ = max(1, math.ceil(w / k)) * pk
                Mx.ports[p_] = ('face', w, f, ly, lo + sp_ / 2, 1)
                lo += sp_ + 2 * pk
            if lo > L:
                raise ValueError(f'{Mx.name}: bundled face {face} overflows ({lo:.1f} > {L:.1f})')
    return Mx


def _faces_r8(m, Mx, it, ports):
    P_ = lambda names: [(n, ports[n][1]) for n in names if n in ports]
    kind, mst = it.kind, Mx.name
    if kind == 'stn':
        horiz = mst.startswith('dsfd_stnh')
        n = len([p_ for p_ in ports if p_.startswith('fi')])
        ins = [x for j in range(n) for x in ((f'fi{j}', 1), (f'di{j}', ports[f'di{j}'][1]))]
        outs = [x for j in range(n) for x in ((f'fo{j}', 1), (f'do{j}', ports[f'do{j}'][1]))]
        _lay(Mx, 'W' if horiz else 'S', ins, 'M4' if horiz else 'M5', gap=0.0)
        _lay(Mx, 'E' if horiz else 'N', outs, 'M4' if horiz else 'M5', gap=0.0)
    elif kind == 'lkck':     # forwarded-clock relay: in toward its driver, out toward the macro ck pin
        for p_, f_, at in (('fi', mst[-2], 2.16), ('fo', mst[-1], 6.48)):
            Mx.face(p_, 1, f_, 'M5' if f_ in 'NS' else 'M4', at, 1)
    elif kind == 'qbank':
        ef = 'N' if mst.endswith('_S') else 'S'
        df = 'S' if ef == 'N' else 'N'
        el = [p_ for p_ in sorted(ports, key=_pnum) if p_[:2] in ('o_', 'e_')]
        dl = [p_ for p_ in sorted(ports, key=_pnum) if p_[:2] in ('i_', 'd_')]
        _lay(Mx, ef, P_(el), 'M5', gap=0.0)
        _lay(Mx, df, P_(dl), 'M5', gap=0.0)
        _lay(Mx, 'W', P_(['ck', 'rs']), 'M4')
    elif kind == 'rly':
        fi, fo = RLY_FACES[mst]
        _lay(Mx, fi, P_(['i']), 'M4' if fi in 'EW' else 'M5', gap=0.0)
        _lay(Mx, fo, P_(['o']), 'M4' if fo in 'EW' else 'M5', gap=0.0)
        cf_ = [f_ for f_ in 'NSEW' if f_ not in (fi, fo)][0]
        _lay(Mx, cf_, P_(['ck', 'rs']), 'M4' if cf_ in 'EW' else 'M5')
    elif kind == 'hstn':
        horiz = mst.startswith('dsfd_hstnh')
        _lay(Mx, 'W' if horiz else 'S', P_(['di']), 'M4' if horiz else 'M5', gap=0.0)
        _lay(Mx, 'E' if horiz else 'N', P_(['dq']), 'M4' if horiz else 'M5', gap=0.0)
        _lay(Mx, 'N' if horiz else 'W', P_(['ck']), 'M5' if horiz else 'M4')
    elif kind == 'sstn':
        _lay(Mx, 'S', P_(['xai', 'xbi', 'cci', 'qt', 'so']), 'M5', pitch=3 if _LAY_K[0] == 1 else 2)
        _lay(Mx, 'N', P_(['e0', 'c0', 'cc', 'xa', 'xb', 'si', 'e1', 'c1']), 'M5', pitch=3 if _LAY_K[0] == 1 else 2)
        _lay(Mx, 'W', P_(['ck', 'rs']), 'M4')
        _lay(Mx, 'E', P_(['nf']), 'M4')
    elif kind == 'node':
        la, lb, up_ = mst[10] == 'L', mst[11] == 'L', mst.endswith('u')
        _lay(Mx, 'W', P_([s_ for s_, lf in (('a', la), ('b', lb)) if lf]), 'M4')
        sface = [s_ for s_, lf in (('a', la),) if not lf] + ['fo'] + ([] if up_ else ['o'])
        nface = [s_ for s_, lf in (('b', lb),) if not lf] + ['fi'] + (['o'] if up_ else [])
        _lay(Mx, 'S', P_(sface), 'M5')
        _lay(Mx, 'N', P_(nface), 'M5')
        _lay(Mx, 'E', P_(['clk', 'rst_n']), 'M4')
    elif kind == 'xstg':           # placed beside the band block: R0 east of it, MY west of it -> o faces the block
        _lay(Mx, 'W', P_(['o']), 'M4', gap=0.0)
        _lay(Mx, 'E', P_(['i']), 'M4', gap=0.0)
        _lay(Mx, 'S', P_(['ck', 'cw']), 'M5')
    elif kind == 'rstg':
        _lay(Mx, 'N', P_(['i']), 'M5')
        _lay(Mx, 'S', P_(['o']), 'M5')
        _lay(Mx, 'W', P_(['ck', 'rs']), 'M4')
    elif kind == 'cfifo':
        c0 = SSTN_X + SSTN_WH[0] / 2 - CF_X
        c1 = COL_W8 - RSC_W / 2 - CF_X
        if CFIFO_V2:              # 432 um outline: the return pins at its E end (the return column lies beyond it)
            c1 = min(c1, Mx.w - 30.0)
        _lay(Mx, 'S', P_(['xf', 'xd']), 'M5', start=c0 - 15.0)
        _lay(Mx, 'S', P_(['rf', 'rd']), 'M5', start=c1 - 30.0)
        _lay(Mx, 'N', P_(['xa', 'xb', 'cc', 'st']), 'M5', start=c0 - 15.0)
        _lay(Mx, 'N', P_(['ri']), 'M5', start=c1 - 2.0)
        _lay(Mx, 'N', P_(['co', 'rs']), 'M5', start=c0 + 60.0)
        _lay(Mx, 'W', P_(['ck', 'rst']), 'M4')
    elif kind == 'seq':
        _lay(Mx, 'W', P_([f'q{j}' for j in range(7)] + ['a'] + [f'ce{j}' for j in range(7)]), 'M4', gap=0.0)
        _lay(Mx, 'N', P_(['cfg', 'go_e']), 'M5')
        _lay(Mx, 'E', P_(['lc', 'st']), 'M4')
        _lay(Mx, 'S', P_(['clk', 'rst_n']), 'M5')
    elif kind == 'hend':
        faces = defaultdict(list)
        for p_ in sorted(ports, key=_pnum):
            faces['S' if p_ in ('ck', 'cks', 'rs', 'rss') else _peer_face(m, it, p_)].append((p_, ports[p_][1]))
        for f, lst in faces.items():
            L = Mx.h if f in 'EW' else Mx.w
            K = _LAY_K[0]
            need = sum(max(1, math.ceil(b / K)) * K * 0.048 + max(0.144, 0.0576 * K) for _, b in lst) + 1.0
            if need > L:
                raise ValueError(f'{Mx.name}: face {f} needs {need:.1f} um > {L:.1f}')
            _lay(Mx, f, lst, 'M4' if f in 'EW' else 'M5', gap=0.0)
    elif kind in ('bf', 'bf_nv'):
        _lay(Mx, 'S', P_(['go', 'cfg', 'ck', 'rs']), 'M5', start=230.0)
        _lay(Mx, 'S', P_(['x0', 'x1']), 'M5', start=SSTN_X - 4.32 - 10.0)
        _lay(Mx, 'N', P_(['nv', 'nvr']), 'M5', start=560.0)
        _lay(Mx, 'E', P_(['r0', 'r1']), 'M4')
        _lay(Mx, 'S', P_(['st']), 'M5', start=SSTN_X - 4.32 + 40.0)
    elif kind == 'nvx':
        _lay(Mx, 'S', P_(['nv', 'nvr']), 'M5', start=560.0)
        _lay(Mx, 'N', P_(['st', 'ck', 'rs']), 'M5', start=SSTN_X)
    elif kind == 'ctrl':
        ph = real_lef(PHY_LEF)
        dfi = real_ports_r8()[ph['name']]['dfi']
        if _LAY_K[0] == 1:
            Mx.ports['phy'] = ('xy', [(ph['pins'][n][1][0] + ph['pins'][n][1][2]) / 2 for n in dfi])
            Mx.order.append('phy')
        else:
            Mx.face('phy', len(dfi), 'S', 'M5', Mx.w / 2, 4)
        _lay(Mx, 'N', P_(['rd']), 'M5')
        _lay(Mx, 'N', P_(['ckh', 'cks', 'rst']), 'M5', start=60.0)
    else:   # hub slabs, band blocks, services: each port on the face toward its peers, ordered by peer position
        faces = defaultdict(list)
        for p_ in sorted(ports):
            if p_ == 'phy':
                continue
            faces[_peer_face(m, it, p_)].append(p_)
        for f, lst in faces.items():
            lst.sort(key=lambda p_: _peer_pos(m, it, p_, f))
            L = Mx.h if f in 'EW' else Mx.w
            K = _LAY_K[0]
            bwf = lambda b: max(1, math.ceil(b / K)) * K * 0.048
            tot = sum(bwf(ports[p_][1]) for p_ in lst) + 2.0 * len(lst)
            if tot > L - 1.0:
                raise ValueError(f'{Mx.name} face {f}: {tot:.0f} um of pins > {L:.0f}')
            # ports in peer order, spread evenly over the whole face (equal gaps): a slab face carries thousands of
            # die wires, and packing them at the peer positions piled them into one GCell column (r8 GRT, VM E face)
            if False:
                gap = (L - 0.8 - sum(bwf(ports[p_][1]) for p_ in lst)) / (len(lst) + 1)
                pos = 0.4 + gap
                for p_ in lst:
                    bw = bwf(ports[p_][1])
                    Mx.face(p_, ports[p_][1], f, 'M4' if f in 'EW' else 'M5', pos + bw / 2, 1)
                    pos += bw + gap
                continue
            pos = 0.4                     # band blocks / services: at their peers' positions where they fit
            for p_ in lst:
                bw = bwf(ports[p_][1])
                want = _peer_pos(m, it, p_, f) - bw / 2
                rem = sum(bwf(ports[q][1]) + 2.0 for q in lst[lst.index(p_) + 1:])
                pos = min(max(pos, want), L - 0.4 - rem - bw)
                Mx.face(p_, ports[p_][1], f, 'M4' if f in 'EW' else 'M5', pos + bw / 2, 1)
                pos += bw + 2.0


def _pnum(p_):
    mm = re.match(r'^([a-z]+)(\d*)$', p_)
    return (int(mm.group(2)) if mm and mm.group(2) else -1, p_)


def _peer_pos(m, it, port, f):
    """peer centroid along face f, in the master frame"""
    by = m['_by']
    xs, ys = [], []
    for bid, cls, bits, eps in m['_nets_of'].get((it.name, port), []):
        for inst, p_ in eps:
            if inst != it.name and inst in by:
                o = by[inst]
                xs.append(o.x + o.w / 2)
                ys.append(o.y + o.h / 2)
    if not xs:
        return 0.0
    if f in 'EW':
        v = sum(ys) / len(ys) - it.y
        return it.h - v if it.orient in ('MX', 'R180') else v
    v = sum(xs) / len(xs) - it.x
    return it.w - v if it.orient in ('MY', 'R180') else v


# ---------------------------------------------------------------------------------------- r8 glue RTL
def _decl(ports):
    return ',\n'.join(f'    {d} wire [{b - 1}:0] {p_}' for p_, (d, b) in sorted(ports.items(), key=lambda kv: _pnum(kv[0])))


def _sync(name, clk, rst_in):
    return (f'    reg [1:0] {name}_q; always @(posedge {clk} or negedge {rst_in}) if (!{rst_in}) {name}_q <= 2\'b00; '
            f'else {name}_q <= {{{name}_q[0], 1\'b1}};\n    wire {name} = {name}_q[1];')


def glue_rtl(m):
    """Verilog of every generated glue master (structural over the real primitives ot_fwd_link_stage, ot_meso_fifo,
    ot_ratio_cdc_fifo, ot_v41_retn_w17w10)."""
    pdir = m['pdir']
    G = m['glue']
    out = ['// GENERATED by tools/dsrom_s81_fulldie.py --gen r8 (CLAUDE S81-DIE): S81 die glue masters.',
           '// Forwarded stations: one ot_fwd_link_stage (ENABLE, W <= 512 slices) per lane; column FIFO: ot_meso_fifo',
           '// W564 entry crossing; hub end/start blocks: ot_meso_fifo / ot_ratio_cdc_fifo; return nodes wrap',
           '// ot_v41_retn_w17w10 with the ot_v41_field_w17w10 leaf packing.  Lane format vr: d[0] rst_n, d[1] valid.',
           '`timescale 1ns/1ps', '']
    for mst in sorted(pdir):
        if not is_glue(mst):
            continue
        ports = pdir[mst]
        body = []
        if mst.startswith('dsfd_lkck'):
            body.append('    assign fo = fi;   // forwarded-clock relay (a clock buffer; CTS sizes it)')
        elif mst.startswith('dsfd_stn'):
            n = len([p_ for p_ in ports if p_.startswith('fi')])
            for j in range(n):
                w = ports[f'di{j}'][1]
                ns = math.ceil(w / 512)
                for s in range(ns):
                    lo, hi = 512 * s, min(w, 512 * (s + 1))
                    fo = f'fo{j}[0]' if s == 0 else f'fx{j}_{s}'
                    if s:
                        body.append(f'    wire {fo};')
                    body.append(f'    ot_fwd_link_stage #(.W({hi - lo}), .ENABLE(1\'b1)) u_{j}_{s} (.fclk_i(fi{j}[0]), '
                                f'.rst_n(1\'b1), .i_v(1\'b1), .i_d(di{j}[{hi - 1}:{lo}]), .fclk_o({fo}), .o_v(), '
                                f'.o_d(do{j}[{hi - 1}:{lo}]));')
        elif mst.startswith('dsfd_qbank'):
            for p_ in sorted(ports, key=_pnum):
                if p_[:2] in ('i_', 'e_'):
                    q_ = ('o_' if p_[:2] == 'i_' else 'd_') + p_[2:]
                    w = ports[p_][1]
                    body.append(f'    reg [{w - 1}:0] r_{p_[2:]};')
                    body.append(f'    always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) r_{p_[2:]} <= {w}\'d0; '
                                f'else r_{p_[2:]} <= {p_};')
                    body.append(f'    assign {q_} = r_{p_[2:]};')
        elif mst.startswith('dsfd_rly'):
            w = ports['i'][1]
            body.append(f'    reg [{w - 1}:0] r; always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) r <= {w}\'d0; else r <= i;')
            body.append('    assign o = r;')
        elif mst.startswith('dsfd_xstg'):
            w = ports['i'][1]
            body += ['    // SEL_XSTG crossing stage (S81-RERUN v8): the end block (its own clock region, cw) -> band block (ck)',
                     '    // crossing is bounded at 382-385 ps, beyond a single-register window (data changes every cycle), so',
                     '    // it crosses through the d8g1 meso FIFO (the closed die crossing: arcs settle in 1.5 T - 60 ps, low',
                     '    // guard flop at 1.5 T) with registered pins.  Lane vr: i[0] rst_n, i[1] valid.',
                     _sync('rsync', 'ck[0]', 'i[0]'),
                     f'    reg [{w - 1}:0] ir; always @(posedge cw[0]) ir <= i;',
                     '    wire rv, wl, rl, wf, rf_, wr; wire [%d:0] rq;' % (w - 3),
                     f'    ot_meso_fifo #(.W({w - 2}), .ENABLE(1\'b1), .DEPTH(8), .OFFSET(4), .GUARD_LO(1), .GUARD_HI(7), '
                     '.CREDITS(16)) u_x (.wclk(cw[0]), .wrst_n(ir[0]), .w_v(ir[1]), .w_rdy(wr), '
                     f'.w_d(ir[{w - 1}:2]), .rclk(ck[0]), .rrst_n(rsync), .r_v(rv), .r_rdy(1\'b1), .r_d(rq), .w_live(wl), '
                     '.r_live(rl), .w_fault(wf), .r_fault(rf_));',
                     f'    reg [{w - 1}:0] orr; always @(posedge ck[0]) orr <= {{rq, rv & rl, rsync}};',
                     '    assign o = orr;']
        elif mst.startswith('dsfd_hstn'):
            w = ports['di'][1]
            body.append('    wire fck;   // common clock: the stage captures on negedge fclk_i = posedge ck')
            body.append('    ot_fwd_clk_inv u_ck (.a(ck[0]), .y(fck));')
            for s_ in range(math.ceil(w / 512)):
                lo, hi = 512 * s_, min(w, 512 * (s_ + 1))
                body.append(f'    ot_fwd_link_stage #(.W({hi - lo}), .ENABLE(1\'b1)) u_{s_} (.fclk_i(fck), .rst_n(1\'b1), '
                            f'.i_v(1\'b1), .i_d(di[{hi - 1}:{lo}]), .fclk_o(), .o_v(), .o_d(dq[{hi - 1}:{lo}]));')
        elif mst.startswith('dsfd_sstn'):
            body.append('    reg [282:0] ra; reg [265:0] rb; reg [14:0] rc; reg [1:0] rst;')
            body.append('    always @(posedge ck[0]) begin ra <= xai; rb <= xbi; end')
            body.append('    always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) rc <= 15\'d0; else rc <= cci;')
            body.append('    assign xa = {ra[282] & rs[0], ra[281:0]};   // xs_v qualified by the column reset')
            body.append('    assign xb = rb;\n    assign cc = rc;')
            if 'qt' in ports:
                body.append('    assign qt = xbi;                             // previous slot q1/e1: same-cycle re-buffer')
            terms = [p_ for p_ in ('e0', 'e1', 'c0', 'c1', 'si') if p_ in ports]
            o = ' | '.join(terms) if terms else "2'b00"
            nf = ' | {nf[0], 1\'b0}' if 'nf' in ports else ''
            body.append(f'    always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) rst <= 2\'b00; else rst <= {o}{nf};')
            body.append('    assign so = rst;')
        elif mst.startswith('dsfd_node'):
            la, lb, fch = mst[10] == 'L', mst[11] == 'L', 'f' in mst[12:]
            for s_, leaf in (('a', la), ('b', lb)):
                if leaf:
                    body.append(f'    wire {s_}_v = {s_}[0]; wire [31:0] {s_}_d = {s_}[32:1]; wire {s_}_e = {s_}[59];')
                    body.append(f'    wire [31:0] {s_}_t = {{{s_}[62:60], {s_}[48:33], {s_}[53:49], 3\'d0, {s_}[58:54]}};')
                else:
                    body.append(f'    wire {s_}_v = {s_}[0]; wire [31:0] {s_}_t = {s_}[32:1]; wire [31:0] {s_}_d = {s_}[64:33]; '
                                f'wire {s_}_e = {s_}[65];')
            body.append('    wire ov, oe, flt; wire [31:0] ot_, od;')
            body.append('    ot_v41_retn_w17w10 #(.RD(64), .RST(1), .BYPASS(1)) u_n (.clk(clk[0]), .rst_n(rst_n[0]), '
                        '.a_v(a_v), .a_t(a_t), .a_d(a_d), .a_e(a_e), .b_v(b_v), .b_t(b_t), .b_d(b_d), .b_e(b_e), '
                        '.o_v(ov), .o_t(ot_), .o_d(od), .o_e(oe), .fault(flt), .quiet());')
            body.append('    assign o = {oe, od, ot_, ov};')
            fi = ' | fi[0]' if fch else ''
            body.append(f'    reg fr; always @(posedge clk[0] or negedge rst_n[0]) if (!rst_n[0]) fr <= 1\'b0; else fr <= flt{fi};')
            body.append('    assign fo = fr;')
        elif mst == 'dsfd_rstg':
            body.append('    reg [65:0] r; always @(posedge ck[0]) r <= i;')
            body.append('    assign o = {r[65:1], r[0] & rs[0]};')
        elif mst == 'dsfd_cfifo' and CFIFO_V2:
            body += [_sync('rsync', 'ck[0]', 'rst[0]'),
                     '    // CFIFO_V2 (S81-RERUN fail-fast, cfifo e654bb52a SS -252 / FF -21): every input captured at its pin,',
                     '    // every data output from a flop, the overrun check in the write domain (sticky, synchronised)',
                     '    assign co = ck;          // column clock-tree root (option C region root)',
                     '    assign rs = rsync;',
                     '    reg [565:0] xi; always @(posedge xf[0]) xi <= xd;',
                     '    reg [1:0] sti; always @(posedge ck[0]) sti <= st;',
                     '    wire xv, wl, rl, wf, rf_, wr; wire [563:0] xq;',
                     f'    ot_meso_fifo #(.W(564), .ENABLE(1\'b1){MESO_P()}) u_x (.wclk(xf[0]), .wrst_n(xi[0]), .w_v(xi[1]), .w_rdy(wr), '
                     '.w_d(xi[565:2]), .rclk(ck[0]), .rrst_n(rsync), .r_v(xv), .r_rdy(1\'b1), .r_d(xq), .w_live(wl), '
                     '.r_live(rl), .w_fault(wf), .r_fault(rf_));',
                     '    reg wov; always @(posedge xf[0]) if (!xi[0]) wov <= 1\'b0; else if (xi[1] & ~wr) wov <= 1\'b1;',
                     '    reg [1:0] wov_s; always @(posedge ck[0]) wov_s <= {wov_s[0], wov};',
                     '    // lane stream {x0 283 | x1 266 | cc 15}; xs_v, go and cfg_go qualified by the FIFO valid, registered',
                     '    reg [282:0] xa_r; reg [265:0] xb_r; reg [14:0] cc_r;',
                     '    always @(posedge ck[0]) begin xa_r <= {xq[282] & xv, xq[281:0]}; xb_r <= xq[548:283];',
                     '        cc_r <= {xq[563:551], xq[550] & xv, xq[549] & xv}; end',
                     '    assign xa = xa_r; assign xb = xb_r; assign cc = cc_r;',
                     '    reg [67:0] rr; reg flt;',
                     '    always @(posedge ck[0] or negedge rsync) if (!rsync) begin rr <= 68\'d0; flt <= 1\'b0; end',
                     '        else begin rr <= {sti[1] | flt, sti[0] | ~rl, ri}; flt <= flt | wf | rf_ | wov_s[1]; end',
                     '    assign rf = ck;',
                     '    assign rd = {rr, rr[0], rsync};   // {status, root word, valid = root o_v, rst_n}']
        elif mst == 'dsfd_cfifo':
            body += [_sync('rsync', 'ck[0]', 'rst[0]'),
                     '    assign co = ck;          // column clock-tree root (option C region root)',
                     '    assign rs = rsync;',
                     '    wire xv, wl, rl, wf, rf_, wr; wire [563:0] xq;',
                     f'    ot_meso_fifo #(.W(564), .ENABLE(1\'b1){MESO_P()}) u_x (.wclk(xf[0]), .wrst_n(xd[0]), .w_v(xd[1]), .w_rdy(wr), '
                     '.w_d(xd[565:2]), .rclk(ck[0]), .rrst_n(rsync), .r_v(xv), .r_rdy(1\'b1), .r_d(xq), .w_live(wl), '
                     '.r_live(rl), .w_fault(wf), .r_fault(rf_));',
                     '    // lane stream {x0 283 | x1 266 | cc 15}; xs_v, go and cfg_go qualified by the FIFO valid',
                     '    assign xa = {xq[282] & xv, xq[281:0]};',
                     '    assign xb = xq[548:283];',
                     '    assign cc = {xq[563:551], xq[550] & xv, xq[549] & xv};',
                     '    reg [67:0] rr; reg flt;',
                     '    always @(posedge ck[0] or negedge rsync) if (!rsync) begin rr <= 68\'d0; flt <= 1\'b0; end',
                     '        else begin rr <= {st[1] | flt, st[0] | ~rl, ri}; flt <= flt | wf | rf_ | (xd[1] & ~wr); end',
                     '    assign rf = ck;',
                     '    assign rd = {rr, rr[0], rsync};   // {status, root word, valid = root o_v, rst_n}']
        else:
            spec = G[mst]
            kind, lanes, fmt = spec['kind'], spec['lanes'], spec['fmt']
            if kind == 'l2r':
                pw = lanes[0]
                body += [_sync('rsl', 'ck[0]', 'rs[0]'), _sync('rss_', 'cks[0]', 'rss[0]'),
                         '    wire wr, wl, rv, rl;', f'    wire [{pw - 1}:0] rd_;',
                         f'    ot_ratio_cdc_fifo #(.W({pw})) u_c (.wclk(ck[0]), .wrst_n(rsl), .w_v(i[0]), .w_rdy(wr), '
                         f'.w_d(i[{pw}:1]), .rclk(cks[0]), .rrst_n(rss_), .r_v(rv), .r_rdy(1\'b1), .r_d(rd_), '
                         '.w_live(wl), .r_live(rl));',
                         '    assign fo = cks;', '    assign od = {rd_, rv, rss_};', "    assign st = {1'b0, wl, wr};"]
            else:
                body.append(_sync('rsl', 'ck[0]', 'rs[0]'))
                base, lv, fl = 0, [], []
                for j, pw in enumerate(lanes):
                    vr = fmt == 'vr'
                    if vr:
                        wr, wv, wd = f'di{j}[0]', f'di{j}[1]', f'di{j}[{pw + 1}:2]'
                    else:
                        body.append(_sync(f'wrs{j}', f'fi{j}[0]', 'rs[0]'))
                        wr, wv, wd = f'wrs{j}', "1'b1", f'di{j}[{pw - 1}:0]'
                    body.append(f'    wire rv{j}, rl{j}, wf{j}, rf{j}; wire [{pw - 1}:0] rq{j};')
                    if kind == 'm2l':
                        body.append(f'    ot_meso_fifo #(.W({pw}), .ENABLE(1\'b1){MESO_P()}) u_{j} (.wclk(fi{j}[0]), .wrst_n({wr}), '
                                    f'.w_v({wv}), .w_rdy(), .w_d({wd}), .rclk(ck[0]), .rrst_n(rsl), .r_v(rv{j}), '
                                    f'.r_rdy(1\'b1), .r_d(rq{j}), .w_live(), .r_live(rl{j}), .w_fault(wf{j}), .r_fault(rf{j}));')
                    else:
                        body.append(f'    assign wf{j} = 1\'b0; assign rf{j} = 1\'b0;')
                        body.append(f'    ot_ratio_cdc_fifo #(.W({pw})) u_{j} (.wclk(fi{j}[0]), .wrst_n({wr}), .w_v({wv}), '
                                    f'.w_rdy(), .w_d({wd}), .rclk(ck[0]), .rrst_n(rsl), .r_v(rv{j}), .r_rdy(1\'b1), '
                                    f'.r_d(rq{j}), .w_live(), .r_live(rl{j}));')
                    body.append(f'    assign o[{base + pw}:{base}] = {{rq{j}, rv{j}}};')
                    base += pw + 1
                    lv.append(f'rl{j}')
                    fl += [f'wf{j}', f'rf{j}']
                body.append(f'    assign o[{base + 1}:{base}] = {{{" | ".join(fl)}, {" & ".join(lv)}}};   // {{fault, live}}')
        out.append(f'module {mst} (\n{_decl(ports)}\n);')
        out += body
        out.append('endmodule\n')
    return '\n'.join(out)


def plan_record_r8(m):
    kinds, area = defaultdict(int), defaultdict(float)
    for it in m['insts']:
        kinds[it.kind] += 1
        area[it.kind] += (it.w + SHAVE) * (it.h + SHAVE) / 1e6
    cls = defaultdict(lambda: dict(buses=0, wires=0))
    for bid, c, bits, eps in m['buses']:
        cls[c]['buses'] += 1
        cls[c]['wires'] += bits
    g = m['geo']
    ch = m['chains']
    fr = m['frames']
    xs, rs = m.get('x_stages', {}), m.get('r_stages', {})
    mc = 4 if MESO_D8 else 2
    hf = m.get('hop_fix', {}).get('fwd_rt_add', 0)
    hf += 2 if CFIFO_V2 else 0              # cfifo v2: xd pin register + output register
    rt = {r: xs.get(r, 0) + mc + (f['last_slot'] + 1) + 1 + f.get('ret_stages', 0) + rs.get(r, 0) + mc
          + f.get('bank_stages', 0) + f.get('relay_x', 0) + f.get('relay_ret', 0) + hf for r, f in fr.items()}
    far = max(rt, key=rt.get)
    stn = [it for it in m['insts'] if it.kind == 'stn']
    slices = sum(math.ceil(w / 512) for it in stn for w in _stn_lanes(m, it))
    meso = sum(1 for it in m['insts'] if it.kind == 'cfifo') + sum(
        len(m['glue'][it.master]['lanes']) for it in m['insts'] if it.kind == 'hend' and m['glue'][it.master]['kind'] == 'm2l')
    ratio = sum(1 for it in m['insts'] if it.kind == 'hend' and m['glue'][it.master]['kind'] != 'm2l')
    over = [c for c in ch if c['max_hop_um'] > LINK_STAGE_UM]
    return dict(
        schema='opentallas.dsrom-s81-fulldie.floorplan.r8.v1', tool='tools/dsrom_s81_fulldie.py --gen r8',
        tool_sha256=sha('tools/dsrom_s81_fulldie.py'),
        sources_sha256={p_: sha(p_) for p_ in (DECISION, Q_LEF, CFG_LEF, PHY_LEF, SERDES_LEF, UCIE_LEF, CFG7_RTL, MESO_V7,
                                               HEAD_A_LEF, HEAD_B_LEF, 'rtl/v41rom/ot_dsrom_head_bundle.sv',
                                               'rtl/common/ot_fwd_link_stage.sv', 'rtl/common/ot_meso_fifo.sv',
                                               'rtl/common/ot_ratio_cdc_fifo.sv', 'rtl/v41die/ot_v41_retn_w17w10.sv')},
        die=dict(w_um=DIE[0], h_um=DIE[1], mm2=round(DIE[0] * DIE[1] / 1e6, 3)), variant=m['variant'],
        slot=dict(elem_frame_h_um=ELEM_FRAME_H, slot_h_um=g['slot_h'], slots_per_column=g['slots'],
                  capacity=capacity_report()),
        instances=dict(kinds), area_mm2_by_kind={k: round(v, 3) for k, v in area.items()},
        placed_footprint_mm2=round(sum(area.values()), 2),
        utilisation=dict(placed_over_die=round(sum(area.values()) / (DIE[0] * DIE[1] / 1e6), 4),
                         field_frames_mm2=round(ROOTS * COL_W8 * g['slots'] * g['slot_h'] / 1e6, 2)),
        geometry={k: (round(v, 3) if isinstance(v, float) else v) for k, v in g.items() if k != 'col_x'},
        forwarded=dict(stations=len(stn), ot_fwd_link_stage_instances=slices, chains=len(ch),
                       max_hop_um=max(c['max_hop_um'] for c in ch), hops_over_430p56=len(over),
                       over_examples=over[:10], meso_fifos=meso, ratio_cdc_fifos=ratio),
        field_round_trip_cycles=dict(farthest_frame=far, cycles=rt[far], x_trunk_stages=xs.get(far),
                                     column_slot_stages=fr[far]['last_slot'] + 1, root_stages=fr[far].get('ret_stages'),
                                     return_trunk_stages=rs.get(far), meso_crossings=2, crossing_cycles_each=mc, hop_fix=m.get('hop_fix'),
                                     q_bank_stages=fr[far].get('bank_stages', 0),
                                     column_relays_x=fr[far].get('relay_x', 0),
                                     column_relays_return=fr[far].get('relay_ret', 0),
                                     basis='per frame: x trunk stations to its tap + entry meso 2 + slot stations '
                                           '+ return-tree root stages + return trunk stations + hub meso 2 (the tree '
                                           'levels and the element pipeline excluded)'),
        bus_classes=dict(cls), chains=ch, scan_die_power=scan_die_power(), rev=REV,
        column_relays=m.get('col_relays', {}),
        hub_stations=m.get('hub_stations', {}),
        power_model={k: dict(w=round(v[0], 6), basis=v[1]) for k, v in POWER8.items()})


def write_glue(elem_h=None, pairs=None):
    """glue RTL for the union of the layer and head dies (one module per master name; names encode the signature)"""
    keep = (DIE_KIND, PAIRS, BF_PAIRS, NV_PAIRS)
    merged = dict(pdir={}, glue={})
    for die in ('layer', 'layer1', 'head'):
        configure(die, 'r8')
        if elem_h:
            slot_geometry(elem_h)
        if pairs and die in ('layer', 'layer1'):
            set_pairs(pairs)
        mm = build()
        finalize_r8(mm)
        for k_, v in mm['pdir'].items():
            if is_glue(k_):
                assert merged['pdir'].setdefault(k_, v) == v, k_
        merged['glue'].update(mm['glue'])
    configure(keep[0], 'r8')
    gp = ROOT / GLUE_RTL.replace('/r8/', f'/{out_rev()}/')
    gp.parent.mkdir(parents=True, exist_ok=True)
    gp.write_text(glue_rtl(merged))


def _stn_lanes(m, it):
    pd = m['pdir'][it.master]
    return [pd[p_][1] for p_ in sorted(pd, key=_pnum) if p_.startswith('di')]


def die_options(ap):
    """die-variant options shared by main and tools/die_top_lint.py (--s81-opts)"""
    ap.add_argument('--die', default='layer', choices=['layer', 'layer1', 'head'])
    ap.add_argument('--gen', default='r7', choices=['r7', 'r8'], help='r7: the 21fcf6469 die (default); r8: wired die')
    ap.add_argument('--head-dies', type=int, default=12, help='head die: dies sharing the head content (default 12)')
    ap.add_argument('--rev', default='r8', choices=['r8', 'r9'], help='r8 sub-revision (r9: S81-RERUN hub-bus stations)')
    ap.add_argument('--elem-h', type=float, help='r8: element frame height in its slot (default 157.68)')
    ap.add_argument('--pairs', type=int, help='r8: pairs (elements) per die (default: the decision value)')
    ap.add_argument('--bf-per-region', type=int, default=None,
                    help='r8 layer die: exactly N BF pairs in every region (0 = q-only flavour; bf-double 2026-10-07)')
    ap.add_argument('--field-margin', type=float, help='r8: min gap field <-> band (default 216 um)')
    ap.add_argument('--cc-reach-um', type=float, help='r9: common-clock hop cap (hub / end-block stations, column '
                    'relays); default the forwarded 430.56 um (MARGIN-FIRST variant: 215)')
    ap.add_argument('--vch-interleave', action='store_true', help='r9: strided VCH lane order (chains spread over '
                    'the whole VCH width; default off)')
    ap.add_argument('--corr-interleave', action='store_true', help='r9: strided HC-corridor lane order (chains spread '
                    'over the whole corridor height; default off)')
    ap.add_argument('--hop-fix', action='store_true', help='r9: a station on every die hop longer than its reach '
                    '(pin anchors of a first build; default off)')
    ap.add_argument('--fwd-pitch', type=float, help='r9: forwarded / every-hop station reach in um (OWNER v6: 300; '
                    'default the 430.56 um stage)')
    ap.add_argument('--cfifo-v2', action='store_true', help='r9: column FIFO v2 (pins registered, outputs from flops, '
                    '432 x 95 um; +2 cycles on the x path; default off)')
    ap.add_argument('--meso-d8', action='store_true', help='r9: meso FIFOs at DEPTH 8 (drift > 300 ps; default off)')
    ap.add_argument('--link-fix', action='store_true', help='r9: link-macro clock relay on the ck face and the final '
                    'tx / rx station at the centre of its pin span (default off)')
    ap.add_argument('--ch-heights', help='r9 (OWNER rule 3): comma list of the TIERS + 1 tier-channel heights in um '
                    '(default 259.2 each)')
    ap.add_argument('--vch-w', type=float, help='r9: VCH width in um (default 1209.6)')
    ap.add_argument('--hc-corr', type=float, help='r9: HC crossing corridor height in um (default 1209.6)')
    ap.add_argument('--pin-relay', action='store_true', help='r9: relay station abutting every hardened-block pin on '
                    'die interfaces (last segment <= 100 um; needs --hop-fix; default off)')
    ap.add_argument('--sel-xstg', action='store_true', help='r9: registered crossing stage on the end block -> '
                    'selector / collector buses (+1 cycle; default off)')
    ap.add_argument('--link-split', action='store_true', help='r9: SerDes tx / rx through two 256-b half-span '
                    'stations (port slices; needs --link-fix; default off)')
    ap.add_argument('--hc-xface', action='store_true', help='r9: hc_s <-> hc_n exchange straight across the corridor '
                    'inside the HC column, face to face (default off: a VCH-edge lane)')
    ap.add_argument('--geometry-fix', action='store_true', help='r9: canonical station footprints and bounded '
                    'k16 pin depth; default off pending geometry and physical gates')
    return ap


def apply_options(a):
    """configure the module globals for the die variant in `a` (die_options)"""
    set_cc_reach(a.cc_reach_um)
    global VCH_INTERLEAVE, LINK_FIX, HC_XFACE, GEOMETRY_FIX
    GEOMETRY_FIX = bool(getattr(a, 'geometry_fix', False))
    VCH_INTERLEAVE = bool(a.vch_interleave)
    HC_XFACE = bool(getattr(a, 'hc_xface', False))
    global LINK_SPLIT, SEL_XSTG
    SEL_XSTG = bool(getattr(a, 'sel_xstg', False))
    global PIN_RELAY, CHS, VCH8, HC_CORR, SPINE_W8
    PIN_RELAY = bool(getattr(a, 'pin_relay', False))
    CHS = [float(v) for v in a.ch_heights.split(',')] if getattr(a, 'ch_heights', None) else None
    VCH8 = float(a.vch_w) if getattr(a, 'vch_w', None) else 1209.6
    HC_CORR = float(a.hc_corr) if getattr(a, 'hc_corr', None) else 1209.6
    SPINE_W8 = SPINE_W + VCH8 - VCH
    LINK_SPLIT = bool(getattr(a, 'link_split', False)) and bool(a.link_fix)
    LINK_FIX = bool(a.link_fix)
    global CORR_INTERLEAVE, HOP_FIX, HOP_PLAN, MESO_D8
    CORR_INTERLEAVE = bool(a.corr_interleave)
    HOP_FIX, HOP_PLAN, MESO_D8 = bool(a.hop_fix), None, bool(a.meso_d8)
    global FWD_REACH, HOP_R_FWD, HOP_R_CC, CFIFO_V2, CF_WH
    CFIFO_V2 = bool(a.cfifo_v2)
    CF_WH = CF_WH_V2 if CFIFO_V2 else (850.176, 47.52)
    FWD_REACH = float(a.fwd_pitch) if a.fwd_pitch else LINK_STAGE_UM
    HOP_R_FWD, HOP_R_CC = LINK_STAGE_UM, 410.0
    if a.fwd_pitch:            # every hop on the die at or under the pitch
        HOP_R_FWD = HOP_R_CC = float(a.fwd_pitch)
    global REV, HEAD_DIES
    REV, HEAD_DIES = a.rev, a.head_dies
    configure(a.die, a.gen)
    if a.gen == 'r8':
        if a.elem_h or a.field_margin is not None:
            slot_geometry(a.elem_h, a.field_margin)
        if getattr(a, 'bf_per_region', None) is not None:
            global BF_PER_REGION
            BF_PER_REGION = a.bf_per_region
            set_pairs(a.pairs or PAIRS)
        elif a.pairs:
            set_pairs(a.pairs)


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
    die_options(ap)
    a = ap.parse_args(argv)
    apply_options(a)
    m = build()
    if a.gen == 'r8':
        finalize_r8(m)
    cov = dict(COV)
    for kv in filter(None, a.cov.split(',')):
        k_, v = kv.split('=')
        cov[k_] = float(v)
    if a.mode == 'check' and a.gen == 'r8':
        print(json.dumps(legality(m), indent=1))
        pc = pin_clashes(m)
        pc16 = pin_clashes(m, 16, 0.024 * 16 - 1e-6)
        write_lefs(m, 16, '/dev/null')
        print(json.dumps(dict(generated_pin_clashes=len(pc), examples=pc[:10], k16_clashes=len(pc16), k16_examples=pc16[:5])))
        rec = plan_record_r8(m)
        print(json.dumps({k_: rec[k_] for k_ in ('slot', 'instances', 'placed_footprint_mm2', 'utilisation', 'forwarded',
                                                  'field_round_trip_cycles')}, indent=1))
        return 0
    if a.mode == 'check':
        print(json.dumps(legality(m), indent=1))
        pc = pin_clashes(m)
        pc16 = pin_clashes(m, 16, 0.024 * 16 - 1e-6)
        print(json.dumps(dict(generated_pin_clashes=len(pc), examples=pc[:10], k16_clashes=len(pc16), k16_examples=pc16[:10])))
        print(json.dumps(trunk_stages(m), indent=1))
        return 0
    if a.mode == 'plan' and a.gen == 'r8':
        out = ROOT / OUT / out_rev() / dict(layer='', layer1='layer1_die', head='head_die')[a.die]
        out.mkdir(parents=True, exist_ok=True)
        rec = plan_record_r8(m)
        rec['legality_python'] = legality(m)
        rec['generated_pin_clashes'] = len(pin_clashes(m))
        rec['windows_um'] = windows(m)
        rec['child_reservations'] = m.get('child_reservations', {})
        (out / 'floorplan.json').write_text(json.dumps(rec, indent=1, default=str) + '\n')
        svg(m, out / 'floorplan.svg')
        write_def_floorplan(m, out / 'floorplan.def')
        if a.die == 'layer':
            write_glue(a.elem_h, a.pairs)
        print(json.dumps({k_: rec[k_] for k_ in ('slot', 'instances', 'placed_footprint_mm2', 'legality_python',
                                                  'generated_pin_clashes', 'forwarded', 'field_round_trip_cycles')},
                         indent=1, default=str))
        return 0
    if a.mode == 'plan':
        out = ROOT / OUT / {'layer': '', 'layer1': 'layer1_die'}.get(a.die, 'head_die')   # layer1 no longer overwrites head
        out.mkdir(parents=True, exist_ok=True)
        rec = plan_record(m)
        rec['legality_python'] = legality(m)
        rec['windows_um'] = windows(m)
        rec['child_reservations'] = m.get('child_reservations', {})
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
                    v_ = man.get('variant', {})
                    configure(v_.get('die', 'layer'), v_.get('gen', 'r7'))
                    if v_.get('gen') == 'r8':
                        REV = v_.get('rev', 'r8')
                        set_cc_reach(v_.get('cc_reach_um'))
                        VCH_INTERLEAVE = bool(v_.get('vch_interleave'))
                        HEAD_DIES = v_.get('head_dies', 12)
                        configure(v_.get('die', 'layer'), v_.get('gen', 'r7'))
                        slot_geometry(v_.get('elem_frame_h'))
                        set_pairs(v_['pairs'])
                    m = build()
                    if man.get('variant', {}).get('gen') == 'r8':
                        finalize_r8(m)
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
