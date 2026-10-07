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
import re
import sys
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


def stage_um(m):
    """die register-hop pitch of forwarded-clock station segments (430.56 um; forwarded reach 491 um)"""
    return LINK_STAGE_UM


REACH_INTER_UM, REACH_INTRA_UM = 359.0, 412.0       # budgets_20261006: SS reach at the 150 ps / 90 ps skew terms


def seg_stages(m, bid, L):
    """r17 (budget stage plan): register hops of one staged segment.  A forwarded-clock segment (station to station,
    the clock travels with the data) at 430.56 um; a common-clock segment (hub nets, the first hop out of a clocked
    source, the last hop into a block) as the budget prices a region-crossing path: one hop at the inter reach, the rest
    at the intra reach (>= the intra-only count).  Rounds before r17: ceil(L / 430.56) everywhere."""
    if L <= 0:
        return 0
    if not (m.get('variant') or {}).get('budget_stages') or bid in m.get('fclk', {}):
        return math.ceil(L / LINK_STAGE_UM)
    return 1 + math.ceil(max(0.0, L - REACH_INTER_UM) / REACH_INTRA_UM)
CLK_HZ = 1.2e9
FINAL_ROUND = 'r19'             # (r16g until 09:30 PT; r16h = r16g + router_env + pin rules; r16i = r16h + index_q bands; r16j = r16i + svc x-band segments; r17 = r16j + budget stage plan)
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
ADOPTED = R19


def build(variant=None):
    variant = dict(variant if variant is not None else ADOPTED)
    Q.CORNER_RULE.clear()
    Q.CORNER_RULE.update(variant.get('corner_rule', {}))
    Q.PIN_CENTRE.clear()
    Q.PIN_CENTRE.update(variant.get('pin_centre', {}))
    smw, smh = sm_dims() if 'sm_wh' not in variant else (up(variant['sm_wh'][0], GX) - SHAVE, up(variant['sm_wh'][1], GY) - SHAVE)
    strip_d = variant.get('strip_d', STRIP_D)
    grp_w = 4 * (smw + SHAVE) + 5 * CH
    grp_h = 2 * (smh + SHAVE) + 2 * CH
    mid_ch = up(variant.get('mid_ch', 2592.0), GX)
    core_w = 2 * grp_w + mid_ch
    W = up(EDGE + SCH + core_w + SCH + strip_d + EDGE, GX)
    side_h = EDGE + PHY_H + 8.64 + SVC_D + SVC_GAP + grp_h
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
                    sx = up(gx + CH + col * (smw + SHAVE + CH), GX)
                    if side == 'S':
                        sy = up(yg + CH + row * (smh + SHAVE + CH), GY) if row else up(yg + 0.0, GY)
                    else:
                        if variant.get('n_mirror_fix'):     # r10: r1-r8 abutted N row 1 on the hub band (no CH)
                            sy = dn(yg + grp_h - (smh + SHAVE) - row * (smh + SHAVE + CH), GY)
                        else:
                            sy = dn(yg + grp_h - (smh + SHAVE) - (CH + row * (smh + SHAVE + CH) if row else 0.0), GY)
                    i = 8 * 'SW SE NW NE'.split().index(st) + 4 * row + col
                    my = variant.get('w_my') and half == 'W'      # r10: W groups mirrored, x face toward the centre
                    if variant.get('orient_fix'):     # r15: bool() -- r1-r14b compared with None (True on S too)
                        flip = (side == 'N') != bool(variant.get('row1_flip') and row == 1)
                    else:
                        flip = (side == 'N') != (variant.get('row1_flip') and row == 1)   # r12: row 1 mirrored about x
                    ori = ('R180' if my else 'MX') if flip else ('MY' if my else 'R0')
                    it = Inst(f'sm{i}', 'hfd_sm', sx, sy, smw, smh, ori, kind='sm', region=f'grp_{st}')
                    it.sm = dict(stack=st, row=row, col=col)
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
                  domain='serial_0p9' if n == 'quant' else 'stream_1p2')
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
                  kind='spine', region='hub', domain='serial_0p9')
        assert it.y + it.h <= hy1, ('spine slot above the hub band', n_, it.y + it.h, hy1)
        insts.append(it)
        hub[n_] = it
        yy = it.y + h_
    if 'router_env' in variant:      # r16h: scoped router envelope (loader / cmdproc fixed, taken from their gaps)
        ry, rh = variant['router_env']
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
    xw, xe = quarters('su', BLOCKS['su'][0] + BLOCKS['su_fused'][0], sx0 - spch, sx0 + spine_w + spch)
    xw, xe = quarters('sfu', BLOCKS['sfu'][0], xw, xe)
    xw, xe = quarters('hc', BLOCKS['hc'][0], xw, xe)
    regions.append(dict(name='centre', kind='hub', rect=[hub['hc_SW'].x, hy0, hub['hc_SE'].x + hub['hc_SE'].w, hy1]))
    # Historical r14b remains replayable. Measured-macro revisions must supply
    # both dimensions: an area-only square can lose the required halo/grid fit.
    tw = up(variant.get('attn_tile_w_um', math.sqrt(BLOCKS['attn_tile'][0] * 1e6)), GX)
    th = up(variant.get('attn_tile_h_um', BLOCKS['attn_tile'][0] * 1e6 / tw), GY)
    tg = 43.2
    assert 4 * th + 3 * tg <= qh + 1e-6, ('attention tiles do not fit the quadrant', 4 * th + 3 * tg, qh)
    iw = up(BLOCKS['index'][0] / 4 * 1e6 / qh, GX)
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
        ix = Inst(f'hb_index_{st}', 'hfd_index_q', ix_x, qy, iw - SHAVE, qh - SHAVE, qori(st), kind='hub', region='hub')
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
    m['buses'], m['paths'] = buses(m)
    if variant.get('stn_share'):
        share_stations(m)
    if variant.get('child_contract'):
        from hbm_die_child_contract import allocations
        m['child_reservations'] = allocations(m)
    if variant.get('split_masters'):
        apply_splits(m, variant['split_masters'], variant.get('split_lattice'))
    if variant.get('split_x_masters'):
        apply_splits_x(m, variant['split_x_masters'])
    if variant.get('barrier_low'):
        fix_ports_from_views(m, ['hfd_barrier'])
    if variant.get('vm_split'):
        split_vm(m)
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


