"""Fail-closed tests for the three DeepSeek-V4.1-Flash comparison contracts.

WP-N of ``docs/DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md`` section 13, under
gate DS41-CMP11.  The contracts are pair identities, not results: no V4.1 token
has been produced in this repository, so every target lock and the Kernel IR
binding are ``pending`` here.  What these tests prove is that the documents say
exactly that, that the area arithmetic they publish is the arithmetic of their
own recorded factors, and that each governance rule bites when it is violated.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tools.abi3_comparison_boundary import (
    CONTRACT_PATHS,
    CONTRACT_SCHEMA_PATH,
    CONTRACT_SCHEMA_PATH_V2,
    CONTRACT_SCHEMA_V2,
    ORACLE_PRODUCER_PATHS,
    contract_schema_path,
    validate_comparison_contract,
)

ROOT = Path(__file__).resolve().parents[1]

WAFER_HBM = "deepseek_v41_rom_wafer_2_vs_hbm_cluster"
ARRAY_HBM = "deepseek_v41_rom_array_51_vs_hbm_cluster"
WAFER_ARRAY = "deepseek_v41_rom_wafer_2_vs_rom_array_51"
V41_IDS = (WAFER_HBM, ARRAY_HBM, WAFER_ARRAY)

#: The paths plan section 13 WP-N names, verbatim.
PLANNED_PATHS = {
    WAFER_HBM: (
        "configs/abi3/comparison_contracts/"
        "deepseek_v41_rom_wafer_2_vs_hbm_cluster_v1.json"
    ),
    ARRAY_HBM: (
        "configs/abi3/comparison_contracts/"
        "deepseek_v41_rom_array_51_vs_hbm_cluster_v1.json"
    ),
    WAFER_ARRAY: (
        "configs/abi3/comparison_contracts/"
        "deepseek_v41_rom_wafer_2_vs_rom_array_51_v1.json"
    ),
}

#: Published die areas, read from configs/hardware/technology.json, never typed
#: in from a document.
TECHNOLOGY = json.loads((ROOT / "configs/hardware/technology.json").read_text())
WAFER_MM2 = TECHNOLOGY["wafer"]["area_mm2"]["value"]
RETICLE_MM2 = TECHNOLOGY["reticle"]["area_mm2"]["value"]
WAFER_NODES = 2
#: The node count the array backend derives, which is NOT the plan's 51-node
#: design point: 384 routed experts per layer must divide by the node count for
#: whole-expert ownership and 384 % 51 = 27, so 51 is inadmissible under plan
#: section 3.2's own rule.  The contracts keep the plan's file names because
#: plan section 13 WP-N registers those paths.
ARRAY_NODES = 64
PLAN_ARRAY_NODES = 51

#: The V4 contracts, which v2 must not disturb.
V1_IDS = (
    "qwen3_rom_single_chip_vs_hbm_single_chip",
    "deepseek_v4_rom_wafer_vs_hbm_cluster_32",
    "deepseek_v4_rom_wafer_vs_rom_array_32",
)


def _load(comparison_id: str) -> dict:
    return json.loads((ROOT / CONTRACT_PATHS[comparison_id]).read_text())


def _validate(comparison_id: str, body: dict) -> dict:
    return validate_comparison_contract(
        body, repo=ROOT, source_path=ROOT / CONTRACT_PATHS[comparison_id]
    )


def _check(comparison_id: str, body: dict, name: str) -> bool:
    return _validate(comparison_id, body)["checks"][name]


@pytest.mark.parametrize("comparison_id", V41_IDS)
def test_registered_at_the_path_the_plan_names(comparison_id: str) -> None:
    assert CONTRACT_PATHS[comparison_id] == PLANNED_PATHS[comparison_id]
    assert (ROOT / PLANNED_PATHS[comparison_id]).is_file()
    assert ORACLE_PRODUCER_PATHS[comparison_id] == (
        "tools/run_deepseek_v41_reference_oracle.py"
    )


@pytest.mark.parametrize("comparison_id", V41_IDS)
def test_validates_against_the_v2_schema(comparison_id: str) -> None:
    body = _load(comparison_id)
    assert body["schema"] == CONTRACT_SCHEMA_V2
    assert contract_schema_path(body) == CONTRACT_SCHEMA_PATH_V2
    schema = json.loads(CONTRACT_SCHEMA_PATH_V2.read_text())
    Draft202012Validator.check_schema(schema)
    assert sorted(
        error.message for error in Draft202012Validator(schema).iter_errors(body)
    ) == []
    assert _validate(comparison_id, body)["schema_errors"] == []


@pytest.mark.parametrize("comparison_id", V1_IDS)
def test_v1_contracts_are_untouched_by_v2(comparison_id: str) -> None:
    """v2 is additive: a v1 contract still resolves to, and passes, v1."""

    body = _load(comparison_id)
    assert body["schema"] == "opentallas.abi3.comparison_contract.v1"
    assert contract_schema_path(body) == CONTRACT_SCHEMA_PATH
    validation = _validate(comparison_id, body)
    assert validation["schema_errors"] == []
    assert validation["valid"] is True
    # None of the v2-only governance keys leaks into a v1 validation result.
    assert not [
        name
        for name in validation["checks"]
        if name.startswith(("iso_area_", "reporting_", "model_binding_"))
    ]


#: The document WP-D emits, and the one every V4.1 contract names as the source
#: of its model lock.  A host without the 510 GB checkpoint has no copy of it, so
#: the identity checks below are asserted against its presence rather than
#: against a claim that it is always there.
_V41_IR = ROOT / "build" / "ir-v3" / "deepseek-v4.1-flash" / "kernel_ir.v3.json"


@pytest.mark.parametrize("comparison_id", V41_IDS)
def test_nothing_is_promoted_past_its_evidence_class(comparison_id: str) -> None:
    """Every lock in a V4.1 contract is pending, and it says why."""

    body = _load(comparison_id)
    assert body["model"]["status"] == "pending"
    assert body["model"]["graph_id"] is None
    assert body["model"]["kernel_ir_source_sha256"] is None
    assert "does not" in body["model"]["pending_reason"]
    assert body["external_oracle"]["status"] == "pending"
    for target in body["targets"].values():
        for label in ("deployment", "capability"):
            assert target[label]["status"] == "pending"
            assert target[label]["digest"] is None
            assert target[label]["source_sha256"] is None
        assert target["cost_policy"]["lock"]["status"] == "pending"
    validation = _validate(comparison_id, body)
    assert validation["ready"] is False
    assert validation["checks"]["model_binding_status_consistent"] is True
    # The IR-derived checks report the literal truth, and that truth has moved:
    # WP-D now emits ``build/ir-v3/deepseek-v4.1-flash/kernel_ir.v3.json``, so the
    # two identities this contract already states -- the model id and the numeric
    # profile -- are confronted with the document and agree.  The two that need a
    # *lock* are still unbound, because binding a graph_id and a source digest is
    # WP-N (DS41-CMP11) and carries its own registration; the contract's
    # ``pending_reason`` still says the IR does not exist, which is the next thing
    # that work package corrects.
    for name in ("model_id_source_exact", "numeric_profile_source_exact"):
        assert validation["checks"][name] is _V41_IR.is_file(), name
    for name in ("graph_id_source_exact", "kernel_ir_source_sha256_exact"):
        assert validation["checks"][name] is False, name


@pytest.mark.parametrize("comparison_id", V41_IDS)
def test_workload_binding_matches_the_committed_pins(comparison_id: str) -> None:
    """The mandatory 200,000-token workload, bound to WP-I's own pin file."""

    pins = json.loads(
        (ROOT / "results/abi3/deepseek_v41_workload_pins.json").read_text()
    )
    entry = pins["workloads"]["TA-DS41-CTX-200K-1"]
    workload = _load(comparison_id)["workload"]
    assert workload["workload_id"] == "TA-DS41-CTX-200K-1"
    assert workload["digest"] == entry["digest"]
    assert workload["rendered_text_sha256"] == entry["rendered_text_sha256"]
    assert workload["prompt_token_count"] == entry["prompt_token_count"] == 200000
    assert workload["max_new_tokens"] == entry["max_new_tokens"]
    assert workload["kind"] == entry["kind"]
    assert workload["tokenizer_sha256"] == (
        pins["tokenizer"]["source"]["tokenizer_sha256"]
    )
    validation = _validate(comparison_id, body=_load(comparison_id))
    for name in (
        "workload_digest_self_consistent",
        "workload_digest_source_exact",
        "workload_source_sha256_exact",
        "workload_index_source_sha256_exact",
        "workload_index_entry_exact",
        "tokenizer_identity_exact",
        "execution_context_exact",
    ):
        assert validation["checks"][name] is True, name


