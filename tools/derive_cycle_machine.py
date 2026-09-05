#!/usr/bin/env python3
"""Derive a matched ROM/HBM cycle-model machine pair from ONE analytical design point.

Why this tool exists
--------------------
``results/roofline/n5_vs_b200/analytical.json`` publishes a ROM-versus-GPU
comparison for three models -- Qwen3-8B at context 8,192,
DeepSeek-V4-Flash-0731 at 200,000 and DeepSeek-V4-Pro-0813 at 1,000,000, each
at exactly one context and never at a common one.  The cycle-accurate
simulator, run on the shipped SKY130/ASAP7 machines, lands four orders of
magnitude away from it and gets the ROM-to-HBM ratio wrong by 5x.  It does so
for two reasons that have nothing to do with the analytical model being wrong:

1.  The shipped cycle machines price a 38.8 MHz open-PDK research prototype,
    not the N5 silicon the analytical study prices.  Their compute differs by
    about six orders of magnitude.
2.  The ROM and HBM sides of the shipped cycle comparison were typed
    separately.  ``rom_qwen3`` declares tensor lanes 512 and
    ``hbm_sram_single_chip`` declares 256, and the two compiled deployments
    carry tensor column groups of 8192 and 512 respectively.  A 2x lane
    advantage and a 16x column-group advantage were being reported as a ROM
    result.

This tool removes both defects by construction.  It reads ONE analytical design
point pair, derives ONE machine, and emits it twice -- once with the weights in
ROM and once with the weights in HBM.  Every compute parameter is shared by
construction because there is only one derivation of it, and
:func:`assert_comparable` re-resolves both machines through
``runtime.cycle.machine.MachineModel`` and fails the emit if any parameter
outside a declared, cited weight-path allowlist differs.

Any cell, not one anchor
------------------------
The tool was written around a single pair -- Qwen3-8B array x4 against two B200
packages -- and four of its rules were that pair's accidents rather than the
study's:

*   the compute roof was ``operations_by_canonical_format['bf16']`` over a
    ``compute_ops_s_per_mm2['bf16']`` density.  Both DeepSeek models execute
    w4a8 and publish no bf16 key at all, so the first raises and the second --
    worse -- does not: it prices a w4a8 point at bf16 density and is 2.7x wrong
    in silence.  The roof is now the point's OWN operations over the point's
    OWN published compute time, which is exact by construction and is
    cross-checked against the study's sum-over-formats derivation.
*   the lane count was ``num_key_value_heads x head_dim``.  Both DeepSeek
    configs are MLA and carry neither key.  The rule was never about GQA: it is
    "the widest lane array at which every tensor operator still runs at the
    roof", and that is read from the model's own neutral IR.
*   the ROM weight rate was ``peak_weight_read_bytes_s``, the design's
    aggregate.  The published component times already carry ``token_slots``, so
    the rate a token can ENGAGE is the aggregate over that design's own slot
    count.  Taking the undivided aggregate on both sides removes a different
    serialisation factor from each -- 4 against 2 on the Flash x32 cell -- and
    hands the more deeply pipelined side a speed-up the study never granted it.
*   the HBM channel could only be shared when the ROM point held KV in HBM.
    Five of the study's design points -- including the batch-1 headline for
    Qwen AND for Flash -- hold KV in SRAM, buy no HBM at all, and were rejected.
    Their KV is now derived onto the SRAM ports, which is a difference the two
    design points genuinely state, and it is licensed by a SECOND allowlist
    that ``allowlist_for`` hands out only to an anchor whose two points name
    different ``kv_store`` values.

``--matrix`` derives every cell the study publishes at batch 1: each model's
own recommendation, each published frontier entry, the best array and best
wafer topology named per model, and the ROM design points the repository
already has a capability shape for.  It writes a manifest saying which cells
were emitted and, for any that were not, exactly what blocked them.

What it does NOT do
-------------------
It does not invent an architecture.  Every emitted number is either an
analytical value divided by a stated denominator, or an explicit statement that
the analytical model prices no counterpart for the term.  Both kinds carry
their derivation string into the artifact.  Where the cycle model cannot
express an analytical term at all -- the link term on a SINGLE_CHIP topology is
the big one -- the tool records the term as structurally absent rather than
approximating it with a fitted number.

Grades
------
Two vocabularies collide here and neither can be bent.
``configs/hardware/technology.json#grade_definitions`` has
assumed/derived/executed/measured/published; the cost-table schema's
``provenance`` field is a closed enum of characterized/datasheet/assumed and
``CostTable.resolve`` raises on anything else.  So every emitted parameter
carries BOTH: ``provenance`` (what the loader validates) is never
``characterized``, and ``analytical_grade`` (the technology.json vocabulary,
ignored by the loader but preserved into the table digest) says ``derived`` or
``assumed``.  D2's "nothing derived may be graded characterized or measured" is
therefore satisfied structurally: the cost-table enum has no ``measured``
member at all, and this tool never writes ``characterized``.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

DEFAULT_ANALYTICAL = "results/roofline/n5_vs_b200/analytical.json"
DEFAULT_TECHNOLOGY = "configs/hardware/technology.json"

TECHNOLOGY_VIEW = "n5_design_target"

#: The five analytical component times, in the order the reconciliation reports.
ANALYTICAL_TERMS = (
    "compute",
    "weight_read",
    "kv_read",
    "link_latency",
    "layer_fixed_latency",
)

#: The nine engine families ``MachineModel.engine`` will resolve.
FAMILIES = (
    "tensor",
    "vector",
    "attention",
    "reduction",
    "route",
    "selection",
    "state",
    "dma",
    "link",
)

#: Submission queues per family.  Shared by both machines by construction.
#: Taken from the ROM capability where it declares one, else from the HBM
#: capability, so neither backend's lowering sees a queue count it has never
#: been exercised with.
#: The two backends derive a SCHEDULE's ``issue_window`` from DIFFERENT
#: capability fields: the ROM lowering from ``limits.max_outstanding_per_queue``
#: (compiler/backends/rom/common/program.py:1795-1797) and the HBM lowering
#: from ``engines.<family>.queues``
#: (compiler/backends/hbm_sram/lower.py:1359).  ``issue_window`` multiplies
#: ``tile_cols`` into the column-group span that caps the batch-1 tensor rate,
#: so leaving those two fields unequal leaves the two deployments with
#: different tensor widths whatever the machine files say.  Setting them equal
#: is the only way one machine's tile pipeline is the other's.
SHARED_OUTSTANDING_PER_QUEUE = 16
SHARED_QUEUES = {f: SHARED_OUTSTANDING_PER_QUEUE for f in FAMILIES}

SHARED_QUEUE_DEPTH = {f: (4 if f == "state" else 8) for f in FAMILIES}

#: Resolved machine parameters the two emitted machines are PERMITTED to
#: differ on, each with the analytical field that justifies the difference.
#: Anything outside this set differing is a hard failure of the emit.
WEIGHT_PATH_ALLOWLIST: dict[str, str] = {
    "rom.arrays": (
        "ROM array count.  The ROM design point stores its weights in ROM and "
        "the GPU design point has no ROM at all; the HBM machine carries a "
        "single inert array because the cost-table schema requires the full "
        "parameter set, and no MEMORY_OBJECT in the HBM deployment is stamped "
        "StorageClass.ROM, so it is never read."
    ),
    "rom.bytes_per_cycle_per_array": (
        "Per-array ROM read rate.  Derived on the ROM machine from "
        "points[ROM].peak_weight_read_bytes_s; inert on the HBM machine."
    ),
    "rom.transaction_bytes": (
        "ROM burst quantum, set equal to rom.bytes_per_cycle_per_array so the "
        "model's ceil(transaction_bytes / bytes_per_cycle) is exactly 1 and no "
        "bandwidth is lost to quantisation; inert on the HBM machine."
    ),
    "rom.interleave_bytes": (
        "ROM address stripe, set equal to the burst quantum so consecutive "
        "bursts land on consecutive arrays; inert on the HBM machine."
    ),
    "hbm.channels": (
        "HBM channel count.  The two design points state different HBM "
        "provisioning: the ROM point buys the stacks its "
        "area_fractions.hbm_phy pays for and serves KV alone from them "
        "(points[ROM].kv_transfer_bytes_per_step / "
        "component_times_s.kv_read), while the GPU point buys 8 stacks per "
        "package and serves weights AND KV from one pool "
        "(points[GPU].kv_transfer_bytes_per_step / "
        "component_times_s.kv_read).  A ROM point whose kv_store is `sram` "
        "buys none at all (area_fractions.hbm_phy 0.0) and carries a single "
        "inert channel.  Both sides resolve to the SAME "
        "hbm.bytes_per_cycle_per_channel; only the channel count differs, "
        "which is exactly what the design points say differs."
    ),
}

#: Resolved parameters the two machines may ALSO differ on, but ONLY when the
#: two anchor points name different ``kv_store`` values.  A ROM design point
#: that holds KV in SRAM prices a real SRAM read rate
#: (technology_derivations.sram_read_bytes_s_per_mm2 through
#: points[ROM].area_fractions.sram) where the GPU point prices none at all, so
#: the ROM machine's activation/KV store is DERIVED and the GPU machine's stays
#: the deliberately non-binding store of the shared derivation.  This is a
#: memory-provisioning difference the artifact states, not a compute one:
#: nothing in the arithmetic path may move.  ``allowlist_for`` adds these
#: entries only for an anchor whose two points disagree on kv_store, so a pair
#: that agrees can never quietly acquire an SRAM advantage.
KV_PATH_ALLOWLIST: dict[str, str] = {
    "sram.bytes_per_cycle_per_port": (
        "SRAM port read rate.  The ROM design point's kv_store is `sram`, so "
        "its KV traffic is an SRAM rate derived from "
        "points[ROM].kv_transfer_bytes_per_step / component_times_s.kv_read; "
        "the GPU point holds KV in HBM and allocates no SRAM area at all "
        "(area_fractions.sram 0.0), so its SRAM keeps the non-binding rate the "
        "shared derivation gives an unpriced store.  The difference is "
        "directionally AGAINST the ROM side: the ROM machine's activation "
        "store is finite where the GPU machine's cannot bind."
    ),
    "sram.transaction_bytes": (
        "SRAM burst quantum, set equal to sram.bytes_per_cycle_per_port on "
        "both machines so the model's ceil() is exact; it differs only because "
        "that rate differs.  See sram.bytes_per_cycle_per_port."
    ),
    "sram.interleave_bytes": (
        "SRAM address stripe, set equal to the SRAM burst on both machines; it "
        "differs only because that rate differs.  See "
        "sram.bytes_per_cycle_per_port."
    ),
}


def allowlist_for(anchor: "Anchor") -> dict[str, str]:
    """The permitted-difference set for THIS anchor, with its own numbers.

    The base weight-path set always applies.  The KV-path set applies only
    when the two design points disagree on ``kv_store``; an anchor whose two
    points agree can never acquire an SRAM difference, and
    :func:`assert_comparable` will reject one.
    """
    out = dict(WEIGHT_PATH_ALLOWLIST)
    if anchor.rom_kv_store != anchor.hbm_kv_store:
        out.update(KV_PATH_ALLOWLIST)
    cite = (
        f"  THIS ANCHOR: {anchor.rom_design} (kv_store "
        f"{anchor.rom_kv_store!r}, token_slots {anchor.rom_token_slots:g}, "
        f"{anchor.rom['device_count']:g} devices) against {anchor.hbm_design} "
        f"(kv_store {anchor.hbm_kv_store!r}, token_slots "
        f"{anchor.hbm_token_slots:g}, {anchor.hbm['device_count']:g} devices)."
    )
    return {k: v + cite for k, v in out.items()}


#: The pair this tool was first written around.  It keeps the emitted file
#: names it was published with; every other pair is keyed on its own identity so
#: a second cell cannot silently overwrite a first.
DEFAULT_ROM_DESIGN = "Qwen3-8B/ROM-N5-native-HBMKV-array-tensor-x4"
DEFAULT_HBM_DESIGN = "Qwen3-8B/b200_sxm-x2-tensor"

#: Base capability by (model, ROM topology_kind).  Only capacities, limits,
#: features and numeric contracts come from it -- every timing parameter is
#: derived -- but those decide whether a deployment could ever be built against
#: the emitted record, so the base is chosen to match the design point's shape
#: rather than left at the Qwen default.
ROM_BASE_CAPABILITY: dict[tuple[str, str], str] = {
    ("Qwen3-8B", "array"): "rom_qwen3.json",
    ("Qwen3-8B", "wafer"): "rom_qwen3.json",
    ("DeepSeek-V4-Flash-0731", "array"): "rom_deepseek_v4_array_32.json",
    ("DeepSeek-V4-Flash-0731", "wafer"): "rom_deepseek_v4.json",
    # Pro takes the Pro array record for BOTH kinds, and the wafer entry is
    # not an oversight.  A Pro program does not fit the Flash shapes at all:
    # it routes 384 experts against max_expert_ids 256 and needs 85.9 GB of
    # ROM against 17.2 GB, so a deployment built against a Flash-based record
    # is refused at admission rather than merely mis-costed.  Pro also has no
    # wafer and no single-chip ROM product and cannot have one -- an unsharded
    # routed expert region needs a per-layer element stride 1.97x over the
    # 32-bit dynamic-term stride field of ABI 3.0 tensor views, and only the
    # array's 32-way node ownership brings it inside (see
    # ``deepseek_v4_pro_array_rom_capability``).  The collapse forces
    # topology_class to SINGLE_CHIP either way, so the base contributes
    # capacities and limits only; the design point's own topology is carried
    # in the manifest and in ``derived_from.design_point``, not here.
    ("DeepSeek-V4-Pro-0813", "array"): "rom_deepseek_v4_pro_array_32.json",
    ("DeepSeek-V4-Pro-0813", "wafer"): "rom_deepseek_v4_pro_array_32.json",
}

#: The GPU-side base is ALWAYS the single-chip record.  The derivation
#: collapses every design point to one logical device, and
#: ``hbm_sram_cluster_32.json`` differs from ``hbm_sram_single_chip.json`` in
#: exactly three places -- topology_class, limits.max_nodes and the link block
#: -- all of which the collapse removes.  Its limits, memory capacities and
#: engine declarations are byte-identical, so nothing is lost by using the
#: single-chip record and the emitted pair keeps one fabric-free shape.
HBM_BASE_CAPABILITY = "hbm_sram_single_chip.json"


def _slug(text: str) -> str:
    out = "".join(c if c.isalnum() else "-" for c in str(text).lower())
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")


def _pair_id(model: str, rom_design: str, hbm_design: str) -> str:
    return "__".join((
        _slug(model),
        _slug(rom_design.split("/", 1)[-1]),
        _slug(hbm_design.split("/", 1)[-1]),
    ))


LEGACY_PAIR_ID = _pair_id("Qwen3-8B", DEFAULT_ROM_DESIGN, DEFAULT_HBM_DESIGN)


def pair_id(anchor: "Anchor") -> str:
    """A filesystem-safe identity for this cell.

    Every emitted file is keyed on it, so deriving a second (model, rom_design,
    hbm_design) triple cannot overwrite a first and ``--check`` cannot report
    DRIFT on a file that is simply a different cell.  The one exception is the
    pair this tool was published with, which keeps its original names.
    """
    return _pair_id(anchor.rom["model"], anchor.rom_design, anchor.hbm_design)


def base_capabilities(anchor: "Anchor", rom_base: str | None = None,
                      hbm_base: str | None = None) -> tuple[str, str]:
    """Repo-relative paths of the two base capability records for this cell."""
    model = str(anchor.rom["model"])
    kind = str(anchor.rom.get("topology_kind", "array"))
    if rom_base is None:
        name = ROM_BASE_CAPABILITY.get((model, kind))
        if name is None:
            raise DerivationError(
                f"no ROM base capability is registered for model {model!r} "
                f"with topology_kind {kind!r}; pass --rom-base explicitly"
            )
        rom_base = f"configs/hardware/abi3_capability/{name}"
    if hbm_base is None:
        hbm_base = f"configs/hardware/abi3_capability/{HBM_BASE_CAPABILITY}"
    return rom_base, hbm_base


class DerivationError(RuntimeError):
    """The derivation could not be carried out, or the emit is not comparable."""


# ---------------------------------------------------------------------------
# One emitted number, with everything needed to audit it
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class Derived:
    """One cost-table parameter with its derivation and both grades."""

    name: str
    value: Any
    unit: str
    #: technology.json grade vocabulary: derived | assumed
    analytical_grade: str
    #: cost-table Provenance enum: assumed | datasheet (never characterized)
    provenance: str
    derivation: str
    source: str | None = None

    def entry(self) -> dict[str, Any]:
        """The cost-table entry.  Unknown keys are preserved into the digest."""
        body: dict[str, Any] = {
            "value": self.value,
            "unit": self.unit,
            "provenance": self.provenance,
            "analytical_grade": self.analytical_grade,
            "note": self.derivation,
        }
        if self.source:
            body["source"] = self.source
        return body

    def row(self) -> dict[str, Any]:
        return {
            "parameter": self.name,
            "value": self.value,
            "unit": self.unit,
            "analytical_grade": self.analytical_grade,
            "cost_table_provenance": self.provenance,
            "derivation": self.derivation,
            **({"source": self.source} if self.source else {}),
        }


# ---------------------------------------------------------------------------
# The analytical anchor
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class Anchor:
    """One analytical ROM/GPU pair plus the technology inputs it was built from."""

    rom_design: str
    hbm_design: str
    batch_size: int
    context_tokens: int
    rom: Mapping[str, Any]
    hbm: Mapping[str, Any]
    summary: Mapping[str, Any]
    technology: Mapping[str, Any]
    derivations: Mapping[str, Any]
    study_id: str
    analytical_path: str

    # -- the collapse ----------------------------------------------------
    # Every rate below is ANALYTICAL BYTES (or operations) OVER THE PUBLISHED
    # COMPONENT TIME.  That one rule is what generalises the derivation off its
    # original anchor, and it is not a choice of convenience: the design point
    # publishes component_times_s already multiplied by ``token_slots``
    # (src/opentallas/roofline.py:3288-3297 -- "the service terms are the
    # per-slot cost multiplied by the slots the token traverses"), so the rate
    # a token can actually engage is the machine's aggregate resource divided
    # by the slots it must traverse.  A pipelined design owns N devices but a
    # token uses one stage at a time; the collapsed logical device therefore
    # carries aggregate/token_slots, and it reproduces the published PER-TOKEN
    # term exactly.  At token_slots = 1 -- the original anchor -- this is
    # bit-identical to reading peak_weight_read_bytes_s directly.
    #
    # Applying the rule on BOTH sides is what keeps the pair comparable.  The
    # two sides of a cell often carry different token_slots (the Flash x32 cell
    # is 4 against 2), so taking the aggregate on both would remove a different
    # serialisation factor from each side and hand one of them a speed-up that
    # the study never granted it.  That is the exact class of defect this
    # generator exists to prevent.
    @property
    def rom_token_slots(self) -> float:
        return float(self.rom.get("token_slots", 1.0) or 1.0)

    @property
    def hbm_token_slots(self) -> float:
        return float(self.hbm.get("token_slots", 1.0) or 1.0)

    @property
    def rom_kv_store(self) -> str:
        return str(self.rom.get("kv_store", "hbm"))

    @property
    def hbm_kv_store(self) -> str:
        return str(self.hbm.get("kv_store", "hbm"))

    # -- derived analytical quantities ----------------------------------
    @property
    def operations_by_format(self) -> Mapping[str, float]:
        return self.rom["operations_by_canonical_format"]

    @property
    def compute_density_by_format(self) -> Mapping[str, float]:
        d = self.derivations["compute_ops_s_per_mm2"]
        return {f: float(d[f]["value"]) for f in self.operations_by_format}

    @property
    def compute_ops_s_per_mm2(self) -> float:
        """Arithmetic density for the format the point declares it executes.

        Audit only -- no emitted parameter reads it.  The design point may
        carry several canonical formats at once (both DeepSeek ROM points
        publish fp32 and w4a8), so there is no single density that prices the
        point and :attr:`compute_roof_ops_s` does not use one.  Reading a
        literal ``bf16`` here, as this tool did on its first anchor, prices a
        w4a8 design point at bf16 density and is wrong by 2.7x without raising.
        """
        d = self.derivations["compute_ops_s_per_mm2"]
        fmt = str(self.rom.get("execution_format", ""))
        if fmt not in d:
            fmt = max(self.operations_by_format,
                      key=lambda f: float(self.operations_by_format[f]))
        return float(d[fmt]["value"])

    @property
    def compute_efficiency(self) -> float:
        return float(self.derivations["efficiencies"]["compute"]["value"])

    @property
    def compute_area_time_s(self) -> float:
        """The analytical compute term rebuilt from area x density x efficiency.

        ``_compute_time`` is a SUM OVER FORMATS -- ops_f / (roof_f x
        efficiency) -- not one density (src/opentallas/roofline.py:2628-2655).
        This reproduces the published component_times_s.compute exactly for
        every ROM design point in the study, single-format and mixed alike, and
        is carried as a cross-check on :attr:`compute_roof_ops_s`.  It does NOT
        reproduce a GPU point's compute term, because a published part's roof
        is the vendor's own per-format number and not area x density; that gap
        is reported as a residual rather than absorbed.
        """
        area = (float(self.rom["area_fractions"]["compute"])
                * float(self.rom["silicon_area_mm2"]))
        eff = self.compute_efficiency
        dens = self.compute_density_by_format
        return sum(
            float(n) / (area * dens[f] * eff)
            for f, n in self.operations_by_format.items()
        ) * self.rom_token_slots

    @property
    def compute_roof_ops_s(self) -> float:
        """The ROM design point's SUSTAINED (post-derate) per-token roof.

        The analytical operations of every canonical format the point executes,
        divided by the compute time the point publishes.  Derated and
        slot-corrected by construction, because the published term already
        carries efficiencies.compute and token_slots.  For the original
        single-format, single-slot anchor this is bit-identical to
        ``area x compute_ops_s_per_mm2.bf16 x efficiencies.compute``.
        """
        return self.operations / float(self.rom["component_times_s"]["compute"])

    @property
    def operations(self) -> float:
        return float(sum(float(v) for v in self.operations_by_format.values()))

    @property
    def operations_per_mac(self) -> float:
        """Analytical operations per active parameter.  NOT a constant.

        2.0 exactly when the study used its active-parameter fallback (every
        Qwen3-8B point: multiplies AND adds over a dense weight pass).  Both
        DeepSeek models are counted by real operator accounting instead and
        come out at 3.8 (Flash) and 6.0 (Pro), so the sentence "the analytical
        count is multiplies and adds" is a statement about ONE anchor and is
        recomputed here for each.
        """
        return self.operations / float(self.summary["active_parameters"])

    @property
    def compute_roof_mac_s(self) -> float:
        return self.compute_roof_ops_s / self.operations_per_mac

    @property
    def rom_weight_read_bytes_s(self) -> float:
        """The ROM weight rate ONE TOKEN engages: the array over the slots.

        ``peak_weight_read_bytes_s / token_slots``, which is exactly
        ``stored_weight_bytes / component_times_s.weight_read`` for every point
        in the study (:meth:`assert_collapse_is_exact` checks it rather than
        assuming it) and is ``peak_weight_read_bytes_s`` itself at one slot.
        The aggregate form is used because it divides exactly.
        """
        return self.rom_peak_weight_read_bytes_s / self.rom_token_slots

    @property
    def rom_peak_weight_read_bytes_s(self) -> float:
        """The aggregate array rate the design point owns, before the collapse."""
        return float(self.rom["peak_weight_read_bytes_s"])

    @property
    def rom_kv_read_bytes_s(self) -> float:
        return float(self.rom["kv_transfer_bytes_per_step"]) / float(
            self.rom["component_times_s"]["kv_read"]
        )

    @property
    def hbm_memory_bytes_s(self) -> float:
        """The GPU point's single HBM rate ONE TOKEN engages.

        ``peak_weight_read_bytes_s / token_slots``, checked against the KV term
        -- ``kv_transfer_bytes_per_step / component_times_s.kv_read``, a pure
        bandwidth term on the GPU's one shared pool -- by
        :meth:`assert_collapse_is_exact`.  The WEIGHT term cannot be used for
        this check on an MoE model, where it also carries the engaged-device
        correction.
        """
        return self.hbm_peak_memory_bytes_s / self.hbm_token_slots

    @property
    def hbm_peak_memory_bytes_s(self) -> float:
        return float(self.hbm["peak_weight_read_bytes_s"])

    def assert_collapse_is_exact(self) -> dict[str, float]:
        """Fail loudly if aggregate/token_slots is not the per-token rate.

        The whole generalisation rests on the claim that the published
        component times are the per-slot cost times the slots traversed.  If a
        point ever breaks it, the derived machine would silently carry the
        wrong bandwidth, so it is checked rather than assumed.
        """
        out = {}
        for role, aggregate_over_slots, bytes_over_time, what in (
            ("rom_weight", self.rom_weight_read_bytes_s,
             float(self.rom["stored_weight_bytes"])
             / float(self.rom["component_times_s"]["weight_read"]),
             "stored_weight_bytes / component_times_s.weight_read"),
            ("hbm_memory", self.hbm_memory_bytes_s,
             float(self.hbm["kv_transfer_bytes_per_step"])
             / float(self.hbm["component_times_s"]["kv_read"]),
             "kv_transfer_bytes_per_step / component_times_s.kv_read"),
        ):
            rel = bytes_over_time / aggregate_over_slots - 1.0
            if abs(rel) > 1e-9:
                raise DerivationError(
                    f"the {role} collapse is not exact: {what} is "
                    f"{bytes_over_time:.6e} B/s but peak_weight_read_bytes_s / "
                    f"token_slots is {aggregate_over_slots:.6e} B/s "
                    f"({rel:+.3e} relative).  The derivation assumes the "
                    f"published component times are the per-slot cost "
                    f"multiplied by the slots a token traverses; this point "
                    f"does not satisfy that, so the collapsed logical device "
                    f"cannot be built from it"
                )
            out[role] = rel
        return out

    # -- technology latency primitives ----------------------------------
    def latency(self, name: str) -> float:
        return float(self.technology["latency"][name]["value"])

    @property
    def global_traversal_s(self) -> float:
        area = float(self.technology["reticle"]["area_mm2"]["value"])
        return math.sqrt(area) * self.latency("global_wire_delay_s_per_mm")

    @property
    def array_pass_boundary_s(self) -> float:
        return self.latency("pipeline_fill_drain_s") + self.global_traversal_s

    @property
    def kv_round_trip_s(self) -> float:
        return self.latency("sram_access_s") + self.global_traversal_s


def _relative(path: Path) -> str:
    """Repo-relative when possible, so the emitted files are host-independent."""
    try:
        return str(Path(path).resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def _select_point(points: Sequence[Mapping[str, Any]], design: str,
                  batch: int, context: int) -> Mapping[str, Any]:
    hits = [
        p for p in points
        if p.get("design") == design
        and int(p.get("batch_size", -1)) == batch
        and int(p.get("context_tokens", -1)) == context
    ]
    if len(hits) != 1:
        raise DerivationError(
            f"{len(hits)} analytical points match design={design!r} "
            f"batch_size={batch} context_tokens={context}; expected exactly 1"
        )
    return hits[0]


def load_anchor(
    analytical_path: Path,
    technology_path: Path,
    *,
    rom_design: str,
    hbm_design: str,
    batch_size: int,
    context_tokens: int,
) -> Anchor:
    body = json.loads(analytical_path.read_text())
    points = body["points"]
    rom = _select_point(points, rom_design, batch_size, context_tokens)
    hbm = _select_point(points, hbm_design, batch_size, context_tokens)
    if rom.get("model") != hbm.get("model"):
        raise DerivationError("the two anchor points name different models")
    summaries = [m for m in body["model_summaries"] if m.get("model") == rom["model"]]
    if len(summaries) != 1:
        raise DerivationError(f"no unique model summary for {rom['model']!r}")
    return Anchor(
        rom_design=rom_design,
        hbm_design=hbm_design,
        batch_size=batch_size,
        context_tokens=context_tokens,
        rom=rom,
        hbm=hbm,
        summary=summaries[0],
        technology=json.loads(technology_path.read_text()),
        derivations=body["technology_derivations"],
        study_id=str(body.get("study_id", "")),
        analytical_path=_relative(analytical_path),
    )


# ---------------------------------------------------------------------------
# The derivation
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class Derivation:
    """Every emitted parameter, split into what is shared and what is not."""

    anchor: Anchor
    shared: dict[str, Derived] = field(default_factory=dict)
    rom_only: dict[str, Derived] = field(default_factory=dict)
    hbm_only: dict[str, Derived] = field(default_factory=dict)
    facts: dict[str, Any] = field(default_factory=dict)
    residuals: list[dict[str, Any]] = field(default_factory=list)

    def parameters(self, role: str) -> dict[str, Derived]:
        extra = self.rom_only if role == "rom" else self.hbm_only
        merged = dict(self.shared)
        merged.update(extra)
        return merged


def _q(target_bytes_s: float, units: int, clock_hz: float) -> tuple[int, float]:
    """Split an aggregate B/s into (integer per-unit B/cycle, achieved B/s).

    The cycle model charges ``max(1, ceil(nbytes / bytes_per_cycle))`` cycles
    for a transaction of at most ``transaction_bytes`` bytes, so setting
    ``transaction_bytes == bytes_per_cycle`` makes the quantisation exactly
    lossless and the achieved aggregate is ``units * bytes_per_cycle * clock``.
    """
    per_unit = target_bytes_s / (units * clock_hz)
    rounded = int(round(per_unit))
    if rounded < 1:
        raise DerivationError(
            f"aggregate {target_bytes_s:.6e} B/s over {units} units at "
            f"{clock_hz:.6e} Hz rounds to less than one byte per cycle"
        )
    return rounded, float(rounded) * units * clock_hz


def derive(anchor: Anchor, *, rom_arrays: int | None = None) -> Derivation:
    """Emit every cost-table parameter for the pair, from the anchor alone.

    ``rom_arrays`` is the ROM bank count of the base capability the pair will
    be emitted against.  It is a granularity choice, not an analytical value:
    the design point fixes only the product arrays x bytes_per_cycle_per_array
    x clock.  It defaults to the shipped Qwen ROM capability's 16 so a caller
    that names no base gets the original anchor's split unchanged.
    """
    d = Derivation(anchor=anchor)
    A = anchor
    d.facts["collapse_exactness"] = A.assert_collapse_is_exact()
    ana = f"{A.analytical_path}#points[design={A.rom_design}]"
    ana_hbm = f"{A.analytical_path}#points[design={A.hbm_design}]"
    tech = f"{DEFAULT_TECHNOLOGY}"

    # -- 1.  Clock ------------------------------------------------------
    # The analytical model states no clock.  It does state how long the
    # sequencer takes to issue and decode one instruction, and the cycle model
    # spends exactly three sequencer cycles on that act (fetch + decode +
    # issue).  Those two statements fix the clock and nothing else in this file
    # is free to choose it.
    front_end_cycles = 3
    seq_s = A.latency("sequencer_issue_decode_s")
    clock_hz = front_end_cycles / seq_s
    d.shared["clock.frequency_hz"] = Derived(
        name="clock.frequency_hz",
        value=clock_hz,
        unit="Hz",
        analytical_grade="derived",
        provenance="assumed",
        derivation=(
            f"{front_end_cycles} sequencer cycles (sequencer.fetch_cycles + "
            f"decode_cycles + issue_cycles, the cycle model's per-instruction "
            f"front end) divided by technology.json#latency."
            f"sequencer_issue_decode_s = {seq_s:g} s.  The analytical model "
            f"states no clock; this is the one analytical quantity that fixes "
            f"one.  Every rate below is an analytical B/s or ops/s divided by "
            f"this clock, so a different clock would move the per-cycle "
            f"numbers and leave every derived TIME unchanged."
        ),
        source=f"{tech}#latency.sequencer_issue_decode_s",
    )

    # -- 2.  Compute ----------------------------------------------------
    # The analytical design point pins ONE arithmetic quantity: the sustained
    # roof in ops/s.  The cycle model's tensor engine delivers
    #     min(lanes, tile_cols * issue_window, cols) * work_per_lane_cycle * clock
    # MAC/s at batch 1 (runtime/cycle/model.py:2420-2436 with
    # tensor_lane_mapping at :838-895).  ``lanes`` therefore saturates at the
    # operator's own output width, and the ONLY choice of lanes for which the
    # engine delivers the derived roof on EVERY tensor operator of this model
    # is the narrowest operator width.  That is a condition for exactness, not
    # a preference: any wider lane array is masked on the narrow projections
    # and delivers less than the roof.
    tensor_ops = tensor_operator_widths(A)
    narrowest = _narrowest_width(A, tensor_ops)
    lanes = narrowest
    wider = sorted({int(o["output_width"]) for o in tensor_ops} - {narrowest})[:2]
    narrow_ops = sorted({
        str(o["kernel_id"]).split(".", 2)[-1] for o in tensor_ops
        if int(o["output_width"]) == narrowest
    })
    roof_mac_s = A.compute_roof_mac_s
    # work_per_lane_cycle is stated in WORK-COUNTER units -- the cost table
    # declares unit "work/lane/cycle" and the characterized SKY130 value was
    # measured as (tensor.multiplications + tensor.additions) / cycles.  The
    # analytical operations count is a work count too -- multiplies AND adds
    # over every canonical format the point executes -- so the roof goes in
    # unconverted and the two vocabularies agree without a factor.  The cycle
    # model reconciles the coordinate count with the work-counter count itself
    # (CycleModel._work_scale).  How many work units a MAC costs is a PROPERTY
    # OF THE ANCHOR and not a constant: exactly two where the study used its
    # active-parameter fallback, and whatever real operator accounting gives
    # otherwise, which Anchor.operations_per_mac recomputes per cell and the
    # compute residual reports.
    wplc = A.compute_roof_ops_s / (lanes * clock_hz)
    d.facts["compute_roof_ops_s"] = A.compute_roof_ops_s
    d.facts["compute_roof_mac_s"] = roof_mac_s
    d.facts["work_units_per_mac"] = A.operations_per_mac
    d.facts["narrowest_tensor_width"] = narrowest
    d.facts["narrowest_tensor_operators"] = narrow_ops[:6]
    d.facts["tensor_operator_count"] = len(tensor_ops)
    d.facts["lane_efficiency_at_wider_widths"] = {
        str(w): lane_efficiency(tensor_ops, w) for w in wider
    }
    d.facts["tensor_mac_per_cycle_at_roof"] = roof_mac_s / clock_hz
    d.facts["operations_by_canonical_format"] = dict(A.operations_by_format)
    d.facts["execution_format"] = A.rom.get("execution_format")
    d.facts["rom_token_slots"] = A.rom_token_slots
    d.facts["hbm_token_slots"] = A.hbm_token_slots
    d.facts["rom_peak_weight_read_bytes_s"] = A.rom_peak_weight_read_bytes_s
    d.facts["hbm_peak_memory_bytes_s"] = A.hbm_peak_memory_bytes_s
    d.facts["compute_area_time_s"] = A.compute_area_time_s
    d.facts["compute_area_time_agreement"] = (
        A.compute_area_time_s / float(A.rom["component_times_s"]["compute"]) - 1.0
    )

    d.shared["engine.tensor.lanes.default"] = Derived(
        name="engine.tensor.lanes.default",
        value=lanes,
        unit="lanes",
        analytical_grade="derived",
        provenance="assumed",
        derivation=(
            f"The narrowest tensor operator output width in "
            f"{A.rom['model']} ({lanes}: "
            f"{', '.join(narrow_ops[:3]) if narrow_ops else 'read from the IR'}"
            f"{' and others' if len(narrow_ops) > 3 else ''}), read from "
            f"build/ir-v3/{model_slug(A)}/kernel_ir.v3.json over the "
            f"{len(tensor_ops)} kernels it declares with counter_class tensor.  "
            f"At batch 1 the cycle model's tensor rate is min(lanes, "
            f"tile_cols*issue_window, cols) x work_per_lane_cycle x clock, so "
            f"lanes above the operator's own output width are masked and "
            f"deliver nothing.  {lanes} is the largest lane count for which "
            f"EVERY tensor operator of this model runs at the full derived "
            f"roof; "
            + ("; ".join(
                f"at {w} the MAC-weighted achieved rate falls to "
                f"{lane_efficiency(tensor_ops, w) * 100:.1f}% of the roof"
                for w in wider
            ) if wider else
               "this model declares only one tensor operator width")
            + f".  The pair (lanes, work_per_lane_cycle) is a gauge split of "
            f"one analytical quantity -- their product times the clock is what "
            f"the design point pins -- and this rule fixes the split by "
            f"exactness."
        ),
        source=f"{ana}.area_fractions.compute",
    )
    d.shared["engine.tensor.work_per_lane_cycle"] = Derived(
        name="engine.tensor.work_per_lane_cycle",
        value=wplc,
        unit="work/lane/cycle",
        analytical_grade="derived",
        provenance="assumed",
        derivation=(
            f"compute roof / (lanes x clock), in work-counter units.  The roof "
            f"is the design point's OWN arithmetic over the design point's OWN "
            f"published time: "
            f"{' + '.join(f'{f} {float(n):.0f}' for f, n in sorted(A.operations_by_format.items()))} "
            f"= {A.operations:.0f} operations / component_times_s.compute "
            f"{A.rom['component_times_s']['compute']!r} s = "
            f"{A.compute_roof_ops_s:.10e} ops/s.  That identity is exact by "
            f"construction, which is the point: a literal 'bf16' index into "
            f"operations_by_canonical_format raises on a w4a8 design point and "
            f"a literal 'bf16' compute density prices one 2.7x too slow "
            f"WITHOUT raising.  Cross-checked against the technology "
            f"derivation the study built the term from -- sum over formats of "
            f"ops_f / (area_fractions.compute "
            f"{A.rom['area_fractions']['compute']!r} x silicon_area_mm2 "
            f"{A.rom['silicon_area_mm2']!r} x compute_ops_s_per_mm2[f] x "
            f"efficiencies.compute {A.compute_efficiency!r}), times "
            f"token_slots {A.rom_token_slots:g} -- which gives "
            f"{A.compute_area_time_s:.15e} s against the published "
            f"{A.rom['component_times_s']['compute']:.15e} s, agreeing to "
            f"{d.facts['compute_area_time_agreement']:+.3e} relative.  Units: "
            f"the cost table declares this parameter in work/lane/cycle and "
            f"the shipped characterized value was measured as "
            f"(tensor.multiplications + tensor.additions) / cycles; the "
            f"analytical operations count is a work count too, at "
            f"{A.operations_per_mac:g} operations per active parameter "
            f"({'the multiply-and-add fallback' if abs(A.operations_per_mac - 2.0) < 1e-9 else 'real operator accounting, NOT the multiply-and-add fallback'}), "
            f"so no conversion is needed and none is applied.  That makes the "
            f"machine's MAC rate lanes x work_per_lane_cycle / "
            f"{A.operations_per_mac:g} x clock = {roof_mac_s:.10e} MAC/s.  In "
            f"the cycle model this value divides the K extent "
            f"(ceil(tile_depth x work_scale / work_per_lane_cycle)), so it is "
            f"the reduction-tree width of one output lane -- "
            f"{roof_mac_s / clock_hz / lanes:.2f} MACs deep -- and not a "
            f"second lane count."
        ),
        source=f"{ana}.component_times_s.compute",
    )

    # Every other engine family gets the SAME roof.  The analytical model
    # prices all arithmetic at one number and draws no distinction between a
    # matmul and a norm, so neither does the derived machine.  For the
    # non-tensor families the cycle model divides directly by lanes x
    # work_per_lane_cycle (model.py:2437-2440), so the same product delivers
    # the same roof without the batch-1 saturation the tensor path has.
    for family in FAMILIES:
        if family == "tensor":
            continue
        d.shared[f"engine.{family}.lanes.default"] = Derived(
            name=f"engine.{family}.lanes.default",
            value=lanes,
            unit="lanes",
            analytical_grade="derived",
            provenance="assumed",
            derivation=(
                f"Same as engine.tensor.lanes.default.  The analytical model "
                f"prices all arithmetic at one roof and names no engine "
                f"families, so every family is given the same width and the "
                f"same per-lane depth.  For {family!r} the cycle model divides "
                f"tile work by lanes x work_per_lane_cycle directly, so the "
                f"product is the whole story."
            ),
            source=f"{ana}.area_fractions.compute",
        )
        d.shared[f"engine.{family}.work_per_lane_cycle"] = Derived(
            name=f"engine.{family}.work_per_lane_cycle",
            value=wplc,
            unit="work/lane/cycle",
            analytical_grade="derived",
            provenance="assumed",
            derivation=(
                "Same as engine.tensor.work_per_lane_cycle: one analytical "
                "compute roof, one arithmetic rate on every engine."
            ),
            source=f"{ana}.component_times_s.compute",
        )

    # -- 3.  Per-instruction fixed latency ------------------------------
    # The analytical layer_fixed_latency is built from four primitives.  The
    # only one with a cycle-model counterpart is the array pass boundary: an
    # engine instruction IS one pass through the compute array, and
    # engine.<family>.fixed_latency_cycles is charged once per engine
    # instruction after the unit is freed (model.py:2352, 2361).
    apb_cycles = int(round(A.array_pass_boundary_s * clock_hz))
    for family in FAMILIES:
        d.shared[f"engine.{family}.fixed_latency_cycles"] = Derived(
            name=f"engine.{family}.fixed_latency_cycles",
            value=apb_cycles,
            unit="cycles",
            analytical_grade="derived",
            provenance="assumed",
            derivation=(
                f"technology.json#latency.pipeline_fill_drain_s "
                f"{A.latency('pipeline_fill_drain_s'):g} s + one global wire "
                f"traversal sqrt(reticle.area_mm2) x "
                f"global_wire_delay_s_per_mm = {A.global_traversal_s:.6e} s, "
                f"the analytical array-pass boundary "
                f"{A.array_pass_boundary_s:.6e} s, times the clock = "
                f"{A.array_pass_boundary_s * clock_hz:.4f} cycles.  The "
                f"analytical model charges "
                f"{A.latency('array_pass_boundaries_per_layer'):g} of these "
                f"per layer; the cycle model charges one per engine "
                f"instruction and has no per-layer hook, so the difference "
                f"between the deployment's instructions per layer and "
                f"{A.latency('array_pass_boundaries_per_layer'):g} is a "
                f"reported residual, not a tuned parameter."
            ),
            source=f"{tech}#latency.pipeline_fill_drain_s",
        )

    # -- 4.  Weight path, ROM role --------------------------------------
    # rom.arrays is the model's independently-addressable ROM unit count.  The
    # deployment's own ROM bank plan fixes it: it is the ROM bank count the
    # base capability this pair is emitted against declares, and the ROM
    # lowering stripes one bank per weight role.
    rom_arrays = int(A.rom.get("_rom_arrays", 0)) or int(rom_arrays or 16)
    rom_bpc, rom_achieved = _q(A.rom_weight_read_bytes_s, rom_arrays, clock_hz)
    d.facts["rom_weight_read_bytes_s_target"] = A.rom_weight_read_bytes_s
    d.facts["rom_weight_read_bytes_s_achieved"] = rom_achieved
    d.facts["rom_arrays"] = rom_arrays
    d.facts["rom_interleave_stripe_bytes"] = rom_arrays * rom_bpc
    rom_resid = rom_achieved / A.rom_weight_read_bytes_s - 1.0
    d.residuals.append({
        "term": "weight_read",
        "role": "rom",
        "kind": "integer_quantisation",
        "relative": rom_resid,
        "note": (
            f"rom.bytes_per_cycle_per_array must be an integer number of bytes "
            f"per cycle; {A.rom_weight_read_bytes_s / (rom_arrays * clock_hz):.6f} "
            f"rounds to {rom_bpc}."
        ),
    })

    d.rom_only["rom.arrays.default"] = Derived(
        name="rom.arrays.default",
        value=rom_arrays,
        unit="arrays",
        analytical_grade="assumed",
        provenance="assumed",
        derivation=(
            f"{rom_arrays} independently-addressable ROM arrays, the ROM bank "
            f"count declared by the base capability this pair is emitted "
            f"against (memory.rom.banks; the ROM lowering stripes one bank per "
            f"weight role).  The analytical model fixes only the product "
            f"arrays x bytes_per_cycle_per_array x clock, so this is the "
            f"granularity choice and the next parameter is the consequence.  "
            f"NOTE: the shipped ROM capabilities advertise this under the key "
            f"'banks', which MachineModel.structural does not read (it looks "
            f"for memory.rom.arrays), so the shipped ROM runs silently used "
            f"the cost table's default of 8.  The emitted capability "
            f"advertises both keys."
        ),
        source=f"{ana}.weight_store",
    )
    d.rom_only["rom.bytes_per_cycle_per_array"] = Derived(
        name="rom.bytes_per_cycle_per_array",
        value=float(rom_bpc),
        unit="B/cycle",
        analytical_grade="derived",
        provenance="assumed",
        derivation=(
            f"The ROM weight rate ONE TOKEN engages: the design "
            f"point's aggregate array rate peak_weight_read_bytes_s "
            f"{A.rom_peak_weight_read_bytes_s:.10e} B/s (= rom area "
            f"{A.rom['area_fractions']['rom'] * A.rom['silicon_area_mm2']:.4f} "
            f"mm2 x technology_derivations.rom_read_bytes_s_per_mm2 x "
            f"efficiencies.rom_read_bandwidth, already derated) divided by "
            f"token_slots {A.rom_token_slots:g}, because a token traverses "
            f"{A.rom_token_slots:g} slot(s) in series and can engage only one "
            f"of them at a time = {A.rom_weight_read_bytes_s:.10e} B/s.  That "
            f"reproduces the published per-token term: "
            f"points[ROM].stored_weight_bytes "
            f"{A.rom['stored_weight_bytes']:.0f} / that rate = "
            f"{float(A.rom['stored_weight_bytes']) / A.rom_weight_read_bytes_s:.6e} s "
            f"against component_times_s.weight_read "
            f"{A.rom['component_times_s']['weight_read']!r} s.  "
            f"Divided by {rom_arrays} arrays and by the clock = "
            f"{A.rom_weight_read_bytes_s / (rom_arrays * clock_hz):.6f}, "
            f"rounded to {rom_bpc}.  Achieved aggregate {rom_achieved:.10e} "
            f"B/s, {rom_resid * 100:+.5f}% against the analytical value."
        ),
        source=f"{ana}.stored_weight_bytes",
    )
    d.rom_only["rom.transaction_bytes"] = Derived(
        name="rom.transaction_bytes",
        value=rom_bpc,
        unit="B",
        analytical_grade="derived",
        provenance="assumed",
        derivation=(
            "Set equal to rom.bytes_per_cycle_per_array so that the cycle "
            "model's max(1, ceil(transaction_bytes / bytes_per_cycle)) is "
            "exactly 1 and the array delivers its full derived rate.  The "
            "analytical model has no burst-size concept, so this is the only "
            "constraint on the value."
        ),
        source=f"{ana}.peak_weight_read_bytes_s",
    )
    d.rom_only["rom.interleave_bytes"] = Derived(
        name="rom.interleave_bytes",
        value=rom_bpc,
        unit="B",
        analytical_grade="derived",
        provenance="assumed",
        derivation=(
            "Set equal to the ROM burst so consecutive bursts of one weight "
            "object land on consecutive arrays and a sweep engages every array."
        ),
        source=f"{ana}.peak_weight_read_bytes_s",
    )

    # The HBM machine has no ROM.  The schema demands the names anyway.
    d.hbm_only["rom.arrays.default"] = Derived(
        name="rom.arrays.default", value=1, unit="arrays",
        analytical_grade="assumed", provenance="assumed",
        derivation=(
            f"The GPU design point {A.hbm_design!r} has no ROM "
            f"(area_fractions.rom = "
            f"{A.hbm['area_fractions']['rom']!r}).  These four rom.* values "
            f"exist because the cost-table schema requires the full parameter "
            f"set; no MEMORY_OBJECT in the HBM deployment is stamped "
            f"StorageClass.ROM, so the ROM unit pool is never scheduled."
        ),
        source=f"{ana_hbm}.area_fractions.rom",
    )
    for nm, val, unit in (
        ("rom.bytes_per_cycle_per_array", 1.0, "B/cycle"),
        ("rom.transaction_bytes", 1, "B"),
        ("rom.interleave_bytes", 1, "B"),
    ):
        d.hbm_only[nm] = Derived(
            name=nm, value=val, unit=unit,
            analytical_grade="assumed", provenance="assumed",
            derivation=(
                "Inert: the GPU design point has no ROM.  See "
                "rom.arrays.default."
            ),
            source=f"{ana_hbm}.area_fractions.rom",
        )

    d.shared["rom.read_latency_cycles"] = Derived(
        name="rom.read_latency_cycles",
        value=int(round(A.global_traversal_s * clock_hz)),
        unit="cycles",
        analytical_grade="derived",
        provenance="assumed",
        derivation=(
            f"The analytical model prices no ROM access latency.  The ROM "
            f"array is on die, so the one analytical latency primitive that "
            f"applies is a global wire traversal of the reticle: "
            f"sqrt(reticle.area_mm2 "
            f"{A.technology['reticle']['area_mm2']['value']!r}) x "
            f"global_wire_delay_s_per_mm "
            f"{A.latency('global_wire_delay_s_per_mm'):g} = "
            f"{A.global_traversal_s:.6e} s = "
            f"{A.global_traversal_s * clock_hz:.4f} cycles."
        ),
        source=f"{tech}#latency.global_wire_delay_s_per_mm",
    )

    # -- 5.  HBM path ---------------------------------------------------
    # Both design points provision HBM in stacks, and both put 8 channels on a
    # stack (the modelling convention the shipped cost tables already use).
    # The per-channel rate comes out IDENTICAL on the two sides -- the ROM
    # point's 5 stacks x 4 devices at 1e12 B/s x 0.9 and the GPU point's 2
    # packages of 8 stacks at 8e12 B/s x 0.9 are the same stack -- so the only
    # thing that differs is how many of them each design buys.
    channels_per_stack = 8
    rom_channels, hbm_channels, per_channel_bpc = _hbm_split(
        A, clock_hz, channels_per_stack
    )
    d.facts["hbm_bytes_per_cycle_per_channel"] = per_channel_bpc
    d.facts["rom_role_hbm_channels"] = rom_channels
    d.facts["hbm_role_hbm_channels"] = hbm_channels
    d.facts["rom_role_hbm_bytes_s_achieved"] = rom_channels * per_channel_bpc * clock_hz
    d.facts["hbm_role_hbm_bytes_s_achieved"] = hbm_channels * per_channel_bpc * clock_hz

    d.shared["hbm.bytes_per_cycle_per_channel"] = Derived(
        name="hbm.bytes_per_cycle_per_channel",
        value=per_channel_bpc,
        unit="B/cycle",
        analytical_grade="derived",
        provenance="assumed",
        derivation=(
            f"One HBM3E channel, taken from the GPU point and shared: "
            f"points[GPU].kv_transfer_bytes_per_step / "
            f"component_times_s.kv_read x token_slots "
            f"{A.hbm_token_slots:g} = {A.hbm_memory_bytes_s * A.hbm_token_slots:.6e} "
            f"B/s of physical pool over {A.hbm['device_count']:g} packages x 8 "
            f"stacks x {channels_per_stack} channels = "
            f"{per_channel_bpc * clock_hz:.6e} B/s per channel = "
            f"{per_channel_bpc:g} B/cycle at this clock.  The COUNT each "
            f"collapsed logical device carries is that design's provisioning "
            f"divided by the slots a token traverses: the GPU role gets "
            f"{hbm_channels} channels for {A.hbm_memory_bytes_s:.6e} B/s and "
            + (f"the ROM role {rom_channels} channels for "
               f"{A.rom_kv_read_bytes_s:.6e} B/s of KV."
               if A.rom_kv_store == "hbm" else
               f"the ROM role a single INERT channel, because its kv_store is "
               f"{A.rom_kv_store!r} and its area_fractions.hbm_phy is "
               f"{A.rom['area_fractions']['hbm_phy']!r} -- it buys no HBM at "
               f"all.")
            + f"  The two design points buy different numbers of the SAME "
            f"channel, which is why hbm.channels is the only HBM parameter the "
            f"two machines are permitted to differ on."
        ),
        source=f"{ana_hbm}.kv_transfer_bytes_per_step",
    )
    tx = int(round(per_channel_bpc * 2)) if per_channel_bpc != int(per_channel_bpc) \
        else int(per_channel_bpc)
    if tx / per_channel_bpc != round(tx / per_channel_bpc):
        raise DerivationError(
            f"hbm.transaction_bytes {tx} is not an exact multiple of "
            f"bytes_per_cycle_per_channel {per_channel_bpc}"
        )
    d.shared["hbm.transaction_bytes"] = Derived(
        name="hbm.transaction_bytes",
        value=tx,
        unit="B",
        analytical_grade="derived",
        provenance="assumed",
        derivation=(
            f"{tx} B = {tx / per_channel_bpc:.0f} x "
            f"hbm.bytes_per_cycle_per_channel, the smallest integer burst for "
            f"which the cycle model's ceil(transaction_bytes / "
            f"bytes_per_cycle) is exact and no channel bandwidth is lost to "
            f"quantisation.  The analytical model has no burst-size concept."
        ),
        source=f"{ana}.kv_transfer_bytes_per_step",
    )
    d.shared["hbm.interleave_bytes"] = Derived(
        name="hbm.interleave_bytes", value=tx, unit="B",
        analytical_grade="derived", provenance="assumed",
        derivation=(
            "Set equal to the HBM burst so consecutive bursts stripe across "
            "channels."
        ),
        source=f"{ana}.kv_transfer_bytes_per_step",
    )
    kv_cycles = int(round(A.kv_round_trip_s * clock_hz))
    for nm in ("hbm.read_latency_cycles", "hbm.write_latency_cycles"):
        d.shared[nm] = Derived(
            name=nm, value=kv_cycles, unit="cycles",
            analytical_grade="derived", provenance="assumed",
            derivation=(
                f"The analytical layer_fixed_latency charges one KV round trip "
                f"per layer: sram_access_s {A.latency('sram_access_s'):g} + one "
                f"global traversal {A.global_traversal_s:.6e} = "
                f"{A.kv_round_trip_s:.6e} s = "
                f"{A.kv_round_trip_s * clock_hz:.4f} cycles.  points[GPU] "
                f"holds KV in {A.hbm_kv_store!r} and points[ROM] in "
                f"{A.rom_kv_store!r}; the primitive is a round trip to "
                f"whichever store holds it, so it is charged identically on "
                f"both machines and is shared."
            ),
            source=f"{tech}#latency.sram_access_s",
        )
    d.rom_only["hbm.channels.default"] = Derived(
        name="hbm.channels.default", value=rom_channels, unit="channels",
        analytical_grade="derived" if A.rom_kv_store == "hbm" else "assumed",
        provenance="assumed",
        derivation=(
            (f"{rom_channels // channels_per_stack} HBM3E stacks x "
             f"{channels_per_stack} channels.  points[ROM].area_fractions."
             f"hbm_phy {A.rom['area_fractions']['hbm_phy']!r} of "
             f"{A.rom['silicon_area_mm2'] / A.rom['device_count']:.0f} mm2 per "
             f"device at 10 mm2 per stack over "
             f"{A.rom['device_count']:g} devices, divided by token_slots "
             f"{A.rom_token_slots:g} because a token engages one slot at a "
             f"time, serving KV alone at {A.rom_kv_read_bytes_s:.6e} B/s "
             f"(kv_transfer_bytes_per_step / component_times_s.kv_read)."
             if A.rom_kv_store == "hbm" else
             f"ONE INERT CHANNEL.  points[ROM].kv_store is {A.rom_kv_store!r} "
             f"and points[ROM].area_fractions.hbm_phy is "
             f"{A.rom['area_fractions']['hbm_phy']!r}: this design point buys "
             f"no HBM at all and its KV is derived onto the SRAM path instead "
             f"(see sram.bytes_per_cycle_per_port).  The channel exists "
             f"because the cost-table schema requires the full parameter set.")
        ),
        source=f"{ana}.area_fractions.hbm_phy",
    )
    d.hbm_only["hbm.channels.default"] = Derived(
        name="hbm.channels.default", value=hbm_channels, unit="channels",
        analytical_grade="derived", provenance="assumed",
        derivation=(
            f"{hbm_channels // channels_per_stack} HBM3E stacks x "
            f"{channels_per_stack} channels: "
            f"{A.hbm['device_count']:g} B200 packages of 8 stacks divided by "
            f"token_slots {A.hbm_token_slots:g}, serving weights AND KV from "
            f"one pool (overlap_rule {A.hbm['overlap_rule']!r}) at "
            f"{A.hbm_memory_bytes_s:.6e} B/s "
            f"(kv_transfer_bytes_per_step / component_times_s.kv_read; the "
            f"weight term cannot be used in its place because on an MoE model "
            f"it also carries the engaged-device correction)."
        ),
        source=f"{ana_hbm}.kv_transfer_bytes_per_step",
    )

    # -- 6.  SRAM -------------------------------------------------------
    # Two different things depending on what the ROM design point does with
    # its KV.
    #
    # When both points hold KV in HBM, neither allocates SRAM area
    # (area_fractions.sram 0.0) and there is no analytical SRAM bandwidth to
    # reproduce.  The cycle model still needs an activation store; rather than
    # invent one it is given a rate that cannot bind, so that no simulated time
    # is attributed to a store the analytical model does not price.  That is
    # stated, not hidden: it makes the derived machine an upper bound.
    #
    # When the ROM design point's kv_store is `sram` it DOES allocate SRAM area
    # and its KV term IS an SRAM term, so the ROM machine's SRAM rate is
    # derived from it and only the GPU machine keeps the non-binding store.
    # The two then differ on the three SRAM rate parameters, which is why
    # allowlist_for() adds them for exactly this case and for no other.
    sram_banks, sram_ports = 32, 4
    kv_on_sram = A.rom_kv_store == "sram"
    neutral_bpc = _cannot_bind_bytes_per_cycle(
        max(A.rom_weight_read_bytes_s, A.hbm_memory_bytes_s, A.rom_kv_read_bytes_s),
        sram_banks * sram_ports, clock_hz,
    )
    if kv_on_sram:
        rom_sram_bpc, rom_sram_achieved = _q(
            A.rom_kv_read_bytes_s, sram_banks * sram_ports, clock_hz
        )
        d.facts["rom_role_sram_bytes_s_target"] = A.rom_kv_read_bytes_s
        d.facts["rom_role_sram_bytes_s_achieved"] = rom_sram_achieved
        d.residuals.append({
            "term": "kv_read",
            "role": "rom",
            "kind": "integer_quantisation",
            "relative": rom_sram_achieved / A.rom_kv_read_bytes_s - 1.0,
            "note": (
                f"sram.bytes_per_cycle_per_port must be an integer number of "
                f"bytes per cycle; "
                f"{A.rom_kv_read_bytes_s / (sram_banks * sram_ports * clock_hz):.6f} "
                f"rounds to {rom_sram_bpc}."
            ),
        })
    else:
        rom_sram_bpc, rom_sram_achieved = neutral_bpc, None

    d.shared["sram.banks.default"] = Derived(
        name="sram.banks.default", value=sram_banks, unit="banks",
        analytical_grade="assumed", provenance="assumed",
        derivation=(
            f"{sram_banks} banks, the bank count the shipped single-chip "
            f"capabilities on both sides already declare, kept so the compiled "
            f"bank masks mean what they meant before.  points[ROM] allocates "
            f"area_fractions.sram {A.rom['area_fractions']['sram']!r} and "
            f"points[GPU] {A.hbm['area_fractions']['sram']!r}; the analytical "
            f"model prices no bank count on either side, so this is a "
            f"granularity choice shared by construction."
        ),
        source=f"{ana}.area_fractions.sram",
    )
    d.shared["sram.ports_per_bank.default"] = Derived(
        name="sram.ports_per_bank.default", value=sram_ports, unit="ports",
        analytical_grade="assumed", provenance="assumed",
        derivation=(
            "Chosen with sram.bytes_per_cycle_per_port.  See that parameter."
        ),
        source=f"{ana}.area_fractions.sram",
    )

    neutral_note = (
        f"The GPU design point prices NO SRAM term and allocates no SRAM area "
        f"(area_fractions.sram {A.hbm['area_fractions']['sram']!r}), so there "
        f"is nothing to reproduce.  banks x ports x this rate x clock = "
        f"{sram_banks * sram_ports * neutral_bpc * clock_hz:.6e} B/s, which "
        f"exceeds every rate this pair derives "
        f"({max(A.rom_weight_read_bytes_s, A.hbm_memory_bytes_s, A.rom_kv_read_bytes_s):.6e} "
        f"B/s) so that the activation store cannot bind and no simulated time "
        f"is attributed to a store the analytical model does not price.  This "
        f"is a deliberate neutralisation for a validation experiment: the "
        f"derived machine is NOT a complete machine and its absolute tokens/s "
        f"is an upper bound."
    )
    rom_note = (
        f"points[ROM].kv_store is 'sram', so this store is NOT unpriced on the "
        f"ROM side: it is the KV array.  "
        f"points[ROM].kv_transfer_bytes_per_step "
        f"{A.rom['kv_transfer_bytes_per_step']:.0f} / component_times_s.kv_read "
        f"{A.rom['component_times_s']['kv_read']!r} s = "
        f"{A.rom_kv_read_bytes_s:.6e} B/s (the design point's SRAM read "
        f"bandwidth, area_fractions.sram "
        f"{A.rom['area_fractions']['sram']!r} x silicon_area_mm2 x "
        f"technology_derivations.sram_read_bytes_s_per_mm2 x "
        f"efficiencies.sram_read_bandwidth, divided by token_slots "
        f"{A.rom_token_slots:g}), over {sram_banks} banks x {sram_ports} "
        f"ports and the clock, rounded to an integer.  Achieved aggregate "
        f"{(rom_sram_achieved or 0.0):.6e} B/s.  The GPU point holds KV in HBM "
        f"and allocates no SRAM area at all, so its SRAM keeps the "
        f"non-binding rate -- a difference that runs AGAINST the ROM side and "
        f"is cited in the KV-path allowlist."
    )
    for name, unit, rom_value, hbm_value, note in (
        ("sram.bytes_per_cycle_per_port", "B/cycle",
         float(rom_sram_bpc), float(neutral_bpc), None),
        ("sram.transaction_bytes", "B", rom_sram_bpc, neutral_bpc,
         "Set equal to sram.bytes_per_cycle_per_port so the model's ceil() is "
         "exact.  See that parameter."),
        ("sram.interleave_bytes", "B", rom_sram_bpc, neutral_bpc,
         "Set equal to the SRAM burst so consecutive bursts stripe across "
         "ports.  See sram.bytes_per_cycle_per_port."),
    ):
        rom_text = note or (rom_note if kv_on_sram else neutral_note)
        hbm_text = note or neutral_note
        grade = "derived" if (kv_on_sram and note is None) else "assumed"
        if kv_on_sram:
            d.rom_only[name] = Derived(
                name=name, value=rom_value, unit=unit,
                analytical_grade=grade, provenance="assumed",
                derivation=rom_text, source=f"{ana}.kv_transfer_bytes_per_step",
            )
            d.hbm_only[name] = Derived(
                name=name, value=hbm_value, unit=unit,
                analytical_grade="assumed", provenance="assumed",
                derivation=hbm_text, source=f"{ana_hbm}.area_fractions.sram",
            )
        else:
            d.shared[name] = Derived(
                name=name, value=hbm_value, unit=unit,
                analytical_grade="assumed", provenance="assumed",
                derivation=hbm_text, source=f"{ana}.area_fractions.sram",
            )
    sram_lat = int(round(A.latency("sram_access_s") * clock_hz))
    for nm in ("sram.read_latency_cycles", "sram.write_latency_cycles"):
        d.shared[nm] = Derived(
            name=nm, value=sram_lat, unit="cycles",
            analytical_grade="derived", provenance="assumed",
            derivation=(
                f"technology.json#latency.sram_access_s "
                f"{A.latency('sram_access_s'):g} s x clock = "
                f"{A.latency('sram_access_s') * clock_hz:.4f} cycles."
            ),
            source=f"{tech}#latency.sram_access_s",
        )

    # -- 7.  Engine byte ports ------------------------------------------
    # engine.<family>.bytes_per_cycle prices an engine's own byte path.  The
    # analytical model has no such term, and at the derived clock the shipped
    # 64 B/cycle would throttle the DMA engine 7400x below the ROM array it is
    # meant to drain.  Both machines are therefore given the larger of the two
    # weight-path rates, so the engine port cannot bind.
    port_bpc = max(
        rom_achieved,
        d.facts["hbm_role_hbm_bytes_s_achieved"],
        A.rom_kv_read_bytes_s,
        rom_sram_achieved or 0.0,
    ) / clock_hz
    for family in FAMILIES:
        d.shared[f"engine.{family}.bytes_per_cycle"] = Derived(
            name=f"engine.{family}.bytes_per_cycle", value=port_bpc, unit="B/cycle",
            analytical_grade="assumed", provenance="assumed",
            derivation=(
                f"The analytical model prices no engine byte-port bandwidth.  "
                f"Both machines are given the larger of the pair's weight-path "
                f"rates ({port_bpc * clock_hz:.6e} B/s) so that no simulated "
                f"time is attributed to an engine port the analytical model "
                f"does not model.  At the shipped 64 B/cycle this would "
                f"throttle DMA to {64 * clock_hz:.3e} B/s, "
                f"{port_bpc / 64:.0f}x below the ROM array it drains."
            ),
            source=f"{ana}.peak_weight_read_bytes_s",
        )

    # -- 8.  Structural counts the compiler and the model share ----------
    for family in FAMILIES:
        d.shared[f"engine.{family}.queues.default"] = Derived(
            name=f"engine.{family}.queues.default", value=SHARED_QUEUES[family],
            unit="queues", analytical_grade="assumed", provenance="assumed",
            derivation=(
                f"Submission queues, shared by both machines by construction.  "
                f"Taken from the shipped ROM capability where it declares one, "
                f"else from the shipped HBM capability, so neither backend's "
                f"lowering sees a queue count it has not been exercised with.  "
                f"The analytical model names no queues.  This "
                f"is a compute-side structural count, so D1 requires the two "
                f"machines to agree on it and they do."
            ),
        )
        d.shared[f"engine.{family}.queue_depth.default"] = Derived(
            name=f"engine.{family}.queue_depth.default",
            value=SHARED_QUEUE_DEPTH[family], unit="descriptors",
            analytical_grade="assumed", provenance="assumed",
            derivation=(
                "Carried unchanged from configs/hardware/"
                "abi3_cost_sky130_rom_v2.json, where it is graded assumed and "
                "is a node-independent descriptor count.  The analytical model "
                "prices no queue occupancy."
            ),
        )
        d.shared[f"engine.{family}.minimum_cycles"] = Derived(
            name=f"engine.{family}.minimum_cycles", value=1, unit="cycles",
            analytical_grade="assumed", provenance="assumed",
            derivation=(
                "The schema minimum.  The analytical model prices no "
                "per-instruction floor, so the derived machine imposes the "
                "smallest one the cycle model permits."
            ),
        )
        d.shared[f"engine.{family}.tile_issue_cycles"] = Derived(
            name=f"engine.{family}.tile_issue_cycles", value=1, unit="cycles",
            analytical_grade="assumed", provenance="assumed",
            derivation=(
                "The schema minimum.  This is a hard floor on the tensor "
                "path's per-tile cost (model.py:2427-2436); the analytical "
                "model prices no tile sequencer, so it is set as low as the "
                "cycle model allows and its residual contribution is reported "
                "by the run's tile_issue_cycles counter."
            ),
        )
        d.shared[f"engine.{family}.tile_pipeline_depth.default"] = Derived(
            name=f"engine.{family}.tile_pipeline_depth.default", value=2,
            unit="tiles", analytical_grade="assumed", provenance="assumed",
            derivation=(
                "Carried unchanged from abi3_cost_sky130_rom_v2.json.  Read "
                "only when a SCHEDULE leaves issue_window at zero, which no "
                "deployment in this repository does."
            ),
        )

    # -- 9.  Sequencer and the rest --------------------------------------
    seq = {
        "sequencer.fetch_cycles": (1, "The cycle model's instruction fetch."),
        "sequencer.decode_cycles": (1, "The cycle model's instruction decode."),
        "sequencer.issue_cycles": (1, "The cycle model's descriptor issue."),
    }
    for nm, (val, what) in seq.items():
        d.shared[nm] = Derived(
            name=nm, value=val, unit="cycles",
            analytical_grade="derived", provenance="assumed",
            derivation=(
                f"{what}  These three are the machine's per-instruction front "
                f"end and their sum is what technology.json#latency."
                f"sequencer_issue_decode_s = {seq_s:g} s prices; that identity "
                f"is what fixes clock.frequency_hz, so they cannot be changed "
                f"without changing the clock."
            ),
            source=f"{tech}#latency.sequencer_issue_decode_s",
        )
    for nm, val in (
        ("sequencer.predicate_cycles", 1),
        ("sequencer.branch_cycles", 2),
        ("sequencer.loop_cycles", 1),
        ("sequencer.wait_check_cycles", 1),
        ("queue.transit_cycles", 2),
    ):
        d.shared[nm] = Derived(
            name=nm, value=val, unit="cycles",
            analytical_grade="assumed", provenance="assumed",
            derivation=(
                "Not priced by the analytical model.  Carried unchanged from "
                "configs/hardware/abi3_cost_sky130_rom_v2.json, where it is "
                "graded assumed and is a node-independent cycle count; the "
                "run's issue_cycles, queue_stall_cycles and wait_stall_cycles "
                "counters report its contribution separately, so it is "
                "attributed rather than zeroed."
            ),
        )
    for nm, val, unit in (
        ("host.bytes_per_cycle", 8.0, "B/cycle"),
        ("host.latency_cycles", 500, "cycles"),
        ("host.transaction_bytes", 64, "B"),
    ):
        d.shared[nm] = Derived(
            name=nm, value=val, unit=unit,
            analytical_grade="assumed", provenance="assumed",
            derivation=(
                "Host management path, carried unchanged from "
                "abi3_cost_sky130_rom_v2.json.  The analytical model has no "
                "host term and no decode-step traffic crosses this path."
            ),
        )
    d.shared["model.max_modeled_transactions_per_access"] = Derived(
        name="model.max_modeled_transactions_per_access", value=4096,
        unit="transactions", analytical_grade="assumed", provenance="assumed",
        derivation=(
            "A simulator fidelity knob, not a machine parameter; carried "
            "unchanged.  Above it an access reserves per-unit time in bulk, "
            "which keeps total occupancy exact and only coarsens the interleave."
        ),
    )
    d.shared["state.backing_storage_class"] = Derived(
        name="state.backing_storage_class", value="SRAM", unit="storage_class",
        analytical_grade="assumed", provenance="assumed",
        derivation=(
            "STATE objects are timed as if they lived in SRAM, unchanged from "
            "the shipped tables.  ADR-003 does not bind the placement of a "
            "state resource and the analytical model has no state term."
        ),
    )

    _record_structural_residuals(d, A, lanes, wplc, clock_hz)
    return d


def model_slug(anchor: Anchor) -> str:
    return str(anchor.rom["model"]).lower().replace(".", "-")


_IR_CACHE: dict[str, list[dict[str, Any]]] = {}


def tensor_operator_widths(anchor: Anchor) -> list[dict[str, Any]]:
    """Every tensor-engine operator in the model's own neutral IR.

    The lane rule is a statement about the MODEL, not about one attention
    scheme: the batch-1 tensor rate is ``min(lanes, tile_cols * issue_window,
    cols) * work_per_lane_cycle * clock``, so a lane array wider than an
    operator's output width is masked on that operator.  Reading it off the
    IR's own ``iteration_domain.output_width`` states the rule once and lets it
    hold for GQA, MLA and MoE alike.  The Qwen3 answer is unchanged: its
    narrowest tensor operator is the key/value projection at 1024 =
    num_key_value_heads x head_dim, which is what the GQA formula this replaces
    computed.  Both DeepSeek configs carry no such pair at all
    (index_heads / index_head_dim, an MLA index path), which is why the formula
    could not be generalised and the IR can.
    """
    slug = model_slug(anchor)
    if slug in _IR_CACHE:
        return _IR_CACHE[slug]
    ir_path = REPO / "build" / "ir-v3" / slug / "kernel_ir.v3.json"
    if not ir_path.exists():
        raise DerivationError(
            f"the lane rule needs the neutral IR for {anchor.rom['model']!r} at "
            f"{_relative(ir_path)}; build it with the model's kernel-IR builder"
        )
    body = json.loads(ir_path.read_text())
    ops: list[dict[str, Any]] = []
    for kernel in body["kernels"]:
        if kernel.get("counter_class") != "tensor":
            continue
        domain = kernel.get("iteration_domain") or {}
        if "output_width" not in domain:
            continue
        width = int(domain["output_width"])
        reduction = int(domain.get("reduction_width", 1) or 1)
        ops.append({
            "kernel_id": kernel["kernel_id"],
            "kind": kernel["kind"],
            "output_width": width,
            "macs": width * reduction,
        })
    if not ops:
        raise DerivationError(
            f"{_relative(ir_path)} declares no tensor operator with an "
            f"output_width; the lane rule has nothing to read"
        )
    _IR_CACHE[slug] = ops
    return ops


def lane_efficiency(ops: Sequence[Mapping[str, Any]], lanes: int) -> float:
    """Fraction of the derived roof a lane array of this width achieves.

    MAC-weighted over the model's tensor operators: an operator of output
    width ``w`` runs at ``min(lanes, w) / lanes`` of the roof, so its cost
    scales by ``lanes / min(lanes, w)``.
    """
    work = sum(float(o["macs"]) for o in ops)
    cost = sum(
        float(o["macs"]) * lanes / min(lanes, int(o["output_width"])) for o in ops
    )
    return work / cost


def _narrowest_width(anchor: Anchor,
                     ops: Sequence[Mapping[str, Any]] | None = None) -> int:
    """The largest lane count at which EVERY tensor operator runs at the roof."""
    meta = anchor.technology.get("_model_metadata")
    if isinstance(meta, Mapping):
        # Test hook: a caller may pin the width without a built IR.
        return int(meta["num_key_value_heads"]) * int(meta["head_dim"])
    ops = ops if ops is not None else tensor_operator_widths(anchor)
    return min(int(o["output_width"]) for o in ops)


def _stacks_of(point: Mapping[str, Any]) -> int:
    return 8 * int(point["device_count"])


def _hbm_split(anchor: Anchor, clock_hz: float,
               channels_per_stack: int) -> tuple[int, int, float]:
    """Channel counts for the two roles and the per-channel rate they share.

    The PHYSICAL channel is taken from the GPU point, which buys 8 HBM3E
    stacks per package: its pool rate, multiplied back up by its own
    ``token_slots``, over its stacks and channels.  Each collapsed logical
    device then carries the number of those channels ONE TOKEN can engage --
    that design's provisioning divided by the slots a token traverses -- so
    both counts must come out whole.  This is what keeps
    ``hbm.bytes_per_cycle_per_channel`` shared while ``hbm.channels`` differs,
    which is the only HBM difference the allowlist permits.

    A ROM point whose ``kv_store`` is not ``hbm`` buys no HBM at all
    (area_fractions.hbm_phy 0.0); it gets one inert channel and its KV is
    derived onto the SRAM path instead.  Forcing an SRAM KV rate onto the HBM
    channel is what made this function reject every SRAM-KV design point in the
    study, including the headline Qwen and Flash pairs.
    """
    physical_stacks = _stacks_of(anchor.hbm)
    per_stack_physical = (
        anchor.hbm_memory_bytes_s * anchor.hbm_token_slots / physical_stacks
    )
    per_channel_bytes_s = per_stack_physical / channels_per_stack
    hbm_channels_f = anchor.hbm_memory_bytes_s / per_channel_bytes_s
    hbm_channels = int(round(hbm_channels_f))
    if abs(hbm_channels - hbm_channels_f) > 1e-6 or hbm_channels < 1:
        raise DerivationError(
            f"the GPU point's {physical_stacks} stacks over token_slots "
            f"{anchor.hbm_token_slots:g} give {hbm_channels_f:.6f} channels, "
            f"not a whole number; the collapsed logical device cannot carry a "
            f"fractional channel"
        )
    if anchor.rom_kv_store == "hbm":
        rom_channels_f = anchor.rom_kv_read_bytes_s / per_channel_bytes_s
        rom_channels = int(round(rom_channels_f))
        if abs(rom_channels - rom_channels_f) > 1e-6 or rom_channels < 1:
            raise DerivationError(
                f"the ROM point's KV bandwidth "
                f"{anchor.rom_kv_read_bytes_s:.6e} B/s is "
                f"{rom_channels_f:.6f} of the GPU point's per-channel rate "
                f"{per_channel_bytes_s:.6e} B/s, not a whole number of "
                f"channels; the two points do not share an HBM generation and "
                f"hbm.bytes_per_cycle_per_channel cannot be shared"
            )
    else:
        rom_channels = 1
    per_channel = per_channel_bytes_s / clock_hz
    b = hbm_channels * per_channel * clock_hz
    if abs(b / anchor.hbm_memory_bytes_s - 1) > 1e-9:
        raise DerivationError("HBM-role HBM aggregate does not reproduce the anchor")
    if anchor.rom_kv_store == "hbm":
        a = rom_channels * per_channel * clock_hz
        if abs(a / anchor.rom_kv_read_bytes_s - 1) > 1e-9:
            raise DerivationError(
                "ROM-role HBM aggregate does not reproduce the anchor"
            )
    return rom_channels, hbm_channels, per_channel


def _cannot_bind_bytes_per_cycle(target_bytes_s: float, units: int,
                                 clock_hz: float) -> int:
    """The smallest power-of-two B/cycle for which ``units`` cannot bind."""
    need = target_bytes_s / (units * clock_hz)
    value = 1
    while value < need:
        value *= 2
    return value


def _record_structural_residuals(d: Derivation, A: Anchor, lanes: int,
                                 wplc: float, clock_hz: float) -> None:
    """Name every analytical term the cycle model cannot express, before any run."""
    ct = A.rom["component_times_s"]
    ch = A.hbm["component_times_s"]
    d.residuals.append({
        "term": "link_latency",
        "role": "both",
        "kind": "structurally_inexpressible",
        "rom_seconds": ct["link_latency"],
        "hbm_seconds": ch["link_latency"],
        "note": (
            f"The cycle model builds NO fabric on TopologyClass.SINGLE_CHIP "
            f"(runtime/cycle/fabric.py:923-930), so a single-chip run has "
            f"structurally zero link cycles.  points[ROM] charges "
            f"{A.rom.get('hop_events_per_token', 0):g} hop events per token "
            f"({A.rom.get('hop_semantics', 'unstated')}) and points[GPU] "
            f"{A.hbm.get('hop_events_per_token', 0):g} "
            f"({A.hbm.get('hop_semantics', 'unstated')}).  The derived "
            f"machines express each anchor as ONE logical device holding the "
            f"resource one token can engage, which is exactly the "
            f"transformation that removes the inter-device fabric; the term is "
            f"therefore absent by construction and is reported, not "
            f"approximated.  It is "
            f"{ct['link_latency'] / A.rom['step_time_s'] * 100:.1f}% of the "
            f"analytical ROM step and "
            f"{ch['link_latency'] / A.hbm['step_time_s'] * 100:.1f}% of the "
            f"GPU step, so removing it is NOT neutral between the two sides "
            f"and the reconciliation reports the ratio with the analytical "
            f"link added back as well as without it."
        ),
    })
    balance = float(A.derivations["efficiencies"]["stage_balance"]["value"])
    d.residuals.append({
        "term": "step_time",
        "role": "both",
        "kind": "combination_rule",
        "note": (
            f"The five analytical component times do NOT sum to the analytical "
            f"step.  step = max(memory_time, compute_time) / "
            f"efficiencies.stage_balance + link_latency + layer_fixed_latency, "
            f"with memory_time = weight + kv when the design point shares one "
            f"memory path and max(weight, kv) when it does not "
            f"(points[ROM].overlap_rule {A.rom['overlap_rule']!r}).  "
            f"token_slots does NOT appear as a separate factor here because "
            f"the published component times ALREADY carry it "
            f"(src/opentallas/roofline.py:3288-3297): they are the per-slot "
            f"cost times the slots a token traverses.  This anchor is "
            f"token_slots {A.rom_token_slots:g} on the ROM side and "
            f"{A.hbm_token_slots:g} on the GPU side.  stage_balance "
            f"{balance!r} is applied where devices > 1 and the parallelism is "
            f"not none, which is the case on "
            f"{'both sides' if (A.rom['device_count'] > 1 and A.hbm['device_count'] > 1) else 'one side only'} "
            f"here; collapsing each point to one logical device sets "
            f"devices = 1, so the derived machines do not carry it and it is "
            f"reported."
        ),
    })
    d.residuals.append({
        "term": "weight_read",
        "role": "both",
        "kind": "slot_serialisation",
        "rom_token_slots": A.rom_token_slots,
        "hbm_token_slots": A.hbm_token_slots,
        "note": (
            f"A token traverses {A.rom_token_slots:g} slot(s) on the ROM "
            f"design and {A.hbm_token_slots:g} on the GPU design, and can "
            f"engage only one at a time.  The collapsed logical device "
            f"therefore carries the design's AGGREGATE resource DIVIDED BY ITS "
            f"OWN SLOT COUNT -- ROM weight "
            f"{A.rom_peak_weight_read_bytes_s:.6e} / {A.rom_token_slots:g} = "
            f"{A.rom_weight_read_bytes_s:.6e} B/s, GPU memory "
            f"{A.hbm_peak_memory_bytes_s:.6e} / {A.hbm_token_slots:g} = "
            f"{A.hbm_memory_bytes_s:.6e} B/s -- which is what reproduces each "
            f"side's published PER-TOKEN term.  Carrying the undivided "
            f"aggregate on both sides instead would remove a factor of "
            f"{A.rom_token_slots:g} from one machine and "
            f"{A.hbm_token_slots:g} from the other, handing the more deeply "
            f"pipelined side a "
            f"{max(A.rom_token_slots, A.hbm_token_slots) / min(A.rom_token_slots, A.hbm_token_slots):.4g}x "
            f"speed-up the study never granted it.  That is the class of "
            f"defect this generator exists to prevent, so it is not done.  "
            f"What the collapse DOES remove is the pipeline's aggregate "
            f"throughput view: the derived machines model one token's latency, "
            f"not the design's {A.rom.get('aggregate_tokens_s', float('nan')):.1f} "
            f"aggregate tokens/s."
        ),
    })
    layers = float(A.summary["num_layers"])
    fallback = abs(A.operations_per_mac - 2.0) < 1e-9
    d.residuals.append({
        "term": "compute",
        "role": "both",
        "kind": "work_disagreement",
        "operations_per_active_parameter": A.operations_per_mac,
        "note": (
            (f"The two models do not agree on the total arithmetic.  The "
             f"analytical count for this model is the explicit "
             f"active-parameter fallback, active_parameters "
             f"{A.summary['active_parameters']} x {A.operations_per_mac:g}, "
             f"with NO attention arithmetic and no context dependence.  The "
             f"cycle model counts attention separately "
             f"(attention.score_multiplications, "
             f"attention.value_multiplications), which at context "
             f"{A.context_tokens} is "
             f"{2 * layers * float(A.summary['hidden_size']) * A.context_tokens:.4g} "
             f"extra MACs per token."
             if fallback else
             f"The two models do not agree on the total arithmetic.  The "
             f"analytical count for this model is NOT the active-parameter "
             f"fallback: it is {A.operations:.6e} operations over "
             f"active_parameters {A.summary['active_parameters']}, "
             f"{A.operations_per_mac:g} per active parameter, which is real "
             f"operator accounting and therefore already carries attention "
             f"and routing arithmetic the 2.0 fallback does not.  The cycle "
             f"model counts attention against the context it is actually run "
             f"at, which is not the {A.context_tokens} the anchor is priced "
             f"at, so the two counts cannot be equal even in principle.")
            + "  The models agree on the weight-driven multiply count and "
              "disagree on the total; this is structural and cannot be tuned "
              "away."
        ),
    })
    hbm_ops = sum(float(v) for v in A.hbm["operations_by_canonical_format"].values())
    hbm_roof = hbm_ops / float(ch["compute"])
    d.residuals.append({
        "term": "compute",
        "role": "hbm",
        "kind": "shared_roof_handicap",
        "rom_roof_ops_s": A.compute_roof_ops_s,
        "hbm_own_roof_ops_s": hbm_roof,
        "ratio": hbm_roof / A.compute_roof_ops_s,
        "direction": (
            "handicaps_the_gpu" if hbm_roof > A.compute_roof_ops_s
            else "credits_the_gpu"
        ),
        "gpu_memory_over_compute_x": ch["weight_read"] / ch["compute"],
        "note": (
            f"The shared arithmetic roof is taken from the ROM point ALONE, "
            f"which is what a single derivation means and what makes every "
            f"compute parameter identical on the two machines.  The GPU point "
            f"prices its own arithmetic at a published per-part roof, not at "
            f"area x density: {hbm_ops:.6e} operations over "
            f"component_times_s.compute {ch['compute']!r} s = "
            f"{hbm_roof:.6e} ops/s, {hbm_roof / A.compute_roof_ops_s:.4g}x the "
            f"shared roof {A.compute_roof_ops_s:.6e} ops/s.  The derived GPU "
            f"machine therefore CANNOT reproduce its own analytical compute "
            f"term, and the direction is NOT the same in every cell: "
            + (f"here the shared roof is BELOW the GPU point's own, so the "
               f"derived GPU machine is HANDICAPPED by "
               f"{hbm_roof / A.compute_roof_ops_s:.4g}x."
               if hbm_roof > A.compute_roof_ops_s else
               f"here the ROM design point buys so much compute area that the "
               f"shared roof is ABOVE the GPU point's own, so the derived GPU "
               f"machine is CREDITED with "
               f"{A.compute_roof_ops_s / hbm_roof:.4g}x more arithmetic than "
               f"the study gives that part.  That favours the GPU side and "
               f"must be read as a modelling artefact, not a result.")
            + f"  It is reported rather than corrected because correcting it "
            f"would mean two compute roofs, which is the defect this generator "
            f"exists to prevent.  Whether it matters is checkable: the GPU "
            f"point is memory-bound by "
            f"{ch['weight_read'] / ch['compute']:.4g}x on the analytical side, "
            f"against a compute factor of "
            f"{hbm_roof / A.compute_roof_ops_s:.4g}x, which leaves it "
            + ("still memory-bound."
               if ch["weight_read"] / ch["compute"] > hbm_roof / A.compute_roof_ops_s
               else "COMPUTE-BOUND, which changes its regime and must be read "
                    "as a modelling artefact.")
        ),
    })
    d.residuals.append({
        "term": "weight_read",
        "role": "rom",
        "kind": "sweep_versus_touched",
        "note": (
            f"The analytical ROM weight_read term is a full sweep of the "
            f"STORED array: stored_weight_bytes {A.rom['stored_weight_bytes']} "
            f"/ peak_weight_read_bytes_s x token_slots {A.rom_token_slots:g} = "
            f"{A.rom['rom_full_array_sweep_time_s']:.6e} s per slot pass.  The "
            f"cycle model has no full-sweep semantics: it charges only the "
            f"bytes the deployment's accesses touch, and at batch 1 the weight "
            f"amplification is 1, so it will charge engaged_weight_bytes "
            f"{A.rom['engaged_weight_bytes']:.0f} "
            f"({A.rom['engaged_weight_fraction'] * 100:.2f}% of stored).  On a "
            f"sparse MoE point that fraction is small and the divergence is "
            f"the dominant one on this term.  The reconciliation must compare "
            f"the cycle model's ROM traffic against the engaged bytes and "
            f"report the sweep-versus-touched difference as a modelling "
            f"divergence, not a machine parameter."
        ),
    })
    stripe = int(d.facts.get("rom_interleave_stripe_bytes", 0))
    d.residuals.append({
        "term": "weight_read",
        "role": "rom",
        "kind": "interleave_granularity",
        "stripe_bytes": stripe,
        "note": (
            f"rom.interleave_bytes and rom.transaction_bytes are both set to "
            f"rom.bytes_per_cycle_per_array, so one full stripe across the "
            f"array pool is {d.facts.get('rom_arrays')} x "
            f"{stripe // max(int(d.facts.get('rom_arrays', 1)), 1)} = {stripe} "
            f"bytes.  runtime/cycle/model.py:1302 stripes on address // "
            f"interleave_bytes and :1336 charges ceil(bytes / "
            f"transaction_bytes) transactions, so a ROM access SMALLER than "
            f"{stripe} bytes engages only some of the arrays and any access "
            f"below one transaction costs exactly one cycle whatever its size. "
            f" Nothing in this tool checks the emitted stripe against a "
            f"deployment's actual ROM access sizes, and the stripe scales with "
            f"the model: it is a machine-side granularity assumption, not an "
            f"analytical value, and a run whose ROM reads are smaller than the "
            f"stripe will not see the derived aggregate rate."
        ),
    })
    d.residuals.append({
        "term": "layer_fixed_latency",
        "role": "both",
        "kind": "granularity",
        "note": (
            f"The analytical term is "
            f"{A.summary['layer_fixed_latency']['seconds_per_layer']:.6e} s per "
            f"layer built from four primitives; only the array-pass boundary "
            f"has a cycle-model counterpart, and the cycle model charges it per "
            f"engine INSTRUCTION, not per layer.  The layer barrier "
            f"({A.latency('layer_barrier_s'):g} s per layer, "
            f"{A.latency('layer_barrier_s') * layers * 1e6:.3f} us per token) "
            f"has no counterpart on a single chip at all."
        ),
    })


# ---------------------------------------------------------------------------
# Emission
# ---------------------------------------------------------------------------
def cost_table(d: Derivation, role: str) -> dict[str, Any]:
    A = d.anchor
    design = A.rom_design if role == "rom" else A.hbm_design
    params = {name: p.entry() for name, p in sorted(d.parameters(role).items())}
    pid = pair_id(A)
    return {
        "cost_table_id": (
            f"abi3-cost-{TECHNOLOGY_VIEW.replace('_', '-')}-"
            f"{pid.replace('_', '-')}-{role}-v1"
            if pid != LEGACY_PAIR_ID else
            f"abi3-cost-{TECHNOLOGY_VIEW.replace('_', '-')}-{role}-v1"
        ),
        "schema": "opentallas.abi3.cost_table.v1",
        "technology_view": TECHNOLOGY_VIEW,
        "version": "1.0.0",
        "description": (
            f"N5 design-target machine for the {role.upper()} role of the "
            f"analytical anchor pair {A.rom_design} vs {A.hbm_design} "
            f"({A.rom['model']}, batch {A.batch_size}, context "
            f"{A.context_tokens}).  "
            f"DERIVED, NOT MEASURED: every parameter here is an analytical "
            f"value divided by a stated denominator or an explicit statement "
            f"that the analytical model prices no counterpart, and every entry "
            f"carries its derivation in `note` and its technology.json grade in "
            f"`analytical_grade`.  Nothing in this file is characterized; the "
            f"measured SKY130 and ASAP7 tables are untouched and describe a "
            f"different machine.  Generated by tools/derive_cycle_machine.py "
            f"from {A.analytical_path}; run that tool with --check to verify "
            f"this file still matches the anchor it claims."
        ),
        "derived_from": {
            "generator": "tools/derive_cycle_machine.py",
            "analytical_artifact": A.analytical_path,
            "study_id": A.study_id,
            "design_point": design,
            "paired_with": A.hbm_design if role == "rom" else A.rom_design,
            "batch_size": A.batch_size,
            "context_tokens": A.context_tokens,
            "role": role,
            "weight_store": "rom" if role == "rom" else "hbm",
            "shared_parameter_count": len(d.shared),
            "role_specific_parameters": sorted(
                (d.rom_only if role == "rom" else d.hbm_only)
            ),
            "model": A.rom["model"],
            "rom_token_slots": A.rom_token_slots,
            "hbm_token_slots": A.hbm_token_slots,
            "rom_kv_store": A.rom_kv_store,
            "hbm_kv_store": A.hbm_kv_store,
            "aggregation": (
                f"The design point's devices are collapsed into ONE logical "
                f"device carrying the resource ONE TOKEN can engage: the "
                f"aggregate divided by that design's own token_slots "
                f"({A.rom_token_slots:g} on the ROM side, "
                f"{A.hbm_token_slots:g} on the GPU side).  That is what "
                f"reproduces each side's published PER-TOKEN component times; "
                f"carrying the undivided aggregate would remove a different "
                f"serialisation factor from each side.  Four of the five "
                f"analytical terms survive the collapse; the fifth, "
                f"link_latency, is removed by it and is reported as a "
                f"structural residual, as is the aggregate-throughput view a "
                f"pipelined design also loses."
            ),
        },
        "parameters": params,
    }


def capability(d: Derivation, role: str, base: Mapping[str, Any],
               base_path: str | None = None,
               context_positions: int | None = None) -> dict[str, Any]:
    """The emitted capability: the shipped one with the compute half replaced.

    Only what D1 requires changes: the technology view (so every structural
    count is graded ``assumed`` automatically -- ``n5_design_target`` is not in
    ``CHARACTERIZED_TECHNOLOGY_VIEWS``), the engine lane and queue counts, the
    outstanding-descriptor limit, and the memory structural counts the machine
    model reads.  Capacities, features, numeric contracts, topology class and
    every other limit are carried through untouched so that both backends lower
    the same program they lower today.
    """
    A = d.anchor
    lanes = int(d.shared["engine.tensor.lanes.default"].value)
    body = json.loads(json.dumps(base, sort_keys=True))
    body["technology_view"] = TECHNOLOGY_VIEW
    stem = Path(base_path).stem if base_path else (
        "rom_qwen3" if role == "rom" else "hbm_sram_single_chip"
    )
    pid = pair_id(A)
    body["capability_id"] = (
        f"{stem}_{TECHNOLOGY_VIEW}_v1" if pid == LEGACY_PAIR_ID
        else f"{stem}_{TECHNOLOGY_VIEW}_{pid}_v1"
    )
    # Every family is declared on BOTH records with BOTH keys.  The shipped
    # ROM capability declares no lanes for dma/selection/state and no link or
    # route engine at all, so those counts fall through to its cost table while
    # the HBM side takes them from its capability -- two machines resolving the
    # same knob from different places, which is how the shipped pair came to
    # have unequal SRAM ports.  assert_comparable() rejects that split, so the
    # emitted records close it.
    engines = {}
    for family in FAMILIES:
        entry = dict(body.get("engines", {}).get(family, {}))
        entry["lanes"] = lanes
        entry["queues"] = SHARED_QUEUES[family]
        engines[family] = entry
    body["engines"] = engines
    limits = dict(body["limits"])
    limits["max_outstanding_per_queue"] = SHARED_OUTSTANDING_PER_QUEUE
    if context_positions is not None:
        # The sharpest declared asymmetry the shipped pair carries: the ROM
        # capability caps positions at 8,256 and the HBM one at 262,144, so one
        # machine can legally be asked for a position its partner cannot serve
        # and NOTHING in the resolved-parameter comparison notices, because
        # limits are not machine parameters.  Both records are given the
        # smaller of the two, so the pair can only be exercised where both can
        # go.
        limits["max_context_positions"] = int(context_positions)
    body["limits"] = limits
    # The derivation expresses each design point as ONE logical device.  A
    # base capability that declares a cluster or a wafer would make
    # MachineModel build a fabric whose parameters _resolve_all does not
    # compare at all, which would put the biggest difference between the two
    # machines outside the assertion.  The emitted records therefore declare
    # SINGLE_CHIP, and assert_comparable refuses anything else.
    body["topology_class"] = 0
    if "max_nodes" in limits:
        limits["max_nodes"] = 1
    body["limits"] = limits

    memory = json.loads(json.dumps(body.get("memory", {}), sort_keys=True))
    # The collapse expresses the design point's devices as ONE logical device,
    # and a logical device that stands for N of them must HOLD what those N
    # hold.  The base record's capacities are one base device's, so leaving
    # them alone declares a machine too small to host the very design point it
    # is derived from: a DeepSeek-V4-Flash GPU comparator plans 229,845,618,692
    # bytes per node against the single-chip record's 103,079,215,104 and the
    # deployment is refused before it can be timed.
    #
    # This is a capacity, never a rate.  ``_resolve_all`` resolves 114
    # parameters and NOT ONE of them is a capacity -- memory.*.bytes is a
    # capability structural field that the machine model never reads for
    # timing, and the three of them are already named in
    # ``declared_asymmetries``.  So this scaling cannot move a cycle count and
    # cannot move the comparability verdict; it decides only whether a
    # deployment fits the collapsed device at all.
    devices = int(A.rom["device_count"] if role == "rom"
                  else A.hbm["device_count"])
    scaled_capacities: list[str] = []
    for klass in ("rom", "hbm", "sram"):
        entry = memory.get(klass)
        if not isinstance(entry, dict) or "bytes" not in entry:
            continue
        entry = dict(entry)
        entry["bytes"] = int(entry["bytes"]) * max(devices, 1)
        memory[klass] = entry
        if devices > 1:
            scaled_capacities.append(f"memory.{klass}.bytes")
    sram = dict(memory.get("sram", {}))
    sram["banks"] = int(d.shared["sram.banks.default"].value)
    sram["ports"] = int(d.shared["sram.ports_per_bank.default"].value)
    memory["sram"] = sram
    hbm = dict(memory.get("hbm", {}))
    hbm["channels"] = int(d.parameters(role)["hbm.channels.default"].value)
    memory["hbm"] = hbm
    if role == "rom":
        rom_mem = dict(memory.get("rom", {}))
        # The shipped capability advertises 'banks', which
        # MachineModel.structural does not read; advertise 'arrays' too so the
        # machine and the compiler see the same number.
        rom_mem["arrays"] = int(d.rom_only["rom.arrays.default"].value)
        rom_mem["banks"] = int(d.rom_only["rom.arrays.default"].value)
        memory["rom"] = rom_mem
    body["memory"] = memory
    body["derived_from"] = {
        "generator": "tools/derive_cycle_machine.py",
        "base_capability": base_path or (
            "configs/hardware/abi3_capability/"
            + ("rom_qwen3.json" if role == "rom" else "hbm_sram_single_chip.json")
        ),
        "analytical_artifact": A.analytical_path,
        "design_point": A.rom_design if role == "rom" else A.hbm_design,
        "changed": [
            "technology_view", "capability_id", "engines.*.lanes",
            "engines.*.queues", "limits.max_outstanding_per_queue",
            "memory.sram.banks", "memory.sram.ports", "memory.hbm.channels",
            "topology_class", "limits.max_nodes",
        ] + scaled_capacities + ([] if context_positions is None
             else ["limits.max_context_positions"])
          + (["memory.rom.arrays", "memory.rom.banks"] if role == "rom" else []),
        "note": (
            "technology_view n5_design_target is deliberately outside "
            "runtime/cycle/machine.py CHARACTERIZED_TECHNOLOGY_VIEWS, so every "
            "structural count this record advertises is graded `assumed` with "
            "no code change, and every run against it prints the "
            "not-a-performance-claim note.  topology_class is forced to "
            "SINGLE_CHIP because the derivation collapses the design point's "
            "devices into one logical device; this record is a MACHINE for "
            "that collapsed device and is not the deployment target of a "
            "multi-node backend."
        ),
    }
    return body


# ---------------------------------------------------------------------------
# D1: the comparability assertion
# ---------------------------------------------------------------------------
def _resolve_all(cap_body: Mapping[str, Any],
                 table_path: Path) -> dict[str, Any]:
    """Every machine parameter a SINGLE_CHIP run of this pair resolves."""
    from runtime.abi3.capability import Capability
    from runtime.cycle.machine import MachineModel, load_cost_table

    cap = Capability.from_dict(cap_body)
    model = MachineModel(cap, load_cost_table(table_path))
    model.clock_hz
    model.sequencer()
    for family in FAMILIES:
        model.engine(family)
    model.memory()
    return {
        name: {"value": p.value, "unit": p.unit, "origin": p.origin,
               "provenance": p.provenance.value}
        for name, p in model.used().items()
    }


def assert_comparable(rom_cap: Mapping[str, Any], rom_table: Path,
                      hbm_cap: Mapping[str, Any], hbm_table: Path,
                      allowlist: Mapping[str, str] | None = None,
                      ) -> dict[str, Any]:
    """Fail unless the two machines differ ONLY inside the weight-path allowlist.

    This compares the RESOLVED parameter sets, not the two documents.  A
    capability that does not advertise a structural count falls through to its
    cost table's default, so two capabilities can look identical and still
    produce machines with different SRAM ports -- which is exactly what the
    shipped Qwen pair does today.  Only the resolved view catches it.
    """
    allow = dict(WEIGHT_PATH_ALLOWLIST if allowlist is None else allowlist)
    # _resolve_all resolves the clock, the sequencer, the nine engines and the
    # memory system -- and NOTHING under fabric.*.  On a cluster or wafer
    # capability MachineModel would build a fabric whose parameters this
    # comparison never sees, which would leave the biggest difference between
    # the two machines outside the assertion.  Refuse it rather than compare
    # half a machine.
    for role, cap in (("rom", rom_cap), ("hbm", hbm_cap)):
        topo = int(cap.get("topology_class", 0) or 0)
        if topo != 0:
            raise DerivationError(
                f"the {role} capability declares topology_class {topo}, not "
                f"SINGLE_CHIP.  assert_comparable resolves no fabric.* "
                f"parameter, so a multi-node pair would be compared with its "
                f"largest difference unexamined.  The derivation collapses "
                f"every design point to one logical device precisely so this "
                f"cannot happen"
            )
    rom = _resolve_all(rom_cap, rom_table)
    hbm = _resolve_all(hbm_cap, hbm_table)
    if set(rom) != set(hbm):
        raise DerivationError(
            "the two machines resolve different parameter SETS: "
            f"only in rom {sorted(set(rom) - set(hbm))}, "
            f"only in hbm {sorted(set(hbm) - set(rom))}"
        )
    differing = {n for n in rom if rom[n]["value"] != hbm[n]["value"]}
    unexpected = sorted(differing - set(allow))
    if unexpected:
        detail = "; ".join(
            f"{n}: rom={rom[n]['value']!r} hbm={hbm[n]['value']!r}"
            for n in unexpected
        )
        raise DerivationError(
            "the two emitted machines differ outside the weight path, which is "
            "the defect this generator exists to prevent.  Offending "
            f"parameters: {detail}"
        )
    # Both machines must also resolve every shared parameter from the SAME
    # place.  A value that agrees today but arrives from a capability on one
    # side and a cost table on the other will silently diverge the moment
    # either file is edited.
    origin_split = sorted(
        n for n in rom
        if n not in allow and rom[n]["origin"] != hbm[n]["origin"]
    )
    if origin_split:
        raise DerivationError(
            "these shared parameters resolve from different origins on the two "
            f"machines and would diverge on the next edit: {origin_split}"
        )
    return {
        "parameters_compared": len(rom),
        "identical": sorted(set(rom) - differing),
        "permitted_differences": {
            n: {"rom": rom[n]["value"], "hbm": hbm[n]["value"],
                "justification": allow[n]}
            for n in sorted(differing)
        },
        "allowlist": sorted(allow),
        "allowlist_unused": sorted(set(allow) - differing),
        "rom_provenance_classes": sorted({p["provenance"] for p in rom.values()}),
        "hbm_provenance_classes": sorted({p["provenance"] for p in hbm.values()}),
    }


# ---------------------------------------------------------------------------
# The deployment-side half of D1: the C2 audit
# ---------------------------------------------------------------------------
#: SCHEDULE fields, grouped by where they enter the cycle cost.  The first
#: group is read by ``tile_mapping``, ``tensor_lane_mapping``,
#: ``apply_tile_amplification`` and ``_compute_cycles`` and decides the tile
#: decomposition itself.  The second enters queue admission
#: (``max_outstanding``, ``queue_index``), the memory scheduler (``bank_mask``,
#: ``port_mask``) or the fabric route (``noc_route_class``).  The third is
#: copied into the mapping and read by nothing that costs a cycle.
SCHEDULE_TILE_FIELDS: tuple[str, ...] = (
    "tile_rows", "tile_cols", "tile_depth", "issue_window",
)
SCHEDULE_ADMISSION_FIELDS: tuple[str, ...] = (
    "max_outstanding", "queue_index", "bank_mask", "port_mask", "noc_route_class",
)
SCHEDULE_INERT_FIELDS: tuple[str, ...] = ("resource_bound", "priority")
SCHEDULE_FIELDS: tuple[str, ...] = (
    SCHEDULE_TILE_FIELDS + SCHEDULE_ADMISSION_FIELDS + SCHEDULE_INERT_FIELDS
)

#: ``"<family>.<field>"`` -> citation.  A SCHEDULE difference is explained only
#: when the design point itself states it -- a per-side tile shape, column
#: group or reduction depth published in the analytical artifact.  No design
#: point in ``results/roofline/n5_vs_b200/analytical.json`` publishes one, so
#: the allowlist is empty and every difference the audit finds is unexplained.
#: An entry added here must cite the artifact field that justifies it.
DEPLOYMENT_AUDIT_ALLOWLIST: dict[str, str] = {}

#: The compiled deployments the repository's own comparison evidence was
#: produced from, keyed by the base capability record each was lowered
#: against.  A cell binds a side to one of these only when the cell's base
#: capability is the key AND the deployment's model is the cell's model; the
#: audit then verifies, from the deployment manifest, that it really carries
#: that capability's digest and is the exact deployment the cited evidence
#: names.  ``build/abi3`` is a build product and is not tracked, so the digests
#: are what make an audit result reproducible.
SHIPPED_DEPLOYMENTS: dict[str, dict[str, Any]] = {
    "configs/hardware/abi3_capability/rom_qwen3.json": {
        "model_id": "qwen3-8b",
        "root": "build/abi3/qwen3-8b-rom-rowfold-v1",
        "deployment_sha256": (
            "5940e5b6b5c507493fc8cf08675c43189aff8a6ecc2e4c7deeb128134893f8f9"
        ),
        "evidence": [
            "results/abi3/cycle/qwen3_rom_exact8k_b1_asap7_decode_pos8000_rowfold_depthfix_v1.json",
            "docs/PERFORMANCE_DESIGN_POSTMORTEM.md (headline table: "
            "qwen3_rom_exact8k_b1_sky130_decode_pos8002_rowfold_depthfix_v1)",
        ],
    },
    "configs/hardware/abi3_capability/hbm_sram_single_chip.json": {
        "model_id": "qwen3-8b",
        "root": "build/abi3/qwen3-8b-hbm-exact8k-b1-lane0",
        "deployment_sha256": (
            "0d7897457e14666fc057ea6223cc32e65c61e39bfe5b2ff675c3b5585fe2ce8e"
        ),
        "evidence": [
            "results/abi3/cycle/qwen3_hbm_exact8k_b1_asap7_decode_pos8000_rowfold_v1.json",
            "docs/PERFORMANCE_DESIGN_POSTMORTEM.md (headline table: "
            "qwen3_hbm_exact8k_b1_sky130_decode_pos8002_rowfold_v1)",
        ],
    },
}

#: Work-counter units per multiply-accumulate coordinate of a contraction.
#: ``FAMILY_WORK_COUNTERS['tensor']`` counts the multiply and the add
#: separately, and the RTL campaign records the two counts equal
#: (``runtime.cycle.model.CycleModel._work_scale``), so one coordinate is two
#: work units.  The audit sets both counters to the coordinate count, which is
#: how ``_work_scale`` arrives at exactly 2.0 on a compiled contraction.
TENSOR_WORK_UNITS_PER_MAC = 2.0

#: A static walk of the control stream is bounded so that a malformed program
#: cannot spin the audit forever.
_STATIC_WALK_STEP_LIMIT = 50_000_000


def decode_request_symbols(batch_size: int, context_tokens: int) -> dict[int, int]:
    """One decode step at the anchor's own context: the request the pair prices.

    ``analytical.json`` prices a design point at exactly one context, and the
    decode step it prices is the one that attends to all of it.  Both
    deployments are surveyed at these bindings, so every matched operator has
    the same useful work on both sides by construction.
    """
    from runtime.abi3.descriptors import Phase, Symbol

    return {
        int(Symbol.SPAN_TOKENS): 1,
        int(Symbol.SPAN_LAST_INDEX): 0,
        int(Symbol.POSITION_START): int(context_tokens) - 1,
        int(Symbol.POSITION_END): int(context_tokens),
        int(Symbol.CONTEXT_LENGTH): int(context_tokens),
        int(Symbol.PHASE): int(Phase.DECODE),
        int(Symbol.GENERATION_INDEX): 1,
        int(Symbol.MAX_NEW_TOKENS): 1,
        int(Symbol.BATCH): int(batch_size),
        int(Symbol.NODE_ID): 0,
        int(Symbol.NODE_COUNT): 1,
    }


def _symbol_names(symbols: Mapping[int, int]) -> dict[str, int]:
    from runtime.abi3.descriptors import Symbol

    out = {}
    for key, value in sorted(symbols.items()):
        try:
            out[Symbol(int(key)).name] = int(value)
        except ValueError:
            out[str(key)] = int(value)
    return out


class _StaticWalkError(RuntimeError):
    """The control stream cannot be walked without executing the program."""


#: Control subs that decide where the walk goes next.  Every other
#: instruction -- every engine issue, WAIT, FENCE, ASSERT, NOP -- leaves the
#: walk at ``pc + 1`` with the loop stack it already had.
_PC_REDIRECTING_CONTROL = frozenset({
    "LOOP_SETUP", "LOOP_NEXT", "BRANCH", "COMPLETE", "TRAP",
})


def _static_issues(dep: Any, symbols: Mapping[int, int],
                   entrypoint_id: int = 0,
                   ) -> tuple[list[tuple[int, dict[int, int], bool]], dict[str, Any]]:
    """``(operator id, loop bindings, conditional)`` per engine issue, and a walk report.

    This interprets the CONTROL stream and nothing else: LOOP_SETUP and
    LOOP_NEXT with the device's own ``loop_trip_count``, BRANCH, COMPLETE, and
    every predicate whose truth is a function of the request symbols and loop
    state.  The loop bindings are kept per issue because a symbol-bounded
    loop's final iteration clamps the views it walks.

    A predicate whose truth is a word in device memory (BOOLEAN_OBJECT,
    EOS_MEMBER) or a fact about the running engines (ENGINE_STATUS,
    ROUTE_VALID) cannot be evaluated without running the program.  That is not
    by itself a reason to refuse, and refusing was too blunt: it is only a
    reason to refuse when the two arms *go different places*.

    Predication in ABI-3 is not a branch.  A predicated instruction that is not
    a control transfer has exactly one successor, ``pc + 1``, on both arms, and
    the only state this walk carries -- the pc, the loop induction map and the
    loop stack -- is untouched by an engine issue or a WAIT.  So the two arms
    rejoin immediately with identical walk state, and the union of what they
    issue is computed with no path enumeration at all: take the arm that
    issues, mark the issue *conditional*, and carry on.  The union is what a
    static survey of a program with runtime control flow should report, and
    here it is exact rather than an approximation of a fork.  (``PREDICATE_INVERT``
    does not enter: the union of the two arms is the same set either way.)

    When an unevaluable predicate gates a control transfer -- BRANCH,
    LOOP_SETUP, LOOP_NEXT, COMPLETE, TRAP -- the arms genuinely diverge, the
    union would need a real fork of the walk, and the walk still refuses rather
    than guess.

    The returned report names every predicate whose truth the walk could not
    read, so the survey can say out loud that its issue list is an upper bound.
    """
    from runtime.abi3.constants import Control, InstructionFlag, Major
    from runtime.abi3.descriptors import (
        Comparison, ExtendedDescriptorType, PredicateKind, Symbol,
    )
    from runtime.abi3.records import decode_body, split_program
    from runtime.cycle.machine import ENGINE_FAMILY_NAMES
    from runtime.cycle.model import NO_ID, TILED_FAMILIES
    from runtime.sim.device import _compare, loop_trip_count

    _, body = split_program(dep.program)
    instructions = decode_body(body)
    entry = next(
        (e for e in dep.entrypoints if int(e.get("entrypoint_id", -1)) == entrypoint_id),
        dep.entrypoints[0] if dep.entrypoints else {"first_instruction": 0},
    )
    pc = int(entry["first_instruction"])
    loops: dict[int, int] = {}
    stack: list[tuple[int, int, int]] = []
    issues: list[tuple[int, dict[int, int], bool]] = []
    unevaluable: dict[int, dict[str, Any]] = {}
    steps = 0

    def predicate(descriptor_id: int) -> bool | None:
        """The predicate's truth, or ``None`` when the walk cannot read it."""
        desc = dep.table.get(descriptor_id, ExtendedDescriptorType.PREDICATE)
        p = desc.payload
        kind = PredicateKind(p["predicate_kind"])
        if kind is PredicateKind.ALWAYS:
            return True
        if kind is PredicateKind.PHASE_IS:
            return symbols[int(Symbol.PHASE)] == p["immediate"]
        if kind is PredicateKind.COMPARE_SYMBOL:
            return _compare(Comparison(p["comparison"]),
                            symbols[int(p["selector_index"])], p["immediate"])
        if kind is PredicateKind.COMPARE_LOOP:
            return _compare(Comparison(p["comparison"]),
                            loops[int(p["selector_index"])], p["immediate"])
        if kind is PredicateKind.LOOP_FIRST:
            return loops.get(int(p["selector_index"]), -1) == 0
        if kind is PredicateKind.LOOP_LAST:
            loop = dep.table[int(p["selector_index"])]
            trip = loop_trip_count(loop.payload, symbols)
            return loops.get(int(p["selector_index"]), -1) == trip - 1
        record = unevaluable.setdefault(int(descriptor_id), {
            "predicate_id": int(descriptor_id),
            "kind": kind.name,
            "reads": (
                f"object {int(p['object_id'])} element {int(p['element_index'])}"
                if kind in (PredicateKind.BOOLEAN_OBJECT, PredicateKind.EOS_MEMBER)
                else "engine or fabric state"
            ),
            "gated_instructions": 0,
        })
        record["gated_instructions"] += 1
        return None

    def redirects_pc(ins: Any) -> bool:
        """Does this instruction decide where the walk goes next?"""
        if int(ins.major) != int(Major.CONTROL):
            return False
        try:
            return Control(ins.sub).name in _PC_REDIRECTING_CONTROL
        except ValueError:
            return False

    while 0 <= pc < len(instructions):
        steps += 1
        if steps > _STATIC_WALK_STEP_LIMIT:
            raise _StaticWalkError(
                f"the control stream did not reach COMPLETE within "
                f"{_STATIC_WALK_STEP_LIMIT} steps"
            )
        ins = instructions[pc]
        conditional = False
        if ins.flags & InstructionFlag.PREDICATED:
            taken = predicate(ins.predicate_id)
            if taken is None:
                # Unreadable truth.  Both arms of a non-transfer rejoin at
                # pc + 1 with this same loop map, so take their union; a
                # control transfer's arms do not, so refuse.
                if redirects_pc(ins):
                    kind = unevaluable[int(ins.predicate_id)]["kind"]
                    raise _StaticWalkError(
                        f"predicate {ins.predicate_id} is {kind} and gates the "
                        f"{Control(ins.sub).name} at pc {pc}: its truth is a "
                        "word in device memory, which a static walk cannot "
                        "read, and the two arms of a control transfer do not "
                        "rejoin, so their union cannot be taken without "
                        "enumerating both paths"
                    )
                conditional = True
            else:
                if ins.flags & InstructionFlag.PREDICATE_INVERT:
                    taken = not taken
                if not taken:
                    pc += 1
                    continue
        if ins.major == int(Major.CONTROL):
            sub = Control(ins.sub)
            if sub is Control.LOOP_SETUP:
                loop = dep.table.get(ins.control_id, ExtendedDescriptorType.LOOP_CONTROL)
                trip = loop_trip_count(loop.payload, symbols)
                if trip == 0:
                    pc = int(loop.payload["body_end"]) + 1
                    continue
                loops[ins.control_id] = int(loop.payload["lower_bound"])
                stack.append((ins.control_id, trip, int(loop.payload["body_start"])))
                pc += 1
                continue
            if sub is Control.LOOP_NEXT:
                if not stack:
                    raise _StaticWalkError(f"LOOP_NEXT at pc {pc} with no open loop")
                loop_id, trip, body_start = stack[-1]
                loop = dep.table[loop_id]
                step = int(loop.payload["step"])
                current = loops[loop_id] + step
                if (current - int(loop.payload["lower_bound"])) // step < trip:
                    loops[loop_id] = current
                    pc = body_start
                    continue
                stack.pop()
                loops.pop(loop_id, None)
                pc += 1
                continue
            if sub is Control.BRANCH:
                pc = int(ins.control_id)
                continue
            if sub is Control.COMPLETE:
                break
            if sub is Control.TRAP:
                raise _StaticWalkError(f"program executes TRAP at pc {pc}")
            pc += 1
            continue
        family = ENGINE_FAMILY_NAMES.get(int(ins.major))
        if family in TILED_FAMILIES and ins.descriptor_id != NO_ID:
            try:
                operator = dep.table.get(ins.descriptor_id, ExtendedDescriptorType.OPERATOR)
            except Exception:  # noqa: BLE001 -- not OPERATOR-driven
                operator = None
            if operator is not None:
                issues.append((operator.descriptor_id, dict(loops), conditional))
        pc += 1
    report = {
        "unevaluable_predicates": [
            unevaluable[k] for k in sorted(unevaluable)
        ],
        "conditional_issues": sum(1 for _, _, c in issues if c),
        "issues": len(issues),
    }
    return issues, report


