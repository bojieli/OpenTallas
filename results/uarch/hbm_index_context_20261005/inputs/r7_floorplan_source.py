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
CLK_HZ = 1.2e9

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
TU_PORTS, TU_FLIT = 8, 546      # 545-bit flit + credit, per direction
HBM_RD_BITS = S.HBM_RD_BITS
SU_IN_BITS = 4 * 8 * W_RES      # result gather trunks into the SU
CLK_BITS = 3

# ------------------------------------------------------------------------------------------------ geometry
CH = 259.2                      # SM grid channel (120 rows of 2.16)
HCH = 345.6                     # hub-band routing channel
PHY_W, PHY_H = 8500.056, 1177.2
SVC_D = 259.2
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


def build(variant=None):
    variant = dict(variant or {})
    smw, smh = sm_dims()
    grp_w = 4 * (smw + SHAVE) + 5 * CH
    grp_h = 2 * (smh + SHAVE) + 2 * CH
    mid_ch = up(variant.get('mid_ch', 2592.0), GX)
    core_w = 2 * grp_w + mid_ch
    W = up(EDGE + SCH + core_w + SCH + STRIP_D + EDGE, GX)
    side_h = EDGE + PHY_H + 8.64 + SVC_D + grp_h
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
                yg = up(ys + SVC_D, GY)
                po = 'R0'
            else:
                yp = dn(H - EDGE - PHY_H, GY)
                ys = dn(yp - 8.64 - SVC_D, GY)
                yg = dn(ys - grp_h, GY)
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
                        sy = dn(yg + grp_h - (smh + SHAVE) - (CH + row * (smh + SHAVE + CH) if row else 0.0), GY)
                    i = 8 * 'SW SE NW NE'.split().index(st) + 4 * row + col
                    it = Inst(f'sm{i}', 'hfd_sm', sx, sy, smw, smh, 'R0' if side == 'S' else 'MX', kind='sm',
                              region=f'grp_{st}')
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
        hs[n] = max(hs[n], up(variant.get('spine_face_um', 1404.0), GY))
    cy0 = dn(hmid - hs['coll'] / 2, GY)
    lower, upper = ['loader', 'router', 'cmdproc'], ['vm', 'barrier', 'quant']
    glo = (cy0 - hy0 - sum(hs[n] for n in lower)) / len(lower)
    ghi = (hy1 - (cy0 + hs['coll']) - sum(hs[n] for n in upper)) / len(upper)
    assert min(glo, ghi) >= 43.2, ('spine column too short', glo, ghi)
    place = [('coll', cy0)]
    yy = hy0 + glo / 2
    for n in lower:
        place.append((n, yy))
        yy += hs[n] + glo
    yy = cy0 + hs['coll'] + ghi / 2
    for n in upper:
        place.append((n, yy))
        yy += hs[n] + ghi
    for n, y_ in place:
        it = Inst(f'hb_{n}', f'hfd_{n}', sx0, up(y_, GY), spine_w - SHAVE, hs[n] - SHAVE, kind='spine', region='hub',
                  domain='serial_0p9' if n == 'quant' else 'stream_1p2')
        insts.append(it)
        hub[n] = it
    qh = dn((hh - HCH) / 2, GY)

    def quarters(name, mm2, xw, xe, dom='serial_0p9'):
        """r3: four quarters (SW, NW W of the spine; SE, NE E of it) of qh each around the equator channel, so that
        every stack quadrant has its own quarter on its side of the spine; returns (west x, east x) of the next ring."""
        w = up(mm2 / 4 * 1e6 / qh, GX)
        for q in ('SW', 'SE', 'NW', 'NE'):
            x_ = dn(xw - w, GX) if q[1] == 'W' else up(xe, GX)
            y_ = hy0 if q[0] == 'S' else dn(hy1 - qh, GY)
            it = Inst(f'hb_{name}_{q}', f'hfd_{name}', x_, y_, w - SHAVE, qh - SHAVE, kind='hub', region='hub', domain=dom)
            insts.append(it)
            hub[f'{name}_{q}'] = it
        return dn(xw - w - HCH, GX), up(xe + w + HCH, GX)
    xw, xe = quarters('su', BLOCKS['su'][0] + BLOCKS['su_fused'][0], sx0 - SPCH, sx0 + spine_w + SPCH)
    xw, xe = quarters('sfu', BLOCKS['sfu'][0], xw, xe)
    xw, xe = quarters('hc', BLOCKS['hc'][0], xw, xe)
    regions.append(dict(name='centre', kind='hub', rect=[hub['hc_SW'].x, hy0, hub['hc_SE'].x + hub['hc_SE'].w, hy1]))
    tw = up(math.sqrt(BLOCKS['attn_tile'][0] * 1e6), GX)
    th = up(BLOCKS['attn_tile'][0] * 1e6 / tw, GY)
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
        ix = Inst(f'hb_index_{st}', 'hfd_index_q', ix_x, qy, iw - SHAVE, qh - SHAVE, kind='hub', region='hub')
        insts.append(ix)
        hub[f'index_{st}'] = ix
        ty0 = up(qy + (qh - 4 * th - 3 * tg) / 2, GY)
        grid = []
        for r in range(4):
            row = []
            for c in range(4):
                it = Inst(f'at_{st}_{r}{c}', 'hfd_attn_tile', up(tx0 + c * (tw + tg), GX), up(ty0 + r * (th + tg), GY),
                          tw - SHAVE, th - SHAVE, kind='attn_tile', region='hub')
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
    rs, ru = S.real_lef(SERDES_LEF), S.real_lef(UCIE_LEF)
    links = []
    cxm = geo['cx']
    sd_w = dn(mid_ch - 2 * 64.8, GX)
    sl = up(BLOCKS['serdes'][0] / 2 * 1e6 / sd_w, GY)
    MG = 103.68                                   # channel between macros (pins on each macro's E face)
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
    ux = up(W - EDGE - STRIP_D, GX)
    hsl_w = dn(STRIP_D - ru['w'] - 8.64, GX)
    hsl = up(BLOCKS['host'][0] * 1e6 / hsl_w, GY)
    uy = up(H / 2 - ru['h'] / 2, GY)
    host_mac = Inst('lk_host', ru['name'], ux, uy, ru['w'], ru['h'], 'R0', kind='link', region='link', domain='link')
    insts.append(host_mac)
    hs = Inst('hs_slab', 'hfd_host_slab', up(ux + ru['w'] + 8.64, GX), up(H / 2 - hsl / 2, GY), hsl_w - SHAVE, hsl - SHAVE,
              kind='host_slab', region='link', domain='link')
    insts.append(hs)
    regions.append(dict(name='strip_E', kind='link', rect=[W - EDGE - STRIP_D, EDGE, W - EDGE, H - EDGE]))
    variant.update(W=W, H=H)
    m = dict(geo=geo, insts=insts, regions=regions, groups=groups, hub=hub, tiles=tiles, scan=scan, links=links, host=host_mac,
             notes=notes, variant=variant, stn_faces={})
    m['buses'], m['paths'] = buses(m)
    return m