@pytest.mark.parametrize("comparison_id", V41_IDS)
def test_side_areas_are_the_product_of_their_own_factors(
    comparison_id: str,
) -> None:
    body = _load(comparison_id)
    for target in body["targets"].values():
        silicon = target["silicon"]
        if silicon["die_area_mm2_per_node"] is None or target["node_count"] is None:
            assert silicon["silicon_area_mm2"] is None
            continue
        assert silicon["silicon_area_mm2"] == (
            silicon["die_area_mm2_per_node"] * target["node_count"]
        )
    assert _check(comparison_id, body, "iso_area_side_arithmetic_exact") is True


def test_wafer_pair_and_array_areas_come_from_technology_json() -> None:
    body = _load(WAFER_ARRAY)
    rom = body["targets"]["rom"]
    array = body["targets"]["rom_array"]
    assert rom["node_class"] == "WAFER" and rom["node_count"] == WAFER_NODES
    assert rom["silicon"]["die_area_mm2_per_node"] == WAFER_MM2
    assert rom["silicon"]["silicon_area_mm2"] == WAFER_NODES * WAFER_MM2
    assert array["node_class"] == "DIE" and array["node_count"] == ARRAY_NODES
    assert array["silicon"]["die_area_mm2_per_node"] == RETICLE_MM2
    assert array["silicon"]["silicon_area_mm2"] == ARRAY_NODES * RETICLE_MM2
    # The two-wafer pipeline is WAFER_LOGICAL_DEVICE with two wafer-class nodes:
    # one deployment, one session, one submission, which is the geometry
    # configs/hardware/abi3_capability/rom_deepseek_v41_wafer.json declares and
    # runtime/abi3/capability.py admits.  The array is a CLUSTER_N, and at 64
    # nodes it is not a CLUSTER_32.
    assert rom["topology_class"] == 2
    assert array["topology_class"] == 3
    assert array["node_count"] != 32


