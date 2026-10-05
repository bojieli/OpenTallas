#!/usr/bin/env python3
"""Power in two separate scenarios, every input tagged with its evidence class and measurement boundary.

    python3 tools/power_scenarios.py [--out results/arch/power_scenarios.json]

Answers finding 3 of docs/ARCHITECTURE_ATLAS_FEASIBILITY_REVIEW_2026_09_27.md: the Qwen3 production power model
mixed an unbuilt lane with measured memory figures across different boundaries, labelled an integer result as an
FP4 MAC, and charged HBM controller energy to the DRAM stacks.  Here

* scenario A (measured implementation) prices every multiply-accumulate at what OUR routed matrix engine reports
  (ASAP7 sign-off, results/physical_abi3/asap7/signoff/energy_per_token.json), and
* scenario B (proposed production) prices it at a floating-point target lane derived from published per-operation
  energies (multiplier + one FP32 add per product: the golden's accumulation contract);

every other input is the same in both and is read from configs/hardware/power_scenarios.json, where each carries
its evidence class (measured-ours / published-measured / published-spec / assumed) and boundary.  The HBM path
energy is split between the DRAM stack (O'Connor's in-DRAM 3.45 pJ/bit) and the logic die (the rest of the least
favourable SC'25 path without a last-level cache, MI250X 13.64 pJ/bit: controller, PHY, I/O, control plane), and the
die's share is charged to die cooling.

Cooling is stated per COOLING CLASS (air, direct liquid) and package topology (logic dies per package): each limit is
a shipping package's rating (H200 SXM / B200 HGX air, GB200 liquid) less its own stacks at peak bandwidth, per die,
and two checks bind -- the die against its share and the package (dies + our stacks) against the rating.  For each
design point the record gives energy per token by component, die power against each class's limit and the rate each
class allows:

* Qwen3-8B ROM package (two reticles over UCIe, every layer split across both dies, 8-bit weights, 8 HBM3E stacks
  for the KV), 8K context, FP8 KV: autoregressive batch 1 and DFlash at the best block of the serial
  draft + verify + commit step (results/speculative/dflash_step_timing.json: tau, tokens per step, step cycles with
  the draft phase, and the drafter's MACs are read from that record, see dflash_point);
* DeepSeek-V4.1 ROM array at 1M and 200K: batch 1 without and with MTP (gamma 5, the measured tau) and the saturated batch,
  on the specification widths (deepseek_v41_rom_array) and on the adopted design point (deepseek_v41_design_point,
  which adds the 28-user fill and the saturated batch with MTP);
* the best switched HBM comparator of results/arch/v41_hbm_switched.json (99 dies in 50 two-die packages, 4 HBM3E
  stacks per die, the tensor group and lane multiplier each operating point picked there) priced on the SAME inputs
  and component list as the ROM design point, weights read from HBM instead of ROM (deepseek_v41_hbm_comparator), and
  the ROM / HBM ratios of rate and energy per token taken from these two blocks (rom_over_hbm).  Both machines are
  priced at the same boundary: the logic dies plus their stacks; switches and the wall chain are outside it (they are
  in v41_hbm_switched.json energy.*.wall_j).

The die's power is static (leakage + clock + HBM idle, and on the V4.1 machines the always-on links) plus dynamic
energy per token x rate, so the cooling-capped rate is (cooling - static) / dynamic energy per token -- per die for
the V4.1 array (see v41_points).  The top-level cooling_limit_w / capped_rate / binds use the liquid design class for
both the Qwen3-8B package (design_points.qwen3.cooling_class) and both V4.1 machines (V41_COOLING); air is a
sensitivity carried beside it in cooling_classes.

Always-on links (both V4.1 machines, the same rule): a 112G PAM4 lane transmits idle symbols when it carries no data,
so its power is static, and a UCIe link idles at its idle share.  The ROM array charges the rack's die-side lanes
(results/arch/v41_lanes.json static_w.rom_serdes: 84 lanes per layer/head package, 2 per table package, 0.728 W a
lane -- the rack's gate C4) and every die's UCIe idle (results/arch/arch_budget_v41.json power.static_w_per_die); the
switched HBM comparator charges the lanes that carry its own fabric's 0.9 TB/s per package per direction
(results/arch/v41_hbm_switched.json hbm_static_w_per_die.serdes, tools/arch_hbm_switched_v41.serdes_w_per_die) and
the same UCIe idle per die.  The per-bit link energy of the dynamic term is kept on both (a conservative overlap with
the always-on charge, the rack's C4 note).  The switch ASICs stay outside the boundary on both machines.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

CFG = ROOT / "configs/hardware/power_scenarios.json"
V41_REC = ROOT / "results/arch/arch_budget_v41.json"
V41_LANES = ROOT / "results/arch/v41_lanes.json"          # the adopted design point (design-point model)
V41_LADDER = ROOT / "results/arch/v41_latency_ladder.json"
V41_SWITCHED = ROOT / "results/arch/v41_hbm_switched.json"   # the best switched HBM comparator (design-point model)
OUT = ROOT / "results/arch/power_scenarios.json"
DFLASH_REC = ROOT / "results/speculative/dflash_step_timing.json"   # the Qwen3 DFlash operating point (single source)
SCHEMA = "opentallas.power-scenarios-result.v1"
SCENARIOS = ("A_measured_implementation", "B_proposed_production")
V41_COOLING = "liquid"      # user decision 2026-09-28: both V4.1 machines are liquid-cooled; air is a sensitivity


def dflash_point(qdp, rec_path=DFLASH_REC):
    """The Qwen3 DFlash operating point of design point `qdp` (the config's design_points.qwen3), read from the serial
    step record (tools/dflash_step_timing.py): the best block at the design context, FP8 KV and the lane multiplier;
    tokens a step (measured, cycle-weighted), step cycles with the draft phase, and the MACs of both phases."""
    spec = qdp["dflash"]
    assert ROOT / spec["from_record"] == rec_path, spec["from_record"]
    rec = json.loads(rec_path.read_text())
    assert rec["clock_hz"] == qdp["clock_hz"], "DFlash step record and design point clocks differ"
    m = qdp["area_mm2"]["lane_multiplier_m"]
    key = f"{qdp['context']}/fp8/m{m}"
    b = rec["rom"][key]["best"]
    B = b["block"]
    macs = {k: b[k] for k in ("draft_weight_macs", "draft_attention_macs", "verify_weight_macs",
                              "verify_attention_macs", "macs_per_step")}
    return dict(spec, record_key=key, tau=b["tokens_per_step"], block=B, slots=B, users=spec["users"],
                drafter=spec["drafter"], tokens_per_step=b["tokens_per_step"],
                tokens_per_step_band=b["tokens_per_step_band"], step_cycles=b["step_cycles"],
                draft_cycles=b["draft_cycles"], verify_cycles=b["verify_cycles"], commit_cycles=b["commit_cycles"],
                record_tokens_s=b["tokens_s"], record_tokens_s_band=b["tokens_s_band"],
                lane_copies_on=min(m, B) - 1, **macs)


def load_cfg(path=CFG, resolve_dflash=True):
    """The config; resolve_dflash reads the Qwen3 DFlash operating point from its record (tools/arch_budget_qwen3
    imports with resolve_dflash=False, because tools/dflash_step_timing.py imports it to WRITE that record)."""
    cfg = json.loads(Path(path).read_text())
    q = cfg["design_points"]["qwen3"]
    if resolve_dflash and "from_record" in q["dflash"]:
        q["dflash"] = dflash_point(q)
    return cfg


def val(x):
    return x["value"] if isinstance(x, dict) else x


def hbm_split(cfg):
    """(total, die, stack, stack_high) pJ/bit: die = total - stack, so the die is charged the controller, PHY,
    I/O and control plane and every joule is counted once."""
    m = cfg["memory"]
    total, stack = val(m["hbm_path_total"]), val(m["stack_share"])
    return dict(total=total, die=total - stack, stack=stack, stack_high=m["stack_share"]["stack_high_pj_per_bit"])


def mac_pj(cfg, scenario, design, fmt):
    """pJ per MAC of `fmt` on `design` ("qwen3" | "v41") in `scenario`."""
    L = cfg["mac_lane"]
    if scenario.startswith("A"):
        return val(L["scenario_A"][design])        # the only built lane: every MAC at its reported energy
    if scenario == "B_gpu_tensor_sensitivity":
        return val(L["bounds"]["gpu_tensor_measured"])
    return val(L["scenario_B"]["per_mac"][fmt])


COOLING_CLASSES = ("air", "liquid")


def reference_die_w(cfg, r):
    """Watts one logic die of reference package `r` may dissipate: the package rating minus its stacks at PEAK
    bandwidth charged at the stack's high-end energy (the largest deduction, so the smallest die share), per die."""
    stacks_w = r["hbm_bw_Bps"] * 8 * cfg["memory"]["stack_share"]["stack_high_pj_per_bit"] * 1e-12
    return (r["package_w"] - stacks_w) / r["dies"], stacks_w


def cooling_limits(cfg):
    """{class: {dies_per_package: limit}}: per-die watts from the LEAST favourable matched reference of the class and
    topology, the package rating it came with; liquid never below air, and air where no liquid reference exists."""
    C = cfg["cooling"]
    refs = C["references"]
    out = {}
    for cls in COOLING_CLASSES:
        out[cls] = {}
        for n in ("1", "2"):
            cands = []
            for k in C["classes"][cls][n]:
                r = refs[k]
                assert r["cooling"] == cls and str(r["dies"]) == n, k
                die_w, stk = reference_die_w(cfg, r)
                cands.append(dict(reference=k, die_w=die_w, package_w=r["package_w"], reference_stacks_w=stk,
                                  reference_die_w_per_mm2=(die_w / r["die_mm2"]) if r.get("die_mm2") else None))
            if cands:
                lim = dict(min(cands, key=lambda x: x["die_w"]), candidates=cands)
            else:
                lim = dict(out["air"][n], candidates=[], note="no liquid reference of this topology: the air limit")
            if cls != "air" and lim["die_w"] < out["air"][n]["die_w"]:
                lim = dict(out["air"][n], candidates=cands, note="liquid never below air")
            out[cls][n] = lim
    return out


def cooling_w(cfg, cls="air", dies_per_package=1):
    return cooling_limits(cfg)[cls][str(dies_per_package)]["die_w"]


def _cap(cool, static_w, dyn_w_per_rate, design_rate):
    """Largest rate with static + dyn_w_per_rate x rate <= cool (dyn_w_per_rate: joules the hottest die spends
    per unit of the rate), and whether it binds below the design rate."""
    head = cool - static_w
    thermal = head / dyn_w_per_rate if head > 0 else 0.0
    return dict(thermal_rate_limit=thermal, capped_rate=min(design_rate, thermal), binds=thermal < design_rate)


def _class_caps(cfg, n, static_w, dyn_w_per_rate, stk_w_per_rate, design_rate, logic_mm2):
    """Per cooling class: the die check (static + dyn x rate <= per-die limit) and the package check (every one of
    the n dies as hot as this one, plus its stacks at the high-end energy, within the reference package rating)."""
    out = {}
    for cls, lims in cooling_limits(cfg).items():
        lim = lims[str(n)]
        die = _cap(lim["die_w"], static_w, dyn_w_per_rate, design_rate)
        pkg = _cap(lim["package_w"] / n, static_w, dyn_w_per_rate + stk_w_per_rate, design_rate)
        thermal = min(die["thermal_rate_limit"], pkg["thermal_rate_limit"])
        capped = min(design_rate, thermal)
        die_w_cap = static_w + dyn_w_per_rate * capped
        out[cls] = dict(reference=lim["reference"], die_limit_w=lim["die_w"], package_limit_w=lim["package_w"],
                        dies_per_package=n, thermal_rate_limit=thermal, capped_rate=capped, binds=thermal < design_rate,
                        bound_by="die" if die["thermal_rate_limit"] <= pkg["thermal_rate_limit"] else "package",
                        die_w_at_cap=die_w_cap, package_w_at_cap=n * (die_w_cap + stk_w_per_rate * capped),
                        die_w_per_mm2_at_cap=die_w_cap / cfg["cooling"]["die_mm2"],
                        logic_w_per_mm2_at_cap_upper=die_w_cap / logic_mm2)
    return out


# -- Qwen3-8B ROM package -----------------------------------------------------------------------------------------------
def _qwen_areas(dp, copies_on):
    """Logic, clocked logic, ROM and SRAM mm2 of the WHOLE package (area_mm2 holds package totals)."""
    a = dp["area_mm2"]
    m = a["lane_multiplier_m"]
    copies = a["lane_copy"] * (m - 1)
    logic = a["compute"] + a["interconnect"] + a["overhead"] + a["hbm_phy"] + a.get("ucie_phy", 0.0) + \
        a["stream_unit_spill"] + copies
    clocked = logic - copies * (1 - copies_on / max(1, m - 1))
    return dict(logic=logic, clocked_logic=clocked, rom=a["rom"] + a["drafter_rom"], sram=a["sram"])


def _die_static(cfg, ar, clock, stacks):
    d = cfg["die"]
    lk, cm = d["leakage_w_per_mm2"], d["clock_region_multiplier"]
    leak = ar["logic"] * val(lk["logic"]) + ar["rom"] * val(lk["rom_array"]) + ar["sram"] * val(lk["sram_array"])
    clk = val(d["clock_j_per_mm2_per_cycle"]) * clock * (ar["clocked_logic"] * cm["logic"] + ar["rom"] * cm["rom_array"]
                                                         + ar["sram"] * cm["sram_array"])
    idle = stacks * val(cfg["memory"]["idle_w_per_stack"])
    return dict(leakage_w=leak, clock_w=clk, hbm_idle_w=idle)


def qwen_point(cfg, scenario, key, hbm_die_pj=None):
    """One Qwen3 ROM-package step on scenario `scenario`: energy by component (per emitted token, the whole package:
    both dies and their stacks), each die's power at the design rate, the cooling-limited rate.  The package is
    dies_per_package reticles splitting every layer (tensor-parallel): both dies carry the same work, so each die
    dissipates 1/n of the package's die-side power and is checked against the per-die limit of its package class.
    `hbm_die_pj` overrides the die's HBM share (sensitivity)."""
    import arch_budget_qwen3 as QB
    dp = cfg["design_points"]["qwen3"]
    pt = dp[key]
    clock = dp["clock_hz"]
    wl = QB.workload(dp["context"])
    kv_per_user = wl["bytes"]["kv_read"] * dp["kv_format_bytes_per_elem"] / 2     # workload() counts BF16 (2 B)
    Q = QB.Q
    n = pt["users"] * pt["slots"]
    dr = pt["drafter"]
    if dr:   # the serial step record's MACs: the verify over the slots and the drafter's forward (dflash_point)
        assert pt["verify_weight_macs"] == n * wl["weight_macs"] and pt["verify_attention_macs"] == n * wl["attention_macs"]
        mac_w = pt["verify_weight_macs"] + pt["draft_weight_macs"]
        mac_a = pt["verify_attention_macs"] + pt["draft_attention_macs"]
    else:
        mac_w, mac_a = n * wl["weight_macs"], n * wl["attention_macs"]
    kvb = pt["users"] * kv_per_user * ((1 + QB.DRAFTER_LAYERS / Q["L"]) if dr else 1)
    sweeps = 1 if dr else math.ceil(n / dp["area_mm2"]["lane_multiplier_m"])
    # Weight format (design point): weight_bits / drafter_weight_bits a weight, weight_scale_bytes of scales read
    # with every sweep of the target, the weight MAC lane weight_mac_format; hbm_weight_bytes (optional, per point)
    # are weights read from the KV stacks instead of ROM (an option of results/arch/qwen3_8bit_design.json).
    wbits, dbits = dp["weight_bits"], dp["drafter_weight_bits"]
    wbytes = sweeps * (wl["weight_macs"] * wbits / 8 + dp.get("weight_scale_bytes", 0)) + \
        (QB.DRAFTER_PARAMS * dbits / 8 if dr else 0)
    hbm_w = pt.get("hbm_weight_bytes", 0)
    d = cfg["die"]
    hb = hbm_split(cfg)
    die_pj = hb["die"] if hbm_die_pj is None else hbm_die_pj
    stack_pj = hb["total"] - die_pj
    sram, dlv = val(d["sram_j_per_byte"]), val(d["operand_delivery_j_per_byte"])
    toks = pt["tokens_per_step"]
    dyn = dict(   # joules per STEP, die-side dynamic, both dies
        mac_weights=mac_w * mac_pj(cfg, scenario, "qwen3", dp["weight_mac_format"]) * 1e-12,
        mac_attention=mac_a * mac_pj(cfg, scenario, "qwen3", "bf16") * 1e-12,
        weight_read_and_delivery=wbytes * (val(d["rom_read_j_per_byte"]) + dlv),
        kv_ring_sram_and_delivery=kvb * (2 * sram + dlv),
        # the drafter's 5 layers add their elementwise work over the same slots (5/36 of the target's)
        stream_unit=n * wl["elementwise_total"] * ((1 + QB.DRAFTER_LAYERS / Q["L"]) if dr else 1)
        * (val(d["stream_fp32_op_j"]) + 12 * sram),
        hbm_controller_phy_io=kvb * 8 * die_pj * 1e-12,
    )
    if hbm_w:
        dyn["hbm_weight_read"] = hbm_w * (8 * die_pj * 1e-12 + 2 * sram + dlv)
    n_pkg = dp["dies_per_package"]
    if n_pkg > 1:   # the TP-2 exchanges over UCIe, both directions: a step's bytes (tools/arch_budget_qwen3.tp_exchanges:
        # the FP32 partials of every slot, the argmax gathers, the embedding rows; the draft's own with DFlash)
        nbytes = QB.tp_exchanges(clock, n)["bytes_per_direction"]
        if dr:
            nbytes += QB.tp_exchanges(clock, n, "draft")["bytes_per_direction"]
        dyn["ucie_exchange"] = nbytes * 2 * 8 * val(d["link_j_per_bit"]["ucie"])
    ar = _qwen_areas(dp, pt["lane_copies_on"])
    st = _die_static(cfg, ar, clock, dp["hbm_stacks"])       # the package's static watts
    static_w = sum(st.values())
    t = pt["step_cycles"] / clock
    rate = toks / t
    dyn_tok = sum(dyn.values()) / toks
    stack_tok = (kvb + hbm_w) * 8 * stack_pj * 1e-12 / toks
    stk_hi_tok = (kvb + hbm_w) * 8 * hb["stack_high"] * 1e-12 / toks
    die_w = (static_w + dyn_tok * rate) / n_pkg
    cls = dp.get("cooling_class", "air")        # the design point's cooling class (Qwen O4: liquid, user decision)
    cool = cooling_w(cfg, cls, n_pkg)
    classes = _class_caps(cfg, n_pkg, static_w / n_pkg, dyn_tok / n_pkg, stk_hi_tok / n_pkg, rate, ar["logic"] / n_pkg)
    cap = {k: classes[cls][k] for k in ("thermal_rate_limit", "capped_rate", "binds")}
    comp = {k: v / toks * 1e3 for k, v in dyn.items()}
    comp.update({k.replace("_w", ""): v / rate * 1e3 for k, v in st.items()})
    return dict(design_rate_tokens_s=rate, step_cycles=pt["step_cycles"], tokens_per_step=toks,
                dies_per_package=n_pkg,
                energy_per_token_mj=(dyn_tok + static_w / rate + stack_tok) * 1e3,
                die_energy_per_token_mj=(dyn_tok + static_w / rate) * 1e3,
                die_dynamic_mj_per_token=dyn_tok * 1e3, stack_energy_per_token_mj=stack_tok * 1e3,
                die_components_mj_per_token=comp, die_static_w={k: v / n_pkg for k, v in st.items()},
                package_static_w=st, die_w_at_design_rate=die_w, package_dies_w_at_design_rate=die_w * n_pkg,
                stacks_w_at_design_rate=stack_tok * rate + 0.0, stacks_w_high=stk_hi_tok * rate,
                cooling_class=cls, cooling_limit_w=cool, die_over_cooling=die_w / cool, cooling_classes=classes, **cap)


# -- DeepSeek-V4.1 ROM array ------------------------------------------------------------------------------------------
FMT = {"fp8": "fp8", "fp4": "fp4", "bf16": "bf16", "fp32": "fp32", "bf16xfp8": "bf16"}


def _v41_energy(cfg, scenario, V, E, ctx, users, positions, hbm_die_pj=None, weights="rom"):
    """Joules per emitted POSITION of the whole array, die-side dynamic by component and the stacks' share.
    Same quantities as tools/arch_budget_v41.energy_per_token (weights read once per microbatch pass, routed
    experts as their union, KV and index keys per user), priced on the scenario's inputs.  weights="hbm" (the HBM
    comparator): the same weight bytes come from the die's stacks -- the die pays the HBM path's die share
    (controller, PHY, I/O) and operand delivery, the stacks their in-DRAM share -- instead of the ROM read."""
    c = E["c"]
    tot, _ = V.token_workload(c, ctx)
    tokens = max(1.0, users * positions)
    NE, KE, FF, D_ = c["num_routed_experts"], c["experts_per_token"], c["moe_intermediate_size"], c["hidden_size"]
    U = V.distinct_experts(round(tokens), NE, KE)
    routed_b = c["num_layers"] * KE * 3 * FF * D_ * V.FP4
    w_bytes = (tot["bytes"]["rom"] - routed_b) / tokens + routed_b * (U / KE) / tokens
    d = cfg["die"]
    hb = hbm_split(cfg)
    die_pj = hb["die"] if hbm_die_pj is None else hbm_die_pj
    hbm_bits = (tot["bytes"]["kv_hbm"] + tot["bytes"]["idx"]) / positions * 8
    lj = d["link_j_per_bit"]
    w_rd = val(d["rom_read_j_per_byte"]) if weights == "rom" else 0.0
    w_bits = w_bytes * 8 if weights == "hbm" else 0.0
    dyn = dict(
        mac=sum(v * mac_pj(cfg, scenario, "v41", FMT.get(k.split(":")[1], "bf16")) * 1e-12
                for k, v in tot["macs"].items()),
        weight_read_and_delivery=w_bytes * (w_rd + val(d["operand_delivery_j_per_byte"])),
        kv_sram=tot["bytes"]["kv_sram"] * val(d["sram_j_per_byte"]),
        stream=sum(tot["elems"].values()) * 3 * val(d["stream_fp32_op_j"]),
        links=tot["collective_bytes"] * 8 * (val(lj["board"]) + val(lj["ucie"])) * 4,
        hbm_controller_phy_io=hbm_bits * die_pj * 1e-12,
    )
    if weights == "hbm":
        dyn["weight_hbm_controller_phy_io"] = w_bits * die_pj * 1e-12
    bits = hbm_bits + w_bits
    return dyn, bits * (hb["total"] - die_pj) * 1e-12, bits * hb["stack_high"] * 1e-12


PLACEMENT = ROOT / "results/arch/v41_die_placement.json"
ROUTED_OPS = ("ffn.experts_w13", "ffn.experts_w2", "ffn.experts_swiglu")
DRAFT_EXPERTS_PER_TOKEN = 3     # DSpark drafter: 128-expert top-3 MoE per stage (arch_budget_v41.draft_cost_s)


def v41_die_workloads(V, c, ctx, G=4, mtp=False, batch=1):
    """Per-DIE op lists of the V4.1 ROM array: each layer die (stage s of results/arch/v41_die_placement.json, tensor
    group G) and a head die.  A layer's routed experts are split over the stages that hold its bytes, in the
    placement's fractions (the experts are ~all of a layer's stored bytes); every other op of the layer (attention,
    indexer, KV, hyper-connections, router, shared expert, combine, Engram) and its collectives run on the stage where
    the layer starts (its attention and KV owner, tools/v41_rack_design.placement) -- the conservative assignment for
    that stage.  Within a stage an op runs at its die share ('tp' = 1/G, 'rep' = every die), KV-SRAM rows are read by
    every die (the rows are all-gathered), as tools/arch_budget_v41.token_workload's die share.  A split index scan
    (tools/v41_stage_rebalance.active_plan) moves its scan and select shares to the helper stages.  Returns
    {stage: [(op, weight)]} and {stage: collective payload bytes per die}, with 'head' for a head die."""
    P_ = json.loads(PLACEMENT.read_text())
    frac, start = {}, {}
    for st in P_["stages"]:
        for l in st["layers"]:
            frac.setdefault(l["layer"], []).append((st["stage"], l["fraction"]))
            start.setdefault(l["layer"], st["stage"])
    ops = {st["stage"]: [] for st in P_["stages"]}
    coll = {st["stage"]: 0.0 for st in P_["stages"]}
    for L in range(c["num_layers"]):
        lops, _meta = V.ops_of_layer(c, L, ctx)
        tot = sum(f for _, f in frac[L])
        for o in lops:
            o["_layer"] = L
            if o["name"] in ROUTED_OPS:
                for s_, f in frac[L]:
                    ops[s_].append((o, f / tot))
            else:
                ops[start[L]].append((o, 1.0))
        coll[start[L]] += sum(p for _, _, p in V.collectives_of_layer(c, L, G))
    ops["head"] = [(o, 1.0) for o in V.head_ops(c)]
    coll["head"] = 0.0
    import v41_stage_rebalance as SR           # a split index scan's shares on its helper stages (the active plan)
    return SR.die_work_split(ops, coll, ctx, mtp=mtp, batch=batch)


def _die_energy(cfg, scenario, V, E, die_ops, coll_B, users, positions, hbm_die_pj=None, G=4):
    """Die-side dynamic joules per POSITION on ONE die (the _v41_energy components, priced op by op at the die's
    share): weights read once per pass (routed experts at their union), KV rows per user."""
    c = E["c"]
    tokens = max(1.0, users * positions)
    NE, KE = c["num_routed_experts"], c["experts_per_token"]
    Ux = V.distinct_experts(round(tokens), NE, KE)
    d = cfg["die"]
    hb = hbm_split(cfg)
    die_pj = hb["die"] if hbm_die_pj is None else hbm_die_pj
    lj = d["link_j_per_bit"]
    w_j = val(d["rom_read_j_per_byte"]) + val(d["operand_delivery_j_per_byte"])
    dyn = dict(mac=0.0, weight_read_and_delivery=0.0, kv_sram=0.0, stream=0.0, links=0.0, hbm_controller_phy_io=0.0)
    for o, w in die_ops:
        sh = (1.0 if o["share"] == "rep" else 1.0 / G) * w
        if o["macs"]:
            dyn["mac"] += o["macs"] * sh * mac_pj(cfg, scenario, "v41", FMT.get(o["fmt"], "bf16")) * 1e-12
        rb = o["bytes"]["rom"] * sh
        rb = rb * (Ux / KE) if o["name"] in ROUTED_OPS else rb
        dyn["weight_read_and_delivery"] += rb / tokens * w_j
        dyn["kv_sram"] += o["bytes"]["kv_sram"] * w * val(d["sram_j_per_byte"])
        if o["elems"] and o["cls"] in ("su", "sfu", "sinkhorn"):
            dyn["stream"] += o["elems"] * sh * 3 * val(d["stream_fp32_op_j"])
        dyn["hbm_controller_phy_io"] += ((o["bytes"]["kv_hbm"] + o["bytes"]["idx"]) * sh / positions * 8
                                         * die_pj * 1e-12)
    dyn["links"] = coll_B * 8 * (val(lj["board"]) + val(lj["ucie"]))
    return dyn


def v41_hottest_die(cfg, scenario, V, E, ctx, users, positions, mtp_factor, draft_overhead, hbm_die_pj=None,
                    window=None, batch=1):
    """The HOTTEST die's dynamic joules per emitted token by component, and every die's total, for one operating
    point: layer dies per stage (v41_die_workloads) and the head die (LM head + argmax per position, plus, with MTP,
    the draft priced from the drafter's own ops, on the 4 head dies).  mtp_factor = (gamma + 1) / tau
    with MTP, else 1.  window: {die: factor} -- the die's power is its joules per token x rate x factor (batch 1:
    the pass time over the die's active window; saturated: 1); the hottest die is the one with the most power."""
    ops, coll = v41_die_workloads(V, E["c"], ctx, mtp=positions > 1, batch=batch)
    per = {s: {k: v * mtp_factor for k, v in _die_energy(cfg, scenario, V, E, o, coll[s], users, positions,
                                                         hbm_die_pj).items()} for s, o in ops.items()}
    draft_proxy = None
    if draft_overhead:
        # the draft on a head die, priced from the drafter's own work (arch_budget_v41.draft_cost_s): 3 DSpark stages
        # over gamma rows with WINDOW-ONLY attention -- priced as layer 0's ops, the sliding-window layer, whose
        # ops with the routed experts at the drafter's top-3 of the target's top-6 -- then gamma Markov steps (an
        # lm_head row, the rank-256 bias, argmax); one draft per verify pass, so per emitted token / tau.  The former
        # proxy (draft_overhead x every layer die's verify energy) is kept as draft_proxy: it charged the target's
        # context-dependent index scans to a drafter that does not scan the context.
        gamma = max(1, positions - 1)
        tau = positions / mtp_factor
        c = E["c"]
        l0, _ = V.ops_of_layer(c, 0, ctx)
        topk = DRAFT_EXPERTS_PER_TOKEN / c["experts_per_token"]      # the drafter's top-3 against the target's top-6
        e_stage = _die_energy(cfg, scenario, V, E, [(o, 3.0 * (topk if o["name"] in ROUTED_OPS else 1.0)) for o in l0],
                              0.0, users, gamma, hbm_die_pj)
        markov = dict(name="draft.markov_bias", sub="head", cls="weight", macs=2 * c["vocab_size"] * 256, fmt="bf16",
                      bytes=dict(rom=2 * c["vocab_size"] * 256 * 2, kv_sram=0, kv_hbm=0, idx=0, engram=0), elems=0,
                      fn="none", chain=0, share="tp", topk=None)
        e_step = _die_energy(cfg, scenario, V, E, [(o, 1.0) for o in V.head_ops(c)] + [(markov, 1.0)], 0.0, users, 1,
                             hbm_die_pj)
        draft_j = (gamma * sum(e_stage.values()) + gamma * sum(e_step.values())) / tau
        layer_total = 4 * sum(sum(v.values()) for s, v in per.items() if s != "head")
        draft_proxy = draft_overhead * layer_total / 4
        per["head"]["draft"] = draft_j
    tot = {str(s): sum(v.values()) for s, v in per.items()}
    win = {s: (window or {}).get(s, 1.0) for s in tot}
    hot = max(tot, key=lambda s: tot[s] * win[s])
    layer = [v for s, v in tot.items() if s != "head"]
    return dict(hottest=hot, hottest_components_j_per_token=per[hot if hot == "head" else int(hot)],
                hottest_j_per_token=tot[hot], hottest_window_factor=win[hot], die_j_per_token=tot,
                window_factor=win, layer_die_mean_j_per_token=sum(layer) / len(layer),
                hottest_over_layer_mean=tot[hot] / (sum(layer) / len(layer)),
                head_draft_j_per_token=per["head"].get("draft"), head_draft_proxy_j_per_token=draft_proxy)


def v41_links_static():
    """Always-on link watts of both V4.1 machines, from their records (see the module doc): per hottest die and per
    machine.  ROM: a layer die's lanes (the budget's serdes_always_on, 84 lanes per package / 2) + UCIe idle; the
    array = the rack's die-side lanes (v41_lanes static_w.rom_serdes) + every die's UCIe idle.  HBM comparator: its
    fabric's lanes per die + the same UCIe idle, x its dies."""
    sw = json.loads(V41_REC.read_text())["power"]["static_w_per_die"]
    ln = json.loads(V41_LANES.read_text())["static_w"]
    hs = json.loads(V41_SWITCHED.read_text())
    dies_rom = json.loads(CFG.read_text())["design_points"]["v41"]["dies"]
    return dict(
        rom=dict(serdes_w_per_die=sw["serdes_always_on"], ucie_idle_w_per_die=sw["ucie_idle"],
                 serdes_w_array=ln["rom_serdes"], ucie_idle_w_array=sw["ucie_idle"] * dies_rom,
                 array_w=ln["rom_serdes"] + sw["ucie_idle"] * dies_rom, dies=dies_rom,
                 source="results/arch/v41_lanes.json static_w.rom_serdes (4,944 die-side lanes x 0.728 W, rack gate "
                        "C4); results/arch/arch_budget_v41.json power.static_w_per_die (serdes_always_on, ucie_idle)"),
        hbm=dict(serdes_w_per_die=hs["hbm_static_w_per_die"]["serdes"], ucie_idle_w_per_die=sw["ucie_idle"],
                 dies=hs["dies"], array_w=(hs["hbm_static_w_per_die"]["serdes"] + sw["ucie_idle"]) * hs["dies"],
                 source="results/arch/v41_hbm_switched.json hbm_static_w_per_die.serdes (the lanes of 0.9 TB/s per "
                        "package per direction, 0.728 W a lane, shared by 2 dies) and dies; UCIe idle as the ROM die"))


def _v41_static(cfg, E, V, D):
    """Per-die static watts of an ACTIVE die: leakage over the die's whole logic and ROM area, clock over the
    whole logic (ungated: the conservative end -- the populated blocks are 87 mm2 of 526), 5 stacks' idle, and a
    layer die's always-on links (112G lanes + UCIe idle, v41_links_static)."""
    d = E["designs"][D.ARRAY_DESIGN]["area_split_per_device"]
    logic = d["total_mm2"] - d["rom_mm2"] - d["sram_mm2"]
    ar = dict(logic=logic, clocked_logic=logic, rom=d["rom_mm2"], sram=d["sram_mm2"])
    st = _die_static(cfg, ar, E["clock"], cfg["design_points"]["v41"]["hbm_stacks_per_die"])
    lk = v41_links_static()["rom"]
    st["links_always_on_w"] = lk["serdes_w_per_die"] + lk["ucie_idle_w_per_die"]
    return st


def _spec_rates(ctx):
    """The SPECIFICATION model's rates (results/arch/arch_budget_v41.json batch rows), MTP at the config's tau."""
    rows = json.loads(V41_REC.read_text())["batch"][str(ctx)]["rows"]["rom"]
    sat = max((r for r in rows if r.get("fits_capacity", True)), key=lambda r: r["ar_aggregate_tokens_s"])
    return dict(ar=rows[0]["ar_tokens_s_per_user"], mtp=rows[0]["mtp_tokens_s_per_user"],
                sat_rate=sat["ar_aggregate_tokens_s"], sat_batch=sat["batch"])


def _dp_rates(ctx):
    """The adopted DESIGN POINT's headline rates (results/arch/v41_lanes.json design_point: collective tails
    measured in the RTL stage bench with the adopted levers) and its saturated aggregate at 1,024 users (energy rows,
    same pricing)."""
    ln = json.loads(V41_LANES.read_text())
    d = ln["design_point"][str(ctx)]
    en = ln["energy"][str(ctx)]
    sat = en["sat1024"]["rom"]
    sb = en["sat1024"].get("batch", 1024)            # the saturated point holds at most the users held (capacity)

    def win(k):
        """Batch 1: a die is active for max(pass / stages, its stage's busy time) of each pass (T / stages alone
        would under-count a heavy stage's window and over-state its power)."""
        e = en[k]
        tau = json.loads(V41_LADDER.read_text())["tau"] if k.endswith("_mtp") else 1.0
        cyc, st = tau / e["rom"]["tokens_s_per_user"] * 1e6, 28          # one pass (verify + draft with MTP), us
        return {s: cyc / max(cyc / st, b) for s, b in e.get("stage_busy_us", {}).items()}
    return dict(ar=d["ar"], mtp=d["mtp"], sat_rate=sat["aggregate_tokens_s"], sat_batch=sb, sat_key=1024,
                windows=dict(ar_batch1=win("b1"), mtp_batch1=win("b1_mtp")),
                extra={"fill28": (28, False, en["fill28"]["rom"]["aggregate_tokens_s"]),
                       "fill28_mtp": (28, True, en["fill28_mtp"]["rom"]["aggregate_tokens_s"]),
                       "saturated_batch1024_mtp": (en["sat1024_mtp"].get("batch", 1024), True,
                                                   en["sat1024_mtp"]["rom"]["aggregate_tokens_s"])})


def v41_design_points(cfg, scenario, hbm_die_pj=None):
    """The same pricing on the DESIGN-POINT model (tools/arch_budget_v41.py workload; rates of
    results/arch/v41_lanes.json design_point; MTP at the design point's measured tau, gamma 5)."""
    import arch_budget_v41 as V
    lad = json.loads(V41_LADDER.read_text())
    return v41_points(cfg, scenario, hbm_die_pj, V=V, rates=_dp_rates, tau=lad["tau"], gamma=lad["gamma"])


def v41_points(cfg, scenario, hbm_die_pj=None, V=None, rates=_spec_rates, tau=None, gamma=None):
    if V is None:
        import arch_budget_v41 as V
    import decode_critical_path as D
    E = V._env()
    dp = cfg["design_points"]["v41"]
    st = _v41_static(cfg, E, V, D)
    static_w = sum(st.values())
    links = v41_links_static()["rom"]
    n_pkg = dp["dies_per_package"]
    cool = cooling_w(cfg, V41_COOLING, n_pkg)
    ad = E["designs"][D.ARRAY_DESIGN]["area_split_per_device"]
    logic_mm2 = ad["total_mm2"] - ad["rom_mm2"] - ad["sram_mm2"]
    ld, stages, dies = dp["layer_dies"], dp["stages"], dp["dies"]
    g, ovh = gamma or dp["mtp"]["gamma"], dp["mtp"]["draft_overhead"]
    tau = tau or V.TAU_HEADLINE           # the measured V4.1-Flash tau (arch_budget_v41, from its record)
    out = {}
    for ctx in dp["contexts"]:
        rt = rates(ctx)
        pts = {}
        # batch 1, autoregressive: one token at a time; a layer die works only while its stage holds it (T/stages),
        # so the hottest die spends (die energy / layer dies) in T/stages: power = E x rate x stages / layer dies
        dyn, stk, stk_hi = _v41_energy(cfg, scenario, V, E, ctx, 1, 1, hbm_die_pj)
        pts["ar_batch1"] = dict(rate=rt["ar"], per_die=stages / ld, dyn=dyn, stk=stk, stk_hi=stk_hi, users=1, pos=1,
                                mtp=False, window=stages,
                                basis="per user; hottest die = the hottest die during its stage window (T / stages)")
        # batch 1 with MTP: a verify pass is gamma+1 positions per tau emitted tokens (+ the draft's ~3/40)
        dv, sv, sv_hi = _v41_energy(cfg, scenario, V, E, ctx, 1, g + 1, hbm_die_pj)
        f = (g + 1) / tau * (1 + ovh)
        pts["mtp_batch1"] = dict(rate=rt["mtp"], per_die=stages / ld,
                                 dyn={k: v * f for k, v in dv.items()}, stk=sv * f, stk_hi=sv_hi * f,
                                 users=1, pos=g + 1, mtp=True, window=stages,
                                 basis=f"per user, gamma {g}, tau {tau}")
        # saturated batch: every layer die busy all the time; its share of the aggregate is 1 / layer dies
        m = V.fill_machine(rt["sat_batch"])
        ds, ss, ss_hi = _v41_energy(cfg, scenario, V, E, ctx, m.microbatch, 1, hbm_die_pj)
        pts[f"saturated_batch{rt.get('sat_key', rt['sat_batch'])}"] = dict(
            rate=rt["sat_rate"], per_die=1 / ld, dyn=ds, stk=ss, stk_hi=ss_hi, batch=rt["sat_batch"],
            users=m.microbatch, pos=1, mtp=False, window=1,
            basis=f"aggregate tokens/s of the array, batch {rt['sat_batch']}")
        # the design point's further operating points: every layer die holds a user (fill) or a microbatch (sat)
        for k, (bt, mtp, rate) in rt.get("extra", {}).items():
            mm = V.fill_machine(bt)
            pos = g + 1 if mtp else 1
            de, se, se_hi = _v41_energy(cfg, scenario, V, E, ctx, mm.microbatch, pos, hbm_die_pj)
            ff = (g + 1) / tau * (1 + ovh) if mtp else 1.0
            pts[k] = dict(rate=rate, per_die=1 / ld, dyn={kk: vv * ff for kk, vv in de.items()}, stk=se * ff,
                          stk_hi=se_hi * ff, users=mm.microbatch, pos=pos, mtp=mtp, window=1, batch=bt, basis=f"aggregate tokens/s of the array, batch {bt}"
                                                   + (f", gamma {g}, tau {tau}" if mtp else ""))
        res = {}
        for k, p in pts.items():
            e_dyn = sum(p["dyn"].values())
            # the HOTTEST die (not the average over layer dies): its own ops at its die share, per emitted token,
            # over its stage window at batch 1 (window = stages: the average window, conservative for a heavy stage)
            wf = rt.get("windows", {}).get(k) if p["window"] > 1 else None
            if p["window"] > 1 and not wf:
                wf = {s: p["window"] for s in [str(i) for i in range(stages)] + ["head"]}
            hd = v41_hottest_die(cfg, scenario, V, E, ctx, p["users"], p["pos"], (g + 1) / tau if p["mtp"] else 1.0,
                                 ovh if p["mtp"] else 0.0, hbm_die_pj, window=wf, batch=p.get("batch", 1))
            hot_j = hd["hottest_j_per_token"] * hd["hottest_window_factor"]
            die_w = static_w + hot_j * p["rate"]
            avg_die_w = static_w + e_dyn * p["per_die"] * p["rate"]
            stk_die = p["stk_hi"] * p["per_die"] * hot_j / max(1e-30, e_dyn * p["per_die"])   # stacks scale with the die
            classes = _class_caps(cfg, n_pkg, static_w, hot_j, stk_die, p["rate"], logic_mm2)
            cap = {k: classes[V41_COOLING][k] for k in ("thermal_rate_limit", "capped_rate", "binds")}
            # whole-array energy per token: dynamic + stacks + the static of every die over the time a token
            # holds the array (idle dies' clock gated: leakage + HBM idle only; active dies clock too)
            active = min(dies, ld) if (k.startswith("sat") or k.startswith("fill")) else ld / stages
            idle_static = st["leakage_w"] + st["hbm_idle_w"]
            arr_static = (dies * idle_static + active * st["clock_w"] + links["array_w"]) / p["rate"]
            res[k] = dict(design_rate_tokens_s=p["rate"], basis=p["basis"],
                          array_dynamic_j_per_token=e_dyn, stack_j_per_token=p["stk"],
                          array_static_j_per_token=arr_static,
                          array_links_always_on_j_per_token=links["array_w"] / p["rate"],
                          energy_per_token_j=e_dyn + p["stk"] + arr_static,
                          die_components_j_per_token=p["dyn"],
                          hottest_die=hd["hottest"], hottest_die_components_j_per_token=hd["hottest_components_j_per_token"],
                          hottest_die_dynamic_j_per_token=hot_j,
                          hottest_over_layer_mean=hd["hottest_over_layer_mean"],
                          hottest_die_window_factor=hd["hottest_window_factor"],
                          die_dynamic_j_per_token_by_stage=hd["die_j_per_token"],
                          array_average_die_w=avg_die_w,
                          hottest_die_w=die_w, die_over_cooling=die_w / cool,
                          hottest_die_stacks_w=p["stk"] * p["per_die"] * p["rate"],
                          hottest_die_stacks_w_high=stk_die * p["rate"], batch=p.get("batch", 1),
                          cooling_classes=classes, **cap)
        out[str(ctx)] = res
    return dict(per_context=out, die_static_w=st, links_always_on=links, cooling_limit_w=cool, dies_per_package=n_pkg,
                layer_dies=ld, stages=stages, dies=dies, mtp_tau=tau, mtp_gamma=g,
                kv_in_hbm="every point charges the users' KV and index-key reads from attached HBM (die share "
                          "hbm_controller_phy_io + the stacks' share), as the HBM comparator does")


HBM_POINTS = (("ar_batch1", "b1"), ("mtp_batch1", "b1_mtp"), ("fill28", "fill28"), ("fill28_mtp", "fill28_mtp"),
              ("saturated_batch1024", "sat1024"), ("saturated_batch1024_mtp", "sat1024_mtp"))


def v41_hbm_comparator(cfg, scenario, hbm_die_pj=None):
    """The best switched HBM comparator (results/arch/v41_hbm_switched.json: 99 dies in 50 two-die packages, 4 HBM3E
    stacks per die, the headline NVL72-class fabric; each operating point at the tensor group G and lane multiplier
    that record picks for it) priced on the SAME power model as the ROM design point: the same workload and
    component list (tools/arch_budget_v41 token_workload), the same MAC, SRAM, stream and link energies and the same
    HBM path split for KV and index keys; the weights are read from the die's stacks instead of ROM.  The die is the
    ROM die with its ROM array re-spent on logic (iso total logic area): leakage and ungated clock over the whole
    non-SRAM area, 4 stacks idle, its fabric's always-on lanes and UCIe idle (v41_links_static).  Links are priced
    on the same collective bytes as the ROM array (tensor group 4),
    which favours the comparator (its G-way all-reduces cross the switch); switches and the wall chain are outside
    the boundary on both machines."""
    import arch_budget_v41 as V
    import decode_critical_path as D
    E = V._env()
    sw = json.loads(V41_SWITCHED.read_text())
    lad = json.loads(V41_LADDER.read_text())
    tau, g = lad["tau"], lad["gamma"]
    ovh = cfg["design_points"]["v41"]["mtp"]["draft_overhead"]
    dies = sw["dies"]
    stacks = cfg["design_points"]["v41"]["hbm_stacks_per_die"]
    n_pkg = 2
    ad = E["designs"][D.ARRAY_DESIGN]["area_split_per_device"]
    logic = ad["total_mm2"] - ad["sram_mm2"]
    ar = dict(logic=logic, clocked_logic=logic, rom=0.0, sram=ad["sram_mm2"])
    st = _die_static(cfg, ar, E["clock"], stacks)
    links = v41_links_static()["hbm"]
    assert links["dies"] == dies, "comparator die count differs between its record and its link charge"
    st["links_always_on_w"] = links["serdes_w_per_die"] + links["ucie_idle_w_per_die"]
    static_w = sum(st.values())
    cool = cooling_w(cfg, V41_COOLING, n_pkg)
    grid = {str(ctx): {r["G"]: r for r in cf["grid"]} for ctx, cf in sw["configs"][sw["headline_config"]].items()}
    out = {}
    for ctx, rows in sw["energy"].items():
        res = {}
        for key, sk in HBM_POINTS:
            h = rows[sk]["hbm"]
            G, mtp = h["G"], sk.endswith("_mtp")
            stages = grid[ctx][G]["stages"]
            bt = int(round(h["aggregate_tokens_s"] / h["tokens_s_per_user"]))
            users = max(1.0, bt / stages)                  # users sharing one weight pass (a stage's microbatch)
            pos = g + 1 if mtp else 1
            de, se, se_hi = _v41_energy(cfg, scenario, V, E, int(ctx), users, pos, hbm_die_pj, weights="hbm")
            ff = (g + 1) / tau * (1 + ovh) if mtp else 1.0
            dyn = {k: v * ff for k, v in de.items()}
            stk, stk_hi = se * ff, se_hi * ff
            rate = h["aggregate_tokens_s"]
            used = min(dies, G * stages)
            # batch 1: the token's stage holds it for T / stages on its G dies; filled: every used die is busy
            per_die = 1 / G if bt < stages else 1 / used
            active = G if bt < stages else used
            e_dyn = sum(dyn.values())
            die_w = static_w + e_dyn * per_die * rate
            classes = _class_caps(cfg, n_pkg, static_w, e_dyn * per_die, stk_hi * per_die, rate, logic)
            cap = {k: classes[V41_COOLING][k] for k in ("thermal_rate_limit", "capped_rate", "binds")}
            arr_static = (dies * (st["leakage_w"] + st["hbm_idle_w"]) + active * st["clock_w"] + links["array_w"]) / rate
            res[key] = dict(design_rate_tokens_s=rate, tokens_s_per_user=h["tokens_s_per_user"], batch=bt,
                            tensor_group=G, stages=stages, lane_mult=h.get("m"),
                            basis=("per user" if bt == 1 else "aggregate tokens/s of the machine")
                                  + (f", gamma {g}, tau {tau}" if mtp else ""),
                            array_dynamic_j_per_token=e_dyn, stack_j_per_token=stk, array_static_j_per_token=arr_static,
                            array_links_always_on_j_per_token=links["array_w"] / rate,
                            energy_per_token_j=e_dyn + stk + arr_static, die_components_j_per_token=dyn,
                            hottest_die_w=die_w, die_over_cooling=die_w / cool,
                            hottest_die_stacks_w=stk * per_die * rate, hottest_die_stacks_w_high=stk_hi * per_die * rate,
                            cooling_classes=classes, **cap)
        out[ctx] = res
    return dict(per_context=out, die_static_w=st, links_always_on=links, die_area_mm2=ar, cooling_limit_w=cool,
                dies_per_package=n_pkg,
                dies=dies, packages=math.ceil(dies / n_pkg), stacks_per_die=stacks, mtp_tau=tau, mtp_gamma=g,
                source=f"{V41_SWITCHED.relative_to(ROOT)} (headline fabric {sw['headline_config']}: rates, tensor "
                       "group, lane multiplier per point)")


def rom_over_hbm(rom, hbm):
    """Per context and operating point: ROM / HBM per-user and aggregate rate, and HBM / ROM energy per token, both
    machines from this record (ROM: the adopted design point; HBM: the best switched comparator)."""
    out = {}
    for ctx, pts in hbm["per_context"].items():
        out[ctx] = {}
        for k, h in pts.items():
            r = rom["per_context"].get(ctx, {}).get(k)
            if r is None:
                continue
            r_user = r["design_rate_tokens_s"] / (h["batch"] if h["batch"] > 1 else 1)
            out[ctx][k] = dict(rom_energy_j=r["energy_per_token_j"], hbm_energy_j=h["energy_per_token_j"],
                               energy_hbm_over_rom=h["energy_per_token_j"] / r["energy_per_token_j"],
                               rate_rom_over_hbm=r["design_rate_tokens_s"] / h["design_rate_tokens_s"],
                               rom_tokens_s_per_user=r_user, hbm_tokens_s_per_user=h["tokens_s_per_user"],
                               batch=h["batch"])
    return out


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build(cfg_path=CFG):
    cfg = load_cfg(cfg_path)
    hb = hbm_split(cfg)
    rec = dict(schema=SCHEMA, tool="tools/power_scenarios.py",
               inputs={str(p.relative_to(ROOT)): _sha(p) for p in (Path(cfg_path), V41_REC, V41_LANES, V41_LADDER,
                                                                    V41_SWITCHED, DFLASH_REC,
                                                                    ROOT / "configs/hardware/technology.json")},
               hbm_split_pj_per_bit=hb,
               mac_pj={s: dict(qwen3_w8=mac_pj(cfg, s, "qwen3", "fp8"), qwen3_bf16=mac_pj(cfg, s, "qwen3", "bf16"),
                               v41_fp4=mac_pj(cfg, s, "v41", "fp4"), v41_fp8=mac_pj(cfg, s, "v41", "fp8"),
                               v41_bf16=mac_pj(cfg, s, "v41", "bf16"), v41_fp32=mac_pj(cfg, s, "v41", "fp32"))
                       for s in SCENARIOS + ("B_gpu_tensor_sensitivity",)},
               scenarios={}, sensitivities={})
    for s in SCENARIOS:
        rec["scenarios"][s] = dict(qwen3_8b_rom_8k={k: qwen_point(cfg, s, k) for k in ("ar_batch1", "dflash")},
                                   deepseek_v41_rom_array=v41_points(cfg, s),
                                   deepseek_v41_design_point=v41_design_points(cfg, s),
                                   deepseek_v41_hbm_comparator=v41_hbm_comparator(cfg, s))
    rec["rom_over_hbm"] = {s: rom_over_hbm(rec["scenarios"][s]["deepseek_v41_design_point"],
                                           rec["scenarios"][s]["deepseek_v41_hbm_comparator"]) for s in SCENARIOS}
    # the lane no better than a shipping tensor core (A100 measured, control plane included)
    rec["sensitivities"]["B_lane_at_gpu_tensor_1p40pj"] = dict(
        qwen3_8b_rom_8k={k: qwen_point(cfg, "B_gpu_tensor_sensitivity", k) for k in ("ar_batch1", "dflash")},
        deepseek_v41_rom_array=v41_points(cfg, "B_gpu_tensor_sensitivity"))
    # the withdrawn allocation: only O'Connor's 0.8 pJ/bit I/O on the die, the rest on the stacks
    rec["sensitivities"]["B_old_hbm_allocation_die_0p8"] = dict(
        qwen3_8b_rom_8k={k: qwen_point(cfg, "B_proposed_production", k, hbm_die_pj=0.8) for k in ("ar_batch1", "dflash")},
        deepseek_v41_rom_array=v41_points(cfg, "B_proposed_production", hbm_die_pj=0.8))
    # the favourable end of the measured HBM paths: GH200 (HBM3) leaves 11.68 - 3.45 = 8.23 pJ/bit on the die
    gh = cfg["memory"]["hbm_path_total"]["measured_parts"]["gh200"] - hb["stack"]
    rec["sensitivities"]["B_hbm_die_gh200_8p23"] = dict(
        qwen3_8b_rom_8k={k: qwen_point(cfg, "B_proposed_production", k, hbm_die_pj=gh) for k in ("ar_batch1", "dflash")},
        deepseek_v41_rom_array=v41_points(cfg, "B_proposed_production", hbm_die_pj=gh))
    rec["cooling_limits_w"] = cooling_limits(cfg)
    rec["cooling_withdrawn"] = cfg["cooling"]["withdrawn"]
    rec["summary"] = summary(rec)
    return rec


def summary(rec):
    """One row per scenario x design point x cooling class."""
    rows = []

    def row(s, design, k, e_mj, die_w, r):
        for cls, c in r["cooling_classes"].items():
            rows.append(dict(scenario=s, design=design, point=k, cooling=cls, energy_per_token_mj=e_mj, die_w=die_w,
                             cooling_w=c["die_limit_w"], package_w=c["package_limit_w"], reference=c["reference"],
                             design_rate=r["design_rate_tokens_s"], capped_rate=c["capped_rate"], binds=c["binds"],
                             bound_by=c["bound_by"]))

    for s, body in list(rec["scenarios"].items()) + [(k, v) for k, v in rec["sensitivities"].items()]:
        for k, r in body["qwen3_8b_rom_8k"].items():
            row(s, "Qwen3-8B ROM 8K", k, r["energy_per_token_mj"], r["die_w_at_design_rate"], r)
        for ctx, pts in body["deepseek_v41_rom_array"]["per_context"].items():
            for k, r in pts.items():
                row(s, f"V4.1 ROM array {int(ctx):,}", k, r["energy_per_token_j"] * 1e3, r["hottest_die_w"], r)
        for ctx, pts in body.get("deepseek_v41_design_point", {}).get("per_context", {}).items():
            for k, r in pts.items():
                row(s, f"V4.1 design point {int(ctx):,}", k, r["energy_per_token_j"] * 1e3, r["hottest_die_w"], r)
        for ctx, pts in body.get("deepseek_v41_hbm_comparator", {}).get("per_context", {}).items():
            for k, r in pts.items():
                row(s, f"V4.1 HBM comparator {int(ctx):,}", k, r["energy_per_token_j"] * 1e3, r["hottest_die_w"], r)
    return rows


def _round(o):
    if isinstance(o, float):
        return float(f"{o:.6g}")
    if isinstance(o, dict):
        return {k: _round(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_round(v) for v in o]
    return o


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    rec = _round(build())
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    for r in rec["summary"]:
        print(f"{r['scenario'][:28]:28s} {r['design']:24s} {r['point']:20s} {r['cooling']:6s} {r['energy_per_token_mj']:8.2f} mJ "
              f"die {r['die_w']:7.1f} W / {r['cooling_w']:.0f} (pkg {r['package_w']:.0f})  rate {r['design_rate']:8.0f} -> "
              f"{r['capped_rate']:8.0f}{'  BINDS ' + r['bound_by'] if r['binds'] else ''}")


if __name__ == "__main__":
    main()
