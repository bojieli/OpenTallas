"""Tests for the area-constrained roofline model and its validation gates.

The two named gates -- ``test_gate_taalas_hc1_...`` and
``test_gate_a100_...`` -- are the load-bearing checks.  They fail loudly if the
methodology drifts, and they are deliberately written to say *how far* off the
model is rather than only that it is off, because the interesting failure is a
technology input that turns out to be wrong rather than a broken assertion.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
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
    LinkEvent,
    Technology,
    Topology,
    a100_power_anchor,
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
    device_static_power,
    rom_device_budget,
    taalas_hc1_anchor,
    load_study_artifact,
    taalas_hc1_power_anchor,
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
ARTIFACTS = ("analytical.json", "points.json", "sweep.csv", "REPORT.md")


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


def test_gate_taalas_hc1_shipping_part_exposes_the_capacity_failure(
    technology, llama
) -> None:
    """The corrected floorplan must retain, not hide, the failed HC1 gate.

    An 8B model on 815 mm2 at N6 with mask-ROM weights should reproduce the
    shipping part before the model is trusted for extrapolation.  The current
    evidence-backed ROM density and compute-in-ROM allocation do not fit that
    model.  Zero throughput is therefore the finding; relaxing capacity until
    the gate passes would turn this validation check into a fit.
    """

    check = taalas_hc1_anchor(technology, llama, per_bit_cim=True)
    requirements = check.detail["back_derived_requirements"]
    assert not check.passed
    assert check.modelled_value == 0.0
    assert check.ratio == 0.0
    assert check.detail["binding_constraint"] == "capacity_or_format"
    reasons = check.detail["step"]["reasons"]
    assert any(reason.startswith("AREA:") for reason in reasons)
    assert any(reason.startswith("CAPACITY:") for reason in reasons)
    assert (
        check.detail["budget"]["weight_capacity_bytes"]
        < check.detail["step"]["metrics"]["stored_weight_bytes"]
    )
    # Capacity fails first, but the independent rate diagnostic remains useful:
    # the ROM read-bandwidth density is not an order of magnitude short.
    assert requirements["rom_density_shortfall_x"] < 2.0
    # The compute-density requirement is deliberately NOT asserted here. HC1 has
    # no MAC array -- the multiply is the array sweep -- so back-deriving a
    # compute density for it asks what a separate compute unit would have to
    # deliver. It is reported because it is the right question for the
    # storage-plus-MAC reading, not because it validates compute-in-ROM.


def test_gate_taalas_hc1_passes_with_one_select_cell_per_weight(
    technology, llama
) -> None:
    """Per-weight select cells, the repository's own mechanism, fit the part.

    The per-bit rule above charged a 1.6x cell per stored bit.  The mechanism
    reconstruction has one select transistor per <=4-bit weight, and with that
    rule (``rom.cim_bits_per_cell``, the default) the HC1 floorplan holds its
    weights and lands inside the gate's 2x tolerance, bound by the array sweep.
    The cell width comes from the vendor the gate checks, so this pass is not
    independent on capacity.
    """

    check = taalas_hc1_anchor(technology, llama)
    assert check.passed
    assert 1.0 < check.ratio < 2.0
    assert check.detail["binding_constraint"] == "weight_read"
    band = check.detail["layer_fixed_latency_band"]
    # The published rate lies inside the latency band, not at a fitted point.
    assert band["high"]["ratio_to_published"] < 1.0 < band["low"]["ratio_to_published"]


def test_gate_taalas_hc1_rom_read_density_remains_near_the_shipping_part(
    technology, llama
) -> None:
    """The ROM read density remains close even though capacity rejects the part.

    This is only a rate diagnostic, not a passing gate: an independent shipping
    part implies a ROM read density near the model's derived value, while the
    corrected capacity chain rejects the floorplan before that rate can bind.
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


def test_the_throughput_gates_report_nonthermal_outcomes(
    technology, llama
) -> None:
    """Neither current throughput result is produced by thermal throttling.

    ``step_time = raw_step_time x thermal_scale`` is the only path from power to
    any rate.  HC1 now returns zero because its corrected array capacity does
    not fit, while A100 remains exact bandwidth arithmetic.  Both must still
    report an unthrottled operating point so the power model cannot be mistaken
    for the cause of either result.
    """

    hc1 = taalas_hc1_anchor(technology, llama)
    assert hc1.modelled_value > 0.0
    assert hc1.detail["binding_constraint"] == "weight_read"
    assert hc1.detail["step"]["thermal_scale"] == 1.0

    a100 = a100_weight_bound_anchor(technology, llama)
    assert a100.modelled_value == pytest.approx(253.9145, abs=1e-3)
    assert a100.ratio == pytest.approx(1.000000, abs=1e-9)
    assert a100.detail["step"]["thermal_scale"] == 1.0


def test_gate_a100_tdp_power_is_reproduced_under_a_saturating_load(
    technology,
) -> None:
    """A TDP is what a part sheds under load, so the gate saturates it.

    This gate is deliberately the WEAKER of the two power gates and the test
    says so: ``power.clock_energy_j_per_mm2_per_cycle`` is 20-45% of a shipping
    GPU's published TDP density, so a sum containing it, compared with a GPU's
    TDP, is partly an input checked against its own family.  What it does test
    is that no term is an order of magnitude out.
    """

    check = a100_power_anchor(technology)
    assert check.published_value == 400.0
    assert check.passed, (
        f"A100 TDP power gate drifted: {check.modelled_value:,.1f} W against a "
        f"published {check.published_value:,.1f} W ({check.ratio:.3f}x). Terms: "
        f"{check.detail['terms_w']}"
    )
    assert 0.5 <= check.ratio <= 1.5
    terms = check.detail["terms_w"]
    # Every term must be present and positive: a gate that passes because a
    # term silently evaluated to zero is worse than one that fails.
    for name in (
        "hbm_traffic",
        "operand_delivery",
        "arithmetic",
        "static_leakage",
        "static_clock",
        "static_memory_interface",
    ):
        assert terms[name] > 0.0, name
    assert check.detail["circularity_warning"]


def test_gate_taalas_hc1_card_power_fails_and_the_failure_is_the_result(
    technology, llama
) -> None:
    """The stronger power gate, and it does not pass. That is the finding.

    Nothing on the ROM side was calibrated on a Taalas figure -- Taalas
    publishes no microarchitecture and no energy -- so this gate is genuinely
    independent, and it says the model is several times below the shipping
    part's published card power.  **This test asserts the SHORTFALL, not a
    pass.**  If someone closes it by tuning a term, this test fails and asks
    them to say which term and why.
    """

    check = taalas_hc1_power_anchor(technology, llama)
    assert check.published_value == 250.0
    assert check.detail["published_band_w"] == [200.0, 250.0]
    assert not check.passed, (
        "the HC1 power gate now passes. That is only good news if a term moved "
        "for a reason. Say which, and check it was not chosen to close this."
    )
    assert 0.15 <= check.ratio <= 0.45, (
        f"HC1 power gate moved out of its reported range: "
        f"{check.modelled_value:,.1f} W ({check.ratio:.3f}x)"
    )
    # ROM leakage is now explicitly charged.  It moves the enumeration just
    # above the measured whole-device idle floor at the point; adding the
    # entire range-high ROM term again is therefore a deliberately conservative
    # upper bound on its effect.
    rom_mm2 = check.detail["area_split_mm2"]["rom_mm2"]
    leak = technology.graded(
        "power", "static_leakage_w_per_mm2", "rom_array"
    ).value
    assert check.detail["rom_array_leakage_charged_w"] == pytest.approx(
        rom_mm2 * leak
    )
    assert check.detail["rom_array_leakage_at_range_high_w"] > check.detail[
        "rom_array_leakage_charged_w"
    ]
    assert not check.detail["terms_w"]["static_floor_binds"]
    assert check.detail["terms_w"]["static_total_charged"] == pytest.approx(
        check.detail["terms_w"]["static_enumerated"]
    )
    closed = check.modelled_value + check.detail[
        "rom_array_leakage_at_range_high_w"
    ]
    assert closed < check.detail["published_band_w"][0]


def test_the_power_band_brackets_both_gates_and_is_monotone(technology, llama) -> None:
    """Every power term is monotone increasing in power, so the band is a band.

    ``at_power_bound`` claims that ``high`` really is the top of the envelope.
    That is a property of the terms rather than of the method, so it is checked
    here instead of assumed there.
    """

    low = technology.at_power_bound("low")
    high = technology.at_power_bound("high")
    for anchor in (
        lambda tech: a100_power_anchor(tech).modelled_value,
        lambda tech: taalas_hc1_power_anchor(tech, llama).modelled_value,
    ):
        assert anchor(low) < anchor(technology) < anchor(high)
    # The band must actually contain the published figures, or it is not a
    # statement about uncertainty -- it is a statement that the model is wrong.
    hc1_low = taalas_hc1_power_anchor(low, llama).modelled_value
    hc1_high = taalas_hc1_power_anchor(high, llama).modelled_value
    assert hc1_low < 200.0 <= hc1_high
    a_low = a100_power_anchor(low).modelled_value
    a_high = a100_power_anchor(high).modelled_value
    assert a_low < 400.0 < a_high


