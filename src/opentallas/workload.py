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
        # A layer that shares another layer's cache (DeepSeek-V4.1 CSA2
        # Reindex/Reuse) reads it but writes and stores nothing of it.
        owner = group.kv_owner
        window_entry = group.effective_window_entry_bytes
        if group.kind == "compressed_sparse":
            main_entries = min(group.top_k, compressed_entries)
            # A profile may declare a compressed-entry count below which its
            # implementation skips the index scan. No shipped profile declares
            # one: the threshold this was written for turned out to be a gap in
            # the measuring instrument rather than a property of the model, and
            # the released implementation scans exactly context/4 at every
            # context measured, 1,001 through 200,001. Zero is the unconditional
            # scan and is what every profile sets. See the retraction under
            # metadata.index_scan_threshold in each DeepSeek profile.
            scans_index = (
                group.scans_index
                and compressed_entries >= group.index_scan_min_compressed_entries
            )
            scanned = compressed_entries if scans_index else 0
            if scanned and group.index_scan_entries_cap:
                # Hierarchical indexer: only the candidate pool is scored.
                scanned = min(scanned, group.index_scan_entries_cap)
            index_read = count * scanned * group.index_entry_bytes
            index_write = (
                count * group.index_entry_bytes / group.compression_ratio if owner else 0.0
            )
            index_storage = (
                count * compressed_entries * group.index_entry_bytes if owner else 0.0
            )
            detail["index_scanned"] = scans_index
            read += index_read
            write += index_write
            storage += index_storage
            detail["index_entries_scanned_per_layer"] = float(scanned)
            detail["index_read_bytes"] = index_read
        if owner and window_entry == group.entry_bytes:
            # The original arithmetic, kept verbatim so every profile that
            # predates cross-layer sharing reproduces byte for byte.
            read += count * (window + main_entries) * group.entry_bytes
            # One full-resolution window entry plus an amortized compressed entry.
            write += count * group.entry_bytes * (1.0 + 1.0 / group.compression_ratio)
            storage += count * (window + compressed_entries) * group.entry_bytes
        else:
            read += count * window * window_entry + count * main_entries * group.entry_bytes
            write += count * window_entry
            storage += count * window * window_entry
            if owner:
                write += count * group.entry_bytes / group.compression_ratio
                storage += count * compressed_entries * group.entry_bytes
        if not owner:
            detail["kv_owner"] = False
        detail["main_entries_read_per_layer"] = float(window + main_entries)
        detail["compressed_entries_stored_per_layer"] = float(
            compressed_entries if owner else 0
        )

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


HBM_RESIDENT_REGIONS = "hbm_resident_regions"
HBM_RESIDENT_WEIGHT_BYTES = "hbm_resident_weight_bytes"