def test_the_array_node_count_is_derived_and_records_the_plans_number() -> None:
    """384 % 51 = 27, so the plan's design point cannot own whole experts."""

    array = _load(WAFER_ARRAY)["targets"]["rom_array"]
    derivation = array["node_count_derivation"]
    assert derivation["fixed_by_work_package"] == "WP-F"
    assert derivation["fixed_by_gate"] == "DS41-P3"
    assert 384 % PLAN_ARRAY_NODES != 0
    assert 384 % ARRAY_NODES == 0
    assert any(str(384 % PLAN_ARRAY_NODES) in line for line in derivation["inputs"])
    assert any(str(PLAN_ARRAY_NODES) in line for line in derivation["inputs"])
    # The identifier keeps the plan's name; the geometry is the field.
    assert "51" in WAFER_ARRAY
    assert array["target_id"].endswith(str(ARRAY_NODES))


def test_the_wafer_pair_records_why_it_is_class_two() -> None:
    derivation = _load(WAFER_ARRAY)["targets"]["rom"]["node_count_derivation"]
    assert derivation["fixed_by_work_package"] == "WP-E"
    assert "CLUSTER_N" in derivation["rule"]
    assert "one submission" in derivation["rule"]
    assert any("max_nodes 2" in line for line in derivation["inputs"])


def test_packaging_pair_ratio_is_locked_out_of_tolerance_and_corrected() -> None:
    body = _load(WAFER_ARRAY)
    iso = body["iso_area"]
    expected = (ARRAY_NODES * RETICLE_MM2) / (WAFER_NODES * WAFER_MM2)
    assert iso["status"] == "locked"
    assert iso["tolerance"] == 0.02
    assert iso["ratio"] == expected
    assert iso["within_tolerance"] is False
    assert abs(expected - 1.0) > iso["tolerance"]

    correction = iso["granularity_correction"]
    assert correction["corrected_role"] == "rom_array"
    assert correction["quantum_mm2"] == RETICLE_MM2
    assert correction["built"] is False
    counts = [entry["node_count"] for entry in correction["admissible_node_counts"]]
    independent = [
        count
        for count in range(1, 400)
        if abs(count * RETICLE_MM2 / (WAFER_NODES * WAFER_MM2) - 1.0) <= iso["tolerance"]
    ]
    assert counts == independent
    assert correction["nearest_node_count"] == min(
        independent, key=lambda n: abs(n * RETICLE_MM2 / (WAFER_NODES * WAFER_MM2) - 1.0)
    )
    assert correction["nearest_node_count"] not in (PLAN_ARRAY_NODES, ARRAY_NODES)
    # The verdict is invariant across both candidate array counts, which is what
    # makes the packaging reading safe while WP-F's derivation is in flight.
    plan_ratio = PLAN_ARRAY_NODES * RETICLE_MM2 / (WAFER_NODES * WAFER_MM2)
    assert abs(plan_ratio - 1.0) > iso["tolerance"]
    assert repr(plan_ratio) in correction["what_the_built_pair_is"]
    for name in (
        "iso_area_ratio_exact",
        "iso_area_verdict_exact",
        "iso_area_correction_exact",
    ):
        assert _check(WAFER_ARRAY, body, name) is True, name


