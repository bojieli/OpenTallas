"""Profile public checkpoints without downloading their tensor payloads.

Safetensors places a JSON tensor table at the beginning of every shard.  Two
small HTTP range reads per shard are enough to recover exact shapes, dtypes, and
storage offsets.  This makes metadata profiling of a multi-terabyte checkpoint
practical on a CPU workstation while never claiming to have executed the model.
"""

from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .schema import AttentionGroup, ModelProfile


HF_BASE = "https://huggingface.co"
USER_AGENT = "OpenTallas/0.1 checkpoint-metadata-profiler"


@dataclass(frozen=True)
class SourceSpec:
    slug: str
    repo: str
    revision: str
    adapter: str
    total_parameters: float
    active_parameters: float


SOURCES: tuple[SourceSpec, ...] = (
    SourceSpec(
        slug="deepseek-v4-flash-0731",
        repo="deepseek-ai/DeepSeek-V4-Flash-0731",
        revision="7872f01b1d1fe23eabc4c98b48bffcef5a386062",
        adapter="deepseek_v4",
        total_parameters=284e9,
        active_parameters=13e9,
    ),
    SourceSpec(
        slug="deepseek-v4-pro-0813",
        repo="deepseek-ai/DeepSeek-V4-Pro-0813",
        revision="72e1d3230f6c080a530b0a1d46f8eb4602340597",
        adapter="deepseek_v4",
        total_parameters=1.6e12,
        active_parameters=49e9,
    ),
    SourceSpec(
        slug="kimi-k3",
        repo="moonshotai/Kimi-K3",
        revision="a590ce090cb049c93a33dfe8c208ec652aa20503",
        adapter="kimi_k3",
        total_parameters=2.8e12,
        active_parameters=104e9,
    ),
    SourceSpec(
        slug="qwen3-8b",
        repo="Qwen/Qwen3-8B",
        revision="b968826d9c46dd6066d109eabc6255188de91218",
        adapter="qwen3",
        # Exact BF16 tensor count published by the official Hugging Face API;
        # the header inventory independently checks bytes == 2 * parameters.
        total_parameters=8_190_735_360,
        # Ordinary decode streams every BF16 tensor except the input embedding
        # lookup: 15,136,811,008 bytes / 2 bytes per parameter.
        active_parameters=7_568_405_504,
    ),
)


@dataclass(frozen=True)
class Inventory:
    repo: str
    revision: str
    checkpoint_bytes: int
    header_storage_bytes: int
    tensor_count: int
    shard_count: int
    dense_bytes: int
    routed_bytes: int
    decode_dense_bytes: int
    decode_routed_bytes: int
    draft_dense_bytes: int
    draft_routed_bytes: int
    resident_only_bytes: int
    dtype_bytes: dict[str, int]
    dtype_tensor_counts: dict[str, int]
    layer_dense_bytes: dict[str, int]
    layer_routed_bytes: dict[str, int]
    decode_layer_dense_bytes: dict[str, int]
    decode_layer_routed_bytes: dict[str, int]
    index_sha256: str
    config_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _request_bytes(url: str, byte_range: tuple[int, int] | None = None, retries: int = 4) -> bytes:
    headers = {"User-Agent": USER_AGENT}
    if byte_range is not None:
        headers["Range"] = f"bytes={byte_range[0]}-{byte_range[1]}"
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = Request(url, headers=headers)
            with urlopen(request, timeout=60) as response:
                status = getattr(response, "status", response.getcode())
                if byte_range is not None and status != 206:
                    raise RuntimeError(
                        f"server ignored Range for {url} (HTTP {status}); refusing full shard"
                    )
                return response.read()
        except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
            last_error = exc
            if attempt + 1 == retries:
                break
            time.sleep(0.5 * 2**attempt)
    raise RuntimeError(f"failed to fetch {url}: {last_error}") from last_error