def hbm_resident_regions(model: ModelProfile) -> tuple[dict[str, float | str], ...]:
    """Immutable weight regions the model holds in its KV store, not its weight store.

    A model may declare that part of its checkpoint is resident in the same
    memory that holds the KV cache -- DeepSeek-V4.1's 202.8 GB of Engram lookup
    tables in wafer-edge HBM are the case this was written for.  Such a region
    is not streamed with the weights and is not per-user state: it takes
    capacity from whichever pipeline stage owns its layer, once, and it is read
    by row on every token, which costs that stage's KV bandwidth.

    Each region declares its own ``layer_id``, so the stage that pays is
    derived from the same layer partition as everything else rather than named.
    A model that declares none -- every profile that predates this -- gets an
    empty tuple and is untouched.
    """

    declared = model.metadata.get(HBM_RESIDENT_REGIONS) or ()
    if not isinstance(declared, (list, tuple)):
        raise ValueError(f"metadata.{HBM_RESIDENT_REGIONS} must be a list of regions")
    regions: list[dict[str, float | str]] = []
    for index, region in enumerate(declared):
        if not isinstance(region, dict):
            raise ValueError(f"metadata.{HBM_RESIDENT_REGIONS}[{index}] must be a mapping")
        try:
            layer_id = int(region["layer_id"])
            resident = float(region["bytes"])
            read = float(region["read_bytes_per_token"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"metadata.{HBM_RESIDENT_REGIONS}[{index}] requires layer_id, bytes "
                "and read_bytes_per_token"
            ) from exc
        if not 0 <= layer_id < model.num_layers:
            raise ValueError(
                f"metadata.{HBM_RESIDENT_REGIONS}[{index}] layer_id {layer_id} is "
                f"outside the {model.num_layers} layers of {model.name}"
            )
        if resident < 0 or read < 0:
            raise ValueError(
                f"metadata.{HBM_RESIDENT_REGIONS}[{index}] bytes and "
                "read_bytes_per_token must not be negative"
            )
        regions.append(
            {
                "label": str(region.get("label", f"hbm_resident_l{layer_id}")),
                "layer_id": float(layer_id),
                "bytes": resident,
                "read_bytes_per_token": read,
            }
        )
    return tuple(regions)


def hbm_resident_weight_bytes(model: ModelProfile) -> float:
    """Total declared KV-store-resident weight bytes, checked against the regions.

    The scalar is what the profile advertises and the regions are what the
    capacity model spends; if they ever disagree the profile is wrong and says
    so here rather than silently charging a different number to each.
    """

    regions = hbm_resident_regions(model)
    total = sum(float(region["bytes"]) for region in regions)
    declared = float(model.metadata.get(HBM_RESIDENT_WEIGHT_BYTES, 0.0))
    if abs(declared - total) > 1.0:
        raise ValueError(
            f"{model.name}: metadata.{HBM_RESIDENT_WEIGHT_BYTES} is {declared:,.0f} B "
            f"but metadata.{HBM_RESIDENT_REGIONS} sum to {total:,.0f} B"
        )
    return declared


def _per_layer_hbm_resident(
    model: ModelProfile, field_name: str
) -> tuple[float, ...]:
    values = [0.0] * model.num_layers
    for region in hbm_resident_regions(model):
        values[int(region["layer_id"])] += float(region[field_name])
    return tuple(values)


def per_layer_hbm_resident_bytes(model: ModelProfile) -> tuple[float, ...]:
    """KV-store capacity each ordered layer's resident regions occupy."""

    return _per_layer_hbm_resident(model, "bytes")


def per_layer_hbm_resident_read_bytes(model: ModelProfile) -> tuple[float, ...]:
    """KV-store read bytes each ordered layer's resident regions cost per token."""

    return _per_layer_hbm_resident(model, "read_bytes_per_token")


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
    # Resident lookup regions share the KV store's read path, so their rows are
    # KV read bytes.  They are written at load and are not per-user, so they add
    # nothing to writes and nothing to storage_bytes_per_user.
    for region in hbm_resident_regions(model):
        read = float(region["read_bytes_per_token"])
        reads += read
        breakdown.append(
            {
                "kind": "hbm_resident_lookup",
                "label": region["label"],
                "layer_id": region["layer_id"],
                "resident_bytes": region["bytes"],
                "read_bytes": read,
                "write_bytes": 0.0,
                "storage_bytes_per_user": 0.0,
                "evidence": (
                    "immutable region resident in the KV store, read by row on "
                    "every decode token; metadata.hbm_resident_regions"
                ),
            }
        )
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
    return tuple(read + write for read, write in per_layer_kv_read_write(model, context_tokens))


def per_layer_kv_read_write(
    model: ModelProfile, context_tokens: int
) -> tuple[tuple[float, float], ...]:
    """Return algorithmic KV read/write bytes for each ordered model layer.

    A layer that owns a resident lookup region in the KV store reads that
    region's rows out of the same store on every token, so those bytes belong to
    this layer's KV read and therefore to whichever pipeline stage holds it.
    """

    resident_read = per_layer_hbm_resident_read_bytes(model)
    layers: list[tuple[float, float]] = []
    for group, resident in zip(layer_groups(model), resident_read):
        read, write = _group_traffic(group, context_tokens)[:2]
        layers.append((read + resident, write))
    return tuple(layers)


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
