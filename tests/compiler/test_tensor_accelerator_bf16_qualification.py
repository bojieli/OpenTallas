from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import numpy as np
import pytest

from compiler.tensor_accelerator.bf16_qualification import (
    BF16QualificationError,
    publish_qualification_report,
    qualify_bf16_projection_payloads,
)
from compiler.tensor_accelerator.common import canonical_json_bytes


LOCK_ID = "a" * 64


def _payloads() -> tuple[dict[str, object], bytes, dict[str, object], bytes]:
    input_codes = np.asarray(
        [[0x3F80, 0x4000], [0xBF80, 0x3F00]], dtype="<u2"
    )
    weight_codes = np.asarray(
        [[0x4040, 0x4080], [0xBF80, 0x3F00]], dtype="<u2"
    )
    input_payload = input_codes.tobytes()
    weight_payload = weight_codes.tobytes()
    return (
        {
            "dtype": "BF16",
            "name": "embedding.weight",
            "payload_sha256": hashlib.sha256(input_payload).hexdigest(),
            "shape": [2, 2],
            "size_bytes": len(input_payload),
        },
        input_payload[:4],
        {
            "dtype": "BF16",
            "name": "projection.weight",
            "payload_sha256": hashlib.sha256(weight_payload).hexdigest(),
            "shape": [2, 2],
            "size_bytes": len(weight_payload),
        },
        weight_payload,
    )


def _report() -> dict[str, object]:
    input_record, input_row, weight_record, weight = _payloads()
    return qualify_bf16_projection_payloads(
        checkpoint_lock_id=LOCK_ID,
        input_record=input_record,
        input_row=0,
        input_row_payload=input_row,
        weight_record=weight_record,
        weight_payload=weight,
        selected_rows=[0, 1],
    )


def test_qualification_report_has_exact_known_answer_and_accounting() -> None:
    report = _report()
    assert report["status"] == "pass"
    assert report["selected_reference"] == {
        "output_codes": [0x4130, 0x0000],
        "output_rows": [0, 1],
        "saturated_element_count": 0,
        "status": "exact_match",
    }
    assert report["accounting"] == {
        "accumulation_additions": 4,
        "input_payload_bytes": 4,
        "scalar_multiplications": 4,
        "weight_payload_bytes": 8,
    }
    body = {key: value for key, value in report.items() if key != "report_id"}
    assert report["report_id"] == hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def test_qualification_rejects_payload_shape_and_selection_drift() -> None:
    input_record, input_row, weight_record, weight = _payloads()
    corrupted = bytearray(weight)
    corrupted[0] ^= 1
    with pytest.raises(BF16QualificationError, match="weight payload differs"):
        qualify_bf16_projection_payloads(
            checkpoint_lock_id=LOCK_ID,
            input_record=input_record,
            input_row=0,
            input_row_payload=input_row,
            weight_record=weight_record,
            weight_payload=bytes(corrupted),
            selected_rows=[0, 1],
        )
    with pytest.raises(BF16QualificationError, match="strictly increasing"):
        qualify_bf16_projection_payloads(
            checkpoint_lock_id=LOCK_ID,
            input_record=input_record,
            input_row=0,
            input_row_payload=input_row,
            weight_record=weight_record,
            weight_payload=weight,
            selected_rows=[1, 0],
        )
    mismatched = copy.deepcopy(weight_record)
    mismatched["shape"] = [2, 4]
    with pytest.raises(BF16QualificationError, match="byte size differs"):
        qualify_bf16_projection_payloads(
            checkpoint_lock_id=LOCK_ID,
            input_record=input_record,
            input_row=0,
            input_row_payload=input_row,
            weight_record=mismatched,
            weight_payload=weight,
            selected_rows=[0, 1],
        )


def test_qualification_publication_is_atomic_and_nonoverwriting(tmp_path: Path) -> None:
    report = _report()
    output = tmp_path / "evidence/report.json"
    publish_qualification_report(report, output)
    assert output.read_bytes() == canonical_json_bytes(report)
    before = output.read_bytes()
    with pytest.raises(BF16QualificationError, match="will not be overwritten"):
        publish_qualification_report(report, output)
    assert output.read_bytes() == before
    assert not list(output.parent.glob(".*.tmp"))


def test_publication_rejects_forged_report_identity(tmp_path: Path) -> None:
    report = _report()
    report["selected_reference"]["output_codes"][0] ^= 1
    with pytest.raises(BF16QualificationError, match="identity or status differs"):
        publish_qualification_report(report, tmp_path / "forged.json")