@pytest.mark.parametrize("comparison_id", (WAFER_HBM, ARRAY_HBM))
def test_hbm_pairs_publish_no_ratio_because_the_denominator_is_absent(
    comparison_id: str,
) -> None:
    body = _load(comparison_id)
    iso = body["iso_area"]
    assert iso["status"] == "pending"
    assert iso["ratio"] is None
    assert iso["within_tolerance"] is None
    assert iso["granularity_correction"] is None
    hbm = body["targets"]["hbm"]
    assert hbm["node_count"] is None
    assert hbm["silicon"]["die_area_grade"] == "unavailable"
    assert hbm["silicon"]["die_area_mm2_per_node"] is None
    assert hbm["silicon"]["silicon_area_mm2"] is None
    derivation = hbm["node_count_derivation"]
    assert derivation["fixed_by_work_package"] == "WP-G"
    assert derivation["fixed_by_gate"] == "DS41-P3"
    assert derivation["inputs"] and derivation["rule"]
    assert _check(comparison_id, body, "iso_area_ratio_exact") is True
    assert _check(comparison_id, body, "contract_integer_fields_strict") is True


@pytest.mark.parametrize("comparison_id", V41_IDS)
def test_each_published_ratio_declares_both_companions(
    comparison_id: str,
) -> None:
    reporting = _load(comparison_id)["reporting"]
    assert reporting["gate_id"] == "DS41-CMP11"
    assert reporting["required_companions"] == [
        "binding_constraint",
        "resident_session_count",
    ]
    assert set(reporting["companion_sources"]) == set(
        reporting["required_companions"]
    )
    for companion in reporting["companion_sources"].values():
        assert companion["per_role"] is True
        assert companion["evidence_class"] == "executed_comparison_artifact"
        assert companion["analytical_antecedent"]
    assert reporting["published_ratios"]


# --------------------------------------------------------------------------
# Every governance rule bites.


def test_a_forged_ratio_is_refused() -> None:
    body = _load(WAFER_ARRAY)
    body["iso_area"]["ratio"] = 1.0
    assert _check(WAFER_ARRAY, body, "iso_area_ratio_exact") is False


def test_a_flattered_verdict_is_refused() -> None:
    body = _load(WAFER_ARRAY)
    body["iso_area"]["within_tolerance"] = True
    assert _check(WAFER_ARRAY, body, "iso_area_verdict_exact") is False


def test_an_out_of_tolerance_pair_may_not_drop_its_correction() -> None:
    body = _load(WAFER_ARRAY)
    body["iso_area"]["granularity_correction"] = None
    assert _check(WAFER_ARRAY, body, "iso_area_correction_exact") is False
    schema = json.loads(CONTRACT_SCHEMA_PATH_V2.read_text())
    assert list(Draft202012Validator(schema).iter_errors(body))


def test_a_correction_whose_counts_are_outside_tolerance_is_refused() -> None:
    body = _load(WAFER_ARRAY)
    correction = body["iso_area"]["granularity_correction"]
    correction["admissible_node_counts"].append(
        {
            "node_count": ARRAY_NODES,
            "ratio_to_denominator": ARRAY_NODES * RETICLE_MM2 / (WAFER_NODES * WAFER_MM2),
            "silicon_area_mm2": ARRAY_NODES * RETICLE_MM2,
        }
    )
    assert _check(WAFER_ARRAY, body, "iso_area_correction_exact") is False


def test_a_correction_is_checked_even_while_the_ratio_is_pending() -> None:
    """Its content depends on the denominator alone, so it is always checkable."""

    body = _load(WAFER_HBM)
    correction = dict(_load(WAFER_ARRAY)["iso_area"]["granularity_correction"])
    # The corrected side of THIS pair is the hbm slot, not the rom_array slot.
    correction["corrected_role"] = "hbm"
    body["iso_area"]["granularity_correction"] = correction
    assert _check(WAFER_HBM, body, "iso_area_correction_exact") is True
    correction["nearest_node_count"] = 999
    assert _check(WAFER_HBM, body, "iso_area_correction_exact") is False


