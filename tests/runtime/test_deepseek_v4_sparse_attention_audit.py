from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools import audit_deepseek_v4_sparse_attention as audit


ROOT = Path(__file__).resolve().parents[2]
REPORT = (
    ROOT
    / "results/model-execution/deepseek-v4-sparse-attention-tilelang018.json"
)
REPORT_SHA256 = "57834785ff91628950e59f90222548f7088d13984366c1ee12f86f1a8edcbc4d"


def _report() -> dict:
    payload = REPORT.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == REPORT_SHA256
    assert payload.endswith(b"\n")
    value = json.loads(payload)
    assert payload == (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    ).encode("ascii")
    return value


def test_sparse_attention_audit_report_has_exact_source_and_environment() -> None:
    report = _report()
    assert report["schema"] == audit.SCHEMA
    assert report["status"] == "bounded_differential_complete"
    assert report["source"] == {
        "kernel_sha256": audit.KERNEL_SOURCE_SHA256,
        "repository": audit.SOURCE_REPOSITORY,
        "revision": audit.SOURCE_REVISION,
    }
    environment = report["environment"]
    assert environment["compute_capability"] == [12, 0]
    assert environment["cuda_compiler"] == (
        "Cuda compilation tools, release 12.8, V12.8.93"
    )
    assert environment["gpu_name"] == (
        "NVIDIA RTX PRO 6000 Blackwell Workstation Edition"
    )
    assert environment["nvidia_driver"] == "595.71.05"
    assert environment["package_versions"] == {
        "apache-tvm-ffi": "0.1.8.post2",
        "tilelang": "0.1.8",
        "torch": "2.10.0+cu128",
        "torch-c-dlpack-ext": "0.1.5",
        "z3-solver": "4.14.1.0",
    }
    wheels = {
        record["filename"]: record["sha256"]
        for record in environment["wheel_artifacts"]
    }
    assert wheels == audit.WHEEL_SHA256


def test_sparse_attention_audit_inputs_regenerate_to_the_committed_hashes() -> None:
    report = _report()
    by_id = {record["id"]: record for record in report["corpora"]}
    for corpus in audit.CORPORA:
        query, kv = audit._build_codes(corpus)
        assert hashlib.sha256(audit._pack_query(query)).hexdigest() == (
            corpus["expected_query_sha256"]
        )
        assert hashlib.sha256(audit._pack_kv(kv)).hexdigest() == (
            corpus["expected_kv_sha256"]
        )
        assert by_id[corpus["id"]]["input"]["query_sha256"] == (
            corpus["expected_query_sha256"]
        )
        assert by_id[corpus["id"]]["input"]["kv_sha256"] == (
            corpus["expected_kv_sha256"]
        )
        assert by_id[corpus["id"]]["input"]["combined_sha256"] == (
            corpus["expected_input_sha256"]
        )


def test_sparse_attention_audit_retains_both_agreement_and_divergence() -> None:
    report = _report()
    exact, broad = report["corpora"]
    assert exact["id"] == "exact_eighths"
    assert exact["output_bf16_value_count"] == 8192
    assert exact["raw_difference_count"] == 0
    assert exact["difference_count_after_positive_zero_canonicalization"] == 0
    assert exact["official_output_sha256"] == exact["reference_output_sha256"]
    assert exact["official_output_sha256"] == (
        "ba327ffb5c554ff940aa0175dd6584c04cdb8b166f345bc466a940f179af9a6b"
    )

    assert broad["id"] == "broad_bf16"
    assert broad["output_bf16_value_count"] == 8192
    assert broad["raw_difference_count"] == 3
    assert broad["difference_count_after_positive_zero_canonicalization"] == 3
    assert broad["official_output_sha256"] == (
        "bb527d4d81562448cbbcaa0af9083f4789de79994090a27d7fc19c1358d3897c"
    )
    assert broad["reference_output_sha256"] == (
        "9f90441e6f04c9beec175c46f27c7794eaf361c12cbe6320f6958783921656b8"
    )
    assert broad["differences"] == [
        {
            "flat_output_index": 5066,
            "official_bf16": "0x3915",
            "reference_bf16": "0x3914",
            "same_sign": True,
            "same_sign_code_steps": 1,
        },
        {
            "flat_output_index": 5651,
            "official_bf16": "0x3c43",
            "reference_bf16": "0x3c44",
            "same_sign": True,
            "same_sign_code_steps": 1,
        },
        {
            "flat_output_index": 6124,
            "official_bf16": "0xbba1",
            "reference_bf16": "0xbba2",
            "same_sign": True,
            "same_sign_code_steps": 1,
        },
    ]


def test_sparse_attention_audit_bytes_and_claim_boundary_are_not_overstated() -> None:
    report = _report()
    sink = report["sink_payload_audit"]
    assert sink == {
        "byte_count": 11_776,
        "negative_count": 264,
        "positive_count": 2_680,
        "sha256": audit.FULL_SINK_SHA256,
        "value_count": 2_944,
        "value_maximum": {
            "binary32_code": "0x401f892c",
            "value": "2.4927473068237305",
        },
        "value_minimum": {
            "binary32_code": "0xc01d58e6",
            "value": "-2.4585509300231934",
        },
        "zero_count": 0,
    }
    for corpus in report["corpora"]:
        counters = corpus["logical_reference_counters"]
        assert counters["valid_selected_rows"] == 12
        assert counters["unique_selected_rows"] == 11
        assert counters["duplicate_selected_rows"] == 1
        assert counters["selected_kv_bf16_values"] == 6_144
        assert counters["selected_kv_read_bytes"] == 12_288
        assert counters["explicit_padding_slots"] == 58
        assert counters["implicit_tail_padding_lanes"] == 58
        assert counters["block_compute_lanes"] == 128
    prohibited = " ".join(report["claim_boundary"]["does_not_establish"])
    assert "service-engine or RTL conformance" in prohibited
    assert "cycles, bandwidth, energy, PPA" in prohibited
    assert "GPU product performance" in prohibited