def _cached_json(url: str, path: Path) -> tuple[dict[str, Any], bytes]:
    if path.exists():
        raw = path.read_bytes()
    else:
        raw = _request_bytes(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return json.loads(raw), raw


def _shard_header(repo: str, revision: str, shard: str, cache_dir: Path) -> dict[str, Any]:
    cached = cache_dir / "headers" / repo.replace("/", "--") / revision / f"{shard}.json"
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))
    url = f"{HF_BASE}/{repo}/resolve/{revision}/{shard}"
    prefix = _request_bytes(url, (0, 7))
    if len(prefix) != 8:
        raise RuntimeError(f"invalid safetensors prefix for {shard}: {len(prefix)} bytes")
    header_len = struct.unpack("<Q", prefix)[0]
    if header_len <= 1 or header_len > 512 * 1024 * 1024:
        raise RuntimeError(f"implausible safetensors header length {header_len} in {shard}")
    raw = _request_bytes(url, (8, 8 + header_len - 1))
    if len(raw) != header_len:
        raise RuntimeError(f"short safetensors header for {shard}")
    header = json.loads(raw.rstrip(b" \t\r\n\0"))
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(header, separators=(",", ":")), encoding="utf-8")
    return header


_LAYER_RE = re.compile(r"(?:^|\.)layers\.(\d+)(?:\.|$)")


def _is_routed(name: str) -> bool:
    return bool(
        re.search(r"(?:^|\.)(?:experts)\.\d+(?:\.|$)", name)
        and (".ffn." in name or ".block_sparse_moe." in name)
    )


def _weight_role(adapter: str, name: str) -> str:
    """Classify how a tensor participates in text decode.

    Physical dense/routed inventory is retained separately.  This role split
    prevents embedding tables, multimodal front ends, and optional MTP draft
    blocks from being counted as full-array reads on every target token.
    """

    if adapter == "deepseek_v4":
        if name.startswith("mtp."):
            return "draft_routed" if _is_routed(name) else "draft_dense"
        if name == "embed.weight" or ".tid2eid" in name:
            return "resident_only"
    elif adapter == "kimi_k3":
        if (
            name == "language_model.model.embed_tokens.weight"
            or name.startswith("vision_tower.")
            or name.startswith("mm_projector.")
        ):
            return "resident_only"
    elif adapter == "qwen3":
        # The input embedding is a lookup, while the checkpoint has a separate,
        # untied LM head that is a full ordinary-decode projection.
        if name == "model.embed_tokens.weight":
            return "resident_only"
    return "decode_routed" if _is_routed(name) else "decode_dense"