def _view_bytes(view: Any) -> int:
    count = int(view.element_count)
    if view.is_sub_byte:
        return (count + 1) // 2
    return count * int(view.numpy_dtype.itemsize)


class _CostArithmetic:
    """The cycle model's own per-instruction cost arithmetic, borrowed whole.

    ``CycleModel._compute_cycles`` reads only the step, the engine parameters
    and the tile mapping, through ``_work_units`` and ``_work_scale``.  Lifting
    the three methods onto this class charges an operator exactly as
    ``CycleModel._time_steps`` would, with no restatement of the formula --
    a restated formula is how the block-loop defect survived its own tests.
    """

    def __init__(self) -> None:
        from runtime.cycle.model import CycleModel

        self._work_units = CycleModel._work_units
        self._work_scale = CycleModel._work_scale.__get__(self, _CostArithmetic)
        self._compute_cycles = CycleModel._compute_cycles.__get__(
            self, _CostArithmetic
        )


def _describe_operator(dep: Any, views: Any, operator_id: int,
                       loops: Mapping[int, int], symbols: Mapping[int, int],
                       params_for: Any, charger: _CostArithmetic | None,
                       loops_known: bool = True,
                       ) -> dict[str, Any]:
    """One OPERATOR descriptor decomposed by its SCHEDULE, per issue.

    ``loops_known`` is false only on ``survey_deployment``'s refusal fallback,
    where the loop bindings are not the program's but an empty stand-in.  A
    view that walks a loop cannot resolve against that, and the honest answer
    is a ``tile_error`` on the operator -- which the audit already counts as
    not comparable -- rather than the ``MemoryError_`` that used to escape the
    tool as a crash.  On the normal path the failure is still raised: silently
    absorbing it there would let a broken survey look like a clean one.
    """
    from runtime.abi3.constants import Dma, mnemonic
    from runtime.abi3.descriptors import ExtendedDescriptorType, Symbol
    from runtime.cycle.machine import ENGINE_FAMILY_NAMES
    from runtime.cycle.model import (
        NO_ID, TENSOR_CONTRACTIONS, MemoryAccess, ScheduleError, TraceStep,
        operand_extents, tile_mapping,
    )

    operator = dep.table.get(operator_id, ExtendedDescriptorType.OPERATOR)
    p = operator.payload
    family = ENGINE_FAMILY_NAMES.get(int(p["engine_family"]), "?")
    try:
        name = mnemonic(int(p["engine_family"]), int(p["engine_sub"]))
    except (KeyError, ValueError):
        name = f"{family}.{int(p['engine_sub'])}"
    schedule_id = int(p.get("schedule_id", NO_ID))
    if schedule_id == NO_ID:
        schedule_id = int(operator.schedule_id)
    schedule: dict[str, int] | None = None
    if schedule_id != NO_ID:
        schedule = {
            k: int(v)
            for k, v in dep.table.get(
                schedule_id, ExtendedDescriptorType.SCHEDULE
            ).payload.items()
            if isinstance(v, int)
        }
    operands: dict[str, dict[str, Any]] = {}
    dims: dict[str, tuple[int, ...]] = {}
    objects: dict[str, int] = {}
    slots = [(f"in{i}", int(p[f"input_view_{i}"])) for i in range(4)]
    slots += [(f"out{i}", int(p[f"output_view_{i}"])) for i in range(2)]
    for slot, view_id in slots:
        if view_id == NO_ID:
            continue
        try:
            view = views.resolve(view_id, loops, symbols)
        except Exception as exc:  # noqa: BLE001 -- re-raised unless guessing
            if loops_known:
                raise
            return {
                "operator_id": operator_id, "family": family, "mnemonic": name,
                "schedule_id": schedule_id,
                "schedule": (
                    {f: schedule.get(f, 0) for f in SCHEDULE_FIELDS}
                    if schedule else None
                ),
                "operands": operands,
                "extent": {"rows": 0, "cols": 0, "depth": 0},
                "useful_work": 0,
                "tile_error": (
                    f"operand {slot} (view {view_id}) could not be resolved "
                    f"because the static walk refused and the loop bindings "
                    f"are unknown: {type(exc).__name__}: {exc}"
                ),
            }
        dims[slot] = tuple(int(d) for d in view.dims)
        objects[slot] = int(view.object_id)
        operands[slot] = {
            "view_id": view_id, "dims": list(dims[slot]),
            "dtype": int(view.dtype), "bytes": _view_bytes(view),
            "object_id": int(view.object_id),
        }
    step = TraceStep(
        index=0, kind="ENGINE", major=int(p["engine_family"]),
        sub=int(p["engine_sub"]), mnemonic=name, family=family,
        operator_id=operator_id, schedule_id=schedule_id, schedule=schedule,
        operand_dims=dims, operand_objects=objects,
    )
    rows, cols, depth = operand_extents(step)
    if family == "attention":
        # The functional device records the positions one attention operator
        # attended as a counter; the cycle model reads its reduction depth from
        # that counter first and from the KV join's row axis only as a
        # fallback.  A decode step attends to the whole context.
        depth = int(symbols[int(Symbol.CONTEXT_LENGTH)])
        step.counter_delta["attention.context_positions"] = depth
    if family == "tensor" and name in TENSOR_CONTRACTIONS:
        macs = rows * cols * depth
        step.counter_delta["tensor.multiplications"] = macs
        step.counter_delta["tensor.additions"] = macs
    rec: dict[str, Any] = {
        "operator_id": operator_id, "family": family, "mnemonic": name,
        "schedule_id": schedule_id,
        "schedule": {f: schedule.get(f, 0) for f in SCHEDULE_FIELDS} if schedule else None,
        "operands": operands,
        "extent": {"rows": rows, "cols": cols, "depth": depth},
        "useful_work": rows * cols * depth,
    }
    params = params_for(family)
    try:
        mapping = tile_mapping(step, params)
    except ScheduleError as exc:
        rec["tile_error"] = str(exc)
        return rec
    rec.update({
        "tiles": mapping.tiles,
        "schedule_tiles": mapping.schedule_tiles,
        "row_tiles": mapping.row_tiles, "col_tiles": mapping.col_tiles,
        "depth_tiles": mapping.depth_tiles,
        "issued_work": mapping.issued_work,
        "padding_work": mapping.padding_work,
        "padding_fraction": (
            round(mapping.padding_work / mapping.issued_work, 6)
            if mapping.issued_work else 0.0
        ),
        "issue_window": mapping.issue_window,
        "max_outstanding": mapping.max_outstanding,
        "column_group_span": mapping.tile_cols * mapping.issue_window,
    })
    if mapping.tensor_lanes is not None:
        rec["output_waves"] = mapping.tensor_lanes.output_waves
        rec["column_groups"] = mapping.tensor_lanes.column_groups
        rec["masked_lane_slots"] = mapping.tensor_lanes.masked_lane_slots
        rec["effective_tensor_width"] = min(params.lanes, rec["column_group_span"])
    if family == "dma":
        # Static payload model: the moved operand once each way, plus the
        # index an indexed transfer reads.  The functional device's exact
        # access list is what the cycle model times; this is the payload the
        # operator names, which is what "bytes per tile" means here.
        data = {k: v for k, v in operands.items() if k != "in0"} or dict(operands)
        payload = min((v["bytes"] for v in data.values()), default=0)
        index_bytes = 0
        sub = int(p["engine_sub"])
        if sub in (int(Dma.GATHER), int(Dma.SCATTER)) and "in0" in operands:
            index_bytes = int(operands["in0"]["bytes"])
        surface = operands.get("out0") or next(iter(data.values()), None)
        itemsize = (
            surface["bytes"] / max(_product_dims(surface["dims"]), 1) if surface else 0.0
        )
        rec["payload_bytes"] = payload
        rec["index_bytes"] = index_bytes
        # The extent the cycle model tiles is the whole destination surface,
        # whatever the payload: a one-row KV scatter is tiled over the cache.
        rec["surface_bytes"] = int(round(mapping.useful_work * itemsize))
        rec["payload_bytes_per_tile"] = (
            round(payload / mapping.tiles, 3) if mapping.tiles else 0.0
        )
        left = objects.get("in0")
        right = objects.get("in1")
        accesses = []
        if index_bytes and left is not None:
            accesses.append(MemoryAccess(
                object_id=left, storage_class=0, address=0,
                nbytes=index_bytes, write=False,
            ))
        src = right if right is not None else left
        if src is not None:
            accesses.append(MemoryAccess(
                object_id=src, storage_class=0, address=0,
                nbytes=payload, write=False,
            ))
        out = objects.get("out0")
        if out is not None:
            accesses.append(MemoryAccess(
                object_id=out, storage_class=0, address=0,
                nbytes=payload, write=True,
            ))
        step.accesses = accesses
    rec.update(_metrics_of(step, mapping, params, charger))
    # Kept for the counterfactual re-tiling in audit_deployments; stripped
    # before the record is written.
    rec["_step"] = step
    return rec


