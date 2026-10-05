#!/usr/bin/env python3
"""ROM-die clock distribution decision (model level, no P&R): GALS (A) vs global mesh (B) vs mesochronous regions
with forwarded link clocks (C), for the Qwen3-8B ROM die and the DeepSeek-V4.1 ROM die (scenario C, one rank a die).

Model first (AGENTS.md design method 1).  For each option and die the tool states:
  * the clock-domain crossings on the single-user token's serial path, counted from the composed model
    (tools/uarch_model.py, read-only: +10-cycle probes on every field op / all-reduce / streamed attention op /
    CDC edge give the number of such edges on the critical path) and the die floorplans;
  * the added latency per token (cycles, us, % of per-user AR rate) at a mesochronous crossing cost that depends on
    the clock wander between the two sides (insertion delay of the non-shared distribution x dynamic derate);
  * FIFO area, clock-distribution power (ASAP7 upper-metal C, 1.2 GHz), skew/jitter against the 60 ps / 25 ps
    uncertainty policy, synchroniser MTBF, implementation risk.

    python3 tools/rom_die_clocking_model.py --output results/uarch/rom_die_clocking_decision_20261003.json

Every constant is labelled MEASURED (with its record), MODEL (computed here from a committed tool) or ASSUMED.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

FULLDIE_COMMIT = "c3a5675416cf435591a6213a88fe0c5f09956fed"      # claude/qwen-rom-fulldie-20261003
FULLDIE_CLOCK = "results/rtl/qwen_rom_fulldie_20261003/clock_trunk.json"
FULLDIE_PLAN = "results/rtl/qwen_rom_fulldie_20261003/floorplan.json"
TWOCLK_COMMIT = "27d86cfe4b8f87dab020886b70f4d75f89a819e6"       # claude/two-clock-rtl-20261003
TWOCLK_MODEL = "results/rtl/two_clock_crossing_20261003/crossing_model.json"
QWEN_CAL = "results/uarch/qwen_rom_calibrated_calendar_20261003/summary-r1.json"
DS_SCEN = "results/uarch/dsrom_return_storage_hbm_20261003/model.json"
SETRC = "results/uarch/dsrom_MTP_selected_parent_containment_20261003/inputs/setRC.tcl"

F = 1.2e9
T_PS = 1e12 / F                       # 833.3 ps
UNC_SETUP_PS, UNC_HOLD_PS = 60.0, 25.0  # AGENTS.md sign-off policy, never relaxed

# ---------------------------------------------------------------------------------------------- constants
C = dict(
    dyn_derate=dict(v=0.05, cls="ASSUMED", why="dynamic (uncalibrated: droop + temperature) share of the non-shared "
                    "insertion that a mesochronous crossing must absorb; the same 5% as the central OCV row of "
                    "clock_trunk.json"),
    supply_sens_per_mV=dict(v=0.0018, cls="ASSUMED", why="d ln(delay)/dV of an ASAP7 buffer near 0.7 V (alpha-power "
                            "law, Vt ~0.3 V, alpha 1.3): 0.18 %/mV"),
    dV_per_cycle_mV=dict(v=(2.0, 4.5, 9.0), cls="ASSUMED", why="supply change within one 833 ps cycle on the rail "
                         "that feeds a clock buffer: 9 mV = the 35 mV first-droop budget slewing over ~3 ns (core rail, "
                         "worst), 2 mV = a filtered clock rail; jitter = sens x dV x insertion"),
    wire_cap_fF_per_um=dict(v=0.2, cls="ASSUMED", why="clock wire on M8/M9 at ~2x minimum width with shields; ASAP7 "
                            "setRC M8/M9 minimum width is 0.104 / 0.093 fF/um (setRC.tcl pinned below)"),
    driver_load_factor=dict(v=1.0, cls="ASSUMED", why="repeater/driver input+self load = 1x the wire C"),
    vdd=dict(v=0.7, cls="ASSUMED", why="ASAP7 nominal supply (power at TT)"),
    ff_um2_per_bit=dict(v=0.37908 / 0.5, cls="MEASURED", why="DFFASRHQNx1_ASAP7_75t_R 0.37908 um2 at 50% placement "
                        "utilisation (the reservation rule of tools/dsrom_return_storage_hbm.py)"),
    mesh_pitch_um=dict(v=(100.0, 150.0, 300.0), cls="ASSUMED", why="global grid pitch (fine / central / coarse); "
                       "local trees hang below it"),
    sync=dict(tau_ps=(10.0, 20.0, 30.0), tw_ps=20.0, tcq_ps=45.0, tsu_ps=25.0, cls="ASSUMED",
              why="synchroniser regeneration constant tau at SS is not characterised for ASAP7; range given; MTBF = "
                  "exp(t_r/tau)/(T_w f_c f_d) (Ginosar 2011)"),
    region_extent_mm=dict(v=5.25, cls="MEASURED-MODEL", why="clock_trunk.json thick-metal 5% OCV: largest H-tree "
                          "subtree within the 60 ps setup uncertainty (1.97 mm within 25 ps hold; skew of a region's "
                          "internal split above 25 ps is hold-fixed by STA on the few buses that cross it)"),
    link_stage_um=dict(v=430.56, cls="MEASURED", why="corridor gate verdict 89e70dd78 (fulldie README)"),
    waypoint_stages=dict(v=4, cls="MODEL", why="LINK_WAYPOINT_UM = 4 x 430.56 um in tools/qwen_rom_fulldie.py: the "
                         "hardened link station, the finest element a link can be split into under A"),
)


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def git_show(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


PINS = {}


def load_git_json(commit, path):
    b = git_show(commit, path)
    PINS[f"{commit}:{path}"] = sha_bytes(b)
    return json.loads(b)


def load_json(path):
    b = (ROOT / path).read_bytes()
    PINS[path] = sha_bytes(b)
    return json.loads(b)


# ---------------------------------------------------------------------------------------------- model probes
def _ds_probe(tag: str):
    import uarch_model as u
    cap = json.loads((ROOT / "results/uarch/dsrom_4096_comparable_capacity_20261002/partition_token_options.json").read_text())
    rows = {r["stages"]: r for r in cap["all_stage_capacity_rows"]}
    S = 58          # the unified model's PAIR1 rank-die basis that scenario C restates (dsrom_return_storage_hbm run())
    u.PRESETS["proposal"]["bf16_stripe_macros"] = 2 * rows[S]["BF16_pairs_per_die"]
    u.PRESETS["proposal"]["idx_reader_Bpc"] = 4 * 750
    add = {}
    if tag == "f2s":
        u.CDC_W18["fast_to_slow_slow_cycles"] += 10
    if tag == "s2f":
        u.CDC_W18["slow_to_fast_fast_cycles"] += 10
    if tag == "matvec":
        pm = u.price_matvec

        def pm10(*a, **k):
            r = pm(*a, **k)
            return None if r is None else dict(r, depth=r["depth"] + 10)
        u.price_matvec = pm10
    if tag == "allreduce":
        add = {"allreduce": 10}
    if tag == "stream":
        for k in ("suffix:idx.score", "suffix:.attn.scores", "suffix:.attn.pv"):
            u.W11_STREAM_SS[k] += 10
    with u._cons_ctx(1048576):
        p = u.cons_v41_rom(S, 8, 36, bf16="columns", clock_hz=u.PRODUCT_CLOCK_HZ,
                           field_concurrency=u.FIELD_CONCURRENCY,
                           added_latency=dict(u.SOFTPLUS_FIX, **u.W11_STREAM_SS, **u.PLUS_LAT, **add),
                           dyn_scale=u.PRODUCT_DYN_SCALE, slow_domain=(.9e9, "w18"), elem_stages=8,
                           ss_wire=True, serial=u.PRODUCT_SERIAL, die=u.DIE_SHRUNK_INTERIM,
                           vmh=u.VMC_FUSED, hub_block=u.PRODUCT_HUB)
    return tag, p["ar_tokens_s_b1"], p["stage_hops"]


def _qwen_probe(extra: int):
    import uarch_model as u
    p = u.qwen_tp_point(4, 6144, "board", clock_hz=u.PRODUCT_CLOCK_HZ, me_lat_extra=167 + extra, su_width=64)
    return extra, p["cycles"], p["layer_chain_cycles"]


def probes():
    with ProcessPoolExecutor(max_workers=8) as ex:
        ds = {t: (r, h) for t, r, h in ex.map(_ds_probe, ["base", "f2s", "s2f", "matvec", "allreduce", "stream"])}
        qw = {e: (c, l) for e, c, l in ex.map(_qwen_probe, [0, 10])}
    base_us = 1e6 / ds["base"][0]

    def n(tag, hz):
        return round((1e6 / ds[tag][0] - base_us) * 1e-6 * hz / 10, 1)
    dsc = dict(basis="cons_v41_rom S58 PAIR1 rank die, 1M, the settings of tools/dsrom_return_storage_hbm.py run(); "
                     "per-layer op structure is unchanged by the S73 restatement (stage count changes hops only). "
                     "Rates are rounded to 0.1 tok/s, so a +10-cycle probe resolves +-2 edges.",
               base_ar_tok_s=ds["base"][0], stage_hops_S58=ds["base"][1],
               field_ops=n("matvec", F), allreduces=n("allreduce", F), streamed_attention_index_ops=n("stream", F),
               cdc_fast_to_slow_edges=n("f2s", 0.9e9), cdc_slow_to_fast_edges=n("s2f", F))
    qwc = dict(basis="qwen_tp_point(4, 6144, 'board', 1.2 GHz, me_lat_extra 167 vs 177, SU64): cycles a token per "
                     "added ME-op cycle = ME ops on the token path",
               me_ops_per_token=round((qw[10][0] - qw[0][0]) / 10, 1),
               me_ops_per_layer=round((qw[10][1] - qw[0][1]) / 10, 1),
               allreduces_per_token=72, allreduce_src="calendar compute.measured.allreduces_per_layer 1,982 = 2 x 991",
               near_hbm_attention_round_trips=36, attention_src="one hub<->strip row-engine round trip a layer (r2 frame)")
    return qwc, dsc


# ---------------------------------------------------------------------------------------------- crossing cost
def meso_delta_cycles(insertion_ps: float) -> dict:
    """Added destination cycles of a mesochronous FIFO over the register stage it replaces, read pointer placed at
    reset (static phase calibrated), margin for the dynamic wander w = derate x non-shared insertion each way."""
    w = C["dyn_derate"]["v"] * insertion_ps
    delta = 1 + math.ceil(max(0.0, 2 * w - T_PS / 2) / T_PS)
    depth = 2 + math.ceil(2 * w / T_PS) + 1                # throughput 2 + wander window + one credit-return slot
    depth_pow2 = max(4, 1 << (depth - 1).bit_length())
    return dict(insertion_ps=round(insertion_ps, 1), wander_ps=round(w, 1), added_cycles=delta,
                depth=depth, depth_pow2=depth_pow2)


def jitter_ps(insertion_ps: float, dv_mv: float) -> float:
    return round(C["supply_sens_per_mV"]["v"] * dv_mv * insertion_ps, 1)


def mtbf(stages: int, tau_ps: float, n_sync_bits: int, f_d: float = 0.5 * F) -> dict:
    s = C["sync"]
    tr = (stages - 1) * (T_PS - s["tcq_ps"]) - s["tsu_ps"]     # resolution time: FF1 -> last FF
    one = math.exp(tr / tau_ps) / (s["tw_ps"] * 1e-12 * F * f_d)
    return dict(stages=stages, tau_ps=tau_ps, t_r_ps=round(tr, 1), mtbf_one_s=float(f"{one:.3g}"),
                n_sync_bits=n_sync_bits, mtbf_system_years=float(f"{one / n_sync_bits / 3.156e7:.3g}"))


def rate_row(cycles: float, token_us: float) -> dict:
    us = cycles / F * 1e6
    return dict(cycles=round(cycles), us=round(us, 3), rate_change_pct=round(-100 * us / (token_us + us), 3))


# ---------------------------------------------------------------------------------------------- evaluation
def evaluate(qwc, dsc):
    trunk = load_git_json(FULLDIE_COMMIT, FULLDIE_CLOCK)
    plan = load_git_json(FULLDIE_COMMIT, FULLDIE_PLAN)
    xing = load_git_json(TWOCLK_COMMIT, TWOCLK_MODEL)
    cal = load_json(QWEN_CAL)["headline_numbers"]
    scen = load_json(DS_SCEN)["scenario_c"]
    PINS[SETRC] = sha_bytes((ROOT / SETRC).read_bytes())
    PINS["tools/uarch_model.py"] = sha_bytes((ROOT / "tools/uarch_model.py").read_bytes())
    PINS["tools/rom_die_clocking_model.py"] = sha_bytes(Path(__file__).read_bytes())

    ins = {m["model"]: m["insertion_ns"] * 1e3 for m in trunk["models"]}
    wire_models = {"central_thick_metal": ins["thick_metal_n5"], "tt_routed": ins["asap7_tt_routed_1mm"],
                   "bound_ss_routed": ins["asap7_ss_routed"]}
    dmeso = {k: meso_delta_cycles(v) for k, v in wire_models.items()}

    qwen_base = dict(calibrated_us=cal["calibrated_current"]["token_us"],
                     near_hbm_selected_us=cal["near_hbm_selected_for_build"]["token_us"])
    ds_C = scen["restated"]["C"]["1048576"]
    ds_base = dict(scenario_c_ar_us=round(1e6 / ds_C["ar"], 3), scenario_c_ar_tok_s=ds_C["ar"],
                   stages=scen["stages"])

    # ---- crossing counts a token, per option ------------------------------------------------------------------
    me, ar, att = qwc["me_ops_per_token"], qwc["allreduces_per_token"], qwc["near_hbm_attention_round_trips"]
    ls = plan["link_stages"]
    wp = C["waypoint_stages"]["v"]
    hub_stack = max(p["stages_430"] for p in ls["paths"])
    hub_io = ls["hub_to_io"]["stages_430"]
    cols_half = plan["instances"]["head"] // 2           # 32 heads a chain (west / east)
    rows_half = plan["corridors"]["stations_per_column"] // 2
    tws = 38                                             # W12 SS level-6 word stages (QWEN_W12_TP4_ME_EXTRA_SS)
    qA_op = dict(spine_to_head=1, head_chain=cols_half, corridor_stations=rows_half, block_tree_levels=4,
                 block_word_waypoints=math.ceil(tws / wp), tree_top_to_vm=1)
    qA = dict(per_me_op=sum(qA_op.values()), per_me_op_terms=qA_op,
              per_attention_round_trip=2 * math.ceil(hub_stack / wp), per_allreduce=2 * math.ceil(hub_io / wp),
              root_split_crossings_per_me_op=2)
    qC = dict(per_me_op=2, per_me_op_terms=dict(tile_tap_fifo=1, tree_top_fifo=1),
              per_me_op_banded_tree=3, per_attention_round_trip=2,
              per_allreduce_merged=0, per_allreduce_unmerged=2)

    def q_cycles(opt, dm):
        if opt == "A":
            # neighbour crossings: siblings deep in the reference tree, wander << T: 1 cycle; the two crossings a
            # path makes over the top-level split see the root-divergence wander
            extra = (dm["added_cycles"] - 1) * qA["root_split_crossings_per_me_op"]
            return me * (qA["per_me_op"] + extra) + att * qA["per_attention_round_trip"] + ar * qA["per_allreduce"]
        if opt == "C":
            return dm["added_cycles"] * (me * qC["per_me_op"] + att * qC["per_attention_round_trip"])
        if opt == "C_unmerged":
            return dm["added_cycles"] * (me * qC["per_me_op"] + att * qC["per_attention_round_trip"]
                                         + ar * qC["per_allreduce_unmerged"])
        if opt == "C_banded":
            return dm["added_cycles"] * (me * qC["per_me_op_banded_tree"] + att * qC["per_attention_round_trip"])
        return 0

    fo, mv, st = dsc["field_ops"], dsc["allreduces"], dsc["streamed_attention_index_ops"]
    hops = scen["stages"]
    die = __import__("uarch_model").DIE_SHRUNK_INTERIM
    bc = __import__("uarch_model").PRESETS["proposal"]["bcast_um"]
    reach = 504.0
    one_way = {r: math.ceil(bc[r] * die["field_scale"] / reach) for r in ("dense", "me", "expert")}
    dA = dict(per_field_op_central=2 * math.ceil(one_way["dense"] / wp) + 6 + 2,
              per_field_op_high=2 * math.ceil(one_way["expert"] / wp) + 6 + 2,
              terms="2 x ceil(one-way field wire stages / 4) link-station domains + 6 return-tree levels "
                    "(log4 of 2,682 pairs) + hub exit/entry; central = dense region, high = expert region",
              field_one_way_stages=one_way,
              per_stream_op=6, per_allreduce=2 * math.ceil(die["coll_stages"] / wp) - 2,
              per_stage_hop=2 * math.ceil(die["coll_stages"] / wp) - 2)
    dC = dict(per_field_op=2, per_stream_op=2, per_allreduce_merged=0, per_stage_hop_merged=0,
              per_allreduce_unmerged=2, per_stage_hop_unmerged=2)

    def d_cycles(opt, dm, high=False):
        if opt == "A":
            pf = dA["per_field_op_high" if high else "per_field_op_central"] + 2 * (dm["added_cycles"] - 1)
            return fo * pf + st * dA["per_stream_op"] + mv * dA["per_allreduce"] + hops * dA["per_stage_hop"]
        if opt == "C":
            return dm["added_cycles"] * (fo * dC["per_field_op"] + st * dC["per_stream_op"])
        if opt == "C_unmerged":
            return dm["added_cycles"] * (fo * dC["per_field_op"] + st * dC["per_stream_op"]
                                         + mv * dC["per_allreduce_unmerged"] + hops * dC["per_stage_hop_unmerged"])
        return 0

    latency = {}
    for wm, dm in dmeso.items():
        latency[wm] = dict(
            qwen={o: dict(vs_calibrated=rate_row(q_cycles(o, dm), qwen_base["calibrated_us"]),
                          vs_near_hbm_selected=rate_row(q_cycles(o, dm), qwen_base["near_hbm_selected_us"]))
                  for o in ("A", "B", "C", "C_unmerged", "C_banded")},
            deepseek={**{o: rate_row(d_cycles(o, dm), ds_base["scenario_c_ar_us"]) for o in ("A", "B", "C", "C_unmerged")},
                      "A_expert_paths": rate_row(d_cycles("A", dm, True), ds_base["scenario_c_ar_us"])})

    # ---- area: FIFO bits ---------------------------------------------------------------------------------------
    bc_cls = plan["bus_classes"]
    um2 = C["ff_um2_per_bit"]["v"]
    d_c = dmeso["central_thick_metal"]["depth_pow2"]
    d_b = dmeso["bound_ss_routed"]["depth_pow2"]
    tap_bits = 511 - 2          # tap minus its clock/reset wires
    q_C_bits = lambda D: (plan["instances"]["tile"] * tap_bits + bc_cls["tree_spine"]["wires"] + 4 * 544) * D
    q_A_wires = sum(bc_cls[k]["wires"] for k in ("corridor", "head_chain", "tree_block", "tree_spine", "link_spine",
                                                  "link_channel", "strip_fan"))
    ds_regions = math.ceil(math.sqrt(scen.get("die_mm2", 855.9)) / 4.9) ** 2
    ds_C_bits = lambda D: ds_regions * (732 + 512) * D + 4 * 1056 * D
    area = dict(
        qwen=dict(A=dict(fifo_bits=q_A_wires * 4, mm2=round(q_A_wires * 4 * um2 / 1e6, 2),
                         basis="every inter-element bus of floorplan.json bus_classes (corridor, head chain, ME tree, "
                               "block words, links, strip fan) at depth 4"),
                  B=dict(fifo_bits=0, mm2=0.0, basis="no FIFOs; hold-fix buffers on split-free mesh not priced"),
                  C=dict(fifo_bits=q_C_bits(d_c), mm2=round(q_C_bits(d_c) * um2 / 1e6, 2),
                         bound_mm2=round(q_C_bits(d_b) * um2 / 1e6, 2),
                         basis=f"1,536 tile-tap FIFOs x {tap_bits} b + 96 block-word FIFOs x 512 b + 4 strip-return "
                               f"x 544 b at depth {d_c} (bound depth {d_b}); gross (each replaces one existing input "
                               "register)"),
                  die_margin_mm2=plan["die"]["margin_mm2"]),
        deepseek=dict(A=dict(mm2_estimate="~6-9 (every field broadcast/return link station and tree edge at depth 4; "
                                          "widths 732 b x-broadcast, 512-1024 b return words, ASSUMED)"),
                      B=dict(mm2=0.0),
                      C=dict(regions=ds_regions, fifo_bits=ds_C_bits(d_c), mm2=round(ds_C_bits(d_c) * um2 / 1e6, 2),
                             bound_mm2=round(ds_C_bits(d_b) * um2 / 1e6, 2),
                             basis=f"{ds_regions} field regions of <= 4.9 x 4.9 mm on the 855.9 mm2 screen, each an "
                                   "entry FIFO (732 b, the 4/3-widened VM x read) and an exit FIFO (512 b return word, "
                                   "ASSUMED) + 4 hub-edge link FIFOs (1,056 b)")))

    # ---- clock distribution power (always-on part; the leaf/local trees are common to all options) -----------
    cpu = C["wire_cap_fF_per_um"]["v"] * (1 + C["driver_load_factor"]["v"])
    P = lambda length_um: length_um * cpu * 1e-15 * C["vdd"]["v"] ** 2 * F
    die_um2 = plan["die"]["w"] * plan["die"]["h"]
    htree_um = trunk["htree_total_mm"] * 1e3                  # 1,580-leaf H-tree to the mesh drivers / elements
    leaves = trunk["leaves"]
    side_mm = math.sqrt(trunk["array_mm"][0] * trunk["array_mm"][1])
    k_h = trunk["htree_total_mm"] / (side_mm * math.sqrt(leaves))
    region_trunk_um = k_h * side_mm * math.sqrt(128) * 1e3
    fwd_um = (plan["corridors"]["count"] * plan["die"]["h"] + 2 * cols_half * 313.632
              + 96 * 15000.0 + 4 * 22000.0 + 4 * 15600.0)
    power = dict(
        note="P = C V^2 f, full swing, activity 1 (clock); the local trees and flop clock pins are identical in all "
             "three options and dominate (ICG mandatory: V4.1 ungated pair clock 593 W a die); only the distribution "
             "above the local trees differs",
        B_mesh_W={f"pitch_{int(p)}um": round(P(2 * die_um2 / p) + P(htree_um), 2) for p in C["mesh_pitch_um"]["v"]},
        B_gating="ungatable inside a running die (the mesh is one net); stops only with the whole die",
        A_reference_tree_W=round(P(htree_um * math.sqrt(sum(plan["instances"].values()) / leaves)), 2),
        A_gating="reference tree always on; element trees gate at their roots",
        C_region_trunk_W=round(P(region_trunk_um), 3),
        C_forwarded_clocks_W_ungated=round(P(fwd_um), 2),
        C_forwarded_clocks_W_gated_40pct=round(0.4 * P(fwd_um), 2),
        C_gating="trunk always on (~0.1 W); every region and every forwarded link clock gates at its root when idle",
        forwarded_length_mm=round(fwd_um / 1e3),
        deepseek_scale=round(855.9 / plan["die"]["mm2"], 3))

    # ---- skew and jitter against the 60 / 25 ps policy --------------------------------------------------------
    thick = [m for m in trunk["models"] if m["model"] == "thick_metal_n5"][0]
    o5 = [o for o in thick["ocv"] if o["ocv_derate"] == 0.05][0]
    dvs = C["dV_per_cycle_mV"]["v"]
    skew = dict(
        rule="a pipelined link (<= 430.56 um a stage) only sees the skew between its two flops; a tree's skew matters "
             "where physically adjacent leaves diverge high in the tree (the top-level split lines)",
        single_tree_root_divergence_ps={m["model"]: [o["root_divergence_skew_ps"] for o in m["ocv"]] for m in trunk["models"]},
        A=dict(intra_element_ps="<= 5 (element <= 1.3 mm)", crossings="FIFO: no skew constraint",
               trunk_insertion_ps=round(ins["thick_metal_n5"]), jitter_ps={f"{d}mV": jitter_ps(ins["thick_metal_n5"], d) for d in dvs}),
        B=dict(adjacent_point_skew_ps="~10-20 (mesh shorts adjacent drivers; ASSUMED)",
               die_corner_to_corner_ps=f"{round(0.3 * o5['root_divergence_skew_ps'])}-{round(0.5 * o5['root_divergence_skew_ps'])} "
                                       "(0.3-0.5 x the 5% thick-metal root divergence, the systematic share a grid does not average; ASSUMED)",
               insertion_ps=round(ins["thick_metal_n5"] + 300),
               jitter_ps={f"{d}mV": jitter_ps(ins["thick_metal_n5"] + 300, d) for d in dvs},
               reading="the mesh driver tree carries ~5 nF on the core rail: at 9 mV a cycle its period jitter "
                       "(~65 ps) alone exceeds the 60 ps setup uncertainty; within budget only on a filtered rail "
                       "(~15 ps) or with adaptive clocking"),
        C=dict(region_internal_split_ps=round(2 * 0.05 * 3.2 * 150, 1),
               region_basis="4x4-tile block (1.25 x 5.17 mm): non-shared root-to-leaf ~3.2 mm on thick metal at 5% "
                            "OCV -> <= 60 ps setup; > 25 ps hold on the few buses crossing the region's own split "
                            "(hold-fixed in STA, propagated clocks)",
               trunk_jitter_ps={f"{d}mV": jitter_ps(ins["thick_metal_n5"], d) for d in dvs},
               forwarded_link_jitter_ps={f"{d}mV": jitter_ps(ins["thick_metal_n5"], d) for d in dvs},
               reading="trunk (~130 loads, ~0.1 W) and forwarded link clocks (~1.4 nF) put on a filtered clock rail: "
                       "~14 ps; wander between a forwarded clock and the receiving region is absorbed by the FIFO "
                       "window, not by the uncertainty"),
        policy=dict(setup_ps=UNC_SETUP_PS, hold_ps=UNC_HOLD_PS, relaxed=False))

    # ---- metastability -----------------------------------------------------------------------------------------
    q_async_bits = (24 + 4 + 2) * 2 * 3                  # H1-H24, K1-K4, L1-L2: two Gray pointers x 3 bits
    d_async_bits_system = scen["dies"] * 8 * 2 * 3       # ~8 async FIFOs a die (links, HBM, IO) on 336 dies
    meta = dict(
        mesochronous="no steady-state synchroniser: the read pointer is placed at reset from a synchronised sample "
                     "(exposure only during the reset handshake); a pointer-distance monitor fails closed if the "
                     "wander ever exceeds the window",
        qwen_async_2ff={f"tau{int(t)}": mtbf(2, t, 4 * q_async_bits) for t in C["sync"]["tau_ps"]},
        qwen_async_3ff={f"tau{int(t)}": mtbf(3, t, 4 * q_async_bits) for t in C["sync"]["tau_ps"]},
        deepseek_async_2ff={f"tau{int(t)}": mtbf(2, t, d_async_bits_system) for t in C["sync"]["tau_ps"]},
        deepseek_async_3ff={f"tau{int(t)}": mtbf(3, t, d_async_bits_system) for t in C["sync"]["tau_ps"]},
        reading="2-FF synchronisers: system MTBF ~6 weeks (Qwen, 4 dies) / ~2 days (DS, 336 dies) at tau 20 ps and "
                "under a second at tau 30 ps; 3-FF: > 1e14 years at tau 20 ps and ~4,000 years (DS) at tau 30 ps. "
                "Every truly asynchronous crossing uses 3 FFs (+1 cycle each). Under a plesiochronous A every one of "
                "the ~60 crossings an ME op would need this too (3 cycles each instead of 1).",
        three_ff_price=dict(qwen_cycles_per_token=36 + 72 * 2, deepseek_cycles_per_token=round(mv * 2 + hops * 2 + 43),
                            note="+1 cycle at each async crossing on the path (HBM KV read a layer, all-reduce TX/RX, "
                                 "stage hop TX/RX); identical in all options, <0.1%"))

    # ---- reference: the related-clock 3:4 crossing already built ------------------------------------------------
    ratio = dict(f2s_slow_cycles=xing["latency"]["fast_to_slow"]["max_dst_cycles"],
                 s2f_fast_cycles=xing["latency"]["slow_to_fast"]["max_dst_cycles"],
                 note="ot_ratio_cdc_fifo needs RELATED, STA-timed clocks (278 ps window): it must sit inside one clock "
                      "region (the hub), so a field-region crossing cannot be merged into it; a merged "
                      "mesochronous-ratio FIFO would save 1 cycle a field op each way (DS 0.14%, below the 1% gate)")

    return dict(trunk=trunk, wire_models=wire_models, dmeso=dmeso, qwen_base=qwen_base, ds_base=ds_base,
                counts=dict(qwen=dict(model=qwc, A=qA, C=qC), deepseek=dict(model=dsc, A=dA, C=dC, stage_hops_S73=hops)),
                latency=latency, area=area, power=power, skew=skew, meta=meta, ratio=ratio)


REFERENCES = [
    dict(id="Vangal08", cite="S. R. Vangal et al., \"An 80-Tile Sub-100-W TeraFLOPS Processor in 65-nm CMOS,\" IEEE JSSC 43(1):29-41, 2008",
         supports="mesochronous tile-to-tile interfaces (FIFO absorbs arbitrary static phase) instead of a die-wide skew budget"),
    dict(id="Howard11", cite="J. Howard et al., \"A 48-Core IA-32 Processor in 45 nm CMOS Using On-Die Message-Passing and DVFS for Performance and Power Scaling,\" IEEE JSSC 46(1):173-183, 2011",
         supports="per-tile frequency domains joined to the mesh by clock-crossing FIFOs (Intel SCC)"),
    dict(id="Restle01", cite="P. J. Restle et al., \"A clock distribution network for microprocessors,\" IEEE JSSC 36(5):792-799, 2001",
         supports="tree-driven global grid (mesh) for low skew in IBM high-performance processors"),
    dict(id="Kurd01", cite="N. A. Kurd et al., \"A multigigahertz clocking scheme for the Pentium 4 microprocessor,\" IEEE JSSC 36(11):1647-1653, 2001",
         supports="die-wide distribution needs active deskew to hold skew at multi-GHz"),
    dict(id="Tam00", cite="S. Tam et al., \"Clock generation and distribution for the first IA-64 microprocessor,\" IEEE JSSC 35(11):1545-1552, 2000",
         supports="regional active deskew of a global clock"),
    dict(id="Gronowski98", cite="P. E. Gronowski et al., \"High-performance microprocessor design,\" IEEE JSSC 33(5):676-686, 1998",
         supports="global clock distribution is a large fraction of chip power in grid-clocked processors (Alpha)"),
    dict(id="Chapiro84", cite="D. M. Chapiro, \"Globally-Asynchronous Locally-Synchronous Systems,\" PhD thesis, Stanford University, 1984",
         supports="origin of GALS"),
    dict(id="Krstic07", cite="M. Krstic, E. Grass, F. K. Gurkaynak, P. Vivet, \"Globally Asynchronous, Locally Synchronous Circuits: Overview and Outlook,\" IEEE Design & Test 24(5):430-441, 2007",
         supports="GALS trade-offs: crossing latency, verification, synchroniser cost"),
    dict(id="Ginosar11", cite="R. Ginosar, \"Metastability and Synchronizers: A Tutorial,\" IEEE Design & Test 28(5):23-35, 2011",
         supports="synchroniser MTBF = exp(t_r/tau)/(T_w f_c f_d); mesochronous/plesiochronous synchronisers"),
    dict(id="DallyPoulton98", cite="W. J. Dally, J. W. Poulton, Digital Systems Engineering, Cambridge University Press, 1998",
         supports="mesochronous / plesiochronous timing, source-synchronous (forwarded-clock) signalling"),
    dict(id="Keller15", cite="B. Keller, M. Fojtik, B. Khailany, \"A Pausible Bisynchronous FIFO for GALS Systems,\" ASYNC 2015",
         supports="low-latency bisynchronous FIFO for fine-grained GALS (NVIDIA Research)"),
    dict(id="Fojtik19", cite="M. Fojtik et al., \"A Fine-Grained GALS SoC with Pausible Adaptive Clocking in 16 nm FinFET,\" ASYNC 2019",
         supports="fine-grained GALS in a recent NVIDIA research SoC: per-partition clocks with FIFO crossings"),
    dict(id="Naffziger21", cite="S. Naffziger et al., \"Pioneering Chiplet Technology and Design for the AMD EPYC and Ryzen Processor Families,\" ISCA 2021",
         supports="product practice: separate core / fabric / memory clock domains joined by FIFOs"),
    dict(id="Grenat14", cite="A. Grenat et al., \"Adaptive clocking system for improved power efficiency in a 28nm x86-64 microprocessor,\" ISSCC 2014",
         supports="supply droop vs clock distribution timing handled by adaptive clock stretching"),
    dict(id="Ho01", cite="R. Ho, K. W. Mai, M. A. Horowitz, \"The future of wires,\" Proc. IEEE 89(4):490-504, 2001",
         supports="repeated global wire reach per cycle shrinks: die-crossing paths must be pipelined"),
    dict(id="Lie23", cite="S. Lie, \"Cerebras Architecture Deep Dive: First Look Inside the Hardware/Software Co-Design for Deep Learning,\" IEEE Micro 43(3):18-30, 2023",
         supports="wafer-scale fabric is a 2D mesh of nearest-neighbour links (no die-spanning synchronous path); its "
                  "clock distribution is not published in detail and is NOT relied on here"),
    dict(id="Choquette23", cite="J. Choquette, \"NVIDIA Hopper H100 GPU: Scaling Performance,\" IEEE Micro 43(3):9-17, 2023",
         supports="814 mm2-class single die; NVIDIA does not publish H100/B200 on-die clock topology, so no claim about "
                  "it is made here (B200's two dies are joined by a die-to-die link, necessarily a clock crossing)"),
    dict(id="Ajayi19", cite="T. Ajayi et al., \"Toward an Open-Source Digital Flow: First Learnings from the OpenROAD Project,\" DAC 2019",
         supports="the repository's flow (OpenROAD CTS) synthesises buffered trees; it has no clock-mesh synthesis"),
]


MEASURED_CONFIG = {"central_thick_metal": "d4_central", "tt_routed": "d8_tt_routed",
                   "bound_ss_routed": "d16_bound_ss"}


def measured_price(campaign_path: Path, physical_path, qwc, dsc, e) -> dict:
    """Option C re-priced with the delta the dual-clock bench measured on rtl/common/ot_meso_fifo.sv.

    Each priced op (Qwen ME op = tile tap in + tree top back; near-HBM attention round trip; DS field matvec and
    streamed op) is a region round trip: two crossings whose lags sum to a whole number of periods.  The bench
    measures that sum directly (data-ring lag + credit-ring lag - 2 T at each static phase), so the price per op is
    the measured round-trip delta: its typical value (every phase but the half-period resolution edge) and
    typical + 1 (the resolution edge, a static property of the chip after reset; also the bound for an op whose two
    crossings join different region pairs).  The phase average of a single
    crossing x 2 is reported alongside."""
    m = json.loads(Path(campaign_path).read_text())
    me, att = qwc["me_ops_per_token"], qwc["near_hbm_attention_round_trips"]
    fo, st = dsc["field_ops"], dsc["streamed_attention_index_ops"]
    out = dict(source=str(campaign_path), scope=m.get("scope"), rtl_sources=m.get("sources"), git=m.get("git"),
               basis="per op = measured round-trip delta (two crossings); model-only price was 2 x DELTA",
               wire_models={})
    for wm, cfg in MEASURED_CONFIG.items():
        c = m["configs"][cfg]
        rt = c["round_trip_delta_periods"]
        hist = rt["integer_histogram"]
        rt_typ = int(max(hist, key=lambda k: hist[k]))
        # the two lags of a round trip sit in OFFSET -+ T/2 windows and sum to whole periods, so the sum is the typical
        # value +-1; +1 occurs at the half-period resolution edge (seen at d4), and also bounds an op whose two
        # crossings join different region pairs (non-integer sum, rounded up at the destination edge)
        rt_max = max(int(round(rt["max"])), rt_typ + 1)
        x_mean = c["latency_no_wander"]["delta_periods_mean_over_phases"]
        rows = {}
        for label, per_op in (("typical", rt_typ), ("worst_phase", rt_max), ("phase_average", 2 * x_mean)):
            qc = per_op * (me + att)
            dc = per_op * (fo + st)
            rows[label] = dict(per_op_cycles=round(per_op, 4),
                               qwen=dict(vs_calibrated=rate_row(qc, e["qwen_base"]["calibrated_us"]),
                                         vs_near_hbm_selected=rate_row(qc, e["qwen_base"]["near_hbm_selected_us"])),
                               deepseek=rate_row(dc, e["ds_base"]["scenario_c_ar_us"]))
        out["wire_models"][wm] = dict(
            config=c["config"], round_trip_histogram=hist, crossing_delta_mean=x_mean,
            crossing_delta_range=[c["latency_no_wander"]["delta_periods_min"],
                                  c["latency_no_wander"]["delta_periods_max"]],
            model_only_per_op_cycles=2 * e["dmeso"][wm]["added_cycles"],
            nominal_words=c["nominal"]["words_delivered"], errors=c["nominal"]["errors"],
            false_faults=c["nominal"]["faults"], window_violations=c["nominal"]["window_violations"],
            drift_violation_before_fault=c["drift"]["violation_before_fault"], price=rows)
    if physical_path:
        ph = json.loads(Path(physical_path).read_text())
        out["physical_note"] = dict(source=str(physical_path),
                                    note="standard-cell area of one W=512 D4 crossing (data + credit rings, 8-entry "
                                         "receive buffer); see the route record for closure")
        m = ph.get("place_and_route", {}).get("metrics", {})
        if m:
            out["physical_note"].update(status=ph.get("status"), std_cell_area_um2=m.get("standard_cell_area_um2"),
                                        drc_errors=m.get("drc_errors"), max_slew_violations=m.get("max_slew_violations"))
        cs = Path(physical_path).with_name("corner_sta.json")
        if cs.is_file():
            c = json.loads(cs.read_text())
            out["physical_note"].update(corner_sta=str(cs), setup_ss_ps=c["setup_ss"]["worst_slack_ps"],
                                        hold_ff_ps=c["hold_ff"]["worst_slack_ps"],
                                        closes_signoff=c.get("closes_signoff"),
                                        latency_note="closure adds no cycles: the crossing delta above is measured "
                                                     "on the same RTL as the route")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--measured-campaign", type=Path, default=None,
                    help="campaign.json of tools/meso_fifo_campaign.py: re-price option C with the measured crossing "
                         "delta (adds measured_price; the model-only fields are unchanged)")
    ap.add_argument("--measured-physical", type=Path, default=None,
                    help="physical.json of the W=512 D4 ot_meso_fifo route: measured standard-cell area a crossing")
    a = ap.parse_args(argv)
    qwc, dsc = probes()
    e = evaluate(qwc, dsc)
    L = e["latency"]
    cen = L["central_thick_metal"]
    table = []
    for o, name in (("A", "GALS per hardened element"), ("B", "global mesh + local trees"),
                    ("C", "mesochronous regions + forwarded link clocks")):
        table.append(dict(option=o, name=name,
                          qwen_cycles=cen["qwen"][o]["vs_calibrated"]["cycles"],
                          qwen_pct_calibrated=cen["qwen"][o]["vs_calibrated"]["rate_change_pct"],
                          qwen_pct_near_hbm=cen["qwen"][o]["vs_near_hbm_selected"]["rate_change_pct"],
                          qwen_pct_near_hbm_bound=L["bound_ss_routed"]["qwen"][o]["vs_near_hbm_selected"]["rate_change_pct"],
                          ds_cycles=cen["deepseek"][o]["cycles"], ds_pct=cen["deepseek"][o]["rate_change_pct"],
                          ds_pct_bound=L["bound_ss_routed"]["deepseek"][o]["rate_change_pct"],
                          qwen_fifo_mm2=e["area"]["qwen"][o].get("mm2"),
                          clock_dist_W=(e["power"]["A_reference_tree_W"] if o == "A" else
                                        e["power"]["B_mesh_W"]["pitch_150um"] if o == "B" else
                                        round(e["power"]["C_region_trunk_W"] + e["power"]["C_forwarded_clocks_W_ungated"], 2)),
                          risk={"A": "low per element, but every per-cycle loop or credit path crossing an element "
                                     "boundary gains FIFO latency; ~8 mm2 of FIFOs",
                                "B": "HIGH: no mesh synthesis or multi-driver clock timing in the flow (SPICE sign-off), "
                                     "~3 W ungatable, jitter over budget unless the mesh is on a filtered rail",
                                "C": "MEDIUM-LOW: per-region OpenROAD CTS, one new FIFO primitive (mesochronous), "
                                     "forwarded-clock link stage + SDC; drift monitor fails closed"}[o]))
    rec = dict(
        schema="opentallas.rom_die_clocking_decision.v1", date="2026-10-03", status="MODEL_ONLY_DECISION_RECORD",
        scope="Qwen3-8B ROM die (fulldie r2 frame, 792.36 mm2) and DeepSeek-V4.1 ROM die (scenario C, S73, one rank a "
              "die). Streaming 1.2 GHz, serial 0.9 GHz (3:4 related, ratio FIFO at the hub), HBM 976.6 MHz (async). "
              "Sign-off SS setup 60 ps / FF hold 25 ps, not relaxed. No P&R run.",
        options=dict(A="GALS: one local tree per hardened element (tile+station, head, link station, spine slab, row "
                       "engine) from a common reference (mesochronous), FIFO at every inter-element bus. A per-COLUMN "
                       "tree is not an option: a half column is 15.5 mm, beyond the measured synchronous extent "
                       "(0.33-5.25 mm), and a clock run along the column is a forwarded clock, i.e. option C.",
                     B="Global mesh on M8/M9 driven by an H-tree, local trees below, one synchronous die, no FIFOs.",
                     C="Mesochronous regions <= 5.25 mm (Qwen: a 4x4-tile ME tree block, 1.25 x 5.17 mm; DS: ~4.9 mm "
                       "field squares; hub, spine segments, strips, IO band each a region) fed by a short trunk; the "
                       "pipelined links carry a forwarded clock with their data; one mesochronous FIFO where a link "
                       "delivers into a region; links ending at an existing async FIFO (SerDes/UCIe RX/TX, HBM) merge "
                       "into it by placing that FIFO's far side at the hub edge (dataflow level 2)."),
        comparison_table=table,
        recommendation=dict(
            qwen_rom="C",
            deepseek_rom="C",
            why=["A costs 3.5% (calibrated) / 6.3% (near-HBM) of Qwen per-user rate and 1.8-2.3% of DS: ~60 crossings "
                 "an ME op on the head chain, corridor, tree and return stations; fails the latency-first objective.",
                 "B adds no crossing latency, but its gain over C is 0.1-0.3% (below the 1% adoption gate) for HIGH "
                 "implementation risk: no mesh synthesis or timing in the flow, ~3 W ungatable a die, and period jitter "
                 "over the 60 ps budget unless the mesh is on a filtered rail.",
                 "C puts FIFOs only where the measured trunk says a single tree must split (H-tree root divergence "
                 "0.38-2.9 ns): 2 crossings a field op, +0.12-0.22% (Qwen) / +0.14% (DS) at central wander, <= 0.9% at "
                 "the SS-routed bound; ~2.5 mm2 of the Qwen die's 22.6 mm2 margin; region trees are ordinary CTS."],
            price_to_model=dict(
                qwen=dict(term="+2 x DELTA cycles on every ME op (tap + tree top) and +2 x DELTA on each near-HBM "
                               "attention round trip; DELTA = 1 central, 4 bound",
                          central_cycles=cen["qwen"]["C"]["vs_calibrated"]["cycles"],
                          central_us=cen["qwen"]["C"]["vs_calibrated"]["us"],
                          bound_cycles=L["bound_ss_routed"]["qwen"]["C"]["vs_calibrated"]["cycles"],
                          if_tree_top_banded_extra_cycles=round(e["counts"]["qwen"]["model"]["me_ops_per_token"]),
                          if_link_fifos_not_merged_extra_cycles=144,
                          rate_change_pct=dict(calibrated=cen["qwen"]["C"]["vs_calibrated"]["rate_change_pct"],
                                               near_hbm=cen["qwen"]["C"]["vs_near_hbm_selected"]["rate_change_pct"])),
                deepseek=dict(term="+2 x DELTA cycles on every field matvec and every streamed attention/index op",
                              central_cycles=cen["deepseek"]["C"]["cycles"], central_us=cen["deepseek"]["C"]["us"],
                              bound_cycles=L["bound_ss_routed"]["deepseek"]["C"]["cycles"],
                              unmerged_cycles=cen["deepseek"]["C_unmerged"]["cycles"],
                              rate_change_pct=cen["deepseek"]["C"]["rate_change_pct"]))),
        implementation_items=[
            "RTL rtl/common/ot_meso_fifo.sv: same-frequency, unknown-static-phase FIFO (forwarded write clock, region "
            "read clock); DOWN->WAIT->RUN reset handshake as ot_ratio_cdc_fifo; read pointer placed at reset from a "
            "3-FF-synchronised write-pointer sample; no steady-state synchroniser; DEPTH 4 (8 for the bound); credit "
            "return; pointer-distance monitor -> sticky fail-closed fault. Gate: dual-clock Verilator bench sweeping "
            "static phase 0..T and sinusoidal wander to +-w, mutants, 1e8 words; ORFS SS 60 ps / FF 25 ps at W=512 D4.",
            "RTL rtl/common/ot_fwd_link_stage.sv: data + forwarded clock register stage at <= 430.56 um; capture on "
            "the opposite edge (or matched delay) for hold; SDC create_generated_clock per segment; route the "
            "forwarded clock as a clock net (shielded M7/M8) beside its bus.",
            "Qwen: tile-tap meso FIFO (511 b) in the tile wrapper, 96 block-word FIFOs at the spine tree top, "
            "strip-return FIFOs at the hub; head chain + corridors become forwarded-clock links from the hub x root; "
            "all behind TAP_MESO=0 default-off; exact gate = bit-identical logits/VM/KV with only cycle shifts.",
            "DS: region entry/exit meso FIFOs on the field broadcast/return trees at each <= 4.9 mm region boundary; "
            "the ratio CDC (ot_ratio_cdc_fifo) stays inside the hub region; die-to-die RX/TX async FIFOs move their "
            "hub-side port to the hub edge; default-off parameter; same exact gate on L0/L20.",
            "All async crossings (HBM H1-H24/K1-K4, UCIe/SerDes, die-to-die): ot_async_fifo with SYNC_STAGES=3.",
            "Physical: REGIONS/GROUPS per clock region in the die DEF; one OpenROAD CTS per region root; a <= 130-leaf "
            "shielded trunk H-tree on M8/M9 from the PLL to region roots, and the forwarded link clocks, on a filtered "
            "clock rail (LDO; ~1.5 W load); per-region SDC create_clock at 0.833 ns, set_clock_groups -asynchronous "
            "between regions, set_max_delay -datapath_only 1 period on FIFO data/pointer arcs.",
            "Model: add the CLOCK_REGION term above to tools/uarch_model.py (Qwen ME op +2, attention +2; DS matvec +2, "
            "streamed op +2; DELTA 1 central, 4 bound) and re-price after the meso FIFO bench measures DELTA.",
            "Characterise ASAP7 synchroniser tau at SS (SPICE on DFFHQNx1) to confirm the 3-FF rule.",
            "Do NOT build a clock mesh; do NOT split below the hardened block (A)."],
        derivation=dict(wire_models_insertion_ps=e["wire_models"], mesochronous_crossing=e["dmeso"],
                        bases=dict(qwen=e["qwen_base"], deepseek=e["ds_base"]), counts=e["counts"],
                        latency=e["latency"], area=e["area"], clock_power=e["power"], skew_jitter=e["skew"],
                        metastability=e["meta"], related_ratio_fifo=e["ratio"], constants=C),
        references=REFERENCES,
        pins=PINS)
    if a.measured_campaign:
        rec["measured_price"] = measured_price(a.measured_campaign, a.measured_physical, qwc, dsc, e)
        rec["pins"][str(a.measured_campaign)] = sha_bytes(a.measured_campaign.read_bytes())
        if a.measured_physical:
            rec["pins"][str(a.measured_physical)] = sha_bytes(a.measured_physical.read_bytes())
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(table, indent=1))


if __name__ == "__main__":
    main()