def test_static_power_is_charged_whether_or_not_traffic_flows(
    technology, llama
) -> None:
    """The property that makes the whole rebuild worth doing.

    A machine with almost no traffic still burns leakage and still clocks, so
    its power must not fall to nothing.  Before this the model's power was
    exactly proportional to bytes moved, which is why an idle wafer drew zero.
    """

    budget = _rom_chip(technology, llama, bits=3.5)
    step = evaluate(
        budget, llama, context_tokens=2048, batch_size=1,
        technology=technology,
        weight_bits_per_parameter=3.5,
    )
    static = step.metrics["static_power_w"]
    assert static > 0.0
    assert step.power_w > static - 1e-9
    # Static is a real share of the total, not a rounding correction.
    assert 0.2 < step.metrics["static_power_fraction_of_total"] < 1.0
    # And it is max(enumeration, measured floor), never their sum.
    detail = step.metrics["static_power"]
    assert static == pytest.approx(max(detail["enumerated_w"], detail["floor_w"]))
    assert static < detail["enumerated_w"] + detail["floor_w"]
    assert detail["enumerated_w"] == pytest.approx(
        detail["leakage_w"] + detail["clock_w"] + detail["memory_interface_w"]
    )


def test_leakage_follows_the_area_split_for_all_region_classes(
    technology, llama
) -> None:
    """Leakage is per mm2 of standard-cell region, not per mm2 of die.

    That unit was the worst defect in the submitted leakage term and it is
    load-bearing here: a compute-in-ROM part is mostly array, so charging a
    logic leakage density over its whole die would roughly triple its leakage.
    """

    budget = _rom_chip(technology, llama, bits=3.5)
    detail = budget.static_power.detail
    logic = detail["logic_mm2_per_device"]
    rom = detail["rom_array_mm2_per_device"]
    sram = detail["sram_array_mm2_per_device"]
    assert rom > 0 and logic > 0
    leak_logic = technology.graded(
        "power", "static_leakage_w_per_mm2", "logic"
    ).value
    leak_sram = technology.graded(
        "power", "static_leakage_w_per_mm2", "sram_array"
    ).value
    leak_rom = technology.graded(
        "power", "static_leakage_w_per_mm2", "rom_array"
    ).value
    assert budget.static_power.leakage_w == pytest.approx(
        logic * leak_logic + sram * leak_sram + rom * leak_rom
    )
    assert leak_rom > 0.0
    assert leak_rom < leak_logic
    assert budget.static_power.leakage_w < (logic + rom + sram) * leak_logic


def test_the_throttle_solves_against_static_headroom_not_total_power(
    technology, llama
) -> None:
    """The old rule made every design coolable; this one does not.

    Under ``thermal_scale = total_power / limit`` stretching a step reduced the
    modelled power, so any power was coolable at some speed.  Static power does
    not fall when a step is stretched, so the coolable step time solves against
    the headroom the static power leaves.  A part whose leakage and clock alone
    exceed its budget is not slow -- it does not exist.
    """

    budget = _rom_chip(technology, llama, bits=3.5)
    limit = budget.cooling_limit_w
    static = budget.static_power.total_w
    assert static < limit

    # Squeeze the budget until the same design is thermally limited, by handing
    # it a cooling limit just above its static power.  Nothing about the design
    # changes; only what it is allowed to shed.
    squeezed = replace(budget, cooling_limit_w=static * 1.02)
    step = evaluate(
        squeezed, llama, context_tokens=2048, batch_size=1,
        technology=technology,
        weight_bits_per_parameter=3.5,
    )
    assert step.thermal_scale > 1.0
    assert step.binding_constraint == "thermal"
    # A throttled point sits exactly ON its limit: that is what the throttle
    # solves for, and under the old rule it could not.
    assert step.power_w == pytest.approx(squeezed.cooling_limit_w, rel=1e-9)
    # And the static share does not shrink as the step is stretched.
    assert step.metrics["static_power_w"] == pytest.approx(static)


def test_a_design_whose_static_power_exceeds_its_budget_does_not_exist(
    technology, llama
) -> None:
    """Dark silicon in its strongest form, which the model could not express.

    If leakage and the clock tree alone meet the cooling budget, no step time
    makes the part coolable.  The honest answer is that the design is
    infeasible, not that it runs slowly.
    """

    budget = _rom_chip(technology, llama, bits=3.5)
    starved = replace(
        budget, cooling_limit_w=budget.static_power.total_w * 0.9
    )
    step = evaluate(
        starved, llama, context_tokens=2048, batch_size=1,
        technology=technology,
        weight_bits_per_parameter=3.5,
    )
    assert not step.feasible
    assert step.binding_constraint == "cooling"
    assert any(reason.startswith("COOLING:") for reason in step.reasons)
    assert step.per_user_tokens_s == 0.0
    # The violation is reported at its true size rather than as an infinity.
    assert math.isfinite(step.power_w)
    assert step.power_w > starved.cooling_limit_w


def test_energy_per_token_includes_the_static_share(technology, llama) -> None:
    """Joules per token is only comparable across machines if it is total.

    A machine that is fast and leaky must not be flattered against one that is
    slow and cool, so the static power is amortised over the tokens the step
    actually produces rather than left out of the numerator.
    """

    budget = _rom_chip(technology, llama, bits=3.5)
    step = evaluate(
        budget, llama, context_tokens=2048, batch_size=1,
        technology=technology,
        weight_bits_per_parameter=3.5,
    )
    total = step.metrics["energy_j_per_token"]
    dynamic = step.metrics["dynamic_energy_j_per_token"]
    assert total > dynamic > 0
    assert total == pytest.approx(
        step.power_w * step.step_time_s / step.metrics["pipeline_fill_users"]
    )
    # And the breakdown of the dynamic half sums to it.
    assert sum(step.metrics["dynamic_energy_breakdown_j"].values()) == pytest.approx(
        dynamic * step.metrics["microbatch_per_slot"]
    )


def test_operand_delivery_is_charged_on_every_byte_that_moves(
    technology, llama
) -> None:
    """The term the model priced at zero: getting a byte to the arithmetic.

    A Horowitz-class MAC energy is the ALU, and ``rom_read_j_per_byte``'s stated
    boundary stops at the macro output latch, so without this term nothing at
    all was charged for the distance between them.
    """

    budget = _rom_chip(technology, llama, bits=3.5)
    step = evaluate(
        budget, llama, context_tokens=2048, batch_size=1,
        technology=technology,
        weight_bits_per_parameter=3.5,
    )
    breakdown = step.metrics["dynamic_energy_breakdown_j"]
    per_byte = technology.graded("energy", "operand_delivery_j_per_byte").value
    moved = (
        step.metrics["engaged_weight_bytes"]
        + step.metrics["kv_transfer_bytes_per_step"]
    )
    assert breakdown["operand_delivery_j"] == pytest.approx(moved * per_byte)
    # On a ROM part it is LARGER than the array read it accompanies, which is
    # the consequence of moving rom_read_j_per_byte from 0.5 to 0.08 pJ/B and
    # is why that correction made the HC1 power gate worse rather than better.
    assert breakdown["operand_delivery_j"] > breakdown["weight_read_j"]


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
        # The term the model priced at zero: getting a byte from the array that
        # holds it to the arithmetic that consumes it.
        "energy.operand_delivery_j_per_byte",
        "energy.rom_read_j_per_byte",
        "energy.sram_read_j_per_byte",
        "floorplan.interconnect_area_fraction",
        "floorplan.overhead_area_fraction",
        # The power block. Every term in it bar the clocked-idle floor (which is
        # `executed`, with its artifact committed) and the logic clock
        # multiplier (which is 1.0 by definition of the calibration region) is
        # a judgement over a stated range, and two of them -- the fabric clock
        # and the array clock multipliers -- MULTIPLY, which is why the power
        # gates are reported at both ends of the whole band rather than at a
        # point inside their product.
        "power.clock_energy_j_per_mm2_per_cycle",
        "power.clock_region_multiplier.rom_array",
        "power.clock_region_multiplier.sram_array",
        "power.fabric_clock_hz",
        "power.gpu_logic_area_fraction",
        "power.memory_interface_idle_w_per_stack",
        "power.static_leakage_w_per_mm2.logic",
        # The ROM-array term now has an explicit device-count derivation, but
        # that derivation still rests on assumed leakage and array inputs.
        "power.static_leakage_w_per_mm2.rom_array",
        "power.static_leakage_w_per_mm2.sram_array",
        # NVIDIA publishes no B200 clock in any first-party document.
        "reference_parts.b200_sxm.clock_frequency_hz",
        "hbm.hbm2e.phy_area_mm2_per_stack",
        "hbm.hbm2e.stack_beachfront_mm",
        "hbm.hbm3e.phy_area_mm2_per_stack",
        "hbm.hbm3e.stack_beachfront_mm",
        "kv.access_granularity_bytes.sram",
        "kv.index_layout",
        "latency.array_pass_boundaries_per_layer",
        "latency.array_pass_boundaries_per_layer_by_model.DeepSeek-V4-Flash-0731",
        "latency.array_pass_boundaries_per_layer_by_model.DeepSeek-V4-Pro-0813",
        "latency.array_pass_boundaries_per_layer_by_model.DeepSeek-V4.1-Flash",
        "latency.array_pass_boundaries_per_layer_by_model.DeepSeek-V4.1-Flash-engram-hbm",
        "latency.array_pass_boundaries_per_layer_by_model.DeepSeek-V4.1-Flash-engram-host",
        "latency.array_pass_boundaries_per_layer_by_model.Qwen3-8B",
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
        "links.inter_wafer.hop_latency_s",
        # The generic NVLink entry, kept for the crossover doc's worked
        # examples and exercised by no study. The three entries the studies
        # actually charge -- nvlink3, nvlink5, nvlink5_nvl72 -- are no longer
        # assumed: each is now half a measured small-message all-reduce on the
        # fabric it prices, and `links.on_wafer.hop_latency_s` is likewise
        # derived from the published Cerebras core grid and clock. This entry
        # still rests on a blog and is still swept.
        "links.nvlink.hop_latency_s",
        "links.on_package.fabric",
        "links.on_package.hop_latency_s",
        "reference_parts.taalas_hc1.weight_amortization",
        "reference_parts.taalas_hc1.weight_bits_per_parameter",
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


