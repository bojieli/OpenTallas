"""Artifact-only, stage-streaming Qwen3-8B functional service engine.

This engine does not import Transformers and never reads the source checkpoint.
It verifies the deployment manifest, decodes the emitted fixed-width
microprogram, memory-maps the generated ROM images, and executes every semantic
instruction. Only one stage's immutable weights is resident on the selected
device at a time; committed KV state remains resident across decode calls.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import threading
from typing import Any, Mapping, Sequence

from compiler.ir.model import canonical_json_bytes, load_strict_json

from .checking import (
    DEPLOYMENT_SCHEMA,
    Qwen3CheckError,
    verify_deployment_artifacts,
    verify_schedule,
)
from .constants import (
    CONFIG_SHA256,
    LAYER_COUNT,
    MODEL_ID,
    OFFICIAL_CHECKPOINT_LOCK_ID,
    REVISION,
    TARGET_CONTEXT_TOKENS,
)
from .graph import GRAPH_SCHEMA, GraphNode
from .isa import NO_INDEX, NO_LAYER, Opcode, Program, decode, verify


EXECUTION_REPORT_SCHEMA = "opentallas.qwen3.execution_report.v1"


class Qwen3RuntimeError(RuntimeError):
    """Raised on an invalid deployment, request, state transition, or result."""


@dataclass(frozen=True)
class TensorLocation:
    name: str
    stage: int
    image_path: Path
    offset_bytes: int
    size_bytes: int
    shape: tuple[int, ...]
    dtype: str


@dataclass(frozen=True)
class SpanResult:
    logits: Any
    report: dict[str, Any]


def _torch() -> Any:
    try:
        import torch
    except ImportError as exc:
        raise Qwen3RuntimeError("Qwen3 runtime requires PyTorch") from exc
    return torch


def _load(path: Path, label: str) -> dict[str, Any]:
    try:
        return load_strict_json(path)
    except (OSError, ValueError) as exc:
        raise Qwen3RuntimeError(f"cannot load {label} {path}: {exc}") from exc


def _sha256_body(value: Mapping[str, Any], identity_field: str) -> str:
    return hashlib.sha256(
        canonical_json_bytes(
            {key: item for key, item in value.items() if key != identity_field}
        )
    ).hexdigest()


def _tensor_sha256(tensor: Any) -> str:
    torch = _torch()
    raw = tensor.detach().contiguous().cpu().view(torch.uint8).numpy().tobytes()
    return hashlib.sha256(raw).hexdigest()


def _parse_nodes(graph: Mapping[str, Any]) -> tuple[GraphNode, ...]:
    raw_nodes = graph.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise Qwen3RuntimeError("semantic graph nodes must be a nonempty array")
    result: list[GraphNode] = []
    for expected_index, raw in enumerate(raw_nodes):
        if not isinstance(raw, dict) or set(raw) != {
            "index",
            "inputs",
            "kind",
            "layer",
            "node_id",
            "outputs",
            "tensors",
        }:
            raise Qwen3RuntimeError(f"graph node {expected_index} has invalid fields")
        node = GraphNode(
            raw["index"],
            raw["kind"],
            tuple(raw["inputs"]),
            tuple(raw["outputs"]),
            tuple(raw["tensors"]),
            raw["layer"],
        )
        if node.index != expected_index or raw["node_id"] != node.node_id:
            raise Qwen3RuntimeError("semantic graph indices/identities differ")
        result.append(node)
    return tuple(result)


class _WeightStore:
    def __init__(self, locations: Mapping[str, TensorLocation], device: Any):
        self.locations = dict(locations)
        self.device = device
        self._mapped_images: dict[int, Any] = {}
        self._device_weights: dict[str, Any] = {}
        self._active_stage: int | None = None
        self.transferred_bytes = 0

    def _mapped_image(self, location: TensorLocation) -> Any:
        torch = _torch()
        cached = self._mapped_images.get(location.stage)
        if cached is None:
            size_bytes = location.image_path.stat().st_size
            if size_bytes % 2:
                raise Qwen3RuntimeError(
                    f"stage {location.stage} image has odd byte size"
                )
            cached = torch.from_file(
                str(location.image_path),
                shared=False,
                size=size_bytes // 2,
                dtype=torch.bfloat16,
            )
            self._mapped_images[location.stage] = cached
        return cached

    def tensor(self, name: str) -> Any:
        torch = _torch()
        location = self.locations.get(name)
        if location is None:
            raise Qwen3RuntimeError(f"microcode references unmapped weight {name!r}")
        if (
            location.dtype != "BF16"
            or location.offset_bytes % 2
            or location.size_bytes % 2
        ):
            raise Qwen3RuntimeError(f"weight {name!r} is not an aligned BF16 tensor")
        if self._active_stage != location.stage:
            self._device_weights.clear()
            self._active_stage = location.stage
            if self.device.type == "cuda":
                torch.cuda.empty_cache()
        cached = self._device_weights.get(name)
        if cached is not None:
            return cached
        image = self._mapped_image(location)
        start = location.offset_bytes // 2
        elements = location.size_bytes // 2
        source = image.narrow(0, start, elements).view(location.shape)
        if self.device.type == "cpu":
            cached = source
        else:
            cached = source.to(device=self.device, dtype=torch.bfloat16)
            self.transferred_bytes += location.size_bytes
        self._device_weights[name] = cached
        return cached

    def reset_span_counter(self) -> None:
        self.transferred_bytes = 0

    def clear(self) -> None:
        self._device_weights.clear()
        self._mapped_images.clear()
        self._active_stage = None


class Qwen3ServiceEngine:
    """Execute prefill and autoregressive decode from compiled Qwen artifacts."""

    def __init__(
        self,
        deployment: Path,
        *,
        device: str = "cuda",
        attention_backend: str = "sdpa",
        verify_artifacts: bool = True,
    ):
        torch = _torch()
        self.root = Path(deployment).resolve()
        if not self.root.is_dir():
            raise Qwen3RuntimeError(f"deployment is not a directory: {self.root}")
        self.manifest = _load(
            self.root / "deployment_manifest.json", "deployment manifest"
        )
        if verify_artifacts:
            try:
                verify_deployment_artifacts(self.root, self.manifest)
            except Qwen3CheckError as exc:
                raise Qwen3RuntimeError(str(exc)) from exc
        if self.manifest.get("schema") != DEPLOYMENT_SCHEMA:
            raise Qwen3RuntimeError("deployment schema differs")
        compiler_identity = self.manifest.get("compiler")
        if (
            not isinstance(compiler_identity, dict)
            or compiler_identity.get("version") != "qwen3-production-v1"
            or compiler_identity.get("deterministic") is not True
            or not isinstance(compiler_identity.get("source_files"), list)
        ):
            raise Qwen3RuntimeError("deployment compiler identity differs")
        source_root = Path(__file__).resolve().parent
        installed_sources = {
            f"compiler/qwen3/{path.name}": hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(source_root.glob("*.py"))
        }
        locked_sources: dict[str, str] = {}
        for item in compiler_identity["source_files"]:
            if (
                not isinstance(item, dict)
                or set(item) != {"path", "sha256"}
                or not isinstance(item["path"], str)
                or not isinstance(item["sha256"], str)
                or item["path"] in locked_sources
            ):
                raise Qwen3RuntimeError("deployment compiler source lock is invalid")
            locked_sources[item["path"]] = item["sha256"]
        if locked_sources != installed_sources:
            raise Qwen3RuntimeError(
                "installed Qwen3 package differs from the compiler source lock"
            )
        model_identity = self.manifest.get("model")
        if not isinstance(model_identity, dict) or any(
            model_identity.get(key) != value
            for key, value in {
                "checkpoint_lock_id": OFFICIAL_CHECKPOINT_LOCK_ID,
                "config_sha256": CONFIG_SHA256,
                "id": MODEL_ID,
                "revision": REVISION,
                "target_context_tokens": TARGET_CONTEXT_TOKENS,
            }.items()
        ):
            raise Qwen3RuntimeError("deployment model identity differs")

        self.config = _load(self.root / "model/config.json", "model config")
        self._validate_config()
        self.graph = _load(self.root / "execution/graph.json", "semantic graph")
        if self.graph.get("schema") != GRAPH_SCHEMA:
            raise Qwen3RuntimeError("semantic graph schema differs")
        if self.graph.get("graph_id") != _sha256_body(self.graph, "graph_id"):
            raise Qwen3RuntimeError("graph_id does not bind the semantic graph")
        if self.manifest["model"].get("graph_id") != self.graph["graph_id"]:
            raise Qwen3RuntimeError("manifest and semantic graph identities differ")
        if self.graph["coverage"].get("matrix_node_count", 0) < 253:
            raise Qwen3RuntimeError(
                "deployment graph is not the full Qwen3 matrix graph"
            )
        self.nodes = _parse_nodes(self.graph)
        self.tables = _load(
            self.root / "execution/microcode_tables.json", "microcode tables"
        )
        buffers = self.tables.get("buffers")
        weights = self.tables.get("weights")
        if not isinstance(buffers, list) or not all(
            isinstance(item, str) for item in buffers
        ):
            raise Qwen3RuntimeError("microcode buffer table is invalid")
        if not isinstance(weights, list) or not all(
            isinstance(item, str) for item in weights
        ):
            raise Qwen3RuntimeError("microcode weight table is invalid")
        try:
            payload = (self.root / "execution/microcode.bin").read_bytes()
            self.program: Program = decode(payload, tuple(buffers), tuple(weights))
            verify(self.program, self.nodes)
        except (OSError, ValueError) as exc:
            raise Qwen3RuntimeError(f"invalid microcode: {exc}") from exc
        if self.program.graph_id != self.graph["graph_id"]:
            raise Qwen3RuntimeError("microcode is bound to a different semantic graph")

        if attention_backend not in {"eager", "sdpa"}:
            raise Qwen3RuntimeError("attention_backend must be 'eager' or 'sdpa'")
        if device.startswith("cuda") and not torch.cuda.is_available():
            raise Qwen3RuntimeError("CUDA was requested but is unavailable")
        self.device = torch.device(device)
        self.attention_backend = attention_backend
        self.physical_map = _load(
            self.root / "physical/physical_map.json", "physical map"
        )
        self.locations = self._load_locations(self.physical_map)
        if set(self.locations) != set(self.program.weights):
            raise Qwen3RuntimeError(
                "microcode weight table differs from physical mapping"
            )
        self.schedule = _load(
            self.root / "schedule/schedule.json", "execution schedule"
        )
        self.schedule_certificate = _load(
            self.root / "schedule/schedule_certificate.json", "schedule certificate"
        )
        try:
            observed_certificate = verify_schedule(
                self.schedule, self.program, self.nodes, self.physical_map
            )
        except Qwen3CheckError as exc:
            raise Qwen3RuntimeError(f"execution schedule is invalid: {exc}") from exc
        if self.schedule_certificate != observed_certificate:
            raise Qwen3RuntimeError(
                "schedule certificate differs from independent replay"
            )
        self.weights = _WeightStore(self.locations, self.device)
        self._last_use = self._buffer_last_uses()
        self._kv: dict[int, tuple[Any, Any]] = {}
        self.position = 0
        self._operation_lock = threading.RLock()
        self._closed = False

    def __enter__(self) -> Qwen3ServiceEngine:
        self._require_open()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()

    def _require_open(self) -> None:
        if getattr(self, "_closed", False):
            raise Qwen3RuntimeError("service engine is closed")

    def _validate_config(self) -> None:
        expected = {
            "hidden_size": 4096,
            "intermediate_size": 12288,
            "num_hidden_layers": 36,
            "num_attention_heads": 32,
            "num_key_value_heads": 8,
            "head_dim": 128,
            "vocab_size": 151936,
            "rope_theta": 1000000,
            "rms_norm_eps": 1e-06,
            "tie_word_embeddings": False,
            "use_sliding_window": False,
            "rope_scaling": None,
        }
        if any(self.config.get(key) != value for key, value in expected.items()):
            raise Qwen3RuntimeError("runtime config differs from Qwen3-8B")

    def _load_locations(self, physical: Mapping[str, Any]) -> dict[str, TensorLocation]:
        if physical.get("physical_map_id") != _sha256_body(physical, "physical_map_id"):
            raise Qwen3RuntimeError("physical_map_id does not bind the physical map")
        stages = physical.get("stages")
        if not isinstance(stages, list) or len(stages) != LAYER_COUNT:
            raise Qwen3RuntimeError("physical map does not contain 36 stages")
        result: dict[str, TensorLocation] = {}
        for expected_stage, stage in enumerate(stages):
            if not isinstance(stage, dict) or stage.get("stage") != expected_stage:
                raise Qwen3RuntimeError("physical stages are invalid")
            image_text = stage.get("image_path")
            if not isinstance(image_text, str):
                raise Qwen3RuntimeError("physical image path is invalid")
            image = (self.root / image_text).resolve()
            if not image.is_relative_to(self.root) or not image.is_file():
                raise Qwen3RuntimeError("physical image escapes or is missing")
            for raw in stage.get("tensors", []):
                if not isinstance(raw, dict):
                    raise Qwen3RuntimeError("physical tensor record is invalid")
                name = raw.get("name")
                shape = raw.get("shape")
                if (
                    not isinstance(name, str)
                    or name in result
                    or not isinstance(shape, list)
                    or not shape
                    or any(
                        isinstance(item, bool) or not isinstance(item, int) or item <= 0
                        for item in shape
                    )
                ):
                    raise Qwen3RuntimeError("physical tensor identity/shape is invalid")
                location = TensorLocation(
                    name,
                    expected_stage,
                    image,
                    raw.get("offset_bytes"),
                    raw.get("size_bytes"),
                    tuple(shape),
                    raw.get("dtype"),
                )
                if (
                    isinstance(location.offset_bytes, bool)
                    or not isinstance(location.offset_bytes, int)
                    or location.offset_bytes < 0
                    or isinstance(location.size_bytes, bool)
                    or not isinstance(location.size_bytes, int)
                    or location.size_bytes <= 0
                    or math.prod(location.shape) * 2 != location.size_bytes
                    or location.offset_bytes + location.size_bytes
                    > image.stat().st_size
                ):
                    raise Qwen3RuntimeError(
                        f"physical tensor {name!r} has invalid bounds"
                    )
                result[name] = location
        return result

    def _buffer_last_uses(self) -> dict[int, int]:
        result: dict[int, int] = {}
        for index, instruction in enumerate(self.program.instructions[:-1]):
            for source in (instruction.source0, instruction.source1):
                if source != NO_INDEX:
                    result[source] = index
        return result

    @property
    def context_tokens(self) -> int:
        return self.position

    def reset(self) -> None:
        if not self._operation_lock.acquire(blocking=False):
            raise Qwen3RuntimeError("another operation is using this session")
        try:
            self._require_open()
            self._reset_locked()
        finally:
            self._operation_lock.release()

    def _reset_locked(self) -> None:
        torch = _torch()
        self._kv.clear()
        self.position = 0
        self.weights.clear()
        if self.device.type == "cuda":
            torch.cuda.empty_cache()

    def close(self) -> None:
        if getattr(self, "_closed", False):
            return
        if not self._operation_lock.acquire(blocking=False):
            raise Qwen3RuntimeError("another operation is using this session")
        try:
            if self._closed:
                return
            self._reset_locked()
            self._closed = True
        finally:
            self._operation_lock.release()

    def _rms_norm(self, value: Any, weight: Any) -> Any:
        input_dtype = value.dtype
        if (
            weight.numel() == int(self.config["head_dim"])
            and value.shape[-1] != weight.numel()
        ):
            value = value.view(*value.shape[:-1], -1, weight.numel())
        fp32 = value.to(_torch().float32)
        variance = fp32.pow(2).mean(-1, keepdim=True)
        normalized = fp32 * _torch().rsqrt(
            variance + float(self.config["rms_norm_eps"])
        )
        return weight * normalized.to(input_dtype)

    @staticmethod
    def _rotate_half(value: Any) -> Any:
        torch = _torch()
        first = value[..., : value.shape[-1] // 2]
        second = value[..., value.shape[-1] // 2 :]
        return torch.cat((-second, first), dim=-1)

    def _rope(self, query: Any, key: Any, positions: Any) -> tuple[Any, Any]:
        torch = _torch()
        head_dim = int(self.config["head_dim"])
        inv_freq = 1.0 / (
            float(self.config["rope_theta"])
            ** (
                torch.arange(0, head_dim, 2, dtype=torch.float32, device=self.device)
                / head_dim
            )
        )
        expanded = inv_freq[None, :, None].expand(positions.shape[0], -1, 1)
        pos = positions[:, None, :].to(torch.float32)
        with torch.autocast(device_type=self.device.type, enabled=False):
            frequencies = (expanded.float() @ pos.float()).transpose(1, 2)
            embedding = torch.cat((frequencies, frequencies), dim=-1)
            cosine = embedding.cos().to(query.dtype).unsqueeze(1)
            sine = embedding.sin().to(query.dtype).unsqueeze(1)
        query = query.transpose(1, 2)
        key = key.transpose(1, 2)
        return (
            query * cosine + self._rotate_half(query) * sine,
            key * cosine + self._rotate_half(key) * sine,
        )

    def _prepare_kv(self, layer: int, key: Any, value: Any, start: int) -> None:
        torch = _torch()
        batch, _, span, head_dim = key.shape
        kv_heads = int(self.config["num_key_value_heads"])
        if value.shape[-1] != kv_heads * head_dim:
            raise Qwen3RuntimeError(f"layer {layer} V projection has the wrong width")
        value = value.view(batch, span, kv_heads, head_dim).transpose(1, 2)
        cache = self._kv.get(layer)
        if cache is None:
            cache = (
                torch.empty(
                    (batch, kv_heads, TARGET_CONTEXT_TOKENS, head_dim),
                    dtype=torch.bfloat16,
                    device=self.device,
                ),
                torch.empty(
                    (batch, kv_heads, TARGET_CONTEXT_TOKENS, head_dim),
                    dtype=torch.bfloat16,
                    device=self.device,
                ),
            )
            self._kv[layer] = cache
        end = start + span
        cache[0][:, :, start:end, :].copy_(key)
        cache[1][:, :, start:end, :].copy_(value)

    def _attention(self, query: Any, layer: int, start: int, span: int) -> Any:
        torch = _torch()
        import torch.nn.functional as functional

        cache = self._kv.get(layer)
        if cache is None:
            raise Qwen3RuntimeError(
                f"layer {layer} attention reads unprepared KV state"
            )
        total = start + span
        key = cache[0][:, :, :total, :]
        value = cache[1][:, :, :total, :]
        if self.attention_backend == "eager":
            groups = int(self.config["num_attention_heads"]) // int(
                self.config["num_key_value_heads"]
            )
            key = key.repeat_interleave(groups, dim=1)
            value = value.repeat_interleave(groups, dim=1)
            scores = torch.matmul(query, key.transpose(2, 3)) * (
                int(self.config["head_dim"]) ** -0.5
            )
            allowed = torch.arange(total, device=self.device)[None, :] <= (
                start + torch.arange(span, device=self.device)[:, None]
            )
            scores = scores.masked_fill(
                ~allowed[None, None, :, :], torch.finfo(scores.dtype).min
            )
            probabilities = functional.softmax(scores, dim=-1, dtype=torch.float32).to(
                query.dtype
            )
            attended = torch.matmul(probabilities, value)
        else:
            mask = None
            is_causal = start == 0 and span > 1
            if start and span > 1:
                allowed = torch.arange(total, device=self.device)[None, :] <= (
                    start + torch.arange(span, device=self.device)[:, None]
                )
                mask = torch.full(
                    (1, 1, span, total),
                    torch.finfo(query.dtype).min,
                    dtype=query.dtype,
                    device=self.device,
                ).masked_fill(allowed[None, None, :, :], 0)
            groups = int(self.config["num_attention_heads"]) // int(
                self.config["num_key_value_heads"]
            )
            if groups != 1:
                batch, kv_heads, key_tokens, head_dim = key.shape
                key = (
                    key[:, :, None, :, :]
                    .expand(batch, kv_heads, groups, key_tokens, head_dim)
                    .reshape(batch, kv_heads * groups, key_tokens, head_dim)
                )
                value = (
                    value[:, :, None, :, :]
                    .expand(batch, kv_heads, groups, key_tokens, head_dim)
                    .reshape(batch, kv_heads * groups, key_tokens, head_dim)
                )
            attended = functional.scaled_dot_product_attention(
                query.contiguous(),
                key.contiguous(),
                value.contiguous(),
                attn_mask=mask,
                dropout_p=0.0,
                is_causal=is_causal,
                scale=int(self.config["head_dim"]) ** -0.5,
            )
        return (
            attended.transpose(1, 2)
            .contiguous()
            .view(query.shape[0], span, int(self.config["hidden_size"]))
        )

    def _rollback_prepared(self, layers: Sequence[int], start: int, span: int) -> None:
        for layer in layers:
            cache = self._kv.get(layer)
            if cache is not None:
                cache[0][:, :, start : start + span, :].zero_()
                cache[1][:, :, start : start + span, :].zero_()

    def _expected_counters(self, start: int, span: int) -> dict[str, int]:
        hidden = int(self.config["hidden_size"])
        intermediate = int(self.config["intermediate_size"])
        heads = int(self.config["num_attention_heads"])
        kv_heads = int(self.config["num_key_value_heads"])
        head_dim = int(self.config["head_dim"])
        vocabulary = int(self.config["vocab_size"])
        matrix_operations = 0
        for node in self.nodes:
            if node.kind != "LINEAR":
                continue
            if len(node.tensors) != 1:
                raise Qwen3RuntimeError("LINEAR node lacks one weight for accounting")
            location = self.locations[node.tensors[0]]
            positions = 1 if node.tensors[0] == "lm_head.weight" else span
            matrix_operations += 2 * math.prod(location.shape) * positions
        causal_pairs = span * start + span * (span + 1) // 2
        vector_elements = span * (
            LAYER_COUNT * (hidden + hidden + kv_heads * head_dim + hidden)
            + hidden
            + LAYER_COUNT * (hidden + kv_heads * head_dim)
            + LAYER_COUNT * 2 * hidden
            + LAYER_COUNT * intermediate
        )
        weight_bytes = sum(location.size_bytes for location in self.locations.values())
        return {
            "attention_calls": LAYER_COUNT,
            "attention_multiply_add_operations": (
                LAYER_COUNT * 4 * heads * head_dim * causal_pairs
            ),
            "embedding_payload_bytes_read": span * hidden * 2,
            "host_to_device_weight_bytes": (
                weight_bytes if self.device.type == "cuda" else 0
            ),
            "instructions_executed": len(self.program.instructions),
            "kv_bytes_read": (
                LAYER_COUNT * 2 * kv_heads * (start + span) * head_dim * 2
            ),
            "kv_bytes_written": LAYER_COUNT * 2 * kv_heads * span * head_dim * 2,
            "matrix_multiplications": sum(node.kind == "LINEAR" for node in self.nodes),
            "matrix_multiply_add_operations": matrix_operations,
            "output_logit_elements": vocabulary,
            "rom_weight_bytes_addressed": weight_bytes,
            "tokens_processed": span,
            "vector_elements_processed": vector_elements,
        }

    def run_span(
        self,
        token_ids: Sequence[int] | Any,
        *,
        capture_layer_hashes: bool = False,
    ) -> SpanResult:
        """Execute one nonempty prefill/decode span and atomically commit its KV state."""

        if not isinstance(capture_layer_hashes, bool):
            raise Qwen3RuntimeError("capture_layer_hashes must be boolean")
        if not self._operation_lock.acquire(blocking=False):
            raise Qwen3RuntimeError("another operation is using this session")
        try:
            self._require_open()
            return self._run_span_locked(
                token_ids, capture_layer_hashes=capture_layer_hashes
            )
        finally:
            self._operation_lock.release()

    def _run_span_locked(
        self,
        token_ids: Sequence[int] | Any,
        *,
        capture_layer_hashes: bool,
    ) -> SpanResult:

        torch = _torch()
        import torch.nn.functional as functional

        if isinstance(token_ids, torch.Tensor):
            tokens = token_ids.detach().to(dtype=torch.long, device="cpu")
            if tokens.ndim == 1:
                tokens = tokens.unsqueeze(0)
        else:
            if isinstance(token_ids, (str, bytes)) or not isinstance(
                token_ids, Sequence
            ):
                raise Qwen3RuntimeError("token_ids must be a sequence or tensor")
            if any(
                isinstance(item, bool) or not isinstance(item, int)
                for item in token_ids
            ):
                raise Qwen3RuntimeError("token_ids must contain integers")
            tokens = torch.tensor([list(token_ids)], dtype=torch.long)
        if tokens.ndim != 2 or tokens.shape[0] != 1 or tokens.shape[1] <= 0:
            raise Qwen3RuntimeError("runtime supports one nonempty batch-1 span")
        if int(tokens.min()) < 0 or int(tokens.max()) >= int(self.config["vocab_size"]):
            raise Qwen3RuntimeError("token ID is outside the Qwen3 vocabulary")
        span = int(tokens.shape[1])
        start = self.position
        if start + span > TARGET_CONTEXT_TOKENS:
            raise Qwen3RuntimeError(
                f"span would exceed the {TARGET_CONTEXT_TOKENS}-token product context"
            )
        tokens = tokens.to(self.device)
        positions = torch.arange(start, start + span, device=self.device).unsqueeze(0)
        buffers: list[Any | None] = [None] * len(self.program.buffers)
        token_buffer = self.program.buffers.index("input.token_ids")
        buffers[token_buffer] = tokens
        prepared: list[int] = []
        layer_hashes: list[dict[str, Any]] = []
        counters = {
            "attention_calls": 0,
            "attention_multiply_add_operations": 0,
            "embedding_payload_bytes_read": 0,
            "host_to_device_weight_bytes": 0,
            "instructions_executed": 0,
            "kv_bytes_read": 0,
            "kv_bytes_written": 0,
            "matrix_multiplications": 0,
            "matrix_multiply_add_operations": 0,
            "output_logit_elements": 0,
            "rom_weight_bytes_addressed": 0,
            "tokens_processed": span,
            "vector_elements_processed": 0,
        }
        expected_counters: dict[str, int] | None = None
        self.weights.reset_span_counter()

        def name(index: int) -> str:
            return self.program.buffers[index]

        try:
            with torch.no_grad():
                for slot in self.schedule["slots"]:
                    index = slot["instruction_index"]
                    instruction = self.program.instructions[index]
                    if instruction.opcode == Opcode.COMPLETE:
                        counters["instructions_executed"] += 1
                        break
                    source0 = (
                        None
                        if instruction.source0 == NO_INDEX
                        else buffers[instruction.source0]
                    )
                    source1 = (
                        None
                        if instruction.source1 == NO_INDEX
                        else buffers[instruction.source1]
                    )
                    if instruction.source0 != NO_INDEX and source0 is None:
                        raise Qwen3RuntimeError(
                            f"instruction {index} reads an unavailable source0"
                        )
                    if instruction.source1 != NO_INDEX and source1 is None:
                        raise Qwen3RuntimeError(
                            f"instruction {index} reads an unavailable source1"
                        )
                    weight = None
                    if instruction.weight != NO_INDEX:
                        weight_name = self.program.weights[instruction.weight]
                        weight = self.weights.tensor(weight_name)
                        counters["rom_weight_bytes_addressed"] += self.locations[
                            weight_name
                        ].size_bytes
                    output0: Any
                    output1: Any | None = None
                    if instruction.opcode == Opcode.TOKEN_EMBEDDING_LOOKUP:
                        output0 = functional.embedding(source0, weight)
                        counters["embedding_payload_bytes_read"] += (
                            int(output0.numel()) * 2
                        )
                    elif instruction.opcode == Opcode.RMS_NORM:
                        output0 = self._rms_norm(source0, weight)
                        counters["vector_elements_processed"] += int(source0.numel())
                    elif instruction.opcode == Opcode.LINEAR:
                        output0 = functional.linear(source0, weight)
                        counters["matrix_multiplications"] += 1
                        counters["matrix_multiply_add_operations"] += (
                            2 * int(output0.numel()) * int(weight.shape[1])
                        )
                    elif instruction.opcode == Opcode.ROPE:
                        output0, output1 = self._rope(source0, source1, positions)
                        counters["vector_elements_processed"] += int(
                            source0.numel() + source1.numel()
                        )
                    elif instruction.opcode == Opcode.KV_COMMIT:
                        if instruction.layer == NO_LAYER:
                            raise Qwen3RuntimeError("KV_COMMIT lacks its layer")
                        self._prepare_kv(instruction.layer, source0, source1, start)
                        prepared.append(instruction.layer)
                        output0 = instruction.layer
                        kv_elements = source0.numel() + source1.numel()
                        counters["kv_bytes_written"] += int(kv_elements) * 2
                    elif instruction.opcode == Opcode.GQA_CAUSAL_ATTENTION:
                        if source1 != instruction.layer:
                            raise Qwen3RuntimeError(
                                "attention state token differs from its layer"
                            )
                        output0 = self._attention(
                            source0, instruction.layer, start, span
                        )
                        kv_heads = int(self.config["num_key_value_heads"])
                        head_dim = int(self.config["head_dim"])
                        counters["kv_bytes_read"] += (
                            2 * kv_heads * (start + span) * head_dim * 2
                        )
                        counters["attention_calls"] += 1
                        causal_pairs = span * start + span * (span + 1) // 2
                        counters["attention_multiply_add_operations"] += (
                            4
                            * int(self.config["num_attention_heads"])
                            * head_dim
                            * causal_pairs
                        )
                    elif instruction.opcode == Opcode.RESIDUAL_ADD:
                        output0 = source0 + source1
                        counters["vector_elements_processed"] += int(source0.numel())
                    elif instruction.opcode == Opcode.SILU_MUL:
                        output0 = functional.silu(source0) * source1
                        counters["vector_elements_processed"] += int(source0.numel())
                    elif instruction.opcode == Opcode.LAST_TOKEN_SELECT:
                        output0 = source0[:, -1:, :]
                    else:
                        raise Qwen3RuntimeError(
                            f"unsupported opcode {instruction.opcode}"
                        )
                    buffers[instruction.destination0] = output0
                    if instruction.destination1 != NO_INDEX:
                        if output1 is None:
                            raise Qwen3RuntimeError(
                                f"instruction {index} omitted destination1"
                            )
                        buffers[instruction.destination1] = output1
                    counters["instructions_executed"] += 1

                    if (
                        capture_layer_hashes
                        and instruction.opcode == Opcode.RESIDUAL_ADD
                    ):
                        destination_name = name(instruction.destination0)
                        if destination_name.startswith("hidden."):
                            layer_hashes.append(
                                {
                                    "layer": int(destination_name.split(".")[1]),
                                    "sha256": _tensor_sha256(output0),
                                    "shape": list(output0.shape),
                                }
                            )
                    for source_index in (instruction.source0, instruction.source1):
                        if (
                            source_index != NO_INDEX
                            and self._last_use.get(source_index) == index
                            and source_index
                            not in {instruction.destination0, instruction.destination1}
                        ):
                            buffers[source_index] = None
                logits_index = self.program.buffers.index("output.logits")
                logits = buffers[logits_index]
                if logits is None or tuple(logits.shape) != (
                    1,
                    1,
                    int(self.config["vocab_size"]),
                ):
                    raise Qwen3RuntimeError(
                        "program did not produce one complete logits vector"
                    )
                counters["output_logit_elements"] = int(logits.numel())
                counters["host_to_device_weight_bytes"] = self.weights.transferred_bytes
                expected_counters = self._expected_counters(start, span)
                if counters != expected_counters:
                    differing = sorted(
                        key
                        for key in set(counters) | set(expected_counters)
                        if counters.get(key) != expected_counters.get(key)
                    )
                    raise Qwen3RuntimeError(
                        f"execution counters do not reconcile exactly: {differing}"
                    )
                self.position = start + span
        except Exception:
            self._rollback_prepared(prepared, start, span)
            raise
        if expected_counters is None:
            raise Qwen3RuntimeError("execution counter reconciliation was not reached")
        argmax = int(logits[0, -1].argmax().item())
        report_body = {
            "attention_backend": self.attention_backend,
            "build_id": self.manifest["build_id"],
            "counters": counters,
            "counter_reconciliation": {
                "exact": True,
                "expected": expected_counters,
                "status": "pass",
            },
            "device": str(self.device),
            "final_context_tokens": self.position,
            "initial_context_tokens": start,
            "layer_boundaries": layer_hashes,
            "logits": {
                "argmax_token_id": argmax,
                "dtype": str(logits.dtype).removeprefix("torch."),
                "sha256": _tensor_sha256(logits),
                "shape": list(logits.shape),
            },
            "schema": EXECUTION_REPORT_SCHEMA,
            "span_tokens": span,
        }
        report = {
            **report_body,
            "report_id": hashlib.sha256(canonical_json_bytes(report_body)).hexdigest(),
        }
        return SpanResult(logits, report)

    def generate_greedy(
        self,
        prompt_ids: Sequence[int],
        *,
        max_new_tokens: int,
        eos_token_ids: Sequence[int] = (151645, 151643),
        capture_layer_hashes: bool = False,
    ) -> dict[str, Any]:
        """Run full prefill plus single-token decode calls with greedy selection."""

        if not isinstance(capture_layer_hashes, bool):
            raise Qwen3RuntimeError("capture_layer_hashes must be boolean")
        if not self._operation_lock.acquire(blocking=False):
            raise Qwen3RuntimeError("another operation is using this session")
        try:
            self._require_open()
            return self._generate_greedy_locked(
                prompt_ids,
                max_new_tokens=max_new_tokens,
                eos_token_ids=eos_token_ids,
                capture_layer_hashes=capture_layer_hashes,
            )
        finally:
            self._operation_lock.release()

    def _generate_greedy_locked(
        self,
        prompt_ids: Sequence[int],
        *,
        max_new_tokens: int,
        eos_token_ids: Sequence[int],
        capture_layer_hashes: bool,
    ) -> dict[str, Any]:

        if (
            isinstance(max_new_tokens, bool)
            or not isinstance(max_new_tokens, int)
            or max_new_tokens <= 0
        ):
            raise Qwen3RuntimeError("max_new_tokens must be a positive integer")
        if isinstance(prompt_ids, (str, bytes)) or not isinstance(prompt_ids, Sequence):
            raise Qwen3RuntimeError("prompt token IDs must be a sequence")
        if len(prompt_ids) <= 0:
            raise Qwen3RuntimeError("prompt must contain at least one token")
        if len(prompt_ids) + max_new_tokens - 1 > TARGET_CONTEXT_TOKENS:
            raise Qwen3RuntimeError(
                "requested generation would process beyond 8,000 tokens"
            )
        eos = set(eos_token_ids)
        if any(
            isinstance(item, bool)
            or not isinstance(item, int)
            or not 0 <= item < int(self.config["vocab_size"])
            for item in eos
        ):
            raise Qwen3RuntimeError("EOS token IDs must be valid vocabulary integers")
        self.reset()
        spans: list[dict[str, Any]] = []
        result = self.run_span(prompt_ids, capture_layer_hashes=capture_layer_hashes)
        spans.append(result.report)
        generated: list[int] = []
        for index in range(max_new_tokens):
            token = int(result.report["logits"]["argmax_token_id"])
            generated.append(token)
            if token in eos or index + 1 == max_new_tokens:
                break
            result = self.run_span([token], capture_layer_hashes=capture_layer_hashes)
            spans.append(result.report)
        body = {
            "build_id": self.manifest["build_id"],
            "context_tokens_committed": self.position,
            "generated_token_ids": generated,
            "mode": "greedy",
            "prompt_token_count": len(prompt_ids),
            "schema": "opentallas.qwen3.generation_result.v1",
            "spans": spans,
            "termination": "eos" if generated and generated[-1] in eos else "length",
        }
        return {
            **body,
            "result_id": hashlib.sha256(canonical_json_bytes(body)).hexdigest(),
        }


__all__ = [
    "EXECUTION_REPORT_SCHEMA",
    "Qwen3RuntimeError",
    "Qwen3ServiceEngine",
    "SpanResult",
    "TensorLocation",
]
