from __future__ import annotations

import ast
from dataclasses import asdict, fields, replace
import hashlib
import inspect
import json
import os
from pathlib import Path
import struct
from types import MappingProxyType

import pytest

import runtime.reference.dspark_main_project as dspark_reference
import runtime.service_engine.dspark_main_project_numeric as dspark_service
from runtime.reference.matrix import dense_fp8_linear_selected_rows_bf16
from runtime.service_engine.fp8_numeric import execute_selected_rows


_EVIDENCE_ROOT_ENV = "OPENTALLAS_DEEPSEEK_V4_EVIDENCE_ROOT"
_OFFICIAL_SELECTED_ROWS = (0, 127, 128, 4095)
_SYNTHETIC_RECORD_SHA256 = (
    "8a2a512e9a14ba1c7b7e6f753d463eba2d9d94333005d0492206b0732bf8a876"
)
_OFFICIAL_RECORD_SHA256 = (
    "782257f37cfa74289ec796442fcfaef9f94f9f5cb2df76764f40c795b6a6782d"
)
_OFFICIAL_EXTENT_AGGREGATE_SHA256 = (
    "d478a402269b768d8ddc4b00ffa4ae6076bbef009fc50690dc174bbaca868dde"
)


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def _flatten_codes(value: object):
    if type(value) is int:
        yield value
        return
    assert type(value) is tuple
    for item in value:
        yield from _flatten_codes(item)


def _code_sha256(value: object, *, width: int) -> str:
    payload = b"".join(
        code.to_bytes(width, "little") for code in _flatten_codes(value)
    )
    return hashlib.sha256(payload).hexdigest()


def _captures(
    source_tokens: tuple[tuple[tuple[int, ...], ...], ...],
) -> tuple[tuple[tuple[tuple[int, ...], ...], ...], ...]:
    # The fixture uses B=1 and supplies each source as its sequence payload.
    return tuple((tokens,) for tokens in source_tokens)


def _synthetic_fixture() -> tuple[
    tuple[tuple[tuple[tuple[int, ...], ...], ...], ...],
    bytes,
    bytes,
    tuple[int, ...],
]:
    palettes = (
        (0x3F80, 0xBF00, 0x4000, 0xBE80),
        (0x4040, 0xC000, 0x3E80, 0x3F00),
    )
    source_tokens: list[tuple[tuple[int, ...], ...]] = []
    for source in range(dspark_reference.SOURCE_COUNT):
        tokens = []
        for token in range(2):
            row = [0] * dspark_reference.HIDDEN_WIDTH
            positions = (
                0,
                127,
                128,
                1023 + source,
                2048 + 3 * source,
                4095,
            )
            for slot, position in enumerate(positions):
                row[position] = palettes[token][(source + slot) % len(palettes[token])]
            tokens.append(tuple(row))
        source_tokens.append(tuple(tokens))

    weights = bytearray(dspark_reference.WEIGHT_BYTES)
    scales = bytearray(dspark_reference.SCALE_BYTES)
    selected_rows = _OFFICIAL_SELECTED_ROWS
    fp8_codes = (0x38, 0xB8, 0x30, 0x40)
    input_columns = (0, 4096 + 128, 8192 + 4095, 2048)
    for row_index, logical_row in enumerate(selected_rows):
        for slot, input_column in enumerate(input_columns):
            offset = logical_row * dspark_reference.CONCATENATED_WIDTH + input_column
            weights[offset] = fp8_codes[(row_index + slot) % len(fp8_codes)]
            tile = logical_row // 128
            block = input_column // 128
            scales[tile * dspark_reference.REDUCTION_BLOCKS + block] = 0x7F

    norm = [0x3F80] * dspark_reference.OUTPUT_WIDTH
    norm[1] = 0x8000
    norm[0] = 0x3F00
    norm[127] = 0x3FC0
    norm[128] = 0xBF80
    norm[4095] = 0x4000
    return _captures(tuple(source_tokens)), bytes(weights), bytes(scales), tuple(norm)


@pytest.fixture(scope="module")
def synthetic_fixture() -> tuple[
    tuple[tuple[tuple[tuple[int, ...], ...], ...], ...],
    bytes,
    bytes,
    tuple[int, ...],
]:
    return _synthetic_fixture()


