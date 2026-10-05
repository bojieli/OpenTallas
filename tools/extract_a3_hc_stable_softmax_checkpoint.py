#!/usr/bin/env python3
"""Extract checkpoint-derived HC_PRE combination logits for RTL vectors.

The emitted binary contains *inputs* to stable softmax, never expected RTL
outputs.  It covers the first 512-token prefill block and the final 320-token
block of the governed 200,000-token DeepSeek workload.  Expected softmax words
are generated later by an independent exact-rational oracle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.service_engine.hc_pre_numeric import (  # noqa: E402
    cr32_exp,
    rn32_add,
    rn32_divide,
)
from runtime.sim.engines.deepseek_vector import (  # noqa: E402
    _hc_normalise_and_project,
)
from tools import build_a3_hc_numeric_vectors as numeric_vectors  # noqa: E402
from tools import qualify_deepseek_hbm_hc_pre_t512 as qualification  # noqa: E402


DEFAULT_WORKLOAD = (
    ROOT / "build/workloads/deepseek-v4-flash-0731/TA-DS-CTX-200K-1.json"
)
DEFAULT_SNAPSHOT = qualification.DEFAULT_SNAPSHOT
DEFAULT_OUTPUT = ROOT / "testdata/rtl/a3_hc_stable_softmax"
LOGITS_FILE = "checkpoint_logits.u32le"
MANIFEST_FILE = "checkpoint_logits.json"
EPSILON = 0x358637BD


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def fp32_order_key(code: int) -> int:
    code = 0 if code & 0x7FFFFFFF == 0 else code
    return (~code & 0xFFFFFFFF) if code & 0x80000000 else code | 0x80000000


def stable_softmax_service(logits: Sequence[int]) -> tuple[int, ...]:
    """Independent service-lane sentinel, used only on four retained rows."""

    if len(logits) != 16:
        raise ValueError("one source-major matrix requires sixteen logits")
    output: list[int] = []
    for row_start in range(0, 16, 4):
        row = [int(code) for code in logits[row_start : row_start + 4]]
        maximum = max(row, key=fp32_order_key)
        negative_maximum = 0 if maximum & 0x7FFFFFFF == 0 else maximum ^ 0x80000000
        exponentials = [cr32_exp(rn32_add(code, negative_maximum)) for code in row]
        denominator = rn32_add(
            rn32_add(exponentials[0], exponentials[1]),
            rn32_add(exponentials[2], exponentials[3]),
        )
        output.extend(
            rn32_add(rn32_divide(code, denominator), EPSILON)
            for code in exponentials
        )
    return tuple(output)


def load_workload(path: Path) -> tuple[list[int], dict[str, Any]]:
    raw = path.read_bytes()
    if sha256_bytes(raw) != qualification.WORKLOAD_FILE_SHA256:
        raise ValueError("governed workload file hash drift")
    body = json.loads(raw)
    if body.get("workload_id") != qualification.WORKLOAD_ID:
        raise ValueError("wrong workload ID")
    if body.get("digest") != qualification.WORKLOAD_DIGEST:
        raise ValueError("workload digest drift")
    token_ids = [int(value) for value in body["token_ids"]]
    if len(token_ids) != 200_000:
        raise ValueError("workload must contain exactly 200,000 prompt tokens")
    return token_ids, {
        "workload_id": body["workload_id"],
        "workload_digest": body["digest"],
        "file_sha256": sha256_bytes(raw),
        "prompt_token_count": len(token_ids),
        "rendered_text_sha256": body["rendered_text_sha256"],
    }


def checkpoint_inputs(
    snapshot: Path, token_ids: Sequence[int]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    request = list(token_ids)
    if not 1 <= len(request) <= qualification.TOKEN_COUNT:
        raise ValueError("checkpoint input request must contain 1..512 tokens")
    # The authenticated loader has a fixed 512-row shape and validates the
    # token-18042 embedding sentinel.  Padding is discarded before arithmetic.
    padded = request + [18_042] * (qualification.TOKEN_COUNT - len(request))
    hidden, projection, base, scale, _ = qualification._load_checkpoint(
        snapshot, padded, full_shard_hash=False
    )
    return hidden[: len(request)], projection, base, scale


def combination_logits(
    hidden: np.ndarray,
    projection: np.ndarray,
    base: np.ndarray,
    scale: np.ndarray,
) -> np.ndarray:
    epsilon = np.asarray([EPSILON], dtype=np.uint32).view(np.float32)[0]
    _, mixes = _hc_normalise_and_project(hidden, projection, epsilon)
    logits = np.add(
        np.multiply(
            mixes[:, 8:].reshape(len(hidden), 4, 4),
            scale[2],
            dtype=np.float32,
        ),
        base[8:].reshape(4, 4),
        dtype=np.float32,
    )
    if logits.shape != (len(hidden), 4, 4) or not bool(np.all(np.isfinite(logits))):
        raise ValueError("checkpoint-derived combination logits are malformed")
    return np.ascontiguousarray(logits).view(np.uint32)


def u32le(values: np.ndarray) -> bytes:
    return np.asarray(values, dtype="<u4").tobytes(order="C")


def extract(
    workload_path: Path = DEFAULT_WORKLOAD,
    snapshot: Path = DEFAULT_SNAPSHOT,
    output: Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    token_ids, workload = load_workload(workload_path)
    first_ids = token_ids[:512]
    final_ids = token_ids[-320:]

    first_hidden, projection, base, scale = checkpoint_inputs(snapshot, first_ids)
    first_logits = combination_logits(first_hidden, projection, base, scale)
    final_hidden, final_projection, final_base, final_scale = checkpoint_inputs(
        snapshot, final_ids
    )
    if not (
        np.array_equal(projection, final_projection)
        and np.array_equal(base, final_base)
        and np.array_equal(scale, final_scale)
    ):
        raise ValueError("checkpoint parameter reload drift")
    final_logits = combination_logits(final_hidden, projection, base, scale)

    retained_first_four = numeric_vectors.CHECKPOINT_STABLE_INPUTS
    for position in range(4):
        observed = stable_softmax_service(
            [int(code) for code in first_logits[position].reshape(-1)]
        )
        if observed != retained_first_four[position]:
            raise ValueError(
                f"checkpoint stable-softmax sentinel mismatch at position {position}"
            )

    first_payload = u32le(first_logits)
    final_payload = u32le(final_logits)
    payload = first_payload + final_payload
    first_token_payload = np.asarray(first_ids, dtype="<u4").tobytes()
    final_token_payload = np.asarray(final_ids, dtype="<u4").tobytes()

    source_paths = (
        ROOT / "runtime/sim/engines/deepseek_vector.py",
        ROOT / "runtime/service_engine/hc_pre_numeric.py",
        ROOT / "tools/qualify_deepseek_hbm_hc_pre_t512.py",
        ROOT / "tools/build_a3_hc_numeric_vectors.py",
        ROOT / "tools/extract_a3_hc_stable_softmax_checkpoint.py",
    )
    body: dict[str, Any] = {
        "schema": "opentallas.rtl.a3_hc_stable_softmax_checkpoint_inputs.v1",
        "status": "checkpoint_derived_input_vectors",
        "workload": workload,
        "checkpoint": {
            "repository": qualification.REPOSITORY,
            "revision": qualification.REVISION,
            "projection_sha256": qualification.TENSOR_SHA256[
                "layers.0.hc_attn_fn"
            ],
            "base_sha256": qualification.TENSOR_SHA256[
                "layers.0.hc_attn_base"
            ],
            "scale_sha256": qualification.TENSOR_SHA256[
                "layers.0.hc_attn_scale"
            ],
        },
        "layout": "segment-major source-major matrices; 16 little-endian u32 logits per token",
        "segments": [
            {
                "name": "first_prefill_t512",
                "position_start": 0,
                "token_count": 512,
                "matrix_offset": 0,
                "token_ids_u32le_sha256": sha256_bytes(first_token_payload),
                "logits_u32le_sha256": sha256_bytes(first_payload),
            },
            {
                "name": "final_prefill_t320",
                "position_start": 199_680,
                "token_count": 320,
                "matrix_offset": 512,
                "token_ids_u32le_sha256": sha256_bytes(final_token_payload),
                "logits_u32le_sha256": sha256_bytes(final_payload),
            },
        ],
        "matrix_count": 832,
        "binary_file": LOGITS_FILE,
        "binary_sha256": sha256_bytes(payload),
        "first_four_service_sentinels_match": True,
        "source_sha256": {
            str(path.relative_to(ROOT)): sha256_file(path) for path in source_paths
        },
        "claim_boundary": {
            "checkpoint_derived_softmax_inputs": True,
            "expected_outputs_in_binary": False,
            "full_hc_pre": False,
            "model_token_generation": False,
            "architectural_timing": False,
            "tpot": False,
        },
    }
    body["record_sha256"] = sha256_bytes(canonical(body))
    output.mkdir(parents=True, exist_ok=True)
    (output / LOGITS_FILE).write_bytes(payload)
    (output / MANIFEST_FILE).write_text(
        json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    return body


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workload", type=Path, default=DEFAULT_WORKLOAD)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = extract(args.workload, args.snapshot, args.output)
    print(
        "extracted HC stable-softmax checkpoint inputs: "
        f"{result['matrix_count']} matrices, sha256={result['binary_sha256']}"
    )


if __name__ == "__main__":
    main()
