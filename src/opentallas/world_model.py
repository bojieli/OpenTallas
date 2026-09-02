"""Analytical workload model for causal and full-clip diffusion transformers.

The ordinary OpenTallas analytical path models one-position language decode.
This module deliberately does not force video inference into that schema.  It
instead exposes the video-specific quantities that decide whether immutable
weight service matters: patch rows per model call, repeated diffusion calls,
causal state traffic, axial/full attention work, and critical-cut payload.

All equations count a fused multiply-add as two operations.  Norms, nonlinear
functions, softmax, scheduler arithmetic, and codec I/O are identified as
unpriced auxiliary work rather than silently assigned a tensor-core rate.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Literal

from .schema import ArchitectureProfile


StoragePolicy = Literal["rom", "same_compute_hbm", "gpu_hbm"]
CacheMode = Literal["reference_recompute", "causal_kv_cache"]


@dataclass(frozen=True)
class WorkPhase:
    """One serial phase of a generated frame or clip."""

    name: str
    tensor_operations: float
    weight_read_bytes: float
    mutable_hbm_bytes: float
    noc_tensor_injected_bytes: float
    noc_cache_injected_bytes: float = 0.0
    calls: int = 1
    token_rows_per_call: int = 0
    frame_rows_per_call: int = 0
    token_weight_bytes_per_call: float = 0.0
    frame_weight_bytes_per_call: float = 0.0
    fixed_weight_bytes_per_call: float = 0.0

    def rom_array_service_bytes(self, row_reuse: int | None = None) -> float:
        """Bytes presented by a storage-ROM array under an activation reuse law.

        ``None`` is the default OpenTallas batched interpretation: each distinct
        matrix is served once per model call and reused across the complete row
        dimension.  An integer exposes the implementation sensitivity in which
        a ROM/MAC tile must re-serve weights after that many activation rows.
        This is a service-byte proxy, not a timing model for per-stream digital
        compute-in-ROM.
        """

        if row_reuse is None:
            return self.weight_read_bytes
        if row_reuse <= 0:
            raise ValueError("row_reuse must be positive")
        if not (
            self.token_weight_bytes_per_call
            or self.frame_weight_bytes_per_call
            or self.fixed_weight_bytes_per_call
        ):
            return self.weight_read_bytes
        token_sweeps = (
            math.ceil(self.token_rows_per_call / row_reuse)
            if self.token_rows_per_call
            else 0
        )
        frame_sweeps = (
            math.ceil(self.frame_rows_per_call / row_reuse)
            if self.frame_rows_per_call
            else 0
        )
        per_call = (
            token_sweeps * self.token_weight_bytes_per_call
            + frame_sweeps * self.frame_weight_bytes_per_call
            + self.fixed_weight_bytes_per_call
        )
        return self.calls * per_call


@dataclass(frozen=True)
class VideoWorkload:
    """A complete frame or clip workload and its interpretation boundary."""

    model: str
    scenario: str
    unit: Literal["frame", "clip"]
    target_interval_s: float
    phases: tuple[WorkPhase, ...]
    metadata: dict[str, Any]

    @property
    def tensor_operations(self) -> float:
        return sum(phase.tensor_operations for phase in self.phases)

    @property
    def weight_read_bytes(self) -> float:
        return sum(phase.weight_read_bytes for phase in self.phases)

    @property
    def mutable_hbm_bytes(self) -> float:
        return sum(phase.mutable_hbm_bytes for phase in self.phases)

    @property
    def noc_tensor_injected_bytes(self) -> float:
        return sum(phase.noc_tensor_injected_bytes for phase in self.phases)

    @property
    def noc_cache_injected_bytes(self) -> float:
        return sum(phase.noc_cache_injected_bytes for phase in self.phases)


@dataclass(frozen=True)
class OasisSpec:
    output_height: int
    output_width: int
    vae_patch_size: int
    dit_patch_size: int
    latent_channels: int
    hidden_size: int
    layers: int
    heads: int
    mlp_ratio: int
    max_frames: int
    action_dim: int
    diffusion_steps: int
    context_timestep: int
    runtime_weight_bytes_per_parameter: int
    vae_encoder_layers: int
    vae_decoder_layers: int

    def __post_init__(self) -> None:
        integer_fields = (
            self.output_height,
            self.output_width,
            self.vae_patch_size,
            self.dit_patch_size,
            self.latent_channels,
            self.hidden_size,
            self.layers,
            self.heads,
            self.mlp_ratio,
            self.max_frames,
            self.action_dim,
            self.diffusion_steps,
            self.context_timestep,
            self.runtime_weight_bytes_per_parameter,
            self.vae_encoder_layers,
            self.vae_decoder_layers,
        )
        if any(value <= 0 for value in integer_fields):
            raise ValueError("Oasis dimensions and counts must be positive")
        if self.output_height % self.vae_patch_size:
            raise ValueError("output height is not divisible by the VAE patch")
        if self.output_width % self.vae_patch_size:
            raise ValueError("output width is not divisible by the VAE patch")
        if (self.output_height // self.vae_patch_size) % self.dit_patch_size:
            raise ValueError("latent height is not divisible by the DiT patch")
        if (self.output_width // self.vae_patch_size) % self.dit_patch_size:
            raise ValueError("latent width is not divisible by the DiT patch")
        if self.hidden_size % self.heads:
            raise ValueError("hidden size must divide evenly across heads")

    @property
    def vae_tokens_per_frame(self) -> int:
        return (self.output_height // self.vae_patch_size) * (
            self.output_width // self.vae_patch_size
        )

    @property
    def spatial_tokens_per_frame(self) -> int:
        return self.vae_tokens_per_frame // self.dit_patch_size**2

    @property
    def dit_token_row_parameters(self) -> int:
        """Parameters whose matrices consume every spatial token row."""

        d = self.hidden_size
        # Per block: two (spatial, temporal) copies of attention (4D^2)
        # plus MLP (8D^2). Biases are retained as 6D per copy.
        blocks = self.layers * (24 * d * d + 12 * d)
        patch_embed = d * self.latent_channels * self.dit_patch_size**2 + d
        final_width = self.latent_channels * self.dit_patch_size**2
        final_projection = d * final_width + final_width
        return blocks + patch_embed + final_projection

    @property
    def dit_frame_row_parameters(self) -> int:
        """Parameters whose matrices consume one conditioning row per frame."""

        d = self.hidden_size
        block_adaln = self.layers * (12 * d * d + 12 * d)
        timestep = 256 * d + d + d * d + d
        action = self.action_dim * d + d
        final_adaln = 2 * d * d + 2 * d
        return block_adaln + timestep + action + final_adaln

    @property
    def dit_parameters(self) -> int:
        return self.dit_token_row_parameters + self.dit_frame_row_parameters

    @property
    def dit_weight_bytes(self) -> int:
        return self.dit_parameters * self.runtime_weight_bytes_per_parameter

    @property
    def vae_decoder_parameters(self) -> int:
        d = self.hidden_size
        # qkv/proj + 4x MLP + two affine LayerNorms per decoder block.
        blocks = self.vae_decoder_layers * (12 * d * d + 13 * d)
        post_quant = self.latent_channels * d + d
        decoder_norm = 2 * d
        pixel_width = 3 * self.vae_patch_size**2
        predictor = d * pixel_width + pixel_width
        return blocks + post_quant + decoder_norm + predictor

    @property
    def vae_decoder_weight_bytes(self) -> int:
        return self.vae_decoder_parameters * self.runtime_weight_bytes_per_parameter

    @property
    def static_model_parameters(self) -> int:
        """DiT plus complete VAE encoder/decoder capacity."""

        d = self.hidden_size
        encoder_blocks = self.vae_encoder_layers * (12 * d * d + 13 * d)
        pixel_width = 3 * self.vae_patch_size**2
        patch_embed = pixel_width * d + d
        encoder_norm = 2 * d
        quant = d * (2 * self.latent_channels) + 2 * self.latent_channels
        full_vae = (
            encoder_blocks
            + patch_embed
            + encoder_norm
            + quant
            + self.vae_decoder_parameters
        )
        return self.dit_parameters + full_vae

    def full_window_call_operations(self, frames: int) -> float:
        if not 1 <= frames <= self.max_frames:
            raise ValueError("frames outside Oasis window")
        d = self.hidden_size
        s = self.spatial_tokens_per_frame
        rows = frames * s
        block_linears = 2 * self.layers * 24 * d * d * rows
        block_adaln = 2 * self.layers * 12 * d * d * frames
        # Spatial attention is dense within each frame. Temporal SDPA is
        # causal, so only F(F+1)/2 query/key pairs are semantically active.
        attention = 4 * self.layers * d * (
            frames * s * s + s * frames * (frames + 1) // 2
        )
        patch_embed = 2 * rows * d * self.latent_channels * self.dit_patch_size**2
        timestep = 2 * frames * (256 * d + d * d)
        action = 2 * frames * self.action_dim * d
        final_adaln = 2 * frames * 2 * d * d
        final_projection = (
            2 * rows * d * self.latent_channels * self.dit_patch_size**2
        )
        return (
            block_linears
            + block_adaln
            + attention
            + patch_embed
            + timestep
            + action
            + final_adaln
            + final_projection
        )

    def cached_frame_call_operations(self, past_frames: int) -> float:
        if not 0 <= past_frames < self.max_frames:
            raise ValueError("past_frames outside Oasis window")
        d = self.hidden_size
        s = self.spatial_tokens_per_frame
        rows = s
        key_frames = past_frames + 1
        block_linears = 2 * self.layers * 24 * d * d * rows
        block_adaln = 2 * self.layers * 12 * d * d
        attention = 4 * self.layers * d * (s * s + s * key_frames)
        patch_embed = 2 * rows * d * self.latent_channels * self.dit_patch_size**2
        timestep = 2 * (256 * d + d * d)
        action = 2 * self.action_dim * d
        final_adaln = 4 * d * d
        final_projection = (
            2 * rows * d * self.latent_channels * self.dit_patch_size**2
        )
        return (
            block_linears
            + block_adaln
            + attention
            + patch_embed
            + timestep
            + action
            + final_adaln
            + final_projection
        )

    def temporal_kv_bytes(self, frames: int) -> int:
        if not 0 <= frames <= self.max_frames:
            raise ValueError("frames outside Oasis window")
        return (
            2
            * self.layers
            * frames
            * self.spatial_tokens_per_frame
            * self.hidden_size
            * 2
        )

    def attention_tensor_bytes(self, token_rows: int) -> int:
        # Q, K, V and output for each of spatial and temporal attention.
        return 8 * self.layers * token_rows * self.hidden_size * 2

    @property
    def vae_decoder_operations(self) -> float:
        d = self.hidden_size
        n = self.vae_tokens_per_frame
        linears = 2 * self.vae_decoder_layers * 12 * d * d * n
        attention = 4 * self.vae_decoder_layers * n * n * d
        post_quant = 2 * n * self.latent_channels * d
        predictor = 2 * n * d * (3 * self.vae_patch_size**2)
        return linears + attention + post_quant + predictor

    @property
    def vae_attention_tensor_bytes(self) -> int:
        return (
            4
            * self.vae_decoder_layers
            * self.vae_tokens_per_frame
            * self.hidden_size
            * 2
        )


@dataclass(frozen=True)
class H3Spec:
    hidden_size: int
    layers: int
    attention_inner_dim: int
    ffn_hidden_size: int
    denoise_calls: int
    active_transformer_weight_bytes: int
    full_transformer_weight_bytes: int
    text_tokens: int
    video_tokens_per_latent_frame: int
    sequence_parallel_degree: int
    runtime_bytes_per_element: int = 2

    @property
    def main_matrix_parameters(self) -> int:
        d = self.hidden_size
        return self.layers * (
            4 * d * self.attention_inner_dim + 3 * d * self.ffn_hidden_size
        )

    def sequence_tokens(
        self, *, latent_video_frames: int, audio_tokens: int
    ) -> int:
        return (
            self.text_tokens
            + latent_video_frames * self.video_tokens_per_latent_frame
            + audio_tokens
        )

    def operations_per_call(self, sequence_tokens: int) -> tuple[float, float]:
        linear = 2 * self.main_matrix_parameters * sequence_tokens
        attention = (
            4
            * self.layers
            * sequence_tokens**2
            * self.attention_inner_dim
        )
        return float(linear), float(attention)

    def qkv_materialization_floor_bytes(self, sequence_tokens: int) -> int:
        # Q/K/V write plus one read, per layer and denoise call.
        return (
            6
            * sequence_tokens
            * self.attention_inner_dim
            * self.runtime_bytes_per_element
            * self.layers
            * self.denoise_calls
        )

    def ulysses_injected_bytes(self, sequence_tokens: int) -> float:
        # Two all-to-alls: QKV into head partitions and attention output back.
        p = self.sequence_parallel_degree
        per_device = (
            4
            * sequence_tokens
            * self.attention_inner_dim
            * self.runtime_bytes_per_element
            * (p - 1)
            / p**2
        )
        return per_device * p * self.layers * self.denoise_calls


def oasis_frame_workload(
    spec: OasisSpec,
    *,
    window_frames: int,
    cache_mode: CacheMode,
    cache_fill_passes: int = 1,
    target_fps: float = 20.0,
) -> VideoWorkload:
    """Construct one output-frame workload from the released Oasis schedule."""

    if not 1 <= window_frames <= spec.max_frames:
        raise ValueError("window_frames outside Oasis maximum")
    if target_fps <= 0:
        raise ValueError("target_fps must be positive")
    s = spec.spatial_tokens_per_frame

    if cache_mode == "reference_recompute":
        calls = spec.diffusion_steps
        token_rows = window_frames * s
        frame_rows = window_frames
        dit = WorkPhase(
            name="dit",
            tensor_operations=(
                calls * spec.full_window_call_operations(window_frames)
            ),
            weight_read_bytes=calls * spec.dit_weight_bytes,
            mutable_hbm_bytes=0.0,
            noc_tensor_injected_bytes=(
                calls * spec.attention_tensor_bytes(token_rows)
            ),
            calls=calls,
            token_rows_per_call=token_rows,
            frame_rows_per_call=frame_rows,
            token_weight_bytes_per_call=(
                spec.dit_token_row_parameters
                * spec.runtime_weight_bytes_per_parameter
            ),
            frame_weight_bytes_per_call=(
                spec.dit_frame_row_parameters
                * spec.runtime_weight_bytes_per_parameter
            ),
        )
        metadata = {
            "cache_mode": cache_mode,
            "window_frames": window_frames,
            "past_frames": window_frames - 1,
            "dit_calls_per_frame": calls,
            "cache_fill_passes": 0,
            "persistent_temporal_kv_bytes": 0,
            "cache_validity": "not_applicable_reference_code_recomputes_window",
        }
    elif cache_mode == "causal_kv_cache":
        if cache_fill_passes < 0:
            raise ValueError("cache_fill_passes cannot be negative")
        # The released schedule's last denoise call does not use the fixed
        # context timestep. Conservatively recompute the completed frame once
        # at that timestep before installing its per-layer temporal K/V.
        calls = spec.diffusion_steps + cache_fill_passes
        past = window_frames - 1
        read_per_call = spec.temporal_kv_bytes(past)
        write_once = spec.temporal_kv_bytes(1)
        dit = WorkPhase(
            name="dit",
            tensor_operations=(
                calls * spec.cached_frame_call_operations(past)
            ),
            weight_read_bytes=calls * spec.dit_weight_bytes,
            mutable_hbm_bytes=calls * read_per_call + write_once,
            noc_tensor_injected_bytes=(
                calls * spec.attention_tensor_bytes(s)
            ),
            noc_cache_injected_bytes=calls * read_per_call,
            calls=calls,
            token_rows_per_call=s,
            frame_rows_per_call=1,
            token_weight_bytes_per_call=(
                spec.dit_token_row_parameters
                * spec.runtime_weight_bytes_per_parameter
            ),
            frame_weight_bytes_per_call=(
                spec.dit_frame_row_parameters
                * spec.runtime_weight_bytes_per_parameter
            ),
        )
        metadata = {
            "cache_mode": cache_mode,
            "window_frames": window_frames,
            "past_frames": past,
            "dit_calls_per_frame": calls,
            "cache_fill_passes": cache_fill_passes,
            "persistent_temporal_kv_bytes": spec.temporal_kv_bytes(
                window_frames
            ),
            "temporal_kv_read_bytes_per_frame": calls * read_per_call,
            "temporal_kv_write_bytes_per_frame": write_once,
            "cache_validity": (
                "derived_transformation_requires_fixed_context_timestep_"
                "causal_temporal_attention_and_position_stable_sliding_window"
            ),
        }
    else:  # pragma: no cover - Literal protects typed callers
        raise ValueError(f"unknown cache mode {cache_mode!r}")

    vae = WorkPhase(
        name="vae_decode",
        tensor_operations=spec.vae_decoder_operations,
        weight_read_bytes=spec.vae_decoder_weight_bytes,
        mutable_hbm_bytes=0.0,
        noc_tensor_injected_bytes=spec.vae_attention_tensor_bytes,
        calls=1,
        token_rows_per_call=spec.vae_tokens_per_frame,
        token_weight_bytes_per_call=spec.vae_decoder_weight_bytes,
    )
    metadata.update(
        {
            "output_resolution": [spec.output_width, spec.output_height],
            "spatial_tokens_per_frame": s,
            "vae_tokens_per_frame": spec.vae_tokens_per_frame,
            "target_fps": target_fps,
            "static_model_bytes_bf16_equivalent": (
                spec.static_model_parameters
                * spec.runtime_weight_bytes_per_parameter
            ),
            "auxiliary_work_status": (
                "norm_softmax_rope_gelu_scheduler_and_io_unpriced"
            ),
        }
    )
    return VideoWorkload(
        model="Oasis-500M-public-code",
        scenario=f"{cache_mode}-W{window_frames}",
        unit="frame",
        target_interval_s=1.0 / target_fps,
        phases=(dit, vae),
        metadata=metadata,
    )


def h3_clip_workload(
    spec: H3Spec,
    *,
    label: str,
    output_frames: int,
    latent_video_frames: int,
    audio_tokens: int,
    playback_fps: float = 24.0,
    attention_density: float = 1.0,
    denoise_calls: int | None = None,
) -> VideoWorkload:
    """Construct a dense or sparsified H3 transformer-only clip workload."""

    if not 0 < attention_density <= 1:
        raise ValueError("attention_density must be in (0, 1]")
    calls = spec.denoise_calls if denoise_calls is None else denoise_calls
    if calls <= 0:
        raise ValueError("denoise_calls must be positive")
    n = spec.sequence_tokens(
        latent_video_frames=latent_video_frames, audio_tokens=audio_tokens
    )
    linear, attention = spec.operations_per_call(n)
    call_scale = calls / spec.denoise_calls
    qkv_floor = spec.qkv_materialization_floor_bytes(n) * call_scale
    ulysses = spec.ulysses_injected_bytes(n) * call_scale * attention_density
    phase = WorkPhase(
        name="h3_transformer",
        tensor_operations=calls * (linear + attention_density * attention),
        weight_read_bytes=calls * spec.active_transformer_weight_bytes,
        # Kept out of the modeled HBM service to make the result a favorable
        # lower bound for H3; the byte floor is retained in metadata.
        mutable_hbm_bytes=0.0,
        noc_tensor_injected_bytes=ulysses,
        calls=calls,
        token_rows_per_call=n,
        token_weight_bytes_per_call=spec.active_transformer_weight_bytes,
    )
    duration = output_frames / playback_fps
    return VideoWorkload(
        model="MiniMax-H3",
        scenario=label,
        unit="clip",
        target_interval_s=duration,
        phases=(phase,),
        metadata={
            "output_frames": output_frames,
            "playback_fps": playback_fps,
            "clip_duration_s": duration,
            "sequence_tokens": n,
            "latent_video_frames": latent_video_frames,
            "audio_tokens": audio_tokens,
            "text_tokens": spec.text_tokens,
            "denoise_calls": calls,
            "linear_operations_per_call": linear,
            "dense_attention_operations_per_call": attention,
            "attention_density": attention_density,
            "attention_operation_share": (
                attention_density * attention
                / (linear + attention_density * attention)
            ),
            "qkv_materialization_floor_bytes": qkv_floor,
            "persistent_kv_cache_bytes": 0,
            "cache_validity": (
                "not_available_full_bidirectional_sequence_recomputed_each_call"
            ),
            "scope": (
                "transformer_only_lower_bound_excludes_text_encoder_video_audio_"
                "vae_softmax_norm_runtime_and_qkv_hbm_service"
            ),
        },
    )


def effective_compute_ops_s(arch: ArchitectureProfile) -> float:
    clock = arch.clock_efficiency * arch.defect_repair_efficiency
    return (
        arch.compute_roof("bf16_x_bf16")
        * arch.compute_efficiency
        * clock
    )


def effective_weight_bytes_s(arch: ArchitectureProfile) -> float:
    clock = arch.clock_efficiency * arch.defect_repair_efficiency
    return (
        arch.device_count
        * arch.weight_bandwidth_bytes_s_per_device
        * arch.weight_bandwidth_efficiency
        * clock
    )


def effective_mutable_bytes_s(arch: ArchitectureProfile) -> float:
    clock = arch.clock_efficiency * arch.defect_repair_efficiency
    return (
        arch.device_count
        * arch.kv_bandwidth_bytes_s_per_device
        * arch.kv_bandwidth_efficiency
        * clock
    )


def effective_wafer_bisection_bytes_s(arch: ArchitectureProfile) -> float:
    comm = arch.wafer_communication
    if comm is None:
        return math.inf
    return (
        comm.bisection_links
        * comm.link_payload_bytes_per_cycle
        * comm.frequency_hz
        * comm.payload_efficiency
    )


def evaluate_video_workload(
    workload: VideoWorkload,
    arch: ArchitectureProfile,
    *,
    storage_policy: StoragePolicy,
    noc_critical_cut_fraction: float,
    cache_remote_fraction: float = 0.0,
    rom_row_reuse: int | None = None,
) -> dict[str, Any]:
    """Evaluate serial phases under explicit compute, storage, and NoC roofs."""

    for name, value in (
        ("noc_critical_cut_fraction", noc_critical_cut_fraction),
        ("cache_remote_fraction", cache_remote_fraction),
    ):
        if not 0 <= value <= 1:
            raise ValueError(f"{name} must be in [0, 1]")
    if storage_policy == "gpu_hbm" and arch.kind != "gpu":
        raise ValueError("gpu_hbm requires a GPU architecture")
    if storage_policy in {"rom", "same_compute_hbm"} and arch.kind != "rom":
        raise ValueError("ROM policies require a ROM architecture")

    compute_rate = effective_compute_ops_s(arch)
    # A ROM profile's device_count is a maximum pipeline-stage count. A model
    # that fits in one stage receives one wafer roof, not 64 wafer roofs.
    compute_devices = arch.device_count if arch.kind == "gpu" else 1
    compute_rate *= compute_devices
    pipeline_efficiency = arch.pipeline_efficiency
    gpu_weight_rate = effective_weight_bytes_s(arch)
    mutable_rate = effective_mutable_bytes_s(arch)
    if arch.kind == "rom":
        # As above, only one fitting wafer participates.
        mutable_rate /= arch.device_count
    rom_rate = (
        arch.weight_bandwidth_bytes_s_per_device
        * arch.weight_bandwidth_efficiency
        * arch.clock_efficiency
        * arch.defect_repair_efficiency
        if arch.kind == "rom"
        else 0.0
    )
    bisection_rate = effective_wafer_bisection_bytes_s(arch)

    phase_results: list[dict[str, Any]] = []
    total_latency = 0.0
    for phase in workload.phases:
        compute_s = phase.tensor_operations / compute_rate / pipeline_efficiency
        mutable_s = phase.mutable_hbm_bytes / mutable_rate
        if storage_policy == "gpu_hbm":
            weight_s = phase.weight_read_bytes / gpu_weight_rate
            storage_s = weight_s + mutable_s
            rom_s = 0.0
        elif storage_policy == "same_compute_hbm":
            # The same wafer compute/NoC with immutable weights moved into its
            # HBM. Weight and mutable traffic share that physical service.
            weight_s = phase.weight_read_bytes / mutable_rate
            storage_s = weight_s + mutable_s
            rom_s = 0.0
        else:
            array_bytes = phase.rom_array_service_bytes(rom_row_reuse)
            rom_s = array_bytes / rom_rate
            weight_s = rom_s
            storage_s = max(rom_s, mutable_s)

        critical_cut_bytes = (
            noc_critical_cut_fraction * phase.noc_tensor_injected_bytes
            + cache_remote_fraction * phase.noc_cache_injected_bytes
        )
        noc_s = (
            critical_cut_bytes / bisection_rate
            if arch.kind == "rom" and math.isfinite(bisection_rate)
            else 0.0
        )
        core_s = max(compute_s, storage_s)
        latency_s = core_s + noc_s
        total_latency += latency_s
        phase_results.append(
            {
                "phase": phase.name,
                "tensor_operations": phase.tensor_operations,
                "weight_read_bytes": phase.weight_read_bytes,
                "mutable_hbm_bytes": phase.mutable_hbm_bytes,
                "rom_array_service_bytes": (
                    phase.rom_array_service_bytes(rom_row_reuse)
                    if storage_policy == "rom"
                    else 0.0
                ),
                "critical_cut_bytes": critical_cut_bytes,
                "compute_service_s": compute_s,
                "weight_service_s": weight_s,
                "mutable_service_s": mutable_s,
                "storage_service_s": storage_s,
                "noc_serialization_floor_s": noc_s,
                "core_service_s": core_s,
                "phase_latency_s": latency_s,
                "binding_core_term": (
                    "compute" if compute_s >= storage_s else "storage"
                ),
                "binding_storage_term": (
                    "mutable"
                    if mutable_s > weight_s
                    else "immutable_weight"
                ),
                "largest_modeled_term": max(
                    {
                        "compute": compute_s,
                        "storage": storage_s,
                        "noc_serialization_floor": noc_s,
                    },
                    key={
                        "compute": compute_s,
                        "storage": storage_s,
                        "noc_serialization_floor": noc_s,
                    }.get,
                ),
            }
        )

    real_time_factor = total_latency / workload.target_interval_s
    result = {
        "model": workload.model,
        "scenario": workload.scenario,
        "unit": workload.unit,
        "architecture": arch.name,
        "storage_policy": storage_policy,
        "target_interval_s": workload.target_interval_s,
        "latency_s": total_latency,
        "real_time_factor": real_time_factor,
        "meets_target_interval": total_latency <= workload.target_interval_s,
        "units_per_s": 1.0 / total_latency if total_latency > 0 else math.inf,
        "noc_critical_cut_fraction": noc_critical_cut_fraction,
        "cache_remote_fraction": cache_remote_fraction,
        "rom_row_reuse": "whole_call" if rom_row_reuse is None else rom_row_reuse,
        "effective_compute_ops_s": compute_rate,
        "effective_weight_bytes_s": (
            rom_rate
            if storage_policy == "rom"
            else mutable_rate
            if storage_policy == "same_compute_hbm"
            else gpu_weight_rate
        ),
        "effective_mutable_bytes_s": mutable_rate,
        "effective_wafer_bisection_bytes_s": (
            bisection_rate if math.isfinite(bisection_rate) else None
        ),
        "phases": phase_results,
    }
    if workload.unit == "frame":
        result["generated_fps"] = result["units_per_s"]
    else:
        result["generated_video_fps"] = (
            workload.metadata["output_frames"] / total_latency
        )
    return result


def workload_to_dict(workload: VideoWorkload) -> dict[str, Any]:
    return asdict(workload)