# ------------------------------------------------------------------------------------------------ nets and waypoints
def _cxy(it, face, along=0.5):
    if face == 'S':
        return (it.x + it.w * along, it.y)
    if face == 'N':
        return (it.x + it.w * along, it.y + it.h)
    if face == 'W':
        return (it.x, it.y + it.h * along)
    return (it.x + it.w, it.y + it.h * along)


def _dirface(ax, ay, bx, by):
    """Face of a block at (ax, ay) that looks toward (bx, by)."""
    if abs(bx - ax) >= abs(by - ay):
        return 'E' if bx > ax else 'W'
    return 'N' if by > ay else 'S'


def buses(m):
    """[(id, class, bits, [(inst, port)])] + named critical paths {path: [bus ids in order]}.  Long paths are chains of
    forwarded-link stations placed in the channels (a station every <= 4 x 430.56 um of route); each station is its own
    abstract with its ports on the faces that look along the route."""
    B, P = [], defaultdict(list)
    insts = m['insts']
    g = m['geo']
    hub = m['hub']
    faces = m['stn_faces']
    n_wp = [0]
    blocked = [(it.x - 4.32, it.y - 4.32, it.x + it.w + 4.32, it.y + it.h + 4.32) for it in insts]

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

    def station(cx, cy, chain, bits, fa, fb, horizontal, kind='stn', extra=None):
        w, h = stn_size(bits, horizontal)
        if extra:
            w, h = max(w, extra[0]), max(h, extra[1])
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
        return it

    def chain(cid, cls, bits, src, dst, pts, path=None):
        """src/dst = (inst, port); pts = polyline through channels; stations every <= WAYPOINT_UM along it.  dst None:
        leave the chain open and return (last endpoint, bus ids)."""
        seq = []
        acc = 0.0
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
            st = station(x, y, cid, bits, fa, fb, hor)
            bid = f'{cid}_{j}'
            B.append((bid, cls, bits, [prev, (st.name, 'a')]))
            ids.append(bid)
            prev = (st.name, 'b')
        if dst is None:
            if path:
                P[path] += ids
            return prev, ids
        bid = f'{cid}_e'
        B.append((bid, cls, bits, [prev, dst]))
        ids.append(bid)
        if path:
            P[path] += ids
        return bid

    def sm_face(it, port):
        f = SM_FACE[port]
        if it.orient == 'MX' and f in 'NS':
            f = 'S' if f == 'N' else 'N'
        return f
    yb0, yb1 = g['side_h'], g['H'] - g['side_h']
    ych = dict(S=yb0 + HCH / 2, N=yb1 - HCH / 2)          # hub-band edge channels
    smw = m['groups']['SW']['sms'][0].w + SHAVE
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
        # (1) weight stream
        for s in sms:
            sid = s.name
            c = s.sm['col']
            if s.sm['row'] == 0:
                B.append((f'wl_{sid}', 'weight', W_LINE, [(svc.name, f'l{sid}'), (sid, 'd')]))
                P[f'weight_{sid}'].append(f'wl_{sid}')
            else:
                dx = s.x + s.w / 2
                pts = [(cxs[c], svc.y + (svc.h if side == 'S' else 0.0)), (cxs[c], y_mid), (dx, y_mid)]
                chain(f'wl_{sid}', 'weight', W_LINE, (svc.name, f'l{sid}'), (sid, 'd'), pts, path=f'weight_{sid}')
            B.append((f'rq_{sid}', 'weight_req', W_REQ, [(sid, 'q'), (svc.name, f'q{sid}')]))
        # spine-side vertical channel (between the spine and the SU / SFU halves) and the group's centre column
        # channel (channel 2) that every tree enters by
        vm = hub['vm']
        xs_sp = hub['vm'].x - SPCH / 2 if half == 'W' else hub['vm'].x + hub['vm'].w + SPCH / 2
        xs_sp += (-60.0 if half == 'W' else 60.0) * (side == 'N')
        cc = cxs[2]
        # (2) activation multicast tree: VM -> spine-side channel -> hub edge channel -> channel 2 -> mid-row channel;
        #     a multicast station per SM column (channel c, west of column c) taps both SMs of the column; the tree
        #     splits at channel 2 into a west arm (1, 0) and an east arm (3)
        root = _cxy(vm, 'W' if half == 'W' else 'E', 0.3 if side == 'S' else 0.7)
        pts = [root, (xs_sp, root[1]), (xs_sp, ych[side] + 20.0 * sgn), (cc - 20.0, ych[side] + 20.0 * sgn), (cc - 20.0, y_mid)]
        prev, trunk = chain(f'xt_{st}', 'x_trunk', W_X, (vm.name, f'x{st}'), None, pts)
        ms = {}
        ms[2] = station(cc, y_mid, f'xm{st}2', W_X, 'N' if side == 'S' else 'S', 'W', False, kind='mcast',
                        extra=(up(2 * W_X * 0.048 * 1.1 + 24, GX), up(2 * W_X * 0.048 * 1.1 + 24, GY)))
        faces[ms[2].master].update(b2='E', t0='S' if side == 'S' else 'N', t1='N' if side == 'S' else 'S')
        B.append((f'xh_{st}_2', 'x_trunk', W_X, [prev, (ms[2].name, 'a')]))
        arm = {2: [f'xh_{st}_2']}
        for c, frm, port in ((1, 2, 'b'), (0, 1, 'b'), (3, 2, 'b2')):
            ms[c] = station(cxs[c], y_mid, f'xm{st}{c}', W_X, 'E' if c < 2 else 'W', 'W' if c < 2 else 'E', True,
                            kind='mcast', extra=(up(W_X * 0.048 * 1.1 + 24, GX), 0))
            faces[ms[c].master].update(t0='S' if side == 'S' else 'N', t1='N' if side == 'S' else 'S')
            bid = f'xh_{st}_{c}'
            B.append((bid, 'x_trunk', W_X, [(ms[frm].name, port), (ms[c].name, 'a')]))
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
            gs[c] = station(cxs[c + 1], gy, f'rg{st}{c}', nb, fa, 'N' if side == 'S' else 'S', False, kind='gath',
                            extra=(up((nb + 2 * W_RES) * 0.048 * 1.1 + 24, GX), up((nb + 2 * W_RES) * 0.048 * 1.1 + 24, GY)))
            faces[gs[c].master].update(t0='W', t1='W', a2='W')
            for r_ in (0, 1):
                s = by_rc[(r_, c)]
                B.append((f'rl_{s.name}', 'result_leaf', W_RES, [(s.name, 'r'), (gs[c].name, f't{r_}')]))
        B.append((f'rh_{st}_0', 'result_trunk', W_RES * 2, [(gs[0].name, 'b'), (gs[1].name, 'a')]))
        B.append((f'rh_{st}_3', 'result_trunk', W_RES * 2, [(gs[3].name, 'b'), (gs[2].name, 'a')]))
        B.append((f'rh_{st}_1', 'result_trunk', W_RES * 4, [(gs[1].name, 'b'), (gs[2].name, 'a2')]))
        tgt = _cxy(su, 'W' if half == 'W' else 'E', 0.3 if side == 'S' else 0.7) if False else \
            _cxy(su, 'S' if side == 'S' else 'N', 0.3 + 0.4 * (half == 'E'))
        g2 = gs[2]
        pts = [(g2.x + g2.w / 2, g2.y + g2.h / 2), (cc + 40.0, g2.y + g2.h / 2), (cc + 40.0, ych[side] - 40.0 * sgn),
               (tgt[0], ych[side] - 40.0 * sgn), tgt]
        chain(f'rt_{st}', 'result_trunk', W_RES * 8, (g2.name, 'b'), (su.name, f'r{st}'), pts)
        tr = [b[0] for b in B if b[0].startswith(f'rt_{st}_')]
        up_arm = {0: [f'rh_{st}_0', f'rh_{st}_1'], 1: [f'rh_{st}_1'], 3: [f'rh_{st}_3'], 2: []}
        for s in sms:
            P[f'result_{s.name}'] = [f'rl_{s.name}'] + up_arm[s.sm['col']] + tr
        # (4) control tree (start / op descriptors out, busy / arrive back; the barrier rides it): cmdproc ->
        #     spine-side channel -> hub edge channel -> a distribution station in channel 2 at the hub-side row
        #     channel (row 1) and one at the mid-row channel (row 0) -> 46-bit leaves to each SM's c face
        cp = hub['cmdproc']
        cpt = _cxy(cp, 'W' if half == 'W' else 'E', 0.3 if side == 'S' else 0.7)
        xcp = xs_sp + (-100.0 if half == 'W' else 100.0)
        yh = ych[side] + 60.0 * sgn
        pts = [cpt, (xcp, cpt[1]), (xcp, yh), (cc + 60.0, yh), (cc + 60.0, y_top)]
        prev, ctr = chain(f'ct_{st}', 'control', 8 * W_CTL, (cp.name, f'c{st}'), None, pts)
        d1 = station(cc + 60.0, y_top, f'cd{st}1', 8 * W_CTL, 'N' if side == 'S' else 'S', 'S' if side == 'S' else 'N',
                     False, kind='cdist', extra=(up(8 * W_CTL * 0.048 * 2.2 + 24, GX), up(4 * W_CTL * 0.048 * 2.2 + 24, GY)))
        B.append((f'cd_{st}_1', 'control', 8 * W_CTL, [prev, (d1.name, 'a')]))
        d0 = station(cc + 60.0, y_mid, f'cd{st}0', 4 * W_CTL, 'N' if side == 'S' else 'S', 'S' if side == 'S' else 'N',
                     False, kind='cdist', extra=(up(4 * W_CTL * 0.048 * 2.2 + 24, GX), up(4 * W_CTL * 0.048 * 2.2 + 24, GY)))
        B.append((f'cd_{st}_0', 'control', 4 * W_CTL, [(d1.name, 'b'), (d0.name, 'a')]))
        for s in sms:
            d = d1 if s.sm['row'] == 1 else d0
            B.append((f'cl_{s.name}', 'control_leaf', W_CTL, [(d.name, f't{s.sm["col"]}'), (s.name, 'c')]))
            P[f'control_{s.name}'] = ctr + [f'cd_{st}_1'] + ([f'cd_{st}_0'] if s.sm['row'] == 0 else []) + [f'cl_{s.name}']
        # (5) expert-fetch descriptor: router -> spine-side channel -> hub edge channel -> channel 2 -> svc N face
        rt = hub['router']
        p0 = _cxy(rt, 'W' if half == 'W' else 'E', 0.5)
        xr = xs_sp + (-140.0 if half == 'W' else 140.0)
        sn = _cxy(svc, 'N' if side == 'S' else 'S', (cc + 80.0 - svc.x) / svc.w)
        pts = [p0, (xr, p0[1]), (xr, ych[side] + 100.0 * sgn), (cc + 80.0, ych[side] + 100.0 * sgn), sn]
        chain(f'ef_{st}', 'expert_req', 128, (rt.name, f'e{st}'), (svc.name, 'e'), pts, path=f'expert_req_{st}')
        # (6) KV rows -> the stack's scan quadrant (attention tiles nearest the stack) and index keys -> its index
        #     quarter: svc outer end -> outer column channel -> hub edge channel -> quadrant face
        sc = m['scan'][st]
        rowt = sc['tiles'][0] if side == 'S' else sc['tiles'][-1]
        for name, tgt_inst, port, off in (('kv', rowt[0] if half == 'W' else rowt[-1], f'k{st}', -50.0),
                                          ('ik', sc['index'], f'k{st}', 50.0)):
            tp = _cxy(tgt_inst, 'S' if side == 'S' else 'N', 0.5)
            so = _cxy(svc, 'W' if half == 'W' else 'E', 0.3 if name == 'kv' else 0.7)
            yy_ = ych[side] + 40.0 * sgn * (1 if name == 'kv' else -1)
            eo = min(range(5), key=lambda c_: abs(cxs[c_] - tp[0]) + abs(cxs[c_] - so[0]))
            sn = _cxy(svc, 'N' if side == 'S' else 'S', (cxs[eo] + off - svc.x) / svc.w)
            pts = [sn, (cxs[eo] + off, yy_), (tp[0], yy_), tp]
            chain(f'{name}_{st}', 'kv_rows', 1024, (svc.name, name), (tgt_inst.name, port), pts, path=f'{name}_{st}')
        # scan quadrant internals: tile row chains (outer -> inner), row end -> index quarter -> SU; KV down the
        # columns; index quarter -> VM (local top-k for the merge)
        grid = sc['tiles']
        for r in range(4):
            row = grid[r] if half == 'W' else grid[r][::-1]
            for a_, b_ in zip(row, row[1:]):
                B.append((f'ta_{a_.name}', 'attn_chain', 512, [(a_.name, 'o'), (b_.name, 'i')]))
            B.append((f'tr_{st}{r}', 'attn_root', 512, [(row[-1].name, 'o'), (sc['index'].name, f'a{r}')]))
        for c in range(4):
            for r in range(3):
                lo, hi_ = (grid[r][c], grid[r + 1][c]) if side == 'S' else (grid[3 - r][c], grid[2 - r][c])
                B.append((f'tk_{st}{r}{c}', 'attn_kv', 1024, [(lo.name, 'ku'), (hi_.name, 'kd')]))
        B.append((f'ao_{st}', 'attn_out', 1024, [(sc['index'].name, 't_su'), (hub[f'su_{st}'].name, f'a{st}')]))
        B.append((f'iv_{st}', 'hub', 512, [(sc['index'].name, 't_vm'), (vm.name, f'i{st}')]))
        P[f'attn_out_{st}'] = [f'tr_{st}0', f'ao_{st}']
    # ---- hub internal (adjacent slabs across one channel, or vertical in the spine column): direct nets; their
    #      stage count is read from the routed length
    hl_ = [('cmdproc', 'coll', 64), ('loader', 'cmdproc', 341), ('barrier', 'cmdproc', 64), ('router', 'cmdproc', 64),
           ('vm', 'quant', 1024), ('vm', 'router', 512), ('vm', 'coll', 512)]
    for q in ('SW', 'SE', 'NW', 'NE'):
        hl_ += [('vm', f'su_{q}', 2048), (f'su_{q}', 'vm', 2048), (f'su_{q}', f'sfu_{q}', 1024), (f'sfu_{q}', f'hc_{q}', 1024),
                (f'su_{q}', 'coll', 1024), ('coll', f'su_{q}', 1024), ('quant', f'su_{q}', 512), ('cmdproc', f'su_{q}', 64),
                (f'su_{q}', 'router', 256)]
    hl_ += [('su_SW', 'su_SE', 1024), ('su_SE', 'su_SW', 1024), ('su_SW', 'su_NW', 1024), ('su_NW', 'su_SW', 1024),
            ('su_SE', 'su_NE', 1024), ('su_NE', 'su_SE', 1024), ('su_NW', 'su_NE', 1024), ('su_NE', 'su_NW', 1024)]
    for a_, b_, bits in hl_:
        B.append((f'hb_{a_}_{b_}', 'hub', bits, [(hub[a_].name, f't_{b_}'), (hub[b_].name, f'f_{a_}')]))
        P[f'hub_{a_}_{b_}'] = [f'hb_{a_}_{b_}']
    # ---- collective -> SerDes: 8 TU ports x 546 b each direction striped over the 9 macros (S centre 5, N centre 4):
    #      spine-side channel -> hub edge channel -> the channel east of the macro -> its E-face pins
    coll = hub['coll']
    tot = TU_PORTS * TU_FLIT * 2
    per = math.ceil(tot / len(m['links']))
    for i, lk in enumerate(m['links']):
        side = lk.name[3]
        j = int(lk.name[4:])
        east = lk.x + lk.w / 2 > coll.x + coll.w / 2
        p0 = _cxy(coll, 'E' if east else 'W', 0.15 + 0.14 * j + (0.0 if side == 'S' else 0.07))
        xsp = (coll.x + coll.w + SPCH / 2 + 60.0 * j - 120.0) if east else (coll.x - SPCH / 2 - 60.0 * j + 120.0)
        yh = ych[side] + (-40.0 * j - 20.0) * (1 if side == 'S' else -1)
        xg = lk.x + lk.w + 103.68 / 2
        ym = lk.y + lk.h / 2
        pts = [p0, (xsp, p0[1]), (xsp, yh), (xg, yh), (xg, ym), (lk.x + lk.w, ym)]
        chain(f'lk_{lk.name}', 'link', min(per, 1024), (coll.name, f'l{lk.name}'), (lk.name, 'io'), pts,
              path=f'link_{lk.name}')
    hl = m['host']
    ld = hub['loader']
    p0 = _cxy(ld, 'E', 0.5)
    xs_ = hl.x - SCH / 2
    pts = [p0, (p0[0] + 200.0, p0[1]), (p0[0] + 200.0, ych['S'] + 60.0), (xs_, ych['S'] + 60.0), (xs_, hl.y + hl.h / 2),
           (hl.x, hl.y + hl.h / 2)]
    chain('host', 'host', 512, (ld.name, 'h'), (hl.name, 'io'), pts, path='host')
    # ---- clock trunks (PLL in the collective block) to every clock-region root
    for nm_ in [it.name for it in insts if it.kind in ('svc', 'hub', 'spine') and it.name != coll.name]:
        B.append((f'clk_{nm_}', 'clock_trunk', CLK_BITS, [(coll.name, 'pll'), (nm_, 'ck')]))
    for st in m['groups']:
        B.append((f'clk_grp_{st}', 'clock_trunk', CLK_BITS, [(coll.name, 'pll'), (m['groups'][st]['sms'][0].name, 'ck')]))
    return B, dict(P)