def _metrics_of(step: Any, mapping: Any, params: Any,
                charger: _CostArithmetic | None) -> dict[str, Any]:
    """The cost-bearing consequences of one tile mapping, per issue."""
    import dataclasses

    from runtime.cycle.model import TENSOR_CONTRACTIONS, apply_tile_amplification

    out: dict[str, Any] = {}
    if step.family == "dma" and step.accesses:
        # apply_tile_amplification writes each access's re-fetch factor in
        # place, so a re-tiled counterfactual must not share the objects.
        step.accesses = [dataclasses.replace(a) for a in step.accesses]
        apply_tile_amplification(step, mapping)
        out["transferred_bytes_static"] = step.bytes_transferred
    if charger is not None and (
        step.family == "dma"
        or (step.family == "tensor" and step.mnemonic in TENSOR_CONTRACTIONS)
    ):
        cycles, tile_issue = charger._compute_cycles(step, params, mapping)
        out["cycles_per_issue"] = int(cycles)
        out["tile_issue_cycles_per_issue"] = int(tile_issue)
    return out


def _retile(rec: Mapping[str, Any], overrides: Mapping[str, int], params: Any,
            charger: _CostArithmetic | None) -> dict[str, Any] | None:
    """Re-decompose one operator with some SCHEDULE fields replaced.

    Everything else -- extents, counters, operands -- is the operator's own,
    so the difference between this and the record is the effect of exactly
    the fields overridden.
    """
    import dataclasses

    from runtime.cycle.model import ScheduleError, tile_mapping

    step = rec.get("_step")
    if step is None or step.schedule is None:
        return None
    probe = dataclasses.replace(
        step, schedule={**step.schedule, **{k: int(v) for k, v in overrides.items()}},
        accesses=[dataclasses.replace(a) for a in step.accesses],
    )
    try:
        mapping = tile_mapping(probe, params)
    except ScheduleError:
        return None
    out = {
        "tiles": mapping.tiles, "issued_work": mapping.issued_work,
        "padding_fraction": (
            round(mapping.padding_work / mapping.issued_work, 6)
            if mapping.issued_work else 0.0
        ),
    }
    if mapping.tensor_lanes is not None:
        out["output_waves"] = mapping.tensor_lanes.output_waves
    out.update(_metrics_of(probe, mapping, params, charger))
    return out


