"""Independent official Transformers 4.51.0 Qwen3 differential runner.

The runner reads the original pinned safetensors snapshot, instantiates exactly
one official decoder layer at a time on a meta device, and dispatches that layer
on the selected execution device. It therefore remains usable when the full
16.38-GB module cannot coexist with other GPU services. It does not consume
compiled images or compiler microcode and is intentionally independent of the
artifact service engine.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import importlib.metadata
import inspect
from pathlib import Path
from typing import Any, Sequence

from compiler.ir.model import canonical_json_bytes, load_strict_json

from .constants import (
    CONFIG_SHA256,
    INDEX_SHA256,
    LAYER_COUNT,
    TARGET_CONTEXT_TOKENS,
    TRANSFORMERS_CONFIG_SOURCE_SHA256,
    TRANSFORMERS_MODEL_SOURCE_SHA256,
    TRANSFORMERS_VERSION,
)


REFERENCE_REPORT_SCHEMA = "opentallas.qwen3.official_reference_report.v1"


class Qwen3ReferenceError(RuntimeError):
    """Raised when the official reference environment or execution differs."""


@dataclass(frozen=True)
class ReferenceSpanResult:
    logits: Any
    report: dict[str, Any]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(16 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _tensor_sha256(tensor: Any) -> str:
    import torch

    raw = tensor.detach().contiguous().cpu().view(torch.uint8).numpy().tobytes()
    return hashlib.sha256(raw).hexdigest()


class OfficialQwen3Reference:
    """Execute official source semantics with layer-at-a-time checkpoint loading."""

    def __init__(
        self,
        snapshot: Path,
        *,
        device: str = "cuda",
        attention_backend: str = "sdpa",
    ):
        try:
            observed_version = importlib.metadata.version("transformers")
        except importlib.metadata.PackageNotFoundError as exc:
            raise Qwen3ReferenceError("Transformers is not installed") from exc
        if observed_version != TRANSFORMERS_VERSION:
            raise Qwen3ReferenceError(
                f"official reference requires transformers {TRANSFORMERS_VERSION}, got {observed_version}"
            )
        try:
            import torch
            import transformers.models.qwen3.configuration_qwen3 as configuration_module
            import transformers.models.qwen3.modeling_qwen3 as modeling_module
            from transformers.cache_utils import DynamicCache
            from transformers.models.qwen3.configuration_qwen3 import Qwen3Config
        except ImportError as exc:
            raise Qwen3ReferenceError(
                f"cannot import official Qwen3 reference: {exc}"
            ) from exc
        if (
            _sha256_file(Path(inspect.getfile(modeling_module)))
            != TRANSFORMERS_MODEL_SOURCE_SHA256
        ):
            raise Qwen3ReferenceError(
                "installed modeling_qwen3.py differs from the source lock"
            )
        if (
            _sha256_file(Path(inspect.getfile(configuration_module)))
            != TRANSFORMERS_CONFIG_SOURCE_SHA256
        ):
            raise Qwen3ReferenceError(
                "installed configuration_qwen3.py differs from the source lock"
            )
        self.snapshot = Path(snapshot).resolve()
        if not self.snapshot.is_dir():
            raise Qwen3ReferenceError(f"snapshot is not a directory: {self.snapshot}")
        config_path = self.snapshot / "config.json"
        index_path = self.snapshot / "model.safetensors.index.json"
        if (
            _sha256_file(config_path) != CONFIG_SHA256
            or _sha256_file(index_path) != INDEX_SHA256
        ):
            raise Qwen3ReferenceError(
                "snapshot config or index differs from the pinned release"
            )
        try:
            index = load_strict_json(index_path)
        except (OSError, ValueError) as exc:
            raise Qwen3ReferenceError(f"cannot load checkpoint index: {exc}") from exc
        weight_map = index.get("weight_map")
        if not isinstance(weight_map, dict) or len(weight_map) != 399:
            raise Qwen3ReferenceError("checkpoint index does not contain 399 tensors")
        self.weight_map = weight_map
        self.config = Qwen3Config.from_json_file(str(config_path))
        if attention_backend not in {"eager", "sdpa"}:
            raise Qwen3ReferenceError("attention_backend must be eager or sdpa")
        self.config._attn_implementation = attention_backend
        if device.startswith("cuda") and not torch.cuda.is_available():
            raise Qwen3ReferenceError("CUDA was requested but is unavailable")
        self.device = torch.device(device)
        self.attention_backend = attention_backend
        self.modeling = modeling_module
        self.cache = DynamicCache()
        self.position = 0

    def _load_tensors(self, names: Sequence[str]) -> dict[str, Any]:
        try:
            from safetensors import safe_open
        except ImportError as exc:
            raise Qwen3ReferenceError("safetensors is not installed") from exc
        by_shard: dict[str, list[str]] = defaultdict(list)
        for name in names:
            shard = self.weight_map.get(name)
            if not isinstance(shard, str):
                raise Qwen3ReferenceError(f"checkpoint index lacks tensor {name!r}")
            by_shard[shard].append(name)
        result: dict[str, Any] = {}
        for shard, shard_names in by_shard.items():
            path = self.snapshot / shard
            try:
                with safe_open(path, framework="pt", device="cpu") as handle:
                    for name in shard_names:
                        result[name] = handle.get_tensor(name)
            except Exception as exc:
                raise Qwen3ReferenceError(f"cannot read {shard}: {exc}") from exc
        return result

    def _layer(self, layer_index: int) -> Any:
        import torch

        prefix = f"model.layers.{layer_index}."
        names = sorted(name for name in self.weight_map if name.startswith(prefix))
        if len(names) != 11:
            raise Qwen3ReferenceError(
                f"layer {layer_index} does not contain 11 tensors"
            )
        values = self._load_tensors(names)
        with torch.device("meta"):
            layer = self.modeling.Qwen3DecoderLayer(self.config, layer_index)
        state = {
            name.removeprefix(prefix): value.to(
                device=self.device, dtype=torch.bfloat16
            )
            for name, value in values.items()
        }
        try:
            result = layer.load_state_dict(state, strict=True, assign=True)
        except Exception as exc:
            raise Qwen3ReferenceError(
                f"cannot bind official layer {layer_index}: {exc}"
            ) from exc
        if result.missing_keys or result.unexpected_keys:
            raise Qwen3ReferenceError(
                f"official layer {layer_index} state coverage differs"
            )
        return layer.eval()

    def _mask(self, dtype: Any, start: int, span: int) -> Any | None:
        import torch

        if start == 0 or span == 1:
            return None
        total = start + span
        allowed = torch.arange(total, device=self.device)[None, :] <= (
            start + torch.arange(span, device=self.device)[:, None]
        )
        mask = torch.full(
            (1, 1, span, total),
            torch.finfo(dtype).min,
            dtype=dtype,
            device=self.device,
        )
        return mask.masked_fill(allowed[None, None, :, :], 0)

    def reset(self) -> None:
        import torch
        from transformers.cache_utils import DynamicCache

        self.cache = DynamicCache()
        self.position = 0
        if self.device.type == "cuda":
            torch.cuda.empty_cache()

    def run_span(
        self,
        token_ids: Sequence[int],
        *,
        capture_layer_hashes: bool = False,
    ) -> ReferenceSpanResult:
        import torch
        import torch.nn.functional as functional

        if (
            isinstance(token_ids, (str, bytes))
            or not isinstance(token_ids, Sequence)
            or not token_ids
        ):
            raise Qwen3ReferenceError("token_ids must be a nonempty sequence")
        if any(
            isinstance(item, bool)
            or not isinstance(item, int)
            or item < 0
            or item >= int(self.config.vocab_size)
            for item in token_ids
        ):
            raise Qwen3ReferenceError("token ID is outside the Qwen3 vocabulary")
        start = self.position
        span = len(token_ids)
        if start + span > TARGET_CONTEXT_TOKENS:
            raise Qwen3ReferenceError("reference span would exceed 8,000 tokens")
        tokens = torch.tensor([list(token_ids)], dtype=torch.long, device=self.device)
        positions = torch.arange(start, start + span, device=self.device)
        position_ids = positions.unsqueeze(0)
        layer_hashes: list[dict[str, Any]] = []
        with torch.no_grad():
            embedding = self._load_tensors(["model.embed_tokens.weight"])[
                "model.embed_tokens.weight"
            ].to(device=self.device, dtype=torch.bfloat16)
            hidden = functional.embedding(tokens, embedding)
            del embedding
            rotary = self.modeling.Qwen3RotaryEmbedding(
                self.config, device=self.device
            ).to(self.device)
            position_embeddings = rotary(hidden, position_ids)
            del rotary
            attention_mask = self._mask(hidden.dtype, start, span)
            for layer_index in range(LAYER_COUNT):
                layer = self._layer(layer_index)
                hidden = layer(
                    hidden,
                    attention_mask=attention_mask,
                    position_ids=position_ids,
                    past_key_value=self.cache,
                    output_attentions=False,
                    use_cache=True,
                    cache_position=positions,
                    position_embeddings=position_embeddings,
                )[0]
                if capture_layer_hashes:
                    layer_hashes.append(
                        {
                            "layer": layer_index + 1,
                            "sha256": _tensor_sha256(hidden),
                            "shape": list(hidden.shape),
                        }
                    )
                del layer
                if self.device.type == "cuda":
                    torch.cuda.empty_cache()
            final_weight = self._load_tensors(["model.norm.weight"])[
                "model.norm.weight"
            ].to(device=self.device, dtype=torch.bfloat16)
            with torch.device("meta"):
                final_norm = self.modeling.Qwen3RMSNorm(
                    int(self.config.hidden_size), eps=float(self.config.rms_norm_eps)
                )
            final_norm.load_state_dict(
                {"weight": final_weight}, strict=True, assign=True
            )
            hidden = final_norm(hidden)
            last = hidden[:, -1:, :]
            head = self._load_tensors(["lm_head.weight"])["lm_head.weight"].to(
                device=self.device, dtype=torch.bfloat16
            )
            logits = functional.linear(last, head)
            self.position = start + span
        report_body = {
            "attention_backend": self.attention_backend,
            "final_context_tokens": self.position,
            "initial_context_tokens": start,
            "layer_boundaries": layer_hashes,
            "logits": {
                "argmax_token_id": int(logits[0, -1].argmax().item()),
                "dtype": str(logits.dtype).removeprefix("torch."),
                "sha256": _tensor_sha256(logits),
                "shape": list(logits.shape),
            },
            "schema": REFERENCE_REPORT_SCHEMA,
            "span_tokens": span,
            "transformers_version": TRANSFORMERS_VERSION,
        }
        return ReferenceSpanResult(
            logits,
            {
                **report_body,
                "report_id": hashlib.sha256(
                    canonical_json_bytes(report_body)
                ).hexdigest(),
            },
        )


def compare_logits(
    service_logits: Any, reference_logits: Any, *, atol: float = 0.0
) -> dict[str, Any]:
    """Compare full vocabulary logits without accepting an argmax-only match."""

    if tuple(service_logits.shape) != tuple(reference_logits.shape):
        raise Qwen3ReferenceError("service/reference logits shapes differ")
    difference = (
        service_logits.detach().float().cpu() - reference_logits.detach().float().cpu()
    ).abs()
    maximum = float(difference.max().item())
    mean = float(difference.mean().item())
    body = {
        "argmax_match": int(service_logits.argmax().item())
        == int(reference_logits.argmax().item()),
        "atol": float(atol),
        "element_count": int(difference.numel()),
        "maximum_absolute_error": maximum,
        "mean_absolute_error": mean,
        "passed": maximum <= atol,
        "schema": "opentallas.qwen3.logits_differential.v1",
        "service_sha256": _tensor_sha256(service_logits),
        "reference_sha256": _tensor_sha256(reference_logits),
    }
    return {**body, "report_id": hashlib.sha256(canonical_json_bytes(body)).hexdigest()}


__all__ = [
    "OfficialQwen3Reference",
    "Qwen3ReferenceError",
    "REFERENCE_REPORT_SCHEMA",
    "ReferenceSpanResult",
    "compare_logits",
]