def test_rom_capacity_density_inherits_the_corrected_derived_grade(technology) -> None:
    ratio = technology.graded("rom", "cell_to_sram_cell_area_ratio")
    assert ratio.grade == "derived"
    assert technology.rom_bits_per_mm2("N6").grade == "derived"


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


def test_the_two_binding_hop_latencies_are_no_longer_assumed(technology) -> None:
    """**The re-grading of 2026-08-31, pinned so it cannot silently revert.**

    Both constants that decide most of the headline were graded ``assumed``
    with sweeps set by judgement: ``on_wafer`` at 100 ns over 30-500 ns (16.7x)
    and ``nvlink3`` at 1.5 us over 1.0-5.5 us.  Each is now ``derived`` from a
    published or measured figure at the granularity the model actually charges,
    and each note has to say what that granularity is -- because the failure
    this test guards is not a wrong number, it is a *right number for the wrong
    object*: Cerebras' published one-cycle hop is a 0.23 mm core-to-core step
    and this model's hop is a 28.5 mm reticle-field crossing, 126 of them, and
    substituting one for the other moves the headline from 8.3x to 14.7x.
    """

    wafer = technology.graded("links", "on_wafer", "hop_latency_s")
    assert wafer.grade == "derived"
    assert wafer.value == pytest.approx(1.25e-7)
    block = technology.raw["links"]["on_wafer"]["hop_latency_s"]
    assert block["range_low"] == pytest.approx(7.5e-8)
    assert block["range_high"] == pytest.approx(2.5e-7)
    # The band is now 3.3x rather than 16.7x, and both ends are computed.
    assert block["range_high"] / block["range_low"] < 4.0
    assert "reticle field" in block["note"]
    assert "NOT a tile-to-tile hop" in block["note"]

    nvlink = technology.graded("links", "nvlink3", "hop_latency_s")
    assert nvlink.grade == "derived"
    assert nvlink.value == pytest.approx(2.5e-6)
    # 2 x hop IS the whole in-domain all-reduce, and the note must say so,
    # because that is the only reading under which the number is defensible.
    assert technology.collective_traversals("nvlink3", 8) == 2.0
    assert "all-reduce" in technology.raw["links"]["nvlink3"]["hop_latency_s"]["note"]
    # The claim this entry used to rest on is withdrawn in the note itself.
    assert "WITHDRAWN" in technology.raw["links"]["nvlink3"]["hop_latency_s"]["note"]

    # The wafer-to-wafer link is the one that is still a judgement, and it is
    # now the largest unmeasured link in the model.  If it is ever re-graded,
    # this assertion should be the thing that fails.
    assert technology.graded(
        "links", "inter_wafer", "hop_latency_s"
    ).grade == "assumed"


def test_a_link_latency_bound_can_be_taken_on_one_side_at_a_time(
    technology,
) -> None:
    """**The presentation fix, pinned.**

    The published band used to move every link at once.  Moving both sides
    together tests a *common-mode* error; it does not answer "how much of this
    uncertainty is ours", and because the two sides partly cancel the joint
    interval came out narrower than the wafer side's own.  ``links=`` restricts
    the sweep to one side's fabrics, and nothing outside that set may move.
    """

    wafer_only = technology.at_link_latency_bound("low", ("on_wafer", "inter_wafer"))
    assert wafer_only.link("on_wafer")[0].value == pytest.approx(7.5e-8)
    assert wafer_only.link("inter_wafer")[0].value == pytest.approx(1e-6)
    # The cluster fabric is untouched, which is the whole point.
    assert wafer_only.link("nvlink3")[0].value == technology.link("nvlink3")[0].value
    assert (
        wafer_only.link("infiniband_hdr")[0].value
        == technology.link("infiniband_hdr")[0].value
    )

    cluster_only = technology.at_link_latency_bound(
        "high", ("nvlink3", "infiniband_hdr")
    )
    assert cluster_only.link("nvlink3")[0].value == pytest.approx(1.03e-5)
    assert cluster_only.link("infiniband_hdr")[0].value == pytest.approx(2.2e-5)
    assert cluster_only.link("on_wafer")[0].value == technology.link("on_wafer")[0].value

    # And the default is still every link, on both sides at once.
    joint = technology.at_link_latency_bound("high")
    assert joint.link("on_wafer")[0].value == pytest.approx(2.5e-7)
    assert joint.link("nvlink3")[0].value == pytest.approx(1.03e-5)


def test_each_study_charges_a_wafer_fabric_of_its_own_node(technology) -> None:
    """**The asymmetry this pair of entries exists to remove.**

    The GPU side of these studies always named its link per generation --
    ``nvlink3`` at 2.5 us for the A100 study, ``nvlink5`` at 1.2 us for the
    B200 study.  The ROM side did not: one ``on_wafer`` constant, derived from
    Cerebras WSE-2 at TSMC **7nm**, served both.  That left ``n6_vs_a100``
    correctly matched and ``n5_vs_b200`` charging a 7nm-era wafer fabric
    against a 4nm-era NVLink, which understates the ROM side in the study where
    it should be strongest.

    This asserts the structure rather than the value.  The two figures happen
    to be equal -- see the test below, which is the null result -- and a test
    on the values alone would pass just as well if the split were quietly
    undone.
    """

    runner = _load_runner()
    wafer_links = {
        study_id: config["rom_intra_link"]
        for study_id, config in runner.STUDIES.items()
    }
    assert wafer_links == {
        "n6_vs_a100": "on_wafer",
        "n5_vs_b200": "on_wafer_n5",
    }, "each study must name the wafer fabric of its own node"
    # Both must exist, and neither study may fall back to the other's.
    for name in wafer_links.values():
        assert name in technology.raw["links"]
        assert technology.link_fabric(name) == "mesh"
    # The GPU side is the precedent this mirrors: two entries, one per
    # generation, and they carry different numbers.
    assert runner.STUDIES["n6_vs_a100"]["intra_link"] == "nvlink3"
    assert runner.STUDIES["n5_vs_b200"]["intra_link"] == "nvlink5"
    assert technology.graded(
        "links", "nvlink3", "hop_latency_s"
    ).value != technology.graded("links", "nvlink5", "hop_latency_s").value


def test_the_two_wafer_fabrics_land_equal_and_say_why(technology) -> None:
    """**A null result, asserted so it cannot be mistaken for an oversight.**

    Splitting ``on_wafer`` by node did not make the N5 study faster.  The
    method has two node-dependent terms and neither moved: Cerebras spent the
    N7-to-N5 shrink on the core (48 kB of SRAM, 110,000 standard cells and a
    50/50 split unchanged, with the transistors going into a 4-wide to 8-wide
    FP16 SIMD) rather than on the pitch between cores, and published no clock
    at all for WSE-3 -- back-derivation from its own memory and fabric
    bandwidths, calibrated on WSE-2 where the clock IS published at 1.1 GHz,
    puts it at 1.01-1.12 GHz.  Three published-input pitch estimators put the
    N5 field crossing at 126-131 hops against the N7 route's 127, i.e. equal to
    within a method whose N7 input is itself a rounded die dimension, and if
    anything **slower**.

    So the two are stated equal, and this test pins that both entries carry the
    derivation that says so.  A future edit that moves one without the other
    should have to come through here.
    """

    n7 = technology.graded("links", "on_wafer", "hop_latency_s")
    n5 = technology.graded("links", "on_wafer_n5", "hop_latency_s")
    assert n5.value == n7.value == pytest.approx(1.25e-07)
    for entry in ("on_wafer", "on_wafer_n5"):
        block = technology.raw["links"][entry]["hop_latency_s"]
        assert block["range_low"] == pytest.approx(7.5e-08)
        assert block["range_high"] == pytest.approx(2.5e-07)
        assert block["grade"] == "derived"
    # `derived` means the formula is in the note, and it is the SAME formula on
    # both: two figures derived two ways would not be comparable, which is the
    # whole reason for splitting the entry.
    for entry in ("on_wafer", "on_wafer_n5"):
        note = technology.raw["links"][entry]["hop_latency_s"]["note"]
        assert "core pitch" in note and "cycles / clock" in note
    n7_note = technology.raw["links"]["on_wafer"]["hop_latency_s"]["note"]
    n5_note = technology.raw["links"]["on_wafer_n5"]["hop_latency_s"]["note"]
    assert "N7" in n7_note and "on_wafer_n5" in n7_note
    assert "WSE-3" in n5_note and "5 nm" in n5_note
    # The null is stated as a null, with its direction, rather than left for a
    # reader to infer from two equal numbers.
    assert "NULL" in n5_note
    assert "SLOWER" in n5_note


