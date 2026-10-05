from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from compiler.tensor_accelerator.common import canonical_json_bytes
from compiler.tensor_accelerator.production_model import (
    ProductionModelGraphError,
    compute_graph_id,
    parse_production_model_graph,
)


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/model_graph_v2.schema.json"
)
FIXTURE = (
    ROOT
    / "testdata/compiler/tensor_accelerator_fixture/production_model_graph.json"
)
TWO = "2" * 64


def _graph() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _rehash(graph: dict[str, object]) -> None:
    graph["graph_id"] = compute_graph_id(graph)


def test_production_graph_round_trips_and_validates_against_draft_2020_12() -> None:
    raw = _graph()
    model = parse_production_model_graph(raw)
    assert model.to_dict() == raw
    assert model.graph_id == compute_graph_id(raw)
    assert model.entrypoints[0].phase == "prefill"
    assert model.entrypoints[1].phase == "decode"
    assert model.operations[1].predicate == {
        "kind": "compare",
        "operator": "le",
        "symbol": "position_end",
        "value": 8000,
    }
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(raw)


def test_graph_identity_covers_source_checkpoint_predicate_and_state_contract() -> None:
    raw = _graph()
    canonical = canonical_json_bytes(raw)
    assert hashlib.sha256(canonical).hexdigest() != raw["graph_id"]
    for mutate in (
        lambda value: value["source"].__setitem__("revision", "fedcba9876543210"),
        lambda value: value["tensors"][1]["binding"].__setitem__("payload_sha256", TWO),
        lambda value: value["operations"][1]["predicate"].__setitem__("value", 7999),
        lambda value: value["operations"][2]["effects"][1].__setitem__("action", "discard"),
    ):
        changed = copy.deepcopy(raw)
        mutate(changed)
        assert compute_graph_id(changed) != raw["graph_id"]
        with pytest.raises(ProductionModelGraphError, match="graph_id differs"):
            parse_production_model_graph(changed)


def test_checkpoint_bindings_are_exact_and_runtime_values_cannot_claim_payloads() -> None:
    mismatch = _graph()
    mismatch["tensors"][1]["binding"]["sources"][0]["shape"] = [4096, 2048]
    _rehash(mismatch)
    with pytest.raises(ProductionModelGraphError, match="identity binding.*differs"):
        parse_production_model_graph(mismatch)

    missing = _graph()
    del missing["tensors"][1]["binding"]
    _rehash(missing)
    with pytest.raises(ProductionModelGraphError, match="lacks an exact checkpoint"):
        parse_production_model_graph(missing)

    forged_runtime = _graph()
    forged_runtime["tensors"][0]["binding"] = copy.deepcopy(
        forged_runtime["tensors"][1]["binding"]
    )
    _rehash(forged_runtime)
    with pytest.raises(ProductionModelGraphError, match="runtime tensor.*must not"):
        parse_production_model_graph(forged_runtime)


def test_phase_dataflow_and_transactional_state_fail_closed() -> None:
    phase_gap = _graph()
    phase_gap["operations"][0]["phases"] = ["prefill"]
    _rehash(phase_gap)
    with pytest.raises(ProductionModelGraphError, match="phase-unavailable.*decode"):
        parse_production_model_graph(phase_gap)

    missing_prepare = _graph()
    missing_prepare["operations"][1]["effects"] = [
        {"action": "read_committed", "state": "state.kv"}
    ]
    _rehash(missing_prepare)
    with pytest.raises(ProductionModelGraphError, match="reads prepared state.*before"):
        parse_production_model_graph(missing_prepare)

    open_prepare = _graph()
    open_prepare["operations"][2]["effects"] = []
    _rehash(open_prepare)
    with pytest.raises(ProductionModelGraphError, match="uncommitted prepared states"):
        parse_production_model_graph(open_prepare)

    illegal_state_boundary = _graph()
    illegal_state_boundary["entrypoints"][1]["states"] = []
    _rehash(illegal_state_boundary)
    with pytest.raises(ProductionModelGraphError, match="outside the decode"):
        parse_production_model_graph(illegal_state_boundary)

    committed_read_during_prepare = _graph()
    committed_read_during_prepare["operations"][2]["effects"][0]["action"] = (
        "read_committed"
    )
    _rehash(committed_read_during_prepare)
    with pytest.raises(ProductionModelGraphError, match="while a prepare is open"):
        parse_production_model_graph(committed_read_during_prepare)


def test_predicates_are_structured_bounded_and_symbol_checked() -> None:
    unknown = _graph()
    unknown["operations"][1]["predicate"]["symbol"] = "unknown_symbol"
    _rehash(unknown)
    with pytest.raises(ProductionModelGraphError, match="unknown runtime symbol"):
        parse_production_model_graph(unknown)

    unstructured = _graph()
    unstructured["operations"][1]["predicate"] = "position_end <= 8000"
    _rehash(unstructured)
    with pytest.raises(ProductionModelGraphError, match="bounded predicate object"):
        parse_production_model_graph(unstructured)

    affine = _graph()
    affine["entrypoints"][1]["predicate"] = {
        "kind": "affine",
        "operator": "eq",
        "terms": [
            {"coefficient": 1, "symbol": "context_tokens"},
            {"coefficient": -1, "symbol": "position_end"},
        ],
        "value": 0,
    }
    _rehash(affine)
    assert parse_production_model_graph(affine).entrypoints[1].predicate == (
        affine["entrypoints"][1]["predicate"]
    )

    duplicate = copy.deepcopy(affine)
    duplicate["entrypoints"][1]["predicate"]["terms"][1]["symbol"] = (
        "context_tokens"
    )
    _rehash(duplicate)
    with pytest.raises(ProductionModelGraphError, match="duplicate symbols"):
        parse_production_model_graph(duplicate)


def test_zero_based_runtime_indices_are_legal_but_not_tensor_dimensions() -> None:
    graph = _graph()
    graph["symbols"].append(
        {
            "binding": {"field": "position_start", "kind": "request"},
            "default": 0,
            "id": "position_start",
            "maximum": 8191,
            "minimum": 0,
            "multiple_of": 1,
        }
    )
    _rehash(graph)
    parsed = parse_production_model_graph(graph)
    assert parsed.symbol_by_id["position_start"].default == 0

    invalid_shape = copy.deepcopy(graph)
    invalid_shape["tensors"][0]["shape"][1] = "position_start"
    _rehash(invalid_shape)
    with pytest.raises(ProductionModelGraphError, match="unknown or non-static"):
        parse_production_model_graph(invalid_shape)


def test_v2_remains_backend_neutral() -> None:
    raw = _graph()
    encoded = canonical_json_bytes(raw)
    assert b"ROM_" not in encoded
    assert b"HBM_" not in encoded
    assert b"SRAM_" not in encoded
    assert b"physical_address" not in encoded
    assert b"bank_id" not in encoded
