#!/usr/bin/env python3
"""Architectural levers against the batch-1 cooling cap of the Qwen3-8B ROM package, each a NAMED scenario.

    python3 tools/qwen_power_levers.py [--out results/arch/qwen_power_levers.json]

The baseline is tools/power_scenarios.py's Qwen3 point (configs/hardware/power_scenarios.json design_points.qwen3):
the O4 package of results/arch/qwen3_8bit_design.json -- two reticles over UCIe, every layer split across both dies
(tensor-parallel 2), INT8 weight-only weights with per-output-channel BF16 scales, 8 HBM3E stacks (4 a die) holding
the users' FP8 KV, 6,144 MAC groups a die, lane multiplier 5.  Both dies carry the same work, so each dissipates half
of the package's die-side power and is checked against the per-die limit of the two-die cooling class (B200 HGX air,
GB200 liquid).  The record's `baseline` block restates that point (design rate, energy per token, per-die watts,
capped rates) from the evaluator, which reproduces tools/power_scenarios.qwen_point exactly; no baseline figure is
restated in this file.

This tool re-prices that SAME point with one lever changed at a time.  Every lever input is read from
configs/hardware/qwen_power_levers.json with its evidence class, boundary, source and quote; every other input is
the baseline's.  Nothing here changes the baseline record or the atlas: the record lists, per lever, which published
figures WOULD change if the lever were adopted.  Every lever is stated for the PACKAGE, both dies alike (the split is
symmetric): an area a die counts twice, and the limit is the two-die class's per-die limit.

The evaluator (`evaluate`) reproduces tools/power_scenarios.qwen_point exactly when no lever is set (checked at
build time and by tests/test_qwen_power_levers.py) -- package static (leakage, clock and stack idle over the package
areas, UCIe PHY included), package dynamic energy including the tensor-parallel UCIe exchanges, weight bytes at the
design point's weight bits plus the swept scales, the weight MAC lane of the design point, per-die power = package /
dies -- and extends it with:

* resident KV: a part of the user's (target-layer) KV kept in an on-die SRAM instead of streamed from HBM, each die
  holding the rows of its own KV heads.  The resident bytes skip the HBM path (die share and stack share) but pay a
  large-SRAM read at the conservative end, AND still pay the baseline's ring write/read/delivery (no credit for
  bypassing the ring); each step writes its new rows once.  The drafter's KV stays in HBM;
* an HBM die-share override (a fixed-function controller built from measured parts: none exists, so the record
  carries it only as a requirement, hbm_die_share_needed_for_target);
* area changes (lane copies traded for SRAM), priced through the baseline's leakage/clock model; the DFlash point at
  another lane multiplier is re-timed on the package's own basis (tools/arch_budget_qwen3.timing_basis via
  tools/dflash_step_timing.design_basis), never on the legacy single-reticle results/speculative/dflash_timing_basis.json;
* a clock/voltage point (only from a sourced V/f table of the node: a vendor N6 OPP table, normalised to its top
  point): core dynamic energy and clock power scale with V^2, clock power with f, leakage unchanged (no credit), the
  HBM path and the UCIe link unchanged (their I/O supplies are not the core rail), and the rate scales with f
  because the batch-1 step is compute-chain bound (the record's dvfs_sweep.basis gives the chain and KV stream).

The superseded single-reticle study's family 3 (a two-die package) IS the baseline now; it is not a lever, and the
record's superseded_levers says so.

For each lever and scenario (A measured lane, B production lane) and cooling class (air, liquid) the record gives
the capped rate, whether the batch-1 per-user rate is kept (the lever's design rate within 1% of the baseline's,
i.e. the lever does not trade per-user rate for power), the area and silicon it costs and its weakest evidence class.
"""
from __future__ import annotations

import argparse
import functools
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
DFLASH_ACCEPT = ROOT / "results/speculative/dflash_block_acceptance.json"
SCHEMA = "opentallas.qwen-power-levers.v2"
SCENARIOS = PS.SCENARIOS
KEYS = ("ar_batch1", "dflash")
RATE_KEPT = 0.99      # a lever keeps the batch-1 per-user rate if its design rate is within 1% of the baseline's
CLASS_RANK = {"measured-ours": 0, "published-measured": 1, "published-spec": 2, "assumed": 3}


