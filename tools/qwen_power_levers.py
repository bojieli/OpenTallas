#!/usr/bin/env python3
"""Architectural levers against the batch-1 cooling cap of the Qwen3-8B ROM reticle, each a NAMED scenario.

    python3 tools/qwen_power_levers.py [--out results/arch/qwen_power_levers.json]

The baseline is tools/power_scenarios.py's Qwen3 point (configs/hardware/power_scenarios.json): at 8,910 tok/s
the die needs 636.6 W (scenario B) / 947.1 W (scenario A) against its 549.5 W air/liquid limit, so batch 1 caps at
7,442 / 4,689 tok/s (DFlash 11,925 / 4,731).  The die's share of the HBM path (10.19 pJ/bit on 604 MB of FP8 KV a
token) is 49.2 mJ of the 59.4 mJ of dynamic die energy a token (scenario B).

This tool re-prices that SAME point with one lever changed at a time (and a few stated combinations).  Every
lever input is read from configs/hardware/qwen_power_levers.json with its evidence class, boundary, source and
quote; every other input is the baseline's.  Nothing here changes the baseline record or the atlas: the record
lists, per lever, which published figures WOULD change if the lever were adopted.

The evaluator (`evaluate`) reproduces tools/power_scenarios.qwen_point exactly when no lever is set (checked at
build time and by tests/test_qwen_power_levers.py), and extends it with:

* resident KV: a part of the user's (target-layer) KV kept in an on-die SRAM instead of streamed from HBM.  The
  resident bytes skip the HBM path (die share and stack share) but pay a large-SRAM read at the conservative
  end, AND still pay the baseline's ring write/read/delivery (no credit for bypassing the ring); each step writes
  its new rows once.  The drafter's KV stays in HBM;
* an HBM die-share override (a fixed-function controller built from measured parts);
* area changes (lane copies traded for SRAM; a second die), priced through the baseline's leakage/clock model;
* a two-die package: layers split across two dies, each with 3 stacks, the KV striped over all 6 stacks so each
  die streams at the full 6-stack bandwidth during its stage (the per-user rate is otherwise halved), the half of
  the KV that crosses the die-to-die link charged at the link energy, and the hottest die charged half of the
  layer work plus ALL of the non-layer work (lm_head, the drafter) -- an upper bound for either die;
* a clock/voltage point (only from a sourced V/f table of the node: a vendor N6 OPP table, normalised to its top
  point): core dynamic energy and clock power scale with V^2, clock power with f, leakage unchanged (no credit), the HBM path unchanged (its I/O voltage is the
  stack's, not the core's), and the rate scales with f because the batch-1 step is compute-chain bound.

For each lever and scenario (A measured lane, B production lane) and cooling class (air, liquid) the record gives
the capped rate, whether the batch-1 per-user rate is kept (the lever's design rate within 1% of the baseline's,
i.e. the lever does not trade per-user rate for power), the area and silicon it costs and its weakest evidence class.
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

import power_scenarios as PS  # noqa: E402

CFG = ROOT / "configs/hardware/qwen_power_levers.json"
OUT = ROOT / "results/arch/qwen_power_levers.json"
DFLASH_BASIS = ROOT / "results/speculative/dflash_timing_basis.json"
DFLASH_ACCEPT = ROOT / "results/speculative/dflash_block_acceptance.json"
SCHEMA = "opentallas.qwen-power-levers.v1"
SCENARIOS = PS.SCENARIOS
KEYS = ("ar_batch1", "dflash")
RATE_KEPT = 0.99      # a lever keeps the batch-1 per-user rate if its design rate is within 1% of the baseline's
CLASS_RANK = {"measured-ours": 0, "published-measured": 1, "published-spec": 2, "assumed": 3}


def val(x):
    return x["value"] if isinstance(x, dict) else x


def load(cfg_path=CFG):
    return PS.load_cfg(), json.loads(Path(cfg_path).read_text())


# -- the DFlash operating point at another lane multiplier ---------------------------------------------------------
def dflash_point_m(qdp, m):
    """tools/power_scenarios.dflash_point at lane multiplier `m`, recomputed with tools/dflash_step_timing's own
    Machine and acceptance (the record only carries m = 1 and m = 3): the block with the most tokens/s."""
    import dflash_step_timing as DST
    basis = json.loads(DFLASH_BASIS.read_text())
    tau = DST.acceptance(json.loads(DFLASH_ACCEPT.read_text()))
    mc = DST.Machine(basis, qdp["context"], "fp8")
    best = None
    for B in DST.BLOCKS:
        if B not in tau:
            continue
        s = mc.serial_step(B, m)
        r = dict(block=B, tokens_per_step=tau[B]["direct"], step_cycles=round(s["cycles"]),
                 tokens_s=round(tau[B]["direct"] * mc.clock / s["cycles"], 1), **mc.step_macs(B, qdp["context"]))
        if best is None or r["tokens_s"] > best["tokens_s"]:
            best = r
    B = best["block"]
    return dict(qdp["dflash"], record_key=f"{qdp['context']}/fp8/m{m} (recomputed)", tau=best["tokens_per_step"],
                block=B, slots=B, tokens_per_step=best["tokens_per_step"], step_cycles=best["step_cycles"],
                record_tokens_s=best["tokens_s"], lane_copies_on=min(m, B) - 1, drafter=B > 1,
                **{k: best[k] for k in ("draft_weight_macs", "draft_attention_macs", "verify_weight_macs",
                                        "verify_attention_macs", "macs_per_step")})


# -- the evaluator -------------------------------------------------------------------------------------------------
def _areas(dp, copies_on, lever):
    """Areas of the HOTTEST die: the baseline's (tools/power_scenarios._qwen_areas) with the lever's changes."""
    a = dict(dp["area_mm2"])
    m = lever.get("lane_multiplier_m", a["lane_multiplier_m"])
    copies = a["lane_copy"] * (m - 1)
    phy = a["hbm_phy"] * lever.get("hbm_phy_scale", 1.0)
    logic = a["compute"] + a["interconnect"] + a["overhead"] + phy + a["stream_unit_spill"] + copies \
        + lever.get("extra_logic_mm2", 0.0)
    clocked = logic - copies * (1 - copies_on / max(1, m - 1))
    rom = a["rom"] * lever.get("rom_scale", 1.0) + a["drafter_rom"]
    sram = a["sram"] + lever.get("kv_sram_mm2", 0.0)
    return dict(logic=logic, clocked_logic=clocked, rom=rom, sram=sram, total=logic + rom + sram, lane_multiplier_m=m)


def evaluate(cfg, scenario, key, lever=None):
    """One Qwen3 ROM-reticle step (tools/power_scenarios.qwen_point) with `lever` applied.  lever keys:
    resident_kv_bytes (per user, target layers), resident_read_j_per_byte, resident_write_j_per_byte,
    hbm_die_pj, kv_bytes_per_elem, lane_multiplier_m, kv_sram_mm2, extra_logic_mm2, hbm_phy_scale, rom_scale,
    dies (1|2), hbm_stacks, link_j_per_bit, cross_die_kv_fraction, hop_bytes_per_slot (a slot's hidden state; the
    drafter's 5 taps with DFlash), hop_latency_s, hop_bytes_s, f_ratio, v_ratio.  Two dies: 2 hops a step (A->B
    and the token back), 4 with DFlash (the draft phase's taps cross too)."""
    import arch_budget_qwen3 as QB
    lever = lever or {}
    dp = cfg["design_points"]["qwen3"]
    if key == "dflash" and "lane_multiplier_m" in lever and lever["lane_multiplier_m"] != dp["area_mm2"]["lane_multiplier_m"]:
        pt = dflash_point_m(dp, lever["lane_multiplier_m"])
    else:
        pt = dp[key]
    f_ratio, v_ratio = lever.get("f_ratio", 1.0), lever.get("v_ratio", 1.0)
    v2 = v_ratio ** 2
    clock = dp["clock_hz"] * f_ratio
    wl = QB.workload(dp["context"])
    kvfmt = lever.get("kv_bytes_per_elem", dp["kv_format_bytes_per_elem"])
    kv_per_user = wl["bytes"]["kv_read"] * kvfmt / 2
    Q = QB.Q
    n = pt["users"] * pt["slots"]
    dr = pt["drafter"]
    dfrac = QB.DRAFTER_LAYERS / Q["L"] if dr else 0.0
    head = wl["macs"]["lm_head"]
    if dr:
        assert pt["verify_weight_macs"] == n * wl["weight_macs"] and pt["verify_attention_macs"] == n * wl["attention_macs"]
        extra_w, extra_a = n * head + pt["draft_weight_macs"], pt["draft_attention_macs"]
    else:
        extra_w, extra_a = n * head, 0
    layer_w, layer_a = n * (wl["weight_macs"] - head), n * wl["attention_macs"]
    kv_target = pt["users"] * kv_per_user
    kv_drafter = kv_target * dfrac
    resident = min(lever.get("resident_kv_bytes", 0.0) * pt["users"], kv_target)
    m_lanes = lever.get("lane_multiplier_m", dp["area_mm2"]["lane_multiplier_m"])
    sweeps = 1 if dr else math.ceil(n / m_lanes)
    wb_all = wl["bytes"]["weights_rom_format"]
    wb_head = head * 3.5 / 8
    d = cfg["die"]
    hb = PS.hbm_split(cfg)
    die_pj = lever.get("hbm_die_pj", hb["die"])
    stack_pj = hb["stack"]            # the stack's in-DRAM share is not the die's lever
    sram, dlv = val(d["sram_j_per_byte"]), val(d["operand_delivery_j_per_byte"])
    rd = lever.get("resident_read_j_per_byte", 0.0)
    wr = lever.get("resident_write_j_per_byte", rd)
    toks = pt["tokens_per_step"]
    rom_j = val(d["rom_read_j_per_byte"])
    new_rows = n * 2 * Q["L"] * Q["KV"] * Q["HD"] * kvfmt if resident else 0.0
    # joules per STEP, die-side dynamic, as (layer work, non-layer work: lm_head and the drafter)
    parts = dict(
        mac_weights=(layer_w, extra_w, PS.mac_pj(cfg, scenario, "qwen3", "w4a8") * 1e-12 * v2),
        mac_attention=(layer_a, extra_a, PS.mac_pj(cfg, scenario, "qwen3", "bf16") * 1e-12 * v2),
        weight_read_and_delivery=(sweeps * (wb_all - wb_head),
                                  sweeps * wb_head + (QB.DRAFTER_PARAMS * 3.5 / 8 if dr else 0), (rom_j + dlv) * v2),
        kv_ring_sram_and_delivery=(kv_target, kv_drafter, (2 * sram + dlv) * v2),
        stream_unit=(n * wl["elementwise_total"], n * wl["elementwise_total"] * dfrac,
                     (val(d["stream_fp32_op_j"]) + 12 * sram) * v2),
        hbm_controller_phy_io=(kv_target - resident, kv_drafter, 8 * die_pj * 1e-12),
    )
    if resident:
        parts["kv_resident_sram_read"] = (resident, 0.0, rd * v2)
        parts["kv_resident_sram_write"] = (new_rows, 0.0, wr * v2)
    dies = lever.get("dies", 1)
    if dies == 2:
        hop_bits = (4 if dr else 2) * n * lever.get("hop_bytes_per_slot", 0.0) * (QB.DRAFTER_LAYERS if dr else 1) * 8
        parts["die_to_die_link"] = (lever.get("cross_die_kv_fraction", 0.0) * (kv_target - resident) * 8, hop_bits,
                                    lever["link_j_per_bit"])
    dyn = {k: (a + b) * e for k, (a, b, e) in parts.items()}
    hot_share = 0.5 if dies == 2 else 1.0
    dyn_hot = {k: (hot_share * a + b) * e for k, (a, b, e) in parts.items()}
    stacks = lever.get("hbm_stacks", dp["hbm_stacks"])            # stacks on the hottest die
    ar = _areas(dp, pt["lane_copies_on"], lever)
    st = PS._die_static(cfg, ar, clock, stacks)
    st["clock_w"] *= v2
    static_w = sum(st.values())
    hops = (4 if dr else 2) if dies == 2 else 0
    hop_bytes = n * lever.get("hop_bytes_per_slot", 0.0) * (QB.DRAFTER_LAYERS if dr else 1)
    hop_s = hops * (lever.get("hop_latency_s", 0.0) + hop_bytes / lever.get("hop_bytes_s", float("inf")))
    step_cycles = pt["step_cycles"]
    if dies == 2 and lever.get("cross_die_kv_fraction", 0.0) == 0.0:
        # each die streams its layers' KV from its own 3 stacks only: the step's KV stream time doubles, so the step
        # is at least twice the KV stream (target + drafter) -- a LOWER bound on the loss
        step_cycles = max(step_cycles, 2 * kv_stream_cycles(cfg) * (1 + dfrac) * (1 - resident / kv_target))
    t = step_cycles / clock + hop_s
    rate = toks / t
    dyn_tok = sum(dyn.values()) / toks
    dyn_hot_tok = sum(dyn_hot.values()) / toks
    hbm_bytes = kv_target - resident + kv_drafter
    stack_tok = hbm_bytes * 8 * stack_pj * 1e-12 / toks
    stack_hi_tok = hbm_bytes * 8 * hb["stack_high"] * 1e-12 / toks
    stk_hi_per_die = stack_hi_tok / dies
    classes = PS._class_caps(cfg, dies, static_w, dyn_hot_tok, stk_hi_per_die, rate, ar["logic"])
    die_w = static_w + dyn_hot_tok * rate
    comp = {k: v / toks * 1e3 for k, v in dyn.items()}
    comp.update({k.replace("_w", ""): v * dies / rate * 1e3 for k, v in st.items()})
    return dict(design_rate_tokens_s=rate, step_cycles=step_cycles, tokens_per_step=toks, block=pt.get("block", 1),
                clock_hz=clock, dies=dies, hop_s_per_step=hop_s,
                energy_per_token_mj=(dyn_tok + dies * static_w / rate + stack_tok) * 1e3,
                die_energy_per_token_mj=(dyn_tok + dies * static_w / rate) * 1e3,
                die_dynamic_mj_per_token=dyn_tok * 1e3, hottest_die_dynamic_mj_per_token=dyn_hot_tok * 1e3,
                stack_energy_per_token_mj=stack_tok * 1e3,
                die_components_mj_per_token=comp, die_static_w=st, die_w_at_design_rate=die_w,
                stacks_w_high=stack_hi_tok * rate, resident_kv_bytes_per_user=resident / pt["users"],
                resident_kv_fraction=resident / kv_target, hbm_kv_bytes_per_step=hbm_bytes, areas_hottest_die_mm2=ar,
                cooling_classes=classes,
                capped_rate=classes["air"]["capped_rate"], binds=classes["air"]["binds"])


def kv_stream_cycles(cfg):
    """The 6-stack KV stream of one token at the design context (results/speculative/dflash_timing_basis.json
    rom_token, FP8): 122,881 cycles at 8K."""
    dp = cfg["design_points"]["qwen3"]
    b = json.loads(DFLASH_BASIS.read_text())
    return b["rom_token"][f"{dp['context']}/fp8"]["kv_stream_cycles"]


def kv_split(cfg, scenario, key):
    """Where the baseline's die energy goes, as fractions: KV streaming (HBM die share + ring), weights (weight MACs
    + ROM read/delivery), attention MACs, control (stream unit), static (leakage, clock, stack idle)."""
    r = evaluate(cfg, scenario, key)
    c = r["die_components_mj_per_token"]
    groups = dict(kv_streaming=c["hbm_controller_phy_io"] + c["kv_ring_sram_and_delivery"],
                  weights=c["mac_weights"] + c["weight_read_and_delivery"], attention_macs=c["mac_attention"],
                  stream_unit=c["stream_unit"], static=c["leakage"] + c["clock"] + c["hbm_idle"])
    tot = sum(groups.values())
    assert abs(tot - r["die_energy_per_token_mj"]) < 1e-9 * tot
    return dict(die_mj_per_token=tot, mj=groups, fraction={k: v / tot for k, v in groups.items()},
                stack_mj_per_token=r["stack_energy_per_token_mj"])


def resident_needed(cfg, scenario, key, lever_base, target_rate, cls="air"):
    """Resident KV bytes a user needs for the die to reach `target_rate` in class `cls` (bisection over bytes), or
    None if even the whole KV on die does not."""
    import arch_budget_qwen3 as QB
    dp = cfg["design_points"]["qwen3"]
    kv = QB.workload(dp["context"])["bytes"]["kv_read"] * dp["kv_format_bytes_per_elem"] / 2

    def ok(b):
        r = evaluate(cfg, scenario, key, dict(lever_base, resident_kv_bytes=b))
        return r["cooling_classes"][cls]["capped_rate"] >= min(target_rate, r["design_rate_tokens_s"]) * (1 - 1e-9)
    if ok(0):
        return 0.0
    if not ok(kv):
        return None
    lo, hi = 0.0, kv
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if ok(mid) else (mid, hi)
    return hi


# -- the levers ----------------------------------------------------------------------------------------------------
def _sram_bytes(L, mm2):
    return mm2 * val(L["sram"]["density_bytes_per_mm2"])


def levers(cfg, L):
    """{name: dict(lever=..., meta=...)}: every lever as a named scenario, inputs from the lever config."""
    dp = cfg["design_points"]["qwen3"]
    a = dp["area_mm2"]
    used = sum(a[k] for k in ("compute", "interconnect", "overhead", "hbm_phy", "stream_unit_spill", "rom",
                              "drafter_rom", "sram")) + a["lane_copy"] * (a["lane_multiplier_m"] - 1)
    slack = cfg["cooling"]["die_mm2"] - used
    S = L["sram"]
    rd = val(S["resident_read_j_per_byte"])
    out = {}

    def kv_lever(name, mm2, m, what, extra=None):
        lv = dict(kv_sram_mm2=mm2, resident_kv_bytes=_sram_bytes(L, mm2), resident_read_j_per_byte=rd,
                  lane_multiplier_m=m, **(extra or {}))
        out[name] = dict(lever=lv, meta=dict(
            family="1 KV window on die", what=what, area_mm2_added=0.0, kv_sram_mm2=mm2,
            lane_copies_removed=a["lane_multiplier_m"] - m, silicon_mm2=cfg["cooling"]["die_mm2"], dies=1, evidence=[S["density_bytes_per_mm2"], S["resident_read_j_per_byte"]]))

    kv_lever("kv_sram_in_slack", slack, a["lane_multiplier_m"],
             f"the reticle's {slack:.1f} mm2 of slack filled with SRAM holding the user's most recent KV rows")
    kv_lever("kv_sram_for_one_lane_copy", slack + a["lane_copy"], 2,
             "one of the two lane copies (69.2 mm2, idle at autoregressive batch 1) plus the slack re-spent on a KV "
             "SRAM; lane multiplier 3 -> 2 (DFlash re-timed at m = 2)")
    kv_lever("kv_sram_for_both_lane_copies", slack + 2 * a["lane_copy"], 1,
             "both lane copies (138.4 mm2) plus the slack re-spent on a KV SRAM; lane multiplier 3 -> 1, so "
             "DFlash degenerates to plain decoding (its best block at m = 1 is 1)")
    # 4-bit KV: a SENSITIVITY only (user rule), not a lever
    out["sensitivity_kv_int4"] = dict(lever=dict(kv_bytes_per_elem=0.5), meta=dict(
        family="sensitivity", what="4-bit KV (0.5 B an element): SENSITIVITY ONLY -- FP8 KV is the design point "
        "(user rule); a golden change with an unmeasured accuracy cost", area_mm2_added=0.0,
        silicon_mm2=cfg["cooling"]["die_mm2"], dies=1, evidence=[]))
    # fixed-function streaming controller: measured PHY + sourced controller logic estimate
    C = L["hbm_controller"]
    if C.get("scenario_die_pj_per_bit") is not None:
        out["fixed_function_streaming_controller"] = dict(
            lever=dict(hbm_die_pj=val(C["scenario_die_pj_per_bit"])),
            meta=dict(family="2 controller/PHY energy", what=C["scenario_die_pj_per_bit"]["boundary"],
                      area_mm2_added=0.0, silicon_mm2=cfg["cooling"]["die_mm2"], dies=1,
                      evidence=[C[k] for k in C["scenario_parts"]]))
    # two-die package
    T = L["two_die"]
    link = val(T["link_j_per_bit"])
    kvb = PS_kv_bytes(cfg)
    two = dict(dies=2, hbm_stacks=3, hbm_phy_scale=0.5, rom_scale=0.5, extra_logic_mm2=val(T["d2d_phy_mm2"]),
               link_j_per_bit=link, cross_die_kv_fraction=0.5, hop_bytes_per_slot=val(T["hop_bytes_per_slot"]),
               hop_latency_s=val(T["hop_latency_s"]), hop_bytes_s=val(T["d2d_bytes_s"]))
    hot_area = _areas(dp, 0, two)["total"]
    out["two_die_striped_kv"] = dict(lever=two, meta=dict(
        family="3 two-die package", what="36 layers split 18/18 over two dies in one package, 3 HBM3E stacks each, "
        "the KV striped over all 6 stacks (half of each die's KV crosses the die-to-die link), each die a full lane "
        "array; hottest die = half the layer work + all lm_head and drafter work",
        area_mm2_added=hot_area * 2 - cfg["cooling"]["die_mm2"], silicon_mm2=2 * hot_area, dies=2,
        hottest_die_mm2=hot_area, evidence=[T[k] for k in ("link_j_per_bit", "d2d_phy_mm2", "hop_latency_s", "d2d_bytes_s", "hop_bytes_per_slot")],
        d2d_bandwidth_needed_bytes_s=0.5 * kvb / 2 / (dp["ar_batch1"]["step_cycles"] / dp["clock_hz"] / 2)))
    free = cfg["cooling"]["die_mm2"] - hot_area
    two_sram = dict(two, kv_sram_mm2=free, resident_read_j_per_byte=rd,
                    resident_kv_bytes=2 * min(_sram_bytes(L, free), kvb / 2))
    out["two_die_striped_kv_plus_kv_sram"] = dict(lever=two_sram, meta=dict(
        family="3 two-die package + 1 KV on die",
        what=f"two_die_striped_kv with each die grown to the reticle ({free:.1f} mm2 of SRAM a die) holding the "
        "user's KV rows of its own layers; the rest striped over the 6 stacks",
        area_mm2_added=2 * cfg["cooling"]["die_mm2"] - cfg["cooling"]["die_mm2"],
        silicon_mm2=2 * cfg["cooling"]["die_mm2"], dies=2, hottest_die_mm2=cfg["cooling"]["die_mm2"],
        evidence=[T[k] for k in ("link_j_per_bit", "d2d_phy_mm2", "hop_latency_s", "d2d_bytes_s", "hop_bytes_per_slot")] + [S["density_bytes_per_mm2"], S["resident_read_j_per_byte"]]))
    out["two_die_unstriped_kv"] = dict(lever=dict(two, cross_die_kv_fraction=0.0), meta=dict(
        family="3 two-die package", what="as two_die_striped_kv but each die reads only its own 3 stacks: its stage "
        "streams its layers' KV at half the bandwidth, so the step's KV time doubles (the per-user rate is halved "
        "at 8K, where the step is KV-bound as much as compute-bound)", area_mm2_added=hot_area * 2 - 815.0,
        silicon_mm2=2 * hot_area, dies=2, hottest_die_mm2=hot_area, evidence=[T["link_j_per_bit"], T["hop_bytes_per_slot"]],
        rate_note="design rate halved: see per_user_rate_kept"))
    # clock/voltage
    for p in dvfs_points(L):
        if p["hz"] not in L["dvfs"]["levers_at_hz"]:
            continue
        out[f"dvfs_f{p['f_ratio']:.3f}"] = dict(lever=dict(f_ratio=p["f_ratio"], v_ratio=p["v_ratio"]), meta=dict(
            family="4 clock/voltage", what=f"core clock x{p['f_ratio']:.3f} at core supply x{p['v_ratio']:.3f} (the "
            f"{p['hz'] / 1e6:.0f} MHz / {p['uv'] / 1e6:.4f} V point of the N6 OPP table over its top point)",
            area_mm2_added=0.0, silicon_mm2=cfg["cooling"]["die_mm2"], dies=1, evidence=[L["dvfs"]["curve"]]))
    return out


def dvfs_points(L):
    """The sourced V/f table normalised to its top point: our 1.0986 GHz is taken to be the table's top (0.75 V)."""
    tab = L["dvfs"]["curve"]["table_hz_uv"]
    hz0, uv0 = max(tab)
    return [dict(hz=h, uv=u, f_ratio=h / hz0, v_ratio=u / uv0) for h, u in sorted(tab, reverse=True)]


def dvfs_sweep(cfg, L):
    """Every point of the table: design rate and capped rate per scenario and class (the best is the lever)."""
    rows = []
    for p in dvfs_points(L):
        row = dict(p)
        for s in SCENARIOS:
            for k in KEYS:
                r = evaluate(cfg, s, k, dict(f_ratio=p["f_ratio"], v_ratio=p["v_ratio"]))
                row[f"{s[0]}/{k}"] = dict(design=r["design_rate_tokens_s"],
                                          air=r["cooling_classes"]["air"]["capped_rate"],
                                          liquid=r["cooling_classes"]["liquid"]["capped_rate"])
        rows.append(row)
    best = {f"{s[0]}/{k}": max(rows, key=lambda x: x[f"{s[0]}/{k}"]["air"]) for s in SCENARIOS for k in KEYS}
    return dict(rows=rows, best_air={kk: dict(hz=v["hz"], f_ratio=v["f_ratio"], v_ratio=v["v_ratio"], **v[kk])
                                     for kk, v in best.items()})


def PS_kv_bytes(cfg):
    import arch_budget_qwen3 as QB
    dp = cfg["design_points"]["qwen3"]
    return QB.workload(dp["context"])["bytes"]["kv_read"] * dp["kv_format_bytes_per_elem"] / 2


def _weakest(evs):
    cls = [e["evidence_class"] for e in evs if isinstance(e, dict) and "evidence_class" in e]
    return max(cls, key=CLASS_RANK.get) if cls else "baseline inputs only"


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build(cfg_path=CFG):
    cfg, L = load(cfg_path)
    base = {s: {k: evaluate(cfg, s, k) for k in KEYS} for s in SCENARIOS}
    # the evaluator IS the baseline model when no lever is set
    for s in SCENARIOS:
        for k in KEYS:
            ref = PS.qwen_point(cfg, s, k)
            for f in ("energy_per_token_mj", "die_w_at_design_rate", "capped_rate", "design_rate_tokens_s"):
                assert abs(ref[f] - base[s][k][f]) <= 1e-9 * abs(ref[f]), (s, k, f, ref[f], base[s][k][f])
    rec = dict(schema=SCHEMA, tool="tools/qwen_power_levers.py",
               inputs={str(Path(p).relative_to(ROOT)): _sha(p) for p in (cfg_path, PS.CFG, PS.DFLASH_REC, DFLASH_BASIS,
                                                                         DFLASH_ACCEPT)},
               target_tokens_s=L["target_tokens_s"],
               baseline={s: {k: _row(base[s][k]) for k in KEYS} for s in SCENARIOS},
               energy_split_batch1={s: {k: kv_split(cfg, s, k) for k in KEYS} for s in SCENARIOS},
               levers={}, not_evaluated=L.get("not_evaluated", {}))
    for name, spec in levers(cfg, L).items():
        lv, meta = spec["lever"], spec["meta"]
        res = {}
        for s in SCENARIOS:
            res[s] = {}
            for k in KEYS:
                r = evaluate(cfg, s, k, lv)
                row = _row(r)
                b = base[s][k]
                row["design_rate_over_baseline"] = r["design_rate_tokens_s"] / b["design_rate_tokens_s"]
                row["per_user_rate_kept"] = row["design_rate_over_baseline"] >= RATE_KEPT
                row["capped_gain_over_baseline_air"] = r["cooling_classes"]["air"]["capped_rate"] / b["capped_rate"]
                row["reaches_target_air"] = r["cooling_classes"]["air"]["capped_rate"] >= L["target_tokens_s"] * (1 - 1e-9)
                row["reaches_target_liquid"] = r["cooling_classes"]["liquid"]["capped_rate"] >= L["target_tokens_s"] * (1 - 1e-9)
                res[s][k] = row
        meta = dict(meta, weakest_evidence_class=_weakest(meta.pop("evidence")))
        rec["levers"][name] = dict(meta, lever_inputs=lv, result=res,
                                   atlas_figures_if_adopted=L["atlas_figures_if_adopted"][meta["family"].split()[0]])
    # how much on-die KV the single reticle would need to reach the target (for scale against the slack)
    rec["resident_kv_needed_for_target"] = {}
    for s in SCENARIOS:
        for cls in ("air", "liquid"):
            b = resident_needed(cfg, s, "ar_batch1", dict(resident_read_j_per_byte=val(L["sram"]["resident_read_j_per_byte"])),
                                L["target_tokens_s"], cls)
            rec["resident_kv_needed_for_target"][f"{s}/{cls}"] = None if b is None else dict(
                bytes=b, fraction_of_kv=b / PS_kv_bytes(cfg),
                sram_mm2=b / val(L["sram"]["density_bytes_per_mm2"]),
                note="SRAM area at the lever config's density, before any leakage/clock of the new area (lower bound "
                     "on the area)")
    rec["dflash_kv_amortisation"] = dflash_amortisation(cfg, base)
    rec["dvfs_sweep"] = dvfs_sweep(cfg, L)
    rec["hbm_die_share_needed_for_target"] = die_share_needed(cfg, L["target_tokens_s"])
    rec["summary"] = summary(rec)
    return rec


def die_share_needed(cfg, target):
    """Lever 2 as a REQUIREMENT (no measured PHY/controller exists to build it from): the HBM die share in pJ/bit
    at which each point reaches min(target, its design rate) in air, by bisection; None if even 0 does not."""
    out = {}
    for s in SCENARIOS:
        for k in KEYS:
            def ok(pj):
                r = evaluate(cfg, s, k, dict(hbm_die_pj=pj))
                return r["cooling_classes"]["air"]["capped_rate"] >= min(target, r["design_rate_tokens_s"]) * (1 - 1e-9)
            base = PS.hbm_split(cfg)["die"]
            if ok(base):
                out[f"{s}/{k}"] = dict(pj_per_bit=base, note="already reaches the target")
                continue
            if not ok(0.0):
                out[f"{s}/{k}"] = None
                continue
            lo, hi = 0.0, base
            for _ in range(60):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if ok(mid) else (lo, mid)
            out[f"{s}/{k}"] = dict(pj_per_bit=lo, reduction_pj_per_bit=base - lo,
                                   reference=dict(baseline_mi250x=base, gh200_hbm3=8.23, oconnor_io_floor=0.8))
    return out


def dflash_amortisation(cfg, base):
    """Lever 5: the KV bytes per EMITTED token with DFlash (one target KV sweep + the drafter's per step, over the
    measured tokens a step) against autoregressive decoding."""
    import arch_budget_qwen3 as QB
    dp = cfg["design_points"]["qwen3"]
    kv = PS_kv_bytes(cfg)
    df = dp["dflash"]
    per_step = kv * (1 + QB.DRAFTER_LAYERS / QB.Q["L"])
    out = dict(block=df["block"], tokens_per_step=df["tokens_per_step"], kv_bytes_per_token_ar=kv,
               kv_bytes_per_step_dflash=per_step, kv_bytes_per_token_dflash=per_step / df["tokens_per_step"],
               ratio_dflash_over_ar=per_step / df["tokens_per_step"] / kv)
    for s in SCENARIOS:
        a, d = base[s]["ar_batch1"], base[s]["dflash"]
        out[s] = dict(hbm_die_mj_per_token_ar=a["die_components_mj_per_token"]["hbm_controller_phy_io"],
                      hbm_die_mj_per_token_dflash=d["die_components_mj_per_token"]["hbm_controller_phy_io"],
                      mac_mj_per_token_ar=a["die_components_mj_per_token"]["mac_weights"]
                      + a["die_components_mj_per_token"]["mac_attention"],
                      mac_mj_per_token_dflash=d["die_components_mj_per_token"]["mac_weights"]
                      + d["die_components_mj_per_token"]["mac_attention"],
                      capped_ar=a["capped_rate"], capped_dflash=d["capped_rate"])
    return out


def _row(r):
    keep = ("design_rate_tokens_s", "clock_hz", "dies", "block", "tokens_per_step", "step_cycles", "hop_s_per_step",
            "energy_per_token_mj", "die_energy_per_token_mj", "die_dynamic_mj_per_token",
            "hottest_die_dynamic_mj_per_token", "stack_energy_per_token_mj", "die_components_mj_per_token",
            "die_static_w", "die_w_at_design_rate", "stacks_w_high", "resident_kv_bytes_per_user",
            "resident_kv_fraction", "hbm_kv_bytes_per_step", "areas_hottest_die_mm2")
    out = {k: r[k] for k in keep}
    out["cooling_classes"] = {c: {k: v for k, v in x.items() if k in (
        "reference", "die_limit_w", "package_limit_w", "dies_per_package", "thermal_rate_limit", "capped_rate", "binds",
        "bound_by", "die_w_at_cap", "package_w_at_cap")} for c, x in r["cooling_classes"].items()}
    out["capped_rate"] = r["capped_rate"]
    return out


def summary(rec):
    rows = []
    for s in SCENARIOS:
        for k in KEYS:
            b = rec["baseline"][s][k]
            rows.append(dict(lever="baseline", scenario=s, point=k, design_rate=b["design_rate_tokens_s"],
                             air=b["cooling_classes"]["air"]["capped_rate"],
                             liquid=b["cooling_classes"]["liquid"]["capped_rate"], per_user_rate_kept=True,
                             silicon_mm2=815.0, evidence="baseline"))
    for name, lv in rec["levers"].items():
        for s in SCENARIOS:
            for k in KEYS:
                r = lv["result"][s][k]
                rows.append(dict(lever=name, scenario=s, point=k, design_rate=r["design_rate_tokens_s"],
                                 air=r["cooling_classes"]["air"]["capped_rate"],
                                 liquid=r["cooling_classes"]["liquid"]["capped_rate"],
                                 per_user_rate_kept=r["per_user_rate_kept"], silicon_mm2=lv["silicon_mm2"],
                                 evidence=lv["weakest_evidence_class"]))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    rec = PS._round(build())
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    for r in rec["summary"]:
        print(f"{r['lever']:36s} {r['scenario'][:1]} {r['point']:9s} design {r['design_rate']:8.0f}  air {r['air']:8.0f}"
              f"  liquid {r['liquid']:8.0f}  rate kept {str(r['per_user_rate_kept']):5s} {r['silicon_mm2']:7.1f} mm2 "
              f"[{r['evidence']}]")


if __name__ == "__main__":
    main()