def test_the_wafer_split_is_load_bearing(technology) -> None:
    """Moving one node's wafer fabric must move that study and only that one.

    Two entries that no study distinguishes are two copies of one number, and
    the defect would be back without the config ever looking wrong.
    """

    runner = _load_runner()
    reticle = technology.graded("reticle", "area_mm2").value
    wafer = technology.graded("wafer", "area_mm2").value
    charged = {}
    for study_id, config in runner.STUDIES.items():
        plans = runner._fabric_plans(
            technology, config, wafer_area=wafer, reticle_area=reticle
        )
        charged[study_id] = {
            plan.intra_link for plan, _area in plans if plan.kind == "wafer"
        }
    assert charged["n6_vs_a100"] == {"on_wafer"}
    assert charged["n5_vs_b200"] == {"on_wafer_n5"}

    # And the sensitivity sweeps the entry each study actually charges, so the
    # per-side band is that side's own band and not a neighbour's.
    assert runner._link_latency_scopes(runner.STUDIES["n6_vs_a100"])["rom"] == (
        "on_wafer",
        "inter_wafer",
    )
    assert runner._link_latency_scopes(runner.STUDIES["n5_vs_b200"])["rom"] == (
        "on_wafer_n5",
        "inter_wafer",
    )

    # Perturbing one moves only its own study's collective.
    raw = json.loads(json.dumps(technology.raw))
    raw["links"]["on_wafer_n5"]["hop_latency_s"]["value"] = 1e-08
    perturbed = replace(technology, raw=raw)
    for name, moved in (("on_wafer_n5", True), ("on_wafer", False)):
        event = LinkEvent(
            count=1,
            link=name,
            kind="all_reduce",
            span=57,
            description=f"probe on {name}",
        )
        before, _ = technology.link_event_cost_s(event, activation_bytes=4096)
        after, _ = perturbed.link_event_cost_s(event, activation_bytes=4096)
        assert (after < before) is moved, (
            f"{name} should {'' if moved else 'not '}move when on_wafer_n5 does"
        )


def test_the_scale_out_link_is_one_number_on_both_sides(technology) -> None:
    """Both studies carry one measured HDR point, with the NDR bias disclosed.

    ``inter_wafer`` is charged by BOTH studies, which looks like the same
    defect ``on_wafer`` had.  It is not, because its counterpart on the GPU
    side is the scale-out fabric, and ``infiniband_hdr`` and ``infiniband_ndr``
    carry the same 2.03 us GPU-buffer measurement.  It was measured on the HDR
    machine; carrying it into the NDR study is an explicit conservative bias,
    not evidence that the generations have identical latency.
    """

    hdr = technology.graded("links", "infiniband_hdr", "hop_latency_s")
    ndr = technology.graded("links", "infiniband_ndr", "hop_latency_s")
    assert hdr.value == ndr.value == pytest.approx(2.03e-06)
    assert hdr.grade == ndr.grade == "measured"
    assert "HDR MEASUREMENT" in technology.raw["links"]["infiniband_ndr"][
        "hop_latency_s"
    ]["note"]
    # They are two entries and they DO differ -- on the terms the node moves.
    assert technology.graded(
        "links", "infiniband_hdr", "bytes_s"
    ).value != technology.graded("links", "infiniband_ndr", "bytes_s").value

    runner = _load_runner()
    for config in runner.STUDIES.values():
        assert config["rom_inter_link"] == "inter_wafer"


def test_on_package_is_charged_by_no_design_in_either_study() -> None:
    """The third link in the audit, and the reason it needs no split.

    ``links.on_package`` is 300 ns, graded ``assumed``, and a single value --
    but no design in either study charges it.  The ROM family's fabrics are the
    wafer mesh and the wafer-to-wafer link; the GPU family's are NVLink and
    InfiniBand.  A constant no comparator binds on cannot introduce an
    asymmetry between two studies, so it is reported rather than changed.
    """

    for study_id in ("n6_vs_a100", "n5_vs_b200"):
        body = load_study_artifact(
            ROOT / "results" / "roofline" / study_id / "analytical.json"
        )
        charged = {
            (point.get("link"), point.get("intra_link"))
            for point in body["points"]
        }
        flat = {name for pair in charged for name in pair if name}
        assert "on_package" not in flat, (
            f"{study_id} now charges on_package; the audit that said no design "
            "does has to be redone"
        )


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


def test_a_rom_pipeline_gives_a_user_less_despite_adding_silicon(
    technology, qwen
) -> None:
    """The same rule on the other family, where it bites harder still.

    A ROM array is sized to the bytes it holds, so adding N pipeline devices
    does not reduce the full-array sweep the way adding GPUs adds HBM channels.
    Each stage takes a technology sweep time for its share, and one token pays
    all N stages.  Even though this probe adds silicon with every device, its
    per-user rate therefore falls.
    """

    stored = qwen.checkpoint_bytes
    resident = kv_traffic(qwen, 8192).storage_bytes_per_user
    rates: dict[int, float] = {}
    corrections: dict[int, float] = {}
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
            # Large enough that the corrected ROM capacity density admits the
            # one-device baseline; otherwise zero-versus-nonzero would test
            # feasibility rather than pipeline latency.
            area_mm2_per_device=4_000.0,
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
        corrections[devices] = step.metrics["latency_correction_x"]
        if devices == 1:
            assert corrections[devices] == 1.0
        else:
            assert 1.0 < corrections[devices] < step.metrics["token_slots"]
    ordered = [rates[devices] for devices in sorted(rates)]
    assert ordered == sorted(ordered, reverse=True)
    assert rates[16] < rates[1] / 10
    ordered_corrections = [corrections[devices] for devices in sorted(corrections)]
    assert ordered_corrections == sorted(ordered_corrections)


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
    has no MAC array, has a larger cell, and reserves the configured fraction
    for pre-compute and accumulation.  It is a different machine at every
    batch.
    """
    from opentallas.roofline import balanced_area_split

    splits = {
        policy: balanced_area_split(
            technology,
            node="N6",
            total_mm2=815.0,
            weight_store="rom",
            kv_store="sram",
            # Leave both floorplans feasible so their structural difference is
            # measured rather than comparing one real split with one clamp.
            stored_weight_bytes=2.0e9,
            resident_kv_bytes=2.0e8,
            weight_amortization=policy,
        )
        for policy in ("batched", "per_stream")
    }
    assert not splits["batched"].reasons
    assert not splits["per_stream"].reasons
    precompute_fraction = technology.graded(
        "rom", "cim_precompute_area_fraction"
    ).value
    assert splits["per_stream"].compute_mm2 == pytest.approx(
        815.0 * precompute_fraction
    )
    assert splits["batched"].compute_mm2 > splits["per_stream"].compute_mm2
    multiplier = technology.rom_cell_area_multiplier("per_stream").value
    assert splits["per_stream"].rom_mm2 == pytest.approx(
        splits["batched"].rom_mm2 * multiplier
    )


def test_the_floorplan_comparison_reports_capacity_before_rate(
    technology, llama
) -> None:
    """A clamped array must not be narrated as holding the requested weights."""

    runner = _load_runner()
    comparison = runner._floorplan_comparison(technology, llama, "N6", 815.0)
    storage = comparison["batched"]
    cim = comparison["per_region"]

    assert storage["feasible"]
    assert storage["capacity_ratio"] == pytest.approx(1.0)
    assert storage["feed_ratio"] > 1.0
    assert not cim["feasible"]
    assert cim["capacity_ratio"] < 1.0
    assert any(reason.startswith("AREA:") for reason in cim["reasons"])


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
    # no region drawn twice.  This makes the per-region sweep-count term equal
    # to the global-broadcast term; it does not erase the policies' different
    # cell sizes and floorplans.
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
            # The corrected density no longer fits this 3.5-bit probe in
            # 815 mm2.  Give every policy enough area so this test isolates the
            # cell multiplier's capacity/bandwidth coupling.
            area_mm2_per_device=2_000.0,
            topology=_single_chip(),
            stored_weight_bytes=llama.total_parameters * 3.5 / 8.0,
            resident_kv_bytes=kv_traffic(llama, 2048).storage_bytes_per_user,
            kv_store="sram",
            weight_amortization=policy,
        )
        sweeps[policy] = budget.provenance["rom_full_array_sweep_time_s"].value
        assert not budget.reasons
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
        total_mm2=2_000.0,
        weight_store="rom",
        kv_store="sram",
        stored_weight_bytes=llama.total_parameters * 3.5 / 8.0,
        resident_kv_bytes=0.0,
        weight_amortization="batched",
    )
    large = balanced_area_split(
        technology,
        node="N6",
        total_mm2=2_000.0,
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

    Every scalar term in the ``latency`` block is ``assumed`` and carries a
    range, and the anchor is evaluated at both ends.  The corrected floorplan
    fails capacity before latency can bind, so all three throughput values are
    zero.  The independently computed latency band must remain ordered, and the
    diagnostic fitted cost remains negative rather than being used as an input.
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
    rates = [band[bound]["modelled_tokens_s"] for bound in ("high", "stated", "low")]
    assert 0.0 < rates[0] < rates[1] < rates[2]
    for bound in ("low", "stated", "high"):
        assert band[bound]["binding_constraint"] == "weight_read"
    # The array sweep leaves room for a positive per-layer cost below the gap.
    assert band["per_layer_cost_that_would_close_the_gap_s"] > 0.0
    legacy = taalas_hc1_anchor(technology, llama, per_bit_cim=True)
    assert legacy.detail["layer_fixed_latency_band"]["stated"]["modelled_tokens_s"] == 0.0


def test_each_amortisation_policy_is_sized_on_its_own_floorplan(technology) -> None:
    """Cell size and pre-compute reservation both raise compute-in-ROM die count.

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
    # The continuous ratio is the cell multiplier times the loss of usable
    # array fraction to the compute-in-ROM pre-compute block.  Integer device
    # counts are the ceiling of each policy's own capacity equation.
    ratio = counts["per_region"] / counts["batched"]
    multiplier = technology.rom_cell_area_multiplier("per_region").value
    fixed_fraction = sum(
        technology.graded("floorplan", name).value
        for name in ("overhead_area_fraction", "interconnect_area_fraction")
    )
    precompute_fraction = technology.graded(
        "rom", "cim_precompute_area_fraction"
    ).value
    density = technology.rom_bits_per_mm2("N6").value / 8.0
    expected = {
        "batched": math.ceil(
            stored / (815.0 * (1.0 - fixed_fraction) * density)
        ),
        "per_region": math.ceil(
            stored
            / (
                815.0
                * (1.0 - fixed_fraction - precompute_fraction)
                * density
                / multiplier
            )
        ),
    }
    assert counts == expected
    continuous_ratio = (
        multiplier
        * (1.0 - fixed_fraction)
        / (1.0 - fixed_fraction - precompute_fraction)
    )
    assert continuous_ratio > multiplier
    assert ratio == pytest.approx(continuous_ratio, rel=0.03)


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

    # At the current 3.5-bit density the capacity floor consumes every spare
    # millimetre, so there is nothing for this policy test to allocate.  A
    # 2-bit representation leaves real spare area on both architectures.
    stored = llama.total_parameters * 2.0 / 8.0
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

    weight_bits = 3.0
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
        # The corrected ROM density makes the full checkpoint representation
        # infeasible in this wafer.  The study's 3-bit point fits and leaves
        # enough SRAM slack to exercise the locality diagnostic at batch 1/8.
        stored_weight_bytes=flash.total_parameters * weight_bits / 8.0,
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
            weight_bits_per_parameter=weight_bits,
        )
        assert step.feasible, step.reasons
        bounds[batch] = step.metrics["kv_read_s_under_bank_locality"]
        assert step.metrics["kv_bank_occupancy"] < 1.0
        assert bounds[batch] > step.component_times_s["kv_read"]
        assert bounds[batch] / step.component_times_s["kv_read"] == pytest.approx(
            1.0 / step.metrics["kv_bank_occupancy"]
        )
    # The bound is batch-independent while there are idle banks, which is the
    # ROM locality rule turning up on the SRAM side: an array sized to the KV it
    # holds delivers a fixed KV sweep, exactly as an array sized to the weights
    # delivers a fixed weight sweep.
    assert bounds[1] == pytest.approx(bounds[8], rel=1e-9)
    step_one = evaluate(
        budget,
        flash,
        context_tokens=200_000,
        batch_size=1,
        technology=technology,
        weight_bits_per_parameter=weight_bits,
    )
    assert bounds[1] / step_one.component_times_s["kv_read"] > 10
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
        budget,
        flash,
        context_tokens=200_000,
        batch_size=64,
        technology=technology,
        weight_bits_per_parameter=weight_bits,
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


