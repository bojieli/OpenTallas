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
energy is split between the DRAM stack (O'Connor's in-DRAM 3.45 pJ/bit) and the logic die (the rest of SC'25's
13.11 pJ/bit: controller, PHY, I/O, control plane), and the die's share is charged to die cooling.

For each design point the record gives energy per token by component, die power against the cooling limit
(0.5 W/mm2 x 815 mm2) and the rate the cooling limit allows:

* Qwen3-8B ROM reticle, 8K context, FP8 KV: autoregressive batch 1 and DFlash (tau 4.1, block 3);
* DeepSeek-V4.1 ROM array at 1M and 200K: batch 1 without and with MTP (gamma 5, tau 4.1) and the saturated batch.

The die's power is static (leakage + clock + HBM idle) plus dynamic energy per token x rate, so the cooling-capped
rate is (cooling - static) / dynamic energy per token -- per die for the V4.1 array (see _v41_point).
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
OUT = ROOT / "results/arch/power_scenarios.json"
SCHEMA = "opentallas.power-scenarios-result.v1"
SCENARIOS = ("A_measured_implementation", "B_proposed_production")


def load_cfg(path=CFG):
    return json.loads(Path(path).read_text())


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


def cooling_w(cfg):
    return val(cfg["cooling"]["w_per_mm2"]) * cfg["cooling"]["die_mm2"]


def _cap(cool, static_w, dyn_w_per_rate, design_rate):
    """Largest rate with static + dyn_w_per_rate x rate <= cool (dyn_w_per_rate: joules the hottest die spends
    per unit of the rate), and whether it binds below the design rate."""
    head = cool - static_w
    thermal = head / dyn_w_per_rate if head > 0 else 0.0
    return dict(thermal_rate_limit=thermal, capped_rate=min(design_rate, thermal), binds=thermal < design_rate)


# -- Qwen3-8B ROM reticle -----------------------------------------------------------------------------------------------
def _qwen_areas(dp, copies_on):
    a = dp["area_mm2"]
    m = a["lane_multiplier_m"]
    copies = a["lane_copy"] * (m - 1)
    logic = a["compute"] + a["interconnect"] + a["overhead"] + a["hbm_phy"] + a["stream_unit_spill"] + copies
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
    """One Qwen3 ROM-reticle step on scenario `scenario`: energy by component (per emitted token), die power at
    the design rate, the cooling-limited rate.  `hbm_die_pj` overrides the die's HBM share (sensitivity)."""
    import arch_budget_qwen3 as QB
    dp = cfg["design_points"]["qwen3"]
    pt = dp[key]
    clock = dp["clock_hz"]
    wl = QB.workload(dp["context"])
    kv_per_user = wl["bytes"]["kv_read"] * dp["kv_format_bytes_per_elem"] / 2     # workload() counts BF16 (2 B)
    per_layer, _ = QB.matrices()
    layer_macs = sum(a * b for a, b in per_layer.values())
    Q = QB.Q
    n = pt["users"] * pt["slots"]
    dr = pt["drafter"]
    draft_macs = (pt["slots"] * QB.DRAFTER_LAYERS * layer_macs + (pt["slots"] - 1) * Q["V"] * Q["H"]
                  + pt["slots"] * QB.DFLASH_FC[0] * QB.DFLASH_FC[1]) if dr else 0
    kvb = pt["users"] * kv_per_user * ((1 + QB.DRAFTER_LAYERS / Q["L"]) if dr else 1)
    sweeps = 1 if dr else math.ceil(n / dp["area_mm2"]["lane_multiplier_m"])
    wbytes = sweeps * wl["bytes"]["weights_rom_format"] + (QB.DRAFTER_PARAMS * 3.5 / 8 if dr else 0)
    d = cfg["die"]
    hb = hbm_split(cfg)
    die_pj = hb["die"] if hbm_die_pj is None else hbm_die_pj
    stack_pj = hb["total"] - die_pj
    sram, dlv = val(d["sram_j_per_byte"]), val(d["operand_delivery_j_per_byte"])
    toks = pt["tokens_per_step"]
    dyn = dict(   # joules per STEP, die-side dynamic
        mac_weights=(n * wl["weight_macs"] + draft_macs) * mac_pj(cfg, scenario, "qwen3", "w4a8") * 1e-12,
        mac_attention=n * wl["attention_macs"] * mac_pj(cfg, scenario, "qwen3", "bf16") * 1e-12,
        weight_read_and_delivery=wbytes * (val(d["rom_read_j_per_byte"]) + dlv),
        kv_ring_sram_and_delivery=kvb * (2 * sram + dlv),
        stream_unit=n * wl["elementwise_total"] * (val(d["stream_fp32_op_j"]) + 12 * sram),
        hbm_controller_phy_io=kvb * 8 * die_pj * 1e-12,
    )
    st = _die_static(cfg, _qwen_areas(dp, pt["lane_copies_on"]), clock, dp["hbm_stacks"])
    static_w = sum(st.values())
    t = pt["step_cycles"] / clock
    rate = toks / t
    dyn_tok = sum(dyn.values()) / toks
    stack_tok = kvb * 8 * stack_pj * 1e-12 / toks
    die_w = static_w + dyn_tok * rate
    cool = cooling_w(cfg)
    cap = _cap(cool, static_w, dyn_tok, rate)
    comp = {k: v / toks * 1e3 for k, v in dyn.items()}
    comp.update({k.replace("_w", ""): v / rate * 1e3 for k, v in st.items()})
    return dict(design_rate_tokens_s=rate, step_cycles=pt["step_cycles"], tokens_per_step=toks,
                energy_per_token_mj=(dyn_tok + static_w / rate + stack_tok) * 1e3,
                die_energy_per_token_mj=(dyn_tok + static_w / rate) * 1e3,
                die_dynamic_mj_per_token=dyn_tok * 1e3, stack_energy_per_token_mj=stack_tok * 1e3,
                die_components_mj_per_token=comp, die_static_w=st, die_w_at_design_rate=die_w,
                stacks_w_at_design_rate=stack_tok * rate + 0.0,
                stacks_w_high=kvb * 8 * hb["stack_high"] * 1e-12 / toks * rate,
                cooling_limit_w=cool, die_over_cooling=die_w / cool, **cap)


