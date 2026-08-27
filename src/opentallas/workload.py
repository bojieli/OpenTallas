"""Model-side accounting independent of any hardware implementation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Iterable

from .schema import AttentionGroup, ModelProfile


@dataclass(frozen=True)
class KVTraffic:
    """KV traffic for one user generating one target token."""

    read_bytes: float
    write_bytes: float
    storage_bytes_per_user: float
    breakdown: tuple[dict[str, float | str], ...]

    @property
    def total_transfer_bytes(self) -> float:
        return self.read_bytes + self.write_bytes

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class WeightTraffic:
    dense_bytes: float
    routed_bytes: float
    routed_expert_coverage: float
    distinct_experts_per_layer: float

    @property
    def total_bytes(self) -> float:
        return self.dense_bytes + self.routed_bytes


def expected_expert_coverage(num_experts: int, experts_per_token: int, samples: int) -> float:
    """Expected fraction of experts touched by ``samples`` independent routes.

    This is the C1 occupancy model. Trace-derived coverage can replace it at the
    simulator boundary; the analytical fallback remains useful for sweeps.
    ``log1p``/``expm1`` keep the calculation stable for very large batches.
    """

    if samples <= 0:
        return 0.0
    if experts_per_token >= num_experts:
        return 1.0
    untouched_log = samples * math.log1p(-experts_per_token / num_experts)
    return -math.expm1(untouched_log)


def expected_engaged_devices(device_count: int, distinct_experts: float) -> float:
    """Expected expert-parallel devices holding at least one selected expert."""

    if device_count <= 1:
        return 1.0
    if distinct_experts <= 0:
        return 1.0
    untouched = math.exp(distinct_experts * math.log1p(-1.0 / device_count))
    return max(1.0, min(float(device_count), device_count * (1.0 - untouched)))


def weight_traffic(
    model: ModelProfile,
    batch_size: int,
    *,
    positions_per_step: int = 1,
    measured_coverage: float | None = None,
) -> WeightTraffic:
    samples = batch_size * positions_per_step
    coverage = (
        expected_expert_coverage(model.num_experts, model.experts_per_token, samples)
        if measured_coverage is None
        else measured_coverage
    )
    if not 0 <= coverage <= 1:
        raise ValueError(f"expert coverage must be in [0,1], got {coverage}")
    return WeightTraffic(
        dense_bytes=model.dense_weight_bytes,
        routed_bytes=model.routed_weight_bytes * coverage,
        routed_expert_coverage=coverage,
        distinct_experts_per_layer=model.num_experts * coverage,
    )


def draft_weight_traffic(
    model: ModelProfile,
    batch_size: int,
    *,
    draft_tokens: int,
) -> WeightTraffic:
    """Weight traffic for an internal/speculative draft submodel.

    Draft weights are a profile input rather than a DeepSeek-specific branch.
    A block of draft positions shares dense weights and touches the union of
    routed experts across ``batch_size * draft_tokens`` samples.
    """

    samples = batch_size * draft_tokens
    coverage = expected_expert_coverage(
        model.num_experts,
        model.experts_per_token,
        samples,
    )
    return WeightTraffic(
        dense_bytes=model.draft_dense_weight_bytes,
        routed_bytes=model.draft_routed_weight_bytes * coverage,
        routed_expert_coverage=coverage,
        distinct_experts_per_layer=model.num_experts * coverage,
    )


def _group_traffic(group: AttentionGroup, context_tokens: int) -> tuple[float, float, float, dict]:
    count = group.count
    window = min(context_tokens, group.window_tokens) if group.window_tokens else 0
    read = write = storage = 0.0
    detail: dict[str, float | str] = {
        "label": group.label or group.kind,
        "kind": group.kind,
        "layers": float(count),
    }

    if group.kind == "window":
        read = count * window * group.entry_bytes
        write = count * group.entry_bytes
        storage = count * window * group.entry_bytes
        detail["entries_read_per_layer"] = float(window)

    elif group.kind in {"compressed_sparse", "compressed_dense"}:
        compressed_entries = math.ceil(context_tokens / group.compression_ratio)
        main_entries = compressed_entries
        if group.kind == "compressed_sparse":
            main_entries = min(group.top_k, compressed_entries)
            index_read = count * compressed_entries * group.index_entry_bytes
            index_write = count * group.index_entry_bytes / group.compression_ratio
            index_storage = count * compressed_entries * group.index_entry_bytes
            read += index_read
            write += index_write
            storage += index_storage
            detail["index_entries_scanned_per_layer"] = float(compressed_entries)
            detail["index_read_bytes"] = index_read
        read += count * (window + main_entries) * group.entry_bytes
        # One full-resolution window entry plus an amortized compressed entry.
        write += count * group.entry_bytes * (1.0 + 1.0 / group.compression_ratio)
        storage += count * (window + compressed_entries) * group.entry_bytes
        detail["main_entries_read_per_layer"] = float(window + main_entries)
        detail["compressed_entries_stored_per_layer"] = float(compressed_entries)

    elif group.kind in {"dense_mla", "dense_kv"}:
        read = count * context_tokens * group.entry_bytes
        write = count * group.entry_bytes
        storage = count * context_tokens * group.entry_bytes
        detail["entries_read_per_layer"] = float(context_tokens)

    elif group.kind == "recurrent":
        per_layer_write = (
            group.recurrent_state_bytes
            if group.recurrent_write_bytes is None
            else group.recurrent_write_bytes
        )
        read = count * group.recurrent_state_bytes
        write = count * per_layer_write
        storage = count * group.recurrent_state_bytes
        detail["state_bytes_per_layer"] = group.recurrent_state_bytes

    detail["read_bytes"] = read
    detail["write_bytes"] = write
    detail["storage_bytes_per_user"] = storage
    return read, write, storage, detail


def kv_traffic(model: ModelProfile, context_tokens: int) -> KVTraffic:
    """Compute exact profile-defined C2 KV traffic for one user/token."""

    if context_tokens <= 0:
        raise ValueError("context_tokens must be positive")
    if context_tokens > model.max_context_tokens:
        raise ValueError(
            f"context {context_tokens} exceeds {model.name} maximum {model.max_context_tokens}"
        )
    reads = writes = storage = 0.0
    breakdown: list[dict[str, float | str]] = []
    for group in model.attention_groups:
        read, write, stored, detail = _group_traffic(group, context_tokens)
        reads += read
        writes += write
        storage += stored
        breakdown.append(detail)
    return KVTraffic(reads, writes, storage, tuple(breakdown))


def rho_one(model: ModelProfile, context_tokens: int) -> float:
    """Architecture-only target screen: active weight bytes / KV read bytes."""

    active_weight_bytes = (
        model.dense_weight_bytes
        + model.routed_weight_bytes * model.routed_fraction_per_token
    )
    return active_weight_bytes / kv_traffic(model, context_tokens).read_bytes


def layer_groups(model: ModelProfile) -> tuple[AttentionGroup, ...]:
    """Expand group counts to one record per layer.

    Profiles may provide ``metadata.attention_sequence`` containing group labels.
    This preserves alternating hybrid layouts for pipeline-balance analysis.
    """

    sequence = model.metadata.get("attention_sequence")
    by_label = {group.label or group.kind: group for group in model.attention_groups}
    if sequence:
        if len(sequence) != model.num_layers:
            raise ValueError("metadata.attention_sequence length does not match num_layers")
        try:
            return tuple(
                AttentionGroup(**{**asdict(by_label[label]), "count": 1}) for label in sequence
            )
        except KeyError as exc:
            raise ValueError(f"unknown attention group label in sequence: {exc.args[0]}") from exc
    expanded: list[AttentionGroup] = []
    for group in model.attention_groups:
        expanded.extend(AttentionGroup(**{**asdict(group), "count": 1}) for _ in range(group.count))
    return tuple(expanded)


def per_layer_kv_transfer(model: ModelProfile, context_tokens: int) -> tuple[float, ...]:
    return tuple(
        sum(_group_traffic(group, context_tokens)[:2]) for group in layer_groups(model)
    )


def per_layer_kv_read_write(
    model: ModelProfile, context_tokens: int
) -> tuple[tuple[float, float], ...]:
    """Return algorithmic KV read/write bytes for each ordered model layer."""

    return tuple(
        _group_traffic(group, context_tokens)[:2] for group in layer_groups(model)
    )


def per_layer_kv_storage(model: ModelProfile, context_tokens: int) -> tuple[float, ...]:
    """Return persistent KV/state bytes per user for each ordered model layer."""

    return tuple(
        _group_traffic(group, context_tokens)[2] for group in layer_groups(model)
    )


def linear_partition(values: Iterable[float], partitions: int) -> tuple[tuple[int, int], ...]:
    """Minimax contiguous partition used for multi-wafer pipeline stages."""

    vals = tuple(float(value) for value in values)
    n = len(vals)
    if n == 0:
        return tuple()
    partitions = max(1, min(partitions, n))
    prefix = [0.0]
    for value in vals:
        prefix.append(prefix[-1] + value)
    dp = [[math.inf] * (partitions + 1) for _ in range(n + 1)]
    cut = [[0] * (partitions + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    for i in range(1, n + 1):
        dp[i][1] = prefix[i]
    for p in range(2, partitions + 1):
        for i in range(p, n + 1):
            for j in range(p - 1, i):
                cost = max(dp[j][p - 1], prefix[i] - prefix[j])
                if cost < dp[i][p]:
                    dp[i][p] = cost
                    cut[i][p] = j
    ranges: list[tuple[int, int]] = []
    i, p = n, partitions
    while p > 1:
        j = cut[i][p]
        ranges.append((j, i))
        i, p = j, p - 1
    ranges.append((0, i))
    ranges.reverse()
    return tuple(ranges)
