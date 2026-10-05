"""Synthetic and checkpoint-router trace generation/analysis."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from pathlib import Path
from typing import Any

import numpy as np

from .profiling import SourceSpec, fetch_tensor_bytes
from .schema import ModelProfile
from .workload import expected_expert_coverage


@dataclass(frozen=True)
class CoverageStat:
    batch_size: int
    analytical_coverage: float
    trace_mean_coverage: float
    trace_p95_coverage: float
    mean_load_balance_efficiency: float
    p05_load_balance_efficiency: float
    mean_engaged_device_fraction: float


def generate_synthetic_routes(
    model: ModelProfile,
    tokens: int,
    *,
    seed: int = 7,
    zipf_alpha: float = 0.0,
    persistence: float = 0.0,
) -> np.ndarray:
    """Generate [layers,tokens,top-k] routes using Gumbel top-k sampling.

    ``zipf_alpha=0`` is uniform. Expert ranks are independently permuted per
    layer so a hotspot does not accidentally map to one global physical lane.
    ``persistence`` reuses a fraction of the previous token's choices, providing
    a bounded correlation stress case without pretending to be a real trace.
    """

    if tokens <= 0:
        raise ValueError("tokens must be positive")
    if zipf_alpha < 0 or not 0 <= persistence < 1:
        raise ValueError("invalid synthetic trace parameters")
    rng = np.random.default_rng(seed)
    n, k, layers = model.num_experts, model.experts_per_token, model.num_layers
    ranks = np.arange(1, n + 1, dtype=np.float64)
    log_base = -zipf_alpha * np.log(ranks)
    routes = np.empty((layers, tokens, k), dtype=np.uint16)
    for layer in range(layers):
        permutation = rng.permutation(n)
        logits = np.empty(n, dtype=np.float64)
        logits[permutation] = log_base
        noise = rng.gumbel(size=(tokens, n))
        selected = np.argpartition(logits[None, :] + noise, -k, axis=1)[:, -k:]
        if persistence:
            reuse = rng.random(tokens - 1) < persistence
            for token in np.flatnonzero(reuse) + 1:
                keep = max(1, k // 2)
                selected[token, :keep] = selected[token - 1, :keep]
                if len(set(int(x) for x in selected[token])) != k:
                    # Deterministic repair is rare and avoids duplicate experts.
                    used = set(int(x) for x in selected[token, :keep])
                    fill = [int(x) for x in selected[token, keep:] if int(x) not in used]
                    fill.extend(int(x) for x in permutation if int(x) not in used and int(x) not in fill)
                    selected[token, keep:] = fill[: k - keep]
        routes[layer] = selected.astype(np.uint16)
    return routes


def summarize_routes(
    routes: np.ndarray,
    num_experts: int,
    batches: tuple[int, ...],
    *,
    device_count: int = 16,
) -> list[CoverageStat]:
    layers, tokens, top_k = routes.shape
    stats: list[CoverageStat] = []
    for batch in batches:
        coverages: list[float] = []
        efficiencies: list[float] = []
        engaged: list[float] = []
        for start in range(0, tokens - batch + 1, batch):
            window = routes[:, start : start + batch]
            for layer in range(layers):
                flat = window[layer].reshape(-1)
                counts = np.bincount(flat, minlength=num_experts)
                active = np.flatnonzero(counts)
                coverages.append(active.size / num_experts)
                if active.size:
                    efficiencies.append(float(counts[active].mean() / counts[active].max()))
                    engaged.append(np.unique(active % device_count).size / device_count)
        if not coverages:
            continue
        stats.append(
            CoverageStat(
                batch_size=batch,
                analytical_coverage=expected_expert_coverage(num_experts, top_k, batch),
                trace_mean_coverage=float(np.mean(coverages)),
                trace_p95_coverage=float(np.percentile(coverages, 95)),
                mean_load_balance_efficiency=float(np.mean(efficiencies)),
                p05_load_balance_efficiency=float(np.percentile(efficiencies, 5)),
                mean_engaged_device_fraction=float(np.mean(engaged)),
            )
        )
    return stats


def _decode_tensor(raw: bytes, metadata: dict[str, Any]) -> np.ndarray:
    dtype = metadata["dtype"]
    shape = tuple(int(value) for value in metadata["shape"])
    if dtype == "BF16":
        words = np.frombuffer(raw, dtype="<u2")
        array = (words.astype(np.uint32) << 16).view(np.float32)
    elif dtype == "F32":
        array = np.frombuffer(raw, dtype="<f4")
    elif dtype == "I64":
        array = np.frombuffer(raw, dtype="<i8")
    elif dtype == "I32":
        array = np.frombuffer(raw, dtype="<i4")
    else:
        raise ValueError(f"router sampler does not support dtype {dtype}")
    return array.reshape(shape)


def _topk(scores: np.ndarray, k: int) -> np.ndarray:
    return np.argpartition(scores, -k, axis=1)[:, -k:]


def checkpoint_router_sample(
    spec: SourceSpec,
    model: ModelProfile,
    cache_dir: Path,
    *,
    tokens: int = 8,
    seed: int = 11,
) -> dict[str, Any]:
    """Route synthetic activations through a small sample of real gate weights.

    The result measures checkpoint gate/bias behavior, not production token
    traffic. DeepSeek hash layers additionally use their exact token-id table.
    """

    rng = np.random.default_rng(seed)
    token_ids = np.array([0, 1, 42, 1024, 8192, 65535, 128000, 129000], dtype=np.int64)[:tokens]
    if token_ids.size < tokens:
        token_ids = rng.integers(0, 129280, size=tokens, dtype=np.int64)
    samples: list[dict[str, Any]] = []
    if spec.adapter == "deepseek_v4":
        for layer in range(min(3, model.num_layers)):
            name = f"layers.{layer}.ffn.gate.tid2eid"
            raw, meta = fetch_tensor_bytes(spec, name, cache_dir)
            table = _decode_tensor(raw, meta)
            routes = table[token_ids % table.shape[0]]
            samples.append({
                "layer": layer,
                "mode": "exact_hash_table",
                "routes": routes.astype(int).tolist(),
                "unique_experts": int(np.unique(routes).size),
            })
        chosen_layers = sorted(set([3, model.num_layers // 2, model.num_layers - 1]))
        prefix = "layers"
        bias_suffix = "bias"
    else:
        chosen_layers = sorted(set([1, model.num_layers // 2, model.num_layers - 1]))
        prefix = "language_model.model.layers"
        bias_suffix = "e_score_correction_bias"
    activations = rng.standard_normal((tokens, model.hidden_size), dtype=np.float32)
    activations /= np.sqrt(np.mean(activations**2, axis=1, keepdims=True))
    for layer in chosen_layers:
        if spec.adapter == "deepseek_v4":
            base = f"{prefix}.{layer}.ffn.gate"
        else:
            base = f"{prefix}.{layer}.block_sparse_moe.gate"
        weight_raw, weight_meta = fetch_tensor_bytes(spec, f"{base}.weight", cache_dir)
        bias_raw, bias_meta = fetch_tensor_bytes(spec, f"{base}.{bias_suffix}", cache_dir)
        weight = _decode_tensor(weight_raw, weight_meta)
        bias = _decode_tensor(bias_raw, bias_meta)
        logits = activations @ weight.T
        if spec.adapter == "deepseek_v4":
            # sqrt(softplus), implemented stably; the bias affects choice only.
            scores = np.sqrt(np.log1p(np.exp(-np.abs(logits))) + np.maximum(logits, 0))
        else:
            scores = 1.0 / (1.0 + np.exp(-np.clip(logits, -30, 30)))
        routes = _topk(scores + bias[None, :], model.experts_per_token)
        samples.append({
            "layer": layer,
            "mode": "checkpoint_gate_with_seeded_gaussian_activations",
            "routes": routes.astype(int).tolist(),
            "unique_experts": int(np.unique(routes).size),
            "bias_min": float(bias.min()),
            "bias_max": float(bias.max()),
            "weight_rms": float(np.sqrt(np.mean(weight**2))),
        })
    return {
        "model": model.name,
        "source_repo": spec.repo,
        "source_revision": spec.revision,
        "tokens": tokens,
        "seed": seed,
        "activation_status": "synthetic Gaussian; not a production activation trace",
        "token_id_status": "fixed diagnostic IDs; exact only for hash-table layers",
        "samples": samples,
    }


def trace_report(model: ModelProfile, routes: np.ndarray, batches: tuple[int, ...]) -> dict[str, Any]:
    return {
        "model": model.name,
        "status": "synthetic",
        "shape": list(routes.shape),
        "batches": [asdict(stat) for stat in summarize_routes(routes, model.num_experts, batches)],
        "sample_routes": routes[:, : min(4, routes.shape[1]), :].astype(int).tolist(),
    }