# -- DeepSeek-V4.1 ROM array ------------------------------------------------------------------------------------------
FMT = {"fp8": "fp8", "fp4": "fp4", "bf16": "bf16", "fp32": "fp32", "bf16xfp8": "bf16"}


def _v41_energy(cfg, scenario, V, E, ctx, users, positions, hbm_die_pj=None):
    """Joules per emitted POSITION of the whole array, die-side dynamic by component and the stacks' share.
    Same quantities as tools/arch_budget_v41.energy_per_token (weights read once per microbatch pass, routed
    experts as their union, KV and index keys per user), priced on the scenario's inputs."""
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
    dyn = dict(
        mac=sum(v * mac_pj(cfg, scenario, "v41", FMT.get(k.split(":")[1], "bf16")) * 1e-12
                for k, v in tot["macs"].items()),
        weight_read_and_delivery=w_bytes * (val(d["rom_read_j_per_byte"]) + val(d["operand_delivery_j_per_byte"])),
        kv_sram=tot["bytes"]["kv_sram"] * val(d["sram_j_per_byte"]),
        stream=sum(tot["elems"].values()) * 3 * val(d["stream_fp32_op_j"]),
        links=tot["collective_bytes"] * 8 * (val(lj["board"]) + val(lj["ucie"])) * 4,
        hbm_controller_phy_io=hbm_bits * die_pj * 1e-12,
    )
    return dyn, hbm_bits * (hb["total"] - die_pj) * 1e-12, hbm_bits * hb["stack_high"] * 1e-12


def _v41_static(cfg, E, V, D):
    """Per-die static watts of an ACTIVE die: leakage over the die's whole logic and ROM area, clock over the
    whole logic (ungated: the conservative end -- the populated blocks are 87 mm2 of 526), 5 stacks' idle."""
    d = E["designs"][D.ARRAY_DESIGN]["area_split_per_device"]
    logic = d["total_mm2"] - d["rom_mm2"] - d["sram_mm2"]
    ar = dict(logic=logic, clocked_logic=logic, rom=d["rom_mm2"], sram=d["sram_mm2"])
    return _die_static(cfg, ar, E["clock"], cfg["design_points"]["v41"]["hbm_stacks_per_die"])


