"""Strict, dependency-light schemas used by every simulator component.

The schema keeps model and hardware details outside the equations.  JSON input
is intentionally boring: it is inspectable, diffable, and can be generated from
checkpoint metadata without importing a model implementation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any, Iterable


class ValidationError(ValueError):
    """Raised when a profile would make a simulation ambiguous or invalid."""


def _positive(name: str, value: float) -> None:
    if value <= 0:
        raise ValidationError(f"{name} must be > 0, got {value!r}")


def _fraction(name: str, value: float, *, allow_zero: bool = False) -> None:
    lower_ok = value >= 0 if allow_zero else value > 0
    if not lower_ok or value > 1:
        op = "[0, 1]" if allow_zero else "(0, 1]"
        raise ValidationError(f"{name} must be in {op}, got {value!r}")


@dataclass(frozen=True)
class AttentionGroup:
    """A group of layers sharing one KV traffic mechanism.

    Supported kinds are deliberately architectural rather than model-named:

    * ``window``: a bounded sliding-window cache;
    * ``compressed_sparse``: full scan of a compact index plus a top-k KV gather;
    * ``compressed_dense``: dense read of a temporally compressed KV cache;
    * ``dense_mla``: context-linear latent KV cache;
    * ``dense_kv``: context-linear full K/V cache, including GQA;
    * ``recurrent``: context-independent state read/modify/write.
    """

    kind: str
    count: int
    entry_bytes: float = 0.0
    window_tokens: int = 0
    compression_ratio: int = 1
    top_k: int = 0
    index_entry_bytes: float = 0.0
    #: Compressed-entry count at or above which the sparse index is scanned.
    #: **Every shipped profile sets this to zero — always scan — and the field
    #: survives only as a hook.**
    #:
    #: It was introduced on the reading that the released DeepSeek implementation
    #: scans no index below roughly 8,001 compressed entries, and that reading was
    #: an instrumentation artifact: the oracle wrapped ``Attention.forward`` and
    #: not ``Indexer.forward``, so a rung whose prefill did not tile counted no
    #: index at all — and the two short rungs were exactly the untiled ones. The
    #: threshold measured was the boundary of the instrument. Re-instrumented, the
    #: scan is exactly ``context / 4`` at every context from 1,001 to 200,001.
    #:
    #: The docstring that stood here said "Measured, not assumed", which is the
    #: grade error this repository has now made three times; the retraction is in
    #: each DeepSeek profile under ``metadata.index_scan_threshold``.
    index_scan_min_compressed_entries: int = 0
    recurrent_state_bytes: float = 0.0
    recurrent_write_bytes: float | None = None
    #: Cross-layer cache sharing, as DeepSeek-V4.1's CSA2 does it.  A layer
    #: that does not own its compressed main cache reads one that a preceding
    #: Full-mode layer wrote: it stores and writes no compressed main entry
    #: and no index entry.  Its sliding window is always its own.  ``True``
    #: for every profile that predates the field.
    kv_owner: bool = True
    #: Whether the layer runs the sparse index scan at all.  A CSA2 Reuse-mode
    #: layer takes the top-k selection its Full or Reindex predecessor made and
    #: scans nothing.  ``True`` for every profile that predates the field.
    scans_index: bool = True
    #: Upper bound on the compressed entries one query scores; 0 is unbounded.
    #: DeepSeek-V4.1's Hierarchical Sparse Indexer lets a decoder Reindex layer
    #: score only the candidate pool the decoder's Full layer built -- 2,048
    #: blocks of 8 positions, 16,384 entries -- so its scan stops growing with
    #: context.  The Full layer itself still scans everything.
    index_scan_entries_cap: int = 0
    #: Bytes of one sliding-window entry when the window is kept at a
    #: different precision from the compressed main cache (V4.1: FP8 window,
    #: FP4 main).  0 means the window entry is ``entry_bytes`` wide.
    window_entry_bytes: float = 0.0
    #: Attention arithmetic that the active-parameter count does not see.
    #: ``2 * active_parameters`` counts every weight matrix once and nothing
    #: else, so a profile without an exact operator inventory used to charge
    #: its attention core -- QK and AV over the cache, or a recurrent state
    #: update -- nothing at all.  These three fields let a profile state that
    #: arithmetic per layer; ``operations.operation_inventory`` adds it for
    #: the non-DeepSeek adapters.  All default to zero / empty, which is the
    #: previous behaviour, and are omitted from serialisation at the default
    #: so every profile that predates them round-trips byte for byte.
    #:
    #: ``operations_per_token``: context-independent operations per layer per
    #: token -- the recurrent-state update and readout of a linear-attention
    #: layer.  ``recurrent`` layers only.
    operations_per_token: float = 0.0
    #: Operations per attended cache entry per layer (QK plus AV over every
    #: head).  The attended entries are the ones ``workload.kv_traffic``
    #: reads: ``min(context, window)`` for ``window`` and ``context`` for
    #: ``dense_kv`` / ``dense_mla``.
    operations_per_entry: float = 0.0
    #: Canonical compute format of those operations; empty means the model's
    #: ``dense_compute_format``.
    operations_format: str = ""
    label: str = ""
    evidence: str = "assumed"

    @property
    def effective_window_entry_bytes(self) -> float:
        return self.window_entry_bytes if self.window_entry_bytes > 0 else self.entry_bytes

    def __post_init__(self) -> None:
        allowed = {
            "window",
            "compressed_sparse",
            "compressed_dense",
            "dense_mla",
            "dense_kv",
            "recurrent",
        }
        if self.kind not in allowed:
            raise ValidationError(f"unsupported attention kind {self.kind!r}")
        if self.count <= 0:
            raise ValidationError("attention group count must be positive")
        if self.kind != "recurrent" and self.entry_bytes <= 0:
            raise ValidationError(f"{self.kind} requires positive entry_bytes")
        if self.kind == "recurrent" and self.recurrent_state_bytes <= 0:
            raise ValidationError("recurrent attention requires state bytes")
        if self.kind == "compressed_dense" and self.compression_ratio <= 1:
            raise ValidationError("compressed_dense attention requires ratio > 1")
        if self.kind == "compressed_sparse" and self.compression_ratio < 1:
            # Ratio 1 is CSA2's "uncompressed main KV" special case: one
            # latent per token, still read through a top-k index.
            raise ValidationError("compressed_sparse attention requires ratio >= 1")
        if self.kind == "compressed_sparse":
            if self.top_k <= 0 or self.index_entry_bytes <= 0:
                raise ValidationError("compressed_sparse requires top_k and index_entry_bytes")
        if not self.kv_owner and not self.kind.startswith("compressed"):
            raise ValidationError("only a compressed cache can be shared from another layer")
        if not self.scans_index and self.kind != "compressed_sparse":
            raise ValidationError("scans_index applies to compressed_sparse layers only")
        if self.index_scan_entries_cap < 0:
            raise ValidationError("index_scan_entries_cap cannot be negative")
        if self.index_scan_entries_cap and self.kind != "compressed_sparse":
            raise ValidationError("index_scan_entries_cap applies to compressed_sparse layers only")
        if self.window_entry_bytes < 0:
            raise ValidationError("window_entry_bytes cannot be negative")
        if self.window_entry_bytes and not self.window_tokens:
            raise ValidationError("window_entry_bytes requires a sliding window")
        if self.operations_per_token < 0 or self.operations_per_entry < 0:
            raise ValidationError("attention operation counts cannot be negative")
        if self.operations_per_token and self.kind != "recurrent":
            raise ValidationError("operations_per_token applies to recurrent layers only")
        if self.operations_per_entry and self.kind not in {
            "window",
            "dense_kv",
            "dense_mla",
        }:
            raise ValidationError(
                "operations_per_entry applies to window, dense_kv and dense_mla layers only"
            )


@dataclass(frozen=True)
class ModelProfile:
    name: str
    source_repo: str
    source_revision: str
    total_parameters: float
    active_parameters: float
    checkpoint_bytes: float
    dense_weight_bytes: float
    routed_weight_bytes: float
    num_layers: int
    num_experts: int
    experts_per_token: int
    hidden_size: int
    max_context_tokens: int
    attention_groups: tuple[AttentionGroup, ...]
    # Arithmetic formats are properties of the released model, not of whether
    # its stored weights happen to occupy four or eight bits.  For example,
    # DeepSeek V4 routes MXFP4 expert weights into FP8 activations; it is not an
    # FP4 x FP4 matrix operation.  Hardware profiles must provide a roof for
    # every format named here so an unsupported/ambiguous pairing fails closed.
    dense_compute_format: str
    routed_compute_format: str | None
    # Exact ordinary-decode storage assigned to each ordered transformer layer.
    # Non-layer tensors, draft modules, and resident-only tensors are kept in the
    # top-level categories and may fill otherwise unused stage ROM capacity.
    layer_dense_weight_bytes: tuple[float, ...] = ()
    layer_routed_weight_bytes: tuple[float, ...] = ()
    # Released checkpoints can contain weights that are resident for capacity
    # purposes but are not streamed by an ordinary one-token decode pass.  The
    # draft categories are read only when speculative decoding is enabled;
    # ``resident_only`` covers lookup tables and modality/prefill-only weights.
    draft_dense_weight_bytes: float = 0.0
    draft_routed_weight_bytes: float = 0.0
    resident_only_weight_bytes: float = 0.0
    operations_per_active_parameter: float = 2.0
    router_trace_status: str = "synthetic"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "total_parameters",
            "active_parameters",
            "checkpoint_bytes",
            "num_layers",
            "num_experts",
            "experts_per_token",
            "hidden_size",
            "max_context_tokens",
        ):
            _positive(name, float(getattr(self, name)))
        if self.active_parameters > self.total_parameters:
            raise ValidationError("active parameters cannot exceed total parameters")
        if self.experts_per_token > self.num_experts:
            raise ValidationError("experts_per_token cannot exceed num_experts")
        if not self.dense_compute_format.strip():
            raise ValidationError("dense_compute_format must be non-empty")
        if self.routed_weight_bytes > 0 and not (
            isinstance(self.routed_compute_format, str)
            and self.routed_compute_format.strip()
        ):
            raise ValidationError(
                "routed checkpoints require a non-empty routed_compute_format"
            )
        if self.routed_weight_bytes == 0 and self.routed_compute_format is not None:
            raise ValidationError(
                "dense checkpoints must set routed_compute_format to null"
            )
        if any(
            value < 0
            for value in (
                self.dense_weight_bytes,
                self.routed_weight_bytes,
                self.draft_dense_weight_bytes,
                self.draft_routed_weight_bytes,
                self.resident_only_weight_bytes,
            )
        ):
            raise ValidationError("weight byte categories cannot be negative")
        categorized = (
            self.dense_weight_bytes
            + self.routed_weight_bytes
            + self.draft_dense_weight_bytes
            + self.draft_routed_weight_bytes
            + self.resident_only_weight_bytes
        )
        if categorized <= 0:
            raise ValidationError("at least one weight byte category is required")
        if abs(categorized - self.checkpoint_bytes) > max(1.0, self.checkpoint_bytes * 0.02):
            raise ValidationError(
                "all weight byte categories must match checkpoint_bytes within 2%"
            )
        layer_count = sum(group.count for group in self.attention_groups)
        if layer_count != self.num_layers:
            raise ValidationError(
                f"attention groups cover {layer_count} layers, expected {self.num_layers}"
            )
        if bool(self.layer_dense_weight_bytes) != bool(self.layer_routed_weight_bytes):
            raise ValidationError("both per-layer weight vectors must be present together")
        if self.layer_dense_weight_bytes:
            if len(self.layer_dense_weight_bytes) != self.num_layers:
                raise ValidationError("layer_dense_weight_bytes length must equal num_layers")
            if len(self.layer_routed_weight_bytes) != self.num_layers:
                raise ValidationError("layer_routed_weight_bytes length must equal num_layers")
            if any(value < 0 for value in self.layer_dense_weight_bytes):
                raise ValidationError("per-layer dense weight bytes cannot be negative")
            if any(value < 0 for value in self.layer_routed_weight_bytes):
                raise ValidationError("per-layer routed weight bytes cannot be negative")
            if sum(self.layer_dense_weight_bytes) > self.dense_weight_bytes + 1:
                raise ValidationError("per-layer dense bytes exceed decode-dense total")
            if sum(self.layer_routed_weight_bytes) > self.routed_weight_bytes + 1:
                raise ValidationError("per-layer routed bytes exceed decode-routed total")

    @property
    def routed_fraction_per_token(self) -> float:
        # Dense checkpoints retain a one-expert/one-selected schema sentinel so
        # the rest of the simulator need not special-case missing positive
        # topology fields. Zero routed storage is the unambiguous discriminator.
        if self.routed_weight_bytes == 0:
            return 0.0
        return self.experts_per_token / self.num_experts

    @property
    def dense_parameters(self) -> float:
        """Infer the non-routed parameter count from total and active counts."""
        frac = self.routed_fraction_per_token
        if frac == 0:
            return self.active_parameters
        return (self.active_parameters - frac * self.total_parameters) / (1.0 - frac)

    @property
    def routed_parameters(self) -> float:
        if self.routed_fraction_per_token == 0:
            return 0.0
        return self.total_parameters - self.dense_parameters

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelProfile":
        copied = dict(data)
        copied["attention_groups"] = tuple(
            AttentionGroup(**group) for group in copied.get("attention_groups", ())
        )
        copied["layer_dense_weight_bytes"] = tuple(
            copied.get("layer_dense_weight_bytes", ())
        )
        copied["layer_routed_weight_bytes"] = tuple(
            copied.get("layer_routed_weight_bytes", ())
        )
        return cls(**copied)

    @classmethod
    def load(cls, path: str | Path) -> "ModelProfile":
        with Path(path).open(encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        # The cross-layer sharing fields were added for DeepSeek-V4.1.  At their
        # defaults they are omitted so every profile written before them
        # round-trips byte for byte.
        defaults = AttentionGroup(kind="window", count=1, entry_bytes=1.0)
        data["attention_groups"] = [
            {
                key: value
                for key, value in group.items()
                if key not in _SHARING_FIELDS or value != getattr(defaults, key)
            }
            for group in data["attention_groups"]
        ]
        return data


_SHARING_FIELDS = frozenset(
    {
        "kv_owner",
        "scans_index",
        "index_scan_entries_cap",
        "window_entry_bytes",
        "operations_per_token",
        "operations_per_entry",
        "operations_format",
    }
)


@dataclass(frozen=True)
class ComputePath:
    """How a model arithmetic format is executed by one architecture.

    ``native`` distinguishes actual format support from an emulation mapping.
    The operation multiplier permits a documented decomposition into a different
    primitive, but it must never be used to hide conversion or memory expansion.
    Those deployment effects require separate accounting.
    """

    execution_format: str
    native: bool
    operation_multiplier: float = 1.0
    conversion_policy: str = "none"
    evidence: str = "assumed"

    def __post_init__(self) -> None:
        if not self.execution_format.strip():
            raise ValidationError("compute-path execution_format must be non-empty")
        _positive("compute-path operation_multiplier", self.operation_multiplier)
        if not self.conversion_policy.strip():
            raise ValidationError("compute-path conversion_policy must be non-empty")
        if not self.evidence.strip():
            raise ValidationError("compute-path evidence must be non-empty")


@dataclass(frozen=True)
class WaferCommunicationProfile:
    """Physical inputs for a distributed on-wafer all-reduce.

    The profile intentionally does not contain a precomputed ``seconds/layer``
    number.  Propagation and serialization are derived for each model, context,
    and batch from the mesh dimensions, link payload, and the two all-reduces in
    the released DeepSeek block.  A coarse hierarchy can be represented by a
    small global mesh plus an explicit local path; a WSE-like nearest-neighbour
    ceiling uses the full core mesh and a zero local path.
    """

    topology: str
    rows: int
    cols: int
    frequency_hz: float
    link_payload_bytes_per_cycle: float
    hop_cycles: float
    bisection_links: int
    local_path_hops: int = 0
    local_hop_cycles: float = 0.0
    endpoint_cycles: float = 0.0
    barrier_cycles: float = 0.0
    payload_efficiency: float = 1.0
    allreduce_events_per_layer: int = 2
    reduction_bytes_per_element: float = 4.0
    result_bytes_per_element: float = 2.0
    evidence: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.topology not in {
            "nearest_neighbor_mesh",
            "hierarchical_mesh",
            "coarse_reticle_exchange",
        }:
            raise ValidationError(
                f"unsupported wafer communication topology {self.topology!r}"
            )
        for name in (
            "rows",
            "cols",
            "frequency_hz",
            "link_payload_bytes_per_cycle",
            "hop_cycles",
            "bisection_links",
            "allreduce_events_per_layer",
            "reduction_bytes_per_element",
            "result_bytes_per_element",
        ):
            _positive(name, float(getattr(self, name)))
        if self.local_path_hops < 0:
            raise ValidationError("local_path_hops cannot be negative")
        for name in ("local_hop_cycles", "endpoint_cycles", "barrier_cycles"):
            if getattr(self, name) < 0:
                raise ValidationError(f"{name} cannot be negative")
        _fraction("payload_efficiency", self.payload_efficiency)
        if self.bisection_links > self.rows * self.cols:
            raise ValidationError("bisection_links cannot exceed mesh node count")


@dataclass(frozen=True)
class ArchitectureProfile:
    """One implementation architecture (GPU cluster or wafer pipeline)."""

    name: str
    kind: str
    device_count: int
    weight_capacity_bytes_per_device: float
    kv_capacity_bytes_per_device: float
    weight_bandwidth_bytes_s_per_device: float
    kv_bandwidth_bytes_s_per_device: float
    compute_roofs_ops_s_per_device: dict[str, float]
    collective_latency_s_per_layer: float
    cost_per_device: float
    power_w_per_device: float
    cooling_limit_w_per_device: float
    collective_bandwidth_bytes_s: float = 1.0e30
    # Algorithmic KV accounting assumes each shared latent/index vector is
    # fetched once.  Real kernels may reread it; keep that implementation
    # effect explicit and architecture-specific.
    kv_read_amplification: float = 1.0
    # Fraction of physical HBM capacity available to checkpoint/KV after runtime
    # workspace, allocator, communication, and safety reserve.
    hbm_capacity_utilization: float = 0.90
    lifetime_years: float = 4.0
    utilization: float = 0.70
    weight_bandwidth_efficiency: float = 0.75
    kv_bandwidth_efficiency: float = 0.75
    compute_efficiency: float = 0.55
    load_balance_efficiency: float = 0.85
    defect_repair_efficiency: float = 1.0
    clock_efficiency: float = 0.90
    sync_efficiency: float = 0.90
    pipeline_efficiency: float = 0.90
    hbm_energy_j_per_byte: float = 4.0e-12
    weight_read_energy_j_per_byte: float = 0.5e-12
    mac_energy_j_per_op: float = 0.2e-12
    # Cost reporting is a deliberately incomplete, but explicit, partial TCO:
    # hardware/NRE amortization plus electricity while serving.  Facility PUE
    # and electricity price remain sweepable assumptions; staffing, financing,
    # networking, floor space, maintenance, and replacement inventory are not
    # silently estimated.
    electricity_cost_per_kwh: float = 0.08
    facility_pue: float = 1.15
    nre_cost: float = 0.0
    production_units: int = 1
    cross_stage_latency_s: float = 0.0
    cross_stage_bandwidth_bytes_s: float = 1.0e30
    compute_paths: dict[str, ComputePath] = field(default_factory=dict)
    wafer_communication: WaferCommunicationProfile | None = None
    weight_storage_technology: str = "unspecified"
    kv_storage_technology: str = "unspecified"
    storage_capacity_policy: str = "unspecified"
    storage_bandwidth_policy: str = "unspecified"
    model_deployment_policy: str = "official_packed"
    evidence: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind not in {"gpu", "rom", "sram"}:
            raise ValidationError("architecture kind must be 'gpu', 'rom', or 'sram'")
        for name in (
            "device_count",
            "weight_capacity_bytes_per_device",
            "kv_capacity_bytes_per_device",
            "weight_bandwidth_bytes_s_per_device",
            "kv_bandwidth_bytes_s_per_device",
            "collective_bandwidth_bytes_s",
            "cross_stage_bandwidth_bytes_s",
            "kv_read_amplification",
            "cost_per_device",
            "power_w_per_device",
            "cooling_limit_w_per_device",
            "lifetime_years",
            "production_units",
            "electricity_cost_per_kwh",
            "facility_pue",
        ):
            _positive(name, float(getattr(self, name)))
        if not self.compute_roofs_ops_s_per_device:
            raise ValidationError("compute_roofs_ops_s_per_device must not be empty")
        for numeric_format, peak in self.compute_roofs_ops_s_per_device.items():
            if not isinstance(numeric_format, str) or not numeric_format.strip():
                raise ValidationError("compute roof names must be non-empty strings")
            _positive(
                f"compute_roofs_ops_s_per_device[{numeric_format!r}]",
                float(peak),
            )
        for model_format, path in self.compute_paths.items():
            if not isinstance(model_format, str) or not model_format.strip():
                raise ValidationError("compute-path model formats must be non-empty strings")
            if not isinstance(path, ComputePath):
                raise ValidationError("compute_paths values must be ComputePath objects")
            if path.execution_format not in self.compute_roofs_ops_s_per_device:
                raise ValidationError(
                    f"compute path for {model_format!r} names unavailable execution "
                    f"format {path.execution_format!r}"
                )
        if self.kind == "gpu" and self.wafer_communication is not None:
            raise ValidationError("GPU profiles cannot define wafer_communication")
        for name in (
            "weight_storage_technology",
            "kv_storage_technology",
            "storage_capacity_policy",
            "storage_bandwidth_policy",
            "model_deployment_policy",
        ):
            if not getattr(self, name).strip():
                raise ValidationError(f"{name} must be non-empty")
        if self.power_w_per_device > self.cooling_limit_w_per_device:
            raise ValidationError(
                "power_w_per_device cannot exceed cooling_limit_w_per_device"
            )
        for name in (
            "utilization",
            "weight_bandwidth_efficiency",
            "kv_bandwidth_efficiency",
            "compute_efficiency",
            "load_balance_efficiency",
            "defect_repair_efficiency",
            "clock_efficiency",
            "sync_efficiency",
            "pipeline_efficiency",
            "hbm_capacity_utilization",
        ):
            _fraction(name, float(getattr(self, name)))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArchitectureProfile":
        copied = dict(data)
        copied["compute_paths"] = {
            numeric_format: (
                path if isinstance(path, ComputePath) else ComputePath(**path)
            )
            for numeric_format, path in copied.get("compute_paths", {}).items()
        }
        wafer_communication = copied.get("wafer_communication")
        if isinstance(wafer_communication, dict):
            copied["wafer_communication"] = WaferCommunicationProfile(
                **wafer_communication
            )
        return cls(**copied)

    def compute_path(self, numeric_format: str) -> ComputePath:
        """Resolve native or explicitly emulated model arithmetic."""

        if numeric_format in self.compute_paths:
            return self.compute_paths[numeric_format]
        if numeric_format in self.compute_roofs_ops_s_per_device:
            return ComputePath(
                execution_format=numeric_format,
                native=True,
                evidence="identity path from architecture compute roof",
            )
        available = ", ".join(
            sorted(set(self.compute_roofs_ops_s_per_device) | set(self.compute_paths))
        )
        raise ValidationError(
            f"{self.name} has no compute path for {numeric_format!r}; "
            f"available formats: {available}"
        )

    def compute_roof(self, numeric_format: str) -> float:
        """Return the execution roof selected by a compatible compute path."""

        path = self.compute_path(numeric_format)
        return self.compute_roofs_ops_s_per_device[path.execution_format]


@dataclass(frozen=True)
class HardwareProfile:
    gpu: ArchitectureProfile
    rom: ArchitectureProfile

    def __post_init__(self) -> None:
        if self.gpu.kind != "gpu" or self.rom.kind != "rom":
            raise ValidationError("HardwareProfile requires gpu and rom architectures")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HardwareProfile":
        return cls(
            gpu=ArchitectureProfile.from_dict(data["gpu"]),
            rom=ArchitectureProfile.from_dict(data["rom"]),
        )

    @classmethod
    def load(cls, path: str | Path) -> "HardwareProfile":
        with Path(path).open(encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SpeculationProfile:
    draft_tokens: int = 0
    acceptance_probability: float = 0.0
    draft_cost_fraction: float = 0.0

    def __post_init__(self) -> None:
        if self.draft_tokens < 0:
            raise ValidationError("draft_tokens cannot be negative")
        if self.draft_tokens:
            _fraction("acceptance_probability", self.acceptance_probability, allow_zero=True)
            if self.draft_cost_fraction < 0:
                raise ValidationError("draft_cost_fraction cannot be negative")

    @property
    def expected_output_tokens(self) -> float:
        if self.draft_tokens == 0:
            return 1.0
        p = self.acceptance_probability
        if p == 1.0:
            return float(self.draft_tokens + 1)
        return (1.0 - p ** (self.draft_tokens + 1)) / (1.0 - p)


@dataclass(frozen=True)
class SimulationRequest:
    context_tokens: int
    batch_size: int
    output_tokens: int = 1024
    prompt_tokens: int = 0
    prefix_cache_hit_rate: float = 0.0
    disaggregated_prefill: bool = False
    kv_handoff_bandwidth_bytes_s: float = 100e9
    speculation: SpeculationProfile = field(default_factory=SpeculationProfile)

    def __post_init__(self) -> None:
        for name in ("context_tokens", "batch_size", "output_tokens"):
            _positive(name, float(getattr(self, name)))
        if self.prompt_tokens < 0:
            raise ValidationError("prompt_tokens cannot be negative")
        _fraction("prefix_cache_hit_rate", self.prefix_cache_hit_rate, allow_zero=True)
        _positive("kv_handoff_bandwidth_bytes_s", self.kv_handoff_bandwidth_bytes_s)


def load_models(paths: Iterable[str | Path]) -> list[ModelProfile]:
    return [ModelProfile.load(path) for path in paths]