def _official_resources() -> tuple[bytes, bytes, tuple[int, ...]]:
    configured = os.environ.get(_EVIDENCE_ROOT_ENV)
    if configured is None:
        pytest.skip(f"set {_EVIDENCE_ROOT_ENV} to run official-payload evidence")
    rank = Path(configured) / "canonical-mp4/ranks/rank-000"
    weight_path = rank / "mtp.0.main_proj.weight.bin"
    scale_path = rank / "mtp.0.main_proj.scale.bin"
    norm_path = rank / "mtp.0.main_norm.weight.bin"
    if not all(path.is_file() for path in (weight_path, scale_path, norm_path)):
        pytest.skip(f"official DSpark resources are unavailable below {rank}")
    weights = weight_path.read_bytes()
    scales = scale_path.read_bytes()
    norm_payload = norm_path.read_bytes()
    assert hashlib.sha256(weights).hexdigest() == dspark_reference.OFFICIAL_WEIGHT_SHA256
    assert hashlib.sha256(scales).hexdigest() == dspark_reference.OFFICIAL_SCALE_SHA256
    assert hashlib.sha256(norm_payload).hexdigest() == (
        dspark_reference.OFFICIAL_NORM_WEIGHT_SHA256
    )
    assert len(norm_payload) == dspark_reference.NORM_WEIGHT_BYTES
    norm = struct.unpack(f"<{dspark_reference.OUTPUT_WIDTH}H", norm_payload)
    return weights, scales, norm


def _zero_captures(token_count: int):
    row = (0,) * dspark_reference.HIDDEN_WIDTH
    return tuple(((row,) * token_count,) for _ in range(dspark_reference.SOURCE_COUNT))


def _assert_result_equal(
    reference: dspark_reference.DSparkMainProjectResult,
    service: dspark_service.DSparkMainProjectServiceResult,
) -> None:
    assert reference.source_layer_ids == service.source_layer_ids
    assert reference.projection_bf16_codes == service.projection_bf16_codes
    assert reference.normalized_bf16_codes == service.normalized_bf16_codes
    assert reference.norm_weight_bf16_codes == service.norm_weight_bf16_codes
    assert (
        reference.mean_square_binary32_codes
        == service.mean_square_binary32_codes
    )
    assert reference.inverse_rms_binary32_codes == service.inverse_rms_binary32_codes
    assert (
        reference.activation_saturated_block_count
        == service.activation_saturated_block_count
    )
    assert (
        reference.projection_saturated_output_count
        == service.projection_saturated_output_count
    )
    assert (
        reference.normalization_saturated_output_count
        == service.normalization_saturated_output_count
    )
    assert asdict(reference.counters) == dict(service.logical_counters)


def _result_record(
    reference: dspark_reference.DSparkMainProjectResult,
    service: dspark_service.DSparkMainProjectServiceResult,
) -> dict[str, object]:
    return {
        "activation_saturations": reference.activation_saturated_block_count,
        "counter_sha256": hashlib.sha256(
            _canonical_bytes(asdict(reference.counters))
        ).hexdigest(),
        "inverse_rms_sha256": _code_sha256(
            reference.inverse_rms_binary32_codes,
            width=4,
        ),
        "mean_square_sha256": _code_sha256(
            reference.mean_square_binary32_codes,
            width=4,
        ),
        "normalized_sha256": _code_sha256(
            reference.normalized_bf16_codes,
            width=2,
        ),
        "normalization_saturations": (
            reference.normalization_saturated_output_count
        ),
        "projection_saturations": reference.projection_saturated_output_count,
        "projection_sha256": _code_sha256(
            reference.projection_bf16_codes,
            width=2,
        ),
        "service_counter_sha256": hashlib.sha256(
            _canonical_bytes(dict(service.logical_counters))
        ).hexdigest(),
        "token_count": reference.counters.token_count,
    }