def _product_dims(dims: Sequence[int]) -> int:
    total = 1
    for d in dims:
        total *= int(d)
    return total


def _static_walk_summary(walk_error: str | None,
                         report: Mapping[str, Any]) -> str:
    """What the walk did, in one line a gate can print.

    ``"complete"`` is reserved for a walk that read every predicate it met, so
    a survey that took a union is never mistaken for an exact one.  The exact
    string is unchanged for an exact walk and for a refusal, because shipped
    artifacts quote it.
    """
    if walk_error is not None:
        return f"REFUSED ({walk_error}); every OPERATOR counted once"
    preds = report.get("unevaluable_predicates") or []
    if not preds:
        return "complete"
    conditional = int(report.get("conditional_issues", 0))
    total = int(report.get("issues", 0))
    kinds = ", ".join(sorted({str(p["kind"]) for p in preds}))
    return (
        f"complete over the UNION of both arms of {len(preds)} data-dependent "
        f"predicate(s) ({kinds}); {conditional} of {total} issues are "
        "conditional, so the issue list is an upper bound"
    )


def survey_deployment(root: Path, *, symbols: Mapping[int, int],
                      params_for: Any, charger: _CostArithmetic | None = None,
                      ) -> dict[str, Any]:
    """Every tiled operator of one deployment at one request, per issue.

    The program contains no tile loops -- one engine instruction names a whole
    contraction and its SCHEDULE descriptor carries the tile shape -- so the
    decomposition can be read off the deployment with the cycle model's own
    ``tile_mapping`` once the operand extents are resolved.  ``_static_issues``
    supplies the issue count per operator so that family totals are the totals
    ``CycleModel`` accumulates for the same request.
    """
    from runtime.abi3.deployment import Deployment
    from runtime.abi3.descriptors import ExtendedDescriptorType
    from runtime.sim.memory import ViewResolver

    dep = Deployment.read(str(root))
    views = ViewResolver(dep, None)
    operators: dict[int, dict[str, Any]] = {}
    walk_error: str | None = None
    walk_report: dict[str, Any] = {
        "unevaluable_predicates": [], "conditional_issues": 0, "issues": 0,
    }
    try:
        issues, walk_report = _static_issues(dep, symbols)
    except _StaticWalkError as exc:
        walk_error = str(exc)
        issues = []
        for desc in dep.table.descriptors():
            if desc.descriptor_type == ExtendedDescriptorType.OPERATOR:
                issues.append((desc.descriptor_id, {}, False))
    loops_known = walk_error is None
    for operator_id, loops, conditional in issues:
        rec = operators.get(operator_id)
        if rec is None:
            rec = _describe_operator(
                dep, views, operator_id, loops, symbols, params_for, charger,
                loops_known,
            )
            rec["issues"] = 0
            operators[operator_id] = rec
        else:
            probe = _describe_operator(
                dep, views, operator_id, loops, symbols, params_for, None,
                loops_known,
            )
            if probe["extent"] != rec["extent"]:
                rec.setdefault("extent_varies", []).append(probe["extent"])
        rec["issues"] += 1
        if conditional:
            # An upper bound: this issue is counted as if the predicate
            # admitted it.  Recorded per operator so the audit can name
            # exactly which operators the bound is loose on.
            rec["conditional_issues"] = rec.get("conditional_issues", 0) + 1
    classes: Counter = Counter()
    for desc in dep.table.descriptors():
        if desc.descriptor_type == ExtendedDescriptorType.MEMORY_OBJECT:
            classes[int(desc.payload.get("storage_class", -1))] += 1
    schedule_shapes: Counter = Counter()
    for desc in dep.table.descriptors():
        if desc.descriptor_type == ExtendedDescriptorType.SCHEDULE:
            q = desc.payload
            schedule_shapes[(
                int(q.get("engine_family", -1)), int(q.get("tile_rows", 0)),
                int(q.get("tile_cols", 0)), int(q.get("tile_depth", 0)),
                int(q.get("issue_window", 0)),
            )] += 1
    families: dict[str, dict[str, Any]] = {}
    for rec in operators.values():
        fam = families.setdefault(rec["family"], {
            "operators": 0, "operations": 0, "tiles": 0, "useful_work": 0,
            "issued_work": 0, "padding_work": 0, "tile_errors": 0,
        })
        fam["operators"] += 1
        fam["operations"] += rec["issues"]
        if "tiles" not in rec:
            fam["tile_errors"] += 1
            continue
        n = rec["issues"]
        fam["tiles"] += rec["tiles"] * n
        fam["useful_work"] += rec["useful_work"] * n
        fam["issued_work"] += rec["issued_work"] * n
        fam["padding_work"] += rec["padding_work"] * n
        if "output_waves" in rec:
            fam["output_waves"] = fam.get("output_waves", 0) + rec["output_waves"] * n
            fam["column_groups"] = fam.get("column_groups", 0) + rec["column_groups"] * n
        if "cycles_per_issue" in rec:
            fam["cycles"] = fam.get("cycles", 0) + rec["cycles_per_issue"] * n
            fam["tile_issue_cycles"] = (
                fam.get("tile_issue_cycles", 0) + rec["tile_issue_cycles_per_issue"] * n
            )
        if rec["family"] == "dma":
            fam["payload_bytes"] = fam.get("payload_bytes", 0) + rec["payload_bytes"] * n
    for fam in families.values():
        fam["padding_fraction"] = (
            round(fam["padding_work"] / fam["issued_work"], 6)
            if fam["issued_work"] else 0.0
        )
    tensor_spans = sorted({
        r["column_group_span"] for r in operators.values()
        if r["family"] == "tensor" and "column_group_span" in r
    })
    lanes = params_for("tensor").lanes
    survey: dict[str, Any] = {
        "root": _relative(Path(root)),
        "model_id": dep.model_id,
        "backend": dep.backend,
        "topology_class": int(dep.topology_class),
        "deployment_sha256": dep.deployment_digest.hex(),
        "capability_digest": dep.capability_digest,
        "request_symbols": _symbol_names(symbols),
        "static_walk": _static_walk_summary(walk_error, walk_report),
        "operators": [operators[k] for k in operators],
        "families": {k: families[k] for k in sorted(families)},
        "schedule_shapes": {
            f"engine_family={a},tile_rows={b},tile_cols={c},tile_depth={d},issue_window={e}": n
            for (a, b, c, d, e), n in sorted(schedule_shapes.items())
        },
        "column_group_spans": tensor_spans,
        "max_column_group_span": max(tensor_spans) if tensor_spans else 0,
        "effective_tensor_width_caps": sorted({min(lanes, s) for s in tensor_spans}),
        "storage_class_counts": dict(sorted(classes.items())),
    }
    if walk_error is None and walk_report.get("unevaluable_predicates"):
        # Only present when the walk was not exact, so an exact survey keeps
        # exactly the keys it has always had and its shipped artifacts do not
        # move.  Absence of this key means "every predicate was read".
        survey["static_walk_detail"] = {
            "rule": (
                "a predicate whose truth is device state does not fork this "
                "walk unless it gates a control transfer: both arms of a "
                "predicated engine issue or WAIT rejoin at pc+1 with the same "
                "loop map, so the walk takes their union and marks the issue "
                "conditional"
            ),
            "conditional_issues": int(walk_report["conditional_issues"]),
            "total_issues": int(walk_report["issues"]),
            "unevaluable_predicates": walk_report["unevaluable_predicates"],
            "bound": (
                "UPPER: every conditional issue is counted as if its predicate "
                "admitted it; the program at run time issues this many or fewer"
            ),
            "conditional_operators": sorted(
                _operator_label(r) for r in operators.values()
                if r.get("conditional_issues")
            ),
        }
    return survey


