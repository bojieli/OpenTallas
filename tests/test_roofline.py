"""Tests for the area-constrained roofline model and its validation gates.

The two named gates -- ``test_gate_taalas_hc1_...`` and
``test_gate_a100_...`` -- are the load-bearing checks.  They fail loudly if the
methodology drifts, and they are deliberately written to say *how far* off the
model is rather than only that it is off, because the interesting failure is a
technology input that turns out to be wrong rather than a broken assertion.
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
from types import ModuleType

import pytest

from opentallas.roofline import (
    GRADES,
    Graded,
    Technology,
    Topology,
    a100_weight_bound_anchor,
    balanced_area_split,
    derived,
    evaluate,
    gpu_device_budget,
    latency_crossover,
    max_hbm_stacks_per_device,
    rom_device_budget,
    taalas_hc1_anchor,
)
from opentallas.schema import ModelProfile, ValidationError
from opentallas.workload import expected_expert_coverage, kv_traffic


ROOT = Path(__file__).resolve().parents[1]
TECHNOLOGY_PATH = ROOT / "configs" / "hardware" / "technology.json"
RUNNER = ROOT / "tools" / "run_roofline_studies.py"
CHECKED_IN = ROOT / "results" / "roofline"
ARTIFACTS = ("analytical.json", "sweep.csv", "REPORT.md")


@pytest.fixture(scope="module")
def technology() -> Technology:
    return Technology.load(TECHNOLOGY_PATH)


@pytest.fixture(scope="module")
def llama() -> ModelProfile:
    return ModelProfile.load(
        ROOT / "configs" / "models" / "anchors" / "llama-3.1-8b.json"
    )


@pytest.fixture(scope="module")
def qwen() -> ModelProfile:
    return ModelProfile.load(ROOT / "configs" / "models" / "qwen3-8b.json")


@pytest.fixture(scope="module")
def flash() -> ModelProfile:
    return ModelProfile.load(
        ROOT / "configs" / "models" / "deepseek-v4-flash-0731.json"
    )


def _single_chip(link: str = "none") -> Topology:
    return Topology(kind="single_chip", device_count=1, parallelism="none", link=link)


def _rom_chip(
    technology: Technology,
    model: ModelProfile,
    *,
    area_mm2: float = 815.0,
    node: str = "N6",
    context: int = 2048,
    batch: int = 1,
    bits: float | None = 4.0,
):
    stored = (
        model.checkpoint_bytes
        if bits is None
        else model.total_parameters * bits / 8.0
    )
    resident = kv_traffic(model, context).storage_bytes_per_user * batch
    return rom_device_budget(
        technology,
        name="test-rom",
        node=node,
        area_mm2_per_device=area_mm2,
        topology=_single_chip(),
        stored_weight_bytes=stored,
        resident_kv_bytes=resident,
        kv_store="sram",
    )


# --------------------------------------------------------------------------
# THE VALIDATION GATES
# --------------------------------------------------------------------------


def test_gate_taalas_hc1_shipping_part_is_reproduced(technology, llama) -> None:
    """An 8B model on 815 mm2 at N6 with mask-ROM weights must come out near 17,000.

    A model that cannot reproduce a shipping part must not be used to predict
    one that does not exist.  If this fails, the densities or the roofline
    combination are wrong -- do NOT relax the tolerance.
    """

    check = taalas_hc1_anchor(technology, llama)
    requirements = check.detail["back_derived_requirements"]
    assert check.passed, (
        f"HC1 anchor drifted: modelled {check.modelled_value:,.0f} tok/s against a "
        f"published {check.published_value:,.0f} tok/s ({check.ratio:.3f}x), binding "
        f"on {check.detail['binding_constraint']}. To land on the published figure "
        f"the ROM read bandwidth density would have to be "
        f"{requirements['rom_density_shortfall_x']:.2f}x the derived value and the "
        f"compute density {requirements['compute_density_shortfall_x']:.2f}x."
    )
    # Both back-derived requirements must stay physically unremarkable. A model
    # that needs an order of magnitude more of either has stopped being a model.
    assert requirements["rom_density_shortfall_x"] < 2.0
    assert requirements["compute_density_shortfall_x"] < 2.0


def test_gate_taalas_hc1_compute_density_matches_the_shipping_part(
    technology, llama
) -> None:
    """The compute density derived from A100's published roofs should be close.

    This is the strongest single piece of evidence that the area-to-compute
    chain is right: an independent shipping part, a different vendor and a
    different node land within a few percent of each other.
    """

    check = taalas_hc1_anchor(technology, llama)
    shortfall = check.detail["back_derived_requirements"][
        "compute_density_shortfall_x"
    ]
    assert 0.8 < shortfall < 1.25, (
        "the compute density this model derives from published GPU roofs is "
        f"{shortfall:.3f}x what the Taalas HC1 must have; the derivation has drifted"
    )


def test_gate_a100_weight_bound_is_exact_arithmetic(technology, llama) -> None:
    """2,039 GB/s divided by 8.03 GB of FP8 checkpoint is 253.9 tok/s.

    Pure arithmetic on published numbers.  Any deviation is a bug, so this runs
    on the ideal roofline with every derate at 1.0.
    """

    check = a100_weight_bound_anchor(technology, llama)
    bandwidth = 2.039e12
    stored = llama.total_parameters * 8.0 / 8.0
    assert check.published_value == pytest.approx(bandwidth / stored, rel=1e-12)
    assert check.published_value == pytest.approx(253.9, abs=0.5)
    assert check.modelled_value == pytest.approx(check.published_value, rel=1e-9)
    assert check.passed
    assert check.detail["binding_constraint"] == "weight_read"


def test_gate_a100_bf16_is_half_the_fp8_rate(technology, llama) -> None:
    check = a100_weight_bound_anchor(
        technology, llama, weight_bits_per_parameter=16.0
    )
    assert check.modelled_value == pytest.approx(126.96, abs=0.5)


# --------------------------------------------------------------------------
# graded inputs
# --------------------------------------------------------------------------


def test_every_technology_input_is_graded_with_a_source(technology) -> None:
    """An ungraded assumption is the failure mode this program exists to prevent."""

    buckets = technology.inputs_by_grade()
    assert set(buckets) == set(GRADES)
    assert sum(len(paths) for paths in buckets.values()) > 50
    assert buckets["published"], "no published inputs found"

    def walk(node, path):
        if isinstance(node, dict):
            if "grade" in node or "source" in node or "value" in node:
                if {"grade", "source", "value"} <= set(node):
                    assert node["grade"] in GRADES, path
                    assert str(node["source"]).strip(), path
                    return
            for key, value in node.items():
                walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]")

    walk(technology.raw, "technology")


def test_graded_rejects_an_unknown_grade_or_missing_source() -> None:
    with pytest.raises(ValidationError):
        Graded(value=1.0, grade="probably", source="x")
    with pytest.raises(ValidationError):
        Graded(value=1.0, grade="published", source="   ")


def test_a_derivation_inherits_the_weakest_input_grade() -> None:
    published = Graded(value=2.0, grade="published", source="p")
    assumed = Graded(value=3.0, grade="assumed", source="a")
    assert derived(6.0, (published, published), "x*y").grade == "derived"
    assert derived(6.0, (published, assumed), "x*y").grade == "assumed"
    assert "p" in derived(6.0, (published, assumed), "x*y").source


def test_the_assumed_inputs_are_the_ones_we_expect(technology) -> None:
    """Pin the assumption surface so a new one cannot be added silently."""

    assumed = set(technology.inputs_by_grade()["assumed"])
    for path in (
        "rom.cell_to_sram_cell_area_ratio",
        "rom.array_efficiency",
        "sram.array_efficiency",
        "efficiencies.compute",
        "efficiencies.rom_read_bandwidth",
        "links.nvlink.hop_latency_s",
        "links.on_wafer.hop_latency_s",
    ):
        assert path in assumed, f"{path} should be graded assumed"
    assert "compute.format_roofs_ops_s.bf16" not in assumed


# --------------------------------------------------------------------------
# derived densities: the area -> capacity/bandwidth/compute chain
# --------------------------------------------------------------------------


def test_sram_capacity_density_is_the_bitcell_over_array_efficiency(
    technology,
) -> None:
    cell = technology.graded("nodes", "N7", "sram_hd_bitcell_um2").value
    efficiency = technology.graded("sram", "array_efficiency").value
    assert technology.sram_bits_per_mm2("N7").value == pytest.approx(
        1e6 / (cell / efficiency)
    )


def test_rom_capacity_density_is_the_scaled_bitcell(technology) -> None:
    cell = technology.graded("nodes", "N6", "sram_hd_bitcell_um2").value
    ratio = technology.graded("rom", "cell_to_sram_cell_area_ratio").value
    efficiency = technology.graded("rom", "array_efficiency").value
    assert technology.rom_bits_per_mm2("N6").value == pytest.approx(
        1e6 / (cell * ratio / efficiency)
    )


def test_rom_capacity_density_inherits_the_assumed_grade(technology) -> None:
    assert technology.rom_bits_per_mm2("N6").grade == "assumed"


def test_rom_read_bandwidth_scales_by_the_published_bitcell_ratio(
    technology,
) -> None:
    anchor = technology.raw["rom"]["read_bandwidth_anchor"]
    base = (
        anchor["operations_s"]["value"]
        / anchor["operations_per_weight"]["value"]
        * anchor["weight_bits"]["value"]
        / 8.0
        / anchor["macro_area_mm2"]["value"]
    )
    scale = (
        anchor["anchor_node_sram_hd_bitcell_um2"]["value"]
        / technology.graded("nodes", "N6", "sram_hd_bitcell_um2").value
    )
    assert technology.rom_read_bytes_s_per_mm2("N6").value == pytest.approx(
        base * scale
    )


def test_compute_density_reproduces_the_anchor_part_exactly(technology) -> None:
    """A100's own die area times its derived density must give its published roof."""

    density = technology.compute_ops_s_per_mm2("N7", "bf16").value
    assert density * 826.0 == pytest.approx(3.12e14, rel=1e-12)
    assert technology.compute_ops_s_per_mm2("N7", "fp8").value * 826.0 == (
        pytest.approx(6.24e14, rel=1e-12)
    )
    assert technology.compute_ops_s_per_mm2("N7", "fp4").value * 826.0 == (
        pytest.approx(1.248e15, rel=1e-12)
    )