def val(x):
    return x["value"] if isinstance(x, dict) else x


def load(cfg_path=CFG):
    return PS.load_cfg(), json.loads(Path(cfg_path).read_text())


@functools.lru_cache(maxsize=None)
def _basis_json():
    import dflash_step_timing as DST
    return json.dumps(DST.design_basis(), default=float)


def timing_basis():
    """The package's timing basis (tools/dflash_step_timing.design_basis = tools/arch_budget_qwen3.timing_basis)."""
    return json.loads(_basis_json())


# -- the DFlash operating point at another lane multiplier ---------------------------------------------------------
@functools.lru_cache(maxsize=None)
def _dflash_best(context, clock_hz, m):
    import dflash_step_timing as DST
    basis = timing_basis()
    assert basis["clock_hz"] == clock_hz, "timing basis and design point clocks differ"
    tau = DST.acceptance(json.loads(DFLASH_ACCEPT.read_text()))
    mc = DST.Machine(basis, context, "fp8")
    best = None
    for B in DST.BLOCKS:
        if B not in tau:
            continue
        s = mc.serial_step(B, m)
        r = dict(block=B, tokens_per_step=tau[B]["direct"], step_cycles=round(s["cycles"]),
                 tokens_s=round(tau[B]["direct"] * mc.clock / s["cycles"], 1), **mc.step_macs(B, context))
        if best is None or r["tokens_s"] > best["tokens_s"]:
            best = r
    return json.dumps(best)


def dflash_point_m(qdp, m):
    """tools/power_scenarios.dflash_point at lane multiplier `m`, recomputed with tools/dflash_step_timing's own
    Machine and acceptance on the PACKAGE's timing basis (the record carries only m = 1 and the design m): the block
    with the most tokens/s."""
    best = json.loads(_dflash_best(qdp["context"], qdp["clock_hz"], m))
    B = best["block"]
    return dict(qdp["dflash"], record_key=f"{qdp['context']}/fp8/m{m} (recomputed)", tau=best["tokens_per_step"],
                block=B, slots=B, tokens_per_step=best["tokens_per_step"], step_cycles=best["step_cycles"],
                record_tokens_s=best["tokens_s"], lane_copies_on=min(m, B) - 1, drafter=B > 1,
                **{k: best[k] for k in ("draft_weight_macs", "draft_attention_macs", "verify_weight_macs",
                                        "verify_attention_macs", "macs_per_step")})


# -- the evaluator -------------------------------------------------------------------------------------------------
def _areas(dp, copies_on, lever):
    """PACKAGE areas (tools/power_scenarios._qwen_areas: area_mm2 holds package totals) with the lever's changes."""
    a = dp["area_mm2"]
    m = lever.get("lane_multiplier_m", a["lane_multiplier_m"])
    copies = a["lane_copy"] * (m - 1)
    logic = a["compute"] + a["interconnect"] + a["overhead"] + a["hbm_phy"] + a.get("ucie_phy", 0.0) + \
        a["stream_unit_spill"] + copies
    clocked = logic - copies * (1 - copies_on / max(1, m - 1))
    rom = a["rom"] + a["drafter_rom"]
    sram = a["sram"] + lever.get("kv_sram_mm2", 0.0)
    n = dp["dies_per_package"]
    return dict(logic=logic, clocked_logic=clocked, rom=rom, sram=sram, total=logic + rom + sram,
                total_per_die=(logic + rom + sram) / n, lane_multiplier_m=m)


