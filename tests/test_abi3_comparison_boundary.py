"""Fail-closed tests for authoritative ABI 3.0 comparison contracts."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from abi3_comparison_contract_support import (
    cycle_inputs,
    make_boundary,
    make_locked_repository,
    semantic_digest,
    sha256_file,
    write_json,
)
from compiler.ir.v3.kernel_ir import KernelGraph
from runtime.abi3.capability import canonical_json
from tools.abi3_comparison_boundary import (
    CONTRACT_PATHS,
    CONTRACT_SCHEMA_PATH,
    ORACLE_PRODUCER_PATHS,
    BoundaryError,
    boundary_digest,
    build_boundary,
    comparison_payload,
    comparison_workload_digest,
    contract_target_roles,
    legacy_workload_digest,
    load_comparison_contract,
    validate_boundary,
    validate_comparison_contract,
)

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_SCHEMA = ROOT / "schemas/abi3/comparison_boundary_v1.schema.json"


def _rewrite_contract(bundle: dict) -> dict:
    write_json(bundle["contract_path"], bundle["contract"])
    return validate_comparison_contract(
        bundle["contract"],
        repo=bundle["repo"],
        source_path=bundle["contract_path"],
    )


def _write_strict_json_violation(path: Path, violation: str) -> None:
    """Keep the parsed payload equivalent except for a forbidden JSON form."""

    body = json.loads(path.read_text(encoding="utf-8"))
    payload = path.read_text(encoding="utf-8").rstrip()
    assert isinstance(body, dict) and payload.endswith("}")
    if violation == "duplicate":
        key = next(iter(body))
        suffix = (
            f",{json.dumps(key)}:"
            f"{json.dumps(body[key], sort_keys=True, separators=(',', ':'))}"
        )
    else:
        suffix = f',"strict_nonfinite_probe":{violation}'
    path.write_text(payload[:-1] + suffix + "}\n", encoding="utf-8")


def test_locked_contract_and_both_boundaries_are_canonical_and_source_valid(
    tmp_path: Path,
) -> None:
    bundle = make_locked_repository(tmp_path)
    rom = make_boundary(bundle, "rom")
    hbm = make_boundary(bundle, "hbm")

    assert bundle["contract_validation"]["ready"] is True
    assert canonical_json(rom) == canonical_json(make_boundary(bundle, "rom"))
    assert rom["comparison_sha256"] == semantic_digest(bundle["contract"])
    assert comparison_payload(rom) == {
        "schema": "opentallas.abi3.comparison_scope.v2",
        "comparison_id": bundle["contract"]["comparison_id"],
        "contract_sha256": semantic_digest(bundle["contract"]),
    }
    assert rom["comparison_sha256"] == hbm["comparison_sha256"]
    assert rom["boundary_sha256"] != hbm["boundary_sha256"]
    assert rom["deployment"]["sha256"] != hbm["deployment"]["sha256"]
    for boundary in (rom, hbm):
        validation = validate_boundary(boundary, repo=tmp_path)
        assert validation["valid"] is True
        assert validation["failed_checks"] == []
        assert boundary["boundary_sha256"] == boundary_digest(boundary)

    contract_schema = json.loads(CONTRACT_SCHEMA_PATH.read_text(encoding="utf-8"))
    boundary_schema = json.loads(BOUNDARY_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(contract_schema)
    Draft202012Validator.check_schema(boundary_schema)
    Draft202012Validator(contract_schema).validate(bundle["contract"])
    Draft202012Validator(boundary_schema).validate(rom)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda body: body["model"].update(numeric_profile="different_numeric_v1"),
        lambda body: body["execution"]["generation"].update(max_new_tokens=2),
        lambda body: body["policy"]["pvt"].update(temperature_c=26),
        lambda body: body["policy"]["clock"].update(comparison_frequency_hz=1),
        lambda body: body["policy"].update(evidence_class="different_evidence_v1"),
        lambda body: body["policy"].update(latency_boundary="different_latency_v1"),
        lambda body: body["policy"].update(state_boundary="different_state_v1"),
        lambda body: body["policy"].update(external_memory_policy="different_memory_v1"),
        lambda body: body["policy"].update(external_fabric_policy="different_fabric_v1"),
        lambda body: body["external_oracle"].update(source_sha256="0" * 64),
        lambda body: body["targets"]["rom"].update(target_id="different-target"),
        lambda body: body["targets"]["rom"]["deployment"].update(digest="0" * 64),
    ],
)
def test_every_scientific_and_target_identity_field_changes_pair_identity(
    tmp_path: Path, mutate
) -> None:
    bundle = make_locked_repository(tmp_path)
    changed = copy.deepcopy(bundle["contract"])
    original_digest = semantic_digest(bundle["contract"])
    mutate(changed)

    assert semantic_digest(changed) != original_digest


@pytest.mark.parametrize(
    "mutate",
    [
        lambda body: body["workload"].update(source_sha256="0" * 64),
        lambda body: body["workload"].update(index_source_sha256="0" * 64),
        lambda body: body["workload"].update(tokenizer_sha256="0" * 64),
        lambda body: body["workload"]["template"].update(source_sha256="0" * 64),
        lambda body: body["workload"].update(rendered_text_sha256="0" * 64),
        lambda body: body["execution"].update(batch=2),
        lambda body: body["execution"].update(concurrency=2),
        lambda body: body["execution"]["generation"].update(max_new_tokens=2),
    ],
)
def test_comparison_workload_digest_covers_every_source_and_execution_lock(
    tmp_path: Path, mutate
) -> None:
    bundle = make_locked_repository(tmp_path)
    baseline = comparison_workload_digest(bundle["contract"])
    changed = copy.deepcopy(bundle["contract"])
    mutate(changed)

    assert comparison_workload_digest(changed) != baseline


@pytest.mark.parametrize(
    ("mutate", "fragment"),
    [
        (lambda body: body.update(comparison_id="not a legal id"), "does not match"),
        (lambda body: body["execution"].update(batch=True), "not of type 'integer'"),
        (
            lambda body: body["execution"].update(phases=["decode", "prefill"]),
            "'prefill' was expected",
        ),
    ],
)
def test_contract_schema_rejects_bad_identifiers_booleans_and_phase_order(
    tmp_path: Path, mutate, fragment: str
) -> None:
    bundle = make_locked_repository(tmp_path)
    mutate(bundle["contract"])
    validation = _rewrite_contract(bundle)

    assert validation["valid"] is False
    assert validation["checks"]["schema_valid"] is False
    assert any(fragment in message for message in validation["schema_errors"])


def test_boundary_validation_invokes_its_json_schema_and_rejects_bool_as_int(
    tmp_path: Path,
) -> None:
    bundle = make_locked_repository(tmp_path)
    boundary = make_boundary(bundle, "rom")
    boundary["target"]["node_count"] = True
    boundary["boundary_sha256"] = boundary_digest(boundary)

    validation = validate_boundary(boundary, repo=tmp_path)
    assert validation["valid"] is False
    assert validation["checks"]["schema_valid"] is False
    assert any("not of type 'integer'" in error for error in validation["schema_errors"])


def test_contract_requires_a_source_locked_external_oracle(tmp_path: Path) -> None:
    bundle = make_locked_repository(tmp_path)
    bundle["contract"].pop("external_oracle")

    validation = _rewrite_contract(bundle)
    assert validation["valid"] is False
    assert validation["checks"]["schema_valid"] is False
    assert "external_oracle_contract_well_formed" in validation["failed_checks"]


def test_locked_external_oracle_and_producer_are_reopened(tmp_path: Path) -> None:
    bundle = make_locked_repository(tmp_path)
    oracle_path = tmp_path / bundle["contract"]["external_oracle"]["path"]
    oracle = json.loads(oracle_path.read_text(encoding="utf-8"))
    oracle["results"][bundle["workload"]["workload_id"]][
        "generated_token_ids"
    ] = [4, 6, 7]
    write_json(oracle_path, oracle)

    validation = _rewrite_contract(bundle)
    assert validation["valid"] is False
    assert "external_oracle_source_exact_if_locked" in validation["failed_checks"]

    bundle = make_locked_repository(tmp_path / "producer")
    producer_path = (
        bundle["repo"] / bundle["contract"]["external_oracle"]["producer"]["tool"]
    )
    write_json(producer_path, {"fixture_source": "tampered-producer"})
    validation = _rewrite_contract(bundle)
    assert validation["valid"] is False
    assert "external_oracle_producer_exact_if_locked" in validation["failed_checks"]


def test_locked_external_oracle_cannot_emit_eos_after_generation_cap(
    tmp_path: Path,
) -> None:
    bundle = make_locked_repository(
        tmp_path,
        max_new_tokens=2,
        oracle_generated_token_ids=[4, 7],
    )
    oracle_path = tmp_path / bundle["contract"]["external_oracle"]["path"]
    oracle = json.loads(oracle_path.read_text(encoding="utf-8"))
    result = oracle["results"][bundle["workload"]["workload_id"]]
    result["generated_token_ids"] = [4, 5, 7]
    result["generated_token_count"] = 3
    write_json(oracle_path, oracle)
    bundle["contract"]["external_oracle"]["source_sha256"] = sha256_file(
        oracle_path
    )

    validation = _rewrite_contract(bundle)
    assert validation["checks"]["external_oracle_source_exact_if_locked"] is True
    assert validation["valid"] is False
    assert "external_oracle_terminal_exact_if_locked" in validation["failed_checks"]


def test_locked_external_oracle_accepts_immediate_eos(tmp_path: Path) -> None:
    bundle = make_locked_repository(
        tmp_path,
        oracle_generated_token_ids=[7],
        oracle_stop_reason="eos",
    )

    validation = bundle["contract_validation"]
    assert validation["checks"]["external_oracle_terminal_exact_if_locked"] is True
    assert validation["ready"] is True


def test_pending_external_oracle_is_valid_but_never_ready(tmp_path: Path) -> None:
    bundle = make_locked_repository(tmp_path)
    external_oracle = bundle["contract"]["external_oracle"]
    external_oracle.update(status="pending", source_sha256=None)
    external_oracle["producer"]["source_sha256"] = None

    validation = _rewrite_contract(bundle)
    assert validation["valid"] is True
    assert validation["ready"] is False
    assert validation["external_oracle_source_ready"] is False
    assert "external_oracle_locked" in validation["failed_checks"]


def test_external_oracle_producer_path_is_comparison_specific(
    tmp_path: Path,
) -> None:
    bundle = make_locked_repository(tmp_path)
    bundle["contract"]["external_oracle"]["producer"]["tool"] = (
        "tools/run_deepseek_v4_reference_oracle.py"
    )

    validation = _rewrite_contract(bundle)
    assert validation["valid"] is False
    assert "external_oracle_contract_well_formed" in validation["failed_checks"]


@pytest.mark.parametrize("violation", ["duplicate", "NaN", "Infinity"])
def test_governed_contract_source_rejects_ambiguous_json(
    tmp_path: Path, violation: str
) -> None:
    bundle = make_locked_repository(tmp_path)
    _write_strict_json_violation(bundle["contract_path"], violation)
    message = "duplicate JSON key" if violation == "duplicate" else "non-finite JSON number"

    with pytest.raises(BoundaryError, match=message):
        load_comparison_contract(
            bundle["contract"]["comparison_id"],
            repo=tmp_path,
            path=bundle["contract_path"],
        )


@pytest.mark.parametrize("violation", ["duplicate", "NaN", "Infinity"])
@pytest.mark.parametrize(
    ("source", "failed_check"),
    [
        ("workload", "workload_digest_self_consistent"),
        ("index", "workload_index_schema_exact"),
        ("oracle", "external_oracle_source_exact_if_locked"),
        ("deployment", "target_rom_deployment_source_exact"),
        ("capability", "target_rom_capability_source_exact"),
        ("cost", "target_rom_cost_source_exact"),
    ],
)
def test_governed_dependency_sources_reject_ambiguous_json(
    tmp_path: Path,
    violation: str,
    source: str,
    failed_check: str,
) -> None:
    bundle = make_locked_repository(tmp_path)
    target = bundle["contract"]["targets"]["rom"]
    if source == "workload":
        path = bundle["workload_path"]
        lock = bundle["contract"]["workload"]
    elif source == "index":
        path = bundle["index_path"]
        lock = bundle["contract"]["workload"]
    elif source == "oracle":
        path = tmp_path / bundle["contract"]["external_oracle"]["path"]
        lock = bundle["contract"]["external_oracle"]
    elif source == "deployment":
        path = bundle["roles"]["rom"]["deployment_path"] / "deployment.json"
        lock = target["deployment"]
    elif source == "capability":
        path = bundle["roles"]["rom"]["capability_path"]
        lock = target["capability"]
    else:
        path = bundle["roles"]["rom"]["cost_table_path"]
        lock = target["cost_policy"]["lock"]

    _write_strict_json_violation(path, violation)
    sha_field = "index_source_sha256" if source == "index" else "source_sha256"
    lock[sha_field] = sha256_file(path)

    validation = _rewrite_contract(bundle)
    assert validation["ready"] is False
    assert failed_check in validation["failed_checks"]


def test_workload_digest_rejects_declared_count_that_differs_from_tokens() -> None:
    with pytest.raises(BoundaryError, match="must equal its positive token_ids length"):
        legacy_workload_digest(
            {
                "workload_id": "TA-W11-2-BAD-COUNT",
                "kind": "contract_test",
                "token_ids": [1, 2, 3],
                "prompt_token_count": 2,
                "max_new_tokens": 1,
            }
        )


@pytest.mark.parametrize(
    ("case", "failed_check"),
    [
        ("index_entry", "workload_index_entry_exact"),
        ("tokenizer", "tokenizer_identity_exact"),
        ("template", "template_identity_exact"),
        ("rendered_text", "rendered_text_digest_self_consistent"),
    ],
)
def test_mutated_index_tokenizer_template_and_rendered_text_are_rejected(
    tmp_path: Path, case: str, failed_check: str
) -> None:
    bundle = make_locked_repository(tmp_path)
    contract = bundle["contract"]
    if case in {"index_entry", "tokenizer"}:
        index = json.loads(bundle["index_path"].read_text(encoding="utf-8"))
        if case == "index_entry":
            index["workloads"][contract["workload"]["workload_id"]]["digest"] = "0" * 64
        else:
            index["tokenizer_sha256"] = "3" * 64
        write_json(bundle["index_path"], index)
        contract["workload"]["index_source_sha256"] = sha256_file(
            bundle["index_path"]
        )
    elif case == "template":
        bundle["template_path"].write_text("changed {prompt}\n", encoding="utf-8")
    else:
        workload = json.loads(bundle["workload_path"].read_text(encoding="utf-8"))
        workload["rendered_text"] = "changed rendered prompt"
        write_json(bundle["workload_path"], workload)
        contract["workload"]["source_sha256"] = sha256_file(bundle["workload_path"])

    validation = _rewrite_contract(bundle)
    assert validation["valid"] is False
    assert failed_check in validation["failed_checks"]


@pytest.mark.parametrize(
    ("field", "value", "failed_check"),
    [
        ("model_id", "forged-model", "model_id_source_exact"),
        ("numeric_profile", "forged_numeric_v1", "numeric_profile_source_exact"),
        ("source", {"exporter": "forged"}, "graph_id_source_exact"),
    ],
)
def test_kernel_ir_model_graph_and_numeric_identity_are_rederived(
    tmp_path: Path, field: str, value, failed_check: str
) -> None:
    bundle = make_locked_repository(tmp_path)
    body = json.loads(bundle["graph_path"].read_text(encoding="utf-8"))
    body.pop("graph_id")
    body[field] = value
    forged = KernelGraph.from_dict(body)
    body["graph_id"] = forged.graph_id
    write_json(bundle["graph_path"], body)
    bundle["contract"]["model"]["kernel_ir_source_sha256"] = sha256_file(
        bundle["graph_path"]
    )

    validation = _rewrite_contract(bundle)
    assert validation["valid"] is False
    assert failed_check in validation["failed_checks"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("role", "hbm"),
        ("backend", "unknown.backend"),
        ("target_id", "wrong-target"),
        ("storage_class", "HBM"),
        ("topology_class", 1),
        ("node_count", 32),
    ],
)
def test_forged_target_role_backend_storage_and_topology_are_rejected(
    tmp_path: Path, field: str, value
) -> None:
    bundle = make_locked_repository(tmp_path)
    boundary = make_boundary(bundle, "rom")
    forged = copy.deepcopy(boundary)
    forged["target"][field] = value
    forged["boundary_sha256"] = boundary_digest(forged)

    validation = validate_boundary(forged, repo=tmp_path)
    assert validation["valid"] is False
    assert "target_identity_contract_exact" in validation["failed_checks"]


@pytest.mark.parametrize(
    ("record", "field", "failed_check"),
    [
        ("deployment", "sha256", "deployment_source_exact"),
        ("capability", "sha256", "capability_source_exact"),
        ("cost_table", "sha256", "cost_source_exact"),
        ("cost_table", "policy_id", "cost_source_exact"),
    ],
)
def test_wrong_deployment_capability_and_cost_locks_are_rejected(
    tmp_path: Path, record: str, field: str, failed_check: str
) -> None:
    bundle = make_locked_repository(tmp_path)
    forged = make_boundary(bundle, "rom")
    forged[record][field] = "0" * 64 if field == "sha256" else "wrong_policy_v1"
    forged["boundary_sha256"] = boundary_digest(forged)

    validation = validate_boundary(forged, repo=tmp_path)
    assert validation["valid"] is False
    assert failed_check in validation["failed_checks"]


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("pvt", "corner_id", "wrong_corner"),
        ("clock", "policy_id", "wrong_clock_v1"),
        (None, "evidence_class", "wrong_evidence_v1"),
        (None, "latency_boundary", "wrong_latency_v1"),
        (None, "state_boundary", "wrong_state_v1"),
        (None, "external_memory_policy", "wrong_memory_v1"),
        (None, "external_fabric_policy", "wrong_fabric_v1"),
    ],
)
def test_policy_identity_drift_invalidates_both_target_cost_locks(
    tmp_path: Path, section: str | None, field: str, value
) -> None:
    bundle = make_locked_repository(tmp_path)
    policy = bundle["contract"]["policy"]
    (policy[section] if section else policy)[field] = value

    validation = _rewrite_contract(bundle)
    assert validation["valid"] is True
    assert validation["ready"] is False
    assert "target_rom_cost_source_exact" in validation["failed_checks"]
    assert "target_hbm_cost_source_exact" in validation["failed_checks"]
    with pytest.raises(BoundaryError, match="target sources are not locked"):
        make_boundary(bundle, "rom")


def test_cycle_inputs_cannot_reuse_boundary_after_identity_mutation(
    tmp_path: Path,
) -> None:
    bundle = make_locked_repository(tmp_path)
    boundary = make_boundary(bundle, "rom")
    inputs = cycle_inputs(bundle, boundary)
    assert validate_boundary(boundary, repo=tmp_path, cycle_inputs=inputs)["valid"]

    mutations = [
        ("cycle_contract_digest_exact", "comparison_contract_digest", "0" * 64),
        ("cycle_execution_scope_exact", "comparison_execution_scope", "full_workload"),
        ("cycle_model_exact", "model_digest", "0" * 64),
        ("cycle_target_exact", "target_id", "wrong-target"),
        ("cycle_target_exact", "node_count", 32),
    ]
    for expected, field, value in mutations:
        forged = copy.deepcopy(inputs)
        forged[field] = value
        validation = validate_boundary(boundary, repo=tmp_path, cycle_inputs=forged)
        assert validation["valid"] is False
        assert expected in validation["failed_checks"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("batch", True),
        ("batch", 1.0),
        ("concurrency", 1.0),
        ("context_tokens", 3.0),
    ],
)
def test_contract_execution_counts_require_exact_integers(
    tmp_path: Path, field: str, value
) -> None:
    bundle = make_locked_repository(tmp_path)
    bundle["contract"]["execution"][field] = value

    validation = _rewrite_contract(bundle)
    assert validation["valid"] is False
    assert validation["checks"]["contract_integer_fields_strict"] is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("topology_class", True),
        ("topology_class", 0.0),
        ("max_nodes", True),
        ("max_nodes", 1.0),
    ],
)
def test_capability_topology_and_max_nodes_require_exact_integers(
    tmp_path: Path, field: str, value
) -> None:
    bundle = make_locked_repository(tmp_path)
    path = bundle["roles"]["rom"]["capability_path"]
    capability = json.loads(path.read_text(encoding="utf-8"))
    if field == "topology_class":
        capability[field] = value
    else:
        capability["limits"][field] = value
    write_json(path, capability)
    bundle["contract"]["targets"]["rom"]["capability"][
        "source_sha256"
    ] = sha256_file(path)

    validation = _rewrite_contract(bundle)
    assert validation["ready"] is False
    assert "target_rom_capability_source_exact" in validation["failed_checks"]


@pytest.mark.parametrize("value", [True, 0.0, 0.75, "0"])
def test_cycle_topology_rejects_bool_float_fraction_and_numeric_string(
    tmp_path: Path, value
) -> None:
    bundle = make_locked_repository(tmp_path)
    boundary = make_boundary(bundle, "rom")
    inputs = cycle_inputs(bundle, boundary)
    inputs["topology_class"] = value

    validation = validate_boundary(boundary, repo=tmp_path, cycle_inputs=inputs)
    assert validation["valid"] is False
    assert "cycle_target_exact" in validation["failed_checks"]


@pytest.mark.parametrize("value", [0, "SINGLE_CHIP"])
def test_cycle_topology_accepts_only_exact_enum_integer_or_canonical_name(
    tmp_path: Path, value
) -> None:
    bundle = make_locked_repository(tmp_path)
    boundary = make_boundary(bundle, "rom")
    inputs = cycle_inputs(bundle, boundary)
    inputs["topology_class"] = value

    assert validate_boundary(
        boundary, repo=tmp_path, cycle_inputs=inputs
    )["valid"] is True


@pytest.mark.parametrize("value", [True, 1.0, 0.75, "1"])
def test_cycle_node_count_requires_an_exact_positive_integer(
    tmp_path: Path, value
) -> None:
    bundle = make_locked_repository(tmp_path)
    boundary = make_boundary(bundle, "rom")
    inputs = cycle_inputs(bundle, boundary)
    inputs["node_count"] = value

    validation = validate_boundary(boundary, repo=tmp_path, cycle_inputs=inputs)
    assert validation["valid"] is False
    assert "cycle_target_exact" in validation["failed_checks"]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda request: request.update(entrypoint_id=999),
        lambda request: request.update(generation_policy_id=123),
        lambda request: request.update(transactions=True),
        lambda request: request.update(transactions=1.0),
        lambda request: request["symbols"].update(PHASE=1),
        lambda request: request["symbols"].update(POSITION_END=99),
        lambda request: request["symbols"].update(UNRELATED=1),
        lambda request: request["symbols"].update(NODE_COUNT=99),
    ],
)
def test_boundary_builder_rejects_self_hashed_but_ungoverned_requests(
    tmp_path: Path, mutate
) -> None:
    bundle = make_locked_repository(tmp_path)
    arguments = dict(bundle["roles"]["rom"])
    request = copy.deepcopy(arguments["request"])
    mutate(request)
    arguments["request"] = request

    with pytest.raises(BoundaryError, match="governed request is invalid"):
        build_boundary(**arguments)


@pytest.mark.parametrize(
    "selector",
    [
        lambda bundle: bundle["contract"]["model"],
        lambda bundle: bundle["contract"]["workload"],
        lambda bundle: bundle["contract"]["workload"]["template"],
        lambda bundle: bundle["contract"]["targets"]["rom"]["deployment"],
        lambda bundle: bundle["contract"]["targets"]["rom"]["capability"],
        lambda bundle: bundle["contract"]["targets"]["rom"]["cost_policy"]["lock"],
        lambda bundle: bundle["contract"]["external_oracle"],
    ],
)
@pytest.mark.parametrize("bad_path", ["/tmp/outside.json", "../outside.json"])
def test_contract_source_paths_must_be_canonical_repo_relative(
    tmp_path: Path, selector, bad_path: str
) -> None:
    bundle = make_locked_repository(tmp_path)
    record = selector(bundle)
    if record is bundle["contract"]["model"]:
        record["kernel_ir_path"] = bad_path
    else:
        record["path"] = bad_path

    validation = _rewrite_contract(bundle)
    assert validation["valid"] is False


def test_workload_index_and_oracle_producer_aliases_are_rejected(
    tmp_path: Path,
) -> None:
    bundle = make_locked_repository(tmp_path)
    bundle["contract"]["workload"]["index_path"] = (
        "build/workloads/abi3-fixture/../abi3-fixture/index.json"
    )
    assert _rewrite_contract(bundle)["valid"] is False

    bundle = make_locked_repository(tmp_path / "producer")
    bundle["contract"]["external_oracle"]["producer"]["tool"] = (
        "tools/../tools/run_qwen3_reference_oracle.py"
    )
    assert _rewrite_contract(bundle)["valid"] is False


def test_contract_source_symlink_escape_is_rejected(tmp_path: Path) -> None:
    bundle = make_locked_repository(tmp_path)
    outside = tmp_path.parent / "w11-2-outside-workload.json"
    write_json(outside, json.loads(bundle["workload_path"].read_text()))
    link = tmp_path / "build/workloads/escaped.json"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(outside)
    bundle["contract"]["workload"]["path"] = link.relative_to(tmp_path).as_posix()
    bundle["contract"]["workload"]["source_sha256"] = sha256_file(outside)

    assert _rewrite_contract(bundle)["valid"] is False


# --- ROM-versus-ROM pairs: the wafer-versus-array packaging comparison -------

CONTRACT_ROOT = ROOT / "configs/abi3/comparison_contracts"
WAFER_ARRAY_ID = "deepseek_v4_rom_wafer_vs_rom_array_32"
WAFER_ARRAY_FILE = "deepseek_v4_rom_wafer_vs_rom_array_32_v1.json"
ARRAY_HBM_FILE = "deepseek_v4_rom_array_32_vs_hbm_cluster_32_v1.json"
WAFER_HBM_FILE = "deepseek_v4_rom_wafer_vs_hbm_cluster_32_v1.json"
QWEN_FILE = "qwen3_rom_single_chip_vs_hbm_single_chip_v1.json"


def _checked_in_contract(name: str) -> dict:
    return json.loads((CONTRACT_ROOT / name).read_text(encoding="utf-8"))


def _contract_validator() -> Draft202012Validator:
    schema = json.loads(CONTRACT_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _shared_checks(validation: dict) -> dict:
    """The contract checks that do not depend on a target slot or the path."""

    return {
        name: passed
        for name, passed in validation["checks"].items()
        if not name.startswith("target_") and name != "registered_path_exact"
    }


def test_wafer_versus_array_contract_validates_and_is_registered() -> None:
    contract = _checked_in_contract(WAFER_ARRAY_FILE)
    _contract_validator().validate(contract)

    assert contract["comparison_id"] == WAFER_ARRAY_ID
    assert CONTRACT_PATHS[WAFER_ARRAY_ID] == (
        "configs/abi3/comparison_contracts/" + WAFER_ARRAY_FILE
    )
    assert ORACLE_PRODUCER_PATHS[WAFER_ARRAY_ID] == (
        "tools/run_deepseek_v4_reference_oracle.py"
    )
    assert contract_target_roles(contract["targets"]) == ("rom", "rom_array")

    # The sides are the two existing contracts' targets, copied exactly.
    wafer_hbm = _checked_in_contract(WAFER_HBM_FILE)
    array_hbm = _checked_in_contract(ARRAY_HBM_FILE)
    assert contract["targets"]["rom"] == wafer_hbm["targets"]["rom"]
    assert contract["targets"]["rom_array"] == {
        **array_hbm["targets"]["rom"],
        "role": "rom_array",
    }
    assert contract["targets"]["rom_array"]["storage_class"] == "ROM"
    for block in ("model", "workload", "execution", "external_oracle"):
        assert contract[block] == array_hbm[block]
    assert contract["external_oracle"]["status"] == "pending"

    source_path = ROOT / CONTRACT_PATHS[WAFER_ARRAY_ID]
    validation = validate_comparison_contract(
        contract, repo=ROOT, source_path=source_path
    )
    checks = validation["checks"]
    assert validation["schema_errors"] == []
    assert checks["schema_valid"] is True
    assert checks["registered_path_exact"] is True
    assert checks["contract_integer_fields_strict"] is True
    assert checks["external_oracle_contract_well_formed"] is True
    assert checks["target_rom_identity_well_formed"] is True
    assert checks["target_rom_array_identity_well_formed"] is True
    assert checks["target_ids_distinct"] is True
    assert checks["target_deployments_distinct"] is True
    assert set(validation["target_sources_ready"]) == {"rom", "rom_array"}
    assert validation["ready"] is False
    # The shared model, workload and oracle blocks are the ones the registered
    # wafer-versus-HBM contract binds, so the two contracts' shared-source
    # checks must agree exactly on this host, whatever the state of the
    # (out-of-tree) build inputs.
    sibling = validate_comparison_contract(
        wafer_hbm, repo=ROOT, source_path=CONTRACT_ROOT / WAFER_HBM_FILE
    )
    assert _shared_checks(validation) == _shared_checks(sibling)


@pytest.mark.parametrize("name", [QWEN_FILE, WAFER_HBM_FILE, ARRAY_HBM_FILE])
def test_existing_contracts_still_validate_against_the_amended_schema(
    name: str,
) -> None:
    contract = _checked_in_contract(name)
    _contract_validator().validate(contract)
    assert contract_target_roles(contract["targets"]) == ("rom", "hbm")

    validation = validate_comparison_contract(
        contract, repo=ROOT, source_path=CONTRACT_ROOT / name
    )
    assert validation["schema_errors"] == []
    assert validation["checks"]["schema_valid"] is True
    assert set(validation["target_sources_ready"]) == {"rom", "hbm"}


def _with_hbm_and_rom_array(contract: dict) -> None:
    hbm = _checked_in_contract(WAFER_HBM_FILE)["targets"]["hbm"]
    contract["targets"]["hbm"] = hbm


def _with_rom_array_in_hbm_storage(contract: dict) -> None:
    contract["targets"]["rom_array"]["storage_class"] = "HBM"


def _with_rom_array_mislabelled_rom(contract: dict) -> None:
    contract["targets"]["rom_array"]["role"] = "rom"


def _with_only_rom(contract: dict) -> None:
    del contract["targets"]["rom_array"]


@pytest.mark.parametrize(
    "mutate",
    [
        _with_hbm_and_rom_array,
        _with_rom_array_in_hbm_storage,
        _with_rom_array_mislabelled_rom,
        _with_only_rom,
    ],
)
def test_targets_refuse_three_sides_and_a_rom_array_that_is_not_rom(
    mutate,
) -> None:
    contract = _checked_in_contract(WAFER_ARRAY_FILE)
    mutate(contract)

    assert not _contract_validator().is_valid(contract)
    validation = validate_comparison_contract(
        contract, repo=ROOT, source_path=ROOT / CONTRACT_PATHS[WAFER_ARRAY_ID]
    )
    assert validation["valid"] is False
    assert validation["checks"]["schema_valid"] is False
    assert validation["schema_errors"]


def test_hbm_pair_refuses_a_rom_array_slot_and_a_rom_array_role() -> None:
    validator = _contract_validator()
    contract = _checked_in_contract(WAFER_HBM_FILE)
    contract["targets"]["rom_array"] = {
        **_checked_in_contract(ARRAY_HBM_FILE)["targets"]["rom"],
        "role": "rom_array",
    }
    assert not validator.is_valid(contract)

    contract = _checked_in_contract(WAFER_HBM_FILE)
    contract["targets"]["hbm"]["role"] = "rom_array"
    assert not validator.is_valid(contract)  # every slot pins its role
    validation = validate_comparison_contract(
        contract, repo=ROOT, source_path=CONTRACT_ROOT / WAFER_HBM_FILE
    )
    assert validation["checks"]["schema_valid"] is False
    assert validation["checks"]["target_hbm_identity_well_formed"] is False


@pytest.mark.parametrize(
    ("contract_file", "slot", "field", "value"),
    [
        (WAFER_HBM_FILE, "rom", "role", "rom_array"),
        (WAFER_HBM_FILE, "rom", "role", "hbm"),
        (WAFER_HBM_FILE, "rom", "storage_class", "HBM"),
        (WAFER_HBM_FILE, "hbm", "role", "rom"),
        (WAFER_HBM_FILE, "hbm", "storage_class", "ROM"),
        (WAFER_ARRAY_FILE, "rom", "role", "rom_array"),
        (WAFER_ARRAY_FILE, "rom", "storage_class", "HBM"),
        (WAFER_ARRAY_FILE, "rom_array", "role", "rom"),
        (WAFER_ARRAY_FILE, "rom_array", "storage_class", "HBM"),
    ],
)
def test_every_slot_pins_its_role_and_storage_class(
    contract_file, slot, field, value
) -> None:
    contract = _checked_in_contract(contract_file)
    assert contract["targets"][slot][field] != value
    contract["targets"][slot][field] = value

    errors = sorted(_contract_validator().iter_errors(contract), key=str)
    assert errors
    assert any(list(error.path) == ["targets", slot, field] for error in errors)


def test_readiness_audit_registers_the_wafer_versus_array_contract() -> None:
    from tools.audit_abi3_asap7_comparison_readiness import (
        SOURCE_PATHS,
        _load_authoritative_contracts,
        _required_functional_sources,
    )

    summaries = {
        item["comparison_id"]: item for item in _load_authoritative_contracts(ROOT)
    }
    assert WAFER_ARRAY_ID in summaries
    summary = summaries[WAFER_ARRAY_ID]
    assert summary["contract_path"] == CONTRACT_PATHS[WAFER_ARRAY_ID]
    assert summary["source_checks"]["schema_valid"] is True
    assert summary["source_checks"]["registered_path_exact"] is True
    assert set(summary["target_lock_status"]) == {"rom", "rom_array"}
    assert set(summary["target_sources_ready"]) == {"rom", "rom_array"}
    assert summary["contract_ready"] is False
    assert summary["external_oracle_lock_status"] == "pending"
    # Shared sources are the array-versus-HBM contract's; the readiness
    # verdict on them is whatever this host gives the wafer-versus-HBM
    # sibling, which binds the same Kernel IR and workload.
    sibling = summaries["deepseek_v4_rom_wafer_vs_hbm_cluster_32"]
    assert summary["contract_source_valid"] == sibling["contract_source_valid"]
    assert CONTRACT_PATHS[WAFER_ARRAY_ID] in SOURCE_PATHS

    from tools.run_accelerator_tokens import _functional_source_sha256

    assert _required_functional_sources(ROOT, WAFER_ARRAY_ID, "rom") == set(
        _functional_source_sha256("rom_deepseek_v4")
    )
    assert _required_functional_sources(ROOT, WAFER_ARRAY_ID, "rom_array") == set(
        _functional_source_sha256("rom_deepseek_v4_array")
    )


def test_rom_versus_rom_fixture_pair_locks_and_resolves_sides_by_identity(
    tmp_path: Path,
) -> None:
    bundle = make_locked_repository(
        tmp_path,
        comparison_id=WAFER_ARRAY_ID,
        namespace="packaging",
        roles=("rom", "rom_array"),
    )
    validation = bundle["contract_validation"]
    assert validation["ready"] is True
    assert validation["target_sources_ready"] == {"rom": True, "rom_array": True}

    _contract_validator().validate(bundle["contract"])
    boundary_schema = json.loads(BOUNDARY_SCHEMA.read_text(encoding="utf-8"))
    rom = make_boundary(bundle, "rom")
    array = make_boundary(bundle, "rom_array")
    for boundary in (rom, array):
        Draft202012Validator(boundary_schema).validate(boundary)
        result = validate_boundary(boundary, repo=tmp_path)
        assert result["valid"] is True
        assert result["failed_checks"] == []
    assert rom["target"]["role"] == "rom"
    assert array["target"]["role"] == "rom_array"
    assert rom["target"]["storage_class"] == array["target"]["storage_class"] == "ROM"
    assert rom["comparison_sha256"] == array["comparison_sha256"]
    assert rom["boundary_sha256"] != array["boundary_sha256"]
    assert rom["deployment"]["sha256"] != array["deployment"]["sha256"]

    # A ROM deployment presented under the other ROM slot is refused: the
    # slot is resolved by backend and target identity, not by storage class.
    forged = copy.deepcopy(array)
    forged["target"]["role"] = "rom"
    forged["boundary_sha256"] = boundary_digest(forged)
    result = validate_boundary(forged, repo=tmp_path)
    assert result["valid"] is False
    assert "target_identity_contract_exact" in result["failed_checks"]

    # The wafer-slot deployment handed the array slot's materials resolves to
    # the rom slot by identity and is then refused by that slot's locks.
    arguments = dict(bundle["roles"]["rom_array"])
    arguments["deployment"] = bundle["roles"]["rom"]["deployment"]
    with pytest.raises(BoundaryError, match="target source lock mismatch"):
        build_boundary(**arguments)
