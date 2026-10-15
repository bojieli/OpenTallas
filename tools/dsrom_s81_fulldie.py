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
from contextlib import contextmanager
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
    global PAIRS, BF_PAIRS, NV_PAIRS, DIE_KIND, GEN, CFG_LEF, HEAD_BUNDLES, HOP_PLAN, BF_EXPLICIT_IDS, CANONICAL_LAYOUT
    BF_EXPLICIT_IDS = None
    CANONICAL_LAYOUT = None
    DIE_KIND, GEN = die, gen
    HOP_PLAN = None                  # --hop-fix plans are per die
    # r8 uses the mirror-legal v2 cfg ROM view (ROM inventory note 2); r7 keeps the v1 view it was run with
    CFG_LEF = CFG_LEF_V2 if gen == 'r8' else CFG_LEF_V1
    REAL_FILES.clear()
    HEAD_BUNDLES = 0
    if die in LAYER_KINDS:
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
BF_EXPLICIT_IDS = None
CANONICAL_LAYOUT = None               # immutable full2417 root-keyed irregular field candidate


def parse_bf_pair_ranges(text, pairs):
    """Explicit BF-double field IDs; comma-separated half-open ranges."""
    ids = set()
    for item in text.split(','):
        ends = item.split(':')
        if len(ends) != 2:
            raise ValueError('BF ranges require start:stop')
        lo, hi = map(int, ends)
        if not 0 <= lo < hi <= pairs:
            raise ValueError(f'BF range {item} outside [0,{pairs})')
        current = set(range(lo, hi))
        if ids & current:
            raise ValueError(f'overlapping BF range {item}')
        ids.update(current)
    return frozenset(ids)


def set_pairs(n):
    """r8: pairs (elements) per die; BF / NV shares scaled as the decision's"""
    global PAIRS, BF_PAIRS, NV_PAIRS
    if BF_EXPLICIT_IDS is not None:
        assert n > max(BF_EXPLICIT_IDS, default=-1), 'explicit BF IDs exceed pair count'
        PAIRS, BF_PAIRS = n, len(BF_EXPLICIT_IDS)
    elif DIE_KIND in LAYER_KINDS and BF_PER_REGION is not None:
        PAIRS, BF_PAIRS = n, BF_PER_REGION * ROOTS
    elif DIE_KIND in LAYER_KINDS:
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


def _real_pin_dirs(master):
    """{pin: INPUT | OUTPUT | INOUT} of a real LEF macro by its master name ({} for a generated master)"""
    for rec in _REAL.values():
        if rec['name'] == master:
            if 'dirs' not in rec:
                rec['dirs'] = {pm.group(1): (re.search(r'DIRECTION (\w+)', pm.group(2)) or [None, None])[1]
                               for pm in re.finditer(r'\n  PIN (\S+)\n(.*?)\n  END \1', rec['text'], re.S)}
            return rec['dirs']
    return {}


def q_pq():
    """True when the q abstract carries the PQ pins (go_tag / bank_free / sh_free / walking): ot_v41_rom_elem_q_qxpq_w10"""
    return 'go_tag[0]' in real_lef(Q_LEF)['pins']


# Real-macro pins that are left without a die net BY DESIGN (build-every-path rule, s81-die-2 2026-10-08: every other
# functional pin of a real macro must have a net, see unbound_functional_pins).  pin name -> reason.
DIAG_PINS = {
    'walking': 'PQ q element diagnostic: no consumer in the PQ design (ot_v41_pair_pq_w17w10 leaves e_walking open; '
               'the PQ spine admits ops by its GAP / GUARD timing, the loader by bank_free / sh_free)',
}


def unbound_functional_pins(m):
    """{(master, pin): instances} of real-macro signal pins (LEF) with no die net, excluding DIAG_PINS,
    UNUSED_BY_DESIGN and the cfg ROM's spare rd_out[71:48].  The generator fails on any (build-every-path rule)."""
    rp = real_ports()
    lefs = {}
    for rel in (Q_LEF, CFG_LEF, PHY_LEF, SERDES_LEF, UCIE_LEF) + ((HEAD_A_LEF, HEAD_B_LEF) if HEAD_BUNDLES else ()):
        r_ = real_lef(rel)
        lefs[r_['name']] = r_['pins']
    by = {it.name: it for it in m['insts']}
    bound = defaultdict(set)
    for bid, cls, bits, eps in m['buses']:
        for inst, port in eps:
            if inst == 'TOP' or inst not in by:
                continue
            mst = by[inst].master
            if mst not in rp:
                continue
            base, lo, hi = pslice(port)
            if base in rp[mst]:
                bound[inst].update(rp[mst][base][:bits] if lo is None else rp[mst][base][lo:hi + 1])
    out = defaultdict(int)
    for it in m['insts']:
        pins = lefs.get(it.master)
        if pins is None:
            continue
        got = bound.get(it.name, set())
        for pn in pins:
            b_ = re.sub(r'\[\d+\]$', '', pn)
            if pn in got or b_ in DIAG_PINS or (it.master, b_) in UNUSED_BY_DESIGN:
                continue
            if b_ == 'rd_out' and int(pn[pn.index('[') + 1:-1]) >= 48:
                continue                    # cfg ROM spare columns (48-b payload)
            out[(it.master, b_)] += 1
    return dict(out)


def q_x1_south():
    """True when the q abstract has xs_q1 / xs_e1 on its S face (QELEM Z22+): the slot's own station drives them"""
    rq = real_lef(Q_LEF)
    ys = [rq['pins'][p_][1][1] for p_ in rq['pins'] if p_.startswith(('xs_q1[', 'xs_e1['))]
    return bool(ys) and max(ys) < rq['h'] / 2


def _bus(base, n):
    return [f'{base}[{i}]' for i in range(n)]


_PSL = re.compile(r'^(.+)\[(\d+)(?::(\d+))?\]$')
_PSRC = re.compile(r'^(.+)@(\d+)$')


def _is_bf_front(it):
    return it is not None and it.master.startswith('dsfd_bf_front')


def psrc(port):
    """S-BIND 2026-10-15: a LOAD endpoint 'p[lo:hi]@k' reads only net bits k .. k + hi - lo of a wider net (e.g. the BF
    front's xb[536:801] = bits 0..265 of the 283-b x0 lane net).  Returns (port spec without the suffix, k or None)."""
    mm = _PSRC.match(port)
    return (mm.group(1), int(mm.group(2))) if mm else (port, None)


def pslice(port):
    """bus endpoint port spec: 'p' (the whole port) or 'p[lo:hi]' (bits lo..hi of port p, ascending; S81-RERUN
    2026-10-07 port slicing: one port served by several nets, e.g. a 512-b link tx by two 256-b final stations).
    Returns (base, lo, hi) with lo = hi = None for a whole port."""
    port = psrc(port)[0]
    mm = _PSL.match(port)
    return (mm.group(1), int(mm.group(2)), int(mm.group(3) or mm.group(2))) if mm else (port, None, None)


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


# ------------------------------------------------------------------------------------------------ by-name view binding
# S81 DIE 2026-10-13: a die master is bound to its REAL routed view (LEF + TT/FF/SS ETM of one export) BY MASTER NAME,
# from a table built by tools/s81/view_binding.py out of results/arch/s81_native_20261013/qualification.json: only a
# master that tools/s81/native_view_qualify.py calls QUALIFIED (and whose export replayed the verdict SDC sequence,
# main abc334b14) is in the table.  Every other generated master stays a placeholder (binding_ledger.json says why).
# --view-binding / OT_S81_VIEW_BINDING: table path (repo-relative or absolute); 'none' binds nothing.
VIEW_BINDING_DEFAULT = 'results/arch/s81_native_20261013/view_binding.json'
VIEW_BINDING = os.environ.get('OT_S81_VIEW_BINDING', VIEW_BINDING_DEFAULT)
VIEW_BINDING_SCHEMA = 's81-view-binding-v1'
_BOUND = {}


def _view_path(rel, root=None):
    return Path(rel) if Path(rel).is_absolute() else Path(root or ROOT) / rel


def bound_views(root=None):
    """{master: dict(lef, tt, ff, ss (paths as in the table), w, h, pins {name: direction}, text, job, export_dir)} of
    the view-binding table.  Hard errors: unknown schema, an entry that is not QUALIFIED, a missing file, a file whose
    sha256 differs from the table (the view changed after it was qualified), a LEF whose MACRO is not the master, a
    corner liberty without that cell."""
    key = (VIEW_BINDING, str(root or ROOT))
    if key in _BOUND:
        return _BOUND[key]
    out = {}
    if VIEW_BINDING and VIEW_BINDING != 'none':
        tp = _view_path(VIEW_BINDING, root)
        if not tp.exists():
            raise SystemExit(f'VIEW_BINDING: table {tp} not found (--view-binding none binds nothing)')
        tab = json.loads(tp.read_text())
        if tab.get('schema') != VIEW_BINDING_SCHEMA:
            raise SystemExit(f'VIEW_BINDING: {tp} schema {tab.get("schema")!r}, expected {VIEW_BINDING_SCHEMA!r}')
        for mst, rec in sorted(tab.get('bound', {}).items()):
            if rec.get('verdict') != 'QUALIFIED':
                raise SystemExit(f'VIEW_BINDING: {mst} is in the table without a QUALIFIED verdict ({rec.get("verdict")!r})')
            r_ = dict(job=rec.get('job'), export_dir=rec.get('export_dir'))
            for k_ in ('lef', 'tt', 'ff', 'ss'):
                f_ = rec.get('files', {}).get(k_) or {}
                fp = _view_path(f_.get('path', ''), root)
                if not f_.get('path') or not fp.is_file():
                    raise SystemExit(f'VIEW_BINDING: {mst} {k_} view file missing: {f_.get("path")!r}')
                raw = fp.read_bytes()
                if hashlib.sha256(raw).hexdigest() != f_.get('sha256'):
                    raise SystemExit(f'VIEW_BINDING: {mst} {k_} {f_["path"]} sha256 differs from the table: the view '
                                     'changed after it was qualified (re-run tools/s81/view_binding.py)')
                r_[k_] = f_['path']
                if k_ == 'lef':
                    r_['text'] = raw.decode()
                elif not re.search(r'^\s*cell\s*\(\s*"?' + re.escape(mst) + r'"?\s*\)', raw.decode(errors='ignore'), re.M):
                    raise SystemExit(f'VIEW_BINDING: {mst} {k_} liberty {f_["path"]} has no cell {mst}')
            macros = re.findall(r'^MACRO (\S+)', r_['text'], re.M)
            if macros != [mst]:
                raise SystemExit(f'VIEW_BINDING: {mst} LEF {r_["lef"]} defines MACRO {macros}, expected exactly [{mst}]')
            sm = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', r_['text'])
            r_['w'], r_['h'] = float(sm.group(1)), float(sm.group(2))
            pins = {}
            for pm in re.finditer(r'\n\s*PIN (\S+)\s*\n(.*?)\n\s*END \1', r_['text'], re.S):
                if re.search(r'USE\s+(POWER|GROUND)', pm.group(2)):
                    continue
                dm = re.search(r'DIRECTION\s+(\w+)', pm.group(2))
                pins[pm.group(1)] = dm.group(1).upper() if dm else None
            r_['pins'] = pins
            out[mst] = r_
    _BOUND[key] = out
    return out


def bound_view_pin_faults(mst, view, ports):
    """Faults of a bound view's LEF signal pins against the die netlist's ports of that master (ports: {port: (dir,
    bits)}, finalize_r8's pdir).  A die port of n bits is the LEF pins port[0..n-1] (a 1-bit port: port[0] or port);
    every die port bit must have its pin with the same direction and the LEF must carry no other signal pin."""
    faults, seen = [], set()
    for p_, (d_, n_) in sorted(ports.items()):
        names = [f'{p_}[{i}]' for i in range(n_)]
        if n_ == 1 and names[0] not in view['pins'] and p_ in view['pins']:
            names = [p_]
        miss = [x for x in names if x not in view['pins']]
        if miss:
            faults.append(f'die port {p_}[{n_}] ({d_}): {len(miss)} LEF pin(s) missing, e.g. {miss[0]}')
        for x in names:
            seen.add(x)
            ld = view['pins'].get(x)
            if ld in ('INPUT', 'OUTPUT') and ld.lower() != d_:
                faults.append(f'pin {x}: LEF DIRECTION {ld}, die netlist {d_}')
                break
    extra = sorted(set(view['pins']) - seen)
    if extra:
        faults.append(f'{len(extra)} LEF signal pin(s) with no die port, e.g. {extra[:3]}')
    return faults


def apply_view_binding(m, pdir):
    """Bind the table's masters present on this die (end of finalize_r8, before any LEF / DEF / netlist is written):
    hard error on a pin-name mismatch with the die netlist, on a non-R0 instance and on a real outline larger than the
    generated slot (the placer chose that slot from the GENERATED outline; it does not re-place).  A fitting instance
    keeps the slot origin and takes the real LEF SIZE.  m['bound_views'] records what was bound."""
    if 'bound_views' in m:
        return m['bound_views']
    bv = bound_views()
    rec = {}
    for it in m['insts'] if bv else ():
        v = bv.get(it.master)
        if v is None:
            continue
        if it.master in REAL_FILES:
            raise SystemExit(f'VIEW_BINDING: {it.master} is a constant-bound hard macro (REAL_FILES), not a table master')
        r_ = rec.get(it.master)
        if r_ is None:
            faults = bound_view_pin_faults(it.master, v, pdir.get(it.master, {}))
            if faults:
                raise SystemExit(f'VIEW_BINDING: {it.master} LEF {v["lef"]} does not match the die netlist ports: '
                                 + '; '.join(faults[:8]))
            r_ = rec[it.master] = dict(lef=v['lef'], libs={c: v[c] for c in ('tt', 'ff', 'ss')}, size_um=[v['w'], v['h']],
                                       generated_slot_um=[round(it.w, 3), round(it.h, 3)], instances=0)
        if it.orient != 'R0':
            raise SystemExit(f'VIEW_BINDING: {it.master} instance {it.name} is {it.orient}: bound views are placed R0 only')
        if v['w'] > it.w + 1e-6 or v['h'] > it.h + 1e-6:
            raise SystemExit(f'VIEW_BINDING: {it.master} real outline {v["w"]} x {v["h"]} exceeds the generated slot '
                             f'{it.w:.3f} x {it.h:.3f} of {it.name}: the placer sizes slots from the generated outline '
                             '(results/arch/s81_native_20261013/BINDING.md, placer assumptions)')
        it.w, it.h = v['w'], v['h']
        r_['instances'] += 1
    m['bound_views'] = rec
    if rec:
        print('OT_VIEW_BINDING %d masters / %d instances bound from %s' % (len(rec), sum(r_['instances'] for r_ in rec.values()),
              VIEW_BINDING), file=sys.stderr)
    return rec


# ------------------------------------------------------------------------------------------------ field map
def region_bounds():
    return [math.floor(r * PAIRS / ROOTS) for r in range(ROOTS + 1)]


def bf_sites():
    if BF_EXPLICIT_IDS is not None:
        assert len(BF_EXPLICIT_IDS) == BF_PAIRS
        assert not (set(BF_EXPLICIT_IDS) & nv_sites())
        return set(BF_EXPLICIT_IDS)
    if BF_PER_REGION is not None and DIE_KIND in LAYER_KINDS:
        # the RTL's flat is_bf map (bf-double): floor(i * PAIRS / NBF), NBF = N x ROOTS; N per region asserted
        nb = BF_PER_REGION * ROOTS
        s = {i * PAIRS // nb for i in range(nb)}
        bd = region_bounds()
        assert len(s) == BF_PAIRS == nb and all(sum(1 for x in s if bd[r] <= x < bd[r + 1]) == BF_PER_REGION
                                                for r in range(ROOTS))
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
    if PQ_PLACE:          # S81-DIE: the PQ core slot right after the VM (VM read by its N face -> core S face)
        centre.insert(centre.index('vm') + 1, 'pq')
        centre_area['pq'] = PQ_CORE_H * cw / 1e6
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
    for port, spec in mst.ports.items():
        if spec[0] == 'rects':
            if k != 1 or wmap.get(port, len(spec[1])) != len(spec[1]):
                raise ValueError(f'exact physical pin rectangles require full width k=1: {mst.name}/{port}')
            out.extend(spec[1])
    xy = {p: s for p, s in mst.ports.items() if s[0] == 'xy'}
    for port, spec in xy.items():
        n = wmap.get(port, len(spec[1]))
        for i, x in enumerate(spec[1][:n]):
            out.append((f'{port}[{i}]', 'M5', (x - 0.012, 0.0, x + 0.012, 0.192)))
    for port, spec in mst.ports.items():      # HBM r18: interior area pin (one bit), e.g. a block-centre ck on M7
        if spec[0] == 'area':
            _, layer, cx, cy, w_, h_ = spec
            out.append((f'{port}[0]', layer, (cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2)))
    rest = Q.Master(mst.name, mst.w, mst.h, mst.obs_top, mst.note)
    rest.ports = {p: s for p, s in mst.ports.items() if s[0] not in ('xy', 'area', 'rects')}
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
    if FACE_PIN_INSET:
        # --face-pin-inset (die-gaps 2026-10-08): face pins start FACE_PIN_INSET inside the outline.  Abutted masters
        # (field node stacks: 0.024 um SHAVE gap) put a lower N-face pin and an upper S-face pin of DIFFERENT nets on
        # one M5 track tip to tip 0.024 um apart, under the ASAP7 M5 LEF58_EOLKEEPOUT 0.025: m221pq_r3 region DRT kept
        # 1,275 fixed-shape EolKeepOut violations (bfcol 1,119 / pqstrip 156) that no iteration can repair.  Inset
        # only where the pin layer lies above the master's OBS (the router reaches the pin over the macro).
        ins = []
        for nm, ly, (x0, y0, x1, y1) in rects:
            spec = rest.ports.get(nm.rsplit('[', 1)[0])
            if spec and spec[0] == 'face' and int(ly[1:]) > mst.obs_top:
                d_ = FACE_PIN_INSET
                x0, x1, y0, y1 = {'W': (x0 + d_, x1 + d_, y0, y1), 'E': (x0 - d_, x1 - d_, y0, y1),
                                  'S': (x0, x1, y0 + d_, y1 + d_), 'N': (x0, x1, y0 - d_, y1 - d_)}[spec[2]]
            ins.append((nm, ly, (x0, y0, x1, y1)))
        rects = ins
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
        if k == 1 and (name in REAL_FILES or name in m.get('bound_views', ())):
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
        if k == 1 and (name in REAL_FILES or name in m.get('bound_views', ())):
            continue             # real LEF: constant-bound hard macro, or a bound view (case_real: bound_views.lef)
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
    spare_out = {}
    if k == 1:
        _cfg = real_lef(CFG_LEF)
        spare_out[(_cfg['name'], 'rd_out')] = sum(1 for p_ in _cfg['pins'] if p_.startswith('rd_out['))
    by = {it.name: it for it in m['insts']}
    conns = defaultdict(list)
    tops = [b for b in m['buses'] if b[1] == 'top_in']        # r8: die top input ports (refclk, por_n)
    touts = [b for b in m['buses'] if b[1] == 'top_out']      # --rtl-bind: link pads out
    V = [f'// tools/dsrom_s81_fulldie.py: die-level nets only (k = {k})',
         f'module {top} (' + ', '.join(b[0] for b in tops + touts) + ');']
    V += [f'  input {b[0]};' if b[2] == 1 else f'  input [{b[2] - 1}:0] {b[0]};' for b in tops]
    V += [f'  output {b[0]};' if b[2] == 1 else f'  output [{b[2] - 1}:0] {b[0]};' for b in touts]
    for bid, cls, bits, eps in m['buses']:
        if cls in skip:
            continue
        n = bits if k == 1 else max(1, math.ceil(bits / k))
        net = bid if cls in ('top_in', 'top_out') else f'n_{bid}'
        if cls not in ('top_in', 'top_out'):
            V.append(f'  wire [{n - 1}:0] {net};')
        for inst, port in eps:
            if inst == 'TOP':
                continue
            mst = by[inst].master
            off_ = psrc(port)[1]
            base, lo, hi = pslice(port)
            if off_ is not None:          # a load reading net bits off_ .. off_ + (hi - lo) (psrc)
                assert lo is not None and not (mst in rp and base in rp[mst]), (inst, port)
                conns[inst].append((base, f'{net}[{off_ + hi - lo}:{off_}]', hi - lo + 1, lo if k == 1 else lo // k))
                continue
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
            assert all(pcs[i][0] + pcs[i][2] <= pcs[i + 1][0] for i in range(len(pcs) - 1)), (it.name, base, pcs)
            if any(pcs[i][0] + pcs[i][2] < pcs[i + 1][0] for i in range(len(pcs) - 1)) or pcs[0][0] != 0:
                # S-BIND 2026-10-15: a port bound by disjoint slices (e.g. --pq-cnt taps PQ t_cnt[455:452] only): each gap
                # gets its own net with no other endpoint, so the connection keeps its order and the die port-bind check
                # sees the gap (an input gap = an UNDRIVEN net, an output gap = an unread net); never a constant
                full_, lo_ = [], 0
                for (o_, net_, n_) in pcs:
                    if o_ > lo_:
                        gn_ = f'n_gap_{it.name}_{base}_{lo_}'
                        V.append(f'  wire [{o_ - lo_ - 1}:0] {gn_};')
                        full_.append((lo_, gn_, o_ - lo_))
                    full_.append((o_, net_, n_)); lo_ = o_ + n_
                pcs = full_
            parts.append(f'.{base}({{' + ', '.join(net for _, net, _ in reversed(pcs)) + '})')
        for base, bits_ in bus_bits.items():
            hi = max(bits_)
            full = spare_out.get((it.master, base))
            if full and full > hi + 1:
                # r5 2026-10-14: a real macro's spare OUTPUT columns (cfg ROM rd_out[71:48]) get their own no-load nets so
                # the connection is the port's full width (OpenSTA 'port rd_out size 72 does not match net size 48',
                # die_port_bind width check); never used for inputs (an unconnected functional input stays an error)
                nc = f'n_nc_{it.name}_{base}'
                V.append(f'  wire [{full - 1}:{hi + 1}] {nc};')
                for j in range(hi + 1, full):
                    bits_[j] = f'{nc}[{j}]'
                hi = full - 1
            cat = ', '.join(bits_.get(j, "1'bz") for j in range(hi, -1, -1))
            parts.append(f'.{Q.esc(base)}({{{cat}}})')
        V.append(f'  {it.master} {it.name} (' + ', '.join(parts) + ');')
    V.append('endmodule\n')
    Path(path).write_text('\n'.join(V))
    if k == 1:
        # s81-die-rtl-bind 2026-10-14: the structural netlist names each hardened master by its base module (OpenSTA reads
        # no #(...) overrides), so the elaboration parameters every master is built with go to a sidecar the RTL binders
        # read (tools/die_port_bind.py --params, tools/die_top_lint.py): {master: {param: value}}.
        Path(str(path) + '.params.json').write_text(json.dumps(dict(
            schema='opentallas.die_params.v1', netlist=Path(path).name, masters=die_master_params(m)), indent=1, sort_keys=True) + '\n')


# s81-die-rtl-bind 2026-10-14: elaboration parameters of the die's hardened masters (the die instantiates each master as
# hardened; the netlist names the base module).  Bound views: the parameters of the CLOSED route (its launch receipt);
# die-shaped masters: the die's own counts (stacks of this die kind).
BOUND_VIEW_RECEIPTS = {
    # q element view physical/s81_die_views/q_elem_qs5f_efs (route dsrom-qelem-qs5f-efs-7fb23b7ff-tc-hm10-cl)
    'ot_v41_rom_elem_q_qxpq_w10': 'results/rtl/dsrom_qelem_pq_20261006/closed_qs5f/receipt.json',
}


def _receipt_params(rel):
    d = json.loads((ROOT / rel).read_text())
    a = d.get('driver_args') or []
    out = {}
    for i, x in enumerate(a):
        if i and a[i - 1] == '--param':
            k_, v_ = x.split('=', 1)
            out[k_] = int(v_) if re.fullmatch(r'-?\d+', v_) else v_
    return out


def die_master_params(m):
    used = {it.master for it in m['insts']}
    out = {}
    for mst, rel in BOUND_VIEW_RECEIPTS.items():
        if mst in used:
            out[mst] = dict(_receipt_params(rel), _source=rel)
    sj = m.get('ctrl_svc_join')
    if sj and CTRL_SVC_JOIN in used:
        out[CTRL_SVC_JOIN] = dict(NS=sj['ns'], _source='die stacks %s' % ','.join(sj['stacks']))
    ch = m.get('ctrl_host')
    if ch and ch.get('master') in used:
        out[ch['master']] = dict(NS=ch['ns'], _source='die stacks %s' % ','.join(ch['stacks']))
    if 'dsfd_sp_hc_c' in used and 'dsfd_sp_hc_t' in used:
        # S-BIND 2026-10-15: with the chain tails in their own die master the head is the production hierarchical slab
        # split at the TAIL_SPLIT 1 seam (t_tf / f_tr); the default TAIL_SPLIT 0 builds the whole chain inside the head and
        # drives t_tf 0, leaving dsfd_sp_hc_t dead hardware
        out['dsfd_sp_hc_c'] = dict(HIER=1, HALF=1, CSPLIT=1, TAIL_SPLIT=1,
                                   _source='hc_t in the die: production hierarchical HC split at the TAIL_SPLIT 1 seam')
    if 'ot_s81_cfg7_seq' in used and q_pq():
        # TA-10: the PQ q element's loader handshake (ef / go_tag) is the PQ 1 loader (tb_ot_s81_cfg7_seq.sv PQ 1)
        out['ot_s81_cfg7_seq'] = dict(PQ=1, _source='q element %s carries go_tag / sh_free / bank_free' % real_lef(Q_LEF)['name'])
    return out


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


# r5 2026-10-14 (IR release gate): the hardened BF pair (--bf-hier: dsfd_bf_col | dsfd_bf_front | dsfd_bf_col MY) draws
# its current where its cells are.  c8p put the whole ASSUMED 2 x q (0.507 W) on the 100.224 x 198.72 front (25.4 W/mm2,
# 178.7 / 193.9 mV field IR) and 0 W on both columns.  MEASURED routed report_power (BC = FF libraries, the higher corner,
# 833.3 ps clock) of the CLOSED views bound by name: ot_v41_bf_col 0.337 W (bfh_compact199_col_kreg_a1200_05a8d46ee-cl
# 6_finish.rpt), ot_s81_bf_front 0.0709 W (el1013-bf-front-align-f003d825f-cl 6_finish.rpt) -> 0.745 W per BF pair (> the
# 0.507 W assumption, kept as the upper of the two), uniform over each block's own outline.
BF_COL_W = (0.337, 'MEASURED routed ot_v41_bf_col report_power BC (bfh_compact199_col_kreg_a1200_05a8d46ee-cl)')
BF_FRONT_W_PWR = (0.0709, 'MEASURED routed ot_s81_bf_front report_power BC (el1013-bf-front-align-f003d825f-cl)')


def inst_power(it):
    if it.kind == 'bfcol':
        return BF_COL_W[0]
    if it.kind == 'bf' and it.master == 'dsfd_bf_front':
        return BF_FRONT_W_PWR[0]
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


# FP-LINT (owner 2026-10-08): die relay margin.  Every driver -> relay ... -> load chain (forwarded stations, column
# relays, hub stations, pin relays) is checked against the SS wire reach (504 um at 1.2 GHz) and for a relay on the far
# side of its driver (r3 hop relays g_rt_*_8a_y1: 776-906 um backwards, 860 ps of GRT wire).  `check` exits 3 on a FAIL.
MARGIN_RELAY_KINDS = ('stn', 'sstn', 'rly', 'hstn', 'rstg', 'pqstn')
SS_REACH_UM = 504.0
TT_REACH_UM = 674.0             # TT wire fit 261 ps + 0.76 ps/um within 833.333 - 60 ps (reported, option B)


def _lint_pin_pt(m):
    """--pin-need lint / placement pin model: (inst, port or 'port[lo:hi]') -> die (x, y) of the centroid of those pins of
    a REAL (hardened LEF) macro -- link macros (250 x 2,250 um), q elements, PHYs -- mirrored with the instance
    orientation.  Generated glue / slab masters get their pin faces from these same nets at finalize (after placement),
    so they keep the instance centre (None) -- except a hop endpoint that --hop-fix's pass 1 anchored (HOP_PLAN: the
    pin anchor a generated slab's pin relay is placed against), which takes that anchor."""
    _init_real()
    rp = real_ports_r8()
    by = {it.name: it for it in m['insts']}
    anc = {}
    for (di, dp, li, lp), (L_, a_, b_, *_r) in (HOP_PLAN or {}).items():
        anc.setdefault((li, lp), b_)
        anc.setdefault((di, dp), a_)

    def pt(inst, port):
        it = by.get(inst)
        if it is not None and it.master not in REAL_FILES and (inst, port) in anc:
            return tuple(anc[(inst, port)])
        if it is None or it.master not in REAL_FILES:
            return None
        r = real_lef(REAL_FILES[it.master])
        base, lo, hi = pslice(port)
        nms = [n for n in (rp.get(it.master, {}).get(base) or [])[(lo or 0):(None if hi is None else hi + 1)]
               if n in r['pins']]
        if not nms:
            return None
        x = sum((r['pins'][n][1][0] + r['pins'][n][1][2]) / 2 for n in nms) / len(nms)
        y = sum((r['pins'][n][1][1] + r['pins'][n][1][3]) / 2 for n in nms) / len(nms)
        if it.orient in ('MY', 'R180'):
            x = r['w'] - x
        if it.orient in ('MX', 'R180'):
            y = r['h'] - y
        return (it.x + x, it.y + y)
    return pt


def die_lef_texts(m):
    """the LEF texts of a die case without a work directory (check mode): generated abstracts + the real macros"""
    import tempfile
    _init_real()
    with tempfile.TemporaryDirectory() as td:
        write_lefs(m, 1, Path(td) / 'elements.lef')
        texts = [(Path(td) / 'elements.lef').read_text()]
    for rel in (Q_LEF, CFG_LEF, PHY_LEF, SERDES_LEF, UCIE_LEF) + ((HEAD_A_LEF, HEAD_B_LEF) if HEAD_BUNDLES else ()):
        try:
            texts.append(_lef_text(rel))
        except OSError:
            pass
    if m.get('bound_views'):
        bv_ = bound_views()
        texts.append('\n'.join(bv_[n_]['text'] for n_ in sorted(m['bound_views'])))
    return texts


def pin_align_gate(m, lef_texts, out=None, raise_on_fail=True):
    """tools/hier_contract/pin_align.py on the die's bundles; prints one OT_PIN_ALIGN line; returns the record.
    OT_PIN_ALIGN_GATE: fail (default) | warn | off."""
    hc = str(ROOT / 'tools' / 'hier_contract')
    if hc not in sys.path:
        sys.path.insert(0, hc)
    import pin_align as PA
    mode = PA.gate_mode()
    if mode == 'off':
        return None
    rp = real_ports()

    def names(it, port, bits):
        base, lo, _hi = pslice(port)
        lo = lo or 0
        t = rp.get(it.master, {}).get(base)
        return t[lo:lo + bits] if t is not None else [f'{base}[{lo + i}]' for i in range(bits)]
    rec = PA.analyze(m['insts'], m['buses'], lef_texts, names)
    if out is not None:
        Path(out).write_text(json.dumps(rec, indent=1) + '\n')
    print(PA.line(rec), file=sys.stderr)
    if rec['verdict'] == 'FAIL' and mode == 'fail' and raise_on_fail:
        raise SystemExit(f'pin align FAIL: {rec["by_verdict"].get("FAIL", 0)} bundles whose jog alone takes > '
                         f'{rec["cut_limit"]:g} of the channel' + (f' (see {out})' if out else '')
                         + '; OT_PIN_ALIGN_GATE=warn builds anyway')
    return rec


def margin_lint(m):
    import fp_margin_lint as FPL
    # s81-gen: per-segment walk (the per-chain walk ran > 5 h on the S81 layer1 die; same tests, same verdict)
    # s81-gen 2026-10-09: data buses only.  Clock trunks / resets / column clock trees fan out from sp_collective (the
    # PLL) to every station's ck: as 'segments' they gave 52,988 false 9-13 mm reach violations on the layer1 die.
    data = [b for b in m['buses'] if b[1] not in HOP_SKIP]
    edges = os.environ.get('OT_S81_MARGIN_CHAINS', '0') != '1'
    pp = _lint_pin_pt(m) if PIN_NEED else None      # --pin-need: far-side measured to the load's real pins
    out = FPL.die_margin(m['insts'], data, MARGIN_RELAY_KINDS, reach_um=SS_REACH_UM, edges=edges, pin_pt=pp)
    out['pin_need'] = bool(pp)
    # s81-gen 2026-10-10: the sign-off corner is TT (owner option B); the SS 504 um verdict above stays the gate, and the
    # TT reach (833.333 - 60 ps setup unc. = 261 ps + 0.76 ps/um x L -> 674 um) is reported beside it
    tt = FPL.die_margin(m['insts'], data, MARGIN_RELAY_KINDS, reach_um=TT_REACH_UM, edges=edges, limit=5, pin_pt=pp)
    out['tt'] = dict(reach_um=TT_REACH_UM, reach_violations=tt['reach_violations'], verdict_reach='PASS' if not tt['reach_violations'] else 'FAIL',
                     max_um=max((r['um'] for r in out['reach_examples']), default=0.0))
    return out


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
    """Place every scalar die pad, including vector PHY ports, on the W edge."""
    tops = [pin for bid, cls, bits, _ in m['buses'] if cls in ('top_in', 'top_out')
            for pin in ([bid] if bits == 1 else [f'{bid}[{b}]' for b in range(bits)])]
    if not tops:
        return ''
    pitch = min(4.32, dn((DIE[1] - 2.0) / max(1, len(tops) - 1), TRK['M4'][1]))
    assert pitch >= TRK['M4'][1], ('die pad track capacity', len(tops), DIE[1])
    span = pitch * (len(tops) - 1)
    assert span + 2.0 <= DIE[1], ('die pad capacity', len(tops), DIE[1])
    y0 = dn(min(m['hub']['collective'].y + m['hub']['collective'].h / 2, DIE[1] - span - 1.0), GY)
    return '\n'.join(f'place_pin -pin_name {{{p}}} -layer M4 -location {{0.5 {y0 + pitch * i:.3f}}} '
                     f'-pin_size {{{1.0 * k:.3f} {max(0.072, 0.024 * k):.3f}}} '
                     f'-force_to_die_boundary' for i, p in enumerate(tops))


# ------------------------------------------------------------------------------------------------ case (a): real
def bundle_bound_lefs(texts):
    """Keep every view's declarations and geometry, with one library terminator.

    OpenROAD stops at END LIBRARY. Concatenating complete exported libraries
    otherwise leaves every bound master after the first unread.
    """
    return '\n'.join(re.sub(r'(?m)^\s*END\s+LIBRARY\s*$', '', text).rstrip()
                     for text in texts) + '\nEND LIBRARY\n'


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
    bnd = m.get('bound_views') or {}
    if bnd:                      # the bound masters' real LEFs, verbatim (bound_views() verified their sha256)
        bv_ = bound_views()
        (work / 'bound_views.lef').write_text(bundle_bound_lefs(bv_[n_]['text'] for n_ in sorted(bnd)))
    write_netlist(m, 1, work / 'die.v')
    # pin ALIGNMENT of every die bundle (owner 2026-10-13, tools/hier_contract/pin_align.py): jog along the shared
    # direction, bit order, pin-to-pin length, from the LEFs written above.  FAIL = the jog alone takes > 0.60 of the
    # channel tracks between the two faces (OT_PIN_ALIGN_GATE=warn|off to build anyway)
    pin_align_gate(m, [(work / f).read_text() for f in ('elements.lef', 'q_elem.lef', 'cfg.lef', 'phy.lef', 'serdes.lef',
                                                         'ucie.lef', 'head_a.lef', 'head_b.lef', 'bound_views.lef')
                       if (work / f).exists()], work / 'pin_align.json')
    if HOP_GATE_UM:
        # s81-die v14 (2026-10-12): hard hop gate before PLACE / GRT (c3: -17.7 ns TT on 2.3 mm unbuffered hub hops;
        # c5: a 1,025 um svc_SW.rv -> ctrl_SW.rd hop) -- every data bit, pin to pin, from the LEFs written above
        sys.path.insert(0, str(ROOT / 'tools' / 's81'))
        import die_hop_gate as HG
        lefs = [(work / f).read_text() for f in ('elements.lef', 'q_elem.lef', 'cfg.lef', 'phy.lef', 'serdes.lef',
                                                 'ucie.lef', 'head_a.lef', 'head_b.lef') + (('bound_views.lef',) if bnd else ())
                if (work / f).exists()]
        # pinreg-pairs 2026-10-13: every hop is judged on ITS pair's real views (pair_check.Gate; the timing table is
        # results/arch/pinreg_audit_1013/pairs/view_timing.json or $OT_PAIR_TIMING); the flat --hop-gate UM stays the
        # limit of placeholder pairs and the ceiling of all.  OT_S81_PAIR_GATE=0 restores the flat rule.
        pair = None
        if os.environ.get('OT_S81_PAIR_GATE', '1') != '0':
            sys.path.insert(0, str(ROOT / 'tools' / 'hier_contract'))
            import pair_check as PC
            pair = PC.Gate(default_um=HOP_GATE_UM, buses=[(b_, c_, n_, [(e_[0], pslice(e_[1])[0]) for e_ in eps_]) for b_, c_, n_, eps_ in m['buses']])
        hg = HG.gate(m['insts'], m['buses'], lefs, pslice, limit_um=HOP_GATE_UM, ss_um=SS_REACH_UM, pair=pair)
        (work / 'hop_gate.json').write_text(json.dumps(hg, indent=1) + '\n')
        print('OT_HOP_GATE %s max %.1f um bits>%g: %d bits>%g(SS): %d' % (hg['verdict'], hg['max_um'], HOP_GATE_UM,
              hg['bits_over_limit'], SS_REACH_UM, hg['bits_over_ss']), file=sys.stderr)
        hf_ = (hg.get('pair_check') or {}).get('hold_fail') or []
        owed_ = [h_ for h_ in hf_ if h_['dst'].rsplit('.', 1)[0] not in (m.get('bound_views') or ())]
        if hg['verdict'] != 'PASS' and not hg['bits_over_limit'] and hf_ and len(owed_) == len(hf_):
            # s81-die v17: every forwarded hold race is on the CLOSED view of a capture master this die case does NOT bind
            # (it is a placeholder here; its capture-edge re-route is on the contract's owed list): a tile defect that
            # keeps the master unbound, not a property of this die plan.  A race on a BOUND view stops the generator.
            print('OT_HOP_HOLD_OWED %d pairs on unbound capture masters: %s' % (len(hf_), ', '.join(
                '%s %.1f' % (h_['dst'], h_['hold_ps']) for h_ in hf_)), file=sys.stderr)
        elif hg['verdict'] != 'PASS':
            raise SystemExit(f'hop gate FAIL: {hg["bits_over_limit"]} bits over {HOP_GATE_UM} um (see {work}/hop_gate.json)')
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
foreach f {{q_elem.lef cfg.lef phy.lef serdes.lef ucie.lef {'head_a.lef head_b.lef ' if HEAD_BUNDLES else ''}{'bound_views.lef ' if bnd else ''}elements.lef}} {{ read_lef /work/$f }}
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
    if bnd:
        man['bound_views'] = dict(table=VIEW_BINDING, masters=bnd)
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


def pg_pitch_grid(p):
    """M8/M9 PG stripe pitch on the manufacturing grid (0.001 um): pdngen snaps the pitch DOWN and the derived spacing
    (pitch/2 - width) UP to the grid and then requires pitch >= 2 x (width + spacing) -- an off-grid bump-aligned pitch
    (63.6396 / 7 = 9.0914) failed PDN-0175 (9.0910 < 9.0920).  Rounded UP to 0.002 um so pitch/2 - 0.48 is on grid
    (the stripe lattice drifts < 0.001 um per bump period from the bump pitch; the vsrc sites stay on the bumps)."""
    return round(math.ceil(round(p / 0.002, 6) - 1e-9) * 0.002, 3)


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
        return pg_pitch_grid(vp / n)
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


PG_M8_MASTERS = set()          # hbmdie-1011 (conservative-1011 a0bda978e): masters whose PG pins are M8 straps (tiled hfd_hc)


def _gen_pg_lef(mst):
    """Generated abstract with M7 PG stripes (0.288 um, 10.8 um pitch, as the routed q element) for the PSM window.
    PG_M8_MASTERS (incl. their window clips): horizontal M8 PG straps instead (0.48 um, 10.8 um pitch) and M1-M7 owned
    by the block; the die joins them with its M9 straps (via89 at every same-net crossing)."""
    if mst.name.split('_clip_')[0] in PG_M8_MASTERS:
        L = [f'MACRO {mst.name}', '  CLASS BLOCK ;', f'  FOREIGN {mst.name} 0 0 ;', f'  SIZE {mst.w:.3f} BY {mst.h:.3f} ;',
             '  SYMMETRY X Y ;']
        for net, off in (('VDD', 1.0), ('VSS', 6.4)):
            L += [f'  PIN {net}', '    DIRECTION INOUT ;', f'    USE {"POWER" if net == "VDD" else "GROUND"} ;', '    PORT',
                  '      LAYER M8 ;']
            y = off
            while y + 0.48 < mst.h - 0.2:
                L.append(f'        RECT 0.300 {y:.3f} {mst.w - 0.3:.3f} {y + 0.48:.3f} ;')
                y += 10.8
            L += ['    END', f'  END {net}']
        L += ['  OBS'] + [f'    LAYER M{i} ;\n      RECT 0 0 {mst.w:.3f} {mst.h:.3f} ;' for i in range(1, 8)] + ['  END',
                                                                                                      f'END {mst.name}', '']
        return '\n'.join(L)
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


IR_GUARD = 2           # IR window guard band, in VDD bump pitches (case_irm)
PG_TILE = 43.2         # current-sink tile of a generated block in the IR model: 4 M7 PG pitches (10.8 um), < 1 bump pitch
PDN_THIN_OFF = 0.5     # local die-M8 strap offset inside a thin block (its M7 stripes span 0.3 .. h-0.3)


def pdn_thin_pitch(h, p8):
    """Local die-M8 per-net pitch for a block of height h whose M7 stripes the die M8 lattice (per-net pitch p8) cannot
    cross twice per net (span h-0.6 < 2 p8 + 0.48), else None.  Four straps (VDD,VSS,VDD,VSS) must fit in
    [0.5, h-0.5]: 0.5 + 1.5 p + 0.48 <= h - 0.5; capped at p8 (never sparser than the die grid)."""
    if h - 0.6 >= 2 * p8 + 0.48:
        return None
    p = math.floor((h - 1.48) / 1.5 / 0.008) * 0.008
    if p < 2 * (0.48 + 0.24):
        raise SystemExit(f'pdn_thin_pitch: block height {h} too thin for two M8 straps per net')
    return round(min(p, p8), 3)


def _lef_pg_m7(text):
    """{macro: {'VDD'|'VSS': [(x0, y0, x1, y1)]}} of the M7 PG rects of a LEF (after _pg_only_m7)."""
    out = {}
    for mm in re.finditer(r'^MACRO (\S+)\n(.*?)^END \1', text, flags=re.S | re.M):
        d = out.setdefault(mm.group(1), {})
        for pm in re.finditer(r'  PIN (VDD|VSS)\n(.*?)\n  END \1', mm.group(2), flags=re.S):
            cur = None
            for line in pm.group(2).splitlines():
                st = line.strip().rstrip(';').split()
                if st and st[0] == 'LAYER':
                    cur = st[1]
                elif st and st[0] == 'RECT' and cur == 'M7':
                    d.setdefault(pm.group(1), []).append(tuple(float(v) for v in st[1:5]))
    return out


def _pgt_lef(nm, tw, th, rects):
    """A real abstract's PG current tile: SIZE tw x th, PG pins = the real M7 PG rects clipped to the tile."""
    L = [f'MACRO {nm}', '  CLASS BLOCK ;', f'  FOREIGN {nm} 0 0 ;', f'  SIZE {tw:.3f} BY {th:.3f} ;', '  SYMMETRY X Y ;']
    for net in ('VDD', 'VSS'):
        L += [f'  PIN {net}', '    DIRECTION INOUT ;', f'    USE {"POWER" if net == "VDD" else "GROUND"} ;', '    PORT',
              '      LAYER M7 ;']
        L += [f'        RECT {a:.3f} {b:.3f} {c:.3f} {e:.3f} ;' for a, b, c, e in rects.get(net, [])]
        L += ['    END', f'  END {net}']
    return '\n'.join(L + [f'END {nm}', ''])


def pg_tile_split(ins, power, M, keep=(), real_pg=None, pgt_lef=None):
    """Every block larger than 1.5 PG_TILE as PG_TILE current tiles, each carrying its area share of the block power,
    so PSM injects the block current over its area as the block's cells draw it (PSM puts an instance's whole current
    on one node).  Generated blocks (incl. window clips): sub-tiles on the same M7 (or PG_M8 M8) lattice phase (tile
    sides are multiples of 10.8 um).  Real abstracts in real_pg ({master: {net: M7 rects}}): the instance is replaced
    by tiles whose PG pins are its own M7 PG rects clipped to the tile (LEF text into pgt_lef), placed through the
    instance orientation -- the same metal, the current spread over it."""
    out, pw = [], {}
    real_pg = real_pg or {}

    def cuts(L):
        n = max(1, round(L / PG_TILE))
        e = [0.0] + [round(k * PG_TILE, 3) for k in range(1, n)] + [L]
        return [(a, round(b - a, 3)) for a, b in zip(e, e[1:])]
    for it in ins:
        real = it.master in REAL_FILES
        if it.master in keep or (real and it.master not in real_pg) or (it.w <= 1.5 * PG_TILE and it.h <= 1.5 * PG_TILE):
            out.append(it); pw[it.name] = power[it.name]; continue
        base = it.master.split('_clip_')[0]
        for i, (dx, tw) in enumerate(cuts(it.w)):
            for j, (dy, th) in enumerate(cuts(it.h)):
                if real:
                    nm = f'{base}_pgt{i}_{j}'
                    if nm not in M:
                        rc = {net: [(max(a, dx) - dx, max(b, dy) - dy, min(c, dx + tw) - dx, min(e, dy + th) - dy)
                                    for a, b, c, e in rr if min(c, dx + tw) - max(a, dx) > 0.05 and
                                    min(e, dy + th) - max(b, dy) > 0.05] for net, rr in real_pg[it.master].items()}
                        M[nm] = Q.Master(nm, tw, th, 'M7', 'PG current tile of real ' + base)
                        pgt_lef[nm] = _pgt_lef(nm, tw, th, rc)
                    px = it.x + (it.w - dx - tw if it.orient in ('MY', 'R180') else dx)
                    py = it.y + (it.h - dy - th if it.orient in ('MX', 'R180') else dy)
                else:
                    nm = f'{base}_clip_t{round(tw * 1000)}x{round(th * 1000)}'
                    if nm not in M:
                        M[nm] = Q.Master(nm, tw, th, M[it.master].obs_top, 'PG current tile of ' + base)
                    px, py = it.x + dx, it.y + dy
                t = Inst(f'{it.name}__t{i}_{j}', nm, round(px, 3), round(py, 3), tw, th, it.orient, it.kind, it.region,
                         it.domain)
                out.append(t); pw[t.name] = power[it.name] * tw * th / (it.w * it.h)
    return out, pw


def case_irm(m, work, window, cov, vdd_pitch=None, peak=True):
    """IR window with the REAL element abstracts: pdngen builds the bump-aligned M8/M9 die grid, connects it to the
    q element's and every generated abstract's M7 PG stripes (M7-M8 vias) and to the cfg ROMs' M4 rails through an
    M5 macro grid (M4-M5, M5-M8 via stacks); PSM solves the grid with each instance's power on its own pins."""
    work.mkdir(parents=True, exist_ok=True)
    vp = vdd_pitch or BUMP_PITCH / math.sqrt(0.5)
    # guard band (el1012-s81pdn): the window is solved with IR_GUARD bump pitches of the surrounding die (its blocks,
    # its bumps, its grid) on every side and judged on the inner window only.  Without it the window edge is an
    # open boundary -- the first VSS bump column sits a full pitch (63.6 um) in from the cut, and the field's
    # edge-column q elements read 40.2 mV against 29.7 mV one column in (v4).
    ix0, iy0, ix1, iy1 = windows(m)[window]
    g = IR_GUARD * vp
    x0, y0 = max(0.0, dn(ix0 - g, GX)), max(0.0, dn(iy0 - g, GY))
    x1, y1 = min(DIE[0], ix1 + g), min(DIE[1], iy1 + g)
    inner = (round(max(ix0, x0) - x0, 3), round(max(iy0, y0) - y0, 3), round(min(ix1, x1) - x0, 3),
             round(min(iy1, y1) - y0, 3))
    W, H = round(x1 - x0, 3), round(y1 - y0, 3)
    p = cov['field']
    raw = dn(0.48 / p, 0.160)
    n = math.ceil(vp / raw - 1e-9)
    n += (n % 2 == 0)
    pitch = pg_pitch_grid(vp / n)
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
    # PDN contract v2 (el1012-s81pdn): (1) every generated block's current is drawn where its cells are -- the block
    # is modelled as PG_TILE-sized sub-tiles on the same M7 lattice, each carrying its area share (PSM injects a
    # macro instance's whole current at ONE node: the 63.6/73.4 mV sp_vm / station "drop" of ir_m948 was that
    # single-node injection, case_psmt measured 54.8 vs 2.4 mV); (2) blocks too thin for the die M8 lattice to
    # cross them twice per net get a local die-M8 strap set (pdn_thin_pitch), joined M7-M8 and M8-M9.
    power0 = {it.name: (clip_pw[it.name] if it.name in clip_pw else inst_power(it)) for it in ins}
    q_pg = _pg_only_m7(_lef_text(Q_LEF))
    pgt = {}
    ins, power0 = pg_tile_split(ins, power0, M, keep={real_lef(CFG_LEF)['name']}, real_pg=_lef_pg_m7(q_pg), pgt_lef=pgt)
    masters_used = sorted({it.master for it in ins})
    (work / 'pgt.lef').write_text('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n' +
                                  '\n'.join(pgt[n_] for n_ in masters_used if n_ in pgt) + 'END LIBRARY\n')
    gen = [M[n_] for n_ in masters_used if n_ not in REAL_FILES and n_ not in pgt]
    (work / 'gen_pg.lef').write_text('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n' +
                                     '\n'.join(_gen_pg_lef(g_) for g_ in gen) + 'END LIBRARY\n')
    (work / 'q_pg.lef').write_text(q_pg)
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
    off = round((vp / 2) % pitch, 3)
    cfgm = real_lef(CFG_LEF)['name']
    m8m = [x for x in masters_used if x.split('_clip_')[0] in PG_M8_MASTERS]
    thin = defaultdict(list)
    for x in masters_used:
        if x != cfgm and x not in m8m and x not in REAL_FILES:
            pl = pdn_thin_pitch(M[x].h, pitch)
            if pl:
                thin[pl].append(x)
    thin_set = {x for v in thin.values() for x in v}
    # pdngen -cells is an unanchored regex search: 'dsfd_rstg' (m7) claimed the dsfd_rstg_pq66_* tiles of a thin grid
    other = ' '.join(f'^{x}$' for x in masters_used if x != cfgm and x not in m8m and x not in thin_set)
    m8grid = ('define_pdn_grid -macro -name m8 -cells {' + ' '.join(f'^{x}$' for x in m8m) + '} -halo {0 0 0 0} -voltage_domains CORE\n'
              'add_pdn_connect -grid m8 -layers {M8 M9}\n') if m8m else ''
    for k, (pl, xs) in enumerate(sorted(thin.items())):
        m8grid += (f'define_pdn_grid -macro -name m7thin{k} -cells {{{" ".join(f"^{x}$" for x in sorted(xs))}}} -halo {{0 0 0 0}} '
                   f'-voltage_domains CORE\n'
                   f'add_pdn_stripe -grid m7thin{k} -layer M8 -width 0.48 -pitch {pl:.3f} -spacing {pl / 2 - 0.48:.3f} '
                   f'-offset {PDN_THIN_OFF:.3f}\n'
                   f'add_pdn_connect -grid m7thin{k} -layers {{M7 M8}}\nadd_pdn_connect -grid m7thin{k} -layers {{M8 M9}}\n')
    power = {n_: p_ * (1.0 if peak else 0.25) for n_, p_ in power0.items()}
    tcl = f"""
set t0 [clock seconds]
read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/q_pg.lef
read_lef /work/cfg.lef
read_lef /work/gen_pg.lef
read_lef /work/pgt.lef
read_def /work/win.def
add_global_connection -net {{VDD}} -inst_pattern {{.*}} -pin_pattern {{^VDD$}} -power
add_global_connection -net {{VSS}} -inst_pattern {{.*}} -pin_pattern {{^VSS$}} -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name top -voltage_domains CORE
add_pdn_stripe -grid top -layer M8 -width 0.48 -pitch {pitch:.3f} -spacing {pitch / 2 - 0.48:.3f} -offset {off:.3f}
add_pdn_stripe -grid top -layer M9 -width 0.48 -pitch {pitch:.3f} -spacing {pitch / 2 - 0.48:.3f} -offset {off:.3f}
add_pdn_connect -grid top -layers {{M8 M9}}
define_pdn_grid -macro -name m7 -cells {{{other}}} -halo {{0 0 0 0}} -voltage_domains CORE
add_pdn_connect -grid m7 -layers {{M7 M8}}
{m8grid}define_pdn_grid -macro -name mcfg -cells {{{cfgm}}} -halo {{0 0 0 0}} -voltage_domains CORE
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
  set f [open /work/ir_$net.rpt r]; gets $f; set w 0.0; set wl ""
  while {{[gets $f line] >= 0}} {{
    set c [split $line ,]; set x [lindex $c 3]; set y [lindex $c 4]; set v [lindex $c 5]
    if {{$x >= {inner[0]} && $x <= {inner[2]} && $y >= {inner[1]} && $y <= {inner[3]}}} {{
      set d [expr {{$net eq "VDD" ? {VDD_V} - $v : $v}}]
      if {{$d > $w}} {{ set w $d; set wl $line }}
    }}
  }}
  close $f
  puts "OT_IR_INNER net=$net worst_mv=[format %.2f [expr {{$w * 1000.0}}]] budget_mv=35 at=$wl"
}}
puts "OT_TIME psm_s=[expr {{[clock seconds]-$t0}}]"
exit
"""
    (work / 'run.tcl').write_text(tcl)
    kinds = {it.name: it.kind for it in ins}
    (work / 'kinds.json').write_text(json.dumps(kinds))
    meta = dict(case='c', method='real element abstracts + pdngen + PSM', window=window, window_um=[x0, y0, x1, y1],
                inner_um=[ix0, iy0, ix1, iy1], inner_local_um=list(inner), guard_um=round(g, 3),
                size_um=[W, H], instances=len(ins), clipped=sorted(clip_pw), power_w=round(sum(power.values()), 4),
                power_w_per_mm2=round(sum(power.values()) / (W * H / 1e6), 4), coverage=cov,
                strap_pitch_um=pitch, strap_offset_um=off, masters=masters_used, pg_tile_um=PG_TILE,
                thin_local_m8={f'{k:.3f}': v for k, v in sorted(thin.items())},
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
    pitch = pg_pitch_grid(3.7435); PL = '/OpenROAD-flow-scripts/flow/platforms/asap7'
    t = f"""read_lef {PL}/lef/asap7_tech_1x_201209.lef
read_lef /work/x.lef
read_def /work/t.def
add_global_connection -net VDD -inst_pattern .* -pin_pattern ^VDD$ -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern ^VSS$ -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name top -voltage_domains CORE
add_pdn_stripe -grid top -layer M8 -width 0.48 -pitch {pitch:.3f} -spacing {pitch/2-0.48:.3f} -offset {(vp/2)%pitch:.3f}
add_pdn_stripe -grid top -layer M9 -width 0.48 -pitch {pitch:.3f} -spacing {pitch/2-0.48:.3f} -offset {(vp/2)%pitch:.3f}
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
# --bf-hier COL_W (s81-gen 2026-10-09, bf-arch request 19:50, branch claude/bf-arch-20261009 f2c75c4f7): the BF pair as
# THREE abutted hardened blocks W -> E: dsfd_bf_col (ot_v41_bf_col, R0) | dsfd_bf_front (ot_s81_bf_front) | dsfd_bf_col (MY),
# all 190.08 um tall (the height the BF blocks route at; the flat dsfd_bf frame was 157.68 by default).  The pair is
# 2 x COL_W + 280.152 wide: every frame's lane zone widens by BF_FRAME_EXTRA (node strip / return column move east) and
# the die widens by 2 x 11 columns x BF_FRAME_EXTRA (no reticle rescue: 128 frames, PQ r128 kept; reported).
BF_HIER = None                       # column width (520.128 | 600.264) or None
TIER_COLS_SET = False                # --tier-cols given (reticle die, ROOTS = 2 x sum(TIER_COLS8))
BF_FRONT_W = 280.152
BF_ROUTE_H = 190.08
BF_FRAME_EXTRA = 0.0
BF_SEAM_UM = 0.0                    # compact199: two die-routed seam channels, not an abutted parent
LANES_W = 2 * LANE_W                 # lane zone width of a frame (2 lanes + BF_FRAME_EXTRA)
BFH_IFACE = (('issue', 1), ('a_ctr', 14), ('i1_v', 1), ('i1_bk', 1), ('i1_bf', 1), ('i1_t', 17), ('i2x_q0', 256),
             ('i2x_e0', 10), ('i2x_q1', 256), ('i2x_e1', 10), ('ze_d', 1), ('so_row', 128), ('so_idx', 40), ('so_n', 40))
COL_PITCH8 = COL_W8 + 8.64
HC_CORR = 1209.6                    # HC split: E-half crossing corridor at the VM's y (604.8: GRT overflow, see r8 README)
VCH8 = 1209.6                       # r8 VCH (604.8 in r7; the r8 forwarded chains + hub CDC blocks overflowed it)
SPINE_W8 = SPINE_W + VCH8 - VCH
X0B, X1B, CCB = 283, 266, 15        # lane stream: x0 (q0 e0 + 17 ctl) | x1 (q1 e1) | cc (go cfg_go cfg_ph cfg_np)
LSW = X0B + X1B + CCB               # 564
# --bf-x2-static (S-BIND 2026-10-15; D2 realisation el1011-s81die.log 10-14 18:08, map physical/s81_die_pins/v20/bf_x2_lane.json):
# the x lane is ONE packed static word {x2 536 | cc 15 | x1 266 | x0 283 | v} (dsfd_sp_pq_n +DSFD_PQ_STATIC_X2 xw/xe
# 1,101 b): every fragment shares every register, so legacy and extension never acquire different delays.  hx start
# blocks = same-stream pin pipelines (no ratio FIFO), the column FIFO = ot_s81_static_column_ingress (fixed epoch, no
# occupancy / ready), slot stations carry x2 beside x0 / x1, and every BF front's xb = {x1[265:0], x0[265:0], x2}
# (load sub-ranges of the x0 / x1 nets + the x2 net).  Owner static-cycle rule: no FIFO ready / credit on the lane.
X2B = 536
BF_X2_STATIC = False
LEAF, NODEB, STB = 63, 66, 2
CRET = NODEB + STB                  # column return payload: root word + {fault, busy}
STEP8 = 400.0                       # nominal forwarded-stage spacing (<= LINK_STAGE_UM after placement)
STEP9 = 425.0                       # r9: closer to the 430.56 um reach (the placement search still enforces it)
HSTN_DOM = dict(serial_0p9='serial', stream_1p2='stream')
SEQ_WH = (34.56, 60.48)
STACKS = dict(layer=('SW', 'SE', 'NW', 'NE'), head=('SW', 'SE', 'NW', 'NE'), layer1=('SW',), layer1e=('SW', 'SE'))
LAYER_KINDS = ('layer', 'layer1', 'layer1e')
# layer1e (s81-gen 2026-10-09; OWNER 10-09 engram-tables-in-hbm; design results/arch/engram_20261008/design.json die_change):
# the layer1 (m221pq) die of the 8 Engram home dies (stages 3 / 42 x 4 TP ranks) + the SE HBM3E stack band: phy_SE + ctrl_SE
# (same masters as SW) and, in the SE service slot, the Engram service eng_SE (dsfd_engram: ot_dsrom_engram_lookup in
# dsfd_engram_lkp, dsfd_engram_sink, ot_dsrom_engram_prefetch SRAM, the SE half of ot_dsrom_engram_hbm_backend), centred on
# ctrl_SE's request face.  The table region (25.35 GB / die) spans both stacks (Codex 4a86bf870: homes SW0 / SE1): the SW
# half is reached through the SW stack's client svc_SW (eq / er: the backend's narrow hq / hr interface; the SW half of the
# backend shares ctrl_SW.rq with the scan service under svc_SW's PC grants).  Widths from the RTL ports:
ENG_WH = (1188.0, 432.0)        # design.json eng_SE outline (route variant A, ~55 % util pending synthesis)
HBM_RQ_BITS = 10912             # dsfd_ctrl rq = 32 x {wdata 256, wstrb 32, tag 17, len 4, addr 30, we, v}
ENG_BUSES = (
    # (driver, driver port, load, load port, bits, what)
    ('collective', 't_eng', 'eng', 'f_win', 73, 'lead flit window: win_v 1 + win_ids 4 x 17 + rel 4 (rank retirements)'),
    ('eng', 't_collective', 'collective', 'f_engc', 1, 'win_cred'),
    ('eng', 't_ag', 'collective', 'f_eng', 282, 'all-gather out: o_v/col5/beat3/slot3/d264 + st_v/slot3/bad + fault'),
    ('collective', 't_engc', 'eng', 'f_agc', 1, 'o_cred'),
    ('collective', 't_engi', 'eng', 'f_ai', 1124, 'all-gather in (4 ranks): in_v4/col20/beat12/slot12/d1056 + st 4/12/4'),
    ('eng', 't_air', 'collective', 'f_engr', 4, 'in_r'),
    ('eng', 't_vm', 'vm', 'f_eng', 532, 'prefetch rows to the consumer: out_v + 512 + ce/ue/fault + rdy 8 + perr 8'),
    ('vm', 't_eng', 'eng', 'f_vm', 16, 'rd_v + rd_addr 11 + rel_v + rel_slot 3'),
    ('host', 't_eng', 'eng', 'f_cfg', 3, 'cfg_layer + cfg_rank (boot CSR)'),
)
HOST_SLAB = False              # host-aware generator default; initialized before direct build() calls
HOST_CF_BITS, HOST_TC_BITS = 514, 130   # collective -> host / host -> collective (--rtl-bind: dsfd_host_c 516 / 81)
CTRL_RQ = False                # --ctrl-rq (implied by layer1e)
FWD_IFACE = False              # --fwd-iface: host-write / Engram die interfaces as forwarded lanes
Q_X1B = False                  # --q-x1b: option-B q pin plan (x1 on the S-face east end, own bank; right lane MY)
# --cfg-rgap UM (ds-1010 2026-10-10): a relay gap of UM in every right-lane cfg ROM row, between ROM CFG_RGAP_AT-1 and
# CFG_RGAP_AT.  Root cause of the x1b residual 128 (one per frame, rt_<f>_8b): a left-lane return leaf runs east from its
# N bank to the node strip through the inter-element band, whose only relay room is the ~35 um strip above the slot
# station (x 365-538); the right-lane sequencer + 7 ROMs (x 557-914) leave no 17.3 um box for 380 um, so the leaf hop
# station-area relay -> beyond the ROM row is 538 um > the 504 um SS reach.  The gap is a real reserved relay site in
# the row (the R row has 126 um of slack to the node strip); default 0 = off (byte-identical).
CFG_RGAP = 0.0
LANE_EQUAL = False             # --lane-equal (ds-1010 lat-audit): equal column-relay counts on xa / xb / cc of a slot segment
CFG_RGAP_AT = 4
RSV_RECTS = []                 # reserved relay sites (x0, y0, x1, y1, tag): tag 'rt' (--cfg-rgap) / 'x' (--xb-rgap)
RSV_ALLOW = None               # the tag whose sites the relay being placed may take (None: no reserved site)
# --xb-rgap UM (ds-1010/s81die 2026-10-10, efs q pin plan = x0 / x1 / cfg / go on ONE S-face bank in the element's
# middle): a reserved relay site of UM in every right-lane cfg ROM row between the pair sequencer and ROM 0, for the
# slot's x-lane relays only (xa_ / xb_ / cc_ column and hop relays).  Root cause (efs check, src 734e82437): the slot
# station (x 365-538) has no free relay box toward its banks; lane-equal x1 relays found none in the 100 %-packed cfg
# ROM + sequencer row and fell up to 250 um BEHIND the station (y_xb_127_7_0 in the slot below), so the hops to the
# right-lane bank / next station ran 517-713 um (768 g_xb / y_xb SS reach + 1,536 x0/x1 field mismatches: the x1 lane
# took extra hop relays x0 did not).  The site sits on the station -> right bank / next-station path.  Default 0 = off.
XB_RGAP = 0.0
XB_RGAP_FIRST = False          # --xb-rgap-first (s81-die v17): the x relay site beside the slot station, the sequencer E of it
# --x-site-pair (s81-die v18, frame-template relay-site repair, owner 10-14): the --xb-rgap gap E of every slot station
# (60.48 x 62.95 um between the station's E edge and the R-lane sequencer) holds TWO stacked relay sites, each owned by ONE
# net: the lower one by xa_<r>_<s+1>, the upper one by xb_<r>_<s+1>, i.e. the lanes the station s itself drives into slot
# s's banks and up to station s+1.  Root cause (v18 native207 hop gate, 545,152 x_lane bits over reach, all in-frame,
# ~4.3k a frame on all 128 frames): the one shared 'x' site was taken first-come by the relay of the PREVIOUS slot's lane
# (its midpoint lies inside the element above the band, nearest free box = the next band's site), so every later lane's
# relay landed one band too far north (y_xa_0_2_0 beside t0_2 instead of t0_1) and the hop fix chained g_ relays to sites
# up to 1,244 um from the banks.  An owned site beside the DRIVER station reaches both banks of its slot (<= ~360 um, bank
# pair limit 407) and the next station's E-end xai / xbi (<= ~290 um, limit 500).  Register counts (cycles) unchanged.
X_SITE_PAIR = False
ALIGN_JOGS = False             # --align-jogs (r5 10-14): move a station facing its peer across by the bundle's jog (pin_align FAIL)
SPLIT_FAR_PINS = False         # --split-far-pins (r5 10-14): a local chain whose assigned target pins split into a run + a far trailing group gets its own chain to that group
HOP_PLAN_R = {}                # --hop-pair: planned hop -> its effective plan reach (pair limit - margin)
HOP_ITER = 0                   # --hop-iter N: re-plan the hop fix on the built die up to N times (new over-limit hops)
HOP_SPREAD = 0                  # --hop-spread BITS (s81-die r6 2026-10-14): a hub hop of a bus >= BITS wide is planned at
                                #   R - (half pin extent of the driver port + of the load port): the gate judges the WORST bit,
                                #   the plan the group anchor (xsp6: hc_s -> hc_t tf2 3,056 b staged at <= 480 um anchors came
                                #   out 744-775 um per bit; collective -> vm 948 um)
HOP_SPREAD_R = {}               # planned hop -> spread-reduced reach (pass 2 counts its stages with it)
HOP_PAIR = 0.0                 # --hop-pair UM: hop-fix plans each hop against its real pair limit minus UM (pin spread margin)
XSITES = {}                    # (frame, slot) -> [(x, y) xa site, (x, y) xb site]  (lower-left corners)
CK_RULE = False               # --ck-rule: generated masters >= 300 um take ck in the middle third of a long face
COLL_SPLIT3 = False            # --coll-split3: collective slab = composition_split3 outline (1,371.792 x 1,369.416)
COLL_SPLIT3_COMP = 'physical/s81_ph_views/collective/composition_split3.json'
COLL_SPLIT3_CR = False         # explicit planning candidate, never a closure claim
COLL_MTP_LANE = False          # --coll-mtp-lane (mtp-colllane-1011): head die: collective slab composition_split3cr_mtpl = split3cr +
                               #   a dedicated MTP lane row (lane tile W4 on lk_W4 + dsfd_coll_mtp_lane: the MTP_SEQ_BUSES
                               #   mtp <-> collective end, dsfd_coll_mtp_ep RTT-sized 8 / 8); RTL define OT_S81PH_COLL_MTPL
COLL_P2_LANE = False           # --coll-p2-lane (mtp-colllane-1011): draft die A: composition_split3cr_p2l = split3cr + P2 lanes W4
                               #   (primary, board) / E4 (die B, UCIe) + dsfd_coll_p2_lane x2 + dsfd_coll_p2_ep (the P2_BUSES
                               #   collective <-> p2 end); RTL define OT_S81PH_COLL_P2L
# --suhc-1011 (ds-1010/s81die 2026-10-11, s81-suhc-1011 transport model results/arch/s81_suhc_20261011/transport_model.json,
# main-approved): the residual h stays resident in the HC master; the all-reduce result y goes collective -> HC directly
# (8,192 b = 4,096 b to each HC half, 20 beats); HC -> VM carries the norm codes (2,048 b); capture -> SU direct g / u
# for quant2 (SUHC_GU b to each SU half: PLANNING width until the model's next revision); the SU / HC slabs run on the
# 1.2 GHz stream domain (their priced su_norm / hcpost / swiglu / qbank pipelines), the VM keeps its narrow buses only.
SUHC_1011 = False
SUHC_DOM = 'serial_0p9'
SUHC_HC_VM = 1024
SUHC_GU = 512
# collective -> HC y as 1,024-b lanes (4 a half): one station chain each (a 4,096-b station found no box in the VCH)
SUHC_BUSES = tuple(('collective', h_, 1024, f't_{h_}{k}', f'f_coll{k}') for h_ in ('hc_s', 'hc_n') for k in range(4)) + \
    (('capture', 'su_s', SUHC_GU, 't_su_s', 'f_capture'), ('capture', 'su_n', SUHC_GU, 't_su_n', 'f_capture'))
# --hrow-tx (ds-1010/s81die 2026-10-11, mtp-dsbind 564941967): the stage dies of layers 37 / 38 / 39 send the HC means of
# the residual (h resident in HC under --suhc-1011) to DSpark primary die P.k on a dedicated MTP lane: ot_dsrom_mtp_hrow_tx
# (header {user, pos, issue epoch} from the WFC kit's t_hep + the die's part strap from the host; 80 x 1,024-b beats from
# hc_n; flit {hdr, last, 512} + grant to the collective's MTP lane).  ~1.6 kbit of state: a 259.2 x 129.6 um slab.
HROW_TX = False
HRTX_UM = (259.2, 129.6)
HRTX_BUSES = (('hc_n', 'hrtx', 1025, 't_hrow', 'f_b'), ('hrtx', 'hc_n', 1, 't_b_r', 'f_hrow_r'),
              ('hrtx', 'collective', 515, 't_lane', 'f_hrow'), ('collective', 'hrtx', 1, 't_hrow_g', 'f_lane_g'))
HRTX_KIT_BUSES = (('wfc', 'hrtx', 36, 't_hep', 'f_h'), ('hrtx', 'wfc', 1, 't_h_r', 'f_hep_r'))
HRTX_HOST_BUSES = (('host', 'hrtx', 2, 't_hpart', 'f_part'),)
COLL_FACE_UM = 1036.8         # --suhc-1011 collective slab height floor (pin face)
# v2 hierarchical slab outlines (um): SU physical/s81_ph_views/su_hier/su_slab_composition.json (claude/s81-suhc-hier-1011
# 36ccf0cb0: 3 x 572.4 columns, 29 tiles); HC root split (5db4c7ec6 / 597e34cac, ds-1010.log 14:14): 3 x 575.992 columns
SU_V2_UM = (1727.976, 6069.6)
HC_V2_UM = (1727.976, 9640.0)
HC_S_GROW_DOWN = 0.0            # explicit contract growth keeps the HC north edge fixed
HC_T_UM = None                  # contract v12 sp_hc_t: the HC chain tails in the E-column floor slot below the corridor
HC_T_COLS = 3                   # HC columns (one chain each); v12 hc_s <-> hc_t crossing buses per column
HC_T_FWD, HC_T_RET = 1264, 1090   # per column: fd 1128 + fv 7 + rst 1 + cy 128 / rd 1082 + rv 8 (ot_s81_hc_cth ports)
HC_RTL_WIDTHS = False           # --hc-rtl-widths (r5 10-14, F9 rtlbind decision): per-column crossings from the RTL formula


def hc_rtl_widths(ng=256, s_rd=2, s_rt=4):
    """dsfd_sp_hc_c / dsfd_sp_hc_t localparams TFW / TRW at the production NG 256, S_RD 2, S_RT 4 (3056 / 2164 per column;
    the 1264 / 1090 die widths were an NG <= 96 cth generation)"""
    big = ((ng // 8 + 2) // 3) * 8 * 32
    tfw = (72 + 16 * s_rd) + max(s_rd * 512, big) + s_rd + 5 + 129
    trw = s_rt + 24 * s_rt + 8 + 512 * s_rt + s_rt + 4
    return tfw, trw
HUB_SOUTH_SHIFT = 0.0           # v18 geometry trial: reserve south corridor explicitly
ASSIGNED_PINS_DIR = None       # exact die-assigned parent pins + per-child clock entries
CONTRACT_SLABS = {}             # --contract FILE (s81-die-iter): centre slab outlines {name: (w, h)} from the hier contract
SUHC_V2_HC_N = False            # --suhc-v2-hc-north: the v2 HC in the slot above the corridor (default: hc_s floor slot)
SUHC_V2 = False                 # --suhc-v2 (s81die-1011/ctrl, die lead decision 3): su_hc contract v2 = ONE SU master
                                #   (dsfd_sp_su_c, su_s W-floor slot) + ONE HC master (dsfd_sp_hc_c, hc_s E-column slot);
                                #   su_n / hc_n slots freed; VM row slots replace the 1,024-b VM <-> SU / HC buses
# physical/s81_ph_views/contracts_1011/su_hc.v2.json: SU 16 rd + 16 wr VM row slots, HC 2 rd + 8 wr, HC y 8,192 from the
# collective (valid / ready); the su -> hc 512, hc_s <-> hc_n 1,024, hc_n -> VM and capture -> SU g/u buses are retired
SUHC_V2_BUSES = tuple(
    # SU VM row slots per pin owner p (ds-1010.log 14:11 slot map: slots 4p..4p+3, po0 at the NE corner = top of the SU)
    b_ for p in range(4) for b_ in (
        ('su_s', 'vm', 4, f'rq_v[{4 * p}:{4 * p + 3}]', f'f_su_rqv[{4 * p}:{4 * p + 3}]'),
        ('su_s', 'vm', 56, f'rq_row[{56 * p}:{56 * p + 55}]', f'f_su_rq[{56 * p}:{56 * p + 55}]'),
        ('vm', 'su_s', 4, f't_su_rsv[{4 * p}:{4 * p + 3}]', f'rs_v[{4 * p}:{4 * p + 3}]'),
        ('vm', 'su_s', 2048, f't_su_rs[{2048 * p}:{2048 * p + 2047}]', f'rs_d[{2048 * p}:{2048 * p + 2047}]'),
        ('su_s', 'vm', 4, f'wq_v[{4 * p}:{4 * p + 3}]', f'f_su_wqv[{4 * p}:{4 * p + 3}]'),
        ('su_s', 'vm', 56, f'wq_row[{56 * p}:{56 * p + 55}]', f'f_su_wq[{56 * p}:{56 * p + 55}]'),
        ('su_s', 'vm', 64, f'wq_mask[{64 * p}:{64 * p + 63}]', f'f_su_wqm[{64 * p}:{64 * p + 63}]'),
        ('su_s', 'vm', 2048, f'wq_d[{2048 * p}:{2048 * p + 2047}]', f'f_su_wqd[{2048 * p}:{2048 * p + 2047}]'))) + (
                 ('hc_s', 'vm', 2, 'rq_v', 'f_hc_rqv'), ('hc_s', 'vm', 28, 'rq_row', 'f_hc_rq'),
                 ('vm', 'hc_s', 2, 't_hc_rsv', 'rs_v'), ('vm', 'hc_s', 1024, 't_hc_rs', 'rs_d'),
                 ('hc_s', 'vm', 8, 'wq_v', 'f_hc_wqv'), ('hc_s', 'vm', 112, 'wq_row', 'f_hc_wq'),
                 ('hc_s', 'vm', 128, 'wq_mask', 'f_hc_wqm'), ('hc_s', 'vm', 4096, 'wq_d', 'f_hc_wqd'),
                 ('collective', 'hc_s', 1, 't_hc_yv', 'y_v')) + tuple(
                 # the 8,192-b y as 8 x 1,024-b lanes (each its own VCH lane / station row, as the v1 4 + 4 lanes were)
                 ('collective', 'hc_s', 1024, f't_hc_y[{1024 * k}:{1024 * k + 1023}]', f'y_d[{1024 * k}:{1024 * k + 1023}]')
                 for k in range(8)) + (

                 ('hc_s', 'collective', 1, 'y_rdy', 'f_hc_yr'),)
SU_E = 0.0                     # --su-e MM2: su_n in the E column above hc_n (W column: su_s + centre)
COLL_SLAB_H = None             # --coll-slab-h H (s81die-1011 hier contract v1): collective slab height at full hub column width
VM_SLAB = None                 # --vm-slab W,H (s81-vm-1011): VM master outline in um
ECOL_SLABS = ()               # --ecol-slabs (ds-1010/s81die): W-column centre slabs moved to an E-column sub-column
ECOL_W = 518.4
CTRL_SVC_ALIGN = False         # --ctrl-svc-align (s81-die v14): stack client pins at their controller bits' x
HOP_GATE_UM = None             # --hop-gate UM (s81-die v14): real mode fails when any data bit's pin-to-pin hop > UM
RLY_REAL_DIMS = False          # reserve native wide relay envelopes before choosing their faces
RLY_FACE_REACH = 0.0           # --rly-face-reach UM (s81-die v16): last column relay's out face by its worst load
HOP_EXTRA = 0                  # --hop-extra N: extra stations a hop may take when its planned count has no clean placement
HOST_MM2 = 0.10
HOST_FACE_UM = 129.6           # --fwd-iface: host slab height floor (pin face for the forwarded lanes)
FRAME_OUT_RELAY = False        # direct-build callers retain the CLI default too
HB_PITCH = (279.936, 280.8)                 # head element pitch (275.23 + halo, on the lattice)
HB_H = 2 * HB_PITCH[1]                      # one bundle: B + glue row, then 4 A row
HB_GLUE = (302.4, 151.2)                    # bundle glue: BST stages, lane skew, B demux, compare (RTL inside the bundle)
HB_GLUE_W = 14000 * FLOP_CLK_W * 1.5        # ~14k flops (2 x 512 BST + 16 lanes x up to 56-deep skew + compare)
SSTN_WH = (172.8, 30.24)            # wide and short: the 564-b stream pins spread at 3 tracks (r8 GRT: a 52 um station
                                    # piled the slot-to-slot stream into one M7 column over the element row)
CF_WH = (850.176, 47.52)
CF_WH_V2 = (432.0, 95.04)        # --cfifo-v2: same area, 2:1 squarer (the 850 x 47.5 slab had 671 ps CTS insertion)
CFIFO_V2 = False
CFIFO_COLCK = False                 # --cfifo-colck (s81-die-2 2026-10-08): the cfifo's column side (read port, x-lane /
                                    # cc output flops, st / ri capture, rd launch, rsync) is clocked from cr, a sink of
                                    # its own column tree (co -> tree -> cr), not from ck: sta_v6 FF class 70k < -100 was
                                    # xa/xb launched at ck (min 161 ps) into the first column relays at co + tree (~450 ps);
                                    # TT class cf* ri capture (column -> cfifo) moves onto the same tree.  0 cycles.
RSTG_WH = (38.88, 34.56)
NVR = RET                           # NV5 draft-head result word back into its lm-head pair
SEQ_XL, SSTN_X, R_CFGX = 326.16, 365.04, 37.152
CF_X = 328.32                       # column FIFO x in the frame
GLUE_RTL = 'results/rtl/dsrom_s81_fulldie_20261004/r8/dsfd_glue.sv'
# REDESIGN-S81 2026-10-08: r2l / l2r hub end blocks register every pin (TT link-budget misses on hx_W / hcol / hsel)
HEND_PINREG = True
# Slot parameterisation (owner decision 2026-10-06: taller q-element slot, fewer elements per die, 55-60 % cell
# utilisation).  ELEM_FRAME_H = the element frame height in its slot (157.68 today: q / BF outline + halo); the slot is
# the cfg band (ELEM_DY) + the element frame + 4.32; SLOTS8 = the slots per column that fit the field height between
# the bands with a >= FIELD_MARGIN gap each side; PAIRS = pairs (elements) per die (configure(pairs=...)).
ELEM_FRAME_H = 157.68
FIELD_MARGIN = FIELD_MARGIN_DEFAULT = 216.0
PQ_FIELD_MARGIN = 108.0       # --pq-place minimum field <-> band gap (see configure: the PQ root row)
SLOT_H8, SLOTS8 = SLOT_H, SLOTS
Q_ELEM_FRAME_H = None             # opt-in independent q frame, BF remains ELEM_FRAME_H
SU_AREA_MM2 = None                # optional current-leaf SU reservation, not a hard macro
FRAME_H8 = SLOTS8 * SLOT_H8


def slot_geometry(elem_frame_h=None, field_margin=None):
    global ELEM_FRAME_H, SLOT_H8, SLOTS8, FIELD_MARGIN, FRAME_H8
    if CANONICAL_LAYOUT is not None:
        # Canonical frames carry their exact packed slot heights independently.
        # Keep the established hub scaffold; never derive a symmetric field
        # or crop these frames through the historical uniform-slot count.
        SLOTS8 = max(f['packed_slots'] for f in CANONICAL_LAYOUT['placements'])
        return SLOT_H8, SLOTS8
    if elem_frame_h:
        ELEM_FRAME_H = float(elem_frame_h)
    if field_margin is not None:
        FIELD_MARGIN = float(field_margin)
    SLOT_H8 = round(up(ELEM_DY + ELEM_FRAME_H + 4.32, GY), 3)
    band = up(EDGE, GY) + PHY_H + 8.64 + CTRL_D + 8.64 + SVC_D
    avail = DIE[1] - 2 * band - 2 * FIELD_MARGIN - sum(chh(t) for t in range(TIERS + 1))
    if Q_ELEM_FRAME_H is None:
        SLOTS8 = int(avail // (TIERS * SLOT_H8))
        FRAME_H8 = SLOTS8 * SLOT_H8
    else:
        assert DIE_KIND in LAYER_KINDS and BF_PER_REGION is not None and NV_PAIRS == 0, \
            'mixed q/BF heights need an r8 layer die with explicit --bf-per-region and no NV'
        qh = round(up(ELEM_DY + Q_ELEM_FRAME_H + 4.32, GY), 3)
        SLOTS8 = math.floor((avail / TIERS - BF_PER_REGION * (SLOT_H8 - qh)) / qh + 1e-9)
        assert SLOTS8 >= BF_PER_REGION, 'BF slots alone exceed field height'
        FRAME_H8 = round(BF_PER_REGION * SLOT_H8 + (SLOTS8 - BF_PER_REGION) * qh, 3)
    return SLOT_H8, SLOTS8


def column_height():
    return FRAME_H8 if Q_ELEM_FRAME_H is not None else SLOTS8 * SLOT_H8


def pack_frame(pairs, bfs, nvs):
    """Exact existing pair order, with independent heights for q and BF slots."""
    slot, half_open, elems, kinds = -1, None, [], []
    for p in pairs:
        if p in nvs:
            slot += 2
            elems.append((p, 'NV', slot - 1, 'B'))
            kinds.extend(['NV', 'NVX'])
        elif p in bfs:
            slot += 1
            elems.append((p, 'BF', slot, 'B'))
            kinds.append('BF')
        elif half_open is not None:
            elems.append((p, 'q', half_open, 'R'))
            half_open = None
        else:
            slot += 1
            half_open = slot
            elems.append((p, 'q', slot, 'L'))
            kinds.append('q')
    offsets, heights, y = [], [], 0.0
    for kind in kinds:
        fh = Q_ELEM_FRAME_H if kind == 'q' and Q_ELEM_FRAME_H is not None else ELEM_FRAME_H
        h = round(up(ELEM_DY + fh + 4.32, GY), 3)
        offsets.append(round(y, 3)); heights.append(h); y += h
    return elems, offsets, heights



def set_globals_pairs(p, b, n):
    global PAIRS, BF_PAIRS, NV_PAIRS
    PAIRS, BF_PAIRS, NV_PAIRS = p, b, n


def _frames_fit(slots, slot_h):
    """the r8 field packing (as build_r8) of the current PAIRS / BF / NV sets fits `slots` per column"""
    rng, hbf = frame_plan_r8()
    bfs, nvs = bf_sites(), nv_sites()
    for r in range(ROOTS):
        lo, hi = rng[r]
        n = hi - lo
        elems, offsets, heights = pack_frame(range(lo, hi), bfs, nvs)
        if len(heights) > slots or sum(heights) > column_height() + 1e-6 or \
                2 * n - 1 > int(column_height() / NODE_FRAME[1] + 1e-6):
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
    if CANONICAL_LAYOUT is not None:
        return dict(scope='Canonical immutable full2417 typed frame inventory; actual native binding and transport gates are separate', pairs=2417, bf_double=519, ordinary=1898, bf_pair_ids=sorted(BF_EXPLICIT_IDS), source_sha256=CANONICAL_LAYOUT['sha256'], frames=128, typed_frame_inventory_complete=True)
    if BF_EXPLICIT_IDS is not None:
        # The typed head inventory is fixed; layer capacity sweeps would
        # change pair identity and omit its dedicated Markov engines.
        return dict(scope='fixed explicit head field inventory; no maximum-die claim',
                    pairs=PAIRS, bf_double=BF_PAIRS, ordinary=PAIRS-BF_PAIRS,
                    bf_pair_ids=sorted(BF_EXPLICIT_IDS), field_frames_fit=_frames_fit(sl, sh),
                    dedicated_Markov_engines_included=False)
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
    return dict(elem_frame_h_um=ELEM_FRAME_H, q_elem_frame_h_um=Q_ELEM_FRAME_H, frame_h_um=column_height(), slot_h_um=sh, slots_per_column=sl, columns=ROOTS,
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
        sh, sl = slot_geometry()
        for p in range(ROOTS * max(n, 1), 4000):
            set_pairs(p)
            if not _frames_fit(sl, sh):
                break
            best = p
        out[str(n)] = dict(max_pairs=best, bf=n * ROOTS, slots_per_column=sl, slot_h_um=sh)
    BF_PER_REGION = kb
    set_globals_pairs(*keep)
    slot_geometry()
    return out
CFG7_RTL = 'rtl/v41die/ot_s81_cfg7_seq.sv'
CFG7_MASTERS = ('ot_s81_cfg7_seq', 'ot_s81_cfg7_seq_bf')     # q pairs (PQ per the q element) / BF pairs (PQ 0)
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
    # s81-die-2 2026-10-08 (tie-off audit TA-10): the PQ q element's op tag in / loader handshake out, bound to its pair
    # sequencer ot_s81_cfg7_seq (go_tag, ef = {bank_free, sh_free}); only when the abstract has them (PQ elements)
    rq_ = real_lef(Q_LEF)['pins']
    if 'go_tag[0]' in rq_:
        qp.update(gt=_bus('go_tag', 2), ef=['sh_free', 'bank_free'])
    assert len(qp['x0']) == X0B and len(qp['x1']) == X1B and len(qp['r0']) == LEAF
    assert len(set(qp['r0'] + qp['r1'])) == 2 * LEAF == RET
    cfg = dict(ck=['clk'], ce=['ce_in'], a=_bus('addr_in', 12), rd=_bus('rd_out', 72))   # a bus binds bits [:width]
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
    return int(column_height() / HB_H + 1e-6)


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

    @contextmanager
    def temporary(self):
        """Reserve a candidate chain's boxes, then restore the exact spatial index."""
        saved = {}

        def reserve(r):
            for k in self._bins(*r):
                if k not in saved:
                    saved[k] = len(self.g[k]) if k in self.g else None
                self.g[k].append(r)

        try:
            yield reserve
        finally:
            for k, length in saved.items():
                if length is None:
                    del self.g[k]
                else:
                    del self.g[k][length:]

    def free(self, r, gap=0.0):
        x0, y0, x1, y1 = r
        for k in self._bins(x0 - gap, y0 - gap, x1 + gap, y1 + gap):
            for a0, b0, a1, b1 in self.g.get(k, ()):
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

    def near(self, cx, cy, w, h, allowed, prev=None, horiz=True, reach=None, span=72.0, rows=10, nxt=None, nreach=None, cross_step=None):
        """Free lattice spot for a w x h block centred near (cx, cy) inside `allowed`, within `reach` of `prev` and
        (s81-die-timing 2026-10-08) within `nreach` of the next point `nxt` of the chain (r3: hop relays that found no
        spot inside a packed frame landed up to 906 um short of their load, on the far side of their driver)."""
        reach = reach or FWD_REACH
        step = cross_step or (h if horiz else w) + 2.16
        cands = _near_cands(span, rows, step)
        if span >= 600.0:
            cands = _near_reachable_prefix(cands, span, rows, step, cx, cy, w, h, allowed, prev, reach, nxt, nreach, horiz)
        for a, c in cands:
            dx, dy = (a, c) if horiz else (c, a)
            x = dn(cx + dx - w / 2, GX)
            y = dn(cy + dy - h / 2, GY)
            # (s81-die-2) the cheap reach tests first: same first hit, the occupancy test only on reachable spots
            if prev is not None and _mh(prev, (x + w / 2, y + h / 2)) > reach:
                continue
            if nxt is not None and _mh(nxt, (x + w / 2, y + h / 2)) > nreach:
                continue
            r = (x, y, x + w, y + h)
            if not _inside(r, allowed) or not self.occ.free(r, 0.432):
                continue
            if RSV_RECTS and any(t_ != RSV_ALLOW and a_ < r[2] and r[0] < c_ and b_ < r[3] and r[1] < d_
                                 for a_, b_, c_, d_, t_ in RSV_RECTS):
                continue
            return x, y
        return None


_NEAR_CANDS = {}


def _near_cands(span, rows, step):
    k = (span, rows, step)
    if k not in _NEAR_CANDS:
        al = [0.0]
        for i in range(1, int(span / 4.32) + 1):
            al += [-4.32 * i, 4.32 * i]
        cr = [0.0]
        for i in range(1, rows + 1):
            cr += [step * i, -step * i]
        _NEAR_CANDS[k] = sorted(((a, c) for a in al for c in cr), key=lambda t_: abs(t_[0]) + 0.6 * abs(t_[1]))
    return _NEAR_CANDS[k]


_NEAR_COSTS = {}

def _near_reachable_prefix(cands, span, rows, step, cx, cy, w, h, allowed, prev, reach, nxt, nreach, horiz):
    """Keep an exact ordered prefix containing every potentially legal candidate.

    Large failed-placement retries otherwise scan offsets thousands of microns
    beyond both endpoint reaches. This only skips impossible suffix candidates;
    the original strict Manhattan, occupancy and rectangle tests still decide.
    """
    import bisect
    eps = 2e-6
    def feasible(offset, axis):
        center, size, grid = (cx, w, GX) if axis == 0 else (cy, h, GY)
        lo = dn(center + offset - size / 2, grid)
        mid = lo + size / 2
        if not any(lo >= r[axis] - eps and lo + size <= r[axis + 2] + eps for r in allowed):
            return False
        if prev is not None and abs(mid - prev[axis]) > reach + eps:
            return False
        if nxt is not None and abs(mid - nxt[axis]) > nreach + eps:
            return False
        return True
    along = [0.0]
    for i in range(1, int(span / 4.32) + 1):
        along.extend((-4.32 * i, 4.32 * i))
    across = [0.0]
    for i in range(1, rows + 1):
        across.extend((step * i, -step * i))
    aa = [v for v in along if feasible(v, 0 if horiz else 1)]
    cc = [v for v in across if feasible(v, 1 if horiz else 0)]
    if not aa or not cc:
        return []
    maximum_cost = max(map(abs, aa)) + 0.6 * max(map(abs, cc))
    key = (span, rows, step)
    if key not in _NEAR_COSTS:
        _NEAR_COSTS[key] = [abs(a) + 0.6 * abs(c) for a, c in cands]
    return cands[:bisect.bisect_right(_NEAR_COSTS[key], maximum_cost + eps)]


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


def relay_dims(bits, horiz):
    """Reserve all supported native orientations before placement selects faces.

    The CLOSED wide SN master is 34.56 x 19.44 and WE is 21.6 x
    30.24. Reserving their enclosing rectangle lets final view binding take
    the exact real outline without growing a placed tile. Corner masters
    still require their own real view; this does not alias them to a stand.
    """
    if RLY_REAL_DIMS and bits in (266, 283):
        return 34.56, 30.24
    return stn_dims([bits], horiz)


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

    def run(self, name, lanes, path, allowed, src, forced=(), first_prev=None, kind='stn', reach=None, force_horiz=False):
        """Place stations along polyline `path` for a chain of `lanes` (list of data widths).  `forced`: path lengths
        where a station MUST stand (taps / branches).  Returns [(inst, s_along)].  src: (x, y) of the source pin."""
        path_receipt=None
        if self.m.get('canonical_layout'):
            path_receipt=dict(chain=name,lanes=list(lanes),path=list(path),source=src,forced_stops=list(forced),force_horiz=force_horiz,stations=[],status='BUILDING')
            self.m.setdefault('chain_paths',[]).append(path_receipt)
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
                horiz = force_horiz or d in 'EW'
                w, h = stn_dims(lanes, horiz)
                # --relay-progress: the LAST station of a chain (its target is the chain end) may not slide past the end
                PL_ = dict(nxt=end, nreach=_mh(cur, end) + 15.0) if RELAY_PROGRESS and L - t_ <= step else {}
                placed = self.P.near(cx, cy, w, h, allowed, prev=cur, horiz=horiz, reach=reach, **PL_)
                if placed is None and PL_:
                    placed = self.P.near(cx, cy, w, h, allowed, prev=cur, horiz=horiz, reach=reach, span=300.0, rows=24, **PL_)
                if placed is None:
                    # --relay-progress: the unanchored must-stop fallback (prev=None) may not stand behind the previous
                    # station w.r.t. the path point one step ahead (detour paths: not w.r.t. the chain end)
                    ah_ = _poly_at(path, min(L, t_ + step))[0]
                    PG_ = dict(nxt=ah_, nreach=_mh(cur, ah_) + 15.0) if RELAY_PROGRESS else {}
                    if must:
                        placed = self.P.near(cx, cy, w, h, allowed, prev=None, horiz=horiz, span=200.0, rows=16, **PG_)
                        if placed is None and PG_:
                            placed = self.P.near(cx, cy, w, h, allowed, prev=None, horiz=horiz, span=400.0, rows=40, **PG_)
                        if placed is None and PG_:
                            _rp_log(dict(chain=name, stop=round(target, 1), cur=cur, end=end))
                            placed = self.P.near(cx, cy, w, h, allowed, prev=None, horiz=horiz, span=200.0, rows=16)
                        break
                    t_ -= 25.0
            if placed is None:            # widen the search (still within reach of the previous station)
                t_ = max(pos + 20.0, target - 150.0)
                (cx, cy), d = _poly_at(path, t_)
                horiz = force_horiz or d in 'EW'
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
            if path_receipt is not None:path_receipt['stations'].append(dict(inst=it.name,master=it.master,box=list(it.box()),center=c,orientation=it.orient))
            cur, pos = c, max(t_, pos + 1.0)
        self.rec.append(dict(chain=name, lanes=list(lanes), stations=len(out), length_um=round(L, 1),
                             max_hop_um=round(max([h_ for _, _, h_ in out] + [_mh(cur, end)]), 1),
                             last_hop_um=round(_mh(cur, end), 1)))
        if path_receipt is not None:path_receipt['status']='CONSTRUCTED'
        return out


def MESO_P():
    # d8g1 (S81-RERUN fail-fast): GUARD_LO 1 gives the crossing arcs 1.5 T (meso / cfifo views SS -65..+14 at T/2)
    return ", .DEPTH(8), .OFFSET(4), .GUARD_LO(1), .GUARD_HI(7), .CREDITS(16)" if MESO_D8 else ''


HOP_FWD_CLS = ('lane',)
HOP_SKIP = ('clock_trunk', 'reset', 'reset_tree', 'clock', 'col_clock', 'col_reset', 'top_in', 'top_out', 'fclk', 'phy_dfi',
            'hbm_read', 'hbm_req', 'bfh')    # hbm_req (s81-gen --ctrl-rq): abutting controller faces, as hbm_read


def _half_extent(Mx, it, port):
    """half the extent of a port's (slice's) pins along its face, um (0 when unknown / real macro)"""
    p = Mx.ports.get(pslice(port)[0]) if Mx is not None else None
    lo_, hi_ = pslice(port)[1:]
    if p and p[0] == 'rects':
        pins_ = p[1] if lo_ is None else p[1][lo_:hi_ + 1]
        if not pins_:
            return 0.0
        xs = [(r[0] + r[2]) / 2 for _, _, r in pins_]
        ys = [(r[1] + r[3]) / 2 for _, _, r in pins_]
        return max(max(xs) - min(xs), max(ys) - min(ys)) / 2
    if p and p[0] == 'face':
        _, n_, face, ly_, c, pt_ = p
        if ly_ not in TRK:
            return 0.0
        nb = n_ if lo_ is None else (hi_ - lo_ + 1)
        return nb * TRK[ly_][1] * pt_ / 2
    return 0.0


def _anchor(Mx, it, port):
    """die coordinates of a port's anchor (generated face centre) on a placed instance; None for real macros"""
    p = Mx.ports.get(pslice(port)[0]) if Mx is not None else None
    if p and p[0] == 'rects':
        lo_, hi_ = pslice(port)[1:]
        pins_ = p[1] if lo_ is None else p[1][lo_:hi_+1]
        assert pins_, (it.name, port, 'no physical pin anchor')
        ax = sum((r[0]+r[2])/2 for _,_,r in pins_)/len(pins_)
        ay = sum((r[1]+r[3])/2 for _,_,r in pins_)/len(pins_)
        if it.orient in ('MY','R180'):
            ax = it.w-ax
        if it.orient in ('MX','R180'):
            ay = it.h-ay
        return it.x+ax,it.y+ay
    if not p or p[0] != 'face':
        return None
    _, n_, face, ly_, c, pt_ = p
    lo_, hi_ = pslice(port)[1:]
    if PEER_PIN_POS and lo_ is not None and hi_ is not None and n_ > (hi_ - lo_ + 1) and ly_ in TRK:
        # s81-die v16: the anchor of a SLICE of a port is the centre of that slice's pins, not of the whole group
        # (v16 run 2: the outer slices of the 8,192-b y_d group, 786 um of pins, were anchored at the group centre,
        # up to 344 um from their own lane, so --pin-relay added an off-lane relay behind the lane's last station)
        st_ = TRK[ly_][1] * pt_
        c = c - n_ * st_ / 2 + (lo_ + hi_ + 1) / 2.0 * st_
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
    pair = None
    if HOP_PAIR:
        # --hop-pair (s81-die v18, 10-14): plan against the hop's OWN pair limit (pair_check.Gate on the real views, the
        # limit the gate judges), not only the flat --hop-r-cc.  xsp1: 36,224 ret_leaf bits between two CLOSED rly_63
        # relays were 472.8-500 um (anchors under 500, real pair reach 472-478) and got no stage.  The margin covers the
        # pin spread around the anchor (gate = worst bit, plan = group anchor).
        sys.path.insert(0, str(ROOT / 'tools' / 'hier_contract'))
        import pair_check as PC
        pair = PC.Gate(default_um=HOP_GATE_UM or 500.0,
                       buses=[(b_, c_, n_, [(e_[0], pslice(e_[1])[0]) for e_ in eps_]) for b_, c_, n_, eps_ in m['buses']])
    for bid, cls, bits, eps in m['buses']:
        if cls in HOP_SKIP or len(eps) < 2 or eps[0][0] == 'TOP':
            continue
        d = by[eps[0][0]]
        a = _anchor(M.get(d.master), d, eps[0][1]) or (d.x + d.w / 2, d.y + d.h / 2)
        R0_ = HOP_R_FWD if cls in HOP_FWD_CLS else HOP_R_CC
        for e in eps[1:]:
            if e[0] == 'TOP':
                continue
            l_ = by[e[0]]
            b = _anchor(M.get(l_.master), l_, e[1]) or (l_.x + l_.w / 2, l_.y + l_.h / 2)
            L = _mh(a, b)
            hard = PIN_RELAY and not (is_glue(d.master) and is_glue(l_.master))
            # --hop-r-hub: only the BRIDGES (a slab pin at one end); station-to-station hops of a chain keep --hop-r-cc
            R = HOP_R_HUB if (cls == 'hub' and HOP_R_HUB and not (is_glue(d.master) and is_glue(l_.master))) else R0_
            if pair is not None and cls not in HOP_FWD_CLS:
                lim_ = pair.limit(d.name, d.master, pslice(eps[0][1])[0], l_.name, l_.master, pslice(e[1])[0])
                if lim_ < pair.default:          # a real (judged) pair limit; placeholders keep the flat rule
                    R = min(R, lim_ - HOP_PAIR)
            if HOP_SPREAD and cls == 'hub' and bits >= HOP_SPREAD:
                sp_ = _half_extent(M.get(d.master), d, eps[0][1]) + _half_extent(M.get(l_.master), l_, e[1])
                R = max(R - sp_, 120.0)
                HOP_SPREAD_R[(eps[0][0], eps[0][1], e[0], e[1])] = R
            if L > R or (hard and L > PIN_SEG):
                plan[(eps[0][0], eps[0][1], e[0], e[1])] = (round(L, 1), a, b, cls)
                if pair is not None:
                    HOP_PLAN_R[(eps[0][0], eps[0][1], e[0], e[1])] = R
    return plan


def collective_variant_binding():
    """Carry the actual candidate interface into downstream assembly selection."""
    return dict(coll_split3=COLL_SPLIT3, coll_split3_cr=COLL_SPLIT3_CR, coll_mtp_lane=COLL_MTP_LANE, coll_p2_lane=COLL_P2_LANE,
                collective_composition=COLL_SPLIT3_COMP if COLL_SPLIT3 else None)


def build_r8(variant=None):
    global HOP_PLAN
    if HOP_FIX and HOP_PLAN is None:
        HOP_PLAN = {}
        ALIGN_EXT[0] = False     # r8: planning passes align single stations only (the r7 rule)
        m0 = build_r8(variant)
        finalize_r8(m0)
        HOP_PLAN = hop_plan(m0)
        RLY_FACES.clear()
        for it_ in range(HOP_ITER):
            # --hop-iter N (s81-die v18, 10-14): the pass-2 build moves relays (hop-fix stations change the occupancy the
            # column relays and the relay-progress fix see), so a hop pass 1 never had can come out over its limit
            # (xsp2: rt_<c>_2b_y3 517-527 um on all 128 frames, unplanned).  Re-plan on the built die and rebuild until
            # no new over-limit hop appears (each hop keeps its first plan; register counts only grow where geometry
            # needs a stage).
            m1 = build_r8(variant)
            finalize_r8(m1)
            add_ = {k_: v_ for k_, v_ in hop_plan(m1).items() if k_ not in HOP_PLAN}
            RLY_FACES.clear()
            print('OT_HOP_ITER %d new planned hops %d' % (it_ + 1, len(add_)), file=sys.stderr)
            if not add_:
                break
            HOP_PLAN.update(add_)
        ALIGN_EXT[0] = True      # the built die: rigid runs / partial moves / spread entry (all re-judged, <= 450 um)
    variant = dict(variant or {})
    W, H = DIE
    insts, regions, notes = [], [], []
    bounds, bfs, nvs = region_bounds(), bf_sites(), nv_sites()
    COLS8 = max(TIER_COLS8)
    x_lw = up(EDGE, GX)
    slack = W - 2 * x_lw - 2 * LINK_COL - 2 * COLS8 * COL_PITCH8 - SPINE_W8 - 2 * SPF
    assert slack >= 0, ("die columns exceed the die width (--tier-cols / --bf-hier)", slack, TIER_COLS8, COL_PITCH8)
    x_fw = up(x_lw + LINK_COL + 0.5 * slack, GX)
    x_sp = up(x_fw + COLS8 * COL_PITCH8 - 8.64 + SPF, GX)       # spine W edge
    x_fe = up(x_sp + SPINE_W8, GX)                                # spine E edge
    x_le = dn(W - EDGE - LINK_COL, GX)
    assert x_fe + SPF + COLS8 * COL_PITCH8 <= x_le + 1e-6
    band = up(EDGE, GY) + PHY_H + 8.64 + CTRL_D + 8.64 + SVC_D
    SLOT_H, SLOTS = slot_geometry()
    FRAME_H = column_height()
    field_h = TIERS * FRAME_H + sum(chh(t_) for t_ in range(TIERS + 1))
    y_f = up((H - field_h) / 2, GY)
    ch_y = [y_f + t * FRAME_H + sum(chh(t_) for t_ in range(t)) for t in range(TIERS + 1)]
    tier_y = [c + chh(t) for t, c in enumerate(ch_y[:TIERS])]
    y_top = ch_y[TIERS] + chh(TIERS)

    def col_x(half, c):
        return dn(x_sp - SPF - (c + 1) * COL_PITCH8 + 8.64, GX) if half == 'W' else up(x_fe + SPF + c * COL_PITCH8, GX)
    geo = dict(slot_h=SLOT_H, slots=SLOTS, frame_h=FRAME_H, q_elem_frame_h=Q_ELEM_FRAME_H, x_lw=x_lw, x_fw=x_fw, x_sp=x_sp, x_fe=x_fe, x_le=x_le, y_f=y_f, y_top=y_top, ch_y=ch_y, tier_y=tier_y,
               band_depth=band, field_h=field_h, spine_cx=x_sp + SPINE_W8 / 2, col_x=col_x, col_pitch=COL_PITCH8,
               col_w=COL_W8, spf=SPF, tier_cols=list(TIER_COLS8))
    rq, rc = real_lef(Q_LEF), real_lef(CFG_LEF)
    frames, slot_of = {}, {}
    order = [(h, t, c) for h in 'WE' for t in range(TIERS) for c in range(TIER_COLS8[t])]
    assert len(order) == ROOTS
    rng, hbf = frame_plan_r8()
    canonical_frames = None
    if CANONICAL_LAYOUT is not None:
        from s81.canonical_layout import geometry as canonical_geometry
        canonical_frames = canonical_geometry(sys.modules[__name__], CANONICAL_LAYOUT, order)
    RSV_RECTS.clear()
    XSITES.clear()
    for r, (half, t, c) in enumerate(order):
        x0, y0 = col_x(half, c), tier_y[t]
        frame_h = FRAME_H
        frames[r] = dict(half=half, tier=t, col=c, x=x0, y=y0)
        if canonical_frames is not None:
            frames[r].update(canonical_frames[r])
            x0, y0, frame_h = frames[r]['x'], frames[r]['y'], frames[r]['h']
        frame_street_top = y0 if canonical_frames is not None else ch_y[t] + chh(t)
        regions.append(dict(name=f'frame_{r}', kind='field', rect=[x0, y0, x0 + COL_W8, y0 + frame_h]))
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
            insts.append(Inst(f'cf{r}', 'dsfd_cfifo', x0 + CF_X, frame_street_top - 4.32 - CF_WH[1], CF_WH[0] - SHAVE,
                              CF_WH[1] - SHAVE, kind='cfifo', region=f'frame_{r}'))
            continue
        pairs = list(range(*rng[r]))
        elems, offsets, heights = pack_frame(pairs, bfs, nvs)
        slot = len(heights) - 1
        assert sum(heights) <= frame_h + 1e-6, f'frame {r}: mixed slots exceed field height'
        frames[r].update(slot_offsets=offsets, slot_heights=heights)
        assert slot < SLOTS, f'frame {r}: {len(pairs)} pairs need {slot + 1} slots > {SLOTS} at slot height {SLOT_H}'
        assert 2 * len(pairs) - 1 <= int(frame_h / NODE_FRAME[1] + 1e-6), f'frame {r}: return strip overflow'
        frames[r]['elems'] = elems
        frames[r]['last_slot'] = slot
        for p, kind, s, ln in elems:
            sy = y0 + offsets[s]
            ex = x0 + (LANE_W if ln == 'R' else 0) + 4.32
            if kind == 'NV':
                it = Inst(f'e{p}', 'dsfd_bfnv', ex, sy + ELEM_DY, 1002.888, ELEM_FRAME_H - SHAVE, kind='bf_nv',
                          region=f'frame_{r}')
                nh = up(NVX_UM2 / 1002.888, GY)
                insts.append(Inst(f'v{p}', 'dsfd_nvx', ex, sy + SLOT_H + CFG_DY, 1002.888, nh - SHAVE, kind='nvx',
                                  region=f'frame_{r}'))
            elif kind == 'BF' and BF_HIER:
                cw_ = BF_HIER
                insts.append(Inst(f'e{p}w', 'dsfd_bf_col', ex, sy + ELEM_DY, cw_, BF_ROUTE_H, 'R0', kind='bfcol',
                                  region=f'frame_{r}'))
                insts.append(Inst(f'e{p}e', 'dsfd_bf_col', ex + cw_ + BF_FRONT_W + 2 * BF_SEAM_UM, sy + ELEM_DY, cw_, BF_ROUTE_H, 'MY',
                                  kind='bfcol', region=f'frame_{r}'))
                it = Inst(f'e{p}', 'dsfd_bf_front', ex + cw_ + BF_SEAM_UM, sy + ELEM_DY, BF_FRONT_W, BF_ROUTE_H, kind='bf',
                          region=f'frame_{r}')
            elif kind == 'BF':
                it = Inst(f'e{p}', 'dsfd_bf', ex, sy + ELEM_DY, 1002.888, ELEM_FRAME_H - SHAVE, kind='bf', region=f'frame_{r}')
            else:
                assert rq['h'] <= (Q_ELEM_FRAME_H or ELEM_FRAME_H), (rq['h'], Q_ELEM_FRAME_H or ELEM_FRAME_H)
                it = Inst(f'e{p}', rq['name'], ex, sy + ELEM_DY, rq['w'], rq['h'], 'MY' if (Q_X1B and ln == 'R') else 'R0', kind='q', region=f'frame_{r}')
            insts.append(it)
            slot_of[p] = (r, s, ln)
            # L lane / BF: ROMs (mirrored, pins east) then the sequencer, east of them, toward the slot station;
            # R lane: the sequencer (mirrored) first, west of its ROMs (pins west), facing the station on its west
            if ln == 'R':
                sx = x0 + LANE_W + R_CFGX
                cx0, ro, so = sx + SEQ_WH[0] + 3.888, 'R0', 'MY'
                rsx_ = cx0 - 3.888                       # --xb-rgap site: W edge (default: between sequencer and ROM 0)
                if XB_RGAP and XB_RGAP_FIRST:
                    # --xb-rgap-first (s81-die v17): slot station | x relay site | sequencer | ROMs.  The site stood E of
                    # the sequencer, 64 um from the station: its relays (real views launch at o 222-229 ps: reach
                    # 398-407 um) were 490 / 426 um from the next station's xai / xbi and 423-440 um from the left
                    # bank.  Beside the station the same relays are 38 um closer to all three loads, and the
                    # sequencer abuts ROM 0 again (its ROM nets no longer cross the site).
                    rsx_, sx = sx - 3.888, sx + XB_RGAP
            else:
                cx0, ro, so = x0 + 4.32, 'MY', 'R0'
                sx = cx0 + (CFG_PER_PAIR - 1) * CFG_PITCH + rc['w'] + 3.888
            if CFG_RGAP and ln == 'R':
                gx0 = cx0 + (CFG_RGAP_AT - 1) * CFG_PITCH + rc['w']
                RSV_RECTS.append((gx0 + XB_RGAP, sy + CFG_DY, cx0 + XB_RGAP + CFG_RGAP_AT * CFG_PITCH + CFG_RGAP,
                                  sy + CFG_DY + rc['h'], 'rt'))
            if XB_RGAP and ln == 'R':
                RSV_RECTS.append((rsx_ + 2.16, sy + CFG_DY, rsx_ + 3.888 + XB_RGAP - 2.16, sy + CFG_DY + rc['h'], 'x'))
            for j in range(CFG_PER_PAIR):
                gx_ = (CFG_RGAP if (ln == 'R' and j >= CFG_RGAP_AT) else 0.0) + (XB_RGAP if ln == 'R' else 0.0)
                insts.append(Inst(f'c{p}_{j}', rc['name'], cx0 + j * CFG_PITCH + gx_, sy + CFG_DY, rc['w'], rc['h'], ro,
                                  kind='cfg', region=f'frame_{r}'))
            # s81-die-rtl-bind 2026-10-14: the BF pair's element (ot_s81_bf_front) has no PQ loader handshake, so its
            # sequencer is the PQ 0 loader master ot_s81_cfg7_seq_bf (no ef / go_tag pins); q pairs keep
            # ot_s81_cfg7_seq, elaborated PQ 1 when the q element is the PQ element (die.v.params.json)
            seq_m_ = 'ot_s81_cfg7_seq_bf' if (RTL_BIND and kind == 'BF') else 'ot_s81_cfg7_seq'
            insts.append(Inst(f's{p}', seq_m_, sx, sy + CFG_DY, SEQ_WH[0] - SHAVE, SEQ_WH[1] - SHAVE, so,
                              kind='seq', region=f'frame_{r}'))
        # slot stations (one per used slot), above the NV extension in an NV slot
        nvslots = {s + 1 for p, kind, s, ln in elems if kind == 'NV'}
        if slot in nvslots:
            slot -= 1                  # a top slot holding only an NV extension needs no station
            frames[r]['last_slot'] = slot
            frames[r]['nv_top'] = True
        for s in range(slot + 1):
            sy = y0 + offsets[s]
            yy = sy + CFG_DY if s not in nvslots else sy + CFG_DY + up(NVX_UM2 / 1002.888, GY) + 4.32
            insts.append(Inst(f't{r}_{s}', 'dsfd_sstn', x0 + SSTN_X, yy, SSTN_WH[0] - SHAVE, SSTN_WH[1] - SHAVE,
                              kind='sstn', region=f'frame_{r}'))
            if X_SITE_PAIR and s not in nvslots:
                # --x-site-pair: two owned relay sites in the gap E of the station (lower = xa, upper = xb)
                rw_, rh_ = relay_dims(X0B, True)
                sx_ = up(x0 + SSTN_X + SSTN_WH[0] + 0.432, GX)
                ylo_ = yy
                yhi_ = up(ylo_ + rh_ + 0.432, GY)
                assert XB_RGAP, '--x-site-pair needs --xb-rgap'
                assert sx_ + rw_ + 0.432 <= x0 + LANE_W + R_CFGX + XB_RGAP + 1e-6, ('--x-site-pair: gap too narrow', r, s, sx_)
                assert yhi_ + rh_ <= sy + CFG_DY + rc['h'] + 1e-6, ('--x-site-pair: band too short', r, s, yhi_)
                XSITES[(r, s)] = [(sx_, ylo_), (sx_, yhi_)]
                for xs_, ys_ in XSITES[(r, s)]:
                    RSV_RECTS.append((xs_, ys_, xs_ + rw_, ys_ + rh_, 'xs'))
        if REV == 'r9':
            for p, kind, s, ln in elems:
                if kind == 'q':
                    insts += _q_banks(p, x0 + (LANE_W if ln == 'R' else 0) + 4.32, y0 + offsets[s] + ELEM_DY, rq,
                                      f'frame_{r}', mirror=Q_X1B and ln == 'R')
        nodes, root = return_tree(2 * len(pairs))
        frames[r]['tree'] = (nodes, root)
        rank = _inorder_rank(nodes, root)
        for j, (nid, a, b) in enumerate(nodes):
            insts.append(Inst(f'n{r}_{j}', 'dsfd_node', x0 + LANES_W + 4.32, y0 + rank[nid] * NODE_FRAME[1],
                              NODE_FRAME[0] - SHAVE, NODE_FRAME[1] - SHAVE, kind='node', region=f'frame_{r}'))
        # column FIFO: entry meso + column clock / reset root + return register, top band of the channel below
        # (--pq-place: below the root row, which takes the channel's top PQ_ROOT_ROW)
        pq_dy = PQ_ROOT_ROW if PQ_ROOTS else 0.0
        insts.append(Inst(f'cf{r}', 'dsfd_cfifo', x0 + CF_X, frame_street_top - pq_dy - 4.32 - CF_WH[1], CF_WH[0] - SHAVE,
                          CF_WH[1] - SHAVE, kind='cfifo', region=f'frame_{r}'))
        if PQ_ROOTS:
            # S81-DIE PQ root row: N station (tree word in) / ret_root_r128 / S station (root word out), centred in the
            # 142.56 um return strip (node strip + rstg sub-column) directly under the frame
            yr = frame_street_top - PQ_ROOT_ROW
            xr = up(x0 + LANES_W + (NS_W + RSC_W - PQ_ROOT_WH[0]) / 2, GX)
            insts.append(Inst(f'pqs{r}', 'dsfd_rstg_pq%d' % PQ_RO, xr, yr + 4.32, PQ_ROOT_WH[0] - SHAVE, PQ_STN_H - SHAVE,
                              kind='pqstn', region=f'frame_{r}'))
            insts.append(Inst(f'pqr{r}', 'dsfd_pq_root', xr, yr + 4.32 + PQ_STN_H, PQ_ROOT_WH[0] - SHAVE,
                              PQ_ROOT_WH[1] - SHAVE, kind='pqroot', region=f'frame_{r}', power_w=PQ_ROOT_W))
            insts.append(Inst(f'pqn{r}', 'dsfd_rstg_pq%d' % PQ_TI, xr, yr + 4.32 + PQ_STN_H + PQ_ROOT_WH[1],
                              PQ_ROOT_WH[0] - SHAVE, PQ_STN_H - SHAVE, kind='pqstn', region=f'frame_{r}'))
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
    su_area = SU_AREA_MM2 if SU_AREA_MM2 is not None else HUB_MM2['su']
    centre = ['gather', 'vm', 'capture', 'collective']
    centre_area = dict(HUB_MM2)
    if CTRL_SLAB:
        from uarch_model import s81_ctrl_die_model
        ctrl_model = s81_ctrl_die_model(cw, CTRL_ROLE)
        centre.insert(centre.index('collective'), 'stage_ctrl')
        centre_area['stage_ctrl'] = ctrl_model['area_mm2_nominal']
    wfc_rect = None
    if DIE_KIND == 'layer':
        centre.insert(2, 'wfc')
        centre_area.update(vm=2.659905216, wfc=0.45610905599999996)
    if PQ_PLACE:          # S81-DIE: the PQ core slot right after the VM (VM read by its N face -> core S face)
        centre.insert(centre.index('vm') + 1, 'pq')
        centre_area['pq'] = PQ_CORE_H * cw / 1e6
    if HOST_SLAB:         # s81-dies / ingest RQ-ING-1: dsfd_host (ot_rom_host_ingest ROWS / IKEY / CSR) beside the collective
        centre.insert(centre.index('collective') + 1, 'host')
        centre_area['host'] = HOST_MM2
        if FWD_IFACE:     # s81-gen: forwarded host-write lanes (580 + 20 b each way per stack) need face (layer1e: 67 > 58 um)
            centre_area['host'] = max(HOST_MM2, HOST_FACE_UM * cw / 1e6)
    if VM_FACE_MM2 and centre_area['vm'] < VM_FACE_MM2:
        # S81-RERUN v9e (OWNER rule 3, coordinator 2026-10-07): the head die's VM slab (0.89 mm2, ~880 um tall) took
        # every end block / pin relay on its E face (v9d head GRT: the last 5 overflowing gcells, ha_* / hsel / hq /
        # capture buses at the VM face); the slab grows to the layer die's VM outline so its face spreads them
        centre_area['vm'] = VM_FACE_MM2
    wfc_die = WFC_HARD and DIE_KIND in LAYER_KINDS and not DRAFT_SIDE
    if wfc_die:
        # MTP-DIE: the bound WFC slab (real master dsfd_wfc) on every layer-class die, after the capture (its
        # core_start / done / result endpoint), next to the collective (stage link in / out) and one slab from the VM
        if 'wfc' in centre:
            centre.remove('wfc')
        centre.insert(centre.index('capture') + 1, 'wfc_hard')
        centre_area['wfc_hard'] = WFC_SLAB_H * cw / 1e6
        if STAGE_SEQ:   # main decision A (2026-10-11): the stage start / done passes dsfd_stage_seq to the engines
            centre.insert(centre.index('wfc_hard') + 1, 'sseq')
            # --ctrl-adapters (s81die-1011/ctrl): dsfd_stage_seq_c carries 12 x (85 + 9 + 2) engine pins + 3 async FIFOs:
            # 0.06 mm2 gave a 37 um slab whose E face could not hold the pins (40 um): 0.15 mm2 (~87 um tall)
            centre_area['sseq'] = max(SSEQ_MM2, 0.15) if CTRL_ADAPTERS else SSEQ_MM2
    if MTP_SEQ and DIE_KIND == 'head':
        centre.insert(centre.index('capture') + 1, 'mtp')
        centre_area['mtp'] = MTP_SEQ_MM2
        if MTP_EP:   # mtp-wfc 2026-10-10 (fixlat a7961fc6d): RTT-sized sequencer partner ends beside capture / VM
            centre.insert(centre.index('vm') + 1, 'vm_ep')
            centre.insert(centre.index('capture') + 1, 'cap_ep')
            centre_area['vm_ep'] = centre_area['cap_ep'] = MTP_EP_MM2
    if HROW_SRC is not None:
        # mtp-dsbind 2026-10-11 (--hrow-src P): the hidden-row source on the stage die of layer 37 + P (rank k), beside the
        # WFC kit (its t_hep issue-epoch events) and one slab from the VM (HC-mean row reads); its lane leaves through
        # the collective (one dedicated hidden lane to the DSpark primary P.k)
        centre.insert(centre.index('collective'), 'hrsrc')
        centre_area['hrsrc'] = up(HSRC_UM[1] + 2 * WFC_HALO, GY) * cw / 1e6
    if SEEDL:
        # mtp-dsbind 2026-10-10 (--seedl, DSpark primary die): the seed-descriptor consumer dsfd_mtp_seed_launch beside
        # the collective (its seed descriptor arrives on the collective's MTP lane, --coll-mtp-far primary) and one
        # slab from the VM (hidden-row reads, x beats to the seed elements, program start)
        centre.insert(centre.index('collective'), 'seedl')
        centre_area['seedl'] = up(SEEDL_UM[1] + 2 * WFC_HALO, GY) * cw / 1e6
    if DRAFT_SIDE == 'A':
        # MD-2 P2 (mtp-draftdie 2026-10-09): the selected-path transport (ot_mtp_p2_prefix_path: PRIMARY_SHARED1
        # 9-SRAM ordered transport + 3-SRAM 16-lane A-prefix + native publisher) on the A die of every draft row
        # package, between the capture (unused on a draft die: no pipeline stage) and the collective (board link
        # from the primary head die + the in-package UCIe from die B): it sums the row's experts in id order
        centre.insert(centre.index('collective'), 'p2')
        centre_area['p2'] = P2_SLAB_MM2
        if P2_LNK:   # mtp-wfc 2026-10-10 (fixlat a7961fc6d): the P2 slab is the core + its RTT-sized link pair
            centre.insert(centre.index('collective'), 'p2_lnk')
            centre_area['p2_lnk'] = P2_LNK_MM2
    if wfc_die or (MTP_SEQ and DIE_KIND == 'head'):
        # the capture slab (0.109 mm2, ~63 um tall) cannot take the WFC / sequencer endpoint pins on its E face
        # (first --wfc-hard check: 66 um of pins > 65): the slab grows to CAPTURE_FACE_UM so its face spreads them
        centre_area['capture'] = max(centre_area['capture'], CAPTURE_FACE_UM * cw / 1e6)
    if COLL_SPLIT3:   # s81-gen (redesign-ds 19:54): the collective slab takes the split3 composition outline
        cs_ = json.loads((ROOT / COLL_SPLIT3_COMP).read_text())['slab_um']
        assert cs_[0] <= cw + 1e-6, ('collective split3 slab wider than the hub column', cs_, cw)
        slab_w = {'collective': up(cs_[0], GX)}
        centre_area['collective'] = slab_w['collective'] * up(cs_[1], GY) / 1e6
    else:
        slab_w = {}
    if SUHC_1011:   # capture -> SU g/u pins on the capture E face (draft dies: 109 um of pins > the 65 um face)
        centre_area['capture'] = max(centre_area['capture'], CAPTURE_FACE_UM * cw / 1e6)
    if SUHC_1011 and not COLL_SPLIT3:
        # --suhc-1011: the collective E face carries the 8 x 1,024-b y lanes to HC on top of its links / VM / host pins
        # (layer1e: 840 um of pins > the 806 um face): the slab grows to COLL_FACE_UM tall (same area rule as capture)
        centre_area['collective'] = max(centre_area['collective'], COLL_FACE_UM * cw / 1e6)
    if COLL_SLAB_H and not COLL_SPLIT3:
        # --coll-slab-h (s81die-1011 hier contract v1): hierarchical collective (lane tiles W, core column 1,360.8: cb parent
        # 972.4 x 423.4 + ce parent + ct) at full column width; the W column has ~5.8 mm free height above the host
        centre_area['collective'] = max(centre_area['collective'], up(COLL_SLAB_H, GY) * cw / 1e6)
    if VM_SLAB:   # --vm-slab W,H (s81-vm-1011): the VM master outline (NP24 bgq tiles), centred in the hub column
        assert VM_SLAB[0] <= cw + 1e-6, ('--vm-slab wider than the hub column', VM_SLAB, cw)
        slab_w['vm'] = up(VM_SLAB[0], GX)
        centre_area['vm'] = slab_w['vm'] * up(VM_SLAB[1], GY) / 1e6
    if CONTRACT_SLABS:
        # --contract FILE (s81-die-iter 2026-10-12): centre hard elements keep their contract outline (w x h) inside a
        # hub column widened for the v3 SU / HC slabs (column channels); each is centred in the column
        for n_, (w_, h_) in CONTRACT_SLABS.items():
            if n_ in centre_area and n_ not in ('su_s', 'hc_s'):
                assert w_ <= cw + 1e-6, ('contract slab wider than the hub column', n_, w_, cw)
                slab_w[n_] = up(w_, GX)
                centre_area[n_] = slab_w[n_] * up(h_, GY) / 1e6
    # --ecol-slabs (ds-1010/s81die 2026-10-10): W-column centre slabs moved to a sub-column of the E (HC) column, beside
    # the HC slabs, next to the crossing corridor (the W column overflowed: split3cr collective + WFC kit + host)
    if RTL_HUB_WIDTHS:
        # s81die-1011/ctrl (die lead decision, order A): bottom-up SU floor -> VM -> capture -> gather -> PQ -> the rest
        # (WFC kit, sequencer, collective, host in their order): SU <-> VM row slots (~17.1 kb), capture -> VM 13,376 b
        # and gather -> capture 6,947 b (12 root lanes) abut; gather <-> PQ stays adjacent; the gather's VM phase words
        # cross only the capture slab (a short staged chain)
        head_ = [n for n in ('vm', 'capture', 'gather', 'pq') if n in centre]
        centre[:] = head_ + [n for n in centre if n not in head_]
    ecol = [n for n in centre if n in ECOL_SLABS or (n == "wfc_hard" and "wfc" in ECOL_SLABS)]
    centre = [n for n in centre if n not in ecol]
    def put(n, x0_, yy, w0_):
        nonlocal wfc_rect
        if n == 'stage_ctrl':
            master = 'dsfd_sp_ctrl' + ('_src' if CTRL_ROLE == 'source' else '_h' if CTRL_ROLE == 'head' else '')
            slab(n, centre_area[n], x0_, yy, w0_, master=master)
            notes.append('S81 stage controller: native shell %s; 1.2 GHz, %.3f mm2 nominal, physical closure pending' % (master, CTRL_MM2))
        elif n == 'wfc_hard' and WFC_KIT:
            # mtp-wfc 2026-10-10 (--wfc-kit): the slab master is the WFC kit itself (rtl/dsrom_sys/mtp/dsfd_wfc_kit.sv:
            # the closed tokpipe core + lnk + vmx (+ tok_hard on the source die), wired element to element inside it,
            # every element boundary registered), on exact die-facing ports (wfc_kit_buses).  First try (sub-instances
            # in the slab) left the hub chains no station spot inside the partly empty slab region (11:27 PT).
            # --wfc-crp (main 10-11): the slab master is dsfd_wfc_cr2 = the routed credit-boundary tile dsfd_wfc_crp at the
            # slab's die edge (every die link / VM signal lands in its pin flops / SRAM landing) + the kit behind it
            ms_ = 'dsfd_wfc_cr2' if WFC_CRP else ('dsfd_wfc_src' if WFC_ROLE == 'source' else 'dsfd_wfc_stg')
            slab('wfc', centre_area[n], up(x0_ + (w0_ - slab_w.get(n, w0_)) / 2, GX), yy, slab_w.get(n, w0_), master=ms_)
            notes.append('MTP-WFC --wfc-kit (%s): %s = %s in a %.2f um slab (%.3f mm2)' % (
                WFC_ROLE, ms_, 'SOURCE tokpipe + tok_hard + lnk + vmx' if WFC_ROLE == 'source' else 'STG tokpipe + lnk + vmx',
                WFC_SLAB_H, centre_area[n]))
        elif n == 'wfc_hard':
            slab('wfc', centre_area[n], x0_, yy, w0_, master='dsfd_wfc')
            notes.append('MTP-DIE --wfc-hard: dsfd_wfc = closed SOURCE ot_dsrom_wfc_tokpipe_src %s um (910e67c7b) + closed '
                         'STG tokpipe %s um (9f7a7f35e) in a %.2f um slab (%.3f mm2 gross)'
                         % (WFC_SRC_UM, WFC_STG_UM, WFC_SLAB_H, centre_area[n]))
        elif n == 'p2':
            slab('p2', centre_area[n], x0_, yy, w0_, master='dsfd_p2')
            notes.append('MD-2 --draft A: dsfd_p2 = ot_mtp_p2_prefix_path (selected P2 path, 12 SRAMs) %.4f mm2 '
                         '(the larger first-route outline %s um)' % (centre_area[n], P2_OUTLINE_UM))
        elif n == 'sseq':
            slab('sseq', centre_area[n], x0_, yy, w0_, master='dsfd_stage_seq')
            notes.append('option A: dsfd_stage_seq (ot_s81_stage_seq) %.3f mm2: kit start / done <-> engine cmd / dn' % centre_area[n])
        elif n in ('vm_ep', 'cap_ep', 'p2_lnk'):
            ms_ = dict(vm_ep='dsfd_vm_mtp_ep', cap_ep='dsfd_cap_mtp_ep', p2_lnk='dsfd_p2_lnk')[n]
            slab(n, centre_area[n], x0_, yy, w0_, master=ms_)
            notes.append('fixlat partner end %s (%s) %.3f mm2' % (n, ms_, centre_area[n]))
        elif n == 'hrsrc':
            slab('hrsrc', centre_area[n], x_sp, yy, cw, master='dsfd_mtp_hrow_src')
            notes.append('MTP-DIE --hrow-src %d: dsfd_mtp_hrow_src (layer %d HC-mean row -> primary die) %.3f mm2'
                         % (HROW_SRC, 37 + HROW_SRC, centre_area[n]))
        elif n == 'seedl':
            slab('seedl', centre_area[n], x0_, yy, w0_, master='dsfd_mtp_seed_launch')
            notes.append('MTP-DIE --seedl: dsfd_mtp_seed_launch (seed descriptor -> seed program, contract %s um) %.3f mm2'
                         % (SEEDL_UM, centre_area[n]))
        elif n == 'mtp':
            slab('mtp', centre_area[n], x0_, yy, w0_, master='dsfd_mtp_seq_rtt' if MTP_SEQ_RTT else 'dsfd_mtp_seq')
            notes.append('MTP-DIE --mtp-seq: dsfd_mtp_seq = ot_dsrom_mtp_seq (accept + draft-chain sequencer) %.3f mm2'
                         % centre_area[n])
        elif n == 'wfc':
            wh = up(centre_area[n] * 1e6 / w0_, GY)
            wfc_rect = [x0_, yy, x0_ + w0_, yy + wh]
        elif n == 'pq':
            # core slab W of a ROM column at the slot's E end (2 phase + 1 stream ot_rom_4096x72, real LEF, mirrored
            # so their pins face the core); the slab carries the core budget (results/uarch/
            # dsrom_s81_pq_fullshape_design_20261007 design.json pq_core: 0.32 mm2 est. incl. 36 SRAM macros)
            rc_ = real_lef(CFG_LEF)
            romc = up(rc_['w'] + 2 * 8.64, GX)
            wc_ = dn(cw - romc, GX)
            slab('pq', PQ_CORE_H * wc_ / 1e6, x_sp, yy, wc_, master=PQ_RTL_MASTER if RTL_BIND else None)
            for j in range(PQ_ROMS):
                insts.append(Inst(f'pqrom{j}', rc_['name'], x_sp + wc_ + 8.64, yy + 8.64 + j * up(rc_['h'] + 17.28, GY),
                                  rc_['w'], rc_['h'], 'R0', kind='pqrom', region='spine', domain='stream_1p2'))
        else:
            slab(n, centre_area[n], up(x0_ + (w0_ - slab_w.get(n, w0_)) / 2, GX), yy, slab_w.get(n, w0_), dom='serial_0p9' if n == 'vm' else 'stream_1p2',
                 master='dsfd_host' if n == 'host' else None)
    ch_ = sum(up(centre_area[n] * 1e6 / slab_w.get(n, cw), GY) for n in centre) + (len(centre) - 1) * SPINE_GAP
    yc = dn(mid - ch_ / 2, GY)
    su_lo = su_area * (yc - y_f) / (yc - y_f + y_top - (yc + ch_))
    # --contract (s81-die-iter, contract v4): a v2 SU wider than the hub column grows WEST (E edge on the column's E edge,
    # clear of the xE trunk / sseq stations by the VCH); the free strip W of the column holds it (10.5 um to the xW stations)
    su_w_ = up(SU_V2_UM[0], GX) if (SUHC_V2 and SU_V2_UM[0] > cw + 1e-6) else cw
    su_x_ = x_sp - (su_w_ - cw)
    if SU_E:
        # --su-e MM2 (ds-1010/s81die 2026-10-11): su_n (MM2) moves to the E column above hc_n; su_s (the rest) sits at the
        # W column floor with the centre stack right above it (the 2.42 mm VM of s81-vm-1011 overflowed the W column)
        su_lo = su_area - SU_E
        if SUHC_V2:     # the one v2 SU: its hierarchical outline (the su_s W-floor slot)
            su_lo = SU_V2_UM[0] * SU_V2_UM[1] / 1e6
        yc = up(band + SPINE_GAP + 4.32 + up(su_lo * 1e6 / su_w_, GY) + SPINE_GAP, GY)
    if HUB_SOUTH_SHIFT:
        assert SU_E and SUHC_V2, '--hub-south-shift requires --su-e and --suhc-v2'
        yc -= HUB_SOUTH_SHIFT
    # --rtl-hub-widths (order A): the SU's VM row slots (~17.1 kb) are face-to-face with the VM right above it
    su_gap = RTL_ABUT_GAP if (RTL_HUB_WIDTHS and SUHC_V2 and centre and centre[0] == 'vm') else SPINE_GAP
    slab('su_s', su_lo, su_x_, dn(yc - su_gap - up(su_lo * 1e6 / su_w_, GY), GY), su_w_, dom=SUHC_DOM)
    yy = yc
    for i_, n in enumerate(centre):
        put(n, x_sp, yy, cw)
        nx_ = centre[i_ + 1] if i_ + 1 < len(centre) else None
        # --rtl-hub-widths: the face-to-face wide pairs (VM <- capture 13,376 b, capture <- gather 6,947 b) sit RTL_ABUT_GAP
        # apart so their buses are direct register-to-register wires (SPINE_GAP 172.8 > the 155 um direct-hop limit)
        gap_ = RTL_ABUT_GAP if RTL_HUB_WIDTHS and {n, nx_} in ({'vm', 'capture'}, {'capture', 'gather'}) else SPINE_GAP
        if PQ_CNT and {n, nx_} == {'capture', 'gather'}:
            gap_ = PQ_CNT_SEAM       # --pq-cnt: the count leaves tile the gather | capture seam
        yy += up(centre_area[n] * 1e6 / slab_w.get(n, cw), GY) + gap_
    m_cnt = []
    if PQ_CNT:
        # --pq-cnt (s81-die r6b): the 12 count leaves under the t_capture pins of the roots they count, x from the slot
        # file relative to the gather slot, y centred in the seam (capture N face .. gather S face)
        g_, c_ = hub['gather'], hub['capture']
        assert c_.y < g_.y, ('--pq-cnt: capture must sit directly below gather (--rtl-hub-widths order)', c_.y, g_.y)
        s0_, s1_ = c_.y + c_.h, g_.y
        gx0_ = PQ_CNT['geometry']['gather_slot'][0]
        for sl_ in PQ_CNT['slots']:
            w_, h_ = sl_['outline'][0], PQ_CNT_LEAF_H
            assert h_ <= s1_ - s0_ + 1e-6, ('--pq-cnt: leaf taller than the seam', sl_['slot'], h_, s1_ - s0_)
            x_ = up(g_.x + (sl_['at_die'][0] - gx0_), GX)
            y_ = dn(s1_ - 2.16 - h_, GY)        # top of the seam: the taps from the gather S face are short
            assert y_ >= s0_ + 17.28 + 2.16, ('--pq-cnt: no relay row under the leaves', sl_['slot'], y_, s0_, s1_)
            assert x_ + w_ <= g_.x + g_.w + 1e-6, ('--pq-cnt: leaf outside the column', sl_['slot'], x_)
            it = Inst(sl_['slot'], sl_['master'], x_, y_, w_, h_, 'R0', kind='pqcnt', region='spine', domain='stream_1p2')
            insts.append(it)
            m_cnt.append((it, sl_))
        notes.append('--pq-cnt: %d count-only return leaves (rwbc15 / rwbc2) in the %.2f um gather | capture seam'
                     % (len(m_cnt), s1_ - s0_))
    if not SU_E and not SUHC_V2:
        slab('su_n', su_area - su_lo, x_sp, yy, cw, dom=SUHC_DOM)
    vm = hub['vm']
    corr_c = vm.y - SPINE_GAP / 2          # corridor at the gather / VM boundary: the E-half returns exit it at gather
    if HUB_SOUTH_SHIFT and SUHC_V2_HC_N and HC_T_UM:
        # The west hub column can move south without shrinking the closed east
        # HC tail. Retain its floor clearance; the longer VM bridge is judged
        # by the normal relay/pair gates, rather than hiding an overlap.
        floor_corr = band + SPINE_GAP + up(HC_T_UM[1], GY) + HC_CORR / 2 + GY
        corr_c = max(corr_c, up(floor_corr, GY))
    c0, c1 = dn(corr_c - HC_CORR / 2, GY), up(corr_c + HC_CORR / 2, GY)
    lo_av, hi_av = c0 - (band + SPINE_GAP), (H - band - SPINE_GAP) - c1      # HC halves sized to the room each side
    fs = lo_av / (lo_av + hi_av)
    # --ecol-slabs: the moved slabs stack upward from the corridor in an ECOL_W sub-column on the E column's W side
    # (toward the VCH and the W column); the HC halves narrow to the rest (taller) and keep abutting the corridor
    hcx, hcw = (up(x_spe + ECOL_W + 8.64, GX), dn(cw - ECOL_W - 8.64, GX)) if ecol else (x_spe, cw)
    if SU_E:   # hc_s fills the E column from the band floor to the corridor, hc_n the rest above it, su_n above hc_n
        fs = min(1.0, (c0 - (band + SPINE_GAP) - 4.32) * hcw / 1e6 / HUB_MM2['hc'])
    hs_ = up(HUB_MM2['hc'] * fs * 1e6 / hcw, GY)
    if SUHC_V2 and SUHC_V2_HC_N:
        # --suhc-v2 n (s81die-1011/ctrl): the one HC in the freed slot ABOVE the corridor, facing the VM rows (order A puts
        # the VM at the corridor): VM row slots run straight across the VCH, the collective's 8,192-b y is ~2.5 mm
        # shorter than to the floor slot (hb_collective_t_hc_y_hc_s: no station spot over a 7,451 um path)
        slab('hc_s', HC_V2_UM[0] * HC_V2_UM[1] / 1e6, hcx, c1 - HC_S_GROW_DOWN, up(HC_V2_UM[0], GX), dom=SUHC_DOM)
        if HC_T_UM:
            # contract v12 (s81-die-iter 2026-10-12): the 64 x 740.88 half-octet slots + root row (17,240 um) exceed the
            # E column above the corridor (12,655.5 um, die = full 26 mm field); the chain tails (7 / 5 / 7 slots) stand
            # in the empty E-column floor slot below the corridor, abutting it; hc_s S face -> hc_t N face per column
            ht_ = up(HC_T_UM[1], GY)
            assert c0 - ht_ >= band + SPINE_GAP, ('hc_t taller than the E-column floor slot', c0 - band - SPINE_GAP, ht_)
            slab('hc_t', HC_T_UM[0] * HC_T_UM[1] / 1e6, hcx, c0 - ht_, up(HC_T_UM[0], GX), dom=SUHC_DOM)
    elif SUHC_V2:   # the floor slot holds c0 - floor um: the 9,640 um HC outline fits only if the corridor sits above it
        assert c0 - (band + SPINE_GAP) >= HC_V2_UM[1], ('v2 HC outline taller than the hc_s floor slot: use '
                                                        '--suhc-v2-hc-north', round(c0 - band - SPINE_GAP, 1), HC_V2_UM)
        slab('hc_s', HC_V2_UM[0] * HC_V2_UM[1] / 1e6, hcx, dn(c0 - HC_V2_UM[1], GY), up(HC_V2_UM[0], GX), dom=SUHC_DOM)
    else:
        slab('hc_s', HUB_MM2['hc'] * fs, hcx, dn(c0 - hs_, GY), hcw, dom=SUHC_DOM)
    if not SUHC_V2:     # --suhc-v2: one HC (hc_s slot); the hc_n slot is free
        slab('hc_n', HUB_MM2['hc'] * (1 - fs), hcx, c1, hcw, dom=SUHC_DOM)
    if SU_E and not SUHC_V2:
        hn_ = hub['hc_n']
        ysn = up(hn_.y + hn_.h + SPINE_GAP, GY)
        if HROW_TX:   # --hrow-tx: the stage die's hidden-row sender between hc_n (its source) and su_n
            slab('hrtx', HRTX_UM[0] * HRTX_UM[1] / 1e6, up(x_spe + (cw - HRTX_UM[0]) / 2, GX), ysn, HRTX_UM[0],
                 dom='stream_1p2', master='dsfd_mtp_hrow_tx')
            ysn = up(ysn + HRTX_UM[1] + SPINE_GAP, GY)
            notes.append('--hrow-tx: dsfd_mtp_hrow_tx (ot_dsrom_mtp_hrow_tx) %s um above hc_n' % (HRTX_UM,))
        slab('su_n', SU_E, x_spe, ysn, cw, dom=SUHC_DOM)
        notes.append('--su-e: su_n %.3f mm2 in the E column above hc_n; su_s %.3f mm2 at the W column floor' % (SU_E, su_lo))
    ye = c1
    for n in ecol:
        put(n, x_spe, ye, ECOL_W)
        ye += up(centre_area[n] * 1e6 / ECOL_W, GY) + SPINE_GAP
        notes.append('--ecol-slabs: %s in the E-column sub-column (x %.2f, %.2f um wide)' % (n, x_spe, ECOL_W))
    regions.append(dict(name='hc_corridor', kind='channel', rect=[x_spe, c0, x_fe, c1]))
    for it in insts:
        if it.region == 'spine':
            # A south-grown SU uses the centre of the south band, while PHY,
            # control and service tiles occupy its shoreline columns. It must
            # remain inside the die and pass the actual-instance overlap gate;
            # requiring the entire centre to stay above the shoreline band
            # would reject the explicitly reserved south extension itself.
            floor_ = EDGE if HUB_SOUTH_SHIFT and it.name == 'sp_su_s' else band + SPINE_GAP
            assert it.y >= floor_ and it.y + it.h <= H - band - SPINE_GAP, (it.name, it.y, it.y + it.h)
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
            if HROW and st == 'SE' and st not in STACKS[DIE_KIND]:
                # mtp-dsbind 2026-10-10 (main decision (a): the store off the full hub spine): the main-hidden row
                # store in the FREE SE service slot of the 1-stack primary die (no PHY / ctrl / svc there; precedent:
                # layer1e eng_SE), at the slot's spine end; its field-facing (N) face carries every port
                hub['hrow'] = Inst(f'hrow_{st}', 'dsfd_mtp_hrow', up(xp, GX), up(ys_ + HROW_TOP_REF - HROW_UM[1], GY), HROW_UM[0], HROW_UM[1], 'R0',
                                   kind='svc', region='svc', power_w=0.4)
                insts.append(hub['hrow'])
                regions.append(dict(name=f'hrow_{st}', kind='svc', rect=[xp, min(ys_, ys_ + HROW_TOP_REF - HROW_UM[1]), xp + PHY_W, ys_ + SVC_D]))
                notes.append('MTP-DIE --hrow: hrow_SE = dsfd_mtp_hrow (main-hidden row store, 120 x 1024x256 SRAM in 3 '
                             'banked part arrays) %.1f x %.1f um in the free SE service slot' % HROW_UM)
                continue
            if st not in STACKS[DIE_KIND]:
                continue           # 1-stack layer die (scenario C): only the SW stack is built
            phys[st] = Inst(f'phy_{st}', rp['name'], xp, yp, rp['w'], rp['h'], orient, kind='phy', region='phy',
                            domain='hbm')
            ctrls[st] = Inst(f'ctrl_{st}', 'dsfd_ctrl', xp, yc_, PHY_W - SHAVE, CTRL_D - SHAVE, orient, kind='ctrl',
                             region='ctrl', domain='hbm')
            if DIE_KIND == 'layer1e' and st == 'SE':
                # layer1e: the Engram service in the SE service slot, centred on ctrl_SE's request face
                ex_ = up(xp + (PHY_W - ENG_WH[0]) / 2, GX)
                hub['eng'] = Inst(f'eng_{st}', 'dsfd_engram', ex_, ys_, ENG_WH[0], ENG_WH[1], orient, kind='svc',
                                  region='svc', power_w=0.6)
                insts += [phys[st], ctrls[st], hub['eng']]
                notes.append('layer1e: eng_SE = dsfd_engram (lookup + sink + prefetch SRAM + SE backend half) %.0f x %.0f um '
                             'in the SE service slot (Engram tables in HBM, owner 10-09)' % ENG_WH)
            else:
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
        if MTP_LINKS and (DIE_KIND == 'head' or DRAFT_SIDE == 'P' or COLL_MTP_FAR):     # MTP-DIE: draft fan-out SerDes, W gets the odd one
            stack += [('serdes', rs_)] * ((MTP_LINKS + (side == 'W')) // 2)
        if COLL_P2_LANE:      # mtp-colllane-1011: draft die A's dedicated P2 lanes: W4 board SerDes (primary), E4 UCIe (die B)
            stack += [('serdes', rs_)] if side == 'W' else [('ucie', ru_)]
        tot = sum(m_['h'] for _, m_ in stack) + (len(stack) - 1) * 43.2
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
    variant.update(tier_cols=list(TIER_COLS8) if TIER_COLS_SET else None, frames=ROOTS, lane_equal=LANE_EQUAL, q_x1b=Q_X1B, cfg_rgap=CFG_RGAP, cfg_rgap_at=CFG_RGAP_AT, xb_rgap=XB_RGAP, suhc_1011=SUHC_1011, su_e_mm2=SU_E or None, hrow_tx=HROW_TX, vm_slab=list(VM_SLAB) if VM_SLAB else None, coll_slab_h=COLL_SLAB_H, ecol_slabs=list(ECOL_SLABS), ecol_w=ECOL_W if ECOL_SLABS else None, ck_rule=CK_RULE, coll_split3=COLL_SPLIT3, bf_hier=BF_HIER, bf_frame_extra_um=BF_FRAME_EXTRA, die_um=list(DIE), host=HOST_SLAB, ctrl_rq=CTRL_RQ, fwd_iface=FWD_IFACE, hop_extra=HOP_EXTRA, path_pick=PATH_PICK, operand_path_pick=OPERAND_PATH_PICK, hop_r_cc=HOP_R_CC, relay_tt_reach=RELAY_TT_REACH, rt_strip=RT_STRIP,
                   wfc_hard=WFC_HARD, face_pin_inset=bool(FACE_PIN_INSET))
    variant.update(collective_variant_binding())
    variant.update(ctrl_slab=CTRL_SLAB, ctrl_role=CTRL_ROLE if CTRL_SLAB else None, su_area_mm2=su_area, hub_column_width_um=cw, gen='r8', geometry_fix=GEOMETRY_FIX, cfifo_v2=CFIFO_V2, cfifo_colck=CFIFO_COLCK, link_fix=LINK_FIX, link_split=LINK_SPLIT, sel_xstg=SEL_XSTG, pin_relay=PIN_RELAY, nxt_reach=NXT_REACH, vm_face_mm2=VM_FACE_MM2, ch_heights=CHS, vch_w=VCH8, hc_corr=HC_CORR, hc_xface=HC_XFACE, hop_fix=HOP_FIX, meso_d8=MESO_D8, fwd_pitch=FWD_REACH, corr_interleave=CORR_INTERLEAVE, rev=REV, cc_reach_um=CC_REACH, vch_interleave=VCH_INTERLEAVE, q_lef=Q_LEF, head_dies=HEAD_DIES, die=DIE_KIND, role=dict(layer='scan die (4 HBM3E stacks; 32 of the rack)',
                                                    layer1='layer die, 1 HBM3E stack (292 of the rack)',
                                                    layer1e='Engram home layer die, 2 HBM3E stacks (8 of the rack: '
                                                            'stages 3 / 42 x 4 ranks)',
                                                    head='head die (4 stacks; 12 of the rack)')[DIE_KIND],
                   pairs=PAIRS, bf=BF_PAIRS, nv=NV_PAIRS, head_bundles=HEAD_BUNDLES, stacks=list(STACKS[DIE_KIND]),
                   elem_frame_h=ELEM_FRAME_H, q_elem_frame_h=Q_ELEM_FRAME_H, frame_h=FRAME_H, slot_h=SLOT_H, slots=SLOTS)
    if BF_EXPLICIT_IDS is not None:
        variant['bf_pair_ids'] = sorted(BF_EXPLICIT_IDS)
    variant.update(wfc_hard=bool(wfc_die), mtp_seq=(MTP_SEQ_MM2 if MTP_SEQ and DIE_KIND == 'head' else None),
                   mtp_links=MTP_LINKS if (DIE_KIND == 'head' or DRAFT_SIDE == 'P' or COLL_MTP_FAR) else 0, draft=DRAFT_SIDE)
    if DRAFT_SIDE:
        variant['role'] = ('MD-2 P2 draft die %s (40 = 5 row packages x 4 ranks x A/B; layer1 recipe): %s'
                           % (DRAFT_SIDE, DRAFT_CONTENT[DRAFT_SIDE]))
        variant['draft_image'] = dict(DRAFT_IMAGE_P if DRAFT_SIDE == 'P' else DRAFT_IMAGE, side=DRAFT_SIDE)
    m = dict(geo=geo, insts=insts, regions=regions, frames=frames, cregions=[], fifo_of={}, hub=hub, phys=phys,
             ctrls=ctrls, svcs=svcs, links=links, notes=notes, slot_of=slot_of, x_vch=x_vch, x_spe=x_spe, mid=mid,
             corridor=(c0, c1), variant=variant, gap_x=(gap_x0, gap_x1))
    m['pq_cnt'] = m_cnt
    spine_y0 = min(it.y for it in insts if it.region == 'spine')
    spine_y1 = max(it.y + it.h for it in insts if it.region == 'spine')
    for reg in regions:
        if reg['name'] in ('spine', 'vch'):
            reg['rect'][1] = min(reg['rect'][1], spine_y0)
            reg['rect'][3] = max(reg['rect'][3], spine_y1)
    if DIE_KIND == 'layer' and wfc_rect is not None:
        reservation = json.loads((ROOT / 'results/uarch/dsrom_s81_wfc_parent_allocation_20261006/model.json').read_text())
        x0, y0, x1, y1 = wfc_rect
        reservation['selected_WFC_gross_um'] = wfc_rect
        reservation['selected_WFC_core_um'] = [x0 + 17.28, y0 + 17.28, x1 - 17.28, y1 - 17.28]
        assert all(not (it.x < x1 and it.x + it.w > x0 and it.y < y1 and it.y + it.h > y0) for it in insts)
        m['child_reservations'] = {'wfc': reservation}
        regions.append(dict(name='wfc_selected_child', kind='soft_child_reservation', rect=[x0, y0, x1, y1]))
        m['wfc_rect'] = wfc_rect
    if CTRL_SLAB:
        m['ctrl_model'] = ctrl_model
        m['ctrl_binding_shell_sha256'] = CTRL_BINDINGS['shell_sha256']
    if CTRL_ADAPTERS:
        for k_, ms_ in CTRL_C_MASTERS.items():
            if k_ in hub:
                hub[k_].master = ms_
        if STATIC_COLLECTIVE and 'collective' in hub:
            assert (ROOT / STATIC_COLLECTIVE_RTL).is_file(), 'static collective RTL not in this source tree (main-first)'
            hub['collective'].master = STATIC_COLLECTIVE_MASTER
        if 'sseq' in hub:   # s81die-1011/ctrl: per-engine c/d/s pins on the stream clock (kit / program faces cross)
            # F4 (--rtl-bind): a layer1 die has engines 0..7 only (stage programs); its master has no pins for 8..11
            # S-BIND (owner 2026-10-14 18:59, static cycle schedule): --rtl-bind binds the STATIC issuer (calendar-fixed
            # issue/KIT/END, completions fault-check only; same c/d/s die faces); the completion-driven c/c8 leave the die
            hub['sseq'].master = ('dsfd_stage_seq_static_c8' if DIE_KIND == 'layer1' else 'dsfd_stage_seq_static_c') if RTL_BIND \
                else 'dsfd_stage_seq_c'
        if RTL_BIND and 'collector' in hub and len(m.get('svcs', {}) or STACKS.get(DIE_KIND, ())) == 1:
            # F5 (--rtl-bind): a 1-stack die's collector has the one stack lane (dsfd_bk_collector_c1: DONE join over the
            # present stack; the 4-lane master would never emit a DONE there)
            hub['collector'].master = 'dsfd_bk_collector_c1'
            # ... and its selector the SW lane with the three absent quarters synthesised empty (dsfd_bk_selector_c1)
            if 'selector' in hub:
                hub['selector'].master = 'dsfd_bk_selector_c1'
    if CANONICAL_LAYOUT is not None:
        m['canonical_layout'] = CANONICAL_LAYOUT
        variant['canonical_layout'] = dict(path=CANONICAL_LAYOUT['path'], sha256=CANONICAL_LAYOUT['sha256'], pair_count=2417, bf_pairs=519, root_count=128, phase_width_by_stage=CANONICAL_LAYOUT['stages'], supplemental_homes_status='unbound reservations, not substituted native masters')
        # Preserve exact supplemental HCP geometry against all station searches.
        for home in CANONICAL_LAYOUT['hcp_homes']:
            xx, yy = home['at_um']; oo = home['outline']
            RSV_RECTS.append((xx, yy, xx + oo['w'], yy + oo['h'], 'canonical_hcp_home'))
    if PIN_OVERRIDES:
        variant['pin_overrides'] = PIN_OVERRIDES['record']
    if MIX4_SLOT:
        xx, yy, ww, hh = MIX4_SLOT
        RSV_RECTS.append((xx, yy, xx + ww, yy + hh, 'mix4_home'))
        variant['mix4_slot'] = dict(at_um=[xx, yy], outline=dict(w=ww, h=hh), master='dsfd_engram_mix4_c',
                                    status='RESERVATION_SCREEN_NOT_BOUND (cluster footprint from S-FUNC sizing pending)')
    if STATIC_SEAMS:
        variant['static_seams'] = dict(vm_collective=[list(b) for b in RTL_HUB_EXTRA_STATIC] + [['collective', 'vm', 2204, 't_vm', 'f_collective']],
                                       dropped=['vm.t_collective[592]', 'vm.tcs[3]', 'hc_s.y_rdy'], hc_tag=list(STATIC_HC_TAG),
                                       collective_master=hub['collective'].master if 'collective' in hub else None)
    m['buses'] = []
    buses_r8(m)
    if RTL_HUB_WIDTHS and 'wfc' in hub and hub['wfc'].master in WFC_FIELD_SPLIT:
        _split_fields(m, hub['wfc'].name, (WFC_FIELD_SPLIT_PRICED if WFC_PRICED else WFC_FIELD_SPLIT)[hub['wfc'].master])
    return m


# --rtl-hub-widths (s81die-1011/ctrl, die lead decision 5): the WFC stage kit's die buses were budgeted as packed groups;
# its RTL (rtl/dsrom_sys/mtp/dsfd_wfc_kit.sv dsfd_wfc_stg FLIT 512, VWA 15, RD2 0) has split valid / data / ready
# ports.  Same bit totals, so each packed group is split field by field at the kit's pins, valid at bit 0 (the hub
# lane convention {.., data, v}): f_li = {f_lid 513, f_liv}, t_lo = {t_lod 513, t_lov}, t_sw_sr = {t_srd 15, t_srv,
# t_swd 527, t_swv}, f_sw_sr = {f_srq 513, f_srr, f_swa, f_swr}.
WFC_FIELD_SPLIT = {'dsfd_wfc_stg': {'f_li': (('f_liv', 1), ('f_lid', 513)),
                                    't_lo': (('t_lov', 1), ('t_lod', 513)),
                                    't_sw_sr': (('t_swv', 1), ('t_swd', 527), ('t_srv', 1), ('t_srd', 15)),
                                    'f_sw_sr': (('f_swr', 1), ('f_swa', 1), ('f_srr', 1), ('f_srq', 513))}}


# --wfc-priced (contract v16, el1013-s81-wfcstg): the kit of record is the PRICED one (tb_mtp_wave_dies.sv:96:
# VM_LINK 1, VMRQ 64, WOUTW 8, POSTED 1, RD2 1): t_srd = {v1, a1[14:0], a0[14:0]} 31 b, f_srq = {rv1, rq1[511:0], rv,
# rq[511:0]} 1,026 b (the VM side dsfd_vm_wfc_ep is already RD2 1), and t_ft[3:0] to the host fault collector.
WFC_PRICED = False
WFC_FIELD_SPLIT_PRICED = {'dsfd_wfc_stg': dict(WFC_FIELD_SPLIT['dsfd_wfc_stg'],
                                               t_sw_sr=(('t_swv', 1), ('t_swd', 527), ('t_srv', 1), ('t_srd', 31)),
                                               f_sw_sr=(('f_swr', 1), ('f_swa', 1), ('f_srr', 1), ('f_srq', 1026)))}


def _split_fields(m, inst, spec):
    """replace every bus touching inst.<group> by one bus per field: inst.<field> <-> the peers' slices of the group
    (a peer port already sliced keeps its offset); bit totals are asserted equal"""
    out = []
    for bid, cls, bits, eps in m['buses']:
        hit = [p_ for i_, p_ in eps if i_ == inst and pslice(p_)[0] in spec]
        if not hit:
            out.append((bid, cls, bits, eps))
            continue
        grp = pslice(hit[0])[0]
        assert pslice(hit[0])[1] is None and sum(n for _, n in spec[grp]) == bits, (bid, grp, bits)
        lo = 0
        for fld, n in spec[grp]:
            eps_ = []
            for i_, p_ in eps:
                if i_ == inst:
                    eps_.append((i_, fld))
                else:
                    b_, l_, h_ = pslice(p_)
                    o_ = l_ or 0
                    eps_.append((i_, f'{b_}[{o_ + lo}:{o_ + lo + n - 1}]'))
            out.append((f'{bid}_{fld}', cls, n, eps_))
            lo += n
    m['buses'] = out


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
    if HUB_SOUTH_SHIFT:
        su = m['hub']['su_s']
        cor['su_south_bypass'] = (su.x - 216.0, EDGE, su.x + su.w + 216.0, su.y - 4.32)
    if COLL_SPLIT3:
        # --coll-split3: the collective slab (1,371.8 um) is narrower than the hub column; the column remainder beside it
        # is free for the link / hub chains' first stations (KE0t had no spot at the slab's E face)
        c_ = m['hub']['collective']
        x0c, x1c = g['x_sp'], g['x_sp'] + (SPINE_W8 - VCH8) / 2
        if c_.x - x0c > 30.0:
            cor['collW'] = (x0c + 4.32, c_.y, c_.x - 4.32, c_.y + c_.h)
        if x1c - (c_.x + c_.w) > 30.0:
            cor['collE'] = (c_.x + c_.w + 4.32, c_.y, x1c - 4.32, c_.y + c_.h)
    if 'hrtx' in m['hub'] and 'su_n' in m['hub']:
        # --hrow-tx: the E-column band between hc_n and su_n around the sender is a station channel (su_n <-> hc_n)
        hn_, sn_ = m['hub']['hc_n'], m['hub']['su_n']
        cor['hrtxG'] = (m['x_spe'] + 4.32, hn_.y + hn_.h + 4.32, g['x_fe'] - 4.32, sn_.y - 4.32)
    if VM_SLAB:
        # --vm-slab: the VM is narrower than the hub column; the column remainder beside it is a station corridor
        # (layer1e: hb_hc_n_vm had no station spot at the VM's E face)
        v_ = m['hub']['vm']
        x0c, x1c = g['x_sp'], g['x_sp'] + (SPINE_W8 - VCH8) / 2
        if v_.x - x0c > 30.0:
            cor['vmW'] = (x0c + 4.32, v_.y, v_.x - 4.32, v_.y + v_.h)
        if x1c - (v_.x + v_.w) > 30.0:
            cor['vmE'] = (v_.x + v_.w + 4.32, v_.y, x1c - 4.32, v_.y + v_.h)
    if ECOL_SLABS:
        # --ecol-slabs: the E-column sub-column outside the moved stack is free; it is the channel beside the narrowed HC
        # halves' W faces (VM -> hc_s / hc_n chains end there: first try had no station spot below the corridor)
        hs_, hn_ = m['hub']['hc_s'], m['hub']['hc_n']
        xs0, xs1 = m['x_spe'] + 4.32, hs_.x - 4.32
        top = max(m['hub'][n].y + m['hub'][n].h for n in m['hub'] if m['hub'][n].x < hs_.x - 1.0 and m['hub'][n].x >= m['x_spe'] - 1.0)
        cor['ecolS'] = (xs0, b0, xs1, m['corridor'][0] + 4.32)
        cor['ecolN'] = (xs0, top + 4.32, xs1, b1)
    if 'eng' in m['hub']:
        # layer1e: the SE service slot around eng_SE is free (no svc_SE): its stations / pin relays stand there and climb
        # into stripS (l1e check: the last VM -> eng hop had no box near eng_SE, 1,181.5 um segment)
        e_ = m['hub']['eng']
        cor['engS'] = (e_.x - (PHY_W - e_.w) / 2 + 4.32, e_.y,
                       e_.x + e_.w + (PHY_W - e_.w) / 2 - 4.32, g['band_depth'] + 4.32)
    if 'hrow' in m['hub']:
        # the SE slot around hrow_SE is free: end blocks / stations stand above its N face and climb into stripS
        e_ = m['hub']['hrow']
        cor['hrowS'] = (e_.x + 4.32, e_.y + e_.h + 4.32, e_.x + PHY_W - 4.32, g['band_depth'] + 4.32)
    for t, c in enumerate(g['ch_y']):
        cor[f'ch{t}'] = (g['x_lw'] + LINK_COL + 4.32, c + 4.32, g['x_le'] - 4.32, c + chh(t) - 4.32 - CF_WH[1] - 2.16)
    if CANONICAL_LAYOUT is not None:
        from s81.canonical_layout import corridors as canonical_corridors
        canonical_corridors(sys.modules[__name__], m, cor)
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
    if CTRL_SLAB:
        _ctrl_native_buses(m, bus)
    # ---------------- head-bundle frames (head die): column stream up a glue chain, result chain down
    for r, f in m['frames'].items():
        if not f.get('bundles'):
            continue
        cf = f'cf{r}'
        nb = f['bundles']
        col_ck, col_rs = [(cf, 'co')] + ([(cf, 'cr')] if CFIFO_COLCK else []), [(cf, 'rs')]
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
        col_ck = [(cf, 'co')] + ([(cf, 'cr')] if CFIFO_COLCK else [])
        col_rs = [(cf, 'rs')]
        # --bf-x2-static: the x2 lane climbs to the last slot holding a BF front (q-only frames carry none)
        _bfs = [s for p, kind, s, ln in elems if _is_bf_front(by.get(f'e{p}'))] if BF_X2_STATIC else []
        x2_last = max(_bfs) if _bfs else None
        # stations
        for s in range(last + 1):
            t_ = f't{r}_{s}'
            col_ck.append((t_, 'ck'))
            col_rs.append((t_, 'rs'))
            if s == 0:
                bus(f'xa_{r}_0', 'x_lane', X0B, [(cf, 'xa'), (t_, 'xai')])
                bus(f'xb_{r}_0', 'x_lane', X1B, [(cf, 'xb'), (t_, 'xbi')])
                bus(f'cc_{r}_0', 'x_ctl', CCB, [(cf, 'cc'), (t_, 'cci')])
                if x2_last is not None:
                    bus(f'x2_{r}_0', 'x_lane', X2B, [(cf, 'x2'), (t_, 'x2i')])
        # elements, sequencers, ROMs, status
        for s in range(last + 1):
            t_ = f't{r}_{s}'
            es = slot_elems.get(s, [])
            xa_eps, xb_eps, cc_eps, x2_eps = [], [], [], []
            for j, (p, kind, ln) in enumerate(es):
                e, sq = f'e{p}', f's{p}'
                xa_eps.append((e, 'x0'))
                if kind in ('BF', 'NV'):
                    xb_eps.append((e, 'x1'))
                if x2_last is not None and _is_bf_front(by.get(e)):
                    # xb = {x1[265:0], x0[265:0], x2[535:0]} (bf_x2_lane.json xb_runs): load sub-ranges of the lane nets
                    xa_eps.append((e, f'xb[{X2B}:{X2B + 265}]@0'))
                    xb_eps.append((e, f'xb[{X2B + 266}:{X2B + 531}]@0'))
                    x2_eps.append((e, f'xb[0:{X2B - 1}]'))
                cc_eps.append((sq, 'lc'))
                col_ck += [(e, 'ck'), (sq, 'clk')] + [(f'c{p}_{k}', 'ck') for k in range(CFG_PER_PAIR)]
                col_rs += [(e, 'rs'), (sq, 'rst_n')]
                bus(f'cfg_{p}', 'cfg', CFGB, [(sq, 'cfg'), (e, 'cfg')])
                bus(f'go_{p}', 'go', 1, [(sq, 'go_e'), (e, 'go')])
                if kind == 'q' and q_pq():
                    # TA-10: op tag with go (the sequencer counts the broadcast gos = the PQ spine's tag), and the
                    # element's {bank_free, sh_free} that hold a configuration load (ot_v41_pair_pq_ld PQ 1)
                    bus(f'gt_{p}', 'cfg', 2, [(sq, 'go_tag'), (e, 'gt')])
                    bus(f'ef_{p}', 'cfg', 2, [(e, 'ef'), (sq, 'ef')])
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
            if x2_last is not None and s <= x2_last:
                B.append((f'x2_{r}_{s + 1}', 'x_lane', X2B, [(t_, 'x2')] + ([(nxt, 'x2i')] if nxt is not None and s < x2_last
                                                                             else []) + x2_eps))
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
        sx = f['x'] + LANES_W + NS_W + 4.32
        ytop = rootn.y + rootn.h
        ybot = cfi.y + cfi.h
        if PQ_ROOTS:      # the strip chain now ends at the root row's N station, not at the column FIFO
            pqn_ = next(i_ for i_ in m['insts'] if i_.name == f'pqn{r}')
            ybot = pqn_.y + pqn_.h
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
        if PQ_ROOTS:
            # tree word -> N station -> ret_root_r128 -> S station -> column FIFO return (all column clock: no crossing)
            bus(f'rr_{r}_{nst}', 'col_ret', NODEB, [prev, (f'pqn{r}', 'i')])
            bus(f'pqt_{r}', 'col_ret', PQ_TI, [(f'pqn{r}', 'o'), (f'pqr{r}', 'ti')])
            bus(f'pqo_{r}', 'col_ret', PQ_RO, [(f'pqr{r}', 'ro'), (f'pqs{r}', 'i')])
            bus(f'pqc_{r}', 'col_ret', PQ_RO, [(f'pqs{r}', 'o'), (cf, 'ri')])
            for n_, ck_, rs_ in ((f'pqn{r}', 'ck', 'rs'), (f'pqr{r}', 'ck', 'rs'), (f'pqs{r}', 'ck', 'rs')):
                col_ck.append((n_, ck_))
                col_rs.append((n_, rs_))
        else:
            bus(f'rr_{r}_{nst}', 'col_ret', NODEB, [prev, (cf, 'ri')])
        f['ret_stages'] = nst
        bus(f'ck_col_{r}', 'col_clock', 1, col_ck)
        bus(f'rs_col_{r}', 'col_reset', 1, col_rs)
    if BF_HIER:
        _bf_hier_nets(m)
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
        if kind == 'm2l' and PQ_PLACE:
            # S81-DIE (m221pq hend views): a d8g1 meso lane FIFO maps to 16.5-18.4 um2 of cells per lane bit (closure-loop
            # calibrate runs s81-hend-m221pq-hl-*/hr-*: 8,440 um2 for 512 b, 13,794 um2 for 11 x 68 b), so the 3 um2/b
            # outline placed it at 100-211 %; sized at ~55 % (33 um2 per bit), square
            side = math.sqrt(bits * M2L_UM2_PER_BIT)
            h = up(max(face, side), GY)
            w = up(max(face, bits * M2L_UM2_PER_BIT / h), GX)
        return name, w - SHAVE, h - SHAVE
    # x root: VM -> two serial->stream CDC start blocks (W channel / VCH)
    # (--pq-place: the PQ core is the lane source; its W / E faces drive the two start blocks)
    xsrc = hub['pq'] if PQ_PLACE else vm
    vmc = xsrc.y + xsrc.h / 2
    starts = {}
    for side in 'WE':
        nm, w, h = end_spec('l2r', [LSW], 'vr')
        it = hub_block(f'hx_{side}', nm, 'hend', w, h, x_sp if side == 'W' else x_vch + 0.0, vmc,
                       side, [cor['s14W'] if side == 'W' else cor['vch']])
        starts[side] = it
        bus(f'xr_{side}', 'local', LSW + 1, [(xsrc.name, f'x{side.lower()}'), (it.name, 'i')])
        bus(f'xrs_{side}', 'local', 3, [(it.name, 'st'), (xsrc.name, f'x{side.lower()}s')])
    # ---------------- x trunks: per half, a vertical spine (up / down) with a branch per tier channel
    rowx = 64.8          # x-trunk station row (offset in the channel)
    rowr = 8.64          # return-trunk row
    rowl = 118.8         # link row
    s14x = {'W': x_sp - SPF / 2, 'E': x_fe + SPF / 2}
    m['chain_paths'] = []

    def tap_x(half, c, off):
        return g['col_x'](half, c) + off

    if CANONICAL_LAYOUT is not None:
        from s81.canonical_layout import trunks as canonical_trunks
        canonical_trunks(sys.modules[__name__], m, CH8, cor, starts, ga, end_spec, hub_block, bus)
    else:
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
                        if CFIFO_FALL:     # r6: the cfifo's xf = the station's non-inverted clock copy fn0 (falling-edge launch)
                            st_ = sts_h[ih][0]
                            _add_tap(m, st_, 0, (f'cf{r}', None, 'xd'))
                            fb = [i_ for i_, b_ in enumerate(m['buses']) if b_[3][0] == (st_.name, 'fn0')]
                            if fb:
                                b_ = m['buses'][fb[0]]
                                m['buses'][fb[0]] = (b_[0], b_[1], b_[2], b_[3] + [(f'cf{r}', 'xf')])
                            else:
                                m['buses'].append((f'{st_.name}_tn0', 'fclk', 1, [(st_.name, 'fn0'), (f'cf{r}', 'xf')]))
                        else:
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
                endb = None
                if RELAY_PROGRESS:
                    # --relay-progress: the end block stands first, and the trunk ends on its facing (trunk-side) pin face
                    # (placed after the trunk, hr_W4 slid 256 um off the path end and the last station overshot it)
                    nm, w, h = end_spec('m2l', [CRET] * ncol, 'vr')
                    endb = hub_block(f'hr_{half}{t}', nm, 'hend', w, h, ga.x if half == 'W' else ga.x + ga.w, gy, half,
                                     [cor['s14W'] if half == 'W' else cor['vch']])
                    ey_ = endb.y + endb.h / 2
                    ex_ = endb.x + endb.w if path[-1][0] >= endb.x + endb.w / 2 else endb.x
                    path = path[:-1] + [(path[-1][0], ey_), (ex_, ey_)]
                path = _dedup(path)
                forced = [abs(xs_[-1] - x_) for x_ in xs_[::-1]]
                lanes_at = []
                allowed = [cor[f'ch{t}'], cor['s14W'] if half == 'W' else cor['s14E'], cor['vch'], cor['hcc']]
                # lanes: column c joins at its tap; a station carries every lane that has joined so far
                sts = _run_multi(CH8, f'r{half}{t}', path, allowed, forced, ncol)
                if endb is None:
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
                                 ('vm', 'hc_s', 1024, 't_hc', 'f_vm'), ('hc_n', 'vm', SUHC_HC_VM, 't_vm', 'f_hc'),
                                 ('vm', 'gather', 512, 't_gather', 'f_vm'), ('gather', 'capture', 576, 't_capture', 'f_gather'),
                                 ('capture', 'vm', 512, 't_vm', 'f_capture'), ('collective', 'vm', 512, 't_vm', 'f_collective'),
                                 ('su_s', 'hc_s', 512, 't_hc', 'f_su_s'), ('su_n', 'hc_n', 512, 't_hc', 'f_su_n'),
                                 ('hc_s', 'hc_n', 1024, 't_n', 'f_s'), ('hc_n', 'hc_s', 1024, 't_s', 'f_n')) + \
            (((('pq', 'vm', 20, 't_vm', 'f_pqx'), ('vm', 'pq', 2049, 't_pqx', 'f_vm')) if RTL_BIND else
              (('vm', 'pq', PQ_VMR, 't_pq', 'f_vm'),)) if PQ_PLACE else ()) + \
            ((('pq', 'gather', PQ_CFG, 't_gather', 'f_pq'),
              ('gather', 'pq', PQ_RCNT, 't_pq', 'f_gather')) if PQ_ROOTS else ()) + \
            (WFC_BUSES if 'wfc' in hub and hub['wfc'].master == 'dsfd_wfc' else ()) + \
            (wfc_kit_buses(WFC_ROLE, 'host' in hub, COLL_MTP_FAR, WFC_CRP) if 'wfc' in hub and hub['wfc'].master in ('dsfd_wfc_src', 'dsfd_wfc_stg', 'dsfd_wfc_cr2') else ()) + \
            ((MTP_SEQ_EP_BUSES if 'cap_ep' in hub else MTP_SEQ_BUSES) if 'mtp' in hub else ()) + \
            (HSRC_BUSES + (HSRC_HOST_BUSES if 'host' in hub else ()) if 'hrsrc' in hub else ()) + \
            ((SEEDL_BUSES_SPINE if 'hrow' in hub else SEEDL_BUSES) + (SEEDL_HOST_BUSES if 'host' in hub else ())
             if 'seedl' in hub else ()) + \
            ((P2_LNK_BUSES if 'p2_lnk' in hub else P2_BUSES) if 'p2' in hub else ()) + \
            ((('collective', 'host', 2, 't_p2flt', 'f_p2flt'),) if COLL_P2_LANE and 'host' in hub else ()) + \
            (SUHC_BUSES if SUHC_1011 and not SUHC_V2 else ()) + (SUHC_V2_BUSES if SUHC_V2 else ()) + \
            ((HRTX_BUSES + (HRTX_KIT_BUSES if 'wfc' in hub else ()) + (HRTX_HOST_BUSES if 'host' in hub else ()))
             if 'hrtx' in hub else ()) + \
            ((('collective', 'host', HOST_CF_BITS, 't_host', 'f_collective'),
              ('host', 'collective', HOST_TC_BITS, 't_collective', 'f_host')) if HOST_SLAB else ()) + \
            (ctrl_adapter_buses(hb) if CTRL_ADAPTERS else ()) + \
            ((RTL_HUB_EXTRA_STATIC if STATIC_SEAMS else RTL_HUB_EXTRA) if RTL_HUB_WIDTHS else ()) + \
            ((STATIC_HC_TAG,) if STATIC_SEAMS and SUHC_V2 and rtl_has_port(hb['hc_s'].master if 'hc_s' in hb else '', 'y_tag') else ()) + \
            (tuple(b_ for k in range(HC_T_COLS) for b_ in (('hc_s', 'hc_t', HC_T_FWD, f't_tf{k}', f'f_sf{k}'),
                                                            ('hc_t', 'hc_s', HC_T_RET, f't_sr{k}', f'f_tr{k}')))
             if 'hc_t' in hub else ()):
        if SUHC_V2 and ((a_, b_) in (('vm', 'su_s'), ('vm', 'su_n'), ('vm', 'hc_s'), ('hc_n', 'vm'), ('su_s', 'hc_s'),
                                     ('su_n', 'hc_n'), ('hc_s', 'hc_n'), ('hc_n', 'hc_s')) and pa in ('t_su_s', 't_su_n', 't_hc', 't_vm', 't_n', 't_s')):
            continue          # su_hc v2 retired these (the VM row slots / y bus replace them)
        if STATIC_SEAMS and (a_, b_, pa, pb) == ('hc_s', 'collective', 'y_rdy', 'f_hc_yr'):
            continue          # static schedule: no consumer ready on the HC y bus
        if RTL_HUB_WIDTHS:
            bits = RTL_HUB_BITS.get((a_, b_), bits)
            if STATIC_SEAMS and (a_, b_) == ('collective', 'vm'):
                bits = 2204 if pa == 't_vm' else 15     # S-BIND: t_crq keeps its 15 bits (was widened to 2204)
        if STATIC_COLLECTIVE and {a_, b_} == {'collective', 'wfc'} and bits == 1:
            continue              # WFC link grants t_lir / t_wfcg: no grant in the static collective
        if m.get('pq_cnt') and (a_, b_, pa, pb) == ('gather', 'capture', 't_capture', 'f_gather'):
            _pq_cnt_buses(m, CH8, cor, bits)
            continue
        if REV == 'r9':
            # mtp-wfc 2026-10-10 (ds-1010 finding): the WFC kit's VM / capture buses are 0.9 GHz serial-domain ports
            # (dsfd_wfc_vmx slow side): their stations are clocked in serial_0p9 and spaced at the 0.9 GHz reach
            ser_ = (WFC_KIT and 'wfc' in (a_, b_) and bool({a_, b_} & {'vm', 'capture'}))
            _hub_bus_chain(m, CH8, cor, a_, b_, bits, pa, pb, dom='serial_0p9' if ser_ else None,
                           reach_um=SER_STAGE_UM if ser_ else None)
        else:
            bus(f'hb_{a_}_{b_}', 'hub', bits, [(hb[a_].name, pa), (hb[b_].name, pb)])
    # ---------------- PHY / controller / service
    npins = len(real_ports_r8()[real_lef(PHY_LEF)['name']]['dfi'])
    for st, ph in m['phys'].items():
        bus(f'dfi_{st}', 'phy_dfi', npins, [(m['ctrls'][st].name, 'phy'), (ph.name, 'dfi')])
        cl_ = m['svcs'][st].name if st in m['svcs'] else hub['eng'].name      # the stack's client
        if st in m['svcs'] and m['svcs'][st].master == CTRL_SVC_MASTER:
            # --ctrl-adapters (s81die-1011/ctrl): dsfd_ctrl rd [8895:0] = {kr_v 32 | kr_beat 32x4 | kr_tag 32x17 |
            # kr_data 32x256} (the RTL also carries the 32 response valids the 8,864-b default bus dropped) onto
            # dsfd_svc_c's per-PC response pins r_data / r_tag / r_beat / rv
            c_ = m['ctrls'][st].name
            for nm_, lo_, n_ in (('r_data', 0, 8192), ('r_tag', 8192, 544), ('r_beat', 8736, 128), ('rv', 8864, 32)):
                bus(f'rd_{st}_{nm_}', 'hbm_read', n_, [(c_, f'rd[{lo_}:{lo_ + n_ - 1}]'), (cl_, nm_)])
            # the controller status st = {fault, live} -> the stack's svc (hs): folded into its job-done fault (jd ->
            # dsfd_svc_join c_st -> sequencer s4) and gating its PC issue on live (composition.json nets.status)
            bus(f'st_{st}', 'hbm_req', 2, [(c_, 'st'), (cl_, 'hs')])
        else:
            # s81-die-iter 2026-10-12 (c1e plan: dsfd_ctrl.rd 8,896 on ctrl_SW vs 8,864 on ctrl_SE): one master, one
            # port width -- under --ctrl-adapters dsfd_ctrl rd is its RTL [8895:0] (32 response valids included) on every
            # stack, so the layer1e Engram client (eng_SE) takes the full word too (dsfd_engram_c has no HBM response
            # port yet: recorded by the ctrl port audit for the svceng stream, OT_S81_CTRL_GATE_WARN=phys)
            bus(f'rd_{st}', 'hbm_read', HBM_RD_BITS + (32 if CTRL_ADAPTERS else 0), [(m['ctrls'][st].name, 'rd'), (cl_, 'rd')])
        if CTRL_RQ:   # s81-gen: the controller's request side (real dsfd_ctrl rq / rk / wd), abutting faces
            bus(f'rq_{st}', 'hbm_req', HBM_RQ_BITS, [(cl_, 'rq'), (m['ctrls'][st].name, 'rq')])
            bus(f'rk_{st}', 'hbm_req', 32, [(m['ctrls'][st].name, 'rk'), (cl_, 'rk')])
            bus(f'wd_{st}', 'hbm_req', 32, [(m['ctrls'][st].name, 'wd'), (cl_, 'wd')])
    if 'eng' in hub and not FWD_IFACE:  # layer1e Engram service (ENG_BUSES) + the SW-home share through svc_SW
        for a_, pa, b_, pb, bits, _ in ENG_BUSES:
            bus(f'eng_{a_}_{b_}_{pa}', 'eng', bits, [(hub[a_].name, pa), (hub[b_].name, pb)])
        bus('eng_sw_q', 'eng', 35, [(hub['eng'].name, 'teq'), (m['svcs']['SW'].name, 'feq')])   # hq_v + atom 31 + tag 3
        bus('eng_sw_r', 'eng', 265, [(m['svcs']['SW'].name, 'ter'), (hub['eng'].name, 'fer')])  # hq_cred + hr 264
    if HOST_SLAB and not (FWD_IFACE and CTRL_RQ):     # host sector writes -> each stack controller's host write port (decode first), completions back
        for st, ct in m['ctrls'].items():
            # s81-gen 2026-10-09: with --ctrl-rq the stack client owns the controller's real request port (rq), so the
            # host writes land in the client (svc / layer1e Engram service), which muxes them into rq (ingest 2f179fc18:
            # per-PC local mux).  The controller's N face is covered by the abutting client (8.64 um gap): the r4 --host
            # hw_SW chain could never reach a pin there (station 5/53 trap); the client's free face can.
            tgt = ((m['svcs'][st].name if st in m['svcs'] else hub['eng'].name) if CTRL_RQ else ct.name)
            bus(f'hw_{st}', 'host_wr', 512 + 64 + 2, [(hub['host'].name, f'tw{st}'), (tgt, 'hw')])
            bus(f'hc_{st}', 'host_wr', 18, [(tgt, 'hc'), (hub['host'].name, f'fc{st}')])
    if PQ_PLACE:      # PQ core <-> its ROMs (real ot_rom_4096x72 ports), direct: they abut the core's E face
        for j in range(PQ_ROMS):
            bus(f'pqra_{j}', 'rom_a', 12, [(hub['pq'].name, f'ra{j}'), (f'pqrom{j}', 'a')])
            bus(f'pqrc_{j}', 'rom_ce', 1, [(hub['pq'].name, f'rc{j}'), (f'pqrom{j}', 'ce')])
            bus(f'pqrq_{j}', 'rom_q', (64 if j < 2 else 48) if RTL_BIND else 48, [(f'pqrom{j}', 'rd'), (hub['pq'].name, f'rq{j}')])
    if HOP_FIX and HOP_PLAN:
        _hop_fix(m, P)
    if RELAY_PROGRESS:
        _relay_progress_fix(m, P)
    if LANE_EQUAL:
        _go_retap(m)
    if CTRL_SLAB and HOP_PLAN:
        _ctrl_vm_latency_check(m)
    # ---------------- clocks, resets, top ports
    col = coll.name
    bus('refclk', 'top_in', 1, [('TOP', 'refclk'), (col, 'refclk')])
    bus('por_n', 'top_in', 1, [('TOP', 'por_n'), (col, 'por')])
    if STATIC_COLLECTIVE:
        bus('rank', 'top_in', 2, [('TOP', 'rank'), (col, 'f_rank')])
    by = {it.name: it for it in m['insts']}
    dom = defaultdict(list)
    rst = defaultdict(list)
    for it in m['insts']:
        if it.kind == 'cfifo':
            dom['stream'].append((it.name, 'ck'))
            rst['stream'].append((it.name, 'rst'))
        elif it.name == 'sp_stage_ctrl':
            dom['stream'].append((it.name, 'ck'))
            rst['stream'].append((it.name, 'rs'))
        elif it.master == 'dsfd_stage_seq':                    # option A sequencer: the kit's serial (ckv) side
            dom['serial'].append((it.name, 'ckv')); rst['serial'].append((it.name, 'rsv'))
        elif RTL_BIND and it.master in DUAL_CLOCK_MASTERS and not _assigned_clock_entries(it):
            # s81-die-rtl-bind 2026-10-14 (F3): *_c masters whose RTL runs two domains: stream ck / rst AND the serial
            # ckv / rsv (gather, capture: the VM-side crossing; stage_seq_c: kit / program / status side)
            dom['stream'].append((it.name, 'ck')); rst['stream'].append((it.name, 'rst'))
            dom['serial'].append((it.name, 'ckv')); rst['serial'].append((it.name, 'rsv'))
        elif it.kind == 'pqcnt':          # --pq-cnt count leaves: PQ stream clock, RTL ports clk / rst_n
            dom['stream'].append((it.name, 'clk')); rst['stream'].append((it.name, 'rst_n'))
        elif RTL_BIND and it.master == 'dsfd_sp_vm':
            ce_ = rtl_clock_reset_entries('dsfd_sp_vm')
            if ce_ is None:
                # VM memory side is serial; compact sequencer and client slots use stream cks/rss.
                dom['serial'].append((it.name, 'ck')); rst['serial'].append((it.name, 'rst'))
                dom['stream'].append((it.name, 'cks')); rst['stream'].append((it.name, 'rss'))
            else:
                # S-BIND 2026-10-15: the static VM's per-category leaf clock / reset entries (one source: the master's
                # RTL header under the die manifest); domain by suffix (_t stream 1.2 GHz, _s serial 0.9 GHz)
                for d_, pl_ in ce_['clock'].items():
                    dom[d_] += [(it.name, p_) for p_ in pl_]
                for d_, pl_ in ce_['reset'].items():
                    rst[d_] += [(it.name, p_) for p_ in pl_]
        elif RTL_BIND and it.master == STATIC_COLLECTIVE_MASTER:
            # static collective leaf clock entries (stream; its PLL / reset controller drives the die nets)
            dom['stream'] += [(it.name, f'{p_}[{i_}:{i_}]') for p_, w_ in STATIC_COLL_CLOCKS for i_ in range(w_)]
        elif RTL_BIND and it.master == PQ_RTL_MASTER:
            # s81-die-rtl-bind r3: the PQ cluster's per-child clock entries (stream; the die delivers phi - R at each pin)
            dom['stream'] += [(it.name, p_) for p_ in pq_rtl_clock_ports()]
            rst['stream'].append((it.name, 'rst'))
        elif RTL_BIND and it.master == CTRL_SVC_JOIN:          # F8: the svc join endpoint runs on the stream clock
            dom['stream'].append((it.name, 'ck')); rst['stream'].append((it.name, 'rst'))
        elif it.master in ('dsfd_wfc_src', 'dsfd_wfc_stg', 'dsfd_wfc_cr2'):   # mtp-wfc: the kit's vmx slow side is the serial domain
            dom['stream'].append((it.name, 'ck')); rst['stream'].append((it.name, 'rst'))
            dom['serial'].append((it.name, 'ckv')); rst['serial'].append((it.name, 'rsv'))
        elif _assigned_clock_entries(it):
            for domain_, names_ in _assigned_clock_entries(it).items():
                dom[domain_] += [(it.name, name_) for name_ in names_]
            for domain_, names_ in _assigned_reset_entries(it).items():
                rst[domain_] += [(it.name, name_) for name_ in names_]
        elif it.kind in ('hub', 'band_blk') and it.name != col:
            d_ = 'serial' if it.domain == 'serial_0p9' else 'stream'
            dom[d_].append((it.name, 'ck'))
            if not (HC_RTL_WIDTHS and it.master == 'dsfd_sp_hc_t'):
                # --hc-rtl-widths (F9): the HC chain tails take reset in band (the forward word's sf bit), no die rst net
                rst[d_].append((it.name, 'rst'))
        elif it.kind == 'hstn':
            dom[HSTN_DOM[it.domain]].append((it.name, 'ck'))
        elif it.kind == 'pqrom':
            dom['stream'].append((it.name, 'ck'))
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
                # --rtl-bind + --pq-place: the x-lane start blocks hx_W / hx_E are written by the PQ core (stream), not the VM
                wd_ = 'stream' if (RTL_BIND and PQ_PLACE and it.name in ('hx_W', 'hx_E')) else 'serial'
                dom[wd_].append((it.name, 'ck'))
                rst[wd_].append((it.name, 'rs'))
                dom['stream'].append((it.name, 'cks'))
                rst['stream'].append((it.name, 'rss'))
            else:
                d_ = 'serial' if spec['kind'] == 'r2l' else 'stream'
                dom[d_].append((it.name, 'ck'))
                rst[d_].append((it.name, 'rs'))
    if RTL_BIND:
        # F10 (--rtl-bind): the link macros are real link layers (rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv): a stream
        # reset, and their PMA lanes leave the die as top pads {pma_tx, pma_tck} out / {pma_rx, pma_rck} in
        for it in m['insts']:
            if it.kind == 'link':
                pw_ = 544 if it.master == real_lef(SERDES_LEF)['name'] else 513
                rst['stream'].append((it.name, 'rst'))
                bus(f'pad_{it.name}_tx', 'top_out', pw_, [(it.name, 'pma_tx'), ('TOP', f'pad_{it.name}_tx')])
                bus(f'pad_{it.name}_tck', 'top_out', 1, [(it.name, 'pma_tck'), ('TOP', f'pad_{it.name}_tck')])
                bus(f'pad_{it.name}_rx', 'top_in', pw_, [('TOP', f'pad_{it.name}_rx'), (it.name, 'pma_rx')])
                bus(f'pad_{it.name}_rck', 'top_in', 1, [('TOP', f'pad_{it.name}_rck'), (it.name, 'pma_rck')])
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
VM_FACE_MM2 = None              # --vm-face-mm2 (v9e): minimum VM slab area on every die (layer die 2.6599)
PIN_RELAY = False               # --pin-relay (OWNER rule 1, 2026-10-07): a relay station abutting every hardened-block pin
PIN_SEG = 100.0                 #   on die interfaces (last segment <= 100 um)
PIN_NEED = False                # --pin-need (hbmdie-1011, compact199): a column net's relay count / path end at a q element
                                # is measured to that port's LEF pin centroid, not the 510 x 221 um element centre (gt: seq ->
                                # go_tag pins on the element S face ~150 um, centre 238 um > the 214 um rule)
SSTN_CCPAD = False              # --sstn-ccpad (hbmdie-1011, compact199): a --lane-equal pad on a cc net driven by a slot
                                # station is N extra cc registers INSIDE that station (master dsfd_sstn_<pins>_cp<N>), not a
                                # floating relay on the ~40 um station -> sequencer hop (no site exists between them)
RELAY_PROGRESS = False          # --relay-progress (hbmdie-1011, compact199 die fit): a column relay must advance toward its
                                # next chain point (mh(relay, nxt) <= mh(driver, nxt) + 15 um, inside the margin lint's 20 um
                                # far-side slack) in EVERY placement attempt incl. the TT and last-resort fallbacks; no site -> assert
RT_STRIP = 0.0                  # --rt-strip UM (s81-die-iter 2026-10-12): return-tree relays ('rt' nets) may also take relay
                                # sites in the UM-high channel strip just above their column frame.  Root cause of the last
                                # 128 SS-reach hops (bn<c> -> y_rt_<c>_<n>b_0, 515.0 um, one per column): the top slot's
                                # L-lane qbank bn<c> sits on the frame's top edge and its return leaf runs east along that
                                # edge to the trunk, but the frame under it is packed (q element, then the cfg / sstn row
                                # 262 um down, saturated with relays), so relay 0 fell to the TT tier in the cfg row.
NXT_REACH = False               # --nxt-reach (s81-die-timing 2026-10-08): a relay must also lie within reach of the
                                #   NEXT point of its chain (the load for the last relay), not only of the previous one
# MTP-DIE hub buses (a, b, bits, port at a, port at b).  WFC (ot_rom_pkg_ctrl_wfc ports): VM write xa_we/waddr15/wdata512
# (528 + valid/ready) and read xa_re/raddr15 out, xa_rq512 in; stage link flit 512 + valid/credit each way through the
# collective (the stage-hop endpoint); core_start / done / result (C8 capture binding) 64 each way.
WFC_BUSES = (('wfc', 'vm', 544, 't_vm', 'f_wfc'), ('vm', 'wfc', 512, 't_wfc', 'f_vm'),
             ('collective', 'wfc', 514, 't_wfc', 'f_collective'), ('wfc', 'collective', 514, 't_collective', 'f_wfc'),
             ('wfc', 'capture', 64, 't_capture', 'f_wfc'), ('capture', 'wfc', 64, 't_wfc', 'f_capture'))
# mtp-wfc 2026-10-10 (--wfc-kit): exact element ports of the WFC kit (rtl/dsrom_sys/mtp/dsfd_wfc_kit.sv; every grant /
# ready is its own reverse bus).  Die-facing: collective <-> lnk link (valid + {last, data} 514, grant 1 back) both ways,
# VM <-> vmx (t_swv/t_swd 528 + t_srv/t_srd 16 = 544 out; f_swr f_swa f_srr 3 + f_srq 513 = 516 in), capture <-> vmx
# (t_ks 53, f_kd 54), SOURCE only: host -> tok cfg f_c 55 and core -> host committed token {valid,user,pos,id} 53.
# The element-to-element wiring is inside the kit master (dsfd_wfc_kit.sv), every element boundary registered.
def wfc_kit_buses(role, host, far=None, crp=False):
    # crp (--wfc-crp): dsfd_wfc_cr2 die ports: credit returns (t_lic / f_loc / f_swc / f_src) in place of the kit's grants,
    # same bit counts; link and VM land in dsfd_wfc_crp
    if crp:
        b = [('collective', 'wfc', 514, 't_wfc', 'f_li'), ('wfc', 'collective', 1, 't_lic', 'f_wfcc'),
             ('wfc', 'collective', 514, 't_lo', 'f_wfc'), ('collective', 'wfc', 1, 't_wfcc', 'f_loc'),
             ('wfc', 'vm', 544, 't_sw_sr', 'f_wfc'), ('vm', 'wfc', 516, 't_wfc', 'f_swc_swa_src_srq'),
             ('wfc', 'capture', 53, 't_ks', 'f_wfc'), ('capture', 'wfc', 54, 't_wfc', 'f_kd')]
        if role == 'source' and host:
            b += [('host', 'wfc', 55, 't_wfc_c', 'f_c'), ('wfc', 'host', 53, 't_tok', 'f_wfc_tok')]
        return _sseq_rebind(tuple(b), host)
    # far 's0' (--coll-mtp-far): the SOURCE kit's link-in is the collective MTP lane's token return (t_mrt {data, valid}
    # / f_mrt grant; kit TOKIN 1) and the accept word t_macc goes to the host
    b = ([('collective', 'wfc', 513, 't_mrt', 'f_mrt'), ('wfc', 'collective', 1, 't_mrg', 'f_mrt')] if far == 's0' else
         [('collective', 'wfc', 514, 't_wfc', 'f_li'), ('wfc', 'collective', 1, 't_lir', 'f_wfcg')]) + [
         ('wfc', 'collective', 514, 't_lo', 'f_wfc'), ('collective', 'wfc', 1, 't_wfcg', 'f_lor'),
         ('wfc', 'vm', 560 if WFC_PRICED else 544, 't_sw_sr', 'f_wfc'), ('vm', 'wfc', 1029 if WFC_PRICED else 516, 't_wfc', 'f_sw_sr'),
         ('wfc', 'capture', 53, 't_ks', 'f_wfc'), ('capture', 'wfc', 54, 't_wfc', 'f_kd')]
    if WFC_PRICED and host:      # contract v16: the kit's fault flags {proto_fault, lnk_ft, 0, vmx_ft} reach the die fault collector
        b += [('wfc', 'host', 4, 't_ft', 'f_wfc_ft')]
    if far == 's0' and host:
        b += [('collective', 'host', 57, 't_macc', 'f_macc')]
    if role == 'source' and host:
        b += [('host', 'wfc', 55, 't_wfc_c', 'f_c'), ('wfc', 'host', 53, 't_tok', 'f_wfc_tok')]
    return _sseq_rebind(tuple(b), host)


def _sseq_rebind(b, host):
    """--stage-seq: the kit's start / done go to dsfd_stage_seq (no capture placeholder pins); program load and status on
    the host cfg path.  The sequencer's engine cmd / dn ports are bound by the engine-adapter work (s81-ctl-1011)."""
    if not STAGE_SEQ:
        return b
    b = tuple(x for x in b if not (set(x[:2]) == {'wfc', 'capture'}))
    b += (('wfc', 'sseq', 53, 't_ks', 'f_ks'), ('sseq', 'wfc', 54, 't_kd', 'f_kd'))
    if host:
        b += (('host', 'sseq', 36, 't_sseq_pw', 'f_pw'), ('host', 'sseq', 8, 't_sseq_plen', 'f_plen'),
              ('sseq', 'host', 6, 't_st', 'f_sseq_st'))
    return b


SEEDL = False                   # --seedl (mtp-dsbind 2026-10-10): DSpark primary die (--draft P) seed-descriptor consumer
SEEDL_UM = (259.2, 259.2)       #   contract physical/s81_ph_views/specs/dsfd_mtp_seed_launch.json
# dsfd_mtp_seed_launch exact ports (rtl/dsrom_sys/mtp/ot_dsrom_mtp_seed_launch.sv): seed descriptor {77, valid} from the
# collective MTP lane (t_mrs) + grant back (f_mrs); VM hidden-row read: request {addr 24, valid} grant protocol + grant,
# in-order response {1024, valid}; x beats {x_b, x_a, valid} 1025 to the VM's seed staging (seed elements) + die join
# {done, rdy} 2; program start event {56, v} 57 to the VM / block issue; host: user clear 11 in, sticky faults 4 out.
# On the primary die the lane's token-return class and accept word are observation only: -> host.
SEEDL_BUSES = (('collective', 'seedl', 78, 't_mrs', 'f_mrs'), ('seedl', 'collective', 1, 't_mrs', 'f_mrs'),
               ('seedl', 'vm', 25, 't_vrq', 'f_seedl_rq'), ('vm', 'seedl', 1, 't_seedl_rqg', 'f_vrq'),
               ('vm', 'seedl', 1025, 't_seedl_rs', 'f_vrs'), ('seedl', 'vm', 1025, 't_x', 'f_seedl_x'),
               ('vm', 'seedl', 2, 't_seedl_xj', 'f_x'), ('seedl', 'vm', 57, 't_ps', 'f_seedl_ps'))
SEEDL_HOST_BUSES = (('host', 'seedl', 11, 't_seedl_clr', 'f_clr'), ('seedl', 'host', 4, 't_flt', 'f_seedl_flt'),
                    ('collective', 'host', 513, 't_mrt', 'f_mrt'), ('host', 'collective', 1, 't_mrg', 'f_mrt'),
                    ('collective', 'host', 57, 't_macc', 'f_macc'))
HROW_SRC = None                 # --hrow-src P (mtp-dsbind 2026-10-11): stage die of layer 37 + P: dsfd_mtp_hrow_src
HSRC_UM = (259.2, 259.2)        #   contract physical/s81_ph_views/specs/dsfd_mtp_hrow_src.json
# wfc kit t_hep {v, user, pos, epoch} 36 (dsfd_wfc_kit HEP 1, mtp-wfc 248f39b23); VM read like the seed client; the
# hidden lane {flit 514, valid} + grant to the collective's dedicated hidden lane (t_mhs / f_mhs: one more LCR lane tile
# + adapter in the collective composition, OPEN in its owner's tree, as on the primary die)
HSRC_BUSES = (('wfc', 'hrsrc', 36, 't_hep', 'f_hep'),
              ('hrsrc', 'vm', 25, 't_vrq', 'f_hsrc_rq'), ('vm', 'hrsrc', 1, 't_hsrc_rqg', 'f_vrq'),
              ('vm', 'hrsrc', 1025, 't_hsrc_rs', 'f_vrs'),
              ('hrsrc', 'collective', 515, 't_hp', 'f_mhs'), ('collective', 'hrsrc', 1, 't_mhsg', 'f_hpg'))
HSRC_HOST_BUSES = (('hrsrc', 'host', 2, 't_flt', 'f_hsrc_flt'),)
HROW = False                    # --hrow (mtp-dsbind 2026-10-10): with --seedl, the main-hidden row store dsfd_mtp_hrow
HROW_UM = (2998.08, 1769.04)     #   contract physical/s81_ph_views/specs/dsfd_mtp_hrow.json (SE service slot, N-face ports)
HROW_TOP_REF = 950.4            # el1011-ds-mtp rev 3 (30 hardened banks): the store grows DOWN into the slot's free PHY / ctrl
                                #   space; its N face (pins, the end-block corridor above it) stays where the 950.4 um store had it
# the seed client reads the row store, not the VM; the 3 part links arrive from the collective's MTP part lanes
# (t_mhp<k> {flit 514, valid} / f_mhp<k> grant: three more LCR lane tiles + adapters in the MTPL composition, OPEN in
# the collective composition owner's tree)
SEEDL_BUSES_HROW = tuple(b for b in SEEDL_BUSES if 'vm' not in (b[0], b[1]) or b[2] in (1025 if b[3] == 't_x' else -1, 2, 57)) + (
    ('seedl', 'hrow', 25, 't_vrq', 'f_vrq'), ('hrow', 'seedl', 1, 't_vrq', 'f_vrq'), ('hrow', 'seedl', 1025, 't_vrs', 'f_vrs'))
HROW_BUSES = tuple(('collective', 'hrow', 515, 't_mhp%d' % k, 'f_hp%d' % k) for k in range(3)) + (
    ('hrow', 'collective', 3, 't_hpg', 'f_mhpg'),)      # the three part grants, one 3-bit lane back
SEEDL_BUSES_SPINE = tuple(b for b in SEEDL_BUSES_HROW if 'hrow' not in b[:2])     # spine-internal (hub chains)
HROW_LANES = tuple(b for b in SEEDL_BUSES_HROW if 'hrow' in b[:2]) + HROW_BUSES     # forwarded lanes to the SE slot
HROW_HOST_BUSES = (('host', 'hrow', 11, 't_hrow_clr', 'f_clr'), ('hrow', 'host', 3, 't_flt', 'f_hrow_flt'))
COLL_MTP_FAR = None             # --coll-mtp-far s0 (mtp-wfc 2026-10-10): the S0 die's end of the head die's MTP lane
MTP_SEQ_RTT = False             # --mtp-seq-rtt (mtp-wfc 2026-10-10): head slab master dsfd_mtp_seq_rtt (RTT-sized grant
                                #   receivers for the head631 relay chains; mtp-seq-rtt-native-61b4bc729 CLOSED), same ports
SER_STAGE_UM = 640.0            # mtp-wfc 2026-10-10: 0.9 GHz (1,111.1 ps) station spacing = LINK_STAGE_UM x (1111.1 - 261) /
                                #   (833.3 - 261) on the SS wire model 261 ps + 1.135 ps/um (504 um at 833 ps; 749 um at 1,111 ps)
STAGE_SEQ = False               # --stage-seq (main decision A 2026-10-11): kit start / done through dsfd_stage_seq
SSEQ_MM2 = 0.06                 #   ot_s81_stage_seq NOPS 128 program (3.6 kbit) + 12 x (FQ 4 + credits) queues; preliminary
WFC_CRP = False                 # --wfc-crp (main 10-11): WFC slab master dsfd_wfc_cr2 (credit-boundary tile dsfd_wfc_crp + kit)
WFC_KIT = False                 # --wfc-kit (mtp-wfc 2026-10-10, default off): the WFC slab as the kit's closed elements
WFC_ROLE = 'stage'              #   'source' on the S0 die (--ctrl-role source), else 'stage'
WFC_VMX_UM = (248.4, 241.92)    #   dsfd_wfc_vmx contract outline (prd-c39e235bb-o292-r2 CLOSED)
WFC_LNK_UM = (216.0, 151.2)     #   dsfd_wfc_lnk (b-0cd6caa1b CLOSED)
WFC_TOK_UM = (108.0, 108.0)     #   dsfd_wfc_tok_hard (e829cb457-r2 CLOSED; dsfd_wfc_tok contract outline)
# sequencer (mtp-lead 2026-10-09, native binding): widths from the ACTUAL dsfd_mtp_seq wrapper ports
# (rtl/dsrom_sys/mtp/dsfd_mtp_tops.sv, NW 21 / USER_W 10 / FLIT 512; each grant port = data + valid + grant):
#   capture -> mtp   RESULT flit f_rv/f_rd/t_rg                                  512 + 2 = 514
#   mtp -> collective token return t_tv/t_td/f_tg 514 + seed to the draft primary t_sv/t_sd/f_sg (SW = 10+3*21+4 = 77)
#                    79 + accept word t_acc (2*21+10+5 = 57, from flops)          514 + 79 + 57 = 650
#   vm -> mtp        rows-ready f_wv/f_wd/t_wg 12 + draft-head result f_qv/f_qd/t_qg (DW = 10+3+21 = 34) 36 = 48
#   mtp -> vm        draft-head step t_hv/t_hd/f_hg                                34 + 2 = 36
# (replaces the 64/128/128/576 aggregates of 2026-10-08, which did not describe the wrapper).
# The grant pins travel in the reverse direction from their data/valid pins.
# Counting grants in a forward aggregate preserves total bits but omits the
# physical return paths. Separate each ordered slab pair (native binding 2026-10-10).
MTP_SEQ_BUSES = (('capture', 'mtp', 513, 't_mtp', 'f_capture'),
                 ('mtp', 'capture', 1, 't_capture', 'f_mtp'),
                 ('mtp', 'collective', 648, 't_collective', 'f_mtp'),
                 ('collective', 'mtp', 2, 't_mtp', 'f_collective'),
                 ('vm', 'mtp', 47, 't_mtp', 'f_vm'),
                 ('mtp', 'vm', 37, 't_vm', 'f_mtp'))
# MTP-DIE (2026-10-08, results/arch/mtp_die_20261008): die-level homes of the DSpark MTP functions (default off: the
# r3 / r4 dies stay reproducible).
CTRL_SLAB = False
CTRL_ROLE = 'layer'
CTRL_MM2 = 0.15                 # preliminary shell/queue reservation; no routed-area claim
CTRL_BINDINGS = None
# --ctrl-adapters (s81-ctl-1011, ADAPTER_CONTRACT_1011): with --stage-seq (the WFC agent's dsfd_stage_seq slab 'sseq',
# decision A), every sequencer engine port c<e> / d<e> / s<e> is bound to the slab endpoint masters listed in
# physical/s81_ctrl/die_ctrl_bindings.json (c_cmd / c_done / c_st; *_c slab masters), staged by common-clock stations
# (pulse nets: fixed latency, no back-pressure); the fld path adds capture t_cd -> gather f_cd (drained event) and
# gather t_xgo -> VM f_xgo (field broadcast go).  The die gate tools/s81_ctrl/die_ctrl_gate.py runs after the build and
# FAILS the generator on any unbound engine, sequencer port or die_port_audit finding (no placeholder pins).
CTRL_ADAPTERS = False
CTRL_C_MASTERS = dict(gather='dsfd_sp_gather_c', capture='dsfd_sp_capture_c', collective='dsfd_sp_collective_c',
                      selector='dsfd_bk_selector_c', collector='dsfd_bk_collector_c',
                      # s81die-1011/ctrl: HC (engine 2) endpoint in hc_s = dsfd_sp_hc_c (dsfd_sp_hc, hc_gate PASS); the
                      # su_hc contract v2 makes HC one logical slab (hc_n folds into it when the suhc floorplan lands)
                      hc_s='dsfd_sp_hc_c', su_s='dsfd_sp_su_c', eng='dsfd_engram_c')
LANE_PINS = 0                   # --lane-pins [P] (s81-die v15): a hub port on a straight VCH station lane takes its pins centred on
                                #   that lane (P-track pitch) on both slabs; lanes are allocated without overlapping pin spans
PEER_SPAN_CENTRE = False        # --peer-span-centre (s81-die-iter 2026-10-12): wide face-to-face groups centred on the span shared with the peer
RTL_HUB_WIDTHS = False          # --rtl-hub-widths (s81die-1011/ctrl, die lead decision 2026-10-11)
# the gated hub masters' real interfaces (DIE_FLD_GATE: 12 root lanes gather -> capture, the tiled capture's VM writes;
# the collective contract results/rtl/s81_ph_20261006/collective/contract.json: f_vm 592 / ts 3 in, t_vm 2,100 out)
RTL_HUB_BITS = {('gather', 'capture'): 6947, ('capture', 'vm'): 13376, ('collective', 'vm'): 2100}
RTL_ABUT_GAP = 21.6             # um between the abutting wide pairs (pin flops on both faces; no logic between)
RTL_HUB_EXTRA = (('vm', 'collective', 592, 't_collective', 'f_vm'), ('vm', 'collective', 3, 'tcs', 'ts'))
# --static-seams (S-DIE r11 2026-10-15, owner static-cycle rule 10-14 18:59): the VM <-> collective seam of the static
# masters (rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm_static.sv: f_collective 2204, f_crq 15, t_crs 513; static collective
# dsfd_sp_collective_static_c: t_vm 2204, t_crq 15, f_crs 513).  The credit push vm.t_collective[592] and the 'room'
# back-pressure vm.tcs[3] are dropped; the HC y bus loses its ready (hc_s.y_rdy -> collective.f_hc_yr) and gains the
# registered row identity collective.t_hc_tag[32] -> hc_s.y_tag (the static HC POST consumer's slot, owner s_func).
STATIC_SEAMS = False
RTL_HUB_EXTRA_STATIC = (('collective', 'vm', 15, 't_crq', 'f_crq'), ('vm', 'collective', 513, 't_crs', 'f_crs'))
STATIC_HC_TAG = ('collective', 'hc_s', 32, 't_hc_tag', 'y_tag')
STATIC_COLLECTIVE_MASTER = 'dsfd_sp_collective_static_c'
STATIC_COLLECTIVE_RTL = 'rtl/dsrom_sys/s81_static_collective/dsfd_sp_collective_static_c.sv'
STATIC_COLLECTIVE = False       # --static-collective: swap the hub collective master (RTL must be on the source tree)
PIN_OVERRIDES = None            # --pin-overrides (S-DIE r11 10-15): adopted GEO-S face re-assignments, see load_pin_overrides
PIN_OVERRIDES_APPLIED = {}


def load_pin_overrides(path):
    """{'by_inst': {inst: {port: rule}}, 'by_master': {...}, 'record': ...}; rule = {'shift_um': d} along the port's
    face, or {'face': F, 'coord_um': c} absolute.  Only candidates with adopted=true enter; every entry names its source."""
    p = Path(path)
    p = p if p.is_absolute() else ROOT / p
    d = json.loads(p.read_text())
    assert d.get('schema') == 'opentallas.s81.pin_overrides.v1', path
    out = dict(by_inst={}, by_master={}, record=dict(path=str(path), adopted=[], not_adopted=[]))
    for c in d['candidates']:
        (out['record']['adopted'] if c.get('adopted') else out['record']['not_adopted']).append(c['id'])
        if not c.get('adopted'):
            continue
        for e in c['pins']:
            key, nm = ('by_inst', e['inst']) if 'inst' in e else ('by_master', e['master'])
            rule = {k: e[k] for k in ('shift_um', 'face', 'coord_um') if k in e}
            assert rule, e
            prev = out[key].setdefault(nm, {}).get(e['port'])
            assert prev is None or prev == rule, ('conflicting pin overrides', nm, e['port'], prev, rule, c['id'])
            out[key][nm][e['port']] = dict(rule, cand=c['id'])
    return out


def _apply_pin_overrides(Mx, it):
    """--pin-overrides on one generated master (first instance `it`): shift / place the named ports' face centres."""
    if not PIN_OVERRIDES:
        return
    rules = dict(PIN_OVERRIDES['by_master'].get(Mx.name, {}))
    rules.update(PIN_OVERRIDES['by_inst'].get(it.name, {}))
    rec_ = _assigned_record(Mx.name)
    for port, r in rules.items():
        assert not (rec_ and port in rec_.get('ports', {})), ('pin override on a die-owned assigned pin: change the pin '
                                                              'file instead', Mx.name, port, r['cand'])
        sp_ = Mx.ports.get(port)
        assert sp_ is not None and sp_[0] == 'face', ('pin override on a port without a generated face pin', Mx.name, port)
        _, bits, f, ly, c, pt = sp_
        if 'coord_um' in r:
            f2 = r.get('face', f)
            c2 = r['coord_um']
            ly = ('M5' if f2 in 'NS' else 'M4') if f2 != f else ly
        else:
            f2, c2 = f, c + r['shift_um']
        L = Mx.w if f2 in 'NS' else Mx.h
        half = max(1, math.ceil(bits / _LAY_K[0])) * _LAY_K[0] * 0.048 * pt / 2
        assert half <= c2 <= L - half, ('pin override leaves the face', Mx.name, port, f2, round(c2, 3), round(L, 3), r['cand'])
        Mx.ports[port] = ('face', bits, f2, ly, c2, pt)
        PIN_OVERRIDES_APPLIED[(Mx.name, port)] = dict(inst=it.name, cand=r['cand'], face=f2, old=round(c, 3), new=round(c2, 3))


MIX4_SLOT = None                # --mix4-slot X,Y,W,H: Engram MIX4 home reservation (screen; real master pins pending sizing)
RTL_BIND = False                # --rtl-bind (s81-die-rtl-bind 2026-10-14)
# S-BIND 2026-10-15: with --static-collective the rest of the static collective's die ABI is bound too: per-leaf clock
# entries ck_control 5 / ck_lane 8 / ck_hc_lane 16 (stream), the TP4 rank from a die pad 'rank' (package strap: every die
# of a group carries the same netlist), host channel 515 / 77 (no t_cr / h_crn credit bits), WFC link data both ways
# without the grants t_lir / t_wfcg.  Peers whose RTL still carries a grant / credit port (dsfd_wfc_stg f_lor,
# dsfd_host_c 516 / 81) then FAIL the port-bind check until their static successors are bound (no tie, no adapter).
# --static-coll = --static-seams --static-collective.
STATIC_COLL_CLOCKS = (('ck_control', 5), ('ck_lane', 8), ('ck_hc_lane', 16))
# --suhc-static-issue (S-BIND 2026-10-15, owner static-cycle rule): the SU / HC slab endpoints issue on the compiler's
# command edge (die build define DSFD_SUHC_STATIC_ISSUE: no f_inp port); the VM -> SU / HC t_inp dependency nets (ready-
# driven issue, VOID under the static rule) leave the die
SUHC_STATIC_ISSUE = False
PQ_RTL_MASTER = 'dsfd_sp_pq_n'  # --rtl-bind PQ slot: rtl/dsrom_sys/s81_die_bind/dsfd_sp_pq_n.sv (native core cluster + ROM / lane leaves)


def pq_rtl_clock_ports(manifest='physical/s81_die_rtl/layer1.f'):
    """clock-entry ports of dsfd_sp_pq_n under the die RTL manifest's OT_PQ_* defines (one source of truth), bit-sliced"""
    defs = set(re.findall(r'^\+define\+(\w+)', (ROOT / manifest).read_text(), re.M))
    vec = [('ck_aq', 2), ('ck_ix', 4), ('ck_bc', 16 if 'OT_PQ_BC_SLICED' in defs else 4)]
    if 'OT_PQ_QB_PHYS_SPLIT' in defs:
        vec.append(('ck_qb_aux', 4))
    if 'OT_PQ_AQ_PHYS_SPLIT' in defs:
        vec.append(('ck_aq_aux', 16))
    if 'OT_PQ_IX_PHYS_SPLIT' in defs:
        vec.append(('ck_ix_read', 32 if 'OT_PQ_IX_BANK_SPLIT' in defs else 16))
    return ['ck_ctl', 'ck_qb', 'ck_fault', 'ck_lane'] + [f'{n}[{i}:{i}]' for n, w in vec for i in range(w)]


_RTL_CLOCK_CACHE = {}


def rtl_clock_reset_entries(master, manifest='physical/s81_die_rtl/layer1.f'):
    """S-BIND 2026-10-15: the leaf clock / reset entry ports of a die master read from its RTL header under the die
    manifest (files + defines; one source of truth with tools/die_port_bind.py), bit-sliced.  Returns None when the
    master has a scalar 'ck' port (legacy two-port form) or is absent from the manifest.  Classes: input ports named
    ck_* / cks (clock) and rss / rss_* / rst_* (reset); domain by suffix: '_t' / cks / rss = stream, '_s' = serial."""
    if master in _RTL_CLOCK_CACHE:
        return _RTL_CLOCK_CACHE[master]
    sys.path.insert(0, str(ROOT / 'tools'))
    import die_port_bind as DPB
    files, defines, _ = DPB.load_manifest(ROOT / manifest)
    env_def = {d: '1' for d in defines}
    out = None
    for f_ in files:
        if not Path(f_).exists():
            continue
        txt = Path(f_).read_text()
        if not re.search(r'\bmodule\s+%s\b' % re.escape(master), txt):
            continue
        for md in DPB.parse_modules(DPB.preprocess(txt, env_def), f_):
            if md.name != master:
                continue
            if 'ck' in md.ports:
                out = None
                break
            env = {}
            for k_, v_ in md.params.items():
                try:
                    env[k_] = DPB.ev(v_, env)
                except Exception:
                    pass
            out = dict(clock=defaultdict(list), reset=defaultdict(list))
            for pn in md.order:
                d_, rng = md.ports[pn]
                if d_ != 'input':
                    continue
                cls_ = 'clock' if (pn == 'cks' or pn.startswith('ck_')) else \
                    'reset' if (pn == 'rss' or pn.startswith(('rss_', 'rst_'))) else None
                if cls_ is None:
                    continue
                dom_ = 'serial' if pn.endswith('_s') else 'stream' if (pn.endswith('_t') or pn in ('cks', 'rss')) else None
                assert dom_, ('rtl_clock_reset_entries: no domain suffix', master, pn)
                w_ = 1
                for hi_, lo_ in rng:
                    w_ *= abs(DPB.ev(hi_, env) - DPB.ev(lo_, env)) + 1
                out[cls_][dom_] += [pn] if (w_ == 1 and not rng) else [f'{pn}[{i_}:{i_}]' for i_ in range(w_)]
            break
        if out is not None:
            break
    _RTL_CLOCK_CACHE[master] = out
    return out


def rtl_has_port(master, port, manifest='physical/s81_die_rtl/layer1.f'):
    """True when the master's RTL header under the die manifest declares PORT (a die net is only added to a real port)."""
    if not master:
        return False
    sys.path.insert(0, str(ROOT / 'tools'))
    import die_port_bind as DPB
    files, defines, _ = DPB.load_manifest(ROOT / manifest)
    env_def = {d: '1' for d in defines}
    for f_ in files:
        if Path(f_).exists() and re.search(r'\bmodule\s+%s\b' % re.escape(master), Path(f_).read_text()):
            for md in DPB.parse_modules(DPB.preprocess(Path(f_).read_text(), env_def), f_):
                if md.name == master:
                    return port in md.ports
    return False


DUAL_CLOCK_MASTERS = ('dsfd_sp_gather_c', 'dsfd_sp_capture_c', 'dsfd_stage_seq_c', 'dsfd_stage_seq_c8',
                      'dsfd_stage_seq_static_c', 'dsfd_stage_seq_static_c8', 'dsfd_host_c')
CTRL_SVC_MASTER = 'dsfd_svc_c'        # svc_<st> under --ctrl-adapters: j / jd job pins from dsfd_svc_join (engine 4)
CTRL_SVC_JOIN = 'dsfd_svc_join'


def ctrl_adapter_buses(hb):
    """--ctrl-adapters: (a, b, bits, port a, port b) hub buses of the engine command plane (ADAPTER_CONTRACT_1011):
    sseq c<e> 85 -> slab c_cmd, slab c_done 9 -> d<e>, slab c_st 2 -> s<e> for every engine whose bindings-file
    master is a slab of this die; the fld path's capture -> gather drained event and gather -> VM field go."""
    bind = json.loads((ROOT / 'physical/s81_ctrl/die_ctrl_bindings.json').read_text())
    eng = dict(fld=0, su=1, hc=2, coll=3, svc=4, sel=5, col=6, hop=7, head=8, emb=9, eng=10, spare=11, vm=12)
    out = []
    for e, k in eng.items():
        if e in ('hop', 'vm') and not RTL_BIND:
            continue          # F4 (--rtl-bind): the hop engine's endpoint lives in the WFC stage kit cluster (dsfd_wfc_hop_ep)
        # band blocks (bk_selector S / bk_collector N) sit in other clock regions across the die: their command lanes
        # need forwarded-clock lane chains with end blocks (as the svc -> selector / collector chains), not common-clock
        # hub stations -- NOT BUILT YET: left unbound, so the die control gate reports sel / col UNBOUND (FAIL)
        for slab_ in [s_ for s_, it in hb.items() if it.master in bind['engines'].get(e, {}).get('masters', [])
                      and it.kind not in ('band_blk', 'svc')]:     # band / svc-band slabs: forwarded ctrl lanes
            out += [('sseq', slab_, 85, f'c{k}', 'c_cmd'), (slab_, 'sseq', 9, 'c_done', f'd{k}'),
                    (slab_, 'sseq', 2, 'c_st', f's{k}')]
    if 'gather' in hb and hb['gather'].master == 'dsfd_sp_gather_c':
        out += [('capture', 'gather', 12, 't_cd', 'f_cd'), ('gather', 'vm', 11, 't_xgo', 'f_xgo')]
    if 'hc_s' in hb and hb['hc_s'].master == 'dsfd_sp_hc_c' and not SUHC_STATIC_ISSUE:
        # HC dependency net (dsfd_sp_hc inp): the VM's row-completion event for the HC head descriptor's operands
        out += [('vm', 'hc_s', 1, 't_inp_hc', 'f_inp')]
    if 'su_s' in hb and hb['su_s'].master == 'dsfd_sp_su_c' and not SUHC_STATIC_ISSUE:     # SU dependency net (dsfd_sp_su inp), same rule
        out += [('vm', 'su_s', 1, 't_inp_su', 'f_inp')]
    return tuple(out)


def _ctrl_native_buses(m, bus):
    """Bind every native shell port from explicit endpoints; ck/rs use the real stream clock tree."""
    it = m['hub']['stage_ctrl']
    names = {x.name for x in m['insts']} | {'TOP'}
    for port, spec in CTRL_BINDINGS['ports'].items():
        if port in ('ck', 'rs'):
            continue
        endpoint = tuple(spec['endpoint'])
        if endpoint[0] not in names:
            raise ValueError('ctrl endpoint does not exist: %s %s' % (port, endpoint))
        eps = [(it.name, port), endpoint] if spec['direction'] == 'output' else [endpoint, (it.name, port)]
        bus('stage_ctrl_' + port, 'stage_ctrl', spec['bits'], eps)


# MD-2 P2 draft die A (mtp-draftdie 2026-10-09): dsfd_p2 = ot_mtp_p2_prefix_path (rtl/experimental/
# mtp_p2_ordered_20261009) ports, bus = data + valid (+ the ready back on the reverse bus):
#   collective -> p2  start (identity 74 + ids 27 + v) 102 + lane 1 = die B expert output over the in-package UCIe
#                     (identity 74 + expert 9 + shared 1 + last 1 + word 7 + data 512 + v 1 = 605) + abort 1
#                     + out_r (the primary link's return credit) 1                                         709
#   vm -> p2          lane 0 = this die's expert output                                                    605
#   p2 -> collective  ret_row to the primary (data 512 + identity 74 + word 7 + last 1 + v 1 = 595) + start_r 1
#                     + lane-1 ready 1 + done / fault / corrected 3                                        600
#   p2 -> vm          lane-0 ready                                                                           1
P2_BUSES = (('collective', 'p2', 709, 't_p2', 'f_collective'), ('vm', 'p2', 605, 't_p2', 'f_vm'),
            ('p2', 'collective', 600, 't_collective', 'f_p2'), ('p2', 'vm', 1, 't_vm', 'f_p2'))
# mtp-wfc 2026-10-10 (fixlat a7961fc6d, rtl/dsrom_sys/mtp/dsfd_mtp_partner_ep.sv, dsfd_p2_lnk.sv): RTT-sized ends.
MTP_EP = False                  # --mtp-ep: head-die dsfd_cap_mtp_ep / dsfd_vm_mtp_ep slabs carry the sequencer buses
MTP_EP_MM2 = 0.112              #   each a 64.8 um strip (cap_ep E face 55 um of pins) of the hub column (cap: 513 b pin flops; vm: D26 35 b receiver)
MTP_SEQ_EP_BUSES = tuple((('cap_ep' if a == 'capture' else 'vm_ep' if a == 'vm' else a),
                          ('cap_ep' if b == 'capture' else 'vm_ep' if b == 'vm' else b), w, pa, pb)
                         for a, b, w, pa, pb in MTP_SEQ_BUSES) + (
    ('capture', 'cap_ep', 513, 't_cap_ep', 'f_c_r'), ('cap_ep', 'capture', 1, 't_c_rr', 'f_cap_ep'),
    ('vm_ep', 'vm', 37, 't_c_h', 'f_vm_ep'), ('vm', 'vm_ep', 47, 't_vm_ep', 'f_c_wq'))
P2_LNK = False                  # --p2-lnk: draft-A P2 slab = dsfd_p2 core + dsfd_p2_lnk (die side 12/14 D30, 8/9 D21)
P2_LNK_MM2 = 0.38               #   ~40k receiver flops (2 x 604 b x D30 + 101 b x D21); 220 um strip (E face 199 um of pins)
P2_LNK_BUSES = (('vm', 'p2_lnk', 605, 't_p2', 'f_l0'), ('p2_lnk', 'vm', 1, 't_vm', 'f_p2g'),
                ('collective', 'p2_lnk', 707, 't_p2', 'f_l1s'), ('p2_lnk', 'collective', 2, 't_collective', 'f_p2g'),
                ('p2_lnk', 'collective', 595, 't_o', 'f_p2'), ('collective', 'p2_lnk', 1, 't_p2g', 'f_og'),
                ('p2_lnk', 'p2', 1313, 't_c', 'f_lnk'), ('p2', 'p2_lnk', 598, 't_lnk', 'f_c'))
P2_OUTLINE_UM = (560.0, 460.0)  # the larger of the two first P2 routes (mtp-p2-path-{a 500x420, b 560x460}-91473d972)
P2_SLAB_MM2 = P2_OUTLINE_UM[0] * P2_OUTLINE_UM[1] / 1e6
DRAFT_SIDE = None               # --draft A|B (MD-2 P2 draft die; None = a stage die)
DRAFT_CONTENT = dict(A='mtp.0 experts 0..127 + mtp.2 experts 0..63 (rank-k row quarter), P2 expert sum in id order',
                     B='mtp.1 experts 0..127 + mtp.2 experts 64..127 (rank-k row quarter), outputs to die A over UCIe',
                     P='DSpark primary rank k: mtp.0..2 attention / router / shared expert (L0 runs, one pair a run per '
                       'phase group) + hc HE / CROM providers + mtp.0 seed projection; board SerDes to the 5 row packages')
DRAFT_IMAGE_P = dict(tool='tools/dsrom_s81_mtp_binding.py', layout='S81 L0 superrow runs, one pair a run per phase group',
                     storage_pairs=1792, words_per_die=2614272, words_capacity=1792 * 8192, fill=0.178,
                     record='results/uarch/dsrom_s81_mtp_binding_20261010')
DRAFT_IMAGE = dict(tool='tools/dsrom_mtp_draft_images.py', layout='rowpack whole-superrow (dsrom_mtp_p2_rowpack)',
                   storage_pairs=1792, words_per_die=13762560, words_capacity=1792 * 8192, fill=0.9375,
                   images_per_side=4, note='8 distinct images (side x rank) serve the 40 dies (5 row replicas)')
# MTP defaults (mtp-lead 2026-10-09).  MTP_SEQ_DEFAULT: the head-die sequencer is ON (dsfd_mtp_seq CLOSED c67a71fe5
# SS +52.37 / FF +5.76).  WFC_HARD_DEFAULT: ON since the WFC kit is complete (mtp-draftdie 2026-10-09 evening): SOURCE
# HARD partner mtp-wfc-src-hard-mxb-910e67c7b-tc-cx CLOSED TT +152.31 / FF +4.02 / DRC 0 (view
# physical/s81_ph_views/closed/ot_dsrom_wfc_tokpipe_src, DIEAREA 293.734 x 293.734 um), STG tokpipe
# mtp-wfc-stg-tokpipe-9f7a7f35e-tc CLOSED (DIEAREA 190.41 x 190.41 um), HARD wfc_tok, wfc_lnk, wfc_vmx closed.
# --no-wfc-hard reproduces the pre-MTP stage dies (soft reservation on the scan die only).
WFC_HARD_DEFAULT = True
MTP_SEQ_DEFAULT = True
WFC_HARD = False                # --wfc-hard: the wavefront controller (ot_rom_pkg_ctrl_wfc, src r24 + stg r11 CLOSED) as a
                                #   BOUND slab on EVERY layer-class die (layer AND layer1: every stage needs it; the soft
                                #   0.456 mm2 reservation sat on the 4-stack scan die only), wired to VM / capture /
                                #   collective (link in / out), sized from the routed outlines (src 78,190.7 + stg
                                #   35,941.7 um2 side by side, 17.28 um halos)
WFC_SRC_UM = (293.734, 293.734)  #   closed SOURCE ot_dsrom_wfc_tokpipe_src (mtp-wfc-src-hard-mxb-910e67c7b-tc-cx DEF DIEAREA)
WFC_STG_UM = (190.41, 190.41)    #   closed STG tokpipe (mtp-wfc-stg-tokpipe-9f7a7f35e-tc DEF DIEAREA)
WFC_HALO = 17.28
#   slab height: the two closed blocks side by side (src + stg + 3 halos = 535.98 um wide of the 1,728 um hub column),
#   the taller (SOURCE) + 2 halos, on the GY grid (was 231.12 from the r24 / r11 outlines 398 x 196.56 / 183 x 196.56)
WFC_SLAB_H = round(math.ceil((max(WFC_SRC_UM[1], WFC_STG_UM[1]) + 2 * WFC_HALO) / 2.16 - 1e-9) * 2.16, 3)
MTP_SEQ = False                 # --mtp-seq: head die: ot_dsrom_mtp_seq (accept NSLOT 8 / NW 17 + draft-chain FSM + acc_n /
                                #   squash word + position / epoch counter + Markov embed lookup control) slab between
                                #   capture and collective, wired to capture (argmax tokens), collective (token return /
                                #   seed / squash), VM (Markov embed row, draft seed x)
MTP_SEQ_MM2 = 0.15              #   audit B1 upper estimate (ctl_f2-class 885 um2 + accept 290 um2 cells; pin-flop banks)
CAPTURE_FACE_UM = 129.6         #   capture slab height with the MTP endpoints (twice the 63 um slab of a 0.109 mm2 capture)
MTP_LINKS = 0                   # --mtp-links N: head die: N extra board SerDes (ot_pdie_serdes, real LEF) for the draft
                                #   fan-out (DP1-EP5 primary on head dies h0..h3: one link per draft ROW package)
PQ_PLACE = False                # --pq-place (S81-DIE 2026-10-07): production PQ roots / core on the mixed221 layer die
PQ_G = False                    # --pq-g (s81-die r6 2026-10-14, PQ return topology G): the gather root leaves are THE roots;
                                #   the frame pq_root row (rstg_pq66 / dsfd_pq_root / rstg_pq68, PQ_ROOT_ROW a tier channel)
                                #   leaves the die, the column return ends at the cfifo as on non-PQ dies; the PQ core stays
                                #   (VM read); its ga / q2f / mdr ports wait for the count-only RWB leaves (UNBOUND, reported)
PQ_ROOTS = False                # = PQ_PLACE and not PQ_G
PQ_CNT = None                   # --pq-cnt FILE (s81-die r6b 2026-10-14, topology G count leaves): the 12 count-only return
                                #   leaves ot_s81_pq_rwbc15 / rwbc2 (rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_rwbc.sv) tile a PQ_CNT_SEAM
                                #   gather | capture seam (physical/s81_die_pins/v19/pq_count_slots.json); each taps 4 b of the
                                #   t_capture root words it counts ({v, tag 2, e}: a second load on those gather -> capture
                                #   bits) + the gather sticky fault; live[3:0] = PQ mdr_o[455:452] and ga 16 / q2f 1 back to the
                                #   PQ core f_cnt ride staged hub lanes (_hub_bus_chain); stream clock clk / rst_n
PQ_CNT_SEAM = 43.2              #   gather S face | capture N face (21.6 RTL abut gap -> 43.2: the W hub column has < 43.2 um of
                                #   height slack, xsp8 r6b): leaves PQ_CNT_LEAF_H tall under the gather (2.16 gap) + a 19.44-um
                                #   relay row above the capture for the leaves' ga / q2f / live lanes
PQ_CNT_LEAF_H = 19.44           #   count-leaf outline height (v20: 142.56 x 19.44, was 38.88 in v19; ~300 flops, pins N 61 / S 17):
                                #   leaves the relay row 9 GY rows, so a 17.28-um station stands on the lattice whatever the capture top
PQ_ROOT_ROW = 241.92            #   root row added to each tier channel 0..TIERS-1 (4.32 + 8.64 + 211.68 + 8.64 + 8.64)
PQ_ROOT_WH = (132.192, 211.68)  #   ret_root_r128 reserved outline.  CLAUDE pq-rootcam 2026-10-08: grown from 133.92 (placed at
                                #   85.8% util, rule ~55-60%) for the pipelined CAM ot_s81_pq_ret_root_cam_p.  ADOPTED PAR 0
                                #   ASPLIT 0 (s81b-pq-rc2-a0-h212-hm10-b761ac1c6: TT +82.06 / FF +4.42 / DRC 0, 49.8% util);
                                #   the PAR 1 variant (241.92 slot) was not adopted
PQ_STN_H = 8.64                 #   return station height (S / N face of the root, full root width)
PQ_CORE_H = 449.28              #   PQ core slot height after the VM (x the hub column width)
PQ_TI, PQ_RO = NODEB, CRET      #   root in = the raw tree word (66); root out carried at the column return width (68):
                                #   the 71-b production word needs cfifo / return-trunk widening (+3 b, open, priced 0)
PQ_VMR = 2069 + 93              #   VM read (S face) + issuer, design.json pq_core faces
PQ_CFG = 458 + 50               #   cfg replica out + fault / status to the gather-side RWBs
PQ_RCNT = 192                   #   row counts in (12 RWB x 16)
PQ_ROMS = 3                     #   2 phase + 1 stream ot_rom_4096x72 (real cfg-ROM LEF) at the core's E end
M2L_UM2_PER_BIT = 33.0           #   d8g1 meso end block outline per lane bit at ~55 % util (measured 16.5-18.4 cells)
PQ_ROOT_W = 17460e-12 * 2.0e6   #   root power: est. area 17,460 um2 at the 2.0 W/mm2 field peak density (budget)
FACE_PIN_INSET = 0.0           # --face-pin-inset: generated face pins 0.048 um inside the outline (abutment EOL)
GEOMETRY_FIX = False            # --geometry-fix: canonical station outlines and bounded bundled pin depth
HOP_R_CC = 410.0                # common-clock reach (budget sheet reach 411-491 um at 833.333 ps SS)
# OT_S81_HOP_R_CC (cont-takeover 2026-10-09, default unset = 410): common-clock hop reach for the frame / column relays.
# Option-B sign-off is TT setup (SS a sensitivity); the TT wire reach exceeds the SS 504 um, so a longer hop cap trades a
# few longer relay segments (timed by the die STA on GRT parasitics) for fewer relays in the 100 %-packed frame cfg bands
# (m221pq_r4c GEN_FAIL rt_0_8a_y1: no legal relay box within 400 um of the driver).
HOP_R_CC = float(os.environ.get('OT_S81_HOP_R_CC', HOP_R_CC))
HOP_R_HUB = 0.0                 # --hop-r-hub UM (s81-die v16): planner reach of the hub-bus bridges (slab pin <-> its chain);
#                                 the planner measures anchor to anchor, the 500-um gate pin to pin: v16 run 1 planned the
#                                 collective -> VM bridge at <= 500 and built 589.8 / 505.1 um hops (Z path, face turns)
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
            + (f'p{int(round(FWD_REACH))}' if FWD_REACH < LINK_STAGE_UM else '') + ('c' if CFIFO_V2 else '') + ('x' if HC_XFACE else '') + ('s' if LINK_SPLIT else '') + ('g' if SEL_XSTG else '') + ('j' if GEOMETRY_FIX else '') + ('p' if PIN_RELAY else '') + ('w' if (CHS or VCH8 != 1209.6 or HC_CORR != 1209.6) else '') + ('v' if VM_FACE_MM2 else '') + ('ctrl' + CTRL_ROLE if CTRL_SLAB else ''))


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


def _rp_log(rec):
    """--relay-progress diagnostics: a relay / station with no forward site (OT_S81_RP_LOG) -- else fail loudly"""
    if not os.environ.get('OT_S81_RP_LOG'):
        return              # the old placement stands; the margin lint (far-side) judges it
    with open(os.environ['OT_S81_RP_LOG'], 'a') as fh_:
        fh_.write(json.dumps(rec) + '\n')


def _q_pin_pt(it, port):
    """--pin-need: die (x, y) of the centroid of q element `it`'s LEF pins for die port `port`, or None"""
    rq = real_lef(Q_LEF)
    nms = [n for n in real_ports_r8().get(rq['name'], {}).get(port, []) if n in rq['pins']]
    if not nms:
        return None
    xs = [(rq['pins'][n][1][0] + rq['pins'][n][1][2]) / 2 for n in nms]
    ys = [(rq['pins'][n][1][1] + rq['pins'][n][1][3]) / 2 for n in nms]
    xc, yc = sum(xs) / len(xs), sum(ys) / len(ys)
    if it.orient == 'MY':
        xc = it.w - xc
    return (it.x + xc, it.y + yc)


def _rsv_tag(bid):
    return 'rt' if bid.startswith('rt_') else ('x' if re.match(r'(xa|xb|cc)_\d+_\d+$', bid) else None)


def _q_banks(p, ex, ey, rq, region, mirror=False):
    """one bank per element face (S below, N above), at the centre of its ports' pins.  --q-x1b (option B, s81-gen
    2026-10-10): x1 is its own S-face bank 'bx' at the x1 pins' centre (element x 400.08-505.44: over the slot station,
    not the packed cfg ROM row), and a mirrored (MY, right-lane) element mirrors the bank x."""
    out = []
    groups = []
    if Q_X1B:
        # A default/legacy q LEF must never silently stand in for the selected
        # split x1 face plan.  A stub is allowed for integration, not closure.
        assert _q_port_face(rq, 'x1') == 'S', '--q-x1b requires x1 on the S face'
        x1c = _q_port_xc(rq, 'x1')
        assert 400.08 <= x1c <= 505.44, ('--q-x1b requires the east-end x1 view', x1c)
    for face in 'SN':
        ports = [q_ for q_ in QBANK_IN + QBANK_OUT if _q_port_face(rq, q_) == face]
        if Q_X1B and face == 'S' and 'x1' in ports:
            ports.remove('x1')
            groups.append(('S', 'bx', ['x1']))
        if ports:
            groups.append((face, f'b{face.lower()}', ports))
    for face, tag, ports in groups:
        xc = sum(_q_port_xc(rq, q_) for q_ in ports) / len(ports)
        if PIN_ALIGN:
            # --pin-align: the bank stands under the EXTENT of its element pins (S bank: x0 / x1 / cfg / go pins span
            # 226.1-284.6, the unweighted port-centroid mean put the 60.5-um bank at 213.8-274.3, 10 um short of x0)
            xs_ = [(rq['pins'][n][1][0] + rq['pins'][n][1][2]) / 2 for q_ in ports for n in real_ports_r8()[rq['name']][q_]
                   if n in rq['pins']]
            assert max(xs_) - min(xs_) <= 60.48 - SHAVE - 0.4, ('qbank narrower than its element pins', face, min(xs_), max(xs_))
            xc = (min(xs_) + max(xs_)) / 2
        if mirror:
            xc = rq['w'] - xc
        w = 60.48
        x = dn(ex + xc - w / 2, GX)
        y = dn(ey - BANK_H - 2.0, GY) if face == 'S' else up(ey + rq['h'] + 1.08, GY)
        out.append(Inst(f'{tag}{p}', f'dsfd_qbank_{face}', x, y, w - SHAVE, BANK_H - SHAVE, kind='qbank',
                        region=region, power_w=0.0))
        BANK_PORTS[out[-1].name] = (face, ports)
    return out


def _bf_hier_nets(m):
    """--bf-hier: the BF pair's partial outputs leave from its columns (old r0 -> west column r, r1 -> east column r),
    the column clock / reset reach all three blocks, and the front <-> column interface is an abutted net per column
    (front c<k> -> column ci: BFH_IFACE 776 b; column qy -> front qy<k>, the registered fault OR)"""
    names = {it.name for it in m['insts']}
    B = m['buses']
    for i, (bid, cls, bits, eps) in enumerate(B):
        eps2 = []
        for inst, port in eps:
            if port in ('r0', 'r1') and f'{inst}w' in names:
                eps2.append((f'{inst}{"w" if port == "r0" else "e"}', 'r'))
            elif cls in ('col_clock', 'col_reset') and f'{inst}w' in names and port in ('ck', 'rs'):
                eps2 += [(inst, port), (f'{inst}w', port), (f'{inst}e', port)]
            else:
                eps2.append((inst, port))
        B[i] = (bid, cls, bits, eps2)
    for it in [x for x in m['insts'] if x.kind == 'bf' and f'{x.name}w' in names]:
        for k, side in ((0, 'w'), (1, 'e')):
            B.append((f'bfh_{it.name}_c{k}', 'bfh', sum(b for _, b in BFH_IFACE), [(it.name, f'c{k}'), (f'{it.name}{side}', 'ci')]))
            B.append((f'bfh_{it.name}_q{k}', 'bfh', 1, [(f'{it.name}{side}', 'qy'), (it.name, f'qy{k}')]))


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


PATH_PICK = os.environ.get('OT_S81_PATH_PICK', '0') == '1'
OPERAND_PATH_PICK = False  # opt-in column A/B/control alternate routes; register counts unchanged
HOPDBG = os.environ.get('OT_S81_HOPDBG', '')
# --relay-tt-reach UM (s81-gen 2026-10-09): option-B sign-off is TT setup (owner 10-07).  A relay / station with no legal box
# inside the SS-derived reach (HOP_R_CC 410 um: the frame / corridor is 100 % packed, m221pq_r4c rt_0_8a_y1) takes the
# nearest legal box within the TT reach instead (real relay, counted in hop_fix.pad_fallback.tt_reach and listed by name in
# hop_fix.tt_reach_relays for the die STA).  TT wire fit 261 ps + 0.76 ps/um: 600 um = 717 ps < 833.333 - 60 ps setup
# uncertainty.  Default None = off (r3 / r4 reproduce byte-identically).
RELAY_TT_REACH = None


def _corr_frac(path, rects, step=20.0):
    tot = ins = 0
    for (x0, y0), (x1, y1) in zip(path, path[1:]):
        L = abs(x1 - x0) + abs(y1 - y0)
        k = max(1, int(L // step))
        for i in range(k + 1):
            t = i / k
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            tot += 1
            ins += any(a - 1e-6 <= x <= c + 1e-6 and b - 1e-6 <= y <= d + 1e-6 for a, b, c, d in rects)
    return ins / tot if tot else 0.0


def _hop_paths(a, b, cor):
    """candidate Manhattan paths a -> b for a die-level hop (s81-gen 2026-10-09, --path-pick): the two L orientations
    and a Z through the centre line of every corridor that spans the turn (vertical corridors: a -> (xc, ay) -> (xc, by)
    -> b; horizontal: a -> (ax, yc) -> (bx, yc) -> b).  The 20.2 mm layer1 hw_SW host chain ran its horizontal-first L
    along y = 14724.7 through packed field frames (station 5 / 53 had no corridor box)."""
    out = [[a, (b[0], a[1]), b], [a, (a[0], b[1]), b]]
    lo_y, hi_y = min(a[1], b[1]), max(a[1], b[1])
    lo_x, hi_x = min(a[0], b[0]), max(a[0], b[0])
    for x0, y0, x1, y1 in cor.values():
        if x1 - x0 < y1 - y0 and y0 <= lo_y + 1e-6 and y1 >= hi_y - 1e-6:       # vertical corridor spanning both ys
            xc = (x0 + x1) / 2
            out.append([a, (xc, a[1]), (xc, b[1]), b])
        if x1 - x0 >= y1 - y0 and x0 <= lo_x + 1e-6 and x1 >= hi_x - 1e-6:     # horizontal corridor spanning both xs
            yc = (y0 + y1) / 2
            out.append([a, (a[0], yc), (b[0], yc), b])
    return out


def _tt_place(P, cx, cy, w_, h_, cur, R_tt, nxt, nreach_tt, horiz):
    """RELAY_TT_REACH tier: nearest legal box anywhere on the die within the TT reach of the previous chain point and
    (when the chain has a next point) of the next one"""
    W, H = DIE
    nr = dict(nxt=nxt, nreach=nreach_tt) if nxt is not None else {}
    for span, rows in ((300.0, 30), (600.0, 60), (1200.0, 120)):
        pl = P.near(cx, cy, w_ + 2.16, h_ + 2.16, [(0.0, 0.0, W, H)], prev=cur, horiz=horiz,
                    reach=R_tt - 10.0, span=span, rows=rows, **nr)
        if pl:
            return (up(pl[0] + 1.08, GX), up(pl[1] + 1.08, GY))
    return None


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
    global RSV_ALLOW
    for i in range(len(B)):
        bid, cls, bits, eps = B[i]
        RSV_ALLOW = _rsv_tag(bid)              # reserved relay sites: return tree ('rt') / slot x lanes ('x')
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
            d0, l0 = by[eps[0][0]], by[e[0]]
            R = HOP_R_FWD if fwd else (HOP_R_HUB if (cls == 'hub' and HOP_R_HUB and not (is_glue(d0.master) and is_glue(l0.master)))
                                       else HOP_R_CC)
            if HOP_PAIR and not fwd and key in HOP_PLAN_R:
                R = min(R, HOP_PLAN_R[key] + HOP_PAIR)     # --hop-pair: the hop's own pair reach (the gate's limit)
            if key in HOP_SPREAD_R:
                R = min(R, HOP_SPREAD_R[key])             # --hop-spread: worst-bit reach of a wide hub bus
            n = math.ceil(L / (R - 20.0) - 1e-9) - 1
            reg = next((x.region for x in (d0, l0) if x.region and x.region.startswith('frame_')), None)
            if fwd:
                fport = 'fi' + e[1][2:] if e[1].startswith('di') else None
                fi_ = fclk_of.get((eps[0][0], e[0], fport)) if fport else None
                if fi_ is None:
                    keep.append(e)
                    rec[cls + ':no_fclk']['hops'] += 1
                    continue
                fdrv = B[fi_][3][0]
            def find(k, n, path, pos, cur, rc, tt):
                """s81-gen: the station search tiers of one hop station (unchanged order); rc counts the fallbacks"""
                Lp = _poly_len(path)
                (cx, cy), dch = _poly_at(path, pos[k])
                horiz = dch in 'EW'
                # s81-die-iter 2026-10-12: a FRAME relay's last station needs only the reach to its load (R - 10), not
                # the remaining path + 40 (a pin-relay rule): on rt_<c>_24b_y1 (y0 -> y1 546 um across a packed slot) the
                # lens <= 490 um from y0 and <= 316 um from y1 was empty, so the TT tier put g_rt_<c>_24b_y1 beside y0
                # and left a 518.4 um hop into y1 (> the 504 um SS reach) on all 128 columns.
                last_nr = (R - 10.0) if (reg is not None and not fwd) else max(Lp - pos[k], PIN_SEG) + 40.0
                NR = dict(nxt=b, nreach=last_nr if k == n - 1 else (n - k) * (R - 10.0)) \
                    if NXT_REACH else {}
                w_, h_ = stn_dims([bits], horiz) if fwd else relay_dims(bits, horiz)
                if not fwd and (reg is not None or not GEOMETRY_FIX):  # frame relay faces chosen later -> square
                    w_ = h_ = max(w_, h_)
                pl = None
                # v6b: stations only in the die's channels (v6 placed them anywhere on the die: 41-54 PA overlaps,
                # and the corridor / VCH crossing got denser); frame relays inside their frame
                if reg is not None and not fwd:
                    f_ = m['frames'][int(reg.split('_')[1])]
                    allowed = [(f_['x'], f_['y'] - 60.0, f_['x'] + COL_W8, f_['y'] + column_height())]
                else:
                    allowed = list(cor.values())
                # v6c: searched with a 2.16 um keep-out each side (the PA track snap moved v6b's tightly packed
                # stations into each other: 41 / 49 / 49 overlaps, all hop-fix stations)
                # v7: a station with no padded spot inside its frame (v6c: rt_63_26b in frame 63) falls back to a
                # 1.08 um, then no keep-out (counted in rc)
                for PAD in (2.16, 1.08, 0.0):
                    for span, rows in ((120.0, 12), (300.0, 30), (600.0, 60), (1200.0, 120)):
                        pl = P.near(cx, cy, w_ + 2 * PAD, h_ + 2 * PAD, allowed, prev=cur, horiz=horiz,
                                    reach=R - 10.0, span=span, rows=rows, **NR)
                        if pl:
                            pl = (up(pl[0] + PAD, GX), up(pl[1] + PAD, GY))
                            break
                    if pl:
                        if PAD < 2.16:
                            rc[f'{PAD:g}'] = rc.get(f'{PAD:g}', 0) + 1
                        break
                if pl is None and reg is not None and not fwd and (PQ_PLACE or FRAME_OUT_RELAY):
                    # S81-DIE (qs5f q abstract fills its 221.4 um frame): a frame relay with no spot inside its frame
                    # takes the nearest legal spot within reach (the strip / channel next to the frame)
                    for span, rows in ((300.0, 30), (1200.0, 120)):
                        pl = P.near(cx, cy, w_ + 2.16, h_ + 2.16, [(0.0, 0.0, W, H)], prev=cur, horiz=horiz,
                                    reach=R - 10.0, span=span, rows=rows, **NR)
                        if pl:
                            pl = (up(pl[0] + 1.08, GX), up(pl[1] + 1.08, GY))
                            rc['frame_out'] = rc.get('frame_out', 0) + 1
                            break
                if pl is None and PIN_RELAY and reg is None:   # a pin relay beside a slab: anywhere legal on the die
                    for span, rows in ((300.0, 30), (1200.0, 120)):
                        pl = P.near(cx, cy, w_ + 2.16, h_ + 2.16, [(0.0, 0.0, W, H)], prev=cur, horiz=horiz,
                                    reach=R - 10.0, span=span, rows=rows, **NR)
                        if pl:
                            pl = (up(pl[0] + 1.08, GX), up(pl[1] + 1.08, GY))
                            rc['die'] = rc.get('die', 0) + 1
                            break
                if pl is None and NR:          # both reaches, anywhere legal on the die (the frame / channel is full)
                    for span, rows in ((300.0, 30), (1200.0, 120)):
                        pl = P.near(cx, cy, w_ + 2.16, h_ + 2.16, [(0.0, 0.0, W, H)], prev=cur, horiz=horiz,
                                    reach=R - 10.0, span=span, rows=rows, **NR)
                        if pl:
                            pl = (up(pl[0] + 1.08, GX), up(pl[1] + 1.08, GY))
                            rc['nxt_die'] = rc.get('nxt_die', 0) + 1
                            break
                if pl is None and NR and RELAY_TT_REACH and RELAY_TT_REACH > R:
                    # s81-gen: the TT tier honours BOTH reaches, so it runs before the legacy prev-only search (qs5f
                    # frames: the legacy tier put g_xb_*_7 beside its driver, 677 um short of the bank)
                    nr_tt = (RELAY_TT_REACH - 10.0) if k == n - 1 else (n - k) * (RELAY_TT_REACH - 10.0)
                    pl = _tt_place(P, cx, cy, w_, h_, cur, RELAY_TT_REACH, b, nr_tt, horiz)
                    if pl:
                        rc['tt_reach'] = rc.get('tt_reach', 0) + 1
                        tt.append(f'g_{bid}_{e[0]}_{k}')
                if pl is None and NR:          # no spot honours the load-side reach: the legacy search, counted
                    rc['nxt_relaxed'] = rc.get('nxt_relaxed', 0) + 1   # (an int in rec broke the summary)
                    for PAD in (2.16, 1.08, 0.0):
                        for span, rows in ((120.0, 12), (300.0, 30), (600.0, 60), (1200.0, 120)):
                            pl = P.near(cx, cy, w_ + 2 * PAD, h_ + 2 * PAD, allowed, prev=cur, horiz=horiz,
                                        reach=R - 10.0, span=span, rows=rows)
                            if pl:
                                pl = (up(pl[0] + PAD, GX), up(pl[1] + PAD, GY))
                                break
                        if pl:
                            break
                    # s81-die-2 2026-10-08: the legacy chain also has the whole-die fallbacks (PQ frame_out, pin relay);
                    # without them a packed frame failed under --nxt-reach where legacy passed (es_12_y0, adopted PQ row)
                    if pl is None and ((reg is not None and not fwd and (PQ_PLACE or FRAME_OUT_RELAY)) or (PIN_RELAY and reg is None)):
                        for span, rows in ((300.0, 30), (1200.0, 120)):
                            pl = P.near(cx, cy, w_ + 2.16, h_ + 2.16, [(0.0, 0.0, W, H)], prev=cur, horiz=horiz,
                                        reach=R - 10.0, span=span, rows=rows)
                            if pl:
                                pl = (up(pl[0] + 1.08, GX), up(pl[1] + 1.08, GY))
                                rc['relaxed_die'] = rc.get('relaxed_die', 0) + 1
                                break
                if pl is None and NXT_REACH:
                    # The coarse row pitch can skip a narrow legal gap in a packed frame. Search a finer
                    # lattice before failing; keep both timing reaches and the original occupancy clearance.
                    for PAD in (2.16, 1.08, 0.0):
                        pl = P.near(cx, cy, w_ + 2 * PAD, h_ + 2 * PAD, [(0.0, 0.0, W, H)],
                                    prev=cur, horiz=horiz, reach=R - 10.0, span=1200.0,
                                    rows=560, cross_step=2.16, **NR)
                        if pl:
                            pl = (up(pl[0] + PAD, GX), up(pl[1] + PAD, GY))
                            rc['fine_lattice'] = rc.get('fine_lattice', 0) + 1
                            break
                if pl is None and RELAY_TT_REACH and RELAY_TT_REACH > R:
                    nr_tt = None
                    if NXT_REACH:
                        nr_tt = (RELAY_TT_REACH - 10.0) if k == n - 1 else (n - k) * (RELAY_TT_REACH - 10.0)
                    pl = _tt_place(P, cx, cy, w_, h_, cur, RELAY_TT_REACH, b if NXT_REACH else None, nr_tt, horiz)
                    if pl:
                        rc['tt_reach'] = rc.get('tt_reach', 0) + 1
                        tt.append(f'g_{bid}_{e[0]}_{k}')
                return pl, (cx, cy), dch, horiz, w_, h_, NR

            def stations_at(path, n, extra=0):
                Lp = _poly_len(path)
                # OWNER rule 1 (2026-10-07, --pin-relay): a relay abutting every hardened-block pin (<= PIN_SEG um last
                # segment) at each non-glue end, the span between them at the reach as before
                pos = [Lp * (k + 1) / (n + 1) for k in range(n)]
                if PIN_RELAY and reg is None:      # die-level interfaces (field frames: q banks already abut the pins)
                    h0, h1 = not is_glue(d0.master), not is_glue(l0.master)
                    if (h0 or h1) and Lp > PIN_SEG:
                        s0 = min(PIN_SEG - 10.0, Lp / 2) if h0 else 0.0
                        s1 = Lp - min(PIN_SEG - 10.0, Lp / 2) if h1 else Lp
                        mid = max(0, math.ceil((s1 - s0) / (R - 20.0) - 1e-9) - 1) + extra
                        pos = ([s0] if h0 else []) + [s0 + (s1 - s0) * (k + 1) / (mid + 1) for k in range(mid)] \
                            + ([s1] if h1 and s1 > s0 + 1.0 else [])
                return pos

            path = [a, (b[0], a[1]), b]
            extra = 0
            if (PATH_PICK and reg is None) or HOP_EXTRA:
                # cont-takeover 2026-10-09 (OT_S81_PATH_PICK=1) / s81-gen (--path-pick): a die-level hop whose stations
                # do not all find a box on the default horizontal-first L (the 20.2 mm layer1 hw_SW host chain along
                # y = 14724.7 through packed field frames: station 5 / 53) tries the other L, then corridor Z paths by
                # corridor share (then length); the station count follows the path.  Dry runs, no occupancy change.
                # A candidate is CLEAN when every station places within both reaches (no relaxed / TT tier: those
                # stations fall behind the path; layer1e VM -> eng_SE ended 1,164 um short).
                # --hop-extra N (s81-gen): a hop with no clean candidate also tries 1..N extra stations (+1 cycle each on
                # that hop; qs5f frames: g_xb_*_7 -> bank 670 um with the planned count).  First clean (path, extra)
                # wins; else the placeable one with the fewest relaxed stations (default L, no extra on ties).
                cands = _hop_paths(a, b, cor) if (PATH_PICK and reg is None) else [path]
                rects = list(cor.values())
                order = [cands[0]] + sorted(cands[1:], key=lambda p_: (-round(_corr_frac(p_, rects), 2), _poly_len(p_)))
                n0 = n
                best = None
                for x_ in range(HOP_EXTRA + 1):
                    for j_, cand in enumerate(order):
                        n_c = (n0 if j_ == 0 else max(n0, math.ceil(_poly_len(cand) / (R - 20.0) - 1e-9) - 1)) + x_
                        pos_c = stations_at(cand, n_c, x_)
                        cur_, ok, rc_ = a, True, {}
                        # Later candidate stations must see the boxes already chosen
                        # for this candidate, exactly as they do during construction.
                        with P.occ.temporary() as reserve:
                            for k in range(len(pos_c)):
                                pl_, _, _, _, w_, h_, _ = find(k, len(pos_c), cand, pos_c, cur_, rc_, [])
                                if pl_ is None:
                                    ok = False
                                    break
                                reserve((pl_[0], pl_[1], pl_[0] + w_, pl_[1] + h_))
                                cur_ = (pl_[0] + w_ / 2, pl_[1] + h_ / 2)
                        if not ok:
                            continue
                        bad = sum(v for k_, v in rc_.items() if k_ in ('nxt_relaxed', 'relaxed_die', 'tt_reach'))
                        if best is None or bad < best[0]:
                            best = (bad, j_, cand, n_c, x_)
                        if bad == 0:
                            break
                    if best is not None and best[0] == 0:
                        break
                if best is not None:
                    _, j_, cand, n_c, extra = best
                    path, n = cand, n_c
                    if j_:
                        kind_ = 'vfirst' if len(cand) == 3 else 'z'
                        rec['path_pick'][kind_] = rec['path_pick'].get(kind_, 0) + 1
                    if extra:
                        rec['hop_extra'][f'+{extra}'] = rec['hop_extra'].get(f'+{extra}', 0) + 1
            Lp = _poly_len(path)
            pos = stations_at(path, n, extra)
            n = len(pos)
            prev, cur = eps[0], a
            fprev = fdrv if fwd else None
            tt_ = m.setdefault('tt_reach_relays', [])
            for k in range(n):
                pl, (cx, cy), dch, horiz, w_, h_, NR = find(k, n, path, pos, cur, rec['pad_fallback'], tt_)
                if HOPDBG and bid.startswith(HOPDBG):     # OT_S81_HOPDBG=<bus prefix>: per-station trace (stderr)
                    print('HOPDBG', bid, e, k, n, [tuple(round(v, 1) for v in q) for q in path], round(pos[k], 1),
                          (round(cx, 1), round(cy, 1)), pl, dict(rec['pad_fallback']), file=sys.stderr)
                assert pl, (bid, e, k, n, round(L, 1), a, b, (round(cx, 1), round(cy, 1)), cur, reg, R, w_, h_, dict(NR))
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
    RSV_ALLOW = None
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
                        reach_um=dict(common_clock=HOP_R_CC, forwarded=HOP_R_FWD, tt_exception=RELAY_TT_REACH),
                        tt_reach_relays=sorted(m.get('tt_reach_relays', [])))


def _pin_stages(m, src):
    """registered relay stages from driver pin src = (inst, port) to every non-relay load pin: {(inst, port): n}"""
    kind = {it.name: it.kind for it in m['insts']}
    outs = {}
    for bid, cls, bits, eps in m['buses']:
        outs.setdefault(tuple(eps[0]), []).append(eps[1:])
    thru = {'i': 'o', 'di': 'dq', 'di0': 'do0'}
    res, stack = {}, [(tuple(src), 0)]
    while stack:
        ep, n = stack.pop()
        for loads in outs.get(ep, []):
            for l_ in loads:
                l_ = tuple(l_)
                if (kind.get(l_[0]) in ('rly', 'hstn') or (kind.get(l_[0]) == 'stn' and l_[0].startswith('g_'))) \
                        and l_[1] in thru:
                    stack.append(((l_[0], thru[l_[1]]), n + 1))
                else:
                    res[l_] = n
    return res


def _ctrl_vm_latency_check(m):
    """ds-1010 lat-audit (2026-10-10): the native stage controller (ot_s81_ctrl / ot_s81_hop_tx) reads the VM in
    FIXED-latency mode by default (USE_VM_RVALID 0: data taken from its own r1 -> rd pipe) and the binding manifest
    claims vm_read_cycles 1.  --hop-fix / --pin-relay put stations on the vre / vra request and the vrq / vrv response
    when the endpoints are apart, so the claim is checked here on the built die: any stage on the read path fails the
    build unless the manifest declares vm_return_valid (the master consumes vrv, which must then carry exactly the
    stages of vrq)."""
    it = m['hub']['stage_ctrl'].name
    P = CTRL_BINDINGS['ports']
    req = max([max(_pin_stages(m, (it, p_)).values(), default=0) for p_ in ('vre', 'vra')])
    rsp = {}
    for p_ in ('vrq', 'vrv'):
        ep = tuple(P[p_]['endpoint'])
        rsp[p_] = _pin_stages(m, ep).get((it, p_), 0)
    m['ctrl_vm_read'] = dict(request_stages=req, response_stages=rsp,
                             vm_return_valid=bool(CTRL_BINDINGS.get('vm_return_valid')))
    if rsp['vrq'] != rsp['vrv']:
        raise SystemExit('--ctrl-slab: VM read data and valid cross different stage counts %s' % rsp)
    if not CTRL_BINDINGS.get('vm_return_valid') and (req or rsp['vrq']):
        raise SystemExit('--ctrl-slab: fixed-latency VM read (USE_VM_RVALID 0, vm_read_cycles 1) but the die puts %d '
                         'request + %d response stages on it: bind the master with --vm-return-valid '
                         '(tools/s81_ctrl/specialize_master.py) and set vm_return_valid in the manifest' % (req, rsp['vrq']))


def _relay_progress_fix(m, P, passes=3):
    """--relay-progress (hbmdie-1011): a point-to-point relay / station that stands farther from its next chain point
    than its own driver (the FP-LINT far-side test, +20 um) is ripped up and re-placed on a free site BETWEEN its driver
    and next point: inside the region rects around it, no farther from the next point than the driver, and neither of
    its two hops longer than the longer of its old hops (same register count, no hop gets longer: latency and reach
    unchanged).  The next point is the load's real LEF pin centroid for a real macro (link tx halves, q ports), else its
    centre.  Records m['relay_progress_fix'] = {moved, left: [...]}."""
    import fp_margin_lint as FPL
    by = {it.name: it for it in m['insts']}
    cen = lambda it: (it.x + it.w / 2, it.y + it.h / 2)
    lpt = _lint_pin_pt(m)
    rects = [r_['rect'] for r_ in m['regions']] + [cr['rect'] for cr in m.get('cregions', [])] + \
        [tuple(r_) for r_ in _corridors(m).values()]
    moved, left = 0, []
    for _ in range(passes):
        data = [b for b in m['buses'] if b[1] not in HOP_SKIP]
        res = FPL.die_margin(m['insts'], data, MARGIN_RELAY_KINDS, reach_um=SS_REACH_UM, edges=True, limit=10 ** 7,
                             pin_pt=lpt)
        todo = {}
        for e in res['far_side_examples']:
            todo.setdefault(e['relay'], e['chain'].split('->'))
        if not todo:
            break
        left = []
        for rn, (dn, nn) in todo.items():
            it, d_ = by[rn], by[dn]
            ports = {e_[1] for b in data if b[3][0][0] == rn for e_ in b[3][1:] if e_[0] == nn}
            qs = [q_ for q_ in (lpt(nn, p_) for p_ in sorted(ports)) if q_ is not None]
            q = (sum(a[0] for a in qs) / len(qs), sum(a[1] for a in qs) / len(qs)) if qs else cen(by[nn])
            a, o = cen(d_), cen(it)
            if _mh(o, q) <= _mh(a, q) + 20.0:
                continue
            R = min(SS_REACH_UM - 30.0, max(_mh(a, o), _mh(o, q)))
            pts = (a, o, q)
            allowed = [r_ for r_ in rects if any(r_[0] <= p_[0] <= r_[2] and r_[1] <= p_[1] <= r_[3] for p_ in pts)]
            box = it.box()
            for k_ in P.occ._bins(*box):
                if box in P.occ.g[k_]:
                    P.occ.g[k_].remove(box)
            pl = None
            # no farther from the next point than the driver + 15 um (inside the lint's 20 um far-side slack)
            for sp_, rw_ in ((72.0, 10), (200.0, 16), (400.0, 40), (800.0, 80)):
                pl = P.near((a[0] + q[0]) / 2, (a[1] + q[1]) / 2, it.w, it.h, allowed, prev=a, reach=R,
                            span=sp_, rows=rw_, nxt=q, nreach=min(R, _mh(a, q) + 15.0))
                if pl is not None:
                    break
            if pl is None:
                P.occ.add(box)
                left.append(dict(relay=rn, drv=dn, nxt=nn, back_um=round(_mh(o, q) - _mh(a, q), 1)))
                continue
            it.x, it.y = pl
            P.occ.add(it.box())
            moved += 1
    m['relay_progress_fix'] = dict(moved=moved, left=left[:40], n_left=len(left))


def _go_retap(m):
    """--lane-equal (ds-1010 lat-audit 2026-10-10): a pair whose sequencer -> element go path (go_<p>, through
    ot_s81_cfg7_seq's combinational go_e) carries k column / hop relays would see go k cycles after its x0 (x0 and the
    cc lane leave the slot station together).  The sequencer's lc then taps the cc chain k registers EARLIER (the net
    into the slot station's cci, or into the relay before it), so go reaches the element with x0; cfg / go_tag leave
    the same sequencer and keep their order to go.  Records m['go_retap'] = {pair: k}."""
    kind = {it.name: it.kind for it in m['insts']}
    B = m['buses']
    drv_of = {}
    for i, (bid, cls, bits, eps) in enumerate(B):
        for e in eps[1:]:
            drv_of[tuple(e)] = i
    out_of = {}
    for i, (bid, cls, bits, eps) in enumerate(B):
        out_of.setdefault(tuple(eps[0]), []).append(i)
    rec, pad_used = {}, {}
    for it in m['insts']:
        if it.kind != 'seq':
            continue
        k, ep = 0, (it.name, 'go_e')
        while True:
            nxt = [e for i in out_of.get(ep, []) for e in B[i][3][1:]]
            if len(nxt) != 1 or kind.get(nxt[0][0]) != 'rly':
                break
            k += 1
            ep = (nxt[0][0], 'o')
        if not k:
            continue
        i = drv_of[(it.name, 'lc')]
        src = B[i][3][0]
        src0 = tuple(src)
        for _ in range(k):          # one register back along the cc chain per go relay
            if kind.get(src[0]) == 'sstn' and src[1] == 'cc' and \
                    pad_used.setdefault(src[0], {}).get(it.name, 0) < m.get('sstn_ccpad', {}).get(src[0], 0):
                # --sstn-ccpad: the station's own pad registers are the last ones before lc: consume one of them
                pad_used[src[0]][it.name] = pad_used[src[0]].get(it.name, 0) + 1
                continue
            if kind.get(src[0]) == 'sstn' and src[1] == 'cc':
                src = B[drv_of[(src[0], 'cci')]][3][0]
            elif kind.get(src[0]) == 'rly':
                src = B[drv_of[(src[0], 'i')]][3][0]
            else:
                raise AssertionError(('--lane-equal: no register to retap before', it.name, src))
        rec[it.name[1:]] = k
        if tuple(src) == src0:      # every retap register came out of the station pad: lc stays on the station cc
            continue
        bid, cls, bits, eps = B[i]
        B[i] = (bid, cls, bits, [e for e in eps if tuple(e) != (it.name, 'lc')])
        j = next(j for j in out_of[tuple(src)] if B[j][1] in ('x_ctl',))
        bj = B[j]
        B[j] = (bj[0], bj[1], bj[2], bj[3] + [(it.name, 'lc')])
        rec[it.name[1:]] = k
    B[:] = [b for b in B if len(b[3]) > 1]      # a top-slot cc net whose every sequencer moved down
    # --sstn-ccpad: a padded station's remaining lc loads must have consumed the same number of pad registers; the
    # station keeps the rest (one pad chain per station, no mid-pad taps)
    for st_, used in pad_used.items():
        P_ = m.get('sstn_ccpad', {}).get(st_, 0)
        if not P_:
            continue
        lc_loads = [e[0] for b in B if tuple(b[3][0]) == (st_, 'cc') for e in b[3][1:] if e[1] == 'lc']
        cs = {used.get(q_, 0) for q_ in lc_loads}
        if len(cs) <= 1:            # every load agrees: the station keeps P - c pad registers
            c_ = cs.pop() if cs else 0
            if P_ - c_:
                m['sstn_ccpad'][st_] = P_ - c_
            else:
                del m['sstn_ccpad'][st_]
            continue
        # loads disagree: a load that consumed c pad registers takes the pad tap cct<P - c> (age 1 + P - c)
        assert P_ <= 4, ('--sstn-ccpad: more than 4 pad taps', st_, P_)
        for q_ in lc_loads:
            c_ = used.get(q_, 0)
            if not c_:
                continue
            for bi, b in enumerate(B):
                if tuple(b[3][0]) == (st_, 'cc') and (q_, 'lc') in [tuple(e) for e in b[3][1:]]:
                    B[bi] = (b[0], b[1], b[2], [e for e in b[3] if tuple(e) != (q_, 'lc')])
                    tb = f'cct_{st_}_{P_ - c_}'
                    ti = next((bj for bj, b2 in enumerate(B) if b2[0] == tb), None)
                    if ti is None:
                        B.append((tb, b[1], b[2], [(st_, f'cct{P_ - c_}'), (q_, 'lc')]))
                    else:
                        B[ti] = (B[ti][0], B[ti][1], B[ti][2], B[ti][3] + [(q_, 'lc')])
                    break
    m['go_retap'] = dict(pairs=len(rec), by_k={str(v): sum(1 for x in rec.values() if x == v) for v in set(rec.values())})


def _col_relays(m, P):
    """common-clock column nets whose driver -> load centre distance exceeds BANK_RULE_UM get relay registers
    (one cycle each) at equal spacing on an L path, inside the frame.  Records per frame the relays on the worst x
    path and on the worst leaf -> root path."""
    by = {it.name: it for it in m['insts']}
    cen = lambda it: (it.x + it.w / 2, it.y + it.h / 2)

    lpt_ = _lint_pin_pt(m) if PIN_NEED else None

    def ep_pt(e, load=False):
        it_ = by[e[0]]
        if PIN_NEED and it_.kind == 'q':
            pt_ = _q_pin_pt(it_, e[1])
            if pt_ is not None:
                return pt_
        if load and lpt_ is not None:
            # s81-die-iter 2026-10-12: a load's real LEF pin (the margin lint's next chain point): the column relays of
            # go / cfg nets (seq -> bf / cfg element) were placed toward the load CENTRE and judged against its pin
            # (512 y_go + 384 y_cfg far-side relays, up to 169.3 um back)
            pt_ = lpt_(e[0], e[1])
            if pt_ is not None:
                return pt_
        return cen(it_)
    RCLS = ('ret_leaf', 'ret_tree', 'x_lane', 'x_ctl', 'stat', 'cfg', 'go', 'col_ret')
    B = m['buses']
    out, added = [], defaultdict(int)       # (bus id) -> relays
    ck_add = defaultdict(list)
    tt_col = []                             # --relay-tt-reach: pass-1 relays placed in the TT-reach tier
    global RSV_ALLOW

    def _need(bid, cls, eps):
        """(frame, L, n, far) of a column net, or None when it takes no relays"""
        if cls not in RCLS or bid.endswith('_eb'):
            return None
        d0 = by.get(eps[0][0])
        if d0 is None or d0.region is None or not d0.region.startswith('frame_'):
            return None
        a0 = ep_pt(eps[0])
        fe = max((e for e in eps[1:] if e[0] in by), key=lambda e: _mh(a0, ep_pt(e, True)), default=None)
        if fe is None:
            return None
        L = _mh(a0, ep_pt(fe, True))
        return math.ceil(L / BANK_RULE_UM - 1e-9) - 1
    # --lane-equal (ds-1010 lat-audit 2026-10-10): the x0 / x1 / cc lanes of one slot segment carry ONE transaction
    # (the element takes x0 and x1 in the same cycle; go rides cc through the pair sequencer), so each of them takes
    # the largest relay count of the three; a lane padded beyond its own reach need gets extra relays on its own path.
    lane_n = {}
    if LANE_EQUAL:
        for bid, cls, bits, eps in B:
            mm = re.fullmatch(r'(xa|xb|cc)_(\d+)_(\d+)', bid)
            if mm:
                n_ = _need(bid, cls, eps)
                k_ = (mm.group(2), mm.group(3))
                lane_n[k_] = max(lane_n.get(k_, 0), n_ or 0)
    for bid, cls, bits, eps in list(B):
        RSV_ALLOW = _rsv_tag(bid)              # reserved relay sites: return tree ('rt') / slot x lanes ('x')
        if cls not in RCLS or bid.endswith('_eb'):
            out.append((bid, cls, bits, eps))
            continue
        d0 = by.get(eps[0][0])
        if d0 is None or d0.region is None or not d0.region.startswith('frame_'):
            out.append((bid, cls, bits, eps))
            continue
        r = int(d0.region.split('_')[1])
        f = m['frames'][r]
        fr = (f['x'], f['y'] - 60.0, f['x'] + COL_W8, f['y'] + column_height())
        if RELAY_PROGRESS:
            # --relay-progress: a net whose driver / far load sits in the channel beside the frame (PQ root row ->
            # column FIFO) may take relay sites between its endpoints there, not only inside the frame box
            ends_ = [by[eps[0][0]]] + [by[e[0]] for e in eps[1:] if e[0] in by]
            fr = (fr[0], min([fr[1]] + [i_.y for i_ in ends_]), fr[2], max([fr[3]] + [i_.y + i_.h for i_ in ends_]))
        if RT_STRIP and RSV_ALLOW == 'rt':
            # --rt-strip: the channel strip above the frame top (the return leaves of the top slot run along that edge)
            fr = (fr[0], fr[1], fr[2], max(fr[3], min(f['y'] + column_height() + RT_STRIP, DIE[1] - EDGE)))
        a0 = ep_pt(eps[0])
        fe = max((e for e in eps[1:] if e[0] in by), key=lambda e: _mh(a0, ep_pt(e, True)), default=None)
        far = by[fe[0]] if fe is not None else None
        if far is None:
            out.append((bid, cls, bits, eps))
            continue
        L = _mh(a0, ep_pt(fe, True))
        n = math.ceil(L / BANK_RULE_UM - 1e-9) - 1
        mm = re.fullmatch(r'(xa|xb|cc)_(\d+)_(\d+)', bid) if LANE_EQUAL else None
        if mm:
            n_pad = max(n, lane_n.get((mm.group(2), mm.group(3)), 0))
            if SSTN_CCPAD and mm.group(1) == 'cc' and d0.kind == 'sstn' and n_pad > max(n, 0):
                # the pad cycles (beyond the cc net's own reach need) are registers inside the driving station
                m.setdefault('sstn_ccpad', {})[d0.name] = m.get('sstn_ccpad', {}).get(d0.name, 0) + n_pad - max(n, 0)
                n_pad = max(n, 0)
            n = n_pad
        if n <= 0:
            out.append((bid, cls, bits, eps))
            continue
        a, b = a0, ep_pt(fe, True)
        w_, h_ = relay_dims(bits, True)
        own_ = None
        if X_SITE_PAIR:
            mx_ = re.fullmatch(r'(xa|xb)_(\d+)_(\d+)', bid)
            if mx_ and int(mx_.group(3)) >= 1 and eps[0][0] == f't{r}_{int(mx_.group(3)) - 1}':
                st_ = XSITES.get((r, int(mx_.group(3)) - 1))
                if st_ is not None:
                    own_ = st_[0 if mx_.group(1) == 'xa' else 1]

        def _pick(path, cur, k, Lp, log=True):
            """one column relay on `path`: (placement, tier) -- tier 'first' = within the column reach of the previous
            point (and the load-side reach under --nxt-reach / --relay-progress); later tiers are the TT / legacy ones"""
            if k == 0 and own_ is not None:
                # --x-site-pair: the lane's first relay takes its owned site beside the driving station
                bx_ = (own_[0], own_[1], own_[0] + w_, own_[1] + h_)
                if P.occ.free(bx_, 0.432) and _mh(cur, (own_[0] + w_ / 2, own_[1] + h_ / 2)) <= BANK_RULE_UM + 40.0:
                    m.setdefault('x_site_pair', []).append(bid)
                    return own_, 'first'
                m.setdefault('x_site_pair_miss', []).append(bid)
            (cx, cy), _ = _poly_at(path, Lp * (k + 1) / (n + 1))
            NR = dict(nxt=b, nreach=(n - k) * (BANK_RULE_UM + 40.0)) if NXT_REACH else {}
            pg = _mh(cur, b) + 15.0 if RELAY_PROGRESS else None     # --relay-progress: never behind the driver
            if pg is not None:
                NR = dict(nxt=b, nreach=min(NR.get('nreach', pg), pg))
            pl = P.near(cx, cy, w_, h_, [fr], prev=cur, horiz=True, reach=BANK_RULE_UM + 40.0, span=200.0, rows=20, **NR)
            if pl is not None:
                return pl, 'first'
            if RELAY_TT_REACH and RELAY_TT_REACH > BANK_RULE_UM + 40.0:
                # s81-gen: the unbounded fallback below put y_rt_0_8a_1 773.7 um from its driver (r4c frame 0); a relay
                # first takes a box within the TT reach (inside the frame, then the strip / channel beside it)
                nr_tt = dict(nxt=b, nreach=(n - k) * (RELAY_TT_REACH - 10.0)) if NXT_REACH else {}
                if pg is not None:
                    nr_tt = dict(nxt=b, nreach=min(nr_tt.get('nreach', pg), pg))
                pl = P.near(cx, cy, w_, h_, [fr], prev=cur, horiz=True, reach=RELAY_TT_REACH - 10.0, span=400.0,
                            rows=40, **nr_tt)
                if pl is None and (PQ_PLACE or FRAME_OUT_RELAY):
                    pl = _tt_place(P, cx, cy, w_, h_, cur, RELAY_TT_REACH, nr_tt.get('nxt'), nr_tt.get('nreach'), True)
                if pl:
                    return pl, 'tt'
            pl = P.near(cx, cy, w_, h_, [fr], prev=None, horiz=True, span=400.0, rows=40,
                        **(dict(nxt=b, nreach=pg) if pg is not None else {}))
            if pl is None and pg is not None and log and os.environ.get('OT_S81_RP_LOG'):
                # diagnostic only: record the frame / path of a relay with no forward site, then legacy fallback
                with open(os.environ['OT_S81_RP_LOG'], 'a') as fh_:
                    bx_ = (min(cur[0], b[0]) - 30, min(cur[1], b[1]) - 30, max(cur[0], b[0]) + 30, max(cur[1], b[1]) + 30)
                    occ_ = [(i_.name, i_.kind, round(i_.x, 2), round(i_.y, 2), round(i_.w, 2), round(i_.h, 2))
                            for i_ in P.m["insts"] if i_.x < bx_[2] and bx_[0] < i_.x + i_.w and i_.y < bx_[3] and bx_[1] < i_.y + i_.h]
                    fh_.write(json.dumps(dict(bus=bid, k=k, n=n, cls=cls, drv=cur, far=b, mid=(cx, cy), frame=fr,
                                              region=d0.region, wh=(w_, h_), occ=occ_)) + '\n')
            if pl is None:
                pl = P.near(cx, cy, w_, h_, [fr], prev=None, horiz=True, span=400.0, rows=40)
            return pl, 'legacy'
        path = [a, (b[0], a[1]), b] if cls != 'ret_tree' else [a, (a[0], b[1]), b]
        operand_candidate = OPERAND_PATH_PICK and re.fullmatch(r'(xa|xb|cc)_\d+_\d+', bid) is not None
        if (cls == 'ret_tree' and RELAY_PROGRESS) or operand_candidate:
            # s81-die-iter 2026-10-12: the return tree's vertical-first L crosses the packed q slots where relay rows lie
            # ~546 um apart (rt_<c>_24b: y0 -> y1 546 um, TT tier, 518.4 um hop on all 128 columns).  Dry-run both L
            # paths and keep the one whose relays all place in the first (column-reach) tier, default L on ties.
            best_ = None
            alternate = [a, (a[0], b[1]), b] if operand_candidate else [a, (b[0], a[1]), b]
            for j_, cand in enumerate((path, alternate)):
                Lc, cur_, bad = _poly_len(cand), a, 0
                with P.occ.temporary() as reserve:
                    for k in range(n):
                        pl_, tier_ = _pick(cand, cur_, k, Lc, log=False)
                        if pl_ is None:
                            bad += 100
                            break
                        reserve((pl_[0], pl_[1], pl_[0] + w_, pl_[1] + h_))
                        bad += tier_ != 'first'
                        cur_ = (pl_[0] + w_ / 2, pl_[1] + h_ / 2)
                if best_ is None or bad < best_[0]:
                    best_ = (bad, j_, cand)
                if bad == 0:
                    break
            if best_[1]:
                path = best_[2]
                m.setdefault('col_relay_path_pick', []).append(bid)
            if operand_candidate:
                m.setdefault('operand_path_candidates', []).append(dict(bus=bid, frame=r, selected_direction='vertical_first' if best_[1] else 'horizontal_first', nonfirst_tiers=best_[0], unchanged_register_count=n, per_bit_gate_required=True))
        prev, cur = eps[0], a
        chain = [a]
        Lp = _poly_len(path)
        for k in range(n):
            pl, tier = _pick(path, cur, k, Lp)
            if HOPDBG and bid.startswith(HOPDBG):    # OT_S81_HOPDBG=<bus prefix>: column relay trace (stderr)
                print('COLDBG', bid, cls, d0.name, d0.kind, k, n, round(Lp, 1), [tuple(round(v, 1) for v in q) for q in path],
                      tuple(round(v, 1) for v in cur), pl and tuple(round(v, 1) for v in pl), (w_, h_), tier, fr,
                      file=sys.stderr)
            if tier == 'tt' and pl:
                tt_col.append(f'y_{bid}_{k}')
            assert pl, ('--relay-progress: no forward relay site in the frame', bid, k) if RELAY_PROGRESS else (bid, k)
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
            if RLY_FACE_REACH and k == len(chain) - 2:
                # --rly-face-reach UM (s81-die v16): the LAST column relay drives every load of the net, not only the
                # farthest one its out face was turned to.  v15 run 4: y_xa_<r>_<s>_0 (dsfd_rly_283_WE) sat in the
                # --xb-rgap site E of the slot station with its out pins on the E face (toward the E element bank),
                # 507.1 um pin to pin from the next station's xai (8,309 bits > 500).  When the default out face
                # centre is farther than UM from a load pin, the relay takes the out face with the smallest worst-load
                # distance.  It stays a STRAIGHT master: first the same axis reversed (dsfd_rly_283_WE -> _EW: same outline
                # class and site, a mirrored kit), else the best face with the in face opposite when the driver is
                # within UM of it.
                fpt_ = dict(E=(it.x + it.w, it.y + it.h / 2), W=(it.x, it.y + it.h / 2),
                            N=(it.x + it.w / 2, it.y + it.h), S=(it.x + it.w / 2, it.y))
                lds_ = [ep_pt(e, True) for e in eps[1:] if e[0] in by]
                wl_ = {f_: max(_mh(fpt_[f_], q_) for q_ in lds_) for f_ in 'NSEW'} if lds_ else None
                if wl_ and wl_[fo] > RLY_FACE_REACH:
                    opp_ = dict(N='S', S='N', E='W', W='E')
                    best_ = min(wl_.values())
                    if fo == opp_[fi] and wl_[fi] < wl_[fo] and wl_[fi] <= best_ + 25.0:
                        # the same straight axis, reversed (in <-> out): the relay keeps its outline class and its site
                        # (W >= 266: the 21.6 x 30.24 E/W class is the one that fits the 25.5-um --xb-rgap site)
                        fi2_, fb_ = fo, fi
                    else:
                        fb_ = min(wl_, key=lambda f_: (wl_[f_], f_))
                        fi2_ = opp_[fb_] if _mh(pa, fpt_[opp_[fb_]]) <= RLY_FACE_REACH else (fi if fi != fb_ else opp_[fb_])
                    if fb_ != fo:
                        m.setdefault('rly_face_reach', []).append((it.name, fi + fo, fi2_ + fb_, round(wl_[fo], 1),
                                                                   round(wl_[fb_], 1)))
                        fi, fo = fi2_, fb_
            if own_ is not None and k == 1 and (round(it.x, 3), round(it.y, 3)) == (round(own_[0], 3), round(own_[1], 3)):
                # --x-site-pair: the owned-site relay is the STRAIGHT E->W master (dsfd_rly_<b>_EW): out on the W face
                # (worst load = the W bank, <= ~340 um pin to pin on native207 geometry, all 2,304 lanes), in on the E face
                # from the station beside it; no corner master (WN) that would need its own real view
                fi, fo = 'E', 'W'
            it.master = f'dsfd_rly_{bits}_{fi}{fo}'
            RLY_FACES[it.master] = (fi, fo)
        out.append((bid, cls, bits, [prev] + list(eps[1:])))
        added[bid] = n
    RSV_ALLOW = None
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
    m['col_relays'] = dict(nets=len(added), relays=sum(added.values()), tt_reach_relays=sorted(tt_col),
                           by_class={c: sum(v for k_, v in added.items() if k_.startswith(c)) for c in
                                     ('rt_', 'xa_', 'xb_', 'cc_', 'qt_', 'es_', 'ss_', 'so_', 'nf_', 'cfg_', 'go_', 'rr_')})


def _split_far_pins(Bk, pb, bits, gap_um=200.0):
    """r5 2026-10-14 (gather hop gate, el1013-s81-gather.log 11:21 answer (a)): the die-assigned pins of Bk.pb as one
    run plus a trailing group whose pins sit > gap_um along the face from the run (gather rW*/rE* [N-2:N-1] = trunk
    status {fault, live} to the bottom control strip).  Returns (k, face, coord) of the trailing group or None."""
    rec = _assigned_record(Bk.master)
    spec = (rec or {}).get('ports', {}).get(pb)
    if not spec or not spec.get('per_bit') or spec['bits'] != bits:
        return None
    pbits = spec['per_bit']
    k = 0
    while k < bits - 1 and abs(pbits[bits - 1 - k][2] - pbits[bits - 2 - k][2]) <= gap_um and pbits[bits - 1 - k][0] == pbits[bits - 2 - k][0]:
        k += 1
    k += 1                                   # trailing group size (pins contiguous with the last pin)
    if k >= bits or abs(pbits[bits - k][2] - pbits[bits - k - 1][2]) <= gap_um:
        return None
    face = pbits[bits - 1][0]
    coord = sum(pb_[2] for pb_ in pbits[bits - k:]) / k
    return k, face, coord


def _local_chain(m, CH8, allowed, A, pa, Bk, pb, bits, name, dom, target=None):
    """r9: a local block-to-block bus (end block -> slab) staged by common-clock stations when it exceeds one hop.
    r5: when Bk's assigned pins of pb split into a run and a far trailing group, the trailing bits are a separate die
    path with their own stations to their own pins (target = (face, coord) along the face)."""
    if target is None and SPLIT_FAR_PINS:
        sp_ = _split_far_pins(Bk, pb, bits)
        if sp_:
            k, face, coord = sp_
            _local_chain(m, CH8, allowed, A, f'{pa}[0:{bits - k - 1}]', Bk, f'{pb}[0:{bits - k - 1}]', bits - k, name, dom)
            _local_chain(m, CH8, allowed, A, f'{pa}[{bits - k}:{bits - 1}]', Bk, f'{pb}[{bits - k}:{bits - 1}]', k,
                         name + '_st', dom, target=(face, coord))
            return
    a = (A.x + A.w / 2, A.y + A.h / 2)
    fx = Bk.x + Bk.w if a[0] > Bk.x + Bk.w else (Bk.x if a[0] < Bk.x else a[0])
    b = (fx, min(max(a[1], Bk.y + 6.0), Bk.y + Bk.h - 6.0))
    if target is not None:
        face, coord = target
        b = ((Bk.x if face == 'W' else Bk.x + Bk.w), Bk.y + coord) if face in 'WE' else \
            (Bk.x + coord, (Bk.y if face == 'S' else Bk.y + Bk.h))
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


def _lane_pin_alloc(m, A, Bk, pa, pb, bits, y_, lo, hi, xa=None, xb=None):
    """--lane-pins (s81-die v15): the die y of a straight hub lane, moved to the nearest row where the bus's pin span
    (bits x LANE_PINS tracks) overlaps no other lane's span, and recorded per (slab, port) for _faces_r8, so the pins of
    both slabs stand ON the lane (v14: wq_d pins centred on the hc_s face 3.3 mm N of its lane -> 32 bridge stations).
    The 8 t_hc_y slices are one 8,192-b port at each end: one span, lane k on the centre of slice k."""
    S, LP = m.setdefault('_lane_spans', []), m.setdefault('_lane_pin', {})
    pw = 0.048 * LANE_PINS
    ba, bb = pslice(pa)[0], pslice(pb)[0]
    grp = pa.startswith('t_hc_y[')
    off = (int(pslice(pa)[1]) // 1024 - 3.5) * 1024 * pw if grp else 0.0
    if grp and (A.name, ba) in LP:
        return LP[(A.name, ba)] + off
    tot = (8 if grp else 1) * bits * pw
    half = max(tot, 17.3) / 2 + 6.0
    y0 = (lo + hi) / 2 if grp else y_
    a0, a1 = lo + tot / 2, hi - tot / 2
    if a1 < a0:
        raise ValueError(f'--lane-pins: {A.name}.{pa} span {tot:.0f} um > the shared rows {hi - lo:.0f} um')
    # rows of the lane covered by a placed macro (link macros hl_* at the VCH W edge, 128 x 132) are not lane rows; 150 um
    # each side stay free for the slab ports that face the macro (g15a run 1: rE2 pushed 840.7 um off hl_E2 by the y span)
    xl_, xh_ = min(xa, xb), max(xa, xb)
    cands = sorted((a0 + 4.8 * i for i in range(int((a1 - a0) // 4.8) + 1)), key=lambda c: abs(c - y0))
    for mg_ in ((150.0, 60.0, 12.0) if grp else (12.0,)):   # the wide margin only for the 786-um t_hc_y span (run 3: at 150 the narrow lanes fragmented the VM rows, wq_d had none)
        Sx = S + [(i_.y - mg_, i_.y + i_.h + mg_) for i_ in m['insts'] if i_ is not A and i_ is not Bk and min(i_.w, i_.h) >= 60.0
                  and i_.x < xh_ - 1.0 and i_.x + i_.w > xl_ + 1.0 and i_.y < hi and i_.y + i_.h > lo]
        c = next((c for c in cands if all(c + half <= s0 or c - half >= s1 for s0, s1 in Sx)), None)
        if c is not None:
            break
    if c is None:
        raise ValueError(f'--lane-pins: no free lane rows for {A.name}.{pa} ({tot:.0f} um in {lo:.0f}..{hi:.0f})')
    S.append((c - half, c + half))
    LP[(A.name, ba)] = LP[(Bk.name, bb)] = c
    m.setdefault('lane_pins', {})[f'{A.name}.{ba}->{Bk.name}.{bb}'] = dict(y_um=round(c, 3), span_um=round(tot, 3), bits=(8 if grp else 1) * bits, pitch_tracks=LANE_PINS)
    return c + off


PQ_CNT_LIVE = (452, 4)           # PQ core mdr_o[455:452] = the four live bits (4 x CFW, CFW = 5 x 19 + 18)
PQ_CNT_WORD = 53                 # gather t_capture root word r = {e, pos 3, row 16, fp32 32, v} at bits 53r .. 53r + 52
PQ_CNT_FLT = 6944                # gather sticky fault bit of t_capture


def _pq_cnt_buses(m, CH8, cor, bits):
    """--pq-cnt (s81-die r6b 2026-10-14, topology G): the gather -> capture root-word bus split at the count-leaf taps (a
    tap = a second load on that slice: v = 53r, tag = 53r + 47 .. 48, e = 53r + 52 of each counted root; the gather fault
    6944 loads all 12 leaves); the leaves' live[3:0] (PQ mdr_o[455:452]) and their ga 16 / q2f 1 (PQ f_cnt: ga_i 16 i
    .. 16 i + 15, q2f_i 192 + i) ride staged hub lanes to / from the PQ core.  Leaf i (slot file order) = RWB i."""
    hb, cnt = m['hub'], m['pq_cnt']
    G, C = hb['gather'].name, hb['capture'].name
    taps = {}                     # t_capture bit -> [(leaf, port[k:k])]
    for it, sl_ in cnt:
        for k, tp in enumerate(sl_['n_face_taps']):
            b0 = tp['t_capture_bits'][0]
            assert b0 % PQ_CNT_WORD == 0 and tp['t_capture_bits'][1] == b0 + PQ_CNT_WORD - 1, ('--pq-cnt tap', it.name, tp)
            taps.setdefault(b0, []).append((it.name, f'r_v[{k}:{k}]'))
            taps.setdefault(b0 + 47, []).append((it.name, f'r_tag[{2 * k}:{2 * k}]'))
            taps.setdefault(b0 + 48, []).append((it.name, f'r_tag[{2 * k + 1}:{2 * k + 1}]'))
            taps.setdefault(b0 + PQ_CNT_WORD - 1, []).append((it.name, f'r_e[{k}:{k}]'))
        taps.setdefault(PQ_CNT_FLT, []).append((it.name, 'g_flt'))
    assert sum(len(sl_['n_face_taps']) for _, sl_ in cnt) == len({b for b in taps if b != PQ_CNT_FLT}) // 4, \
        '--pq-cnt: a root is counted twice or not at all'
    lo, n_ = 0, 0
    cuts = sorted(taps)
    for b in cuts + [bits]:
        if b > lo:      # plain run lo .. b - 1
            CH8.bus(f'hb_gather_capture_p{n_}', 'hub', b - lo, [(G, f't_capture[{lo}:{b - 1}]'), (C, f'f_gather[{lo}:{b - 1}]')])
            n_ += 1
        if b < bits:    # the tapped bit: gather -> capture + the leaves
            CH8.bus(f'hb_gather_capture_t{b}', 'hub', 1, [(G, f't_capture[{b}:{b}]'), (C, f'f_gather[{b}:{b}]')] + taps[b])
            lo = b + 1
    m.setdefault('hub_stations', {})['hb_gather_capture'] = dict(path_um=round(hb['gather'].y - hb['capture'].y - hb['capture'].h, 1),
                                                                stations=0, floor_added=0, taps=len(cuts))
    # live / ga / q2f: one staged hub lane per leaf and signal (the leaves are temporary hub members for the lane planner)
    # lanes (s81-die r6b): the leaves' ga 16 + q2f 1 (one 17-b chain per leaf) and the live broadcast run in a RELAY ROW
    # under the leaves (seam bottom), to the nearer column edge (W: the S14 channel, E: the VCH), up past the gather in that
    # channel, then along the gather | PQ gap (SPINE_GAP) into the PQ core's S face.  Stations: hstn at <= the hub reach.
    P_, G_ = hb['pq'], hb['gather']
    lx0, lx1 = G_.x, G_.x + G_.w
    ly0 = up(hb['capture'].y + hb['capture'].h + 0.432, GY)       # first lattice row above the capture N face
    ly1 = min(it.y for it, _ in cnt) - 0.432
    row = (lx0 + 4.32, ly0 - 1e-3, lx1 - 4.32, ly1)
    gap = (lx0 + 4.32, G_.y + G_.h + 4.32, lx1 - 4.32, P_.y - 4.32)
    assert ly1 - ly0 >= 17.28 and gap[3] - gap[1] >= 30.0, ('--pq-cnt: relay row / gather|PQ gap too small', row, gap)
    yr = ly0 + stn_dims([17], True)[1] / 2 + 0.01   # station centre: dn(yr - h / 2, GY) = ly0 (Placer.near snaps down)
    assert ly0 + stn_dims([17], True)[1] <= ly1 + 1e-6, ('--pq-cnt: relay row lower than a station', ly0, ly1)
    yg = (gap[1] + gap[3]) / 2
    kl = m.setdefault('_pqcnt_lane', {'W': 0, 'E': 0})

    def path_for(leaf, k_side):
        side = 'W' if leaf.x + leaf.w / 2 < (lx0 + lx1) / 2 else 'E'
        n_ = kl[side]
        kl[side] += 1
        vx = (cor['s14W'][2] - 30.0 - HUB_LANE_PITCH * n_) if side == 'W' else (cor['vch'][0] + 30.0 + HUB_LANE_PITCH * (n_ + 0.5))
        tx = min(max(leaf.x + leaf.w / 2, P_.x + 20.0), P_.x + P_.w - 20.0)
        p_ = [((leaf.x if side == 'W' else leaf.x + leaf.w), yr), (vx, yr), (vx, yg), (tx, yg), (tx, P_.y)]
        allowed = [row, gap, cor['s14W'] if side == 'W' else cor['vch']]
        return _dedup(p_), allowed

    def staged(name, path, allowed, bits, src_eps, dst_eps):
        """chain of hstn stations along path; src_eps / dst_eps: [(inst, port, lo, n)] slices of the bits lane"""
        sts = CH8.run(name, [bits], path, allowed, path[0], reach=CC_REACH if CC_REACH < LINK_STAGE_UM else None)
        pin = 'di'
        for k, (it, s_, hop) in enumerate(sts):
            it.kind, it.domain = 'hstn', P_.domain
            it.master = 'dsfd_hstn%s_%d' % ('h' if it.master.startswith('dsfd_stnh') else 'v', bits)
        nodes = [(it.name, 'di', 'dq') for it, _, _ in sts]
        first, last = (nodes[0][0], 'di') if nodes else None, (nodes[-1][0], 'dq') if nodes else None
        if not nodes:
            for (si, sp, lo, n), (di, dp, lo2, n2) in zip(src_eps, dst_eps):
                CH8.bus(f'{name}_d0_{lo}', 'hub', n, [(si, sp), (di, dp)])
            return 0
        for si, sp, lo, n in src_eps:
            CH8.bus(f'{name}_d0_{lo}', 'hub', n, [(si, sp), (first[0], f'di[{lo}:{lo + n - 1}]')])
        for k in range(1, len(nodes)):
            CH8.bus(f'{name}_d{k}', 'hub', bits, [(nodes[k - 1][0], 'dq'), (nodes[k][0], 'di')])
        for di, dp, lo, n in dst_eps:
            CH8.bus(f'{name}_d{len(nodes)}_{lo}', 'hub', n, [(last[0], f'dq[{lo}:{lo + n - 1}]'), (di, dp)])
        m.setdefault('hub_stations', {})[name] = dict(path_um=round(_poly_len(path), 1), stations=len(nodes))
        return len(nodes)

    # live: ONE staged lane PQ -> the E-end leaf (reverse of its path), then leaf to leaf along the seam through each leaf's
    # registered live_o (one ~144-um hop a leaf): a PQ output bit drives exactly one die net
    lv0, lvn = PQ_CNT_LIVE
    order = sorted(cnt, key=lambda c: c[0].x)
    e_ = order[-1][0]
    pth, alw = path_for(e_, 'live')
    stg = {'live': staged('hb_pq_pqcnt_live', pth[::-1], alw, lvn, [(P_.name, f't_cnt[{lv0}:{lv0 + lvn - 1}]', 0, lvn)],
                          [(e_.name, 'live', 0, lvn)])}
    for (a_, _), (b_, _) in zip(order[1:], order[:-1]):
        CH8.bus(f'pqcnt_live_{a_.name}_{b_.name}', 'hub', lvn, [(a_.name, 'live_o'), (b_.name, 'live')])
    for i, (it, sl_) in enumerate(cnt):
        pth, alw = path_for(it, 'ga')
        stg[it.name] = staged(f'hb_{it.name}_pq', pth, alw, 17, [(it.name, 'ga', 0, 16), (it.name, 'q2f', 16, 1)],
                              [(P_.name, f'f_cnt[{16 * i}:{16 * i + 15}]', 0, 16), (P_.name, f'f_cnt[{192 + i}:{192 + i}]', 16, 1)])
    m['pq_cnt_stages'] = stg
    assert len(cnt) == 12, ('--pq-cnt: the PQ core reads 12 RWB counts (ga_i 192 = 12 x 16)', len(cnt))


def _hub_bus_chain(m, CH8, cor, a_, b_, bits, pa, pb, dom=None, reach_um=None):
    """r9 (S81-RERUN): a hub slab-to-slab bus staged by common-clock stations (ot_fwd_link_stage clocked by the
    driver slab's domain clock, so no crossing and one cycle per station) every <= 430.56 um.  Spine-column slabs
    (VM, SU, gather, capture, collective) leave from their E face and HC slabs from their W face; the bus runs in its
    own VCH lane between them.  A bus whose path fits one hop stays a direct register-to-register wire."""
    hb = m['hub']
    A, Bk = hb[a_], hb[b_]
    hcA, hcB = A.name.startswith('sp_hc_'), Bk.name.startswith('sp_hc_')
    # --ecol-slabs: a second chain between the same slab pair (wfc t_lo + t_lir -> collective: direct face-to-face
    # wires in one column, staged across the VCH once the kit moves) takes its driver port in the name, so its
    # stations do not collide with the first chain's
    lane_forced = ()
    hbn = f'hb_{a_}_{b_}' if f'hb_{a_}_{b_}' not in m.get('hub_stations', {}) else \
        f'hb_{a_}_{re.sub(r"[^A-Za-z0-9_]+", "_", pa).strip("_")}_{b_}'
    # --ecol-slabs: a moved slab stands in the E column (W of the HC halves): it faces the VCH with its W face like HC
    ecol_ = lambda it: bool(ECOL_SLABS or SU_E) and it.x >= m['x_spe'] - 1.0 and not it.name.startswith('sp_hc_')
    fx = lambda it: it.x if (it.name.startswith('sp_hc_') or ecol_(it)) else it.x + it.w
    if SU_E and not ECOL_SLABS:   # --su-e: su_n / hrtx are full-width E-column slabs: on the HC side of the VCH
        hcA, hcB = hcA or ecol_(A), hcB or ecol_(Bk)
    lo, hi = max(A.y, Bk.y) + 20.0, min(A.y + A.h, Bk.y + Bk.h) - 20.0
    same_col = min(A.x + A.w, Bk.x + Bk.w) - max(A.x, Bk.x) > 0.0
    if SUHC_V2 and not SUHC_V2_HC_N and {a_, b_} == {'hc_s', 'vm'} and 'hcc' in cor:
        # --suhc-v2 (order A): the HC's VM row slots (~5.4 kb) leave hc_s by its N face into the HC corridor rows and
        # cross the VCH straight to the VM's E face at those rows (the VM's lowest band, directly opposite the corridor);
        # the corridor + VCH rows are their reserved relay pocket, one y lane per bus spread over the rows the corridor
        # and the VM share (hb_vm_hc_s had no spot when routed up the VCH to the VM's middle)
        hc_, vm_ = (A, Bk) if a_ == 'hc_s' else (Bk, A)
        k_ = m.setdefault('_hcv_lane', [0])
        y0_, y1_ = max(vm_.y, cor['hcc'][1]) + 30.0, min(vm_.y + vm_.h, cor['hcc'][3]) - 30.0
        assert y1_ - y0_ > 100.0, ('HC corridor rows do not face the VM', y0_, y1_)
        yl_ = y0_ + (y1_ - y0_) * ((k_[0] * 0.37) % 1.0)
        xh_ = hc_.x + 60.0 + 90.0 * (k_[0] % 12)
        k_[0] += 1
        p_ = [(xh_, hc_.y + hc_.h), (xh_, yl_), (vm_.x + vm_.w, yl_)]
        path = p_ if hc_ is A else p_[::-1]
        L = _poly_len(path)
        sts = CH8.run(hbn, [bits], path, [cor['hcc'], cor['vch']] + [cor[k2] for k2 in ('vmE',) if k2 in cor], path[0],
                      reach=reach_um or (CC_REACH if CC_REACH < LINK_STAGE_UM else None))
        prev = (A.name, pa)
        for k, (it, s_, hop) in enumerate(sts):
            it.kind, it.domain = 'hstn', dom or A.domain
            it.master = 'dsfd_hstn%s_%d' % ('h' if it.master.startswith('dsfd_stnh') else 'v', bits)
            CH8.bus(f'{hbn}_d{k}', 'hub', bits, [prev, (it.name, 'di')])
            prev = (it.name, 'dq')
        CH8.bus(f'{hbn}_d{len(sts)}', 'hub', bits, [prev, (Bk.name, pb)])
        m.setdefault('hub_stations', {})[hbn] = dict(path_um=round(L, 1), stations=len(sts),
                                                     floor_added=max(0, math.ceil(L / LINK_STAGE_UM - 1e-9) - 1))
        return
    xcol = [cor[k_] for k_ in ('ecolS', 'ecolN', 'vmW', 'vmE', 'hrtxG') if k_ in cor]
    if (hcA != hcB or ((ECOL_SLABS or SU_E) and not same_col)) and hi - lo > 100.0:
        # across the VCH where the two slabs overlap in y: a straight horizontal bus
        lane = m.setdefault('_hb_lane', {}).setdefault('x', [0])
        # --suhc-v2: 8 y lanes + the VM slot buses share these rows: spread over 90 % of the overlap (not the middle half)
        y_ = lo + (hi - lo) * ((0.05 + 0.9 * ((lane[0] * 0.37) % 1.0)) if SUHC_V2 else (0.25 + 0.5 * ((lane[0] * 0.37) % 1.0)))
        if SUHC_V2 and pa.startswith('t_hc_y['):
            # the 8 y lanes: evenly spaced rows of their own over the collective / HC overlap (the shared 0.37-stride
            # counter put lane 7 onto an occupied row: no first-station spot at the VCH W edge)
            ky_ = int(pslice(pa)[1]) // 1024
            y_ = lo + (hi - lo) * (ky_ + 0.5) / 8.0
        if LANE_PINS:
            y_ = _lane_pin_alloc(m, A, Bk, pa, pb, bits, y_, lo, hi, fx(A), fx(Bk))
            if LANE_PINS > 1 and abs(fx(A) - fx(Bk)) > 2 * PIN_SEG:
                # v16 (cut table of v15 run 5): the lane's OWN first / last station stands on the lane row next to each
                # slab face, instead of a separate --pin-relay station that found its site 170-366 um off the lane
                # (g_hb_collective_t_hc_y_*: every bit of the slice jogging across the 60-um face gap, ratio up to
                # 0.615; at the HC face the 1-track station sat 5 um from the 2-track pins: 256 b in 5 um = 2.11).
                # Gap g between the P-track pin face and the 1-track station: the bits/4 that cross the worst line of
                # the fan-in get >= 2 x their tracks on M5 + M7 (ratio <= 0.50): g = bits / 4 / (0.50 x 27.9 /um).
                g_ = min(max(30.0, bits / 4.0 / (0.50 * 27.9)), PIN_SEG - 20.0)
                lane_forced = (g_ + 9.0, abs(fx(A) - fx(Bk)) - g_ - 9.0)
        lane[0] += 1
        path = [(fx(A), y_), (fx(Bk), y_)]
    elif hcA == hcB and same_col and max(A.y, Bk.y) - min(A.y + A.h, Bk.y + Bk.h) <= CC_REACH - (0.0 if {a_, b_} == {'vm', 'pq'} else 60.0):
        # stacked neighbours in one column: face to face across the gap, one hop
        g_ = max(A.y, Bk.y) - min(A.y + A.h, Bk.y + Bk.h)
        CH8.bus(hbn, 'hub', bits, [(A.name, pa), (Bk.name, pb)])
        m.setdefault('hub_stations', {})[hbn] = dict(path_um=round(g_, 1), stations=0, floor_added=0)
        return
    else:
        cl = lambda v, it: min(max(v, it.y + 6.0), it.y + it.h - 6.0)
        ya = cl(Bk.y + Bk.h / 2, A)
        yb = cl(ya, Bk)
        ya = cl(yb, A)
        if ECOL_SLABS:   # an HC face beside the moved stack is covered: enter / leave it beyond the stack
            st_ = [it for it in hb.values() if ecol_(it)]
            if st_:
                s0, s1 = min(it.y for it in st_) - 20.0, max(it.y + it.h for it in st_) + 20.0
                for it_, nm_ in ((A, 'a'), (Bk, 'b')):
                    yv = ya if nm_ == 'a' else yb
                    if it_.name.startswith('sp_hc_') and s0 < yv < s1:
                        yv = s1 if it_.y + it_.h - 6.0 > s1 else s0
                        if nm_ == 'a':
                            ya = yv
                        else:
                            yb = yv
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
            mk_ = re.fullmatch(r't_(tf|sr)(\d)', pa)
            if 'hc_t' in (a_, b_) and mk_:
                # contract v12: one crossing per HC column, at that column's centre (fwd W of it, return E of it)
                cp_ = (HC_V2_UM[0] + 43.2) / HC_T_COLS        # 576.72 slot + 43.2 channel = 619.92
                # --hc-rtl-widths: the two runs (2 tracks a bit) sit side by side without overlap around the column centre
                off_ = max(90.0, (HC_T_FWD + HC_T_RET) * 0.048 * LANE_PINS / 4 + 10.0) if HC_RTL_WIDTHS else 90.0
                xx = A.x + cp_ * int(mk_.group(2)) + (cp_ - 43.2) / 2 + (-off_ if mk_.group(1) == 'tf' else off_)
            path = [(xx, A.y + A.h), (xx, Bk.y)] if A.y < Bk.y else [(xx, A.y), (xx, Bk.y + Bk.h)]
            L = _poly_len(path)
            name = hbn
            sts = CH8.run(name, [bits], path, [cor['hcc']] + ([cor['hrtxG']] if 'hrtxG' in cor else []), path[0], reach=CC_REACH if CC_REACH < LINK_STAGE_UM else None)
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
            if CTRL_ADAPTERS and vx > m['x_vch'] + VCH8 - 30.0:
                # --ctrl-adapters (s81die-1011/ctrl): the engine command plane adds ~25 narrow sp chains; lane k past the
                # VCH's E edge ran into the HC column (hb_capture_gather: no station spot at x 17,620).  Overflow lanes
                # wrap inside the VCH half a pitch off the first pass (stations are placed against occupancy).
                nl_ = max(1, int((VCH8 - 60.0) // HUB_LANE_PITCH))
                vx = m['x_vch'] + 30.0 + HUB_LANE_PITCH * ((k_[0] % nl_) + 0.5 * ((k_[0] // nl_) % 2))
        elif side == 'hc':
            vx = m['x_spe'] - 30.0 - HUB_LANE_PITCH * k_[0]
        else:
            vx = m['x_vch'] + VCH8 / 2 + 70.0 * k_[0]
        k_[0] += 1
        path = _dedup([(fx(A), ya), (vx, ya), (vx, yb), (fx(Bk), yb)])
    name = hbn
    L = _poly_len(path)
    if L <= (reach_um or CC_REACH) - 30.0:
        CH8.bus(name, 'hub', bits, [(A.name, pa), (Bk.name, pb)])
        m.setdefault('hub_stations', {})[name] = dict(path_um=round(L, 1), stations=0)
        return
    try:
        sts = CH8.run(name, [bits], path, [cor['vch']] + [cor[k_] for k_ in ('collE', 'collW') if k_ in cor] + xcol, path[0],
                      forced=lane_forced, reach=reach_um or (CC_REACH if CC_REACH < LINK_STAGE_UM else None))
    except RuntimeError:
        if LANE_PINS:   # diagnosis: what stands on the lane
            x0_, x1_ = min(p_[0] for p_ in path), max(p_[0] for p_ in path)
            y0_, y1_ = min(p_[1] for p_ in path) - 60.0, max(p_[1] for p_ in path) + 60.0
            print('LANE_PINS blocked', name, path, 'cor', {k_: v_ for k_, v_ in cor.items() if k_ in ('vch', 'collE', 'collW')},
                  [(i_.name, i_.master, round(i_.x), round(i_.y), round(i_.w), round(i_.h)) for i_ in m['insts']
                   if i_.x < x1_ and i_.x + i_.w > x0_ and i_.y < y1_ and i_.y + i_.h > y0_][:40], file=sys.stderr, flush=True)
        raise   # collE/W: --coll-split3 column remainder
    prev = (A.name, pa)
    for k, (it, s_, hop) in enumerate(sts):
        it.kind, it.domain = 'hstn', dom or A.domain
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
            if sink[1] is not None:
                m['buses'][i] = (bid, cls, bits, eps + [(sink[0], sink[1])])
        elif eps[0] == (st_inst.name, do):
            m['buses'][i] = (bid, cls, bits, eps + [(sink[0], sink[2])])
            break
    else:
        lw = int(st_inst.master.split('_')[2].split('x')[0])
        if sink[1] is not None:
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

    def single(name, payload, fmt, src, src_xy, path, sink_end, canonical_access=None):
        """src: (inst, fclk port, data port); sink_end: (end inst) -> lane 0 ports fi0/di0"""
        lw = payload + (2 if fmt == 'vr' else 0)
        if HUB_SOUTH_SHIFT:
            su = hub['su_s']
            clearance = max(stn_dims([lw], True) + stn_dims([lw], False)) + 17.28
            below = su.y - clearance
            left, right = su.x - clearance, su.x + su.w + clearance
            detour = [path[0]]
            for a_, b_ in zip(path, path[1:]):
                if (abs(a_[1]-b_[1]) < 1e-6 and su.y < a_[1] < su.y+su.h
                        and min(a_[0], b_[0]) < left and max(a_[0], b_[0]) > right):
                    entry, exit_ = (left, right) if a_[0] < b_[0] else (right, left)
                    detour += [(entry,a_[1]), (entry,below), (exit_,below), (exit_,b_[1])]
                    m.setdefault('south_su_bypass_chains', []).append(name)
                detour.append(b_)
            path = detour
        if MIX4_SLOT:
            # S-DIE r11 10-15: the MIX4 home sits in the VCH south of the VM (x 15714, 771 wide); a vertical VCH lane
            # through it (GEN17: only the d5_bk_selector ctrl lane at x 16102) steps east of the home for its length
            mx0, my0, mw, mh = MIX4_SLOT
            clr = max(stn_dims([lw], True) + stn_dims([lw], False)) + 17.28
            nb_ = len(m.setdefault('mix4_bypass_chains', []))
            xb = mx0 + mw + clr + 21.6 * (nb_ % 4)
            out_ = [path[0]]
            for a_, b_ in zip(path, path[1:]):
                if (abs(a_[0] - b_[0]) < 1e-6 and mx0 - clr < a_[0] < mx0 + mw + clr
                        and min(a_[1], b_[1]) < my0 + mh + clr and max(a_[1], b_[1]) > my0 - clr):
                    out_ += [(xb, a_[1]), (xb, b_[1])]
                    m['mix4_bypass_chains'].append(name)
                out_.append(b_)
            path = out_
        narrow_service = CANONICAL_LAYOUT and (canonical_access is not None or re.fullmatch(r'(q|a|ix|co)[NS][WE]',name))
        if narrow_service:
            from s81.canonical_layout import service_path
            endpoint=(sink_end.x+sink_end.w/2,sink_end.y+sink_end.h/2)
            side,service_source=canonical_access or (name[-1],name[0]!='q')
            if not service_source:
                path=service_path(sys.modules[__name__],m,cor,src_xy,endpoint,side)
            else:
                path=list(reversed(service_path(sys.modules[__name__],m,cor,endpoint,src_xy,side)))
        # A wide service record uses its real W/E-face station in an RSC
        # vertical access lane; its17.256um body fits, its54.84um N/S-face
        # alternative does not. Actual pin turns/reach remain to be audited.
        sts = CH8.run(name, [lw], _dedup(path), allc, src_xy,
                      force_horiz=bool(narrow_service and not CANONICAL_LAYOUT.get('service_access_corridors')
                                       and stn_dims([lw],False)[0]>RSC_W-.864))
        chain_nets(CH8, name, src, [it for it, _, _ in sts], [lw])
        tail = m['chain_tail'][name]
        CH8.bus(f'{name}_fe', 'fclk', 1, [(tail[0], tail[1]), (sink_end.name, 'fi0')])
        CH8.bus(f'{name}_de', 'lane', lw, [(tail[0], tail[2]), (sink_end.name, 'di0')])
        return sts

    def beside_svc(name, master, w, h, sv, off):
        x, y = face_pt(sv, off)
        yy = y + h / 2 + 6.0 if sv.orient == 'R0' else y - h / 2 - 6.0
        pl = P.near(x, yy, w, h, [cor['stripS'] if sv.orient == 'R0' else cor['stripN']], horiz=True, span=400.0)
        if not pl and BF_SEAM_UM:
            # The compact BF frame changes the shoreline strip's available
            # sites. Place the receiver on the service's complete physical
            # face, then let its generated peer pins and normal reach gates
            # judge the connection; never force it into the old 400-um pocket.
            strip_ = cor['stripS'] if sv.orient == 'R0' else cor['stripN']
            face_ = (max(strip_[0],sv.x), strip_[1], min(strip_[2],sv.x+sv.w), strip_[3])
            pl = P.near(x, yy, w, h, [face_], horiz=True, span=sv.w,
                        rows=max(1, int((face_[3]-face_[1])/max(h,4.32))))
            if not pl and face_[3]-face_[1] < h:
                # The true compact frame leaves only 103.68 um above the
                # shoreline service, less than the receiver's height. Allocate
                # side bays beside that service instead of stretching the
                # strip or shrinking a hardened leaf. Occupancy still rejects
                # every overlap with service/control/SU tiles.
                if sv.orient == 'R0':
                    by0, by1 = sv.y+sv.h-h-17.28, face_[3]
                else:
                    by0, by1 = face_[1], sv.y+h+17.28
                bays = [(sv.x-w-21.6,by0,sv.x-4.32,by1),
                        (sv.x+sv.w+4.32,by0,sv.x+sv.w+w+21.6,by1)]
                pl = P.near(x,yy,w,h,bays,horiz=True,span=sv.w+2*w,rows=8)
                if pl:
                    allc.extend(bays)
                    m.setdefault('compact_bf_service_bays', {})[name] = bays
            if pl:
                m.setdefault('compact_bf_service_sites', {})[name] = dict(rect=[*pl,w,h], service=sv.name, corridor=face_)
            else:
                raise RuntimeError(('no service-facing receiver site',name,'leaf_um',(w,h),'corridor',face_,
                                    'service_rect',sv.box()))
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
    if FWD_IFACE:
        _fwd_ifaces(m, CH8, P, cor, end_spec, single, beside_svc, face_pt, strip_y, spine_x, vmy)


def _fwd_ifaces(m, CH8, P, cor, end_spec, single, beside_svc, face_pt, strip_y, spine_x, vmy):
    """--fwd-iface (s81-gen 2026-10-09): the die-crossing host-write and layer1e Engram interfaces as FORWARDED lanes
    (source-synchronous stations + an end block at the sink: m2l meso into a stream block, r2l ratio CDC into the serial
    VM; an l2r start block when the VM is the source), the way the svc <-> VM / selector / collector chains are built.
    The common-clock hop-fix chains they replace ran 20 mm through 6-8 clock regions: die-evidence-2 s81_l1full clock
    plan, 8 inter-region pairs up to 322 ps (budget 150) on hw_SW / hc_SW."""
    hub = m['hub']
    vm = hub['vm']
    band = lambda it: it.kind == 'svc'
    offs = {}

    def nxt_off(it):
        """next face offset (from the east end) on a band block: svc_SW from 1,900 um west of the existing svc chain
        taps (400-1,500) in 150 um steps; eng_SE (1,188 um) from its east end in 80 um steps"""
        wide = it.w > 3000
        o_ = offs.get(it.name, 1900.0 if wide else 40.0)
        offs[it.name] = o_ + (150.0 if wide else 80.0)
        assert o_ < it.w - 20.0, (it.name, o_)
        return o_

    def sink_end(tag, payload, dst, side):
        kind = 'r2l' if dst.domain == 'serial_0p9' else 'm2l'
        nm, w, h = end_spec(kind, [payload], 'vr')
        if band(dst):
            x, y = face_pt(dst, nxt_off(dst))
            if dst is hub.get('eng') or dst is hub.get('hrow'):   # end blocks in the free SE slot, on the block's top face
                pl = P.near(x, y + h / 2 + 6.0, w, h, [cor['engS' if dst is hub.get('eng') else 'hrowS']], horiz=True,
                            span=1200.0, rows=20)
                assert pl, tag
                return P.add(Inst(f'he_{tag}', nm, pl[0], pl[1], w, h, 'R0', kind='hend', region='svc'))
            return beside_svc(f'he_{tag}', nm, w, h, dst, dst.x + dst.w - x)
        y = dst.y + dst.h / 2 + (len(m.setdefault('_fwd_end', {}).setdefault(dst.name, [])) - 2) * 60.0
        m['_fwd_end'][dst.name].append(tag)
        return P.add(_hub_at(P, f'he_{tag}', nm, w, h, dst, side, y, cor))

    def pin(it, side, tag):
        if band(it):
            return face_pt(it, nxt_off(it))
        k_ = len(m.setdefault('_fwd_src', {}).setdefault(it.name, []))
        m['_fwd_src'][it.name].append(tag)
        return (it.x if side == 'W' else it.x + it.w, it.y + it.h / 2 + (k_ - 2) * 40.0)

    def lane(tag, payload, src, sport, dst, dport, side):
        """src.sport -> dst.dport (payload bits + valid/ready framing), forwarded on `side` of the spine"""
        start = src
        if src.domain == 'serial_0p9':          # serial VM: an l2r start block beside it
            nm, w, h = end_spec('l2r', [payload], 'vr')
            start = P.add(_hub_at(P, f'hs_{tag}', nm, w, h, src, side, vmy + 1150.0 + 60.0 * len(m.get('_fwd_l2r', [])), cor))
            m.setdefault('_fwd_l2r', []).append(tag)
            CH8.bus(f'hs_{tag}_i', 'local', payload + 1, [(src.name, sport), (start.name, 'i')])
            CH8.bus(f'hs_{tag}_s', 'local', 3, [(start.name, 'st'), (src.name, sport + 's')])
            a = (start.x + start.w / 2, start.y + start.h / 2)
            srcp = (start.name, 'fo', 'od')
        else:
            a = pin(src, side, tag)
            srcp = (src.name, sport + 'f', sport + 'd')
        he = sink_end(tag, payload, dst, side)
        b = (he.x + he.w / 2, he.y + he.h / 2)
        sx = spine_x(side)
        if band(src) and band(dst):             # band -> band along the strip
            sy = strip_y(src, tag)
            path = [a, (a[0], sy), (b[0], sy), b]
        elif band(src):
            sy = strip_y(src, tag)
            path = [a, (a[0], sy), (sx, sy), (sx, b[1]), b]
        elif band(dst):
            sy = strip_y(dst, tag)
            path = [a, (sx, a[1]), (sx, sy), (b[0], sy), b]
        else:
            path = [a, (sx, a[1]), (sx, b[1]), b]
        access=(side,band(src)) if band(src)!=band(dst) else None
        single(tag, payload, 'vr', srcp, a, path, he, canonical_access=access)
        CH8.bus(f'he_{tag}_o', 'local', payload + 3, [(he.name, 'o'), (dst.name, dport)])

    if HOST_SLAB and CTRL_RQ and not _svc_c_host():
        for st in m['ctrls']:
            cl = m['svcs'][st] if st in m['svcs'] else hub['eng']
            side = 'W' if st[1] == 'W' else 'E'
            lane(f'hw{st}', 512 + 64 + 2, hub['host'], f'tw{st}', cl, 'hw', side)
            lane(f'hc{st}', 18, cl, 'hc', hub['host'], f'fc{st}', side)
    if 'hrow' in hub:      # mtp-dsbind: the row store's lanes (SE slot <-> spine slabs / host), forwarded like Engram's
        for a_, b_, bits, pa, pb in HROW_LANES + (HROW_HOST_BUSES if 'host' in hub else ()):
            # into a spine slab: the end block in the S14 W channel (the VCH beside the collective is taken by the
            # collective's own lane ends); out of the spine / into the SE slot: the E (VCH) side
            lane(f'h_{a_}_{pa}_{pb}', bits, hub[a_], pa, hub[b_], pb, 'W' if hub[b_].kind != 'svc' else 'E')
    if CTRL_ADAPTERS:
        _ctrl_band_lanes(m, CH8, P, cor, end_spec, single, beside_svc, face_pt, strip_y, spine_x, sink_end, band)
    if 'eng' in hub:
        for a_, pa, b_, pb, bits, _ in ENG_BUSES:
            lane(f'e_{a_}_{pa}', bits, hub[a_], pa, hub[b_], pb, 'E')
        lane('e_swq', 35, hub['eng'], 'teq', m['svcs']['SW'], 'feq', 'W')
        lane('e_swr', 265, m['svcs']['SW'], 'ter', hub['eng'], 'fer', 'W')


def _svc_c_host():
    """--ctrl-adapters with the svc join bound: the per-stack host write faces are dsfd_host_s hw / hc <-> dsfd_svc_c"""
    if not CTRL_ADAPTERS:
        return False
    b_ = json.loads((ROOT / 'physical/s81_ctrl/die_ctrl_bindings.json').read_text())
    return CTRL_SVC_JOIN in b_['engines'].get('svc', {}).get('masters', [])


def _ctrl_band_lanes(m, CH8, P, cor, end_spec, single, beside_svc, face_pt, strip_y, spine_x, sink_end, band):
    """--ctrl-adapters (s81die-1011/ctrl): the engine command plane to slabs OUTSIDE the hub column (the band blocks
    bk_selector / bk_collector, the per-stack svc slabs through dsfd_svc_join, the layer1e eng_SE slab).  They sit in
    other clock regions, so each pulse group travels as a FORWARDED lane (source-synchronous stations) between a start
    block at the driver (l2r: i = {v, payload}) and an end block at the sink (m2l meso; o[0:w-1] = the group), the
    way the svc <-> VM / selector / collector chains are built: sseq c<e> 85 -> slab c_cmd, slab c_done 9 -> d<e>,
    slab c_st 2 -> s<e>, three lanes per engine (a lane never mixes a pulse group with the level status).
    svc (engine 4): one dsfd_svc_join beside svc_SW (the die's first stack) holds the pinned endpoint; its job pulses
    j_cmd {v, arg 24, tag 8} 33 b and the slabs' j_dn {fault, done} 2 b run as lanes to every svc_<st> (direct pins
    for the adjacent stack)."""
    hub = m['hub']
    bind = json.loads((ROOT / 'physical/s81_ctrl/die_ctrl_bindings.json').read_text())
    eng = dict(fld=0, su=1, hc=2, coll=3, svc=4, sel=5, col=6, hop=7, head=8, emb=9, eng=10, spare=11, vm=12)
    sq = hub['sseq']
    starts = m.setdefault('_ctrl_starts', {})

    def blk_at(name, nm, w, h, blk):
        """a lane end / start block beside a band block (bk_selector S / bk_collector N) in the S / N gap, E face,
        spread over the block's height (the hix / hco ends use 0.3 / 0.7 of it)"""
        k_ = len(m.setdefault('_ctrl_blk', {}).setdefault(blk.name, []))
        m['_ctrl_blk'][blk.name].append(name)
        y = blk.y + blk.h * (0.15 + 0.1 * (k_ % 8))
        x = blk.x + blk.w + w / 2 + 6.0
        pl = P.near(x, y, w, h, [cor['gapS'] if blk.y < DIE[1] / 2 else cor['gapN']], horiz=False, span=400.0, rows=12)
        assert pl, name
        return P.add(Inst(name, nm, pl[0], pl[1], w, h, 'R0', kind='hend', region='svc'))

    def end_at(tag, payload, at, side):
        if at.kind == 'band_blk':
            nm, w, h = end_spec('m2l', [payload], 'vr')
            return blk_at(f'he_{tag}', nm, w, h, at)
        return sink_end(tag, payload, at, side)

    def start_at(tag, w_i, at, side):
        nm, w, h = end_spec('l2r', [w_i - 1], 'vr')
        if at.kind == 'band_blk':
            st_ = blk_at(f'hs_{tag}', nm, w, h, at)
        elif band(at):
            x, y = face_pt(at, nxt_off_c(at))
            yy = y + h / 2 + 6.0 if at.orient == 'R0' else y - h / 2 - 6.0
            strip_ = cor['stripS'] if at.orient == 'R0' else cor['stripN']
            # s81-die-iter 10-12 (c1e plan: AssertionError d10_eng_SE): a band slab in the free SE service slot (layer1e
            # eng_SE / hrow_SE) sits below stripS, so its start blocks stand in the slot box around it (engS / hrowS, as
            # the fwd-iface sink ends do) before climbing into the strip
            slot_ = cor.get('engS') if at is hub.get('eng') else cor.get('hrowS') if at is hub.get('hrow') else None
            pl = P.near(x, yy, w, h, ([slot_] if slot_ else []) + [strip_], horiz=True, span=1200.0,
                        rows=20 if slot_ else 12)
            assert pl, tag
            st_ = P.add(Inst(f'hs_{tag}', nm, pl[0], pl[1], w, h, 'R0', kind='hend', region='svc'))
        else:
            st_ = P.add(_hub_at(P, f'hs_{tag}', nm, w, h, at, side, at.y + at.h / 2 + 50.0 * (len(starts) % 8 - 4), cor))
        starts[tag] = st_
        return st_

    offs_c = {}

    def nxt_off_c(it):
        """start-block face offsets on a band slab: 2,600 um west of its east end (past the svc / fwd-iface taps) in
        90 um steps; a narrow band slab (eng_SE) from its centre"""
        o_ = offs_c.get(it.name, 2600.0 if it.w > 3000 else it.w / 2)
        offs_c[it.name] = o_ + 90.0 * (1 if it.w > 3000 else -1)
        return o_

    def ctrl_lane(tag, w_i, src, sport, dst, dport, side, src_at=None, dst_at=None):
        """src.sport (w_i bits = {v, payload}) -> dst.dport (w_i bits), forwarded; *_at = the placement anchor (the
        svc join stands beside svc_SW: its lane ends are placed on svc_SW's face)"""
        sa, da = src_at or src, dst_at or dst
        st_ = start_at(tag, w_i, sa, side)
        CH8.bus(f'hs_{tag}_i', 'local', w_i, [(src.name, sport), (st_.name, 'i')])
        he = end_at(tag, w_i - 1, da, side)
        a = (st_.x + st_.w / 2, st_.y + st_.h / 2)
        b = (he.x + he.w / 2, he.y + he.h / 2)
        sx = spine_x(side)
        bk_ = lambda it: (it.y - 30.0) if it.y > DIE[1] / 2 else (it.y + it.h + 30.0)   # band block's die-centre edge
        if sa.kind == 'band_blk':          # leave the band block's gap at its die-centre edge, then the spine
            path = [a, (a[0], bk_(sa)), (sx, bk_(sa)), (sx, b[1]), b]
        elif da.kind == 'band_blk':
            path = [a, (sx, a[1]), (sx, bk_(da)), (b[0], bk_(da)), b]
        elif band(da) and band(sa):
            sy = strip_y(da, tag)
            path = [a, (a[0], sy), (b[0], sy), b]
        elif band(sa):
            sy = strip_y(sa, tag)
            path = [a, (a[0], sy), (sx, sy), (sx, b[1]), b]
        elif band(da):
            sy = strip_y(da, tag)
            path = [a, (sx, a[1]), (sx, sy), (b[0], sy), b]
        else:
            path = [a, (sx, a[1]), (sx, b[1]), b]
        access=(side,band(sa)) if band(sa)!=band(da) else None
        single(tag, w_i - 1, 'vr', (st_.name, 'fo', 'od'), a, path, he, canonical_access=access)
        CH8.bus(f'he_{tag}_o', 'local', w_i, [(he.name, f'o[0:{w_i - 1}]'), (dst.name, dport)])

    def bind_slab(e, slab, side, at=None):
        k = eng[e]
        ctrl_lane(f'c{k}_{slab.name}', 85, sq, f'c{k}', slab, 'c_cmd', side, dst_at=at)
        ctrl_lane(f'd{k}_{slab.name}', 9, slab, 'c_done', sq, f'd{k}', side, src_at=at)
        ctrl_lane(f's{k}_{slab.name}', 2, slab, 'c_st', sq, f's{k}', side, src_at=at)

    for e, key in (('sel', 'selector'), ('col', 'collector'), ('eng', 'eng')):
        it = hub.get(key)
        if it is not None and it.master in bind['engines'].get(e, {}).get('masters', []):
            bind_slab(e, it, 'E')
    svcs = m.get('svcs', {})
    if svcs and CTRL_SVC_JOIN in bind['engines'].get('svc', {}).get('masters', []):
        sts = list(svcs)
        sv0 = svcs[sts[0]]
        for st in sts:
            svcs[st].master = CTRL_SVC_MASTER
        jw, jh = 64.8, 43.2                          # contract v12: closed ref_tile view s81_svcjoin_ref (scalar ck / rst)
        x, y = face_pt(sv0, 2300.0)
        yy = y + jh / 2 + 6.0 if sv0.orient == 'R0' else y - jh / 2 - 6.0
        pl = P.near(x, yy, jw, jh, [cor['stripS'] if sv0.orient == 'R0' else cor['stripN']], horiz=True, span=800.0)
        assert pl, 'svcj'
        jn = P.add(Inst('svcj', CTRL_SVC_JOIN, pl[0], pl[1], jw, jh, 'R0', kind='svcj', region='svc', domain=sv0.domain))
        m.setdefault('ctrl_svc_join', dict(inst='svcj', ns=len(sts), stacks=sts))
        bind_slab('svc', jn, 'W' if sts[0][1] == 'W' else 'E', at=sv0)
        for i_, st in enumerate(sts):
            sv = svcs[st]
            js, ds = f'j_cmd[{33 * i_}:{33 * i_ + 32}]', f'j_dn[{2 * i_}:{2 * i_ + 1}]'
            if i_ == 0:                              # the adjacent stack: face-to-face pins (join beside its face)
                CH8.bus(f'svcj_j{st}', 'local', 33, [(jn.name, js), (sv.name, 'j')])
                CH8.bus(f'svcj_d{st}', 'local', 2, [(sv.name, 'jd'), (jn.name, ds)])
            else:                                    # other stacks: forwarded lanes (band -> band / across the VCH)
                sd_ = 'W' if st[1] == 'W' else 'E'
                ctrl_lane(f'j_{st}', 33, jn, js, sv, 'j', sd_, src_at=sv0)
                ctrl_lane(f'jd_{st}', 2, sv, 'jd', jn, ds, sd_, dst_at=sv0)
        if HOST_SLAB and CTRL_RQ and 'host' in hub:
            # per-stack host writes (s81-svceng host interface, ds-1010.log: host master dsfd_host_s #(NS); svc side
            # dsfd_svc_c hw / hc, claude/el1011-s81svch eccab9f14): host hw[292 s +: 292] = {cls 2, we, addr 32, d 256, v}
            # -> svc_<st> hw; svc hc {ack 8, cr} -> host hc[9 s +: 9]; forwarded lanes as the old 578 / 18-b host lanes
            # s81-die-rtl-bind 2026-10-14 (F6): a layer die's host master is dsfd_host_c (rtl/dsrom_sys/s81_ingest:
            # the ingest behind the collective's host channel + the sequencer program / status faces); dsfd_host_s
            # (host-link face h_v / h_cls / h_d) stays the head-die master
            hm_ = 'dsfd_host_c' if (RTL_BIND and DIE_KIND in ('layer', 'layer1', 'layer1e')) else 'dsfd_host_s'
            hub['host'].master = hm_
            m.setdefault('ctrl_host', dict(master=hm_, ns=len(sts), stacks=sts))
            for i_, st in enumerate(sts):
                sd_ = 'W' if st[1] == 'W' else 'E'
                ctrl_lane(f'hw{st}', 292, hub['host'], f'hw[{292 * i_}:{292 * i_ + 291}]', svcs[st], 'hw', sd_)
                ctrl_lane(f'hc{st}', 9, svcs[st], 'hc', hub['host'], f'hc[{9 * i_}:{9 * i_ + 8}]', sd_)


def _hub_at(P, name, master, w, h, slab, side, y, cor):
    """an end / start block beside a hub slab: side 'W' in the S14 W channel, 'E' in the VCH"""
    assigned = _assigned_record(master + '__' + name)
    if assigned and assigned.get('outline_change_request'):
        w, h = assigned['outline_um']
    x = slab.x - w / 2 - 6.0 if side == 'W' else slab.x + slab.w + w / 2 + 6.0
    pl = P.near(x, y, w, h, [cor['s14W'] if side == 'W' else cor['vch']], horiz=False, span=1800.0, rows=6)
    if not pl and name.startswith('he_h_'):
        # mtp-dsbind hrow lanes: the channel beside a crowded slab (collective with the MTP lanes) is full near its
        # centre; search the channel's whole height for the end block (the lane's stations follow it there)
        pl = P.near(x, y, w, h, [cor['s14W'] if side == 'W' else cor['vch']], horiz=False, span=6000.0, rows=20)
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
        if RELAY_PROGRESS:
            # --relay-progress: the half station stays within 150 um of the half's pin centre (it must not slide along
            # the macro face behind its feeding chain); a wider search along the face, not a far slot
            pl = P.near(x0 + w / 2, yc, w, h_, allc, prev=None, horiz=False, span=400.0, rows=40,
                        nxt=(x0 + w / 2, yc), nreach=150.0)
            if pl is None:
                _rp_log(dict(split=nm, port=port, half=h, yc=yc))
                pl = P.near(x0 + w / 2, yc, w, h_, allc, prev=None, horiz=False, span=200.0, rows=16)
        else:
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
        if PIN_ALIGN and not (LINK_SPLIT and lk.master == real_lef(SERDES_LEF)['name']):
            # --pin-align: an un-split link macro (UCIe: 512 tx / rx pins over 823 um of its face) fans into ONE 25-um
            # station pin group: up to 249 jog wires cross the gap between macro and station.  At the 5.5 / 8.6 um gap
            # that is 1.43 / 0.92 of its tracks (FAIL); the end stations are aimed 26 um off the face (gap >= 14: <= 0.57).
            lx += 26.0 if side == 'W' else -26.0      # the 36.7-um edge corridor starts 5 um off the face: +26 = gap >= 14
        if LINK_FIX:
            ly_t, ly_r = link_span_y(lk, 'tx'), link_span_y(lk, 'rx')
        else:
            ly_t = ly_r = ly
        n_side = sum(1 for l_ in m['links'] if l_.name[3] == side)
        yy = cy + (i - 1.5) * 90.0 if n_side <= 4 else cy + (i - (n_side - 1) / 2) * min(90.0, 0.8 * coll.h / n_side)
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
        if CANONICAL_LAYOUT is not None:
            from s81.canonical_layout import Roadmap
            road = Roadmap(sys.modules[__name__], m, cor)
            ci = 0 if side == 'W' else 21
            roots = [r for r, f in m['frames'].items() if f['column_index'] == ci]
            rr = min(roots, key=lambda r: abs(m['frames'][r]['street'][1] + 79.8 - ly_t))
            field_path = _dedup(core + road.to_root(side, core[-1], rr, 'x'))
            ry = field_path[-1][1]
            path = _dedup(field_path + [(edge[side], ry), (edge[side], ly_t), (lx, ly_t)])
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
            off_ = psrc(port)[1]
            port, lo, hi = pslice(port)
            if lo is not None:
                assert (hi - lo + 1 == bits) if off_ is None else (j > 0 and off_ + hi - lo + 1 <= bits), \
                    (bid, inst, port, lo, hi, bits, off_)
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
            it.master = f'dsfd_sstn_{code or "x"}' + ('_x2' if 'x2i' in u else '')
            if m.get('sstn_ccpad', {}).get(it.name):
                it.master += f"_cp{m['sstn_ccpad'][it.name]}"     # --sstn-ccpad: N extra cc registers
                it.master += ''.join(f't{j}' for j in range(4) if f'cct{j}' in u)   # + pad taps cct<j>
        elif it.kind == 'node':
            par = [e for b_ in m['_nets_of_o'].get(it.name, []) for e in b_[3][1:]]
            py = max((by_[e[0]].y for e in par), default=0.0)
            it.master = 'dsfd_node_%s%s%s%s' % ('L' if u['a'][1] == LEAF else 'N', 'L' if u['b'][1] == LEAF else 'N',
                                                'f' if 'fi' in u else '', 'u' if py > it.y else 'd')
    pdir = defaultdict(dict)
    real_ = set(real_ports()) if RTL_BIND else set()
    for it in m['insts']:
        for p_, (d, b) in use.get(it.name, {}).items():
            old = pdir[it.master].get(p_)
            if old and old[0] == d == 'output' and it.master in real_:
                # --rtl-bind: a REAL macro's output bundle may be read to different depths per instance (cfg ROM rd 48 for
                # the field sequencers, 64 for the PQ phase ROMs): the netlist binds the read bits by pin name and gives
                # the rest spare no-load nets, so the master records the widest use
                pdir[it.master][p_] = (d, max(b, old[1]))
                continue
            if old and (old[0] != d or old[1] != b):
                raise ValueError(f'{it.master}.{p_}: {old} vs {(d, b)} on {it.name}')
            pdir[it.master][p_] = (d, b)
    m['pdir'] = pdir
    for it in m['insts']:
        if it.kind == 'hend':
            it.power_w = 5 * sum(b for d, b in pdir[it.master].values() if d == 'input') * FLOP_CLK_W * 1.5
    apply_view_binding(m, pdir)
    if ALIGN_JOGS:
        align_station_jogs(m)
    return pdir


STATION_KINDS = ('stn', 'hstn', 'sstn', 'xstg')
ALIGN_EXT = [True]             # r8: align-jogs extensions (aligned runs, partial moves, spread entry) on the final build only:
                               # r8b screen applied them in the hop-plan passes too, so the plan saw a spread / shifted chain
                               # the final build did not reproduce (tf2 d8: 3,056 b at 799 um, 11,377 bits over 500)
ALIGN_STN_REACH_UM = 450.0     # r7: a station->station hop moved by --align-jogs stays <= 450 um a bit (hop gate 500)
ALIGN_HARD_SHORT_UM = 100.0    # r11 10-15: a pure normal retreat of a station off a hard face may lengthen that short hop by the
                               # retreat only while every bit stays <= 100 um (below the smallest die pair reach, cc 215 um).
                               # GEN17: f_crE2_E0_hub_20 -> hr_E2 (2.9-um gap, 28.3-um jog, cut 0.77) and crW0_W0
                               # edge43_3 -> edge46_1 (abutted, 19.4-um jog) need only a 0.9-4 um wider channel, but every
                               # retreat candidate carried a tangent move that lengthened a lane jogging the other way.


def align_station_jogs(m, rounds=2):
    """--align-jogs (r5 2026-10-14, pin_align FAIL bundles of xsp4: station -> hub end block / gather with a 28-430 um
    sideways jog in a 0.7-38 um channel): a generated station facing its peer straight across is moved along the shared
    face axis by the bundle's jog, so its pins stand opposite the peer's (the station master's pins are shared by all its
    instances; the instance moves, not the pins).  Only when the moved box overlaps nothing and stays on the die; the
    hop gate / pin align gate re-judge the result."""
    for d_ in (str(ROOT / 'tools' / 'hier_contract'), str(ROOT / 'tools' / 's81')):   # die_hop_gate lives in tools/s81
        if d_ not in sys.path:
            sys.path.insert(0, d_)
    import pin_align as PA
    import die_hop_gate as HG
    rp = real_ports()

    def names(it, port, bits):
        base, lo, _hi = pslice(port)
        lo = lo or 0
        t = rp.get(it.master, {}).get(base)
        return t[lo:lo + bits] if t is not None else [f'{base}[{lo + i}]' for i in range(bits)]
    by = {it.name: it for it in m['insts']}
    moved = {}
    # Aligning one face must preserve every other data hop of that station.
    # xsp7 moved a VM->PQ bridge 1028 um and broke its already staged input.
    incident = {}
    for bid, cls, bits, eps in m['buses']:
        if cls in HOP_SKIP:
            continue
        if not eps or eps[0][0] not in by:
            continue
        for load in eps[1:]:
            if load[0] not in by:
                continue
            hop = (eps[0], load, bits)
            for nm in {eps[0][0], load[0]}:
                incident.setdefault(nm, []).append(hop)

    ppins = PA.read_pins(die_lef_texts(m))

    def pts(it, port, bits):
        w, h, pp = ppins.get(it.master, (0.0, 0.0, {}))
        nm = names(it, port, bits)
        out = []
        for i in range(bits):
            q = pp.get(nm[i]) if i < len(nm) else None
            if q is None and bits == 1:
                q = pp.get(pslice(port)[0])
            out.append(None if q is None else PA.place(it, w, h, q))
        return out

    def worsens_hop(it, nx, ny, group=None, hard_allow=0.0):
        """True when moving `it` to (nx, ny) is not safe for one of its connected data hops.  A hop may not get longer,
        EXCEPT a station-to-station hop (both ends generated stations, registered at both ends): it may lengthen up to
        ALIGN_STN_REACH_UM per bit provided the re-judged bundle is not a pin_align FAIL (r7 10-14: the never-lengthen
        rule left jog9's 5 hub station chains (hb_collective_vm d10/d16, hb_hc_s_hc_t d8, hc_t t_sr1, hr_W2 -> gather)
        with 84-255 um jogs in 4.6-86 um channels: moving the station onto its jogged peer adds the same y to a long
        straight hop of its other side, which only spreads the jog over a longer channel).
        `group` (r8): the other stations moved rigidly with `it` by the same offset; hops between two group members
        keep their geometry and are not judged."""
        ox, oy = it.x, it.y
        dx_, dy_ = nx - ox, ny - oy
        grp = group or {}
        saved = {g_.name: (g_.x, g_.y) for g_ in grp.values()}
        try:
            for (an, ap), (bn, bp), bits in incident.get(it.name, []):
                other = bn if an == it.name else an
                if other in grp:
                    continue
                it.x, it.y = ox, oy
                A0, B0 = pts(by[an], ap, bits), pts(by[bn], bp, bits)
                if any(q is None for q in A0 + B0):
                    return 'no_pin:' + other
                it.x, it.y = nx, ny
                A1, B1 = pts(by[an], ap, bits), pts(by[bn], bp, bits)
                L0 = [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(A0, B0)]
                L1 = [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(A1, B1)]
                if all(l1 <= l0 + 1e-6 for l0, l1 in zip(L0, L1)):
                    continue
                if by[an].kind not in STATION_KINDS or by[bn].kind not in STATION_KINDS:
                    if hard_allow > 0 and max(L1) <= ALIGN_HARD_SHORT_UM and all(
                            l1 <= l0 + hard_allow + 1e-6 for l0, l1 in zip(L0, L1)):
                        if PA.bundle(A1, B1)['verdict'] == 'FAIL' and other != hard_tgt[0]:
                            return 'other_hop_fail:' + other
                        continue
                    return 'lengthens_hard_end:' + other  # pair limits of hard ends may be below 500: never lengthen
                if max(L1) > ALIGN_STN_REACH_UM:
                    return 'reach:%s:%.1f' % (other, max(L1))
                if PA.bundle(A1, B1)['verdict'] == 'FAIL':
                    return 'other_hop_fail:' + other
            return False
        finally:
            it.x, it.y = ox, oy
            for n_, (x_, y_) in saved.items():
                by[n_].x, by[n_].y = x_, y_

    def aligned_run(nm, ax):
        """r8 2026-10-14: the stations reachable from `nm` through station-station hops whose two ends stand at the same
        coordinate on the move axis (a straight aligned column / row of the same chain, jog 0): moved rigidly, their
        internal hops keep their geometry.  jog10's d8 (hb_hc_s_hc_t _1 -> _2) and d10 (hb_collective_vm _10 -> _11)
        FAILs sit between two such runs: a single station move lengthened the other side past the 450-um reach."""
        c_ = lambda i_: (i_.x + i_.w / 2, i_.y + i_.h / 2)[ax]
        run, todo = {nm: by[nm]}, [nm]
        while todo:
            cur_ = todo.pop()
            for (an, _ap), (bn, _bp), _bits in incident.get(cur_, []):
                o_ = bn if an == cur_ else an
                if o_ in run or o_ in moved or by[o_].kind not in STATION_KINDS:
                    continue
                if abs(c_(by[o_]) - c_(by[cur_])) > 0.5:
                    continue
                run[o_] = by[o_]
                todo.append(o_)
        return run

    hard_tgt = ['']

    def try_move(members, dx, dy, hard_allow=0.0):
        """members {name: inst} moved rigidly by (dx, dy) (snapped): '' on success, else the refusal reason"""
        boxes = {}
        for n_, it_ in members.items():
            nx, ny = up(it_.x + dx, GX), up(it_.y + dy, GY)
            boxes[n_] = (nx, ny, nx + it_.w, ny + it_.h)
        for n_, bx in boxes.items():
            if bx[0] < 0 or bx[1] < 0 or bx[2] > DIE[0] or bx[3] > DIE[1]:
                return 'outside:' + n_
        for n_, it_ in members.items():
            grp = {k_: v_ for k_, v_ in members.items() if k_ != n_}
            why = worsens_hop(it_, boxes[n_][0], boxes[n_][1], grp, hard_allow)
            if why:
                return why
        for o in m['insts']:
            if o.name in members:
                continue
            for n_, bx in boxes.items():
                if o.x < bx[2] - 1e-6 and bx[0] < o.x + o.w - 1e-6 and o.y < bx[3] - 1e-6 and bx[1] < o.y + o.h - 1e-6:
                    return 'overlap:%s<-%s' % (n_, o.name)
        for n_, it_ in members.items():
            moved[n_] = (round(boxes[n_][0] - it_.x, 3), round(boxes[n_][1] - it_.y, 3), cur_bus[0])
            it_.x, it_.y = boxes[n_][0], boxes[n_][1]
        return ''

    refused = {}
    cur_bus = ['']
    for _ in range(rounds):
        rec = PA.analyze(m['insts'], m['buses'], die_lef_texts(m), names)
        todo = [r for r in rec['flagged'] if r['verdict'] == 'FAIL' and r.get('kind') == 'straight']
        if not todo:
            break
        n0 = len(moved)
        for r in todo:
            fa = r['face'][0]
            ax = 0 if fa in 'NS' else 1
            d = r['at'][2 + ax] - r['at'][ax]
            cur_bus[0] = r['bus']
            why_ = []
            cands = []
            for nm, sg in ((r['drv'], 1.0), (r['load'], -1.0)):
                it = by.get(nm)
                if it is None or it.kind not in STATION_KINDS or nm in moved:
                    why_.append('%s:not_movable' % nm)
                    continue
                cands.append(({nm: it}, sg))
            for nm, sg in (((r['load'], -1.0), (r['drv'], 1.0)) if ALIGN_EXT[0] else ()):   # r8: aligned runs
                it = by.get(nm)
                if it is None or it.kind not in STATION_KINDS or nm in moved:
                    continue
                run = aligned_run(nm, ax)
                if len(run) > 1:
                    cands.append((run, sg))
            tgt = [h_ for h_ in incident.get(r['drv'], []) if h_[0][0] == r['drv'] and h_[1][0] == r['load']]

            def tgt_ok():
                """the flagged bundle and every other lane bundle between the same two instances (r11: a multi-lane
                station carries one bus per lane, e.g. crE2_E0 de0/de3/de4/de5), re-judged here: none a FAIL"""
                if not tgt:
                    return False
                for (an, ap), (bn, bp), bits in tgt:
                    A_, B_ = pts(by[an], ap, bits), pts(by[bn], bp, bits)
                    if any(q is None for q in A_ + B_) or PA.bundle(A_, B_)['verdict'] == 'FAIL':
                        return False
                return True
            ok_ = False
            # r8: the full jog first, then partial moves: a FAIL needs only jog_cut <= 0.6, i.e. the jog shortened
            # until its crossing wires fit the channel (jog10 d10: 2,100 b, 108 um in 86.7 um; <= ~78 um suffices)
            for frac in ((1.0, 0.75, 0.6, 0.45, 0.3) if ALIGN_EXT[0] else (1.0,)):
                for members, sg in cands:
                    dd = up(frac * d, GX if ax == 0 else GY) if d > 0 else -up(-frac * d, GX if ax == 0 else GY)
                    dx, dy = (sg * dd, 0.0) if ax == 0 else (0.0, sg * dd)
                    snap = {n_: (i_.x, i_.y) for n_, i_ in members.items()}
                    mv0 = dict(moved)
                    w_ = try_move(members, dx, dy)
                    if not w_ and (frac == 1.0 or tgt_ok()):
                        ok_ = True
                        break
                    if not w_:          # moved but the bundle is still a FAIL: undo
                        for n_, (x_, y_) in snap.items():
                            by[n_].x, by[n_].y = x_, y_
                        moved.clear()
                        moved.update(mv0)
                        w_ = 'partial_still_fail'
                    why_.append('%s[%d]@%.2f:%s' % (next(iter(members)), len(members), frac, w_))
                if ok_:
                    why_ = []
                    break
            # A banded hard port can need a wider channel rather than a full
            # tangential alignment. Move the terminal station away from the
            # hard face and toward its load pins together. The Manhattan length
            # may stay unchanged even though the normal gap grows. try_move
            # preserves EVERY hard-ended bit length, station reach and legality;
            # tgt_ok rechecks the actual per-bit channel cut (no waiver).
            if why_ and ALIGN_EXT[0] and tgt:
                normal = 1 - ax
                for members, sg in cands:
                    if len(members) != 1:
                        continue
                    nm, it = next(iter(members.items()))
                    # Driver moves away from the load; load moves away from
                    # the driver. Opposing straight faces give this sign.
                    away = (-1.0 if fa in 'EN' else 1.0) * sg
                    other_end = r['load'] if nm == r['drv'] else r['drv']
                    for nstep in range(1, 21):
                        retreat = nstep * (GX if normal == 0 else GY)
                        # r11: the pure retreat first (tangent 0): it only widens the channel; the flagged hop may
                        # lengthen by the retreat (+ one grid of snap) while short (ALIGN_HARD_SHORT_UM).
                        for tangent in (0.0, retreat, 2 * retreat, 0.5 * retreat):
                            delta = [0.0, 0.0]
                            delta[normal] = away * retreat
                            delta[ax] = sg * math.copysign(tangent, d)
                            snap = {n_: (i_.x, i_.y) for n_, i_ in members.items()}
                            mv0 = dict(moved)
                            hard_tgt[0] = other_end if tangent == 0.0 else ''
                            w_ = try_move(members, *delta, hard_allow=(retreat + (GX if normal == 0 else GY))
                                          if tangent == 0.0 else 0.0)
                            hard_tgt[0] = ''
                            if not w_ and tgt_ok():
                                ok_ = True
                                why_ = []
                                break
                            if not w_:
                                for n_, (x_, y_) in snap.items():
                                    by[n_].x, by[n_].y = x_, y_
                                moved.clear()
                                moved.update(mv0)
                        if ok_:
                            break
                    if ok_:
                        break
            if why_:
                refused[r['bus']] = why_
        if len(moved) == n0:
            break
    # r8 2026-10-14 SPREAD ENTRY: a straight FAIL whose driver is a generated hstn station facing a hard load port
    # whose per-bit pins are spread along the face far beyond the station's face (jog10: g_hr_W2_o_d1 -> sp_gather.rW2,
    # 759 b in a 43-um station vs three lane bands over 388 um: jog 255 in a 21-um channel; no position of a compact
    # station can fix it).  The die owns the station (top-down): it becomes a dedicated master spanning the load pins,
    # every dq bit exactly opposite its load pin and di at the same coordinate on the input face, so the fan-out is
    # made on the input side in the wide channel toward the previous station (re-judged: not a FAIL, <= 450 um a bit).
    # Same register stage, no cycle added; RTL is the generated hstn glue (one ot_fwd_link_stage per 512 bits).
    if refused and ALIGN_EXT[0]:
        rec = PA.analyze(m['insts'], m['buses'], die_lef_texts(m), names)
        spread = m.setdefault('spread_stations', {})
        for r in [r for r in rec['flagged'] if r['verdict'] == 'FAIL' and r.get('kind') == 'straight']:
            it = by.get(r['drv'])
            ld = by.get(r['load'])
            if it is None or ld is None or it.kind != 'hstn' or ld.kind in STATION_KINDS:
                continue
            horiz = it.master.startswith('dsfd_hstnh')
            fa = r['face'][0]
            if horiz != (fa in 'EW') or it.orient not in (('R0', 'MY') if horiz else ('R0', 'MX')):
                continue
            hop_out = [(a_, b_, n_) for a_, b_, n_ in incident.get(it.name, []) if a_[0] == it.name and b_[0] == ld.name]
            hop_in = [(a_, b_, n_) for a_, b_, n_ in incident.get(it.name, []) if b_[0] == it.name]
            if len(hop_out) != 1 or len(hop_in) != 1:
                continue
            (_, (ln, lp), bits), ((pn, pp), _, _) = hop_out[0], hop_in[0]
            B = pts(ld, lp, bits)
            A = pts(by[pn], pp, bits)
            if any(q is None for q in A + B):
                continue
            al = 1 if horiz else 0                      # coordinate along the face
            lo, hi = min(q[al] for q in B), max(q[al] for q in B)
            g0 = GY if horiz else GX
            start = math.floor((lo - 0.5) / g0) * g0
            span = math.ceil((hi + 0.5 - start) / g0) * g0
            thick = it.w if horiz else it.h
            toward = 1.0 if fa in 'EN' else -1.0       # the load lies in +axis direction from the driver face
            lc = (ld.x if toward > 0 else ld.x + ld.w) if horiz else (ld.y if toward > 0 else ld.y + ld.h)
            g1 = GX if horiz else GY
            base = (lc - thick - 1.0) if toward > 0 else (lc + 1.0)
            cands = [up(base - toward * g1 * k, g1) if toward > 0 else up(base + g1 * k, g1) for k in range(0, 140)]
            done_ = None
            for c0 in cands:
                bx = (c0, start, c0 + thick, start + span) if horiz else (start, c0, start + span, c0 + thick)
                if bx[0] < 0 or bx[1] < 0 or bx[2] > DIE[0] or bx[3] > DIE[1]:
                    continue
                if any(o is not it and o.x < bx[2] - 1e-6 and bx[0] < o.x + o.w - 1e-6 and o.y < bx[3] - 1e-6
                       and bx[1] < o.y + o.h - 1e-6 for o in m['insts']):
                    continue
                # per-bit pins: dq on the load-facing face, di on the opposite face, same along-coordinate
                fo_ = bx[2] if (horiz and toward > 0) else bx[0] if horiz else (bx[3] if toward > 0 else bx[1])
                fi_ = bx[0] if (horiz and toward > 0) else bx[2] if horiz else (bx[1] if toward > 0 else bx[3])
                ly_ = 'M4' if horiz else 'M5'
                fq_ = ('E' if toward > 0 else 'W') if horiz else ('N' if toward > 0 else 'S')
                fd_ = dict(E='W', W='E', N='S', S='N')[fq_]
                Dq = [((fo_, q[1], fq_, ly_) if horiz else (q[0], fo_, fq_, ly_)) for q in B]
                Di = [((fi_, q[1], fd_, ly_) if horiz else (q[0], fi_, fd_, ly_)) for q in B]
                bi = PA.bundle(A, Di)
                if bi['verdict'] == 'FAIL' or max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(A, Di)) > ALIGN_STN_REACH_UM:
                    continue
                if PA.bundle(Dq, B)['verdict'] == 'FAIL':
                    continue
                done_ = (bx, [q[al] - start for q in B], bi['verdict'])
                break
            if done_ is None:
                # A whole-height spread rectangle can cover empty spaces
                # occupied by other chains. Split only across actual gaps in
                # the hard port's pins; all slices keep the SAME capture edge.
                # Every bit still uses the real hstn register primitive.
                if horiz and it.orient == 'R0' and fa == 'E':
                    from s81 import banded_terminal as BT
                    ins_ = [b_ for b_ in m['buses'] if len(b_[3]) == 2 and b_[3][1] == (it.name, 'di')]
                    outs_ = [b_ for b_ in m['buses'] if len(b_[3]) == 2 and b_[3][0] == (it.name, 'dq')]
                    if len(ins_) == len(outs_) == 1:
                        obs_ = [(o.name,o.x,o.y,o.w,o.h) for o in m['insts']]
                        split_ = BT.propose(A,B,pts(it,'dq',bits),obs_,it.name,it.w,PA,
                                            gx=GX,gy=GY,inset=FACE_PIN_INSET,reach=ALIGN_STN_REACH_UM)
                        if split_:
                            ch_ = BT.apply(sys.modules[__name__],m,it,split_,ins_[0],outs_[0])
                            moved[it.name] = ('band_split',[c_.name for c_ in ch_],r['bus'])
                            refused.pop(r['bus'],None)
                            continue
                refused[r['bus']] = refused.get(r['bus'], []) + ['spread:no_position']
                continue
            bx, loc, vin = done_
            old = it.master
            it.master = '%s_sp%d' % (old, len(spread))
            m['pdir'][it.master] = dict(m['pdir'][old])
            it.x, it.y, it.w, it.h = bx[0], bx[1], bx[2] - bx[0], bx[3] - bx[1]
            spread[it.master] = dict(along=[round(v, 4) for v in loc], horiz=horiz, out_face=(
                ('E' if toward > 0 else 'W') if horiz else ('N' if toward > 0 else 'S')), orient=it.orient)
            moved[it.name] = ('spread', it.master, r['bus'], round(span, 2), vin)
            refused.pop(r['bus'], None)
    m['station_jog_refused'] = refused
    if refused:
        print('OT_ALIGN_JOGS refused %d bundles: %s' % (len(refused), json.dumps(refused)[:1500]), file=sys.stderr)
    m['station_jog_moves'] = moved
    print('OT_ALIGN_JOGS moved %d stations: %s' % (len(moved), json.dumps(moved)[:600]), file=sys.stderr)


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
PIN_ALIGN = False               # --pin-align (s81-die v17): field-frame pins bit-aligned with their abutting peers
HEND_VR_NOBP = False            # --hend-vr-nobp (s81 grpA 10-14): wide (>= 512 b) m2l VR lane ends take NOBP + WCHK
FWD_NEGCAP = False              # --fwd-negcap (s81-die v17): forwarded-lane ENDS capture on the falling forwarded edge
CFIFO_FALL = False              # --cfifo-fall-launch (s81-die r6 2026-10-14, cfifo edge decision (i)): the CLOSED colck cfifo
                                #   captures xd on the RISING xf edge; the x-lane station that taps it forwards a NON-inverted
                                #   copy of its input clock (port fn<j> = fi<j> through two clock inverters) as that cfifo's xf,
                                #   so xd (launched on negedge fi) changes on the FALLING xf edge: a half-cycle source-synchronous
                                #   hop (hold ~ T/2) instead of the rising/rising race (FF -189..-206); the tile is untouched


def _qbank_exact(m, Mx, it, face, ports):
    """--pin-align: the element-side pins of a q bank at the EXACT x of the q element pin of the same bit (both M5, the
    bank 2.4 um from the element face: every bit crosses straight).  The packed 1-track group centred on the bank was
    up to 38.7 um beside its pin and interleaved against the element's field order (v16: 2,560 bundles, jog cut 2.5-3.6)."""
    rq = real_lef(Q_LEF)
    rp = real_ports_r8()[rq['name']]
    e = m['_by']['e' + it.name[2:]]
    assert it.orient == 'R0' and e.orient in ('R0', 'MY'), (it.name, it.orient, e.orient)
    d_ = FACE_PIN_INSET
    y0, y1 = (Mx.h - 0.192 - d_, Mx.h - d_) if face == 'N' else (d_, 0.192 + d_)
    off = round(e.x - it.x, 3)
    for o_ in m['insts']:           # one master: every instance must sit at the same offset from its element
        if o_.master == it.master:
            e2 = m['_by']['e' + o_.name[2:]]
            assert round(e2.x - o_.x, 3) == off and e2.orient == e.orient, ('qbank offset differs', it.name, o_.name)
    for p_, bits in ports:
        nms = rp[p_[2:]]
        assert len(nms) == bits, (it.master, p_, bits, len(nms))
        rects = []
        for i, n in enumerate(nms):
            b = rq['pins'][n][1]
            x = (b[0] + b[2]) / 2
            x = off + (rq['w'] - x if e.orient == 'MY' else x)
            assert 0.2 <= x <= Mx.w - 0.2, (it.master, p_, i, x)
            rects.append((f'{p_}[{i}]', 'M5', (x - 0.012, y0, x + 0.012, y1)))
        Mx.ports[p_] = ('rects', rects)
        Mx.order.append(p_)


_BV_SPAN = {}


def _view_pin_span(m, o, port):
    """(lo, hi, pitch in tracks) of instance o's pins of `port` along its N/S face, master frame: a bound view's LEF pins,
    else the generated relay's centred 1-track group"""
    if o.master in (m.get('bound_views') or ()):
        k_ = (o.master, port)
        if k_ not in _BV_SPAN:
            t = bound_views()[o.master]['text']
            xs = sorted((float(a) + float(c)) / 2 for a, c in re.findall(
                r'PIN ' + re.escape(port) + r'(?:\[\d+\])?\s.*?RECT\s+([\d.]+)\s+[\d.]+\s+([\d.]+)\s+[\d.]+', t, re.S))
            _BV_SPAN[k_] = (xs[0], xs[-1], max(1, round((xs[-1] - xs[0]) / max(1, len(xs) - 1) / 0.048))) if xs else None
        return _BV_SPAN[k_]
    return None


def _abut_relay_fix(m, it, ports, face):
    """--pin-align: {port: (centre, pitch)} for the ports of slot station `it` whose ONE load is a column relay standing
    within 30 um of `face` with its in face toward the station: the station pins take the relay's pin x and pitch (v16:
    sstn_e0c0sinf.xa / xb at 3 tracks beside 1-track relay pins 31-57 um off, 256 bundles FAIL; the relay order xa / xb
    is swapped against the station's port order on that master)."""
    out = {}
    by = m['_by']
    for p_, bits in ports:
        pe = [(i_, q_) for _b, _c, _w, eps_ in m['_nets_of'].get((it.name, p_), []) for i_, q_ in eps_[1:]
              if eps_[0][0] == it.name and i_ in by]
        if len(pe) != 1 or by[pe[0][0]].kind != 'rly' or pe[0][1] != 'i':
            continue
        o = by[pe[0][0]]
        fi = RLY_FACES.get(o.master, ('?', '?'))[0]
        g_ = o.y - (it.y + it.h) if face == 'N' else it.y - (o.y + o.h)
        if fi != dict(N='S', S='N')[face] or not (0.0 <= g_ <= 30.0) or o.orient != 'R0' or it.orient != 'R0':
            continue
        sp = _view_pin_span(m, o, 'i')
        c_, pt_ = ((sp[0] + sp[1]) / 2, sp[2]) if sp else (o.w / 2, 1)
        out[p_] = (o.x + c_ - it.x, pt_)
    return out


_GEN_PROBE = {}


def _gen_face_pin(m, o, port):
    """('face', bits, face, layer, centre, pitch) of generated instance o's `port`, from a probe lay-out of its master
    with the same _faces_r8 rules (None for bound / real masters or an area / rect port)"""
    if o.master in REAL_FILES or o.master in (m.get('bound_views') or ()) or '_pdir' not in m:
        return None
    if o.master not in _GEN_PROBE:
        Px = Q.Master(o.master, o.w, o.h, 7, 'probe')
        _faces_r8(m, Px, o, m['_pdir'].get(o.master, {}))
        _GEN_PROBE[o.master] = Px
    sp = _GEN_PROBE[o.master].ports.get(port)
    return sp if sp and sp[0] == 'face' else None


def _abut_cfifo_fix(m, it, ports):
    """--pin-align: {port: (centre, pitch)} for slot-station inputs whose ONE driver is a generated column FIFO standing
    0-30 um below the station (N face toward it, both R0): the station pins take the FIFO pin x and pitch.  Only when
    every instance of the station master sees the same offset (one master, one pin set)."""
    by = m['_by']
    out = None
    for st_ in [i_ for i_ in m['insts'] if i_.master == it.master]:
        cur = {}
        for p_, bits in ports:
            drv = [eps_[0] for _b, _c, _w, eps_ in m['_nets_of'].get((st_.name, p_), [])
                   if eps_ and eps_[0][0] != st_.name and any(i_ == st_.name for i_, _q in eps_[1:])]
            if len(drv) != 1 or drv[0][0] not in by:
                return {}
            o = by[drv[0][0]]
            g_ = st_.y - (o.y + o.h)
            if o.kind != 'cfifo' or o.orient != 'R0' or st_.orient != 'R0' or not (0.0 <= g_ <= 30.0):
                return {}
            sp = _gen_face_pin(m, o, pslice(drv[0][1])[0])
            if not sp or sp[2] != 'N' or sp[1] != bits:
                return {}
            cur[p_] = (round(o.x + sp[4] - st_.x, 4), sp[5])
        if out is None:
            out = cur
        elif cur != out:
            return {}
    return out or {}


def _lay_fixed(Mx, face, ports, layer, pitch, fixed, gap=0.96):
    """_lay with some ports pinned: `fixed` {port: (centre, pitch)} first, the others in order at `pitch` in the free
    stretches of the face (left to right, stepping over the pinned groups)"""
    p = TRK[layer][1]
    L = Mx.h if face in 'EW' else Mx.w
    sp = lambda b, pt: max(1, b) * p * pt
    resv = []
    for name, b in ports:
        if name in fixed:
            c_, pt_ = fixed[name]
            w_ = sp(b, pt_)
            assert 2 * p <= c_ - w_ / 2 and c_ + w_ / 2 <= L - 2 * p, (Mx.name, name, c_, w_, L)
            assert all(c_ + w_ / 2 + gap <= r0 or c_ - w_ / 2 - gap >= r1 for r0, r1 in resv), (Mx.name, name, 'pinned groups overlap')
            resv.append((c_ - w_ / 2, c_ + w_ / 2))
    rest = [(n_, b) for n_, b in ports if n_ not in fixed]
    tot = sum(sp(b, pitch) for _, b in rest) + gap * max(0, len(rest) - 1)
    pos = max(2 * p + 0.2, (L - tot - sum(r1 - r0 + gap for r0, r1 in resv)) / 2)
    placed = {}
    for name, b in rest:
        w_ = sp(b, pitch)
        for r0, r1 in sorted(resv):
            if pos < r1 + gap and pos + w_ > r0 - gap:
                pos = r1 + gap
        assert pos + w_ <= L - 2 * p, (Mx.name, face, name, 'no room beside the pinned groups')
        placed[name] = (pos + w_ / 2, pitch)
        pos += w_ + gap
    for name, b in ports:           # port order kept (pin_rects / LEF order)
        c_, pt_ = fixed[name] if name in fixed else placed[name]
        Mx.face(name, b, face, layer, c_, pt_)


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


_ASSIGNED_PIN_CACHE = {}


def _assigned_record(master):
    if not ASSIGNED_PINS_DIR:
        return None
    if master not in _ASSIGNED_PIN_CACHE:
        # ':'-separated overlay (S-DIE r11): the first directory holding the master's record wins
        path = next((ROOT / d_ / (master + '.json') for d_ in ASSIGNED_PINS_DIR.split(':')
                     if (ROOT / d_ / (master + '.json')).exists()), ROOT / ASSIGNED_PINS_DIR.split(':')[-1] / (master + '.json'))
        rec = json.loads(path.read_text()) if path.exists() else None
        if rec:
            assert rec['master'] == master and rec['schema'] == 'opentallas.s81.assigned_pins.v1', path
        _ASSIGNED_PIN_CACHE[master] = rec
    return _ASSIGNED_PIN_CACHE[master]


def _assigned_clock_entries(it):
    rec = _assigned_record(it.master)
    return rec.get('clock_entries', {}) if rec else {}


def _assigned_reset_entries(it):
    """Match reset nets to actual assigned ports, including native dual-root leaves.
    Legacy assigned records used rst/rsv. Never invent rst on rst_n masters.
    """
    rec = _assigned_record(it.master)
    if not rec:
        return {}
    if 'reset_entries' in rec:
        return rec['reset_entries']
    default = 'serial' if set(rec.get('clock_entries', {})) == {'serial'} else 'stream'
    out = {}
    for port in ('rst', 'rsv', 'rst_n', 'crst_n', 'srst_n', 'rst_in', 'srs'):
        if port in rec['ports']:
            domain = 'serial' if port in ('rsv', 'srst_n') else 'stream' if port == 'crst_n' else default
            out.setdefault(domain, []).append(port)
    return out


def _assigned_physical_pins(Mx, ports):
    """Apply exact die-owned bit rectangles; missing/extra data bits are defects, never width-clamped.
    Closed bound macros are excluded by write_lefs and still stand at their measured pins.
    """
    rec = _assigned_record(Mx.name)
    if not rec:
        return
    assert all(abs(x - y) <= 0.025 for x, y in zip(rec['outline_um'], (Mx.w, Mx.h))), (Mx.name, 'assigned outline differs')
    for port, spec in rec['ports'].items():
        assert port in ports, (Mx.name, port, 'assigned port absent from die buses')
        assert spec['bits'] == ports[port][1], (Mx.name, port, spec['bits'], ports[port])
        coords = spec.get('per_bit')
        if coords is None:
            at = spec['at']
            cs = [at[0] + i * at[1] for i in range(spec['bits'])] if spec['uniform'] else at
            coords = [[spec['face'], spec['layer'], c, spec['depth']] for c in cs]
        rects = []
        for i, (face, layer, c, depth) in enumerate(coords):
            # Explicit child pins include the M2/M3 access layers of M5
            # leaves. TRK describes die channel allocation (M4 and above),
            # not the technology's complete set of legal pin layers.
            assert layer in ('M2', 'M3', *TRK) and face in 'NSEW', (Mx.name, port, i)
            assert 0.012 <= c <= (Mx.h if face in 'EW' else Mx.w) - 0.012, (Mx.name, port, i, c)
            half_width = .009 if layer in ('M2','M3') else .012
            rect = {'N': (c-half_width, Mx.h-depth, c+half_width, Mx.h), 'S': (c-half_width, 0, c+half_width, depth),
                    'W': (0, c-half_width, depth, c+half_width), 'E': (Mx.w-depth, c-half_width, Mx.w, c+half_width)}[face]
            rects.append((f'{port}[{i}]', layer, rect))
        Mx.ports[port] = ('rects', rects)
        if port not in Mx.order:
            Mx.order.append(port)


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
    m['_laid_all'] = {}
    m['_pdir'] = pdir
    _GEN_PROBE.clear()
    # --peer-pin-pos (s81-die v16): the stations / link ends are laid FIRST (their pin groups do not depend on a slab),
    # so a slab port can stand on its peer's PIN GROUP instead of the peer's outline centre
    order_ = sorted(first.items(), key=lambda kv: kv[1].kind not in PEER_PIN_KINDS) if PEER_PIN_POS else list(first.items())
    for mst, it in order_:
        if mst in REAL_FILES:
            continue
        ports = pdir.get(mst, {})
        Mx = Q.Master(mst, it.w, it.h, 3 if is_glue(mst) or mst in CFG7_MASTERS else 7, f'r8 {it.kind}')
        M[mst] = Mx
        _faces_r8(m, Mx, it, ports)
        _apply_pin_overrides(Mx, it)
        if k == 1:
            _assigned_physical_pins(Mx, ports)
        if PEER_PIN_POS and it.kind in PEER_PIN_KINDS:
            m['_laid_all'][mst] = Mx
        if CK_RULE:
            _ck_rule(Mx)
    if k > 1:
        for name, ports in real_ports_r8().items():
            M[name] = _spread_ports(_real_master_bundled(REAL_FILES[name], k, ports), k)
    return M


def _ck_rule(Mx, min_l=300.0):
    """--ck-rule (s81-gen 2026-10-09, redesign-ds proposal; checker tools/s81_ph/ck_pin_rule.py): a generated master
    whose longer side L >= min_l takes its clock pin(s) on a LONG face within the middle third (|pos - L/2| <= L/6), at
    the free spot nearest the middle (ck at a corner / short face of a long tile cost 600-1,150 ps of insertion)."""
    w, h = Mx.w, Mx.h
    L = max(w, h)
    if L < min_l:
        return
    longf = ('S', 'N') if w >= h else ('W', 'E')
    K = _LAY_K[0]
    span = lambda b: max(1, math.ceil(b / K)) * K * 0.048 + 0.432
    for ckp in [p_ for p_ in Mx.order if p_ in ('ck', 'clk', 'cks', 'ckh')]:
        sp_ = Mx.ports[ckp]
        if sp_[0] != 'face':
            continue
        _, bits, f0, ly0, c0, pt0 = sp_
        if f0 in longf and abs(c0 - L / 2) <= L / 6:
            continue
        best = None
        for f in ((f0,) if f0 in longf else ()) + longf:
            occ = [(v[4] - span(v[1]) / 2, v[4] + span(v[1]) / 2) for q_, v in Mx.ports.items()
                   if q_ != ckp and v[0] == 'face' and v[2] == f]
            ly = 'M5' if f in 'NS' else 'M4'
            for j in range(0, int(L / 6 / 0.432)):
                for c in (L / 2 + j * 0.432, L / 2 - j * 0.432):
                    lo, hi = c - span(bits) / 2, c + span(bits) / 2
                    if all(hi <= a_ or lo >= b_ for a_, b_ in occ):
                        best = (f, ly, c)
                        break
                if best:
                    break
            if best:
                break
        assert best, (Mx.name, ckp, 'no free spot in the middle third of a long face')
        Mx.ports[ckp] = ('face', bits, best[0], best[1], best[2], 1)


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
    if _LAY_K[0] == 1 and BF_HIER == 450.144 and BF_ROUTE_H == 198.72 and it.master in ('dsfd_bf_front', 'dsfd_bf_col'):
        from s81.bf_direct_pins import populate
        populate(sys.modules[__name__], Mx, it.master == 'dsfd_bf_col', ports)
        return
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
        if PIN_ALIGN and _LAY_K[0] == 1:
            _qbank_exact(m, Mx, it, ef, P_(el))
        else:
            _lay(Mx, ef, P_(el), 'M5', gap=0.0)
        _lay(Mx, df, P_(dl), 'M5', gap=0.0)
        _lay(Mx, 'W', P_(['ck', 'rs']), 'M4')
    elif kind == 'rly':
        fi, fo = RLY_FACES[mst]
        _lay(Mx, fi, P_(['i']), 'M4' if fi in 'EW' else 'M5', gap=0.0)
        _lay(Mx, fo, P_(['o']), 'M4' if fo in 'EW' else 'M5', gap=0.0)
        cf_ = [f_ for f_ in 'NSEW' if f_ not in (fi, fo)][0]
        _lay(Mx, cf_, P_(['ck', 'rs']), 'M4' if cf_ in 'EW' else 'M5')
    elif kind == 'hstn' and mst in m.get('spread_stations', {}):
        # r8 spread-entry station (align_station_jogs): di / dq per bit at the load pin's coordinate along the face
        sp_ = m['spread_stations'][mst]
        horiz = sp_['horiz']
        ly_ = 'M4' if horiz else 'M5'
        d_ = 0.192
        for p_, f_ in (('di', 'W' if horiz else 'S'), ('dq', 'E' if horiz else 'N')):
            assert ports[p_][1] == len(sp_['along']), (mst, p_, ports[p_], len(sp_['along']))
            rects = []
            for i, c in enumerate(sp_['along']):
                assert 0.2 <= c <= (Mx.h if horiz else Mx.w) - 0.2, (mst, p_, i, c)
                in_ = FACE_PIN_INSET
                rect = {'N': (c - .012, Mx.h - d_ - in_, c + .012, Mx.h - in_), 'S': (c - .012, in_, c + .012, d_ + in_),
                        'W': (in_, c - .012, d_ + in_, c + .012), 'E': (Mx.w - d_ - in_, c - .012, Mx.w - in_, c + .012)}[f_]
                rects.append((f'{p_}[{i}]', ly_, rect))
            Mx.ports[p_] = ('rects', rects)
            Mx.order.append(p_)
        _lay(Mx, 'N' if horiz else 'W', P_(['ck']), 'M5' if horiz else 'M4')
    elif kind == 'hstn':
        horiz = mst.startswith('dsfd_hstnh')
        _lay(Mx, 'W' if horiz else 'S', P_(['di']), 'M4' if horiz else 'M5', gap=0.0)
        _lay(Mx, 'E' if horiz else 'N', P_(['dq']), 'M4' if horiz else 'M5', gap=0.0)
        _lay(Mx, 'N' if horiz else 'W', P_(['ck']), 'M5' if horiz else 'M4')
    elif kind == 'sstn':
        sl5_ = P_(['xai', 'xbi', 'x2i', 'cci', 'qt', 'so'])
        fs_ = _abut_cfifo_fix(m, it, P_(['xai', 'xbi'])) if PIN_ALIGN and _LAY_K[0] == 1 else {}
        if fs_:
            # s81-die r7 2026-10-14 (jog9 pin_align 261 FAIL, 195 = xa/xb cf<r> -> t<r>_0): with --pq-g the cfifo sits
            # 8.95 um under the slot-0 station (was 250 um), so the station's pitch-3 xai / xbi group (44-85 um) against
            # the cfifo's 1-track xa / xb (71-99 um in the station frame) jogged 27 um in a 9-um channel (cut 0.67).
            # The station is die-generated (top-down pins): xai / xbi take the cfifo's pin x and pitch exactly.
            _lay_fixed(Mx, 'S', sl5_, 'M5', 3, fs_)
        elif XB_RGAP_FIRST and _LAY_K[0] == 1 and 'nf' not in ports:
            # --xb-rgap-first: xai / xbi come from the previous slot's x relays, which stand beside that slot's station
            # E edge: the two groups take the E end of the S face (xai outermost), cci / qt / so W of them
            sl_ = P_(['cci', 'qt', 'so', 'x2i', 'xbi', 'xai'])
            tot_ = sum(b_ * 0.144 for _, b_ in sl_) + 0.96 * (len(sl_) - 1)
            _lay(Mx, 'S', sl_, 'M5', start=Mx.w - 0.6 - tot_, pitch=3)
        else:
            _lay(Mx, 'S', sl5_, 'M5', pitch=3 if _LAY_K[0] == 1 else 2)
        nl_ = P_(['e0', 'c0', 'cc', 'cct0', 'cct1', 'cct2', 'cct3', 'xa', 'xb', 'x2', 'si', 'e1', 'c1'])
        fx_ = _abut_relay_fix(m, it, nl_, 'N') if PIN_ALIGN and _LAY_K[0] == 1 else {}
        if fx_:
            _lay_fixed(Mx, 'N', nl_, 'M5', 3, fx_)
        else:
            _lay(Mx, 'N', nl_, 'M5', pitch=3 if _LAY_K[0] == 1 else 2)
        _lay(Mx, 'W', P_(['ck', 'rs']), 'M4')
        _lay(Mx, 'E', P_(['nf']), 'M4')
    elif kind == 'node':
        la, lb, up_ = mst[10] == 'L', mst[11] == 'L', mst.endswith('u')
        _lay(Mx, 'W', P_([s_ for s_, lf in (('a', la), ('b', lb)) if lf]), 'M4')
        sface = [s_ for s_, lf in (('a', la),) if not lf] + ['fo'] + ([] if up_ else ['o'])
        nface = [s_ for s_, lf in (('b', lb),) if not lf] + ['fi'] + (['o'] if up_ else [])
        # S81-DIE region DRT (m221pq PQ root-row strip): 132 M5 Lef58EolKeepOut between adjacent 1-track node pins
        # (n_rt_* tree words): the N / S faces are laid at 2 tracks under --pq-place
        if PIN_ALIGN:
            # --pin-align: FIXED slots on both faces, so every abutted pair of the node stack (gap 0.312 um) meets bit for
            # bit: child o <-> parent a / b at cA, the fault chain fo (S) <-> fi (N) at cF, a node's own o toward its
            # relay at cB.  The centred per-face packing put each port where the OTHER ports of its face left it:
            # o <-> a 1.06 um, o <-> b 4.70 um, fo <-> fi 3.65-7.30 um off (v16: 3,968 abutted bundles FAIL).
            cA, cF, cB = Mx.w / 2 - 12.0, Mx.w / 2, Mx.w / 2 + 12.0
            pt_ = 2 if PQ_PLACE else 1
            for f_, lst_ in (('S', sface), ('N', nface)):
                for s_, b_ in P_(lst_):
                    c_ = cF if s_ in ('fo', 'fi') else cA if (s_ in ('a', 'b') or mst[10] == 'L') else cB
                    Mx.face(s_, b_, f_, 'M5', c_, pt_)
        else:
            _lay(Mx, 'S', P_(sface), 'M5', pitch=2 if PQ_PLACE else 1)
            _lay(Mx, 'N', P_(nface), 'M5', pitch=2 if PQ_PLACE else 1)
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
        _lay(Mx, 'N', P_(['xa', 'xb', 'x2', 'cc', 'st']), 'M5', start=c0 - 15.0)
        _lay(Mx, 'N', P_(['ri']), 'M5', start=c1 - 2.0)
        _lay(Mx, 'N', P_(['co', 'cr', 'rs']), 'M5', start=c0 + 60.0)
        _lay(Mx, 'W', P_(['ck', 'rst']), 'M4')
    elif kind == 'seq':
        _lay(Mx, 'W', P_([f'q{j}' for j in range(7)] + ['a'] + [f'ce{j}' for j in range(7)]), 'M4', gap=0.0)
        _lay(Mx, 'N', P_(['cfg', 'go_e', 'go_tag', 'ef']), 'M5')
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
            if PIN_ALIGN and K == 1:
                # --pin-align: a port whose peers are all stations stands on the stations' pin group, the other ports of
                # the face around it (v16: hr_E3.o packed first on a face it shares with 11 lane inputs, 110 um beside
                # its first station f_hr_E3_o_1 across a 37.9-um gap: 761 jog wires, cut 0.64, 147.9 um pin to pin
                # against the pair reach of 92.9 um)
                fx_ = {}
                for p1_, b1_ in lst:
                    pe_ = {i_ for _b, _c, _w, eps_ in m['_nets_of'].get((it.name, p1_), []) for i_, _q in eps_
                           if i_ != it.name and i_ in m['_by']}
                    if b1_ >= 64 and pe_ and all(m['_by'][i_].kind in ('hstn', 'stn', 'xstg') for i_ in pe_) and \
                            ports[p1_][0] == 'output':
                        bw_ = b1_ * 0.048
                        c_ = min(max(_peer_pos(m, it, p1_, f), bw_ / 2 + 0.4), L - bw_ / 2 - 0.4)
                        if all(abs(c_ - c2_) >= (bw_ + ports[q_][1] * 0.048) / 2 + 0.3 for q_, (c2_, _p) in fx_.items()):
                            fx_[p1_] = (c_, 1)
                if fx_ and len(fx_) < len(lst):
                    try:
                        _lay_fixed(Mx, f, lst, 'M4' if f in 'EW' else 'M5', 1, fx_, gap=0.144)
                        continue
                    except AssertionError:
                        for q_ in [q_ for q_, _b in lst if q_ in Mx.ports]:      # no room around the pinned port: packed as before
                            del Mx.ports[q_]; Mx.order.remove(q_)
                elif fx_:
                    (p1_, (c_, _p)), = fx_.items()
                    Mx.face(p1_, ports[p1_][1], f, 'M4' if f in 'EW' else 'M5', c_, 1)
                    continue
            _lay(Mx, f, lst, 'M4' if f in 'EW' else 'M5', gap=0.0)
    elif kind == 'bf' and BF_HIER:   # dsfd_bf_front: x stream N, control S, column interfaces W / E (abutted)
        _lay(Mx, 'N', P_(['x0', 'x1', 'xb']), 'M5', pitch=1)     # xb: --bf-x2-static BF16 stream (x2 + x0 / x1 sub-ranges)
        _lay(Mx, 'S', P_(['go', 'cfg', 'st', 'ck', 'rs']), 'M5')
        _lay(Mx, 'W', P_(['c0', 'qy0']), 'M4', gap=0.0)
        _lay(Mx, 'E', P_(['c1', 'qy1']), 'M4', gap=0.0)
    elif kind == 'bfcol':            # dsfd_bf_col: front interface on E (MY east copy faces west), partials + ck S (middle)
        _lay(Mx, 'E', P_(['ci', 'qy']), 'M4', gap=0.0)
        _lay(Mx, 'S', P_(['r', 'ck', 'rs']), 'M5')
    elif kind in ('bf', 'bf_nv'):
        _lay(Mx, 'S', P_(['go', 'cfg', 'ck', 'rs']), 'M5', start=230.0)
        _lay(Mx, 'S', P_(['x0', 'x1', 'xb']), 'M5', start=SSTN_X - 4.32 - 10.0)
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
        _lay(Mx, 'N', P_(['rd', 'rq', 'rk', 'wd', 'hw', 'hc']), 'M5')   # s81-gen: rq / rk / wd (--ctrl-rq), host hw / hc
        _lay(Mx, 'N', P_(['ckh', 'rst']), 'M5', start=60.0)
        # die-gaps 2026-10-08: the stream-side clock entry sits at the face end under the stream peer's (dsfd_svc) clock
        # entry (svc 'ck' is laid toward the clk_stream root at the same end), so the hbm_read interface ctrl -> svc is
        # one clock region; at the west end (60 um) the two entries were 8.4 mm apart in two regions and the plan's
        # inter-region skew bound was 197.2 ps > 150 (m221pq_r3 clock plan).
        east = _peer_pos(m, it, 'cks', 'N') > Mx.w / 2       # the end the svc 'ck' takes (same net, same peer sort)
        _lay(Mx, 'N', P_(['cks']), 'M5', start=(Mx.w - 62.0) if east else 2.0)
        m.setdefault('_laid', {})[Mx.name] = Mx
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
            # --rtl-hub-widths (s81die-1011/ctrl): the wide face-to-face hub ports (>= 2,048 b: gather -> capture lanes,
            # capture -> VM, the VM row slots) are centred on their faces FIRST, so both ends of an abutting pair line
            # up (the pin-relay rule: a die hop over 100 um gets relays, and the 21.6 um abut gap has no room for them)
            lres_ = []
            if LANE_PINS and it.kind == 'hub' and f in 'EW':
                # --lane-pins: ports of a straight VCH lane stand on the lane's die y (both slabs), LANE_PINS-track pitch
                lp_ = m.get('_lane_pin', {})
                for p_ in [q_ for q_ in lst if (it.name, q_) in lp_]:
                    bw = bwf(ports[p_][1]) * LANE_PINS
                    cen_ = lp_[(it.name, p_)] - it.y
                    cen_ = L - cen_ if it.orient in ('MX', 'R180') else cen_
                    cen_ = min(max(cen_, 0.4 + bw / 2), L - 0.4 - bw / 2)
                    Mx.face(p_, ports[p_][1], f, 'M4', cen_, LANE_PINS)
                    lres_.append((cen_ - bw / 2 - 1.0, cen_ + bw / 2 + 1.0))
                    lst = [q_ for q_ in lst if q_ != p_]
            wide = [p_ for p_ in lst if RTL_HUB_WIDTHS and it.kind == 'hub' and ports[p_][1] >= 2048] if it.kind == 'hub' else []
            resv = list(lres_)
            if wide:
                tw_ = sum(bwf(ports[p_][1]) + 2.0 for p_ in wide) - 2.0
                ctr_ = L / 2
                if PEER_SPAN_CENTRE:
                    # s81-die-iter 2026-10-12 (--contract: SU 1,890 grows W of the 1,728 column, VM 1,520): centring
                    # on each OWN face put the abutting pair's wide groups 81 um apart (rs_d 102.8 um > PIN_SEG -> a
                    # 103.7 um pin relay with no room in the 21.6 um abut gap).  Centre the group on the centre of the
                    # die span the face shares with its wide-port peers: the same point at both ends of the pair.
                    by_ = m['_by']
                    pe_ = {i_ for p_ in wide for _b, _c, _w, eps_ in m['_nets_of'].get((it.name, p_), [])
                           for i_, _q in eps_ if i_ != it.name and i_ in by_}
                    if pe_:
                        if f in 'NS':
                            lo_ = max(it.x, min(by_[i_].x for i_ in pe_))
                            hi_ = min(it.x + it.w, max(by_[i_].x + by_[i_].w for i_ in pe_))
                            org_, flip_ = it.x, it.orient in ('MY', 'R180')
                        else:
                            lo_ = max(it.y, min(by_[i_].y for i_ in pe_))
                            hi_ = min(it.y + it.h, max(by_[i_].y + by_[i_].h for i_ in pe_))
                            org_, flip_ = it.y, it.orient in ('MX', 'R180')
                        if hi_ - lo_ >= tw_ + 0.8:
                            ctr_ = (lo_ + hi_) / 2 - org_
                            ctr_ = L - ctr_ if flip_ else ctr_
                c_ = min(max(ctr_ - tw_ / 2, 0.4), L - 0.4 - tw_)
                for r0_, r1_ in sorted(lres_):            # --lane-pins: the centred group steps past the lane ports
                    if c_ < r1_ and c_ + tw_ > r0_:
                        c_ = r1_ + 1.0
                if '_bus_of' not in m:
                    bo_ = {}
                    for bid_, _c, _b, eps_ in m['buses']:
                        for i_, q_ in eps_:
                            bo_.setdefault((i_, pslice(q_)[0]), bid_)
                    m['_bus_of'] = bo_
                # order by the connecting bus (the same key at both ends of an abutting pair -> mirrored order)
                for p_ in sorted(wide, key=lambda q: (m['_bus_of'].get((it.name, q), ''), q)):
                    bw = bwf(ports[p_][1])
                    Mx.face(p_, ports[p_][1], f, 'M4' if f in 'EW' else 'M5', c_ + bw / 2, 1)
                    resv.append((c_ - 1.0, c_ + bw + 1.0))
                    c_ += bw + 2.0
                lst = [p_ for p_ in lst if p_ not in wide]
            if CTRL_SVC_ALIGN and it.kind == 'svc' and f in 'NS':
                # --ctrl-svc-align (s81-die v14): the stack client's controller-facing ports take the EXACT x of the
                # controller bits they connect to (bit for bit, both faces M5), so the ~20k-bit rq / rd interface
                # crosses the abut gap straight on its M5 tracks.  v13 centred each face's ports independently: svc
                # rq / r_data sat 488 um E of ctrl rq / rd and rv 1,025 um off (c3 GRT: 20% of the overflow in the
                # 0.4 mm pinch at x 7.2-7.6 mm, M7-M9)
                for p_, cen_, bw_ in _ctrl_aligned(m, it, Mx, lst, ports, f):
                    Mx.face(p_, ports[p_][1], f, 'M5', cen_, 1)
                    resv.append((cen_ - bw_ / 2 - 1.0, cen_ + bw_ / 2 + 1.0))
                    lst = [q_ for q_ in lst if q_ != p_]
            if PEER_PIN_POS and it.orient == 'R0':
                # --peer-pin-pos: a port whose single peer ABUTS this face (link end / station within 30 um) goes on
                # the peer's pin group FIRST and is reserved; the sequential packing below then steps over it.  v16
                # run 2: two ports of one abutting link end (o and the lane return) wanted the same 25 um, the second
                # was pushed 27.6 um along the face: 515 b jogging in the 6-um gap.
                for p_ in list(lst):
                    pe_ = {i_ for _b, _c, _w, eps_ in m['_nets_of'].get((it.name, p_), []) for i_, _q in eps_
                           if i_ != it.name and i_ in m['_by']}
                    if len(pe_) != 1:
                        continue
                    o_ = m['_by'][next(iter(pe_))]
                    g_ = dict(E=o_.x - (it.x + it.w), W=it.x - (o_.x + o_.w), N=o_.y - (it.y + it.h), S=it.y - (o_.y + o_.h))[f]
                    if not (0.0 <= g_ <= 30.0) or o_.master not in (m.get('_laid_all') or {}):
                        continue
                    bw = bwf(ports[p_][1])
                    c0_ = min(max(_peer_pos(m, it, p_, f) - bw / 2, 0.4), L - 0.4 - bw)
                    if any(c0_ < r1_ and c0_ + bw > r0_ for r0_, r1_ in resv):
                        continue
                    Mx.face(p_, ports[p_][1], f, 'M4' if f in 'EW' else 'M5', c0_ + bw / 2, 1)
                    resv.append((c0_ - 1.0, c0_ + bw + 1.0))
                    lst.remove(p_)
            pos = 0.4                     # band blocks / services: at their peers' positions where they fit
            for p_ in lst:
                bw = bwf(ports[p_][1])
                want = _peer_pos(m, it, p_, f) - bw / 2
                rem = sum(bwf(ports[q][1]) + 2.0 for q in lst[lst.index(p_) + 1:])
                pos = max(pos, min(max(pos, want), L - 0.4 - rem - bw))   # never back onto the previous port (v16 run 3:
                #                                    with reserved ranges ahead the room clamp fell below pos: sp_vm f_wfc on t_wfc)
                for r0_, r1_ in sorted(resv):             # step over the centred wide ports
                    if pos < r1_ and pos + bw > r0_:      # (sorted: one pass in an arbitrary order could step INTO a
                        pos = r1_ + 1.0                   #  range already visited -- v15 dsfd_svc_c hs[1:0] on rk[23:22])
                if pos + bw > L - 0.2:
                    # the reserved ranges fragmented the face: this port takes the free gap nearest its peer instead of
                    # the next position in peer order (dsfd_stage_seq_c E face, 88.5 um: t_st ended at 90.4)
                    occ_, g0_, best_ = sorted(resv), 0.4, None
                    for r0_, r1_ in occ_ + [(L - 0.4, L)]:
                        if r0_ - g0_ >= bw:
                            s_ = min(max(want, g0_), r0_ - bw)
                            if best_ is None or abs(s_ - want) < abs(best_ - want):
                                best_ = s_
                        g0_ = max(g0_, r1_)
                    if best_ is None:
                        raise ValueError(f'{Mx.name} face {f}: no free {bw:.1f} um for port {p_} on {L:.1f} um')
                    Mx.face(p_, ports[p_][1], f, 'M4' if f in 'EW' else 'M5', best_ + bw / 2, 1)
                    resv.append((best_ - 0.2, best_ + bw + 0.2))
                    pos = min(pos, L - 0.4)
                    continue
                Mx.face(p_, ports[p_][1], f, 'M4' if f in 'EW' else 'M5', pos + bw / 2, 1)
                resv.append((pos - 0.2, pos + bw + 0.2))
                pos += bw + 2.0


def _ctrl_aligned(m, it, Mx, lst, ports, f):
    """--ctrl-svc-align: [(port, centre, width)] for the ports of `it` (a stack client) whose single peer is a laid
    controller master: centre chosen so that bit b of the port lands on the controller's pin of the same net bit"""
    by_ = m['_by']
    laid = m.get('_laid', {})
    out = []
    fx_ = lambda o: o.orient in ('MY', 'R180')
    for p_ in lst:
        for _bid, _c, _w, eps_ in m['_nets_of'].get((it.name, p_), []):
            pe_ = [(i_, q_) for i_, q_ in eps_ if i_ != it.name and i_ in by_]
            if len(pe_) != 1 or by_[pe_[0][0]].kind != 'ctrl':
                continue
            ct_ = by_[pe_[0][0]]
            cm_ = laid.get(ct_.master)
            base_, lo_, _hi = pslice(pe_[0][1])
            mine_ = pslice([q_ for i_, q_ in eps_ if i_ == it.name][0])
            sp_ = cm_.ports.get(base_) if cm_ is not None else None
            if sp_ is None or sp_[0] != 'face' or sp_[2] not in 'NS' or fx_(ct_) != fx_(it) or mine_[1] not in (None, 0):
                continue
            _, n_, _f, ly_, c_, pt_ = sp_
            off_, pp_ = TRK[ly_]
            step_ = pp_ * pt_
            st_ = max(c_ - n_ * step_ / 2, 2 * pp_)
            if st_ + n_ * step_ > ct_.w - 2 * pp_:
                st_ = ct_.w - 2 * pp_ - n_ * step_
            first_ = off_ + math.ceil((st_ - off_) / pp_ - 1e-9) * pp_
            x_ = first_ + (lo_ or 0) * step_                       # ctrl master frame, bit lo
            xd_ = ct_.x + (ct_.w - x_ if fx_(ct_) else x_)         # die
            xl_ = (it.x + it.w - xd_) if fx_(it) else (xd_ - it.x)  # client master frame
            nb_ = ports[p_][1]                                      # (both mirrored: bits ascend in both frames)
            out.append((p_, xl_ + nb_ * step_ / 2, nb_ * step_))
            break
    return out


def _pnum(p_):
    mm = re.match(r'^([a-z]+)(\d*)$', p_)
    return (int(mm.group(2)) if mm and mm.group(2) else -1, p_)


PEER_PIN_POS = False            # --peer-pin-pos (s81-die v16)
PEER_PIN_KINDS = ('hend', 'hstn', 'stn')


def _peer_pos(m, it, port, f):
    """peer centroid along face f, in the master frame.  --peer-pin-pos: a peer whose master is already laid (station,
    link end) counts at the centre of ITS pin group of this net, not at its outline centre: v15 run 5 put
    sp_collective.rE0 / rE3 / rW2 27.6 um beside the abutting link end's `o` pins (two ports of one peer stacked at the
    peer centre: 515 b jogging in a 6-um gap, cut 3.27) and sp_wfc.f_lid / sp_gather.f_vm 35-44 um beside their last
    station (0.85-0.87)."""
    by = m['_by']
    la = m.get('_laid_all') or {}
    xs, ys = [], []
    for bid, cls, bits, eps in m['_nets_of'].get((it.name, port), []):
        for inst, p_ in eps:
            if inst != it.name and inst in by:
                o = by[inst]
                px, py = o.x + o.w / 2, o.y + o.h / 2
                sp_ = la[o.master].ports.get(pslice(p_)[0]) if o.master in la else None
                if sp_ and sp_[0] == 'face':
                    c_ = sp_[4]
                    lo_, hi_ = pslice(p_)[1:]
                    if lo_ is not None and hi_ is not None and sp_[1] > (hi_ - lo_ + 1) and sp_[3] in TRK:
                        # the peer's SLICE of this net: fields of one station group keep the station's bit order
                        # (v16 run 2: sp_wfc t_swv / t_swd / t_srv / t_srd all wanted the station centre, were laid in
                        # name order = reversed against di[0:559]; t_swv ended 515 um from its bit)
                        st_ = TRK[sp_[3]][1] * sp_[5]
                        c_ = c_ - sp_[1] * st_ / 2 + (lo_ + hi_ + 1) / 2.0 * st_
                    if sp_[2] in 'EW':
                        py = o.y + (o.h - c_ if o.orient in ('MX', 'R180') else c_)
                    else:
                        px = o.x + (o.w - c_ if o.orient in ('MY', 'R180') else c_)
                xs.append(px)
                ys.append(py)
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
                if f'fn{j}' in ports:   # --cfifo-fall-launch: non-inverted forwarded-clock copy for a rising-capture cfifo
                    body.append(f'    wire fnb{j}; ot_fwd_clk_inv u_fn{j}a (.a(fi{j}[0]), .y(fnb{j})); '
                                f'ot_fwd_clk_inv u_fn{j}b (.a(fnb{j}), .y(fn{j}[0]));')
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
                     '    // Hold pad (s81-die-iter 2026-10-12): i -> ir passes a 120 ps (FF) dont_touch delay chain placed in',
                     '    // this stage (its feeder is the adjacent end block\'s boundary flops); tools/s81/die_sta.py INPUT_PAD.',
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
            if 'x2i' in ports:   # --bf-x2-static: the BF x2 fragment in the SAME station register as x0 / x1 / cc
                body.append(f'    reg [{X2B - 1}:0] r2; always @(posedge ck[0]) r2 <= x2i;')
                body.append('    assign x2 = {r2[%d:5], r2[4] & rs[0], r2[3:1], r2[0] & rs[0]};   // xb_v / go_bf by the column reset' % (X2B - 1))
            body.append('    always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) rc <= 15\'d0; else rc <= cci;')
            body.append('    assign xa = {ra[282] & rs[0], ra[281:0]};   // xs_v qualified by the column reset')
            cp_ = re.search(r'_cp(\d+)(?:t\d)*$', mst)
            if cp_:      # --sstn-ccpad: the lane-equal pad registers on cc, after the station's own cc register
                np_ = int(cp_.group(1))
                body.append(f'    reg [14:0] rcp [0:{np_ - 1}];')
                body.append('    always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) begin : g_cp_rst')
                body.append(f'        integer j_; for (j_ = 0; j_ < {np_}; j_ = j_ + 1) rcp[j_] <= 15\'d0; end')
                body.append(f'    else begin : g_cp integer j_; rcp[0] <= rc; for (j_ = 1; j_ < {np_}; j_ = j_ + 1) rcp[j_] <= rcp[j_ - 1]; end')
                body.append(f'    assign xb = rb;\n    assign cc = rcp[{np_ - 1}];')
                for j_ in range(np_):        # pad taps: cct<j> = cc after the station register and j pad stages
                    if f'cct{j_}' in ports:
                        body.append(f'    assign cct{j_} = ' + ('rc;' if j_ == 0 else f'rcp[{j_ - 1}];'))
            else:
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
        elif mst.startswith('dsfd_rstg_pq'):     # S81-DIE PQ root-row return station (registered, column clock)
            w_ = ports['i'][1]
            body.append(f'    reg [{w_ - 1}:0] r; always @(posedge ck[0]) r <= i;')
            body.append(f'    assign o = {{r[{w_ - 1}:1], r[0] & rs[0]}};')
        elif mst == 'dsfd_rstg':
            body.append('    reg [65:0] r; always @(posedge ck[0]) r <= i;')
            body.append('    assign o = {r[65:1], r[0] & rs[0]};')
        elif mst == 'dsfd_cfifo' and BF_X2_STATIC:
            rk = 'cr[0]' if CFIFO_COLCK else 'ck[0]'
            body += [_sync('rsync', rk, 'rst[0]'),
                     '    // --bf-x2-static (S-BIND 2026-10-15, owner static-cycle rule): column entry = ot_s81_static_column_ingress',
                     '    // (pin capture of the forwarded record on xf, fixed epoch shift from the forwarded reset marker, no',
                     '    // occupancy / ready / credit).  xd = {x2 536 | cc 15 | x1 266 | x0 283 | v | rst_n}: one packed word.',
                     '    assign co = ck;          // column clock-tree root (option C region root)',
                     '    assign rs = rsync;',
                     f'    reg [1:0] sti; always @(posedge {rk}) sti <= st;',
                     f'    wire [{LSW}:0] xw_; wire xflt;',
                     f'    ot_s81_static_column_ingress u_x (.f_ck(xf[0]), .i(xd), .ck({rk}), .rst_n(rsync), .o(xw_), .fault(xflt));',
                     '    wire xv = xw_[0];',
                     '    reg [282:0] xa_r; reg [265:0] xb_r; reg [14:0] cc_r; reg [%d:0] x2_r;' % (X2B - 1),
                     f'    always @(posedge {rk}) begin xa_r <= {{xw_[283] & xv, xw_[282:1]}}; xb_r <= xw_[549:284];',
                     '        cc_r <= {xw_[564:552], xw_[551] & xv, xw_[550] & xv};',
                     f'        x2_r <= {{xw_[{LSW}:570], xw_[569] & xv, xw_[568:566], xw_[565] & xv}}; end',
                     '    assign xa = xa_r; assign xb = xb_r; assign cc = cc_r; assign x2 = x2_r;',
                     '    reg [67:0] rr; reg flt;',
                     f'    always @(posedge {rk} or negedge rsync) if (!rsync) begin rr <= 68\'d0; flt <= 1\'b0; end',
                     '        else begin rr <= {sti[1] | flt, sti[0], ri}; flt <= flt | xflt; end',
                     f'    assign rf = {rk[:2]};          // forwarded with rd (the clock that launches it)',
                     '    assign rd = {rr, rr[0], rsync};   // {status, root word, valid = root o_v, rst_n}']
        elif mst == 'dsfd_cfifo' and CFIFO_V2:
            rk = 'cr[0]' if CFIFO_COLCK else 'ck[0]'       # column-side clock (--cfifo-colck: the column tree's return)
            body += [_sync('rsync', rk, 'rst[0]'),
                     '    // CFIFO_V2 (S81-RERUN fail-fast, cfifo e654bb52a SS -252 / FF -21): every input captured at its pin,',
                     '    // every data output from a flop, the overrun check in the write domain (sticky, synchronised)',
                     '    assign co = ck;          // column clock-tree root (option C region root)',
                     '    assign rs = rsync;',
                     ('    // --fwd-negcap: the lane station launches xd on the RISING edge of xf (it captures on negedge fi and\n'
                      '    // forwards the inverted clock): xd is captured on the FALLING edge = a half-cycle path, as station ->\n'
                      '    // station (posedge capture = the launch instant: full-cycle setup, zero-cycle hold, FF -206 ps)\n'
                      '    reg [565:0] xi; always @(negedge xf[0]) xi <= xd;' if FWD_NEGCAP and not CFIFO_FALL else
                      '    reg [565:0] xi; always @(posedge xf[0]) xi <= xd;'),
                     f'    reg [1:0] sti; always @(posedge {rk}) sti <= st;',
                     '    wire xv, wl, rl, wf, rf_, wr; wire [563:0] xq;',
                     f'    ot_meso_fifo #(.W(564), .ENABLE(1\'b1){MESO_P()}) u_x (.wclk(xf[0]), .wrst_n(xi[0]), .w_v(xi[1]), .w_rdy(wr), '
                     f'.w_d(xi[565:2]), .rclk({rk}), .rrst_n(rsync), .r_v(xv), .r_rdy(1\'b1), .r_d(xq), .w_live(wl), '
                     '.r_live(rl), .w_fault(wf), .r_fault(rf_));',
                     '    reg wov; always @(posedge xf[0]) if (!xi[0]) wov <= 1\'b0; else if (xi[1] & ~wr) wov <= 1\'b1;',
                     f'    reg [1:0] wov_s; always @(posedge {rk}) wov_s <= {{wov_s[0], wov}};',
                     '    // lane stream {x0 283 | x1 266 | cc 15}; xs_v, go and cfg_go qualified by the FIFO valid, registered',
                     '    reg [282:0] xa_r; reg [265:0] xb_r; reg [14:0] cc_r;',
                     f'    always @(posedge {rk}) begin xa_r <= {{xq[282] & xv, xq[281:0]}}; xb_r <= xq[548:283];',
                     '        cc_r <= {xq[563:551], xq[550] & xv, xq[549] & xv}; end',
                     '    assign xa = xa_r; assign xb = xb_r; assign cc = cc_r;',
                     '    reg [67:0] rr; reg flt;',
                     f'    always @(posedge {rk} or negedge rsync) if (!rsync) begin rr <= 68\'d0; flt <= 1\'b0; end',
                     '        else begin rr <= {sti[1] | flt, sti[0] | ~rl, ri}; flt <= flt | wf | rf_ | wov_s[1]; end',
                     f'    assign rf = {rk[:2]};          // forwarded with rd (the clock that launches it)',
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
            if kind == 'l2r' and BF_X2_STATIC and lanes[0] == LSW:
                pw = lanes[0]
                # --bf-x2-static: the PQ core and the x start block share the stream clock (ck = cks = clk_stream): a
                # fixed same-stream pin pipeline (input pin flop, output pin flop), no ratio FIFO / ready.  st reports the
                # two reset releases (observation only; the PQ's xws / xes never gate data, validity or progress).
                body += [_sync('rsl', 'ck[0]', 'rs[0]'), _sync('rss_', 'cks[0]', 'rss[0]'),
                         f'    reg [{pw}:0] i_q; always @(posedge ck[0]) i_q <= i;   // input pin flop',
                         '    assign fo = cks;',
                         f'    reg [{pw + 1}:0] od_q; always @(posedge cks[0]) od_q <= {{i_q[{pw}:1], i_q[0] & rsl, rss_}};   // output pin flop',
                         "    reg [2:0] st_q; always @(posedge ck[0]) st_q <= {1'b0, rss_, rsl};",
                         '    assign od = od_q;', '    assign st = st_q;']
            elif kind == 'l2r':
                pw = lanes[0]
                body += [_sync('rsl', 'ck[0]', 'rs[0]'), _sync('rss_', 'cks[0]', 'rss[0]'),
                         '    wire wr, wl, rv, rl;', f'    wire [{pw - 1}:0] rd_;',
                         f'    ot_ratio_cdc_fifo #(.W({pw})) u_c (.wclk(ck[0]), .wrst_n(rsl), .w_v(i[0]), .w_rdy(wr), '
                         f'.w_d(i[{pw}:1]), .rclk(cks[0]), .rrst_n(rss_), .r_v(rv), .r_rdy(1\'b1), .r_d(rd_), '
                         '.w_live(wl), .r_live(rl));',
                         '    assign fo = cks;', '    assign od = {rd_, rv, rss_};', "    assign st = {1'b0, wl, wr};"]
                if HEND_PINREG:
                    # REDESIGN-S81 2026-10-08 (hx_W TT -130 rp->od read mux to the pin, -32 r_st_w->st, -21 i->mem):
                    # a flop at every pin -- i captured on ck before the FIFO (+1 ck cycle), od / st launched from
                    # flops (+1 cks cycle on od); same stream, no protocol change
                    body[-6:] = ['    wire wr, wl, rv, rl;', f'    wire [{pw - 1}:0] rd_;',
                                 f'    reg [{pw}:0] i_q; always @(posedge ck[0]) i_q <= i;   // input pin flop',
                                 f'    ot_ratio_cdc_fifo #(.W({pw})) u_c (.wclk(ck[0]), .wrst_n(rsl), .w_v(i_q[0]), .w_rdy(wr), '
                                 f'.w_d(i_q[{pw}:1]), .rclk(cks[0]), .rrst_n(rss_), .r_v(rv), .r_rdy(1\'b1), .r_d(rd_), '
                                 '.w_live(wl), .r_live(rl));',
                                 '    assign fo = cks;',
                                 f'    reg [{pw + 1}:0] od_q; always @(posedge cks[0]) od_q <= {{rd_, rv, rss_}};   // output pin flop',
                                 "    reg [2:0] st_q; always @(posedge ck[0]) st_q <= {1'b0, wl, wr};   // output pin flop",
                                 '    assign od = od_q;', '    assign st = st_q;']
            else:
                body.append(_sync('rsl', 'ck[0]', 'rs[0]'))
                base, lv, fl = 0, [], []
                for j, pw in enumerate(lanes):
                    vr = fmt == 'vr'
                    dn_ = f'di{j}'
                    if FWD_NEGCAP:
                        # the lane's last station launches di on the RISING edge of fi (negedge capture + inverted
                        # forward): a pin register on the FALLING edge makes the end a half-cycle hop like every station;
                        # the FIFO write (posedge fi) then takes it half a cycle later = the same write edge as before
                        dw_ = pw + 2 if vr else pw
                        body.append(f'    reg [{dw_ - 1}:0] dq{j}; always @(negedge fi{j}[0]) dq{j} <= di{j};   // pin register, falling forwarded edge')
                        dn_ = f'dq{j}'
                    if vr:
                        wr, wv, wd = f'{dn_}[0]', f'{dn_}[1]', f'{dn_}[{pw + 1}:2]'
                    else:
                        body.append(_sync(f'wrs{j}', f'fi{j}[0]', 'rs[0]'))
                        wr, wv, wd = f'wrs{j}', "1'b1", f'{dn_}[{pw - 1}:0]'
                    body.append(f'    wire rv{j}, rl{j}, wf{j}, rf{j}; wire [{pw - 1}:0] rq{j};')
                    if kind == 'm2l':
                        # --hend-vr-nobp (s81 grpA 2026-10-14, hco/hix/hqe_SW TT -91.65/-53.85 + GRT congestion): a wide VR
                        # lane end has r_rdy tied 1, so the 16 x W receive buffer is dead logic the netlist cannot prove
                        # dead (cnt -> empty -> o_d mux) -> NOBP; and the negedge pin register's valid / reset bits fan
                        # out to all DEPTH x W ring write enables in HALF a cycle -> WCHK (64-bit chunks written every
                        # cycle from a registered one-hot slot copy; validity stays in the slot v bits). Same words,
                        # same cycles (both proven in ot_meso_fifo, used by the HBM stations).
                        xp = ", .NOBP(1'b1), .WCHK(1'b1)" if (HEND_VR_NOBP and vr and pw >= 512 and pw % 64 == 0) else ''
                        body.append(f'    ot_meso_fifo #(.W({pw}), .ENABLE(1\'b1){MESO_P()}{xp}) u_{j} (.wclk(fi{j}[0]), .wrst_n({wr}), '
                                    f'.w_v({wv}), .w_rdy(), .w_d({wd}), .rclk(ck[0]), .rrst_n(rsl), .r_v(rv{j}), '
                                    f'.r_rdy(1\'b1), .r_d(rq{j}), .w_live(), .r_live(rl{j}), .w_fault(wf{j}), .r_fault(rf{j}));')
                    else:
                        body.append(f'    assign wf{j} = 1\'b0; assign rf{j} = 1\'b0;')
                        # --hend-vr-nobp (s81 grpA r3 2026-10-14, hcol / hsel TT -25.78: negedge pin register -> w_fire ->
                        # DEPTH x W ratio-FIFO write enables in half a cycle): wide VR r2l ends write the FIFO always (WALL)
                        wa = ", .WALL(1'b1)" if (HEND_VR_NOBP and vr and pw >= 512) else ''
                        body.append(f'    ot_ratio_cdc_fifo #(.W({pw}){wa}) u_{j} (.wclk(fi{j}[0]), .wrst_n({wr}), .w_v({wv}), '
                                    f'.w_rdy(), .w_d({wd}), .rclk(ck[0]), .rrst_n(rsl), .r_v(rv{j}), .r_rdy(1\'b1), '
                                    f'.r_d(rq{j}), .w_live(), .r_live(rl{j}));')
                    pr = HEND_PINREG and kind == 'r2l'
                    body.append(f'    assign {"o_d" if pr else "o"}[{base + pw}:{base}] = {{rq{j}, rv{j}}};')
                    base += pw + 1
                    lv.append(f'rl{j}')
                    fl += [f'wf{j}', f'rf{j}']
                if HEND_PINREG and kind == 'r2l':
                    # REDESIGN-S81 2026-10-08 (hcol TT -15.4 / hsel -10.3: rp -> sh[rp] read mux -> o pin): every
                    # output from a flop (+1 ck cycle, same stream)
                    body.insert(body.index(next(b for b in body if 'wire rv0' in b)), f'    wire [{base + 1}:0] o_d;')
                    body.append(f'    assign o_d[{base + 1}:{base}] = {{{" | ".join(fl)}, {" & ".join(lv)}}};   // {{fault, live}}')
                    body.append(f'    reg [{base + 1}:0] o_q; always @(posedge ck[0]) o_q <= o_d;   // output pin flop')
                    body.append('    assign o = o_q;')
                else:
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
    hf += (1 if FWD_NEGCAP else 2) if CFIFO_V2 else 0   # cfifo v2: xd pin register + output register (--fwd-negcap: the pin
    #                                                     register is on the falling edge, the FIFO writes half a cycle later)
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
        ctrl_model=m.get('ctrl_model'), ctrl_binding_shell_sha256=m.get('ctrl_binding_shell_sha256'),
        slot=dict(elem_frame_h_um=ELEM_FRAME_H, q_elem_frame_h_um=Q_ELEM_FRAME_H, frame_h_um=g['frame_h'], slot_h_um=g['slot_h'], slots_per_column=g['slots'],
                  capacity=capacity_report()),
        instances=dict(kinds), area_mm2_by_kind={k: round(v, 3) for k, v in area.items()},
        placed_footprint_mm2=round(sum(area.values()), 2),
        utilisation=dict(placed_over_die=round(sum(area.values()) / (DIE[0] * DIE[1] / 1e6), 4),
                         field_frames_mm2=round(sum(COL_W8 * f.get('h', g['frame_h']) for f in fr.values()) / 1e6, 2)),
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
        column_relays=m.get('col_relays', {}), go_retap=m.get('go_retap'),
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
    ap.add_argument('--canonical-layout', help='Source-pinned full2417 capacity JSON; exact519 BF IDs and128 root bounds, irregular local streets/RSC transit and per-root actual flight calendar')
    ap.add_argument('--die', default='layer', choices=['layer', 'layer1', 'layer1e', 'head'])
    ap.add_argument('--ctrl-rq', action='store_true', help='s81-gen 2026-10-09: every stack controller\'s request '
                    'side bound (dsfd_ctrl rq 10,912 / rk 32 / wd 32 to its client: the svc, or the Engram service on '
                    'the layer1e SE stack); the r3 / r4 dies left these real controller ports without a die net. '
                    'Implied by --die layer1e; default off')
    ap.add_argument('--gen', default='r7', choices=['r7', 'r8'], help='r7: the 21fcf6469 die (default); r8: wired die')
    ap.add_argument('--head-dies', type=int, default=12, help='head die: dies sharing the head content (default 12)')
    ap.add_argument('--rev', default='r8', choices=['r8', 'r9'], help='r8 sub-revision (r9: S81-RERUN hub-bus stations)')
    ap.add_argument('--elem-h', type=float, help='r8: element frame height in its slot (default 157.68)')
    ap.add_argument('--q-elem-h', type=float, help='r8 layer/layer1: independent q frame height; --elem-h remains BF height; requires --bf-per-region')
    ap.add_argument('--pairs', type=int, help='r8: pairs (elements) per die (default: the decision value)')
    ap.add_argument('--bf-pair-ranges', help='r8 head: explicit BF-double IDs as comma-separated half-open ranges; e.g. 0:338 for the typed 696-slot inventory')
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
    ap.add_argument('--hub-south-shift', type=float, default=0.0, help='v18 geometry trial: move W-column SU and centre stack south by UM; legality and hop gates remain binding')
    ap.add_argument('--rly-real-dims', action='store_true', help='reserve the native wide relay envelope before placement; final closed view binding takes the exact outline, no master aliases')
    ap.add_argument('--assigned-pins-dir', help='consume die-assigned pin JSON files for parent data and per-child clock entries')
    ap.add_argument('--hub-column-width', type=float, help='r9: each hub column width in um; spends existing die horizontal slack; default unchanged')
    ap.add_argument('--su-mm2', type=float, help='r9: SU total reservation area in mm2, split north/south; requires sizing record; default unchanged')
    ap.add_argument('--vm-face-mm2', type=float, help='r9: minimum VM slab area in mm2 on every die (spreads its pin '
                    'face; layer die value 2.6599; default off)')
    ap.add_argument('--cfifo-colck', action='store_true', help='with --cfifo-v2: the cfifo column side clocked from its '
                    'own column tree (pin cr); fixes the FF xa/xb -> first relay hold class (sta_v6)')
    ap.add_argument('--pin-need', action='store_true', help='column relay need / path to q element ports measured at the '
                    'real LEF pin centroid (not the element centre)')
    ap.add_argument('--sstn-ccpad', action='store_true', help='--lane-equal cc padding as extra cc registers in the '
                    'driving slot station (no floating pad relay)')
    ap.add_argument('--rt-strip', type=float, default=0.0, help='return-tree relays may use a UM-high strip above their '
                    'column frame (the top-edge return leaves run there; s81-die-iter 10-12)')
    ap.add_argument('--relay-progress', action='store_true', help='column relays only on sites that advance toward the next '
                    'chain point (no far-side relay); a packed frame without such a site fails loudly')
    ap.add_argument('--nxt-reach', action='store_true', help='relay placement honours the reach to the next chain point '
                    '(r3 GRT: hop relays 776-906 um from their load, TT -244 on ck_col relay paths)')
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
    ap.add_argument('--face-pin-inset', action='store_true', help='die-gaps 2026-10-08: generated face pins start '
                    '0.048 um inside the outline (abutted node stacks put different-net M5 pins tip to tip under the '
                    'EOL keepout); default off for reproducing r3/r4')
    ap.add_argument('--host', action='store_true', help='s81-dies / ingest RQ-ING-1: dsfd_host slab (0.10 mm2) beside '
                    'the collective (HOST class demuxed from the board SerDes) wired to every stack controller; default off')
    ap.add_argument('--hop-r-cc', type=float, help='s81-gen 2026-10-09: common-clock hop reach in um (default 410; '
                    '= OT_S81_HOP_R_CC, which die_sta kit / extract_die re-runs lose; 500 <= the 504 um SS wire reach: '
                    'cont-takeover r4e passes the r4c rt_0_8a_y1 trap)')
    ap.add_argument('--q-x1b', action='store_true', help='s81-gen 2026-10-10 (coordinator option B): the q element x1 '
                    'port on its S-face east end with its own bank, right-lane elements mirrored MY; needs the x1b q view '
                    '(OT_S81_Q_LEF; stub physical/s81_die_views/q_elem_qs5f_x1b_stub); default off')
    ap.add_argument('--cfg-rgap', type=float, default=0.0, help='ds-1010 2026-10-10: reserved relay gap (um, e.g. 21.6) '
                    'in every right-lane cfg ROM row between ROM --cfg-rgap-at - 1 and --cfg-rgap-at (x1b residual '
                    'rt_<f>_8b return-leaf SS reach class); default 0 = off')
    ap.add_argument('--xb-rgap', type=float, default=0.0, help='ds-1010/s81die 2026-10-10: reserved x-lane relay site (um, '
                    'e.g. 25.92) in every right-lane cfg ROM row between the sequencer and ROM 0, for xa_/xb_/cc_ relays '
                    'only (efs q: x1 in the element middle, the slot station had no relay box toward its banks); default 0')
    ap.add_argument('--cfg-rgap-at', type=int, default=4, help='ROM index the --cfg-rgap gap precedes (default 4)')
    ap.add_argument('--lane-equal', action='store_true', help='ds-1010 lat-audit 2026-10-10: column relays on the x0 / x1 / '
                    'cc lanes of one slot segment (xa_/xb_/cc_<f>_<k>) take the MAX relay count of the three, so the three '
                    'lanes of a transaction stay the same age (tools/s81/field_alignment.py: x1b+rgap had 256 x0/x1 and '
                    '128 go-early mismatches); default off')
    ap.add_argument('--ck-rule', action='store_true', help='s81-gen 2026-10-09 (redesign-ds clock-pin rule): every generated '
                    'master with a side >= 300 um takes its clock pin on a long face in the middle third; default off')
    ap.add_argument('--coll-split3', action='store_true', help='s81-gen 2026-10-09 (redesign-ds): collective slab outline from '
                    'physical/s81_ph_views/collective/composition_split3.json (three-tile core column); default off')
    ap.add_argument('--coll-mtp-lane', action='store_true', help='mtp-colllane-1011: head die collective with the dedicated MTP '
                    'lane row (composition_split3cr_mtpl.json, lane W4 = lk_W4, RTL OT_S81PH_COLL_MTPL); needs --coll-split3-cr, '
                    '--mtp-seq, --mtp-links >= 1; default off')
    ap.add_argument('--coll-p2-lane', action='store_true', help='mtp-colllane-1011: draft die A collective with the P2 lanes '
                    '(composition_split3cr_p2l.json, W4 primary / E4 die B, RTL OT_S81PH_COLL_P2L); needs --coll-split3-cr '
                    'and --draft A; default off')
    ap.add_argument('--coll-split3-cr', action='store_true', help='opt-in planning candidate: use composition_split3cr.json with credit seams and LCR lane tiles; implies --coll-split3, all four routed masters required for adoption')
    ap.add_argument('--bf-hier', type=float, choices=[520.128, 600.264], help='s81-gen 2026-10-09 (bf-arch): BF pair as '
                    'dsfd_bf_col | dsfd_bf_front | dsfd_bf_col (MY), 190.08 um tall; frames and die widen; default off')
    ap.add_argument('--bf-hier-height', type=float, choices=[198.72, 220.32, 241.92], default=220.32, help='model-priced compact hardened BF heights, default 220.32 (198.72 = bfh_compact199: frame 207.36); requires --bf-hier-compact')
    ap.add_argument('--bf-hier-compact', action='store_true', help='(bf-hier, claude/bf-compact-1011; OWNER 2026-10-10 BF of record) '
                    'column 450.144 / front 100.224, height 220.32: the pair (1,000.512 um) fits the original lane zone, 1,792 '
                    'pairs / 128 regions kept; requires a BF frame of 228.96 or taller (--elem-h); default off')
    ap.add_argument('--suhc-1011', action='store_true', help='ds-1010/s81die 2026-10-11 (s81-suhc-1011, main-approved): SU / HC '
                    'slabs on the 1.2 GHz stream domain; direct collective -> HC y (4,096 b a half), HC -> VM 2,048 b, capture '
                    '-> SU g/u (512 b a half, planning width); h resident in HC; default off')
    ap.add_argument('--su-e', type=float, default=0.0, help='ds-1010/s81die 2026-10-11: su_n of MM2 in the E column above hc_n, '
                    'su_s = the rest at the W column floor under the centre stack (room for the --vm-slab VM); default 0 = off')
    ap.add_argument('--hrow-tx', action='store_true', help='ds-1010/s81die 2026-10-11: stage die of layer 37/38/39: the '
                    'hidden-row sender dsfd_mtp_hrow_tx (hc_n -> MTP lane, header from the WFC kit); needs --suhc-1011 --su-e')
    ap.add_argument('--coll-slab-h', type=float, help='s81die-1011 (hier contract v1, 2026-10-11): collective slab = full hub '
                    'column width x H um (hierarchical collective: 8 lane tiles stacked on the W face, core column 1,360.8 um '
                    'with cb 972.4 x 423.4 / ce / ct; e.g. 2721.6)')
    ap.add_argument('--vm-slab', help='ds-1010/s81die 2026-10-11 (s81-vm-1011): VM slab outline W,H in um (e.g. 1520,2420); '
                    'default: the HUB_MM2 area at the column width')
    ap.add_argument('--ecol-slabs', help='ds-1010/s81die 2026-10-10: comma list of W hub-column centre slabs (wfc, host, '
                    'capture) moved to a sub-column of the E (HC) column beside the HC halves, stacked up from the crossing '
                    'corridor (the W column overflowed with --coll-split3-cr + --wfc-kit); default none')
    ap.add_argument('--ecol-w', type=float, default=518.4, help='--ecol-slabs sub-column width (um, default 518.4)')
    ap.add_argument('--tier-cols', help='ds-1010 2026-10-10 (owner: hierarchical full-rate BF AT THE RETICLE): comma list of '
                    'the TIERS frame columns per tier and half (default 10,11,11,11,11,10 = 128 frames); with --bf-hier the '
                    'die stays 33 x 26 mm (no widening) and the columns must fit it (e.g. 8,8,8,8,8,8 = 96 frames at col600); '
                    'frames (= PQ roots) = 2 x the sum')
    ap.add_argument('--ctrl-svc-align', action='store_true', help='s81-die v14: the stack client (dsfd_svc_c) '
                    'controller-facing pins take the x of the controller bits they connect to (straight M5 abut crossing)')
    ap.add_argument('--hop-gate', type=float, help='s81-die v14: real mode hard gate: every data bit pin-to-pin '
                    'hop <= UM (tools/s81/die_hop_gate.py; hop_gate.json in --work)')
    ap.add_argument('--hop-extra', type=int, default=0, help='s81-gen 2026-10-09: a hop whose stations cannot all place '
                    'within both reaches may take up to N extra stations (+1 cycle each on that hop; dry-run chosen); default 0')
    ap.add_argument('--fwd-iface', action='store_true', help='s81-gen 2026-10-09: host-write (with --ctrl-rq) and layer1e '
                    'Engram interfaces as forwarded lanes with meso / ratio-CDC end blocks (the common-clock hop-fix '
                    'chains crossed 6-8 clock regions: 322 ps inter-region skew); default off')
    ap.add_argument('--path-pick', action='store_true', help='s81-gen 2026-10-09: a die-level hop runs on the L or '
                    'corridor Z path with the largest corridor share (station count from that path); = OT_S81_PATH_PICK=1')
    ap.add_argument('--operand-path-pick', action='store_true', help='Source candidate: column xa/xb/cc relays try both L routes with actual trial occupancy; register counts unchanged. Full per-bit reach/cut gates remain required.')
    ap.add_argument('--relay-tt-reach', type=float, help='s81-gen 2026-10-09: a relay with no legal box inside the SS '
                    'reach takes the nearest box within this TT reach in um (option B: TT setup; 600 = 717 ps of TT wire); '
                    'listed in hop_fix.tt_reach_relays / col_relays.tt_reach_relays; default off')
    ap.add_argument('--frame-out-relay', action='store_true', help='s81-dies: a frame relay with no spot in its full '
                    'frame takes the nearest legal spot within reach outside it, as --pq-place does (head die); default off')
    ap.add_argument('--pq-place', action='store_true', help='S81-DIE (2026-10-07): production PQ placement on the '
                    'mixed layer die: a 241.92 um root row in the first TIERS tier channels (one ret_root_r128 a '
                    'region, 132.192 x 211.68, between two 8.64 um return stations in the 142.56 um return strip) and '
                    'the PQ core in a 449.28 um x hub-column slot after the VM (with its 3 stream / phase ROMs)')
    ap.add_argument('--wfc-hard', action=argparse.BooleanOptionalAction, default=None,
                    help='MTP-DIE: bound, wired WFC slab (dsfd_wfc) on every layer-class STAGE die (layer and layer1; '
                    'not draft dies) instead of the scan-die-only soft reservation; default WFC_HARD_DEFAULT (off '
                    'until the SOURCE HARD partner closes)')
    ap.add_argument('--seedl', action='store_true', help='mtp-dsbind 2026-10-10: DSpark primary die (--draft P): '
                    'dsfd_mtp_seed_launch slab (seed descriptor from the collective MTP lane -> seed program); needs '
                    '--coll-mtp-far primary')
    ap.add_argument('--hrow-src', type=int, choices=[0, 1, 2], help='mtp-dsbind 2026-10-11: stage die of layer 37 + P: '
                    'the hidden-row source dsfd_mtp_hrow_src (t_hep from the WFC kit, VM row reads, one hidden lane)')
    ap.add_argument('--hrow', action='store_true', help='mtp-dsbind 2026-10-10: with --seedl, the main-hidden row store '
                    'dsfd_mtp_hrow (3 part links from the MTP part lanes; the seed client reads it)')
    ap.add_argument('--coll-mtp-far', choices=['s0', 'primary'], help='mtp-wfc 2026-10-10: S0 die collective with the MTP lane '
                    '(far end of the head lane): token return -> WFC kit link-in (TOKIN), accept word -> host')
    ap.add_argument('--mtp-ep', action='store_true', help='mtp-wfc 2026-10-10: head-die RTT-sized sequencer partner ends')
    ap.add_argument('--p2-lnk', action='store_true', help='mtp-wfc 2026-10-10: draft-A P2 slab = core + dsfd_p2_lnk')
    ap.add_argument('--mtp-seq-rtt', action='store_true', help='mtp-wfc 2026-10-10: head sequencer slab master '
                    'dsfd_mtp_seq_rtt (native RTT successor, same ports)')
    ap.add_argument('--stage-seq', action='store_true', help='main decision A: with --wfc-kit, a dsfd_stage_seq slab carries '
                    'the kit start / done (no capture placeholder pins); engine cmd / dn bound by the adapter work')
    ap.add_argument('--wfc-crp', action='store_true', help='main 10-11: with --wfc-kit, the WFC slab master is dsfd_wfc_cr2 '
                    '(dsfd_wfc_crp credit-boundary tile at the die edge + the kit)')
    ap.add_argument('--wfc-kit', action='store_true',
                    help='mtp-wfc 2026-10-10: with --wfc-hard, place the WFC kit closed elements (tokpipe core, lnk, '
                    'vmx, tok on the source die) as their own masters in the WFC slab, wired at exact ports')
    ap.add_argument('--mtp-seq', action=argparse.BooleanOptionalAction, default=None,
                    help='MTP-DIE: head die ot_dsrom_mtp_seq slab (dsfd_mtp_seq) between capture and collective, '
                    'wired; default MTP_SEQ_DEFAULT (ON since mtp-lead 2026-10-09: dsfd_mtp_seq CLOSED c67a71fe5); '
                    '--no-mtp-seq reproduces the pre-MTP head dies')
    ap.add_argument('--draft', choices=['A', 'B', 'P'], help='MD-2 P2 draft die (40 dies = 5 row packages x 4 ranks x '
                    'A/B): the layer1 recipe with the draft ROM image of side A or B; P = the DSpark PRIMARY die (4 = '
                    'TP4; mtp-dsbind 2026-10-10: non-expert mtp.0..2 + seed on the L0 run rule, '
                    'tools/dsrom_s81_mtp_binding.py; takes --mtp-links N draft fan-out SerDes) '
                    '(tools/dsrom_mtp_draft_images.py); side A also carries the P2 selected-path transport slab '
                    '(dsfd_p2 = ot_mtp_p2_prefix_path) between capture and collective; no WFC (not a pipeline stage)')
    ap.add_argument('--ctrl-slab', action='store_true', help='S81 native stage controller slab beside collective; requires complete --ctrl-bindings; default off')
    ap.add_argument('--ctrl-role', choices=['layer', 'source', 'head'], default='layer')
    ap.add_argument('--contract', help='s81-die-iter 2026-10-12: hier contract JSON (repo path): SU / HC / VM / centre slab outlines')
    ap.add_argument('--view-binding', help='S81 DIE 2026-10-13: by-name real view table (tools/s81/view_binding.py; repo path or '
                    'absolute); default OT_S81_VIEW_BINDING or ' + VIEW_BINDING_DEFAULT + "; 'none' binds nothing")
    ap.add_argument('--suhc-v2', action='store_true', help='s81die-1011: su_hc contract v2 (one SU in su_s, one HC in hc_s, VM '
                    'row slots, collective y 8,192 to HC); needs --suhc-1011 --ctrl-adapters')
    ap.add_argument('--suhc-v2-hc-north', action='store_true', help='s81die-1011: with --suhc-v2, the HC in the slot above '
                    'the HC corridor (facing the VM rows of order A) instead of the floor slot')
    ap.add_argument('--hop-r-hub', type=float, default=0.0, help='s81-die v16: hop-fix planner reach (um) of the hub-bus '
                    'bridges; default = --hop-r-cc')
    ap.add_argument('--xb-rgap-first', action='store_true', help='s81-die v17: the --xb-rgap relay site stands beside the slot '
                    'station (station | site | sequencer | ROMs) and the station takes xai / xbi at the E end of its S face')
    ap.add_argument('--hop-pair', type=float, default=0.0, help='s81-die v18: hop-fix plans every common-clock hop against its '
                    'real pair limit (pair_check, the gate\'s limit) minus UM of pin-spread margin; 0 = flat --hop-r-cc only')
    ap.add_argument('--hop-iter', type=int, default=0, help='s81-die v18: re-plan the hop fix on the built die up to N times '
                    '(hops the pass-2 build created over their limit get their stage); 0 = one plan (unchanged)')
    ap.add_argument('--pdn-field-cov', type=float, default=0.0, help='r5 10-14 IR release gate: per-net die M8/M9 strap '
                    'coverage over the field / channels (default COV field 0.0439); pitch = bump pitch / odd n (bump-aligned)')
    ap.add_argument('--hc-rtl-widths', action='store_true', help='r5 10-14 (F9): hc_s <-> hc_t per-column crossings from the '
                    'RTL TFW / TRW (3056 / 2164 at NG 256), hc_t takes no die reset (in-band)')
    ap.add_argument('--align-jogs', action='store_true', help='r5 10-14: a station facing its peer straight across moves along '
                    'the face axis by the bundle jog when the box is free (pin_align FAIL: jog spills past the channel)')
    ap.add_argument('--split-far-pins', action='store_true', help='r5 10-14: a hub local chain (end block -> slab) whose '
                    'die-assigned target pins split into a run and a far trailing group (gather rW*/rE* trunk status '
                    '{fault, live} -> control strip) routes the trailing bits as their own staged die path')
    ap.add_argument('--x-site-pair', action='store_true', help='s81-die v18 frame-template relay-site repair: two owned relay '
                    'sites in the --xb-rgap gap E of every slot station, lower = xa_<r>_<s+1>, upper = xb_<r>_<s+1> (the lanes '
                    'that station drives); needs --xb-rgap-first')
    ap.add_argument('--pin-align', action='store_true', help='s81-die v17: q-bank pins at the q element pin of the same bit, '
                    'return-tree node pins in fixed slots (abutted stack bit-aligned), slot-station xa / xb on the pins of '
                    'their abutting column relay (pin_align gate: 0 FAIL in the field frames)')
    ap.add_argument('--hend-vr-nobp', action='store_true', help='s81 grpA 10-14: wide (>= 512 b) m2l VR hub ends: ot_meso_fifo NOBP + WCHK (r_rdy is tied 1; the negedge pin register no longer fans out to every ring write enable in half a cycle); same words / cycles')
    ap.add_argument('--hop-spread', type=int, default=0, help='s81-die r6: plan hub hops of buses >= N bits at R minus the '
                    'half pin extents of both ports (the gate judges the worst bit)')
    ap.add_argument('--pq-g', action='store_true', help='s81-die r6: PQ return topology G (the gather roots are the roots; '
                    'no frame pq_root row; PQ core count inputs await the count-only RWB leaves)')
    ap.add_argument('--pq-cnt', default=None, help='s81-die r6b: topology G count-only return leaves from this slot file '
                    '(physical/s81_die_pins/v19/pq_count_slots.json): 12 rwbc leaves in a 43.2 gather | capture seam, '
                    't_capture root-word taps, live / ga / q2f lanes to the PQ core (needs --pq-g --rtl-bind --rtl-hub-widths)')
    ap.add_argument('--cfifo-fall-launch', action='store_true', help='s81-die r6: the x-lane station that taps a cfifo '
                    'forwards a non-inverted clock copy (fn0) as its xf: xd launches on the falling xf edge, the closed colck '
                    'cfifo captures on the rising one (half-cycle source-synchronous hop)')
    ap.add_argument('--fwd-negcap', action='store_true', help='s81-die v17 glue RTL: the ends of a forwarded lane (dsfd_cfifo xd, '
                    'm2l / r2l end relays di<j>) capture on the falling forwarded-clock edge (half-cycle hop, as the stations)')
    ap.add_argument('--peer-pin-pos', action='store_true', help='s81-die v16: a slab port stands on the pin group of its '
                    'station / link-end peer (laid first), not on the peer outline centre')
    ap.add_argument('--rtl-bind', action='store_true', help='s81-die-rtl-bind 2026-10-14 (owner NO STUBS rule): die nets '
                    'bound to the masters\' REAL RTL ports -- serial ckv / rsv of the two-clock *_c masters (F3), svc_join '
                    'ck / rst (F8), the layer1 sequencer master dsfd_stage_seq_c8 (engines 0..7, F4).  Changes pins: '
                    'adopt with a regenerated pin set')
    ap.add_argument('--wfc-priced', action='store_true', help='contract v16: WFC kit die pins of the PRICED kit (RD2 1: '
                    't_srd 31, f_srq 1026; t_ft 4 to the host fault collector)')
    ap.add_argument('--rly-face-reach', type=float, default=0.0, help='s81-die v16: the last column relay of a net takes '
                    'the out face nearest its worst load when the default face centre is > UM from a load pin (straight '
                    'master kept: in face opposite)')
    ap.add_argument('--lane-pins', type=int, nargs='?', const=2, default=0, help='s81-die v15: hub ports of a straight VCH '
                    'station lane take their pins centred on the lane at P-track pitch (default 2) on both slabs; lanes '
                    'are allocated with non-overlapping pin spans; the 8 t_hc_y slices follow the slices of the one port')
    ap.add_argument('--peer-span-centre', action='store_true', help='s81-die-iter: with --rtl-hub-widths, centre each '
                    'face-to-face wide group on the die span shared with its peers (both ends of an abutting pair line up)')
    ap.add_argument('--bf-x2-static', action='store_true', help='S-BIND 2026-10-15: packed 1,101-b static x lane '
                    '(legacy 564 + BF x2 536 + valid): static hx pipelines, static column ingress, x2 slot stations, BF xb bound')
    ap.add_argument('--static-coll', action='store_true', help='S-BIND 2026-10-15: = --static-seams --static-collective')
    ap.add_argument('--suhc-static-issue', action='store_true', help='S-BIND 2026-10-15: SU / HC endpoints issue on the '
                    'compiler command edge (manifest define DSFD_SUHC_STATIC_ISSUE); the void VM -> SU / HC t_inp nets leave')
    ap.add_argument('--static-seams', action='store_true', help='S-DIE r11 2026-10-15: static VM<->collective seam (t_vm 2204, t_crq 15, t_crs 513), drop vm.t_collective/tcs credit and hc_s.y_rdy, add collective.t_hc_tag -> hc_s.y_tag')
    ap.add_argument('--static-collective', action='store_true', help='swap the hub collective to dsfd_sp_collective_static_c (needs its RTL in the tree)')
    ap.add_argument('--mix4-slot', help='X,Y,W,H um: Engram MIX4 home reservation (screen)')
    ap.add_argument('--pin-overrides', help='S-DIE r11: JSON (opentallas.s81.pin_overrides.v1) of adopted die pin re-assignments '
                    '(GEO-S C1..C7 / D*): per inst or master, port centre shifted along its face (or set absolute); '
                    'applied to the generated masters before any station search, refused when a pin leaves its face')
    ap.add_argument('--rtl-hub-widths', action='store_true', help='s81die-1011 (die lead decision): W hub column gather -> '
                    'capture -> VM (capture directly above gather) and the hub buses at the RTL widths: gather t_capture 6,947 '
                    '(12 root lanes), capture t_vm 13,376, collective t_vm 2,100, VM -> collective f_vm 592 + ts 3')
    ap.add_argument('--ctrl-adapters', action='store_true', help='s81-ctl-1011: with --stage-seq, engine c/d/s buses from the sseq slab to the '
                    '*_c slab endpoints (physical/s81_ctrl/die_ctrl_bindings.json); the die control gate FAILS the build on '
                    'any unbound engine / port-audit finding')

    ap.add_argument('--ctrl-bindings', type=Path, help='native control-plane endpoint manifest, audited before build')
    ap.add_argument('--mtp-seq-mm2', type=float, help='MTP-DIE: sequencer slab area (default 0.15 mm2)')
    ap.add_argument('--mtp-links', type=int, default=0, help='MTP-DIE: head die extra draft fan-out SerDes '
                    '(default 0; the DP1-EP5 primary head die takes 5: one per draft row package)')
    return ap


def apply_options(a):
    """configure the module globals for the die variant in `a` (die_options)"""
    global CTRL_SLAB, CTRL_ROLE, CTRL_BINDINGS, VIEW_BINDING
    global CANONICAL_LAYOUT, PAIRS, BF_PAIRS, NV_PAIRS
    if getattr(a, 'view_binding', None):
        VIEW_BINDING = a.view_binding
    CTRL_SLAB = bool(getattr(a, 'ctrl_slab', False))
    CTRL_ROLE = getattr(a, 'ctrl_role', 'layer')
    CTRL_BINDINGS = None
    global CTRL_ADAPTERS, RTL_HUB_WIDTHS
    global STATIC_SEAMS, STATIC_COLLECTIVE, MIX4_SLOT
    STATIC_SEAMS = bool(getattr(a, 'static_seams', False) or getattr(a, 'static_coll', False))
    STATIC_COLLECTIVE = bool(getattr(a, 'static_collective', False) or getattr(a, 'static_coll', False))
    global SUHC_STATIC_ISSUE, BF_X2_STATIC, LSW
    SUHC_STATIC_ISSUE = bool(getattr(a, 'suhc_static_issue', False))
    BF_X2_STATIC = bool(getattr(a, 'bf_x2_static', False))
    LSW = X0B + X1B + CCB + (X2B if BF_X2_STATIC else 0)
    MIX4_SLOT = tuple(float(v) for v in a.mix4_slot.split(',')) if getattr(a, 'mix4_slot', None) else None
    global PIN_OVERRIDES
    PIN_OVERRIDES = load_pin_overrides(a.pin_overrides) if getattr(a, 'pin_overrides', None) else None
    if STATIC_COLLECTIVE and not STATIC_SEAMS:
        raise ValueError('--static-collective needs --static-seams (its ports are the static seam)')
    CTRL_ADAPTERS = bool(getattr(a, 'ctrl_adapters', False))
    RTL_HUB_WIDTHS = bool(getattr(a, 'rtl_hub_widths', False))
    global PEER_SPAN_CENTRE, LANE_PINS
    LANE_PINS = int(getattr(a, 'lane_pins', 0) or 0)
    PEER_SPAN_CENTRE = bool(getattr(a, 'peer_span_centre', False))
    global SUHC_V2, SUHC_V2_HC_N
    SUHC_V2 = bool(getattr(a, 'suhc_v2', False))
    SUHC_V2_HC_N = bool(getattr(a, 'suhc_v2_hc_north', False))
    if SUHC_V2 and not (getattr(a, 'suhc_1011', False) and CTRL_ADAPTERS):
        raise ValueError('--suhc-v2 needs --suhc-1011 --ctrl-adapters (the v2 masters are the *_c endpoints)')
    if CTRL_ADAPTERS and not (getattr(a, 'stage_seq', False) and getattr(a, 'wfc_kit', False)):
        raise ValueError('--ctrl-adapters binds the engines of the dsfd_stage_seq slab: needs --wfc-kit --stage-seq')
    if CTRL_ADAPTERS and (a.gen != 'r8' or a.rev != 'r9'):
        raise ValueError('--ctrl-adapters requires the r9 wired die (staged hub buses)')
    if CTRL_ADAPTERS and CTRL_SLAB:
        raise ValueError('--ctrl-adapters with --ctrl-slab: one stage controller (decision A: dsfd_stage_seq + adapters)')
    if CTRL_SLAB:
        if not (getattr(a, 'hop_fix', False) and getattr(a, 'pin_relay', False)):
            raise ValueError('--ctrl-slab requires implemented --hop-fix --pin-relay endpoint stations')
        if a.gen != 'r8' or a.rev != 'r9':
            raise ValueError('--ctrl-slab requires r9 wired die')
        if not getattr(a, 'ctrl_bindings', None):
            raise ValueError('--ctrl-slab requires real native endpoints (--ctrl-bindings); no inferred or tied-off binding')
        from s81_ctrl.die_binding_contract import validate_manifest
        CTRL_BINDINGS = validate_manifest(a.ctrl_bindings, ROOT, CTRL_ROLE)
    global Q_ELEM_FRAME_H, BF_PER_REGION, SU_AREA_MM2, BF_EXPLICIT_IDS
    SU_AREA_MM2 = getattr(a, "su_mm2", None)
    Q_ELEM_FRAME_H = getattr(a, "q_elem_h", None)
    BF_PER_REGION = getattr(a, "bf_per_region", None)
    set_cc_reach(a.cc_reach_um)
    global VCH_INTERLEAVE, LINK_FIX, HC_XFACE, GEOMETRY_FIX
    GEOMETRY_FIX = bool(getattr(a, 'geometry_fix', False))
    global FACE_PIN_INSET
    FACE_PIN_INSET = 0.048 if getattr(a, 'face_pin_inset', False) else 0.0
    VCH_INTERLEAVE = bool(a.vch_interleave)
    HC_XFACE = bool(getattr(a, 'hc_xface', False))
    global LINK_SPLIT, SEL_XSTG
    SEL_XSTG = bool(getattr(a, 'sel_xstg', False))
    global PIN_RELAY, NXT_REACH, CHS, VCH8, HC_CORR, SPINE_W8
    PIN_RELAY = bool(getattr(a, 'pin_relay', False))
    NXT_REACH = bool(getattr(a, 'nxt_reach', False))
    global RELAY_PROGRESS, RT_STRIP
    RELAY_PROGRESS = bool(getattr(a, 'relay_progress', False))
    RT_STRIP = float(getattr(a, 'rt_strip', 0.0) or 0.0)
    global SSTN_CCPAD
    SSTN_CCPAD = bool(getattr(a, 'sstn_ccpad', False))
    global PIN_NEED
    PIN_NEED = bool(getattr(a, 'pin_need', False))
    global VM_FACE_MM2
    VM_FACE_MM2 = getattr(a, 'vm_face_mm2', None)
    CHS = [float(v) for v in a.ch_heights.split(',')] if getattr(a, 'ch_heights', None) else None
    global PQ_PLACE, FIELD_MARGIN
    # MTP-DIE option binding (0544fca2c; dropped by a later merge, which made --wfc-hard / --mtp-seq / --mtp-links
    # silent no-ops: restored by mtp-draftdie 2026-10-09, test_s81_mtp_options_bind guards it)
    global WFC_HARD, MTP_SEQ, MTP_SEQ_MM2, MTP_LINKS, DRAFT_SIDE, WFC_KIT, WFC_ROLE, MTP_SEQ_RTT
    MTP_SEQ_RTT = bool(getattr(a, 'mtp_seq_rtt', False))
    global MTP_EP, P2_LNK
    MTP_EP = bool(getattr(a, 'mtp_ep', False)); P2_LNK = bool(getattr(a, 'p2_lnk', False))
    WFC_KIT = bool(getattr(a, 'wfc_kit', False))
    global WFC_PRICED, PEER_PIN_POS, HOP_R_HUB
    HOP_R_HUB = float(getattr(a, 'hop_r_hub', 0.0) or 0.0)
    PEER_PIN_POS = bool(getattr(a, 'peer_pin_pos', False))
    global PIN_ALIGN, FWD_NEGCAP, HEND_VR_NOBP
    PIN_ALIGN = bool(getattr(a, 'pin_align', False))
    global XB_RGAP_FIRST, X_SITE_PAIR
    XB_RGAP_FIRST = bool(getattr(a, 'xb_rgap_first', False))
    X_SITE_PAIR = bool(getattr(a, 'x_site_pair', False))
    global SPLIT_FAR_PINS
    SPLIT_FAR_PINS = bool(getattr(a, 'split_far_pins', False))
    global ALIGN_JOGS
    ALIGN_JOGS = bool(getattr(a, 'align_jogs', False))
    global HC_RTL_WIDTHS, HC_T_FWD, HC_T_RET
    HC_RTL_WIDTHS = bool(getattr(a, 'hc_rtl_widths', False))
    if HC_RTL_WIDTHS:
        HC_T_FWD, HC_T_RET = hc_rtl_widths()
    if getattr(a, 'pdn_field_cov', 0.0):
        COV['field'] = COV['channel'] = float(a.pdn_field_cov)
    global HOP_PAIR, HOP_ITER, HOP_SPREAD
    HOP_SPREAD = int(getattr(a, 'hop_spread', 0) or 0)
    HOP_PAIR = float(getattr(a, 'hop_pair', 0.0) or 0.0)
    HOP_ITER = int(getattr(a, 'hop_iter', 0) or 0)
    assert not X_SITE_PAIR or XB_RGAP_FIRST, '--x-site-pair needs --xb-rgap-first (and --xb-rgap)'
    FWD_NEGCAP = bool(getattr(a, 'fwd_negcap', False))
    global CFIFO_FALL
    CFIFO_FALL = bool(getattr(a, 'cfifo_fall_launch', False))
    HEND_VR_NOBP = bool(getattr(a, 'hend_vr_nobp', False))
    WFC_PRICED = bool(getattr(a, 'wfc_priced', False))
    global RTL_BIND, HOST_CF_BITS, HOST_TC_BITS   # HC_T_FWD / HC_T_RET / HC_RTL_WIDTHS declared global above (r6: was a SyntaxError)
    RTL_BIND = bool(getattr(a, 'rtl_bind', False))
    if RTL_BIND:
        # F6: the collective <-> layer-die host channel at dsfd_host_c's RTL widths: collective -> host {t_cr, h_cls 2,
        # h_d 512, h_v} = 516, host -> collective {st 11, h_crn 5, t_v, t_d 64} = 81 (were 514 / 130 placeholders)
        HOST_CF_BITS, HOST_TC_BITS = 516, 81
        if STATIC_COLLECTIVE:
            # static collective host channel: t_host 515 {h_cls 2, h_d 512, h_v} (no t_cr credit), f_host 77 {valid,
            # status 11, completion 65} (no h_crn credits)
            HOST_CF_BITS, HOST_TC_BITS = 515, 77
        # F9: one implementation (die lead r5 4f0307291): --rtl-bind implies --hc-rtl-widths = hc_rtl_widths() of the
        # production HC (3,056 / 2,164 per column, hc_t reset in band) with the fwd / ret runs moved apart
        HC_RTL_WIDTHS = True
        HC_T_FWD, HC_T_RET = hc_rtl_widths()
    assert not WFC_PRICED or (WFC_KIT and not getattr(a, 'wfc_crp', False)), '--wfc-priced: the --wfc-kit stage / source kit (not --wfc-crp)'
    global WFC_CRP, STAGE_SEQ
    WFC_CRP = bool(getattr(a, 'wfc_crp', False)) and WFC_KIT
    STAGE_SEQ = bool(getattr(a, 'stage_seq', False)) and WFC_KIT
    if WFC_CRP and getattr(a, 'coll_mtp_far', None):
        raise SystemExit('--wfc-crp with --coll-mtp-far: the TOKIN token-return path is a kit port, not a cr2 port (not built)')
    WFC_ROLE = 'source' if getattr(a, 'ctrl_role', 'layer') == 'source' else 'stage'
    ws, ms = getattr(a, 'wfc_hard', None), getattr(a, 'mtp_seq', None)
    WFC_HARD = WFC_HARD_DEFAULT if ws is None else bool(ws)
    MTP_SEQ = MTP_SEQ_DEFAULT if ms is None else bool(ms)
    MTP_SEQ_MM2 = getattr(a, 'mtp_seq_mm2', None) or 0.15
    MTP_LINKS = int(getattr(a, 'mtp_links', 0) or 0)
    DRAFT_SIDE = getattr(a, 'draft', None)
    if DRAFT_SIDE:
        assert a.gen == 'r8' and a.die == 'layer1', '--draft: the MD-2 draft die is the r8 layer1 recipe'
    PQ_PLACE = bool(getattr(a, 'pq_place', False))
    global FRAME_OUT_RELAY, HOST_SLAB
    FRAME_OUT_RELAY = bool(getattr(a, 'frame_out_relay', False))
    HOST_SLAB = bool(getattr(a, 'host', False))
    global COLL_SPLIT3, COLL_SPLIT3_CR, COLL_SPLIT3_COMP, CK_RULE, Q_X1B
    Q_X1B = bool(getattr(a, 'q_x1b', False))
    global CFG_RGAP, CFG_RGAP_AT
    CFG_RGAP = float(getattr(a, 'cfg_rgap', 0.0) or 0.0)
    CFG_RGAP_AT = int(getattr(a, 'cfg_rgap_at', 4) or 4)
    global XB_RGAP
    XB_RGAP = float(getattr(a, 'xb_rgap', 0.0) or 0.0)
    assert not XB_RGAP or abs(XB_RGAP / GX - round(XB_RGAP / GX)) < 1e-6, ('--xb-rgap off the x lattice', XB_RGAP)
    global LANE_EQUAL
    LANE_EQUAL = bool(getattr(a, 'lane_equal', False))
    if CFG_RGAP:
        assert CFG_RGAP > 0 and abs(CFG_RGAP / GX - round(CFG_RGAP / GX)) < 1e-6, ('--cfg-rgap off the x lattice', CFG_RGAP, GX)
    CK_RULE = bool(getattr(a, 'ck_rule', False))
    COLL_SPLIT3_CR = bool(getattr(a, 'coll_split3_cr', False))
    COLL_SPLIT3 = bool(getattr(a, 'coll_split3', False)) or COLL_SPLIT3_CR
    COLL_SPLIT3_COMP = 'physical/s81_ph_views/collective/composition_split3cr.json' if COLL_SPLIT3_CR else 'physical/s81_ph_views/collective/composition_split3.json'
    # mtp-colllane-1011 (ds-1010 decision: DEDICATED MTP lanes, never a pass-through queue in the collective core)
    global COLL_MTP_LANE, COLL_P2_LANE
    COLL_MTP_LANE = bool(getattr(a, 'coll_mtp_lane', False))
    COLL_P2_LANE = bool(getattr(a, 'coll_p2_lane', False))
    global COLL_MTP_FAR
    COLL_MTP_FAR = getattr(a, 'coll_mtp_far', None)
    global SEEDL, HROW, HROW_SRC
    SEEDL = bool(getattr(a, 'seedl', False))
    HROW_SRC = getattr(a, 'hrow_src', None)
    if HROW_SRC is not None and (getattr(a, 'die', None) != 'layer1' or not getattr(a, 'wfc_kit', False)):
        raise SystemExit('--hrow-src: a layer1 stage die with --wfc-kit (the t_hep issue-epoch events)')
    HROW = bool(getattr(a, 'hrow', False))
    if HROW and (not SEEDL or not getattr(a, 'fwd_iface', False) or getattr(a, 'die', None) != 'layer1'):
        raise SystemExit('--hrow: with --seedl --fwd-iface on the 1-stack primary die (store in the free SE slot)')
    if SEEDL and (getattr(a, 'draft', None) != 'P' or COLL_MTP_FAR != 'primary'):
        raise SystemExit('--seedl: DSpark primary die (--draft P) with --coll-mtp-far primary')
    if COLL_MTP_FAR == 'primary':   # mtp-dsbind: the primary die's end of a head MTP lane (seed descriptor class)
        if not (COLL_SPLIT3_CR and int(getattr(a, 'mtp_links', 0) or 0) and getattr(a, 'draft', None) == 'P'
                and getattr(a, 'host', False)):
            raise SystemExit('--coll-mtp-far primary: needs --draft P --coll-split3-cr --mtp-links >= 1 --host')
        COLL_MTP_LANE = True
    elif COLL_MTP_FAR:   # mtp-wfc 2026-10-10: the far (S0) end of the head die's MTP lane: same lane composition
        if not (COLL_SPLIT3_CR and int(getattr(a, 'mtp_links', 0) or 0) and getattr(a, 'ctrl_role', None) == 'source'
                and getattr(a, 'wfc_kit', False)):
            raise SystemExit('--coll-mtp-far s0: needs --coll-split3-cr --mtp-links >= 1 --ctrl-role source --wfc-kit')
        COLL_MTP_LANE = True
    if COLL_MTP_LANE or COLL_P2_LANE:
        if not COLL_SPLIT3_CR or (COLL_MTP_LANE and COLL_P2_LANE):
            raise SystemExit('--coll-mtp-lane / --coll-p2-lane: one of them, with --coll-split3-cr (credit seams, LCR lane tiles)')
        if COLL_MTP_LANE and not COLL_MTP_FAR and (getattr(a, 'die', None) != 'head' or not int(getattr(a, 'mtp_links', 0) or 0) or getattr(a, 'mtp_seq', None) is False):
            raise SystemExit('--coll-mtp-lane: head die with --mtp-seq and --mtp-links >= 1 (lane W4 = the first MTP SerDes lk_W4)')
        if COLL_P2_LANE and getattr(a, 'draft', None) != 'A':
            raise SystemExit('--coll-p2-lane: MD-2 P2 draft die A (--draft A)')
        COLL_SPLIT3_COMP = 'physical/s81_ph_views/collective/composition_split3cr_%s.json' % ('mtpl' if COLL_MTP_LANE else 'p2l')
    global CTRL_RQ, FWD_IFACE, HOP_EXTRA, HOP_GATE_UM, CTRL_SVC_ALIGN, BF_HIER, BF_FRAME_EXTRA, BF_FRONT_W, BF_ROUTE_H, BF_SEAM_UM, LANES_W, COL_W8, COL_PITCH8, DIE
    BF_HIER = getattr(a, 'bf_hier', None)
    if getattr(a, 'bf_hier_compact', False):
        assert BF_HIER is None, '--bf-hier and --bf-hier-compact are exclusive'
        BF_HIER, BF_FRONT_W, BF_ROUTE_H = 450.144, 100.224, a.bf_hier_height
    else:
        BF_FRONT_W, BF_ROUTE_H = 280.152, 190.08
    BF_SEAM_UM = 1.188 if getattr(a, 'bf_hier_compact', False) else 0.0
    BF_FRAME_EXTRA = up(max(0.0, 2 * BF_HIER + BF_FRONT_W + 2 * BF_SEAM_UM + 8.64 - 2 * LANE_W), GX) if BF_HIER else 0.0
    LANES_W = 2 * LANE_W + BF_FRAME_EXTRA
    COL_W8 = LANES_W + NS_W + RSC_W
    COL_PITCH8 = COL_W8 + 8.64
    global HUB_SOUTH_SHIFT, ASSIGNED_PINS_DIR
    HUB_SOUTH_SHIFT = float(getattr(a, 'hub_south_shift', 0.0))
    ASSIGNED_PINS_DIR = getattr(a, 'assigned_pins_dir', None)
    _ASSIGNED_PIN_CACHE.clear()
    global SUHC_1011, SUHC_DOM, SUHC_HC_VM, VM_SLAB, COLL_SLAB_H
    COLL_SLAB_H = getattr(a, 'coll_slab_h', None)
    global SU_V2_UM, HC_V2_UM, HROW_UM, HC_T_UM, HC_S_GROW_DOWN, P2_OUTLINE_UM, P2_SLAB_MM2
    HC_S_GROW_DOWN = 0.0
    if getattr(a, 'contract', None):
        # --contract (s81-die-iter 2026-10-12): slab outlines from results/arch/hier_contract_1011/s81.json (v3+): SU / HC v2
        # slabs (column channels), centre hard elements, VM slab (overrides --vm-slab), MTP hrow
        cslots_ = {s_['name']: s_ for s_ in json.loads((ROOT / a.contract).read_text())['slots']}
        def _o(n_):
            return (float(cslots_[n_]['outline']['w']), float(cslots_[n_]['outline']['h']))
        SU_V2_UM, HC_V2_UM = _o('sp_su_s'), _o('sp_hc_s')
        HC_S_GROW_DOWN = float(cslots_['sp_hc_s'].get('grow_down_um', 0.0))
        assert HC_S_GROW_DOWN >= 0.0, 'HC contract growth must preserve the north edge'
        HC_T_UM = _o('sp_hc_t') if 'sp_hc_t' in cslots_ else None
        if 'sp_p2' in cslots_:   # contract v13: draft-A P2 = xport + head + fadd16 tiles (prefix_path_hub dropped)
            P2_OUTLINE_UM = _o('sp_p2')
            P2_SLAB_MM2 = P2_OUTLINE_UM[0] * P2_OUTLINE_UM[1] / 1e6
        CONTRACT_SLABS.clear()
        for n_, k_ in (('capture', 'sp_capture'), ('gather', 'sp_gather'), ('collective', 'sp_collective'), ('wfc_hard', 'sp_wfc')):
            if k_ in cslots_ and _o(k_)[0] > 0:
                CONTRACT_SLABS[n_] = _o(k_)
        if 'sp_vm' in cslots_:
            a.vm_slab = '%.3f,%.3f' % _o('sp_vm')
        for k_ in ('rep/hrow', 'hrow'):      # v6: the replicated-slot key (the bare key never matched)
            if k_ in cslots_ and _o(k_)[0] > 0:
                HROW_UM = _o(k_)
                break
    SUHC_1011 = bool(getattr(a, 'suhc_1011', False))
    SUHC_DOM, SUHC_HC_VM = ('stream_1p2', 2048) if SUHC_1011 else ('serial_0p9', 1024)
    global SU_E, HROW_TX
    SU_E = float(getattr(a, 'su_e', 0.0) or 0.0)
    HROW_TX = bool(getattr(a, 'hrow_tx', False))
    assert not HROW_TX or (SUHC_1011 and SU_E), '--hrow-tx needs --suhc-1011 --su-e (h resident in HC, E-column slot)'
    VM_SLAB = tuple(float(x) for x in a.vm_slab.split(',')) if getattr(a, 'vm_slab', None) else None
    global ECOL_SLABS, ECOL_W
    ECOL_SLABS = tuple(x for x in (getattr(a, 'ecol_slabs', None) or '').split(',') if x)
    assert set(ECOL_SLABS) <= {'wfc', 'host', 'capture', 'seedl', 'p2'}, ('--ecol-slabs: wfc / host / capture / seedl / p2', ECOL_SLABS)
    ECOL_W = float(getattr(a, 'ecol_w', 518.4) or 518.4)
    global TIER_COLS8, ROOTS, TIER_COLS_SET
    TIER_COLS_SET = bool(getattr(a, 'tier_cols', None))
    if TIER_COLS_SET:
        TIER_COLS8 = tuple(int(x) for x in a.tier_cols.split(','))
        assert len(TIER_COLS8) == TIERS and min(TIER_COLS8) >= 1, ('--tier-cols needs one count per tier', TIER_COLS8)
        assert a.die in LAYER_KINDS, '--tier-cols: layer dies only (head bundles assume 128 frames)'
        ROOTS = 2 * sum(TIER_COLS8)
    # --tier-cols: the reticle die (33 x 26 mm); build_r8 asserts the columns fit.  Without it --bf-hier keeps the
    # over-reticle evidence vehicle (128 frames, die widened by 2 x 11 x BF_FRAME_EXTRA).
    DIE = (up(33000.0 + 2 * max(TIER_COLS8) * BF_FRAME_EXTRA, GX) if (BF_HIER and BF_FRAME_EXTRA > 0 and not TIER_COLS_SET) else 33000.0, 26000.0)
    if BF_HIER:
        assert (Q_ELEM_FRAME_H or 0) >= 0 and (getattr(a, 'elem_h', None) or ELEM_FRAME_H) >= BF_ROUTE_H + 8.64 - 1e-6, \
            '--bf-hier: the BF frame (--elem-h) must hold the routed BF blocks (BF_ROUTE_H) + halos'
    HOP_EXTRA = int(getattr(a, 'hop_extra', 0) or 0)
    global RLY_FACE_REACH, RLY_REAL_DIMS
    RLY_REAL_DIMS = bool(getattr(a, "rly_real_dims", False))
    RLY_FACE_REACH = float(getattr(a, 'rly_face_reach', 0.0) or 0.0)
    HOP_GATE_UM = getattr(a, 'hop_gate', None)
    CTRL_SVC_ALIGN = bool(getattr(a, 'ctrl_svc_align', False))
    FWD_IFACE = bool(getattr(a, 'fwd_iface', False))
    CTRL_RQ = bool(getattr(a, 'ctrl_rq', False)) or a.die == 'layer1e'
    if a.die == 'layer1e':
        assert a.gen == 'r8' and a.rev == 'r9' and HOST_SLAB, \
            'layer1e: the r9 wired die with --host (Engram table boot load + cfg through dsfd_host)'
    if getattr(a, 'field_margin', None) is not None:
        FIELD_MARGIN = float(a.field_margin)     # explicit, every gen (a leftover --pq-place margin must not leak)
    else:
        # s81-die-2 2026-10-08: the adopted PQ root (211.68 tall, row 241.92 vs 164.16) takes 6 x 77.76 um from the field;
        # at the 216 um minimum gap the mixed221 frame lost its 9th slot by 0.35 um a tier ("mixed slots exceed field
        # height").  Under --pq-place the minimum gap is PQ_FIELD_MARGIN; the field stays centred (actual gap ~215 um).
        FIELD_MARGIN = PQ_FIELD_MARGIN if (PQ_PLACE and not getattr(a, 'pq_g', False)) else FIELD_MARGIN_DEFAULT
    global PQ_G, PQ_ROOTS
    PQ_G = bool(getattr(a, 'pq_g', False))
    assert not PQ_G or PQ_PLACE, '--pq-g needs --pq-place (the PQ core slot)'
    PQ_ROOTS = PQ_PLACE and not PQ_G
    global PQ_CNT
    PQ_CNT = None
    if getattr(a, 'pq_cnt', None):
        assert PQ_G and getattr(a, 'rtl_bind', False) and getattr(a, 'rtl_hub_widths', False), \
            '--pq-cnt needs --pq-g --rtl-bind --rtl-hub-widths (the count leaves tap the RTL-width t_capture bus)'
        PQ_CNT = json.loads((ROOT / a.pq_cnt).read_text())
    if PQ_PLACE:
        assert a.gen == 'r8' and a.rev == 'r9' and a.die in LAYER_KINDS and getattr(a, 'q_elem_h', None), \
            '--pq-place: the r9 mixed q/BF layer die (--q-elem-h) only'
        CHS = [c + (PQ_ROOT_ROW if (t < TIERS and PQ_ROOTS) else 0.0) for t, c in enumerate(CHS or [CH] * (TIERS + 1))]
    VCH8 = float(a.vch_w) if getattr(a, 'vch_w', None) else 1209.6
    HC_CORR = float(a.hc_corr) if getattr(a, 'hc_corr', None) else 1209.6
    SPINE_W8 = (2 * up(a.hub_column_width, GX) + VCH8) if getattr(a, "hub_column_width", None) else SPINE_W + VCH8 - VCH
    LINK_SPLIT = bool(getattr(a, 'link_split', False)) and bool(a.link_fix)
    LINK_FIX = bool(a.link_fix)
    global CORR_INTERLEAVE, HOP_FIX, HOP_PLAN, MESO_D8
    CORR_INTERLEAVE = bool(a.corr_interleave)
    HOP_FIX, HOP_PLAN, MESO_D8 = bool(a.hop_fix), None, bool(a.meso_d8)
    global FWD_REACH, HOP_R_FWD, HOP_R_CC, CFIFO_V2, CF_WH
    CFIFO_V2 = bool(a.cfifo_v2)
    global CFIFO_COLCK
    CFIFO_COLCK = bool(getattr(a, 'cfifo_colck', False))
    assert not CFIFO_COLCK or CFIFO_V2, '--cfifo-colck needs --cfifo-v2'
    CF_WH = CF_WH_V2 if CFIFO_V2 else (850.176, 47.52)
    FWD_REACH = float(a.fwd_pitch) if a.fwd_pitch else LINK_STAGE_UM
    # s81-gen: the OT_S81_HOP_R_CC override (9917e9987) was reset to 410 here, after import (the r4e_rcc runs were no-ops)
    HOP_R_FWD, HOP_R_CC = LINK_STAGE_UM, float(getattr(a, 'hop_r_cc', None) or os.environ.get('OT_S81_HOP_R_CC', 410.0))
    global PATH_PICK, RELAY_TT_REACH, OPERAND_PATH_PICK
    OPERAND_PATH_PICK = bool(getattr(a, 'operand_path_pick', False))
    PATH_PICK = bool(getattr(a, 'path_pick', False)) or os.environ.get('OT_S81_PATH_PICK', '0') == '1'
    RELAY_TT_REACH = getattr(a, 'relay_tt_reach', None)
    if a.fwd_pitch:            # every hop on the die at or under the pitch
        HOP_R_FWD = HOP_R_CC = float(a.fwd_pitch)
    global REV, HEAD_DIES
    REV, HEAD_DIES = a.rev, a.head_dies
    configure(a.die, a.gen)
    if a.gen == 'r8':
        if a.elem_h or a.field_margin is not None:
            slot_geometry(a.elem_h, a.field_margin)
        if getattr(a, 'bf_per_region', None) is not None:
            BF_PER_REGION = a.bf_per_region
            set_pairs(a.pairs or PAIRS)
        elif a.pairs:
            set_pairs(a.pairs)
        if getattr(a, 'bf_pair_ranges', None) is not None:
            assert a.die == 'head' and BF_PER_REGION is None and NV_PAIRS == 0, \
                '--bf-pair-ranges requires r8 head, no NV, and no --bf-per-region'
            BF_EXPLICIT_IDS = parse_bf_pair_ranges(a.bf_pair_ranges, PAIRS)
            set_pairs(PAIRS)
        slot_geometry()
    else:
        assert getattr(a, 'bf_pair_ranges', None) is None, '--bf-pair-ranges requires r8'


    CANONICAL_LAYOUT = None
    if getattr(a, 'canonical_layout', None):
        assert a.gen == 'r8' and a.die in LAYER_KINDS and not HEAD_BUNDLES
        from s81.canonical_layout import load as canonical_load
        CANONICAL_LAYOUT = canonical_load(a.canonical_layout, ROOT)
        assert ROOTS == 128 and CFG_PER_PAIR == 7
        PAIRS, BF_PAIRS, NV_PAIRS = 2417, 519, 0
        BF_PER_REGION = None
        BF_EXPLICIT_IDS = frozenset(CANONICAL_LAYOUT['bf_ids'])
        slot_geometry()


def main(argv=None):
    global BF_EXPLICIT_IDS
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['plan', 'real', 'netlist', 'grt', 'ir', 'irm', 'psmt', 'record', 'check'])
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
        ub = unbound_functional_pins(m)
        if ub:     # build-every-path rule (s81-die-2 2026-10-08, tie-off audit TA-10): no functional pin without a net
            raise SystemExit('UNBOUND functional real-macro pins (master, pin): instances: '
                             + json.dumps({f'{k[0]}.{k[1]}': v for k, v in sorted(ub.items())}))
        if CTRL_ADAPTERS:  # s81-ctl-1011: engine command plane + port audit (no placeholder pins, no unbound engine)
            from s81_ctrl.die_ctrl_gate import gate as ctrl_gate
            # a layer1 die (no eng_SE: not an Engram home) runs the stage programs without Engram ops
            cg = ctrl_gate(m, 'layer1' if (CTRL_ROLE == 'layer' and DIE_KIND == 'layer1') else CTRL_ROLE)
            m['ctrl_gate'] = cg
            if a.out:
                ctrl_record = Path(str(a.out) + '.ctrl_gate.json')
                ctrl_record.parent.mkdir(parents=True, exist_ok=True)
                ctrl_record.write_text(json.dumps(cg, indent=1, default=str) + '\n')
            if cg['verdict'] != 'PASS':
                msg_ = 'DIE_CTRL_GATE FAIL (%d): ' % len(cg['findings']) + '; '.join(cg['findings'][:40])
                wv_ = os.environ.get('OT_S81_CTRL_GATE_WARN')
                if (wv_ == '1' and a.mode == 'plan') or (wv_ == 'phys' and a.mode in ('plan', 'real', 'netlist', 'irm', 'check')):
                    # s81-die-iter 2026-10-12 ('phys'): the die PHYSICAL chain (assembly / GRT / STA / IR) also proceeds;
                    # the RTL port-audit findings stay a FAIL record (<out>.ctrl_gate.json / the die README), not waived
                    # s81die-1011: geometry-only die-fit (plan) proceeds; the port-audit findings stay a FAIL record
                    print('WARNING ' + msg_, file=sys.stderr)
                else:
                    raise SystemExit(msg_)
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
        ml = margin_lint(m)
        print(json.dumps(dict(margin_lint=ml), indent=1))
        pa = pin_align_gate(m, die_lef_texts(m), (a.work / 'pin_align.json') if getattr(a, 'work', None) else None,
                            raise_on_fail=False)
        if pa is not None:
            print(json.dumps(dict(pin_align={k_: pa[k_] for k_ in ('verdict', 'bundles', 'bits', 'by_verdict', 'by_kind',
                                                                    'by_order', 'jog_over_warn', 'order_not_preserved',
                                                                    'jog_max', 'jog_hist_um', 'bits_without_pin')}), indent=1))
            if pa['verdict'] == 'FAIL' and os.environ.get('OT_PIN_ALIGN_GATE', 'fail') == 'fail':
                return 3
        return 3 if ml['verdict'] == 'FAIL' else 0
    if a.mode == 'check':
        print(json.dumps(legality(m), indent=1))
        pc = pin_clashes(m)
        pc16 = pin_clashes(m, 16, 0.024 * 16 - 1e-6)
        print(json.dumps(dict(generated_pin_clashes=len(pc), examples=pc[:10], k16_clashes=len(pc16), k16_examples=pc16[:10])))
        print(json.dumps(trunk_stages(m), indent=1))
        ml = margin_lint(m)
        print(json.dumps(dict(margin_lint=ml), indent=1))
        return 3 if ml['verdict'] == 'FAIL' else 0
    if a.mode == 'plan' and a.gen == 'r8':
        out = ROOT / OUT / out_rev() / dict(layer='', layer1='layer1_die', layer1e='layer1e_die', head='head_die')[a.die]
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
        out = ROOT / OUT / {'layer': '', 'layer1': 'layer1_die', 'layer1e': 'layer1e_die'}.get(a.die, 'head_die')   # layer1 no longer overwrites head
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
                    # MTP homes replay from the case's own variant (a case without the keys predates them: off)
                    globals().update(WFC_HARD=bool(v_.get('wfc_hard')), MTP_SEQ=v_.get('mtp_seq') is not None,
                                     MTP_SEQ_MM2=v_.get('mtp_seq') or 0.15, MTP_LINKS=int(v_.get('mtp_links') or 0),
                                     DRAFT_SIDE=v_.get('draft'))
                    configure(v_.get('die', 'layer'), v_.get('gen', 'r7'))
                    if v_.get('gen') == 'r8':
                        REV = v_.get('rev', 'r8')
                        set_cc_reach(v_.get('cc_reach_um'))
                        VCH_INTERLEAVE = bool(v_.get('vch_interleave'))
                        HEAD_DIES = v_.get('head_dies', 12)
                        configure(v_.get('die', 'layer'), v_.get('gen', 'r7'))
                        slot_geometry(v_.get('elem_frame_h'))
                        set_pairs(v_['pairs'])
                        if v_.get('bf_pair_ids') is not None:
                            assert DIE_KIND == 'head' and NV_PAIRS == 0
                            BF_EXPLICIT_IDS = frozenset(v_['bf_pair_ids'])
                            assert all(0 <= p < PAIRS for p in BF_EXPLICIT_IDS)
                            set_pairs(PAIRS)
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
    if a.mode == 'netlist':      # s81-die-rtl-bind 2026-10-14: the structural die netlist only (port-bind / die-top lint)
        work.mkdir(parents=True, exist_ok=True)
        write_netlist(m, 1, work / 'die.v')
        if GEN == 'r8':
            (work / 'die_glue.sv').write_text(glue_rtl(m))    # this case's glue masters (die_port_bind --rtl-file)
        print(json.dumps(dict(die_v=str(work / 'die.v'), insts=len(m['insts']))))
    elif a.mode == 'real':
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