def evaluate(cfg, scenario, key, lever=None):
    """One Qwen3 ROM-package step (tools/power_scenarios.qwen_point) with `lever` applied.  lever keys (all per
    PACKAGE): resident_kv_bytes (per user, target layers, both dies), resident_read_j_per_byte,
    resident_write_j_per_byte, hbm_die_pj, kv_bytes_per_elem, lane_multiplier_m, kv_sram_mm2, f_ratio, v_ratio."""
    import arch_budget_qwen3 as QB
    lever = lever or {}
    dp = cfg["design_points"]["qwen3"]
    m0 = dp["area_mm2"]["lane_multiplier_m"]
    m_lanes = lever.get("lane_multiplier_m", m0)
    pt = dflash_point_m(dp, m_lanes) if key == "dflash" and m_lanes != m0 else dp[key]
    f_ratio, v_ratio = lever.get("f_ratio", 1.0), lever.get("v_ratio", 1.0)
    v2 = v_ratio ** 2
    clock = dp["clock_hz"] * f_ratio
    wl = QB.workload(dp["context"])
    kvfmt = lever.get("kv_bytes_per_elem", dp["kv_format_bytes_per_elem"])
    kv_per_user = wl["bytes"]["kv_read"] * kvfmt / 2          # workload() counts BF16 (2 B)
    Q = QB.Q
    n = pt["users"] * pt["slots"]
    dr = pt["drafter"]
    dmul = (1 + QB.DRAFTER_LAYERS / Q["L"]) if dr else 1
    if dr:
        assert pt["verify_weight_macs"] == n * wl["weight_macs"] and pt["verify_attention_macs"] == n * wl["attention_macs"]
        mac_w = pt["verify_weight_macs"] + pt["draft_weight_macs"]
        mac_a = pt["verify_attention_macs"] + pt["draft_attention_macs"]
    else:
        mac_w, mac_a = n * wl["weight_macs"], n * wl["attention_macs"]
    kv_target = pt["users"] * kv_per_user
    kvb = kv_target * dmul                                      # target + drafter KV a step
    resident = min(lever.get("resident_kv_bytes", 0.0) * pt["users"], kv_target)
    sweeps = 1 if dr else math.ceil(n / m_lanes)
    wbytes = sweeps * (wl["weight_macs"] * dp["weight_bits"] / 8 + dp.get("weight_scale_bytes", 0)) + \
        (QB.DRAFTER_PARAMS * dp["drafter_weight_bits"] / 8 if dr else 0)
    hbm_w = pt.get("hbm_weight_bytes", 0)
    d = cfg["die"]
    hb = PS.hbm_split(cfg)
    die_pj = lever.get("hbm_die_pj", hb["die"])
    stack_pj = hb["stack"]            # the stack's in-DRAM share is not the die's lever
    sram, dlv = val(d["sram_j_per_byte"]), val(d["operand_delivery_j_per_byte"])
    rd = lever.get("resident_read_j_per_byte", 0.0)
    wr = lever.get("resident_write_j_per_byte", rd)
    toks = pt["tokens_per_step"]
    new_rows = n * 2 * Q["L"] * Q["KV"] * Q["HD"] * kvfmt if resident else 0.0
    dyn = dict(   # joules per STEP, die-side dynamic, both dies (the order of tools/power_scenarios.qwen_point)
        mac_weights=mac_w * PS.mac_pj(cfg, scenario, "qwen3", dp["weight_mac_format"]) * 1e-12 * v2,
        mac_attention=mac_a * PS.mac_pj(cfg, scenario, "qwen3", "bf16") * 1e-12 * v2,
        weight_read_and_delivery=wbytes * (val(d["rom_read_j_per_byte"]) + dlv) * v2,
        kv_ring_sram_and_delivery=kvb * (2 * sram + dlv) * v2,
        stream_unit=n * wl["elementwise_total"] * dmul * (val(d["stream_fp32_op_j"]) + 12 * sram) * v2,
        hbm_controller_phy_io=(kvb - resident) * 8 * die_pj * 1e-12,
    )
    if hbm_w:
        dyn["hbm_weight_read"] = hbm_w * (8 * die_pj * 1e-12 + (2 * sram + dlv) * v2)
    n_pkg = dp["dies_per_package"]
    if n_pkg > 1:   # the TP-2 exchanges (link I/O: not on the core rail, not scaled by DVFS), as power_scenarios
        nbytes = QB.tp_exchanges(dp["clock_hz"], n)["bytes_per_direction"]
        if dr:
            nbytes += QB.tp_exchanges(dp["clock_hz"], n, "draft")["bytes_per_direction"]
        dyn["ucie_exchange"] = nbytes * 2 * 8 * val(d["link_j_per_bit"]["ucie"])
    if resident:
        dyn["kv_resident_sram_read"] = resident * rd * v2
        dyn["kv_resident_sram_write"] = new_rows * wr * v2
    ar = _areas(dp, pt["lane_copies_on"], lever)
    st = PS._die_static(cfg, ar, clock, dp["hbm_stacks"])      # the package's static watts
    st["clock_w"] *= v2
    static_w = sum(st.values())
    t = pt["step_cycles"] / clock
    rate = toks / t
    dyn_tok = sum(dyn.values()) / toks
    hbm_bytes = kvb - resident + hbm_w
    stack_tok = hbm_bytes * 8 * stack_pj * 1e-12 / toks
    stk_hi_tok = hbm_bytes * 8 * hb["stack_high"] * 1e-12 / toks
    classes = PS._class_caps(cfg, n_pkg, static_w / n_pkg, dyn_tok / n_pkg, stk_hi_tok / n_pkg, rate,
                             ar["logic"] / n_pkg)
    die_w = (static_w + dyn_tok * rate) / n_pkg
    comp = {k: v / toks * 1e3 for k, v in dyn.items()}
    comp.update({k.replace("_w", ""): v / rate * 1e3 for k, v in st.items()})
    return dict(design_rate_tokens_s=rate, step_cycles=pt["step_cycles"], tokens_per_step=toks,
                block=pt.get("block", 1), lane_multiplier_m=m_lanes, clock_hz=clock, dies=n_pkg,
                energy_per_token_mj=(dyn_tok + static_w / rate + stack_tok) * 1e3,
                die_energy_per_token_mj=(dyn_tok + static_w / rate) * 1e3,
                die_dynamic_mj_per_token=dyn_tok * 1e3, per_die_dynamic_mj_per_token=dyn_tok / n_pkg * 1e3,
                stack_energy_per_token_mj=stack_tok * 1e3,
                die_components_mj_per_token=comp, die_static_w={k: v / n_pkg for k, v in st.items()},
                package_static_w=st, die_w_at_design_rate=die_w, package_dies_w_at_design_rate=die_w * n_pkg,
                stacks_w_high=stk_hi_tok * rate, resident_kv_bytes_per_user=resident / pt["users"],
                resident_kv_fraction=resident / kv_target, hbm_kv_bytes_per_step=hbm_bytes, areas_package_mm2=ar,
                cooling_classes=classes,
                capped_rate=classes[dp.get("cooling_class", "air")]["capped_rate"],
                binds=classes[dp.get("cooling_class", "air")]["binds"])


