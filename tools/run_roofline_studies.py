#!/usr/bin/env python3
"""Run the area-constrained roofline studies and render their report.

Every number emitted here comes from ``opentallas.roofline`` evaluating
``configs/hardware/technology.json`` against the released model profiles.  No
figure in the generated report is hand-computed, and the two validation gates
run inside the study so a methodology drift shows up in the artifact rather than
only in the test suite.

Two studies are produced, each iso-node and each iso-area:

* ``n6_vs_a100``  -- reticle-class ROM silicon at TSMC N6 against NVIDIA A100
  80GB at N7.  This is the pairing the Taalas HC1 anchor validates: 815 mm2 at
  N6 against 826 mm2 at N7, essentially the same die one node apart.
* ``n5_vs_b200``  -- ROM silicon at N5 against NVIDIA B200 at 4NP, counted per
  two-die package so the areas match.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, replace
import hashlib
import io
import json
from collections.abc import Mapping, Sequence
import math
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from opentallas.roofline import (  # noqa: E402
    CimCellAccounting,
    BITS_PER_BYTE,
    DeviceBudget,
    RooflineStep,
    Technology,
    Topology,
    a100_power_anchor,
    a100_weight_bound_anchor,
    evaluate,
    gpu_device_budget,
    latency_crossover,
    layer_fixed_latency,
    max_hbm_stacks_per_device,
    rom_device_budget,
    taalas_hc1_anchor,
    taalas_hc1_power_anchor,
)
from opentallas.schema import ModelProfile, ValidationError  # noqa: E402
from opentallas.workload import (  # noqa: E402
    hbm_resident_weight_bytes,
    kv_traffic,
)


TECHNOLOGY_PATH = ROOT / "configs" / "hardware" / "technology.json"

#: The routed ASAP7 blocks this repository holds, read for the fabric-clock
#: sensitivity below.  They are named here rather than transcribed: the
#: sensitivity reads ``place_and_route.metrics.fmax_hz`` out of each artifact,
#: so a re-run of the physical flow moves the sensitivity and no number in this
#: file has to be edited by hand.  **These are predictive-PDK figures and
#: `docs/METHODOLOGY.md` section 9 forbids scaling them to N6/N5/N7/N4** -- they
#: appear here as a sensitivity a reader can see the size of, never as a value.
ASAP7_ROUTED_BLOCKS = (
    ("asap7_reduction_s8_g2", "results/physical_abi3/asap7/reduction_s8_g2/pnr.json"),
    (
        "asap7_add_bf16_sram_engine",
        "results/physical_abi3/asap7/add_bf16_sram_engine/pnr.json",
    ),
    (
        "asap7_matmul_bf16_sram_engine",
        "results/physical_abi3/asap7/matmul_bf16_sram_engine/pnr.json",
    ),
)

#: The two ROM-to-SRAM bit-cell area ratios this repository has MEASURED, at two
#: nodes that disagree by 92.7%.  ``rom.cell_to_sram_cell_area_ratio``'s stated
#: band must contain both: a sweep that excludes a measurement the same
#: repository made is a sweep that has already been refuted, and the previous
#: prose-only "1/6 to 1/4" bracket excluded the 130 nm one.  Checked by the
#: consistency audit, which is the thing that should have refused it.
MEASURED_ROM_CELL_RATIOS = (
    (
        "ihp_sg13g2_130nm",
        "results/spice/ihp_sg13g2_bitcell/bitcell.json",
        ("ratio", "measured"),
    ),
    (
        "asap7_7nm_via_programmed",
        "results/asap7_physical/bitcell_density/bitcell_density.json",
        ("measurement", "ratio_via_programmed_rom_to_sram"),
    ),
    (
        "asap7_7nm_shared_source_drain",
        "results/asap7_physical/bitcell_density/bitcell_density.json",
        ("measurement", "ratio_shared_sd_rom_to_sram"),
    ),
)
OUTPUT_ROOT = ROOT / "results" / "roofline"
ARTIFACTS = ("analytical.json", "points.json", "sweep.csv", "REPORT.md")
VARIANT_ARTIFACTS = ("analytical.json", "points.json", "REPORT.md")
"""No ``sweep.csv`` for the variant, and that is a decision rather than an
omission: there is no row on that page anyone should be pulling into a
spreadsheet."""


def variant_output_root(output_root: Path) -> Path:
    """Where the secondary quantised variant is written.

    A separate directory, one level down, so a path never resolves to a variant
    when a reader meant the primary study.
    """

    return output_root / "quantised_variant"

ANCHOR_MODEL_PATH = (
    ROOT / "configs" / "models" / "anchors" / "llama-3.1-8b.json"
)
"""The anchor model lives under ``anchors/`` rather than beside the study
models because ``configs/models/*.json`` is globbed by the legacy standard run
and by the NoC sweep, which evaluate every profile they find at contexts this
model cannot serve. It is a validation fixture, not a study target."""

# Model, its study context, and why that context.
STUDY_MODELS: tuple[tuple[str, Path, int], ...] = (
    (
        "Qwen3-8B",
        ROOT / "configs" / "models" / "qwen3-8b.json",
        8_192,
    ),
    (
        "DeepSeek-V4-Flash-0731",
        ROOT / "configs" / "models" / "deepseek-v4-flash-0731.json",
        200_000,
    ),
    (
        "DeepSeek-V4-Pro-0813",
        ROOT / "configs" / "models" / "deepseek-v4-pro-0813.json",
        1_000_000,
    ),
)
CONTEXT_LADDER: dict[str, tuple[int, ...]] = {
    "DeepSeek-V4-Flash-0731": (8_192, 32_768, 1_000_000),
    "DeepSeek-V4-Pro-0813": (8_192, 32_768, 200_000),
}
"""The other contexts each DeepSeek model is run at, in its own artifact tree.

The primary studies run each model at one context, and every figure a release
document binds is read from those two artifacts, so adding contexts to them
would move the byte-identity of every bound figure.  The ladder rungs are
therefore separate single-model studies, selected by the same rule on the same
code path, written under ``results/roofline/context_ladder/<study>/<rung>/``.
``ASSUMPTIONS.md`` states the authoritative contexts as 8,192 / 32,768 /
200,000 / 1,000,000; the primary context of each model is excluded here
because it is the primary artifact."""


def context_ladder_output_root(output_root: Path) -> Path:
    return output_root / "context_ladder"


CANDIDATE_MODELS: tuple[tuple[str, str, Path, int], ...] = (
    (
        "deepseek-v41-flash",
        "DeepSeek-V4.1-Flash",
        ROOT / "configs" / "models" / "candidates" / "deepseek-v4.1-flash.json",
        200_000,
    ),
    (
        "deepseek-v41-flash-engram-host",
        "DeepSeek-V4.1-Flash-engram-host",
        ROOT
        / "configs"
        / "models"
        / "candidates"
        / "deepseek-v4.1-flash-engram_host.json",
        200_000,
    ),
    (
        "deepseek-v41-flash-engram-hbm",
        "DeepSeek-V4.1-Flash-engram-hbm",
        ROOT
        / "configs"
        / "models"
        / "candidates"
        / "deepseek-v4.1-flash-engram_hbm.json",
        200_000,
    ),
    # Kimi-K3 (69 KDA linear-attention layers + 24 MLA) and Xiaomi
    # MiMo-V2.6 Pro/Flash (hybrid 128-token SWA + global GQA), 2026-09-24.
    # Each is run at the DeepSeek primary context and at the two ends of the
    # context ladder, 8,192 and 1,000,000, because the three attention designs
    # scale with context in three different ways: a fixed recurrent state, a
    # 576-byte latent per token, and a 2.5-5 KB GQA entry per token.
    *(
        (
            f"{family}{suffix}",
            model_name,
            ROOT / "configs" / "models" / "candidates" / profile,
            context,
        )
        for family, model_name, profile in (
            ("kimi-k3", "Kimi-K3", "kimi-k3-attention_ops.json"),
            ("mimo-v26-pro", "MiMo-V2.6-Pro", "mimo-v2.6-pro.json"),
            ("mimo-v26-flash", "MiMo-V2.6-Flash", "mimo-v2.6-flash.json"),
        )
        for suffix, context in (("", 200_000), ("-8k", 8_192), ("-1m", 1_000_000))
    ),
    # DeepSeek-V4.1-Flash at the ends of the context ladder (2026-09-24), for
    # the base profile and for the Engram-in-KV-store placement the ROM target
    # takes; its 200K primary rows above are unchanged.
    *(
        (
            f"{slug}{suffix}",
            model_name,
            ROOT / "configs" / "models" / "candidates" / profile,
            context,
        )
        for slug, model_name, profile in (
            ("deepseek-v41-flash", "DeepSeek-V4.1-Flash", "deepseek-v4.1-flash.json"),
            ("deepseek-v41-flash-engram-hbm", "DeepSeek-V4.1-Flash-engram-hbm",
             "deepseek-v4.1-flash-engram_hbm.json"),
        )
        for suffix, context in (("-8k", 8_192), ("-1m", 1_000_000))
    ),
    # Qwen3-8B beyond its 8,192-token primary study (2026-09-24).  These rungs
    # are HYPOTHETICAL: the released model's native context is 40,960 tokens
    # (131,072 with YaRN), so 200K and 1M price the machines as if the model
    # served them -- same weights, a KV cache grown to that context.
    *(
        (f"qwen3-8b{suffix}", "Qwen3-8B",
         ROOT / "configs" / "models" / "candidates" / "qwen3-8b-context-extended.json", context)
        for suffix, context in (("-200k", 200_000), ("-1m", 1_000_000))
    ),
)
"""Candidate models, each run as a single-model study in its own tree.

A candidate is a model profiled from its official checkpoint that no lane in
this repository has executed and no release document binds a figure to.  It is
kept out of ``STUDY_MODELS`` for the same reason the context ladder is: adding
a model to the primary studies moves the byte-identity of every figure bound to
them.  Each candidate is written under
``results/roofline/candidates/<slug>/<study>/`` by the same rule on the same
code path as the primary, at the DeepSeek-V4-Flash primary context.

DeepSeek-V4.1-Flash (2026-09-10) is carried three times, once per placement of
its 203 GB of Engram n-gram tables: stored beside the weights on both sides, in
host memory on both sides as DeepSeek's own serving stack places them, and
resident in the store that holds the KV cache -- wafer-edge HBM on the ROM side
and the same HBM on the GPU side.  The third is the placement the V4.1 primary
target takes (plan section 3.4) and it is the only one the machine actually
pays for: the tables leave the weight store, so the ROM is sized without them,
and in exchange the KV store loses their capacity on the stage that owns them
and their 24 rows per module per token cost that store's bandwidth."""


def candidates_output_root(output_root: Path) -> Path:
    return output_root / "candidates"


def context_rung_label(model_name: str, context: int) -> str:
    """``flash-8k``, ``pro-200k``, ``flash-1m``: a path segment, not a title."""

    short = model_name.split("-")
    family = next(
        (part.lower() for part in short if part.lower() in ("flash", "pro")),
        short[0].lower(),
    )
    if context >= 1_000_000 and context % 1_000_000 == 0:
        span = f"{context // 1_000_000}m"
    elif context % 1024 == 0:
        span = f"{context // 1024}k"
    else:
        span = f"{context // 1000}k"
    return f"{family}-{span}"


BATCHES = (1, 2, 4, 8, 16, 32, 64, 256, 1024, 4096)
"""Doubling from 1 to 64, then 256, 1024 and 4096.

The ladder used to stop at 256, where a GPU's aggregate throughput is still
rising: the framework review (docs/ANALYTICAL_REPORT.md,
finding 6) found aggregate ratios being read before the amortising machine
saturated.  1024 and 4096 let each side reach its own peak or its KV capacity.

The coarse grid this replaced -- 1, 8, 32, 64, 256 -- could report the endpoints
of the batching argument but not the shape between them, and the shape is where
the argument actually lives.  A dense model's KV read is per-user and never
amortises, so a ROM design that wins by an order of magnitude at batch 1 gives
that lead back as batch rises; a sparse model's routed weights engage more of the
array with every added stream, so it gains.  Both effects are monotone and
neither is visible at two points.  Powers of two locate the crossing to within a
factor of two without the sweep growing enough to matter."""
DESIGN_BATCH = 1
"""SRAM area is silicon area, so an SRAM-KV design is sized at batch 1 -- the
minimum machine -- and the study then reports the batch at which its KV capacity
runs out.  HBM capacity is bought in stacks rather than in die area, so an
HBM-KV design is instead provisioned for the largest study batch, subject to the
die-edge beachfront check."""
PROVISION_BATCH = max(BATCHES)

#: **Every link a study charges is named per study, on BOTH sides.**  The GPU
#: side always was -- ``nvlink3`` for the A100 generation, ``nvlink5`` for
#: Blackwell -- and until 2026-08-31 the ROM side was not: one ``on_wafer``
#: constant derived from Cerebras WSE-2, a TSMC **7nm** part, served both.  That
#: made ``n6_vs_a100`` correctly matched (a 7nm-era wafer fabric against a
#: 7nm-era GPU) and ``n5_vs_b200`` mismatched: a 7nm-era wafer fabric against a
#: 4nm-era NVLink, which understates the ROM side in the study where it should
#: be strongest.  ``rom_intra_link`` closes that.  The N5 entry lands on the
#: same 125 ns as the N7 one -- see ``links.on_wafer_n5``'s note for the WSE-3
#: derivation and why it is a null result -- but the two are now separately
#: stated and separately swept, so either can move without dragging the other.
#:
#: ``rom_inter_link`` is ``inter_wafer`` in both, and that is not the same
#: defect: its GPU counterpart is the scale-out fabric, where ``infiniband_hdr``
#: and ``infiniband_ndr`` are also two entries carrying the SAME measured 4.5 us
#: hop, because small-message RDMA latency is set by the NIC and the protocol
#: stack rather than by the logic node.  Both sides' scale-out latency is one
#: number across the two studies, so the asymmetry the wafer fabric had does not
#: arise here.
STUDIES: dict[str, dict[str, Any]] = {
    "n6_vs_a100": {
        "rom_node": "N6",
        "gpu_parts": ("a100_sxm_80gb",),
        "hbm_generation": "hbm2e",
        "intra_link": "nvlink3",
        "inter_link": "infiniband_hdr",
        "rom_intra_link": "on_wafer",
        "rom_inter_link": "rom_wafer_serdes",
        "rom_array_intra_link": "rom_package_ucie",
        "rom_array_inter_link": "rom_board_serdes",
        "contract": (
            "Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at "
            "N7, compared at equal silicon area with the area stated on both sides. "
            "This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 "
            "against 826 mm2 at N7, essentially the same die one node apart."
        ),
    },
    "n5_vs_b200": {
        "rom_node": "N5",
        "gpu_parts": ("b200_sxm",),
        "hbm_generation": "hbm3e",
        "intra_link": "nvlink5",
        "inter_link": "infiniband_ndr",
        "rom_intra_link": "on_wafer_n5",
        "rom_inter_link": "rom_wafer_serdes",
        "rom_array_intra_link": "rom_package_ucie",
        "rom_array_inter_link": "rom_board_serdes",
        "gpu_domain_sensitivity": "nvlink5_nvl72",
        "gpu_best_intra_link": "nvlink5_nvl72",
        "contract": (
            "Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at "
            "equal silicon area. Blackwell is a two-die package, so B200 is counted "
            "per package at 1,600 mm2 of silicon."
        ),
    },
}

#: ------------------------------------------------------------------------
#: THE QUANTISED VARIANT.  SECONDARY.  A PROJECTION, NOT A MEASUREMENT.
#: ------------------------------------------------------------------------
#: The primary studies price the released checkpoint's own packing on both
#: sides and nothing else.  This block prices ONE alternative, in its own
#: artifact directory, under one rule: **the quantisation applies to both
#: sides.**  A GPU serving 4.25-bit weights reads 3.76x fewer weight bytes too,
#: and a study that halved the ROM side's weight traffic while leaving the GPU
#: at BF16 would be running exactly the asymmetry the released-packing rule was
#: written to stop -- the same rule this program already records for an FP8 KV
#: latent in the DeepSeek profile's ``kv_precision_sensitivity``.
#:
#: **No token has ever been produced at this precision anywhere in this
#: program, on either backend.**  ``configs/hardware/abi3_capability/
#: rom_qwen3.json`` declares BF16 numeric contracts and no sub-byte weight
#: decode and no w4a8 contraction; the 192 oracle-identical tokens this program
#: rests on were produced at BF16.  Every number the variant emits is therefore
#: graded ``derived`` and is a projection of a machine nobody has run at a
#: precision nobody has measured the accuracy of.  It is published so the
#: question "what would quantisation do to this comparison" has a computed
#: answer instead of an intuition, and for no other purpose.
QUANTISED_VARIANT: dict[str, Any] = {
    "variant_id": "quantised_variant",
    "status": "SECONDARY -- PROJECTION, NOT A MEASUREMENT",
    "models": (STUDY_MODELS[0],),
    "representation": ("q4p25", 4.25),
    "bits_per_parameter": 4.25,
    "executed_tokens_at_this_precision": 0,
    "format": (
        "4.25 bits per parameter, held identical on both sides. That is MXFP4 "
        "as the OCP Microscaling specification defines it -- 4-bit E2M1 "
        "elements in blocks of 32 with one 8-bit E8M0 block scale, "
        "(32x4 + 8) / 32 = 4.25 -- and it is within a rounding of INT4 "
        "group-128 with an FP16 scale and an INT4 zero point, "
        "(128x4 + 16 + 4) / 128 = 4.16, which is how vLLM and TensorRT-LLM "
        "actually ship 4-bit weights today."
    ),
    "arithmetic": (
        "Both sides declare the w4a8 datapath their stored width implies, and "
        "each part then executes it or emulates it according to its OWN "
        "published format table, which is where the two studies stop being "
        "symmetric. configs/hardware/technology.json gives a100_sxm_80gb "
        "native_formats [bf16, fp32] and emulates fp4, fp8 and w4a8 to bf16: "
        "Ampere has no low-precision floating-point tensor core, so an A100 "
        "serving 4-bit weights gains BYTES and never arithmetic. b200_sxm "
        "declares w4a8 native. The ROM side takes the arithmetic credit in "
        "both studies. That asymmetry is a fact about Ampere, not a modelling "
        "choice, and it is the reason BOTH pairings are published: reporting "
        "only n6_vs_a100 would be selecting the study in which the GPU is "
        "architecturally forbidden from taking the credit the ROM side takes."
    ),
    "scope": (
        "Qwen3-8B only. The variant is defined only where the release ships "
        "ABOVE the width production GPU stacks already serve. Qwen3-8B ships "
        "at 16.00 bits and qualifies. DeepSeek-V4-Flash-0731 at 4.70 and "
        "DeepSeek-V4-Pro-0813 at 4.46 bits already ship mixed FP8 dense plus "
        "MXFP4 routed -- they are at that floor, and re-quantising them would "
        "mean pushing the GPU below what any production stack serves, which is "
        "the same one-sided offer in the other direction."
    ),
    "unmodelled": (
        "Four real mask-ROM advantages have no term in this roofline and the "
        "variant must not be argued on them: zero scale-storage (a GPU pays "
        "0.25 bits per parameter for an MXFP4 block scale and 0.5 for NVFP4, a "
        "mask ROM folds it into the datapath at mask time), zero "
        "dequantisation instructions and energy (QServe measures 20-90% GPU "
        "runtime overhead for INT4 dequant), free non-byte-aligned widths, and "
        "free codebook quantisation. One real mask-ROM DISadvantage is equally "
        "unmodelled: a mask ROM cannot be re-quantised after tape-out, so a bad "
        "quantisation is a scrapped mask set, a risk with no GPU counterpart. "
        "A fifth term, the balanced ROM+MAC floorplan rule, IS modelled and is "
        "modelled wrongly at this width -- see known_defect."
    ),
    "known_defect": (
        "src/opentallas/roofline.py's balanced ROM+MAC rule sizes the MAC "
        "array at one weight byte per multiply-accumulate against a hard-coded "
        "fp8 compute density. At 4.25 bits a byte carries 1.88 weights, so the "
        "MAC array is under-provisioned by that factor and the array is "
        "correspondingly over-provisioned. The rule is exactly right at 16 "
        "bits on a bf16 datapath, which is why the BF16 primary is untouched by "
        "it. It is left as it is here rather than corrected, because "
        "correcting it would move 1,456 published ROM points in the PRIMARY "
        "studies -- 728 in each, every batched design with "
        "spare_area_policy = rom on a w4a8 datapath, all of them DeepSeek, "
        "which already executes w4a8 at its released packing of 4.70 and 4.46 "
        "bits -- and the instruction for this revision is that the primary "
        "result does not move except where the design selection moves it. The "
        "defect is recorded, its direction is stated on every variant table, "
        "and it should be fixed on its own, in its own change, where the size "
        "of the correction is the only thing being read."
    ),
    "accuracy": (
        "ABSENT ENTIRELY, on both sides, and this is the variant's real "
        "exposure rather than its rate. The published band on 4.25-bit weights "
        "runs from NVIDIA's vendor-run '1% or less' on one model to the OCP MX "
        "authors' own direct-cast MXFP4 measurement of a 24% relative Lambada "
        "drop on LLaMA-7B (0.736 -> 0.557). Nothing in this program has "
        "measured where a real deployment lands inside that band, on either "
        "backend. A rate reported without that band beside it is the same class "
        "of claim as a projected speedup for a machine nobody has run."
    ),
    "what_would_make_it_a_measurement": (
        "(i) Quantise Qwen3-8B to this format and run the existing HBM lane: "
        "configs/hardware/abi3_capability/hbm_sram_single_chip.json already "
        "declares mxfp4 and fp8 contracts and an FP4 quantise/reconstruct pair, "
        "executed for DeepSeek. (ii) Build the ROM lane, where nothing exists: "
        "rom_qwen3.json needs a sub-byte weight-decode contract, a w4a8 "
        "contraction contract, backend lowering and a re-exported image. "
        "(iii) The gate cannot be token identity against the BF16 oracle -- "
        "quantisation changes tokens by construction. It has to be "
        "cross-backend identity, the ROM lane and the HBM lane at the SAME "
        "format producing identical tokens position for position, plus a "
        "measured accuracy budget with a divergence horizon in the form this "
        "program already reports. (iv) The w4a8 compute density needs silicon "
        "behind it at N6; it is currently derived from published A100 INT4/INT8 "
        "roofs scaled by logic density."
    ),
}

# The policy list has exactly one definition, in the model.  This file used
# to keep its own copy, and a second restatement of one list is how the two
# come apart -- the third policy was added to the model and silently not
# studied here.
from opentallas.roofline import WEIGHT_AMORTIZATIONS  # noqa: E402


def _cim_cells(technology: Technology, bits: float | None) -> CimCellAccounting:
    """Select-cell accounting for a compute-in-ROM design of this representation.

    Native checkpoints here store FP4, FP8, BF16 and FP32 elements, all whole
    multiples of a 4-bit cell, so they pack at exactly the cell width.  A
    uniform re-quantisation stores ``floor(bits)``-bit elements plus the
    fractional remainder as block scales (MXFP4: 4 + 0.25).
    """

    width = technology.graded("rom", "cim_bits_per_cell")
    if bits is None:
        return CimCellAccounting(width.value, width)
    element = float(math.floor(bits))
    return CimCellAccounting(element, width, scale_bits=bits - element)
"""The unresolved architectural fork from docs/ANALYTICAL_REPORT.md.
``batched`` is ROM-as-storage feeding a separate MAC array, where one sweep
serves the whole batch. ``per_stream`` is compute-in-ROM, where a cell both
stores and multiplies, so each concurrent stream needs its own pass and
aggregate per-die throughput collapses onto per-user throughput. They are
equal in sweep count at batch 1, but their cell size and pre-compute reservation
give them different floorplans. The batch-1 anchor can test those physical
consequences; it cannot establish the high-batch scaling law. Both are
evaluated; the main tables show ``batched`` and the fork section shows the
difference."""
SPARE_AREA_POLICIES: tuple[str, ...] = ("sram", "rom")
"""What a ROM design does with silicon it does not have to spend on its array.

``sram`` is the previous behaviour: the array is sized to the stored bytes, and
what is left becomes KV store on a compute-in-ROM part or a MAC array on an
amortising one.  ``rom`` grows the array into that silicon as **replicated
copies of the same weights**, which cuts the full-array sweep time by the
replication factor because each copy carries its own bitlines and sense amps.

Both are emitted for **all three** amortisation policies.  Offering the
floorplan sweep only to compute-in-ROM would decide the comparison by the
allocation rule rather than by physics -- which is exactly the failure this
sweep exists to remove."""

ROM_AREA_LADDER: tuple[int, ...] = (1, 2, 3, 4, 6, 8, 12)
"""Wafer counts the ROM side is emitted at regardless of what the sizing sweep
chooses, so the iso-area curve is sampled at the same silicon on both sides and
a correction that moves the sizing optimum cannot silently move the areas the
comparison is read at.  Seven rungs rather than every integer: they span the
whole range, they include every area the published headline was read at, and the
artifact is a checked-in file whose size is a real cost."""

GPU_AREA_LADDER: tuple[int, ...] = ROM_AREA_LADDER

ARRAY_DEVICE_LADDER_MULTIPLIERS: tuple[float, ...] = (1.25, 1.5, 2.0, 3.0, 4.0)
"""Where the reticle-array class is sampled beyond its own sizing choice.

Until 2026-09-03 ``ROM_AREA_LADDER`` was applied where ``plan.kind == "wafer"``
and nowhere else, so an array existed at an area only if some sizing sweep
landed there, and the report said so in its own closing paragraph.  Two rung
families close that hole.  Multiples of the smallest machine that physically
holds the design sample the array's own curve between its floor and four times
it.  The device counts whose silicon equals each wafer rung of
``ROM_AREA_LADDER`` put an array at every area a wafer design is emitted at,
which is the row the wafer-versus-array comparison is read on.  Both are capped
by ``ARRAY_SWEEP_CAP`` like every other array."""
"""The GPU baseline is evaluated at the same wafer-equivalents of silicon
whatever the ROM sizing sweep chooses, so the iso-area curve is sampled over the
whole range this study spans rather than only where a ROM design lands."""

ARRAY_SWEEP_CAP = 400
SWEEP_PATIENCE = 8
"""Stop the device sweep once eight consecutive larger machines fail to beat the
best latency found so far.  Adding devices adds compute area but also adds a
serial hop, so the curve has one minimum."""
DEVICE_SIZING_TOLERANCE = 0.02
"""A design point is the smallest device count within 2% of the best latency the
sweep found.  Without this a model is handed a whole wafer to buy the last 1% of
a rate it already had on four chips."""
BEST_DESIGN_TOLERANCE = 0.05
"""When the topology-choice table names a winner it takes the smallest silicon
area within 5% of the best per-user rate, so a topology cannot win by simply
being handed more silicon."""
MAX_OVERPROVISION = 4
"""A design may spend at most four times the device count its stored weights and
resident KV actually demand.  Beyond that it is a different machine and belongs
in the comparison as one, not as a sizing choice; without this bound the
latency-minimising sweep will hand an 8B model twenty-one wafers to buy the last
few percent of KV bandwidth."""


def _rom_sweep_time_s(technology: Technology, node: str) -> float:
    """The ROM full-array sweep time, which is the ROM path's hard floor.

    HBM is provisioned against this: there is no point buying KV bandwidth that
    would beat a floor the weight path cannot beat anyway.
    """

    capacity_bytes_per_mm2 = technology.rom_bits_per_mm2(node).value / 8.0
    bandwidth = (
        technology.rom_read_bytes_s_per_mm2(node).value
        * technology.efficiency("rom_read_bandwidth").value
    )
    return capacity_bytes_per_mm2 / bandwidth


def _model_tag(model: ModelProfile) -> str:
    """Short, stable tag so design identifiers do not collide across models."""

    return model.name.split("-0")[0].replace("DeepSeek-V4-", "DSV4-")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finite(value: float) -> float | None:
    return value if math.isfinite(value) else None


def _crossover_row(
    design_id: str, model: ModelProfile, topology: Topology, technology: Technology
) -> dict[str, Any]:
    """One latency-crossover record, with its infinities written down as such.

    A topology with no inter-partition event at all -- a model that fits on one
    device -- has zero link time on a token's critical path, so the rate at
    which hops would consume a tenth of the budget and the rate at which they
    would consume all of it are both unbounded.  ``math.inf`` is the honest
    value and is not JSON, so it is emitted as ``null`` and the fact is stated
    in a field of its own rather than by a reader guessing what a missing number
    meant.  No design in the primary studies has ever hit this; the quantised
    variant does, because an 8B checkpoint at 4.25 bits fits on one reticle.
    """

    record = {
        "design": design_id,
        "model": model.name,
        **latency_crossover(topology, model, technology).to_dict(),
    }
    unbounded = [
        key
        for key in ("viable_tokens_s", "hard_ceiling_tokens_s")
        if isinstance(record.get(key), float) and not math.isfinite(record[key])
    ]
    for key in unbounded:
        record[key] = None
    record["link_latency_unbounded_rate"] = bool(unbounded)
    return record


def _representations(model: ModelProfile) -> tuple[tuple[str, float | None], ...]:
    """Stored representations offered to a mask-ROM design.

    **The released checkpoint's own packing, and nothing else.**

    An earlier version also offered an FP8 variant wherever the release was
    wider than 8.5 bits, on the reasoning that mask ROM freezes its
    representation at manufacture and so the representation is a design variable
    rather than an inherited constant. That reasoning is defensible in the
    abstract and it was wrong here, for three reasons that compound:

    * **It was offered to one side only.** Every GPU design is evaluated at
      ``official_packed``. An 8-bit ROM machine against a 16-bit GPU is not an
      iso-anything comparison, and it halves the ROM array's weight traffic for
      free. Half of every feasible Qwen comparison -- 430 of 862 -- was being
      won by such a design, the best of them at 30.79x.
    * **No executed lane validates it.** ``rom_qwen3`` declares BF16 contracts
      and no FP8 contract at all, and the 192 oracle-identical tokens this
      program rests on were produced at BF16. A projected speedup for a machine
      nothing has ever run is the kind of claim this program exists to refuse.
    * **It changes the model's outputs.** Re-encoding BF16 weights to FP8 is a
      quantisation, not a repacking. It would produce different tokens, and how
      different is unmeasured.

    Only Qwen3-8B was affected: it ships at 16.0 bits per parameter, while
    DeepSeek V4 Flash and Pro ship mixed FP8/MXFP4 at 4.70 and 4.46 bits, below
    the threshold that offered the variant.

    If a future study wants to price a quantised part, it must quantise **both**
    sides and validate the arithmetic against an execution -- the same rule this
    program applies to an FP8 KV latent, recorded in the DeepSeek profile's
    ``kv_precision_sensitivity``.
    """

    return (("native", None),)


def _execution_format(technology: Technology, bits: float | None, model: ModelProfile) -> str:
    """Canonical datapath a model-specific ROM part would build for a representation.

    A part that stores 8-bit weights builds an 8-bit datapath; one that stores
    4-to-5-bit weights against 8-bit activations builds a w4a8 datapath.  The
    released checkpoint's arithmetic is not automatically what the ASIC executes.
    """

    if bits is None:
        bits = model.checkpoint_bytes / model.total_parameters * 8.0
    if bits <= 6.0:
        return "w4a8"
    if bits <= 8.5:
        return "fp8"
    return "bf16"


def _rom_stored_bytes(model: ModelProfile, bits: float | None) -> float:
    if bits is None:
        return model.checkpoint_bytes
    return model.total_parameters * bits / 8.0


def _hbm_stacks_for(
    technology: Technology,
    *,
    generation: str,
    resident_kv_bytes: float,
    kv_transfer_bytes: float,
    sweep_time_s: float,
    die_area_mm2: float,
    devices: int,
) -> int:
    """Stacks per device, provisioned for KV capacity *and* KV bandwidth.

    Weights live in ROM on these designs, so HBM carries only the mutable KV.
    The stated provisioning rule is: enough stacks that neither KV capacity nor
    KV bandwidth binds before the ROM full-array sweep does, capped by what the
    die edge can physically attach at the beachfront utilisation shipping GPUs
    achieve.  When the cap bites, KV bandwidth or capacity binds -- and that is
    a physical result about die perimeter, not a modelling shortcut.
    """

    capacity = technology.hbm(generation, "stack_capacity_bytes").value
    usable = capacity * technology.efficiency("hbm_capacity").value
    bandwidth = (
        technology.hbm(generation, "stack_bandwidth_bytes_s").value
        * technology.efficiency("hbm_bandwidth").value
    )
    for_capacity = math.ceil(resident_kv_bytes / max(1, devices) / usable)
    for_bandwidth = (
        math.ceil(kv_transfer_bytes / max(1, devices) / (sweep_time_s * bandwidth))
        if sweep_time_s > 0
        else 0
    )
    limit = max_hbm_stacks_per_device(
        technology, generation=generation, die_area_mm2=die_area_mm2
    )
    return max(1, min(limit, max(for_capacity, for_bandwidth)))


# --------------------------------------------------------------------------
# design construction
# --------------------------------------------------------------------------


def _array_device_ladder(
    floor: int, *, wafer_area: float, reticle_area: float
) -> set[int]:
    """The device counts an array is emitted at beyond its sizing sweep's pick.

    ``floor`` is the smallest device count that physically holds the design.
    The multiplier rungs sample the array's own curve above it; the wafer-area
    rungs are the counts whose silicon equals ``k`` wafers for each ``k`` in
    ``ROM_AREA_LADDER``, so that every wafer design has an array at the same
    area.  Nothing below the floor is emitted -- the design does not fit there
    -- and nothing above ``ARRAY_SWEEP_CAP``.
    """

    rungs: set[int] = set()
    for multiplier in ARRAY_DEVICE_LADDER_MULTIPLIERS:
        rungs.add(int(math.ceil(floor * multiplier)))
    dies_per_wafer = wafer_area / reticle_area
    for wafers in ROM_AREA_LADDER:
        rungs.add(int(round(wafers * dies_per_wafer)))
    return {count for count in rungs if floor <= count <= ARRAY_SWEEP_CAP}


def _regions_for(
    plan: "FabricPlan",
    devices: int,
    wafer_area: float | None,
    reticle_area: float | None,
) -> int:
    """Reticle fields a design spans, which is what its hop count is counted in."""

    if plan.kind == "wafer" and wafer_area and reticle_area:
        return max(1, math.ceil(devices * wafer_area / reticle_area))
    return 1


@dataclass(frozen=True)
class FabricPlan:
    """The two link classes a machine actually has, and the domain between them.

    A cluster is not one fabric.  An HGX baseboard is an all-to-all NVLink
    island of ``intra_domain_size`` devices; past the island edge every byte
    goes onto a scale-out network an order of magnitude slower in latency and
    more than an order slower in per-device bandwidth.  A wafer is the same
    shape with different numbers: an on-wafer stitched mesh inside one wafer,
    a package-class link between wafers.

    The same plan is handed to the ROM side and to the GPU side of each study,
    so neither is charged a fabric the other is not.
    """

    kind: str
    parallelism: str
    intra_link: str
    inter_link: str
    intra_domain_size: int
    label: str
    moe_fanout: int = 0

    def topology(self, devices: int, regions: int) -> Topology:
        group = (
            self.intra_domain_size
            if self.parallelism in ("hybrid", "expert")
            else 1
        )
        return Topology(
            kind=self.kind,
            device_count=devices,
            parallelism=self.parallelism,
            link=self.inter_link,
            on_wafer_regions=regions,
            intra_link=self.intra_link,
            intra_domain_size=self.intra_domain_size,
            tensor_group_size=group,
            moe_fanout=self.moe_fanout,
        )


def _fabric_plans(
    technology: Technology,
    config: dict[str, Any],
    *,
    wafer_area: float,
    reticle_area: float,
) -> tuple[tuple[FabricPlan, float], ...]:
    """Every (topology, area-per-device) pair the ROM side is allowed to choose.

    Three parallelisms on each of two device classes.  ``hybrid`` is the one a
    real deployment runs -- tensor-parallel inside the high-bandwidth domain,
    pipeline-parallel across domains -- and it was previously offered to
    neither side.
    """

    intra = str(config["intra_link"])
    inter = str(config["inter_link"])
    # The wafer fabrics are named by the study, not hard-wired here, so the ROM
    # side scales with its node exactly as the GPU side does.
    wafer_intra = str(config["rom_intra_link"])
    wafer_inter = str(config["rom_inter_link"])
    array_domain = max(1, int(technology.link_domain_size(intra).value))
    regions_per_wafer = max(1, math.ceil(wafer_area / reticle_area))
    plans: list[tuple[FabricPlan, float]] = []
    # **Hardware-limited ROM arrays** (the redesign): dies share an interposer
    # package over UCIe-class links and packages connect over direct SerDes,
    # with latencies built from PHY, flight and router terms and no software
    # stack.  A hybrid plan puts one layer's tensor group inside one package
    # and pipelines layers across packages -- a ROM stage reads its own weights
    # locally, so pipelining costs it no bandwidth.  These plans are ROM-only;
    # the GPU keeps the published fabric it ships with.
    hw_intra = config.get("rom_array_intra_link")
    hw_inter = config.get("rom_array_inter_link")
    if hw_intra and hw_inter:
        hw_domain = max(1, int(technology.link_domain_size(str(hw_intra)).value))
        for parallelism in ("pipeline", "tensor", "hybrid"):
            plans.append(
                (
                    FabricPlan(
                        kind="array",
                        parallelism=parallelism,
                        intra_link=str(hw_intra),
                        inter_link=str(hw_inter),
                        intra_domain_size=hw_domain,
                        label=f"array-hw-{parallelism}",
                    ),
                    reticle_area,
                )
            )
    for parallelism in ("pipeline", "tensor", "hybrid"):
        plans.append(
            (
                FabricPlan(
                    kind="array",
                    parallelism=parallelism,
                    intra_link=intra,
                    inter_link=inter,
                    intra_domain_size=array_domain,
                    label=f"array-{parallelism}",
                ),
                reticle_area,
            )
        )
        plans.append(
            (
                FabricPlan(
                    kind="wafer",
                    parallelism=parallelism,
                    intra_link=wafer_intra,
                    inter_link=wafer_inter,
                    intra_domain_size=regions_per_wafer,
                    label=f"wafer-{parallelism}",
                ),
                wafer_area,
            )
        )
    return tuple(plans)


def _build_rom_budget(
    technology: Technology,
    *,
    name: str,
    node: str,
    area_per_device: float,
    devices: int,
    plan: FabricPlan,
    on_wafer_regions: int,
    stored_weight_bytes: float,
    resident_kv_bytes: float,
    kv_transfer_bytes: float,
    kv_store: str,
    hbm_generation: str,
    weight_amortization: str = "batched",
    spare_area_policy: str = "sram",
    weight_bits: float | None = None,
) -> DeviceBudget:
    stacks = 0
    if kv_store == "hbm":
        stacks = _hbm_stacks_for(
            technology,
            generation=hbm_generation,
            resident_kv_bytes=resident_kv_bytes,
            kv_transfer_bytes=kv_transfer_bytes,
            sweep_time_s=_rom_sweep_time_s(technology, node),
            die_area_mm2=area_per_device,
            devices=devices,
        )
    topology = plan.topology(devices, on_wafer_regions)
    return rom_device_budget(
        technology,
        name=name,
        node=node,
        area_mm2_per_device=area_per_device,
        topology=topology,
        stored_weight_bytes=stored_weight_bytes,
        resident_kv_bytes=resident_kv_bytes if kv_store == "sram" else 0.0,
        kv_store=kv_store,
        hbm_stacks=stacks,
        hbm_generation=hbm_generation,
        weight_amortization=weight_amortization,
        spare_area_policy=spare_area_policy,
        cim_cells=_cim_cells(technology, weight_bits),
    )


def _minimum_devices(
    technology: Technology,
    *,
    node: str,
    area_per_device: float,
    stored_weight_bytes: float,
    resident_kv_bytes: float,
    kv_transfer_bytes: float,
    kv_store: str,
    hbm_generation: str,
    plan: FabricPlan,
    wafer_area: float | None,
    reticle_area: float | None,
    weight_amortization: str = "batched",
    spare_area_policy: str = "sram",
    weight_bits: float | None = None,
) -> int:
    """Fewest devices that can physically hold the design.

    **Sized on the policy's own floorplan.**  This used to size once on the
    batched machine and hand the count to all three, on the reasoning that their
    sweep-count terms coincide at batch 1.  That reasoning omitted the policy's
    physical floorplan: a compute-in-ROM cell is 1.6x a storage cell, so the
    same weights need 1.6x the array and can need more dies.  Sizing all three
    on the batched floorplan denied compute-in-ROM the dies it needs and
    reported the result as infeasibility -- "it cannot hold this model" when
    the truth was "we never tried enough dies".

    ROM area is fixed by the stored weights and SRAM area by the resident KV, so
    the remainder available for compute is what device count actually buys.  For
    an HBM-KV design the die edge is a second, independent floor: a machine that
    cannot attach enough stacks to hold the provisioning batch's KV needs more
    dies, however much compute area it already has.
    """

    usable_stack = (
        technology.hbm(hbm_generation, "stack_capacity_bytes").value
        * technology.efficiency("hbm_capacity").value
    )
    for devices in range(1, ARRAY_SWEEP_CAP + 1):
        regions = _regions_for(plan, devices, wafer_area, reticle_area)
        budget = _build_rom_budget(
            technology,
            name="minimum-probe",
            node=node,
            area_per_device=area_per_device,
            devices=devices,
            plan=plan,
            on_wafer_regions=regions,
            stored_weight_bytes=stored_weight_bytes,
            resident_kv_bytes=resident_kv_bytes,
            kv_transfer_bytes=kv_transfer_bytes,
            kv_store=kv_store,
            hbm_generation=hbm_generation,
            weight_amortization=weight_amortization,
            spare_area_policy=spare_area_policy,
            weight_bits=weight_bits,
        )
        if budget.reasons or budget.split.compute_mm2 <= 0:
            continue
        if budget.weight_capacity_bytes + 1.0 < stored_weight_bytes:
            continue
        if kv_store == "hbm":
            attachable = (
                max_hbm_stacks_per_device(
                    technology,
                    generation=hbm_generation,
                    die_area_mm2=area_per_device,
                )
                * devices
                * usable_stack
            )
            if attachable + 1.0 < resident_kv_bytes:
                continue
        elif budget.kv_capacity_bytes + 1.0 < resident_kv_bytes:
            continue
        return devices
    return ARRAY_SWEEP_CAP + 1


def _size_array(
    technology: Technology,
    model: ModelProfile,
    *,
    node: str,
    area_per_device: float,
    stored_weight_bytes: float,
    resident_kv_bytes: float,
    kv_transfer_bytes: float,
    kv_store: str,
    hbm_generation: str,
    context_tokens: int,
    execution_format: str,
    weight_bits: float | None,
    plan: FabricPlan,
    wafer_area: float | None = None,
    reticle_area: float | None = None,
    weight_amortization: str = "batched",
    spare_area_policy: str = "sram",
) -> tuple[int, list[dict[str, Any]]]:
    """Choose the device count that minimises per-user token latency at batch 1.

    Adding devices adds compute area and SRAM area but leaves total ROM area --
    and therefore the ROM full-array sweep time -- unchanged, because ROM area
    is set by the stored weights.  It also adds one serial hop per device under
    pipeline parallelism.  The optimum is therefore where compute stops being
    the binding term, and beyond it the interconnect takes over: the sweep below
    is exactly the wafer-versus-array trade, resolved rather than asserted.
    """

    minimum = _minimum_devices(
        technology,
        node=node,
        area_per_device=area_per_device,
        stored_weight_bytes=stored_weight_bytes,
        resident_kv_bytes=resident_kv_bytes,
        kv_transfer_bytes=kv_transfer_bytes,
        kv_store=kv_store,
        hbm_generation=hbm_generation,
        plan=plan,
        wafer_area=wafer_area,
        reticle_area=reticle_area,
        weight_amortization=weight_amortization,
        spare_area_policy=spare_area_policy,
        weight_bits=weight_bits,
    )
    if minimum > ARRAY_SWEEP_CAP:
        return minimum, []
    upper = min(ARRAY_SWEEP_CAP, minimum * MAX_OVERPROVISION)
    sweep: list[dict[str, Any]] = []
    best_latency = math.inf
    stale = 0
    for devices in range(minimum, upper + 1):
        regions = _regions_for(plan, devices, wafer_area, reticle_area)
        budget = _build_rom_budget(
            technology,
            name="sizing-probe",
            node=node,
            area_per_device=area_per_device,
            devices=devices,
            plan=plan,
            on_wafer_regions=regions,
            stored_weight_bytes=stored_weight_bytes,
            resident_kv_bytes=resident_kv_bytes,
            kv_transfer_bytes=kv_transfer_bytes,
            kv_store=kv_store,
            hbm_generation=hbm_generation,
            weight_amortization=weight_amortization,
            spare_area_policy=spare_area_policy,
            weight_bits=weight_bits,
        )
        step = evaluate(
            budget,
            model,
            context_tokens=context_tokens,
            batch_size=DESIGN_BATCH,
            technology=technology,
            weight_bits_per_parameter=weight_bits,
            execution_format=execution_format,
        )
        latency = step.step_time_s if step.feasible else math.inf
        sweep.append(
            {
                "device_count": devices,
                "silicon_area_mm2": budget.silicon_area_mm2_total,
                "compute_mm2_per_device": budget.split.compute_mm2,
                "feasible": step.feasible,
                "per_user_tokens_s": step.per_user_tokens_s,
                "step_time_s": _finite(step.step_time_s),
                "binding_constraint": step.binding_constraint,
                "component_times_s": dict(step.component_times_s),
            }
        )
        if latency < best_latency * (1.0 - 1e-12):
            best_latency = latency
            stale = 0
        else:
            stale += 1
            if stale >= SWEEP_PATIENCE and math.isfinite(best_latency):
                break
    # Buying more silicon than the latency actually rewards is the failure this
    # model exists to catch, so the design point is the SMALLEST device count
    # within DEVICE_SIZING_TOLERANCE of the best latency in the sweep, not the
    # fastest point in it.
    threshold = best_latency * (1.0 + DEVICE_SIZING_TOLERANCE)
    for entry in sweep:
        if entry["feasible"] and entry["step_time_s"] is not None:
            if entry["step_time_s"] <= threshold:
                return entry["device_count"], sweep
    return minimum, sweep


# --------------------------------------------------------------------------
# study
# --------------------------------------------------------------------------


def _best_ttft(rom: list[dict[str, Any]], gpu: list[dict[str, Any]]) -> dict[str, Any]:
    """Each side's fastest prefill layout at one area (prefill is priced at batch 1)."""

    r = [p for p in rom if p.get("time_to_first_token_s")]
    g = [p for p in gpu if p.get("time_to_first_token_s")]
    if not r or not g:
        return {}
    rb = min(r, key=lambda p: p["time_to_first_token_s"])
    gb = min(g, key=lambda p: p["time_to_first_token_s"])
    return {
        "rom_best_ttft_design": rb["design"],
        "rom_best_time_to_first_token_s": rb["time_to_first_token_s"],
        "gpu_best_ttft_design": gb["design"],
        "gpu_best_time_to_first_token_s": gb["time_to_first_token_s"],
        "time_to_first_token_ratio": rb["time_to_first_token_s"] / gb["time_to_first_token_s"],
    }


def _capacity_comparison(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Each side's best achievable throughput and energy at the same silicon.

    Framework review finding 1: a throughput ratio is only meaningful between
    two machines each run at their own best operating point.  For every model,
    context and ROM silicon area this takes the best feasible aggregate rate and
    the lowest energy per delivered token over **every** design and batch on
    each side at that area (within 6%), and states the users each needed.
    """

    rows: list[dict[str, Any]] = []
    feasible = [p for p in points if p["feasible"]]
    keys = sorted({(p["model"], p["context_tokens"]) for p in feasible})
    for model_name, context in keys:
        here = [p for p in feasible if p["model"] == model_name and p["context_tokens"] == context]
        rom = [p for p in here if p["family"] == "rom"]
        gpu = [p for p in here if p["family"] == "gpu"]
        for area in sorted({round(p["silicon_area_mm2"], -2) for p in rom}):
            r = [p for p in rom if abs(p["silicon_area_mm2"] - area) <= 0.06 * area]
            g = [p for p in gpu if abs(p["silicon_area_mm2"] - area) <= 0.06 * area]
            if not r or not g:
                continue
            ra = max(r, key=lambda p: p["aggregate_tokens_s"])
            ga = max(g, key=lambda p: p["aggregate_tokens_s"])
            energetic = [p for p in r if p["energy_j_per_token"]]
            genergetic = [p for p in g if p["energy_j_per_token"]]
            re_ = min(energetic, key=lambda p: p["energy_j_per_token"]) if energetic else None
            ge = min(genergetic, key=lambda p: p["energy_j_per_token"]) if genergetic else None
            rows.append(
                {
                    "model": model_name,
                    "context_tokens": context,
                    "silicon_area_mm2": area,
                    "rom_best_aggregate_design": ra["design"],
                    "rom_best_aggregate_batch": ra["batch_size"],
                    "rom_best_aggregate_users": ra["pipeline_fill_users"],
                    "rom_best_aggregate_tokens_s": ra["aggregate_tokens_s"],
                    "gpu_best_aggregate_design": ga["design"],
                    "gpu_best_aggregate_batch": ga["batch_size"],
                    "gpu_best_aggregate_users": ga["pipeline_fill_users"],
                    "gpu_best_aggregate_tokens_s": ga["aggregate_tokens_s"],
                    "aggregate_ratio": (
                        ra["aggregate_tokens_s"] / ga["aggregate_tokens_s"]
                        if ga["aggregate_tokens_s"]
                        else None
                    ),
                    "rom_best_energy_design": re_["design"] if re_ else None,
                    "rom_best_energy_batch": re_["batch_size"] if re_ else None,
                    "rom_best_energy_j_per_token": re_["energy_j_per_token"] if re_ else None,
                    "gpu_best_energy_design": ge["design"] if ge else None,
                    "gpu_best_energy_batch": ge["batch_size"] if ge else None,
                    "gpu_best_energy_j_per_token": ge["energy_j_per_token"] if ge else None,
                    "tokens_per_joule_ratio": (
                        ge["energy_j_per_token"] / re_["energy_j_per_token"]
                        if re_ and ge
                        else None
                    ),
                    **_best_ttft(r, g),
                }
            )
    return rows


def _step_row(
    step: RooflineStep,
    budget: DeviceBudget,
    *,
    family: str,
    design_id: str,
    model: ModelProfile,
) -> dict[str, Any]:
    metrics = step.metrics
    return {
        "family": family,
        "design": design_id,
        "model": step.model,
        "context_tokens": step.context_tokens,
        "batch_size": step.batch_size,
        "device_count": budget.topology.device_count,
        "topology_kind": budget.topology.kind,
        "parallelism": budget.topology.parallelism,
        "link": budget.topology.link,
        "intra_link": budget.topology.inner_link,
        "intra_domain_size": budget.topology.intra_domain_size,
        # The CHOSEN tensor group: a hybrid layout searches its group per point.
        "tensor_group": metrics["tensor_group"],
        "tensor_group_declared": budget.topology.tensor_group,
        "pipeline_stages": metrics["pipeline_stages"],
        "pipeline_stages_uncapped": metrics["pipeline_stages_uncapped"],
        "hop_breakdown": (
            f"{metrics['serial_latency']['collectives_per_layer']:.2f} collectives per layer "
            f"({', '.join(metrics['serial_latency']['collective_algorithms']) or 'none'}), "
            f"{metrics['serial_latency']['pipeline_hops']} pipeline hops; "
            f"collectives {metrics['serial_latency']['collective_s'] * 1e6:,.2f} us, "
            f"hops {metrics['serial_latency']['pipeline_hop_s'] * 1e6:,.2f} us on the path"
        ),
        "serial_chain_s": metrics["serial_latency"]["chain_s"],
        "serial_critical_path_s": metrics["serial_latency"]["critical_path_s"],
        "serial_binding": metrics["serial_latency"]["binding"],
        "collectives_per_layer": metrics["serial_latency"]["collectives_per_layer"],
        "collective_algorithms": list(metrics["serial_latency"]["collective_algorithms"]),
        "stream_unit_width": metrics["serial_latency"]["stream_unit_width"],
        "serial_clock_hz": metrics["serial_latency"]["clock_hz"],
        "serial_sweep_s": metrics["serial_latency"]["sweep_s"],
        "serial_kv_share_of_sweep": metrics["serial_latency"]["kv_share_of_sweep"],
        "tensor_group_search": [
            {"tensor_group": row["tensor_group"], "step_s": _finite(row["step_s"])}
            for row in metrics["serial_latency"]["tensor_group_search"]
        ],
        "legacy_layer_fixed_latency_s": metrics["legacy_layer_fixed_latency_s"],
        "legacy_link_latency_s": metrics["legacy_link_latency_s"],
        "link_latency_s": step.component_times_s["link_latency"],
        # What the stage cap removes: the extra boundaries a token would cross
        # if it visited every partition, priced by the legacy per-hop rule and
        # added to this step.
        "link_latency_without_stage_cap_s": step.component_times_s["link_latency"]
        + metrics["link_latency_without_stage_cap_s"]
        - metrics["legacy_link_latency_s"],
        "step_time_without_stage_cap_s": (
            step.step_time_s
            + metrics["link_latency_without_stage_cap_s"]
            - metrics["legacy_link_latency_s"]
            if math.isfinite(step.step_time_s)
            else None
        ),
        "link_share_of_step": (
            step.component_times_s["link_latency"] / step.step_time_s
            if math.isfinite(step.step_time_s) and step.step_time_s > 0
            else None
        ),
        "node": budget.node,
        "weight_store": budget.weight_store,
        "kv_store": budget.kv_store,
        "weight_amortization": budget.weight_amortization,
        "spare_area_policy": (
            "rom" if "-romfill" in design_id else "sram"
        ),
        "rom_replication_factor": metrics.get("rom_replication_factor"),
        "rom_sweeps_per_step": metrics.get("rom_sweeps_per_step"),
        "silicon_area_mm2": step.silicon_area_mm2,
        "silicon_area_mm2_per_device": budget.silicon_area_mm2_per_device,
        "feasible": step.feasible,
        "reasons": list(step.reasons),
        # **Two rates, and they are not the same number times the batch.**
        # ``per_user_tokens_s`` is one user's token rate on the full serial
        # path; ``aggregate_tokens_s`` is the machine's rate with every slot
        # occupied, which needs ``token_slots`` concurrent users;
        # ``delivered_tokens_s`` is what the machine actually produces at the
        # requested concurrency.  ``*_throughput_view`` is the single number
        # this study reported for both before the two were separated.
        "per_user_tokens_s": step.per_user_tokens_s,
        "aggregate_tokens_s": step.aggregate_tokens_s,
        "delivered_tokens_s": metrics["delivered_tokens_s"],
        "per_user_tokens_s_throughput_view": metrics[
            "per_user_tokens_s_throughput_view"
        ],
        "latency_correction_x": metrics["latency_correction_x"],
        "token_slots": metrics["token_slots"],
        "microbatch_per_slot": metrics["microbatch_per_slot"],
        "pipeline_fill_users": metrics["pipeline_fill_users"],
        "pipeline_fill_fraction": metrics["pipeline_fill_fraction"],
        "pipeline_fill_limited_by": metrics["pipeline_fill_limited_by"],
        "service_time_per_slot_s": metrics["service_time_per_slot_s"],
        "step_time_s": _finite(step.step_time_s),
        "binding_constraint": step.binding_constraint,
        "component_times_s": dict(step.component_times_s),
        "power_w": step.power_w,
        "thermal_scale": step.thermal_scale,
        # **Power is no longer proportional to traffic.**  ``static_power_w`` is
        # charged per second whether or not a byte moves, which is what lets
        # ``thermal_scale`` bind at all: under the old rule stretching a step
        # always reduced modelled power, so every design was coolable.
        "static_power_w": metrics["static_power_w"],
        "static_power_fraction_of_total": metrics["static_power_fraction_of_total"],
        "static_leakage_w": metrics["static_power"]["leakage_w"],
        "static_clock_w": metrics["static_power"]["clock_w"],
        "static_memory_interface_w": metrics["static_power"]["memory_interface_w"],
        "static_enumerated_w": metrics["static_power"]["enumerated_w"],
        "static_floor_w": metrics["static_power"]["floor_w"],
        "static_floor_binds": metrics["static_power"]["floor_binds"],
        "dynamic_power_w_before_throttle": metrics["dynamic_power_w_before_throttle"],
        "dynamic_energy_breakdown_j": dict(metrics["dynamic_energy_breakdown_j"]),
        "power_density_w_per_mm2": metrics["power_density_w_per_mm2"],
        "static_power_density_w_per_mm2": metrics["static_power_density_w_per_mm2"],
        "power_headroom_fraction": _finite(metrics["power_headroom_fraction"]),
        "cooling_limit_w": metrics["cooling_limit_w"],
        "cooling_headroom_w": metrics["cooling_headroom_w"],
        "cooling_infeasible": metrics["cooling_infeasible"],
        "energy_j_per_token": _finite(metrics["energy_j_per_token"]),
        "energy_j_per_token_at_pipeline_fill": _finite(
            metrics["energy_j_per_token_at_pipeline_fill"]
        ),
        **(
            {
                "time_to_first_token_s": _finite(
                    metrics["prefill"]["time_to_first_token_s"]
                ),
                "prefill_tokens_s": _finite(metrics["prefill"]["prefill_tokens_s"]),
                "prefill_binding_per_chunk": metrics["prefill"]["binding_per_chunk"],
                "request_output_tokens_s": _finite(
                    metrics["prefill"]["request_output_tokens_s"]
                ),
            }
            if "prefill" in metrics and step.feasible
            else {}
        ),
        "dynamic_energy_j_per_token": metrics["dynamic_energy_j_per_token"],
        "stored_weight_bytes": metrics["stored_weight_bytes"],
        "engaged_weight_bytes": metrics["engaged_weight_bytes"],
        "engaged_weight_fraction": metrics["engaged_weight_fraction"],
        "expert_coverage": metrics["expert_coverage"],
        "engaged_devices": metrics["engaged_devices"],
        "effective_weight_read_bytes_s": metrics["effective_weight_read_bytes_s"],
        "peak_weight_read_bytes_s": metrics["peak_weight_read_bytes_s"],
        "kv_transfer_bytes_per_step": metrics["kv_transfer_bytes_per_step"],
        "resident_kv_bytes": metrics["resident_kv_bytes"],
        "max_resident_users": metrics["max_resident_users"],
        "weight_capacity_bytes": metrics["weight_capacity_bytes"],
        "kv_capacity_bytes": metrics["kv_capacity_bytes"],
        # Carried only where the model declares a region resident in its KV
        # store, so that the capacity the placement costs is auditable in the
        # artifact rather than only implied by a smaller max_resident_users, and
        # so that no prior point row gains a zero column.
        **(
            {
                "kv_store_resident_weight_bytes": metrics[
                    "kv_store_resident_weight_bytes"
                ]
            }
            if "kv_store_resident_weight_bytes" in metrics
            else {}
        ),
        "weight_to_kv_read_ratio": _finite(metrics["weight_to_kv_read_ratio"]),
        "execution_format": metrics["execution_format"],
        "hop_events_per_token": metrics["hop_events_per_token"],
        "hop_semantics": metrics["hop_semantics"],
        "operations_by_canonical_format": dict(
            metrics["operations_by_canonical_format"]
        ),
        "area_fractions": budget.split.fractions(),
        "rom_full_array_sweep_time_s": metrics.get("rom_full_array_sweep_time_s"),
        "rom_sweep_ceiling_tokens_s": metrics.get("rom_sweep_ceiling_tokens_s"),
        "overlap_rule": metrics["overlap_rule"],
        # The four completeness corrections, carried on every point so that a
        # reader can see what each one cost where it was applied rather than
        # only in a summary table.
        "region_sweep_depth_mean_uncorrected": metrics.get(
            "region_sweep_depth_mean_uncorrected"
        ),
        "region_sweep_depth_max_over_mean": metrics.get(
            "region_sweep_depth_max_over_mean"
        ),
        "mean_engaged_devices_uncorrected": metrics["mean_engaged_devices_uncorrected"],
        "engaged_device_max_over_mean_correction": metrics[
            "engaged_device_max_over_mean_correction"
        ],
        "layer_fixed_latency_s": metrics["layer_fixed_latency_s"],
        "layer_fixed_latency_fraction_of_step": metrics[
            "layer_fixed_latency_fraction_of_step"
        ],
        "kv_access_granularity_bytes": metrics["kv_access_granularity"][
            "granularity_bytes"
        ],
        "kv_index_layout": metrics["kv_access_granularity"]["layout"],
        "kv_access_granularity_inflation": metrics["kv_access_granularity_inflation"],
        "kv_native_transfer_bytes_per_step": metrics["kv_native_transfer_bytes_per_step"],
        "kv_bank_occupancy": metrics["kv_bank_occupancy"],
        "kv_read_s_under_bank_locality": _finite(
            metrics["kv_read_s_under_bank_locality"]
        ),
    }


def _iso_area_gpu_counts(
    technology: Technology, part: str, target_area_mm2: float
) -> int:
    spec = technology.reference_part(part)
    area = float(spec["die_area_mm2"]["value"])
    return max(1, int(round(target_area_mm2 / area)))


def _minimum_gpu_count(
    technology: Technology,
    part: str,
    *,
    stored_weight_bytes: float,
    resident_kv_bytes: float,
) -> int:
    spec = technology.reference_part(part)
    capacity = float(spec["hbm_capacity_bytes"]["value"])
    usable = capacity * technology.efficiency("hbm_capacity").value
    needed = stored_weight_bytes + resident_kv_bytes
    return max(1, math.ceil(needed / usable))


def _per_region_sizing(
    technology: Technology, model: ModelProfile, node: str
) -> dict[str, Any] | None:
    """How big one expert region is, and what its own pre-compute block costs.

    The per-region design's cost is not the arithmetic: it is a pre-compute
    block and an activation distribution network per region.  Sizing it needs
    the compute-in-ROM array density -- the storage density divided by the cell
    multiplier -- and nothing else, so it is emitted here rather than computed
    in prose.
    """

    if model.num_experts <= 1 or model.routed_weight_bytes <= 0:
        return None
    density = (
        technology.rom_bits_per_mm2_for(node, "per_region").value / BITS_PER_BYTE
    )
    precompute_fraction = technology.graded(
        "rom", "cim_precompute_area_fraction"
    ).value
    reticle_area = technology.graded("reticle", "area_mm2").value
    per_expert_bytes = model.routed_weight_bytes / model.num_experts
    region_mm2 = per_expert_bytes / density
    checkpoint_mm2 = model.checkpoint_bytes / density
    return {
        "num_experts": model.num_experts,
        "experts_per_token": model.experts_per_token,
        "compute_in_rom_capacity_density_bytes_mm2": density,
        "routed_bytes_per_expert": per_expert_bytes,
        "region_mm2": region_mm2,
        "precompute_mm2_per_region": precompute_fraction * region_mm2,
        "all_regions_mm2": region_mm2 * model.num_experts,
        "all_precompute_mm2": precompute_fraction * region_mm2 * model.num_experts,
        "precompute_fraction_of_array": precompute_fraction,
        "whole_checkpoint_mm2": checkpoint_mm2,
        "whole_checkpoint_reticles": checkpoint_mm2 / reticle_area,
    }


def _floorplan_comparison(
    technology: Technology, model: ModelProfile, node: str, area_mm2: float
) -> dict[str, Any]:
    """The two ROM floorplans on one die, and whether the MAC array can be fed.

    The storage machine spends its leftover silicon on a MAC array.  Whether
    that array is reachable is a bandwidth question the model can answer
    directly: at one weight byte per multiply-accumulate, the roof it can
    sustain is the ROM read rate beside it.
    """

    # **Read from the register, never hard-coded.**  This was
    # ``model.total_parameters * 3.5`` with a literal ``3.5`` emitted beside
    # it, so if ``reference_parts.taalas_hc1.weight_bits_per_parameter`` ever
    # moved -- and it is `assumed` with a stated 3.0-6.0 sweep, so it is meant
    # to -- this artifact would silently keep reporting the old packing under
    # the new entry's name.  That is a config-drift defect of exactly the class
    # this program keeps finding: legal values, no trap, nothing refused.
    weight_bits = technology.graded(
        "reference_parts", "taalas_hc1", "weight_bits_per_parameter"
    )
    stored = model.total_parameters * weight_bits.value / BITS_PER_BYTE
    resident = 0.0
    out: dict[str, Any] = {
        "die_area_mm2": area_mm2,
        "stored_weight_bytes": stored,
        "weight_bits_per_parameter": weight_bits.value,
        "weight_bits_per_parameter_grade": weight_bits.grade,
        "weight_bits_per_parameter_source": (
            "configs/hardware/technology.json#reference_parts.taalas_hc1."
            "weight_bits_per_parameter"
        ),
    }
    for policy in ("batched", "per_region"):
        budget = rom_device_budget(
            technology,
            name=f"floorplan-{policy}",
            node=node,
            area_mm2_per_device=area_mm2,
            topology=Topology(
                kind="single_chip", device_count=1, parallelism="none", link="none"
            ),
            stored_weight_bytes=stored,
            resident_kv_bytes=resident,
            kv_store="sram",
            weight_amortization=policy,
            cim_cells=CimCellAccounting(
                weight_bits.value,
                technology.graded("rom", "cim_bits_per_cell"),
                hc1_mixture=not float(weight_bits.value).is_integer(),
            ),
        )
        # The fp8 roof, because the question is whether an 8-bit-weight MAC
        # array can be fed at one weight byte per multiply-accumulate, and the
        # sustained-fraction derate the model charges everywhere else.
        roof = budget.compute_ops_s.get("fp8", 0.0) * technology.efficiency(
            "compute"
        ).value
        # Two operations per MAC, one weight byte per MAC.
        demanded = roof / 2.0
        out[policy] = {
            "rom_mm2": budget.split.rom_mm2,
            "compute_mm2": budget.split.compute_mm2,
            "sram_mm2": budget.split.sram_mm2,
            "weight_capacity_bytes": budget.weight_capacity_bytes,
            "capacity_ratio": (
                budget.weight_capacity_bytes / stored if stored > 0 else None
            ),
            "feasible": not budget.reasons and budget.weight_capacity_bytes >= stored,
            "reasons": list(budget.reasons),
            "peak_compute_ops_s": roof,
            "weight_read_bytes_s": budget.weight_read_bytes_s,
            "weight_bytes_s_demanded_by_the_roof": demanded,
            "feed_ratio": (
                budget.weight_read_bytes_s / demanded if demanded > 0 else None
            ),
            "full_array_sweep_time_s": budget.provenance[
                "rom_full_array_sweep_time_s"
            ].value,
            "cell_area_multiplier": budget.provenance[
                "rom_cell_area_multiplier"
            ].value,
        }
    return out


def _emit_rom_design(
    technology: Technology,
    model: ModelProfile,
    *,
    designs: list[dict[str, Any]],
    points: list[dict[str, Any]],
    crossovers: list[dict[str, Any]],
    node: str,
    representation: str,
    bits: float | None,
    execution: str,
    kv_store: str,
    topology_name: str,
    suffix: str,
    plan: FabricPlan,
    area_per_device: float,
    devices: int,
    regions: int,
    stored: float,
    design_batch_kv: float,
    design_batch_kv_transfer: float,
    hbm_generation: str,
    amortization: str,
    spare_area_policy: str,
    context: int,
    sweep: list[dict[str, Any]],
    sized: bool,
) -> None:
    """Build one ROM design, its crossover and its whole batch sweep."""

    design_id = (
        f"{_model_tag(model)}/ROM-{node}-{representation}-"
        f"{kv_store.upper()}KV-{topology_name}-x{devices}{suffix}"
    )
    budget = _build_rom_budget(
        technology,
        name=design_id,
        node=node,
        area_per_device=area_per_device,
        devices=devices,
        plan=plan,
        on_wafer_regions=regions,
        stored_weight_bytes=stored,
        resident_kv_bytes=design_batch_kv,
        kv_transfer_bytes=design_batch_kv_transfer,
        kv_store=kv_store,
        hbm_generation=hbm_generation,
        weight_amortization=amortization,
        spare_area_policy=spare_area_policy,
        weight_bits=bits,
    )
    designs.append(
        {
            "design": design_id,
            "family": "rom",
            "model": model.name,
            "representation": representation,
            "stored_bits_per_parameter": (
                bits
                if bits is not None
                else model.checkpoint_bytes / model.total_parameters * 8.0
            ),
            "execution_format": execution,
            "topology": topology_name,
            "weight_amortization": amortization,
            "spare_area_policy": spare_area_policy,
            "sizing_rule": (
                (
                    "smallest device count within "
                    f"{DEVICE_SIZING_TOLERANCE:.0%} of the best per-user "
                    f"latency at batch {DESIGN_BATCH}, bounded at "
                    f"{MAX_OVERPROVISION}x the minimum feasible count. "
                    f"SRAM-KV designs are sized at batch {DESIGN_BATCH} "
                    "because SRAM is silicon area; HBM-KV designs are "
                    f"provisioned for batch {PROVISION_BATCH} for both KV "
                    "capacity and enough KV bandwidth to keep KV off the "
                    "critical path ahead of the ROM sweep, capped by the "
                    "die-edge beachfront a shipping GPU achieves"
                )
                if sized
                else (
                    "area-ladder point: this device count is not the sizing "
                    "sweep's choice, it is emitted so the iso-area curve is "
                    "sampled at the same silicon areas on both sides"
                )
            ),
            "device_count_sweep": sweep,
            **budget.to_dict(),
        }
    )
    if sized and amortization == "batched" and spare_area_policy == "sram":
        # Link latency is a property of the topology, so the two
        # amortisation policies produce identical crossovers.
        crossovers.append(
            _crossover_row(design_id, model, budget.topology, technology)
        )
    for batch in BATCHES:
        step = evaluate(
            budget,
            model,
            context_tokens=context,
            batch_size=batch,
            technology=technology,
            weight_bits_per_parameter=bits,
            execution_format=execution,
            prompt_tokens=context if batch == 1 else None,
        )
        points.append(
            _step_row(
                step, budget, family="rom", design_id=design_id, model=model
            )
        )


def _link_latency_scopes(config: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    """The link bands that belong to each side, and the two together.

    A wafer design's only fabrics are the study's ``rom_intra_link`` inside a
    wafer and its ``rom_inter_link`` between wafers, and nothing on the GPU
    side ever touches either.  They are named per study rather than hard-wired
    so the wafer fabric scales with the ROM node exactly as ``nvlink3`` and
    ``nvlink5`` scale with the GPU's, which is why this returns the config's
    values rather than the literals it used to.  The cluster fabrics -- this
    study's ``intra_link`` and ``inter_link`` -- are charged to **both** sides,
    because a ROM array is built on the same interconnect the GPUs are; they
    are grouped as ``gpu`` because the headline GPU design is the only design
    in either family whose whole link budget is made of them.
    """

    return {
        "rom": (str(config["rom_intra_link"]), str(config["rom_inter_link"])),
        "gpu": (str(config["intra_link"]), str(config["inter_link"])),
        "joint": None,  # type: ignore[dict-item]
    }


def _link_latency_sensitivity(
    study_id: str, technology: Technology
) -> list[dict[str, Any]]:
    """The headline table at both ends of every link latency band, per side.

    **Reported three ways, and the reason is an artefact this study used to
    have.**  The band used to be published jointly only -- every link at its
    low end, then every link at its high end.  Moving both sides together
    partly cancels, so the joint band came out *narrower* than the ROM side's
    own band, and a reader could not see that essentially all of the width came
    from one side's constants.  A joint band is the right test for a
    common-mode error and the wrong one for asking how much of the uncertainty
    is ours.  So the wafer fabrics are now swept alone, the cluster fabrics
    alone, and both together, and all three are printed.
    """

    rows: list[dict[str, Any]] = []
    scopes = _link_latency_scopes(STUDIES[study_id])
    for scope, links in scopes.items():
        for bound in ("low", "high"):
            bounded = technology.at_link_latency_bound(bound, links)
            result = _simulate_study(study_id, bounded, with_sensitivity=False)
            for row in _headline_rows(result):
                rows.append(
                    {
                        "scope": scope,
                        "scope_links": list(links or sorted(technology.raw["links"])),
                        "bound": bound,
                        "model": row["model"],
                        "rom_silicon_area_mm2": row["rom_silicon_area_mm2"],
                        "rom_design": row["rom_design"],
                        "rom_per_user_tokens_s": row["rom_per_user_tokens_s"],
                        "iso_area_gpu_design": row["iso_area_gpu_design"],
                        "iso_area_gpu_parallelism": (
                            row["iso_area_gpu_parallelism"]
                        ),
                        "iso_area_gpu_per_user_tokens_s": (
                            row["iso_area_gpu_per_user_tokens_s"]
                        ),
                        "per_user_speed_ratio": row["per_user_speed_ratio"],
                    }
                )
    return rows


def _model_technology(technology: Technology, model_name: str) -> Technology:
    """This model's own serial matrix-pass depth, applied to BOTH sides.

    ``latency.array_pass_boundaries_per_layer`` used to be one flat number for
    every architecture, and it was **right for exactly one of the three models
    in these studies**: Qwen3-8B's decoder layer really does have the four
    serially dependent matrix passes the constant enumerates, so the constant
    looked correct wherever anyone checked it.  DeepSeek-V4's layer has five --
    the router's expert scores must exist before the expert matrices can be
    selected and started -- and the flat value undercharged it by one pass on
    every layer of every point.  That is the failure mode this repository keeps
    finding: a legal value, no trap, nothing refused, and the wrong answer for
    two of three models.

    The fixed per-layer budget is charged to the GPU designs and the ROM
    designs identically, so this is a **model** property and never a family
    property, and returning one technology per model rather than per side is
    what keeps it that way.

    A model that is not named in the table is refused rather than defaulted:
    silently falling back on the dense-block value is how the flat constant
    survived in the first place.
    """

    block = technology.raw["latency"]
    table = block.get("array_pass_boundaries_per_layer_by_model")
    if not isinstance(table, dict):
        raise ValidationError(
            "latency.array_pass_boundaries_per_layer_by_model is missing; the "
            "serial matrix-pass depth is a per-model quantity and this study "
            "will not fall back on a single number for every architecture"
        )
    entry = table.get(model_name)
    if not isinstance(entry, dict) or "value" not in entry:
        raise ValidationError(
            f"no latency.array_pass_boundaries_per_layer_by_model entry for "
            f"{model_name!r}. Add one -- with its own grade, source and note "
            f"-- rather than letting this model inherit another "
            f"architecture's serial depth"
        )
    raw = json.loads(json.dumps(technology.raw))
    raw["latency"]["array_pass_boundaries_per_layer"] = {
        **raw["latency"]["array_pass_boundaries_per_layer"],
        **entry,
    }
    return replace(technology, raw=raw)


def _node_technology(technology: Technology, node: str) -> Technology:
    """This node's own ROM-to-SRAM bit-cell area ratio, substituted before use.

    ``rom.cell_to_sram_cell_area_ratio`` was ONE node-free number applied at
    both modelled ROM nodes, and this repository had already measured that the
    quantity is not node-stable: 0.1298 at 130 nm against 0.2500 at a
    predictive 7 nm node, 92.7% apart.  ``docs/ROM_DENSITY_NODE_TRANSFER.md``
    concluded that the key "needs a per-node treatment, exactly as
    ``links.on_wafer`` was split into ``links.on_wafer`` and
    ``links.on_wafer_n5``".  This is that treatment, in the shape the sibling
    split already has: the study names its node, the node names its value, and
    **a node with no entry is refused rather than defaulted**, because
    inheriting another node's ratio silently is exactly how the flat one
    survived.

    It moves no number today and that is stated in the entries themselves: N6
    and N5 carry the same point and the same band, because nothing published
    and nothing measured here distinguishes them, and ``docs/METHODOLOGY.md``
    section 9 forbids interpolating the two measured nodes to a target one.
    What it changes is that the value is addressed by the node it is for.
    """

    block = technology.raw["rom"]
    table = block.get("cell_to_sram_cell_area_ratio_by_node")
    if not isinstance(table, dict):
        raise ValidationError(
            "rom.cell_to_sram_cell_area_ratio_by_node is missing; the "
            "ROM-to-SRAM cell area ratio is a per-node quantity -- this "
            "repository measured it 92.7% apart at two nodes -- and this "
            "study will not fall back on one node-free number"
        )
    entry = table.get(node)
    if not isinstance(entry, dict) or "value" not in entry:
        raise ValidationError(
            f"no rom.cell_to_sram_cell_area_ratio_by_node entry for {node!r}. "
            f"Add one -- with its own grade, source, note and band -- rather "
            f"than letting this node inherit another node's bit-cell ratio"
        )
    raw = json.loads(json.dumps(technology.raw))
    raw["rom"]["cell_to_sram_cell_area_ratio"] = {
        **raw["rom"]["cell_to_sram_cell_area_ratio"],
        **entry,
    }
    return replace(technology, raw=raw)


def _fabric_clock_variant(technology: Technology, hz: float) -> Technology:
    """A copy at a different fabric clock, with the cycle-derived terms moved.

    ``power.fabric_clock_hz`` sets no rate: it is read once, in
    ``Technology.clock_frequency_hz``, and consumed once, in the clock leg of
    ``device_static_power``.  **But two entries in the ``latency`` block are
    derived in fabric cycles against it** -- ``pipeline_fill_drain_s`` is 32
    cycles and ``sequencer_issue_decode_s`` is 3, with both bands exact integer
    cycle counts -- and neither of them READS it.  Moving the clock on its own
    therefore leaves two constants asserting a derivation that has stopped
    being true, and those two are on the critical path of every token on both
    sides.

    This function moves all three together, which is the only way the question
    "what is this constant worth" has an answer that means anything.  The
    consistency audit refuses the committed file if they ever drift apart.
    """

    raw = json.loads(json.dumps(technology.raw))
    raw["power"]["fabric_clock_hz"] = {
        **raw["power"]["fabric_clock_hz"],
        "value": hz,
    }
    for name in ("pipeline_fill_drain_s", "sequencer_issue_decode_s"):
        entry = raw["latency"][name]
        cycles = entry["derived_in_fabric_cycles"]
        raw["latency"][name] = {
            **entry,
            "value": cycles["value"] / hz,
            "range_low": cycles["range_low"] / hz,
            "range_high": cycles["range_high"] / hz,
        }
    return replace(technology, raw=raw)


def _fabric_clock_points(technology: Technology) -> list[dict[str, Any]]:
    """Every clock the sensitivity is evaluated at, and where it comes from."""

    entry = technology.raw["power"]["fabric_clock_hz"]
    points = [
        {
            "label": "band_low",
            "fabric_clock_hz": float(entry["range_low"]),
            "provenance": "power.fabric_clock_hz.range_low",
            "within_stated_band": True,
        },
        {
            "label": "stated",
            "fabric_clock_hz": float(entry["value"]),
            "provenance": "power.fabric_clock_hz.value",
            "within_stated_band": True,
        },
        {
            "label": "band_high",
            "fabric_clock_hz": float(entry["range_high"]),
            "provenance": "power.fabric_clock_hz.range_high",
            "within_stated_band": True,
        },
    ]
    for label, relative in ASAP7_ROUTED_BLOCKS:
        artifact = ROOT / relative
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        hz = float(payload["place_and_route"]["metrics"]["fmax_hz"])
        points.append(
            {
                "label": label,
                "fabric_clock_hz": hz,
                "provenance": f"{relative}#place_and_route.metrics.fmax_hz",
                "within_stated_band": (
                    float(entry["range_low"]) <= hz <= float(entry["range_high"])
                ),
                "claim_boundary": (
                    "ASAP7 is a PREDICTIVE academic PDK, not a foundry PDK and "
                    "not silicon, and docs/METHODOLOGY.md section 9 forbids "
                    "scaling a frequency from it to N6/N5/N7/N4. This row is "
                    "the size of a question, not a value: it says what the "
                    "study would do if the fabric clock were as slow as an "
                    "unpipelined open-flow implementation of one ABI 3.0 "
                    "engine, and it may not be quoted as a target-node clock."
                ),
            }
        )
    return points


def _fabric_clock_sensitivity(
    study_id: str, technology: Technology
) -> list[dict[str, Any]]:
    """The headline table at every fabric clock, with the cycle terms moved.

    Written because the constant was read as setting the compute roof, which it
    does not, while the place it *is* load-bearing -- two latency constants
    stated in fabric cycles that never read it -- had nothing measuring it.
    """

    rows: list[dict[str, Any]] = []
    for point in _fabric_clock_points(technology):
        variant = _fabric_clock_variant(technology, point["fabric_clock_hz"])
        result = _simulate_study(study_id, variant, with_sensitivity=False)
        fixed = layer_fixed_latency(
            variant, ModelProfile.load(STUDY_MODELS[0][1])
        )[0]
        for row in _headline_rows(result):
            rows.append(
                {
                    **{
                        key: point[key]
                        for key in ("label", "fabric_clock_hz", "provenance",
                                    "within_stated_band")
                    },
                    "qwen3_8b_layer_fixed_latency_s_per_token": fixed,
                    "model": row["model"],
                    "rom_silicon_area_mm2": row["rom_silicon_area_mm2"],
                    "rom_design": row["rom_design"],
                    "rom_per_user_tokens_s": row["rom_per_user_tokens_s"],
                    "rom_binding_constraint": row["rom_binding_constraint"],
                    "iso_area_gpu_design": row["iso_area_gpu_design"],
                    "iso_area_gpu_per_user_tokens_s": (
                        row["iso_area_gpu_per_user_tokens_s"]
                    ),
                    "iso_area_gpu_binding_constraint": (
                        row["iso_area_gpu_binding_constraint"]
                    ),
                    "per_user_speed_ratio": row["per_user_speed_ratio"],
                }
            )
    return rows


def _observed_ratio_coupling(technology: Technology, node: str) -> str:
    """Does ROM read-bandwidth density actually follow the storage cell ratio?

    Measured, not read off the source: halve the ratio and look at what the
    model returns.  ``"proportional"`` if bandwidth density tracks capacity
    density, ``"none"`` if it does not move at all.
    """

    halved = _rom_cell_ratio_variant(
        technology,
        float(technology.raw["rom"]["cell_to_sram_cell_area_ratio"]["value"]) / 2.0,
    )
    before = technology.rom_read_bytes_s_per_mm2(node).value
    after = halved.rom_read_bytes_s_per_mm2(node).value
    return "none" if math.isclose(before, after, rel_tol=1e-9) else "proportional"


def _observed_cim_coupling(technology: Technology, node: str) -> str:
    """The same question asked of the compute-in-ROM cell multiplier."""

    storage = technology.rom_read_bytes_s_per_mm2_for(node, "native").value
    cim = technology.rom_read_bytes_s_per_mm2_for(node, "per_region").value
    return "none" if math.isclose(storage, cim, rel_tol=1e-9) else "proportional"


def _rom_cell_ratio_variant(technology: Technology, ratio: float) -> Technology:
    """A copy at a different ROM-to-SRAM bit-cell area ratio.

    Writes the flat key AND every per-node entry, for two reasons.  The flat
    key is what ``src/opentallas/roofline.py:rom_bits_per_mm2`` reads and what
    the Taalas HC1 gate path is priced with; the per-node entries are what
    ``_node_technology`` substitutes on the way into a study.  Moving one and
    not the other would price the sweep at one ratio and the anchor at another
    inside a single artifact, which is the shape of the one-sided correction
    this repository has already shipped once.
    """

    raw = json.loads(json.dumps(technology.raw))
    raw["rom"]["cell_to_sram_cell_area_ratio"] = {
        **raw["rom"]["cell_to_sram_cell_area_ratio"],
        "value": ratio,
    }
    table = raw["rom"].get("cell_to_sram_cell_area_ratio_by_node")
    if isinstance(table, dict):
        for node_name, entry in table.items():
            table[node_name] = {**entry, "value": ratio}
    return replace(technology, raw=raw)


def _rom_cell_ratio_points(technology: Technology) -> list[dict[str, Any]]:
    """Every ROM cell ratio the sensitivity is evaluated at, and its provenance.

    Both band ends, the stated point, and **all three ratios this repository
    has measured itself**, read out of the committed artifacts rather than
    typed here, so re-running either physical campaign moves this sweep.
    """

    entry = technology.raw["rom"]["cell_to_sram_cell_area_ratio"]
    low = float(entry["range_low"])
    high = float(entry["range_high"])
    points = [
        {
            "label": "band_low",
            "cell_to_sram_cell_area_ratio": low,
            "provenance": "rom.cell_to_sram_cell_area_ratio.range_low",
            "within_stated_band": True,
        },
        {
            "label": "stated",
            "cell_to_sram_cell_area_ratio": float(entry["value"]),
            "provenance": "rom.cell_to_sram_cell_area_ratio.value",
            "within_stated_band": True,
        },
        {
            "label": "band_high",
            "cell_to_sram_cell_area_ratio": high,
            "provenance": "rom.cell_to_sram_cell_area_ratio.range_high",
            "within_stated_band": True,
        },
    ]
    for label, relative, path in MEASURED_ROM_CELL_RATIOS:
        payload: Any = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        for key in path:
            payload = payload[key]
        ratio = float(payload)
        points.append(
            {
                "label": f"measured_{label}",
                "cell_to_sram_cell_area_ratio": ratio,
                "provenance": f"{relative}#{'.'.join(path)}",
                "within_stated_band": low <= ratio <= high,
                "claim_boundary": (
                    "Measured in this repository at a node that is NOT the "
                    "node this study models. docs/METHODOLOGY.md section 9 "
                    "forbids scaling, blending or interpolating a 130 nm or "
                    "predictive-7 nm open-PDK figure to N6/N5/N7/N4, so this "
                    "row is the size of a question and never a value: it says "
                    "what the study would do if the ratio at the target node "
                    "turned out to be the one measured there."
                ),
            }
        )
    return points


def _rom_cell_ratio_sensitivity(
    study_id: str, technology: Technology
) -> list[dict[str, Any]]:
    """The headline table at every ROM bit-cell ratio in the stated band.

    Written because the band was DECLARED and never RUN.  The previous repair
    turned a prose-only "1/6 to 1/4" bracket into real ``range_low`` /
    ``range_high`` fields and made the audit refuse a band excluding either
    committed measurement -- but nothing re-ran the study at those ends, so the
    stated uncertainty was still a claim about the model rather than a result
    from it.  A range that nothing executes is the same defect as a bracket in
    prose, one field further along.

    **This term is one-sided by construction and that is not a fairness
    breach**: the GPU comparators hold no mask ROM, so the ratio cannot reach
    them.  What must therefore be read off this table is not a ratio-to-ratio
    difference but the ROM side's own span, which is reported here alongside
    the binding constraint on BOTH sides at every point -- a less dense array
    is more ROM silicon and therefore more parallel read bandwidth, so the sign
    of this sweep on the headline is not knowable from the band alone.
    """

    node = str(STUDIES[study_id]["rom_node"])
    rows: list[dict[str, Any]] = []
    for point in _rom_cell_ratio_points(technology):
        variant = _rom_cell_ratio_variant(
            technology, point["cell_to_sram_cell_area_ratio"]
        )
        result = _simulate_study(study_id, variant, with_sensitivity=False)
        capacity = variant.rom_bits_per_mm2(node).value / BITS_PER_BYTE
        sweep_s = _rom_sweep_time_s(variant, node)
        for row in _headline_rows(result):
            rows.append(
                {
                    **{
                        key: point[key]
                        for key in ("label", "cell_to_sram_cell_area_ratio",
                                    "provenance", "within_stated_band")
                    },
                    "rom_node": node,
                    "rom_capacity_bytes_per_mm2": capacity,
                    "rom_full_array_sweep_s": sweep_s,
                    "model": row["model"],
                    "rom_silicon_area_mm2": row["rom_silicon_area_mm2"],
                    "rom_design": row["rom_design"],
                    "rom_per_user_tokens_s": row["rom_per_user_tokens_s"],
                    "rom_binding_constraint": row["rom_binding_constraint"],
                    "iso_area_gpu_design": row["iso_area_gpu_design"],
                    "iso_area_gpu_per_user_tokens_s": (
                        row["iso_area_gpu_per_user_tokens_s"]
                    ),
                    "iso_area_gpu_binding_constraint": (
                        row["iso_area_gpu_binding_constraint"]
                    ),
                    "per_user_speed_ratio": row["per_user_speed_ratio"],
                }
            )
    return rows


def _headline_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    """The batch-1 iso-area row at each silicon area, best ROM design per area.

    This is the table the program's headline ratios are read off, so it is the
    table a sensitivity has to be reported on.
    """

    best: dict[tuple[str, int], dict[str, Any]] = {}
    for row in result["comparisons"]:
        if row["batch_size"] != 1 or not row["rom_feasible"]:
            continue
        key = (row["model"], int(round(row["rom_silicon_area_mm2"])))
        current = best.get(key)
        if current is None or (
            row["rom_per_user_tokens_s"] > current["rom_per_user_tokens_s"]
        ):
            best[key] = row
    order = _model_order(result)
    return sorted(
        best.values(),
        key=lambda row: (order[row["model"]], row["rom_silicon_area_mm2"]),
    )


# --------------------------------------------------------------------------
# design selection
# --------------------------------------------------------------------------

SELECTION_AMORTIZATION = "batched"
"""The selection reads the amortising machine, which is what the main tables
show.  The compute-in-ROM fork is a different machine and is reported in its own
section; mixing the two into one frontier would let an unexecuted arithmetic
assumption pick the design."""

MARGINAL_RETURN_BAR = 1.0
"""Parity, not a tuned fraction.

A larger machine is accepted only when the per-user tokens/s it adds per added
mm2 beats the tokens/s per mm2 the machine you already have returns on average
-- you never buy silicon that works less hard than the silicon you have.  The
bar is 1.0 because parity is the only value that needs no defence; every other
value is a preference about how much rate a reader may buy with how much area,
and this study has no standing to set one.  Raising or lowering it cannot be
used to move an answer, because at 1.0 the walk is algebraically identical to
maximising per-user tokens/s per mm2: accepting when
``(r - r0) / (a - a0) >= r0 / a0`` is exactly ``r / a >= r0 / a0``."""

SELECTION_METRIC = (
    "Among the ROM designs feasible for this model at this batch, keep every "
    "design that no other feasible design of the same model and batch beats on "
    "BOTH per-user tokens/s and tokens/s per 1,000 mm2. That non-dominated set "
    "is the reported frontier, and it is published in full. Order it by silicon "
    "area, start at the smallest feasible machine, and accept each larger rung "
    "only while the per-user tokens/s it adds per added mm2 is strictly greater "
    "than the tokens/s per mm2 the incumbent already returns on average; ties go "
    "to the smaller machine. The rung the walk stops on is the recommended "
    "design. Equivalently: maximise per-user tokens/s per mm2 over the feasible "
    "set. The two statements are the same rule -- accepting when "
    "(r - r0) / (a - a0) >= r0 / a0 is exactly r / a >= r0 / a0 -- and the "
    "marginal form is the one to read, because it is the engineering question: "
    "does the next slab of silicon work at least as hard as the slab you have?"
)

SELECTION_METRIC_RATIONALE = (
    "Ranking on per-user tokens/s alone hands an 8B model a 46,225 mm2 wafer, "
    "because a per-user rate has no area in it and a wafer is always at least as "
    "fast as anything cut out of it -- on Qwen3-8B that is 2.33x the rate of the "
    "three 815 mm2 reticles that hold the same checkpoint, bought with 18.9x the "
    "silicon and an eighth of the throughput density. Ranking on silicon area "
    "alone picks the smallest machine that "
    "physically holds the checkpoint, whatever it delivers. A 5%-of-peak "
    "tolerance does not fix the first: it is a tie-break among near-peak designs "
    "and is orthogonal to area, so it shrinks the machine only in the cases "
    "nobody was worried about. The domination filter plus the marginal-return "
    "walk fixes both, needs no latency target to be stated, and -- because the "
    "filter is on (per-user rate, rate per mm2) -- makes it structurally "
    "impossible to recommend a design that another feasible design of the same "
    "model beats on both axes at once."
)


def _selection_density(row: dict[str, Any]) -> float:
    """Per-user tokens/s per 1,000 mm2 of silicon."""

    area = row["silicon_area_mm2"]
    return row["per_user_tokens_s"] / area * 1000.0 if area > 0 else 0.0


def _selection_candidates(
    points: list[dict[str, Any]], model_name: str, batch: int
) -> list[dict[str, Any]]:
    return [
        row
        for row in points
        if row["family"] == "rom"
        and row["model"] == model_name
        and row["batch_size"] == batch
        and row["weight_amortization"] == SELECTION_AMORTIZATION
        and row["feasible"]
        and row["per_user_tokens_s"] > 0
        and row["silicon_area_mm2"] > 0
    ]


def _design_frontier(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Designs no other feasible design beats on BOTH axes at once.

    This is the property the recommendation has to have and the one whose
    absence let a wafer be published as the answer for an 8B model, so it is a
    filter and not a report: the walk below can only ever choose from this set.
    """

    scored = [(row["per_user_tokens_s"], _selection_density(row), row) for row in rows]
    kept: list[tuple[float, float, dict[str, Any]]] = []
    for rate, density, row in scored:
        dominated = False
        for other_rate, other_density, other in scored:
            if other is row:
                continue
            if (
                other_rate >= rate * (1.0 - 1e-12)
                and other_density >= density * (1.0 - 1e-12)
                and (
                    other_rate > rate * (1.0 + 1e-12)
                    or other_density > density * (1.0 + 1e-12)
                )
            ):
                dominated = True
                break
        if not dominated:
            kept.append((rate, density, row))
    # Exact ties -- the same rate on the same silicon under two design labels --
    # collapse to one row, chosen by name so the artifact is deterministic.
    unique: dict[tuple[float, float], dict[str, Any]] = {}
    for rate, density, row in kept:
        key = (round(rate, 6), round(density, 9))
        current = unique.get(key)
        if current is None or row["design"] < current["design"]:
            unique[key] = row
    return sorted(
        unique.values(),
        key=lambda row: (
            row["silicon_area_mm2"],
            -row["per_user_tokens_s"],
            row["design"],
        ),
    )


def _marginal_return_walk(frontier: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The walk, with its arithmetic recorded rung by rung.

    Returned as a ladder rather than a winner so the report can show the reader
    the number that stopped it.  The last accepted rung is the recommendation.
    """

    ladder: list[dict[str, Any]] = []
    if not frontier:
        return ladder
    incumbent = frontier[0]
    ladder.append(
        {
            "design": incumbent["design"],
            "silicon_area_mm2": incumbent["silicon_area_mm2"],
            "per_user_tokens_s": incumbent["per_user_tokens_s"],
            "tokens_s_per_1000mm2": _selection_density(incumbent),
            "marginal_tokens_s_per_1000mm2": None,
            "incumbent_average_tokens_s_per_1000mm2": _selection_density(incumbent),
            "verdict": "start: the smallest feasible machine",
            "accepted": True,
        }
    )
    for row in frontier[1:]:
        delta_area = row["silicon_area_mm2"] - incumbent["silicon_area_mm2"]
        if delta_area <= 0:
            continue
        marginal = (
            (row["per_user_tokens_s"] - incumbent["per_user_tokens_s"])
            / delta_area
            * 1000.0
        )
        average = _selection_density(incumbent)
        accepted = marginal > average * MARGINAL_RETURN_BAR * (1.0 + 1e-12)
        ladder.append(
            {
                "design": row["design"],
                "silicon_area_mm2": row["silicon_area_mm2"],
                "per_user_tokens_s": row["per_user_tokens_s"],
                "tokens_s_per_1000mm2": _selection_density(row),
                "marginal_tokens_s_per_1000mm2": marginal,
                "incumbent_average_tokens_s_per_1000mm2": average,
                "verdict": (
                    "accepted: the added silicon works harder than the silicon "
                    "already bought"
                    if accepted
                    else "rejected: the added silicon works less hard than the "
                    "silicon already bought"
                ),
                "accepted": accepted,
            }
        )
        if accepted:
            incumbent = row
    return ladder


def _selection_row(
    row: dict[str, Any], comparison: dict[str, Any] | None
) -> dict[str, Any]:
    """One published row: the whole tuple, never a single number.

    Every one of these fields is load-bearing somewhere in the argument, and
    publishing the per-user rate without the resident-session count beside it is
    how a one-session latency device gets read as a server.
    """

    record = {
        "design": row["design"],
        "silicon_area_mm2": row["silicon_area_mm2"],
        "silicon_area_mm2_per_device": row["silicon_area_mm2_per_device"],
        "device_count": row["device_count"],
        "topology_kind": row["topology_kind"],
        "parallelism": row["parallelism"],
        "kv_store": row["kv_store"],
        "spare_area_policy": row["spare_area_policy"],
        "per_user_tokens_s": row["per_user_tokens_s"],
        "aggregate_tokens_s": row["aggregate_tokens_s"],
        "delivered_tokens_s": row["delivered_tokens_s"],
        "tokens_s_per_1000mm2": _selection_density(row),
        "aggregate_tokens_s_per_1000mm2": (
            row["aggregate_tokens_s"] / row["silicon_area_mm2"] * 1000.0
        ),
        "max_resident_users": row["max_resident_users"],
        "pipeline_fill_users": row["pipeline_fill_users"],
        "pipeline_fill_limited_by": row["pipeline_fill_limited_by"],
        "binding_constraint": row["binding_constraint"],
        "power_w": row["power_w"],
        "power_density_w_per_mm2": row["power_density_w_per_mm2"],
        "energy_j_per_token": row["energy_j_per_token"],
        "thermal_scale": row["thermal_scale"],
        "rom_replication_factor": row["rom_replication_factor"],
    }
    if comparison is not None:
        record.update(
            {
                "iso_area_gpu_design": comparison["iso_area_gpu_design"],
                "iso_area_gpu_device_count": comparison["iso_area_gpu_device_count"],
                "iso_area_gpu_silicon_area_mm2": comparison[
                    "iso_area_gpu_silicon_area_mm2"
                ],
                "iso_area_ratio": comparison["iso_area_ratio"],
                "iso_area_gpu_feasible": comparison["iso_area_gpu_feasible"],
                "iso_area_gpu_parallelism": comparison["iso_area_gpu_parallelism"],
                "iso_area_gpu_per_user_tokens_s": comparison[
                    "iso_area_gpu_per_user_tokens_s"
                ],
                "iso_area_gpu_aggregate_tokens_s": comparison[
                    "iso_area_gpu_aggregate_tokens_s"
                ],
                "iso_area_gpu_max_resident_users": comparison[
                    "iso_area_gpu_max_resident_users"
                ],
                "iso_area_gpu_energy_j_per_token": comparison[
                    "iso_area_gpu_energy_j_per_token"
                ],
                "per_user_speed_ratio": comparison["per_user_speed_ratio"],
                "aggregate_speed_ratio": comparison["aggregate_speed_ratio"],
                "tokens_per_joule_advantage_x": comparison[
                    "tokens_per_joule_advantage_x"
                ],
                "fastest_feasible_gpu_design": comparison[
                    "fastest_feasible_gpu_design"
                ],
                "fastest_feasible_gpu_silicon_area_mm2": comparison[
                    "fastest_feasible_gpu_silicon_area_mm2"
                ],
                "fastest_feasible_gpu_per_user_tokens_s": comparison[
                    "fastest_feasible_gpu_per_user_tokens_s"
                ],
            }
        )
    return record


ISO_AREA_MATCH_TOLERANCE = 0.05
"""An array counts as "at the wafer's area" within this fraction of it."""


def _iso_area_by_batch(
    points: list[dict[str, Any]],
    comparisons: dict[tuple[str, int], dict[str, Any]],
    model_name: str,
) -> list[dict[str, Any]]:
    """The three classes read at iso-area, batch by batch.

    For every batch the study evaluates, each ROM class (reticle array, wafer)
    enters at its own optimum -- its fastest feasible design and its densest --
    and each is paired with the GPU comparator at *its own* silicon area, which
    is the ``iso_area_gpu_*`` row the comparison table already carries for that
    design and batch.  A third row reads the array at the wafer's area: the
    fastest array design whose silicon is within ``ISO_AREA_MATCH_TOLERANCE``
    of the fastest wafer's, which exists because the array ladder samples the
    device counts whose silicon equals each wafer rung.

    Resident sessions, power and energy ride on every row, because a per-user
    rate divided by a per-user rate is a latency claim and a latency claim from
    a one-session machine against a thousand-session machine is not the trade
    it looks like.
    """

    rows: list[dict[str, Any]] = []
    for batch in BATCHES:
        candidates = _selection_candidates(points, model_name, batch)
        record: dict[str, Any] = {"batch_size": batch, "classes": []}
        by_kind: dict[str, list[dict[str, Any]]] = {}
        for row in candidates:
            by_kind.setdefault(row["topology_kind"], []).append(row)
        for kind in ("array", "wafer"):
            in_class = by_kind.get(kind, [])
            if not in_class:
                continue
            fastest = max(
                in_class,
                key=lambda row: (row["per_user_tokens_s"], -row["silicon_area_mm2"]),
            )
            densest = max(
                in_class,
                key=lambda row: (_selection_density(row), -row["silicon_area_mm2"]),
            )
            record["classes"].append(
                {
                    "topology_kind": kind,
                    "designs_evaluated": len(in_class),
                    "fastest": _selection_row(
                        fastest, comparisons.get((fastest["design"], batch))
                    ),
                    "densest": _selection_row(
                        densest, comparisons.get((densest["design"], batch))
                    ),
                }
            )
        wafers = by_kind.get("wafer", [])
        arrays = by_kind.get("array", [])
        record["array_at_wafer_area"] = None
        if wafers and arrays:
            wafer = max(
                wafers,
                key=lambda row: (row["per_user_tokens_s"], -row["silicon_area_mm2"]),
            )
            target = wafer["silicon_area_mm2"]
            matched = [
                row
                for row in arrays
                if abs(row["silicon_area_mm2"] - target) <= ISO_AREA_MATCH_TOLERANCE * target
            ]
            if matched:
                best = max(
                    matched,
                    key=lambda row: (row["per_user_tokens_s"], -row["silicon_area_mm2"]),
                )
                paired = _selection_row(best, comparisons.get((best["design"], batch)))
                paired["wafer_reference_design"] = wafer["design"]
                paired["wafer_reference_silicon_area_mm2"] = target
                paired["wafer_reference_per_user_tokens_s"] = wafer["per_user_tokens_s"]
                paired["wafer_reference_max_resident_users"] = wafer["max_resident_users"]
                paired["wafer_reference_energy_j_per_token"] = wafer["energy_j_per_token"]
                paired["area_ratio_to_wafer"] = best["silicon_area_mm2"] / target
                paired["per_user_ratio_wafer_over_array"] = (
                    wafer["per_user_tokens_s"] / best["per_user_tokens_s"]
                    if best["per_user_tokens_s"] > 0
                    else None
                )
                paired["resident_sessions_ratio_array_over_wafer"] = (
                    best["max_resident_users"] / wafer["max_resident_users"]
                    if wafer["max_resident_users"]
                    else None
                )
                record["array_at_wafer_area"] = paired
        rows.append(record)
    return rows


def _model_order(result: dict[str, Any]) -> dict[str, int]:
    """Report order of the models in ONE study's result.

    The primary studies list their models in ``STUDY_MODELS`` order, so this is
    that order for them to the byte.  A single-model tree -- a context-ladder
    rung, a candidate model -- lists its own model, which ``STUDY_MODELS`` may
    not know; ordering by the result's own summaries is what lets the same
    renderer serve both without a candidate being refused at the report stage.
    """

    order = {
        str(summary["model"]): index
        for index, summary in enumerate(result.get("model_summaries", ()))
    }
    for name, _path, _context in STUDY_MODELS:
        order.setdefault(name, len(order))
    return order


def _design_selection(
    result: dict[str, Any], study_models: tuple[tuple[str, Path, int], ...]
) -> dict[str, Any]:
    """Pick, and publish, one design per model -- and the curve it sits on.

    The previous rule is evaluated beside the new one on the same data, so the
    report can state the headline before and after without either being retyped.
    """

    points = result["points"]
    comparisons = {
        (row["rom_design"], row["batch_size"]): row for row in result["comparisons"]
    }
    models: list[dict[str, Any]] = []
    for model_name, _path, context in study_models:
        per_batch: list[dict[str, Any]] = []
        headline: dict[str, Any] | None = None
        frontier_rows: list[dict[str, Any]] = []
        walk: list[dict[str, Any]] = []
        for batch in BATCHES:
            rows = _selection_candidates(points, model_name, batch)
            frontier = _design_frontier(rows)
            ladder = _marginal_return_walk(frontier)
            accepted = [rung for rung in ladder if rung["accepted"]]
            chosen_id = accepted[-1]["design"] if accepted else None
            chosen = next(
                (row for row in frontier if row["design"] == chosen_id), None
            )
            record: dict[str, Any] = {
                "batch_size": batch,
                "feasible_designs": len(rows),
                "frontier_size": len(frontier),
            }
            if chosen is None:
                record["recommended"] = None
                record["reason"] = "no feasible ROM design at this batch"
            else:
                record["recommended"] = _selection_row(
                    chosen, comparisons.get((chosen["design"], batch))
                )
            per_batch.append(record)
            if batch == 1 and chosen is not None:
                headline = record["recommended"]
                frontier_rows = [
                    _selection_row(row, comparisons.get((row["design"], batch)))
                    for row in frontier
                ]
                walk = ladder

        # What ranking on per-user rate alone buys, at batch 1, so the cost of
        # the rejected rule is a number in the artifact rather than an assertion.
        batch_one = _selection_candidates(points, model_name, 1)
        fastest = (
            max(batch_one, key=lambda row: (row["per_user_tokens_s"], -row["silicon_area_mm2"]))
            if batch_one
            else None
        )
        previous = (
            _pick_best(batch_one, "per_user_tokens_s", "silicon_area_mm2")
            if batch_one
            else None
        )
        smallest = (
            min(batch_one, key=lambda row: (row["silicon_area_mm2"], -row["per_user_tokens_s"]))
            if batch_one
            else None
        )

        # A frontier can honestly be one row -- when one design wins on both
        # axes at once there is no trade to report -- and a one-row table tells
        # the reader nothing about what it beat.  The class contrast is
        # published beside it so "array or wafer" is answered with the losing
        # class's own best machine on the page, not by its absence from it.
        class_comparison: list[dict[str, Any]] = []
        for kind in ("array", "wafer"):
            in_class = [row for row in batch_one if row["topology_kind"] == kind]
            if not in_class:
                continue
            densest = max(
                in_class,
                key=lambda row: (_selection_density(row), -row["silicon_area_mm2"]),
            )
            fastest_in_class = max(
                in_class,
                key=lambda row: (row["per_user_tokens_s"], -row["silicon_area_mm2"]),
            )
            smallest_in_class = min(
                in_class,
                key=lambda row: (row["silicon_area_mm2"], -row["per_user_tokens_s"]),
            )
            class_comparison.append(
                {
                    "topology_kind": kind,
                    "designs_evaluated": len(in_class),
                    "best_by_throughput_density": _selection_row(
                        densest, comparisons.get((densest["design"], 1))
                    ),
                    "best_by_per_user_rate": _selection_row(
                        fastest_in_class,
                        comparisons.get((fastest_in_class["design"], 1)),
                    ),
                    "smallest_feasible": _selection_row(
                        smallest_in_class,
                        comparisons.get((smallest_in_class["design"], 1)),
                    ),
                }
            )

        regimes: list[dict[str, Any]] = []
        for record in per_batch:
            design = (
                record["recommended"]["design"] if record["recommended"] else None
            )
            if regimes and regimes[-1]["design"] == design:
                regimes[-1]["batches"].append(record["batch_size"])
                continue
            regimes.append(
                {
                    "design": design,
                    "batches": [record["batch_size"]],
                    "silicon_area_mm2": (
                        record["recommended"]["silicon_area_mm2"]
                        if record["recommended"]
                        else None
                    ),
                    "topology_kind": (
                        record["recommended"]["topology_kind"]
                        if record["recommended"]
                        else None
                    ),
                    "kv_store": (
                        record["recommended"]["kv_store"]
                        if record["recommended"]
                        else None
                    ),
                    "max_resident_users": (
                        record["recommended"]["max_resident_users"]
                        if record["recommended"]
                        else None
                    ),
                }
            )

        models.append(
            {
                "model": model_name,
                "context_tokens": context,
                "recommended": headline,
                "marginal_return_walk": walk,
                "frontier_batch_1": frontier_rows,
                "batch_regimes": per_batch,
                "regimes": regimes,
                "regime_count": len(regimes),
                "best_design_differs_by_batch": len(regimes) > 1,
                "class_comparison": class_comparison,
                "iso_area_by_batch": _iso_area_by_batch(
                    points, comparisons, model_name
                ),
                "rejected_per_user_maximum": (
                    _selection_row(fastest, comparisons.get((fastest["design"], 1)))
                    if fastest
                    else None
                ),
                "rejected_smallest_feasible": (
                    _selection_row(smallest, comparisons.get((smallest["design"], 1)))
                    if smallest
                    else None
                ),
                "previous_rule_choice": (
                    _selection_row(previous, comparisons.get((previous["design"], 1)))
                    if previous
                    else None
                ),
            }
        )

    return {
        "metric": SELECTION_METRIC,
        "why_this_metric": SELECTION_METRIC_RATIONALE,
        "marginal_return_bar": MARGINAL_RETURN_BAR,
        "amortisation_scope": SELECTION_AMORTIZATION,
        "previous_rule": (
            "smallest silicon within "
            f"{BEST_DESIGN_TOLERANCE:.0%} of the best per-user rate "
            "(BEST_DESIGN_TOLERANCE), retained here only so the before/after is "
            "computed rather than asserted"
        ),
        "iso_area_convention": (
            "The GPU comparator at each ROM area is N copies of one unified HBM "
            "die, N chosen so the silicon matches, and the cluster is allowed to "
            "pick its own parallelism. The comparison is read at the ROM side's "
            "CHOSEN area, not at a fixed rung of the area ladder where both "
            "sides are past their own optimum."
        ),
        "models": models,
    }


def _simulate_study(
    study_id: str,
    technology: Technology,
    *,
    with_sensitivity: bool = True,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = STUDIES[study_id] if config is None else config
    # A study may narrow the model list and may name its own stored
    # representation.  The two primary studies do neither, so they are
    # unaffected to the byte; the quantised variant does both, which is how it
    # stays a separate artifact instead of extra rows in this one.
    study_models: tuple[tuple[str, Path, int], ...] = tuple(
        config.get("models", STUDY_MODELS)
    )
    representation_override = config.get("representation")
    node = str(config["rom_node"])
    # The ROM bit-cell ratio is a per-node quantity and this study runs at one
    # node.  Substituted here, before ANY term is derived, so that the whole
    # artifact -- densities, designs, sweeps, sensitivities -- is priced at one
    # ratio.  Refuses a node it has no entry for.
    technology = _node_technology(technology, node)
    hbm_generation = str(config["hbm_generation"])
    reticle_area = technology.graded("reticle", "area_mm2").value
    wafer_area = technology.graded("wafer", "area_mm2").value
    fabric_plans = _fabric_plans(
        technology, config, wafer_area=wafer_area, reticle_area=reticle_area
    )
    gpu_plans = tuple(
        plan
        for plan, _area in fabric_plans
        if plan.kind == "array" and not plan.label.startswith("array-hw-")
    )
    # **The HBM side at its best shipping fabric.**  A general-purpose HBM
    # accelerator keeps NVLink: the largest shipping domain (GB200 NVL72, where
    # the study's part generation has one) is added to the 8-GPU baseboard.
    # Specialised hardware links are a property of the model-specific ROM
    # machine and are not given to the general-purpose baseline.
    extra_gpu_fabrics = []
    if config.get("gpu_best_intra_link"):
        extra_gpu_fabrics.append(
            ("nvl72", str(config["gpu_best_intra_link"]), str(config["inter_link"]))
        )
    for tag, intra_name, inter_name in extra_gpu_fabrics:
        domain = max(1, int(technology.link_domain_size(intra_name).value))
        gpu_plans = gpu_plans + tuple(
            FabricPlan(
                kind="array",
                parallelism=parallelism,
                intra_link=intra_name,
                inter_link=inter_name,
                intra_domain_size=domain,
                label=f"array-{tag}-{parallelism}",
            )
            for parallelism in ("tensor", "hybrid")
        )
    domain_sensitivity_link = config.get("gpu_domain_sensitivity")
    domain_sensitivity: list[dict[str, Any]] = []

    points: list[dict[str, Any]] = []
    designs: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    crossovers: list[dict[str, Any]] = []
    model_summaries: list[dict[str, Any]] = []

    for model_name, model_path, context in study_models:
        model = ModelProfile.load(model_path)
        model_technology = _model_technology(technology, model.name)
        kv = kv_traffic(model, context)
        model_summaries.append(
            {
                "model": model.name,
                "source_repo": model.source_repo,
                "source_revision": model.source_revision,
                "context_tokens": context,
                "num_layers": model.num_layers,
                "hidden_size": model.hidden_size,
                "total_parameters": model.total_parameters,
                "active_parameters": model.active_parameters,
                "checkpoint_bytes": model.checkpoint_bytes,
                "native_bits_per_parameter": (
                    model.checkpoint_bytes / model.total_parameters * 8.0
                ),
                "kv_read_bytes_per_user_token": kv.read_bytes,
                "kv_write_bytes_per_user_token": kv.write_bytes,
                "kv_storage_bytes_per_user": kv.storage_bytes_per_user,
                "weight_to_kv_read_ratio_b1": (
                    model.dense_weight_bytes
                    + model.routed_weight_bytes * model.routed_fraction_per_token
                )
                / kv.read_bytes,
                "num_experts": model.num_experts,
                "experts_per_token": model.experts_per_token,
                "compressed_sparse_layers": sum(
                    group.count
                    for group in model.attention_groups
                    if group.kind == "compressed_sparse"
                ),
                "layer_fixed_latency": layer_fixed_latency(model_technology, model)[1],
                "per_region_sizing": _per_region_sizing(model_technology, model, node),
            }
        )

        for representation, bits in (
            (representation_override,)
            if representation_override
            else _representations(model)
        ):
            stored = _rom_stored_bytes(model, bits)
            execution = _execution_format(model_technology, bits, model)
            for kv_store in ("sram", "hbm"):
                provision_batch = (
                    DESIGN_BATCH if kv_store == "sram" else PROVISION_BATCH
                )
                # The KV store has to hold the provisioning batch's KV *and*
                # any region the model declares resident in that same store, so
                # both size it: stacks on an HBM design, array area on an SRAM
                # one.  This is the identity for every model that declares no
                # such region, and it is what stops an Engram-in-HBM design from
                # being sized for KV alone and then refused for capacity.
                design_batch_kv = (
                    kv.storage_bytes_per_user * provision_batch
                    + hbm_resident_weight_bytes(model)
                )
                design_batch_kv_transfer = (
                    kv.read_bytes + kv.write_bytes
                ) * provision_batch
                for amortization, spare_area_policy in (
                    (policy, spare)
                    for policy in WEIGHT_AMORTIZATIONS
                    # Where a compute-in-ROM design spends the silicon it
                    # recovers from the MAC array is a design choice, so both
                    # answers are emitted and the comparison picks between
                    # them.  The amortising machine has no spare area by
                    # definition -- the remainder IS its MAC array -- so it has
                    # only one floorplan.
                    for spare in SPARE_AREA_POLICIES
                ):
                    # **Size every parallelism first, then emit every
                    # parallelism at every size any of them chose.**  Sizing and
                    # emitting in one pass means a topology only exists at the
                    # silicon area its own sweep happened to pick, so an
                    # iso-area row can end up comparing the only design that
                    # exists at that area rather than the best one -- which is
                    # the same defect as letting one side pick its topology,
                    # arrived at through the sizing rule instead.
                    sized: dict[str, tuple[int, list[dict[str, Any]]]] = {}
                    for plan, area_per_device in fabric_plans:
                        devices, sweep = _size_array(
                            model_technology,
                            model,
                            node=node,
                            area_per_device=area_per_device,
                            stored_weight_bytes=stored,
                            resident_kv_bytes=design_batch_kv,
                            kv_transfer_bytes=design_batch_kv_transfer,
                            kv_store=kv_store,
                            hbm_generation=hbm_generation,
                            context_tokens=context,
                            execution_format=execution,
                            weight_bits=bits,
                            plan=plan,
                            wafer_area=wafer_area if plan.kind == "wafer" else None,
                            reticle_area=(
                                reticle_area if plan.kind == "wafer" else None
                            ),
                            weight_amortization=amortization,
                            spare_area_policy=spare_area_policy,
                        )
                        sized[plan.label] = (devices, sweep)
                    counts_by_kind: dict[str, set[int]] = {}
                    for plan, _area in fabric_plans:
                        devices, plan_sweep = sized[plan.label]
                        if devices > ARRAY_SWEEP_CAP:
                            continue
                        if amortization != "batched":
                            # Only the batched machine enters the iso-area
                            # comparison, so only it needs every topology at
                            # every sized area; the other two policies are read
                            # from the fork table at their own sizing point.
                            counts_by_kind.setdefault(plan.kind, set()).add(devices)
                            continue
                        floor = (
                            plan_sweep[0]["device_count"] if plan_sweep else devices
                        )
                        bucket = counts_by_kind.setdefault(plan.kind, set())
                        bucket.add(devices)
                        # The ladder is anchored at the smallest machine that
                        # physically holds the design, not at the one the
                        # latency sweep preferred, so the area grid does not
                        # move when a latency assumption moves.
                        if plan.kind == "wafer" and amortization == "batched":
                            bucket.update(
                                count for count in ROM_AREA_LADDER if count >= floor
                            )
                        if plan.kind == "array" and amortization == "batched":
                            bucket.update(
                                _array_device_ladder(
                                    floor,
                                    wafer_area=wafer_area,
                                    reticle_area=reticle_area,
                                )
                            )
                    for plan, area_per_device in fabric_plans:
                        topology_name = plan.label
                        kind = plan.kind
                        parallelism = plan.parallelism
                        chosen, sweep = sized[plan.label]
                        if chosen > ARRAY_SWEEP_CAP:
                            continue
                        # The floor is the smallest count that physically holds
                        # the design, not the count this plan's own latency
                        # sweep preferred -- otherwise a topology is absent from
                        # an area only because a different topology's sweep
                        # liked a slightly different machine.
                        minimum = sweep[0]["device_count"] if sweep else chosen
                        suffix = {
                            "batched": "",
                            "per_stream": "-perstream",
                            "per_region": "-perregion",
                        }[amortization]
                        if spare_area_policy == "rom":
                            suffix += "-romfill"
                        for devices in sorted(counts_by_kind.get(kind, ())):
                            if devices < minimum:
                                # Below this the design does not physically
                                # hold the model.
                                continue
                            regions = _regions_for(
                                plan,
                                devices,
                                wafer_area if kind == "wafer" else None,
                                reticle_area if kind == "wafer" else None,
                            )
                            # A machine with one partition has no
                            # inter-partition event at all, so every parallelism
                            # collapses onto the same design and only the
                            # pipeline label is emitted.  A hybrid whose tensor
                            # group covers every partition it has is a pure
                            # tensor machine under another name, and one whose
                            # group is a single partition is a pure pipeline;
                            # neither is emitted twice.
                            probe = plan.topology(devices, regions)
                            if parallelism != "pipeline" and probe.partitions <= 1:
                                continue
                            if parallelism == "hybrid" and (
                                probe.tensor_group <= 1
                                or probe.tensor_group >= probe.partitions
                            ):
                                continue
                            _emit_rom_design(
                                model_technology,
                                model,
                                designs=designs,
                                points=points,
                                crossovers=crossovers,
                                node=node,
                                representation=representation,
                                bits=bits,
                                execution=execution,
                                kv_store=kv_store,
                                topology_name=topology_name,
                                suffix=suffix,
                                plan=plan,
                                area_per_device=area_per_device,
                                devices=devices,
                                regions=regions,
                                stored=stored,
                                design_batch_kv=design_batch_kv,
                                design_batch_kv_transfer=design_batch_kv_transfer,
                                hbm_generation=hbm_generation,
                                amortization=amortization,
                                spare_area_policy=spare_area_policy,
                                context=context,
                                sweep=sweep if devices == chosen else [],
                                sized=devices == chosen,
                            )

        # --- iso-area GPU baselines --------------------------------------
        rom_areas = sorted(
            {
                round(row["silicon_area_mm2"], 6)
                for row in points
                if row["model"] == model.name and row["family"] == "rom"
            }
        )
        for part in config["gpu_parts"]:
            # No execution-format override for a GPU: the part's own
            # native/emulated table decides what it can run, so A100's lack of
            # an FP8 unit shows up as BF16 emulation rather than as a study knob.
            counts: dict[int, str] = {}
            for area in rom_areas:
                counts.setdefault(
                    _iso_area_gpu_counts(model_technology, part, area),
                    f"iso-area with {area:,.0f} mm2 of ROM silicon",
                )
            # A fixed area ladder, independent of which ROM design the sizing
            # sweep happens to pick.  Without it the GPU curve is only sampled
            # where a ROM design exists, so a correction that makes the ROM
            # side prefer smaller machines silently truncates the GPU curve
            # too -- and the question "does the GPU still get slower as it is
            # given more silicon" then cannot be asked at the areas where the
            # previous answer was published.
            for wafers in GPU_AREA_LADDER:
                area = wafer_area * wafers
                counts.setdefault(
                    _iso_area_gpu_counts(model_technology, part, area),
                    f"area ladder: {wafers} wafer-equivalent"
                    f"{'s' if wafers > 1 else ''} of silicon ({area:,.0f} mm2)",
                )
            # **Whatever the ROM side is priced at, the GPU is priced at.**  A
            # quantisation is a property of the checkpoint, not of the machine
            # reading it: a GPU serving 4.25-bit weights reads 3.8x fewer weight
            # bytes too, and a study that gave the saving to one side would be
            # the exact asymmetry the released-packing rule exists to forbid.
            gpu_bits = (
                float(representation_override[1])
                if representation_override
                and representation_override[1] is not None
                else None
            )
            gpu_representation = (
                str(representation_override[0])
                if representation_override
                else "official_packed"
            )
            gpu_execution = (
                _execution_format(model_technology, gpu_bits, model)
                if gpu_bits is not None
                else None
            )
            gpu_stored_bytes = _rom_stored_bytes(model, gpu_bits)
            minimum = _minimum_gpu_count(
                model_technology,
                part,
                stored_weight_bytes=gpu_stored_bytes,
                # A GPU has one store, so a region the model declares resident
                # in the KV store is HBM the cluster must also buy.  Without
                # this the "smallest cluster whose HBM holds the checkpoint plus
                # the KV" would be a cluster that does not hold the tables.
                resident_kv_bytes=kv.storage_bytes_per_user * PROVISION_BATCH
                + hbm_resident_weight_bytes(model),
            )
            counts.setdefault(
                minimum,
                "smallest cluster whose HBM holds the checkpoint plus the "
                f"batch-{PROVISION_BATCH} KV",
            )
            for count, rationale in sorted(counts.items()):
                # **The GPU gets the same topology sweep the ROM side gets.**
                # It previously got one: pipeline, at every cluster size, which
                # charged a 672-GPU deployment 671 serial hops per token at
                # batch 1 and reported the resulting collapse as a property of
                # GPUs.  No such deployment exists.  Every parallelism the ROM
                # side may choose is now offered here too, priced on the same
                # two-tier fabric, and the comparison takes the best.
                if count == 1:
                    plans_here: tuple[FabricPlan, ...] = (
                        FabricPlan(
                            kind="single_chip",
                            parallelism="none",
                            intra_link="none",
                            inter_link="none",
                            intra_domain_size=1,
                            label="single",
                        ),
                    )
                else:
                    plans_here = gpu_plans
                    if (model.num_experts or 1) > 1 and gpu_plans:
                        # **Expert parallelism, the layout DeepSeek actually
                        # serves on GPUs** (framework review finding 7): attention
                        # tensor-parallel inside one NVLink domain and replicated
                        # per domain, experts sharded over every device and
                        # reached by dispatch/combine.  Offered to the GPU only:
                        # replicating or concentrating dense weights in mask ROM
                        # needs a non-uniform floorplan this model does not
                        # build, so the ROM side keeps its three layouts and the
                        # asymmetry favours the GPU.
                        fabrics = {}
                        for plan in gpu_plans:
                            fabrics.setdefault(
                                (plan.intra_link, plan.inter_link),
                                (plan.label.rsplit("-", 1)[0], plan.intra_domain_size),
                            )
                        plans_here = gpu_plans + tuple(
                            FabricPlan(
                                kind="array",
                                parallelism="expert",
                                intra_link=intra_name,
                                inter_link=inter_name,
                                intra_domain_size=domain,
                                label=f"{prefix}-expert",
                                moe_fanout=int(model.experts_per_token or 1),
                            )
                            for (intra_name, inter_name), (prefix, domain) in fabrics.items()
                        )
                for plan in plans_here:
                    topology = plan.topology(count, 1)
                    if plan.parallelism == "hybrid" and (
                        topology.tensor_group <= 1
                        or topology.tensor_group >= topology.partitions
                    ):
                        continue
                    suffix = (
                        ""
                        if count == 1
                        else f"-{plan.label.removeprefix('array-')}"
                    )
                    design_id = f"{_model_tag(model)}/{part}-x{count}{suffix}"
                    budget = gpu_device_budget(
                        model_technology, part=part, topology=topology, name=design_id
                    )
                    designs.append(
                        {
                            "design": design_id,
                            "family": "gpu",
                            "model": model.name,
                            "representation": gpu_representation,
                            "stored_bits_per_parameter": (
                                gpu_bits
                                if gpu_bits is not None
                                else model.checkpoint_bytes
                                / model.total_parameters
                                * 8.0
                            ),
                            "execution_format": (
                                (
                                    f"{gpu_execution} "
                                    + (
                                        "native"
                                        if gpu_execution in budget.native_formats
                                        else "emulated to "
                                        + budget.emulated_formats.get(
                                            gpu_execution, "?"
                                        )
                                    )
                                )
                                if gpu_execution is not None
                                else "native where available, else "
                                + ", ".join(
                                    f"{src}->{dst}"
                                    for src, dst in sorted(
                                        budget.emulated_formats.items()
                                    )
                                )
                                or "native"
                            ),
                            "topology": f"cluster-{plan.parallelism}",
                            "sizing_rule": rationale,
                            "device_count_sweep": [],
                            **budget.to_dict(),
                        }
                    )
                    if count > 1:
                        crossovers.append(
                            _crossover_row(design_id, model, topology, model_technology)
                        )
                    for batch in BATCHES:
                        step = evaluate(
                            budget,
                            model,
                            context_tokens=context,
                            batch_size=batch,
                            technology=model_technology,
                            weight_bits_per_parameter=gpu_bits,
                            execution_format=gpu_execution,
                            prompt_tokens=context if batch == 1 else None,
                        )
                        points.append(
                            _step_row(
                                step,
                                budget,
                                family="gpu",
                                design_id=design_id,
                                model=model,
                            )
                        )
                        # What the same cluster costs on the larger NVLink
                        # domain the vendor also ships.  The part this study
                        # prices is an SXM module on an eight-GPU baseboard, so
                        # eight is the value; 72 is a published fact about a
                        # different product and is reported rather than
                        # borrowed.
                        if (
                            domain_sensitivity_link
                            and batch == 1
                            and step.feasible
                            and math.isfinite(step.step_time_s)
                        ):
                            wide = replace(
                                topology,
                                intra_link=domain_sensitivity_link,
                                intra_domain_size=max(
                                    1,
                                    int(
                                        model_technology.link_domain_size(
                                            domain_sensitivity_link
                                        ).value
                                    ),
                                ),
                                tensor_group_size=(
                                    max(
                                        1,
                                        int(
                                            model_technology.link_domain_size(
                                                domain_sensitivity_link
                                            ).value
                                        ),
                                    )
                                    if plan.parallelism == "hybrid"
                                    else topology.tensor_group_size
                                ),
                            )
                            wide_link, _detail, _payload = model_technology.link_time_s(
                                wide,
                                model.num_layers,
                                activation_bytes=(
                                    batch * model.hidden_size * 2.0
                                ),
                            )
                            wide_step = (
                                step.step_time_s
                                - step.component_times_s["link_latency"]
                                + wide_link
                            )
                            domain_sensitivity.append(
                                {
                                    "design": design_id,
                                    "model": model.name,
                                    "device_count": count,
                                    "parallelism": plan.parallelism,
                                    "silicon_area_mm2": step.silicon_area_mm2,
                                    "domain_size": topology.intra_domain_size,
                                    "wide_domain_link": domain_sensitivity_link,
                                    "wide_domain_size": wide.intra_domain_size,
                                    "link_latency_s": step.component_times_s[
                                        "link_latency"
                                    ],
                                    "wide_domain_link_latency_s": wide_link,
                                    "per_user_tokens_s": step.per_user_tokens_s,
                                    "wide_domain_per_user_tokens_s": (
                                        1.0 / wide_step if wide_step > 0 else None
                                    ),
                                }
                            )

    # --- iso-area comparisons -------------------------------------------
    gpu_rows = [row for row in points if row["family"] == "gpu"]
    for row in points:
        if row["family"] != "rom" or row["weight_amortization"] != "batched":
            continue
        candidates = [
            gpu
            for gpu in gpu_rows
            if gpu["model"] == row["model"] and gpu["batch_size"] == row["batch_size"]
        ]
        if not candidates:
            continue
        # **The GPU is allowed to pick its topology, exactly as the ROM side
        # is.**  Selecting on area alone and then reading off whichever
        # parallelism happened to be first is how the comparison came to charge
        # the GPU a 672-way pipeline while the ROM ran tensor-parallel at the
        # same area.  Among the clusters closest in area, the fastest feasible
        # one is the comparator; the pipeline-only figure is carried beside it
        # so the size of the previous error stays visible.
        closest = min(
            abs(gpu["silicon_area_mm2"] - row["silicon_area_mm2"])
            for gpu in candidates
        )
        at_area = [
            gpu
            for gpu in candidates
            if abs(gpu["silicon_area_mm2"] - row["silicon_area_mm2"])
            <= closest + 1e-6
        ]
        feasible_at_area = [gpu for gpu in at_area if gpu["feasible"]]
        iso = (
            max(feasible_at_area, key=lambda gpu: gpu["per_user_tokens_s"])
            if feasible_at_area
            else at_area[0]
        )
        # **Each metric is compared against the GPU design that is best at
        # THAT metric** (framework review finding 1).  Dividing a ROM pipeline's
        # every-slot-busy aggregate by the GPU layout chosen for single-user
        # speed compared hundreds of users with one.
        iso_aggregate = (
            max(feasible_at_area, key=lambda gpu: gpu["aggregate_tokens_s"])
            if feasible_at_area
            else iso
        )
        # Prefill is only priced at batch 1; each side's fastest prefill layout.
        prefilled = [gpu for gpu in feasible_at_area if gpu.get("time_to_first_token_s")]
        iso_ttft = (
            min(prefilled, key=lambda gpu: gpu["time_to_first_token_s"])
            if prefilled
            else None
        )
        iso_energy = (
            min(
                feasible_at_area,
                key=lambda gpu: gpu["energy_j_per_token"] or math.inf,
            )
            if feasible_at_area
            else iso
        )
        pipeline_only = next(
            (gpu for gpu in at_area if gpu["parallelism"] in ("pipeline", "none")),
            iso,
        )
        feasible_gpus = [gpu for gpu in candidates if gpu["feasible"]]
        fastest = (
            max(feasible_gpus, key=lambda gpu: gpu["per_user_tokens_s"])
            if feasible_gpus
            else None
        )
        comparisons.append(
            {
                "model": row["model"],
                "context_tokens": row["context_tokens"],
                "batch_size": row["batch_size"],
                "rom_design": row["design"],
                "rom_silicon_area_mm2": row["silicon_area_mm2"],
                "rom_device_count": row["device_count"],
                "rom_feasible": row["feasible"],
                "rom_reasons": row["reasons"],
                "rom_per_user_tokens_s": row["per_user_tokens_s"],
                "rom_aggregate_tokens_s": row["aggregate_tokens_s"],
                "rom_binding_constraint": row["binding_constraint"],
                # **How many sessions each side can actually hold, on the same
                # row as the ratio.**  A per-user rate divided by a per-user
                # rate is a latency claim, and a latency claim taken from a
                # machine that holds one session against one that holds
                # hundreds is not the same trade the reader thinks it is.
                # Publishing the two counts beside the quotient is the whole
                # fix; suppressing them is how a single-session part gets read
                # as a server.
                "rom_max_resident_users": row["max_resident_users"],
                # **Energy per token, on both sides, at the same area.**  This
                # was unpublishable until the power model enumerated anything
                # beyond memory bytes and MACs, and it is much of the ROM
                # argument: a mask-ROM part does not pay DRAM access energy for
                # its weights.  The number includes the static share amortised
                # over the tokens the step actually produces, so a machine that
                # is fast and leaky is not flattered against one that is slow
                # and cool.
                "rom_energy_j_per_token": row["energy_j_per_token"],
                "rom_dynamic_energy_j_per_token": row["dynamic_energy_j_per_token"],
                "rom_power_w": row["power_w"],
                "rom_static_power_w": row["static_power_w"],
                "rom_power_density_w_per_mm2": row["power_density_w_per_mm2"],
                "rom_thermal_scale": row["thermal_scale"],
                "iso_area_gpu_design": iso["design"],
                "iso_area_gpu_silicon_area_mm2": iso["silicon_area_mm2"],
                "iso_area_gpu_device_count": iso["device_count"],
                "iso_area_ratio": (
                    row["silicon_area_mm2"] / iso["silicon_area_mm2"]
                    if iso["silicon_area_mm2"] > 0
                    else None
                ),
                "iso_area_gpu_feasible": iso["feasible"],
                "iso_area_gpu_reasons": iso["reasons"],
                "iso_area_gpu_per_user_tokens_s": iso["per_user_tokens_s"],
                "iso_area_gpu_aggregate_tokens_s": iso["aggregate_tokens_s"],
                "iso_area_gpu_binding_constraint": iso["binding_constraint"],
                "iso_area_gpu_max_resident_users": iso["max_resident_users"],
                "iso_area_gpu_energy_j_per_token": iso["energy_j_per_token"],
                "iso_area_gpu_dynamic_energy_j_per_token": iso[
                    "dynamic_energy_j_per_token"
                ],
                "iso_area_gpu_power_w": iso["power_w"],
                "iso_area_gpu_static_power_w": iso["static_power_w"],
                "iso_area_gpu_power_density_w_per_mm2": iso[
                    "power_density_w_per_mm2"
                ],
                "iso_area_gpu_thermal_scale": iso["thermal_scale"],
                "iso_area_gpu_energy_design": iso_energy["design"],
                "iso_area_gpu_best_energy_j_per_token": iso_energy["energy_j_per_token"],
                "energy_per_token_ratio": (
                    row["energy_j_per_token"] / iso_energy["energy_j_per_token"]
                    if row["feasible"]
                    and iso_energy["feasible"]
                    and row["energy_j_per_token"]
                    and iso_energy["energy_j_per_token"]
                    else None
                ),
                "tokens_per_joule_advantage_x": (
                    iso_energy["energy_j_per_token"] / row["energy_j_per_token"]
                    if row["feasible"]
                    and iso_energy["feasible"]
                    and row["energy_j_per_token"]
                    and iso_energy["energy_j_per_token"]
                    else None
                ),
                "rom_time_to_first_token_s": row.get("time_to_first_token_s"),
                "iso_area_gpu_ttft_design": iso_ttft["design"] if iso_ttft else None,
                "iso_area_gpu_time_to_first_token_s": (
                    iso_ttft.get("time_to_first_token_s") if iso_ttft else None
                ),
                "time_to_first_token_ratio": (
                    row["time_to_first_token_s"] / iso_ttft["time_to_first_token_s"]
                    if row.get("time_to_first_token_s") and iso_ttft
                    else None
                ),
                "iso_area_gpu_parallelism": iso["parallelism"],
                "iso_area_gpu_pipeline_stages": iso["pipeline_stages"],
                "iso_area_gpu_pipeline_stages_uncapped": iso[
                    "pipeline_stages_uncapped"
                ],
                "iso_area_gpu_link_latency_without_stage_cap_s": iso[
                    "link_latency_without_stage_cap_s"
                ],
                "iso_area_gpu_per_user_tokens_s_without_stage_cap": (
                    1.0 / iso["step_time_without_stage_cap_s"]
                    if iso.get("step_time_without_stage_cap_s")
                    else None
                ),
                "per_user_speed_ratio_without_stage_cap": (
                    row["per_user_tokens_s"]
                    * iso["step_time_without_stage_cap_s"]
                    if row["feasible"]
                    and iso["feasible"]
                    and iso.get("step_time_without_stage_cap_s")
                    else None
                ),
                "iso_area_gpu_hop_events_per_token": iso["hop_events_per_token"],
                "iso_area_gpu_link_latency_s": iso["component_times_s"][
                    "link_latency"
                ],
                "iso_area_gpu_link_share_of_step": (
                    iso["component_times_s"]["link_latency"] / iso["step_time_s"]
                    if iso["step_time_s"]
                    else None
                ),
                "pipeline_only_gpu_design": pipeline_only["design"],
                "pipeline_only_gpu_per_user_tokens_s": (
                    pipeline_only["per_user_tokens_s"]
                ),
                "pipeline_only_gpu_link_latency_s": (
                    pipeline_only["component_times_s"]["link_latency"]
                ),
                "topology_choice_gain": (
                    iso["per_user_tokens_s"] / pipeline_only["per_user_tokens_s"]
                    if pipeline_only["per_user_tokens_s"] > 0
                    else None
                ),
                "per_user_speed_ratio_pipeline_only_gpu": (
                    row["per_user_tokens_s"] / pipeline_only["per_user_tokens_s"]
                    if row["feasible"]
                    and pipeline_only["feasible"]
                    and pipeline_only["per_user_tokens_s"] > 0
                    else None
                ),
                "per_user_speed_ratio": (
                    row["per_user_tokens_s"] / iso["per_user_tokens_s"]
                    if row["feasible"] and iso["feasible"] and iso["per_user_tokens_s"] > 0
                    else None
                ),
                "iso_area_gpu_aggregate_design": iso_aggregate["design"],
                "iso_area_gpu_best_aggregate_tokens_s": iso_aggregate["aggregate_tokens_s"],
                "iso_area_gpu_best_aggregate_users": iso_aggregate["pipeline_fill_users"],
                "rom_aggregate_users": row["pipeline_fill_users"],
                "aggregate_speed_ratio": (
                    row["aggregate_tokens_s"] / iso_aggregate["aggregate_tokens_s"]
                    if row["feasible"]
                    and iso_aggregate["feasible"]
                    and iso_aggregate["aggregate_tokens_s"] > 0
                    else None
                ),
                "fastest_feasible_gpu_design": (
                    fastest["design"] if fastest else None
                ),
                "fastest_feasible_gpu_silicon_area_mm2": (
                    fastest["silicon_area_mm2"] if fastest else None
                ),
                "fastest_feasible_gpu_per_user_tokens_s": (
                    fastest["per_user_tokens_s"] if fastest else None
                ),
            }
        )

    # --- GPU topology choice ----------------------------------------------
    # The symmetric half of the table below.  For every cluster size the study
    # evaluates, this records what each parallelism actually delivered, so the
    # claim "the GPU was allowed to choose" is checkable rather than asserted.
    gpu_topology_choices: list[dict[str, Any]] = []
    gpu_sizes: dict[tuple[str, int, int], list[dict[str, Any]]] = {}
    for row in points:
        if row["family"] != "gpu":
            continue
        gpu_sizes.setdefault(
            (row["model"], row["device_count"], row["batch_size"]), []
        ).append(row)
    for (model_name, count, batch), rows in sorted(gpu_sizes.items()):
        by_parallelism = {row["parallelism"]: row for row in rows}
        feasible = [row for row in rows if row["feasible"]]
        if not feasible:
            continue
        best = max(feasible, key=lambda row: row["per_user_tokens_s"])
        gpu_topology_choices.append(
            {
                "model": model_name,
                "device_count": count,
                "batch_size": batch,
                "silicon_area_mm2": best["silicon_area_mm2"],
                "best_parallelism": best["parallelism"],
                "best_per_user_tokens_s": best["per_user_tokens_s"],
                "best_link_latency_s": best["link_latency_s"],
                "best_link_share_of_step": best["link_share_of_step"],
                "best_hop_events_per_token": best["hop_events_per_token"],
                "best_hop_semantics": best["hop_semantics"],
                "binding_constraint": best["binding_constraint"],
                **{
                    f"{name}_per_user_tokens_s": (
                        by_parallelism[name]["per_user_tokens_s"]
                        if name in by_parallelism
                        else None
                    )
                    for name in ("none", "pipeline", "tensor", "hybrid")
                },
                **{
                    f"{name}_link_latency_s": (
                        by_parallelism[name]["link_latency_s"]
                        if name in by_parallelism
                        else None
                    )
                    for name in ("none", "pipeline", "tensor", "hybrid")
                },
            }
        )

    # --- topology choice --------------------------------------------------
    topology_choices: list[dict[str, Any]] = []
    for model_name, _, context in study_models:
        for batch in BATCHES:
            rows = [
                row
                for row in points
                if row["model"] == model_name
                and row["batch_size"] == batch
                and row["family"] == "rom"
                and row["weight_amortization"] == "batched"
                and row["feasible"]
            ]
            if not rows:
                topology_choices.append(
                    {
                        "model": model_name,
                        "context_tokens": context,
                        "batch_size": batch,
                        "best_design": None,
                        "best_per_user_tokens_s": None,
                        "array_best_per_user_tokens_s": None,
                        "wafer_best_per_user_tokens_s": None,
                        "array_or_wafer": "no feasible ROM design",
                    }
                )
                continue
            arrays = [row for row in rows if row["topology_kind"] == "array"]
            wafers = [row for row in rows if row["topology_kind"] == "wafer"]
            best = _pick_best(rows, "per_user_tokens_s", "silicon_area_mm2")
            array_best = (
                _pick_best(arrays, "per_user_tokens_s", "silicon_area_mm2")
                if arrays
                else None
            )
            wafer_best = (
                _pick_best(wafers, "per_user_tokens_s", "silicon_area_mm2")
                if wafers
                else None
            )
            topology_choices.append(
                {
                    "model": model_name,
                    "context_tokens": context,
                    "batch_size": batch,
                    "best_design": best["design"],
                    "best_per_user_tokens_s": best["per_user_tokens_s"],
                    "best_aggregate_tokens_s": best["aggregate_tokens_s"],
                    "best_silicon_area_mm2": best["silicon_area_mm2"],
                    "best_binding_constraint": best["binding_constraint"],
                    "best_tokens_s_per_mm2": (
                        best["per_user_tokens_s"] / best["silicon_area_mm2"]
                    ),
                    "array_best_design": array_best["design"] if array_best else None,
                    "array_best_silicon_area_mm2": (
                        array_best["silicon_area_mm2"] if array_best else None
                    ),
                    "wafer_best_silicon_area_mm2": (
                        wafer_best["silicon_area_mm2"] if wafer_best else None
                    ),
                    "array_best_per_user_tokens_s": (
                        array_best["per_user_tokens_s"] if array_best else None
                    ),
                    "wafer_best_design": wafer_best["design"] if wafer_best else None,
                    "wafer_best_per_user_tokens_s": (
                        wafer_best["per_user_tokens_s"] if wafer_best else None
                    ),
                    "array_or_wafer": best["topology_kind"],
                    "array_or_wafer_per_mm2": max(
                        rows,
                        key=lambda row: row["per_user_tokens_s"]
                        / row["silicon_area_mm2"],
                    )["topology_kind"],
                    "wafer_over_array_ratio": (
                        wafer_best["per_user_tokens_s"]
                        / array_best["per_user_tokens_s"]
                        if array_best
                        and wafer_best
                        and array_best["per_user_tokens_s"] > 0
                        else None
                    ),
                }
            )

    amortization_fork: list[dict[str, Any]] = []
    for model_name, _, context in study_models:
      for spare in SPARE_AREA_POLICIES:
        for batch in BATCHES:
            # Compared at a MATCHED floorplan.  Picking each policy's best over
            # both floorplans mixes the amortisation question with the
            # allocation question and hides both: a per-region machine that
            # replicated its array would be compared against a broadcast one
            # that did not.
            pair: dict[str, dict[str, Any] | None] = {}
            for policy in WEIGHT_AMORTIZATIONS:
                rows = [
                    row
                    for row in points
                    if row["model"] == model_name
                    and row["family"] == "rom"
                    and row["batch_size"] == batch
                    and row["weight_amortization"] == policy
                    and row["spare_area_policy"] == spare
                    and row["feasible"]
                ]
                pair[policy] = (
                    max(rows, key=lambda row: row["aggregate_tokens_s"])
                    if rows
                    else None
                )
            batched = pair.get("batched")
            record: dict[str, Any] = {
                "model": model_name,
                "context_tokens": context,
                "batch_size": batch,
                "spare_area_policy": spare,
            }
            for policy, point in pair.items():
                record[f"{policy}_design"] = point["design"] if point else None
                record[f"{policy}_per_user_tokens_s"] = (
                    point["per_user_tokens_s"] if point else None
                )
                record[f"{policy}_aggregate_tokens_s"] = (
                    point["aggregate_tokens_s"] if point else None
                )
                record[f"{policy}_binding_constraint"] = (
                    point["binding_constraint"] if point else None
                )
                # How much aggregate throughput this policy gives up against
                # the amortising one.  1.0 means it gives up nothing.
                record[f"{policy}_aggregate_penalty_x"] = (
                    batched["aggregate_tokens_s"] / point["aggregate_tokens_s"]
                    if batched and point and point["aggregate_tokens_s"] > 0
                    else None
                )
                record[f"{policy}_silicon_area_mm2"] = (
                    point["silicon_area_mm2"] if point else None
                )
            amortization_fork.append(record)

    floorplan_sweep: list[dict[str, Any]] = []
    for model_name, _, context in study_models:
        for batch in BATCHES:
            reference = None
            for policy in WEIGHT_AMORTIZATIONS:
                for spare in SPARE_AREA_POLICIES:
                    rows = [
                        row
                        for row in points
                        if row["model"] == model_name
                        and row["family"] == "rom"
                        and row["batch_size"] == batch
                        and row["weight_amortization"] == policy
                        and row["spare_area_policy"] == spare
                        and row["feasible"]
                    ]
                    point = (
                        max(rows, key=lambda row: row["aggregate_tokens_s"])
                        if rows
                        else None
                    )
                    if policy == "batched" and spare == "sram":
                        reference = point
                    floorplan_sweep.append(
                        {
                            "model": model_name,
                            "context_tokens": context,
                            "batch_size": batch,
                            "weight_amortization": policy,
                            "spare_area_policy": spare,
                            "design": point["design"] if point else None,
                            "device_count": point["device_count"] if point else None,
                            "silicon_area_mm2": (
                                point["silicon_area_mm2"] if point else None
                            ),
                            "rom_replication_factor": (
                                point["rom_replication_factor"] if point else None
                            ),
                            "rom_sweeps_per_step": (
                                point["rom_sweeps_per_step"] if point else None
                            ),
                            "per_user_tokens_s": (
                                point["per_user_tokens_s"] if point else None
                            ),
                            "aggregate_tokens_s": (
                                point["aggregate_tokens_s"] if point else None
                            ),
                            "aggregate_tokens_s_per_mm2": (
                                point["aggregate_tokens_s"] / point["silicon_area_mm2"]
                                if point and point["silicon_area_mm2"] > 0
                                else None
                            ),
                            "binding_constraint": (
                                point["binding_constraint"] if point else None
                            ),
                            "vs_reference_floorplan_x": (
                                point["aggregate_tokens_s"]
                                / reference["aggregate_tokens_s"]
                                if point
                                and reference
                                and reference["aggregate_tokens_s"] > 0
                                else None
                            ),
                        }
                    )
    result: dict[str, Any] = {
        "schema_version": 1,
        "study_id": study_id,
        "comparison_contract": config["contract"],
        "model": "src/opentallas/roofline.py",
        "inputs": {
            "technology_config": str(TECHNOLOGY_PATH.relative_to(ROOT)),
            "technology_sha256": _sha256(TECHNOLOGY_PATH),
            "models": {
                name: {
                    "path": str(path.relative_to(ROOT)),
                    "sha256": _sha256(path),
                    "context_tokens": context,
                }
                for name, path, context in study_models
            },
            "anchor_model": {
                "path": str(ANCHOR_MODEL_PATH.relative_to(ROOT)),
                "sha256": _sha256(ANCHOR_MODEL_PATH),
            },
            "batches": list(BATCHES),
            "rom_node": node,
            "gpu_parts": list(config["gpu_parts"]),
            "hbm_generation": hbm_generation,
            "design_batch": DESIGN_BATCH,
            "provision_batch": PROVISION_BATCH,
            "wafer_area_mm2": wafer_area,
            "reticle_area_mm2": reticle_area,
            "rom_area_ladder_wafers": list(ROM_AREA_LADDER),
            "gpu_area_ladder_wafers": list(GPU_AREA_LADDER),
            "array_device_ladder_multipliers": list(
                ARRAY_DEVICE_LADDER_MULTIPLIERS
            ),
            "array_device_ladder_note": (
                "arrays are also emitted at the device counts whose silicon "
                "equals each wafer rung, so every wafer design has an array at "
                "the same area"
            ),
            "counting_convention": (
                "one multiply plus one add equals two operations"
            ),
        },
        "technology_derivations": _technology_derivations(technology, node, config),
        "graded_inputs": technology.inputs_by_grade(),
        "model_summaries": model_summaries,
        "floorplan_comparison": _floorplan_comparison(
            technology,
            ModelProfile.load(ANCHOR_MODEL_PATH),
            node,
            technology.graded("reticle", "area_mm2").value,
        ),
        "designs": designs,
        "points": points,
        "comparisons": comparisons,
        "capacity_comparison": _capacity_comparison(points),
        "nvlink_domain_sensitivity": domain_sensitivity,
        "link_latency_sensitivity": (
            _link_latency_sensitivity(study_id, technology)
            if with_sensitivity
            else []
        ),
        "fabric_clock_sensitivity": (
            _fabric_clock_sensitivity(study_id, technology)
            if with_sensitivity
            else []
        ),
        "rom_cell_ratio_sensitivity": (
            _rom_cell_ratio_sensitivity(study_id, technology)
            if with_sensitivity
            else []
        ),
        "topology_choices": topology_choices,
        "gpu_topology_choices": gpu_topology_choices,
        "amortization_fork": amortization_fork,
        "floorplan_sweep": floorplan_sweep,
        "latency_crossovers": crossovers,
    }
    result["latency_correction_ladder"] = _latency_correction_ladder(result)
    result["power_and_energy"] = _power_and_energy(result)
    result["design_selection"] = _design_selection(result, study_models)
    result["consistency_audit"] = _consistency_audit(result, technology)
    return result


def _area_class(area_mm2: float) -> str:
    if area_mm2 >= 40_000:
        return "wafer (>=40,000 mm2)"
    if area_mm2 >= 5_000:
        return "large array (5,000-40,000 mm2)"
    if area_mm2 >= 1_600:
        return "small array (1,600-5,000 mm2)"
    return "single die (<1,600 mm2)"


def _power_and_energy(result: dict[str, Any]) -> dict[str, Any]:
    """Where the cooling limit binds, and what a token costs on each side.

    Both halves of this were unpublishable before the power model enumerated
    anything beyond memory bytes and multiply-accumulates.  ``thermal_scale``
    was exactly 1.0 at every feasible point in both studies, so the model did
    not express dark silicon at all; and every watt and every joule per token
    it reported was 7-9x low against two published parts, so none of them could
    be quoted.
    """

    points = result["points"]
    feasible = [row for row in points if row["feasible"]]
    throttled = [row for row in feasible if row["thermal_scale"] > 1.0 + 1e-12]
    uncoolable = [row for row in points if row.get("cooling_infeasible")]

    by_class: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in feasible:
        by_class.setdefault(
            (row["family"], _area_class(row["silicon_area_mm2"])), []
        ).append(row)
    headroom = []
    for (family, klass), rows in sorted(by_class.items()):
        fractions = sorted(row["power_headroom_fraction"] or 0.0 for row in rows)
        headroom.append(
            {
                "family": family,
                "area_class": klass,
                "points": len(rows),
                "throttled": sum(
                    1 for row in rows if row["thermal_scale"] > 1.0 + 1e-12
                ),
                "median_power_headroom_fraction": fractions[len(fractions) // 2],
                "max_power_headroom_fraction": fractions[-1],
                "max_power_density_w_per_mm2": max(
                    row["power_density_w_per_mm2"] for row in rows
                ),
                "median_static_share_of_power": sorted(
                    row["static_power_fraction_of_total"] for row in rows
                )[len(rows) // 2],
            }
        )

    worst = sorted(throttled, key=lambda row: -row["thermal_scale"])[:12]
    # One row per (model, batch), and the design chosen by the SAME rule the
    # report uses everywhere else it says "best": the smallest silicon within
    # 5% of the fastest per-user rate.  Listing every comparison instead would
    # bury the answer under wafers serving one user, whose joules per token are
    # enormous for a reason that has nothing to do with the memory technology.
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in result["comparisons"]:
        if row["rom_feasible"] and row["iso_area_gpu_feasible"]:
            grouped.setdefault((row["model"], row["batch_size"]), []).append(row)
    energy = []
    for (model, batch), rows in sorted(grouped.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        best = _pick_best(rows, "rom_per_user_tokens_s", "rom_silicon_area_mm2")
        if best is None:
            continue
        energy.append(
            {
                "model": model,
                "batch_size": batch,
                "rom_design": best["rom_design"],
                "silicon_area_mm2": best["rom_silicon_area_mm2"],
                "rom_energy_j_per_token": best["rom_energy_j_per_token"],
                "rom_dynamic_energy_j_per_token": best[
                    "rom_dynamic_energy_j_per_token"
                ],
                "rom_power_w": best["rom_power_w"],
                "rom_static_power_w": best["rom_static_power_w"],
                "rom_binds_on": best["rom_binding_constraint"],
                "rom_per_user_tokens_s": best["rom_per_user_tokens_s"],
                "gpu_design": best["iso_area_gpu_design"],
                "gpu_energy_j_per_token": best["iso_area_gpu_energy_j_per_token"],
                "gpu_dynamic_energy_j_per_token": best[
                    "iso_area_gpu_dynamic_energy_j_per_token"
                ],
                "gpu_power_w": best["iso_area_gpu_power_w"],
                "gpu_static_power_w": best["iso_area_gpu_static_power_w"],
                "gpu_binds_on": best["iso_area_gpu_binding_constraint"],
                "gpu_per_user_tokens_s": best["iso_area_gpu_per_user_tokens_s"],
                "tokens_per_joule_advantage_x": best["tokens_per_joule_advantage_x"],
            }
        )

    # Wafer-scale ROM silicon specifically.  "46,225 mm2" on the GPU side is a
    # 56-die CLUSTER, each die at its own published TDP, so including it here
    # would answer a different question.
    # ``topology_kind`` rather than an area threshold: since the array ladder
    # samples reticle arrays at every wafer area, a 57-die array is wafer-sized
    # silicon but not a wafer, and it is exactly the class the paragraph this
    # metric feeds contrasts wafers against.
    wafer_rom = [
        row
        for row in feasible
        if row["family"] == "rom" and row.get("topology_kind") == "wafer"
    ]
    wafer_rom_headroom = (
        max(row["power_headroom_fraction"] or 0.0 for row in wafer_rom)
        if wafer_rom
        else None
    )
    if throttled:
        worst_row = worst[0]
        stores = sorted({row["kv_store"] for row in throttled})
        reading = (
            "The cooling limit binds, and it binds where a uniform multiplier on "
            "the old traffic-proportional model said it would NOT. It is not the "
            "wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep "
            "is a fixed cost spread over far more silicon, and the busiest one "
            "here reaches "
            + (
                f"{wafer_rom_headroom * 100:.0f}% of its budget. "
                if wafer_rom_headroom is not None
                else "no such design is in this study. "
            )
            + "It is the SMALL, DENSE ARRAYS, and specifically the ones that put "
            f"KV in {'/'.join(store.upper() for store in stores)}: the worst "
            "point's dynamic energy is dominated by KV traffic and not by the ROM "
            "sweep at all. The batch dependence the earlier uniform-multiplier "
            "analysis predicted does NOT survive -- static power does not scale "
            "with traffic, so batch "
            f"{min(row['batch_size'] for row in throttled)} throttles too, and "
            f"the worst point here is at batch {worst_row['batch_size']}."
        )
    else:
        reading = (
            "Nothing in this study is power-limited. That is a statement about "
            "these designs and not an artifact of the energy model: static power "
            "is charged per mm2 per second, so a design cannot escape it by "
            "moving fewer bytes. The busiest point reaches "
            f"{max(row['max_power_headroom_fraction'] for row in headroom) * 100:.0f}% "
            "of its cooling budget"
            + (
                f", and the busiest wafer-scale ROM design {wafer_rom_headroom * 100:.0f}%. "
                if wafer_rom_headroom is not None
                else ". "
            )
            + "The companion study at the other node, whose HBM generation "
            "delivers more than twice the bandwidth per stack, does have "
            "power-limited points."
        )

    return {
        "purpose": (
            "The two questions the old power model could not answer: does the "
            "cooling limit ever bind, and what does a token cost in joules on "
            "each side. Neither was askable while power was proportional to "
            "traffic -- a throttled step drew LESS modelled power the more it "
            "was throttled, so every design was coolable at some speed, and "
            "every watt was 7-9x low against both published parts."
        ),
        "feasible_points": len(feasible),
        "thermally_throttled_points": len(throttled),
        "thermally_throttled_fraction": (
            len(throttled) / len(feasible) if feasible else 0.0
        ),
        "uncoolable_points": len(uncoolable),
        "throttled_by_family": {
            family: sum(1 for row in throttled if row["family"] == family)
            for family in sorted({row["family"] for row in throttled})
        },
        "throttled_by_area_class": {
            klass: sum(
                1 for row in throttled if _area_class(row["silicon_area_mm2"]) == klass
            )
            for klass in sorted(
                {_area_class(row["silicon_area_mm2"]) for row in throttled}
            )
        },
        "throttled_by_batch": {
            str(batch): sum(1 for row in throttled if row["batch_size"] == batch)
            for batch in sorted({row["batch_size"] for row in throttled})
        },
        "throttled_by_kv_store": {
            store: sum(1 for row in throttled if row["kv_store"] == store)
            for store in sorted({row["kv_store"] for row in throttled})
        },
        "power_headroom_by_area_class": headroom,
        "worst_throttled_points": [
            {
                "design": row["design"],
                "model": row["model"],
                "batch_size": row["batch_size"],
                "silicon_area_mm2": row["silicon_area_mm2"],
                "kv_store": row["kv_store"],
                "thermal_scale": row["thermal_scale"],
                "power_w": row["power_w"],
                "cooling_limit_w": row["cooling_limit_w"],
                "static_power_w": row["static_power_w"],
                "static_share_of_power": row["static_power_fraction_of_total"],
                "dynamic_energy_breakdown_j": row["dynamic_energy_breakdown_j"],
                "per_user_tokens_s": row["per_user_tokens_s"],
                "per_user_tokens_s_unthrottled": (
                    row["per_user_tokens_s"] * row["thermal_scale"]
                ),
            }
            for row in worst
        ],
        "energy_per_token": energy,
        "energy_per_token_selection_rule": (
            "One row per (model, batch). The ROM design is the smallest silicon "
            "within 5% of the fastest per-user rate -- the same rule the report "
            "uses everywhere it says 'best' -- and the GPU beside it is the "
            "iso-area comparator that comparison already chose. Listing every "
            "comparison instead buries the answer under wafers serving one user."
        ),
        "wafer_scale_rom_max_power_headroom_fraction": wafer_rom_headroom,
        "reading": reading,
    }


def _technology_derivations(
    technology: Technology, node: str, config: dict[str, Any]
) -> dict[str, Any]:
    formats = ("bf16", "fp8", "w4a8", "fp4", "fp32")
    rom_capacity = technology.rom_bits_per_mm2(node)
    rom_bandwidth = technology.rom_read_bytes_s_per_mm2(node)
    rom_eff = technology.efficiency("rom_read_bandwidth")
    sweep = (
        rom_capacity.value / 8.0 / (rom_bandwidth.value * rom_eff.value)
    )
    ideal_sweep = rom_capacity.value / 8.0 / rom_bandwidth.value
    return {
        "node": node,
        "sram_capacity_bits_per_mm2": technology.sram_bits_per_mm2(node).to_dict(),
        "rom_capacity_bits_per_mm2": rom_capacity.to_dict(),
        "rom_read_bytes_s_per_mm2": rom_bandwidth.to_dict(),
        "sram_read_bytes_s_per_mm2": technology.sram_read_bytes_s_per_mm2(
            node
        ).to_dict(),
        "compute_ops_s_per_mm2": {
            fmt: technology.compute_ops_s_per_mm2(node, fmt).to_dict()
            for fmt in formats
        },
        "rom_full_array_sweep_time_s": sweep,
        "rom_full_array_sweep_ceiling_tokens_s": 1.0 / sweep,
        "rom_full_array_sweep_time_s_before_derate": ideal_sweep,
        "rom_full_array_sweep_ceiling_tokens_s_before_derate": 1.0 / ideal_sweep,
        "rom_sweep_note": (
            "The ROM full-array sweep time is rom_capacity_density divided by "
            "rom_read_bandwidth_density. Both scale with the same published "
            "bitcell-area ratio under this derivation, so the sweep time -- and "
            "hence the ROM path's hard per-token ceiling -- is the SAME at every "
            "node. Process scaling buys a ROM design capacity, not per-token "
            "speed. No clock-frequency bonus is credited, which makes this the "
            "conservative reading."
        ),
        "efficiencies": {
            name: technology.efficiency(name).to_dict()
            for name in ("compute", "rom_read_bandwidth", "sram_read_bandwidth",
                         "hbm_bandwidth", "hbm_capacity", "stage_balance")
        },
        "links": {
            name: {
                "hop_latency_s": technology.link(name)[0].to_dict(),
                "bytes_s": technology.link(name)[1].to_dict(),
                "fabric": technology.link_fabric(name),
                "domain_size": technology.link_domain_size(name).to_dict(),
                "switch_radix": technology.link_switch_radix(name).to_dict(),
            }
            for name in sorted(technology.raw["links"])
            if name != "none"
        },
        "link_plan": {
            "intra": str(config["intra_link"]),
            "inter": str(config["inter_link"]),
            "rule": (
                "Both sides of this study are charged the same two link classes. "
                "A cluster is tensor-parallel inside one high-bandwidth domain and "
                "pipeline-parallel across domains; a wafer machine is the same shape "
                "with the on-wafer mesh inside a wafer and a package-class link "
                "between wafers."
            ),
        },
        "hbm": {
            field: technology.hbm(config["hbm_generation"], field).to_dict()
            for field in (
                "stack_capacity_bytes",
                "stack_bandwidth_bytes_s",
                "stack_beachfront_mm",
                "phy_area_mm2_per_stack",
            )
        },
    }


# --------------------------------------------------------------------------
# audit
# --------------------------------------------------------------------------


def _latency_correction_ladder(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Before and after the latency separation, on the fixed area ladder.

    The **before** column is not a memory of an earlier run: every point in this
    study carries ``per_user_tokens_s_throughput_view``, the number the model
    produced when it charged a pipeline's service time on the machine's
    aggregate resources and its hops on the single-token path.  Ranking each
    side by that column reproduces the previous study's choice of topology as
    well as its rate, so the two corrections -- the ranking and the rate -- are
    visible separately.

    Both sides are read at the same seven rungs of silicon, so a correction that
    moves one family's preferred machine cannot move the area the comparison is
    read at.
    """

    inputs = result["inputs"]
    wafer_area = inputs["wafer_area_mm2"]
    ladder = [wafer_area * count for count in inputs["rom_area_ladder_wafers"]]
    points = [row for row in result["points"] if row["batch_size"] == 1]
    rom = [
        row
        for row in points
        if row["family"] == "rom"
        and row["weight_amortization"] == "batched"
        and row["feasible"]
    ]
    gpu = [row for row in points if row["family"] == "gpu" and row["feasible"]]
    rows: list[dict[str, Any]] = []
    for summary in result["model_summaries"]:
        model = summary["model"]
        for wafers, area in zip(inputs["rom_area_ladder_wafers"], ladder):
            rom_here = [
                row
                for row in rom
                if row["model"] == model
                and abs(row["silicon_area_mm2"] - area) <= 1.0
            ]
            gpu_all = [row for row in gpu if row["model"] == model]
            if not rom_here or not gpu_all:
                continue
            closest = min(
                abs(row["silicon_area_mm2"] - area) for row in gpu_all
            )
            gpu_here = [
                row
                for row in gpu_all
                if abs(row["silicon_area_mm2"] - area) <= closest + 1e-6
            ]
            record: dict[str, Any] = {
                "model": model,
                "wafer_equivalents": wafers,
                "silicon_area_mm2": area,
                "gpu_silicon_area_mm2": gpu_here[0]["silicon_area_mm2"],
                "gpu_device_count": gpu_here[0]["device_count"],
            }
            for label, key in (
                ("before", "per_user_tokens_s_throughput_view"),
                ("after", "per_user_tokens_s"),
            ):
                best_rom = max(rom_here, key=lambda row: row[key])
                best_gpu = max(gpu_here, key=lambda row: row[key])
                record[f"rom_{label}_tokens_s"] = best_rom[key]
                record[f"rom_{label}_topology"] = (
                    f"{best_rom['topology_kind']}-{best_rom['parallelism']}"
                )
                record[f"rom_{label}_device_count"] = best_rom["device_count"]
                record[f"rom_{label}_token_slots"] = best_rom["token_slots"]
                record[f"gpu_{label}_tokens_s"] = best_gpu[key]
                record[f"gpu_{label}_topology"] = best_gpu["parallelism"]
                record[f"gpu_{label}_token_slots"] = best_gpu["token_slots"]
                record[f"ratio_{label}"] = (
                    best_rom[key] / best_gpu[key] if best_gpu[key] > 0 else None
                )
            record["ratio_change_x"] = (
                record["ratio_after"] / record["ratio_before"]
                if record["ratio_before"]
                else None
            )
            record["rom_correction_x"] = (
                record["rom_before_tokens_s"] / record["rom_after_tokens_s"]
                if record["rom_after_tokens_s"] > 0
                else None
            )
            record["gpu_correction_x"] = (
                record["gpu_before_tokens_s"] / record["gpu_after_tokens_s"]
                if record["gpu_after_tokens_s"] > 0
                else None
            )
            rows.append(record)
    return rows


def _audit_technology(
    technology: Technology,
    result: dict[str, Any],
    check: Any,
) -> None:
    """Refusals on the CONFIG, not on the generated arithmetic.

    Everything else in this audit checks that the numbers this file produced
    are consistent with each other.  These three check that the constants they
    were produced from are consistent with the evidence and with each other,
    because that is where this program's silent defects have actually lived: a
    legal value, no trap, nothing refused, and a wrong answer.

    1. **The fabric clock and the two constants derived in fabric cycles.**
       ``power.fabric_clock_hz`` is read in exactly one place and consumed in
       exactly one -- the clock leg of the static-power term -- so it sets no
       rate and a reader may reasonably conclude it is inert.  It is not:
       ``latency.pipeline_fill_drain_s`` and
       ``latency.sequencer_issue_decode_s`` state their values and both band
       ends as integer fabric-cycle counts against it, and **neither reads
       it**.  Move the clock alone and those two notes become false while the
       model keeps running, and those two are on the critical path of every
       token on both sides.  This refuses that.

    2. **The ROM cell-ratio band against this repository's own measurements.**
       ``rom.cell_to_sram_cell_area_ratio`` carried a prose-only "1/6 to 1/4"
       sweep that nothing ran and that *excluded* the 0.1298 this repository
       measured at 130 nm.  A stated uncertainty that does not contain a
       measurement the same repository committed has already been refuted; it
       just had nothing to refuse it.

    3. **Every model the study runs has its own serial matrix-pass depth.**
       ``_model_technology`` refuses at simulation time; this says so again in
       the artifact, where a reader looks.
    """

    latency = technology.raw["latency"]
    clock = float(technology.raw["power"]["fabric_clock_hz"]["value"])
    for name in ("pipeline_fill_drain_s", "sequencer_issue_decode_s"):
        entry = latency.get(name, {})
        cycles = entry.get("derived_in_fabric_cycles")
        check(
            isinstance(cycles, dict),
            f"latency.{name} states its value in fabric cycles in its note but "
            f"carries no machine-readable derived_in_fabric_cycles field, so "
            f"nothing can check it against power.fabric_clock_hz",
        )
        if not isinstance(cycles, dict):
            continue
        for key in ("value", "range_low", "range_high"):
            check(
                math.isclose(
                    float(entry[key]) * clock, float(cycles[key]), rel_tol=1e-9
                ),
                f"latency.{name}.{key} is {entry[key]!r} s, which is "
                f"{float(entry[key]) * clock:.6g} cycles at the "
                f"power.fabric_clock_hz of {clock:,.0f} Hz, not the "
                f"{cycles[key]!r} its own derivation claims. The fabric clock "
                f"and the terms derived in fabric cycles have drifted apart; "
                f"move them together or restate the derivation.",
            )

    ratio = technology.raw["rom"]["cell_to_sram_cell_area_ratio"]
    low = ratio.get("range_low")
    high = ratio.get("range_high")
    check(
        low is not None and high is not None,
        "rom.cell_to_sram_cell_area_ratio states no range_low/range_high, so "
        "its own note's instruction that it 'must be swept' is prose that "
        "nothing can execute",
    )
    for label, relative, path in MEASURED_ROM_CELL_RATIOS:
        artifact = ROOT / relative
        check(
            artifact.is_file(),
            f"rom.cell_to_sram_cell_area_ratio is checked against {relative}, "
            f"which is not in the repository",
        )
        if not artifact.is_file() or low is None or high is None:
            continue
        payload: Any = json.loads(artifact.read_text(encoding="utf-8"))
        for key in path:
            payload = payload[key]
        measured = float(payload)
        check(
            float(low) <= measured <= float(high),
            f"rom.cell_to_sram_cell_area_ratio sweeps "
            f"{float(low):.4f}-{float(high):.4f}, which EXCLUDES the "
            f"{measured:.4f} this repository measured itself at {label} "
            f"({relative}). A sweep that does not contain a measurement we "
            f"made is not an honest statement of what is unknown.",
        )

    # -- the per-node split, and the divergence it is not yet allowed to have
    by_node = technology.raw["rom"].get("cell_to_sram_cell_area_ratio_by_node")
    check(
        isinstance(by_node, dict) and bool(by_node),
        "rom.cell_to_sram_cell_area_ratio_by_node is missing or empty. This "
        "repository measured the ROM-to-SRAM cell ratio 92.7% apart at two "
        "nodes, so one node-free number applied at every modelled node is a "
        "legal value with nothing to refuse it.",
    )
    if isinstance(by_node, dict):
        for study_config in STUDIES.values():
            rom_node = str(study_config["rom_node"])
            check(
                rom_node in by_node,
                f"no rom.cell_to_sram_cell_area_ratio_by_node entry for "
                f"{rom_node}, which is a ROM node this program runs a study "
                f"at. No node may inherit another node's bit-cell ratio.",
            )
        for node_name, node_entry in by_node.items():
            for key in ("value", "range_low", "range_high"):
                # THE TRAP.  ``src/opentallas/roofline.py:rom_bits_per_mm2``
                # still reads the FLAT key with no node argument, and the
                # Taalas HC1 gate path never goes through ``_node_technology``
                # at all.  So a by-node value that differs from the flat one
                # would price the sweep at one ROM density and the anchor at
                # another, inside one artifact, with nothing saying so.  Until
                # that one call takes the node it is already handed, the split
                # is allowed to ADDRESS the value by node and not to CHANGE it.
                check(
                    math.isclose(
                        float(node_entry[key]),
                        float(ratio[key]),
                        rel_tol=1e-12,
                    ),
                    f"rom.cell_to_sram_cell_area_ratio_by_node.{node_name}."
                    f"{key} is {node_entry[key]!r} but the flat "
                    f"rom.cell_to_sram_cell_area_ratio.{key} is {ratio[key]!r}. "
                    f"They may not diverge yet: "
                    f"src/opentallas/roofline.py:rom_bits_per_mm2 reads the "
                    f"flat key with no node argument and run_anchors -> "
                    f"taalas_hc1_anchor never goes through the study's node "
                    f"substitution, so a divergence would price the sweep and "
                    f"the HC1 gate at two different ROM densities in one "
                    f"artifact and nothing would say so. Make that one call "
                    f"take the node it is already passed, then diverge.",
                )
            for label, relative, path in MEASURED_ROM_CELL_RATIOS:
                artifact = ROOT / relative
                if not artifact.is_file():
                    continue
                payload: Any = json.loads(artifact.read_text(encoding="utf-8"))
                for key in path:
                    payload = payload[key]
                measured = float(payload)
                check(
                    float(node_entry["range_low"])
                    <= measured
                    <= float(node_entry["range_high"]),
                    f"rom.cell_to_sram_cell_area_ratio_by_node.{node_name} "
                    f"sweeps {float(node_entry['range_low']):.4f}-"
                    f"{float(node_entry['range_high']):.4f}, which EXCLUDES "
                    f"the {measured:.4f} this repository measured itself at "
                    f"{label} ({relative}).",
                )

    # -- the two cell-area constants, and which of them the read bandwidth
    #    actually follows.  THE DEFECT THIS REFUSES: `rom_bits_per_mm2` scales
    #    capacity with `rom.cell_to_sram_cell_area_ratio` while
    #    `rom_read_bytes_s_per_mm2` never reads it, so the ROM lane's hard
    #    floor -- the full-array sweep -- moves 3.0x across that constant's own
    #    band.  One function away, `rom_read_bytes_s_per_mm2_for` DOES divide
    #    bandwidth by `rom.cim_cell_area_multiplier`, on the stated ground that
    #    a bigger cell adds no bitlines and no sense amps, which makes the sweep
    #    invariant.  Two cell-area constants in one density chain with opposite
    #    coupling rules, and until this check existed nothing anywhere compared
    #    them.  Neither reading is adopted here: what is refused is holding both
    #    without declaring which is which.
    rule = technology.raw["rom"].get("read_bandwidth_scaling_rule", {})
    node = str(result["inputs"]["rom_node"])
    for field, description, measure in (
        (
            "cell_area_coupling",
            "rom.cell_to_sram_cell_area_ratio",
            lambda tech: _observed_ratio_coupling(tech, node),
        ),
        (
            "cim_cell_area_coupling",
            "rom.cim_cell_area_multiplier",
            lambda tech: _observed_cim_coupling(tech, node),
        ),
    ):
        declared = rule.get(field)
        check(
            declared in ("none", "proportional"),
            f"rom.read_bandwidth_scaling_rule.{field} is {declared!r}. It must "
            f"declare, as \"none\" or \"proportional\", whether ROM read "
            f"bandwidth density follows {description}. The model answers this "
            f"question differently for the two cell-area constants in the same "
            f"chain, and an undeclared answer is how it held both at once.",
        )
        if declared not in ("none", "proportional"):
            continue
        observed = measure(technology)
        check(
            observed == declared,
            f"rom.read_bandwidth_scaling_rule.{field} declares {declared!r} but "
            f"the model MEASURES {observed!r}: moving {description} changes ROM "
            f"capacity density and "
            + (
                "leaves"
                if observed == "none"
                else "moves"
            )
            + f" read-bandwidth density, so the full-array sweep is "
            + ("not " if observed == "none" else "")
            + f"invariant to it. Either src/opentallas/roofline.py and this "
            f"declaration have drifted apart, or one of them is the fix.",
        )

    # -- the band is not merely stated, it is executed
    ratio_rows = result.get("rom_cell_ratio_sensitivity") or []
    # Nested runs are evaluated with ``with_sensitivity=False`` and legitimately
    # carry none, so this is gated on the same flag the other sensitivities are.
    if result.get("fabric_clock_sensitivity"):
        check(
            bool(ratio_rows),
            "the study ran its sensitivities but produced no "
            "rom_cell_ratio_sensitivity, so rom.cell_to_sram_cell_area_ratio's "
            "band is once again declared and never executed",
        )
        run_at = {
            round(float(row["cell_to_sram_cell_area_ratio"]), 6)
            for row in ratio_rows
        }
        for key in ("range_low", "value", "range_high"):
            check(
                round(float(ratio[key]), 6) in run_at,
                f"rom.cell_to_sram_cell_area_ratio.{key} = {ratio[key]!r} is "
                f"declared but the study was never re-run at it. A band that "
                f"nothing executes is the prose-only bracket again, one field "
                f"further along.",
            )

    table = latency.get("array_pass_boundaries_per_layer_by_model", {})
    for row in result["model_summaries"]:
        check(
            isinstance(table, dict) and row["model"] in table,
            f"no latency.array_pass_boundaries_per_layer_by_model entry for "
            f"{row['model']}; the serial matrix-pass depth is a per-model "
            f"quantity and no model may inherit another architecture's",
        )


def _consistency_audit(
    result: dict[str, Any], technology: Technology | None = None
) -> dict[str, Any]:
    errors: list[str] = []
    checks = 0

    def check(condition: bool, message: str) -> None:
        nonlocal checks
        checks += 1
        if not condition:
            errors.append(message)

    def close(actual: float, expected: float, tol: float = 1e-9) -> bool:
        return math.isclose(actual, expected, rel_tol=tol, abs_tol=1e-12)

    seen: set[tuple[str, str, int]] = set()
    for row in result["points"]:
        key = (row["design"], row["model"], row["batch_size"])
        check(key not in seen, f"duplicate point {key}")
        seen.add(key)
        if not row["feasible"]:
            check(row["per_user_tokens_s"] == 0.0, f"infeasible per-user rate {key}")
            check(row["aggregate_tokens_s"] == 0.0, f"infeasible aggregate {key}")
            check(bool(row["reasons"]), f"infeasible without a reason {key}")
            continue
        check(row["step_time_s"] is not None and row["step_time_s"] > 0,
              f"non-positive step time {key}")
        check(
            close(row["per_user_tokens_s"], 1.0 / row["step_time_s"]),
            f"per-user rate identity {key}",
        )
        # **The identity that used to be here is gone, and its removal is the
        # point.**  ``aggregate = batch x per_user`` held by construction only
        # because the model charged one number for both.  A machine cut into
        # ``token_slots`` slots reaches its aggregate rate only when every slot
        # has a user in it, so the aggregate is over ``pipeline_fill_users``,
        # which is the batch when the batch is large enough to fill the machine
        # and the slot count when it is not.  What the machine delivers at the
        # requested concurrency is the weaker ``delivered_tokens_s``, and *that*
        # is the quantity the old identity was about.
        check(
            close(
                row["aggregate_tokens_s"],
                row["pipeline_fill_users"] * row["per_user_tokens_s"],
            ),
            f"aggregate = fill x per-user identity {key}",
        )
        check(
            close(
                row["delivered_tokens_s"],
                row["batch_size"] * row["per_user_tokens_s"],
            ),
            f"delivered = batch x per-user identity {key}",
        )
        check(
            row["pipeline_fill_users"] >= row["batch_size"] - 1e-9,
            f"fill below the requested batch {key}",
        )
        check(
            row["aggregate_tokens_s"] >= row["delivered_tokens_s"] * (1 - 1e-9),
            f"aggregate below delivered {key}",
        )
        # A single-slot machine -- one chip, or a tensor group spanning every
        # partition -- is the one case where the two views coincide, and the
        # correction must be exactly 1.0 there.  Both validation gates are such
        # machines, which is why a correct fix leaves them untouched.
        if row["token_slots"] <= 1.0 + 1e-12:
            check(
                close(
                    row["per_user_tokens_s_throughput_view"],
                    row["per_user_tokens_s"],
                ),
                f"single-slot machine must have no latency correction {key}",
            )
        elif row["microbatch_per_slot"] >= row["batch_size"] - 1e-9:
            # Below one user per slot the two views see the same microbatch and
            # the same activation payload on every hop, so the correction is
            # exactly the extra service the serial path pays: never below one.
            # **Above it the correction can fall below one, and that is not a
            # bug.** The throughput view charged the whole batch's activations
            # across each hop while calling the result one user's latency; the
            # serial path charges one slot's microbatch, which is smaller. On a
            # KV-bound pipeline at high batch the service terms scale with the
            # batch and cancel exactly, leaving only that payload difference, so
            # the old number comes out *slower* than the corrected one. The
            # regime the ROM case is made in is batch 1, where the check bites.
            check(
                row["latency_correction_x"] >= 1.0 - 1e-9,
                f"latency correction below one {key}",
            )
        else:
            check(
                row["latency_correction_x"] > 0.0
                and math.isfinite(row["latency_correction_x"]),
                f"latency correction not a positive finite number {key}",
            )
        components = row["component_times_s"]
        service = max(
            components["weight_read"], components["kv_read"], components["compute"]
        )
        # The step time can never fall below the largest single service term
        # divided by the stage-balance derate, and never below the link latency.
        check(
            row["step_time_s"] + 1e-15 >= service,
            f"step below the largest component {key}",
        )
        check(
            row["step_time_s"] + 1e-15 >= components["link_latency"],
            f"step below link latency {key}",
        )
        check(
            row["step_time_s"] + 1e-15 >= components["layer_fixed_latency"],
            f"step below the per-layer fixed latency {key}",
        )
        check(
            row["binding_constraint"]
            in {
                "weight_read",
                "kv_read",
                "compute",
                "link_latency",
                "layer_fixed_latency",
                "thermal",
            },
            f"unknown binding constraint {key}: {row['binding_constraint']}",
        )
        # -- power ---------------------------------------------------------
        # The property, not the formula: static power is charged per second and
        # does not fall when the step is stretched, so total power is never
        # below it and the throttle can only push the machine down onto the
        # cooling limit, never through it.
        check(
            row["static_power_w"] >= -1e-12,
            f"negative static power {key}",
        )
        check(
            row["power_w"] >= row["static_power_w"] - 1e-9,
            f"total power below the static floor {key}",
        )
        check(
            close(
                row["static_power_w"],
                max(row["static_enumerated_w"], row["static_floor_w"]),
            ),
            f"static power is not max(enumerated, floor) {key}",
        )
        check(
            close(
                row["static_enumerated_w"],
                row["static_leakage_w"]
                + row["static_clock_w"]
                + row["static_memory_interface_w"],
            ),
            f"enumerated static power does not sum from its terms {key}",
        )
        check(
            row["power_w"]
            <= row["cooling_limit_w"] * (1 + 1e-6) or row["cooling_infeasible"],
            f"power above the cooling limit on a coolable point {key}",
        )
        if row["thermal_scale"] > 1.0 + 1e-9:
            # A throttled point sits exactly on its cooling limit; that is what
            # the throttle solves for.  Before static power existed this could
            # never happen, because stretching a step reduced modelled power.
            check(
                close(row["power_w"], row["cooling_limit_w"], tol=1e-6),
                f"throttled point is not on its cooling limit {key}",
            )
            check(
                row["binding_constraint"] == "thermal",
                f"throttled point does not bind on thermal {key}",
            )
        check(
            row["energy_j_per_token"] is None or row["energy_j_per_token"] > 0,
            f"non-positive energy per token {key}",
        )
        if row["binding_constraint"] != "thermal":
            check(
                components[row["binding_constraint"]]
                >= max(components.values()) - 1e-15,
                f"binding constraint is not the largest term {key}",
            )
        check(
            0.0 < row["engaged_weight_fraction"] <= 1.0 + 1e-12,
            f"engaged weight fraction out of range {key}",
        )
        # Under the compute-in-ROM policy the array is swept once per concurrent
        # stream, so the engaged bytes are that many array-fulls, not one.
        sweeps = row.get("rom_sweeps_per_step") or 1.0
        check(
            row["engaged_weight_bytes"]
            <= row["stored_weight_bytes"] * sweeps * (1 + 1e-9),
            f"engaged bytes exceed {sweeps:g} array sweeps {key}",
        )
        if row["family"] == "rom":
            # Check the property, not the formula.  Restating the model's
            # arithmetic here would make this a copy that can drift from it --
            # which is exactly how the policy list came apart.
            policy = row["weight_amortization"]
            if policy == "batched":
                check(sweeps == 1, f"batched must sweep once {key}")
            elif policy == "per_stream":
                # One sweep per concurrent stream **in one slot**.  A slot holds
                # the microbatch, not the whole batch: on a machine cut into
                # slots the batch is spread across them and each slot sweeps for
                # the users it actually holds.
                check(
                    close(sweeps, row["microbatch_per_slot"]),
                    f"per_stream must sweep once per stream in a slot {key}",
                )
            elif policy == "per_region":
                # Disjoint regions run together, so the sweep depth is the
                # busiest region's queue: never below one, never worse than
                # every token in the slot landing on the same region.
                check(
                    1.0 - 1e-9 <= sweeps <= row["microbatch_per_slot"] + 1e-9,
                    f"per_region sweep depth outside [1, microbatch] {key}",
                )
            else:
                check(False, f"unknown amortisation policy {policy!r} {key}")
        check(
            row["resident_kv_bytes"] <= row["kv_capacity_bytes"] + 1.0
            or row["kv_store"] == "hbm",
            f"resident KV exceeds capacity on a feasible point {key}",
        )
        check(row["power_w"] > 0, f"non-positive power {key}")
        check(
            row["thermal_scale"] >= 1.0 - 1e-12,
            f"thermal scale below one {key}",
        )
        fractions = row["area_fractions"]
        check(
            close(sum(fractions.values()), 1.0, tol=1e-9),
            f"area fractions do not sum to one {key}",
        )
        check(
            all(value >= -1e-12 for value in fractions.values()),
            f"negative area fraction {key}",
        )
        if row["family"] == "rom":
            check(
                row["rom_full_array_sweep_time_s"] is not None,
                f"ROM point without a sweep floor {key}",
            )
            # The sweep floor is per slot; a token traverses ``token_slots`` of
            # them, and ``component_times_s`` is the serial path.
            serial_sweep = row["rom_full_array_sweep_time_s"] * row["token_slots"]
            check(
                components["weight_read"] <= serial_sweep * (1 + 1e-9),
                f"ROM weight time above the serial full-array sweep floor {key}",
            )
            check(
                components["weight_read"] >= serial_sweep * (1 - 1e-9),
                f"ROM weight time below the serial full-array sweep floor {key}",
            )

    for row in result["comparisons"]:
        checks += 1
        if row["rom_feasible"] and row["iso_area_gpu_feasible"]:
            if not close(
                row["per_user_speed_ratio"],
                row["rom_per_user_tokens_s"] / row["iso_area_gpu_per_user_tokens_s"],
            ):
                errors.append(f"speed-ratio identity {row['rom_design']}")

    expected_points = 0
    for design in result["designs"]:
        expected_points += len(BATCHES)
    check(
        len(result["points"]) == expected_points,
        f"point matrix incomplete: {len(result['points'])} != {expected_points}",
    )
    check(bool(result["designs"]), "study produced no designs")
    check(
        all(row["silicon_area_mm2"] > 0 for row in result["points"]),
        "a point has no stated silicon area",
    )

    # --- the recommendation is checked, not asserted ---------------------
    # The property is the one whose absence let a wafer be recommended for an
    # 8B model: nothing feasible may beat the recommended design on BOTH
    # per-user rate and rate per mm2 at once.  It is checked here against the
    # raw point list rather than against the frontier the selector built, so a
    # bug in the selector shows up as a failing audit rather than as a
    # self-consistent wrong answer.
    selection = result.get("design_selection") or {}
    by_key = {
        (row["design"], row["model"], row["batch_size"]): row
        for row in result["points"]
    }
    for entry in selection.get("models", []):
        model_name = entry["model"]
        for record in entry["batch_regimes"]:
            batch = record["batch_size"]
            recommended = record["recommended"]
            candidates = _selection_candidates(result["points"], model_name, batch)
            if recommended is None:
                check(
                    not candidates,
                    f"no recommendation offered for {model_name} at batch {batch} "
                    f"although {len(candidates)} designs are feasible",
                )
                continue
            point = by_key.get((recommended["design"], model_name, batch))
            check(
                point is not None and point["feasible"],
                f"recommended design is not a feasible point {model_name} b{batch}",
            )
            if point is None:
                continue
            check(
                close(recommended["per_user_tokens_s"], point["per_user_tokens_s"]),
                f"recommendation restates a rate the point does not have "
                f"{model_name} b{batch}",
            )
            check(
                close(
                    recommended["tokens_s_per_1000mm2"],
                    point["per_user_tokens_s"] / point["silicon_area_mm2"] * 1000.0,
                ),
                f"recommendation density identity {model_name} b{batch}",
            )
            rate = point["per_user_tokens_s"]
            density = _selection_density(point)
            dominators = [
                other["design"]
                for other in candidates
                if other["design"] != point["design"]
                and other["per_user_tokens_s"] >= rate * (1.0 + 1e-9)
                and _selection_density(other) >= density * (1.0 + 1e-9)
            ]
            check(
                not dominators,
                f"recommended design {point['design']} at batch {batch} is "
                f"dominated on both axes by {dominators[:3]}",
            )
            check(
                recommended["max_resident_users"] is not None,
                f"recommendation published without a resident-session count "
                f"{model_name} b{batch}",
            )
        walk = entry.get("marginal_return_walk") or []
        if walk:
            accepted = [rung for rung in walk if rung["accepted"]]
            check(
                bool(accepted) and accepted[-1]["design"] == entry["recommended"]["design"],
                f"the walk's last accepted rung is not the recommendation "
                f"{model_name}",
            )
            check(
                all(
                    rung["marginal_tokens_s_per_1000mm2"] is None
                    or rung["accepted"]
                    == (
                        rung["marginal_tokens_s_per_1000mm2"]
                        > rung["incumbent_average_tokens_s_per_1000mm2"]
                        * MARGINAL_RETURN_BAR
                        * (1.0 + 1e-12)
                    )
                    for rung in walk
                ),
                f"a walk rung's verdict does not follow from its own arithmetic "
                f"{model_name}",
            )
        frontier = entry.get("frontier_batch_1") or []
        if frontier:
            check(
                entry["recommended"]["design"]
                in {row["design"] for row in frontier},
                f"the recommendation is not on the published frontier {model_name}",
            )
    if technology is not None:
        _audit_technology(technology, result, check)

    return {
        "status": "pass" if not errors else "fail",
        "checks_evaluated": checks,
        "errors": errors,
        "scope": [
            "Generated arithmetic identities, area-accounting identities and the "
            "ROM full-array sweep floor only.",
            "A passing audit is not evidence for ROM macro timing, array read "
            "bandwidth at a leading node, NoC timing, package, power delivery, "
            "yield, or model accuracy.",
            "The two validation gates are reported separately and are the only "
            "checks against a shipping part.",
        ],
    }


# --------------------------------------------------------------------------
# anchors
# --------------------------------------------------------------------------


def run_anchors(technology: Technology) -> dict[str, Any]:
    model = ModelProfile.load(ANCHOR_MODEL_PATH)
    hc1 = taalas_hc1_anchor(technology, model)
    a100 = a100_weight_bound_anchor(technology, model)
    # The two POWER gates, in the shape of the two throughput gates above and
    # subject to the same rule: they are reported as an OUTCOME and nothing is
    # tuned to close them.  Both are evaluated at the stated values and at both
    # ends of the whole power band, because every term in that block bar one is
    # `assumed` and two of them multiply.
    a100_power = a100_power_anchor(technology)
    hc1_power = taalas_hc1_power_anchor(technology, model)
    power_band: dict[str, Any] = {}
    for bound in ("low", "stated", "high"):
        variant = technology if bound == "stated" else technology.at_power_bound(bound)
        a_check = a100_power_anchor(variant)
        h_check = taalas_hc1_power_anchor(variant, model)
        power_band[bound] = {
            "a100_tdp_power_w": a_check.modelled_value,
            "a100_ratio_to_published": a_check.ratio,
            "taalas_hc1_card_power_w": h_check.modelled_value,
            "taalas_hc1_ratio_to_published": h_check.ratio,
            "taalas_hc1_ratio_to_band_low": h_check.detail["ratio_to_band_low"],
        }
    sensitivity = []
    for bits in (3.0, 3.5, 4.0, 5.0, 6.0):
        check = taalas_hc1_anchor(technology, model, weight_bits_per_parameter=bits)
        sensitivity.append(
            {
                "weight_bits_per_parameter": bits,
                "modelled_tokens_s": check.modelled_value,
                "ratio_to_published": check.ratio,
                "binding_constraint": check.detail["binding_constraint"],
            }
        )
    context_sensitivity = []
    for context in (1024, 1536, 2048):
        check = taalas_hc1_anchor(technology, model, context_tokens=context)
        context_sensitivity.append(
            {
                "context_tokens": context,
                "modelled_tokens_s": check.modelled_value,
                "ratio_to_published": check.ratio,
                "binding_constraint": check.detail["binding_constraint"],
            }
        )
    return {
        "taalas_hc1": hc1.to_dict(),
        "a100_weight_bound": a100.to_dict(),
        "a100_tdp_power": a100_power.to_dict(),
        "taalas_hc1_card_power": hc1_power.to_dict(),
        "power_gate_band": power_band,
        "power_gate_policy": (
            "Both power gates run at the stated values and at both ends of the "
            "whole power band -- leakage, clock energy, clock frequency, the "
            "array clock multipliers, the clocked-idle floor, the memory-"
            "interface idle floor and the four traffic energies, moved together. "
            "Moving one term at a time would report a sensitivity that is really "
            "a bias. The LINK bands are reported differently and deliberately so "
            "-- each side's fabrics alone and then both together -- because there "
            "the two sides partly cancel and a joint-only interval hid which "
            "side's constants the width came from. NOTHING WAS TUNED TO CLOSE "
            "EITHER GATE: the "
            "A100 gate lands close and the HC1 gate does not, and the asymmetry "
            "between them is the finding rather than an embarrassment. The A100 "
            "gate is also the weaker of the two, because the clock term inside "
            "it was calibrated as a fraction of a shipping GPU's TDP density."
        ),
        "taalas_hc1_weight_bits_sensitivity": sensitivity,
        "taalas_hc1_context_sensitivity": context_sensitivity,
        "gate_policy": (
            "The Taalas HC1 gate is evaluated with the achievable derates because "
            "17,000 tok/s is a product figure. The A100 gate is evaluated on the "
            "ideal roofline with every derate at 1.0 because it is pure arithmetic: "
            "published HBM bandwidth divided by checkpoint bytes."
        ),
    }


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------


def _fmt(value: float | None, spec: str = ",.1f") -> str:
    if value is None or not math.isfinite(value):
        return "—"
    return format(value, spec)


def _fmt_ratio(value: float | None) -> str:
    return "—" if value is None or not math.isfinite(value) else f"{value:.2f}x"


def _fmt_us(value: float | None) -> str:
    if value is None or not math.isfinite(value):
        return "—"
    return f"{value * 1e6:,.2f}"


def _fmt_area(value: float | None) -> str:
    return "—" if value is None else f"{value:,.0f}"


def _render_corrections(result: dict[str, Any]) -> list[str]:
    """What the four completeness corrections cost, from the points themselves.

    A correction that is only described is a correction a reader has to take on
    trust.  Each block below is computed from the same evaluated points as
    every other table in this report.
    """

    points = result["points"]
    lines = [
        "",
        "## What the completeness corrections cost",
        "",
        "Four terms the model priced wrongly or not at all. Each row is",
        "computed from the evaluated points, not restated from prose.",
        "",
        "### 1. Per-region sweep depth: the busiest region, not the mean",
        "",
        "The compute-in-ROM per-region machine used to charge `batch * k /",
        "(N * coverage)` -- the load of the AVERAGE engaged region -- and then",
        "divide it by a flat 0.85 whose own note said the depth is set by the",
        "busiest region. The busiest region is now computed from the routing",
        "distribution. The correction is not a constant: it is a function of",
        "how many users one array pass actually serves.",
        "",
        "**Read the `Users per slot` column, not the batch.** Since per-user",
        "latency was separated from aggregate throughput, a machine cut into",
        "`token_slots` slots spreads its batch across them, and the region",
        "collisions this correction is about happen inside **one** slot. Where",
        "the design the sweep chose has more slots than the batch has users, one",
        "pass serves one user, no two tokens can collide on a region, and the",
        "correction is 1.00x by construction rather than by accident. The",
        "statistic itself is unchanged and is checked against a Monte Carlo of",
        "the routing in `tests/test_roofline.py`; what moved is which point on it",
        "these designs sit at.",
        "",
        "| Model | B | Slots | Users per slot | Mean engaged region | "
        "Busiest region | Correction |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    seen: set[tuple[str, int]] = set()
    for row in points:
        depth = row.get("region_sweep_depth_max_over_mean")
        if depth is None or not row["feasible"]:
            continue
        key = (row["model"], row["batch_size"])
        if key in seen:
            continue
        seen.add(key)
        lines.append(
            f"| {row['model']} | {row['batch_size']} | "
            f"{row['token_slots']:,.0f} | "
            f"{row['microbatch_per_slot']:,.2f} | "
            f"{row['region_sweep_depth_mean_uncorrected']:,.3f} | "
            f"{row['rom_sweeps_per_step']:,.3f} | "
            f"{_fmt_ratio(depth)} |"
        )

    lines.extend(
        [
            "",
            "### 2. Expert-parallel devices: the busiest device, not the mean engaged one",
            "",
            "The same error on the GPU side of the comparison. A routed fetch",
            "finishes when the most loaded device finishes, not when the average",
            "of the engaged ones does. `opentallas.workload` is shared with",
            "`opentallas.analytical` and is unchanged; the correction is applied",
            "in `roofline` and both numbers are carried on every point, because",
            "correcting only the ROM side would be its own bias.",
            "",
            "| Model | B | Devices | Mean engaged | Effective | Correction |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    gpu_seen: set[tuple[str, int, int]] = set()
    for row in points:
        if row["family"] != "gpu" or not row["feasible"]:
            continue
        correction = row["engaged_device_max_over_mean_correction"]
        if correction is None or correction <= 1.0 + 1e-9:
            continue
        key = (row["model"], row["batch_size"], row["device_count"])
        if key in gpu_seen:
            continue
        gpu_seen.add(key)
        lines.append(
            f"| {row['model']} | {row['batch_size']} | {row['device_count']} | "
            f"{row['mean_engaged_devices_uncorrected']:,.2f} | "
            f"{row['engaged_devices']:,.2f} | {_fmt_ratio(correction)} |"
        )

    lines.extend(
        [
            "",
            "### 3. The per-layer serial cost, and who pays it",
            "",
            "Before this term the only latency in the model was",
            "`links.*.hop_latency_s`, charged at inter-partition boundaries -- so",
            "a `single_chip` design had a decode step with no fixed cost at all.",
            "**The asymmetry is the finding and it runs against the ROM thesis:**",
            "a ROM step is tens of microseconds over 32-61 layers while a GPU step",
            "for the same model is milliseconds, so the same per-layer floor is a",
            "large fraction of one and a rounding error on the other.",
            "",
            "| Family | Model | B | Fixed latency (us) | Share of the fastest step |",
            "|---|---|---:|---:|---:|",
        ]
    )
    best_share: dict[tuple[str, str, int], dict[str, Any]] = {}
    for row in points:
        if not row["feasible"]:
            continue
        key = (row["family"], row["model"], row["batch_size"])
        current = best_share.get(key)
        if current is None or row["per_user_tokens_s"] > current["per_user_tokens_s"]:
            best_share[key] = row
    for key in sorted(best_share, key=lambda item: (item[0], item[1], item[2])):
        row = best_share[key]
        if row["batch_size"] != 1:
            continue
        lines.append(
            f"| {row['family']} | {row['model']} | {row['batch_size']} | "
            f"{_fmt_us(row['layer_fixed_latency_s'])} | "
            f"{row['layer_fixed_latency_fraction_of_step']:.1%} |"
        )

    lines.extend(
        [
            "",
            "### 4. KV access granularity, which is a layout choice",
            "",
            "`workload.kv_traffic` counts the bytes the algorithm needs. A memory",
            "moves whole granules, and for a sparse-index model most of the KV",
            "read is a scan of entries far smaller than one granule. Whether that",
            "costs anything is a **layout** decision, so it is stated as one.",
            "",
            "| Model | KV store | Layout | Granule | Inflation |",
            "|---|---|---|---:|---:|",
        ]
    )
    kv_seen: set[tuple[str, str]] = set()
    for row in points:
        key = (row["model"], row["kv_store"])
        if key in kv_seen:
            continue
        kv_seen.add(key)
        lines.append(
            f"| {row['model']} | {row['kv_store']} | {row['kv_index_layout']} | "
            f"{row['kv_access_granularity_bytes']:,.0f} B | "
            f"{_fmt_ratio(row['kv_access_granularity_inflation'])} |"
        )

    lines.extend(
        [
            "",
            "### 5. The SRAM KV path, which is still never exercised",
            "",
            "A reported bound rather than a correction. The step credits ONE user",
            "with the whole array's read bandwidth. That is defensible for KV in a",
            "way it is not for ROM -- KV is written at run time and can be striped",
            "across every bank, whereas an expert's weights live where they were",
            "masked -- but it holds only if the design really stripes, and nothing",
            "in the model checks. The bound below is what the same read costs if a",
            "user can draw only the banks its own footprint occupies.",
            "",
            "| Model | B | Devices | Bank occupancy | KV read as charged (us) | "
            "Under bank locality (us) |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    sram_seen: set[tuple[str, int]] = set()
    for row in points:
        if row["kv_store"] != "sram" or not row["feasible"]:
            continue
        if row["kv_bank_occupancy"] >= 1.0 - 1e-9:
            continue
        key = (row["model"], row["batch_size"])
        if key in sram_seen:
            continue
        sram_seen.add(key)
        lines.append(
            f"| {row['model']} | {row['batch_size']} | {row['device_count']} | "
            f"{row['kv_bank_occupancy']:.2%} | "
            f"{_fmt_us(row['component_times_s']['kv_read'])} | "
            f"{_fmt_us(row['kv_read_s_under_bank_locality'])} |"
        )
    return lines


def _render_power_gates(anchors: dict[str, Any]) -> list[str]:
    """The two power gates, their band, and what each one is worth."""

    a100 = anchors["a100_tdp_power"]
    hc1 = anchors["taalas_hc1_card_power"]
    band = anchors["power_gate_band"]
    low, high = hc1["detail"]["published_band_w"]
    shortfalls = sorted(hc1["detail"]["shortfall_x_against_band"])
    if hc1["detail"]["modelled_tokens_s"] > 0:
        hc1_energy_cell = f"{hc1['detail']['energy_j_per_token']:,.6f} J/token"
        energy_summary = [
            "That is a factor of "
            f"{anchors['a100_weight_bound']['detail']['step']['metrics']['energy_j_per_token'] / hc1['detail']['energy_j_per_token']:,.0f} "
            "in tokens per joule, and **it is a ceiling on the ROM advantage, not "
            "a measurement of it**, for three reasons that all point the same way. "
            "The GPU is at batch 1, which is a GPU's worst operating point -- it "
            "re-reads the whole checkpoint from DRAM for one token, and the "
            "batched rows in the table below are the fair comparison. The ROM "
            "side's read energy is `assumed` over a 17x bracket. And the HC1 "
            f"power gate says this model's ROM total is {shortfalls[0]:.1f}-"
            f"{shortfalls[-1]:.1f}x below the shipping part's published card "
            "power, so the ROM joules here are a lower bound by roughly that factor."
        ]
    else:
        hc1_energy_cell = (
            f"n/a ({hc1['detail']['energy_j_per_token']:,.6f} J/attempt)"
        )
        energy_summary = [
            "No tokens-per-joule ratio is admissible for this pair: the HC1 "
            "throughput reconstruction is capacity-infeasible and delivers zero "
            "modelled tokens. Its energy cell above is the attempted-step energy "
            "inside the diagnostic power calculation, not the energy of a feasible "
            "machine. The power gate remains useful as a disclosed component check, "
            f"and it is {shortfalls[0]:.1f}-{shortfalls[-1]:.1f}x below the "
            "shipping card's published band, but it cannot support an efficiency "
            "advantage."
        ]
    lines = [
        "",
        "### The two power gates, and the residual they leave",
        "",
        "Two gates in the shape of the two above, added because every watt this",
        "program reported was 7-9x low against both published parts and because",
        "`thermal_scale` was exactly 1.0 at every feasible point, so no rate",
        "depended on the energy model at all. **Nothing was tuned to close",
        "either of them.** Six power terms were derived from primitives and",
        "adversarially verified; every one was sent back with a correction, and",
        "the corrections are what is applied. Two of them move power up and two",
        "move it down.",
        "",
        "The A100 gate is evaluated at a **saturating** operating point --",
        f"{a100['detail']['saturating_bytes_s'] / 1e12:,.3f} TB/s of published HBM",
        f"bandwidth and {a100['detail']['roof_ops_s'] / 1e12:,.0f} T ops/s of published",
        f"dense roof at {a100['detail']['clock_frequency_hz'] / 1e6:,.0f} MHz, both at",
        "once -- because a TDP is what a part is built to shed under load, not",
        "what a decode step draws. The HC1 gate is evaluated at exactly the point",
        "its throughput gate already uses, read off that gate's own step so the",
        "two cannot drift apart.",
        "",
        "| Gate | Published | Modelled | Ratio | Result |",
        "|---|---:|---:|---:|---|",
        f"| A100 at TDP, saturating | {_fmt(a100['published_value'])} W | "
        f"{_fmt(a100['modelled_value'])} W | {_fmt_ratio(a100['ratio'])} | "
        f"{'PASS' if a100['passed'] else 'FAIL'} |",
        f"| Taalas HC1 card power | {_fmt(low)}-{_fmt(high)} W | "
        f"{_fmt(hc1['modelled_value'])} W | {_fmt_ratio(hc1['ratio'])} | "
        f"{'PASS' if hc1['passed'] else 'FAIL'} |",
        "",
        "**Where the watts come from.**",
        "",
        "| Term | A100 at TDP | Taalas HC1 |",
        "|---|---:|---:|",
    ]
    a_terms = a100["detail"]["terms_w"]
    h_terms = hc1["detail"]["terms_w"]
    h_dyn = hc1["detail"]["dynamic_power_w_by_term"]
    lines.extend(
        [
            f"| memory / array traffic (weights) | {_fmt(a_terms['hbm_traffic'])} W | "
            f"{_fmt(h_dyn['weight_read_j'])} W |",
            f"| KV traffic | n/a: one saturating HBM stream | "
            f"{_fmt(h_dyn['kv_read_j'])} W |",
            f"| operand delivery | {_fmt(a_terms['operand_delivery'])} W | "
            f"{_fmt(h_dyn['operand_delivery_j'])} W |",
            f"| arithmetic | {_fmt(a_terms['arithmetic'])} W | "
            f"{_fmt(h_dyn['arithmetic_j'])} W |",
            f"| static: leakage | {_fmt(a_terms['static_leakage'])} W | "
            f"{_fmt(h_terms['static_leakage'])} W |",
            f"| static: clock distribution | {_fmt(a_terms['static_clock'])} W | "
            f"{_fmt(h_terms['static_clock'])} W |",
            f"| static: memory-interface idle | "
            f"{_fmt(a_terms['static_memory_interface'])} W | "
            f"{_fmt(h_terms['static_memory_interface'])} W |",
            f"| **static charged** (max of the enumeration and the measured "
            f"clocked-idle floor) | {_fmt(a_terms['static_total_charged'])} W | "
            f"{_fmt(h_terms['static_total_charged'])} W |",
            f"| **total** | {_fmt(a100['modelled_value'])} W | "
            f"{_fmt(hc1['modelled_value'])} W |",
            "",
            "On HC1 the enumerated static power is "
            f"{_fmt(h_terms['static_enumerated'])} W and the measured clocked-idle "
            f"floor is {_fmt(h_terms['static_clocked_idle_floor'])} W, so "
            + (
                "**the floor binds**: the bottom-up enumeration of this part's "
                "leakage and clock tree is below what a shipping clocked device "
                "is measured to draw, and the floor is charged instead. The two "
                "are combined with `max` and never added, because a measured "
                "clocked-idle reading IS mostly leakage and clock tree."
                if h_terms["static_floor_binds"]
                else "the enumeration binds and the floor is inert."
            ),
            "",
            "**The band.** Every term in the power block bar one is `assumed`, and",
            "two of them -- the fabric clock and the array clock multiplier --",
            "multiply, so the gates are reported at both ends of the whole band",
            "with every term moved together. Moving one at a time would report a",
            "sensitivity that is really a bias.",
            "",
            "| Power band | A100 at TDP | Ratio | HC1 card | Ratio to 250 W | Ratio to 200 W |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for bound in ("low", "stated", "high"):
        entry = band[bound]
        lines.append(
            f"| {bound} | {_fmt(entry['a100_tdp_power_w'])} W | "
            f"{_fmt_ratio(entry['a100_ratio_to_published'])} | "
            f"{_fmt(entry['taalas_hc1_card_power_w'])} W | "
            f"{_fmt_ratio(entry['taalas_hc1_ratio_to_published'])} | "
            f"{_fmt_ratio(entry['taalas_hc1_ratio_to_band_low'])} |"
        )
    lines.extend(
        [
            "",
            "**The outcome, stated as an outcome.** The A100 gate lands at "
            f"{_fmt_ratio(a100['ratio'])} of its published TDP. The HC1 gate lands at "
            f"{_fmt_ratio(hc1['ratio'])} of the top of its published band, "
            f"**{1.0 / hc1['ratio']:.2f}x low**, against "
            f"{1.0 / hc1['detail']['ratio_to_band_low']:.2f}x low at the bottom of it. "
            "The asymmetry is the finding and it should not be smoothed over.",
            "",
            "**Why the A100 gate is the weaker of the two, and must not be quoted",
            "as independent.** `power.clock_energy_j_per_mm2_per_cycle` was",
            "calibrated as 20-45% of a shipping GPU's published TDP density. It is",
            "a different GPU -- P100 and GV100 at 16FF+/12FFN, not this part -- but",
            "it is still a GPU TDP, so adding that term to the others and comparing",
            "the sum with a GPU's TDP is partly checking an input against its own",
            "family. What the gate does test is that the traffic terms, the",
            "arithmetic and the static terms are mutually consistent in size, and",
            "it would fail loudly if any were an order of magnitude out. The HC1",
            "gate has no such circularity: nothing on the ROM side was calibrated",
            "on a Taalas figure, because Taalas publishes no microarchitecture and",
            "no energy at all. **It is the stronger gate and it is the one that",
            "fails.**",
            "",
            "**Energy accounting at the two anchors.** Both parts serve the same "
            "workload -- Llama-3.1-8B at batch 1 -- so this is the cleanest "
            "statement the model can make about the ROM argument, and it could "
            "not be made at all until the power terms existed:",
            "",
            "| Part | Energy | W | tok/s |",
            "|---|---:|---:|---:|",
            f"| Taalas HC1 (modelled reconstruction) | "
            f"{hc1_energy_cell} | "
            f"{_fmt(hc1['modelled_value'])} | "
            f"{_fmt(hc1['detail']['modelled_tokens_s'])} |",
            f"| A100 80GB, weight-bound gate, same model and batch | "
            f"{anchors['a100_weight_bound']['detail']['step']['metrics']['energy_j_per_token']:,.6f} J/token | "
            f"{_fmt(anchors['a100_weight_bound']['detail']['step']['power_w'])} | "
            f"{_fmt(anchors['a100_weight_bound']['detail']['step']['per_user_tokens_s'])} |",
            "",
            *energy_summary,
            "",
            "**Where the remaining HC1 shortfall could live, none of it fitted.**",
            "The ROM array is charged its stated leakage density: "
            f"{_fmt(hc1['detail']['rom_array_leakage_charged_w'])} W at the point",
            "and "
            f"{_fmt(hc1['detail']['rom_array_leakage_at_range_high_w'])} W at the",
            "top of its range. The point charge moves the enumerated static",
            "estimate just above the measured clocked-idle floor and is therefore",
            "included in the charged static total. `energy.rom_read_j_per_byte`",
            "moved from 0.5 to 0.08 pJ/B on the evidence, which made this gate",
            "**worse by about 4x on that term alone** and was adopted anyway. The",
            "honest reading is that a compute-in-ROM part's energy has never been",
            "published at any node, and this model's ROM side is built from macros",
            "that are mostly simulated, at 28-130 nm, with boundaries that do not",
            "match the term they are being asked to supply.",
            "",
        ]
    )
    return lines


def _render_power_and_energy(result: dict[str, Any]) -> list[str]:
    """Dark silicon, and what a token costs in joules on each side."""

    block = result.get("power_and_energy")
    if not block:
        return []
    binds = bool(block["thermally_throttled_points"])
    headline = (
        [
            "**The thermal limit binds here, and this is the first version of this",
            "study in which it could.**",
        ]
        if binds
        else [
            "**The thermal limit can bind now, and this is the first version of this",
            "study in which it could -- in this one it does not, and the companion",
            "study at the other node is where it does.**",
        ]
    )
    lines = [
        "",
        "## Power, dark silicon and energy per token",
        "",
        *headline,
        "Static power is charged per mm2 per second whether or not a byte moves,",
        "so the coolable step time solves",
        "`t >= E_dynamic / (cooling_limit - P_static)` rather than dividing the",
        "total energy by the total limit. Under the old rule stretching a step",
        "always reduced modelled power, so every design was coolable at some speed",
        "and `thermal_scale` was exactly 1.0 at all 11,747 feasible points across",
        "both studies.",
        "",
        f"- **{block['thermally_throttled_points']:,} of "
        f"{block['feasible_points']:,} feasible points "
        f"({block['thermally_throttled_fraction'] * 100:.1f}%) are power-limited.**",
        f"- {block['uncoolable_points']:,} points are uncoolable at any speed "
        "(static power alone at or above the cooling budget).",
    ]
    if block["throttled_by_family"]:
        lines.append(
            "- By family: "
            + ", ".join(
                f"{name} {count}"
                for name, count in block["throttled_by_family"].items()
            )
            + "."
        )
        lines.append(
            "- By area class: "
            + ", ".join(
                f"{name} {count}"
                for name, count in block["throttled_by_area_class"].items()
            )
            + "."
        )
        lines.append(
            "- By KV store: "
            + ", ".join(
                f"{name} {count}"
                for name, count in block["throttled_by_kv_store"].items()
            )
            + "."
        )
        lines.append(
            "- By batch: "
            + ", ".join(
                f"B={name} {count}"
                for name, count in block["throttled_by_batch"].items()
            )
            + "."
        )
    lines.extend(["", block["reading"], ""])

    lines.extend(
        [
            "| Family | Area class | Points | Throttled | Median power / budget | "
            "Worst power / budget | Peak W/mm2 | Median static share |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in block["power_headroom_by_area_class"]:
        lines.append(
            f"| {row['family']} | {row['area_class']} | {row['points']:,} | "
            f"{row['throttled']:,} | "
            f"{row['median_power_headroom_fraction'] * 100:.1f}% | "
            f"{row['max_power_headroom_fraction'] * 100:.1f}% | "
            f"{row['max_power_density_w_per_mm2']:.3f} | "
            f"{row['median_static_share_of_power'] * 100:.0f}% |"
        )

    if block["worst_throttled_points"]:
        lines.extend(
            [
                "",
                "### The points that cannot be cooled at full speed",
                "",
                "| Design | Model | B | mm2 | KV | Throttle | Power / budget | "
                "Static share | tok/s | tok/s unthrottled |",
                "|---|---|---:|---:|---|---:|---|---:|---:|---:|",
            ]
        )
        for row in block["worst_throttled_points"]:
            lines.append(
                f"| `{row['design']}` | {row['model']} | {row['batch_size']} | "
                f"{_fmt_area(row['silicon_area_mm2'])} | {row['kv_store']} | "
                f"{row['thermal_scale']:.3f}x | "
                f"{_fmt(row['power_w'])} / {_fmt(row['cooling_limit_w'])} W | "
                f"{row['static_share_of_power'] * 100:.0f}% | "
                f"{_fmt(row['per_user_tokens_s'])} | "
                f"{_fmt(row['per_user_tokens_s_unthrottled'])} |"
            )
        worst = block["worst_throttled_points"][0]
        breakdown = worst["dynamic_energy_breakdown_j"]
        total = sum(breakdown.values()) or 1.0
        lines.extend(
            [
                "",
                "The worst point's dynamic energy is "
                + ", ".join(
                    f"{name.replace('_j', '').replace('_', ' ')} "
                    f"{value / total * 100:.1f}%"
                    for name, value in sorted(
                        breakdown.items(), key=lambda item: -item[1]
                    )
                )
                + ". **The ROM sweep is not what melts it.** A mask-ROM array",
                "reads its weights for almost nothing; what it still pays for, at",
                "the same rate a GPU does, is KV traffic to DRAM. That is an",
                "argument for keeping KV on die, and it is visible here only",
                "because the power model now distinguishes the two.",
            ]
        )

    energy = block["energy_per_token"]
    if energy:
        lines.extend(
            [
                "",
                "### Energy per token, both sides, at equal area",
                "",
                "**This number has been unpublishable until now.** Not paying DRAM",
                "access energy for weights is much of the ROM argument, and the",
                "model could not state it while every watt in it was 7-9x low. The",
                "figures below include the static share amortised over the tokens",
                "the step actually produces, so a machine that is fast and leaky is",
                "not flattered against one that is slow and cool.",
                "",
                block["energy_per_token_selection_rule"],
                "",
                "| Model | B | mm2 | ROM design | ROM J/token | ROM W | ROM binds | "
                "iso-area GPU | GPU J/token | GPU W | GPU binds | ROM tokens/joule |",
                "|---|---:|---:|---|---:|---:|---|---|---:|---:|---|---:|",
            ]
        )
        for row in energy:
            lines.append(
                f"| {row['model']} | {row['batch_size']} | "
                f"{_fmt_area(row['silicon_area_mm2'])} | `{row['rom_design']}` | "
                f"{_fmt(row['rom_energy_j_per_token'], ',.6f')} | "
                f"{_fmt(row['rom_power_w'])} | {row['rom_binds_on']} | "
                f"`{row['gpu_design']}` | "
                f"{_fmt(row['gpu_energy_j_per_token'], ',.6f')} | "
                f"{_fmt(row['gpu_power_w'])} | {row['gpu_binds_on']} | "
                f"{_fmt_ratio(row['tokens_per_joule_advantage_x'])} |"
            )
        lines.extend(
            [
                "",
                "**Read this with the power gates beside it.** The ROM side's energy",
                "rests on `energy.rom_read_j_per_byte`, which is `assumed` over a",
                "17x-wide bracket, and on an operand-delivery scalar that is the",
                "tile-local floor with no long-path ladder in it. The HC1 power gate",
                "says the ROM side's total is several times below a shipping part's",
                "published card power, so **every ROM joule-per-token here is a",
                "lower bound and should be quoted as one.** The GPU side rests on",
                "a measured, peer-reviewed HBM figure and on a gate that lands",
                "within a few percent of a published TDP, so the two sides are not",
                "equally well founded and the ratio inherits the weaker of them.",
                "",
                "**A dense model gives the energy advantage back as batch rises and",
                "a sparse one does not.** A GPU amortises one weight read over the",
                "whole batch, so its joules per token fall roughly as 1/batch until",
                "KV takes over; the ROM part's weight read was already nearly free,",
                "so it has nothing to amortise. On a sparse model the GPU cannot",
                "amortise -- batching engages more experts -- so the ROM advantage",
                "grows instead. Quoting a dense model's batch-1 number without its",
                "batch-256 number beside it is quoting the best case as the case.",
                "",
            ]
        )
    return lines


def _cell(value: Any, spec: str = ",.0f", dash: str = "--") -> str:
    """Format a number for a selection table, or a dash where there is none.

    Deliberately NOT named ``_fmt``.  It was, and being defined later in the
    file it silently shadowed the report's own ``_fmt`` -- whose default is one
    decimal place and whose dash is an em dash -- and quietly reformatted every
    number in every other table, including the Taalas HC1 gate's displayed value.
    ``test_json_csv_and_report_are_mutually_consistent`` caught it because it
    asserts the gate's own value appears in the report it is reported in.  The
    two helpers differ in default precision and in dash, so they must not share
    a name.
    """

    if value is None:
        return dash
    try:
        return format(float(value), spec)
    except (TypeError, ValueError):
        return str(value)


def _array_sampling_lines(result: dict[str, Any]) -> list[str]:
    """Which reticle-array device counts this study actually emitted.

    Printed rather than described, because the holes in this grid are the one
    thing the selection section cannot correct for and a reader has to be able
    to see exactly where they are.
    """

    grid: dict[tuple[str, str, str], set[int]] = {}
    for row in result["points"]:
        if (
            row["family"] != "rom"
            or row["batch_size"] != 1
            or row["weight_amortization"] != SELECTION_AMORTIZATION
            or row["topology_kind"] != "array"
        ):
            continue
        key = (row["model"], row["kv_store"], row["spare_area_policy"])
        grid.setdefault(key, set()).add(int(row["device_count"]))
    if not grid:
        return ["*No reticle-array design was emitted for this study.*", ""]
    lines = [
        "| model | KV store | spare silicon | reticle counts emitted |",
        "| --- | --- | --- | --- |",
    ]
    for (model, kv_store, spare), counts in sorted(grid.items()):
        lines.append(
            f"| {model} | {kv_store.upper()} | {spare} | "
            + ", ".join(str(count) for count in sorted(counts))
            + " |"
        )
    lines.append("")
    return lines


def _render_design_selection(result: dict[str, Any]) -> list[str]:
    """The recommended design per model, the rule that picks it, and the curve.

    This section exists because the report previously named a "best design" by a
    rule -- smallest silicon within 5% of the best per-user rate -- that is
    orthogonal to area and therefore could not stop a 46,225 mm2 wafer being
    recommended for an 8B model that holds in three 815 mm2 reticles.  The rule
    below is stated in the report, applied by the study, and checked by the
    consistency audit.
    """

    selection = result.get("design_selection")
    if not selection:
        return []
    lines: list[str] = [
        "",
        "## The recommended design per model, and the rule that picks it",
        "",
        "**The metric, stated here because a recommendation without its rule is an",
        "opinion.**",
        "",
        f"> {selection['metric']}",
        "",
        f"Why this rule and not another: {selection['why_this_metric']}",
        "",
        f"The bar is `{selection['marginal_return_bar']:g}` -- parity. The frontier is",
        f"taken over the `{selection['amortisation_scope']}` machine, which is what the",
        "main tables show. **The recommendation is not a single number and must not be",
        "quoted as one:** every row below carries per-user rate, aggregate rate,",
        "resident sessions, throughput density, power, energy per token and the",
        "binding constraint together, because a per-user rate published without the",
        "resident-session count beside it is how a one-session latency device gets",
        "read as a server.",
        "",
        f"{selection['iso_area_convention']}",
        "",
    ]

    for entry in selection["models"]:
        model = entry["model"]
        best = entry["recommended"]
        lines.extend([f"### {model} at {entry['context_tokens']:,} tokens", ""])
        if best is None:
            lines.extend(["No feasible ROM design at batch 1.", ""])
            continue
        gpu_count = best.get("iso_area_gpu_device_count")
        lines.extend(
            [
                f"**Recommended: `{best['design'].split('/')[-1]}`** -- "
                f"{best['device_count']:,} x "
                f"{best['silicon_area_mm2_per_device']:,.0f} mm2 "
                f"{'wafer' if best['topology_kind'] == 'wafer' else 'reticle die'}"
                f"{'s' if best['device_count'] != 1 else ''}, "
                f"{best['silicon_area_mm2']:,.0f} mm2 total, "
                f"`{best['parallelism']}`-parallel, KV in "
                f"{best['kv_store'].upper()}, spare silicon to "
                f"`{best['spare_area_policy']}`.",
                "",
                f"- **{best['per_user_tokens_s']:,.1f} tok/s per user** "
                f"({1e3 / best['per_user_tokens_s']:,.2f} ms/token), binding on "
                f"`{best['binding_constraint']}`",
                f"- **{best['tokens_s_per_1000mm2']:,.1f} tok/s per 1,000 mm2** -- the "
                "quantity the rule maximises",
                f"- {best['aggregate_tokens_s']:,.0f} tok/s aggregate with every slot "
                f"full, over {_cell(best['max_resident_users'])} resident session"
                f"{'' if best['max_resident_users'] == 1 else 's'} "
                f"(fill limited by `{best['pipeline_fill_limited_by']}`)",
                f"- {best['power_w']:,.0f} W at "
                f"{best['power_density_w_per_mm2']:.3f} W/mm2, "
                f"{best['energy_j_per_token'] * 1e3:,.1f} mJ/token, thermal scale "
                f"{best['thermal_scale']:.3f}",
                "",
            ]
        )
        if best.get("iso_area_gpu_design"):
            lines.extend(
                [
                    "**Iso-area, at the area the rule chose.** The comparator is "
                    f"{gpu_count:,} copies of one unified HBM die -- "
                    f"`{best['iso_area_gpu_design'].split('/')[-1]}`, "
                    f"{best['iso_area_gpu_silicon_area_mm2']:,.0f} mm2, area ratio "
                    f"{_cell(best.get('iso_area_ratio'), '.4f')} -- running the "
                    f"`{best['iso_area_gpu_parallelism']}` topology it chose for "
                    "itself.",
                    "",
                    "| | ROM | iso-area GPU | ratio |",
                    "| --- | ---: | ---: | ---: |",
                    f"| silicon mm2 | {best['silicon_area_mm2']:,.0f} | "
                    f"{best['iso_area_gpu_silicon_area_mm2']:,.0f} | "
                    f"{_cell(best.get('iso_area_ratio'), '.4f')} |",
                    f"| user tok/s | {best['per_user_tokens_s']:,.1f} | "
                    f"{_cell(best.get('iso_area_gpu_per_user_tokens_s'), ',.1f')} | "
                    f"{_cell(best.get('per_user_speed_ratio'), ',.2f')}x |",
                    f"| aggregate tok/s | {best['aggregate_tokens_s']:,.0f} | "
                    f"{_cell(best.get('iso_area_gpu_aggregate_tokens_s'), ',.0f')} | "
                    f"{_cell(best.get('aggregate_speed_ratio'), ',.2f')}x |",
                    f"| resident sessions | {_cell(best['max_resident_users'])} | "
                    f"{_cell(best.get('iso_area_gpu_max_resident_users'))} | -- |",
                    f"| J/token | {best['energy_j_per_token']:,.4f} | "
                    f"{_cell(best.get('iso_area_gpu_energy_j_per_token'), ',.4f')} | "
                    f"{_cell(best.get('tokens_per_joule_advantage_x'), ',.1f')}x |",
                    "",
                    (
                        "**The areas do not match exactly, and the mismatch is "
                        "stated rather than rounded away.** A GPU cluster is "
                        "quantised in whole dies and a ROM design is not, so at "
                        f"{best['silicon_area_mm2']:,.0f} mm2 the closest whole "
                        f"number of {best['iso_area_gpu_silicon_area_mm2'] / max(1, best['iso_area_gpu_device_count']):,.0f} mm2 "
                        f"dies is {best['iso_area_gpu_device_count']:,}, i.e. "
                        f"{best['iso_area_gpu_silicon_area_mm2']:,.0f} mm2. The "
                        "ROM side is therefore compared against "
                        + (
                            f"{(1.0 / best['iso_area_ratio'] - 1.0) * 100:,.0f}% MORE "
                            "silicon than it has, which makes the ratio "
                            "CONSERVATIVE for the ROM side."
                            if best["iso_area_ratio"] < 1.0
                            else f"{(1.0 - 1.0 / best['iso_area_ratio']) * 100:,.0f}% LESS "
                            "silicon than it has, which makes the ratio "
                            "GENEROUS to the ROM side and it should be read with "
                            "that in mind."
                        )
                        if abs(best["iso_area_ratio"] - 1.0) > 0.02
                        else "The areas match to within 2%, so no granularity "
                        "correction is needed on this row."
                    ),
                    "",
                    "**Read the resident-session row before the ratio row.** A "
                    "per-user rate divided by a per-user rate is a latency claim, "
                    "and a latency claim taken from a machine that holds "
                    f"{_cell(best['max_resident_users'])} session"
                    f"{'' if best['max_resident_users'] == 1 else 's'} against one "
                    f"that holds {_cell(best.get('iso_area_gpu_max_resident_users'))} "
                    "is not the trade it looks like. Where those two numbers are far "
                    "apart the honest reading is the batch-regime table below, not "
                    "this row.",
                    "",
                    "The GPU's own best machine at **any** area is "
                    f"`{str(best.get('fastest_feasible_gpu_design') or '--').split('/')[-1]}` "
                    f"at {_cell(best.get('fastest_feasible_gpu_silicon_area_mm2'))} mm2 "
                    f"and {_cell(best.get('fastest_feasible_gpu_per_user_tokens_s'), ',.1f')} "
                    "tok/s per user, which is the area-free bound and is quoted so the "
                    "iso-area row is not the only comparison on the page.",
                    "",
                ]
            )

        previous = entry.get("previous_rule_choice")
        rejected = entry.get("rejected_per_user_maximum")
        lines.extend(["**Headline before and after.**", ""])
        lines.append(
            "| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | "
            "resident sessions | iso-area ratio |"
        )
        lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: |")
        for label, row in (
            (
                f"before -- smallest within {BEST_DESIGN_TOLERANCE:.0%} of peak rate",
                previous,
            ),
            ("rank on per-user rate alone", rejected),
            ("smallest feasible machine", entry.get("rejected_smallest_feasible")),
            ("**after -- this report's rule**", best),
        ):
            if not row:
                continue
            lines.append(
                f"| {label} | `{row['design'].split('/')[-1]}` | "
                f"{row['silicon_area_mm2']:,.0f} | "
                f"{row['per_user_tokens_s']:,.1f} | "
                f"{row['tokens_s_per_1000mm2']:,.1f} | "
                f"{_cell(row['max_resident_users'])} | "
                f"{_cell(row.get('per_user_speed_ratio'), ',.2f')}x |"
            )
        lines.append("")

        walk = entry.get("marginal_return_walk") or []
        if len(walk) == 1:
            lines.extend(
                [
                    "**There is nothing to walk to.** The frontier is a single row, "
                    "which is what it means for one design to beat every other "
                    "feasible design of this model on BOTH axes at once. No "
                    "trade-off has to be argued and no threshold is doing any work "
                    "here: the recommendation is simply the only non-dominated "
                    "machine. What it beat is in the class table below.",
                    "",
                ]
            )
        elif walk:
            lines.extend(
                [
                    "**The walk, rung by rung.** The number in the `marginal` column is "
                    "what the next slab of silicon returns; the number in `incumbent "
                    "average` is what the silicon already bought returns. The walk stops "
                    "the first time the former is not larger.",
                    "",
                    "| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | "
                    "incumbent average | verdict |",
                    "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
                ]
            )
            for rung in walk:
                lines.append(
                    f"| `{rung['design'].split('/')[-1]}` | "
                    f"{rung['silicon_area_mm2']:,.0f} | "
                    f"{rung['per_user_tokens_s']:,.1f} | "
                    f"{rung['tokens_s_per_1000mm2']:,.1f} | "
                    f"{_cell(rung['marginal_tokens_s_per_1000mm2'], ',.1f')} | "
                    f"{_cell(rung['incumbent_average_tokens_s_per_1000mm2'], ',.1f')} | "
                    f"{'ACCEPT' if rung['accepted'] else 'stop'} |"
                )
            lines.append("")

        frontier = entry.get("frontier_batch_1") or []
        if frontier:
            lines.extend(
                [
                    "**The frontier at batch 1, published in full.** Every design here "
                    "is one that nothing else beats on both axes at once, so a reader "
                    "with a latency target this report does not know about can read "
                    "their own point off it. An honest curve beats a false single "
                    "answer, and the rows above and below the recommendation are the "
                    "ones that show what the rule is doing.",
                    "",
                    "| design | mm2 | devices | user tok/s | aggregate tok/s | "
                    "tok/s per 1,000 mm2 | resident sessions | binds on | W | "
                    "mJ/token | iso-area GPU | ratio |",
                    "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | "
                    "---: | --- | ---: |",
                ]
            )
            for row in frontier:
                mark = " **<-- recommended**" if row["design"] == best["design"] else ""
                lines.append(
                    f"| `{row['design'].split('/')[-1]}`{mark} | "
                    f"{row['silicon_area_mm2']:,.0f} | "
                    f"{row['device_count']:,} | "
                    f"{row['per_user_tokens_s']:,.1f} | "
                    f"{row['aggregate_tokens_s']:,.0f} | "
                    f"{row['tokens_s_per_1000mm2']:,.1f} | "
                    f"{_cell(row['max_resident_users'])} | "
                    f"`{row['binding_constraint']}` | "
                    f"{row['power_w']:,.0f} | "
                    f"{row['energy_j_per_token'] * 1e3:,.1f} | "
                    f"`{str(row.get('iso_area_gpu_design') or '--').split('/')[-1]}` | "
                    f"{_cell(row.get('per_user_speed_ratio'), ',.2f')}x |"
                )
            lines.append("")

        classes = entry.get("class_comparison") or []
        if classes:
            lines.extend(
                [
                    "**Array or wafer, with the losing class's own best machine on "
                    "the page.** A frontier can honestly be a single row -- that is "
                    "what it means for one design to win on both axes at once -- and "
                    "a single row tells a reader nothing about what it beat. Each "
                    "class enters at its own optimum, never at its minimum-feasible "
                    "machine, because comparing against a floor is how a class gets "
                    "beaten by its own under-provisioning rather than by the other "
                    "class.",
                    "",
                    "| class | designs | pick | design | mm2 | user tok/s | "
                    "tok/s per 1,000 mm2 | resident sessions |",
                    "| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |",
                ]
            )
            for record in classes:
                for label, key in (
                    ("densest", "best_by_throughput_density"),
                    ("fastest", "best_by_per_user_rate"),
                    ("smallest", "smallest_feasible"),
                ):
                    row = record[key]
                    lines.append(
                        f"| {record['topology_kind']} | "
                        f"{record['designs_evaluated']:,} | {label} | "
                        f"`{row['design'].split('/')[-1]}` | "
                        f"{row['silicon_area_mm2']:,.0f} | "
                        f"{row['per_user_tokens_s']:,.1f} | "
                        f"{row['tokens_s_per_1000mm2']:,.1f} | "
                        f"{_cell(row['max_resident_users'])} |"
                    )
            lines.append("")

        iso_rows = entry.get("iso_area_by_batch") or []
        if iso_rows:
            lines.extend(_render_iso_area_by_batch(iso_rows))

        regimes = entry.get("regimes") or []
        lines.extend(
            [
                (
                    "**The best design differs by batch, and here is where it "
                    "changes.**"
                    if entry.get("best_design_differs_by_batch")
                    else "**One design wins at every batch this study evaluates.**"
                ),
                "",
                "| batches | design | mm2 | class | KV | resident sessions |",
                "| --- | --- | ---: | --- | --- | ---: |",
            ]
        )
        for regime in regimes:
            batches = regime["batches"]
            span = (
                f"{batches[0]}"
                if len(batches) == 1
                else f"{batches[0]}-{batches[-1]}"
            )
            if regime["design"] is None:
                lines.append(f"| {span} | *no feasible design* | -- | -- | -- | -- |")
                continue
            lines.append(
                f"| {span} | `{regime['design'].split('/')[-1]}` | "
                f"{regime['silicon_area_mm2']:,.0f} | {regime['topology_kind']} | "
                f"{str(regime['kv_store']).upper()} | "
                f"{_cell(regime['max_resident_users'])} |"
            )
        lines.append("")
        lines.extend(
            [
                "Per-user rate falls as the batch rises on a fixed machine, so "
                "`tok/s per 1,000 mm2` at batch B is the same ordering as "
                "`delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly "
                "B times per-user. The rule is therefore the same rule at every "
                "batch, and the design moving is the study telling you the answer "
                "genuinely depends on the operating point, not the metric changing "
                "under it.",
                "",
            ]
        )

    lines.extend(
        [
            "**Where the array class is sampled, so the reader can see the "
            "rungs rather than take them on trust.** Until 2026-09-03 the ROM "
            "array class was sampled only at the device counts each floorplan's "
            "own sizing sweep chose. It is now emitted on an explicit ladder: "
            "multiples of the smallest machine that holds the design "
            f"({', '.join(f'{m:g}x' for m in ARRAY_DEVICE_LADDER_MULTIPLIERS)}) "
            "and the device counts whose silicon equals each wafer rung of "
            "`ROM_AREA_LADDER`, so every wafer design has an array at the same "
            "area. The counts this study actually emitted, per model and per "
            "`(kv_store, spare_area_policy)` combination, are printed below:",
            "",
            *_array_sampling_lines(result),
            "A wafer chosen over the array class is now compared against an "
            "array sampled at the wafer's own area and at four rungs above the "
            "array's floor; the `array @ wafer area` rows in the iso-area "
            "table above are that comparison. The curve BETWEEN rungs is still "
            "not evidence and must not be read as any.",
            "",
        ]
    )
    return lines


def _render_iso_area_by_batch(rows: list[dict[str, Any]]) -> list[str]:
    """The three classes at iso-area, batch by batch, resident sessions on every row."""

    lines = [
        "**Three classes at iso-area, batch by batch.** Each ROM class enters "
        "at its fastest feasible design for that batch and is read against the "
        "GPU comparator at *its own* silicon area (the area ratio is stated). "
        "The `array @ wafer area` row is the fastest reticle array within "
        f"{ISO_AREA_MATCH_TOLERANCE:.0%} of the wafer's silicon, which is the "
        "wafer-versus-array comparison at iso-area. Read resident sessions "
        "before the ratio.",
        "",
        "| batch | class | design | mm2 | user tok/s | aggregate tok/s | "
        "resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user "
        "tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | "
        "J/token ratio |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | "
        "--- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for record in rows:
        batch = record["batch_size"]
        emitted = False
        for klass in record["classes"]:
            row = klass["fastest"]
            emitted = True
            lines.append(_iso_area_line(batch, klass["topology_kind"], row))
        paired = record.get("array_at_wafer_area")
        if paired:
            emitted = True
            lines.append(_iso_area_line(batch, "array @ wafer area", paired))
            lines.append(
                f"| {batch} | wafer reference | "
                f"`{paired['wafer_reference_design'].split('/')[-1]}` | "
                f"{paired['wafer_reference_silicon_area_mm2']:,.0f} | "
                f"{paired['wafer_reference_per_user_tokens_s']:,.1f} | -- | "
                f"{_cell(paired['wafer_reference_max_resident_users'])} | -- | "
                f"{paired['wafer_reference_energy_j_per_token'] * 1e3:,.1f} | -- | "
                f"-- | -- | -- | -- | {paired['area_ratio_to_wafer']:.3f} | "
                f"{_cell(paired.get('per_user_ratio_wafer_over_array'), ',.2f')}x "
                f"wafer/array | -- |"
            )
        if not emitted:
            lines.append(f"| {batch} | -- | *no feasible ROM design* | | | | | | | | | | | | | | |")
    lines.append("")
    return lines


def _iso_area_line(batch: int, label: str, row: dict[str, Any]) -> str:
    gpu = row.get("iso_area_gpu_design")
    return (
        f"| {batch} | {label} | `{row['design'].split('/')[-1]}` | "
        f"{row['silicon_area_mm2']:,.0f} | {row['per_user_tokens_s']:,.1f} | "
        f"{row['aggregate_tokens_s']:,.0f} | {_cell(row['max_resident_users'])} | "
        f"{row['power_w']:,.0f} | {row['energy_j_per_token'] * 1e3:,.1f} | "
        f"`{row['binding_constraint']}` | "
        f"`{str(gpu or '--').split('/')[-1]}` | "
        f"{_cell(row.get('iso_area_gpu_per_user_tokens_s'), ',.1f')} | "
        f"{_cell(row.get('iso_area_gpu_max_resident_users'))} | "
        f"{_cell((row.get('iso_area_gpu_energy_j_per_token') or 0) * 1e3 if row.get('iso_area_gpu_energy_j_per_token') is not None else None, ',.1f')} | "
        f"{_cell(row.get('iso_area_ratio'), '.3f')} | "
        f"{_cell(row.get('per_user_speed_ratio'), ',.2f')}x | "
        f"{_cell(row.get('tokens_per_joule_advantage_x'), ',.1f')}x |"
    )


def _render_hc1_residual(hc1: dict[str, Any]) -> list[str]:
    """What the HC1 throughput gate did, including refusing to run at all.

    This used to be one sentence that divided by the gate's ratio, which is a
    line that works right up until the gate says the shipping part cannot
    exist -- and then crashes rather than reporting the most important result
    the gate has ever produced.  A gate whose failure mode is a traceback is
    not a gate.

    ``modelled_value == 0`` means the anchor design was **infeasible**: the
    model could not place Llama-3.1-8B on 815 mm2 at all, so there is no rate
    to under-predict and no shortfall to back-derive.  That is a stronger
    statement than a missed ratio and it is printed as one.
    """

    ratio = float(hc1["ratio"])
    if ratio > 0:
        return [
            f"The model **under**-predicts the shipping part by "
            f"{1.0 / ratio:.2f}x. Rather than tune the densities until the anchor",
            "is hit, the gate back-derives what each input would have to be for the",
            "model to land exactly on 17,000 tok/s:",
        ]
    reasons = hc1["detail"]["area_split_mm2"].get("reasons") or hc1["detail"][
        "step"
    ].get("reasons") or []
    return [
        "**THE ANCHOR IS INFEASIBLE, AND THAT IS THE RESULT.** The model does not",
        "under-predict the shipping part here -- it cannot place it. Taalas ships",
        "this die; this model says the die cannot hold its own weights. At least one",
        "of the constants below is therefore wrong, and the gate exists to say so",
        "rather than to be closed:",
        "",
        *(f"- {reason}" for reason in reasons),
        "",
        "The candidates, in the order they should be attacked: "
        "`rom.cell_to_sram_cell_area_ratio` and `rom.array_efficiency`, whose",
        "product is now set by one sentence in one paper about a foundry memory",
        "compiler and which together cut ROM capacity density by 2.243x;",
        "`rom.cim_precompute_area_fraction`, taken from a different fabricated part",
        "with a different architecture; `rom.cim_cell_area_multiplier`, for which no",
        "published compute-in-ROM cell exists at any node; and",
        "`reference_parts.taalas_hc1.weight_bits_per_parameter`, whose 3.0-6.0 sweep",
        "the vendor's own 3-bit base type sits at the bottom of. **Nothing here is",
        "tuned to make this gate pass.** The back-derivation below is still printed,",
        "because what each input would have to be is exactly the question a failing",
        "gate asks:",
    ]


def _render_serial_latency(result: dict[str, Any]) -> list[str]:
    """The serial part of the step at the recommended designs, from the operator graph."""

    points = result.get("points") or []
    by_key = {(row["design"], row["batch_size"]): row for row in points}
    lines = [
        "## Serial latency and collectives",
        "",
        "The serial part of every step is the longest path of one token's operator",
        "dependency graph (`src/opentallas/critical_path.py`): the dependent-operator",
        "chain priced with measured RTL depths (ROM) or a published CUDA-graph launch gap",
        "per dependent kernel (GPU), every collective the weight split needs with its",
        "latency and real payload, and every pipeline hop. A hybrid layout's tensor",
        "group and every collective's reduction algorithm are searched per point.",
        "`legacy` is the flat per-layer floor plus two all-reduces per layer this",
        "replaced.",
        "",
        "| Model | Design | Batch | Group | Coll./layer | Algorithms | Chain (us) | Comm. (us) | Sweep (us) | Legacy serial (us) | tok/s/user |",
        "|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|",
    ]
    rows = 0
    for entry in result.get("design_selection", {}).get("models", []):
        best = entry.get("recommended")
        if not best:
            continue
        designs = [best["design"]]
        if best.get("iso_area_gpu_design"):
            designs.append(best["iso_area_gpu_design"])
        for design in designs:
            for batch in (1, 64):
                row = by_key.get((design, batch))
                if row is None or not row.get("feasible") or "serial_chain_s" not in row:
                    continue
                rows += 1
                lines.append(
                    f"| {row['model']} | `{design.split('/')[-1]}` | {batch} | "
                    f"{row['tensor_group']} | {row['collectives_per_layer']:.2f} | "
                    f"{', '.join(row['collective_algorithms']) or '--'} | "
                    f"{row['serial_chain_s'] * 1e6:,.2f} | {row['link_latency_s'] * 1e6:,.2f} | "
                    f"{row['serial_sweep_s'] * 1e6:,.2f} | "
                    f"{(row['legacy_layer_fixed_latency_s'] + row['legacy_link_latency_s']) * 1e6:,.2f} | "
                    f"{_fmt(row['per_user_tokens_s'])} |"
                )
    if not rows:
        return []
    lines.append("")
    return lines


def render_report(result: dict[str, Any], anchors: dict[str, Any]) -> str:
    study_id = result["study_id"]
    derivations = result["technology_derivations"]
    node = derivations["node"]
    a100_power = anchors["a100_tdp_power"]
    hc1_power = anchors["taalas_hc1_card_power"]
    hc1_power_shortfalls = sorted(
        hc1_power["detail"]["shortfall_x_against_band"]
    )
    lines: list[str] = [
        f"# Area-constrained roofline: {study_id}",
        "",
        f"> {result['comparison_contract']}",
        "",
        "Every figure below is produced by `src/opentallas/roofline.py` from",
        "`configs/hardware/technology.json` and the released model profiles. Nothing",
        "here is hand-computed. Silicon area is the primary input; capacity,",
        "bandwidth and compute roof are derived from it.",
        "",
        "## What the model says",
        "",
        *(
            f"{index}. {item}"
            for index, item in enumerate(_findings(result), 1)
        ),
        "",
        *_render_design_selection(result),
        *_render_serial_latency(result),
        "## The overlap and serialisation rule",
        "",
        "```",
        "t_memory  = t_weight + t_kv        weights and KV share one memory system",
        "t_memory  = max(t_weight, t_kv)    weights and KV are separate arrays",
        "t_service = max(t_memory, t_compute)      on the AGGREGATE machine",
        "S         = token_slots * t_service / stage_balance      the sweep a token waits for",
        "t_user    = max(S, longest path of the token's operator graph with S spread",
        "                over its operators by bytes, + every pipeline hop)",
        "t_user   *= thermal_scale",
        "",
        "per_user_tokens_s  = 1 / t_user",
        "aggregate_tokens_s = fill_users / t_user      fill_users = max(batch, slots)",
        "delivered_tokens_s = batch / t_user",
        "```",
        "",
        "Compute overlaps memory. Weight and KV traffic **add** on a GPU because they",
        "contend for the same HBM channels, and **overlap** on a ROM part because the",
        "mask ROM and the KV store are physically separate arrays -- that single rule",
        "is most of the architectural difference and it is stated rather than hidden",
        "in an efficiency factor. Hop and collective latency is **added** to the",
        "critical path at every batch size, because decode is sequential across",
        "layers.",
        "",
        "`t_service` is computed on the machine's **aggregate** resources: all of the",
        "array bandwidth, all of the compute roof. That denominator is correct only",
        "for partitions that are working on the same token at the same instant, which",
        "is what tensor parallelism is. `token_slots = partitions / tensor_group` is",
        "how many independent groups the machine is cut into, and a token is served by",
        "exactly one of them at a time, so its latency is `token_slots` service times",
        "long. **Under pipeline parallelism the two factors cancel exactly** -- each of",
        "N stages holds 1/N of the weights and reads them with 1/N of the bandwidth --",
        "so adding devices buys aggregate throughput and buys one user nothing.",
        "Tensor parallelism is different in kind: every partition is on the same token,",
        "`token_slots` is 1, and the price is every collective the weight split needs,",
        "charged on the token's operator graph (see *Serial latency and collectives*).",
        "",
        "**`aggregate = batch x per-user rate` no longer holds and its removal is the",
        "point.** The aggregate rate is the machine's rate with every slot occupied,",
        "which needs `token_slots` concurrent users; below that the surplus slots idle",
        "and the machine delivers `delivered_tokens_s` instead. The fill is capped by",
        "the users whose KV the machine can hold, reported per point as",
        "`pipeline_fill_limited_by`. Fill and drain are not charged: decode is a",
        "continuous stream of steps and the pipeline is taken to be in steady state,",
        "which flatters a deep pipeline by at most one traversal per request.",
        "",
        "Every point also carries `per_user_tokens_s_throughput_view`: the single",
        "number this study reported for both quantities before they were separated, so",
        "the size of this correction is separable from every other one.",
        "",
        "## Validation gates",
        "",
    ]

    hc1 = anchors["taalas_hc1"]
    a100 = anchors["a100_weight_bound"]
    a100_power = anchors["a100_tdp_power"]
    hc1_power = anchors["taalas_hc1_card_power"]
    power_band = anchors["power_gate_band"]
    requirements = hc1["detail"]["back_derived_requirements"]
    lines.extend(
        [
            "| Gate | Published | Modelled | Ratio | Tolerance | Result |",
            "|---|---:|---:|---:|---:|---|",
            f"| Taalas HC1, Llama-3.1-8B on {_fmt_area(hc1['detail']['die_area_mm2'])} mm2 at "
            f"{hc1['detail']['node']}, per user | {_fmt(hc1['published_value'])} tok/s | "
            f"{_fmt(hc1['modelled_value'])} tok/s | {_fmt_ratio(hc1['ratio'])} | "
            f"within {hc1['tolerance']:.0f}x | {'PASS' if hc1['passed'] else 'FAIL'} |",
            f"| A100 80GB weight-bound, Llama-3.1-8B FP8 batch 1 on "
            f"{_fmt_area(a100['detail']['die_area_mm2'])} mm2 | "
            f"{_fmt(a100['published_value'],',.2f')} tok/s | "
            f"{_fmt(a100['modelled_value'],',.2f')} tok/s | "
            f"{_fmt_ratio(a100['ratio'])} | within {a100['tolerance']*100:.0f}% | "
            f"{'PASS' if a100['passed'] else 'FAIL'} |",
            f"| A100 80GB at its published TDP, saturating load | "
            f"{_fmt(a100_power['published_value'])} W | "
            f"{_fmt(a100_power['modelled_value'])} W | "
            f"{_fmt_ratio(a100_power['ratio'])} | "
            f"within {a100_power['tolerance']:.0f}x | "
            f"{'PASS' if a100_power['passed'] else 'FAIL'} |",
            f"| Taalas HC1 card power at its published operating point | "
            f"{_fmt(hc1_power['detail']['published_band_w'][0])}-"
            f"{_fmt(hc1_power['published_value'])} W | "
            f"{_fmt(hc1_power['modelled_value'])} W | "
            f"{_fmt_ratio(hc1_power['ratio'])} | "
            f"within {hc1_power['tolerance']:.0f}x | "
            f"{'PASS' if hc1_power['passed'] else 'FAIL'} |",
            "",
            f"HC1 binds on `{hc1['detail']['binding_constraint']}`. Its component times are "
            + ", ".join(
                f"{name} {_fmt_us(value)} us"
                for name, value in hc1["detail"]["component_times_s"].items()
            )
            + ".",
            "",
            *_render_hc1_residual(hc1),
            "",
            "| Derived input | This model | Required by the shipping part | Shortfall |",
            "|---|---:|---:|---:|",
            f"| ROM read bandwidth density (B/s/mm2) | "
            f"{requirements['derived_rom_read_bandwidth_density_bytes_s_mm2']:.3e} | "
            f"{requirements['required_rom_read_bandwidth_density_bytes_s_mm2']:.3e} | "
            f"{requirements['rom_density_shortfall_x']:.2f}x |",
            f"| Compute density (ops/s/mm2) | "
            f"{requirements['derived_compute_density_ops_s_mm2']:.3e} | "
            f"{requirements['required_compute_density_ops_s_mm2']:.3e} | "
            f"{requirements['compute_density_shortfall_x']:.2f}x |",
            "",
            "The gate fails before either rate density can bind: the corrected",
            "ROM capacity density and compute-in-ROM floorplan cannot fit the",
            "published model in 815 mm2. The rate diagnostics remain useful --",
            f"ROM read density is {requirements['rom_density_shortfall_x']:.2f}x and",
            f"compute density is {requirements['compute_density_shortfall_x']:.2f}x",
            "the value implied by the shipping rate -- but neither can rescue a",
            "capacity failure. The required ROM read density remains below the SRAM",
            "read-bandwidth density derived from Cerebras WSE-2",
            f"({derivations['sram_read_bytes_s_per_mm2']['value']:.3e} B/s/mm2).",
            "",
            "### The serial-latency band, and why the gate is not fitted",
            "",
            "The serial part of the step is the dependent-operator chain of the",
            "Llama-3.1-8B decode graph (`src/opentallas/critical_path.py`), priced",
            "with this repository's measured RTL depths",
            "(`serial_latency.rom_datapath`). Nothing in it is fitted to this",
            "anchor. Its few assumed inputs -- the clock the RTL is applied at,",
            "the stream-unit share of the compute area, the select units, the",
            "row-access latency -- carry ranges, and the gate is evaluated at both",
            "ends. The flat per-layer floor this chain replaced is shown beside it.",
            "",
            "| Serial chain | Per layer | Per token | Legacy floor per token | Modelled tok/s | Ratio | Binds on |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    band = anchors["taalas_hc1"]["detail"]["layer_fixed_latency_band"]
    for bound in ("low", "stated", "high"):
        entry = band[bound]
        lines.append(
            f"| range {bound} | "
            f"{entry['layer_fixed_latency_s_per_layer'] * 1e9:,.1f} ns/layer | "
            f"{_fmt_us(entry['layer_fixed_latency_s_per_token'])} us | "
            f"{_fmt_us(entry['legacy_floor_s_per_token'])} us | "
            f"{_fmt(entry['modelled_tokens_s'])} | "
            f"{_fmt_ratio(entry['ratio_to_published'])} | "
            f"{entry['binding_constraint']} |"
        )
    closing = band["per_layer_cost_that_would_close_the_gap_s"]
    lines.extend(
        [
            "",
            "The per-layer serial cost that would land the model exactly on the",
            f"published figure is **{closing * 1e9:,.1f} ns/layer**. It is"
            + (
                " negative, which means no positive latency term could close the"
                " gate. The current result is decided earlier by the reported"
                " capacity failure."
                if closing < 0
                else " reported so the distance between the measured chain and"
                " the one the shipping part implies is visible. It is never used"
                " as an input: a chain longer than it means the hardwired"
                " datapath modelled here is serially slower than HC1's."
            ),
            "",
            "### Anchor sensitivity",
            "",
            "| Stored bits/parameter | Modelled tok/s | Ratio | Binds on |",
            "|---:|---:|---:|---|",
        ]
    )
    for row in anchors["taalas_hc1_weight_bits_sensitivity"]:
        lines.append(
            f"| {row['weight_bits_per_parameter']:.1f} | "
            f"{_fmt(row['modelled_tokens_s'])} | {_fmt_ratio(row['ratio_to_published'])} | "
            f"{row['binding_constraint']} |"
        )
    lines.extend(
        [
            "",
            "| Anchor context | Modelled tok/s | Ratio | Binds on |",
            "|---:|---:|---:|---|",
        ]
    )
    for row in anchors["taalas_hc1_context_sensitivity"]:
        lines.append(
            f"| {row['context_tokens']:,} | {_fmt(row['modelled_tokens_s'])} | "
            f"{_fmt_ratio(row['ratio_to_published'])} | {row['binding_constraint']} |"
        )

    lines.extend(_render_power_gates(anchors))
    lines.extend(_render_power_and_energy(result))

    lines.extend(
        [
            "",
            f"## Derived technology at {node}",
            "",
            "These are outputs of the graded primitives, not inputs.",
            "",
            "| Quantity | Value | Grade |",
            "|---|---:|---|",
            f"| SRAM capacity density | "
            f"{derivations['sram_capacity_bits_per_mm2']['value'] / 8e6:,.3f} MB/mm2 | "
            f"{derivations['sram_capacity_bits_per_mm2']['grade']} |",
            f"| ROM capacity density | "
            f"{derivations['rom_capacity_bits_per_mm2']['value'] / 8e6:,.3f} MB/mm2 | "
            f"{derivations['rom_capacity_bits_per_mm2']['grade']} |",
            f"| ROM read bandwidth density | "
            f"{derivations['rom_read_bytes_s_per_mm2']['value'] / 1e9:,.1f} GB/s/mm2 | "
            f"{derivations['rom_read_bytes_s_per_mm2']['grade']} |",
            f"| SRAM read bandwidth density | "
            f"{derivations['sram_read_bytes_s_per_mm2']['value'] / 1e9:,.1f} GB/s/mm2 | "
            f"{derivations['sram_read_bytes_s_per_mm2']['grade']} |",
        ]
    )
    for fmt, entry in derivations["compute_ops_s_per_mm2"].items():
        lines.append(
            f"| Compute density, {fmt} | {entry['value'] / 1e12:,.3f} Tops/s/mm2 | "
            f"{entry['grade']} |"
        )
    lines.extend(
        [
            f"| ROM full-array sweep time | "
            f"{derivations['rom_full_array_sweep_time_s'] * 1e6:,.1f} us | derived |",
            f"| ROM per-token ceiling from that sweep | "
            f"{derivations['rom_full_array_sweep_ceiling_tokens_s']:,.0f} tok/s | derived |",
            f"| ROM per-token ceiling before the read derate | "
            f"{derivations['rom_full_array_sweep_ceiling_tokens_s_before_derate']:,.0f} "
            "tok/s | derived |",
            "",
            derivations["rom_sweep_note"],
            "",
            "## Models and their work",
            "",
            "| Model | Context | Params | Checkpoint | Native bits/param | KV read/token | "
            "KV/user | W:KV at B=1 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for summary in result["model_summaries"]:
        lines.append(
            f"| {summary['model']} | {summary['context_tokens']:,} | "
            f"{summary['total_parameters'] / 1e9:,.0f} B | "
            f"{summary['checkpoint_bytes'] / 1e9:,.1f} GB | "
            f"{summary['native_bits_per_parameter']:.2f} | "
            f"{summary['kv_read_bytes_per_user_token'] / 1e9:,.3f} GB | "
            f"{summary['kv_storage_bytes_per_user'] / 1e9:,.3f} GB | "
            f"{summary['weight_to_kv_read_ratio_b1']:,.1f} |"
        )

    ladder = result.get("latency_correction_ladder") or []
    if ladder:
        lines.extend(
            [
                "",
                "## The latency separation, before and after, at batch 1",
                "",
                "Per-user latency and aggregate throughput used to be one number in",
                "this study. The service time was computed on the machine's",
                "**aggregate** resources -- the throughput view -- and the hops were",
                "added on the single-token path, which is the latency view. A token",
                "under pipeline parallelism is served by one stage's silicon at a time",
                "and has to visit every stage, so its latency is that service time",
                "multiplied by the slot count, not divided by anything.",
                "",
                "**Before** is not a memory of an earlier run. Every point carries",
                "`per_user_tokens_s_throughput_view`, the number the old rule produced,",
                "and each side is ranked by it -- so the before column reproduces the",
                "previous topology choice as well as the previous rate, and the two",
                "corrections stay separable. Both sides are read at the same seven",
                "rungs of silicon.",
                "",
                "| Model | Wafer-eq | mm2 | ROM before | topo | ROM after | topo | ROM /x |"
                " GPU before | topo | GPU after | topo | GPU /x | Ratio before |"
                " Ratio after | Ratio change |",
                "|---|---:|---:|---:|---|---:|---|---:|---:|---|---:|---|---:|---:|---:|---:|",
            ]
        )
        for row in ladder:
            lines.append(
                f"| {row['model']} | {row['wafer_equivalents']} | "
                f"{_fmt_area(row['silicon_area_mm2'])} | "
                f"{_fmt(row['rom_before_tokens_s'])} | "
                f"{row['rom_before_topology']} | "
                f"{_fmt(row['rom_after_tokens_s'])} | "
                f"{row['rom_after_topology']} | "
                f"{_fmt_ratio(row['rom_correction_x'])} | "
                f"{_fmt(row['gpu_before_tokens_s'])} | "
                f"{row['gpu_before_topology']} | "
                f"{_fmt(row['gpu_after_tokens_s'])} | "
                f"{row['gpu_after_topology']} | "
                f"{_fmt_ratio(row['gpu_correction_x'])} | "
                f"{_fmt_ratio(row['ratio_before'])} | "
                f"{_fmt_ratio(row['ratio_after'])} | "
                f"{_fmt_ratio(row['ratio_change_x'])} |"
            )
        changes = [
            row["ratio_change_x"] for row in ladder if row.get("ratio_change_x")
        ]
        if changes:
            lines.extend(
                [
                    "",
                    "**Did the error cancel in the ratio?** If it had, `Ratio change`"
                    " would be 1.00x on every row. It runs from"
                    f" {min(changes):.2f}x to {max(changes):.2f}x across this ladder."
                    " It does not cancel, for the reason the two families reach equal"
                    " area at very different device counts and therefore at very"
                    " different slot counts, and because the correction changes which"
                    " topology each side picks -- a change that lands on whichever"
                    " side was relying on depth.",
                    "",
                ]
            )

    lines.extend(
        [
            "",
            "## Iso-area comparison",
            "",
            "Two ROM designs per operating point -- the **fastest** and the",
            "**smallest silicon that serves the point at all** -- each against the GPU",
            "cluster of the closest equal silicon area. **The area is stated on both",
            "sides.** Where one row appears, the two coincide.",
            "",
            "**Both sides choose their own parallelism.** The GPU cluster is",
            "evaluated under pipeline, tensor and hybrid and the best is reported,",
            "exactly as the ROM side is. `PP-only ratio` is what the same comparison",
            "says when the GPU is allowed pipeline and nothing else.",
            "",
            "`Ratio without the layer cap` is what the comparison says when a token",
            "is allowed to cross more stage boundaries than the model has layers --",
            "which is what this study charged before. That column, not the topology",
            "sweep, is where the previously published ratios came from.",
            "",
            "**`user tok/s` and `aggregate tok/s` are different quantities and no",
            "longer differ by the batch.** `user tok/s` is one user's token rate on",
            "the full serial path through the machine. `aggregate tok/s` is the",
            "machine's total rate with a user in every slot, which needs",
            "`token_slots` concurrent users; where the batch is smaller than that,",
            "the surplus slots idle and what the machine actually delivers at the",
            "stated batch is `batch x user tok/s`, carried per point as",
            "`delivered_tokens_s`. Read the per-user ratio for a latency claim and",
            "the aggregate ratio for a throughput claim; reading either as the other",
            "is the error this study made.",
            "",
            "| Model | B | Pick | ROM design | ROM mm2 | ROM user tok/s | "
            "ROM aggregate tok/s | ROM binds on | GPU | GPU mm2 | Area ratio | "
            "GPU parallelism | GPU link us | GPU user tok/s | GPU aggregate tok/s | "
            "GPU binds on | Per-user ratio | Aggregate ratio | PP-only ratio | "
            "Ratio without the layer cap |",
            "|---|---:|---|---|---:|---:|---:|---|---|---:|---:|---|---:|---:|---:|---|---:|---:|---:|---:|",
        ]
    )
    best_rows = _best_comparisons(result)
    for row in best_rows:
        lines.append(
            f"| {row['model']} | {row['batch_size']} | {row.get('selection', '—')} | "
            f"{row['rom_design']} | "
            f"{_fmt_area(row['rom_silicon_area_mm2'])} | "
            f"{_fmt(row['rom_per_user_tokens_s']) if row['rom_feasible'] else 'infeasible'} | "
            f"{_fmt(row['rom_aggregate_tokens_s']) if row['rom_feasible'] else '—'} | "
            f"{row['rom_binding_constraint']} | {row['iso_area_gpu_design']} | "
            f"{_fmt_area(row['iso_area_gpu_silicon_area_mm2'])} | "
            f"{_fmt_ratio(row['iso_area_ratio'])} | "
            f"{row['iso_area_gpu_parallelism']} | "
            f"{_fmt_us(row['iso_area_gpu_link_latency_s'])} | "
            f"{_fmt(row['iso_area_gpu_per_user_tokens_s']) if row['iso_area_gpu_feasible'] else 'infeasible'} | "
            f"{_fmt(row['iso_area_gpu_aggregate_tokens_s']) if row['iso_area_gpu_feasible'] else '—'} | "
            f"{row['iso_area_gpu_binding_constraint']} | "
            f"{_fmt_ratio(row['per_user_speed_ratio'])} | "
            f"{_fmt_ratio(row['aggregate_speed_ratio'])} | "
            f"{_fmt_ratio(row.get('per_user_speed_ratio_pipeline_only_gpu'))} | "
            f"{_fmt_ratio(row.get('per_user_speed_ratio_without_stage_cap'))} |"
        )

    sensitivity = result.get("link_latency_sensitivity") or []
    if sensitivity:
        stated = {
            (row["model"], round(row["rom_silicon_area_mm2"])): row
            for row in _headline_rows(result)
        }
        by_scope: dict[
            tuple[str, int], dict[tuple[str, str], dict[str, Any]]
        ] = {}
        scope_links: dict[str, list[str]] = {}
        for row in sensitivity:
            key = (row["model"], round(row["rom_silicon_area_mm2"]))
            scope = str(row.get("scope", "joint"))
            by_scope.setdefault(key, {})[(scope, row["bound"])] = row
            scope_links.setdefault(scope, list(row.get("scope_links") or []))

        def _cell(key: tuple[str, int], scope: str) -> str:
            bounds = by_scope.get(key, {})
            low = (bounds.get((scope, "low")) or {}).get("per_user_speed_ratio")
            high = (bounds.get((scope, "high")) or {}).get(
                "per_user_speed_ratio"
            )
            if low is None or high is None:
                return "—"
            return f"{_fmt_ratio(low)} → {_fmt_ratio(high)}"

        def _span(key: tuple[str, int], scope: str) -> float | None:
            bounds = by_scope.get(key, {})
            low = (bounds.get((scope, "low")) or {}).get("per_user_speed_ratio")
            high = (bounds.get((scope, "high")) or {}).get(
                "per_user_speed_ratio"
            )
            if not low or not high:
                return None
            return max(low, high) / min(low, high)

        rom_links = ", ".join(f"`{name}`" for name in scope_links.get("rom", []))
        gpu_links = ", ".join(f"`{name}`" for name in scope_links.get("gpu", []))
        lines.extend(
            [
                "",
                "## The headline is a band, and each side's share of it is "
                "reported apart",
                "",
                "Every hop latency in this model states a range, and the ratio "
                "moves inside it.",
                "This table re-runs the whole study at both ends of those "
                "ranges three ways:",
                f"the **wafer fabric** alone ({rom_links}), which no GPU design "
                "touches; the",
                f"**cluster fabric** alone ({gpu_links}), which is charged to "
                "both families; and",
                "both together.",
                "",
                "**Why three and not one.** This study used to publish the "
                "joint band only. Moving",
                "both sides at once is the right test for a *common-mode* "
                "error, and the wrong one",
                "for asking how much of the uncertainty is ours: the two sides "
                "partly cancel, so the",
                "joint band comes out narrower than the wafer side's own band "
                "and the reader cannot",
                "see that most of the width sits on the side with the weaker "
                "evidence. Reading the",
                "cells: a **low** wafer hop makes the ROM machine faster and "
                "the ratio larger, and a",
                "**low** cluster hop makes the GPU faster and the ratio "
                "smaller, so the two columns",
                "run in opposite directions by construction.",
                "",
                "| Model | ROM mm2 | Ratio stated | Wafer fabric low → high | "
                "Cluster fabric low → high | Both together | Widest one-sided "
                "span |",
                "|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for key in sorted(by_scope, key=lambda item: (item[0], item[1])):
            point = stated.get(key)
            if point is None or point["per_user_speed_ratio"] is None:
                continue
            spans = [
                span
                for span in (_span(key, "rom"), _span(key, "gpu"))
                if span is not None
            ]
            widest = f"{max(spans):,.1f}x" if spans else "—"
            lines.append(
                f"| {key[0]} | {key[1]:,} | "
                f"{_fmt_ratio(point['per_user_speed_ratio'])} | "
                f"{_cell(key, 'rom')} | "
                f"{_cell(key, 'gpu')} | "
                f"{_cell(key, 'joint')} | "
                f"{widest} |"
            )

    clock_rows = result.get("fabric_clock_sensitivity") or []
    if clock_rows:
        # The three CHOSEN designs only -- one column each.  Every area is in
        # the artifact; a report table with thirty-one ratio columns is a
        # table nobody reads.
        chosen = {
            (
                str(entry["model"]),
                round(float(entry["recommended"]["silicon_area_mm2"])),
            ): entry["recommended"]
            for entry in result["design_selection"]["models"]
            if entry.get("recommended")
        }
        labels: list[str] = []
        by_label: dict[str, dict[tuple[str, int], dict[str, Any]]] = {}
        meta: dict[str, dict[str, Any]] = {}
        for row in clock_rows:
            label = str(row["label"])
            if label not in by_label:
                labels.append(label)
                by_label[label] = {}
                meta[label] = row
            by_label[label][
                (row["model"], round(row["rom_silicon_area_mm2"]))
            ] = row
        lines.extend(
            [
                "",
                "## What the fabric clock is worth, and what it is not",
                "",
                "`power.fabric_clock_hz` is `assumed` at 1.0 GHz and it has been read as "
                "setting",
                "the compute roof on both sides. **It does not.** It is read in one place, "
                "`Technology.clock_frequency_hz`, and consumed in one, the clock leg of the "
                "static-power",
                "term; the compute roof comes from `compute.format_roofs_ops_s` over the "
                "anchor die",
                "area, scaled by node logic density, and never reads it. Where it *is* "
                "load-bearing is",
                "the `latency` block: `pipeline_fill_drain_s` (32 fabric cycles) and "
                "`sequencer_issue_decode_s`",
                "(3 fabric cycles) are both derived against it and **neither reads it**, so "
                "moving the",
                "clock alone silently falsifies two constants that sit on every token's "
                "critical path on",
                "both sides. This table moves all three together, which is the only way the "
                "question has",
                "an answer that means anything.",
                "",
                "The last rows are this repository's own **routed ASAP7** blocks, at the "
                "fmax each",
                "artifact records. ASAP7 is a *predictive* academic PDK -- not a foundry "
                "PDK, not",
                "silicon -- and `docs/METHODOLOGY.md` section 9 forbids scaling a frequency "
                "from it to",
                "N6/N5/N7/N4, so those rows are **the size of a question and never a "
                "value**. They are",
                "here because the slowest of them is 17x below the stated clock and a "
                "reader is owed",
                "the measurement of what that would cost rather than an argument about it.",
                "",
                "| Fabric clock | GHz | In stated band | Qwen3-8B fixed latency/token |"
                + "".join(
                    f" {model} @ {area:,} mm2 |"
                    for model, area in sorted(chosen, key=lambda k: (k[0], k[1]))
                    if any(
                        (model, area) in rows_for for rows_for in by_label.values()
                    )
                ),
                "|---|---:|---|---:|"
                + "".join(
                    "---:|"
                    for model, area in sorted(chosen, key=lambda k: (k[0], k[1]))
                    if any(
                        (model, area) in rows_for for rows_for in by_label.values()
                    )
                ),
            ]
        )
        columns = [
            key
            for key in sorted(chosen, key=lambda k: (k[0], k[1]))
            if any(key in rows_for for rows_for in by_label.values())
        ]
        for label in labels:
            info = meta[label]
            cells = "".join(
                (
                    f" {_fmt_ratio(by_label[label][key]['per_user_speed_ratio'])} |"
                    if key in by_label[label]
                    else " — |"
                )
                for key in columns
            )
            lines.append(
                f"| `{label}` | {info['fabric_clock_hz'] / 1e9:,.4f} | "
                f"{'yes' if info['within_stated_band'] else '**no**'} | "
                f"{info['qwen3_8b_layer_fixed_latency_s_per_token'] * 1e6:,.2f} us |"
                + cells
            )

    ratio_rows = result.get("rom_cell_ratio_sensitivity") or []
    if ratio_rows:
        chosen = {
            (
                str(entry["model"]),
                round(float(entry["recommended"]["silicon_area_mm2"])),
            ): entry["recommended"]
            for entry in result["design_selection"]["models"]
            if entry.get("recommended")
        }
        labels = []
        by_label = {}
        meta = {}
        for row in ratio_rows:
            label = str(row["label"])
            if label not in by_label:
                labels.append(label)
                by_label[label] = {}
                meta[label] = row
            by_label[label][
                (row["model"], round(row["rom_silicon_area_mm2"]))
            ] = row
        columns = [
            key
            for key in sorted(chosen, key=lambda k: (k[0], k[1]))
            if any(key in rows_for for rows_for in by_label.values())
        ]
        lines.extend(
            [
                "",
                "## What the ROM bit-cell ratio is worth, executed rather than declared",
                "",
                "`rom.cell_to_sram_cell_area_ratio` decides how much weight fits per mm2, "
                "which",
                "decides how many devices a model needs, which decides mesh diameter, "
                "which is over",
                "half the step time at batch 1. Its stated uncertainty used to be the "
                "prose string",
                "\"1/6 to 1/4\", which nothing ran and which **excluded a measurement this "
                "repository",
                "had already committed** -- 0.1298 at 130 nm. The band is now "
                "0.11-0.33 and every",
                "row below is a full re-run of this study at one ratio, not an "
                "extrapolation.",
                "",
                "The `measured_*` rows are this repository's own bit-cell measurements at "
                "nodes that",
                "are **not** this study's node. `docs/METHODOLOGY.md` section 9 forbids "
                "scaling or",
                "blending a 130 nm or predictive-7 nm open-PDK figure to N6/N5/N7/N4, so "
                "they are the",
                "size of a question and never a value.",
                "",
                "The sign is not obvious and that is why it is run: a **less** dense array "
                "is more ROM",
                "silicon for the same weights and therefore more parallel read bandwidth, "
                "so the",
                "capacity loss and the bandwidth gain pull opposite ways. The binding "
                "constraint on",
                "each side is in the artifact at every point.",
                "",
                "| ROM cell ratio | Value | In stated band | ROM capacity | Full-array "
                "sweep |"
                + "".join(f" {model} @ {area:,} mm2 |" for model, area in columns),
                "|---|---:|---|---:|---:|" + "".join("---:|" for _ in columns),
            ]
        )
        for label in labels:
            info = meta[label]
            cells = "".join(
                (
                    f" {_fmt_ratio(by_label[label][key]['per_user_speed_ratio'])} |"
                    if key in by_label[label]
                    else " \u2014 |"
                )
                for key in columns
            )
            lines.append(
                f"| `{label}` | {info['cell_to_sram_cell_area_ratio']:.4f} | "
                f"{'yes' if info['within_stated_band'] else '**no**'} | "
                f"{info['rom_capacity_bytes_per_mm2'] / 1e6:,.3f} MB/mm2 | "
                f"{info['rom_full_array_sweep_s'] * 1e6:,.1f} us |" + cells
            )

    domain_rows = result.get("nvlink_domain_sensitivity") or []
    if domain_rows:
        best_by_size: dict[tuple[str, int], dict[str, Any]] = {}
        for row in domain_rows:
            key = (row["model"], row["device_count"])
            current = best_by_size.get(key)
            if current is None or row["per_user_tokens_s"] > current["per_user_tokens_s"]:
                best_by_size[key] = row
        widest = max(
            domain_rows,
            key=lambda row: (row["domain_size"], row["wide_domain_size"]),
        )
        lines.extend(
            [
                "",
                "## The NVLink domain is a published number, and there are two of them",
                "",
                f"This study prices an SXM module on a baseboard whose NVLink domain is "
                f"{widest['domain_size']} GPUs, which is what the vendor publishes for "
                "that part. The",
                f"same vendor also ships a {widest['wide_domain_size']}-GPU single-tier "
                "NVLink domain in a rack-scale product built",
                "from a different module. Borrowing the larger domain for this part "
                "would be",
                "choosing an input by its answer, so it is reported here instead. "
                "Batch 1,",
                "best topology at each cluster size.",
                "",
                f"| Model | GPUs | mm2 | Link us at domain {widest['domain_size']} | "
                f"Link us at domain {widest['wide_domain_size']} | tok/s at "
                f"{widest['domain_size']} | tok/s at {widest['wide_domain_size']} |",
                "|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for key in sorted(best_by_size, key=lambda item: (item[0], item[1])):
            row = best_by_size[key]
            lines.append(
                f"| {row['model']} | {row['device_count']:,} | "
                f"{_fmt_area(row['silicon_area_mm2'])} | "
                f"{_fmt_us(row['link_latency_s'])} | "
                f"{_fmt_us(row['wide_domain_link_latency_s'])} | "
                f"{_fmt(row['per_user_tokens_s'])} | "
                f"{_fmt(row['wide_domain_per_user_tokens_s'])} |"
            )

    gpu_choices = [
        row for row in result.get("gpu_topology_choices", []) if row["batch_size"] == 1
    ]
    if gpu_choices:
        lines.extend(
            [
                "",
                "## The GPU's own topology choice, at batch 1",
                "",
                "Every cluster size in the study, under each parallelism it can",
                "actually run, at **per-user** rate. `pipeline` is what this study",
                "charged the GPU before, at every size; `hybrid` is tensor-parallel",
                "inside the NVLink domain and pipeline-parallel across it, which is",
                "what a real deployment of this size runs. A blank cell is a topology",
                "that collapses onto another at that size and is not emitted twice.",
                "",
                "**This table is where the latency separation shows up most",
                "plainly.** A pipeline column is now a machine cut into as many slots",
                "as it has GPUs, and a token visits every one of them; the whole",
                "cluster's HBM bandwidth is on that token's path only under `tensor`,",
                "which is why a 672-GPU pipeline reads as fractions of a token per",
                "second while the same silicon tensor-parallel reads in the hundreds.",
                "",
                "| Model | GPUs | mm2 | Pipeline tok/s | Tensor tok/s | Hybrid tok/s | "
                "Best | Best link us | Link share | Binds on |",
                "|---|---:|---:|---:|---:|---:|---|---:|---:|---|",
            ]
        )
        for row in gpu_choices:
            share = row["best_link_share_of_step"]
            lines.append(
                f"| {row['model']} | {row['device_count']} | "
                f"{_fmt_area(row['silicon_area_mm2'])} | "
                f"{_fmt(row['pipeline_per_user_tokens_s'])} | "
                f"{_fmt(row['tensor_per_user_tokens_s'])} | "
                f"{_fmt(row['hybrid_per_user_tokens_s'])} | "
                f"{row['best_parallelism']} | "
                f"{_fmt_us(row['best_link_latency_s'])} | "
                f"{'—' if share is None else f'{share * 100:.1f}%'} | "
                f"{row['binding_constraint']} |"
            )

    lines.extend(
        [
            "",
            "## Array or wafer: the crossover, reported rather than assumed",
            "",
            "`Array viable to` is the per-user rate at which the topology's hops alone",
            "consume 10% of the token budget; `hard ceiling` is the rate at which they",
            "consume all of it. Below the first number the interconnect is a design",
            "cost; above the second the topology cannot deliver the rate at all.",
            "",
            "Each event is priced on the link it actually crosses and, for a",
            "collective, on how many partitions it spans: an all-reduce costs",
            "`traversals x hop latency` plus `(p-1)/p` of the payload each way, where",
            "`traversals` is `2 lg p` in the fabric's own switch radix (Thakur,",
            "Rabenseifner & Gropp 2005) or 1.1x the mesh diameter on a stitched",
            "fabric (Rocki et al., SC20). `Events` spells the breakdown out.",
            "",
            "| Design | Model | Devices | Parallelism | Intra link | Inter link | "
            "Hops/token | Link latency/token | Viable to (10% budget) | "
            "Hard ceiling | Events |",
            "|---|---|---:|---|---|---|---:|---:|---:|---:|---|",
        ]
    )
    seen_crossovers: set[str] = set()
    for row in result["latency_crossovers"]:
        if row["design"] in seen_crossovers:
            continue
        seen_crossovers.add(row["design"])
        lines.append(
            f"| {row['design']} | {row['model']} | {row['device_count']} | "
            f"{row['parallelism']} | {row.get('intra_link') or row['link']} | "
            f"{row['link']} | {row['hop_events_per_token']:,.0f} | "
            f"{_fmt_us(row['link_latency_s_per_token'])} us | "
            f"{_fmt(row['viable_tokens_s'])} tok/s | "
            f"{_fmt(row['hard_ceiling_tokens_s'])} tok/s | "
            f"{'; '.join(row.get('breakdown') or ()) or '—'} |"
        )

    lines.extend(
        [
            "",
            "## Topology choice at each operating point",
            "",
            "Selection rule: the smallest silicon area within 5% of the best",
            "per-user rate at that point, so a topology cannot win by simply being",
            "given more silicon.",
            "",
            "| Model | B | Winner on rate | Winner per mm2 | Best design | "
            "Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | "
            "Best wafer tok/s (mm2) | Wafer/array | Binds on |",
            "|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in result["topology_choices"]:
        lines.append(
            f"| {row['model']} | {row['batch_size']} | {row['array_or_wafer']} | "
            f"{row.get('array_or_wafer_per_mm2') or '—'} | "
            f"{row.get('best_design') or '—'} | "
            f"{_fmt_area(row.get('best_silicon_area_mm2'))} | "
            f"{_fmt(row.get('best_per_user_tokens_s'))} | "
            f"{_fmt(row.get('best_tokens_s_per_mm2'), ',.3f')} | "
            f"{_fmt(row.get('array_best_per_user_tokens_s'))} "
            f"({_fmt_area(row.get('array_best_silicon_area_mm2'))}) | "
            f"{_fmt(row.get('wafer_best_per_user_tokens_s'))} "
            f"({_fmt_area(row.get('wafer_best_silicon_area_mm2'))}) | "
            f"{_fmt_ratio(row.get('wafer_over_array_ratio'))} | "
            f"{row.get('best_binding_constraint') or '—'} |"
        )

    floorplan = result.get("floorplan_comparison")
    if floorplan:
        storage = floorplan["batched"]
        cim = floorplan["per_region"]
        if storage["feasible"] and cim["feasible"]:
            capacity_summary = (
                "Both machines hold the requested weights. They are different "
                "floorplans, not one floorplan with two arithmetics."
            )
        elif storage["feasible"] and not cim["feasible"]:
            capacity_summary = (
                "The ROM-plus-MAC floorplan holds the requested weights; the "
                f"compute-in-ROM floorplan holds only {cim['capacity_ratio']:.1%} "
                "and is infeasible at this area. The failed floorplan is retained "
                "so the capacity cost of the larger cell remains visible."
            )
        else:
            capacity_summary = (
                "At least one floorplan is capacity-infeasible at this area; the "
                "table reports each capacity ratio instead of treating a clamped "
                "array as if it held the requested weights."
            )
        if storage["feed_ratio"] < 1.0:
            feed_summary = [
                "The ROM-plus-MAC machine is bandwidth-starved: its array supplies",
                f"only {storage['feed_ratio']:.2f}x of the bytes its MAC roof wants,",
                "so some compute capacity cannot be exercised.",
            ]
        else:
            feed_summary = [
                "The ROM-plus-MAC machine is not bandwidth-starved at this point:",
                f"its array supplies {storage['feed_ratio']:.2f}x the bytes its MAC",
                "roof demands, so the fp8 compute block can be fully fed and the",
                "remaining array bandwidth is unused.",
            ]
        lines.extend(
            [
                "",
                "## The two ROM floorplans on one die",
                "",
                f"This probe requests {floorplan['stored_weight_bytes']/1e9:,.2f} GB "
                f"of weights at {floorplan['weight_bits_per_parameter']:g} bits per "
                f"parameter on the same {floorplan['die_area_mm2']:,.0f} mm2. "
                + capacity_summary,
                "",
                "| | ROM + MAC array | compute-in-ROM |",
                "|---|---:|---:|",
                f"| cell area vs a storage-only bit | {storage['cell_area_multiplier']:.1f}x "
                f"| {cim['cell_area_multiplier']:.1f}x |",
                f"| ROM array | {storage['rom_mm2']:,.1f} mm2 | {cim['rom_mm2']:,.1f} mm2 |",
                f"| weight capacity | {storage['weight_capacity_bytes']/1e9:,.2f} GB "
                f"({storage['capacity_ratio']:.1%}) | "
                f"{cim['weight_capacity_bytes']/1e9:,.2f} GB "
                f"({cim['capacity_ratio']:.1%}) |",
                f"| capacity-feasible | {'yes' if storage['feasible'] else '**no**'} | "
                f"{'yes' if cim['feasible'] else '**no**'} |",
                f"| compute block | {storage['compute_mm2']:,.1f} mm2 | "
                f"{cim['compute_mm2']:,.1f} mm2 (pre-compute only) |",
                f"| SRAM | {storage['sram_mm2']:,.1f} mm2 | {cim['sram_mm2']:,.1f} mm2 |",
                f"| sustained fp8 compute roof | {storage['peak_compute_ops_s']:.3e} ops/s | "
                "the array sweep itself |",
                f"| weight bytes/s the roof wants | "
                f"{storage['weight_bytes_s_demanded_by_the_roof']:.3e} | n/a |",
                f"| weight bytes/s the array supplies | "
                f"{storage['weight_read_bytes_s']:.3e} | "
                f"{cim['weight_read_bytes_s']:.3e} |",
                f"| **can the compute block be fed?** | "
                f"**{storage['feed_ratio']:.2f}x** | there is nothing to feed |",
                f"| full-array sweep | {_fmt_us(storage['full_array_sweep_time_s'])} us | "
                f"{_fmt_us(cim['full_array_sweep_time_s'])} us |",
                "",
                "**The sweep is identical.** Both the capacity density and the",
                "read-bandwidth density scale as one over bitcell area, so a larger",
                "compute-in-ROM cell holds proportionally fewer bits AND delivers",
                "proportionally fewer bytes per second: the cell size cancels in",
                "their ratio. What the larger cell costs is capacity -- the same",
                "weights need a bigger array, and that silicon comes out of the SRAM",
                "beside it. An earlier version of this model applied the multiplier",
                "to area alone and credited the result with the storage cell's",
                "bandwidth density, which handed compute-in-ROM a free "
                f"{cim['cell_area_multiplier']:.1f}x on throughput.",
                "",
                *feed_summary,
            ]
        )

    sizing_rows = [
        summary
        for summary in result["model_summaries"]
        if summary.get("per_region_sizing")
    ]
    if sizing_rows:
        lines.extend(
            [
                "",
                "## Sizing one expert region",
                "",
                "The per-region machine's cost is not arithmetic; it is a",
                "pre-compute block and an activation distribution network per",
                "region. The block is small against the array it serves. The",
                "distribution network is the real cost and this model does not",
                "price it.",
                "",
                "| Model | Experts | Routed bytes/expert | One region | Pre-compute/region "
                "| All regions | All pre-compute | Whole checkpoint |",
                "|---|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for summary in sizing_rows:
            sizing = summary["per_region_sizing"]
            lines.append(
                f"| {summary['model']} | {sizing['num_experts']} | "
                f"{sizing['routed_bytes_per_expert']/1e6:,.1f} MB | "
                f"{sizing['region_mm2']:,.1f} mm2 | "
                f"{sizing['precompute_mm2_per_region']:,.2f} mm2 "
                f"({sizing['precompute_fraction_of_array']:.1%}) | "
                f"{sizing['all_regions_mm2']:,.0f} mm2 | "
                f"{sizing['all_precompute_mm2']:,.0f} mm2 | "
                f"{sizing['whole_checkpoint_mm2']:,.0f} mm2 = "
                f"{sizing['whole_checkpoint_reticles']:,.1f} reticles |"
            )

    lines.extend(
        [
            "",
            "## The batch-amortisation fork, reported rather than resolved",
            "",
            "`docs/ANALYTICAL_REPORT.md` names an open",
            "high-batch question the anchor cannot settle. If a ROM cell both stores its bits",
            "and performs the multiply for them -- compute-in-ROM, as Taalas",
            "describes HC1 -- then a second concurrent stream needs a second pass",
            "through the fabric, and **aggregate per-die throughput equals per-user",
            "throughput at every batch**. If instead the ROM is storage feeding a",
            "separate MAC array, one sweep serves the whole batch exactly as one HBM",
            "fetch does on a GPU. Their sweep counts coincide at batch 1, but",
            "their cell size and pre-compute reservation give them different",
            "floorplans; the current compute-in-ROM anchor reconstruction is",
            "capacity-infeasible. A batch-1 rate therefore cannot validate the",
            "distinct high-batch scaling laws.",
            "",
            "Every other table in this report uses the batched (ROM-as-storage)",
            "machine; `-perstream` is compute-in-ROM with a global activation "
            "broadcast and `-perregion` gives each expert region its own port",
            "variant.",
            "",
            "The third column set is the per-region machine, which is the whole",
            "subject of `docs/ANALYTICAL_REPORT.md`: its sweep depth",
            "is the load of the **busiest** expert region, computed from the routing",
            "distribution rather than from the mean engaged region.",
            "",
            "| Model | B | Spare silicon | Batched aggregate | Per-stream aggregate | "
            "Per-region aggregate | Per-stream penalty | Per-region over broadcast | "
            "Batched binds on | Per-stream binds on | Per-region binds on |",
            "|---|---:|---|---:|---:|---:|---:|---:|---|---|---|",
        ]
    )
    for row in result["amortization_fork"]:
        broadcast = row.get("per_stream_aggregate_tokens_s") or 0.0
        region = row.get("per_region_aggregate_tokens_s") or 0.0
        gain = region / broadcast if broadcast > 0 else None
        lines.append(
            f"| {row['model']} | {row['batch_size']} | "
            f"{row['spare_area_policy']} | "
            f"{_fmt(row['batched_aggregate_tokens_s'])} | "
            f"{_fmt(row['per_stream_aggregate_tokens_s'])} | "
            f"{_fmt(row['per_region_aggregate_tokens_s'])} | "
            f"{_fmt_ratio(row.get('per_stream_aggregate_penalty_x'))} | "
            f"{_fmt_ratio(gain)} | "
            f"{row['batched_binding_constraint'] or '—'} | "
            f"{row['per_stream_binding_constraint'] or '—'} | "
            f"{row['per_region_binding_constraint'] or '—'} |"
        )

    sweep_rows = [
        row for row in result.get("floorplan_sweep", []) if row["design"]
    ]
    if sweep_rows:
        lines.extend(
            [
                "",
                "## The floorplan sweep: where the recovered silicon goes",
                "",
                "Compute-in-ROM has no MAC array, so it recovers that silicon.",
                "What it is spent on decides the comparison, so it is swept",
                "rather than assumed, and **the same sweep is offered to the",
                "amortising machine** -- offering it to one side only would move",
                "the artefact rather than remove it.",
                "",
                "* `sram` sizes the array to the stored bytes. Compute-in-ROM's",
                "  spare silicon becomes KV store, which is the split Taalas",
                "  describes; the amortising machine's becomes MAC array.",
                "* `rom` grows the array into that silicon as **replicated copies",
                "  of the same weights**. R copies carry R sets of bitlines and",
                "  sense amps, so R disjoint slices of the weight set are read at",
                "  once and the sweep time falls by R. On the amortising machine",
                "  the MAC array is then sized to consume exactly what the array",
                "  can read, at one weight byte per multiply-accumulate -- a",
                "  derived split, not a swept one.",
                "",
                "`R` is the replication factor the design ended up with, which is",
                "`weight_capacity / stored`. **Areas differ down this table**, so",
                "read `tok/s/mm2` and not only aggregate: a design is allowed to",
                "buy throughput with silicon here, and the iso-area table above is",
                "where that is controlled for.",
                "",
                "| Model | B | Amortisation | Spare | Design | mm2 | R | Sweeps | Aggregate | tok/s/mm2 | Binds on | vs ROM+MAC/sram |",
                "|---|---:|---|---|---|---:|---:|---:|---:|---:|---|---:|",
            ]
        )
        for row in sweep_rows:
            lines.append(
                f"| {row['model']} | {row['batch_size']} | "
                f"{row['weight_amortization']} | {row['spare_area_policy']} | "
                f"{row['design']} | {_fmt_area(row['silicon_area_mm2'])} | "
                f"{row['rom_replication_factor']:,.2f} | "
                f"{row['rom_sweeps_per_step']:,.2f} | "
                f"{_fmt(row['aggregate_tokens_s'])} | "
                f"{row['aggregate_tokens_s_per_mm2']:,.3f} | "
                f"{row['binding_constraint']} | "
                f"{_fmt_ratio(row['vs_reference_floorplan_x'])} |"
            )

    lines.extend(_render_corrections(result))

    lines.extend(
        [
            "",
            "## Sparse-MoE engagement on a ROM machine",
            "",
            "Expected distinct experts touched by a batch is `1 - (1 - k/N)^B`, so the",
            "bytes a step engages grow with batch while the ROM full-array sweep time",
            "does not: an unselected expert's read ports cannot be borrowed, and a",
            "selected one is read once however many batch members chose it. **MoE",
            "sparsity on a ROM machine therefore converts into aggregate throughput,",
            "not into lower per-token latency** -- which is the opposite of what it does",
            "on an HBM machine, where bandwidth is global and sparsity directly",
            "reduces the bytes fetched.",
            "",
            "| Model | B | Expert coverage | Engaged weight bytes | Engaged fraction | "
            "Effective ROM read | Peak ROM read | Per-user tok/s | Aggregate tok/s |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in _engagement_rows(result):
        lines.append(
            f"| {row['model']} | {row['batch_size']} | "
            f"{row['expert_coverage'] * 100:,.2f}% | "
            f"{row['engaged_weight_bytes'] / 1e9:,.1f} GB | "
            f"{row['engaged_weight_fraction'] * 100:,.2f}% | "
            f"{row['effective_weight_read_bytes_s'] / 1e12:,.2f} TB/s | "
            f"{row['peak_weight_read_bytes_s'] / 1e12:,.2f} TB/s | "
            f"{_fmt(row['per_user_tokens_s'])} | {_fmt(row['aggregate_tokens_s'])} |"
        )

    lines.extend(
        [
            "",
            "## Binding constraint census",
            "",
            "| Family | Binding constraint | Points |",
            "|---|---|---:|",
        ]
    )
    census: dict[tuple[str, str], int] = {}
    for row in result["points"]:
        key = (row["family"], row["binding_constraint"] if row["feasible"] else "infeasible")
        census[key] = census.get(key, 0) + 1
    for (family, binding), count in sorted(census.items()):
        lines.append(f"| {family} | {binding} | {count} |")

    infeasible: dict[tuple[str, str], int] = {}
    for row in result["points"]:
        if row["feasible"]:
            continue
        for reason in row["reasons"]:
            infeasible[(row["family"], reason.split(":", 1)[0])] = (
                infeasible.get((row["family"], reason.split(":", 1)[0]), 0) + 1
            )
    if infeasible:
        lines.extend(
            [
                "",
                "Why the infeasible points are infeasible:",
                "",
                "| Family | Reason class | Points |",
                "|---|---|---:|",
            ]
        )
        for (family, reason), count in sorted(infeasible.items()):
            lines.append(f"| {family} | {reason} | {count} |")

    audit = result["consistency_audit"]
    lines.extend(
        [
            "",
            "## Mechanical consistency audit",
            "",
            f"**{audit['status'].upper()}** over {audit['checks_evaluated']:,} checks.",
            "",
        ]
    )
    if audit["errors"]:
        lines.extend(f"- ERROR: {message}" for message in audit["errors"][:50])
        lines.append("")
    lines.extend(f"- {item}" for item in audit["scope"])

    graded = result["graded_inputs"]
    lines.extend(
        [
            "",
            "## Evidence ledger",
            "",
            "| Grade | Inputs |",
            "|---|---:|",
        ]
    )
    for grade in ("measured", "published", "derived", "assumed"):
        lines.append(f"| {grade} | {len(graded.get(grade, []))} |")
    lines.extend(
        [
            "",
            "Every `assumed` input, in full, because an ungraded assumption is the",
            "failure mode this program exists to prevent:",
            "",
        ]
    )
    lines.extend(f"- `{path}`" for path in graded.get("assumed", []))

    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "- No mask-ROM macro has been fabricated at a leading node for this",
            "  program. The ROM capacity density rests on an assumed cell-area ratio",
            "  against a published SRAM bitcell, and the ROM read bandwidth density on",
            "  a *simulated* 28 nm ROM-CIM macro scaled by published bitcell areas.",
            "  Both are named in the evidence ledger above.",
            "- Compute density is charged at a published GPU's whole-die roof per mm2,",
            "  applied to a modelled design's compute-only area. Newer parts are",
            "  denser than the A100 anchor, so this understates a 2026 design.",
            "- Hop latencies are floors. They ignore switch contention, per-hop",
            "  payload queueing beyond the modelled serialisation, and pipeline fill",
            "  at batch 1. Each of those makes an array worse, never better, so the",
            "  reported array crossovers are upper bounds.",
            "- **Power is now enumerated, and it is close on one published part and",
            f"  {hc1_power_shortfalls[0]:.1f}-{hc1_power_shortfalls[-1]:.1f}x low on the other.** Leakage, clock distribution, operand",
            "  delivery and a measured clocked-idle floor are charged per mm2 per",
            "  second whether or not a byte moves, and the HBM traffic energy is a",
            "  measured SC 2025 figure rather than an HBM2-era model. The A100 lands",
            f"  at {a100_power['ratio']:.2f}x of its published TDP under a saturating load; the Taalas HC1",
            f"  lands at {hc1_power['ratio']:.2f}x of its published card power. **The second one FAILS its",
            "  gate and the failure is reported rather than tuned away.** The A100",
            "  gate is also the weaker of the two, because the clock term inside it",
            "  was calibrated as a fraction of a shipping GPU's TDP density -- read",
            "  the power-gate section before quoting it. Every ROM watt and every ROM",
            "  joule-per-token here is a LOWER BOUND by roughly the HC1 gate's",
            "  shortfall.",
            "- **`thermal_scale` now binds, which it never did before.** Static power",
            "  does not fall when a step is stretched, so the coolable step time",
            "  solves `t >= E_dynamic / (cooling_limit - P_static)` rather than",
            "  dividing total energy by the total limit. Some designs are power-",
            "  limited and their rates are reduced accordingly; the power-and-energy",
            "  section names every one of them. Rates on unthrottled points are",
            "  unchanged, so the two validation gates above are untouched by this.",
            "- **Aggregate throughput is reported at steady state with every slot",
            "  occupied, and fill and drain are not charged.** A request that is short",
            "  compared with the slot count pays up to one extra traversal that this",
            "  model does not bill, which flatters a deep pipeline. The delivered rate",
            "  at the requested concurrency is reported separately and is not affected.",
            "- **The weight replication a deep pipeline implies is not charged against",
            "  capacity.** Beyond the layer count the surplus partitions hold replicas",
            "  of a stage, and each replica needs its own copy of that stage's weights;",
            "  the capacity check credits the machine with holding the model once. This",
            "  favours the deepest pipelines, which are on the GPU side of this",
            "  comparison, so correcting it would widen the ROM ratios rather than",
            "  narrow them.",
            "- Prefill, speculative decoding and cost are out of scope for this model.",
            "",
        ]
    )
    return "\n".join(lines)


def _pick_best(rows: list[dict[str, Any]], rate_key: str, area_key: str):
    """Smallest silicon area within 5% of the best per-user rate.

    Selecting on rate alone hands an 8B model a 46,225 mm2 wafer to buy the last
    few percent of a rate it already had on four reticle chips.  The rule is
    stated here and applied everywhere the report says "best".
    """

    feasible = [row for row in rows if row.get(rate_key)]
    if not feasible:
        return rows[0] if rows else None
    best_rate = max(row[rate_key] for row in feasible)
    threshold = best_rate * (1.0 - BEST_DESIGN_TOLERANCE)
    within = [row for row in feasible if row[rate_key] >= threshold]
    return min(within, key=lambda row: (row[area_key], -row[rate_key]))


def _findings(result: dict[str, Any]) -> list[str]:
    """Headline results, every number pulled from the study rather than typed."""

    derivations = result["technology_derivations"]
    node = derivations["node"]
    findings: list[str] = [
        "**The ROM path has a hard per-token ceiling that is a technology "
        "constant, not a design choice.** The full-array sweep time is the ROM "
        "capacity density divided by its read-bandwidth density, so it does not "
        "depend on model size, batch, or expert coverage: "
        f"{derivations['rom_full_array_sweep_time_s'] * 1e6:,.1f} us, or "
        f"{derivations['rom_full_array_sweep_ceiling_tokens_s']:,.0f} tok/s per user. "
        "Under this derivation both densities scale with the same published "
        "bitcell-area ratio, so that ceiling is the same at every node: process "
        "scaling buys a ROM design capacity, not per-token speed.",
    ]

    # The latency separation, stated first because it moved every other number
    # in this report and because the correction is not symmetric between the
    # two families.
    corrections: dict[str, list[dict[str, Any]]] = {"rom": [], "gpu": []}
    for row in result["points"]:
        if row["batch_size"] != 1 or not row["feasible"]:
            continue
        corrections.setdefault(row["family"], []).append(row)
    if corrections["rom"] and corrections["gpu"]:
        parts = []
        for family, label in (("rom", "ROM"), ("gpu", "GPU")):
            rows = corrections[family]
            worst = max(rows, key=lambda row: row["latency_correction_x"])
            winner = _pick_best(rows, "per_user_tokens_s", "silicon_area_mm2")
            parts.append(
                f"On the {label} side the correction reaches "
                f"{worst['latency_correction_x']:,.0f}x "
                f"({worst['design'].split('/')[-1]}, {worst['token_slots']:,.0f} "
                f"slots), and the batch-1 design that now wins -- the smallest "
                f"silicon within "
                f"{BEST_DESIGN_TOLERANCE:.0%} of the best per-user rate, which is "
                "the rule this report has since REPLACED and keeps only to compute "
                "the before/after -- runs "
                f"`{winner['parallelism']}` on "
                f"{winner['device_count']:,} device"
                f"{'s' if winner['device_count'] != 1 else ''}"
            )
        findings.append(
            "**Per-user latency and aggregate throughput are now separate "
            "quantities, and separating them is the largest correction in this "
            "report.** A token under pipeline parallelism is served by one stage's "
            "silicon at a time and must visit every stage, so its latency is the "
            "aggregate service time multiplied by `token_slots`, not divided by "
            "anything. The two factors cancel exactly: **adding devices under "
            "pipeline parallelism buys aggregate throughput and buys one user "
            "nothing.** " + ". ".join(parts) + ". Both validation gates are "
            "single-slot machines and are unchanged to the digit."
        )

    # **The headline is read at the design the study RECOMMENDS, at that
    # design's own area.**  It used to be read at whichever row in the whole
    # comparison table happened to carry the largest ratio, which is a number
    # about the sampling grid rather than about either machine, and at areas
    # where both sides are past their own optimum.
    selection = result.get("design_selection") or {}
    picks = [
        entry for entry in selection.get("models", []) if entry.get("recommended")
    ]
    if picks:
        sentences = []
        for entry in picks:
            best = entry["recommended"]
            ratio = best.get("per_user_speed_ratio")
            sentences.append(
                f"{entry['model']} takes "
                f"{best['device_count']:,} x "
                f"{best['silicon_area_mm2_per_device']:,.0f} mm2 "
                f"({best['silicon_area_mm2']:,.0f} mm2, "
                f"{best['topology_kind']}, KV in {best['kv_store'].upper()}) at "
                f"{best['per_user_tokens_s']:,.0f} tok/s per user and "
                f"{best['tokens_s_per_1000mm2']:,.0f} tok/s per 1,000 mm2, "
                f"holding {_cell(best['max_resident_users'])} session"
                f"{'' if best['max_resident_users'] == 1 else 's'}, "
                f"against {_cell(best.get('iso_area_gpu_device_count'))} copies of "
                "one unified HBM die at the same silicon: "
                f"{_cell(ratio, ',.1f')}x per user"
            )
        classes = {entry["recommended"]["topology_kind"] for entry in picks}
        findings.append(
            "**Each model is recommended one design, by a rule stated in this "
            "report, and the answer is not the same class for all three.** The "
            "rule keeps every design nothing else beats on BOTH per-user tokens/s "
            "and tokens/s per mm2, then walks that frontier from the smallest "
            "feasible machine and stops when the next slab of silicon returns "
            "less than the silicon already bought. "
            + ". ".join(sentences)
            + ". "
            + (
                "Two granularities come out of one rule, which is the point: the "
                "class is chosen per model on evidence rather than assumed."
                if len(classes) > 1
                else "Every model lands in the same class under this rule, which "
                "is a result rather than an assumption."
            )
            + " Ranking on per-user rate alone -- which is what this report used "
            "to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in "
            "three reticle dies."
        )

    batch_one = [
        row
        for row in result["comparisons"]
        if row["batch_size"] == 1
        and row["rom_feasible"]
        and row["iso_area_gpu_feasible"]
        and row["per_user_speed_ratio"] is not None
    ]
    if batch_one:
        top = max(batch_one, key=lambda row: row["per_user_speed_ratio"])
        findings.append(
            "**The largest ratio anywhere in this study is not the study's "
            "result, and it is reported here so nobody has to go looking for "
            f"it.** The maximum batch-1 per-user ratio is {top['model']} on "
            f"{top['rom_silicon_area_mm2']:,.0f} mm2 of ROM silicon at "
            f"{top['rom_per_user_tokens_s']:,.0f} tok/s per user against "
            f"{top['iso_area_gpu_silicon_area_mm2']:,.0f} mm2 of "
            f"{top['iso_area_gpu_design'].split('/')[-1]} at "
            f"{top['iso_area_gpu_per_user_tokens_s']:,.0f} tok/s: "
            f"**{top['per_user_speed_ratio']:,.1f}x**, ROM binding on "
            f"`{top['rom_binding_constraint']}` and the GPU on "
            f"`{top['iso_area_gpu_binding_constraint']}`. It holds "
            f"{_cell(top.get('rom_max_resident_users'))} resident session"
            f"{'' if top.get('rom_max_resident_users') == 1 else 's'} against the "
            f"GPU cluster's {_cell(top.get('iso_area_gpu_max_resident_users'))}. "
            "A maximum over a sampling grid is a fact about the grid; the "
            "recommended-design ratios above are the ones this report stands "
            "behind."
        )

    symmetry = [
        row
        for row in result["comparisons"]
        if row["batch_size"] == 1
        and row["rom_feasible"]
        and row["iso_area_gpu_feasible"]
        and row.get("per_user_speed_ratio_without_stage_cap") is not None
        and row.get("per_user_speed_ratio") is not None
        # Read the cap off a comparator it actually binds on. Once per-user
        # latency is charged honestly the iso-area GPU usually picks a tensor
        # group, which has one stage and no boundary for the cap to remove, and
        # quoting that row would describe the correction with a machine it does
        # not apply to.
        and row["iso_area_gpu_pipeline_stages_uncapped"]
        > row["iso_area_gpu_pipeline_stages"]
    ]
    if symmetry:
        # The largest absolute fall, which is the one a headline is read off,
        # rather than the largest proportional one, which on this study is a
        # model where the GPU wins either way and the fall is 1.4x of nothing.
        worst = max(
            symmetry,
            key=lambda row: row["per_user_speed_ratio_without_stage_cap"]
            - row["per_user_speed_ratio"],
        )
        findings.append(
            "**A token cannot cross more stage boundaries than the model has "
            "layers, and charging it as though it could was most of the reported "
            "advantage at scale.** At "
            f"{worst['rom_silicon_area_mm2']:,.0f} mm2 on {worst['model']} at batch 1, "
            f"the iso-area GPU cluster is "
            f"{worst['iso_area_gpu_device_count']:,} devices. Cut as one serial "
            f"pipeline that is "
            f"{worst['iso_area_gpu_pipeline_stages_uncapped']:,} stages and "
            f"{worst['iso_area_gpu_link_latency_without_stage_cap_s'] * 1e6:,.0f} us "
            "of link latency per token; but the model has "
            f"{[m for m in result['model_summaries'] if m['model'] == worst['model']][0]['num_layers']} "
            "layers, so at most "
            f"{worst['iso_area_gpu_pipeline_stages']} of those boundaries can exist "
            "and the rest of the silicon is replication, which adds bandwidth and no "
            f"serial event: {worst['iso_area_gpu_link_latency_s'] * 1e6:,.0f} us. The "
            "iso-area per-user ratio at that point falls from "
            f"{worst['per_user_speed_ratio_without_stage_cap']:,.1f}x to "
            f"{worst['per_user_speed_ratio']:,.1f}x. The same cap is applied to the "
            "ROM side, where it is worth more still because a twelve-wafer machine "
            "spans 681 reticle fields."
        )

    if not symmetry:
        findings.append(
            "**The layer cap on serial stage boundaries is still applied and is "
            "no longer visible in the headline, because no comparator it binds on "
            "wins any more.** A token cannot cross more stage boundaries than the "
            "model has layers, and this study charges at most that many. With "
            "per-user latency separated from aggregate throughput, both families "
            "now pick a topology with a tensor group at batch 1, and a tensor "
            "group has one stage and no boundary for the cap to remove. The "
            "`Ratio without the layer cap` column in the iso-area table therefore "
            "equals the stated ratio wherever the winner is tensor-parallel; it "
            "still differs wherever a pipeline wins."
        )

    choice = [
        row
        for row in result["comparisons"]
        if row["batch_size"] == 1
        and row["rom_feasible"]
        and row["iso_area_gpu_feasible"]
        and row.get("topology_choice_gain") is not None
    ]
    if choice:
        best_gain = max(choice, key=lambda row: row["topology_choice_gain"])
        gain = best_gain["topology_choice_gain"]
        if gain > 1.01:
            findings.append(
                "**Letting the GPU choose its own parallelism is worth up to "
                f"{gain:.2f}x to it.** At "
                f"{best_gain['rom_silicon_area_mm2']:,.0f} mm2 on "
                f"{best_gain['model']} the pipeline-only GPU delivers "
                f"{best_gain['pipeline_only_gpu_per_user_tokens_s']:,.2f} tok/s and "
                f"the same silicon running "
                f"{best_gain['iso_area_gpu_parallelism']} delivers "
                f"{best_gain['iso_area_gpu_per_user_tokens_s']:,.0f} tok/s."
            )
        else:
            findings.append(
                "**Giving the GPU the same topology sweep the ROM side gets is worth "
                f"at most {gain:.2f}x to it at this batch.** Pipeline, tensor and "
                "hybrid are evaluated at every cluster size and the best is taken. "
                "Where the gain is small the cluster is small enough that its single "
                "stage already holds the model."
            )

    high_batch = [
        row
        for row in result["comparisons"]
        if row["batch_size"] == max(BATCHES)
        and row["rom_feasible"]
        and row["iso_area_gpu_feasible"]
        and row["aggregate_speed_ratio"] is not None
    ]
    if high_batch:
        worst = min(high_batch, key=lambda row: row["aggregate_speed_ratio"])
        best = max(high_batch, key=lambda row: row["aggregate_speed_ratio"])
        findings.append(
            "**The advantage erodes with batch, and the erosion is a KV effect.** "
            f"At batch {max(BATCHES)} the aggregate ratio at equal area spans "
            f"{worst['aggregate_speed_ratio']:.2f}x ({worst['model']}, ROM binding on "
            f"`{worst['rom_binding_constraint']}`) to "
            f"{best['aggregate_speed_ratio']:.2f}x ({best['model']}, ROM binding on "
            f"`{best['rom_binding_constraint']}`). Weight traffic is what ROM "
            "removes; KV traffic it does not, and KV traffic is what grows with "
            "batch."
        )

    engagement = _engagement_rows(result)
    for low in [
        row
        for row in engagement
        if row["expert_coverage"] < 0.1 and row["batch_size"] == 1
    ]:
        high = next(
            (
                row
                for row in engagement
                if row["model"] == low["model"]
                and row["batch_size"] == max(BATCHES)
            ),
            None,
        )
        if high is None:
            continue
        findings.append(
            "**Sparse MoE buys aggregate throughput on a ROM machine, not "
            f"latency.** {low['model']} engages "
            f"{low['engaged_weight_fraction'] * 100:.1f}% of its ROM array at batch 1 "
            f"and {high['engaged_weight_fraction'] * 100:.1f}% at batch "
            f"{high['batch_size']}, while the weight-read time is identical at both. "
            f"What the machine delivers rises from "
            f"{low['delivered_tokens_s']:,.0f} to {high['delivered_tokens_s']:,.0f} "
            f"tok/s, and its rate with every slot occupied from "
            f"{low['aggregate_tokens_s']:,.0f} to {high['aggregate_tokens_s']:,.0f}. "
            "The second rises far less than the first because the batch-1 figure "
            "is already a full-machine number -- this design has "
            f"{low['token_slots']:,.0f} slots -- so most of what batching adds "
            "there is coverage rather than occupancy. An unselected expert's read "
            "ports cannot be borrowed, so its idle bandwidth is only recovered by "
            "giving the sweep more users."
        )
        break

    wafer_wins = sum(
        1
        for row in result["topology_choices"]
        if row.get("array_or_wafer") == "wafer"
    )
    array_wins = sum(
        1
        for row in result["topology_choices"]
        if row.get("array_or_wafer") == "array"
    )
    tensor_nvlink = [
        row
        for row in result["latency_crossovers"]
        if row["parallelism"] == "tensor"
        and str(row.get("intra_link", "")).startswith("nvlink")
        and row["hard_ceiling_tokens_s"] is not None
    ]
    tensor_wafer = [
        row
        for row in result["latency_crossovers"]
        if row["parallelism"] == "tensor"
        and str(row.get("intra_link", "")).startswith("on_wafer")
        and row["hard_ceiling_tokens_s"] is not None
    ]
    wafer_per_mm2 = sum(
        1
        for row in result["topology_choices"]
        if row.get("array_or_wafer_per_mm2") == "wafer"
    )
    array_per_mm2 = sum(
        1
        for row in result["topology_choices"]
        if row.get("array_or_wafer_per_mm2") == "array"
    )
    if tensor_nvlink and tensor_wafer:
        wafer_ceiling = min(row["hard_ceiling_tokens_s"] for row in tensor_wafer)
        nvlink_ceiling = min(row["hard_ceiling_tokens_s"] for row in tensor_nvlink)
        # Like for like: the same model's collective on one wafer against the
        # same model's collective on NVLink.  Comparing the two worst cases
        # would compare different machines.
        matched: list[float] = []
        for wafer_row in tensor_wafer:
            if wafer_row["device_count"] != 1:
                continue
            peer = next(
                (
                    row
                    for row in tensor_nvlink
                    if row["model"] == wafer_row["model"]
                ),
                None,
            )
            if peer and wafer_row["link_latency_s_per_token"] > 0:
                matched.append(
                    peer["link_latency_s_per_token"]
                    / wafer_row["link_latency_s_per_token"]
                )
        advantage = min(matched) if matched else float("nan")
        findings.append(
            "**Tensor parallelism is better on a wafer than on NVLink and is not "
            "good anywhere, and the published claim that it reaches Taalas-class "
            "rates on-wafer is RETRACTED.** Two all-reduces per layer per token "
            "cost up to "
            f"{max(row['link_latency_s_per_token'] for row in tensor_nvlink) * 1e6:,.0f} us "
            "over NVLink, capping per-user decode at "
            f"{nvlink_ceiling:,.0f} tok/s before any arithmetic happens; the same "
            "collectives on-wafer cost at most "
            f"{max(row['link_latency_s_per_token'] for row in tensor_wafer) * 1e6:,.1f} us "
            f"and cap it at {wafer_ceiling:,.0f} tok/s. The ordering survives, and "
            "on a like-for-like comparison -- the same model's collective on one "
            f"wafer against the same model's on NVLink -- the wafer is at least "
            f"{advantage:,.1f}x cheaper. But the previous figures of 116,278 and "
            "81,966 tok/s came from charging a stitched 2-D mesh one flat hop "
            "however many reticle fields the collective spanned. A mesh has no "
            "switch, so an all-reduce costs about 1.1 times its diameter, and the "
            "model now charges that. What the collective buys is what makes it "
            "worth paying: with per-user latency separated from aggregate "
            "throughput, a tensor group is the only arrangement that puts the "
            "whole machine on one token, and the topology tables below show both "
            "families choosing one at batch 1 in spite of this cost."
        )
    findings.append(
        "**Which topology wins depends entirely on what is being maximised, and "
        "the study reports both rather than choosing.** On per-user rate at equal "
        f"area a wafer wins {wafer_wins} of {len(result['topology_choices'])} "
        f"operating points and an array {array_wins}; on tokens per second per "
        f"square millimetre the same points go {array_per_mm2} to the array and "
        f"{wafer_per_mm2} to the wafer. A wafer is not faster per unit silicon -- "
        "it is faster because it is more silicon, plus a hop latency an array "
        "cannot match."
    )

    feasible = sum(1 for row in result["points"] if row["feasible"])
    kv_bound = sum(
        1
        for row in result["points"]
        if row["feasible"] and row["binding_constraint"] == "kv_read"
    )
    findings.append(
        "**A wafer has less die edge per unit area than the same area of separate "
        "dies, and that is an argument against it.** Perimeter grows as the square "
        "root of area, so HBM beachfront -- and therefore KV bandwidth -- does not "
        "scale with wafer area the way compute and ROM capacity do. This model "
        "charges both sides the same edge utilisation a shipping GPU achieves, and "
        f"the consequence shows up wherever a design binds on `kv_read`: {kv_bound} "
        f"of {feasible} feasible points."
    )

    fork = [
        row
        for row in result.get("amortization_fork", [])
        if row.get("per_stream_aggregate_penalty_x") is not None
        and row["batch_size"] == max(BATCHES)
    ]
    if fork:
        worst = max(fork, key=lambda row: row["per_stream_aggregate_penalty_x"])
        findings.append(
            "**The largest open question is not in this model's inputs but in the "
            "architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both "
            "stores and multiplies, each concurrent stream needs its own pass and "
            "aggregate per-die throughput never exceeds the per-user rate. At batch "
            f"{max(BATCHES)} that costs up to "
            f"{worst['per_stream_aggregate_penalty_x']:,.1f}x of aggregate "
            f"throughput ({worst['model']}). Their sweep counts coincide at batch 1, "
            "but their cell and pre-compute costs make their floorplans different; "
            "the current compute-in-ROM anchor reconstruction fails capacity. A "
            "batch-1 validation therefore cannot establish either high-batch law."
        )
        # Scanned over every batch, not only the largest: the per-region gain
        # peaks in the middle of the range and reporting only batch 256 would
        # miss it.
        regional = [
            row
            for row in result.get("amortization_fork", [])
            if row.get("per_region_aggregate_tokens_s")
            and row.get("per_stream_aggregate_tokens_s")
            and row.get("batched_aggregate_tokens_s")
        ]
        if regional:
            def _gain(row: dict[str, Any]) -> float:
                return (
                    row["per_region_aggregate_tokens_s"]
                    / row["per_stream_aggregate_tokens_s"]
                )

            best = max(regional, key=_gain)
            best_depth = max(
                (
                    row["region_sweep_depth_max_over_mean"]
                    for row in result["points"]
                    if row["model"] == best["model"]
                    and row["batch_size"] == best["batch_size"]
                    and row.get("region_sweep_depth_max_over_mean")
                ),
                default=1.0,
            )
            loses = [
                row
                for row in regional
                if row["per_region_aggregate_tokens_s"]
                < row["batched_aggregate_tokens_s"] * (1 - 1e-9)
            ]
            findings.append(
                "**A third machine sits between them, and for a sparse model it "
                "recovers part of what compute-in-ROM gives up -- less than the "
                "mean-region arithmetic used to say.** Give each expert region its "
                "own activation port and two tokens selecting disjoint experts "
                "drive disjoint regions at the same time; only the tokens landing "
                "on one region serialise, and the sweep waits for the BUSIEST "
                "region rather than the average engaged one. The largest gain over "
                f"a global broadcast is {_gain(best):,.2f}x, on {best['model']} at "
                f"batch {best['batch_size']}, where the busiest region carries "
                f"{best_depth:,.2f}x the load of the mean engaged one. It is not "
                "free ground: per-region "
                f"still loses to the amortising ROM-plus-MAC machine at "
                f"{len(loses)} of {len(regional)} operating points. A dense model "
                "has one region, so it gains nothing -- the disjointness is what "
                "sparsity buys."
            )

    findings.append(
        "**Every number here is conditional on the assumed inputs listed in the "
        "evidence ledger below.** The ROM cell-area ratio and the ROM read "
        "bandwidth density are the two that move the answer most, and neither has "
        f"been measured at {node}."
    )
    power = result.get("power_and_energy") or {}
    if power.get("thermally_throttled_points"):
        worst = power["worst_throttled_points"][0]
        breakdown = worst["dynamic_energy_breakdown_j"]
        total = sum(breakdown.values()) or 1.0
        biggest = max(breakdown, key=lambda name: breakdown[name])
        findings.append(
            "**The cooling limit binds, and not where a uniform correction said "
            f"it would.** {power['thermally_throttled_points']:,} of "
            f"{power['feasible_points']:,} feasible points "
            f"({power['thermally_throttled_fraction'] * 100:.1f}%) are "
            "power-limited now that leakage, clock distribution and a measured "
            "clocked-idle floor are charged per mm2 per second rather than per "
            "byte moved. The worst is "
            f"`{worst['design']}` at batch {worst['batch_size']} on "
            f"{worst['silicon_area_mm2']:,.0f} mm2, throttled "
            f"{worst['thermal_scale']:.2f}x from "
            f"{worst['per_user_tokens_s_unthrottled']:,.0f} to "
            f"{worst['per_user_tokens_s']:,.0f} tok/s per user. **No wafer is "
            "throttled anywhere in this study**: a ROM sweep is a fixed cost "
            "spread over far more silicon, so wafer-scale is power-sparse. And "
            f"{worst['kv_store'].upper()} KV is what melts the arrays -- the "
            f"worst point's dynamic energy is {breakdown[biggest] / total * 100:.0f}% "
            f"{biggest.replace('_j', '').replace('_', ' ')} against "
            f"{breakdown['weight_read_j'] / total * 100:.1f}% weight read. The ROM "
            "sweep is not what melts it."
        )
    elif power:
        findings.append(
            "**No point in this study is power-limited.** Static power is charged "
            "per mm2 per second, so this is a statement about the designs rather "
            "than an artifact of a traffic-proportional energy model: the worst "
            "point here reaches "
            f"{max(row['max_power_headroom_fraction'] for row in power['power_headroom_by_area_class']) * 100:.0f}% "
            "of its cooling budget. The companion study at the other node does "
            "have power-limited points."
        )
    return findings


def _engagement_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    """One ROM row per (model, batch) chosen consistently, to expose engagement.

    The design is held fixed across the batch sweep -- the smallest feasible
    HBM-KV array at batch 1 -- so the table shows what the *batch* does rather
    than what a different machine does.
    """

    rows: list[dict[str, Any]] = []
    order = _model_order(result)
    for model_name in order:
        candidates = [
            row
            for row in result["points"]
            if row["model"] == model_name
            and row["family"] == "rom"
            and row["weight_amortization"] == "batched"
            and row["kv_store"] == "hbm"
            and row["batch_size"] == 1
            and row["feasible"]
        ]
        if not candidates:
            continue
        design = min(candidates, key=lambda row: row["silicon_area_mm2"])["design"]
        for row in result["points"]:
            if row["design"] == design and row["model"] == model_name:
                rows.append(row)
    return sorted(rows, key=lambda row: (order[row["model"]], row["batch_size"]))


def _best_comparisons(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Two rows per (model, batch): the fastest ROM design and the smallest one.

    Reporting only the fastest lets a topology win by being handed more silicon;
    reporting only the smallest hides the rate a bigger machine actually buys.
    Both are emitted, each against its own equal-area GPU cluster, which is what
    "state the area on both sides" is for.
    """

    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in result["comparisons"]:
        grouped.setdefault((row["model"], row["batch_size"]), []).append(row)
    chosen: list[dict[str, Any]] = []
    for rows in grouped.values():
        feasible = [row for row in rows if row["rom_feasible"]]
        if not feasible:
            chosen.append({**rows[0], "selection": "no feasible ROM design"})
            continue
        fastest = max(feasible, key=lambda row: row["rom_per_user_tokens_s"])
        smallest = min(
            feasible,
            key=lambda row: (
                row["rom_silicon_area_mm2"],
                -row["rom_per_user_tokens_s"],
            ),
        )
        chosen.append({**fastest, "selection": "fastest"})
        if smallest["rom_design"] != fastest["rom_design"]:
            chosen.append({**smallest, "selection": "smallest silicon"})
    order = _model_order(result)
    return sorted(
        chosen,
        key=lambda row: (
            order[row["model"]],
            row["batch_size"],
            row.get("selection", ""),
        ),
    )


CSV_FIELDS = (
    "family",
    "design",
    "model",
    "context_tokens",
    "batch_size",
    "device_count",
    "topology_kind",
    "parallelism",
    "link",
    "intra_link",
    "intra_domain_size",
    "tensor_group",
    "pipeline_stages",
    "link_latency_s",
    "link_share_of_step",
    "node",
    "weight_store",
    "kv_store",
    "weight_amortization",
    "silicon_area_mm2",
    "silicon_area_mm2_per_device",
    "feasible",
    "per_user_tokens_s",
    "aggregate_tokens_s",
    "delivered_tokens_s",
    "per_user_tokens_s_throughput_view",
    "latency_correction_x",
    "token_slots",
    "microbatch_per_slot",
    "pipeline_fill_users",
    "pipeline_fill_limited_by",
    "step_time_s",
    "binding_constraint",
    "power_w",
    "static_power_w",
    "static_power_fraction_of_total",
    "power_density_w_per_mm2",
    "power_headroom_fraction",
    "cooling_limit_w",
    "energy_j_per_token",
    "thermal_scale",
    "stored_weight_bytes",
    "engaged_weight_bytes",
    "engaged_weight_fraction",
    "expert_coverage",
    "resident_kv_bytes",
    "max_resident_users",
    "weight_to_kv_read_ratio",
    "execution_format",
    "hop_events_per_token",
    "rom_sweep_ceiling_tokens_s",
)


def render_csv(result: dict[str, Any]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in result["points"]:
        writer.writerow({field: row.get(field) for field in CSV_FIELDS})
    return output.getvalue()


def render_variant_report(
    result: dict[str, Any], primary: dict[str, Any]
) -> str:
    """The quantised variant's own report, and it opens with what it is not.

    Deliberately short.  The variant exists to answer one question -- what would
    quantising BOTH sides do to this comparison -- and every additional table
    would make it look more like a result than it is.
    """

    variant = result["representation_variant"]
    selection = result["design_selection"]
    primary_selection = primary["design_selection"]
    primary_by_model = {
        entry["model"]: entry for entry in primary_selection["models"]
    }
    primary_id = result.get("primary_study_id", primary["study_id"])
    lines: list[str] = [
        f"# SECONDARY: quantised variant of `{primary_id}`",
        "",
        f"> **{variant['status']}.** Both sides are re-quantised to "
        f"{variant['bits_per_parameter']:g} bits per parameter. "
        f"**{variant['executed_tokens_at_this_precision']} tokens have ever been "
        "produced at this precision anywhere in this program, on either "
        "backend**, and no accuracy has been measured on either side. Every "
        "figure below is `derived`. This is a projection of a machine nobody "
        "has run.",
        "",
        "> **This is not the primary result.** The primary result is "
        f"`results/roofline/{primary_id}/`, which prices the released "
        "checkpoint's own packing on both sides and is unchanged by anything "
        "here. No ratio on this page may be quoted without the primary ratio "
        "from the same row in the same sentence, and the columns below are laid "
        "out so that is the natural way to read it.",
        "",
        "## The rule the variant follows",
        "",
        "**A quantisation applies to both sides.** That is not a courtesy; it is",
        "arithmetic. A GPU serving 4.25-bit weights reads 3.76x fewer weight bytes",
        "exactly as the ROM part does, and a study that gave the saving to one side",
        "would be running the asymmetry the released-packing rule exists to stop --",
        "the same rule this program already records for an FP8 KV latent in the",
        "DeepSeek profile's `kv_precision_sensitivity`.",
        "",
        f"- **Format.** {variant['format']}",
        f"- **Arithmetic.** {variant['arithmetic']}",
        f"- **Scope.** {variant['scope']}",
        "",
        "## What it changes, against the primary, row for row",
        "",
        "| Model | | design | mm2 | user tok/s | tok/s per 1,000 mm2 | "
        "resident sessions | iso-area GPU | GPU user tok/s | ratio |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
    ]
    for entry in selection["models"]:
        model = entry["model"]
        rows = [("PRIMARY (BF16, 16.00 bits)", primary_by_model.get(model))]
        rows.append(
            (
                f"variant ({variant['bits_per_parameter']:g} bits, both sides)",
                entry,
            )
        )
        for label, record in rows:
            best = record["recommended"] if record else None
            if best is None:
                lines.append(f"| {model} | {label} | *no feasible design* | | | | | | | |")
                continue
            lines.append(
                f"| {model} | {label} | "
                f"`{best['design'].split('/')[-1]}` | "
                f"{best['silicon_area_mm2']:,.0f} | "
                f"{best['per_user_tokens_s']:,.1f} | "
                f"{best['tokens_s_per_1000mm2']:,.1f} | "
                f"{_cell(best['max_resident_users'])} | "
                f"`{str(best.get('iso_area_gpu_design') or '--').split('/')[-1]}` | "
                f"{_cell(best.get('iso_area_gpu_per_user_tokens_s'), ',.1f')} | "
                f"{_cell(best.get('per_user_speed_ratio'), ',.2f')}x |"
            )
    lines.extend(
        [
            "",
            "**Read the ratio column as a pair, never alone.** If the variant's ratio",
            "is larger than the primary's, quantisation did not level the comparison,",
            "and the reason has to be stated rather than banked: on a ROM machine the",
            "weight term is a full-array sweep whose duration is a technology constant",
            "independent of the bytes stored, so fewer bits buy the ROM side array area",
            "and replication rather than sweep time, while the GPU's weight term is",
            "bytes over bandwidth and falls exactly in proportion. Whichever way the",
            "number moves, both studies are published, because the A100 pairing is the",
            "one where the GPU physically cannot follow the ROM side's datapath change",
            "and the B200 pairing is the one where it can.",
            "",
            "**The variant is selected by the same rule as the primary, applied to",
            "the same code path.** That is not a nicety: if the two artifacts were",
            "selected by different rules, the row-for-row table above would be",
            "comparing a rule change and a precision change at once and no reader",
            "could tell which one moved the number. The rule and the frontier it",
            "produces follow.",
            "",
        ]
    )
    lines.extend(_render_design_selection(result)[1:])
    lines.extend(
        [
            "## What is wrong with these numbers, stated before anyone quotes them",
            "",
            f"- **Known modelling defect.** {variant['known_defect']}",
            f"- **Unmodelled on both sides.** {variant['unmodelled']}",
            f"- **Accuracy.** {variant['accuracy']}",
            f"- **What would make this a measurement.** "
            f"{variant['what_would_make_it_a_measurement']}",
            "- **Everything the primary report's interpretation boundary says still",
            "  applies here, and one thing more: the primary is a projection of a",
            "  machine nobody has built running arithmetic this program HAS executed.",
            "  The variant is a projection of a machine nobody has built running",
            "  arithmetic nobody has executed. Those are not the same claim and this",
            "  page is the weaker one.",
            "",
        ]
    )
    return "\n".join(lines)



def _study_files(destination: Path, result: dict[str, Any]) -> list[tuple[Path, str]]:
    """Serialise one study as ``analytical.json`` plus a ``points.json`` shard.

    A study that fits under a Git host's 100 MB file limit today will not after
    the next sweep widens, so the per-point records -- the bulk -- go to their
    own compact file, and each design's graded provenance (a few hundred
    distinct blobs repeated over ~1,600 designs) is stored once.  Read the pair
    back with ``opentallas.roofline.load_study_artifact``.
    """

    summary = {key: value for key, value in result.items() if key != "points"}
    table: dict[str, Any] = {}
    designs = []
    for design in result.get("designs", ()):
        if isinstance(design.get("provenance"), Mapping):
            blob = json.dumps(design["provenance"], sort_keys=True, allow_nan=False)
            key = hashlib.sha256(blob.encode()).hexdigest()[:16]
            table[key] = design["provenance"]
            design = {**design, "provenance": key}
        designs.append(design)
    summary["designs"] = designs
    summary["provenance_table"] = table
    summary["points_file"] = "points.json"
    return [
        (
            destination / "analytical.json",
            json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
        ),
        (
            destination / "points.json",
            json.dumps(
                result.get("points", []),
                sort_keys=True,
                allow_nan=False,
                separators=(",", ":"),
            )
            + "\n",
        ),
    ]

def run_all(
    output_root: Path = OUTPUT_ROOT, *, force: bool = False, candidates: bool = True
) -> dict[str, dict[str, Any]]:
    technology = Technology.load(TECHNOLOGY_PATH)
    anchors = run_anchors(technology)
    results: dict[str, dict[str, Any]] = {}
    variants: dict[str, dict[str, Any]] = {}
    planned: list[tuple[Path, str]] = []
    for study_id in STUDIES:
        result = _simulate_study(study_id, technology)
        result["validation_gates"] = anchors
        results[study_id] = result
        destination = output_root / study_id
        planned.extend(_study_files(destination, result))
        planned.append((destination / "sweep.csv", render_csv(result)))
        planned.append(
            (
                destination / "REPORT.md",
                render_report(result, anchors).rstrip() + "\n",
            )
        )

    # --- the quantised variant, in its own tree ---------------------------
    # It is deliberately NOT another entry in ``STUDIES``: a secondary result
    # that lands in the same directory as the primary, under the same file
    # names, is one copy-paste away from being quoted as the primary.  It gets
    # its own directory, its own short report that opens with what it is not,
    # and no sweep.csv at all -- there is no row here anyone should be reading
    # into a spreadsheet.
    for study_id in STUDIES:
        config = dict(STUDIES[study_id])
        config.update(QUANTISED_VARIANT)
        config["contract"] = (
            f"SECONDARY VARIANT of {study_id}. "
            + str(STUDIES[study_id]["contract"])
            + " Both sides re-quantised to "
            f"{QUANTISED_VARIANT['bits_per_parameter']:g} bits per parameter. "
            "A projection: no token has been produced at this precision on "
            "either backend."
        )
        variant = _simulate_study(
            study_id, technology, with_sensitivity=False, config=config
        )
        variant["study_id"] = f"{study_id}-{QUANTISED_VARIANT['variant_id']}"
        variant["primary_study_id"] = study_id
        variant["representation_variant"] = {
            key: value
            for key, value in QUANTISED_VARIANT.items()
            if key not in ("models", "representation")
        }
        variant["representation_variant"]["representation"] = list(
            QUANTISED_VARIANT["representation"]
        )
        variant["validation_gates"] = anchors
        # Deliberately NOT added to ``results``: every consumer of that mapping
        # -- the report, the tests, the printed summary -- treats its entries as
        # the study's result, and a secondary projection sitting in that
        # mapping is one loop away from being read as one.  The variant is
        # written, and it is found by path.
        variants[variant["study_id"]] = variant
        destination = variant_output_root(output_root) / study_id
        planned.extend(_study_files(destination, variant))
        planned.append(
            (
                destination / "REPORT.md",
                render_variant_report(variant, results[study_id]).rstrip() + "\n",
            )
        )

    # --- the context ladder, in its own tree ------------------------------
    # One single-model study per (model, context) that is not the primary
    # context, selected by the same rule on the same code path.  Kept out of
    # ``results`` for the same reason the quantised variant is: a rung sitting
    # in that mapping is one loop away from being read as the primary.
    for study_id in STUDIES:
        for model_name, model_path, primary_context in STUDY_MODELS:
            for context in CONTEXT_LADDER.get(model_name, ()):
                if context == primary_context:
                    continue
                config = dict(STUDIES[study_id])
                config["models"] = ((model_name, model_path, context),)
                config["contract"] = (
                    f"CONTEXT-LADDER RUNG of {study_id}: {model_name} at "
                    f"{context:,} tokens. "
                    + str(STUDIES[study_id]["contract"])
                    + " Same rule, same code path as the primary; only the "
                    "context differs, and the primary artifact is unchanged."
                )
                rung = _simulate_study(
                    study_id, technology, with_sensitivity=False, config=config
                )
                label = context_rung_label(model_name, context)
                rung["study_id"] = f"{study_id}-{label}"
                rung["primary_study_id"] = study_id
                rung["context_ladder"] = {
                    "model": model_name,
                    "context_tokens": context,
                    "primary_context_tokens": primary_context,
                    "label": label,
                }
                rung["validation_gates"] = anchors
                destination = context_ladder_output_root(output_root) / study_id / label
                planned.extend(_study_files(destination, rung))
                planned.append(
                    (
                        destination / "REPORT.md",
                        render_report(rung, anchors).rstrip() + "\n",
                    )
                )

    # --- candidate models, each in its own tree ---------------------------
    # ``--no-candidates`` leaves them to separate ``--candidates`` runs, so the
    # two halves of a full regeneration can run as parallel processes.
    if candidates:
        planned.extend(_candidate_files(output_root, technology, anchors))

    existing = [path for path, _ in planned if path.exists()]
    if existing and not force:
        raise SystemExit(
            "refusing to overwrite existing study artifacts without --force:\n  "
            + "\n  ".join(str(path) for path in existing)
        )
    for path, payload in planned:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8", newline="")
    return results


def _candidate_files(
    output_root: Path,
    technology: Technology,
    anchors: dict[str, Any],
    slugs: Sequence[str] | None = None,
) -> list[tuple[Path, str]]:
    """Every candidate model's single-model study, or only ``slugs``."""

    unknown = set(slugs or ()) - {entry[0] for entry in CANDIDATE_MODELS}
    if unknown:
        raise SystemExit(f"unknown candidate slug(s): {sorted(unknown)}")
    planned: list[tuple[Path, str]] = []
    for study_id in STUDIES:
        for slug, model_name, model_path, context in CANDIDATE_MODELS:
            if slugs is not None and slug not in slugs:
                continue
            config = dict(STUDIES[study_id])
            config["models"] = ((model_name, model_path, context),)
            config["contract"] = (
                f"CANDIDATE MODEL under {study_id}: {model_name} at "
                f"{context:,} tokens. "
                + str(STUDIES[study_id]["contract"])
                + " Same rule, same code path as the primary; the model is "
                "profiled from its official checkpoint headers and has been "
                "executed by no lane in this repository. The primary artifact "
                "is unchanged."
            )
            candidate = _simulate_study(
                study_id, technology, with_sensitivity=False, config=config
            )
            candidate["study_id"] = f"{study_id}-{slug}"
            candidate["primary_study_id"] = study_id
            candidate["candidate_model"] = {
                "model": model_name,
                "slug": slug,
                "context_tokens": context,
                "profile": str(model_path.relative_to(ROOT)),
            }
            candidate["validation_gates"] = anchors
            destination = candidates_output_root(output_root) / slug / study_id
            planned.extend(_study_files(destination, candidate))
            planned.append(
                (
                    destination / "REPORT.md",
                    render_report(candidate, anchors).rstrip() + "\n",
                )
            )
    return planned


def run_candidates(
    output_root: Path, slugs: Sequence[str], *, force: bool = False
) -> list[Path]:
    """Run only the named candidate studies; the primaries are not touched.

    Same rule and code path as ``run_all``, which runs every candidate after
    the primaries; this exists so adding a candidate does not cost the ~26
    minutes of regenerating every primary artifact.
    """

    technology = Technology.load(TECHNOLOGY_PATH)
    anchors = run_anchors(technology)
    planned = _candidate_files(output_root, technology, anchors, tuple(slugs))
    existing = [path for path, _ in planned if path.exists()]
    if existing and not force:
        raise SystemExit(
            "refusing to overwrite existing study artifacts without --force:\n  "
            + "\n  ".join(str(path) for path in existing)
        )
    for path, payload in planned:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8", newline="")
    return [path for path, _ in planned]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_ROOT)
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing artifacts under the output directory",
    )
    parser.add_argument(
        "--candidates",
        nargs="+",
        metavar="SLUG",
        help=(
            "run only these candidate-model studies (slugs from CANDIDATE_MODELS) "
            "and leave every other artifact untouched"
        ),
    )
    parser.add_argument(
        "--no-candidates",
        action="store_true",
        help=(
            "run the primaries, their variants and context ladders but not the "
            "candidate models (run those with --candidates, possibly in parallel)"
        ),
    )
    args = parser.parse_args(argv)
    if args.candidates:
        for path in run_candidates(args.output, args.candidates, force=args.force):
            print(path.resolve())
        return 0
    results = run_all(args.output, force=args.force, candidates=not args.no_candidates)
    for study_id, result in results.items():
        audit = result["consistency_audit"]
        print(
            f"{study_id}: {len(result['points'])} points, audit "
            f"{audit['status']} ({audit['checks_evaluated']} checks)"
        )
        print((args.output / study_id / "REPORT.md").resolve())
        selection = result["design_selection"]
        for entry in selection["models"]:
            best = entry["recommended"]
            if best is None:
                continue
            print(
                f"  recommended {entry['model']}: "
                f"{best['design'].split('/')[-1]} "
                f"({best['silicon_area_mm2']:,.0f} mm2, "
                f"{best['per_user_tokens_s']:,.1f} tok/s/user, "
                f"{best['tokens_s_per_1000mm2']:,.1f} tok/s per 1,000 mm2, "
                f"{best['max_resident_users']:,.0f} resident)"
            )
    for study_id in STUDIES:
        print(
            "SECONDARY quantised variant (projection, not a measurement): "
            + str(
                (
                    variant_output_root(args.output) / study_id / "REPORT.md"
                ).resolve()
            )
        )
    for study_id in STUDIES:
        for model_name, _path, primary_context in STUDY_MODELS:
            for context in CONTEXT_LADDER.get(model_name, ()):
                if context == primary_context:
                    continue
                label = context_rung_label(model_name, context)
                print(
                    f"context-ladder rung {study_id}/{label}: "
                    + str(
                        (
                            context_ladder_output_root(args.output)
                            / study_id
                            / label
                            / "REPORT.md"
                        ).resolve()
                    )
                )
    for study_id in STUDIES:
        for slug, _model_name, _path, _context in CANDIDATE_MODELS:
            print(
                f"candidate model {slug}/{study_id}: "
                + str(
                    (
                        candidates_output_root(args.output)
                        / slug
                        / study_id
                        / "REPORT.md"
                    ).resolve()
                )
            )
    gates = next(iter(results.values()))["validation_gates"]
    for name in (
        "taalas_hc1",
        "a100_weight_bound",
        "a100_tdp_power",
        "taalas_hc1_card_power",
    ):
        gate = gates[name]
        print(
            f"gate {name}: modelled {gate['modelled_value']:,.2f} vs published "
            f"{gate['published_value']:,.2f} ({gate['ratio']:.3f}x) "
            f"{'PASS' if gate['passed'] else 'FAIL'}"
        )
    # A failing gate is reported, not swallowed, and it is not an error exit:
    # the residual IS the result, and turning it into a non-zero exit code
    # would create pressure to tune it away.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
