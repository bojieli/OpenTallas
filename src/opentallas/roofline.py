"""Area-constrained, first-principles decode roofline.

Why this module exists
----------------------
``opentallas.analytical`` takes ``weight_capacity_bytes_per_device``,
``compute_roofs_ops_s_per_device`` and the bandwidths as *independent free
inputs*.  Nothing ties them to silicon area, so a profile can give a whole wafer
less compute than one GPU die without the model objecting.  It also has no
latency model for a distributed decode step, so the wafer-versus-array question
cannot be asked at all.

This module replaces the hardware side of that.  It keeps the model side --
``workload.weight_traffic``, ``workload.kv_traffic`` and
``operations.operation_inventory``, all measured from released checkpoints --
and derives every hardware quantity from **one primary input: silicon area**,
split across ROM array, compute, SRAM, interconnect, HBM PHY and overhead.
Capacity, bandwidth and compute roof are outputs of that split and of graded
technology densities.  They are never inputs.

The central overlap/serialisation assumption
--------------------------------------------
One decode step on the whole system costs::

    t_memory  = t_weight + t_kv          if weights and KV share one memory system
    t_memory  = max(t_weight, t_kv)      if they are physically separate arrays
    t_service = max(t_memory, t_compute)
    t_token   = t_service / stage_balance + t_link
    t_token  *= thermal_scale

and the four rules behind it, each of which is a modelling choice rather than a
derivation, are:

1. **Compute overlaps memory.**  Weight fetch and arithmetic are pipelined
   stages of one dataflow, so they combine with ``max``.  This is the ordinary
   roofline assumption.
2. **Weight traffic and KV traffic add when they share a memory system and take
   the max when they do not.**  On a GPU both come out of the same HBM
   channels, so they contend and add -- this is what makes a GPU
   weight-plus-KV bound.  On a ROM part the weights are in a mask-ROM array and
   the KV is in SRAM or in HBM; those are physically separate arrays with
   separate ports, so they overlap.  This single rule is most of the difference
   between the two architectures and it is stated here rather than buried in an
   efficiency factor.
3. **Hop and collective latency does not overlap anything.**  Decode is
   sequential across layers: layer *n+1* cannot start until layer *n*'s
   activation has arrived.  Inter-device latency is therefore added to the
   critical path at every batch size, including batch 1, where a pipelined
   array supplies no parallelism whatsoever.
4. **Per-user latency is the full serial traversal, and aggregate throughput is
   ``batch / per-user latency``.**  A pipelined array of N devices does not make
   one user's token faster; it only lets other users occupy the stages this
   user is not in.  Computing the service time on the *aggregate* resources and
   adding the hops is exactly the balanced-pipeline traversal, and it keeps the
   identity ``aggregate = batch x per_user_rate`` true by construction.

The ROM locality rule
---------------------
Mask-ROM weights are physically local to the array that holds them.  An expert
region that is not selected contributes neither read bandwidth nor stored bytes
to the step, so its read ports **cannot be borrowed** by the regions that are
selected.  The consequence, derived rather than assumed, is that the ROM
weight-read time is the *full-array sweep time*::

    t_weight_rom = stored_bytes / rom_read_bytes_s
                 = rom_capacity_density / rom_read_bandwidth_density

which is a pure technology constant: independent of model size, of batch, and
of expert coverage.  MoE sparsity on a ROM machine therefore converts into
*aggregate* throughput (more concurrent users swept per pass, via
``workload.expected_expert_coverage``) and not into lower per-token latency.
On an HBM machine the opposite holds: bandwidth is global, so sparsity reduces
the bytes fetched and directly reduces the step time.

(Whether one sweep can in fact serve the whole batch is the separate question
in "The batch-amortisation fork" below.  The batch-independence stated here is
the ``batched`` policy; under ``per_stream`` the sweep count is the batch.)

Compute is treated the other way round, and deliberately: a compute fabric is a
designed, multiplexable resource, and no one places a multiplier per stored
weight for a 900 GB checkpoint.  Compute therefore sees the full roof and gains
the full benefit of sparsity.  The asymmetry between the two is the point --
memory arrays have per-bank read ports inherently, compute arrays do not.

The batch-amortisation fork
---------------------------
There is a second, unresolved question underneath that, and this model does not
answer it -- it parameterises it and reports both answers:

* ``weight_amortization="batched"`` -- **ROM as storage with a separate MAC
  array**.  Weights are read out of the ROM into a compute fabric, so one sweep
  serves every member of the batch exactly as one HBM fetch does on a GPU.
  Weight-read time is independent of batch and aggregate throughput rises with
  it.
* ``weight_amortization="per_stream"`` -- **compute-in-ROM**, where a cell both
  stores its bits and performs the multiply for them.  A second concurrent
  stream then needs a second pass through the fabric, weight-read time scales
  linearly with batch, and **aggregate per-die throughput equals per-user
  throughput at every batch**.

These are different machines with different scaling laws.  The two are identical
at batch 1 -- which is why the Taalas HC1 anchor cannot distinguish them and why
the anchor must not be used to justify a high-batch claim.  Both are evaluated
and both are reported.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

from .operations import operation_inventory
from .schema import ModelProfile, ValidationError
from .workload import (
    expected_engaged_devices,
    kv_traffic,
    weight_traffic,
)


GRADES = ("measured", "published", "derived", "assumed")
BITS_PER_BYTE = 8.0
UM2_PER_MM2 = 1.0e6

WEIGHT_TRAFFIC_POLICIES = ("decode_streamed", "full_checkpoint")
WEIGHT_STORES = ("rom", "hbm", "sram")
KV_STORES = ("sram", "hbm")
PARALLELISMS = ("none", "pipeline", "tensor")
WEIGHT_AMORTIZATIONS = ("batched", "per_stream", "per_region")
#: Policies where the cell selects a partial product, so the multiply lives
#: in the array and there is no separate MAC block.
COMPUTE_IN_ROM_POLICIES = ("per_stream", "per_region")


# --------------------------------------------------------------------------
# graded values
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Graded:
    """A number with its evidence class and source.

    An ungraded input is the failure mode this program exists to prevent, so
    every technology primitive and every derived quantity carries one of these.
    ``derived`` values name the inputs they were computed from.
    """

    value: float
    grade: str
    source: str
    note: str = ""

    def __post_init__(self) -> None:
        if self.grade not in GRADES:
            raise ValidationError(
                f"grade must be one of {GRADES}, got {self.grade!r}"
            )
        if not str(self.source).strip():
            raise ValidationError("a graded value requires a non-empty source")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Graded":
        return cls(
            value=float(data["value"]),
            grade=str(data["grade"]),
            source=str(data["source"]),
            note=str(data.get("note", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _weakest_grade(grades: Iterable[str]) -> str:
    """The weakest evidence class present, which is what a derivation inherits."""

    worst = 0
    for grade in grades:
        worst = max(worst, GRADES.index(grade))
    return GRADES[worst]


def derived(
    value: float, inputs: Iterable[Graded], formula: str, note: str = ""
) -> Graded:
    """Build a ``derived`` value that inherits the weakest input grade.

    A quantity computed from an assumed input is not better evidenced than that
    input, so the grade floor propagates.  ``derived`` is only ever *stronger*
    than the inputs in the sense of being reproducible, never in evidence.
    """

    materialised = list(inputs)
    grade = _weakest_grade(item.grade for item in materialised)
    if grade != "assumed":
        grade = "derived"
    sources = " ; ".join(dict.fromkeys(item.source for item in materialised))
    return Graded(value=value, grade=grade, source=sources, note=f"{formula}. {note}".strip())


# --------------------------------------------------------------------------
# technology
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Technology:
    """Graded technology primitives plus the derivations built on them."""

    raw: Mapping[str, Any]
    efficiency_override: float | None = None

    # -- loading ----------------------------------------------------------

    @classmethod
    def load(cls, path: str | Path) -> "Technology":
        with Path(path).open(encoding="utf-8") as handle:
            return cls(raw=json.load(handle))

    def ideal(self) -> "Technology":
        """A copy with every efficiency derate set to 1.0.

        This is the pure-arithmetic roofline used by the A100 validation gate
        and reported alongside the achievable number in every study, so a reader
        can always separate the physics from the judgement about how much of it
        a real kernel keeps.
        """

        return replace(self, efficiency_override=1.0)

    # -- primitives -------------------------------------------------------

    def graded(self, *path: str) -> Graded:
        node: Any = self.raw
        for key in path:
            if key not in node:
                raise ValidationError(f"technology config has no {'.'.join(path)}")
            node = node[key]
        return Graded.from_dict(node)

    def efficiency(self, name: str) -> Graded:
        base = self.graded("efficiencies", name)
        if self.efficiency_override is None:
            return base
        return Graded(
            value=self.efficiency_override,
            grade="derived",
            source="ideal-roofline override",
            note=f"{name} derate forced to {self.efficiency_override} for the ideal roofline",
        )

    def node_names(self) -> tuple[str, ...]:
        return tuple(self.raw["nodes"])

    # -- derived densities ------------------------------------------------

    def sram_bits_per_mm2(self, node: str) -> Graded:
        cell = self.graded("nodes", node, "sram_hd_bitcell_um2")
        eff = self.graded("sram", "array_efficiency")
        value = UM2_PER_MM2 / (cell.value / eff.value)
        return derived(
            value,
            (cell, eff),
            "1e6 um2/mm2 / (bitcell_um2 / array_efficiency)",
            f"{node} 6T high-density SRAM array capacity density in bits/mm2",
        )

    def rom_bits_per_mm2(self, node: str) -> Graded:
        cell = self.graded("nodes", node, "sram_hd_bitcell_um2")
        ratio = self.graded("rom", "cell_to_sram_cell_area_ratio")
        eff = self.graded("rom", "array_efficiency")
        value = UM2_PER_MM2 / (cell.value * ratio.value / eff.value)
        return derived(
            value,
            (cell, ratio, eff),
            "1e6 um2/mm2 / (sram_bitcell_um2 * rom_cell_ratio / rom_array_efficiency)",
            f"{node} mask-ROM array capacity density in bits/mm2",
        )

    def rom_read_bytes_s_per_mm2(self, node: str) -> Graded:
        anchor = self.raw["rom"]["read_bandwidth_anchor"]
        area = Graded.from_dict(anchor["macro_area_mm2"])
        ops = Graded.from_dict(anchor["operations_s"])
        per_weight = Graded.from_dict(anchor["operations_per_weight"])
        bits = Graded.from_dict(anchor["weight_bits"])
        anchor_cell = Graded.from_dict(anchor["anchor_node_sram_hd_bitcell_um2"])
        target_cell = self.graded("nodes", node, "sram_hd_bitcell_um2")
        anchor_density = (
            ops.value / per_weight.value * bits.value / BITS_PER_BYTE
        ) / area.value
        scale = anchor_cell.value / target_cell.value
        return derived(
            anchor_density * scale,
            (area, ops, per_weight, bits, anchor_cell, target_cell),
            "(anchor_ops_s / ops_per_weight * weight_bits / 8 / macro_area) "
            "* (anchor_bitcell_um2 / target_bitcell_um2)",
            f"{node} mask-ROM array read-bandwidth density in bytes/s/mm2; "
            f"anchor density {anchor_density:.3e} B/s/mm2 scaled by {scale:.3f}x",
        )

    def sram_read_bytes_s_per_mm2(self, node: str) -> Graded:
        anchor = self.raw["sram"]["read_bandwidth_anchor"]
        rate = Graded.from_dict(anchor["aggregate_sram_read_bytes_s"])
        area = Graded.from_dict(anchor["die_area_mm2"])
        anchor_cell = self.graded("nodes", anchor["node"], "sram_hd_bitcell_um2")
        target_cell = self.graded("nodes", node, "sram_hd_bitcell_um2")
        scale = anchor_cell.value / target_cell.value
        return derived(
            rate.value / area.value * scale,
            (rate, area, anchor_cell, target_cell),
            "(anchor_sram_read_bytes_s / anchor_die_area_mm2) "
            "* (anchor_bitcell_um2 / target_bitcell_um2)",
            f"{node} SRAM array read-bandwidth density in bytes/s/mm2; the anchor "
            "rate is charged against WHOLE-die area and then applied only to array "
            "area, which is conservative",
        )

    def compute_ops_s_per_mm2(self, node: str, canonical_format: str) -> Graded:
        anchor_name = self.raw["compute"]["anchor_part"]
        anchor = self.raw["reference_parts"][anchor_name]
        anchor_node = anchor["node"]
        area = Graded.from_dict(anchor["die_area_mm2"])
        anchor_scale = self.graded("nodes", anchor_node, "logic_density_vs_n7")
        target_scale = self.graded("nodes", node, "logic_density_vs_n7")
        roofs = self.raw["compute"]["format_roofs_ops_s"]
        if canonical_format == "w4a8":
            low = Graded.from_dict(roofs["fp8"])
            high = Graded.from_dict(roofs["fp4"])
            value = math.sqrt(low.value * high.value) / area.value
            value *= target_scale.value / anchor_scale.value
            return derived(
                value,
                (low, high, area, anchor_scale, target_scale),
                "sqrt(fp8_roof * fp4_roof) / anchor_die_area_mm2 "
                "* (target_logic_density / anchor_logic_density)",
                "4-bit-weight by 8-bit-activation datapath, bracketed below by the "
                "published w8a8 roof and above by the published w4a4 roof on the "
                "same die; both endpoints are reported separately",
            )
        if canonical_format not in roofs:
            raise ValidationError(
                f"no published anchor roof for canonical format {canonical_format!r}"
            )
        roof = Graded.from_dict(roofs[canonical_format])
        value = roof.value / area.value * target_scale.value / anchor_scale.value
        return derived(
            value,
            (roof, area, anchor_scale, target_scale),
            "anchor_format_roof_ops_s / anchor_die_area_mm2 "
            "* (target_logic_density / anchor_logic_density)",
            f"{node} {canonical_format} compute density in ops/s/mm2, derived from "
            f"the published {anchor_name} dense roof and die area",
        )

    # -- lookups ----------------------------------------------------------

    def canonical_format(self, model_format: str) -> str:
        mapping = self.raw["compute"]["model_format_map"]
        if model_format not in mapping:
            raise ValidationError(
                f"technology config has no canonical mapping for model format "
                f"{model_format!r}"
            )
        return str(mapping[model_format])

    def link(self, name: str) -> tuple[Graded, Graded]:
        return (
            self.graded("links", name, "hop_latency_s"),
            self.graded("links", name, "bytes_s"),
        )

    def hbm(self, generation: str, field_name: str) -> Graded:
        return self.graded("hbm", generation, field_name)

    def mac_energy_j_per_op(self, canonical_format: str) -> Graded:
        table = self.raw["energy"]["mac_energy_j_per_op"]
        if canonical_format not in table:
            raise ValidationError(
                f"no MAC energy for canonical format {canonical_format!r}"
            )
        return Graded.from_dict(table[canonical_format])

    def reference_part(self, name: str) -> Mapping[str, Any]:
        parts = self.raw["reference_parts"]
        if name not in parts:
            raise ValidationError(f"unknown reference part {name!r}")
        return parts[name]

    def inputs_by_grade(self) -> dict[str, list[str]]:
        """Every graded leaf in the config, bucketed by evidence class.

        The study report prints this so an ``assumed`` input cannot enter the
        result without appearing in the output.
        """

        found: dict[str, list[str]] = {grade: [] for grade in GRADES}

        def walk(node: Any, path: tuple[str, ...]) -> None:
            if isinstance(node, Mapping):
                if "grade" in node and "source" in node and "value" in node:
                    found[str(node["grade"])].append(".".join(path))
                    return
                for key, value in node.items():
                    walk(value, path + (str(key),))
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    walk(value, path + (str(index),))

        walk(self.raw, ())
        return {grade: sorted(paths) for grade, paths in found.items()}


# --------------------------------------------------------------------------
# area allocation
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class AreaSplit:
    """How one device's silicon is spent.  This is the model's primary input.

    ``balanced_area_split`` solves it from a workload -- ROM sized to the stored
    weights, SRAM sized to the resident KV, fixed fractions for overhead and
    interconnect, HBM PHY sized by stack count, and compute taking whatever
    remains.  An explicit split can also be supplied directly; the evaluation
    path is identical either way.
    """

    total_mm2: float
    rom_mm2: float
    compute_mm2: float
    sram_mm2: float
    interconnect_mm2: float
    hbm_phy_mm2: float
    overhead_mm2: float
    policy: str
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.total_mm2 <= 0:
            raise ValidationError("total area must be positive")
        for name in (
            "rom_mm2",
            "compute_mm2",
            "sram_mm2",
            "interconnect_mm2",
            "hbm_phy_mm2",
            "overhead_mm2",
        ):
            if getattr(self, name) < 0:
                raise ValidationError(f"{name} cannot be negative")

    @property
    def allocated_mm2(self) -> float:
        return (
            self.rom_mm2
            + self.compute_mm2
            + self.sram_mm2
            + self.interconnect_mm2
            + self.hbm_phy_mm2
            + self.overhead_mm2
        )

    @property
    def slack_mm2(self) -> float:
        return self.total_mm2 - self.allocated_mm2

    def fractions(self) -> dict[str, float]:
        return {
            "rom": self.rom_mm2 / self.total_mm2,
            "compute": self.compute_mm2 / self.total_mm2,
            "sram": self.sram_mm2 / self.total_mm2,
            "interconnect": self.interconnect_mm2 / self.total_mm2,
            "hbm_phy": self.hbm_phy_mm2 / self.total_mm2,
            "overhead": self.overhead_mm2 / self.total_mm2,
            "slack": self.slack_mm2 / self.total_mm2,
        }

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["allocated_mm2"] = self.allocated_mm2
        data["slack_mm2"] = self.slack_mm2
        data["fractions"] = self.fractions()
        data["reasons"] = list(self.reasons)
        return data


def max_hbm_stacks_per_device(
    technology: Technology, *, generation: str, die_area_mm2: float
) -> int:
    """How many HBM stacks a die of this area can actually attach.

    HBM bandwidth is a die-edge property, not an area property.  The pitch
    ceiling is charged at the utilisation shipping GPUs actually achieve, so a
    modelled ROM part is never allowed a more aggressive beachfront than NVIDIA
    takes on the same die size.  A direct consequence is that at equal area both
    sides of the comparison have the *same* KV bandwidth ceiling: the ROM part's
    advantage is that it does not also have to spend that bandwidth on weights.
    """

    pitch = technology.hbm(generation, "stack_beachfront_mm").value
    utilisation = technology.hbm(generation, "max_beachfront_utilization").value
    perimeter = 4.0 * math.sqrt(die_area_mm2)
    return max(0, int(perimeter * utilisation // pitch))


def balanced_area_split(
    technology: Technology,
    *,
    node: str,
    total_mm2: float,
    weight_store: str,
    kv_store: str,
    stored_weight_bytes: float,
    resident_kv_bytes: float,
    hbm_stacks: int = 0,
    hbm_generation: str = "hbm3e",
    weight_amortization: str = "batched",
) -> AreaSplit:
    """Solve the split from the workload rather than guessing fractions.

    ROM area and SRAM area are *demanded* by the model and by the resident KV;
    overhead and interconnect are fixed graded fractions; HBM PHY follows the
    stack count; compute takes the remainder.  A negative remainder is returned
    as a reason rather than silently clamped, because a design that cannot fit
    its own weights is the result, not an error.

    **The floorplan depends on the amortisation policy, because the policies are
    different machines and not one machine with different arithmetic.**

    ``batched`` is ROM as storage feeding a separate MAC array.  Its ROM cell
    holds bits and nothing else, and the compute block is a real MAC array that
    takes whatever area is left.

    ``per_stream`` and ``per_region`` are compute-in-ROM.  There **is no MAC
    array**: the cell selects a pre-computed partial product, so the multiply
    lives in the array itself.  Two things follow, and both were missing when
    this function ignored the policy.  The cell is larger, because it carries a
    pass transistor and the product-line wiring on top of its via programming.
    And the compute block shrinks to the pre-computation logic that forms every
    product of one activation with the weight alphabet -- a couple of percent of
    the die, not the remainder of it.

    Handing a compute-in-ROM design the leftover area as a MAC array, as this
    function did before, gives it arithmetic it does not have and takes silicon
    from the array that is its whole point.
    """

    overhead_fraction = technology.graded("floorplan", "overhead_area_fraction")
    interconnect_fraction = technology.graded(
        "floorplan", "interconnect_area_fraction"
    )
    reasons: list[str] = []

    compute_in_rom = weight_amortization in COMPUTE_IN_ROM_POLICIES
    rom_mm2 = 0.0
    cell_multiplier = 1.0
    if weight_store == "rom":
        density = technology.rom_bits_per_mm2(node).value / BITS_PER_BYTE
        if compute_in_rom:
            cell_multiplier = technology.graded(
                "rom", "cim_cell_area_multiplier"
            ).value
        rom_mm2 = stored_weight_bytes * cell_multiplier / density

    sram_mm2 = 0.0
    if kv_store == "sram":
        density = technology.sram_bits_per_mm2(node).value / BITS_PER_BYTE
        sram_mm2 = resident_kv_bytes / density

    hbm_phy_mm2 = 0.0
    if hbm_stacks:
        phy = technology.hbm(hbm_generation, "phy_area_mm2_per_stack")
        hbm_phy_mm2 = hbm_stacks * phy.value

    overhead_mm2 = overhead_fraction.value * total_mm2
    interconnect_mm2 = interconnect_fraction.value * total_mm2
    fixed = rom_mm2 + sram_mm2 + hbm_phy_mm2 + overhead_mm2 + interconnect_mm2
    if compute_in_rom and weight_store == "rom":
        # No MAC array.  The compute block is only the pre-computation logic;
        # whatever area is left over belongs to the ROM array, because more
        # array is more parameters and more parallel selection.
        precompute_fraction = technology.graded(
            "rom", "cim_precompute_area_fraction"
        ).value
        compute_mm2 = precompute_fraction * total_mm2
        leftover = total_mm2 - (fixed + compute_mm2)
        if leftover > 0:
            # Spare area becomes SRAM, not more ROM.  The array is sized by the
            # weights it holds; making it larger than that would buy read
            # bandwidth for bits that do not exist, which is how an earlier
            # version of this function modelled the anchor as twice as fast as
            # the shipping part.  Taalas describes exactly this split -- a mask
            # ROM recall fabric beside an SRAM recall fabric for KV and adapters
            # -- so the spare silicon has a real job.
            sram_mm2 += leftover
        elif leftover < 0:
            reasons.append(
                f"AREA: compute-in-ROM needs ROM {rom_mm2:,.0f} + SRAM "
                f"{sram_mm2:,.0f} + HBM PHY {hbm_phy_mm2:,.0f} + pre-compute "
                f"{compute_mm2:,.0f} + overhead {overhead_mm2:,.0f} + "
                f"interconnect {interconnect_mm2:,.0f} mm2, over {total_mm2:,.0f}"
            )
        return AreaSplit(
            total_mm2=total_mm2,
            rom_mm2=rom_mm2,
            compute_mm2=compute_mm2,
            sram_mm2=sram_mm2,
            interconnect_mm2=interconnect_mm2,
            hbm_phy_mm2=hbm_phy_mm2,
            overhead_mm2=overhead_mm2,
            policy=(
                f"compute-in-ROM: cells {cell_multiplier:g}x a storage-only bit, "
                "no MAC array, pre-compute block only, all remaining area to the "
                "array"
            ),
            reasons=tuple(reasons),
        )
    compute_mm2 = total_mm2 - fixed
    if compute_mm2 <= 0:
        reasons.append(
            f"AREA: ROM {rom_mm2:,.0f} + SRAM {sram_mm2:,.0f} + HBM PHY "
            f"{hbm_phy_mm2:,.0f} + overhead {overhead_mm2:,.0f} + interconnect "
            f"{interconnect_mm2:,.0f} mm2 leaves no compute area in {total_mm2:,.0f} mm2"
        )
        compute_mm2 = 0.0
    return AreaSplit(
        total_mm2=total_mm2,
        rom_mm2=rom_mm2,
        compute_mm2=compute_mm2,
        sram_mm2=sram_mm2,
        interconnect_mm2=interconnect_mm2,
        hbm_phy_mm2=hbm_phy_mm2,
        overhead_mm2=overhead_mm2,
        policy="balanced: ROM sized to stored weights, SRAM sized to resident KV, "
        "graded fixed fractions for overhead and interconnect, compute takes the rest",
        reasons=tuple(reasons),
    )


# --------------------------------------------------------------------------
# topology
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Topology:
    """Where the devices are and how a token gets through them."""

    kind: str
    device_count: int
    parallelism: str
    link: str
    on_wafer_regions: int = 1

    def __post_init__(self) -> None:
        if self.device_count < 1:
            raise ValidationError("device_count must be at least 1")
        if self.parallelism not in PARALLELISMS:
            raise ValidationError(f"parallelism must be one of {PARALLELISMS}")
        if self.kind not in ("single_chip", "array", "wafer"):
            raise ValidationError("topology kind must be single_chip, array or wafer")
        if self.kind == "single_chip" and self.device_count != 1:
            raise ValidationError("single_chip topology must have one device")

    @property
    def partitions(self) -> int:
        """Independently placed pieces the model is cut into.

        A wafer is one manufactured device but is still stitched from reticle
        fields, so its hop count comes from the fields it spans rather than from
        ``device_count``.
        """

        if self.kind == "wafer":
            return max(1, self.on_wafer_regions)
        return self.device_count

    def hop_events(self, num_layers: int) -> tuple[float, str]:
        """Serial inter-partition events on one token's critical path.

        Pipeline parallelism crosses one boundary per partition boundary, so
        N-1 hops per token regardless of batch.  Tensor parallelism needs two
        all-reduces per layer, every token, *however few partitions it spans* --
        which is why it is roughly fifteen times more expensive than pipelining
        and why it is only available on a fabric with sub-microsecond hops.
        """

        partitions = self.partitions
        if partitions <= 1 or self.parallelism == "none":
            return 0.0, "no inter-partition event on one token's critical path"
        if self.parallelism == "tensor":
            return (
                2.0 * num_layers,
                "two all-reduces per layer per token (tensor parallel)",
            )
        return (
            float(partitions - 1),
            "one hop per partition boundary per token (pipeline parallel)",
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------
# device budget: everything derived from area
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class DeviceBudget:
    """System-level resources derived from an area split and graded densities.

    Every field here is an *output*.  The inputs were the area, the split, the
    node and the technology table.
    """

    name: str
    node: str
    topology: Topology
    split: AreaSplit
    weight_store: str
    kv_store: str
    weight_amortization: str
    silicon_area_mm2_per_device: float
    silicon_area_mm2_total: float

    weight_capacity_bytes: float
    kv_capacity_bytes: float
    weight_read_bytes_s: float
    kv_read_bytes_s: float
    compute_ops_s: Mapping[str, float]
    shared_memory_path: bool
    cooling_limit_w: float
    hbm_stacks: int
    hbm_generation: str
    native_formats: tuple[str, ...]
    emulated_formats: Mapping[str, str]
    provenance: Mapping[str, Graded]
    reasons: tuple[str, ...] = ()
    published_reference: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "node": self.node,
            "topology": self.topology.to_dict(),
            "area_split_per_device": self.split.to_dict(),
            "weight_store": self.weight_store,
            "kv_store": self.kv_store,
            "weight_amortization": self.weight_amortization,
            "silicon_area_mm2_per_device": self.silicon_area_mm2_per_device,
            "silicon_area_mm2_total": self.silicon_area_mm2_total,
            "weight_capacity_bytes": self.weight_capacity_bytes,
            "kv_capacity_bytes": self.kv_capacity_bytes,
            "weight_read_bytes_s": self.weight_read_bytes_s,
            "kv_read_bytes_s": self.kv_read_bytes_s,
            "compute_ops_s": dict(self.compute_ops_s),
            "shared_memory_path": self.shared_memory_path,
            "cooling_limit_w": self.cooling_limit_w,
            "hbm_stacks": self.hbm_stacks,
            "hbm_generation": self.hbm_generation,
            "native_formats": list(self.native_formats),
            "emulated_formats": dict(self.emulated_formats),
            "published_reference": self.published_reference,
            "provenance": {
                key: value.to_dict() for key, value in self.provenance.items()
            },
            "reasons": list(self.reasons),
        }


def _canonical_formats(technology: Technology) -> tuple[str, ...]:
    mapping = technology.raw["compute"]["model_format_map"]
    return tuple(sorted(set(mapping.values())))


def rom_device_budget(
    technology: Technology,
    *,
    name: str,
    node: str,
    area_mm2_per_device: float,
    topology: Topology,
    stored_weight_bytes: float,
    resident_kv_bytes: float,
    kv_store: str = "sram",
    hbm_stacks: int = 0,
    hbm_generation: str = "hbm3e",
    weight_amortization: str = "batched",
    split: AreaSplit | None = None,
) -> DeviceBudget:
    """Derive a mask-ROM design's resources from its area.

    ``stored_weight_bytes`` and ``resident_kv_bytes`` are *system* totals; the
    split is solved per device against the per-device share of each.
    """

    if weight_amortization not in WEIGHT_AMORTIZATIONS:
        raise ValidationError(
            f"weight_amortization must be one of {WEIGHT_AMORTIZATIONS}"
        )
    devices = topology.device_count
    total_area = area_mm2_per_device * devices
    if split is None:
        split = balanced_area_split(
            technology,
            node=node,
            total_mm2=area_mm2_per_device,
            weight_store="rom",
            kv_store=kv_store,
            stored_weight_bytes=stored_weight_bytes / devices,
            resident_kv_bytes=resident_kv_bytes / devices,
            hbm_stacks=hbm_stacks,
            hbm_generation=hbm_generation,
            weight_amortization=weight_amortization,
        )

    rom_capacity_density = technology.rom_bits_per_mm2(node)
    rom_bandwidth_density = technology.rom_read_bytes_s_per_mm2(node)
    sram_capacity_density = technology.sram_bits_per_mm2(node)
    sram_bandwidth_density = technology.sram_read_bytes_s_per_mm2(node)
    rom_eff = technology.efficiency("rom_read_bandwidth")
    sram_eff = technology.efficiency("sram_read_bandwidth")
    hbm_bw_eff = technology.efficiency("hbm_bandwidth")
    hbm_cap_eff = technology.efficiency("hbm_capacity")
    cooling = technology.graded("thermal", "cooling_limit_w_per_mm2")

    weight_capacity = (
        split.rom_mm2 * devices * rom_capacity_density.value / BITS_PER_BYTE
    )
    weight_read = (
        split.rom_mm2 * devices * rom_bandwidth_density.value * rom_eff.value
    )

    reasons: list[str] = list(split.reasons)
    if kv_store == "sram":
        kv_capacity = (
            split.sram_mm2 * devices * sram_capacity_density.value / BITS_PER_BYTE
        )
        kv_read = (
            split.sram_mm2 * devices * sram_bandwidth_density.value * sram_eff.value
        )
    else:
        stack_capacity = technology.hbm(hbm_generation, "stack_capacity_bytes")
        stack_bandwidth = technology.hbm(hbm_generation, "stack_bandwidth_bytes_s")
        beachfront = technology.hbm(hbm_generation, "stack_beachfront_mm")
        kv_capacity = hbm_stacks * devices * stack_capacity.value * hbm_cap_eff.value
        kv_read = hbm_stacks * devices * stack_bandwidth.value * hbm_bw_eff.value
        limit = max_hbm_stacks_per_device(
            technology,
            generation=hbm_generation,
            die_area_mm2=area_mm2_per_device,
        )
        if hbm_stacks > limit:
            utilisation = technology.hbm(
                hbm_generation, "max_beachfront_utilization"
            ).value
            reasons.append(
                f"BEACHFRONT: {hbm_stacks} stacks per device exceed the {limit} a "
                f"{area_mm2_per_device:,.0f} mm2 die can attach at {beachfront.value:.0f} mm "
                f"pitch and {utilisation:.0%} edge utilisation"
            )

    compute: dict[str, float] = {}
    provenance: dict[str, Graded] = {
        "rom_capacity_density_bits_mm2": rom_capacity_density,
        "rom_read_bandwidth_density_bytes_s_mm2": rom_bandwidth_density,
        "sram_capacity_density_bits_mm2": sram_capacity_density,
        "sram_read_bandwidth_density_bytes_s_mm2": sram_bandwidth_density,
        "cooling_limit_w_per_mm2": cooling,
        "compute_efficiency": technology.efficiency("compute"),
        "rom_read_bandwidth_efficiency": rom_eff,
        "sram_read_bandwidth_efficiency": sram_eff,
    }
    for canonical in _canonical_formats(technology):
        density = technology.compute_ops_s_per_mm2(node, canonical)
        compute[canonical] = split.compute_mm2 * devices * density.value
        provenance[f"compute_density_ops_s_mm2[{canonical}]"] = density

    # The full-array sweep floor is a pure technology constant; recording it
    # here makes it auditable independently of any particular model.
    sweep_floor = (
        rom_capacity_density.value
        / BITS_PER_BYTE
        / (rom_bandwidth_density.value * rom_eff.value)
    )
    provenance["rom_full_array_sweep_time_s"] = derived(
        sweep_floor,
        (rom_capacity_density, rom_bandwidth_density, rom_eff),
        "rom_capacity_density_bytes_mm2 / (rom_read_bandwidth_density * "
        "rom_read_efficiency)",
        "time to read every stored weight once; independent of model size, batch "
        "and expert coverage, so it is a hard per-token ceiling for a ROM design",
    )

    return DeviceBudget(
        name=name,
        node=node,
        topology=topology,
        split=split,
        weight_store="rom",
        kv_store=kv_store,
        weight_amortization=weight_amortization,
        silicon_area_mm2_per_device=area_mm2_per_device,
        silicon_area_mm2_total=total_area,
        weight_capacity_bytes=weight_capacity,
        kv_capacity_bytes=kv_capacity,
        weight_read_bytes_s=weight_read,
        kv_read_bytes_s=kv_read,
        compute_ops_s=compute,
        shared_memory_path=False,
        cooling_limit_w=cooling.value * total_area,
        hbm_stacks=hbm_stacks,
        hbm_generation=hbm_generation if kv_store == "hbm" else "",
        native_formats=_canonical_formats(technology),
        emulated_formats={},
        provenance=provenance,
        reasons=tuple(reasons),
    )


def gpu_device_budget(
    technology: Technology,
    *,
    part: str,
    topology: Topology,
    name: str | None = None,
) -> DeviceBudget:
    """A published GPU, stated at its published area.

    Nothing is derived from area here -- the part exists and its bandwidth,
    capacity and roofs are published.  What the model *does* do is state the
    silicon area on this side of the comparison too, and cross-check the
    published aggregate HBM figures against stacks times per-stack values.
    """

    spec = technology.reference_part(part)
    node = str(spec["node"])
    area = Graded.from_dict(spec["die_area_mm2"])
    devices = topology.device_count
    hbm_generation = str(spec["hbm_generation"])
    stacks = Graded.from_dict(spec["hbm_stacks"])
    capacity = Graded.from_dict(spec["hbm_capacity_bytes"])
    bandwidth = Graded.from_dict(spec["hbm_bandwidth_bytes_s"])
    power = Graded.from_dict(spec["power_w"])
    hbm_bw_eff = technology.efficiency("hbm_bandwidth")
    hbm_cap_eff = technology.efficiency("hbm_capacity")

    reasons: list[str] = []
    stack_capacity = technology.hbm(hbm_generation, "stack_capacity_bytes")
    stack_bandwidth = technology.hbm(hbm_generation, "stack_bandwidth_bytes_s")
    derived_capacity = stacks.value * stack_capacity.value
    derived_bandwidth = stacks.value * stack_bandwidth.value
    capacity_error = abs(derived_capacity - capacity.value) / capacity.value
    bandwidth_error = abs(derived_bandwidth - bandwidth.value) / bandwidth.value

    published_roofs = spec.get("published_format_roofs_ops_s")
    compute: dict[str, float] = {}
    provenance: dict[str, Graded] = {
        "die_area_mm2": area,
        "hbm_capacity_bytes": capacity,
        "hbm_bandwidth_bytes_s": bandwidth,
        "hbm_stacks": stacks,
        "power_w": power,
        "hbm_bandwidth_efficiency": hbm_bw_eff,
        "hbm_capacity_efficiency": hbm_cap_eff,
        "compute_efficiency": technology.efficiency("compute"),
        "hbm_capacity_stack_cross_check_relative_error": Graded(
            value=capacity_error,
            grade="derived",
            source=f"{capacity.source} ; {stack_capacity.source}",
            note="published aggregate HBM capacity against stacks x per-stack capacity",
        ),
        "hbm_bandwidth_stack_cross_check_relative_error": Graded(
            value=bandwidth_error,
            grade="derived",
            source=f"{bandwidth.source} ; {stack_bandwidth.source}",
            note="published aggregate HBM bandwidth against stacks x per-stack bandwidth",
        ),
    }
    for canonical in _canonical_formats(technology):
        if published_roofs and canonical in published_roofs:
            roof = Graded.from_dict(published_roofs[canonical])
            compute[canonical] = devices * roof.value
            provenance[f"compute_roof_ops_s[{canonical}]"] = roof
            continue
        if (
            canonical == "w4a8"
            and published_roofs
            and "fp8" in published_roofs
            and "fp4" in published_roofs
        ):
            # Interpolate this part's OWN published endpoints rather than
            # importing the anchor part's density, which can otherwise place a
            # w4a8 roof below the same part's published w8a8 roof.
            low = Graded.from_dict(published_roofs["fp8"])
            high = Graded.from_dict(published_roofs["fp4"])
            roof = derived(
                math.sqrt(low.value * high.value),
                (low, high),
                "sqrt(published_fp8_roof * published_fp4_roof)",
                "4-bit-weight by 8-bit-activation datapath bracketed by this "
                "part's own published endpoints",
            )
            compute[canonical] = devices * roof.value
            provenance[f"compute_roof_ops_s[{canonical}]"] = roof
            continue
        density = technology.compute_ops_s_per_mm2(node, canonical)
        compute[canonical] = devices * area.value * density.value
        provenance[f"compute_density_ops_s_mm2[{canonical}]"] = density

    split = AreaSplit(
        total_mm2=area.value,
        rom_mm2=0.0,
        compute_mm2=area.value,
        sram_mm2=0.0,
        interconnect_mm2=0.0,
        hbm_phy_mm2=0.0,
        overhead_mm2=0.0,
        policy="published part: die area is stated for the iso-area comparison, "
        "not allocated by this model; capacity, bandwidth and roofs are published",
    )
    return DeviceBudget(
        name=name or f"{part}-x{devices}",
        node=node,
        topology=topology,
        split=split,
        weight_store="hbm",
        kv_store="hbm",
        weight_amortization="batched",
        silicon_area_mm2_per_device=area.value,
        silicon_area_mm2_total=area.value * devices,
        weight_capacity_bytes=devices * capacity.value * hbm_cap_eff.value,
        kv_capacity_bytes=devices * capacity.value * hbm_cap_eff.value,
        weight_read_bytes_s=devices * bandwidth.value * hbm_bw_eff.value,
        kv_read_bytes_s=devices * bandwidth.value * hbm_bw_eff.value,
        compute_ops_s=compute,
        shared_memory_path=True,
        cooling_limit_w=devices * power.value,
        hbm_stacks=int(stacks.value * devices),
        hbm_generation=hbm_generation,
        native_formats=tuple(spec.get("native_formats", ())),
        emulated_formats=dict(spec.get("emulated_formats", {})),
        provenance=provenance,
        reasons=tuple(reasons),
        published_reference=part,
    )


# --------------------------------------------------------------------------
# the roofline
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class RooflineStep:
    """One evaluated operating point.

    ``component_times_s`` are the four terms of the roofline before the overlap
    rule is applied; ``step_time_s`` is after it.  ``binding_constraint`` names
    the term that actually sets the answer, so no result can be read without
    knowing why it came out that way.
    """

    design: str
    model: str
    context_tokens: int
    batch_size: int
    feasible: bool
    reasons: tuple[str, ...]
    step_time_s: float
    per_user_tokens_s: float
    aggregate_tokens_s: float
    binding_constraint: str
    component_times_s: Mapping[str, float]
    silicon_area_mm2: float
    power_w: float
    thermal_scale: float
    metrics: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["reasons"] = list(self.reasons)
        data["component_times_s"] = dict(self.component_times_s)
        data["metrics"] = dict(self.metrics)
        return data


def _scaled_operations(
    model: ModelProfile,
    technology: Technology,
    context_tokens: int,
    batch_size: float,
    execution_format: str | None = None,
) -> dict[str, float]:
    """Decode operations for the step, bucketed by canonical compute format.

    Routed (expert) operations are scaled by the batch rather than by expert
    coverage: every routed token does its own ``experts_per_token`` worth of
    arithmetic no matter how many *distinct* experts the batch collectively
    touches.  Coverage governs bytes and engaged area, not operation count.

    ``execution_format`` exists because a model-specific ASIC freezes one
    datapath at manufacture.  A part that stores 3-to-6-bit weights does not
    execute the checkpoint's released BF16 arithmetic and must not be priced at
    the BF16 roof.  The remap is therefore a property of the hardware, and it is
    always reported in the result.

    ``fp32`` is deliberately exempt from the remap.  The full-precision terms in
    a released model -- index-score reduction, normalisation accumulation --
    exist because they need the range, and a narrow weight datapath does not
    make them narrow.  A GPU with no low-precision unit is handled the other
    way, through the architecture's own native/emulated format table, so that
    the emulation stays visible as an architecture property.
    """

    inventory = operation_inventory(model, context_tokens)
    scaled: dict[str, float] = {}
    for model_format, operations in inventory.operations_by_format.items():
        canonical = technology.canonical_format(model_format)
        if execution_format is not None and canonical != "fp32":
            canonical = execution_format
        scaled[canonical] = scaled.get(canonical, 0.0) + operations * batch_size
    return scaled


def _compute_time(
    operations: Mapping[str, float],
    budget: DeviceBudget,
    technology: Technology,
) -> tuple[float, dict[str, float], list[str]]:
    """Serialise format-specific work through the roofs that can execute it."""

    efficiency = technology.efficiency("compute").value
    times: dict[str, float] = {}
    reasons: list[str] = []
    for canonical, count in operations.items():
        if count <= 0:
            continue
        execution = canonical
        if budget.native_formats and canonical not in budget.native_formats:
            execution = budget.emulated_formats.get(canonical, "")
            if not execution:
                reasons.append(
                    f"FORMAT: {budget.name} has no native or emulated path for "
                    f"{canonical!r}"
                )
                continue
        roof = budget.compute_ops_s.get(execution, 0.0)
        if roof <= 0:
            reasons.append(f"COMPUTE: {budget.name} has a zero {execution!r} roof")
            continue
        times[canonical] = count / (roof * efficiency)
    return sum(times.values()), times, reasons


def evaluate(
    budget: DeviceBudget,
    model: ModelProfile,
    *,
    context_tokens: int,
    batch_size: int,
    technology: Technology,
    weight_bits_per_parameter: float | None = None,
    weight_traffic_policy: str = "decode_streamed",
    execution_format: str | None = None,
    measured_expert_coverage: float | None = None,
) -> RooflineStep:
    """Evaluate one decode step against an area-derived resource budget."""

    if weight_traffic_policy not in WEIGHT_TRAFFIC_POLICIES:
        raise ValidationError(
            f"weight_traffic_policy must be one of {WEIGHT_TRAFFIC_POLICIES}"
        )
    if batch_size < 1:
        raise ValidationError("batch_size must be at least 1")
    if context_tokens > model.max_context_tokens:
        raise ValidationError(
            f"context {context_tokens} exceeds {model.name} maximum "
            f"{model.max_context_tokens}"
        )

    reasons: list[str] = list(budget.reasons)

    # -- representation ---------------------------------------------------
    # A mask ROM freezes the stored representation at manufacture, so it is a
    # design variable rather than an inherited constant.  Rescaling the whole
    # checkpoint uniformly keeps the deployment story auditable.
    if weight_bits_per_parameter is None:
        representation_scale = 1.0
        stored_weight_bytes = model.checkpoint_bytes
    else:
        stored_weight_bytes = (
            model.total_parameters * weight_bits_per_parameter / BITS_PER_BYTE
        )
        representation_scale = stored_weight_bytes / model.checkpoint_bytes

    # -- model-side accounting (reused, not reimplemented) ----------------
    kv = kv_traffic(model, context_tokens)
    traffic = weight_traffic(
        model, batch_size, measured_coverage=measured_expert_coverage
    )
    coverage = traffic.routed_expert_coverage
    if weight_traffic_policy == "full_checkpoint":
        engaged_weight_bytes = stored_weight_bytes
    else:
        engaged_weight_bytes = traffic.total_bytes * representation_scale
    operations = _scaled_operations(
        model, technology, context_tokens, float(batch_size), execution_format
    )

    resident_kv_bytes = kv.storage_bytes_per_user * batch_size
    kv_transfer_bytes = (kv.read_bytes + kv.write_bytes) * batch_size

    # -- capacity ---------------------------------------------------------
    if stored_weight_bytes > budget.weight_capacity_bytes + 1.0:
        reasons.append(
            f"CAPACITY: stored weights {stored_weight_bytes:,.0f} B exceed weight "
            f"capacity {budget.weight_capacity_bytes:,.0f} B"
        )
    if budget.shared_memory_path:
        remaining = budget.kv_capacity_bytes - stored_weight_bytes
    else:
        remaining = budget.kv_capacity_bytes
    if resident_kv_bytes > remaining + 1.0:
        reasons.append(
            f"CAPACITY: resident KV {resident_kv_bytes:,.0f} B exceeds available KV "
            f"capacity {max(0.0, remaining):,.0f} B at batch {batch_size}"
        )
    max_resident_users = (
        int(max(0.0, remaining) // kv.storage_bytes_per_user)
        if kv.storage_bytes_per_user > 0
        else 0
    )

    # -- weight read ------------------------------------------------------
    devices = budget.topology.device_count
    region_sweeps = 1.0
    if budget.weight_store == "rom":
        # ROM locality: an unselected region's read ports cannot be borrowed, so
        # the engaged bandwidth is the engaged fraction of the array's.  The
        # engaged bytes then take exactly the full-array sweep time.
        engaged_fraction = (
            engaged_weight_bytes / stored_weight_bytes
            if stored_weight_bytes > 0
            else 1.0
        )
        effective_weight_bw = budget.weight_read_bytes_s * engaged_fraction
        weight_time = (
            engaged_weight_bytes / effective_weight_bw
            if effective_weight_bw > 0
            else math.inf
        )
        if budget.weight_amortization == "per_region":
            # Compute-in-ROM with a per-region activation port.  Compute stays
            # bound to the weight, so nothing is amortised the way a fetched
            # weight is -- but two tokens that select *disjoint* experts drive
            # disjoint regions and proceed at the same time.  What serialises is
            # only the tokens landing on one region.
            #
            # With B tokens each selecting k of N experts, B*k expert
            # activations spread over the N*coverage regions the batch engages,
            # so the mean engaged region sees B*k / (N*coverage) of them and the
            # sweep is that many passes deep.  At B=1 that is exactly one pass,
            # which is why this and per_stream and batched all agree at batch 1
            # and the Taalas anchor cannot separate them.
            #
            # A dense model has one region by construction, so every token lands
            # on it and this reduces to per_stream -- correctly, because a dense
            # model has no disjointness to exploit.  The load-balance derate
            # carries the gap between the mean region and the busiest one.
            experts_per_token = max(1, int(model.experts_per_token or 1))
            num_experts = max(1, int(model.num_experts or 1))
            engaged_regions = max(1.0, num_experts * coverage)
            passes = (batch_size * experts_per_token) / engaged_regions
            # The imbalance derate only means something when there is more than
            # one region to be imbalanced across.  A dense model has exactly one,
            # so every token lands on it and this reduces to per_stream exactly.
            if engaged_regions > 1.0:
                balance = technology.efficiency("expert_load_balance").value
                passes = passes / max(balance, 1e-9)
            # A per-region fabric can never be worse than a global broadcast --
            # in the limit every token lands on one region, which is per_stream.
            passes = min(max(1.0, passes), float(batch_size))
            region_sweeps = passes

            per_stream_traffic = weight_traffic(model, 1)
            per_stream_bytes = per_stream_traffic.total_bytes * representation_scale
            if weight_traffic_policy == "full_checkpoint":
                per_stream_bytes = stored_weight_bytes
            engaged_weight_bytes = per_stream_bytes * passes
            engaged_fraction = (
                per_stream_bytes / stored_weight_bytes
                if stored_weight_bytes > 0
                else 1.0
            )
            effective_weight_bw = budget.weight_read_bytes_s * engaged_fraction
            weight_time = (
                engaged_weight_bytes / effective_weight_bw
                if effective_weight_bw > 0
                else math.inf
            )
        elif budget.weight_amortization == "per_stream":
            # Compute-in-ROM: a cell both stores its bits and multiplies them,
            # so a second concurrent stream needs a second pass through the
            # fabric.  Every batch member pays its own sweep, aggregate
            # throughput per die collapses onto per-user throughput, and the
            # per-stream expert set is what each pass engages rather than the
            # batch's union.
            per_stream_traffic = weight_traffic(model, 1)
            per_stream_bytes = per_stream_traffic.total_bytes * representation_scale
            if weight_traffic_policy == "full_checkpoint":
                per_stream_bytes = stored_weight_bytes
            engaged_weight_bytes = per_stream_bytes * batch_size
            engaged_fraction = (
                per_stream_bytes / stored_weight_bytes
                if stored_weight_bytes > 0
                else 1.0
            )
            effective_weight_bw = budget.weight_read_bytes_s * engaged_fraction
            weight_time = (
                engaged_weight_bytes / effective_weight_bw
                if effective_weight_bw > 0
                else math.inf
            )
    else:
        # Global bandwidth: only the engaged bytes are fetched, and for an
        # expert-parallel cluster only the devices holding a selected expert
        # contribute their share of it.
        engaged_fraction = 1.0
        per_device_bw = budget.weight_read_bytes_s / max(1, devices)
        dense_bytes = model.dense_weight_bytes * representation_scale
        routed_bytes = model.routed_weight_bytes * representation_scale * coverage
        if weight_traffic_policy == "full_checkpoint":
            dense_bytes = engaged_weight_bytes
            routed_bytes = 0.0
        engaged_devices = expected_engaged_devices(
            devices, traffic.distinct_experts_per_layer
        )
        weight_time = dense_bytes / max(budget.weight_read_bytes_s, 1e-30)
        if routed_bytes > 0:
            weight_time += routed_bytes / max(engaged_devices * per_device_bw, 1e-30)
        effective_weight_bw = (
            engaged_weight_bytes / weight_time if weight_time > 0 else math.inf
        )

    # -- KV read ----------------------------------------------------------
    kv_time = (
        kv_transfer_bytes / budget.kv_read_bytes_s
        if budget.kv_read_bytes_s > 0
        else math.inf
    )

    # -- compute ----------------------------------------------------------
    compute_time, compute_by_format, compute_reasons = _compute_time(
        operations, budget, technology
    )
    reasons.extend(compute_reasons)

    # -- link -------------------------------------------------------------
    hops, hop_semantics = budget.topology.hop_events(model.num_layers)
    hop_latency, link_bytes_s = technology.link(budget.topology.link)
    if budget.topology.parallelism == "tensor":
        # Reduction payload in fp32, result broadcast in bf16, per the DeepSeek
        # block convention already used by opentallas.analytical.
        payload_bytes = batch_size * model.hidden_size * (4 + 2)
    else:
        payload_bytes = batch_size * model.hidden_size * 2
    link_time = hops * (hop_latency.value + payload_bytes / link_bytes_s.value)

    # -- the roofline combination ----------------------------------------
    if budget.shared_memory_path:
        memory_time = weight_time + kv_time
        overlap_rule = "weights and KV share one memory system: their times add"
    else:
        memory_time = max(weight_time, kv_time)
        overlap_rule = "weights and KV are physically separate arrays: their times overlap"
    if (
        budget.weight_store == "rom"
        and budget.weight_amortization in COMPUTE_IN_ROM_POLICIES
    ):
        # In a compute-in-ROM fabric the multiply *is* the sweep: every cell the
        # pass selects contributes one product, so there is no arithmetic that
        # can proceed while the array is being walked and none that continues
        # after it.  Putting compute in a max() against the weight read would
        # model two independent units, which is exactly the machine this policy
        # says does not exist.  The KV path is genuinely separate and still
        # overlaps.
        service_time = max(weight_time, kv_time)
        overlap_rule = (
            "compute-in-ROM: the multiply is the array sweep, so weight read and "
            "compute are one term; KV is a separate array and overlaps"
        )
    else:
        service_time = max(memory_time, compute_time)
    balance = technology.efficiency("stage_balance").value
    apply_balance = devices > 1 and budget.topology.parallelism != "none"
    if apply_balance:
        service_time /= balance
    raw_step_time = service_time + link_time

    # -- power and thermal ------------------------------------------------
    energy_j = 0.0
    if budget.weight_store == "rom":
        energy_j += (
            engaged_weight_bytes
            * technology.graded("energy", "rom_read_j_per_byte").value
        )
    else:
        energy_j += (
            engaged_weight_bytes * technology.graded("energy", "hbm_j_per_byte").value
        )
    if budget.kv_store == "sram":
        energy_j += (
            kv_transfer_bytes
            * technology.graded("energy", "sram_read_j_per_byte").value
        )
    else:
        energy_j += (
            kv_transfer_bytes * technology.graded("energy", "hbm_j_per_byte").value
        )
    for canonical, count in operations.items():
        energy_j += count * technology.mac_energy_j_per_op(canonical).value
    dynamic_power = energy_j / max(raw_step_time, 1e-30)
    thermal_scale = max(1.0, dynamic_power / max(budget.cooling_limit_w, 1e-30))
    step_time = raw_step_time * thermal_scale
    power = energy_j / max(step_time, 1e-30)

    fused_compute = (
        budget.weight_store == "rom"
        and budget.weight_amortization in COMPUTE_IN_ROM_POLICIES
    )
    component_times = {
        "weight_read": weight_time,
        "kv_read": kv_time,
        # In a compute-in-ROM fabric the arithmetic is the sweep, so reporting a
        # separate compute time would name a component that cannot bind and
        # would break the invariant that the step is at least its largest part.
        # The MACs still happen; they take exactly as long as the walk.
        "compute": weight_time if fused_compute else compute_time,
        "link_latency": link_time,
    }
    if reasons:
        binding = "capacity_or_format"
        per_user = 0.0
        aggregate = 0.0
    else:
        if thermal_scale > 1.0 + 1e-12:
            binding = "thermal"
        else:
            binding = max(component_times, key=lambda key: component_times[key])
        per_user = 1.0 / step_time
        aggregate = batch_size * per_user

    metrics: dict[str, Any] = {
        "overlap_rule": overlap_rule,
        "latency_rule": (
            "hop and collective latency is added to the critical path, never "
            "overlapped; per-user latency is the full serial traversal and "
            "aggregate = batch x per-user rate"
        ),
        "hop_events_per_token": hops,
        "hop_semantics": hop_semantics,
        "hop_latency_s": hop_latency.value,
        "link": budget.topology.link,
        "link_payload_bytes_per_event": float(payload_bytes),
        "stored_weight_bytes": stored_weight_bytes,
        "representation_scale_vs_checkpoint": representation_scale,
        "weight_traffic_policy": weight_traffic_policy,
        "weight_amortization": budget.weight_amortization,
        "execution_format": execution_format or "checkpoint-declared",
        "engaged_weight_bytes": engaged_weight_bytes,
        "engaged_weight_fraction": engaged_fraction,
        "effective_weight_read_bytes_s": effective_weight_bw,
        "peak_weight_read_bytes_s": budget.weight_read_bytes_s,
        "expert_coverage": coverage,
        "distinct_experts_per_layer": traffic.distinct_experts_per_layer,
        "engaged_devices": (
            expected_engaged_devices(devices, traffic.distinct_experts_per_layer)
            if budget.weight_store != "rom"
            else float(devices)
        ),
        "kv_read_bytes_per_user_token": kv.read_bytes,
        "kv_write_bytes_per_user_token": kv.write_bytes,
        "kv_storage_bytes_per_user": kv.storage_bytes_per_user,
        "kv_transfer_bytes_per_step": kv_transfer_bytes,
        "resident_kv_bytes": resident_kv_bytes,
        "max_resident_users": float(max_resident_users),
        "weight_capacity_bytes": budget.weight_capacity_bytes,
        "kv_capacity_bytes": budget.kv_capacity_bytes,
        "operations_by_canonical_format": dict(operations),
        "compute_times_s_by_format": compute_by_format,
        "compute_roofs_ops_s": dict(budget.compute_ops_s),
        "memory_time_s": memory_time,
        "service_time_s": service_time,
        "stage_balance_applied": apply_balance,
        "raw_step_time_before_thermal_s": raw_step_time,
        "energy_j_per_step": energy_j,
        "dynamic_power_w_before_throttle": dynamic_power,
        "cooling_limit_w": budget.cooling_limit_w,
        "weight_to_kv_read_ratio": (
            engaged_weight_bytes / (kv.read_bytes * batch_size)
            if kv.read_bytes > 0
            else math.inf
        ),
        "silicon_area_mm2_per_device": budget.silicon_area_mm2_per_device,
        "device_count": float(devices),
    }
    if budget.weight_store == "rom":
        if budget.weight_amortization == "per_stream":
            sweeps = float(batch_size)
        elif budget.weight_amortization == "per_region":
            # The busiest expert region's queue depth, not the batch: disjoint
            # regions run together and only co-located tokens serialise.
            sweeps = float(region_sweeps)
        else:
            sweeps = 1.0
        metrics["rom_sweeps_per_step"] = float(sweeps)
        metrics["rom_full_array_sweep_time_s"] = (
            sweeps * stored_weight_bytes / budget.weight_read_bytes_s
            if budget.weight_read_bytes_s > 0
            else math.inf
        )
        metrics["rom_sweep_ceiling_tokens_s"] = (
            1.0 / metrics["rom_full_array_sweep_time_s"]
            if metrics["rom_full_array_sweep_time_s"] > 0
            else math.inf
        )

    return RooflineStep(
        design=budget.name,
        model=model.name,
        context_tokens=context_tokens,
        batch_size=batch_size,
        feasible=not reasons,
        reasons=tuple(reasons),
        step_time_s=step_time,
        per_user_tokens_s=per_user,
        aggregate_tokens_s=aggregate,
        binding_constraint=binding,
        component_times_s=component_times,
        silicon_area_mm2=budget.silicon_area_mm2_total,
        power_w=power,
        thermal_scale=thermal_scale,
        metrics=metrics,
    )


# --------------------------------------------------------------------------
# topology crossover
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class LatencyCrossover:
    """Where hop latency stops being a design cost and becomes a wall.

    ``viable_tokens_s`` is the per-user rate at which the hops alone consume
    ``budget_fraction`` of the whole token budget.  Above it the topology is
    still arithmetically possible but the interconnect, not the silicon, is
    setting the answer.
    """

    topology: str
    device_count: int
    parallelism: str
    link: str
    hop_events_per_token: float
    hop_latency_s: float
    link_latency_s_per_token: float
    budget_fraction: float
    viable_tokens_s: float
    hard_ceiling_tokens_s: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def latency_crossover(
    topology: Topology,
    model: ModelProfile,
    technology: Technology,
    *,
    budget_fraction: float = 0.10,
    batch_size: int = 1,
) -> LatencyCrossover:
    """Report the per-user rate at which a topology's hops bind.

    This is reported rather than one topology being asserted, because the
    wafer-versus-array question has no single answer: it is decided by the
    target per-user decode rate against the hop count.
    """

    hops, _ = topology.hop_events(model.num_layers)
    hop_latency, link_bytes_s = technology.link(topology.link)
    if topology.parallelism == "tensor":
        payload_bytes = batch_size * model.hidden_size * (4 + 2)
    else:
        payload_bytes = batch_size * model.hidden_size * 2
    per_token = hops * (hop_latency.value + payload_bytes / link_bytes_s.value)
    viable = budget_fraction / per_token if per_token > 0 else math.inf
    ceiling = 1.0 / per_token if per_token > 0 else math.inf
    return LatencyCrossover(
        topology=topology.kind,
        device_count=topology.device_count,
        parallelism=topology.parallelism,
        link=topology.link,
        hop_events_per_token=hops,
        hop_latency_s=hop_latency.value,
        link_latency_s_per_token=per_token,
        budget_fraction=budget_fraction,
        viable_tokens_s=viable,
        hard_ceiling_tokens_s=ceiling,
    )


# --------------------------------------------------------------------------
# validation anchors
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class AnchorCheck:
    name: str
    published_value: float
    modelled_value: float
    ratio: float
    tolerance: float
    passed: bool
    detail: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["detail"] = dict(self.detail)
        return data


def taalas_hc1_anchor(
    technology: Technology,
    model: ModelProfile,
    *,
    tolerance: float = 2.0,
    context_tokens: int | None = None,
    weight_bits_per_parameter: float | None = None,
) -> AnchorCheck:
    """Reproduce the shipping Taalas HC1: 8B on 815 mm2 at N6, ~17,000 tok/s/user.

    A methodology that predicts 2,000 or 200,000 for a part that exists is
    wrong however internally consistent it is.  This is a gate, not a datapoint
    to be averaged in, and it is deliberately evaluated with the *achievable*
    derates rather than the ideal roofline because 17,000 is a product figure.
    """

    spec = technology.reference_part("taalas_hc1")
    area = Graded.from_dict(spec["die_area_mm2"])
    published = Graded.from_dict(spec["published_tokens_s_per_user"])
    bits = Graded.from_dict(spec["weight_bits_per_parameter"])
    batch = int(Graded.from_dict(spec["batch_size"]).value)
    if context_tokens is None:
        context_tokens = int(
            Graded.from_dict(spec["input_tokens"]).value
            + Graded.from_dict(spec["output_tokens"]).value
        )
    if weight_bits_per_parameter is None:
        weight_bits_per_parameter = bits.value

    stored = model.total_parameters * weight_bits_per_parameter / BITS_PER_BYTE
    resident_kv = kv_traffic(model, context_tokens).storage_bytes_per_user * batch
    topology = Topology(
        kind="single_chip", device_count=1, parallelism="none", link=str(spec["link"])
    )
    budget = rom_device_budget(
        technology,
        name="Taalas-HC1-reconstruction",
        node=str(spec["node"]),
        area_mm2_per_device=area.value,
        topology=topology,
        stored_weight_bytes=stored,
        resident_kv_bytes=resident_kv,
        kv_store=str(spec["kv_store"]),
        # Read raw: Graded coerces to float and this is a categorical choice.
        # It is still graded in the config, and still an assumption -- Taalas
        # publishes no microarchitecture, and the whole floorplan now turns on it.
        weight_amortization=str(spec["weight_amortization"]["value"]),
    )
    step = evaluate(
        budget,
        model,
        context_tokens=context_tokens,
        batch_size=batch,
        technology=technology,
        weight_bits_per_parameter=weight_bits_per_parameter,
        execution_format=str(spec["execution_format_name"]),
    )
    ratio = step.per_user_tokens_s / published.value if published.value else math.inf

    # Back-derive what each density would have to be for the model to land
    # exactly on the shipping part. Reporting the shortfall as a falsifiable
    # statement about a technology input is the point of the gate; tuning the
    # input until the anchor is hit would destroy the gate's value.
    budget_s = 1.0 / published.value
    rom_density = budget.provenance["rom_read_bandwidth_density_bytes_s_mm2"]
    rom_eff = budget.provenance["rom_read_bandwidth_efficiency"]
    compute_density = budget.provenance[
        f"compute_density_ops_s_mm2[{spec['execution_format_name']}]"
    ]
    compute_eff = budget.provenance["compute_efficiency"]
    required_rom_density = (
        stored / (budget.split.rom_mm2 * budget_s * rom_eff.value)
        if budget.split.rom_mm2 > 0
        else math.inf
    )
    total_ops = sum(
        step.metrics["operations_by_canonical_format"].values()
    )
    required_compute_density = (
        total_ops / (budget.split.compute_mm2 * budget_s * compute_eff.value)
        if budget.split.compute_mm2 > 0
        else math.inf
    )
    requirements = {
        "token_budget_s_at_published_rate": budget_s,
        "derived_rom_read_bandwidth_density_bytes_s_mm2": rom_density.value,
        "required_rom_read_bandwidth_density_bytes_s_mm2": required_rom_density,
        "rom_density_shortfall_x": required_rom_density / rom_density.value,
        "derived_compute_density_ops_s_mm2": compute_density.value,
        "required_compute_density_ops_s_mm2": required_compute_density,
        "compute_density_shortfall_x": (
            required_compute_density / compute_density.value
        ),
    }

    return AnchorCheck(
        name="taalas_hc1_per_user_tokens_s",
        published_value=published.value,
        modelled_value=step.per_user_tokens_s,
        ratio=ratio,
        tolerance=tolerance,
        passed=(1.0 / tolerance) <= ratio <= tolerance,
        detail={
            "node": spec["node"],
            "die_area_mm2": area.value,
            "context_tokens": context_tokens,
            "batch_size": batch,
            "weight_bits_per_parameter": weight_bits_per_parameter,
            "execution_format": spec["execution_format_name"],
            "binding_constraint": step.binding_constraint,
            "component_times_s": dict(step.component_times_s),
            "area_split_mm2": budget.split.to_dict(),
            "back_derived_requirements": requirements,
            "step": step.to_dict(),
            "budget": budget.to_dict(),
        },
    )


def a100_weight_bound_anchor(
    technology: Technology,
    model: ModelProfile,
    *,
    weight_bits_per_parameter: float = 8.0,
    tolerance: float = 0.01,
) -> AnchorCheck:
    """Pure arithmetic: published HBM bandwidth divided by checkpoint bytes.

    An A100 80GB serving an 8B model at batch 1 is weight-bound.  The expected
    answer is ``2,039 GB/s / 8.03 GB = 253.9 tok/s`` at FP8, and any deviation
    is a bug rather than a modelling choice, so this runs on the *ideal*
    roofline with every derate at 1.0.
    """

    ideal = technology.ideal()
    topology = Topology(
        kind="single_chip", device_count=1, parallelism="none", link="none"
    )
    budget = gpu_device_budget(
        ideal, part="a100_sxm_80gb", topology=topology, name="A100-80GB-x1"
    )
    step = evaluate(
        budget,
        model,
        context_tokens=2048,
        batch_size=1,
        technology=ideal,
        weight_bits_per_parameter=weight_bits_per_parameter,
        weight_traffic_policy="full_checkpoint",
    )
    weight_time = step.component_times_s["weight_read"]
    modelled = 1.0 / weight_time
    stored = model.total_parameters * weight_bits_per_parameter / BITS_PER_BYTE
    bandwidth = Graded.from_dict(
        technology.reference_part("a100_sxm_80gb")["hbm_bandwidth_bytes_s"]
    ).value
    expected = bandwidth / stored
    ratio = modelled / expected
    return AnchorCheck(
        name="a100_weight_bound_tokens_s",
        published_value=expected,
        modelled_value=modelled,
        ratio=ratio,
        tolerance=tolerance,
        passed=abs(ratio - 1.0) <= tolerance,
        detail={
            "hbm_bandwidth_bytes_s": bandwidth,
            "stored_weight_bytes": stored,
            "weight_bits_per_parameter": weight_bits_per_parameter,
            "die_area_mm2": budget.silicon_area_mm2_total,
            "binding_constraint": step.binding_constraint,
            "component_times_s": dict(step.component_times_s),
            "full_step_per_user_tokens_s": step.per_user_tokens_s,
            "step": step.to_dict(),
        },
    )