def tensor_parity_band(rom_depth: int, hbm_depth: int, rate: float, *,
                       scale: float = TENSOR_WORK_UNITS_PER_MAC,
                       tile_issue_cycles: int = 1) -> dict[str, Any]:
    """Where two reduction depths cost the same cycles per unit of depth.

    ``_compute_cycles`` charges a full depth tile
    ``max(ceil(tile_depth * scale / rate), tile_issue_cycles)`` cycles, so per
    unit of depth the two shapes cost ``k_rom / d_rom`` and ``k_hbm / d_hbm``.
    ``ceil(a / r) = k`` exactly on ``a / k <= r < a / (k - 1)``, so the band of
    rates on which both k are what they are at ``rate`` is the intersection of
    the two intervals, and parity is a fact about that whole band.
    """
    a_rom = rom_depth * scale
    a_hbm = hbm_depth * scale
    k_rom = max(math.ceil(a_rom / rate), tile_issue_cycles)
    k_hbm = max(math.ceil(a_hbm / rate), tile_issue_cycles)
    per_depth_rom = k_rom / rom_depth
    per_depth_hbm = k_hbm / hbm_depth
    lo = max(a_rom / k_rom, a_hbm / k_hbm)
    hi = min(
        a_rom / (k_rom - 1) if k_rom > 1 else math.inf,
        a_hbm / (k_hbm - 1) if k_hbm > 1 else math.inf,
    )
    if per_depth_rom == per_depth_hbm:
        favours = "neither"
    else:
        favours = "rom" if per_depth_rom < per_depth_hbm else "hbm"
    ratio = (
        max(per_depth_rom, per_depth_hbm) / min(per_depth_rom, per_depth_hbm)
        if min(per_depth_rom, per_depth_hbm) else math.inf
    )
    return {
        "rom_tile_depth": rom_depth, "hbm_tile_depth": hbm_depth,
        "work_per_lane_cycle": rate, "work_units_per_mac": scale,
        "tile_issue_cycles": tile_issue_cycles,
        "cycles_per_full_depth_tile": {"rom": k_rom, "hbm": k_hbm},
        "cycles_per_unit_depth": {"rom": per_depth_rom, "hbm": per_depth_hbm},
        "parity": per_depth_rom == per_depth_hbm,
        "favours": favours,
        "magnitude_x": ratio,
        "band": [lo, hi],
        "note": (
            "rates on which the two depths are charged alike per unit of "
            "depth; the machine rate sits inside it" if per_depth_rom == per_depth_hbm
            else "rates on which the two depths keep this same unequal charge"
        ),
    }


def _fallback_params_for(lanes: int | None) -> Any:
    from runtime.cycle.machine import EngineParams

    def params_for(family: str) -> EngineParams:
        return EngineParams(
            family=family, lanes=int(lanes or 1), queues=1, queue_depth=1,
            max_outstanding=1, work_per_lane_cycle=1.0, fixed_latency_cycles=0,
            bytes_per_cycle=1.0, minimum_cycles=1, tile_issue_cycles=1,
            tile_pipeline_depth=1,
        )
    return params_for


def _values_by_side(records: Sequence[Mapping[str, Any]], field: str,
                    source: str = "schedule") -> dict[str, int]:
    """Distinct values of one field, weighted by how often they issue."""
    counts: Counter = Counter()
    for rec in records:
        if source == "schedule":
            if not rec.get("schedule"):
                continue
            value = rec["schedule"].get(field)
        else:
            value = rec.get(field)
        if value is None:
            continue
        counts[int(value)] += int(rec.get("issues", 1))
    return {str(v): n for v, n in sorted(counts.items())}


def _modal(values: Mapping[str, int]) -> int | None:
    if not values:
        return None
    return int(max(values.items(), key=lambda kv: (kv[1], -int(kv[0])))[0])


def _favours(rom: float, hbm: float, *, lower_is_better: bool = True) -> str:
    if rom == hbm:
        return "neither"
    better_rom = rom < hbm if lower_is_better else rom > hbm
    return "rom" if better_rom else "hbm"


def _ratio(rom: float, hbm: float) -> float:
    lo, hi = min(rom, hbm), max(rom, hbm)
    if lo == 0:
        return math.inf if hi else 1.0
    return hi / lo


def _match_operators(rom_ops: Sequence[Mapping[str, Any]],
                     hbm_ops: Sequence[Mapping[str, Any]]) -> tuple[
                         list[tuple[Mapping[str, Any], Mapping[str, Any]]],
                         list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    """Pair operators that perform the same useful work on both sides.

    Program order first: the two backends lower the same neutral IR, so when
    the streams agree operator-for-operator the pairing is exact.  Otherwise
    each operator is paired with the first unpaired operator of the same
    family, mnemonic and extent; what remains is reported, not guessed.
    """
    def key(rec: Mapping[str, Any]) -> tuple[Any, ...]:
        return (rec["family"], rec["mnemonic"],
                rec["extent"]["rows"], rec["extent"]["cols"], rec["extent"]["depth"])

    if len(rom_ops) == len(hbm_ops) and all(
        key(a) == key(b) for a, b in zip(rom_ops, hbm_ops)
    ):
        return list(zip(rom_ops, hbm_ops)), [], []
    pairs: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
    unmatched_hbm = list(hbm_ops)
    unmatched_rom: list[Mapping[str, Any]] = []
    for rec in rom_ops:
        k = key(rec)
        hit = next((i for i, other in enumerate(unmatched_hbm) if key(other) == k), None)
        if hit is None:
            unmatched_rom.append(rec)
        else:
            pairs.append((rec, unmatched_hbm.pop(hit)))
    return pairs, unmatched_rom, unmatched_hbm


def _operator_label(rec: Mapping[str, Any]) -> str:
    e = rec["extent"]
    return f"{rec['mnemonic']} ({e['rows']}x{e['cols']}x{e['depth']})"


def _field_effect(family: str, field: str, rom_v: int, hbm_v: int,
                  pairs: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]],
                  params_for: Any, charger: _CostArithmetic | None,
                  parity: Mapping[str, Any] | None,
                  topology_class: int) -> dict[str, Any]:
    """Which side one differing field favours, all other fields as they are.

    For the four tile fields the answer is computed, not argued: every
    matched HBM operator carrying the HBM value is re-tiled with the ROM value
    of this one field, and the family's cost-bearing totals before and after
    say whether the ROM value costs less.  The admission and memory-scheduling
    fields do not enter ``tile_mapping``; their direction follows the rule
    that reads them, and where no rule gives one the audit says so.
    """
    fam_pairs = [(a, b) for a, b in pairs if a["family"] == family]
    params = params_for(family)

    def verdict(favours: str, effect: float | None, why: str) -> dict[str, Any]:
        return {"favours": favours, "effect_x": effect, "why": why}

    if field in SCHEDULE_TILE_FIELDS:
        subjects = [
            (a, b) for a, b in fam_pairs
            if b.get("schedule") and b["schedule"].get(field) == hbm_v
            and a.get("schedule") and a["schedule"].get(field) == rom_v
            and "tiles" in b
        ]
        if not subjects:
            return verdict("unknown", None, "no matched operator carries both values")
        metrics = {"tiles": [0, 0], "issued_work": [0, 0], "output_waves": [0, 0],
                   "cycles_per_issue": [0, 0]}
        seen = set()
        for _, b in subjects:
            after = _retile(b, {field: rom_v}, params, charger)
            if after is None:
                return verdict("unknown", None,
                               f"the ROM value {rom_v} cannot tile the HBM operator")
            n = int(b.get("issues", 1))
            for m in metrics:
                if m in b and m in after:
                    metrics[m][0] += b[m] * n
                    metrics[m][1] += after[m] * n
                    seen.add(m)

        def side(m: str) -> tuple[str, float, str]:
            before, after = metrics[m]
            if before == after:
                return "neither", 1.0, f"{m} {before:,} either way"
            # A lower HBM cost with the ROM value means the ROM value is the
            # better one for this field.
            return (
                ("rom" if after < before else "hbm"), _ratio(before, after),
                f"{m} on the HBM side {before:,} as compiled, {after:,} with "
                f"the ROM value {rom_v}",
            )

        if family == "tensor":
            # The charge itself when a machine is given; otherwise the tile
            # count, which is waves x depth tiles and so sees every field.
            order = ["cycles_per_issue", "tiles", "output_waves"]
        elif family == "dma":
            order = ["cycles_per_issue", "tiles", "issued_work"]
        else:
            order = ["tiles", "issued_work"]
        order = [m for m in order if m in seen]
        if not order:
            return verdict("unknown", None, "no cost-bearing metric could be recomputed")
        first = side(order[0])
        favours, effect, why = first
        if family not in ("tensor", "dma") and len(order) > 1:
            second = side(order[1])
            if favours == "neither" and second[0] != "neither":
                favours, effect = second[0], second[1]
                why = (
                    f"{first[2]}; {second[2]} (padded work is charged only when "
                    "a tile's work exceeds the one-cycle issue floor)"
                )
            elif second[0] not in ("neither", favours):
                favours = "mixed"
                why = f"{first[2]} but {second[2]}"
            else:
                why = f"{first[2]}; {second[2]}"
        if family == "tensor" and field == "tile_depth" and parity is not None:
            lo, hi = parity["band"]
            why += (
                f"; per unit of depth {parity['cycles_per_full_depth_tile']['rom']}/"
                f"{rom_v} against {parity['cycles_per_full_depth_tile']['hbm']}/{hbm_v} "
                f"cycles at work_per_lane_cycle {parity['work_per_lane_cycle']:.6g}, "
                f"parity band [{lo:.6g}, {hi:.6g})"
                + (": the machine rate sits inside it, and outside it the larger "
                   "depth is the cheaper" if parity["parity"] else "")
            )
        if family == "tensor" and field in ("tile_cols", "issue_window"):
            rom_cap = max((min(params.lanes, a["column_group_span"]) for a, _ in fam_pairs), default=0)
            hbm_cap = max((min(params.lanes, b["column_group_span"]) for _, b in fam_pairs), default=0)
            why += (
                f"; effective tensor width min(lanes={params.lanes}, tile_cols x "
                f"issue_window) {rom_cap} vs {hbm_cap}"
            )
        if family == "tensor" and field == "tile_rows" and favours == "neither":
            rows = max((a["extent"]["rows"] for a, _ in fam_pairs), default=0)
            why += f"; every tensor operator has rows {rows} <= {min(rom_v, hbm_v)} at this request"
        return verdict(favours, effect, why)
    if field == "max_outstanding":
        rom_b = min(params.queue_depth, rom_v)
        hbm_b = min(params.queue_depth, hbm_v)
        if rom_b == hbm_b:
            return verdict("neither", 1.0, (
                f"admission is bounded by min(queue_depth={params.queue_depth}, "
                f"max_outstanding), {rom_b} on both sides at this machine"
            ))
        return verdict(_favours(rom_b, hbm_b, lower_is_better=False), _ratio(rom_b, hbm_b), (
            f"admission bound min(queue_depth={params.queue_depth}, max_outstanding) "
            f"{rom_b} vs {hbm_b}"
        ))
    if field == "queue_index":
        rom_q = len({a["schedule"]["queue_index"] for a, _ in fam_pairs if a.get("schedule")})
        hbm_q = len({b["schedule"]["queue_index"] for _, b in fam_pairs if b.get("schedule")})
        return verdict(_favours(rom_q, hbm_q, lower_is_better=False), _ratio(rom_q, hbm_q), (
            f"operators spread over {rom_q} vs {hbm_q} {family} queue(s) of the "
            f"{params.queues} the machine has"
        ))
    if field in ("bank_mask", "port_mask"):
        return verdict("unknown", None, (
            f"{field} selects banks/ports in MemorySystem.schedule; the direction "
            "is a property of the placement and is not derived by this audit"
        ))
    if field == "noc_route_class":
        if topology_class == 0:
            return verdict("neither", 1.0, "SINGLE_CHIP builds no fabric, so no route is selected")
        return verdict("unknown", None, "selects the fabric route; not derived by this audit")
    return verdict("neither", 1.0, "not read by the cycle model")


def _shape(records: Sequence[Mapping[str, Any]]) -> str:
    """The modal tile shape of a family on one side, ``rows x cols x depth``."""
    parts = []
    for f in ("tile_rows", "tile_cols", "tile_depth"):
        m = _modal(_values_by_side(records, f))
        parts.append("?" if m is None else str(m))
    return "x".join(parts)


def _fx(x: float | None) -> str:
    if x is None or x == math.inf:
        return ""
    if abs(x - 1.0) < 0.005:
        return f"{x:.4f}x"
    return f"{x:.4g}x"


def _render_verdict(comparable: bool, pairs: Sequence[Any], fields_compared: int,
                    allow: Mapping[str, str], unexplained: Sequence[Mapping[str, Any]],
                    program_mismatch: bool, only_rom: Sequence[Any],
                    only_hbm: Sequence[Any], tile_errors: Sequence[Any],
                    family_rows: Mapping[str, Any],
                    operator_asymmetries: Sequence[Mapping[str, Any]],
                    rom: Mapping[str, Any], hbm: Mapping[str, Any],
                    parity: Mapping[str, Any] | None, lanes: int) -> str:
    """One sentence a gate can print: the tile-shape asymmetries first."""
    if comparable:
        return (
            f"COMPARABLE: {len(pairs)} operators matched operator-for-operator with "
            f"identical SCHEDULE fields in every family ({fields_compared} fields "
            f"compared); tiles per step equal in every family"
            + (f"; {len(allow)} allowlisted difference(s), all cited" if allow else "")
            + ".  The machine files alone decide the rate."
        )
    by_key = {(a["family"], a["field"]): a for a in unexplained}
    clauses: list[str] = []
    families = ["tensor", "attention", "dma", "vector"] + sorted(
        {a["family"] for a in unexplained} - {"tensor", "attention", "dma", "vector"}
    )
    for family in families:
        tile_diffs = [by_key[(family, f)] for f in SCHEDULE_TILE_FIELDS if (family, f) in by_key]
        if not tile_diffs:
            continue
        rom_ops = [r for r in rom["operators"] if r["family"] == family]
        hbm_ops = [r for r in hbm["operators"] if r["family"] == family]
        row = family_rows.get(family, {})
        if family == "tensor":
            bits = []
            for f in ("tile_depth", "tile_rows"):
                a = by_key.get((family, f))
                if a is None:
                    continue
                if a["favours"] == "neither":
                    if f == "tile_depth" and parity is not None:
                        lo, hi = parity["band"]
                        bits.append(
                            f"tile_depth {a['rom_value']} vs {a['hbm_value']} (neutral at "
                            f"work_per_lane_cycle {parity['work_per_lane_cycle']:.6g}, parity "
                            f"band [{lo:.6g}, {hi:.6g}); outside it the larger depth is cheaper)"
                        )
                    else:
                        bits.append(f"{f} {a['rom_value']} vs {a['hbm_value']} (neutral at batch-1 decode)")
                else:
                    bits.append(
                        f"{f} {a['rom_value']} vs {a['hbm_value']} (favours {a['favours']} "
                        f"{_fx(a['effect_x'])})"
                    )
            cols = by_key.get((family, "tile_cols"))
            win = by_key.get((family, "issue_window"))
            if cols or win:
                caps = row.get("effective_tensor_width_caps", {})
                span_rom = f"{_modal(_values_by_side(rom_ops, 'tile_cols'))}x{_modal(_values_by_side(rom_ops, 'issue_window'))}"
                span_hbm = f"{_modal(_values_by_side(hbm_ops, 'tile_cols'))}x{_modal(_values_by_side(hbm_ops, 'issue_window'))}"
                lead = cols or win
                bits.append(
                    f"tile_cols x issue_window {span_rom} vs {span_hbm} (effective tensor "
                    f"width {max(caps.get('rom', [0]))} vs {max(caps.get('hbm', [0]))} at "
                    f"lanes={lanes}, favours {lead['favours']} {_fx(lead['effect_x'])})"
                )
            cyc = row.get("cycles")
            if cyc:
                bits.append(
                    f"contraction cycles per step {cyc['rom']:,} vs {cyc['hbm']:,}"
                    + ("" if cyc["favours"] == "neither" else f" (favours {cyc['favours']} {_fx(cyc['magnitude_x'])})")
                )
            clauses.append("tensor " + ", ".join(bits))
            continue
        tiles = row.get("tiles")
        issued = row.get("issued_work")
        text = f"{family} tile {_shape(rom_ops)} vs {_shape(hbm_ops)}"
        inner = []
        if tiles:
            inner.append(
                f"tiles per step {tiles['rom']:,} vs {tiles['hbm']:,}"
                + ("" if tiles["favours"] == "neither" else f", favours {tiles['favours']} {_fx(tiles['magnitude_x'])}")
            )
        if issued and family != "dma" and issued["favours"] != (tiles or {}).get("favours"):
            inner.append(
                f"issued work incl. padding {issued['rom']:,} vs {issued['hbm']:,}"
                + ("" if issued["favours"] == "neither" else f", favours {issued['favours']} {_fx(issued['magnitude_x'])}")
            )
        if family == "dma":
            for o in [o for o in operator_asymmetries if o["family"] == "dma" and o["metric"] == "tiles_per_issue"][:2]:
                inner.append(
                    f"{o['operator']} {o['rom']} vs {o['hbm']} tiles per issue, favours "
                    f"{o['favours']} {_fx(o['magnitude_x'])}"
                )
        clauses.append(text + (" (" + "; ".join(inner) + ")" if inner else ""))
    other = [a for a in unexplained if a["field"] not in SCHEDULE_TILE_FIELDS]
    if other:
        names = sorted({a["field"] for a in other}, key=SCHEDULE_FIELDS.index)
        clauses.append(
            f"{len(other)} further cost-bearing field(s) differ ({', '.join(names)}; "
            "see asymmetries)"
        )
    if program_mismatch:
        clauses.append(
            f"{len(only_rom)} rom / {len(only_hbm)} hbm operators have no counterpart "
            "with the same useful work"
        )
    if tile_errors:
        clauses.append(f"{len(tile_errors)} operator(s) cannot be tiled")
    return (
        "NOT COMPARABLE: " + "; ".join(clauses)
        + f"; allowlist {'empty' if not allow else 'cites ' + str(len(allow))}"
        + ".  These are SCHEDULE fields, so no machine file can correct them; the "
        "deployments must be re-emitted under one SCHEDULE rule."
    )


