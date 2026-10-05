"""Rung G1d's derivation must emit the RTL's token, or none at all.

The cheapest way to make a token gate green is to write the oracle's ids into
the record and compare them with themselves.  That is the exact defect this
programme exists to remove, so the first tests here are about where
``record_token_ids`` comes from and what happens when nothing emitted one.

The rest are about the head: that it is found in the program rather than
listed here, that its arithmetic and its shard plan are derived from the
descriptor's own extents, that a probe which merely dispatched a head operator
cannot turn a field true, and that the shard plan's exactness claim is checked
by something that could have failed.
"""

from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools/build_abi3_g1d_token.py"
ORACLE = ROOT / "results/abi3/qwen3_reference_oracle_eos.json"
VECTORS = ROOT / "testdata/compiler/abi3_shipped_prefix/abi3_shipped_prefix_vectors.json"


def _load():
    spec = importlib.util.spec_from_file_location("_g1d_tool", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def tool():
    return _load()


@pytest.fixture(scope="module")
def artifact(tool, tmp_path_factory):
    out = tmp_path_factory.mktemp("g1d") / "artifact.json"
    return tool.build(out, None, None, None, tool.SHARD_COUNT, False)


def _record(artifact, storage_class):
    return next(
        r for r in artifact["records"] if r["storage_class"] == storage_class
    )


@pytest.fixture(scope="module")
def context(tool):
    vectors = json.loads(VECTORS.read_text())
    key, directory = tool._g1c.STORAGE_CLASSES["rom"]
    case = next(c for c in vectors["cases"] if c["deployment"] == key)
    kernels = tool._g1b.kernel_index(case)
    facts = tool._g1c.ProgramFacts(ROOT / directory)
    loop = tool._g1c.layer_loop(facts, kernels)
    head = tool.head_operators(facts, loop, kernels)
    roles = tool.role_sites(head)
    return {"facts": facts, "loop": loop, "head": head, "roles": roles}


# --------------------------------------------------------------------------
# The token is the RTL's, or the record has none.
# --------------------------------------------------------------------------
@pytest.mark.parametrize("storage_class", ["rom", "hbm"])
def test_the_record_carries_no_token_because_none_was_emitted(
    artifact, storage_class
):
    record = _record(artifact, storage_class)
    assert record["record_token_ids"] == []
    assert record["oracle"]["agreement"] is False
    assert record["record_token_ids"] != record["oracle"]["generated_token_ids"]


def test_the_oracles_ids_are_not_written_into_the_tool(tool):
    """A literal oracle id in the derivation is a self-fulfilling comparison."""
    ids = set(tool._dig(json.loads(ORACLE.read_text()), tool.ORACLE_TOKEN_FIELD))
    literals = {
        node.value
        for node in ast.walk(ast.parse(TOOL.read_text()))
        if isinstance(node, ast.Constant) and isinstance(node.value, int)
    }
    assert not (ids & literals), (
        f"the tool carries the oracle's token id(s) {sorted(ids & literals)} "
        "as literals; the emitted ids must come from the RTL and the expected "
        "ids from the oracle file"
    )


def test_the_oracle_is_read_from_the_declared_field(tool):
    oracle = tool.oracle_evidence()
    body = json.loads(ORACLE.read_text())
    assert oracle["generated_token_ids"] == tool._dig(
        body, tool.ORACLE_TOKEN_FIELD
    )[: tool.ORACLE_TOKEN_COUNT]
    assert oracle["artifact_sha256"] == tool.sha256_file(ORACLE)


# --------------------------------------------------------------------------
# The head is found in the program, and its arithmetic is the descriptor's.
# --------------------------------------------------------------------------
def test_the_head_is_everything_after_the_layer_loop(context):
    head, loop = context["head"], context["loop"]
    assert head, "the program issues nothing after the loop"
    assert min(site["pc"] for site in head) > loop["back_edge_pc"]
    kinds = {site["kernel_kind"] for site in head}
    assert {"RMS_NORM", "VOCAB_PROJECT", "ARGMAX"} <= kinds


def test_each_named_field_binds_to_exactly_one_site(context):
    roles = context["roles"]
    assert set(roles) == set(_load().HEAD_ROLES)
    assert len({site["pc"] for site in roles.values()}) == 3
    assert roles["lm_head"]["kernel_kind"] == "VOCAB_PROJECT"
    assert roles["argmax"]["kernel_kind"] == "ARGMAX"


def test_the_head_arithmetic_is_derived_from_the_weight_view(tool, context):
    arithmetic = tool.lm_head_arithmetic(context["roles"]["lm_head"])
    assert arithmetic["mac_count"] == (
        arithmetic["output_rows"] * arithmetic["reduction"]
    )
    assert arithmetic["mac_count"] > 0
    literals = {
        node.value
        for node in ast.walk(ast.parse(TOOL.read_text()))
        if isinstance(node, ast.Constant) and isinstance(node.value, int)
    }
    for value in (
        arithmetic["mac_count"],
        arithmetic["output_rows"],
        arithmetic["reduction"],
    ):
        assert value not in literals, (
            f"{value} is written into the tool as a literal; the head's shape "
            "must come from its own TENSOR_VIEW descriptor"
        )


def test_the_shard_plan_partitions_the_output_axis_exactly(tool, context):
    arithmetic = tool.lm_head_arithmetic(context["roles"]["lm_head"])
    plan = tool.shard_plan(arithmetic, tool.SHARD_COUNT)
    assert plan["sharded_axis"] == "output"
    assert plan["reduction_axis_is_partitioned"] is False
    assert plan["remainder_rows"] == 0
    assert plan["ranges_are_disjoint_and_contiguous"] is True
    assert plan["ranges_cover_the_axis_exactly"] is True
    assert plan["structurally_exact"] is True
    assert sum(r["rows"] for r in plan["ranges"]) == arithmetic["output_rows"]
    assert plan["ranges"][0]["start_row"] == 0
    assert plan["ranges"][-1]["stop_row_exclusive"] == arithmetic["output_rows"]


def test_a_shard_count_that_does_not_divide_is_not_exact(tool, context):
    arithmetic = tool.lm_head_arithmetic(context["roles"]["lm_head"])
    plan = tool.shard_plan(arithmetic, 7)
    assert plan["remainder_rows"] != 0
    assert plan["ranges_cover_the_axis_exactly"] is False
    assert plan["structurally_exact"] is False


# --------------------------------------------------------------------------
# Absence of evidence is a failure, never a zero.
# --------------------------------------------------------------------------
@pytest.mark.parametrize("storage_class", ["rom", "hbm"])
def test_the_logit_comparison_is_null_not_zero(artifact, storage_class):
    head = _record(artifact, storage_class)["head"]
    assert head["compared_logits"] == 0
    assert head["mismatched_logits"] is None, (
        "zero mismatched logits over zero compared logits is not evidence"
    )
    assert head["final_norm_in_rtl"] is False
    assert head["lm_head_in_rtl"] is False
    assert head["argmax_in_rtl"] is False


@pytest.mark.parametrize("storage_class", ["rom", "hbm"])
def test_no_head_instruction_was_fetched(artifact, storage_class):
    execution = _record(artifact, storage_class)["head"]["execution_measured"]
    assert execution["head_sites_fetched"] == 0
    assert execution["head_site_count"] >= 3
    assert all(
        site["fetched_by_the_integrated_run"] is False
        for site in execution["head_sites"]
    )


@pytest.mark.parametrize("storage_class", ["rom", "hbm"])
def test_a_probe_dispatch_cannot_turn_a_field_true(artifact, storage_class):
    """The final norm did dispatch under a mid-program entry.  It stays red."""
    record = _record(artifact, storage_class)
    probe = record["head"]["entry_probe_observation"]
    if not probe.get("present"):
        pytest.skip("the entry probe artifact is not in this tree")
    assert record["head"]["final_norm_in_rtl"] is False
    assert probe["why_it_does_not_make_a_field_true"]


def test_an_absent_campaign_still_reports_the_head_unrun(tool, tmp_path):
    summary = tool.build(
        tmp_path / "g1d.json", tmp_path / "nothing.json", None, None,
        tool.SHARD_COUNT, False,
    )
    for record in summary["records"]:
        assert record["head"]["mismatched_logits"] is None
        assert record["record_token_ids"] == []
        assert record["head"]["execution_measured"]["head_sites_fetched"] == 0


def test_a_head_site_the_run_did_reach_is_reported_as_reached(tool, context):
    """The red is a measurement: a run that fetched the head says so."""
    vectors = json.loads(VECTORS.read_text())
    key, _ = tool._g1c.STORAGE_CLASSES["rom"]
    case = next(c for c in vectors["cases"] if c["deployment"] == key)
    index = vectors["cases"].index(case)
    campaign = {
        "observed_cases": [
            {
                "index": index,
                "fetched": len(context["facts"].instructions),
                "fault": -1,
                "trap": 0,
            }
        ],
        "expected_cases": [],
        "operator_admission": {"trapped_families": [], "launches": {}},
    }
    execution = tool.head_execution(
        campaign, context["head"], context["roles"], case, index
    )
    assert execution["head_sites_fetched"] == execution["head_site_count"]
    assert all(
        site["fetched_by_the_integrated_run"] for site in execution["head_sites"]
    )


# --------------------------------------------------------------------------
# The shard-composition claim rests on a property that can be falsified.
# --------------------------------------------------------------------------
def test_a_row_split_is_exact_and_a_reduction_split_is_not():
    """The claim the shard plan makes, on a case engineered to expose it.

    Under ``bf16_bf16_fp32_sequential_rne_v1`` the reduction association is
    fixed in ascending index and does not depend on the operand's shape, so
    splitting the OUTPUT rows cannot move a bit.  Splitting the REDUCTION axis
    re-associates the sum, and here it does: the whole reduction cancels to
    zero while the two halves cancel to one.  Without that second half the
    first would be proving nothing.
    """
    import numpy as np
    from runtime.sim.backend import CONTRACT_SEQUENTIAL, NumpyBackend

    backend = NumpyBackend()
    big = np.float32(2.0) ** 24
    weights = np.array(
        [
            [big, 1.0, 1.0, -big],
            [1.0, 1.0, 1.0, 1.0],
            [big, -big, 1.0, 1.0],
            [2.0, 2.0, 2.0, 2.0],
        ],
        dtype=np.float32,
    )
    activation = np.ones((1, 4), dtype=np.float32)

    whole = backend.matmul_binary32(activation, weights, contract=CONTRACT_SEQUENTIAL)
    rows = np.concatenate(
        [
            backend.matmul_binary32(
                activation, weights[start:start + 1], contract=CONTRACT_SEQUENTIAL
            )
            for start in range(weights.shape[0])
        ],
        axis=1,
    )
    assert np.array_equal(
        np.ascontiguousarray(whole, dtype=np.float32).view(np.uint32),
        np.ascontiguousarray(rows, dtype=np.float32).view(np.uint32),
    ), "splitting the output rows changed a bit under a fixed association"

    half = weights.shape[1] // 2
    split = backend.matmul_binary32(
        activation[:, :half], weights[:, :half], contract=CONTRACT_SEQUENTIAL
    ) + backend.matmul_binary32(
        activation[:, half:], weights[:, half:], contract=CONTRACT_SEQUENTIAL
    )
    assert not np.array_equal(whole, split), (
        "the reduction split reproduced the whole, so this comparison could "
        "not have detected a plan that partitioned the reduction axis"
    )


def test_the_recorded_shard_check_carries_a_control_that_had_teeth():
    """The artifact must not claim exactness from a comparison that cannot fail."""
    artifact = ROOT / "results/rtl/abi3_g1d_token.json"
    if not artifact.is_file():
        pytest.skip("the G1d artifact has not been built in this tree")
    body = json.loads(artifact.read_text())
    for record in body["records"]:
        check = record["head"]["shard_composition_check"]
        if not check.get("ran"):
            continue
        assert check["falsification_control_has_teeth"] is True, (
            "the reduction-split control agreed with the whole, so the row "
            "shard agreement establishes nothing"
        )
        for contract, result in check["by_contract"].items():
            assert result["per_activation"], contract
            assert all(
                row["compared_logits"] > 0 for row in result["per_activation"]
            ), f"{contract} compared no logit at all"