# ------------------------------------------------------------------------------------------------ abstracts
def real_ports():
    phy = S.real_lef(PHY_LEF)
    dfi = sorted(phy['pins'], key=lambda p: (phy['pins'][p][1][0], p))
    sd = dict(io=S._bus('tx', 512) + S._bus('rx', 512), ck=['clk'])
    return {phy['name']: dict(dfi=dfi), S.real_lef(SERDES_LEF)['name']: sd, S.real_lef(UCIE_LEF)['name']: sd}


REAL = {}


def _init_real():
    for rel in (PHY_LEF, SERDES_LEF, UCIE_LEF):
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
    for bid, cls, bits, eps in m['buses']:
        for i, (inst, port) in enumerate(eps):
            it = by[inst]
            if it is not first[it.master]:
                continue
            others = [by[o] for j, (o, _) in enumerate(eps) if j != i]
            peers[(it.master, port)] += others
    notes = {'hfd_sm': 'SM element ot_hbm_accel_sm_v NC8/SUB4 (sm_r2 context 2202.768 x 2072.79, 202 macros; pin regions '
                       'of the context: d/req/rsp bottom, xw left, results right, control top; element route OPEN)'}
    for it in m['insts']:
        if it.master in M or it.master in REAL:
            continue
        nt = notes.get(it.master) or (f'{it.kind}: forwarded-link / multicast / gather station' if it.kind == 'waypoint'
                                      else f'{it.kind} placeholder sized from the block ledger')
        M[it.master] = Q.Master(it.master, it.w, it.h, 3 if it.kind == 'waypoint' else 7, nt)
    sm_fixed = dict(d='S', q='S', x='W', r='E', c='N', ck='N')
    sm_span = dict(S=(550.7, 1652.1), W=(518.2, 1554.6), E=(518.2, 1554.6), N=(550.7, 1652.1))
    items = defaultdict(lambda: defaultdict(list))
    for (mname, port), others in peers.items():
        if mname in REAL or mname not in M:
            continue
        if mname.startswith('hfd_svc_') and port == 'phy':
            continue
        it = first[mname]
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
            if it.orient == 'MX':
                face = {'N': 'S', 'S': 'N'}.get(face, face)
            if it.orient == 'MY':
                face = {'E': 'W', 'W': 'E'}.get(face, face)
        if it.orient == 'MX':
            ly = it.h - ly
        if it.orient == 'MY':
            lx = it.w - lx
        along = ly if face in 'EW' else lx
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
            if mname.startswith('hfd_stn') or mname.startswith('hfd_mcast') or mname.startswith('hfd_gath') \
                    or mname.startswith('hfd_cdist') or mname == 'hfd_sm':
                pitch = 2 if 2 * sum(n) * p + (len(n) - 1) * gap <= room else 1
            need = [x * p * pitch for x in n]
            if sum(need) + gap * (len(n) - 1) > room + 1e-6:
                raise ValueError(f'{mname} face {face}: {sum(need):.1f} um of pins on {room:.1f} um')
            pos, starts = a0, []
            spread = mname in SPREAD_MASTERS and full >= 500.0 and mname != 'hfd_sm' and not mname.startswith(('hfd_svc_', 'hfd_stn', 'hfd_mcast',
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
        mst = M[f'hfd_svc_{st}']
        if k == 1:
            ph = S.real_lef(PHY_LEF)
            mst.ports['phy'] = ('xy', [(ph['pins'][n_][1][0] + ph['pins'][n_][1][2]) / 2
                                       for n_ in real_ports()[ph['name']]['dfi']])
            mst.order.append('phy')
        else:
            mst.face('phy', max(1, pw.get((mst.name, 'phy'), 1)), 'S', 'M5', mst.w / 2, 4)
    if k > 1:
        for name, ports in real_ports().items():
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
    rp = real_ports() if k == 1 else {}
    by = {it.name: it for it in m['insts']}
    conns = defaultdict(list)
    V = [f'// tools/hbm_accel_die_fp.py: die-level nets only (k = {k})', f'module {top} ();']
    for bid, cls, bits, eps in m['buses']:
        n = bits if k == 1 else max(1, math.ceil(bits / k))
        net = f'n_{bid}'
        V.append(f'  wire [{n - 1}:0] {net};')
        for inst, port in eps:
            mst = by[inst].master
            if mst in rp and port in rp[mst]:
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
            segs.append(round(ln, 1))
            L += ln
        out[p] = dict(segments=len(ids), um=round(L, 1),
                      stages_430=sum(math.ceil(s_ / LINK_STAGE_UM) for s_ in segs if s_ > 0),
                      stages_504=sum(math.ceil(s_ / SS_REACH_UM) for s_ in segs if s_ > 0))
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
)


def path_class(p):
    for k in ('weight', 'xbcast', 'result', 'control', 'expert_req', 'kv', 'ik', 'link', 'host'):
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
        power=die_power(m), pdn=pdn_plan(m), clock_region_list=clock_regions(m), notes=m['notes'], variant=m['variant'])