def kv_split(cfg, scenario, key):
    """Where the baseline's package die-side energy goes, as fractions: KV streaming (HBM die share + ring), weights
    (weight MACs + ROM read/delivery), attention MACs, control (stream unit), the die-to-die exchanges, static
    (leakage, clock, stack idle)."""
    r = evaluate(cfg, scenario, key)
    c = r["die_components_mj_per_token"]
    groups = dict(kv_streaming=c["hbm_controller_phy_io"] + c["kv_ring_sram_and_delivery"],
                  weights=c["mac_weights"] + c["weight_read_and_delivery"], attention_macs=c["mac_attention"],
                  stream_unit=c["stream_unit"], ucie_exchange=c.get("ucie_exchange", 0.0),
                  static=c["leakage"] + c["clock"] + c["hbm_idle"])
    tot = sum(groups.values())
    assert abs(tot - r["die_energy_per_token_mj"]) < 1e-9 * tot
    return dict(die_mj_per_token=tot, mj=groups, fraction={k: v / tot for k, v in groups.items()},
                stack_mj_per_token=r["stack_energy_per_token_mj"])


def resident_needed(cfg, scenario, key, lever_base, target_rate, cls="air"):
    """Resident KV bytes a user needs (both dies together) for the package to reach `target_rate` in class `cls`
    (bisection over bytes), or None if even the whole KV on die does not."""
    kv = PS_kv_bytes(cfg)

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


def package_slack_mm2(cfg):
    """The package's unused silicon: dies x reticle less the design point's package areas (the budget's slack a
    die, results/arch/qwen3_budget.json area.slack_mm2, times the dies, up to its rounding)."""
    dp = cfg["design_points"]["qwen3"]
    a = dp["area_mm2"]
    used = sum(a[k] for k in ("compute", "interconnect", "overhead", "hbm_phy", "ucie_phy", "stream_unit_spill", "rom",
                              "drafter_rom", "sram")) + a["lane_copy"] * (a["lane_multiplier_m"] - 1)
    return dp["dies_per_package"] * cfg["cooling"]["die_mm2"] - used


