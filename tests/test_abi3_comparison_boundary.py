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
    BoundaryError,
    CONTRACT_SCHEMA_PATH,
    boundary_digest,
    build_boundary,
    comparison_payload,
    comparison_workload_digest,
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
