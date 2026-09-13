"""Profile public checkpoints without downloading their tensor payloads.

Safetensors places a JSON tensor table at the beginning of every shard.  Two
small HTTP range reads per shard are enough to recover exact shapes, dtypes, and
storage offsets.  This makes metadata profiling of a multi-terabyte checkpoint
practical on a CPU workstation while never claiming to have executed the model.
"""

from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
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
#: Placement variants of the DeepSeek-V4.1 checkpoint.  ``""`` is the released
#: placement (tables beside the weights), ``engram_host`` puts the tables in
#: host memory and ``engram_hbm`` makes them a resident region of the KV store.
V41_VARIANTS = ("", "engram_host", "engram_hbm")


@dataclass(frozen=True)
class SourceSpec:
    slug: str
    repo: str
    revision: str
    adapter: str
    total_parameters: float
    active_parameters: float
    #: A named placement variant of the same checkpoint.  Two are defined, both
    #: for DeepSeek-V4.1, and both move only the Engram lookup tables off the
    #: weight store: ``engram_host`` puts them in host memory, as DeepSeek's own
    #: serving stack places them, where they cost capacity and bandwidth on
    #: neither side of a comparison; ``engram_hbm`` makes them a resident,
    #: load-once, read-only region of the same store that holds the KV cache, so
    #: they cost that store's capacity on the stage that holds them and their
    #: per-token row reads cost that store's bandwidth.  The inventory is the
    #: checkpoint's and is shared by every variant.
    variant: str = ""
    #: Where the profile is written under ``configs/models``.  Candidate
    #: models that no release document binds a figure to live one level down,
    #: as the anchor does, so the legacy glob over ``configs/models/*.json``
    #: and the artifacts it feeds are untouched.
    profile_dir: str = ""

    @property
    def inventory_slug(self) -> str:
        return self.slug[: -len(f"-{self.variant}")] if self.variant else self.slug


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
    # DeepSeek-V4.1-Flash, released 2026-09-10.  Published counts: 552B
    # backbone plus 196B Engram, 16B activated per decode token (8B per
    # prefill token under the causal encoder-decoder).  The header inventory
    # reproduces them: 551.88B backbone, 196.61B Engram, 16.13B streamed per
    # decode token including the untied head.
    SourceSpec(
        slug="deepseek-v4.1-flash",
        repo="deepseek-ai/DeepSeek-V4.1-Flash",
        revision="dba1be0a40aa45a94ad051997016db3960a90277",
        adapter="deepseek_v41",
        total_parameters=552e9,
        active_parameters=16e9,
        profile_dir="candidates",
    ),
    SourceSpec(
        slug="deepseek-v4.1-flash-engram_host",
        repo="deepseek-ai/DeepSeek-V4.1-Flash",
        revision="dba1be0a40aa45a94ad051997016db3960a90277",
        adapter="deepseek_v41",
        total_parameters=552e9,
        active_parameters=16e9,
        variant="engram_host",
        profile_dir="candidates",
    ),
    SourceSpec(
        slug="deepseek-v4.1-flash-engram_hbm",
        repo="deepseek-ai/DeepSeek-V4.1-Flash",
        revision="dba1be0a40aa45a94ad051997016db3960a90277",
        adapter="deepseek_v41",
        total_parameters=552e9,
        active_parameters=16e9,
        variant="engram_hbm",
        profile_dir="candidates",
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
    deployment_storage: dict[str, Any]
    #: Exact element counts by decode role, from the pinned shapes.  A packed
    #: I8 routed-expert byte holds two MXFP4 values; block-scale tensors carry
    #: no parameters.  Populated for every adapter profiled after 2026-09-13;
    #: older inventories omit it.
    parameter_counts: dict[str, int] = field(default_factory=dict)
    #: Bytes of lookup tables that are read sparsely per token rather than
    #: streamed -- today only DeepSeek-V4.1's Engram tables -- in released
    #: packing and in the A100 BF16 expansion.
    lookup_table_bytes: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if not self.parameter_counts:
            data.pop("parameter_counts")
        if not self.lookup_table_bytes:
            data.pop("lookup_table_bytes")
        return data


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
_ENGRAM_TABLE_RE = re.compile(r"^layers\.\d+\.engram\.embed\.(weight|scale)$")
DEEPSEEK_ADAPTERS = frozenset({"deepseek_v4", "deepseek_v41"})


def _parameter_count(name: str, dtype: str, shape: list[int]) -> int:
    """Elements a released tensor holds, packed I8 MXFP4 counted as two."""

    if name.endswith(".scale"):
        return 0
    count = 1
    for extent in shape:
        count *= int(extent)
    if dtype == "I8":
        if not (_is_routed(name) and name.endswith(".weight")):
            raise RuntimeError(f"unexpected I8 tensor {name!r}")
        return 2 * count
    return count


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
    elif adapter == "deepseek_v41":
        # DSpark draft blocks are read only under speculation.  The input
        # embedding, the vision encoder with its projector and image
        # delimiters, and the two Engram n-gram tables are looked up rather
        # than streamed: an Engram module reads 24 rows of 264 bytes per token
        # (inference/engram.py), which the profile records as auxiliary
        # traffic.  The Engram key/value projection, the untied head and
        # everything else is streamed on every decode token.
        if name.startswith("mtp."):
            return "draft_routed" if _is_routed(name) else "draft_dense"
        if (
            name == "embed.weight"
            or name.startswith("vision.")
            or name.startswith("aligner.")
            or name in {"image_start", "image_end", "image_newline"}
            or _ENGRAM_TABLE_RE.search(name)
        ):
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


def _deepseek_a100_bf16_storage_bytes(name: str, dtype: str, storage: int) -> int:
    """Bytes after offline expansion into arithmetic A100 can execute natively.

    A100 has BF16 Tensor Cores but no FP8 or floating-point FP4 Tensor Core path.
    FP8 values expand from one to two bytes.  Each released I8 expert payload
    byte contains two MXFP4 values, so it expands to four BF16 bytes.  E8M0
    block scales are absorbed during offline dequantization and need not remain
    resident.  Already-BF16, FP32, and integer lookup tensors are unchanged.
    """

    if dtype == "F8_E8M0":
        return 0
    if dtype == "F8_E4M3":
        return storage * 2
    if dtype == "I8":
        if not (_is_routed(name) and name.endswith(".weight")):
            raise RuntimeError(f"unexpected DeepSeek I8 tensor {name!r}")
        return storage * 4
    return storage


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
    deployment_roles: dict[str, int] = defaultdict(int)
    deployment_layer_dense: dict[str, int] = defaultdict(int)
    deployment_layer_routed: dict[str, int] = defaultdict(int)
    parameter_counts: dict[str, int] = defaultdict(int)
    lookup_packed = lookup_expanded = 0
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
            parameter_counts[role] += _parameter_count(
                name, dtype, list(tensor.get("shape", ()))
            )
            if spec.adapter in DEEPSEEK_ADAPTERS:
                deployed = _deepseek_a100_bf16_storage_bytes(
                    name, dtype, storage
                )
                deployment_roles[role] += deployed
                if layer is not None and role == "decode_dense":
                    deployment_layer_dense[layer] += deployed
                elif layer is not None and role == "decode_routed":
                    deployment_layer_routed[layer] += deployed
                if _ENGRAM_TABLE_RE.search(name):
                    lookup_packed += storage
                    lookup_expanded += deployed
                    parameter_counts["engram_table"] += _parameter_count(
                        name, dtype, list(tensor.get("shape", ()))
                    )
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
        deployment_storage=(
            {
                "a100_bf16_expanded": {
                    "checkpoint_bytes": sum(deployment_roles.values()),
                    "decode_dense_bytes": deployment_roles["decode_dense"],
                    "decode_routed_bytes": deployment_roles["decode_routed"],
                    "draft_dense_bytes": deployment_roles["draft_dense"],
                    "draft_routed_bytes": deployment_roles["draft_routed"],
                    "resident_only_bytes": deployment_roles["resident_only"],
                    "decode_layer_dense_bytes": dict(
                        sorted(
                            deployment_layer_dense.items(),
                            key=lambda pair: int(pair[0]),
                        )
                    ),
                    "decode_layer_routed_bytes": dict(
                        sorted(
                            deployment_layer_routed.items(),
                            key=lambda pair: int(pair[0]),
                        )
                    ),
                    "policy": (
                        "offline exact-value expansion: FP8 to BF16, packed MXFP4 "
                        "to BF16, E8M0 scales absorbed"
                    ),
                }
            }
            if spec.adapter in DEEPSEEK_ADAPTERS
            else {}
        ),
        parameter_counts=dict(sorted(parameter_counts.items())),
        lookup_table_bytes=(
            {
                "engram_table_packed": lookup_packed,
                "engram_table_a100_bf16_expanded": lookup_expanded,
            }
            if lookup_packed
            else {}
        ),
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
        dense_compute_format="fp8_e4m3_x_fp8_e4m3",
        routed_compute_format="mxfp4_e2m1_x_fp8_e4m3",
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
            "weight_storage_policy": (
                "routed experts MXFP4 E2M1 with E8M0 microscaling; "
                "dense/shared matrices FP8 E4M3 with E8M0 block scales"
            ),
            "compute_precision_policy": (
                "routed expert GEMMs use MXFP4 weights x FP8 activations; "
                "dense/shared GEMMs use FP8 weights x FP8 activations"
            ),
            "compute_precision_status": "published DeepSeek report and pinned config",
            "num_hash_layers": int(config.get("num_hash_layers", 0)),
            "weight_traffic_policy": "main decode streamed; MTP charged only under speculation; embeddings/hash tables resident-only",
            "index_heads": int(config["index_n_heads"]),
            "index_head_dim": index_dim,
            "index_topk": int(config["index_topk"]),
            # Tensor-contraction accounting is derived from these official
            # dimensions and the released inference implementation.  Keep the
            # complete input beside the generated profile so a result never
            # relies on rounded "active parameter" arithmetic.
            "operator_config": {
                "vocab_size": int(config["vocab_size"]),
                "hidden_size": int(config["hidden_size"]),
                "moe_intermediate_size": int(config["moe_intermediate_size"]),
                "num_attention_heads": int(config["num_attention_heads"]),
                "head_dim": head_dim,
                "rope_head_dim": rope_dim,
                "q_lora_rank": int(config["q_lora_rank"]),
                "o_groups": int(config["o_groups"]),
                "o_lora_rank": int(config["o_lora_rank"]),
                "num_routed_experts": int(config["n_routed_experts"]),
                "num_shared_experts": int(config["n_shared_experts"]),
                "experts_per_token": int(config["num_experts_per_tok"]),
                "index_heads": int(config["index_n_heads"]),
                "index_head_dim": index_dim,
                "index_topk": int(config["index_topk"]),
                "window_tokens": window,
                "hc_mult": int(config["hc_mult"]),
                "hc_sinkhorn_iters": int(config["hc_sinkhorn_iters"]),
                "compress_ratios": list(ratios),
            },
            "operator_accounting_source": (
                "official config, pinned safetensors tensor shapes/dtypes, and "
                "pinned DeepSeek inference/model.py"
            ),
            "deployment_storage": inventory.deployment_storage,
        },
    )


