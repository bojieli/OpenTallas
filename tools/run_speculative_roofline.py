#!/usr/bin/env python3
"""Apply a speculative-decoding layer to the roofline artifacts already produced.

**This tool computes nothing new about the machine.**  It reads the committed
``results/roofline/**/analytical.json`` written by ``tools/run_roofline_studies.py``,
recovers the five terms of each point's critical path exactly, and re-assembles
them for a speculative cycle.  It never calls ``opentallas.roofline.evaluate``,
never imports the study driver, and never writes anywhere except
``results/roofline/speculative/``.

Why a separate tool rather than an option on the study driver: the study driver
owns every published figure and takes nine minutes.  Everything the speculative
arithmetic needs is already in the artifact, exactly, and the gate below proves
it -- so this layer is additive by construction and a stale artifact is a
refusal rather than a silent mixture.

THE ARITHMETIC, in the terms of DFlash equation (1)
---------------------------------------------------
``L = (T_draft + T_verify) / tau``, ``speedup = L_target / L``, with ``tau`` in
``[1, gamma+1]`` the expected accepted tokens per cycle INCLUDING the target's
bonus token.  Write ``n = gamma + 1`` for the positions one verification pass
carries.  For a point ``p`` and its design ``d``, with ``W, K, C, Lk, F`` the
five entries of ``p.component_times_s`` (already multiplied by ``token_slots``):

* ``bal``  = ``stage_balance`` when ``device_count > 1 and parallelism != "none"``, else 1
* ``M0``   = ``W + K`` if ``d.shared_memory_path`` else ``max(W, K)``
* ``S``    = ``max(M0, C)/bal``, the sweep a token waits for, and
  ``T0``   = ``max(S, P(mb, S)) * p.thermal_scale`` -- and this MUST equal
  ``p.step_time_s``.  ``P(mb, S)`` is the longest path of the token's operator
  graph (``opentallas.critical_path``) at the point's own microbatch with ``S``
  spread over its operators, plus its pipeline hops: ``Lk + F + sweep on the
  path``.  It is checked on every feasible point before any
  speculative arithmetic runs; a failure stops the run, because it means this
  layer has misread the model rather than that the point is odd.

The verification pass carries ``n`` positions on one pass through the weights:

* ROM, ``batched``:    ``W_v = W * infl``            (one sweep serves the block, as it serves a batch)
* ROM, ``per_stream``: ``W_v = W * infl * n``        (compute-in-ROM: each position is its own pass)
* ROM, ``per_region``: ``W_v = W * infl * R(mb*n)/R(mb)``
* HBM:                 ``W_v = W * t(mb*n)/t(mb)``   (the union of routed experts widens with the block)
* ``K_v = K * (read + n*write)/(read + write)`` -- the block shares one prefix, so the
  context is read ONCE per cycle and only the writes multiply
* ``C_v = C * n`` -- exact under the model's own convention, ``_scaled_operations``
  being linear in ``effective_batch``
* the verification pass is ``max(S_v, P(mb*n, S_v))``: the same operator graph with
  ``n`` positions riding every operator, so every collective and hop payload and
  every vector op's issue scale with ``n`` and every latency is paid once

The draft pass is the same machine under the same rules with the drafter's own
numbers, and on a ROM machine it is where the locality rule bites: ``t =
stored/peak`` is a technology constant, so a pass that touches only the
drafter's region still takes a full-array sweep.

Nothing here invents an acceptance rate.  The headline is the BREAK-EVEN
acceptance ``tau* = T_cycle / step_time_s``: speculation pays iff ``tau >= tau*``,
and ``tau <= gamma+1`` always, so ``tau* > gamma+1`` at every gamma is a
parameter-free verdict that speculation cannot pay on that design at any
acceptance rate.  A speedup is published only where a tau is sourced, and it is
labelled with the model and the hardware that tau was measured on.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from opentallas import critical_path as serial_graph  # noqa: E402
from opentallas.roofline import (  # noqa: E402
    Technology,
    effective_engaged_devices,
    expected_max_region_load,
)
from opentallas.schema import ModelProfile  # noqa: E402
from opentallas.workload import (  # noqa: E402
    draft_weight_traffic,
    expected_expert_coverage,
    kv_traffic,
)

PROFILE_PATH = ROOT / "configs" / "studies" / "speculative_profiles.json"
TECHNOLOGY_PATH = ROOT / "configs" / "hardware" / "technology.json"
SOURCE_ROOT = ROOT / "results" / "roofline"
OUTPUT_ROOT = ROOT / "results" / "roofline" / "speculative"

#: The two amortisation policies in which the ROM cell both stores and
#: multiplies, so the arithmetic IS the sweep and cannot be put in a max()
#: against it.  Mirrors ``roofline.COMPUTE_IN_ROM_POLICIES``; named here rather
#: than imported so a change on that side shows up as a gate failure.
COMPUTE_IN_ROM_POLICIES = ("per_stream", "per_region")

TOPOLOGY_FIELDS = (
    "kind",
    "device_count",
    "parallelism",
    "link",
    "on_wafer_regions",
    "intra_link",
    "intra_domain_size",
    "tensor_group_size",
    "moe_fanout",
)

RECONSTRUCTION_TOLERANCE = 1e-9


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------



def _load_study_artifact(path):
    """A roofline study as one dict: ``analytical.json`` plus its ``points.json``
    shard and the de-duplicated design provenance (see
    ``opentallas.roofline.load_study_artifact``, which this mirrors so the tool
    stays standard-library only)."""

    path = Path(path)
    body = json.loads(path.read_text())
    shard = body.pop("points_file", None)
    if shard:
        body["points"] = json.loads((path.parent / shard).read_text())
    table = body.pop("provenance_table", None)
    if table:
        for design in body.get("designs", ()):
            reference = design.get("provenance")
            if isinstance(reference, str) and reference in table:
                design["provenance"] = table[reference]
    return body

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _close(left: float, right: float, tolerance: float = RECONSTRUCTION_TOLERANCE) -> bool:
    scale = max(abs(left), abs(right), 1e-30)
    return abs(left - right) <= tolerance * scale


#: Memo caches.  This layer evaluates the same coverage, region-load and
#: engaged-device statistics thousands of times over the same handful of
#: (experts, draws) pairs; the caches make the pass a few seconds instead of a
#: few minutes and change no value.  Keys are exact, so the result is identical
#: with or without them.
_COVERAGE_CACHE: dict[tuple[int, int, float], float] = {}
_REGION_CACHE: dict[tuple[int, int, float], float] = {}
_DEVICES_CACHE: dict[tuple[int, float], float] = {}


def _coverage(num_experts: int, experts_per_token: int, samples: float) -> float:
    key = (num_experts, experts_per_token, samples)
    value = _COVERAGE_CACHE.get(key)
    if value is None:
        value = expected_expert_coverage(num_experts, experts_per_token, samples)
        _COVERAGE_CACHE[key] = value
    return value


def _region_load(num_experts: int, draws: float, experts_per_token: int) -> float:
    key = (num_experts, experts_per_token, draws)
    value = _REGION_CACHE.get(key)
    if value is None:
        value = expected_max_region_load(num_experts, draws, experts_per_token)
        _REGION_CACHE[key] = value
    return value


def _engaged_devices(device_count: int, distinct_experts: float) -> float:
    key = (device_count, distinct_experts)
    value = _DEVICES_CACHE.get(key)
    if value is None:
        value = effective_engaged_devices(device_count, distinct_experts)
        _DEVICES_CACHE[key] = value
    return value


# --------------------------------------------------------------------------
# the drafter
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Drafter:
    """What one profile's drafter costs, in this repository's own byte counts."""

    profile: str
    model: str
    layers: int
    #: Bytes streamed by one draft pass, before the design's representation scale.
    dense_bytes: float
    routed_bytes: float
    #: Bytes the drafter OCCUPIES, which is not the same thing: a shared
    #: embedding and LM head are read by the draft pass and stored once.
    stored_bytes: float
    #: True when those stored bytes are already inside the target's
    #: ``stored_weight_bytes``, which for a mask-ROM design they are whenever the
    #: released checkpoint ships the drafter.
    already_in_checkpoint: bool
    block_passes: float
    sequential_passes_per_draft_token: float
    grade: str
    source: str
    note: str

    @property
    def extra_stored_bytes(self) -> float:
        """Bytes the array must hold that it is not already holding.

        Zero whenever the released checkpoint ships the drafter, because the
        study driver stores the whole checkpoint: the design is already paying
        for these bytes on every ordinary decode token.
        """

        return 0.0 if self.already_in_checkpoint else self.stored_bytes


def build_drafter(profile_name: str, profile: dict, model: ModelProfile) -> Drafter | None:
    """The drafter this profile puts on this model, or None if it has none."""

    params = profile["parameters"]
    if profile["drafter_family"] == "mtp_stack_with_sequential_markov_bias":
        dense = float(model.draft_dense_weight_bytes)
        routed = float(model.draft_routed_weight_bytes)
        if dense + routed <= 0:
            return None
        return Drafter(
            profile=profile_name,
            model=model.name,
            layers=int(params["draft_stages"]["value"]),
            dense_bytes=dense,
            routed_bytes=routed,
            stored_bytes=dense + routed,
            # The released checkpoint holds the MTP stack, and
            # ``_rom_stored_bytes`` in the study driver stores the WHOLE
            # checkpoint, so a mask-ROM design in the published artifact is
            # already sweeping these bytes on every ordinary decode token.
            already_in_checkpoint=True,
            block_passes=float(params["draft_block_passes"]["value"]),
            sequential_passes_per_draft_token=float(
                params["draft_sequential_passes_per_draft_token"]["value"]
            ),
            grade=params["draft_weight_bytes_source"]["grade"],
            source=params["draft_weight_bytes_source"]["source"],
            note=(
                "Draft bytes are the released checkpoint's own MTP inventory, "
                "already counted in this design's stored bytes."
            ),
        )
    if profile["drafter_family"] == "block_diffusion_parallel":
        layers = int(params["draft_layers"]["value"])
        per_layer = model.layer_dense_weight_bytes
        if not per_layer:
            return None
        stored = float(per_layer[0]) * layers
        shared = float(model.resident_only_weight_bytes)
        return Drafter(
            profile=profile_name,
            model=model.name,
            layers=layers,
            dense_bytes=stored + shared,
            routed_bytes=0.0,
            stored_bytes=stored,
            already_in_checkpoint=False,
            block_passes=float(params["draft_block_passes"]["value"]),
            sequential_passes_per_draft_token=float(
                params["draft_sequential_passes_per_draft_token"]["value"]
            ),
            grade=params["drafter_derivation_when_absent"]["grade"],
            source=params["drafter_derivation_when_absent"]["source"],
            note=params["drafter_derivation_when_absent"]["note"],
        )
    raise SystemExit(f"unknown drafter_family in profile {profile_name!r}")


# --------------------------------------------------------------------------
# the weight-path physics, recovered from the artifact
# --------------------------------------------------------------------------


def _sweeps(amortization: str, num_experts: int, experts_per_token: int, draws: float, imbalance: float) -> float:
    """ROM passes through the array for ``draws`` concurrent position-samples."""

    if amortization == "batched":
        return 1.0
    if amortization == "per_stream":
        return float(draws)
    passes = _region_load(max(1, num_experts), draws, max(1, experts_per_token))
    passes *= max(imbalance, 1e-9)
    return min(max(1.0, passes), float(draws))


def _engaged_bytes(
    dense: float,
    routed: float,
    *,
    amortization: str,
    weight_store: str,
    draws: float,
    scale: float,
    num_experts: int,
    experts_per_token: int,
    imbalance: float,
    in_array: bool = True,
) -> float:
    """Weight bytes a pass set actually engages, at the design's representation.

    ``in_array`` says whether the pass actually goes through the mask-ROM
    fabric.  The compute-in-ROM sweep multiplier is a property of THAT PATH: it
    exists because the multiply is the sweep.  A tensor held outside the array
    -- the drafter under the ``in_kv_store`` placement -- is read over an
    ordinary bandwidth path and is charged one read of ``dense + routed *
    coverage(draws)``, exactly as the ``in_hbm`` branch charges it.  Multiplying
    that read by the array's sweep count would charge a fabric cost to a
    transfer that never touches the fabric.
    """

    if in_array and weight_store == "rom" and amortization in COMPUTE_IN_ROM_POLICIES:
        per_stream = dense + routed * _coverage(num_experts, experts_per_token, 1)
        passes = _sweeps(amortization, num_experts, experts_per_token, draws, imbalance)
        return scale * per_stream * passes
    coverage = _coverage(num_experts, experts_per_token, draws) if routed > 0 else 0.0
    return scale * (dense + routed * coverage)


def _hbm_weight_time(
    dense: float,
    routed: float,
    *,
    draws: float,
    scale: float,
    num_experts: int,
    experts_per_token: int,
    peak_bytes_s: float,
    devices: int,
) -> float:
    """Seconds a global-bandwidth machine spends fetching one pass's weights."""

    seconds = dense * scale / max(peak_bytes_s, 1e-30)
    if routed > 0:
        coverage = _coverage(num_experts, experts_per_token, draws)
        engaged = _engaged_devices(devices, num_experts * coverage)
        per_device = peak_bytes_s / max(1, devices)
        seconds += routed * scale * coverage / max(engaged * per_device, 1e-30)
    return seconds


# --------------------------------------------------------------------------
# one point
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Baseline:
    """The autoregressive point, decomposed and checked."""

    weight_s: float
    kv_s: float
    compute_s: float
    link_s: float
    fixed_s: float
    balance: float
    fused_compute: bool
    shared_memory_path: bool
    slots: float
    microbatch: float
    scale: float
    link_latency_only_s: float
    link_transfer_s: float
    step_time_s: float
    raw_step_time_s: float
    thermal_scale: float
    engaged_weight_bytes: float
    kv_read_bytes: float
    kv_write_bytes: float


def _row_machine(point: dict, microbatch: float) -> tuple[Any, tuple | None]:
    """The machine a published point's serial path was priced on, at ``microbatch`` users per slot."""

    single = point["topology_kind"] == "single_chip" or point["parallelism"] == "none"
    expert = point["parallelism"] == "expert"
    parts = int(point["device_count"])
    machine = serial_graph.MachineSpec(
        family=point["family"],
        group=1 if single else int(point["tensor_group"]),
        microbatch=float(microbatch),
        clock_hz=float(point["serial_clock_hz"]),
        su_width=int(point["stream_unit_width"] or 16),
        kv_in_hbm=point["kv_store"] == "hbm",
        multi_stage=int(point["pipeline_stages"]) > 1,
        expert_parallel=expert,
        ep_span=parts if expert else 1,
        ep_tokens_per_node=float(microbatch) / parts if expert else 0.0,
    )
    links = None if single else (
        point["intra_link"], point["link"], int(point["intra_domain_size"]), parts if expert else 0
    )
    return machine, links


