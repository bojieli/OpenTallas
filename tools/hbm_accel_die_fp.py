#!/usr/bin/env python3
"""HBM accelerator compute die: floorplan, die-level global route, legality, PDN/IR and wire-stage pricing (2026-10-05).

First-release scope (tape-out workstreams out of scope).  Floorplan -> one hardened element -> replicate (AGENTS.md design
method 2), on the DS S81 / Qwen full-die flow (tools/dsrom_s81_fulldie.py, tools/qwen_rom_fulldie.py): every block is an
abstract with real ASAP7 signal pins on its facing edges (real LEFs where a hardened view exists, sized placeholders with
generated pins otherwise), placed through the orientation-aware snap library, connected by every die-level net.

Census (the measured DS-V4.1 1M composition, TP-96: results/uarch/hbm_current_target_portmap_20261005/model_portmap.json
DS): 32 SMs (ot_hbm_accel_sm_v NC8/SUB4, 8 per stack), four HBM3E stacks of 32 PCs, the N1024 SU with the fused SU
chains, SFU, HC/mHC, the 64-tile attention engine, the index path, router + expert workgroup steering, the TU collective
endpoint (8 ports x 545-bit flits) and its SerDes, command processor + pipelined issue, VM / activation-multicast root,
barrier root, loader + host link.

Layout (one quadrant per stack, mirrored N/S, E/W):

  S / N edges   two ot_hbm3e_phy_v41x_aw30_e8p5 each (real LEF, controller-side pins on the core face), the per-stack
                stream service (32 PC stream controllers + expert fetch + CDC FIFOs) above it, then the stack's 8-SM
                group: 4 columns x 2 rows of the SM element on a 259.2 um channel grid.
  hub band      between the S and N groups: index | attention (64 tiles) | spine (collective, cmdproc/issue, VM/x root,
                barrier root, loader, router/workgroup, quant) | SU (+fused chains) | SFU | HC.
  E / W edges   SerDes strips (real ot_pdie_serdes macros at the core face + reservation slab), host UCIe on E.

Paths priced (forwarded-link waypoints at <= 4 x 430.56 um; stage bound = sum over GRT-routed segments of
ceil(len / 430.56)):  HBM -> SM weight stream, SM -> SU result gather, SU -> collective endpoint -> SerDes, VM root -> SM
activation multicast, spine -> stream service (expert-fetch request), stream service -> attention (KV rows), barrier.

Modes:  plan | check | real --work W | grt --work W --k K --iters N [--empty] | ir --work W --window NAME |
        irwin (list every IR window) | record --work ROOT | price --feas F
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import qwen_rom_fulldie as Q  # noqa: E402
import dsrom_s81_fulldie as S  # noqa: E402

OUT = 'results/rtl/hbm_accel_die_floorplan_20261005'
PHY_LEF = S.PHY_LEF
SERDES_LEF = S.SERDES_LEF
UCIE_LEF = S.UCIE_LEF
# r16j (OWNER 2026-10-06 ~19:20): host PHY pin-accurate black box (tools/hbm_phy_bb.py): the loader host interface's
# AXI4-Lite BAR target + 64-bit AXI host DMA, PHY directions, W face M4, the UCIe-class outline unchanged
HOST_LEF = 'physical/hbm_accel_die_views/phy_bb/ot_hbm_host_phy/ot_hbm_host_phy.lef'
SNAP_LIB = S.SNAP_LIB
PLAT = S.PLAT
SM_CTX = 'results/uarch/hbm_accel_fulldie_inputs_20261004/providers/sm_r2/routes/sm_r2/fp/floorplan.json'
PORTMAP = 'results/uarch/hbm_current_target_portmap_20261005/model_portmap.json'
MATCHED = 'results/rtl/dshbm_matched_reference_20261005/composition.json'
ALLMEAS = 'results/rtl/dshbm_1m_allmeasured_20261004/composition.json'
QWEN = 'results/rtl/qwen_hbmacc_p8191_20261004/measured_composition.json'
QWEN_ALL = 'results/rtl/qwen_hbmacc_p8191_20261004/allmeasured.json'

GX, GY, SHAVE = S.GX, S.GY, S.SHAVE
up, dn = S.up, S.dn
EDGE = 20.0
LINK_STAGE_UM = 430.56          # corridor-gate closing pitch (S81 / Qwen die)
SS_REACH_UM = 504.0             # SS wire reach at 0.833 ns (W15)
WAYPOINT_UM = 4 * LINK_STAGE_UM
WP_DEFAULT = WAYPOINT_UM


RLY_CLASSES = (8, 48, 136, 304, 624, 1136)   # hbfd_rly width classes (tools/hbm_die_rly_kits.py CLASSES)
RLY_PIN_UM = 0.096              # 2 tracks a bit on one layer a face (M4 E / W, M5 N / S): buildable under the M5 cap
PIN_REACH_UM = 500.0            # owner 2026-10-13: register at the pin -> wire <= 500 um -> register at the pin


def rly_compose(bits):
    """the hbfd_rly class tiles one register stage of `bits` is built from (hbm_die_rly_kits.compose)"""
    n = math.ceil(bits / RLY_CLASSES[-1])
    per = math.ceil(bits / n)
    return [next(c for c in RLY_CLASSES if c >= per)] * n


def rly_face_um(bits):
    """data face of a `bits` register stage as family tiles side by side: each class face is Wc x 0.096 + 4.32 um on
    the 2.16-um lattice, >= 21.6 (hbm_die_rly_kits.face_len)"""
    return sum(max(21.6, round(math.ceil((c * RLY_PIN_UM + 4.32) / 2.16 - 1e-9) * 2.16, 2)) for c in rly_compose(bits))


def rly_depth_um(bits, horiz):
    """depth of the strip along the flow: 21.6 um; the N-S strips of the classes >= 304 b take 23.76 (their recipe-2
    kits, flops and hold cells at both pin faces, were 61.1-61.5 % utilised at 21.6: FLOORPLAN_MARGIN, 10-13)"""
    return 23.76 if (not horiz and rly_compose(bits)[0] >= 304) else 21.6


def stage_um(m):
    """die register-hop pitch of forwarded-clock station segments (430.56 um; forwarded reach 491 um)"""
    return LINK_STAGE_UM


def port_base(p):
    """'port@lo:hi[,lo:hi]' (a bus endpoint on a bit-slice of a port) -> 'port'"""
    return p.split('@', 1)[0]


def port_idx(p):
    """bit indices of a sliced endpoint 'port@lo:hi[,lo:hi]' in bus-bit order, else None"""
    if '@' not in p:
        return None
    out = []
    for r_ in p.split('@', 1)[1].split(','):
        lo, hi = map(int, r_.split(':'))
        out += list(range(lo, hi + 1))
    return out


def slice_port(p, k):
    """the port a sliced generated endpoint binds at bundling k: the base port at k = 1, a per-slice bundled port
    '<base>_s<first bit>' at k > 1 (bundled abstracts need no bit fidelity)"""
    if '@' not in p:
        return p
    return port_base(p) if k == 1 else f'{port_base(p)}_s{port_idx(p)[0]}'


REACH_INTER_UM, REACH_INTRA_UM = 359.0, 412.0       # budgets_20261006: SS reach at the 150 ps / 90 ps skew terms


def seg_stages(m, bid, L):
    """r17 (budget stage plan): register hops of one staged segment.  A forwarded-clock segment (station to station,
    the clock travels with the data) at 430.56 um; a common-clock segment (hub nets, the first hop out of a clocked
    source, the last hop into a block) as the budget prices a region-crossing path: one hop at the inter reach, the rest
    at the intra reach (>= the intra-only count).  Rounds before r17: ceil(L / 430.56) everywhere."""
    if L <= 0:
        return 0
    if not (m.get('variant') or {}).get('budget_stages') or bid in m.get('fclk', {}):
        return math.ceil(L / LINK_STAGE_UM) + m.get('relay_count', {}).get(bid, 0)
    extra = 1 if bid in m.get('pin_stage_buses', ()) else 0     # r19b: a station abutting the receiving pin
    extra += m.get('relay_count', {}).get(bid, 0)                 # r22: relay stations abutting block pins
    return 1 + math.ceil(max(0.0, L - REACH_INTER_UM) / REACH_INTRA_UM) + extra
CLK_HZ = 1.2e9
FINAL_ROUND = 'r25'             # (r16g until 09:30 PT; r16h = r16g + router_env + pin rules; r16i = r16h + index_q bands; r16j = r16i + svc x-band segments; r17 = r16j + budget stage plan)
# the round the records and the pricing are taken from (r8 until 2026-10-05 pm, r14b
#                                 until 2026-10-06: measured with the 16 S SMs mirrored, see R15 orient_fix)

# ------------------------------------------------------------------------------------------------ block ledger
# (mm2, grade, source).  grade: measured (placed/routed record), model (unified-model ledger), estimate (labelled).
SM_W, SM_H = 2202.768, 2072.79           # sm_r2 element context (SM_CTX), 202 macros, route OPEN
BLOCKS = dict(
    sm=(SM_W * SM_H / 1e6, 'measured-placed', SM_CTX + ' die (2202.768 x 2072.79 um, 202 macros; element route OPEN, '
        'hbm_accel_fmax_inventory_20261004/sm/closure.json)'),
    svc=(1.40, 'estimate', 'per-stack stream service: 32 x ot_hbm_accel_stream_pc_wb 12,033 um2 + 2 x ot_hbm_r14_stream_stack '
         '~9,000 + 8 x ot_hbm_accel_cdc_fifo_r2 30,052 (routed, hbm_accel_fmax_inventory_20261004/svc) + expert fetch '
         '(est 0.2 mm2) = 0.84 mm2 at 0.6 utilisation'),
    su=(11.96, 'measured-placed', 'N1024 SU lane array, side 3,458 um (results/rtl/dshbm_1m_allmeasured_20261004/su_n2048/'
        'wire_stages.json, from the placed MLAT4/ALAT3 lane 7,349 um2)'),
    su_fused=(3.59, 'estimate', 'L3 fused SU chains (ot_dsrom_su_norm hc/q/kv, ot_dsrom_su_swiglu, hc_post NG256): +30 % of '
              'the SU lane array for the fused per-lane registers and quant tails (no area record; su_fused/fused.json is '
              'cycles only)'),
    sfu=(8.819, 'model', 'tools/uarch_model.hbm_gpu_design(v41).dedicated_units_mm2.sfu'),
    hc=(6.087, 'model', 'hc_fp32_lanes 5.984 + sinkhorn_select_engram 0.103 (same ledger)'),
    attn_tile=(0.5, 'estimate', 'attention tile ~0.5 mm2 x 64 (hbm_accel_fmax_inventory_20261004/attn/closure.json '
               'blocker field; ledger 16.69 mm2 for the engine is smaller, the estimate is kept conservative)'),
    index=(20.57, 'model', 'tools/uarch_model.hbm_gpu_design(v41).dedicated_units_mm2.indexer (idx_array + sel + '
           'sel_cand + l20_index_topk + actquant; no HBM-die record)'),
    coll=(1.10, 'estimate', 'TU endpoint 1.1 mm2 at 70 % utilisation (hbm_accel_ha2_ar_20261004/measured_composition.json '
          'G-area); routed endpoint context noc_tw_coll_ctx_f12x 0.2916 mm2 (noc/routes/collctx_f12x_r6)'),
    cmdproc=(0.60, 'estimate', 'ot_ds_hbm_cmdproc20 static program store + pipelined issue sequencer (no area record)'),
    vm=(1.50, 'estimate', 'VM / activation-multicast root: x staging 2 x 2,048 b x 128 deep + result publication buffers '
        '(S81 VM slab 0.892 mm2 x 1.7)'),
    barrier=(0.05, 'measured-routed', 'ot_hbm_accel barrier_k32 routed (ctl_takeover_20261005, +384.3 / +39.39 ps), slot'),
    loader=(0.3321, 'measured-slot', 'ot_hbm_accel_loader_host slot 576.288^2 um (tapeout_hbm_loader_20261004; host SS '
            '-3,672 ps, not adopted)'),
    router=(0.1861, 'measured-routed', 'ot_gpu_router_topk_f topk_f3 86,102 um2 (ctl_takeover_20261005) + expert workgroup '
            'steering/descriptor logic est 0.1 mm2 (lever L1, not built)'),
    quant=(0.50, 'estimate', 'ot_hdc_actquant FP4/FP8 quantisers (index_q, chains not fused)'),
    serdes=(18.0, 'model', 'TU SerDes reservation 18 mm2 (results/floorplan/hbm_gpu/v41_hbm_die.json fabric_serdes; '
            'hbm_accel_ha2_ar 40 lanes 16.0-17.1 mm2): real ot_pdie_serdes pin macros + slab'),
    host=(10.0, 'model', 'host UCIe/PCIe reservation 10 mm2 (v41_hbm_die.json ucie_phy): real ot_pdie_ucie pin macro + slab'),
)

# ------------------------------------------------------------------------------------------------ interfaces (bits)
W_LINE = 1088 + 10 + 2          # bulk-copy line + tag + valid/ready  (DS_FETCH LINE1088/tag10)
W_REQ = 48                      # SM descriptor / request back to the stream service
W_X = 2048 + 7 + 7 + 1          # xw_data2048 / xw_addr7 / xw_grp7 / xw_en
W_RES = 256 + 12 + 1 + 1        # rdata256 / rrow12 / rv / fault
W_CTL = 13 + 16 + 8 + 1 + 2 + 1 + 4   # start/op_rows13/op_c16/op_g8/op_gs1/op_fmt2/busy/arrive/release
W_DESC = 1 + 1 + 32 + 24        # r15 sm_desc: d_valid / d_ready / d_base / d_lines (ot_hbm_accel_sm_v bulk-copy descriptor)
TU_PORTS, TU_FLIT = 8, 546      # 545-bit flit + credit, per direction
HBM_RD_BITS = S.HBM_RD_BITS
ATTN_LD = 1 + 1 + 3 + 8 + 1024 + 1   # r15 attn_rtl: ld_v / ld_mode / ld_bank / ld_grp / ld_w / ld_w2v
ATTN_Q = 1 + 3 + 576                 # iv / ibank / ib
ATTN_PKT = ATTN_LD + ATTN_Q          # 1,618: ot_attn_tile_registered_parent packet
ATTN_OUT = 1 + 512 + 16              # ov / oy / oflt
SU_IN_BITS = 4 * 8 * W_RES      # result gather trunks into the SU
CLK_BITS = 3

# ------------------------------------------------------------------------------------------------ geometry
CH = 259.2                      # SM grid channel (120 rows of 2.16)
HCH = 345.6                     # hub-band routing channel
PHY_W, PHY_H = 8500.056, 1177.2
SVC_D = 259.2
SVC_GAP = 129.6                 # r8: channel between the stream service and SM row 0 (r7 i50 residual overflow:
#                                 the abutted service N face / SM S face weight lines, y = 1.46 mm)
STRIP_D = 2000.088              # SerDes / host strip depth
SPREAD_MASTERS = {'hfd_vm', 'hfd_coll'}   # r6: the two spine blocks whose faces carry the die trunks
SPCH = 1382.4                   # r5: channels either side of the spine (r2-r4 GRT overflow at the coll / VM faces;
#                                 r3 at 691.2 um: 2,519 i5 overflow, all at the spine faces)
SCH = 345.6                     # strip-side channel (core edge to the SerDes / host strips)
SM_FACE = dict(d='S', x='W', r='E', c='N')      # sm_r2 pin regions (SM_CTX pin_regions)


def sm_dims():
    return up(SM_W, GX) - SHAVE, up(SM_H, GY) - SHAVE


class Inst(S.Inst):
    """S81 instance record with a free attribute dict (SM grid coordinates)."""


# Adopted floorplan (r14b; README round history).  Each key is a structural change, absent = the r1-r8 behaviour:
#   n_mirror_fix  N groups mirror S exactly (a 259.2 um channel between the hub band and N row 1; r1-r8 abutted them)
#   w_my          W groups mirrored (MY): every group's x face looks at the spine
#   strip_d       E host strip 2,000 -> 864 um (the host slab spans the die height): 503.7 -> 481.3 mm2
#   x_chain       x multicast enters at the column nearest the spine and chains outward
#   port_fix      shared hub masters' copies mirrored and their ports role-named (r1-r8: 128 net ends had no pin)
#   ew_corridor   SU E <-> W quarter links cross the spine through the router/cmdproc and VM/barrier gaps
#   sm_xmid       SM x / c pins centred in their pin regions (row-neutral leaves)
#   spch          spine side channels 1,382.4 -> 1,036.8 um
#   lanes         every die trunk owns a lane in the spine and hub-edge channels
#   root_pins     trunk roots leave their spine block at the face end toward their trunk
#   serdes_mg     250.56 um routing gap beside each SerDes macro's io face (was 103.68)
R14B = dict(n_mirror_fix=True, x_chain=True, w_my=True, strip_d=864.0, port_fix=True, ew_corridor=True, sm_xmid=True,
            lanes=True, spch=1036.8, root_pins=True, serdes_mg=250.56)
R10 = dict(n_mirror_fix=True, w_my=True, strip_d=864.0, x_chain=True, port_fix=True)
# r15 (CLAUDE HBM-DIE-FIX, 2026-10-06): the die-top lint defects (results/rtl/die_top_lint_20261006/findings.json H1-H13,
# TF1-TF7), fixed in the generator.  Each key is absent in r1-r14b, so --variant r14b / r8 replay those rounds exactly.
#   orient_fix  H2/TF6: flip = (side == 'N') != bool(row1_flip and row == 1).  r1-r14b evaluated (side == 'N') != None,
#               True on the S side too: all 16 S SMs were mirrored about x (d / q faced away from their stream service,
#               c away from the hub) and every r1-r14b GRT and wire price was measured with that orientation
#   clk_dom     H1/H3/H8/TF1-TF4: one PLL output port and ONE multi-load net per clock domain (stream / serial / hbm /
#               link) reaching every clocked block (all 32 SMs, 64 tiles, link macros, meso stations), plus one reset net
#               per domain (r1-r14b: N two-pin nets on the single port pll, 28 SMs and every tile unclocked, no reset)
#   sm_rtl_w    H5/TF7: weight line 1,099 b (no rsp_ready pin) and request 44 b, the ot_hbm_accel_sm_v pins
#   sm_desc     H4: the SM bulk-copy descriptor d_valid / d_ready / d_base[31:0] / d_lines[23:0] (58 b) rides the control
#               tree with start / op (control leaf 45 -> 103 b)
#   link_rtl    H6/TF5: per SerDes macro tx[486:0] + rx[486:0] = 8 TU ports x (545 flit + valid + credit) each way over 9
#               macros; host link tx[255:0] + rx[255:0] (r1-r14b: tx[511:0] + rx[458:0], host TX only)
#   coll_rtl    H9: the collective block's die ports are ot_hbm_accel_tu_endpoint's (+ the 4-quarter SU fan-in / fan-out
#               inside the block): SU quarter -> endpoint inject data 1,024; endpoint -> SU quarter delivery lane
#               545 + valid + inject index / read 34 = 580; cmdproc -> endpoint rank / pf / go 25, back fault + stall 33;
#               the r14b VM -> endpoint 512 (no RTL port) removed
#   attn_rtl    H7: attention tiles carry the ot_attn_tile_registered_parent packet (ld 1,038 + query 580 = 1,618 b) and
#               result (ov + oy 512 + oflt 16 = 529 b): query VM -> corner tile (chained), packet down the row-head column
#               and along each row, results along the row to the index quarter
#   hub_io      H10: HC -> SFU -> SU result returns, cmdproc -> barrier arrive input
#   fwd         H12a/b: forwarded-link stations carry their forwarded clocks (one fclk per 512 b slice and direction,
#               ot_fwd_link_stage) inside every chained segment; the terminal stations that hand a forwarded word to a
#               local clock region are meso stations (ot_meso_fifo W512 slices, sized into the station) on that
#               region's clock; FIFOs inside receiving hub blocks are listed in the census (area added to the ledger)
#   rq_chain    the row-1 SM request (44 b, SM -> stream service, ~2.5 mm) chained through stations (r1-r14b: one
#               unregistered die net)
#   stn_share   H13: station masters shared by role (kind, port widths, master-frame faces, size), mirrored copies
#               placed MX / MY / R180 (r1-r14b: one master per instance, 208 masters)
FIX15 = dict(orient_fix=True, clk_dom=True, sm_rtl_w=True, sm_desc=True, link_rtl=True, coll_rtl=True, attn_rtl=True,
             hub_io=True, fwd=True, rq_chain=True, stn_share=True)
ATTN_MEAS = dict(attn_tile_w_um=1349.136, attn_tile_h_um=1350.0)   # 16 m6h1 head macros (hbm_child_contract_20261005)
R15 = dict(R14B, **FIX15)
# r16e (adopted 2026-10-06): r15 with the measured attention-tile outline (64 x 1,349 x 1,350 um: the hub band grows
# 7.2 -> 12.1 mm, 481.3 -> 600.8 mm2), the spine column on a centred 7.5 mm span (the taller band otherwise spreads its
# blocks apart), a 1,400 um spine with 1,244 um side channels and a 2,000 um VM face (r16b, the same die without them:
# GRT i50 overflow 121 at the VM faces and on the N link trunks).  Variants in feasibility.json r16a-f.
R16E = dict(R15, hub_h=12100.0, spine_h=7500.0, spine_w=1399.68, spch=1244.16, face_vm=2000.0, **ATTN_MEAS)
# r16g (adopted): r16e + face_fix -- the shared tile / SU masters' role ports on fixed faces (SW frame: the tile packet
# enters from the hub edge (k, ci on S; cf on N), the query and the results on the inner face (q, o on E; i, rf on W;
# ri on E), the SU result trunk on the hub-edge face S)
R16G = dict(R16E, face_fix=True)
FACE_FIX = {('hfd_attn_tile', 'k'): 'S', ('hfd_attn_tile', 'ci'): 'S', ('hfd_attn_tile', 'cf'): 'N',
            ('hfd_attn_tile', 'q'): 'E', ('hfd_attn_tile', 'o'): 'E', ('hfd_attn_tile', 'ri'): 'E',
            ('hfd_attn_tile', 'i'): 'W', ('hfd_attn_tile', 'rf'): 'W', ('hfd_su', 'r'): 'S'}
# r16h (adopted 2026-10-06, CLAUDE HBM-ABSTRACTS as generator owner, on Turing's finite router frame
# TURING_TO_CARSON_GIBBS_KANT_CLAUDE_ROUTER_FINITE_FRAME_20261006): the router envelope grows from 133.896 to 326.280 um
# tall, [11069.136, 9338.688, 12468.792, 9664.968], taken from the loader / cmdproc gaps (each keeps 327.192 um);
# loader and cmdproc do not move.  The die's pipelined router view (ot_gpu_router_topk_ps, ~7.4k um2 placed) fits either
# envelope; the resize carries the alternative topk_f3 child frame (315.956 um square + 5 um halo).
R16H = dict(R16G, router_env=(9338.688, 326.28),
            corner_rule={m_: dict(keep=1.0, tail=8) for m_ in ('hfd_stn_r26', 'hfd_stn_r11', 'hfd_stn_r19', 'hfd_stn_r21',
                                                                'hfd_stn_r23', 'hfd_meso_r1')},
            pin_centre={('hfd_stn_r23', 'rst'): 10.0})   # rst below the widened a run (a fills the face above it)
# r8 real-abstract die pin access (DRT-0073, own-wire OBS over the corner pin): r11 a[2157], r19 a[246], r21 a[1024],
# r23 a[580], meso_r1 a[1100] join r26 under the corner rule
# corner_rule: fully packed 48 nm faces keep >= 1 um off the corner with the last 8 pins at 96 nm (only masters whose
# routed view showed M5 spacing DRC at the corner: hfd_stn_r26; r4 / r11 have the same packing and routed DRC 0)
# Generator decisions recorded in floorplan.json (generator owner CLAUDE HBM-ABSTRACTS, 2026-10-06)
DECISIONS = dict(
    item9_collective_path=('The selected native SM (ot_hbm_accel_sm_v / TU) has no O_COLL / VR path. The die collective '
                           'path is the native one: SM result gather -> SU -> TU collective endpoint (SU quarter -> '
                           'endpoint inj_data 1,024 b, endpoint -> quarter return 580 b), as coll_rtl wires it. The '
                           'original 32-caller O_COLL / B_COLL x 64 b ABI join (Dirac minimum slice) is NOT built and no '
                           'alias pins are added (decision 2026-10-06, re TURING ITEM9_ACTUAL_PORTTOP_P0 / '
                           'ITEM9_NATIVE_JOIN_DECISION).'),
    r16h_router_env=('Router envelope [11069.136, 9338.688, 12468.792, 9664.968] (326.280 um tall, from 133.896) per '
                     'TURING ROUTER_FINITE_FRAME allocation; loader / cmdproc fixed, each adjacent gap 327.192 um. The '
                     'die router view (ot_gpu_router_topk_ps PIPESEL=1, ~7.4k um2 placed) fits.'))
# r16i (2026-10-06, coordinator decision on the svc / index_q clock blocker): no multi-tap clock pins; a long master is
# split into ~1 mm segment masters (bands), each with one ck pin (a normal die clock leaf) and registered faces, at
# boundaries on existing wire-stage registers (0 cycles).  The split record (tools/hbm_die_split.py) gives every band its
# parent ports at unchanged absolute positions plus the cross buses between abutting bands; the generator replaces each
# parent instance by its bands in the same slot (mirrored with the parent) and rewires (apply_splits).
# split_lattice (r9 a_real, measured): the band origins of split.json are off the 2.16 um origin lattice, so ot_mts
# snapped them by -0.48..+0.72 um into 8 overlaps.  Each band is packed bottom-up at its own legal residue (mod 2.16, by
# orientation class) at or above the band below: the slot grows by <= ~5 um into the channel, parent pins move <= 5 um.
IDXQ_LAT = {'hfd_index_q_b1:R0': 0.27, 'hfd_index_q_b4:R0': 1.62, 'hfd_index_q_b1:MX': 1.62,
            **{f'hfd_index_q_b{i}:{c}': 0.0 for i, c in ((0, 'R0'), (2, 'R0'), (3, 'R0'), (5, 'R0'), (0, 'MX'), (2, 'MX'),
                                                       (3, 'MX'), (4, 'MX'), (5, 'MX'))}}
R16I = dict(R16H, split_masters={'hfd_index_q': 'physical/hbm_accel_die_views/index_q/split/split.json'},
            split_lattice={'hfd_index_q': IDXQ_LAT},
            spine_slots={'su_red': (1399.656, 218.136), 'su_full': (346.008, 347.736)})
# r16j (2026-10-06 18:40, OWNER: blocks <= ~1 mm hardened leaves joined by registered hops): the four stream services
# hfd_svc_{SW,SE,NW,NE} (8500 x 259 um) replaced by 8 x-band segment masters per family (svcidx split record
# svc/split/split.json, schema hbm_die_split_x.v1: SW = NW placed MX, SE = NE placed MX); band ports renamed by SM rank
# (port_map), the PHY dfi bundle split by bit range (bus endpoint 'dfi@lo:hi'), cross buses between abutting bands,
# one die clock leaf ck / rst per band.  Every other master keeps its pins.
R16J = dict(R16I, split_x_masters='physical/hbm_accel_die_views/svc/split/split.json', host_bb=True)
# r17 (2026-10-06 ~20:30, budgets coordinator: results/rtl/budgets_20261006 SUMMARY 'infeasible as planned'):
#  budget_stages: common-clock staged segments (hub nets, first / last hop of a chain) get 1 + ceil((L - 359) / 412)
#    register hops (inter reach 359 um, intra 412; at 430.56 they came out one short: su <-> router / cmdproc / vm /
#    coll / index, vm <-> router, the last hop into the SM); forwarded station segments keep 430.56 (reach 491).
#  hub_stage_all: the attention root buses tr_<q><r> (tile row -> index band, 1.7-4.5 mm) are staged paths (only the
#    farthest row of a quadrant was).
#  fwd_hub: index b5 -> VM (iv_<q>, 5.1-5.3 mm) and VM -> router (3.8 mm) cross clock regions by 198-268 / 197 ps:
#    forwarded-clock station chains (first station clocked from the source region, last station a meso FIFO into the
#    receiver's clock, endpoint pins unchanged), on new spine-side lanes 'iv' / 'rv'.
#  spine_region: loader + router + cmdproc are one clock region HUB-SP (2.6 mm) apart from HUB-C (cmdproc <-> router /
#    loader were split across HUB-C cuts at 197 ps).
#  barrier_low: the barrier (only peer: cmdproc) moved into the cmdproc / coll gap, inside HUB-SP.
#  The SM 3x3 grid (smh element) joins r17 when the SM view exports.
R17 = dict(R16J, budget_stages=True, hub_stage_all=True, fwd_hub=True, spine_region=True, barrier_low=True)
# r18 (2026-10-06 ~21:45, views agent handover): r17 + the band clock pins at the block centre (CK_CENTRE, M7 area pin)
#   + gath_r9 / stn_r19 re-read from their re-routed views (index) + fwd hub chain station directions (die_top_lint).
R18 = dict(R17, ck_centre=True)
# r19 (2026-10-06 ~23:55, coordinator decision on the views agent's hfd_vm NEEDS_BUDGET): the VM as four quadrant
#   tiles joined by registered cross buses (split_vm); +1 cycle per cross hop.
R19 = dict(R18, vm_split=True)
# r19b (2026-10-07, views agent: hfd_index_q_b5 a3 SS -222 is a budget artefact, the 4,525 um attn root path's last
#   segment into the band pin was 377 um = 644.7 ps input delay): every attention root bus tr_<q><r> (tile row -> index
#   band a0..a3) ends in a die station abutting the band pin (last segment <= 100 um), +1 register hop.
R19B = dict(R19, pin_stage_roots=True)
# Candidate only: measured VM clock entry and the real cmdproc halves. No adoption before contextual gates.
R19C = dict(R19B, vm_centre_ck=True, split_masters=dict(R19B['split_masters'],
            hfd_cmdproc='physical/hbm_accel_die_views/cmdproc/split/split.json'))
# r20 (2026-10-07, coordinator): the VM tiles' ck at the tile centre (M7 area pin, as the svc bands: SW_s1 1,304 ->
#   788 ps measured); tiles on x = 0 mod 1.728 (shift +0.432 um)
R20 = dict(R19B, vm_ck_centre=True)
# r21 (2026-10-07): a station abutting each index b5 t_vm pin (iv_pin_stn; b5 FF hold -177 infeasible on the 313 um
#   first segment)
R21 = dict(R20, iv_pin_stn=True)
# r22 (OWNER 2026-10-07 three rules): relay stations abutting every hardened-block pin of every die interface whose
#   pin segment exceeds 100 um (relay_ends, +1 cycle per relay end, priced through seg_stages); credit-based handshakes
#   on ready/valid paths with < ~200 ps internal (inventory, owners implement; 0 steady-state cycles); die area grows
#   to ~55-60 % utilisation if a round overflows on real views (current overflow = the interim attention tile chain).
R22 = dict(R21, relay_all=True)
# r23 (OWNER 2026-10-07): the hub transport gets ~2x area: SU / SFU / HC quarters x2 (registered transport tiles at
#   ~55 % utilisation for the SU / attn / router agent), SFU between its consumers SU and HC as before; the centre
#   channel (mid_ch) widens by the added quarter widths, so the die grows in x
R23 = dict(R22, hub_scale=2.0, stable_roles=True, hub_pin_window=500.0, split_stations=('hfd_mcast_r6',),
           attn_tile_w_um=1778.544, attn_tile_w0_um=1349.136, attn_grow_mid=True, serdes_w_um=2462.4, vm_cross_aligned=True,
           fix_station_pins=('hfd_cdist_r14', 'hfd_cdist_r15', 'hfd_gath_r10', 'hfd_gath_r24', 'hfd_gath_r25', 'hfd_gath_r8',
                             'hfd_gath_r9', 'hfd_meso_r28', 'hfd_meso_r32', 'hfd_stn_r2', 'hfd_stn_r34', 'hfd_stn_r18',
                             'hfd_stn_r20', 'hfd_stn_r31'))
# r23v (OWNER 2026-10-07 VM fallback, flag default OFF): R23 with the VM quadrant tiles cut into south / north sub-tiles
R23V = dict(R23, vm_split8=True)
# r24 (coordinator 2026-10-07): R23 + 8 per-segment ck pins on every hub quarter (hfd_su / hfd_sfu / hfd_hc)
R24 = dict(R23, hub_ck_seg=8)
R24P = dict(R24, hub_pin_p4=True, hub_pin_window=1200.0)   # r24 + hub quarter face buses at 4 tracks a bit (2 when
#   only that fits) in a 1,200 um window: r24 HC E face 2,048 bits in 196 um = its only GRT overflow; SU E face 9.5k bits
#   at 1 track a bit in 500 um
# Candidate only: paired half-rate DDIV64 full lane, sized by unified-model
# commit 6dc3c9707.  Reserve >=400 x 400 um on the existing macro/site lattice;
# keep the other slots and adopted floorplan unchanged.
R24F = dict(R24, spine_slots=dict(R24['spine_slots'], su_full=(400.008, 401.736)))
# Separate candidate reservation: full-width W2 credit senders own their area.
# This is an unbound floorplan slot until a measured wrapper supplies pins/RTL.
R24W = dict(R24F, spine_slots=dict(R24F['spine_slots'], w2_sender=(400.008, 401.736)),
            spine_slot_domains={'w2_sender': 'stream_1p2'})
# Geometry-only successor sized by hbm_w2_slot_model.py (ac7d9ee59).
# Logical SM identity/ports stay 4x2; physical locations become eight of nine
# 3x3 sites. Network generation is intentionally unavailable pending remapping.
# W2/HA2 partial interfaces stay inside hb_coll; the earlier R24W
# external sender reservation is historical diagnostic geometry only.
R24SM3 = dict(R24F, sm_wh=(3075.84, 1131.84), sm_physical_grid=(3, 3), side_padding_um=207.36)
# Geometry candidate only: full VM8 port/latency contract and routed closure remain gates.
R24SM3V = dict(R24SM3, vm_split8=True, vm8_nonoverlap=True, vm8_exact_pins=True)
R24SM3VO = dict(R24SM3V, native_owner_bays=True)
R24SM3VOC = dict(R24SM3VO, native_descriptor_bays=True)
R24SM3VOCE = dict(R24SM3VOC, native_control_escape_bays=True)
R24SM3VOCEU = dict(R24SM3VOCE, native_control_u_corridors=True)
R24SM3VOCEUR = dict(R24SM3VOCEU, native_result_store_bays=True)
# r25 (coordinator 2026-10-07 ~21:00, hbm-die owner decisions): r24p hub faces (4 tracks a bit, 1,200 um window) + the
#   VM quadrant cross buses on two pin layers at 2 tracks a bit + hfd_cmdproc split into its two closed halves (r19c
#   placement, both CLOSED: hfd_cmdproc_n SS +60.84 / FF +19.69, hfd_cmdproc_s).  Attention tile height 1,600.5 um is
#   R25A (adopted only if its queued route converges)
R25 = dict(R24P, vm_cross_2layer=True, hub_ports_file='physical/hbm_accel_die_views/hub_ports_r24p.json', split_masters=dict(R24P.get('split_masters', {}),
           hfd_cmdproc='physical/hbm_accel_die_views/cmdproc/split/split.json'))
# the split moves the router / loader ck and rst peer projections by < 1 um: keep the r23 positions (the router's
#   queued r23-pin re-harden and the loader route stay valid)
R25['pin_centre'] = {**R25.get('pin_centre', {}), **{(m_, p_): c_ for m_ in ('hfd_router', 'hfd_loader')
                                                     for p_, c_ in (('rst', 366.0253), ('ck', 612.5932))}}
R25A = dict(R25, attn_tile_h_um=1600.5)
# r25s (attn-split, OWNER 2026-10-08 18:10 PT; flag default OFF, r25 stays ADOPTED until both halves close): every
#   attention tile slot holds the two HALF tiles hfd_attn_half_lo / hfd_attn_half_hi (rtl/hdc/v41x/
#   ot_hdc_v41x_attn_die_half_b.sv, cut between the quad rows; pins / outlines from tools/hbm_attn_half_tile_place.py,
#   physical/hbm_attn_tile_r/half/<master>/ports.json + io_place.tcl), abutting at the seam: xp (1,619 b) and xr (272 b)
#   are die nets between face-to-face pin banks (register -> pin | pin -> register, ~0 um, no relay, no credit: no ready
#   crosses).  Slot 1778.52 x (814.32 + 673.92) = 1,488.24 um (+10.2 % vs r25's 1,349.976); the hub band grows by
#   2 x 4 x 138.264 um so the four tile rows still fit each scan quadrant (die H 25.7 mm <= 26 mm; a 1,661 um slot made
#   27.1 mm).  Zero added cycles (the halves keep hfd_attn_tile_b's port latencies).
ATTN_HALF_DIR = 'physical/hbm_attn_tile_r/half'
ATTN_HALF_OF = dict(k='lo', ks='lo', ci='lo', q='lo', ri='lo', rf='lo', rst='lo', cf='hi', i='hi', o='hi')
R25S = dict(R25, attn_split=ATTN_HALF_DIR, attn_tile_h_um=1488.24,
            hub_h=R25['hub_h'] + 2 * (4 * (1488.24 - 1349.976)) + 2 * 2.16,
            # everything else in the hub keeps its r25 size: SU / SFU / HC quarters (cq_h, at the hub edge) and their
            # widths (hub_h_ref), the index quarters (index_h: their closed split bands), the spine (spine_h, centred;
            # the router envelope moves with it)
            hub_h_ref=R25['hub_h'], cq_h=5529.6, index_h=5529.6)
# r25m (MTP-DIE 2026-10-08): r25 + the DSpark MTP master hfd_mtp in a low spine slot (see build).  Slot from the closed
# standalone routes (ctl_takeover_20261005 cell areas: topk_f3 28,799.6 + argmax_f1 6,144.3 + union_f3 3,116.3 +
# spec_f3 1,430.7 + scratch_c2 909.8 + ctl_f2 885.3 + accept_a0 290.1 + fence_a1 247.9 = 41,824 um2 of cells) at 45 %
# cell / 55 % with pin-flop banks and hold buffers: 92.9k um2 -> 466.56 x 200.88 um (0.0937 mm2), <= 1 mm a side.
MTP_SLOT = (466.56, 200.88)
# (a, b, bits): dspark_top ports.  cmdproc -> mtp: start / cfg_gamma / force / ngen / plen (37) + eng_done + sr_* spec
#   requests (54) + host token reads p_tok / f_tok (34) = 126; mtp -> cmdproc: cmd_v/op/idx/ncol/pos/tok1/toks (203) +
#   sa_* rollback addresses / n_committed (84) + p_addr / f_addr (32) + done = 320; su_red -> mtp: logit rows lg_*
#   (523: 8 lanes x FP32 value + bias, mask, last, bias_en); mtp -> coll: am_v / am_idx / am_fault for the 96-die
#   argmax select (19) + e_v / e_tok / e_idx (34) -> 64; coll -> mtp: merged argmax (64); su_red -> mtp: router vectors
#   rv_* (134); mtp -> router: t_ids / t_col (58) + union u_* (20) = 78 (the expert-fetch request rides the router's
#   expert_req chain); router -> mtp: u_ready (1) -> 8; loader -> mtp emitted-token sink is the cmdproc's.
MTP_HUB_LINKS = (('cmdproc', 'mtp', 126), ('mtp', 'cmdproc', 320), ('su_red', 'mtp', 523 + 134), ('mtp', 'coll', 64),
                 ('coll', 'mtp', 64), ('mtp', 'router', 78), ('router', 'mtp', 8))
# loader memory side widths (ot_hfd_loader_half ports): request = req_v 2 + req_we 2 + req_addr 64 + req_wdata 512 +
#   req_wstrb 64 + req_tag 32 + m_ar* 76 + m_aw* 76 + m_w* 74 + m_rready + m_bready = 904; response = rsp_v 2 + rsp_we 2 +
#   rsp_tag 32 + rsp_data 512 + req_rdy 2 + m_arready + m_r* 68 + m_awready + m_wready + m_b* 3 = 624 (per stack: the
#   loader's address decode selects the stack; ingest owns the RTL demux)
LD_MEM_NATIVE = (904, 624)
LR_DX = 420.0                   # response chain's svc-face offset from the column channel (its own station column)
LM_BUNDLES = lambda m: math.ceil(sum(m['variant']['ld_mem']) / 16)    # lane width in k16 bundles (both directions)
R25M = dict(R25, ld_mem=LD_MEM_NATIVE, split_x_new_ports={'lq': LD_MEM_NATIVE[0], 'lr': LD_MEM_NATIVE[1]}, spine_slots_low={'mtp': MTP_SLOT}, spine_slot_domains=dict(R25.get('spine_slot_domains', {}), mtp='stream_1p2'),
            # ECO pins on the closed cmdproc S half's S face (it looks at the loader and the MTP slot below): the MTP
            # command port pair; the cmdproc stream adds them (re-route of hfd_cmdproc_s, mtp-hbm / cmdproc owner)
            split_extra_ports={'hfd_cmdproc': {'t_mtp': ('hfd_cmdproc_s', 320, 'S', 'M5', 0.30, 2),
                                               'f_mtp': ('hfd_cmdproc_s', 126, 'S', 'M5', 0.70, 2)}})
# Native indexer successors remain opt-in until source joins and physical evidence close.
R25I = dict(R25, native_indexer=True, iv_pin_stn=False,
    split_x_new_ports={**{f'ki{p}':1099 for p in range(8)}, **{f'kc{p}':1 for p in range(8)}},
    split_x_new_port_band={f'{kind}{p}':p for kind in ('ki','kc') for p in range(8)})
R25IC2 = dict(R25I, indexer_large_slot=True)
R25IQ = dict(R25I,indexer_quarter_end=True)
R25IQC2 = dict(R25IQ,indexer_large_slot=True)
R25IQG = dict(R25IQ,indexer_mirror_grid=True)
R25IQGC2 = dict(R25IQG,indexer_large_slot=True)
# Actual x-controller bus facade and SRAM writeback slots. Loader stays on its
# historical base until the ND1/ADDR37 facade and service landing are qualified.
R25IMW = dict(R25IQG, native_mtp_wb=True,
    # hbm-forks 2026-10-09: the MTP slot's cmdproc command pair (t_mtp / f_mtp ECO pins on hfd_cmdproc_s) as in R25M;
    # without them `--ds-var r25imw[s]` fails in apply_splits (('hfd_cmdproc', 't_mtp'))
    split_extra_ports=R25M['split_extra_ports'],
    spine_slots_low={'mtp': MTP_SLOT, 'kvwb': (300.24, 241.92)},
    spine_slot_masters={'mtp': 'hfd_mtp_native', 'kvwb': 'hfd_kvwb_native'},
    spine_slot_domains=dict(R25IQG.get('spine_slot_domains', {}),
        mtp='stream_1p2', kvwb='stream_1p2'))
R25IMWS = dict(R25IMW, native_mtp_stop=True,
    spine_slot_masters={'mtp': 'hfd_mtp_native_stop', 'kvwb': 'hfd_kvwb_native'})
# hbm-forks 2026-10-09 (coordinator; results/arch/hbm_generic_20261009 PLAN R25G): one generic HBM die for Qwen3-8B
# and DS-V4.1 = r25s (split attention tiles) + r25m (MTP slot, loader memory ports) + r25iqg (native indexer) + the fmt3
# wide SM grid (3x3 sites, Codex qwen_r25_fmt3), with the indexer anchors rebased to the wider outline.  Candidate only.
FMT3_WIDE = dict(sm_wh=(3214.08, 1131.84), sm_physical_grid=(3, 3), side_padding_um=207.36)


def _vmerge(*vs):
    out = dict(vs[0])
    for v in vs[1:]:
        for k, x in v.items():
            if k in R25 and R25[k] == x:
                continue
            out[k] = {**out[k], **x} if isinstance(x, dict) and isinstance(out.get(k), dict) else x
    return out


R25SPS = dict(R25S, split_x_masters='physical/hbm_accel_die_views/svc/split_ps/split.json',
              attn_split='physical/hbm_attn_tile_r/half_ps', attn_entry8=True)
# hgi-takeover 2026-10-09 (die-evidence-2: closed hfd_mtp view = hfd_mtp_x_stop, 466.56 x 200.88, raw ports): the MTP
# slot's die buses are the closed view's real ports grouped by peer (hbm_mtp_native_contract.stop_model: f_cmdproc 179,
# t_cmdproc 517, f_su_red 523, f_router 59, t_router 58, t_coll 19, f_coll 1); the master hfd_mtp is the pure-wiring
# wrapper physical/hbm_accel_die_views/mtp_hfd/hfd_mtp.sv around the closed block (no re-route).  The CP-south ECO pair
# follows: t_mtp 179 (cmdproc -> mtp) / f_mtp 517 (mtp -> cmdproc) -- cmdproc_s side owned by mtp-lead (MX1 stream).
MTP_X_STOP = dict(mtp_x_stop=True,
                  split_extra_ports={'hfd_cmdproc': {'t_mtp': ('hfd_cmdproc_s', 179, 'S', 'M5', 0.30, 2),
                                                     'f_mtp': ('hfd_cmdproc_s', 517, 'S', 'M5', 0.70, 2)}})
R25G = _vmerge(R25S, R25M, R25IQG, FMT3_WIDE, dict(indexer_rebase=True, router_exact=True), MTP_X_STOP)   # router_exact: hgi-takeover die gap 1e
# hbm-forks 2026-10-09: R25G on the QUALIFIED 4 x 2 SM grid (no fmt3 wide retile): valid when the INT8 front fits the
# nominal 432-um front_c strip (route line hgi_smh_front_c_int8_nom).  787.15 mm2, 30.59 x 25.73 mm (H on the 26-mm
# axis), full network build (not a probe), margin lint PASS, SM path stages = R25S.
R25G4 = _vmerge(R25S, R25M, R25IQG, dict(indexer_rebase=True, router_exact=True), MTP_X_STOP)
R25G4T4 = dict(R25G4, indexer_t4_native=True)  # reservation only until16tap views+4joins and native endpoints qualify
# die-evidence-2 2026-10-09 18:00 PT: R25GP = R25G on the CLOSING attention / svc views: the PS halves (half_ps: PS entry
# ks port, attn_entry8) with the hi half widened to 689.04 um (hbm-forks 11c7e95b3 --hi-channel-rows 7), slot
# 814.32 + 689.04 = 1,503.36 um (+15.12 vs R25S), the hub band grown by the same 2 x 4 x 15.12 um; svc split_ps segments.
# GENERATES (hgi-takeover 2026-10-09 evening): the SE_s7 ki7 span is fixed (hbm-forks 65d804e91) and the plan record
# serialises through plan_json (tuple-keyed pin_centre); plan --ds-var r25gp: 31,734.288 x 25,282.8 um, 802.33 mm2,
# 1,245 instances, 0 overlaps / 0 outside, die lint rc 0.  (R25SPS at 1,503.36 still fails 'no room for station of ks5_SW'.)
R25GP = dict(R25G, attn_split='physical/hbm_attn_tile_r/half_ps', attn_entry8=True,
             split_x_masters='physical/hbm_accel_die_views/svc/split_ps/split.json',
             attn_tile_h_um=1503.36, hub_h=R25G['hub_h'] + 2 * 4 * (1503.36 - 1488.24))
# mtp-lead 2026-10-09: the generic die's MTP master (key mtp_master='hgi_native'; tools/hbm_mtp_native_contract.py
# generic_model).  Slot 'mtp' (MD-7 466.56 x 200.88) = hgi_mtp_native (checked CP-result DSpark controller, EXTERNAL_AM,
# no su_red logit bus) + the ARGMAX unit (hgi_dispatch 'argmax' -> block 'mtp').  The CP south band is the MX1 view
# (hfd_cmdproc_s_mtp_native_mx1: t_mtp 197 / f_mtp 517 / f_am 18 + transaction join + finite-8 emit queue), whose
# pins are its own ports.json, so the R25M 320/126 ECO pair is dropped.  Buses: cmdproc_s <-> mtp 197 / 517,
# mtp <-> router 58 / 59 (XSEL selections), mtp <-> coll 19 / 1 (expert union), coll -> cmdproc_s f_am 18 (merged
# argmax).  The MX1 host / provider / backend endpoints are NOT die buses yet (generic backend translator open):
# m['mtp_generic']['unbound'] lists them.  Default-on in R25G when the master and MX1 routes are CLOSED.
MTP_GENERIC_JOBS = ('hgi_mtp_native', 'hfd_cmdproc_s_mtp_native_mx1')


def _mtp_generic_closed():
    """True when a CLOSED closure-loop verdict exists for every MTP_GENERIC_JOBS block (results/closure_loop/*/verdict.json)."""
    seen = set()
    for f in (ROOT / 'results/closure_loop').glob('*/verdict.json'):
        name = f.parent.name
        # job names: <block>-..., <block>_<suffix>-... (e.g. hfd_cmdproc_s_mtp_native_mx1_rb-arcts-...), or dashed
        blk = next((b for b in MTP_GENERIC_JOBS if re.match(re.escape(b) + r'[-_]', name)
                    or name.startswith(b.replace('_', '-') + '-')), None)
        if blk is None:
            continue
        try:
            if json.loads(f.read_text()).get('status') == 'CLOSED':
                seen.add(blk)
        except (ValueError, OSError):
            pass
    return seen == set(MTP_GENERIC_JOBS)


def _hgi_mtp(v):
    ex = {k: dict(x) for k, x in (v.get('split_extra_ports') or {}).items()}
    for p_ in ('t_mtp', 'f_mtp'):
        ex.get('hfd_cmdproc', {}).pop(p_, None)
    from hbm_mtp_native_contract import GENERIC_MASTER, MX1_SPLIT, MX1_BAND
    return dict(v, mtp_master='hgi_native', split_extra_ports=ex,
                split_masters=dict(v.get('split_masters', {}), hfd_cmdproc=MX1_SPLIT),
                cp_band_alias={'hfd_cmdproc_s': MX1_BAND},
                # MX1 r3 pins (collar_mx1 ports.json): t_hgi_argmax 764.928-895.896 um, f_hgi_argmax 900.096-900.504 um
                # (S face, 0.192-um pitch = 4 tracks); centres / 1399.656
                cp_pin_override={'t_hgi_argmax': (0.593297, 4), 'f_hgi_argmax': (0.643229, 4)},
                hgi_dispatch=sorted(set(v.get('hgi_dispatch') or []) | {'argmax'}),
                spine_slot_masters=dict(v.get('spine_slot_masters', {}), mtp=GENERIC_MASTER),
                # two-instance MD-7 slot (466.56 x 200.88): the controller's closed view (mtp_hgi, 286.56 x 200.88) and
                # the ARGMAX unit's closed view (argmax_hgi, ot_hgi_argmax18_m 180 x 140) side by side, bottom-aligned
                spine_slot_split={'mtp': (('mtp', GENERIC_MASTER, MTP_HGI_WH), ('mtp_am', 'ot_hgi_argmax18_m', ARGMAX_HGI_WH))},
                hgi_unit_block={'argmax': 'mtp_am'})


# closed views (physical/hbm_accel_die_views/{mtp_hgi,argmax_hgi}): hgi_mtp_native-nreg-a-lvt-eaea6da41-tc TT +10.43 /
# FF +1.80; hgi_argmax18_pinsep-30853dbe1-pd55-tc-cl TT +52.2 / FF +11.54 / DRC 0
MTP_HGI_WH, ARGMAX_HGI_WH = (286.56, 200.88), (180.0, 140.0)
ARGMAX_HGI_IN = (('in_v', 1), ('in_last', 1), ('in_bias_en', 1), ('in_mask', 8), ('in_vals', 256), ('in_bias', 256))
ARGMAX_HGI_OUT = (('out_v', 1), ('out_idx', 18), ('out_nan', 1), ('fault', 1), ('out_range_fault', 1), ('out_value', 32))
R25GM = _hgi_mtp(R25G)
# hgi-takeover 2026-10-09 (hgi-e2e DIE GAP): the generic die as an HGI-1 machine on the closing views (R25GP): the single
# CP (ot_hgi_cp_die) with every record unit on a die record bus (tools/hgi_die_dispatch.py: sm / att inside the CP block,
# su / sfu / hc at the SW quarter, dma beside the loader, coll, quant, idx, argmax in the MTP slot), the HGI VM with 8
# packet clients, and the MTP slot (hgi_mtp_native + the dispatched ARGMAX unit hfd_hgi_am)
HGI_FULL = ['argmax', 'cp', 'coll', 'quant', 'idx', 'sm', 'su', 'sfu', 'att', 'dma', 'hc']
R25GPH = dict(_hgi_mtp(R25GP), hgi_dispatch=HGI_FULL, router_exact=True,
              hgi_fused=True)   # hgi-1010/c2 AUDIT N5: FUSED station in hb_quant (unit-4 record 1,216 b, 2 VM clients, kport lane)
R25GPHT4 = dict(R25GPH,indexer_t4_native=True,indexer_hgi_native=True)  # native join reservation, no closure claim
R25G4M = _hgi_mtp(R25G4)       # same on the qualified 4 x 2 SM grid (full network build)
if _mtp_generic_closed():
    R25G, R25G4 = R25GM, R25G4M
# vm8-seam 2026-10-09: R25G with the VM as the eight vertical-cut halves (vm/vcut8; VM slot and outline unchanged).
R25GV = dict(R25G, vm_split8=True, vm8_vcut=True, vm8_exact_pins=True)
ADOPTED = R25
# hbmdie-1011/rf2: textbook audit row 1 (every die segment > 504 um gets PHYSICAL relays, no budget credit) -- best
# variant: bits-scaled direction-registered stations, relay trees for multicast, block-avoiding routes, stations
# anchored to the previous node's actual box, svc -> SM channels +108 um (die 849.82 -> 856.95 mm2), hfd_hc_eng slot
# 4,600.8 -> 4,384.8 wide (E edge fixed) so the VM / hc_eng corridor is 322 um.  Not yet the default (see notes).
R25GQ_V8 = dict(   # hbm-die-iter contract v8 (10-12): the 19 hfd_hc pins the closed tiled quarter's route places (r25gqw
    # io_place / LEF: f_sfu / t_sfu 4-track at y 404 / 601, rst 801, ck<c>e M4 except c 2-3 on M6) are taken exactly; the
    # die-only HC ports (VM lane / map / cmdproc) pack around them
    anchor_ports={'hfd_hc': 'physical/hbm_accel_die_views/hcp/r25gqw/ports/hfd_hc/ports.json'}, relay_repair_rounds=20,
    # windowed GRT 10-12 (hub window 11-19 x 9-17 mm, k=16, 5 iters, epyc1tb/epyc2): die-wide M4/M5 adjustment 1.0 left
    # only pin access in the channels (2,118,679 window overflow); blocks keep M2-M5 1.0 over their outlines, channels keep
    # 0.5 of M4/M5 for PDN stripes + relay pin access -> 1,335,381 (-37 %); lane-group splits (lgE -> E + E2, W+E) were
    # +29 % and fail reach (3 lgE rdn segments 545-912 um): rejected
    grt_m45=0.5)
# hbm-die-iter contract v9 (10-12, D22): the HGI HC unit gets its own die slot hb_hgi_hc (hfd_hgi_hc = ot_hgi_hc_unit + the
# hard ot_hgi_hc_tile cluster of hbm-hcvm [hc], 656.64 x 725.76): 2,016 x 820.8 directly N of hb_sfu_SW (same x span), in
# the free band between hb_sfu_SW and hb_sfu_NW, ~1.2 mm from the VM W face (the quarter's E face was ~3.6 mm away).  The
# column under hb_hc_SW was tried first: its lgW hop ran down the 345-um HC | SU channel and failed reach (4.8 mm).  Its 10 die ports (record cmdproc 939 / 3, VM packet vmq 338 / vmr 274, aperture vmap 2,224 / 16,
# lgW client tap rdn 8,257 / wdn 65 / rup 513 / wup 8,961) move off the closed quarter, which keeps exactly its 19 ports.
# The lgW chain's third client station abuts the slot's S face, facing the SFU's N-face station (hop < 100 um).
HGI_HC_PORTS = ('f_hgi_cmdproc', 't_hgi_cmdproc', 't_hgi_vmq', 'f_hgi_vmr', 'f_hgi_vmap', 't_hgi_vmap',
                'f_lgW_rdn', 'f_lgW_wdn', 't_lgW_rup', 't_lgW_wup')
R25GQ_PR = dict(phys_free_min=0.45,  # rf2: a 100-um route cell < 45 % free (a <= 43-um abutment gap; every 84-um lk_ep channel keeps one cell >= 46 %) is a block for
                # physical-relay / clock-tree routes: no station or buffer pair fits a stage there
                pinned_faces='physical/hbm_accel_die_views/ports_r25gqn', hgi_idx_wh=(1270.08, 1719.36), spine_over_n=1836.0, phys_relays=True, relay_tree=True, phys_block_cost=400.0, svc_ch_dh=108.0, relay_repair_rounds=10,
                hc_eng=dict(name='hb_hc_eng', master='hfd_hc_eng', xy=(16794.0, 12096.0), wh=(4384.8, 1566.0)))
# hbm-phys-1010 [fp] 2026-10-10: R25GQ = the owner's Option A re-floorplan (REVIEW_20261009 'OWNER DECISION 2026-10-10'),
# the R25GP successor on the SAME outline (31,734.288 x 25,282.8 um).  Opt-in only (build_r25gq): every other variant is
# untouched.  A PLACEMENT plan: the instances are the R25GPH instances (exact measured outlines, names, masters) re-placed
# and right-sized; the die nets are NOT rebuilt here (geometry_only) -- tools/hbm_r25gq_plan.py carries the R25GPH logical
# nets over (+ the Option A additions) for the channel / stage / power model until the dependent blocks are re-routed.
#   SM 32 (3 x 3 grid, 8 per stack) | attention 32 tiles (4 x 2 per quadrant, PS halves) | SU 512 lanes (128-lane tiled
#   quarter, 128 hfd_su_tile_xl in 8 columns, slot from tools/hbm_hub_quarter_gen.py --tiled --lanes 128 --groups 4
#   --wct 456 @ dc737578e: 116.64 um column channels) | SFU half (on the SU column) | HC 4 quarters (over the index
#   stack) | index score grids 36/64 | VM8 vertical halves | spine reorder: quant | HGI VM | CP abut (shared lane group)
#   Freed height -> svc-to-SM gap (129.6 -> 345.6 um), SM row channels (520 -> 1,209.6 um, 259 -> 561.6 um) and the
#   SM-to-hub edge channel (551 -> 648 um); the inner SM column channels 259.2 -> 432 um (the outer SM column stays);
#   spine side channels 1,244.16 -> 1,546.56 um.
# loader host port h from rtl/hbm_accel/generic/loader/ot_hfd_loader_hgi.sv (origin/main 2026-10-10), host-facing ports
# (tx = loader outputs, rx = loader inputs): s_* AXI-lite slave 37 / 65, h_* AXI-lite master 65 / 37, h_dma_* 74 / 205,
# m_* host-memory AXI master 228 / 74, irq + fault 2 / 0  ->  406 / 381 (R25GPH: 256 / 256, short 150 / 125)
HOST_H_HGI = (37 + 65 + 74 + 228 + 2, 65 + 37 + 205 + 74 + 0)
R25GQ = dict(r25gq=True, r25gq_base='r25gph', host_h=HOST_H_HGI,
             # [idx] lead decisions 10-10 (claude/hbmphys-idx-20261010 d578aa824): the index_q bands go; attention row
             # outputs reach the SU over 60 hfd_att_su_relay stations (8 tr_<q><r> buses, 529 b); index score grids are
             # the 12-lane hfd_idx_score_native_g12 slot 2,000.16 x 2,646
             att_su_relays='physical/hbm_accel_die_views/att_su_relay/relays_r25gq.json',
             idx_score_slot=('hfd_idx_score_native_g12', 2646.0),
             svc_gap_add=216.0, sm_colch_add=172.8, sm_ch01=1209.6, sm_ch12=561.6, hub_edge_ch=648.0, eq_ch=518.4,
             su_slot=(2016.144, 2808.0), sfu_frac=0.5, hc_mm2=550.8 * 5529.6 / 1e6, idx_score_frac=36 / 64,
             attn_rows=2, attn_cols=4, attn_col_gap=259.2, attn_row_gap=345.6, hub_col_gap=345.6,
             # hbmdie-1011 (main 10-11: taller attention halves, not M8): lo 1,024.92 / hi 867.24 (tile 1,892.16, +25.9 %)
             # grown into the empty band between the S and N row pairs; die height / hub blocks unchanged
             attn_tall='physical/hbm_attn_tile_r/half_v10', attn_tall_corridor=108.0,   # attn v10 (9170f7d5e): lo 1,263.6 / hi 689.04
             # (tile 1,952.64): the 4 rows take 1,797 of the 1,918 um band; the ~121 um central corridor holds only the E host
             # wire chain (stations <= 67 um); die routes cross the tiles on M8 / M9. face_coll 1,560 (el1011-hbm-coll: 9 tiles +
             # core SRAMs, hierarchical hfd_coll): the spine stack re-gaps evenly (cross gap loader -> coll 302.4 kept)
             coll_h=1560.0,
             hc_wh=(2263.68, 1499.04), hc_col_w=2032.944,    # hbmdie-1011 contract v6: the CLOSED tiled hfd_hc quarter (88
             # hfd_hc_tile_xl 8 x 11, pka10 view; r25gqw ports, E-face pins +230.736) -- the die adapts to the closed element.
             # Wider than its column, it keeps its SU-facing edge (ix_x + hc_col_w, the v1 slot's) and grows AWAY from the
             # spine into the HC | attention channel (345.6 -> 114.96 um); the v1 2,032.944 x 1,684.8 taller slot is retired
             phys_trees=True,
             pg_m8_masters=(),   # hbmdie-1011 contract v1 (layer rule: M8/M9 die top only): the hfd_hc quarter cluster takes M7 PG
             # stripes (its tiles PG M6 / signals <= M6, quarter straps M7), die joins M7-M8 like every block; 7c875ca6c's M8 PG path kept off.   # conservative-1011 a0bda978e: tiled hfd_hc PG pins on M8 (die M9 straps join by via89)      # hbmdie-1011 textbook audit rows 2-3: regional pipelined reset tree + clock H-tree per domain
             # (phys_relays, row 1, stays OFF: fully physical relaying of the hub's wide buses does not fit this
             # floorplan's channels -- relays reach 64.5 % of a 2 x 2 mm hub cell; needs the row-4 re-floorplan)
             idx_cols=((0, 1, 2), (3, 4, 5)), idx_col_gap=172.8, idx_gap=43.2, hc_gap=172.8, sfu_gap=216.0,
             idx_score_dx=432.0, spine_over=864.0, spch_q=1546.56,
             # hgi-1010/b lane groups (ot_hgi_vm_lanearb ace618cd8): VM | CP | quant abut, the W group leaves the VM's W face
             # for the SW quarter (SU -> SFU -> HC), the E group its E face up the E spine channel past CP and quant
             # lead 10-10 (IDX.INDEX selector path): the native selector abuts hgi_idx (its t_sel / f_sel ports: fs, qb,
             # kin, toc, coc down, qbr, to, co, ev back), so no ready crosses a relay chain; the score grids stay N / S
             # [link] / hgi-1010/c RGX (hgi_rgx): coll gains the row-gather lanes to the loader (~1.25 kb) and the VM
             # packet + W2 wide-write client to hgi_vm (~9.6 kb): coll moves between the loader and hgi_vm (abutting
             # hgi_vm) so those buses are face to face; router moves north of barrier
             # audit 10-10 (N12 / N15 / N16): hb_barrier, hb_su_red, hb_su_full (no RTL / no function on the HGI die) are
             # gone, with the legacy cmdproc <-> SU / coll / barrier buses and the stale ARGMAX out_* -> hfd_vm_se net
             # + hb_router: its outputs were folded and its MTP links dropped (N14), HGI expert selection is IDX.TOPK
             spine_order=('hgi_idx', 'idx_sel', 'mtp', 'loader', 'coll', 'hgi_vm', 'cmdproc', 'quant', 'vm8'),
             drop_blocks=('hb_barrier', 'hb_su_red', 'hb_su_full', 'hb_router'),
             drop_buses=r'hb_(cmdproc_coll|coll_cmdproc|barrier_cmdproc|cmdproc_barrier|cmdproc_su_[NS][EW]|su_red_am_\w+|am_vm_\w+'
                        r'|router_mtp|mtp_router|mtp_coll|coll_mtp)|hgi_vmw_dma(_done)?',     # + N14 DROP (d98cc3409); vmw_dma
                                                                                    # re-staged below at 8,992 / 32
             # [svc] N8 / N9 10-10 (shared-ks): the svc key rows ks<k> feed the score grid too (no ki pins / chains)
             shared_ks=dict(family={'hfd_svc_SW': 'SW', 'hfd_svc_NW': 'SW', 'hfd_svc_SE': 'SE', 'hfd_svc_NE': 'SE'},
                            band=dict(SW=(0, 0, 1, 2, 3, 5, 6, 7), SE=(0, 0, 1, 2, 3, 4, 5, 7))),
             hgi_rgx=True, del_obase=True,
             # [svc-ep] 10-10: PS native-endpoint chains (+~320 b every cut, worst ~2,830 b) at <= 55 % cut use on the
             # strip's 10.3 b/um (M4 / M6 alternate, 0.096 um a bit): 2,830 / 0.55 / 10.3 = 500 um (was 259.176)
             svc_h=500.04, split_x_new_port_band=dict(lq=3, lr=3),
             svc_split='physical/hbm_accel_die_views/svc/split_psn/split.json',
             vmr2_dma=True, ctl_leaf_w=112, vmap=True, att_e2=True, vmw_dma=True,   # e2: CP ATT KV STREAM issuer -> svc s3     # N4: SM control leaf 103 -> 112 b
             # [cg-hc] 10-10 decision (A): HC row roots ck<c>e / ck<c>w (8 -> 16 pins), E on M6 (the E data band is M4)
             hc_ck_ew=((93.708, 281.1, 468.492, 655.884, 843.18, 1030.572, 1217.964, 1405.356), tuple(range(8))),
             # hgi-1010/b 10-10: hfd_hc_eng (FUSED HC_POST + HC_PRE_NORM, ~4-5 mm2 of cells) at ~50 %: 6,069.6 x 1,490.4 um in
             # the E hub centre band (the freed column under HC is crossed by the attention -> SU row buses: 2.5 mm2 free)
             # lead 10-11 (b): the die widens 1,250 um E of x 16,700 (31.73 -> 32.98 mm, reticle 33): hc_eng sits in the
             # E centre band beside the spine (between the SE / NE SFU halves), within ~3 relays of the VM's lgE chain
             col_split=(16700.0, 1250.0),
             hc_eng=dict(name='hb_hc_eng', master='hfd_hc_eng', xy=(16578.0, 12096.0), wh=(4600.8, 1566.0)),      # hgi-1010/c: loader dma_vr2q / dma_vr2r <-> VM read group 2 (DS MTP swapout 8.7k -> 3.5k cycles)
             # hgi-1010/b 10-10: a larger hgi_vm outline, single-layer faces at every other track (<= 10.4 b/um)
             hgi_vm_w=2073.6, hgi_vm_h=2073.6,
             lane_chain_nets=(('rdn', 8259), ('wdn', 67), ('rup', 515), ('wup', 8963)),
             dense_face_masters=('hfd_loader', 'hfd_coll', 'hfd_hgi_vm', 'hfd_su', 'hfd_sfu', 'hfd_hc', 'hfd_quant',
                                 'hfd_hc_eng', 'hfd_stn_lgW0', 'hfd_stn_lgW1', 'hfd_stn_lgW2', 'hfd_stn_lgE0', 'hfd_stn_lgE1', 'hfd_stn_lgE2', 'hfd_stn_lgE3',
                                 'hfd_meso_r28', 'hfd_meso_r47', 'hfd_stn_r27', 'hfd_stn_r29'),   # + the widened flit-chain stations
             spine_abut=(('hgi_idx', 'idx_sel'), ('coll', 'hgi_vm'), ('hgi_vm', 'cmdproc')),
             spine_cross=(('loader', 'coll'), ('quant', 'vm8')), spine_cross_um=302.4,
             lane_groups=dict(W=('hb_hgi_vm', 'hb_su_SW', 'hb_sfu_SW', 'hb_hc_SW'), E=('hb_hgi_vm', 'hb_cmdproc', 'hb_quant')),
             lane_rd_bits=8800, lane_wr_bits=9000,
             face_force={('hfd_hgi_vm', 't_lgW'): 'W', ('hfd_hgi_vm', 't_lgE'): 'E',     # clients' taps: by peer
                         ('hfd_loader', 't_dma_vr2q'): 'N', ('hfd_loader', 'f_dma_vr2r'): 'N',   # loader's long face
                         ('hfd_loader', 't_hgi_vmw'): 'N', ('hfd_loader', 'f_hgi_vmw'): 'N'},
             # [fp]/[sfu] decision (a) 10-10: the W lane-group trunk (17,800 b) does not pass through hfd_sfu (its slot
             # has no free M1-M7 corridor and the 17,800-pin windows were 20.8 b/um/layer).  The trunk runs SU (N face)
             # -> a client-station relay bank hfd_stn_lgW in the SFU | HC gap -> HC (E face); hfd_sfu keeps a narrow
             # W-face client tap: f_lgW 273 b (read data in) + t_lgW 280 b (write data out) = 553 b, placeholder widths
             # until hgi-1010/b posts the ot_hgi_vm_lanearb client width.
             # lead 10-10 decision (b): a per-link endpoint hfd_lk_ep beside every SerDes (PHY lane packer moved out of
             # hfd_coll + ot_hbm_link_retry_pipeline 690 x 460 um); the llk die nets become the TU flit bus, each way
             # {valid, flit 545, credit} + a fault bit = 1,095 b (+ 2 forwarded clocks), was 976 b of gearboxed lanes
             # [link] 10-10 (a81f05080): NS = 3 retry macros 690 x 460 um + FMT1 gearbox / CRC / queues: 2 x 2 macro block
             # (one corner = logic) 1,728 x 1,015.2 um (1.754 mm2, [link] floorplan lint: 1.49 mm2 was 64.6 % util); flit bus {v, flit 545, credit} each way = 1,094 b + session 24
             # down + {fault, locked} up = 1,120 b; PHY side
             # tx[486:0] out + rx[486:0] in = 974 b, the die's SerDes lane contract (H6 link_rtl: 8 TU ports x 547 b a
             # direction over 9 links); 1,024 b does not fit the SerDes face in the k = 16 GRT bundling
             link_ep=dict(wh=(1728.0, 1015.2), gap=43.2, flit_bits=1120, phy_bits=974),
             # hbmdie-1011 contract v2 (granted 10-11): hfd_lk_ep = 3-tile cluster 2,600 x 830 (was 1,728 x 1,015.2)
             # hbmdie-1011 contract v5 (D16, 10-11): the S row of 5 in one 13,504-um gap between sm7 and sm14 left only
             # 84-um inter-slot channels for every N-S crossing (8 clock/reset tree segments > 504 um, far-side relays).
             # S becomes a 3 + 2 brick in the free band y 6,016-7,977 under SU/hgi_idx: row 1 (y 6,016) A1 / A2 / A3,
             # row 2 (y 7,046) B1 over A1 and B2 over A3; channels >= 200 um (A1-A2 1,014, A2-A3 2,170 over the SerDes,
             # rows 200, B2-hgi_idx 200, sm7-A1 400); per-slot (x, y) in SerDes x order S0..S4
             link_ep_v2=dict(wh=(2600.0, 830.0), xy=dict(S=((7886.0, 6016.0), (7886.0, 7046.0), (11500.0, 6016.0),
                                                           (16270.0, 6016.0), (16270.0, 7046.0)),
                                                       N=((9984.0, 12668.0, 15352.0, 18036.0), 18919.0))),
             lane_bypass=dict(W=dict(client='hb_sfu_SW', after='hb_su_SW', toward='hb_hc_SW', stn='hb_stn_lgW',
                                     master='hfd_stn_lgW', w=43.2, tap_rd=273, tap_wr=280)),
             # lead 10-10: no lane-group pass-through in any block: lgW = VM -> stations abutting the SU (E face, SU =
             # client slot 0), SFU (N face), HC (N face); lgE = VM -> a station abutting quant's S face (cmdproc was only
             # a pass-through: off the chain).  Taps at full width (b: ot_hgi_vm_lanestation local side)
             lane_stations=dict(
                 W=dict(src='hb_hgi_vm', thick=64.8, gap=21.6, align=dict(hb_stn_lgW_su='top'),
                        stations=(('hb_stn_lgW_su', 'hb_su_SW', 'E', 2073.6), ('hb_stn_lgW_sfu', 'hb_sfu_SW', 'N', 2073.6),
                                  ('hb_stn_lgW_hc', 'hb_hc_SW', 'N', 2073.6))),
                 # lgE KE = 4 (hgi-1010/b): slots CP 0 / ATT 1 / quant 2 / HC_ENG 3; chain in geometric order VM -> HC_ENG
                 # (beside the VM) -> CP (cmdproc E face) -> quant (S face) -> ATT (cmdproc W face: the ATT staging
                 # client sits with the ATT record adapter in the CP block; the attention band is >= 6 mm away)
                 E=dict(src='hb_hgi_vm', thick=64.8, gap=21.6,
                        stations=(('hb_stn_lgE_hce', 'hb_hc_eng', 'N', 3024.0), ('hb_stn_lgE_cp', 'hb_cmdproc', 'N', 2073.6, 'cp'),
                                  ('hb_stn_lgE_q', 'hb_quant', 'S', 2073.6), ('hb_stn_lgE_att', 'hb_cmdproc', 'W', 1360.8, 'att')))),
             lane_tap_nets=(('rdn', 8257), ('wdn', 65), ('rup', 513), ('wup', 8961)),
             lane_chain_nets_E=(('rdn', 8260), ('wdn', 68), ('rup', 516), ('wup', 8964)))   # lgE KE = 4 bundles


def build_r25gq(variant):
    """R25GQ placement (see R25GQ above).  Returns a geometry-only model (buses / paths empty) with m['base'] = the
    R25GPH network-probe model the instances were taken from, and m['r25gq_map'] = base instance -> R25GQ instance (None
    when the instance is gone: the merged attention tiles map onto their surviving row)."""
    V = dict(variant)
    base = build(variant_arg(V['r25gq_base']), network_probe=True)
    g0 = base['geo']
    W, H = g0['W'], g0['H']
    B = {it.name: it for it in base['insts']}
    svc_d = 0.0
    if V.get('svc_h'):      # R25GQ 10-10 ([svc-ep] PS native endpoint chains): taller svc strips, S and N; the die grows
        h0_ = {round(it.h, 3) for it in base['insts'] if it.kind == 'svc'}
        assert len(h0_) == 1, h0_
        svc_d = round(V['svc_h'] - h0_.pop(), 4)
        H = round(H + 2 * svc_d, 4)
    if V.get('hgi_vm_h') and 'hb_hgi_vm' in B:      # R25GQ 10-10: a larger VM slot for its 19-20 k pins a face
        B['hb_hgi_vm'].h = V['hgi_vm_h']
        if V.get('hgi_vm_w'):       # wider than the spine column: centred on it, overhanging both side channels
            B['hb_hgi_vm'].x = dn(B['hb_hgi_vm'].x + B['hb_hgi_vm'].w / 2 - V['hgi_vm_w'] / 2, GX)
            B['hb_hgi_vm'].w = V['hgi_vm_w']
    if V.get('svc_ch_dh'):      # hbmdie-1011/rf2: the svc -> SM channel (S and N) grows by svc_ch_dh for the physical
        # relay stations (it was the saturated channel); the die grows 2 x svc_ch_dh in y, the hub band is unchanged
        H = round(H + 2 * V['svc_ch_dh'], 4)
        V['svc_gap_add'] = V.get('svc_gap_add', 0.0) + V['svc_ch_dh']
    cx = g0['cx']
    insts, regions, notes, rmap = [], [], [], {}

    def add(name, src, x, y, w=None, h=None, master=None, orient=None, kind=None, region=None):
        s = B[src]
        it = Inst(name, master or s.master, round(x, 6), round(y, 6), round(w if w is not None else s.w, 6),
                  round(h if h is not None else s.h, 6), orient or s.orient, kind=kind or s.kind, region=region or s.region,
                  domain=s.domain)
        insts.append(it)
        return it

    def mx(x, w):          # mirror about the spine centre (E half)
        return round(2 * cx - x - w, 6)

    def my(y, h):          # mirror about the die centre (N half)
        return round(H - y - h, 6)
    # ---- side bands: PHY / svc / SerDes / host unchanged; SM rows re-pitched (S side; N mirrored)
    for it in base['insts']:
        if it.kind in ('phy', 'svc', 'link', 'serdes_slab', 'host_slab'):
            n_ = it.y + it.h / 2 > g0['H'] / 2
            cd_ = V.get('svc_ch_dh', 0.0)     # rf2: N half +2cd, centre band +cd (S fixed)
            if it.kind == 'svc':
                add(it.name, it.name, it.x, it.y + (svc_d + 2 * cd_ if n_ else 0.0), h=it.h + svc_d)
            else:       # N half +2d, S half fixed, a band across the centre (host) +d
                add(it.name, it.name, it.x, it.y + (2 * (svc_d + cd_) if it.y > g0['H'] / 2 else 0.0
                                                    if it.y + it.h < g0['H'] / 2 else svc_d + cd_))
            rmap[it.name] = it.name
    sms = [it for it in base['insts'] if it.kind == 'sm']
    smh = sms[0].h
    ys = sorted({round(it.y, 3) for it in sms if it.y < H / 2})
    assert len(ys) == 3, ys
    row_y = [up(ys[0] + V.get('svc_gap_add', 0.0) + svc_d, GY)]
    row_y.append(up(row_y[0] + smh + V['sm_ch01'], GY))
    row_y.append(up(row_y[1] + smh + V['sm_ch12'], GY))
    colx = {}
    for st in ('SW', 'SE', 'NW', 'NE'):       # inner SM column channels widened: the outer column stays, the inner
        xs_ = sorted({round(i.x, 3) for i in sms if i.region == f'grp_{st}'}, reverse=st[1] == 'E')   # ones move spineward
        for k, x_ in enumerate(xs_):
            colx[(st, x_)] = x_ + (k * V.get('sm_colch_add', 0.0) * (1 if st[1] == 'W' else -1))
    for it in sms:
        s_ = it.y < H / 2
        yr_ = it.y if s_ else g0['H'] - it.y - it.h      # the N groups sit 2.16 um off the exact mirror (GY snap)
        r_ = min(range(3), key=lambda k: abs(ys[k] - yr_))
        add(it.name, it.name, colx[(it.region[4:], round(it.x, 3))], row_y[r_] if s_ else my(row_y[r_], it.h), region=it.region)
        rmap[it.name] = it.name
    hb0 = up(row_y[2] + smh + V['hub_edge_ch'], GY)     # first hub block row (S); N mirrored
    hb1 = my(hb0, 0.0)
    hmid = (hb0 + hb1) / 2
    qh = dn((hb1 - hb0 - V['eq_ch']) / 2, GY)
    geo = dict(W=W, H=H, x0=g0['x0'], cx=cx, hub_blocks_y=(hb0, hb1), quadrant_h=qh, sm_row_y=row_y,
               side_h=dn(hb0 - V['hub_edge_ch'], GY))
    # ---- index score grids: 36/64 height, shifted outward (the SM group east strip 264 -> ~950 um)
    for q in ('SW', 'SE', 'NW', 'NE'):
        s = B[f'idx_score_{q}']
        h_ = up(s.h * V['idx_score_frac'], GY) if not V.get('idx_score_slot') else V['idx_score_slot'][1]
        x_ = s.x + V['idx_score_dx'] if q[1] == 'W' else s.x - V['idx_score_dx']
        y_ = s.y if q[0] == 'S' else s.y + s.h - h_
        if V.get('idx_score_box'):      # hbmdie 10-14 v13: native IDX leaf+macro area 38.169 mm2 vs 4 x 5.292 slots
            ib_ = V['idx_score_box']    # (lower bound, no glue): each scorer takes its corner band (bottom edge kept)
            y_ = dn(ib_['y'][q], GY) if q in (ib_.get('y') or {}) else y_
            add(s.name, s.name, dn(ib_['x'].get(q, ib_['x'][q[1]]), GX), y_, w=up(ib_['w'], GX), h=up(ib_['h'], GY),
                master=V['idx_score_slot'][0] if V.get('idx_score_slot') else None)
            rmap[s.name] = s.name
            continue
        add(s.name, s.name, x_, y_, h=h_,
            master=V['idx_score_slot'][0] if V.get('idx_score_slot') else None)
        rmap[s.name] = s.name
    # ---- spine column: re-stacked (quant | HGI VM | CP abutting), VM8 halves, centred on the hub band
    sx0 = B['hb_cmdproc'].x
    sw = B['hb_cmdproc'].w
    vm8 = []
    for q in ('sw', 'se', 'nw', 'ne'):
        s = B[f'hb_vm_{q}']
        hw = dn(s.w / 2, GX)
        for k, h_ in enumerate('we'):
            vm8.append((f'hb_vm_{q}{h_}', s.name, s.x + k * hw, hw, f'hfd_vm_{q}{h_}'))
    stack = dict(hgi_idx=['hb_hgi_idx'], mtp=['hb_mtp', 'hb_mtp_am'], loader=['hb_loader'], router=['hb_router'],
                 quant=['hb_quant'], hgi_vm=['hb_hgi_vm'], cmdproc=['hb_cmdproc'], barrier=['hb_barrier'], coll=['hb_coll'],
                 vm8=['hb_vm_sw', 'hb_vm_nw'], su_red=['hb_su_red'], su_full=['hb_su_full'], idx_sel=['idx_selector'])
    hgt = {k: (B[v[0]].h if k != 'vm8' else B['hb_vm_sw'].h + B['hb_vm_nw'].h) for k, v in stack.items()}
    if V.get('coll_h'):          # hbmdie-1011: hierarchical hfd_coll slot height (el1011-hbm-coll), the stack re-gaps evenly
        hgt['coll'] = up(V['coll_h'], GY)
    if V.get('quant_h'):         # contract v12: hfd_quant grows for the QDQ cluster (622.08 x 596.16); the preset takes the
        hgt['quant'] = up(V['quant_h'], GY)     # same height out of the hgi_vm void, so only cmdproc + quant's S edge move
    if V.get('hgi_idx_wh'):      # hbmdie-1011 contract v3: hfd_hgi_idx holds the hgi_idx_topk_w8 CLUSTER (w8 hub 1,250 x 520,
        # 4 + 4 heap tiles 260 x 260 abutted N / S, seams <= 410 um) beside the existing hgi_idx logic: taller slot in the
        # spine column, still abutting its native selector (idx_sel follows it at 43.2 um)
        hgt['hgi_idx'] = up(V['hgi_idx_wh'][1], GY)
    order = V['spine_order']
    pairs = list(zip(order, order[1:]))
    gap = {p: 43.2 for p in pairs if p in V['spine_abut']}
    gap.update({p: V['spine_cross_um'] for p in pairs if p in V['spine_cross']})
    y_lo, y_hi = hb0 - V['spine_over'], hb1 + V.get('spine_over_n', V['spine_over'])   # rf2: N-only extension (the S end is the lk_ep row)
    free = (y_hi - y_lo) - sum(hgt.values()) - sum(gap.values())
    rest = [p for p in pairs if p not in gap]
    g_ = dn(free / len(rest), GY)
    assert g_ >= 43.2, ('spine column too short', g_)
    gap.update({p: g_ for p in rest})
    yy = up(y_lo, GY)
    spine_y = {}
    for k in order:
        spine_y[k] = yy
        if k == 'vm8':
            for nm, src, x_, w_, mst in vm8:
                lo = src.endswith(('sw', 'se'))
                add(nm, src, x_, yy if lo else yy + B['hb_vm_sw'].h, w=w_, master=mst)
                rmap.setdefault(src, nm)
        else:
            for nm in stack[k]:
                s = B[nm]
                if nm == 'hb_hgi_idx' and V.get('hgi_idx_wh'):
                    w_i = up(V['hgi_idx_wh'][0], GX)
                    assert w_i <= sw, ('hgi_idx slot wider than the spine column', w_i, sw)
                    add(nm, nm, dn(sx0 + (sw - w_i) / 2, GX), yy, w=w_i, h=hgt['hgi_idx'])
                else:
                    add(nm, nm, s.x, yy, **({'h': hgt['coll']} if nm == 'hb_coll' and V.get('coll_h') else
                                            {'h': hgt['quant']} if nm == 'hb_quant' and V.get('quant_h') else {}))
                rmap[nm] = nm
        yy = up(yy + hgt[k] + (gap[(k, order[order.index(k) + 1])] if k != order[-1] else 0.0), GY)
    assert yy <= y_hi + GY, ('spine overflows', yy, y_hi)
    regions.append(dict(name='spine', kind='hub', rect=[sx0, y_lo, sx0 + sw, y_hi]))
    # ---- hub quadrants (S built, N mirrored in y; E mirrored about the spine centre)
    spch = V.get('spch_q', base['geo']['spch'])
    geo['spch'] = spch
    su_w, su_h = V['su_slot']
    su_x = dn(sx0 - spch - su_w, GX)
    ix_w = 2 * B['hb_index_SW_b0'].w + V['idx_col_gap']
    if V.get('hc_wh'):      # hbmdie-1011: explicit hfd_hc quarter outline (conservative-1011 tiled quarter, 88
        # hfd_hc_tile_xl at ~55 %).  The column cannot widen (W slack 18.6 um to the die edge channel) but the R25GQ HC
        # column is empty below the HC (the index stack left it), so the quarter grows in HEIGHT, its equator-side edge fixed
        assert V.get('att_su_relays'), 'hc_wh needs the R25GQ hub (no index stack in the HC column)'
        # contract v6: a quarter wider than the column overhangs it on the attention side (one row-1 station + 2 x 20 um left)
        assert V['hc_wh'][0] - ix_w <= V['hub_col_gap'] - 43.2 - 2 * 20.0, ('HC overhang closes the channel', V['hc_wh'][0], ix_w)
    ix_x = dn(su_x - V['hub_col_gap'] - ix_w, GX)
    tw = B['at_SW_00_lo'].w
    at_w = V['attn_cols'] * tw + (V['attn_cols'] - 1) * V['attn_col_gap']
    at_x = dn(ix_x - V['hub_col_gap'] - at_w, GX)
    assert at_x >= g0['x0'] + HCH / 2, ('W hub quadrant overflows', at_x)
    th_lo, th_hi = B['at_SW_00_lo'].h, B['at_SW_00_hi'].h
    tp = th_lo + th_hi
    at_h = V['attn_rows'] * tp + (V['attn_rows'] - 1) * V['attn_row_gap']
    assert at_h <= qh, ('attention rows do not fit the quadrant', at_h, qh)
    at_h0 = at_h
    if V.get('attn_tall'):      # hbmdie-1011 (main 10-11: taller attention halves, M8 / M9 stay die-only): the halves take
        # the attn_tall records' outlines; the S row pair keeps its bottom edge and grows UP into the empty band between
        # the S and N pairs (N mirrored: grows DOWN), so the die height and the hub blocks do not move
        recs_t = {h: json.loads((ROOT / V['attn_tall'] / f'hfd_attn_half_{h}/ports.json').read_text()) for h in ('lo', 'hi')}
        assert abs(recs_t['lo']['w_um'] - tw) < 1e-6 and abs(recs_t['hi']['w_um'] - B['at_SW_00_hi'].w) < 1e-6, 'widths change'
        th_lo, th_hi = recs_t['lo']['h_um'], recs_t['hi']['h_um']
        tp = th_lo + th_hi
        at_h = V['attn_rows'] * tp + (V['attn_rows'] - 1) * V['attn_row_gap']
    sfu_h = up(B['hb_sfu_SW'].w * B['hb_sfu_SW'].h * V['sfu_frac'] / su_w + V.get('sfu_h_add', 0.0), GY)
    hc_h = up(V['hc_wh'][1], GY) if V.get('hc_wh') else up(V['hc_mm2'] * 1e6 / ix_w, GY)
    assert su_h + V['sfu_gap'] + sfu_h <= qh, ('SU + SFU column overflows', su_h + V['sfu_gap'] + sfu_h, qh)
    for q in ('SW', 'SE', 'NW', 'NE'):
        S_, E_ = q[0] == 'S', q[1] == 'E'

        def put(name, src, x, y, w, h, master=None, kind=None):
            xx = mx(x, w) if E_ else x
            yy_ = y if S_ else my(y, h)
            o = B[src.replace('SW', q)].orient if src.replace('SW', q) in B else B[src].orient
            return add(name, src.replace('SW', q) if src.replace('SW', q) in B else src, xx, yy_, w=w, h=h, master=master,
                       orient=o, kind=kind, region='hub')
        qy = hb0
        put(f'hb_su_{q}', 'hb_su_SW', su_x, qy, su_w, su_h)
        put(f'hb_sfu_{q}', 'hb_sfu_SW', su_x, up(qy + su_h + V['sfu_gap'], GY), su_w, sfu_h)
        rmap[f'hb_su_{q}'], rmap[f'hb_sfu_{q}'] = f'hb_su_{q}', f'hb_sfu_{q}'
        ytop = qy
        for c_, col in enumerate(V['idx_cols'] if not V.get('att_su_relays') else ()):
            y_ = qy
            for b_ in col:
                s = B[f'hb_index_SW_b{b_}']
                put(f'hb_index_{q}_b{b_}', f'hb_index_SW_b{b_}', ix_x + c_ * (s.w + V['idx_col_gap']), y_, s.w, s.h)
                rmap[f'hb_index_{q}_b{b_}'] = f'hb_index_{q}_b{b_}'
                y_ = up(y_ + s.h + V['idx_gap'], GY)
            ytop = max(ytop, y_ - V['idx_gap'])
        if V.get('att_su_relays'):       # HC stays where it sat over the R25GQ index stack ([idx]: 'HC stays')
            for col in V['idx_cols']:
                y_ = qy
                for b_ in col:
                    y_ = up(y_ + B[f'hb_index_SW_b{b_}'].h + V['idx_gap'], GY)
                ytop = max(ytop, y_ - V['idx_gap'])
        hc_y = up(ytop + V['hc_gap'], GY)
        if V.get('hc_wh'):      # equator-side edge where the ledger-sized quarter had it; grow away from the equator
            hc_y = min(dn(hc_y + up(V['hc_mm2'] * 1e6 / ix_w, GY) - hc_h, GY), dn(qy + qh - hc_h, GY))
            assert hc_y >= qy, ('taller HC leaves its column', hc_y, qy)
        assert hc_y + hc_h <= qy + qh, ('HC over the index stack overflows', hc_y + hc_h, qy + qh)
        hc_w = V['hc_wh'][0] if V.get('hc_wh') else ix_w
        # v6: the SU-facing edge stays where the v1 slot had it (ix_x + hc_col_w): the mirrored E copies keep their 0.432-grid
        # origin, the W copies land on the 0.048 track grid (as the v1 slot's E edge did)
        hc_x = ix_x if hc_w <= ix_w + 1e-6 else round(ix_x + V.get('hc_col_w', ix_w) - hc_w, 6)
        it_hc_ = put(f'hb_hc_{q}', 'hb_hc_SW', hc_x, hc_y, hc_w, hc_h)
        if (V.get('hc_orient') or {}).get(q):     # contract v10: ONE hfd_hc master -> its tap face maps to every station
            it_hc_.orient = V['hc_orient'][q]
        if V.get('hc_track_origins'):
            # Actual ASAP7 site/track intersection (OpenROAD HC-only readback).
            # Preserve the closed geometry; make the model use the placed origin.
            phase = 0.216 if it_hc_.orient == 'MY' else 0.0
            it_hc_.x = round(phase + math.floor((it_hc_.x - phase) / 0.432 + 0.5) * 0.432, 6)
            it_hc_.y = round(math.floor(it_hc_.y / 8.64 + 0.5 - 1e-9) * 8.64, 6)
        rmap[f'hb_hc_{q}'] = f'hb_hc_{q}'
        ty0 = up(qy + (qh - at_h0) / 2, GY)
        if V.get('attn_tall'):      # S top below the die equator with half the >= 346 um central corridor
            corr_ = H / 2 - (hb0 + ty0 - qy + at_h)
            assert 2 * corr_ >= V.get('attn_tall_corridor', 345.6) - 1e-6, ('taller attention rows close the corridor', 2 * corr_)
        for r in range(V['attn_rows']):
            for c in range(V['attn_cols']):
                # S: row 0 at the hub edge; N (mirrored): row 0 at the equator, as the R25GP grid (MX copies)
                rr = r if S_ else V['attn_rows'] - 1 - r
                y_ = ty0 + rr * (tp + V['attn_row_gap'])
                # W: column 0 outermost; E mirrored (the base grid's column 0 is the outermost on both halves)
                # E quadrants name-mirrored ([idx] 10-10): the R25GP E tile chains run c3 -> c0, so column 0 (the chain
                # root) sits next to the SU on both halves
                x_ = at_x + ((V['attn_cols'] - 1 - c) if E_ else c) * (tw + V['attn_col_gap'])
                lo_y, hi_y = y_, y_ + th_lo      # N: mirrored below, hi under lo as the R25GP MX copies
                for half, yh, hh_ in (('lo', lo_y, th_lo), ('hi', hi_y, th_hi)):
                    nm = f'at_{q}_{r}{c}_{half}'
                    xx = mx(x_, tw) if E_ else x_
                    yy_ = yh if S_ else my(yh, hh_)
                    add(nm, f'at_{q}_00_{half}', xx, yy_, h=(hh_ if V.get('attn_tall') else None), kind='attn_tile',
                        region='hub')
    # attention: base rows r (0..3) and columns c map onto R25GQ row r // 2 (the merged pair's work runs on one tile)
    for nm in B:
        m_ = re.fullmatch(r'at_([NS][EW])_(\d)(\d)_(lo|hi)', nm)
        if m_:
            q, r, c, h_ = m_.groups()
            rmap[nm] = f'at_{q}_{int(r) * V["attn_rows"] // 4}{c}_{h_}'
    for q in ('SW', 'SE', 'NW', 'NE'):     # quadrant regions: attention outer edge .. spine face
        xa, xb = (at_x, sx0) if q[1] == 'W' else (sx0 + sw, 2 * cx - at_x)
        y0_, y1_ = (hb0, hb0 + qh) if q[0] == 'S' else (hb1 - qh, hb1)
        regions.append(dict(name=f'quad_{q}', kind='hub', rect=[round(xa, 3), round(y0_, 3), round(xb, 3), round(y1_, 3)]))
    for st, grp in base['groups'].items():
        S_ = st[0] == 'S'
        y0_ = row_y[0] if S_ else my(row_y[2], smh)
        y1_ = row_y[2] + smh if S_ else my(row_y[0], smh) + smh
        ga_ = 2 * V.get('sm_colch_add', 0.0)
        xa_, xb_ = (grp['x'], grp['x'] + g0['grp_w'] + ga_) if st[1] == 'W' else (grp['x'] - ga_, grp['x'] + g0['grp_w'])
        regions.append(dict(name=f'grp_{st}', kind='field', rect=[xa_, y0_, xb_, y1_]))
    regions.append(dict(name='hub', kind='hub', rect=[g0['x0'], hb0, g0['x0'] + g0['core_w'], hb1]))
    if V.get('att_su_relays'):
        rl_ = json.loads((ROOT / V['att_su_relays']).read_text())['relays']
        rby_ = {q_['name']: q_ for q_ in rl_}
        for r_ in rl_:
            y_r = r_['y'] + V.get('svc_ch_dh', 0.0)    # rf2: the hub band moves up by svc_ch_dh
            if V.get('hc_wh') and re.fullmatch(r'rly_N[WE]_1_\d+', r_['name']):
                # hbmdie-1011: the N tr row-1 chain runs just above the N HC quarter; the taller quarter pushes the whole
                # row (all 8 stations, so every hop keeps its length but the tile -> first relay hop) up by the growth
                y_r = round(y_r + up(V['hc_wh'][1], GY) - up(V['hc_mm2'] * 1e6 / (2 * B['hb_index_SW_b0'].w + V['idx_col_gap']), GY), 6)
            x_r = r_['x']
            if V.get('hc_wh') and V['hc_wh'][0] > 2 * B['hb_index_SW_b0'].w + V['idx_col_gap'] + 1e-6 and \
                    re.fullmatch(r'rly_N[WE]_1_1', r_['name']):
                # contract v6: the wider N HC quarter takes the channel column this station sat in; it moves to the centre
                # of the narrowed HC | attention channel, at the height that balances its hops 1_0 -> 1_1 -> 1_2 (<= 504 um)
                hq_ = next(i for i in insts if i.name == f"hb_hc_N{r_['name'][5]}")
                at_ = [i for i in insts if i.kind == 'attn_tile' and i.name.startswith(f"at_N{r_['name'][5]}")]
                if r_['name'][5] == 'W':
                    c0_, c1_ = max(i.x + i.w for i in at_ if i.x < hq_.x), hq_.x
                else:
                    c0_, c1_ = hq_.x + hq_.w, min(i.x for i in at_ if i.x > hq_.x)
                assert c1_ - c0_ >= r_['w'] + 40.0, ('HC | attention channel too narrow for the row-1 station', c0_, c1_)
                x_r = round(dn((c0_ + c1_ - r_['w']) / 2, GX), 6)
                p0_, p2_ = rby_[r_['name'][:-1] + '0'], rby_[r_['name'][:-1] + '2']     # same y shift as this station
                y0_, y2_ = p0_['y'] + y_r - r_['y'], p2_['y'] + y_r - r_['y']
                y_r = round(up((y0_ + y2_ + abs(p2_['x'] - x_r) - abs(x_r - p0_['x'])) / 2, GY), 6)
                h0_, h2_ = abs(x_r - p0_['x']) + abs(y_r - y0_), abs(p2_['x'] - x_r) + abs(y2_ - y_r)
                assert max(h0_, h2_) <= 504.0, ('row-1 station hops over reach', r_['name'], h0_, h2_)
            insts.append(Inst(r_['name'], r_['master'], x_r, y_r, r_['w'], r_['h'], r_['orient'], kind='waypoint',
                              region='channel', domain='stream_1p2'))
    notes.append(f'R25GQ: SM rows at {row_y} (S), hub blocks {hb0:.2f}-{hb1:.2f} um, quadrant {qh:.2f} um; spine gap '
                 f'{g_:.2f} um (+ abut 43.2 / cross {V["spine_cross_um"]})')
    if V.get('col_split'):      # lead 10-11 decision (b): the die widens in x; everything E of `cut` moves E by dx, which
        cut_, dx_ = V['col_split']  # opens the E centre band beside the spine for hfd_hc_eng (lgE <= 8 relays)
        for it_ in insts:
            if it_.x >= cut_:
                it_.x = round(it_.x + dx_, 6)
        for r_ in regions:
            x0_, y0_, x1_, y1_ = r_['rect']
            r_['rect'] = [x0_ + (dx_ if x0_ >= cut_ else 0.0), y0_, x1_ + (dx_ if x1_ > cut_ else 0.0), y1_]
        W = round(W + dx_, 6)
        geo['W'] = W
    V.update(W=W, H=H)
    m = dict(geo=geo, insts=insts, regions=regions, groups={}, hub={}, tiles=[i for i in insts if i.kind == 'attn_tile'],
             scan={}, links=[i for i in insts if i.kind == 'link'], host=next(i for i in insts if i.name == 'lk_host'),
             notes=notes, variant=V, stn_faces={}, buses=[], paths={}, geometry_only=True, base=base, r25gq_map=rmap)
    m['notes'].append('Placement plan only: die nets are the R25GPH logical nets carried over by tools/hbm_r25gq_plan.py '
                      '(model); the dependent blocks are re-routed after the plan is on main.')
    return m


def build_r25gq_net(variant):
    """R25GQ DIE NETWORK (opt-in preset r25gqn) by transplant: the R25GPH network (same buses, ports, masters, relay
    chain topology; the loader host port at host_h) on the R25GQ placement.
      * blocks move to their R25GQ sites (the VM keeps its four R25GPH quads on the VM8 footprint: the vcut8 seam is
        inside the footprint); SU / SFU / HC take their R25GQ outlines (generated abstracts, the R24P frozen quarter pin
        file is dropped because those faces changed);
      * attention: the R25GPH tiles of rows 0 / 1 are the R25GQ tiles (same names); rows 2 / 3 and every bus end on them
        are removed, relay waypoints left serving only them are pruned;
      * every relay waypoint is re-placed on the R25GQ grid-router path (tools/hbm_r25gq_plan.py) between the two
        terminals it sat between, at its R25GPH fraction of that path, then legalised off the blocks;
      * the Option A nets (VM lane groups A / B, CP <-> MTP f_mtp / t_mtp, ATT records) are added as staged chains.
    The SM result-pin bays move with their SM."""
    import hbm_r25gq_plan as RP
    V = dict(variant)
    _T0 = time.time()
    geo_m = build_r25gq(dict(V, r25gq_net=False))
    bv = dict(variant_arg(V['r25gq_base']), host_h=V['host_h'], hub_ports_file=None, hgi_rgx=V.get('hgi_rgx'),
              del_obase=V.get('del_obase'))
    if V.get('split_x_new_port_band'):      # [svc-ep] 10-10: lq / lr on band 3 of every svc stack
        bv['split_x_new_port_band'] = dict(bv.get('split_x_new_port_band') or {}, **V['split_x_new_port_band'])
    if V.get('ctl_leaf_w'):
        bv['ctl_leaf_w'] = V['ctl_leaf_w']
    if V.get('sm_native_abi'):
        bv['sm_native_abi'] = True
    if V.get('dense_face_masters'):     # dense faces are spread whole: no fixed ck / rst centres inside them
        bv['pin_centre'] = {k_: v_ for k_, v_ in (bv.get('pin_centre') or {}).items() if k_[0] not in V['dense_face_masters']}
    if V.get('svc_split'):      # [svc-ep] 10-10: the native-endpoint segment records (split_psn, h = 500.04): lq / lr / kc
        bv['split_x_masters'] = V['svc_split']    # are pinned in the band records themselves (no ECO new ports)
        bv['split_x_new_ports'] = {k_: v_ for k_, v_ in (bv.get('split_x_new_ports') or {}).items()
                                   if not re.fullmatch(r'lq|lr|kc\d', k_)}
    if V.get('dbk_wd'):         # contract v12: DMA BACK write lanes (ECO pins wd / wdc on svc band 3, as lq / lr)
        bv['dbk_wd'] = tuple(V['dbk_wd'])
        bv['split_x_new_ports'] = dict(bv.get('split_x_new_ports') or {}, wd=V['dbk_wd'][0], wdc=V['dbk_wd'][1])
        bv['split_x_new_port_band'] = dict(bv.get('split_x_new_port_band') or {}, wd=3, wdc=3)
    if V.get('shared_ks'):      # [svc] N8 10-10 (shared-ks): no ki pins; kc<k> lands on the band that drives ks<k>
        bv['shared_ks'] = V['shared_ks']
        bv['split_x_new_port_band'] = dict(bv.get('split_x_new_port_band') or {},
                                           **{f'kc{k_}': {par_: V['shared_ks']['band'][fam_][k_]
                                                          for par_, fam_ in V['shared_ks']['family'].items()}
                                              for k_ in range(8)})
    base = build(bv, network_probe=True)
    if V.get('attn_tall'):      # hbmdie-1011: the taller halves' pin plans (N-face pins at the new top edge)
        attn_half_fixed_ports(base, V['attn_tall'])
    Q = {it.name: it for it in geo_m['insts']}
    kind = {it.name: it.kind for it in base['insts']}
    gone = {n for n in kind if re.fullmatch(r'at_[NS][EW]_[23]\d_(lo|hi)', n)}
    if V.get('att_su_relays'):          # [idx] the index_q bands and every die net on them go
        gone |= {n for n in kind if re.fullmatch(r'hb_index_[NS][EW]_b\d', n)}
    gone |= set(V.get('drop_blocks') or ())
    # ---- blocks to their R25GQ sites
    insts, moved = [], {}
    for it in base['insts']:
        if it.kind == 'waypoint' or it.name in gone:
            continue
        q = Q.get(it.name)
        if q is None and it.name.startswith('hb_vm_'):
            q0 = Q[it.name + 'w']
            q = Inst(it.name, it.master, q0.x, q0.y, it.w, it.h, it.orient)
        assert q is not None, ('no R25GQ site', it.name)
        moved[it.name] = (q.x - it.x, q.y - it.y)
        it.x, it.y, it.w, it.h, it.orient = q.x, q.y, q.w, q.h, q.orient
        insts.append(it)
    if V.get('block_xy'):       # contract v14 (owner 10-14 P2P step 1): blocks re-sited by absolute origin (the VM8 union
        # into the centre spine void); the closed tiles of a moved block move with it (child slots are block-relative)
        byn_ = {i.name: i for i in insts}
        for n_, xy_ in V['block_xy'].items():
            it_ = byn_[n_]
            it_.x, it_.y = round(xy_[0], 6), round(xy_[1], 6)     # exact (a whole-row GY shift keeps the union's seams)
        for n_ in V['block_xy']:
            bx_ = byn_[n_].box()
            hh_ = [i.name for i in insts if i.name not in V['block_xy'] and i.kind != 'waypoint'
                   and bx_[0] - 40 < i.x + i.w and i.x < bx_[2] + 40 and bx_[1] - 40 < i.y + i.h and i.y < bx_[3] + 40]
            assert not hh_, ('re-sited block overlaps / closer than 40 um', n_, hh_)
    if V.get('att_su_relays'):          # the att -> SU relay stations sit at their [idx] positions
        insts += [i for i in geo_m['insts'] if i.master == 'hfd_att_su_relay']
    if V.get('hc_eng'):         # hgi-1010/b 10-10: the FUSED one-pass HC_POST + HC_PRE_NORM engine (~4-5 mm2 of cells,
        he_ = V['hc_eng']       # ~50 % density): the largest free hub area, the E centre band (lgE client after quant)
        hce_ = Inst(he_['name'], he_['master'], dn(he_['xy'][0], GX), dn(he_['xy'][1] + V.get('svc_ch_dh', 0.0), GY), up(he_['wh'][0], GX),
                    up(he_['wh'][1], GY), 'R0', kind='hub', region='hub')
        bx_ = hce_.box()
        hh_ = [i.name for i in insts if i.kind != 'waypoint' and bx_[0] - 100 < i.x + i.w and i.x < bx_[2] + 100
               and bx_[1] - 100 < i.y + i.h and i.y < bx_[3] + 100]
        assert not hh_, ('hc_eng slot overlaps', hh_)
        insts.append(hce_)
    vb2_ = V.get('vm_b2') or {}
    if vb2_:    # hbm-b2 10-12 (owner B2: compute next to its data, no central hub): the central hb_hgi_vm (32 banks,
        # 2.07 x 2.07 mm, ~62 kb of wide ports on the spine) becomes 4 quadrant slices hb_vms_<q> (8 banks / 8 lanes +
        # mirror window, ot_hgi_vm_unit NB=8), each beside its quadrant's SU | SFU column; slices talk over a 2 x 2
        # credit ring (results/arch/hbm_b2_1012/SPEC.md)
        for q_, (x_, y_) in vb2_['xy'].items():
            sl_ = Inst(f'hb_vms_{q_}', f'hfd_hgi_vms_{q_}', dn(x_, GX), dn(y_, GY), up(vb2_['wh'][0], GX), up(vb2_['wh'][1], GY), 'R0',
                       kind='hub', region='hub')
            bx_ = sl_.box()
            hh_ = [i.name for i in insts if i.kind != 'waypoint' and bx_[0] - 100 < i.x + i.w and i.x < bx_[2] + 100
                   and bx_[1] - 100 < i.y + i.h and i.y < bx_[3] + 100]
            assert not hh_, ('vm slice overlaps', q_, hh_)
            insts.append(sl_)
    if V.get('hgi_hc_slot'):    # hbm-die-iter D22 (contract v9): the HGI HC unit (ot_hgi_hc_unit + its hard hc tile
        # cluster, hbm-hcvm [hc]) is its own die slot.  The closed hfd_hc quarter (cons B, 88 hfd_hc_tile_xl) has only its
        # 19 ports (sfu / ck / rst); the unit's record (cmdproc 939 / 3), VM packet (vmq 338 / vmr 274), aperture (vmap
        # 2,224 / 16) and lgW client tap (17.8 kb) land here, N of hb_sfu_SW (the lgW client after the SFU)
        hs_ = V['hgi_hc_slot']
        hgh_ = Inst(hs_['name'], hs_['master'], dn(hs_['xy'][0], GX), dn(hs_['xy'][1], GY), up(hs_['wh'][0], GX),
                    up(hs_['wh'][1], GY), 'R0', kind='hub', region='hub')
        bx_ = hgh_.box()
        hh_ = [i.name for i in insts if i.kind != 'waypoint' and bx_[0] - 100 < i.x + i.w and i.x < bx_[2] + 100
               and bx_[1] - 100 < i.y + i.h and i.y < bx_[3] + 100]
        assert not hh_, ('hgi_hc slot overlaps', hh_)
        insts.append(hgh_)
    for ds_ in V.get('die_slots') or ():
        # contract v12: die-level slots granted to closed / in-flight leaves and chains that have no block of their own
        # in the R25GQ record (the collective TKM chain, the per-cluster DMA BACK); real blocks: obstacles, pins, clock
        it_ = Inst(ds_['name'], ds_['master'], dn(ds_['xy'][0], GX), dn(ds_['xy'][1], GY), up(ds_['wh'][0], GX),
                   up(ds_['wh'][1], GY), ds_.get('orient', 'R0'), kind='hub', region='hub')
        bx_, cl_ = it_.box(), ds_.get('clear', 20.0)
        hh_ = [i.name for i in insts if i.kind != 'waypoint' and bx_[0] - cl_ < i.x + i.w and i.x < bx_[2] + cl_
               and bx_[1] - cl_ < i.y + i.h and i.y < bx_[3] + cl_]
        assert not hh_, ('die slot overlaps / closer than its clearance', ds_['name'], hh_)
        insts.append(it_)
    ep_of = {}
    if V.get('link_ep') and V.get('link_ep_v2'):
        V['link_ep'] = dict(V['link_ep'], **V['link_ep_v2'])
    if V.get('link_ep'):    # lead 10-10 decision (b): a link endpoint slot beside every SerDes (packer + retry)
        ew, eh = V['link_ep']['wh']
        for grp in ('S', 'N'):
            sds = sorted((i for i in insts if i.master == 'ot_pdie_serdes' and re.fullmatch(f'lk_{grp}\\d', i.name)),
                         key=lambda i: i.x)
            if not sds:
                continue
            tot = len(sds) * ew + (len(sds) - 1) * V['link_ep']['gap']
            cx = sum(i.x + i.w / 2 for i in sds) / len(sds)
            x0 = dn(cx - tot / 2, GX)
            y0 = up(max(i.y + i.h for i in sds) + V['link_ep']['gap'], GY) if grp == 'S' else \
                dn(min(i.y for i in sds) - V['link_ep']['gap'] - eh, GY)
            sp_ = [i for i in insts if i.kind == 'spine' and i.y < y0 + eh and y0 < i.y + i.h]
            if sp_:     # the band would cross the spine column (spine_over reaches it): split it around the column
                cx0_, cx1_ = min(i.x for i in sp_), max(i.x + i.w for i in sp_)
                nl_ = (len(sds) + 1) // 2
                xs_ = [cx0_ - V['link_ep']['gap'] - (nl_ - k) * (ew + V['link_ep']['gap']) + V['link_ep']['gap']
                       for k in range(nl_)] + [cx1_ + V['link_ep']['gap'] + k * (ew + V['link_ep']['gap'])
                                               for k in range(len(sds) - nl_)]
            else:
                xs_ = [x0 + k * (ew + V['link_ep']['gap']) for k in range(len(sds))]
            if V['link_ep'].get('xy'):      # hbmdie-1011 contract v2 grant: hfd_lk_ep 3-tile cluster 2,600 x 830, fixed
                # slots (S row bottom 6,016, N row top kept at 19,749), in serdes x order
                g_ = V['link_ep']['xy'][grp]
                if isinstance(g_[1], (int, float)):     # (xs, y): one row
                    xs_, y0 = g_
                    ys_ = [y0] * len(xs_)
                else:                                   # v5: per-slot (x, y) (the S 3 + 2 brick)
                    xs_, ys_ = [p_[0] for p_ in g_], [p_[1] for p_ in g_]
                ys_ = [y_ + (2 * V.get('svc_ch_dh', 0.0) if grp == 'N' else 0.0) for y_ in ys_]   # rf2: N rides the N half
                assert len(xs_) == len(sds), ('link_ep grant / serdes count', grp, len(xs_), len(sds))
            else:
                ys_ = [y0] * len(xs_)
            for k, sd in enumerate(sds):
                ep = Inst(f'ep_{sd.name[3:]}', 'hfd_lk_ep', dn(xs_[k], GX), ys_[k], ew, eh,
                          'R0' if grp == 'S' else 'MX', kind='hub', region='hub')
                bx = ep.box()
                hit_ = [i.name for i in insts if i.kind != 'waypoint' and bx[0] < i.x + i.w and i.x < bx[2]
                        and bx[1] < i.y + i.h and i.y < bx[3]]
                assert not hit_, ('link endpoint slot overlaps', ep.name, hit_)
                insts.append(ep)
                ep_of[sd.name] = ep.name
    if vb2_:
        slc_ = {q_: by_i.box() for q_ in vb2_['xy'] for by_i in insts if by_i.name == f'hb_vms_{q_}'}
        cen_ = lambda b: ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
        bpos_ = {it.name: cen_(it.box()) for it in base['insts']}
        bpos_.update({it.name: cen_(it.box()) for it in insts})

        def b2_retarget(bid, cls, eps):
            """hb_hgi_vm ends -> the slice nearest the bus's other end (clock / reset: every slice); the loader's quadrant
            memory ports lq_<q> / lr_<q> -> slice q (per-quadrant loader inside the slice tile)"""
            m_ = re.fullmatch(r'l[qr]_(SW|SE|NW|NE)\w*', bid)
            if m_:
                return [(f'hb_vms_{m_.group(1)}', e[1]) if e[0] == 'hb_loader' else e for e in eps]
            m_ = re.fullmatch(r'l([wx])_(SW|SE|NW|NE)\w*', bid)
            if m_:      # contract v12: the DMA BACK write lanes end on the cluster's hb_dbk_<q> (one master: one port name)
                return [(f'hb_dbk_{m_.group(2)}', 't_wd' if m_.group(1) == 'w' else 'f_wdc') if e[0] == 'hb_loader' else e
                        for e in eps]
            if not any(e[0] == 'hb_hgi_vm' for e in eps):
                return eps
            if cls.startswith(('clock', 'reset')):
                return [e for e in eps if e[0] != 'hb_hgi_vm'] + [(f'hb_vms_{q_}', e[1]) for e in eps if e[0] == 'hb_hgi_vm'
                                                                   for q_ in slc_]
            oth_ = [bpos_[e[0]] for e in eps if e[0] != 'hb_hgi_vm' and e[0] in bpos_]
            if not oth_:
                return eps
            ox_, oy_ = oth_[0]
            q_ = min(slc_, key=lambda q: abs(cen_(slc_[q])[0] - ox_) + abs(cen_(slc_[q])[1] - oy_))
            return [(f'hb_vms_{q_}', e[1]) if e[0] == 'hb_hgi_vm' else e for e in eps]
    # ---- buses: drop removed-tile ends, then prune waypoints that serve nothing
    buses = []
    for bid, cls, bits, eps in base['buses']:
        if V.get('drop_buses') and re.fullmatch(V['drop_buses'], bid):
            continue
        if V.get('ck_root'):    # contract v14: the PLL / POR ports leave hb_coll for the die clock root block
            eps = [(V['ck_root'], e[1]) if e[0] == 'hb_coll' and re.fullmatch(r'(pll|por)_\w+', e[1]) else e
                   for e in eps]
        if vb2_:
            eps = b2_retarget(bid, cls, eps)
        eps2 = [e for e in eps if e[0] not in gone]
        if len(eps2) >= 2 or (cls.startswith(('clock', 'reset')) and eps2):
            buses.append((bid, cls, bits, eps2))
    while True:
        deg = defaultdict(int)
        for bid, cls, bits, eps in buses:
            if cls.startswith(('clock', 'reset', 'strap')):
                continue
            for e in eps:
                deg[e[0]] += 1
        leaf = {n for n, d_ in deg.items() if kind.get(n) == 'waypoint' and d_ <= 1}
        if not leaf:
            break
        buses = [(b_, c_, w_, [e for e in eps if e[0] not in leaf]) for b_, c_, w_, eps in buses]
        buses = [b for b in buses if len(b[3]) >= 2 or (b[1].startswith(('clock', 'reset')) and b[3])]
        gone |= leaf
    if V.get('p2p'):    # contract v14: a dropped chain's relays are on no DATA bus any more: they go, and leave the
        # clock / reset trees they were sinks of (v14 check: 70+ orphan lk_lk stations kept only by clk_link / rst_link)
        used_ = {e[0] for b_ in buses if not b_[1].startswith(('clock', 'reset')) for e in b_[3]}
        orph_ = {n for n, k_ in kind.items() if k_ == 'waypoint' and n not in used_}
        gone |= orph_
        buses = [(b_, c_, w_, [e for e in eps if e[0] not in orph_]) for b_, c_, w_, eps in buses]
        buses = [b for b in buses if len(b[3]) >= 2 or (b[1].startswith(('clock', 'reset')) and b[3])]
    # ---- waypoints onto the R25GQ router paths
    wps = {it.name: it for it in base['insts'] if it.kind == 'waypoint' and it.name not in gone}
    adj = defaultdict(set)
    for bid, cls, bits, eps in buses:
        if cls.startswith(('clock', 'reset', 'strap')):
            continue
        ns = [e[0] for e in eps]
        for a in ns:
            for b in ns:
                if a != b:
                    adj[a].add(b)
    B0 = {it.name: it for it in build(bv, network_probe=True)['insts']}       # R25GPH positions
    if vb2_:    # the slices replace hb_hgi_vm in the R25GPH network the waypoints were built on
        B0.update({f'hb_vms_{q_}': B0['hb_hgi_vm'] for q_ in vb2_['xy']})
    B0.update({ds_['name']: B0[ds_['base_as']] for ds_ in V.get('die_slots') or () if ds_.get('base_as')})
    c0 = lambda n: (B0[n].x + B0[n].w / 2, B0[n].y + B0[n].h / 2)
    probe = dict(geo_m, insts=insts)
    G = RP.Grid(probe)
    rings, pcache = {}, {}
    # rf2: with physical relays every route that carries stations avoids long block crossings (phys_block_cost)
    # v13 window congestion (tools/hbm_r25gq_windows.py --cost-out): a (ny, nx) route-cell cost from the window check of
    # the previous build of this preset (demand / tracks per 2-D window, history-summed).  Every chain / relay /
    # pin-repair route pays it, so the buses that only PASS THROUGH a hot window (v12: the N link chains, the TKM stream
    # and the NW lane group through x 12-15 / y 14-17 mm) take the emptier channels; a bus that ends there cannot.
    CG_ = 0.0
    if V.get('cong'):
        import numpy as _npc
        CG_ = _npc.load(ROOT / V['cong'])
        assert CG_.shape == (G.ny, G.nx), ('window congestion cost is not on this die\'s route grid', CG_.shape, (G.ny, G.nx))
    A = G.graph(1.0 + (V.get('phys_block_cost') or RP.BLOCK_COST) * G.blocked + CG_)
    from scipy.sparse.csgraph import dijkstra as _dj

    spt_ = {}

    def gpath(a, b):
        if (a, b) not in pcache:
            ra = rings.setdefault(a, G.ring(a))
            rb = rings.setdefault(b, G.ring(b))
            if a not in spt_:       # hbmdie-1011/rf: one shortest-path tree per source (multicast loads share prefixes)
                spt_[a] = _dj(A, indices=ra, min_only=True, return_predecessors=True)[:2]
            d_, pr_ = spt_[a]
            k_ = min(rb, key=lambda x: d_[x])
            pth = [k_]
            while pr_[pth[-1]] >= 0:
                pth.append(pr_[pth[-1]])
            pcache[(a, b)] = pth[::-1]
        return pcache[(a, b)]

    # hbmdie-1011/rf2: physical-relay routes avoid crossing blocks (a relay cannot sit inside a block, so a crossing
    # longer than one stage cannot be relayed): blocked cells cost PHYS_BLOCK_COST per 100-um cell, so a route detours
    # through the channels unless the crossing is short
    A_p, spt_p, pcache_p = None, {}, {}

    # v13 r8 PRESENT congestion (V['cong_present'] = (gain, u0)): the relay routes are made one bus after another on
    # ONE cost, so every chain between two regions took the same shortest corridor (v12 / v13: five N link chains, the
    # TKM stream, the ring and the x-load buses all in the 386-um gap W of hb_cmdproc -> the die GRT's hot window)
    # while the 1.3-mm gap E of it stayed empty.  Each routed bus now adds its bits to the route cells it crosses
    # (PC_['use']); a cell's cost grows with use / tracks (one direction's die tracks through a 100-um cell: M8 / M9
    # over a block, + M4-M7 x their GRT share in the open) above u0, and the graph is rebuilt between buses.  The
    # buses that are already within reach when the relay passes start are counted first (pc_seed).
    PC_ = dict(use=None, n=0, built=0, key=None, seen=set(), extra=0.0)
    if V.get('cong_present'):
        import numpy as _npp
        PC_['use'] = _npp.zeros((G.ny, G.nx))
        PC_['cap'] = RP.CELL * (9.68 + 25.26 * _npp.clip(G.free, 0.0, 1.0))
        PC_['gain'], PC_['u0'] = V['cong_present']

    def pc_cost():
        if PC_['use'] is None:
            return 0.0
        return PC_['gain'] * _npp.minimum(4.0, _npp.maximum(0.0, PC_['use'] / PC_['cap'] - PC_['u0']) / (1.0 - PC_['u0']))

    def pc_add(cells, bits, key=None):
        """count `bits` on the route cells (flat indices) once per key"""
        if PC_['use'] is None or not bits:
            return
        if key is not None and key != PC_['key']:
            PC_['key'], PC_['seen'] = key, set()
        uf_ = PC_['use'].reshape(-1)
        for k_ in cells:
            if key is None or k_ not in PC_['seen']:
                uf_[k_] += bits
                if key is not None:
                    PC_['seen'].add(k_)
        PC_['n'] += 1

    def pc_seg(p_, q_, bits, w_=0.5):
        """count a pin-to-pin hop as its two L shapes, half the bits each"""
        if PC_['use'] is None or not bits:
            return
        ci_ = lambda v_, n_: min(n_ - 1, max(0, int(v_ // RP.CELL)))
        i0, i1 = sorted((ci_(p_[0], G.nx), ci_(q_[0], G.nx)))
        j0, j1 = sorted((ci_(p_[1], G.ny), ci_(q_[1], G.ny)))
        for jj_ in {ci_(p_[1], G.ny), ci_(q_[1], G.ny)} if i1 > i0 else ():
            PC_['use'][jj_, i0:i1 + 1] += bits * w_ * (2 if j0 == j1 else 1)
        for ii_ in {ci_(p_[0], G.nx), ci_(q_[0], G.nx)} if j1 > j0 else ():
            PC_['use'][j0:j1 + 1, ii_] += bits * w_ * (2 if i0 == i1 else 1)
        PC_['n'] += 1

    def gpath_p(a, b, bits=0, key=None):
        nonlocal A_p
        if not V.get('phys_block_cost'):
            return gpath(a, b)
        if PC_['use'] is None:
            bits, key = 0, None
        if A_p is None or (bits and key != PC_['key'] and PC_['n'] - PC_['built'] >= 6):
            A_p = G.graph(1.0 + V['phys_block_cost'] * (G.free < V.get('phys_free_min', 0.2)) + CG_ + PC_['extra'] + pc_cost())
            spt_p.clear()
            PC_['built'] = PC_['n']
        if bits:        # a counted bus: its own route on the cost as it stands (the same bus asks again: same route)
            if (a, b, key) not in pcache_p:
                ra = rings.setdefault(a, G.ring(a))
                rb = rings.setdefault(b, G.ring(b))
                if a not in spt_p:
                    spt_p[a] = _dj(A_p, indices=ra, min_only=True, return_predecessors=True)[:2]
                d_, pr_ = spt_p[a]
                k_ = min(rb, key=lambda x: d_[x])
                pth = [k_]
                while pr_[pth[-1]] >= 0:
                    pth.append(pr_[pth[-1]])
                pcache_p[(a, b, key)] = pth[::-1]
                pc_add(pth, bits, key)
            return pcache_p[(a, b, key)]
        if (a, b) not in pcache_p:
            ra = rings.setdefault(a, G.ring(a))
            rb = rings.setdefault(b, G.ring(b))
            if a not in spt_p:
                spt_p[a] = _dj(A_p, indices=ra, min_only=True, return_predecessors=True)[:2]
            d_, pr_ = spt_p[a]
            k_ = min(rb, key=lambda x: d_[x])
            pth = [k_]
            while pr_[pth[-1]] >= 0:
                pth.append(pr_[pth[-1]])
            pcache_p[(a, b)] = pth[::-1]
        return pcache_p[(a, b)]
    placed = []
    for w, it in wps.items():
        # nearest terminals per neighbour subtree (graph distance on R25GPH centres)
        best = {}
        for nb in sorted(adj[w]):      # die-iter 10-12: sorted (set order made the die PYTHONHASHSEED-dependent)
            seen, stack = {w}, [(nb, abs(c0(nb)[0] - c0(w)[0]) + abs(c0(nb)[1] - c0(w)[1]))]
            while stack:
                n, d_ = stack.pop()
                if n in seen:
                    continue
                seen.add(n)
                if kind.get(n) != 'waypoint':
                    if nb not in best or d_ < best[nb][1]:
                        best[nb] = (n, d_)
                    continue
                for n2 in sorted(adj[n]):
                    if n2 not in seen:
                        stack.append((n2, d_ + abs(c0(n2)[0] - c0(n)[0]) + abs(c0(n2)[1] - c0(n)[1])))
        ends = sorted(best.values(), key=lambda t: (t[1], t[0]))
        if not ends:
            continue
        if len(ends) == 1:
            (ta, da), (tb, db) = ends[0], ends[0]
        else:
            (ta, da), (tb, db) = ends[0], ends[1]
        f_ = da / (da + db) if da + db > 0 else 0.5
        pth = gpath(ta, tb) if ta != tb else gpath(ta, ta)
        k_ = pth[min(len(pth) - 1, int(round(f_ * (len(pth) - 1))))]
        j_, i_ = divmod(k_, G.nx)
        it.x = dn((i_ + .5) * RP.CELL - it.w / 2, GX)
        it.y = dn((j_ + .5) * RP.CELL - it.h / 2, GY)
        placed.append(it)
    # legalise: off the blocks and the other relays (spiral search on a 21.6-um lattice, <= 1.2 mm)
    # ---- SM result-pin bays move with their SM
    bays = []
    for b_ in base.get('result_pin_bays', []):
        dx, dy = moved[b_['sm']]
        bx = b_['box_um']
        bays.append(dict(sm=b_['sm'], box_um=[bx[0] + dx, bx[1] + dy, bx[2] + dx, bx[3] + dy]))
    occ = [i.box() for i in insts] + [tuple(b_['box_um']) for b_ in bays]
    import bisect
    GS_ = 100.0     # hbmdie-1011/rf2: occupancy hash cell (was 500 um: thousands of boxes per cell once relays are physical)
    def hit(bx, lst):
        return any(bx[0] < o[2] and o[0] < bx[2] and bx[1] < o[3] and o[1] < bx[3] for o in lst)
    grid_ = defaultdict(list)
    def near(bx):
        out = []
        for gx_ in range(int(bx[0] // GS_) - 1, int(bx[2] // GS_) + 2):
            for gy_ in range(int(bx[1] // GS_) - 1, int(bx[3] // GS_) + 2):
                out += grid_[(gx_, gy_)]
        return out
    for o in occ:
        for gx_ in range(int(o[0] // GS_), int(o[2] // GS_) + 1):
            for gy_ in range(int(o[1] // GS_), int(o[3] // GS_) + 1):
                grid_[(gx_, gy_)].append(o)
    W_, H_ = geo_m['geo']['W'], geo_m['geo']['H']
    unplaced, unplaced_xy = [], []

    def legal(it):
        x0_, y0_ = it.x, it.y
        ok = False
        for r_ in range(0, 56):
            cand = [(0, 0)] if r_ == 0 else [(dx, dy) for dx in range(-r_, r_ + 1) for dy in (-r_, r_)] + \
                [(dx, dy) for dy in range(-r_ + 1, r_) for dx in (-r_, r_)]
            for dx, dy in cand:
                x_, y_ = dn(x0_ + dx * 21.6, GX), dn(y0_ + dy * 21.6, GY)
                bx = (x_ - 2.0, y_ - 2.0, x_ + it.w + 2.0, y_ + it.h + 2.0)
                if x_ < 20 or y_ < 20 or x_ + it.w > W_ - 20 or y_ + it.h > H_ - 20 or hit(bx, near(bx)):
                    continue
                it.x, it.y, ok = x_, y_, True
                break
            if ok:
                break
        if not ok:
            unplaced.append(it.name)
            unplaced_xy.append((it.name, round(x0_, 1), round(y0_, 1), it.w, it.h))
        b_ = it.box()
        for gx_ in range(int(b_[0] // GS_), int(b_[2] // GS_) + 1):
            for gy_ in range(int(b_[1] // GS_), int(b_[3] // GS_) + 1):
                grid_[(gx_, gy_)].append(b_)
    for it in placed:
        legal(it)
    insts += [wps[w] for w in wps]
    # ---- Option A nets (staged on their router path: a relay every LINK_STAGE_UM)
    names = {i.name for i in insts}
    lw = sum(b_ for _, b_ in V['lane_chain_nets']) if V.get('lane_chain_nets') else V['lane_rd_bits'] + V['lane_wr_bits']
    # lead 10-10 net fixes: (1) one class per net type, one direction each (no 'control' SM word pattern on these);
    # (2) f_mtp_q / t_mtp_q dropped: the transplanted hb_mtp_cmdproc (f_mtp 517) / hb_cmdproc_mtp (t_mtp 197) carry them;
    # (3) att_rec stays INSIDE the CP block while the ATT record adapter lives there (hgi_die_dispatch INTERNAL_UNITS,
    # until D4): no die net; (4) the IDX.INDEX selector path hgi_idx <-> idx_selector (abutted in the spine)
    # (5) [svc] 10-10: cp_mtp_ports (t_mtpk 120 b) had no RTL counterpart (ot_hgi_cp_die: f_mtp 517 / t_mtp 197 only;
    # the mh_* host side goes to the loader): a budget placeholder, dropped
    extra = ([('hgi_vmw_dma', 'hub', 8992, ('hb_loader', 't_hgi_vmw'), ('hb_hgi_vm', 'f_hgi_vmw_dma')),     # DMA lanes
              ('hgi_vmw_rdy', 'hub', 32, ('hb_hgi_vm', 't_hgi_vmw_rdy'), ('hb_loader', 'f_hgi_vmw')),       # 32 x 281 b
              # hbmdie-1011/vmwdone: the per-lane write COMPLETION (ot_hgi_vm_unit wq_done -> ot_hgi_dma_mover wl_done);
              # dropped with hgi_vmw_dma_done by drop_buses and not re-staged, so the loader view had bound its done
              # port to the VM's AP stop (wq_rdy).  wq_rdy stays: the AP stop the mover needs once its aperture route
              # exists (today ap = 0, so it never falls for VM writes).
              ('hgi_vmw_done', 'hub', 32, ('hb_hgi_vm', 't_hgi_vmw_done'), ('hb_loader', 'f_hgi_vmw_done'))]
             if V.get('vmw_dma') else []) + \
            ([('hgi_vmap', 'hub', 2224, ('hb_hgi_vm', 't_hgi_vmap'), ('hb_hc_SW', 'f_hgi_vmap')),      # b / d 10-11: VM ->
              ('hgi_vmap_r', 'hub', 16, ('hb_hc_SW', 't_hgi_vmap'), ('hb_hgi_vm', 'f_hgi_vmap'))]       # HC aperture, 8 lanes
             if V.get('vmap') else []) + \
            ([('hc_fused_ne', 'hub', 151, ('hb_quant', 't_fused_ne'), ('hb_hc_eng', 'f_fused_ne')),      # {g_rdy, job_v, job 149}
              ('hc_fused_ne_r', 'hub', 3, ('hb_hc_eng', 't_fused_ne'), ('hb_quant', 'f_fused_ne'))]      # {job_rdy, fault, done}
             if V.get('hc_eng') else []) + \
            ([('hgi_vmr2_dma', 'hub', 513, ('hb_loader', 't_dma_vr2q'), ('hb_hgi_vm', 'f_dma_vr2q')),     # hgi-1010/c DS MTP
              ('hgi_vmr2_dma_r', 'hub', 8257, ('hb_hgi_vm', 't_dma_vr2r'), ('hb_loader', 'f_dma_vr2r'))]   # swapout store on
             if V.get('vmr2_dma') else []) + \
            [(f'hgi_sel_{p_}', 'idx_sel', w_, ('hb_hgi_idx', f't_sel_{p_}'), ('idx_selector', p_))
             for p_, w_ in (('fs', 90), ('qb', 1048), ('kin', 345), ('toc', 1), ('coc', 1))] + \
            [(f'hgi_sel_{p_}', 'idx_sel', w_, ('idx_selector', p_), ('hb_hgi_idx', f'f_sel_{p_}'))
             for p_, w_ in (('qbr', 1), ('to', 612), ('co', 72), ('ev', 2))] + \
            ([(f'e2_{q}', 'expert_req', 129, ('hb_cmdproc', f't_hgi_e2{q}'), (f'svc_{q}_s3', 'e2'))   # [svc] 10-11: ATT KV
              for q in ('SW', 'SE', 'NW', 'NE')] if V.get('att_e2') else []) + \
            [(f'hgi_iks_{q}', 'expert_req', 128 + 1, ('hb_hgi_idx', f't_hgi_iks{q}'), (f'svc_{q}_s3', 'e'))   # [svc] IKS issuer
             for q in ('SW', 'SE', 'NW', 'NE')]     # -> the free svc e pins (ef_<st> skipped on HGI dies); 128 b + fclk
    if vb2_:
        extra += b2_nets(vb2_)
    extra += [tuple(n_) for n_ in V.get('die_slot_nets') or ()]
    for ds_ in V.get('die_slots') or ():        # each die slot is a sink of its domain's clock and reset tree
        if ds_.get('no_tree'):      # v14: the clock root block (PLL / POR) is the source of the trees, not a sink
            continue
        for cls_, pre_, pin_ in (('clock_trunk', 'clk_', 'ck'), ('reset_tree', 'rst_', 'rst')):
            hit_ = [b_ for b_ in buses if b_[1] == cls_ and b_[0] == pre_ + ds_.get('domain', 'stream')]
            assert len(hit_) == 1, ('die slot clock / reset net', ds_['name'], pre_, len(hit_))
            hit_[0][3].append((ds_['name'], pin_))
    if V.get('hgi_hc_slot'):    # D22: retarget the HGI HC unit's buses from the quarter to its own slot
        hs_ = V['hgi_hc_slot']
        frm_, hp_ = hs_['from'], set(hs_['ports'])
        rt_ = lambda e: (hs_['name'], e[1]) if e[0] == frm_ and e[1] in hp_ else e
        buses = [(b_, c_, w_, [rt_(e) for e in eps]) for b_, c_, w_, eps in buses]
        extra = [(b_, c_, w_, rt_(a_), rt_(z_)) for b_, c_, w_, a_, z_ in extra]
    by = {i.name: i for i in insts}
    nst = 0
    lane_rec = {}
    pend = []
    fclk_new_ = {}
    lkm_ = set()
    lsf_ = {}

    def gap_um(a, b):
        ba_, bb_ = by[a].box(), by[b].box()
        return max(ba_[0] - bb_[2], bb_[0] - ba_[2], ba_[1] - bb_[3], bb_[1] - ba_[3])

    stnf_ = {}      # hbmdie-1011/rf2: registered a/b faces of the physical relay station masters (+ wide relays())

    def _near_pt(it, q):
        return (min(max(q[0], it.x), it.x + it.w), min(max(q[1], it.y), it.y + it.h))

    def eseg(a, b):
        if V.get('pin_reach'):
            # v13: the exact rectilinear gap of the two boxes.  The two-step nearest-point form below is not a box
            # distance when one box spans the other's projection: PHY (8.5 mm wide) -> the svc band abutting it 8.6 um
            # above read 517-662 um, so the DFI abutment got 98 relay stations of 2,488-4,206 b in v12.
            return max(0.0, a.x - (b.x + b.w), b.x - (a.x + a.w)) + max(0.0, a.y - (b.y + b.h), b.y - (a.y + a.h))
        ca, cb = (a.x + a.w / 2, a.y + a.h / 2), (b.x + b.w / 2, b.y + b.h / 2)
        p_, q_ = _near_pt(a, cb), _near_pt(b, ca)
        p_, q_ = _near_pt(a, q_), _near_pt(b, p_)
        return abs(p_[0] - q_[0]) + abs(p_[1] - q_[1])

    _OPP = {'E': 'W', 'W': 'E', 'N': 'S', 'S': 'N'}
    nal_ = [0]      # stations placed on their upstream lane (aligned pin rows)

    def _mh2(p_, q_):
        return abs(p_[0] - q_[0]) + abs(p_[1] - q_[1])

    def face_pt(it, face):
        """centre of a face of an (R0) station outline: where a registered a / b pin row has its centroid"""
        return {'W': (it.x, it.y + it.h / 2), 'E': (it.x + it.w, it.y + it.h / 2),
                'S': (it.x + it.w / 2, it.y), 'N': (it.x + it.w / 2, it.y + it.h)}[face]

    def out_pt(it, toward):
        """where a node's downstream pins are: the b face centre of a face-registered station, else (a block or a
        peer-faced station, whose pin follows its peer) the box point nearest `toward`"""
        f_ = (stnf_.get(it.master) or {}).get('b')
        return face_pt(it, f_) if f_ and it.kind == 'waypoint' else _near_pt(it, toward)


    def place1(bid, bits, pth, ix, anc=None, reach=None, okf=None, aln=None):
        """one route-aware relay station of bus bid at route cell pth[ix] (hbmdie-1011/rf: shared by prelays / rtree).
        Anchored (anc): a site counts only within `reach` of the previous node.  v13 (pin_reach): the measure is PIN TO
        PIN -- the previous node's downstream pins (out_pt) to this station's a-face centre -- not box to box; okf(st,
        flow face) -> bool replaces the test (pin_repair: the half perimeter of the whole net); okf=False keeps the
        box measure (an anchor that is the DOWNSTREAM node).  aln = (x, y): the upstream pin row's centre -- the station
        first tries the sites that keep its own pin rows ON that lane (same track columns: bit k runs straight from
        pin to pin), sliding only along the flow."""
        nonlocal nst
        if True:
            if anc is not None and okf is not False and V.get('pin_reach'):
                # v13: an anchored station is wanted at the farthest route cell its reach allows, never beyond (the
                # callers pick ix by route fraction; a cell past the reach sent every site search to the slow disk pass)
                cc_ = lambda k_: ((k_ % G.nx + .5) * RP.CELL, (k_ // G.nx + .5) * RP.CELL)
                while ix > 0 and _mh2(out_pt(anc, cc_(pth[ix])), cc_(pth[ix])) > reach - 60.0:
                    ix -= 1
            kk = pth[ix]
            # hbmdie-1011/rf2: station outline scales with its bits (a 21.6-um-deep strip, pins at the station pin
            # density 0.048 um/bit on the two faces across the flow, >= 21.6 x 21.6), oriented by the route direction
            # over +-2 cells, and its a/b faces REGISTERED (stn_faces): a faces upstream, b downstream
            ja_, ia_ = divmod(pth[max(0, ix - 2)], G.nx)
            jb_, ib_ = divmod(pth[min(len(pth) - 1, ix + 2)], G.nx)
            ddx, ddy = ib_ - ia_, jb_ - ja_
            horiz = abs(ddx) >= abs(ddy)
            fl_ = ('E' if ddx >= 0 else 'W') if horiz else ('N' if ddy >= 0 else 'S')
            ln_ = up(max(21.6, bits * 0.048 + 20.0), GY)
            if V.get('rly_family'):     # v13: the hbfd_rly family outline (2 tracks a bit on one layer a face)
                ln_ = up(rly_face_um(bits), GY)
            if okf is None and anc is not None and V.get('pin_reach'):
                okf = lambda s_, f_: _mh2(out_pt(anc, face_pt(s_, _OPP[f_])), face_pt(s_, _OPP[f_])) <= reach
            far_ = (lambda s_, f_: not okf(s_, f_)) if okf else (lambda s_, f_: eseg(anc, s_) > reach)
            dph_, dpv_ = (rly_depth_um(bits, True), rly_depth_um(bits, False)) if V.get('rly_family') else (21.6, 21.6)
            sw_, sh_ = (dph_, ln_) if horiz else (up(ln_, GX), dpv_)
            nm = f'wq{nst}_{bid}'
            nst += 1
            mst_ = f'hfd_stn_q{bid.split("_")[0]}{nst}' if bits > 1400 else f'hfd_stn_q{bits}{fl_}'
            stnf_[mst_] = dict(a={'E': 'W', 'W': 'E', 'N': 'S', 'S': 'N'}[fl_], b=fl_)
            if V.get('rly_family'):     # ck / rst on a third face (the family's pin plan: S on E-W flow, W on N-S flow)
                stnf_[mst_].update(ck='S' if fl_ in 'EW' else 'W', rst='S' if fl_ in 'EW' else 'W')
            st_ = Inst(nm, mst_, 0.0, 0.0, sw_, sh_, 'R0', kind='waypoint', region='channel')
            ok_ = False
            # hbmdie-1011/rf2: search the whole channel cross-section (+-8 lattice steps = +-173 um across, +-1 along)
            # at each of +-4 route cells before the spiral legaliser (stations stay ON their route, so stages keep reach)
            offs_ = [(0, 0)] + [o for r in range(1, 9) for o in ((r, 0), (-r, 0), (0, r), (0, -r), (r, 1), (-r, 1),
                                                                   (r, -1), (-r, -1), (1, r), (1, -r), (-1, r), (-1, -r))]
            # anchored (relay tree): a site counts only within `reach` (edge to edge) of the previous node's ACTUAL box,
            # searched backward along the route first, so legalisation never stretches a stage
            dds_ = (0, -1, -2, -3, -4, -5, -6, 1, 2) if anc is not None else (0, -1, 1, -2, 2, -3, 3, -4, 4)
            if aln is not None and V.get('rly_family'):
                for dd in (0, -1):      # at the wanted cell only (walking back to the anchor is no stage at all)
                    jx = ix + dd
                    if not 0 <= jx < len(pth) or ok_:
                        continue
                    j_, i_ = divmod(pth[jx], G.nx)
                    if abs(((j_ + .5) * RP.CELL if horiz else (i_ + .5) * RP.CELL) - aln[1 if horiz else 0]) > 60.0:
                        continue        # a straight run only: at a route bend the upstream lane is not this cell's lane
                    for da in (0.0, 21.6, -21.6, 43.2, -43.2):
                        if horiz:
                            x_, y_ = dn((i_ + .5) * RP.CELL - sw_ / 2 + da, GX), dn(aln[1] - sh_ / 2, GY)
                        else:
                            x_, y_ = dn(aln[0] - sw_ / 2, GX), dn((j_ + .5) * RP.CELL - sh_ / 2 + da, GY)
                        bx = (x_ - 2.0, y_ - 2.0, x_ + sw_ + 2.0, y_ + sh_ + 2.0)
                        if x_ < 20 or y_ < 20 or x_ + sw_ > W_ - 20 or y_ + sh_ > H_ - 20 or hit(bx, near(bx)):
                            continue
                        st_.x, st_.y = x_, y_
                        if anc is not None and far_(st_, fl_):
                            continue
                        ok_ = True
                        nal_[0] += 1
                        break
            for dd in (() if ok_ else dds_):
                jx = ix + dd
                if not 0 <= jx < len(pth):
                    continue
                j_, i_ = divmod(pth[jx], G.nx)
                for ox, oy in offs_:
                    x_ = dn((i_ + .5) * RP.CELL - sw_ / 2 + ox * 21.6, GX)
                    y_ = dn((j_ + .5) * RP.CELL - sh_ / 2 + oy * 21.6, GY)
                    bx = (x_ - 2.0, y_ - 2.0, x_ + sw_ + 2.0, y_ + sh_ + 2.0)
                    if x_ < 20 or y_ < 20 or x_ + sw_ > W_ - 20 or y_ + sh_ > H_ - 20 or hit(bx, near(bx)):
                        continue
                    if anc is not None:
                        st_.x, st_.y = x_, y_
                        if far_(st_, fl_):
                            continue
                    st_.x, st_.y, ok_ = x_, y_, True
                    break
                if ok_:
                    break
            if not ok_ and anc is not None:
                # rf2 fine pass: narrow slots (e.g. 84-um gaps between abutting blocks) are missed by the 21.6-um lattice;
                # retry the first route cells on a 4.32-um lattice across +-64.8 um in both axes
                for dd in (0, -1, -2, 1):
                    jx = ix + dd
                    if not 0 <= jx < len(pth) or ok_:
                        continue
                    j_, i_ = divmod(pth[jx], G.nx)
                    for fx in range(-15, 16):
                        for fy in range(-15, 16):
                            x_ = dn((i_ + .5) * RP.CELL - sw_ / 2 + fx * 4.32, GX)
                            y_ = dn((j_ + .5) * RP.CELL - sh_ / 2 + fy * 4.32, GY)
                            bx = (x_ - 2.0, y_ - 2.0, x_ + sw_ + 2.0, y_ + sh_ + 2.0)
                            if x_ < 20 or y_ < 20 or x_ + sw_ > W_ - 20 or y_ + sh_ > H_ - 20 or hit(bx, near(bx)):
                                continue
                            st_.x, st_.y = x_, y_
                            if far_(st_, fl_):
                                continue
                            ok_ = True
                            break
                        if ok_:
                            break
            if not ok_ and V.get('phys_relays'):
                # rf2 wide pass (congested pockets, e.g. beside the index score grids): any site within +-216 um of the
                # first route cells on a 10.8-um lattice, nearest first, still inside the anchored reach
                for dd in ((0, -1, -2, -3, 1) if anc is not None else (0, -1, 1, -2, 2)):
                    jx = ix + dd
                    if not 0 <= jx < len(pth) or ok_:
                        continue
                    j_, i_ = divmod(pth[jx], G.nx)
                    for fx, fy in _WIDE_RING:
                        x_ = dn((i_ + .5) * RP.CELL - sw_ / 2 + fx * 10.8, GX)
                        y_ = dn((j_ + .5) * RP.CELL - sh_ / 2 + fy * 10.8, GY)
                        bx = (x_ - 2.0, y_ - 2.0, x_ + sw_ + 2.0, y_ + sh_ + 2.0)
                        if x_ < 20 or y_ < 20 or x_ + sw_ > W_ - 20 or y_ + sh_ > H_ - 20 or hit(bx, near(bx)):
                            continue
                        st_.x, st_.y = x_, y_
                        if anc is not None and far_(st_, fl_):
                            continue
                        ok_ = True
                        break
            if not ok_ and anc is not None and V.get('phys_relays'):
                # rf2 anchored disk pass: any free site (either orientation) within the reach of the previous node's
                # box, nearest to the wanted route cell first -- never the spiral legaliser for an anchored station
                # (it threw wide lane-chain banks 1-3 mm away and the repair rounds chased them)
                j_, i_ = divmod(pth[ix], G.nx)
                tx_, ty_ = (i_ + .5) * RP.CELL, (j_ + .5) * RP.CELL
                ax_, ay_ = anc.x + anc.w / 2, anc.y + anc.h / 2
                cands_ = []
                for fx in range(-46, 47):
                    for fy in range(-46, 47):
                        px_, py_ = ax_ + fx * 10.8, ay_ + fy * 10.8
                        cands_.append((abs(px_ - tx_) + abs(py_ - ty_), px_, py_))
                cands_.sort()
                for _, px_, py_ in cands_:
                    for sw2_, sh2_ in ((sw_, sh_), (up(ln_, GX), dpv_) if horiz else (dph_, ln_)):
                        x_ = dn(px_ - sw2_ / 2, GX)
                        y_ = dn(py_ - sh2_ / 2, GY)
                        bx = (x_ - 2.0, y_ - 2.0, x_ + sw2_ + 2.0, y_ + sh2_ + 2.0)
                        if x_ < 20 or y_ < 20 or x_ + sw2_ > W_ - 20 or y_ + sh2_ > H_ - 20 or hit(bx, near(bx)):
                            continue
                        st_.x, st_.y, st_.w, st_.h = x_, y_, sw2_, sh2_
                        fl2_ = fl_ if (sw2_, sh2_) == (sw_, sh_) else {'E': 'N', 'W': 'S', 'N': 'E', 'S': 'W'}[fl_]
                        if far_(st_, fl2_):
                            st_.w, st_.h = sw_, sh_
                            continue
                        ok_ = True
                        if (sw2_, sh2_) != (sw_, sh_):      # rotated: the a / b faces turn with it (flow face fl2_)
                            if bits <= 1400:        # shared narrow masters are named by their flow face
                                st_.master = f'hfd_stn_q{bits}{fl2_}'
                            stnf_[st_.master] = dict(a={'E': 'W', 'W': 'E', 'N': 'S', 'S': 'N'}[fl2_], b=fl2_)
                            if V.get('rly_family'):
                                stnf_[st_.master].update(ck='S' if fl2_ in 'EW' else 'W', rst='S' if fl2_ in 'EW' else 'W')
                        break
                    if ok_:
                        break
            if ok_:
                b_ = st_.box()
                for gx_ in range(int(b_[0] // GS_), int(b_[2] // GS_) + 1):
                    for gy_ in range(int(b_[1] // GS_), int(b_[3] // GS_) + 1):
                        grid_[(gx_, gy_)].append(b_)
            else:
                j_, i_ = divmod(kk, G.nx)
                st_.x, st_.y = dn((i_ + .5) * RP.CELL - sw_ / 2, GX), dn((j_ + .5) * RP.CELL - sh_ / 2, GY)
                legal(st_)
            insts.append(st_)
            by[nm] = st_
            return nm
    def relays(bid, bits, pth, L, tap_end=False):
        """relay instances along pth every <= LINK_STAGE_UM (+ a tap relay at the path end); returns their names."""
        nonlocal nst
        ns_ = max(0, math.ceil(L / LINK_STAGE_UM) - 1) + (1 if tap_end else 0)
        out = []
        for k in range(ns_):
            fr = (k + 1) / (ns_ + (0 if tap_end else 1))
            ix = min(len(pth) - 1, int(round(fr * (len(pth) - 1))))
            if V.get('rly_family'):     # v13: every register stage is a family-outline strip with registered faces
                out.append(place1(bid, bits, pth, ix))
                continue
            kk = pth[ix]
            j_, i_ = divmod(kk, G.nx)
            if bits <= 1400:        # a 58 x 71 um station holds ~1,450 pins a face (2,224-b vmap: 2,400 was too many)
                sw_, sh_ = 58.32, 71.28
                # v10 STA smoke 10-12: a 1,200-b vmap station (hfd_stn_q1200) put 57.6 um of pins (one M5 track
                # each) on a 57.1-um S face (58.32 minus the 2-track + 0.5-um end margins) and masters() refused it.
                # Size each face to its bus: bits on the 0.048 track + both end margins + 1 um, on the placement grid.
                need_ = bits * 0.048 + 2 * (2 * 0.048 + 0.5) + 1.0
                # 10-13: the k = 16 GRT bundle model (`check`, grt) packs ceil(bits / 16) pins at 16 tracks with a
                # 2-bundle end margin: 1,200 b = 57.6 um on 56.0 um was refused the same way (pin_clashes(m, 16))
                need_ = max(need_, math.ceil(bits / 16) * 16 * 0.048 + 2 * (2 * 16 * 0.048 + 0.5) + 0.5)
                sw_, sh_ = max(sw_, up(need_, GX)), max(sh_, up(need_, GY))
            else:       # a wide registered bus: a thin relay bank across the route, its faces as long as the bus needs
                ln_ = up(bits * 0.048 + 20.0, GY)
                k2 = pth[max(0, ix - 1)] if ix else pth[min(len(pth) - 1, 1)]
                horiz = abs(k2 - kk) == 1
                sw_, sh_ = (21.6, ln_) if horiz else (up(ln_, GX), 21.6)
            nm = f'wq{nst}_{bid}'
            nst += 1
            if bits > 1400 and V.get('phys_relays'):
                # rf2: a wide relay bank's a / b faces are REGISTERED from its route direction (a upstream, b
                # downstream); peer-derived faces put both on one face at a route corner (hfd_stn_qhgi1183: 2 x 8,257 b on S)
                ja_, ia_ = divmod(pth[max(0, ix - 2)], G.nx)
                jb_, ib_ = divmod(pth[min(len(pth) - 1, ix + 2)], G.nx)
                hz_ = abs(ib_ - ia_) >= abs(jb_ - ja_)
                fl_ = ('E' if ib_ >= ia_ else 'W') if hz_ else ('N' if jb_ >= ja_ else 'S')
                sw_, sh_ = (21.6, ln_) if hz_ else (up(ln_, GX), 21.6)
                stnf_[f'hfd_stn_q{bid.split("_")[0]}{nst}'] = dict(a={'E': 'W', 'W': 'E', 'N': 'S', 'S': 'N'}[fl_], b=fl_)
            st_ = Inst(nm, f'hfd_stn_q{bid.split("_")[0]}{nst}' if bits > 1400 else f'hfd_stn_q{bits}',
                       dn((i_ + .5) * RP.CELL - sw_ / 2, GX), dn((j_ + .5) * RP.CELL - sh_ / 2, GY), sw_, sh_, 'R0',
                       kind='waypoint', region='channel')
            legal(st_)
            insts.append(st_)
            by[nm] = st_
            out.append(nm)
        return out

    def link(bid, cls, bits, pts):
        for k in range(len(pts) - 1):
            p0_ = pts[k] if k == 0 else (pts[k][0], 'b')
            p1_ = pts[k + 1] if k + 1 == len(pts) - 1 else (pts[k + 1][0], 'a')
            buses.append((f'{bid}_{k}' if len(pts) > 2 else bid, cls, bits, [p0_, p1_]))
    if V.get('att_su_relays'):          # tr_<q><r>: attention row output -> relays -> SU lane slice
        rp_ = json.loads((ROOT / V['att_su_relays']).read_text())
        rl_ = defaultdict(list)
        for r_ in rp_['relays']:
            q_, ln_, k_ = re.fullmatch(r'rly_([NS][EW])_(\d)_(\d+)', r_['name']).groups()
            rl_[(q_, int(ln_))].append((int(k_), r_['name']))
        for bb_ in rp_['buses']:
            q_, ln_ = bb_['bus'][3:5], int(bb_['bus'][5])
            src_ = tuple(bb_['src'].split('.'))
            dm_ = re.fullmatch(r'(\w+)\.(\w+)\[(\d+):(\d+)\]', bb_['dst'])
            dst_ = (dm_.group(1), f'{dm_.group(2)}@{dm_.group(4)}:{dm_.group(3)}')
            chain_ = [src_] + [(n_, 'x') for _, n_ in sorted(rl_[(q_, ln_)])] + [dst_]
            for k_ in range(len(chain_) - 1):
                p0_ = chain_[k_] if k_ == 0 else (chain_[k_][0], 'o')
                p1_ = chain_[k_ + 1] if k_ + 1 == len(chain_) - 1 else (chain_[k_ + 1][0], 'i')
                buses.append((f"{bb_['bus']}_{k_}", 'attn_out', bb_['bits'], [p0_, p1_]))
    if ep_of:       # the coll -> SerDes chains end at the endpoint (545-b TU flit + valid + credit each way + fault);
        #             the endpoint drives the SerDes iox (gearboxed PHY lanes, phy_bits) over its own relayed hop
        fw = V['link_ep']['flit_bits']
        nb_ = []
        for bid, cls, bits, eps in buses:
            hit_ = [e for e in eps if e[0] in ep_of and e[1] == 'iox']
            if bid.startswith('lk_lk_') and cls == 'link':
                if hit_:
                    eps = [e if e not in hit_ else (ep_of[e[0]], 'f_lk') for e in eps]
                    nb_.append((bid, 'link_flit', fw, eps))
                    sd_ = hit_[0][0]
                    pth = gpath(ep_of[sd_], sd_)
                    L = (len(pth) - 1) * RP.CELL if gap_um(ep_of[sd_], sd_) > 2.0 else 0.0
                    pb_ = V['link_ep'].get('phy_bits', bits)
                    rl = relays(f'lkp{sd_[3:]}', pb_, pth, L)
                    pend.append((f'lkp_{sd_[3:]}', 'link', pb_, [(ep_of[sd_], 'phy')] + [(r_, 'b') for r_ in rl] + [(sd_, 'iox')]))
                    continue
                nb_.append((bid, 'link_flit', fw + 2, eps))      # + the two forwarded clocks (fclk map rebased below)
                continue
            nb_.append((bid, cls, bits, eps))
        # [link] 10-10 (98493b213) endpoint control: clk = clk_link, rst_n = rst_link (the SerDes clock / reset trees);
        # session[23:0] (coll -> ep, the coordinated-reset epoch) and {fault, locked} (ep -> coll status aggregation)
        # ride the flit chain's stations: f_lk = [1093:0] flit bus, [1117:1094] session, [1119:1118] {locked, fault}
        nb_ = [(b_, c_, w_, e_ + [(ep_of[e[0]], 'clk') for e in e_ if e[0] in ep_of and e[1] == 'ck']
                if b_ == 'clk_link' else e_ + ([(e, 'rst_n') for e in sorted(set(ep_of.values()))] if b_ == 'rst_link' else []))
               for b_, c_, w_, e_ in nb_]
        buses[:] = nb_
        # the coll -> endpoint chain stations were sized for 976 b: scale their pin faces to the flit bus
        lkm_ = {by[e[0]].master for b_, c_, w_, e_ in buses if b_.startswith('lk_lk_') for e in e_
                if e[0] in by and by[e[0]].kind == 'waypoint'}
        for it_ in insts:
            if it_.master in lkm_:
                it_.w = up(it_.w * (fw + 2) / 976.0 + 4.0, GX)        # both faces: the pin face is either
                it_.h = up(it_.h * (fw + 2) / 976.0 + 4.0, GY)
                legal(it_)
        for bid, cls, bits, pts in pend:
            link(bid, cls, bits, pts)
    if V.get('shared_ks'):
        # [svc] N8 / N9 10-10: ks<k> (1,099 b + 3 fclk) fans out at the svc port to the attention entry (existing chain)
        # AND the stack's score grid ik slice; the grid's ikc<k> credit returns on kc<k> (existing chain, band per map);
        # kq<k> (2 b {fclk, v}) is the attention entry's line credit back to the ks<k> band; kd (2 b {fclk, done}) fans
        # out from band 3 to every ks consumer.  Branches staged with relays, a register at each consumer.
        def branch_heads(bid, bits, src, sinks, cls, fclk_=None):
            heads, rest = [], []
            for k_, (snk, sp_) in enumerate(sinks):
                pth = gpath(src[0], snk)
                L = (len(pth) - 1) * RP.CELL if gap_um(src[0], snk) > 2.0 else 0.0
                rl = relays(f'{bid}{k_}', bits, pth, L)
                nodes = [(r_, None) for r_ in rl] + [(snk, sp_)]
                heads.append((nodes[0][0], 'a') if rl else (snk, sp_))
                for j_ in range(len(nodes) - 1):
                    a_ = (nodes[j_][0], 'b')
                    b_ = nodes[j_ + 1] if j_ + 1 == len(nodes) - 1 else (nodes[j_ + 1][0], 'a')
                    rest.append((f'{bid}_{k_}_{j_ + 1}', cls, bits, [a_, b_]))
            return heads, rest
        ksend = {}
        for bid_, c_, w_, eps_ in buses:
            mm_ = re.fullmatch(r'ks(\d)_([NS][EW])_e', bid_)
            if mm_:
                ksend[(mm_.group(2), int(mm_.group(1)))] = [e for e in eps_ if e[1] == 'ks'][0][0]
        for st_ in ('SW', 'SE', 'NW', 'NE'):
            fam_ = 'SW' if st_[1] == 'W' else 'SE'
            bandk_ = V['shared_ks']['band'][fam_]
            g_ = f'idx_score_{st_}'
            for k_ in range(8):
                src_ = (f'svc_{st_}_s{bandk_[k_]}', f'ks{k_}')
                i0_ = next((i for i, b_ in enumerate(buses) if b_[0] == f'ks{k_}_{st_}_0'), None)
                hd_, rs_ = branch_heads(f'ksg{k_}{st_}', 1102, src_, [(g_, f'ik@{k_ * 1099}:{k_ * 1099 + 1098}')], 'kv_rows')
                if i0_ is not None:     # the row already feeds an attention entry: fan out at the svc port
                    b0_ = buses[i0_]
                    buses[i0_] = (b0_[0], b0_[1], b0_[2], b0_[3] + hd_)
                else:                   # the grid is this row's only consumer
                    buses.append((f'ks{k_}_{st_}_g0', 'kv_rows', 1102 if hd_[0][0] != g_ else 1099, [src_] + hd_))
                    if hd_[0][0] != g_:
                        fclk_new_[f'ks{k_}_{st_}_g0'] = (1099, 3, 0)
                for r_ in rs_:     # the grid takes the 1,099 data bits (its own fclk pin is the grid owner's to add)
                    last_ = r_[3][1][0] == g_
                    buses.append((r_[0], r_[1], 1099 if last_ else 1102, r_[3]))
                    if last_ and r_[3][0][0] in by:     # the grid-side relay drops the fclk copies: its own master
                        om_ = by[r_[3][0][0]].master
                        by[r_[3][0][0]].master = 'hfd_stn_q1102g' + (om_[-1] if V.get('rly_family') else '')
                        if om_ in stnf_:
                            stnf_[by[r_[3][0][0]].master] = dict(stnf_[om_])
                    if not last_:
                        fclk_new_[r_[0]] = (1099, 3, 0)
                at_ = ksend.get((st_, k_))
                if at_:
                    pth = gpath(at_, src_[0])
                    L = (len(pth) - 1) * RP.CELL if gap_um(at_, src_[0]) > 2.0 else 0.0
                    link(f'kq{k_}_{st_}', 'kv_credit', 2, [(at_, 'kq')] + [(r_, 'b') for r_ in relays(f'kq{k_}{st_}', 2, pth, L)]
                         + [(src_[0], f'kq{k_}')])
            sinks_ = [(ksend[(st_, k_)], 'kd') for k_ in range(8) if (st_, k_) in ksend] + [(g_, 'kd')]
            hd_, rs_ = branch_heads(f'kd{st_}', 2, (f'svc_{st_}_s3', 'kd'), sinks_, 'kv_credit')
            buses.append((f'kd_{st_}_0', 'kv_credit', 2, [(f'svc_{st_}_s3', 'kd')] + hd_))
            buses.extend(rs_)
    for bid, cls, bits, a, b in extra:
        pth = gpath(a[0], b[0])
        L = (len(pth) - 1) * RP.CELL if gap_um(a[0], b[0]) > 2.0 else 0.0
        link(bid, cls, bits, [a] + [(r_, 'b') for r_ in relays(bid, bits, pth, L)] + [b])
    # hgi-1010/b lane groups: one registered read + write bus a group, through its clients: each client block hosts its
    # client station (the bus enters one face, leaves another), relays only on the open stretches
    for sd_, cfg_ in (V.get('lane_stations') or {}).items():
        # lead 10-10 (SU client slot 0 / lgE off cmdproc) + hgi-1010/b tap contract (ot_hgi_vm_lanestation local side,
        # full width: read up 513 / down 8,257, write up 8,961 / down 65): no lane-group pass-through in any block.  Each
        # client has a station bank abutting its VM-facing face (the full-width tap is a short abutment); the chain runs
        # VM -> station -> station on the banks' outer faces
        rec = []
        sts_ = []
        for k_, st_cfg_ in enumerate(cfg_['stations']):
            snm_, cl_, cf_, lmax_ = st_cfg_[:4]
            c_ = by[cl_]
            th_, g_ = cfg_['thick'], cfg_['gap']
            if cf_ in 'EW':
                L_ = lmax_
                x_ = c_.x + c_.w + g_ if cf_ == 'E' else c_.x - g_ - th_
                y_ = c_.y + c_.h - 20.0 - L_ if cfg_.get('align', {}).get(snm_) == 'top' else c_.y + (c_.h - L_) / 2
                w_, h_ = th_, L_
            else:
                L_ = lmax_
                x_ = c_.x + (c_.w - L_) / 2
                y_ = c_.y + c_.h + g_ if cf_ == 'N' else c_.y - g_ - th_
                w_, h_ = L_, th_
            st_ = Inst(snm_, f'hfd_stn_lg{sd_}{k_}', dn(x_, GX), dn(y_, GY), up(w_, GX), up(h_, GY), 'R0', kind='waypoint',
                       region='channel')
            hh_ = [i.name for i in insts if i.kind != 'waypoint' and st_.box()[0] < i.x + i.w and i.x < st_.box()[2]
                   and st_.box()[1] < i.y + i.h and i.y < st_.box()[3]]
            assert not hh_, ('lane station overlaps', snm_, hh_)
            insts.append(st_)
            by[snm_] = st_
            G.inst[snm_] = st_
            b_ = st_.box()
            for gx_ in range(int(b_[0] // GS_), int(b_[2] // GS_) + 1):
                for gy_ in range(int(b_[1] // GS_), int(b_[3] // GS_) + 1):
                    grid_[(gx_, gy_)].append(b_)
            for wp_ in [i for i in insts if i.kind == 'waypoint' and i is not st_ and b_[0] < i.x + i.w and i.x < b_[2]
                        and b_[1] < i.y + i.h and i.y < b_[3]]:
                legal(wp_)          # a waypoint placed before the station: move it off the bank
            sts_.append((snm_, cl_, st_cfg_[4] if len(st_cfg_) > 4 else ''))
            lsf_[snm_] = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}[cf_]     # the station's face toward its client
        nodes0_ = [cfg_['src']] + [n_ for n_, _, _ in sts_]
        for ci, (src, cl) in enumerate(zip(nodes0_, nodes0_[1:])):
            pth = gpath(src, cl)
            L = (len(pth) - 1) * RP.CELL if gap_um(src, cl) > 2.0 else 0.0
            rl = relays(f'lg{sd_}{ci}', lw, pth, L)
            nodes_ = [src] + rl + [cl]
            for suf_, bits_ in (V.get(f'lane_chain_nets_{sd_}') or V['lane_chain_nets']):
                nn_ = nodes_ if suf_.endswith('dn') else nodes_[::-1]
                for k_ in range(len(nn_) - 1):
                    buses.append((f'hgi_lg{sd_.lower()}_{suf_}_{ci}' + (f'_{k_}' if len(nn_) > 2 else ''), 'hub', bits_,
                                  [(nn_[k_], f't_lg{sd_}_{suf_}'), (nn_[k_ + 1], f'f_lg{sd_}_{suf_}')]))
            rec.append(dict(station=cl, from_=src, path_um=L, relays=len(rl)))
        for snm_, cl_, tg_ in sts_:     # the abutting full-width tap: station t_lg<G>c_<dn> -> client, client t_* -> station
            for suf_, bits_ in (V.get(f'lane_tap_nets_{sd_}') or V['lane_tap_nets']):     # (a block with two client slots names them by tag: f_lgE<tag>_*)
                cg_ = 'c' if cl_ in (V.get('lane_tap_generic') or ()) else f'{sd_}{tg_}'   # v10: replicated client, one port name
                ends_ = [(snm_, f't_lg{sd_}c_{suf_}'), (cl_, f'f_lg{cg_}_{suf_}')] if suf_.endswith('dn') else \
                    [(cl_, f't_lg{cg_}_{suf_}'), (snm_, f'f_lg{sd_}c_{suf_}')]
                buses.append((f'hgi_lg{sd_.lower()}_tap_{suf_}_{cl_[3:]}{tg_}', 'hub', bits_, ends_))
            rec.append(dict(client=cl_, station=snm_, box=[round(x, 3) for x in by[snm_].box()],
                            tap_bits=sum(b_ for _, b_ in (V.get(f'lane_tap_nets_{sd_}') or V['lane_tap_nets']))))
        lane_rec[sd_] = rec
    for sd_, chain_ in ({} if V.get('lane_stations') else V['lane_groups']).items():
        rec = []
        byp = (V.get('lane_bypass') or {}).get(sd_)
        if byp:     # decision (a): a client-station relay bank in the client | next-block gap replaces the pass-through
            cb_, nb_ = by[byp['client']].box(), by[byp['toward']].box()
            if nb_[2] <= cb_[0]:        # next block W of the client: the vertical gap column between them
                gx0, gx1 = nb_[2], cb_[0]
            else:
                gx0, gx1 = cb_[2], nb_[0]
            gy0, gy1 = max(cb_[1], nb_[1]), min(cb_[3], nb_[3])
            ln_ = up((lw + byp['tap_rd'] + byp['tap_wr']) * 0.048 + 60.0, GY)    # + the k = 16 bundle gaps of 6 ports
            assert gx1 - gx0 >= byp['w'] + 2 * 43.2 and gy1 - gy0 >= ln_, ('lane bypass gap too small', byp, gx0, gx1, gy0, gy1, ln_)
            stn = Inst(byp['stn'], byp['master'], dn((gx0 + gx1 - byp['w']) / 2, GX), dn((gy0 + gy1 - ln_) / 2, GY),
                       byp['w'], ln_, 'R0', kind='waypoint', region='channel')
            assert not hit(stn.box(), near(stn.box())), ('lane bypass station overlaps', stn.box())
            insts.append(stn)
            by[stn.name] = stn
            G.inst[stn.name] = stn
            b_ = stn.box()
            for gx_ in range(int(b_[0] // GS_), int(b_[2] // GS_) + 1):
                for gy_ in range(int(b_[1] // GS_), int(b_[3] // GS_) + 1):
                    grid_[(gx_, gy_)].append(b_)
            i_ = chain_.index(byp['client'])
            assert chain_[i_ - 1] == byp['after'] and chain_[i_ + 1] == byp['toward'], ('lane bypass order', chain_)
            chain_ = tuple(chain_[:i_]) + (stn.name,) + tuple(chain_[i_ + 1:])
            buses.append((f'vm_lg{sd_}_tap_rd', 'hub', byp['tap_rd'], [(stn.name, f't_lg{sd_}c'), (byp['client'], f'f_lg{sd_}')]))
            buses.append((f'vm_lg{sd_}_tap_wr', 'hub', byp['tap_wr'], [(byp['client'], f't_lg{sd_}'), (stn.name, f'f_lg{sd_}c')]))
            rec.append(dict(bypass=byp['client'], station=stn.name, box=[round(x, 3) for x in stn.box()],
                            tap_bits=byp['tap_rd'] + byp['tap_wr']))
        for ci, (src, cl) in enumerate(zip(chain_, chain_[1:])):
            pth = gpath(src, cl)
            L = (len(pth) - 1) * RP.CELL if gap_um(src, cl) > 2.0 else 0.0
            rl = relays(f'lg{sd_}{ci}', lw, pth, L)
            if V.get('lane_chain_nets'):
                # hgi-1010/b VM DIE CONTRACT (10-10 20:10): four registered chain buses a lane group, hgi_lg<g>_{rdn,
                # wdn} down the chain (VM -> clients), {rup, wup} up it; every node takes f_<..> in and drives t_<..> out
                nodes_ = [src] + rl + [cl]
                for suf_, bits_ in V['lane_chain_nets']:
                    nn_ = nodes_ if suf_.endswith('dn') else nodes_[::-1]
                    for k_ in range(len(nn_) - 1):
                        buses.append((f'hgi_lg{sd_.lower()}_{suf_}_{ci}' + (f'_{k_}' if len(nn_) > 2 else ''), 'hub', bits_,
                                      [(nn_[k_], f't_lg{sd_}_{suf_}'), (nn_[k_ + 1], f'f_lg{sd_}_{suf_}')]))
            else:
                link(f'vm_lg{sd_}_{ci}', 'hub', lw, [(src, f't_lg{sd_}')] + [(r_, 'b') for r_ in rl] + [(cl, f'f_lg{sd_}')])
            rec.append(dict(client=cl, from_=src, gap_um=round(max(gap_um(src, cl), 0.0), 1), path_um=L, relays=len(rl)))
        lane_rec[sd_] = rec
    # hbmdie-1011 (textbook audit row 1, phys_relays): every budgeted register hop becomes a physical relay.  A driver ->
    # load segment longer than one stage gets relay stations every <= LINK_STAGE_UM along its grid-router path (the
    # same relays() stations as the Option A chains: forwarded clock where the bus is an fclk bus, common clock
    # otherwise); the first relay takes the far load's place on the original net (fan-out buses stay one net; bus ids,
    # fclk entries and named paths keep working) and the chain continues as <bid>_p<j>_<k>.
    phys_rec = None
    new_rl = {}
    fcl_ = dict(base.get('fclk') or {}, **fclk_new_)

    def prelays(bid, bits, pth, L):
        """hbmdie-1011 phys_relays: relays() with ROUTE-AWARE placement -- each station first takes a free site on its
        own path (+-4 grid cells along the route, <= 2 lattice steps across it), only then the spiral legaliser."""
        ns_ = max(0, math.ceil(L / LINK_STAGE_UM) - 1)
        out = []
        for k in range(ns_):
            fr = (k + 1) / (ns_ + 1)
            ix = min(len(pth) - 1, int(round(fr * (len(pth) - 1))))
            out.append(place1(bid, bits, pth, ix))
        return out

    if V.get('phys_relays'):
        PR_LIM = SS_REACH_UM - 20.0
        nb_, n_rl, n_ch = [], 0, 0
        if PC_['use'] is not None:      # pc_seed: the hops that need no relay are demand the relay routes must see
            for bid, cls, bits, eps in buses:
                if cls in ('clock_trunk', 'reset_tree') or len(eps) < 2 or eps[0][0] not in by:
                    continue
                a_ = by[eps[0][0]]
                for e in eps[1:]:
                    if e[0] in by and e[0] != eps[0][0] and eseg(a_, by[e[0]]) <= PR_LIM:
                        ca_ = (a_.x + a_.w / 2, a_.y + a_.h / 2)
                        q_ = _near_pt(by[e[0]], ca_)
                        pc_seg(_near_pt(a_, q_), q_, bits)
            PC_['built'] = PC_['n']
        for b_ in buses:
            bid, cls, bits, eps = b_
            if cls in ('clock_trunk', 'reset_tree') or len(eps) < 2 or eps[0][0] not in by or eps[0][0] == 'TOP':
                nb_.append(b_)
                continue
            d0 = eps[0]
            keep, far_ = [d0], []
            for e in eps[1:]:
                if e[0] in by and e[0] != d0[0] and eseg(by[d0[0]], by[e[0]]) > PR_LIM:
                    far_.append(e)
                else:
                    keep.append(e)
            if not far_:
                nb_.append(b_)
                continue
            if os.environ.get('OT_HBMDIE_TRACE') == '2' and cls == 'phy_dfi':
                print('DFI far', bid, d0, [round(v) for v in by[d0[0]].box()], [(e, [round(v) for v in by[e[0]].box()],
                      round(eseg(by[d0[0]], by[e[0]]))) for e in far_], file=sys.stderr, flush=True)
            if V.get('relay_tree'):
                # hbmdie-1011/rf (relay TREE): the far loads of one bus share relay stations along the common prefix of
                # their routes (one shortest-path tree per source), branching where the routes diverge; a station each
                # time the route length since the last one reaches STEP (one route cell of legalisation margin)
                STEP = LINK_STAGE_UM - RP.CELL
                G.inst.setdefault(d0[0], by[d0[0]])
                trie, st_of, kids = {}, {}, defaultdict(list)
                for e in far_:
                    G.inst.setdefault(e[0], by[e[0]])
                    pth = gpath_p(d0[0], e[0], bits, bid)
                    cur, par, last_i = 0, None, 0
                    anc_ = by[d0[0]]
                    for i_ in range(1, len(pth)):
                        cur = trie.setdefault((cur, pth[i_]), len(trie) + 1)
                        if (i_ - last_i) * RP.CELL >= STEP and (len(pth) - 1 - i_) * RP.CELL > RP.CELL:
                            if cur not in st_of:
                                st_of[cur] = place1(bid, bits, pth, i_, anc=anc_, reach=V.get('relay_reach', 480.0),
                                                    aln=face_pt(anc_, stnf_[anc_.master]['b']) if V.get('rly_lane_align') and
                                                    anc_.kind == 'waypoint' and (stnf_.get(anc_.master) or {}).get('b') else None)
                                G.inst[st_of[cur]] = by[st_of[cur]]
                                new_rl[st_of[cur]] = bid
                                n_rl += 1
                            sn_ = st_of[cur]
                            anc_ = by[sn_]
                            if par is None:
                                if (sn_, 'a') not in keep:
                                    keep.append((sn_, 'a'))
                            elif (sn_, 'a') not in kids[par]:
                                kids[par].append((sn_, 'a'))
                            par, last_i = sn_, i_
                    if par is None:
                        keep.append(e)
                    else:
                        kids[par].append(e)
                        n_ch += 1
                for t_, (sn_, ch_) in enumerate(kids.items()):
                    nid = f'{bid}_t{t_}'
                    nb_.append((nid, cls, bits, [(sn_, 'b')] + ch_))
                    if bid in fcl_ or bid in fclk_new_:     # H-DIE 1014pm: a segment split after the fcl_ snapshot
                        fclk_new_[nid] = fcl_.get(bid) or fclk_new_[bid]
                nb_.append((bid, cls, bits, keep))
                continue
            for j_, e in enumerate(far_):
                G.inst.setdefault(d0[0], by[d0[0]])
                G.inst.setdefault(e[0], by[e[0]])
                pth = gpath_p(d0[0], e[0], bits, bid)
                L = max((len(pth) - 1) * RP.CELL, eseg(by[d0[0]], by[e[0]]) + LINK_STAGE_UM / 2)
                rl = prelays(bid, bits, pth, L)
                if not rl:
                    keep.append(e)
                    continue
                for r_ in rl:
                    G.inst[r_] = by[r_]
                    new_rl[r_] = bid
                n_rl += len(rl)
                n_ch += 1
                keep.append((rl[0], 'a'))
                for k_ in range(len(rl)):
                    nid = f'{bid}_p{j_}_{k_}'
                    nb_.append((nid, cls, bits, [(rl[k_], 'b'), (rl[k_ + 1], 'a') if k_ + 1 < len(rl) else e]))
                    if bid in fcl_ or bid in fclk_new_:     # H-DIE 1014pm: a segment split after the fcl_ snapshot
                        fclk_new_[nid] = fcl_.get(bid) or fclk_new_[bid]
            nb_.append((bid, cls, bits, keep))
        buses[:] = nb_
        phys_rec = dict(data_chains=n_ch, data_relays=n_rl)
        if os.environ.get('OT_HBMDIE_TRACE'):
            print('phys relays', phys_rec, len(insts), 'insts', round(time.time() - _T0), 's', file=sys.stderr, flush=True)
    # far-side relays (legalisation pushed a relay behind its driver): step it toward its sink and re-legalise
    import fp_margin_lint as FPL
    for _ in range(20):     # R25GQ link endpoints: the IKS chains detour the S endpoint band (4 passes left 3 far-side relays)
        ml_ = FPL.die_margin(insts, buses, MARGIN_RELAY_KINDS, reach_um=SS_REACH_UM, stages=lambda bid, L: 0, limit=200,
                             edges=True)    # per register segment: the bidirectional lane chains made the path walk explode
        bad = [x['relay'] for x in ml_.get('far_side_examples', [])] if ml_['far_side_relays'] else []
        if not bad:
            break
        for r_ in bad:
            it = by[r_]
            snk = next(e2[0] for b_, c_, w_, eps in buses if (r_, 'b') in eps for e2 in eps if e2[0] != r_)
            sk = by[snk]
            drv = next((eps[0][0] for b_, c_, w_, eps in buses if (r_, 'a') in eps and eps[0][0] != r_), None)
            if _ >= 6 and drv in by:    # still behind after 6 steps: the midpoint of its driver and its sink
                dv = by[drv]
                it.x = dn((dv.x + dv.w / 2 + sk.x + sk.w / 2) / 2 - it.w / 2, GX)
                it.y = dn((dv.y + dv.h / 2 + sk.y + sk.h / 2) / 2 - it.h / 2, GY)
            else:
                it.x = dn(it.x + 0.4 * (sk.x + sk.w / 2 - it.x), GX)
                it.y = dn(it.y + 0.4 * (sk.y + sk.h / 2 - it.y), GY)
            legal(it)
    if V.get('phys_relays'):
        # repair: a relay legalised off its route can still leave a segment over the reach -> one more relay on it
        bad_ = ()
        # v13 (pin_reach): the box-to-box repair is not run -- pin_repair below repairs every net on the pin measure,
        # which bounds the box measure (it also diverged at the family outlines: a fixed station count per route
        # length falls short at the pin-to-pin pitch, 207 -> 447 segments over in rounds 1-7)
        for _r in range(0 if V.get('pin_reach') else V.get('relay_repair_rounds', 6)):
            ml_ = FPL.die_margin(insts, [b_ for b_ in buses if b_[1] not in ('clock_trunk', 'reset_tree')],
                                 MARGIN_RELAY_KINDS, reach_um=SS_REACH_UM, stages=lambda bid, L: 0, limit=100000, edges=True)
            bad_ = {tuple(x['seg'].split('->')) for x in ml_['reach_examples']}
            if os.environ.get('OT_HBMDIE_TRACE'):
                print('relay repair round', _r, len(bad_), 'segments over', len(insts), 'insts', round(time.time() - _T0), 's',
                      file=sys.stderr, flush=True)
            if not bad_:
                break
            if _r >= 2 and V.get('relay_tree'):
                # rf2: congestion-aware repair routes -- a cell's cost grows with the relay stations already in it, so a
                # chain that cannot find a site in a full channel (e.g. the 84-um gaps of the S lk_ep row) detours
                # through an emptier one
                import numpy as _np
                occ_ = _np.zeros((G.ny, G.nx))
                for it_ in insts:
                    if it_.kind == 'waypoint':
                        i_, j_ = int((it_.x + it_.w / 2) // RP.CELL), int((it_.y + it_.h / 2) // RP.CELL)
                        if 0 <= i_ < G.nx and 0 <= j_ < G.ny:
                            occ_[j_, i_] += it_.w * it_.h / RP.CELL ** 2
                free_ = _np.maximum(G.free, 0.05)
                PC_['extra'] = 40.0 * _np.minimum(occ_ / free_, 2.0)
                A_p = None
                spt_p.clear()
                pcache_p.clear()
            nb_ = []
            for b_ in buses:
                bid, cls, bits, eps = b_
                hit_ = [e for e in eps[1:] if (eps[0][0], e[0]) in bad_] if cls not in ('clock_trunk', 'reset_tree') else []
                if not hit_:
                    nb_.append(b_)
                    continue
                keep = [e for e in eps if e not in hit_]
                for j_, e in enumerate(hit_):
                    G.inst.setdefault(eps[0][0], by[eps[0][0]])
                    G.inst.setdefault(e[0], by[e[0]])
                    if V.get('relay_tree'):     # rf2: anchored sequential stations along the (block-avoiding) route
                        pth = gpath_p(eps[0][0], e[0], bits, f'{bid}/r{_r}')
                        ns_ = max(1, math.ceil((len(pth) - 1) * RP.CELL / LINK_STAGE_UM) - 1)
                        rl, anc_ = [], by[eps[0][0]]
                        for k in range(ns_):
                            ix = min(len(pth) - 1, int(round((k + 1) / (ns_ + 1) * (len(pth) - 1))))
                            rl.append(place1(bid, bits, pth, ix, anc=anc_, reach=V.get('relay_reach', 480.0)))
                            anc_ = by[rl[-1]]
                    else:
                        rl = prelays(bid, bits, gpath_p(eps[0][0], e[0], bits, f'{bid}/r{_r}'), 2 * LINK_STAGE_UM - 1.0)
                    if V.get('relay_tree') and eseg(by[rl[-1]], by[e[0]]) > PR_LIM:
                        # rf2: the anchored chain can end short of a far waypoint in a congested pocket -> one more
                        # station anchored on the TARGET (searched back along the route); the gap before it is
                        # a mid-route segment the next round repairs
                        pth = gpath_p(eps[0][0], e[0], bits, f'{bid}/r{_r}')
                        rl.append(place1(bid, bits, pth, max(0, len(pth) - 3), anc=by[e[0]],
                                         reach=V.get('relay_reach', 480.0), okf=False))
                    for r_ in rl:
                        G.inst[r_] = by[r_]
                        new_rl[r_] = bid
                    phys_rec['data_relays'] += len(rl)
                    keep.append((rl[0], 'a'))
                    for k_ in range(len(rl) - 1):   # rf2 fix: the stations of a multi-station repair chain were never
                        # linked to each other (rl[0].b and rl[-1].a dangling whenever ns_ > 1)
                        nid_ = f'{bid}_r{_r}{j_}_{k_}'
                        nb_.append((nid_, cls, bits, [(rl[k_], 'b'), (rl[k_ + 1], 'a')]))
                        if bid in fcl_ or bid in fclk_new_:     # H-DIE 1014pm: a segment split after the fcl_ snapshot
                            fclk_new_[nid_] = fcl_.get(bid) or fclk_new_[bid]
                    nid = f'{bid}_r{_r}{j_}'
                    nb_.append((nid, cls, bits, [(rl[-1], 'b'), e]))
                    if bid in fcl_ or bid in fclk_new_:     # H-DIE 1014pm: a segment split after the fcl_ snapshot
                        fclk_new_[nid] = fcl_.get(bid) or fclk_new_[bid]
                nb_.append((bid, cls, bits, keep))
            buses[:] = nb_
        phys_rec['data_reach_left'] = len(bad_)
        # rf2 far-side pass: a point-to-point station farther from its next node than its own driver (a detour the
        # anchored placement took around a congested pocket) moves to the free site nearest its driver -> next line
        # that keeps BOTH stages within the reach and is not behind its driver
        def _mh(p_, q_):
            return abs(p_[0] - q_[0]) + abs(p_[1] - q_[1])

        def _ctr(it_):
            return (it_.x + it_.w / 2, it_.y + it_.h / 2)
        n_fs = 0
        for _f in range(4):
            ml_ = FPL.die_margin(insts, [b_ for b_ in buses if b_[1] not in ('clock_trunk', 'reset_tree')],
                                 MARGIN_RELAY_KINDS, reach_um=SS_REACH_UM, stages=lambda bid, L: 0, limit=100000, edges=True)
            fs_ = ml_.get('far_side_examples', []) if ml_['far_side_relays'] else []
            if not fs_:
                break
            for x_ in fs_:
                cur_, nxt_ = x_['chain'].split('->')
                r_ = by.get(x_['relay'])
                if r_ is None or cur_ not in by or nxt_ not in by or r_.kind != 'waypoint':
                    continue
                A_, Z_ = by[cur_], by[nxt_]
                qa_, qz_ = _ctr(A_), _ctr(Z_)
                ob_ = r_.box()
                for gx_ in range(int(ob_[0] // GS_), int(ob_[2] // GS_) + 1):
                    for gy_ in range(int(ob_[1] // GS_), int(ob_[3] // GS_) + 1):
                        if ob_ in grid_[(gx_, gy_)]:
                            grid_[(gx_, gy_)].remove(ob_)
                x0_, y0_ = r_.x, r_.y
                best_ = None
                mx_, my_ = (qa_[0] + qz_[0]) / 2, (qa_[1] + qz_[1]) / 2
                grid2_ = [(qa_[0] + fx * 10.8, qa_[1] + fy * 10.8) for fx in range(-46, 47) for fy in range(-46, 47)] + \
                    [(mx_ + fx * 4.32, my_ + fy * 4.32) for fx in range(-30, 31) for fy in range(-30, 31)]
                for px_, py_ in grid2_:
                    if True:
                        if _mh((px_, py_), qz_) > _mh(qa_, qz_) + 15.0:
                            continue
                        x1_, y1_ = dn(px_ - r_.w / 2, GX), dn(py_ - r_.h / 2, GY)
                        bx = (x1_ - 2.0, y1_ - 2.0, x1_ + r_.w + 2.0, y1_ + r_.h + 2.0)
                        if x1_ < 20 or y1_ < 20 or x1_ + r_.w > W_ - 20 or y1_ + r_.h > H_ - 20 or hit(bx, near(bx)):
                            continue
                        r_.x, r_.y = x1_, y1_
                        if eseg(A_, r_) > PR_LIM or eseg(r_, Z_) > PR_LIM:
                            continue
                        k_ = eseg(A_, r_) + eseg(r_, Z_)
                        if best_ is None or k_ < best_[0]:
                            best_ = (k_, x1_, y1_)
                r_.x, r_.y = (best_[1], best_[2]) if best_ else (x0_, y0_)
                n_fs += bool(best_)
                nb2_ = r_.box()
                for gx_ in range(int(nb2_[0] // GS_), int(nb2_[2] // GS_) + 1):
                    for gy_ in range(int(nb2_[1] // GS_), int(nb2_[3] // GS_) + 1):
                        grid_[(gx_, gy_)].append(nb2_)
        phys_rec['far_side_moved'] = n_fs
    def _model():
        """the die model of the network as it stands (the return value; also the pin_repair / tree passes' view of the
        pin plans: masters() on it gives every block's and station's pins before the clock / reset trees exist)"""
        m_ = dict(base)
        m_.update(insts=insts, buses=buses, geo=dict(base['geo'], **geo_m['geo']), regions=geo_m['regions'],
                  variant=dict(bv, **V), result_pin_bays=bays, reserved_regions=[b_['box_um'] for b_ in bays],
                  paths={k: [b_ for b_ in v if b_ in {x[0] for x in buses}] for k, v in base['paths'].items()},
                  notes=geo_m['notes'] + [f'R25GQ network by transplant of R25GPH: {len(gone)} attention / pruned waypoint '
                                          f'instances removed, {len(wps)} waypoints re-placed ({len(unplaced)} unplaced), '
                                          f'{nst} Option A relays'],
                  r25gq_unplaced=unplaced, r25gq_unplaced_xy=unplaced_xy, r25gq_lane_groups=lane_rec, network_probe=True)
        if ep_of:
            m_['fclk'] = {k: ((V['link_ep']['flit_bits'], *v[1:]) if k.startswith('lk_lk_') else v)
                          for k, v in (base.get('fclk') or {}).items()}
        m_['lane_station_face'] = lsf_
        if stnf_:
            m_['stn_faces'] = dict(m_.get('stn_faces') or {}, **stnf_)
        if ep_of:       # the widened flit-chain stations get generated pin plans (their fixed 976-b plans no longer fit)
            m_['fixed_ports'] = {k_: v_ for k_, v_ in (m_.get('fixed_ports') or {}).items() if k_ not in lkm_}
        if fclk_new_:
            m_['fclk'] = dict(m_.get('fclk') or {}, **fclk_new_)
        return m_

    pin_rec = None
    if V.get('pin_reach') and V.get('phys_relays'):
        # v13 (owner 2026-10-13: register at the pin -> wire <= 500 um -> register at the pin).  The passes above space
        # stations box to box; a hop into a pin on the far face of a wide block, between two long station faces at a
        # route corner, or from a block whose published face looks away, is longer between PINS.  pin_repair measures
        # every data net on the pin plans masters() gives this network (pin_points) and puts registered stations on
        # the pin-to-pin route of each net over the reach: each station goes as far along the route as the half
        # perimeter of its net (driver pins, the loads that stay, its own a face) allows; the chain continues from its
        # b face.  Rounds repeat until no data net is over (a pin that follows its peer moves to its new station).
        PLIM = float(V['pin_reach'])
        import numpy as _np
        if os.environ.get('OT_HBMDIE_TRACE'):
            print('pin_repair start', len(insts), 'insts', len(buses), 'buses', file=sys.stderr, flush=True)
        SL_ = float(V.get('pin_repair_slack', 12.0))
        pin_rec = dict(reach_um=PLIM, rounds=[], stations=0)
        Ag_ = G.graph(1.0 + V['phys_block_cost'] * (G.free < V.get('phys_free_min', 0.2)) + CG_)
        cell_k = lambda q_: min(G.ny - 1, max(0, int(q_[1] // RP.CELL))) * G.nx + min(G.nx - 1, max(0, int(q_[0] // RP.CELL)))
        cell_c = lambda k_: ((k_ % G.nx + .5) * RP.CELL, (k_ // G.nx + .5) * RP.CELL)
        hp_ = lambda ps_: max(q_[0] for q_ in ps_) - min(q_[0] for q_ in ps_) + max(q_[1] for q_ in ps_) - min(q_[1] for q_ in ps_)
        sp_pp = {}
        dead_e = set()      # load endpoints a chain could not advance to

        def ppath(pa, pb):
            """block-avoiding route cells from the cell of point pa to the cell of point pb"""
            ka, kb = cell_k(pa), cell_k(pb)
            if ka not in sp_pp:
                sp_pp[ka] = _dj(Ag_, indices=ka, return_predecessors=True)[1]
            pr_ = sp_pp[ka]
            pth = [kb]
            while pr_[pth[-1]] >= 0:
                pth.append(pr_[pth[-1]])
            return pth[::-1]
        sp_d = {}

        Ao_ = [Ag_, 0]

        def regraph():
            """the distance field's cost with the stations as they stand: a route cell whose block-free area is taken
            by stations costs up to 9x (a packed channel is no way through: the field on the blocks alone sent every
            chain along the 23-um strip left beside the multicast blocks of the SM columns, where no site exists)"""
            f_ = 10
            occ_ = _np.zeros((G.ny * f_, G.nx * f_), bool)
            for it_ in insts:
                if it_.kind != 'waypoint':
                    continue
                bx0, by0, bx1, by1 = it_.x - 2.0, it_.y - 2.0, it_.x + it_.w + 2.0, it_.y + it_.h + 2.0
                occ_[max(0, int(by0 / RP.CELL * f_)):int(math.ceil(by1 / RP.CELL * f_)),
                     max(0, int(bx0 / RP.CELL * f_)):int(math.ceil(bx1 / RP.CELL * f_))] = True
            ow_ = occ_.reshape(G.ny, f_, G.nx, f_).mean(axis=(1, 3))
            fill_ = _np.minimum(1.0, ow_ / _np.maximum(G.free, 0.05))
            Ao_[0] = G.graph(1.0 + V['phys_block_cost'] * (G.free < V.get('phys_free_min', 0.2)) +
                             8.0 * _np.maximum(0.0, fill_ - 0.25) / 0.75 + CG_ + pc_cost())
            Ao_[1] = len(insts)
            sp_d.clear()

        def dfield(kb):
            """block- and station-avoiding distance (um) of every route cell from cell kb, as a (ny, nx) array"""
            if len(insts) - Ao_[1] >= 400:
                regraph()
            if kb not in sp_d:
                if len(sp_d) > 300:
                    sp_d.clear()
                sp_d[kb] = _dj(Ao_[0], indices=kb).reshape(G.ny, G.nx)
            return sp_d[kb]

        def dscore(D, px, py):
            """distance to the field's source from die points (arrays): through the point's cell or a neighbour cell"""
            ci = _np.clip((px // RP.CELL).astype(int), 0, G.nx - 1)
            cj = _np.clip((py // RP.CELL).astype(int), 0, G.ny - 1)
            best = D[cj, ci] + _np.abs(px - (ci + .5) * RP.CELL) + _np.abs(py - (cj + .5) * RP.CELL)
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ni, nj = _np.clip(ci + di, 0, G.nx - 1), _np.clip(cj + dj, 0, G.ny - 1)
                best = _np.minimum(best, D[nj, ni] + _np.abs(px - (ni + .5) * RP.CELL) + _np.abs(py - (nj + .5) * RP.CELL))
            return best
        # 10.8-um site lattice (21.6 missed the 43-um strips beside the SM columns by 0.2 um: 2-b stations unplaced)
        _lat = [(ix_ * 10.8, iy_ * 10.8) for ix_ in range(-46, 47) for iy_ in range(-46, 47)
                if (abs(ix_) + abs(iy_)) * 10.8 <= PLIM]
        _lx, _ly = _np.array([q[0] for q in _lat]), _np.array([q[1] for q in _lat])
        MINADV = float(V.get('pin_repair_min_advance', 40.0))

        def unplace(nm_):
            st_ = by[nm_]
            ob_ = st_.box()
            for gx_ in range(int(ob_[0] // GS_), int(ob_[2] // GS_) + 1):
                for gy_ in range(int(ob_[1] // GS_), int(ob_[3] // GS_) + 1):
                    if ob_ in grid_[(gx_, gy_)]:
                        grid_[(gx_, gy_)].remove(ob_)
            insts.remove(st_)
            del by[nm_]
            G.inst.pop(nm_, None)
            new_rl.pop(nm_, None)

        _site_fail = {}

        def site_toward(bid, bits, cp_, tgt_, D, lim_, skip_=()):
            """place one family station of bus bid on the free site, within the pin reach of the pins cp_ (the half
            perimeter of cp_ + its a face), whose b face is nearest tgt_ on the field D; None when no free site
            advances by MINADV"""
            nonlocal nst
            rx_, ry_ = cp_[0]
            ln_ = up(rly_face_um(bits), GY) if V.get('rly_family') else up(max(21.6, bits * 0.048 + 20.0), GY)
            dph_, dpv_ = (rly_depth_um(bits, True), rly_depth_um(bits, False)) if V.get('rly_family') else (21.6, 21.6)
            px, py = rx_ + _lx, ry_ + _ly
            sc = dscore(D, px, py)
            cur = float(dscore(D, _np.array([rx_]), _np.array([ry_]))[0])
            fs_ = _site_fail
            fs_.update(cur=round(cur), best=round(float(sc.min())), tried=0, hp=0, hit=0, lim=round(lim_), hitby=None)
            for n_ in _np.argsort(sc, kind='stable'):
                if sc[n_] > cur - MINADV:
                    break
                cx_, cy_ = float(px[n_]), float(py[n_])
                if skip_ and any(abs(cx_ - q_[0]) + abs(cy_ - q_[1]) < 80.0 for q_ in skip_):
                    continue
                hz_ = abs(cx_ - rx_) >= abs(cy_ - ry_)
                for horiz in (hz_, not hz_):
                    sw_, sh_ = (dph_, ln_) if horiz else (up(ln_, GX), dpv_)
                    x_, y_ = dn(cx_ - sw_ / 2, GX), dn(cy_ - sh_ / 2, GY)
                    if x_ < 20 or y_ < 20 or x_ + sw_ > W_ - 20 or y_ + sh_ > H_ - 20:
                        continue
                    fl_ = ('E' if cx_ >= rx_ else 'W') if horiz else ('N' if cy_ >= ry_ else 'S')
                    apt_ = {'E': (x_, y_ + sh_ / 2), 'W': (x_ + sw_, y_ + sh_ / 2),
                            'N': (x_ + sw_ / 2, y_), 'S': (x_ + sw_ / 2, y_ + sh_)}[fl_]
                    fs_['tried'] += 1
                    if hp_(cp_ + [apt_]) > lim_:
                        fs_['hp'] += 1
                        continue
                    bx = (x_ - 2.0, y_ - 2.0, x_ + sw_ + 2.0, y_ + sh_ + 2.0)
                    if hit(bx, near(bx)):
                        fs_['hit'] += 1
                        if fs_['hitby'] is None:
                            fs_['hitby'] = [[round(v) for v in o] for o in near(bx)
                                            if bx[0] < o[2] and o[0] < bx[2] and bx[1] < o[3] and o[1] < bx[3]][:2]
                        continue
                    nm = f'wq{nst}_{bid}'
                    nst += 1
                    mst_ = f'hfd_stn_q{bid.split("_")[0]}{nst}' if bits > 1400 else f'hfd_stn_q{bits}{fl_}'
                    stnf_[mst_] = dict(a=_OPP[fl_], b=fl_)
                    if V.get('rly_family'):
                        stnf_[mst_].update(ck='S' if fl_ in 'EW' else 'W', rst='S' if fl_ in 'EW' else 'W')
                    st_ = Inst(nm, mst_, x_, y_, sw_, sh_, 'R0', kind='waypoint', region='channel')
                    b_ = st_.box()
                    for gx_ in range(int(b_[0] // GS_), int(b_[2] // GS_) + 1):
                        for gy_ in range(int(b_[1] // GS_), int(b_[3] // GS_) + 1):
                            grid_[(gx_, gy_)].append(b_)
                    insts.append(st_)
                    by[nm] = st_
                    G.inst[nm] = st_
                    new_rl[nm] = bid
                    pc_seg((rx_, ry_), apt_, bits)
                    return nm
            return None
        if V.get('rly_family'):
            # v13 r7: the box-era relay banks do not survive the family outline.  A lane-group chain bank (wq*_lg*: one
            # strip registering rdn 2,067 + wdn 19 + rup 131 + wup 2,243 b) is 1,832 um long at 0.096 um a bit: it
            # walls its channel and two of the 34 found no site at all (left on top of hb_su_NW / hb_vms_NW).  A bank
            # is only a register stage of four independent nets, so it is DISSOLVED: each net runs through (in -> out
            # joined) and the rounds below stage it with family tiles on free sites.  The same for any other box-era
            # station that overlaps a block or a station.
            def _ovl(it_):
                b_ = it_.box()
                return any(o != b_ and b_[0] < o[2] - 0.01 and o[0] < b_[2] - 0.01 and b_[1] < o[3] - 0.01 and o[1] < b_[3] - 0.01
                           for o in near(b_))
            gone_ = [it_ for it_ in insts if it_.kind == 'waypoint' and it_.master.startswith('hfd_stn_q') and
                     (re.fullmatch(r'wq\d+_lg(?:SW|SE|NW|NE|W|E)\d*', it_.name) or _ovl(it_))]
            n_dis = 0
            for it_ in gone_:
                nm_ = it_.name
                tb_ = [(i_, b_) for i_, b_ in enumerate(buses) if any(e[0] == nm_ for e in b_[3])]
                if any('@' in e[1] or b_[1] in ('clock_trunk', 'reset_tree') for _, b_ in tb_ for e in b_[3] if e[0] == nm_):
                    continue
                ins_ = {e[1]: i_ for i_, b_ in tb_ for e in b_[3][1:] if e[0] == nm_}
                outs_ = {b_[3][0][1]: i_ for i_, b_ in tb_ if b_[3][0][0] == nm_}
                pair_ = lambda p_: 'b' if p_ == 'a' else ('t' + p_[1:] if p_.startswith('f_') else None)
                if any(pair_(p_) is None for p_ in ins_) or any(o_ not in {pair_(p_) for p_ in ins_} for o_ in outs_):
                    continue
                drop_ = set()
                for p_, i_ in ins_.items():
                    bi_ = buses[i_]
                    eps_ = [e for e in bi_[3] if e != (nm_, p_)]
                    o_ = outs_.get(pair_(p_))
                    if o_ is not None:
                        eps_ += list(buses[o_][3][1:])
                        drop_.add(o_)
                    buses[i_] = (bi_[0], bi_[1], bi_[2], eps_)
                buses[:] = [b_ for i_, b_ in enumerate(buses) if i_ not in drop_]
                unplace(nm_)
                n_dis += 1
            pin_rec['dissolved_box_stations'] = n_dis
            if os.environ.get('OT_HBMDIE_TRACE'):
                print('dissolved', n_dis, 'of', len(gone_), 'box-era stations', file=sys.stderr, flush=True)
        for _pr in range(V.get('pin_repair_rounds', 10)):
            P_ = pin_points(_model(), 16)

            P0_ = P_

            def P_(i_, p_):     # a slice made this round has no pins yet: its port's own centroid until the next round
                q_ = P0_(i_, p_)
                return P0_(i_, port_base(p_)) if q_ is None and '@' in p_ else q_

            def ept(e):
                q_ = P_(e[0], e[1])
                if q_ is None:      # a pin-less placeholder end: its box point nearest the die centre of the net
                    it_ = by[e[0]]
                    q_ = (it_.x + it_.w / 2, it_.y + it_.h / 2)
                return q_

            def sub_port(port, lo, hi):
                """bus bits lo..hi of an endpoint port, as a slice of that port"""
                idx = port_idx(port)
                sel = list(range(lo, hi + 1)) if idx is None else idx[lo:hi + 1]
                rg, a_ = [], sel[0]
                for u_, v_ in zip(sel, sel[1:] + [None]):
                    if v_ != u_ + 1:
                        rg.append(f'{a_}:{u_}')
                        a_ = v_
                return port_base(port) + '@' + ','.join(rg)
            nb_, n_bad, n_new, n_stuck, n_noprog, n_dead, worst_, n_split = [], 0, 0, 0, 0, 0, 0.0, 0
            _t0 = time.time()
            work_, wi_ = list(buses), 0
            regraph()
            mcount_ = defaultdict(int)
            for it_ in insts:
                mcount_[it_.master] += 1
            while wi_ < len(work_):
                b_ = work_[wi_]
                wi_ += 1
                bid, cls, bits, eps = b_
                ends_ = [e for e in eps if e[0] in by]
                if cls in ('clock_trunk', 'reset_tree') or len(ends_) < 2 or eps[0][0] not in by or \
                        len({e[0] for e in ends_}) < 2:
                    nb_.append(b_)
                    continue
                pts_ = {e: ept(e) for e in ends_}
                if any(P_(e[0], e[1]) is None for e in ends_):     # placeholder end: box nearest point (the lint's measure)
                    kn_ = [P_(e[0], e[1]) for e in ends_ if P_(e[0], e[1]) is not None] or list(pts_.values())
                    cx_, cy_ = sum(q[0] for q in kn_) / len(kn_), sum(q[1] for q in kn_) / len(kn_)
                    pts_ = {e: (P_(e[0], e[1]) or _near_pt(by[e[0]], (cx_, cy_))) for e in ends_}
                L0_ = hp_(list(pts_.values()))
                if L0_ <= PLIM - 1.0:
                    nb_.append(b_)
                    continue
                if all(e in dead_e for e in ends_[1:] if _mh2(pts_[eps[0]], pts_[e]) > PLIM - SL_):
                    n_dead += 1         # only loads already found unreachable: reported, not tried again
                    nb_.append(b_)
                    continue
                if bits > RLY_CLASSES[-1] and V.get('rly_family') and bid not in fcl_ and bid not in fclk_new_ and all(e[0] in by for e in eps) and \
                        all((by[e[0]].master.startswith('hfd_stn_q') and port_base(e[1]) in ('a', 'b') or
                             by[e[0]].master.startswith('hfd_stn_lg') and mcount_[by[e[0]].master] == 1
                             if by[e[0]].kind == 'waypoint' else mcount_[by[e[0]].master] == 1) for e in eps):
                    for e in eps:       # a station of a shared master gets its own (its ports are sliced, the others' not)
                        it_ = by[e[0]]
                        if it_.kind == 'waypoint' and mcount_[it_.master] > 1:
                            mcount_[it_.master] -= 1
                            nm2_ = f'{it_.master}_u{it_.name.split("_")[0]}'
                            if it_.master in stnf_:
                                stnf_[nm2_] = dict(stnf_[it_.master])
                            it_.master = nm2_
                            mcount_[nm2_] = 1
                    # (H-DIE 10-14: a segment forwarded after the fcl_ snapshot (fclk_new_) is never sliced into common-clock
                    #  tiles: the slices carried its forwarded-clock positions as data, 5 phantom bits at the launch)
                    # v13 r7: a bus wider than the widest family tile (1,136 b) travels as that many tile-wide slices,
                    # each on its own chain of single tiles (109 x 21.6 um).  One strip of tiles side by side (2,068 b
                    # = 229 um, 4,206 b = 458 um) found no site in the hub channels; tiles of one bus need not abut.
                    ns_ = math.ceil(bits / RLY_CLASSES[-1])
                    ch_ = math.ceil(bits / ns_ / 16) * 16
                    for s_ in range(ns_):
                        lo_, hi_ = s_ * ch_, min(bits, (s_ + 1) * ch_) - 1
                        if hi_ >= lo_:
                            work_.append((f'{bid}_w{s_}', cls, hi_ - lo_ + 1, [(e[0], sub_port(e[1], lo_, hi_)) for e in eps]))
                    n_split += 1
                    continue
                n_bad += 1
                worst_ = max(worst_, L0_)
                d0 = eps[0]
                keep = [d0]
                kpts = [pts_[d0]]
                # loads nearest the driver stay on the net while its half perimeter allows; the others get a chain
                far_ = []
                for e in sorted(ends_[1:], key=lambda e_: _mh2(pts_[d0], pts_[e_])):
                    if not far_ and hp_(kpts + [pts_[e]]) <= PLIM - SL_:
                        keep.append(e)
                        kpts.append(pts_[e])
                    else:
                        far_.append(e)
                keep += [e for e in eps[1:] if e[0] not in by]
                # v13 r7: the far loads hang on a TREE of stations.  A node is the driver net or the b net of a station
                # of this bus; each far load starts from the node nearest it on the block-avoiding distance field of
                # its own cell (dfield) and gets a chain of stations from there, every station on the FREE site within
                # the pin reach of its node's pins that is nearest the load.  No fixed route and no legaliser: a
                # chain is complete (every hop within the reach, pin to pin) or absent (its load is reported).  The
                # driver net shares its reach between the directions its far loads leave in (a first station at the
                # full reach toward one load leaves no half perimeter for a load on the other side).
                nodes = {None: dict(pts=kpts, loads=keep)}
                order_ = []
                sect_ = lambda q_: (('E' if q_[0] >= pts_[d0][0] else 'W') if abs(q_[0] - pts_[d0][0]) >= abs(q_[1] - pts_[d0][1])
                                    else ('N' if q_[1] >= pts_[d0][1] else 'S'))
                for j_, e in enumerate(far_):
                    tgt_ = pts_[e]
                    D_ = dfield(cell_k(tgt_))
                    cand_n = sorted(nodes, key=lambda n_: float(dscore(D_, _np.array([nodes[n_]['pts'][0][0]]),
                                                                       _np.array([nodes[n_]['pts'][0][1]]))[0]))[:3]
                    done_ = False
                    for n0_ in cand_n:
                        nd_ = nodes[n0_]
                        if hp_(nd_['pts'] + [tgt_]) <= PLIM - SL_:
                            nd_['loads'].append(e)
                            nd_['pts'].append(tgt_)
                            done_ = True
                            break
                        lim1_ = PLIM - SL_
                        if n0_ is None:
                            dirs_ = len({sect_(pts_[e2_]) for e2_ in far_[j_:]})
                            lim1_ = hp_(kpts) + max(80.0, (PLIM - SL_ - hp_(kpts)) / dirs_)
                        cur_pts, rl = list(nd_['pts']), []
                        # depth-first with backtracking: a chain that runs into a full pocket takes its last station
                        # off and tries the next-best site at least 80 um from it (<= 40 steps back a chain)
                        skips_, nbt_ = [[]], 0
                        while hp_(cur_pts + [tgt_]) > PLIM - SL_ and len(rl) < 200:
                            nm_ = site_toward(bid, bits, cur_pts, tgt_, D_, lim1_ if not rl else PLIM - SL_, skips_[-1])
                            if nm_ is None:
                                if not rl or nbt_ >= 40:
                                    break
                                st_ = by[rl.pop()]
                                skips_.pop()
                                skips_[-1].append((st_.x + st_.w / 2, st_.y + st_.h / 2))
                                unplace(st_.name)
                                nbt_ += 1
                                cur_pts = [face_pt(by[rl[-1]], stnf_[by[rl[-1]].master]['b'])] if rl else list(nd_['pts'])
                                continue
                            st_ = by[nm_]
                            rl.append(nm_)
                            skips_.append([])
                            cur_pts = [face_pt(st_, stnf_[st_.master]['b'])]
                        if hp_(cur_pts + [tgt_]) > PLIM - SL_:      # a full pocket / a pin no free site reaches: undo
                            for nm_ in rl:
                                unplace(nm_)
                            continue
                        nd_['loads'].append((rl[0], 'a'))
                        nd_['pts'].append(face_pt(by[rl[0]], stnf_[by[rl[0]].master]['a']))
                        for k_, nm_ in enumerate(rl):
                            nx_e = (rl[k_ + 1], 'a') if k_ + 1 < len(rl) else e
                            nx_p = face_pt(by[rl[k_ + 1]], stnf_[by[rl[k_ + 1]].master]['a']) if k_ + 1 < len(rl) else tgt_
                            nodes[nm_] = dict(pts=[face_pt(by[nm_], stnf_[by[nm_].master]['b']), nx_p], loads=[nx_e])
                            order_.append(nm_)
                        n_new += len(rl)
                        done_ = True
                        break
                    if not done_:
                        n_noprog += 1
                        if os.environ.get('OT_HBMDIE_TRACE') == '2':
                            print('DEAD', bid, bits, d0, [round(v) for v in pts_[d0]], e, [round(v) for v in tgt_],
                                  len(far_), dict(_site_fail), file=sys.stderr, flush=True)
                        dead_e.add(e)
                        keep.append(e)      # stays on the driver net (reported over the reach); not in the node's box
                for c_, nm_ in enumerate(order_):
                    nid_ = f'{bid}_q{_pr}n{c_}'
                    nb_.append((nid_, cls, bits, [(nm_, 'b')] + nodes[nm_]['loads']))
                    if bid in fcl_ or bid in fclk_new_:     # H-DIE 1014pm: a segment split after the fcl_ snapshot
                        fclk_new_[nid_] = fcl_.get(bid) or fclk_new_[bid]
                nb_.append((bid, cls, bits, keep))
            buses[:] = nb_
            pin_rec['rounds'].append(dict(nets_over=n_bad, worst_um=round(worst_, 1), stations=n_new, stuck=n_stuck,
                                          no_progress=n_noprog, unreachable=n_dead, wide_split=n_split))
            if os.environ.get('OT_HBMDIE_TRACE'):
                print('pin_repair round', _pr, pin_rec['rounds'][-1], round(time.time() - _t0), 's', file=sys.stderr, flush=True)
            pin_rec['stations'] += n_new
            phys_rec['data_relays'] += n_new
            if not n_bad:
                break
        if V.get('lane_align'):
            # v13 r8 (pin_align: 237 FAIL bundles, all relay to relay).  Two consecutive stations whose registered
            # faces LOOK AT EACH OTHER (b of one, a of the next, the same flow axis) but sit off each other's lane need
            # a jog wire a bit in the gap between the two faces; at 0.096 um a bit a 36-um offset of a 378-b bus already
            # fills 0.60 of a 20-um gap (tools/hier_contract/pin_align.py judge), and the rest spills over the tiles.
            # A chain that turns is fine (perpendicular faces: an L).  Here every such pair is put on one lane: the
            # downstream station slides across the flow onto the upstream b row (else the upstream one onto the
            # downstream a row) when the site is free, every net of the moved station stays within the pin reach, and
            # the move leaves fewer off-lane pairs than it found.
            Pq_ = pin_points(_model(), 16)
            touch_ = defaultdict(list)
            for b_ in buses:
                if b_[1] in ('clock_trunk', 'reset_tree'):
                    continue
                for e in b_[3]:
                    if e[0] in by and by[e[0]].kind == 'waypoint':
                        touch_[e[0]].append(b_)

            def sface(e):
                it_ = by.get(e[0])
                if it_ is None or it_.kind != 'waypoint' or '@' in e[1]:
                    return None
                f_ = (stnf_.get(it_.master) or {}).get(e[1])
                return (f_, face_pt(it_, f_)) if f_ in _OPP and e[1] in ('a', 'b') else None

            def offlane(b_):
                """[(driver end, load end, axis across the flow, jog um)] of the facing station pairs of a bus that fail"""
                out_ = []
                A_ = sface(b_[3][0])
                if A_ is None:
                    return out_
                for e in b_[3][1:]:
                    B_ = sface(e)
                    if B_ is None or A_[0] != _OPP[B_[0]]:
                        continue
                    t_ = 0 if A_[0] in 'EW' else 1
                    gap_ = (B_[1][t_] - A_[1][t_]) * (1 if A_[0] in 'EN' else -1)
                    jog_ = B_[1][1 - t_] - A_[1][1 - t_]
                    if gap_ < -0.01 or abs(jog_) <= 20.0:
                        continue
                    if min(b_[2], math.ceil(abs(jog_) / RLY_PIN_UM)) <= 0.6 * 31.51 * gap_:
                        continue
                    out_.append((b_[3][0], e, 1 - t_, jog_))
                return out_

            def reach_ok(nm_):
                for b_ in touch_[nm_]:
                    ps_ = []
                    for e in b_[3]:
                        if e[0] not in by:
                            continue
                        s_ = sface(e)
                        q_ = s_[1] if s_ else (Pq_(e[0], e[1]) or _near_pt(by[e[0]], face_pt(by[nm_], 'W')))
                        ps_.append(q_)
                    if len(ps_) > 1 and hp_(ps_) > PLIM - 1.0:
                        return False
                return True

            def slide(nm_, ax_, d_):
                """move station nm_ by d_ um along axis ax_ if legal; returns True when it leaves fewer off-lane pairs"""
                st_ = by[nm_]
                n0_ = sum(len(offlane(b_)) for b_ in touch_[nm_])
                ob_, ox_, oy_ = st_.box(), st_.x, st_.y
                nx_, ny_ = (dn(ox_ + d_ + GX / 2, GX), oy_) if ax_ == 0 else (ox_, dn(oy_ + d_ + GY / 2, GY))
                if nx_ < 20 or ny_ < 20 or nx_ + st_.w > W_ - 20 or ny_ + st_.h > H_ - 20:
                    return False
                for gx_ in range(int(ob_[0] // GS_), int(ob_[2] // GS_) + 1):
                    for gy_ in range(int(ob_[1] // GS_), int(ob_[3] // GS_) + 1):
                        if ob_ in grid_[(gx_, gy_)]:
                            grid_[(gx_, gy_)].remove(ob_)
                bx = (nx_ - 2.0, ny_ - 2.0, nx_ + st_.w + 2.0, ny_ + st_.h + 2.0)
                ok_ = not hit(bx, near(bx))
                if ok_:
                    st_.x, st_.y = nx_, ny_
                    ok_ = reach_ok(nm_) and sum(len(offlane(b_)) for b_ in touch_[nm_]) < n0_
                    if not ok_:
                        st_.x, st_.y = ox_, oy_
                nb2_ = st_.box()
                for gx_ in range(int(nb2_[0] // GS_), int(nb2_[2] // GS_) + 1):
                    for gy_ in range(int(nb2_[1] // GS_), int(nb2_[3] // GS_) + 1):
                        grid_[(gx_, gy_)].append(nb2_)
                return ok_
            _fam_re = re.compile(r'hfd_stn_q(\d+)([NSEW])$')

            def turn(nm_, fl_):
                """re-orient family station nm_ in place to flow toward fl_ (its a face then looks back along the
                jog: the facing pair becomes an L, one horizontal and one vertical segment a bit, no jog in the gap);
                True when legal and it leaves fewer off-lane pairs"""
                st_ = by[nm_]
                mm_ = _fam_re.match(st_.master)
                if not mm_ or mm_.group(2) == fl_ or not V.get('rly_family'):
                    return False
                bits_ = int(mm_.group(1))
                n0_ = sum(len(offlane(b_)) for b_ in touch_[nm_])
                hz_ = fl_ in 'EW'
                ln_ = up(rly_face_um(bits_), GY)
                sw_, sh_ = (rly_depth_um(bits_, True), ln_) if hz_ else (up(ln_, GX), rly_depth_um(bits_, False))
                old_ = (st_.x, st_.y, st_.w, st_.h, st_.master)
                ob_ = st_.box()
                nx_, ny_ = dn(st_.x + st_.w / 2 - sw_ / 2, GX), dn(st_.y + st_.h / 2 - sh_ / 2, GY)
                if nx_ < 20 or ny_ < 20 or nx_ + sw_ > W_ - 20 or ny_ + sh_ > H_ - 20:
                    return False
                for gx_ in range(int(ob_[0] // GS_), int(ob_[2] // GS_) + 1):
                    for gy_ in range(int(ob_[1] // GS_), int(ob_[3] // GS_) + 1):
                        if ob_ in grid_[(gx_, gy_)]:
                            grid_[(gx_, gy_)].remove(ob_)
                bx = (nx_ - 2.0, ny_ - 2.0, nx_ + sw_ + 2.0, ny_ + sh_ + 2.0)
                ok_ = not hit(bx, near(bx))
                if ok_:
                    mst_ = f'hfd_stn_q{bits_}{fl_}'
                    stnf_.setdefault(mst_, dict(a=_OPP[fl_], b=fl_, ck='S' if hz_ else 'W', rst='S' if hz_ else 'W'))
                    st_.x, st_.y, st_.w, st_.h, st_.master = nx_, ny_, sw_, sh_, mst_
                    ok_ = reach_ok(nm_) and sum(len(offlane(b_)) for b_ in touch_[nm_]) < n0_
                    if not ok_:
                        st_.x, st_.y, st_.w, st_.h, st_.master = old_
                nb2_ = st_.box()
                for gx_ in range(int(nb2_[0] // GS_), int(nb2_[2] // GS_) + 1):
                    for gy_ in range(int(nb2_[1] // GS_), int(nb2_[3] // GS_) + 1):
                        grid_[(gx_, gy_)].append(nb2_)
                return ok_
            la_rec = dict(rounds=[])
            for _la in range(6):
                bad_ = [o_ for b_ in buses if b_[1] not in ('clock_trunk', 'reset_tree') for o_ in offlane(b_)]
                moved_ = turned_ = 0
                for A_, B_, ax_, jog_ in bad_:
                    if not any(o_[0] == A_ and o_[1] == B_ for b_ in touch_[B_[0]] for o_ in offlane(b_)):
                        continue        # an earlier move of this round already put the pair right
                    if slide(B_[0], ax_, -jog_) or slide(A_[0], ax_, jog_):
                        moved_ += 1
                        continue
                    # the wires leave A toward the jog side: B (or A) turned to flow that way makes the pair an L
                    fj_ = ('N' if jog_ > 0 else 'S') if ax_ == 1 else ('E' if jog_ > 0 else 'W')
                    if turn(B_[0], fj_) or turn(A_[0], fj_):
                        turned_ += 1
                la_rec['rounds'].append(dict(off_lane_pairs=len(bad_), moved=moved_, turned=turned_))
                if not moved_ and not turned_:
                    break
            la_rec['off_lane_left'] = sum(len(offlane(b_)) for b_ in buses if b_[1] not in ('clock_trunk', 'reset_tree'))
            pin_rec['lane_align'] = la_rec
            if os.environ.get('OT_HBMDIE_TRACE'):
                print('lane_align', la_rec, file=sys.stderr, flush=True)
        pin_rec['unreachable_loads'] = sorted(f'{e_[0]}.{e_[1]}' for e_ in dead_e)[:400]
        pin_rec['stations_on_lane'] = nal_[0]
        phys_rec['pin_repair'] = pin_rec
        if os.environ.get('OT_HBMDIE_STOP') == 'pin':
            m_ = _model()
            ph_ = pin_hop_lint(m_, limit=4000)
            json.dump(ph_, open(os.environ.get('OT_HBMDIE_STOP_OUT', '/dev/null'), 'w'), indent=1)
            print(json.dumps({k_: v_ for k_, v_ in ph_.items() if k_ != 'examples'}, indent=1), file=sys.stderr)
            print(json.dumps(_legality(m_))[:3000], file=sys.stderr)
            import pickle as _pk
            Pd_ = pin_points(m_, 16)
            _pk.dump(dict(insts={i.name: (i.master, i.kind, i.x, i.y, i.w, i.h, i.orient) for i in insts},
                          buses=[(b_[0], b_[1], b_[2], list(b_[3])) for b_ in buses], stnf=dict(stnf_), dead=sorted(dead_e),
                          pts={(b_[0], e_): Pd_(e_[0], e_[1]) for b_ in buses for e_ in b_[3] if e_[0] in by},
                          free=G.free, cell=RP.CELL),
                     open(os.environ.get('OT_HBMDIE_STOP_OUT', '/dev/null') + '.pkl', 'wb'))
            raise SystemExit('OT_HBMDIE_STOP=pin')
    # OT_HBMDIE_NO_TREES=1: data-placement iterations only (window check of data hops, which never counts the clock /
    # reset trees): skip the tree build (~70 of the ~75 generator minutes on v14).  Never for a case, GRT or netlist.
    if (V.get('phys_trees') or V.get('phys_relays')) and not os.environ.get('OT_HBMDIE_NO_TREES'):
        phys_rec = phys_rec or {}
        # textbook audit rows 2 + 3: per clock domain ONE balanced H-tree from the PLL port on hb_coll to region leaves
        # (leaf cells <= 480 um, empty branches pruned).  Every tree node carries a clock buffer (hfd_ckb) and, beside
        # it, a registered reset relay (hfd_rrl, clocked by that buffer): the reset is a pipelined regional tree, never a
        # die-wide net.  Edges get buffer / relay pairs every <= LINK_STAGE_UM, so sibling paths are equal (balanced).
        # Leaves drive the block ck / rst pins of their cell and the common-clock data relays.
        coll_ = next(i for i in insts if i.name == V.get('ck_root', 'hb_coll') and (V.get('ck_root') or i.kind == 'spine'))
        ck_sinks, rs_sinks, keep_b = defaultdict(list), defaultdict(list), []
        # v13 (pin_reach): the trees are built to the sinks' PINS (pin plans of this network, before the trees: a
        # block's ck / rst pin is where the die-wide net put it and pin_hold keeps it there), not to the block point
        # nearest the die-wide net's centroid -- a leaf then sits within reach of the pin it drives
        Pt_ = pin_points(_model(), 16) if V.get('pin_reach') else None
        if os.environ.get('OT_HBMDIE_TRACE'):
            print('trees start', len(insts), 'insts', file=sys.stderr, flush=True)

        def sink_pt(e):
            it_ = by[e[0]]
            q_ = Pt_(e[0], e[1]) if Pt_ is not None else None
            if q_ is None and Pt_ is not None and (stnf_.get(it_.master) or {}).get(e[1]):
                q_ = face_pt(it_, stnf_[it_.master][e[1]])
            if q_ is None:
                q_ = pin_pt.get(e, (it_.x + it_.w / 2, it_.y + it_.h / 2))
            return q_
        # block ck / rst pins keep the position the die-wide net gave them (their peers on the old net), so no data pin
        # of a block moves; the block attaches to the tree leaf at that pin (the block point nearest the old peers)
        pin_hold, pin_pt = {}, {}
        first_of = {}
        for it_ in insts:
            first_of.setdefault(it_.master, it_)
        for b_ in buses:
            if b_[1] in ('clock_trunk', 'reset_tree') and (b_[0].startswith('clk_') or b_[0].startswith('rst_')):
                es_ = [e for e in b_[3] if e[0] in by]
                if not es_:
                    continue
                sx_ = sum(by[e[0]].x + by[e[0]].w / 2 for e in es_)
                sy_ = sum(by[e[0]].y + by[e[0]].h / 2 for e in es_)
                eps_ = b_[3]
                if V.get('hc_ck_ew') and b_[1].startswith('clock'):     # as the hc_ck_ew pass below will expand them
                    eps_ = [x for e in eps_ for x in ([(e[0], e[1] + 'e'), (e[0], e[1] + 'w')]
                                                       if e[0].startswith('hb_hc_') and re.fullmatch(r'ck\d', e[1]) else [e])]
                for i_, e in enumerate(eps_):           # the PLL source port on hb_coll too
                    if e[0] not in by:
                        continue
                    it = by[e[0]]
                    n_ = len(es_) - 1
                    ox_ = (sx_ - (it.x + it.w / 2)) / max(1, n_)
                    oy_ = (sy_ - (it.y + it.h / 2)) / max(1, n_)
                    if it.kind != 'waypoint':       # blocks attach at their held pin; stations at their centre
                        pin_pt[e] = (min(max(ox_, it.x), it.x + it.w), min(max(oy_, it.y), it.y + it.h))
                    # exactly the peers masters() saw on the old net: every other endpoint by index (same inst's other
                    # ports and repeats included), per copy
                    pin_hold.setdefault(f'{it.master}|{e[1]}|{it.name}', []).extend(
                        x[0] for j_, x in enumerate(eps_) if j_ != i_ and x[0] != 'TOP')
        for b_ in buses:
            if b_[1] == 'clock_trunk' and b_[0].startswith('clk_'):
                ck_sinks[b_[0][4:]] += [e for e in b_[3][1:]]
            elif b_[1] == 'reset_tree' and b_[0].startswith('rst_'):
                rs_sinks[b_[0][4:]] += [e for e in b_[3][1:]]
            else:
                keep_b.append(b_)
        dom_of = {}
        for d_, es_ in ck_sinks.items():
            for e in es_:
                dom_of.setdefault(e[0], d_)
        # Pin repair creates new forwarded segments after fcl_ was snapshotted.
        # Use the complete current map for clock admission AND circuit-master selection.
        fcl_live_ = dict(fcl_, **fclk_new_)
        isf_ = lambda b: b in fcl_live_ or b.split('_p')[0] in fcl_live_ or re.sub(r'_(t|r)?\d+$', '', b) in fcl_live_
        for r_, bid in new_rl.items():      # new relays: reset always, clock unless the bus forwards its clock
            b0_ = bid.split('_p')[0]
            drv_ = next((b_[3][0][0] for b_ in buses if b_[0] == b0_), None)
            d_ = dom_of.get(drv_) or 'stream'
            rs_sinks[d_].append((r_, 'rst'))
            if not isf_(bid):
                ck_sinks[d_].append((r_, 'ck'))
        # hbmdie-v10-sta 2026-10-12 (the kv_die 758ccc84c pattern): the Option-A chain stations of relays() (wq*_<bid>,
        # hfd_stn_q*) and the attention -> SU relays (hfd_att_su_relay) are register stages but joined no clock net, so
        # their masters had no ck pin and the die STA could time none of their hops (v10: 3,512 of 6,388 stations).
        # Each one now joins the clock tree of the domain of the first non-station driver up its chain, unless a bus
        # on that chain forwards its clock (fclk: source-synchronous, clock in the a/b bits) or it is a forwarded
        # station (fwd_dom).
        ckd_ = {e[0] for es_ in ck_sinks.values() for e in es_}
        byl_ = {i.name: i for i in insts}
        isr_ = lambda n: n in byl_ and (byl_[n].master.startswith('hfd_stn') or byl_[n].master == 'hfd_att_su_relay')
        inb_ = {}
        for b_ in buses:
            if len(b_[3]) == 2 and b_[1] not in ('clock_trunk', 'reset_tree'):
                inb_.setdefault(b_[3][1][0], (b_[0], b_[3][0][0]))
        phys_rec['stations_clock_added'] = phys_rec['stations_forwarded'] = 0
        for it_ in insts:
            if not isr_(it_.name) or it_.name in ckd_ or it_.name in (base.get('fwd_dom') or {}):
                continue
            cur_, fwd_, seen_ = it_.name, False, set()
            while cur_ in inb_ and cur_ not in seen_:
                seen_.add(cur_)
                bid_, cur_ = inb_[cur_]
                fwd_ = fwd_ or isf_(bid_)
                if not isr_(cur_):
                    break
            if fwd_:
                phys_rec['stations_forwarded'] += 1
                if V.get('fwd_master_split') and not it_.master.endswith('F'):
                    # v14 (OWNER NO STUBS): a forwarded-clock station is a different circuit (ot_hbm_stn_fwd / launch /
                    # meso, clock in its a / b bits) from a common-clock relay of the same width class: own master
                    om_ = it_.master
                    it_.master = om_ + 'F'
                    if om_ in stnf_:
                        stnf_[it_.master] = dict(stnf_[om_])
                continue
            ck_sinks[dom_of.get(cur_) or 'stream'].append((it_.name, 'ck'))
            phys_rec['stations_clock_added'] += 1
        old_order = list(buses)        # tree nets go where the die-wide net they replace sat (masters() packs a face's
        buses[:] = keep_b               # ports in first-seen order: the block pin plans stay identical)
        tree_nets = defaultdict(list)
        CKW, CKH = 12.96, 12.96        # >= 3 generated 1-b pins + gaps a face in the k = 16 bundled view
        tree_rec = {}

        def free_at(x_, y_, w_, h_):
            bx = (x_ - 1.0, y_ - 1.0, x_ + w_ + 1.0, y_ + h_ + 1.0)
            return not (x_ < 20 or y_ < 20 or x_ + w_ > W_ - 20 or y_ + h_ > H_ - 20 or hit(bx, near(bx)))

        def occupy(it):
            b_ = it.box()
            for gx_ in range(int(b_[0] // GS_), int(b_[2] // GS_) + 1):
                for gy_ in range(int(b_[1] // GS_), int(b_[3] // GS_) + 1):
                    grid_[(gx_, gy_)].append(b_)

        blk_boxes_ = [i_.box() for i_ in insts if i_.kind != 'waypoint']
        TC_ = bool(V.get('tree_cap') and V.get('phys_relays') and V.get('phys_block_cost'))
        tcap_rec = None
        if TC_:
            import numpy as _np
            wide_, widef_ = tree_wide_mask(blk_boxes_, W_, H_, G.nx, G.ny, RP.CELL)
            WCU_ = RP.CELL / 10
            tocc_ = _np.zeros((G.ny, G.nx))         # waypoint (station + pair) area per route cell / cell area
            tstall_ = _np.zeros((G.ny, G.nx))       # stalls recorded per route cell (closes it for the tree)
            for it_ in insts:
                if it_.kind == 'waypoint':
                    i_, j_ = int((it_.x + it_.w / 2) // RP.CELL), int((it_.y + it_.h / 2) // RP.CELL)
                    if 0 <= i_ < G.nx and 0 <= j_ < G.ny:
                        tocc_[j_, i_] += it_.w * it_.h / RP.CELL ** 2
            tg_ = dict(A=None, n=0, n0=0, dirty=False, builds=0)
            tspt_ = {}
            tcap_rec = dict(stalls=0, reroutes=0, pads_open=0, pads_any=0, pads_at_child=0, edges_capped=0)
            tpairs_ = _np.zeros((G.ny, G.nx), int)  # tree pairs per route cell (the per-channel count)

            def is_open(x_, y_):
                """the site centre lies in open (>= TREE_WIDE_UM) space and its route cell is not full"""
                jj_, ii_ = int(y_ // WCU_), int(x_ // WCU_)
                if not (0 <= jj_ < wide_.shape[0] and 0 <= ii_ < wide_.shape[1] and wide_[jj_, ii_]):
                    return False
                j_, i_ = int(y_ // RP.CELL), int(x_ // RP.CELL)
                return tocc_[j_, i_] < TREE_FULL * max(G.free[j_, i_], 0.05)

            def troute(a, b):
                """route a -> b on the capacity-aware cost (rebuilt after a stall or every 12 placed pairs)"""
                if tg_['A'] is None or tg_['dirty'] or tg_['n'] - tg_['n0'] >= 12:
                    tg_.update(A=G.graph((tree_fp_cost if V.get('tree_fixed_path') else tree_cap_cost)(
                                   G.free, tocc_, tstall_, widef_, V['phys_block_cost'], V.get('phys_free_min', 0.2))),
                               n0=tg_['n'], dirty=False, builds=tg_['builds'] + 1)
                    tspt_.clear()
                ra = rings.setdefault(a, G.ring(a))
                rb = rings.setdefault(b, G.ring(b))
                if a not in tspt_:
                    tspt_[a] = _dj(tg_['A'], indices=ra, min_only=True, return_predecessors=True)[:2]
                d2_, pr_ = tspt_[a]
                k_ = min(rb, key=lambda x: d2_[x])
                pth = [k_]
                while pr_[pth[-1]] >= 0:
                    pth.append(pr_[pth[-1]])
                return pth[::-1]

        def pad_site(a_, b_, open_only):
            """tree_cap: a free pair site within one stage of BOTH a_ and b_ (consecutive pairs of one tree edge),
            nearest their midpoint; open_only = only in open (>= TREE_WIDE_UM, not full) space.  None if there is none."""
            pw_ = 2 * CKW + 4.32
            mx_ = (a_.x + a_.w / 2 + b_.x + b_.w / 2) / 2
            my_ = (a_.y + a_.h / 2 + b_.y + b_.h / 2) / 2
            tmp_ = Inst('_t', 'x', 0.0, 0.0, pw_, CKH, 'R0', kind='waypoint')
            for ox, oy in _PAD_RING:
                x_, y_ = dn(mx_ + ox * 21.6 - pw_ / 2, GX), dn(my_ + oy * 21.6 - CKH / 2, GY)
                if open_only and not is_open(x_ + pw_ / 2, y_ + CKH / 2):
                    continue
                tmp_.x, tmp_.y = x_, y_
                if eseg(a_, tmp_) > 400.0 or eseg(b_, tmp_) > 400.0:
                    continue
                if free_at(x_, y_, pw_, CKH):
                    return x_, y_
            return None

        def pair_at(nm_ck, nm_rr, x, y, cells=None, anc=None, anc2=None, pad=False, branch=False, site=None):
            """a clock buffer + its reset relay side by side (one 13 x 4.3 um footprint): first on the given route cells
            near (x, y), else the spiral legaliser on the pair footprint"""
            pw_ = 2 * CKW + 4.32
            cands = []
            if cells:
                for kk_ in cells:
                    j_, i_ = divmod(kk_, G.nx)
                    cands.append(((i_ + .5) * RP.CELL, (j_ + .5) * RP.CELL))
            cands.append((x, y))
            px = py = None
            if site is not None:
                px, py = site
            if TC_ and anc is None and branch:
                # tree_cap: a branch node (two child edges + their pads start here) takes the nearest OPEN site within
                # 400 um of its wanted point; only then the ring / disk passes below
                for d_r, ox, oy in _DISK37:
                    x_, y_ = dn(x + ox * 10.8 - pw_ / 2, GX), dn(y + oy * 10.8 - CKH / 2, GY)
                    if is_open(x_ + pw_ / 2, y_ + CKH / 2) and free_at(x_, y_, pw_, CKH):
                        px, py = x_, y_
                        break
            if TC_ and pad and anc is not None and px is None:
                # tree_cap: a balancing pad at the child (only when no site along the edge took it) still prefers an
                # open site within the stage of its parent pair and of the child it pads
                ax_, ay_ = anc.x + anc.w / 2, anc.y + anc.h / 2
                tmp_ = Inst('_t', 'x', 0.0, 0.0, pw_, CKH, 'R0', kind='waypoint')
                for _, cx_, cy_ in sorted(((abs(ax_ + fx * 10.8 - x) + abs(ay_ + fy * 10.8 - y), ax_ + fx * 10.8,
                                           ay_ + fy * 10.8) for fx in range(-37, 38) for fy in range(-37, 38))):
                    x_, y_ = dn(cx_ - pw_ / 2, GX), dn(cy_ - CKH / 2, GY)
                    if not is_open(x_ + pw_ / 2, y_ + CKH / 2) or not free_at(x_, y_, pw_, CKH):
                        continue
                    tmp_.x, tmp_.y = x_, y_
                    if eseg(anc, tmp_) <= 400.0 and (anc2 is None or eseg(anc2, tmp_) <= 400.0):
                        px, py = x_, y_
                        break
            for cx_, cy_ in (cands if px is None else ()):
                for ox, oy in (_PAIR_RING if V.get('phys_relays') else
                               ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, 2), (0, -2))):
                    # rf2: with physical data relays the channels are full; search a +-108 um ring (10.8 lattice,
                    # nearest first) before the spiral legaliser, which can push a pair > 1 mm away (2,465 tree
                    # segments over the reach)
                    x_ = dn(cx_ - pw_ / 2 + ox * 10.8, GX)
                    y_ = dn(cy_ - CKH / 2 + oy * 10.8, GY)
                    if free_at(x_, y_, pw_, CKH):
                        if anc is None and V.get('phys_relays') and any(
                                x_ - 25.0 < o[2] and o[0] < x_ + pw_ + 25.0 and y_ - 25.0 < o[3] and o[1] < y_ + CKH + 25.0
                                for o in blk_boxes_):
                            continue    # rf2: an unanchored subtree node never sits in an abutment gap
                        if anc is not None and V.get('phys_relays'):
                            # rf2: an anchored pair's ring site must also be within the stage of its parent pair
                            t_ = Inst('_t', 'x', x_, y_, pw_, CKH, 'R0', kind='waypoint')
                            if eseg(anc, t_) > 400.0 or (anc2 is not None and eseg(anc2, t_) > 400.0):
                                continue
                        px, py = x_, y_
                        break
                if px is not None:
                    break
            if px is None and anc is None and V.get('phys_relays'):
                # rf2: an unanchored node (subtree centre / leaf) takes the free site nearest its wanted point within
                # 400 um before the spiral legaliser (947 legaliser throws left leaves 1.5 mm from their sinks)
                for d_r, ox, oy in _DISK37 + _DISK_FAR:     # 400 um, then out to 1 mm (never the spiral legaliser)
                    x_, y_ = dn(x + ox * 10.8 - pw_ / 2, GX), dn(y + oy * 10.8 - CKH / 2, GY)
                    i_, j_ = int((x_ + pw_ / 2) // RP.CELL), int((y_ + CKH / 2) // RP.CELL)
                    if not (0 <= i_ < G.nx and 0 <= j_ < G.ny) or G.free[j_, i_] < V.get('phys_free_min', 0.2):
                        continue    # rf2: only a routable cell (not a 43-um abutment gap the tree route cannot reach)
                    if any(x_ - 25.0 < o[2] and o[0] < x_ + pw_ + 25.0 and y_ - 25.0 < o[3] and o[1] < y_ + CKH + 25.0
                           for o in blk_boxes_):
                        continue    # rf2: >= 25 um from every block (fits an 84-um channel, never a 43-um abutment gap)
                    if free_at(x_, y_, pw_, CKH):
                        px, py = x_, y_
                        break
            if px is None and anc is not None and V.get('phys_relays'):
                # rf2 anchored disk: a chain / pad pair goes to the free site nearest its wanted point WITHIN 400 um of
                # its parent pair (never the spiral legaliser, which threw pairs 1.5-3.5 mm and broke the stage)
                ax_, ay_ = anc.x + anc.w / 2, anc.y + anc.h / 2
                cands_ = sorted(((abs(ax_ + fx * 10.8 - x) + abs(ay_ + fy * 10.8 - y), ax_ + fx * 10.8, ay_ + fy * 10.8)
                                 for fx in range(-37, 38) for fy in range(-37, 38)))
                tmp_ = Inst('_t', 'x', 0.0, 0.0, pw_, CKH, 'R0', kind='waypoint')
                for a2_ in ((anc2, None) if anc2 is not None else (None,)):
                    for _, cx_, cy_ in cands_:
                        x_, y_ = dn(cx_ - pw_ / 2, GX), dn(cy_ - CKH / 2, GY)
                        if not free_at(x_, y_, pw_, CKH):
                            continue
                        tmp_.x, tmp_.y = x_, y_
                        if eseg(anc, tmp_) <= 400.0 and (a2_ is None or eseg(a2_, tmp_) <= 400.0):
                            px, py = x_, y_
                            break
                    if px is not None:
                        break
            _PAIR_LOG[nm_ck] = (round(x), round(y), px, py, anc.name if anc is not None else None)
            fp_ = Inst(nm_ck + '_fp', 'x', px if px is not None else dn(x - pw_ / 2, GX),
                       py if py is not None else dn(y - CKH / 2, GY), pw_, CKH, 'R0', kind='waypoint')
            if px is None and V.get('pin_reach'):
                # v13 r7: never the spiral legaliser (beyond its 1.2 mm it leaves the pair where it is, on top of
                # whatever is there: 315 overlaps in the SE service stack): the nearest free site out to 4 mm
                _PAIR_FALLBACK['anchored' if anc is not None else 'free'] += 1
                x0_, y0_ = fp_.x, fp_.y
                for r_ in range(1, 186):
                    for dx_, dy_ in ([(dx_, dy_) for dx_ in range(-r_, r_ + 1) for dy_ in (-r_, r_)] +
                                     [(dx_, dy_) for dy_ in range(-r_ + 1, r_) for dx_ in (-r_, r_)]):
                        x_, y_ = dn(x0_ + dx_ * 21.6, GX), dn(y0_ + dy_ * 21.6, GY)
                        if free_at(x_, y_, pw_, CKH):
                            px, py = x_, y_
                            break
                    if px is not None:
                        break
                if px is not None:
                    fp_.x, fp_.y = px, py
                    occupy(fp_)
                else:
                    legal(fp_)
            elif px is None:
                _PAIR_FALLBACK['anchored' if anc is not None else 'free'] += 1
                legal(fp_)          # the spiral legaliser places (and occupies) the pair footprint
            else:
                occupy(fp_)
            if TC_:
                i_, j_ = int((fp_.x + pw_ / 2) // RP.CELL), int((fp_.y + CKH / 2) // RP.CELL)
                if 0 <= i_ < G.nx and 0 <= j_ < G.ny:
                    tocc_[j_, i_] += pw_ * CKH / RP.CELL ** 2
                    tpairs_[j_, i_] += 1
                tg_['n'] += 1
            cb_ = Inst(nm_ck, 'hfd_ckb', fp_.x, fp_.y, CKW, CKH, 'R0', kind='waypoint', region='channel')
            rr_ = Inst(nm_rr, 'hfd_rrl', fp_.x + CKW + 4.32, fp_.y, CKW, CKH, 'R0', kind='waypoint', region='channel')
            for it in (cb_, rr_):
                insts.append(it)
                by[it.name] = it
                G.inst[it.name] = it
            return cb_, rr_

        for d_ in ('stream', 'serial', 'hbm', 'link'):
            sk_ = [(e, 'ck') for e in ck_sinks.get(d_, [])] + [(e, 'rst') for e in rs_sinks.get(d_, [])]
            if not sk_:
                continue
            cen_ = {e: sink_pt(e) for e, _ in sk_}
            xs_, ys_ = [c[0] for c in cen_.values()], [c[1] for c in cen_.values()]
            X0, X1, Y0, Y1 = min(xs_), max(xs_) + 1.0, min(ys_), max(ys_) + 1.0
            nx_ = max(0, math.ceil(math.log2(max(1.0, (X1 - X0) / 480.0))))
            ny_ = max(0, math.ceil(math.log2(max(1.0, (Y1 - Y0) / 480.0))))
            leafw, leafh = (X1 - X0) / 2 ** nx_, (Y1 - Y0) / 2 ** ny_
            cell_of = defaultdict(list)
            for e, kind_ in sk_:
                cx, cy = cen_[e]
                cell_of[(min(2 ** nx_ - 1, int((cx - X0) / leafw)), min(2 ** ny_ - 1, int((cy - Y0) / leafh)))].append((e, kind_))
            cnt = [0]
            nets_ck, nets_rs = defaultdict(list), defaultdict(list)      # driver inst -> loads
            leaf_L = []
            rec_ = dict(pairs=0, sinks=len(sk_), leaves=0, levels=nx_ + ny_, leaf_um=[round(leafw, 1), round(leafh, 1)])

            def node(x, y, cells=None, par=None, tgt=None, pad=False, branch=False, site=None):
                cnt[0] += 1
                cb_, rr_ = pair_at(f'ck_{d_}_{cnt[0]}', f'rr_{d_}_{cnt[0]}', x, y, cells,
                                   anc=by[par[0]] if par is not None else None,
                                   anc2=by[tgt[0]] if tgt is not None else None, pad=pad, branch=branch, site=site)
                nets_ck[cb_.name].append((rr_.name, 'ck'))      # the relay clocked by the buffer beside it
                rec_['pairs'] += 1
                return cb_.name, rr_.name

            leaves_ = []         # (leaf pair, stage depth, leaf x, leaf y, ck sinks, rst sinks)
            edges_ = []          # rf2: tree edges (par, ch, last chain node before ch, stages) for branch-point balancing

            def edge_tc(par, x1_, y1_, branch, ch=None):
                """tree_cap edge: the chain is built pair by pair along the capacity-aware route from the LAST PLACED
                pair to the child (so a pair that drifts is followed, not ignored).  A pair that lands > TREE_STALL_UM
                from its wanted route cells has stalled: those cells are closed for the tree and the rest of the edge
                is re-routed from that pair through another channel."""
                unit_ = ch is not None      # shortest-path tree: every pair is a tree node (unit edges)
                if ch is None:
                    ch = node(x1_, y1_, branch=branch)
                cur, n_, Lp, nst_, chain_ = par, 0, None, 0, [par]
                ctr_ = lambda kk_: ((kk_ % G.nx + .5) * RP.CELL, (kk_ // G.nx + .5) * RP.CELL)
                if V.get('tree_fixed_path') and not unit_:
                    # v14 H-DIE 10-14: ONE capacity-aware route per edge, pairs placed in order ALONG it.  The chase
                    # form below re-routes from wherever the last pair landed; with stall closures the route flips
                    # between channels and the chain orbits a block (v14 SE: 42 edges hit the 150-pair cap, 0.2-3.3 mm
                    # edges built from 45-56 mm of pairs, hbm tree 811 stages, 72k pairs).  Here progress along the
                    # fixed route is monotone, so an edge costs ~L / step pairs; a pair that lands off its route
                    # still charges the cells it could not enter (later edges avoid them) but does not re-route this one.
                    G.inst.setdefault(cur[0], by[cur[0]])
                    G.inst.setdefault(ch[0], by[ch[0]])
                    pq_ = troute(cur[0], ch[0])
                    Lp = (len(pq_) - 1) * RP.CELL
                    stp_ = max(1, int(TREE_STEP_UM // RP.CELL))
                    ix_, close_ = 0, 0
                    while eseg(by[cur[0]], by[ch[0]]) > 400.0 and close_ < 3:
                        tix_ = min(len(pq_) - 1, ix_ + stp_)
                        close_ += tix_ >= len(pq_) - 1      # at most 3 closing pairs once the route is used up
                        if tix_ >= len(pq_) - 1:
                            want_, wx_, wy_ = None, by[ch[0]].x + by[ch[0]].w / 2, by[ch[0]].y + by[ch[0]].h / 2
                        else:
                            want_ = [pq_[tix_]] + [pq_[j_] for j_ in (tix_ - 1, tix_ + 1, tix_ - 2) if 0 <= j_ < len(pq_)]
                            wx_, wy_ = ctr_(pq_[tix_])
                        nd = node(wx_, wy_, want_, par=cur)
                        nets_ck[cur[0]].append((nd[0], 'i'))
                        nets_rs[cur[1]].append((nd[1], 'i'))
                        n_ += 1
                        chain_.append(nd)
                        p_ = by[nd[0]]
                        qx_, qy_ = p_.x + CKW + 2.16, p_.y + CKH / 2
                        # the route index the pair actually serves: nearest route cell in a window ahead of the last
                        lo_, hi_ = ix_ + 1, min(len(pq_), tix_ + 2 * stp_ + 1)
                        off_, jx_ = min(((abs(qx_ - ctr_(pq_[j_])[0]) + abs(qy_ - ctr_(pq_[j_])[1]), j_)
                                         for j_ in range(lo_, hi_)), default=(0.0, tix_))
                        if off_ > TREE_STALL_UM:
                            for kk_ in pq_[max(0, tix_ - 1):tix_ + 2]:
                                tstall_[kk_ // G.nx, kk_ % G.nx] += 1.0
                            tg_['dirty'] = True
                            tcap_rec['stalls'] += 1
                            nst_ += 1
                            jx_ = tix_          # progress is along the route, not toward where the pair landed
                        ix_ = max(ix_ + 1, jx_)
                        cur = nd
                    if eseg(by[cur[0]], by[ch[0]]) > 400.0:
                        tcap_rec['reach_left'] = tcap_rec.get('reach_left', 0) + 1
                    p0_, c0_ = by[par[0]], by[ch[0]]
                    mh_ = abs(p0_.x - c0_.x) + abs(p0_.y - c0_.y)
                    tcap_rec.setdefault('fp_edges', []).append(
                        (d_, round(p0_.x), round(p0_.y), round(c0_.x), round(c0_.y), round(Lp), round(mh_), n_, nst_))
                    if nst_:
                        tcap_rec['fixed_path_stalled_edges'] = tcap_rec.get('fixed_path_stalled_edges', 0) + 1
                    nets_ck[cur[0]].append((ch[0], 'i'))
                    nets_rs[cur[1]].append((ch[1], 'i'))
                    chain_.append(ch)
                    edges_.append(dict(par=par, ch=ch, last=cur, d=n_ + 1, chain=chain_))
                    return ch, Lp, n_ + 1
                while eseg(by[cur[0]], by[ch[0]]) > 400.0:
                    if n_ >= 150:
                        tcap_rec['edges_capped'] += 1
                        if len(tcap_rec.setdefault('capped', [])) < 200:     # v14 diag: where the chains thrash
                            p0_, c0_ = by[par[0]], by[ch[0]]
                            tcap_rec['capped'].append(dict(dom=d_, par=[round(p0_.x), round(p0_.y)],
                                                           ch=[round(c0_.x), round(c0_.y)], stalls=nst_,
                                                           last=[round(by[cur[0]].x), round(by[cur[0]].y)]))
                        break
                    G.inst.setdefault(cur[0], by[cur[0]])
                    pq_ = troute(cur[0], ch[0])
                    if Lp is None:
                        Lp = (len(pq_) - 1) * RP.CELL
                    if len(pq_) > 4:
                        want_ = [pq_[3], pq_[2], pq_[1]]
                        wx_, wy_ = ctr_(pq_[3])
                    else:
                        want_ = None
                        c_ = by[ch[0]]
                        wx_, wy_ = c_.x + c_.w / 2, c_.y + c_.h / 2
                    nd = node(wx_, wy_, want_, par=cur)
                    nets_ck[cur[0]].append((nd[0], 'i'))
                    nets_rs[cur[1]].append((nd[1], 'i'))
                    n_ += 1
                    chain_.append(nd)
                    if want_:
                        p_ = by[nd[0]]
                        qx_, qy_ = p_.x + CKW + 2.16, p_.y + CKH / 2
                        off_, ixn_ = min((abs(qx_ - ctr_(kk_)[0]) + abs(qy_ - ctr_(kk_)[1]), i_)
                                         for i_, kk_ in enumerate(pq_[:7]))
                        if off_ > TREE_STALL_UM or ixn_ < 1:
                            # stalled (off the route, or no progress along it): the cells it could not enter are
                            # charged, so the rest of this edge -- and later edges -- take another channel
                            for kk_ in (pq_[1:4] if off_ > TREE_STALL_UM else pq_[ixn_ + 1:ixn_ + 3]):
                                tstall_[kk_ // G.nx, kk_ % G.nx] += 1.0
                            tg_['dirty'] = True
                            tcap_rec['stalls'] += 1
                            nst_ += 1
                    cur = nd
                if nst_:
                    tcap_rec['reroutes'] += 1
                nets_ck[cur[0]].append((ch[0], 'i'))
                nets_rs[cur[1]].append((ch[1], 'i'))
                chain_.append(ch)
                if unit_:
                    for a_, b_ in zip(chain_, chain_[1:]):
                        edges_.append(dict(par=a_, ch=b_, last=a_, d=1, chain=[a_, b_]))
                    return chain_
                edges_.append(dict(par=par, ch=ch, last=cur, d=n_ + 1, chain=chain_))
                return ch, Lp or 0.0, n_ + 1

            def spt_tree(root):
                """tree_cap topology: a shortest-path tree on the channel graph instead of the geometric H-tree.  The
                H-tree put each branch node at the centre of its sink rectangle, wherever the blocks are: consecutive
                levels fell on opposite sides of an attention tile row and every edge went round the row end (a
                4-mm sweep a level; v12: 189 stages on a 26-mm leaf, 6,078 pad pairs).  Here every leaf pair sits at
                its sinks' centroid and hangs on the LAST tree pair along its shortest channel route from the root
                (near leaves first, so trunks are built once and shared); only the new part of the route gets pairs.
                Depth = channel distance, not rectangle levels; the branches are then balanced with pad pairs."""
                lf_ = []
                for (ci_, cj_), sks_ in sorted(cell_of.items()):
                    pts_ = [cen_[e] for e, _ in sks_]
                    cx, cy = sum(q[0] for q in pts_) / len(pts_), sum(q[1] for q in pts_) / len(pts_)
                    lf_.append((node(cx, cy), cx, cy, sks_))
                A0_ = G.graph(tree_cap_cost(G.free, tocc_, tstall_, widef_, V['phys_block_cost'], V.get('phys_free_min', 0.2)))
                d0_, pr0_ = _dj(A0_, indices=rings.setdefault(root[0], G.ring(root[0])), min_only=True,
                                return_predecessors=True)[:2]
                todo_ = []
                for me, cx, cy, sks_ in lf_:
                    k_ = min(rings.setdefault(me[0], G.ring(me[0])), key=lambda x: d0_[x])
                    pth = [k_]
                    while pr0_[pth[-1]] >= 0:
                        pth.append(pr0_[pth[-1]])
                    todo_.append((float(d0_[k_]), len(todo_), me, cx, cy, sks_, pth))    # pth: leaf -> root
                reg_, nkid_ = {}, defaultdict(int)       # route cell -> tree pairs placed in it; children per pair

                def reg(nd):
                    it_ = by[nd[0]]
                    reg_.setdefault((int((it_.x + it_.w) // RP.CELL), int((it_.y + it_.h / 2) // RP.CELL)), []).append(nd)
                reg(root)
                for dist_, _, me, cx, cy, sks_, pth in sorted(todo_, key=lambda t_: t_[:2]):
                    att_ = None
                    for kk_ in pth:             # from the leaf back toward the root: the first tree pair on the route
                        j_, i_ = divmod(kk_, G.nx)
                        cs_ = [nd for di_ in (0, -1, 1) for dj_ in (0, -1, 1) for nd in reg_.get((i_ + di_, j_ + dj_), ())
                               if nkid_[nd] < 4 or nd == root]
                        if cs_:
                            tx_, ty_ = (i_ + .5) * RP.CELL, (j_ + .5) * RP.CELL
                            att_ = min(cs_, key=lambda nd: abs(by[nd[0]].x - tx_) + abs(by[nd[0]].y - ty_))
                            break
                    att_ = att_ or root
                    nkid_[att_] += 1
                    ch_ = edge_tc(att_, cx, cy, False, ch=me)
                    for nd in ch_[1:-1]:
                        nkid_[nd] += 1
                        reg(nd)
                    rec_['leaves'] += 1
                    leaf_L.append(dist_)
                    leaves_.append((me, len(ch_) - 1, cx, cy, sks_))

            def edge(par, x1_, y1_, branch=False):
                """the child node at (x1_, y1_) (legalised), reached from par along the channel router path with a
                buffer / relay pair every <= 400 um of route; returns (child pair, route length)"""
                if TC_:
                    return edge_tc(par, x1_, y1_, branch)
                ch = node(x1_, y1_)
                # rf2: with physical relays the tree edges take the block-avoiding route too (a buffer / relay pair
                # cannot sit inside a hard block; on a block-crossing route the legaliser threw pairs > 1.5 mm away)
                pth = gpath_p(par[0], ch[0]) if V.get('phys_relays') else gpath(par[0], ch[0])
                Lp = (len(pth) - 1) * RP.CELL
                n_ = max(0, math.ceil(Lp / 400.0) - 1)
                cur = par
                for k_ in range(n_):
                    ix = min(len(pth) - 1, int(round((k_ + 1) / (n_ + 1) * (len(pth) - 1))))
                    j_, i_ = divmod(pth[ix], G.nx)
                    nd = node((i_ + .5) * RP.CELL, (j_ + .5) * RP.CELL, pth[max(0, ix - 2):ix + 3], par=cur)
                    nets_ck[cur[0]].append((nd[0], 'i'))
                    nets_rs[cur[1]].append((nd[1], 'i'))
                    cur = nd
                ex_ = 0
                while V.get('phys_relays') and ex_ < 60 and eseg(by[cur[0]], by[ch[0]]) > 400.0:
                    # rf2: close the last gap (anchored pairs can drift off the route) with pairs toward the child
                    c_ = by[ch[0]]
                    # rf2: follow the routable path (not the straight line into an abutment gap): want the route cell
                    # ~3 cells along from cur
                    G.inst.setdefault(cur[0], by[cur[0]])
                    pq_ = gpath_p(cur[0], ch[0]) if V.get('phys_relays') else []
                    if len(pq_) > 4:
                        j_, i_ = divmod(pq_[3], G.nx)
                        wx_, wy_ = (i_ + .5) * RP.CELL, (j_ + .5) * RP.CELL
                    else:
                        wx_, wy_ = c_.x + c_.w / 2, c_.y + c_.h / 2
                    nd = node(wx_, wy_, par=cur)
                    nets_ck[cur[0]].append((nd[0], 'i'))
                    nets_rs[cur[1]].append((nd[1], 'i'))
                    cur = nd
                    ex_ += 1
                n_ += ex_
                nets_ck[cur[0]].append((ch[0], 'i'))
                nets_rs[cur[1]].append((ch[1], 'i'))
                edges_.append(dict(par=par, ch=ch, last=cur, d=n_ + 1))
                return ch, Lp, n_ + 1

            def sub(i0, i1, j0, j1, par, Lpar, Dpar):
                if not any(i0 <= a < i1 and j0 <= b < j1 for a, b in cell_of):
                    return
                cx = X0 + (i0 + i1) / 2 * leafw
                cy = Y0 + (j0 + j1) / 2 * leafh
                if V.get('phys_relays') and i1 - i0 == 1 and j1 - j0 == 1 and cell_of.get((i0, j0)):
                    # rf2: a leaf pair sits at its sinks' centroid (the cell centre can fall inside a block)
                    pts_ = [cen_[e] for e, _ in cell_of[(i0, j0)]]
                    cx, cy = sum(q[0] for q in pts_) / len(pts_), sum(q[1] for q in pts_) / len(pts_)
                lf1_ = i1 - i0 == 1 and j1 - j0 == 1
                # tree_fixed_path: a LEAF also takes an open site within the stage of its sinks' centroid (v14: leaves of
                # the S-centre serdes / link sinks sat in the 44 / 65-um slots between sd_S, lk_S* and the IDX band,
                # and their edges detoured 20-24 mm out of the slot: stream tree 289 stages vs hbm 160)
                me, Le, De = edge(par, cx, cy, branch=(not lf1_) or ('leaf' if V.get('tree_fixed_path') else False))
                if i1 - i0 == 1 and j1 - j0 == 1:
                    rec_['leaves'] += 1
                    leaf_L.append(Lpar + Le)
                    leaves_.append((me, Dpar + De, cx, cy, cell_of[(i0, j0)]))
                    return
                if (i1 - i0) >= (j1 - j0) and i1 - i0 > 1:
                    im = (i0 + i1) // 2
                    sub(i0, im, j0, j1, me, Lpar + Le, Dpar + De)
                    sub(im, i1, j0, j1, me, Lpar + Le, Dpar + De)
                else:
                    jm = (j0 + j1) // 2
                    sub(i0, i1, j0, jm, me, Lpar + Le, Dpar + De)
                    sub(i0, i1, jm, j1, me, Lpar + Le, Dpar + De)
            G.inst.setdefault(coll_.name, coll_)
            root_xy = (coll_.x + coll_.w / 2, coll_.y - 30.0)       # the domain's root pair at the PLL block's S face
            if Pt_ is not None:     # v13: at the POR / PLL pin itself (the root net is a hop too)
                root_xy = Pt_(coll_.name, f'por_{d_}') or Pt_(coll_.name, f'pll_{d_}') or root_xy
            root = node(*root_xy)
            nets_ck[('PLL',)] = [(root[0], 'i')]
            nets_rs[('POR',)] = [(root[1], 'i')]
            if TC_ and V.get('tree_spt'):
                # measured on r25gqn_v10_hclegal: 42-98 stages (H-tree 77-143) but 28.0k pairs (H-tree 13.6k): every
                # shallow leaf on a trunk needs its own pads.  Off by default; the balanced H-tree shares them.
                spt_tree(root)
            else:
                sub(0, 2 ** nx_, 0, 2 ** ny_, root, 0.0, 0)
            # balance by construction: every leaf is padded to the deepest leaf's stage count with buffer / relay pairs
            # placed AT the leaf, so each sink sees the same number of clock buffers and reset relay cycles from the PLL
            npad = 0
            if V.get('phys_relays') and leaves_:
                # rf2 branch-point balancing (industry practice: pad the shallower BRANCH once, not every leaf): each
                # edge gets (subtree depth of its parent - its own stages - its child's subtree depth) pad pairs just
                # before its child node, shared by every leaf below.  Leaf-only padding stacked ~90 pairs per leaf near
                # the root (85k pairs, 1,215 per mm2 at the hub centre) and starved the data relays there.
                kids_ = defaultdict(list)
                for E in edges_:
                    kids_[E['par']].append(E)
                dep_ = {}

                def _dep(n):
                    if n not in dep_:
                        dep_[n] = max((E['d'] + _dep(E['ch']) for E in kids_.get(n, ())), default=0)
                    return dep_[n]
                if TC_:     # unit edges: the recursion is as deep as the tree; children were created after parents
                    for E in reversed(edges_):
                        dep_.setdefault(E['ch'], max((E2['d'] + dep_[E2['ch']] for E2 in kids_.get(E['ch'], ())), default=0))
                _dep(root)
                for E in edges_:
                    need_ = _dep(E['par']) - E['d'] - _dep(E['ch'])
                    if need_ <= 0:
                        continue
                    last_, ch_ = E['last'], E['ch']
                    if TC_:
                        # tree_cap: the pad pairs of an edge are spread ALONG the edge, each between two consecutive
                        # pairs of its chain (within one stage of both), in open space first; they were stacked at the
                        # child, filled its channel and wandered off when it was full
                        segs_ = [[E['chain'][i_], E['chain'][i_ + 1], 0] for i_ in range(len(E['chain']) - 1)]
                        for _p in range(need_):
                            got_ = None
                            ordr_ = sorted(range(len(segs_)), key=lambda s_: (
                                segs_[s_][2], -eseg(by[segs_[s_][0][0]], by[segs_[s_][1][0]]), s_))[:8]
                            for open_ in (True, False):
                                for si_ in ordr_:
                                    st_ = pad_site(by[segs_[si_][0][0]], by[segs_[si_][1][0]], open_)
                                    if st_ is not None:
                                        got_ = (si_, st_, open_)
                                        break
                                if got_:
                                    break
                            if got_ is None:
                                break
                            si_, st_, open_ = got_
                            A_, B_, c_n = segs_[si_]
                            nd = node(0.0, 0.0, site=st_)
                            nets_ck[A_[0]].remove((B_[0], 'i'))
                            nets_rs[A_[1]].remove((B_[1], 'i'))
                            nets_ck[A_[0]].append((nd[0], 'i'))
                            nets_rs[A_[1]].append((nd[1], 'i'))
                            nets_ck[nd[0]].append((B_[0], 'i'))
                            nets_rs[nd[1]].append((B_[1], 'i'))
                            segs_[si_:si_ + 1] = [[A_, nd, c_n + 1], [nd, B_, c_n + 1]]
                            if B_ == ch_:
                                last_ = nd
                            tcap_rec['pads_open' if open_ else 'pads_any'] += 1
                            npad += 1
                            need_ -= 1
                        tcap_rec['pads_at_child'] += need_
                        if need_ <= 0:
                            continue
                    nets_ck[last_[0]].remove((ch_[0], 'i'))
                    nets_rs[last_[1]].remove((ch_[1], 'i'))
                    c_ = by[ch_[0]]
                    cur = last_
                    for _p in range(need_):
                        nd = node(c_.x + c_.w / 2, c_.y + c_.h / 2, par=cur, tgt=ch_, pad=True)
                        nets_ck[cur[0]].append((nd[0], 'i'))
                        nets_rs[cur[1]].append((nd[1], 'i'))
                        cur = nd
                        npad += 1
                    nets_ck[cur[0]].append((ch_[0], 'i'))
                    nets_rs[cur[1]].append((ch_[1], 'i'))
                D0_ = _dep(root)
                leaves_ = [(me, D0_, lx, ly, sks) for me, dd, lx, ly, sks in leaves_]
            Dmax = max((lf[1] for lf in leaves_), default=0)
            finals_ = []
            for me, dd, lx, ly, sks in leaves_:
                cur = me
                for _p in range(Dmax - dd):
                    nd = node(lx, ly, par=cur)
                    nets_ck[cur[0]].append((nd[0], 'i'))
                    nets_rs[cur[1]].append((nd[1], 'i'))
                    cur = nd
                    npad += 1
                finals_.append((cur, sks))
            nre_ = 0
            for cur, sks in finals_:
                for e, kind_ in sks:
                    if Pt_ is not None and e[0] in by:
                        # v13: the same re-homing on the sink's PIN (leaf relay centre -> pin)
                        ctr2_ = lambda n_: (by[n_].x + by[n_].w / 2, by[n_].y + by[n_].h / 2)
                        if _mh2(ctr2_(cur[1]), cen_[e]) > float(V['pin_reach']) - 60.0:
                            alt_ = min(finals_, key=lambda f_: _mh2(ctr2_(f_[0][1]), cen_[e]))[0]
                            if _mh2(ctr2_(alt_[1]), cen_[e]) < _mh2(ctr2_(cur[1]), cen_[e]):
                                nre_ += 1
                                (nets_ck[alt_[0]] if kind_ == 'ck' else nets_rs[alt_[1]]).append(e)
                                continue
                    elif V.get('phys_relays') and e[0] in by and eseg(by[cur[0]], by[e[0]]) > 480.0:
                        # rf2: a sink beyond the stage of its own leaf joins the nearest OTHER leaf's final pair within
                        # the stage -- every final pair is at depth Dmax + 1, so the tree stays balanced
                        alt_ = min(finals_, key=lambda f_: eseg(by[f_[0][0]], by[e[0]]))[0]
                        if eseg(by[alt_[0]], by[e[0]]) < eseg(by[cur[0]], by[e[0]]):
                            nre_ += 1
                            (nets_ck[alt_[0]] if kind_ == 'ck' else nets_rs[alt_[1]]).append(e)
                            continue
                    (nets_ck[cur[0]] if kind_ == 'ck' else nets_rs[cur[1]]).append(e)
            rec_['sinks_rehomed'] = nre_
            if Pt_ is not None:
                # v13 reset fan-out rule: every reset net (a relay's o pin + the i / rst pins it drives) is a hop, half
                # perimeter <= the reach.  A relay whose loads spread wider is DUPLICATED beside itself -- one more
                # pair driven by the same parent, at the same depth, so every sink still sees the same number of
                # clock buffers and reset cycles -- and each copy drives one cluster of loads (the cluster's box with
                # the copy inside the reach).  Children first, so a parent sees its children's copies.
                RL_ = float(V['pin_reach']) - 20.0
                ctr_p = lambda n_: (by[n_].x + by[n_].w / 2, by[n_].y + by[n_].h / 2)
                rpt_ = lambda e_: ctr_p(e_[0]) if by[e_[0]].master in ('hfd_rrl', 'hfd_ckb') else cen_.get(e_) or sink_pt(e_)
                hp2_ = lambda ps_: max(q_[0] for q_ in ps_) - min(q_[0] for q_ in ps_) + max(q_[1] for q_ in ps_) - min(q_[1] for q_ in ps_)
                pred_rs = {ld_[0]: dv_ for dv_, lds_ in nets_rs.items() if dv_ != ('POR',) for ld_ in lds_ if ld_[1] == 'i'}
                ndup_, nleft_ = 0, 0
                for dv_ in reversed(list(nets_rs)):
                    lds_ = nets_rs[dv_]
                    if dv_ == ('POR',) or not lds_ or dv_ not in by:
                        continue
                    dpt_ = ctr_p(dv_)
                    if hp2_([dpt_] + [rpt_(e_) for e_ in lds_]) <= RL_:
                        continue
                    rest_, cls_ = list(lds_), []
                    while rest_:
                        seed_ = max(rest_, key=lambda e_: _mh2(dpt_, rpt_(e_)))
                        cl_ = [seed_]
                        for e_ in sorted((x_ for x_ in rest_ if x_ is not seed_), key=lambda e_: _mh2(rpt_(seed_), rpt_(e_))):
                            if hp2_([dpt_] + [rpt_(x_) for x_ in cl_ + [e_]]) <= RL_ - 60.0:
                                cl_.append(e_)
                        rest_ = [x_ for x_ in rest_ if x_ not in cl_]
                        cls_.append(cl_)
                    nleft_ += sum(1 for cl_ in cls_ if hp2_([dpt_] + [rpt_(x_) for x_ in cl_]) > RL_)
                    if len(cls_) < 2:
                        continue
                    cls_.sort(key=len, reverse=True)
                    par_ = pred_rs.get(dv_)
                    dck_ = 'ck' + dv_[2:]
                    for cl_ in cls_[1:]:
                        nd = node(dpt_[0], dpt_[1], par=('ck' + par_[2:], par_) if par_ else None)
                        nets_ck[('ck' + par_[2:]) if par_ else ('PLL',)].append((nd[0], 'i'))
                        nets_rs[par_ if par_ else ('POR',)].append((nd[1], 'i'))
                        if par_:
                            pred_rs[nd[1]] = par_
                        for e_ in cl_:
                            nets_rs[dv_].remove(e_)
                            nets_rs[nd[1]].append(e_)
                            if e_[1] == 'i' and by[e_[0]].master == 'hfd_rrl':     # a child pair: its clock buffer follows
                                ce_ = ('ck' + e_[0][2:], 'i')
                                pred_rs[e_[0]] = nd[1]
                                if ce_ in nets_ck[dck_]:
                                    nets_ck[dck_].remove(ce_)
                                    nets_ck[nd[0]].append(ce_)
                            else:           # a sink: its ck pins follow its rst pin to the copy
                                for ce_ in [x_ for x_ in nets_ck[dck_] if x_[0] == e_[0] and x_[1] != 'i']:
                                    nets_ck[dck_].remove(ce_)
                                    nets_ck[nd[0]].append(ce_)
                        ndup_ += 1
                # v13 r7 reset EXTENSION: a load (or a cluster of loads) no copy beside its relay reaches -- its pin lies
                # more than the reach from every leaf, e.g. on the far face of a wide block -- gets a chain of pairs from
                # its relay, each on the free site within the reach of the last that is nearest the cluster on the
                # block-avoiding distance field.  Only the RESET moves to the chain's last relay (released that many
                # cycles later: the staged release); the sink's clock stays on its leaf buffer, so the clock depth
                # every sink sees is unchanged.  The chain's buffers only clock its relays.
                next_, nleft_ = 0, 0
                pw2_ = 2 * CKW + 4.32
                for dv_ in list(nets_rs):
                    lds_ = nets_rs[dv_]
                    if dv_ == ('POR',) or not lds_ or dv_ not in by:
                        continue
                    dpt_ = ctr_p(dv_)
                    if hp2_([dpt_] + [rpt_(e_) for e_ in lds_]) <= RL_:
                        continue
                    rest_, cls_ = list(lds_), []
                    while rest_:
                        seed_ = max(rest_, key=lambda e_: _mh2(dpt_, rpt_(e_)))
                        cl_ = [seed_]
                        for e_ in sorted((x_ for x_ in rest_ if x_ is not seed_), key=lambda e_: _mh2(rpt_(seed_), rpt_(e_))):
                            if hp2_([rpt_(x_) for x_ in cl_ + [e_]]) <= RL_ - 160.0:
                                cl_.append(e_)
                        rest_ = [x_ for x_ in rest_ if x_ not in cl_]
                        cls_.append(cl_)
                    cls_.sort(key=lambda cl_: _mh2(dpt_, rpt_(cl_[0])))
                    kept_ = []
                    for cl_ in cls_:
                        cpts_ = [rpt_(x_) for x_ in cl_]
                        if hp2_([dpt_] + [rpt_(x_) for x_ in kept_] + cpts_) <= RL_:
                            kept_ += cl_
                            continue
                        tg2_ = (sum(q_[0] for q_ in cpts_) / len(cpts_), sum(q_[1] for q_ in cpts_) / len(cpts_))
                        D2_ = dfield(cell_k(tg2_))
                        cur_rr, cur_pt, ok2_ = dv_, dpt_, False
                        for _x in range(60):
                            if hp2_([cur_pt] + cpts_) <= RL_:
                                ok2_ = True
                                break
                            px2, py2 = cur_pt[0] + _lx, cur_pt[1] + _ly
                            sc2 = dscore(D2_, px2, py2)
                            c2 = float(dscore(D2_, _np.array([cur_pt[0]]), _np.array([cur_pt[1]]))[0])
                            site_ = None
                            for n_ in _np.argsort(sc2, kind='stable'):
                                if sc2[n_] > c2 - 40.0:
                                    break
                                if abs(_lx[n_]) + abs(_ly[n_]) > RL_ - 30.0:
                                    continue
                                x_, y_ = dn(float(px2[n_]) - pw2_ / 2, GX), dn(float(py2[n_]) - CKH / 2, GY)
                                if free_at(x_, y_, pw2_, CKH):
                                    site_ = (x_, y_)
                                    break
                            if site_ is None:
                                break
                            nd = node(site_[0] + pw2_ / 2, site_[1] + CKH / 2, par=('ck' + cur_rr[2:], cur_rr), site=site_)
                            nets_ck['ck' + cur_rr[2:]].append((nd[0], 'i'))
                            nets_rs[cur_rr].append((nd[1], 'i'))
                            cur_rr, cur_pt = nd[1], ctr_p(nd[1])
                            next_ += 1
                        if cur_rr != dv_:
                            for e_ in cl_:
                                nets_rs[dv_].remove(e_)
                                nets_rs[cur_rr].append(e_)
                        nleft_ += not ok2_
                rec_['reset_extension_pairs'] = next_
                rec_['reset_fanout_copies'] = ndup_
                if os.environ.get('OT_HBMDIE_TRACE'):
                    print('tree', d_, 'copies', ndup_, 'beyond', nleft_, file=sys.stderr, flush=True)
                rec_['reset_loads_beyond_reach'] = nleft_
            rec_['stages_root_to_leaf'] = Dmax + 1
            rec_['pad_pairs'] = npad
            for drv_, lds_ in nets_ck.items():
                src_ = (coll_.name, f'pll_{d_}') if drv_ == ('PLL',) else (drv_, 'o')
                tree_nets[f'clk_{d_}'].append((f'clk_{d_}' if drv_ == ('PLL',) else f'clk_{d_}_{drv_}', 'clock_trunk', 1,
                                               [src_] + lds_))
            for drv_, lds_ in nets_rs.items():
                src_ = (coll_.name, f'por_{d_}') if drv_ == ('POR',) else (drv_, 'o')
                tree_nets[f'rst_{d_}'].append((f'rst_{d_}' if drv_ == ('POR',) else f'rst_{d_}_{drv_}', 'reset_tree', 1,
                                               [src_] + lds_))
            rec_['root_route_um'] = dict(min=round(min(leaf_L), 1), max=round(max(leaf_L), 1),
                                         spread=round(max(leaf_L) - min(leaf_L), 1)) if leaf_L else None
            tree_rec[d_] = rec_
        phys_rec['clock_reset_trees'] = tree_rec
        if TC_:
            # pairs per channel: the fullest route cells (tree pairs, fill = waypoint area / free area, narrow or open)
            top_ = sorted(((tocc_[j_, i_] / max(G.free[j_, i_], 0.05), int(tpairs_[j_, i_]), i_, j_)
                           for j_ in range(G.ny) for i_ in range(G.nx) if tpairs_[j_, i_]), reverse=True)[:12]
            nar_ = (widef_ < 0.3) & (G.free >= V.get('phys_free_min', 0.2))
            tcap_rec.update(route_graph_builds=tg_['builds'], cells_closed=int((tstall_ > 0).sum()),
                            pairs_in_narrow_cells=int(tpairs_[nar_].sum()), pairs=int(tpairs_.sum()),
                            max_pairs_per_cell=int(tpairs_.max()),
                            fullest_cells=[dict(xy_um=[i_ * RP.CELL, j_ * RP.CELL], pairs=n_, fill=round(f_, 3),
                                                narrow=bool(nar_[j_, i_])) for f_, n_, i_, j_ in top_])
            phys_rec['tree_cap'] = tcap_rec
        nb_ = []
        for b_ in old_order:
            if b_[1] in ('clock_trunk', 'reset_tree') and b_[0] in tree_nets:
                nb_.extend(tree_nets.pop(b_[0]))
            elif b_[1] not in ('clock_trunk', 'reset_tree') or not (b_[0].startswith('clk_') or b_[0].startswith('rst_')):
                nb_.append(b_)
        for v_ in tree_nets.values():
            nb_.extend(v_)
        buses[:] = nb_
    m = _model()
    if phys_rec is not None:
        m['phys_relays'] = phys_rec
        if os.environ.get('OT_HBMDIE_PHYS_REC'):        # diagnostic dump: tree / relay records of this build
            Path(os.environ['OT_HBMDIE_PHYS_REC']).write_text(json.dumps(phys_rec, indent=1, default=str) + '\n')
    if V.get('child_slots'):
        m['child_slots'] = child_slots_check(V['child_slots'], insts)
    if V.get('vm8_union'):
        m['group_slots'] = [vm8_union_group(insts)]
    if (V.get('phys_trees') or V.get('phys_relays')) and not os.environ.get('OT_HBMDIE_NO_TREES'):
        m['pin_peer_hold'] = pin_hold
    if V.get('hc_ck_ew'):       # the die clock reaches both halves of every HC row root
        buses[:] = [(b_, c_, w_, [x for e in e_ for x in ([(e[0], e[1] + 'e'), (e[0], e[1] + 'w')]
                                                           if e[0].startswith('hb_hc_') and re.fullmatch(r'ck\d', e[1]) else [e])])
                    if c_.startswith('clock') else (b_, c_, w_, e_) for b_, c_, w_, e_ in buses]
        m['link_endpoints'] = dict(ep_of)
    if V.get('ck_root') and V.get('ck_root_inputs'):    # v14: the die clock root's own inputs are die top pins (bumps)
        ck_ = next(i for i in insts if i.name == V['ck_root'])
        m['top_input_ports'] = dict(m.get('top_input_ports') or {})
        for n_, (pin_, use_) in V['ck_root_inputs'].items():
            buses.append((f'top_{n_}', 'ctl_top', 1, [('TOP', n_), (V['ck_root'], pin_)]))
            m['top_input_ports'][n_] = dict(direction='input', use=use_, layer='M5', size_um=[0.024, 0.084],
                                            center_um=[round(ck_.x + ck_.w / 2, 3), 0.042], domain='ref',
                                            note='bump-fed at the ckgen site; DEF pin on the S edge below it')
    return m


def build(variant=None, *, geometry_only=False, network_probe=False):
    if variant is not None and variant.get('r25gq'):
        return build_r25gq_net(variant) if variant.get('r25gq_net') else build_r25gq(variant)
    variant = dict(variant if variant is not None else ADOPTED)
    if variant.get('hgi_dispatch') and not variant.get('hgi_dispatch_pins_done'):
        # hgi-takeover 2026-10-09: the normative dispatch's ECO pins on the cmdproc split view (tools/hgi_die_dispatch.py)
        from hgi_die_dispatch import variant as hgi_dispatch_variant
        variant = dict(hgi_dispatch_variant(variant, variant['hgi_dispatch']), hgi_dispatch_pins_done=True)
        # mtp-lead 2026-10-09: a CP band with its own pin record (MX1) overrides a planned dispatch pin's (fraction, pitch)
        # -- the plan's argmax span (0.50 x 1399.656, 2 tracks = 667-733 um) lies on MX1's f_loader pins
        ov_ = variant.get('cp_pin_override') or {}
        if ov_ and 'hfd_cmdproc' in (variant.get('split_extra_ports') or {}):   # 'cp': one CP block, no MX1 band
            ex_ = {k: dict(x) for k, x in variant['split_extra_ports'].items()}
            for pn_, (frac_, pitch_) in ov_.items():
                t_ = ex_['hfd_cmdproc'][pn_]
                ex_['hfd_cmdproc'][pn_] = t_[:4] + (frac_, pitch_)
            variant['split_extra_ports'] = ex_
    Q.CORNER_RULE.clear()
    Q.CORNER_RULE.update(variant.get('corner_rule', {}))
    Q.PIN_CENTRE.clear()
    Q.PIN_CENTRE.update(variant.get('pin_centre', {}))
    smw, smh = sm_dims() if 'sm_wh' not in variant else (up(variant['sm_wh'][0], GX) - SHAVE, up(variant['sm_wh'][1], GY) - SHAVE)
    strip_d = variant.get('strip_d', STRIP_D)
    if variant.get('sm_physical_grid'):
        # Measured hard macro dimensions must never be shaved or rescaled.
        smw, smh = variant['sm_wh']
    physical_cols, physical_rows = variant.get('sm_physical_grid', (4, 2))
    if (physical_cols, physical_rows) not in ((4, 2), (3, 3)):
        raise ValueError('SM physical grid must preserve eight logical SMs per stack')
    if variant.get('sm_physical_grid') and not (geometry_only or network_probe):
        raise ValueError('Retiled SM network paths and latency are not yet qualified; use geometry_only=True')
    grp_w = physical_cols * (smw + SHAVE) + (physical_cols + 1) * CH
    grp_h = physical_rows * (smh + SHAVE) + physical_rows * CH
    mid_ch = up(variant.get('mid_ch', 2592.0), GX)
    if variant.get('hub_scale'):        # r23: the SU / SFU / HC quarters grow by hub_scale; the centre channel widens by
        #   the added quarter widths on both sides (each quarter is BLOCKS mm2 / 4 over the quarter height qhc)
        hub_h0 = up(variant.get('hub_h_ref', variant.get('hub_h', 7200.0)), GY)   # r25s: the r25 quarter widths
        hh0 = dn(hub_h0 - 2 * HCH, GY) - 0.0
        qh0 = dn((dn(hub_h0 - 2 * HCH, GY) - HCH) / 2, GY)
        add = 0.0
        for n_ in (('su', 'su_fused'), ('sfu',), ('hc',)):
            mm2 = sum(BLOCKS[x][0] for x in n_)
            add += up(mm2 * variant['hub_scale'] / 4 * 1e6 / qh0, GX) - up(mm2 / 4 * 1e6 / qh0, GX)
        mid_ch = up(mid_ch + 2 * add, GX)
    if variant.get('attn_tile_w_um') and variant.get('attn_grow_mid'):   # r23: wider attention tiles widen the scan
        #   quadrants by 4 x (tile growth) per side; the centre channel grows by both sides' growth (the hub centre moves
        #   by half of it, so the W quadrant gains the same room)
        tw0 = up(math.sqrt(BLOCKS['attn_tile'][0] * 1e6), GX) if not variant.get('attn_tile_w0_um') else variant['attn_tile_w0_um']
        mid_ch = up(mid_ch + 2 * 4 * (up(variant['attn_tile_w_um'], GX) - tw0), GX)
    core_w = 2 * grp_w + mid_ch
    W = up(EDGE + SCH + core_w + SCH + strip_d + EDGE, GX)
    side_h = EDGE + PHY_H + 8.64 + SVC_D + SVC_GAP + grp_h + variant.get('side_padding_um', 0.0)
    hub_h = up(variant.get('hub_h', 7200.0), GY)
    H = up(2 * side_h + hub_h, GY)
    assert W <= 33000 and H <= 26000, (W, H)
    insts, regions, notes = [], [], []
    x0 = up(EDGE + SCH, GX)
    geo = dict(W=W, H=H, x0=x0, grp_w=grp_w, grp_h=grp_h, mid_ch=mid_ch, hub_h=hub_h, side_h=side_h,
               core_w=core_w, cx=x0 + grp_w + mid_ch / 2)
    rp = S.real_lef(PHY_LEF)
    groups = {}
    for side in 'SN':
        for half in 'WE':
            st = side + half
            gx = x0 if half == 'W' else x0 + grp_w + mid_ch
            if side == 'S':
                yp = up(EDGE, GY)
                ys = up(yp + PHY_H + 8.64, GY)
                yg = up(ys + SVC_D + SVC_GAP, GY)
                po = 'R0'
            else:
                yp = dn(H - EDGE - PHY_H, GY)
                ys = dn(yp - 8.64 - SVC_D, GY)
                yg = dn(ys - SVC_GAP - grp_h, GY)
                po = 'MX'
            xp = up(gx + grp_w / 2 - PHY_W / 2, GX)
            phy = Inst(f'phy_{st}', rp['name'], xp, yp, rp['w'], rp['h'], po, kind='phy', region='phy', domain='hbm')
            svc = Inst(f'svc_{st}', f'hfd_svc_{st}', xp, ys, PHY_W - SHAVE, SVC_D - SHAVE, po, kind='svc', region='svc',
                       domain='hbm')
            insts += [phy, svc]
            regions.append(dict(name=f'grp_{st}', kind='field', rect=[gx, yg, gx + grp_w, yg + grp_h]))
            regions.append(dict(name=f'svc_{st}', kind='svc', rect=[xp, ys, xp + PHY_W, ys + SVC_D]))
            sms = []
            for row in range(2):
                for col in range(4):
                    physical_row, physical_col = divmod(4 * row + col, physical_cols)
                    sx = up(gx + CH + physical_col * (smw + SHAVE + CH), GX)
                    if side == 'S':
                        sy = up(yg + CH + physical_row * (smh + SHAVE + CH), GY) if physical_row else up(yg + 0.0, GY)
                    else:
                        if variant.get('n_mirror_fix'):     # r10: r1-r8 abutted N row 1 on the hub band (no CH)
                            sy = dn(yg + grp_h - (smh + SHAVE) - physical_row * (smh + SHAVE + CH), GY)
                        else:
                            sy = dn(yg + grp_h - (smh + SHAVE) - (CH + physical_row * (smh + SHAVE + CH) if physical_row else 0.0), GY)
                    i = 8 * 'SW SE NW NE'.split().index(st) + 4 * row + col
                    my = variant.get('w_my') and half == 'W'      # r10: W groups mirrored, x face toward the centre
                    if variant.get('orient_fix'):     # r15: bool() -- r1-r14b compared with None (True on S too)
                        flip = (side == 'N') != bool(variant.get('row1_flip') and row == 1)
                    else:
                        flip = (side == 'N') != (variant.get('row1_flip') and row == 1)   # r12: row 1 mirrored about x
                    ori = ('R180' if my else 'MX') if flip else ('MY' if my else 'R0')
                    it = Inst(f'sm{i}', 'hfd_sm', sx, sy, smw, smh, ori, kind='sm', region=f'grp_{st}')
                    it.sm = dict(stack=st, row=row, col=col)
                    if variant.get('sm_physical_grid'):
                        it.sm.update(physical_row=physical_row, physical_col=physical_col)
                    insts.append(it)
                    sms.append(it)
            groups[st] = dict(x=gx, y=yg, sms=sms, phy=phy, svc=svc, side=side, half=half)
    # ---- hub band: centre column (spine, SU W of it, SFU + HC E of it) and four per-stack scan quadrants (16
    #      attention tiles + a quarter of the index path each, beside the stack's SM group: near-HBM attention/index)
    yb0 = up(side_h + 0.0, GY)
    yb1 = dn(H - side_h, GY)
    regions.append(dict(name='hub', kind='hub', rect=[x0, yb0, x0 + core_w, yb1]))
    hy0, hy1 = up(yb0 + HCH, GY), dn(yb1 - HCH, GY)
    hh = hy1 - hy0
    hub = {}
    spine_w = up(variant.get('spine_w', 1814.4), GX)
    sx0 = up(geo['cx'] - spine_w / 2, GX)
    hmid = (hy0 + hy1) / 2
    hs = {n: up(BLOCKS[n][0] * 1e6 / spine_w, GY) for n in BLOCKS if n in
          ('loader', 'router', 'cmdproc', 'coll', 'vm', 'barrier', 'quant')}
    for n in ('coll', 'vm', 'cmdproc'):          # r4: face length for pin escape (r2/r3 GRT hot spot at their faces)
        hs[n] = max(hs[n], up(variant.get(f'face_{n}', variant.get('spine_face_um', 1404.0)), GY))
    ctr = variant.get('spine_centre', 'coll')
    cy0 = dn(hmid - hs[ctr] / 2, GY)
    lower = variant.get('spine_lower', ['loader', 'router', 'cmdproc'])
    upper = variant.get('spine_upper', ['vm', 'barrier', 'quant'])
    # r16 option spine_h: the spine column spans a centred band of that height (a taller hub band for the measured
    # attention tiles otherwise spreads the spine blocks apart)
    sy0, sy1 = (hy0, hy1) if 'spine_h' not in variant else (up(hmid - variant['spine_h'] / 2, GY), dn(hmid + variant['spine_h'] / 2, GY))
    glo = (cy0 - sy0 - sum(hs[n] for n in lower)) / len(lower)
    ghi = (sy1 - (cy0 + hs[ctr]) - sum(hs[n] for n in upper)) / len(upper)
    assert min(glo, ghi) >= 43.2, ('spine column too short', glo, ghi)
    place = [(ctr, cy0)]
    yy = sy0 + glo / 2
    for n in lower:
        place.append((n, yy))
        yy += hs[n] + glo
    yy = cy0 + hs[ctr] + ghi / 2
    for n in upper:
        place.append((n, yy))
        yy += hs[n] + ghi
    for n, y_ in place:
        it = Inst(f'hb_{n}', f'hfd_{n}', sx0, up(y_, GY), spine_w - SHAVE, hs[n] - SHAVE, kind='spine', region='hub',
                  domain='serial_0p9' if n == 'quant' and 'quant' not in (variant.get('hgi_dispatch') or []) else 'stream_1p2')   # hgi quant unit: stream 1.2 GHz (the record path and the VM are stream)
        insts.append(it)
        hub[n] = it
    # r16i (hub REQUEST 12:10 PT): one-per-die SU slots stacked above the top spine block (quant) in the free top
    # end of the spine column, at the spine's upper gap pitch: su_red (the SU reducer: hfd_su accumulate chains in on
    # its W / E faces, result out on its N face) then su_full (the full SU lane on the SU broadcast bus: S face from
    # su_red, W / E faces to the SU broadcast, nearest spine block to it the VM).  Nothing else moves (a spine re-stack
    # renumbers the station masters and moves the attention tiles' q pins: 7 closed views invalidated, measured).
    yy = yy - ghi
    for n_, (w_, h_) in variant.get('spine_slots', {}).items():
        it = Inst(f'hb_{n_}', f'hfd_{n_}', up(sx0 + (spine_w - SHAVE - w_) / 2, GX), up(yy + ghi, GY), w_, h_,
                  kind='spine', region='hub', domain=variant.get('spine_slot_domains', {}).get(n_, 'serial_0p9'))
        assert it.y + it.h <= hy1, ('spine slot above the hub band', n_, it.y + it.h, hy1)
        insts.append(it)
        hub[n_] = it
        yy = it.y + h_
    # r25m (MTP-DIE 2026-10-08): one-per-die slots BELOW the lowest spine block (the loader), stacked downward at the
    # spine's lower gap pitch, in the free bottom end of the spine column (r25: 2.17 mm free between the hub band
    # edge and the loader).  hfd_mtp = ot_dshbm_dspark_top (dspark_ctl f2 + argmax f1 + union f3 + accept a0 +
    # spec_state + scratch c2 + fence + the drafter's router_topk), 0.6-1.5 mm from its control peers (loader,
    # router, cmdproc).  Nothing else moves; the die outline is unchanged.
    yy = min(it.y for it in hub.values() if it.kind == 'spine' and it.x == sx0) - glo / 2
    for n_, (w_, h_) in variant.get('spine_slots_low', {}).items():
        y_ = dn(yy - glo / 2 - h_, GY)
        master_ = variant.get('spine_slot_masters', {}).get(n_, f'hfd_{n_}')
        it = Inst(f'hb_{n_}', master_, up(sx0 + (spine_w - SHAVE - w_) / 2, GX), y_, w_, h_,
                  kind='spine', region='hub', domain=variant.get('spine_slot_domains', {}).get(n_, 'stream_1p2'))
        assert it.y >= hy0 + 43.2, ('low spine slot below the hub band', n_, it.y, hy0)
        parts_ = variant.get('spine_slot_split', {}).get(n_)
        if parts_:
            # mtp-lead 2026-10-09: a multi-instance slot: closed views side by side from the slot's west edge,
            # bottom-aligned; they must fit the slot outline (the slot keeps its reserved size)
            xx_ = it.x
            for key_, mst_, (pw_, ph_) in parts_:
                assert ph_ <= h_ + 1e-6 and xx_ + pw_ <= it.x + w_ + 1e-6, ('slot split overflows', n_, key_)
                sub_ = Inst(f'hb_{key_}', mst_, round(xx_, 4), y_, pw_, ph_, kind='spine', region='hub',
                            domain=it.domain)
                insts.append(sub_)
                hub[key_] = sub_
                xx_ += pw_
        else:
            insts.append(it)
            hub[n_] = it
        yy = it.y
    if 'router_env' in variant:      # r16h: scoped router envelope (loader / cmdproc fixed, taken from their gaps)
        ry, rh = variant['router_env']
        if 'hub_h_ref' in variant:     # r25s: a taller hub band moves the centred spine column up by half the growth
            ry = up(ry + (hub_h - up(variant['hub_h_ref'], GY)) / 2, GY)
        if variant.get('sm_physical_grid'):
            # Historical envelope is absolute; preserve its hub-relative location.
            ry += grp_h - (2 * (sm_dims()[1] + SHAVE) + 2 * CH) + variant.get('side_padding_um', 0.0)
        it = hub['router']
        assert ry >= hub['loader'].y + hub['loader'].h and ry + rh <= hub['cmdproc'].y, ('router_env overlaps', ry, rh)
        it.y, it.h = ry, rh
    # r12: the SU E <-> W quarter links (1,024 b each way per pair) cross the spine column through the gap between
    # router and cmdproc (S pair) and between VM and barrier (N pair); r11 crossed the blocks (402 M6 overflow)
    if variant.get('attn_rtl'):
        geo['hub_y'] = (hy0, hy1)
    geo['ew_y'] = dict(S=(hub['router'].y + hub['router'].h + SHAVE + hub['cmdproc'].y) / 2,
                       N=(hub['vm'].y + hub['vm'].h + SHAVE + hub['barrier'].y) / 2)
    if variant.get('barrier_low'):      # r17: the barrier (whose only peer is the cmdproc) sits in the cmdproc / coll
        #   gap, 4 mm closer to its peer and inside the cmdproc's clock region (r17 plan: barrier <-> cmdproc 198.7 ps
        #   across HUB-C / HUB-SP); nothing else moves (ew_y keeps the pre-move N gap)
        it, cp, co = hub['barrier'], hub['cmdproc'], hub['coll']
        gap0, gap1 = cp.y + cp.h + SHAVE, co.y
        it.y = up(gap0 + (gap1 - gap0 - it.h) / 2, GY)
        assert gap0 + 20.0 <= it.y and it.y + it.h + 20.0 <= gap1, ('barrier_low does not fit', gap0, gap1, it.h)
    qh = dn((hh - HCH) / 2, GY)
    # r16 option cq_h: SU / SFU / HC quarters keep that height (r14b 3,080 um) on a taller hub band, at the hub edge
    # (cq_at='edge') or against the equator channel (cq_at='equator'); the scan quadrants use the full qh
    qhc = min(qh, dn(variant['cq_h'], GY)) if 'cq_h' in variant else qh

    def qori(q):
        """r10: the four copies of a shared hub master (SU / SFU / HC quarters, index quarters, attention tiles) are
        mirrored images of the SW copy, so one master's pin faces look the same way (spine, equator, hub edge) in every
        quadrant.  r1-r8 placed all four R0 and took every pin face from the SW copy."""
        if not variant.get('port_fix'):
            return 'R0'
        return {'SW': 'R0', 'SE': 'MY', 'NW': 'MX', 'NE': 'R180'}[q]

    def quarters(name, mm2, xw, xe, dom='serial_0p9'):
        """r3: four quarters (SW, NW W of the spine; SE, NE E of it) of qh each around the equator channel, so that
        every stack quadrant has its own quarter on its side of the spine; returns (west x, east x) of the next ring."""
        w = up(mm2 / 4 * 1e6 / qhc, GX)
        eq = variant.get('cq_at') == 'equator'
        for q in ('SW', 'SE', 'NW', 'NE'):
            x_ = dn(xw - w, GX) if q[1] == 'W' else up(xe, GX)
            if eq:
                y_ = dn(hmid - HCH / 2 - qhc, GY) if q[0] == 'S' else up(hmid + HCH / 2, GY)
            else:
                y_ = hy0 if q[0] == 'S' else dn(hy1 - qhc, GY)
            it = Inst(f'hb_{name}_{q}', f'hfd_{name}', x_, y_, w - SHAVE, qhc - SHAVE, qori(q), kind='hub', region='hub',
                      domain=dom)
            insts.append(it)
            hub[f'{name}_{q}'] = it
        return dn(xw - w - HCH, GX), up(xe + w + HCH, GX)
    spch = variant.get('spch', SPCH)
    geo['spch'] = spch
    hsc = variant.get('hub_scale', 1.0)
    xw, xe = quarters('su', (BLOCKS['su'][0] + BLOCKS['su_fused'][0]) * hsc, sx0 - spch, sx0 + spine_w + spch)
    xw, xe = quarters('sfu', BLOCKS['sfu'][0] * hsc, xw, xe)
    xw, xe = quarters('hc', BLOCKS['hc'][0] * hsc, xw, xe)
    regions.append(dict(name='centre', kind='hub', rect=[hub['hc_SW'].x, hy0, hub['hc_SE'].x + hub['hc_SE'].w, hy1]))
    # Historical r14b remains replayable. Measured-macro revisions must supply
    # both dimensions: an area-only square can lose the required halo/grid fit.
    tw = up(variant.get('attn_tile_w_um', math.sqrt(BLOCKS['attn_tile'][0] * 1e6)), GX)
    th = up(variant.get('attn_tile_h_um', BLOCKS['attn_tile'][0] * 1e6 / tw), GY)
    tg = 43.2
    assert 4 * th + 3 * tg <= qh + 1e-6, ('attention tiles do not fit the quadrant', 4 * th + 3 * tg, qh)
    # r25s: the index quarters keep the r25 height (their closed split bands, physical/hbm_accel_die_views/index_q/split)
    #   at the hub edge of a taller scan quadrant
    ixh = min(qh, dn(variant['index_h'], GY)) if 'index_h' in variant else qh
    iw = up(BLOCKS['index'][0] / 4 * 1e6 / ixh, GX)
    tiles, scan = [], {}
    for st in ('SW', 'SE', 'NW', 'NE'):
        side, half = st
        qy = hy0 if side == 'S' else dn(hy1 - qh, GY)
        if half == 'W':
            ix_x = dn(hub['hc_SW'].x - HCH - iw, GX)
            tx0 = dn(ix_x - HCH - 4 * tw - 3 * tg, GX)
            assert tx0 >= x0 + HCH / 2 - 1e-6, ('W scan quadrant overflows', tx0, x0)
        else:
            ix_x = up(hub['hc_SE'].x + hub['hc_SE'].w + SHAVE + HCH, GX)
            tx0 = up(ix_x + iw + HCH, GX)
            assert tx0 + 4 * tw + 3 * tg <= x0 + core_w - HCH / 2 + 1e-6, ('E scan quadrant overflows', tx0)
        ix = Inst(f'hb_index_{st}', 'hfd_index_q', ix_x, qy if side == 'S' else dn(qy + qh - ixh, GY), iw - SHAVE, ixh - SHAVE,
                  qori(st), kind='hub', region='hub')
        insts.append(ix)
        hub[f'index_{st}'] = ix
        ty0 = up(qy + (qh - 4 * th - 3 * tg) / 2, GY)
        grid = []
        for r in range(4):
            row = []
            for c in range(4):
                it = Inst(f'at_{st}_{r}{c}', 'hfd_attn_tile', up(tx0 + c * (tw + tg), GX), up(ty0 + r * (th + tg), GY),
                          tw - SHAVE, th - SHAVE, qori(st), kind='attn_tile', region='hub')
                insts.append(it)
                tiles.append(it)
                row.append(it)
            grid.append(row)
        scan[st] = dict(index=ix, tiles=grid)
        regions.append(dict(name=f'scan_{st}', kind='hub', rect=[min(tx0, ix_x), qy, max(tx0 + 4 * tw + 3 * tg, ix_x + iw), qy + qh]))
    notes.append(f'hub band {hh:.1f} um tall; scan quadrant {qh:.1f} um; W slack '
                 f'{min(s_["tiles"][0][0].x for k_, s_ in scan.items() if k_[1] == "W") - x0:.1f} um')
    # ---- SerDes: centre of the S (5 macros) and N (4 macros) edges, in the widened mid channel between the PHY pairs
    #      (r2: from the E/W strips, which put the endpoint 11-16 mm from its farthest macro); reservation slab at the
    #      edge, the real ot_pdie_serdes pin macros on its core side.  Host UCIe + slab on the E strip.
    rs, ru = S.real_lef(SERDES_LEF), S.real_lef(HOST_LEF if variant.get('host_bb') else UCIE_LEF)
    links = []
    cxm = geo['cx']
    sd_w = dn(mid_ch - 2 * 64.8, GX)
    if variant.get('serdes_w_um'):     # r23: the widened centre channel must not stretch the SerDes slab (r23b a_real:
        sd_w = min(sd_w, up(variant['serdes_w_um'], GX))   # sd_N 8.65 mm wide snapped outside the die)
    sl = up(BLOCKS['serdes'][0] / 2 * 1e6 / sd_w, GY)
    MG = variant.get('serdes_mg', 103.68)          # channel E of each macro (its io pins); r14 option: wider
    for side, n in (('S', 5), ('N', 4)):
        sx = up(cxm - sd_w / 2, GX)
        if side == 'S':
            sy = up(EDGE, GY)
            my = up(sy + sl + 43.2, GY)
        else:
            sy = dn(H - EDGE - sl, GY)
            my = dn(sy - 43.2 - rs['h'], GY)
        insts.append(Inst(f'sd_{side}', 'hfd_serdes_slab', sx, sy, sd_w - SHAVE, sl - SHAVE, kind='serdes_slab',
                          region='link', domain='link'))
        row_w = n * rs['w'] + n * MG
        mx = up(cxm - row_w / 2, GX)
        for i in range(n):
            it = Inst(f'lk_{side}{i}', rs['name'], up(mx + i * (rs['w'] + MG), GX), my, rs['w'], rs['h'], 'R0', kind='link',
                      region='link', domain='link')
            insts.append(it)
            links.append(it)
        top = max(sy + sl, my + rs['h']) if side == 'S' else H - min(sy, my)
        assert top <= side_h + 1e-6, (f'{side} SerDes block reaches the hub band', top, side_h)
        regions.append(dict(name=f'serdes_{side}', kind='link', rect=[sx, min(sy, my), sx + sd_w, max(sy + sl, my + rs['h'])]))
    ux = up(W - EDGE - strip_d, GX)
    hsl_w = dn(strip_d - ru['w'] - 8.64, GX)
    hsl = up(BLOCKS['host'][0] * 1e6 / hsl_w, GY)
    uy = up(H / 2 - ru['h'] / 2, GY)
    host_mac = Inst('lk_host', ru['name'], ux, uy, ru['w'], ru['h'], 'R0', kind='link', region='link', domain='link')
    insts.append(host_mac)
    hs = Inst('hs_slab', 'hfd_host_slab', up(ux + ru['w'] + 8.64, GX), up(H / 2 - hsl / 2, GY), hsl_w - SHAVE, hsl - SHAVE,
              kind='host_slab', region='link', domain='link')
    insts.append(hs)
    assert hsl <= H - 2 * EDGE, ('host slab taller than the die', hsl)
    regions.append(dict(name='strip_E', kind='link', rect=[W - EDGE - strip_d, EDGE, W - EDGE, H - EDGE]))
    variant.update(W=W, H=H)
    m = dict(geo=geo, insts=insts, regions=regions, groups=groups, hub=hub, tiles=tiles, scan=scan, links=links, host=host_mac,
             notes=notes, variant=variant, stn_faces={})
    if variant.get('r5a_sidebands'):
        from hbm_r5a_parent_allocation import allocate
        allocate(m)
    if variant.get('native_indexer'):
        from hbm_indexer_die_topology import install
        import sys
        install(m, sys.modules[__name__])
    if variant.get('mtp_x_stop') and variant.get('mtp_master') != 'hgi_native' and not variant.get('native_mtp_wb'):
        fix_ports_mtp_x_stop(m)
    if variant.get('native_mtp_wb'):
        from hbm_mtp_wb_die_model import model as native_model
        m['mtp_wb_native'] = native_model(ROOT)
        if variant.get('native_mtp_stop'):
            from hbm_mtp_native_contract import stop_model
            m['mtp_wb_native']['MTP'] = stop_model(ROOT)
        m['notes'].append('R25IMW reserves actual MTP native facade and SRAM WB slots; endpoint joins and real native views remain unqualified. No historical904/624 loader bundle is adopted.')
    if geometry_only:
        m['buses'], m['paths'] = [], {}
        m['geometry_only'] = True
        m['notes'].append('Placement candidate only: network paths, fixed-pin transforms, clock delivery and latency unqualified.')
        return m
    if network_probe:
        m['network_probe'] = True
        m['notes'].append('Unqualified network probe: old logical tree association, moved anchors; actual pin routes and timing require validation.')
        if variant.get('sm_physical_grid'):
            # Actual 27-piece top result pins from generator 2bd92cae4 +
            # 1d11fbb3e, pins.tcl SHA256 53e4a2bf2cc8e736a9669d796115596c
            # 5cf9e82c469fa92f255536cbe5f003e2. Reserve an outward 120um
            # station bay before placing unrelated tree/request/KV stations.
            bays = []
            for sm in (i for i in insts if i.kind == 'sm'):
                lo, hi = 1467.804, 1608.444
                if sm.orient in ('MY', 'R180'):
                    lo, hi = sm.w - hi, sm.w - lo
                x0, x1 = sm.x + lo - 24, sm.x + hi + 24
                if sm.orient in ('MX', 'R180'):
                    box = [x0, sm.y + sm.h, x1, sm.y + sm.h + 120]
                else:
                    box = [x0, sm.y - 120, x1, sm.y]
                bays.append(dict(sm=sm.name, box_um=box))
            m['result_pin_bays'] = bays
            m.setdefault('reserved_regions', []).extend(q['box_um'] for q in bays)
            if variant.get('native_owner_bays'):
                if any(abs(i.w-3075.84)>1e-6 or abs(i.h-1131.84)>1e-6 for i in insts if i.kind=='sm'):
                    raise ValueError('native owner/descriptor pin reservations require original3075.84x1131.84 SM contract')
                # Opt-in reservation for the protected native owner. Area/grid
                # is priced before a physical master exists; this is not a cell.
                owner_bays=[]
                for sm in (i for i in insts if i.kind == 'sm'):
                    cx=1538.22
                    if sm.orient in ('MY','R180'):
                        cx=sm.w-cx
                    x0=round(round((sm.x+cx-256.176/2)/GX)*GX,6)
                    if sm.orient in ('MX','R180'):
                        y1=sm.y-2.16
                        box=[x0,y1-129.6,x0+256.176,y1]
                    else:
                        y0=sm.y+sm.h+2.16
                        box=[x0,y0,x0+256.176,y0+129.6]
                    owner_bays.append(dict(sm=sm.name,box_um=[round(v,6) for v in box]))
                m['native_owner_bays']=owner_bays
                m.setdefault('reserved_regions',[]).extend(q['box_um'] for q in owner_bays)
                if variant.get('native_descriptor_bays'):
                    descriptor_bays=[]
                    for sm in (i for i in insts if i.kind=='sm'):
                        x0,x1=1312.848,1441.152
                        if sm.orient in ('MY','R180'):
                            x0,x1=sm.w-x1,sm.w-x0
                        if sm.orient in ('MX','R180'):
                            y0,y1=sm.y+sm.h+2.16,sm.y+sm.h+66.96
                        else:
                            y0,y1=sm.y-66.96,sm.y-2.16
                        descriptor_bays.append(dict(sm=sm.name,box_um=[round(sm.x+x0,6),round(y0,6),round(sm.x+x1,6),round(y1,6)]))
                    m['native_descriptor_bays']=descriptor_bays
                    m.setdefault('reserved_regions',[]).extend(q['box_um'] for q in descriptor_bays)
                    if variant.get('native_control_escape_bays'):
                        escape_bays=[]
                        sm_by={i.name:i for i in insts if i.kind=='sm'}
                        for role,group in (('owner',owner_bays),('descriptor',descriptor_bays)):
                            for bay in group:
                                x0,y0,x1,y1=bay['box_um'];cy=(y0+y1)/2
                                if sm_by[bay['sm']].orient in ('MY','R180'):
                                    box=[x1,cy-24,x1+40,cy+24]
                                else:
                                    box=[x0-40,cy-24,x0,cy+24]
                                escape_bays.append(dict(sm=bay['sm'],role=role,box_um=[round(v,6) for v in box]))
                        m['native_control_escape_bays']=escape_bays
                        m.setdefault('reserved_regions',[]).extend(q['box_um'] for q in escape_bays)
                        if variant.get('native_control_u_corridors'):
                            if abs(geo['W']-30904.848)>1e-6 or abs(geo['H']-24051.6)>1e-6:
                                raise ValueError('control U corridor proposal belongs to original retile outline')
                            proposal=json.loads((ROOT/'results/uarch/hbm_sm_owner_reservation_20261007/control_u_successor/proposal.json').read_text())
                            corridors=[dict(sm=row['sm'],box_um=box) for row in proposal['rows'] for box in row['corridor_rectangles_um']]
                            m['native_control_u_corridors']=corridors
                            m.setdefault('reserved_regions',[]).extend(q['box_um'] for q in corridors)
    if network_probe and variant.get('native_result_store_bays'):
        proposal=json.loads((ROOT/'results/uarch/hbm_sm_result_store_reservation_20261007/model.json').read_text())
        sm_by={i.name:i for i in insts if i.kind=='sm'}
        for site in proposal['sites']:
            b=site['sm_group_start'];col=sm_by[f'sm{b+2}'];row=sm_by[f'sm{b+6}']
            actual=[col.x,row.y,col.x+col.w,row.y+row.h]
            if any(abs(a-v)>1e-6 for a,v in zip(actual,site['box_um'])):
                raise ValueError('native result-store proposal does not match actual vacant SM site')
        stores=[dict(sm=s['source_sm'],name=s['name'],box_um=s['box_um']) for s in proposal['stores']]
        m['native_result_store_bays']=stores
        m.setdefault('reserved_regions',[]).extend(s['box_um'] for s in stores)
        m['notes'].append('Full native result-store slot reservations only; no physical master, capture route, or installed-destination service is qualified.')
    m['buses'], m['paths'] = buses(m)
    if variant.get('stn_share'):
        share_stations(m)
    if variant.get('child_contract'):
        from hbm_die_child_contract import allocations
        m['child_reservations'] = allocations(m)
    if variant.get('split_masters'):
        apply_splits(m, variant['split_masters'], variant.get('split_lattice'))
    if variant.get('native_indexer'):
        # Allocate the already-qualified wide station A/B footprints first;
        # native relays must not occupy a required B-half landing region.
        for role_ in variant.get('split_stations', ()):
            split_station(m, role_)
        from hbm_indexer_die_topology import networks
        import sys
        old_names={i.name for i in m['insts']}
        _,native_chain=_router(m,m['buses'],m['paths'])
        networks(m,sys.modules[__name__],m['buses'],m['paths'],native_chain)
        # Existing split clock leaves remain intact. Extend the unique domain
        # roots only with newly allocated native relay endpoints.
        for i in m['insts']:
            if i.name in old_names:
                continue
            d=m.get('clocked',{}).get(i.name)
            if d:
                bus=next(b for b in m['buses'] if b[0]==f'clk_{d}')
                bus[3].append((i.name,'ck'))
            d=d or m.get('fwd_dom',{}).get(i.name,'stream')
            bus=next(b for b in m['buses'] if b[0]==f'rst_{d}')
            bus[3].append((i.name,'rst'))
    if variant.get('split_x_masters'):
        apply_splits_x(m, variant['split_x_masters'])
    fixv = ['hfd_barrier'] if variant.get('barrier_low') else []
    if variant.get('fix_station_pins'):     # r23: these station roles keep their committed view's pins (the hub
        #   re-layout moved their generated pin plan; views with uniform pin runs only -- the r16h corner-rule views
        #   (r11 / r19 / r21 / r23 / r26 / meso_r1) still match the generator and are not listed)
        fixv += list(variant['fix_station_pins'])
    if fixv:
        fix_ports_from_views(m, fixv)
    if variant.get('vm_split'):
        split_vm(m)
    if variant.get('vm_split8'):        # r23v: VM 8-way fallback (default off)
        split_vm8(m)
    if variant.get('attn_split'):       # r25s: attention tiles as two half-tile die blocks (default off)
        split_attn(m, variant['attn_split'])
    for role_ in (() if variant.get('native_indexer') else variant.get('split_stations', ())):     # r23: station roles split into half-bus A / B masters
        split_station(m, role_)
    if variant.get('relay_all'):        # r22: relays at every block pin (pin_stage_buses become a subset of them)
        rf = ROOT / 'physical/hbm_accel_die_views/relay_ends.json'   # the budget's pin-to-pin list (authoritative)
        if rf.exists():
            m['relay_ends'] = [tuple(r) for r in json.loads(rf.read_text())]
            cnt = defaultdict(int)
            for r in m['relay_ends']:
                cnt[r[0]] += 1
            m['relay_count'] = dict(cnt)
        else:
            relay_ends(m)
    if variant.get('hub_ck_seg'):       # r24: the hub quarters' ck becomes ck0..ck{n-1} (one die clock sink per segment)
        hq = [it.name for it in m['insts'] if it.master in HUB_QUARTERS]
        for i_, (bid, cls, bits, eps) in enumerate(m['buses']):
            if cls == 'clock_trunk' and any(e[0] in hq and e[1] == 'ck' for e in eps):
                eps2 = [e for e in eps if not (e[0] in hq and e[1] == 'ck')]
                eps2 += [(e[0], f'ck{j}') for e in eps if e[0] in hq and e[1] == 'ck' for j in range(variant['hub_ck_seg'])]
                m['buses'][i_] = (bid, cls, bits, eps2)
    if variant.get('pin_stage_roots') and not variant.get('relay_all'):
        # + the index-key chains' last segment into index b0 k (ik_<q>_e, 396 um, internal 179 ps: same pattern)
        m['pin_stage_buses'] = sorted(b[0] for b in m['buses'] if b[1] == 'attn_root' or re.match(r'ik_[NS][EW]_e$', b[0]))
    return m


def _split_spec(ports):
    """('face', bits, face, layer, centre, pitch) reproducing a split record's explicit pins (uniform per port)."""
    out, order = {}, []
    for pn, v in ports.items():
        face, layer = v['face'], v['layer']
        pins = sorted(v['pins'], key=lambda q: int(re.search(r'\[(\d+)\]', q[0]).group(1)))
        pos = [((q[2] + q[4]) / 2) if face in 'NS' else ((q[3] + q[5]) / 2) for q in pins]
        step = (pos[-1] - pos[0]) / (len(pos) - 1) if len(pos) > 1 else Q.TRK[layer][1]
        pitch = max(1, round(step / Q.TRK[layer][1]))
        out[pn] = ('face', v['bits'], face, layer, round(pos[0] + v['bits'] * pitch * Q.TRK[layer][1] / 2, 4), pitch)
        order.append(pn)
    return out, order


LAT_Y = 2.16     # macro origin lattice in y: lcm(0.27 um rows, 0.048 um M4/M6 track pitch)


def _jsonable(o):
    """manifest-safe copy: tuple dict keys (r16h pin_centre / corner rule) as 'a|b' strings, sets / tuples as lists."""
    if isinstance(o, dict):
        return {('|'.join(map(str, k)) if isinstance(k, tuple) else k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [_jsonable(v) for v in o]
    return o if isinstance(o, (str, int, float, bool)) or o is None else str(o)


def plan_json(rec):
    """floorplan.json text: the record through _jsonable, so a variant's tuple-keyed dicts (pin_centre from the r23 /
    R25 presets, corner rules) serialise as 'master|port' keys instead of failing json.dumps."""
    return json.dumps(_jsonable(rec), indent=1)


# index_q bands are NOT in the list (r16b a_real, measured + derived): they are placed both R0 and x-mirrored (MY /
# R180).  With M5 pins on x = 0.012 mod 0.048 and an M7 pin on x = 0.016 mod 0.064, an R0 copy needs the M7 pin at
# local x = 0 mod 0.016 and an x-mirrored copy at 0.008 mod 0.016: no single master has a legal origin in both.  Their
# edge ck stays; the budget re-plans their die entry target from the measured insertion (the die tree arrives early).
VM_CENTRE = tuple(f'hfd_vm_{q}' for q in ('sw', 'se', 'nw', 'ne'))
CK_CENTRE = ('hfd_svc_SE_s0', 'hfd_svc_SE_s1', 'hfd_svc_SE_s3', 'hfd_svc_SE_s5', 'hfd_svc_SW_s0', 'hfd_svc_SW_s1', 'hfd_svc_SW_s7',   # SE_s1: 956 ps edge-ck
             'hfd_vm_sw', 'hfd_vm_se', 'hfd_vm_nw', 'hfd_vm_ne')   # r20: VM tiles (all placed R0)   # SW_s1 / SW_s7: edge-ck insertion 1,304 / 1,123 ps


def ck_centre(mst_, sp_):
    """r18 (views agent REQUEST 20:25 / 21:30, measured insertion 927-1,324 ps > the 900 ps target with ck at a band
    edge): the band's ck is an M7 area pin at the band centre (0.064 x 0.288 um on the M7 track between the 10.8 um PG
    stripes: x = 5.4 + 10.8 k + 0.032 nearest the centre; y on the 0.048 grid); the die clock leaf drops onto it from
    M8 (the die owns M8 / M9).  rst stays on its edge."""
    if mst_.name not in CK_CENTRE + VM_CENTRE or 'ck' not in sp_:
        return
    # r16 a_real (measured): the pin must sit on the M7 track lattice (x = 0.016 mod 0.064, block and die alike) or no
    # origin is legal with the M5 pins (ot_mts); the instance origins of these masters are packed on x = 0 mod 1.728
    # (lcm of site 0.054, M5 0.048, M7 0.064).  Among those tracks: the one nearest the centre that lies mid-way between
    # the block's 10.8 um M7 PG stripes (VDD x = 1.0, VSS x = 6.4 mod 10.8): x mod 10.8 within 3.7 +- 0.4 or 9.1 +- 0.4.
    best = None
    k0 = round((mst_.w / 2 - 0.016) / 0.064)
    for d in range(0, 400):
        for kk in (k0 + d, k0 - d):
            x = 0.016 + 0.064 * kk
            r = x % 10.8
            if abs(r - 3.7) <= 0.4 or abs(r - 9.1) <= 0.4:
                best = x
                break
        if best is not None:
            break
    cx = round(best, 4)
    cy = round(round(mst_.h / 2 / 0.048) * 0.048, 4)
    sp_['ck'] = ('area', 'M7', cx, cy, 0.064, 0.288)


VM_TILE_OF = {           # r19: VM port -> quadrant tile (each tile carries the faces toward its quadrant)
    'f_su_SW': 'sw', 't_su_SW': 'sw', 'xSW': 'sw', 'qSW': 'sw', 'iSW': 'sw', 't_router': 'sw',
    'f_su_SE': 'se', 't_su_SE': 'se', 'xSE': 'se', 'qSE': 'se', 'iSE': 'se',
    'f_su_NW': 'nw', 't_su_NW': 'nw', 'xNW': 'nw', 'qNW': 'nw', 'iNW': 'nw', 't_quant': 'nw',
    'f_su_NE': 'ne', 't_su_NE': 'ne', 'xNE': 'ne', 'qNE': 'ne', 'iNE': 'ne',
    **{f'f_am_{p_}': 'se' for p_ in ('out_v', 'out_idx', 'out_nan', 'fault', 'out_range_fault', 'out_value')}}
# mtp-lead: generic-die ARGMAX unit O (south spine slot) lands on the SE VM tile
VM_X_ROW, VM_X_WR, VM_X_CTL = 2256, 2264, 256     # per directed neighbour edge, registered at both pins


def split_vm(m):
    """r19 (coordinator 2026-10-06 ~23:50, views agent NEEDS_BUDGET hfd_vm 1,921 ps insertion, 1,400 x 2,000 um, 120k
    sinks): the VM becomes four quadrant tiles hfd_vm_{sw,se,nw,ne} (2 x 2 in the VM slot, abutting, ~700 x 1,000 um).
    Each tile carries its quadrant's faces (SU publication in / out, x trunk root, attention query, index return) and
    a quarter of the multicast root's row store (banks split by address).  Neighbour tiles (W-E in a row, S-N in a
    column) are joined by registered cross buses on the shared edge, per direction:
      row  2,256 b  read-multicast row (2,063 data + 192 owner + valid): owner tile -> the other taps
      wr   2,264 b  write forward (2,063 data + 192 owner + 7 addr + bank + valid) to the owning tile
      ctl    256 b  read command / ACK / drained / fault exchange
    +1 cycle per cross hop (diagonal tile 2 hops), priced in hbm_die_views_recompose (vm_split).  t_router rides the
    SW tile, t_quant the NW tile."""
    vm = next(i for i in m['insts'] if i.name == 'hb_vm')
    if m['variant'].get('vm_centre_ck'):
        # One R0 copy per master: the M7 centre pin needs origin x=0 mod 1.728.
        # Move the quartet together; preserve its abutments and every station identity.
        vm.x = round(math.ceil(round(vm.x * 1000) / 1728) * 1.728, 4)
    Wf, Hf = vm.w + SHAVE, vm.h + SHAVE
    wl = dn(Wf / 2, GX)
    hb_ = dn(Hf / 2, GY)
    # r20: centre-ck tiles sit on x = 0 mod 1.728 (M7 track lattice with the M5 pins, as the svc bands); wl is a
    # multiple of 1.728, so both columns shift by the same <= 1.7 um and stay abutting
    x0_ = math.ceil(round(vm.x * 1000) / 1728) * 1.728 if (m['variant'].get('vm_ck_centre')) else vm.x
    assert not m['variant'].get('vm_ck_centre') or round(wl * 1000) % 1728 == 0, wl
    geo = dict(sw=(0.0, 0.0, wl, hb_), se=(wl, 0.0, Wf - wl, hb_), nw=(0.0, hb_, wl, Hf - hb_), ne=(wl, hb_, Wf - wl, Hf - hb_))
    tiles = {}
    for q, (dx, dy, w, h) in geo.items():
        tiles[q] = Inst(f'hb_vm_{q}', f'hfd_vm_{q}', round(x0_ + dx, 4), round(vm.y + dy, 4), round(w - SHAVE, 4),
                        round(h - SHAVE, 4), vm.orient, kind=vm.kind, region=vm.region, domain=vm.domain)
    m['insts'] = [i for i in m['insts'] if i.name != 'hb_vm'] + list(tiles.values())
    nb = []
    for bid, cls, bits, eps in m['buses']:
        e2 = []
        for inst, port in eps:
            if inst != 'hb_vm':
                e2.append((inst, port))
            elif port in ('ck', 'rst'):
                e2 += [(t.name, port) for t in tiles.values()]
            else:
                e2.append((tiles[VM_TILE_OF[port]].name, port))
        nb.append((bid, cls, bits, e2))
    for a_, b_, d_ab, d_ba in (('sw', 'se', 'e', 'w'), ('nw', 'ne', 'e', 'w'), ('sw', 'nw', 'n', 's'), ('se', 'ne', 'n', 's')):
        for src, dst, d_, r_ in ((a_, b_, d_ab, d_ba), (b_, a_, d_ba, d_ab)):
            for nm, w in (('row', VM_X_ROW), ('wr', VM_X_WR), ('ctl', VM_X_CTL)):
                nb.append((f'hb_vm_x_{src}_{dst}_{nm}', 'hub', w, [(tiles[src].name, f't_{d_}_{nm}'), (tiles[dst].name, f'f_{r_}_{nm}')]))
    m['buses'] = nb
    m['vm_tiles'] = {q: t.name for q, t in tiles.items()}


RELAY_LAST_UM = 100.0
RELAY_SKIP_CLS = ('clock_trunk', 'reset_tree', 'phy_dfi')


def relay_ends(m):
    """r22 (OWNER 2026-10-07 DIE-WIDE INTERFACE RULE): a relay station abuts every hardened-block pin of every die
    interface whose die segment at that pin is longer than RELAY_LAST_UM (the last die segment into / out of a block
    pin is then <= 100 um).  Stations / waypoints are relays already; PHY / link macro pins and the PHY dfi bundle
    (the svc bands sit on the PHY pins) are excluded; clock / reset trees are CTS.  The relay is a die-level register
    row in the channel at the pin (like the priced wire stages: no generated master), +1 cycle per relay end on its
    bus.  Segment length = Manhattan between the two instances' nearest points (manhattan_paths' measure)."""
    by = {it.name: it for it in m['insts']}

    def c(it):
        return (it.x + it.w / 2, it.y + it.h / 2)

    def near(it, q):
        return (min(max(q[0], it.x), it.x + it.w), min(max(q[1], it.y), it.y + it.h))
    out, cnt = [], defaultdict(int)
    for bid, cls, bits, eps in m['buses']:
        if cls in RELAY_SKIP_CLS or len(eps) != 2 or any(e[0] not in by for e in eps):
            continue
        A, B_ = by[eps[0][0]], by[eps[1][0]]
        a, b = near(A, c(B_)), near(B_, c(A))
        a, b = near(A, b), near(B_, a)
        L = abs(a[0] - b[0]) + abs(a[1] - b[1])
        if L <= RELAY_LAST_UM:
            continue
        for it, (inst, port) in ((A, eps[0]), (B_, eps[1])):
            if it.kind in ('waypoint', 'link', 'phy'):
                continue
            out.append((bid, inst, port))
            cnt[bid] += 1
    m['relay_ends'] = out
    m['relay_count'] = dict(cnt)


def hub_pin_window(mst, window, p4=False):
    """r23 (hub owner a4649202a85580933, OWNER 2x hub): the SU / SFU / HC quarter ports of each long (E / W) face sit in
    one window <= `window` um centred on the face's port band (the bit-weighted mean of the generator's peer-projected
    port centres), so the registered transport tiles reach every die port within ~250 um.  All on M4 (the quarters are
    placed mirrored in y: an M6 pin cannot share a legal origin with the M4 pins in both orientations, r23 a_real),
    2 tracks per bit (0.096 um) when the face fits the window, else 1 track (0.048 um)."""
    byf = defaultdict(list)
    for p_, sp_ in mst.ports.items():
        if sp_[0] == 'face' and sp_[2] in 'EW':
            byf[sp_[2]].append(p_)
    t = Q.TRK['M4'][1]
    for f_, pns in byf.items():
        pns.sort(key=lambda p_: mst.ports[p_][4])
        bits = {p_: mst.ports[p_][1] for p_ in pns}
        c = sum(mst.ports[p_][4] * bits[p_] for p_ in pns) / max(1, sum(bits.values()))
        pitch = 2 if sum(b * 2 * t + 4 * t for b in bits.values()) <= window else 1
        if p4 and sum(b * 4 * t + 4 * t for b in bits.values()) <= window:
            pitch = 4       # r24p (hbm-blocks 2026-10-07): 4 tracks a bit when the face's buses fit the window: the r24 HC
                            # quarter's E face (2,048 bits at 0.096 um in 196 um) was its only GRT overflow (33,722)
        span = sum(b * pitch * t + 4 * t for b in bits.values())
        c_ = min(max(c, span / 2 + 2.0), mst.h - span / 2 - 2.0)
        y = c_ - span / 2
        for p_ in pns:
            n_ = bits[p_] * pitch * t
            sp_ = mst.ports[p_]
            mst.ports[p_] = ('face', sp_[1], f_, 'M4', round(y + 2 * t + n_ / 2, 4), pitch)
            y += n_ + 4 * t


HUB_QUARTERS = ('hfd_su', 'hfd_sfu', 'hfd_hc')


def hub_ck_seg(mst, n, k=1, distinct=False):
    """r24 (coordinator 2026-10-07, SU/hub agent request): a 5.53 mm hub quarter cannot meet the 900 ps block insertion
    from one ck pin (r16g interim HC quarter measured 4,680 ps SS).  The quarter gets n ck pins ck0..ck{n-1}, one per
    band segment of h / n (691 um at n = 8), each a separate die clock sink (the die tree aligns them; the quarter
    builds one sub-tree per segment from its pin).  M4 on the W face (E if a W port window covers a segment centre):
    M4 face pins are legal in all four quarter orientations (R0 / MX / MY / R180), an M7 area pin is not."""
    t = Q.TRK['M4'][1] * k
    win = defaultdict(list)
    for p_, sp_ in mst.ports.items():
        if sp_[0] == 'face' and sp_[2] in 'EW' and not re.fullmatch(r'ck\d+', p_):
            half = sp_[1] * sp_[5] * t / 2 + 2 * t
            win[sp_[2]].append((sp_[4] - half, sp_[4] + half))
    ys = [round(((i + 0.5) * mst.h / n) / t) * t for i in range(n)]
    face = next((f_ for f_ in ('W', 'E') if not any(a_ - 2.0 <= y_ <= b_ + 2.0 for y_ in ys for a_, b_ in win[f_])), None)
    if face is None:        # both faces have ports over a segment centre: each ck pin moves to the nearest free spot
        face = 'W'

        def free_(y_):
            return 2.0 <= y_ <= mst.h - 2.0 and not any(a_ - 1.0 <= y_ <= b_ + 1.0 for a_, b_ in win[face])
        if distinct:      # R25GQ: short quarters -- the face with the most free length, ck pins spread evenly over it
            def frees(f_):
                iv, y0_ = [], 2.0
                for a_, b_ in sorted(win[f_]):
                    if a_ - 1.0 > y0_:
                        iv.append((y0_, a_ - 1.0))
                    y0_ = max(y0_, b_ + 1.0)
                if mst.h - 2.0 > y0_:
                    iv.append((y0_, mst.h - 2.0))
                return iv
            face = max(('W', 'E'), key=lambda f_: sum(b_ - a_ for a_, b_ in frees(f_)))
            iv = frees(face)
            tot = sum(b_ - a_ for a_, b_ in iv)
            ys = []
            for i in range(n):
                r_ = (i + 0.5) * tot / n
                for a_, b_ in iv:
                    if r_ <= b_ - a_:
                        ys.append(round((a_ + r_) / t) * t)
                        break
                    r_ -= b_ - a_
        else:
            ys = [next((y_ + s_ * d_ * t for d_ in range(0, 20000) for s_ in (1, -1) if free_(y_ + s_ * d_ * t)), y_)
                  for y_ in ys]
    mst.ports.pop('ck', None)
    if 'ck' in mst.order:
        mst.order.remove('ck')
    for i, y_ in enumerate(ys):
        mst.ports[f'ck{i}'] = ('face', 1, face, 'M4', round(y_, 4), 1)
        if f'ck{i}' not in mst.order:
            mst.order.append(f'ck{i}')


def split_station(m, role, h_data=1024):
    """r23 (coordinator, views agent REQUEST 05:35: mcast_r6 -328 ps over its 467 um width): every instance of station
    role `role` becomes two die masters <role>a / <role>b side by side (each the original outline: ~2x total area, half
    the logic), A carrying data bits [0, h_data) with their forwarded clocks (one per 512 b slice), B the rest.  Every
    bus on the instance is split in two; the neighbour keeps its port and binds the two halves as bit slices
    ('port@lo:hi,lo:hi').  Paths take the A half (same stage count)."""
    by = {it.name: it for it in m['insts']}
    ins = [it for it in m['insts'] if it.master == role]
    if not ins:
        return
    fcl = m.setdefault('fclk', {})
    pair = {}
    for it in ins:
        a = Inst(it.name + 'a', role + 'a', it.x, it.y, it.w, it.h, it.orient, kind=it.kind, region=it.region, domain=it.domain)
        bx = None
        def reserved_free(x, y):
            return all(not (x < r[2] + 4 and r[0] < x + it.w + 4 and
                            y < r[3] + 4 and r[1] < y + it.h + 4)
                       for r in m.get('reserved_regions', []))
        for cand in (it.x + it.w + SHAVE + 8.64, it.x - it.w - SHAVE - 8.64):
            if reserved_free(cand,it.y) and all(not (cand < j.x + j.w + 4 and j.x < cand + it.w + 4 and it.y < j.y + j.h + 4 and j.y < it.y + it.h + 4)
                   for j in m['insts'] if j is not it):
                bx = cand
                break
        by_ = it.y
        if bx is None and m.get('network_probe'):
            # Retiled geometry may have a free row corridor rather than a
            # second side-by-side slot. Preserve both real macro dimensions.
            for cy in (it.y + it.h + SHAVE + 8.64, it.y - it.h - SHAVE - 8.64):
                if cy < EDGE or cy + it.h > m['geo']['H'] - EDGE:
                    continue
                if reserved_free(it.x,cy) and all(not (it.x < j.x + j.w + 4 and j.x < it.x + it.w + 4 and cy < j.y + j.h + 4 and j.y < cy + it.h + 4)
                       for j in m['insts'] if j is not it):
                    bx, by_ = it.x, cy
                    break
        if bx is None and m.get('network_probe'):
            offsets = sorted(((dx, dy) for dx in range(-24, 25) for dy in range(-24, 25)),
                             key=lambda xy: abs(xy[0]) + abs(xy[1]))
            for dx, dy in offsets:
                cx, cy = up(it.x + dx * 43.2, GX), up(it.y + dy * 43.2, GY)
                if cx < EDGE or cy < EDGE or cx + it.w > m['geo']['W'] - EDGE or cy + it.h > m['geo']['H'] - EDGE:
                    continue
                if reserved_free(cx,cy) and all(not (cx < j.x + j.w + 4 and j.x < cx + it.w + 4 and cy < j.y + j.h + 4 and j.y < cy + it.h + 4)
                       for j in m['insts']):
                    bx, by_ = cx, cy
                    break
        if bx is None and m.get('network_probe'):
            # The unoccupied ninth physical site is explicitly available for
            # tree macros. Its longer wires remain an unqualified probe cost.
            candidates = []
            for group in m['groups'].values():
                sm0 = group['sms'][0]
                ex = group['x'] + CH + 2 * (sm0.w + SHAVE + CH)
                ey = (group['y'] + 2 * (sm0.h + SHAVE + CH)
                      if group['side'] == 'S' else group['y'])
                for dx in range(0, int(sm0.w - it.w), 108):
                    for dy in range(0, int(sm0.h - it.h), 108):
                        candidates.append((up(ex + dx, GX), up(ey + dy, GY)))
            candidates.sort(key=lambda xy: abs(xy[0]-it.x)+abs(xy[1]-it.y))
            for cx, cy in candidates:
                if reserved_free(cx,cy) and all(not (cx < j.x + j.w + 4 and j.x < cx + it.w + 4 and cy < j.y + j.h + 4 and j.y < cy + it.h + 4)
                       for j in m['insts']):
                    bx, by_ = cx, cy
                    break
        assert bx is not None, ('no room for the B half', it.name)
        b = Inst(it.name + 'b', role + 'b', round(bx, 4), round(by_, 4), it.w, it.h, it.orient, kind=it.kind, region=it.region,
                 domain=it.domain)
        pair[it.name] = (a, b)
    m['insts'] = [i for i in m['insts'] if i.name not in pair] + [x for ab in pair.values() for x in ab]
    nb, ren = [], {}
    for bid, cls, bits, eps in m['buses']:
        hit = [j for j, e in enumerate(eps) if e[0] in pair]
        if not hit:
            nb.append((bid, cls, bits, eps))
            continue
        if cls in ('clock_trunk', 'reset_tree'):
            e2 = []
            for e in eps:
                e2 += [(pair[e[0]][0].name, e[1]), (pair[e[0]][1].name, e[1])] if e[0] in pair else [e]
            nb.append((bid, cls, bits, e2))
            continue
        assert len(eps) == 2, (bid, eps)
        fc = fcl.pop(bid, None)
        D, nd = (fc[0], fc[1]) if fc else (bits, 0)
        assert not fc or fc[2] == 0, (bid, fc)
        ha = min(h_data, D)
        nca = min(nd, math.ceil(ha / 512)) if nd else 0
        halves = (('a', list(range(0, ha)) + list(range(D, D + nca)), ha, nca),
                  ('b', list(range(ha, D)) + list(range(D + nca, D + nd)), D - ha, nd - nca))
        for tag, idx, dbits, ncl in halves:
            e2 = []
            for j, (inst, port) in enumerate(eps):
                if inst in pair:
                    e2.append((pair[inst][0 if tag == 'a' else 1].name, port))
                else:
                    rs, lo = [], idx[0]
                    for q, v in enumerate(idx):
                        if q + 1 == len(idx) or idx[q + 1] != v + 1:
                            rs.append(f'{lo}:{v}')
                            if q + 1 < len(idx):
                                lo = idx[q + 1]
                    e2.append((inst, f"{port}@{','.join(rs)}"))
            nid = f'{bid}{tag}'
            nb.append((nid, cls, dbits + ncl, e2))
            if fc:
                fcl[nid] = (dbits, ncl, 0)
        ren[bid] = f'{bid}a'
    m['buses'] = nb
    np_ = {}
    for p, ids in m['paths'].items():
        np_[p] = [ren.get(b_, b_) for b_ in ids]
        if any(b_ in ren for b_ in ids):          # the B half is a parallel path (its own stage count, priced)
            np_[p + '_b'] = [f'{b_}b' if b_ in ren else b_ for b_ in ids]
    m['paths'] = np_
    for d_ in ('clocked', 'fwd_dom'):
        dd = m.get(d_, {})
        for n_, (a, b) in pair.items():
            if n_ in dd:
                dd[a.name] = dd[b.name] = dd.pop(n_)
    for rec in m.get('meso', []):
        if rec.get('inst') in pair:
            rec['inst'] = pair[rec['inst']][0].name + '+' + pair[rec['inst']][1].name
    fa = m['stn_faces'].pop(role, None)
    if fa is not None:
        m['stn_faces'][role + 'a'] = dict(fa)
        m['stn_faces'][role + 'b'] = dict(fa)
    r_ = m.get('station_roles', {}).pop(role, None)
    if r_ is not None:
        for t_ in 'ab':
            m['station_roles'][role + t_] = dict(r_, split_of=role)


def vm_cross_align(M, k, two_layer=False):
    """r23 (r23b GRT: 55k overflow at the abutting VM tile edges): every cross bus between two abutting VM tiles has its
    pins at the SAME along-edge positions on both faces (zero-length die nets, as the index_q band cross buses), packed
    from the edge middle at one track per bit (M4 on E / W, M5 on N / S)."""
    pairs = (('sw', 'se', 'E', 'W', 'e', 'w'), ('nw', 'ne', 'E', 'W', 'e', 'w'),
             ('sw', 'nw', 'N', 'S', 'n', 's'), ('se', 'ne', 'N', 'S', 'n', 's'))
    for a, b, fa, fb, da, db in pairs:
        A, B = M[f'hfd_vm_{a}'], M[f'hfd_vm_{b}']
        L_ = 'M4' if fa in 'EW' else 'M5'
        t = Q.TRK[L_][1] * k
        along = A.h if fa in 'EW' else A.w
        runs = [(A, f't_{da}_{nm}', B, f'f_{db}_{nm}') for nm in ('row', 'wr', 'ctl')] + \
               [(A, f'f_{da}_{nm}', B, f't_{db}_{nm}') for nm in ('row', 'wr', 'ctl')]
        bits = [A.ports[pa][1] for _, pa, _, _ in runs]
        need = [max(1, b_) * t + 4 * t for b_ in bits]      # bits: the master's port width at this k (bundled)
        y = along / 2 - sum(need) / 2
        assert y > 2 * t, ('VM cross buses do not fit the edge', a, b)
        if two_layer and k == 1:
            # r25 (coordinator 2026-10-07 VM decision): ~9.5k cross pins per shared edge at 1 track a bit -> two pin
            #   layers at 2 tracks a bit each (E/W: even bits M4 at 0.096, odd bits M6 at 0.128; N/S: M5 / M7), same
            #   along-edge positions on both faces (zero-length die nets); explicit rects (k = 1)
            L2 = {'M4': 'M6', 'M5': 'M7'}[L_]
            trk = {'M4': (0.012, 0.048), 'M5': (0.012, 0.048), 'M6': (0.016, 0.064), 'M7': (0.016, 0.064)}
            hw = {'M4': 0.012, 'M5': 0.012, 'M6': 0.016, 'M7': 0.016}
            span = [math.ceil(b_ / 2) * 2 * trk[L2][1] + 8 * trk[L2][1] for b_ in bits]
            y = along / 2 - sum(span) / 2
            assert y > 1.0, ('VM cross buses do not fit the edge on two layers', a, b)
            dep = 0.192
            for (X, pa, Y, pb), b_, sp in zip(runs, bits, span):
                ra, rb = [], []
                for i in range(b_):
                    ly = L_ if i % 2 == 0 else L2
                    off, pt = trk[ly]
                    pos = y + 4 * trk[L2][1] + (i // 2) * 2 * pt
                    pos = off + math.ceil((pos - off) / pt - 1e-9) * pt
                    for (Z, pz, fz, rr) in ((X, pa, fa, ra), (Y, pb, fb, rb)):
                        W_, H_ = Z.w, Z.h
                        if fz == 'E':
                            box = (W_ - dep, pos - hw[ly], W_, pos + hw[ly])
                        elif fz == 'W':
                            box = (0.0, pos - hw[ly], dep, pos + hw[ly])
                        elif fz == 'N':
                            box = (pos - hw[ly], H_ - dep, pos + hw[ly], H_)
                        else:
                            box = (pos - hw[ly], 0.0, pos + hw[ly], dep)
                        rr.append((f'{pz}[{i}]', ly, tuple(round(v, 4) for v in box)))
                X.ports[pa] = ('rects', ra)
                Y.ports[pb] = ('rects', rb)
                y += sp
            continue
        for (X, pa, Y, pb), b_, nd in zip(runs, bits, need):
            c = round(y + 2 * t + (nd - 4 * t) / 2, 4)
            X.ports[pa] = ('face', b_, fa, L_, c, 1)
            Y.ports[pb] = ('face', b_, fb, L_, c, 1)
            y += nd


VM8_DIR = 'physical/hbm_accel_die_views/vm/split8/ports'
VM8V_DIR = 'physical/hbm_accel_die_views/vm/vcut8/ports'   # vm8-seam 2026-10-09: vertical-cut halves (vm8_vcut)


def split_vm8(m):
    """r23v (OWNER 2026-10-07 VM fallback, default OFF; VM-split agent a25e9c721716b6662, branch
    claude/hbm-vm-split8-20261007 654733cc5): every VM quadrant tile hfd_vm_<q> becomes a south / north sub-tile
    hfd_vm_<q>_s / _n (699.816 x 500.04 um, north at y + 500.016), each with its own centre M7 ck and rst; every die
    port goes to the half whose record (vm/split8/ports/<master>/ports.json) carries it, and the halves are joined by
    the zero-length seam s2n / n2s (registered both ends, +2 cycles per crossing).  Pin plans fixed to the records."""
    # vm8_vcut (vm8-seam 2026-10-09, vm/vcut8/make_vm_vcut8.py): the quadrant is cut at x = 349.056 into a west / east
    # half (349.056 / 350.760 x 1,000.056 um, both origins on the 1.728 um centre-ck lattice), seam w2e / e2w on the cut;
    # same quadrant outline, so the VM slot is unchanged.  Pins only from the half records (exact rectangles).
    vcut = bool(m['variant'].get('vm8_vcut'))
    HS = 'we' if vcut else 'sn'
    recs = {}
    for q in ('sw', 'se', 'nw', 'ne'):
        for h in HS:
            recs[(q, h)] = json.loads((ROOT / (VM8V_DIR if vcut else VM8_DIR) / f'hfd_vm_{q}_{h}/ports.json').read_text())
    tiles = {it.name: it for it in m['insts'] if it.name.startswith('hb_vm_') and it.master.startswith('hfd_vm_')}
    halves, own = {}, {}
    for nm, it in tiles.items():
        q = it.master[len('hfd_vm_'):]
        if vcut:
            rw, re_ = recs[(q, 'w')], recs[(q, 'e')]
            assert abs(rw['w_um'] + re_['w_um'] - it.w) < 0.05 and rw['h_um'] <= it.h + 0.05, (nm, it.w, it.h)
            hs = Inst(nm + '_w', it.master + '_w', it.x, it.y, rw['w_um'], rw['h_um'], it.orient, kind=it.kind, region=it.region,
                      domain=it.domain)
            hn = Inst(nm + '_e', it.master + '_e', round(it.x + rw['w_um'], 4), it.y, re_['w_um'], re_['h_um'], it.orient,
                      kind=it.kind, region=it.region, domain=it.domain)
        else:
            dy = 500.04 if m['variant'].get('vm8_nonoverlap') else 1000.056 - 500.04
            hs = Inst(nm + '_s', it.master + '_s', it.x, it.y, 699.816, 500.04, it.orient, kind=it.kind, region=it.region, domain=it.domain)
            hn = Inst(nm + '_n', it.master + '_n', it.x, round(it.y + dy, 4), 699.816, 500.04, it.orient, kind=it.kind,
                      region=it.region, domain=it.domain)
        halves[nm] = (hs, hn)
        for h, x in zip(HS, (hs, hn)):
            for p_ in recs[(q, h)]['ports']:
                own[(nm, p_)] = x.name
    m['insts'] = [i for i in m['insts'] if i.name not in tiles] + [x for ab in halves.values() for x in ab]
    nb = []
    for bid, cls, bits, eps in m['buses']:
        e2 = []
        for inst, port in eps:
            if inst not in tiles:
                e2.append((inst, port))
            elif port in ('ck', 'rst'):
                e2 += [(halves[inst][0].name, port), (halves[inst][1].name, port)]
                if port == 'ck' and vcut:   # vm8-seam tap clock leaves (ck<face><i>) ride the same clock net
                    q_ = tiles[inst].master[len('hfd_vm_'):]
                    e2 += [(x.name, tp) for h_, x in zip(HS, halves[inst]) for tp in sorted(recs[(q_, h_)]['ports'])
                           if re.fullmatch(r'ck[wens]\d*', tp)]
            else:
                e2.append((own[(inst, port)], port))
        nb.append((bid, cls, bits, e2))
    for nm, (hs, hn) in halves.items():
        q = tiles[nm].master[len('hfd_vm_'):]
        if vcut:
            rp = recs[(q, 'w')]['ports']
            nb.append((f'{nm}_seam_w2e', 'hub', rp['w2e']['bits'], [(hs.name, 'w2e'), (hn.name, 'w2e')]))
            nb.append((f'{nm}_seam_e2w', 'hub', rp['e2w']['bits'], [(hn.name, 'e2w'), (hs.name, 'e2w')]))
            continue
        rp = recs[(q, 's')]['ports']
        nb.append((f'{nm}_seam_s2n', 'hub', rp['s2n']['bits'], [(hs.name, 's2n'), (hn.name, 's2n')]))
        nb.append((f'{nm}_seam_n2s', 'hub', rp['n2s']['bits'], [(hn.name, 'n2s'), (hs.name, 'n2s')]))
    m['buses'] = nb
    fixed = m.setdefault('fixed_ports', {})
    for (q, h), rec in recs.items():
        W_, H_ = rec['w_um'], rec['h_um']
        spec, order = {}, []
        for p_, v in rec['ports'].items():
            (x0, x1), (y0, y1) = v['x'], v['y']
            n_ = v['bits']
            if v['layer'] == 'M7' and n_ == 1 and 1.0 < x0 < W_ - 1.0 and 1.0 < y0 < H_ - 1.0:
                spec[p_] = ('area', 'M7', x0, y0, 0.064, 0.288)
            else:
                if x0 == x1:
                    face = 'W' if x0 < W_ / 2 else 'E'
                    lo, hi = y0, y1
                else:
                    face = 'S' if y0 < H_ / 2 else 'N'
                    lo, hi = x0, x1
                tr = Q.TRK[v['layer']][1]
                pitch = max(1, round((hi - lo) / max(1, n_ - 1) / tr)) if n_ > 1 else 1
                spec[p_] = ('face', n_, face, v['layer'], round((lo + hi) / 2, 4), pitch)
            order.append(p_)
        if m['variant'].get('vm8_exact_pins'):
            # Preserve each requested rectangle and bit identity. Ranges lose
            # single-pin faces and the half-track origin of even-width groups.
            text=(ROOT / (VM8V_DIR if vcut else VM8_DIR) / f'hfd_vm_{q}_{h}/io_place.tcl').read_text()
            pattern=r'place_pin -pin_name \{(\w+)\[(\d+)\]\} -layer (\w+) -location \{([\d.]+) ([\d.]+)\} -pin_size \{([\d.]+) ([\d.]+)\}'
            exact=defaultdict(dict)
            for port,bit,layer,x,y,w_,h_ in re.findall(pattern,text):
                bit=int(bit);x,y,w_,h_=map(float,(x,y,w_,h_))
                if bit in exact[port]:
                    raise ValueError(f'duplicate VM requested pin: {q}/{h}/{port}[{bit}]')
                exact[port][bit]=(f'{port}[{bit}]',layer,(x-w_/2,y-h_/2,x+w_/2,y+h_/2))
            if set(exact)!=set(rec['ports']):
                raise ValueError(f'VM requested pin port mismatch: {q}/{h}')
            for port,v in rec['ports'].items():
                if set(exact[port])!=set(range(v['bits'])):
                    raise ValueError(f'VM requested pin bit mismatch: {q}/{h}/{port}')
                spec[port]=('rects',[exact[port][b] for b in range(v['bits'])])

        def fn(mst, k=1, spec=spec, order=order):
            sp_ = dict(spec)
            if k > 1 and any(v[0]=='rects' for v in sp_.values()):
                raise ValueError('exact VM requested pins require full width k=1')
            if k > 1:
                _bundle_pack(mst, sp_, order, k)
            mst.ports, mst.order = sp_, list(order)
        fixed[f'hfd_vm_{q}_{h}'] = fn
    m['vm8'] = {nm: [x.name for x in ab] for nm, ab in halves.items()}


def split_attn(m, half_dir):
    """r25s (attn-split): every hfd_attn_tile instance becomes hfd_attn_half_lo (master frame: the bottom of the slot)
    + hfd_attn_half_hi (the top), abutting; the tile's die ports go to the half that owns them (ATTN_HALF_OF; ck to
    both), and the seam buses xp (lo -> hi, the ROOT packet) / xr (lo -> hi, quad row 0's results) join face-to-face
    pin banks.  Pin plans fixed to the half records (exact rectangles at k = 1, face runs when bundled).  m['tiles'] and
    the scan grids keep the lo halves (one per logical tile)."""
    recs = {h: json.loads((ROOT / half_dir / f'hfd_attn_half_{h}/ports.json').read_text()) for h in ('lo', 'hi')}
    hl, hh = recs['lo']['h_um'], recs['hi']['h_um']
    tiles = {it.name: it for it in m['insts'] if it.master == 'hfd_attn_tile'}
    halves = {}
    for nm, it in tiles.items():
        assert it.h + SHAVE >= hl + hh - 1e-6, ('attention tile slot shorter than the two halves', nm, it.h, hl + hh)
        flip = it.orient in ('MX', 'R180')                  # mirrored copies: lo on top, still facing its quadrant
        lo = Inst(nm + '_lo', 'hfd_attn_half_lo', it.x, round(it.y + (hh if flip else 0.0), 4), recs['lo']['w_um'], hl,
                  it.orient, kind=it.kind, region=it.region, domain=it.domain)
        hi = Inst(nm + '_hi', 'hfd_attn_half_hi', it.x, round(it.y + (0.0 if flip else hl), 4), recs['hi']['w_um'], hh,
                  it.orient, kind=it.kind, region=it.region, domain=it.domain)
        halves[nm] = dict(lo=lo, hi=hi)
    m['insts'] = [i for i in m['insts'] if i.name not in tiles] + [x for d in halves.values() for x in (d['lo'], d['hi'])]
    nb = []
    for bid, cls, bits, eps in m['buses']:
        e2 = []
        for inst, port in eps:
            if inst not in tiles:
                e2.append((inst, port))
            elif port == 'ck':
                e2 += [(halves[inst]['lo'].name, port), (halves[inst]['hi'].name, port)]
            else:
                e2.append((halves[inst][ATTN_HALF_OF[port]].name, port))
        nb.append((bid, cls, bits, e2))
    for nm, d in halves.items():
        for p_ in ('xp', 'xr'):
            nb.append((f'{nm}_seam_{p_}', 'hub', recs['lo']['ports'][p_]['bits'], [(d['lo'].name, p_), (d['hi'].name, p_)]))
    m['buses'] = nb
    for k_ in ('tiles',):
        m[k_] = [halves[t.name]['lo'] if t.name in halves else t for t in m[k_]]
    for sc in m['scan'].values():
        sc['tiles'] = [[halves[t.name]['lo'] for t in row] for row in sc['tiles']]
    if isinstance(m.get('clocked'), dict):
        for nm, d in halves.items():
            if nm in m['clocked']:
                dom = m['clocked'].pop(nm)
                m['clocked'][d['lo'].name] = m['clocked'][d['hi'].name] = dom
    for e in m.get('meso', []):
        if e.get('inst') in halves:
            e['inst'] = halves[e['inst']]['lo'].name            # the q receiver
    attn_half_fixed_ports(m, half_dir)
    m['attn_halves'] = {nm: [d['lo'].name, d['hi'].name] for nm, d in halves.items()}


def attn_half_fixed_ports(m, half_dir):
    """pin plans of hfd_attn_half_lo / _hi fixed to the half records in half_dir (exact rectangles at k = 1, face runs when
    bundled).  split_attn's tail; hbmdie-1011: also re-bound on the R25GQ net by the taller-slot knob attn_tall."""
    recs = {h: json.loads((ROOT / half_dir / f'hfd_attn_half_{h}/ports.json').read_text()) for h in ('lo', 'hi')}
    fixed = m.setdefault('fixed_ports', {})
    for h, rec in recs.items():
        text = (ROOT / half_dir / f'hfd_attn_half_{h}/io_place.tcl').read_text()
        pat = r'place_pin -pin_name \{(\w+)\[(\d+)\]\} -layer (\w+) -location \{([\d.]+) ([\d.]+)\} -pin_size \{([\d.]+) ([\d.]+)\}'
        exact = defaultdict(dict)
        for port, bit, layer, x, y, w_, h_ in re.findall(pat, text):
            x, y, w_, h_ = map(float, (x, y, w_, h_))
            exact[port][int(bit)] = (f'{port}[{bit}]', layer, (x - w_ / 2, y - h_ / 2, x + w_ / 2, y + h_ / 2))
        if set(exact) != set(rec['ports']) or any(set(exact[p_]) != set(range(v['bits'])) for p_, v in rec['ports'].items()):
            raise ValueError(f'attn half {h}: io_place / ports.json mismatch')
        W_, H_ = rec['w_um'], rec['h_um']
        spec, order = {}, []
        for p_, v in rec['ports'].items():
            (x0, x1), (y0, y1) = v['x'], v['y']
            n_ = v['bits']
            if x0 == x1:
                face, lo_, hi_ = ('W' if x0 < W_ / 2 else 'E'), y0, y1
            else:
                face, lo_, hi_ = ('S' if y0 < H_ / 2 else 'N'), x0, x1
            tr = Q.TRK[v['layer']][1]
            # bundled planning: a port in separate runs (xr: W and E ends of the seam) is planned at its longest run
            al = sorted(((r[2][0] + r[2][2]) / 2 if face in 'SN' else (r[2][1] + r[2][3]) / 2) for r in exact[p_].values())
            runs, cur = [], [al[0]]
            for u in al[1:]:
                if u - cur[-1] > 10.0:
                    runs.append(cur)
                    cur = []
                cur.append(u)
            runs.append(cur)
            run_ = max(runs, key=len)
            pitch = max(1, round((hi_ - lo_) / max(1, n_ - 1) / tr)) if n_ > 1 and len(runs) == 1 else 4
            spec[p_] = ('face', n_, face, v['layer'], round((run_[0] + run_[-1]) / 2, 4), pitch)
            order.append(p_)
        rects = {p_: ('rects', [exact[p_][b] for b in range(v['bits'])]) for p_, v in rec['ports'].items()}

        def fn(mst, k=1, spec=spec, rects=rects, order=order):
            if k > 1:                                       # bundled planning: face runs (the jogs between bank
                sp_ = dict(spec)                            #   chunks are below the bundle pitch)
                _bundle_pack(mst, sp_, order, k)
            else:
                sp_ = dict(rects)
            mst.ports, mst.order = sp_, list(order)
        fixed[f'hfd_attn_half_{h}'] = fn


MTP_X_STOP_LEF = 'physical/hbm_accel_die_views/mtp/hfd_mtp.lef'


def fix_ports_mtp_x_stop(m):
    """hgi-takeover 2026-10-09: the R25G MTP slot master hfd_mtp keeps its die bus ports (the stop_model groups f_cmdproc /
    t_cmdproc / f_su_red / f_router / t_router / t_coll / f_coll, plus ck / rst) but every bit's PIN is the closed view's
    raw controller pin (name, layer, rectangle from physical/hbm_accel_die_views/mtp/hfd_mtp.lef): group bit i of field
    F is the pin F[j] (F for 1-bit fields), ck is clk and rst is rst_n.  The view then checks MATCH unchanged (no
    re-route); the die netlist binds the groups to the raw ports (die_top_lint real block hfd_mtp = hfd_mtp_x_stop)."""
    from hbm_mtp_native_contract import stop_model
    r = S.real_lef(MTP_X_STOP_LEF)
    groups = stop_model(ROOT)['groups']
    rects, order = {}, []
    def pin(nm):
        layer, box = r['pins'][nm]
        return (nm, layer, tuple(box))
    for g, gr in groups.items():
        bits = []
        for f in gr['fields']:
            for b in range(f['width']):
                bits.append(pin(f['port'] if f['width'] == 1 else f"{f['port']}[{b}]"))
        rects[g] = ('rects', bits)
        order.append(g)
    rects['ck'] = ('rects', [pin('clk')]); rects['rst'] = ('rects', [pin('rst_n')])
    order += ['ck', 'rst']
    used = {x[0] for v in rects.values() for x in v[1]}
    if used != set(r['pins']):
        raise ValueError(f'mtp x_stop pins: {len(set(r["pins"]) - used)} view pins unmapped, {len(used - set(r["pins"]))} unknown')

    def fn(mst, k=1, rects=rects, order=order):
        mst.ports, mst.order = dict(rects), list(order)
    m.setdefault('fixed_ports', {})['hfd_mtp'] = fn


def fix_ports_from_views(m, masters_):
    """r17: masters whose generated pin plan must stay the CLOSED view's although the block moved (barrier_low): the
    pins are fixed to the view LEF (same faces / layers / positions), so the view still checks MATCH."""
    fixed = m.setdefault('fixed_ports', {})
    idx = json.loads((ROOT / 'physical/hbm_accel_die_views/index.json').read_text())['masters']
    for mst in masters_:
        v = idx[mst]
        r = S.real_lef(f"{v['dir']}/{v['lef']}")
        ports = defaultdict(list)
        for pn, (layer, (x0, y0, x1, y1)) in r['pins'].items():
            base = re.sub(r'\[\d+\]$', '', pn)
            ports[base].append([pn if '[' in pn else f'{pn}[0]', layer, x0, y0, x1, y1])
        rec = {}
        for b, pins in ports.items():
            q = pins[0]
            face = 'W' if q[2] <= 0.01 else 'E' if q[4] >= r['w'] - 0.01 else 'S' if q[3] <= 0.01 else 'N'
            rec[b] = dict(bits=len(pins), layer=q[1], face=face, pins=pins)
        spec, order = _split_spec(rec)

        def fn(mst_, k=1, spec=spec, order=order):
            sp_ = dict(spec)
            if k > 1:
                _bundle_pack(mst_, sp_, order, k)
            mst_.ports, mst_.order = sp_, list(order)
        fixed[mst] = fn


def apply_splits(m, specs, lattice=None):
    """r16i: replace each instance of a split parent by its bands (same slot, mirrored with the parent), move every
    parent-port bus end to the band that owns the port, give every band the parent's ck / rst nets, add the cross buses
    between abutting bands, and fix the band masters' pin plans to the split record (m['fixed_ports'])."""
    V_ck = (m.get('variant') or {}).get('ck_centre')
    fixed = m.setdefault('fixed_ports', {})
    lattice = lattice or {}
    for parent, rel in specs.items():
        sp = json.loads((ROOT / rel).read_text())
        bands = sorted(sp['bands'].items(), key=lambda kv: kv[1]['y0_um'])
        Hp = sp['parent_size_um'][1]
        recs = {}
        # r25m (MTP-DIE): ports a die variant adds to a closed split view (an ECO pin set the owning block stream adds
        # to the block): {parent: {port: (band, bits, face, layer, fraction along the face, pitch in tracks)}}
        extra = (m.get('variant') or {}).get('split_extra_ports', {}).get(parent, {})
        for bn, b in bands:
            recs[bn] = json.loads((ROOT / rel).parent.joinpath(bn, 'ports.json').read_text())
            spec, order = _split_spec(recs[bn]['ports'])
            for pn_, (bn_, bits_, face_, layer_, frac_, pitch_) in extra.items():
                if bn_ == bn:
                    span_ = sp['parent_size_um'][0] if face_ in 'NS' else b['h_um']
                    spec[pn_] = ('face', bits_, face_, layer_, round(frac_ * span_, 4), pitch_)
                    order.append(pn_)
            def fn(mst, k=1, spec=spec, order=order):
                sp_ = dict(spec)
                if k > 1:
                    _bundle_pack(mst, sp_, order, k)
                if V_ck:
                    ck_centre(mst, sp_)
                mst.ports, mst.order = sp_, list(order)
            fixed[bn] = fn
        # mtp-lead 2026-10-10 (design standard 2026-10-09, svc --fc practice): a band's face clock taps (cks / ckn / cke /
        # ckw in its own pin record) ride the parent's ck net: die clock leaves balanced by the die tree.  The offset each
        # leaf needs (the band's tap source latency) is recorded in m['clock_leaf_offsets'] (from <record dir>/fc_taps.json
        # when the band's route has measured it, else PENDING), as for the svc segments.
        fc_taps_ = {bn: [p_ for p_ in ('cks', 'ckn', 'cke', 'ckw') if p_ in recs[bn]['ports']] for bn, _ in bands}
        fct_ = (ROOT / rel).parent / 'fc_taps.json'
        fc_off_ = json.loads(fct_.read_text()) if fct_.exists() else {}
        owner = {pp: bn for bn, b in bands for pp in b['parent_ports']}
        # mtp-lead 2026-10-09: a band's own new ports (e.g. MX1 f_am) can carry a die bus addressed to the parent
        owner.update({pn_: bn for bn, b in bands for pn_ in b.get('new_ports', {}) if pn_ not in ('ck', 'rst')})
        owner.update({pn_: v_[0] for pn_, v_ in extra.items()})
        new_insts, repl = [], {}
        for it in m['insts']:
            if it.master != parent:
                new_insts.append(it)
                continue
            assert abs(it.h - Hp) < 0.01, (parent, it.h, Hp)
            names = {}
            mx = it.orient in ('MX', 'R180')
            if V_ck and any(bn in CK_CENTRE for bn, _ in bands):    # r18: band origins on x = 0 mod 1.728 (M7 ck pin)
                it.x = math.ceil(round(it.x * 1000) / 1728) * 1.728
            lat = lattice.get(parent, {})
            top = None
            for bn, b in (bands[::-1] if mx else bands):     # bottom-up in die y
                y0, h = b['y0_um'], b['h_um']
                yy = it.y + (Hp - y0 - h if mx else y0)
                r_ = lat.get(f'{bn}:{"MX" if mx else "R0"}')
                if r_ is not None:      # r16i-l: pack on the band's own legal origin lattice (ot_mts rule, measured r9)
                    lo = yy if top is None else max(yy, top)
                    k_ = math.ceil(round((lo - r_) / LAT_Y, 6))
                    yy = round(k_ * LAT_Y + r_, 4)
                    if top is not None and yy < top - 1e-6:
                        yy = round(yy + LAT_Y, 4)
                top = yy + h
                nm = f'{it.name}_{bn.rsplit("_", 1)[1]}'
                new_insts.append(Inst(nm, bn, it.x, round(yy, 4), it.w, h, it.orient, kind=it.kind, region=it.region,
                                      domain=it.domain))
                names[bn] = nm
            repl[it.name] = names
        m['insts'] = new_insts
        nb = []
        for bid, cls, bits, eps in m['buses']:
            e2 = []
            for inst, port in eps:
                if inst not in repl:
                    e2.append((inst, port))
                elif port in ('ck', 'rst'):
                    e2 += [(repl[inst][bn], port) for bn, _ in bands]
                    if port == 'ck':
                        e2 += [(repl[inst][bn], tp) for bn, _ in bands for tp in fc_taps_[bn]]
                else:
                    assert port in owner, (parent, port)
                    e2.append((repl[inst][owner[port]], port))
            nb.append((bid, cls, bits, e2))
        for pin_, names in repl.items():
            for j, x in enumerate(sp['cross']):
                fb, fp = x['from'].split('.')
                tb, tp = x['to'].split('.')
                nb.append((f'{pin_}_x{j}', 'hub', x['bits'], [(names[fb], fp), (names[tb], tp)]))
        m['buses'] = nb
        hub = m['hub']
        for k_, v_ in list(hub.items()):
            if getattr(v_, 'name', None) in repl:
                hub[k_] = next(i for i in new_insts if i.name == repl[v_.name][bands[-1][0]])
        m.setdefault('splits', {})[parent] = dict(record=rel, bands=[bn for bn, _ in bands], instances=sorted(repl))
        for pin_, names in repl.items():
            for bn, nm in names.items():
                for tp in fc_taps_[bn]:
                    o_ = (fc_off_.get(bn) or {}).get(tp)
                    net_ = next((b_[0] for b_ in nb if (nm, 'ck') in b_[3]), None)
                    m.setdefault('clock_leaf_offsets', []).append(dict(
                        net=net_, inst=nm, master=bn, pin=tp, ref_pin='ck', offset_ps=o_['ps'] if o_ else None,
                        source=o_['source'] if o_ else None, status='resolved' if o_ else
                        'PENDING: tap source latency not measured yet (band route not closed)'))


def _bundle_pack(mst, sp_, order, k):
    """bundled view (k > 1): runs of one face packed apart (>= two bundled tracks between runs)."""
    byf = defaultdict(list)
    for pn in order:
        if sp_[pn][0] != 'face':      # area / xy pins are not bundled-packed
            continue
        byf[sp_[pn][2]].append(pn)
    for f_, pns in byf.items():
        runs = []
        for pn in pns:
            t_ = sp_[pn]
            st_ = Q.TRK[t_[3]][1] * k * t_[5]
            n_ = max(1, math.ceil(t_[1] / k))
            runs.append([t_[4] - n_ * st_ / 2, n_ * st_, pn])
        along = mst.h if f_ in 'EW' else mst.w
        gap = 2 * Q.TRK['M4' if f_ in 'EW' else 'M5'][1] * k
        for r_ in runs:     # the clamp Q.pin_rects applies
            r_[0] = min(max(r_[0], gap), along - gap - r_[1])
        runs.sort()
        for a_, b_ in zip(runs, runs[1:]):          # push up
            b_[0] = max(b_[0], a_[0] + a_[1] + gap)
        if runs and runs[-1][0] + runs[-1][1] > along - gap:   # then down from the top
            runs[-1][0] = along - gap - runs[-1][1]
            for a_, b_ in zip(runs[-2::-1], runs[::-1]):
                a_[0] = min(a_[0], b_[0] - gap - a_[1])
        for r_ in runs:
            t_ = sp_[r_[2]]
            sp_[r_[2]] = t_[:4] + (round(r_[0] + r_[1] / 2, 4),) + t_[5:]



def _xy_or_split_spec(ports):
    """_split_spec plus 'xy' ports (S-face M5 pins at explicit x, e.g. a svc band's PHY dfi slice)."""
    face_ports = {pn: v for pn, v in ports.items() if v['face'] != 'xy'}
    spec, order = _split_spec(face_ports)
    for pn, v in ports.items():
        if v['face'] == 'xy':
            pins = sorted(v['pins'], key=lambda q: int(re.search(r'\[(\d+)\]', q[0]).group(1)))
            spec[pn] = ('xy', [round((q[2] + q[4]) / 2, 4) for q in pins])
            order.append(pn)
    return spec, order


def fc_tap_latency(rel, band, pins):
    """Per-segment face clock tap latency from the segment's block timing model: set_clock_latency -source <ps> on
    ckw / cke in its SDC (the split record's sibling sdc_* directories, <band>*.sdc), read in ps (values < 10 are ns).
    Returns {pin: {ps, source}} for the pins that have one."""
    out = {}
    base = (ROOT / rel).parent.parent
    tag = (ROOT / rel).parent.name.replace('split', '')            # split_psfc -> _psfc
    for d in [base / f'sdc{tag}'] + sorted(p_ for p_ in base.glob('sdc*') if p_.name != f'sdc{tag}'):
        for f in sorted(d.glob(f'{band}*.sdc')) if d.is_dir() else []:
            for ln in f.read_text().splitlines():
                mm = re.match(r'\s*set_clock_latency\s+(.*)$', ln)
                if not mm or '-source' not in mm.group(1):
                    continue
                toks = mm.group(1)
                val = re.search(r'(?:^|\s)(-?[0-9]+(?:\.[0-9]+)?)(?=\s)', ' ' + re.sub(r'\[.*', '', toks) + ' ')
                tgt = re.search(r'\[get_(?:ports|clocks)\s+\{?([^\]\}]*)', toks)
                if not val or not tgt:
                    continue
                v = float(val.group(1))
                ps = v * 1000.0 if v < 10 else v
                for tp in pins:
                    if re.search(rf'(^|\s|\{{){tp}(\[0\])?(\s|\}}|$)', tgt.group(1)) and tp not in out:
                        out[tp] = dict(ps=round(ps, 3), source=str(f.relative_to(ROOT)))
        if out:
            break
    return out


def apply_splits_x(m, rel):
    """r16j: x-axis split (hbm_die_split_x.v1).  Each instance of a split parent is replaced by its bands in the same
    slot (same orientation; MY / R180 mirror the band x), parent-port bus ends move to the owning band under its band
    port name (port_map), a bus on a port split by bit range (the svc PHY dfi bundle) becomes one bus per band whose
    real-macro end is the slice 'dfi@lo:hi', ck / rst reach every band, and the record's cross buses join abutting
    bands of each parent instance."""
    V_ck = (m.get('variant') or {}).get('ck_centre')
    sp = json.loads((ROOT / rel).read_text())
    fc_lat_ = {}
    fixed = m.setdefault('fixed_ports', {})
    # r25m (MTP-DIE, RQ-ING-4): ports a die variant adds to a split parent (the loader memory chains on the stream
    # services): each lands on the band under its peer's x, as an inner-face (master N) M5 run at the free face span nearest the peer's x at the peer's x (an
    # ECO pin set the owning block stream adds to that band's view)
    newp = (m.get('variant') or {}).get('split_x_new_ports', {})
    by_ = {it.name: it for it in m['insts']}
    extra_x, new_owner = defaultdict(dict), {}
    if newp:
        for bid, cls, bits, eps in m['buses']:
            for i, (inst, port) in enumerate(eps):
                it = by_.get(inst)
                if it is None or port not in newp or it.master not in sp['parents']:
                    continue
                o = by_[eps[1 - i][0]] if len(eps) == 2 else None
                ox = (o.x + o.w / 2) if o is not None else it.x + it.w / 2
                ordered = sp['parents'][it.master]['bands']
                forced = (m.get('variant') or {}).get('split_x_new_port_band', {}).get(port)
                if isinstance(forced, dict):        # R25GQ 10-10: a per-parent band (svc family SW vs SE ks maps)
                    forced = forced.get(it.master)
                eligible = [ordered[forced]] if forced is not None else ordered
                for bn in eligible:
                    b = sp['bands'][bn]
                    if forced is not None or it.x + b['x0_um'] <= ox < it.x + b['x0_um'] + b['w_um'] or bn == ordered[-1]:
                        xl = min(max(ox - it.x - b['x0_um'], 0.1 * b['w_um']), 0.9 * b['w_um'])
                        if port not in b.get('ports', {}):     # split_psn: lq / lr / kc are pinned in the record itself
                            extra_x[bn][port] = ('face', newp[port], 'N', 'M5', round(xl, 4), 2)
                        new_owner[(inst, port)] = bn
                        break
    fc_taps = {}     # hbm-forks --fc (split_psfc): face clock taps ckw / cke ride the band's ck net (balanced die leaves)
    for bn in sp['bands']:
        rec = json.loads((ROOT / rel).parent.joinpath(bn, 'ports.json').read_text())
        fc_taps[bn] = [p_ for p_ in ('ckw', 'cke') if p_ in rec['ports']]
        if fc_taps[bn]:
            fc_lat_[bn] = fc_tap_latency(rel, bn, fc_taps[bn])
        spec, order = _xy_or_split_spec(rec['ports'])
        for pn_, t_ in extra_x.get(bn, {}).items():
            # the nearest free N-face M5 span (existing band pins + earlier new ports, 2 um apart)
            half_ = t_[1] * t_[5] * 0.048 / 2 + 2.0
            occ = [(c - b_ * pt * 0.048 / 2 - 2.0, c + b_ * pt * 0.048 / 2 + 2.0)
                   for f_, b_, fc_, ly, c, pt in (v_ for v_ in spec.values() if v_[0] == 'face') if fc_ == 'N' and ly == 'M5']
            wb = sp['bands'][bn]['w_um']
            cands = sorted((abs(c_ - t_[4]), c_) for c_ in (half_ + 0.5 * i for i in range(int((wb - 2 * half_) / 0.5) + 1))
                           if all(c_ + half_ <= a or c_ - half_ >= b for a, b in occ))
            assert cands, ('no free N-face span for', bn, pn_)
            spec[pn_] = t_[:4] + (round(cands[0][1], 3),) + t_[5:]
            order.append(pn_)
        def fn(mst, k=1, spec=spec, order=order):
            sp_ = dict(spec)
            if k > 1:       # bundled view: an xy port becomes one S-face M5 run centred on its pins
                for pn, t_ in list(sp_.items()):
                    if t_[0] == 'xy':
                        sp_[pn] = ('face', len(t_[1]), 'S', 'M5', round(sum(t_[1]) / len(t_[1]), 4), 1)
                _bundle_pack(mst, sp_, order, k)
            if V_ck:
                ck_centre(mst, sp_)
            mst.ports, mst.order = sp_, list(order)
        fixed[bn] = fn
    repl, pmap = {}, {}
    new_insts = []
    for it in m['insts']:
        par = sp['parents'].get(it.master)
        if par is None:
            new_insts.append(it)
            continue
        names = {}
        mirror_x = it.orient in ('MY', 'R180')
        assert not mirror_x, (it.name, it.orient)     # x packing below assumes R0 / MX parents (all four are)
        end = None
        for j, bn in enumerate(par['bands']):
            b = sp['bands'][bn]
            x0, w = b['x0_um'], b['w_um']
            # r12 a_real (measured): split cuts are off the site grid, ot_mts snapped bands into 14 overlaps.  Pack
            # left to right on x = 0 mod 0.054 (site) and x = nominal mod 0.048 (M5 tracks: band pins keep their
            # track), at or right of the nominal origin and the previous band's end (period lcm 0.432 um).
            nom = round((it.x + x0) * 1000)
            lo = nom if end is None else max(nom, end)
            xd = lo
            m64 = 64 if ((m.get('variant') or {}).get('ck_centre') and bn in CK_CENTRE) else 1
            while xd % 54 or (xd - nom) % 48 or xd % m64:
                xd += 6
            end = xd + round(w * 1000)
            xx = xd / 1000.0
            nm = f'{it.name}_s{j}'
            new_insts.append(Inst(nm, bn, round(xx, 4), it.y, w, b['h_um'], it.orient, kind=it.kind, region=it.region,
                                  domain=it.domain))
            names[bn] = nm
        repl[it.name] = names
        pm = defaultdict(list)
        for bn, ports in par['port_map'].items():
            for bp, v in ports.items():
                if v['parent_port'] != '<new>':
                    pm[v['parent_port']].append((names[bn], bp, v['parent_bits'][0], v['parent_bits'][1]))
        pmap[it.name] = pm
    m['insts'] = new_insts
    nb = []
    for bid, cls, bits, eps in m['buses']:
        hit = [(i, e) for i, e in enumerate(eps) if e[0] in repl]
        if not hit:
            nb.append((bid, cls, bits, eps))
            continue
        split = [e for _, e in hit if e[1] not in ('ck', 'rst') and (e[0], e[1]) not in new_owner
                 and len(pmap[e[0]][e[1]]) > 1]
        if split:
            assert len(split) == 1 and len(eps) == 2, (bid, eps)
            (pi, pp), = split
            other = next(e for e in eps if e[0] != pi)
            for bi, bp, lo, hi in sorted(pmap[pi][pp], key=lambda t: t[2]):
                nb.append((f'{bid}_{bi.rsplit("_", 1)[1]}', cls, hi - lo + 1, [(other[0], f'{other[1]}@{lo}:{hi}'), (bi, bp)]))
            continue
        e2 = []
        for inst, port in eps:
            if inst not in repl:
                e2.append((inst, port))
            elif port in ('ck', 'rst'):
                e2 += [(nm, port) for nm in repl[inst].values()]
                if port == 'ck':
                    e2 += [(nm, tp) for bn_, nm in repl[inst].items() for tp in fc_taps[bn_]]
            elif (inst, port) in new_owner:
                e2.append((repl[inst][new_owner[(inst, port)]], port))
            else:
                (bi, bp, lo, hi), = pmap[inst][port]
                e2.append((bi, bp))
        nb.append((bid, cls, bits, e2))
    for inst, names in repl.items():
        fam = next(par for par in sp['parents'] if names.get(sp['parents'][par]['bands'][0]))
        for j, x in enumerate(sp['cross']):
            fb, fp = x['frm'].split('.')
            tb, tp = x['to'].split('.')
            if fb in names and tb in names:
                nb.append((f'{inst}_x{j}', 'hub', x['bits'], [(names[fb], fp), (names[tb], tp)]))
    m['buses'] = nb
    m.setdefault('splits', {})['svc_x'] = dict(record=rel, instances=sorted(repl))
    # coordinator 2026-10-09 ~22:10: a face clock tap (ckw / cke) clocks the segment's face registers directly, while ck
    # reaches its interior registers through the segment's own tree (insertion I ~480-540 ps).  The block timing model
    # declares I as set_clock_latency -source on ckw / cke; the die clock plan must deliver those leaves I LATER than
    # the segment's ck leaf (a per-leaf delay / tap in the die tree) so face and interior registers line up.
    rows_ = []
    for inst, names in repl.items():
        for bn, nm in names.items():
            for tp in fc_taps.get(bn, ()):
                lat = fc_lat_[bn].get(tp)
                rows_.append(dict(net='clk_hbm', inst=nm, master=bn, pin=tp, ref_pin='ck',
                                  offset_ps=lat['ps'] if lat else None, source=lat['source'] if lat else None,
                                  status='resolved' if lat else 'PENDING: no set_clock_latency -source on this pin in the '
                                  'segment timing model yet (segment not closed)'))
    if rows_:
        m.setdefault('clock_leaf_offsets', []).extend(rows_)   # mtp-lead: keep the cmdproc bands' rows


# ------------------------------------------------------------------------------------------------ station masters
_OFLIP = {'R0': {}, 'MX': {'N': 'S', 'S': 'N'}, 'MY': {'E': 'W', 'W': 'E'},
          'R180': {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}}


def share_stations(m):
    """r15 stn_share (H13): one master per station role.  Every station was its own master (hfd_stn_<n>, placed R0 with
    die-frame faces).  Two stations share a master when their kind, size, port widths and port faces agree up to a
    mirror; the canonical frame of a role is the orientation whose (port, face, width) list sorts first, and each
    copy is placed in the orientation that maps it onto that frame (MX / MY / R180)."""
    pw = defaultdict(dict)
    for bid, cls, bits, eps in m['buses']:
        for inst, port in eps:
            pw[inst][port] = max(pw[inst].get(port, 0), bits)
    reg, faces = {}, {}
    # r23 stable_roles: a role keeps the name it had in the registry (station_roles.json, written from the r22 build):
    # a re-layout no longer renumbers the closed station views
    stable = None
    if m['variant'].get('stable_roles'):
        rf = ROOT / 'physical/hbm_accel_die_views/station_roles.json'
        stable = json.loads(rf.read_text()) if rf.exists() else {}
    for it in m['insts']:
        if it.kind != 'waypoint':
            continue
        kind = re.match(r'hfd_([a-z]+)_\d+$', it.master).group(1)
        f0 = m['stn_faces'].get(it.master, {})
        best = None
        for o in ('R0', 'MX', 'MY', 'R180'):
            fl = _OFLIP[o]
            key = (kind, round(it.w, 3), round(it.h, 3),
                   tuple(sorted((p, fl.get(f0[p], f0[p]) if p in f0 else '-', w) for p, w in pw[it.name].items())))
            if best is None or repr(key) < repr(best[0]):
                best = (key, o)
        key, o = best
        if key not in reg:
            nm_ = stable.get(repr(key)) if stable else None
            if nm_ is None:          # a new role: next number after every registered and used one
                used = set(reg.values()) | set(stable.values() if stable else ())
                k_ = 0
                while f'hfd_{kind}_r{k_}' in used or any(v.endswith(f'_r{k_}') for v in used):
                    k_ += 1
                nm_ = f'hfd_{kind}_r{k_}' if stable else f'hfd_{kind}_r{len(reg)}'
            reg[key] = nm_
            faces[reg[key]] = {p: f for p, f, _ in key[3] if f != '-'}
        it.master = reg[key]
        it.orient = o
    m['stn_faces'] = faces
    m['station_role_keys'] = {repr(k): v for k, v in reg.items()}
    m['station_roles'] = {v: dict(kind=k[0], w_um=k[1], h_um=k[2], ports={p: w for p, _, w in k[3]},
                                  copies=sum(1 for it in m['insts'] if it.master == v)) for k, v in reg.items()}


# ------------------------------------------------------------------------------------------------ nets and waypoints
def _cxy(it, face, along=0.5):
    if face == 'S':
        return (it.x + it.w * along, it.y)
    if face == 'N':
        return (it.x + it.w * along, it.y + it.h)
    if face == 'W':
        return (it.x, it.y + it.h * along)
    return (it.x + it.w, it.y + it.h * along)


MESO_UM2 = 4842.31 / 0.6       # one ot_meso_fifo W512 D4 crossing, std-cell area (results/uarch/meso_fifo_20261004/
#                                 clocking_model_measured.json) at 0.6 utilisation


def fcbits(fc):
    """Forwarded clocks of a forwarded-link segment: one per 512 b slice and direction (ot_fwd_link_stage W=512)."""
    if not fc:
        return 0
    return sum(math.ceil(b / 512) for b in fc if b > 0)


def fcsplit(fc):
    """(downstream, upstream) forwarded clocks of fc = (down bits[, up bits])."""
    return (math.ceil(fc[0] / 512) if fc[0] > 0 else 0,
            math.ceil(fc[1] / 512) if len(fc) > 1 and fc[1] > 0 else 0)


def _dirface(ax, ay, bx, by):
    """Face of a block at (ax, ay) that looks toward (bx, by)."""
    if abs(bx - ax) >= abs(by - ay):
        return 'E' if bx > ax else 'W'
    return 'N' if by > ay else 'S'


def _router(m, B, P):
    """(station, chain) closures over the die model m: forwarded-link / multicast / gather stations placed in free
    channel space, and polyline chains with a station every <= WAYPOINT_UM.  Shared by the DS SM die and the Qwen tile
    die builders."""
    insts = m['insts']
    g = m['geo']
    faces = m['stn_faces']
    n_wp = [max([int(q.group(1)) for it in insts
                 if (q := re.match(r'^w(\d+)_',it.name))]+[0])]
    pf = m['variant'].get('port_fix')
    fwd_on = m['variant'].get('fwd')
    blocked = [(it.x - 4.32, it.y - 4.32, it.x + it.w + 4.32, it.y + it.h + 4.32) for it in insts]

    blocked += [tuple(r) for r in m.get('reserved_regions', [])]

    def free(x, y, w, h):
        if x < EDGE or y < EDGE or x + w > g['W'] - EDGE or y + h > g['H'] - EDGE:
            return False
        for (a, b, c, d) in blocked:
            if a < x + w and x < c and b < y + h and y < d:
                return False
        return True

    def stn_size(bits, horizontal):
        span = up(bits * 0.048 * 1.1 + 12.0, GX if not horizontal else GY)
        area = 4 * bits * 0.2916 / 0.6 + 2000.0          # 4 stages of the bus width at 0.6 utilisation
        short = max(34.56, area / span)
        if horizontal:      # ports on E/W faces: tall
            return up(short, GX), up(span, GY)
        return up(span, GX), up(short, GY)

    def station(cx, cy, chain, bits, fa, fb, horizontal, kind='stn', extra=None, fifo_bits=0, dom='stream'):
        w, h = stn_size(bits, horizontal)
        if m['variant'].get('native_indexer') and bits == 1 and chain.startswith('idx_'):
            from hbm_indexer_r25i_model import hbm_indexer_scalar_credit_relay_model
            scalar_model = hbm_indexer_scalar_credit_relay_model()
            w,h=scalar_model['outline_um']
            m['scalar_credit_station_model']=scalar_model
        if extra:
            w, h = max(w, extra[0]), max(h, extra[1])
        nf = math.ceil(fifo_bits / 512) if fifo_bits else 0
        if nf:              # r15 fwd: a meso station holds nf ot_meso_fifo W512 D4 slices beside its stages
            if horizontal:
                w = up(w + nf * MESO_UM2 / h, GX)
            else:
                h = up(h + nf * MESO_UM2 / w, GY)
        base = (cx - w / 2, cy - h / 2)
        tries = [(0, 0)]
        for k_ in range(1, 40):
            for s_ in (1, -1):
                tries.append((s_ * k_, 0) if horizontal else (0, s_ * k_))
        for k_ in range(1, 40):
            for s_ in (1, -1):
                tries.append((0, s_ * k_) if horizontal else (s_ * k_, 0))
        if m.get('network_probe'):
            # Pin bays can block both one-axis searches. Explore neighbouring
            # two-dimensional slots without shrinking a real macro footprint.
            tries += sorted(((i, j) for i in range(-12, 13) for j in range(-12, 13) if i and j),
                            key=lambda ij: abs(ij[0]) + abs(ij[1]))
        for (i, j) in tries:
            x = dn(base[0] + i * (w + 8.64), GX)
            y = dn(base[1] + j * (h + 8.64), GY)
            if free(x, y, w, h):
                break
        else:
            raise RuntimeError(f'no room for station of {chain} near ({cx:.0f}, {cy:.0f})')
        n_wp[0] += 1
        name = f'w{n_wp[0]}_{chain}'
        it = Inst(name, f'hfd_{kind}_{n_wp[0]}', x, y, w - SHAVE, h - SHAVE, kind='waypoint', region='channel')
        insts.append(it)
        blocked.append((x - 4.32, y - 4.32, x + w + 4.32, y + h + 4.32))
        faces[it.master] = dict(a=fa, b=fb)
        if nf:
            m.setdefault('meso', []).append(dict(inst=name, kind=kind, chain=chain, fifo_bits=fifo_bits, slices=nf,
                                                 clock=f'clk_{dom}', where='station'))
            m.setdefault('clocked', {})[name] = dom
        return it

    def chain(cid, cls, bits, src, dst, pts, path=None, fc=None, meso_end=False, dom='stream', local_src=False,
              first_um=None):
        """src/dst = (inst, port); pts = polyline through channels; stations every <= WAYPOINT_UM along it.  dst None:
        leave the chain open and return (last endpoint, bus ids).  r15 fwd: fc = (downstream bits, upstream bits) adds
        the forwarded clocks (one per 512 b slice and direction) to every segment; meso_end: the last station is a meso
        station (forwarded -> clk_<dom>) and the final segment into dst (a real macro / SM pin) carries data only;
        local_src: src (an SM pin) launches in its region clock, the first station (clocked) starts the forwarded clock."""
        nfc = fcbits(fc) if fwd_on else 0
        seq = []
        acc = 0.0
        WAYPOINT_UM = m['variant'].get('wp_um', WP_DEFAULT)     # r13 option: station spacing (registered segment)
        if first_um is not None:        # r17: the first station first_um from the source (inside its clock region)
            acc = WAYPOINT_UM - first_um
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            L = abs(bx - ax) + abs(by - ay)
            if L <= 0:
                continue
            t = WAYPOINT_UM - acc
            while t < L - 1e-6:
                f = t / L
                hor = abs(bx - ax) > abs(by - ay)
                seq.append((ax + (bx - ax) * f, ay + (by - ay) * f, hor, _dirface(bx, by, ax, ay), _dirface(ax, ay, bx, by)))
                t += WAYPOINT_UM
            acc = (acc + L) % WAYPOINT_UM
        prev = src
        ids = []
        for j, (x, y, hor, fa, fb) in enumerate(seq):
            last = meso_end and fwd_on and j == len(seq) - 1
            st = station(x, y, cid, bits, fa, fb, hor, kind='meso' if last else 'stn',
                         fifo_bits=(fc[0] if fc else bits) if last else 0, dom=dom)
            if not last and fwd_on:
                m.setdefault('fwd_dom', {})[st.name] = dom
            bid = f'{cid}_{j}'
            first_local = local_src and fwd_on and j == 0
            if first_local:
                m.setdefault('clocked', {})[st.name] = dom
            B.append((bid, cls, bits + (0 if first_local else nfc), [prev, (st.name, 'a')]))
            if nfc and not first_local:
                m.setdefault('fclk', {})[bid] = (bits, *fcsplit(fc))
            ids.append(bid)
            prev = (st.name, 'b')
        if dst is None:
            if path:
                P[path] += ids
            return prev, ids
        bid = f'{cid}_e'
        B.append((bid, cls, bits + (0 if (meso_end and seq) else nfc), [prev, dst]))
        if nfc and not (meso_end and seq):
            m.setdefault('fclk', {})[bid] = (bits, *fcsplit(fc))
        ids.append(bid)
        if path:
            P[path] += ids
        return bid
    return station, chain


def buses(m):
    """[(id, class, bits, [(inst, port)])] + named critical paths {path: [bus ids in order]}.  Long paths are chains of
    forwarded-link stations placed in the channels (a station every <= 4 x 430.56 um of route); each station is its own
    abstract with its ports on the faces that look along the route."""
    B, P = [], defaultdict(list)
    insts = m['insts']
    g = m['geo']
    hub = m['hub']
    faces = m['stn_faces']
    station, chain = _router(m, B, P)
    pf = m['variant'].get('port_fix')
    V = m['variant']
    fwd = V.get('fwd')
    wctl = W_CTL + W_DESC if V.get('sm_desc') else W_CTL           # r15: + the 58 b bulk-copy descriptor
    if V.get('ctl_leaf_w'):         # R25GQ 10-10 N4 (hgi-1010 + d): the SM control leaf from ot_hgi_sm_record is 112 b
        wctl = V['ctl_leaf_w']
    ctl_up = 4 if V.get('sm_desc') else 3                            # busy / arrive / released (+ d_ready)
    wres = W_RES
    if V.get('sm_native_abi'):
        # H-DIE 10-14 (SM ABI root handed to H-DIE): the control leaf is the record's per-SM ABI, read from source
        # (rtl/hbm_accel/generic/adapters/ot_hgi_sm_record.sv sm_cmd / sm_ret, CW = 106): 106 b down {start, op_rows 13,
        # op_c 16, op_g 8, op_gs, op_fmt 2, op_xb 7, d_valid, d_base 32, d_lines 24, release_in} + 4 b up {start_ready,
        # d_ready, arrive, fault} + the record's sm_cg_en (production OT_SMH_CG wake input of every SM) = 111 b (the
        # 112-b setting carried invented bits); the SM's single fault pin rides the control leaf to its only RTL
        # consumer, so the result leaf is rv / rrow 12 / rdata 256 = 269 b
        wctl, ctl_up, wres = 111, 4, W_RES - 1
    wline = W_LINE - 1 if V.get('sm_rtl_w') else W_LINE              # r15: no rsp_ready pin
    wreq = 44 if V.get('sm_rtl_w') else W_REQ

    def fcw(bid, base, *fc):
        """segment width with its forwarded clocks (r15 fwd); records (base, down fclk, up fclk) for the lint."""
        if not fwd:
            return base
        nd = math.ceil(fc[0] / 512) if fc[0] > 0 else 0
        nu = math.ceil(fc[1] / 512) if len(fc) > 1 and fc[1] > 0 else 0
        m.setdefault('fclk', {})[bid] = (base, nd, nu)
        return base + nd + nu

    def sm_face(it, port):
        f = SM_FACE[port]
        if it.orient == 'MX' and f in 'NS':
            f = 'S' if f == 'N' else 'N'
        return f
    yb0, yb1 = g['side_h'], g['H'] - g['side_h']
    ych = dict(S=yb0 + HCH / 2, N=yb1 - HCH / 2)          # hub-band edge channels
    lanes = m['variant'].get('lanes')
    # r13: dedicated lanes.  r12 stacked every die trunk within 140 um of the spine-channel centre line and of the
    # hub-edge channel centre line, so the 129-bundle x trunk and the link / control / expert trunks jogged around each
    # other (+200-600 um per 1.7 mm segment, one stage each).  Each trunk now owns a lane sized to its bundle count.
    sp_off, ed_off = {}, {}
    pos = 60.0
    for n_, nb in (('lk0', 64), ('lk1', 64), ('lk2', 64), ('xt', 129), ('ct', 23), ('ef', 8)) + \
            ((('qa', 38),) if m['variant'].get('attn_rtl') else ()) + \
            ((('iv', 33), ('rv', 33)) if m['variant'].get('fwd_hub') else ()) + \
            ((('lm', LM_BUNDLES(m)),) if m['variant'].get('ld_mem') else ()):
        sp_off[n_] = pos + nb * 1.2 / 2
        pos += nb * 1.2 + 40.0
    pos = 30.0
    for n_, nb in (('lk0', 64), ('lk1', 64), ('lk2', 64), ('ef', 8), ('ct', 23), ('xt', 129), ('rt', 135)) + \
            ((('lm', LM_BUNDLES(m)),) if m['variant'].get('ld_mem') else ()) + \
            (tuple((f'ks{g}', math.ceil(1102 / 16)) for g in range(8)) if m['variant'].get('attn_entry8') else ()):
        ed_off[n_] = pos + nb * 0.8 / 2
        pos += nb * 0.8 + 25.0
    spx = (hub['vm'].x, hub['vm'].x + hub['vm'].w)

    def xlane(half_, n_, default):
        if not lanes:
            return default
        return spx[0] - sp_off[n_] if half_ == 'W' else spx[1] + sp_off[n_]

    def ylane(side_, n_, default):
        if not lanes:
            return default
        return (yb0 + HCH - ed_off[n_]) if side_ == 'S' else (yb1 - HCH + ed_off[n_])
    smw = m['groups']['SW']['sms'][0].w + SHAVE

    def attn_rtl_nets(st, side, half, grid, corner, sc, vm):
        """r15 (H7): ot_attn_tile_registered_parent interface.  Packet = ld (1,038: ld_v / ld_mode / ld_bank / ld_grp /
        ld_w / ld_w2v, from the stream service) + query (580: iv / ibank / ib, from the VM).  The corner tile (inner
        column, hub-edge row) takes both; the packet goes down the inner column (cf -> ci) and along every row outward
        (rf -> ri), one registered tile hop each (the parent's launch register); results (ov / oy / oflt, 529) travel
        the row inward (o -> i) to the index quarter, then to the SU.  The forward ports (ci / cf / ri / rf / i) are the
        tile die wrapper's, not ot_attn_tile_registered_parent's (owner HBM-ATTN: expose `launch` and the merge input)."""
        # query: VM face -> spine-side channel lane -> equator channel -> the channel between the index quarter and the
        # tiles -> the corner tile's inner face
        xq = xlane(half, 'qa', vm.x - g['spch'] / 2 if half == 'W' else vm.x + vm.w + g['spch'] / 2)
        hy0_, hy1_ = g['hub_y']
        ye = (hy0_ + hy1_) / 2 + (-60.0 if side == 'S' else 60.0) + (-20.0 if half == 'W' else 20.0)
        ix = sc['index']
        xg = (ix.x - HCH / 2) if half == 'W' else (ix.x + ix.w + SHAVE + HCH / 2)
        root = _cxy(vm, 'W' if half == 'W' else 'E', 0.35 if side == 'S' else 0.65)
        tp = _cxy(corner, 'E' if half == 'W' else 'W', 0.5)
        pts = [root, (xq, root[1]), (xq, ye), (xg, ye), (xg, tp[1]), tp]
        qids = chain(f'qa_{st}', 'attn_query', ATTN_Q, (vm.name, f'q{st}'), None, pts, fc=(ATTN_Q,))
        prev, qids = qids
        B.append((f'qa_{st}_e', 'attn_query', fcw(f'qa_{st}_e', ATTN_Q, ATTN_Q), [prev, (corner.name, 'q')]))
        qids = qids + [f'qa_{st}_e']
        if fwd:
            m.setdefault('meso', []).append(dict(inst=corner.name, kind='attn_tile', chain=f'qa_{st}', fifo_bits=ATTN_Q,
                                                 slices=math.ceil(ATTN_Q / 512), clock='clk_stream',
                                                 where='inside the receiving tile wrapper'))
        rows = grid if side == 'S' else grid[::-1]          # from the hub-edge row inward
        inner = 3 if half == 'W' else 0
        col = [r_[inner] for r_ in rows]
        hops_c = []
        for a_, b_ in zip(col, col[1:]):
            B.append((f'tc_{a_.name}', 'attn_packet', ATTN_PKT, [(a_.name, 'cf'), (b_.name, 'ci')]))
            hops_c.append(f'tc_{a_.name}')
        far = []
        for r_, row in enumerate(rows):
            out = row[::-1] if half == 'W' else row          # inner -> outer
            hops_r = []
            for a_, b_ in zip(out, out[1:]):
                B.append((f'tp_{a_.name}', 'attn_packet', ATTN_PKT, [(a_.name, 'rf'), (b_.name, 'ri')]))
                hops_r.append(f'tp_{a_.name}')
            back = out[::-1]                                  # outer -> inner: results
            hops_o = []
            for a_, b_ in zip(back, back[1:]):
                B.append((f'ta_{a_.name}', 'attn_chain', ATTN_OUT, [(a_.name, 'o'), (b_.name, 'i')]))
                hops_o.append(f'ta_{a_.name}')
            ri = grid.index(row)
            B.append((f'tr_{st}{ri}', 'attn_root', ATTN_OUT, [(back[-1].name, 'o'), (sc['index'].name, f'a{ri}')]))
            far.append((r_, hops_r, hops_o, f'tr_{st}{ri}'))
        r_, hops_r, hops_o, tr = far[-1]                       # the row farthest from the corner
        P[f'attn_q_{st}'] = qids + hops_c + hops_r
        P[f'kv_{st}'] = P[f'kv_{st}'] + hops_c + hops_r
        B.append((f'ao_{st}', 'attn_out', 2 * ATTN_OUT, [(sc['index'].name, 't_su'), (hub[f'su_{st}'].name, 'a' if pf else f'a{st}')]))
        if not V.get('native_indexer'):
            B.append((f'iv_{st}', 'hub', 512, [(sc['index'].name, 't_vm'), (vm.name, f'i{st}')]))
        P[f'attn_out_{st}'] = hops_o + [tr, f'ao_{st}']

    for st, G in m['groups'].items():
        side, half = G['side'], G['half']
        svc, phy = G['svc'], G['phy']
        npins = len(real_ports()[phy.master]['dfi'])
        B.append((f'dfi_{st}', 'phy_dfi', npins, [(phy.name, 'dfi'), (svc.name, 'phy')]))
        sms = G['sms']
        r0 = next(s for s in sms if s.sm['row'] == 0)
        r1 = next(s for s in sms if s.sm['row'] == 1)
        sgn = 1 if side == 'S' else -1
        if side == 'S':
            y_mid = r0.y + r0.h + SHAVE + CH / 2
            y_top = r1.y + r1.h + SHAVE + CH / 2
            y_svc = svc.y + svc.h / 2
        else:
            y_mid = r0.y - CH / 2
            y_top = r1.y - CH / 2
            y_svc = svc.y + svc.h / 2
        # Preserve four logical branches while adapting anchor span to three
        # physical columns. These are tree anchors, never SM pin coordinates.
        anchor_pitch = ((g['grp_w'] - CH) / 4 if m.get('network_probe')
                        and V.get('sm_physical_grid') else smw + CH)
        cxs = [G['x'] + CH / 2 + c * anchor_pitch for c in range(5)]
        jx = G['x'] + g['grp_w'] + g['mid_ch'] / 2 if half == 'W' else G['x'] - g['mid_ch'] / 2
        jside = 4 if half == 'W' else 0                     # the column channel next to the mid channel
        by_rc = {(s.sm['row'], s.sm['col']): s for s in sms}
        my = sms[0].orient in ('MY', 'R180')               # r10: mirrored group: x face E, result face W
        xch = (lambda c_: c_ + 1) if my else (lambda c_: c_)          # channel of column c's x face
        rch = (lambda c_: c_) if my else (lambda c_: c_ + 1)          # channel of column c's result face
        vm_ = hub['vm']
        bias = m['variant'].get('root_bias')
        # (1) weight stream
        for s in sms:
            sid = s.name
            c = s.sm['col']
            if s.sm['row'] == 0:
                B.append((f'wl_{sid}', 'weight', wline, [(svc.name, f'l{sid}'), (sid, 'd')]))
                P[f'weight_{sid}'].append(f'wl_{sid}')
            elif m['variant'].get('row1_flip'):     # r12: row 1's d face looks at the hub-side row channel; the line
                #                                       climbs the column's result channel (the x leaves own the other)
                dx = s.x + s.w / 2
                wx = cxs[rch(c)]
                pts = [(wx, svc.y + (svc.h if side == 'S' else 0.0)), (wx, y_top), (dx, y_top)]
                chain(f'wl_{sid}', 'weight', wline, (svc.name, f'l{sid}'), (sid, 'd'), pts, path=f'weight_{sid}',
                      fc=(wline,), meso_end=True)
            else:
                dx = s.x + s.w / 2
                pts = [(cxs[c], svc.y + (svc.h if side == 'S' else 0.0)), (cxs[c], y_mid), (dx, y_mid)]
                chain(f'wl_{sid}', 'weight', wline, (svc.name, f'l{sid}'), (sid, 'd'), pts, path=f'weight_{sid}',
                      fc=(wline,), meso_end=True)
            if s.sm['row'] == 1 and V.get('rq_chain') and not V.get('row1_flip'):
                # r15: the row-1 request climbs its column channel beside the weight line (r1-r14b: one ~2.5 mm net)
                dx = s.x + s.w / 2
                qx = cxs[c] + 40.0
                pts = [(dx + 40.0, y_mid), (qx, y_mid), (qx, svc.y + (svc.h if side == 'S' else 0.0))]
                chain(f'rq_{sid}', 'weight_req', wreq, (sid, 'q'), (svc.name, f'q{sid}'), pts, path=f'request_{sid}',
                      fc=(wreq,), local_src=True)
            else:
                B.append((f'rq_{sid}', 'weight_req', wreq, [(sid, 'q'), (svc.name, f'q{sid}')]))
        # spine-side vertical channel (between the spine and the SU / SFU halves) and the group's centre column
        # channel (channel 2) that every tree enters by
        vm = hub['vm']
        xs_sp = hub['vm'].x - g['spch'] / 2 if half == 'W' else hub['vm'].x + hub['vm'].w + g['spch'] / 2
        xs_sp += (-60.0 if half == 'W' else 60.0) * (side == 'N')
        cc = cxs[2]
        # (2) activation multicast tree: VM -> spine-side channel -> hub edge channel -> channel 2 -> mid-row channel;
        #     a multicast station per SM column (channel c, west of column c) taps both SMs of the column; the tree
        #     splits at channel 2 into a west arm (1, 0) and an east arm (3)
        root = _cxy(vm, 'W' if half == 'W' else 'E', (0.1 if side == 'S' else 0.9) if bias else (0.3 if side == 'S' else 0.7))
        xin = m['variant'].get('x_chain')
        if xin:     # r10: enter at the column nearest the spine and chain outward (r8 entered at column 2: the E groups'
            #         column-0 leaf doubled back two SM pitches, the x-multicast floor)
            order = sorted(range(4), key=lambda c_: abs(cxs[xch(c_)] - g['cx']))
            out_f = 'W' if half == 'W' else 'E'
            in_f = 'E' if half == 'W' else 'W'
        else:
            order = [2]
        e0 = order[0]
        ccx = cxs[xch(e0)]
        xx_ = xlane(half, 'xt', xs_sp)
        yx_ = ylane(side, 'xt', ych[side] + 20.0 * sgn)
        pts = [root, (xx_, root[1]), (xx_, yx_), (ccx - 20.0, yx_), (ccx - 20.0, y_mid)]
        prev, trunk = chain(f'xt_{st}', 'x_trunk', W_X, (vm.name, f'x{st}'), None, pts, fc=(W_X,))
        ms = {}
        ms[e0] = station(ccx, y_mid, f'xm{st}{e0}', W_X, 'N' if side == 'S' else 'S', out_f if xin else 'W', False,
                         kind='mcast', extra=(up(2 * W_X * 0.048 * 1.1 + 24, GX), up(2 * W_X * 0.048 * 1.1 + 24, GY)),
                         fifo_bits=W_X if fwd else 0)
        faces[ms[e0].master].update(b2='E', t0='S' if side == 'S' else 'N', t1='N' if side == 'S' else 'S')
        B.append((f'xh_{st}_{e0}', 'x_trunk', fcw(f'xh_{st}_{e0}', W_X, W_X), [prev, (ms[e0].name, 'a')]))
        arm = {e0: [f'xh_{st}_{e0}']}
        if xin:
            steps = [(c_, f_, 'b') for f_, c_ in zip(order, order[1:])]
            fab = {c_: (in_f, out_f) for c_ in order}
        else:
            steps = ((1, 2, 'b'), (0, 1, 'b'), (3, 2, 'b2'))
            fab = {c_: ('E' if c_ < 2 else 'W', 'W' if c_ < 2 else 'E') for c_ in range(4)}
        for c, frm, port in steps:
            ms[c] = station(cxs[xch(c)], y_mid, f'xm{st}{c}', W_X, fab[c][0], fab[c][1], True,
                            kind='mcast', extra=(up(W_X * 0.048 * 1.1 + 24, GX), 0), fifo_bits=W_X if fwd else 0)
            faces[ms[c].master].update(t0='S' if side == 'S' else 'N', t1='N' if side == 'S' else 'S')
            bid = f'xh_{st}_{c}'
            B.append((bid, 'x_trunk', fcw(bid, W_X, W_X), [(ms[frm].name, port), (ms[c].name, 'a')]))
            arm[c] = arm[frm] + [bid]
        for c in range(4):
            for r_ in (0, 1):
                s = by_rc[(r_, c)]
                B.append((f'xl_{s.name}', 'x_leaf', W_X, [(ms[c].name, f't{r_}'), (s.name, 'x')]))
                P[f'xbcast_{s.name}'] = trunk + arm[c] + [f'xl_{s.name}']
        # (3) result gather tree: SM r face (E) -> gather station in channel c + 1 beside row 1; arms (0 -> 1) and
        #     (3 -> 2) join at the channel-2 station, which climbs channel 2 to the hub edge channel and the SU half
        su = hub[f'su_{st}']
        gy = (r1.y + r1.h * 0.3) if side == 'S' else (r1.y + r1.h * 0.7)
        gs = {}
        for c in (0, 3, 1, 2):
            nb = wres * 2 * {0: 1, 3: 1, 1: 2, 2: 4}[c]
            fa = {0: 'W', 1: 'W', 2: 'E', 3: 'E'}[c]
            gs[c] = station(cxs[rch(c)], gy, f'rg{st}{c}', nb, fa, 'N' if side == 'S' else 'S', False, kind='gath',
                            extra=(up((nb + 2 * wres) * 0.048 * 1.1 + 24, GX), up((nb + 2 * wres) * 0.048 * 1.1 + 24, GY)),
                            fifo_bits=wres * 4 if (fwd and c == 2) else 0)
            if fwd:     # r15: gather stations launch from their column half's local clock
                m.setdefault('clocked', {})[gs[c].name] = 'stream'
            faces[gs[c].master].update(t0='E' if my else 'W', t1='E' if my else 'W', a2='W')
            for r_ in (0, 1):
                s = by_rc[(r_, c)]
                B.append((f'rl_{s.name}', 'result_leaf', wres, [(s.name, 'r'), (gs[c].name, f't{r_}')]))
        B.append((f'rh_{st}_0', 'result_trunk', wres * 2, [(gs[0].name, 'b'), (gs[1].name, 'a')]))
        B.append((f'rh_{st}_3', 'result_trunk', wres * 2, [(gs[3].name, 'b'), (gs[2].name, 'a')]))
        B.append((f'rh_{st}_1', 'result_trunk', fcw(f'rh_{st}_1', wres * 4, wres * 4), [(gs[1].name, 'b'), (gs[2].name, 'a2')]))
        tgt = _cxy(su, 'W' if half == 'W' else 'E', 0.3 if side == 'S' else 0.7) if False else \
            _cxy(su, 'S' if side == 'S' else 'N', 0.3 + 0.4 * (half == 'E'))
        g2 = gs[2]
        yr_ = ylane(side, 'rt', ych[side] - 40.0 * sgn)
        pts = [(g2.x + g2.w / 2, g2.y + g2.h / 2), (cc + 40.0, g2.y + g2.h / 2), (cc + 40.0, yr_), (tgt[0], yr_), tgt]
        chain(f'rt_{st}', 'result_trunk', wres * 8, (g2.name, 'b'), (su.name, 'r' if pf else f'r{st}'), pts,
              fc=(wres * 8,))
        tr = [b[0] for b in B if b[0].startswith(f'rt_{st}_')]
        up_arm = {0: [f'rh_{st}_0', f'rh_{st}_1'], 1: [f'rh_{st}_1'], 3: [f'rh_{st}_3'], 2: []}
        for s in sms:
            P[f'result_{s.name}'] = [f'rl_{s.name}'] + up_arm[s.sm['col']] + tr
        # (4) control tree (start / op descriptors out, busy / arrive back; the barrier rides it): cmdproc ->
        #     spine-side channel -> hub edge channel -> a distribution station in channel 2 at the hub-side row
        #     channel (row 1) and one at the mid-row channel (row 0) -> 46-bit leaves to each SM's c face
        cp = hub['cmdproc']
        cpt = _cxy(cp, 'W' if half == 'W' else 'E', (0.1 if side == 'S' else 0.9) if bias else (0.3 if side == 'S' else 0.7))
        xcp = xlane(half, 'ct', xs_sp + (-100.0 if half == 'W' else 100.0))
        yh = ylane(side, 'ct', ych[side] + 60.0 * sgn)
        if m['variant'].get('ctl_chain'):
            # r12: with row 1 flipped both rows' c faces look at the mid-row channel: one control station per column in
            # that channel above the column, chained outward from the inner column (no star leaves across the group)
            corder = sorted(range(4), key=lambda c_: abs(by_rc[(0, c_)].x + by_rc[(0, c_)].w / 2 - g['cx']))
            cin = cxs[4] if half == 'W' else cxs[0]
            pts = [cpt, (xcp, cpt[1]), (xcp, yh), (cin + (-60.0 if half == 'W' else 60.0), yh),
                   (cin + (-60.0 if half == 'W' else 60.0), y_mid)]
            prev, ctr = chain(f'ct_{st}', 'control', 8 * wctl, (cp.name, f'c{st}'), None, pts,
                              fc=(8 * (wctl - ctl_up), 8 * ctl_up))
            ofc, ifc = ('W', 'E') if half == 'W' else ('E', 'W')
            t0f, t1f = ('S', 'N') if side == 'S' else ('N', 'S')
            arm_c, last = [], prev
            for j, c_ in enumerate(corder):
                s0 = by_rc[(0, c_)]
                d = station(s0.x + s0.w / 2, y_mid, f'cd{st}{c_}', 8 * wctl - j * 2 * wctl, ifc, ofc, True, kind='cdist',
                            extra=(0, up(2 * wctl * 0.048 * 2.2 + 24, GY)),
                            fifo_bits=(8 * wctl - j * 2 * wctl) if fwd else 0)
                faces[d.master].update(t0=t0f, t1=t1f)
                bid = f'cd_{st}_{c_}'
                nw_ = 8 * wctl - j * 2 * wctl
                B.append((bid, 'control', fcw(bid, nw_, nw_ // wctl * (wctl - ctl_up), nw_ // wctl * ctl_up),
                          [last, (d.name, 'a')]))
                arm_c = arm_c + [bid]
                last = (d.name, 'b')
                for r_ in (0, 1):
                    sm_ = by_rc[(r_, c_)]
                    B.append((f'cl_{sm_.name}', 'control_leaf', wctl, [(d.name, f't{r_}'), (sm_.name, 'c')]))
                    P[f'control_{sm_.name}'] = ctr + list(arm_c) + [f'cl_{sm_.name}']
        else:
            pts = [cpt, (xcp, cpt[1]), (xcp, yh), (cc + 60.0, yh), (cc + 60.0, y_top)]
            prev, ctr = chain(f'ct_{st}', 'control', 8 * wctl, (cp.name, f'c{st}'), None, pts,
                              fc=(8 * (wctl - ctl_up), 8 * ctl_up))
        if not m['variant'].get('ctl_chain'):
            d1 = station(cc + 60.0, y_top, f'cd{st}1', 8 * wctl, 'N' if side == 'S' else 'S', 'S' if side == 'S' else 'N',
                         False, kind='cdist', extra=(up(8 * wctl * 0.048 * 2.2 + 24, GX), up(4 * wctl * 0.048 * 2.2 + 24, GY)),
                         fifo_bits=8 * wctl if fwd else 0)
            B.append((f'cd_{st}_1', 'control', fcw(f'cd_{st}_1', 8 * wctl, 8 * (wctl - ctl_up), 8 * ctl_up), [prev, (d1.name, 'a')]))
            d0 = station(cc + 60.0, y_mid, f'cd{st}0', 4 * wctl, 'N' if side == 'S' else 'S', 'S' if side == 'S' else 'N',
                         False, kind='cdist', extra=(up(4 * wctl * 0.048 * 2.2 + 24, GX), up(4 * wctl * 0.048 * 2.2 + 24, GY)),
                         fifo_bits=4 * wctl if fwd else 0)
            B.append((f'cd_{st}_0', 'control', fcw(f'cd_{st}_0', 4 * wctl, 4 * (wctl - ctl_up), 4 * ctl_up), [(d1.name, 'b'), (d0.name, 'a')]))
            if fwd:     # the upstream busy / arrive / released leave the group forwarded: a meso FIFO in the cmdproc
                m.setdefault('meso', []).append(dict(inst=cp.name, kind='hub', chain=f'ct_{st} (upstream)',
                                                     fifo_bits=8 * ctl_up, slices=1, clock='clk_stream',
                                                     where='inside the receiving hub block'))
            for s in sms:
                d = d1 if s.sm['row'] == 1 else d0
                B.append((f'cl_{s.name}', 'control_leaf', wctl, [(d.name, f't{s.sm["col"]}'), (s.name, 'c')]))
                P[f'control_{s.name}'] = ctr + [f'cd_{st}_1'] + ([f'cd_{st}_0'] if s.sm['row'] == 0 else []) + [f'cl_{s.name}']
        # (5) expert-fetch descriptor: router -> spine-side channel -> hub edge channel -> channel 2 -> svc N face
        rt = hub['router']
        p0 = _cxy(rt, 'W' if half == 'W' else 'E', 0.5)
        xr = xlane(half, 'ef', xs_sp + (-140.0 if half == 'W' else 140.0))
        sn = _cxy(svc, 'N' if side == 'S' else 'S', (cc + 80.0 - svc.x) / svc.w)
        ye_ = ylane(side, 'ef', ych[side] + 100.0 * sgn)
        pts = [p0, (xr, p0[1]), (xr, ye_), (cc + 80.0, ye_), sn]
        if 'cp' not in (m['variant'].get('hgi_dispatch') or []):   # HGI (review 10:45): expert weights stream by id
            chain(f'ef_{st}', 'expert_req', 128, (rt.name, f'e{st}'), (svc.name, 'e'), pts, path=f'expert_req_{st}',
                  fc=(128,))
        lmem = m['variant'].get('ld_mem')
        if lmem:
            # r25m (MTP-DIE, RQ-ING-4): the loader's memory side (memory AXI m_* + request / response req_* / rsp_*,
            # tied to a cfg shift chain in the r25 die view: NO physical loader -> HBM path) wired to every stack's
            # stream service: request (loader -> svc) and response (svc -> loader) forwarded chains on the expert-fetch
            # route (loader W/E face -> spine-side channel -> hub edge channel -> svc inner face), stations every
            # <= 430.56 um (< the 504 um SS reach), a pin flop at both ends (the loader / svc pin banks)
            ld_ = hub['loader']
            q0 = _cxy(ld_, 'W' if half == 'W' else 'E', 0.35)
            xl_ = xlane(half, 'lm', xs_sp + (-200.0 if half == 'W' else 200.0))
            sn2 = _cxy(svc, 'N' if side == 'S' else 'S', (cc + 140.0 - svc.x) / svc.w)
            yl_ = ylane(side, 'lm', ych[side] + 130.0 * sgn)
            pts2 = [q0, (xl_, q0[1]), (xl_, yl_), (cc + 140.0, yl_), sn2]
            chain(f'lq_{st}', 'loader_mem', lmem[0], (ld_.name, f'q{st}'), (svc.name, 'lq'), pts2,
                  path=f'loader_mem_{st}', fc=(lmem[0],))
            q1 = _cxy(ld_, 'W' if half == 'W' else 'E', 0.65)
            xr2 = xl_ + (-60.0 if half == 'W' else 60.0)
            sr2 = _cxy(svc, 'N' if side == 'S' else 'S', (cc + LR_DX - svc.x) / svc.w)
            yr2 = yl_ + 60.0 * sgn
            pts3 = [sr2, (cc + LR_DX, yr2), (xr2, yr2), (xr2, q1[1]), q1]
            chain(f'lr_{st}', 'loader_mem', lmem[1], (svc.name, 'lr'), (ld_.name, f'r{st}'), pts3,
                  path=f'loader_rsp_{st}', fc=(lmem[1],))
            dbw_ = m['variant'].get('dbk_wd')
            if dbw_:
                # contract v12 (MTP swap-out, zero-new-wire option): the per-cluster DMA BACK writes its own stack's
                # stream service -- wd (8 x 289 b) down, credits + acks (8 + 4) back -- on the loader-memory route;
                # the R25GQ transplant moves the loader ends to hb_dbk_<q> (ECO pins wd / wdc on svc band 3)
                chain(f'lw_{st}', 'loader_mem', dbw_[0], (ld_.name, f'w{st}'), (svc.name, 'wd'),
                      [q0, (xl_ + (30.0 if half == 'W' else -30.0), q0[1]), (xl_ + (30.0 if half == 'W' else -30.0), yl_ - 30.0 * sgn),
                       (cc + 110.0, yl_ - 30.0 * sgn), _cxy(svc, 'N' if side == 'S' else 'S', (cc + 110.0 - svc.x) / svc.w)],
                      fc=(dbw_[0],))
                chain(f'lx_{st}', 'loader_mem', dbw_[1], (svc.name, 'wdc'), (ld_.name, f'x{st}'),
                      [_cxy(svc, 'N' if side == 'S' else 'S', (cc + 125.0 - svc.x) / svc.w), (cc + 125.0, yl_ - 15.0 * sgn),
                       (xl_ + (15.0 if half == 'W' else -15.0), yl_ - 15.0 * sgn), (xl_ + (15.0 if half == 'W' else -15.0), q1[1]), q1],
                      fc=(dbw_[1],))
        # (6) KV rows -> the stack's scan quadrant (attention tiles nearest the stack) and index keys -> its index
        #     quarter: svc outer end -> outer column channel -> hub edge channel -> quadrant face
        sc = m['scan'][st]
        rowt = sc['tiles'][0] if side == 'S' else sc['tiles'][-1]
        attn_rtl = V.get('attn_rtl')
        # r15 attn_rtl: the packet (KV 1,038 + query 580) enters the hub-edge tile of the INNER column (beside the index
        # quarter, nearest the VM); r1-r14b fed KV into the outer corner
        corner = (rowt[-1] if half == 'W' else rowt[0]) if attn_rtl else (rowt[0] if half == 'W' else rowt[-1])
        for name, tgt_inst, port, off in (('kv', corner, 'k' if pf else f'k{st}', -50.0),
                                          ('ik', sc['index'], 'k' if pf else f'k{st}', 50.0)):
            if V.get('native_indexer') and name == 'ik':
                continue
            tp = _cxy(tgt_inst, 'S' if side == 'S' else 'N', 0.5)
            so = _cxy(svc, 'W' if half == 'W' else 'E', 0.3 if name == 'kv' else 0.7)
            yy_ = ylane(side, 'lk0' if name == 'kv' else 'lk1', ych[side] + 40.0 * sgn * (1 if name == 'kv' else -1))
            eo = min(range(5), key=lambda c_: abs(cxs[c_] - tp[0]) + abs(cxs[c_] - so[0]))
            sn = _cxy(svc, 'N' if side == 'S' else 'S', (cxs[eo] + off - svc.x) / svc.w)
            pts = [sn, (cxs[eo] + off, yy_), (tp[0], yy_), tp]
            kb = ATTN_LD if (attn_rtl and name == 'kv') else 1024
            chain(f'{name}_{st}', 'kv_rows', kb, (svc.name, name), (tgt_inst.name, port), pts, path=f'{name}_{st}',
                  fc=(kb,))
            if fwd:     # forwarded words land in the scan quadrant's clock region: a meso FIFO in the receiving block
                m.setdefault('meso', []).append(dict(inst=tgt_inst.name, kind=tgt_inst.kind, chain=f'{name}_{st}',
                                                     fifo_bits=kb, slices=math.ceil(kb / 512), clock='clk_stream',
                                                     where='inside the receiving hub block'))
        if V.get('attn_entry8'):
            # hbm-forks RQ-HF-4 (review-0400 / 0412): 8 KV entry points a stack.  Pair g of the scan quadrant (row r,
            # inner / outer pair of the row, inner -> outer) takes the svc PS row port ks<g> on its entry tile's `ks`
            # pin (half_lo); the partner tile gets the rows on the existing rf -> ri hop (strap ldk: entry 1, partner 0,
            # a by_design die tie).  Route: svc inner face at the ks<g> pins -> the outer column channel -> the hub edge
            # channel (one lane each, 12 um apart) -> the entry tile's S / N face; stations every <= WAYPOINT_UM.
            sps_ = json.loads((ROOT / V['split_x_masters']).read_text())
            par = sps_['parents'][svc.master]
            rows_ = sc['tiles'] if side == 'S' else sc['tiles'][::-1]
            for gk in range(8):
                r_, pr = divmod(gk, 2)
                out_ = rows_[r_][::-1] if half == 'W' else rows_[r_]
                ent = out_[2 * pr]
                band = next(b_ for b_ in par['bands'] if f'ks{gk}' in par['port_map'][b_])
                prec = json.loads((ROOT / V['split_x_masters']).parent.joinpath(band, 'ports.json').read_text())
                pins_ = prec['ports'][f'ks{gk}']['pins']
                xg = sps_['bands'][band]['x0_um'] + (pins_[0][2] + pins_[-1][4]) / 2
                if svc.orient in ('MY', 'R180'):
                    xg = svc.w - xg
                sn = _cxy(svc, 'N' if side == 'S' else 'S', xg / svc.w)
                tp = _cxy(ent, 'S' if side == 'S' else 'N', 0.65)
                eo = min(range(5), key=lambda c_: abs(cxs[c_] - tp[0]) + abs(cxs[c_] - sn[0]))
                xl_ = cxs[eo] - 40.0 + 12.0 * gk
                yy_ = ylane(side, f'ks{gk}', ych[side] + (20.0 + 6.0 * gk) * sgn)
                pts = [sn, (sn[0], yy_), (xl_, yy_), (xl_, tp[1] - 30.0 * sgn), (tp[0], tp[1] - 30.0 * sgn), tp]
                chain(f'ks{gk}_{st}', 'kv_rows', 1099, (svc.name, f'ks{gk}'), (ent.name, 'ks'), pts, path=f'ks{gk}_{st}',
                      fc=(1099,))
                if fwd:
                    m.setdefault('meso', []).append(dict(inst=ent.name, kind=ent.kind, chain=f'ks{gk}_{st}', fifo_bits=1099,
                                                         slices=3, clock='clk_stream', where='inside the entry tile'))
                m.setdefault('straps', []).append(dict(inst=ent.name, port='ldk', value=1, cls='by_design',
                                                       reason='RQ-HF-4 entry tile: ld from its own ks port'))
                m['straps'].append(dict(inst=out_[2 * pr + 1].name, port='ldk', value=0, cls='by_design',
                                        reason='RQ-HF-4 partner tile: ld from the forward hop'))
        # scan quadrant internals: tile row chains (outer -> inner), row end -> index quarter -> SU; KV down the
        # columns; index quarter -> VM (local top-k for the merge)
        grid = sc['tiles']
        actual_attn = 'attn_tile_w_um' in m['variant'] and not attn_rtl
        if attn_rtl:
            attn_rtl_nets(st, side, half, grid, corner, sc, vm)
            continue
        if actual_attn:
            # 576 operand bits + 18 controls. LD data remains the 1024-bit
            # service path. These are reservations, not a new RTL broadcaster.
            B.append((f'qi_{st}', 'attn_operand', 594,
                      [(vm.name, f'q{st}'), (rowt[0 if half == 'W' else -1].name, 'q')]))
        for r in range(4):
            row = grid[r] if half == 'W' else grid[r][::-1]
            for a_, b_ in zip(row, row[1:]):
                B.append((f'ta_{a_.name}', 'attn_chain', 529 if actual_attn else 512, [(a_.name, 'o'), (b_.name, 'i')]))
                if actual_attn:
                    B.append((f'ti_{a_.name}', 'attn_input', 1618, [(a_.name, 'iu'), (b_.name, 'id')]))
            B.append((f'tr_{st}{r}', 'attn_root', 529 if actual_attn else 512, [(row[-1].name, 'o'), (sc['index'].name, f'a{r}')]))
        for c in range(4):
            for r in range(3):
                lo, hi_ = (grid[r][c], grid[r + 1][c]) if side == 'S' else (grid[3 - r][c], grid[2 - r][c])
                B.append((f'tk_{st}{r}{c}', 'attn_kv', 1618 if actual_attn else 1024, [(lo.name, 'ku'), (hi_.name, 'kd')]))
        B.append((f'ao_{st}', 'attn_out', 1058 if actual_attn else 1024, [(sc['index'].name, 't_su'), (hub[f'su_{st}'].name, 'a' if pf else f'a{st}')]))
        if not V.get('native_indexer'):
            B.append((f'iv_{st}', 'hub', 512, [(sc['index'].name, 't_vm'), (vm.name, f'i{st}')]))
        P[f'attn_out_{st}'] = [f'tr_{st}0', f'ao_{st}']
    # ---- hub internal (adjacent slabs across one channel, or vertical in the spine column): direct nets; their
    #      stage count is read from the routed length
    crtl = V.get('coll_rtl')
    if crtl:    # r15 (H9): ot_hbm_accel_tu_endpoint rank[7:0] / pf[15:0] / go in, fault / stat_credit_stall[31:0] out
        hl_ = [('cmdproc', 'coll', 8 + 16 + 1), ('coll', 'cmdproc', 1 + 32)]
    else:
        hl_ = [('cmdproc', 'coll', 64)]
    hgi_q = 'quant' in (V.get('hgi_dispatch') or [])      # hgi-takeover: the hgi quant unit reads / writes VM by packets
    hgi_cp_ = 'cp' in (V.get('hgi_dispatch') or [])    # hgi-takeover: the loader <-> CP link replaces the program-store bus
    hl_ += ([] if hgi_cp_ else [('loader', 'cmdproc', 341), ('router', 'cmdproc', 64)]) + [('barrier', 'cmdproc', 64),
            ('vm', 'router', 512)] + ([] if hgi_q else [('vm', 'quant', 1024)]) + ([] if crtl else [('vm', 'coll', 512)])
    if V.get('hub_io'):     # r15 (H10): the barrier's arrive input (SM arrives ride the control tree to the cmdproc)
        hl_ += [('cmdproc', 'barrier', 64)]
    if 'mtp' in hub:        # r25m (MTP-DIE): ot_dshbm_dspark_top die interfaces (port widths from the RTL)
        if V.get('mtp_master') == 'hgi_native':
            # mtp-lead 2026-10-09 (generic die): hgi_mtp_native groups; cmdproc side = MX1 t_mtp / f_mtp
            from hbm_mtp_native_contract import generic_model
            gm_ = generic_model(ROOT)
            for name, group in gm_['groups'].items():
                peer_ = name[2:]
                hl_.append((peer_, 'mtp', group['bits']) if name.startswith('f_') else ('mtp', peer_, group['bits']))
        elif V.get('mtp_x_stop') and not V.get('native_mtp_wb'):
            # hgi-takeover: the closed hfd_mtp_x_stop view's real ports, grouped by peer (stop_model)
            from hbm_mtp_native_contract import stop_model
            for name, group in stop_model(ROOT)['groups'].items():
                peer_ = name[2:]
                hl_.append((peer_, 'mtp', group['bits']) if name.startswith('f_') else ('mtp', peer_, group['bits']))
        elif V.get('native_mtp_wb'):
            from hbm_mtp_native_contract import model, stop_model
            native_contract = stop_model if V.get('native_mtp_stop') else model
            contract = native_contract(ROOT)
            for name, group in contract['groups'].items():
                peer_ = name[2:]
                hl_.append((peer_, 'mtp', group['bits']) if name.startswith('f_')
                           else ('mtp', peer_, group['bits']))
        else:
            hl_ += list(MTP_HUB_LINKS)
    for q in ('SW', 'SE', 'NW', 'NE'):
        # coll_rtl: SU quarter -> endpoint inject data (inj_data 2 x 512, muxed by the fan-in inside the block);
        # endpoint -> SU quarter: delivery lane del_flit 545 + del_valid + inj_idx 2 x 16 + inj_rd 2 = 580
        # (del_obase, R25GQ 10-10: + the 40-b delivery output base hgi_del_obase, functional with PIPE = 620)
        hl_ += [('vm', f'su_{q}', 2048), (f'su_{q}', 'vm', 2048), (f'su_{q}', f'sfu_{q}', 1024), (f'sfu_{q}', f'hc_{q}', 1024),
                (f'su_{q}', 'coll', 1024), ('coll', f'su_{q}', (620 if V.get('del_obase') else 580) if crtl else 1024)] + ([] if hgi_q else [('quant', f'su_{q}', 512)]) + [
                ('cmdproc', f'su_{q}', 64)] + ([] if V.get('router_exact') and q != 'SW' else
                                               [(f'su_{q}', 'router', 2 if V.get('router_exact') else 256)])
        # router_exact (hgi-takeover 2026-10-09, die gap 1e): the router RTL takes only in_valid / in_last from the SU (SW);
        # the other quarters' 256 b and SW's 254 spare bits carried nothing (wrapper ledger: dropped die inputs)
        if V.get('hub_io'):     # r15 (H10): HC (mHC / Sinkhorn) and SFU results return to the SU
            hl_ += [(f'hc_{q}', f'sfu_{q}', 1024), (f'sfu_{q}', f'su_{q}', 1024)]
    hl_ += [('su_SW', 'su_SE', 1024), ('su_SE', 'su_SW', 1024), ('su_SW', 'su_NW', 1024), ('su_NW', 'su_SW', 1024),
            ('su_SE', 'su_NE', 1024), ('su_NE', 'su_SE', 1024), ('su_NW', 'su_NE', 1024), ('su_NE', 'su_NW', 1024)]
    def role(me, peer):
        """r10: port names of a shared quarter master name the peer's role, not its quadrant (r1-r8 named t_sfu_SW etc.,
        so only the SW copy's ports existed in the master: 3 of 4 copies' quadrant-named nets had no pin at that end)."""
        if not pf or '_' not in me:
            return peer
        if '_' not in peer:
            return peer
        pt, pq = peer.split('_')
        mq = me.split('_')[1]
        if pq == mq:
            return pt
        return pt + ('_ew' if pq[0] == mq[0] else '_ns')
    for a_, b_, bits in hl_:
        B.append((f'hb_{a_}_{b_}', 'hub', bits, [(hub[a_].name, f't_{role(a_, b_)}'), (hub[b_].name, f'f_{role(b_, a_)}')]))
        P[f'hub_{a_}_{b_}'] = [f'hb_{a_}_{b_}']
    if V.get('hgi_dispatch'):
        # hgi-takeover 2026-10-09: normative ot_hgi_seq v1.0 record dispatch to the generic units (opt-in, buses only)
        from hgi_die_dispatch import install as install_hgi_dispatch
        install_hgi_dispatch(m, B, P, V['hgi_dispatch'])
    if V.get('mtp_master') == 'hgi_native' and 'mtp' in hub:
        # mtp-lead 2026-10-09: the ARGMAX unit (unit 7) is the slot's second instance hb_mtp_am, master ot_hgi_argmax18_m
        # (closed view physical/hbm_accel_die_views/argmax_hgi, 604 pins).  Its die buses use the view's own ports:
        # the logit STREAM from the LM head (su_red) in_* 523, and the result O {value, id, nan, fault, range fault} 54
        # to VM (HGI 6.6: ARGMAX O in VM; COLL.ARGMAX_MERGE reads it there).  The record dispatch (hgi_argmax_cmd 683 /
        # ret 3) lands on hb_mtp_am, whose bare view has no record decode (cfg_rank 7 / cfg_imm_a 18 + in_v gating):
        # the dispatch adapter is an hgi-takeover obligation (die check lists it).  The merged id reaches MX1 f_am
        # from the CP sequencer's CTL.AMAX step (reads VM A[0] per verify row, cp_vocab check).
        am_ = hub.get('mtp_am', hub['mtp'])
        for port_, bits_ in ARGMAX_HGI_IN:
            B.append((f'hb_su_red_am_{port_}', 'hub', bits_, [(hub['su_red'].name, f't_am_{port_}'), (am_.name, port_)]))
            P[f'hub_su_red_am_{port_}'] = [f'hb_su_red_am_{port_}']
        for port_, bits_ in ARGMAX_HGI_OUT:
            B.append((f'hb_am_vm_{port_}', 'hub', bits_, [(am_.name, port_), (hub['vm'].name, f'f_am_{port_}')]))
            P[f'hub_am_vm_{port_}'] = [f'hb_am_vm_{port_}']
        ob_ = json.loads((ROOT / 'physical/hbm_cp_mtp_native/collar_mx1/endpoint_obligations.json').read_text())
        bound_ = {'t_mtp', 'f_mtp'}
        m['mtp_generic'] = dict(master='hgi_mtp_native', cp_band='hfd_cmdproc_s_mtp_native_mx1',
            slot_content={k_: (hub[k_].master, hub[k_].w, hub[k_].h, round(hub[k_].x, 3), round(hub[k_].y, 3))
                          for k_ in ('mtp', 'mtp_am') if k_ in hub},
            buses=[b_[0] for b_ in B if b_[0].startswith(('hb_mtp_', 'hb_cmdproc_mtp', 'hb_router_mtp', 'hb_coll_mtp',
                                                            'hb_su_red_am_', 'hb_am_vm_', 'hgi_argmax_'))],
            unbound={k: v for k, v in ob_['required_endpoints'].items() if k not in bound_},
            unbound_owner=dict(f_am='ot_hgi_seq CTL.AMAX (VM A[0] per verify row, cp_vocab-checked) -> MX1 f_am',
                               backend='generic backend translator: t_backend eng_cmd 201 -> ot_hgi_seq doorbell '
                                       '{token, pos, job, gen, entry verify/draft, ncol} + per-slot TOKEN DYN; '
                                       'CTL.END/AMAX completions -> f_backend (job/gen/sequence echo, drained)',
                               host='host doorbell / emit path (f_host, t_host, t_emit_host, f_emit_host, t_drained, t_abort)',
                               provider='prompt / forced token reads and spec-state requests (f_provider, t_provider, t_emit)'),
            default_on=_mtp_generic_closed())
        m['notes'].append('mtp_master hgi_native: hgi_mtp_native + MX1 CP south band; MX1 host/provider/backend '
                          'endpoints unbound (m["mtp_generic"]["unbound"]).')
    # ---- collective -> SerDes: 8 TU ports x 546 b each direction striped over the 9 macros (S centre 5, N centre 4):
    #      spine-side channel -> hub edge channel -> the channel east of the macro -> its E-face pins
    coll = hub['coll']
    MG_ = m['variant'].get('serdes_mg', 103.68)
    tot = TU_PORTS * TU_FLIT * 2
    per = math.ceil(tot / len(m['links']))
    lrtl = V.get('link_rtl')
    if lrtl:    # r15 (H6): each way 8 TU ports x (545 flit + valid + credit) striped over the macros, tx / rx halves
        per = 2 * math.ceil(TU_PORTS * (545 + 2) / len(m['links']))
    lane_j = defaultdict(int)
    for i, lk in enumerate(m['links']):
        side = lk.name[3]
        j = int(lk.name[4:])
        east = lk.x + lk.w / 2 > coll.x + coll.w / 2
        p0 = _cxy(coll, 'E' if east else 'W', 0.15 + 0.14 * j + (0.0 if side == 'S' else 0.07))
        xsp = (coll.x + coll.w + g['spch'] / 2 + 60.0 * j - 120.0) if east else (coll.x - g['spch'] / 2 - 60.0 * j + 120.0)
        yh = ych[side] + (-40.0 * j - 20.0) * (1 if side == 'S' else -1)
        if lanes:
            hk = (side, east)
            ln_ = f'lk{lane_j[hk]}'
            lane_j[hk] += 1
            xsp = xlane('E' if east else 'W', ln_, xsp)
            yh = ylane(side, ln_, yh)
        xg = lk.x + lk.w + MG_ / 2
        ym = lk.y + lk.h / 2
        pts = [p0, (xsp, p0[1]), (xsp, yh), (xg, yh), (xg, ym), (lk.x + lk.w, ym)]
        if lrtl:
            chain(f'lk_{lk.name}', 'link', per, (coll.name, f'l{lk.name}'), (lk.name, 'iox'), pts, path=f'link_{lk.name}',
                  fc=(per // 2, per // 2), meso_end=True, dom='link')
            if fwd:     # the rx half arrives forwarded at the endpoint: a meso FIFO into its pclk domain
                m.setdefault('meso', []).append(dict(inst=coll.name, kind='spine', chain=f'lk_{lk.name} (rx)',
                                                     fifo_bits=per // 2, slices=math.ceil(per / 2 / 512),
                                                     clock='clk_link', where='inside the receiving hub block'))
        else:
            chain(f'lk_{lk.name}', 'link', min(per, 1024), (coll.name, f'l{lk.name}'), (lk.name, 'io'), pts,
                  path=f'link_{lk.name}')
    hl = m['host']
    ld = hub['loader']
    p0 = _cxy(ld, 'E', 0.5)
    xs_ = hl.x - SCH / 2
    pts = [p0, (p0[0] + 200.0, p0[1]), (p0[0] + 200.0, ych['S'] + 60.0), (xs_, ych['S'] + 60.0), (xs_, hl.y + hl.h / 2),
           (hl.x, hl.y + hl.h / 2)]
    if lrtl:    # r15 (H6): host link tx[255:0] + rx[255:0] (r1-r14b: tx only, the loader had no input)
        # host_h (R25GQ, [fp] 2026-10-10): (tx, rx) sized exactly from ot_hfd_loader_hgi's host-facing ports (HOST_H_HGI)
        htx_, hrx_ = V.get('host_h', (256, 256))
        chain('host', 'host', htx_ + hrx_, (ld.name, 'h'), (hl.name, 'iox'), pts, path='host', fc=(htx_, hrx_),
              meso_end=True, dom='link')
        if fwd:
            m.setdefault('meso', []).append(dict(inst=ld.name, kind='spine', chain='host (rx)', fifo_bits=hrx_,
                                                 slices=math.ceil(hrx_ / 512),
                                                 clock='clk_link', where='inside the receiving hub block'))
    else:
        chain('host', 'host', 512, (ld.name, 'h'), (hl.name, 'io'), pts, path='host')
    if V.get('hub_stage_all'):          # r17: every attention root bus is a staged path
        for b_ in B:
            if b_[1] == 'attn_root' and not any(b_[0] in ids for ids in P.values()):
                P[f'attn_root_{b_[0][3:]}'] = [b_[0]]
    if V.get('fwd_hub'):                # r17: forwarded-clock chains for the two region crossings > 150 ps
        vm = hub['vm']
        hy0_, hy1_ = g['hub_y']
        drop = set()
        for st in (() if V.get('native_indexer') else ('SW', 'SE', 'NW', 'NE')):
            sc = m['scan'][st]
            ix = sc['index']
            side, half = st[0], st[1]
            ye = (hy0_ + hy1_) / 2 + (-130.0 if side == 'S' else 130.0) + (-20.0 if half == 'W' else 20.0)
            xi = xlane(half, 'iv', vm.x - g['spch'] / 2 if half == 'W' else vm.x + vm.w + g['spch'] / 2)
            xc = (ix.x + ix.w + SHAVE + HCH / 2) if half == 'W' else (ix.x - HCH / 2)
            iy = (ix.y + ix.h - 200.0) if side == 'S' else (ix.y + 200.0)
            src = (ix.x + ix.w, iy) if half == 'W' else (ix.x, iy)
            dst = _cxy(vm, 'W' if half == 'W' else 'E', 0.15 if side == 'S' else 0.25)
            pts = [src, (xc, iy), (xc, ye), (xi, ye), (xi, dst[1]), dst]
            drop.add(f'iv_{st}')
            n0 = len(insts)
            chain(f'iv_{st}', 'hub', 512, (ix.name, 't_vm'), (vm.name, f'i{st}'), pts, path=f'index_vm_{st}', fc=(512,),
                  meso_end=True, local_src=True, first_um=HCH / 2 + 60.0)   # (r19b tried 60 um: it renumbers the r33-r37 station roles already in the closure loop)
            w0 = insts[n0]          # the clocked first station: a sink of the index quarter's region
            m.setdefault('region_extra', []).append(dict(name=f'HUB-Q{st}', clock='clk_stream',
                                                         rect=[round(w0.x, 1), round(w0.y, 1), round(w0.x + w0.w, 1), round(w0.y + w0.h, 1)]))
        rt = hub['router']
        xr = xlane('W', 'rv', vm.x - g['spch'] / 2)
        a0 = _cxy(vm, 'W', 0.05)
        b0 = _cxy(rt, 'W', 0.5)
        drop.add('hb_vm_router')
        P.pop('hub_vm_router', None)
        n0 = len(insts)
        chain('vr', 'hub', 512, (vm.name, 't_router'), (rt.name, 'f_vm'), [a0, (xr, a0[1]), (xr, b0[1]), b0],
              path='hub_vm_router', fc=(512,), meso_end=True, local_src=True)
        w1 = insts[-1]              # the meso station into the router: a sink of the router's region
        assert len(insts) > n0 and w1.master.startswith('hfd_meso')
        m.setdefault('region_extra', []).append(dict(name='HUB-SP', clock='clk_stream',
                                                     rect=[round(w1.x, 1), round(w1.y, 1), round(w1.x + w1.w, 1), round(w1.y + w1.h, 1)]))
        B[:] = [b_ for b_ in B if b_[0] not in drop]
    if V.get('iv_pin_stn') and V.get('fwd_hub'):
        # r21 (closure loop hbm_idxq_b5_48529891f_r19b: FF hold -177 on t_vm, the hold ECO could not move it): index b5
        # t_vm had 247.7 ps internal output budget over its 313 um first segment, no room for the hold delay the band's
        # early output leaf (622 ps vs 856 mean FF) needs.  A station abutting the t_vm pin (last <= ~60 um) gives the
        # output ~500 ps internal.  Appended after every other station (no station role renumbered); +1 hop per index
        # scan on the index -> VM path.
        for st in ('SW', 'SE', 'NW', 'NE'):
            ix = m['scan'][st]['index']
            half = st[1]
            b0 = next(b_ for b_ in B if b_[0] == f'iv_{st}_0')
            # opposite the t_vm pin run of band b5 (split record: band y0 + the pin run centre; parent R0 / MX)
            sp_ = json.loads((ROOT / 'physical/hbm_accel_die_views/index_q/split/split.json').read_text())
            pr_ = json.loads((ROOT / 'physical/hbm_accel_die_views/index_q/split/hfd_index_q_b5/ports.json').read_text())
            ys_ = [(q[3] + q[5]) / 2 for q in pr_['ports']['t_vm']['pins']]
            ly = sp_['bands']['hfd_index_q_b5']['y0_um'] + (min(ys_) + max(ys_)) / 2
            iy = ix.y + (ix.h - ly if ix.orient in ('MX', 'R180') else ly)
            fa_, fb_ = ('W', 'E') if half == 'W' else ('E', 'W')
            ps = station((ix.x + ix.w + SHAVE + 30.0) if half == 'W' else (ix.x - 30.0), iy, f'ivp_{st}', 512, fa_, fb_, True)
            m.setdefault('clocked', {})[ps.name] = 'stream'
            m.setdefault('region_extra', []).append(dict(name=f'HUB-Q{st}', clock='clk_stream',
                                                         rect=[round(ps.x, 1), round(ps.y, 1), round(ps.x + ps.w, 1), round(ps.y + ps.h, 1)]))
            i0 = B.index(b0)
            B[i0] = (b0[0], b0[1], b0[2], [(ps.name, 'b')] + b0[3][1:])
            B.append((f'iv_{st}_p', 'hub', 512, [b0[3][0], (ps.name, 'a')]))
            P[f'index_vm_{st}'] = [f'iv_{st}_p'] + P[f'index_vm_{st}']
    if V.get('clk_dom'):
        clock_nets(m, B, coll)
        return B, dict(P)
    # ---- clock trunks (PLL in the collective block) to every clock-region root
    for nm_ in [it.name for it in insts if it.kind in ('svc', 'hub', 'spine') and it.name != coll.name]:
        B.append((f'clk_{nm_}', 'clock_trunk', CLK_BITS, [(coll.name, 'pll'), (nm_, 'ck')]))
    for st in m['groups']:
        B.append((f'clk_grp_{st}', 'clock_trunk', CLK_BITS, [(coll.name, 'pll'), (m['groups'][st]['sms'][0].name, 'ck')]))
    return B, dict(P)


def clock_nets(m, B, coll):
    """r15 clk_dom (H1 / H3 / H8, TF1-TF4): ONE net per clock domain from its PLL output port on the collective block
    (pll_stream / pll_serial / pll_hbm / pll_link) to every clocked block of the domain, and one reset net per domain
    (por_*).  Forwarded-link stations take their clock from the forwarded clock bits of their segments (r15 fwd) and only
    the reset.  The nets are logical: CTS builds a tree per clock region (domains.sdc) from them."""
    ck = defaultdict(list)
    rst = defaultdict(list)
    clocked = m.get('clocked', {})
    for it in m['insts']:
        if it.name == coll.name:
            continue
        d = None
        if it.kind in ('sm', 'attn_tile'):
            d = 'stream'
        elif it.kind in ('hub', 'spine'):
            d = 'serial' if it.domain == 'serial_0p9' else 'stream'
        elif it.kind == 'svc':
            d = 'hbm'
        elif it.kind == 'link':
            d = 'link'
        elif it.name in clocked:
            d = clocked[it.name]
        if d:
            ck[d].append(it.name)
            if it.kind != 'link':           # the link macro views have no reset pin
                rst[d].append(it.name)
        elif it.kind == 'waypoint':
            rst[m.get('fwd_dom', {}).get(it.name, 'stream')].append(it.name)
    for d in ('stream', 'serial', 'hbm', 'link'):
        if ck[d]:
            B.append((f'clk_{d}', 'clock_trunk', 1, [(coll.name, f'pll_{d}')] + [(n, 'ck') for n in ck[d]]))
        if rst[d]:
            B.append((f'rst_{d}', 'reset_tree', 1, [(coll.name, f'por_{d}')] + [(n, 'rst') for n in rst[d]]))


# ------------------------------------------------------------------------------------------------ abstracts
def _real_ports0(m=None):
    phy = S.real_lef(PHY_LEF)
    dfi = sorted(phy['pins'], key=lambda p: (phy['pins'][p][1][0], p))
    sd = dict(io=S._bus('tx', 512) + S._bus('rx', 512), ck=['clk'])
    if m is not None and m['variant'].get('link_rtl'):     # r15 (H6): even tx / rx halves of the chain
        h = TU_PORTS * (545 + 2)
        h = math.ceil(h / max(1, len(m['links'])))
        return {phy['name']: dict(dfi=dfi),
                S.real_lef(SERDES_LEF)['name']: dict(iox=S._bus('tx', 512)[:h] + S._bus('rx', 512)[:h], ck=['clk']),
                S.real_lef(UCIE_LEF)['name']: dict(iox=S._bus('tx', 512)[:256] + S._bus('rx', 512)[:256], ck=['clk'])}
    return {phy['name']: dict(dfi=dfi), S.real_lef(SERDES_LEF)['name']: sd, S.real_lef(UCIE_LEF)['name']: sd}


def _host_bind(out):
    """host PHY black box: iox = every signal pin in LEF order (outputs and inputs of the AXI-Lite BAR target and the
    64-bit host DMA, 381 b of the 512-b host chain; the rest are spare chain bits), ck = clk."""
    hb = S.real_lef(HOST_LEF)
    out[hb['name']] = dict(iox=[p for p in hb['pins'] if p != 'clk'], ck=['clk'])
    return out


def real_ports(m=None):
    return _host_bind(_real_ports0(m))


REAL = {}


def _init_real():
    for rel in (PHY_LEF, SERDES_LEF, UCIE_LEF, HOST_LEF):
        REAL[S.real_lef(rel)['name']] = rel


def port_widths(m, k):
    w = {}
    by = {it.name: it for it in m['insts']}
    for bid, cls, bits, eps in m['buses']:
        n = bits if k == 1 else max(1, math.ceil(bits / k))
        for inst, port in eps:
            if inst == 'TOP':
                continue
            mst = by[inst].master
            if '@' in port and mst not in REAL:      # r23: a sliced generated endpoint
                key = (mst, slice_port(port, k))
                n_ = max(port_idx(port)) + 1 if k == 1 else n
                w[key] = max(w.get(key, 0), n_)
                continue
            key = (mst, port)
            w[key] = max(w.get(key, 0), n)
    return w


_PF_CACHE = {}
_DISK_FAR = sorted((abs(ox) + abs(oy), ox, oy) for ox in range(-93, 94, 2) for oy in range(-93, 94, 2) if max(abs(ox), abs(oy)) > 37)
_PAIR_LOG = {}
_DISK37 = sorted((abs(ox) + abs(oy), ox, oy) for ox in range(-37, 38) for oy in range(-37, 38))
_PAIR_FALLBACK = {'anchored': 0, 'free': 0}
# hbmdie 10-13 (tree_cap): capacity-aware clock / reset tree routing.  A tree edge is a chain of buffer / relay pairs along
# a channel route; four domain trees used to push their trunks through the same narrow channels (e.g. the 121-um attention
# equator channel, 40 % filled by 236 pairs), the next pairs found no site inside, piled up at the channel mouth and the
# edge was left with a 1.5-4.2 mm hop.  With tree_cap the route cost of a cell grows with the pairs / stations already
# in it, a cell where a pair stalled is closed for the tree, and balancing pads prefer open (>= TREE_WIDE_UM) space.
TREE_WIDE_UM = 200.0        # a channel narrower than this in either axis is 'narrow' (no free 200 x 200 um square)
TREE_OCC_COST = 20.0        # route cost of a full cell (fill = waypoint area / free area of the 100-um cell)
TREE_FILL0, TREE_FILL1 = 0.15, 0.45     # the fill charge ramps from 0 at FILL0 to TREE_OCC_COST at FILL1
TREE_NARROW_COST = 1.0      # extra route cost of a narrow-channel cell (trunks prefer open channels at equal length)
TREE_FULL = 0.30            # a cell is full for pads / branch nodes at this waypoint fill of its free area
TREE_STALL_UM = 150.0       # a chain pair landing farther than this from its route has stalled
TREE_STEP_UM = 300.0        # tree_fixed_path: a pair every this much of the edge's route (reach 400 um box gap)
TREE_STALL_COST = 0.1       # of the block cost, per stall recorded on a cell (10 stalls close it like a block)
_PAD_RING = sorted(((ox, oy) for ox in range(-18, 19) for oy in range(-18, 19)), key=lambda o: (abs(o[0]) + abs(o[1]), o))


def tree_wide_mask(blocks, W, H, nx, ny, cell=100.0, f=10, wide_um=TREE_WIDE_UM):
    """(wide, widef): wide = (ny * f, nx * f) raster, True where the point lies in some block-free wide_um x wide_um
    square inside the die (morphological opening of the free space); widef = its mean per route cell"""
    import numpy as np
    from scipy import ndimage as ndi
    cu = cell / f
    fr = np.ones((ny * f, nx * f), np.uint8)
    for x0, y0, x1, y1 in blocks:
        fr[max(0, int(y0 // cu)):max(0, int(math.ceil(y1 / cu))), max(0, int(x0 // cu)):max(0, int(math.ceil(x1 / cu)))] = 0
    fr[int(H // cu):, :] = 0
    fr[:, int(W // cu):] = 0
    k = int(round(wide_um / cu)) | 1
    wide = ndi.maximum_filter(ndi.minimum_filter(fr, size=k, mode='constant', cval=0), size=k, mode='constant', cval=0)
    wide = (wide > 0) & (fr > 0)
    return wide, wide.reshape(ny, f, nx, f).mean(axis=(1, 3))


def tree_cap_cost(free, occ, stall, widef, block_cost, free_min=0.2):
    """per-cell route cost of a capacity-aware tree edge: 1 + the block cost of an unroutable cell + the fill of the
    cell (waypoint area / free area) + a closed cell where a pair stalled + a small charge for a narrow channel"""
    import numpy as np
    fr = np.maximum(free, 0.05)
    fill = np.clip((occ / fr - TREE_FILL0) / (TREE_FILL1 - TREE_FILL0), 0.0, 1.0)
    return (1.0 + block_cost * (free < free_min) + TREE_OCC_COST * fill
            + block_cost * np.minimum(TREE_STALL_COST * stall, 1.0)
            + TREE_NARROW_COST * ((widef < 0.3) & (free >= free_min)))
def tree_fp_cost(free, occ, stall, widef, block_cost, free_min=0.2):
    """tree_fixed_path (H-DIE 10-14 pm) route cost of a clock / reset tree edge.  The clock wire runs on M8 / M9 over
    blocks; only its buffer / relay pairs need free sites (<= 400 um apart).  The tree_cap cost charged a full cell
    20x and a blocked cell 400x, so v14 tree edges detoured 4-6x (stream root->leaf route up to 169 mm on a 33 x 26 mm
    die, 575 stages).  Here: a cell whose free sites are full costs TREE_FP_FILL x, a blocked cell on the rim of a block
    (a free cell beside it: blocks <= ~200 um wide, abutment gaps and block edges) TREE_FP_RIM x, a block interior the
    full block cost, a stall TREE_FP_STALL x per stall."""
    import numpy as np
    from scipy import ndimage as ndi
    fr = np.maximum(free, 0.05)
    fill = np.clip((occ / fr - TREE_FILL0) / (TREE_FILL1 - TREE_FILL0), 0.0, 1.0)
    blk = free < free_min
    rim = blk & ndi.binary_dilation(~blk, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool))
    return (1.0 + TREE_FP_FILL * fill + TREE_FP_RIM * rim + block_cost * (blk & ~rim)
            + TREE_FP_STALL * np.minimum(stall, 10.0))


TREE_FP_FILL = float(os.environ.get('OT_HBMDIE_TREE_FP_FILL', '1.0'))
TREE_FP_RIM = float(os.environ.get('OT_HBMDIE_TREE_FP_RIM', '4.0'))
TREE_FP_STALL = float(os.environ.get('OT_HBMDIE_TREE_FP_STALL', '1.0'))
_WIDE_RING = sorted(((ox, oy) for ox in range(-20, 21) for oy in range(-20, 21)), key=lambda o: (abs(o[0]) + abs(o[1]), o))
_PAIR_RING = sorted(((ox, oy) for ox in range(-10, 11) for oy in range(-10, 11)), key=lambda o: (abs(o[0]) + abs(o[1]), o))


def _anchor_ports(spec):
    """contract v8 (hbm-die-iter 10-12): {master: {port: dict(face, layer, centre, pitch, bits)}} from a CLOSED element's
    port record ({master: 'path/ports.json'}): the die master takes those ports exactly where the element's LEF has them
    (face from the pin x/y, centre = pin-centre mean, pitch in tracks); the die's other ports on that face pack around."""
    if not spec:
        return {}
    key = json.dumps(spec, sort_keys=True)
    if key not in _PF_CACHE:
        out = {}
        for mname, path in spec.items():
            d_ = json.loads((ROOT / path).read_text())
            W_, H_ = d_['w_um'], d_['h_um']
            o_ = out.setdefault(mname, {})
            for p_, r_ in d_['ports'].items():
                pins = r_['pins']
                xs = [(q[2] + q[4]) / 2 for q in pins]
                ys = [(q[3] + q[5]) / 2 for q in pins]
                x0, y0 = sum(xs) / len(xs), sum(ys) / len(ys)
                face = min((('W', x0), ('E', W_ - x0), ('S', y0), ('N', H_ - y0)), key=lambda t: t[1])[0]
                al = ys if face in 'EW' else xs
                lay = pins[0][1]
                step = (al[-1] - al[0]) / (len(al) - 1) if len(al) > 1 else Q.TRK[lay][1]
                # the LEF writer starts a port's first pin at centre - n * step / 2: that centre puts every pin on its
                # quarter track (a single pin: its own centre)
                o_[p_] = dict(face=face, layer=lay, centre=round(al[0] + len(al) * step / 2 if len(al) > 1 else al[0], 4),
                              bits=r_['bits'],
                              pitch=max(1, round(abs(step) / Q.TRK[lay][1])))
        _PF_CACHE[key] = out
    return _PF_CACHE[key]


def _pack_anchored(mst, face, lst, anc, pw, k):
    """place the anchored ports of one face exactly; return the rest with their wanted centres moved out of the anchored
    intervals (each slides to the nearer free side, order kept by the generic packer that follows)."""
    rest, busy = [], []
    for want, pt in lst:
        a_ = anc.get(pt)
        if a_ and a_['face'] == face:
            n_ = max(1, pw.get((mst.name, pt), 1))
            mst.face(pt, n_, face, a_['layer'], a_['centre'], a_['pitch'])
            half = n_ * Q.TRK[a_['layer']][1] * k * a_['pitch'] / 2
            busy.append((a_['centre'] - half, a_['centre'] + half, n_, a_['layer']))
        else:
            rest.append((want, pt))
    if busy and rest:
        mst.anchor_busy = getattr(mst, 'anchor_busy', {})
        mst.anchor_busy[face] = sorted(busy)
    return rest


def _pinned_faces(root):
    """hbmdie-1011/rf2: {(master, port): face} from the pinned die-view port records (ports_r25gqn/<master>/ports.json)"""
    if not root:
        return {}
    if root not in _PF_CACHE:
        out = {}
        for f_ in sorted((ROOT / root).glob('*/ports.json')):
            d_ = json.loads(f_.read_text())
            for p_, r_ in d_['ports'].items():
                if r_.get('face') in ('N', 'S', 'E', 'W'):
                    out[(d_['master'], p_)] = r_['face']
        _PF_CACHE[root] = out
    return _PF_CACHE[root]


def masters(m, k=1):
    """Generated abstracts.  Each port sits on the face that looks at its peer (stations: the faces registered along
    their route), at the position nearest its peer's projection; ports on one face are packed in that order.  SM ports
    use the sm_r2 context pin regions."""
    M = {}
    by = {it.name: it for it in m['insts']}
    pw = port_widths(m, k)
    _init_real()
    first = {}
    for it in m['insts']:
        first.setdefault(it.master, it)
    peers = defaultdict(list)
    ref = {}
    slice_keys = set()
    pf = m['variant'].get('port_fix')
    for bid, cls, bits, eps in m['buses']:
        for i, (inst, port) in enumerate(eps):
            if inst == 'TOP':
                continue
            it = by[inst]
            key = (it.master, slice_port(port, k) if it.master not in REAL else port)
            if '@' in port and k > 1 and it.master not in REAL:
                slice_keys.add(key)
            if pf:      # r10: a port that only another copy uses still gets its pin, placed from that copy's frame
                if key in ref and ref[key] is not it and ref[key] is first[it.master]:
                    continue
                if key in ref and ref[key] is not it and it is not first[it.master]:
                    continue
                if key in ref and ref[key] is not it:          # the first copy has it too: prefer the first copy
                    peers[key] = []
                ref[key] = it
            elif it is not first[it.master]:
                continue
            others = [by[o] for j, (o, _) in enumerate(eps) if j != i and o != 'TOP']
            peers[key] += others
    hold_ = m.get('pin_peer_hold') or {}      # hbmdie-1011: block ck / rst pins stay where the die-wide net put them
    if hold_:                                 # (clock / reset trees): peers of the copy masters() pins this port from
        for (mst_, prt_) in list(peers):
            it_ = ref.get((mst_, prt_), first.get(mst_))
            nm_ = hold_.get(f'{mst_}|{prt_}|{it_.name}') if it_ is not None else None
            if nm_ is not None:
                peers[(mst_, prt_)] = [by[n_] for n_ in nm_ if n_ in by]
    notes = {'hfd_sm': 'SM element ot_hbm_accel_sm_v NC8/SUB4 (sm_r2 context 2202.768 x 2072.79, 202 macros; pin regions '
                       'of the context: d/req/rsp bottom, xw left, results right, control top; element route OPEN)'}
    notes.update(m.get('master_notes', {}))
    fixed = m.get('fixed_ports', {})       # master -> fn(Master): replicated elements with a fixed pin plan
    for it in m['insts']:
        if it.master in M or it.master in REAL:
            continue
        nt = notes.get(it.master) or (f'{it.kind}: forwarded-link / multicast / gather station' if it.kind == 'waypoint'
                                      else f'{it.kind} placeholder sized from the block ledger')
        M[it.master] = Q.Master(it.master, it.w, it.h, 3 if it.kind in ('waypoint', 'head') else 7, nt)
    sm_fixed = dict(d='S', q='S', x='W', r='E', c='N', ck='N', rst='N')
    sm_span = dict(S=(550.7, 1652.1), W=(518.2, 1554.6), E=(518.2, 1554.6), N=(550.7, 1652.1))
    if m['variant'].get('sm_faces'):        # r17 probe: the smh element's own face map / pin spans (master frame)
        sm_fixed = dict(m['variant']['sm_faces'])
        sm_span = dict(m['variant']['sm_span'])
    items = defaultdict(lambda: defaultdict(list))
    for mname, fn in fixed.items():
        if mname in M:
            try:
                fn(M[mname], k)
            except TypeError:
                fn(M[mname])
    for (mname, port), others in peers.items():
        if mname in REAL or mname not in M or mname in fixed:
            continue
        if mname.startswith('hfd_svc_') and port == 'phy':
            continue
        it = ref.get((mname, port), first[mname])
        if not others:      # a die-top strap (no peer block, e.g. hfd_su qid): placed on the block's own centre face
            others = [it]
        ox = sum(o.x + o.w / 2 for o in others) / len(others)
        oy = sum(o.y + o.h / 2 for o in others) / len(others)
        lx, ly = ox - it.x, oy - it.y
        bport = re.sub(r'_s\d+$', '', port) if (mname, port) in slice_keys else port   # r23 bundled slice port
        if mname == 'hfd_sm':
            face = sm_fixed[bport]                          # master frame
        elif mname in m['stn_faces'] and bport in m['stn_faces'][mname]:
            face = m['stn_faces'][mname][bport]             # stations are placed R0
        else:
            dx, dy = (ox - it.x - it.w / 2) / it.w, (oy - it.y - it.h / 2) / it.h
            face = ('E' if dx > 0 else 'W') if abs(dx) >= abs(dy) else ('N' if dy > 0 else 'S')   # die frame
            if it.kind == 'spine' and abs(ox - it.x - it.w / 2) > it.w / 2:
                face = 'E' if dx > 0 else 'W'     # r7: spine blocks escape sideways (N/S faces look at the next block)
            if it.orient in ('MX', 'R180'):
                face = {'N': 'S', 'S': 'N'}.get(face, face)
            if it.orient in ('MY', 'R180'):
                face = {'E': 'W', 'W': 'E'}.get(face, face)
        if it.orient in ('MX', 'R180'):
            ly = it.h - ly
        if it.orient in ('MY', 'R180'):
            lx = it.w - lx
        along = ly if face in 'EW' else lx
        if mname == 'hfd_su' and port in ('t_su_ew', 'f_su_ew') and m['variant'].get('ew_corridor'):
            ly = m['geo']['ew_y'][it.name[-2]] - it.y
            if it.orient in ('MX', 'R180'):
                ly = it.h - ly
            along = ly
        if it.kind == 'spine' and m['variant'].get('root_pins') and face in 'EW':
            # r14: a trunk root (x multicast, control, expert request, link) leaves its spine block at the face end on
            # the side its trunk heads for (r13: placed by peer projection among the hub nets, +0.6 mm first segment)
            mt = re.fullmatch(r'[xce](SW|SE|NW|NE)', port) or re.fullmatch(r'llk_([SN])\d', port)
            if mt:
                along = 0.0 if mt.group(1)[0] == 'S' else it.h
        ff_ = m['variant'].get('face_force') or {}
        if isinstance(ff_, dict) and any(isinstance(k_, str) for k_ in ff_):    # a JSON variant: 'master|port' keys
            ff_ = {tuple(k_.split('|')) if isinstance(k_, str) else k_: v_ for k_, v_ in ff_.items()}
        mlg_ = re.fullmatch(r'([tf])_(lg(?:[WE]2?|[NS][EW]))_(rdn|wdn|rup|wup)', bport)
        if mlg_:        # chain nets: down buses keep the old t_ / f_ face, up buses enter / leave on the opposite one
            port_ff = (mlg_.group(1) if mlg_.group(3).endswith('dn') else {'t': 'f', 'f': 't'}[mlg_.group(1)]) + '_' + mlg_.group(2)
        else:
            port_ff = port
        mst_ = re.fullmatch(r'([tf])_(lg(?:[WE]2?|[NS][EW]))(c?)_(rdn|wdn|rup|wup)', bport)
        if mst_ and mname.startswith('hfd_stn_lg') and (m.get('lane_station_face') or {}).get(it.name):
            # a lane-group client station: the full-width tap on the face toward its client, the chain on the opposite
            # (outer) face -- a mid-chain station's upstream and downstream share the outer face
            cf_ = m['lane_station_face'][it.name]
            face = cf_ if mst_.group(3) == 'c' else {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}[cf_]
            along = ly if face in 'EW' else lx
        if mlg_ and it.kind == 'waypoint' and mname.startswith('hfd_stn_q'):
            # a lane-group relay bank: the upstream side (f_*dn in, t_*up out) on one long face, the downstream side on
            # the opposite one, ordered by where the two peers sit (a bank at a route corner has both peers on one side)
            pu_ = peers.get((mname, f'f_{mlg_.group(2)}_rdn')) or [it]
            pd_ = peers.get((mname, f't_{mlg_.group(2)}_rdn')) or [it]
            upside_ = (mlg_.group(1) == 'f') == mlg_.group(3).endswith('dn')
            if it.w >= it.h:
                su_ = 'N' if pu_[0].y + pu_[0].h / 2 >= pd_[0].y + pd_[0].h / 2 else 'S'
                face = su_ if upside_ else {'N': 'S', 'S': 'N'}[su_]
            else:
                su_ = 'E' if pu_[0].x + pu_[0].w / 2 >= pd_[0].x + pd_[0].w / 2 else 'W'
                face = su_ if upside_ else {'E': 'W', 'W': 'E'}[su_]
            along = ly if face in 'EW' else lx
        pf_ = _pinned_faces(m['variant'].get('pinned_faces'))
        # v13: a tile-wide slice of a port (pin_repair) keeps the face rules of its port
        kp_ = (mname, port) if bport == port else (mname, bport)
        if (mname, port) in pf_ or kp_ in pf_:    # rf2: physical relays must not move a pinned block's port faces (the routed / queued
            # block pin plans in ports_r25gqn stay valid): a port keeps its pinned face, the first station sits beside it
            face = pf_.get((mname, port)) or pf_[kp_]
            along = ly if face in 'EW' else lx
        if (mname, port_ff) in ff_ or kp_ in ff_:     # R25GQ: lane-group ports on a fixed face
            face = ff_.get((mname, port_ff)) or ff_[kp_]
            along = ly if face in 'EW' else lx
        if m['variant'].get('face_fix') and ((mname, port) in FACE_FIX or kp_ in FACE_FIX):
            # r16g: role ports of shared masters on their fixed master-frame face (r16e lint: the corner-tile KV pin
            # and three SU result pins took their face from another copy's peer and faced away on the mirrors)
            face = FACE_FIX.get((mname, port)) or FACE_FIX[kp_]
            along = ly if face in 'EW' else lx
        fk_ = m['variant'].get('face_keep') or {}
        if (mname, port) in fk_ or kp_ in fk_:
            # contract v12: a published slot face is an interface (clusters are built to it): a port stays on its
            # published face when a neighbour's move would only re-seat its first station (the route bends instead)
            face = fk_.get((mname, port)) or fk_[kp_]
            along = ly if face in 'EW' else lx
        if mname == 'hfd_sm' and port in ('x', 'c') and m['variant'].get('sm_xmid'):
            along = sum(sm_span[face]) / 2      # r12 option: x / c pins centred in their pin region (row-neutral)
        items[mname][face].append((along, port))
    anc_ = _anchor_ports(m['variant'].get('anchor_ports'))
    for mname, fs in items.items():
        mst = M[mname]
        for face, lst in fs.items():
            if mname in anc_:
                lst = _pack_anchored(mst, face, lst, anc_[mname], pw, k)
                if not lst:
                    continue
            layer = 'M4' if face in 'EW' else 'M5'
            p = Q.TRK[layer][1] * k
            full = mst.h if face in 'EW' else mst.w
            a0, a1 = sm_span[face] if mname == 'hfd_sm' else (2 * p + 0.5, full - 2 * p - 0.5)
            lst.sort()
            n = [max(1, pw.get((mname, pt), 1)) for _, pt in lst]
            room = a1 - a0
            gap = 4 * p
            pitch = 1
            for pc in (4, 2):
                if pc * sum(n) * p + (len(n) - 1) * gap <= room * (0.5 if mname.startswith('hfd_') and
                                                                        not M[mname].note.startswith('waypoint') else 1.0):
                    pitch = pc
                    break
            if mname.startswith(('hfd_stn', 'hfd_mcast', 'hfd_gath', 'hfd_cdist', 'hfd_meso')) or mname == 'hfd_sm' or \
                    mname in (m['variant'].get('dense_face_masters') or ()):
                # R25GQ [svc] 10-10: hfd_loader's N face (t_hgi_vmw 8,960 b + the HGI ports, 10,953 pins) packed at the
                # 0.048 track was 20.8 b/um (fp gate 12): every other track over the whole face (10.4 b/um)
                pitch = max(pitch, 2) if 2 * sum(n) * p + (len(n) - 1) * gap <= room else pitch
            need = [x * p * pitch for x in n]
            if mname in (m['variant'].get('dense_face_masters') or ()) and pitch >= 1 and \
                    2 * sum(n) * p + (len(n) - 1) * gap > room and \
                    not (k > 1 and sum(n) * p + (len(n) - 1) * gap <= room):   # GRT bundles: one layer when it fits
                # R25GQ 10-10: a dense face that cannot hold every other track on one layer interleaves two layers
                # (M5 + M7 on N / S, M4 + M6 on E / W), every other track on each: <= 10.4 b/um a layer
                l2_ = 'M7' if layer == 'M5' else 'M6'
                peff = 1.0 / (1.0 / (2 * Q.TRK[layer][1] * k) + 1.0 / (2 * Q.TRK[l2_][1] * k))
                layer, pitch = f'{layer}+{l2_}', 1
                need = [x * peff * 1.03 + 0.5 for x in n]      # the merged grids' edge rounding: a little slack
            if sum(need) + gap * (len(n) - 1) > room + 1e-6:
                raise ValueError(f'{mname} face {face}: {sum(need):.1f} um of pins on {room:.1f} um ' + str([(pt, nn_) for (_, pt), nn_ in zip(lst, n)]))
            pos, starts = a0, []
            spread = (mname in SPREAD_MASTERS or mname in (m['variant'].get('dense_face_masters') or ())) and not m['variant'].get('no_spread') and full >= 500.0 and mname != 'hfd_sm' and not mname.startswith(('hfd_svc_', 'hfd_stn', 'hfd_mcast',
                                                                                      'hfd_gath', 'hfd_cdist'))
            if spread:          # r4 spread every hub port evenly: overflow 2,519 -> 5,223; r6: coll / VM only
                g_even = (room - sum(need)) / (len(need) + 1)
                gap = max(gap, g_even)
                pos = a0 + g_even
            busy_ = (getattr(mst, 'anchor_busy', None) or {}).get(face)
            if busy_:       # v8 anchored face: each free port (largest first) takes the feasible slot nearest its want;
                # a multi-bit anchor blocks every layer, a single-pin anchor (clock / reset) only its own layer, so a free
                # port that finds no room on the face's layer steps over the single pins on the face's second layer
                occ, st_, ly_ = [(b0, b1, None) for b0, b1, nb, _ in busy_ if nb > 1], {}, {}
                pts = [(b0, b1, bl) for b0, b1, nb, bl in busy_ if nb == 1]
                gap = 4 * p        # the plain pin gap (no spread on an anchored face)
                l2 = 'M6' if face in 'EW' else 'M7'
                for (want, pt), nd in sorted(zip(lst, need), key=lambda t: -t[1]):
                    for lay_ in (layer, l2):
                        blk = occ + [q for q in pts if q[2] in lay_.split('+')]
                        blk = [q for q in blk if q[2] is None or q[2] in lay_.split('+')]
                        cands = [min(max(want - nd / 2, a0), a1 - nd)] + [b1 + gap for _, b1, _ in blk] + \
                            [b0 - gap - nd for b0, _, _ in blk]
                        ok = [c for c in cands if a0 - 1e-6 <= c and c + nd <= a1 + 1e-6 and
                              all(c >= b1 + gap - 1e-6 or c + nd <= b0 - gap + 1e-6 for b0, b1, _ in blk)]
                        if ok:
                            break
                    else:
                        raise ValueError(f'{mname} face {face}: anchored ports leave no room for {pt} ({nd:.1f} um)')
                    s0 = min(ok, key=lambda c: abs(c + nd / 2 - want))
                    st_[pt], ly_[pt] = s0, lay_
                    occ.append((s0, s0 + nd, lay_ if lay_ != layer else None))
                for (want, pt), nd, nn in zip(lst, need, n):
                    mst.face(pt, nn, face, ly_[pt], st_[pt] + nd / 2, pitch)
                continue
            else:
                for (want, pt), nd in zip(lst, need):
                    s0 = pos if spread else min(max(want - nd / 2, pos), a1 - nd)
                    starts.append(s0)
                    pos = s0 + nd + gap
                end = a1
                for i in range(len(starts) - 1, -1, -1):
                    if starts[i] + need[i] > end:
                        starts[i] = end - need[i]
                    end = starts[i] - gap
            for (want, pt), nd, s0, nn in zip(lst, need, starts, n):
                mst.face(pt, nn, face, layer, s0 + nd / 2, pitch)
    for st in m['groups']:
        if f'hfd_svc_{st}' not in M:      # r16j: svc split into x-band segment masters (fixed pin plans)
            continue
        mst = M[f'hfd_svc_{st}']
        if k == 1:
            ph = S.real_lef(PHY_LEF)
            mst.ports['phy'] = ('xy', [(ph['pins'][n_][1][0] + ph['pins'][n_][1][2]) / 2
                                       for n_ in real_ports()[ph['name']]['dfi']])
            mst.order.append('phy')
        else:
            mst.face('phy', max(1, pw.get((mst.name, 'phy'), 1)), 'S', 'M5', mst.w / 2, 4)
    if m['variant'].get('vm_centre_ck'):
        for name in VM_CENTRE:
            ck_centre(M[name], M[name].ports)
    if m['variant'].get('hub_pin_window') and k == 1:    # r23: hub quarter ports in a <= 500 um window per face
        for nm_ in ('hfd_su', 'hfd_sfu', 'hfd_hc'):
            if nm_ in M and nm_ not in (m['variant'].get('dense_face_masters') or ()):   # R25GQ: dense faces spread
                hub_pin_window(M[nm_], m['variant']['hub_pin_window'], p4=bool(m['variant'].get('hub_pin_p4')))
    if m['variant'].get('hub_ports_file') and k == 1:   # r25: hub quarter E/W faces frozen at the r24p plan (the
        #   cmdproc split shifts the peer-projected SU E window by ~2.6 um; the queued r24p quarter routes stay valid)
        for nm_, specs in json.loads((ROOT / m['variant']['hub_ports_file']).read_text()).items():
            if nm_ in M:
                for p_, sp_ in specs.items():
                    M[nm_].ports[p_] = tuple(sp_)
    if m['variant'].get('hub_ck_seg'):      # r24: per-segment ck pins on the 5.53 mm hub quarters
        for nm_ in HUB_QUARTERS:
            if nm_ in M:
                hub_ck_seg(M[nm_], m['variant']['hub_ck_seg'], k, distinct=bool(m['variant'].get('r25gq')))
    if m['variant'].get('hc_ck_ew') and 'hfd_hc' in M:     # [cg-hc] 10-10 decision (A): each HC row root ck<c> is two pins,
        ys_, m6_ = m['variant']['hc_ck_ew']                  # ck<c>e (E face) / ck<c>w (W face) at the row centre y
        hc_m = M['hfd_hc']
        for c_, y_ in enumerate(ys_):
            for p_ in (f'ck{c_}', f'ck{c_}e', f'ck{c_}w'):
                hc_m.ports.pop(p_, None)
                while p_ in hc_m.order:
                    hc_m.order.remove(p_)
            for f_ in ('e', 'w'):
                hc_m.face(f'ck{c_}{f_}', 1, f_.upper(), 'M6' if (f_ == 'e' and c_ in m6_) else 'M4', y_, 1)
        for p_, a_ in (_anchor_ports(m['variant'].get('anchor_ports')).get('hfd_hc') or {}).items():
            if re.fullmatch(r'ck\d+[ew]', p_):    # v8: the closed quarter's clock pins (layer / centre of its LEF)
                hc_m.ports[p_] = ('face', 1, a_['face'], a_['layer'], a_['centre'], 1)
    if m['variant'].get('vm_cross_aligned') and 'hfd_vm_sw' in M:   # r23: abutting VM tiles' cross buses face to face
        vm_cross_align(M, k, two_layer=bool(m['variant'].get('vm_cross_2layer')))
    if m['variant'].get('vm_ck_centre'):      # r20: the VM tiles' ck as the centre M7 area pin
        for q in ('sw', 'se', 'nw', 'ne'):
            if f'hfd_vm_{q}' in M:
                ck_centre(M[f'hfd_vm_{q}'], M[f'hfd_vm_{q}'].ports)
    if k > 1:
        for name, ports in real_ports(m).items():
            if name == 'ot_hbm_host_phy':     # bundle as many runs as the 512-b chain carries (spare bits)
                ports = dict(ports, iox=ports['iox'] + [ports['iox'][-1]] * (pw.get((name, 'iox'), 0) * k - len(ports['iox'])))
            M[name] = S._real_master_bundled(REAL[name], k, ports)
    return M


def svc_phy_pins(M, m, k):
    return


def write_lefs(m, k, path):
    M = masters(m, k)
    svc_phy_pins(M, m, k)
    pw = port_widths(m, k)
    txt, npins = [], 0
    for name, mst in M.items():
        if k == 1 and name in REAL:
            continue
        wmap = {p: pw.get((name, p), 0) for p in mst.order}
        if m.get('network_probe') and k == 1:
            # die-evidence-2 2026-10-09: a network probe (R25G) carries exact-rectangle masters whose ports the probe
            # does not wire (the native indexer's st / fs / co / kin / qb / to): write those pins UNCONNECTED at full
            # width so the physical case exists.  They are build-every-path GAPS, listed in m['unwired_rect_ports']
            # and in die_top_lint's unbound_real_pins; never a die net.
            for p_ in mst.order:
                sp_ = mst.ports.get(p_)
                if wmap[p_] == 0 and sp_ and sp_[0] == 'rects':
                    wmap[p_] = len(sp_[1])
                    m.setdefault('unwired_rect_ports', []).append(f'{name}/{p_}')
        t, n = S.lef_text(mst, k, wmap)
        if name in ('hfd_attn_half_lo', 'hfd_attn_half_hi'):
            # Unpublished half placeholders reserve an explicit peripheral
            # contact corridor: 192 nm contact depth plus 48 nm clearance.
            # The full-outline OBS formerly covered every exact face pin.
            # This is a pathfinding reservation, never a routed-view export.
            margin = 0.240
            head, obs = t.split('  OBS', 1)
            for layer in range(4, mst.obs_top + 1):
                old = f'LAYER M{layer} ;\n      RECT 0 0 {mst.w:.3f} {mst.h:.3f} ;'
                new = (f'LAYER M{layer} ;\n      RECT {margin:.3f} {margin:.3f} '
                       f'{mst.w - margin:.3f} {mst.h - margin:.3f} ;')
                obs = obs.replace(old, new)
            t = head + '  OBS' + obs
        txt.append(t.replace('tools/dsrom_s81_fulldie.py', 'tools/hbm_accel_die_fp.py'))
        npins += n
    Path(path).write_text('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n' + '\n'.join(txt) + 'END LIBRARY\n')
    return npins


def pin_clashes(m, k=1):
    M = masters(m, k)
    svc_phy_pins(M, m, k)
    pw = port_widths(m, k)
    space = 0.024 * k - 1e-6
    out = []
    for name, mst in M.items():
        if name in REAL:
            continue
        if any(sp_[0] == 'rects' for sp_ in mst.ports.values()):
            # exact hardened pin rectangles (native indexer views): no generated pins to clash; a die bus whose width
            # differs from the hardened port is reported instead of aborting the check
            for p_, sp_ in mst.ports.items():
                if sp_[0] == 'rects' and pw.get((name, p_), len(sp_[1])) != len(sp_[1]) and k == 1:
                    out.append((name, f'width {p_}: die bus {pw[(name, p_)]} b != hardened {len(sp_[1])} b', '', ''))
            continue
        rects = sorted(S.pin_rects(mst, k, {p: pw.get((name, p), 0) for p in mst.order}), key=lambda r: (r[1], r[2][0]))
        by = defaultdict(list)
        for nm, ly, r in rects:
            by[ly].append((nm, r))
        for ly, rs in by.items():     # R25GQ 10-10: 2 um bucket grid (the x sweep went quadratic on 20 k-pin E / W faces)
            grid_ = defaultdict(list)
            for nm, r in rs:
                bx0, bx1 = int((r[0] - space) // 2.0), int((r[2] + space) // 2.0)
                by0, by1 = int((r[1] - space) // 2.0), int((r[3] + space) // 2.0)
                seen_ = set()
                for gx_ in range(bx0, bx1 + 1):
                    for gy_ in range(by0, by1 + 1):
                        for an, ar in grid_[(gx_, gy_)]:
                            if an in seen_:
                                continue
                            seen_.add(an)
                            if ar[0] < r[2] + space and r[0] < ar[2] + space and ar[1] < r[3] + space and r[1] < ar[3] + space:
                                out.append((name, ly, an, nm))
                for gx_ in range(int(r[0] // 2.0), int(r[2] // 2.0) + 1):
                    for gy_ in range(int(r[1] // 2.0), int(r[3] // 2.0) + 1):
                        grid_[(gx_, gy_)].append((nm, r))
    return out


def write_netlist(m, k, path, top='hfd_die'):
    rp = real_ports(m) if k == 1 else {}
    by = {it.name: it for it in m['insts']}
    conns = defaultdict(list)
    top_ports = m.get('top_input_ports', {})
    if k > 1:       # v14: the bundled GRT model has no die pins (the ckgen bumps refclk / por_n are k = 1 STA / DEF only)
        top_ports = {}
    declarations = ', '.join(f'input wire {name}' for name in top_ports)
    V = [f'// tools/hbm_accel_die_fp.py: die-level nets only (k = {k})', f'module {top} ({declarations});']
    for bid, cls, bits, eps in m['buses']:
        if k > 1 and any(e[0] == 'TOP' for e in eps):
            continue
        n = bits if k == 1 else max(1, math.ceil(bits / k))
        net = f'n_{bid}'
        V.append(f'  wire [{n - 1}:0] {net};')
        for inst, port in eps:
            if inst == 'TOP':
                if n != 1 or port not in top_ports:
                    raise ValueError(f'unsupported top connection {port}')
                V.append(f'  assign {net}[0] = {port};')
        for inst, port in eps:
            if inst == 'TOP':
                continue
            mst = by[inst].master
            if '@' in port and mst not in REAL:      # r23: sliced generated endpoint
                if k == 1:
                    conns[inst].append(('mslice', port_base(port), port_idx(port), net))
                else:
                    conns[inst].append((slice_port(port, k), net, n))
            elif '@' in port:         # r16j: slice lo:hi of a real or bundled port (svc band <- PHY dfi range)
                base = port_base(port)
                idx = port_idx(port)
                lo = idx[0]
                if mst in rp and base in rp[mst]:
                    conns[inst].append(([rp[mst][base][i_] for i_ in idx], net))
                else:
                    conns[inst].append(('slice', base, lo // k, n, net))
            elif mst in rp and port in rp[mst]:
                conns[inst].append((rp[mst][port][:n], net))
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
            elif c[0] == 'slice':
                _, base, off, n, net = c
                for i in range(n):
                    bus_bits[base].setdefault(off + i, f'{net}[{i}]')
            elif c[0] == 'mslice':
                _, base, idx, net = c
                for i, b_ in enumerate(idx):
                    bus_bits[base][b_] = f'{net}[{i}]'
            else:
                port, net, n = c
                # OpenSTA 26Q3 collapses one-bit Liberty data buses to bit pins.
                # Binding the bus name crashes VerilogReader::makeModuleInst;
                # the explicit escaped bit pin preserves the same connection.
                if m.get('relay_masters', {}).get(it.master) == 1 and port in ('d', 'q'):
                    parts.append(f'.{Q.esc(port + "[0]")}({net}[0])')
                else:
                    parts.append(f'.{port}({net})')
        for base, bits_ in bus_bits.items():
            hi = max(bits_)
            cat = ', '.join(bits_.get(j, "1'bz") for j in range(hi, -1, -1))
            parts.append(f'.{Q.esc(base)}({{{cat}}})')
        for sp_, sv_ in ((m['variant'].get('die_straps') or {}).get(it.name) or {}).items():    # v14: identity straps
            parts.append(f".{sp_}(2'd{sv_})")
        V.append(f'  {it.master} {it.name} (' + ', '.join(parts) + ');')
    V.append('endmodule\n')
    Path(path).write_text('\n'.join(V))


# ------------------------------------------------------------------------------------------------ power
DENS = dict(sm=1.20, svc=3.924, hub=1.05, spine=1.05, attn_tile=1.05, waypoint=0.6)
DENS_BASIS = ('W/mm2 at the peak in-phase point, ASSUMED: SM 1.20 (above the H100 die average 0.86 W/mm2 = 700 W / 814 mm2, '
              'all 32 SMs streaming in phase); stream service 3.924 (Qwen strip/controller class); hub logic 1.05 (Qwen '
              'full-die hub class, as S81); waypoints 0.6; PHY, SerDes and host on their own supplies (no core-grid load)')
DENS_OVR = dict(hb_index=1.25)


def inst_power(it):
    if it.kind in ('phy', 'link', 'serdes_slab', 'host_slab'):
        return 0.0
    d = DENS_OVR.get(it.name, DENS.get(it.kind, 0.0))
    return d * (it.w + SHAVE) * (it.h + SHAVE) / 1e6


def die_power(m):
    by = defaultdict(float)
    for it in m['insts']:
        by[it.kind] += inst_power(it)
    return dict(peak_in_phase_w=round(sum(by.values()), 1), by_kind={k: round(v, 2) for k, v in by.items()},
                cooling_limit_w=474.56, basis=DENS_BASIS)


# ------------------------------------------------------------------------------------------------ records
RESERVATION_KEYS = ('result_pin_bays', 'native_owner_bays', 'native_descriptor_bays', 'native_control_escape_bays',
                    'native_control_u_corridors', 'native_result_store_bays')   # the order build() extends reserved_regions
ROUTE_CORRIDOR_KEYS = {'native_control_escape_bays', 'native_control_u_corridors'}


def legality(m):
    return S.legality(dict(m, insts=m['insts'])) if False else _legality(m)


def _legality(m):
    grid = defaultdict(list)
    ov, out = [], []
    W, H = m['geo']['W'], m['geo']['H']
    for i, it in enumerate(m['insts']):
        x0, y0, x1, y1 = it.box()
        if x0 < -1e-6 or y0 < -1e-6 or x1 > W + 1e-6 or y1 > H + 1e-6:
            out.append(it.name)
        seen = set()
        for a in range(int(x0 // 200), int(x1 // 200) + 1):
            for b in range(int(y0 // 200), int(y1 // 200) + 1):
                for j in grid[(a, b)]:
                    if j in seen:
                        continue
                    seen.add(j)
                    o = m['insts'][j]
                    a0, b0, a1, b1 = o.box()
                    if a0 < x1 - 1e-6 and x0 < a1 - 1e-6 and b0 < y1 - 1e-6 and y0 < b1 - 1e-6:
                        ov.append((o.name, it.name))
                grid[(a, b)].append(i)
    # reserved regions (result pin / owner / descriptor / escape bays, U corridors, result stores) are obstacles too:
    # an instance or another reservation may not overlap one (the audit omitted them until 2026-10-07)
    rr = [tuple(b) for b in m.get('reserved_regions', [])]
    tags = [(k, r.get('sm')) for k in RESERVATION_KEYS for r in m.get(k, [])]
    if len(tags) != len(rr):
        tags = [(None, None)] * len(rr)
    rov = []
    for k, b in enumerate(rr):
        if b[0] < -1e-6 or b[1] < -1e-6 or b[2] > W + 1e-6 or b[3] > H + 1e-6:
            out.append(f'reserved[{k}]')
        for a in range(int(b[0] // 200), int(b[2] // 200) + 1):
            for c in range(int(b[1] // 200), int(b[3] // 200) + 1):
                for j in grid[(a, c)]:
                    a0, b0, a1, b1 = m['insts'][j].box()
                    if a0 < b[2] - 1e-6 and b[0] < a1 - 1e-6 and b0 < b[3] - 1e-6 and b[1] < b1 - 1e-6:
                        rov.append((m['insts'][j].name, f'reserved[{k}]'))
        for k2 in range(k + 1, len(rr)):
            e = rr[k2]
            if b[0] < e[2] - 1e-6 and e[0] < b[2] - 1e-6 and b[1] < e[3] - 1e-6 and e[1] < b[3] - 1e-6:
                (ka, sa), (kb, sb) = tags[k], tags[k2]
                if sa is not None and sa == sb and {ka, kb} & ROUTE_CORRIDOR_KEYS:
                    continue        # one SM's route corridor joining its own escape portal: a connected keep-out
                rov.append((f'reserved[{k}]', f'reserved[{k2}]'))
    rov = sorted(set(rov))
    return dict(instances=len(m['insts']), overlaps=len(ov) + len(rov), overlap_examples=(ov + rov)[:20],
                outside=len(out), outside_examples=out[:20], reserved_regions=len(rr), reserved_overlaps=len(rov),
                reserved_overlap_examples=rov[:20])


def write_def_floorplan(m, path):
    W, H = m['geo']['W'], m['geo']['H']
    o = {'R0': 'N', 'MY': 'FN', 'MX': 'FS', 'R180': 'S'}
    d = ['VERSION 5.8 ;', 'DIVIDERCHAR "/" ;', 'BUSBITCHARS "[]" ;', 'DESIGN hfd_die ;', 'UNITS DISTANCE MICRONS 1000 ;',
         f'DIEAREA ( 0 0 ) ( {round(W * 1000)} {round(H * 1000)} ) ;']
    regs = [(r['name'], r['rect']) for r in m['regions']]
    d.append(f'REGIONS {len(regs)} ;')
    for n, (a, b, c, e) in regs:
        d.append(f'- {n} ( {round(a * 1000)} {round(b * 1000)} ) ( {round(c * 1000)} {round(e * 1000)} ) + TYPE GUIDE ;')
    d += ['END REGIONS', f'COMPONENTS {len(m["insts"])} ;']
    for it in m['insts']:
        d.append(f'- {it.name} {it.master} + FIXED ( {round(it.x * 1000)} {round(it.y * 1000)} ) {o[it.orient]} ;')
    d += ['END COMPONENTS']
    if m.get('top_input_ports'):
        d.append(f'PINS {len(m["top_input_ports"])} ;')
        for name, pin in m['top_input_ports'].items():
            x, y = pin['center_um']; w, h = pin['size_um']
            d.append(f'- {name} + NET {name} + DIRECTION INPUT + USE {pin["use"]}'
                     f' + LAYER {pin["layer"]} ( {round(-w*500)} {round(-h*500)} )'
                     f' ( {round(w*500)} {round(h*500)} ) + FIXED ( {round(x*1000)} {round(y*1000)} ) N ;')
        d.append('END PINS')
    d += ['END DESIGN', '']
    Path(path).write_text('\n'.join(d))


def svg(m, path, scale=0.03):
    W, H = m['geo']['W'], m['geo']['H']
    s = scale
    col = dict(sm='#9ecae1', svc='#fdd0a2', phy='#756bb1', hub='#74c476', spine='#31a354', attn_tile='#fd8d3c',
               waypoint='#08519c', link='#fee391', serdes_slab='#fff7bc', host_slab='#fec44f')
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W * s:.0f}" height="{H * s:.0f}" viewBox="0 0 {W * s:.1f} {H * s:.1f}">',
         f'<rect width="{W * s:.1f}" height="{H * s:.1f}" fill="#fff" stroke="#000"/>']
    for r in m['regions']:
        a, b, c, e = r['rect']
        o.append(f'<rect x="{a * s:.1f}" y="{(H - e) * s:.1f}" width="{(c - a) * s:.1f}" height="{(e - b) * s:.1f}" '
                 f'fill="none" stroke="#e6550d" stroke-dasharray="4 2" stroke-width="0.6"/>')
    for it in m['insts']:
        o.append(f'<rect x="{it.x * s:.2f}" y="{(H - it.y - it.h) * s:.2f}" width="{max(it.w * s, 0.4):.2f}" '
                 f'height="{max(it.h * s, 0.4):.2f}" fill="{col.get(it.kind, "#ccc")}" stroke="#555" stroke-width="0.05"/>')
        if it.kind in ('hub', 'spine', 'svc', 'phy') or (it.kind == 'sm' and it.name in ('sm0',)):
            o.append(f'<text x="{(it.x + 30) * s:.1f}" y="{(H - it.y - it.h + 160) * s:.1f}" font-size="4">{it.name}</text>')
    o.append('</svg>\n')
    Path(path).write_text('\n'.join(o))


# FP-LINT (owner 2026-10-08): die relay margin -- every driver -> station / waypoint ... -> load chain against the SS
# reach (504 um) after the segment's priced wire stages (seg_stages), and no station on the far side of its driver.
MARGIN_RELAY_KINDS = ('stn', 'waypoint')


def pin_points(m, k=16, M=None):
    """Pin model of the die hop rule: pt(inst, port) -> die (x, y) of the centroid of the pins a bus endpoint lands on,
    from the masters' own pin plans (masters(m, k): generated faces, fixed slot pin plans, split / view records, and at
    k > 1 the real LEF macros as bundled masters on their real faces), mirrored with the instance orientation; None
    when the master carries no pin for that endpoint (a placeholder: fp_margin_lint.die_pin_hops flags the net as
    box-to-box).  The endpoint -> pin binding is write_netlist's."""
    M = masters(m, k) if M is None else M
    svc_phy_pins(M, m, k)
    pw = port_widths(m, k)
    by = {it.name: it for it in m['insts']}
    cen, real_c = {}, {}

    def master_pins(name):
        if name not in cen:
            d = cen[name] = defaultdict(dict)
            mst = M.get(name)
            if mst is not None:
                try:
                    rects = S.pin_rects(mst, k, {p_: pw.get((name, p_), 0) for p_ in mst.order})
                except ValueError:      # exact hardened rectangles are full-width k = 1 pins
                    rects = [r_ for sp_ in mst.ports.values() if sp_[0] == 'rects' for r_ in sp_[1]]
                for nm, _ly, (x0, y0, x1, y1) in rects:
                    mm = re.match(r'^(.*)\[(\d+)\]$', nm)
                    d[mm.group(1) if mm else nm][int(mm.group(2)) if mm else 0] = ((x0 + x1) / 2, (y0 + y1) / 2)
        return cen[name]

    def pt(inst, port):
        it = by.get(inst)
        if it is None:
            return None
        d = master_pins(it.master)
        bits = None
        if '@' in port and it.master not in REAL:
            bus = slice_port(port, k)
            if k == 1:
                bits = port_idx(port)
        elif '@' in port:
            bus = port_base(port)
            bits = port_idx(port) if k == 1 else sorted({i_ // k for i_ in port_idx(port)})
        else:
            bus = port
        pins = d.get(bus)
        if not pins and it.master in REAL and k > 1:
            # a real macro port the bundled model gives no pins (the PHY dfi rows): its real LEF pins, the slice's own
            rk = (it.master, bus, tuple(port_idx(port)) if '@' in port else None)
            if rk not in real_c:
                r_ = S.real_lef(REAL[it.master])
                nms = (real_ports(m).get(it.master) or {}).get(bus) or []
                if rk[2] is not None:
                    nms = [nms[i_] for i_ in rk[2] if i_ < len(nms)]
                bx_ = [r_['pins'][n_][1] for n_ in nms if n_ in r_['pins']]
                real_c[rk] = ((sum(b_[0] + b_[2] for b_ in bx_) / 2 / len(bx_), sum(b_[1] + b_[3] for b_ in bx_) / 2 / len(bx_),
                               r_['w'], r_['h']) if bx_ else None)
            if real_c[rk] is None:
                return None
            x, y, w_, h_ = real_c[rk]
            if it.orient in ('MY', 'R180'):
                x = w_ - x
            if it.orient in ('MX', 'R180'):
                y = h_ - y
            return (it.x + x, it.y + y)
        if not pins:
            return None
        ps = [pins[b_] for b_ in bits if b_ in pins] if bits else []
        ps = ps or list(pins.values())
        x, y = sum(q[0] for q in ps) / len(ps), sum(q[1] for q in ps) / len(ps)
        mst = M[it.master]
        if it.orient in ('MY', 'R180'):
            x = mst.w - x
        if it.orient in ('MX', 'R180'):
            y = mst.h - y
        return (it.x + x, it.y + y)
    return pt


def plan_dump(m, out):
    """die-timing classification inputs (owner 2026-10-13: classify failing endpoints by cause before fixing; the S81
    pilot's tools/s81/sta_path_classes.py): <out>/plan.json.gz = {insts: [[name, master, kind, x, y, w, h, orient]],
    hops: [[bus, class, bits, driver inst, port, load inst, port, um]]} with um = the pin-to-pin Manhattan length of
    that driver -> load pair (None: a placeholder end without pins), and <out>/clock_delivery.json = {tiles: {master:
    {view: real | hard_macro | relay | placeholder}}} (real = a LEF the die binds from a closed view)."""
    import gzip
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    P = pin_points(m, 16)
    by = {it.name: it for it in m['insts']}
    hops = []
    for bid, cls, bits, eps in m['buses']:
        ends = [e for e in eps if e[0] in by]
        if len(ends) < 2:
            continue
        q0 = P(*ends[0])
        for e in ends[1:]:
            q1 = P(*e)
            um = round(abs(q0[0] - q1[0]) + abs(q0[1] - q1[1]), 1) if q0 and q1 else None
            hops.append([bid, cls, bits, ends[0][0], port_base(ends[0][1]), e[0], port_base(e[1]), um])
    json.dump(dict(insts=[[it.name, it.master, it.kind, round(it.x, 3), round(it.y, 3), round(it.w, 3), round(it.h, 3), it.orient]
                          for it in m['insts']], hops=hops), gzip.open(out / 'plan.json.gz', 'wt'))
    tiles = {}
    for it in m['insts']:
        if it.master not in tiles:
            tiles[it.master] = dict(view='hard_macro' if it.kind in ('phy', 'serdes_slab') and it.master in REAL else
                                    'real' if it.master in REAL else
                                    'relay' if it.kind == 'waypoint' else 'placeholder', kind=it.kind)
    (out / 'clock_delivery.json').write_text(json.dumps(dict(tiles=tiles), indent=1) + '\n')
    return dict(plan=str(out / 'plan.json.gz'), hops=len(hops), masters=len(tiles),
                real_masters=sum(1 for t in tiles.values() if t['view'] == 'real'))


def pin_hop_lint(m, k=16, limit=20):
    """the die hop rule, pin to pin (owner 2026-10-13): fp_margin_lint.die_pin_hops on this die's own pin plans"""
    import fp_margin_lint as FPL
    return FPL.die_pin_hops(m['insts'], m['buses'], pin_points(m, k), relay_kinds=MARGIN_RELAY_KINDS, limit=limit)


def margin_lint(m, pins=True):
    """die relay lint.  reach: PIN TO PIN <= 500 um per die net (pin_hops; owner 2026-10-13), on the pin plans of the
    slots / views; the older box-to-box segment walk (504 um, instance box to nearest box point) stays as the relay
    chain test (far-side relays, placeholders) but is NOT the die rule: it read 0 on contract v12 while 2,000 data
    hops and 1,197 reset nets were over 500 um between pins.  pins=False: the box walk alone (superseded rounds)."""
    import fp_margin_lint as FPL
    phys_ = bool((m.get('variant') or {}).get('phys_relays'))     # hbmdie-1011: physical relays only, no budget credit
    out = FPL.die_margin(m['insts'], m['buses'], MARGIN_RELAY_KINDS, reach_um=SS_REACH_UM,
                         stages=(lambda bid, L: 0) if phys_ else (lambda bid, L: seg_stages(m, bid, L)),
                         edges=bool((m.get('variant') or {}).get('lane_stations')))   # R25GQ: per register segment
    out['reach_measure'] = 'box-to-box (instance box to nearest box point); the die rule is pin_hops'
    if pins:
        out['pin_hops'] = ph = pin_hop_lint(m)
        out['reach_violations_box'] = out['reach_violations']
        out['reach_violations'] = ph['hops_over']
        out['reach_measure'] = (f"pin-to-pin, {ph['reach_um']:g} um ({ph['box_to_box_nets']} nets with a pin-less "
                                f"placeholder end measured box-to-box, {ph['box_to_box_over']} of them over)")
        if ph['verdict'] == 'FAIL':
            out['verdict'] = 'FAIL'
    return out


def manhattan_paths(m):
    """Built-route length per critical path (sum of segment Manhattan lengths between consecutive endpoints)."""
    by = {it.name: it for it in m['insts']}
    bus = {b[0]: b for b in m['buses']}

    def c(it):
        return (it.x + it.w / 2, it.y + it.h / 2)

    def near(it, q):
        return (min(max(q[0], it.x), it.x + it.w), min(max(q[1], it.y), it.y + it.h))
    out = {}
    for p, ids in m['paths'].items():
        L, segs = 0.0, []
        for bid in ids:
            eps = bus[bid][3]
            A, Bb = by[eps[0][0]], by[eps[-1][0]]
            a, b = near(A, c(Bb)), near(Bb, c(A))
            a, b = near(A, b), near(Bb, a)
            ln = abs(a[0] - b[0]) + abs(a[1] - b[1])
            segs.append((bid, round(ln, 1)))
            L += ln
        out[p] = dict(segments=len(ids), um=round(L, 1),
                      stages_430=sum(seg_stages(m, b_, s_) for b_, s_ in segs if s_ > 0),
                      stages_504=sum(math.ceil(s_ / SS_REACH_UM) for _, s_ in segs if s_ > 0))
    return out


PATH_CLASSES = dict(
    weight='HBM -> SM weight stream (stream service -> SM d face)',
    xbcast='VM root -> SM activation multicast (x face)',
    result='SM -> SU result gather',
    control='cmdproc / issue -> SM control (start/op, arrive/release)',
    expert_req='router -> stream service (expert-fetch descriptor)',
    loader_mem='loader -> stream service (memory AXI + request; r25m RQ-ING-4)',
    loader_rsp='stream service -> loader (memory AXI + response; r25m RQ-ING-4)',
    kv='stream service -> attention tiles (KV rows)',
    ik='stream service -> index (index keys)',
    link='collective endpoint -> SerDes macro',
    hub_su_coll='SU -> collective endpoint',
    hub_coll_su='collective endpoint -> SU',
    host='loader -> host link',
    attn_q='VM -> attention tiles (query operand, r15 attn_rtl: chain + packet hops to the farthest tile)',
)


def path_class(p):
    for k in ('weight', 'xbcast', 'result', 'control', 'expert_req', 'kv', 'ik', 'link', 'host', 'attn_q', 'loader_mem',
              'loader_rsp'):
        if p.startswith(k + '_') or p == k:
            return k
    if p == 'hub_su_coll':
        return 'hub_su_coll'
    if p == 'hub_coll_su':
        return 'hub_coll_su'
    return None


def class_bounds(per_path):
    out = {}
    for p, v in per_path.items():
        c = path_class(p)
        if not c:
            continue
        e = out.setdefault(c, dict(paths=0, max_um=0.0, max_stages_430=0, max_stages_504=0, worst=None, what=PATH_CLASSES[c]))
        e['paths'] += 1
        if v['stages_430'] > e['max_stages_430'] or (v['stages_430'] == e['max_stages_430'] and v['um'] > e['max_um']):
            e['worst'] = p
        e['max_um'] = max(e['max_um'], v['um'])
        e['max_stages_430'] = max(e['max_stages_430'], v['stages_430'])
        e['max_stages_504'] = max(e['max_stages_504'], v['stages_504'])
    return out


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def plan_record(m):
    kinds, area = defaultdict(int), defaultdict(float)
    for it in m['insts']:
        kinds[it.kind] += 1
        pad = 0 if it.kind in ('phy', 'link') else SHAVE
        area[it.kind] += (it.w + pad) * (it.h + pad) / 1e6
    cls = defaultdict(lambda: dict(buses=0, wires=0))
    for bid, c, bits, eps in m['buses']:
        cls[c]['buses'] += 1
        cls[c]['wires'] += bits
    g = m['geo']
    mp = manhattan_paths(m)
    ledger = {k: dict(mm2=round(v[0], 4), grade=v[1], source=v[2]) for k, v in BLOCKS.items()}
    if 'attn_tile_w_um' in m['variant']:
        ledger['attn_tile'] = dict(mm2=area['attn_tile']/len(m['tiles']),
                                  grade='measured macro plus analytical route reservation',
                                  source='results/rtl/hbm_child_contract_20261005/model.json')
    else:
        ledger['attn_tile']['physical_fit'] = False
        ledger['attn_tile']['note'] = 'Historical 0.5mm2 slots fail measured m6h1 footprint; not current fit evidence.'
    placed = sum(area.values())
    return dict(
        schema='opentallas.hbm-accel-die-floorplan.v1', tool='tools/hbm_accel_die_fp.py', tool_sha256=sha('tools/hbm_accel_die_fp.py'),
        sources_sha256={p: sha(p) for p in (PHY_LEF, SERDES_LEF, UCIE_LEF, SNAP_LIB, SM_CTX, PORTMAP, MATCHED, QWEN,
                                            'tools/dsrom_s81_fulldie.py', 'tools/qwen_rom_fulldie.py')},
        die=dict(w_um=g['W'], h_um=g['H'], mm2=round(g['W'] * g['H'] / 1e6, 2), reticle_mm2=858.0,
                 reticle_margin_mm2=round(858.0 - g['W'] * g['H'] / 1e6, 1)),
        census=dict(sm=32, sm_per_stack=8, stacks=4, pcs_per_stack=32, attention_tiles=len(m['tiles']),
                    serdes_macros=len(m['links']), tu_ports=TU_PORTS, tu_flit_bits=TU_FLIT - 1),
        block_ledger=ledger, instances=dict(kinds), area_mm2_by_kind={k: round(v, 3) for k, v in area.items()},
        child_reservations=m.get('child_reservations'),
        placed_footprint_mm2=round(placed, 2), utilisation_of_die=round(placed / (g['W'] * g['H'] / 1e6), 3),
        geometry={k: (round(v, 3) if isinstance(v, float) else v) for k, v in g.items()},
        clock_domains=dict(stream_1p2='SM array, attention, index, collective endpoint, VM, cmdproc, router, waypoints '
                                      '(1.2 GHz, 0.833 ns)', serial_0p9='SU + fused chains, SFU, HC, quantisers (0.9 GHz '
                                      'by design, 1.2 GHz lever L2)', hbm='PHY + stream service (1.024 ns CK/2)',
                           link='SerDes / host (own clocks)',
                           regions=['4 SM groups (one region per group, <= 5.25 mm: 9.68 x 4.75 mm groups split in two '
                                    'column halves)', 'hub W (index + attention)', 'spine', 'hub E (SU/SFU/HC)',
                                    '4 stream services', 'link strips'],
                           crossings='async FIFOs at every svc <-> SM/hub boundary (hbm <-> stream), ratio CDC at SU/SFU/HC '
                                     '(0.9 <-> 1.2, 3:4), mesochronous FIFO at each group entry (x multicast, control) '
                                     'and at the spine side of each trunk'),
        bus_classes=dict(cls), manhattan_paths=mp, manhattan_class_bounds=class_bounds(mp),
        lever_area_mm2=dict(
            fused_su_chains=dict(mm2=BLOCKS['su_fused'][0], where='inside the SU quarters (hb_su_*)', grade='estimate'),
            expert_workgroup=dict(mm2=0.1, where='inside hb_router (descriptor + steering)', grade='estimate'),
            pipelined_issue=dict(mm2=BLOCKS['cmdproc'][0], where='hb_cmdproc (static program store + issue sequencer)',
                                 grade='estimate'),
            activation_multicast=dict(mm2=round(sum((i.w + SHAVE) * (i.h + SHAVE) for i in m['insts']
                                                    if i.master.startswith('hfd_mcast')) / 1e6
                                                + sum((i.w + SHAVE) * (i.h + SHAVE) for i in m['insts']
                                                      if i.master.startswith('hfd_stn') and '_xt_' in i.name) / 1e6, 4),
                                      where='multicast stations (one per SM column) + the x trunk stations', grade='sized: '
                                      '4 stages x bus width x 0.2916 um2 DFF at 0.6 utilisation')),
        power=die_power(m), pdn=pdn_plan(m), clock_region_list=clock_regions(m), notes=m['notes'], variant=m['variant'],
        clock_leaf_offsets=m.get('clock_leaf_offsets', []),
        generator_decisions=DECISIONS,
        **r15_record(m))


def r15_record(m):
    """r15: the lint-fix census (forwarded clocks, meso FIFO slices, station roles, clock / reset nets)."""
    if not m['variant'].get('fwd') and not m['variant'].get('clk_dom'):
        return {}
    meso = m.get('meso', [])
    fcl = m.get('fclk', {})
    by = defaultdict(lambda: dict(slices=0, fifo_bits=0, count=0))
    for x in meso:
        k = x['where'] if x['where'] != 'station' else f"station:{x['kind']}"
        by[k]['slices'] += x['slices']
        by[k]['fifo_bits'] += x['fifo_bits']
        by[k]['count'] += 1
    hub_area = sum(x['slices'] for x in meso if x['where'] != 'station') * MESO_UM2 / 1e6
    wp = [it for it in m['insts'] if it.kind == 'waypoint']
    fwd_slices = 0
    wpb = defaultdict(int)
    by_i = {it.name: it for it in m['insts']}
    for bid, cls, bits, eps in m['buses']:
        for inst, port in eps:
            if inst != 'TOP' and by_i[inst].kind == 'waypoint':
                wpb[inst] = max(wpb[inst], bits)
    fwd_slices = sum(4 * math.ceil(b / 512) for b in wpb.values())
    cks = {b[0]: len(b[3]) - 1 for b in m['buses'] if b[1] in ('clock_trunk', 'reset_tree')}
    return dict(r15_lint_fix=dict(
        source='results/rtl/die_top_lint_20261006/findings.json (H1-H13, TF1-TF7)',
        forwarded_links=dict(segments_with_fclk=len(fcl), fclk_wires=sum(a + b for _, a, b in fcl.values()),
                             ot_fwd_link_stage_W512_slices=fwd_slices,
                             basis='4 forwarded stages of the widest bus per station (station area = 4 x bus width DFF '
                                   'at 0.6 utilisation), one fclk per 512 b slice and direction'),
        meso_fifo=dict(W512_slices=sum(x['slices'] for x in meso), by_location=dict(by),
                       um2_per_slice=round(MESO_UM2, 1), area_in_stations='sized into the station abstracts',
                       area_in_receiving_blocks_mm2=round(hub_area, 4),
                       area_basis='ot_meso_fifo W512 D4 std-cell 4,842.31 um2 at 0.6 utilisation '
                                  '(results/uarch/meso_fifo_20261004)', list=meso),
        station_masters=dict(count=len({it.master for it in wp}), instances=len(wp), roles=m.get('station_roles')),
        clock_reset_nets=cks))


def write_sdc(path, m=None):
    if m is not None and m['variant'].get('clk_dom'):
        sdc_ = SDC_R15 if not m['variant'].get('ck_root') else \
            SDC_R15.replace('hb_coll/pll_', m['variant']['ck_root'] + '/pll_').replace('on hb_coll', 'on ' + m['variant']['ck_root'])
        Path(path).write_text(sdc_ + (vm8_fwd_clock_sdc() if m['variant'].get('vm8_fwd_clocks') else ''))
        return
    Path(path).write_text("""# HBM accelerator die clock domains (AGENTS.md clock domains), tools/hbm_accel_die_fp.py
create_clock -name clk_stream -period 0.833 [get_pins {hb_vm/ck sm*/ck hb_cmdproc/ck hb_coll/pll}]
create_clock -name clk_serial -period 1.111 [get_pins {hb_su_*/ck hb_sfu_*/ck hb_hc_*/ck hb_quant/ck}]
create_clock -name clk_hbm    -period 1.024 [get_pins {phy_*/clk svc_*/ck}]
set_clock_uncertainty -setup 0.060 [all_clocks]
set_clock_uncertainty -hold 0.025 [all_clocks]
# clock regions (no die-wide synchronous tree: 25.6 x 19.5 mm, qwen_rom_fulldie case d):
#   G{SW,SE,NW,NE}{w,e}  SM group halves (2 columns x 2 rows, <= 4.9 x 4.7 mm), one local tree each
#   HUB-C               centre column (spine + SU / SFU / HC quarters), HUB-Q{SW,SE,NW,NE} scan quadrants
#   SVC{SW,SE,NW,NE}    stream services (clk_hbm, PHY CK/2), STRIP-W/E link macros (own clocks)
# crossings (each a FIFO, never a timed single-cycle path):
#   M*  hub <-> group-half mesochronous FIFOs on every die-level trunk (x multicast, result gather, control, expert
#       request): 2 periods each (results/uarch/meso_fifo_20261004), charged once per hub <-> group traversal
#   H*  stream service (clk_hbm) -> SM weight lines / KV / index rows: async two-clock FIFOs inside the service
#   X*  SU / SFU / HC / quant (clk_serial) <-> hub stream: ratio CDC 3:4 (inside the SU's HUB_IN / HUB_OUT stages)
#   L*  endpoint <-> SerDes / host: plesiochronous at the link macro
set_clock_groups -asynchronous -group {clk_stream} -group {clk_serial} -group {clk_hbm}
""")


SDC_R15 = """# HBM accelerator die clock domains (AGENTS.md clock domains), tools/hbm_accel_die_fp.py r15 (clk_dom / fwd)
# one PLL output port per domain on hb_coll, ONE logical net per domain to every clocked block (CTS builds a tree per
# clock region from it); one reset net per domain (por_*)
create_clock -name clk_stream -period 0.833 [get_pins hb_coll/pll_stream]
create_clock -name clk_serial -period 1.111 [get_pins hb_coll/pll_serial]
create_clock -name clk_hbm    -period 1.024 [get_pins hb_coll/pll_hbm]
create_clock -name clk_link   -period 0.833 [get_pins hb_coll/pll_link]
set_clock_uncertainty -setup 0.060 [all_clocks]
set_clock_uncertainty -hold 0.025 [all_clocks]
# clock regions (no die-wide synchronous tree):
#   G{SW,SE,NW,NE}{w,e}  SM group halves (2 columns x 2 rows), one local tree each (SMs, multicast / control /
#                        gather stations of the half, row-1 weight meso stations, row-1 request launch stations)
#   HUB-C               centre column (spine + SU / SFU / HC quarters), HUB-Q{SW,SE,NW,NE} scan quadrants (tiles, index)
#   SVC{SW,SE,NW,NE}    stream services (clk_hbm, PHY CK/2), LINK (SerDes / UCIe parallel side, endpoint pclk)
# forwarded links (ot_fwd_link_stage, W512 slices): every chained segment carries its forwarded clocks (one per 512 b
#   slice and direction); a station's flops are clocked by the forwarded clock of its incoming segment, never by a
#   region tree; generated clocks follow the actual forwarded waveform (inverted per stage)
# crossings (each a FIFO, never a timed single-cycle path):
#   M*  forwarded -> region: ot_meso_fifo W512 D4 slices in the meso stations (multicast, control distribution,
#       gather arm entry, row-1 weight line end, link macro end) and inside the receiving hub blocks (cmdproc control
#       upstream, scan quadrant KV / index keys / query, endpoint link rx, loader host rx): 2 periods each,
#       charged once per traversal
#   H*  stream service (clk_hbm) <-> stream: async two-clock FIFOs inside the service
#   X*  SU / SFU / HC / quant (clk_serial) <-> hub stream: ratio CDC 3:4 (inside the SU's HUB_IN / HUB_OUT stages)
#   L*  endpoint core <-> pclk: inside ot_hbm_accel_tu_endpoint
set_clock_groups -asynchronous -group {clk_stream} -group {clk_serial} -group {clk_hbm} -group {clk_link}
"""


VM8_FACE_TILES = ('fe0', 'fe1', 'fe2', 'fe3', 'fw0', 'fw1', 'fw2', 'fw3')


def vm8_fwd_clock_ports(root=None):
    """{tile cell: [forwarded-clock output ports]} of the eight VM8 face tiles, read from the tile route SDC (the
    `set_false_path -to` lines of physical/ref_tile/vm_cp_<t>_cx/clock.sdc are the single source of the port list)"""
    root = Path(root) if root else Path(__file__).resolve().parents[1]
    out = {}
    for t in VM8_FACE_TILES:
        txt = (root / f'physical/ref_tile/vm_cp_{t}_cx/clock.sdc').read_text()
        ports = re.findall(r'^set_false_path -to \[get_ports \{([^}]+)\}\]', txt, re.M)
        assert ports, ('no forwarded-clock port in the tile SDC', t)
        out[f'vm_cp_{t}'] = ports
    return out


def vm8_fwd_clock_etm_arcs(root=None, corners=('tt', 'ff', 'ss')):
    """the tile ETMs must carry the ck -> forwarded-clock port arc AS A CLOCK ARC (one negative-unate combinational
    arc: ck rise -> port fall, ck fall -> port rise).  write_timing_model exports the port as data launched by ck (a
    rising_edge and a falling_edge group, half of whose tables are the other edge re-referenced across half a period);
    the die's inverted generated clock then reads a wrong latency on one edge or both (OpenSTA 2.6.0 on vm_cp_fe0 TT:
    rise 0.8 ps, fall -251.7 ps; as a clock arc 175.3 / 168.9 = the routed insertion).  tools/hier_contract/
    fclk_arc_fix.py rewrites the export.  Returns {cell: {port: {corner: state}}}, state = 'clock_arc' (right),
    'data_arcs' (the raw export), 'other', or None (no arc from ck: the insertion is hidden from die timing)."""
    root = Path(root) if root else Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(Path(__file__).resolve().parent / 'hier_contract'))
    import fclk_arc_fix as FA
    out = {}
    for cell, ports in vm8_fwd_clock_ports(root).items():
        out[cell] = {p: {} for p in ports}
        for c in corners:
            lib = root / f'physical/ref_tile/{cell}_cx/views/{cell}/{cell}_{c}.lib'
            txt = lib.read_text() if lib.exists() else ''
            for p in ports:
                st = FA.arc_state(txt, p)
                out[cell][p][c] = None if st == 'missing' else st
    return out


def vm8_fwd_clock_sdc(root=None):
    """die SDC section (coordinator decision 10-13, FACE2): each VM8 face tile forwards ~ck on its fclk ports
    (ot_fwd_clk_inv at the face).  The TILE SDC false-paths those ports (they are clocks, not data; closed tiles
    stand), so the DIE defines each as a generated clock of the tile's own clock pin -- its latency is then the tile
    ETM's ck -> port arc, i.e. the tile's routed insertion -- and every receiver that captures with it is timed against
    it through the die net.  Instances are found by cell, so the section holds for any hierarchy the die top uses."""
    o = ['', '# ---- VM8 forwarded clocks (generated clocks; form of physical/rom_clock/fwd_hop2.sdc)',
         '# tile SDC: set_false_path -to <fclk ports> (data budget does not apply); tile ETM: the ck -> port arc is KEPT',
         '# (tools/hbm_accel_die_fp.py vm8_fwd_clock_etm_arcs checks every corner); the receiving capture flops are',
         '# clocked by the die net of the port, so they are referenced to the generated clock by propagation.',
         'set vm8_fck {}']
    for cell, ports in vm8_fwd_clock_ports(root).items():
        # OpenSTA / OpenROAD: get_cells returns a Tcl list (there is no foreach_in_collection)
        o.append(f'foreach vm8_c [get_cells -quiet -hierarchical -filter "ref_name == {cell}"] {{')
        o.append('  set vm8_n [get_full_name $vm8_c]')
        o.append('  foreach vm8_p {' + ' '.join('{' + p + '}' for p in ports) + '} {')
        o.append('    set vm8_k fck_[string map {/ _ . _ [ _ ] ""} ${vm8_n}_${vm8_p}]')
        o.append('    create_generated_clock -name $vm8_k -source [get_pins ${vm8_n}/ck] -divide_by 1 -invert '
                 '[get_pins [format {%s/%s} $vm8_n $vm8_p]]')
        o.append('    lappend vm8_fck $vm8_k')
        o.append('  }')
        o.append('}')
    o += ['# the forwarded clocks are synchronous to clk_stream (their master) and to each other; cut only to the others',
          'if {[llength $vm8_fck]} {',
          '  set_clock_groups -asynchronous -name vm8_fwd -group [get_clocks $vm8_fck] -group {clk_serial clk_hbm clk_link}',
          '  set_clock_uncertainty -setup 0.060 [get_clocks $vm8_fck]',
          '  set_clock_uncertainty -hold 0.025 [get_clocks $vm8_fck]',
          '}', '']
    return '\n'.join(o)


def pdn_plan(m, cov=None):
    cov = cov or COV
    vp = S.BUMP_PITCH / math.sqrt(0.5)

    def pitch(c):
        raw = dn(0.48 / c, 0.160)
        n = math.ceil(vp / raw - 1e-9)
        n += (n % 2 == 0)
        return round(vp / n, 4)
    return dict(
        layers='M8 (horizontal) / M9 (vertical) straps, 0.48 um, VDD/VSS interleaved half a pitch, aligned to the bump '
               'columns; via89 at every same-net crossing; macro M7 grids (element sign-off) join the die grid',
        coverage_per_net=cov, strap_pitch_um={k: pitch(v) for k, v in cov.items()},
        bumps=dict(array_pitch_um=S.BUMP_PITCH, vdd_vss_pitch_um=round(vp, 2), size_um=S.BUMP_SIZE,
                   scheme='every core bump a power bump (VDD/VSS interleaved); PHY and link strips carry signal bumps'),
        supply_v=S.VDD_V, budget_mv_rail_to_rail=35.0,
        grt_reservation='M8/M9 GRT layer adjustment 0.05 + 2 x coverage per region (the routing the straps take)',
        ir_method='PSM on every 2.6 x 2.6 mm window of the die (88 windows, overlapping by two bump pitches so the '
                  'window interiors tile the die), 20 um load cells at the peak in-phase densities')


def clock_regions(m):
    out = [dict(r) for r in m.get('region_extra', [])]     # r17: station rects of a named region, matched first
    for st, G in m['groups'].items():
        retiled = bool(m['variant'].get('sm_physical_grid'))
        if retiled:
            # hbm-forks 2026-10-09 (SM-group clock distribution for the 3 x 3 retile): ONE region per SM group covering
            # the whole group rect (SM sites + the column / row channels, so the x / result / control tree stations in
            # the channels are inside it).  The clock plan splits it at the median into <= 4 mm sub-regions G<st>.k,
            # which share ONE family root at the group centre (clock_plan.clock_nets: fk = G<st>): a common trunk down
            # to the group and a balanced sub-tree per sub-region (the planned root pads equalise their insertion).
            g_ = m['geo']
            x0, y0 = G['x'], G['y']
            x1, y1 = x0 + g_['grp_w'], y0 + g_['grp_h']
            out.append(dict(name=f'G{st}', clock='clk_stream', rect=[round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)],
                            extent_um=round(max(x1 - x0, y1 - y0), 1), sms=[s.name for s in G['sms']]))
            continue
        cuts = [('w', (0, 1)), ('e', (2, 3))]
        for h, cols in cuts:
            ss = [s for s in G['sms'] if s.sm['physical_col' if retiled else 'col'] in cols]
            x0 = min(s.x for s in ss)
            y0 = min(s.y for s in ss)
            x1 = max(s.x + s.w for s in ss)
            y1 = max(s.y + s.h for s in ss)
            out.append(dict(name=f'G{st}{h}', clock='clk_stream', rect=[round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)],
                            extent_um=round(max(x1 - x0, y1 - y0), 1), sms=[s.name for s in ss]))
    hb = m['hub']
    sp_ = (('loader', 'router', 'cmdproc') + (('barrier',) if m['variant'].get('barrier_low') else ())
           if m['variant'].get('spine_region') else ())
    if sp_:     # r17: loader + router + cmdproc in one region (their sync nets stayed inside one tree cut); listed
        #         before HUB-C, whose rect contains them (sink_regions takes the first rect holding a sink)
        sp = [hb[k] for k in sp_]
        out.append(dict(name='HUB-SP', clock='clk_stream', rect=[round(min(i.x for i in sp), 1), round(min(i.y for i in sp), 1),
                        round(max(i.x + i.w for i in sp), 1), round(max(i.y + i.h for i in sp), 1)]))
        # HUB-V: the VM and the clocked stations at its faces (iv meso FIFOs, vr first station, x / query trunk roots)
        # in one region: the plan's median cut of HUB-C put the VM and its west-channel stations in two cuts (197 ps)
        vm = hb['vm']
        xs = [it for it in m['insts'] if it.kind == 'waypoint' and it.name in m.get('clocked', {})
              and vm.y - 900.0 <= it.y <= vm.y + vm.h and vm.x - 1100.0 <= it.x <= vm.x + vm.w + 1100.0]
        bx = [vm] + xs
        out.append(dict(name='HUB-V', clock='clk_stream', rect=[round(min(i.x for i in bx) - 1, 1), round(min(i.y for i in bx) - 1, 1),
                        round(max(i.x + i.w for i in bx) + 1, 1), round(max(i.y + i.h for i in bx) + 1, 1)]))
    cen = [hb[k] for k in hb if not k.startswith('index_') and k not in sp_]
    out.append(dict(name='HUB-C', clock='clk_stream + clk_serial', rect=[round(min(i.x for i in cen), 1), round(min(i.y for i in cen), 1),
                    round(max(i.x + i.w for i in cen), 1), round(max(i.y + i.h for i in cen), 1)]))
    for r in m['regions']:
        if r['name'].startswith('scan_'):
            out.append(dict(name='HUB-Q' + r['name'][5:], clock='clk_stream', rect=[round(v, 1) for v in r['rect']],
                            extent_um=round(max(r['rect'][2] - r['rect'][0], r['rect'][3] - r['rect'][1]), 1)))
        if r['name'].startswith('svc_'):
            out.append(dict(name='SVC' + r['name'][4:], clock='clk_hbm', rect=[round(v, 1) for v in r['rect']]))
    return out


# ------------------------------------------------------------------------------------------------ cases
def case_real(m, work):
    work.mkdir(parents=True, exist_ok=True)
    npins = write_lefs(m, 1, work / 'elements.lef')
    _init_real()
    for rel, nm in ((PHY_LEF, 'phy.lef'), (SERDES_LEF, 'serdes.lef'), (UCIE_LEF, 'ucie.lef')):
        (work / nm).write_text(S._lef_text(rel))
    if m['variant'].get('host_bb'):      # host PHY black box macro appended to the link LEF the case already reads
        ht = S._lef_text(HOST_LEF)
        body = ht[ht.index('MACRO '):ht.rindex('END LIBRARY')]
        ut = (work / 'ucie.lef').read_text()
        (work / 'ucie.lef').write_text(ut[:ut.rindex('END LIBRARY')] + body + 'END LIBRARY\n')
    (work / 'snap.tcl').write_text((ROOT / SNAP_LIB).read_text())
    write_netlist(m, 1, work / 'die.v')
    W, H = m['geo']['W'], m['geo']['H']
    src = (ROOT / 'tools/dsrom_s81_fulldie.py').read_text()
    pl_head = re.search(r"pl = \['set _blk.*?placed \(%\.3f, %\.3f\)\" \$nm \[\$m getName\] \$o \$x \$y \$px \$py\] \} \}'\]",
                        src, re.S)
    assert pl_head
    pl = eval(pl_head.group(0)[5:])          # the S81 snap-only placer (fplace)
    pl += [f'fplace {it.name} {it.x:.3f} {it.y:.3f} {it.orient}' for it in m['insts']]
    (work / 'place.tcl').write_text('\n'.join(pl) + '\n')
    tcl = S.case_real.__code__  # noqa: F841  (the tcl body below is the S81 case (a) with this die's files)
    body = f"""# case (a): HBM accelerator die floorplan, macro legality, on-track assert, pin access
proc mem {{tag}} {{ set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {{VmRSS:\\s+(\\d+)}} $s -> r; puts "OTMEM $tag [expr {{$r/1024}}] MB [clock seconds]" }}
read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f {{phy.lef serdes.lef ucie.lef elements.lef}} {{ read_lef /work/$f }}
read_verilog /work/die.v
link_design hfd_die
initialize_floorplan -die_area {{0 0 {W:.3f} {H:.3f}}} -core_area {{0 0 {W:.3f} {H:.3f}}} -site asap7sc7p5t
source {PLAT}/openRoad/make_tracks.tcl
set ::env(MAKE_TRACKS) {PLAT}/openRoad/make_tracks.tcl
source /work/snap.tcl
set t0 [clock seconds]
source /work/place.tcl
puts "OT_TIME place_s=[expr {{[clock seconds]-$t0}}]"
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
if {{[catch {{ot_mts::assert_on_track -label hbmaccdie}} err]}} {{ puts "OT_ASSERT FAIL $err" }} else {{ puts "OT_ASSERT PASS" }}
set t0 [clock seconds]
set_routing_layers -signal M2-M9
if {{[catch {{pin_access -verbose 1}} err]}} {{ puts "OT_PA FAIL $err" }} else {{ puts "OT_PA DONE" }}
puts "OT_TIME pa_s=[expr {{[clock seconds]-$t0}}]"
mem pa
"""
    (work / 'run.tcl').write_text(body)
    man = dict(case='a', instances=len(m['insts']), generated_pins=npins, nets_bits=sum(b[2] for b in m['buses']),
               variant=m['variant'])
    (work / 'manifest.json').write_text(json.dumps(_jsonable(man), indent=1))
    return man


VIA_OBS = S.VIA_OBS
COV = dict(field=0.0878, hub=0.0878, spine=0.0878, svc=0.1639, channel=0.0878)   # r2: 2 x the Qwen r2 field class (r1 at 0.0439 failed the top-row windows, 41.45 mV)


def case_grt(m, work, k, tag, iters, cov, empty=False, win=None, m45=None):
    """win (x0, y0, x1, y1) um: a WINDOWED experiment GRT (hbm-die-iter 10-12): the whole die is placed (every block
    keeps its OBS), but only the die nets whose endpoint bounding box crosses the window are routed, so a hub
    restructuring is compared on its window overflow in ~1/10 of a full run.  Never a run of record.
    m45: channel capacity of M4 / M5 (adjustment; None = the M2-M5 1.0 die-wide block of record).  M2 / M3 stay 1.0
    (relay / station cells and rails), every block keeps M2-M5 at 1.0 by a region adjustment over its outline, and the
    channels between blocks keep m45 of M4 / M5 for the PDN stripes and relay pin access."""
    from chip_assembly import v41_die as VD
    work.mkdir(parents=True, exist_ok=True)
    npins = write_lefs(m, k, work / 'elements.lef')
    (work / 'tech.lef').write_text(VD.bundled_tech_lef(k))
    mm = dict(m)
    if empty:
        mm['buses'] = [next(b_ for b_ in m['buses'] if b_[1] == 'clock_trunk')]
    if win:
        byn = {it.name: it for it in m['insts']}

        def _hit(b_):
            pts = [(byn[i_].x + byn[i_].w / 2, byn[i_].y + byn[i_].h / 2) for i_, _ in b_[3] if i_ != 'TOP']
            if not pts:
                return False
            return (min(x for x, _ in pts) <= win[2] and max(x for x, _ in pts) >= win[0]
                    and min(y for _, y in pts) <= win[3] and max(y for _, y in pts) >= win[1])
        mm['buses'] = [b_ for b_ in mm['buses'] if _hit(b_)]
    write_netlist(mm, k, work / 'die.v')
    W, H = m['geo']['W'], m['geo']['H']
    tracks = [f'make_tracks {n} -x_offset {off * k:.3f} -x_pitch {p * k:.3f} -y_offset {off * k:.3f} -y_pitch {p * k:.3f}'
              for n, d, p, wd, sp, off in VD.ASAP7_LAYERS]
    place = [f'place_inst -name {it.name} -location {{{it.x:.3f} {it.y:.3f}}} -orientation {it.orient} -status FIRM'
             for it in m['insts']]
    adj = []
    for ln in ('M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 'M9'):
        a = 1.0 if ln in ('M2', 'M3', 'M4', 'M5') else (VIA_OBS + 2 * cov['field'] if ln in ('M8', 'M9') else VIA_OBS)
        if m45 is not None and ln in ('M4', 'M5'):
            a = m45
        adj.append(f'set_global_routing_layer_adjustment {ln} {a:.4f}')
    if m45 is not None:
        for it in m['insts']:
            if it.kind == 'waypoint':
                continue
            for ln in ('M4', 'M5'):
                adj.append(f'set_global_routing_region_adjustment {{{it.x:.3f} {it.y:.3f} {it.x + it.w:.3f} '
                           f'{it.y + it.h:.3f}}} -layer {ln} -adjustment 1.0')
    for r in m['regions']:
        c = cov.get(r['kind'])
        if c is None or r['kind'] == 'field':
            continue
        x0, y0, x1, y1 = r['rect']
        for ln in ('M8', 'M9'):
            adj.append(f'set_global_routing_region_adjustment {{{x0:.3f} {y0:.3f} {x1:.3f} {y1:.3f}}} -layer {ln} '
                       f'-adjustment {VIA_OBS + 2 * c:.4f}')
    src = (ROOT / 'tools/dsrom_s81_fulldie.py').read_text()
    gtail = re.search(r'tcl \+= r"""\n(set blk \[ord::get_db_block\].*?mem done\n)"""', src, re.S).group(1)
    tcl = f"""# case (b): bundled (k = {k}) global route of every HBM accelerator die-level net{' (EMPTY baseline)' if empty else ''}
proc mem {{tag}} {{ set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {{VmRSS:\\s+(\\d+)}} $s -> r; puts "OTMEM $tag [expr {{$r/1024}}] MB [clock seconds]" }}
read_lef /work/tech.lef
read_lef /work/elements.lef
read_verilog /work/die.v
link_design hfd_die
initialize_floorplan -die_area {{0 0 {W:.3f} {H:.3f}}} -core_area {{0 0 {W:.3f} {H:.3f}}} -site bsite
{chr(10).join(tracks)}
{chr(10).join(place)}
{chr(10).join(adj)}
set_routing_layers -signal M2-M9
set t0 [clock seconds]
global_route -verbose -allow_congestion -congestion_iterations {iters} -congestion_report_file /work/grt_congestion.rpt
puts "OT_TIME grt_s=[expr {{[clock seconds]-$t0}}]"
mem grt
report_wire_length -net * -global_route -file /work/wirelength.csv
""" + gtail
    (work / 'run.tcl').write_text(tcl)
    man = dict(case='b', tag=tag, bundle_k=k, congestion_iterations=iters, empty_baseline=empty, window=win, m45=m45,
               instances=len(m['insts']), bundle_pins=npins,
               bundle_nets=0 if empty else sum(max(1, math.ceil(b[2] / k)) for b in mm['buses']),
               wires=0 if empty else sum(b[2] for b in mm['buses']), coverage=cov, variant=m['variant'])
    (work / 'manifest.json').write_text(json.dumps(_jsonable(man), indent=1))
    return man


# ---- IR: every window of the die (tiled with one-bump-pitch overlaps so that the window interiors cover the die)
IR_WIN = 2600.0


def ir_windows(m):
    """Every window of the die, origins on the die-anchored bump lattice (VDD/VSS pitch), overlapping by more than two
    bump pitches so the window interiors (one pitch in from each window edge) tile the whole die; the last column /
    row extends to the die edge."""
    W, H = m['geo']['W'], m['geo']['H']
    vp = S.BUMP_PITCH / math.sqrt(0.5)
    step = math.floor((IR_WIN - 2 * vp - 4.0) / vp) * vp
    xs = [0.0]
    while xs[-1] + IR_WIN < W:
        xs.append(xs[-1] + step)
    ys = [0.0]
    while ys[-1] + IR_WIN < H:
        ys.append(ys[-1] + step)
    out = {}
    for j, y0 in enumerate(ys):
        for i, x0 in enumerate(xs):
            x1 = W if i == len(xs) - 1 else x0 + IR_WIN
            y1 = H if j == len(ys) - 1 else y0 + IR_WIN
            out[f'w{i:02d}_{j:02d}'] = (round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3))
    return out


def _s_adapter(m):
    """Present this die to S.case_ir (geometry, power, kind map) without touching S's globals beyond DIE."""
    S.DIE = (m['geo']['W'], m['geo']['H'])
    S.inst_power = inst_power
    S.PG_M8_MASTERS = set((m.get('variant') or {}).get('pg_m8_masters', ()))   # hbmdie-1011: M8 PG pins (hfd_hc)

    def kind_at(_m, x, y):
        for it in m['insts']:
            if it.kind in ('phy', 'link', 'serdes_slab', 'host_slab') and it.x <= x < it.x + it.w and it.y <= y < it.y + it.h:
                return 'phy'
        for r in m['regions']:
            a, b, c, e = r['rect']
            if a <= x < c and b <= y < e:
                return {'svc': 'svc', 'hub': 'hub'}.get(r['kind'], 'field')
        return 'field'
    S.kind_at = kind_at
    S.windows = lambda _m: ir_windows(m)


def case_ir(m, work, window, cov):
    _s_adapter(m)
    meta = S.case_ir(m, work, window, cov, peak=True, vdd_pitch=None, align=True, signal_bumps_phy=True)
    return meta


B2_TAP8 = (('rdn', 2065), ('wdn', 17), ('rup', 129), ('wup', 2241))      # one 8-lane client tap (32-lane 8,257/65/513/8,961)
B2_CHAIN8 = (('rdn', 2067), ('wdn', 19), ('rup', 131), ('wup', 2243))    # one 8-lane chain hop (32-lane 8,259/67/515/8,963)


def b2_nets(vb2):
    """hbm-b2 (SPEC results/arch/hbm_b2_1012/SPEC.md): the die nets of the quadrant VM slices other than the local lane
    groups (lane_stations): ring links, COLL broadcast tree, central-unit ring-client taps, SM x-load to the quadrant VM8,
    HC aperture per quarter"""
    out = []
    for a_, b_ in vb2['ring']:      # 2 x 2 ring, one link each way: {v, credit, op 4, word 17, data 2,048, tag 8, ...}
        for s_, d_ in ((a_, b_), (b_, a_)):
            out.append((f'vring_{s_}_{d_}', 'hub', vb2['ring_bits'], (f'hb_vms_{s_}', f't_ring_{d_}'), (f'hb_vms_{d_}', f'f_ring_{s_}')))
            out.append((f'vring_{s_}_{d_}_c', 'hub', 4, (f'hb_vms_{d_}', f't_ringc_{s_}'), (f'hb_vms_{s_}', f'f_ringc_{d_}')))
    for s_, d_ in vb2['coll_tree']:  # COLL result broadcast (replaces hgi_vmw2_coll 8,961 b)
        sn_ = 'hb_coll' if s_ == 'coll' else f'hb_vms_{s_}'
        out.append((f'vcb_{s_}_{d_}', 'hub', vb2['coll_bits'], (sn_, 't_vcb' if s_ == 'coll' else f't_vcb_{d_}'), (f'hb_vms_{d_}', 'f_vcb')))
        out.append((f'vcb_{s_}_{d_}_c', 'hub', 2, (f'hb_vms_{d_}', 't_vcbc'), (sn_, f'f_vcbc_{d_}')))
    for cl_, tg_, q_ in vb2['clients']:     # central units: 8-lane ring-client taps at one slice's ring stop
        for suf_, bits_ in B2_TAP8:
            dn_ = suf_.endswith('dn')
            a_ = (f'hb_vms_{q_}', f't_rc{tg_}_{suf_}') if dn_ else (cl_, f't_rc{tg_}_{suf_}')
            b_ = (cl_, f'f_rc{tg_}_{suf_}') if dn_ else (f'hb_vms_{q_}', f'f_rc{tg_}_{suf_}')
            out.append((f'vrc_{tg_}_{suf_}', 'hub', bits_, a_, b_))
    for q_ in vb2['xy']:
        if vb2.get('xload'):    # SM.MATVEC x load: slice q -> its quadrant VM8 (hb_vm_<q>), read half of a tap
            out.append((f'vxl_{q_}', 'hub', 2065, (f'hb_vms_{q_}', 't_xl_rdn'), (f'hb_vm_{q_.lower()}', 'f_xl_rdn')))
            out.append((f'vxl_{q_}_r', 'hub', 129, (f'hb_vm_{q_.lower()}', 't_xl_rup'), (f'hb_vms_{q_}', 'f_xl_rup')))
        if vb2.get('vmap'):     # HC x lanes a quarter: v0.6 556 + 4 (2 x 278); SPEC v0.7 vmap_bits 1,200 + 16 (8 x 150 b, cr / done)
            out.append((f'vmap_{q_}', 'hub', vb2.get('vmap_bits', 556), (f'hb_vms_{q_}', 't_hgi_vmap'), (f'hb_hc_{q_}', 'f_hgi_vmap')))
            out.append((f'vmap_{q_}_r', 'hub', vb2.get('vmap_r_bits', 4), (f'hb_hc_{q_}', 't_hgi_vmap'), (f'hb_vms_{q_}', 'f_hgi_vmap')))
    return out


def r25gq_b2():
    """hbm-b2 10-12: B2 = contract v8 with the VM split into 4 quadrant slices (STUDY hbm_die_phy_study_1012)"""
    v = dict(R25GQ, r25gq_net=True, **dict(R25GQ_PR, **R25GQ_V8))
    sw_ = (13400.0, 9000.0); se_ = (17770.0, 9000.0); nw_ = (13400.0, 15200.0); ne_ = (17770.0, 15200.0)
    st_ = lambda q, fs: dict(src=f'hb_vms_{q}', thick=64.8, gap=21.6, stations=tuple(
        (f'hb_stn_lg{q}_{c}', f'hb_{c}_{q}', f_, 1036.8) for c, f_ in fs))
    v.update(
        drop_blocks=tuple(v['drop_blocks']) + ('hb_hgi_vm',),
        drop_buses=v['drop_buses'] + r'|hgi_vmw2_coll\w*',
        vmw_dma=False, vmr2_dma=False, vmap=False,
        lane_stations=dict(
            SW=st_('SW', (('su', 'E'), ('sfu', 'N'), ('hc', 'N'))), SE=st_('SE', (('su', 'W'), ('sfu', 'S'), ('hc', 'S'))),
            NW=st_('NW', (('su', 'E'), ('sfu', 'S'), ('hc', 'S'))), NE=st_('NE', (('su', 'W'), ('sfu', 'N'), ('hc', 'N')))),
        dense_face_masters=tuple(m_ for m_ in v['dense_face_masters'] if not m_.startswith(('hfd_hgi_vm', 'hfd_stn_lgE', 'hfd_stn_lgW')))
        + tuple(f'hfd_hgi_vms_{q}' for q in ('SW', 'SE', 'NW', 'NE')) + tuple(f'hfd_stn_lg{q}{k}' for q in ('SW', 'SE', 'NW', 'NE') for k in range(3)),
        vm_b2=dict(xy=dict(SW=sw_, SE=se_, NW=nw_, NE=ne_), wh=(950.4, 1684.8),
                   ring=(('SW', 'NW'), ('SE', 'NE'), ('SW', 'SE'), ('NW', 'NE')), ring_bits=2148,
                   coll_tree=(('coll', 'SW'), ('coll', 'SE'), ('SW', 'NW'), ('SE', 'NE')), coll_bits=1088,
                   clients=(('hb_cmdproc', 'cp', 'NW'), ('hb_cmdproc', 'att', 'NE'), ('hb_quant', 'q', 'NW'), ('hb_hc_eng', 'hce', 'SE')),
                   xload=True, vmap=True))
    for q in ('SW', 'SE', 'NW', 'NE'):
        v[f'lane_chain_nets_{q}'] = B2_CHAIN8
        v[f'lane_tap_nets_{q}'] = B2_TAP8
    v['face_force'] = {k: f for k, f in v['face_force'].items() if k[0] != 'hfd_hgi_vm'}
    # chain ports of each station on its long outer face (the su bank faces its slice; sfu / hc banks their outer face)
    for q, (f0, f1, f2) in dict(SW=('E', 'N', 'N'), SE=('W', 'S', 'S'), NW=('E', 'S', 'S'), NE=('W', 'N', 'N')).items():
        # E side: hc_eng fills the SFU-N / SFU-S channels, so the E chains run su(W) -> sfu(S/N, the su|sfu gap) -> hc(S/N, its outer face; the sfu|hc column stays free for the link clock tree)
        for k, f_ in ((0, f0), (1, f1), (2, f2)):
            for suf, _ in B2_CHAIN8:
                for d_ in ('t', 'f'):
                    v['face_force'][(f'hfd_stn_lg{q}{k}', f'{d_}_lg{q}_{suf}')] = f_
    return v
def r25gq_v10():
    """contract v10 (hbmdie 10-12) = B2 (r25gqn_b2) + SPEC v0.7 HC x lanes (vmap 1,200 + 16 b a quarter) + ONE hfd_hc
    master for all four quarters: the local-group tap is one port set f_lgc_rdn / f_lgc_wdn / t_lgc_rup / t_lgc_wup on the
    master N face, and the E quarters are placed SE R180 / NE MY (was MY / R180) so that face meets each station (W
    quarters: equator side; E quarters: outer side, hc_eng holds the equator channel); vmap stays on the master E face
    = the face toward the quarter's slice for every orient."""
    v = r25gq_b2()
    v['vm_b2'] = dict(v['vm_b2'], vmap_bits=1200, vmap_r_bits=16)
    v['hc_orient'] = dict(SE='R180', NE='MY')
    v['lane_tap_generic'] = tuple(f'hb_hc_{q}' for q in ('SW', 'SE', 'NW', 'NE'))
    return v


def r25gq_v10_hclegal():
    """Placement successor preserving the closed HC master: use only R0/MY.

    In nanometers, M4 pins need y=0 mod48 in R0, while M6 needs
    y=0 mod64. A y mirror requires y=24 mod48 and y=0 mod64,
    whose residues disagree mod16. MX/R180 therefore have no legal origin.
    Move the SE/NW tap stations to the master's physical N face and
    rebuild all die relays; the v10 routed/clock case is not reusable.
    """
    v = r25gq_v10()
    v['hc_orient'] = dict(SW='R0', SE='MY', NW='R0', NE='MY')
    v['hc_track_origins'] = True
    v['tree_cap'] = True        # 10-13: capacity-aware clock / reset tree routing (see TREE_WIDE_UM)
    v['lane_stations'] = {
        q: dict(cfg, stations=tuple(
            (st[0], st[1], 'N', *st[3:]) if st[1] == f'hb_hc_{q}' else st
            for st in cfg['stations']))
        for q, cfg in v['lane_stations'].items()}
    v['face_force'] = dict(v['face_force'])
    for q in ('SE', 'NW'):
        for suf, _ in B2_CHAIN8:
            for d in ('t', 'f'):
                v['face_force'][(f'hfd_stn_lg{q}2', f'{d}_lg{q}_{suf}')] = 'N'
    return v


def r25gq_v12():
    """contract v12 (hbmdie 10-13) = v10_hclegal + the slots granted on 10-13.

    * hb_coll stays 1,560 um tall.  The first v12 grew it 2,030 um into the void the dropped central VM left in the
      spine column: with the void closed the N link chains lost a station site (1 data segment 1.7-2.1 mm) and the clock
      / reset trees doubled their depth (189-275 stages, base 77-143).  The void is the spine's E-W crossing: it stays.
    * hb_tkm (hfd_coll_tkm): the collective TKM cluster, 32 x ot_hgi_coll_tkm_tile + its sequencer strip.  The closed
      tile is 300.24 um square (the 2.2 x 1.1 mm request assumed 252 um), so the cluster is 2,255.04 x 1,844.64 (6 x 6
      sites + a 302-um strip, 4.16 mm2).  It fits neither hb_coll nor the void (28 tiles), and beside the spine it
      walls a slice off: in the W column between the SW and NW slices it left 20 data segments and 230 tree hops
      over the reach (lane-group banks found no site).  It goes to the empty band of the NW HC column (x 8,449-11,173,
      y 16,150-18,250: 6 stations today), 7.6 mm from hb_coll: ~18 relay stages each way on the cluster's stream
      ports (del_flit 4 x 545 down, w_data up), latency once an operation, recorded, never re-priced.
    * hb_dbk_<q> (ot_hgi_dma_back, closed leaf 293.76 sq, W pins M4 + M6 -> R0 / MY only): one beside each slice, in
      the slice | spine gap (W quadrants) / W of the slice (E quadrants); N = the slice's 8-lane read group, W = the
      move bus of the cluster's b2_dma_q endpoint, S = wd 8 x 289 + cr 8 + ack 4 to the stack's stream service (ECO
      pins wd / wdc on svc band 3, on the loader-memory route).
    * hb_quant 358.56 -> 648.0 tall for the QDQ cluster (622.08 x 596.16, child slot at its W end, W face toward the
      NW slice); the 289.44 um come out of the void, so only hb_cmdproc (-289.44 in y) and hb_quant's S edge move.
    * child slots (hfd_coll_tkm 32, hfd_coll 9 hcoll ports, hfd_su 16 + 1 SU.VOP, hfd_quant QDQ): child_slots."""
    v = r25gq_v10_hclegal()
    v['quant_h'] = QUANT_H
    v['hgi_vm_h'] = 2073.6 - (QUANT_H - 358.56)
    sx_ = dict(SW=13399.776, NW=13399.776, SE=17769.888, NE=17769.888)       # slice x (r25gq_b2, on the grid)
    sy_ = dict(SW=8998.56, SE=8998.56, NW=15199.92, NE=15199.92)
    ds = [dict(name='hb_tkm', master='hfd_coll_tkm', xy=(8683.632, 16277.76), wh=TKM_WH, clear=100.0)]
    nets = [('tkm_del', 'hub', 2180, ('hb_coll', 't_tkm_del'), ('hb_tkm', 'f_del')),     # del_flit 4 x 545
            ('tkm_w', 'hub', 545, ('hb_tkm', 't_w'), ('hb_coll', 'f_tkm_w')),            # {w_data 512, addr, v / rdy}
            ('tkm_cfg', 'hub', 40, ('hb_coll', 't_tkm_cfg'), ('hb_tkm', 'f_cfg')),
            ('tkm_st', 'hub', 8, ('hb_tkm', 't_st'), ('hb_coll', 'f_tkm_st'))]
    for q in ('SW', 'SE', 'NW', 'NE'):
        w_ = q[1] == 'W'
        x_ = sx_[q] + 950.4 + 43.2 if w_ else sx_[q] - 43.2 - DBK_WH[0]
        y_ = sy_[q] + 21.6 if q[0] == 'S' else sy_[q] + 1684.8 - 21.6 - DBK_WH[1]
        ds.append(dict(name=f'hb_dbk_{q}', master='ot_hgi_dma_back', xy=(x_, y_), wh=DBK_WH, orient='R0' if w_ else 'MY',
                       clear=20.0, base_as='hb_loader'))
        nets += [(f'dbk_mv_{q}', 'hub', 229, (f'hb_vms_{q}', 't_dbk_mv'), (f'hb_dbk_{q}', 'f_mv')),     # {mv 227, v, src}
                 (f'dbk_mvr_{q}', 'hub', 4, (f'hb_dbk_{q}', 't_mv'), (f'hb_vms_{q}', 'f_dbk_mv')),      # rdy/done/fault/quiet
                 (f'vdb_{q}', 'hub', 2065, (f'hb_vms_{q}', 't_db_rdn'), (f'hb_dbk_{q}', 'f_vr2r')),     # read half of a tap
                 (f'vdb_{q}_r', 'hub', 129, (f'hb_dbk_{q}', 't_vr2q'), (f'hb_vms_{q}', 'f_db_rup'))]
    v['die_slots'], v['die_slot_nets'], v['dbk_wd'] = tuple(ds), tuple(nets), (2312, 12)
    v['face_force'] = dict(v['face_force'])
    for p_, f_ in (('f_mv', 'W'), ('t_mv', 'W'), ('f_vr2r', 'N'), ('t_vr2q', 'N'), ('t_wd', 'S'), ('f_wdc', 'S')):
        v['face_force'][('ot_hgi_dma_back', p_)] = f_     # the closed leaf's pin faces (master frame)
    # published (contract v11) faces of slice ports whose peer station moved with hb_tkm / the DBK slots: kept
    v['face_keep'] = {('hfd_hgi_vms_NW', 'f_lgNW_wup'): 'W', ('hfd_hgi_vms_NW', 't_lgNW_rdn'): 'W',
                      ('hfd_hgi_vms_NW', 't_ringc_SW'): 'S', ('hfd_hgi_vms_NW', 'f_ring_SW'): 'S',
                      ('hfd_hgi_vms_SW', 'f_xl_rup'): 'E', ('hfd_hgi_vms_SW', 'f_hgi_vmap'): 'W',
                      ('hfd_hgi_vms_SW', 'f_hgi_hc'): 'N'}
    v['child_slots'] = r25gq_v12_children()
    v['xp'] = dict(landing_credits_per_lane=16, bank_queue_credit=10)     # SM.MATVEC x plane (el1013-hbm-redesign-smmv)
    v['vm8_fwd_clocks'] = True      # die SDC: the VM8 face tiles' forwarded clocks are generated clocks (FACE2 10-13)
    return v


def r25gq_v13():
    """contract v13 (hbmdie 10-13) = v12 + the die hop rule PIN TO PIN (owner 2026-10-13: register at the pin ->
    wire <= 500 um -> register at the pin).

    * pin_reach 500: the relay passes measure a hop between PINS (a station's registered a / b face centres, a
      block's pins from its slot pin plan / view LEF), not between boxes; pin_repair puts registered stations on every
      data net whose pins are over the reach (v12: 1,896 data nets up to 4,886 um, e.g. an SM result pin on the far face
      of the 3.2 mm SM); the clock / reset trees are built to the sinks' pins and a reset relay whose loads spread
      over the reach is copied at its own depth (v12: 1,272 reset nets over).
    * rly_family: every register stage takes the hbfd_rly outline -- 21.6 um deep, data faces at 0.096 um a bit (2
      tracks a bit on one layer, buildable under the M5 cap; v12 stations had 0.048-0.071), ck / rst on a third face,
      a bus wider than 1,136 b as class tiles side by side (2,068 b = 2 x 1136 = 228.96 um)."""
    v = r25gq_v12()
    # Unpublished v13 endpoint placeholder: 830 um cannot be placed MX on
    # the 270 nm row / 48 nm M4 lattice. 830.52 is a row multiple with
    # H mod 48 nm = 24 nm, preserving the local 12 nm pin phase under MX.
    # This is a candidate slot change (+0.52 um), not a v12 contract edit.
    v['link_ep_v2'] = dict(v['link_ep_v2'], wh=(2600.0, 830.52))
    v['pin_reach'] = PIN_REACH_UM
    v['rly_family'] = True
    # hot window (v12 GRT: x 12-15 / y 14-17 mm, 91 % of 524,552 overflow in the hub).  v12 put hb_dbk_SW / _NW in the
    # 386-um slice | spine gap, at the slice's far end: 294 um of block in a 386-um channel left 43 + 49 um, i.e. it
    # CLOSED the only N-S corridor W of hb_cmdproc (the N link chains then looped W around the whole NW slice and
    # back: lk_lk_N1 14.5 -> 13.3 -> 14.5 mm at y 15.1).  v13: the two W back-ends sit under their slice's S end
    # (E edges flush, 43.2-um channel, N face = the slice's read group as before): the gap is a clear 386-um channel.
    sxw_, wd_ = 13399.776, 950.4
    v['die_slots'] = tuple(
        dict(ds_, xy=(sxw_ + wd_ - DBK_WH[0], dict(SW=8998.56, NW=15199.92)[ds_['name'][-2:]] - 43.2 - DBK_WH[1]))
        if ds_['name'] in ('hb_dbk_SW', 'hb_dbk_NW') else ds_ for ds_ in v['die_slots'])
    v['cong_present'] = (3.0, 0.5)      # relay routes see the buses already routed (PC_, build_r25gq)
    v['lane_align'] = True              # facing station pairs on one lane, else an L (pin_align)
    v['vm8_union'] = True
    v['child_slots'] = dict(v['child_slots'])
    v['child_slots']['hfd_quant'] = list(v['child_slots']['hfd_quant']) + qdq_children(v['child_slots']['hfd_quant'][0]['xy'])
    # hbmdie 10-14 (window check FAIL on v13: 86 / 21 / 4 windows, worst V 1.351 at x 14.3 / y 15.3 mm): PathFinder
    # history cost from tools/hbm_r25gq_windows.py --cost-out of the previous round (OT_HBMDIE_CONG overrides the
    # committed round while iterating)
    # hbmdie 10-14 area re-plan (results/arch/hbm_die_feasibility_1014/area_v13_1014.md): native IDX scorer = the
    # free corner band W of the serdes / E of the SM group (2,965 x 4,374 um = 12.97 mm2 vs leaf+macro 9.54 mm2 a
    # scorer, bottom edge kept, the band below the lk_ep rows / above them in the N).  The SFU slot does NOT grow
    # (+108 um collides with hb_hc_eng's 100-um clearance in the E band): full leaf + cache 1.6688 mm2 fits the
    # 2.2079 mm2 slot once the SFU's internal ring corridor is <= 0.539 mm2 (today 0.755): a corridor repair (SFU owner)
    if os.environ.get('OT_HBMDIE_V13_AREA', '1') == '1':
        # E x is the PRE col_split coordinate (col_split moves x >= 16,700 east by 1,250): 16,731.6 lands at 17,981.6,
        # 43 um W of the SE / NE SM columns (v13 as committed gave 17,981.6 pre-split = 19,231.6: the E bands overlapped
        # sm8 / sm11 / sm24 / sm27, svc_*E_s0 and phy_NE -- v14 check, 10-14)
        v['idx_score_box'] = dict(w=2965.0, h=4374.0, x=dict(W=11175.0, E=16731.6))
    c_ = os.environ.get('OT_HBMDIE_CONG', V13_CONG)
    if c_:
        v['cong'] = c_
    return v


V13_CONG = 'results/arch/hbm_die_feasibility_1014/v13_win_grt/cong_r4.npy'   # PathFinder round 4 (best GRT: 136,189)

# contract v14 (owner 2026-10-14 09:00, HANDOFF 0ab: HBM peer-to-peer step 1; study results/arch/hbm_p2p_1014/STUDY.md)
P2P_LINKS = dict(S0=('SW', 0), S1=('SW', 1), S2=('SW', 2), S3=('SE', 0), S4=('SE', 1),
                 N0=('NW', 0), N1=('NW', 1), N2=('NE', 0), N3=('NE', 1))       # links rail-aligned 3 / 2 / 2 / 2
P2P_RING = (('SW', 'SE'), ('SE', 'NE'), ('NE', 'NW'), ('NW', 'SW'))            # clockwise 2 x 2 ring, no diagonals
COLLQ_H = 864.0                     # one row of closed ot_hcoll_port (406.08 x 401.76) + the engine core band
COLLQ_WH = dict(hfd_coll_q3=(2255.04, 1844.64 + COLLQ_H),    # SW: engine band + the 32-tile TKM array (TKM_WH) above it
                hfd_coll_q2=(950.4, COLLQ_H))                   # 2 hcoll ports + engine core
P2P_COLL = dict(SW=('hfd_coll_q3', (8700.0, 7950.0)), SE=('hfd_coll_q2', (18960.0, 6960.0)),
                NW=('hfd_coll_q2', (12150.0, 18135.0)), NE=('hfd_coll_q2', (19500.0, 18135.0)))
CKGEN_WH = (216.0, 216.0)           # die clock root: PLL (behavioural analog core) + per-domain POR / reset release
PR_BITS, RC_BITS, RR_BITS = 280, 261, 261   # ot_hfd_coll_q RW = 280; RED_CARRY {v, tag 3, mode, d 256} / {v, tag 3, d 256, rdy}


def r25gq_v14():
    """contract v14 (hbmdie 10-14, owner-approved P2P step 1, HANDOFF 0ab) = v13 (pin-to-pin hops, IDX corner bands) +
      * four quadrant COLL engines at their link edges, one parameterised RTL (ot_hfd_coll_q, COLL agent
        el1014-hbm-p2p-coll.log) under two die masters that bind it (rtl/hbm_accel/generic/collective/p2p/hfd_coll_q.sv):
        hfd_coll_q3 = SW (links S0-S2, HOME + QSOLO, the 32-tile TOPK_MERGE array INSIDE the master: TOPK_MERGE k = 2,048
        is not exact over 4 x 8 tiles, COLL finding 07:50 option (a)), hfd_coll_q2 = SE / NW / NE (2 links each).  The
        central hb_coll and the separate hb_tkm slot are gone.
      * every COLL die net is ONE RTL port of the master (no invented width): own SU quarter (inject, delivery,
        RED_CARRY), own lk_ep rail (the 1,120-b f_lk bundle of hfd_lk_ep split per direction: llk_t 571 b / llk_r 549 b),
        the command processor record (968 + 40 to every engine, recx 554 and ret 3 SW only), the RGX lanes (SW: loader x
        lanes, SW slice VM queue + the 2,213-b ROW_GATHER write stream to the slice master's receive leaves), the TOPK_MERGE writes (SW slice).
      * 2 x 2 registered peer ring between the engines (280 b a direction, pr_cw / pr_ccw); the SU <-> SU 8 x 1,024 b
        cross links are REMOVED (RED_CARRY rides the ring, B2 sec 4).
      * VM8 union (25 closed tiles, cross buses abutted) moves into the centre spine void.
      * hb_hc_eng leaves the E equator band (it walled the SU_SE | SU_NE crossing: GRT r4 overflow there) for the
        freed N spine band; its ring-client tap moves to the NE slice.
      * die clock root hb_ckgen (hfd_ckgen: the PLL hard macro + per-domain POR release, rtl/hbm_accel/control/
        hfd_ckgen.sv) at the spine centre below VM8: the trees start there (per-quadrant phi - R at the pins), the
        reset is staged down the same tree."""
    v = r25gq_v13()
    v['p2p'] = True
    # H-DIE 10-14: SM die master = native ot_hbm_accel_smh, control leaf = the record ABI (111 b), result leaf 269 b
    v['sm_native_abi'] = True
    v['fwd_master_split'] = True
    # the attention -> SU chains tr_SW0 / tr_SW1 ran through the SW COLL slot: re-placed around it, SU pins unchanged
    # (tools/hbm_die_v14_att_relays.py; tr_SW0 +6 cycles, recorded)
    v['att_su_relays'] = 'physical/hbm_accel_die_views/att_su_relay/relays_r25gq_v14.json'
    v['ck_root'] = 'hb_ckgen'
    # H-DIE 10-14 pm: clock / reset tree edges follow ONE capacity-aware route each (the chase form orbited blocks in the
    # SE quadrant: 72k pairs, 811 stages, trunk CTS case 72k nets -> four 300-s timeouts)
    v['tree_fixed_path'] = True
    # H-DIE 10-14 pm (window c6 FAIL 42 / 13 / 3, worst H 1.463 at x 22.0-23.6 / y 1.5-2.2 mm; GRT c6 SE bins): the SE
    # IDX band sat 43 um W of the sm8 / sm11 / sm14 column, so the SE key rows (ks0-3 from svc_SE_s0-s2 to the attention
    # entries) and the band's ksg / wl_sm / lw hops all squeezed through the 455-um strip svc_SE | sm8 and the 43-um
    # abutment gap, and the clock / reset tree could not enter the SE SM field (42 capped tree edges).  The band moves
    # W against the serdes slab sd_S (as SW sits against it: pre-split x < 16,700, so col_split leaves it there),
    # opening a ~1.3-mm channel between the band and the SE SM column.  NE is unchanged (not hot).
    # H-DIE 10-14 pm (window SE-fixed: 5 windows, worst V 1.072, coll_rgx_c 86 %): the SW engine's 8,961-b TOPK_MERGE
    # write lanes to the SW slice (t_rgx_c / f_rgx_c) left its E face into the 218-um COLL | SU_SW gap and ran down it;
    # on the S face they drop into the open column E of ep_S1 and run E under SU_SW (window PathFinder round 2: PASS
    # 0 / 0 / 0, worst 0.876).  Die-assigned pins (hfd_coll_q3 is a new master: top-down pin assignment).
    # H-COLL 10-14 night: the 8,961-b W2 client bus is replaced by the registered ROW_GATHER write stream t_rgx_t
    # (2,213 b) / f_rgx_t (5 b): the receive leaves and the VM / HBM write clients sit inside the SW slice master
    # (ot_vms_slice_coll_sw).  Same S face.
    v['face_force'] = {**(v.get('face_force') or {}), ('hfd_coll_q3', 't_rgx_t'): 'S', ('hfd_coll_q3', 'f_rgx_t'): 'S'}
    for kv_ in filter(None, os.environ.get('OT_HBMDIE_FACE_FORCE', '').split(',')):    # iteration override: m|p=F
        k_, f_ = kv_.split('=')
        v['face_force'] = {**(v.get('face_force') or {}), tuple(k_.split('|')): f_}
    if v.get('idx_score_box'):
        v['idx_score_box'] = dict(v['idx_score_box'], x=dict(v['idx_score_box']['x'],
                                                             SE=float(os.environ.get('OT_HBMDIE_IDX_SE_X', '16699.0'))))
        if os.environ.get('OT_HBMDIE_IDX_SW_Y'):
            v['idx_score_box']['y'] = dict(v['idx_score_box'].get('y') or {}, SW=float(os.environ['OT_HBMDIE_IDX_SW_Y']))
        if os.environ.get('OT_HBMDIE_IDX_NE_X'):
            v['idx_score_box']['x']['NE'] = float(os.environ['OT_HBMDIE_IDX_NE_X'])
    vdx_ = os.environ.get('OT_HBMDIE_VMS_DX')       # iteration override 'dxW,dxE': slices toward the spine
    if vdx_ and v.get('vm_b2'):
        dw_, de_ = (float(t_) for t_ in vdx_.split(','))
        xy_ = {q_: ((p_[0] + dw_) if q_[1] == 'W' else (p_[0] - de_), p_[1]) for q_, p_ in v['vm_b2']['xy'].items()}
        v['vm_b2'] = dict(v['vm_b2'], xy=xy_)
        v['die_slots'] = [dict(d_, xy=(xy_[d_['name'][-2:]][0] - 43.2 - d_['wh'][0], d_['xy'][1]))
                          if d_['name'] in ('hb_dbk_SE', 'hb_dbk_NE') else d_ for d_ in v['die_slots']]
    if os.environ.get('OT_HBMDIE_EPS2_Y') and v.get('link_ep_v2'):
        xy_ = dict(v['link_ep_v2']['xy'])
        s_ = list(xy_['S'])
        s_[2] = (s_[2][0], float(os.environ['OT_HBMDIE_EPS2_Y']))
        xy_['S'] = tuple(s_)
        v['link_ep_v2'] = dict(v['link_ep_v2'], xy=xy_)
    v['drop_blocks'] = tuple(v['drop_blocks']) + ('hb_coll',)
    v['drop_buses'] = v['drop_buses'] + (r'|lk_lk_[NS]\d\w*|hb_su_[NS][EW]_coll\w*|hb_coll_su_[NS][EW]\w*|hgi_vmaddr_[NS][EW]\w*'
                                         r'|hgi_coll_(cmd|ret)\w*|hgi_cfg_coll\w*|hgi_rgx[qrwa][01]\w*|hgi_vm[qr]_coll\w*'
                                         r'|hb_su_[NS][EW]_su_[NS][EW]\w*|vcb_coll\w*')
    v['vm_b2'] = dict(v['vm_b2'], coll_tree=(),
                      clients=tuple((c, t, 'NE' if c == 'hb_hc_eng' else q) for c, t, q in v['vm_b2']['clients']))
    # hb_hc_eng to the N spine band (x 14,304-18,689 / y 17,064-18,630; the preset y is before svc_ch_dh)
    v['hc_eng'] = dict(v['hc_eng'], xy=(14304.0, 17064.0 - 108.0))
    # SFU (area v13: full leaf + cache 1.6688 mm2 > usable 1.4531): with hb_hc_eng out of the equator band the slot grows
    # +216 um toward the equator (usable 1.8886, 13 % margin) instead of the v13 internal-corridor repair
    v['sfu_h_add'] = 216.0
    dy_ = -4918.32      # VM8 union: 2,277 rows of 2.16 down, centred on the die y centre (11,990.16 .. 13,990.27)
    v['block_xy'] = {n_: (x_, y_ + dy_) for n_, (x_, y_) in dict(
        hb_vm_sw=(14736.384, 16908.48), hb_vm_se=(15436.224, 16908.48),
        hb_vm_nw=(14736.384, 17908.536), hb_vm_ne=(15436.224, 17908.536)).items()}
    ds = [ds_ for ds_ in v['die_slots'] if ds_['name'] != 'hb_tkm']
    for q, (mst_, xy_) in P2P_COLL.items():
        ds.append(dict(name=f'hb_coll_{q}', master=mst_, xy=xy_, wh=COLLQ_WH[mst_], clear=60.0))
    ds.append(dict(name='hb_ckgen', master='hfd_ckgen', xy=(15328.0, 11500.0), wh=CKGEN_WH, clear=20.0, no_tree=True))
    v['ck_root_inputs'] = dict(refclk=('refclk', 'CLOCK'), por_n=('por_n', 'SIGNAL'))
    nets = [n_ for n_ in v['die_slot_nets'] if not n_[0].startswith('tkm_')]
    for l_, (q, k) in P2P_LINKS.items():        # one hfd_lk_ep f_lk bundle a link (class link_flit: per-bit directions,
        # endpoint 0 = the COLL engine): [546:0] + [1117:1094] COLL -> link, [1093:547] + [1119:1118] link -> COLL
        nets.append((f'lkq_{l_}', 'link_flit', 1120, (f'hb_coll_{q}', f'llk{k}'), (f'ep_{l_}', 'f_lk')))
    for q in ('SW', 'SE', 'NW', 'NE'):
        c_, su_ = f'hb_coll_{q}', f'hb_su_{q}'
        nets += [(f'coll_inj_{q}', 'hub', 34, (c_, 't_inj'), (su_, 'f_coll_inj')),
                 (f'coll_inja_{q}', 'hub', 160, (c_, 't_inj_addr'), (su_, 'f_coll_inj_addr')),
                 (f'coll_vma_{q}', 'hub', 80, (c_, 't_vmaddr'), (su_, 'f_hgi_vmaddr')),
                 (f'coll_injd_{q}', 'hub', 1024, (su_, 't_coll_inj_d'), (c_, 'f_inj_d')),
                 (f'coll_del_{q}', 'hub', 2344, (c_, 't_del'), (su_, 'f_coll_del')),
                 (f'coll_rc_{q}', 'hub', RC_BITS, (su_, 't_rc'), (c_, 'f_rc')),
                 (f'coll_rr_{q}', 'hub', RR_BITS, (c_, 't_rr'), (su_, 'f_rr')),
                 (f'coll_rec_{q}', 'hub', 968, ('hb_cmdproc', f't_coll_rec_{q}'), (c_, 'f_hgi_rec')),
                 (f'coll_cfg_{q}', 'hub', 40, ('hb_cmdproc', f't_coll_cfg_{q}'), (c_, 'f_hgi_cfg'))]
    nets.append(('coll_ret', 'hub', 3, ('hb_coll_SW', 't_hgi_ret'), ('hb_cmdproc', 'f_coll_ret')))
    # the TOPK record extension reaches the SW (QSOLO) engine only: ot_hfd_coll_q2 has no hgi_recx port
    nets.append(('coll_recx_SW', 'hub', 554, ('hb_cmdproc', 't_coll_recx_SW'), ('hb_coll_SW', 'f_hgi_recx')))
    for a_, b_ in P2P_RING:     # cw a -> b, ccw b -> a
        nets += [(f'pr_cw_{a_}_{b_}', 'hub', PR_BITS, (f'hb_coll_{a_}', 't_pr_cw'), (f'hb_coll_{b_}', 'f_pr_cw')),
                 (f'pr_ccw_{b_}_{a_}', 'hub', PR_BITS, (f'hb_coll_{b_}', 't_pr_ccw'), (f'hb_coll_{a_}', 'f_pr_ccw'))]
    # SW only (QSOLO): TOPK_MERGE writes and the RGX lanes
    # (ports of hfd_coll_q3 / ot_hfd_coll_q3 and of the SW slice master ot_vms_slice_coll_sw; the ROW_GATHER HBM write
    # lanes xw / xwa now leave the slice master, where the HBM write clients sit beside the receive leaves)
    nets += [('coll_tkw', 'hub', 569, ('hb_coll_SW', 't_tkw'), ('hb_vms_SW', 'f_coll_tkw')),
             ('coll_tkw_cr', 'hub', 1, ('hb_vms_SW', 't_coll_tkw_cr'), ('hb_coll_SW', 'f_tkw_cr')),
             ('coll_rgx_xq', 'hub', 76, ('hb_coll_SW', 't_rgx_xq'), ('hb_loader', 'f_coll_rgx_xq')),
             ('coll_rgx_xr', 'hub', 514, ('hb_loader', 't_coll_rgx_xr'), ('hb_coll_SW', 'f_rgx_xr')),
             ('coll_rgx_xw', 'hub', 652, ('hb_vms_SW', 't_coll_rgx_xw'), ('hb_loader', 'f_coll_rgx_xw')),
             ('coll_rgx_xwa', 'hub', 2, ('hb_loader', 't_coll_rgx_xwa'), ('hb_vms_SW', 'f_coll_rgx_xwa')),
             ('coll_rgx_vmq', 'hub', 338, ('hb_coll_SW', 't_rgx_vmq'), ('hb_vms_SW', 'f_hgi_coll')),
             ('coll_rgx_vmr', 'hub', 274, ('hb_vms_SW', 't_hgi_coll'), ('hb_coll_SW', 'f_rgx_vmr')),
             ('coll_rgx_t', 'hub', 2213, ('hb_coll_SW', 't_rgx_t'), ('hb_vms_SW', 'f_coll_rgx_t')),
             ('coll_rgx_f', 'hub', 5, ('hb_vms_SW', 't_coll_rgx_f'), ('hb_coll_SW', 'f_rgx_t'))]
    v['die_slots'], v['die_slot_nets'] = tuple(ds), tuple(nets)
    v['die_straps'] = {f'hb_coll_{q}': dict(qid=i) for i, q in enumerate(('SW', 'SE', 'NW', 'NE'))}
    v['dense_face_masters'] = tuple(m_ for m_ in v['dense_face_masters'] if m_ != 'hfd_coll') + ('hfd_coll_q3', 'hfd_coll_q2')
    cs_ = dict(v['child_slots'])
    cs_.pop('hfd_coll', None)
    tkm_ = cs_.pop('hfd_coll_tkm')
    for mq_, n_ in (('hfd_coll_q3', 3), ('hfd_coll_q2', 2)):
        cs_[mq_] = [dict(name=f'u_q.u_ep.u_port[{c}]', cell='ot_hcoll_port', wh=HCOLL_WH,
                         xy=(45.36 + c * (HCOLL_WH[0] + 45.36), 21.6), orient='R0') for c in range(n_)]
    # SW: the TOPK_MERGE array (closed tiles, serpentine) above the engine band
    cs_['hfd_coll_q3'] += [dict(c_, name='u_q.u_ep.g_tkm.u_tkm.' + c_['name'], xy=(c_['xy'][0], c_['xy'][1] + COLLQ_H))
                           for c_ in tkm_]
    v['child_slots'] = cs_
    c_ = os.environ.get('OT_HBMDIE_CONG', V14_CONG)
    if c_:
        v['cong'] = c_
    else:
        v.pop('cong', None)
    return v


V14_CONG = ''       # v14: no PathFinder history yet (rounds write results/arch/hbm_die_v14/cong_r<k>.npy)


def _lef_size(lef, macro):
    txt = Path(lef).read_text()
    body = txt[txt.index(f'MACRO {macro}'):]
    return tuple(map(float, re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', body).groups()))


def qdq_children(origin, root=None):
    """contract v13: the leaves of the QDQ cluster u_qdq (ot_hgi_qdq_q_pin4, 622.08 x 596.16) as grandchild slots of
    hfd_quant, from the cluster's own kit spec (tools/ref_tile/specs_hbmb2vm/qdq_q_ref.json children: view + origin in
    the cluster frame).  A leaf with a closed view takes the view's outline; one without (its view directory does not
    exist yet) the kit floorplan's."""
    root = Path(root) if root else Path(__file__).resolve().parents[1]
    spec = json.loads((root / 'tools/ref_tile/specs_hbmb2vm/qdq_q_ref.json').read_text())
    out = []
    for c in spec['children']:
        vd = root / c['view']
        cell, kit = vd.name, vd.parents[1].name
        if (vd / f'{cell}.lef').exists():
            wh, view = _lef_size(vd / f'{cell}.lef', cell), c['view']
        else:
            d_ = json.loads((root / 'physical/ref_tile' / kit / 'floorplan.json').read_text())['die']
            wh, view = (d_[2], d_[3]), None
        out.append(dict(name=c['inst'], cell=cell, wh=wh, xy=(origin[0] + c['at'][0], origin[1] + c['at'][1]), orient='R0',
                        within='u_qdq', **({'view': view} if view else {}),
                        status=(f'CLOSED view {view}' if view else f'no view yet (kit {kit}); el1013-hbm-qdq') +
                               '; leaf of the QDQ cluster u_qdq at its kit-spec origin'))
    return out


def vm8_union_group(insts, root=None):
    """contract v13: the VM8 CP cluster is ONE region, the union of the four logical quarter slots hb_vm_<q>
    (1,399.632 x 2,000.112), holding 25 closed tiles of 19 kits (root, 3 + 1 slices, RE, ring rb / rt / rw, eight face
    tiles) whose origins the VM8 stream's plan gives in the union frame
    (physical/hbm_accel_die_views/vm/cp/candidate_geometry.py: make_vm_cp.INST + the kit specs + face_pin_plan).  The
    quarter slots stay as the die-face port carriers of the cluster; the 36 half-tile sub-slots of contract v3 (D8) are
    gone.  Every child's outline must be its closed view's (asserted)."""
    import subprocess
    root = Path(root) if root else Path(__file__).resolve().parents[1]
    cp = root / 'physical/hbm_accel_die_views/vm/cp'
    r_ = subprocess.run([sys.executable, str(cp / 'candidate_geometry.py')], capture_output=True, text=True, check=True)
    g = json.loads(r_.stdout)
    by = {it.name: it for it in insts}
    mem = ('hb_vm_sw', 'hb_vm_se', 'hb_vm_nw', 'hb_vm_ne')
    x0, y0 = min(by[n_].x for n_ in mem), min(by[n_].y for n_ in mem)
    x1, y1 = max(by[n_].x + by[n_].w for n_ in mem), max(by[n_].y + by[n_].h for n_ in mem)
    # the quarters sit on the die placement grid: their union is 24 nm wider than the plan region (1,399.656)
    assert abs(x1 - x0 - g['region'][0]) < 0.05 and abs(y1 - y0 - g['region'][1]) < 0.05, \
        ('VM8 union is not the four quarter slots', (x1 - x0, y1 - y0), g['region'])
    ch, boxes = [], []
    for nm, i_ in g['instances'].items():
        cell = i_['master']
        vds = sorted((root / 'physical/ref_tile').glob(f'{cell}*/views/{cell}/{cell}.lef'))
        fit = [v_ for v_ in vds if max(abs(a_ - b_) for a_, b_ in zip(_lef_size(v_, cell), (i_['w'], i_['h']))) < 0.006]
        assert fit, ('VM8 tile outline is not a closed view', nm, cell, (i_['w'], i_['h']))
        bx = (i_['x'], i_['y'], i_['x'] + i_['w'], i_['y'] + i_['h'])
        assert bx[0] >= -1e-6 and bx[1] >= -1e-6 and bx[2] <= g['region'][0] + 1e-6 and bx[3] <= g['region'][1] + 1e-6, nm
        for n2, b2 in boxes:
            assert bx[2] <= b2[0] + 1e-6 or b2[2] <= bx[0] + 1e-6 or bx[3] <= b2[1] + 1e-6 or b2[3] <= bx[1] + 1e-6, \
                ('VM8 tiles overlap', nm, n2)
        boxes.append((nm, bx))
        ch.append(dict(name=nm, cell=cell, wh=[round(i_['w'], 3), round(i_['h'], 3)], xy=[round(i_['x'], 3), round(i_['y'], 3)],
                       orient=i_['orient'], view=str(fit[-1].parent.relative_to(root)),
                       status=f'CLOSED view {fit[-1].parents[2].name}; VM8 CP tile at its plan origin (union frame)'))
    return dict(name='hb_vm_cp', cell='hfd_vm_cp', members=list(mem), xy=[round(x0, 3), round(y0, 3)],
                wh=[round(x1 - x0, 3), round(y1 - y0, 3)], children=ch,
                per_bit_hops_over_500=len(g.get('per_bit_hops_above500') or []),
                note='VM8 CP cluster = union of the four logical quarter slots; 25 closed tiles (19 kits), wires-only '
                     'cluster; per-bit tile-to-tile hops <= 500 um by the stream\'s face_pin_plan')


def r25gq_v9():
    """contract v9 = v8 + D22 (the HGI HC unit slot hb_hgi_hc; see HGI_HC_PORTS)"""
    ls_ = R25GQ['lane_stations']
    w_ = dict(ls_['W'], stations=tuple(st if st[0] != 'hb_stn_lgW_hc' else ('hb_stn_lgW_hc', 'hb_hgi_hc', 'S', 2016.0)
                                       for st in ls_['W']['stations']))
    lg_ = dict(R25GQ['lane_groups'], W=tuple('hb_hgi_hc' if n_ == 'hb_hc_SW' else n_ for n_ in R25GQ['lane_groups']['W']))
    return dict(R25GQ, r25gq_net=True, **dict(R25GQ_PR, **R25GQ_V8), lane_stations=dict(ls_, W=w_), lane_groups=lg_,
                dense_face_masters=tuple(R25GQ['dense_face_masters']) + ('hfd_hgi_hc',),
                hgi_hc_slot=dict(name='hb_hgi_hc', master='hfd_hgi_hc', xy=(11173.0, 12290.4),
                                 wh=(2016.0, 820.8), ports=HGI_HC_PORTS, **{'from': 'hb_hc_SW'}))


def child_slots_check(cs, insts):
    """contract v12: the child slots granted inside a parent slot ({parent master: [child dicts, parent frame R0]}).
    Every child lies inside its parent's outline and no two overlap; returns the record build() publishes
    (m['child_slots']) and the hierarchy contract writes."""
    first = {}
    for it in insts:
        first.setdefault(it.master, it)
    out = {}
    for mst, ch in cs.items():
        assert mst in first, ('child slots of a master the die does not place', mst)
        P, boxes = first[mst], []
        for c in ch:
            (x, y), (w, h) = c['xy'], c['wh']
            assert x >= -1e-6 and y >= -1e-6 and x + w <= P.w + 1e-6 and y + h <= P.h + 1e-6, \
                ('child slot outside its parent', mst, c['name'], (x, y, w, h), (P.w, P.h))
            if c.get('within'):     # a grandchild: inside the named child slot (a wires-only cluster), parent frame
                wb = dict(boxes)[c['within']]
                assert x >= wb[0] - 1e-6 and y >= wb[1] - 1e-6 and x + w <= wb[2] + 1e-6 and y + h <= wb[3] + 1e-6, \
                    ('grandchild outside its cluster slot', mst, c['name'], c['within'])
            for (n2, b), c2 in zip(boxes, ch):
                if n2 == c.get('within') or (c2.get('within') and c2['within'] != c.get('within') and False):
                    continue
                assert x + w <= b[0] + 1e-6 or b[2] <= x + 1e-6 or y + h <= b[1] + 1e-6 or b[3] <= y + 1e-6, \
                    ('child slots overlap', mst, c['name'], n2)
            boxes.append((c['name'], (x, y, x + w, y + h)))
        out[mst] = [dict(c, xy=[round(c['xy'][0], 3), round(c['xy'][1], 3)], wh=[round(c['wh'][0], 3), round(c['wh'][1], 3)])
                    for c in ch]
    return out


# contract v12 (hbmdie 10-13): granted slots.  Outlines of closed views are the view's own (LEF SIZE).
TKM_TILE, TKM_COLS, TKM_ROWS, TKM_CH, TKM_SEQ_W = 300.24, 6, 6, 21.6, 302.4   # ot_hgi_coll_tkm_tile (coll_tkm_tile_cx view)
TKM_WH = (TKM_SEQ_W + TKM_CH + TKM_COLS * (TKM_TILE + TKM_CH), TKM_ROWS * TKM_TILE + 2 * TKM_CH)   # 2,255.04 x 1,844.64
DBK_WH = (293.76, 293.76)                                       # ot_hgi_dma_back (hgi_dma_back_b2_ref view)
QDQ_WH = (622.08, 596.16)                                       # ot_hgi_qdq_q_pin4 (qdq_q_ref q8 outline)
QUANT_H = 648.0                                                 # hfd_quant: 358.56 -> 648.0 (QDQ + 2 x 25.92)
HCOLL_WH = (406.08, 401.76)                                     # ot_hcoll_port (hcoll_port_cx view)
SEQ_WH, SEQ_XY = (347.76, 272.16), (43.2, 561.6)                # ot_hgi_seq_split slot (unchanged) / origin in hfd_cmdproc
SV_LEAF_WH, SV_HEAD_WH = (95.04, 103.68), (216.0, 216.0)        # ot_hgi_sv_lane2 (reference leaf) / ot_hgi_sv_head (est.)


def r25gq_v12_children():
    """child slots of contract v12 in their parent frames (R0)"""
    # TKM cluster (el1013-hbm-coll.log physical spec, re-drawn for the CLOSED 300.24-um tile): the sequencer strip
    # (decode, lane FIFOs, entry sort, 2 SRAMs, packer, tau / busy trees) along the W face, then 6 columns of N-S
    # abutting tiles, serpentine from the strip: even columns run N -> S (R0: ins N, ovf S), odd columns S -> N (MX),
    # a 681-b registered relay at each U-turn; 32 of the 36 sites are used (column 5 holds 2)
    tkm = [dict(name='seq_strip', cell='ot_hgi_coll_tkm (sequencer region, cluster logic)', wh=(TKM_SEQ_W, TKM_ROWS * TKM_TILE),
                xy=(0.0, TKM_CH), orient='R0', kind='region')]
    for k in range(32):
        c, r = divmod(k, TKM_ROWS)
        row = (TKM_ROWS - 1 - r) if c % 2 == 0 else r
        tkm.append(dict(name=f'u_t[{k}]', cell='ot_hgi_coll_tkm_tile', wh=(TKM_TILE, TKM_TILE),
                        xy=(TKM_SEQ_W + TKM_CH + c * (TKM_TILE + TKM_CH), TKM_CH + row * TKM_TILE),
                        orient='R0' if c % 2 == 0 else 'MX'))
    hcoll = [dict(name=f'u_port[{3 * r + c}]', cell='ot_hcoll_port', wh=HCOLL_WH,
                  xy=(45.36 + c * (HCOLL_WH[0] + 45.36), 21.6 + r * (HCOLL_WH[1] + 21.6)), orient='R0')
             for r in range(3) for c in range(3)]
    su = [dict(name=f'u_lane[{k}]', cell='ot_hgi_sv_lane2', wh=SV_LEAF_WH,
               xy=(2016.144 - 21.6 - SV_LEAF_WH[0], 367.2 + k * 129.6), orient='R0') for k in range(16)]
    su.append(dict(name='u_head', cell='ot_hgi_sv_head', wh=SV_HEAD_WH,
                   xy=(2016.144 - 21.6 - SV_LEAF_WH[0] - 43.2 - SV_HEAD_WH[0], (2808.0 - SV_HEAD_WH[1]) / 2), orient='R0'))
    # sequencer (el1013-hbm-seq-split): the slot is unchanged, 347.76 x 272.16, now a wires-only cluster of three
    # hardened leaves on their own clock roots (FE 4,683 / AU 7,517 / BE 14,491 sinks; worst internal cut 0.40 at the AU
    # E face).  Its origin in hfd_cmdproc is the die's choice until the cmdproc floorplan (b2-cp) pins it: W third,
    # mid height (W = cfg / clock, N = fetch, E = dispatch, S = doorbell / VM / completion, as hgi_seq_v26s).
    sx, sy = SEQ_XY
    seq = [dict(name='u_seq', cell='ot_hgi_seq_split', wh=SEQ_WH, xy=(sx, sy), orient='R0', kind='cluster'),
           dict(name='u_seq.u_fe', cell='ot_hgi_seq_fe', wh=(248.4, 211.68), xy=(sx, sy), orient='R0', within='u_seq'),
           dict(name='u_seq.u_be', cell='ot_hgi_seq_be', wh=(88.56, 272.16), xy=(sx + 259.2, sy), orient='R0', within='u_seq'),
           dict(name='u_seq.u_au', cell='ot_hgi_seq_au', wh=(254.88, 56.16), xy=(sx, sy + 216.0), orient='R0', within='u_seq')]
    return dict(hfd_coll_tkm=tkm, hfd_coll=hcoll, hfd_su=su, hfd_cmdproc=seq,
                hfd_quant=[dict(name='u_qdq', cell='ot_hgi_qdq_q_pin4', wh=QDQ_WH, xy=(25.92, 25.92), orient='R0')])


def variant_arg(v):
    """'' -> the adopted default (r16g); 'r8' -> the r1-r8 geometry; 'r10' / 'r14b' / 'r15' / 'r15m' / 'r16e' presets; a JSON dict
    -> those keys (absent keys = r8 behaviour); a JSON dict with "base": preset -> the preset updated with the keys."""
    if v == 'service-attn-r1':          # Codex child-contract revision: built on the r14b nets (kept replayable)
        return dict(R14B, hub_h=12355.2, attn_tile_w_um=1349.136,
                    attn_tile_h_um=1350.0, child_contract='hbm_child_contract_20261005')
    if not v:
        return None
    pre = dict(r8={}, r10=R10, r14b=R14B, r15=R15, r16e=R16E, r16g=R16G, r16h=R16H, r16i=R16I, r19b=R19B, r19c=R19C, r23=R23, r23v=R23V, r24=R24, r24p=R24P, r25=R25, r25a=R25A, r25s=R25S, r25m=R25M, r25i=R25I, r25ic2=R25IC2, r25iq=R25IQ, r25iqc2=R25IQC2, r25iqg=R25IQG, r25iqgc2=R25IQGC2, r25imw=R25IMW, r25imws=R25IMWS, r25g=R25G, r25g4=R25G4, r25g4t4=R25G4T4, r25gp=R25GP, r25gph=R25GPH, r25gpht4=R25GPHT4, r25gv=R25GV, r25gq=R25GQ, r25gqn=dict(R25GQ, r25gq_net=True), r25gqn_pr=dict(R25GQ, r25gq_net=True, **R25GQ_PR), r25gqn_pr8=dict(R25GQ, r25gq_net=True, **dict(R25GQ_PR, **R25GQ_V8)), r25gqn_pr9=r25gq_v9(), r25gqn_b2=r25gq_b2(), r25gqn_v10=r25gq_v10(), r25gqn_v10_hclegal=r25gq_v10_hclegal(), r25gqn_v12=r25gq_v12(), r25gqn_v13=r25gq_v13(), r25gqn_v14=r25gq_v14(), r25gm=R25GM, r25g4m=R25G4M, r25sps=R25SPS, r24f=R24F, r24w=R24W, adopted=ADOPTED, r15m=dict(R15, hub_h=12355.2, **ATTN_MEAS))
    if v in pre:
        return dict(pre[v])
    d = json.loads(v)
    if 'base' in d:
        return dict(pre[d.pop('base')], **d)
    return json.loads(v)
# ================================================================================================================
# Qwen3-8B HBM accelerator die (the HA8 W12 vehicle's own organisation: 1,536 tiles, 4 HBM3E stacks, 421.5 MiB SRAM)
# ================================================================================================================
# Census per die (results/uarch/hbm_current_target_portmap_20261005/model_portmap.json Qwen): one core + spine, 1,536
# W12 tiles (TG4, G = 6,144), the four-stack wstream (128 PC stream controllers), the TP collective, the loader.
# Floorplan -> hardened element -> replicate: the tile element is the W12 tile logic (measured routed core) + its
# 421.5 MiB share of the code/KV SRAM (real ASAP7 macros) + its corridor and fill forwarding banks, replicated 96 x 16.
#
#   field     96 columns x 16 rows of the tile element, W half (48 columns) | spine | E half (48 columns); the column
#             head row (MIDCH) between rows 7 and 8 feeds each column's corridor (instruction + x + forwarded clock)
#             north and south through the abutting tile elements
#   stacks    one stack per 24-column quarter: SW (columns 0-23) and SE (48-71) fill from the S edge, NW (24-47) and
#             NE (72-95) from the N edge.  Each stack's PHY (real ot_hbm3e_phy_v41x_aw30_e8p5, 8.5 mm) sits on its
#             quarter's edge with the stream service between it and the field; the service drops one 512 b fill bus
#             into the end tile of each of its 24 columns, and the fill runs through the column's tile elements
#             (each HBM word's 64 B tile slices are striped so that a stack holds its own quarter's slices)
#   tree      W12 split tree: blocks of 4 x 4 tiles (15 in-block nodes hosted by tiles, 512 b words), 96 block words
#             (512 b) into the spine port slice of the block-row band (4 bands), port slices -> core tree top
#   spine     between the halves: core (tree top, VM / x root, constants + sequencer, SU64 + SFU, stream control),
#             four port slices and four scale-store slabs (the W5 spine reservations of the ROM die), loader; SerDes
#             macros at the spine's S end, host UCIe macro at its N end; collective + SerDes slab in the free S band
#             W of the spine, host slab in the free N band E of the spine
Q_OUT = 'results/rtl/hbm_accel_qwen_die_floorplan_20261005'
Q_FINAL_ROUND = 'q3'
Q_TILE_ROUTE = dict(TP2='results/rtl/hbm_accel_fmax_inventory_20261004/qwen_me/routes/tile_tp2_t4/physical.json',
                    TP4='results/rtl/hbm_accel_fmax_inventory_20261004/qwen_me/routes/tile_tp4_t4/physical.json')
Q_SRAM_RW = 'physical/asap7_memory_macros/ot_sram_1rw_2048x128_m4/ot_sram_1rw_2048x128_m4.json'
Q_SRAM_WIN = 'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.json'
Q_STORAGE = 'results/uarch/qwen_hbm_storage_binding_20261005/storage_binding.json'
Q_ME_OPS = 'results/rtl/qwen_rom_fulldie_20261003/b3r3/wire_bound_8k.json'
Q_CHAINS = 'results/rtl/hbm_accel_qwen_chains_20261004/composition.json'
QCOLS, QROWS = 96, 16
QBLK = (4, 4)                   # tiles per tree block (columns, rows)
QT_W = 313.632                  # tile slot width: the W12 slot of the ROM die (726 x 0.432), 52.704 um corridor strip on E
QT_CORR = 52.704
Q_COR_BITS = Q.CORRIDOR_BITS    # 637: clock 64 + reset 64 + instruction 379 + go 1 + x 128 + ready 1
Q_FILL_BITS = 512 + 16          # 64 B tile slice of an HBM word + tile select / word index / valid
Q_TREE_BITS = Q.TREE_BITS       # 512
Q_PORT_BITS = 12 * 512          # one band's 12 port words (of the 48 x 512 b ME result) per half -> core
Q_STAT_BITS = 64                # w_c_gray32 + a_gray32 (stream status, model_portmap Q_STREAM_STATUS)
Q_LOAD_BITS = 341 + 273         # loader request + response (qwen_physical_model service_loader)
Q_COLL_BITS = 512               # c_data512 / r_data512 (Q_COLLECTIVE)
Q_SERDES = 4                    # TP4: three peers + one spare lane group (ot_rom_oneshot_allreduce N = 4)
MIDCH = 345.6                   # column-head row between rows 7 and 8
Q_GAP = 43.2
QBLOCKS = dict(
    tile=(None, 'measured-routed + real macros', 'see tile_element'),
    core=(2.397 + 0.725 + 2.157 + 1.6 + 0.2, 'model + estimate', 'W12 core: tree top 2.397 + VM 0.725 + constants/'
          'sequencer 2.157 (W5 spine reservations, tools/qwen_rom_fulldie.py SPINE_BLOCKS) + SU64/SFU 1.6 (estimate) + '
          'stream control 0.2 (window use-count release ot_hbmacc_win_usecount 85 um2 routed + gray-count syncs, '
          'estimate)'),
    port=(11.08, 'model', 'W5 spine_port_tiles (96 port groups), as four band slices'),
    scale=(14.359, 'model', 'W5 spine_scale_rom reservation, kept as the scale-constant store (the 421.5 MiB code '
           'budget excludes scales: storage_binding includes_VM_program_scale_constants = false)'),
    coll=(3.6, 'model', 'collective block (Qwen ROM die IO ledger, tools/qwen_rom_fulldie.py IO_BLOCKS)'),
    serdes=(4.0, 'model', 'board SerDes reservation (Qwen ROM die IO ledger): real ot_pdie_serdes pin macros + slab'),
    host=(10.0, 'model', 'host UCIe reservation (Qwen ROM die IO ledger): real ot_pdie_ucie pin macro + slab'),
    loader=(0.3321, 'measured-slot', 'ot_hbm_accel_loader_host slot 576.288^2 um (tapeout_hbm_loader_20261004)'),
    svc=(BLOCKS['svc'][0], BLOCKS['svc'][1], BLOCKS['svc'][2]),
)


def q_tile():
    """The replicated tile element: measured routed W12 tile logic core (the larger of the TP2 / TP4 routes, so that
    one die frame carries either build) + the tile's share of the code/KV SRAM on real ASAP7 macros + the corridor
    strip.  SRAM: the HA8 budget is 421.5 MiB / die = 4,496 code words of 98,304 B = 4,496 x 512 b per tile (the
    window carved out of it); the tile reads 2 group-pair columns x 256 b per code word (ot_qwen_rom_tile_w12 code
    bank geometry).  Resident words: 2 columns x 2 x ot_sram_1rw_2048x128_m4 wide x 2 deep (4,096 words); the stream
    window (and the resident tail) in 2 x ot_sram_1r1w_1024x256_m2_r2c2 (1,024 words), so the stream writes never
    contend with the engine reads."""
    tl = {k: json.loads((ROOT / p).read_text())['design'] for k, p in Q_TILE_ROUTE.items()}
    logic = max(v['core_area_um2'] for v in tl.values())
    rw = json.loads((ROOT / Q_SRAM_RW).read_text())['area']
    wn = json.loads((ROOT / Q_SRAM_WIN).read_text())['area']
    body_w = QT_W - QT_CORR
    halo = 4.32
    rw_w, rw_h, wn_w, wn_h = rw['macro_width_um'], rw['macro_height_um'], wn['macro_width_um'], wn['macro_height_um']
    assert 2 * rw_w + 3 * halo <= body_w and wn_w + 2 * halo <= body_w
    band_h = 4 * (rw_h + halo) + 2 * (wn_h + halo) + halo
    h = up(logic / body_w + band_h, GY)
    words = 2048 * 2 + 1024
    sb = json.loads((ROOT / Q_STORAGE).read_text())['weight_sram_budget']
    macros = [dict(master='ot_sram_1rw_2048x128_m4', n=8, w=rw_w, h=rw_h, um2=rw['macro_area_um2'],
                   role='resident code words 0..4,095: 2 group-pair columns x 2 wide (256 b) x 2 deep'),
              dict(master='ot_sram_1r1w_1024x256_m2_r2c2', n=2, w=wn_w, h=wn_h, um2=wn['macro_area_um2'],
                   role='stream window + resident tail, words 4,096..5,119: 1R1W so the stream fill never blocks a read')]
    sram_um2 = sum(x['n'] * x['um2'] for x in macros)
    return dict(w=QT_W, h=h, body_w=body_w, corridor_w=QT_CORR, logic_core_um2=logic,
                logic_basis={k: dict(core_um2=v['core_area_um2'], cell_um2=v['area_um2'],
                                     utilisation=v['utilization_fraction'], fmax_tt_hz=v['fmax_hz'], closed=v['closed'],
                                     source=Q_TILE_ROUTE[k]) for k, v in tl.items()},
                macro_band_h=round(band_h, 3), logic_h=round(h - band_h, 3), macros=macros,
                sram_um2=round(sram_um2, 1), words_per_tile=words, word_bits=512,
                sram_mib_per_die=round(words * 64 * QCOLS * QROWS / 2 ** 20, 1),
                goal_words_per_tile=sb['word_capacity'], goal_mib_per_die=sb['mib_per_die'],
                capacity_over_goal_pct=round(100 * (words / sb['word_capacity'] - 1), 1),
                hop_stages=math.ceil(h / LINK_STAGE_UM),
                mm2=round(QT_W * h / 1e6, 5))


def build_qwen(variant=None):
    variant = dict(variant or {}, die='qwen')
    T = q_tile()
    T['tree_pin_pitch'] = int(variant.get('tree_pitch', 2))   # q3: 2 (q2 tried 4 with packing: i50 2,764)
    th = T['h']
    spw = up(variant.get('spine_w', 2000.16), GX)
    spc = up(variant.get('spine_ch', 172.8), GX)
    xfw = up(EDGE, GX)
    xsp = xfw + 48 * QT_W
    xfe = xsp + spw
    W = up(xfe + 48 * QT_W + EDGE, GX)
    yp_s = up(EDGE, GY)
    ys_s = up(yp_s + PHY_H + 8.64, GY)
    yr0 = up(ys_s + SVC_D + SVC_GAP, GY)
    row_y = [yr0 + r * th for r in range(8)]
    ym = yr0 + 8 * th
    row_y += [ym + MIDCH + r * th for r in range(8)]
    ytop = row_y[-1] + th
    ys_n = up(ytop + SVC_GAP, GY)
    yp_n = up(ys_n + SVC_D + 8.64, GY)
    H = up(yp_n + PHY_H + EDGE, GY)
    assert W <= 33000 and H <= 26000, ('die exceeds the reticle', W, H)
    insts, regions, notes = [], [], []

    def col_x(c):
        return xfw + c * QT_W if c < 48 else xfe + (c - 48) * QT_W
    geo = dict(W=W, H=H, xfw=xfw, xsp=xsp, xfe=xfe, spine_w=spw, spine_ch=spc, yr0=yr0, ym=ym, ytop=ytop, tile_h=th,
               row_y=row_y, side_h=yr0, mid=ym + MIDCH / 2)
    tiles = {}
    for c in range(QCOLS):
        for r in range(QROWS):
            it = Inst(f't_{c}_{r}', 'qhd_tile', col_x(c), row_y[r], QT_W - SHAVE, th - SHAVE, 'R0', kind='tile',
                      region='field_W' if c < 48 else 'field_E')
            insts.append(it)
            tiles[(c, r)] = it
    hh = 69.12
    heads = {}
    for c in range(QCOLS):
        it = Inst(f'h_{c}', 'qhd_head', col_x(c) + QT_W - QT_CORR, up(ym + (MIDCH - hh) / 2, GY), QT_CORR - SHAVE,
                  hh - SHAVE, 'R0', kind='head', region='midch')
        insts.append(it)
        heads[c] = it
    regions += [dict(name='field_W', kind='field', rect=[xfw, yr0, xsp, ytop]),
                dict(name='field_E', kind='field', rect=[xfe, yr0, xfe + 48 * QT_W, ytop]),
                dict(name='midch', kind='channel', rect=[xfw, ym, xfe + 48 * QT_W, ym + MIDCH]),
                dict(name='spine', kind='hub', rect=[xsp, yr0, xfe, ytop])]
    # ---- stacks: PHY + stream service on the edge of each 24-column quarter
    rp = S.real_lef(PHY_LEF)
    groups = {}
    qcols = dict(SW=range(0, 24), NW=range(24, 48), SE=range(48, 72), NE=range(72, 96))
    for st, cols in qcols.items():
        side = st[0]
        x_lo, x_hi = col_x(cols[0]), col_x(cols[-1]) + QT_W
        if st == 'SW':
            xp = up(xfw, GX)
        elif st == 'NW':
            xp = dn(xsp - PHY_W, GX)
        elif st == 'SE':
            xp = up(xfe, GX)
        else:
            xp = dn(xfe + 48 * QT_W - PHY_W, GX)
        yp, ys, po = (yp_s, ys_s, 'R0') if side == 'S' else (yp_n, ys_n, 'MX')
        phy = Inst(f'phy_{st}', rp['name'], xp, yp, rp['w'], rp['h'], po, kind='phy', region='phy', domain='hbm')
        svc = Inst(f'svc_{st}', f'hfd_svc_{st}', xp, ys, PHY_W - SHAVE, SVC_D - SHAVE, po, kind='svc', region='svc',
                   domain='hbm')
        insts += [phy, svc]
        regions.append(dict(name=f'svc_{st}', kind='svc', rect=[xp, ys, xp + PHY_W, ys + SVC_D]))
        groups[st] = dict(phy=phy, svc=svc, side=side, cols=list(cols), x_lo=x_lo, x_hi=x_hi)
    # ---- IO: SerDes macros at the spine's S end, collective + SerDes slab in the free S band W of the spine; UCIe at
    #      the spine's N end, host slab in the free N band E of the spine (+ its remainder beside the UCIe macro)
    rs, ru = S.real_lef(SERDES_LEF), S.real_lef(UCIE_LEF)
    MG = 103.68
    links = []
    row_w = Q_SERDES * rs['w'] + (Q_SERDES - 1) * MG
    assert row_w <= spw - 2 * Q_GAP
    sx = up(xsp + (spw - row_w) / 2, GX)
    for i in range(Q_SERDES):
        it = Inst(f'lk_S{i}', rs['name'], up(sx + i * (rs['w'] + MG), GX), up(EDGE, GY), rs['w'], rs['h'], 'R0',
                  kind='link', region='link', domain='link')
        insts.append(it)
        links.append(it)
    io_y0, io_y1 = up(EDGE, GY), dn(ys_s + SVC_D, GY)     # the service channel stays open above the IO band
    band_d = io_y1 - io_y0
    free_s = (groups['SW']['phy'].x + PHY_W + Q_GAP, xsp - Q_GAP)
    cw = up(QBLOCKS['coll'][0] * 1e6 / band_d, GX)
    coll = Inst('io_coll', 'qhd_coll', dn(free_s[1] - cw, GX), io_y0, cw - SHAVE, band_d - SHAVE, kind='hub', region='io',
                domain='serial_0p9')
    sw_ = up(QBLOCKS['serdes'][0] * 1e6 / band_d, GX)
    sslab = Inst('io_sd_slab', 'qhd_serdes_slab', dn(coll.x - Q_GAP - sw_, GX), io_y0, sw_ - SHAVE, band_d - SHAVE,
                 kind='serdes_slab', region='io', domain='link')
    assert sslab.x >= free_s[0] - 1e-6, ('S band does not hold the collective + SerDes slab', sslab.x, free_s)
    insts += [coll, sslab]
    regions.append(dict(name='io_S', kind='link', rect=[sslab.x, io_y0, xsp, io_y1]))
    ux = up(xsp + spw - Q_GAP - ru['w'], GX)
    uy = dn(H - EDGE - ru['h'], GY)
    host = Inst('lk_host', ru['name'], ux, uy, ru['w'], ru['h'], 'R0', kind='link', region='link', domain='link')
    insts.append(host)
    io_n0, io_n1 = up(ys_n, GY), dn(H - EDGE, GY)
    free_n = (xfe + Q_GAP, groups['NE']['phy'].x - Q_GAP)
    hw_a = dn(free_n[1] - free_n[0], GX)
    ha_mm2 = min(QBLOCKS['host'][0], hw_a * (io_n1 - io_n0) / 1e6)
    hs_a = Inst('io_host_a', 'qhd_host_slab_a', up(free_n[0], GX), io_n0, hw_a - SHAVE, dn(io_n1 - io_n0, GY) - SHAVE,
                kind='host_slab', region='io', domain='link')
    insts.append(hs_a)
    hb_mm2 = round(QBLOCKS['host'][0] - ha_mm2, 4)
    regions.append(dict(name='io_N', kind='link', rect=[xfe, io_n0, free_n[1], io_n1]))
    # ---- spine: core centred on the head row, port + scale slabs per band, loader, host-slab remainder at the N end
    bw = spw - 2 * spc
    bx = up(xsp + spc, GX)
    bw = dn(xfe - spc - bx, GX)
    y_lo = up(max(EDGE + rs['h'], yr0) + Q_GAP, GY)
    y_hi = dn(min(uy, ytop) - Q_GAP, GY)
    hub = {}

    def blk(name, master, mm2, y, kind='spine', dom='stream_1p2', x=None, w=None):
        w = w or bw
        h = up(mm2 * 1e6 / w, GY)
        it = Inst(name, master, x if x is not None else bx, y, w - SHAVE, h - SHAVE, kind=kind, region='hub', domain=dom)
        insts.append(it)
        hub[name] = it
        return it
    core_h = up(QBLOCKS['core'][0] * 1e6 / bw, GY)
    core = blk('sp_core', 'qhd_core', QBLOCKS['core'][0], dn(geo['mid'] - core_h / 2, GY))
    band_port = bool(variant.get('band_ports'))    # put each band's port slice at its own band's mid-height
    # q2: the port slices pack against the core (q1 GRT: 65 % of the i5 overflow was the 6,144-bit port -> core words
    #     climbing over the slabs between them); the scale slabs and the loader spread over the rest of the column
    packed = variant.get('port_core', 0)   # q3: MEASURED q1 spread i50 overflow 0; packing at the core (q2) gave 2,764 (pword at the slab boundary)
    if packed:
        lower = [('sp_scale0', 'scale', 0), ('sp_scale1', 'scale', 1), ('sp_port0', 'port', 0), ('sp_port1', 'port', 1)]
        upper = [('sp_port2', 'port', 2), ('sp_port3', 'port', 3), ('sp_scale2', 'scale', 2), ('sp_scale3', 'scale', 3),
                 ('sp_loader', 'loader', None)]
    else:
        lower = [('sp_scale0', 'scale', 0), ('sp_port0', 'port', 0), ('sp_port1', 'port', 1), ('sp_scale1', 'scale', 1)]
        upper = [('sp_scale2', 'scale', 2), ('sp_port2', 'port', 2), ('sp_port3', 'port', 3), ('sp_scale3', 'scale', 3),
                 ('sp_loader', 'loader', None)]
    if hb_mm2 > 0:
        upper.append(('sp_host_b', 'host_b', None))

    def mm(kind_):
        return dict(scale=QBLOCKS['scale'][0] / 4, port=QBLOCKS['port'][0] / 4, loader=QBLOCKS['loader'][0],
                    host_b=hb_mm2)[kind_]
    PG_ = 2 * Q_GAP                                   # port slice <-> core / port spacing when packed
    # slab order: with band_ports the port slices sit at their own block-row band's mid-height (the q3 bound showed the
    # port word reaching 81 stages against the vehicle's 38); the scale slabs and the loader fill the remaining column.
    kinds_of = dict((nn, kk) for nn, kk, _ in lower + upper)

    def slab_gap(occ, need):
        gs = [(y_lo, occ[0][0])] + [(occ[i][1], occ[i + 1][0]) for i in range(len(occ) - 1)] + \
             [(occ[-1][1], y_hi)]
        gs = [g for g in gs if g[1] - g[0] > need + Q_GAP]
        if not gs:
            return None
        gs.sort(key=lambda g: -(g[1] - g[0]))
        return gs[0]
    if band_port:
        ph = up(mm('port') * 1e6 / bw, GY)
        occ = []
        for band in range(4):
            r0 = band * 4
            ymid = (row_y[r0] + row_y[r0 + 3] + th) / 2
            yb_ = up(min(max(ymid - ph / 2, y_lo), y_hi - ph), GY)
            cz0, cz1 = core.y - Q_GAP - ph, core.y + core.h + SHAVE + Q_GAP     # clear of the core slab
            if yb_ < cz1 and yb_ + ph > cz0:                                     # band mid-height is inside the core
                yb_ = dn(cz0 - Q_GAP, GY) if ymid < (cz0 + cz1) / 2 else up(cz1 + Q_GAP, GY)
            yb_ = up(min(max(yb_, y_lo), y_hi - ph), GY)
            blk(f'sp_port{band}', 'qhd_port', mm('port'), yb_, w=bw)
            occ.append((yb_, yb_ + ph + SHAVE))
        occ.sort()
        rest = [n for n, k_, _ in lower + upper if k_ != 'port']
        hs_r = [up(mm(kinds_of[n]) * 1e6 / bw, GY) for n in rest]
        gs = [(y_lo, occ[0][0])] + [(occ[i][1], occ[i + 1][0]) for i in range(len(occ) - 1)] + [(occ[-1][1], y_hi)]
        gs = [g for g in gs if g[1] - g[0] > 2 * Q_GAP]
        gs.sort(key=lambda g: -(g[1] - g[0]))          # fill the largest free span first
        for n, h_ in zip(rest, hs_r):
            placed = False
            for gi, (a_, b_) in enumerate(gs):
                if b_ - a_ >= h_ + 2 * Q_GAP:
                    blk(n, f'qhd_{n[3:]}', mm(kinds_of[n]), up(a_ + Q_GAP, GY),
                        kind='host_slab' if n == 'sp_host_b' else 'spine',
                        dom='link' if n == 'sp_host_b' else 'stream_1p2')
                    gs[gi] = (a_ + Q_GAP + h_ + Q_GAP, b_)
                    placed = True
                    break
            assert placed, ('no free column span for ' + n, h_, gs, occ)
        gs.sort(key=lambda g: -(g[1] - g[0]))
    for seq, a_, b_ in ((lower, y_lo, core.y - Q_GAP), (upper, core.y + core.h + SHAVE + Q_GAP, y_hi)):
        if band_port:
            continue
        hs_ = [up(mm(k_) * 1e6 / bw, GY) for _, k_, _ in seq]
        gap = (b_ - a_ - sum(hs_)) / (len(seq) + 1)
        assert gap >= Q_GAP - 1e-6, ('spine does not pack', gap, a_, b_, sum(hs_))
        y = a_ + gap
        for (name, k_, _), h_ in zip(seq, hs_):
            blk(name, f'qhd_{name[3:]}', mm(k_), up(y, GY), kind='host_slab' if k_ == 'host_b' else 'spine',
                dom='link' if k_ == 'host_b' else 'stream_1p2')
            y += h_ + gap
    notes.append(f'spine blocks {bw:.1f} um wide in a {spw:.1f} um column ({spc:.1f} um channels); host slab '
                 f'{ha_mm2:.3f} mm2 in the N band + {hb_mm2:.3f} mm2 at the spine N end')
    m = dict(die='qwen', geo=geo, insts=insts, regions=regions, internal_nets=[], groups=groups, hub=hub, tiles=tiles, heads=heads,
             links=links, host=host, coll=coll, notes=notes, variant=variant, stn_faces={}, tile_element=T,
             final_round=Q_FINAL_ROUND, out=Q_OUT, col_x=col_x, qcols=qcols)
    m['buses'], m['paths'] = buses_qwen(m)
    m['fixed_ports'] = dict(qhd_tile=lambda mst: _q_tile_pins(mst, T), qhd_head=_q_head_pins)
    by = {it.name: it for it in insts}
    tree_x = {p_: 40.0 + 60.0 * i for i, p_ in enumerate(('t_out', 'n_a', 'n_b', 'n_y'))}

    def pin_xy(inst, port):
        it = by[inst]
        if it.kind != 'tile' or port not in tree_x:
            return None
        return (it.x + tree_x[port] + 0.2, it.y + T['macro_band_h'] + T['logic_h'] / 2)
    m['pin_xy'] = pin_xy
    m['master_notes'] = dict(
        qhd_tile=(f'Qwen HBM tile element: W12 tile logic (routed core {T["logic_core_um2"]:.0f} um2) + 8 x '
                  f'ot_sram_1rw_2048x128_m4 + 2 x ot_sram_1r1w_1024x256_m2_r2c2 + corridor/fill forwarding banks '
                  f'({T["hop_stages"]} per hop); internal M1-M7, M8/M9 over the top for die nets'),
        qhd_head='column head: head-chain station + corridor split north / south (637 b)')
    return m


def _q_tile_pins(mst, T):
    """Fixed tile pin plan (one master for all 1,536 instances): corridor in the corridor strip on the N/S faces, the
    fill bus over the macro band on the N/S faces, the tree words as M8 area pins over the logic."""
    xc = T['body_w'] + T['corridor_w'] / 2
    for p_, f_ in (('cs', 'S'), ('cn', 'N')):
        mst.face(p_, Q_COR_BITS, f_, 'M5', xc, 1)
    for p_, f_ in (('fs', 'S'), ('fn', 'N')):
        mst.face(p_, Q_FILL_BITS, f_, 'M5', T['body_w'] / 2, 2)
    for i, p_ in enumerate(('t_out', 'n_a', 'n_b', 'n_y')):
        mst.area(p_, Q_TREE_BITS, 40.0 + 60.0 * i, T['macro_band_h'] + T['logic_h'] / 2, T['tree_pin_pitch'])


def _q_head_pins(mst):
    for p_, f_, ly in (('n', 'N', 'M5'), ('s', 'S', 'M5'), ('w', 'W', 'M4'), ('e', 'E', 'M4')):
        mst.face(p_, Q_COR_BITS, f_, ly, (mst.w if f_ in 'NS' else mst.h) / 2, 1)


def buses_qwen(m):
    B, P = [], defaultdict(list)
    internal_nets = m.setdefault('internal_nets', [])
    station, chain = _router(m, B, P)
    g = m['geo']
    T = m['tile_element']
    hub = m['hub']
    core = hub['sp_core']
    # (1) corridors: head -> rows 8.. (north) and rows 7.. (south) through the abutting tile elements
    for c in range(QCOLS):
        B.append((f'cor_{c}_n', 'corridor', Q_COR_BITS, [(f'h_{c}', 'n'), (f't_{c}_8', 'cs')]))
        B.append((f'cor_{c}_s', 'corridor', Q_COR_BITS, [(f'h_{c}', 's'), (f't_{c}_7', 'cn')]))
        for r in range(QROWS - 1):
            if r == 7:
                continue
            B.append((f'cor_{c}_{r}', 'corridor_hop', Q_COR_BITS, [(f't_{c}_{r}', 'cn'), (f't_{c}_{r + 1}', 'cs')]))
    # (2) x / instruction distribution from the core's x roots along the head row: a registered head per column
    #     (ROM-die chain: one stage per 313.632 um hop) or, with variant x_trunk, one trunk per half that every head
    #     taps (registers every <= 430.56 um of trunk, priced from the trunk's routed length)
    trunk = bool(m['variant'].get('x_trunk'))
    if trunk:
        B.append(('xtr_W', 'head_chain', Q_COR_BITS, [(core.name, 'xw')] + [(f'h_{c}', 'e') for c in range(47, -1, -1)]))
        B.append(('xtr_E', 'head_chain', Q_COR_BITS, [(core.name, 'xe')] + [(f'h_{c}', 'w') for c in range(48, QCOLS)]))
    else:
        prev = (core.name, 'xw')
        for c in range(47, -1, -1):
            B.append((f'head_{c}', 'head_chain', Q_COR_BITS, [prev, (f'h_{c}', 'e')]))
            prev = (f'h_{c}', 'w')
        prev = (core.name, 'xe')
        for c in range(48, QCOLS):
            B.append((f'head_{c}', 'head_chain', Q_COR_BITS, [prev, (f'h_{c}', 'w')]))
            prev = (f'h_{c}', 'e')
    for c in range(QCOLS):
        rng = range(c, 48) if c < 48 else range(48, c + 1)
        ids = ([f'xtr_{"W" if c < 48 else "E"}'] if trunk else
               [f'head_{k}' for k in (sorted(rng, reverse=True) if c < 48 else rng)])
        for r_far, entry in ((15, f'cor_{c}_n'), (0, f'cor_{c}_s')):
            P[f'bd_{c}_{"n" if r_far else "s"}'] = ids + [entry]
    # (3) fill: stream service -> end tile of each of its columns; tile-to-tile hops through the elements
    for st, G in m['groups'].items():
        svc = G['svc']
        npins = len(real_ports()[G['phy'].master]['dfi'])
        B.append((f'dfi_{st}', 'phy_dfi', npins, [(G['phy'].name, 'dfi'), (svc.name, 'phy')]))
        for c in G['cols']:
            end = (f't_{c}_0', 'fs') if G['side'] == 'S' else (f't_{c}_15', 'fn')
            B.append((f'fill_{c}', 'fill', Q_FILL_BITS, [(svc.name, f'f{c}'), end]))
            P[f'fill_{st}_{c}'] = [f'fill_{c}']
            for r in range(QROWS - 1):
                B.append((f'fh_{c}_{r}', 'fill_hop', Q_FILL_BITS, [(f't_{c}_{r}', 'fn'), (f't_{c}_{r + 1}', 'fs')]))
    # (4) ME split tree: 4 x 4 blocks, nodes hosted by tiles (W12 morton host assignment, as the ROM die)
    bc, br = QBLK
    nb = 0
    roots = []
    for c0 in range(0, QCOLS, bc):
        for r0 in range(0, QROWS, br):
            tl = sorted(((c, r) for c in range(c0, c0 + bc) for r in range(r0, r0 + br)),
                        key=lambda t: Q.morton(t[0] - c0, t[1] - r0))
            used = set()
            level = [(f't_{c}_{r}', 't_out') for c, r in tl]
            lv = 0
            while len(level) > 1:
                nxt = []
                for i in range(0, len(level), 2):
                    span = 2 ** (lv + 1)
                    sub = tl[i * (2 ** lv): i * (2 ** lv) + span]
                    hostt = next(f't_{c}_{r}' for c, r in sub if f't_{c}_{r}' not in used)
                    used.add(hostt)
                    # the host tile's own t_out feeding its own n_a is INSIDE the element (not a die net): emit it
                    # as an internal connection, never as a die-level bus (a self net is unroutable / degenerate)
                    for cid_, peer in ((f'tree_{nb}_{lv}_{i}a', level[i]), (f'tree_{nb}_{lv}_{i}b', level[i + 1])):
                        if peer[0] == hostt:
                            internal_nets.append(dict(id=cid_, bits=Q_TREE_BITS, at=hostt, port=peer[1],
                                                           note='host tile consumes its own t_out: element-internal'))
                        else:
                            B.append((cid_, 'tree_block', Q_TREE_BITS, [peer, (hostt, 'n_a' if cid_.endswith('a') else 'n_b')]))
                    nxt.append((hostt, 'n_y'))
                level = nxt
                lv += 1
            roots.append((nb, level[0], c0, r0))
            nb += 1
    # every leaf -> root path (q_tree_paths) is priced from the routed lengths
    for b, root, c0, r0 in roots:
        band = r0 // br
        port = hub[f'sp_port{band}']
        B.append((f'bword_{b}', 'tree_spine', Q_TREE_BITS, [root, (port.name, f'b{b}')]))
        P[f'tws_{b}'] = [f'bword_{b}', f'pword_{band}']
    for band in range(4):
        B.append((f'pword_{band}', 'spine_port', Q_PORT_BITS, [(hub[f'sp_port{band}'].name, 'p'), (core.name, f'p{band}')]))
        B.append((f'scale_{band}', 'spine_port', 512, [(hub[f'sp_scale{band}'].name, 's'), (hub[f'sp_port{band}'].name, 's')]))
    m['tree_blocks'] = [dict(block=b, c0=c0, r0=r0, root=root[0]) for b, root, c0, r0 in roots]
    # (5) collective: core <-> collective (spine W channel, down to the S band), collective -> SerDes macros
    xw_ch = g['xsp'] + g['spine_ch'] / 2
    co = m['coll']
    c0_ = _cxy(core, 'W', 0.2)
    tgt = _cxy(co, 'N', 0.7)
    yb = g['yr0'] - SVC_GAP / 2 + 20.0
    pts = [c0_, (xw_ch, c0_[1]), (xw_ch, yb), (tgt[0], yb), tgt]
    chain('ct', 'collective', Q_COLL_BITS, (core.name, 'ct'), (co.name, 'vt'), pts, path='coll_tx')
    c1_ = _cxy(core, 'W', 0.1)
    tgt = _cxy(co, 'N', 0.85)
    pts = [c1_, (xw_ch + 40.0, c1_[1]), (xw_ch + 40.0, yb + 10.0), (tgt[0], yb + 10.0), tgt]
    chain('cr', 'collective', Q_COLL_BITS, (co.name, 'vr'), (core.name, 'cr'), pts[::-1], path='coll_rx')
    for lk in m['links']:
        B.append((f'lk_{lk.name}', 'link', 1024, [(co.name, f'l{lk.name}'), (lk.name, 'io')]))
        P[f'link_{lk.name}'] = [f'lk_{lk.name}']
    # (6) stream status (gray counts) svc <-> core, and the loader <-> each svc (load path, off the token path)
    xe_ch = g['xfe'] - g['spine_ch'] / 2
    ld = hub['sp_loader']
    for st, G in m['groups'].items():
        svc = G['svc']
        side = G['side']
        west = st[1] == 'W'
        ych_ = g['yr0'] - SVC_GAP / 2 if side == 'S' else g['ytop'] + SVC_GAP / 2
        xch = (xw_ch - 30.0) if west else (xe_ch + 30.0)
        sp = _cxy(core, 'W' if west else 'E', 0.65 if side == 'N' else 0.35)
        tp = _cxy(svc, 'N' if side == 'S' else 'S', 0.95 if west else 0.05)
        pts = [tp, (tp[0], ych_), (xch, ych_), (xch, sp[1]), sp]
        chain(f'stat_{st}', 'stream_status', Q_STAT_BITS, (svc.name, 'st'), (core.name, f'st{st}'), pts,
              path=f'stat_{st}')
        lp = _cxy(ld, 'W' if west else 'E', 0.5)
        xl = (xw_ch + 30.0) if west else (xe_ch - 30.0)
        yl = ych_ + (12.0 if side == 'S' else -12.0)
        tq = _cxy(svc, 'N' if side == 'S' else 'S', 0.9 if west else 0.1)
        pts = [lp, (xl, lp[1]), (xl, yl), (tq[0], yl), tq]
        chain(f'ld_{st}', 'load', Q_LOAD_BITS, (ld.name, f'l{st}'), (svc.name, 'ld'), pts)
    B.append(('ld_host', 'host', 1024, [(ld.name, 'h'), (m['host'].name, 'io')]))
    B.append(('ld_core', 'hub', 256, [(ld.name, 'c'), (core.name, 'ld')]))
    # (7) clock trunks: PLL in the collective block -> every service and spine block root; the field takes the
    #     corridor-forwarded clock from the heads (the core's x root)
    for it in m['insts']:
        if it.kind in ('svc', 'spine'):
            B.append((f'clk_{it.name}', 'clock_trunk', CLK_BITS, [(co.name, 'pll'), (it.name, 'ck')]))
    return B, dict(P)


def q_tree_paths(m):
    """Every leaf -> root path of every block: [bus ids] (four levels).  Built from the tree buses: a node input bus
    'tree_b_lv_ia/b' feeds host.n_a/n_b; the host's n_y feeds the next level."""
    by_dst, src_of = {}, {}
    for bid, cls, bits, eps in m['buses']:
        if cls == 'tree_block':
            by_dst[bid] = eps
            src_of[(eps[1][0], eps[1][1])] = bid
    out_from = defaultdict(list)
    for bid, eps in by_dst.items():
        out_from[eps[0]].append(bid)
    # a host tile consuming its own t_out is an element-internal hop (no die net, no die-level stage)
    internal = {(e['at'], e['port']) for e in m.get('internal_nets', [])}
    paths = {}
    for (c, r), it in m['tiles'].items():
        p, node = [], (it.name, 't_out')
        while node in out_from or node in internal:
            if node in internal:
                node = (node[0], 'n_y')
                continue
            bid = out_from[node][0]
            p.append(bid)
            node = (by_dst[bid][1][0], 'n_y')
        paths[it.name] = p
    return paths


def plan_record_qwen(m):
    kinds, area = defaultdict(int), defaultdict(float)
    for it in m['insts']:
        kinds[it.kind] += 1
        pad = 0 if it.kind in ('phy', 'link') else SHAVE
        area[it.kind] += (it.w + pad) * (it.h + pad) / 1e6
    cls = defaultdict(lambda: dict(buses=0, wires=0))
    for bid, c, bits, eps in m['buses']:
        cls[c]['buses'] += 1
        cls[c]['wires'] += bits
    g = m['geo']
    T = m['tile_element']
    mp = manhattan_paths(m)
    ledger = {k: dict(mm2=round(v[0], 4) if v[0] is not None else None, grade=v[1], source=v[2]) for k, v in QBLOCKS.items()}
    ledger['tile'].update(mm2=T['mm2'], per_die_mm2=round(T['mm2'] * QCOLS * QROWS, 2))
    placed = sum(area.values())
    return dict(
        schema='opentallas.hbm-accel-qwen-die-floorplan.v1', tool='tools/hbm_accel_die_fp.py --die qwen',
        tool_sha256=sha('tools/hbm_accel_die_fp.py'),
        sources_sha256={p: sha(p) for p in (PHY_LEF, SERDES_LEF, UCIE_LEF, SNAP_LIB, PORTMAP, QWEN, QWEN_ALL, Q_SRAM_RW,
                                            Q_SRAM_WIN, Q_STORAGE, Q_ME_OPS, Q_CHAINS, *Q_TILE_ROUTE.values(),
                                            'tools/dsrom_s81_fulldie.py', 'tools/qwen_rom_fulldie.py')},
        die=dict(w_um=g['W'], h_um=g['H'], mm2=round(g['W'] * g['H'] / 1e6, 2), reticle_mm2=858.0,
                 reticle_margin_mm2=round(858.0 - g['W'] * g['H'] / 1e6, 1), dies_per_rank=1,
                 tp2_dies=2, tp4_dies=4),
        census=dict(tiles=QCOLS * QROWS, columns=QCOLS, rows=QROWS, tree_blocks=len(m['tree_blocks']),
                    block_words=len(m['tree_blocks']), stacks=4, pcs_per_stack=32, serdes_macros=len(m['links']),
                    column_heads=QCOLS),
        tile_element=T, block_ledger=ledger, instances=dict(kinds), area_mm2_by_kind={k: round(v, 3) for k, v in area.items()},
        placed_footprint_mm2=round(placed, 2), utilisation_of_die=round(placed / (g['W'] * g['H'] / 1e6), 3),
        geometry={k: (round(v, 3) if isinstance(v, float) else v) for k, v in g.items() if k != 'row_y'},
        row_y_um=[round(v, 3) for v in g['row_y']],
        stack_columns={k: [v[0], v[-1]] for k, v in ((k_, list(v_)) for k_, v_ in m['qcols'].items())},
        clock_domains=dict(stream_1p2='tiles, heads, corridors (forwarded clock), core, port / scale slabs, loader '
                                      '(1.2 GHz, 0.833 ns)', serial_0p9='SU64/SFU inside the core, collective',
                           hbm='PHY + stream services (1.024 ns)', link='SerDes / host (own clocks)'),
        crossings=dict(fill='async FIFO in each stream service (hbm -> stream), charged 2 cycles per first access',
                       corridor='the corridor forwards its own clock (64 tracks) with the instruction and x; a '
                                'mesochronous FIFO at the core x root',
                       block_words='mesochronous FIFO at each port slice (forwarded tile clock -> spine clock), '
                                   'charged 2 cycles on the tree return',
                       status='gray-coded counts through the vehicle\'s two-flop synchronisers (inside its cycles)'),
        bus_classes=dict(cls), manhattan_paths=mp, power=die_power(m), pdn=pdn_plan(m, Q_COV), notes=m['notes'],
        variant={k: v for k, v in m['variant'].items()})


def q_check(m):
    pc = pin_clashes(m)
    pc16 = pin_clashes(m, 16)
    out = dict(legality=_legality(m), generated_pin_clashes=len(pc), examples=pc[:10], k16_clashes=len(pc16),
               die_mm2=round(m['geo']['W'] * m['geo']['H'] / 1e6, 2), W=m['geo']['W'], H=m['geo']['H'],
               tile=dict((k, m['tile_element'][k]) for k in ('h', 'mm2', 'hop_stages', 'sram_mib_per_die',
                                                              'capacity_over_goal_pct')),
               power=die_power(m)['peak_in_phase_w'], notes=m['notes'],
               buses=len(m['buses']), wires=sum(b[2] for b in m['buses']),
               replicated_copy_pin_check=_copy_pins(m), internal_nets=len(m.get('internal_nets', [])),
               instances=len(m['insts']))
    mp = manhattan_paths(m)
    worst = {}
    for p, v in mp.items():
        k = p.split('_')[0]
        if v['stages_430'] > worst.get(k, (0, ''))[0]:
            worst[k] = (v['stages_430'], p, v['um'])
    out['manhattan_worst'] = worst
    return out


def _copy_pins(m):
    """Every replicated copy must own its pins: no die net may connect two ends to the same instance, and no port of
    one instance may carry two different die nets (the DS-die failure class: 128 nets unroutable)."""
    deg = defaultdict(lambda: defaultdict(list))
    selfnets = []
    for bid, cls, bits, eps in m['buses']:
        if len({e[0] for e in eps}) < len(eps):
            selfnets.append(bid)
            continue
        for inst, port in eps:
            deg[inst][port].append(bid)
    multi = {(i, p): ids for i, d in deg.items() for p, ids in d.items() if len(ids) > 1}
    return dict(self_nets=len(selfnets), self_net_examples=selfnets[:5], ports_with_two_nets=len(multi),
                examples=[(k, v[:3]) for k, v in list(multi.items())[:5]],
                instances_without_pins=[it.name for it in m['insts'] if it.name not in deg and
                                        it.kind not in ('phy', 'link', 'serdes_slab', 'host_slab')][:10],
                verdict='PASS' if not selfnets else 'FAIL')


DENS.update(tile=1.05, head=0.6)
# Qwen die PG: the DS r2 classes, stream-service straps raised to 0.25 (ir1 at 0.1639: the 10 N-edge windows over the
# PHY signal-bump rows + service failed, worst 37.6 mV; the 0.25 screen passed them at 23.54 mV)
Q_COV = dict(COV, svc=0.25)


def write_sdc_qwen(path):
    Path(path).write_text("""# Qwen3-8B HBM accelerator die clock domains (AGENTS.md clock domains), tools/hbm_accel_die_fp.py --die qwen
create_clock -name clk_stream -period 0.833 [get_pins {sp_core/ck sp_port*/ck sp_scale*/ck sp_loader/ck}]
create_clock -name clk_serial -period 1.111 [get_pins {io_coll/pll}]
create_clock -name clk_hbm    -period 1.024 [get_pins {phy_*/clk svc_*/ck}]
set_clock_uncertainty -setup 0.060 [all_clocks]
set_clock_uncertainty -hold 0.025 [all_clocks]
# no die-wide synchronous tree (32 x 26 mm; qwen_rom_fulldie case d): the core x root launches the corridor with its
# own forwarded clock (64 corridor tracks) through the head chain and every column's abutting tile elements; the tile
# tree words return to the port slices through a mesochronous FIFO (2 periods, charged on the TWS path)
#   H*  stream service (clk_hbm) -> fill bus / status: async FIFO inside the service (2 periods, charged per first
#       access); status counts gray-coded through the vehicle's two-flop synchronisers
#   X*  SU64/SFU and collective (clk_serial) <-> core: ratio CDC 3:4 inside the core
#   L*  collective <-> SerDes, loader <-> UCIe: plesiochronous at the link macro
set_clock_groups -asynchronous -group {clk_stream} -group {clk_serial} -group {clk_hbm}
""")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['plan', 'check', 'real', 'grt', 'ir', 'irwin', 'record', 'price', 'floor'])
    ap.add_argument('--work', type=Path)
    ap.add_argument('--k', type=int, default=16)
    ap.add_argument('--tag', default='base')
    ap.add_argument('--iters', type=int, default=50)
    ap.add_argument('--empty', action='store_true')
    ap.add_argument('--window', default='w00_00')
    ap.add_argument('--grt-win', default='', help='grt: x0,y0,x1,y1 um window experiment (nets crossing it only)')
    ap.add_argument('--m45', type=float, default=None, help='grt: M4/M5 channel adjustment (blocks stay 1.0)')
    ap.add_argument('--cov', default='')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--only', default='')
    ap.add_argument('--die', choices=['ds', 'qwen'], default='ds', help='ds: the DS SM die (r8); qwen: the Qwen3-8B '
                    'W12 tile die')
    ap.add_argument('--var', default='', help='qwen floorplan variant knobs k=v,... (spine_w, spine_ch)')
    ap.add_argument('--ds-var', default='', help='ds die: a preset name (e.g. r25m, the MTP-DIE variant) or a JSON '
                    'variant (variant_arg); default the ADOPTED round')
    a = ap.parse_args(argv)
    if a.die == 'qwen':
        var = {k_: float(v_) for k_, v_ in (kv.split('=') for kv in filter(None, a.var.split(',')))}
        m = build_qwen(var)
    else:
        v_ = variant_arg(a.ds_var)
        # die-evidence-2 (2026-10-09): a retiled-SM variant (R25G) builds only as a labelled network probe
        m = build(v_, network_probe=bool(v_ and v_.get('sm_physical_grid')))
    cov = dict(Q_COV if a.die == 'qwen' else COV)
    for kv in filter(None, a.cov.split(',')):
        k_, v = kv.split('=')
        cov[k_] = float(v)
    if a.die == 'qwen' and a.mode == 'check':
        print(json.dumps(q_check(m), indent=1))
        return 0
    if a.die == 'qwen' and a.mode == 'plan':
        out = ROOT / Q_OUT
        out.mkdir(parents=True, exist_ok=True)
        rec = plan_record_qwen(m)
        rec['legality_python'] = _legality(m)
        rec['ir_windows_um'] = ir_windows(m)
        (out / 'floorplan.json').write_text(plan_json(rec) + '\n')
        svg(m, out / 'floorplan.svg', scale=0.03)
        write_def_floorplan(m, out / 'floorplan.def')
        write_sdc_qwen(out / 'domains.sdc')
        print(json.dumps({k_: rec[k_] for k_ in ('die', 'instances', 'placed_footprint_mm2', 'legality_python', 'power')},
                         indent=1))
        return 0
    if a.die == 'qwen' and a.mode in ('record', 'price'):
        import hbm_accel_die_price as PR
        if a.mode == 'record':
            return PR.record(m, a.work, a.out or ROOT / Q_OUT / 'feasibility.json', a.only)
        return PR.price_qwen(m, a.work, a.out)
    if a.mode == 'check':
        print(json.dumps(_legality(m), indent=1))
        pc = pin_clashes(m)
        pc16 = pin_clashes(m, 16)
        print(json.dumps(dict(generated_pin_clashes=len(pc), examples=pc[:10], k16_clashes=len(pc16), k16_examples=pc16[:5])))
        print(json.dumps(class_bounds(manhattan_paths(m)), indent=1))
        print(json.dumps(dict(die_mm2=round(m['geo']['W'] * m['geo']['H'] / 1e6, 2), W=m['geo']['W'], H=m['geo']['H'],
                              notes=m['notes'], power=die_power(m)['peak_in_phase_w'])))
        ml = margin_lint(m)
        print(json.dumps(dict(margin_lint=ml), indent=1))
        if a.out:       # the hop list of the die-timing classifier (S81 method, tools/s81/sta_path_classes.py)
            print(json.dumps(plan_dump(m, a.out.resolve())))
        return 3 if ml['verdict'] == 'FAIL' else 0
    if a.mode == 'irwin':
        print(' '.join(ir_windows(m)))
        return 0
    if a.mode == 'plan':
        # --out: write the plan elsewhere (a variant build must not overwrite the committed default-die record)
        out = a.out.resolve() if a.out else ROOT / OUT
        out.mkdir(parents=True, exist_ok=True)
        rec = plan_record(m)
        rec['legality_python'] = _legality(m)
        rec['ir_windows_um'] = ir_windows(m)
        (out / 'floorplan.json').write_text(plan_json(rec) + '\n')
        svg(m, out / 'floorplan.svg')
        write_def_floorplan(m, out / 'floorplan.def')
        write_sdc(out / 'domains.sdc', m)
        print(json.dumps({k_: rec[k_] for k_ in ('die', 'instances', 'placed_footprint_mm2', 'legality_python',
                                                  'manhattan_class_bounds', 'power')}, indent=1))
        return 0
    if a.mode == 'record':
        import hbm_accel_die_price as PR
        return PR.record(m, a.work, a.out, a.only)
    if a.mode == 'floor':
        import hbm_accel_die_price as PR
        PR.floor(m)
        return 0
    if a.mode == 'price':
        import hbm_accel_die_price as PR
        return PR.price(m, a.work, a.out)
    if a.work is None:
        ap.error('--work required')
    work = a.work.resolve()
    if a.mode == 'real':
        print(json.dumps(case_real(m, work)))
    elif a.mode == 'grt':
        gw = tuple(float(v_) for v_ in a.grt_win.split(',')) if a.grt_win else None
        print(json.dumps(_jsonable(case_grt(m, work, a.k, a.tag, a.iters, cov, empty=a.empty, win=gw, m45=a.m45 if a.m45 is not None else m['variant'].get('grt_m45')))))
    elif a.mode == 'ir':
        print(json.dumps(case_ir(m, work, a.window, cov)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
