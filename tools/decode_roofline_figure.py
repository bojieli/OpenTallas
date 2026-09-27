#!/usr/bin/env python3
"""Decode roofline for ONE user (batch 1): commodity GPUs against the specialised
HBM accelerator and the ROM designs, for Qwen3-8B (8K, FP8 KV) and
DeepSeek-V4.1-Flash (1M primary, 200K secondary).

WHAT THE FIGURE SHOWS
---------------------
x = off-chip memory (HBM/GDDR) bandwidth devoted to the user, sustained, TB/s (log);
y = tokens per second for that user (log).

* Bandwidth roofs (diagonals): tok/s <= BW / bytes-per-token.  Two per model:
  weights + KV at the weight format named on the line, and KV only.  A ROM design
  keeps its weights on die, so its roof is the KV-only diagonal: the weight term
  leaves the roofline altogether.
* Synchronisation ceilings (horizontal): 1 / (N_sync x t_sync + N_dep x t_dep) with
  the MEASURED Blackwell primitives and the cited GB200 all-reduce floor / NCCL
  latencies of results/arch/sync_cost_table.json (validated against normative
  sources by the link-latency agent), drawn as a band; the same ceiling for our
  dataflow designs with our RTL/normative link costs from the same table.
* Points, each carrying an evidence class: measured, cited, calibrated, modelled,
  bound.  GPU points on the multi-device curves are MODELLED from measured
  primitives: T(N) = max(W / (N x BW), N_dep x t_dep) + N_coll x t_coll.  The model
  is deliberately optimistic for the GPU: it overlaps every on-chip boundary with
  the weight stream, charges no compute, no kernel launch, no MoE imbalance and no
  pipeline stage hop.

THE ATTRIBUTION LADDER (user-approved structure, binding)
---------------------------------------------------------
Per model and per metric (per-user tok/s at batch 1 -- primary; energy per token;
aggregate throughput at the fill batch), a fixed path with matched constraints:

  S0 GPU application or shipped-library baseline (measured/cited where available;
     otherwise modelled on cited communication latency);
  S1 the same GPUs, idealised runtime (fused persistent kernel, best measured
     all-reduce) -- the SOFTWARE gap;
  S2 the specialised HBM accelerator at no more silicon and no more HBM bandwidth
     than S1 -- SPECIALISATION (dataflow, cheap handoffs, short links, placement);
  S3 a specialised ROM accelerator at the same logic-area budget -- Qwen
     retains the core and format but has fewer HBM stacks than S2; V4.1 also
     changes die count and system topology.

The order is part of the definition: the factors are not independent (ROM without
specialisation is not a meaningful machine), so a multiplier is only defined at its
rung.  Every step keeps or REDUCES the silicon and memory bandwidth of the step
before it.  The V4.1 S2-to-S3 multiplier is a whole-design comparison, not an
isolated ROM weight-store effect.
Qwen3-8B needs one extra rung, S1f, because the ROM stores the HC1-class 3.5-bit
format: S1f re-prices the idealised GPU at that weight format. Qwen S2 has
B200-class bandwidth and S3 has six stacks; the matched six-stack HBM/ROM
comparison is reported separately. Steps S2 and S3 are conditional on the
design's open gates (the 1.087 GHz clock for V4.1; its collectives are priced with the exposure the RTL stage
bench measured, rack gate C7 not met).

INPUTS are read with `git show <commit>:<path>` at the pinned commits below (the
producing branches are not all merged); each input's sha256 is recorded.  Cited
constants carry their source strings.  Nothing here is fitted.

Usage:
  python3 tools/decode_roofline_figure.py            # write JSON + HTML
  python3 tools/decode_roofline_figure.py --check    # rebuild, compare with disk
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "results/arch/decode_roofline.json"
OUT_DIR = ROOT / "results/arch/figures"
SCHEMA = "opentallas.decode-roofline.v1"

# --------------------------------------------------------------------------- inputs

# Every input is this tree's committed record (commit None = the working tree's file, hashed into the record).
SOURCES = {
    # Qwen3 top-down spec + production power
    "qwen3_budget": (None, "results/arch/qwen3_budget.json"),
    # Qwen3 iso-area study + GPU calibration + local RTX PRO 6000
    "iso_qwen": ("b42f86065977850499995c874f2b630aa1aa5bf0", "results/roofline/iso_area/qwen3_8b.json"),   # NOT on main: pinned
    # validated synchronisation costs
    "sync": (None, "results/arch/sync_cost_table.json"),
    # V4.1 design-point model: the headline (measured collective exposure), best HBM comparator, ladder, spec budget
    "v41_lanes": (None, "results/arch/v41_lanes.json"),
    "v41_hbm_best": (None, "results/arch/v41_hbm_best.json"),
    "v41_ladder": (None, "results/arch/v41_latency_ladder.json"),
    "v41_budget": (None, "results/arch/arch_budget_v41_dp.json"),   # checkpoint weight precision (design-point base)
    # Validated rack links and switched HBM comparator, including wall energy.
    "v41_switched": (None, "results/arch/v41_hbm_switched.json"),
    # clocked-idle floor
    "idle_floor": (None, "results/roofline/gpu_clocked_idle_floor.json"),
}


def load_sources(sources: dict = SOURCES) -> tuple[dict, dict]:
    data, meta = {}, {}
    for key, (commit, path) in sources.items():
        raw = None
        try:
            if commit is None:
                raise FileNotFoundError(path)
            raw = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, check=True,
                                 capture_output=True).stdout
            origin = f"{commit[:8]}:{path}"
        except (subprocess.CalledProcessError, FileNotFoundError):
            local = ROOT / path
            if not local.exists():
                raise SystemExit(f"input {key}: {path} is not available")
            raw = local.read_bytes()
            origin = f"worktree:{path}"
        data[key] = json.loads(raw)
        meta[key] = {"from": origin, "sha256": hashlib.sha256(raw).hexdigest()}
    return data, meta


# ------------------------------------------------------------------ cited constants

def C(value, unit, evidence, source):
    return {"value": value, "unit": unit, "evidence": evidence, "source": source}


CITED = {
    "hbm_efficiency": C(0.90, "", "assumed (repository-wide)",
                        "configs/hardware/technology.json efficiencies.hbm_bandwidth: 0.90 of peak on ANY HBM device"),
    "b200_hbm_Bps": C(8.0e12, "B/s", "published", "NVIDIA Blackwell architecture page: B200 8 TB/s over 8 HBM3E stacks"),
    "b200_capacity_B": C(180e9, "B", "published", "configs/hardware/architectures.json NVIDIA-B200 weight_capacity_bytes_per_device"),
    "b200_logic_mm2": C(1600.0, "mm2", "approximate",
                        "results/roofline/iso_area/qwen3_8b.json area.b200: ~1,600 mm2, two reticle-limited dies (per-die area unpublished)"),
    "b300_hbm_Bps": C(7.75e12, "B/s", "published", "configs/hardware/architectures.json: DGX B300 62 TB/s aggregate / 8"),
    "h200_hbm_Bps": C(4.8e12, "B/s", "published", "NVIDIA H200 product page: 4.8 TB/s"),
    "rtx6000_Bps": C(1.792e12, "B/s", "published", "RTX PRO 6000 Blackwell (GB202) architecture whitepaper: GDDR7 512-bit 1.792 TB/s"),
    "hbm_capacity_utilization": C(0.90, "", "assumed", "configs/hardware/architectures.json hbm_capacity_utilization"),
    "dflash_b200": C({"ar": 230.0, "dflash": 1175.0, "tau": 8.01}, "tok/s", "cited (author measurement)",
                     "DFlash (Chen, Liang, Liu, ICML 2026, arXiv:2602.06036v2) Table 3: one B200, SGLang, concurrency 1, Qwen3-8B, MATH-500"),
    "lmsys_v4pro": C({"tok_s": 383.7, "tau": 5.0, "gpus": 8}, "tok/s", "cited (SGLang integration measurement)",
                     "LMSYS Org, 'DSpark in SGLang', https://www.lmsys.org/blog/2026-07-06-dspark-sglang/ (6 Jul 2026): "
                     "'383.7 tok/s at accept length ~5 at batch size 1 on DeepSeek-V4-Pro, TP=8, B300' (V4-Pro: 49 B active "
                     "parameters against V4.1-Flash's 13 B; context not stated)"),
    "megatron_ar_per_layer": C(2, "all-reduces per layer", "published",
                               "Shoeybi et al., Megatron-LM, arXiv:1909.08053, s3: two all-reduces per transformer layer in the forward pass"),
    "b200_decode_draw_w": C(689.0, "W", "measured (cited)", "arXiv:2609.11133: B200 decode natural draw 688-689 W"),
    "b200_tdp_hgx_w": C(1000.0, "W", "published", "NVIDIA Blackwell datasheet: HGX B200 1,000 W"),
    "v41_text_model_B": C(509.3e9, "B", "measured (safetensors headers)",
                          "docs/ARCH_SPEC_V41.md s2.1: text model 509.3 GB (Engram tables 202.8 GB, routed experts 288.8 GB)"),
    "qwen_on_chip_boundaries": C(220, "all-SM boundaries per token", "model on measured primitive",
                                 "results/arch/sync_cost_table.json row 'Per token, Qwen3-8B on one die (~220 all-SM boundaries)'"),
}

# Per-collective GPU latency (us) for a small all-reduce, from the sync-cost table's
# cross-package collective row (20 KB) and its references.
GPU_COLLECTIVE_US = {
    "sol_floor": (1.404, "GB200 speed-of-light all-reduce floor, 'independent of the number of ranks' [Shen et al., arXiv:2607.16100]"),
    "best_kernel": (2.37, "best measured low-latency kernel, 4 x GB200 [Shen et al., arXiv:2607.16100, Fig. 1]"),
    "nccl_2_27": (5.0, "NCCL 2.27 small-message all-reduce, GB200, 32 ranks, ~5 us [NVIDIA technical blog, 14 Jul 2025]"),
    "nccl_ring": (11.0, "NCCL ring, 4 x GB200 [Shen et al., Fig. 1]"),
}


# ---------------------------------------------------------------------- the models

def gpu_step_s(weight_kv_bytes: float, n: int, bw_sustained: float, n_dep: int, t_dep_s: float,
               n_coll: int, t_coll_s: float) -> float:
    """One token on N GPUs sharing the user's bytes evenly (TP/EP, no pipeline).

    Optimistic for the GPU: every on-chip dependent boundary overlaps the weight
    stream (max, not sum); collectives sit on the dependent path (they cannot be
    hidden behind the stream that produces their operand).  No compute, launch or
    MoE-imbalance term.
    """
    stream = weight_kv_bytes / (n * bw_sustained)
    chain = n_dep * t_dep_s
    coll = n_coll * t_coll_s if n > 1 else 0.0
    return max(stream, chain) + coll


def rate(step_s: float, tokens_per_step: float = 1.0) -> float:
    return tokens_per_step / step_s


def step(key, label, value, unit, evidence, basis, matching="", prev=None):
    d = {"step": key, "label": label, "value": value, "unit": unit, "evidence": evidence,
         "basis": basis, "matching": matching}
    if prev is not None and value is not None and prev.get("value") is not None:
        lower_is_better = unit.startswith("mJ") or unit.startswith("J")
        d["multiplier"] = (prev["value"] / value) if lower_is_better else (value / prev["value"])
    else:
        d["multiplier"] = None
    return d


def ladder(steps: list[dict]) -> list[dict]:
    """Chain multipliers: each step relative to the previous step that has a value."""
    out, prev = [], None
    for s in steps:
        s = step(**s, prev=prev)
        out.append(s)
        if s["value"] is not None:
            prev = s
    return out


def build_qwen(src: dict) -> dict:
    qb, iq, sy = src["qwen3_budget"], src["iso_qwen"], src["sync"]
    eff = CITED["hbm_efficiency"]["value"]
    b200 = CITED["b200_hbm_Bps"]["value"] * eff
    hdc = qb["hbm_design"]["stacks"] * qb["hbm_design"]["stack_bytes_s"] * qb["hbm_design"]["efficiency"]
    cmp8k = qb["hbm_comparator"]["8192"]
    W = {"bf16": cmp8k["bf16"]["bytes_per_token"], "fp8": cmp8k["fp8"]["bytes_per_token"],
         "rom35": cmp8k["rom_format_3.5b"]["bytes_per_token"]}
    kv = qb["requirements"]["kv_hbm"]["bytes_per_token"]
    t_dep = next(r for r in sy["rows"] if r["event"].startswith("On-chip all-unit gather"))["gpu"]["value"] * 1e-9
    t_dep_ours = next(r for r in sy["rows"] if r["event"].startswith("On-chip all-unit gather"))["ot"]["value"] * 1e-9
    n_dep = CITED["qwen_on_chip_boundaries"]["value"]
    L = qb["shape"]["L"]
    n_coll = CITED["megatron_ar_per_layer"]["value"] * L + 1  # + the vocabulary-split logits gather
    tc = {k: v[0] * 1e-6 for k, v in GPU_COLLECTIVE_US.items()}

    def g(fmt, n, t="best_kernel"):
        return rate(gpu_step_s(W[fmt], n, b200, n_dep, t_dep, n_coll, tc[t]))

    pp = qb["power_production"]
    rom_ar = pp["rom"]["ar_batch1"]["tokens_s"]
    rom_df = pp["rom"]["dflash_tau4.1_block3"]["tokens_s"]
    hdc_bf16 = qb["hbm_comparator"]["8192"]["bf16"]["tokens_s"]
    hdc_35 = qb["hbm_comparator"]["8192"]["rom_format_3.5b"]["tokens_s"]
    hdc_35_df = qb["dflash"]["hbm"]["rom_format_3.5b"]["tokens_s_at_tau_central"]
    hdc_bf16_df = qb["dflash"]["hbm"]["bf16"]["tokens_s_at_tau_central"]
    auto = iq["contexts"]["8192"]["autoregressive"]
    loc = iq["local_gpu_rtx_pro_6000"]["concurrency_1"]
    dfl = CITED["dflash_b200"]["value"]
    s1 = g("bf16", 1)
    s1f = g("rom35", 1)
    s2 = rate(max(W["rom35"] / b200, n_dep * t_dep_ours))  # specialised core at the B200's bandwidth
    tp8 = {t: g("bf16", 8, t) for t in tc}
    tp8_35 = g("rom35", 8)
    rom_sweep_ceiling = qb["budget"]["ceiling_tokens_s"]
    kv_floor = hdc / kv
    tau = qb["dflash"]["hbm"]["bf16"].get("tau", 4.1)

    points = [
        # key, label, x (TB/s), y, evidence, family, spec, basis
        dict(key="rtx_bf16", label="RTX PRO 6000, BF16", x=CITED["rtx6000_Bps"]["value"] * eff / 1e12, y=loc["bf16"]["ar_tok_s"],
             evidence="measured", family="gpu", spec=False, basis="this machine, MATH-500, short context (iso_qwen local_gpu_rtx_pro_6000)"),
        dict(key="rtx_fp8", label="RTX PRO 6000, FP8", x=CITED["rtx6000_Bps"]["value"] * eff / 1e12, y=loc["fp8"]["ar_tok_s"],
             evidence="measured", family="gpu", spec=False, basis="this machine, MATH-500, short context"),
        dict(key="rtx_bf16_dflash", label="RTX PRO 6000 + DFlash", x=CITED["rtx6000_Bps"]["value"] * eff / 1e12, y=loc["bf16"]["dflash_tok_s"],
             evidence="measured", family="gpu", spec=True, basis=f"tau {loc['bf16']['dflash_tau']:.2f}; host-bound on a loaded host"),
        dict(key="h200_bf16", label="H200, BF16", x=CITED["h200_hbm_Bps"]["value"] * eff / 1e12, y=auto["h200_bf16"]["tok_s"],
             evidence="calibrated", family="gpu", spec=False, basis="NIM H200 two-point fit, shape-adjusted to Qwen3-8B at 8K (iso_qwen gpu_calibration)"),
        dict(key="b200_bf16", label="B200, SGLang, BF16", x=b200 / 1e12, y=dfl["ar"], evidence="cited", family="gpu", spec=False,
             basis=CITED["dflash_b200"]["source"]),
        dict(key="b200_dflash", label="B200 + DFlash", x=b200 / 1e12, y=dfl["dflash"], evidence="cited", family="gpu", spec=True,
             basis=f"same source; tau {dfl['tau']} (MATH-500), not the 4.1 used for our designs"),
        dict(key="b200_ideal_bf16", label="B200 idealised, BF16", x=b200 / 1e12, y=s1, evidence="modelled", family="gpu", spec=False,
             basis="bandwidth roof at 0.90; 220 measured all-SM boundaries overlapped"),
        dict(key="b200_ideal_rom35", label="B200 idealised, 3.5-bit", x=b200 / 1e12, y=s1f, evidence="modelled", family="gpu", spec=False,
             basis="as above at the ROM's weight format (byte-proportional; no GPU has shown it: on an H20 AWQ-INT4 ran 0.96x FP8)"),
        dict(key="nvl72_tp8_bf16", label="NVL72 slice, TP8, BF16", x=8 * b200 / 1e12, y=tp8["best_kernel"], evidence="modelled", family="gpu", spec=False,
             basis=f"TP8 (8 KV heads: the largest legal split), {n_coll} all-reduces at the best measured kernel 2.37 us"),
        dict(key="hdc_bf16", label="HDC-HBM, BF16", x=hdc / 1e12, y=hdc_bf16, evidence="modelled", family="hbm", spec=False,
             basis="one reticle, 6 HBM3E stacks at 0.90 (qwen3_budget hbm_comparator)"),
        dict(key="hdc_rom35", label="HDC-HBM, 3.5-bit", x=hdc / 1e12, y=hdc_35, evidence="modelled", family="hbm", spec=False,
             basis="same machine at the ROM's weight format"),
        dict(key="hdc_rom35_dflash", label="HDC-HBM + DFlash", x=hdc / 1e12, y=hdc_35_df, evidence="modelled", family="hbm", spec=True,
             basis=f"tau {tau} (measured on real Qwen3-8B, 561 blocks)"),
        dict(key="hdc_matched", label="S2: HDC core at B200 bandwidth", x=b200 / 1e12, y=s2, evidence="modelled", family="hbm", spec=False,
             basis="specialised core on a B200-sized package (8 stacks, 7.2 TB/s), 3.5-bit weights, 220 x 4.8 ns handoffs"),
        dict(key="rom", label="ROM reticle", x=hdc / 1e12, y=rom_ar, evidence="calibrated", family="rom", spec=False,
             basis="RTL-calibrated sequencer model at spec widths, 123,301 cycles at 1.099 GHz; KV-bound (qwen3_budget power_production)"),
        dict(key="rom_dflash", label="ROM + DFlash (m=3)", x=hdc / 1e12, y=rom_df, evidence="modelled", family="rom", spec=True,
             basis="tau 4.1, block 3, three MAC copies per weight read in the freed SRAM; conditional on the lane copies"),
    ]
    roofs = [
        dict(key="roof_bf16", label="weights BF16 + KV", bytes_per_token=W["bf16"]),
        dict(key="roof_rom35", label="weights 3.5-bit + KV", bytes_per_token=W["rom35"]),
        dict(key="roof_kv", label="KV only (ROM)", bytes_per_token=kv, rom=True),
    ]
    ceilings = [
        dict(key="gpu_onchip", family="gpu", label="GPU on-chip sync, 1 die",
             y=1.0 / (n_dep * t_dep), evidence="model on measured primitive",
             basis=f"{n_dep} all-SM boundaries x {t_dep*1e9:.0f} ns (GB202 measured)"),
        dict(key="rom_sweep", family="rom", label="ROM weight sweep", y=rom_sweep_ceiling, evidence="modelled",
             basis="57,740 cycles: one weight per lane per cycle"),
        dict(key="ours_onchip", family="rom", label="our on-chip sync", y=1.0 / (n_dep * t_dep_ours),
             evidence="RTL-derived", basis=f"{n_dep} x {t_dep_ours*1e9:.1f} ns"),
    ]
    curves = [
        dict(key="gpu_tp_best", family="gpu", label="B200 TP-N, best kernel",
             pts=[(n * b200 / 1e12, g("bf16", n)) for n in (1, 2, 4, 8)]),
        dict(key="gpu_tp_band", family="gpu", label="TP-N band: SoL floor to NCCL 2.27", band=True,
             lo=[(n * b200 / 1e12, g("bf16", n, "nccl_2_27")) for n in (1, 2, 4, 8)],
             hi=[(n * b200 / 1e12, g("bf16", n, "sol_floor")) for n in (1, 2, 4, 8)]),
    ]
    arrows = [("b200_bf16", "b200_ideal_bf16", "software"), ("b200_ideal_bf16", "b200_ideal_rom35", "format"),
              ("hdc_matched", "rom", "ROM")]

    # ---- ladders
    m_draw = CITED["b200_decode_draw_w"]["value"]
    per_user = ladder([
        dict(key="S0", label="B200, SGLang, BF16 weights", value=dfl["ar"], unit="tok/s", evidence="cited",
             basis=CITED["dflash_b200"]["source"], matching="2 reticles of logic, 8 HBM3E stacks (7.2 TB/s sustained)"),
        dict(key="S1", label="same B200, idealised runtime", value=s1, unit="tok/s", evidence="modelled on measured primitives",
             basis="bandwidth roof at 0.90 with 220 measured all-SM boundaries overlapped (GPU-optimistic)", matching="same GPU"),
        dict(key="S1f", label="same, weights at the ROM's 3.5-bit format", value=s1f, unit="tok/s", evidence="modelled",
             basis="byte-proportional; not demonstrated on a GPU", matching="same GPU, weight format matched to the ROM"),
        dict(key="S2", label="specialised HBM core, same bandwidth", value=s2, unit="tok/s", evidence="modelled (RTL-calibrated handoff)",
             basis="bandwidth roof; 220 handoffs at 4.8 ns (RTL)", matching="<= B200 logic area, = B200 HBM bandwidth, 3.5-bit"),
        dict(key="S3", label="same core, weights in ROM", value=rom_ar, unit="tok/s", evidence="calibrated model",
             basis="RTL-calibrated sequencer model; KV-bound on 6 stacks", matching="one reticle + 6 stacks for KV (less than S2)"),
    ])
    energy = ladder([
        dict(key="S0", label="B200, SGLang, BF16", value=m_draw / dfl["ar"] * 1e3, unit="mJ/token", evidence="measured draw / cited rate",
             basis="689 W measured B200 decode draw [arXiv:2609.11133] / 230 tok/s [DFlash]; different workloads", matching=""),
        dict(key="S1", label="idealised runtime, BF16", value=m_draw / s1 * 1e3, unit="mJ/token", evidence="modelled",
             basis="draw held at the measured 689 W", matching="same GPU"),
        dict(key="S1f", label="idealised, 3.5-bit", value=m_draw / s1f * 1e3, unit="mJ/token", evidence="modelled",
             basis="draw held at 689 W", matching="same GPU"),
        dict(key="S2", label="HDC-HBM, 3.5-bit (iso-area, 6 stacks)", value=pp["hbm_comparator"]["rom35_batch1"]["energy_per_token_mj"],
             unit="mJ/token", evidence="modelled (production power inputs)",
             basis="package energy; HBM priced at the conservative 13.1 pJ/bit system figure, so S1f->S2 mixes a measured GPU draw with a conservative model",
             matching="one reticle, 6 stacks"),
        dict(key="S3", label="ROM reticle", value=pp["rom"]["ar_batch1"]["energy_per_token_mj"], unit="mJ/token",
             evidence="modelled (production power inputs)", basis="same power model as S2: the matched-format ratio",
             matching="one reticle, 6 stacks"),
    ])
    kv_bound_b200 = b200 / kv
    aggregate = ladder([
        dict(key="S0", label="B200, real software", value=None, unit="tok/s", evidence="not available",
             basis="no measured Qwen3-8B 8K fill-batch B200 figure in the repository", matching=""),
        dict(key="S1", label="B200, KV-stream bound", value=kv_bound_b200, unit="tok/s", evidence="bound",
             basis="weights amortised over the batch; 7.2 TB/s / 604 MB of FP8 KV per token", matching="8 stacks"),
        dict(key="S2", label="HDC-HBM, 3.5-bit, batch 128", value=pp["hbm_comparator"]["rom35_batch128"]["tokens_s"], unit="tok/s",
             evidence="modelled", basis="qwen3_budget power_production", matching="6 stacks (0.75x the B200's KV bandwidth)"),
        dict(key="S3", label="ROM reticle, batch 128", value=pp["rom"]["batch128"]["tokens_s"], unit="tok/s",
             evidence="modelled", basis="KV-bound: 5.4 TB/s / 604 MB", matching="6 stacks"),
    ])
    spec_rows = [
        dict(machine="B200, SGLang (measured)", ar=dfl["ar"], spec=dfl["dflash"], tau=dfl["tau"], evidence="cited"),
        dict(machine="B200 idealised, BF16 (bound: tau x AR)", ar=s1, spec=tau * s1, tau=tau, evidence="bound"),
        dict(machine="HDC-HBM, 3.5-bit", ar=hdc_35, spec=hdc_35_df, tau=tau, evidence="modelled"),
        dict(machine="HDC-HBM, BF16", ar=hdc_bf16, spec=hdc_bf16_df, tau=tau, evidence="modelled"),
        dict(machine="ROM reticle (m = 3 lane copies)", ar=rom_ar, spec=rom_df, tau=tau, evidence="modelled"),
    ]
    return dict(
        title="Qwen3-8B, 8K context, FP8 KV, one user",
        x_range=[1.0, 100.0], y_range=[50.0, 1.0e6],
        bytes_per_token={"weights_bf16_plus_kv": W["bf16"], "weights_fp8_plus_kv": W["fp8"],
                         "weights_rom35_plus_kv": W["rom35"], "kv_fp8": kv},
        gpu_model=dict(n_dep=n_dep, t_dep_ns=t_dep * 1e9, n_coll_tp=n_coll, t_coll_us={k: v[0] for k, v in GPU_COLLECTIVE_US.items()},
                       tp8_bf16_tok_s=tp8, tp8_rom35_tok_s=tp8_35, kv_floor_rom_tok_s=kv_floor),
        points=points, roofs=roofs, ceilings=ceilings, curves=curves, arrows=arrows,
        ladders=dict(per_user=per_user, energy=energy, aggregate=aggregate), speculation=spec_rows,
    )


def build_v41(src: dict) -> dict:
    ln, hb, ld, bu, sy, idle, switched = (
        src["v41_lanes"], src["v41_hbm_best"], src["v41_ladder"], src["v41_budget"],
        src["sync"], src["idle_floor"], src["v41_switched"])
    eff = CITED["hbm_efficiency"]["value"]
    b200 = CITED["b200_hbm_Bps"]["value"] * eff
    out = {}
    per_ctx = {}
    for ctx in ("1048576", "200000"):
        by = bu["workload"][ctx]["totals"]["bytes"]
        w = by["rom"]
        kv = by["kv_sram"] + by["kv_hbm"] + by["idx"] + by["engram"]
        per_ctx[ctx] = dict(weights=w, kv=kv, total=w + kv)
    row6 = next(r for r in sy["rows"] if r["event"].startswith("Per token, V4.1"))
    n_coll = sy["ladder"]["collectives"]
    ours_sync_us = (sy["ladder"]["collective_latency_us"] + sy["ladder"].get("collective_exposed_bytes_us", 0.0)
                    + sy["ladder"]["pipeline_hops_us"])
    tc = {k: v[0] * 1e-6 for k, v in GPU_COLLECTIVE_US.items()}
    cap = CITED["b200_capacity_B"]["value"] * CITED["hbm_capacity_utilization"]["value"]
    n_min = math.ceil(CITED["v41_text_model_B"]["value"] / cap)
    comp = hb["comparator"]
    comp_bw_total = comp["dies"] * comp["bw_Bps_per_die"]
    comp_logic = comp["dies"] * comp["logic_mm2_per_die"]
    n_iso = math.ceil(max(comp_bw_total / b200, comp_logic / CITED["b200_logic_mm2"]["value"]))

    def g(ctx, n, t="best_kernel"):
        # GPU: weights + KV streamed over N GPUs; collectives of the same graph; no stage hops,
        # no on-chip boundaries (both GPU-optimistic).
        return rate(gpu_step_s(per_ctx[ctx]["total"], n, b200, 0, 0.0, n_coll, tc[t]))

    ctx = "1048576"
    dp = ln["design_point"]
    bd = dp[ctx]["breakdown_us"]                     # the headline token (measured collective exposure)
    rom_x = per_ctx[ctx]["kv"] / (bd["kv_sweep"] * 1e-6) / 1e12
    switched_case = switched["configs"][switched["headline_config"]][ctx]
    grid = switched_case["grid"]
    hbm_ar = switched_case["best_ar"]["rate"]
    hbm_mtp = switched_case["best_mtp"]["rate"]
    g_ar = switched_case["best_ar"]["G"]
    g_mtp = switched_case["best_mtp"]["G"]
    tau = hb["tau"]
    s0 = g(ctx, n_iso, "nccl_2_27")
    s1 = g(ctx, n_iso)
    s1_sol = g(ctx, n_iso, "sol_floor")
    nvl72 = g(ctx, 72)
    lm = CITED["lmsys_v4pro"]["value"]
    points = [
        dict(key="gpu_s0", label=f"{n_iso} x B200, modelled NCCL 2.27", x=n_iso * b200 / 1e12, y=s0, evidence="modelled on cited latency",
             family="gpu", spec=False, basis=f"{n_coll} collectives x ~5 us (NCCL 2.27) + weight/KV stream over {n_iso} GPUs"),
        dict(key="gpu_s1", label=f"{n_iso} x B200, best kernel", x=n_iso * b200 / 1e12, y=s1, evidence="modelled on measured primitives",
             family="gpu", spec=False, basis=f"{n_coll} collectives x 2.37 us (best measured GB200 kernel)"),
        dict(key="gpu_nvl72", label="NVL72, 72 x B200", x=72 * b200 / 1e12, y=nvl72, evidence="modelled on measured primitives",
             family="gpu", spec=False, basis="the whole rack on one user: sync-bound, so 72 GPUs add only 2%"),
        dict(key="gpu_mtp_bound", label="B200 set + MTP, bound", x=n_iso * b200 / 1e12, y=tau * s1, evidence="bound",
             family="gpu", spec=True, basis=f"tau x AR (tau {tau}): free draft and verify; an upper bound"),
        dict(key="v4pro_b300", label="V4-Pro + DSpark, 8 x B300", x=lm["gpus"] * CITED["b300_hbm_Bps"]["value"] * eff / 1e12,
             y=lm["tok_s"], evidence="cited", family="gpu", spec=True, basis=CITED["lmsys_v4pro"]["source"]),
        dict(key="hbm_ar", label=f"HBM comparator (G={g_ar})", x=g_ar * comp["bw_Bps_per_die"] / 1e12, y=hbm_ar,
             evidence="modelled (RTL-calibrated + validated links)", family="hbm", spec=False,
             basis=f"{comp['dies']} dies x {comp['stacks_per_die']} HBM3E stacks, equal logic area to the ROM array; best tensor group G={g_ar}"),
        dict(key="hbm_mtp", label=f"HBM comparator + MTP (G={g_mtp})", x=g_mtp * comp["bw_Bps_per_die"] / 1e12, y=hbm_mtp,
             evidence="modelled", family="hbm", spec=True, basis=f"DSpark gamma 5, tau {tau}, m = {switched_case['best_mtp']['m']}"),
        dict(key="rom_ar", label="ROM array", x=rom_x, y=dp[ctx]["ar"], evidence="modelled, C7 measured", family="rom", spec=False,
             basis="rack lane-split design point with the RTL stage bench's measured collective exposure (v41_lanes "
                   "design_point); conditional on the 1.087 GHz clock"),
        dict(key="rom_mtp", label="ROM array + MTP", x=rom_x, y=dp[ctx]["mtp"], evidence="modelled, C7 measured", family="rom", spec=True,
             basis=f"DSpark gamma 5, tau {tau}"),
    ]
    roofs = [
        dict(key="roof_w", label="weights (checkpoint dtypes) + KV", bytes_per_token=per_ctx[ctx]["total"]),
        dict(key="roof_kv", label="KV + index only (ROM)", bytes_per_token=per_ctx[ctx]["kv"], rom=True),
    ]
    comp_sync = next(e for e in grid if e["G"] == g_ar)["breakdown_us"]
    ceilings = [
        dict(key="gpu_sync", family="gpu", label=f"GPU sync, {n_coll} collectives", y=1.0 / (n_coll * tc["best_kernel"]),
             band=[1.0 / (n_coll * tc["nccl_ring"]), 1.0 / (n_coll * tc["sol_floor"])],
             evidence="model on measured primitives", basis="best kernel 2.37 us; band NCCL ring 11 us to the SoL floor 1.404 us"),
        dict(key="hbm_sync", family="hbm", label=f"comparator sync at G={g_ar}",
             y=1.0 / ((comp_sync["collective_latency"] + comp_sync["pipeline_hops"]) * 1e-6), evidence="modelled",
             basis="its collectives at span G on the realistic fabric"),
        dict(key="rom_chain", family="rom", label="ROM compiled chain", y=1.0 / ((bd["compute_chain"] + bd["control"]) * 1e-6),
             evidence="modelled", basis="compute chain + control of the design point's headline token"),
        dict(key="ours_sync", family="rom", label="ROM array sync", y=1.0 / (ours_sync_us * 1e-6), evidence="model, normative basis",
             basis=f"{sy['ladder']['collective_latency_us']:.1f} us collectives + "
                   f"{sy['ladder'].get('collective_exposed_bytes_us', 0.0):.1f} us measured exposed collective bytes + "
                   f"{sy['ladder']['pipeline_hops_us']:.2f} us stage hops (209 ns cable tier)"),
    ]
    curves = [
        dict(key="gpu_best", family="gpu", label="B200 set, best kernel",
             pts=[(n * b200 / 1e12, g(ctx, n)) for n in (n_min, 8, 16, 32, n_iso, 72)]),
        dict(key="gpu_band", family="gpu", label="band: SoL floor to NCCL 2.27", band=True,
             lo=[(n * b200 / 1e12, g(ctx, n, "nccl_2_27")) for n in (n_min, 8, 16, 32, n_iso, 72)],
             hi=[(n * b200 / 1e12, g(ctx, n, "sol_floor")) for n in (n_min, 8, 16, 32, n_iso, 72)]),
        dict(key="hbm_grid", family="hbm", label="comparator vs tensor group G",
             pts=[(e["G"] * comp["bw_Bps_per_die"] / 1e12, e["ar"]) for e in grid]),
        dict(key="hbm_grid_mtp", family="hbm", label="comparator + MTP vs G", spec=True,
             pts=[(e["G"] * comp["bw_Bps_per_die"] / 1e12, e["mtp_m6"]) for e in grid]),
    ]
    arrows = [("gpu_s0", "gpu_s1", "software"), ("gpu_s1", "hbm_ar", "specialisation"), ("hbm_ar", "rom_ar", "ROM array")]

    en = switched["energy"][ctx]
    draw = CITED["b200_decode_draw_w"]["value"]
    idle_w = idle["four_part_mean"]["mean_fraction"] * CITED["b200_tdp_hgx_w"]["value"]
    per_user = ladder([
        dict(key="S0", label=f"{n_iso} x B200, modelled NCCL", value=s0, unit="tok/s", evidence="modelled on cited latency",
             basis="no published V4.1-Flash batch-1 GPU figure exists; nearest: V4-Pro + DSpark 383.7 tok/s on 8 x B300 [LMSYS]",
             matching=f"{n_iso} B200: >= the comparator's logic area ({comp_logic:,.0f} mm2) and HBM bandwidth ({comp_bw_total/1e12:.0f} TB/s)"),
        dict(key="S1", label="same GPUs, best measured all-reduce", value=s1, unit="tok/s", evidence="modelled on measured primitives",
             basis=f"fixed 209-collective graph, 2.37 us per collective; against the SoL floor 1.404 us: {s1_sol:,.0f} tok/s; a different GPU mapping could change the graph", matching="same GPUs"),
        dict(key="S2", label="specialised HBM accelerator", value=hbm_ar, unit="tok/s", evidence="modelled (RTL-calibrated + validated links)",
             basis=f"best switched HBM comparator, G = {g_ar}", matching=f"{comp['dies']} dies, {comp_logic:,.0f} mm2 logic, {comp_bw_total/1e12:.0f} TB/s"),
        dict(key="S3", label="equal-area specialised ROM array", value=dp[ctx]["ar"], unit="tok/s", evidence="modelled, C7 measured",
             basis="ROM array design point, collective exposure measured in the RTL stage bench (gate C7 not met; "
                   "full overlap would give the conditional point); open gate: 1.087 GHz clock",
             matching="equal logic area (188 x 328.9 mm2); die count, topology, HBM allocation and weight placement all differ"),
    ])
    energy = ladder([
        dict(key="S0", label=f"{n_iso} x B200, modelled NCCL", value=n_iso * draw / s0, unit="J/token", evidence="modelled",
             basis=f"{n_iso} x 689 W measured decode draw; a sync-bound GPU may draw less: at the clocked-idle floor "
                   f"({idle_w:.0f} W) {n_iso * idle_w / s0:.1f} J", matching=""),
        dict(key="S1", label="best measured all-reduce", value=n_iso * draw / s1, unit="J/token", evidence="modelled",
             basis=f"at the clocked-idle floor {n_iso * idle_w / s1:.2f} J", matching="same GPUs"),
        dict(key="S2", label="HBM comparator", value=en["b1"]["hbm"]["wall_j"], unit="J/token", evidence="modelled",
             basis="dynamic + static + switches + wall overhead (v41_hbm_switched energy b1)", matching=""),
        dict(key="S3", label="ROM array", value=en["b1"]["rom"]["wall_j"], unit="J/token", evidence="modelled, C7 measured",
             basis="same wall energy model", matching=""),
    ])
    aggregate = ladder([
        dict(key="S0", label="B200 set, real software", value=None, unit="tok/s", evidence="not available",
             basis="no measured or cited V4.1 throughput at 1M", matching=""),
        dict(key="S1", label="B200 set, idealised", value=None, unit="tok/s", evidence="not derived",
             basis="needs a routed-expert-union and KV-capacity model for the GPU set; not built", matching=""),
        dict(key="S2", label="HBM comparator, fill batch (28 users)", value=en["fill28"]["hbm"]["aggregate_tokens_s"], unit="tok/s",
             evidence="modelled", basis=f"per user {en['fill28']['hbm']['tokens_s_per_user']:,.0f} tok/s; at 1,024 users "
                                        f"{en['sat1024']['hbm']['aggregate_tokens_s']:,.0f}", matching=""),
        dict(key="S3", label="ROM array, fill batch (28 users)", value=en["fill28"]["rom"]["aggregate_tokens_s"], unit="tok/s",
             evidence="modelled, C7 measured", basis=f"per user {en['fill28']['rom']['tokens_s_per_user']:,.0f} tok/s; at 1,024 users "
                                                     f"{en['sat1024']['rom']['aggregate_tokens_s']:,.0f}", matching=""),
    ])
    secondary = {}
    c2 = "200000"
    secondary[c2] = dict(
        gpu_s0=g(c2, n_iso, "nccl_2_27"), gpu_s1=g(c2, n_iso), gpu_sol=g(c2, n_iso, "sol_floor"),
        hbm_ar=switched["configs"][switched["headline_config"]][c2]["best_ar"]["rate"],
        hbm_mtp=switched["configs"][switched["headline_config"]][c2]["best_mtp"]["rate"],
        rom_ar=dp[c2]["ar"], rom_mtp=dp[c2]["mtp"],
        bytes_per_token=per_ctx[c2],
    )
    spec_rows = [
        dict(machine="V4-Pro + DSpark, 8 x B300 (different model)", ar=None, spec=lm["tok_s"], tau=lm["tau"], evidence="cited"),
        dict(machine=f"{n_iso} x B200, best kernel (bound: tau x AR)", ar=s1, spec=tau * s1, tau=tau, evidence="bound"),
        dict(machine="HBM comparator", ar=hbm_ar, spec=hbm_mtp, tau=tau, evidence="modelled"),
        dict(machine="ROM array", ar=dp[ctx]["ar"], spec=dp[ctx]["mtp"], tau=tau, evidence="modelled, C7 measured"),
    ]
    out = dict(
        title="DeepSeek-V4.1-Flash, 1M context, one user",
        x_range=[10.0, 1000.0], y_range=[100.0, 1.0e5],
        bytes_per_token=per_ctx,
        gpu_model=dict(n_collectives=n_coll, n_min_by_capacity=n_min, n_iso=n_iso, t_coll_us={k: v[0] for k, v in GPU_COLLECTIVE_US.items()},
                       sol_floor_tok_s=s1_sol, sync_table_per_token_us=row6["gpu"]["value"],
                       note="GPU pays only the weight/KV stream and the collectives of the ROM array's graph (209 per token): no "
                            "on-chip boundaries, no compute, no stage hops (the sync table's 517 us includes 27 hops; dropped here)"),
        points=points, roofs=roofs, ceilings=ceilings, curves=curves, arrows=arrows,
        ladders=dict(per_user=per_user, energy=energy, aggregate=aggregate), speculation=spec_rows,
        secondary=secondary,
    )
    return out


FINDINGS = (
    "Why GPUs plateau. A GPU's per-user rate is bounded twice: by the bandwidth roof of the devices serving the user "
    "(tokens/s <= bandwidth / bytes per token) and by a synchronisation ceiling that more devices cannot raise. On one "
    "B200, the Qwen3-8B modeled 8K roof is {q_s1:,.0f} tok/s at BF16; the cited {q_s0:,.0f}-tok/s application point has no verified 8K context match. Spreading it "
    "over an NVL72 slice (TP8, the largest split its 8 KV heads allow) raises the roof eightfold but adds {q_ncoll} "
    "dependent all-reduces, so the idealised rate stops at {q_tp8:,.0f}. DeepSeek-V4.1-Flash never reaches its roof on "
    "GPUs under the modeled collective graph: its {v_ncoll} collectives per token at the best measured GB200 kernel (2.37 us) cap it near {v_ceil:,.0f} tok/s "
    "however many GPUs are added ({v_s1:,.0f} on {v_n} B200s, {v_72:,.0f} on all 72 of an NVL72; {v_sol:,.0f} even at the "
    "speed-of-light collective floor). "
    "The specialised HBM accelerator raises the synchronisation ceiling, not the roof: with compiled handoffs (4.8 ns "
    "on chip against 1.0 us) and in-switch reduction it reaches {v_s2:,.0f} tok/s on V4.1 at roughly matched "
    "HBM bandwidth ({v_x_s2:.0f} against {v_x_s1:.0f} TB/s), {v_m2:.2f}x the best-kernel GPU; on a "
    "single die at the same modeled bandwidth roof, this model assigns no added rate to the specialised HBM core ({q_m2:.2f}x on Qwen3-8B). "
    "ROM removes the weight term: the design leaves the weights-plus-KV roof for the KV-only roof, {q_kvroof:,.0f} tok/s "
    "on six stacks for Qwen3-8B at 8K, where the ROM reticle sits ({q_s3:,.0f}, {q_m3:.1f}x the same core streaming "
    "3.5-bit weights at the B200's bandwidth); for V4.1 it is bound by its compiled chain and reaches {v_s3:,.0f} tok/s, "
    "{v_m3:.1f}x the equal-area HBM array ({v_s3_mtp:,.0f} with MTP); this V4.1 step also changes topology and HBM allocation. End to end, S0 -> S3 is {q_tot:.0f}x for Qwen3-8B "
    "(illustrative because S0 context is unverified; {q_fmt:.1f}x is the modeled format step) and a modeled {v_tot:.1f}x for V4.1 at 1M; the steps are ordered by definition and "
    "S2-S3 are conditional on the design's open gates. The same roofline shows where ROM does not help: at 8K and a full "
    "batch, aggregate throughput is KV-bound on every machine, and the B200's eight stacks out-stream the ROM reticle's six "
    "({q_agg_b200:,.0f} against {q_agg_rom:,.0f} tok/s)."
)


def findings(q: dict, v: dict) -> str:
    qu = {s["step"]: s for s in q["ladders"]["per_user"]}
    vu = {s["step"]: s for s in v["ladders"]["per_user"]}
    qa = {s["step"]: s for s in q["ladders"]["aggregate"]}
    vp = {p["key"]: p for p in v["points"]}
    vc = {c["key"]: c for c in v["ceilings"]}
    return FINDINGS.format(
        q_s1=qu["S1"]["value"], q_s0=qu["S0"]["value"], q_ncoll=q["gpu_model"]["n_coll_tp"],
        q_tp8=q["gpu_model"]["tp8_bf16_tok_s"]["best_kernel"], v_ncoll=v["gpu_model"]["n_collectives"],
        v_ceil=vc["gpu_sync"]["y"], v_s1=vu["S1"]["value"], v_n=v["gpu_model"]["n_iso"], v_72=vp["gpu_nvl72"]["y"],
        v_sol=v["gpu_model"]["sol_floor_tok_s"], v_s2=vu["S2"]["value"], v_x_s2=vp["hbm_ar"]["x"], v_x_s1=vp["gpu_s1"]["x"],
        v_m2=vu["S2"]["multiplier"], q_m2=qu["S2"]["multiplier"],
        q_kvroof=q["gpu_model"]["kv_floor_rom_tok_s"], q_s3=qu["S3"]["value"], q_m3=qu["S3"]["multiplier"],
        v_s3=vu["S3"]["value"], v_m3=vu["S3"]["multiplier"], v_s3_mtp=vp["rom_mtp"]["y"],
        q_tot=qu["S3"]["value"] / qu["S0"]["value"], q_fmt=qu["S1f"]["multiplier"],
        v_tot=vu["S3"]["value"] / vu["S0"]["value"],
        q_agg_b200=qa["S1"]["value"], q_agg_rom=qa["S3"]["value"],
    )


# --------------------------------------------------------------------------- render

SANS = "IBM Plex Sans, system-ui, sans-serif"
MONO = "IBM Plex Mono, ui-monospace, monospace"
FAM = {"gpu": "var(--muted)", "hbm": "var(--hbm)", "rom": "var(--rom)"}
FILLED = {"measured", "cited"}
W_SVG, H_SVG = 1000, 600
PL, PR, PT, PB = 78, 690, 46, 548  # plot box: left, right, top, bottom


class Axes:
    def __init__(self, xr, yr):
        self.lx0, self.lx1 = math.log10(xr[0]), math.log10(xr[1])
        self.ly0, self.ly1 = math.log10(yr[0]), math.log10(yr[1])

    def x(self, v):
        return PL + (math.log10(v) - self.lx0) / (self.lx1 - self.lx0) * (PR - PL)

    def y(self, v):
        return PB - (math.log10(v) - self.ly0) / (self.ly1 - self.ly0) * (PB - PT)

    def inside(self, xv, yv):
        return (10 ** self.lx0 <= xv <= 10 ** self.lx1) and (10 ** self.ly0 <= yv <= 10 ** self.ly1)


def _t(x, y, s, size=10, weight=400, anchor="start", fill="var(--ink)", font=SANS, extra=""):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{fill}"{extra}>{html.escape(s)}</text>')


def _fmt_tick(v):
    if v >= 1e6:
        return f"{v/1e6:g}M"
    if v >= 1e3:
        return f"{v/1e3:g}k"
    return f"{v:g}"


def _marker(fam, x, y, filled, spec, r=5.5):
    col = FAM[fam]
    fill = col if filled else "var(--panel)"
    sw = 1.6
    if fam == "gpu":
        shape = f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" style="fill:{fill};stroke:{col};stroke-width:{sw}"/>'
    elif fam == "hbm":
        shape = (f'<rect x="{x-r:.1f}" y="{y-r:.1f}" width="{2*r:.1f}" height="{2*r:.1f}" '
                 f'style="fill:{fill};stroke:{col};stroke-width:{sw}"/>')
    else:
        pts = f"{x:.1f},{y-r-1.5:.1f} {x+r+1.5:.1f},{y:.1f} {x:.1f},{y+r+1.5:.1f} {x-r-1.5:.1f},{y:.1f}"
        shape = f'<polygon points="{pts}" style="fill:{fill};stroke:{col};stroke-width:{sw}"/>'
    if spec:
        shape += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r+3.5:.1f}" style="fill:none;stroke:{col};stroke-width:0.9;stroke-dasharray:2 2"/>'
    return shape


# label placement per point key: (dx, dy, anchor)
LABEL_POS = {
    "qwen3": {
        "rtx_bf16": (-9, 4, "end"), "rtx_fp8": (-9, 4, "end"), "rtx_bf16_dflash": (-9, 4, "end"),
        "h200_bf16": (-9, 4, "end"), "b200_bf16": (9, 12, "start"), "b200_dflash": (9, 4, "start"),
        "b200_ideal_bf16": (9, 4, "start"), "b200_ideal_rom35": (9, -8, "start"), "hdc_matched": (9, 10, "start"),
        "nvl72_tp8_bf16": (-9, -8, "end"), "hdc_bf16": (-9, 4, "end"), "hdc_rom35": (-9, 4, "end"),
        "hdc_rom35_dflash": (-9, 4, "end"), "rom": (-11, 4, "end"), "rom_dflash": (-11, 4, "end"),
    },
    "v41": {
        "gpu_s0": (9, 12, "start"), "gpu_s1": (9, -6, "start"), "gpu_nvl72": (-2, 20, "end"),
        "gpu_mtp_bound": (9, 4, "start"), "v4pro_b300": (9, 4, "start"), "hbm_ar": (9, 14, "start"),
        "hbm_mtp": (9, -8, "start"), "rom_ar": (-11, 4, "end"), "rom_mtp": (-11, 4, "end"),
    },
}


def render_svg(model_key: str, m: dict) -> str:
    ax = Axes(m["x_range"], m["y_range"])
    o = [f'<svg viewBox="0 0 {W_SVG} {H_SVG}" role="img" aria-label="{html.escape(m["title"])}: decode roofline" '
         f'xmlns="http://www.w3.org/2000/svg">']
    mid = f"dr-{model_key}"
    o.append(f'<defs><marker id="{mid}-a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
             f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" style="fill:var(--ink)"/></marker>'
             f'<clipPath id="{mid}-clip"><rect x="{PL}" y="{PT}" width="{PR-PL}" height="{PB-PT}"/></clipPath></defs>')
    o.append(_t(PL, 24, m["title"] + " — decode roofline, batch 1", 12, 600))
    # grid + ticks
    o.append(f'<rect x="{PL}" y="{PT}" width="{PR-PL}" height="{PB-PT}" style="fill:none;stroke:var(--rule);stroke-width:1"/>')
    for d in range(int(math.floor(ax.lx0)), int(math.ceil(ax.lx1)) + 1):
        for k in range(1, 10):
            v = k * 10 ** d
            if not (10 ** ax.lx0 <= v <= 10 ** ax.lx1):
                continue
            X = ax.x(v)
            major = k == 1
            o.append(f'<line x1="{X:.1f}" y1="{PT}" x2="{X:.1f}" y2="{PB}" style="stroke:var(--grid);stroke-width:{1 if major else 0.5}"/>')
            if major:
                o.append(_t(X, PB + 16, f"{v:,.0f}", 10, 400, "middle", "var(--muted)", MONO))
    for d in range(int(math.floor(ax.ly0)), int(math.ceil(ax.ly1)) + 1):
        for k in range(1, 10):
            v = k * 10 ** d
            if not (10 ** ax.ly0 <= v <= 10 ** ax.ly1):
                continue
            Y = ax.y(v)
            major = k == 1
            o.append(f'<line x1="{PL}" y1="{Y:.1f}" x2="{PR}" y2="{Y:.1f}" style="stroke:var(--grid);stroke-width:{1 if major else 0.5}"/>')
            if major or (k == 5 and ax.ly1 - ax.ly0 < 3.5):
                o.append(_t(PL - 6, Y + 3.5, _fmt_tick(v), 10, 400, "end", "var(--muted)", MONO))
    o.append(_t((PL + PR) / 2, PB + 36, "off-chip memory bandwidth devoted to the user, sustained (TB/s, log)", 10.5, 600, "middle", "var(--muted)"))
    o.append(f'<text x="18" y="{(PT+PB)/2:.1f}" font-family="{SANS}" font-size="10.5" font-weight="600" text-anchor="middle" '
             f'transform="rotate(-90 18 {(PT+PB)/2:.1f})" style="fill:var(--muted)">tokens/s for one user (log)</text>')
    g = [f'<g clip-path="url(#{mid}-clip)">']
    # GPU bands first (under everything)
    for c in m["curves"]:
        if c.get("band"):
            poly = [(ax.x(x), ax.y(y)) for x, y in c["hi"]] + [(ax.x(x), ax.y(y)) for x, y in reversed(c["lo"])]
            g.append('<polygon points="' + " ".join(f"{a:.1f},{b:.1f}" for a, b in poly) +
                     f'" style="fill:{FAM[c["family"]]};fill-opacity:0.13;stroke:none"/>')
    for c in m["ceilings"]:
        if c.get("band"):
            y0, y1 = ax.y(c["band"][1]), ax.y(c["band"][0])
            g.append(f'<rect x="{PL}" y="{y0:.1f}" width="{PR-PL}" height="{y1-y0:.1f}" '
                     f'style="fill:{FAM[c["family"]]};fill-opacity:0.10;stroke:none"/>')
    # roofs (diagonals)
    for r in m["roofs"]:
        col = "var(--rom)" if r.get("rom") else "var(--ink)"
        x0, x1 = 10 ** ax.lx0, 10 ** ax.lx1
        ya, yb = x0 * 1e12 / r["bytes_per_token"], x1 * 1e12 / r["bytes_per_token"]
        g.append(f'<line x1="{ax.x(x0):.1f}" y1="{ax.y(ya):.1f}" x2="{ax.x(x1):.1f}" y2="{ax.y(yb):.1f}" '
                 f'style="stroke:{col};stroke-width:1.3;stroke-dasharray:{"7 4" if r.get("rom") else "none"};opacity:0.75"/>')
    # ceilings (horizontal)
    for c in m["ceilings"]:
        if not (10 ** ax.ly0 <= c["y"] <= 10 ** ax.ly1):
            continue
        Y = ax.y(c["y"])
        g.append(f'<line x1="{PL}" y1="{Y:.1f}" x2="{PR}" y2="{Y:.1f}" style="stroke:{FAM[c["family"]]};stroke-width:1.2;stroke-dasharray:3 3"/>')
    # curves
    for c in m["curves"]:
        if c.get("band"):
            continue
        pts = " ".join(f"{ax.x(x):.1f},{ax.y(y):.1f}" for x, y in c["pts"])
        g.append(f'<polyline points="{pts}" style="fill:none;stroke:{FAM[c["family"]]};stroke-width:1.5;'
                 f'stroke-dasharray:{"4 3" if c.get("spec") else "none"}"/>')
        for x, y in c["pts"]:
            g.append(f'<circle cx="{ax.x(x):.1f}" cy="{ax.y(y):.1f}" r="2" style="fill:{FAM[c["family"]]}"/>')
    g.append("</g>")
    o += g
    # roof labels, placed at the right edge where the diagonal is inside the box
    for r in m["roofs"]:
        col = "var(--rom)" if r.get("rom") else "var(--ink)"
        xv = 10 ** ax.lx1
        yv = xv * 1e12 / r["bytes_per_token"]
        if yv > 10 ** ax.ly1:  # exits through the top
            yv = 10 ** ax.ly1 / 1.6
            xv = yv * r["bytes_per_token"] / 1e12
        ang = -math.degrees(math.atan((PB - PT) / (ax.ly1 - ax.ly0) / ((PR - PL) / (ax.lx1 - ax.lx0))))
        X, Y = ax.x(xv) - 6, ax.y(yv) - 6
        o.append(f'<text x="{X:.1f}" y="{Y:.1f}" font-family="{SANS}" font-size="9.5" font-weight="600" text-anchor="end" '
                 f'transform="rotate({ang:.1f} {X:.1f} {Y:.1f})" style="fill:{col}">roof: {html.escape(r["label"])}</text>')
    for c in m["ceilings"]:
        if 10 ** ax.ly0 <= c["y"] <= 10 ** ax.ly1:
            o.append(_t(PL + 6, ax.y(c["y"]) - 4, f'{c["label"]} · {c["y"]:,.0f}', 9, 600, "start", FAM[c["family"]]))
        elif c["y"] > 10 ** ax.ly1:
            o.append(_t(PL + 6, PT + 12, f'↑ {c["label"]}: {c["y"]:,.0f} (off scale)', 9, 600, "start", FAM[c["family"]]))
    # ladder arrows
    pk = {p["key"]: p for p in m["points"]}
    for a, b, lab in m["arrows"]:
        pa, pb = pk[a], pk[b]
        x1, y1, x2, y2 = ax.x(pa["x"]), ax.y(pa["y"]), ax.x(pb["x"]), ax.y(pb["y"])
        L = math.hypot(x2 - x1, y2 - y1)
        if L < 20:
            continue
        ux, uy = (x2 - x1) / L, (y2 - y1) / L
        sx, sy, ex, ey = x1 + ux * 9, y1 + uy * 9, x2 - ux * 11, y2 - uy * 11
        o.append(f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" '
                 f'style="stroke:var(--ink);stroke-width:1.6" marker-end="url(#{mid}-a)"/>')
        mult = pb["y"] / pa["y"]
        mx, my = (sx + ex) / 2, (sy + ey) / 2
        o.append(_t(mx + (6 if abs(ux) < 0.3 else 0), my - (0 if abs(ux) < 0.3 else 6), f"×{mult:.2f} {lab}" if mult < 10 else f"×{mult:.1f} {lab}",
                    9.5, 700, "start" if abs(ux) < 0.3 else "middle", "var(--ink)"))
    # points + labels
    pos = LABEL_POS.get(model_key, {})
    for p in m["points"]:
        if not ax.inside(p["x"], p["y"]):
            continue
        X, Y = ax.x(p["x"]), ax.y(p["y"])
        o.append(_marker(p["family"], X, Y, p["evidence"] in FILLED, p["spec"]))
        dx, dy, anc = pos.get(p["key"], (9, 4, "start"))
        o.append(_t(X + dx, Y + dy, f'{p["label"]} · {p["y"]:,.0f}', 9.5, 600, anc, FAM[p["family"]] if p["family"] != "gpu" else "var(--ink)"))
    # legend (right column)
    lx, ly = PR + 24, PT + 4
    o.append(_t(lx, ly + 6, "Machines", 10.5, 700))
    items = [("gpu", "GPU (NVIDIA)"), ("hbm", "specialised HBM accelerator"), ("rom", "ROM design")]
    for i, (fam, lab) in enumerate(items):
        yy = ly + 26 + i * 20
        o.append(_marker(fam, lx + 7, yy - 4, True, False, 5))
        o.append(_t(lx + 20, yy, lab, 10))
    ly2 = ly + 26 + 3 * 20 + 8
    o.append(_t(lx, ly2, "Evidence", 10.5, 700))
    o.append(_marker("gpu", lx + 7, ly2 + 16, True, False, 5))
    o.append(_t(lx + 20, ly2 + 20, "filled: measured or cited", 10))
    o.append(_marker("gpu", lx + 7, ly2 + 36, False, False, 5))
    o.append(_t(lx + 20, ly2 + 40, "hollow: calibrated, modelled, bound", 10))
    o.append(_marker("gpu", lx + 7, ly2 + 56, False, True, 5))
    o.append(_t(lx + 20, ly2 + 60, "dashed ring: with speculation", 10))
    ly3 = ly2 + 84
    o.append(_t(lx, ly3, "Lines", 10.5, 700))
    o.append(f'<line x1="{lx}" y1="{ly3+14}" x2="{lx+16}" y2="{ly3+6}" style="stroke:var(--ink);stroke-width:1.3"/>')
    o.append(_t(lx + 22, ly3 + 14, "bandwidth roof: BW / bytes per token", 10))
    o.append(f'<line x1="{lx}" y1="{ly3+32}" x2="{lx+16}" y2="{ly3+24}" style="stroke:var(--rom);stroke-width:1.3;stroke-dasharray:7 4"/>')
    o.append(_t(lx + 22, ly3 + 32, "KV-only roof (weights in ROM)", 10))
    o.append(f'<line x1="{lx}" y1="{ly3+46}" x2="{lx+16}" y2="{ly3+46}" style="stroke:var(--muted);stroke-width:1.2;stroke-dasharray:3 3"/>')
    o.append(_t(lx + 22, ly3 + 50, "ceiling (sync / chain)", 10))
    o.append(f'<rect x="{lx}" y="{ly3+58}" width="16" height="10" style="fill:var(--muted);fill-opacity:0.18"/>')
    o.append(_t(lx + 22, ly3 + 67, "GPU band: SoL floor to NCCL", 10))
    o.append(f'<line x1="{lx}" y1="{ly3+84}" x2="{lx+16}" y2="{ly3+84}" style="stroke:var(--ink);stroke-width:1.6" marker-end="url(#{mid}-a)"/>')
    o.append(_t(lx + 22, ly3 + 88, "ladder step (× multiplier)", 10))
    # ladder summary box
    ly4 = ly3 + 112
    o.append(_t(lx, ly4, "Attribution ladder, tok/s", 10.5, 700))
    for i, s in enumerate(m["ladders"]["per_user"]):
        mult = "" if s["multiplier"] is None else f'  ×{s["multiplier"]:.2f}'
        val = "—" if s["value"] is None else f'{s["value"]:,.0f}'
        o.append(_t(lx, ly4 + 18 + i * 15, f'{s["step"]:<4}{val:>7}{mult}', 9.5, 400, "start", "var(--ink)", MONO,
                    ' xml:space="preserve"'))
    o.append("</svg>")
    return "".join(o)


def _tag(ev: str) -> str:
    e = ev.lower()
    cls = "meas" if (e.startswith("measured") or e.startswith("cited")) else ("pend" if ("not " in e or "bound" in e) else "mod")
    return f'<span class="tag {cls}">{html.escape(ev)}</span>'


def render_table(title: str, rows: list[dict]) -> str:
    unit = next((r["unit"] for r in rows if r.get("unit")), "")
    h = [f'<div class="tablebox"><table class="data"><caption>{html.escape(title)}</caption>',
         f'<thead><tr><th>Step</th><th>Machine</th><th class="r">{html.escape(unit)}</th><th class="r">× step</th>'
         f'<th>Evidence</th><th>Matching and basis</th></tr></thead><tbody>']
    for r in rows:
        v = "—" if r["value"] is None else (f'{r["value"]:,.0f}' if r["value"] >= 100 else f'{r["value"]:,.2f}')
        mlt = "" if r["multiplier"] is None else f'{r["multiplier"]:.2f}×'
        basis = "; ".join(x for x in (r.get("matching"), r.get("basis")) if x)
        h.append(f'<tr><td>{r["step"]}</td><td>{html.escape(r["label"])}</td><td class="r m">{v}</td><td class="r m">{mlt}</td>'
                 f'<td>{_tag(r["evidence"])}</td><td>{html.escape(basis)}</td></tr>')
    h.append("</tbody></table></div>")
    return "".join(h)


CAPTIONS = {
    "qwen3": (
        "Figure 8-R1. Qwen3-8B decode roofline for one user (8K context, FP8 KV, batch 1). "
        "Diagonals are bandwidth roofs, tokens/s = bandwidth / bytes per token, for BF16 and for the ROM's 3.5-bit weights "
        "(each with FP8 KV); the dashed orange diagonal is the KV-only roof a ROM design lives under, because its weights "
        "never cross the memory interface. Dotted horizontals are ceilings: one GPU's on-chip synchronisation (220 all-SM "
        "boundaries at the measured 1.0 µs), the ROM weight sweep, and our compiled handoffs (4.8 ns, RTL; off scale). "
        "The grey curve is B200 tensor parallelism on an NVL72 slice (TP ≤ 8, the KV-head limit) with 73 all-reduces at "
        "the best measured GB200 kernel, the band spanning the speed-of-light floor to NCCL 2.27. Arrows are the "
        "attribution ladder: software (measured B200 to its idealised roof), weight format (to the ROM's 3.5-bit), "
        "specialisation (×1.00: on one die both machines are on the same roof) and ROM. Sources: DFlash Table 3 [DFlash]; "
        "local RTX PRO 6000 measurement; H200 calibrated on NIM; results/arch/qwen3_budget.json; results/arch/sync_cost_table.json "
        "[Shen et al.; NCCL 2.27]; tools/decode_roofline_figure.py."
    ),
    "v41": (
        "Figure 8-R2. DeepSeek-V4.1-Flash decode roofline for one user (1M context, batch 1). "
        "The diagonal is the bandwidth roof for the checkpoint's own weight dtypes plus KV and index reads (13.2 GB per "
        "token); the dashed orange diagonal is the KV-only roof of the ROM array. GPU points are modelled on measured "
        "primitives: the weight/KV stream over N B200s plus the 209 collectives of the array's graph at the best measured "
        "GB200 all-reduce (2.37 µs), the band spanning the speed-of-light floor (1.40 µs) to NCCL 2.27 (~5 µs); no "
        "on-chip boundaries or compute are charged, so the GPU curve is optimistic for this graph. A different GPU mapping could change the 209-collective graph. It flattens at the synchronisation "
        "ceiling: 72 GPUs add 2% over the iso-area set. The blue curve is the specialised HBM comparator against its "
        "tensor-group span G, which peaks at G = 96 on the validated switched fabric. The ROM array leaves the weight roof "
        "and is bound by its compiled chain. The only published V4-class batch-1 GPU figure is V4-Pro (49 B active) with "
        "DSpark on 8 B300s [LMSYS]; no V4.1-Flash figure exists. ROM rates carry the collective exposure measured in the RTL "
        "stage bench (rack gate C7 not met) and are conditional on the 1.087 GHz clock. Sources: results/arch/v41_lanes.json, v41_hbm_switched.json, v41_latency_ladder.json, "
        "arch_budget_v41.json, sync_cost_table.json; tools/decode_roofline_figure.py."
    ),
}


def render_html(model_key: str, m: dict) -> str:
    fig_id = f"fig-decode-roofline-{model_key}"
    lad = m["ladders"]
    name = "Qwen3-8B, 8K" if model_key == "qwen3" else "DeepSeek-V4.1-Flash, 1M"
    parts = [f"<!-- generated by tools/decode_roofline_figure.py from results/arch/decode_roofline.json -->",
             f'<figure class="fig" id="{fig_id}">',
             f'  <div class="svgbox">{render_svg(model_key, m)}</div>',
             f"  <figcaption><b>{html.escape(CAPTIONS[model_key].split('. ', 1)[0])}.</b> "
             f"{html.escape(CAPTIONS[model_key].split('. ', 1)[1])}</figcaption>",
             "</figure>",
             render_table(f"Table 8-R{'1' if model_key == 'qwen3' else '2'}a. Attribution ladder, {name}: tokens/s for one user at "
                          "batch 1. Each modeled step keeps or reduces the silicon and memory "
                          "bandwidth of the step before it." + (" V4.1 S2 to S3 is a whole-design comparison." if model_key == "v41" else ""), lad["per_user"]),
             render_table(f"Table 8-R{'1' if model_key == 'qwen3' else '2'}b. Attribution ladder, {name}: energy per token at batch 1.",
                          lad["energy"]),
             render_table(f"Table 8-R{'1' if model_key == 'qwen3' else '2'}c. Attribution ladder, {name}: aggregate throughput at the "
                          "fill batch.", lad["aggregate"])]
    return "\n".join(parts) + "\n"


def build() -> dict:
    src, meta = load_sources()
    q = build_qwen(src)
    v = build_v41(src)
    return {
        "schema": SCHEMA,
        "tool": "tools/decode_roofline_figure.py",
        "inputs": meta,
        "cited": CITED,
        "gpu_collective_us": {k: {"value": a, "source": b} for k, (a, b) in GPU_COLLECTIVE_US.items()},
        "axes": {"x": "off-chip memory bandwidth devoted to the user, sustained (TB/s)", "y": "tokens/s for one user"},
        "ladder_definition": (
            "S0 GPU application or shipped-library baseline, modeled where a same-model measurement is unavailable; S1 same GPUs, idealised runtime (software gap); S2 specialised HBM accelerator "
            "at no more silicon and HBM bandwidth than S1 (specialisation); S3 a specialised ROM accelerator at equal logic area. Qwen3-8B adds "
            "S1f (the ROM's 3.5-bit weight format). Qwen S2 has B200-class bandwidth while S3 has six stacks; the matched six-stack HBM/ROM comparison is separate. The order is part of "
            "the definition: the factors are not independent (ROM without specialisation is not a meaningful machine). "
            "Each step keeps or reduces the silicon and bandwidth of the step before it. V4.1 S2-to-S3 also changes die count, topology and HBM allocation, so its multiplier is not an isolated ROM effect. "
            "S2-S3 are conditional on the design's open gates (clock; V4.1 collectives at their measured exposure)."
        ),
        "models": {"qwen3": q, "v41": v},
        "captions": CAPTIONS,
        "findings": findings(q, v),
    }


def _round(o):
    if isinstance(o, float):
        return float(f"{o:.6g}")
    if isinstance(o, dict):
        return {k: _round(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_round(v) for v in o]
    return o


def write(rec: dict) -> list[Path]:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rec = _round(rec)
    OUT_JSON.write_text(json.dumps(rec, indent=1) + "\n")
    paths = [OUT_JSON]
    for key, name in (("qwen3", "qwen3"), ("v41", "v41")):
        p = OUT_DIR / f"decode_roofline_{name}.html"
        p.write_text(render_html(key, rec["models"][key]))
        paths.append(p)
    p = OUT_DIR / "decode_roofline_findings.html"
    p.write_text("<!-- generated by tools/decode_roofline_figure.py -->\n<p>" + html.escape(rec["findings"]) + "</p>\n")
    paths.append(p)
    return paths


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="rebuild and compare with the committed JSON")
    a = ap.parse_args(argv)
    rec = _round(build())
    if a.check:
        on_disk = json.loads(OUT_JSON.read_text())
        if on_disk != json.loads(json.dumps(rec)):
            print("decode_roofline.json is stale; re-run tools/decode_roofline_figure.py", file=sys.stderr)
            return 1
        print("decode_roofline.json is current")
        return 0
    for p in write(rec):
        print(p.relative_to(ROOT))
    print(rec["findings"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