def audit_deployments(rom_root: Path, hbm_root: Path,
                      lanes: int | None = None, *,
                      symbols: Mapping[int, int] | None = None,
                      machine: Any = None,
                      allowlist: Mapping[str, str] | None = None,
                      ) -> dict[str, Any]:
    """Do the two deployments hand either side a tile-shape advantage?

    The machine files cannot make a comparison fair on their own: the tensor
    engine's batch-1 rate is ``min(lanes, tile_cols * issue_window, cols) *
    work_per_lane_cycle * clock`` and two of those factors live in the
    deployment's SCHEDULE descriptors, the reduction depth is charged in
    ``ceil(tile_depth * scale / rate)`` quanta, and a DMA operator is charged
    once per tile.  This compares, per engine family and per operator, every
    SCHEDULE field ``tile_mapping`` reads, the tile counts and padding those
    fields produce for the same useful work, and for DMA the tile count and
    bytes per tile -- with the direction and magnitude of each difference.

    ``comparable`` is true only when no cost-bearing field differs outside the
    cited allowlist and every operator of one side has its counterpart on the
    other.  With ``machine`` (a ``MachineModel``) the tile counts are the ones
    that machine's lane count produces and the tensor and DMA charges are
    computed with the cycle model's own arithmetic; with only ``lanes`` the
    survey still decomposes every operator but charges nothing.
    """
    from runtime.abi3.constants import StorageClass

    allow = dict(DEPLOYMENT_AUDIT_ALLOWLIST if allowlist is None else allowlist)
    if symbols is None:
        symbols = decode_request_symbols(1, 8192)
    if machine is not None:
        params_cache: dict[str, Any] = {}

        def params_for(family: str) -> Any:
            if family not in params_cache:
                params_cache[family] = machine.engine(family)
            return params_cache[family]
        charger: _CostArithmetic | None = _CostArithmetic()
    else:
        params_for = _fallback_params_for(lanes)
        charger = None
    tensor_params = params_for("tensor")
    lanes = int(tensor_params.lanes)

    rom = survey_deployment(rom_root, symbols=symbols, params_for=params_for, charger=charger)
    hbm = survey_deployment(hbm_root, symbols=symbols, params_for=params_for, charger=charger)
    pairs, only_rom, only_hbm = _match_operators(rom["operators"], hbm["operators"])

    # -- the parity band for the pair's actual tensor depths -------------
    parity: dict[str, Any] | None = None
    rom_depths = _values_by_side(
        [r for r in rom["operators"] if r["family"] == "tensor"], "tile_depth"
    )
    hbm_depths = _values_by_side(
        [r for r in hbm["operators"] if r["family"] == "tensor"], "tile_depth"
    )
    rom_depth, hbm_depth = _modal(rom_depths), _modal(hbm_depths)
    if rom_depth and hbm_depth and machine is not None:
        parity = tensor_parity_band(
            rom_depth, hbm_depth, float(tensor_params.work_per_lane_cycle),
            tile_issue_cycles=int(tensor_params.tile_issue_cycles),
        )

    # -- field by field, family by family --------------------------------
    families = sorted(set(rom["families"]) | set(hbm["families"]))
    asymmetries: list[dict[str, Any]] = []
    fields_compared = 0
    topology = int(rom["topology_class"])
    for family in families:
        rom_ops = [r for r in rom["operators"] if r["family"] == family]
        hbm_ops = [r for r in hbm["operators"] if r["family"] == family]
        for field in SCHEDULE_FIELDS:
            rom_vals = _values_by_side(rom_ops, field)
            hbm_vals = _values_by_side(hbm_ops, field)
            fields_compared += 1
            if rom_vals == hbm_vals:
                continue
            rom_m, hbm_m = _modal(rom_vals), _modal(hbm_vals)
            if field == "queue_index":
                # The value that matters is how many queues the family's
                # operators are spread over, not which index is commonest.
                rom_m, hbm_m = len(rom_vals), len(hbm_vals)
            cost_bearing = field not in SCHEDULE_INERT_FIELDS
            if rom_m is not None and hbm_m is not None and cost_bearing:
                effect = _field_effect(
                    family, field, rom_m, hbm_m, pairs, params_for, charger,
                    parity, topology,
                )
            elif not cost_bearing:
                effect = {"favours": "neither", "effect_x": 1.0, "why": (
                    f"{field} is copied into the tile mapping and read by nothing "
                    "that costs a cycle"
                )}
            else:
                effect = {"favours": "unknown", "effect_x": None,
                          "why": "the field is present on one side only"}
            key = f"{family}.{field}"
            ratio_fields = SCHEDULE_TILE_FIELDS + ("max_outstanding",) + SCHEDULE_INERT_FIELDS
            asymmetries.append({
                "family": family, "field": field,
                "rom": rom_vals, "hbm": hbm_vals,
                "rom_value": rom_m, "hbm_value": hbm_m,
                "magnitude_x": (
                    _ratio(rom_m, hbm_m)
                    if field in ratio_fields and rom_m is not None and hbm_m is not None
                    else None
                ),
                "cost_bearing": cost_bearing,
                "enters": (
                    "tile_mapping / tensor_lane_mapping / apply_tile_amplification / _compute_cycles"
                    if field in SCHEDULE_TILE_FIELDS else
                    "queue admission" if field in ("max_outstanding", "queue_index") else
                    "MemorySystem.schedule" if field in ("bank_mask", "port_mask") else
                    "fabric route" if field == "noc_route_class" else "nothing"
                ),
                "favours": effect["favours"],
                "effect_x": effect["effect_x"],
                "why": effect["why"],
                "allowlisted": key in allow,
                "justification": allow.get(key),
            })

    # -- per operator, for equal useful work ------------------------------
    operator_rows: list[dict[str, Any]] = []
    operator_asymmetries: list[dict[str, Any]] = []
    for a, b in pairs:
        row: dict[str, Any] = {
            "family": a["family"], "mnemonic": a["mnemonic"],
            "extent": dict(a["extent"]), "useful_work": a["useful_work"],
            "issues": {"rom": a.get("issues", 1), "hbm": b.get("issues", 1)},
            "rom_operator_id": a["operator_id"], "hbm_operator_id": b["operator_id"],
            "schedule": {
                f: {"rom": (a.get("schedule") or {}).get(f), "hbm": (b.get("schedule") or {}).get(f)}
                for f in SCHEDULE_TILE_FIELDS + ("max_outstanding", "queue_index")
            },
        }
        if "tiles" in a and "tiles" in b:
            for metric in ("tiles", "issued_work", "padding_fraction", "output_waves",
                           "column_groups", "column_group_span", "effective_tensor_width",
                           "payload_bytes_per_tile", "cycles_per_issue",
                           "tile_issue_cycles_per_issue"):
                if metric in a or metric in b:
                    row[metric] = {"rom": a.get(metric), "hbm": b.get(metric)}
            if a["tiles"] != b["tiles"]:
                side = _favours(a["tiles"], b["tiles"])
                operator_asymmetries.append({
                    "family": a["family"], "operator": _operator_label(a),
                    "metric": "tiles_per_issue",
                    "rom": a["tiles"], "hbm": b["tiles"],
                    "magnitude_x": _ratio(a["tiles"], b["tiles"]),
                    "favours": side,
                })
            if a["family"] == "dma" and a.get("payload_bytes_per_tile") != b.get("payload_bytes_per_tile"):
                operator_asymmetries.append({
                    "family": "dma", "operator": _operator_label(a),
                    "metric": "payload_bytes_per_tile",
                    "rom": a.get("payload_bytes_per_tile"), "hbm": b.get("payload_bytes_per_tile"),
                    "magnitude_x": _ratio(a.get("payload_bytes_per_tile", 0), b.get("payload_bytes_per_tile", 0)),
                    "favours": _favours(a.get("payload_bytes_per_tile", 0), b.get("payload_bytes_per_tile", 0), lower_is_better=False),
                    "note": "more bytes per tile is fewer tiles for the same payload",
                })
            if "cycles_per_issue" in a and "cycles_per_issue" in b and a["cycles_per_issue"] != b["cycles_per_issue"]:
                operator_asymmetries.append({
                    "family": a["family"], "operator": _operator_label(a),
                    "metric": "cycles_per_issue",
                    "rom": a["cycles_per_issue"], "hbm": b["cycles_per_issue"],
                    "magnitude_x": _ratio(a["cycles_per_issue"], b["cycles_per_issue"]),
                    "favours": _favours(a["cycles_per_issue"], b["cycles_per_issue"]),
                })
        else:
            row["tile_error"] = {"rom": a.get("tile_error"), "hbm": b.get("tile_error")}
        operator_rows.append(row)

    # -- per family, per step ---------------------------------------------
    family_rows: dict[str, Any] = {}
    for family in families:
        r = rom["families"].get(family, {})
        h = hbm["families"].get(family, {})
        row = {}
        for metric in ("operations", "tiles", "useful_work", "issued_work",
                       "padding_fraction", "output_waves", "column_groups",
                       "cycles", "tile_issue_cycles", "payload_bytes"):
            if metric in r or metric in h:
                rv, hv = r.get(metric, 0), h.get(metric, 0)
                entry: dict[str, Any] = {"rom": rv, "hbm": hv}
                if metric not in ("useful_work", "operations", "payload_bytes"):
                    entry["favours"] = _favours(rv, hv)
                    entry["magnitude_x"] = _ratio(rv, hv)
                row[metric] = entry
        if family == "tensor":
            row["effective_tensor_width_caps"] = {
                "rom": rom["effective_tensor_width_caps"],
                "hbm": hbm["effective_tensor_width_caps"],
            }
        if family == "dma":
            row["payload_bytes_per_tile"] = {
                "rom": round(r.get("payload_bytes", 0) / r["tiles"], 3) if r.get("tiles") else None,
                "hbm": round(h.get("payload_bytes", 0) / h["tiles"], 3) if h.get("tiles") else None,
            }
            if machine is not None:
                dma = params_for("dma")
                row["machine"] = {
                    "bytes_per_cycle": dma.bytes_per_cycle,
                    "tile_issue_cycles": dma.tile_issue_cycles,
                    "rule": (
                        "a DMA operator costs tiles x max(ceil(bytes_transferred / tiles / "
                        "bytes_per_cycle), tile_issue_cycles); at this rate every tile of "
                        "these deployments is at the issue floor, so the DMA charge is the tile count"
                        if all(
                            (rec.get("transferred_bytes_static", 0) / max(rec.get("tiles", 1), 1))
                            <= dma.bytes_per_cycle
                            for rec in rom["operators"] + hbm["operators"]
                            if rec["family"] == "dma" and "tiles" in rec
                        ) else
                        "a DMA operator costs tiles x max(ceil(bytes_transferred / tiles / "
                        "bytes_per_cycle), tile_issue_cycles)"
                    ),
                }
        family_rows[family] = row

    # -- verdict ----------------------------------------------------------
    unexplained = [
        a for a in asymmetries if a["cost_bearing"] and not a["allowlisted"]
    ]
    allowlist_unused = sorted(
        set(allow) - {f"{a['family']}.{a['field']}" for a in asymmetries}
    )
    program_mismatch = bool(only_rom or only_hbm)
    tile_errors = [
        (side, rec["operator_id"], rec["tile_error"])
        for side, survey in (("rom", rom), ("hbm", hbm))
        for rec in survey["operators"] if "tile_error" in rec
    ]
    comparable = not unexplained and not program_mismatch and not tile_errors
    rom_weight_classes = set(rom["storage_class_counts"])
    hbm_weight_classes = set(hbm["storage_class_counts"])
    spans_match = rom["effective_tensor_width_caps"] == hbm["effective_tensor_width_caps"]

    verdict = _render_verdict(
        comparable, pairs, fields_compared, allow, unexplained, program_mismatch,
        only_rom, only_hbm, tile_errors, family_rows, operator_asymmetries,
        rom, hbm, parity, lanes,
    )
    for survey in (rom, hbm):
        for rec in survey["operators"]:
            for k in [k for k in rec if k.startswith("_")]:
                del rec[k]
    return {
        "schema": "opentallas.deployment_audit.v2",
        "rule": (
            "compare, per engine family and per operator, every SCHEDULE field "
            "runtime.cycle.model.tile_mapping reads, the tile counts and padding "
            "those fields produce for the same useful work at the same request, "
            "and for DMA the tile count and bytes per tile; comparable only when "
            "no cost-bearing field differs outside the cited allowlist"
        ),
        "comparable": comparable,
        "verdict": verdict,
        "basis": (
            f"SCHEDULE fields at lanes={lanes}"
            + (", charged with the cycle model's own _compute_cycles" if machine is not None else "")
        ),
        "lanes": lanes,
        "request_symbols": _symbol_names(symbols),
        "rom": rom,
        "hbm": hbm,
        "fields_compared": fields_compared,
        "asymmetries": asymmetries,
        "unexplained_asymmetries": [f"{a['family']}.{a['field']}" for a in unexplained],
        "operator_asymmetries": operator_asymmetries,
        "operators": operator_rows,
        "operators_unmatched": {
            "rom": [_operator_label(r) for r in only_rom],
            "hbm": [_operator_label(r) for r in only_hbm],
        },
        "families": family_rows,
        "tensor_parity_band": parity,
        "allowlist": dict(allow),
        "allowlist_unused": allowlist_unused,
        "column_group_spans_match": spans_match,
        "storage_classes_differ_as_expected": (
            int(StorageClass.ROM) in rom_weight_classes
            and int(StorageClass.ROM) not in hbm_weight_classes
        ),
    }


def _model_slug_of_pair(anchor: "Anchor") -> str:
    return pair_id(anchor).split("__", 1)[0]


def _bind_shipped_deployment(base_capability: str, model_id: str,
                             role: str) -> tuple[Path | None, dict[str, Any]]:
    """The deployment the cell's ``role`` side is bound to, or why there is none."""
    from runtime.abi3.capability import Capability

    entry = SHIPPED_DEPLOYMENTS.get(base_capability)
    record: dict[str, Any] = {
        "role": role, "base_capability": base_capability, "model_id": model_id,
    }
    if entry is None or entry["model_id"] != model_id:
        record["status"] = "no deployment built"
        record["why"] = (
            f"no compiled {model_id} deployment is bound to {base_capability}"
        )
        return None, record
    root = REPO / entry["root"]
    record.update({
        "root": entry["root"], "evidence": list(entry["evidence"]),
        "registered_deployment_sha256": entry["deployment_sha256"],
    })
    manifest_path = root / "deployment.json"
    if not manifest_path.exists():
        record["status"] = "no deployment built"
        record["why"] = f"{entry['root']} is absent from this tree"
        return None, record
    manifest = json.loads(manifest_path.read_text())
    expected_cap = Capability.from_dict(
        json.loads((REPO / base_capability).read_text())
    ).digest
    record["capability_digest"] = manifest.get("capability_digest")
    record["deployment_sha256"] = manifest.get("deployment_sha256")
    if manifest.get("capability_digest") != expected_cap:
        record["status"] = "bound to a different capability"
        record["why"] = (
            f"{entry['root']} carries capability digest "
            f"{str(manifest.get('capability_digest'))[:12]}, not "
            f"{expected_cap[:12]} of {base_capability}"
        )
        return None, record
    if manifest.get("deployment_sha256") != entry["deployment_sha256"]:
        record["status"] = "not the registered deployment"
        record["why"] = (
            f"{entry['root']} is deployment {str(manifest.get('deployment_sha256'))[:12]}, "
            f"not the {entry['deployment_sha256'][:12]} the cited evidence names"
        )
        return None, record
    record["status"] = "bound"
    return root, record


def deployment_audit_for_pair(anchor: "Anchor", d: "Derivation",
                              bodies: Mapping[str, Mapping[str, Any]],
                              tables: Mapping[str, Path]) -> dict[str, Any]:
    """The C2 audit of one cell: its bound deployments, or why it has none.

    Absence is a failure, never a skip: a cell whose deployments were never
    built reports ``comparable = false`` with the reason, so that the gate
    reads a verdict rather than a missing key.
    """
    from runtime.abi3.capability import Capability
    from runtime.cycle.machine import MachineModel, load_cost_table

    model_id = _model_slug_of_pair(anchor)
    rom_base = str(d.facts.get("rom_base_capability"))
    hbm_base = str(d.facts.get("hbm_base_capability"))
    rom_root, rom_bind = _bind_shipped_deployment(rom_base, model_id, "rom")
    hbm_root, hbm_bind = _bind_shipped_deployment(hbm_base, model_id, "hbm")
    symbols = decode_request_symbols(anchor.batch_size, anchor.context_tokens)
    base: dict[str, Any] = {
        "schema": "opentallas.deployment_audit.v2",
        "generator": "tools/derive_cycle_machine.py",
        "pair_id": pair_id(anchor),
        "gate": "C2",
        "deployments": {"rom": rom_bind, "hbm": hbm_bind},
        "request_symbols": _symbol_names(symbols),
    }
    if rom_root is None or hbm_root is None:
        missing = [b for b in (rom_bind, hbm_bind) if b["status"] != "bound"]
        base.update({
            "comparable": False,
            "reason": "no deployment built",
            "verdict": (
                "NOT COMPARABLE: no deployment built -- "
                + "; ".join(f"{b['role']}: {b['why']}" for b in missing)
                + ".  A cell with no compiled deployment pair has no "
                "deployment-side evidence, and absence is a failure, not a skip."
            ),
        })
        return base
    # Both sides of the derived pair share every engine parameter (D1), so
    # the ROM machine is the machine the audit charges with.
    machine = MachineModel(
        Capability.from_dict(bodies["rom_capability"]),
        load_cost_table(tables["rom_cost_table"]),
    )
    report = audit_deployments(
        rom_root, hbm_root, symbols=symbols, machine=machine,
        allowlist=DEPLOYMENT_AUDIT_ALLOWLIST,
    )
    tensor = machine.engine("tensor")
    base.update(report)
    base["machine"] = {
        "capability": _relative(tables["rom_capability"]) if isinstance(
            tables.get("rom_capability"), Path) else str(tables.get("rom_capability")),
        "cost_table": _relative(tables["rom_cost_table"]),
        "tensor_lanes": tensor.lanes,
        "tensor_work_per_lane_cycle": tensor.work_per_lane_cycle,
        "queue_depth": tensor.queue_depth,
        "dma_bytes_per_cycle": machine.engine("dma").bytes_per_cycle,
    }
    base["reason"] = "comparable" if report["comparable"] else "not comparable"
    return base


#: The per-operator survey is the bulk of an audit -- every operator's
#: operands, extents and tile decomposition on both sides.  The pair artifact
#: embeds the audit without it and names the standalone file that has it.
_AUDIT_BULK_KEYS = ("operators",)


def deployment_audit_summary(audit: Mapping[str, Any],
                             full_report: str) -> dict[str, Any]:
    """The audit as embedded in the pair artifact: verdicts, not surveys."""
    out: dict[str, Any] = {}
    for key, value in audit.items():
        if key in _AUDIT_BULK_KEYS:
            continue
        if key in ("rom", "hbm") and isinstance(value, Mapping):
            out[key] = {k: v for k, v in value.items() if k not in _AUDIT_BULK_KEYS}
        else:
            out[key] = value
    out["full_report"] = full_report
    return out


# ---------------------------------------------------------------------------
# D6: the reconciliation contract
# ---------------------------------------------------------------------------
def _store_wall_seconds(run: Mapping[str, Any], klass: str) -> float:
    """Wall time one storage class was busy.

    ``busy_cycles`` is summed over units, so the wall time is the sum divided
    by units x ports.  The cycle model reports no per-term wall clock and no
    binding constraint; both have to be derived here.
    """
    stats = run["memory"].get(klass) or {}
    if not stats.get("busy_cycles"):
        return 0.0
    structure = stats.get("structure", {})
    units = int(structure.get("units", 1)) * int(structure.get("ports_per_unit", 1))
    return stats["busy_cycles"] / max(units, 1) / run["timing"]["clock_frequency_hz"]


def reconcile(anchor: Anchor, rom_run: Mapping[str, Any],
              hbm_run: Mapping[str, Any]) -> dict[str, Any]:
    """Put the analytical five terms and the measured cycle terms side by side.

    Nothing here is tuned.  Where the cycle model has no counterpart for an
    analytical term the entry says so; where it has one and disagrees, the
    disagreement is reported with the term responsible named.
    """
    A = anchor
    out: dict[str, Any] = {
        "schema": "opentallas.derived_cycle_machine.reconciliation.v1",
        "anchor": {
            "rom_design": A.rom_design, "hbm_design": A.hbm_design,
            "model": A.rom["model"], "batch_size": A.batch_size,
            "context_tokens": A.context_tokens,
        },
        "runs": {
            role: {
                "deployment_digest": run["inputs"]["deployment_digest"],
                "capability_digest": run["inputs"]["capability_digest"],
                "capability_technology_view": run["inputs"].get(
                    "capability_technology_view"),
                "cost_table": run["inputs"]["cost_table"]["path"],
                "cost_table_sha256": run["inputs"]["cost_table"]["sha256"],
                "request_symbols": run["inputs"]["request"]["symbols"],
                "provenance_class": run.get("provenance", {}).get("class"),
            }
            for role, run in (("rom", rom_run), ("hbm", hbm_run))
            if "inputs" in run
        },
        "combination_rule": (
            "analytical step = max(memory_time, compute_time) / "
            "efficiencies.stage_balance x token_slots + link_latency + "
            "layer_fixed_latency, where memory_time = weight + kv for a shared "
            "memory path and max(weight, kv) for separate arrays.  The five "
            "component times do NOT sum to the step; the derived machines "
            "collapse each design point to one logical device, so token_slots "
            "and stage_balance are both inert on the cycle side."
        ),
        "targets": {},
    }
    for role, run, point in (("rom", rom_run, A.rom), ("hbm", hbm_run, A.hbm)):
        timing = run["timing"]
        clock = timing["clock_frequency_hz"]
        engines = run["engines"]
        ct = point["component_times_s"]
        rom_wall = _store_wall_seconds(run, "rom")
        hbm_wall = _store_wall_seconds(run, "hbm")
        counters = run["counters"]["architectural"]
        weight_bytes = counters.get("rom.bytes_read") or 0
        if role == "hbm":
            # Weights and KV share one pool; attribute the pool's wall time by
            # the architectural byte split, which is the same rule the
            # analytical point's shared_memory_path uses.
            total = counters.get("hbm.bytes_read", 0) + counters.get(
                "hbm.bytes_written", 0)
            kv_and_other = total - _hbm_weight_bytes(run)
            weight_share = _hbm_weight_bytes(run) / total if total else 0.0
            measured_weight = hbm_wall * weight_share
            measured_kv = hbm_wall * (1.0 - weight_share)
            weight_store_note = (
                f"weights and KV share the HBM pool, so its "
                f"{hbm_wall * 1e6:.3f} us of occupancy is split by the "
                f"architectural byte count: "
                f"{_hbm_weight_bytes(run)} weight bytes of {total} total."
            )
        else:
            measured_weight = rom_wall
            measured_kv = hbm_wall
            weight_store_note = (
                "weights are in ROM and KV in HBM: two physically separate "
                "unit pools, so their occupancies are read off directly and "
                "overlap exactly as the analytical overlap_rule says."
            )
        terms = {
            "compute": {
                "analytical_s": ct["compute"],
                "cycle_s": timing["compute_cycles"] / clock,
                "cycle_tensor_only_s": (
                    engines["tensor"]["compute_bound_cycles"] / clock
                ),
                "note": (
                    "The tensor engine alone is the analytical term's "
                    "counterpart; the analytical operation count has NO "
                    "attention arithmetic and no other engine family.  "
                    "cycle_s is every family, cycle_tensor_only_s is the "
                    "comparable one."
                ),
            },
            "weight_read": {
                "analytical_s": ct["weight_read"],
                "cycle_s": measured_weight,
                "note": weight_store_note,
            },
            "kv_read": {
                "analytical_s": ct["kv_read"],
                "cycle_s": measured_kv,
                "note": (
                    "The deployment moves "
                    f"{counters.get('hbm.bytes_read', 0)} read + "
                    f"{counters.get('hbm.bytes_written', 0)} written bytes "
                    "through HBM, against the analytical "
                    f"kv_transfer_bytes_per_step "
                    f"{point['kv_transfer_bytes_per_step']:.0f}."
                ),
            },
            "link_latency": {
                "analytical_s": ct["link_latency"],
                "cycle_s": timing["link_cycles"] / clock,
                "note": (
                    "STRUCTURALLY ZERO.  build_fabric returns None for "
                    "TopologyClass.SINGLE_CHIP, so no cost-table value can put "
                    "a single-chip run in this regime.  The derived machines "
                    "are the design points collapsed to one logical device, "
                    "which is the transformation that removes the fabric."
                ),
            },
            "layer_fixed_latency": {
                "analytical_s": ct["layer_fixed_latency"],
                "cycle_s": None,
                "note": (
                    "NOT SEPARATELY REPORTED.  engine.<family>."
                    "fixed_latency_cycles is charged per engine instruction "
                    "after the unit is freed, so it reaches the step only "
                    "through WAIT dependencies and the model attributes no "
                    "counter to it.  The machine carries "
                    f"{round(A.array_pass_boundary_s * clock)} cycles per "
                    f"instruction against "
                    f"{counters.get('instructions.retired', 0)} instructions "
                    "retired."
                ),
            },
        }
        for name, term in terms.items():
            a_s, c_s = term["analytical_s"], term["cycle_s"]
            term["ratio_cycle_over_analytical"] = (
                (c_s / a_s) if (c_s is not None and a_s) else None
            )
        measurable = {k: v["cycle_s"] for k, v in terms.items()
                      if v["cycle_s"] is not None}
        # The like-for-like binding test.  The cycle model cannot express
        # link_latency on a single chip and reports no separate fixed-latency
        # term, so the analytical binding constraint has to be recomputed over
        # the terms both models actually have before the two can be compared.
        expressible = {k: v["analytical_s"] for k, v in terms.items()
                       if v["cycle_s"] is not None and k != "link_latency"}
        analytical_expressible_binding = max(expressible, key=expressible.get)
        cycle_binding = max(
            {k: v for k, v in measurable.items() if k != "link_latency"},
            key=lambda k: measurable[k],
        )
        out["targets"][role] = {
            "analytical": {
                "step_time_s": point["step_time_s"],
                "per_user_tokens_s": point["per_user_tokens_s"],
                "binding_constraint": point["binding_constraint"],
                "component_times_s": dict(ct),
            },
            "cycle": {
                "step_time_s": timing["seconds"],
                "per_user_tokens_s": 1.0 / timing["seconds"],
                "total_cycles": timing["total_cycles"],
                "clock_frequency_hz": clock,
                "binding_constraint": cycle_binding,
                "binding_constraint_rule": (
                    "argmax over the measured terms; the cycle model reports "
                    "no binding constraint of its own"
                ),
            },
            "binding_regime": {
                "analytical_over_all_five_terms": point["binding_constraint"],
                "analytical_over_expressible_terms": analytical_expressible_binding,
                "cycle": cycle_binding,
                "same_regime": analytical_expressible_binding == cycle_binding,
                "rule": (
                    "The cycle model builds no fabric on SINGLE_CHIP and "
                    "attributes no counter to fixed latency, so the two "
                    "binding constraints are only comparable over the terms "
                    "both models express: compute, weight_read and kv_read."
                ),
            },
            "terms": terms,
            "step_ratio_cycle_over_analytical": (
                timing["seconds"] / point["step_time_s"]
            ),
        }
    rom_t = out["targets"]["rom"]["cycle"]["per_user_tokens_s"]
    hbm_t = out["targets"]["hbm"]["cycle"]["per_user_tokens_s"]
    published = A.rom["per_user_tokens_s"] / A.hbm["per_user_tokens_s"]
    rom_link = A.rom["component_times_s"]["link_latency"]
    hbm_link = A.hbm["component_times_s"]["link_latency"]
    with_link = (
        (1.0 / (out["targets"]["hbm"]["cycle"]["step_time_s"] + hbm_link))
        and (out["targets"]["hbm"]["cycle"]["step_time_s"] + hbm_link)
        / (out["targets"]["rom"]["cycle"]["step_time_s"] + rom_link)
    )
    out["headline"] = {
        "analytical_ratio": published,
        "cycle_ratio": rom_t / hbm_t,
        "cycle_ratio_with_analytical_link_added_to_both": with_link,
        "analytical_ratio_with_link_removed_from_both": (
            (A.hbm["step_time_s"] - hbm_link) / (A.rom["step_time_s"] - rom_link)
        ),
        "note": (
            f"Four numbers because the link term is expressible in one model "
            f"and not the other, and it is "
            f"{rom_link / A.rom['step_time_s'] * 100:.0f}% of the analytical "
            f"ROM step and {hbm_link / A.hbm['step_time_s'] * 100:.0f}% of the "
            f"analytical GPU step.  Compare cycle_ratio against "
            "analytical_ratio_with_link_removed_from_both -- those two are "
            "the like-for-like pair -- and read the other two as the effect "
            "of the term the cycle model cannot express."
        ),
    }
    return out


def _hbm_weight_bytes(run: Mapping[str, Any]) -> int:
    """Weight bytes the HBM-role deployment reads, from the tensor tiling block."""
    tensor = run.get("tiling", {}).get("by_family", {}).get("tensor", {})
    traffic = tensor.get("memory_traffic", {})
    return int(traffic.get("bytes_touched", 0))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def canonical(body: Mapping[str, Any]) -> str:
    return json.dumps(body, indent=2, sort_keys=True) + "\n"


#: Declared capability fields the two records may legitimately differ on
#: without any of it reaching a machine parameter.  They are REPORTED rather
#: than harmonised, because each bounds what can be LOWERED onto the machine
#: rather than how fast the machine runs -- except max_context_positions, which
#: bounds what the pair can be ASKED and is harmonised in capability().
_REPORTED_LIMIT_FIELDS = (
    "max_expert_ids", "max_instructions", "max_descriptors", "max_events",
    "max_loop_depth", "max_loop_trip", "max_outstanding_per_queue",
)


