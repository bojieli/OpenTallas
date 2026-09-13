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
    t_service = max(t_memory, t_compute)          on the machine's AGGREGATE
    t_token   = token_slots * t_service / stage_balance + t_link
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
4. **Per-user latency and aggregate throughput are separate quantities and are
   both reported.**  The service time above is computed on the machine's
   *aggregate* resources -- every byte of array bandwidth, every operation of
   compute roof.  That is the right denominator only for partitions that are
   all working on the same token at the same instant, which is what tensor
   parallelism is.  A token under pipeline parallelism is served by one stage's
   silicon at a time and must visit every stage in turn, so::

       t_per_user = token_slots x t_service_on_the_whole_machine + t_link

   where ``token_slots = partitions / tensor_group``.  The two factors in a
   pipeline cancel exactly -- each of N stages holds ``1/N`` of the weights and
   reads them at ``1/N`` of the bandwidth -- so **adding devices under pipeline
   parallelism buys aggregate throughput and buys one user nothing**, and the
   answer is the same as one device holding the whole model at one device's
   bandwidth.  Tensor parallelism is different in kind: ``token_slots`` is one,
   the whole machine is on the token, and the price is two all-reduces per
   layer, charged in ``t_link``.

   Aggregate throughput is then the same serial path with **every slot
   occupied**: ``aggregate = fill_users / t_per_user`` where ``fill_users`` is
   ``max(batch, token_slots)``, capped by the users whose KV the machine can
   actually hold.  ``aggregate = batch x per_user_rate`` is therefore true only
   when the machine has at least as many concurrent users as slots; below that
   the surplus slots idle and what the machine delivers at the requested
   concurrency is reported separately as ``delivered_tokens_s``.  Fill and
   drain are not charged: decode is a continuous stream of steps and the
   pipeline is assumed to be in steady state, which flatters a deep pipeline by
   at most one traversal per request.

   **This rule was the largest known defect in the model.**  Until it was fixed
   the model charged a pipeline's service time on the aggregate view and its
   hops on the latency view, reporting a balanced ``S``-stage pipeline as ``S``
   times faster per user than it is.  Every point now carries
   ``per_user_tokens_s_throughput_view`` -- the number the defect produced --
   so the size of this correction stays separable from every other one.

The fabric model
----------------
A cluster is not one link class and a token's serial depth is not its partition
count.  Both mistakes were in this model and both decided results.

* **Two link classes, from published domain sizes.**  Partitions inside one
  high-bandwidth domain -- an 8-GPU NVSwitch baseboard, or one wafer's stitched
  mesh -- talk over ``Topology.intra_link``; everything past the domain edge
  goes over ``Topology.link``, an order of magnitude slower in latency and more
  than that in per-device bandwidth.  With ``intra_domain_size = 1`` the model
  reduces exactly to the single-link behaviour it replaced.
* **A collective is priced by the published cost model for its fabric.**  On a
  switch it is ``2 lg p`` traversals in the fabric's own radix (Thakur,
  Rabenseifner & Gropp 2005), which inside a single all-to-all tier is 2
  regardless of rank count.  On a mesh it is ``1.1 x`` the mesh diameter, which
  is what Cerebras measured on their own wafer (Rocki et al., SC20).  The
  bandwidth term carries the ``(p-1)/p`` factor of the bandwidth-optimal
  all-reduce, so a 2-way collective is cheaper than a 672-way one.
* **A token cannot cross more stage boundaries than the model has layers.**
  672 partitions do not make 671 pipeline stages of a 61-layer model.  Under
  rule 4 the surplus partitions still contribute their bandwidth, but nothing
  on the token's path waits for them, so they add no serial event.

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

These are different machines with different scaling laws and different
floorplans.  Their *sweep-count terms* coincide at batch 1, but their cell area,
pre-compute reservation, capacity and rate need not.  A batch-1 anchor can test
those physical consequences; it cannot establish how either machine scales at
high batch.  Both are evaluated and both are reported.
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
    hbm_resident_weight_bytes,
    kv_traffic,
    weight_traffic,
)


GRADES = ("measured", "executed", "published", "derived", "assumed")
"""Evidence classes, ordered strongest to weakest.

The order is load-bearing: ``_weakest_grade`` takes the largest index, so a
derivation inherits the weakest evidence that went into it.

``executed`` is the class this program mostly lives in and it was missing until
`configs/hardware/technology.json` named it: **we ran it, in this repository,
and the artifact holding the numbers is committed.** It is deliberately
distinct from ``measured``, which means fabricated silicon reported in a
peer-reviewed venue -- almost nothing here is that. Its absence was pushing
executed values into ``measured`` (too strong) or ``published`` (the wrong
category), and this file rejected the grade outright, which would have crashed
the study the first time a config entry used it.

It sits above ``published`` because a number obtained by running the released
artefact is first-hand evidence about that artefact, where a vendor figure is a
claim about it. This program has twice found implementation-derived constants
wrong -- DeepSeek's 583-byte KV entry and the sparse-index threshold -- while
the executed counts held.
"""
BITS_PER_BYTE = 8.0
UM2_PER_MM2 = 1.0e6

CAPACITY_TOLERANCE_BYTES = 1.0
"""One byte of slack on every capacity comparison, and the SAME byte on all of
them.

Capacities are solved from areas through a chain of float multiplications, so a
design sized to hold exactly one session's KV lands a fraction of a byte short
of it -- 1,207,959,551.9999998 B against 1,207,959,552.0 B on the three-reticle
Qwen machine.  The feasibility tests have always carried this tolerance.
``max_resident_users`` did not, so it floored to zero on precisely those
designs, and because zero is falsy the pipeline-fill cap that reads it was
skipped there too: the machine was declared feasible for one session and then
published an aggregate rate for as many sessions as it had pipeline stages.
Both the tests and the count now read this one constant, so they cannot
disagree about whether a session fits."""

WEIGHT_TRAFFIC_POLICIES = ("decode_streamed", "full_checkpoint")
WEIGHT_STORES = ("rom", "hbm", "sram")
KV_STORES = ("sram", "hbm")
PARALLELISMS = ("none", "pipeline", "tensor", "hybrid")
LINK_FABRICS = ("switched", "mesh")
MESH_ALLREDUCE_DIAMETER_FACTOR = 1.1
"""An all-reduce on a 2-D mesh costs about 1.1 times the mesh diameter.

Cerebras measured this on their own wafer: *"The single cycle-per-hop latency
of the interconnect allows us to implement the AllReduce operation in a cycle
count only about 10% greater than the diameter of the system"* (Rocki et al.,
`Fast Stencil-Code Computation on a Wafer-Scale Processor`, SC20,
arXiv:2010.03660).  It is the one number in the collective model that comes
from a measurement rather than from an algorithm, and it is on the ROM side.

**It is also the optimistic end of a measured band, and it has no sweep.**
Rocki's 1.1x is a *centre-rooted* collective: reduce along rows to the middle
columns, down them to a central core, then broadcast back, so the path is about
one diameter.  The collective Cerebras' own SDK ships and that Luczynski et al.
measured on a CS-2 is *corner-rooted* X-Y -- reduce along X to column 0, along Y
to PE(0,0), broadcast back -- whose path is about **2x** the diameter, and their
whole contribution is that the vendor library is up to 3.27x off optimal
(`Near-Optimal Wafer-Scale Reduce`, HPDC 2024, doi 10.1145/3625549.3658693).  So
this factor is 1.1 for a hand-written kernel and ~2.0 for the shipped one, a
1.8x range that would move the ROM side as much as the hop latency it
multiplies.  It is not swept here because it is a single module constant pinned
by a test; instead the 1.8x is folded into the top of the stated range of
BOTH wafer-fabric entries -- ``links.on_wafer.hop_latency_s`` at N7 and
``links.on_wafer_n5.hop_latency_s`` at N5 -- and both notes say so.
Naming it is the point: it is the second-largest unswept quantity on the ROM
side of this comparison.
"""
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
# occupancy statistics: the busiest bin, not the average one
# --------------------------------------------------------------------------
#
# Two places in this model used to divide work by the *mean* number of engaged
# units when the wall-clock is set by the *busiest* one.  A sweep that has to
# wait for the deepest queue is not the mean queue deep, and an expert-parallel
# fetch that has to wait for the most loaded device is not the mean device's
# share.  Both are the same statistic -- the expected maximum bin load -- and
# both are computed here, once.


def _binomial_max_bin_load(bins: int, trials: int, p: float) -> float:
    """``E[max]`` over ``bins`` bins whose loads are ``Binomial(trials, p)``.

    Each bin is marked by a given draw with probability ``p``, independently
    across draws, so one bin's load is exactly ``Binomial(trials, p)``.  Bins
    are weakly negatively correlated (a draw that marks one bin cannot mark it
    twice), and treating them as independent for the maximum is the standard
    approximation::

        P(max >= L) = 1 - (1 - P(Bin(trials, p) >= L))^bins
        E[max]      = sum_{L>=1} P(max >= L)

    ``tests/test_roofline.py`` checks this against a 4,000-trial Monte Carlo
    that draws ``k`` distinct experts per token; it agrees to within 2% for
    every batch from 1 to 256 at both 256 and 384 experts, and returns 1.0 at
    batch 1 where the true answer is exactly 1.
    """

    if trials <= 0 or p <= 0.0:
        return 0.0
    if p >= 1.0:
        return float(trials)
    total = 0.0
    # pmf[0] = P(X = 0); survival tracks P(X >= L) as L advances.
    pmf = math.exp(trials * math.log1p(-p))
    survival = 1.0
    for level in range(1, trials + 1):
        survival -= pmf
        if survival <= 0.0:
            break
        # 1 - (1 - survival)^bins, evaluated without cancellation.
        reached = (
            1.0
            if survival >= 1.0
            else -math.expm1(bins * math.log1p(-survival))
        )
        total += reached
        if reached < 1e-12 and level > trials * p + 1.0:
            break
        pmf *= (trials - level + 1) / level * p / (1.0 - p)
    return total


def expected_max_bin_load(bins: int, draws: float, bins_per_draw: float = 1.0) -> float:
    """Expected load of the BUSIEST of ``bins`` bins.

    ``draws`` independent draws each mark ``bins_per_draw`` distinct bins.  A
    fractional ``draws`` -- which is what an expected count of distinct experts
    is -- is interpolated between the two integers that bracket it.
    """

    bins = max(1, int(bins))
    if bins == 1:
        return max(0.0, float(draws))
    if draws <= 0:
        return 0.0
    p = min(1.0, max(0.0, float(bins_per_draw) / bins))
    low = int(math.floor(draws))
    frac = draws - low
    value = _binomial_max_bin_load(bins, low, p)
    if frac > 0.0:
        upper = _binomial_max_bin_load(bins, low + 1, p)
        value += frac * (upper - value)
    return value


def expected_max_region_load(
    num_regions: int, batch_size: int, regions_per_token: int
) -> float:
    """Sweep depth of the busiest expert region, in passes.

    This replaces ``batch * k / (N * coverage)``, which is the load of the
    *average* engaged region.  The array cannot finish until its deepest queue
    has drained, so the mean understates the sweep by 1.6x to 2.7x over the
    batches this study covers -- most severely between batch 4 and batch 32,
    exactly where the per-region argument is made.

    Never below 1.0: one token still costs one pass.  Never above ``batch``:
    the worst case is every token landing on one region, which is a global
    broadcast.
    """

    depth = expected_max_bin_load(num_regions, float(batch_size), float(regions_per_token))
    return min(max(1.0, depth), float(max(1, batch_size)))