def serial_path(point: dict, model: ModelProfile, technology: Technology, microbatch: float,
                sweep_s: float) -> tuple[float, float, float]:
    """(path, collectives-and-hops on it, sweep on it) of one token at ``microbatch`` users per slot."""

    machine, links = _row_machine(point, microbatch)
    context = int(point["context_tokens"])
    compiled, _summary = serial_graph.serial_compiled(
        technology, model, context_tokens=context, machine=machine, fabric_links=links
    )
    share = float(point["serial_kv_share_of_sweep"])
    path, comm, sweep = compiled.solve(sweep_s * (1.0 - share), sweep_s * share)
    hops = serial_graph.price_stage_hops(
        technology,
        serial_graph.decode_shape(model, context),
        stages=int(point["pipeline_stages"]),
        fabric_links=links,
        group=machine.group,
        microbatch=float(microbatch),
    )
    hop = hops["latency_s"] + hops["bytes_s"]
    return path + hop, comm + hop, sweep


def decompose(point: dict, design: dict, model: ModelProfile, technology: Technology, kv, balance_value: float) -> tuple[Baseline, list[str]]:
    """Recover every term of one published point, and check it reproduces."""

    problems: list[str] = []
    times = point["component_times_s"]
    weight = float(times["weight_read"])
    kv_time = float(times["kv_read"])
    compute = float(times["compute"])
    link = float(times["link_latency"])
    fixed = float(times["layer_fixed_latency"])
    slots = float(point["token_slots"])
    microbatch = float(point["microbatch_per_slot"])
    fused = point["weight_store"] == "rom" and point["weight_amortization"] in COMPUTE_IN_ROM_POLICIES
    shared = bool(design["shared_memory_path"])
    balance = balance_value if (point["device_count"] > 1 and point["parallelism"] != "none") else 1.0

    memory = weight + kv_time if shared else max(weight, kv_time)
    service = max(weight, kv_time) if fused else max(memory, compute)
    sweep = service / balance
    thermal = float(point["thermal_scale"])
    path, comm, sweep_on_path = serial_path(point, model, technology, microbatch, sweep)
    rebuilt = max(sweep, path) * thermal
    if not _close(rebuilt, float(point["step_time_s"])):
        problems.append(
            f"{point['design']} @ batch {point['batch_size']}: step time reconstructs to "
            f"{rebuilt:.12e} against the published {point['step_time_s']:.12e}"
        )
    if not _close(comm, link) or not _close(path - comm - sweep_on_path, fixed, 1e-6):
        problems.append(
            f"{point['design']} @ batch {point['batch_size']}: serial terms reconstruct to "
            f"link {comm:.12e} / chain {path - comm - sweep_on_path:.12e} against the published "
            f"{link:.12e} / {fixed:.12e}"
        )

    # The link term split into what one more microbatch of positions adds to
    # it (its payloads) and what it does not (its latencies): the operator
    # graph re-priced at twice the users per slot.
    _p2, comm2, _s2 = serial_path(point, model, technology, 2.0 * microbatch, sweep)
    transfer = max(0.0, comm2 - comm)

    # The representation scale, solved from the point's own engaged bytes.
    unit = _engaged_bytes(
        model.dense_weight_bytes,
        model.routed_weight_bytes,
        amortization=point["weight_amortization"],
        weight_store=point["weight_store"],
        draws=microbatch,
        scale=1.0,
        num_experts=model.num_experts,
        experts_per_token=model.experts_per_token,
        imbalance=technology.efficiency("expert_router_imbalance").value,
    )
    scale = float(point["engaged_weight_bytes"]) / unit if unit > 0 else 1.0

    return (
        Baseline(
            weight_s=weight,
            kv_s=kv_time,
            compute_s=compute,
            link_s=link,
            fixed_s=fixed,
            balance=balance,
            fused_compute=fused,
            shared_memory_path=shared,
            slots=slots,
            microbatch=microbatch,
            scale=scale,
            link_latency_only_s=max(0.0, link - transfer),
            link_transfer_s=transfer,
            step_time_s=float(point["step_time_s"]),
            raw_step_time_s=float(point["step_time_s"]) / max(thermal, 1e-30),
            thermal_scale=thermal,
            engaged_weight_bytes=float(point["engaged_weight_bytes"]),
            kv_read_bytes=float(kv.read_bytes),
            kv_write_bytes=float(kv.write_bytes),
        ),
        problems,
    )


def _service(weight: float, kv_time: float, compute: float, base: Baseline) -> float:
    memory = weight + kv_time if base.shared_memory_path else max(weight, kv_time)
    if base.fused_compute:
        return max(weight, kv_time)
    return max(memory, compute)


def speculative_cycle(
    point: dict,
    design: dict,
    model: ModelProfile,
    technology: Technology,
    base: Baseline,
    drafter: Drafter | None,
    gamma: int,
    placement: str,
    draft_kv_share: float,
) -> dict:
    """One speculative cycle: verify n positions, then draft the next block.

    ``draft_kv_share`` selects the end of the unsourced drafter-KV band: 0.0
    charges the drafter no KV traffic at all, 1.0 charges it its layer share of
    the target's KV read.  Neither is a measurement and both are published.
    """

    positions = float(gamma + 1)
    imbalance = technology.efficiency("expert_router_imbalance").value
    amortization = point["weight_amortization"]
    store = point["weight_store"]
    devices = int(point["device_count"])
    peak = float(design["weight_read_bytes_s"])
    microbatch = base.microbatch
    draws_block = microbatch * positions

    in_rom = store == "rom" and placement == "in_rom"
    inflation = 1.0
    if drafter is not None and in_rom:
        extra = drafter.extra_stored_bytes * base.scale
        stored = float(point["stored_weight_bytes"])
        inflation = (stored + extra) / stored if stored > 0 else 1.0

    # -- verification pass ------------------------------------------------
    if store == "rom":
        ratio = _sweeps(amortization, model.num_experts, model.experts_per_token, draws_block, imbalance) / _sweeps(
            amortization, model.num_experts, model.experts_per_token, microbatch, imbalance
        )
        weight_verify = base.weight_s * inflation * ratio
    else:
        block = _hbm_weight_time(
            model.dense_weight_bytes,
            model.routed_weight_bytes,
            draws=draws_block,
            scale=base.scale,
            num_experts=model.num_experts,
            experts_per_token=model.experts_per_token,
            peak_bytes_s=peak,
            devices=devices,
        )
        single = _hbm_weight_time(
            model.dense_weight_bytes,
            model.routed_weight_bytes,
            draws=microbatch,
            scale=base.scale,
            num_experts=model.num_experts,
            experts_per_token=model.experts_per_token,
            peak_bytes_s=peak,
            devices=devices,
        )
        weight_verify = base.weight_s * (block / single if single > 0 else 1.0)

    kv_total = base.kv_read_bytes + base.kv_write_bytes
    kv_ratio = (base.kv_read_bytes + positions * base.kv_write_bytes) / kv_total if kv_total > 0 else 1.0
    kv_verify = base.kv_s * kv_ratio
    compute_verify = base.compute_s * positions
    # The verification pass is the same operator graph with ``n`` positions
    # riding every operator: every payload and every vector issue scale with
    # them, every latency is paid once.
    sweep_verify = _service(weight_verify, kv_verify, compute_verify, base) / base.balance
    path_verify, link_verify, sweep_on_path_verify = serial_path(
        point, model, technology, base.microbatch * positions, sweep_verify
    )
    fixed_verify = max(0.0, path_verify - link_verify - sweep_on_path_verify)
    verify_s = max(sweep_verify, path_verify)

    # -- draft pass -------------------------------------------------------
    draft = {
        "weight_s": 0.0,
        "kv_s": 0.0,
        "compute_s": 0.0,
        "link_s": 0.0,
        "fixed_s": 0.0,
        "total_s": 0.0,
        "engaged_bytes": 0.0,
        "ops_ratio": 0.0,
        "placement_feasible": True,
        "placement_reason": "",
    }
    if drafter is not None:
        layer_share = drafter.layers / max(1, model.num_layers)
        sequential = drafter.sequential_passes_per_draft_token * float(gamma)
        draft_engaged = _engaged_bytes(
            drafter.dense_bytes,
            drafter.routed_bytes,
            amortization=amortization,
            weight_store=store,
            draws=draws_block,
            scale=base.scale,
            num_experts=model.num_experts,
            experts_per_token=model.experts_per_token,
            imbalance=imbalance,
        )
        target_engaged = _engaged_bytes(
            model.dense_weight_bytes,
            model.routed_weight_bytes,
            amortization=amortization,
            weight_store=store,
            draws=draws_block,
            scale=base.scale,
            num_experts=model.num_experts,
            experts_per_token=model.experts_per_token,
            imbalance=imbalance,
        )
        ops_ratio = draft_engaged / target_engaged if target_engaged > 0 else 0.0
        # The same drafter, priced for a read that does NOT go through the ROM
        # fabric.  Used by the ``in_kv_store`` placement, whose read is served
        # by the KV store's bandwidth and therefore cannot carry the array's
        # sweep count.  On every other point this equals ``draft_engaged``.
        draft_off_array_bytes = _engaged_bytes(
            drafter.dense_bytes,
            drafter.routed_bytes,
            amortization=amortization,
            weight_store=store,
            draws=draws_block,
            scale=base.scale,
            num_experts=model.num_experts,
            experts_per_token=model.experts_per_token,
            imbalance=imbalance,
            in_array=False,
        )

        # Every weight term below is an AGGREGATE-resource time and must be
        # multiplied by ``token_slots`` to reach one user's critical path, for
        # exactly the reason the roofline itself does it: a token is served by
        # one slot at a time and must visit every slot.  The verification terms
        # above need no such factor because they are ratios applied to
        # ``component_times_s``, which already carries it.
        slots = base.slots
        if store == "rom" and placement == "in_rom":
            # THE LOCALITY RULE.  ``t = stored/peak`` is a technology constant,
            # so a pass touching only the drafter's region takes exactly as long
            # as sweeping the whole array.  One sweep per block pass, and one
            # more per sequential bias application.
            unit_sweep = float(point["stored_weight_bytes"]) * inflation / max(peak, 1e-30)
            passes = drafter.block_passes * _sweeps(
                amortization, model.num_experts, model.experts_per_token, draws_block, imbalance
            ) + sequential
            draft["weight_s"] = unit_sweep * passes * slots
        elif store == "rom":
            # Held OUT of the array, in the KV store.  An architectural proposal
            # this study has NOT costed in silicon area.  The read is a
            # bandwidth read over ``kv_read_bytes_s`` and is charged ONCE for
            # the whole block, which is why it uses the off-array byte count:
            # a compute-in-ROM design's sweep multiplier belongs to the fabric
            # and this transfer never enters the fabric.
            kv_bandwidth = float(design["kv_read_bytes_s"])
            draft["weight_s"] = draft_off_array_bytes * drafter.block_passes / max(kv_bandwidth, 1e-30) * slots
            spare = float(point["kv_capacity_bytes"]) - float(point["resident_kv_bytes"])
            need = drafter.stored_bytes * base.scale
            if need > spare:
                draft["placement_feasible"] = False
                draft["placement_reason"] = (
                    f"the drafter needs {need:,.0f} B of the KV store and only "
                    f"{spare:,.0f} B is spare after the resident KV"
                )
        else:
            draft["weight_s"] = (
                _hbm_weight_time(
                    drafter.dense_bytes,
                    drafter.routed_bytes,
                    draws=draws_block,
                    scale=base.scale,
                    num_experts=model.num_experts,
                    experts_per_token=model.experts_per_token,
                    peak_bytes_s=peak,
                    devices=devices,
                )
                * drafter.block_passes
                * slots
            )

        draft["kv_s"] = base.kv_s * layer_share * draft_kv_share
        draft["compute_s"] = base.compute_s * positions * ops_ratio
        draft["link_s"] = (base.link_latency_only_s + base.link_transfer_s * positions) * layer_share
        draft["fixed_s"] = base.fixed_s * layer_share
        # Energy follows the same path the time follows: bytes the drafter
        # moves off-array are off-array bytes.
        draft["engaged_bytes"] = (
            draft_off_array_bytes if placement == "in_kv_store" else draft_engaged
        ) * drafter.block_passes
        draft["ops_ratio"] = ops_ratio
        if store == "rom" and placement == "in_kv_store":
            # The drafter now lives in the array the KV lives in, so its read
            # and the KV read contend rather than overlap.
            memory = draft["weight_s"] + draft["kv_s"]
            service = memory if base.fused_compute else max(memory, draft["compute_s"])
        else:
            service = _service(draft["weight_s"], draft["kv_s"], draft["compute_s"], base)
        draft["total_s"] = service / base.balance + draft["link_s"] + draft["fixed_s"]

    raw_cycle = verify_s + draft["total_s"]

    # -- energy and the throttle ------------------------------------------
    breakdown = point["dynamic_energy_breakdown_j"]
    fill_users = float(point["pipeline_fill_users"])
    per_token = {key: float(value) / max(microbatch, 1e-30) for key, value in breakdown.items()}
    weight_bytes_cycle = _engaged_bytes(
        model.dense_weight_bytes,
        model.routed_weight_bytes,
        amortization=amortization,
        weight_store=store,
        draws=draws_block,
        scale=base.scale,
        num_experts=model.num_experts,
        experts_per_token=model.experts_per_token,
        imbalance=imbalance,
    ) + draft["engaged_bytes"]
    weight_energy_ratio = weight_bytes_cycle / max(base.engaged_weight_bytes, 1e-30)
    kv_bytes_ratio = kv_ratio + (drafter.layers / max(1, model.num_layers) * draft_kv_share if drafter else 0.0)
    arithmetic_ratio = positions * (1.0 + draft["ops_ratio"])
    kv_bytes_base = float(point["kv_transfer_bytes_per_step"])
    weight_plus_kv_base = base.engaged_weight_bytes + kv_bytes_base
    operand_ratio = (
        (weight_bytes_cycle + kv_bytes_base * kv_bytes_ratio) / weight_plus_kv_base
        if weight_plus_kv_base > 0
        else 1.0
    )
    ratios = {
        "weight_read_j": weight_energy_ratio,
        "kv_read_j": kv_bytes_ratio,
        "arithmetic_j": arithmetic_ratio,
        "operand_delivery_j": operand_ratio,
    }
    cycle_energy_j = fill_users * sum(per_token[key] * ratios.get(key, 1.0) for key in per_token)
    headroom = float(point["cooling_limit_w"]) - float(point["static_power_w"])
    if headroom > 0:
        thermal = max(1.0, (cycle_energy_j / headroom) / max(raw_cycle, 1e-30))
    else:
        thermal = 1.0
    cycle_s = raw_cycle * thermal

    components = {
        "weight_read": weight_verify + draft["weight_s"],
        "kv_read": kv_verify + draft["kv_s"],
        "compute": (weight_verify + draft["weight_s"]) if base.fused_compute else (compute_verify + draft["compute_s"]),
        "link_latency": link_verify + draft["link_s"],
        "layer_fixed_latency": fixed_verify + draft["fixed_s"],
    }
    binding = "thermal" if thermal > 1.0 + 1e-12 else max(components, key=lambda key: components[key])

    memory0 = base.weight_s + base.kv_s if base.shared_memory_path else max(base.weight_s, base.kv_s)
    flip = None
    if not base.fused_compute and base.compute_s > 0:
        flip = memory0 / base.compute_s

    return {
        "gamma": gamma,
        "positions_per_verify": int(positions),
        "draft_placement": placement,
        "draft_kv_share": draft_kv_share,
        "storage_inflation": inflation,
        "verify_s": verify_s,
        "verify_weight_s": weight_verify,
        "verify_kv_s": kv_verify,
        "verify_compute_s": None if base.fused_compute else compute_verify,
        "verify_link_s": link_verify,
        "verify_fixed_s": fixed_verify,
        "weight_ratio_verify": weight_verify / base.weight_s if base.weight_s > 0 else None,
        "kv_ratio_verify": kv_ratio,
        "draft_s": draft["total_s"],
        "draft_weight_s": draft["weight_s"],
        "draft_kv_s": draft["kv_s"],
        "draft_compute_s": draft["compute_s"],
        "draft_link_s": draft["link_s"],
        "draft_ops_ratio": draft["ops_ratio"],
        "draft_share_of_cycle": draft["total_s"] / raw_cycle if raw_cycle > 0 else None,
        "placement_feasible": draft["placement_feasible"],
        "placement_reason": draft["placement_reason"],
        "cycle_raw_s": raw_cycle,
        "cycle_thermal_scale": thermal,
        "cycle_s": cycle_s,
        "cycle_energy_j": cycle_energy_j,
        "tau_break": cycle_s / base.step_time_s if base.step_time_s > 0 else None,
        "tau_cap": positions,
        "spec_binding_constraint": binding,
        # The block size at which a verification pass moves this design from
        # memory-bound to compute-bound: max(memory, compute)/compute at the
        # autoregressive point.  Null on a compute-in-ROM fabric, where the
        # multiply IS the sweep and there is no separate compute term to flip
        # against.  It moves with the compute efficiency derate, which is
        # graded `assumed`.
        "n_flip": flip,
    }


