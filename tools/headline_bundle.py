#!/usr/bin/env python3
"""One reproducible source/configuration/result bundle for the atlas headlines.

Answers finding 6 and recommendation 6 of
docs/ARCHITECTURE_ATLAS_FEASIBILITY_REVIEW_2026_09_27.md: "publish one
reproducible source/configuration/result bundle, with explicit evidence classes
and sensitivity ranges".

WHAT IT DOES
------------
``HEADLINES`` below enumerates the headline figures of docs/ARCHITECTURE_ATLAS.html
-- the lead and abstract, Tables 2-1 and 2-2, and the findings of chapters 6-11
(V4.1 rates and MTP, ROM / HBM ratios, energies, the Qwen3-8B target, cooling
caps and DFlash rate, quality results, RTL gate results and physical closure
results).  For each one it records

  * the value as printed, at every place the atlas prints it (an anchor phrase
    picks one paragraph or table row; the printed literal must occur in it);
  * the record and JSON key it is bound to, and the value the record holds
    (read with tools/check_prose_figures.py's selector grammar and compared
    with its written-precision rule, so a figure agrees here exactly when a
    ``figure:`` annotation would agree);
  * the record's generating tool and command;
  * every source the record pins, with the pinned hash and whether it is still
    current (the pin shapes of tools/audit_source_currency_drift.py, plus the
    ``input_sha256``, ``tools``, ``inputs`` and ``golden_pin`` shapes that
    audit does not read), and whether any snapshot commit the record names is
    in HEAD's history;
  * an evidence class (below) and, where a record carries one, a sensitivity
    range built from the record's own variant fields.

A headline no record produces is listed with ``binding: null`` and the reason.
That list is the durable output: it is what a reviewer cannot reproduce.

The bundle is written to results/arch/headline_bundle.json and rendered as the
appendix docs/HEADLINE_BUNDLE.md, whose bound rows carry ``figure:`` annotations
so tools/check_prose_figures.py checks them too.

CHECK MODE
----------
``--check`` rebuilds the bundle and fails when

  1. a printed value differs from its record (never baselined: fix the atlas or
     regenerate the record; the only exceptions are the disagreements named in
     ``ACKNOWLEDGED_DISAGREEMENTS``, each pinned to its exact printed and
     recorded value, so any further movement fails);
  2. an anchor or printed literal is no longer in the atlas (the prose moved:
     update the manifest here, not the value);
  3. a bound record is missing or untracked, or a selector no longer resolves;
  4. a NEW finding appears that the committed bundle does not already list: a
     source pin that is stale against the tree, a pinned source that is
     missing, a snapshot commit outside HEAD's history, or a headline that is
     unbound.  Existing findings are carried in ``known_findings`` (a ratchet,
     as ``REQUIRED_COVERAGE`` is in check_prose_figures.py): drift is systemic
     in this repository (results/derived/source_currency_drift.json) and is
     not mass-regenerated, but it must not grow silently;
  5. the committed JSON or Markdown differs from what this tool now writes
     (regenerate with ``python3 tools/headline_bundle.py``).

It changes nothing in the atlas and never rewrites a pin.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from audit_source_currency_drift import BINDING_FIELDS, classify_binding  # noqa: E402
from check_prose_figures import (  # noqa: E402
    NUMBER,
    AnnotationError,
    Quantity,
    _to_quantity,
    agree,
    resolve_json,
)

ATLAS = Path("docs/ARCHITECTURE_ATLAS.html")
OUT_JSON = Path("results/arch/headline_bundle.json")
OUT_MD = Path("docs/HEADLINE_BUNDLE.md")
SCHEMA = "opentallas.headline-bundle.v1"

EVIDENCE_CLASSES = {
    "measured-RTL": "Observed in an RTL simulation of this repository's RTL (Verilator or Icarus) "
                    "against a golden; reduced vehicles unless stated.",
    "measured-physical": "Read from an ASAP7 synthesis, place-and-route or DFT run of this "
                         "repository's RTL (predictive 7 nm PDK; not silicon).",
    "measured-quality": "Measured model quality or acceptance on real weights, on a GPU, under an "
                        "emulation of the deployment arithmetic.",
    "measured-gpu": "Measured by this project on GPU hardware (microbenchmarks, application runs).",
    "model": "An analytical, specification, calibrated or design-point model evaluated by a "
             "repository tool; RTL-calibrated where stated. Not a measurement of a chip.",
    "third-party": "A figure published by someone else and carried into a record as a cited input.",
}

# Pin maps in addition to the six the source-currency audit reads.  Each maps a
# repository path to a SHA-256 (or a label to a {path|from, sha256} object).
EXTRA_PIN_FIELDS = ("input_sha256", "tools", "inputs")
COMMIT_FIELDS = ("source_snapshot_commit", "execution_source_commit", "published_equivalent_commit")

RATCHET_KINDS = {"stale-pin", "missing-pin", "commit-outside-head", "at-commit-mismatch", "unbound"}


# --------------------------------------------------------------------------
# manifest helpers


def B(record: str, selector: str, scale: float | None = None) -> dict[str, Any]:
    """One record field."""
    out: dict[str, Any] = {"record": record, "selector": selector}
    if scale is not None:
        out["scale"] = scale
    return out


def RATIO(num: dict[str, Any], den: dict[str, Any]) -> dict[str, Any]:
    """A ratio of two record fields.  Derived here, so reported as derived."""
    return {"ratio": [num, den]}


def AGG(fn: str, record: str, pattern: str, scale: float | None = None) -> dict[str, Any]:
    """min/max over a `*` wildcard selector (e.g. every DFT block)."""
    out: dict[str, Any] = {"agg": fn, "record": record, "selector": pattern}
    if scale is not None:
        out["scale"] = scale
    return out


def at(anchor: str, text: str, pick: int = 0, tol: str | None = None) -> dict[str, Any]:
    """The printed literal `text`, in the one atlas block containing `anchor`.

    `pick` chooses which number inside `text` is the figure (default: first).
    `tol` loosens the written-precision rule for a figure the prose rounds on
    purpose ("near 1,170"), as check_prose_figures.py's tol= does.
    """
    out: dict[str, Any] = {"in": anchor, "text": text, "pick": pick}
    if tol is not None:
        out["tol"] = tol
    return out


def S(label: str, binding: dict[str, Any]) -> dict[str, Any]:
    return {"label": label, "binding": binding}


QB = "results/arch/qwen3_budget.json"
PS = "results/arch/power_scenarios.json"
LN = "results/arch/v41_lanes.json"
SW = "results/arch/v41_hbm_switched.json"
AB = "results/arch/arch_budget_v41.json"
DR = "results/arch/decode_roofline.json"
SC = "results/arch/sync_cost_table.json"
RK = "results/arch/v41_rack.json"
QQ = "results/quality/qwen3_8b_deployment_arithmetic.json"
BA = "results/speculative/dflash_block_acceptance.json"
DT = "results/speculative/dflash_step_timing.json"
GG = "results/gpu/blackwell_gather_designs.json"
MT = "results/physical_hdc/asap7/matvec_memory_tile_ingress_slew60/physical.json"
DFT = "results/dft/summary.json"

PB = "scenarios.B_proposed_production"
PA = "scenarios.A_measured_implementation"
QPB = "power_production.scenarios.B_proposed_production"
QPA = "power_production.scenarios.A_measured_implementation"
POB = "rom_over_hbm.B_proposed_production"
POA = "rom_over_hbm.A_measured_implementation"
QWEN_ROM = f"{QB}"

# Atlas anchors: phrases that pick one paragraph or table row.  Chosen to avoid
# the numbers themselves where possible, so that an edited figure is reported
# as a disagreement rather than as a lost anchor.
LEAD = "Mask-ROM weights beside the multipliers"
ABS = "Interactive and agentic use of language models"
PAYOFF = "previews the result at the design points we chose"
FIG21 = "Per-user decode rate at batch 1 at the three design points"
DEPLOY = "Two deployment questions follow"
S84 = "The GPU comparisons in the attribution ladder separate software"
S84V = "The comparator uses its best configuration on shipping hardware"
C7 = "Rack gate C7: measured exposure, partly recovered"
CONCL = "Fast per-user decode is limited on today's accelerators"
S101 = "The modeled operating energy is lower at the batch sizes"
S101B = "Throughput per silicon is not the price of speed either"
S84E = "Finding: data movement, not arithmetic, dominates decode energy"
QHEAD = "Qwen3-8B headline: one reticle, 8K, per user, batch 1, DFlash"
QAR = "Qwen3-8B without speculation, at specification widths"
QPWR = "Qwen3-8B reticle at 8,910 tok/s without speculation, power scenarios B / A"
QPWR2 = "Qwen3-8B reticle under the power scenarios, production lane / lane as built"
QT814 = "Qwen3-8B, 8K, FP8 KV, DFlash (m = 3, block 3) / autoregressive"


def _power_variants(path_tail: str, scen: str = PB) -> list[dict[str, Any]]:
    """The same power-scenario field under every recorded sensitivity."""
    names = {
        "B_lane_at_gpu_tensor_1p40pj": "production lane at 1.40 pJ/MAC (GPU tensor core)",
        "B_old_hbm_allocation_die_0p8": "older HBM die allocation (0.8)",
        "B_hbm_die_gh200_8p23": "HBM die energy at the GH200 8.23 pJ/bit",
        "A_measured_implementation": "scenario A (measured ASAP7 lane)",
    }
    out = []
    for key, label in names.items():
        sel = (f"scenarios.{key}.{path_tail}" if key.startswith("A_")
               else f"sensitivities.{key}.{path_tail}")
        out.append(S(label, B(PS, sel)))
    return out


def _fabric_ratio(ctx: str, mode: str) -> list[dict[str, Any]]:
    """ROM / HBM at the other recorded comparator fabrics (Table 8-25)."""
    rom = B(LN, f"design_point.{ctx}.{mode}")
    labels = {"nvl_0p9": "comparator without NVLS", "nvl_1p8_nvls": "comparator at doubled package bandwidth with NVLS",
              "nvl_1p8": "comparator at doubled package bandwidth without NVLS"}
    return [S(lbl, RATIO(rom, B(SW, f"configs.{cfg}.{ctx}.best_{mode}.rate")))
            for cfg, lbl in labels.items()]


# --------------------------------------------------------------------------
# THE HEADLINES
#
# id: stable key.  claim: what the number is.  cls: evidence class.
# binding: B/RATIO/AGG or None (with `unbound`: why).  printed: every place.

HEADLINES: list[dict[str, Any]] = [
    # ---------------------------------------------------------------- Qwen3-8B headline: DFlash
    # Since acb8d122 the atlas leads with DFlash on one reticle (13,052 design
    # rate; 11,925 / 4,731 cooling-capped); 8,910 is the uncapped autoregressive
    # chain beside it.
    dict(id="qwen.dflash", section="Qwen3-8B headline (DFlash)", cls="model",
         claim="Qwen3-8B headline: DFlash, three lane copies, block 3, serial draft + verify + commit, design rate (tokens/s)",
         binding=B(QB, 'dflash.rom["8192/fp8/m3"].best.tokens_s'),
         sensitivity=[S("equal-weighted tau 2.321 instead of pooled 2.265",
                        B(QB, 'dflash.rom["8192/fp8/m3"].best.tokens_s_band')),
                      S("cooling cap, scenario B (production lane)", B(PS, f"{PB}.qwen3_8b_rom_8k.dflash.capped_rate")),
                      S("cooling cap, scenario A (lane as built)", B(PS, f"{PA}.qwen3_8b_rom_8k.dflash.capped_rate"))],
         printed=[at(LEAD, "a 13,052-token/s design rate"),
                  at(ABS, "a design rate of 13,052 tokens/s"),
                  at(QHEAD, "13,052 tok/s (1.70×"),
                  at(S84, "at a 13,052-token/s design rate"),
                  at("ROM reticle, specification chain (three lane copies", "13,052"),
                  at(QT814, "13,052 / 8,910 tok/s"),
                  at(CONCL, "a 13,052-token/s design rate at 8K")]),
    dict(id="qwen.dflash_cap_B", section="Qwen3-8B headline (DFlash)", cls="model",
         claim="Qwen3-8B DFlash cooling-capped rate at the single-die cooling limit, scenario B (production lane)",
         binding=B(PS, f"{PB}.qwen3_8b_rom_8k.dflash.capped_rate"),
         sensitivity=_power_variants("qwen3_8b_rom_8k.dflash.capped_rate")[:3],
         printed=[at(LEAD, "11,925 tokens/s under the air/liquid cooling limit"),
                  at(ABS, "capped at 11,925 tokens/s"),
                  at(QHEAD, "cap 11,925 / 4,731"),
                  at(S84, "capped by cooling at 11,925"),
                  at("Qwen3-8B cooling-capped rate at 549.5 W per die", "11,925 / 7,442 and 4,731 / 4,689"),
                  at(QPWR, "7,442 / 11,925 (B)", pick=1),
                  at("ROM die power-capped at 549.5 W, production lane", "11,925"),
                  at(QT814, "cooling-capped at 11,925 on the production lane"),
                  at(CONCL, "11,925 tokens/s under the cooling limit")]),
    dict(id="qwen.dflash_cap_A", section="Qwen3-8B headline (DFlash)", cls="model",
         claim="Qwen3-8B DFlash cooling-capped rate at the single-die cooling limit, scenario A (lane as built, ASAP7)",
         binding=B(PS, f"{PA}.qwen3_8b_rom_8k.dflash.capped_rate"),
         printed=[at(LEAD, "(4,731 with the lane as built)"),
                  at(ABS, "4,731 with the lane as built"),
                  at(QHEAD, "cap 11,925 / 4,731", pick=1),
                  at(S84, "4,731 on the lane as built"),
                  at("Qwen3-8B cooling-capped rate at 549.5 W per die", "11,925 / 7,442 and 4,731 / 4,689", pick=2),
                  at(QPWR, "4,689 / 4,731 (A)", pick=1),
                  at("ROM die power-capped at 549.5 W, measured ASAP7 lane", "4,731"),
                  at(CONCL, "(4,731 with the lane as built)")]),
    dict(id="qwen.dflash_speedup", section="Qwen3-8B headline (DFlash)", cls="model",
         claim="Qwen3-8B DFlash speed-up over the plain chain (three lane copies)",
         binding=B(QB, 'dflash.rom["8192/fp8/m3"].best.speedup'),
         printed=[at(QHEAD, "(1.70× the plain chain)"),
                  at("Speculation cures the memory wall", "1.70× with three copies")]),
    dict(id="qwen.cooling_limit_w", section="Qwen3-8B headline (DFlash)", cls="model",
         claim="Single-die package cooling limit, air = liquid (W per die)",
         binding=B(PS, f"{PB}.qwen3_8b_rom_8k.ar_batch1.cooling_limit_w"),
         printed=[at(ABS, "exceeds the 549.5 W that a shipping single-die package cools"),
                  at(QHEAD, "cooling-capped at 549.5 W per die")]),
    dict(id="qwen.dflash_energy_B", section="Qwen3-8B headline (DFlash)", cls="model",
         claim="Qwen3-8B reticle with DFlash at its design rate, energy per token, scenario B (mJ)",
         binding=B(PS, f"{PB}.qwen3_8b_rom_8k.dflash.energy_per_token_mj"),
         sensitivity=_power_variants("qwen3_8b_rom_8k.dflash.energy_per_token_mj"),
         printed=[at(ABS, "with DFlash spends 53.6 mJ per token"),
                  at(QPWR2, "53.6 / 108 mJ"),
                  at("Qwen3-8B reticle with DFlash (m = 3, block 3) at the serial step", "53.6 / 108.3 mJ")]),
    dict(id="qwen.dflash_energy_A", section="Qwen3-8B headline (DFlash)", cls="model",
         claim="Qwen3-8B reticle with DFlash, energy per token, scenario A (mJ)",
         binding=B(PS, f"{PA}.qwen3_8b_rom_8k.dflash.energy_per_token_mj"),
         printed=[at(ABS, "(108 mJ on our measured lane"),
                  at(QPWR2, "53.6 / 108 mJ", pick=1),
                  at("Qwen3-8B reticle with DFlash (m = 3, block 3) at the serial step", "53.6 / 108.3 mJ", pick=1)]),
    dict(id="qwen.dflash_die_power_B", section="Qwen3-8B headline (DFlash)", cls="model",
         claim="Qwen3-8B die power with DFlash at its design rate, scenario B (W)",
         binding=B(PS, f"{PB}.qwen3_8b_rom_8k.dflash.die_w_at_design_rate"),
         printed=[at(QPWR2, "590 / 1,304 W")]),
    dict(id="qwen.dflash_die_power_A", section="Qwen3-8B headline (DFlash)", cls="model",
         claim="Qwen3-8B die power with DFlash at its design rate, scenario A (W)",
         binding=B(PS, f"{PA}.qwen3_8b_rom_8k.dflash.die_w_at_design_rate"),
         printed=[at(QPWR2, "590 / 1,304 W", pick=1),
                  at("Where the energy goes", "die at 1,304 W with DFlash")]),
    dict(id="qwen.tau_block3", section="Qwen3-8B headline (DFlash)", cls="measured-quality",
         claim="DFlash acceptance tau at block 3, pooled over 264 prompt turns (BF16, GPU)",
         binding=B(BA, "blocks.3.pooled.primary.tau_direct_cycle_weighted"),
         sensitivity=[S("lowest workload", B(BA, "blocks.3.pooled.primary.tau_direct_workload_range[0]")),
                      S("highest workload", B(BA, "blocks.3.pooled.primary.tau_direct_workload_range[1]"))],
         printed=[at("DFlash acceptance τ on real Qwen3-8B (BF16, GPU)", "2.265 (1.97"),
                  at(FIG21, "τ = 2.265 measured directly at that block")]),
    dict(id="qwen.tau_block16", section="Qwen3-8B headline (DFlash)", cls="measured-quality",
         claim="DFlash acceptance tau at block 16, pooled",
         binding=B(BA, "blocks.16.pooled.primary.tau_direct_cycle_weighted"),
         sensitivity=[S("equal-weighted mean of workloads", B(BA, "blocks.16.pooled.primary.tau_direct_mean_of_workloads"))],
         printed=[at("DFlash acceptance τ on real Qwen3-8B (BF16, GPU)", "/ 3.656")]),
    # ---------------------------------------------------------------- Qwen3-8B autoregressive
    dict(id="qwen.rate_8k", section="Qwen3-8B autoregressive (uncapped target)", cls="model",
         claim="Qwen3-8B without speculation: uncapped autoregressive design rate at specification widths (RTL-calibrated)",
         binding=B(QB, "power.points.ar_batch1.at.design.tokens_s"),
         sensitivity=[S("cooling cap, scenario B (production lane)", B(PS, f"{PB}.qwen3_8b_rom_8k.ar_batch1.capped_rate")),
                      S("cooling cap, scenario A (lane as built)", B(PS, f"{PA}.qwen3_8b_rom_8k.ar_batch1.capped_rate")),
                      S("KV in BF16 instead of FP8", B(QB, 'rom_token["8192/bf16"].tokens_s'))],
         printed=[at(ABS, "the RTL-calibrated chain targets 8,910 tokens/s"),
                  at(QAR, "8,910 tok/s (8,941; 8,494)"),
                  at("S3 · specialized ROM accelerator", "8,910 calibrated"),
                  at(S84, "the calibrated model targets 8,910 tokens/s"),
                  at("ROM reticle, the core at specification widths", "8,910"),
                  at(QT814, "13,052 / 8,910 tok/s", pick=1),
                  at(CONCL, "at 8,910 tokens/s, is within 0.3%")]),
    dict(id="qwen.kv_floor", section="Qwen3-8B autoregressive (uncapped target)", cls="model",
         claim="Qwen3-8B ideal FP8 KV bandwidth ceiling at 8K (tokens/s)",
         binding=B(QB, f"{QPB}.rom.kv_bound_batch2.tokens_s"),
         printed=[at(ABS, "ideal FP8 KV bandwidth ceiling of 8,941 tokens/s", pick=1),
                  at(QAR, "8,910 tok/s (8,941; 8,494)", pick=1),
                  at("ROM reticle, budget target (KV stream", "8,494 / 8,941", pick=1)]),
    dict(id="qwen.target", section="Qwen3-8B autoregressive (uncapped target)", cls="model",
         claim="Qwen3-8B budget target (KV stream / 0.95)",
         binding=B(QB, "budget.target_tokens_s"),
         printed=[at(ABS, "above its 8,494 target"),
                  at(QAR, "8,910 tok/s (8,941; 8,494)", pick=2),
                  at("ROM reticle, budget target (KV stream", "8,494 / 8,941")]),
    dict(id="qwen.chain_cycles", section="Qwen3-8B autoregressive (uncapped target)", cls="model",
         claim="Qwen3-8B calibrated dependency chain per token at 8K (cycles)",
         binding=B(QB, "as_built_calibrated.8192.cycles"),
         printed=[at(ABS, "Its 123,301-cycle dependency chain"),
                  at(QT814, "123,301-cycle calibrated chain"),
                  at("The Qwen3 chain was cut to the KV floor", "174,856 → 123,301 cycles", pick=1)]),
    dict(id="qwen.kv_stream_cycles", section="Qwen3-8B autoregressive (uncapped target)", cls="model",
         claim="Qwen3-8B FP8 KV stream floor at 8K (cycles)",
         binding=B(QB, "roofline_rom.8192.kv_hbm_read.cycles"),
         printed=[at(ABS, "the 122,881-cycle KV stream floor"),
                  at(QT814, "a 122,881-cycle KV stream"),
                  at("The Qwen3 chain was cut to the KV floor", "the 122,881-cycle FP8 KV stream")]),
    dict(id="qwen.spec_chain", section="Qwen3-8B autoregressive (uncapped target)", cls="model",
         claim="Qwen3-8B token in the analytical (specification) chain",
         binding=B(QB, 'dependency_chain["8192/spec"].tokens_s'),
         printed=[at("Same token in the analytical chain at specification widths", "7,689 tok/s"),
                  at("ROM reticle, specification chain (three lane copies", "7,689")]),
    dict(id="qwen.cap_B", section="Qwen3-8B autoregressive (uncapped target)", cls="model",
         claim="Qwen3-8B autoregressive cooling-capped rate, scenario B (production lane)",
         binding=B(PS, f"{PB}.qwen3_8b_rom_8k.ar_batch1.capped_rate"),
         sensitivity=_power_variants("qwen3_8b_rom_8k.ar_batch1.capped_rate")[:3],
         printed=[at(ABS, "Cooling caps this autoregressive rate at 7,442"),
                  at(QAR, "cap 7,442 / 4,689"),
                  at("Qwen3-8B cooling-capped rate at 549.5 W per die", "11,925 / 7,442 and 4,731 / 4,689", pick=1),
                  at(QPWR, "7,442 / 11,925 (B)"),
                  at(S84, "(capped at 7,442 and 4,689)"),
                  at("ROM die power-capped at 549.5 W, production lane", "7,442")]),
    dict(id="qwen.cap_A", section="Qwen3-8B autoregressive (uncapped target)", cls="model",
         claim="Qwen3-8B autoregressive cooling-capped rate, scenario A (lane as built, ASAP7)",
         binding=B(PS, f"{PA}.qwen3_8b_rom_8k.ar_batch1.capped_rate"),
         printed=[at(ABS, "autoregressive rate at 7,442 and 4,689", pick=1),
                  at(QAR, "cap 7,442 / 4,689", pick=1),
                  at("Qwen3-8B cooling-capped rate at 549.5 W per die", "11,925 / 7,442 and 4,731 / 4,689", pick=3),
                  at(QPWR, "4,689 / 4,731 (A)"),
                  at(S84, "(capped at 7,442 and 4,689)", pick=1),
                  at("ROM die power-capped at 549.5 W, measured ASAP7 lane", "4,689")]),
    # ---------------------------------------------------------------- Qwen3 ROM / HBM
    dict(id="qwen.hdc_hbm_rate", section="Qwen3-8B ROM / HBM", cls="model",
         claim="HDC-HBM: the same core on six HBM stacks at the ROM's 3.5-bit weights (tokens/s)",
         binding=B(QB, 'hbm_comparator.8192["rom_format_3.5b"].tokens_s'),
         printed=[at("HDC-HBM: the same core on six stacks", "1,379")]),
    dict(id="qwen.rom_over_hdc_hbm", section="Qwen3-8B ROM / HBM", cls="model",
         claim="Qwen3-8B ROM / same core on six HBM stacks, per-user rate (derived from two calibrated rows)",
         binding=RATIO(B(QB, "power.points.ar_batch1.at.design.tokens_s"),
                       B(QB, 'hbm_comparator.8192["rom_format_3.5b"].tokens_s')),
         printed=[at(ABS, "it is 6.5× the same core"),
                  at(LEAD, "the two designs are 6.5× and 2.3×"),
                  at("Qwen3-8B, ROM ÷ same core on 6 HBM stacks", "6.5×"),
                  at(PAYOFF, "one user gets 6.5× the tokens per second"),
                  at(S84, "that is 6.5× the same core on six HBM stacks"),
                  at("HDC-HBM: the same core on six stacks", "6.5×")]),
    dict(id="qwen.ladder_s3_over_s2", section="Qwen3-8B ROM / HBM", cls="model",
         claim="Attribution ladder S3 / S2, Qwen3-8B",
         binding=B(DR, "models.qwen3.ladders.per_user[step=S3].multiplier"),
         printed=[at("S3 · specialized ROM accelerator", "4.84× S2")]),
    dict(id="qwen.ladder_s0", section="Qwen3-8B ROM / HBM", cls="third-party",
         claim="Ladder S0: cited B200 SGLang Qwen3-8B batch-1 rate (context match unverified)",
         binding=B(DR, "models.qwen3.ladders.per_user[step=S0].value"),
         printed=[at("S0 · GPU application / shipped collectives", "230 cited B200 SGLang")]),
    dict(id="qwen.ladder_s1", section="Qwen3-8B ROM / HBM", cls="model",
         claim="Ladder S1: idealized maximum-fusion B200, BF16",
         binding=B(DR, "models.qwen3.ladders.per_user[step=S1].value"),
         printed=[at("S1 · idealized maximum-fusion GPU", "457 modeled BF16")]),
    dict(id="qwen.ladder_s2", section="Qwen3-8B ROM / HBM", cls="model",
         claim="Ladder S1f/S2: 3.5-bit format / specialised HBM core at B200 bandwidth",
         binding=B(DR, "models.qwen3.ladders.per_user[step=S2].value"),
         printed=[at("S1 · idealized maximum-fusion GPU", "1,839 after a 3.5-bit format substep"),
                  at("S2 · specialized HBM accelerator", "1,839 modeled")]),
    dict(id="qwen.gpu_measured_bf16", section="Qwen3-8B ROM / HBM", cls="measured-gpu",
         claim="RTX PRO 6000 Blackwell (GB202) Qwen3-8B batch-1, BF16, vLLM (tokens/s)",
         binding=B(DR, "models.qwen3.points[0].y"),
         printed=[at("Serving systems and hardware roadmaps, however", "94 tokens/s at BF16")]),
    dict(id="qwen.gpu_measured_fp8", section="Qwen3-8B ROM / HBM", cls="measured-gpu",
         claim="RTX PRO 6000 Blackwell (GB202) Qwen3-8B batch-1, FP8, vLLM (tokens/s)",
         binding=B(DR, "models.qwen3.points[1].y"),
         printed=[at("Serving systems and hardware roadmaps, however", "151 at FP8")]),
    dict(id="qwen.h200_fp8", section="Qwen3-8B ROM / HBM", cls="model",
         claim="H200 FP8 Qwen3-8B batch-1, calibrated to NVIDIA NIM", binding=None,
         unbound="results/roofline/iso_area/qwen3_8b.json, the record Table 8-9 cites, is not on main "
                 "(last committed at b42f8606 on a side branch); no tracked record holds 217",
         printed=[at("Serving systems and hardware roadmaps, however", "217 on an H200 at FP8")]),
    dict(id="qwen.hbm_class_ceiling", section="Qwen3-8B ROM / HBM", cls="model",
         claim="HBM-class ceiling, (weights + KV) over six-stack bandwidth, and ROM / ceiling", binding=None,
         unbound="bound only in results/roofline/iso_area/qwen3_8b.json, which is not on main",
         printed=[at("HBM-class ceiling: (weights + KV)", "1,533"),
                  at("HBM-class ceiling: (weights + KV)", "5.8×")]),
    # ---------------------------------------------------------------- Qwen3 energy
    dict(id="qwen.energy_B", section="Qwen3-8B energy", cls="model",
         claim="Qwen3-8B ROM reticle energy per token at batch 1, scenario B (mJ)",
         binding=B(PS, f"{PB}.qwen3_8b_rom_8k.ar_batch1.energy_per_token_mj"),
         sensitivity=_power_variants("qwen3_8b_rom_8k.ar_batch1.energy_per_token_mj"),
         printed=[at(ABS, "88 and 123 mJ without speculation"),
                  at(DEPLOY, "spends 88 mJ per token at batch 1"),
                  at("Qwen3-8B energy per token at batch 1, power scenario B", "B: 88.1 /"),
                  at(QPWR, "88.1 / 123 mJ;"),
                  at(QPWR2, "(88.1 / 123 mJ"),
                  at("At large batch, energy per token is KV bytes", "ROM 88.1 mJ"),
                  at(S101, "spends 88.1 mJ per token")]),
    dict(id="qwen.energy_A", section="Qwen3-8B energy", cls="model",
         claim="Qwen3-8B ROM reticle energy per token at batch 1, scenario A (mJ)",
         binding=B(PS, f"{PA}.qwen3_8b_rom_8k.ar_batch1.energy_per_token_mj"),
         printed=[at(ABS, "88 and 123 mJ without speculation", pick=1),
                  at(DEPLOY, "123 against 595 mJ"),
                  at("Qwen3-8B energy per token at batch 1, power scenario B", "A: 123 /"),
                  at(QPWR, "88.1 / 123 mJ;", pick=1),
                  at(QPWR2, "(88.1 / 123 mJ", pick=1)]),
    dict(id="qwen.hbm_energy_B", section="Qwen3-8B energy", cls="model",
         claim="Same core on HBM at 3.5-bit weights, energy per token at batch 1, scenario B (mJ)",
         binding=B(QB, f"{QPB}.hbm_comparator.rom35_batch1.energy_per_token_mj"),
         printed=[at(DEPLOY, "against 560 mJ"),
                  at("Qwen3-8B energy per token at batch 1, power scenario B", "88.1 / 560 mJ", pick=1),
                  at("At large batch, energy per token is KV bytes", "the HBM core 560 mJ"),
                  at(S101, "against 560 mJ")]),
    dict(id="qwen.hbm_energy_A", section="Qwen3-8B energy", cls="model",
         claim="Same core on HBM at 3.5-bit weights, energy per token at batch 1, scenario A (mJ)",
         binding=B(QB, f"{QPA}.hbm_comparator.rom35_batch1.energy_per_token_mj"),
         printed=[at(DEPLOY, "123 against 595 mJ", pick=1),
                  at("Qwen3-8B energy per token at batch 1, power scenario B", "123 / 595 mJ", pick=1)]),
    dict(id="qwen.energy_ratio_B", section="Qwen3-8B energy", cls="model",
         claim="Qwen3-8B energy HBM / ROM at batch 1, same 3.5-bit weights, scenario B",
         binding=B(QB, f"{QPB}.ratios_batch1.hbm_rom_format_over_rom"),
         printed=[at(DEPLOY, "(6.4×;"),
                  at("Qwen3-8B energy per token at batch 1, power scenario B", "560 mJ: 6.4×", pick=1),
                  at("At large batch, energy per token is KV bytes", "(6.4×)")]),
    dict(id="qwen.energy_ratio_B_fp8", section="Qwen3-8B energy", cls="model",
         claim="Qwen3-8B energy HBM (FP8 weights) / ROM at batch 1, scenario B",
         binding=B(QB, f"{QPB}.ratios_batch1.hbm_over_rom"),
         printed=[at("Qwen3-8B energy per token at batch 1, power scenario B", "(13.2×)")]),
    dict(id="qwen.energy_ratio_A", section="Qwen3-8B energy", cls="model",
         claim="Qwen3-8B energy HBM / ROM at batch 1, same 3.5-bit weights, scenario A",
         binding=B(QB, f"{QPA}.ratios_batch1.hbm_rom_format_over_rom"),
         printed=[at(DEPLOY, "4.8×)"),
                  at("Qwen3-8B energy per token at batch 1, power scenario B", "595 mJ: 4.8×", pick=1)]),
    dict(id="qwen.energy_ratio_A_fp8", section="Qwen3-8B energy", cls="model",
         claim="Qwen3-8B energy HBM (FP8 weights) / ROM at batch 1, scenario A",
         binding=B(QB, f"{QPA}.ratios_batch1.hbm_over_rom"),
         printed=[at("Qwen3-8B energy per token at batch 1, power scenario B", "(9.7×)")]),
    dict(id="qwen.die_power_B", section="Qwen3-8B power", cls="model",
         claim="Qwen3-8B die power at the design rate, scenario B (W)",
         binding=B(PS, f"{PB}.qwen3_8b_rom_8k.ar_batch1.die_w_at_design_rate"),
         printed=[at(QPWR, "637 / 947 W"),
                  at(QPWR2, "637 / 947 W)")]),
    dict(id="qwen.die_power_A", section="Qwen3-8B power", cls="model",
         claim="Qwen3-8B die power at the design rate, scenario A (W)",
         binding=B(PS, f"{PA}.qwen3_8b_rom_8k.ar_batch1.die_w_at_design_rate"),
         printed=[at(QPWR, "637 / 947 W", pick=1),
                  at(QPWR2, "637 / 947 W)", pick=1)]),
    dict(id="qwen.provisioned_w", section="Qwen3-8B power", cls="model",
         claim="Qwen3-8B package provisioned power at 1.2 times the saturated worst case, scenario B (W)",
         binding=B(QB, f"{QPB}.worst_case.provisioned_w"),
         printed=[at("Provisioned power at 1.2× the saturated worst case: Qwen3-8B package", "1,608 W")]),
    dict(id="qwen.total_throughput", section="Qwen3-8B batching", cls="model",
         claim="Qwen3-8B reticle total throughput from batch 2 (KV-stream-bound)",
         binding=B(QB, f"{QPB}.rom.kv_bound_batch2.tokens_s"),
         printed=[at("Qwen3-8B reticle, total throughput from batch 2", "8,941 tok/s"),
                  at(S101B, "(8,941 tokens/s, KV-bound)")]),
    dict(id="qwen.hbm_batch128", section="Qwen3-8B batching", cls="model",
         claim="Same core on HBM at 128 users, total throughput",
         binding=B(QB, f"{QPB}.hbm_comparator.rom35_batch128.tokens_s"),
         printed=[at(S101B, "at 128 users (8,573)", pick=1)]),
    dict(id="qwen.energy_b128_rom", section="Qwen3-8B batching", cls="model",
         claim="Qwen3-8B ROM energy per token at 128 users, scenario B (mJ)",
         binding=B(QB, f"{QPB}.rom.batch128.energy_per_token_mj"),
         printed=[at("At large batch, energy per token is KV bytes", "88.8 vs 95.0 mJ")]),
    dict(id="qwen.energy_b128_table10", section="Qwen3-8B batching", cls="model",
         claim="Table 10-1: Qwen3-8B energy per token at 128 users, ROM vs HBM (mJ)", binding=None,
         unbound="no tracked record holds 83.1 or 89.2; Table 8-26 prints 88.8 vs 95.0 for the same "
                 "measure from results/arch/qwen3_budget.json -- the two tables disagree",
         printed=[at("Energy per token at 128 users (V4.1: 1,024 users)", "83.1 vs 89.2 mJ")]),
    # ---------------------------------------------------------------- quality
    dict(id="quality.contract_ppl_2k", section="Qwen3-8B quality", cls="measured-quality",
         claim="Arithmetic contract + FP8 KV: WikiText-2 perplexity change at 2K vs vendor BF16 (%)",
         binding=B(QQ, "modes.f_contract_kvfp8.wikitext2_2048.rel_delta_ppl", scale=100),
         printed=[at("Full Qwen3-8B quality against vendor BF16", "-0.16%")]),
    dict(id="quality.contract_ppl_8k", section="Qwen3-8B quality", cls="measured-quality",
         claim="Arithmetic contract + FP8 KV: WikiText-2 perplexity change at 8K (%)",
         binding=B(QQ, "modes.f_contract_kvfp8.wikitext2_8192.rel_delta_ppl", scale=100),
         printed=[at("Full Qwen3-8B quality against vendor BF16", "/ -0.09%")]),
    dict(id="quality.contract_mmlu", section="Qwen3-8B quality", cls="measured-quality",
         claim="Arithmetic contract + FP8 KV: MMLU change (points)",
         binding=B(QQ, "modes.f_contract_kvfp8.mmlu.delta_pt"),
         printed=[at("Full Qwen3-8B quality against vendor BF16", "-0.3 pt")]),
    dict(id="quality.w35_ppl_2k", section="Qwen3-8B quality", cls="measured-quality",
         claim="Adding the 3.5-bit INT3/INT6 GPTQ stand-in: WikiText-2 perplexity change at 2K (%)",
         binding=B(QQ, "modes.e_full_gptq.wikitext2_2048.rel_delta_ppl", scale=100),
         printed=[at("Full Qwen3-8B quality against vendor BF16", "+22.7%")]),
    dict(id="quality.w35_ppl_8k", section="Qwen3-8B quality", cls="measured-quality",
         claim="Adding the 3.5-bit stand-in: WikiText-2 perplexity change at 8K (%)",
         binding=B(QQ, "modes.e_full_gptq.wikitext2_8192.rel_delta_ppl", scale=100),
         printed=[at("Full Qwen3-8B quality against vendor BF16", "+29.6%")]),
    dict(id="quality.w35_mmlu", section="Qwen3-8B quality", cls="measured-quality",
         claim="Adding the 3.5-bit stand-in: MMLU change (points)",
         binding=B(QQ, "modes.e_full_gptq.mmlu.delta_pt"),
         printed=[at("Full Qwen3-8B quality against vendor BF16", "-7.5 pt")]),
    # ---------------------------------------------------------------- V4.1 rates
    dict(id="v41.rate_1m", section="DeepSeek-V4.1 rate", cls="model",
         claim="V4.1 ROM array, adopted design, 1M, batch 1, per-user rate (collective tails bench-measured)",
         binding=B(LN, "design_point.1048576.ar"),
         sensitivity=[S("collective exposure without the levers (ablation)", B(LN, "design_point_no_levers.1048576.ar")),
                      S("every collective fully overlapped (gate C7 recovered)", B(LN, "design_point_overlap_assumed.1048576.ar")),
                      S("rack geometry: 29 ring cables at worst layout length", B(RK, "reprice_sensitivity.geometry.rate_tokens_s"))],
         printed=[at(LEAD, "at 1M context gets 8,185 tokens/s", pick=1),
                  at(ABS, "the adopted design decodes 8,185 tokens/s"),
                  at("DeepSeek-V4.1 array, adopted design, per user, batch 1", "8,185 / 8,568"),
                  at("S3 · specialized ROM accelerator", "8,185 design-point model"),
                  at(S84, "decodes 8,185 tokens/s per user at 1M"),
                  at(S84V, "reaches 8,185 tokens/s per user"),
                  at("ROM array, adopted design (top of the latency ladder", "8,185")]),
    dict(id="v41.rate_200k", section="DeepSeek-V4.1 rate", cls="model",
         claim="V4.1 ROM array, adopted design, 200K, batch 1, per-user rate",
         binding=B(LN, "design_point.200000.ar"),
         sensitivity=[S("without the levers", B(LN, "design_point_no_levers.200000.ar")),
                      S("fully overlapped", B(LN, "design_point_overlap_assumed.200000.ar"))],
         printed=[at(LEAD, "(8,568 at 200K)"),
                  at(ABS, "8,568 and 24,864 at 200K"),
                  at("DeepSeek-V4.1 array, adopted design, per user, batch 1", "8,185 / 8,568", pick=1),
                  at(S84, "8,568 at 200K"),
                  at("ROM array, adopted design (top of the latency ladder", "8,568"),
                  at("V4.1 array at 200K: per-user rate flat to 28 users", "8,568 ·")]),
    dict(id="v41.mtp_1m", section="DeepSeek-V4.1 rate", cls="model",
         claim="V4.1 adopted design with native MTP (tau 5.0, third-party DSpark acceptance), 1M",
         binding=B(LN, "design_point.1048576.mtp"),
         sensitivity=[S("without the levers", B(LN, "design_point_no_levers.1048576.mtp")),
                      S("fully overlapped", B(LN, "design_point_overlap_assumed.1048576.mtp"))],
         printed=[at(ABS, "(23,818 with its native MTP"),
                  at("DeepSeek-V4.1 array, adopted design, per user, batch 1", "(23,756 / 24,797)"),
                  at(S84, "(23,756 and 24,797 with MTP"),
                  at("ROM array, adopted design (top of the latency ladder", "23,756"),
                  at(C7, "23,818 at 1M")]),
    dict(id="v41.mtp_200k", section="DeepSeek-V4.1 rate", cls="model",
         claim="V4.1 adopted design with MTP, 200K",
         binding=B(LN, "design_point.200000.mtp"),
         printed=[at(ABS, "8,568 and 24,864 at 200K", pick=1),
                  at("DeepSeek-V4.1 array, adopted design, per user, batch 1", "23,756 / 24,797", pick=1),
                  at("ROM array, adopted design (top of the latency ladder", "24,797")]),
    dict(id="v41.overlap_1m", section="DeepSeek-V4.1 rate", cls="model",
         claim="V4.1 with every collective fully overlapped (conditional on gate C7), 1M",
         binding=B(LN, "design_point_overlap_assumed.1048576.ar"),
         printed=[at(ABS, "full overlap would give 8,622"),
                  at("DeepSeek-V4.1 array, adopted design, per user, batch 1", "8,622 / 9,041"),
                  at(FIG21, "they would be 8,622 / 23,578"),
                  at("S3 · specialized ROM accelerator", "(8,622 with full overlap)"),
                  at(S84, "8,622 and 9,041 if the collectives"),
                  at("ROM array, same design with every collective fully overlapped", "8,622")]),
    dict(id="v41.overlap_200k", section="DeepSeek-V4.1 rate", cls="model",
         claim="V4.1 fully overlapped, 200K", binding=B(LN, "design_point_overlap_assumed.200000.ar"),
         printed=[at("DeepSeek-V4.1 array, adopted design, per user, batch 1", "8,622 / 9,041", pick=1),
                  at("ROM array, same design with every collective fully overlapped", "9,041")]),
    dict(id="v41.overlap_mtp_1m", section="DeepSeek-V4.1 rate", cls="model",
         claim="V4.1 fully overlapped with MTP, 1M", binding=B(LN, "design_point_overlap_assumed.1048576.mtp"),
         printed=[at("DeepSeek-V4.1 array, adopted design, per user, batch 1", "(23,517 / 24,536)"),
                  at("ROM array, same design with every collective fully overlapped", "23,517"),
                  at(C7, "the overlap-assumed 23,578")]),
    dict(id="v41.overlap_mtp_200k", section="DeepSeek-V4.1 rate", cls="model",
         claim="V4.1 fully overlapped with MTP, 200K", binding=B(LN, "design_point_overlap_assumed.200000.mtp"),
         printed=[at("DeepSeek-V4.1 array, adopted design, per user, batch 1", "23,517 / 24,536", pick=1),
                  at("ROM array, same design with every collective fully overlapped", "24,536")]),
    dict(id="v41.no_levers_1m", section="DeepSeek-V4.1 rate", cls="model",
         claim="Ablation: collective exposure measured without the levers, 1M",
         binding=B(LN, "design_point_no_levers.1048576.ar"),
         printed=[at("Ablation: same design, collective exposure measured without the levers", "7,579")]),
    dict(id="v41.no_levers_200k", section="DeepSeek-V4.1 rate", cls="model",
         claim="Ablation without the levers, 200K", binding=B(LN, "design_point_no_levers.200000.ar"),
         printed=[at("Ablation: same design, collective exposure measured without the levers", "7,905")]),
    dict(id="v41.levers_recovered", section="DeepSeek-V4.1 rate", cls="model",
         claim="Share of the overlap loss the four adopted collective levers recover, 1M (%)",
         binding=B(LN, "collective_exposure.recovered_share.1048576.ar", scale=100),
         printed=[at(ABS, "recover about 58% of the loss"),
                  at(C7, "about 58% of the overlap loss")]),
    dict(id="v41.golden_orders", section="DeepSeek-V4.1 rate", cls="model",
         claim="Golden (sequential) summation orders: V4.1 ceiling at any width, 200K",
         binding=B(AB, "ablations_tokens_s_per_user.golden_orders.200000"),
         printed=[at("Golden (sequential) summation orders", "1,171 tok/s"),
                  at("The reference's summation order is a latency wall", "1,171 tok/s"),
                  at(ABS, "near 1,170 tokens/s", tol="0.2%")]),
    # ---------------------------------------------------------------- V4.1 comparator
    dict(id="v41.hbm_rate", section="DeepSeek-V4.1 ROM / HBM", cls="model",
         claim="Best HBM comparator (96-die tensor group, NVL72-class switched domain), batch 1",
         binding=B(SW, "configs.nvl_0p9_nvls.1048576.best_ar.rate"),
         printed=[at("S2 · specialized HBM accelerator", "3,580 modeled"),
                  at(S84V, "against 3,580 for the HBM comparator"),
                  at("HBM comparator at its best: 96-die tensor group", "3,580")]),
    dict(id="v41.hbm_mtp", section="DeepSeek-V4.1 ROM / HBM", cls="model",
         claim="Best HBM comparator with MTP (m = 6), batch 1",
         binding=B(SW, "configs.nvl_0p9_nvls.1048576.best_mtp.rate"),
         printed=[at("HBM comparator at its best: 96-die tensor group", "11,978")]),
    dict(id="v41.ratio_1m", section="DeepSeek-V4.1 ROM / HBM", cls="model",
         claim="V4.1 ROM array / best equal-logic-area HBM array, per-user rate, 1M",
         binding=B(SW, "ratios_batch1.1048576.ar.ratio"),
         sensitivity=_fabric_ratio("1048576", "ar"),
         printed=[at(LEAD, "the two designs are 6.5× and 2.3×", pick=1),
                  at(ABS, "That is 2.3× an HBM array of equal logic area"),
                  at("V4.1 ROM array ÷ HBM array of equal logic area at its best", "2.3× / 2.4×"),
                  at(PAYOFF, "reaches 2.3× the rate"),
                  at("S3 · specialized ROM accelerator", "2.29× S2"),
                  at(S84, "2.3× and 2.4× an HBM array"),
                  at("ROM ÷ best HBM (headline row)", "2.29×"),
                  at("Per-user rate, batch 1, without / with MTP (τ = 5.0)", "2.29× / 1.98×"),
                  at("A wide-group HBM machine gains more from MTP", "ROM ÷ HBM is 2.3×")]),
    dict(id="v41.ratio_200k", section="DeepSeek-V4.1 ROM / HBM", cls="model",
         claim="V4.1 ROM / best HBM, per-user rate, 200K",
         binding=B(SW, "ratios_batch1.200000.ar.ratio"),
         sensitivity=_fabric_ratio("200000", "ar"),
         printed=[at("V4.1 ROM array ÷ HBM array of equal logic area at its best", "2.3× / 2.4×", pick=1),
                  at(S84, "2.3× and 2.4× an HBM array", pick=1),
                  at("ROM ÷ best HBM (headline row)", "2.39×"),
                  at("Per-user rate, batch 1, without / with MTP (τ = 5.0)", "2.39× / 2.07×")]),
    dict(id="v41.ratio_mtp_1m", section="DeepSeek-V4.1 ROM / HBM", cls="model",
         claim="V4.1 ROM / best HBM, both with MTP, 1M",
         binding=B(SW, "ratios_batch1.1048576.mtp.ratio"),
         sensitivity=_fabric_ratio("1048576", "mtp"),
         printed=[at(ABS, "and 2.0× with MTP on both"),
                  at("V4.1 ROM array ÷ HBM array of equal logic area at its best", "(2.0× / 2.1×)"),
                  at(S84, "2.0× and 2.1× when both machines speculate"),
                  at("ROM ÷ best HBM (headline row)", "1.98×"),
                  at("Per-user rate, batch 1, without / with MTP (τ = 5.0)", "2.29× / 1.98×", pick=1)]),
    dict(id="v41.ratio_mtp_200k", section="DeepSeek-V4.1 ROM / HBM", cls="model",
         claim="V4.1 ROM / best HBM, both with MTP, 200K",
         binding=B(SW, "ratios_batch1.200000.mtp.ratio"),
         printed=[at("V4.1 ROM array ÷ HBM array of equal logic area at its best", "2.0× / 2.1×)", pick=1),
                  at("ROM ÷ best HBM (headline row)", "2.07×"),
                  at("Per-user rate, batch 1, without / with MTP (τ = 5.0)", "2.39× / 2.07×", pick=1)]),
    dict(id="v41.ladder_s0", section="DeepSeek-V4.1 ROM / HBM", cls="model",
         claim="Ladder S0: 50 B200s, the present 209-collective graph on cited NCCL latency",
         binding=B(DR, "models.v41.ladders.per_user[step=S0].value"),
         printed=[at("S0 · GPU application / shipped collectives", "924 modeled on cited NCCL latency")]),
    dict(id="v41.ladder_s1", section="DeepSeek-V4.1 ROM / HBM", cls="model",
         claim="Ladder S1: same GPUs with the best measured all-reduce",
         binding=B(DR, "models.v41.ladders.per_user[step=S1].value"),
         printed=[at("S1 · idealized maximum-fusion GPU", "1,879 modeled with the best measured all-reduce")]),
    # ---------------------------------------------------------------- V4.1 energy
    dict(id="v41.energy_rom_1m", section="DeepSeek-V4.1 energy", cls="model",
         claim="V4.1 ROM array energy per token at 1M, batch 1, scenario B (J)",
         binding=B(PS, f"{POB}.1048576.ar_batch1.rom_energy_j"),
         sensitivity=[S("scenario A (measured lane)", B(PS, f"{POA}.1048576.ar_batch1.rom_energy_j"))],
         printed=[at(DEPLOY, "spends 1.57 J per token at batch 1"),
                  at("Energy per token, batch 1 (both static-dominated)", "2.07 vs 6.70 J"),
                  at("Static power decides array energy at low batch", "1.57 J per token")]),
    dict(id="v41.energy_hbm_1m", section="DeepSeek-V4.1 energy", cls="model",
         claim="Best HBM comparator energy per token at 1M, batch 1, scenario B (J)",
         binding=B(PS, f"{POB}.1048576.ar_batch1.hbm_energy_j"),
         printed=[at(DEPLOY, "against 5.94 J for the best HBM comparator"),
                  at("Energy per token, batch 1 (both static-dominated)", "2.07 vs 6.70 J", pick=1)]),
    dict(id="v41.energy_ratio_1m", section="DeepSeek-V4.1 energy", cls="model",
         claim="V4.1 energy per token HBM / ROM at 1M, batch 1, scenario B",
         binding=B(PS, f"{POB}.1048576.ar_batch1.energy_hbm_over_rom"),
         sensitivity=[S("scenario A (measured lane)", B(PS, f"{POA}.1048576.ar_batch1.energy_hbm_over_rom"))],
         printed=[at(ABS, "and 3.8× lower at batch 1"),
                  at("V4.1 energy per token, 1M, HBM ÷ ROM on one power model", "3.2× / 7.5×"),
                  at("Energy per token, batch 1 (both static-dominated)", "6.70 J: 3.2×", pick=1),
                  at("Static power decides array energy at low batch", "3.8× less than the best HBM comparator")]),
    dict(id="v41.energy_ratio_1m_A", section="DeepSeek-V4.1 energy", cls="model",
         claim="V4.1 energy HBM / ROM at 1M, batch 1, scenario A (measured lane)",
         binding=B(PS, f"{POA}.1048576.ar_batch1.energy_hbm_over_rom"),
         printed=[at("Table 8-11. ROM ÷ best HBM comparator, adopted ROM design", "ratio at 1M is 3.3×", pick=1)]),
    dict(id="v41.energy_ratio_1m_mtp", section="DeepSeek-V4.1 energy", cls="model",
         claim="V4.1 energy HBM / ROM at 1M, batch 1, with MTP, scenario B",
         binding=B(PS, f"{POB}.1048576.mtp_batch1.energy_hbm_over_rom"),
         printed=[at("V4.1 energy per token, 1M, HBM ÷ ROM on one power model", "(3.9× / 10.1×)"),
                  at("Energy per token, batch 1, with MTP", "2.40 J: 3.3×", pick=1)]),
    dict(id="v41.energy_ratio_1m_fill28", section="DeepSeek-V4.1 energy", cls="model",
         claim="V4.1 energy HBM / ROM at 1M, 28-user fill, scenario B",
         binding=B(PS, f"{POB}.1048576.fill28.energy_hbm_over_rom"),
         printed=[at(ABS, "8.0–10.1× lower at a filled 28-user pipeline"),
                  at("V4.1 energy per token, 1M, HBM ÷ ROM on one power model", "3.2× / 7.5×", pick=1),
                  at("Energy per token, 28-user fill: ROM vs HBM", "1,023 mJ: 7.5×", pick=1),
                  at("Static power decides array energy at low batch", "8.0–10.1× at the fill")]),
    dict(id="v41.energy_ratio_1m_fill28_mtp", section="DeepSeek-V4.1 energy", cls="model",
         claim="V4.1 energy HBM / ROM at 1M, 28-user fill, with MTP, scenario B",
         binding=B(PS, f"{POB}.1048576.fill28_mtp.energy_hbm_over_rom"),
         printed=[at(ABS, "8.0–10.1× lower", pick=1),
                  at("V4.1 energy per token, 1M, HBM ÷ ROM on one power model", "3.3× / 9.8×", pick=1),
                  at("Energy per token, 28-user fill, with MTP", "587 mJ: 9.8×", pick=1)]),
    dict(id="v41.energy_rom_1m_fill28", section="DeepSeek-V4.1 energy", cls="model",
         claim="V4.1 ROM energy per token at 1M, 28-user fill, scenario B (mJ)",
         binding=B(PS, f"{POB}.1048576.fill28.rom_energy_j", scale=1000),
         printed=[at(DEPLOY, "118 mJ against 944 mJ"),
                  at("Energy per token, 28-user fill: ROM vs HBM", "136 vs 1,023 mJ"),
                  at("Static power decides array energy at low batch", "118 mJ at the 28-user fill")]),
    dict(id="v41.energy_hbm_1m_fill28", section="DeepSeek-V4.1 energy", cls="model",
         claim="Best HBM comparator energy per token at 1M, 28-user fill, scenario B (mJ)",
         binding=B(PS, f"{POB}.1048576.fill28.hbm_energy_j", scale=1000),
         printed=[at(DEPLOY, "118 mJ against 944 mJ", pick=1),
                  at("Energy per token, 28-user fill: ROM vs HBM", "136 vs 1,023 mJ", pick=1)]),
    dict(id="v41.energy_rom_200k", section="DeepSeek-V4.1 energy", cls="model",
         claim="V4.1 ROM energy per token at 200K, batch 1, scenario B (J)",
         binding=B(PS, f"{POB}.200000.ar_batch1.rom_energy_j"),
         printed=[at("Energy per token, batch 1 (both static-dominated)", "1.96 vs 6.68 J")]),
    dict(id="v41.energy_ratio_200k", section="DeepSeek-V4.1 energy", cls="model",
         claim="V4.1 energy HBM / ROM at 200K, batch 1, scenario B",
         binding=B(PS, f"{POB}.200000.ar_batch1.energy_hbm_over_rom"),
         printed=[at("Energy per token, batch 1 (both static-dominated)", "6.68 J: 3.4×", pick=1)]),
    dict(id="v41.agg_ratio_fill28_1m", section="DeepSeek-V4.1 batching", cls="model",
         claim="V4.1 aggregate throughput ROM / HBM at 1M, 28 users, without MTP",
         binding=B(PS, f"{POB}.1048576.fill28.rate_rom_over_hbm"),
         printed=[at("Aggregate throughput, 28 users, without / with MTP", "6.7× / 11.6×")]),
    dict(id="v41.agg_ratio_fill28_1m_mtp", section="DeepSeek-V4.1 batching", cls="model",
         claim="V4.1 aggregate throughput ROM / HBM at 1M, 28 users, with MTP",
         binding=B(PS, f"{POB}.1048576.fill28_mtp.rate_rom_over_hbm"),
         printed=[at("Aggregate throughput, 28 users, without / with MTP", "6.7× / 11.6×", pick=1)]),
    dict(id="v41.agg_ratio_fill28_1m_s101", section="DeepSeek-V4.1 batching", cls="model",
         claim="§10.1 prose: V4.1 aggregate ROM / best HBM at the 28-user fill, 1M (same measure as Table 8-11)",
         binding=B(PS, f"{POB}.1048576.fill28.rate_rom_over_hbm"),
         printed=[at(S101B, "aggregate is 6.7× the best HBM array's")]),
    dict(id="v41.agg_ratio_fill28_1m_mtp_s101", section="DeepSeek-V4.1 batching", cls="model",
         claim="§10.1 prose: V4.1 aggregate ROM / best HBM at the 28-user fill, 1M, with MTP",
         binding=B(PS, f"{POB}.1048576.fill28_mtp.rate_rom_over_hbm"),
         printed=[at(S101B, "(11.6× with MTP)")]),
    dict(id="v41.agg_1024_200k", section="DeepSeek-V4.1 batching", cls="model",
         claim="V4.1 array aggregate throughput at 1,024 users, 200K (thousand tokens/s)",
         binding=B(LN, "energy.200000.sat1024.rom.aggregate_tokens_s", scale=0.001),
         printed=[at("V4.1 array at 200K: per-user rate flat to 28 users", "891 K tok/s")]),
    dict(id="v41.users_200k", section="DeepSeek-V4.1 batching", cls="model",
         claim="Users held in four HBM3E stacks per die at 200K",
         binding=B(AB, "capacity.200000.rom_users"),
         printed=[at("V4.1 array at 200K: per-user rate flat to 28 users", "5,018 users")]),
    dict(id="v41.agg_ratio_1024_1m", section="DeepSeek-V4.1 batching", cls="model",
         claim="Adopted design vs best comparator aggregate at 1,024 users, 1M",
         binding=B(PS, f"{POB}.1048576.saturated_batch1024.rate_rom_over_hbm"),
         printed=[at("Aggregate throughput, 1,024 users, without / with MTP", "10.8× / 11.4×"),
                  at("Total throughput, ROM vs HBM comparator as defined above", "13.2× / 10.8×", pick=1)]),
    dict(id="v41.agg_ratio_1024_200k", section="DeepSeek-V4.1 batching", cls="model",
         claim="Adopted design vs best comparator aggregate at 1,024 users, 200K",
         binding=B(PS, f"{POB}.200000.saturated_batch1024.rate_rom_over_hbm"),
         printed=[at("Aggregate throughput, 1,024 users, without / with MTP", "13.2× / 11.4×"),
                  at("Total throughput, ROM vs HBM comparator as defined above", "13.2× / 10.8×")]),
    dict(id="v41.rack_kw", section="DeepSeek-V4.1 power", cls="model",
         claim="V4.1 rack provisioned at 1.2 times the saturated worst case (kW)",
         binding=B(RK, "comparison[0].rack_kw"),
         printed=[at(DEPLOY, "provisioned at 53.9 kW"),
                  at("Provisioned power at 1.2× the saturated worst case: Qwen3-8B package", "53.9 kW"),
                  at("A fixed schedule bounds power", "provisioned at 53.9 kW")]),
    dict(id="v41.nvl72_kw", section="DeepSeek-V4.1 power", cls="third-party",
         claim="GB200 NVL72 rack power (cited)", binding=B(RK, "comparison[1].rack_kw"),
         printed=[at(DEPLOY, "against 132 kW for a GB200 NVL72"),
                  at("Provisioned power at 1.2× the saturated worst case: Qwen3-8B package", "132 kW")]),
    # ---------------------------------------------------------------- synchronisation
    dict(id="sync.handoff_ratio", section="Synchronisation", cls="measured-gpu",
         claim="On-chip dependent handoff, GPU / OpenTallas (GB202 measured vs RTL)",
         binding=B(SC, "rows[0].ratio"),
         printed=[at("Synchronisation, GPU ÷ OpenTallas", "77× /"),
                  at("The synchronisation advantage is on chip", "77× and 208×")]),
    dict(id="sync.handoff_gpu_ns", section="Synchronisation", cls="measured-gpu",
         claim="GB202 measured on-chip dependent handoff (ns)", binding=B(SC, "rows[0].gpu.value"),
         printed=[at(ABS, "against 371 ns measured on a GB202 GPU")]),
    dict(id="sync.collective_floor", section="Synchronisation", cls="model",
         claim="4-die collective vs the GB200 speed-of-light floor (low end of the printed range)",
         binding=B(SC, "rows[4].ratio_vs.sol_floor"),
         printed=[at("Synchronisation, GPU ÷ OpenTallas", "7.9–13.4×"),
                  at(ABS, "narrows to 8–13× the best measured GB200 collective"),
                  at("The synchronisation advantage is on chip", "7.9–13.4× a GB200")]),
    dict(id="sync.collective_best", section="Synchronisation", cls="model",
         claim="4-die collective vs the best measured GB200 kernel (high end)",
         binding=B(SC, "rows[4].ratio"),
         printed=[at("Synchronisation, GPU ÷ OpenTallas", "7.9–13.4×", pick=1),
                  at(ABS, "narrows to 8–13×", pick=1)]),
    dict(id="sync.per_token", section="Synchronisation", cls="model",
         claim="Synchronisation per V4.1 token at 1M, GPU / OpenTallas, same graph",
         binding=B(SC, "rows[6].ratio"),
         printed=[at("Synchronisation, GPU ÷ OpenTallas", "/ 17×"),
                  at("The synchronisation advantage is on chip", "17× per V4.1 token")]),
    dict(id="sync.gpu_boundary_low", section="Synchronisation", cls="measured-gpu",
         claim="GPU all-SM boundary, vector delivered, best design (ns)",
         binding=B(GG, "summary_table[design=3d_sharded1_rep8].bf16_8KiB_min_ns"),
         printed=[at("GPU all-SM boundary, vector delivered", "1,004–1,151 ns")]),
    dict(id="sync.gpu_boundary_high", section="Synchronisation", cls="measured-gpu",
         claim="GPU all-SM boundary, vector delivered, flag-in-data design (ns)",
         binding=B(GG, "summary_table[design=2d_ll16_rep8].fp32_16KiB_min_ns"),
         printed=[at("GPU all-SM boundary, vector delivered", "1,004–1,151 ns", pick=1)]),
    dict(id="sync.handoff_cycles", section="Synchronisation", cls="measured-RTL",
         claim="OpenTallas on-chip dependent handoff (cycles)", binding=None,
         unbound="results/arch/sync_cost_table.json carries 4.8 ns and the phrase '5-cycle' only as note "
                 "text; no record field holds the cycle count",
         printed=[at(ABS, "a dependent handoff costs 5 cycles in RTL")]),
    # ---------------------------------------------------------------- energy cross-check
    dict(id="energy.common_kv_ratio", section="Energy cross-check", cls="model",
         claim="Reduced Qwen3 step, common HBM KV: energy HBM weights / ROM weights (derived)", binding=None,
         unbound="results/physical_abi3/asap7/signoff/energy_common_kv.json, the record Figures 8-1/8-2 cite, is "
                 "not on main (only on a side branch at 66434aa3); no tracked record holds 5.7 or 58.82/335.35",
         printed=[at(ABS, "gives a derived 5.7× energy ratio"),
                  at("Energy per step, same core: HBM ÷ ROM (reduced Qwen3, ASAP7)", "5.7×"),
                  at(S84E, "(5.7×)"),
                  at(S101, "gives 5.7× lower energy")]),
    dict(id="energy.common_kv_rom_uj", section="Energy cross-check", cls="model",
         claim="Reduced Qwen3 step energy with ROM weights, common HBM KV (uJ)", binding=None,
         unbound="energy_common_kv.json not on main (see energy.common_kv_ratio)",
         printed=[at(S84E, "the ROM-weight step is 58.82 µJ")]),
    dict(id="energy.common_kv_hbm_uj", section="Energy cross-check", cls="model",
         claim="Reduced Qwen3 step energy with HBM weights, common HBM KV (uJ)", binding=None,
         unbound="energy_common_kv.json not on main (see energy.common_kv_ratio)",
         printed=[at(S84E, "versus 335.35 µJ")]),
    dict(id="energy.mac_pj", section="Energy cross-check", cls="measured-physical",
         claim="Routed matrix-engine energy per MAC in the reduced step (pJ, ASAP7)",
         binding=B(PS, "mac_pj.A_measured_implementation.qwen3_w4a8"),
         printed=[at(S84E, "3.97 pJ per MAC"),
                  at("Reduced Qwen3 routed matrix-engine energy, pJ per MAC (ASAP7)", "3.97")]),
    # ---------------------------------------------------------------- RTL gates
    dict(id="rtl.qwen_reduced_token", section="RTL gates", cls="measured-RTL",
         claim="Reduced Qwen3 token, bit-exact in logits, vector memory and KV (cycles)", binding=None,
         unbound="no tracked record under results/ holds 24,992 cycles",
         printed=[at("Reduced Qwen3 token, bit-exact in logits", "24,992 cycles")]),
    dict(id="rtl.v41_reduced_token", section="RTL gates", cls="measured-RTL",
         claim="Reduced DeepSeek-V4.1 token, 40 layers, bit-exact (cycles)",
         binding=B("results/rtl/hdc_v41_decode_campaign.json", "single_step.cycles"),
         printed=[at("Reduced DeepSeek-V4.1 token, 40 layers, bit-exact", "344,109 cycles")]),
    dict(id="rtl.egather_bw", section="RTL gates", cls="measured-RTL",
         claim="Engram per-bank gather, measured bytes per cycle",
         binding=B("results/rtl/hdc_v41x_egather_campaign.json", "spec.measured_bytes_per_cycle"),
         printed=[at("V4.1 blocks against their benches", "32.9 B/cycle"),
                  at("600 shipped-geometry and 436 vehicle tokens", "= 32.9 B/cycle")]),
    dict(id="rtl.egather_required", section="RTL gates", cls="model",
         claim="Engram gather requirement (bytes per cycle)",
         binding=B("results/rtl/hdc_v41x_egather_campaign.json", "spec.required_bytes_per_cycle"),
         printed=[at("V4.1 blocks against their benches", "(≥13.7)")]),
    dict(id="rtl.select_rate", section="RTL gates", cls="measured-RTL",
         claim="Index top-512 select, ingest scores per cycle (specification row)",
         binding=B("results/rtl/hdc_v41x_sel_campaign.json", "spec.ingest_scores_per_cycle.spec"),
         printed=[at("V4.1 blocks against their benches", "64 scores/cycle")]),
    dict(id="rtl.select_tail", section="RTL gates", cls="measured-RTL",
         claim="Index top-512 select, measured tail at 200K per die (cycles)",
         binding=B("results/rtl/hdc_v41x_sel_campaign.json", "spec.tail_200k_per_die.measured_max"),
         printed=[at("V4.1 blocks against their benches", "tail 149")]),
    dict(id="rtl.hcp_six", section="RTL gates", cls="measured-RTL",
         claim="Hyper-connection projection, 2,048 lanes, six positions (cycles)",
         binding=B("results/rtl/hdc_v41x_hcp_campaign.json", "spec_check.six_positions_2048_lanes.measured"),
         printed=[at("within the sublayer body, also for MTP", "1,578 for six")]),
    dict(id="rtl.qwen_vector_multi", section="RTL gates", cls="measured-RTL",
         claim="Qwen3 integrated vector core, 18 steps, one-cycle behavioural HBM (cycles)",
         binding=B("results/rtl/hdc_qwen_vector_system_multi_g4sw16.json", "summary.total_cycles"),
         printed=[at("Qwen3-8B integrated vector core, physical-HBM KV, empty cache", "439,897 cycles")]),
    dict(id="rtl.qwen_vector_timed", section="RTL gates", cls="measured-RTL",
         claim="Same 18 steps on the timed four-pseudo-channel KV-HBM controller (cycles)",
         binding=B("results/rtl/hdc_qwen_vector_system_timed_g4sw16.json", "summary.total_cycles"),
         printed=[at("Qwen3-8B integrated vector core, same 18 steps on the timed", "492,687 core cycles")]),
    dict(id="rtl.matched_rom", section="RTL gates", cls="measured-RTL",
         claim="Matched vector core, ROM weights, 18 steps (summed core cycles)",
         binding=B("results/rtl/hdc_qwen_vector_matched_weight_full_g4sw16.json", "rom.summary.total_cycles"),
         printed=[at("Qwen3-8B matched vector core, ROM weights against HBM weights", "494,099 summed core cycles"),
                  at("Same controller, ROM or HBM weights", "494,099")]),
    dict(id="rtl.matched_hbm", section="RTL gates", cls="measured-RTL",
         claim="Matched vector core, HBM weights through the shared controller (summed core cycles)",
         binding=B("results/rtl/hdc_qwen_vector_matched_weight_full_g4sw16.json", "hbm.summary.total_cycles"),
         printed=[at("Qwen3-8B matched vector core, ROM weights against HBM weights", "521,782"),
                  at("Same controller, ROM or HBM weights", "521,782")]),
    dict(id="rtl.matched_ratio", section="RTL gates", cls="measured-RTL",
         claim="Matched vector core, HBM-weight cycles over ROM-weight cycles (derived, %)",
         binding=RATIO(B("results/rtl/hdc_qwen_vector_matched_weight_full_g4sw16.json", "hbm.summary.total_cycles"),
                       B("results/rtl/hdc_qwen_vector_matched_weight_full_g4sw16.json", "rom.summary.total_cycles")),
         derived_as="(ratio - 1) x 100",
         printed=[at("Qwen3-8B matched vector core, ROM weights against HBM weights", "(+5.60%)"),
                  at("Same controller, ROM or HBM weights", "(+5.60%")]),
    dict(id="rtl.qwen_ctx_2048", section="RTL gates", cls="measured-RTL",
         claim="Qwen3 vector core, reducer LV=7, one token at position 2047 (core cycles)",
         binding=B("results/rtl/hdc_qwen_context_2048.json", "token.cycles"),
         printed=[at("Qwen3-8B vector core with the reducer at LV=7", "1,357,554 core cycles")]),
    dict(id="rtl.qwen_ctx_1024", section="RTL gates", cls="measured-RTL",
         claim="Qwen3 vector core, reducer LV=6, one token at position 1023 (core cycles)",
         binding=B("results/rtl/hdc_qwen_context_1024.json", "token.cycles"),
         printed=[at("Qwen3-8B vector core with the reducer at LV=6", "687,598 core cycles")]),
    dict(id="rtl.qwen_ctx_512", section="RTL gates", cls="measured-RTL",
         claim="Qwen3 vector core, reducer LV=5, one token at position 511 (core cycles)",
         binding=B("results/rtl/hdc_qwen_context_512.json", "token.cycles"),
         printed=[at("Qwen3-8B vector core with the reducer at LV=5", "321,363 core cycles")]),
    dict(id="rtl.qwen_ctx_256", section="RTL gates", cls="measured-RTL",
         claim="Qwen3 vector core, reducer LV=4, one token at position 255 (core cycles)",
         binding=B("results/rtl/hdc_qwen_long_context_256_control.json", "token.cycles"),
         printed=[at("Qwen3-8B vector core at the LV=4 reducer limit, one token at position 255", "192,856 core cycles")]),
    dict(id="rtl.qwen_scalar_rom", section="RTL gates", cls="measured-RTL",
         claim="Scalar-controller matched gate, ROM weights, one token (cycles)",
         binding=B("results/rtl/hdc_qwen_matched_weight_single.json", "rom.cycles"),
         printed=[at("Same controller, ROM or HBM weights", "30,127 cycles")]),
    dict(id="rtl.qwen_scalar_hbm", section="RTL gates", cls="measured-RTL",
         claim="Scalar-controller matched gate, HBM weights, one token (cycles)",
         binding=B("results/rtl/hdc_qwen_matched_weight_single.json", "hbm.cycles"),
         printed=[at("Same controller, ROM or HBM weights", "30,539 with HBM weights")]),
    dict(id="rtl.v41_pooled_multi", section="RTL gates", cls="measured-RTL",
         claim="V4.1 combined QE-weight and pooled index-key HBM, ten dependent steps (cycles)",
         binding=B("results/rtl/hdc_v41x_whbm_pooled_multi.json", "summary.total_cycles"),
         printed=[at("DeepSeek-V4.1 combined QE weight and pooled index-key HBM, ten dependent steps", "4,326,779 cycles")]),
    dict(id="rtl.v41_array_b2", section="RTL gates", cls="measured-RTL",
         claim="V4.1 two-package point-to-point array, three tokens (cycles to the last)",
         binding=B("results/rtl/hdc_v41x_array_b2_6afcfba3_campaign.json", "configurations[0].runs[0].total_cycles"),
         printed=[at("DeepSeek-V4.1 two-package point-to-point array", "967,618 cycles")]),
    dict(id="rtl.v41_array_allunit", section="RTL gates", cls="measured-RTL",
         claim="V4.1 two-package all-unit array, three tokens (cycles to the last)",
         binding=B("results/rtl/hdc_v41x_array_allunit_b2_o1fast_full.json", "observed.array_summary.total_cycles"),
         printed=[at("DeepSeek-V4.1 two-package array, all units (X_HE", "1,283,915 cycles")]),
    # ---------------------------------------------------------------- physical
    dict(id="phys.matvec_tile_setup", section="Physical closure", cls="measured-physical",
         claim="Reduced W4/G2 matvec/ROM/SRAM tile at 1.5 ns: setup slack (ps)",
         binding=B(MT, "place_and_route.metrics.raw_timing_library_units.setup_wns_ns"),
         printed=[at("Qwen3 reduced W4/G2 matvec tile, registered ingress", "setup +83.7999 ps")]),
    dict(id="phys.matvec_tile_hold", section="Physical closure", cls="measured-physical",
         claim="Reduced matvec tile: hold slack (ps)",
         binding=B(MT, "place_and_route.metrics.raw_timing_library_units.hold_wns_ns"),
         printed=[at("Qwen3 reduced W4/G2 matvec tile, registered ingress", "hold +19.7745 ps")]),
    dict(id="phys.matvec_tile_cells", section="Physical closure", cls="measured-physical",
         claim="Reduced matvec tile: standard-cell area (um2)",
         binding=B(MT, "place_and_route.metrics.standard_cell_area_um2"),
         printed=[at("Qwen3 reduced W4/G2 matvec tile, registered ingress", "12,217.6 µm² standard cells")]),
    dict(id="phys.matvec_tile_macros", section="Physical closure", cls="measured-physical",
         claim="Reduced matvec tile: macro area (um2)",
         binding=B(MT, "place_and_route.metrics.macro_area_um2"),
         printed=[at("Qwen3 reduced W4/G2 matvec tile, registered ingress", "63,846.9 µm² macros")]),
    dict(id="phys.dft_coverage", section="Physical closure", cls="measured-physical",
         claim="Lowest stuck-at test coverage over the DFT blocks (%)",
         binding=AGG("min", DFT, "blocks.*.atpg.test_coverage", scale=100),
         printed=[at("Table 7-2. Stuck-at test coverage", "≥99.6%")]),
    dict(id="phys.engram_fmax", section="Physical closure", cls="measured-physical",
         claim="V4.1 Engram gather slice / assembler routed Fmax (MHz)", binding=None,
         unbound="no tracked record field holds 1,656 or 1,179 MHz (the route directories carry slack, "
                 "not a published Fmax field)",
         printed=[at("V4.1 Engram gather slice / assembler", "1,656 / 1,179 MHz")]),
    dict(id="phys.indexer_tree_fmax", section="Physical closure", cls="measured-physical",
         claim="V4.1 indexer output tree routed Fmax (MHz)", binding=None,
         unbound="no tracked record field holds 1,153 MHz",
         printed=[at("V4.1 indexer output tree", "1,153 MHz")]),
    dict(id="phys.select_ctrl_fmax", section="Physical closure", cls="measured-physical",
         claim="V4.1 select control routed Fmax (MHz)", binding=None,
         unbound="no tracked record field holds 1,094 MHz",
         printed=[at("V4.1 select control", "1,094 MHz")]),
    dict(id="phys.host_if_fmax", section="Physical closure", cls="measured-physical",
         claim="Shared host interface routed Fmax (MHz)", binding=None,
         unbound="no tracked record field holds 1,135 MHz for the host interface",
         printed=[at("Shared host interface", "1,135 MHz")]),
    dict(id="phys.lane_copy_fmax", section="Physical closure", cls="measured-physical",
         claim="Qwen3 lane copy, 16 lanes, routed Fmax (GHz)", binding=None,
         unbound="no tracked record field holds the lane copy's ~1.2 GHz",
         printed=[at("Qwen3 lane copy, 16 lanes", "≈1.2 GHz")]),
]

#: A printed value that disagrees with its record, named here so that the check
#: can pass while the disagreement is open -- and ONLY at exactly this printed
#: and recorded value.  Any movement of either fails.  These are for the atlas
#: owner to correct; this tool never edits the atlas.
ACKNOWLEDGED_DISAGREEMENTS: dict[tuple[str, str], str] = {
}


# --------------------------------------------------------------------------
# atlas


#: A written figure that never ends in a separator ("23,578," reads as 23,578).
_FIGURE = r"[-+]?\d(?:[\d,_]*\d)?(?:\.\d+)?(?:[eE][-+]?\d+)?"
_BLOCK = re.compile(r"<(p|tr|li|figcaption|caption|h[1-4])\b[^>]*>(.*?)</\1>", re.S)


def normalise(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    for a, b in (("\u2212", "-"), ("\xa0", " "), ("\u2009", " "), ("\u202f", " ")):
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text).strip()


def atlas_blocks(text: str) -> list[str]:
    return [normalise(body) for _, body in _BLOCK.findall(text)]


def _norm_literal(text: str) -> str:
    return normalise(text)


def find_printed(blocks: list[str], occ: dict[str, Any]) -> tuple[str | None, Quantity | None, str | None]:
    """(block, quantity, error) for one printed occurrence."""
    anchor = _norm_literal(occ["in"])
    hits = [b for b in blocks if anchor in b]
    # A <tr> contains its <caption>-free cells; a caption is its own block.  When
    # an anchor is in several blocks, prefer the shortest (the innermost).
    if not hits:
        return None, None, f"anchor not in the atlas: {occ['in']!r}"
    distinct = sorted(set(hits), key=len)
    if len(distinct) > 1 and not all(distinct[0] in d for d in distinct[1:]):
        return None, None, f"anchor is ambiguous ({len(distinct)} blocks): {occ['in']!r}"
    block = distinct[0]
    literal = _norm_literal(occ["text"])
    # Match the literal with its numbers as wildcards, so an edited figure is
    # read (and reported as a disagreement) instead of reported as lost prose.
    pattern, last = "", 0
    count = 0
    for m in NUMBER.finditer(literal):
        pattern += re.escape(literal[last:m.start()]) + f"(?P<n{count}>{_FIGURE})"
        last, count = m.end(), count + 1
    pattern += re.escape(literal[last:])
    pick = occ.get("pick", 0)
    if pick >= count:
        return block, None, f"printed literal {occ['text']!r} has no number #{pick}"
    matches = list(re.finditer(pattern, block))
    exact = [m for m in matches if m.group(0) == literal]
    if not matches:
        return block, None, f"printed literal {occ['text']!r} not in the block anchored by {occ['in']!r}"
    chosen = exact[0] if exact else matches[0]
    if not exact and len({m.group(0) for m in matches}) > 1:
        return block, None, f"printed literal {occ['text']!r} matches several edited places; update the manifest"
    return block, _to_quantity(chosen.group(f"n{pick}")), None


# --------------------------------------------------------------------------
# records


_RECORD_CACHE: dict[str, Any] = {}


def load_record(path: str) -> Any:
    if path not in _RECORD_CACHE:
        _RECORD_CACHE[path] = json.loads((ROOT / path).read_text())
    return _RECORD_CACHE[path]


def _wildcard(body: Any, selector: str, where: str) -> list[Any]:
    head, _, tail = selector.partition(".*.")
    node = resolve_json(body, head, where)
    if not isinstance(node, dict):
        raise AnnotationError(f"{where}: {head} is not an object; `*` needs one")
    out = []
    for key in sorted(node):
        try:
            value = resolve_json(node[key], tail, where)
        except AnnotationError:
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            out.append(value)
    if not out:
        raise AnnotationError(f"{where}: {selector} matched no numeric field")
    return out


def evaluate(binding: dict[str, Any]) -> tuple[float, list[str]]:
    """(value, records read) for a binding; raises AnnotationError."""
    if "ratio" in binding:
        num, den = binding["ratio"]
        a, ra = evaluate(num)
        b, rb = evaluate(den)
        return a / b, ra + rb
    record = binding["record"]
    if not (ROOT / record).is_file():
        raise AnnotationError(f"record {record} is not in the tree")
    body = load_record(record)
    scale = binding.get("scale", 1.0)
    if "agg" in binding:
        values = _wildcard(body, binding["selector"], record)
        value = min(values) if binding["agg"] == "min" else max(values)
        return value * scale, [record]
    value = resolve_json(body, binding["selector"], record)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AnnotationError(f"{record}#{binding['selector']} is {value!r}, not a number")
    return float(value) * scale, [record]


def binding_label(binding: dict[str, Any]) -> str:
    if "ratio" in binding:
        return f"({binding_label(binding['ratio'][0])}) / ({binding_label(binding['ratio'][1])})"
    text = f"{binding['record']}#{binding['selector']}"
    if "agg" in binding:
        text = f"{binding['agg']}({text})"
    if "scale" in binding:
        text += f" x {binding['scale']:g}"
    return text


# --------------------------------------------------------------------------
# pins


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)


_TRACKED: set[str] | None = None


def tracked(path: str) -> bool:
    global _TRACKED
    if _TRACKED is None:
        _TRACKED = set(git("ls-files", "results", "configs", "docs", "tools").stdout.split())
    return path in _TRACKED


_ANCESTOR: dict[str, bool] = {}


def in_head_history(commit: str) -> bool:
    if commit not in _ANCESTOR:
        exists = git("cat-file", "-e", f"{commit}^{{commit}}").returncode == 0
        _ANCESTOR[commit] = exists and git("merge-base", "--is-ancestor", commit, "HEAD").returncode == 0
    return _ANCESTOR[commit]


def _commit_blob_sha256(commit: str, path: str) -> str | None:
    proc = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True, check=False)
    return hashlib.sha256(proc.stdout).hexdigest() if proc.returncode == 0 else None


def _git_blob(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def record_pins(record: str, body: dict[str, Any]) -> dict[str, Any]:
    """Every source pin the record carries, each classified against the tree."""
    artifact = ROOT / record
    pins: list[dict[str, Any]] = []
    containers = [("", body)]
    if isinstance(body.get("provenance"), dict):
        containers.append(("provenance.", body["provenance"]))
    for prefix, container in containers:
        for field in (*BINDING_FIELDS, *EXTRA_PIN_FIELDS):
            mapping = container.get(field)
            if not isinstance(mapping, dict):
                continue
            for key, value in mapping.items():
                entry: dict[str, Any] = {"field": prefix + field, "key": key}
                if isinstance(value, dict) and isinstance(value.get("from"), str):
                    origin, _, path = value["from"].partition(":")
                    entry.update(path=path, pinned=value.get("sha256"))
                    if origin != "worktree":
                        entry["commit"] = origin
                        if not in_head_history(origin):
                            entry["status"] = "commit-outside-head"
                        elif _commit_blob_sha256(origin, path) != value.get("sha256"):
                            entry["status"] = "at-commit-mismatch"
                        else:
                            current = sha256_file(ROOT / path)
                            entry["status"] = ("current" if current == value.get("sha256")
                                               else "at-commit" if current else "at-commit-deleted")
                        pins.append(entry)
                        continue
                    kind, where, expected = "label_path", ROOT / path, value.get("sha256")
                else:
                    kind, where, expected = classify_binding(
                        field if field in BINDING_FIELDS else "source_sha256", key, value, artifact, body)
                if kind in ("build_output", "ephemeral"):
                    entry.update(path=key, pinned=expected, status=kind)
                elif where is None:
                    entry.update(path=None, pinned=expected, status="unresolvable")
                else:
                    try:
                        shown = str(where.relative_to(ROOT))
                    except ValueError:
                        shown = str(where)
                    entry.update(path=shown, pinned=expected)
                    if expected is None:
                        entry["status"] = "path-only" if where.is_file() else "missing"
                    elif not where.is_file():
                        entry["status"] = "missing"
                    else:
                        entry["status"] = "current" if sha256_file(where) == expected else "stale"
                pins.append(entry)
    golden = body.get("golden_pin")
    if isinstance(golden, dict) and isinstance(golden.get("file"), str) and golden.get("git_blob"):
        now = _git_blob(ROOT / golden["file"])
        pins.append({"field": "golden_pin", "key": golden["file"], "path": golden["file"],
                     "pinned": golden["git_blob"], "hash": "git-blob",
                     "status": "missing" if now is None else "current" if now == golden["git_blob"] else "stale"})
    commits = []
    for prefix, container in containers:
        for field in COMMIT_FIELDS:
            value = container.get(field)
            if isinstance(value, str) and re.fullmatch(r"[0-9a-f]{7,40}", value):
                commits.append({"field": prefix + field, "commit": value, "in_head_history": in_head_history(value)})
    g = body.get("git")
    if isinstance(g, dict) and isinstance(g.get("commit"), str):
        commits.append({"field": "git.commit", "commit": g["commit"], "in_head_history": in_head_history(g["commit"])})
    counts: dict[str, int] = {}
    for p in pins:
        counts[p["status"]] = counts.get(p["status"], 0) + 1
    return {"pins": pins, "pin_counts": dict(sorted(counts.items())), "commits": commits}


#: Records that name no producer.  The producer is the tool whose default
#: output path is the record (found by grepping tools/ for the record name);
#: it is reported as INFERRED, because the record itself does not say so.
INFERRED_PRODUCERS = {
    "results/rtl/hdc_v41_decode_campaign.json": "tools/rtl_hdc_v41_decode_campaign.py",
    "results/rtl/hdc_v41x_egather_campaign.json": "tools/rtl_hdc_v41x_egather_campaign.py",
    "results/rtl/hdc_v41x_sel_campaign.json": "tools/rtl_hdc_v41x_sel_campaign.py",
    "results/rtl/hdc_v41x_hcp_campaign.json": "tools/rtl_hdc_v41x_hcp_campaign.py",
    "results/rtl/hdc_qwen_vector_system_multi_g4sw16.json": "tools/rtl_hdc_qwen_vector_system_multi.py",
    "results/rtl/hdc_qwen_vector_system_timed_g4sw16.json": "tools/rtl_hdc_qwen_vector_system_timed.py",
    "results/rtl/hdc_qwen_vector_matched_weight_full_g4sw16.json": "tools/rtl_hdc_qwen_vector_matched_weight_full.py",
    "results/rtl/hdc_qwen_context_2048.json": "tools/rtl_hdc_qwen_context_2048.py",
    "results/rtl/hdc_qwen_context_1024.json": "tools/rtl_hdc_qwen_context_ladder.py",
    "results/rtl/hdc_qwen_context_512.json": "tools/rtl_hdc_qwen_context_ladder.py",
    "results/rtl/hdc_qwen_long_context_256_control.json": "tools/rtl_hdc_qwen_long_context_stress.py",
    "results/rtl/hdc_qwen_matched_weight_single.json": "tools/rtl_hdc_qwen_matched_weight.py",
    "results/dft/summary.json": "tools/dft/summarize.py",
}


def record_command(record: str, body: dict[str, Any]) -> tuple[str | None, str | None]:
    tool = body.get("tool") if isinstance(body.get("tool"), str) else None
    for key in ("campaign_command", "command"):
        if isinstance(body.get(key), str):
            return tool, body[key]
    prov = body.get("provenance") if isinstance(body.get("provenance"), dict) else {}
    if isinstance(prov.get("campaign_command"), str):
        return tool, prov["campaign_command"]
    runner = body.get("runner")
    if isinstance(runner, dict) and isinstance(runner.get("argv"), list) and runner["argv"]:
        argv = [str(a) for a in runner["argv"]]
        return argv[0], "python3 " + " ".join(argv)
    if tool:
        script = tool.split()[0]
        return tool, (f"python3 {tool}" if script.endswith(".py") else None)
    if record in INFERRED_PRODUCERS:
        return INFERRED_PRODUCERS[record], f"python3 {INFERRED_PRODUCERS[record]}  (inferred; the record names no command)"
    return None, None


# --------------------------------------------------------------------------
# build


def fmt(value: float) -> str:
    if value == 0:
        return "0"
    mag = abs(value)
    digits = 6 if mag < 10 else 6
    return f"{value:.{digits}g}"


def build() -> dict[str, Any]:
    atlas_text = (ROOT / ATLAS).read_text()
    blocks = atlas_blocks(atlas_text)
    records: dict[str, dict[str, Any]] = {}
    findings: list[dict[str, Any]] = []
    out_headlines = []

    def note_record(path: str) -> None:
        if path in records:
            return
        entry: dict[str, Any] = {"exists": (ROOT / path).is_file(), "tracked": tracked(path)}
        if entry["exists"]:
            entry["sha256"] = sha256_file(ROOT / path)
            body = load_record(path)
            if isinstance(body, dict):
                tool, command = record_command(path, body)
                entry.update(schema=body.get("schema") or body.get("schema_version"), tool=tool, command=command)
                entry.update(record_pins(path, body))
        records[path] = entry

    ids = set()
    for h in HEADLINES:
        assert h["id"] not in ids, f"duplicate headline id {h['id']}"
        ids.add(h["id"])
        row: dict[str, Any] = {"id": h["id"], "section": h["section"], "claim": h["claim"],
                               "evidence_class": h["cls"]}
        binding = h.get("binding")
        value = None
        if binding is None:
            row["binding"] = None
            row["unbound_reason"] = h["unbound"]
            findings.append({"key": f"unbound:{h['id']}", "kind": "unbound", "headline": h["id"],
                             "detail": h["unbound"]})
        else:
            row["binding"] = binding_label(binding)
            row["derived"] = "ratio" in binding or "agg" in binding
            try:
                value, used = evaluate(binding)
                if h.get("derived_as") == "(ratio - 1) x 100":
                    value = (value - 1) * 100
                row["derivation"] = h.get("derived_as")
                row["record_value"] = float(fmt(value))
                row["records"] = sorted(set(used))
                for r in used:
                    note_record(r)
                    if not records[r]["tracked"]:
                        findings.append({"key": f"untracked:{r}", "kind": "record-untracked", "headline": h["id"],
                                         "detail": f"{r} is not tracked by git"})
            except (AnnotationError, OSError, ValueError, KeyError, ZeroDivisionError) as error:
                findings.append({"key": f"unresolvable:{h['id']}", "kind": "binding-unresolvable",
                                 "headline": h["id"], "detail": str(error)})
        printed_rows = []
        for occ in h["printed"]:
            block, qty, error = find_printed(blocks, occ)
            prow: dict[str, Any] = {"in": occ["in"], "text": occ["text"]}
            if error:
                prow["status"] = "not-found"
                findings.append({"key": f"atlas:{h['id']}:{occ['text']}", "kind": "atlas-drift",
                                 "headline": h["id"], "detail": error})
            else:
                prow["printed_value"] = qty.literal
                if value is None:
                    prow["status"] = "unbound"
                else:
                    ok, allowed = agree(qty, _to_quantity(repr(value)), occ.get("tol", h.get("tol")))
                    if ok:
                        prow["status"] = "agrees"
                    elif ACKNOWLEDGED_DISAGREEMENTS.get((h["id"], occ["text"])) == fmt(value):
                        prow["status"] = "disagrees-acknowledged"
                        findings.append({"key": f"ack:{h['id']}:{occ['text']}", "kind": "acknowledged-disagreement",
                                         "headline": h["id"],
                                         "detail": f"atlas prints {qty.literal} (anchor {occ['in']!r}); record {fmt(value)}"})
                    else:
                        prow["status"] = "disagrees"
                        findings.append({"key": f"value:{h['id']}:{occ['text']}", "kind": "value-mismatch",
                                         "headline": h["id"],
                                         "detail": f"atlas prints {qty.literal} in {occ['text']!r} (anchor {occ['in']!r}); "
                                                   f"record {row.get('binding')} = {fmt(value)} "
                                                   f"(allowed difference {allowed:g})"})
            printed_rows.append(prow)
        row["printed"] = printed_rows
        sens = h.get("sensitivity") or []
        if sens and value is not None:
            svals = []
            for s in sens:
                try:
                    sv, used = evaluate(s["binding"])
                    for r in used:
                        note_record(r)
                    svals.append({"label": s["label"], "binding": binding_label(s["binding"]), "value": float(fmt(sv))})
                except (AnnotationError, OSError, ValueError, KeyError, ZeroDivisionError) as error:
                    findings.append({"key": f"sensitivity:{h['id']}:{s['label']}", "kind": "binding-unresolvable",
                                     "headline": h["id"], "detail": f"sensitivity {s['label']!r}: {error}"})
            if svals:
                allv = [value] + [s["value"] for s in svals]
                row["sensitivity"] = {"variants": svals, "range": [float(fmt(min(allv))), float(fmt(max(allv)))]}
        out_headlines.append(row)

    for path, entry in sorted(records.items()):
        for pin in entry.get("pins", []):
            status = pin["status"]
            if status in ("stale", "missing", "commit-outside-head", "at-commit-mismatch"):
                kind = {"stale": "stale-pin", "missing": "missing-pin"}.get(status, status)
                findings.append({"key": f"{kind}:{path}:{pin['path'] or pin['key']}", "kind": kind, "record": path,
                                 "detail": f"{pin['field']}[{pin['key']}] -> {pin['path']} is {status}"})
        for c in entry.get("commits", []):
            if not c["in_head_history"]:
                findings.append({"key": f"commit-outside-head:{path}:{c['commit']}", "kind": "commit-outside-head",
                                 "record": path, "detail": f"{c['field']} {c['commit']} is not in HEAD's history"})

    findings.sort(key=lambda f: f["key"])
    bound = [h for h in out_headlines if h["binding"] is not None]
    pin_totals: dict[str, int] = {}
    for entry in records.values():
        for k, v in entry.get("pin_counts", {}).items():
            pin_totals[k] = pin_totals.get(k, 0) + v
    kinds: dict[str, int] = {}
    for f in findings:
        kinds[f["kind"]] = kinds.get(f["kind"], 0) + 1
    return {
        "schema": SCHEMA,
        "generated_by": "tools/headline_bundle.py",
        "command": "python3 tools/headline_bundle.py",
        "check_command": "python3 tools/headline_bundle.py --check",
        "atlas": str(ATLAS),
        "answers": "docs/ARCHITECTURE_ATLAS_FEASIBILITY_REVIEW_2026_09_27.md finding 6, recommendation 6",
        "evidence_classes": EVIDENCE_CLASSES,
        "summary": {
            "headlines": len(out_headlines),
            "bound": len(bound),
            "derived_in_bundle": sum(1 for h in bound if h.get("derived")),
            "unbound": len(out_headlines) - len(bound),
            "printed_occurrences": sum(len(h["printed"]) for h in out_headlines),
            "occurrences_agreeing": sum(1 for h in out_headlines for p in h["printed"] if p["status"] == "agrees"),
            "with_sensitivity_range": sum(1 for h in out_headlines if "sensitivity" in h),
            "by_evidence_class": {c: sum(1 for h in out_headlines if h["evidence_class"] == c)
                                  for c in EVIDENCE_CLASSES},
            "records": len(records),
            "records_with_source_pins": sum(1 for e in records.values() if e.get("pins")),
            "pins_by_status": dict(sorted(pin_totals.items())),
            "findings_by_kind": dict(sorted(kinds.items())),
        },
        "headlines": out_headlines,
        "records": records,
        "findings": findings,
    }


# --------------------------------------------------------------------------
# markdown


def _cell(text: Any) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def _annotation(h: dict[str, Any], spec: dict[str, Any]) -> str:
    """A figure: annotation for the prose checker, for a single-field binding."""
    b = spec.get("binding")
    if not b or "ratio" in b or "agg" in b or spec.get("derived_as"):
        return ""
    printed = next((p for p in h["printed"] if p.get("status") == "agrees"), None)
    if printed is None:
        return ""
    # The annotation's own attributes are double-quoted, so a bracketed key is
    # written with single quotes, which the selector grammar also accepts.
    selector = re.sub(r'\["([^"]*)"\]', r"['\1']", b["selector"])
    attrs = f'src="{b["record"]}#{selector}"'
    if "scale" in b:
        attrs += f' scale="{b["scale"]:g}"'
    return f' <!-- figure: {printed["printed_value"]} {attrs} name="{h["id"]}" -->'


def render_markdown(bundle: dict[str, Any]) -> str:
    specs = {h["id"]: h for h in HEADLINES}
    s = bundle["summary"]
    lines = [
        "# Headline bundle: sources, configuration and results behind the atlas figures",
        "",
        "Generated by `python3 tools/headline_bundle.py` from `results/arch/headline_bundle.json`; "
        "do not edit by hand. `python3 tools/headline_bundle.py --check` (part of `make check-figures`) "
        "fails when a printed atlas figure leaves its record, a bound record disappears, or a new stale "
        "source pin, outside-history snapshot or unbound headline appears.",
        "",
        "This appendix answers finding 6 and recommendation 6 of "
        "`docs/ARCHITECTURE_ATLAS_FEASIBILITY_REVIEW_2026_09_27.md`: one reproducible "
        "source/configuration/result bundle for every headline comparison in "
        "`docs/ARCHITECTURE_ATLAS.html`, with explicit evidence classes and sensitivity ranges. "
        "It restates no argument. For each headline it names the record that produces the number, the "
        "tool that wrote that record, and the sources the record pins, and it says which headlines no "
        "record produces.",
        "",
        "## B.1 Coverage",
        "",
        f"- Headlines enumerated: {s['headlines']} ({s['printed_occurrences']} printed occurrences in the atlas).",
        f"- Bound to a record: {s['bound']}, of which {s['derived_in_bundle']} are a ratio or an aggregate of "
        "record fields computed here. Unbound: "
        f"{s['unbound']} (Section B.5).",
        f"- Printed occurrences that agree with their record under the written-precision rule: "
        f"{s['occurrences_agreeing']}.",
        f"- Headlines with a sensitivity range taken from the record's own variants: {s['with_sensitivity_range']}.",
        f"- Records: {s['records']}, of which {s['records_with_source_pins']} pin their sources.",
        "",
        "Written-precision rule (from `tools/check_prose_figures.py`): a printed figure agrees with its "
        "record when they differ by at most half of the last digit printed, so `2.3` agrees with 2.286 "
        "and `8,185` with 8,184.9.",
        "",
        "## B.2 Evidence classes",
        "",
        "| Class | Headlines | Meaning |",
        "|---|---|---|",
    ]
    for c, meaning in bundle["evidence_classes"].items():
        lines.append(f"| {c} | {s['by_evidence_class'][c]} | {_cell(meaning)} |")
    lines += ["", "No headline in the atlas is a measurement of fabricated silicon. Every rate of a full-size "
              "chip is `model`; the RTL and physical classes are reduced vehicles, blocks and tiles.", ""]

    lines += ["## B.3 Headlines", "",
              "Printed: the atlas literal and how many places print it. Record value: what the bound field "
              "holds now. Range: the lowest and highest of the headline and the record's own variants "
              "(listed under each section), unit as in the claim.", ""]
    sections: dict[str, list[dict[str, Any]]] = {}
    for h in bundle["headlines"]:
        sections.setdefault(h["section"], []).append(h)
    for name, rows in sections.items():
        lines += [f"### {name}", "", "| Id | Claim | Printed | Places | Record value | Class | Bound to | Range |",
                  "|---|---|---|---|---|---|---|---|"]
        notes = []
        for h in rows:
            first = h["printed"][0]
            printed = first.get("printed_value", "?")
            statuses = {p["status"] for p in h["printed"]}
            places = f"{len(h['printed'])}" + ("" if statuses <= {"agrees", "unbound"} else " (disagreement)")
            value = "unbound" if h["binding"] is None else fmt(h.get("record_value", float("nan")))
            bound = "—" if h["binding"] is None else f"`{_cell(h['binding'])}`"
            rng = ""
            if "sensitivity" in h:
                lo, hi = h["sensitivity"]["range"]
                rng = f"{fmt(lo)} – {fmt(hi)}"
                notes.append(f"- `{h['id']}`: " + "; ".join(
                    f"{v['label']}: {fmt(v['value'])}" for v in h["sensitivity"]["variants"]))
            ann = _annotation(h, specs[h["id"]])
            lines.append(f"| `{h['id']}` | {_cell(h['claim'])} | {_cell(printed)} | {places} | {value} | "
                         f"{h['evidence_class']} | {bound} | {rng} |{ann}")
        if notes:
            lines += ["", "Sensitivity variants:", ""] + notes
        lines.append("")

    lines += ["## B.4 Records, tools and source pins", "",
              "Each record is reproduced by its command, from the sources it pins. `current` pins hash "
              "to the tree; `stale` pins do not (the record was produced from an earlier version of that "
              "source and has not been re-taken); `path-only` sources are named without a digest; "
              "`at-commit` pins bind a source at a named commit. A record with no pins binds nothing: "
              "its reproducibility rests on the tool and the tree it was run from.", "",
              "| Record | Tracked | Command | Pins | Snapshot commits |", "|---|---|---|---|---|"]
    for path, e in bundle["records"].items():
        pins = ", ".join(f"{k} {v}" for k, v in e.get("pin_counts", {}).items()) or "none"
        commits = ", ".join(f"{c['commit'][:8]}{'' if c['in_head_history'] else ' (outside HEAD)'}"
                            for c in e.get("commits", [])) or "—"
        cmd = e.get("command") or (e.get("tool") or "not recorded")
        lines.append(f"| `{path}` | {'yes' if e.get('tracked') else 'NO'} | `{_cell(cmd)}` | {pins} | {commits} |")
    lines.append("")

    lines += ["## B.5 Unbound headlines", "",
              "These figures are printed in the atlas and produced by no tracked record. They are typed by "
              "hand, or produced by a record that is not on main. They cannot be reproduced from this "
              "repository as it stands.", "",
              "| Id | Printed | Where | Why unbound |", "|---|---|---|---|"]
    for h in bundle["headlines"]:
        if h["binding"] is None:
            where = "; ".join(_cell(p["in"][:48]) for p in h["printed"])
            printed = " / ".join(p.get("printed_value", "?") for p in h["printed"])
            lines.append(f"| `{h['id']}` | {printed} | {where} | {_cell(h['unbound_reason'])} |")
    lines.append("")

    groups: dict[str, list[dict[str, Any]]] = {}
    for f in bundle["findings"]:
        if f["kind"] == "unbound":
            continue
        groups.setdefault(f["kind"], []).append(f)
    lines += ["## B.6 Findings", "",
              "Everything below is known to the check. A new entry of any kind fails it; a value "
              "disagreement always fails unless named in `ACKNOWLEDGED_DISAGREEMENTS`.", ""]
    if not groups:
        lines += ["None.", ""]
    for kind, items in sorted(groups.items()):
        lines += [f"### {kind} ({len(items)})", ""]
        by_record: dict[str, list[str]] = {}
        for f in items:
            owner = f.get("record") or f.get("headline")
            by_record.setdefault(owner, []).append(f["detail"])
        for owner, details in by_record.items():
            if kind in ("stale-pin", "missing-pin") and len(details) > 3:
                lines.append(f"- `{owner}`: {len(details)} pins, e.g. " + "; ".join(_cell(d) for d in details[:3]))
            else:
                for d in details:
                    lines.append(f"- `{owner}`: {_cell(d)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------
# main


def serialise(bundle: dict[str, Any]) -> str:
    return json.dumps(bundle, indent=1, sort_keys=False, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="rebuild, compare with the committed bundle, and fail on new findings")
    ap.add_argument("--blocks", metavar="PHRASE", help="debug: print every atlas block containing PHRASE")
    args = ap.parse_args(argv)

    if args.blocks:
        for block in atlas_blocks((ROOT / ATLAS).read_text()):
            if _norm_literal(args.blocks) in block:
                print(block, "\n")
        return 0

    bundle = build()
    committed_path = ROOT / OUT_JSON
    committed = json.loads(committed_path.read_text()) if committed_path.is_file() else None
    known = set(committed.get("known_findings", [])) if committed else set()
    ratchet_now = sorted(f["key"] for f in bundle["findings"] if f["kind"] in RATCHET_KINDS)
    bundle["known_findings"] = ratchet_now
    text = serialise(bundle)
    md = render_markdown(bundle)
    s = bundle["summary"]
    print(f"headlines {s['headlines']}: bound {s['bound']} (derived {s['derived_in_bundle']}), unbound {s['unbound']}; "
          f"occurrences {s['printed_occurrences']}, agreeing {s['occurrences_agreeing']}; "
          f"records {s['records']}; pins {s['pins_by_status']}")

    hard = [f for f in bundle["findings"]
            if f["kind"] in ("value-mismatch", "atlas-drift", "binding-unresolvable", "record-untracked")]
    if not args.check:
        (ROOT / OUT_JSON).write_text(text)
        (ROOT / OUT_MD).write_text(md)
        print(f"wrote {OUT_JSON} and {OUT_MD}")
        for f in hard:
            print(f"  FAIL {f['kind']}: {f['headline']}: {f['detail']}")
        return 2 if hard else 0

    problems = [f"{f['kind']}: {f.get('headline') or f.get('record')}: {f['detail']}" for f in hard]
    if committed is None:
        problems.append(f"{OUT_JSON} is missing: run python3 tools/headline_bundle.py")
    else:
        new = [f for f in bundle["findings"] if f["kind"] in RATCHET_KINDS and f["key"] not in known]
        problems += [f"NEW {f['kind']}: {f.get('headline') or f.get('record')}: {f['detail']}" for f in new]
        if not problems and (committed_path.read_text() != text or not (ROOT / OUT_MD).is_file()
                             or (ROOT / OUT_MD).read_text() != md):
            problems.append(f"{OUT_JSON} / {OUT_MD} are out of date (a record, pin or the manifest moved): "
                            "run python3 tools/headline_bundle.py and commit both")
        gone = sorted(known - set(ratchet_now))
        if gone and not problems:
            print(f"  {len(gone)} known finding(s) cleared; regenerate to tighten the ratchet")
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems:
            print(f"  {p}")
        return 2
    print("every bound headline matches its record; no new stale pin, outside-history snapshot or unbound headline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