def levers(cfg, L):
    """{name: dict(lever=..., meta=...)}: every lever as a named scenario, inputs from the lever config."""
    dp = cfg["design_points"]["qwen3"]
    a = dp["area_mm2"]
    n_pkg = dp["dies_per_package"]
    m0 = a["lane_multiplier_m"]
    silicon = n_pkg * cfg["cooling"]["die_mm2"]
    slack = package_slack_mm2(cfg)
    S = L["sram"]
    rd = val(S["resident_read_j_per_byte"])
    out = {}

    def kv_lever(name, mm2, m, what):
        lv = dict(kv_sram_mm2=mm2, resident_kv_bytes=_sram_bytes(L, mm2), resident_read_j_per_byte=rd,
                  lane_multiplier_m=m)
        out[name] = dict(lever=lv, meta=dict(
            family="1 KV window on die", what=what, area_mm2_added=0.0, kv_sram_mm2=mm2,
            kv_sram_mm2_per_die=mm2 / n_pkg, lane_copies_removed_per_die=m0 - m, silicon_mm2=silicon, dies=n_pkg,
            evidence=[S["density_bytes_per_mm2"], S["resident_read_j_per_byte"]]))

    kv_lever("kv_sram_in_slack", slack, m0,
             f"each die's {slack / n_pkg:.1f} mm2 of slack ({slack:.1f} mm2 in the package) filled with SRAM holding "
             "the user's most recent KV rows of that die's own KV heads")
    for m in L["lane_trades"]["lane_multiplier_options"]:
        k = m0 - m
        kv_lever(f"kv_sram_for_{k}_lane_cop{'y' if k == 1 else 'ies'}_per_die", slack + k * a["lane_copy"], m,
                 f"{k} of the {m0 - 1} lane copies a die ({k * a['lane_copy'] / n_pkg:.1f} mm2 a die, idle at "
                 f"autoregressive batch 1) plus the slack re-spent on a KV SRAM; lane multiplier {m0} -> {m} "
                 + ("(DFlash re-timed on the package basis at m = %d)" % m if m > 1 else
                    "(DFlash degenerates: its best block at m = 1 on the package basis is re-timed)"))
    # 4-bit KV: a SENSITIVITY only (user rule), not a lever
    out["sensitivity_kv_int4"] = dict(lever=dict(kv_bytes_per_elem=0.5), meta=dict(
        family="sensitivity", what="4-bit KV (0.5 B an element): SENSITIVITY ONLY -- FP8 KV is the design point "
        "(user rule); a golden change with an unmeasured accuracy cost", area_mm2_added=0.0,
        silicon_mm2=silicon, dies=n_pkg, evidence=[]))
    # fixed-function streaming controller: measured PHY + sourced controller logic estimate
    C = L["hbm_controller"]
    if C.get("scenario_die_pj_per_bit") is not None:
        out["fixed_function_streaming_controller"] = dict(
            lever=dict(hbm_die_pj=val(C["scenario_die_pj_per_bit"])),
            meta=dict(family="2 controller/PHY energy", what=C["scenario_die_pj_per_bit"]["boundary"],
                      area_mm2_added=0.0, silicon_mm2=silicon, dies=n_pkg,
                      evidence=[C[k] for k in C["scenario_parts"]]))
    # clock/voltage
    for p in dvfs_points(L):
        if p["hz"] not in L["dvfs"]["levers_at_hz"]:
            continue
        out[f"dvfs_f{p['f_ratio']:.3f}"] = dict(lever=dict(f_ratio=p["f_ratio"], v_ratio=p["v_ratio"]), meta=dict(
            family="4 clock/voltage", what=f"core clock of both dies x{p['f_ratio']:.3f} at core supply "
            f"x{p['v_ratio']:.3f} (the {p['hz'] / 1e6:.0f} MHz / {p['uv'] / 1e6:.4f} V point of the N6 OPP table "
            "over its top point)", area_mm2_added=0.0, silicon_mm2=silicon, dies=n_pkg,
            evidence=[L["dvfs"]["curve"]]))
    return out


