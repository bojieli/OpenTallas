from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = (
    ROOT / "results/model-execution/deepseek-v4-compressor-audit.json"
)
EXPECTED_REPORT_SHA256 = (
    "d14c2b33d9cfc105af9ba3dc18c4ac3b749a203bd0a6b0d3f1d8592315651324"
)


def _report() -> dict:
    payload = REPORT.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == EXPECTED_REPORT_SHA256
    return json.loads(payload)


def test_compressor_audit_is_content_pinned_and_path_independent() -> None:
    from compiler.ir.model import canonical_json_bytes

    report = _report()
    assert REPORT.read_bytes() == canonical_json_bytes(report)
    assert report["schema"] == "opentallas.deepseek_v4_compressor_audit.v1"
    assert report["source"]["repository"] == "deepseek-ai/DeepSeek-V4-Flash-0731"
    assert report["source"]["revision"] == (
        "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
    )
    assert report["source"]["model"]["sha256"] == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    serialized = REPORT.read_text(encoding="ascii")
    assert "/home/" not in serialized
    assert "/tmp/" not in serialized
    assert "timestamp" not in serialized
    assert "elapsed" not in serialized


def test_exact_official_compressor_method_slices_are_retained() -> None:
    methods = {
        record["name"]: record
        for record in _report()["source"]["model"]["method_slices"]
    }
    assert methods == {
        "Compressor": {
            "byte_count": 5484,
            "line_start": 285,
            "line_stop_inclusive": 383,
            "name": "Compressor",
            "sha256": (
                "7d1cc51b4e19ccd10d083d00a57b4fd3e219d65ab17cd72febe328c2c7fb9ef5"
            ),
        },
        "Compressor.forward": {
            "byte_count": 3241,
            "line_start": 322,
            "line_stop_inclusive": 383,
            "name": "Compressor.forward",
            "sha256": (
                "892ce7ca46af7a150a7370253743c33602bb63edd3736960a700756ac38c8bac"
            ),
        },
        "Compressor.overlap_transform": {
            "byte_count": 387,
            "line_start": 313,
            "line_stop_inclusive": 320,
            "name": "Compressor.overlap_transform",
            "sha256": (
                "6b956922a6c32d1c3986e20730a69a81326c5b904e70cd6abf7a6da2775088cd"
            ),
        },
    }


def test_all_released_ape_payloads_are_finite_and_profile_complete() -> None:
    audit = _report()["ape_checkpoint_audit"]
    assert audit["tensor_count"] == 62
    assert audit["finite_value_count"] == 1_418_240
    assert audit["byte_count"] == 5_672_960
    assert audit["aggregate_sha256"] == (
        "ad6333d91c83b72c3fc426ea712b91446ef4020eac1dc39a299d9e56ab288ea4"
    )
    assert audit["negative_value_count"] == 799_732
    assert audit["positive_value_count"] == 618_508
    assert audit["zero_value_count"] == 0
    assert audit["minimum"] == {
        "binary32_code": "0xc0561b5d",
        "flat_tensor_index": 323,
        "tensor": "layers.2.attn.indexer.compressor.ape",
        "value": "-3.3454201221466064",
    }
    assert audit["maximum"] == {
        "binary32_code": "0x3f943acc",
        "flat_tensor_index": 838,
        "tensor": "layers.8.attn.indexer.compressor.ape",
        "value": "1.1580443382263184",
    }
    assert Counter(
        (tuple(record["shape"]), record["tensor_count"])
        for record in audit["profiles"]
    ) == Counter(
        {
            ((4, 256), 21): 1,
            ((4, 1024), 21): 1,
            ((128, 512), 20): 1,
        }
    )
    assert len(audit["tensors"]) == 62
    assert all(record["dtype"] == "F32" for record in audit["tensors"])


def test_bounded_unmodified_method_differentials_are_explicit() -> None:
    reports = {record["id"]: record for record in _report()["method_differentials"]}
    assert set(reports) == {"ape_cancelled_exact", "broad_exact_eighths"}
    exact = reports["ape_cancelled_exact"]
    assert exact["output_bf16_value_count"] == 1024
    assert exact["target_output_sha256"] == (
        "539d6235e9e75c4e4dd051b1dec413a5e21ea4b7670f22f7431141039ba9bcef"
    )
    assert {record["device"] for record in exact["device_results"]} == {
        "cpu",
        "cuda",
    }
    assert all(record["difference_count"] == 0 for record in exact["device_results"])

    broad = reports["broad_exact_eighths"]
    assert broad["seed"] == 0x434F_4D50_4E41_5449
    assert broad["target_output_sha256"] == (
        "545368262c0155f705ba9c5c691df299f5d3de15c0f49ea6da01a175f2294bb9"
    )
    for device in broad["device_results"]:
        assert device["official_output_sha256"] == (
            "e14f1ede0bcf8ed7149cb1eeb52c024a0a520cf7e433a2f0a13ae71ee455adcb"
        )
        assert device["difference_count"] == 1
        assert device["maximum_ordered_encoding_steps"] == 1
        assert device["differences"] == [
            {
                "flat_index": 672,
                "official_bf16": "0x3d08",
                "ordered_encoding_steps": 1,
                "target_bf16": "0x3d09",
            }
        ]


def test_audit_keeps_performance_and_execution_claims_open() -> None:
    boundary = _report()["claim_boundary"]
    assert "exact released compressor APE payload identity and finite range" in (
        boundary["establishes"]
    )
    unresolved = " ".join(boundary["does_not_establish"])
    assert "checkpoint-derived compressor projection inputs" in unresolved
    assert "service-engine or RTL execution" in unresolved
    assert "cycles bandwidth latency energy area PPA or GPU advantage" in unresolved
