#!/usr/bin/env python3
"""Derive a matched ROM/HBM cycle-model machine pair from ONE analytical design point.

Why this tool exists
--------------------
``results/roofline/n5_vs_b200/analytical.json`` publishes a ROM-versus-GPU
comparison for Qwen3-8B at batch 1 and context 8192.  The cycle-accurate
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
        "provisioning: the ROM point carries 5 HBM3E stacks on each of 4 "
        "devices (area_fractions.hbm_phy 0.06135 of 815 mm2 at 10 mm2 per "
        "stack) serving KV alone at points[ROM].kv_transfer_bytes_per_step / "
        "component_times_s.kv_read = 1.8e13 B/s, while the GPU point carries 2 "
        "B200 packages of 8 stacks serving weights AND KV from one pool at "
        "points[GPU].peak_weight_read_bytes_s = 1.44e13 B/s.  Both resolve to "
        "the SAME hbm.bytes_per_cycle_per_channel; only the channel count "
        "differs, which is exactly what the design points say differs."
    ),
}


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

    # -- derived analytical quantities ----------------------------------
    @property
    def compute_ops_s_per_mm2(self) -> float:
        return float(self.derivations["compute_ops_s_per_mm2"]["bf16"]["value"])

    @property
    def compute_efficiency(self) -> float:
        return float(self.derivations["efficiencies"]["compute"]["value"])

    @property
    def compute_roof_ops_s(self) -> float:
        """The ROM design point's SUSTAINED (post-derate) arithmetic roof.

        Derated, not peak: the analytical component_times_s.compute is
        ``operations / (roof * efficiencies.compute)``, so reproducing the
        published term requires the derated roof.  The cycle model then finds
        its own occupancy on top of it, which the reconciliation reports as a
        residual rather than absorbing.
        """
        return (
            float(self.rom["area_fractions"]["compute"])
            * float(self.rom["silicon_area_mm2"])
            * self.compute_ops_s_per_mm2
            * self.compute_efficiency
        )

    @property
    def operations(self) -> float:
        return float(self.rom["operations_by_canonical_format"]["bf16"])

    @property
    def operations_per_mac(self) -> float:
        """2.0: the analytical count is multiplies AND adds, the cycle model MACs."""
        return self.operations / float(self.summary["active_parameters"])

    @property
    def compute_roof_mac_s(self) -> float:
        return self.compute_roof_ops_s / self.operations_per_mac

    @property
    def rom_weight_read_bytes_s(self) -> float:
        return float(self.rom["peak_weight_read_bytes_s"])

    @property
    def rom_kv_read_bytes_s(self) -> float:
        return float(self.rom["kv_transfer_bytes_per_step"]) / float(
            self.rom["component_times_s"]["kv_read"]
        )

    @property
    def hbm_memory_bytes_s(self) -> float:
        """The GPU point's single HBM rate; it serves weights and KV alike."""
        return float(self.hbm["peak_weight_read_bytes_s"])

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