def _csa2_layer_modes(text: dict[str, Any], layers: int) -> list[dict[str, Any]]:
    """One record per backbone layer, read the way ``inference/model.py`` does.

    ``compress_ratios[l] == 0`` is sliding-window-only.  Otherwise the layer is
    CSA2: it owns a compressed main cache only if it is a ``kv_source_layer``
    (Full mode); it runs an indexer only if it is an ``index_source_layer``
    (Full when it also owns the cache, Reindex otherwise); every other CSA2
    layer is Reuse mode and takes the latest top-k from its predecessor.  An
    indexer strictly after ``candidate_source_layer_id`` scores only the
    candidate pool that layer built.
    """

    ratios = [int(value) for value in text["compress_ratios"][:layers]]
    kv_sources = {int(value) for value in text["kv_source_layer_ids"]}
    index_sources = {int(value) for value in text["index_source_layer_ids"]}
    candidate_source = int(text.get("candidate_source_layer_id", -1))
    pool = int(text.get("candidate_topk_blocks", 0)) * int(
        text.get("candidate_block_size", 0)
    )
    records: list[dict[str, Any]] = []
    for layer, ratio in enumerate(ratios):
        if ratio == 0:
            records.append({"layer": layer, "ratio": 0, "mode": "swa", "label": "swa"})
            continue
        owner = layer in kv_sources
        indexes = layer in index_sources
        if owner and indexes:
            mode = "full"
        elif indexes:
            mode = "reindex"
        elif owner:
            raise ValueError(f"layer {layer} owns a cache but never indexes it")
        else:
            mode = "reuse"
        uses_pool = indexes and 0 <= candidate_source < layer
        records.append(
            {
                "layer": layer,
                "ratio": ratio,
                "mode": mode,
                "label": f"csa2-{ratio}-{mode}",
                "kv_owner": owner,
                "scans_index": indexes,
                "index_scan_entries_cap": pool if uses_pool else 0,
                "is_candidate_source": layer == candidate_source,
            }
        )
    return records