def write_sdc(path):
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
    out = []
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
    cen = [hb[k] for k in hb if not k.startswith('index_')]
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
    (work / 'manifest.json').write_text(json.dumps(man, indent=1))
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
    (work / 'manifest.json').write_text(json.dumps(man, indent=1))
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['plan', 'check', 'real', 'grt', 'ir', 'irwin', 'record', 'price'])
    ap.add_argument('--work', type=Path)
    ap.add_argument('--k', type=int, default=16)
    ap.add_argument('--tag', default='base')
    ap.add_argument('--iters', type=int, default=50)
    ap.add_argument('--empty', action='store_true')
    ap.add_argument('--window', default='w00_00')
    ap.add_argument('--cov', default='')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--only', default='')
    a = ap.parse_args(argv)
    m = build()
    cov = dict(COV)
    for kv in filter(None, a.cov.split(',')):
        k_, v = kv.split('=')
        cov[k_] = float(v)
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
        write_sdc(out / 'domains.sdc')
        print(json.dumps({k_: rec[k_] for k_ in ('die', 'instances', 'placed_footprint_mm2', 'legality_python',
                                                  'manhattan_class_bounds', 'power')}, indent=1))
        return 0
    if a.mode == 'record':
        import hbm_accel_die_price as PR
        return PR.record(m, a.work, a.out, a.only)
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