def _digest(path: Path) -> str:
    """SHA-256 of an artifact, for comparisons pytest must not try to diff.

    ``analytical.json`` is 50 MB. Asserting two of them equal as ``bytes``
    passes when they match and, when they do NOT, hands pytest fifty megabytes
    to build an assertion diff out of -- which consumes the machine and reports
    nothing a reader can act on. The digest fails in one line and says which
    file, which is the whole of what the byte comparison was ever telling us.
    """

    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_runner_is_byte_deterministic(generated) -> None:
    runner, _, first, second = generated
    for study_id in runner.STUDIES:
        for artifact in ARTIFACTS:
            left = first / study_id / artifact
            right = second / study_id / artifact
            assert _digest(left) == _digest(right), (
                f"{study_id}/{artifact} is not reproducible: two runs of the "
                "same inputs produced different bytes"
            )


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
            assert _digest(checked_in) == _digest(first / study_id / artifact), (
                f"results/roofline/{study_id}/{artifact} is stale -- re-run "
                "`python3 tools/run_roofline_studies.py --force`"
            )


def test_every_study_audit_passes(generated) -> None:
    _, results, _, _ = generated
    for study_id, result in results.items():
        audit = result["consistency_audit"]
        assert audit["status"] == "pass", (study_id, audit["errors"][:5])
        assert audit["checks_evaluated"] > 1000


def test_the_band_is_reported_per_side_and_not_only_jointly(generated) -> None:
    """The joint band alone was an artefact, and it hid its own width.

    ``docs/ANALYTICAL_REPORT.md`` A1: the one-sided ROM band was
    13.48x-3.26x while the *published* joint band was 11.82x-4.46x, so the
    interval a reader was given was narrower than the interval one side's own
    constants produced.  Three scopes are emitted now, and this asserts all
    three exist rather than asserting a value, because the values move whenever
    a constant is re-graded and the presentation must not.
    """

    runner, results, _, _ = generated
    for study_id, result in results.items():
        config = runner.STUDIES[study_id]
        rows = result["link_latency_sensitivity"]
        assert rows, study_id
        scopes = {row["scope"] for row in rows}
        assert scopes == {"rom", "gpu", "joint"}, (study_id, scopes)
        for row in rows:
            assert row["bound"] in ("low", "high")
        # The wafer scope is exactly the fabrics this study's ROM designs
        # charge, read from the study rather than hard-wired -- the wafer
        # fabric is node-keyed, so n5_vs_b200's is `on_wafer_n5`.
        rom_links = {
            link for row in rows if row["scope"] == "rom" for link in row["scope_links"]
        }
        wafer_fabric = {
            str(config["rom_intra_link"]),
            str(config["rom_inter_link"]),
        }
        assert rom_links == wafer_fabric, study_id
        # The cluster scope must not smuggle a wafer fabric in with it.
        gpu_links = {
            link for row in rows if row["scope"] == "gpu" for link in row["scope_links"]
        }
        assert not (gpu_links & wafer_fabric), study_id