def profile_checkpoint(spec: SourceSpec, cache_dir: Path, workers: int = 8) -> tuple[dict, Inventory]:
    root = cache_dir / "metadata" / spec.slug / spec.revision
    config_url = f"{HF_BASE}/{spec.repo}/resolve/{spec.revision}/config.json"
    index_url = f"{HF_BASE}/{spec.repo}/resolve/{spec.revision}/model.safetensors.index.json"
    config, config_raw = _cached_json(config_url, root / "config.json")
    index, index_raw = _cached_json(index_url, root / "model.safetensors.index.json")
    weight_map = index.get("weight_map", {})
    shards = sorted(set(weight_map.values()))
    if not shards:
        raise RuntimeError(f"{spec.repo} has no sharded safetensors weight map")

    headers: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {
            pool.submit(_shard_header, spec.repo, spec.revision, shard, cache_dir): shard
            for shard in shards
        }
        for future in as_completed(futures):
            headers[futures[future]] = future.result()

    dense = routed = header_storage = tensor_count = 0
    decode_dense = decode_routed = 0
    draft_dense = draft_routed = resident_only = 0
    dtype_bytes: dict[str, int] = defaultdict(int)
    dtype_counts: dict[str, int] = defaultdict(int)
    layer_dense: dict[str, int] = defaultdict(int)
    layer_routed: dict[str, int] = defaultdict(int)
    decode_layer_dense: dict[str, int] = defaultdict(int)
    decode_layer_routed: dict[str, int] = defaultdict(int)
    names: set[str] = set()
    for shard in shards:
        for name, tensor in headers[shard].items():
            if name == "__metadata__":
                continue
            offsets = tensor.get("data_offsets")
            if not offsets or len(offsets) != 2:
                raise RuntimeError(f"tensor {name} lacks data offsets")
            storage = int(offsets[1]) - int(offsets[0])
            if storage < 0:
                raise RuntimeError(f"negative tensor size for {name}")
            tensor_count += 1
            header_storage += storage
            names.add(name)
            dtype = str(tensor.get("dtype", "UNKNOWN"))
            dtype_bytes[dtype] += storage
            dtype_counts[dtype] += 1
            layer_match = _LAYER_RE.search(name)
            layer = layer_match.group(1) if layer_match else None
            if _is_routed(name):
                routed += storage
                if layer is not None:
                    layer_routed[layer] += storage
            else:
                dense += storage
                if layer is not None:
                    layer_dense[layer] += storage
            role = _weight_role(spec.adapter, name)
            if role == "decode_dense":
                decode_dense += storage
                if layer is not None:
                    decode_layer_dense[layer] += storage
            elif role == "decode_routed":
                decode_routed += storage
                if layer is not None:
                    decode_layer_routed[layer] += storage
            elif role == "draft_dense":
                draft_dense += storage
            elif role == "draft_routed":
                draft_routed += storage
            elif role == "resident_only":
                resident_only += storage
            else:  # pragma: no cover - defensive against future role additions
                raise RuntimeError(f"unknown weight role {role!r}")

    missing = set(weight_map) - names
    extra = names - set(weight_map)
    if missing or extra:
        raise RuntimeError(
            f"header/index mismatch for {spec.repo}: {len(missing)} missing, {len(extra)} extra"
        )
    expected = int(index.get("metadata", {}).get("total_size", 0))
    if expected and header_storage != expected:
        raise RuntimeError(
            f"storage sum mismatch for {spec.repo}: headers={header_storage}, index={expected}"
        )
    inventory = Inventory(
        repo=spec.repo,
        revision=spec.revision,
        checkpoint_bytes=expected or header_storage,
        header_storage_bytes=header_storage,
        tensor_count=tensor_count,
        shard_count=len(shards),
        dense_bytes=dense,
        routed_bytes=routed,
        decode_dense_bytes=decode_dense,
        decode_routed_bytes=decode_routed,
        draft_dense_bytes=draft_dense,
        draft_routed_bytes=draft_routed,
        resident_only_bytes=resident_only,
        dtype_bytes=dict(sorted(dtype_bytes.items())),
        dtype_tensor_counts=dict(sorted(dtype_counts.items())),
        layer_dense_bytes=dict(sorted(layer_dense.items(), key=lambda pair: int(pair[0]))),
        layer_routed_bytes=dict(sorted(layer_routed.items(), key=lambda pair: int(pair[0]))),
        decode_layer_dense_bytes=dict(
            sorted(decode_layer_dense.items(), key=lambda pair: int(pair[0]))
        ),
        decode_layer_routed_bytes=dict(
            sorted(decode_layer_routed.items(), key=lambda pair: int(pair[0]))
        ),
        index_sha256=hashlib.sha256(index_raw).hexdigest(),
        config_sha256=hashlib.sha256(config_raw).hexdigest(),
    )
    return config, inventory