# --------------------------------------------------------------------------
# study pass
# --------------------------------------------------------------------------


def _tau_range(profile: dict) -> tuple[float, float]:
    acceptance = profile["acceptance_length"]
    return float(acceptance["range_low"]), float(acceptance["range_high"])


def _clamp_tau(tau: float, gamma: int) -> tuple[float, bool]:
    cap = float(gamma + 1)
    clamped = min(max(tau, 1.0), cap)
    return clamped, not _close(clamped, tau, 1e-12)


def process_study(
    source: Path,
    profile_name: str,
    profile: dict,
    technology: Technology,
    gamma_ladder: list[int],
    verify_shas: bool,
) -> dict:
    body = _load_study_artifact(source)
    inputs = body["inputs"]
    problems: list[str] = []

    if verify_shas:
        actual = _sha256(TECHNOLOGY_PATH)
        if actual != inputs["technology_sha256"]:
            raise SystemExit(
                f"{source}: the artifact was produced against technology.json "
                f"{inputs['technology_sha256'][:12]} and the file on disk is {actual[:12]}. "
                "Refusing to mix a new speculative layer with a stale machine model."
            )

    models: dict[str, ModelProfile] = {}
    for name, entry in inputs["models"].items():
        path = ROOT / entry["path"]
        if verify_shas:
            actual = _sha256(path)
            if actual != entry["sha256"]:
                raise SystemExit(
                    f"{source}: model {name} was pinned at {entry['sha256'][:12]} and "
                    f"{entry['path']} now hashes to {actual[:12]}."
                )
        models[name] = ModelProfile.load(path)

    balance_value = float(body["technology_derivations"]["efficiencies"]["stage_balance"]["value"])
    designs = {design["name"]: design for design in body["designs"]}
    drafters = {name: build_drafter(profile_name, profile, model) for name, model in models.items()}

    served_key = profile["served_gamma_parameter"]
    served_block = int(profile["parameters"][served_key]["value"])
    # THE BLOCK SIZE IS THE SPECULATION BUDGET, on both sources' own definition.
    # DFlash, arXiv:2602.06036v2: "the block size IS the speculation budget.
    # With block size 16, the diffusion drafter generates exactly 16 new draft
    # tokens per forward pass", and tau in [1, gamma+1] gives 17.  DSpark,
    # arXiv:2607.05147v1: "gamma input tokens (anchor + gamma-1 masks) yield
    # gamma draft logits", so a block of 5 is gamma = 5 with a cap of 6.  There
    # is no block_size-1 anywhere in either paper and the tool must not invent
    # one: it would verify one position short and publish a cap one too low.
    served_gamma = served_block
    cross_gamma = profile.get("cross_check_gamma_parameter")
    cross_check_gamma = int(profile["parameters"][cross_gamma]["value"]) if cross_gamma else None
    gammas = sorted(
        {
            *gamma_ladder,
            served_gamma,
            *(() if cross_check_gamma is None else (cross_check_gamma,)),
            *(int(g) for g in profile.get("sensitivity_gammas", ())),
        }
    )

    kv_cache: dict[tuple[str, int], Any] = {}
    rows: list[dict] = []
    lookup: dict[tuple[str, int, int], dict] = {}
    checked = 0

    for point in body["points"]:
        if not point["feasible"]:
            continue
        model = models[point["model"]]
        design = designs[point["design"]]
        key = (point["model"], int(point["context_tokens"]))
        if key not in kv_cache:
            kv_cache[key] = kv_traffic(model, int(point["context_tokens"]))
        base, issues = decompose(point, design, model, technology, kv_cache[key], balance_value)
        problems.extend(issues)
        checked += 1
        drafter = drafters[point["model"]]

        placements = ["in_rom", "in_kv_store"] if point["weight_store"] == "rom" else ["in_hbm"]
        variants: dict[str, dict] = {}
        for placement in placements:
            served = {}
            for share, label in ((0.0, "low"), (1.0, "high")):
                served[label] = speculative_cycle(
                    point, design, model, technology, base, drafter, served_gamma, placement, share
                )
            ladder_low = []
            ladder_high = []
            cross: dict[str, dict] | None = None
            for gamma in gammas:
                low = speculative_cycle(point, design, model, technology, base, drafter, gamma, placement, 0.0)
                high = speculative_cycle(point, design, model, technology, base, drafter, gamma, placement, 1.0)
                ladder_low.append(low["tau_break"])
                ladder_high.append(high["tau_break"])
                if cross_check_gamma is not None and gamma == cross_check_gamma:
                    cross = {"low": low, "high": high}
            cannot_pay = all(
                value is not None and value > gamma + 1 for value, gamma in zip(ladder_low, gammas)
            )
            variants[placement] = {
                "served": {"low": served["low"], "high": served["high"]},
                # The same cycle evaluated at the block size an external
                # deployment actually uses, so a cross-check never quotes a
                # cycle from one configuration beside an acceptance length
                # measured at another.
                "cross_check": cross,
                "tau_break_by_gamma_low": ladder_low,
                "tau_break_by_gamma_high": ladder_high,
                "cannot_pay_at_any_gamma": cannot_pay,
                "placement_feasible": served["low"]["placement_feasible"],
                "placement_reason": served["low"]["placement_reason"],
            }

        row = {
            "design": point["design"],
            "model": point["model"],
            "family": point["family"],
            "topology_kind": point["topology_kind"],
            "weight_store": point["weight_store"],
            "kv_store": point["kv_store"],
            "weight_amortization": point["weight_amortization"],
            "parallelism": point["parallelism"],
            "context_tokens": point["context_tokens"],
            "batch_size": point["batch_size"],
            "device_count": point["device_count"],
            "silicon_area_mm2": point["silicon_area_mm2"],
            "binding_constraint": point["binding_constraint"],
            "step_time_s": point["step_time_s"],
            "per_user_tokens_s": point["per_user_tokens_s"],
            "pipeline_fill_users": point["pipeline_fill_users"],
            "drafter_applies": drafter is not None,
            "variants": variants,
        }
        rows.append(row)
        lookup[(point["design"], int(point["batch_size"]), int(point["context_tokens"]))] = row

    if problems:
        head = "\n  ".join(problems[:10])
        raise SystemExit(
            f"{source}: the speculative layer failed to reconstruct "
            f"{len(problems)} of {checked} feasible points from the published artifact:\n  {head}\n"
            "This means the layer has misread the model, not that the points are odd."
        )

    return {
        "study_id": body["study_id"],
        "source_artifact": str(source.relative_to(ROOT)),
        "source_sha256": _sha256(source),
        "technology_sha256": inputs["technology_sha256"],
        "models": {
            name: {
                "path": entry["path"],
                "sha256": entry["sha256"],
                "context_tokens": entry["context_tokens"],
                "drafter": (
                    None
                    if drafters[name] is None
                    else {
                        "layers": drafters[name].layers,
                        "dense_bytes": drafters[name].dense_bytes,
                        "routed_bytes": drafters[name].routed_bytes,
                        "stored_bytes": drafters[name].stored_bytes,
                        "already_in_target_checkpoint": drafters[name].already_in_checkpoint,
                        "block_passes": drafters[name].block_passes,
                        "sequential_passes_per_draft_token": drafters[name].sequential_passes_per_draft_token,
                        "grade": drafters[name].grade,
                        "source": drafters[name].source,
                        "note": drafters[name].note,
                    }
                ),
            }
            for name, entry in inputs["models"].items()
        },
        "served_gamma": served_gamma,
        "served_gamma_parameter": served_key,
        "cross_check_gamma": cross_check_gamma,
        "gamma_ladder": gammas,
        "reconstruction_gate": {
            "feasible_points_checked": checked,
            "failures": 0,
            "tolerance_relative": RECONSTRUCTION_TOLERANCE,
            "statement": (
                "max(max(memory, compute)/stage_balance, serial path) x thermal_scale == "
                "step_time_s, with memory assembled by designs[].shared_memory_path and the "
                "compute-in-ROM fusion rule, and the serial path -- link_latency + "
                "layer_fixed_latency + the sweep on the path -- independently rebuilt from "
                "the model profile, the technology file and the token's operator graph "
                "(opentallas.critical_path)"
            ),
        },
        "points": rows,
        "_lookup": lookup,
        "_body": body,
    }


# --------------------------------------------------------------------------
# the tables the report reads
# --------------------------------------------------------------------------


def _spec_rate(row: dict, placement: str, tau: float, band: str) -> float | None:
    served = row["variants"][placement]["served"][band]
    return tau / served["cycle_s"] if served["cycle_s"] > 0 else None


def class_table(study: dict, profile: dict) -> list[dict]:
    """One row per model, context, batch and design class.

    The ROM-versus-GPU ratio under speculation is ``T_cycle(GPU) / T_cycle(ROM)``:
    ``tau`` is a property of the model and the drafter, not of the machine, so it
    is the SAME on both sides and cancels out of the ratio.  The ratio therefore
    moves under speculation for machine reasons alone, which is exactly the
    quantity this study is for.
    """

    body = study["_body"]
    lookup = study["_lookup"]
    tau_low, tau_high = _tau_range(profile)
    rows: list[dict] = []
    for entry in body["design_selection"]["models"]:
        model = entry["model"]
        context = int(entry["context_tokens"])
        for batch_entry in entry["iso_area_by_batch"]:
            batch = int(batch_entry["batch_size"])
            for klass in batch_entry["classes"]:
                for pick in ("fastest", "densest"):
                    chosen = klass.get(pick)
                    if not chosen:
                        continue
                    rom = lookup.get((chosen["design"], batch, context))
                    if rom is None:
                        continue
                    gpu_name = chosen.get("iso_area_gpu_design")
                    gpu = lookup.get((gpu_name, batch, context)) if gpu_name else None
                    row: dict[str, Any] = {
                        "model": model,
                        "context_tokens": context,
                        "batch_size": batch,
                        "design_class": klass["topology_kind"],
                        "pick": pick,
                        "designs_evaluated": klass.get("designs_evaluated"),
                        "rom_design": chosen["design"],
                        "rom_silicon_area_mm2": chosen.get("silicon_area_mm2"),
                        "rom_binding_constraint": rom["binding_constraint"],
                        "rom_max_resident_users": chosen.get("max_resident_users"),
                        "autoregressive_rom_per_user_tokens_s": rom["per_user_tokens_s"],
                        "drafter_applies": rom["drafter_applies"],
                    }
                    if gpu is not None:
                        row.update(
                            {
                                "iso_area_gpu_design": gpu_name,
                                "iso_area_gpu_silicon_area_mm2": chosen.get("iso_area_gpu_silicon_area_mm2"),
                                "iso_area_ratio": chosen.get("iso_area_ratio"),
                                "iso_area_gpu_binding_constraint": gpu["binding_constraint"],
                                "iso_area_gpu_max_resident_users": chosen.get("iso_area_gpu_max_resident_users"),
                                "autoregressive_iso_area_gpu_per_user_tokens_s": gpu["per_user_tokens_s"],
                                "autoregressive_ratio": (
                                    rom["per_user_tokens_s"] / gpu["per_user_tokens_s"]
                                    if gpu["per_user_tokens_s"]
                                    else None
                                ),
                            }
                        )
                    if not rom["drafter_applies"]:
                        row["speculative"] = None
                        rows.append(row)
                        continue
                    spec: dict[str, Any] = {}
                    for placement in rom["variants"]:
                        for band in ("low", "high"):
                            rom_cycle = rom["variants"][placement]["served"][band]["cycle_s"]
                            block = {
                                "rom_tau_break": rom["variants"][placement]["served"][band]["tau_break"],
                                "rom_cycle_s": rom_cycle,
                                "rom_spec_binding_constraint": rom["variants"][placement]["served"][band][
                                    "spec_binding_constraint"
                                ],
                                "rom_placement_feasible": rom["variants"][placement]["served"][band][
                                    "placement_feasible"
                                ],
                                "rom_per_user_tokens_s_at_tau_low": _spec_rate(
                                    rom, placement, _clamp_tau(tau_low, rom["variants"][placement]["served"][band]["gamma"])[0], band
                                ),
                                "rom_per_user_tokens_s_at_tau_high": _spec_rate(
                                    rom, placement, _clamp_tau(tau_high, rom["variants"][placement]["served"][band]["gamma"])[0], band
                                ),
                                "rom_pays_at_best_sourced_tau": (
                                    _clamp_tau(tau_high, rom["variants"][placement]["served"][band]["gamma"])[0]
                                    >= rom["variants"][placement]["served"][band]["tau_break"]
                                ),
                            }
                            if gpu is not None:
                                gpu_cycle = gpu["variants"]["in_hbm"]["served"][band]["cycle_s"]
                                gamma = gpu["variants"]["in_hbm"]["served"][band]["gamma"]
                                block.update(
                                    {
                                        "gpu_tau_break": gpu["variants"]["in_hbm"]["served"][band]["tau_break"],
                                        "gpu_cycle_s": gpu_cycle,
                                        "gpu_spec_binding_constraint": gpu["variants"]["in_hbm"]["served"][band][
                                            "spec_binding_constraint"
                                        ],
                                        "gpu_per_user_tokens_s_at_tau_low": _spec_rate(
                                            gpu, "in_hbm", _clamp_tau(tau_low, gamma)[0], band
                                        ),
                                        "gpu_per_user_tokens_s_at_tau_high": _spec_rate(
                                            gpu, "in_hbm", _clamp_tau(tau_high, gamma)[0], band
                                        ),
                                        "speculative_ratio": gpu_cycle / rom_cycle if rom_cycle > 0 else None,
                                        "gpu_pays_at_best_sourced_tau": (
                                            _clamp_tau(tau_high, gamma)[0]
                                            >= gpu["variants"]["in_hbm"]["served"][band]["tau_break"]
                                        ),
                                    }
                                )
                                if row.get("autoregressive_ratio"):
                                    block["ratio_movement_x"] = (
                                        block["speculative_ratio"] / row["autoregressive_ratio"]
                                    )
                            spec[f"{placement}/{band}"] = block
                    row["speculative"] = spec
                    rows.append(row)
    return rows


