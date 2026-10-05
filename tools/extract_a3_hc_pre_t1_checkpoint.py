#!/usr/bin/env python3
"""Retain the exact checkpoint inputs for one DeepSeek HC_PRE RTL token.

The selected token is the first token (ID 18042) in the governed
``TA-DS-CTX-200K-1`` workload.  The shipped HC expansion replicates its
authentic 4096-element BF16 embedding over four streams, producing the fixed
16384-element input consumed by HC_PRE.  This tool extracts that input and the
complete layer-zero projection/base/scale tensors from the pinned official
checkpoint without interpreting them as host floating point.

This is an explicit checkpoint-to-vector provenance step.  It performs no RTL
execution, model decoding, EOS check, architectural timing, or TPOT estimate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
TOKEN_ID = 18_042
HIDDEN = 4_096
HC_MULTIPLIER = 4
FLATTENED = HIDDEN * HC_MULTIPLIER
FIELDS = 24

SHARD_1 = "model-00001-of-00048.safetensors"
SHARD_2 = "model-00002-of-00048.safetensors"
SHARD_IDENTITIES = {
    SHARD_1: {
        "bytes": 1_059_061_856,
        "sha256": "f3668ba4cccf1ca6a7eb84e888fb92c1cdc7204d472ba9db771e6fd3abf6b874",
    },
    SHARD_2: {
        "bytes": 3_566_321_192,
        "sha256": "77b26c939a0e25b3113c8d6bb04e1901a748bd4a7d2589e3bfdaabdf1e9bba14",
    },
}
TENSOR_IDENTITIES = {
    "embed.weight": {
        "dtype": "BF16",
        "shape": [129_280, HIDDEN],
        "sha256": "b356e08eaa9457627bbd343805d25374d3ebed7921c1d9ea851ffb8419a9aea3",
    },
    "layers.0.hc_attn_fn": {
        "dtype": "F32",
        "shape": [FIELDS, FLATTENED],
        "sha256": "f5c1ffdfb92df2c04ac17e9a31e38701f2b7a5cac0cd427a2df2aa3e239987fc",
    },
    "layers.0.hc_attn_base": {
        "dtype": "F32",
        "shape": [FIELDS],
        "sha256": "edaa695cf5de59f919415f6e71dcb35be5ad817a06fa7222ee3021d9f388adda",
    },
    "layers.0.hc_attn_scale": {
        "dtype": "F32",
        "shape": [3],
        "sha256": "0b0e327d2f4d1a104c53d6e0a9172cf532028383e82cdf6d70537cb83092c63f",
    },
}
TOKEN_ROW_SHA256 = (
    "f91a7a1b42cf9951ca55ac28f76d55cd6f4c4bfd1a5dbab1ac5bcdb5eb55072c"
)

DEFAULT_SNAPSHOT = (
    Path.home()
    / ".cache/huggingface/hub"
    / "models--deepseek-ai--DeepSeek-V4-Flash-0731"
    / "snapshots"
    / REVISION
)
DEFAULT_OUTPUT = ROOT / "testdata/rtl/a3_hc_pre_t1_checkpoint"
OUTPUT_FILES = ("hidden.hex", "projection.hex", "base.hex", "scale.hex")


class ExtractionError(RuntimeError):
    """The pinned checkpoint or an extracted extent did not authenticate."""


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(16 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ExtractionError(message)


def safetensors_header(path: Path) -> tuple[dict[str, Any], int, str]:
    with path.open("rb") as handle:
        prefix = handle.read(8)
        require(len(prefix) == 8, f"{path}: truncated header length")
        header_bytes = int.from_bytes(prefix, "little")
        require(2 <= header_bytes <= path.stat().st_size - 8, f"{path}: bad header size")
        raw = handle.read(header_bytes)
    require(len(raw) == header_bytes, f"{path}: truncated JSON header")
    try:
        header = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"{path}: malformed safetensors header: {exc}") from exc
    require(isinstance(header, dict), f"{path}: safetensors header is not an object")
    return header, 8 + header_bytes, sha256_bytes(raw)


def tensor_extent(
    path: Path,
    name: str,
    expected_dtype: str,
    expected_shape: list[int],
) -> tuple[int, int, dict[str, object]]:
    header, payload_start, header_sha256 = safetensors_header(path)
    require(name in header, f"{path.name}: missing tensor {name}")
    record = header[name]
    require(isinstance(record, dict), f"{name}: malformed tensor record")
    require(record.get("dtype") == expected_dtype, f"{name}: dtype drift")
    require(record.get("shape") == expected_shape, f"{name}: shape drift")
    offsets = record.get("data_offsets")
    require(
        isinstance(offsets, list) and len(offsets) == 2,
        f"{name}: malformed data offsets",
    )
    start, stop = (int(item) for item in offsets)
    absolute_start = payload_start + start
    absolute_stop = payload_start + stop
    require(
        0 <= start <= stop and absolute_stop <= path.stat().st_size,
        f"{name}: extent outside {path.name}",
    )
    return absolute_start, absolute_stop, {
        "shard": path.name,
        "header_sha256": header_sha256,
        "absolute_offset": absolute_start,
        "bytes": absolute_stop - absolute_start,
    }


def read_exact(path: Path, offset: int, length: int) -> bytes:
    with path.open("rb") as handle:
        handle.seek(offset)
        payload = handle.read(length)
    require(len(payload) == length, f"{path.name}: short read at {offset}")
    return payload


def unpack_words(payload: bytes, width: int) -> tuple[int, ...]:
    require(width in (16, 32), "word width must be 16 or 32")
    step = width // 8
    require(len(payload) % step == 0, "payload is not whole words")
    return tuple(
        int.from_bytes(payload[offset : offset + step], "little")
        for offset in range(0, len(payload), step)
    )


def hex_payload(values: Iterable[int], width: int) -> bytes:
    digits = width // 4
    mask = (1 << width) - 1
    return "".join(f"{int(value) & mask:0{digits}x}\n" for value in values).encode(
        "ascii"
    )


def build(
    snapshot: Path = DEFAULT_SNAPSHOT,
    output: Path = DEFAULT_OUTPUT,
    *,
    full_shard_hash: bool = True,
) -> dict[str, object]:
    shard_paths = {name: snapshot / name for name in SHARD_IDENTITIES}
    shard_records: dict[str, object] = {}
    for name, identity in SHARD_IDENTITIES.items():
        path = shard_paths[name]
        require(path.is_file(), f"missing pinned checkpoint shard {path}")
        require(path.stat().st_size == identity["bytes"], f"{name}: size drift")
        if full_shard_hash:
            require(sha256_file(path) == identity["sha256"], f"{name}: hash drift")
        shard_records[name] = {
            **identity,
            "full_hash_verified": bool(full_shard_hash),
        }

    extents: dict[str, tuple[Path, int, int, dict[str, object]]] = {}
    for name, identity in TENSOR_IDENTITIES.items():
        path = shard_paths[SHARD_1 if name == "embed.weight" else SHARD_2]
        start, stop, record = tensor_extent(
            path,
            name,
            str(identity["dtype"]),
            list(identity["shape"]),
        )
        extents[name] = (path, start, stop, record)

    embed_path, embed_start, embed_stop, embed_record = extents["embed.weight"]
    row_bytes = HIDDEN * 2
    row_offset = embed_start + TOKEN_ID * row_bytes
    require(row_offset + row_bytes <= embed_stop, "selected embedding row is out of range")
    row_raw = read_exact(embed_path, row_offset, row_bytes)
    require(sha256_bytes(row_raw) == TOKEN_ROW_SHA256, "token-18042 row hash drift")
    row_words = unpack_words(row_raw, 16)
    hidden_words = row_words * HC_MULTIPLIER

    retained: dict[str, tuple[tuple[int, ...], int]] = {
        "hidden.hex": (hidden_words, 16),
    }
    tensor_records: dict[str, object] = {
        "embed.weight": {
            **TENSOR_IDENTITIES["embed.weight"],
            **embed_record,
            "selected_row": TOKEN_ID,
            "selected_row_offset": row_offset,
            "selected_row_bytes": row_bytes,
            "selected_row_sha256": TOKEN_ROW_SHA256,
            "hc_expand": "replicate one [4096] row over four streams in stream-major order",
        }
    }
    for tensor_name, filename in (
        ("layers.0.hc_attn_fn", "projection.hex"),
        ("layers.0.hc_attn_base", "base.hex"),
        ("layers.0.hc_attn_scale", "scale.hex"),
    ):
        path, start, stop, extent_record = extents[tensor_name]
        raw = read_exact(path, start, stop - start)
        identity = TENSOR_IDENTITIES[tensor_name]
        require(sha256_bytes(raw) == identity["sha256"], f"{tensor_name}: hash drift")
        retained[filename] = (unpack_words(raw, 32), 32)
        tensor_records[tensor_name] = {
            **identity,
            **extent_record,
        }

    expected_counts = {
        "hidden.hex": FLATTENED,
        "projection.hex": FIELDS * FLATTENED,
        "base.hex": FIELDS,
        "scale.hex": 3,
    }
    output.mkdir(parents=True, exist_ok=True)
    files: dict[str, object] = {}
    for filename in OUTPUT_FILES:
        values, width = retained[filename]
        require(len(values) == expected_counts[filename], f"{filename}: count drift")
        payload = hex_payload(values, width)
        (output / filename).write_bytes(payload)
        files[filename] = {
            "word_bits": width,
            "words": len(values),
            "bytes": len(payload),
            "sha256": sha256_bytes(payload),
        }

    body: dict[str, object] = {
        "schema": "opentallas.rtl.a3_hc_pre_t1_checkpoint.v1",
        "checkpoint": {
            "repository": REPOSITORY,
            "revision": REVISION,
            "snapshot_leaf": snapshot.name,
            "shards": shard_records,
            "tensors": tensor_records,
        },
        "workload_binding": {
            "workload_id": "TA-DS-CTX-200K-1",
            "prompt_token_count": 200_000,
            "position": 0,
            "token_id": TOKEN_ID,
        },
        "geometry": {
            "hidden": [1, HC_MULTIPLIER, HIDDEN],
            "flattened_hidden": FLATTENED,
            "projection": [FIELDS, FLATTENED],
            "base": [FIELDS],
            "scale": [3],
        },
        "files": files,
        "source": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "claim_boundary": {
            "authenticated_checkpoint_input": True,
            "hc_pre_arithmetic": False,
            "rtl_execution": False,
            "model_token_generation": False,
            "eos": False,
            "architectural_timing": False,
            "tpot": False,
        },
    }
    body["manifest_id"] = sha256_bytes(canonical(body))
    (output / "index.json").write_bytes(
        json.dumps(body, indent=2, sort_keys=True).encode("ascii") + b"\n"
    )
    return body


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--skip-full-shard-hash",
        action="store_true",
        help="development-only: trust pinned sizes and tensor hashes",
    )
    args = parser.parse_args()
    result = build(
        args.snapshot,
        args.output,
        full_shard_hash=not args.skip_full_shard_hash,
    )
    print(
        "extracted A3 HC_PRE T=1 checkpoint inputs: "
        f"token={result['workload_binding']['token_id']} "
        f"projection_words={result['files']['projection.hex']['words']}"
    )


if __name__ == "__main__":
    main()