def dvfs_points(L):
    """The sourced V/f table normalised to its top point: our routed clock is taken to be the table's top (0.75 V)."""
    tab = L["dvfs"]["curve"]["table_hz_uv"]
    hz0, uv0 = max(tab)
    return [dict(hz=h, uv=u, f_ratio=h / hz0, v_ratio=u / uv0) for h, u in sorted(tab, reverse=True)]


def dvfs_basis(cfg):
    """Why the rate scales with f: the batch-1 step's cycles against the KV stream's at the design context."""
    dp = cfg["design_points"]["qwen3"]
    b = timing_basis()["rom_token"][f"{dp['context']}/fp8"]
    kv_s = b["kv_stream_cycles"] / dp["clock_hz"]
    step = dp["ar_batch1"]["step_cycles"]
    return dict(ar_step_cycles=step, kv_stream_cycles=b["kv_stream_cycles"], kv_stream_s=kv_s,
                highest_f_ratio_still_compute_bound=step / b["kv_stream_cycles"],
                source="configs/hardware/power_scenarios.json design_points.qwen3.ar_batch1.step_cycles; "
                       "tools/arch_budget_qwen3.timing_basis rom_token['<context>/fp8'].kv_stream_cycles (the 8 "
                       "stacks' stream, whose seconds do not scale with the core clock)",
                note="lowering the core clock lengthens the chain's seconds while the KV stream's stay fixed, so "
                     "the step stays compute-chain bound at every f_ratio <= highest_f_ratio_still_compute_bound "
                     "(the chain's cycles over the stream's) and the rate scales with f.  The UCIe hops' seconds "
                     "are also fixed, so the rate at a lowered clock is a lower bound (conservative)")


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
    return dict(basis=dvfs_basis(cfg), rows=rows,
                best_air={kk: dict(hz=v["hz"], f_ratio=v["f_ratio"], v_ratio=v["v_ratio"], **v[kk])
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


def target_rate(cfg):
    """The target every lever is graded against (configs/hardware/qwen_power_levers.json target): the baseline's
    own autoregressive batch-1 design rate, i.e. batch 1 uncapped."""
    return PS.qwen_point(cfg, SCENARIOS[-1], "ar_batch1")["design_rate_tokens_s"]


def build(cfg_path=CFG):
    cfg, L = load(cfg_path)
    base = {s: {k: evaluate(cfg, s, k) for k in KEYS} for s in SCENARIOS}
    # the evaluator IS the baseline model when no lever is set
    for s in SCENARIOS:
        for k in KEYS:
            ref = PS.qwen_point(cfg, s, k)
            for f in ("energy_per_token_mj", "die_energy_per_token_mj", "die_w_at_design_rate", "capped_rate",
                      "design_rate_tokens_s", "stack_energy_per_token_mj"):
                assert abs(ref[f] - base[s][k][f]) <= 1e-9 * abs(ref[f]), (s, k, f, ref[f], base[s][k][f])
    # the DFlash re-timing reproduces the record at the design lane multiplier
    dp = cfg["design_points"]["qwen3"]
    p = dflash_point_m(dp, dp["area_mm2"]["lane_multiplier_m"])
    for f in ("block", "tokens_per_step", "step_cycles", "macs_per_step"):
        assert p[f] == dp["dflash"][f], (f, p[f], dp["dflash"][f])
    target = target_rate(cfg)
    rec = dict(schema=SCHEMA, tool="tools/qwen_power_levers.py",
               inputs={str(Path(q).relative_to(ROOT)): _sha(q) for q in (cfg_path, PS.CFG, PS.DFLASH_REC,
                                                                         DFLASH_ACCEPT)},
               timing_basis=dict(source="tools/dflash_step_timing.design_basis (tools/arch_budget_qwen3.timing_basis)",
                                 sha256=hashlib.sha256(json.dumps(timing_basis(), sort_keys=True,
                                                                  default=float).encode()).hexdigest()),
               target_tokens_s=target, target_rule=L["target"]["rule"],
               baseline={s: {k: _row(base[s][k]) for k in KEYS} for s in SCENARIOS},
               energy_split_batch1={s: {k: kv_split(cfg, s, k) for k in KEYS} for s in SCENARIOS},
               package_slack_mm2=package_slack_mm2(cfg),
               levers={}, superseded_levers=L.get("superseded_levers", {}), not_evaluated=L.get("not_evaluated", {}))
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
                row["reaches_target_air"] = r["cooling_classes"]["air"]["capped_rate"] >= target * (1 - 1e-9)
                row["reaches_target_liquid"] = r["cooling_classes"]["liquid"]["capped_rate"] >= target * (1 - 1e-9)
                res[s][k] = row
        meta = dict(meta, weakest_evidence_class=_weakest(meta.pop("evidence")))
        rec["levers"][name] = dict(meta, lever_inputs=lv, result=res,
                                   atlas_figures_if_adopted=L["atlas_figures_if_adopted"][meta["family"].split()[0]])
    # how much on-die KV the package would need to reach the target (for scale against the slack)
    rec["resident_kv_needed_for_target"] = {}
    for s in SCENARIOS:
        for cls in ("air", "liquid"):
            b = resident_needed(cfg, s, "ar_batch1", dict(resident_read_j_per_byte=val(L["sram"]["resident_read_j_per_byte"])),
                                target, cls)
            rec["resident_kv_needed_for_target"][f"{s}/{cls}"] = None if b is None else dict(
                bytes=b, fraction_of_kv=b / PS_kv_bytes(cfg),
                sram_mm2=b / val(L["sram"]["density_bytes_per_mm2"]),
                sram_mm2_per_die=b / val(L["sram"]["density_bytes_per_mm2"]) / dp["dies_per_package"],
                note="SRAM area (package total, both dies) at the lever config's density, before any leakage/clock "
                     "of the new area (lower bound on the area)")
    rec["dflash_kv_amortisation"] = dflash_amortisation(cfg, base)
    rec["dvfs_sweep"] = dvfs_sweep(cfg, L)
    rec["hbm_die_share_needed_for_target"] = die_share_needed(cfg, target)
    rec["summary"] = summary(rec, cfg)
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
                                   reference=dict(baseline_mi250x=base, gh200_hbm3=8.23, oconnor_io_floor=0.8),
                                   below_gh200_derived=lo < 8.23)
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
    keep = ("design_rate_tokens_s", "clock_hz", "dies", "block", "lane_multiplier_m", "tokens_per_step", "step_cycles",
            "energy_per_token_mj", "die_energy_per_token_mj", "die_dynamic_mj_per_token",
            "per_die_dynamic_mj_per_token", "stack_energy_per_token_mj", "die_components_mj_per_token",
            "die_static_w", "package_static_w", "die_w_at_design_rate", "package_dies_w_at_design_rate",
            "stacks_w_high", "resident_kv_bytes_per_user", "resident_kv_fraction", "hbm_kv_bytes_per_step",
            "areas_package_mm2")
    out = {k: r[k] for k in keep}
    out["cooling_classes"] = {c: {k: v for k, v in x.items() if k in (
        "reference", "die_limit_w", "package_limit_w", "dies_per_package", "thermal_rate_limit", "capped_rate", "binds",
        "bound_by", "die_w_at_cap", "package_w_at_cap")} for c, x in r["cooling_classes"].items()}
    out["capped_rate"] = r["capped_rate"]
    return out


def summary(rec, cfg):
    dp = cfg["design_points"]["qwen3"]
    silicon = dp["dies_per_package"] * cfg["cooling"]["die_mm2"]
    rows = []
    for s in SCENARIOS:
        for k in KEYS:
            b = rec["baseline"][s][k]
            rows.append(dict(lever="baseline", scenario=s, point=k, design_rate=b["design_rate_tokens_s"],
                             air=b["cooling_classes"]["air"]["capped_rate"],
                             liquid=b["cooling_classes"]["liquid"]["capped_rate"], per_user_rate_kept=True,
                             silicon_mm2=silicon, evidence="baseline"))
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
        print(f"{r['lever']:40s} {r['scenario'][:1]} {r['point']:9s} design {r['design_rate']:8.0f}  air {r['air']:8.0f}"
              f"  liquid {r['liquid']:8.0f}  rate kept {str(r['per_user_rate_kept']):5s} {r['silicon_mm2']:7.1f} mm2 "
              f"[{r['evidence']}]")


if __name__ == "__main__":
    main()
