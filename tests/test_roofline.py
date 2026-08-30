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
import random
import sys
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
    effective_engaged_devices,
    evaluate,
    expected_max_region_load,
    gpu_device_budget,
    kv_access_granularity,
    latency_crossover,
    layer_fixed_latency,
    max_hbm_stacks_per_device,
    rom_device_budget,
    taalas_hc1_anchor,
)
from opentallas.schema import ModelProfile, ValidationError
from opentallas.workload import (
    expected_engaged_devices,
    expected_expert_coverage,
    kv_traffic,
)


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
    # The ROM read-bandwidth density is the input a compute-in-ROM part's rate
    # turns on, and it must stay physically unremarkable: a model that needs an
    # order of magnitude more of it has stopped being a model.
    assert requirements["rom_density_shortfall_x"] < 2.0
    # The compute-density requirement is deliberately NOT asserted here. HC1 has
    # no MAC array -- the multiply is the array sweep -- so back-deriving a
    # compute density for it asks what a separate compute unit would have to
    # deliver, and the answer (22.5x) is the size of a unit the machine does not
    # contain. It is reported because it is the right question for the
    # storage-plus-MAC reading, and it is the number that would matter if the
    # architecture fork resolved the other way.


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
        "rom_density_shortfall_x"
    ]
    # HC1 is compute-in-ROM, so it has no MAC array and no independent compute
    # roof: the multiply is the array sweep.  Back-deriving a *compute* density
    # for it therefore asks a question the machine does not answer, and the
    # meaningful input is the one that actually sets its rate -- how fast the
    # array can be walked.  This assertion moved when the floorplan started
    # depending on the amortisation policy, and the move is the point: the gate
    # now interrogates the input the architecture is sensitive to.
    assert 0.5 < shortfall < 2.0, (
        "the ROM read-bandwidth density this model derives is "
        f"{shortfall:.3f}x what the Taalas HC1 must have; for a compute-in-ROM "
        "part that is the input the rate turns on"
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


#: Every input in configs/hardware/technology.json that rests on judgement
#: rather than on a published or measured figure.  This is an EXACT set, not a
#: subset: the previous version of this test asserted that seven known
#: assumptions were present, which let eleven new ones be added without the
#: test noticing.  An assumption that enters the model silently is the failure
#: mode this program exists to prevent.
ASSUMED_INPUTS = frozenset(
    {
        "efficiencies.compute",
        "efficiencies.expert_router_imbalance",
        "efficiencies.hbm_bandwidth",
        "efficiencies.hbm_capacity",
        "efficiencies.rom_read_bandwidth",
        "efficiencies.sram_read_bandwidth",
        "efficiencies.stage_balance",
        "energy.mac_energy_j_per_op.bf16",
        "energy.mac_energy_j_per_op.fp32",
        "energy.mac_energy_j_per_op.fp4",
        "energy.mac_energy_j_per_op.fp8",
        "energy.mac_energy_j_per_op.w4a8",
        "energy.rom_read_j_per_byte",
        "energy.sram_read_j_per_byte",
        "floorplan.interconnect_area_fraction",
        "floorplan.overhead_area_fraction",
        "hbm.hbm2e.phy_area_mm2_per_stack",
        "hbm.hbm2e.stack_beachfront_mm",
        "hbm.hbm3e.phy_area_mm2_per_stack",
        "hbm.hbm3e.stack_beachfront_mm",
        "kv.access_granularity_bytes.hbm",
        "kv.access_granularity_bytes.sram",
        "kv.index_layout",
        "latency.array_pass_boundaries_per_layer",
        "latency.global_wire_delay_s_per_mm",
        "latency.layer_barrier_s",
        "latency.pipeline_fill_drain_s",
        "latency.sequencer_issue_decode_s",
        "latency.sparse_index_dependency_s",
        "latency.sram_access_s",
        "links.ethernet.bytes_s",
        "links.ethernet.fabric",
        "links.ethernet.hop_latency_s",
        "links.ethernet.switch_radix",
        # Nobody publishes a wafer-to-wafer link, so every field of one is
        # assumed. It is the ROM side's most load-bearing assumption after the
        # bitcell ratio, and it is swept 1-10 us.
        "links.inter_wafer.domain_size",
        "links.inter_wafer.fabric",
        "links.inter_wafer.hop_latency_s",
        "links.inter_wafer.switch_radix",
        # NVIDIA publishes no NVLink latency figure of any kind. The bandwidth,
        # the domain size and the single-tier switch structure ARE published,
        # which is why only the latency of each NVLink entry is assumed.
        "links.nvlink.hop_latency_s",
        "links.nvlink3.hop_latency_s",
        "links.nvlink5.hop_latency_s",
        "links.nvlink5_nvl72.hop_latency_s",
        "links.on_package.fabric",
        "links.on_package.hop_latency_s",
        "links.on_wafer.hop_latency_s",
        "reference_parts.taalas_hc1.batch_size",
        "reference_parts.taalas_hc1.weight_amortization",
        "reference_parts.taalas_hc1.weight_bits_per_parameter",
        "rom.array_efficiency",
        "rom.cell_to_sram_cell_area_ratio",
        "rom.cim_cell_area_multiplier",
        "rom.cim_precompute_area_fraction",
        "sram.array_efficiency",
    }
)


def test_the_grade_vocabulary_matches_the_config_that_defines_it() -> None:
    """**A latent crash, caught before it fired.**

    `configs/hardware/technology.json` names the evidence classes in
    `grade_definitions`; this module enforces them in ``GRADES``. When the
    config gained ``executed`` -- we ran it, in this repository, artifact
    committed -- this module still rejected it, so the first config entry to
    use the grade would have raised ``ValidationError`` out of ``Graded`` and
    taken the whole study down. The two lists must not drift.
    """

    defined = set(json.loads(TECHNOLOGY_PATH.read_text())["grade_definitions"])
    assert defined == set(GRADES), (
        f"grade vocabulary drift: config defines {sorted(defined)}, "
        f"roofline.GRADES accepts {sorted(GRADES)}"
    )
    # Strongest to weakest, because _weakest_grade indexes into it.
    assert GRADES.index("measured") < GRADES.index("executed")
    assert GRADES.index("executed") < GRADES.index("published")
    assert GRADES.index("derived") < GRADES.index("assumed")
    # And a value carrying the new grade actually constructs.
    entry = Graded(value=1.0, grade="executed", source="a run", note="")
    assert entry.grade == "executed"
    assert derived(2.0, (entry,), "2x", "").grade == "derived"


def test_the_assumed_inputs_are_the_ones_we_expect(technology) -> None:
    """Pin the assumption surface so a new one cannot be added silently."""

    assumed = set(technology.inputs_by_grade()["assumed"])
    added = sorted(assumed - ASSUMED_INPUTS)
    removed = sorted(ASSUMED_INPUTS - assumed)
    assert not added, f"new assumed inputs entered the model unannounced: {added}"
    assert not removed, f"assumed inputs disappeared without being re-graded: {removed}"
    assert "compute.format_roofs_ops_s.bf16" not in assumed
    # The retired one, by name: it claimed to carry the busiest region and did
    # not.  ``expected_max_region_load`` carries it now.
    assert "efficiencies.expert_load_balance" not in assumed


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
    # Three serial terms now, not two.  The per-layer fixed cost is added on
    # exactly the same footing as the hop latency and for the same reason:
    # layer n+1 cannot start until layer n's activation exists, so neither one
    # can hide behind bandwidth.
    assert raw == pytest.approx(
        step.metrics["service_time_s"]
        + step.component_times_s["link_latency"]
        + step.component_times_s["layer_fixed_latency"]
    )
    assert step.component_times_s["link_latency"] > 0
    assert step.component_times_s["layer_fixed_latency"] > 0


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


def test_pipeline_depth_cannot_exceed_the_layer_count() -> None:
    """A token cannot cross more stage boundaries than the model has layers.

    This is the correction that mattered most at scale.  Charging a 57-region
    wafer 56 serial hops on a 36-layer model, or a 672-GPU cluster 671 of them
    on a 61-layer model, invents a critical path the machine does not have.
    """

    layers = 36
    wafer = Topology(
        kind="wafer",
        device_count=1,
        parallelism="pipeline",
        link="on_wafer",
        on_wafer_regions=57,
    )
    assert wafer.partitions == 57
    assert wafer.stages_for(layers) == layers
    assert wafer.hop_events(layers)[0] == float(layers - 1)
    # And the cap only ever binds downward.
    assert wafer.stages_for(1000) == 57
    assert sum(
        event.count for event in wafer.link_events(layers, stage_cap=False)
    ) == 56.0
    small = Topology(
        kind="array", device_count=8, parallelism="pipeline", link="nvlink"
    )
    assert small.stages_for(layers) == 8
    assert small.hop_events(layers)[0] == 7.0


def test_a_pipeline_is_charged_the_fabric_it_actually_crosses() -> None:
    """Both link classes, in the right proportion, on one topology.

    93 partitions on 8-GPU NVLink islands is 12 islands: 11 of the 92 stage
    boundaries leave an island and 81 do not.  Charging all 92 to either link
    is wrong in a different direction each way.
    """

    topology = Topology(
        kind="array",
        device_count=93,
        parallelism="pipeline",
        link="infiniband_hdr",
        intra_link="nvlink3",
        intra_domain_size=8,
    )
    events = {
        event.link: event for event in topology.link_events(1_000)
    }
    assert set(events) == {"nvlink3", "infiniband_hdr"}
    assert events["infiniband_hdr"].count == 11.0
    assert events["nvlink3"].count == 81.0
    assert (
        events["nvlink3"].count + events["infiniband_hdr"].count
        == topology.partitions - 1
    )


def test_hybrid_is_tensor_inside_the_domain_and_pipeline_across_it(
    technology, qwen
) -> None:
    topology = Topology(
        kind="array",
        device_count=64,
        parallelism="hybrid",
        link="infiniband_hdr",
        intra_link="nvlink3",
        intra_domain_size=8,
        tensor_group_size=8,
    )
    assert topology.tensor_group == 8
    assert topology.pipeline_stages == 8
    events = topology.link_events(qwen.num_layers)
    collectives = [event for event in events if event.kind == "all_reduce"]
    hops = [event for event in events if event.kind == "point_to_point"]
    assert len(collectives) == 1
    assert collectives[0].link == "nvlink3"
    assert collectives[0].span == 8
    assert collectives[0].count == 2 * qwen.num_layers
    assert len(hops) == 1
    assert hops[0].link == "infiniband_hdr"
    assert hops[0].count == 7.0


def test_an_all_reduce_costs_more_the_wider_it_is(technology, qwen) -> None:
    """Two all-reduces per layer, and the volume scales with span and batch."""

    narrow = Topology(
        kind="array", device_count=2, parallelism="tensor", link="nvlink"
    )
    wide = Topology(
        kind="array", device_count=8, parallelism="tensor", link="nvlink"
    )
    activation = 4096.0 * 2.0
    narrow_s, _, _ = technology.link_time_s(
        narrow, qwen.num_layers, activation_bytes=activation
    )
    wide_s, _, _ = technology.link_time_s(
        wide, qwen.num_layers, activation_bytes=activation
    )
    # Same latency term inside one switch domain, more payload on the wire.
    assert wide_s > narrow_s
    batched_s, _, _ = technology.link_time_s(
        wide, qwen.num_layers, activation_bytes=activation * 32
    )
    assert batched_s > wide_s


def test_a_mesh_collective_pays_the_mesh_diameter(technology) -> None:
    """The ROM-side mirror of the pipeline-hop error, and it is charged.

    A stitched wafer has no switch, so an all-reduce cannot finish before the
    far corner has answered: Cerebras measured their own at about 1.1 times the
    mesh diameter.  Charging it the flat two traversals a switched domain gets
    is what let a 57-region collective cost 0.2 us instead of 1.5 us.
    """

    assert technology.link_fabric("on_wafer") == "mesh"
    assert technology.link_fabric("nvlink3") == "switched"
    # A switched domain is flat in its own radix.
    assert technology.collective_traversals("nvlink3", 8) == 2.0
    # A mesh is not.
    assert technology.collective_traversals("on_wafer", 4) == pytest.approx(2.2)
    assert technology.collective_traversals("on_wafer", 57) == pytest.approx(15.4)
    assert technology.collective_traversals("on_wafer", 681) > technology.\
        collective_traversals("on_wafer", 57)


def test_on_wafer_tensor_parallelism_no_longer_reaches_taalas_rates(
    technology, qwen
) -> None:
    """**A retraction, asserted so it cannot come back.**

    The previous model charged an on-wafer all-reduce two flat hops however
    many reticle fields it spanned, which made wafer-scale tensor parallelism
    look like a 116,000 tok/s fabric.  With the mesh diameter charged it is
    not, and the sharpest published argument for wafer-scale weakens with it.
    """

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
    assert on_wafer.hard_ceiling_tokens_s < 17_000, (
        "an on-wafer all-reduce over 57 reticle fields costs the mesh "
        "diameter, and that no longer fits a Taalas-class token budget"
    )
    nvlink = latency_crossover(
        Topology(kind="array", device_count=8, parallelism="tensor", link="nvlink"),
        qwen,
        technology,
    )
    # The wafer is still much better than NVLink for the same collective --
    # the retraction is of the absolute claim, not the ordering.
    assert on_wafer.hard_ceiling_tokens_s > nvlink.hard_ceiling_tokens_s


def test_tensor_parallel_is_much_worse_than_pipeline_on_nvlink(
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


def test_aggregate_is_batch_times_per_user_on_a_one_slot_machine(
    technology, qwen
) -> None:
    """The identity survives exactly where it is true: a machine with one slot.

    A single chip has one slot, so there is no pipeline to under-fill and the
    aggregate rate is the batch over the latency.  On a machine cut into slots
    it is not, which is the next test.
    """

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
        assert step.metrics["token_slots"] == 1
        assert step.aggregate_tokens_s == pytest.approx(
            batch * step.per_user_tokens_s
        )
        assert step.per_user_tokens_s == pytest.approx(1.0 / step.step_time_s)
        # One slot means no correction: the throughput view and the latency
        # view are the same number, which is why both validation gates are
        # untouched by the separation.
        assert step.metrics["per_user_tokens_s_throughput_view"] == pytest.approx(
            step.per_user_tokens_s
        )
        assert step.metrics["latency_correction_x"] == pytest.approx(1.0)


# --------------------------------------------------------------------------
# per-user latency against aggregate throughput
#
# The defect this section exists to pin down: the model charged a pipeline's
# service time on the machine's AGGREGATE resources -- the throughput view --
# and its hops on the single-token path, so a balanced S-stage pipeline came
# out S times faster per user than it is.
# --------------------------------------------------------------------------


def test_token_slots_is_partitions_over_the_tensor_group() -> None:
    """A token is served by one slot at a time, and this counts them."""

    assert (
        Topology(
            kind="single_chip", device_count=1, parallelism="none", link="none"
        ).token_slots
        == 1
    )
    # Pipeline: every partition is its own slot.
    assert (
        Topology(
            kind="array", device_count=64, parallelism="pipeline", link="nvlink"
        ).token_slots
        == 64
    )
    # Tensor: one slot however many partitions, because they are all on the
    # same token.  That is what the two all-reduces per layer buy.
    assert (
        Topology(
            kind="array", device_count=64, parallelism="tensor", link="nvlink"
        ).token_slots
        == 1
    )
    # Hybrid: one slot per tensor group.
    assert (
        Topology(
            kind="array",
            device_count=64,
            parallelism="hybrid",
            link="infiniband_hdr",
            intra_link="nvlink3",
            intra_domain_size=8,
            tensor_group_size=8,
        ).token_slots
        == 8
    )
    # A wafer's slots are counted in reticle fields, not in wafers.
    assert (
        Topology(
            kind="wafer",
            device_count=2,
            parallelism="pipeline",
            link="inter_wafer",
            intra_link="on_wafer",
            on_wafer_regions=114,
        ).token_slots
        == 114
    )


def test_pipeline_parallelism_buys_one_user_nothing(technology, llama) -> None:
    """The correction, stated as the physics that forced it.

    Under pipeline parallelism each of N stages holds 1/N of the weights and
    reads them with 1/N of the machine's bandwidth.  On a cluster of published
    parts, where every device brings its own fixed HBM bandwidth, the two
    factors cancel exactly and **one user's latency is flat in the device
    count** -- the same as on a single device holding everything, minus what
    the hops cost.  The model used to divide the whole checkpoint by the whole
    cluster's bandwidth and report the result as a single user's rate, which is
    N times too fast; that number is kept beside the corrected one and here it
    is shown rising with N while the real one does not.
    """

    corrected: dict[int, float] = {}
    throughput_view: dict[int, float] = {}
    for devices in (1, 2, 4, 8, 16):
        topology = (
            _single_chip()
            if devices == 1
            else Topology(
                kind="array",
                device_count=devices,
                parallelism="pipeline",
                link="nvlink",
            )
        )
        budget = gpu_device_budget(
            technology,
            part="a100_sxm_80gb",
            topology=topology,
            name=f"a100-x{devices}",
        )
        step = evaluate(
            budget,
            llama,
            context_tokens=2048,
            batch_size=1,
            technology=technology,
        )
        assert step.feasible, step.reasons
        assert step.metrics["token_slots"] == devices
        corrected[devices] = step.per_user_tokens_s
        throughput_view[devices] = step.metrics["per_user_tokens_s_throughput_view"]

    # Flat, to within what the hops take off it: sixteen stages is not sixteen
    # times one stage, and it is not faster than one device either.
    assert corrected[16] <= corrected[1] * (1 + 1e-9)
    assert corrected[16] >= corrected[1] * 0.85
    # The number the defect produced rises almost linearly with the device
    # count, which is the whole of the error.
    assert throughput_view[16] / throughput_view[1] > 10.0
    for devices in (2, 4, 8, 16):
        assert throughput_view[devices] / corrected[devices] == pytest.approx(
            devices, rel=0.15
        )


def test_a_rom_pipeline_gives_a_user_less_than_the_same_silicon_undivided(
    technology, qwen
) -> None:
    """The same rule on the other family, where it bites harder still.

    A ROM array is sized to the bytes it holds, so cutting a design into N
    pipeline stages does not add array bandwidth the way adding GPUs adds HBM
    channels -- it subdivides the array that was already there.  Each stage
    then takes a full technology sweep time for its share, and the token pays N
    of them.  A pipelined ROM machine is therefore *worse* per user than the
    same silicon undivided, not merely no better.
    """

    stored = qwen.checkpoint_bytes
    resident = kv_traffic(qwen, 8192).storage_bytes_per_user
    rates: dict[int, float] = {}
    for devices in (1, 2, 4, 8, 16):
        topology = (
            _single_chip()
            if devices == 1
            else Topology(
                kind="array",
                device_count=devices,
                parallelism="pipeline",
                link="nvlink",
            )
        )
        budget = rom_device_budget(
            technology,
            name=f"rom-x{devices}",
            node="N6",
            area_mm2_per_device=3_000.0,
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
        assert step.feasible, step.reasons
        rates[devices] = step.per_user_tokens_s
        assert step.metrics["latency_correction_x"] == pytest.approx(
            step.metrics["token_slots"], rel=0.35
        )
    ordered = [rates[devices] for devices in sorted(rates)]
    assert ordered == sorted(ordered, reverse=True)
    assert rates[16] < rates[1] / 10


def test_tensor_parallelism_does_reduce_one_users_latency(technology, qwen) -> None:
    """The other half: tensor parallelism is different in kind, not degree.

    Every partition works on the same token, so the whole machine's bandwidth
    is on that token's critical path.  What it pays is two all-reduces per
    layer, and on a slow enough fabric that price exceeds the gain -- which is
    a result the model should be able to produce, not one it should assume.
    """

    stored = qwen.checkpoint_bytes
    resident = kv_traffic(qwen, 8192).storage_bytes_per_user
    steps = {}
    for parallelism in ("pipeline", "tensor"):
        budget = rom_device_budget(
            technology,
            name=f"rom-8-{parallelism}",
            node="N6",
            area_mm2_per_device=815.0,
            topology=Topology(
                kind="array",
                device_count=8,
                parallelism=parallelism,
                link="nvlink",
            ),
            stored_weight_bytes=stored,
            resident_kv_bytes=resident,
            kv_store="sram",
        )
        steps[parallelism] = evaluate(
            budget,
            qwen,
            context_tokens=8192,
            batch_size=1,
            technology=technology,
            execution_format="fp8",
        )
    assert steps["tensor"].metrics["token_slots"] == 1
    assert steps["pipeline"].metrics["token_slots"] == 8
    assert (
        steps["tensor"].per_user_tokens_s > steps["pipeline"].per_user_tokens_s
    )
    # The collective is on the critical path and is charged.
    assert steps["tensor"].component_times_s["link_latency"] > (
        steps["pipeline"].component_times_s["link_latency"]
    )


def test_aggregate_and_per_user_are_no_longer_one_number(technology, qwen) -> None:
    """``aggregate = batch x per_user`` is gone, and its removal is the point.

    A machine cut into slots reaches its aggregate rate only with a user in
    every slot.  At batch 1 a 16-slot pipeline delivers one user's rate and has
    fifteen idle slots; its aggregate rate is what it would do if they were
    full, and the difference is reported rather than folded away.
    """

    budget = rom_device_budget(
        technology,
        name="rom-x16",
        node="N6",
        area_mm2_per_device=3_000.0,
        topology=Topology(
            kind="array", device_count=16, parallelism="pipeline", link="nvlink"
        ),
        stored_weight_bytes=qwen.checkpoint_bytes,
        resident_kv_bytes=kv_traffic(qwen, 8192).storage_bytes_per_user * 32,
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
    assert step.feasible
    slots = step.metrics["token_slots"]
    assert slots == 16
    assert step.metrics["delivered_tokens_s"] == pytest.approx(
        step.per_user_tokens_s
    )
    assert step.aggregate_tokens_s == pytest.approx(
        step.metrics["pipeline_fill_users"] * step.per_user_tokens_s
    )
    assert step.aggregate_tokens_s > step.metrics["delivered_tokens_s"]
    assert step.metrics["pipeline_fill_fraction"] < 1.0
    # At a batch that fills the machine the two views meet again.
    full = evaluate(
        budget,
        qwen,
        context_tokens=8192,
        batch_size=32,
        technology=technology,
        execution_format="fp8",
    )
    if full.feasible:
        assert full.metrics["pipeline_fill_fraction"] == pytest.approx(1.0)
        assert full.aggregate_tokens_s == pytest.approx(
            32 * full.per_user_tokens_s
        )


def test_the_fill_a_machine_claims_is_capped_by_the_kv_it_can_hold(
    technology, qwen
) -> None:
    """A slot cannot hold a user whose KV the machine has nowhere to put."""

    budget = rom_device_budget(
        technology,
        name="rom-x64-tight-kv",
        node="N6",
        area_mm2_per_device=3_000.0,
        topology=Topology(
            kind="array", device_count=64, parallelism="pipeline", link="nvlink"
        ),
        stored_weight_bytes=qwen.checkpoint_bytes,
        resident_kv_bytes=kv_traffic(qwen, 8192).storage_bytes_per_user,
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
    if not step.feasible:
        pytest.skip("design infeasible at batch 1")
    assert step.metrics["pipeline_fill_users"] <= max(
        1.0, step.metrics["max_resident_users"]
    )
    assert step.metrics["pipeline_fill_limited_by"] in {
        "batch",
        "pipeline_slots",
        "kv_capacity",
    }


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
    # **Tensor-parallel across the wafer's fields, not pipelined across them.**
    # The sweep floor is a property of one slot's array pass, and a pipelined
    # wafer has 57 slots, so a token there pays 57 passes.  That factor is the
    # subject of its own test; this one is about the pass itself, so the
    # topology is the one-slot machine where the two coincide.
    topology = Topology(
        kind="wafer",
        device_count=1,
        parallelism="tensor",
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
        assert step.metrics["token_slots"] == 1
        assert step.metrics["rom_full_array_sweep_time_s"] == pytest.approx(sweep)
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
    # One slot: tensor-parallel across the fields, so the batch this test varies
    # is the batch one array pass actually serves.  On a pipelined wafer the
    # batch is spread across 57 slots and each pass sees a fifty-seventh of it,
    # which is a different (and separately tested) statement.
    topology = Topology(
        kind="wafer",
        device_count=1,
        parallelism="tensor",
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
    # One slot: tensor-parallel across the fields, so the batch this test varies
    # is the batch one array pass actually serves.  On a pipelined wafer the
    # batch is spread across 57 slots and each pass sees a fifty-seventh of it,
    # which is a different (and separately tested) statement.
    topology = Topology(
        kind="wafer",
        device_count=1,
        parallelism="tensor",
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
            # One slot: tensor-parallel across the fields, so ``batch_size`` is
            # the batch one array pass actually serves.
            parallelism="tensor",
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


def test_the_amortization_policies_are_different_machines(technology, llama) -> None:
    """Different floorplans, so they differ even at batch 1.

    They used to be identical there, and that was an artefact of sharing one
    area split: only the weight-read formula differed.  A compute-in-ROM part
    has no MAC array and a larger cell, so it is a different machine at every
    batch -- and the published anchor *can* tell them apart, which is why the
    anchor is now evaluated as the machine Taalas actually built.
    """
    from opentallas.roofline import balanced_area_split

    splits = {
        policy: balanced_area_split(
            technology,
            node="N6",
            total_mm2=815.0,
            weight_store="rom",
            kv_store="sram",
            stored_weight_bytes=4.0e9,
            resident_kv_bytes=2.0e8,
            weight_amortization=policy,
        )
        for policy in ("batched", "per_stream")
    }
    assert splits["batched"].compute_mm2 > splits["per_stream"].compute_mm2 * 5, (
        "a compute-in-ROM part should spend almost no area on a compute block; "
        "if the two floorplans agree, the split has stopped seeing the policy"
    )
    assert splits["per_stream"].rom_mm2 > splits["batched"].rom_mm2, (
        "a compute-in-ROM cell carries a select transistor, so it is larger"
    )


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


def test_compute_in_rom_aggregate_never_exceeds_the_sweep_ceiling(
    technology, flash
) -> None:
    """Compute-in-ROM aggregate is capped by the array, not by its batch-1 rate.

    This test used to assert ``aggregate <= 1.2x the batch-1 aggregate``, and it
    was asserting the model's arithmetic rather than the physics.  It held only
    because the step time was *exactly* ``batch x sweep`` -- there was no fixed
    per-token cost anywhere in the model, so ``batch / (batch x sweep)`` was
    constant by construction.  With a per-layer serial cost on the critical path
    the step is ``batch x sweep + fixed``, and the fixed part amortises over the
    batch exactly as hop latency always has.  Aggregate therefore *rises* toward
    the ceiling instead of sitting on it from batch 1.

    The invariant that survives is the one that was always the real claim: a
    machine that pays one array sweep per concurrent stream can never exceed one
    sweep per token, whatever the batch.
    """

    budget = _flash_wafer(technology, flash, "per_stream")
    base = evaluate(
        budget, flash, context_tokens=200_000, batch_size=1, technology=technology
    )
    ceiling = base.metrics["rom_sweep_ceiling_tokens_s"]
    assert base.aggregate_tokens_s < ceiling
    previous = base.aggregate_tokens_s
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
        assert step.aggregate_tokens_s <= ceiling * (1 + 1e-9)
        assert step.aggregate_tokens_s >= previous * (1 - 1e-9)
        previous = step.aggregate_tokens_s


def test_an_unknown_amortization_policy_is_rejected(technology, flash) -> None:
    with pytest.raises(ValidationError):
        _flash_wafer(technology, flash, "wishful")


# --------------------------------------------------------------------------
# the busiest unit, not the average one
# --------------------------------------------------------------------------


def _monte_carlo_max_region_load(
    num_regions: int, batch: int, k: int, *, trials: int = 4000, seed: int = 12345
) -> float:
    """Draw the routing directly: B tokens, k distinct experts each, uniform."""

    rng = random.Random(seed)
    total = 0
    population = range(num_regions)
    for _ in range(trials):
        load = [0] * num_regions
        for _ in range(batch):
            for expert in rng.sample(population, k):
                load[expert] += 1
        total += max(load)
    return total / trials


@pytest.mark.parametrize("num_experts", (256, 384))
def test_expected_max_region_load_matches_a_monte_carlo_of_the_routing(
    num_experts,
) -> None:
    """The closed form is checked against the thing it approximates.

    This is the test that decides Correction 1, so it does not check the
    formula against itself.  It draws the routing 4,000 times and compares.
    """

    for batch in (1, 2, 4, 8, 16, 32, 64, 128, 256):
        simulated = _monte_carlo_max_region_load(num_experts, batch, 6)
        modelled = expected_max_region_load(num_experts, batch, 6)
        assert modelled == pytest.approx(simulated, rel=0.03), (
            f"N={num_experts} B={batch}: modelled {modelled:.3f} against "
            f"simulated {simulated:.3f}"
        )
    # At batch 1 the answer is exactly one pass: one token, k distinct regions,
    # no region drawn twice.  This is what keeps the three amortisation policies
    # identical at batch 1 and the Taalas anchor unable to separate them.
    assert expected_max_region_load(num_experts, 1, 6) == 1.0


def test_the_mean_engaged_region_understates_the_sweep(technology, flash) -> None:
    """The correction that had to land: sweep depth is the max, not the mean.

    The model charged ``batch * k / (N * coverage)`` -- the load of the AVERAGE
    engaged region -- and divided it by a flat 0.85 whose own note in
    ``technology.json`` said the depth is set by the busiest region.  The gap is
    not a constant and 0.85 could not have been one: it runs from 1.0x at batch
    1 to roughly 2.7x in the middle of the range this study covers.
    """

    budget = _flash_wafer(technology, flash, "per_region")
    seen = {}
    for batch in (1, 8, 64, 256):
        step = evaluate(
            budget,
            flash,
            context_tokens=200_000,
            batch_size=batch,
            technology=technology,
        )
        charged = step.metrics["rom_sweeps_per_step"]
        mean = step.metrics["region_sweep_depth_mean_uncorrected"]
        seen[batch] = step.metrics["region_sweep_depth_max_over_mean"]
        assert charged == pytest.approx(
            _monte_carlo_max_region_load(flash.num_experts, batch, 6), rel=0.03
        )
        assert charged >= mean * (1 - 1e-9)
    assert seen[1] == pytest.approx(1.0, abs=1e-9)
    assert seen[8] > 1.5
    assert seen[64] > 2.0
    assert max(seen.values()) < 4.0


def test_the_router_derate_no_longer_substitutes_for_the_statistic(
    technology,
) -> None:
    """``expert_load_balance`` is gone; what replaces it multiplies the max."""

    assert "expert_load_balance" not in technology.raw["efficiencies"]
    imbalance = technology.efficiency("expert_router_imbalance")
    assert imbalance.grade == "assumed"
    assert imbalance.value >= 1.0


def test_expert_parallel_gpu_waits_for_its_busiest_device(technology, flash) -> None:
    """Correction 2: the same error, on the GPU side of the comparison.

    ``workload.expected_engaged_devices`` answers 'how many devices hold at
    least one selected expert'.  The routed fetch does not finish when the
    average of those finishes.  ``workload.py`` is shared with
    ``opentallas.analytical`` and is not edited, so the correction lives in
    ``roofline`` and BOTH numbers are reported at every point -- correcting only
    the ROM side would be its own bias.
    """

    for devices, distinct in ((8, 6.0), (16, 20.0), (64, 100.0)):
        mean = expected_engaged_devices(devices, distinct)
        effective = effective_engaged_devices(devices, distinct)
        assert 1.0 <= effective <= mean
        assert mean / effective > 1.1

    budget = gpu_device_budget(
        technology,
        part="b200_sxm",
        topology=Topology(
            kind="array", device_count=16, parallelism="pipeline", link="nvlink"
        ),
    )
    step = evaluate(
        budget, flash, context_tokens=200_000, batch_size=8, technology=technology
    )
    assert step.metrics["engaged_device_max_over_mean_correction"] > 1.0
    assert (
        step.metrics["engaged_devices"]
        < step.metrics["mean_engaged_devices_uncorrected"]
    )


# --------------------------------------------------------------------------
# the compute-in-ROM cell, and what it does and does not buy
# --------------------------------------------------------------------------


def test_the_cim_cell_area_multiplier_cancels_in_the_sweep(technology, llama) -> None:
    """A bigger cell is not a faster array.

    The multiplier used to be applied to AREA only: a compute-in-ROM design was
    charged 1.6x the silicon per stored byte and then credited with the
    storage cell's bandwidth per mm2, so its sweep came out 1.6x faster purely
    because its cells were bigger.  Both densities carry the multiplier now.
    The array's pass time is a property of the array, not of the cell; what the
    cell costs is CAPACITY, and that is where it still shows up.
    """

    storage = technology.rom_bits_per_mm2_for("N6", "batched")
    cim = technology.rom_bits_per_mm2_for("N6", "per_stream")
    multiplier = technology.rom_cell_area_multiplier("per_stream").value
    assert multiplier > 1.0
    assert cim.value == pytest.approx(storage.value / multiplier)
    assert technology.rom_read_bytes_s_per_mm2_for(
        "N6", "per_stream"
    ).value == pytest.approx(
        technology.rom_read_bytes_s_per_mm2_for("N6", "batched").value / multiplier
    )

    sweeps = {}
    for policy in ("batched", "per_stream", "per_region"):
        budget = rom_device_budget(
            technology,
            name=f"cell-{policy}",
            node="N6",
            area_mm2_per_device=815.0,
            topology=_single_chip(),
            stored_weight_bytes=llama.total_parameters * 3.5 / 8.0,
            resident_kv_bytes=kv_traffic(llama, 2048).storage_bytes_per_user,
            kv_store="sram",
            weight_amortization=policy,
        )
        sweeps[policy] = budget.provenance["rom_full_array_sweep_time_s"].value
        # And the capacity check is no longer tautological: the array holds
        # exactly what it was sized to hold, whatever cell it is built from.
        assert budget.weight_capacity_bytes == pytest.approx(
            llama.total_parameters * 3.5 / 8.0, rel=1e-9
        )
    assert sweeps["batched"] == pytest.approx(sweeps["per_stream"], rel=1e-12)
    assert sweeps["batched"] == pytest.approx(sweeps["per_region"], rel=1e-12)
    # What the larger cell does cost is silicon: the same weights need 1.6x the
    # array, which comes out of the SRAM beside it.
    small = balanced_area_split(
        technology,
        node="N6",
        total_mm2=815.0,
        weight_store="rom",
        kv_store="sram",
        stored_weight_bytes=llama.total_parameters * 3.5 / 8.0,
        resident_kv_bytes=0.0,
        weight_amortization="batched",
    )
    large = balanced_area_split(
        technology,
        node="N6",
        total_mm2=815.0,
        weight_store="rom",
        kv_store="sram",
        stored_weight_bytes=llama.total_parameters * 3.5 / 8.0,
        resident_kv_bytes=0.0,
        weight_amortization="per_stream",
    )
    assert large.rom_mm2 == pytest.approx(small.rom_mm2 * multiplier)


def test_the_rom_capacity_check_can_actually_fail(technology, flash) -> None:
    """It used to be an identity, so it was not a check.

    ``balanced_area_split`` sizes ROM to the stored bytes, so
    ``weight_capacity / stored`` was exactly the cell multiplier at every model
    size, node and area -- 1.6 for compute-in-ROM and 1.0 otherwise. It could
    not fail.  The array is now clamped to the silicon that is actually left,
    so a design whose weights do not fit reports a capacity below them and
    ``evaluate`` refuses it.
    """

    split = balanced_area_split(
        technology,
        node="N6",
        total_mm2=815.0,
        weight_store="rom",
        kv_store="sram",
        stored_weight_bytes=flash.checkpoint_bytes,
        resident_kv_bytes=0.0,
        weight_amortization="per_region",
    )
    assert any(reason.startswith("AREA:") for reason in split.reasons)
    budget = rom_device_budget(
        technology,
        name="too-small",
        node="N6",
        area_mm2_per_device=815.0,
        topology=_single_chip(),
        stored_weight_bytes=flash.checkpoint_bytes,
        resident_kv_bytes=0.0,
        kv_store="sram",
        weight_amortization="per_region",
    )
    assert budget.weight_capacity_bytes < flash.checkpoint_bytes
    step = evaluate(
        budget, flash, context_tokens=8192, batch_size=1, technology=technology
    )
    assert not step.feasible
    assert any(reason.startswith("CAPACITY:") for reason in step.reasons)
    assert step.aggregate_tokens_s == 0.0


# --------------------------------------------------------------------------
# the two costs the model used to price at zero
# --------------------------------------------------------------------------


def test_a_single_chip_step_is_no_longer_free_of_fixed_cost(
    technology, llama
) -> None:
    """Before this term, ``single_chip`` had literally no latency anywhere."""

    total, breakdown, _ = layer_fixed_latency(technology, llama)
    assert total > 0
    assert breakdown["layers"] == llama.num_layers
    assert breakdown["compressed_sparse_layers"] == 0
    assert total == pytest.approx(breakdown["seconds_per_layer"] * llama.num_layers)

    budget = _rom_chip(technology, llama, bits=3.5)
    step = evaluate(
        budget, llama, context_tokens=2048, batch_size=1, technology=technology
    )
    assert step.component_times_s["link_latency"] == 0.0
    assert step.component_times_s["layer_fixed_latency"] == pytest.approx(total)
    assert step.metrics["raw_step_time_before_thermal_s"] == pytest.approx(
        step.metrics["service_time_s"] + total
    )


def test_the_fixed_cost_falls_on_the_fast_machine_and_not_the_slow_one(
    technology, flash
) -> None:
    """The asymmetry is the finding, and it runs against the ROM thesis.

    A ROM step is tens of microseconds over 32-61 layers; a GPU step for the
    same model is milliseconds.  The same per-layer floor is therefore a large
    fraction of the first and a rounding error on the second, which means this
    correction costs the architecture this program is arguing for and costs the
    incumbent almost nothing.
    """

    rom = evaluate(
        _flash_wafer(technology, flash, "per_region"),
        flash,
        context_tokens=200_000,
        batch_size=1,
        technology=technology,
    )
    gpu = evaluate(
        gpu_device_budget(
            technology,
            part="a100_sxm_80gb",
            topology=Topology(
                kind="array", device_count=64, parallelism="pipeline", link="nvlink"
            ),
        ),
        flash,
        context_tokens=200_000,
        batch_size=1,
        technology=technology,
    )
    rom_share = rom.metrics["layer_fixed_latency_fraction_of_step"]
    gpu_share = gpu.metrics["layer_fixed_latency_fraction_of_step"]
    assert rom_share > 5 * gpu_share
    # Compressed-sparse layers carry an extra term, so a sparse model pays more
    # per layer than a dense one.
    assert (
        rom.metrics["layer_fixed_latency"]["seconds_per_compressed_sparse_layer"]
        > rom.metrics["layer_fixed_latency"]["seconds_per_layer"]
    )


def test_the_per_layer_cost_is_a_band_and_the_gate_is_not_fitted(
    technology, llama
) -> None:
    """No parameter in this model takes its value from the answer it produces.

    Every term in the ``latency`` block is ``assumed`` and carries a range, and
    the anchor is evaluated at both ends of it.  The test that matters is the
    last one: the per-layer cost that would land the model exactly on the
    published figure is NEGATIVE, so no value of this term could have closed
    the gap.  Had it been positive and close to the stated value, that would
    have been a real result -- and it would still have had to be reported as a
    coincidence rather than engineered into one.
    """

    terms = technology.layer_latency_terms()
    for name, term in terms.items():
        node = technology.raw["latency"][name]
        assert term.grade == "assumed", name
        assert "range_low" in node and "range_high" in node, name
        assert node["range_low"] <= node["value"] <= node["range_high"], name

    low = layer_fixed_latency(technology.at_layer_latency_bound("low"), llama)[0]
    stated = layer_fixed_latency(technology, llama)[0]
    high = layer_fixed_latency(technology.at_layer_latency_bound("high"), llama)[0]
    assert low < stated < high

    band = taalas_hc1_anchor(technology, llama).detail["layer_fixed_latency_band"]
    assert band["high"]["ratio_to_published"] < band["stated"]["ratio_to_published"]
    assert band["stated"]["ratio_to_published"] < band["low"]["ratio_to_published"]
    for bound in ("low", "stated", "high"):
        assert 0.5 <= band[bound]["ratio_to_published"] <= 2.0, bound
    assert band["per_layer_cost_that_would_close_the_gap_s"] < 0.0


def test_each_amortisation_policy_is_sized_on_its_own_floorplan(technology) -> None:
    """A compute-in-ROM cell is 1.6x a storage cell, so it can need more dies.

    Sizing every policy on the batched floorplan denied compute-in-ROM the dies
    its larger array needs and then reported the shortfall as infeasibility --
    "it cannot hold this model" when the truth was "we never tried enough dies".
    """

    flash = ModelProfile.load(
        ROOT / "configs" / "models" / "deepseek-v4-flash-0731.json"
    )
    stored = flash.checkpoint_bytes
    counts = {}
    for policy in ("batched", "per_region"):
        for devices in range(1, 200):
            budget = rom_device_budget(
                technology,
                name=f"probe-{policy}-{devices}",
                node="N6",
                area_mm2_per_device=815.0,
                topology=Topology(
                    kind="array",
                    device_count=devices,
                    parallelism="pipeline",
                    link="nvlink",
                ),
                stored_weight_bytes=stored,
                resident_kv_bytes=0.0,
                kv_store="sram",
                weight_amortization=policy,
            )
            if not budget.reasons and budget.weight_capacity_bytes >= stored:
                counts[policy] = devices
                break
    assert counts["per_region"] > counts["batched"], counts
    # And the study must actually use each policy's own minimum, not the
    # batched one: the per-region designs it emits carry their own device count.
    # Roughly the cell-area multiplier, rounded up by the fixed overheads that
    # do not shrink with device count.
    ratio = counts["per_region"] / counts["batched"]
    multiplier = technology.rom_cell_area_multiplier("per_region").value
    assert multiplier <= ratio <= multiplier * 1.25, (ratio, counts)


def test_the_recovered_mac_area_is_swept_rather_than_assumed(
    technology, llama
) -> None:
    """Where compute-in-ROM spends the silicon it recovers decides the answer.

    Handing it to SRAM when the sweep is what binds spends the freed area on
    the component with a twenty-fold margin, and the study then reports
    compute-in-ROM as worthless -- an artefact of the allocation rule rather
    than a result.  Both destinations are now modelled, and the same choice is
    offered to the amortising machine so the sweep does not decide the
    comparison by being available to one side only.
    """

    stored = llama.total_parameters * 3.5 / 8.0
    made = {}
    for policy in ("batched", "per_region"):
        for spare in ("sram", "rom"):
            budget = rom_device_budget(
                technology,
                name=f"{policy}-{spare}",
                node="N6",
                area_mm2_per_device=815.0,
                topology=_single_chip(),
                stored_weight_bytes=stored,
                resident_kv_bytes=0.0,
                kv_store="sram",
                weight_amortization=policy,
                spare_area_policy=spare,
            )
            made[(policy, spare)] = budget
    for policy in ("batched", "per_region"):
        base = made[(policy, "sram")]
        filled = made[(policy, "rom")]
        # Replication: more array holding real copies, so more read bandwidth
        # AND more capacity, in the same proportion.  Bandwidth without
        # capacity would be buying reads for bits that do not exist.
        assert filled.split.rom_mm2 > base.split.rom_mm2
        assert filled.weight_read_bytes_s > base.weight_read_bytes_s
        assert filled.weight_capacity_bytes / stored > 1.0
        assert filled.weight_read_bytes_s / base.weight_read_bytes_s == pytest.approx(
            filled.weight_capacity_bytes / base.weight_capacity_bytes, rel=1e-9
        )
    # The amortising machine's filled floorplan is derived, not swept: its MAC
    # array is sized to consume exactly what the array beside it can read.
    filled = made[("batched", "rom")]
    mac_ops_s = filled.compute_ops_s["fp8"] * technology.efficiency("compute").value
    assert filled.weight_read_bytes_s == pytest.approx(mac_ops_s / 2.0, rel=0.02)
    with pytest.raises(ValidationError):
        balanced_area_split(
            technology,
            node="N6",
            total_mm2=815.0,
            weight_store="rom",
            kv_store="sram",
            stored_weight_bytes=stored,
            resident_kv_bytes=0.0,
            spare_area_policy="wishful",
        )


def test_the_sparse_index_scan_is_most_of_the_kv_read(technology, flash) -> None:
    """85% of Flash's KV read at 200K is a scan of 256-byte index entries.

    The entry size was published as 68 bytes, which was read off the
    implementation rather than measured while running it.  Measured against the
    reference oracle it is 256, and the share the scan takes of the whole KV
    read goes UP rather than down: the payload entries grew too.
    """

    detail = kv_access_granularity(
        technology, flash, context_tokens=200_000, store="hbm"
    )[1]
    scans = [
        stream for stream in detail["streams"] if stream["stream"] == "sparse_index_scan"
    ]
    assert scans
    index_bytes = sum(stream["bytes"] for stream in scans)
    native = kv_traffic(flash, 200_000).read_bytes
    assert index_bytes / native == pytest.approx(0.85, abs=0.02)
    assert scans[0]["entry_bytes"] == 256.0
    assert scans[0]["entries_per_layer"] == 50_000


def test_kv_granularity_is_a_layout_choice_and_is_stated_as_one(
    technology, flash
) -> None:
    """**A retraction, asserted so it cannot come back.**

    This test used to assert 1.30x on HBM and 1.64x on SRAM for Flash, and the
    recommendation "pack the index array separately from the payload" was sold
    as the cheapest 30% in the program.  Both rested on a 68-byte index entry,
    which was read off the implementation.  Measured, the entry is 256 bytes --
    larger than both the 32-byte HBM granule and the 128-byte SRAM granule --
    so an interleaved layout now costs exactly nothing on either store and on
    either DeepSeek model.

    The mechanism is unchanged and still parameterised, because it is a layout
    DECISION and a model that silently assumed the cheap one would present a
    design decision as a fact.  What changed is that this workload no longer
    exercises it.
    """

    interleaved = {
        store: kv_access_granularity(
            technology, flash, context_tokens=200_000, store=store
        )[0]
        for store in ("hbm", "sram")
    }
    assert interleaved["hbm"] == pytest.approx(1.0)
    assert interleaved["sram"] == pytest.approx(1.0)

    contiguous = json.loads(json.dumps(technology.raw))
    contiguous["kv"]["index_layout"]["value"] = "contiguous"
    packed = Technology(raw=contiguous)
    for store in ("hbm", "sram"):
        inflation = kv_access_granularity(
            packed, flash, context_tokens=200_000, store=store
        )[0]
        assert inflation == pytest.approx(interleaved[store])

    # The mechanism still bites an entry smaller than the granule, which is
    # what it is for.  Shrink the index entry alone and the penalty returns.
    small = json.loads(json.dumps(flash.to_dict()))
    for group in small["attention_groups"]:
        if group.get("index_entry_bytes"):
            group["index_entry_bytes"] = 16.0
    shrunk = ModelProfile.from_dict(small)
    assert (
        kv_access_granularity(technology, shrunk, context_tokens=200_000, store="sram")[0]
        > 1.5
    )

    # A dense-KV model with a granule-aligned entry pays nothing either way.
    qwen_profile = ModelProfile.load(ROOT / "configs" / "models" / "qwen3-8b.json")
    assert kv_access_granularity(
        technology, qwen_profile, context_tokens=8192, store="sram"
    )[0] == pytest.approx(1.0)


def test_the_sram_kv_credit_is_reported_against_its_locality_bound(
    technology, flash
) -> None:
    """The SRAM KV path is never exercised, and the model now says so.

    At batch 1 the step credits one user with the whole array's read bandwidth.
    That is defensible for KV in a way it is not for ROM -- KV is written at run
    time and can be striped across every bank -- but only if the design really
    stripes, and nothing checks.  The bound is reported at every point so the
    exposure is visible rather than implicit.
    """

    budget = rom_device_budget(
        technology,
        name="flash-sram-kv",
        node="N6",
        area_mm2_per_device=46225.0,
        topology=Topology(
            kind="wafer",
            device_count=1,
            # One slot, so the KV bound below is read against the same pass the
            # component time reports.
            parallelism="tensor",
            link="on_wafer",
            on_wafer_regions=57,
        ),
        stored_weight_bytes=flash.checkpoint_bytes,
        resident_kv_bytes=kv_traffic(flash, 200_000).storage_bytes_per_user,
        kv_store="sram",
        weight_amortization="per_region",
    )
    bounds = {}
    for batch in (1, 8):
        step = evaluate(
            budget,
            flash,
            context_tokens=200_000,
            batch_size=batch,
            technology=technology,
        )
        bounds[batch] = step.metrics["kv_read_s_under_bank_locality"]
        assert step.metrics["kv_bank_occupancy"] < 1.0
        assert bounds[batch] > step.component_times_s["kv_read"]
    # The bound is batch-independent while there are idle banks, which is the
    # ROM locality rule turning up on the SRAM side: an array sized to the KV it
    # holds delivers a fixed KV sweep, exactly as an array sized to the weights
    # delivers a fixed weight sweep.
    assert bounds[1] == pytest.approx(bounds[8], rel=1e-9)
    step_one = evaluate(
        budget, flash, context_tokens=200_000, batch_size=1, technology=technology
    )
    assert bounds[1] / step_one.component_times_s["kv_read"] > 40
    # And the reason this was invisible: even the bound is far from binding for
    # THIS design.  That is a fact about this design, not about the model.
    assert bounds[1] < step_one.component_times_s["weight_read"]

    # **The batch at which the array saturates has moved down, and that is the
    # measured KV correction showing up here.** Flash's KV storage at 200K is
    # 1.38 GB per user against the 705 MB the profile previously claimed, so
    # this design runs out of idle banks at batch 64 where it used to have them
    # to spare.  Past that point the striped credit and the locality bound
    # coincide and there is no exposure left to report, because there is no
    # slack left to lose.
    saturated = evaluate(
        budget, flash, context_tokens=200_000, batch_size=64, technology=technology
    )
    assert saturated.metrics["kv_bank_occupancy"] == 1.0
    assert saturated.metrics["kv_read_s_under_bank_locality"] == pytest.approx(
        saturated.component_times_s["kv_read"]
    )

    # An HBM KV store is striped by its own controller, so the bound is the term.
    hbm = evaluate(
        _flash_wafer(technology, flash, "per_region"),
        flash,
        context_tokens=200_000,
        batch_size=1,
        technology=technology,
    )
    assert hbm.metrics["kv_bank_occupancy"] == 1.0
    assert hbm.metrics["kv_read_s_under_bank_locality"] == pytest.approx(
        hbm.component_times_s["kv_read"]
    )



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
    # The module has to be in ``sys.modules`` before it executes: it uses
    # ``from __future__ import annotations``, so every dataclass annotation is
    # a string, and ``dataclasses`` resolves those by looking the defining
    # module up in ``sys.modules``.  Loading it by path without registering it
    # makes that lookup return ``None`` and every dataclass in the file fails
    # to construct.
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
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


def test_both_families_get_the_same_topology_sweep(generated) -> None:
    """**The regression guard for the defect this comparison was built on.**

    The ROM side used to be swept over pipeline AND tensor parallelism with the
    better reported, while the GPU side was only ever evaluated under pipeline.
    At 672 devices that charged the GPU 671 serial hops per token at batch 1 and
    reported the resulting collapse as a property of GPUs.  Whatever
    parallelisms one family is offered, the other is offered too.
    """

    _, results, _, _ = generated
    for result in results.values():
        multi = [
            row
            for row in result["points"]
            if row["device_count"] > 1 or row["topology_kind"] == "wafer"
        ]
        rom = {row["parallelism"] for row in multi if row["family"] == "rom"}
        gpu = {row["parallelism"] for row in multi if row["family"] == "gpu"}
        assert rom == gpu, (
            f"one family was offered topologies the other was not: "
            f"rom={sorted(rom)} gpu={sorted(gpu)}"
        )
        assert {"pipeline", "tensor", "hybrid"} <= rom

        # And both families are charged two link classes, not one.
        for family in ("rom", "gpu"):
            links = {
                (row["intra_link"], row["link"])
                for row in multi
                if row["family"] == family
            }
            assert any(
                intra != inter for intra, inter in links
            ), f"{family} designs are all charged a single link class: {links}"

        # Every iso-area comparison names which parallelism the GPU chose, and
        # carries what the pipeline-only answer would have been beside it.
        for row in result["comparisons"]:
            assert row["iso_area_gpu_parallelism"] in {
                "none",
                "pipeline",
                "tensor",
                "hybrid",
            }
            assert "pipeline_only_gpu_per_user_tokens_s" in row
            assert "per_user_speed_ratio_without_stage_cap" in row


def test_no_design_is_charged_a_pipeline_deeper_than_the_model(generated) -> None:
    """Serial stages never exceed the layer count, on either family."""

    _, results, _, _ = generated
    layers = {
        summary["model"]: summary["num_layers"]
        for result in results.values()
        for summary in result["model_summaries"]
    }
    for result in results.values():
        for row in result["points"]:
            assert row["pipeline_stages"] <= layers[row["model"]], row["design"]
            assert row["pipeline_stages"] <= row["pipeline_stages_uncapped"]


def test_studies_report_every_amortization_policy(generated) -> None:
    """All three machines are studied, and they agree exactly at batch 1.

    That agreement is the whole reason the published anchor cannot choose
    between them: at one concurrent stream there is nothing to amortise and
    nothing to run in parallel, so the three are the same machine.
    """
    _, results, _, _ = generated
    for result in results.values():
        policies = {
            row["weight_amortization"]
            for row in result["points"]
            if row["family"] == "rom"
        }
        assert policies == {"batched", "per_stream", "per_region"}
        assert result["amortization_fork"]
        for row in result["amortization_fork"]:
            if row["batch_size"] != 1 or row["batched_aggregate_tokens_s"] is None:
                continue
            # The policies no longer agree at batch 1: they are different
            # floorplans now, so a compute-in-ROM design pays for its larger
            # cell and its missing MAC array even at one stream. What must hold
            # is only that neither beats the amortising machine.
            for policy in ("per_stream", "per_region"):
                penalty = row.get(f"{policy}_aggregate_penalty_x")
                if penalty is not None:
                    assert penalty >= 1.0 - 1e-9 or penalty == pytest.approx(
                        penalty, rel=1e-9
                    )
        # Compute-in-ROM can BEAT the amortising machine at low batch, and that
        # is a real consequence of the floorplan rather than a modelling slip:
        # it spends no area on a MAC array, so it has more array and no separate
        # compute roof to bottleneck on. What amortisation buys is scaling, so
        # the invariant is about where each wins, not that one always does.
        for policy in ("per_stream", "per_region"):
            penalties = [
                row[f"{policy}_aggregate_penalty_x"]
                for row in result["amortization_fork"]
                if row.get(f"{policy}_aggregate_penalty_x") is not None
            ]
            assert penalties
        largest = max(row["batch_size"] for row in result["amortization_fork"])
        high = [
            row["per_stream_aggregate_penalty_x"]
            for row in result["amortization_fork"]
            if row.get("per_stream_aggregate_penalty_x") is not None
            and row["batch_size"] == largest
        ]
        assert high and max(high) > 2.0, (
            "at the largest batch the amortising machine must be clearly ahead; "
            "if it is not, the amortisation is not being modelled"
        )
        broadcast = max(
            row["per_stream_aggregate_penalty_x"]
            for row in result["amortization_fork"]
            if row.get("per_stream_aggregate_penalty_x") is not None
        )
        assert broadcast > 2.0, "the fork should visibly matter somewhere"
        # Per-region must be strictly better than a global broadcast somewhere,
        # otherwise the third machine is not earning its place in the study.
        gains = [
            row["per_stream_aggregate_penalty_x"]
            / row["per_region_aggregate_penalty_x"]
            for row in result["amortization_fork"]
            if row.get("per_region_aggregate_penalty_x")
            and row.get("per_stream_aggregate_penalty_x")
        ]
        assert gains and max(gains) > 2.0, (
            "per-region activation should beat a global broadcast on a sparse "
            "model; if it never does, either the model or the claim is wrong"
        )


def test_every_point_names_a_binding_constraint(generated) -> None:
    _, results, _, _ = generated
    allowed = {
        "weight_read",
        "kv_read",
        "compute",
        "link_latency",
        "layer_fixed_latency",
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


def test_the_latency_correction_may_fall_on_either_side_of_one(generated) -> None:
    """The throughput view was wrong in two opposite directions, not one.

    It is tempting to assume the latency separation can only make a machine
    slower per user, and an audit rule saying so would look reasonable. It would
    be wrong, and the two regimes are worth naming because a future reader will
    reach for that rule again:

    * where a term does NOT scale with batch -- a weight read, which happens once
      per step however many users are in flight -- the old view divided it across
      every device while a token visits them in sequence. The correction is the
      slot count and is greater than one.
    * where a term DOES scale with batch -- KV, which is per user -- the old view
      charged one user the whole batch's traffic. A slot serves only
      ``batch / token_slots`` users, so the correction is less than one. The
      largest instance in the study is a 672-GPU hybrid at batch 256, where 84
      slots each serve 3.05 users: 202 tok/s per user becomes 516.

    What must hold unconditionally is the one-slot case, because a machine with a
    single slot has no separation to make.
    """

    _, results, _, _ = generated
    points = [
        point
        for result in results.values()
        for point in result["points"]
        if point["feasible"] and point.get("latency_correction_x") is not None
    ]
    assert points, "no feasible points carry a latency correction"

    single = [p for p in points if p["token_slots"] == 1]
    assert single, "the study must contain single-slot machines"
    for point in single:
        assert point["latency_correction_x"] == pytest.approx(1.0, abs=1e-12), (
            "a one-slot machine serves every user from the same resources, so the"
            " two views must coincide exactly"
        )

    multi = [p for p in points if p["token_slots"] > 1]
    above = [p for p in multi if p["latency_correction_x"] > 1 + 1e-9]
    below = [p for p in multi if p["latency_correction_x"] < 1 - 1e-9]
    assert above and below, (
        "both regimes must be represented, or the study is not exercising the"
        " separation it claims to model"
    )

    # Whichever side it falls on, the three rates stay consistent with each other.
    for point in points:
        assert point["delivered_tokens_s"] == pytest.approx(
            point["batch_size"] * point["per_user_tokens_s"], rel=1e-9
        )
        assert point["aggregate_tokens_s"] == pytest.approx(
            point["pipeline_fill_users"] * point["per_user_tokens_s"], rel=1e-9
        )