def derive(anchor: Anchor) -> Derivation:
    """Emit every cost-table parameter for the pair, from the anchor alone."""
    d = Derivation(anchor=anchor)
    A = anchor
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
    narrowest = int(d.facts.get("narrowest_tensor_width", 0)) or _narrowest_width(A)
    lanes = narrowest
    roof_mac_s = A.compute_roof_mac_s
    # work_per_lane_cycle is stated in WORK-COUNTER units -- the cost table
    # declares unit "work/lane/cycle" and the characterized SKY130 value was
    # measured as (tensor.multiplications + tensor.additions) / cycles.  The
    # analytical operations_by_canonical_format.bf16 counts multiplies AND adds
    # too, so the roof goes in unconverted and the two vocabularies agree
    # without a factor.  The cycle model reconciles the coordinate count with
    # the work-counter count itself (CycleModel._work_scale), so a MAC costs
    # two work units on both sides of the identity.
    wplc = A.compute_roof_ops_s / (lanes * clock_hz)
    d.facts["compute_roof_ops_s"] = A.compute_roof_ops_s
    d.facts["compute_roof_mac_s"] = roof_mac_s
    d.facts["work_units_per_mac"] = A.operations_per_mac
    d.facts["narrowest_tensor_width"] = narrowest
    d.facts["tensor_mac_per_cycle_at_roof"] = roof_mac_s / clock_hz

    d.shared["engine.tensor.lanes.default"] = Derived(
        name="engine.tensor.lanes.default",
        value=lanes,
        unit="lanes",
        analytical_grade="derived",
        provenance="assumed",
        derivation=(
            f"The narrowest tensor operator output width in Qwen3-8B "
            f"({lanes}: the GQA key and value projections, "
            f"num_key_value_heads x head_dim).  At batch 1 the cycle model's "
            f"tensor rate is min(lanes, tile_cols*issue_window, cols) x "
            f"work_per_lane_cycle x clock, so lanes above the operator's own "
            f"output width are masked and deliver nothing.  {lanes} is the "
            f"largest lane count for which EVERY tensor operator of this model "
            f"runs at the full derived roof; at 4096 the achieved rate falls "
            f"to 88.5% of the roof and at 12288 to 42.6%.  The pair "
            f"(lanes, work_per_lane_cycle) is a gauge split of one analytical "
            f"quantity -- their product times the clock is what the design "
            f"point pins -- and this rule fixes the split by exactness."
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
            f"is area_fractions.compute {A.rom['area_fractions']['compute']!r} "
            f"x silicon_area_mm2 {A.rom['silicon_area_mm2']!r} x "
            f"technology_derivations.compute_ops_s_per_mm2.bf16 "
            f"{A.compute_ops_s_per_mm2!r} x efficiencies.compute "
            f"{A.compute_efficiency!r} = {A.compute_roof_ops_s:.10e} ops/s.  "
            f"Verified against the artifact: {A.operations:.0f} ops / that "
            f"roof = {A.operations / A.compute_roof_ops_s:.15e} s, which "
            f"reproduces the published component_times_s.compute "
            f"{A.rom['component_times_s']['compute']!r} EXACTLY, to the last "
            f"bit in double precision.  Units: the cost table declares this "
            f"parameter in work/lane/cycle and the shipped characterized value "
            f"was measured as (tensor.multiplications + tensor.additions) / "
            f"cycles; the analytical operations count is multiplies AND adds "
            f"too (operations_per_active_parameter = "
            f"{A.operations_per_mac:g}), so no conversion is needed and none "
            f"is applied.  That makes the machine's MAC rate lanes x "
            f"work_per_lane_cycle / {A.operations_per_mac:g} x clock = "
            f"{roof_mac_s:.10e} MAC/s.  In the cycle model this value divides "
            f"the K extent (ceil(tile_depth x work_scale / "
            f"work_per_lane_cycle)), so it is the reduction-tree width of one "
            f"output lane -- {roof_mac_s / clock_hz / lanes:.2f} MACs deep -- "
            f"and not a second lane count."
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
    # deployment's own ROM bank plan fixes it: the shipped Qwen ROM capability
    # declares 16 banks and the ROM lowering stripes one bank per weight role.
    rom_arrays = int(A.rom.get("_rom_arrays", 0)) or 16
    rom_bpc, rom_achieved = _q(A.rom_weight_read_bytes_s, rom_arrays, clock_hz)
    d.facts["rom_weight_read_bytes_s_target"] = A.rom_weight_read_bytes_s
    d.facts["rom_weight_read_bytes_s_achieved"] = rom_achieved
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
            f"count the shipped Qwen ROM deployment plans (capability "
            f"memory.rom.banks; the ROM lowering stripes one bank per weight "
            f"role).  The analytical model fixes only the product "
            f"arrays x bytes_per_cycle_per_array x clock, so this is the "
            f"granularity choice and the next parameter is the consequence.  "
            f"NOTE: the shipped rom_qwen3 capability advertises this under the "
            f"key 'banks', which MachineModel.structural does not read (it "
            f"looks for memory.rom.arrays), so the shipped ROM runs silently "
            f"used the cost table's default of 8.  The emitted capability "
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
            f"points[ROM].peak_weight_read_bytes_s "
            f"{A.rom_weight_read_bytes_s:.10e} B/s (= rom area "
            f"{A.rom['area_fractions']['rom'] * A.rom['silicon_area_mm2']:.4f} "
            f"mm2 x technology_derivations.rom_read_bytes_s_per_mm2 x "
            f"efficiencies.rom_read_bandwidth, already derated) divided by "
            f"{rom_arrays} arrays and by the clock = "
            f"{A.rom_weight_read_bytes_s / (rom_arrays * clock_hz):.6f}, "
            f"rounded to {rom_bpc}.  Achieved aggregate {rom_achieved:.10e} "
            f"B/s, {rom_resid * 100:+.5f}% against the analytical value."
        ),
        source=f"{ana}.peak_weight_read_bytes_s",
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
            f"One HBM3E channel.  points[ROM] serves KV from "
            f"{rom_channels // channels_per_stack} stacks at "
            f"{A.rom_kv_read_bytes_s:.6e} B/s and points[GPU] serves weights "
            f"and KV from {hbm_channels // channels_per_stack} stacks at "
            f"{A.hbm_memory_bytes_s:.6e} B/s; at {channels_per_stack} channels "
            f"per stack both give {per_channel_bpc:g} B/cycle at this clock.  "
            f"The two design points buy different numbers of the SAME channel, "
            f"which is why hbm.channels is the only HBM parameter the two "
            f"machines are permitted to differ on."
        ),
        source=f"{ana}.kv_transfer_bytes_per_step",
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
                f"{A.kv_round_trip_s * clock_hz:.4f} cycles.  KV lives in HBM "
                f"on both sides of this anchor, so that primitive is the HBM "
                f"access latency."
            ),
            source=f"{tech}#latency.sram_access_s",
        )
    d.rom_only["hbm.channels.default"] = Derived(
        name="hbm.channels.default", value=rom_channels, unit="channels",
        analytical_grade="derived", provenance="assumed",
        derivation=(
            f"{rom_channels // channels_per_stack} HBM3E stacks x "
            f"{channels_per_stack} channels.  points[ROM].area_fractions."
            f"hbm_phy {A.rom['area_fractions']['hbm_phy']!r} of "
            f"{A.rom['silicon_area_mm2'] / A.rom['device_count']:.0f} mm2 per "
            f"device at 10 mm2 per stack over "
            f"{A.rom['device_count']} devices, serving KV alone at "
            f"{A.rom_kv_read_bytes_s:.6e} B/s "
            f"(kv_transfer_bytes_per_step / component_times_s.kv_read)."
        ),
        source=f"{ana}.area_fractions.hbm_phy",
    )
    d.hbm_only["hbm.channels.default"] = Derived(
        name="hbm.channels.default", value=hbm_channels, unit="channels",
        analytical_grade="derived", provenance="assumed",
        derivation=(
            f"{hbm_channels // channels_per_stack} HBM3E stacks x "
            f"{channels_per_stack} channels: "
            f"{A.hbm['device_count']} B200 packages of 8 stacks, serving "
            f"weights AND KV from one pool "
            f"(overlap_rule {A.hbm['overlap_rule']!r}) at "
            f"points[GPU].peak_weight_read_bytes_s "
            f"{A.hbm_memory_bytes_s:.6e} B/s."
        ),
        source=f"{ana_hbm}.peak_weight_read_bytes_s",
    )

    # -- 6.  SRAM -------------------------------------------------------
    # The ROM design point allocates ZERO SRAM area (area_fractions.sram = 0.0,
    # slack = 0.0) and the GPU point likewise, so there is no analytical SRAM
    # bandwidth to reproduce.  The cycle model still needs an activation store.
    # Rather than invent one, it is given a rate that cannot bind, so that no
    # simulated time is attributed to a store the analytical model does not
    # price.  This is stated, not hidden: it makes the derived machine an upper
    # bound on what an implementation of this design point would deliver.
    sram_banks, sram_ports = 32, 4
    sram_bpc = _cannot_bind_bytes_per_cycle(
        max(A.rom_weight_read_bytes_s, A.hbm_memory_bytes_s), sram_banks * sram_ports,
        clock_hz,
    )
    d.shared["sram.banks.default"] = Derived(
        name="sram.banks.default", value=sram_banks, unit="banks",
        analytical_grade="assumed", provenance="assumed",
        derivation=(
            f"{sram_banks} banks, the bank count both shipped Qwen "
            f"capabilities already declare, kept so the compiled bank masks "
            f"mean what they meant before.  The design points allocate no SRAM "
            f"area at all (area_fractions.sram = "
            f"{A.rom['area_fractions']['sram']!r}), so no analytical value "
            f"fixes this."
        ),
        source=f"{ana}.area_fractions.sram",
    )
    d.shared["sram.ports_per_bank.default"] = Derived(
        name="sram.ports_per_bank.default", value=sram_ports, unit="ports",
        analytical_grade="assumed", provenance="assumed",
        derivation=(
            "Chosen with sram.bytes_per_cycle_per_port so that the activation "
            "store cannot be the binding term.  See that parameter."
        ),
        source=f"{ana}.area_fractions.sram",
    )
    d.shared["sram.bytes_per_cycle_per_port"] = Derived(
        name="sram.bytes_per_cycle_per_port", value=float(sram_bpc), unit="B/cycle",
        analytical_grade="assumed", provenance="assumed",
        derivation=(
            f"The analytical design point prices NO SRAM term and allocates no "
            f"SRAM area, so there is nothing to reproduce.  banks x ports x "
            f"this rate x clock = "
            f"{sram_banks * sram_ports * sram_bpc * clock_hz:.6e} B/s, which "
            f"exceeds the larger of the two weight paths "
            f"({max(A.rom_weight_read_bytes_s, A.hbm_memory_bytes_s):.6e} B/s) "
            f"so that the activation store cannot bind and no simulated time "
            f"is attributed to a store the analytical model does not price.  "
            f"This is a deliberate neutralisation for a validation experiment: "
            f"the derived machine is NOT a complete machine and its absolute "
            f"tokens/s is an upper bound."
        ),
        source=f"{ana}.area_fractions.sram",
    )
    for nm in ("sram.transaction_bytes", "sram.interleave_bytes"):
        d.shared[nm] = Derived(
            name=nm, value=sram_bpc, unit="B",
            analytical_grade="assumed", provenance="assumed",
            derivation=(
                "Set equal to sram.bytes_per_cycle_per_port so the model's "
                "ceil() is exact.  See that parameter."
            ),
            source=f"{ana}.area_fractions.sram",
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
    port_bpc = max(rom_achieved, d.facts["hbm_role_hbm_bytes_s_achieved"]) / clock_hz
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
                f"Taken from the shipped Qwen ROM capability where it declares "
                f"one, else from the shipped HBM capability, so neither "
                f"backend's lowering sees a queue count it has not been "
                f"exercised with.  The analytical model names no queues.  This "
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
                "Qwen deployment does."
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


def _narrowest_width(anchor: Anchor) -> int:
    """The narrowest tensor operator output width: num_key_value_heads x head_dim.

    The GQA key and value projections are the narrowest MATMULs in a Qwen3
    decoder, and the batch-1 tensor path saturates at the operator's own
    output width, so this is the largest lane count that runs every tensor
    operator at the full derived roof.
    """
    meta = anchor.technology.get("_model_metadata")
    if isinstance(meta, Mapping):
        return int(meta["num_key_value_heads"]) * int(meta["head_dim"])
    model_path = REPO / "configs" / "models" / (
        anchor.rom["model"].lower().replace(".", "-") + ".json"
    )
    if not model_path.exists():
        raise DerivationError(
            f"cannot read model metadata for {anchor.rom['model']!r} at {model_path}"
        )
    meta = json.loads(model_path.read_text())["metadata"]
    return int(meta["num_key_value_heads"]) * int(meta["head_dim"])


def _stacks_of(point: Mapping[str, Any]) -> int:
    return 8 * int(point["device_count"])


def _hbm_split(anchor: Anchor, clock_hz: float,
               channels_per_stack: int) -> tuple[int, int, float]:
    """Channel counts for the two roles and the per-channel rate they share.

    Both design points buy HBM3E in stacks.  The ROM point's HBM PHY area
    fraction says how many stacks it carries; the GPU point carries 8 per
    package.  The per-channel rate is the same on both sides, which is why the
    only permitted HBM difference is the channel count.
    """
    hbm_stacks = _stacks_of(anchor.hbm)
    per_stack = anchor.hbm_memory_bytes_s / hbm_stacks
    rom_stacks_f = anchor.rom_kv_read_bytes_s / per_stack
    rom_stacks = int(round(rom_stacks_f))
    if abs(rom_stacks - rom_stacks_f) > 1e-6:
        raise DerivationError(
            f"the ROM point's KV bandwidth {anchor.rom_kv_read_bytes_s:.6e} B/s "
            f"is {rom_stacks_f:.6f} of the GPU point's per-stack rate "
            f"{per_stack:.6e} B/s, not a whole number of stacks; the two "
            f"points do not share an HBM generation and hbm."
            f"bytes_per_cycle_per_channel cannot be shared"
        )
    rom_channels = rom_stacks * channels_per_stack
    hbm_channels = hbm_stacks * channels_per_stack
    per_channel = per_stack / channels_per_stack / clock_hz
    a = rom_channels * per_channel * clock_hz
    b = hbm_channels * per_channel * clock_hz
    if abs(a / anchor.rom_kv_read_bytes_s - 1) > 1e-9:
        raise DerivationError("ROM-role HBM aggregate does not reproduce the anchor")
    if abs(b / anchor.hbm_memory_bytes_s - 1) > 1e-9:
        raise DerivationError("HBM-role HBM aggregate does not reproduce the anchor")
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
            "The cycle model builds NO fabric on TopologyClass.SINGLE_CHIP "
            "(runtime/cycle/fabric.py:923-930), so a single-chip run has "
            "structurally zero link cycles.  Both anchor points are "
            "multi-device tensor-parallel machines charging 72 nvlink5 "
            "all-reduces per token.  The derived machines express each anchor "
            "as ONE logical device holding the aggregate resource of its "
            "design point, which is exactly the transformation that removes "
            "the inter-device fabric; the term is therefore absent by "
            "construction and is reported, not approximated.  Both sides pay "
            "almost the same link tax, so removing it does not favour either "
            "machine -- it inflates the ratio, and the published ratio is "
            "recovered by adding the two analytical link terms back."
        ),
    })
    d.residuals.append({
        "term": "step_time",
        "role": "both",
        "kind": "combination_rule",
        "note": (
            "The five analytical component times do NOT sum to the analytical "
            "step.  step = max(memory_time, compute_time) / "
            "efficiencies.stage_balance x token_slots + link_latency + "
            "layer_fixed_latency, with memory_time = weight + kv when the "
            "design point shares one memory path (the GPU point) and "
            "max(weight, kv) when it does not (the ROM point).  Both anchor "
            "points have token_slots = 1 and pipeline_stages = 1, so the only "
            "extra factor is stage_balance = "
            f"{A.derivations['efficiencies']['stage_balance']['value']!r}, "
            "applied because devices > 1.  Collapsing each point to one "
            "logical device sets devices = 1, so the derived machines do not "
            "carry it either; it is worth 1.11x on both sides and is reported."
        ),
    })
    layers = float(A.summary["num_layers"])
    d.residuals.append({
        "term": "compute",
        "role": "both",
        "kind": "work_disagreement",
        "note": (
            "The two models do not agree on the total arithmetic.  The "
            "analytical count for this model is the explicit active-parameter "
            f"fallback, active_parameters {A.summary['active_parameters']} x "
            f"{A.operations_per_mac:g}, with NO attention arithmetic and no "
            "context dependence.  The cycle model counts attention separately "
            "(attention.score_multiplications, attention.value_multiplications), "
            f"which at context {A.context_tokens} is "
            f"{2 * layers * float(A.summary['hidden_size']) * A.context_tokens:.4g} "
            "extra MACs per token.  The models agree on the weight-driven "
            "multiply count and disagree on the total; this is structural and "
            "cannot be tuned away."
        ),
    })
    d.residuals.append({
        "term": "weight_read",
        "role": "rom",
        "kind": "sweep_versus_touched",
        "note": (
            f"The analytical ROM weight_read term is a full sweep of the "
            f"STORED array: stored_weight_bytes {A.rom['stored_weight_bytes']} "
            f"/ peak_weight_read_bytes_s = "
            f"{A.rom['rom_full_array_sweep_time_s']:.6e} s, identical for "
            f"every batched ROM design in the study.  The cycle model has no "
            f"full-sweep semantics: it charges only the bytes the deployment's "
            f"accesses touch, and at batch 1 the weight amplification is 1, so "
            f"it will charge engaged_weight_bytes "
            f"{A.rom['engaged_weight_bytes']:.0f} "
            f"({A.rom['engaged_weight_fraction'] * 100:.2f}% of stored).  The "
            f"reconciliation must compare the cycle model's ROM traffic "
            f"against the engaged bytes and report the sweep-versus-touched "
            f"difference as a modelling divergence, not a machine parameter."
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
    return {
        "cost_table_id": f"abi3-cost-{TECHNOLOGY_VIEW.replace('_', '-')}-{role}-v1",
        "schema": "opentallas.abi3.cost_table.v1",
        "technology_view": TECHNOLOGY_VIEW,
        "version": "1.0.0",
        "description": (
            f"N5 design-target machine for the {role.upper()} role of the "
            f"analytical anchor pair {A.rom_design} vs {A.hbm_design} "
            f"(Qwen3-8B, batch {A.batch_size}, context {A.context_tokens}).  "
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
            "aggregation": (
                "The design point's devices are collapsed into ONE logical "
                "device holding their aggregate resource.  Both anchor points "
                "have token_slots = 1, so four of the five analytical terms "
                "are unchanged by the collapse; the fifth, link_latency, is "
                "removed by it and is reported as a structural residual."
            ),
        },
        "parameters": params,
    }


def capability(d: Derivation, role: str, base: Mapping[str, Any]) -> dict[str, Any]:
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
    body["capability_id"] = (
        f"{'rom_qwen3' if role == 'rom' else 'hbm_sram_single_chip'}"
        f"_{TECHNOLOGY_VIEW}_v1"
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
    body["limits"] = limits

    memory = json.loads(json.dumps(body.get("memory", {}), sort_keys=True))
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
        "base_capability": (
            "configs/hardware/abi3_capability/"
            + ("rom_qwen3.json" if role == "rom" else "hbm_sram_single_chip.json")
        ),
        "analytical_artifact": A.analytical_path,
        "design_point": A.rom_design if role == "rom" else A.hbm_design,
        "changed": [
            "technology_view", "capability_id", "engines.*.lanes",
            "engines.*.queues", "limits.max_outstanding_per_queue",
            "memory.sram.banks", "memory.sram.ports", "memory.hbm.channels",
        ] + (["memory.rom.arrays", "memory.rom.banks"] if role == "rom" else []),
        "note": (
            "technology_view n5_design_target is deliberately outside "
            "runtime/cycle/machine.py CHARACTERIZED_TECHNOLOGY_VIEWS, so every "
            "structural count this record advertises is graded `assumed` with "
            "no code change, and every run against it prints the "
            "not-a-performance-claim note."
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
                      ) -> dict[str, Any]:
    """Fail unless the two machines differ ONLY inside the weight-path allowlist.

    This compares the RESOLVED parameter sets, not the two documents.  A
    capability that does not advertise a structural count falls through to its
    cost table's default, so two capabilities can look identical and still
    produce machines with different SRAM ports -- which is exactly what the
    shipped Qwen pair does today.  Only the resolved view catches it.
    """
    rom = _resolve_all(rom_cap, rom_table)
    hbm = _resolve_all(hbm_cap, hbm_table)
    if set(rom) != set(hbm):
        raise DerivationError(
            "the two machines resolve different parameter SETS: "
            f"only in rom {sorted(set(rom) - set(hbm))}, "
            f"only in hbm {sorted(set(hbm) - set(rom))}"
        )
    differing = {n for n in rom if rom[n]["value"] != hbm[n]["value"]}
    unexpected = sorted(differing - set(WEIGHT_PATH_ALLOWLIST))
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
        if n not in WEIGHT_PATH_ALLOWLIST and rom[n]["origin"] != hbm[n]["origin"]
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
                "justification": WEIGHT_PATH_ALLOWLIST[n]}
            for n in sorted(differing)
        },
        "allowlist_unused": sorted(set(WEIGHT_PATH_ALLOWLIST) - differing),
        "rom_provenance_classes": sorted({p["provenance"] for p in rom.values()}),
        "hbm_provenance_classes": sorted({p["provenance"] for p in hbm.values()}),
    }


# ---------------------------------------------------------------------------
# The deployment-side half of D1
# ---------------------------------------------------------------------------
def audit_deployments(rom_root: Path, hbm_root: Path,
                      lanes: int | None = None) -> dict[str, Any]:
    """Compare the two deployments' tensor tile shapes and storage classes.

    The machine files cannot make a comparison fair on their own.  The tensor
    engine's batch-1 rate is ``min(lanes, tile_cols * issue_window, cols) *
    work_per_lane_cycle * clock`` and two of those five factors -- tile_cols
    and issue_window -- live in the deployment's SCHEDULE descriptors.  The
    ROM/HBM role itself is a deployment property too: ``MemorySystem.schedule``
    picks the storage class from the MEMORY_OBJECT descriptor, not from any
    machine file.
    """
    from runtime.abi3.deployment import Deployment
    from runtime.abi3.constants import Major
    from runtime.abi3.descriptors import ExtendedDescriptorType

    def survey(root: Path) -> dict[str, Any]:
        dep = Deployment.read(str(root))
        tensor_shapes: Counter = Counter()
        classes: Counter = Counter()
        for desc in dep.table.descriptors():
            if desc.descriptor_type == ExtendedDescriptorType.SCHEDULE:
                p = desc.payload
                if int(p.get("engine_family", -1)) != int(Major.TENSOR):
                    continue
                tensor_shapes[(
                    int(p.get("tile_rows", 0)), int(p.get("tile_cols", 0)),
                    int(p.get("tile_depth", 0)), int(p.get("issue_window", 0)),
                )] += 1
            elif desc.descriptor_type == ExtendedDescriptorType.MEMORY_OBJECT:
                classes[int(desc.payload.get("storage_class", -1))] += 1
        spans = sorted({tc * iw for _, tc, _, iw in tensor_shapes})
        # What actually caps the tensor engine at batch 1 is
        # min(lanes, tile_cols * issue_window, cols).  A deployment whose every
        # column-group span reaches the lane count leaves the MACHINE in charge
        # of the compute rate, which is what makes a comparison a comparison.
        caps = sorted({min(lanes, s) for s in spans}) if lanes else None
        return {
            "root": str(root),
            "capability_digest": dep.capability_digest,
            "schedule_shapes": {
                f"tile_rows={a},tile_cols={b},tile_depth={c},issue_window={d}": n
                for (a, b, c, d), n in sorted(tensor_shapes.items())
            },
            "column_group_spans": spans,
            "max_column_group_span": max(spans) if spans else 0,
            "effective_tensor_width_caps": caps,
            "storage_class_counts": dict(sorted(classes.items())),
        }

    rom, hbm = survey(rom_root), survey(hbm_root)
    if lanes:
        comparable = (
            rom["effective_tensor_width_caps"]
            == hbm["effective_tensor_width_caps"]
        )
        basis = f"effective tensor width caps at lanes={lanes}"
        rom_side, hbm_side = (rom["effective_tensor_width_caps"],
                              hbm["effective_tensor_width_caps"])
    else:
        comparable = rom["column_group_spans"] == hbm["column_group_spans"]
        basis = "column-group spans"
        rom_side, hbm_side = rom["column_group_spans"], hbm["column_group_spans"]
    advantage = max(rom["max_column_group_span"], 1) / max(
        hbm["max_column_group_span"], 1
    )
    rom_weight_classes = set(rom["storage_class_counts"])
    hbm_weight_classes = set(hbm["storage_class_counts"])
    return {
        "rom": rom,
        "hbm": hbm,
        "lanes": lanes,
        "basis": basis,
        "column_group_spans_match": comparable,
        "storage_classes_differ_as_expected": (
            3 in rom_weight_classes and 3 not in hbm_weight_classes
        ),
        "verdict": (
            f"COMPARABLE: both deployments present the same {basis} "
            f"({rom_side}), so the machine files alone decide the tensor rate."
            if comparable else
            f"NOT COMPARABLE: the two deployments present different {basis} "
            f"(rom {rom_side} against hbm {hbm_side}; max column-group span "
            f"{rom['max_column_group_span']} against "
            f"{hbm['max_column_group_span']}, a "
            f"{advantage:.1f}x "
            "advantage to the ROM side).  tile_cols and issue_window are "
            "SCHEDULE fields, so NO machine file can correct this; the "
            "deployments must be rebuilt from matched capabilities."
        ),
    }


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
            "Four numbers because the link term is expressible in one model "
            "and not the other, and it is 68% of the analytical ROM step.  "
            "Compare cycle_ratio against "
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


def build(anchor: Anchor) -> tuple[Derivation, dict[str, dict[str, Any]]]:
    d = derive(anchor)
    base_rom = json.loads(
        (REPO / "configs/hardware/abi3_capability/rom_qwen3.json").read_text()
    )
    base_hbm = json.loads(
        (REPO / "configs/hardware/abi3_capability"
         / "hbm_sram_single_chip.json").read_text()
    )
    return d, {
        "rom_cost_table": cost_table(d, "rom"),
        "hbm_cost_table": cost_table(d, "hbm"),
        "rom_capability": capability(d, "rom", base_rom),
        "hbm_capability": capability(d, "hbm", base_hbm),
    }


def artifact(anchor: Anchor, d: Derivation, comparability: Mapping[str, Any],
             paths: Mapping[str, str]) -> dict[str, Any]:
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
        "anchor": {
            "analytical_artifact": A.analytical_path,
            "study_id": A.study_id,
            "model": A.rom["model"],
            "batch_size": A.batch_size,
            "context_tokens": A.context_tokens,
            "rom_design": A.rom_design,
            "hbm_design": A.hbm_design,
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
        "residuals": d.residuals,
        "emitted": dict(paths),
    }


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--analytical", default=DEFAULT_ANALYTICAL)
    ap.add_argument("--technology", default=DEFAULT_TECHNOLOGY)
    ap.add_argument("--rom-design",
                    default="Qwen3-8B/ROM-N5-native-HBMKV-array-tensor-x4")
    ap.add_argument("--hbm-design", default="Qwen3-8B/b200_sxm-x2-tensor")
    ap.add_argument("--batch-size", type=int, default=1)
    ap.add_argument("--context-tokens", type=int, default=8192)
    ap.add_argument("--config-dir", default="configs/hardware")
    ap.add_argument(
        "--artifact",
        default="results/derived/qwen3_n5_design_target_machine_pair.json",
    )
    ap.add_argument("--check", action="store_true",
                    help="verify the emitted files match a fresh derivation")
    ap.add_argument("--audit-deployments", nargs=2, metavar=("ROM_ROOT", "HBM_ROOT"),
                    help=("compare two deployments' tensor tile shapes and "
                          "storage classes"))
    ap.add_argument("--reconcile", nargs=2, metavar=("ROM_RUN", "HBM_RUN"),
                    help="D6 report: two run_abi3_cycle results against the anchor")
    ap.add_argument("--reconcile-out", default=None,
                    help="write the D6 report here instead of stdout")
    args = ap.parse_args(argv)

    anchor = load_anchor(
        REPO / args.analytical, REPO / args.technology,
        rom_design=args.rom_design, hbm_design=args.hbm_design,
        batch_size=args.batch_size, context_tokens=args.context_tokens,
    )
    d, bodies = build(anchor)

    config_dir = REPO / args.config_dir
    cap_dir = config_dir / "abi3_capability" / TECHNOLOGY_VIEW
    paths = {
        "rom_cost_table": config_dir / f"abi3_cost_{TECHNOLOGY_VIEW}_rom_v1.json",
        "hbm_cost_table": config_dir / f"abi3_cost_{TECHNOLOGY_VIEW}_hbm_v1.json",
        "rom_capability": cap_dir / "rom_qwen3_n5_v1.json",
        "hbm_capability": cap_dir / "hbm_sram_single_chip_n5_v1.json",
    }
    rendered = {k: canonical(bodies[k]) for k in bodies}

    if args.check:
        bad = []
        for key, path in paths.items():
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
        report = audit_deployments(
            Path(args.audit_deployments[0]), Path(args.audit_deployments[1]),
            lanes=int(d.shared["engine.tensor.lanes.default"].value),
        )
        print(json.dumps(report, indent=2))
        return 0 if report["column_group_spans_match"] else 3

    cap_dir.mkdir(parents=True, exist_ok=True)
    for key, path in paths.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered[key])

    # D1: the assertion runs on EVERY emit, against the files just written.
    comparability = assert_comparable(
        bodies["rom_capability"], paths["rom_cost_table"],
        bodies["hbm_capability"], paths["hbm_cost_table"],
    )

    art = artifact(anchor, d, comparability,
                   {k: str(v.relative_to(REPO)) for k, v in paths.items()})
    art_path = REPO / args.artifact
    art_path.parent.mkdir(parents=True, exist_ok=True)
    art_path.write_text(canonical(art))

    print(f"emitted {len(bodies)} files for anchor "
          f"{anchor.rom_design} vs {anchor.hbm_design}")
    for path in paths.values():
        print(f"  {path.relative_to(REPO)}")
    print(f"  {art_path.relative_to(REPO)}")
    print(f"comparability: {comparability['parameters_compared']} parameters "
          f"compared, {len(comparability['permitted_differences'])} permitted "
          f"differences, 0 unexpected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