def declared_asymmetries(rom_cap: Mapping[str, Any],
                         hbm_cap: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Declared differences the resolved-parameter comparison cannot see.

    ``assert_comparable`` compares the parameters ``MachineModel`` resolves and
    nothing else, so two records can pass it while declaring different
    capacities, features and lowering limits.  Those differences do not change
    a cycle, but they change what each side can be asked to run, and leaving
    them unnamed is how a comparison quietly stops being one.
    """
    out: list[dict[str, Any]] = []
    rl, hl = rom_cap.get("limits", {}), hbm_cap.get("limits", {})
    for field in _REPORTED_LIMIT_FIELDS:
        if rl.get(field) != hl.get(field):
            out.append({
                "field": f"limits.{field}",
                "rom": rl.get(field), "hbm": hl.get(field),
                "why": ("carried through from two different base capabilities; "
                        "bounds what can be lowered, not how fast it runs"),
            })
    rf = set(rom_cap.get("features", []) or [])
    hf = set(hbm_cap.get("features", []) or [])
    if rf != hf:
        out.append({
            "field": "features",
            "rom_only": sorted(rf - hf), "hbm_only": sorted(hf - rf),
            "why": ("advertised feature sets of the two base capabilities; no "
                    "feature bit reaches a cost-table parameter"),
        })
    for cls in ("rom", "hbm", "sram"):
        r = (rom_cap.get("memory", {}) or {}).get(cls, {}) or {}
        h = (hbm_cap.get("memory", {}) or {}).get(cls, {}) or {}
        if r.get("bytes") != h.get("bytes"):
            out.append({
                "field": f"memory.{cls}.bytes",
                "rom": r.get("bytes"), "hbm": h.get("bytes"),
                "why": ("capacity, not bandwidth.  The weight STORE differs by "
                        "construction -- that is the comparison -- and no "
                        "capacity resolves to a machine parameter"),
            })
    return out


def build(anchor: Anchor, rom_base: str | None = None,
          hbm_base: str | None = None,
          ) -> tuple[Derivation, dict[str, dict[str, Any]]]:
    rom_base, hbm_base = base_capabilities(anchor, rom_base, hbm_base)
    base_rom = json.loads((REPO / rom_base).read_text())
    base_hbm = json.loads((REPO / hbm_base).read_text())
    rom_banks = int(
        ((base_rom.get("memory") or {}).get("rom") or {}).get("banks", 16) or 16
    )
    d = derive(anchor, rom_arrays=rom_banks)
    d.facts["rom_base_capability"] = rom_base
    d.facts["hbm_base_capability"] = hbm_base
    positions = min(
        int(base_rom["limits"]["max_context_positions"]),
        int(base_hbm["limits"]["max_context_positions"]),
    )
    d.facts["max_context_positions"] = positions
    bodies = {
        "rom_cost_table": cost_table(d, "rom"),
        "hbm_cost_table": cost_table(d, "hbm"),
        "rom_capability": capability(d, "rom", base_rom, rom_base, positions),
        "hbm_capability": capability(d, "hbm", base_hbm, hbm_base, positions),
    }
    d.facts["declared_asymmetries"] = declared_asymmetries(
        bodies["rom_capability"], bodies["hbm_capability"]
    )
    return d, bodies


def emitted_paths(anchor: Anchor, config_dir: Path, artifact_dir: Path,
                  rom_base: str, hbm_base: str) -> dict[str, Path]:
    """Where this cell's four files and its artifact go.

    Keyed on the cell, so a second triple cannot overwrite a first.  The pair
    this tool was published with keeps the paths it was published at.
    """
    pid = pair_id(anchor)
    cap_dir = config_dir / "abi3_capability" / TECHNOLOGY_VIEW
    if pid == LEGACY_PAIR_ID:
        return {
            "rom_cost_table":
                config_dir / f"abi3_cost_{TECHNOLOGY_VIEW}_rom_v1.json",
            "hbm_cost_table":
                config_dir / f"abi3_cost_{TECHNOLOGY_VIEW}_hbm_v1.json",
            "rom_capability": cap_dir / "rom_qwen3_n5_v1.json",
            "hbm_capability": cap_dir / "hbm_sram_single_chip_n5_v1.json",
            "artifact":
                artifact_dir / "qwen3_n5_design_target_machine_pair.json",
            "deployment_audit":
                artifact_dir / "qwen3_n5_design_target_deployment_audit.json",
        }
    cost_dir = config_dir / TECHNOLOGY_VIEW
    return {
        "rom_cost_table":
            cost_dir / f"abi3_cost_{TECHNOLOGY_VIEW}_{pid}_rom_v1.json",
        "hbm_cost_table":
            cost_dir / f"abi3_cost_{TECHNOLOGY_VIEW}_{pid}_hbm_v1.json",
        "rom_capability":
            cap_dir / f"{Path(rom_base).stem}_{TECHNOLOGY_VIEW}_{pid}_v1.json",
        "hbm_capability":
            cap_dir / f"{Path(hbm_base).stem}_{TECHNOLOGY_VIEW}_{pid}_v1.json",
        "artifact": artifact_dir / f"{pid}_machine_pair.json",
        "deployment_audit": artifact_dir / f"{pid}_deployment_audit.json",
    }


def artifact(anchor: Anchor, d: Derivation, comparability: Mapping[str, Any],
             paths: Mapping[str, str],
             deployment_audit: Mapping[str, Any] | None = None) -> dict[str, Any]:
    A = anchor
    rows = []
    rom_p, hbm_p = d.parameters("rom"), d.parameters("hbm")
    for name in sorted(set(rom_p) | set(hbm_p)):
        r, h = rom_p.get(name), hbm_p.get(name)
        rows.append({
            "parameter": name,
            "rom_value": r.value if r else None,
            "hbm_value": h.value if h else None,
            "shared": bool(r and h and r.value == h.value),
            "unit": (r or h).unit,
            "analytical_grade": (r or h).analytical_grade,
            "cost_table_provenance": (r or h).provenance,
            "derivation": (r or h).derivation,
            **({"source": (r or h).source} if (r or h).source else {}),
        })
    return {
        "schema": "opentallas.derived_cycle_machine.v1",
        "generator": "tools/derive_cycle_machine.py",
        "pair_id": pair_id(A),
        "base_capabilities": {
            "rom": d.facts.get("rom_base_capability"),
            "hbm": d.facts.get("hbm_base_capability"),
        },
        "declared_asymmetries": d.facts.get("declared_asymmetries", []),
        "declared_asymmetries_note": (
            "assert_comparable compares the parameters MachineModel resolves "
            "and nothing else.  These declared fields differ between the two "
            "emitted records, reach no cost-table parameter, and are listed so "
            "that a reader can see what the assertion does NOT cover.  "
            "limits.max_context_positions is the one exception: it bounds what "
            "the pair can be asked rather than how fast it runs, so both "
            "records are harmonised to the smaller of the two bases."
        ),
        "anchor": {
            "analytical_artifact": A.analytical_path,
            "study_id": A.study_id,
            "model": A.rom["model"],
            "batch_size": A.batch_size,
            "context_tokens": A.context_tokens,
            "rom_design": A.rom_design,
            "hbm_design": A.hbm_design,
            "rom_topology_kind": A.rom.get("topology_kind"),
            "rom_parallelism": A.rom.get("parallelism"),
            "rom_kv_store": A.rom_kv_store,
            "hbm_kv_store": A.hbm_kv_store,
            "rom_token_slots": A.rom_token_slots,
            "hbm_token_slots": A.hbm_token_slots,
            "rom_execution_format": A.rom.get("execution_format"),
            "hbm_execution_format": A.hbm.get("execution_format"),
            "rom_devices": A.rom["device_count"],
            "hbm_devices": A.hbm["device_count"],
            "rom_area_mm2": A.rom["silicon_area_mm2"],
            "hbm_area_mm2": A.hbm["silicon_area_mm2"],
            "iso_area_ratio": A.rom["silicon_area_mm2"] / A.hbm["silicon_area_mm2"],
            "iso_area": abs(
                A.rom["silicon_area_mm2"] / A.hbm["silicon_area_mm2"] - 1
            ) < 0.02,
            "rom_binding_constraint": A.rom["binding_constraint"],
            "hbm_binding_constraint": A.hbm["binding_constraint"],
            "rom_per_user_tokens_s": A.rom["per_user_tokens_s"],
            "hbm_per_user_tokens_s": A.hbm["per_user_tokens_s"],
            "published_ratio": (
                A.rom["per_user_tokens_s"] / A.hbm["per_user_tokens_s"]
            ),
            "rom_component_times_s": dict(A.rom["component_times_s"]),
            "hbm_component_times_s": dict(A.hbm["component_times_s"]),
            "rom_step_time_s": A.rom["step_time_s"],
            "hbm_step_time_s": A.hbm["step_time_s"],
        },
        "derived_facts": d.facts,
        "parameters": rows,
        "comparability_assertion": comparability,
        "deployment_audit": (
            dict(deployment_audit) if deployment_audit is not None else {
                "comparable": False,
                "reason": "audit not run",
                "verdict": "NOT COMPARABLE: the deployment audit was not run for this cell",
            }
        ),
        "residuals": d.residuals,
        "emitted": dict(paths),
    }


# ---------------------------------------------------------------------------
# The matrix: every cell the study itself publishes
# ---------------------------------------------------------------------------
#: ROM design points the repository already carries an ABI3 capability shape
#: for, added to the study's own selections so the matrix covers the
#: deployments that exist as well as the designs the study recommends.  Each
#: entry states why it is here; the GPU comparator is never chosen here, it is
#: always read from the artifact's own iso-area comparison.
REPOSITORY_CELLS: tuple[tuple[str, str], ...] = (
    (DEFAULT_ROM_DESIGN,
     "the pair this generator was published with: array x4, KV in HBM, one "
     "token slot.  rom_qwen3 (SINGLE_CHIP) against hbm_sram_single_chip"),
    ("Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x1",
     "Qwen's wafer rung with KV in HBM and one token slot"),
    ("DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x32",
     "the one analytical cell that matches a CLUSTER_32 capability: "
     "rom_deepseek_v4_array_32 against hbm_sram_cluster_32, and both "
     "deployments already exist on disk"),
    ("DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1",
     "the rom_deepseek_v4 wafer capability's own shape with KV in HBM"),
    ("DSV4-Pro/ROM-N5-native-HBMKV-array-tensor-x170",
     "Pro's array rung nearest the wafer headline's area, priced at the same "
     "iso-area GPU comparator; the study says array and wafer disagree by "
     "1.6x here, so which one is 'the' Pro cell has to be stated"),
)


def matrix_cells(body: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Every (rom_design, hbm_design) cell this matrix covers, from the artifact.

    Chosen from the study, not from preference: the batch-1 recommendation of
    each model, every entry of each model's published batch-1 frontier, the
    best array and best wafer topology the study names for each model, and the
    ROM design points the repository already has a capability shape for.  The
    GPU side of every cell is the artifact's OWN iso-area comparator for that
    ROM design; nothing here picks a comparator.
    """
    iso: dict[str, str] = {}
    for c in body["comparisons"]:
        if int(c.get("batch_size", -1)) != 1:
            continue
        gpu = c.get("iso_area_gpu_design")
        if gpu:
            iso.setdefault(c["rom_design"], gpu)
    known = {p["design"] for p in body["points"] if int(p["batch_size"]) == 1}

    seen: dict[tuple[str, str], dict[str, Any]] = {}

    def add(design: str, why: str) -> None:
        if not design or design not in known:
            return
        gpu = iso.get(design)
        if not gpu:
            return
        key = (design, gpu)
        if key in seen:
            if why not in seen[key]["why"]:
                seen[key]["why"].append(why)
            return
        seen[key] = {"rom_design": design, "hbm_design": gpu, "why": [why]}

    for model in body["design_selection"]["models"]:
        name = model["model"]
        for regime in model.get("batch_regimes", []):
            if int(regime.get("batch_size", -1)) != 1:
                continue
            rec = regime.get("recommended") or {}
            add(rec.get("design"),
                f"design_selection batch-1 recommendation for {name} -- the "
                f"study's own headline pair")
        for entry in model.get("frontier_batch_1", []) or []:
            add(entry.get("design"),
                f"published batch-1 frontier entry for {name}")
    for row in body.get("topology_choices", []):
        if int(row.get("batch_size", -1)) != 1:
            continue
        name = row["model"]
        add(row.get("array_best_design"),
            f"best ARRAY topology the study names for {name} at batch 1")
        add(row.get("wafer_best_design"),
            f"best WAFER topology the study names for {name} at batch 1")
        add(row.get("best_design"),
            f"best topology overall the study names for {name} at batch 1")
    for design, why in REPOSITORY_CELLS:
        add(design, why)
    return [seen[k] for k in sorted(seen)]


def emit_cell(anchor: Anchor, config_dir: Path, artifact_dir: Path, *,
              rom_base: str | None = None, hbm_base: str | None = None,
              write: bool = True) -> dict[str, Any]:
    """Derive, assert and (optionally) write one cell.  Raises on any failure."""
    rom_base, hbm_base = base_capabilities(anchor, rom_base, hbm_base)
    d, bodies = build(anchor, rom_base, hbm_base)
    paths = emitted_paths(anchor, config_dir, artifact_dir, rom_base, hbm_base)
    rendered = {k: canonical(bodies[k]) for k in bodies}
    drift: list[str] = []
    if write:
        for key, path in paths.items():
            if key in ("artifact", "deployment_audit"):
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered[key])
        tables = paths
    else:
        for key in ("rom_cost_table", "hbm_cost_table",
                    "rom_capability", "hbm_capability"):
            path = paths[key]
            if not path.exists():
                drift.append(f"{_relative(path)} is missing")
            elif path.read_text() != rendered[key]:
                drift.append(
                    f"{_relative(path)} does not match a fresh derivation"
                )
        tables = paths
    with tempfile.TemporaryDirectory() as tmp:
        if not write:
            # The assertion re-resolves both machines through MachineModel,
            # which reads the cost tables from disk.  A dry run must not depend
            # on the emitted files already being there, so render them into a
            # scratch directory instead.
            scratch = Path(tmp)
            tables = dict(paths)
            for key in ("rom_cost_table", "hbm_cost_table"):
                tables[key] = scratch / paths[key].name
                tables[key].write_text(rendered[key])
        # D1 runs on EVERY emit, against the files just written.
        comparability = assert_comparable(
            bodies["rom_capability"], tables["rom_cost_table"],
            bodies["hbm_capability"], tables["hbm_cost_table"],
            allowlist=allowlist_for(anchor),
        )
        # C2 runs on every emit too: the deployment-side half of D1, against
        # the compiled deployments the cell's base capabilities bind to, or a
        # recorded failure when there are none.
        deployment_audit = deployment_audit_for_pair(anchor, d, bodies, tables)
    art = artifact(anchor, d, comparability, {
        k: _relative(v) for k, v in paths.items()
        if k not in ("artifact", "deployment_audit")
    }, deployment_audit_summary(deployment_audit, _relative(paths["deployment_audit"])))
    if write:
        paths["artifact"].parent.mkdir(parents=True, exist_ok=True)
        paths["artifact"].write_text(canonical(art))
        paths["deployment_audit"].write_text(canonical(deployment_audit))
    return {
        "derivation": d, "bodies": bodies, "paths": paths, "drift": drift,
        "rendered": rendered, "comparability": comparability, "artifact": art,
        "deployment_audit": deployment_audit,
    }


# ---------------------------------------------------------------------------
# L3 calibration: the cycle model against the L1 block-cycle records (gate G4)
# ---------------------------------------------------------------------------
#
# Gate G4 (configs/gates/redesign_gates.json) reads ONE artifact,
# results/derived/*calibration*.json, for two fields:
#
#     calibration.block_cycles_within_band          -- the RTL half
#     calibration.derived_machine_reproduces_anchor -- the analytical half
#
# ``--calibrate`` produces that artifact.  It does NOT re-fit anything: it
# takes the cycle model's own per-block cost formula (runtime/cycle/model.py,
# ``CycleModel._compute_cycles`` and ``_time_steps``), parameterises it with
# exactly the operation each L1 record ran -- same output surface, same
# reduction depth, same lane count, and the record's own measured rate as
# ``work_per_lane_cycle`` -- and divides what the model charges by what the
# RTL took.  Every ratio is written out; the verdict is a conjunction over
# them and over the boundary rule of docs/CHIP_ARCHITECTURE_DESIGN.md
# section 11.5, which is quoted into the artifact together with the decision
# taken on it.  Nothing here widens the band, and a number that no
# computation produced is written as ``null`` with the reason beside it.

CALIBRATION_SCHEMA = "opentallas.derived_cycle_machine.calibration.v1"

#: docs/CHIP_ARCHITECTURE_DESIGN.md section 11.5, row "L3 / G4, C3, C4":
#: "block cycles within +/-10 % of L1".
CALIBRATION_BAND = (0.9, 1.1)

DEFAULT_LANE_RECORD = "results/rtl/abi3_pipelined_lane.json"
DEFAULT_LANE_GROUPS_RECORD = "results/rtl/abi3_pipelined_lane_groups.json"
DEFAULT_LQ8_RECORD = "results/rtl/abi3_lq8.json"
DEFAULT_CONTROL_PLANE_RECORD = "results/rtl/abi3_deployment_campaign.json"
DEFAULT_RECONCILIATION = "results/derived/qwen3_n5_design_target_reconciliation.json"
DEFAULT_CALIBRATION_OUT = "results/derived/qwen3_n5_design_target_calibration.json"
DESIGN_DOC = "docs/CHIP_ARCHITECTURE_DESIGN.md"
GATES_CONFIG = "configs/gates/redesign_gates.json"
CYCLE_MODEL_SOURCES = ("runtime/cycle/model.py", "runtime/cycle/machine.py")

#: Work-counter units the tensor engine records per product coordinate: one
#: multiply and one add (``FAMILY_WORK_COUNTERS["tensor"]``).  The cycle
#: model's rate is stated in these units and ``CycleModel._work_scale`` reads
#: the same factor off a real step's counters, so the calibration step carries
#: exactly the counters a contraction of that size would.
TENSOR_WORK_UNITS_PER_PRODUCT = 2

#: The blocks whose measured cycles G4 is about.  Each must contribute at
#: least one ratio; a block that carries no cycle count is reported as such
#: and fails the verdict on absence rather than dropping out of it.
CALIBRATED_BLOCKS = ("lane", "lane_groups", "lq8", "control_plane")