def _deepseek_v41_profile(
    spec: SourceSpec, config: dict, inventory: Inventory
) -> ModelProfile:
    """DeepSeek-V4.1-Flash: CED backbone, CSA2 with cross-layer KV sharing.

    Every byte width below is read off the pinned ``inference/model.py`` and
    the technical report, not measured by running the model here:

    * main KV latent: E2M1 over ``head_dim`` channels with one E4M3 scale per
      16 channels (report section 2.4.4; ``fp4_act_quant(latent, 16, ...,
      scale_dtype=float8_e4m3fn)`` in ``Attention._compress_kv``);
    * indexer key: E2M1 over ``index_head_dim`` with one E8M0 scale per 32
      (``fp4_act_quant(k, fp4_block_size, True)`` in ``Indexer.forward``);
    * sliding-window KV: E4M3 over ``head_dim`` with one E8M0 scale per 32
      (``act_quant(kv, fp8_block_size, ...)`` in ``Attention._window_kv``);
      the report keeps the window at FP8 "due to its sensitivity".

    With ``head_dim = 512`` and ``index_head_dim = 128`` that is 288 + 68
    bytes per owned global entry; three encoder owners at ratio 2 and one
    decoder owner at ratio 1 give 890 bytes of global KV per token, which is
    the figure the model card and report publish.
    """

    text = config["text_config"]
    layers = int(text["num_hidden_layers"])
    head_dim = int(text["head_dim"])
    rope_dim = int(text["qk_rope_head_dim"])
    index_dim = int(text["index_head_dim"])
    window = int(text["sliding_window"])
    quant = config.get("quantization_config", {})
    fp8_block = int(quant.get("weight_block_size", [32, 32])[1])
    main_entry_bytes = head_dim / 2 + head_dim / 16  # E2M1 + E4M3 per 16
    index_entry_bytes = index_dim / 2 + index_dim / 32  # E2M1 + E8M0 per 32
    window_entry_bytes = head_dim + head_dim / fp8_block  # E4M3 + E8M0 per block

    records = _csa2_layer_modes(text, layers)
    groups: list[AttentionGroup] = []
    seen: dict[str, int] = {}
    for record in records:
        seen[record["label"]] = seen.get(record["label"], 0) + 1
    for record in records:
        label = record["label"]
        if label not in seen:
            continue
        count = seen.pop(label)
        if record["mode"] == "swa":
            groups.append(
                AttentionGroup(
                    kind="window",
                    count=count,
                    entry_bytes=window_entry_bytes,
                    window_tokens=window,
                    label=label,
                    evidence=(
                        "official config compress_ratios == 0; FP8 window entry "
                        "read off pinned inference/model.py Attention._window_kv"
                    ),
                )
            )
            continue
        groups.append(
            AttentionGroup(
                kind="compressed_sparse",
                count=count,
                entry_bytes=main_entry_bytes,
                window_tokens=window,
                window_entry_bytes=window_entry_bytes,
                compression_ratio=int(record["ratio"]),
                top_k=int(text["index_topk"]),
                index_entry_bytes=index_entry_bytes,
                kv_owner=bool(record["kv_owner"]),
                scans_index=bool(record["scans_index"]),
                index_scan_entries_cap=int(record["index_scan_entries_cap"]),
                label=label,
                evidence=(
                    f"CSA2 {record['mode']} mode from official config kv_source_layer_ids / "
                    "index_source_layer_ids / candidate_source_layer_id as pinned "
                    "inference/model.py reads them; FP4 main and index entries per "
                    "technical report section 2.4.4"
                ),
            )
        )
    sequence = [record["label"] for record in records]

    lookup = inventory.lookup_table_bytes
    engram_packed = int(lookup.get("engram_table_packed", 0))
    engram_expanded = int(lookup.get("engram_table_a100_bf16_expanded", 0))
    if spec.variant not in V41_VARIANTS:
        raise ValueError(f"unknown DeepSeek-V4.1 variant {spec.variant!r}")
    engram_host = spec.variant == "engram_host"
    engram_hbm = spec.variant == "engram_hbm"
    # Both placement variants take the tables off the weight store, so both
    # subtract the same bytes from the checkpoint that store has to hold.  They
    # differ in where the bytes go next: host memory charges capacity and
    # bandwidth to neither side of a comparison, while HBM residency charges
    # the capacity of the KV store on the stage that holds them and the
    # bandwidth of that store for every row read.
    off_weight_store = engram_host or engram_hbm
    if engram_packed <= 0:
        raise ValueError("DeepSeek-V4.1 inventory carries no Engram table bytes")

    checkpoint_bytes = inventory.checkpoint_bytes - (engram_packed if off_weight_store else 0)
    resident_only = inventory.resident_only_bytes - (engram_packed if off_weight_store else 0)
    expanded = dict(inventory.deployment_storage["a100_bf16_expanded"])
    if off_weight_store:
        expanded["checkpoint_bytes"] = int(expanded["checkpoint_bytes"]) - engram_expanded
        expanded["resident_only_bytes"] = int(expanded["resident_only_bytes"]) - engram_expanded
        expanded["policy"] = str(expanded["policy"]) + (
            "; Engram tables host-resident"
            if engram_host
            else "; Engram tables resident in the KV store"
        )

    engram_cfg = {
        "layer_ids": [int(value) for value in text["engram_layer_ids"]],
        "num_embeddings": [int(value) for value in text["engram_num_embeddings"]],
        "max_ngram_size": int(text["engram_max_ngram_size"]),
        "n_heads": int(text["engram_n_heads"]),
        "head_dim": int(text["engram_head_dim"]),
        "compressed_vocab_size": int(text["engram_compressed_vocab_size"]),
    }
    hash_cols = (engram_cfg["max_ngram_size"] - 1) * engram_cfg["n_heads"]
    row_bytes = engram_cfg["head_dim"] + engram_cfg["head_dim"] / fp8_block
    engram_cfg["rows_read_per_token_per_module"] = hash_cols
    engram_cfg["row_bytes_packed"] = row_bytes
    engram_cfg["lookup_bytes_per_token"] = len(engram_cfg["layer_ids"]) * hash_cols * row_bytes

    # One resident region per Engram module, sized by that module's own
    # embedding count and read at that module's own row depth.  Nothing here is
    # written down: the bytes are num_embeddings x row_bytes and the per-token
    # reads are rows_read_per_token_per_module x row_bytes, and both are
    # cross-checked against the header inventory below, which is what makes the
    # per-stage attribution in the analytical model a derivation rather than an
    # assignment.
    expanded_row_bytes = float(2 * engram_cfg["head_dim"])
    regions: list[dict[str, Any]] = []
    expanded_regions: list[dict[str, Any]] = []
    for layer_id, count in zip(engram_cfg["layer_ids"], engram_cfg["num_embeddings"]):
        regions.append(
            {
                "label": f"engram_table_l{layer_id}",
                "layer_id": layer_id,
                "bytes": count * row_bytes,
                "read_bytes_per_token": hash_cols * row_bytes,
                "rows": count,
                "row_bytes": row_bytes,
                "rows_read_per_token": hash_cols,
            }
        )
        expanded_regions.append(
            {
                "label": f"engram_table_l{layer_id}",
                "layer_id": layer_id,
                "bytes": count * expanded_row_bytes,
                "read_bytes_per_token": hash_cols * expanded_row_bytes,
                "rows": count,
                "row_bytes": expanded_row_bytes,
                "rows_read_per_token": hash_cols,
            }
        )
    for total, measured, what in (
        (sum(region["bytes"] for region in regions), engram_packed, "packed"),
        (
            sum(region["bytes"] for region in expanded_regions),
            engram_expanded,
            "A100 BF16 expanded",
        ),
    ):
        if abs(total - measured) > 1.0:
            raise ValueError(
                f"{what} Engram region bytes derived from the config "
                f"({total:.0f} B) disagree with the header inventory ({measured} B)"
            )

    name = "DeepSeek-V4.1-Flash" + {
        "": "",
        "engram_host": "-engram-host",
        "engram_hbm": "-engram-hbm",
    }[spec.variant]
    if engram_host:
        placement = (
            "Engram tables in HOST memory, prefetched by RDMA as DeepSeek's serving "
            "stack does (report sections 2.4.2, 3.1.3); they count against neither "
            "ROM nor HBM capacity on either side of a comparison"
        )
    elif engram_hbm:
        placement = (
            "Engram tables resident in the KV store -- wafer-edge HBM on the ROM "
            "side, the same HBM on the GPU side -- as a load-once, read-only "
            "region written at load and never at runtime (plan section 3.4). The "
            "weight store holds none of them, so a mask ROM is sized without "
            "them; instead they take capacity from the stage whose layers own "
            "them (metadata.hbm_resident_regions) and their row reads take that "
            "store's bandwidth on that stage"
        )
    else:
        placement = (
            "Engram tables resident beside the weights: in mask ROM on the ROM "
            "side (they are immutable and read by row address, which is what a ROM "
            "does) and in HBM on the GPU side; both sides pay the capacity"
        )
    resident_metadata: dict[str, Any] = {}
    if engram_hbm:
        resident_metadata = {
            "hbm_resident_weight_bytes": engram_packed,
            "hbm_resident_regions": regions,
            "hbm_resident_policy": (
                "immutable lookup tables held in the KV store rather than the "
                "weight store: capacity is charged to the pipeline stage whose "
                "layer range contains layer_id, and read_bytes_per_token is "
                "charged to that stage's KV read traffic on every decode token. "
                "Written once at load, so no write traffic and no per-user "
                "storage"
            ),
        }
        expanded["hbm_resident_bytes"] = engram_expanded
        expanded["hbm_resident_regions"] = expanded_regions
    return ModelProfile(
        name=name,
        source_repo=spec.repo,
        source_revision=spec.revision,
        total_parameters=spec.total_parameters,
        active_parameters=spec.active_parameters,
        checkpoint_bytes=checkpoint_bytes,
        dense_weight_bytes=inventory.decode_dense_bytes,
        routed_weight_bytes=inventory.decode_routed_bytes,
        dense_compute_format="fp8_e4m3_x_fp8_e4m3",
        routed_compute_format="mxfp4_e2m1_x_fp8_e4m3",
        draft_dense_weight_bytes=inventory.draft_dense_bytes,
        draft_routed_weight_bytes=inventory.draft_routed_bytes,
        resident_only_weight_bytes=resident_only,
        num_layers=layers,
        num_experts=int(text["n_routed_experts"]),
        experts_per_token=int(text["num_experts_per_tok"]),
        hidden_size=int(text["hidden_size"]),
        max_context_tokens=int(text["max_position_embeddings"]),
        attention_groups=tuple(groups),
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
            "adapter": "deepseek_v41",
            "variant": spec.variant,
            "architecture": (
                "Causal Encoder-Decoder: 20 encoder layers whose final hidden "
                "state is projected into the decoder's single shared global KV "
                "(layer 20, CSA2 Full, ratio 1); 20 decoder layers; every layer "
                "keeps its own 128-token FP8 sliding window"
            ),
            "attention_sequence": sequence,
            "csa2_layer_modes": records,
            "checkpoint_inventory": f"data/inventory/{spec.inventory_slug}.json",
            "engram": engram_cfg,
            "engram_placement": placement,
            "host_resident_weight_bytes": engram_packed if engram_host else 0,
            **resident_metadata,
            "kv_cache_policy": (
                f"global KV shared across layers: FP4 E2M1 main latent with one E4M3 "
                f"scale per 16 channels ({main_entry_bytes:.0f} B) plus FP4 index key "
                f"with one E8M0 scale per 32 ({index_entry_bytes:.0f} B), owned by "
                f"layers {sorted(int(v) for v in text['kv_source_layer_ids'])}; "
                f"FP8 sliding-window KV ({window_entry_bytes:.0f} B) per layer, "
                f"{window} entries, never persisted (SWA Bounded Replay)"
            ),
            "kv_cache_policy_status": (
                "published (model card, report section 2.4.4) and read off pinned "
                "inference/model.py; NOT measured by executing the model in this "
                "repository. 890 B/token global reproduces the published figure"
            ),
            "global_kv_bytes_per_token": sum(
                (main_entry_bytes + index_entry_bytes) / record["ratio"]
                for record in records
                if record["mode"] == "full"
            ),
            "prefill": {
                "active_parameters_published": 8e9,
                "policy": (
                    "under CED only the 20 encoder layers plus the decoder's KV "
                    "projection run over the prompt; the decoder replays the last "
                    "128 tokens (Decoder SWA Bounded Replay). Prefill is outside "
                    "the decode-only scope of this program's studies"
                ),
            },
            "weight_storage_policy": (
                "routed experts MXFP4 E2M1 with E8M0 microscaling (32x32 blocks); "
                "dense/shared/Engram-projection matrices FP8 E4M3 with E8M0 block "
                "scales; Engram tables FP8 E4M3 rows with E8M0 per 32; embeddings, "
                "head, vision encoder, compressor and indexer-key projections BF16; "
                "mHC coefficients FP32"
            ),
            "compute_precision_policy": (
                "routed expert GEMMs use MXFP4 weights x FP8 activations; "
                "dense/shared GEMMs use FP8 weights x FP8 activations"
            ),
            "compute_precision_status": "published DeepSeek report and pinned config",
            "weight_traffic_policy": (
                "all 40 backbone layers and the untied head streamed on every "
                "decode token; DSpark draft charged only under speculation; input "
                "embedding, vision encoder, projector and Engram tables resident-only "
                "(each Engram module reads 24 rows of 264 B per token, recorded "
                "under metadata.engram.lookup_bytes_per_token)"
            ),
            "parameter_counts": dict(inventory.parameter_counts),
            "index_heads": int(text["index_n_heads"]),
            "index_head_dim": index_dim,
            "index_topk": int(text["index_topk"]),
            "operator_config": {
                "vocab_size": int(text["vocab_size"]),
                "hidden_size": int(text["hidden_size"]),
                "moe_intermediate_size": int(text["moe_intermediate_size"]),
                "num_attention_heads": int(text["num_attention_heads"]),
                "head_dim": head_dim,
                "rope_head_dim": rope_dim,
                "q_lora_rank": int(text["q_lora_rank"]),
                "o_groups": int(text["o_groups"]),
                "o_lora_rank": int(text["o_lora_rank"]),
                "num_routed_experts": int(text["n_routed_experts"]),
                "num_shared_experts": int(text["n_shared_experts"]),
                "experts_per_token": int(text["num_experts_per_tok"]),
                "index_heads": int(text["index_n_heads"]),
                "index_head_dim": index_dim,
                "index_topk": int(text["index_topk"]),
                "window_tokens": window,
                "hc_mult": int(text["hc_mult"]),
                "hc_sinkhorn_iters": int(text["hc_sinkhorn_iters"]),
                "compress_ratios": [int(v) for v in text["compress_ratios"][:layers]],
                "kv_source_layer_ids": sorted(int(v) for v in text["kv_source_layer_ids"]),
                "index_source_layer_ids": sorted(
                    int(v) for v in text["index_source_layer_ids"]
                ),
                "candidate_source_layer_id": int(text["candidate_source_layer_id"]),
                "candidate_topk_blocks": int(text["candidate_topk_blocks"]),
                "candidate_block_size": int(text["candidate_block_size"]),
                "engram_layer_ids": engram_cfg["layer_ids"],
                "engram_hash_columns": hash_cols,
                "engram_head_dim": engram_cfg["head_dim"],
                "fp8_weight_block": fp8_block,
            },
            "operator_accounting_source": (
                "official config, pinned safetensors tensor shapes/dtypes, pinned "
                "DeepSeek inference/model.py and inference/engram.py, and the "
                "DeepSeek-V4.1-Flash technical report"
            ),
            "deployment_storage": {"a100_bf16_expanded": expanded},
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
        dense_compute_format="bf16_x_bf16",
        routed_compute_format="mxfp4_e2m1_x_mxfp8_e4m3",
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
            "compute_precision_policy": (
                "routed expert GEMMs use MXFP4 weights x MXFP8 activations; "
                "dense BF16 checkpoint tensors use the BF16 roof"
            ),
            "compute_precision_status": "mixed published checkpoint/README and derived classification",
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
        dense_compute_format="bf16_x_bf16",
        routed_compute_format=None,
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
            "compute_precision_policy": "BF16 weights x BF16 activations",
            "compute_precision_status": "released BF16 baseline",
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
    if spec.adapter == "deepseek_v41":
        return _deepseek_v41_profile(spec, config, inventory)
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
