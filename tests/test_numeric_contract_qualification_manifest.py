"""A7 provenance tests for phase-specific numeric qualification shapes."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "qualify_numeric_contracts",
    REPO / "tools/qualify_numeric_contracts.py",
)
tool = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(tool)


class ObservedBackend:
    """Small backend double exposing the same observation boundary as Backend."""

    name = "observed"

    def __init__(self) -> None:
        self.calls = 0
        self.resets = 0
        self.corrupt_digest = False

    def implementation_identity(self) -> dict:
        return {
            "backend": self.name,
            "library": "test",
            "library_version": "1",
            "device": "test",
            "flags": {"threads": 1},
        }

    def reset_executed_associations(self) -> None:
        self.calls = 0
        self.resets += 1

    def record_blocked(self) -> None:
        self.calls += 1

    def executed_association_manifest(self) -> dict:
        entries = []
        if self.calls:
            entries.append(
                {
                    "numeric_contract": tool.CONTRACT_BLOCKED,
                    "activation_shape": [1, 8],
                    "weight_shape": [4, 8],
                    "output_shape": [1, 4],
                    "call_count": self.calls,
                }
            )
        body = {
            "schema": tool.ASSOCIATION_SCHEMA,
            "association_policy": tool.ASSOCIATION_POLICY,
            "implementation_identity": self.implementation_identity(),
            "entries": entries,
            "distinct_association_count": len(entries),
            "blocked_call_count": self.calls,
        }
        body["manifest_sha256"] = tool._association_manifest_digest(body)
        if self.corrupt_digest:
            body["manifest_sha256"] = "0" * 64
        return body


def _identity(name: str = "observed") -> dict:
    return {
        "backend": name,
        "library": "test",
        "library_version": "1",
        "device": "test",
        "flags": {"threads": 1},
    }


def _entry(
    *,
    activation: list[object] | None = None,
    weight: list[object] | None = None,
    output: list[object] | None = None,
    contract: object = tool.CONTRACT_BLOCKED,
    call_count: object = 1,
) -> dict:
    return {
        "numeric_contract": contract,
        "activation_shape": [1, 8] if activation is None else activation,
        "weight_shape": [4, 8] if weight is None else weight,
        "output_shape": [1, 4] if output is None else output,
        "call_count": call_count,
    }


def _resign(manifest: dict) -> dict:
    manifest.pop("manifest_sha256", None)
    manifest["manifest_sha256"] = tool._association_manifest_digest(manifest)
    return manifest


def _manifest(
    *, entries: list[dict] | None = None, identity: dict | None = None
) -> dict:
    selected_entries = deepcopy([_entry()] if entries is None else entries)
    selected_identity = deepcopy(_identity() if identity is None else identity)
    body = {
        "schema": tool.ASSOCIATION_SCHEMA,
        "association_policy": tool.ASSOCIATION_POLICY,
        "implementation_identity": selected_identity,
        "entries": selected_entries,
        "distinct_association_count": len(selected_entries),
        "blocked_call_count": sum(
            int(entry["call_count"]) for entry in selected_entries
        ),
    }
    return _resign(body)


def test_empty_phase_manifest_is_refused() -> None:
    backend = ObservedBackend()
    tool._begin_association_phase(backend)
    with pytest.raises(tool.BackendError, match="executed no blocked contraction"):
        tool._association_provenance(backend, "empty")


def test_manifest_digest_is_recomputed_by_the_qualification_tool() -> None:
    backend = ObservedBackend()
    backend.record_blocked()
    backend.corrupt_digest = True
    with pytest.raises(tool.BackendError, match="invalid manifest digest"):
        tool._association_provenance(backend, "corrupt")


def test_manifest_with_wrong_contract_is_refused_after_resigning() -> None:
    manifest = _manifest()
    manifest["entries"][0]["numeric_contract"] = tool.CONTRACT_SEQUENTIAL
    _resign(manifest)

    with pytest.raises(tool.BackendError, match="uses the wrong contract"):
        tool._validate_association_manifest(
            manifest, expected_identity=_identity()
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("activation_shape", [1]),
        ("activation_shape", [0, 8]),
        ("activation_shape", [True, 8]),
        ("weight_shape", [4, -1]),
        ("weight_shape", [4, 8, 1]),
        ("output_shape", [1, 1.5]),
    ],
    ids=(
        "rank-one",
        "zero-dimension",
        "boolean-dimension",
        "negative-dimension",
        "rank-three",
        "non-integer-dimension",
    ),
)
def test_manifest_with_invalid_shape_is_refused_after_resigning(
    field: str, value: list[object]
) -> None:
    manifest = _manifest()
    manifest["entries"][0][field] = value
    _resign(manifest)

    with pytest.raises(tool.BackendError, match="has invalid shapes"):
        tool._validate_association_manifest(
            manifest, expected_identity=_identity()
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("weight_shape", [4, 7]),
        ("output_shape", [2, 4]),
    ],
    ids=("incompatible-reduction", "incorrect-output"),
)
def test_manifest_with_incompatible_shapes_is_refused_after_resigning(
    field: str, value: list[int]
) -> None:
    manifest = _manifest()
    manifest["entries"][0][field] = value
    _resign(manifest)

    with pytest.raises(tool.BackendError, match="shapes do not contract"):
        tool._validate_association_manifest(
            manifest, expected_identity=_identity()
        )


def test_manifest_with_zero_entry_call_count_is_refused_after_resigning() -> None:
    manifest = _manifest()
    manifest["entries"][0]["call_count"] = 0
    manifest["blocked_call_count"] = 0
    _resign(manifest)

    with pytest.raises(tool.BackendError, match="invalid call_count"):
        tool._validate_association_manifest(
            manifest, expected_identity=_identity()
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "distinct_association_count",
            2,
            "distinct association count is inconsistent",
        ),
        ("blocked_call_count", 2, "blocked call count is inconsistent"),
    ],
)
def test_manifest_with_inconsistent_aggregate_is_refused_after_resigning(
    field: str, value: int, message: str
) -> None:
    manifest = _manifest()
    manifest[field] = value
    _resign(manifest)

    with pytest.raises(tool.BackendError, match=message):
        tool._validate_association_manifest(
            manifest, expected_identity=_identity()
        )


@pytest.mark.parametrize(
    "field", ("distinct_association_count", "blocked_call_count")
)
@pytest.mark.parametrize("value", (True, 1.0), ids=("boolean", "float"))
def test_manifest_aggregate_counts_must_be_json_integers(
    field: str, value: object
) -> None:
    manifest = _manifest()
    manifest[field] = value
    _resign(manifest)

    with pytest.raises(tool.BackendError, match="count"):
        tool._validate_association_manifest(
            manifest, expected_identity=_identity()
        )


@pytest.mark.parametrize(
    "entries",
    [
        [_entry(), _entry()],
        [
            _entry(activation=[2, 8], weight=[3, 8], output=[2, 3]),
            _entry(activation=[1, 8], weight=[2, 8], output=[1, 2]),
        ],
    ],
    ids=("duplicate", "unsorted"),
)
def test_manifest_entries_must_be_unique_and_canonically_sorted(
    entries: list[dict],
) -> None:
    manifest = _manifest(entries=entries)

    with pytest.raises(tool.BackendError, match="not unique canonical order"):
        tool._validate_association_manifest(
            manifest, expected_identity=_identity()
        )


@pytest.mark.parametrize(
    "identity",
    [{}, {"unavailable": "test backend unavailable"}],
    ids=("empty", "unavailable"),
)
def test_manifest_with_unavailable_identity_is_refused(identity: dict) -> None:
    manifest = _manifest(identity=identity)

    with pytest.raises(tool.BackendError, match="identity is unavailable"):
        tool._validate_association_manifest(
            manifest, expected_identity=identity
        )


@pytest.mark.parametrize("backend_name", tool.backends.available_backends())
def test_representative_case_records_actual_tiled_library_shapes(
    backend_name: str,
) -> None:
    backend = tool.backends.get_backend(backend_name)
    report = tool._case_report(
        backend,
        {"model": "fixture", "operation": "projection", "rows": 2, "k": 8, "n": 5},
        seed=7,
        argmax=False,
        column_tile=3,
    )

    provenance = report["executed_association"]
    assert provenance["phase"] == "case:fixture:projection"
    assert provenance["manifest_sha256"] == provenance["manifest"]["manifest_sha256"]
    assert provenance["manifest"]["blocked_call_count"] == 2
    assert provenance["manifest"]["entries"] == [
        {
            "numeric_contract": tool.CONTRACT_BLOCKED,
            "activation_shape": [2, 8],
            "weight_shape": [2, 8],
            "output_shape": [2, 2],
            "call_count": 1,
        },
        {
            "numeric_contract": tool.CONTRACT_BLOCKED,
            "activation_shape": [2, 8],
            "weight_shape": [3, 8],
            "output_shape": [2, 3],
            "call_count": 1,
        },
    ]


def test_case_observation_interval_does_not_accumulate_previous_shapes() -> None:
    backend = tool.backends.NumpyBackend()
    first = tool._case_report(
        backend,
        {"model": "fixture", "operation": "first", "rows": 2, "k": 8, "n": 5},
        seed=8,
        argmax=False,
        column_tile=3,
    )
    second = tool._case_report(
        backend,
        {"model": "fixture", "operation": "second", "rows": 1, "k": 4, "n": 2},
        seed=9,
        argmax=False,
        column_tile=2,
    )

    assert first["executed_association"]["manifest"]["blocked_call_count"] == 2
    manifest = second["executed_association"]["manifest"]
    assert manifest["blocked_call_count"] == 1
    assert manifest["entries"][0]["activation_shape"] == [1, 4]
    assert manifest["entries"][0]["weight_shape"] == [2, 4]


def test_throughput_excludes_context_warmup_and_includes_real_calibration(
    monkeypatch,
) -> None:
    backend = tool.backends.NumpyBackend()

    stale_left = backend.widen_bf16(np.zeros((3, 2), dtype=np.uint16))
    stale_weight = backend.widen_bf16(np.zeros((5, 2), dtype=np.uint16))
    backend.matmul_binary32(
        stale_left, stale_weight, contract=tool.CONTRACT_BLOCKED
    )

    monkeypatch.setattr(
        tool,
        "_operands",
        lambda *_args, **_kwargs: (
            np.zeros((1, 8), dtype=np.uint16),
            np.zeros((4, 8), dtype=np.uint16),
        ),
    )
    monkeypatch.setattr(tool.backends, "get_backend", lambda _name: backend)

    report = tool._throughput(["numpy"], rows=1)["backends"]["numpy"]
    provenance = report["executed_association"]
    assert provenance["phase"] == "throughput:numpy"
    # The context warmup and deliberately stale call are pre-reset.  The
    # measured end-to-end call plus contraction-only calibration and timed
    # calls all remain in the governed phase.
    assert provenance["manifest"]["blocked_call_count"] == 3
    assert provenance["manifest"]["entries"] == [
        {
            "numeric_contract": tool.CONTRACT_BLOCKED,
            "activation_shape": [1, 8],
            "weight_shape": [4, 8],
            "output_shape": [1, 4],
            "call_count": 3,
        }
    ]


def test_determinism_manifest_is_isolated_and_counts_every_tile(
    monkeypatch,
) -> None:
    backend = tool.backends.NumpyBackend()
    stale_left = backend.widen_bf16(np.zeros((3, 2), dtype=np.uint16))
    stale_weight = backend.widen_bf16(np.zeros((5, 2), dtype=np.uint16))
    backend.matmul_binary32(
        stale_left, stale_weight, contract=tool.CONTRACT_BLOCKED
    )
    monkeypatch.setattr(
        tool,
        "_operands",
        lambda *_args, **_kwargs: (
            np.zeros((2, 8), dtype=np.uint16),
            np.zeros((5, 8), dtype=np.uint16),
        ),
    )

    report = tool._determinism(backend, repeats=3, column_tile=3)

    assert report["bit_identical"] is True
    provenance = report["executed_association"]
    assert provenance["phase"] == "blocked_determinism"
    assert provenance["manifest"]["blocked_call_count"] == 6
    assert provenance["manifest"]["entries"] == [
        {
            "numeric_contract": tool.CONTRACT_BLOCKED,
            "activation_shape": [2, 8],
            "weight_shape": [2, 8],
            "output_shape": [2, 2],
            "call_count": 3,
        },
        {
            "numeric_contract": tool.CONTRACT_BLOCKED,
            "activation_shape": [2, 8],
            "weight_shape": [3, 8],
            "output_shape": [2, 3],
            "call_count": 3,
        },
    ]


def test_reduced_forward_phases_are_isolated(monkeypatch) -> None:
    backend = tool.backends.NumpyBackend()
    monkeypatch.setattr(
        tool,
        "QWEN",
        {"hidden": 4, "vocabulary": 5, "layers": 2, "context": 5},
    )
    monkeypatch.setattr(
        tool,
        "QWEN_LAYER_CONTRACTIONS",
        (("projection", 4, 4), ("down", 6, 3)),
    )
    monkeypatch.setattr(
        tool,
        "_bf16_buffer",
        lambda shape, *_args, **_kwargs: np.zeros(shape, dtype=np.uint16),
    )

    stale_left = backend.widen_bf16(np.zeros((7, 2), dtype=np.uint16))
    stale_weight = backend.widen_bf16(np.zeros((6, 2), dtype=np.uint16))
    backend.matmul_binary32(
        stale_left, stale_weight, contract=tool.CONTRACT_BLOCKED
    )
    first = tool._forward_contractions(
        backend,
        tokens=5,
        row_tile=2,
        contract=tool.CONTRACT_BLOCKED,
        column_tile=3,
        association_phase="forward:first",
    )
    second = tool._forward_contractions(
        backend,
        tokens=1,
        row_tile=1,
        contract=tool.CONTRACT_BLOCKED,
        column_tile=3,
        association_phase="forward:second",
    )

    first_provenance = first["executed_association"]
    assert first_provenance["phase"] == "forward:first"
    assert first_provenance["manifest"]["blocked_call_count"] == 14
    assert any(
        entry["activation_shape"][0] == 2
        for entry in first_provenance["manifest"]["entries"]
    )
    assert all(
        entry["activation_shape"] != [7, 2]
        for entry in first_provenance["manifest"]["entries"]
    )

    second_provenance = second["executed_association"]
    assert second_provenance["phase"] == "forward:second"
    assert second_provenance["manifest"]["blocked_call_count"] == 6
    assert all(
        entry["activation_shape"][0] == 1
        for entry in second_provenance["manifest"]["entries"]
    )


def test_rmsnorm_enforces_and_restores_the_explicit_backend_scope(
    monkeypatch,
) -> None:
    backend = tool.backends.get_backend("numpy")
    previous_selection = "previous-test-selection"
    monkeypatch.setattr(tool.backends, "_selected", previous_selection)
    monkeypatch.setattr(
        tool,
        "_bf16_normal",
        lambda shape, *_args, **_kwargs: np.zeros(shape, dtype=np.uint16),
    )

    def fake_qwen(values, _gains, *, epsilon_code):
        assert epsilon_code == tool.EPSILON_CODE
        return SimpleNamespace(values=np.zeros_like(values))

    observed_backends = []

    def fake_deepseek(values, _gains, *, epsilon_bits):
        assert epsilon_bits == tool.EPSILON_CODE
        observed_backends.append(tool.backends.get_backend())
        return np.zeros_like(values), 0

    monkeypatch.setattr(tool, "qwen_rms_norm_bf16", fake_qwen)
    monkeypatch.setattr(tool, "deepseek_rms_norm_binary32", fake_deepseek)

    report = tool._rmsnorm_report(2, backend)

    assert observed_backends == [backend] * 4
    assert tool.backends.selected_backend_name() == previous_selection
    provenance = report["execution_provenance"]
    assert provenance["backend_scope_enforced"] is True
    assert provenance["deepseek_implementation_identity"] == (
        tool._stable_implementation_identity(backend)
    )
