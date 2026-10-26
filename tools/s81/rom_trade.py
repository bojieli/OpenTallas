#!/usr/bin/env python3
"""S81 ROM-for-hub trade sizing (S-ROMTRADE, 2026-10-15).

Owner direction 18:55: fewer ROM pairs per S81 die so the hub gets real room (A2 VM, SU, capture group, collective,
MIX4, HC side by side; >=20 % hub whitespace; every road / local cut <= 0.50; no relay-stage growth).  This tool:

  breakdown   area of the current die (canonical full2417 capacity + GEN19b hard boxes) by class
  roots       re-pack the 128 field roots into the columns left after removing k hub-adjacent columns (max pairs,
              BF share kept), for each sizing point
  (allocator) tools/dsrom_s73_pair1.py is run separately at each point's pairs/BF (metadata mapping, ~2 min a run)
  summarise   joins geometry, allocator stage counts, per-stage issue cycles, array dies / stacks / power / silicon
              and the AR / MTP hop effect into results/arch/s81_rom_trade_1015/rom_trade.json

Everything here is a SCREEN: block outlines are source/contract sizes, roads are track counts from the option-C
replay at 21.09 tracks/um, root heights are the canonical slot heights, stage counts come from the real allocator,
tok/s deltas are the measured full-FEC stage hop applied to the published composition.  No RTL, no P&R.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAP = "results/physical/die_iter_1012/s81/canonical_gen_1015/capacity_service_gap_broad_reroot_E.json"
INV = "results/uarch/dsrom_s81_released_binding_20261004/canonical/inventory.json"
OPTC = "results/arch/s81_globalfp_1015/optc_r2/optc1_homes_roads.json"
A2FIT = "results/arch/s81_die_vm_fit_1015/a2_fit.json"
GRAPH = "results/arch/s81_globalfp_1015/graph.json"
CMP = "results/arch/three_machine_compose/compose.json"
SYSTEMS = "results/arch/token_path_20261009/systems.json"
RACK = "results/arch/dsrom_s81_rack_20261006/rack.json"
FULLDIE = "results/rtl/dsrom_s81_fulldie_20261004/floorplan.json"
OUT = ROOT / "results/arch/s81_rom_trade_1015"

DIE_W, DIE_H = 33000.0, 26000.0
PITCH = 1191.456                      # field column pitch (canonical columns)
FRAME_W = 1182.816
CH_FIRST, CH_BETWEEN = 259.2, 388.8   # interframe channels (canonical interframe_channels_um)
SLOT_BF, SLOT_Q = 289.44, 304.56      # canonical slot heights (BF slot holds 1 pair, q slot 2 pairs)
TRK_PER_UM = 21.09                    # raw tracks / um of road (option C: 6,126 tr / 509.76 um / 0.5697)
CUT = 0.50                            # owner 18:55: every road and local cut <= 0.50
STAGE_UM = 500.0                      # seam rule reach per registered stage
HUB_Y0, HUB_Y1 = 1786.3, 23608.4      # hub interval (bk_selector top .. bk_collector - gap), a2_fit 21,822 um
STATIONS_MM2 = 3.6                    # coordinator 19:0x: f6/f8 station outlines accepted, +3.6 mm2 a die
BF_SHARE = 519 / 2417
CLK = 1.2e9

# hub blocks (w, h um): source / contract outlines (a2_fit, s81.json v19 slots, MIX4 slot, S-VM A2 37a313326)
BLOCKS = dict(
    su=(1935.36, 10463.04),            # su_s after closure (a) (20.25 mm2; 1,890 x 10,709 before)
    vm=(3369.6, 5063.0),               # A2 VM, 547 hard leaves (S-VM 17:50)
    mix4=(3229.2, 1321.92),            # MIX4 slot rotated onto the VM N face
    cap=(1728.0, 3207.6),              # capture + gather + pq + wfc + sseq stack (a2_fit)
    coll=(1728.0, 2894.4),             # collective (a2_fit height incl. seam)
    host=(1728.0, 129.6),
    hc_t=(1816.56, 9849.6), hc_corr=(1816.56, 799.2), hc_s=(1816.56, 9324.7),
)


def J(p):
    return json.loads((ROOT / p).read_text())


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def area(b):
    return b[0] * b[1] / 1e6


# ------------------------------------------------------------------------------------------- area breakdown
def breakdown():
    cap = J(CAP)
    hard = {b[0]: b[1:] for b in cap["hard_fixed_boxes"]}
    frames = sum(p["outline_um"][0] * p["outline_um"][1] for p in cap["placements"]) / 1e6
    cols = cap["columns"]
    col_env = sum(FRAME_W * c["height_um"] for c in cols) / 1e6
    hub_names = ["sp_su_s", "sp_vm", "sp_capture", "sp_gather", "sp_pq", "sp_wfc", "sp_sseq", "sp_collective",
                 "sp_host", "sp_hc_s", "sp_hc_t"]
    hub_blocks = sum(hard[n][2] * hard[n][3] for n in hub_names) / 1e6
    io = sum(hard[n][2] * hard[n][3] for n in hard if n.startswith(("phy_", "ctrl_", "svc_", "lk_", "svcj"))) / 1e6
    bk = sum(hard[n][2] * hard[n][3] for n in ("bk_selector", "bk_collector")) / 1e6
    hcp = sum(h["outline"]["w"] * h["outline"]["h"] for h in cap["hcp_homes"]) / 1e6
    w_edge = max(c["x_um"] for c in cols if c["x_um"] < 16000) + FRAME_W
    e_edge = min(c["x_um"] for c in cols if c["x_um"] > 16000)
    gap = e_edge - w_edge
    hub_interval = 5097.6 * (HUB_Y1 - HUB_Y0) / 1e6
    strip = gap * DIE_H / 1e6
    die = DIE_W * DIE_H / 1e6
    rows = dict(
        rom_field_frames_mm2=round(frames, 2),
        rom_field_interframe_channels_mm2=round(col_env - frames, 2),
        field_column_gaps_and_service_streets_mm2=round((22 * PITCH - 22 * FRAME_W) * DIE_H / 1e6, 2),
        hub_blocks_mm2=round(hub_blocks, 2),
        hub_strip_mm2=round(strip, 2),
        hub_strip_roads_whitespace_mm2=round(strip - hub_blocks - bk, 2),
        bank_selector_collector_mm2=round(bk, 2),
        io_phy_ctrl_svc_links_mm2=round(io, 2),
        hcp_homes_mm2=round(hcp, 2),
    )
    used = col_env + rows["field_column_gaps_and_service_streets_mm2"] + strip + io + hcp
    rows["edges_corners_unassigned_mm2"] = round(die - used, 2)
    return dict(die_mm2=die, field_columns=len(cols), roots=cap["root_count"], pairs=cap["pair_count"],
                bf=cap["bf_pairs"], hub_gap_between_fields_um=round(gap, 3), field_w_edge_um=round(w_edge, 3),
                field_e_edge_um=round(e_edge, 3), hub_interval_um=[5097.6, round(HUB_Y1 - HUB_Y0, 1)],
                hub_interval_mm2=round(hub_interval, 2),
                hub_interval_fill_current=round(hub_blocks / hub_interval, 3),
                rows=rows, share={k: round(v / die, 4) for k, v in rows.items()},
                rom_share_note="ROM field = frames + interframe channels + column gaps; hub strip = everything "
                               "between the W and E fields (roads S14W/VCH/S14E included)",
                columns=[dict(x=c["x_um"], h=round(c["height_um"], 1), roots=c["roots"]) for c in cols])


# ------------------------------------------------------------------------------------------- root re-pack
def root_types():
    out = []
    for n in range(12, 23):
        for b in range(2, 7):
            q = n - b
            if q <= 0:
                continue
            h = SLOT_BF * b + SLOT_Q * math.ceil(q / 2)
            out.append((n, b, round(h, 2)))
    # keep the Pareto set: for each height the max pairs, then max BF
    best = {}
    for n, b, h in out:
        k = (h,)
        if k not in best or (n, b) > best[k][:2]:
            best[k] = (n, b, h)
    return sorted(best.values(), key=lambda t: t[2])


def col_options(H, types):
    """every multiset of root types that fits a column of height H: (roots, pairs, bf) -> keep Pareto by pairs"""
    opts = {}
    maxk = int((H - CH_FIRST + CH_BETWEEN) // (min(t[2] for t in types) + CH_BETWEEN))
    for k in range(0, maxk + 1):
        for combo in itertools.combinations_with_replacement(range(len(types)), k):
            h = CH_FIRST + sum(types[i][2] for i in combo) + CH_BETWEEN * max(0, k - 1) if k else 0
            if h > H + 1e-6:
                continue
            n = sum(types[i][0] for i in combo)
            b = sum(types[i][1] for i in combo)
            key = (k, b)
            if key not in opts or n > opts[key][0]:
                opts[key] = (n, combo)
    return opts


def pack(heights, roots=128, bf_share=BF_SHARE):
    """max pairs with exactly `roots` roots over the columns, BF >= share x pairs (DP over columns: (roots, bf))"""
    # Pareto root frames (pairs, BF, height): 20p/4bf = 19p/4bf height (the canonical 19p frames leave one q lane empty)
    types = [(20, 4, 3594.24), (19, 5, 3579.12), (18, 4, 3289.68), (17, 3, 3000.24), (16, 4, 2985.12), (15, 3, 2695.68),
             (13, 3, 2391.12), (11, 3, 2086.56)]
    dp = {(0, 0): (0, [])}
    for H in heights:
        co = col_options(H, types)
        nd = {}
        for (r, b), (n, picks) in dp.items():
            for (k, bb), (nn, combo) in co.items():
                r2, b2 = r + k, b + bb
                if r2 > roots:
                    continue
                v = n + nn
                key = (r2, b2)
                if key not in nd or v > nd[key][0]:
                    nd[key] = (v, picks + [combo])
        dp = nd
    best = None
    for (r, b), (n, picks) in dp.items():
        if r == roots and b >= bf_share * n - 1e-9:
            if best is None or (n, -b) > (best[0], -best[1]):
                best = (n, b, picks)
    if best is None:
        return dict(pairs=0, bf=0, roots=roots, root_types={}, fits=False)
    n, b, picks = best
    hist = {}
    for combo in picks:
        for i in combo:
            t = types[i]
            hist[f"{t[0]}p/{t[1]}bf"] = hist.get(f"{t[0]}p/{t[1]}bf", 0) + 1
    return dict(pairs=n, bf=b, roots=roots, root_types=hist)


# ------------------------------------------------------------------------------------------- sizing points
REMOVE_ORDER = ["W10", "E11", "W9", "E12", "W8", "E13", "W7", "E14"]


def col_names(cap):
    names = []
    for c in cap["columns"]:
        i = len(names)
        names.append(f"W{i}" if c["x_um"] < 16000 else f"E{i}")
    return names


def roads():
    o = J(OPTC)["result"]
    s14w_tdm = o["per_road_peak"]["S14W"]["tracks"]
    s14w_no_tdm = round(0.649 * 509.76 * TRK_PER_UM)          # option C before the 12 return-TDM pairs (S14W 0.649)
    s14e = o["per_road_peak"]["S14E"]["tracks"]
    need = lambda tr: round(tr / (TRK_PER_UM * CUT), 1)
    return dict(S14W_tracks_no_tdm=s14w_no_tdm, S14W_tracks_tdm=s14w_tdm, S14E_tracks=s14e,
                S14W_um_at_050_no_tdm=need(s14w_no_tdm), S14W_um_at_050_tdm=need(s14w_tdm),
                S14E_um_at_050=need(s14e), track_density_per_um=TRK_PER_UM,
                note="option C (44bb36c57) levers A/B/D/E kept (cost <= 0 stages); return TDM (C, +2 stages on 12 "
                     "paths) NOT used: the owner forbids relay-stage growth, so S14W is sized for its pre-TDM demand")


def layout(point, gap):
    """hub strip W->E; returns geometry + checks.  Order (mirror of today so the collective keeps its x):
    S14W | HC tower (or HC_t|HC_s side by side) | ch | capture col (capture group + collective + host) | VM col
    (VM + MIX4 on its N face) | SU | S14E"""
    R = roads()
    w = BLOCKS
    hc_w = w["hc_t"][0] * (2 if point["hc_side_by_side"] else 1)
    su_w = point.get("su_w", w["su"][0])
    su_h = w["su"][0] * w["su"][1] / su_w
    ch = point["internal_channel_um"]
    s14w = R["S14W_um_at_050_no_tdm"]
    content = s14w + hc_w + ch + w["cap"][0] + w["vm"][0] + su_w
    s14e_avail = gap - content
    ok_roads = s14e_avail >= R["S14E_um_at_050"]
    hub_w = gap - s14w - s14e_avail if s14e_avail > 0 else hc_w + ch + w["cap"][0] + w["vm"][0] + su_w
    # vertical: VM centred on the die (y 13,000); capture group abuts the VM side, collective above it, host on top
    vm_y0 = 13000 - w["vm"][1] / 2
    col_stack = w["cap"][1] + w["coll"][1] + w["host"][1]
    vm_stack = w["vm"][1] + w["mix4"][1]
    hc_h = (w["hc_t"][1] + w["hc_corr"][1] + w["hc_s"][1]) if not point["hc_side_by_side"] else max(w["hc_t"][1], w["hc_s"][1])
    tier_h = max(su_h, vm_stack, col_stack, hc_h)
    blocks_mm2 = (area(w["su"]) + area(w["vm"]) + area(w["mix4"]) + area(w["cap"]) + area(w["coll"]) + area(w["host"])
                  + area(w["hc_t"]) + area(w["hc_s"]) + (0 if point["hc_side_by_side"] else area(w["hc_corr"])))
    blocks_mm2 += STATIONS_MM2 * point.get("stations_in_hub_share", 0.35)
    hub_h = HUB_Y1 - HUB_Y0
    full_strip_mm2 = hub_w * hub_h / 1e6
    fits_height = max(su_h, hc_h, vm_stack + 0, col_stack) <= hub_h
    res = dict(hub_strip_gap_um=round(gap, 1), S14W_um=s14w, S14E_um=round(s14e_avail, 1),
               S14E_cut=round(R["S14E_tracks"] / (TRK_PER_UM * max(s14e_avail, 1)), 3),
               S14W_cut=round(R["S14W_tracks_no_tdm"] / (TRK_PER_UM * s14w), 3),
               hub_content_w_um=round(hub_w, 1), su_outline_um=[round(su_w, 2), round(su_h, 1)],
               tier_h_um=round(tier_h, 1), fits_height=fits_height, roads_ok_050=ok_roads,
               hub_blocks_mm2=round(blocks_mm2, 2), hub_area_full_strip_mm2=round(full_strip_mm2, 2),
               whitespace_full_strip=round(1 - blocks_mm2 / full_strip_mm2, 3))
    # L-hub: give the strip above the tier (except the HC column when it is a full-height tower) back to roots
    if point.get("l_hub"):
        free_w = hub_w - (hc_w + ch if not point["hc_side_by_side"] else 0)
        tier_top = HUB_Y0 + tier_h
        lhub_mm2 = (hub_w * tier_h + (0 if point["hc_side_by_side"] else (hc_w + ch) * (hub_h - tier_h))) / 1e6
        res.update(l_hub=dict(tier_top_um=round(tier_top, 1), returned_w_um=round(free_w, 1),
                              returned_h_um=round(HUB_Y1 - tier_top - 509.76, 1), hub_area_mm2=round(lhub_mm2, 2),
                              whitespace=round(1 - blocks_mm2 / lhub_mm2, 3)))
    # bus checks: edge-to-edge gap today vs here, stages at 500 um
    bus = []
    hc_vm_gap = ch + w["cap"][0]                         # HC_s -> VM through the capture column
    today = dict(su_vm=0, cap_vm=0, cap_gather=0, mix4_vm=514.0, coll_vm=1100.0, hc_s_vm=1734.3, coll_hc_s=1641.6,
                 hc_s_hc_t=799.2)
    here = dict(su_vm=0, cap_vm=0, cap_gather=0, mix4_vm=0, coll_vm=0, hc_s_vm=hc_vm_gap,
                coll_hc_s=ch, hc_s_hc_t=0 if point["hc_side_by_side"] else 799.2)
    for k in today:
        bus.append(dict(bus=k, today_gap_um=today[k], gap_um=round(here[k], 1),
                        today_stages=math.ceil(today[k] / STAGE_UM), stages=math.ceil(here[k] / STAGE_UM),
                        growth=math.ceil(here[k] / STAGE_UM) - math.ceil(today[k] / STAGE_UM)))
    res["bus_stage_check"] = bus
    res["relay_growth_any"] = any(b["growth"] > 0 for b in bus)
    return res


POINTS = [
    dict(name="minimal", k=3, hc_side_by_side=False, internal_channel_um=0.0, su_w=1586.0,
         why="3 columns; SU reshaped to 1,586 x 12,770 (same 20.25 mm2), no internal channel, S14E at the 0.50 "
             "limit: everything abuts; tight"),
    dict(name="recommended", k=4, hc_side_by_side=False, internal_channel_um=216.0,
         why="4 columns; SU as closure (a), 216-um channel between the HC tower and the capture column, ~500 um "
             "spare road width"),
    dict(name="compact_L", k=5, hc_side_by_side=True, internal_channel_um=0.0, l_hub=True,
         why="5 columns; HC_t | HC_s side by side so the whole hub is one 10.5-mm tier; field roots return into "
             "the strip above the tier (L-shaped hub); needs a field-topology screen (those roots return straight "
             "down into the gather)"),
    dict(name="generous", k=6, hc_side_by_side=True, internal_channel_um=216.0,
         why="6 columns; HC_t | HC_s side by side (corridor and its 5.2k VCH lanes vanish), whole hub one ~10.5-mm "
             "tier, roads well under 0.50"),
]


def geometry():
    cap = J(CAP)
    names = col_names(cap)
    heights = {n: c["height_um"] for n, c in zip(names, cap["columns"])}
    base_gap = breakdown()["hub_gap_between_fields_um"]
    base_pack = pack(list(heights.values()))
    pts = []
    for p in POINTS:
        removed = REMOVE_ORDER[: p["k"]]
        left = [heights[n] for n in names if n not in removed]
        gap = base_gap + p["k"] * PITCH
        lay = layout(p, gap)
        extra = []
        if p.get("l_hub"):
            lh = lay["l_hub"]
            ncols = int(lh["returned_w_um"] // PITCH)
            extra = [lh["returned_h_um"]] * ncols
            lay["l_hub"]["returned_columns"] = ncols
        pk = pack(left + extra)
        pts.append(dict(p, removed_columns=removed, columns_left=len(left), layout=lay, roots=pk))
    return dict(base_pack_check=base_pack, base_gap_um=base_gap, roads=roads(), points=pts)


# ------------------------------------------------------------------------------------------- array effect
HOP_US = (1004 + 171 / 84) / CLK * 1e6     # measured full-KP4 stage hop (RTL ot_dsrom_link_rt) + rack mean flight
SCAN_LAYERS = [2, 8, 14, 20, 24, 28, 32, 36]
HEAD, DRAFT, TABLE, SCAN_DIES = 12, 40, 0, 32  # array v2 choice (head 12, draft 40, Engram tables in HBM)
W_SERDES, W_STATIC_REST, W_DYN = 30.6, 50.196 - 30.6, 33.9   # S81 layer die: static (ICG ledger, SerDes part), dyn
W_HEAD, W_STACK, STACK_MM2, DIE_MM2 = 92.34, 2.8, 1089.0, 858.0


# report headline (systems.json ds_rom: 120 stages, HALF_PHL BF, 1,792-pair mapping): AR 1,447.7 / MTP 4,238.4 at tau 4.159
HEADLINE = dict(stages=120, AR_tok_s=1447.7, MTP_tok_s=4238.4, tau=4.159)


def alloc_stats(d):
    inv = json.loads((d / "inventory.json").read_text())
    occ = inv["occupied_pairs_per_stage"]
    words = inv["used_logical_words_per_stage"]
    P = inv["pairs_per_rank_die"]
    matrix_stages = max(i for i, v in enumerate(occ) if v > 32) + 1     # providers alone hold <= 9-18 pairs
    cyc = {}
    for line in gzip.open(d / "matrix_map.jsonl.gz", "rt"):
        m = json.loads(line)
        if m["stage"] is not None:
            cyc[m["stage"]] = cyc.get(m["stage"], 0) + m.get("issue_cycles_LAT8_condition", 0)
    v = [cyc.get(i, 0) for i in range(matrix_stages)]
    verdict = json.loads((d / "mapping_verdict.json").read_text())
    return dict(pairs=P, bf=inv["BF_dual_pairs"], stages_run=inv["stages"], matrix_stages=matrix_stages,
                occupied_pairs_total=sum(occ), word_fill_matrix_stages=round(
                    sum(words[:matrix_stages]) / (matrix_stages * P * 8192), 4),
                issue_cycles_per_stage=dict(mean=round(sum(v) / len(v)), max=max(v), min=min(v),
                                            max_over_mean=round(max(v) / (sum(v) / len(v)), 4)),
                capacity_pass=verdict["decoder_matrix_capacity_PASS"], failures=len(verdict["failures"]))


def array(stages, pairs, ref):
    layer = 4 * stages
    dies = layer + HEAD + DRAFT + TABLE
    stacks = layer + 3 * SCAN_DIES + 4 * HEAD + 8
    w_layer = W_SERDES + (W_STATIC_REST + W_DYN) * pairs / 2417
    chips_w = layer * w_layer + HEAD * W_HEAD + DRAFT * (W_SERDES + W_STATIC_REST + W_DYN) + stacks * W_STACK
    ar_us = ref["AR_us"] + (stages - ref["stages"]) * HOP_US
    mtp_us = ref["MTP_step_us"] + (stages - ref["stages"]) * HOP_US
    hl = HEADLINE
    ar_h = 1e6 / hl["AR_tok_s"] + (stages - hl["stages"]) * HOP_US
    mtp_h = hl["tau"] * 1e6 / hl["MTP_tok_s"] + (stages - hl["stages"]) * HOP_US
    d_ar = 1e6 / hl["AR_tok_s"] + (stages - 81) * HOP_US
    d_mtp = hl["tau"] * 1e6 / hl["MTP_tok_s"] + (stages - 81) * HOP_US
    return dict(stages=stages, layer_dies=layer,
                vs_today_headline=dict(basis="today's report headline (AR 1,447.7 / MTP 4,238.4, tau 4.159) taken "
                                             "as the 81-stage die; only the stage-hop change applied",
                                       d_stages=stages - 81, AR_tok_s=round(1e6 / d_ar, 1),
                                       MTP_tok_s=round(hl["tau"] * 1e6 / d_mtp, 1),
                                       MTP_ge_3000=hl["tau"] * 1e6 / d_mtp >= 3000),
                l20_scan_home_stage=20 * stages // 40,
                headline_anchor=dict(AR_tok_s=round(1e6 / ar_h, 1), MTP_tok_s=round(hl["tau"] * 1e6 / mtp_h, 1),
                                     MTP_ge_3000=hl["tau"] * 1e6 / mtp_h >= 3000), dies=dies, stacks=stacks, packages=dies // 2,
                trays=math.ceil(stages / 2), stage_hops=stages - 1,
                AR_us=round(ar_us, 3), AR_tok_s=round(1e6 / ar_us, 1),
                MTP_step_us=round(mtp_us, 3), MTP_tok_s=round(ref["tau"] * 1e6 / mtp_us, 1),
                chips_w=round(chips_w), die_silicon_mm2=round(dies * DIE_MM2), stack_silicon_mm2=round(stacks * STACK_MM2),
                total_silicon_mm2=round(dies * DIE_MM2 + stacks * STACK_MM2))


def summarise(alloc_root: Path):
    """join geometry + allocator runs (alloc_root/p<P>s<S>) + array model into OUT/rom_trade.json"""
    cmp_ = J(CMP)["ds_rom"]
    ref = dict(stages=85, AR_us=cmp_["AR_us"], MTP_step_us=cmp_["MTP_step_us"], tau=cmp_["tau"])
    geo = geometry()
    bd = breakdown()

    def run(P, S):
        d = alloc_root / f"p{P}s{S}"
        return alloc_stats(d) if (d / "mapping_verdict.json").exists() else None

    base81 = run(2417, 81)
    base74 = run(2417, 74)
    full20 = run(2509, 70)
    rows = dict(today_binding=dict(what="current die (2,417 pairs, 22 columns) at the released 81-stage binding",
                                   alloc=base81, array=array(81, 2417, ref)),
                today_repacked=dict(what="same die, layers re-cut onto the stages they need (providers homed inside)",
                                    alloc=base74, array=array(base74["stages_run"], 2417, ref) if base74 else None),
                today_full_frames=dict(what="same 22 columns with 20-pair frames (the canonical 19-pair frames leave "
                                            "one q lane empty): 2,509 pairs", alloc=full20,
                                       array=array(full20["stages_run"], 2509, ref) if full20 else None))
    for pt in geo["points"]:
        P = pt["roots"]["pairs"]
        S = {2316: 74, 2176: 82, 1904: 96, 2421: 74}.get(P)
        a = run(P, S) if S else None
        rows[pt["name"]] = dict(what=pt["why"], removed_columns=pt["removed_columns"], roots=pt["roots"],
                                layout=pt["layout"], alloc=a, array=array(a["stages_run"], P, ref) if a else None)
    out = dict(schema="opentallas.s81.rom_trade.v1", date="2026-10-15", author="S-ROMTRADE (Claude)",
               question="fewer ROM pairs per S81 die for a roomy hub (owner 18:55): sizing points, die count, "
                        "tok/s, power, silicon",
               grades=dict(stage_counts="MODEL: real allocator tools/dsrom_s73_pair1.py (metadata mapping, every "
                                        "decoder matrix placed, 0 failures) at each pair/BF count; not RTL",
                           geometry="SCREEN: source/contract outlines, canonical slot heights, option-C track counts "
                                    "at 21.09 tracks/um; no GEN, no GRT",
                           tok_s="DERIVED: published composition (three_machine_compose ds_rom, 85 stages, AR "
                                 f"{cmp_['AR_us']} us / MTP step {cmp_['MTP_step_us']} us, tau {cmp_['tau']}) + "
                                 f"(stages - 85) x {HOP_US:.4f} us (measured full-KP4 hop + rack mean flight); "
                                 "field phases and per-layer compute unchanged (fewer pairs a die does not change "
                                 "pairs a layer)",
                           power="MODEL: every layer die at the busiest-die saturated basis (SerDes 30.6 W fixed, the "
                                 "other static 19.6 W and dynamic 33.9 W scaled by pairs a die), head 92.34 W, draft "
                                 "84.1 W, stack 2.8 W"),
               area_breakdown=bd, roads=geo["roads"], stations_mm2_accepted=STATIONS_MM2,
               base_pack_check=geo["base_pack_check"], rows=rows,
               alternatives=dict(
                   in_reticle_closure_a=dict(
                       what="today's plan: su_s reshape 1,935 x 10,463 (c22a, main 755620003), A2 stacked in the W "
                            "column, option C roads",
                       rom_change_pairs=0, stages=81, hub_vertical_slack_um=round(246.2 - 246.2, 1),
                       road_cuts="S14W 0.570 (with return TDM +2 stages on 12 paths, +0.34 % AR), S14E 0.391, street "
                                 "0.597, VCH needs the HC t<->s lanes moved into the corridor",
                       meets_owner_1855=False,
                       why="0 um height slack, cuts at 0.60 not 0.50, TDM adds relay stages, VM/SU/capture stacked"),
                   multi_die_hub_split=dict(
                       what="fallback B: VM + MIX4 + capture/gather on a companion die per layer die",
                       added_dies=324, d2d_bits=dict(su_vm=17137, vm_capture=13376, mix4_vm=12732),
                       su_vm_bandwidth_tbps=round(17137 * 1.2e9 / 1e12, 1),
                       latency="UCIe 10 ns (12 cycles) per crossing, >= 2 crossings a field phase; ~40 layers x ~10 "
                               "phases -> >= 9,600 cycles = >= 8 us a token (>= +1.3 % AR) before serialization",
                       meets_owner_1855=False,
                       why="+324 dies and packages of 4, ~21 Tb/s of SU<->VM D2D a die, new PHY RTL; strictly worse "
                           "than removing <= 4 field columns")),
               sources={p: sha(p) for p in (CAP, INV, OPTC, A2FIT, GRAPH, CMP, RACK, FULLDIE)},
               tool_sha256=sha("tools/s81/rom_trade.py"))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rom_trade.json").write_text(json.dumps(out, indent=1) + "\n")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["breakdown", "geometry", "summarise"])
    ap.add_argument("--alloc-root", type=Path, default=Path("/tmp/romtrade/alloc"))
    a = ap.parse_args()
    if a.cmd == "summarise":
        out = summarise(a.alloc_root)
        for k, r in out["rows"].items():
            print(k, r["alloc"] and (r["alloc"]["pairs"], r["alloc"]["matrix_stages"], r["alloc"]["stages_run"]),
                  r["array"])
    elif a.cmd == "breakdown":
        print(json.dumps(breakdown(), indent=1))
    else:
        print(json.dumps(geometry(), indent=1))


if __name__ == "__main__":
    main()