def _sha256_of(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_state(inputs: Sequence[str]) -> dict[str, Any]:
    import subprocess

    def run(*argv: str) -> str:
        return subprocess.run(
            ["git", *argv], cwd=REPO, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, check=False,
        ).stdout.strip()

    status = run("status", "--porcelain")
    dirty_paths = sorted(line[3:] for line in status.splitlines()) if status else []
    return {
        "commit": run("rev-parse", "HEAD"),
        "dirty": bool(status),
        "dirty_paths": dirty_paths,
        "dirty_inputs": sorted(p for p in inputs if p in set(dirty_paths)),
    }


def _doc_row(text: str, first_cell: str) -> list[str]:
    """The cells of the one markdown table row whose first cell is ``first_cell``."""
    prefix = f"| {first_cell} |"
    rows = [line for line in text.splitlines() if line.startswith(prefix)]
    if len(rows) != 1:
        raise DerivationError(
            f"{DESIGN_DOC}: expected exactly one table row starting {prefix!r}, "
            f"found {len(rows)}"
        )
    return [c.strip() for c in rows[0].strip().strip("|").split("|")]


def design_boundary_rule(doc_text: str) -> dict[str, Any]:
    """Read the design's boundary figure and the L3/G4 rung rule off the doc.

    Both numbers are the design document's, not this tool's: section 2.1 row
    33 states the per-boundary exposed latency and its band, and section 11.5
    states what the L3 / G4 rung must reach.  They are parsed rather than
    typed here so the artifact cannot drift from the document it cites.
    """
    import re

    row33 = _doc_row(doc_text, "33")
    m = re.search(r"\*\*(\d+) cycles\*\* \(band (\d+)[–-](\d+)\)", row33[2])
    if not m:
        raise DerivationError(
            f"{DESIGN_DOC} section 2.1 row 33 no longer states '**N cycles** "
            f"(band lo-hi)': {row33[2][:120]!r}"
        )
    cycles, lo, hi = (int(m.group(i)) for i in (1, 2, 3))
    decomposition = row33[2].split(":", 1)[1].split(";")[0].strip() if ":" in row33[2] else ""
    l3 = _doc_row(doc_text, "L3 / G4, C3, C4")
    return {
        "design_cycles_per_boundary": cycles,
        "design_band": [lo, hi],
        "design_decomposition": decomposition,
        "design_source": f"{DESIGN_DOC} section 2.1 row 33: {row33[1]}",
        "rung_rule": l3[3],
        "rung_rule_source": f"{DESIGN_DOC} section 11.5 row '{l3[0]}' column 'number it must reach'",
    }


def _calibration_step(rows: int, cols: int, depth: int) -> Any:
    """One tensor contraction step of the RTL case's shape, with its counters."""
    from runtime.cycle.model import TraceStep

    products = rows * cols * depth
    return TraceStep(
        index=0,
        kind="ENGINE",
        node=0,
        family="tensor",
        mnemonic="TENSOR.MATMUL",
        schedule_id=1,
        schedule={
            "tile_rows": rows, "tile_cols": cols, "tile_depth": depth,
            "issue_window": 1,
        },
        operand_dims={
            "out0": (rows, cols), "in0": (rows, depth), "in1": (depth, cols),
        },
        counter_delta={
            "tensor.multiplications": products,
            "tensor.additions": products,
        },
    )


def model_block_charge(
    *, rows: int, cols: int, depth: int, lanes: int,
    products_per_lane_cycle: float, engine: Any, sequencer: Any, memory: Any,
) -> dict[str, Any]:
    """What the cycle model charges for one contraction of this exact shape.

    ``engine`` is the derived machine's tensor ``EngineParams``; its lane
    count and rate are replaced by the RTL block's, everything else (tile
    issue floor, minimum cycles, fixed latency) is the machine's own.  The
    compute charge comes from ``CycleModel._compute_cycles`` and the
    whole-instruction span from ``CycleModel._time_steps``, i.e. from the
    model's code and not from a mirror of it.
    """
    import dataclasses
    from collections import defaultdict

    from runtime.cycle.model import (
        CycleModel, MemorySystem, _EngineUnit, _Queue, tile_mapping,
    )

    rate_units = products_per_lane_cycle * TENSOR_WORK_UNITS_PER_PRODUCT
    params = dataclasses.replace(engine, lanes=lanes, work_per_lane_cycle=rate_units)
    model = CycleModel.__new__(CycleModel)
    model.sequencer = sequencer

    step = _calibration_step(rows, cols, depth)
    mapping = tile_mapping(step, params)
    scale = model._work_scale(step, "tensor", mapping)
    compute, tile_issue = model._compute_cycles(step, params, mapping)
    assert mapping.tensor_lanes is not None
    waves = mapping.tensor_lanes.output_waves
    depth_cycles = compute // waves if waves and compute % waves == 0 else None

    def span(steps: Sequence[Any]) -> tuple[int, dict[str, int]]:
        unit = _EngineUnit("tensor", params)
        queue = _Queue("tensor", params.queue_depth, params.max_outstanding)
        totals: dict[str, int] = defaultdict(int)
        _seq_free, end = model._time_steps(
            list(steps), 0,
            queues={"tensor": queue, "tensor.0": queue},
            engines={"tensor": unit},
            memory=MemorySystem(memory),
            events={}, totals=totals, counters=None, fabric=None,
            fabric_timings=[], tiles_seen={}, node_id=0, node_count=1,
        )
        return int(end), dict(totals)

    whole, totals = span([step])
    front_end = sequencer.fetch_cycles + sequencer.decode_cycles + sequencer.queue_transit_cycles
    if whole != front_end + compute + params.fixed_latency_cycles:
        raise DerivationError(
            "CycleModel._time_steps no longer charges one engine instruction as "
            "fetch + decode + queue transit + compute + fixed latency "
            f"({whole} != {front_end} + {compute} + {params.fixed_latency_cycles}); "
            "the calibration's whole-run decomposition must be re-derived"
        )
    return {
        "lanes": lanes,
        "work_per_lane_cycle_units": rate_units,
        "work_units_per_product": scale,
        "output_waves": waves,
        "tiles": mapping.tiles,
        "depth_cycles_per_wave": depth_cycles,
        "compute_cycles": int(compute),
        "tile_issue_cycles": int(tile_issue),
        "front_end_cycles": int(front_end),
        "fixed_latency_cycles": int(params.fixed_latency_cycles),
        "whole_run_cycles": whole,
        "totals": {k: int(v) for k, v in sorted(totals.items())},
    }


def _ratio_row(**kw: Any) -> dict[str, Any]:
    rtl = kw["rtl_cycles"]
    model = kw["model_cycles"]
    ratio = (model / rtl) if (rtl and model is not None) else None
    lo, hi = CALIBRATION_BAND
    kw["ratio_model_over_rtl"] = ratio
    kw["within_band"] = None if ratio is None else (lo <= ratio <= hi)
    return kw


def calibrate_rate_record(
    record: Mapping[str, Any], *, block: str, engine: Any, sequencer: Any,
    memory: Any,
) -> list[dict[str, Any]]:
    """Every ratio one lane/LQ8 campaign record supports.

    The record's ``measured.mac_per_lane_cycle`` -- the block's headline D2
    figure, the minimum over its rate cases -- is the rate handed to the
    model, times ``g`` products per lane-op for a group-mode case, times the
    work units per product.  Each rate case's own cycle counts are then
    compared with the model's charge for that case, so a block rate that did
    not generalise across its cases would show here as a ratio off 1.
    """
    measured = record["measured"]
    rate_lane_ops = float(measured["mac_per_lane_cycle"])
    cases_by_depth: dict[str, dict[int, Mapping[str, Any]]] = {}
    for depth_entry in record["depths"]:
        key = f"L{int(depth_entry['adder_stages'])}"
        cases_by_depth[key] = {
            int(c["id"]): c for c in depth_entry["vectors"]["cases"] if c.get("rate")
        }
    rows_out: list[dict[str, Any]] = []
    for depth_key in sorted(measured["rates_by_depth"]):
        for entry in measured["rates_by_depth"][depth_key]:
            case = cases_by_depth[depth_key][int(entry["case"])]
            g = int(case["group"])
            lanes = int(entry.get("lanes") or measured.get("lanes") or 1)
            rows, cols, depth = int(case["rows"]), int(case["cols"]), int(case["depth"])
            if int(entry["products"]) != rows * cols * depth:
                raise DerivationError(
                    f"{block} {depth_key} case {entry['case']}: products "
                    f"{entry['products']} != rows x cols x depth {rows * cols * depth}"
                )
            charge = model_block_charge(
                rows=rows, cols=cols, depth=depth, lanes=lanes,
                products_per_lane_cycle=rate_lane_ops * g,
                engine=engine, sequencer=sequencer, memory=memory,
            )
            window = int(entry["window_cycles"])
            total = int(entry["total_cycles"])
            waves = charge["output_waves"]
            common = {
                "block": block,
                "depth": depth_key,
                "adder_stages": int(depth_key[1:]),
                "case": int(entry["case"]),
                "name": entry["name"],
                "simulator": entry["simulator"],
                "shape": {"rows": rows, "cols": cols, "depth": depth, "group": g,
                          "lanes": lanes},
                "rtl_lane_ops": int(entry["lane_ops"]),
                "rtl_products": int(entry["products"]),
                "rtl_first_retire_cycle": int(entry["first_retire_cycle"]),
                "rtl_last_retire_cycle": int(entry["last_retire_cycle"]),
                "rate_handed_to_model": {
                    "lane_ops_per_lane_cycle": rate_lane_ops,
                    "products_per_lane_cycle": rate_lane_ops * g,
                    "work_units_per_lane_cycle": charge["work_per_lane_cycle_units"],
                },
                "rtl_products_per_lane_window_cycle": (
                    int(entry["products"]) / (window * lanes) if window else None
                ),
                "model": {k: v for k, v in charge.items() if k != "totals"},
            }
            rows_out.append(_ratio_row(
                quantity="steady_state",
                definition=(
                    "model compute cycles (output_waves x depth cycles per wave, "
                    "CycleModel._compute_cycles) over the RTL's cycles from the "
                    "first to the last retirement inclusive (window_cycles)"
                ),
                rtl_cycles=window, model_cycles=charge["compute_cycles"], **common,
            ))
            rows_out.append(_ratio_row(
                quantity="per_pass",
                definition=(
                    "model depth cycles per output wave over the RTL's window "
                    "cycles per pass, one pass being one output accumulator's "
                    "walk over the reduction depth on one lane; passes per lane "
                    "= output waves"
                ),
                rtl_cycles=window / waves if waves else None,
                model_cycles=charge["depth_cycles_per_wave"],
                passes_per_lane=waves, **common,
            ))
            rows_out.append(_ratio_row(
                quantity="whole_run",
                definition=(
                    "model span of one engine instruction from fetch to "
                    "completion (fetch + decode + queue transit + compute + "
                    "fixed latency, CycleModel._time_steps) over the RTL's "
                    "total_cycles from start to done, fill and drain included"
                ),
                rtl_cycles=total, model_cycles=charge["whole_run_cycles"], **common,
            ))
    return rows_out


def calibrate_control_plane(record: Mapping[str, Any], sequencer: Any) -> dict[str, Any]:
    """The L1-CP record against the model's sequencer cost -- if it can be.

    The whole-transaction co-simulation records what the microsequencer
    fetched, retired and issued per case and compares every issue and view
    with the golden device, but neither the campaign tool nor its harness
    counts clock cycles, so there is no per-transaction cycle count to divide
    the model's sequencer charge by.  The model's front-end charge for the
    recorded fetch count is written as the lower bound it is; the ratio is
    ``null`` and the block is reported as unmeasured.
    """
    per_instruction = (
        sequencer.fetch_cycles + sequencer.decode_cycles + sequencer.issue_cycles
    )
    cases: list[dict[str, Any]] = []
    cycle_fields = sorted(
        k for sim in record.get("cases", []) for c in sim.get("observed_cases", [])
        for k in c if "cycle" in k.lower()
    )
    for sim in record.get("cases", []):
        for c in sim.get("observed_cases", []):
            fetched = int(c["rtl_fetched"])
            cases.append(_ratio_row(
                block="control_plane",
                quantity="transaction",
                simulator=sim["name"],
                case=int(c["index"]),
                tag=c["tag"],
                deployment_index=int(c["deployment_index"]),
                phase=int(c["phase"]),
                rtl_fetched=fetched,
                rtl_retired=int(c["rtl_retired"]),
                rtl_engine_issues=int(c["issues_compared"]),
                rtl_predicates=int(c["predicates_compared"]),
                verdict=c["verdict"],
                rtl_cycles=None,
                model_cycles=None,
                model_front_end_cycles_lower_bound=fetched * per_instruction,
                model_front_end_rule=(
                    f"rtl_fetched x (sequencer.fetch_cycles {sequencer.fetch_cycles} "
                    f"+ decode_cycles {sequencer.decode_cycles} + issue_cycles "
                    f"{sequencer.issue_cycles}); waits, branch and loop cycles, "
                    "queue and credit stalls are NOT included because the record "
                    "carries no per-instruction trace to charge them from"
                ),
            ))
    return {
        "record_schema": record.get("schema"),
        "campaign": record.get("campaign"),
        "measured": False,
        "status": "unmeasured",
        "why": (
            "results/rtl/abi3_deployment_campaign.json records rtl_fetched, "
            "rtl_retired, issues_compared, views_compared and predicates_compared "
            "per case and no clock-cycle count of any kind (cycle-named fields "
            f"present: {cycle_fields or 'none'}); rtl/test/tb_a3_deployment.sv and "
            "rtl/test/a3_deployment_harness.cpp count checks, not cycles.  The "
            "model's sequencer cost per transaction (issue_cycles x issued "
            "instructions + waits) therefore has nothing measured to be divided "
            "by, and the control plane contributes no ratio.  Measuring it needs "
            "the campaign to print the cycle count from the transaction's first "
            "fetch to its completion, per case, on both simulators."
        ),
        "sequencer_parameters": sequencer.to_dict(),
        "cases": cases,
    }


def calibrate_boundary(
    anchor: Anchor, *, engine: Any, sequencer: Any, memory: Any,
    clock_hz: float, doc_text: str, fill_observations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """The model's per-boundary charge against the design's 120 cycles.

    Unmeasured: no routed or simulated boundary structure -- tile sequencer,
    K-block tree, mesh return / broadcast, completion tree -- exists in
    results/rtl or results/physical_abi3, and the lane records' own
    ``claim_boundary`` excludes integration and the K-block tree.  What CAN be
    computed is what the model charges between two serially dependent engine
    instructions, from ``_time_steps`` on a two-step dependent chain.
    """
    from collections import defaultdict

    from runtime.cycle.model import (
        CycleModel, MemorySystem, _EngineUnit, _Queue,
    )

    rule = design_boundary_rule(doc_text)
    design = rule["design_cycles_per_boundary"]
    lo, hi = rule["design_band"]

    # Two dependent engine instructions: B waits on the event A signals.
    a = _calibration_step(1, 1, 1)
    a.signal_event_id = 7
    b = _calibration_step(1, 1, 1)
    b.index = 1
    b.wait_set_id = 1
    b.wait_producers = (7,)
    model = CycleModel.__new__(CycleModel)
    model.sequencer = sequencer

    def end_of(steps: Sequence[Any]) -> int:
        unit = _EngineUnit("tensor", engine)
        queue = _Queue("tensor", engine.queue_depth, engine.max_outstanding)
        _seq_free, end = model._time_steps(
            list(steps), 0,
            queues={"tensor": queue, "tensor.0": queue}, engines={"tensor": unit},
            memory=MemorySystem(memory), events={}, totals=defaultdict(int),
            counters=None, fabric=None, fabric_timings=[], tiles_seen={},
            node_id=0, node_count=1,
        )
        return int(end)

    one = end_of([a])
    two = end_of([a, b])
    compute_b = max(1, engine.minimum_cycles)  # a 1x1x1 contraction: the floor
    chain = two - one - compute_b
    decomposition = {
        "engine.tensor.fixed_latency_cycles": int(engine.fixed_latency_cycles),
        "sequencer.wait_check_cycles": int(sequencer.wait_check_cycles),
        "queue.transit_cycles": int(sequencer.queue_transit_cycles),
    }
    if chain != sum(decomposition.values()):
        raise DerivationError(
            f"the model's dependent chain {chain} cycles is not fixed latency + "
            f"wait check + queue transit {decomposition}; re-derive the boundary "
            "decomposition"
        )
    analytical_cycles = anchor.array_pass_boundary_s * clock_hz
    pfd = anchor.technology["latency"]["pipeline_fill_drain_s"]
    rederived = str(pfd.get("grade")) in {"derived", "executed", "measured"}
    model_ratio = chain / design
    fixed_ratio = engine.fixed_latency_cycles / design
    within = lo <= chain <= hi
    return {
        **rule,
        "measured": False,
        "rtl_measured_boundary_cycles": None,
        "why_unmeasured": (
            "no routed or simulated boundary structure exists: results/rtl and "
            "results/physical_abi3 hold the lane, the LQ8 block, the "
            "microsequencer front end and the engines, and no tile sequencer, "
            "K-block pairwise tree, mesh return / operand broadcast or completion "
            "tree.  The lane records' claim_boundary.does_not_establish names "
            "'integration' and 'k_block_tree' explicitly.  The 120-cycle figure "
            "is a design statement (grade A in section 2.1), not a measurement."
        ),
        "model_exposed_chain_cycles": chain,
        "model_exposed_chain_rule": (
            "CycleModel._time_steps on two serially dependent engine instructions: "
            "the consumer starts at the producer's unit finish + "
            "engine.tensor.fixed_latency_cycles + sequencer.wait_check_cycles + "
            "queue.transit_cycles (model.py: finish = unit_finish + fixed_latency; "
            "ready = max(arrival, event) + wait_check; start = admitted + transit)"
        ),
        "model_exposed_chain_decomposition": decomposition,
        "model_fixed_latency_cycles": int(engine.fixed_latency_cycles),
        "analytical_per_boundary_s": anchor.array_pass_boundary_s,
        "analytical_per_boundary_cycles_at_clock": analytical_cycles,
        "analytical_per_boundary_rule": (
            "technology.json#latency.pipeline_fill_drain_s + sqrt(reticle.area_mm2) "
            "x latency.global_wire_delay_s_per_mm, times clock.frequency_hz; this "
            "is what engine.<family>.fixed_latency_cycles is derived from"
        ),
        "ratio_model_chain_over_design": model_ratio,
        "ratio_model_fixed_latency_over_design": fixed_ratio,
        "model_chain_within_design_band": within,
        "technology_latency_rederived": rederived,
        "technology_latency_grade": {
            "pipeline_fill_drain_s": {
                "grade": pfd.get("grade"), "source": pfd.get("source"),
                "value": pfd.get("value"),
            },
        },
        "lane_fill_observations": list(fill_observations),
        "lane_fill_note": (
            "first_retire_cycle is the isolated lane's (or LQ8 block's) cycles "
            "from the start pulse to its first retirement, driven directly by "
            "the checker with no tile sequencer, staging SRAM or H-tree; it is "
            "one component of the design's decomposition ('fill 36'), not a "
            "boundary measurement, and it is not a block-cycle ratio.  The "
            "model has no per-output retire time to compare it with; its "
            "counterpart is the per-instruction fixed latency above."
        ),
        "rung_item_met": False,
        "rung_item_decision": (
            "Section 11.5's rule for the L3 / G4 rung is quoted in rung_rule.  It "
            "lists the boundary beside the block cycles, under the same +/-10 %, "
            "as a number the rung must reach, and section 3.6 states 'Gate G4 "
            "compares the RTL-measured boundary against this 120-cycle figure; "
            "technology.json#latency must be re-derived from these structures or "
            "the design's boundary shortened before G4 can pass at +/-10 %'.  The "
            "rule therefore makes the boundary part of G4's band and it is FOLDED "
            "into calibration.block_cycles_within_band.  It is unmet on every "
            "reading: no RTL-measured boundary exists (absence is FAIL); the "
            f"model's exposed chain is {chain} cycles against the design's {design} "
            f"(ratio {model_ratio:.4f}, outside [{CALIBRATION_BAND[0]}, "
            f"{CALIBRATION_BAND[1]}] and outside the design band [{lo}, {hi}]); "
            "and technology.json#latency.pipeline_fill_drain_s is still graded "
            f"'{pfd.get('grade')}', not re-derived from any RTL structure."
        ),
    }


def calibrate_derived_machine(
    anchor: Anchor, *, rom_table: Mapping[str, Any], hbm_table: Mapping[str, Any],
    reconciliation: Mapping[str, Any],
) -> dict[str, Any]:
    """The emitted machine's compute roof against the analytical artifact.

    The roof is recomputed from the emitted cost tables on disk -- lanes x
    work_per_lane_cycle x clock -- and compared with the anchor read from
    ``results/roofline/n5_vs_b200/analytical.json`` itself (operations over
    the published compute time), not with the copy the pair artifact carries.
    """
    def roof(table: Mapping[str, Any]) -> tuple[float, dict[str, float]]:
        p = table["parameters"]
        lanes = float(p["engine.tensor.lanes.default"]["value"])
        wplc = float(p["engine.tensor.work_per_lane_cycle"]["value"])
        clock = float(p["clock.frequency_hz"]["value"])
        return lanes * wplc * clock, {"lanes": lanes, "work_per_lane_cycle": wplc,
                                      "clock_hz": clock}

    target = anchor.compute_roof_ops_s
    rom_roof, rom_p = roof(rom_table)
    hbm_roof, hbm_p = roof(hbm_table)
    rom_err = abs(rom_roof - target) / target
    hbm_err = abs(hbm_roof - target) / target
    published = float(anchor.rom["component_times_s"]["compute"])
    compute_time = anchor.operations / rom_roof
    time_err = abs(compute_time - published) / published
    tolerance = 1e-9
    regimes = {
        role: reconciliation["targets"][role]["binding_regime"]
        for role in ("rom", "hbm")
    }
    same = all(bool(r.get("same_regime")) for r in regimes.values())
    ok = rom_err < tolerance and hbm_err < tolerance and time_err < tolerance
    return {
        "reproduces_anchor": ok,
        "tolerance_relative": tolerance,
        "anchor": {
            "analytical_artifact": anchor.analytical_path,
            "rom_design": anchor.rom_design,
            "operations": anchor.operations,
            "component_times_s_compute": published,
            "compute_roof_ops_s": target,
            "rule": "operations_by_canonical_format summed over formats / component_times_s.compute",
        },
        "rom_machine": {**rom_p, "compute_roof_ops_s": rom_roof, "relative_error": rom_err},
        "hbm_machine": {**hbm_p, "compute_roof_ops_s": hbm_roof, "relative_error": hbm_err},
        "compute_time_s_from_machine": compute_time,
        "compute_time_relative_error": time_err,
        "binding_regime": {
            **regimes,
            "same_regime_both_targets": same,
            "source": DEFAULT_RECONCILIATION,
            "note": "recorded from the reconciliation artifact (gate C3); not part of this field's verdict",
        },
    }


def calibrate(
    anchor: Anchor,
    *,
    lane: Mapping[str, Any],
    lane_groups: Mapping[str, Any],
    lq8: Mapping[str, Any],
    control_plane: Mapping[str, Any],
    reconciliation: Mapping[str, Any],
    rom_table: Mapping[str, Any],
    hbm_table: Mapping[str, Any],
    rom_capability: Mapping[str, Any],
    doc_text: str,
    routed_records: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """The ``calibration`` body: every ratio, both verdict fields, the rules."""
    from runtime.abi3.capability import Capability
    from runtime.cycle.machine import CostTable, MachineModel

    machine = MachineModel(
        Capability.from_dict(rom_capability), CostTable.from_dict(rom_table)
    )
    sequencer = machine.sequencer()
    engine = machine.engine("tensor")
    memory = machine.memory()
    clock_hz = machine.clock_hz

    ratios: list[dict[str, Any]] = []
    for block, record in (("lane", lane), ("lane_groups", lane_groups), ("lq8", lq8)):
        ratios.extend(calibrate_rate_record(
            record, block=block, engine=engine, sequencer=sequencer, memory=memory,
        ))
    cp = calibrate_control_plane(control_plane, sequencer)

    lo, hi = CALIBRATION_BAND
    per_depth: dict[str, Any] = {}
    per_block: dict[str, Any] = {}
    for r in ratios:
        for key, table in ((r["depth"], per_depth), (r["block"], per_block)):
            slot = table.setdefault(key, {"ratios": 0, "min": None, "max": None,
                                          "all_within_band": True})
            slot["ratios"] += 1
            v = r["ratio_model_over_rtl"]
            slot["min"] = v if slot["min"] is None else min(slot["min"], v)
            slot["max"] = v if slot["max"] is None else max(slot["max"], v)
            slot["all_within_band"] = slot["all_within_band"] and r["within_band"]
    per_block["control_plane"] = {
        "ratios": 0, "min": None, "max": None, "all_within_band": False,
        "status": cp["status"],
    }
    block_ratios_within = bool(ratios) and all(r["within_band"] for r in ratios)
    missing = [b for b in CALIBRATED_BLOCKS if per_block.get(b, {}).get("ratios", 0) == 0]

    fills = [
        {
            "block": r["block"], "depth": r["depth"], "case": r["case"],
            "simulator": r["simulator"], "lanes": r["shape"]["lanes"],
            "first_retire_cycle": r["rtl_first_retire_cycle"],
        }
        for r in ratios if r["quantity"] == "steady_state"
    ]
    boundary = calibrate_boundary(
        anchor, engine=engine, sequencer=sequencer, memory=memory,
        clock_hz=clock_hz, doc_text=doc_text, fill_observations=fills,
    )
    derived = calibrate_derived_machine(
        anchor, rom_table=rom_table, hbm_table=hbm_table,
        reconciliation=reconciliation,
    )

    block_cycles_within_band = (
        block_ratios_within and not missing and boundary["rung_item_met"]
    )
    reasons: list[str] = []
    outside = [r for r in ratios if not r["within_band"]]
    if outside:
        reasons.append(
            f"{len(outside)} of {len(ratios)} block-cycle ratios outside [{lo}, {hi}]: "
            + "; ".join(
                f"{r['block']} {r['depth']} case {r['case']} {r['quantity']} "
                f"{r['ratio_model_over_rtl']:.4f}" for r in outside[:4]
            )
        )
    if missing:
        reasons.append(
            "no measured cycles for: " + ", ".join(missing)
            + " (see control_plane.why)"
        )
    if not boundary["rung_item_met"]:
        reasons.append(
            "section 11.5 boundary item unmet: unmeasured, model chain "
            f"{boundary['model_exposed_chain_cycles']} vs design "
            f"{boundary['design_cycles_per_boundary']} (ratio "
            f"{boundary['ratio_model_chain_over_design']:.4f}), "
            "technology.json#latency not re-derived"
        )
    reason = (
        "; ".join(reasons) if reasons
        else f"every ratio inside [{lo}, {hi}], every block measured, boundary item met"
    )

    routed = {}
    for name, rec in (routed_records or {}).items():
        design_block = rec.get("design", {}) if isinstance(rec.get("design"), Mapping) else {}
        pnr = rec.get("place_and_route", {}) if isinstance(rec.get("place_and_route"), Mapping) else {}
        routed[name] = {
            "clock_period_ns": design_block.get("clock_period_ns") or pnr.get("clock_period_ns"),
            "fmax_hz": design_block.get("fmax_hz") or (pnr.get("metrics") or {}).get("fmax_hz"),
        }

    return {
        "block_cycles_within_band": block_cycles_within_band,
        "derived_machine_reproduces_anchor": derived["reproduces_anchor"],
        "verdict_rule": (
            "block_cycles_within_band = (every block-cycle ratio inside the band) "
            "AND (every block in calibrated_blocks contributed a measured ratio) "
            "AND (the boundary item of section 11.5's L3 / G4 rule is met).  "
            "derived_machine_reproduces_anchor = the emitted machines' compute "
            "roof and compute time reproduce the analytical artifact within "
            "1e-9 relative.  Absence of a measurement is FAIL, never "
            "not_evaluable (configs/gates/redesign_gates.json#principle)."
        ),
        "reason": reason,
        "band": {"low": lo, "high": hi,
                 "source": f"{DESIGN_DOC} section 11.5 row 'L3 / G4, C3, C4'"},
        "block_ratios_within_band": block_ratios_within,
        "calibrated_blocks": list(CALIBRATED_BLOCKS),
        "blocks_without_measured_cycles": missing,
        "ratio_count": len(ratios),
        "per_depth": per_depth,
        "per_block": per_block,
        "machine": {
            "clock_frequency_hz": clock_hz,
            "sequencer": sequencer.to_dict(),
            "tensor_engine_as_derived": engine.to_dict(),
            "note": (
                "lanes and work_per_lane_cycle are replaced per block by the "
                "RTL's; every other parameter is the derived machine's own"
            ),
        },
        "mapping": {
            "operation": (
                "each rate case is one TENSOR.MATMUL of the case's rows x cols "
                "output surface and reduction depth, tiled as one tile "
                "(tile_rows = rows, tile_cols = cols, tile_depth = depth, "
                "issue_window 1) and lane-mapped by tensor_lane_mapping with "
                "lanes = the block's lane count; the cost is "
                "CycleModel._compute_cycles's tensor branch, "
                "output_waves x ceil(tile_depth x scale / work_per_lane_cycle)"
            ),
            "units": (
                "the RTL measures lane-ops per lane-cycle, one lane-op being one "
                "multiply-accumulate of g products; the model's coordinate is one "
                "product (K element) and its rate is in work-counter units, "
                f"{TENSOR_WORK_UNITS_PER_PRODUCT} per product (tensor.multiplications "
                "+ tensor.additions, read off the step by CycleModel._work_scale).  "
                "work_per_lane_cycle handed to the model = measured.mac_per_lane_cycle "
                f"x g x {TENSOR_WORK_UNITS_PER_PRODUCT}.  The ratio is invariant to "
                "this unit choice because scale and rate carry the same factor."
            ),
            "lane_assignment": (
                "the model's mapper folds rows onto lanes (wave_rows = min(rows, "
                "lanes)) while ot_a3_lq8.sv gives lane i the block columns c x "
                "LANES + i; the two assignments yield the same wave count for "
                "every rate case here (rows x cols / lanes waves), which is the "
                "only thing the charge depends on"
            ),
            "steady_state_is_a_structure_check": (
                "with the model's rate set to the block's measured rate, the "
                "steady-state ratio can leave the band only through the wave "
                "count, the depth quantisation (ceil) or the tile-issue floor -- "
                "it checks the formula's structure, not the rate.  whole_run "
                "additionally compares the model's fixed per-instruction "
                "overheads (front end + fixed latency) with the RTL's fill and "
                "drain."
            ),
            "per_case_rate_vs_block_rate": (
                "rtl_products_per_lane_window_cycle is each case's own rate; the "
                "rate handed to the model is the record's headline "
                "measured.mac_per_lane_cycle, so a case whose own rate differed "
                "from the block's would show as a ratio off 1"
            ),
        },
        "ratios": ratios,
        "control_plane": cp,
        "boundary": boundary,
        "derived_machine": derived,
        "binding_regime": derived["binding_regime"],
        "clock": {
            "calibrated": False,
            "note": (
                "every ratio above is in cycles; the derived machine's clock "
                f"({clock_hz:g} Hz, from technology.json#latency."
                "sequencer_issue_decode_s) is a design-target assumption and no "
                "routed record at N5 exists.  The routed periods below are the "
                "open-PDK records and are context, not calibration."
            ),
            "routed": routed,
        },
    }


def calibration_artifact(
    anchor: Anchor, *, paths: Mapping[str, Path], **kw: Any,
) -> dict[str, Any]:
    """The full artifact: inputs by path and digest, git state, calibration."""
    inputs = {
        _relative(p): {"sha256": _sha256_of(p)} for p in sorted(set(paths.values()))
    }
    body = calibrate(anchor, **kw)
    return {
        "schema": CALIBRATION_SCHEMA,
        "generator": "tools/derive_cycle_machine.py --calibrate",
        "gate": "G4",
        "rung": "L3",
        "anchor": {
            "analytical_artifact": anchor.analytical_path,
            "rom_design": anchor.rom_design,
            "hbm_design": anchor.hbm_design,
            "batch_size": anchor.batch_size,
            "context_tokens": anchor.context_tokens,
        },
        "inputs": inputs,
        "git": _git_state(list(inputs)),
        "calibration": body,
    }


def calibration_input_paths(
    analytical: Path, technology: Path, *,
    lane_record: str = DEFAULT_LANE_RECORD,
    lane_groups_record: str = DEFAULT_LANE_GROUPS_RECORD,
    lq8_record: str = DEFAULT_LQ8_RECORD,
    control_plane_record: str = DEFAULT_CONTROL_PLANE_RECORD,
    reconciliation: str = DEFAULT_RECONCILIATION,
) -> dict[str, Path]:
    """Every file the calibration reads, by role; all are digested into the artifact."""
    tables = {
        "rom_cost_table": REPO / f"configs/hardware/abi3_cost_{TECHNOLOGY_VIEW}_rom_v1.json",
        "hbm_cost_table": REPO / f"configs/hardware/abi3_cost_{TECHNOLOGY_VIEW}_hbm_v1.json",
        "rom_capability": REPO / f"configs/hardware/abi3_capability/{TECHNOLOGY_VIEW}/rom_qwen3_n5_v1.json",
        "hbm_capability": REPO / f"configs/hardware/abi3_capability/{TECHNOLOGY_VIEW}/hbm_sram_single_chip_n5_v1.json",
    }
    return {
        "lane": REPO / lane_record,
        "lane_groups": REPO / lane_groups_record,
        "lq8": REPO / lq8_record,
        "control_plane": REPO / control_plane_record,
        "reconciliation": REPO / reconciliation,
        "pair_artifact": REPO / "results/derived/qwen3_n5_design_target_machine_pair.json",
        "analytical": analytical,
        "technology": technology,
        "design_doc": REPO / DESIGN_DOC,
        "gates": REPO / GATES_CONFIG,
        **tables,
        **{f"source:{s}": REPO / s for s in CYCLE_MODEL_SOURCES},
    }


ROUTED_CONTEXT_RECORDS = (
    "results/physical_abi3/asap7/a3_lane_pipelined/pnr.json",
    "results/physical_abi3/asap7/a3_lq8_array/pnr.json",
    "results/physical_abi3/asap7/a3_microsequencer/pnr.json",
)


def run_calibration(anchor: Anchor, analytical: Path, technology: Path,
                    **records: str) -> dict[str, Any]:
    """Load every input from disk and build the calibration artifact body."""
    paths = calibration_input_paths(analytical, technology, **records)
    missing = [str(p) for p in paths.values() if not p.exists()]
    if missing:
        raise DerivationError("calibration input(s) missing: " + ", ".join(missing))

    def load(key: str) -> Any:
        return json.loads(paths[key].read_text())

    routed: dict[str, Any] = {}
    for rel in ROUTED_CONTEXT_RECORDS:
        p = REPO / rel
        if p.exists():
            routed[rel] = json.loads(p.read_text())
            paths[f"routed:{rel}"] = p
    return calibration_artifact(
        anchor, paths=paths,
        lane=load("lane"), lane_groups=load("lane_groups"), lq8=load("lq8"),
        control_plane=load("control_plane"), reconciliation=load("reconciliation"),
        rom_table=load("rom_cost_table"), hbm_table=load("hbm_cost_table"),
        rom_capability=load("rom_capability"),
        doc_text=paths["design_doc"].read_text(),
        routed_records=routed,
    )


def _print_calibration(body: Mapping[str, Any]) -> None:
    cal = body["calibration"]
    print(f"{'block':<12} {'depth':<4} {'case':>4} {'sim':<9} {'quantity':<13} "
          f"{'rtl':>12} {'model':>12} {'ratio':>10} band")
    for r in cal["ratios"]:
        rtl = r["rtl_cycles"]
        rtl_s = f"{rtl:>12.1f}" if isinstance(rtl, float) else f"{rtl:>12}"
        print(f"{r['block']:<12} {r['depth']:<4} {r['case']:>4} {r['simulator']:<9} "
              f"{r['quantity']:<13} {rtl_s} {r['model_cycles']:>12} "
              f"{r['ratio_model_over_rtl']:>10.6f} "
              f"{'in' if r['within_band'] else 'OUT'}")
    cp = cal["control_plane"]
    print(f"control_plane: {cp['status']} -- {len(cp['cases'])} cases, no cycle count recorded")
    b = cal["boundary"]
    print(f"boundary: model chain {b['model_exposed_chain_cycles']} vs design "
          f"{b['design_cycles_per_boundary']} (band {b['design_band']}), ratio "
          f"{b['ratio_model_chain_over_design']:.4f}, measured={b['measured']}, "
          f"rung item met={b['rung_item_met']}")
    d = cal["derived_machine"]
    print(f"derived machine: roof {d['rom_machine']['compute_roof_ops_s']:.10e} vs "
          f"anchor {d['anchor']['compute_roof_ops_s']:.10e}, relative error "
          f"{d['rom_machine']['relative_error']:.3e}; regime same={d['binding_regime']['same_regime_both_targets']}")
    print(f"calibration.block_cycles_within_band = {cal['block_cycles_within_band']}")
    print(f"calibration.derived_machine_reproduces_anchor = {cal['derived_machine_reproduces_anchor']}")
    print(f"reason: {cal['reason']}")



def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--analytical", default=DEFAULT_ANALYTICAL)
    ap.add_argument("--technology", default=DEFAULT_TECHNOLOGY)
    ap.add_argument("--rom-design", default=DEFAULT_ROM_DESIGN)
    ap.add_argument("--hbm-design", default=DEFAULT_HBM_DESIGN)
    ap.add_argument("--rom-base", default=None,
                    help=("base ROM capability, repo-relative; defaults to the "
                          "record matching the model and topology_kind"))
    ap.add_argument("--hbm-base", default=None,
                    help="base GPU-side capability, repo-relative")
    ap.add_argument("--batch-size", type=int, default=1)
    ap.add_argument("--context-tokens", type=int, default=8192)
    ap.add_argument("--config-dir", default="configs/hardware")
    ap.add_argument("--artifact-dir", default="results/derived")
    ap.add_argument("--artifact", default=None,
                    help="override the artifact path for a single cell")
    ap.add_argument("--check", action="store_true",
                    help="verify the emitted files match a fresh derivation")
    ap.add_argument("--matrix", action="store_true",
                    help=("derive every cell the study publishes at batch 1 "
                          "and write a manifest of what could and could not "
                          "be reached"))
    ap.add_argument("--matrix-out",
                    default="results/derived/n5_design_target_matrix.json")
    ap.add_argument("--audit-deployments", nargs=2, metavar=("ROM_ROOT", "HBM_ROOT"),
                    help=("compare two deployments' tensor tile shapes and "
                          "storage classes"))
    ap.add_argument("--reconcile", nargs=2, metavar=("ROM_RUN", "HBM_RUN"),
                    help="D6 report: two run_abi3_cycle results against the anchor")
    ap.add_argument("--reconcile-out", default=None,
                    help="write the D6 report here instead of stdout")
    ap.add_argument("--calibrate", action="store_true",
                    help=("L3 / G4: charge the cycle model with exactly the "
                          "operations the L1 block records ran and write the "
                          "calibration artifact; with --check, verify the "
                          "artifact on disk against a fresh calibration"))
    ap.add_argument("--calibration-out", default=DEFAULT_CALIBRATION_OUT,
                    help="where --calibrate writes its artifact")
    ap.add_argument("--lane-record", default=DEFAULT_LANE_RECORD)
    ap.add_argument("--lane-groups-record", default=DEFAULT_LANE_GROUPS_RECORD)
    ap.add_argument("--lq8-record", default=DEFAULT_LQ8_RECORD)
    ap.add_argument("--control-plane-record", default=DEFAULT_CONTROL_PLANE_RECORD)
    ap.add_argument("--reconciliation", default=DEFAULT_RECONCILIATION)
    args = ap.parse_args(argv)

    config_dir = REPO / args.config_dir
    artifact_dir = REPO / args.artifact_dir
    analytical = REPO / args.analytical
    technology = REPO / args.technology

    if args.matrix:
        return _run_matrix(args, analytical, technology, config_dir, artifact_dir)

    anchor = load_anchor(
        analytical, technology,
        rom_design=args.rom_design, hbm_design=args.hbm_design,
        batch_size=args.batch_size, context_tokens=args.context_tokens,
    )
    if args.calibrate:
        body = run_calibration(
            anchor, analytical, technology,
            lane_record=args.lane_record,
            lane_groups_record=args.lane_groups_record,
            lq8_record=args.lq8_record,
            control_plane_record=args.control_plane_record,
            reconciliation=args.reconciliation,
        )
        out = REPO / args.calibration_out
        if args.check:
            if not out.exists():
                print(f"DRIFT: {out} is missing", file=sys.stderr)
                return 1
            on_disk = json.loads(out.read_text())
            fresh = {k: v for k, v in body.items() if k != "git"}
            stale = {k: v for k, v in on_disk.items() if k != "git"}
            if canonical(fresh) != canonical(stale):
                print(
                    f"DRIFT: {out} does not match a fresh calibration of its "
                    "inputs; re-run --calibrate",
                    file=sys.stderr,
                )
                return 1
            cal = on_disk["calibration"]
            print(
                f"derive_cycle_machine --calibrate --check: {_relative(out)} "
                f"reproduces from its inputs; block_cycles_within_band="
                f"{cal['block_cycles_within_band']}, "
                f"derived_machine_reproduces_anchor="
                f"{cal['derived_machine_reproduces_anchor']}"
            )
            return 0
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(canonical(body))
        _print_calibration(body)
        print(f"wrote {_relative(out)}")
        return 0

    rom_base, hbm_base = base_capabilities(anchor, args.rom_base, args.hbm_base)
    d, bodies = build(anchor, rom_base, hbm_base)
    paths = emitted_paths(anchor, config_dir, artifact_dir, rom_base, hbm_base)
    if args.artifact:
        paths["artifact"] = REPO / args.artifact
    rendered = {k: canonical(bodies[k]) for k in bodies}

    if args.check:
        bad = []
        for key in ("rom_cost_table", "hbm_cost_table",
                    "rom_capability", "hbm_capability"):
            path = paths[key]
            if not path.exists():
                bad.append(f"{path} is missing")
            elif path.read_text() != rendered[key]:
                bad.append(f"{path} does not match a fresh derivation")
        if bad:
            for line in bad:
                print(f"DRIFT: {line}", file=sys.stderr)
            return 1
        # The assertion runs on --check too: a hand edit that kept both files
        # internally consistent but broke comparability must not pass.
        comparability = assert_comparable(
            bodies["rom_capability"], paths["rom_cost_table"],
            bodies["hbm_capability"], paths["hbm_cost_table"],
            allowlist=allowlist_for(anchor),
        )
        print(
            f"derive_cycle_machine --check: all emitted files match the "
            f"anchor; {comparability['parameters_compared']} parameters "
            f"compared, {len(comparability['permitted_differences'])} "
            f"permitted differences, 0 unexpected"
        )
        return 0

    if args.reconcile:
        report = reconcile(
            anchor,
            json.loads(Path(args.reconcile[0]).read_text()),
            json.loads(Path(args.reconcile[1]).read_text()),
        )
        text = canonical(report)
        if args.reconcile_out:
            out = Path(args.reconcile_out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text)
            print(f"wrote {out}")
        else:
            print(text)
        return 0

    if args.audit_deployments:
        from runtime.abi3.capability import Capability
        from runtime.cycle.machine import MachineModel, load_cost_table

        # Charge with the derived machine of this anchor, rendered to scratch
        # so the audit does not depend on the emitted files being on disk.
        with tempfile.TemporaryDirectory() as tmp:
            table = Path(tmp) / paths["rom_cost_table"].name
            table.write_text(rendered["rom_cost_table"])
            machine = MachineModel(
                Capability.from_dict(bodies["rom_capability"]),
                load_cost_table(table),
            )
            report = audit_deployments(
                Path(args.audit_deployments[0]), Path(args.audit_deployments[1]),
                symbols=decode_request_symbols(args.batch_size, args.context_tokens),
                machine=machine,
            )
        print(json.dumps(report, indent=2))
        return 0 if report["comparable"] else 3

    out = emit_cell(anchor, config_dir, artifact_dir,
                    rom_base=rom_base, hbm_base=hbm_base, write=True)
    if args.artifact:
        art_path = REPO / args.artifact
        art_path.parent.mkdir(parents=True, exist_ok=True)
        art_path.write_text(canonical(out["artifact"]))
    comparability = out["comparability"]
    print(f"emitted {len(bodies)} files for anchor "
          f"{anchor.rom_design} vs {anchor.hbm_design}")
    for path in out["paths"].values():
        print(f"  {_relative(path)}")
    print(f"comparability: {comparability['parameters_compared']} parameters "
          f"compared, {len(comparability['permitted_differences'])} permitted "
          f"differences, 0 unexpected")
    return 0


def _run_matrix(args: Any, analytical: Path, technology: Path,
                config_dir: Path, artifact_dir: Path) -> int:
    body = json.loads(analytical.read_text())
    cells = matrix_cells(body)
    emitted: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    drifted: list[str] = []
    for cell in cells:
        record = {
            "rom_design": cell["rom_design"],
            "hbm_design": cell["hbm_design"],
            "why_this_cell": cell["why"],
            "batch_size": args.batch_size,
        }
        try:
            anchor = load_anchor(
                analytical, technology,
                rom_design=cell["rom_design"], hbm_design=cell["hbm_design"],
                batch_size=args.batch_size,
                context_tokens=int(
                    [p for p in body["points"]
                     if p["design"] == cell["rom_design"]
                     and int(p["batch_size"]) == args.batch_size][0]
                    ["context_tokens"]
                ),
            )
            out = emit_cell(anchor, config_dir, artifact_dir, write=not args.check)
        except Exception as exc:  # noqa: BLE001 -- the manifest records why
            record["blocked_by"] = f"{type(exc).__name__}: {exc}"
            blocked.append(record)
            continue
        if out["drift"]:
            drifted.extend(out["drift"])
        A, d = anchor, out["derivation"]
        record.update({
            "pair_id": pair_id(A),
            "model": A.rom["model"],
            "context_tokens": A.context_tokens,
            "rom_topology_kind": A.rom.get("topology_kind"),
            "rom_parallelism": A.rom.get("parallelism"),
            "rom_kv_store": A.rom_kv_store,
            "rom_token_slots": A.rom_token_slots,
            "hbm_token_slots": A.hbm_token_slots,
            "rom_execution_format": A.rom.get("execution_format"),
            "rom_devices": A.rom["device_count"],
            "hbm_devices": A.hbm["device_count"],
            "iso_area_ratio": (
                A.rom["silicon_area_mm2"] / A.hbm["silicon_area_mm2"]
            ),
            "rom_binding_constraint": A.rom["binding_constraint"],
            "hbm_binding_constraint": A.hbm["binding_constraint"],
            "binding_constraints_agree": (
                A.rom["binding_constraint"] == A.hbm["binding_constraint"]
            ),
            "rom_per_user_tokens_s": A.rom["per_user_tokens_s"],
            "hbm_per_user_tokens_s": A.hbm["per_user_tokens_s"],
            "published_ratio": (
                A.rom["per_user_tokens_s"] / A.hbm["per_user_tokens_s"]
            ),
            "compute_roof_ops_s": d.facts["compute_roof_ops_s"],
            "shared_roof": next(
                ({"direction": r["direction"], "ratio": r["ratio"],
                  "gpu_memory_over_compute_x": r["gpu_memory_over_compute_x"]}
                 for r in d.residuals if r["kind"] == "shared_roof_handicap"),
                None,
            ),
            "residual_kinds": sorted({r["kind"] for r in d.residuals}),
            "tensor_lanes": int(d.shared["engine.tensor.lanes.default"].value),
            "rom_arrays": d.facts["rom_arrays"],
            "base_capabilities": {
                "rom": d.facts["rom_base_capability"],
                "hbm": d.facts["hbm_base_capability"],
            },
            "comparability": {
                "parameters_compared":
                    out["comparability"]["parameters_compared"],
                "permitted_differences":
                    sorted(out["comparability"]["permitted_differences"]),
                "allowlist": out["comparability"]["allowlist"],
                "allowlist_unused": out["comparability"]["allowlist_unused"],
                "unexpected_differences": 0,
            },
            "declared_asymmetries": [
                a["field"] for a in d.facts.get("declared_asymmetries", [])
            ],
            "emitted": {k: _relative(v) for k, v in out["paths"].items()},
        })
        emitted.append(record)

    manifest = {
        "schema": "opentallas.derived_cycle_machine.matrix.v1",
        "generator": "tools/derive_cycle_machine.py --matrix",
        "analytical_artifact": _relative(analytical),
        "study_id": body.get("study_id", ""),
        "batch_size": args.batch_size,
        "context_note": (
            "The study prices each model at exactly ONE context: Qwen3-8B at "
            "8,192, DeepSeek-V4-Flash-0731 at 200,000 and DeepSeek-V4-Pro-0813 "
            "at 1,000,000.  There is no batch-1/context-8192 cell for either "
            "DeepSeek model and none can be read from this artifact, so each "
            "cell is derived at its own model's published context and the "
            "context is recorded per cell.  The derived KV term is anchored to "
            "that context while a cycle run must use a short one, so the "
            "kv_read residual for both DeepSeek models is a REPORTED "
            "divergence and must not be closed by lengthening the run."
        ),
        "selection_rule": (
            "Every cell is taken from the artifact: the batch-1 recommendation "
            "of each model, every entry of each published batch-1 frontier, "
            "the best array and best wafer topology the study names per model, "
            "and the ROM design points the repository already has a capability "
            "shape for.  The GPU side of each cell is the artifact's own "
            "iso-area comparator for that ROM design; no comparator is chosen "
            "here."
        ),
        "cells_considered": len(cells),
        "cells_emitted": len(emitted),
        "cells_blocked": len(blocked),
        "emitted": emitted,
        "blocked": blocked,
    }
    out_path = REPO / args.matrix_out
    if args.check:
        if out_path.exists() and out_path.read_text() != canonical(manifest):
            drifted.append(f"{_relative(out_path)} does not match a fresh run")
        elif not out_path.exists():
            drifted.append(f"{_relative(out_path)} is missing")
        for line in drifted:
            print(f"DRIFT: {line}", file=sys.stderr)
        print(f"matrix --check: {len(emitted)} cells emitted, "
              f"{len(blocked)} blocked, {len(drifted)} drifted")
        return 1 if drifted else 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(canonical(manifest))
    print(f"matrix: {len(emitted)} cells emitted, {len(blocked)} blocked, "
          f"of {len(cells)} considered")
    for row in emitted:
        print(f"  OK      {row['model']:24s} {row['rom_design']}")
    for row in blocked:
        print(f"  BLOCKED {row['rom_design']}: {row['blocked_by'][:120]}")
    print(f"  {_relative(out_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