def break_even_census(study: dict) -> dict:
    """How often speculation cannot pay at any acceptance rate, and where."""

    buckets: dict[tuple[str, str, str, str], dict] = {}
    for row in study["points"]:
        if not row["drafter_applies"]:
            continue
        for placement, variant in row["variants"].items():
            key = (row["model"], row["family"], placement, row["binding_constraint"])
            bucket = buckets.setdefault(
                key,
                {
                    "model": row["model"],
                    "family": row["family"],
                    "draft_placement": placement,
                    "autoregressive_binding_constraint": row["binding_constraint"],
                    "points": 0,
                    "cannot_pay_at_any_gamma": 0,
                    "placement_infeasible": 0,
                    "tau_break_served_low": [],
                },
            )
            bucket["points"] += 1
            if variant["cannot_pay_at_any_gamma"]:
                bucket["cannot_pay_at_any_gamma"] += 1
            if not variant["placement_feasible"]:
                bucket["placement_infeasible"] += 1
            value = variant["served"]["low"]["tau_break"]
            if value is not None and math.isfinite(value):
                bucket["tau_break_served_low"].append(value)
    census = []
    for key in sorted(buckets):
        bucket = buckets[key]
        values = sorted(bucket.pop("tau_break_served_low"))
        if values:
            bucket["tau_break_served_min"] = values[0]
            bucket["tau_break_served_median"] = values[len(values) // 2]
            bucket["tau_break_served_max"] = values[-1]
        census.append(bucket)
    return {
        "rule": (
            "tau* = T_cycle / step_time_s. Speculation pays iff tau >= tau*, and tau <= gamma+1 "
            "always, so a design whose tau* exceeds gamma+1 at every gamma on the ladder cannot "
            "be sped up by speculation at ANY acceptance rate. Counted at the LOW end of the "
            "unsourced drafter-KV band, which is the most favourable assumption available."
        ),
        "buckets": census,
    }


def capacity_requirements(study: dict, technology: Technology) -> list[dict]:
    """What the drafter costs in array area, stated as a requirement.

    Every evaluated ROM design carries ``weight_capacity_bytes == stored_weight_bytes``
    (the ``romfill`` variants reach 1.0039x), so no evaluated design has room for
    a drafter it does not already store.  Re-solving the area split is
    ``balanced_area_split``'s job and that file is not touched here, so the
    output is a requirement -- this many extra square millimetres of array, and
    this much extra sweep on every pass -- rather than a new design.
    """

    body = study["_body"]
    lookup = study["_lookup"]
    seen: set[tuple[str, str, str, str]] = set()
    rows: list[dict] = []
    for entry in body["design_selection"]["models"]:
        model = entry["model"]
        context = int(entry["context_tokens"])
        for batch_entry in entry["iso_area_by_batch"]:
            if int(batch_entry["batch_size"]) != 1:
                continue
            for klass in batch_entry["classes"]:
                chosen = klass.get("fastest")
                if not chosen:
                    continue
                row = lookup.get((chosen["design"], 1, context))
                if row is None or row["family"] != "rom":
                    continue
                drafter = study["models"][model]["drafter"]
                if drafter is None:
                    continue
                point = next(
                    p
                    for p in body["points"]
                    if p["design"] == chosen["design"] and p["batch_size"] == 1 and p["context_tokens"] == context
                )
                key = (model, chosen["design"], point["weight_amortization"], point["node"])
                if key in seen:
                    continue
                seen.add(key)
                inflation = row["variants"]["in_rom"]["served"]["low"]["storage_inflation"]
                stored = float(point["stored_weight_bytes"])
                extra = stored * (inflation - 1.0)
                density = technology.rom_bits_per_mm2_for(point["node"], point["weight_amortization"])
                rows.append(
                    {
                        "model": model,
                        "design": chosen["design"],
                        "design_class": klass["topology_kind"],
                        "node": point["node"],
                        "weight_amortization": point["weight_amortization"],
                        "stored_weight_bytes": stored,
                        "weight_capacity_bytes": float(point["weight_capacity_bytes"]),
                        "capacity_over_stored": float(point["weight_capacity_bytes"]) / stored,
                        "drafter_already_in_checkpoint": drafter["already_in_target_checkpoint"],
                        "extra_stored_bytes_required": extra,
                        "extra_array_mm2_required": extra * 8.0 / density.value,
                        "rom_capacity_bits_per_mm2": density.value,
                        "rom_capacity_grade": density.grade,
                        "sweep_inflation_if_area_held_fixed": inflation,
                        "silicon_area_mm2": point["silicon_area_mm2"],
                        "extra_area_fraction": (extra * 8.0 / density.value) / float(point["silicon_area_mm2"]),
                    }
                )
    return rows


def _selection_rule(candidates: list[tuple[str, float, float]]) -> str | None:
    """The published rule, restated: non-dominated on both axes, then a marginal-return walk.

    ``candidates`` are ``(design, per_user_tokens_s, area_mm2)``.  The second
    axis is per-user tokens/s per 1,000 mm2, which is what
    ``design_selection.models[].recommended.tokens_s_per_1000mm2`` holds in the
    published artifact -- and the reproduction of the published autoregressive
    recommendation is reported beside every re-ranking, because a re-ranking
    whose baseline does not reproduce is not evidence of anything.

    ``tau`` is a common factor on BOTH axes, so the rule's answer under
    speculation is independent of the acceptance rate.
    """

    frontier = []
    for name, rate, area in candidates:
        density = rate / (area / 1000.0)
        dominated = any(
            other_rate > rate and other_rate / (other_area / 1000.0) > density
            for other_name, other_rate, other_area in candidates
            if other_name != name
        )
        if not dominated:
            frontier.append((name, rate, area))
    if not frontier:
        return None
    frontier.sort(key=lambda item: (item[2], item[0]))
    incumbent = frontier[0]
    for candidate in frontier[1:]:
        if candidate[2] <= incumbent[2]:
            continue
        marginal = (candidate[1] - incumbent[1]) / (candidate[2] - incumbent[2])
        average = incumbent[1] / incumbent[2]
        if marginal > average:
            incumbent = candidate
        else:
            break
    return incumbent[0]


def selection_under_speculation(study: dict, profile: dict) -> list[dict]:
    """Which rung of the SAME ladder the published rule chooses once a block is verified.

    A re-ranking, not a re-simulation: every design here was already evaluated.
    ``tau`` is a common factor on both axes of the rule, so the choice is
    independent of the acceptance rate -- which is why it can be published
    without one.
    """

    body = study["_body"]
    rows: list[dict] = []
    for entry in body["design_selection"]["models"]:
        model = entry["model"]
        context = int(entry["context_tokens"])
        published = entry["recommended"]["design"]
        pool = [
            row
            for row in study["points"]
            if row["model"] == model
            and row["family"] == "rom"
            and row["batch_size"] == 1
            and row["context_tokens"] == context
            and row["weight_amortization"] == "batched"
        ]
        if not pool:
            continue
        autoregressive = _selection_rule(
            [(row["design"], row["per_user_tokens_s"], row["silicon_area_mm2"]) for row in pool]
        )
        result = {
            "model": model,
            "context_tokens": context,
            "published_recommendation": published,
            "rule_reproduces_published_recommendation": autoregressive == published,
            "rule_reproduction": autoregressive,
        }
        if pool[0]["drafter_applies"]:
            for placement in ("in_rom", "in_kv_store"):
                usable = [
                    row
                    for row in pool
                    if row["variants"][placement]["placement_feasible"]
                    and row["variants"][placement]["served"]["low"]["cycle_s"] > 0
                ]
                if not usable:
                    result[f"speculative_recommendation_{placement}"] = None
                    continue
                choice = _selection_rule(
                    [
                        (
                            row["design"],
                            1.0 / row["variants"][placement]["served"]["low"]["cycle_s"],
                            row["silicon_area_mm2"],
                        )
                        for row in usable
                    ]
                )
                result[f"speculative_recommendation_{placement}"] = choice
                result[f"speculative_moves_the_choice_{placement}"] = choice != autoregressive
        else:
            result["drafter_applies"] = False
        rows.append(result)
    return rows


# --------------------------------------------------------------------------
# cross-checks
# --------------------------------------------------------------------------


def dflash_overhead_gate(study: dict, profile: dict, config: dict) -> dict | None:
    """A band check against DFlash's own measurement, in the style of a validation gate.

    Their overhead factor is ``tau / speedup``.  In this arithmetic that quantity
    is exactly ``T_cycle / step_time_s`` -- the break-even acceptance -- so it is
    a property of the machine and the block size alone and carries no acceptance
    rate at all.  Theirs is measured on an H200 with their own kernels; ours is a
    modelled B200-class cluster with an assumed 0.55 compute derate and a 0.9
    stage balance.  THIS IS NOT A VALIDATION OF THE MACHINE.  It is evidence that
    the arithmetic is not obviously wrong, and the residual is reported as a
    residual.
    """

    if profile["drafter_family"] != "block_diffusion_parallel":
        return None
    body = study["_body"]
    lookup = study["_lookup"]
    target = None
    for entry in body["design_selection"]["models"]:
        if entry["model"] != "Qwen3-8B":
            continue
        context = int(entry["context_tokens"])
        comparator = entry["recommended"].get("iso_area_gpu_design")
        if comparator:
            target = lookup.get((comparator, 1, context))
        break
    if target is None:
        return None
    reference = config["cross_checks"]["dflash_overhead_factor"]
    ladder = study["gamma_ladder"]
    modelled = {
        str(gamma): value
        for gamma, value in zip(ladder, target["variants"]["in_hbm"]["tau_break_by_gamma_low"])
    }
    served = target["variants"]["in_hbm"]["served"]
    low = served["low"]["tau_break"]
    high = served["high"]["tau_break"]
    inside = reference["band_low"] <= low <= reference["band_high"]
    return {
        "gate": "dflash_overhead_factor",
        "kind": "band check, never an equality",
        "modelled_on": target["design"],
        "modelled_batch_size": 1,
        "modelled_context_tokens": target["context_tokens"],
        "modelled_gamma": served["low"]["gamma"],
        "modelled_overhead_factor_draft_kv_low": low,
        "modelled_overhead_factor_draft_kv_high": high,
        "modelled_overhead_factor_by_gamma_draft_kv_low": modelled,
        "published_band_low": reference["band_low"],
        "published_band_high": reference["band_high"],
        "published_outlier": reference["outlier"],
        "published_source": reference["source"],
        "inside_published_band": inside,
        "residual_vs_band_low_x": low / reference["band_low"],
        "residual_statement": (
            f"this layer models an overhead factor of {low:.3f} at the low end of the unsourced "
            f"drafter-KV band and {high:.3f} at the high end, against a published "
            f"{reference['band_low']:.2f}-{reference['band_high']:.2f} measured on an H200. "
            "The gap is the gate residual and its named causes are: the drafter's own KV traffic "
            "at the low bound of an unsourced band, no sampler and no scheduler cost anywhere in "
            "this model, and a modelled B200-class cluster against their measured H200."
        ),
        "not_a_validation": (
            "Their speedups are measured with their kernels on their part. Nothing here measures "
            "a speedup, and no sentence in this artifact may be read as though it did."
        ),
    }


def draft_traffic_reconciliation(profile: dict, models: dict[str, ModelProfile]) -> dict | None:
    """The repository's own draft inventory against the externally published decomposition.

    They do not agree, and neither is silently preferred.  The modelled input is
    the repository's own ``configs/models/*.json``; the external decomposition is
    carried beside it with the divergence stated at every block size.
    """

    external = profile.get("external_draft_traffic_decomposition")
    if not external:
        return None
    rows = []
    for name in sorted(models):
        model = models[name]
        if model.draft_dense_weight_bytes + model.draft_routed_weight_bytes <= 0:
            continue
        target_pass = model.dense_weight_bytes + model.routed_weight_bytes * (
            model.experts_per_token / model.num_experts
        )
        for tokens in (1, 2, 3, 4, 5, 6, 7, 8):
            repo = draft_weight_traffic(model, 1, draft_tokens=tokens)
            entry = {
                "model": name,
                "draft_tokens": tokens,
                "repository_config_bytes": repo.total_bytes,
                "repository_config_fraction_of_target_pass": repo.total_bytes / target_pass,
                "target_pass_bytes": target_pass,
            }
            if name == "DeepSeek-V4-Pro-0813":
                published = external["constant_bytes"] + external["bytes_per_draft_token"] * tokens
                entry["externally_published_bytes"] = published
                entry["externally_published_fraction_of_target_pass"] = published / target_pass
                entry["divergence_x"] = repo.total_bytes / published
            rows.append(entry)
    return {
        "what_this_is": (
            "The draft weight traffic this study models comes from the repository's own "
            "checkpoint inventory. An externally published decomposition for "
            "DeepSeek-V4-Pro-0813 gives a different answer, and the two are printed side by side "
            "rather than reconciled by choosing one."
        ),
        "external_source": external["source"],
        "external_grade": external["grade"],
        "external_note": external["note"],
        "rows": rows,
    }


def xiaomi_cross_check(studies: list[dict], profile: dict, config: dict) -> dict | None:
    """A commodity GPU node on a Pro-scale model, against Xiaomi's own claim.

    A CROSS-CHECK, NOT A CALIBRATION TARGET.  Every condition the blog does not
    state is named on every row, and where this study evaluates no machine of
    the size the blog describes, that is said rather than extrapolated.
    """

    if profile["drafter_family"] != "block_diffusion_parallel":
        return None
    reference = config["cross_checks"]["xiaomi_mimo_ultraspeed"]
    candidates = [
        row
        for study in studies
        for row in study["points"]
        if row["model"] == "DeepSeek-V4-Pro-0813" and row["family"] != "rom"
    ]
    if not candidates:
        return None
    counts = sorted({row["device_count"] for row in candidates})
    # Eight packages is 12,800 mm2 of silicon and this study's GPU area ladder
    # is anchored to the ROM areas a 1.6-trillion-parameter model needs, so it
    # may contain no eight-device rung at all.  Say so rather than extrapolate.
    eight_present = 8 in counts
    near = [value for value in counts if abs(value - 8) <= 2]
    if not near:
        near = [min(counts, key=lambda value: abs(value - 8))]
    wanted = set(near)
    rows = []
    for row in candidates:
        if row["device_count"] not in wanted:
            continue
        # THE CYCLE AND THE ACCEPTANCE LENGTH MUST COME FROM THE SAME
        # CONFIGURATION.  Xiaomi's acceptance lengths are published at their own
        # block size, so the cycle beside them is evaluated at that block size
        # and not at this profile's served block.  ``cross_check`` is that
        # cycle; there is no fallback to ``served``, because quoting a block-16
        # cycle under a block-8 acceptance length is the error this exists to
        # prevent.
        served = row["variants"]["in_hbm"]["cross_check"]
        if served is None:
            continue
        entry = {
            "design": row["design"],
            "device_count": row["device_count"],
            "parallelism": row["parallelism"],
            "batch_size": row["batch_size"],
            "context_tokens": row["context_tokens"],
            "silicon_area_mm2": row["silicon_area_mm2"],
            "autoregressive_per_user_tokens_s": row["per_user_tokens_s"],
            "autoregressive_aggregate_tokens_s": row["pipeline_fill_users"] * row["per_user_tokens_s"],
            "resident_sessions": row["pipeline_fill_users"],
            "binding_constraint": row["binding_constraint"],
            "gamma": served["low"]["gamma"],
            "block_size": served["low"]["gamma"],
            "positions_per_verify": served["low"]["positions_per_verify"],
            "tau_break_draft_kv_low": served["low"]["tau_break"],
            "tau_break_draft_kv_high": served["high"]["tau_break"],
            "speculative_by_workload": {},
        }
        for point in profile["external_acceptance_cross_check"]["points"]:
            tau, clamped = _clamp_tau(float(point["value"]), served["low"]["gamma"])
            entry["speculative_by_workload"][point["workload"]] = {
                "tau": tau,
                "tau_clamped": clamped,
                "per_user_tokens_s_draft_kv_low": tau / served["low"]["cycle_s"],
                "per_user_tokens_s_draft_kv_high": tau / served["high"]["cycle_s"],
                "aggregate_tokens_s_draft_kv_low": row["pipeline_fill_users"] * tau / served["low"]["cycle_s"],
                "pays": tau >= served["low"]["tau_break"],
            }
        rows.append(entry)
    if not rows:
        return None
    rows.sort(key=lambda item: (item["context_tokens"], item["device_count"], item["batch_size"], item["design"]))
    block = rows[0]["block_size"]
    return {
        "block_size": block,
        "positions_per_verify": rows[0]["positions_per_verify"],
        "block_size_statement": (
            f"Every row below is evaluated at gamma = {block}, the block size Xiaomi's own "
            f"deployment uses, so the verification pass carries {rows[0]['positions_per_verify']} "
            "positions. The acceptance lengths applied to it are the ones Xiaomi publishes at "
            f"that same block size. This is NOT this profile's served block size, and the cycle "
            "and the acceptance length are never taken from different configurations."
        ),
        "eight_device_comparator_present": eight_present,
        "device_counts_reported": sorted(wanted),
        "gpu_device_counts_evaluated_for_this_model": counts,
        "eight_device_statement": (
            "This study evaluates no eight-device GPU cluster for DeepSeek-V4-Pro-0813. Eight "
            "B200-class packages is 12,800 mm2 of silicon; the GPU comparator ladder in this "
            "study is anchored to the areas the ROM designs need for a 1.6-trillion-parameter "
            "checkpoint, and it contains no eight-package rung. The rows below are the nearest "
            f"rungs it does contain -- {', '.join(str(value) for value in sorted(wanted))} "
            "packages -- and they are NOT an eight-device figure. Producing one would mean "
            "evaluating a design this study has not evaluated, which this tool does not do."
            if not eight_present
            else "Eight packages is an evaluated rung for this model and the rows below include it."
        ),
        "what_this_is": (
            "Our own model, run on the GPU clusters this study evaluates that are nearest in "
            "size to an eight-package node, carrying DeepSeek-V4-Pro-0813 -- a "
            "1.6-trillion-parameter fine-grained MoE, the closest thing in this study to the "
            "model Xiaomi describes -- with the block-diffusion drafter at gamma = "
            f"{block}, the block size Xiaomi's deployment uses, and with the acceptance lengths "
            "Xiaomi publishes at that same block size. It is put beside Xiaomi's claim, and it "
            "does not calibrate to it."
        ),
        "claim": {
            "tokens_s": reference["claimed_tokens_s"],
            "figure_caption_tokens_s": reference["claimed_tokens_s_figure_caption"],
            "total_parameters": reference["total_parameters"],
            "active_parameters": reference["active_parameters"],
            "node": reference["node"],
            "source": reference["source"],
        },
        "unstated_conditions": reference["unstated_conditions"],
        "stacked_techniques": reference["stacked_techniques"],
        "acceptance_lengths_used": profile["external_acceptance_cross_check"],
        "differences_from_our_model": [
            "Xiaomi quantises MoE experts to MXFP4 with quantisation-aware training; the "
            "DeepSeek-V4-Pro-0813 profile in this repository is evaluated at the released "
            "checkpoint's own packing and no quantised Pro variant exists in this study.",
            "Xiaomi runs the TileRT runtime; this model charges an assumed 0.55 compute "
            "efficiency and an assumed 0.9 stage balance and knows nothing about any runtime.",
            "Xiaomi declines to attribute the speedup among quantisation, drafter and runtime, so "
            "no part of the claim can be read as a speculative-decoding result on its own.",
            "The model is not the same model. DeepSeek-V4-Pro-0813 and MiMo-V2.5-Pro share only a "
            "parameter count.",
        ],
        "rows": rows,
    }


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------


def _n(value: Any, digits: int = 1) -> str:
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "--"
    return f"{value:,.{digits}f}"


def _pct(value: Any) -> str:
    return "--" if value is None else f"{value * 100:.1f}%"


def _graded_rows(node: Any, path: str = "") -> list[tuple[str, dict]]:
    found: list[tuple[str, dict]] = []
    if isinstance(node, dict):
        if "grade" in node:
            found.append((path, node))
        for key, value in node.items():
            found.extend(_graded_rows(value, f"{path}.{key}" if path else key))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(_graded_rows(value, f"{path}[{index}]"))
    return found


def _findings(payload: dict) -> list[str]:
    """The numbered findings at the head of the report, computed from the payload."""

    profile = payload["profile"]
    _, tau_high = _tau_range(profile)
    studies = payload["studies"]
    verdicts = 0
    total_variants = 0
    for study in studies:
        for row in study["points"]:
            if not row["drafter_applies"]:
                continue
            for variant in row["variants"].values():
                total_variants += 1
                if variant["cannot_pay_at_any_gamma"]:
                    verdicts += 1
    class_rows = [
        row
        for study in studies
        for row in study["class_table"]
        if row["pick"] == "fastest" and row.get("speculative") and "in_rom/low" in row["speculative"]
    ]
    movements = [
        row["speculative"]["in_rom/low"]["ratio_movement_x"]
        for row in class_rows
        if row["speculative"]["in_rom/low"].get("ratio_movement_x") is not None
    ]
    batch_one = [
        row
        for row in class_rows
        if row["batch_size"] == 1
        and row["speculative"]["in_rom/low"].get("ratio_movement_x") is not None
    ]
    rom_pays = sum(1 for row in class_rows if row["speculative"]["in_rom/low"].get("rom_pays_at_best_sourced_tau"))
    gpu_pays = sum(1 for row in class_rows if row["speculative"]["in_rom/low"].get("gpu_pays_at_best_sourced_tau"))
    checked = sum(study["reconstruction_gate"]["feasible_points_checked"] for study in studies)
    already = sorted(
        {
            name
            for study in studies
            for name, entry in study["models"].items()
            if entry["drafter"] and entry["drafter"]["already_in_target_checkpoint"]
        }
    )
    absent = sorted(
        {
            name
            for study in studies
            for name, entry in study["models"].items()
            if entry["drafter"] is None
        }
    )
    findings = [
        "**Every term the speculative arithmetic needs is already in the published artifact, "
        f"exactly.** {checked:,} feasible points across {len(studies)} studies were rebuilt from "
        "their own five critical-path terms and every one reproduced its published step time to "
        "1e-9 relative. Nothing here re-ran the machine model, and the layer is additive by "
        "construction rather than by promise.",
        "**The headline is a break-even, not a speedup.** `tau* = T_cycle / step_time_s`, and "
        f"`tau <= gamma+1` always. Of {total_variants:,} (point, draft-placement) pairs where this "
        f"profile's drafter applies, {verdicts:,} ({verdicts / max(1, total_variants) * 100:.1f}%) "
        "cannot be sped up by speculation at ANY acceptance rate, at any block size on the ladder, "
        "even charging the drafter no KV traffic at all.",
        "**The ROM-versus-GPU ratio under speculation carries no acceptance rate.** It is "
        "`T_cycle(GPU) / T_cycle(ROM)`: `tau` is a property of the model and its drafter, not of "
        "the machine, so it is identical on both sides and cancels. Every movement this report "
        "shows is a machine effect and nothing else, which is why it can be published without "
        "inventing an acceptance rate.",
    ]
    if movements:
        compress = sum(1 for value in movements if value < 1.0)
        findings.append(
            ("**The ratio moves, and it mostly compresses.** " if compress > len(movements) / 2
             else "**The ratio moves, and which way it moves depends on the machine.** ")
            + f"Across {len(movements)} "
            f"model-context-batch-class rows, {compress} move the ROM-versus-GPU per-user ratio "
            f"DOWN under speculation and {len(movements) - compress} move it UP, spanning "
            f"{min(movements):.3f}x to {max(movements):.3f}x. "
            + (
                "The ROM advantage compresses on most operating points."
                if compress > len(movements) / 2
                else "The ROM advantage does not compress on most operating points."
            )
        )
    if batch_one:
        worst = min(batch_one, key=lambda row: row["speculative"]["in_rom/low"]["ratio_movement_x"])
        best = max(batch_one, key=lambda row: row["speculative"]["in_rom/low"]["ratio_movement_x"])
        findings.append(
            "**At batch 1 the two extremes are opposite in sign, and they are the result.** "
            f"{worst['model']} on `{worst['design_class']}` silicon goes from "
            f"{worst['autoregressive_ratio']:.2f}x to "
            f"{worst['speculative']['in_rom/low']['speculative_ratio']:.2f}x -- a "
            f"{worst['speculative']['in_rom/low']['ratio_movement_x']:.3f}x movement -- while "
            f"{best['model']} on `{best['design_class']}` silicon goes from "
            f"{best['autoregressive_ratio']:.2f}x to "
            f"{best['speculative']['in_rom/low']['speculative_ratio']:.2f}x, a "
            f"{best['speculative']['in_rom/low']['ratio_movement_x']:.3f}x movement. A layer that "
            "multiplied both sides by `tau` would have reported neither."
        )
    findings.append(
        "**A moving ratio is not a win for either side, and the report says so on every table.** "
        f"At the most favourable sourced acceptance ({tau_high:.2f}) speculation is worth having "
        f"on {rom_pays} of {len(class_rows)} ROM class rows and {gpu_pays} of {len(class_rows)} "
        "GPU rows; everywhere else the design runs SLOWER with a drafter than without one. Where "
        "both sides lose, a rising ratio means only that the comparator lost more."
    )
    findings.append(
        "**Compute is never a gain and always a loss.** A verification pass over `n` positions "
        "charges `n` times the arithmetic exactly, so per accepted token compute costs "
        "`(n/tau) >= 1` times what it did. A compute-bound design cannot be sped up by "
        "speculation at any acceptance rate; it can only be slowed. That is where the recommended "
        "ROM designs live, because the sizing rule gives them just enough compute for one token "
        "per sweep."
    )
    findings.append(
        "**On a mask-ROM machine the draft pass costs a full array sweep, and that is the "
        "load-bearing assumption of the whole ROM verdict.** `stored/peak` is a technology "
        "constant in `src/opentallas/roofline.py`, so a pass reading only the drafter's region "
        "takes as long as sweeping the entire array. The alternative -- holding the drafter in "
        "the KV store -- is priced beside it on every ROM row and has NOT been costed in silicon "
        "area."
    )
    if already:
        findings.append(
            "**The mask-ROM designs are already storing this drafter, and already sweeping it on "
            "every ordinary token.** `_rom_stored_bytes` stores the whole released checkpoint, "
            "and the checkpoint ships the draft module for "
            + ", ".join(already)
            + ". So the storage inflation is 1.000x, the extra array requirement is zero, and the "
            "autoregressive ROM baseline in the published study is ALREADY paying for a drafter "
            "it does not use. The HBM comparators are not: their engaged bytes exclude the draft "
            "categories entirely."
        )
    if absent:
        findings.append(
            "**This profile does not apply to " + ", ".join(absent) + ".** "
            + ("Its released checkpoint carries" if len(absent) == 1 else "Their released checkpoints carry")
            + " no draft weights at all, and transplanting a drafter that was never trained for "
            + ("it" if len(absent) == 1 else "them")
            + " would be inventing a model. "
            + ("It is" if len(absent) == 1 else "They are")
            + " reported as not applicable rather than modelled."
        )
    sequential = float(
        profile["parameters"].get("draft_sequential_passes_per_draft_token", {}).get("value", 0)
    )
    if sequential > 0:
        rom_draft = []
        for study in studies:
            quoted = _quoted_keys(study)
            for row in study["points"]:
                if row["family"] != "rom" or not row["drafter_applies"]:
                    continue
                if (row["design"], row["batch_size"], row["context_tokens"]) not in quoted:
                    continue
                rom_draft.append(row["variants"]["in_rom"]["served"]["low"])
        shares = sorted(
            entry["draft_share_of_cycle"] for entry in rom_draft if entry["draft_share_of_cycle"] is not None
        )
        if shares:
            findings.append(
                "**This drafter's SEQUENTIAL step is what it costs on a mask-ROM machine, and it "
                "costs more than the drafter's own size.** The bias is applied once per draft "
                "token with no transformer re-run, so on a bandwidth machine it moves a table and "
                "is nearly free -- but under the locality rule every pass that touches the array "
                "takes the full-array sweep time whatever it reads, so `gamma` sequential "
                f"applications cost `gamma` full sweeps. The draft pass is "
                f"{shares[0] * 100:.0f}% to {shares[-1] * 100:.0f}% of the whole speculative "
                f"cycle on the ROM designs this report quotes (median "
                f"{shares[len(shares) // 2] * 100:.0f}%), almost all of it those sweeps. A "
                "block-diffusion drafter has no such term at all, which is the single largest "
                "structural difference between the two profiles on this silicon."
            )
    gate = payload.get("dflash_overhead_gate")
    if gate:
        findings.append(
            "**The overhead factor lands below the only published measurement of it, and the gap "
            "is reported as a residual.** This layer models "
            f"{gate['modelled_overhead_factor_draft_kv_low']:.3f} on "
            f"`{gate['modelled_on'].split('/')[-1]}` against a published "
            f"{gate['published_band_low']:.2f}-{gate['published_band_high']:.2f} measured on an "
            "H200 with the authors' own kernels. The named causes are the drafter's unsourced KV "
            "traffic at the bottom of its band, no sampler or scheduler cost anywhere in this "
            "model, and a different part. It is a band check and it validates nothing about the "
            "machine."
        )
    findings.append(
        "**Every number here is conditional on inputs nobody has measured.** The drafter's own KV "
        "traffic is unsourced for both drafters and is published as a band on every row; the "
        "compute efficiency derate that decides which designs are compute-bound is graded "
        "`assumed` at 0.55; and no speculative decoder has ever been executed in this repository."
    )
    return findings


def render_report(payload: dict) -> str:
    profile = payload["profile"]
    name = payload["profile_name"]
    tau_low, tau_high = _tau_range(profile)
    out: list[str] = []
    add = out.append

    add(f"# Speculative decoding on the area-constrained roofline: {name}")
    add("")
    add(f"> {profile['label']}. Every figure below is derived from the roofline artifacts")
    add("> this repository has already published, by re-assembling each point's own five")
    add("> critical-path terms for a speculative cycle. Nothing here re-runs the machine")
    add("> model, and nothing here invents an acceptance rate.")
    add("")
    add("## What this layer says")
    add("")
    for index, item in enumerate(_findings(payload), start=1):
        add(f"{index}. {item}")
    add("")
    add("## What this layer is, and what it is not")
    add("")
    add(
        "It **is** an arithmetic layer over `results/roofline/**/analytical.json`. Every term it "
        "uses -- weight read, KV read, compute, link latency, the per-layer serial floor, the "
        "thermal throttle -- is recovered exactly from the published artifact, and the "
        "reconstruction is gated on every feasible point before any speculative arithmetic runs."
    )
    add("")
    add(
        "It is **not** a measurement of a speculative system. No token in this repository has been "
        "produced by a speculative decoder. The only quantities taken from outside are the "
        "drafter's shape and the acceptance lengths, both published by their authors and both "
        "measured on hardware that is not in this study."
    )
    add("")
    add(
        "The headline is therefore **not a speedup**. It is the break-even acceptance "
        "`tau* = T_cycle / step_time_s`: speculation pays if and only if `tau >= tau*`, and "
        "`tau <= gamma+1` always. A design whose `tau*` exceeds `gamma+1` at every block size "
        "**cannot be sped up by speculation at any acceptance rate** -- a verdict that needs no "
        "acceptance rate to state, and the only kind of verdict this study can honestly publish "
        "for a model whose acceptance nobody has measured."
    )
    add("")
    add("## The arithmetic")
    add("")
    add("Write `n = gamma + 1` for the positions one verification pass carries, the extra one")
    add("being the target's own bonus token. DFlash equation (1) is `L = (T_draft + T_verify)/tau`")
    add("with `tau` in `[1, gamma+1]` counting accepted tokens INCLUDING that bonus token.")
    add("")
    add(
        "**`gamma` is the block size, taken from each source's own definition and never derived "
        "as `block_size - 1`.** DFlash states that the block size IS the speculation budget, so a "
        "block of 16 proposes 16 draft tokens and caps `tau` at 17. DSpark treats the anchor "
        "itself as the first prediction position, so a block of `gamma` (anchor plus `gamma-1` "
        "masks) yields `gamma` draft logits and caps `tau` at `gamma+1`. A ladder rung above the "
        "block size a source actually configures is an extension this study states rather than a "
        "configuration anyone has served."
    )
    add("")
    served_gamma = payload["studies"][0]["served_gamma"] if payload["studies"] else None
    if served_gamma is not None:
        ladder = payload["studies"][0]["gamma_ladder"]
        # The profile names its own block-size parameters; nothing is inferred
        # from a note, so a rung is only called sourced when a source names it.
        sourced = sorted(
            {
                int(payload["profile"]["parameters"][name]["value"])
                for name in payload["profile"].get("block_size_parameters", ())
            }
        )
        extensions = [value for value in ladder if value not in sourced]
        add(
            f"**Every headline figure in this report is at gamma = {served_gamma}, so a verification "
            f"pass carries {served_gamma + 1} positions and `tau` is capped at {served_gamma + 1}.** "
            "The break-even ladder runs over gamma = "
            + ", ".join(str(value) for value in ladder)
            + ". Of those, "
            + ", ".join(str(value) for value in sourced)
            + " are block sizes a source names for this drafter; "
            + ", ".join(str(value) for value in extensions)
            + " are rungs no source configures, carried so the parameter-free verdict below is "
            "tested over a wider range than anyone serves, and never quoted as a served figure."
        )
        add("")
    add("| term | verification pass over `n` positions | why |")
    add("| --- | --- | --- |")
    add("| weight, ROM `batched` | `W` | one array sweep serves the block exactly as it serves a batch, and it is immune to the expert-union widening that taxes a bandwidth machine |")
    add("| weight, ROM `per_stream` | `W * n` | compute-in-ROM: the multiply IS the sweep, so each position is its own pass through the fabric |")
    add("| weight, ROM `per_region` | `W * R(mb*n)/R(mb)` | the busiest expert region carries more of a wider block |")
    add("| weight, HBM | `W * t(mb*n)/t(mb)` | **not invariant**: `n` positions are `n` independent expert draws, so the union of routed experts widens and the engaged bytes grow |")
    add("| weight, drafter held off-array (`in_kv_store`) | `(dense + routed * coverage(mb*n)) / kv_read_bytes_s` | a bandwidth read over the KV store's own path, charged ONCE for the block. The compute-in-ROM sweep multiplier belongs to the fabric and this transfer never enters the fabric. |")
    add("| KV | `K * (read + n*write)/(read + write)` | the block shares one prefix, so the context is read ONCE per cycle and only the writes multiply |")
    add("| compute | `C * n` | exact under the model's own convention: `_scaled_operations` is linear in positions |")
    add("| link | `lat + xfer * n` | only the payload half of a link event scales with positions; the latency half is fixed per cycle |")
    add("| per-layer floor | `F` | one traversal of the layers however many positions ride it |")
    add("")
    add(
        "The draft pass runs on the same machine under the same rules with the drafter's own "
        "numbers. On a mask-ROM machine it is where the locality rule bites: `t = stored/peak` is "
        "a technology constant in `src/opentallas/roofline.py`, so a pass that touches only the "
        "drafter's region takes exactly as long as sweeping the whole array."
    )
    add("")
    add("## The profile, and every parameter's grade")
    add("")
    add("| parameter | value | grade | source |")
    add("| --- | --- | --- | --- |")
    for path, entry in sorted(_graded_rows(profile)):
        value = entry.get("value")
        if value is None and entry.get("band_high_rule"):
            value = f"BAND [{entry.get('band_low', 0)}, {entry['band_high_rule']}]"
        elif value is None:
            value = "(a block of values; see the tables in this report)"
        if isinstance(value, str) and len(value) > 90:
            value = value[:87] + "..."
        source = str(entry.get("source", ""))
        if len(source) > 130:
            source = source[:127] + "..."
        add(f"| `{path}` | {value} | `{entry['grade']}` | {source} |")
    add("")
    acceptance = profile["acceptance_length"]
    add(
        f"**The acceptance length is an input, never an output, and it is task-dependent.** "
        f"The range carried here is {tau_low:.2f} to {tau_high:.2f}, graded `{acceptance['grade']}`, "
        f"from {acceptance['source']}. Every speculative rate below is published across that range."
    )
    add("")
    add("| workload | tau | source's own reported speedup |")
    add("| --- | ---: | ---: |")
    for point in acceptance["points"]:
        add(f"| {point['workload']} | {point['value']:.2f} | {point.get('reported_speedup_x', '--')} |")
    add("")
    add(f"_{acceptance['note']}_")
    add("")

    add("## The reconstruction gate")
    add("")
    add(
        "Before any speculative arithmetic runs, every feasible point in every study is rebuilt "
        "from its own published terms and must reproduce its published step time to 1e-9 relative."
    )
    add("")
    add("| study | feasible points checked | failures |")
    add("| --- | ---: | ---: |")
    for study in payload["studies"]:
        gate = study["reconstruction_gate"]
        add(f"| `{study['study_id']}` | {gate['feasible_points_checked']:,} | {gate['failures']} |")
    add("")
    add(f"The identity checked is: `{payload['studies'][0]['reconstruction_gate']['statement']}`.")
    add("")

    add("## Headline: where speculation cannot pay at any acceptance rate")
    add("")
    add(
        "Counted at the LOW end of the unsourced drafter-KV band, which is the most favourable "
        "assumption available to speculation. `tau*` is the break-even acceptance at this "
        "profile's served block size."
    )
    add("")
    add("| study | model | family | draft placement | binds on (autoregressive) | points | cannot pay at any gamma | tau* min | tau* median | tau* max |")
    add("| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |")
    for study in payload["studies"]:
        for bucket in study["break_even_census"]["buckets"]:
            add(
                f"| `{study['study_id']}` | {bucket['model']} | `{bucket['family']}` | "
                f"`{bucket['draft_placement']}` | `{bucket['autoregressive_binding_constraint']}` | "
                f"{bucket['points']:,} | {bucket['cannot_pay_at_any_gamma']:,} | "
                f"{_n(bucket.get('tau_break_served_min'), 2)} | {_n(bucket.get('tau_break_served_median'), 2)} | "
                f"{_n(bucket.get('tau_break_served_max'), 2)} |"
            )
    add("")

    add("## Per model, per context, per batch and per design class")
    add("")
    add(
        "Each row is that class's **fastest** feasible design at that batch, read against the "
        "iso-area GPU comparator the published study already chose for it. The `densest` pick of "
        "every class is in `analytical.json` beside it."
    )
    add("")
    add(
        "**The ROM-versus-GPU ratio under speculation is `T_cycle(GPU) / T_cycle(ROM)` and carries "
        "no `tau` at all.** The acceptance length is a property of the model and its drafter, not "
        "of the machine, so it is the same on both sides and cancels out of the ratio. Every "
        "movement in the last column is therefore a machine effect and nothing else."
    )
    add("")
    for study in payload["studies"]:
        add(f"### `{study['study_id']}`")
        add("")
        rows = [row for row in study["class_table"] if row["pick"] == "fastest"]
        if not rows:
            add("_no class rows._")
            add("")
            continue
        add(
            "| model | ctx | batch | class | ROM design | AR ROM tok/s | spec ROM tok/s (tau "
            f"{tau_low:.2f}-{tau_high:.2f}) | ROM tau* | ROM pays | iso-area GPU | AR GPU tok/s | spec GPU tok/s | GPU tau* | GPU pays | AR ratio | spec ratio | ratio move |"
        )
        add("| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |")
        for row in rows:
            spec = (row.get("speculative") or {}).get("in_rom/low")
            if spec is None:
                add(
                    f"| {row['model']} | {row['context_tokens']:,} | {row['batch_size']} | "
                    f"`{row['design_class']}` | `{row['rom_design'].split('/')[-1]}` | "
                    f"{_n(row['autoregressive_rom_per_user_tokens_s'])} | not applicable | -- | -- | "
                    f"`{str(row.get('iso_area_gpu_design', '--')).split('/')[-1]}` | "
                    f"{_n(row.get('autoregressive_iso_area_gpu_per_user_tokens_s'))} | not applicable | -- | -- | "
                    f"{_n(row.get('autoregressive_ratio'), 3)}x | -- | -- |"
                )
                continue
            add(
                f"| {row['model']} | {row['context_tokens']:,} | {row['batch_size']} | "
                f"`{row['design_class']}` | `{row['rom_design'].split('/')[-1]}` | "
                f"{_n(row['autoregressive_rom_per_user_tokens_s'])} | "
                f"{_n(spec.get('rom_per_user_tokens_s_at_tau_low'))}-{_n(spec.get('rom_per_user_tokens_s_at_tau_high'))} | "
                f"{_n(spec.get('rom_tau_break'), 2)} | "
                f"{'yes' if spec.get('rom_pays_at_best_sourced_tau') else '**no**'} | "
                f"`{str(row.get('iso_area_gpu_design', '--')).split('/')[-1]}` | "
                f"{_n(row.get('autoregressive_iso_area_gpu_per_user_tokens_s'))} | "
                f"{_n(spec.get('gpu_per_user_tokens_s_at_tau_low'))}-{_n(spec.get('gpu_per_user_tokens_s_at_tau_high'))} | "
                f"{_n(spec.get('gpu_tau_break'), 2)} | "
                f"{'yes' if spec.get('gpu_pays_at_best_sourced_tau') else '**no**'} | "
                f"{_n(row.get('autoregressive_ratio'), 3)}x | {_n(spec.get('speculative_ratio'), 3)}x | "
                f"{_n(spec.get('ratio_movement_x'), 3)}x |"
            )
        add("")
        movements = [
            row["speculative"]["in_rom/low"]["ratio_movement_x"]
            for row in rows
            if row.get("speculative") and "in_rom/low" in row["speculative"]
            and row["speculative"]["in_rom/low"].get("ratio_movement_x") is not None
        ]
        if movements:
            compressing = sum(1 for value in movements if value < 1.0)
            add(
                f"**Does the ratio compress?** Of {len(movements)} class rows in this study, "
                f"{compressing} move the ROM-versus-GPU ratio DOWN under speculation and "
                f"{len(movements) - compressing} move it UP. The movement spans "
                f"{min(movements):.3f}x to {max(movements):.3f}x. "
                + (
                    "The ratio compresses: speculation is worth more to the GPU comparator than "
                    "to the ROM design on most of this study's operating points."
                    if compressing > len(movements) / 2
                    else "The ratio does not compress on most of this study's operating points."
                )
            )
            add("")
            both = [
                row
                for row in rows
                if row.get("speculative") and "in_rom/low" in row["speculative"]
            ]
            rom_pays = sum(1 for row in both if row["speculative"]["in_rom/low"].get("rom_pays_at_best_sourced_tau"))
            gpu_pays = sum(1 for row in both if row["speculative"]["in_rom/low"].get("gpu_pays_at_best_sourced_tau"))
            add(
                "**A moving ratio is not a win for either side.** At the most favourable sourced "
                f"acceptance ({tau_high:.2f}) speculation is worth having on {rom_pays} of "
                f"{len(both)} ROM rows and {gpu_pays} of {len(both)} GPU rows; on every other row "
                "the honest reading is that the design runs SLOWER with a drafter than without "
                "one. Where both sides lose, a ratio that rises means only that the comparator "
                "lost more."
            )
            add("")

    add("## Where the drafter lives on a ROM machine")
    add("")
    add(
        "The locality rule -- `stored/peak` is a technology constant -- is the load-bearing "
        "assumption of the whole ROM verdict. A pass that reads only the drafter's region uses "
        "only that region's read ports and takes exactly as long as sweeping the entire array. "
        "Two placements are therefore priced side by side, and the second is an architectural "
        "proposal this study **has not costed in silicon area**."
    )
    add("")
    add(
        "The same rule is what makes a SEQUENTIAL draft step expensive here. A per-position "
        "operation that moves only a small table is nearly free on a global-bandwidth store and "
        "costs a full array sweep on this one, so a drafter with `gamma` sequential applications "
        "pays `gamma` sweeps for them. That term is charged in full below; on a bandwidth store "
        "the bytes it moves are not separately charged at all, because this repository's model "
        "configs carry no size for the table -- an omission whose size, on "
        "DeepSeek-V4-Pro-0813, is the externally published 132,382,720 B per draft token, 0.33% "
        "of the 39,666,603,980 B target pass."
    )
    add("")
    add("| study | model | ctx | batch | class | design | tau* draft in ROM | tau* draft in KV store | KV placement feasible | why not |")
    add("| --- | --- | ---: | ---: | --- | --- | ---: | ---: | --- | --- |")
    for study in payload["studies"]:
        for row in study["class_table"]:
            if row["pick"] != "fastest" or not row.get("speculative"):
                continue
            in_rom = row["speculative"].get("in_rom/low")
            in_kv = row["speculative"].get("in_kv_store/low")
            if in_rom is None or in_kv is None:
                continue
            add(
                f"| `{study['study_id']}` | {row['model']} | {row['context_tokens']:,} | "
                f"{row['batch_size']} | `{row['design_class']}` | "
                f"`{row['rom_design'].split('/')[-1]}` | {_n(in_rom.get('rom_tau_break'), 2)} | "
                f"{_n(in_kv.get('rom_tau_break'), 2)} | "
                f"{'yes' if in_kv.get('rom_placement_feasible') else 'NO'} | "
                f"{'--' if in_kv.get('rom_placement_feasible') else 'the KV store has no room for it'} |"
            )
    add("")

    add("## The capacity requirement, stated as a requirement")
    add("")
    add(
        "Every evaluated ROM design carries `weight_capacity_bytes == stored_weight_bytes` (the "
        "`romfill` variants reach 1.0039x), so no evaluated design has spare array for a drafter "
        "it does not already store. Re-solving the area split is `balanced_area_split`'s job and "
        "that file is not touched here, so what follows is a requirement -- this much extra array, "
        "or this much extra sweep on every pass -- and not a new design. **The "
        "speculative-optimal ROM design has not been computed, only bounded by the rungs that "
        "already exist.**"
    )
    add("")
    add("| study | model | design | drafter already in the checkpoint | extra stored bytes | extra array mm2 | as a fraction of the design | sweep inflation if area is held fixed |")
    add("| --- | --- | --- | --- | ---: | ---: | ---: | ---: |")
    for study in payload["studies"]:
        for row in study["capacity_requirements"]:
            add(
                f"| `{study['study_id']}` | {row['model']} | `{row['design'].split('/')[-1]}` | "
                f"{'YES -- it costs nothing extra to store' if row['drafter_already_in_checkpoint'] else 'no'} | "
                f"{_n(row['extra_stored_bytes_required'], 0)} | {_n(row['extra_array_mm2_required'], 1)} | "
                f"{_pct(row['extra_area_fraction'])} | {_n(row['sweep_inflation_if_area_held_fixed'], 4)}x |"
            )
    add("")

    add("## Which design the published rule chooses once a block is verified")
    add("")
    add(
        "A re-ranking of designs the study already evaluated, under the study's own selection "
        "rule (non-dominated on per-user tokens/s and tokens/s per 1,000 mm2, then a "
        "marginal-return walk from the smallest feasible machine). `tau` is a common factor on "
        "both axes, so the choice is independent of the acceptance rate. The rule's reproduction "
        "of the published autoregressive recommendation is reported first, because a re-ranking "
        "whose baseline does not reproduce is not evidence of anything."
    )
    add("")
    add("| study | model | published recommendation | rule reproduces it | under speculation, draft in ROM | draft in KV store | moves |")
    add("| --- | --- | --- | --- | --- | --- | --- |")
    for study in payload["studies"]:
        for row in study["selection_under_speculation"]:
            add(
                f"| `{study['study_id']}` | {row['model']} | `{row['published_recommendation'].split('/')[-1]}` | "
                f"{'yes' if row['rule_reproduces_published_recommendation'] else 'NO -- ' + str(row['rule_reproduction'])} | "
                f"`{str(row.get('speculative_recommendation_in_rom', '--')).split('/')[-1]}` | "
                f"`{str(row.get('speculative_recommendation_in_kv_store', '--')).split('/')[-1]}` | "
                + (
                    "the drafter does not apply to this model |"
                    if row.get("drafter_applies") is False
                    else "read nothing here: the baseline does not reproduce |"
                    if not row["rule_reproduces_published_recommendation"]
                    else ("yes |" if row.get("speculative_moves_the_choice_in_rom") else "no |")
                )
            )
    add("")
    walks = [row for study in payload["studies"] for row in study["selection_under_speculation"]]
    reproduced = sum(1 for row in walks if row["rule_reproduces_published_recommendation"])
    applicable = [row for row in walks if row.get("drafter_applies") is not False and row["rule_reproduces_published_recommendation"]]
    moved = sum(1 for row in applicable if row.get("speculative_moves_the_choice_in_rom"))
    add(
        f"**The rule reproduces the published autoregressive recommendation on {reproduced} of "
        f"{len(walks)} model-and-study rows.** Of the {len(applicable)} rows where it reproduces "
        f"and the drafter applies, verifying a block moves the chosen rung on {moved}. Where it "
        "moves, it moves toward machines with compute headroom for a block, which is exactly what "
        "the arithmetic predicts: a verification pass raises arithmetic intensity by the block "
        "size, and a machine sized with just enough compute for one token per sweep has no room "
        "for it. **This is a re-ranking of rungs that already exist. The speculative-optimal "
        "design has not been computed: that would need the area split re-solved, which is "
        "`balanced_area_split`'s job and not this layer's.**"
    )
    add("")

    gate = payload.get("dflash_overhead_gate")
    if gate:
        add("## Gate: the DFlash overhead factor")
        add("")
        add(f"_{gate['kind']}._")
        add("")
        add(f"- modelled on `{gate['modelled_on']}` at batch 1, {gate['modelled_context_tokens']:,} tokens of context, gamma {gate['modelled_gamma']}")
        add(f"- modelled overhead factor: **{gate['modelled_overhead_factor_draft_kv_low']:.3f}** with the drafter charged no KV, **{gate['modelled_overhead_factor_draft_kv_high']:.3f}** at the top of the band")
        add(f"- published band: {gate['published_band_low']:.2f}-{gate['published_band_high']:.2f}, outlier {gate['published_outlier']['workload']} at {gate['published_outlier']['value']:.2f}")
        add(f"- source: {gate['published_source']}")
        add(f"- inside the published band: **{'yes' if gate['inside_published_band'] else 'no'}**")
        add("")
        add(f"**Residual.** {gate['residual_statement']}")
        add("")
        add(f"**{gate['not_a_validation']}**")
        add("")

    reconciliation = payload.get("draft_traffic_reconciliation")
    if reconciliation:
        add("## The draft-traffic decomposition does not reproduce, and both readings are printed")
        add("")
        add(f"_{reconciliation['what_this_is']}_")
        add("")
        add(f"External source, graded `{reconciliation['external_grade']}`: {reconciliation['external_source']}")
        add("")
        add("| model | draft tokens | repository config bytes | as a fraction of the target pass | externally published bytes | as a fraction | repo / published |")
        add("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
        for row in reconciliation["rows"]:
            add(
                f"| {row['model']} | {row['draft_tokens']} | {_n(row['repository_config_bytes'], 0)} | "
                f"{_pct(row['repository_config_fraction_of_target_pass'])} | "
                f"{_n(row.get('externally_published_bytes'), 0)} | "
                f"{_pct(row.get('externally_published_fraction_of_target_pass'))} | "
                f"{_n(row.get('divergence_x'), 3)}x |"
            )
        add("")
        add(f"_{reconciliation['external_note']}_")
        add("")

    xiaomi = payload.get("xiaomi_cross_check")
    if xiaomi:
        add("## Cross-check: Xiaomi MiMo-V2.5-Pro-UltraSpeed")
        add("")
        add("**This is a cross-check. It is not a calibration target, and nothing in this study is fitted to it.**")
        add("")
        add(f"_{xiaomi['what_this_is']}_")
        add("")
        claim = xiaomi["claim"]
        add(
            f"Xiaomi reports **{claim['tokens_s']:,} tokens/s** decode on a "
            f"{claim['total_parameters'] / 1e12:.0f}-trillion-parameter model, with a figure caption "
            f"reading up to about {claim['figure_caption_tokens_s']:,} tokens/s, on "
            f"\"{claim['node']}\" ({claim['source']})."
        )
        add("")
        add("**What the blog does not state, and what therefore cannot be inferred from it:**")
        add("")
        for condition in xiaomi["unstated_conditions"]:
            add(f"- {condition}")
        add("")
        add("The claimed rate is the product of three stacked techniques, and Xiaomi explicitly declines to attribute it among them:")
        add("")
        for technique in xiaomi["stacked_techniques"]:
            add(f"- {technique}")
        add("")
        add("**How this study's model differs from that deployment:**")
        add("")
        for difference in xiaomi["differences_from_our_model"]:
            add(f"- {difference}")
        add("")
        add("**What our model says for the closest thing this study evaluates.**")
        add("")
        add(f"_{xiaomi['eight_device_statement']}_")
        add("")
        add(f"**{xiaomi['block_size_statement']}**")
        add("")
        add(
            "GPU cluster sizes this study evaluates for DeepSeek-V4-Pro-0813: "
            + ", ".join(str(value) for value in xiaomi["gpu_device_counts_evaluated_for_this_model"])
            + " packages."
        )
        add("")
        add(
            "DeepSeek-V4-Pro-0813 is 1.6 trillion total parameters with 49 billion active; the "
            "model Xiaomi describes is 1 trillion total, and its active count is ASSUMED at 42 "
            "billion -- the blog states no active parameter count, that figure comes from "
            "secondary reporting, and it is graded `assumed` here and used for nothing but this "
            "sentence. They are the same class and they are not the same model."
        )
        add("")
        add("| design | packages | batch | ctx | block (gamma) | positions verified | AR per-user tok/s | AR aggregate tok/s | resident sessions | binds on | tau* | coding tau 6.30 | maths tau 5.56 | agent tau 4.29 |")
        add("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |")
        for row in xiaomi["rows"]:
            by = row["speculative_by_workload"]
            add(
                f"| `{row['design'].split('/')[-1]}` | {row['device_count']} | {row['batch_size']} | {row['context_tokens']:,} | "
                f"{row['block_size']} | {row['positions_per_verify']} | "
                f"{_n(row['autoregressive_per_user_tokens_s'], 2)} | {_n(row['autoregressive_aggregate_tokens_s'], 0)} | "
                f"{_n(row['resident_sessions'], 0)} | `{row['binding_constraint']}` | "
                f"{_n(row['tau_break_draft_kv_low'], 2)} | "
                f"{_n(by.get('coding', {}).get('per_user_tokens_s_draft_kv_low'), 2)} | "
                f"{_n(by.get('maths and reasoning', {}).get('per_user_tokens_s_draft_kv_low'), 2)} | "
                f"{_n(by.get('agent', {}).get('per_user_tokens_s_draft_kv_low'), 2)} |"
            )
        add("")
        add(
            "The per-user columns are what one session sees; the aggregate column is what the "
            "machine delivers with every slot full. Xiaomi does not say which of those two its "
            "number is, and the two differ here by orders of magnitude, so the comparison cannot "
            "be closed from the published side."
        )
        add("")

    add("## Evidence ledger")
    add("")
    add("| grade | entries |")
    add("| --- | ---: |")
    for grade, entries in sorted(payload["graded_inputs"].items()):
        add(f"| `{grade}` | {len(entries)} |")
    add("")
    for grade, entries in sorted(payload["graded_inputs"].items()):
        add(f"**`{grade}`**: " + "; ".join(f"`{entry}`" for entry in entries))
        add("")
    add("## What would change the answer")
    add("")
    for item in payload["open_questions"]:
        add(f"- {item}")
    add("")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------


def discover_sources() -> list[Path]:
    """Every roofline artifact this layer reads, excluding its own output tree."""

    found = []
    for path in sorted(SOURCE_ROOT.rglob("analytical.json")):
        if OUTPUT_ROOT in path.parents:
            continue
        found.append(path)
    return found


def _display(path: Path) -> str:
    """A path as a reader would cite it: repository-relative where it can be."""

    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def _guard_output(path: Path) -> None:
    """Refuse to write anywhere in this repository except this layer's own tree.

    A path outside the repository -- a scratch directory, a test's temporary
    directory -- is allowed, because the thing being protected is the committed
    evidence, not the filesystem.  A path inside the repository that is not
    under ``results/roofline/speculative/`` is refused, which is what keeps this
    layer additive: it can never overwrite the roofline artifacts it reads.
    """

    resolved = path.resolve()
    repository = ROOT.resolve()
    output = OUTPUT_ROOT.resolve()
    inside_repository = resolved == repository or repository in resolved.parents
    inside_output = resolved == output or output in resolved.parents
    if inside_repository and not inside_output:
        raise SystemExit(
            f"refusing to write {path}: inside this repository this tool writes only under "
            f"{OUTPUT_ROOT.relative_to(ROOT)}, so that the roofline artifacts it reads can "
            "never be overwritten by it"
        )


def build_payload(
    profile_name: str,
    config: dict,
    technology: Technology,
    sources: list[Path],
    verify_shas: bool,
) -> dict:
    profile = config["profiles"][profile_name]
    for path, entry in _graded_rows(profile):
        if "source" not in entry and "evidence" not in entry:
            raise SystemExit(f"profile {profile_name}: graded entry {path!r} carries no source")
        if entry["grade"] not in ("measured", "executed", "published", "derived", "assumed"):
            raise SystemExit(
                f"profile {profile_name}: entry {path!r} is graded {entry['grade']!r}, which is "
                "not one of the grades configs/hardware/technology.json defines"
            )
    if "acceptance_length" not in profile:
        raise SystemExit(f"profile {profile_name}: no acceptance_length block")
    acceptance = profile["acceptance_length"]
    if "grade" not in acceptance or "source" not in acceptance:
        raise SystemExit(f"profile {profile_name}: acceptance_length carries no grade or no source")

    studies = []
    for source in sources:
        study = process_study(
            source,
            profile_name,
            profile,
            technology,
            [int(value) for value in config["gamma_ladder"]],
            verify_shas,
        )
        study["class_table"] = class_table(study, profile)
        study["break_even_census"] = break_even_census(study)
        study["capacity_requirements"] = capacity_requirements(study, technology)
        study["selection_under_speculation"] = selection_under_speculation(study, profile)
        studies.append(study)

    headline_study = next(
        (study for study in studies if study["study_id"] == "n5_vs_b200"), studies[0] if studies else None
    )
    gate = dflash_overhead_gate(headline_study, profile, config) if headline_study else None
    xiaomi = xiaomi_cross_check(studies, profile, config) if studies else None
    every_model: dict[str, ModelProfile] = {}
    for source in sources:
        for name, entry in json.loads(source.read_text())["inputs"]["models"].items():
            every_model.setdefault(name, ModelProfile.load(ROOT / entry["path"]))
    reconciliation = draft_traffic_reconciliation(profile, every_model)

    graded: dict[str, list[str]] = {}
    for path, entry in sorted(_graded_rows(profile)):
        graded.setdefault(entry["grade"], []).append(path)

    payload = {
        "schema_version": 1,
        "artifact_id": f"speculative-{profile_name}",
        "profile_name": profile_name,
        "profile": profile,
        "produced_by": {
            "tool": "tools/run_speculative_roofline.py",
            "reads": [str(path.relative_to(ROOT)) for path in sources],
            "writes_only_under": str(OUTPUT_ROOT.relative_to(ROOT)),
            "does_not_import": "tools/run_roofline_studies.py",
            "does_not_call": "opentallas.roofline.evaluate",
        },
        "inputs": {
            "profile_config": str(PROFILE_PATH.relative_to(ROOT)),
            "profile_config_sha256": _sha256(PROFILE_PATH),
            "technology_config": str(TECHNOLOGY_PATH.relative_to(ROOT)),
            "technology_sha256": _sha256(TECHNOLOGY_PATH),
            "input_pins_verified": verify_shas,
        },
        "method": {
            "cycle": "T_cycle = T_verify + T_draft, thermally stretched by the cycle's own dynamic energy",
            "break_even": "tau* = T_cycle / step_time_s; speculation pays iff tau >= tau*, and tau <= gamma+1 always",
            "ratio": (
                "the ROM-versus-GPU per-user ratio under speculation is T_cycle(GPU)/T_cycle(ROM) "
                "and contains no tau: the acceptance length is a property of the model and its "
                "drafter, not of the machine, so it is identical on both sides and cancels"
            ),
            "drafter_kv": (
                "unsourced for both drafters and therefore published as a band [0, K x draft_layers "
                "/ num_layers], never as a point value"
            ),
            "sequential_draft_passes": (
                "on a ROM machine each sequential draft application costs a full array sweep, "
                "because stored/peak is a technology constant. On a global-bandwidth store the "
                "bytes those applications move are not separately charged: the repository's model "
                "configs carry no size for the drafter's bias table. For DeepSeek-V4-Pro-0813 the "
                "externally published slope is 132,382,720 B per draft token, 0.33% of the "
                "39,666,603,980 B target pass, which is the size of the omission."
            ),
        },
        "graded_inputs": graded,
        "studies": studies,
        "dflash_overhead_gate": gate,
        "xiaomi_cross_check": xiaomi,
        "draft_traffic_reconciliation": reconciliation,
        "open_questions": [
            "The drafter's own KV traffic is not sourced for either drafter and is published as a "
            "band. DFlash injects target hidden features from five uniformly selected layers as "
            "Key/Value into every draft layer and gives no byte count; DSpark's three MTP stages "
            "carry their own cache and the paper gives no byte count. At 200K-1M context this term "
            "could dominate the draft pass.",
            "The ROM draft sweep is the largest single modelled penalty and it rests entirely on "
            "the locality rule in src/opentallas/roofline.py. If a designer replicates the drafter "
            "across the array, gives it dedicated wide ports, or holds it off-array, the draft "
            "weight term collapses and the ROM verdict can change sign. The alternative placement "
            "is priced beside it and has not been costed in silicon area.",
            "The compute headroom that decides whether a verification block flips a design from "
            "memory-bound to compute-bound is downstream of the compute efficiency derate, which "
            "is graded `assumed` at 0.55 and has never been measured. The block size at which the "
            "flip happens is reported on every point so the exposure is visible.",
            "The DeepSeek-V4-Pro-0813 draft-traffic decomposition published externally "
            "(3,770,773,788 B constant plus 132,382,720 B per draft token) does not reproduce from "
            "this repository's own configs/models/deepseek-v4-pro-0813.json inventory. Both are "
            "reported; neither is silently preferred.",
            "No speculative decoder has been executed anywhere in this repository. Every rate here "
            "is modelled, and the acceptance lengths that turn a break-even into a speedup were "
            "measured by other people on other hardware.",
        ],
    }
    return payload


#: Significant digits kept in the per-point census.  The census exists to make
#: every verdict auditable, not to be re-differentiated; the designs the report
#: actually quotes are carried at full precision in ``detail`` beside it.  The
#: rounding is deterministic, so two runs remain byte-identical.
CENSUS_SIGNIFICANT_DIGITS = 6


def _round(value: Any) -> Any:
    if isinstance(value, float):
        if not math.isfinite(value) or value == 0.0:
            return value
        digits = CENSUS_SIGNIFICANT_DIGITS - 1 - int(math.floor(math.log10(abs(value))))
        return round(value, digits)
    if isinstance(value, list):
        return [_round(item) for item in value]
    return value


def _census_row(row: dict) -> dict:
    """One auditable line per feasible point: the verdict and what decides it."""

    compact = {
        key: row[key]
        for key in (
            "design",
            "model",
            "family",
            "topology_kind",
            "weight_store",
            "kv_store",
            "weight_amortization",
            "context_tokens",
            "batch_size",
            "device_count",
            "silicon_area_mm2",
            "binding_constraint",
            "drafter_applies",
        )
    }
    compact["step_time_s"] = _round(row["step_time_s"])
    compact["per_user_tokens_s"] = _round(row["per_user_tokens_s"])
    variants = {}
    for placement, variant in row["variants"].items():
        low = variant["served"]["low"]
        high = variant["served"]["high"]
        variants[placement] = {
            "gamma": low["gamma"],
            "tau_cap": low["tau_cap"],
            "tau_break_draft_kv_low": _round(low["tau_break"]),
            "tau_break_draft_kv_high": _round(high["tau_break"]),
            "cycle_s_draft_kv_low": _round(low["cycle_s"]),
            "draft_share_of_cycle": _round(low["draft_share_of_cycle"]),
            "spec_binding_constraint": low["spec_binding_constraint"],
            "storage_inflation": _round(low["storage_inflation"]),
            "placement_feasible": variant["placement_feasible"],
            "cannot_pay_at_any_gamma": variant["cannot_pay_at_any_gamma"],
            "tau_break_by_gamma_draft_kv_low": _round(variant["tau_break_by_gamma_low"]),
        }
    compact["variants"] = variants
    return compact


def _quoted_keys(study: dict) -> set[tuple[str, int, int]]:
    keys: set[tuple[str, int, int]] = set()
    for row in study["class_table"]:
        keys.add((row["rom_design"], row["batch_size"], row["context_tokens"]))
        if row.get("iso_area_gpu_design"):
            keys.add((row["iso_area_gpu_design"], row["batch_size"], row["context_tokens"]))
    for row in study["selection_under_speculation"]:
        for key in ("published_recommendation", "speculative_recommendation_in_rom", "speculative_recommendation_in_kv_store"):
            name = row.get(key)
            if name:
                keys.add((name, 1, row["context_tokens"]))
    return keys


def strip_private(payload: dict) -> dict:
    """Drop the working state and shrink ``points`` to an auditable census.

    ``detail`` keeps the full decomposition for exactly the designs the report
    quotes, so nothing the report says rests on a rounded number.
    """

    for study in payload["studies"]:
        quoted = _quoted_keys(study)
        detail = [
            row
            for row in study["points"]
            if (row["design"], row["batch_size"], row["context_tokens"]) in quoted
        ]
        study["detail"] = detail
        study["points"] = [_census_row(row) for row in study["points"]]
        study["points_note"] = (
            "One line per feasible point of the source study, rounded to "
            f"{CENSUS_SIGNIFICANT_DIGITS} significant digits. The designs the report quotes are "
            "carried at full precision in `detail`."
        )
        study.pop("_lookup", None)
        study.pop("_body", None)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", action="append", default=None, help="profile name; repeatable, default every profile")
    parser.add_argument("--study", action="append", default=None, help="study id or path fragment; repeatable, default every study")
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--force", action="store_true", help="overwrite an existing artifact")
    parser.add_argument("--list", action="store_true", help="list the artifacts this layer would read and exit")
    args = parser.parse_args()

    config = json.loads(PROFILE_PATH.read_text())
    sources = discover_sources()
    if args.study:
        wanted = [str(value) for value in args.study]
        # Match on the path first: reading a study id means parsing an
        # eighty-megabyte artifact, and there is no reason to do that for every
        # source when the caller named a directory.
        selected = [
            path for path in sources if any(value in str(path.relative_to(ROOT)) for value in wanted)
        ]
        if not selected:
            selected = [
                path for path in sources if json.loads(path.read_text())["study_id"] in wanted
            ]
        sources = selected
    if args.list:
        for path in sources:
            print(path.relative_to(ROOT))
        return 0
    if not sources:
        raise SystemExit("no roofline artifacts matched; nothing to read")

    profiles = args.profile or sorted(config["profiles"])
    unknown = [name for name in profiles if name not in config["profiles"]]
    if unknown:
        raise SystemExit(f"unknown profile(s): {unknown}. Known: {sorted(config['profiles'])}")

    technology = Technology.load(TECHNOLOGY_PATH)
    output_root = args.output_root
    # Refuse before doing the work, not after: reading sixteen roofline
    # artifacts takes a while and a caller who forgot --force should be told
    # immediately.
    planned = {}
    for name in profiles:
        directory = output_root / name
        _guard_output(directory)
        analytical = directory / "analytical.json"
        markdown = directory / "REPORT.md"
        for path in (analytical, markdown):
            _guard_output(path)
            if path.exists() and not args.force:
                raise SystemExit(f"{_display(path)} exists; pass --force to overwrite")
        planned[name] = (directory, analytical, markdown)

    for name in profiles:
        directory, analytical, markdown = planned[name]
        payload = build_payload(name, config, technology, sources, verify_shas=True)
        report = render_report(payload)
        strip_private(payload)
        directory.mkdir(parents=True, exist_ok=True)
        analytical.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        markdown.write_text(report, encoding="utf-8")
        total = sum(len(study["points"]) for study in payload["studies"])
        print(
            f"{name}: {len(payload['studies'])} studies, {total:,} feasible points, "
            f"-> {_display(analytical)} ({analytical.stat().st_size / 1e6:.1f} MB), "
            f"{_display(markdown)} ({markdown.stat().st_size / 1e3:.0f} kB)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
