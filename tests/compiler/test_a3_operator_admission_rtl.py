"""Focused checks for the six newly admitted ABI 3.0 operator families."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile

from tools import build_a3_operator_admission_vectors as admission
from tools import build_a3_operator_unit_vectors as units
from tools import run_a3_operator_admission_rtl_campaign as campaign


ROOT = Path(__file__).resolve().parents[2]
ADMISSION_ROOT = ROOT / "testdata/rtl/a3_operator_admission"
UNIT_ROOT = ROOT / "testdata/rtl/a3_operator_units"
RESULT = ROOT / "results/rtl/a3_operator_admission_campaign.json"

# The six families rtl/abi3/ot_a3_engine_issue_bridge.sv used to answer with
# TRAP_CAPABILITY, as (family, subopcode) pairs.
GOVERNED_FAMILIES = [
    {"family": 0x10, "sub": 0x03},  # DMA.SCATTER
    {"family": 0x30, "sub": 0x03},  # VECTOR.ADD
    {"family": 0x30, "sub": 0x04},  # VECTOR.SILU_MUL
    {"family": 0x40, "sub": 0x01},  # ATTENTION.GQA
    {"family": 0x70, "sub": 0x00},  # SELECTION.ARGMAX
    {"family": 0x70, "sub": 0x01},  # SELECTION.TOKEN_APPEND
]

# The families outside the six, issued by this campaign for the placement
# question rather than the admission one.  DMA.GATHER is here because its
# dense-row form was admitted only in FP32 until the source dtype was widened
# to the two codes the mover can carry; the rest were already admitted.
OBJECT_KEYED_FAMILIES = [
    {"family": 0x10, "sub": 0x02},  # DMA.GATHER
    {"family": 0x20, "sub": 0x00},  # TENSOR.MATMUL
    {"family": 0x30, "sub": 0x00},  # VECTOR.RMS_NORM
    {"family": 0x30, "sub": 0x01},  # VECTOR.HEAD_RMS_NORM
    {"family": 0x30, "sub": 0x02},  # VECTOR.ROPE
]


def test_vectors_are_byte_exact_and_source_current() -> None:
    with tempfile.TemporaryDirectory() as name:
        generated = Path(name)
        manifest = admission.build(generated / "admission")
        for filename in campaign.ADMISSION_FILES:
            assert (generated / "admission" / filename).read_bytes() == (
                ADMISSION_ROOT / filename
            ).read_bytes()
        unit_manifest = units.build(generated / "units")
        for filename in campaign.UNIT_FILES:
            assert (generated / "units" / filename).read_bytes() == (
                UNIT_ROOT / filename
            ).read_bytes()

    assert manifest["schema"] == admission.SCHEMA
    assert unit_manifest["schema"] == units.SCHEMA
    # The six are all there, and they are no longer all of it: the campaign
    # now also issues the four object-keyed families the bridge already
    # admitted, which is how it binds and resolves objects the six never name.
    for entry in GOVERNED_FAMILIES:
        assert entry in manifest["admitted_families"]
    assert [
        entry for entry in manifest["admitted_families"]
        if entry not in GOVERNED_FAMILIES
    ] == OBJECT_KEYED_FAMILIES
    # PC 1 joins the governed set with the dma_gather_rope_coefficient_row_select
    # case.  It is there so that ONE campaign drives both descriptors of the ROM
    # DMA.GATHER class: PCs 1 and 68 resolve to the same shape and merge into a
    # single class, G1a's rule is evaluated per campaign with no union across
    # campaigns, and before this the two descriptors were driven by two
    # different vehicles -- so the class was uncovered despite both being
    # exercised.  Closing it takes G1a from 11/15 to 12/15 on ROM.
    assert manifest["governed_program_counters"] == [
        1, 8, 14, 17, 20, 23, 26, 29, 32, 35, 38, 44, 47, 56, 62, 66, 68, 70, 72
    ]


def test_every_governed_family_has_a_positive_case_at_its_own_program_counter() -> None:
    manifest = json.loads((ADMISSION_ROOT / "index.json").read_text())
    positive = [item for item in manifest["cases"] if not item["expected"]["fault"]]
    covered = {(item["family"], item["sub"]) for item in positive}
    assert covered == {
        (entry["family"], entry["sub"])
        for entry in GOVERNED_FAMILIES + OBJECT_KEYED_FAMILIES
    }
    # The three decode positions the governed workload runs need contexts 17
    # and 19 to be expressible; a constant 17 made the later ones a refusal.
    attention = [item for item in positive if item["family"] == 0x40]
    assert sorted(item["context_length"] for item in attention) == [17, 19]
    scatters = [item for item in positive if item["family"] == 0x10]
    assert sorted({item["context_length"] for item in scatters}) == [17, 19]


def test_fail_closed_matrix_is_present_and_distinct() -> None:
    manifest = json.loads((ADMISSION_ROOT / "index.json").read_text())
    refusals = {
        item["name"]: item["expected"]
        for item in manifest["cases"]
        if item["expected"]["fault"]
    }
    assert len(refusals) == 10
    assert refusals["capability_refusal_vector_softmax"]["trap_class"] == 4
    assert refusals["descriptor_refusal_mutated_add_contract"]["trap_class"] == 3
    assert refusals["capability_refusal_unmapped_output_object"]["trap_class"] == 4
    # An instance that has not bound its operand banks keeps the exact
    # TRAP_CAPABILITY it gave before these families were implemented.
    assert refusals["capability_refusal_placement_not_configured"]["trap_class"] == 4
    assert (
        refusals["descriptor_refusal_gqa_context_disagrees_with_index"]["trap_class"]
        == 3
    )
    assert refusals["engine_refusal_token_outside_vocabulary"]["trap_class"] == 8
    assert refusals["capability_refusal_sampling_generation_policy"]["trap_class"] == 4
    # Three shipped instructions of the governed program that this bridge
    # does not admit at all.  They are measured rather than read out of the
    # source, because the objects these operators name can be resolved by no
    # run of this design.  They were four: PC 68's BF16 dense-row DMA.GATHER
    # is now a PASSING case, so a refusal record for it here would be a stale
    # assertion about a gap that is closed.
    for name in (
        "descriptor_refusal_mlp_gate_projection_weight_view",
        "descriptor_refusal_mlp_up_projection_weight_view",
        "descriptor_refusal_mlp_down_projection_weight_view",
    ):
        assert refusals[name]["trap_class"] == 3
    assert "descriptor_refusal_bf16_dense_row_gather" not in refusals
    passing = {item["name"] for item in manifest["cases"]
               if not item["expected"]["fault"]}
    assert "dma_gather_head_row_select" in passing
    assert "tensor_matmul_key_projection" in passing
    assert "tensor_matmul_value_projection" in passing
    for expected in refusals.values():
        assert expected["write_beats"] == 0


def test_unit_vectors_cover_the_contract_corners() -> None:
    manifest = json.loads((UNIT_ROOT / "index.json").read_text())
    silu = {item["name"]: item for item in manifest["silu_cases"]}
    assert silu["silu_mul_directed_and_seeded"]["expected_error"] == 0
    assert silu["silu_mul_directed_and_seeded"]["expected_saturations"] >= 1
    assert silu["silu_mul_nonfinite_gate"]["expected_error"] == 1
    assert silu["silu_mul_nonfinite_up"]["expected_error"] == 1
    assert silu["silu_mul_gated_product_range"]["expected_error"] == 2
    assert silu["silu_mul_degenerate_count"]["expected_error"] == 7
    # The gated-product refusal must be caught between the two multiplies of
    # its element, which the work count is the only witness to.
    assert silu["silu_mul_gated_product_range"]["expected_work_count"] == 5

    append = {item["name"]: item for item in manifest["append_cases"]}
    assert append["token_append_eos_beats_length_stop"]["expected_eos"] == 1
    assert append["token_append_length_stop"]["expected_eos"] == 2
    assert append["token_append_outside_vocabulary"]["expected_error"] == 4
    assert append["token_append_sampling_policy"]["expected_capability"] is True
    assert append["token_append_sampling_policy"]["expected_reads"] == 0
    for name in (
        "token_append_sampling_policy",
        "token_append_request_bound_zero",
        "token_append_request_above_policy",
        "token_append_eos_count_above_abi_bound",
        "token_append_empty_vocabulary",
        "token_append_outside_vocabulary",
    ):
        assert append[name]["expected_out_count"] == 0
        assert append[name]["expected_appended"] == 0


def test_retained_dual_simulator_campaign_is_source_current() -> None:
    assert campaign.validate_retained(RESULT) == []
    result = json.loads(RESULT.read_text())
    assert result["status"] == "pass"
    assert result["simulators_agree"]
    assert (
        result["admission"]["previously_capability_trapped_families_admitted"]
        == GOVERNED_FAMILIES
    )
    assert result["admission"]["previously_capability_trapped_family_count"] == 6
    assert result["admission"]["object_keyed_families_also_issued"] == (
        OBJECT_KEYED_FAMILIES
    )
    assert result["admission"]["capability_trapped_family_count"] == 0
    assert result["contexts_covered"] == [17, 19]
    aggregate = result["aggregate"]
    assert aggregate["admission_case_count"] == 33
    assert aggregate["admission_positive_case_count"] == 23
    assert aggregate["admission_negative_case_count"] == 10
    assert aggregate["admission_words_compared"] == 62_213
    assert aggregate["silu_elements_compared"] == 1_217
    assert aggregate["append_case_count"] == 13
    scope = result["scope"]
    assert scope["bit_exact_against_independent_reference"]
    assert scope["six_previously_capability_trapped_families_admitted"]
    assert scope["read_modify_write_placement"]
    assert scope["fail_closed_matrix"]
    assert scope["model_token_generation"] is False
    assert scope["tpot"] is False
    # Two of the layer's seven projections are issued, on the checkpoint's
    # own layer-zero k_proj and v_proj; five are not, so the boolean stays
    # false and the count carries the fact.
    assert scope["layer_matmuls_issued"] is False
    assert scope["layer_matmuls_issued_count"] == 2
    assert scope["layer_matmul_count"] == 7
    assert scope["real_checkpoint_projection_weights"] is True


def test_the_placement_depth_is_measured_and_not_declared() -> None:
    """What the campaign publishes about the bridge's one object table.

    The number that matters to G1a and G1b is how many distinct objects ONE
    binding of that table held while the design resolved every one of them.
    Three things make it a measurement rather than a declaration, and each is
    checked here: it counts only objects some case's operands actually named,
    it counts only cases the simulators reported as issued with no fault and
    whose whole result region was compared, and it can never exceed the table
    the run bound.
    """

    result = json.loads(RESULT.read_text())
    manifest = json.loads((ADMISSION_ROOT / "index.json").read_text())
    placement = result["placement"]
    by_name = {item["name"]: item for item in manifest["cases"]}

    resolved = placement["objects_resolved_and_compared"]
    bound = placement["objects_bound"]
    assert placement["measured_simultaneous_objects"] == len(resolved)
    assert set(resolved) <= set(bound)
    assert placement["table_entries_bound"] == len(bound)
    assert placement["measured_simultaneous_objects"] <= placement[
        "vector_format_entries"
    ]
    assert placement["bridge"] == "rtl/abi3/ot_a3_engine_issue_bridge.sv"

    credited = placement["cases_credited"]
    assert credited, "a measurement with no case behind it is not a measurement"
    named: set[int] = set()
    for name in credited:
        case = by_name[name]
        assert case["expected"]["fault"] is False
        assert case["placement_valid"] is True
        assert case["expected"]["compare_count"] > 0
        # Every credited case ran under the SAME table, or "simultaneous"
        # would mean nothing.
        assert case["object_map"] == by_name[credited[0]]["object_map"]
        named |= {int(value) for value in case["objects_named"]}
    assert sorted(named & set(bound)) == resolved

    # A refused case binds the table and resolves nothing out of it, which is
    # the distinction the whole field turns on.
    for name, case in by_name.items():
        if case["expected"]["fault"]:
            assert name not in credited
