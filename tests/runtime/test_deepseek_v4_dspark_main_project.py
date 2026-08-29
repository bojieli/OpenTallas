from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, asdict, fields, replace
import hashlib
import json
from pathlib import Path

import pytest

import runtime.reference.dspark_main_project as dspark


_SNAPSHOT = (
    Path.home()
    / ".cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4-Flash-0731"
    / "snapshots"
    / dspark.OFFICIAL_REVISION
)


def _captures(
    source_rows: tuple[tuple[int, ...], ...],
    *,
    batches: int = 1,
    sequence_length: int = 1,
) -> tuple[tuple[tuple[tuple[int, ...], ...], ...], ...]:
    return tuple(
        tuple(tuple(row for _ in range(sequence_length)) for _ in range(batches))
        for row in source_rows
    )


def _zero_captures(
    *,
    batches: int = 1,
    sequence_length: int = 1,
) -> tuple[tuple[tuple[tuple[int, ...], ...], ...], ...]:
    row = (0,) * dspark.HIDDEN_WIDTH
    return _captures(
        (row,) * dspark.SOURCE_COUNT,
        batches=batches,
        sequence_length=sequence_length,
    )


@pytest.fixture(scope="module")
def zero_resources() -> tuple[bytes, bytes, tuple[int, ...]]:
    return (
        bytes(dspark.WEIGHT_BYTES),
        bytes(dspark.SCALE_BYTES),
        (0x3F80,) * dspark.OUTPUT_WIDTH,
    )


@pytest.fixture(scope="module")
def ordered_resources() -> tuple[bytes, bytes, tuple[int, ...]]:
    weights = bytearray(dspark.WEIGHT_BYTES)
    # E4M3FN 1.0 at output row zero/source-40 column zero and output row
    # one/source-41 column zero makes the concatenation order observable.
    weights[0] = 0x38
    weights[dspark.CONCATENATED_WIDTH + dspark.HIDDEN_WIDTH] = 0x38
    scales = bytearray(dspark.SCALE_BYTES)
    scales[0] = 0x7F
    scales[dspark.HIDDEN_WIDTH // 128] = 0x7F
    return bytes(weights), bytes(scales), (0x3F80,) * dspark.OUTPUT_WIDTH


def test_dspark_main_project_is_bound_to_pinned_source_and_payloads() -> None:
    assert dspark.OFFICIAL_REPOSITORY == "deepseek-ai/DeepSeek-V4-Flash-0731"
    assert dspark.OFFICIAL_REVISION == (
        "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
    )
    assert dspark.MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert dspark.INFERENCE_CONFIG_SHA256 == (
        "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
    )
    assert dspark.CHECKPOINT_LOCK_ID == (
        "30b3d07304b92cb26440e5ea9e28dcb06c835dbf35652529fa9a856da07ad760"
    )
    assert dspark.OFFICIAL_WEIGHT_SHA256 == (
        "1b405d7483945533ca2195df653940e4a536775e1be6cdbd735fc80b9070c9bd"
    )
    assert dspark.OFFICIAL_SCALE_SHA256 == (
        "fa8ca8b8728b715805cd2722d3f27da8e47397d8fe70ebea8dbd38c0753e656b"
    )
    assert dspark.OFFICIAL_NORM_WEIGHT_SHA256 == (
        "c794bc276bb502e0a60f4c817da6c3fd31d3f6b3ad848643d94d9f221771a684"
    )


def test_official_source_order_config_and_expressions_are_frozen() -> None:
    assert dspark.SOURCE_LAYER_IDS == (40, 41, 42)
    assert dspark.CONFIG_EXPECTED_FIELDS == (
        ("dim", 4096),
        ("dtype", "fp8"),
        ("dspark_target_layer_ids", [40, 41, 42]),
    )
    assert dspark.SOURCE_EXPRESSIONS == (
        "if i in self.target_layer_ids:",
        "main_hiddens.append(h.mean(dim=2))",
        "main_hidden = torch.cat(main_hiddens, dim=-1) if main_hiddens else None",
        "main_x = self.main_norm(self.main_proj(main_hidden))",
    )
    source_path = _SNAPSHOT / dspark.MODEL_SOURCE_PATH
    config_path = _SNAPSHOT / dspark.INFERENCE_CONFIG_PATH
    if not source_path.is_file() or not config_path.is_file():
        pytest.skip("pinned official source snapshot is unavailable")
    source_payload = source_path.read_bytes()
    config_payload = config_path.read_bytes()
    assert hashlib.sha256(source_payload).hexdigest() == dspark.MODEL_SOURCE_SHA256
    assert hashlib.sha256(config_payload).hexdigest() == (
        dspark.INFERENCE_CONFIG_SHA256
    )
    source = source_payload.decode("utf-8")
    assert all(expression in source for expression in dspark.SOURCE_EXPRESSIONS)
    config = json.loads(config_payload)
    assert all(config[name] == expected for name, expected in dspark.CONFIG_EXPECTED_FIELDS)


def test_official_shape_dtype_and_transaction_extent_are_complete() -> None:
    assert dspark.SOURCE_COUNT == 3
    assert dspark.HIDDEN_WIDTH == 4096
    assert dspark.CONCATENATED_WIDTH == 12288
    assert dspark.OUTPUT_WIDTH == 4096
    assert dspark.REDUCTION_BLOCKS == 96
    assert dspark.WEIGHT_BYTES == 50_331_648
    assert dspark.SCALE_BYTES == 3_072
    assert dspark.NORM_WEIGHT_BYTES == 8_192
    assert dspark.MAX_TOKENS_PER_TRANSACTION == 4
    assert dspark.NORM_EPSILON_BINARY32 == 0x358637BD


def test_production_reference_has_no_framework_compiler_or_service_dependency() -> None:
    path = Path(dspark.__file__)
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        (node.module or "").split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.level == 0
    )
    assert imported_roots.isdisjoint(
        {"compiler", "decimal", "math", "mpmath", "numpy", "torch"}
    )
    assert "runtime.service_engine" not in source
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "float"
        for node in ast.walk(tree)
    )