def test_w4a8_density_is_the_geometric_mean_of_the_published_endpoints(
    technology,
) -> None:
    low = technology.compute_ops_s_per_mm2("N6", "fp8").value
    high = technology.compute_ops_s_per_mm2("N6", "fp4").value
    assert technology.compute_ops_s_per_mm2("N6", "w4a8").value == pytest.approx(
        math.sqrt(low * high)
    )
    assert low < technology.compute_ops_s_per_mm2("N6", "w4a8").value < high


def test_node_scaling_uses_the_published_logic_density_ratio(technology) -> None:
    n7 = technology.compute_ops_s_per_mm2("N7", "bf16").value
    n6 = technology.compute_ops_s_per_mm2("N6", "bf16").value
    assert n6 / n7 == pytest.approx(1.18)


def test_the_rom_sweep_time_is_a_node_independent_technology_constant(
    technology,
) -> None:
    """Sweep time is capacity density over bandwidth density.

    Both scale with the same published bitcell-area ratio, so process scaling
    buys a ROM design capacity and not per-token speed.  If this test starts
    failing, someone has credited a clock bonus to one side and not the other --
    which may well be right, but it changes the headline result and must be
    deliberate.
    """

    times = []
    for node in ("N7", "N6", "N5", "4NP"):
        capacity = technology.rom_bits_per_mm2(node).value / 8.0
        bandwidth = technology.rom_read_bytes_s_per_mm2(node).value
        times.append(capacity / bandwidth)
    assert all(value == pytest.approx(times[0]) for value in times)