def _deepseek_profile(spec: SourceSpec, config: dict, inventory: Inventory) -> ModelProfile:
    layers = int(config["num_hidden_layers"])
    ratios = tuple(int(value) for value in config["compress_ratios"][:layers])
    window = int(config["sliding_window"])
    head_dim = int(config["head_dim"])
    rope_dim = int(config["qk_rope_head_dim"])
    # Official B300 serving recipe: FP8 main KV, BF16 RoPE dimensions, one
    # E8M0 scale per 64 FP8 values; FP4 index cache with one scale per 32.
    main_entry_bytes = (head_dim - rope_dim) + 2 * rope_dim + math.ceil((head_dim - rope_dim) / 64)
    index_dim = int(config["index_head_dim"])
    index_entry_bytes = index_dim / 2 + math.ceil(index_dim / 32)
    counts = {ratio: ratios.count(ratio) for ratio in set(ratios)}
    groups: list[AttentionGroup] = []
    if counts.get(0):
        groups.append(
            AttentionGroup(
                kind="window",
                count=counts[0],
                entry_bytes=main_entry_bytes,
                window_tokens=window,
                label="window",
                evidence="derived from official config and serving recipe",
            )
        )
    if counts.get(4):
        groups.append(
            AttentionGroup(
                kind="compressed_sparse",
                count=counts[4],
                entry_bytes=main_entry_bytes,
                window_tokens=window,
                compression_ratio=4,
                top_k=int(config["index_topk"]),
                index_entry_bytes=index_entry_bytes,
                label="csa",
                evidence="derived from official inference implementation",
            )
        )
    for ratio in sorted(value for value in counts if value not in {0, 4}):
        groups.append(
            AttentionGroup(
                kind="compressed_dense",
                count=counts[ratio],
                entry_bytes=main_entry_bytes,
                window_tokens=window,
                compression_ratio=ratio,
                label=f"hca-{ratio}",
                evidence="derived from official inference implementation",
            )
        )
    sequence = ["window" if ratio == 0 else "csa" if ratio == 4 else f"hca-{ratio}" for ratio in ratios]
    return ModelProfile(
        name=spec.repo.split("/")[-1],
        source_repo=spec.repo,
        source_revision=spec.revision,
        total_parameters=spec.total_parameters,
        active_parameters=spec.active_parameters,
        checkpoint_bytes=inventory.checkpoint_bytes,
        dense_weight_bytes=inventory.decode_dense_bytes,
        routed_weight_bytes=inventory.decode_routed_bytes,
        draft_dense_weight_bytes=inventory.draft_dense_bytes,
        draft_routed_weight_bytes=inventory.draft_routed_bytes,
        resident_only_weight_bytes=inventory.resident_only_bytes,
        num_layers=layers,
        num_experts=int(config["n_routed_experts"]),
        experts_per_token=int(config["num_experts_per_tok"]),
        hidden_size=int(config["hidden_size"]),
        max_context_tokens=int(config["max_position_embeddings"]),
        attention_groups=tuple(groups),
        layer_dense_weight_bytes=tuple(
            inventory.decode_layer_dense_bytes.get(str(layer), 0)
            for layer in range(layers)
        ),
        layer_routed_weight_bytes=tuple(
            inventory.decode_layer_routed_bytes.get(str(layer), 0)
            for layer in range(layers)
        ),
        router_trace_status="synthetic except exact hash tables; no production activations",
        metadata={
            "adapter": "deepseek_v4",
            "attention_sequence": sequence,
            "checkpoint_inventory": f"data/inventory/{spec.slug}.json",
            "kv_cache_policy": "FP8 main + BF16 RoPE; FP4 index",
            "kv_cache_policy_status": "published serving recipe plus derived scale overhead",
            "num_hash_layers": int(config.get("num_hash_layers", 0)),
            "weight_traffic_policy": "main decode streamed; MTP charged only under speculation; embeddings/hash tables resident-only",
            "index_heads": int(config["index_n_heads"]),
            "index_head_dim": index_dim,
            "index_topk": int(config["index_topk"]),
        },
    )