def test_nonclaims_keep_logical_work_separate_from_physical_results() -> None:
    assert set(dspark.EXCLUDED_CLAIMS) == {
        "target_hidden_capture_execution",
        "checkpoint_derived_activation",
        "complete_dspark_stage_execution",
        "artifact_driven_service_execution",
        "rtl_execution",
        "physical_schedule",
        "cycles_bandwidth_latency_energy_area_ppa",
        "gpu_performance_advantage",
    }
    names = {field.name for field in fields(dspark.DSparkMainProjectCounters)}
    assert not names & {
        "bytes",
        "cycles",
        "bandwidth",
        "latency",
        "throughput",
        "energy",
        "area",
        "power",
        "ppa",
    }


def test_layer_order_is_visible_at_both_retained_boundaries(
    ordered_resources: tuple[bytes, bytes, tuple[int, ...]],
) -> None:
    source_40 = (0x3F80,) + (0,) * (dspark.HIDDEN_WIDTH - 1)
    source_41 = (0x4000,) + (0,) * (dspark.HIDDEN_WIDTH - 1)
    source_42 = (0,) * dspark.HIDDEN_WIDTH
    weights, scales, norm = ordered_resources
    ordered = dspark.dspark_main_project_bf16(
        _captures((source_40, source_41, source_42)),
        weights,
        scales,
        norm,
    )
    swapped = dspark.dspark_main_project_bf16(
        _captures((source_41, source_40, source_42)),
        weights,
        scales,
        norm,
    )
    assert ordered.projection_bf16_codes[0][0][:2] == (0x3F80, 0x4000)
    assert swapped.projection_bf16_codes[0][0][:2] == (0x4000, 0x3F80)
    assert ordered.projection_bf16_codes != swapped.projection_bf16_codes
    assert ordered.normalized_bf16_codes != swapped.normalized_bf16_codes