def test_ideal_technology_zeroes_every_derate(technology) -> None:
    ideal = technology.ideal()
    for name in ("compute", "rom_read_bandwidth", "hbm_bandwidth", "stage_balance"):
        assert ideal.efficiency(name).value == 1.0
        assert technology.efficiency(name).value < 1.0


# --------------------------------------------------------------------------
# area allocation
# --------------------------------------------------------------------------


def test_area_split_accounts_for_every_square_millimetre(technology, llama) -> None:
    budget = _rom_chip(technology, llama)
    split = budget.split
    assert split.allocated_mm2 == pytest.approx(split.total_mm2)
    assert split.slack_mm2 == pytest.approx(0.0, abs=1e-6)
    assert sum(split.fractions().values()) == pytest.approx(1.0)
    assert split.compute_mm2 > 0


def test_capacity_and_bandwidth_are_derived_from_the_split_not_supplied(
    technology, llama
) -> None:
    budget = _rom_chip(technology, llama)
    density = technology.rom_bits_per_mm2("N6").value / 8.0
    bandwidth = (
        technology.rom_read_bytes_s_per_mm2("N6").value
        * technology.efficiency("rom_read_bandwidth").value
    )
    assert budget.weight_capacity_bytes == pytest.approx(
        budget.split.rom_mm2 * density
    )
    assert budget.weight_read_bytes_s == pytest.approx(
        budget.split.rom_mm2 * bandwidth
    )
    sram_density = technology.sram_bits_per_mm2("N6").value / 8.0
    assert budget.kv_capacity_bytes == pytest.approx(
        budget.split.sram_mm2 * sram_density
    )
    for canonical, roof in budget.compute_ops_s.items():
        expected = (
            budget.split.compute_mm2
            * technology.compute_ops_s_per_mm2("N6", canonical).value
        )
        assert roof == pytest.approx(expected)


def test_a_split_that_leaves_no_compute_area_reports_a_reason(technology) -> None:
    split = balanced_area_split(
        technology,
        node="N6",
        total_mm2=100.0,
        weight_store="rom",
        kv_store="sram",
        stored_weight_bytes=100e9,
        resident_kv_bytes=0.0,
    )
    assert split.compute_mm2 == 0.0
    assert any(reason.startswith("AREA") for reason in split.reasons)


def test_a_negative_area_is_rejected(technology) -> None:
    from opentallas.roofline import AreaSplit

    with pytest.raises(ValidationError):
        AreaSplit(
            total_mm2=100.0,
            rom_mm2=-1.0,
            compute_mm2=1.0,
            sram_mm2=0.0,
            interconnect_mm2=0.0,
            hbm_phy_mm2=0.0,
            overhead_mm2=0.0,
            policy="test",
        )
    with pytest.raises(ValidationError):
        AreaSplit(
            total_mm2=0.0,
            rom_mm2=0.0,
            compute_mm2=0.0,
            sram_mm2=0.0,
            interconnect_mm2=0.0,
            hbm_phy_mm2=0.0,
            overhead_mm2=0.0,
            policy="test",
        )