def _kimi_profile(spec: SourceSpec, config: dict, inventory: Inventory) -> ModelProfile:
    text = config["text_config"]
    linear = text["linear_attn_config"]
    layers = int(text["num_hidden_layers"])
    kda_ids = {int(value) - 1 for value in linear["kda_layers"]}
    kda_count = len(kda_ids)
    mla_count = layers - kda_count
    heads = int(linear["num_heads"])
    state_dim = int(linear["head_dim"])
    conv_kernel = int(linear["short_conv_kernel_size"])
    # FLA recurrent kernels retain an FP32 [heads,d,d] state. Three BF16 short
    # convolution histories are included. This is a conservative CPU-code-based
    # traffic model and remains a sensitivity input until hardware profiling.
    recurrent_state_bytes = (
        heads * state_dim * state_dim * 4
        + 3 * heads * state_dim * max(0, conv_kernel - 1) * 2
    )
    latent_dims = int(text["kv_lora_rank"]) + int(text["qk_rope_head_dim"])
    # Production comparison assumes an optimized absorbed-MLA cache in FP8.
    # The reference Transformers implementation expands K/V in BF16 and is
    # retained as a pessimistic sensitivity case rather than the baseline.
    mla_entry_bytes = float(latent_dims)
    groups = (
        AttentionGroup(
            kind="recurrent",
            count=kda_count,
            recurrent_state_bytes=recurrent_state_bytes,
            label="kda",
            evidence="derived from official KDA state shapes; precision assumed FP32/BF16",
        ),
        AttentionGroup(
            kind="dense_mla",
            count=mla_count,
            entry_bytes=mla_entry_bytes,
            label="gated-mla",
            evidence="optimized latent cache; FP8 precision is an explicit assumption",
        ),
    )
    sequence = ["kda" if layer in kda_ids else "gated-mla" for layer in range(layers)]
    return ModelProfile(
        name="Kimi-K3",
        source_repo=spec.repo,
        source_revision=spec.revision,
        total_parameters=spec.total_parameters,
        active_parameters=spec.active_parameters,
        checkpoint_bytes=inventory.checkpoint_bytes,
        dense_weight_bytes=inventory.decode_dense_bytes,
        routed_weight_bytes=inventory.decode_routed_bytes,
        draft_dense_weight_bytes=inventory.draft_dense_bytes,
        draft_routed_weight_bytes=inventory.draft_routed_bytes,
        resident_only_weight_bytes=inventory.resident_only_bytes,
        num_layers=layers,
        num_experts=int(text["num_experts"]),
        experts_per_token=int(text["num_experts_per_token"]),
        hidden_size=int(text["hidden_size"]),
        max_context_tokens=int(text["max_position_embeddings"]),
        attention_groups=groups,
        layer_dense_weight_bytes=tuple(
            inventory.decode_layer_dense_bytes.get(str(layer), 0)
            for layer in range(layers)
        ),
        layer_routed_weight_bytes=tuple(
            inventory.decode_layer_routed_bytes.get(str(layer), 0)
            for layer in range(layers)
        ),
        router_trace_status="synthetic; no production activations",
        metadata={
            "adapter": "kimi_k3",
            "attention_sequence": sequence,
            "checkpoint_inventory": f"data/inventory/{spec.slug}.json",
            "kv_cache_policy": "FP32 KDA recurrent state + optimized FP8 latent MLA",
            "kv_cache_policy_status": "mixed derived/assumed; swept in sensitivity analysis",
            "full_attention_layers": mla_count,
            "kda_layers": kda_count,
            "weight_traffic_policy": "text decode streamed; embedding and multimodal front end resident-only",
        },
    )


def _qwen3_profile(spec: SourceSpec, config: dict, inventory: Inventory) -> ModelProfile:
    layers = int(config["num_hidden_layers"])
    kv_heads = int(config["num_key_value_heads"])
    head_dim = int(config["head_dim"])
    if config.get("torch_dtype") != "bfloat16" or set(inventory.dtype_bytes) != {"BF16"}:
        raise ValueError("Qwen3-8B baseline requires an all-BF16 released checkpoint")
    if bool(config.get("tie_word_embeddings")):
        raise ValueError("Qwen3-8B profile expects the published untied LM head")
    if inventory.checkpoint_bytes != int(spec.total_parameters) * 2:
        raise ValueError("Qwen3-8B BF16 storage does not match the pinned parameter count")
    if inventory.decode_dense_bytes != int(spec.active_parameters) * 2:
        raise ValueError("Qwen3-8B decode bytes do not match active parameter accounting")

    # One K vector plus one V vector for each KV head. BF16 is the explicit,
    # conservative baseline; FP8 remains a sensitivity case, not an official
    # serving claim for this workload.
    entry_bytes = 2 * kv_heads * head_dim * 2
    group = AttentionGroup(
        kind="dense_kv",
        count=layers,
        entry_bytes=entry_bytes,
        label="full-gqa",
        evidence="published GQA topology; BF16 KV precision assumed",
    )
    return ModelProfile(
        name="Qwen3-8B",
        source_repo=spec.repo,
        source_revision=spec.revision,
        total_parameters=spec.total_parameters,
        active_parameters=spec.active_parameters,
        checkpoint_bytes=inventory.checkpoint_bytes,
        dense_weight_bytes=inventory.decode_dense_bytes,
        routed_weight_bytes=0,
        draft_dense_weight_bytes=0,
        draft_routed_weight_bytes=0,
        resident_only_weight_bytes=inventory.resident_only_bytes,
        num_layers=layers,
        # Positive sentinels represent a dense model; routed_weight_bytes == 0
        # is the schema-level discriminator used by operation accounting.
        num_experts=1,
        experts_per_token=1,
        hidden_size=int(config["hidden_size"]),
        max_context_tokens=int(config["max_position_embeddings"]),
        attention_groups=(group,),
        layer_dense_weight_bytes=tuple(
            inventory.decode_layer_dense_bytes.get(str(layer), 0)
            for layer in range(layers)
        ),
        layer_routed_weight_bytes=tuple(0 for _ in range(layers)),
        router_trace_status="not applicable: dense model",
        metadata={
            "adapter": "qwen3",
            "attention_sequence": ["full-gqa"] * layers,
            "checkpoint_inventory": f"data/inventory/{spec.slug}.json",
            "checkpoint_storage_dtype": "BF16",
            "decode_active_parameter_derivation": (
                "all ordinary-decode BF16 tensors divided by two bytes; input embedding excluded"
            ),
            "kv_cache_policy": "BF16 full GQA K/V",
            "kv_cache_policy_status": "precision assumed; topology published",
            "native_context_tokens_published": 32_768,
            "study_context_tokens": 8_192,
            "num_attention_heads": int(config["num_attention_heads"]),
            "num_key_value_heads": kv_heads,
            "head_dim": head_dim,
            "tie_word_embeddings": False,
            "weight_traffic_policy": (
                "decoder and untied LM head streamed; input embedding lookup resident-only"
            ),
            "speculation_policy": "none; no attached draft module in pinned checkpoint",
        },
    )


