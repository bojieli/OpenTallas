#!/usr/bin/env python3
"""Inventory the locally pinned Qwen3-VL MoE FP8 checkpoint for break-even use."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import struct
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs" / "benchmarks" / "local_qwen3_vl_30b_fp8_profile.json"
DEFAULT_OUTPUT = ROOT / "configs" / "benchmarks" / "local_qwen3_vl_30b_fp8_lock.json"
DTYPE_BITS = {"BF16": 16, "F32": 32, "F8_E4M3": 8}
LAYER_RE = re.compile(r"^model\.language_model\.layers\.(\d+)\.")


class ProfileError(RuntimeError):
    """Raised when the local checkpoint violates the governed profile."""


def strict_json(path: Path) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ProfileError(f"duplicate JSON key {key!r} in {path}")
            result[key] = value
        return result

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise ProfileError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProfileError(f"expected an object in {path}")
    return value


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_profile_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != 1:
        raise ProfileError("profile config schema_version must be 1")
    for field in (
        "profile_id",
        "model_repo",
        "revision",
        "endpoint_root",
        "expected",
        "decode_contract",
        "claim_boundary",
    ):
        if field not in config:
            raise ProfileError(f"profile config is missing {field}")
    revision = config["revision"]
    if not isinstance(revision, str) or re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise ProfileError("profile revision must be a 40-character commit hash")
    if not isinstance(config["expected"], dict):
        raise ProfileError("profile expected block must be an object")


def validate_snapshot(snapshot: Path, config: dict[str, Any]) -> None:
    if not snapshot.is_dir():
        raise ProfileError(f"snapshot directory is missing: {snapshot}")
    if snapshot.name != config["revision"]:
        raise ProfileError(
            f"snapshot revision {snapshot.name!r} does not match {config['revision']!r}"
        )
    for name in ("config.json", "model.safetensors.index.json"):
        if not (snapshot / name).is_file():
            raise ProfileError(f"snapshot is missing {name}")


def safetensors_header(path: Path) -> tuple[dict[str, Any], bytes, int]:
    try:
        with path.open("rb") as handle:
            prefix = handle.read(8)
            if len(prefix) != 8:
                raise ProfileError(f"short safetensors prefix in {path}")
            header_length = struct.unpack("<Q", prefix)[0]
            if not 1 < header_length <= 512 * 1024 * 1024:
                raise ProfileError(
                    f"implausible safetensors header length {header_length} in {path}"
                )
            raw = handle.read(header_length)
    except OSError as exc:
        raise ProfileError(f"cannot read safetensors header {path}: {exc}") from exc
    if len(raw) != header_length:
        raise ProfileError(f"short safetensors header in {path}")
    try:
        decoded = json.loads(raw.rstrip(b" \t\r\n\0"))
    except json.JSONDecodeError as exc:
        raise ProfileError(f"invalid safetensors header in {path}: {exc}") from exc
    if not isinstance(decoded, dict):
        raise ProfileError(f"safetensors header is not an object in {path}")
    return decoded, raw, header_length


def tensor_storage_bytes(name: str, tensor: dict[str, Any]) -> int:
    dtype = tensor.get("dtype")
    shape = tensor.get("shape")
    offsets = tensor.get("data_offsets")
    if dtype not in DTYPE_BITS:
        raise ProfileError(f"unsupported tensor dtype {dtype!r} for {name}")
    if not isinstance(shape, list) or not all(
        isinstance(value, int) and not isinstance(value, bool) and value >= 0
        for value in shape
    ):
        raise ProfileError(f"invalid tensor shape for {name}")
    if (
        not isinstance(offsets, list)
        or len(offsets) != 2
        or not all(isinstance(value, int) for value in offsets)
        or offsets[1] < offsets[0]
    ):
        raise ProfileError(f"invalid tensor offsets for {name}")
    storage = offsets[1] - offsets[0]
    elements = math.prod(shape)
    expected_bits = elements * DTYPE_BITS[dtype]
    if expected_bits % 8 or storage != expected_bits // 8:
        raise ProfileError(
            f"tensor storage disagrees with shape/dtype for {name}: "
            f"{storage} bytes versus {expected_bits / 8:g}"
        )
    return storage


def tensor_role(name: str) -> str:
    if name.startswith("model.visual."):
        return "visual_resident_only"
    if name == "model.language_model.embed_tokens.weight":
        return "input_embedding_resident_lookup"
    if name.startswith("model.language_model.layers.") and ".mlp.experts." in name:
        return "text_decode_routed_experts"
    if name.startswith("model.language_model.layers."):
        return "text_decode_dense_layer"
    if name == "lm_head.weight" or name == "model.language_model.norm.weight":
        return "text_decode_dense_unlayered"
    raise ProfileError(f"unclassified checkpoint tensor {name!r}")


def config_value_checks(model_config: dict[str, Any], expected: dict[str, Any]) -> None:
    text = model_config.get("text_config", {})
    quantization = model_config.get("quantization_config", {})
    checks = {
        "architecture": (model_config.get("architectures") or [None])[0],
        "model_type": model_config.get("model_type"),
        "text_model_type": text.get("model_type"),
        "quantization_method": quantization.get("quant_method"),
        "quantization_format": quantization.get("fmt"),
        "activation_scheme": quantization.get("activation_scheme"),
        "text_dtype": text.get("dtype"),
        "num_hidden_layers": text.get("num_hidden_layers"),
        "hidden_size": text.get("hidden_size"),
        "num_attention_heads": text.get("num_attention_heads"),
        "num_key_value_heads": text.get("num_key_value_heads"),
        "head_dim": text.get("head_dim"),
        "num_experts": text.get("num_experts"),
        "num_experts_per_token": text.get("num_experts_per_tok"),
    }
    mismatches = {
        field: {"actual": checks.get(field), "expected": value}
        for field, value in expected.items()
        if field not in {"tensor_count", "shard_count"} and checks.get(field) != value
    }
    if mismatches:
        raise ProfileError(f"model config mismatch: {mismatches}")


def profile(snapshot: Path, profile_config_path: Path) -> dict[str, Any]:
    profile_config = strict_json(profile_config_path)
    validate_profile_config(profile_config)
    validate_snapshot(snapshot, profile_config)
    cache_root = snapshot.parent.parent
    ref_path = cache_root / "refs" / "main"
    if not ref_path.is_file():
        raise ProfileError(f"local cache is missing its main ref: {ref_path}")
    ref_revision = ref_path.read_text(encoding="utf-8").strip()
    snapshot_revisions = sorted(
        path.name for path in snapshot.parent.iterdir() if path.is_dir()
    )
    if ref_revision != profile_config["revision"]:
        raise ProfileError(
            f"local main ref {ref_revision!r} does not select "
            f"{profile_config['revision']!r}"
        )
    if snapshot_revisions != [profile_config["revision"]]:
        raise ProfileError(
            "governed endpoint cache must contain exactly the accounting snapshot; "
            f"found {snapshot_revisions}"
        )
    config_path = snapshot / "config.json"
    index_path = snapshot / "model.safetensors.index.json"
    config_raw = config_path.read_bytes()
    index_raw = index_path.read_bytes()
    try:
        model_config = json.loads(config_raw)
        index = json.loads(index_raw)
    except json.JSONDecodeError as exc:
        raise ProfileError(f"invalid snapshot JSON: {exc}") from exc
    expected = profile_config["expected"]
    config_value_checks(model_config, expected)
    weight_map = index.get("weight_map")
    if not isinstance(weight_map, dict) or not weight_map:
        raise ProfileError("checkpoint index has no weight_map")
    shards = sorted(set(weight_map.values()))
    if len(shards) != int(expected["shard_count"]):
        raise ProfileError(
            f"checkpoint has {len(shards)} shards, expected {expected['shard_count']}"
        )

    tensors: dict[str, dict[str, Any]] = {}
    shard_manifests = []
    for shard in shards:
        shard_path = snapshot / shard
        if not shard_path.is_file():
            raise ProfileError(f"checkpoint shard is missing: {shard}")
        if not shard_path.is_symlink():
            raise ProfileError(
                f"checkpoint shard is not a cache-object symlink: {shard}"
            )
        blob_id = Path(shard_path.readlink()).name
        if re.fullmatch(r"[0-9a-f]{64}", blob_id) is None:
            raise ProfileError(
                f"checkpoint shard has no SHA-256 cache object ID: {shard}"
            )
        header, header_raw, header_length = safetensors_header(shard_path)
        names = []
        payload_bytes = 0
        for name, tensor in header.items():
            if name == "__metadata__":
                continue
            if name in tensors:
                raise ProfileError(f"duplicate tensor {name!r} across shards")
            if not isinstance(tensor, dict):
                raise ProfileError(f"tensor metadata is not an object for {name}")
            storage = tensor_storage_bytes(name, tensor)
            tensors[name] = {
                "dtype": tensor["dtype"],
                "shape": tensor["shape"],
                "storage_bytes": storage,
                "shard": shard,
            }
            names.append(name)
            payload_bytes += storage
        shard_manifests.append(
            {
                "name": shard,
                "cache_blob_sha256": blob_id,
                "cache_blob_identity_semantics": "Hugging Face LFS cache-object name; the 32-GB payload was not rehashed by this metadata profiler",
                "resolved_size_bytes": shard_path.stat().st_size,
                "header_length_bytes": header_length,
                "header_sha256": sha256_bytes(header_raw),
                "tensor_count": len(names),
                "payload_bytes": payload_bytes,
            }
        )
    if set(tensors) != set(weight_map):
        missing = sorted(set(weight_map) - set(tensors))
        extra = sorted(set(tensors) - set(weight_map))
        raise ProfileError(
            f"header/index tensor mismatch: {len(missing)} missing, {len(extra)} extra"
        )
    if any(tensors[name]["shard"] != shard for name, shard in weight_map.items()):
        raise ProfileError("header shard assignment differs from checkpoint index")
    if len(tensors) != int(expected["tensor_count"]):
        raise ProfileError(
            f"checkpoint has {len(tensors)} tensors, expected {expected['tensor_count']}"
        )

    role_bytes: Counter[str] = Counter()
    role_tensor_counts: Counter[str] = Counter()
    dtype_bytes: Counter[str] = Counter()
    dtype_tensor_counts: Counter[str] = Counter()
    layer_role_bytes: dict[int, Counter[str]] = {
        layer: Counter() for layer in range(int(expected["num_hidden_layers"]))
    }
    for name, tensor in tensors.items():
        role = tensor_role(name)
        storage = int(tensor["storage_bytes"])
        role_bytes[role] += storage
        role_tensor_counts[role] += 1
        dtype_bytes[str(tensor["dtype"])] += storage
        dtype_tensor_counts[str(tensor["dtype"])] += 1
        layer_match = LAYER_RE.match(name)
        if layer_match:
            layer = int(layer_match.group(1))
            if layer not in layer_role_bytes:
                raise ProfileError(f"tensor layer {layer} is outside configured range")
            layer_role_bytes[layer][role] += storage

    num_experts = int(expected["num_experts"])
    experts_per_token = int(expected["num_experts_per_token"])
    if not 0 < experts_per_token <= num_experts:
        raise ProfileError("invalid configured expert selection")
    for name, tensor in tensors.items():
        if tensor_role(name) != "text_decode_routed_experts":
            continue
        shape = tensor["shape"]
        if not shape or int(shape[0]) != num_experts:
            raise ProfileError(
                f"expert tensor does not have {num_experts} experts: {name}"
            )
        if int(tensor["storage_bytes"]) * experts_per_token % num_experts:
            raise ProfileError(f"selected expert storage is fractional for {name}")

    routed_selected_bytes = (
        role_bytes["text_decode_routed_experts"] * experts_per_token // num_experts
    )
    dense_active_bytes = (
        role_bytes["text_decode_dense_layer"]
        + role_bytes["text_decode_dense_unlayered"]
    )
    active_immutable_bytes = dense_active_bytes + routed_selected_bytes

    fp8_selected_elements = 0
    bf16_matrix_elements = 0
    for name, tensor in tensors.items():
        role = tensor_role(name)
        elements = math.prod(tensor["shape"])
        if tensor["dtype"] == "F8_E4M3":
            if role == "text_decode_routed_experts":
                fp8_selected_elements += elements * experts_per_token // num_experts
            elif role in {
                "text_decode_dense_layer",
                "text_decode_dense_unlayered",
            }:
                fp8_selected_elements += elements
        elif (
            tensor["dtype"] == "BF16"
            and len(tensor["shape"]) == 2
            and role
            in {
                "text_decode_dense_layer",
                "text_decode_dense_unlayered",
            }
        ):
            bf16_matrix_elements += elements

    text_config = model_config["text_config"]
    kv_bytes_per_context_token = (
        int(text_config["num_hidden_layers"])
        * int(text_config["num_key_value_heads"])
        * int(text_config["head_dim"])
        * 2
        * 2
    )
    checkpoint_bytes = sum(dtype_bytes.values())
    text_image_bytes = checkpoint_bytes - role_bytes["visual_resident_only"]
    result = {
        "schema_version": 1,
        "profile_id": profile_config["profile_id"],
        "status": "pass",
        "model": {
            "repo": profile_config["model_repo"],
            "revision": profile_config["revision"],
            "endpoint_root": profile_config["endpoint_root"],
            "architecture": expected["architecture"],
            "model_type": expected["model_type"],
        },
        "runtime_binding": {
            "endpoint_root": profile_config["endpoint_root"],
            "endpoint_api_revision_attested": False,
            "local_cache_ref": "main",
            "local_cache_ref_revision": ref_revision,
            "local_cache_snapshot_revisions": snapshot_revisions,
            "accounting_snapshot_revision": profile_config["revision"],
            "status": "model-root plus sole default-ref snapshot linked; revision is not API-attested",
        },
        "source_manifests": {
            "profile_config": {
                "path": str(profile_config_path.relative_to(ROOT)),
                "sha256": sha256_file(profile_config_path),
                "size_bytes": profile_config_path.stat().st_size,
            },
            "snapshot_config": {
                "name": "config.json",
                "sha256": sha256_bytes(config_raw),
                "size_bytes": len(config_raw),
            },
            "snapshot_index": {
                "name": "model.safetensors.index.json",
                "sha256": sha256_bytes(index_raw),
                "size_bytes": len(index_raw),
            },
            "shard_headers": shard_manifests,
            "runner": {
                "path": str(Path(__file__).resolve().relative_to(ROOT)),
                "sha256": sha256_file(Path(__file__).resolve()),
                "size_bytes": Path(__file__).resolve().stat().st_size,
            },
        },
        "architecture": {
            key: value
            for key, value in expected.items()
            if key not in {"tensor_count", "shard_count"}
        },
        "checkpoint": {
            "tensor_count": len(tensors),
            "shard_count": len(shards),
            "full_checkpoint_payload_bytes": checkpoint_bytes,
            "text_image_payload_bytes": text_image_bytes,
            "dtype_bytes": dict(sorted(dtype_bytes.items())),
            "dtype_tensor_counts": dict(sorted(dtype_tensor_counts.items())),
            "role_bytes": dict(sorted(role_bytes.items())),
            "role_tensor_counts": dict(sorted(role_tensor_counts.items())),
            "layer_role_bytes": {
                str(layer): dict(sorted(values.items()))
                for layer, values in sorted(layer_role_bytes.items())
            },
        },
        "ordinary_text_decode": {
            "active_immutable_bytes_per_token": active_immutable_bytes,
            "dense_active_bytes_per_token": dense_active_bytes,
            "selected_expert_bytes_per_token": routed_selected_bytes,
            "selected_expert_fraction": experts_per_token / num_experts,
            "matrix_weight_elements_per_token": {
                "fp8_e4m3_dynamic_activation": fp8_selected_elements,
                "bf16": bf16_matrix_elements,
            },
            "matrix_operations_lower_bound_per_token_by_format": {
                "bf16_x_bf16": 2 * bf16_matrix_elements,
                "fp8_e4m3_x_fp8_e4m3": 2 * fp8_selected_elements,
            },
            "matrix_operations_lower_bound_per_token": 2
            * (fp8_selected_elements + bf16_matrix_elements),
            "kv_bytes_per_context_token": kv_bytes_per_context_token,
            "kv_write_bytes_per_generated_token": kv_bytes_per_context_token,
        },
        "decode_contract": profile_config["decode_contract"],
        "claim_boundary": profile_config["claim_boundary"],
    }
    validate_lock(result)
    return result


def validate_lock(lock: dict[str, Any]) -> None:
    if lock.get("schema_version") != 1 or lock.get("status") != "pass":
        raise ProfileError("profile lock must be schema 1 and passing")
    checkpoint = lock.get("checkpoint")
    decode = lock.get("ordinary_text_decode")
    if not isinstance(checkpoint, dict) or not isinstance(decode, dict):
        raise ProfileError("profile lock lacks checkpoint or decode accounting")
    dtype_bytes = checkpoint.get("dtype_bytes")
    role_bytes = checkpoint.get("role_bytes")
    if not isinstance(dtype_bytes, dict) or not isinstance(role_bytes, dict):
        raise ProfileError("profile lock lacks byte classifications")
    full = int(checkpoint["full_checkpoint_payload_bytes"])
    if sum(int(value) for value in dtype_bytes.values()) != full:
        raise ProfileError("dtype bytes do not sum to full checkpoint")
    if sum(int(value) for value in role_bytes.values()) != full:
        raise ProfileError("role bytes do not sum to full checkpoint")
    if full - int(role_bytes["visual_resident_only"]) != int(
        checkpoint["text_image_payload_bytes"]
    ):
        raise ProfileError("text image capacity identity failed")
    operations = decode.get("matrix_operations_lower_bound_per_token_by_format")
    if not isinstance(operations, dict) or sum(
        int(value) for value in operations.values()
    ) != int(decode["matrix_operations_lower_bound_per_token"]):
        raise ProfileError("matrix operation identity failed")
    if int(decode["active_immutable_bytes_per_token"]) != int(
        decode["dense_active_bytes_per_token"]
    ) + int(decode["selected_expert_bytes_per_token"]):
        raise ProfileError("active immutable byte identity failed")
    binding = lock.get("runtime_binding")
    if not isinstance(binding, dict):
        raise ProfileError("profile lock lacks runtime binding")
    if binding.get("endpoint_api_revision_attested") is not False:
        raise ProfileError("endpoint revision must remain explicitly unattested")
    accounting_revision = binding.get("accounting_snapshot_revision")
    if binding.get("local_cache_ref_revision") != accounting_revision or binding.get(
        "local_cache_snapshot_revisions"
    ) != [accounting_revision]:
        raise ProfileError("local cache revision binding is inconsistent")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    result = profile(arguments.snapshot.resolve(), arguments.config.resolve())
    output = arguments.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    try:
        display = output.relative_to(ROOT)
    except ValueError:
        display = output
    print(
        f"wrote {display}: {result['checkpoint']['tensor_count']} tensors, "
        f"{result['checkpoint']['full_checkpoint_payload_bytes'] / 1e9:.3f} GB"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProfileError as exc:
        raise SystemExit(f"local Qwen profile error: {exc}") from exc