# index_q bands are NOT in the list (r16b a_real, measured + derived): they are placed both R0 and x-mirrored (MY /
# R180).  With M5 pins on x = 0.012 mod 0.048 and an M7 pin on x = 0.016 mod 0.064, an R0 copy needs the M7 pin at
# local x = 0 mod 0.016 and an x-mirrored copy at 0.008 mod 0.016: no single master has a legal origin in both.  Their
# edge ck stays; the budget re-plans their die entry target from the measured insertion (the die tree arrives early).
CK_CENTRE = ('hfd_svc_SE_s0', 'hfd_svc_SE_s3', 'hfd_svc_SW_s0', 'hfd_svc_SW_s1', 'hfd_svc_SW_s7')   # SW_s1 / SW_s7: edge-ck insertion 1,304 / 1,123 ps


def ck_centre(mst_, sp_):
    """r18 (views agent REQUEST 20:25 / 21:30, measured insertion 927-1,324 ps > the 900 ps target with ck at a band
    edge): the band's ck is an M7 area pin at the band centre (0.064 x 0.288 um on the M7 track between the 10.8 um PG
    stripes: x = 5.4 + 10.8 k + 0.032 nearest the centre; y on the 0.048 grid); the die clock leaf drops onto it from
    M8 (the die owns M8 / M9).  rst stays on its edge."""
    if mst_.name not in CK_CENTRE or 'ck' not in sp_:
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
    'f_su_NE': 'ne', 't_su_NE': 'ne', 'xNE': 'ne', 'qNE': 'ne', 'iNE': 'ne'}
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
    Wf, Hf = vm.w + SHAVE, vm.h + SHAVE
    wl = dn(Wf / 2, GX)
    hb_ = dn(Hf / 2, GY)
    geo = dict(sw=(0.0, 0.0, wl, hb_), se=(wl, 0.0, Wf - wl, hb_), nw=(0.0, hb_, wl, Hf - hb_), ne=(wl, hb_, Wf - wl, Hf - hb_))
    tiles = {}
    for q, (dx, dy, w, h) in geo.items():
        tiles[q] = Inst(f'hb_vm_{q}', f'hfd_vm_{q}', round(vm.x + dx, 4), round(vm.y + dy, 4), round(w - SHAVE, 4),
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
        for bn, b in bands:
            recs[bn] = json.loads((ROOT / rel).parent.joinpath(bn, 'ports.json').read_text())
            spec, order = _split_spec(recs[bn]['ports'])
            def fn(mst, k=1, spec=spec, order=order):
                sp_ = dict(spec)
                if k > 1:
                    _bundle_pack(mst, sp_, order, k)
                if V_ck:
                    ck_centre(mst, sp_)
                mst.ports, mst.order = sp_, list(order)
            fixed[bn] = fn
        owner = {pp: bn for bn, b in bands for pp in b['parent_ports']}
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


def _bundle_pack(mst, sp_, order, k):
    """bundled view (k > 1): runs of one face packed apart (>= two bundled tracks between runs)."""
    byf = defaultdict(list)
    for pn in order:
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


def apply_splits_x(m, rel):
    """r16j: x-axis split (hbm_die_split_x.v1).  Each instance of a split parent is replaced by its bands in the same
    slot (same orientation; MY / R180 mirror the band x), parent-port bus ends move to the owning band under its band
    port name (port_map), a bus on a port split by bit range (the svc PHY dfi bundle) becomes one bus per band whose
    real-macro end is the slice 'dfi@lo:hi', ck / rst reach every band, and the record's cross buses join abutting
    bands of each parent instance."""
    V_ck = (m.get('variant') or {}).get('ck_centre')
    sp = json.loads((ROOT / rel).read_text())
    fixed = m.setdefault('fixed_ports', {})
    for bn in sp['bands']:
        rec = json.loads((ROOT / rel).parent.joinpath(bn, 'ports.json').read_text())
        spec, order = _xy_or_split_spec(rec['ports'])
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
        split = [e for _, e in hit if e[1] not in ('ck', 'rst') and len(pmap[e[0]][e[1]]) > 1]
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
            reg[key] = f'hfd_{kind}_r{len(reg)}'
            faces[reg[key]] = {p: f for p, f, _ in key[3] if f != '-'}
        it.master = reg[key]
        it.orient = o
    m['stn_faces'] = faces
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
    n_wp = [0]
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
    ctl_up = 4 if V.get('sm_desc') else 3                            # busy / arrive / released (+ d_ready)
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
            ((('iv', 33), ('rv', 33)) if m['variant'].get('fwd_hub') else ()):
        sp_off[n_] = pos + nb * 1.2 / 2
        pos += nb * 1.2 + 40.0
    pos = 30.0
    for n_, nb in (('lk0', 64), ('lk1', 64), ('lk2', 64), ('ef', 8), ('ct', 23), ('xt', 129), ('rt', 135)):
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
        cxs = [G['x'] + CH / 2 + c * (smw + CH) for c in range(5)]
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
            nb = W_RES * 2 * {0: 1, 3: 1, 1: 2, 2: 4}[c]
            fa = {0: 'W', 1: 'W', 2: 'E', 3: 'E'}[c]
            gs[c] = station(cxs[rch(c)], gy, f'rg{st}{c}', nb, fa, 'N' if side == 'S' else 'S', False, kind='gath',
                            extra=(up((nb + 2 * W_RES) * 0.048 * 1.1 + 24, GX), up((nb + 2 * W_RES) * 0.048 * 1.1 + 24, GY)),
                            fifo_bits=W_RES * 4 if (fwd and c == 2) else 0)
            if fwd:     # r15: gather stations launch from their column half's local clock
                m.setdefault('clocked', {})[gs[c].name] = 'stream'
            faces[gs[c].master].update(t0='E' if my else 'W', t1='E' if my else 'W', a2='W')
            for r_ in (0, 1):
                s = by_rc[(r_, c)]
                B.append((f'rl_{s.name}', 'result_leaf', W_RES, [(s.name, 'r'), (gs[c].name, f't{r_}')]))
        B.append((f'rh_{st}_0', 'result_trunk', W_RES * 2, [(gs[0].name, 'b'), (gs[1].name, 'a')]))
        B.append((f'rh_{st}_3', 'result_trunk', W_RES * 2, [(gs[3].name, 'b'), (gs[2].name, 'a')]))
        B.append((f'rh_{st}_1', 'result_trunk', fcw(f'rh_{st}_1', W_RES * 4, W_RES * 4), [(gs[1].name, 'b'), (gs[2].name, 'a2')]))
        tgt = _cxy(su, 'W' if half == 'W' else 'E', 0.3 if side == 'S' else 0.7) if False else \
            _cxy(su, 'S' if side == 'S' else 'N', 0.3 + 0.4 * (half == 'E'))
        g2 = gs[2]
        yr_ = ylane(side, 'rt', ych[side] - 40.0 * sgn)
        pts = [(g2.x + g2.w / 2, g2.y + g2.h / 2), (cc + 40.0, g2.y + g2.h / 2), (cc + 40.0, yr_), (tgt[0], yr_), tgt]
        chain(f'rt_{st}', 'result_trunk', W_RES * 8, (g2.name, 'b'), (su.name, 'r' if pf else f'r{st}'), pts,
              fc=(W_RES * 8,))
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
        chain(f'ef_{st}', 'expert_req', 128, (rt.name, f'e{st}'), (svc.name, 'e'), pts, path=f'expert_req_{st}',
              fc=(128,))
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
        B.append((f'iv_{st}', 'hub', 512, [(sc['index'].name, 't_vm'), (vm.name, f'i{st}')]))
        P[f'attn_out_{st}'] = [f'tr_{st}0', f'ao_{st}']
    # ---- hub internal (adjacent slabs across one channel, or vertical in the spine column): direct nets; their
    #      stage count is read from the routed length
    crtl = V.get('coll_rtl')
    if crtl:    # r15 (H9): ot_hbm_accel_tu_endpoint rank[7:0] / pf[15:0] / go in, fault / stat_credit_stall[31:0] out
        hl_ = [('cmdproc', 'coll', 8 + 16 + 1), ('coll', 'cmdproc', 1 + 32)]
    else:
        hl_ = [('cmdproc', 'coll', 64)]
    hl_ += [('loader', 'cmdproc', 341), ('barrier', 'cmdproc', 64), ('router', 'cmdproc', 64),
            ('vm', 'quant', 1024), ('vm', 'router', 512)] + ([] if crtl else [('vm', 'coll', 512)])
    if V.get('hub_io'):     # r15 (H10): the barrier's arrive input (SM arrives ride the control tree to the cmdproc)
        hl_ += [('cmdproc', 'barrier', 64)]
    for q in ('SW', 'SE', 'NW', 'NE'):
        # coll_rtl: SU quarter -> endpoint inject data (inj_data 2 x 512, muxed by the fan-in inside the block);
        # endpoint -> SU quarter: delivery lane del_flit 545 + del_valid + inj_idx 2 x 16 + inj_rd 2 = 580
        hl_ += [('vm', f'su_{q}', 2048), (f'su_{q}', 'vm', 2048), (f'su_{q}', f'sfu_{q}', 1024), (f'sfu_{q}', f'hc_{q}', 1024),
                (f'su_{q}', 'coll', 1024), ('coll', f'su_{q}', 580 if crtl else 1024), ('quant', f'su_{q}', 512),
                ('cmdproc', f'su_{q}', 64), (f'su_{q}', 'router', 256)]
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
        chain('host', 'host', 512, (ld.name, 'h'), (hl.name, 'iox'), pts, path='host', fc=(256, 256), meso_end=True,
              dom='link')
        if fwd:
            m.setdefault('meso', []).append(dict(inst=ld.name, kind='spine', chain='host (rx)', fifo_bits=256, slices=1,
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
        for st in ('SW', 'SE', 'NW', 'NE'):
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
                  meso_end=True, local_src=True, first_um=HCH / 2 + 60.0)
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
            key = (by[inst].master, port)
            w[key] = max(w.get(key, 0), n)
    return w


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
    pf = m['variant'].get('port_fix')
    for bid, cls, bits, eps in m['buses']:
        for i, (inst, port) in enumerate(eps):
            it = by[inst]
            key = (it.master, port)
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
            others = [by[o] for j, (o, _) in enumerate(eps) if j != i]
            peers[key] += others
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
        ox = sum(o.x + o.w / 2 for o in others) / len(others)
        oy = sum(o.y + o.h / 2 for o in others) / len(others)
        lx, ly = ox - it.x, oy - it.y
        if mname == 'hfd_sm':
            face = sm_fixed[port]                          # master frame
        elif mname in m['stn_faces'] and port in m['stn_faces'][mname]:
            face = m['stn_faces'][mname][port]             # stations are placed R0
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
        if m['variant'].get('face_fix') and (mname, port) in FACE_FIX:
            # r16g: role ports of shared masters on their fixed master-frame face (r16e lint: the corner-tile KV pin
            # and three SU result pins took their face from another copy's peer and faced away on the mirrors)
            face = FACE_FIX[(mname, port)]
            along = ly if face in 'EW' else lx
        if mname == 'hfd_sm' and port in ('x', 'c') and m['variant'].get('sm_xmid'):
            along = sum(sm_span[face]) / 2      # r12 option: x / c pins centred in their pin region (row-neutral)
        items[mname][face].append((along, port))
    for mname, fs in items.items():
        mst = M[mname]
        for face, lst in fs.items():
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
            if mname.startswith(('hfd_stn', 'hfd_mcast', 'hfd_gath', 'hfd_cdist', 'hfd_meso')) or mname == 'hfd_sm':
                pitch = 2 if 2 * sum(n) * p + (len(n) - 1) * gap <= room else 1
            need = [x * p * pitch for x in n]
            if sum(need) + gap * (len(n) - 1) > room + 1e-6:
                raise ValueError(f'{mname} face {face}: {sum(need):.1f} um of pins on {room:.1f} um')
            pos, starts = a0, []
            spread = mname in SPREAD_MASTERS and not m['variant'].get('no_spread') and full >= 500.0 and mname != 'hfd_sm' and not mname.startswith(('hfd_svc_', 'hfd_stn', 'hfd_mcast',
                                                                                      'hfd_gath', 'hfd_cdist'))
            if spread:          # r4 spread every hub port evenly: overflow 2,519 -> 5,223; r6: coll / VM only
                g_even = (room - sum(need)) / (len(need) + 1)
                gap = max(gap, g_even)
                pos = a0 + g_even
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
        t, n = S.lef_text(mst, k, wmap)
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
        rects = sorted(S.pin_rects(mst, k, {p: pw.get((name, p), 0) for p in mst.order}), key=lambda r: (r[1], r[2][0]))
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


def write_netlist(m, k, path, top='hfd_die'):
    rp = real_ports(m) if k == 1 else {}
    by = {it.name: it for it in m['insts']}
    conns = defaultdict(list)
    V = [f'// tools/hbm_accel_die_fp.py: die-level nets only (k = {k})', f'module {top} ();']
    for bid, cls, bits, eps in m['buses']:
        n = bits if k == 1 else max(1, math.ceil(bits / k))
        net = f'n_{bid}'
        V.append(f'  wire [{n - 1}:0] {net};')
        for inst, port in eps:
            mst = by[inst].master
            if '@' in port:         # r16j: slice lo:hi of a real or bundled port (svc band <- PHY dfi range)
                base, rng = port.split('@')
                lo, hi = map(int, rng.split(':'))
                if mst in rp and base in rp[mst]:
                    conns[inst].append((rp[mst][base][lo:hi + 1], net))
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
    return dict(instances=len(m['insts']), overlaps=len(ov), overlap_examples=ov[:20], outside=len(out),
                outside_examples=out[:20])


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
    d += ['END COMPONENTS', 'END DESIGN', '']
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
    kv='stream service -> attention tiles (KV rows)',
    ik='stream service -> index (index keys)',
    link='collective endpoint -> SerDes macro',
    hub_su_coll='SU -> collective endpoint',
    hub_coll_su='collective endpoint -> SU',
    host='loader -> host link',
    attn_q='VM -> attention tiles (query operand, r15 attn_rtl: chain + packet hops to the farthest tile)',
)


def path_class(p):
    for k in ('weight', 'xbcast', 'result', 'control', 'expert_req', 'kv', 'ik', 'link', 'host', 'attn_q'):
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
            if by_i[inst].kind == 'waypoint':
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
        Path(path).write_text(SDC_R15)
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
        for h, cols in (('w', (0, 1)), ('e', (2, 3))):
            ss = [s for s in G['sms'] if s.sm['col'] in cols]
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


def case_grt(m, work, k, tag, iters, cov, empty=False):
    from chip_assembly import v41_die as VD
    work.mkdir(parents=True, exist_ok=True)
    npins = write_lefs(m, k, work / 'elements.lef')
    (work / 'tech.lef').write_text(VD.bundled_tech_lef(k))
    mm = dict(m)
    if empty:
        mm['buses'] = [next(b_ for b_ in m['buses'] if b_[1] == 'clock_trunk')]
    write_netlist(mm, k, work / 'die.v')
    W, H = m['geo']['W'], m['geo']['H']
    tracks = [f'make_tracks {n} -x_offset {off * k:.3f} -x_pitch {p * k:.3f} -y_offset {off * k:.3f} -y_pitch {p * k:.3f}'
              for n, d, p, wd, sp, off in VD.ASAP7_LAYERS]
    place = [f'place_inst -name {it.name} -location {{{it.x:.3f} {it.y:.3f}}} -orientation {it.orient} -status FIRM'
             for it in m['insts']]
    adj = []
    for ln in ('M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 'M9'):
        a = 1.0 if ln in ('M2', 'M3', 'M4', 'M5') else (VIA_OBS + 2 * cov['field'] if ln in ('M8', 'M9') else VIA_OBS)
        adj.append(f'set_global_routing_layer_adjustment {ln} {a:.4f}')
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
    man = dict(case='b', tag=tag, bundle_k=k, congestion_iterations=iters, empty_baseline=empty,
               instances=len(m['insts']), bundle_pins=npins,
               bundle_nets=0 if empty else sum(max(1, math.ceil(b[2] / k)) for b in m['buses']),
               wires=0 if empty else sum(b[2] for b in m['buses']), coverage=cov, variant=m['variant'])
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


def variant_arg(v):
    """'' -> the adopted default (r16g); 'r8' -> the r1-r8 geometry; 'r10' / 'r14b' / 'r15' / 'r15m' / 'r16e' presets; a JSON dict
    -> those keys (absent keys = r8 behaviour); a JSON dict with "base": preset -> the preset updated with the keys."""
    if v == 'service-attn-r1':          # Codex child-contract revision: built on the r14b nets (kept replayable)
        return dict(R14B, hub_h=12355.2, attn_tile_w_um=1349.136,
                    attn_tile_h_um=1350.0, child_contract='hbm_child_contract_20261005')
    if not v:
        return None
    pre = dict(r8={}, r10=R10, r14b=R14B, r15=R15, r16e=R16E, r16g=R16G, r16h=R16H, r16i=R16I, adopted=ADOPTED, r15m=dict(R15, hub_h=12355.2, **ATTN_MEAS))
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
    ap.add_argument('--cov', default='')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--only', default='')
    ap.add_argument('--die', choices=['ds', 'qwen'], default='ds', help='ds: the DS SM die (r8); qwen: the Qwen3-8B '
                    'W12 tile die')
    ap.add_argument('--var', default='', help='qwen floorplan variant knobs k=v,... (spine_w, spine_ch)')
    a = ap.parse_args(argv)
    if a.die == 'qwen':
        var = {k_: float(v_) for k_, v_ in (kv.split('=') for kv in filter(None, a.var.split(',')))}
        m = build_qwen(var)
    else:
        m = build()
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
        (out / 'floorplan.json').write_text(json.dumps(rec, indent=1) + '\n')
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
        return 0
    if a.mode == 'irwin':
        print(' '.join(ir_windows(m)))
        return 0
    if a.mode == 'plan':
        out = ROOT / OUT
        out.mkdir(parents=True, exist_ok=True)
        rec = plan_record(m)
        rec['legality_python'] = _legality(m)
        rec['ir_windows_um'] = ir_windows(m)
        (out / 'floorplan.json').write_text(json.dumps(rec, indent=1) + '\n')
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
        print(json.dumps(case_grt(m, work, a.k, a.tag, a.iters, cov, empty=a.empty)))
    elif a.mode == 'ir':
        print(json.dumps(case_ir(m, work, a.window, cov)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