def effective_engaged_devices(device_count: int, distinct_experts: float) -> float:
    """Devices an expert-parallel routed fetch can *actually* draw on.

    ``workload.expected_engaged_devices`` returns the expected number of devices
    holding at least one selected expert.  That is the right answer to a
    question this model is not asking: the routed bytes do not finish when the
    average engaged device finishes, they finish when the busiest one does.  A
    device holding twice the mean share takes twice as long, and every other
    device is idle for the second half of it.

    The effective device count is therefore ``distinct_experts / E[max experts
    on one device]``, which is at most the engaged count and at least 1.

    ``workload.py`` is shared with ``opentallas.analytical`` and is not changed;
    this function overrides it for the roofline only, and both numbers are
    reported in every step's metrics so the correction is visible rather than
    silent.
    """

    device_count = max(1, int(device_count))
    if device_count == 1 or distinct_experts <= 0:
        return 1.0
    busiest = expected_max_bin_load(device_count, float(distinct_experts), 1.0)
    if busiest <= 0:
        return 1.0
    return max(1.0, min(float(device_count), distinct_experts / busiest))


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

    def rom_cell_area_multiplier(self, weight_amortization: str) -> Graded:
        """Area of this policy's ROM bitcell relative to a storage-only bit.

        A compute-in-ROM cell carries a pass transistor and a product-line tap
        on top of its via programming, so it is larger.  It is *only* larger:
        it adds no bitline and no sense amp, so the array's access rate per
        cell is unchanged and its rate per mm2 falls in exactly the proportion
        its capacity per mm2 falls.  Both densities are therefore divided by
        this multiplier, and the full-array sweep time -- their ratio -- is
        invariant to it.  See ``rom_bits_per_mm2_for``.
        """

        if weight_amortization in COMPUTE_IN_ROM_POLICIES:
            return self.graded("rom", "cim_cell_area_multiplier")
        return Graded(
            value=1.0,
            grade="derived",
            source="storage-only mask-ROM bitcell is the reference cell",
            note="ROM-as-storage feeding a separate MAC array: the cell holds "
            "bits and nothing else, so it is the reference for the multiplier",
        )

    def rom_bits_per_mm2_for(self, node: str, weight_amortization: str) -> Graded:
        """Capacity density of the array this policy actually builds."""

        base = self.rom_bits_per_mm2(node)
        multiplier = self.rom_cell_area_multiplier(weight_amortization)
        if multiplier.value == 1.0:
            return base
        return derived(
            base.value / multiplier.value,
            (base, multiplier),
            "storage_rom_bits_per_mm2 / cim_cell_area_multiplier",
            f"{node} compute-in-ROM array capacity density: a larger cell holds "
            "proportionally fewer bits in the same silicon",
        )

    def rom_read_bytes_s_per_mm2_for(
        self, node: str, weight_amortization: str
    ) -> Graded:
        """Read-bandwidth density of the array this policy actually builds.

        The correction this carries: a compute-in-ROM cell is larger, so a
        square millimetre of it contains fewer cells and delivers proportionally
        fewer bytes per second.  Charging the larger cell against area while
        crediting it with the storage cell's bandwidth density -- which the
        model did before -- handed compute-in-ROM a free 1.6x, because the
        sweep time is capacity density over bandwidth density and only the
        numerator was being scaled.  With both scaled the cell size cancels and
        the sweep is the same for either machine.
        """

        base = self.rom_read_bytes_s_per_mm2(node)
        multiplier = self.rom_cell_area_multiplier(weight_amortization)
        if multiplier.value == 1.0:
            return base
        return derived(
            base.value / multiplier.value,
            (base, multiplier),
            "storage_rom_read_bytes_s_per_mm2 / cim_cell_area_multiplier",
            f"{node} compute-in-ROM array read-bandwidth density: a larger cell "
            "means fewer cells per mm2 and no extra bitlines or sense amps",
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

    def link_fabric(self, name: str) -> str:
        """Whether this link is a switch domain or a stitched mesh.

        The distinction is not decorative: it decides how a collective's
        latency grows with the number of partitions it spans.  Inside a
        switched all-to-all domain every partition is one traversal from every
        other, so the depth is 1 however wide the domain is.  On a mesh there
        is no switch, so the far corner is physically ``2(sqrt(N)-1)``
        traversals away and a collective cannot be faster than that.
        """

        block = self.raw["links"].get(name, {})
        fabric = str(block.get("fabric", {}).get("value", "switched"))
        if fabric not in LINK_FABRICS:
            raise ValidationError(
                f"link {name!r} declares unknown fabric {fabric!r}; "
                f"expected one of {LINK_FABRICS}"
            )
        return fabric

    def link_domain_size(self, name: str) -> Graded:
        """Partitions reachable over this link without leaving its domain."""

        block = self.raw["links"].get(name, {})
        if "domain_size" in block:
            return Graded.from_dict(block["domain_size"])
        return Graded(
            value=1.0,
            grade="derived",
            source=f"links.{name} declares no domain size",
            note="treated as a single-partition domain, so no traffic is "
            "credited to it as intra-domain",
        )

    def link_switch_radix(self, name: str) -> Graded:
        """Endpoints one switch tier of this fabric reaches.

        Only meaningful for a ``switched`` fabric, where a collective spanning
        more endpoints than one tier reaches must climb tiers.
        """

        block = self.raw["links"].get(name, {})
        if "switch_radix" in block:
            return Graded.from_dict(block["switch_radix"])
        domain = self.link_domain_size(name)
        return derived(
            max(2.0, domain.value),
            (domain,),
            "max(2, links.<link>.domain_size)",
            "no switch radix stated, so one tier is taken to reach exactly one "
            "domain",
        )

    def collective_traversals(self, name: str, span: int) -> float:
        """Serial link traversals one whole all-reduce over ``span`` costs.

        Neither branch is a free parameter; each is the published cost model
        for the fabric it describes.

        **Switched fabric** -- Rabenseifner's algorithm as given by Thakur,
        Rabenseifner & Gropp, *Optimization of Collective Communication
        Operations in MPICH*, IJHPCA 19(1):49-66, 2005: reduce-scatter costs
        ``lg p`` startups and all-gather another ``lg p``, so an all-reduce is
        ``2 lg p`` traversals.  The ``lg`` is taken in the radix the fabric
        actually provides rather than always in base 2, which matters because
        an NVSwitch baseboard is a **single all-to-all tier**: every GPU is one
        traversal from every other, so a collective inside one domain costs 2
        traversals however wide the domain is.  That is not a convenience --
        it is what the hardware does, and it is what the measured
        speed-of-light all-reduce floor on GB200 NVL72 shows when it comes out
        "independent of rank count" (Shen et al., arXiv:2607.16100).

        **Mesh fabric** -- a stitched wafer has no switch, so an all-reduce
        cannot finish before the far corner has been heard from and answered.
        Cerebras measured their own: *"the AllReduce operation in a cycle count
        only about 10% greater than the diameter of the system"* (Rocki et al.,
        SC20, arXiv:2010.03660).  The diameter of an ``N``-region square mesh
        is ``2(sqrt(N) - 1)``, so the whole collective is ``1.1`` times that.
        Charging a mesh the flat two traversals a switch gets is the ROM-side
        mirror of charging a GPU cluster a 672-way pipeline, and this model
        used to do exactly that.
        """

        if span <= 1:
            return 0.0
        if self.link_fabric(name) == "mesh":
            diameter = 2.0 * (math.ceil(math.sqrt(span)) - 1)
            return max(1.0, MESH_ALLREDUCE_DIAMETER_FACTOR * diameter)
        radix = max(2.0, self.link_switch_radix(name).value)
        tiers = max(1, math.ceil(math.log(span) / math.log(radix)))
        return 2.0 * tiers

    def link_event_cost_s(
        self, event: "LinkEvent", *, activation_bytes: float
    ) -> tuple[float, dict[str, Any]]:
        """Seconds one event of this class costs on one token's critical path.

        ``activation_bytes`` is ``batch x hidden_size`` bf16 -- one layer's
        activation for the whole batch.  Two rules, both stated rather than
        fitted:

        * **point-to-point**: one hop latency plus the activation serialised
          onto the link.
        * **all-reduce over p partitions**: ``2 * depth * alpha`` of latency
          plus ``(p-1)/p`` of the payload each way -- the bandwidth-optimal
          collective lower bound.  The payload convention is the one already
          used throughout this program: the reduction moves in fp32 and the
          result comes back in bf16, so ``(4 + 2)/2`` times the bf16
          activation.  The ``(p-1)/p`` factor is what makes a 2-way all-reduce
          cheaper than a 672-way one at the same hidden size, and it is the
          reason a collective must know how wide it is.
        """

        hop_latency, link_bytes_s = self.link(event.link)
        if event.kind == "point_to_point":
            payload = activation_bytes
            latency = hop_latency.value
            depth = 1.0
        else:
            span = max(2, int(event.span))
            depth = self.collective_traversals(event.link, span)
            latency = depth * hop_latency.value
            payload = activation_bytes * 3.0 * (span - 1) / span
        transfer = payload / max(link_bytes_s.value, 1e-30)
        detail = {
            "link": event.link,
            "kind": event.kind,
            "count": event.count,
            "span": event.span,
            "fabric": self.link_fabric(event.link),
            "collective_traversals": depth,
            "hop_latency_s": hop_latency.value,
            "link_bytes_s": link_bytes_s.value,
            "payload_bytes_per_event": payload,
            "latency_s_per_event": latency,
            "transfer_s_per_event": transfer,
            "seconds": event.count * (latency + transfer),
            "description": event.description,
        }
        return event.count * (latency + transfer), detail

    def link_time_s(
        self,
        topology: "Topology",
        num_layers: int,
        *,
        activation_bytes: float,
        stage_cap: bool = True,
    ) -> tuple[float, list[dict[str, Any]], float]:
        """Total inter-partition time on one token's critical path."""

        total = 0.0
        payload_total = 0.0
        breakdown: list[dict[str, Any]] = []
        for event in topology.link_events(num_layers, stage_cap=stage_cap):
            seconds, detail = self.link_event_cost_s(
                event, activation_bytes=activation_bytes
            )
            total += seconds
            payload_total += detail["payload_bytes_per_event"] * event.count
            breakdown.append(detail)
        return total, breakdown, payload_total

    def hbm(self, generation: str, field_name: str) -> Graded:
        return self.graded("hbm", generation, field_name)

    def kv_access_granularity_bytes(self, store: str) -> Graded:
        """Smallest number of bytes a KV read of this store actually moves."""

        return self.graded("kv", "access_granularity_bytes", store)

    def kv_index_layout(self) -> tuple[str, str, str]:
        """How index entries sit relative to their payload entries.

        Returned as ``(value, grade, source)``: it is a categorical layout
        CHOICE rather than a physical constant, which is why it is stated here
        and reported in every step rather than buried in a byte count.
        """

        node = self.raw["kv"]["index_layout"]
        return str(node["value"]), str(node["grade"]), str(node["source"])

    def layer_latency_terms(self) -> dict[str, Graded]:
        """The serial per-layer dependency budget."""

        block = self.raw["latency"]
        return {
            key: Graded.from_dict(value)
            for key, value in block.items()
            if isinstance(value, Mapping) and "grade" in value
        }

    def at_layer_latency_bound(self, bound: str) -> "Technology":
        """A copy with every per-layer latency term at one end of its range.

        Every term in the ``latency`` block is ``assumed`` and carries
        ``range_low``/``range_high``.  A single point value inside a wide band
        invites the reader to treat it as measured, and inviting that is how a
        gate becomes a fit.  The anchor is therefore reported at BOTH ends as
        well as at the stated value, and the band is what the reader is asked
        to believe rather than the point.
        """

        if bound not in ("low", "high"):
            raise ValidationError("layer latency bound must be 'low' or 'high'")
        key = "range_low" if bound == "low" else "range_high"
        raw = json.loads(json.dumps(self.raw))
        for name, node in raw["latency"].items():
            if isinstance(node, Mapping) and key in node:
                raw["latency"][name] = {**node, "value": node[key]}
        return replace(self, raw=raw)

    def at_link_latency_bound(
        self, bound: str, links: "Iterable[str] | None" = None
    ) -> "Technology":
        """A copy with link hop latencies at one end of their stated range.

        ``links`` selects which fabrics move.  Passing ``None`` moves every
        link that states a range, which is the joint band: the comparison's
        content is the ratio between two fabrics, and a common-mode error
        moves both.  But a joint band is *not* a statement of how much of the
        uncertainty is ours, and when one side's constants are better
        evidenced than the other's the two partly cancel and the band comes
        out narrower than either side's own.  So the studies also call this
        with one side's links at a time and report the three bands separately.

        Every link with a stated range moves, including one graded
        ``published``.  That is deliberate and it is a change from what this
        docstring used to claim: a measured spread is a real spread, and
        freezing the GPU's measured InfiniBand band while sweeping the ROM's
        would understate the GPU side's own uncertainty.  What must never
        happen is moving a band without saying so, which is why the per-side
        tables name the links in each scope.
        """

        if bound not in ("low", "high"):
            raise ValidationError("link latency bound must be 'low' or 'high'")
        key = "range_low" if bound == "low" else "range_high"
        selected = None if links is None else set(links)
        raw = json.loads(json.dumps(self.raw))
        for name, node in raw["links"].items():
            if selected is not None and name not in selected:
                continue
            latency = node.get("hop_latency_s")
            if isinstance(latency, Mapping) and key in latency:
                raw["links"][name]["hop_latency_s"] = {
                    **latency,
                    "value": latency[key],
                }
        return replace(self, raw=raw)

    #: The energy terms that are part of the POWER band rather than the
    #: latency band.  They are swept with the ``power`` block because a power
    #: gate that moved the leakage but not the traffic energy would report a
    #: band narrower than the one the reader is actually asked to believe.
    POWER_ENERGY_TERMS = (
        "hbm_j_per_byte",
        "rom_read_j_per_byte",
        "operand_delivery_j_per_byte",
        "sram_read_j_per_byte",
    )

    def power_terms(self) -> dict[str, Graded]:
        """Every graded leaf of the ``power`` block, flattened for reporting."""

        found: dict[str, Graded] = {}

        def walk(node: Any, path: tuple[str, ...]) -> None:
            if isinstance(node, Mapping):
                if "grade" in node and "value" in node:
                    found[".".join(path)] = Graded.from_dict(node)
                    return
                for key, value in node.items():
                    walk(value, path + (str(key),))

        walk(self.raw["power"], ())
        return found

    def at_power_bound(self, bound: str) -> "Technology":
        """A copy with every power term at one end of its stated range.

        Every term in the ``power`` block is ``assumed`` bar one, and the two
        that decide the ROM side's answer -- ``fabric_clock_hz`` and the array
        ``clock_region_multiplier`` -- multiply, so a point value inside their
        product invites exactly the misreading the latency band was built to
        prevent.  The two power gates are therefore reported at BOTH ends as
        well as at the stated value, and the band is what the reader is asked
        to believe rather than the point.

        Every term here is monotone increasing in power, so ``high`` really is
        the top of the envelope and ``low`` really is the bottom.  That is a
        property of the terms and not of this method, and it is checked in the
        test suite rather than assumed here.
        """

        if bound not in ("low", "high"):
            raise ValidationError("power bound must be 'low' or 'high'")
        key = "range_low" if bound == "low" else "range_high"
        raw = json.loads(json.dumps(self.raw))

        def move(node: Any) -> Any:
            if isinstance(node, Mapping):
                if "grade" in node and "value" in node:
                    return {**node, "value": node[key]} if key in node else dict(node)
                return {name: move(value) for name, value in node.items()}
            return node

        raw["power"] = move(raw["power"])
        for name in self.POWER_ENERGY_TERMS:
            node = raw["energy"].get(name)
            if isinstance(node, Mapping) and key in node:
                raw["energy"][name] = {**node, "value": node[key]}
        for part in raw["reference_parts"].values():
            clock = part.get("clock_frequency_hz")
            if isinstance(clock, Mapping) and key in clock:
                part["clock_frequency_hz"] = {**clock, "value": clock[key]}
        return replace(self, raw=raw)

    def clock_frequency_hz(self, part: str | None = None) -> Graded:
        """The clock the clock-energy term is evaluated at.

        ``clock_energy_j_per_mm2_per_cycle`` has units of joules per mm2 per
        CYCLE, and before this there was no clock frequency anywhere in the
        technology table or in this module -- so the term could not be applied
        at all without one.  A published part states its own; a modelled design
        falls back on ``power.fabric_clock_hz``, which is the clock the
        ``latency`` block was already reasoning at without ever saying so.
        """

        if part is not None:
            spec = self.reference_part(part)
            if "clock_frequency_hz" in spec:
                return Graded.from_dict(spec["clock_frequency_hz"])
        return self.graded("power", "fabric_clock_hz")

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
# the two costs the model used to price at zero
# --------------------------------------------------------------------------


def layer_fixed_latency(
    technology: Technology, model: ModelProfile
) -> tuple[float, dict[str, float], dict[str, Graded]]:
    """Serial per-layer cost that no amount of bandwidth removes.

    Before this term the only latency anywhere in the model was
    ``links.*.hop_latency_s``, charged at inter-partition boundaries -- so a
    ``single_chip`` design had a decode step with *literally no fixed cost*.
    That is not a small omission: it says a layer can be started, executed and
    retired with nothing but bandwidth, which is false on every architecture.

    **Every term is derived from a primitive that exists independently of the
    Taalas HC1 anchor**, and each carries a stated range:

    * ``sequencer_issue_decode_s`` -- fetch, decode and operand setup for one
      layer's command stream.  Once per layer.
    * ``layer_barrier_s`` -- the layer transition is a barrier: every lane's
      partial must retire and the residual must be formed before the next
      layer's activation exists.  Once per layer.
    * ``sram_access_s`` plus one global traversal -- the KV round trip.  The KV
      *bytes* are charged against bandwidth elsewhere; this is only the
      dependency bandwidth cannot overlap.  Once per layer.
    * ``pipeline_fill_drain_s`` plus one global traversal -- the boundary
      between two serially dependent array passes, charged
      ``array_pass_boundaries_per_layer`` times.
    * ``sparse_index_dependency_s`` -- the index-scan to top-k to gather
      dependency, on ``compressed_sparse`` layers only.  The gather address is
      not known until the scan's top-k completes.

    The broadcast *distance* is derived from the floorplan rather than assumed:
    ``sqrt(reticle.area_mm2)`` is one die edge, taken as the mean distance an
    activation covers, and multiplied by a graded per-millimetre wire delay.

    **The value is deliberately not fitted to the anchor.**  Choosing it to
    close the HC1 gap would turn a validation gate into a one-parameter curve
    fit.  ``taalas_hc1_anchor`` evaluates the gate at both ends of the band and
    reports where it lands as an outcome.

    The same budget is charged to every architecture, which is conservative for
    the ROM side: a GPU's real per-layer floor includes kernel launch and tail
    effects larger than this, and none of that is modelled.
    """

    terms = technology.layer_latency_terms()
    sram_access = terms["sram_access_s"]
    sequencer = terms["sequencer_issue_decode_s"]
    fill_drain = terms["pipeline_fill_drain_s"]
    barrier = terms["layer_barrier_s"]
    wire_per_mm = terms["global_wire_delay_s_per_mm"]
    boundaries = terms["array_pass_boundaries_per_layer"]
    sparse = terms["sparse_index_dependency_s"]
    reticle = technology.graded("reticle", "area_mm2")

    traversal_mm = math.sqrt(reticle.value)
    traversal_s = traversal_mm * wire_per_mm.value

    # The scan-to-top-k-to-gather dependency exists only on a layer that runs
    # its own index scan.  A DeepSeek-V4.1 CSA2 Reuse-mode layer takes its
    # predecessor's selection and has no such dependency.
    sparse_layers = float(
        sum(
            group.count
            for group in model.attention_groups
            if group.kind == "compressed_sparse" and group.scans_index
        )
    )
    layers = float(model.num_layers)

    kv_round_trip_s = sram_access.value + traversal_s
    boundary_s = fill_drain.value + traversal_s
    per_layer_s = (
        sequencer.value
        + barrier.value
        + kv_round_trip_s
        + boundaries.value * boundary_s
    )
    total_s = layers * per_layer_s + sparse_layers * sparse.value

    breakdown = {
        "sequencer_issue_decode_s": sequencer.value,
        "layer_barrier_s": barrier.value,
        "kv_round_trip_s": kv_round_trip_s,
        "array_pass_boundary_s": boundary_s,
        "array_pass_boundaries_per_layer": boundaries.value,
        "global_traversal_mm": traversal_mm,
        "global_traversal_s": traversal_s,
        "extra_s_on_compressed_sparse_layers": sparse.value,
        "compressed_sparse_layers": sparse_layers,
        "layers": layers,
        "seconds_per_layer": per_layer_s,
        "seconds_per_compressed_sparse_layer": per_layer_s + sparse.value,
        "total_s_per_token": total_s,
    }
    inputs = (
        sram_access,
        sequencer,
        fill_drain,
        barrier,
        wire_per_mm,
        boundaries,
        sparse,
        reticle,
    )
    provenance = {
        "layer_fixed_latency_global_traversal_s": derived(
            traversal_s,
            (wire_per_mm, reticle),
            "sqrt(reticle_area_mm2) * global_wire_delay_s_per_mm",
            "mean on-die distance an activation broadcast covers, from the "
            "floorplan rather than assumed",
        ),
        "layer_fixed_latency_s_per_layer": derived(
            per_layer_s,
            inputs,
            "sequencer + barrier + (sram_access + traversal) + boundaries * "
            "(pipeline_fill_drain + traversal)",
            "serial dependency on one token's critical path through one layer",
        ),
        "layer_fixed_latency_s_per_token": derived(
            total_s,
            inputs,
            "layers * per_layer + compressed_sparse_layers * sparse_index",
            "added to the step, never overlapped: layer n+1 cannot start until "
            "layer n's activation exists",
        ),
    }
    return total_s, breakdown, provenance


def _granule_factor(entry_bytes: float, granularity_bytes: float) -> float:
    """Cost of one isolated access of ``entry_bytes`` at this granularity."""

    if entry_bytes <= 0 or granularity_bytes <= 0:
        return 1.0
    return math.ceil(entry_bytes / granularity_bytes) * granularity_bytes / entry_bytes


def kv_access_granularity(
    technology: Technology,
    model: ModelProfile,
    *,
    context_tokens: int,
    store: str,
) -> tuple[float, dict[str, Any], dict[str, Graded]]:
    """How much more than the algorithmic KV bytes the memory actually moves.

    ``workload.kv_traffic`` counts the bytes the algorithm needs.  A memory
    system moves whole access granules, and for DeepSeek-V4-Flash at 200K
    context **72% of the KV read is a scan of 50,000 index entries of 68 bytes
    each, per compressed-sparse layer**.  Whether that costs anything at all is
    a *layout* question, not a physical one, and the answer differs by more than
    1.6x between the two plausible layouts -- which is exactly why it is stated
    here as a named choice rather than folded into a byte count:

    * ``contiguous`` -- the index array is packed separately from its payload,
      so the scan is one long sequential run and granule rounding is lost in
      the noise.  This is the layout a design would choose *if it knew to*.
    * ``interleaved`` -- each index entry sits beside the 583-byte payload entry
      it describes, which is the natural layout if the two are written together
      at generation time.  Every index entry is then its own access and costs a
      whole granule: 96 of 68 useful bytes at a 32-byte HBM granule, 128 at a
      128-byte SRAM row.

    Reads that are genuinely sequential for one user -- the sliding window, a
    full compressed-cache scan -- are charged no rounding.  The top-k gather is,
    because a gather is a gather.
    """

    layout, layout_grade, layout_source = technology.kv_index_layout()
    granularity = technology.kv_access_granularity_bytes(store)
    grain = granularity.value

    sequential = 0.0
    random_native = 0.0
    random_charged = 0.0
    streams: list[dict[str, Any]] = []
    for group in model.attention_groups:
        count = float(group.count)
        window = (
            float(min(context_tokens, group.window_tokens))
            if group.window_tokens
            else 0.0
        )
        entry = float(group.entry_bytes)
        window_entry = float(group.effective_window_entry_bytes)
        if group.kind == "window":
            sequential += count * window * entry
        elif group.kind in {"compressed_sparse", "compressed_dense"}:
            compressed = float(math.ceil(context_tokens / group.compression_ratio))
            sequential += count * window * window_entry
            if group.kind == "compressed_sparse":
                gathered = float(min(group.top_k, compressed))
                native = count * gathered * entry
                factor = _granule_factor(entry, grain)
                random_native += native
                random_charged += native * factor
                streams.append(
                    {
                        "group": group.label or group.kind,
                        "stream": "top_k_payload_gather",
                        "entry_bytes": entry,
                        "bytes": native,
                        "granule_factor": factor,
                    }
                )
                # A Reuse-mode layer scans nothing; a Reindex-mode layer scans
                # only the candidate pool (see AttentionGroup).
                scanned = compressed if group.scans_index else 0.0
                if scanned and group.index_scan_entries_cap:
                    scanned = min(scanned, float(group.index_scan_entries_cap))
                index_native = count * scanned * float(group.index_entry_bytes)
                if layout == "interleaved":
                    index_factor = _granule_factor(
                        float(group.index_entry_bytes), grain
                    )
                    random_native += index_native
                    random_charged += index_native * index_factor
                else:
                    index_factor = 1.0
                    sequential += index_native
                streams.append(
                    {
                        "group": group.label or group.kind,
                        "stream": "sparse_index_scan",
                        "entry_bytes": float(group.index_entry_bytes),
                        "entries_per_layer": scanned,
                        "bytes": index_native,
                        "granule_factor": index_factor,
                    }
                )
            else:
                sequential += count * compressed * entry
        elif group.kind in {"dense_mla", "dense_kv"}:
            sequential += count * float(context_tokens) * entry
        elif group.kind == "recurrent":
            sequential += count * float(group.recurrent_state_bytes)
        # Writes: one full-resolution entry per layer, plus the amortised
        # compressed entry, landing wherever the allocator put them.
        if group.kind == "window":
            write = count * entry
        elif group.kind in {"compressed_sparse", "compressed_dense"}:
            if group.kv_owner and window_entry == entry:
                write = count * entry * (1.0 + 1.0 / group.compression_ratio)
            else:
                write = count * window_entry
                if group.kv_owner:
                    write += count * entry / group.compression_ratio
            if group.kind == "compressed_sparse" and group.kv_owner:
                write += count * float(group.index_entry_bytes) / group.compression_ratio
        elif group.kind == "recurrent":
            write = count * float(
                group.recurrent_state_bytes
                if group.recurrent_write_bytes is None
                else group.recurrent_write_bytes
            )
        else:
            write = count * entry
        factor = _granule_factor(entry, grain)
        random_native += write
        random_charged += write * factor

    native = sequential + random_native
    charged = sequential + random_charged
    inflation = charged / native if native > 0 else 1.0
    detail = {
        "layout": layout,
        "layout_grade": layout_grade,
        "layout_source": layout_source,
        "granularity_bytes": grain,
        "store": store,
        "sequential_bytes": sequential,
        "granule_sensitive_bytes": random_native,
        "granule_sensitive_bytes_charged": random_charged,
        "native_transfer_bytes_per_user_token": native,
        "charged_transfer_bytes_per_user_token": charged,
        "inflation": inflation,
        "streams": streams,
    }
    provenance = {
        "kv_access_granularity_bytes": granularity,
        "kv_access_granularity_inflation": derived(
            inflation,
            (granularity,),
            "sum(bytes * ceil(entry/granule)*granule/entry) / sum(bytes), "
            "sequential runs charged at 1.0",
            f"{store} KV under the {layout!r} index layout",
        ),
    }
    return inflation, detail, provenance


# --------------------------------------------------------------------------
# the power a machine spends whether or not a byte moves
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class StaticPower:
    """Traffic-independent power, charged per mm2 per second.

    This is the term the model did not have.  Before it, ``energy_j`` counted
    memory bytes and multiply-accumulates and nothing else, so power was
    exactly proportional to traffic: an idle machine drew zero and a throttled
    one drew less the more it was throttled.  Both are wrong in the same way,
    and the second one is why ``thermal_scale`` could never bind -- stretching
    a step made the modelled power fall, so any power was coolable.

    Leakage and the clock network do not care whether a byte moves.  They are
    charged against the AREA SPLIT: leakage per mm2 of standard-cell region and
    per mm2 of SRAM and ROM array, clock energy per mm2 per cycle scaled by a
    region-class multiplier, times the clock frequency.  Each region reads its
    own graded density from ``power.static_leakage_w_per_mm2``.

    ``total_w`` is ``max(enumerated_w, floor_w)`` rather than their sum.  The
    measured clocked-idle floor of a shipping device IS mostly its leakage and
    its clock tree, so adding a bottom-up enumeration of those to a measurement
    of them double-counts.  Taking the larger charges whichever estimate is
    higher, never both, and reporting the two side by side says how far apart
    they are -- which on a GPU is a long way, and that gap is a finding rather
    than an embarrassment.
    """

    leakage_w: float
    clock_w: float
    memory_interface_w: float
    enumerated_w: float
    floor_w: float
    total_w: float
    clock_frequency_hz: float
    detail: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "leakage_w": self.leakage_w,
            "clock_w": self.clock_w,
            "memory_interface_w": self.memory_interface_w,
            "enumerated_w": self.enumerated_w,
            "floor_w": self.floor_w,
            "total_w": self.total_w,
            "floor_binds": self.floor_w > self.enumerated_w,
            "clock_frequency_hz": self.clock_frequency_hz,
            "detail": dict(self.detail),
        }