def v41_points(cfg, scenario, hbm_die_pj=None):
    import arch_budget_v41 as V
    import decode_critical_path as D
    E = V._env()
    dp = cfg["design_points"]["v41"]
    rec = json.loads(V41_REC.read_text())
    st = _v41_static(cfg, E, V, D)
    static_w = sum(st.values())
    cool = cooling_w(cfg)
    ld, stages, dies = dp["layer_dies"], dp["stages"], dp["dies"]
    g, tau, ovh = dp["mtp"]["gamma"], dp["mtp"]["tau"], dp["mtp"]["draft_overhead"]
    out = {}
    for ctx in dp["contexts"]:
        rows = rec["batch"][str(ctx)]["rows"]["rom"]
        b1 = rows[0]
        sat = max(rows, key=lambda r: r["ar_aggregate_tokens_s"])
        pts = {}
        # batch 1, autoregressive: one token at a time; a layer die works only while its stage holds it (T/stages),
        # so the hottest die spends (die energy / layer dies) in T/stages: power = E x rate x stages / layer dies
        dyn, stk, stk_hi = _v41_energy(cfg, scenario, V, E, ctx, 1, 1, hbm_die_pj)
        pts["ar_batch1"] = dict(rate=b1["ar_tokens_s_per_user"], per_die=stages / ld, dyn=dyn, stk=stk, stk_hi=stk_hi,
                                basis="per user; hottest die = a layer die during its stage window")
        # batch 1 with MTP: a verify pass is gamma+1 positions per tau emitted tokens (+ the draft's ~3/40)
        dv, sv, sv_hi = _v41_energy(cfg, scenario, V, E, ctx, 1, g + 1, hbm_die_pj)
        f = (g + 1) / tau * (1 + ovh)
        pts["mtp_batch1"] = dict(rate=b1["mtp_tokens_s_per_user"], per_die=stages / ld,
                                 dyn={k: v * f for k, v in dv.items()}, stk=sv * f, stk_hi=sv_hi * f,
                                 basis=f"per user, gamma {g}, tau {tau}")
        # saturated batch: every layer die busy all the time; its share of the aggregate is 1 / layer dies
        m = V.fill_machine(sat["batch"])
        ds, ss, ss_hi = _v41_energy(cfg, scenario, V, E, ctx, m.microbatch, 1, hbm_die_pj)
        pts[f"saturated_batch{sat['batch']}"] = dict(rate=sat["ar_aggregate_tokens_s"], per_die=1 / ld, dyn=ds, stk=ss,
                                                     stk_hi=ss_hi, basis="aggregate tokens/s of the array")
        res = {}
        for k, p in pts.items():
            e_dyn = sum(p["dyn"].values())
            die_w = static_w + e_dyn * p["per_die"] * p["rate"]
            cap = _cap(cool, static_w, e_dyn * p["per_die"], p["rate"])
            # whole-array energy per token: dynamic + stacks + the static of every die over the time a token
            # holds the array (idle dies' clock gated: leakage + HBM idle only; active dies clock too)
            active = min(dies, ld) if k.startswith("sat") else ld / stages
            idle_static = st["leakage_w"] + st["hbm_idle_w"]
            arr_static = (dies * idle_static + active * st["clock_w"]) / p["rate"]
            res[k] = dict(design_rate_tokens_s=p["rate"], basis=p["basis"],
                          array_dynamic_j_per_token=e_dyn, stack_j_per_token=p["stk"],
                          array_static_j_per_token=arr_static,
                          energy_per_token_j=e_dyn + p["stk"] + arr_static,
                          die_components_j_per_token=p["dyn"],
                          hottest_die_w=die_w, die_over_cooling=die_w / cool,
                          hottest_die_stacks_w=p["stk"] * p["per_die"] * p["rate"],
                          hottest_die_stacks_w_high=p["stk_hi"] * p["per_die"] * p["rate"], **cap)
        out[str(ctx)] = res
    return dict(per_context=out, die_static_w=st, cooling_limit_w=cool,
                layer_dies=ld, stages=stages, dies=dies)


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build(cfg_path=CFG):
    cfg = load_cfg(cfg_path)
    hb = hbm_split(cfg)
    rec = dict(schema=SCHEMA, tool="tools/power_scenarios.py",
               inputs={str(p.relative_to(ROOT)): _sha(p) for p in (Path(cfg_path), V41_REC,
                                                                    ROOT / "configs/hardware/technology.json")},
               hbm_split_pj_per_bit=hb,
               mac_pj={s: dict(qwen3_w4a8=mac_pj(cfg, s, "qwen3", "w4a8"), qwen3_bf16=mac_pj(cfg, s, "qwen3", "bf16"),
                               v41_fp4=mac_pj(cfg, s, "v41", "fp4"), v41_fp8=mac_pj(cfg, s, "v41", "fp8"),
                               v41_bf16=mac_pj(cfg, s, "v41", "bf16"), v41_fp32=mac_pj(cfg, s, "v41", "fp32"))
                       for s in SCENARIOS + ("B_gpu_tensor_sensitivity",)},
               scenarios={}, sensitivities={})
    for s in SCENARIOS:
        rec["scenarios"][s] = dict(qwen3_8b_rom_8k={k: qwen_point(cfg, s, k) for k in ("ar_batch1", "dflash")},
                                   deepseek_v41_rom_array=v41_points(cfg, s))
    # the lane no better than a shipping tensor core (A100 measured, control plane included)
    rec["sensitivities"]["B_lane_at_gpu_tensor_1p40pj"] = dict(
        qwen3_8b_rom_8k={k: qwen_point(cfg, "B_gpu_tensor_sensitivity", k) for k in ("ar_batch1", "dflash")},
        deepseek_v41_rom_array=v41_points(cfg, "B_gpu_tensor_sensitivity"))
    # the withdrawn allocation: only O'Connor's 0.8 pJ/bit I/O on the die, the rest on the stacks
    rec["sensitivities"]["B_old_hbm_allocation_die_0p8"] = dict(
        qwen3_8b_rom_8k={k: qwen_point(cfg, "B_proposed_production", k, hbm_die_pj=0.8) for k in ("ar_batch1", "dflash")},
        deepseek_v41_rom_array=v41_points(cfg, "B_proposed_production", hbm_die_pj=0.8))
    rec["was"] = cfg["design_points"]["qwen3"]["was"]
    rec["summary"] = summary(rec)
    return rec