def test_studies_carry_the_validation_gates(generated) -> None:
    _, results, _, _ = generated
    for result in results.values():
        gates = result["validation_gates"]
        assert not gates["taalas_hc1"]["passed"]
        assert gates["taalas_hc1"]["modelled_value"] == 0.0
        assert gates["taalas_hc1"]["detail"]["binding_constraint"] == (
            "capacity_or_format"
        )
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
    """All three machines are studied under their own floorplans.

    Their sweep-count rules coincide at one stream, but their cell sizes and
    reserved pre-compute areas do not.  The generated fork must retain each
    machine rather than equating their batch-1 rates.
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
        # Static power alone at or above the cooling budget: a design that no
        # step time makes coolable, which the model could not express before.
        "cooling",
        "capacity_or_format",
    }
    for result in results.values():
        for row in result["points"]:
            assert row["binding_constraint"] in allowed
            if not row["feasible"]:
                assert row["reasons"]


def test_the_thermal_limit_actually_binds_somewhere(generated) -> None:
    """Dark silicon exists in the study, and this is the guard that it stays.

    Before static power was charged per second, ``thermal_scale`` was exactly
    1.0 at all 11,747 feasible points in both studies, so ``step_time =
    raw_step_time x thermal_scale`` -- the only path from power to any rate --
    was inert and the model did not express dark silicon at all.  If this test
    starts failing, either the power terms have been quietly shrunk or the
    throttle has gone back to dividing total energy by the total limit.
    """

    _, results, _, _ = generated
    throttled = [
        row
        for result in results.values()
        for row in result["points"]
        if row["feasible"] and row["thermal_scale"] > 1.0 + 1e-12
    ]
    assert throttled, (
        "no point in either study is power-limited. thermal_scale is inert "
        "again and the power model has stopped reaching any rate."
    )
    for row in throttled:
        # A throttled point sits exactly on its cooling limit, which is what
        # the throttle solves for.
        assert row["power_w"] == pytest.approx(row["cooling_limit_w"], rel=1e-6)
        assert row["binding_constraint"] == "thermal"
        assert row["static_power_w"] < row["cooling_limit_w"]


def test_dark_silicon_hits_dense_rom_arrays_and_not_rom_wafers(generated) -> None:
    """Distinguish one ROM wafer from an equal-area cluster of GPU packages.

    A ROM wafer is power-SPARSE: a ROM sweep is a fixed cost spread over far
    more silicon.  An equal-area GPU row is not a wafer; it is a cluster of
    separately powered packages, and some such clusters are throttled in the
    N5/B200 study.  The earlier assertion applied the ROM-wafer claim to both
    families and therefore rejected the very GPU-cluster rows the report
    distinguishes.  What also does NOT survive the old uniform-multiplier
    analysis is its batch dependence -- static power does not scale with
    traffic, so batch 1 is throttled too.
    """

    _, results, _, _ = generated
    throttled = [
        row
        for result in results.values()
        for row in result["points"]
        if row["feasible"] and row["thermal_scale"] > 1.0 + 1e-12
    ]
    assert throttled
    rom_throttled = [row for row in throttled if row["family"] == "rom"]
    assert rom_throttled
    # A ROM *wafer* is the topology kind, not an area: since 2026-09-03 the
    # array ladder samples reticle arrays at every wafer area, and a 57-die
    # array is wafer-sized silicon that is throttled exactly like the smaller
    # arrays are -- it is the wafer's stitched mesh and single power domain
    # the power-sparse reading is about.
    assert all(row["topology_kind"] != "wafer" for row in rom_throttled), (
        "a ROM wafer is now power-limited, which reverses the study's stated "
        "power-sparse result. Say why before accepting it."
    )
    assert any(
        row["family"] == "rom" and row["silicon_area_mm2"] >= 40_000
        for row in throttled
    ), "the wafer-area reticle arrays the ladder emits should throttle like arrays"
    # "46,225 mm2" on the GPU side is a many-package CLUSTER, not one piece of
    # silicon, and every package carries its own published cooling budget. Keep
    # a witness so this distinction cannot silently collapse back into an
    # all-families area assertion.
    assert any(
        row["family"] == "gpu" and row["silicon_area_mm2"] >= 40_000
        for row in throttled
    )
    wafer_headroom = max(
        row["power_headroom_fraction"] or 0.0
        for result in results.values()
        for row in result["points"]
        if row["feasible"]
        and row["family"] == "rom"
        and row["topology_kind"] == "wafer"
    )
    assert wafer_headroom < 0.75, (
        f"a wafer-scale ROM design now reaches {wafer_headroom:.0%} of its "
        "cooling budget; the study's wafer-is-power-sparse reading needs "
        "revisiting before it is repeated"
    )
    assert min(row["batch_size"] for row in rom_throttled) == 1, (
        "no batch-1 point is throttled, which is what a purely "
        "traffic-proportional power model would give. Static power is supposed "
        "to be charged whether or not traffic flows."
    )


def test_every_point_reports_energy_per_token_on_both_sides(generated) -> None:
    """Feasible study points retain energy accounting under the two gate bounds."""

    _, results, _, _ = generated
    for result in results.values():
        for row in result["points"]:
            if not row["feasible"]:
                continue
            assert row["energy_j_per_token"] > 0
            assert row["energy_j_per_token"] >= row["dynamic_energy_j_per_token"]
        rows = result["power_and_energy"]["energy_per_token"]
        assert rows, "no energy-per-token comparison was produced"
        for row in rows:
            assert row["rom_energy_j_per_token"] > 0
            assert row["gpu_energy_j_per_token"] > 0
            assert row["tokens_per_joule_advantage_x"] == pytest.approx(
                row["gpu_energy_j_per_token"] / row["rom_energy_j_per_token"]
            )


def test_json_csv_and_report_are_mutually_consistent(generated) -> None:
    runner, results, first, _ = generated
    import csv as csv_module

    for study_id, result in results.items():
        payload = load_study_artifact(first / study_id / "analytical.json")
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
        assert "FAIL" in report
        assert "No tokens-per-joule ratio is admissible" in report
        assert "machines are identical at batch 1" not in report.lower()
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


def test_no_design_stores_weights_at_a_precision_the_release_does_not_have(generated) -> None:
    """Neither side may be priced at a quantisation the checkpoint does not ship.

    An earlier version offered ROM designs an FP8 re-encoding wherever the
    release was wider than 8.5 bits, and offered it to the ROM side only. Half
    of every feasible Qwen comparison was then won by an 8-bit ROM machine
    competing against a 16-bit GPU -- a free halving of weight traffic for a
    part no execution has ever validated, since ``rom_qwen3`` declares BF16
    contracts and no FP8 contract at all.

    The rule this pins is symmetry, not conservatism: a study may price a
    quantised part, but it must quantise both sides and validate the arithmetic.
    """

    _, results, _, _ = generated
    for study_id, result in results.items():
        by_model: dict[str, set[float]] = {}
        for design in result["designs"]:
            bits = design.get("stored_bits_per_parameter")
            if bits is None:
                continue
            by_model.setdefault(design["model"], set()).add(round(float(bits), 6))
        for model, widths in by_model.items():
            assert len(widths) == 1, (
                f"{study_id}: {model} is priced at more than one stored width "
                f"{sorted(widths)} -- both families must be held at the release's "
                "own packing, or the comparison is not iso-precision"
            )
        for design in result["designs"]:
            assert design.get("representation") in {"native", "official_packed"}, (
                f"{study_id}: {design['design']} declares representation "
                f"{design.get('representation')!r}; only the released packing is priced"
            )


# --------------------------------------------------------------------------
# design selection
# --------------------------------------------------------------------------


def test_a_recommended_design_is_never_dominated_on_both_axes(generated) -> None:
    """**The property whose absence let a wafer be recommended for an 8B model.**

    The old rule ranked ROM designs by per-user tokens/s and then took the
    smallest silicon within 5% of the peak.  A 5% band is a tie-break among
    near-peak designs and is orthogonal to area, so it engages only when a
    smaller design is already within 5% of the best rate -- which is precisely
    the case nobody was worried about.  For Qwen3-8B the best sub-wafer design
    sits at 54% of the wafer's per-user rate, so the band never fired and the
    published answer for an 8B checkpoint that holds in three 815 mm2 reticles
    was one 46,225 mm2 wafer: 2.33x the rate for 18.9x the silicon and an eighth
    of the throughput density.

    This test does not pin an area, a device count or a topology -- any of those
    would have to be retyped every time a technology input moves.  It pins the
    property: **nothing feasible may beat the recommended design on BOTH
    per-user tokens/s and tokens/s per mm2 at once.**  A design that loses on
    both axes to something else that is also buildable is not a recommendation
    under any metric, and a rule that can emit one is the rule that has to
    change.  It is checked against the raw point list rather than against the
    frontier the selector built, so a bug in the selector fails here instead of
    producing a self-consistent wrong answer.
    """

    _, results, _, _ = generated
    checked = 0
    for study_id, result in results.items():
        selection = result["design_selection"]
        for entry in selection["models"]:
            model = entry["model"]
            for record in entry["batch_regimes"]:
                batch = record["batch_size"]
                recommended = record["recommended"]
                if recommended is None:
                    continue
                feasible = [
                    row
                    for row in result["points"]
                    if row["family"] == "rom"
                    and row["model"] == model
                    and row["batch_size"] == batch
                    and row["weight_amortization"]
                    == selection["amortisation_scope"]
                    and row["feasible"]
                    and row["per_user_tokens_s"] > 0
                    and row["silicon_area_mm2"] > 0
                ]
                assert feasible, (
                    f"{study_id}: {model} at batch {batch} has a recommendation "
                    "but no feasible designs"
                )
                rate = recommended["per_user_tokens_s"]
                density = recommended["tokens_s_per_1000mm2"]
                dominators = [
                    (
                        row["design"],
                        row["per_user_tokens_s"],
                        row["per_user_tokens_s"] / row["silicon_area_mm2"] * 1000.0,
                    )
                    for row in feasible
                    if row["design"] != recommended["design"]
                    and row["per_user_tokens_s"] >= rate * (1.0 + 1e-9)
                    and row["per_user_tokens_s"] / row["silicon_area_mm2"] * 1000.0
                    >= density * (1.0 + 1e-9)
                ]
                assert not dominators, (
                    f"{study_id}: the recommended design for {model} at batch "
                    f"{batch} is {recommended['design']} at {rate:,.1f} tok/s per "
                    f"user and {density:,.1f} tok/s per 1,000 mm2, and "
                    f"{len(dominators)} feasible design(s) of the same model beat "
                    f"it on BOTH axes at once, e.g. {dominators[:3]}. A "
                    "recommendation that loses on both axes to something else "
                    "that is also buildable is not a recommendation."
                )
                checked += 1
    assert checked >= 2 * len(STUDY_MODEL_NAMES), (
        f"only {checked} recommendations were checked; the selection block is "
        "not being produced for every model and batch"
    )


STUDY_MODEL_NAMES = (
    "Qwen3-8B",
    "DeepSeek-V4-Flash-0731",
    "DeepSeek-V4-Pro-0813",
)


def test_the_recommendation_is_on_its_own_published_frontier(generated) -> None:
    """The curve is the result; the pick is one point on it.

    The brief this section answers says an honest curve beats a false single
    answer, so the frontier is published in full and the recommendation has to
    be a member of it.  If the pick ever leaves the published curve, the curve
    is not the evidence for the pick and the section is decoration.
    """

    _, results, _, _ = generated
    for study_id, result in results.items():
        for entry in result["design_selection"]["models"]:
            frontier = {row["design"] for row in entry["frontier_batch_1"]}
            best = entry["recommended"]
            assert best is not None, f"{study_id}: {entry['model']} has no pick"
            assert best["design"] in frontier, (
                f"{study_id}: {entry['model']} recommends {best['design']}, "
                f"which is not on its own published frontier {sorted(frontier)}"
            )
            walk = entry["marginal_return_walk"]
            accepted = [rung for rung in walk if rung["accepted"]]
            assert accepted and accepted[-1]["design"] == best["design"], (
                f"{study_id}: {entry['model']}'s walk does not end on its own "
                "recommendation"
            )


def test_every_published_recommendation_states_its_resident_session_count(
    generated,
) -> None:
    """A per-user rate without a session count beside it is not a server claim.

    The recommended machine for Qwen3-8B at batch 1 holds exactly one 8,192-token
    session and the iso-area GPU cluster holds 165.  Dividing the first rate by
    the second and printing the quotient alone is how a single-session latency
    device gets read as a server, so both counts are required on the row.
    """

    _, results, _, _ = generated
    for study_id, result in results.items():
        for entry in result["design_selection"]["models"]:
            for record in entry["batch_regimes"]:
                best = record["recommended"]
                if best is None:
                    continue
                assert best["max_resident_users"] is not None, (
                    f"{study_id}: {entry['model']} at batch "
                    f"{record['batch_size']} publishes a rate with no resident "
                    "session count"
                )
                if best.get("per_user_speed_ratio") is not None:
                    assert (
                        best.get("iso_area_gpu_max_resident_users") is not None
                    ), (
                        f"{study_id}: {entry['model']} at batch "
                        f"{record['batch_size']} publishes a ratio without the "
                        "GPU's resident session count"
                    )


def test_the_selection_metric_is_stated_in_the_report_that_applies_it(
    generated,
) -> None:
    """A recommendation without its rule on the same page is an opinion."""

    runner, results, first, _ = generated
    for study_id, result in results.items():
        report = (first / study_id / "REPORT.md").read_text(encoding="utf-8")
        assert result["design_selection"]["metric"] in report, (
            f"{study_id}: the selection metric is in the JSON but not in the "
            "report that uses it"
        )
        assert "## The recommended design per model" in report
        for entry in result["design_selection"]["models"]:
            best = entry["recommended"]
            assert best["design"].split("/")[-1] in report, (
                f"{study_id}: {entry['model']}'s recommended design is not named "
                "in the report"
            )


def test_the_old_rule_and_the_new_rule_are_both_computed_so_the_move_is_visible(
    generated,
) -> None:
    """The before/after is arithmetic in the artifact, not a claim in prose.

    Both rules are evaluated on the same points, so a reader can see what the
    change bought and a future edit that quietly reverts it fails here.  For
    Qwen3-8B specifically the old rule must still land on a wafer and the new
    one must not: that is the whole reason this section exists, and if it ever
    stops being true the section should be rewritten rather than left standing.
    """

    _, results, _, _ = generated
    for study_id, result in results.items():
        for entry in result["design_selection"]["models"]:
            previous = entry["previous_rule_choice"]
            best = entry["recommended"]
            assert previous is not None and best is not None
            assert best["tokens_s_per_1000mm2"] >= previous[
                "tokens_s_per_1000mm2"
            ] * (1.0 - 1e-9), (
                f"{study_id}: {entry['model']} -- the new rule is supposed to "
                "maximise throughput density and it chose a design with less of "
                "it than the rule it replaced"
            )
            if entry["model"] != "Qwen3-8B":
                continue
            assert previous["topology_kind"] == "wafer", (
                f"{study_id}: the rule this report replaced no longer hands "
                "Qwen3-8B a wafer, so the before/after in the report is stale"
            )
            assert best["topology_kind"] == "array", (
                f"{study_id}: Qwen3-8B is recommended a "
                f"{best['topology_kind']} at {best['silicon_area_mm2']:,.0f} mm2 "
                "-- an 8B checkpoint that holds in three reticle dies must not be "
                "handed a wafer"
            )
            assert best["silicon_area_mm2"] < previous["silicon_area_mm2"]


def test_the_recommendation_is_read_against_n_copies_of_one_unified_die(
    generated,
) -> None:
    """Iso-area, at the ROM side's chosen area, against a real GPU cluster.

    The comparison used to be read at a fixed rung of the area ladder where both
    sides are past their own optimum.  It is now read at the area the selection
    rule picked, and the comparator is N copies of the one unified HBM die the
    GPU side has always been built from.

    The test does NOT demand a tight area ratio, because a GPU cluster is
    quantised in whole dies and a ROM design is not: at N5 the B200 package is
    1,600 mm2 of silicon, so a 2,445 mm2 ROM machine has no exact partner and
    the honest comparator is two packages, 3,200 mm2 -- the ROM side compared
    against 31% MORE silicon than it has.  What is pinned instead is that the
    comparator is a whole number of one unchanging die AND that no other whole
    number would land closer, so the granularity is visible and never chosen.
    """

    _, results, _, _ = generated
    for study_id, result in results.items():
        gpu_area_per_device = {
            row["design"]: row["silicon_area_mm2_per_device"]
            for row in result["points"]
            if row["family"] == "gpu"
        }
        die_areas = set(gpu_area_per_device.values())
        assert len(die_areas) == 1, (
            f"{study_id}: the GPU side is built from more than one die area "
            f"{sorted(die_areas)}; the comparison is not N copies of one die"
        )
        die = die_areas.pop()
        for entry in result["design_selection"]["models"]:
            best = entry["recommended"]
            if not best.get("iso_area_gpu_design"):
                continue
            count = best["iso_area_gpu_device_count"]
            assert count == int(count) and count >= 1
            assert best["iso_area_gpu_silicon_area_mm2"] == pytest.approx(
                die * count, rel=1e-9
            ), (
                f"{study_id}: the GPU comparator for {entry['model']} is not N "
                "copies of one die"
            )
            rom_area = best["silicon_area_mm2"]
            nearest = min(
                range(1, 2 * int(rom_area // die) + 3),
                key=lambda n: (abs(die * n - rom_area), n),
            )
            assert abs(die * count - rom_area) <= abs(die * nearest - rom_area) + 1e-6, (
                f"{study_id}: {entry['model']} is compared against {count} dies "
                f"({die * count:,.0f} mm2) when {nearest} ({die * nearest:,.0f} "
                f"mm2) is closer to the ROM side's {rom_area:,.0f} mm2"
            )
            assert best["iso_area_ratio"] == pytest.approx(
                rom_area / best["iso_area_gpu_silicon_area_mm2"], rel=1e-9
            )


def test_a_regime_change_across_batch_is_reported_rather_than_averaged(
    generated,
) -> None:
    """Where the best design differs by batch, the study has to say so.

    The recommendation is recomputed at every studied batch, and the contiguous
    runs are published as regimes.  This pins that the regime list is a true
    partition of the batch grid -- a summary that dropped or duplicated a batch
    would let a reader believe one machine covers an operating point it was
    never evaluated at.
    """

    runner, results, _, _ = generated
    for study_id, result in results.items():
        for entry in result["design_selection"]["models"]:
            batches = [
                record["batch_size"] for record in entry["batch_regimes"]
            ]
            assert batches == list(runner.BATCHES)
            flattened: list[int] = []
            for regime in entry["regimes"]:
                flattened.extend(regime["batches"])
            assert flattened == list(runner.BATCHES), (
                f"{study_id}: {entry['model']}'s regime summary is not a "
                "partition of the batch grid"
            )
            assert entry["regime_count"] == len(entry["regimes"])
            assert entry["best_design_differs_by_batch"] == (
                entry["regime_count"] > 1
            )


# --------------------------------------------------------------------------
# the quantised variant
# --------------------------------------------------------------------------


def test_the_quantised_variant_is_written_and_is_byte_deterministic(
    generated,
) -> None:
    runner, _, first, second = generated
    root_a = runner.variant_output_root(first)
    root_b = runner.variant_output_root(second)
    for study_id in runner.STUDIES:
        for artifact in runner.VARIANT_ARTIFACTS:
            assert (root_a / study_id / artifact).exists()
            assert _digest(root_a / study_id / artifact) == _digest(
                root_b / study_id / artifact
            ), f"quantised_variant/{study_id}/{artifact} is not reproducible"
    assert not (root_a / "n6_vs_a100" / "sweep.csv").exists(), (
        "the variant must not ship a sweep.csv: there is no row on that page "
        "anyone should be pulling into a spreadsheet"
    )


def test_the_checked_in_quantised_variant_matches_the_runner(generated) -> None:
    runner, _, first, _ = generated
    for study_id in runner.STUDIES:
        for artifact in runner.VARIANT_ARTIFACTS:
            checked_in = runner.variant_output_root(CHECKED_IN) / study_id / artifact
            assert checked_in.exists(), f"missing checked-in {checked_in}"
            assert _digest(checked_in) == _digest(
                runner.variant_output_root(first) / study_id / artifact
            ), (
                f"results/roofline/quantised_variant/{study_id}/{artifact} is "
                "stale -- re-run `python3 tools/run_roofline_studies.py --force`"
            )


def _variants(runner, root: Path) -> dict[str, dict]:
    return {
        study_id: json.loads(
            (runner.variant_output_root(root) / study_id / "analytical.json").read_text(
                encoding="utf-8"
            )
        )
        for study_id in runner.STUDIES
    }


def test_the_quantisation_is_applied_to_both_sides_or_it_is_not_published(
    generated,
) -> None:
    """**The rule the variant exists to obey.**

    A quantisation is a property of the checkpoint, not of the machine reading
    it.  A GPU serving 4.25-bit weights reads 3.76x fewer weight bytes exactly as
    the mask-ROM part does, so a variant that quantised one side would be handing
    it a free halving of weight traffic -- the same asymmetry the released-packing
    rule already forbids in the primary studies, and the one this program records
    for an FP8 KV latent in the DeepSeek profile's ``kv_precision_sensitivity``.

    The check is per model and spans BOTH families: one stored width, or the
    variant is not iso-precision and must not be published.
    """

    runner, _, first, _ = generated
    for study_id, variant in _variants(runner, first).items():
        declared = float(variant["representation_variant"]["bits_per_parameter"])
        by_model: dict[str, set[float]] = {}
        families: dict[str, set[str]] = {}
        for design in variant["designs"]:
            bits = design.get("stored_bits_per_parameter")
            assert bits is not None, design["design"]
            by_model.setdefault(design["model"], set()).add(round(float(bits), 6))
            families.setdefault(design["model"], set()).add(design["family"])
        assert by_model, f"{study_id}: the variant produced no designs"
        for model, widths in by_model.items():
            assert widths == {round(declared, 6)}, (
                f"{study_id}: {model} is priced at {sorted(widths)} bits in the "
                f"variant, which declares {declared}. Both families must be held "
                "at one stored width or the variant is not iso-precision."
            )
            assert families[model] == {"rom", "gpu"}, (
                f"{study_id}: {model} is quantised on {sorted(families[model])} "
                "only -- a quantisation applies to both sides"
            )


def test_the_variant_says_plainly_that_nothing_has_been_executed_at_that_precision(
    generated,
) -> None:
    """It is a projection, and every reader has to hit that before a number."""

    runner, _, first, _ = generated
    for study_id, variant in _variants(runner, first).items():
        declared = variant["representation_variant"]
        assert declared["executed_tokens_at_this_precision"] == 0
        assert "PROJECTION, NOT A MEASUREMENT" in declared["status"]
        assert declared["accuracy"]
        assert declared["known_defect"]
        report = (
            runner.variant_output_root(first) / study_id / "REPORT.md"
        ).read_text(encoding="utf-8")
        head = report.split("## ", 1)[0]
        assert "SECONDARY" in head
        assert "PROJECTION, NOT A MEASUREMENT" in head
        assert "not the primary result" in head
        assert (
            "0 tokens have ever been produced at this precision" in head
        ), "the variant must state the executed-token count before any figure"
        for design in variant["designs"]:
            assert design["representation"] == "q4p25", (
                f"{study_id}: {design['design']} does not carry the variant tag, "
                "so a row of it could be pasted into the primary unnoticed"
            )


def test_the_variant_does_not_touch_the_primary_result(generated) -> None:
    """The primary studies must not know the variant exists.

    ``run_all`` returns the primary results only, the variant is written to its
    own directory, and no primary design carries the variant's representation.
    """

    runner, results, first, _ = generated
    assert set(results) == set(runner.STUDIES), (
        "run_all's return value is the set of primary studies; a secondary "
        "projection in that mapping is one loop away from being read as one"
    )
    for study_id, result in results.items():
        for design in result["designs"]:
            assert design["representation"] in {"native", "official_packed"}
        assert "representation_variant" not in result
    for study_id, variant in _variants(runner, first).items():
        assert variant["primary_study_id"] == study_id
        assert variant["study_id"] != study_id


def test_the_variant_prices_only_models_above_the_production_quantisation_floor(
    generated,
) -> None:
    """Scope, and the reason for it.

    Qwen3-8B ships at 16.00 bits and is above the width production GPU stacks
    already serve, so re-quantising it is a question a study can ask of both
    sides.  DeepSeek V4 Flash and Pro ship mixed FP8 dense plus MXFP4 routed at
    4.70 and 4.46 bits -- they are already at that floor, and re-quantising them
    would mean pushing the GPU BELOW what any production stack serves, which is
    the same one-sided offer in the other direction.
    """

    runner, results, first, _ = generated
    declared = float(runner.QUANTISED_VARIANT["bits_per_parameter"])
    native_bits = {
        summary["model"]: summary["native_bits_per_parameter"]
        for summary in results["n6_vs_a100"]["model_summaries"]
    }
    for study_id, variant in _variants(runner, first).items():
        priced = {design["model"] for design in variant["designs"]}
        assert priced == {"Qwen3-8B"}, (
            f"{study_id}: the variant prices {sorted(priced)}"
        )
        for model in priced:
            assert native_bits[model] > declared, (
                f"{model} ships at {native_bits[model]} bits, which is not above "
                f"the variant's {declared}"
            )


def test_the_variant_is_selected_by_the_same_rule_as_the_primary(generated) -> None:
    """One rule, two artifacts -- or the two cannot be read side by side."""

    runner, results, first, _ = generated
    for study_id, variant in _variants(runner, first).items():
        assert (
            variant["design_selection"]["metric"]
            == results[study_id]["design_selection"]["metric"]
        )
        assert (
            variant["design_selection"]["marginal_return_bar"]
            == results[study_id]["design_selection"]["marginal_return_bar"]
        )
        assert variant["consistency_audit"]["status"] == "pass"


def test_the_variant_report_never_quotes_a_ratio_without_the_primary_one(
    generated,
) -> None:
    """Both rows on the same table, so the pair is the only way to read it."""

    runner, _, first, _ = generated
    for study_id in runner.STUDIES:
        report = (
            runner.variant_output_root(first) / study_id / "REPORT.md"
        ).read_text(encoding="utf-8")
        assert "PRIMARY (BF16" in report
        assert "variant (4.25 bits, both sides)" in report


def test_capacity_feasibility_and_the_resident_count_use_one_tolerance(
    technology, qwen
) -> None:
    """A design declared feasible for one session must report room for one.

    Capacities are solved from areas through a chain of float multiplications,
    so a machine sized to hold exactly one session's KV lands a fraction of a
    byte short of it: the three-reticle Qwen design's SRAM comes out at
    1,207,959,551.9999998 B against a session needing 1,207,959,552.0 B.  The
    feasibility test has always carried a one-byte tolerance.  The resident
    count did not -- it floored an exact division, returned 0, and because 0 is
    falsy the pipeline-fill cap that reads it was skipped on exactly those
    machines.  The design was then published as feasible for one session AND as
    delivering the aggregate rate of as many sessions as it had pipeline stages.

    Both now read ``CAPACITY_TOLERANCE_BYTES``.  This test builds the shortfall
    directly rather than hunting for the design that happens to have it, so it
    keeps working when a technology input moves.
    """

    kv = kv_traffic(qwen, 8_192)
    per_user = kv.storage_bytes_per_user
    topology = _single_chip()
    density = technology.sram_bits_per_mm2("N6").value / 8.0
    # SRAM area that lands a hair UNDER one session, which is the case that broke.
    sram_mm2 = (per_user - 0.25) / density
    split = balanced_area_split(
        technology,
        node="N6",
        total_mm2=4_000.0,
        weight_store="rom",
        kv_store="sram",
        stored_weight_bytes=qwen.checkpoint_bytes,
        resident_kv_bytes=per_user,
    )
    budget = rom_device_budget(
        technology,
        name="tolerance-probe",
        node="N6",
        area_mm2_per_device=4_000.0,
        topology=topology,
        stored_weight_bytes=qwen.checkpoint_bytes,
        resident_kv_bytes=per_user,
        kv_store="sram",
        split=replace(split, sram_mm2=sram_mm2),
    )
    assert budget.kv_capacity_bytes < per_user, (
        "the probe is meant to sit just under one session; it does not"
    )
    step = evaluate(
        budget,
        qwen,
        context_tokens=8_192,
        batch_size=1,
        technology=technology,
    )
    assert step.feasible, step.reasons
    assert step.metrics["max_resident_users"] >= 1, (
        "a design the capacity test calls feasible for one session reports room "
        "for none; the two are not reading the same tolerance"
    )


def test_a_machine_that_holds_one_session_cannot_claim_a_pipeline_of_them(
    technology, qwen
) -> None:
    """The fill cap has to fire at a resident count of one, not only above it.

    ``if max_resident_users and fill_users > max_resident_users`` is falsy at
    zero, so the cap was skipped precisely where capacity was tightest.  With the
    tolerance fixed the count is one there, and one is truthy -- but the guard is
    now an explicit ``> 0`` so the behaviour does not depend on that coincidence.
    """

    kv = kv_traffic(qwen, 8_192)
    per_user = kv.storage_bytes_per_user
    topology = Topology(
        kind="array",
        device_count=3,
        parallelism="pipeline",
        link="infiniband_hdr",
        intra_link="nvlink3",
        intra_domain_size=8,
    )
    split = balanced_area_split(
        technology,
        node="N6",
        total_mm2=815.0,
        weight_store="rom",
        kv_store="sram",
        stored_weight_bytes=qwen.checkpoint_bytes / 3.0,
        resident_kv_bytes=per_user / 3.0,
    )
    budget = rom_device_budget(
        technology,
        name="one-session-pipeline",
        node="N6",
        area_mm2_per_device=815.0,
        topology=topology,
        stored_weight_bytes=qwen.checkpoint_bytes,
        resident_kv_bytes=per_user,
        kv_store="sram",
        split=split,
    )
    step = evaluate(
        budget,
        qwen,
        context_tokens=8_192,
        batch_size=1,
        technology=technology,
    )
    if not step.feasible:
        pytest.skip(f"probe design is infeasible for other reasons: {step.reasons}")
    resident = step.metrics["max_resident_users"]
    assert step.metrics["pipeline_fill_users"] <= max(1.0, float(resident)) + 1e-9, (
        "a three-stage pipeline that holds one session is claiming the aggregate "
        "rate of three"
    )
    assert step.aggregate_tokens_s == pytest.approx(
        step.metrics["pipeline_fill_users"] * step.per_user_tokens_s, rel=1e-9
    )
