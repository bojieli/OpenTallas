#!/usr/bin/env python3
"""ROM-weight vs GPU-organised HBM: which LLMs suit a ROM design?  (model only, 2026-10-03)

MODEL ONLY: no RTL, no place and route, no model inference.  Inputs are the header-only profiles in
configs/models/candidates/rom_sweep/ (tools/rom_model_sweep_profile.py) and the calibrations listed in CAL below,
each taken from a committed record of this repository.

The per-user token is a latency chain, priced in 1.2 GHz streaming-domain cycles:

ROM (compute beside the weight macros; the Qwen3-8B option-C element replicated):
  layer = BODY_FIXED + W_layer / (k * BW_DIE)          the measured RTL body (position 0) split into its fixed
                                                      dependent-op latency and its weight stream
        + 2 * AR(k, H)                                 one-stream all-reduces, the measured TP-4 board collective
        + ATTN_FIXED + KV_layer / (k * s * STACK_Bpc)  near-HBM two-phase attention (K phase + V phase)
        [+ MOE_SELECT on MoE layers] [+ state r/w + LIN_CHAIN on linear-attention layers]
  token = sum(layers) + NONLAYER_FIXED + head / (k * BW_DIE) + (S - 1) * stage hop
  dies D = ceil(stored 8-bit text weights / ROM_DIE_B), at least k, rounded up to a multiple of k; S = D / k stages.
  Only the active stage's k dies work on a token, so the weight term is active bytes / (k * BW_DIE) no matter how
  many stages hold the model: total parameters cost dies and silicon, active parameters cost time.

HBM (GPU organisation, right-sized die with 4 stacks, every matrix TP-sharded over all n dies):
  layer = max(W_layer / BW_sys, BODY_FIXED) + ATTN_FIXED + KV_layer / BW_sys + 2 * AR_hbm(n)  [+ the same extras]
  token = sum(layers) + head / BW_sys + NONLAYER_FIXED
  BW_sys = 4 * n * 0.9 TB/s.  Weights are prefetched under the previous layer's compute (stream_overlap), KV is not.
  AR_hbm: in-package TP-2 = the measured UCIe one-shot (71 cycles); wider = the measured board collective with
  in-switch reduction (flat in n, as the W19 TP-96 composition's 0.91 us a collective).

Calibration identity (asserted in main()): Qwen3-8B, ROM k = 4, s = 4 reproduces the near-HBM-selected 229,158-cycle
token (5,236.6 tok/s); HBM n = 2 reproduces the 880.5 tok/s tier-3 comparator within 2%.

Speculation: ROM lanes are sized for one position (m = 1, the adopted V4.1 MTP policy), so a P-position verify
re-streams the weights P times through the same lanes; collectives carry P x payload; the KV is read once.  The HBM
SM columns (16) take up to 16 positions on one weight fetch, so verify costs bandwidth once (MoE: the union of
experts the P positions touch).  Drafter passes are priced on the same machinery.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROF = ROOT / "configs/models/candidates/rom_sweep"
TECH = json.loads((ROOT / "configs/hardware/technology.json").read_text())
NEAR = ROOT / "results/uarch/qwen_rom_calibrated_calendar_20261003/near-hbm-selected-r1.json"
W15 = ROOT / "results/rtl/w15_collectives.json"

CLOCK = 1.2e9
_near = json.loads(NEAR.read_text())
_comp = _near["composition"]
_w15 = json.loads(W15.read_text())
_fit = _w15["configs"]["v41p17_r0d1024_sweep"]["fit"]

CAL = dict(
    clock_hz=CLOCK,
    body_cycles_qwen=_comp["body_cycles"],                       # 2,599: RTL TP-4 layer body less attention, less ARs
    ar_tp4_cycles=991,                                           # measured, two segment (near-hbm-selected headline case)
    attn_fixed_cycles=sum(v for k, v in _comp["attention_terms_primary"].items() if k in ("q_in", "drain", "return_and_hub")),
    nonlayer_cycles_qwen=_comp["nonlayer_cycles"],               # 3,042: embedding, final norm, head, argmax
    ar_ucie_tp2_cycles=_w15["configs"]["q256d64"]["exchanges"]["allreduce_cycles_mean"],   # 71, measured W15
    hop_fixed_ns=_fit["all_gather"]["fixed_cycles"] / _w15["configs"]["v41p17_r0d1024_sweep"]["clock_hz"] * 1e9,
    collective_cycles_per_64B=_fit["all_reduce"]["cycles_per_word"],
    stack_Bps=0.9e12,              # HBM3E, 1.0 TB/s a stack x 0.90 sustained (arch_budget_qwen3.HBM; HBM_STACK_BPS)
    stack_capacity_B=22.5e9 * 0.9,  # HBM_STACK_B x HBM_CAP_EFF (uarch_model.py)
    rom_mbit_per_mm2=75.0,          # storage-only N5, the ruled analytical density (uarch_model.py DENSITY RULE); no ECC
                                    # (AGENTS.md ROM reliability policy 2026-10-02)
    rom_array_mm2=560.0,            # QWEN_AREA.array_mm2: tile array after PHYs, UCIe, spine, corridors
    rom_groups=6144,
    rom_group_logic_mm2=(552.9 - 265.0 - (4 * 10.0 + 10.0 + 12.8)) / 6144,   # qwen_rom_area_per_group_mm2()
    rom_die_mm2=815.0,              # reticle-class die (arch_budget_qwen3.FLOORPLAN die_mm2)
    hbm_die_mm2=340.5,              # right-sized GPU-organised die, 4 stacks (consolidation.json comparison_rule)
    hbm_stack_mm2=1150.0,           # USER RULE: an HBM stack is silicon, ~1,000-1,300 mm2 (DRAM dies + base die); centre
    moe_select_cycles=419,          # ASSUMED proxy: router + top-k select = the measured wide select (W15b, 419 cycles)
    lin_chain_cycles=200,           # ASSUMED: gated-delta-rule state update chain per linear-attention layer
    hbm_cols=16,                    # SM_ELEM qwen cols: positions one weight fetch serves
    e_mac=TECH["energy"]["mac_energy_j_per_op"]["bf16"]["value"] * 2,   # J per MAC (2 ops), the BF16 lane of both
    e_rom_B=TECH["energy"]["rom_read_j_per_byte"]["value"] + TECH["energy"]["operand_delivery_j_per_byte"]["value"],
    e_hbm_B=TECH["energy"]["hbm_j_per_byte"]["value"],
    e_sram_B=TECH["energy"]["sram_read_j_per_byte"]["value"],
    e_board_bit=TECH["energy"]["link_j_per_bit"]["board_serdes_112g"]["value"],
    hbm_idle_w_stack=TECH["power"]["memory_interface_idle_w_per_stack"]["value"],
    rom_die_static_w=(200.0 - 16 * 2.8) / 4,     # economics.json qwen_rom static 200 W / 4 dies less 16 stacks idle
    hbm_die_static_w=(68.7 - 8 * 2.8) / 2,       # economics.json qwen_hbm static 68.7 W / 2 dies less 8 stacks idle
    rom_leak_w_mm2=TECH["power"]["static_leakage_w_per_mm2"]["rom_array"]["value"],
)
CAL["rom_array_rom_mm2"] = CAL["rom_array_mm2"] - CAL["rom_groups"] * CAL["rom_group_logic_mm2"]
CAL["rom_die_B"] = CAL["rom_array_rom_mm2"] * CAL["rom_mbit_per_mm2"] * 1e6 / 8
CAL["stack_Bpc"] = CAL["stack_Bps"] / CLOCK
CAL["hop_fixed_cycles"] = CAL["hop_fixed_ns"] * 1e-9 * CLOCK

# Speculation (tau = accepted tokens per verify pass, P = positions verified; drafter cost in layer passes)
SPEC = dict(
    mtp1=dict(P=2, tau=1.80, draft_layers=1, draft_heads=1, grade="ASSUMED: one native MTP module, ~80% acceptance "
              "(DeepSeek-V3 report 85-90% for the 2nd token)"),
    mtp3=dict(P=4, tau=2.60, draft_layers=3, draft_heads=3, grade="ASSUMED: three chained native MTP modules"),
    eagle3=dict(P=8, tau=3.00, draft_layers=7, draft_heads=7, head_frac=0.25, grade="ASSUMED: EAGLE-3 chain of 7, "
                "tau 3.0 (conservative vs the EAGLE-3 paper's tree acceptance)"),
    eagle=dict(P=6, tau=2.60, draft_layers=5, draft_heads=5, head_frac=1.0, grade="ASSUMED: EAGLE-1/2-class chain of 5"),
    eagle1=dict(P=6, tau=2.60, draft_layers=5, draft_heads=5, head_frac=1.0, grade="ASSUMED: EAGLE-1-class chain of 5"),
    dspark=dict(P=6, tau=3.649, draft_layers=3, draft_heads=1, grade="repo-measured DSpark gamma 5 on V4.1-Flash "
                "(results/speculative/v41_flash_dspark_onpolicy_greedy.json); 3 draft blocks"),
    dflash=dict(P=16, tau=3.656, draft_layers=5, draft_heads=16, draft_parallel=True,
                grade="repo-measured tau on Qwen3-8B (results/speculative/dflash_block_acceptance.json, block 16), "
                      "applied to other targets' DFlash drafters ASSUMED"),
)

CTXS = (8192, 32768, 131072)


def load(slug):
    return json.loads((PROF / f"{slug}.json").read_text())


def kv_bytes(m, ctx):
    """Per token: (KV/state bytes read, KV bytes stored at ctx) summed over layers, FP8 KV."""
    read = stored = 0.0
    per_layer = []
    for d in m["kv_layers"]:
        if d["kind"] == "linear":
            r = 2 * d["state_bytes"]                   # read + write the recurrent state every token
            s = d["state_bytes"]
        elif d["kind"] == "csa":                       # DeepSeek-V4.1 compressed sparse attention (+ index scan)
            ent = ctx / d["ratio"]
            scan = min(ent, d["scan_cap"]) if d.get("scan_cap") else ent
            r = (min(ent, d["top_k"]) * d["bytes_per_pos"] + min(ctx, d["window"]) * d["window_entry"]
                 + (scan * d["index_entry"] if d["scans"] else 0.0))
            s = (ent * (d["bytes_per_pos"] + d["index_entry"]) if d["owner"] else 0.0) + min(ctx, d["window"]) * d["window_entry"]
        else:
            pos = min(ctx, d["window"]) if d["window"] else ctx
            r = s = pos * d["bytes_per_pos"]
        read += r
        stored += s
        per_layer.append(r)
    return read, stored, per_layer


def arch(m):
    L = m["layers"]
    moe = m["moe"]["experts"] > 0
    pp = m["params"]
    w_layer = (pp["dense_layers"] + pp["active_routed"]) / L          # 8-bit: 1 B a parameter
    lin_layers = sum(1 for d in m["kv_layers"] if d["kind"] == "linear")
    return dict(L=L, H=m["hidden"], moe=moe, w_layer=w_layer, head=pp["head_streamed"], lin=lin_layers,
                stored=pp["total_text"], active=pp["active_per_token"], dense_layers=pp["dense_layers"],
                routed=pp["routed"], E=m["moe"]["experts"], topk=m["moe"]["top_k"])


def ar_cycles(H, P=1, base=None):
    base = CAL["ar_tp4_cycles"] if base is None else base
    return base + (P * H * 4 - 4096 * 4) / 64 * CAL["collective_cycles_per_64B"]


def distinct_frac(E, k, P):
    """Expected distinct experts touched by P tokens over top-k of E, as a multiple of k."""
    if not E:
        return 1.0
    return E * (1 - (1 - k / E) ** P) / k


def rom_ar(H, k, P=1):
    """TP-k all-reduce: the measured TP-4 board collective; each doubling beyond 4 adds one hop stage (ASSUMED at the
    W15 all-gather fixed latency)."""
    return ar_cycles(H, P) + max(0, math.log2(k / 4)) * CAL["hop_fixed_cycles"]


def rom_design(m, ctx, k=4, s=4, spread=False, P=1, spec=None):
    a = arch(m)
    D = max(k, math.ceil(a["stored"] / CAL["rom_die_B"]))
    D = math.ceil(D / k) * k
    S = D // k
    bw = k * CAL["bw_die"]
    kv_dies = D if spread else k          # spread: every layer's KV striped over every die's stacks
    kv_read, kv_stored, kv_l = kv_bytes(m, ctx)
    cyc = 0.0
    parts = dict(body_fixed=0.0, weights=0.0, allreduce=0.0, attention=0.0, moe_select=0.0, linear=0.0)
    for i in range(a["L"]):
        lin = m["kv_layers"][i]["kind"] == "linear"
        parts["body_fixed"] += CAL["body_fixed"]
        parts["weights"] += P * a["w_layer"] / bw
        parts["allreduce"] += 2 * rom_ar(a["H"], k, P)
        parts["attention"] += (CAL["attn_fixed_cycles"] + kv_l[i] / (kv_dies * s * CAL["stack_Bpc"])
                               + (2 * CAL["hop_fixed_cycles"] if spread and S > 1 else 0.0))
        if lin:
            parts["linear"] += CAL["lin_chain_cycles"] * P
        if a["moe"]:
            parts["moe_select"] += CAL["moe_select_cycles"]
    parts["nonlayer"] = CAL["nonlayer_fixed"] + P * a["head"] / bw
    parts["stage_hops"] = (S - 1) * (CAL["hop_fixed_cycles"] + P * a["H"] * 2 / 64)
    cyc = sum(parts.values())
    T = cyc / CLOCK
    # drafter (ROM-resident, priced on the same machinery)
    draft_T = 0.0
    if spec:
        sp = SPEC[spec]
        layer_one = CAL["body_fixed"] + 2 * rom_ar(a["H"], k) + a["w_layer"] / bw + CAL["attn_fixed_cycles"]
        if sp.get("draft_parallel"):
            dl = sp["draft_layers"] * (CAL["body_fixed"] + 2 * rom_ar(a["H"], k, sp["P"]) + sp["P"] * a["w_layer"] / bw
                                       + CAL["attn_fixed_cycles"])
            dh = sp["P"] * a["head"] / bw + CAL["nonlayer_fixed"]
        else:
            dl = sp["draft_layers"] * layer_one
            dh = sp["draft_heads"] * (sp.get("head_frac", 1.0) * a["head"] / bw + CAL["nonlayer_fixed"])
        draft_T = (dl + dh) / CLOCK
    silicon = D * CAL["rom_die_mm2"] + D * s * CAL["hbm_stack_mm2"]
    # energy (b1): dynamic per token, static per second
    act = a["active"]
    e_dyn = (act * CAL["e_mac"] + act * CAL["e_rom_B"] + kv_read * (CAL["e_hbm_B"] + 2 * CAL["e_sram_B"])
             + 2 * a["L"] * a["H"] * 4 * 8 * CAL["e_board_bit"] * (k - 1))
    rom_mm2 = min(a["stored"] / D, CAL["rom_die_B"]) * 8 / (CAL["rom_mbit_per_mm2"] * 1e6)
    p_static = D * (CAL["rom_die_static_w"] + (rom_mm2 - 229.3) * CAL["rom_leak_w_mm2"] + s * CAL["hbm_idle_w_stack"])
    return dict(k=k, s=s, kv_spread=spread, dies=D, stages=S, packages=math.ceil(D / 2), stacks=D * s, silicon_mm2=round(silicon),
                cycles=round(cyc), T_us=T * 1e6, tok_s=1 / T, parts_us={x: round(v / CLOCK * 1e6, 2) for x, v in parts.items()},
                draft_us=draft_T * 1e6, kv_read_B=kv_read, kv_stored_B=kv_stored,
                kv_fits=kv_stored <= D * s * CAL["stack_capacity_B"],
                e_dyn_J=e_dyn, p_static_W=p_static,
                energy_mJ=(e_dyn + p_static * T) * 1e3, power_W=p_static + e_dyn / T)


def hbm_design(m, ctx, n, P=1, spec=None):
    a = arch(m)
    bw = 4 * n * CAL["stack_Bpc"]                  # bytes a cycle, whole system
    ar = 0.0 if n == 1 else (CAL["ar_ucie_tp2_cycles"] if n == 2 else CAL["ar_tp4_cycles"])
    kv_read, kv_stored, kv_l = kv_bytes(m, ctx)
    passes = math.ceil(P / CAL["hbm_cols"])
    if a["moe"]:
        dense_l = a["dense_layers"] / a["L"]
        routed_l = a["routed"] / a["L"] * a["topk"] / a["E"] * min(distinct_frac(a["E"], a["topk"], P), a["E"] / a["topk"])
        w_l = dense_l + routed_l
    else:
        w_l = a["w_layer"]
    parts = dict(weights_or_body=0.0, attention=0.0, allreduce=0.0, moe_select=0.0, linear=0.0)
    for i in range(a["L"]):
        lin = m["kv_layers"][i]["kind"] == "linear"
        parts["weights_or_body"] += max(passes * w_l / bw, CAL["body_fixed"])
        parts["attention"] += CAL["attn_fixed_cycles"] + kv_l[i] / bw
        parts["allreduce"] += 2 * (ar_cycles(a["H"], P, ar) if ar else 0.0)
        if lin:
            parts["linear"] += CAL["lin_chain_cycles"] * P
        if a["moe"]:
            parts["moe_select"] += CAL["moe_select_cycles"]
    parts["nonlayer"] = CAL["nonlayer_fixed"] + passes * a["head"] / bw
    cyc = sum(parts.values())
    T = cyc / CLOCK
    draft_T = 0.0
    if spec:
        sp = SPEC[spec]
        one = max(a["w_layer"] / bw, CAL["body_fixed"]) + CAL["attn_fixed_cycles"] + 2 * (ar_cycles(a["H"], 1, ar) if ar else 0)
        heads = sp["draft_heads"] if not sp.get("draft_parallel") else 1
        dh = heads * (max(sp.get("head_frac", 1.0) * a["head"] / bw, 0) + CAL["nonlayer_fixed"])
        draft_T = (sp["draft_layers"] * one + dh) / CLOCK
    stored_fp8 = a["stored"]
    cap_ok = stored_fp8 + kv_stored <= 4 * n * CAL["stack_capacity_B"]
    silicon = n * (CAL["hbm_die_mm2"] + 4 * CAL["hbm_stack_mm2"])
    act = a["active"]
    wbytes = (w_l * a["L"] + a["head"]) * passes
    e_dyn = (act * P * CAL["e_mac"] + (wbytes + kv_read) * CAL["e_hbm_B"] + wbytes * 2 * CAL["e_sram_B"]
             + (2 * a["L"] * a["H"] * 4 * P * 8 * CAL["e_board_bit"] * 2 if n > 2 else 0.0))
    p_static = n * (CAL["hbm_die_static_w"] + 4 * CAL["hbm_idle_w_stack"])
    return dict(dies=n, packages=math.ceil(n / 2), stacks=4 * n, silicon_mm2=round(silicon), capacity_ok=cap_ok,
                cycles=round(cyc), T_us=T * 1e6, tok_s=1 / T, draft_us=draft_T * 1e6,
                parts_us={x: round(v / CLOCK * 1e6, 2) for x, v in parts.items()},
                e_dyn_J=e_dyn, p_static_W=p_static, energy_mJ=(e_dyn + p_static * T) * 1e3, power_W=p_static + e_dyn / T)


def hbm_min_dies(m, ctx):
    a = arch(m)
    _, kv_stored, _ = kv_bytes(m, ctx)
    return max(1, math.ceil((a["stored"] + kv_stored) / (4 * CAL["stack_capacity_B"])))


def spec_rate(design_fn, m, ctx, spec, **kw):
    sp = SPEC[spec]
    r = design_fn(m, ctx, P=sp["P"], spec=spec, **kw)
    return sp["tau"] / ((r["T_us"] + r["draft_us"]) * 1e-6)


def drafter_options(m):
    opts = []
    nm = m["mtp"]["native_modules"]
    if nm and m["mtp"]["weights_present"]:
        opts.append("mtp3" if nm >= 3 else "mtp1")
    for kind in m["drafters_published"]:
        if kind in SPEC:
            opts.append(kind)
    return opts


def calibrate(q):
    """Split the Qwen RTL body into fixed latency and weight stream; derive the per-die ROM read rate."""
    a = arch(q)
    # unit_busy weights (18,432) + lm_head (1,584) over the 36 layers + head of one TP-4 die is the weight stream
    # (results/uarch/consolidation.json qwen_rom.product_row.unit_busy): 18,432 / 36 = 512 cycles a layer
    w_cycles_layer = 18432 / 36
    CAL["bw_die"] = a["w_layer"] / 4 / w_cycles_layer
    CAL["body_fixed"] = CAL["body_cycles_qwen"] - w_cycles_layer
    CAL["nonlayer_fixed"] = CAL["nonlayer_cycles_qwen"] - a["head"] / (4 * CAL["bw_die"])


def evaluate(m):
    out = dict(slug=m["slug"], repo=m["original_repo"], profiled_repo=m["repo"], revision=m["revision"], license=m["license"])
    a = arch(m)
    out["shape"] = dict(
        total_params_B=round(m["params"]["total_text"] / 1e9, 2), active_params_B=round(a["active"] / 1e9, 2),
        sparsity_active_over_total=round(a["active"] / m["params"]["total_text"], 3),
        layers=a["L"], hidden=a["H"], heads=m["heads"], kv_heads=m["kv_heads"], head_dim=m["head_dim"],
        attention=sorted({d["kind"] for d in m["kv_layers"]}),
        attention_mix={k: sum(1 for d in m["kv_layers"] if d["kind"] == k) for k in sorted({d["kind"] for d in m["kv_layers"]})},
        experts=m["moe"]["experts"], top_k=m["moe"]["top_k"], shared_experts=m["moe"]["shared"],
        rom_weight_GB_8bit=round(m["params"]["total_text"] / 1e9, 2), hbm_weight_GB_fp8=round(m["params"]["total_text"] / 1e9, 2),
        active_weight_GB_per_token=round(a["active"] / 1e9, 2),
        vision_params_B_excluded=round(m["params"]["vision"] / 1e9, 2),
        mtp=m["mtp"], drafters_published=m["drafters_published"], max_context=m["max_context"],
        quantization_released=m.get("quantization"))
    out["kv"] = {str(c): dict(read_MB_per_token=round(kv_bytes(m, c)[0] / 1e6, 2),
                              stored_MB=round(kv_bytes(m, c)[1] / 1e6, 2),
                              per_position_B=round(kv_bytes(m, c)[1] / c, 1)) for c in CTXS}
    out["kv_bytes_per_position_per_layer"] = sorted({(d["kind"], d["bytes_per_pos"], d["window"]) for d in m["kv_layers"]})
    opts = drafter_options(m)
    res = {}
    for ctx in (8192, 32768):
        if m["max_context"] and ctx > m["max_context"]:
            res[str(ctx)] = dict(skipped=f"beyond the released max context {m['max_context']}")
            continue
        best = None
        configs = []
        for k in (4, 8, 16):
            for s in (1, 2, 4):
                for spread in (False, True):
                    r = rom_design(m, ctx, k=k, s=s, spread=spread)
                    n_iso = max(hbm_min_dies(m, ctx),
                                round(r["silicon_mm2"] / (CAL["hbm_die_mm2"] + 4 * CAL["hbm_stack_mm2"])))
                    h = hbm_design(m, ctx, n_iso)
                    ratio = r["tok_s"] / h["tok_s"]
                    configs.append(dict(k=k, s=s, kv_spread=spread, dies=r["dies"], rom_tok_s=round(r["tok_s"], 1),
                                        silicon_mm2=r["silicon_mm2"], hbm_dies=n_iso, hbm_tok_s=round(h["tok_s"], 1),
                                        ratio=round(ratio, 3)))
                    cand = (ratio, (k, s, spread), r, h, n_iso)
                    if best is None or ratio > best[0]:
                        best = cand
        ratio, (k, s, spread), r, h, n_iso = best
        adopted = next(c for c in configs if c["k"] == 4 and c["s"] == 4 and not c["kv_spread"])
        fastest = max(configs, key=lambda c: c["rom_tok_s"])
        # iso-power: the HBM die count whose b1 power matches the ROM system's
        n_pw = hbm_min_dies(m, ctx)
        while hbm_design(m, ctx, n_pw + 1)["power_W"] <= r["power_W"]:
            n_pw += 1
        hp = hbm_design(m, ctx, n_pw)
        sp_rom = {o: spec_rate(rom_design, m, ctx, o, k=k, s=s, spread=spread) for o in opts}
        sp_iso = {o: spec_rate(hbm_design, m, ctx, o, n=n_iso) for o in opts}
        sp_pw = {o: spec_rate(hbm_design, m, ctx, o, n=n_pw) for o in opts}
        if opts:                       # either side may decline speculation when it does not pay (AR = tau 1)
            sp_rom["ar"], sp_iso["ar"], sp_pw["ar"] = r["tok_s"], h["tok_s"], hp["tok_s"]
        br = max(sp_rom, key=sp_rom.get) if sp_rom else None
        bh = max(sp_iso, key=sp_iso.get) if sp_iso else None
        bp = max(sp_pw, key=sp_pw.get) if sp_pw else None
        res[str(ctx)] = dict(
            rom=dict(r, chosen="k, s, kv_spread maximising the iso-silicon AR ratio"), rom_configs=configs,
            rom_adopted_style_k4_s4=adopted, rom_fastest=fastest, hbm_iso_silicon=h, hbm_iso_power=hp,
            ratio_ar_iso_silicon=round(ratio, 3), ratio_ar_iso_power=round(r["tok_s"] / hp["tok_s"], 3),
            hbm_iso_power_dies=n_pw, hbm_iso_silicon_dies=n_iso, hbm_capacity_min_dies=hbm_min_dies(m, ctx),
            hbm_silicon_over_rom=round(h["silicon_mm2"] / r["silicon_mm2"], 3),
            energy_ratio_hbm_over_rom_iso_silicon=round(h["energy_mJ"] / r["energy_mJ"], 2),
            spec=dict(options=opts, rom=sp_rom, hbm_iso_silicon=sp_iso, hbm_iso_power=sp_pw,
                      rom_best=br, hbm_best=bh,
                      ratio_best_iso_silicon=(round(sp_rom[br] / sp_iso[bh], 3) if br else None),
                      ratio_best_iso_power=(round(sp_rom[br] / sp_pw[bp], 3) if br else None)))
        for side in ("rom", "hbm_iso_silicon", "hbm_iso_power"):
            for kk in ("T_us", "tok_s", "draft_us", "energy_mJ", "power_W", "e_dyn_J", "p_static_W"):
                res[str(ctx)][side][kk] = round(res[str(ctx)][side][kk], 4 if kk == "e_dyn_J" else 1)
            for kk in ("kv_read_B", "kv_stored_B"):
                res[str(ctx)][side].pop(kk, None)
        res[str(ctx)]["spec"] = {kk: ({o: round(v, 1) for o, v in vv.items()} if isinstance(vv, dict) else vv)
                                 for kk, vv in res[str(ctx)]["spec"].items()}
    out["results"] = res
    return out


def fmt(x, n=0):
    return "n/a" if x is None else (f"{x:,.{n}f}")


def write_md(rec, path):
    rows = sorted(rec["models"], key=lambda x: -(x["results"]["8192"].get("ratio_ar_iso_silicon") or 0))
    L = ["# ROM vs HBM model sweep: generated tables", "",
         "Generated by `tools/rom_model_sweep.py` from `sweep.json`. MODEL ONLY. Ranked by the iso-total-silicon AR "
         "ratio at 8K. ROM config = TP width k, HBM stacks a ROM die s, S = KV striped over every die's stacks "
         "(chosen to maximise the iso-silicon ratio; the adopted-style k = 4, s = 4 row is in `sweep.json`).", "",
         "## 1. Ranking: per-user rate, batch 1", "",
         "| # | model | active / total B | act/tot | layers | ROM dies (pkgs) | ROM cfg | ROM AR 8K | HBM iso-Si 8K (dies) "
         "| **AR ratio iso-Si 8K** | AR ratio iso-Si 32K | AR ratio iso-power 8K | spec ROM / HBM 8K (drafter) | "
         "**spec ratio iso-Si 8K** | mJ/token ROM / HBM-iso-Si 8K |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, x in enumerate(rows, 1):
        sh, r8, r32 = x["shape"], x["results"]["8192"], x["results"].get("32768", {})
        rr, hh, sp = r8["rom"], r8["hbm_iso_silicon"], r8["spec"]
        cfg = f"k{rr['k']} s{rr['s']}{' S' if rr['kv_spread'] else ''}"
        spc = (f"{fmt(sp['rom'][sp['rom_best']])} ({sp['rom_best']}) / {fmt(sp['hbm_iso_silicon'][sp['hbm_best']])} "
               f"({sp['hbm_best']})") if sp["rom_best"] else "no drafter"
        L.append(f"| {i} | {x['slug']} | {sh['active_params_B']:.1f} / {sh['total_params_B']:.1f} | "
                 f"{sh['sparsity_active_over_total']:.2f} | {sh['layers']} | {rr['dies']} ({rr['packages']}) | {cfg} | "
                 f"{fmt(rr['tok_s'])} | {fmt(hh['tok_s'])} ({r8['hbm_iso_silicon_dies']}) | **{r8['ratio_ar_iso_silicon']:.2f}x** | "
                 f"{('%.2fx' % r32['ratio_ar_iso_silicon']) if 'ratio_ar_iso_silicon' in r32 else 'n/a (ctx)'} | "
                 f"{r8['ratio_ar_iso_power']:.2f}x | {spc} | "
                 f"{('**%.2fx**' % sp['ratio_best_iso_silicon']) if sp['ratio_best_iso_silicon'] else '-'} | "
                 f"{fmt(rr['energy_mJ'])} / {fmt(hh['energy_mJ'])} |")
    L += ["", "## 2. Model shapes (from safetensors headers + config.json)", "",
          "| model | HF repo (profiled @rev) | license | total B | active B | layers | hidden | heads / KV / hd | attention "
          "| experts / top-k | 8-bit ROM GB = FP8 HBM GB | KV B/pos/layer kinds | KV MB at 8K / 32K / 128K (FP8) | MTP / drafters |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for x in rows:
        sh = x["shape"]
        kinds = "; ".join(f"{k}:{b:g}{('@' + str(w)) if w else ''}" for k, b, w in x["kv_bytes_per_position_per_layer"])
        kvs = " / ".join(fmt(x["kv"][c]["stored_MB"]) for c in ("8192", "32768", "131072"))
        mtp = sh["mtp"]
        dr = ", ".join(f"{k}: {v}" for k, v in sh["drafters_published"].items()) or "none found"
        mt = (f"native MTP x{mtp['native_modules']}" + ("" if mtp["weights_present"] else " (weights not released)")
              if mtp["native_modules"] else "no native MTP")
        rev = (x["revision"] or "")[:8]
        L.append(f"| {x['slug']} | {x['profiled_repo']}@{rev} | {x['license']} | {sh['total_params_B']:.1f} | "
                 f"{sh['active_params_B']:.2f} | {sh['layers']} | {sh['hidden']} | {sh['heads']} / {sh['kv_heads']} / "
                 f"{sh['head_dim']} | {', '.join(f'{k} {v}' for k, v in sh['attention_mix'].items())} | "
                 f"{sh['experts'] or '-'} / {sh['top_k'] or '-'} | {sh['rom_weight_GB_8bit']:.1f} | {kinds} | {kvs} | "
                 f"{mt}; {dr} |")
    L += ["", "## 3. ROM and HBM systems at 8K and 32K", "",
          "| model | ctx | ROM dies / stacks / mm2 | ROM us (body, weights, AR, attn) | ROM AR tok/s | ROM W | HBM iso-Si dies / mm2 "
          "| HBM iso-Si us (w-or-body, attn, AR) | HBM iso-Si tok/s | HBM iso-power dies / tok/s | ROM adopted-style k4 s4 tok/s (ratio) |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for x in rows:
        for c in ("8192", "32768"):
            r = x["results"].get(c, {})
            if "rom" not in r:
                continue
            rr, hh, hp, ad = r["rom"], r["hbm_iso_silicon"], r["hbm_iso_power"], r["rom_adopted_style_k4_s4"]
            pu, hu = rr["parts_us"], hh["parts_us"]
            L.append(f"| {x['slug']} | {int(c)//1024}K | {rr['dies']} / {rr['stacks']} / {fmt(rr['silicon_mm2'])} | "
                     f"{rr['T_us']:.0f} ({pu['body_fixed']:.0f}, {pu['weights']:.0f}, {pu['allreduce']:.0f}, {pu['attention']:.0f}) | "
                     f"{fmt(rr['tok_s'])} | {fmt(rr['power_W'])} | {hh['dies']} / {fmt(hh['silicon_mm2'])} | "
                     f"{hh['T_us']:.0f} ({hu['weights_or_body']:.0f}, {hu['attention']:.0f}, {hu['allreduce']:.0f}) | "
                     f"{fmt(hh['tok_s'])} | {hp['dies']} / {fmt(hp['tok_s'])} | {fmt(ad['rom_tok_s'])} ({ad['ratio']:.2f}x) |")
    path.write_text("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "results/uarch/rom_model_sweep_20261003/sweep.json")
    ap.add_argument("--stack-mm2", type=float, default=None, help="sensitivity: HBM stack silicon (default 1,150)")
    a = ap.parse_args()
    if a.stack_mm2:
        CAL["hbm_stack_mm2"] = a.stack_mm2
    q = load("qwen3-8b")
    calibrate(q)
    # calibration identities
    r = rom_design(q, 8192)
    assert abs(r["cycles"] - _near["headline"]["token_cycles"]) <= 0.002 * _near["headline"]["token_cycles"], r["cycles"]
    h = hbm_design(q, 8192, 2)
    assert abs(h["tok_s"] / 880.5 - 1) < 0.02, h["tok_s"]
    slugs = sorted(p.stem for p in PROF.glob("*.json"))
    rows = [evaluate(load(sl)) for sl in slugs]
    srcs = [NEAR, W15, ROOT / "configs/hardware/technology.json", Path(__file__),
            ROOT / "tools/rom_model_sweep_profile.py"] + sorted(PROF.glob("*.json"))
    rec = dict(schema="rom_model_sweep.v1", status="MODEL_ONLY_NOT_ADOPTED",
               scope="per-user AR and speculative decode, batch 1, ROM vs GPU-organised HBM at iso total silicon "
                     "(HBM stacks counted as silicon) and iso power; no RTL, no P&R, no inference",
               calibration=dict(CAL, identity=dict(qwen_rom_cycles=r["cycles"], qwen_rom_target=_near["headline"]["token_cycles"],
                                                  qwen_hbm_n2_tok_s=round(h["tok_s"], 1), qwen_hbm_target=880.5)),
               speculation=SPEC, contexts=list(CTXS), models=rows,
               sources={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in srcs})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=float) + "\n")
    write_md(rec, a.out.with_name("tables.md"))
    for x in sorted(rows, key=lambda x: -(x["results"]["8192"].get("ratio_ar_iso_silicon") or 0)):
        r8 = x["results"]["8192"]
        r32 = x["results"].get("32768", {})
        print(f"{x['slug']:22s} act/tot {x['shape']['active_params_B']:6.1f}/{x['shape']['total_params_B']:7.1f} "
              f"D {r8['rom']['dies']:4d} k{r8['rom']['k']}s{r8['rom']['s']}{'S' if r8['rom']['kv_spread'] else '-'} ROM {r8['rom']['tok_s']:7.0f} HBMiso {r8['hbm_iso_silicon']['tok_s']:7.0f}"
              f"(n{r8['hbm_iso_silicon_dies']}) x{r8['ratio_ar_iso_silicon']:5.2f} pw x{r8['ratio_ar_iso_power']:5.2f} "
              f"32K x{r32.get('ratio_ar_iso_silicon', float('nan')):5.2f} spec x{r8['spec']['ratio_best_iso_silicon']}")


if __name__ == "__main__":
    main()