def device_static_power(
    technology: Technology,
    *,
    logic_mm2: float,
    sram_array_mm2: float,
    rom_array_mm2: float,
    unallocated_mm2: float = 0.0,
    devices: int = 1,
    hbm_stacks_per_device: float = 0.0,
    clock: Graded | None = None,
) -> tuple[StaticPower, dict[str, Graded]]:
    """Leakage, clock distribution and memory-interface idle for one machine.

    Areas are **per device** and the result is for the whole machine, because
    every other resource in this model is stated that way.  ``unallocated_mm2``
    is reported and charged nothing: silicon the area split did not assign is
    silicon the model cannot say is populated, and inventing a population for
    it would be inventing power.
    """

    if clock is None:
        clock = technology.clock_frequency_hz()
    leak_logic = technology.graded("power", "static_leakage_w_per_mm2", "logic")
    leak_sram = technology.graded("power", "static_leakage_w_per_mm2", "sram_array")
    leak_rom = technology.graded("power", "static_leakage_w_per_mm2", "rom_array")
    clock_energy = technology.graded("power", "clock_energy_j_per_mm2_per_cycle")
    mult_logic = technology.graded("power", "clock_region_multiplier", "logic")
    mult_sram = technology.graded("power", "clock_region_multiplier", "sram_array")
    mult_rom = technology.graded("power", "clock_region_multiplier", "rom_array")
    floor = technology.graded("power", "clocked_idle_floor_w_per_device")
    memory_idle = technology.graded("power", "memory_interface_idle_w_per_stack")

    leakage_per_device = (
        logic_mm2 * leak_logic.value
        + sram_array_mm2 * leak_sram.value
        + rom_array_mm2 * leak_rom.value
    )
    clock_w_per_mm2 = clock_energy.value * clock.value
    clock_per_device = clock_w_per_mm2 * (
        logic_mm2 * mult_logic.value
        + sram_array_mm2 * mult_sram.value
        + rom_array_mm2 * mult_rom.value
    )
    memory_per_device = hbm_stacks_per_device * memory_idle.value

    leakage_w = devices * leakage_per_device
    clock_w = devices * clock_per_device
    memory_interface_w = devices * memory_per_device
    enumerated_w = leakage_w + clock_w + memory_interface_w
    floor_w = devices * floor.value
    total_w = max(enumerated_w, floor_w)

    detail = {
        "logic_mm2_per_device": logic_mm2,
        "sram_array_mm2_per_device": sram_array_mm2,
        "rom_array_mm2_per_device": rom_array_mm2,
        "unallocated_mm2_per_device_charged_nothing": unallocated_mm2,
        "devices": float(devices),
        "hbm_stacks_per_device": hbm_stacks_per_device,
        "leakage_w_per_device": leakage_per_device,
        "clock_w_per_device": clock_per_device,
        "memory_interface_w_per_device": memory_per_device,
        "clock_w_per_mm2_of_logic": clock_w_per_mm2 * mult_logic.value,
        "clock_w_per_mm2_of_array": clock_w_per_mm2 * mult_rom.value,
        "static_w_per_mm2_of_logic": leak_logic.value + clock_w_per_mm2 * mult_logic.value,
        "static_w_per_mm2_of_rom_array": leak_rom.value + clock_w_per_mm2 * mult_rom.value,
        "static_w_per_mm2_of_sram_array": leak_sram.value + clock_w_per_mm2 * mult_sram.value,
        "total_w_per_mm2": (
            total_w / (devices * (logic_mm2 + sram_array_mm2 + rom_array_mm2 + unallocated_mm2))
            if (logic_mm2 + sram_array_mm2 + rom_array_mm2 + unallocated_mm2) > 0
            else 0.0
        ),
        "rule": (
            "static = max(leakage + clock + memory-interface idle, clocked-idle "
            "floor). The floor is a measured whole-device reading and the "
            "enumeration is a bottom-up estimate OF THE SAME PHYSICS, so they are "
            "combined with max and never added"
        ),
    }
    provenance = {
        "static_leakage_w_per_mm2_logic": leak_logic,
        "static_leakage_w_per_mm2_sram_array": leak_sram,
        "static_leakage_w_per_mm2_rom_array": leak_rom,
        "clock_energy_j_per_mm2_per_cycle": clock_energy,
        "clock_frequency_hz": clock,
        "clock_region_multiplier_logic": mult_logic,
        "clock_region_multiplier_sram_array": mult_sram,
        "clock_region_multiplier_rom_array": mult_rom,
        "clocked_idle_floor_w_per_device": floor,
        "memory_interface_idle_w_per_stack": memory_idle,
        "device_static_power_w": derived(
            total_w,
            (leak_logic, leak_sram, clock_energy, clock, floor, memory_idle),
            "max(leakage_per_mm2 . area + clock_j_per_mm2_per_cycle * f . area * "
            "class_multiplier + stacks * memory_idle, devices * clocked_idle_floor)",
            "traffic-independent power for the whole machine, charged per second "
            "whether or not a byte moves",
        ),
    }
    return (
        StaticPower(
            leakage_w=leakage_w,
            clock_w=clock_w,
            memory_interface_w=memory_interface_w,
            enumerated_w=enumerated_w,
            floor_w=floor_w,
            total_w=total_w,
            clock_frequency_hz=clock.value,
            detail=detail,
        ),
        provenance,
    )


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
    spare_area_policy: str = "sram",
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
    And the compute block shrinks to the pre-computation and accumulation logic
    that forms and sums the products of one activation with the weight alphabet
    -- a configured fixed fraction of the die, not the remainder of it.

    Handing a compute-in-ROM design the leftover area as a MAC array, as this
    function did before, gives it arithmetic it does not have and takes silicon
    from the array that is its whole point.

    **What the freed silicon is spent on is a design choice and is swept, not
    assumed.**  Compute-in-ROM recovers the MAC array's area -- 299 mm2 per
    device on the Qwen array design.  ``spare_area_policy`` decides where it
    goes and the study emits both answers as separate designs:

    * ``"sram"`` -- spare silicon becomes KV store.  Taalas describes exactly
      this split, a mask-ROM recall fabric beside an SRAM recall fabric.  It is
      the right answer when KV binds.
    * ``"rom"`` -- spare silicon becomes **more array, holding a replicated
      copy of the same weights**.  R copies each carry their own bitlines and
      sense amps, so R disjoint slices of the weight set are read at once and
      the full-array sweep time falls by R.  It is the right answer when the
      sweep binds, which at batch 1 it always does.

    ``"rom"`` is offered to the **amortising machine too**, and it has to be:
    giving compute-in-ROM a floorplan sweep and denying it to ROM-plus-MAC
    would move the artefact rather than remove it.  For that machine the array
    cannot simply eat the die, because the MAC array is what executes the
    arithmetic -- so the split is *derived* rather than swept.  The MAC array
    is sized so that its sustained fp8 roof consumes exactly what the array
    beside it can read, at one weight byte per multiply-accumulate.  That is
    the balanced floorplan, and it is the one a designer would actually draw;
    the default ``"sram"`` floorplan instead sizes ROM to the stored bytes and
    gives everything left to MACs, which can leave more MAC roof than the array
    bandwidth can feed.  The resulting feed ratio is reported for each node
    rather than frozen into this contract.

    The replication reading matters: crediting a *larger* array with more
    bandwidth while it holds the *same* bits once would be buying bandwidth for
    bits that do not exist, and an earlier version of this model did exactly
    that and made the anchor twice as fast as the shipping part.  Under
    ``"rom"`` the extra area holds real, addressable copies, and
    ``weight_capacity_bytes`` divided by the stored bytes reports the
    replication factor rather than concealing it.
    """

    if spare_area_policy not in ("sram", "rom"):
        raise ValidationError("spare_area_policy must be 'sram' or 'rom'")

    overhead_fraction = technology.graded("floorplan", "overhead_area_fraction")
    interconnect_fraction = technology.graded(
        "floorplan", "interconnect_area_fraction"
    )
    reasons: list[str] = []

    compute_in_rom = weight_amortization in COMPUTE_IN_ROM_POLICIES
    rom_mm2 = 0.0
    cell_multiplier = technology.rom_cell_area_multiplier(weight_amortization).value
    if weight_store == "rom":
        # The policy's OWN capacity density, already divided by its cell-area
        # multiplier.  The multiplier used to be applied here and nowhere else,
        # so a compute-in-ROM design was charged for a larger cell and then
        # credited with the storage cell's bandwidth per mm2 -- a free 1.6x on
        # the sweep.  Both densities now carry it and it cancels.
        density = (
            technology.rom_bits_per_mm2_for(node, weight_amortization).value
            / BITS_PER_BYTE
        )
        rom_mm2 = stored_weight_bytes / density

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

    # The ROM capacity check used to be tautological.  ROM area was solved from
    # the stored bytes, so ``weight_capacity / stored`` was whatever the cell
    # multiplier happened to be -- 1.6 for compute-in-ROM, 1.0 otherwise, at
    # every model size, every node and every area.  It could not fail, which
    # means it was not a check.  Clamping the array to the silicon that is
    # actually left makes it one: a design whose weights do not fit reports a
    # capacity it cannot reach, and ``evaluate`` refuses it.
    reserved = sram_mm2 + hbm_phy_mm2 + overhead_mm2 + interconnect_mm2
    if compute_in_rom and weight_store == "rom":
        reserved += (
            technology.graded("rom", "cim_precompute_area_fraction").value * total_mm2
        )
    available_for_rom = total_mm2 - reserved
    if weight_store == "rom" and rom_mm2 > available_for_rom:
        reasons.append(
            f"AREA: the array needs {rom_mm2:,.1f} mm2 to hold "
            f"{stored_weight_bytes:,.0f} B but only {max(0.0, available_for_rom):,.1f} "
            f"mm2 of {total_mm2:,.0f} mm2 is left after SRAM, HBM PHY, overhead "
            f"and interconnect"
        )
        rom_mm2 = max(0.0, available_for_rom)

    if (
        spare_area_policy == "rom"
        and weight_store == "rom"
        and not compute_in_rom
        and available_for_rom > rom_mm2
    ):
        # Balanced ROM-plus-MAC: size the MAC array to exactly consume the read
        # rate of the array beside it, at one weight byte per MAC, and give the
        # array everything else.  Both sides of the ratio are graded densities,
        # so the split is derived rather than chosen.
        read_density = (
            technology.rom_read_bytes_s_per_mm2_for(node, weight_amortization).value
            * technology.efficiency("rom_read_bandwidth").value
        )
        mac_density = (
            technology.compute_ops_s_per_mm2(node, "fp8").value
            * technology.efficiency("compute").value
            / 2.0
        )
        if mac_density > 0:
            mm2_of_mac_per_mm2_of_rom = read_density / mac_density
            balanced_rom = available_for_rom / (1.0 + mm2_of_mac_per_mm2_of_rom)
            rom_mm2 = max(rom_mm2, balanced_rom)

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
            # Where the recovered MAC-array silicon goes.  Both answers are
            # emitted by the study as separate designs; neither is assumed.
            if spare_area_policy == "rom":
                rom_mm2 += leftover
            else:
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
                "no MAC array, pre-compute block only, spare silicon to "
                + (
                    "a replicated array copy"
                    if spare_area_policy == "rom"
                    else "SRAM"
                )
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
        policy=(
            "balanced: ROM sized to the stored weights, SRAM sized to the "
            "resident KV, graded fixed fractions for overhead and "
            "interconnect, compute takes the rest"
            if spare_area_policy == "sram"
            else "balanced ROM+MAC: the array is grown into the spare silicon "
            "as replicated copies and the MAC array is sized to consume exactly "
            "what it can read, at one weight byte per multiply-accumulate"
        ),
        reasons=tuple(reasons),
    )


# --------------------------------------------------------------------------
# topology
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class LinkEvent:
    """One class of inter-partition event on a token's critical path.

    An event is either a **collective** -- an all-reduce over ``span``
    partitions, which every partition must both contribute to and wait for --
    or a **point-to-point** hop across a pipeline-stage boundary, which is one
    send and one receive.  The two are priced differently and on different
    links, which is the whole reason this is a structure rather than a count.
    """

    count: float
    link: str
    kind: str
    span: int
    description: str

    def __post_init__(self) -> None:
        if self.kind not in ("all_reduce", "point_to_point"):
            raise ValidationError(
                "link event kind must be all_reduce or point_to_point"
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Topology:
    """Where the devices are and how a token gets through them.

    Every multi-device topology here is one shape with two knobs: ``G``
    partitions tensor-parallel inside a stage, ``S = ceil(P / G)`` stages
    pipelined across.  ``pipeline`` is ``G = 1``, ``tensor`` is ``S = 1``, and
    ``hybrid`` is what a real deployment does -- tensor-parallel inside a
    high-bandwidth domain, pipeline-parallel across domains.

    The **domain** is the second half of that.  A fabric is not one link class:
    an HGX baseboard is an all-to-all NVLink island of ``intra_domain_size``
    GPUs, and everything past the island edge is a scale-out fabric an order of
    magnitude slower in both latency and bandwidth.  A wafer is the same shape
    with different numbers -- an on-wafer mesh inside one wafer, a package-class
    link between wafers.  ``intra_link`` carries traffic inside a domain and
    ``link`` carries it between domains.  With ``intra_domain_size = 1`` (the
    default) every event lands on ``link`` and the model reduces exactly to the
    single-link behaviour it replaced.
    """

    kind: str
    device_count: int
    parallelism: str
    link: str
    on_wafer_regions: int = 1
    intra_link: str = ""
    intra_domain_size: int = 1
    tensor_group_size: int = 1

    def __post_init__(self) -> None:
        if self.device_count < 1:
            raise ValidationError("device_count must be at least 1")
        if self.parallelism not in PARALLELISMS:
            raise ValidationError(f"parallelism must be one of {PARALLELISMS}")
        if self.kind not in ("single_chip", "array", "wafer"):
            raise ValidationError("topology kind must be single_chip, array or wafer")
        if self.kind == "single_chip" and self.device_count != 1:
            raise ValidationError("single_chip topology must have one device")
        if self.intra_domain_size < 1:
            raise ValidationError("intra_domain_size must be at least 1")
        if self.tensor_group_size < 1:
            raise ValidationError("tensor_group_size must be at least 1")

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

    @property
    def inner_link(self) -> str:
        """The link inside one high-bandwidth domain."""

        return self.intra_link or self.link

    @property
    def tensor_group(self) -> int:
        """Partitions one all-reduce spans.

        ``tensor`` spans the whole machine -- which is exactly why nobody runs
        it that way at scale.  ``hybrid`` spans a domain.  ``pipeline`` spans
        nothing.
        """

        partitions = self.partitions
        if self.parallelism == "tensor":
            return partitions
        if self.parallelism == "hybrid":
            return max(1, min(self.tensor_group_size, partitions))
        return 1

    @property
    def pipeline_stages(self) -> int:
        """Stages the partitions would form before the layer-count cap.

        ``link_events`` applies the cap, because it is the only place that
        knows how many layers the model has.
        """

        group = self.tensor_group
        if group <= 0:
            return self.partitions
        return max(1, math.ceil(self.partitions / group))

    @property
    def token_slots(self) -> int:
        """Independent groups the machine is cut into for one token's purposes.

        A token is served by exactly **one** of these at a time, so this is the
        factor between the machine's aggregate service time and one user's
        latency.  It is ``partitions / tensor_group``: the partitions that work
        on the same token simultaneously divide out, and everything else
        multiplies the serial path.

        * A single chip has one slot.
        * A **tensor**-parallel machine has one slot however many partitions it
          holds, because they are all on the same token.  That is what tensor
          parallelism buys and what its two all-reduces per layer pay for.
        * A **pipeline** of ``P`` partitions has ``P`` slots.  Adding devices
          under pipeline parallelism buys aggregate throughput and buys one user
          nothing: each stage holds ``1/P`` of the weights and reads them with
          ``1/P`` of the bandwidth, so the two cancel and the token's latency is
          the same as on one device that held everything.
        * A **hybrid** machine has one slot per tensor group.

        This is the same quantity as ``pipeline_stages``, before the layer cap.
        The cap belongs to ``link_events``, which counts *boundaries a token
        crosses*; beyond the layer count the surplus partitions hold replicas of
        a stage, and a replica adds no boundary and no speed -- it serves a
        different user.  Both readings give the same latency, which is why the
        cap can differ between the two without either being wrong.
        """

        return self.pipeline_stages

    def stages_for(self, num_layers: int) -> int:
        """Serially dependent stages a token actually traverses."""

        return min(self.pipeline_stages, max(1, int(num_layers)))

    def link_events(
        self, num_layers: int, *, stage_cap: bool = True
    ) -> tuple[LinkEvent, ...]:
        """Every inter-partition event on one token's critical path.

        Tensor parallelism costs **two all-reduces per layer per token** --
        after the attention output projection and after the MLP down
        projection -- at every batch size, and the collective is split across
        the two link classes exactly as a hierarchical all-reduce is: reduce
        inside each domain, reduce across domains, broadcast back.  Pipeline
        parallelism costs **one point-to-point hop per stage boundary** and no
        collective, and those boundaries are charged to the fabric they
        actually cross: a 672-partition pipeline laid out on 8-GPU islands
        crosses 588 island-internal boundaries and 83 network boundaries, not
        671 of either.
        """

        partitions = self.partitions
        if partitions <= 1 or self.parallelism == "none":
            return ()

        domain = max(1, self.intra_domain_size)
        inner = self.inner_link
        group = self.tensor_group
        # **A token cannot cross more stage boundaries than the model has
        # layers.**  672 partitions do not make 671 pipeline stages of a
        # 61-layer model; they make at most 61, and the partitions past that
        # hold another copy of a stage.  Under this model's own service rule
        # those extra partitions still contribute their bandwidth to the step
        # -- that rule already credits every device with every token -- but
        # they add no serial event, because nothing on the token's path waits
        # for them.  Without this cap a large cluster is charged a serial hop
        # for silicon that is not on its critical path at all, and that single
        # miscount was most of the reported iso-area advantage at scale.
        stages = self.stages_for(num_layers) if stage_cap else self.pipeline_stages
        events: list[LinkEvent] = []

        if group > 1:
            inside = min(group, domain)
            across = math.ceil(group / domain)
            if inside > 1:
                events.append(
                    LinkEvent(
                        count=2.0 * num_layers,
                        link=inner,
                        kind="all_reduce",
                        span=inside,
                        description=(
                            f"two all-reduces per layer per token over {inside} "
                            f"partitions inside one {inner} domain"
                        ),
                    )
                )
            if across > 1:
                events.append(
                    LinkEvent(
                        count=2.0 * num_layers,
                        link=self.link,
                        kind="all_reduce",
                        span=across,
                        description=(
                            f"two all-reduces per layer per token across {across} "
                            f"{self.link} domains"
                        ),
                    )
                )

        if stages > 1:
            stages_per_domain = max(1, domain // group)
            domains = math.ceil(stages / stages_per_domain)
            outer_boundaries = domains - 1
            inner_boundaries = (stages - 1) - outer_boundaries
            if inner_boundaries > 0:
                events.append(
                    LinkEvent(
                        count=float(inner_boundaries),
                        link=inner,
                        kind="point_to_point",
                        span=2,
                        description=(
                            f"{inner_boundaries} pipeline-stage boundaries inside a "
                            f"{inner} domain"
                        ),
                    )
                )
            if outer_boundaries > 0:
                events.append(
                    LinkEvent(
                        count=float(outer_boundaries),
                        link=self.link,
                        kind="point_to_point",
                        span=2,
                        description=(
                            f"{outer_boundaries} pipeline-stage boundaries across "
                            f"{self.link}"
                        ),
                    )
                )
        return tuple(events)

    def hop_events(self, num_layers: int) -> tuple[float, str]:
        """Total serial inter-partition events, and what they are.

        Kept as a scalar for the reports and the sizing sweep; the priced
        breakdown is ``link_events``.
        """

        events = self.link_events(num_layers)
        if not events:
            return 0.0, "no inter-partition event on one token's critical path"
        total = sum(event.count for event in events)
        return total, "; ".join(event.description for event in events)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["inner_link"] = self.inner_link
        data["tensor_group"] = self.tensor_group
        data["pipeline_stages"] = self.pipeline_stages
        return data


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
    static_power: StaticPower
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
            "static_power_w": self.static_power.total_w,
            "static_power": self.static_power.to_dict(),
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
    spare_area_policy: str = "sram",
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
            spare_area_policy=spare_area_policy,
        )

    rom_capacity_density = technology.rom_bits_per_mm2_for(node, weight_amortization)
    rom_bandwidth_density = technology.rom_read_bytes_s_per_mm2_for(
        node, weight_amortization
    )
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
        "and expert coverage, so it is a hard per-token ceiling for a ROM design. "
        "It is also independent of the CELL, because both densities carry the "
        "cell-area multiplier: a compute-in-ROM array and a storage-only array "
        "sweep in the same time and differ only in how much they hold",
    )
    provenance["rom_cell_area_multiplier"] = technology.rom_cell_area_multiplier(
        weight_amortization
    )

    # -- traffic-independent power ---------------------------------------
    # Charged against the SOLVED area split, so a design that spends its
    # silicon differently pays differently.  Compute, interconnect, HBM PHY and
    # overhead are all standard-cell-class regions; the ROM and SRAM arrays are
    # not, and are charged at the array leakage and array clock multipliers.
    # HBM PHY is deliberately NOT charged at zero clock: the argument that its
    # power is already inside ``energy.hbm_j_per_byte`` is wrong, because that
    # term is a per-byte access energy and carries no idle floor.
    static_power, static_provenance = device_static_power(
        technology,
        logic_mm2=(
            split.compute_mm2
            + split.interconnect_mm2
            + split.hbm_phy_mm2
            + split.overhead_mm2
        ),
        sram_array_mm2=split.sram_mm2,
        rom_array_mm2=split.rom_mm2,
        unallocated_mm2=split.slack_mm2,
        devices=devices,
        hbm_stacks_per_device=float(hbm_stacks) if kv_store == "hbm" else 0.0,
    )
    provenance.update(static_provenance)

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
        static_power=static_power,
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

    # -- traffic-independent power ---------------------------------------
    # This model does not floorplan a published part -- its area is STATED for
    # the iso-area comparison, not solved -- so the one number a per-mm2-of-
    # standard-cell leakage density needs is stated too, as
    # ``power.gpu_logic_area_fraction``, rather than smuggled in by charging
    # logic leakage over 40 MB of L2 and five HBM PHYs.  The clock term needs
    # no such split: it was calibrated on a GPU's WHOLE-die TDP density, so the
    # whole die is its reference region and carries multiplier 1.0.
    logic_fraction = technology.graded("power", "gpu_logic_area_fraction")
    clock = technology.clock_frequency_hz(part)
    static_power, static_provenance = device_static_power(
        technology,
        logic_mm2=area.value * logic_fraction.value,
        sram_array_mm2=area.value * (1.0 - logic_fraction.value),
        rom_array_mm2=0.0,
        devices=devices,
        hbm_stacks_per_device=stacks.value,
        clock=clock,
    )
    # The clock term's calibration region is the whole die, so the array-class
    # multiplier must not be applied to a GPU's non-logic area.  Recompute the
    # clock leg over the full die and keep the leakage split.
    clock_energy = technology.graded("power", "clock_energy_j_per_mm2_per_cycle")
    clock_w = devices * area.value * clock_energy.value * clock.value
    enumerated = static_power.leakage_w + clock_w + static_power.memory_interface_w
    static_power = replace(
        static_power,
        clock_w=clock_w,
        enumerated_w=enumerated,
        total_w=max(enumerated, static_power.floor_w),
        detail={
            **static_power.detail,
            "clock_w_per_device": clock_w / devices,
            "clock_region_note": (
                "clock charged over the WHOLE die at multiplier 1.0, because "
                "power.clock_energy_j_per_mm2_per_cycle is calibrated on a GPU's "
                "whole-die TDP density and this is that reference region"
            ),
            "gpu_logic_area_fraction": logic_fraction.value,
        },
    )
    provenance.update(static_provenance)
    provenance["gpu_logic_area_fraction"] = logic_fraction

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
        static_power=static_power,
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

    ``component_times_s`` are the terms of the roofline before the overlap rule
    is applied, each **on one user's critical path**: the three service terms
    are already multiplied by the slots a token traverses, so the largest of
    them is the one that actually sets ``step_time_s``.  ``binding_constraint``
    names it, so no result can be read without knowing why it came out that way.

    ``step_time_s`` is one user's latency and ``per_user_tokens_s`` is its
    reciprocal.  ``aggregate_tokens_s`` is the machine's rate with every slot
    occupied and is **not** ``batch_size * per_user_tokens_s``; that quantity is
    ``metrics["delivered_tokens_s"]``.  ``metrics["token_slots"]`` is what
    separates them, and ``metrics["per_user_tokens_s_throughput_view"]`` is the
    single number this model reported for both before they were separated.
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
@dataclass(frozen=True)
class ServiceTerms:
    """The batch-dependent half of one step, evaluated at one effective batch.

    ``evaluate`` needs this at two different batches and the two answers mean
    different things:

    * at the **microbatch one pipeline slot holds**, it is what a single user's
      token actually costs at each stage it visits, and multiplying by the slot
      count gives that user's latency;
    * at the **whole batch**, it is the throughput view -- what the machine's
      aggregate resources cost if every device were working on every token at
      once, which is true only under tensor parallelism.

    The model used to compute the second and report it as the first.  Sharing
    one implementation between them is what stops the two drifting apart again.
    """

    effective_batch: float
    weight_time_s: float
    kv_time_s: float
    compute_time_s: float
    memory_time_s: float
    service_time_s: float
    link_time_s: float
    energy_j: float
    overlap_rule: str
    reasons: tuple[str, ...]
    detail: Mapping[str, Any]


def _service_terms(
    budget: DeviceBudget,
    model: ModelProfile,
    technology: Technology,
    *,
    context_tokens: int,
    effective_batch: float,
    stored_weight_bytes: float,
    representation_scale: float,
    weight_traffic_policy: str,
    execution_format: str | None,
    measured_expert_coverage: float | None,
    kv: Any,
    kv_inflation: float,
) -> ServiceTerms:
    """One pass of the whole model over ``effective_batch`` concurrent tokens.

    Every resource here is the machine's **aggregate** -- the full array
    bandwidth, the full compute roof.  That is the right denominator for a set
    of partitions that all work on the same token at the same time, which is
    what tensor parallelism is.  It is the wrong denominator for a token that
    visits its partitions in sequence, and ``evaluate`` is where that
    distinction is applied: it multiplies this by the number of slots the
    machine is cut into.  Nothing in this function knows about that factor.
    """

    reasons: list[str] = []
    devices = budget.topology.device_count
    traffic = weight_traffic(
        model, effective_batch, measured_coverage=measured_expert_coverage
    )
    coverage = traffic.routed_expert_coverage
    if weight_traffic_policy == "full_checkpoint":
        engaged_weight_bytes = stored_weight_bytes
    else:
        engaged_weight_bytes = traffic.total_bytes * representation_scale
    operations = _scaled_operations(
        model, technology, context_tokens, effective_batch, execution_format
    )
    resident_kv_bytes = kv.storage_bytes_per_user * effective_batch
    native_kv_transfer_bytes = (kv.read_bytes + kv.write_bytes) * effective_batch
    kv_transfer_bytes = native_kv_transfer_bytes * kv_inflation

    # -- weight read ------------------------------------------------------
    region_sweeps = 1.0
    mean_region_passes: float | None = None
    mean_engaged_devices: float | None = None
    engaged_devices = float(devices)
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
            # With B tokens each selecting k of N experts, the array is not
            # finished when the AVERAGE engaged region has drained: it is
            # finished when the BUSIEST one has.  ``expected_max_region_load``
            # computes the busiest region directly, and the router-quality
            # multiplier is what is LEFT for a derate: the residual imbalance of
            # a trained router against the uniform-random draw that statistic
            # assumes.
            #
            # A dense model has one region by construction, so every token lands
            # on it and this reduces to per_stream -- correctly, because a dense
            # model has no disjointness to exploit.
            experts_per_token = max(1, int(model.experts_per_token or 1))
            num_experts = max(1, int(model.num_experts or 1))
            mean_engaged_regions = max(1.0, num_experts * coverage)
            mean_region_passes = max(
                1.0,
                min(
                    (effective_batch * experts_per_token) / mean_engaged_regions,
                    float(effective_batch),
                ),
            )
            passes = expected_max_region_load(
                num_experts, effective_batch, experts_per_token
            )
            router_imbalance = technology.efficiency("expert_router_imbalance").value
            passes *= max(router_imbalance, 1e-9)
            # A per-region fabric can never be worse than a global broadcast --
            # in the limit every token lands on one region, which is per_stream.
            passes = min(max(1.0, passes), float(effective_batch))
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
            engaged_weight_bytes = per_stream_bytes * effective_batch
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
            region_sweeps = float(effective_batch)
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
        # The same mean-for-maximum error, on the other side of the comparison.
        # ``workload.expected_engaged_devices`` returns the expected number of
        # devices holding at least one selected expert, and the routed fetch was
        # divided by it -- but the fetch finishes when the BUSIEST device
        # finishes, not when the average one does.  ``workload.py`` is shared
        # with ``opentallas.analytical`` and is not edited; the correction lives
        # here and both numbers are reported, because correcting only the ROM
        # side would be its own bias.
        mean_engaged_devices = expected_engaged_devices(
            devices, traffic.distinct_experts_per_layer
        )
        engaged_devices = effective_engaged_devices(
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
    # A diagnostic, not a term.  The line above credits ONE user with the whole
    # array's read bandwidth, which at batch 1 on a wafer reads a user's 99 MB
    # of KV in nanoseconds.  That is defensible for KV and not for ROM: KV is
    # written at run time and can be striped across every bank, whereas an
    # expert's weights live where they were masked.  But it is defensible only
    # if the design actually stripes, and the model never checks.  The bound
    # below is what the same read costs if a user can only draw the banks its
    # own footprint occupies -- the ROM locality rule applied to SRAM.  It is
    # reported at every point so the exposure is visible rather than implicit.
    # Only for an on-die array.  HBM is striped across channels by construction
    # -- that is what a memory controller is for -- so the global-bandwidth
    # credit is not an assumption there, and the bound equals the term.
    kv_bank_occupancy = (
        min(1.0, resident_kv_bytes / budget.kv_capacity_bytes)
        if (budget.kv_store == "sram" and budget.kv_capacity_bytes > 0)
        else 1.0
    )
    kv_time_under_bank_locality = (
        kv_time / kv_bank_occupancy if kv_bank_occupancy > 0 else math.inf
    )

    # -- compute ----------------------------------------------------------
    compute_time, compute_by_format, compute_reasons = _compute_time(
        operations, budget, technology
    )
    reasons.extend(compute_reasons)

    # -- link -------------------------------------------------------------
    # Every event is priced on the link it actually crosses and, for a
    # collective, on how many partitions it spans.  Charging one link class and
    # one flat hop cost for a whole machine is what let a 672-partition
    # pipeline look like 671 NVLink hops and a 681-region all-reduce look like
    # two on-wafer hops; neither is a machine anyone builds.
    activation_bytes = effective_batch * model.hidden_size * 2.0
    link_time, link_breakdown, link_payload_bytes = technology.link_time_s(
        budget.topology, model.num_layers, activation_bytes=activation_bytes
    )
    # What the same machine would be charged if a token were allowed to cross
    # more stage boundaries than the model has layers -- which is what this
    # study did before.  Carried on every point because it is the size of the
    # correction, and the correction is most of the headline.
    link_time_without_stage_cap, _, _ = technology.link_time_s(
        budget.topology,
        model.num_layers,
        activation_bytes=activation_bytes,
        stage_cap=False,
    )

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

    # -- energy -----------------------------------------------------------
    # DYNAMIC energy only: what one pass over ``effective_batch`` users costs
    # in bytes moved and arithmetic done.  Everything that costs power whether
    # or not a byte moves lives in ``budget.static_power`` and is charged per
    # second in ``evaluate``, not per byte here.
    if budget.weight_store == "rom":
        weight_energy_term = technology.graded("energy", "rom_read_j_per_byte")
    else:
        weight_energy_term = technology.graded("energy", "hbm_j_per_byte")
    if budget.kv_store == "sram":
        kv_energy_term = technology.graded("energy", "sram_read_j_per_byte")
    else:
        kv_energy_term = technology.graded("energy", "hbm_j_per_byte")
    # Getting a byte from the array that holds it to the arithmetic that
    # consumes it.  A Horowitz-class MAC energy is the ALU and
    # ``rom_read_j_per_byte``'s stated boundary stops at the macro output
    # latch, so without this term the model charges nothing at all for the
    # distance between them.  It is the TILE-LOCAL floor: the long-path ladder
    # -- HBM to L2 to register file is a further 8-10 pJ/B on an A100 -- is not
    # represented, and charging one scalar to both sides penalises the ROM side
    # about 1.6x on its dominant term against about 1.01x on the GPU's, which
    # is the safe direction for this comparison.
    operand_delivery = technology.graded("energy", "operand_delivery_j_per_byte")
    weight_energy_j = engaged_weight_bytes * weight_energy_term.value
    kv_energy_j = kv_transfer_bytes * kv_energy_term.value
    operand_energy_j = (
        engaged_weight_bytes + kv_transfer_bytes
    ) * operand_delivery.value
    mac_energy_j = sum(
        count * technology.mac_energy_j_per_op(canonical).value
        for canonical, count in operations.items()
    )
    energy_j = weight_energy_j + kv_energy_j + operand_energy_j + mac_energy_j
    energy_breakdown = {
        "weight_read_j": weight_energy_j,
        "kv_read_j": kv_energy_j,
        "operand_delivery_j": operand_energy_j,
        "arithmetic_j": mac_energy_j,
    }

    detail: dict[str, Any] = {
        "engaged_weight_bytes": engaged_weight_bytes,
        "engaged_weight_fraction": engaged_fraction,
        "effective_weight_read_bytes_s": effective_weight_bw,
        "expert_coverage": coverage,
        "distinct_experts_per_layer": traffic.distinct_experts_per_layer,
        "engaged_devices": (
            engaged_devices
            if (budget.weight_store != "rom" and mean_engaged_devices is not None)
            else float(devices)
        ),
        "mean_engaged_devices_uncorrected": (
            mean_engaged_devices if mean_engaged_devices is not None else float(devices)
        ),
        "engaged_device_max_over_mean_correction": (
            mean_engaged_devices / engaged_devices
            if (mean_engaged_devices is not None and engaged_devices > 0)
            else 1.0
        ),
        "kv_native_transfer_bytes_per_step": native_kv_transfer_bytes,
        "kv_transfer_bytes_per_step": kv_transfer_bytes,
        "resident_kv_bytes_this_pass": resident_kv_bytes,
        "kv_bank_occupancy": kv_bank_occupancy,
        "kv_read_s_under_bank_locality": kv_time_under_bank_locality,
        "operations_by_canonical_format": dict(operations),
        "compute_times_s_by_format": compute_by_format,
        "link_breakdown": link_breakdown,
        "link_latency_without_stage_cap_s": link_time_without_stage_cap,
        "link_payload_bytes_per_token": float(link_payload_bytes),
        "region_sweeps": region_sweeps,
        "mean_region_passes": mean_region_passes,
        "stage_balance_applied": apply_balance,
        "dynamic_energy_breakdown_j": energy_breakdown,
    }
    return ServiceTerms(
        effective_batch=float(effective_batch),
        weight_time_s=weight_time,
        kv_time_s=kv_time,
        compute_time_s=compute_time,
        memory_time_s=memory_time,
        service_time_s=service_time,
        link_time_s=link_time,
        energy_j=energy_j,
        overlap_rule=overlap_rule,
        reasons=tuple(reasons),
        detail=detail,
    )


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
    """Evaluate one decode step against an area-derived resource budget.

    Two rates come out of this and they are **not** the same number divided by
    the batch:

    ``per_user_tokens_s``
        One user's token rate: the reciprocal of the full serial path that
        user's token takes through the machine, including every slot it must
        visit in turn and every collective its tensor group must complete.

    ``aggregate_tokens_s``
        The machine's total rate **with every slot occupied**.  A machine cut
        into ``S`` slots needs ``S`` concurrent users before it reaches this;
        below that its slots idle and what it actually delivers is
        ``batch_size x per_user_tokens_s``, reported as ``delivered_tokens_s``.

    They coincide only when the machine has one slot -- a single chip, or a
    tensor-parallel group that spans every partition.
    """

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
    kv_inflation, kv_granularity_detail, kv_granularity_provenance = (
        kv_access_granularity(
            technology,
            model,
            context_tokens=context_tokens,
            store=budget.kv_store,
        )
    )
    resident_kv_bytes = kv.storage_bytes_per_user * batch_size

    # -- capacity ---------------------------------------------------------
    # A region the model declares resident in its KV store is already out of
    # ``checkpoint_bytes``, so the weight store is sized without it and its
    # released packing is unaffected by ``weight_bits_per_parameter`` -- the ROM
    # representation is a choice about what the ROM holds, and the ROM holds none
    # of this.  A design whose two stores are the same store pays it once, on both
    # sides of the same comparison.
    resident_kv_store_bytes = hbm_resident_weight_bytes(model)
    weight_store_demand = stored_weight_bytes + (
        resident_kv_store_bytes if budget.shared_memory_path else 0.0
    )
    if weight_store_demand > budget.weight_capacity_bytes + CAPACITY_TOLERANCE_BYTES:
        reasons.append(
            f"CAPACITY: stored weights {weight_store_demand:,.0f} B exceed weight "
            f"capacity {budget.weight_capacity_bytes:,.0f} B"
        )
    if budget.shared_memory_path:
        remaining = (
            budget.kv_capacity_bytes - stored_weight_bytes - resident_kv_store_bytes
        )
    else:
        remaining = budget.kv_capacity_bytes - resident_kv_store_bytes
    if resident_kv_bytes > remaining + CAPACITY_TOLERANCE_BYTES:
        reasons.append(
            f"CAPACITY: resident KV {resident_kv_bytes:,.0f} B exceeds available KV "
            f"capacity {max(0.0, remaining):,.0f} B at batch {batch_size}"
        )
    # **The same one-byte tolerance the feasibility test above uses.**  Without
    # it the two disagree: a design whose remaining capacity is
    # 1,207,959,551.9999998 B against a session needing 1,207,959,552.0 B is
    # declared FEASIBLE at batch 1 by the ``+ 1.0`` comparison and then reports
    # ``max_resident_users = 0`` from an exact floor division.  Zero is falsy,
    # so the pipeline-fill cap below was skipped exactly on the machines that
    # needed it most, and their aggregate throughput was published as the
    # pipeline depth times a rate the machine could not deliver to that many
    # users.  One rule, stated once, used by both.
    max_resident_users = (
        int((max(0.0, remaining) + CAPACITY_TOLERANCE_BYTES) // kv.storage_bytes_per_user)
        if kv.storage_bytes_per_user > 0
        else 0
    )

    # -- the two views ----------------------------------------------------
    # ``token_slots`` is the number of independent groups the machine is cut
    # into: partitions divided by the partitions that work on one token at
    # once.  A single chip has one.  A tensor-parallel machine has one, however
    # many partitions it holds, because they are all on the same token.  A
    # 672-way pipeline has 672, and a token is served by exactly one of them at
    # a time.
    slots = float(budget.topology.token_slots)
    # Users sharing one weight pass inside one slot.  Below one slot's worth of
    # users the pass still happens, so the microbatch floors at one and the
    # surplus slots idle.
    microbatch = max(1.0, batch_size / slots) if slots > 0 else float(batch_size)

    terms = _service_terms(
        budget,
        model,
        technology,
        context_tokens=context_tokens,
        effective_batch=microbatch,
        stored_weight_bytes=stored_weight_bytes,
        representation_scale=representation_scale,
        weight_traffic_policy=weight_traffic_policy,
        execution_format=execution_format,
        measured_expert_coverage=measured_expert_coverage,
        kv=kv,
        kv_inflation=kv_inflation,
    )
    reasons.extend(terms.reasons)
    if math.isclose(microbatch, float(batch_size), rel_tol=1e-12):
        throughput_view = terms
    else:
        throughput_view = _service_terms(
            budget,
            model,
            technology,
            context_tokens=context_tokens,
            effective_batch=float(batch_size),
            stored_weight_bytes=stored_weight_bytes,
            representation_scale=representation_scale,
            weight_traffic_policy=weight_traffic_policy,
            execution_format=execution_format,
            measured_expert_coverage=measured_expert_coverage,
            kv=kv,
            kv_inflation=kv_inflation,
        )

    # -- the per-layer serial floor ---------------------------------------
    # Decode is sequential across layers, and each layer has dependencies that
    # no bandwidth removes.  Before this term a single_chip design had no fixed
    # cost whatsoever on its critical path.
    fixed_latency, fixed_latency_detail, fixed_latency_provenance = (
        layer_fixed_latency(technology, model)
    )

    # -- the serial path --------------------------------------------------
    # **The correction.**  A token is served by one slot at a time, so it gets
    # ``1/slots`` of the machine's aggregate resource and must visit every slot
    # before its step is done.  The two factors do not cancel: they multiply the
    # service time by ``slots``.  Charging the aggregate service time and then
    # adding the hops -- which is what this model did -- is a throughput view of
    # the silicon wearing a latency view of the fabric, and it reported a
    # balanced S-stage pipeline as S times faster per user than it is.
    #
    # Tensor parallelism is the exception and that is the whole point of it:
    # every partition works on the same token, ``slots`` is one, and the
    # multiplier disappears.  What the tensor group pays instead is two
    # all-reduces per layer, already priced in ``link_time_s``.
    service_time = terms.service_time_s * slots
    raw_step_time = service_time + terms.link_time_s + fixed_latency
    # The number this model used to report as per-user latency, kept on every
    # point so the size of this correction is separable from every other one.
    throughput_view_step_time = (
        throughput_view.service_time_s
        + throughput_view.link_time_s
        + fixed_latency
    )

    # -- power and thermal ------------------------------------------------
    # Energy per token, times the rate the machine actually produces tokens at.
    # ``terms.energy_j`` is one pass over ``microbatch`` users, so dividing by
    # the microbatch gives the energy one token costs, and a machine with every
    # slot busy produces ``fill_users`` tokens per serial path.  On a single
    # chip ``slots`` and ``fill_users/batch`` are both one and this is exactly
    # the previous expression.
    fill_users = max(float(batch_size), slots * microbatch)
    if max_resident_users > 0 and fill_users > max_resident_users:
        # A slot cannot be occupied by a user whose KV the machine cannot hold.
        fill_users = max(float(batch_size), float(max_resident_users))
        fill_limit = "kv_capacity"
    elif slots * microbatch > batch_size:
        fill_limit = "pipeline_slots"
    else:
        fill_limit = "batch"
    dynamic_energy_per_token = terms.energy_j / max(microbatch, 1e-30)
    dynamic_energy_j = dynamic_energy_per_token * fill_users
    dynamic_power = dynamic_energy_j / max(raw_step_time, 1e-30)

    # **The throttle rule, and it is not the old one.**  Static power does not
    # fall when a step is stretched -- that is what makes it static -- so the
    # coolable step time is set by the DYNAMIC energy against the headroom the
    # static power leaves, not by the total power against the whole budget:
    #
    #     P(t) = P_static + E_dyn / t <= cooling_limit
    #     t    >= E_dyn / (cooling_limit - P_static)
    #
    # The old expression divided the total energy by the total limit, so
    # throttling always reduced modelled power and every design was coolable at
    # some speed.  With a static term that is false, and it is false in a way
    # that matters: if the leakage and the clock tree alone exceed the cooling
    # budget the part cannot be run at ANY speed, and the honest answer is that
    # the design does not exist rather than that it runs slowly.  That is dark
    # silicon in its strongest form and the model can now express it.
    static_power_w = budget.static_power.total_w
    cooling_headroom_w = budget.cooling_limit_w - static_power_w
    cooling_infeasible = cooling_headroom_w <= 0.0
    if cooling_infeasible:
        reasons.append(
            f"COOLING: traffic-independent power {static_power_w:,.1f} W (leakage "
            f"{budget.static_power.leakage_w:,.1f} W + clock "
            f"{budget.static_power.clock_w:,.1f} W + memory interface "
            f"{budget.static_power.memory_interface_w:,.1f} W) already meets or "
            f"exceeds the {budget.cooling_limit_w:,.1f} W this silicon can shed, "
            "so no step time makes this design coolable"
        )
        # Reported unthrottled, because throttling cannot help: the numbers
        # below are what the design WOULD draw, and the point is that they are
        # above the budget at every step time.  Reporting infinities instead
        # would hide the size of the violation, which is the only interesting
        # thing about it.
        thermal_scale = 1.0
        step_time = raw_step_time
        power = static_power_w + dynamic_energy_j / max(step_time, 1e-30)
        energy_j = power * step_time
        energy_per_token = energy_j / max(fill_users, 1e-30)
    else:
        thermal_floor_s = dynamic_energy_j / cooling_headroom_w
        thermal_scale = max(1.0, thermal_floor_s / max(raw_step_time, 1e-30))
        step_time = raw_step_time * thermal_scale
        power = static_power_w + dynamic_energy_j / max(step_time, 1e-30)
        # Energy per token now includes the static share amortised over the
        # tokens the step actually produces, which is the only definition that
        # is comparable across two machines with different fixed costs.
        energy_j = power * step_time
        energy_per_token = energy_j / max(fill_users, 1e-30)

    fused_compute = (
        budget.weight_store == "rom"
        and budget.weight_amortization in COMPUTE_IN_ROM_POLICIES
    )
    # Every term here is on **one user's critical path**: the service terms are
    # the per-slot cost multiplied by the slots the token traverses, and the
    # link and fixed terms are already counted per token.  Scaling the three
    # service terms together leaves the overlap rule intact, because max() and
    # + both commute with a positive scalar.
    component_times = {
        "weight_read": terms.weight_time_s * slots,
        "kv_read": terms.kv_time_s * slots,
        # In a compute-in-ROM fabric the arithmetic is the sweep, so reporting a
        # separate compute time would name a component that cannot bind and
        # would break the invariant that the step is at least its largest part.
        # The MACs still happen; they take exactly as long as the walk.
        "compute": (terms.weight_time_s if fused_compute else terms.compute_time_s)
        * slots,
        "link_latency": terms.link_time_s,
        "layer_fixed_latency": fixed_latency,
    }
    if reasons:
        binding = "cooling" if cooling_infeasible else "capacity_or_format"
        per_user = 0.0
        aggregate = 0.0
        delivered = 0.0
        throughput_view_rate = 0.0
    else:
        if thermal_scale > 1.0 + 1e-12:
            binding = "thermal"
        else:
            binding = max(component_times, key=lambda key: component_times[key])
        per_user = 1.0 / step_time
        # **No longer batch x per_user.**  The machine reaches this rate only
        # when every slot has a user in it; with fewer users the surplus slots
        # idle and the machine delivers ``delivered_tokens_s`` instead.
        aggregate = fill_users * per_user
        delivered = batch_size * per_user
        throughput_view_rate = (
            1.0 / (throughput_view_step_time * thermal_scale)
            if throughput_view_step_time > 0
            else math.inf
        )

    hops, hop_semantics = budget.topology.hop_events(model.num_layers)
    hop_latency, link_bytes_s = technology.link(budget.topology.link)
    link_payload_bytes = terms.detail["link_payload_bytes_per_token"]
    payload_bytes = link_payload_bytes / hops if hops > 0 else 0.0
    devices = budget.topology.device_count

    metrics: dict[str, Any] = {
        "overlap_rule": terms.overlap_rule,
        "latency_rule": (
            "per-user latency is the full serial path: the service time on one "
            "slot's share of the machine, multiplied by the slots a token must "
            "traverse, plus every hop and collective on that path, none of "
            "which overlaps anything. Aggregate throughput is that latency with "
            "every slot occupied, which needs token_slots concurrent users; it "
            "is no longer batch x per-user rate"
        ),
        "token_slots": slots,
        "microbatch_per_slot": microbatch,
        "pipeline_fill_users": fill_users,
        "pipeline_fill_fraction": (
            min(1.0, batch_size / fill_users) if fill_users > 0 else 1.0
        ),
        "pipeline_fill_limited_by": fill_limit,
        "delivered_tokens_s": delivered,
        "serial_slot_multiplier": slots,
        "service_time_per_slot_s": terms.service_time_s,
        "service_time_s": service_time,
        "service_time_throughput_view_s": throughput_view.service_time_s,
        "step_time_throughput_view_s": throughput_view_step_time * thermal_scale,
        "per_user_tokens_s_throughput_view": throughput_view_rate,
        "latency_correction_x": (
            throughput_view_rate / per_user if per_user > 0 else 1.0
        ),
        "hop_events_per_token": hops,
        "hop_semantics": hop_semantics,
        "hop_latency_s": hop_latency.value,
        "link": budget.topology.link,
        "intra_link": budget.topology.inner_link,
        "intra_domain_size": budget.topology.intra_domain_size,
        "tensor_group": budget.topology.tensor_group,
        "pipeline_stages": budget.topology.stages_for(model.num_layers),
        "pipeline_stages_uncapped": budget.topology.pipeline_stages,
        "link_breakdown": terms.detail["link_breakdown"],
        "link_latency_without_stage_cap_s": terms.detail[
            "link_latency_without_stage_cap_s"
        ],
        "link_payload_bytes_per_event": float(payload_bytes),
        "link_payload_bytes_per_token": float(link_payload_bytes),
        "stored_weight_bytes": stored_weight_bytes,
        "representation_scale_vs_checkpoint": representation_scale,
        "weight_traffic_policy": weight_traffic_policy,
        "weight_amortization": budget.weight_amortization,
        "execution_format": execution_format or "checkpoint-declared",
        "engaged_weight_bytes": terms.detail["engaged_weight_bytes"],
        "engaged_weight_fraction": terms.detail["engaged_weight_fraction"],
        "effective_weight_read_bytes_s": terms.detail[
            "effective_weight_read_bytes_s"
        ],
        "peak_weight_read_bytes_s": budget.weight_read_bytes_s,
        "expert_coverage": terms.detail["expert_coverage"],
        "distinct_experts_per_layer": terms.detail["distinct_experts_per_layer"],
        "engaged_devices": terms.detail["engaged_devices"],
        "mean_engaged_devices_uncorrected": terms.detail[
            "mean_engaged_devices_uncorrected"
        ],
        "engaged_device_max_over_mean_correction": terms.detail[
            "engaged_device_max_over_mean_correction"
        ],
        "kv_native_transfer_bytes_per_step": terms.detail[
            "kv_native_transfer_bytes_per_step"
        ],
        "kv_access_granularity": kv_granularity_detail,
        "kv_access_granularity_inflation": kv_inflation,
        "kv_bank_occupancy": terms.detail["kv_bank_occupancy"],
        "kv_read_s_under_bank_locality": terms.detail[
            "kv_read_s_under_bank_locality"
        ],
        "layer_fixed_latency_s": fixed_latency,
        "layer_fixed_latency": fixed_latency_detail,
        "layer_fixed_latency_fraction_of_step": (
            fixed_latency / raw_step_time if raw_step_time > 0 else 0.0
        ),
        "kv_read_bytes_per_user_token": kv.read_bytes,
        "kv_write_bytes_per_user_token": kv.write_bytes,
        "kv_storage_bytes_per_user": kv.storage_bytes_per_user,
        "kv_transfer_bytes_per_step": terms.detail["kv_transfer_bytes_per_step"],
        "kv_transfer_bytes_per_step_throughput_view": throughput_view.detail[
            "kv_transfer_bytes_per_step"
        ],
        "resident_kv_bytes": resident_kv_bytes,
        "max_resident_users": float(max_resident_users),
        "weight_capacity_bytes": budget.weight_capacity_bytes,
        "kv_capacity_bytes": budget.kv_capacity_bytes,
        # Present only for a model that declares one, so a design evaluated
        # against a model with no resident region gains no zero column.
        **(
            {"kv_store_resident_weight_bytes": resident_kv_store_bytes}
            if resident_kv_store_bytes
            else {}
        ),
        "graded_derivations": {
            key: value.to_dict()
            for key, value in {
                **fixed_latency_provenance,
                **kv_granularity_provenance,
            }.items()
        },
        "operations_by_canonical_format": dict(
            terms.detail["operations_by_canonical_format"]
        ),
        "compute_times_s_by_format": terms.detail["compute_times_s_by_format"],
        "compute_roofs_ops_s": dict(budget.compute_ops_s),
        "memory_time_s": terms.memory_time_s * slots,
        "stage_balance_applied": terms.detail["stage_balance_applied"],
        "raw_step_time_before_thermal_s": raw_step_time,
        "energy_j_per_step": energy_j,
        "energy_j_per_token": energy_per_token,
        "dynamic_energy_j_per_step": dynamic_energy_j,
        "dynamic_energy_j_per_token": dynamic_energy_per_token,
        "dynamic_energy_breakdown_j": terms.detail["dynamic_energy_breakdown_j"],
        "dynamic_power_w_before_throttle": dynamic_power,
        "static_power_w": static_power_w,
        "static_power": budget.static_power.to_dict(),
        "static_power_fraction_of_total": (
            static_power_w / power if power > 0 else 0.0
        ),
        "cooling_limit_w": budget.cooling_limit_w,
        "cooling_headroom_w": cooling_headroom_w,
        "cooling_infeasible": cooling_infeasible,
        "power_density_w_per_mm2": (
            power / budget.silicon_area_mm2_total
            if budget.silicon_area_mm2_total > 0
            else 0.0
        ),
        "static_power_density_w_per_mm2": (
            static_power_w / budget.silicon_area_mm2_total
            if budget.silicon_area_mm2_total > 0
            else 0.0
        ),
        "power_headroom_fraction": (
            power / budget.cooling_limit_w if budget.cooling_limit_w > 0 else math.inf
        ),
        "weight_to_kv_read_ratio": (
            terms.detail["engaged_weight_bytes"]
            / (kv.read_bytes * microbatch)
            if kv.read_bytes > 0
            else math.inf
        ),
        "silicon_area_mm2_per_device": budget.silicon_area_mm2_per_device,
        "device_count": float(devices),
    }
    if budget.weight_store == "rom":
        if budget.weight_amortization == "per_stream":
            sweeps = float(microbatch)
        elif budget.weight_amortization == "per_region":
            # The busiest expert region's queue depth, not the batch and not the
            # mean region: disjoint regions run together, only co-located tokens
            # serialise, and the array waits for the deepest queue.
            sweeps = float(terms.detail["region_sweeps"])
            mean_region_passes = terms.detail["mean_region_passes"]
            metrics["region_sweep_depth_mean_uncorrected"] = (
                mean_region_passes if mean_region_passes is not None else 1.0
            )
            metrics["region_sweep_depth_max_over_mean"] = (
                sweeps / mean_region_passes if mean_region_passes else 1.0
            )
        else:
            sweeps = 1.0
        metrics["rom_sweeps_per_step"] = float(sweeps)
        # Under spare_area_policy="rom" the array is grown past the bytes it
        # must hold and the extra silicon carries replicated copies, so this
        # is above 1.0 by exactly the replication factor.  Under "sram" it is
        # 1.0 and the check that used to be tautological is now an identity
        # only because the array is sized to fit -- and it fails when it cannot.
        metrics["rom_replication_factor"] = (
            budget.weight_capacity_bytes / stored_weight_bytes
            if stored_weight_bytes > 0
            else 1.0
        )
        # The sweep a single slot performs.  A token traverses ``token_slots``
        # of them, which is what ``component_times_s["weight_read"]`` reports.
        metrics["rom_full_array_sweep_time_s"] = (
            sweeps * stored_weight_bytes / budget.weight_read_bytes_s
            if budget.weight_read_bytes_s > 0
            else math.inf
        )
        metrics["rom_serial_sweep_time_s"] = (
            metrics["rom_full_array_sweep_time_s"] * slots
        )
        metrics["rom_sweep_ceiling_tokens_s"] = (
            1.0 / metrics["rom_serial_sweep_time_s"]
            if metrics["rom_serial_sweep_time_s"] > 0
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
    intra_link: str = ""
    tensor_group: int = 1
    pipeline_stages: int = 1
    breakdown: tuple[str, ...] = ()

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
    hop_latency, _link_bytes_s = technology.link(topology.link)
    per_token, breakdown, _payload = technology.link_time_s(
        topology,
        model.num_layers,
        activation_bytes=batch_size * model.hidden_size * 2.0,
    )
    viable = budget_fraction / per_token if per_token > 0 else math.inf
    ceiling = 1.0 / per_token if per_token > 0 else math.inf
    return LatencyCrossover(
        topology=topology.kind,
        device_count=topology.device_count,
        parallelism=topology.parallelism,
        link=topology.link,
        intra_link=topology.inner_link,
        tensor_group=topology.tensor_group,
        pipeline_stages=topology.stages_for(model.num_layers),
        hop_events_per_token=hops,
        hop_latency_s=hop_latency.value,
        link_latency_s_per_token=per_token,
        budget_fraction=budget_fraction,
        viable_tokens_s=viable,
        hard_ceiling_tokens_s=ceiling,
        breakdown=tuple(
            f"{detail['count']:,.0f} x {detail['kind']} span {detail['span']} on "
            f"{detail['link']} (traversals {detail['collective_traversals']:.1f}) = "
            f"{detail['seconds'] * 1e6:,.2f} us"
            for detail in breakdown
        ),
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

    # Every term in the per-layer latency block is ``assumed`` and carries a
    # range.  Reporting the gate at one point inside a wide band invites the
    # reader to read the point as measured, and that is how a gate turns into a
    # fit.  The band is what the reader is asked to believe.
    band: dict[str, Any] = {}
    for bound in ("low", "stated", "high"):
        variant = (
            technology
            if bound == "stated"
            else technology.at_layer_latency_bound(bound)
        )
        fixed_s, fixed_detail, _ = layer_fixed_latency(variant, model)
        bound_step = evaluate(
            budget,
            model,
            context_tokens=context_tokens,
            batch_size=batch,
            technology=variant,
            weight_bits_per_parameter=weight_bits_per_parameter,
            execution_format=str(spec["execution_format_name"]),
        )
        band[bound] = {
            "layer_fixed_latency_s_per_layer": fixed_detail["seconds_per_layer"],
            "layer_fixed_latency_s_per_token": fixed_s,
            "modelled_tokens_s": bound_step.per_user_tokens_s,
            "ratio_to_published": (
                bound_step.per_user_tokens_s / published.value
                if published.value
                else math.inf
            ),
            "binding_constraint": bound_step.binding_constraint,
        }
    # What a per-layer cost WOULD have to be to close the remaining gap. It is
    # reported so the reader can see how far the derived value sits from the
    # fitted one, and it is never used as an input.
    gap_s = 1.0 / published.value - (
        step.step_time_s - step.component_times_s["layer_fixed_latency"]
    )
    band["per_layer_cost_that_would_close_the_gap_s"] = (
        gap_s / model.num_layers if model.num_layers else math.inf
    )
    band["note"] = (
        "The per-layer latency terms are derived from primitives independent of "
        "this anchor -- SRAM access time, sequencer issue and decode, pipeline "
        "fill and drain across a dependent array-pass boundary, the layer "
        "barrier, and a floorplan-derived on-die wire delay -- and are reported "
        "at both ends of their stated range. A negative "
        "'per_layer_cost_that_would_close_the_gap_s' means the model is already "
        "slower than the shipping part before any fixed cost is charged, so no "
        "value of this term could have closed the gap and the residual lies "
        "elsewhere."
    )

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
            "layer_fixed_latency_band": band,
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


def a100_power_anchor(
    technology: Technology,
    *,
    part: str = "a100_sxm_80gb",
    roof_format: str = "bf16",
    tolerance: float = 2.0,
) -> AnchorCheck:
    """A published GPU against its published TDP, under a saturating load.

    A TDP is not a decode step's draw; it is what the part is built to shed
    when something is driving it hard.  The operating point is therefore
    synthetic and stated rather than taken from a workload: **every byte of
    published HBM bandwidth moving and the published dense tensor roof issuing,
    at the same time, for one second**, on top of the traffic-independent
    power.  That is the same check
    ``docs/TECHNICAL_DIRECTION_RECOMMENDATION.md`` 0.11 used to show the old
    power model's shortfall was structural rather than an activity factor: it
    produced 85.3 W against 400 W then, and an activity-factor error would have
    closed at peak.

    **This gate is weaker than it looks and the reason must travel with it.**
    ``power.clock_energy_j_per_mm2_per_cycle`` was calibrated as 20-45% of a
    shipping GPU's published TDP density.  It is a different GPU -- P100 and
    GV100, not this part -- but it is still a GPU TDP, so a gate that adds that
    term to the others and compares the sum with a GPU TDP is partly checking
    an input against its own family.  What it does test independently is
    whether the traffic terms, the arithmetic and the static terms are
    mutually consistent in SIZE, and it would fail loudly if any of them were
    an order of magnitude out.  The Taalas gate beside it has no such
    circularity and is the stronger of the two.
    """

    ideal = technology.ideal()
    topology = Topology(
        kind="single_chip", device_count=1, parallelism="none", link="none"
    )
    budget = gpu_device_budget(ideal, part=part, topology=topology, name=f"{part}-x1")
    spec = technology.reference_part(part)
    published = Graded.from_dict(spec["power_w"])

    hbm_energy = technology.graded("energy", "hbm_j_per_byte")
    operand = technology.graded("energy", "operand_delivery_j_per_byte")
    mac = technology.mac_energy_j_per_op(roof_format)
    saturating_bytes_s = budget.weight_read_bytes_s
    roof_ops_s = budget.compute_ops_s[roof_format]

    traffic_w = saturating_bytes_s * hbm_energy.value
    operand_w = saturating_bytes_s * operand.value
    arithmetic_w = roof_ops_s * mac.value
    static = budget.static_power
    modelled = traffic_w + operand_w + arithmetic_w + static.total_w
    ratio = modelled / published.value if published.value else math.inf

    return AnchorCheck(
        name="a100_tdp_power_w",
        published_value=published.value,
        modelled_value=modelled,
        ratio=ratio,
        tolerance=tolerance,
        passed=(1.0 / tolerance) <= ratio <= tolerance,
        detail={
            "part": part,
            "die_area_mm2": budget.silicon_area_mm2_total,
            "operating_point": (
                f"saturating: {saturating_bytes_s:,.0f} B/s of published HBM "
                f"bandwidth and {roof_ops_s:,.0f} ops/s of published dense "
                f"{roof_format} roof, simultaneously"
            ),
            "saturating_bytes_s": saturating_bytes_s,
            "roof_ops_s": roof_ops_s,
            "terms_w": {
                "hbm_traffic": traffic_w,
                "operand_delivery": operand_w,
                "arithmetic": arithmetic_w,
                "static_leakage": static.leakage_w,
                "static_clock": static.clock_w,
                "static_memory_interface": static.memory_interface_w,
                "static_total_charged": static.total_w,
            },
            "static_power": static.to_dict(),
            "power_density_w_per_mm2": modelled / budget.silicon_area_mm2_total,
            "published_power_density_w_per_mm2": (
                published.value / budget.silicon_area_mm2_total
            ),
            "clock_frequency_hz": static.clock_frequency_hz,
            "circularity_warning": (
                "power.clock_energy_j_per_mm2_per_cycle is 20-45% of a shipping "
                "GPU's published TDP density evaluated at that part's published "
                "clock. Comparing a sum containing that term with a GPU's TDP is "
                "not a fully independent test, and this gate must never be quoted "
                "as one."
            ),
        },
    )


def taalas_hc1_power_anchor(
    technology: Technology,
    model: ModelProfile,
    *,
    tolerance: float = 2.0,
    published_low_w: float | None = None,
) -> AnchorCheck:
    """The shipping Taalas HC1's published card power at its published point.

    This one has no circularity in it: nothing in the ROM side's power -- the
    ROM read primitive, the operand-delivery scalar, the array clock multiplier
    or the leakage over a solved area split -- was calibrated on a Taalas
    figure, because Taalas publishes no microarchitecture and no energy at all.
    It is therefore the stronger of the two power gates and it is the one that
    fails.

    The operating point is not chosen either: it is exactly the point the
    throughput gate already evaluates, obtained by reading that gate's own step
    rather than rebuilding it, so the two cannot drift apart.
    """

    throughput = taalas_hc1_anchor(technology, model)
    step = throughput.detail["step"]
    spec = technology.reference_part("taalas_hc1")
    published = Graded.from_dict(spec["power_w"])
    low = (
        published_low_w
        if published_low_w is not None
        else float(spec["power_w"].get("range_low", published.value))
    )
    modelled = float(step["power_w"])
    ratio = modelled / published.value if published.value else math.inf

    metrics = step["metrics"]
    static = metrics["static_power"]
    rom_mm2 = float(throughput.detail["area_split_mm2"]["rom_mm2"])
    rom_leakage = technology.graded(
        "power", "static_leakage_w_per_mm2", "rom_array"
    )
    rom_leakage_node = technology.raw["power"]["static_leakage_w_per_mm2"][
        "rom_array"
    ]
    rom_leakage_high = float(
        rom_leakage_node.get("range_high", rom_leakage.value)
    )
    return AnchorCheck(
        name="taalas_hc1_card_power_w",
        published_value=published.value,
        modelled_value=modelled,
        ratio=ratio,
        tolerance=tolerance,
        passed=(1.0 / tolerance) <= ratio <= tolerance,
        detail={
            "published_band_w": [low, published.value],
            "ratio_to_band_low": modelled / low if low else math.inf,
            "ratio_to_band_high": ratio,
            "shortfall_x_against_band": [
                published.value / modelled if modelled else math.inf,
                low / modelled if modelled else math.inf,
            ],
            "operating_point": (
                "the same point the HC1 throughput gate evaluates: "
                f"{throughput.detail['context_tokens']} tokens of context at batch "
                f"{throughput.detail['batch_size']}, "
                f"{throughput.detail['weight_bits_per_parameter']} bits per "
                f"parameter, {throughput.detail['execution_format']}"
            ),
            "modelled_tokens_s": throughput.modelled_value,
            "energy_j_per_token": metrics["energy_j_per_token"],
            "terms_w": {
                "dynamic_total": modelled - metrics["static_power_w"],
                "static_total_charged": metrics["static_power_w"],
                "static_leakage": static["leakage_w"],
                "static_clock": static["clock_w"],
                "static_memory_interface": static["memory_interface_w"],
                "static_enumerated": static["enumerated_w"],
                "static_clocked_idle_floor": static["floor_w"],
                "static_floor_binds": static["floor_binds"],
            },
            "dynamic_energy_breakdown_j_per_step": metrics[
                "dynamic_energy_breakdown_j"
            ],
            # The same breakdown as watts, so the report is not the only place
            # that division happens and the figures in it are checkable against
            # an artifact rather than against a renderer.  One step's energy
            # covers ``microbatch_per_slot`` users and the machine produces
            # ``pipeline_fill_users`` of them per step time.
            "dynamic_power_w_by_term": {
                name: value
                * metrics["pipeline_fill_users"]
                / max(metrics["microbatch_per_slot"], 1e-30)
                / max(float(step["step_time_s"]), 1e-30)
                for name, value in metrics["dynamic_energy_breakdown_j"].items()
            },
            "power_density_w_per_mm2": metrics["power_density_w_per_mm2"],
            "cooling_limit_w": metrics["cooling_limit_w"],
            "area_split_mm2": throughput.detail["area_split_mm2"],
            "rom_array_leakage_charged_w": rom_mm2 * rom_leakage.value,
            "rom_array_leakage_at_range_high_w": rom_mm2 * rom_leakage_high,
            "note": (
                "The ROM array is charged its stated leakage density. The "
                "charge moves the enumerated static estimate just above the "
                "measured whole-device clocked-idle floor at this point, so it "
                "is included in static_total_charged. The watts the array would "
                "contribute at its range-high density are reported in "
                "'rom_array_leakage_at_range_high_w'."
            ),
        },
    )