def test_zero_path_retains_complete_declared_semantic_work(
    zero_resources: tuple[bytes, bytes, tuple[int, ...]],
) -> None:
    weights, scales, norm = zero_resources
    result = dspark.dspark_main_project_bf16(
        _zero_captures(batches=2, sequence_length=2),
        weights,
        scales,
        norm,
    )
    assert result.projection_bf16_codes == (
        ((0,) * dspark.OUTPUT_WIDTH,) * 2,
    ) * 2
    assert result.normalized_bf16_codes == result.projection_bf16_codes
    assert result.mean_square_binary32_codes == (0,) * 4
    assert result.inverse_rms_binary32_codes == (0x447A0000,) * 4
    counters = result.counters
    assert counters.token_count == 4
    assert counters.capture_input_bf16_values == 4 * 12_288
    assert counters.projection_block_dots == 4 * 4_096 * 96
    assert counters.projection_exact_product_accumulates == 4 * 4_096 * 12_288
    # A canonical padded 96-leaf tree performs 96 additions: the odd
    # 3-element level is padded to four before its final two levels.
    assert counters.projection_cross_block_reduction_adds == 4 * 4_096 * 96
    assert counters.rms_reduction_adds == 4 * (4_096 - 1)
    assert counters.transaction_commits == 1


@pytest.mark.parametrize(
    "captures",
    [
        (),
        (_zero_captures()[0],) * 2,
        (_zero_captures()[0],) * 4,
        tuple(((),) for _ in range(3)),
        tuple((((),),) for _ in range(3)),
    ],
)
def test_malformed_capture_axes_poison_before_commit(captures: object) -> None:
    with pytest.raises(dspark.DSparkMainProjectReferenceError):
        dspark.dspark_main_project_bf16(captures, b"", b"", ())


def test_ragged_and_oversized_capture_axes_poison(
    zero_resources: tuple[bytes, bytes, tuple[int, ...]],
) -> None:
    weights, scales, norm = zero_resources
    row = (0,) * dspark.HIDDEN_WIDTH
    ragged = (
        (((row, row)),),
        (((row,)),),
        (((row, row)),),
    )
    with pytest.raises(dspark.DSparkMainProjectReferenceError, match="rectangular"):
        dspark.dspark_main_project_bf16(ragged, weights, scales, norm)
    with pytest.raises(dspark.DSparkMainProjectReferenceError, match="exceeds"):
        dspark.dspark_main_project_bf16(
            _zero_captures(batches=2, sequence_length=3),
            weights,
            scales,
            norm,
        )


def test_nonfinite_bf16_and_malformed_resources_poison(
    zero_resources: tuple[bytes, bytes, tuple[int, ...]],
) -> None:
    weights, scales, norm = zero_resources
    bad_row = (0x7F80,) + (0,) * (dspark.HIDDEN_WIDTH - 1)
    with pytest.raises(dspark.DSparkMainProjectReferenceError, match="finite BF16"):
        dspark.dspark_main_project_bf16(
            _captures((bad_row,) + ((0,) * dspark.HIDDEN_WIDTH,) * 2),
            weights,
            scales,
            norm,
        )
    with pytest.raises(dspark.DSparkMainProjectReferenceError, match="immutable bytes"):
        dspark.dspark_main_project_bf16(_zero_captures(), bytearray(weights), scales, norm)
    with pytest.raises(dspark.DSparkMainProjectReferenceError, match="length"):
        dspark.dspark_main_project_bf16(_zero_captures(), weights[:-1], scales, norm)
    with pytest.raises(dspark.DSparkMainProjectReferenceError, match="length"):
        dspark.dspark_main_project_bf16(_zero_captures(), weights, scales[:-1], norm)
    bad_norm = (0x7FC0,) + norm[1:]
    with pytest.raises(dspark.DSparkMainProjectReferenceError, match="finite BF16"):
        dspark.dspark_main_project_bf16(_zero_captures(), weights, scales, bad_norm)