def summary(rec):
    rows = []
    for s, body in list(rec["scenarios"].items()) + [(k, v) for k, v in rec["sensitivities"].items()]:
        for k, r in body["qwen3_8b_rom_8k"].items():
            rows.append(dict(scenario=s, design="Qwen3-8B ROM 8K", point=k, energy_per_token_mj=r["energy_per_token_mj"],
                             die_w=r["die_w_at_design_rate"], cooling_w=r["cooling_limit_w"],
                             design_rate=r["design_rate_tokens_s"], capped_rate=r["capped_rate"], binds=r["binds"]))
        for ctx, pts in body["deepseek_v41_rom_array"]["per_context"].items():
            for k, r in pts.items():
                rows.append(dict(scenario=s, design=f"V4.1 ROM array {int(ctx):,}", point=k,
                                 energy_per_token_mj=r["energy_per_token_j"] * 1e3, die_w=r["hottest_die_w"],
                                 cooling_w=body["deepseek_v41_rom_array"]["cooling_limit_w"],
                                 design_rate=r["design_rate_tokens_s"], capped_rate=r["capped_rate"], binds=r["binds"]))
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
        print(f"{r['scenario'][:30]:30s} {r['design']:24s} {r['point']:22s} {r['energy_per_token_mj']:9.2f} mJ/tok "
              f"die {r['die_w']:7.1f} W / {r['cooling_w']:.0f}  rate {r['design_rate']:9.0f} -> {r['capped_rate']:9.0f}"
              f"{'  BINDS' if r['binds'] else ''}")


if __name__ == "__main__":
    main()