def test_hbm_stacks_are_capped_by_the_die_edge(technology) -> None:
    pitch = technology.hbm("hbm3e", "stack_beachfront_mm").value
    utilisation = technology.hbm("hbm3e", "max_beachfront_utilization").value
    for area in (815.0, 1600.0, 46225.0):
        expected = int(4.0 * math.sqrt(area) * utilisation // pitch)
        assert (
            max_hbm_stacks_per_device(
                technology, generation="hbm3e", die_area_mm2=area
            )
            == expected
        )
    # Perimeter grows as the square root of area, so a wafer has far less die
    # edge per mm2 than an equal area of separate reticle dies.  That is a real
    # argument against wafer-scale for an HBM-bandwidth-bound workload.
    wafer = max_hbm_stacks_per_device(
        technology, generation="hbm3e", die_area_mm2=46225.0
    )
    dies = max_hbm_stacks_per_device(
        technology, generation="hbm3e", die_area_mm2=815.0
    ) * round(46225.0 / 815.0)
    assert wafer < dies


def test_too_many_stacks_for_the_edge_is_reported(technology, llama) -> None:
    resident = kv_traffic(llama, 2048).storage_bytes_per_user
    budget = rom_device_budget(
        technology,
        name="over-beachfront",
        node="N6",
        area_mm2_per_device=815.0,
        topology=_single_chip(),
        stored_weight_bytes=4.0e9,
        resident_kv_bytes=resident,
        kv_store="hbm",
        hbm_stacks=64,
        hbm_generation="hbm2e",
    )
    assert any(reason.startswith("BEACHFRONT") for reason in budget.reasons)


# --------------------------------------------------------------------------
# the roofline combination
# --------------------------------------------------------------------------


def test_separate_arrays_overlap_and_shared_memory_adds(technology, llama) -> None:
    rom = _rom_chip(technology, llama)
    rom_step = evaluate(
        rom,
        llama,
        context_tokens=2048,
        batch_size=1,
        technology=technology,
        weight_bits_per_parameter=4.0,
        execution_format="w4a8",
    )
    components = rom_step.component_times_s
    assert rom_step.metrics["memory_time_s"] == pytest.approx(
        max(components["weight_read"], components["kv_read"])
    )

    gpu = gpu_device_budget(technology, part="a100_sxm_80gb", topology=_single_chip())
    gpu_step = evaluate(
        gpu, llama, context_tokens=2048, batch_size=1, technology=technology
    )
    gpu_components = gpu_step.component_times_s
    assert gpu_step.metrics["memory_time_s"] == pytest.approx(
        gpu_components["weight_read"] + gpu_components["kv_read"]
    )


def test_compute_overlaps_memory(technology, llama) -> None:
    step = evaluate(
        _rom_chip(technology, llama),
        llama,
        context_tokens=2048,
        batch_size=1,
        technology=technology,
        weight_bits_per_parameter=4.0,
        execution_format="w4a8",
    )
    assert step.metrics["service_time_s"] == pytest.approx(
        max(step.metrics["memory_time_s"], step.component_times_s["compute"])
    )


def test_link_latency_is_added_never_overlapped(technology, qwen) -> None:
    stored = qwen.checkpoint_bytes
    resident = kv_traffic(qwen, 8192).storage_bytes_per_user
    topology = Topology(
        kind="array", device_count=8, parallelism="pipeline", link="nvlink"
    )
    budget = rom_device_budget(
        technology,
        name="array8",
        node="N6",
        area_mm2_per_device=815.0,
        topology=topology,
        stored_weight_bytes=stored,
        resident_kv_bytes=resident,
        kv_store="sram",
    )
    step = evaluate(
        budget,
        qwen,
        context_tokens=8192,
        batch_size=1,
        technology=technology,
        execution_format="fp8",
    )
    raw = step.metrics["raw_step_time_before_thermal_s"]
    assert raw == pytest.approx(
        step.metrics["service_time_s"] + step.component_times_s["link_latency"]
    )
    assert step.component_times_s["link_latency"] > 0


def test_batch_one_pipeline_gets_no_parallelism_only_hops(technology, qwen) -> None:
    """Adding pipeline stages at batch 1 can only add latency, never remove it."""

    stored = qwen.checkpoint_bytes
    resident = kv_traffic(qwen, 8192).storage_bytes_per_user
    latencies = []
    for devices in (4, 8, 16):
        topology = Topology(
            kind="array",
            device_count=devices,
            parallelism="pipeline",
            link="nvlink",
        )
        budget = rom_device_budget(
            technology,
            name=f"array{devices}",
            node="N6",
            area_mm2_per_device=815.0,
            topology=topology,
            stored_weight_bytes=stored,
            resident_kv_bytes=resident,
            kv_store="sram",
        )
        step = evaluate(
            budget,
            qwen,
            context_tokens=8192,
            batch_size=1,
            technology=technology,
            execution_format="fp8",
        )
        latencies.append(step.component_times_s["link_latency"])
    assert latencies == sorted(latencies)
    assert latencies[0] < latencies[-1]


def test_hop_counts_match_the_topology_semantics() -> None:
    layers = 36
    assert Topology(
        kind="single_chip", device_count=1, parallelism="none", link="none"
    ).hop_events(layers)[0] == 0.0
    assert Topology(
        kind="array", device_count=10, parallelism="pipeline", link="nvlink"
    ).hop_events(layers)[0] == 9.0
    assert Topology(
        kind="array", device_count=10, parallelism="tensor", link="nvlink"
    ).hop_events(layers)[0] == 72.0
    assert Topology(
        kind="wafer",
        device_count=1,
        parallelism="pipeline",
        link="on_wafer",
        on_wafer_regions=57,
    ).hop_events(layers)[0] == 56.0


def test_tensor_parallel_is_about_fifteen_times_worse_than_pipeline(
    technology, qwen
) -> None:
    """The doc's central latency claim, computed rather than asserted."""

    pipeline = latency_crossover(
        Topology(kind="array", device_count=4, parallelism="pipeline", link="nvlink"),
        qwen,
        technology,
    )
    tensor = latency_crossover(
        Topology(kind="array", device_count=4, parallelism="tensor", link="nvlink"),
        qwen,
        technology,
    )
    ratio = tensor.link_latency_s_per_token / pipeline.link_latency_s_per_token
    assert ratio > 15.0
    assert tensor.hard_ceiling_tokens_s < 17_000, (
        "NVLink tensor parallelism should be unable to reach Taalas-class rates"
    )
    on_wafer = latency_crossover(
        Topology(
            kind="wafer",
            device_count=1,
            parallelism="tensor",
            link="on_wafer",
            on_wafer_regions=57,
        ),
        qwen,
        technology,
    )
    assert on_wafer.hard_ceiling_tokens_s > 17_000, (
        "on-wafer tensor parallelism should reach Taalas-class rates"
    )


def test_aggregate_is_batch_times_per_user(technology, qwen) -> None:
    budget = _rom_chip(
        technology, qwen, area_mm2=46225.0, context=8192, batch=1, bits=8.0
    )
    for batch in (1, 8, 32):
        step = evaluate(
            budget,
            qwen,
            context_tokens=8192,
            batch_size=batch,
            technology=technology,
            weight_bits_per_parameter=8.0,
            execution_format="fp8",
        )
        if not step.feasible:
            continue
        assert step.aggregate_tokens_s == pytest.approx(
            batch * step.per_user_tokens_s
        )
        assert step.per_user_tokens_s == pytest.approx(1.0 / step.step_time_s)


def test_binding_constraint_is_the_largest_component(technology, qwen) -> None:
    budget = _rom_chip(
        technology, qwen, area_mm2=46225.0, context=8192, batch=1, bits=8.0
    )
    step = evaluate(
        budget,
        qwen,
        context_tokens=8192,
        batch_size=1,
        technology=technology,
        weight_bits_per_parameter=8.0,
        execution_format="fp8",
    )
    assert step.feasible
    largest = max(step.component_times_s, key=lambda key: step.component_times_s[key])
    assert step.binding_constraint == largest


# --------------------------------------------------------------------------
# the ROM locality rule and MoE engagement
# --------------------------------------------------------------------------


def test_rom_weight_time_is_the_full_array_sweep_at_every_batch(
    technology, flash
) -> None:
    """The ROM sweep floor is independent of batch and of expert coverage."""

    stored = flash.checkpoint_bytes
    resident = kv_traffic(flash, 200_000).storage_bytes_per_user * 64
    topology = Topology(
        kind="wafer",
        device_count=1,
        parallelism="pipeline",
        link="on_wafer",
        on_wafer_regions=57,
    )
    budget = rom_device_budget(
        technology,
        name="flash-wafer",
        node="N6",
        area_mm2_per_device=46225.0,
        topology=topology,
        stored_weight_bytes=stored,
        resident_kv_bytes=resident,
        kv_store="sram",
    )
    sweep = stored / budget.weight_read_bytes_s
    times = []
    for batch in (1, 8, 32, 64):
        step = evaluate(
            budget,
            flash,
            context_tokens=200_000,
            batch_size=batch,
            technology=technology,
        )
        times.append(step.component_times_s["weight_read"])
    assert all(value == pytest.approx(sweep) for value in times)


def test_rom_sweep_time_does_not_depend_on_model_size(technology, qwen, flash) -> None:
    expected = (
        technology.rom_bits_per_mm2("N6").value
        / 8.0
        / (
            technology.rom_read_bytes_s_per_mm2("N6").value
            * technology.efficiency("rom_read_bandwidth").value
        )
    )
    for model, context, bits in ((qwen, 8192, 8.0), (flash, 200_000, None)):
        budget = _rom_chip(
            technology,
            model,
            area_mm2=46225.0,
            context=context,
            batch=1,
            bits=bits,
        )
        step = evaluate(
            budget,
            model,
            context_tokens=context,
            batch_size=1,
            technology=technology,
            weight_bits_per_parameter=bits,
        )
        assert step.component_times_s["weight_read"] == pytest.approx(expected)


def test_moe_engagement_follows_the_coverage_formula(technology, flash) -> None:
    stored = flash.checkpoint_bytes
    topology = Topology(
        kind="wafer",
        device_count=1,
        parallelism="pipeline",
        link="on_wafer",
        on_wafer_regions=57,
    )
    budget = rom_device_budget(
        technology,
        name="flash-hbm",
        node="N6",
        area_mm2_per_device=46225.0,
        topology=topology,
        stored_weight_bytes=stored,
        resident_kv_bytes=0.0,
        kv_store="hbm",
        hbm_stacks=40,
        hbm_generation="hbm3e",
    )
    fractions = []
    for batch in (1, 8, 32, 64, 256):
        step = evaluate(
            budget,
            flash,
            context_tokens=200_000,
            batch_size=batch,
            technology=technology,
        )
        expected = expected_expert_coverage(
            flash.num_experts, flash.experts_per_token, batch
        )
        assert step.metrics["expert_coverage"] == pytest.approx(expected)
        fractions.append(step.metrics["engaged_weight_fraction"])
        # Locality: the effective bandwidth is the engaged fraction of the peak.
        assert step.metrics["effective_weight_read_bytes_s"] == pytest.approx(
            step.metrics["peak_weight_read_bytes_s"]
            * step.metrics["engaged_weight_fraction"]
        )
    assert fractions == sorted(fractions)
    assert fractions[0] < 0.1 < fractions[-1]


def test_moe_sparsity_raises_aggregate_but_not_per_user_rate(
    technology, flash
) -> None:
    """The central ROM/HBM asymmetry, checked rather than asserted in prose."""

    stored = flash.checkpoint_bytes
    topology = Topology(
        kind="wafer",
        device_count=1,
        parallelism="pipeline",
        link="on_wafer",
        on_wafer_regions=57,
    )
    budget = rom_device_budget(
        technology,
        name="flash-hbm",
        node="N6",
        area_mm2_per_device=46225.0,
        topology=topology,
        stored_weight_bytes=stored,
        resident_kv_bytes=0.0,
        kv_store="hbm",
        hbm_stacks=40,
        hbm_generation="hbm3e",
    )
    steps = {
        batch: evaluate(
            budget,
            flash,
            context_tokens=200_000,
            batch_size=batch,
            technology=technology,
        )
        for batch in (1, 8)
    }
    assert steps[1].component_times_s["weight_read"] == pytest.approx(
        steps[8].component_times_s["weight_read"]
    )
    assert steps[8].aggregate_tokens_s > steps[1].aggregate_tokens_s


def test_hbm_weight_time_does_shrink_with_sparsity(technology, flash) -> None:
    """On a global-bandwidth memory, sparsity reduces the bytes and the time."""

    gpu_one = gpu_device_budget(
        technology,
        part="b200_sxm",
        topology=Topology(
            kind="array", device_count=8, parallelism="pipeline", link="nvlink"
        ),
    )
    small = evaluate(
        gpu_one, flash, context_tokens=200_000, batch_size=1, technology=technology
    )
    large = evaluate(
        gpu_one, flash, context_tokens=200_000, batch_size=64, technology=technology
    )
    assert (
        large.component_times_s["weight_read"]
        > small.component_times_s["weight_read"]
    )


# --------------------------------------------------------------------------
# the batch-amortisation fork
# --------------------------------------------------------------------------


def _flash_wafer(technology, flash, amortization: str):
    return rom_device_budget(
        technology,
        name=f"flash-{amortization}",
        node="N6",
        area_mm2_per_device=46225.0,
        topology=Topology(
            kind="wafer",
            device_count=1,
            parallelism="pipeline",
            link="on_wafer",
            on_wafer_regions=57,
        ),
        stored_weight_bytes=flash.checkpoint_bytes,
        resident_kv_bytes=0.0,
        kv_store="hbm",
        hbm_stacks=40,
        hbm_generation="hbm3e",
        weight_amortization=amortization,
    )


def test_the_two_amortization_policies_are_identical_at_batch_one(
    technology, flash
) -> None:
    """Which is exactly why the published anchor cannot settle the fork."""

    steps = [
        evaluate(
            _flash_wafer(technology, flash, policy),
            flash,
            context_tokens=200_000,
            batch_size=1,
            technology=technology,
        )
        for policy in ("batched", "per_stream")
    ]
    assert steps[0].step_time_s == pytest.approx(steps[1].step_time_s)
    assert steps[0].aggregate_tokens_s == pytest.approx(steps[1].aggregate_tokens_s)


def test_compute_in_rom_pays_one_array_sweep_per_concurrent_stream(
    technology, flash
) -> None:
    batched = _flash_wafer(technology, flash, "batched")
    per_stream = _flash_wafer(technology, flash, "per_stream")
    single = evaluate(
        per_stream,
        flash,
        context_tokens=200_000,
        batch_size=1,
        technology=technology,
    ).component_times_s["weight_read"]
    for batch in (8, 32, 64):
        step = evaluate(
            per_stream,
            flash,
            context_tokens=200_000,
            batch_size=batch,
            technology=technology,
        )
        assert step.component_times_s["weight_read"] == pytest.approx(batch * single)
        assert step.metrics["rom_sweeps_per_step"] == batch
        reference = evaluate(
            batched,
            flash,
            context_tokens=200_000,
            batch_size=batch,
            technology=technology,
        )
        assert reference.metrics["rom_sweeps_per_step"] == 1
        assert step.aggregate_tokens_s <= reference.aggregate_tokens_s * (1 + 1e-9)


def test_compute_in_rom_aggregate_never_exceeds_its_batch_one_rate(
    technology, flash
) -> None:
    """The doc's claim: aggregate per die collapses onto per-user throughput."""

    budget = _flash_wafer(technology, flash, "per_stream")
    base = evaluate(
        budget, flash, context_tokens=200_000, batch_size=1, technology=technology
    )
    for batch in (8, 32, 64, 256):
        step = evaluate(
            budget,
            flash,
            context_tokens=200_000,
            batch_size=batch,
            technology=technology,
        )
        if not step.feasible:
            continue
        assert step.aggregate_tokens_s <= base.aggregate_tokens_s * 1.2


def test_an_unknown_amortization_policy_is_rejected(technology, flash) -> None:
    with pytest.raises(ValidationError):
        _flash_wafer(technology, flash, "wishful")


# --------------------------------------------------------------------------
# representation, capacity and validation
# --------------------------------------------------------------------------


def test_representation_scales_stored_and_engaged_bytes_together(
    technology, qwen
) -> None:
    budget = _rom_chip(
        technology, qwen, area_mm2=46225.0, context=8192, batch=1, bits=8.0
    )
    native = evaluate(
        budget, qwen, context_tokens=8192, batch_size=1, technology=technology
    )
    fp8 = evaluate(
        budget,
        qwen,
        context_tokens=8192,
        batch_size=1,
        technology=technology,
        weight_bits_per_parameter=8.0,
        execution_format="fp8",
    )
    assert fp8.metrics["stored_weight_bytes"] == pytest.approx(
        qwen.total_parameters * 1.0
    )
    assert fp8.metrics["representation_scale_vs_checkpoint"] == pytest.approx(
        fp8.metrics["stored_weight_bytes"] / qwen.checkpoint_bytes
    )
    assert fp8.metrics["engaged_weight_bytes"] < native.metrics["engaged_weight_bytes"]


def test_full_checkpoint_policy_streams_the_whole_checkpoint(technology, llama) -> None:
    gpu = gpu_device_budget(technology, part="a100_sxm_80gb", topology=_single_chip())
    step = evaluate(
        gpu,
        llama,
        context_tokens=2048,
        batch_size=1,
        technology=technology.ideal(),
        weight_bits_per_parameter=8.0,
        weight_traffic_policy="full_checkpoint",
    )
    assert step.metrics["engaged_weight_bytes"] == pytest.approx(
        llama.total_parameters
    )
    streamed = evaluate(
        gpu,
        llama,
        context_tokens=2048,
        batch_size=1,
        technology=technology.ideal(),
        weight_bits_per_parameter=8.0,
    )
    # The embedding table is gathered, not streamed, so decode-streamed traffic
    # is strictly smaller than the whole checkpoint.
    assert streamed.metrics["engaged_weight_bytes"] < step.metrics[
        "engaged_weight_bytes"
    ]


def test_capacity_shortfall_produces_a_reason_and_zero_throughput(
    technology, qwen
) -> None:
    budget = _rom_chip(
        technology, qwen, area_mm2=815.0, context=8192, batch=1, bits=8.0
    )
    step = evaluate(
        budget,
        qwen,
        context_tokens=8192,
        batch_size=1024,
        technology=technology,
        weight_bits_per_parameter=8.0,
        execution_format="fp8",
    )
    assert not step.feasible
    assert any(reason.startswith("CAPACITY") for reason in step.reasons)
    assert step.per_user_tokens_s == 0.0
    assert step.aggregate_tokens_s == 0.0
    assert step.binding_constraint == "capacity_or_format"


def test_a_format_the_device_cannot_execute_fails_closed(technology, flash) -> None:
    """A100 has no FP8 unit; the emulation must be visible, not silent."""

    gpu = gpu_device_budget(technology, part="a100_sxm_80gb", topology=_single_chip())
    assert gpu.emulated_formats["fp8"] == "bf16"
    step = evaluate(
        gpu, flash, context_tokens=200_000, batch_size=1, technology=technology
    )
    # It executes, but at the BF16 roof rather than an invented FP8 one.
    assert "w4a8" in step.metrics["operations_by_canonical_format"]
    assert step.metrics["compute_roofs_ops_s"]["bf16"] == pytest.approx(3.12e14)


def test_invalid_requests_are_rejected(technology, qwen) -> None:
    budget = _rom_chip(
        technology, qwen, area_mm2=46225.0, context=8192, batch=1, bits=8.0
    )
    with pytest.raises(ValidationError):
        evaluate(
            budget,
            qwen,
            context_tokens=8192,
            batch_size=0,
            technology=technology,
        )
    with pytest.raises(ValidationError):
        evaluate(
            budget,
            qwen,
            context_tokens=10_000_000,
            batch_size=1,
            technology=technology,
        )
    with pytest.raises(ValidationError):
        evaluate(
            budget,
            qwen,
            context_tokens=8192,
            batch_size=1,
            technology=technology,
            weight_traffic_policy="wishful",
        )
    with pytest.raises(ValidationError):
        Topology(kind="array", device_count=0, parallelism="pipeline", link="nvlink")
    with pytest.raises(ValidationError):
        Topology(kind="array", device_count=2, parallelism="magic", link="nvlink")
    with pytest.raises(ValidationError):
        Topology(kind="single_chip", device_count=4, parallelism="none", link="none")


def test_gpu_published_totals_match_stacks_times_per_stack(technology) -> None:
    for part in ("a100_sxm_80gb", "b200_sxm"):
        budget = gpu_device_budget(technology, part=part, topology=_single_chip())
        assert (
            budget.provenance[
                "hbm_capacity_stack_cross_check_relative_error"
            ].value
            == pytest.approx(0.0, abs=1e-9)
        )
        assert (
            budget.provenance[
                "hbm_bandwidth_stack_cross_check_relative_error"
            ].value
            == pytest.approx(0.0, abs=1e-9)
        )


def test_gpu_area_is_stated_and_scales_with_device_count(technology) -> None:
    one = gpu_device_budget(technology, part="a100_sxm_80gb", topology=_single_chip())
    assert one.silicon_area_mm2_total == pytest.approx(826.0)
    many = gpu_device_budget(
        technology,
        part="a100_sxm_80gb",
        topology=Topology(
            kind="array", device_count=56, parallelism="pipeline", link="nvlink"
        ),
    )
    assert many.silicon_area_mm2_total == pytest.approx(826.0 * 56)
    # A 46,225 mm2 wafer is about 56 A100 dies -- the iso-area rule.
    assert round(46225.0 / 826.0) == 56
    b200 = gpu_device_budget(technology, part="b200_sxm", topology=_single_chip())
    assert b200.silicon_area_mm2_total == pytest.approx(1600.0)


def test_b200_w4a8_roof_sits_between_its_own_published_endpoints(technology) -> None:
    budget = gpu_device_budget(technology, part="b200_sxm", topology=_single_chip())
    assert (
        budget.compute_ops_s["fp8"]
        < budget.compute_ops_s["w4a8"]
        < budget.compute_ops_s["fp4"]
    )


# --------------------------------------------------------------------------
# the study runner
# --------------------------------------------------------------------------


def _load_runner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_roofline_studies", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generated(tmp_path_factory: pytest.TempPathFactory):
    runner = _load_runner()
    first = tmp_path_factory.mktemp("roofline-first")
    second = tmp_path_factory.mktemp("roofline-second")
    results = runner.run_all(first)
    runner.run_all(second)
    return runner, results, first, second


def test_runner_is_byte_deterministic(generated) -> None:
    runner, _, first, second = generated
    for study_id in runner.STUDIES:
        for artifact in ARTIFACTS:
            assert (first / study_id / artifact).read_bytes() == (
                second / study_id / artifact
            ).read_bytes()


def test_runner_refuses_to_overwrite_without_force(generated, tmp_path) -> None:
    runner, _, _, _ = generated
    runner.run_all(tmp_path)
    with pytest.raises(SystemExit) as excinfo:
        runner.run_all(tmp_path)
    assert "--force" in str(excinfo.value)
    runner.run_all(tmp_path, force=True)


def test_checked_in_artifacts_match_the_runner(generated) -> None:
    runner, _, first, _ = generated
    for study_id in runner.STUDIES:
        for artifact in ARTIFACTS:
            checked_in = CHECKED_IN / study_id / artifact
            assert checked_in.exists(), f"missing checked-in {checked_in}"
            assert checked_in.read_bytes() == (first / study_id / artifact).read_bytes()


def test_every_study_audit_passes(generated) -> None:
    _, results, _, _ = generated
    for study_id, result in results.items():
        audit = result["consistency_audit"]
        assert audit["status"] == "pass", (study_id, audit["errors"][:5])
        assert audit["checks_evaluated"] > 1000


def test_studies_carry_the_validation_gates(generated) -> None:
    _, results, _, _ = generated
    for result in results.values():
        gates = result["validation_gates"]
        assert gates["taalas_hc1"]["passed"]
        assert gates["a100_weight_bound"]["passed"]


def test_every_point_states_the_silicon_area_on_both_sides(generated) -> None:
    _, results, _, _ = generated
    for result in results.values():
        for row in result["points"]:
            assert row["silicon_area_mm2"] > 0
        for row in result["comparisons"]:
            assert row["rom_silicon_area_mm2"] > 0
            assert row["iso_area_gpu_silicon_area_mm2"] > 0
            assert 0.5 < row["iso_area_ratio"] < 2.0


def test_studies_cover_the_required_models_contexts_and_batches(generated) -> None:
    runner, results, _, _ = generated
    required = {
        ("Qwen3-8B", 8_192),
        ("DeepSeek-V4-Flash-0731", 200_000),
        ("DeepSeek-V4-Pro-0813", 1_000_000),
    }
    for result in results.values():
        seen = {
            (row["model"], row["context_tokens"]) for row in result["points"]
        }
        assert required <= seen
        for model, context in required:
            batches = {
                row["batch_size"]
                for row in result["points"]
                if row["model"] == model
            }
            assert set(runner.BATCHES) <= batches


def test_studies_report_both_topologies_and_the_crossover(generated) -> None:
    _, results, _, _ = generated
    for result in results.values():
        kinds = {row["topology_kind"] for row in result["points"] if row["family"] == "rom"}
        assert {"array", "wafer"} <= kinds
        assert result["latency_crossovers"]
        for row in result["latency_crossovers"]:
            assert row["viable_tokens_s"] > 0
            assert row["hard_ceiling_tokens_s"] >= row["viable_tokens_s"]
        for row in result["topology_choices"]:
            assert row["array_or_wafer"] in {"array", "wafer", "no feasible ROM design"}


def test_studies_report_both_amortization_policies(generated) -> None:
    _, results, _, _ = generated
    for result in results.values():
        policies = {
            row["weight_amortization"]
            for row in result["points"]
            if row["family"] == "rom"
        }
        assert policies == {"batched", "per_stream"}
        assert result["amortization_fork"]
        for row in result["amortization_fork"]:
            if row["batch_size"] != 1:
                continue
            if row["batched_aggregate_tokens_s"] is None:
                continue
            assert row["aggregate_penalty_x"] == pytest.approx(1.0, rel=1e-6)
        penalties = [
            row["aggregate_penalty_x"]
            for row in result["amortization_fork"]
            if row["aggregate_penalty_x"] is not None
        ]
        assert penalties and min(penalties) >= 1.0 - 1e-9
        assert max(penalties) > 2.0, (
            "the fork should visibly matter somewhere in the study"
        )


def test_every_point_names_a_binding_constraint(generated) -> None:
    _, results, _, _ = generated
    allowed = {
        "weight_read",
        "kv_read",
        "compute",
        "link_latency",
        "thermal",
        "capacity_or_format",
    }
    for result in results.values():
        for row in result["points"]:
            assert row["binding_constraint"] in allowed
            if not row["feasible"]:
                assert row["reasons"]


def test_json_csv_and_report_are_mutually_consistent(generated) -> None:
    runner, results, first, _ = generated
    import csv as csv_module

    for study_id, result in results.items():
        payload = json.loads((first / study_id / "analytical.json").read_text())
        assert payload["study_id"] == study_id
        rows = list(
            csv_module.DictReader(
                (first / study_id / "sweep.csv").read_text().splitlines()
            )
        )
        assert len(rows) == len(payload["points"])
        report = (first / study_id / "REPORT.md").read_text()
        assert "Validation gates" in report
        assert "PASS" in report
        gate = payload["validation_gates"]["taalas_hc1"]
        assert f"{gate['modelled_value']:,.1f}" in report


def test_report_lists_every_assumed_input(generated) -> None:
    runner, results, first, _ = generated
    for study_id, result in results.items():
        report = (first / study_id / "REPORT.md").read_text()
        for path in result["graded_inputs"]["assumed"]:
            assert f"`{path}`" in report