def test_forbidden_fp8_and_scale_codes_poison_even_on_zero_input(
    zero_resources: tuple[bytes, bytes, tuple[int, ...]],
) -> None:
    weights, scales, norm = zero_resources
    for forbidden in (0x7F, 0xFF):
        bad_weights = bytearray(weights)
        bad_weights[-1] = forbidden
        with pytest.raises(dspark.DSparkMainProjectReferenceError, match="forbidden"):
            dspark.dspark_main_project_bf16(
                _zero_captures(), bytes(bad_weights), scales, norm
            )
    bad_scales = bytearray(scales)
    bad_scales[-1] = 0xFF
    with pytest.raises(dspark.DSparkMainProjectReferenceError, match="forbidden"):
        dspark.dspark_main_project_bf16(
            _zero_captures(), weights, bytes(bad_scales), norm
        )


def test_resource_hash_helper_validates_before_hashing(
    zero_resources: tuple[bytes, bytes, tuple[int, ...]],
) -> None:
    weights, scales, norm = zero_resources
    identities = dspark.official_resource_hashes(weights, scales, norm)
    assert identities == {
        "norm_weight_sha256": hashlib.sha256(b"\x80\x3f" * 4096).hexdigest(),
        "scale_sha256": hashlib.sha256(scales).hexdigest(),
        "weight_sha256": hashlib.sha256(weights).hexdigest(),
    }
    with pytest.raises(dspark.DSparkMainProjectReferenceError, match="length"):
        dspark.official_resource_hashes(weights[:-1], scales, norm)
    bad_scale = scales[:-1] + b"\xff"
    with pytest.raises(dspark.DSparkMainProjectReferenceError, match="forbidden"):
        dspark.official_resource_hashes(weights, bad_scale, norm)


def test_intermediate_binary32_overflow_poisons_the_transaction() -> None:
    row = (0x7F7F,) + (0,) * (dspark.HIDDEN_WIDTH - 1)
    weights = bytearray(dspark.WEIGHT_BYTES)
    weights[0] = 0x7E
    scales = bytearray(dspark.SCALE_BYTES)
    scales[0] = 0xFE
    with pytest.raises(dspark.DSparkMainProjectReferenceError, match="overflow"):
        dspark.dspark_main_project_bf16(
            _captures((row,) + ((0,) * dspark.HIDDEN_WIDTH,) * 2),
            bytes(weights),
            bytes(scales),
            (0x3F80,) * dspark.OUTPUT_WIDTH,
        )


def test_result_is_deeply_immutable_and_constructor_reconciles_rms(
    zero_resources: tuple[bytes, bytes, tuple[int, ...]],
) -> None:
    result = dspark.dspark_main_project_bf16(
        _zero_captures(),
        *zero_resources,
    )
    with pytest.raises(FrozenInstanceError):
        result.numeric_profile = "forged"  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.projection_bf16_codes[0][0][0] = 1  # type: ignore[index]
    forged_normalized = (
        ((1,) + result.normalized_bf16_codes[0][0][1:],),
    )
    with pytest.raises(dspark.DSparkMainProjectReferenceError, match="does not reconcile"):
        replace(result, normalized_bf16_codes=forged_normalized)
    with pytest.raises(dspark.DSparkMainProjectReferenceError, match="sequence extent"):
        replace(result, projection_bf16_codes=((),))
    with pytest.raises(dspark.DSparkMainProjectReferenceError, match="counters"):
        replace(result.counters, transaction_commits=0)


def test_exact_record_types_reject_subclass_forgery(
    zero_resources: tuple[bytes, bytes, tuple[int, ...]],
) -> None:
    result = dspark.dspark_main_project_bf16(_zero_captures(), *zero_resources)

    class DerivedResult(dspark.DSparkMainProjectResult):
        pass

    kwargs = {field.name: getattr(result, field.name) for field in fields(result)}
    with pytest.raises(dspark.DSparkMainProjectReferenceError, match="exact"):
        DerivedResult(**kwargs)


def test_counter_record_matches_public_serialization(
    zero_resources: tuple[bytes, bytes, tuple[int, ...]],
) -> None:
    result = dspark.dspark_main_project_bf16(_zero_captures(), *zero_resources)
    values = asdict(result.counters)
    assert values["transaction_commits"] == 1
    assert values["projection_weight_e4m3_values"] == dspark.WEIGHT_BYTES
    assert values["projection_scale_e8m0_values"] == dspark.SCALE_BYTES