def build_profile(spec: SourceSpec, config: dict, inventory: Inventory) -> ModelProfile:
    if spec.adapter == "deepseek_v4":
        return _deepseek_profile(spec, config, inventory)
    if spec.adapter == "kimi_k3":
        return _kimi_profile(spec, config, inventory)
    if spec.adapter == "qwen3":
        return _qwen3_profile(spec, config, inventory)
    raise ValueError(f"unknown source adapter {spec.adapter!r}")


def source_by_slug(slug: str) -> SourceSpec:
    for source in SOURCES:
        if source.slug == slug:
            return source
    raise KeyError(slug)


def fetch_tensor_bytes(spec: SourceSpec, tensor_name: str, cache_dir: Path) -> tuple[bytes, dict[str, Any]]:
    """Fetch one tensor payload by range, with dtype/shape metadata.

    This is intended for small router tensors. It refuses missing metadata and
    caches the exact payload under the pinned checkpoint revision.
    """

    root = cache_dir / "metadata" / spec.slug / spec.revision
    index_url = f"{HF_BASE}/{spec.repo}/resolve/{spec.revision}/model.safetensors.index.json"
    index, _ = _cached_json(index_url, root / "model.safetensors.index.json")
    try:
        shard = index["weight_map"][tensor_name]
    except KeyError as exc:
        raise KeyError(f"tensor {tensor_name!r} not found in {spec.repo}") from exc
    header = _shard_header(spec.repo, spec.revision, shard, cache_dir)
    tensor = header[tensor_name]
    start, end = (int(value) for value in tensor["data_offsets"])
    cache_key = hashlib.sha256(tensor_name.encode()).hexdigest()[:20]
    payload_path = (
        cache_dir
        / "tensors"
        / spec.slug
        / spec.revision
        / f"{cache_key}-{Path(shard).stem}.bin"
    )
    expected = end - start
    if payload_path.exists() and payload_path.stat().st_size == expected:
        return payload_path.read_bytes(), tensor
    url = f"{HF_BASE}/{spec.repo}/resolve/{spec.revision}/{shard}"
    prefix = _request_bytes(url, (0, 7))
    header_len = struct.unpack("<Q", prefix)[0]
    absolute_start = 8 + header_len + start
    absolute_end = 8 + header_len + end - 1
    raw = _request_bytes(url, (absolute_start, absolute_end))
    if len(raw) != expected:
        raise RuntimeError(
            f"short tensor range for {tensor_name}: expected {expected}, got {len(raw)}"
        )
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_bytes(raw)
    return raw, tensor