def test_a_pending_pair_may_not_carry_a_ratio() -> None:
    body = _load(WAFER_HBM)
    body["iso_area"]["ratio"] = 3.0
    assert _check(WAFER_HBM, body, "iso_area_ratio_exact") is False
    schema = json.loads(CONTRACT_SCHEMA_PATH_V2.read_text())
    assert list(Draft202012Validator(schema).iter_errors(body))


def test_a_class_two_target_must_declare_wafer_class_nodes() -> None:
    """WAFER_LOGICAL_DEVICE pins the node class, and deliberately not the count."""

    schema = json.loads(CONTRACT_SCHEMA_PATH_V2.read_text())
    body = _load(WAFER_ARRAY)
    body["targets"]["rom"]["node_class"] = "DIE"
    assert list(Draft202012Validator(schema).iter_errors(body))
    body = _load(WAFER_ARRAY)
    body["targets"]["rom"]["node_count"] = 3
    body["targets"]["rom"]["silicon"]["silicon_area_mm2"] = 3 * WAFER_MM2
    assert sorted(e.message for e in Draft202012Validator(schema).iter_errors(body)) == []


def test_a_side_area_that_is_not_its_own_product_is_refused() -> None:
    body = _load(WAFER_ARRAY)
    body["targets"]["rom"]["silicon"]["silicon_area_mm2"] = WAFER_MM2
    assert _check(WAFER_ARRAY, body, "iso_area_side_arithmetic_exact") is False


def test_a_forged_graph_id_under_a_pending_model_is_refused() -> None:
    body = _load(WAFER_ARRAY)
    body["model"]["graph_id"] = "0" * 64
    assert _check(WAFER_ARRAY, body, "model_binding_status_consistent") is False
    schema = json.loads(CONTRACT_SCHEMA_PATH_V2.read_text())
    assert list(Draft202012Validator(schema).iter_errors(body))


def test_a_null_node_count_without_a_derivation_is_refused() -> None:
    body = _load(WAFER_HBM)
    body["targets"]["hbm"]["node_count_derivation"] = None
    assert _check(WAFER_HBM, body, "contract_integer_fields_strict") is False
    assert _check(WAFER_HBM, body, "target_hbm_identity_well_formed") is False
    schema = json.loads(CONTRACT_SCHEMA_PATH_V2.read_text())
    assert list(Draft202012Validator(schema).iter_errors(body))


def test_a_null_node_count_under_a_locked_deployment_is_refused() -> None:
    """A node count may be absent only while the deployment that fixes it is."""

    body = _load(WAFER_HBM)
    body["targets"]["hbm"]["deployment"] = {
        "digest": "1" * 64,
        "path": body["targets"]["hbm"]["deployment"]["path"],
        "source_sha256": "2" * 64,
        "status": "locked",
    }
    assert _check(WAFER_HBM, body, "contract_integer_fields_strict") is False


def test_a_missing_companion_is_refused() -> None:
    body = _load(WAFER_ARRAY)
    del body["reporting"]["companion_sources"]["resident_session_count"]
    body["reporting"]["required_companions"] = ["binding_constraint"]
    assert _check(WAFER_ARRAY, body, "reporting_companions_exact") is False
    schema = json.loads(CONTRACT_SCHEMA_PATH_V2.read_text())
    assert list(Draft202012Validator(schema).iter_errors(body))


def test_a_v1_contract_may_not_borrow_the_v2_geometry_relaxation() -> None:
    """The pending node count is a v2 affordance and only a v2 affordance."""

    body = copy.deepcopy(_load("deepseek_v4_rom_wafer_vs_hbm_cluster_32"))
    body["targets"]["hbm"]["node_count"] = None
    body["targets"]["hbm"]["node_count_derivation"] = {
        "fixed_by_gate": "X",
        "fixed_by_work_package": "Y",
        "inputs": ["z"],
        "rule": "z",
    }
    validation = validate_comparison_contract(
        body,
        repo=ROOT,
        source_path=ROOT / CONTRACT_PATHS["deepseek_v4_rom_wafer_vs_hbm_cluster_32"],
    )
    assert validation["checks"]["contract_integer_fields_strict"] is False
    assert validation["schema_errors"]