def test_reference_and_service_are_independent_compositions() -> None:
    reference_source = inspect.getsource(dspark_reference)
    service_source = inspect.getsource(dspark_service)
    assert "runtime.service_engine" not in reference_source
    service_tree = ast.parse(service_source)
    service_import_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(service_tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    service_import_roots.update(
        (node.module or "").split(".", 1)[0]
        for node in ast.walk(service_tree)
        if isinstance(node, ast.ImportFrom) and node.level == 0
    )
    assert service_import_roots.isdisjoint(
        {"compiler", "runtime.reference", "numpy", "torch"}
    )
    assert not any(
        isinstance(node, ast.ImportFrom)
        and (
            node.level > 1
            or (node.module or "").startswith("runtime.reference")
        )
        for node in ast.walk(service_tree)
    )
    assert "from .matrix import" in reference_source
    assert "from .fp8_numeric import" in service_source
    assert "from .normalization import" in reference_source
    assert "from .rms_numeric import" in service_source


def test_complete_sparse_full_shape_composition_matches_every_observable(
    synthetic_fixture,
) -> None:
    captures, weights, scales, norm = synthetic_fixture
    reference = dspark_reference.dspark_main_project_bf16(
        captures,
        weights,
        scales,
        norm,
    )
    service = dspark_service.execute_dspark_main_project_bf16(
        captures,
        weights,
        scales,
        norm,
    )
    _assert_result_equal(reference, service)
    assert any(reference.projection_bf16_codes[0][0])
    assert any(reference.projection_bf16_codes[0][1])
    assert reference.counters.concatenated_width == 12_288
    assert reference.counters.projection_output_width == 4_096
    record = _result_record(reference, service)
    assert hashlib.sha256(_canonical_bytes(record)).hexdigest() == (
        _SYNTHETIC_RECORD_SHA256
    )


def test_source_order_mutation_is_equally_visible_in_both_lanes(
    synthetic_fixture,
) -> None:
    captures, weights, scales, norm = synthetic_fixture
    mutated = (captures[1], captures[0], captures[2])
    reference = dspark_reference.dspark_main_project_bf16(
        mutated,
        weights,
        scales,
        norm,
    )
    service = dspark_service.execute_dspark_main_project_bf16(
        mutated,
        weights,
        scales,
        norm,
    )
    _assert_result_equal(reference, service)
    baseline = dspark_reference.dspark_main_project_bf16(
        captures,
        weights,
        scales,
        norm,
    )
    assert reference.projection_bf16_codes != baseline.projection_bf16_codes
    assert reference.normalized_bf16_codes != baseline.normalized_bf16_codes


def test_both_lanes_validate_complete_resources_before_zero_acceleration(
    synthetic_fixture,
) -> None:
    _, weights, scales, norm = synthetic_fixture
    captures = _zero_captures(1)
    bad_weights = weights[:-1] + b"\x7f"
    for execute, error in (
        (
            dspark_reference.dspark_main_project_bf16,
            dspark_reference.DSparkMainProjectReferenceError,
        ),
        (
            dspark_service.execute_dspark_main_project_bf16,
            dspark_service.DSparkMainProjectServiceNumericError,
        ),
    ):
        with pytest.raises(error, match="forbidden"):
            execute(captures, bad_weights, scales, norm)
        with pytest.raises(error, match="forbidden"):
            execute(captures, weights, scales[:-1] + b"\xff", norm)


def test_service_result_is_deeply_immutable_and_reconciles_public_construction(
    synthetic_fixture,
) -> None:
    result = dspark_service.execute_dspark_main_project_bf16(*synthetic_fixture)
    with pytest.raises(TypeError):
        result.logical_counters["transaction_commits"] = 0  # type: ignore[index]
    with pytest.raises(TypeError):
        result.projection_bf16_codes[0][0][0] = 0  # type: ignore[index]

    forged_projection = (
        (
            (0,) + result.projection_bf16_codes[0][0][1:],
            result.projection_bf16_codes[0][1],
        ),
    )
    with pytest.raises(
        dspark_service.DSparkMainProjectServiceNumericError,
        match="does not reconcile",
    ):
        replace(result, projection_bf16_codes=forged_projection)

    backing = dict(result.logical_counters)
    copied = replace(result, logical_counters=MappingProxyType(backing))
    backing["transaction_commits"] = 0
    assert copied.logical_counters["transaction_commits"] == 1


def test_service_exact_record_type_rejects_subclass_forgery(
    synthetic_fixture,
) -> None:
    result = dspark_service.execute_dspark_main_project_bf16(*synthetic_fixture)

    class DerivedResult(dspark_service.DSparkMainProjectServiceResult):
        pass

    kwargs = {field.name: getattr(result, field.name) for field in fields(result)}
    with pytest.raises(
        dspark_service.DSparkMainProjectServiceNumericError,
        match="exact",
    ):
        DerivedResult(**kwargs)


def test_complete_official_resources_zero_input_match_for_every_bound() -> None:
    weights, scales, norm = _official_resources()
    records = []
    for token_count in range(1, 5):
        captures = _zero_captures(token_count)
        reference = dspark_reference.dspark_main_project_bf16(
            captures,
            weights,
            scales,
            norm,
        )
        service = dspark_service.execute_dspark_main_project_bf16(
            captures,
            weights,
            scales,
            norm,
        )
        _assert_result_equal(reference, service)
        assert reference.projection_bf16_codes == (
            ((0,) * dspark_reference.OUTPUT_WIDTH,) * token_count,
        )
        assert reference.normalized_bf16_codes == reference.projection_bf16_codes
        assert reference.counters.projection_weight_e4m3_values == len(weights)
        assert reference.counters.projection_scale_e8m0_values == len(scales)
        records.append(_result_record(reference, service))
    aggregate = {
        "norm_weight_sha256": dspark_reference.OFFICIAL_NORM_WEIGHT_SHA256,
        "records": records,
        "scale_sha256": hashlib.sha256(scales).hexdigest(),
        "weight_sha256": hashlib.sha256(weights).hexdigest(),
    }
    assert hashlib.sha256(_canonical_bytes(aggregate)).hexdigest() == (
        _OFFICIAL_EXTENT_AGGREGATE_SHA256
    )


def test_selected_official_weight_rows_match_across_scale_tile_boundaries() -> None:
    weights, scales, _ = _official_resources()
    input_row = [0] * dspark_reference.CONCATENATED_WIDTH
    palette = (0x3F80, 0xBF00, 0x4000, 0xBE80, 0x4040, 0xC000)
    for block in range(dspark_reference.REDUCTION_BLOCKS):
        input_row[block * 128 + block % 128] = palette[block % len(palette)]
    input_rows = (tuple(input_row),)

    weight_view = memoryview(weights)
    scale_view = memoryview(scales)
    selected_weights = tuple(
        weight_view[
            logical_row
            * dspark_reference.CONCATENATED_WIDTH : (logical_row + 1)
            * dspark_reference.CONCATENATED_WIDTH
        ]
        for logical_row in _OFFICIAL_SELECTED_ROWS
    )
    scale_rows = tuple(
        scale_view[
            tile
            * dspark_reference.REDUCTION_BLOCKS : (tile + 1)
            * dspark_reference.REDUCTION_BLOCKS
        ]
        for tile in range(dspark_reference.OUTPUT_WIDTH // 128)
    )
    reference = dense_fp8_linear_selected_rows_bf16(
        input_rows,
        selected_weights,
        scale_rows,
        output_row_indices=_OFFICIAL_SELECTED_ROWS,
        declared_output_count=dspark_reference.OUTPUT_WIDTH,
    )

    def weight_row(logical_row: int) -> bytes:
        start = logical_row * dspark_reference.CONCATENATED_WIDTH
        return weights[start : start + dspark_reference.CONCATENATED_WIDTH]

    def scale_code(logical_row: int, block: int) -> int:
        return scales[(logical_row // 128) * dspark_reference.REDUCTION_BLOCKS + block]

    service_values, activation_saturations, output_saturations = execute_selected_rows(
        input_rows,
        selected_rows=_OFFICIAL_SELECTED_ROWS,
        input_features=dspark_reference.CONCATENATED_WIDTH,
        weight_row=weight_row,
        scale_code=scale_code,
    )
    assert reference.values == service_values
    assert reference.activation_saturated_block_count == activation_saturations
    assert reference.output_saturated_element_count == output_saturations
    record = {
        "activation_sha256": _code_sha256(input_rows, width=2),
        "activation_saturations": activation_saturations,
        "output_saturations": output_saturations,
        "output_sha256": _code_sha256(service_values, width=2),
        "scale_sha256": hashlib.sha256(scales).hexdigest(),
        "selected_rows": list(_OFFICIAL_SELECTED_ROWS),
        "selected_weight_sha256": hashlib.sha256(
            b"".join(selected_weights)
        ).hexdigest(),
    }
    assert hashlib.sha256(_canonical_bytes(record)).hexdigest() == (
        _OFFICIAL_RECORD_SHA256
    )
