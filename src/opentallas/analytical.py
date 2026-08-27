"""Constraint-complete first-order inference architecture simulator.

Every reported step exposes the component times and binding constraint.  This
keeps C1--C11 auditable and prevents a single attractive throughput number from
hiding a capacity, latency, or thermal failure.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
from typing import Any

from .schema import ArchitectureProfile, HardwareProfile, ModelProfile, SimulationRequest
from .workload import (
    KVTraffic,
    WeightTraffic,
    draft_weight_traffic,
    expected_engaged_devices,
    kv_traffic,
    linear_partition,
    per_layer_kv_read_write,
    per_layer_kv_storage,
    rho_one,
    weight_traffic,
)


SECONDS_PER_YEAR = 365.25 * 24 * 3600


@dataclass(frozen=True)
class OperatingPoint:
    model: str
    architecture: str
    architecture_kind: str
    context_tokens: int
    batch_size: int
    feasible: bool
    infeasible_reasons: tuple[str, ...]
    stages: int
    max_concurrent_users: int
    expected_output_tokens_per_step: float
    step_interval_s: float
    per_user_token_latency_s: float
    aggregate_tokens_s: float
    per_user_tokens_s: float
    amortized_capex_per_million_tokens: float
    electricity_cost_per_million_tokens: float
    partial_tco_per_million_tokens: float
    power_w: float
    rho_one: float
    binding_constraint: str
    component_times_s: dict[str, float]
    metrics: dict[str, float | str | bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ROMLayout:
    """A fixed, context-independent contiguous layer-to-wafer assignment."""

    stages: int
    partitions: tuple[tuple[int, int], ...]
    layer_storage_bytes: tuple[float, ...]
    checkpoint_storage_bytes: tuple[float, ...]
    exact_layer_inventory: bool
    reasons: tuple[str, ...] = ()


def _layer_weight_vectors(model: ModelProfile) -> tuple[tuple[float, ...], tuple[float, ...], bool]:
    if model.layer_dense_weight_bytes:
        return (
            model.layer_dense_weight_bytes,
            model.layer_routed_weight_bytes,
            True,
        )
    # Backward-compatible fallback for external profiles. Generated standard
    # profiles always provide exact layer vectors and tests flag any regression.
    return (
        tuple(model.dense_weight_bytes / model.num_layers for _ in range(model.num_layers)),
        tuple(model.routed_weight_bytes / model.num_layers for _ in range(model.num_layers)),
        False,
    )


def _rom_layout(model: ModelProfile, arch: ArchitectureProfile) -> ROMLayout:
    dense, routed, exact = _layer_weight_vectors(model)
    layer_bytes = tuple(d + r for d, r in zip(dense, routed))
    capacity = arch.weight_capacity_bytes_per_device
    minimum = max(1, math.ceil(model.checkpoint_bytes / capacity))
    last_partitions: tuple[tuple[int, int], ...] = ((0, model.num_layers),)
    last_layer_storage: tuple[float, ...] = (sum(layer_bytes),)

    for stages in range(minimum, model.num_layers + 1):
        partitions = linear_partition(layer_bytes, stages)
        stage_layer_storage = tuple(
            sum(layer_bytes[start:end]) for start, end in partitions
        )
        last_partitions = partitions
        last_layer_storage = stage_layer_storage
        if len(partitions) != stages or max(stage_layer_storage) > capacity:
            continue
        if model.checkpoint_bytes > stages * capacity:
            continue

        # Non-layer decode tensors, draft modules, and resident-only arrays are
        # capacity-resident but need not define the contiguous main-layer cut.
        # Stripe them over remaining slack in proportion to that slack. This is a
        # placement assumption and is reported explicitly in every result.
        unassigned = model.checkpoint_bytes - sum(stage_layer_storage)
        if unassigned < -max(1.0, model.checkpoint_bytes * 1e-9):
            return ROMLayout(
                stages,
                partitions,
                stage_layer_storage,
                stage_layer_storage,
                exact,
                ("C9: per-layer decode inventory exceeds checkpoint storage",),
            )
        unassigned = max(0.0, unassigned)
        slack = tuple(capacity - value for value in stage_layer_storage)
        total_slack = sum(slack)
        if unassigned > total_slack + 1.0:
            continue
        fraction = unassigned / total_slack if total_slack else 0.0
        checkpoint_storage = tuple(
            value + free * fraction
            for value, free in zip(stage_layer_storage, slack)
        )
        reasons = () if stages <= arch.device_count else (
            f"C9: {stages} capacity-legal ROM stages required, profile permits {arch.device_count}",
        )
        return ROMLayout(
            stages,
            partitions,
            stage_layer_storage,
            checkpoint_storage,
            exact,
            reasons,
        )

    return ROMLayout(
        max(minimum, len(last_partitions)),
        last_partitions,
        last_layer_storage,
        last_layer_storage,
        exact,
        (
            "C9: no capacity-legal contiguous layer partition exists without "
            "splitting a layer across ROM stages",
        ),
    )


def _capacity(
    model: ModelProfile,
    arch: ArchitectureProfile,
    kv: KVTraffic,
    stages: int,
    context_tokens: int,
    partitions: tuple[tuple[int, int], ...],
) -> tuple[int, tuple[float, ...], list[str]]:
    reasons: list[str] = []
    if arch.kind == "gpu":
        total_weight_capacity = (
            arch.device_count
            * arch.weight_capacity_bytes_per_device
            * arch.hbm_capacity_utilization
        )
        if model.checkpoint_bytes > total_weight_capacity:
            reasons.append(
                f"C7: checkpoint requires {model.checkpoint_bytes:.3g} B but GPU capacity is "
                f"{total_weight_capacity:.3g} B"
            )
        # GPU weights and KV share HBM. ``kv_capacity`` may be set below physical
        # capacity to reserve runtime workspace.
        available = (
            arch.device_count
            * arch.kv_capacity_bytes_per_device
            * arch.hbm_capacity_utilization
            - model.checkpoint_bytes
        )
        users = max(0, math.floor(available / kv.storage_bytes_per_user)) if available > 0 else 0
        stage_storage = (kv.storage_bytes_per_user,)
    else:
        # HBM is physically local to each wafer edge. Every long-lived session
        # has a persistent layer shard on every stage, including while a different
        # microbatch is active there. Therefore the worst stage, not pooled HBM,
        # limits resident users. This also exposes hybrid-attention imbalance.
        layer_storage = per_layer_kv_storage(model, context_tokens)
        stage_storage = tuple(
            sum(layer_storage[start:end]) for start, end in partitions
        )
        if len(stage_storage) != stages or any(value <= 0 for value in stage_storage):
            reasons.append("C8/C9: invalid or empty stage-local KV partition")
            users = 0
        else:
            users = min(
                math.floor(
                    arch.kv_capacity_bytes_per_device
                    * arch.hbm_capacity_utilization
                    / value
                )
                for value in stage_storage
            )
    if users == 0:
        reasons.append("C7/C8: no complete user KV cache fits after weight allocation")
    return users, stage_storage, reasons


def _binding(component_times: dict[str, float], thermal_scale: float) -> str:
    if thermal_scale > 1.0 + 1e-12:
        return "thermal_cooling"
    return max(component_times, key=component_times.get)


class AnalyticalSimulator:
    def __init__(self, hardware: HardwareProfile):
        self.hardware = hardware
        self._rom_layout_cache: dict[tuple[object, ...], ROMLayout] = {}

    def _cached_rom_layout(
        self, model: ModelProfile, arch: ArchitectureProfile
    ) -> ROMLayout:
        # Layout is deliberately independent of context and batch: mask-ROM layer
        # placement cannot change between operating points. Sensitivity variants
        # that change encoded weight bytes or ROM capacity receive a distinct key.
        key = (
            model.name,
            model.source_revision,
            model.checkpoint_bytes,
            model.dense_weight_bytes,
            model.routed_weight_bytes,
            model.layer_dense_weight_bytes,
            model.layer_routed_weight_bytes,
            arch.weight_capacity_bytes_per_device,
            arch.device_count,
        )
        if key not in self._rom_layout_cache:
            self._rom_layout_cache[key] = _rom_layout(model, arch)
        return self._rom_layout_cache[key]

    def simulate_pair(self, model: ModelProfile, request: SimulationRequest) -> tuple[OperatingPoint, OperatingPoint]:
        return (
            self.simulate(model, self.hardware.gpu, request),
            self.simulate(model, self.hardware.rom, request),
        )

    def simulate(
        self,
        model: ModelProfile,
        arch: ArchitectureProfile,
        request: SimulationRequest,
        *,
        measured_expert_coverage: float | None = None,
    ) -> OperatingPoint:
        if request.context_tokens > model.max_context_tokens:
            raise ValueError("requested context exceeds model maximum")

        spec = request.speculation
        positions = spec.draft_tokens + 1 if spec.draft_tokens else 1
        expected_outputs = spec.expected_output_tokens
        main_weights = weight_traffic(
            model,
            request.batch_size,
            positions_per_step=positions,
            measured_coverage=measured_expert_coverage,
        )
        draft_weights = (
            draft_weight_traffic(
                model,
                request.batch_size,
                draft_tokens=spec.draft_tokens,
            )
            if spec.draft_tokens
            else WeightTraffic(0.0, 0.0, 0.0, 0.0)
        )
        weights = WeightTraffic(
            dense_bytes=main_weights.dense_bytes + draft_weights.dense_bytes,
            routed_bytes=main_weights.routed_bytes + draft_weights.routed_bytes,
            # Main verification sees at least as many positions as the draft
            # block, so it sets the engaged-device envelope.
            routed_expert_coverage=main_weights.routed_expert_coverage,
            distinct_experts_per_layer=main_weights.distinct_experts_per_layer,
        )
        kv = kv_traffic(model, request.context_tokens)

        if arch.kind == "rom":
            layout = self._cached_rom_layout(model, arch)
            stages = layout.stages
            partitions = layout.partitions
            layout_reasons = list(layout.reasons)
            stage_checkpoint_storage = layout.checkpoint_storage_bytes
            stage_layer_storage = layout.layer_storage_bytes
            exact_layer_inventory = layout.exact_layer_inventory
        else:
            stages = 1
            partitions = ((0, model.num_layers),)
            layout_reasons = []
            stage_checkpoint_storage = (model.checkpoint_bytes,)
            stage_layer_storage = (
                sum(model.layer_dense_weight_bytes)
                + sum(model.layer_routed_weight_bytes),
            )
            exact_layer_inventory = bool(model.layer_dense_weight_bytes)
        max_users, stage_kv_storage, reasons = _capacity(
            model,
            arch,
            kv,
            stages,
            request.context_tokens,
            partitions,
        )
        reasons = layout_reasons + reasons
        # A ROM pipeline has one microbatch resident at every stage.  Therefore
        # batch is per stage and the number of simultaneously stored sessions is
        # batch*stages.  Comparing batch alone with aggregate HBM capacity would
        # overstate high-batch feasibility by exactly the pipeline depth.
        resident_users_required = request.batch_size * stages if arch.kind == "rom" else request.batch_size
        if resident_users_required > max_users:
            reasons.append(
                f"C7/C8: {resident_users_required} resident users required "
                f"(batch {request.batch_size} x {stages} stages) exceeds capacity {max_users}"
            )

        effective_clock = arch.clock_efficiency * arch.defect_repair_efficiency
        dense_active_parameters = max(
            0.0, min(model.active_parameters, model.dense_parameters)
        )
        routed_active_parameters = model.active_parameters - dense_active_parameters
        dense_ops = (
            model.operations_per_active_parameter
            * dense_active_parameters
            * request.batch_size
            * positions
        )
        routed_ops = (
            model.operations_per_active_parameter
            * routed_active_parameters
            * request.batch_size
            * positions
        )
        total_ops = dense_ops + routed_ops
        kv_transfer_per_user = (
            kv.read_bytes * arch.kv_read_amplification + kv.write_bytes
        )
        kv_transfer = kv_transfer_per_user * request.batch_size * positions
        collective_payload_bytes = (
            request.batch_size * positions * model.hidden_size * (2 + 4)
        )

        if arch.kind == "gpu":
            devices = arch.device_count
            all_weight_bw = (
                devices
                * arch.weight_bandwidth_bytes_s_per_device
                * arch.weight_bandwidth_efficiency
                * effective_clock
            )
            engaged = expected_engaged_devices(devices, weights.distinct_experts_per_layer)
            routed_bw = (
                engaged
                * arch.weight_bandwidth_bytes_s_per_device
                * arch.weight_bandwidth_efficiency
                * arch.load_balance_efficiency
                * effective_clock
            )
            dense_weight_s = weights.dense_bytes / all_weight_bw
            routed_weight_s = weights.routed_bytes / routed_bw
            weight_s = dense_weight_s + routed_weight_s
            kv_s = kv_transfer / (
                devices
                * arch.kv_bandwidth_bytes_s_per_device
                * arch.kv_bandwidth_efficiency
                * effective_clock
            )
            dense_compute_s = dense_ops / (
                devices
                * arch.higher_precision_peak_ops_s_per_device
                * arch.compute_efficiency
                * effective_clock
            )
            routed_compute_s = routed_ops / (
                devices
                * arch.peak_ops_s_per_device
                * arch.compute_efficiency
                * effective_clock
                * arch.load_balance_efficiency
            )
            compute_s = dense_compute_s + routed_compute_s
            collective_s = (
                model.num_layers
                * (
                    arch.collective_latency_s_per_layer
                    + collective_payload_bytes / arch.collective_bandwidth_bytes_s
                )
                / arch.sync_efficiency
            )
            component_times = {
                "gpu_weight_memory_C3": weight_s,
                "kv_memory_C2": kv_s,
                "compute_C5": compute_s,
                "collective_floor_C6": collective_s,
            }
            # Weight and KV use the same HBM channels and are additive. Compute
            # can overlap memory, while collectives remain a serialized floor.
            core_s = max(weight_s + kv_s, compute_s) + collective_s
            used_devices = devices
            per_user_multiplier = 1.0
            stage_balance = 1.0
            stage_service_times = (core_s,)
            stage_weight_transfer = (weights.total_bytes,)
            stage_kv_transfer = (kv_transfer,)
            stage_ops = (total_ops,)
            stage_dense_ops = (dense_ops,)
            stage_routed_ops = (routed_ops,)
            bottleneck_stage = 0
        else:
            used_devices = stages
            layer_dense, layer_routed, exact_layer_inventory = _layer_weight_vectors(model)
            unlayered_main_dense = max(
                0.0, model.dense_weight_bytes - sum(layer_dense)
            )
            unlayered_main_routed = max(
                0.0, model.routed_weight_bytes - sum(layer_routed)
            )
            unlayered_main_traffic = (
                unlayered_main_dense
                + unlayered_main_routed * main_weights.routed_expert_coverage
            )
            stage_weight_transfer = tuple(
                sum(
                    layer_dense[index]
                    + layer_routed[index] * main_weights.routed_expert_coverage
                    for index in range(start, end)
                )
                + (unlayered_main_traffic + draft_weights.total_bytes) / stages
                for start, end in partitions
            )

            layer_kv = per_layer_kv_read_write(model, request.context_tokens)
            stage_kv_per_user = tuple(
                sum(
                    read * arch.kv_read_amplification + write
                    for read, write in layer_kv[start:end]
                )
                for start, end in partitions
            )
            stage_kv_transfer = tuple(
                value * request.batch_size * positions for value in stage_kv_per_user
            )

            # Exact per-layer active parameter counts are not published. Use the
            # released-format B=1 active-byte distribution as the deterministic
            # operation-share proxy, and report that assumption explicitly.
            routed_fraction = model.routed_fraction_per_token
            layer_dense_proxy = layer_dense
            layer_routed_proxy = tuple(
                routed * routed_fraction for routed in layer_routed
            )
            stage_dense_proxy = tuple(
                sum(layer_dense_proxy[start:end]) + unlayered_main_dense / stages
                for start, end in partitions
            )
            stage_routed_proxy = tuple(
                sum(layer_routed_proxy[start:end])
                + unlayered_main_routed * routed_fraction / stages
                for start, end in partitions
            )
            dense_proxy_total = sum(stage_dense_proxy)
            routed_proxy_total = sum(stage_routed_proxy)
            if dense_proxy_total <= 0:
                stage_dense_ops = tuple(dense_ops / stages for _ in partitions)
            else:
                stage_dense_ops = tuple(
                    dense_ops * value / dense_proxy_total for value in stage_dense_proxy
                )
            if routed_proxy_total <= 0:
                stage_routed_ops = tuple(routed_ops / stages for _ in partitions)
            else:
                stage_routed_ops = tuple(
                    routed_ops * value / routed_proxy_total
                    for value in stage_routed_proxy
                )
            stage_ops = tuple(
                dense + routed
                for dense, routed in zip(stage_dense_ops, stage_routed_ops)
            )

            weight_times = tuple(
                value
                / (
                    arch.weight_bandwidth_bytes_s_per_device
                    * arch.weight_bandwidth_efficiency
                    * effective_clock
                )
                for value in stage_weight_transfer
            )
            kv_times = tuple(
                value
                / (
                    arch.kv_bandwidth_bytes_s_per_device
                    * arch.kv_bandwidth_efficiency
                    * effective_clock
                )
                for value in stage_kv_transfer
            )
            compute_times = tuple(
                dense
                / (
                    arch.higher_precision_peak_ops_s_per_device
                    * arch.compute_efficiency
                    * effective_clock
                )
                + routed
                / (
                    arch.peak_ops_s_per_device
                    * arch.compute_efficiency
                    * effective_clock
                    * arch.load_balance_efficiency
                )
                for dense, routed in zip(stage_dense_ops, stage_routed_ops)
            )
            per_layer_collective_s = (
                arch.collective_latency_s_per_layer
                + collective_payload_bytes / arch.collective_bandwidth_bytes_s
            ) / arch.sync_efficiency
            collective_times = tuple(
                (end - start) * per_layer_collective_s for start, end in partitions
            )
            stage_service_times = tuple(
                max(weight, kv_time, compute) + collective
                for weight, kv_time, compute, collective in zip(
                    weight_times, kv_times, compute_times, collective_times
                )
            )
            bottleneck_stage = max(
                range(stages), key=lambda index: stage_service_times[index]
            )
            weight_s = max(weight_times)
            kv_s = max(kv_times)
            compute_s = max(compute_times)
            collective_s = max(collective_times)
            component_times = {
                "rom_full_array_read_C4": weight_s,
                "kv_beachfront_C8": kv_s,
                "compute_C5": compute_s,
                "collective_floor_C6": collective_s,
            }
            mean_stage_service = sum(stage_service_times) / stages
            stage_balance = mean_stage_service / max(stage_service_times)
            core_s = max(stage_service_times) / arch.pipeline_efficiency
            per_user_multiplier = stages

        # Explicit draft cost fixes the old pure-multiplier speculation model.
        # The target verification above already processes every candidate. Draft
        # generation is serial and charged as a measured/assumed fraction of a
        # one-position active-model compute pass.
        draft_s = 0.0
        if spec.draft_tokens:
            one_position_compute = compute_s / positions
            draft_s = spec.draft_tokens * spec.draft_cost_fraction * one_position_compute
            component_times["speculative_draft_cost"] = draft_s
        raw_interval = core_s + draft_s

        energy_j = (
            weights.total_bytes * arch.weight_read_energy_j_per_byte
            + kv_transfer * arch.hbm_energy_j_per_byte
            + total_ops * arch.mac_energy_j_per_op
        )
        dynamic_power = energy_j / max(raw_interval, 1e-30)
        # ``power_w_per_device`` is the allocated steady operating-power proxy,
        # not energy added on top of the activity estimate.  Taking the maximum
        # avoids the former error of reporting implausibly tiny system power from
        # MAC/HBM dynamic-energy terms alone, while also avoiding double-counting
        # power already included in a published system envelope.
        steady_operating_power = used_devices * arch.power_w_per_device
        cooling_limit = used_devices * arch.cooling_limit_w_per_device
        thermal_scale = max(1.0, max(dynamic_power, steady_operating_power) / cooling_limit)
        interval = raw_interval * thermal_scale
        throttled_dynamic_power = energy_j / max(interval, 1e-30)
        power = max(throttled_dynamic_power, steady_operating_power)

        cross_stage = max(0, stages - 1) * arch.cross_stage_latency_s
        per_user_step_latency = interval * per_user_multiplier + cross_stage
        aggregate_tps = request.batch_size * expected_outputs / interval
        per_user_tps = expected_outputs / per_user_step_latency

        capex = used_devices * arch.cost_per_device + arch.nre_cost / arch.production_units
        lifetime_tokens = (
            aggregate_tps
            * arch.lifetime_years
            * SECONDS_PER_YEAR
            * arch.utilization
        )
        amortized_capex_per_million = (
            capex / lifetime_tokens * 1e6 if lifetime_tokens > 0 else math.inf
        )
        active_lifetime_hours = (
            arch.lifetime_years * SECONDS_PER_YEAR / 3600 * arch.utilization
        )
        lifetime_electricity_cost = (
            power
            / 1000
            * arch.facility_pue
            * active_lifetime_hours
            * arch.electricity_cost_per_kwh
        )
        electricity_cost_per_million = (
            lifetime_electricity_cost / lifetime_tokens * 1e6
            if lifetime_tokens > 0
            else math.inf
        )
        partial_tco_per_million = (
            amortized_capex_per_million + electricity_cost_per_million
        )

        # Short-prompt prefill is weight-load-bound; long-prompt prefill is
        # compute-bound. Prefix hits remove work, and disaggregation pays a cold
        # KV handoff explicitly.
        uncached_prompt = request.prompt_tokens * (1.0 - request.prefix_cache_hit_rate)
        prefill_s = 0.0
        kv_handoff_s = 0.0
        if uncached_prompt:
            prefill_weight_s = model.checkpoint_bytes / (
                used_devices
                * arch.weight_bandwidth_bytes_s_per_device
                * arch.weight_bandwidth_efficiency
                * effective_clock
            )
            prefill_dense_compute_s = (
                model.operations_per_active_parameter
                * dense_active_parameters
                * uncached_prompt
                / (
                    used_devices
                    * arch.higher_precision_peak_ops_s_per_device
                    * arch.compute_efficiency
                    * effective_clock
                )
            )
            prefill_routed_compute_s = (
                model.operations_per_active_parameter
                * routed_active_parameters
                * uncached_prompt
                / (
                    used_devices
                    * arch.peak_ops_s_per_device
                    * arch.compute_efficiency
                    * effective_clock
                    * arch.load_balance_efficiency
                )
            )
            prefill_compute_s = prefill_dense_compute_s + prefill_routed_compute_s
            prefill_s = max(prefill_weight_s, prefill_compute_s)
            if request.disaggregated_prefill:
                built_fraction = uncached_prompt / max(request.context_tokens, 1)
                kv_handoff_s = (
                    kv.storage_bytes_per_user
                    * built_fraction
                    / request.kv_handoff_bandwidth_bytes_s
                )

        feasible = not reasons
        if not feasible:
            aggregate_tps = 0.0
            per_user_tps = 0.0
            amortized_capex_per_million = math.inf
            electricity_cost_per_million = math.inf
            partial_tco_per_million = math.inf

        metrics: dict[str, float | str | bool] = {
            "C1_expert_coverage": main_weights.routed_expert_coverage,
            "C1_draft_expert_coverage": draft_weights.routed_expert_coverage,
            "C1_weight_bytes_per_step": weights.total_bytes,
            "C1_main_weight_bytes_per_step": main_weights.total_bytes,
            "C1_draft_weight_bytes_per_step": draft_weights.total_bytes,
            "C5_dense_higher_precision_operations": dense_ops,
            "C5_routed_low_precision_operations": routed_ops,
            "C5_dense_active_parameters": dense_active_parameters,
            "C5_routed_active_parameters": routed_active_parameters,
            "C2_kv_read_bytes_per_user_token": kv.read_bytes,
            "C2_kv_write_bytes_per_user_token": kv.write_bytes,
            "C2_kv_read_amplification": arch.kv_read_amplification,
            "C2_kv_transfer_bytes_per_user_token_after_amplification": kv_transfer_per_user,
            "C3_engaged_gpu_devices": (
                expected_engaged_devices(arch.device_count, weights.distinct_experts_per_layer)
                if arch.kind == "gpu"
                else float(stages)
            ),
            "C7_C8_kv_storage_bytes_per_user": kv.storage_bytes_per_user,
            "C7_C8_hbm_capacity_utilization": arch.hbm_capacity_utilization,
            "C7_C8_resident_users_required": float(resident_users_required),
            "C7_C8_max_batch_per_stage": float(max_users // stages),
            "C7_C8_stage_kv_storage_bytes_per_user": str(stage_kv_storage),
            "C9_pipeline_stages": float(stages),
            "C9_exact_layer_weight_inventory": exact_layer_inventory,
            "C9_layer_storage_bytes_by_stage": str(stage_layer_storage),
            "C9_checkpoint_storage_bytes_by_stage": str(stage_checkpoint_storage),
            "C9_non_layer_storage_policy": "striped_proportional_to_stage_slack",
            "C10_per_user_pipeline_multiplier": float(per_user_multiplier),
            "C11_stage_balance_efficiency": stage_balance,
            "C11_combined_pipeline_efficiency": stage_balance * arch.pipeline_efficiency,
            "C11_bottleneck_stage": float(bottleneck_stage),
            "C11_stage_service_times_s": str(stage_service_times),
            "C11_stage_weight_transfer_bytes": str(stage_weight_transfer),
            "C11_stage_kv_transfer_bytes": str(stage_kv_transfer),
            "C11_stage_operations": str(stage_ops),
            "C11_stage_dense_operations": str(stage_dense_ops),
            "C11_stage_routed_operations": str(stage_routed_ops),
            "C11_operation_partition_proxy": "released_format_active_bytes_at_batch_one",
            "thermal_scale": thermal_scale,
            "dynamic_power_w_before_throttle": dynamic_power,
            "steady_operating_power_w": steady_operating_power,
            "electricity_cost_per_kwh": arch.electricity_cost_per_kwh,
            "facility_pue": arch.facility_pue,
            "partial_tco_scope": "hardware_and_nre_capex_plus_active_electricity_only",
            "prefill_latency_s": prefill_s,
            "kv_handoff_latency_s": kv_handoff_s,
            "router_trace_status": model.router_trace_status,
            "stage_partitions": str(partitions),
        }
        return OperatingPoint(
            model=model.name,
            architecture=arch.name,
            architecture_kind=arch.kind,
            context_tokens=request.context_tokens,
            batch_size=request.batch_size,
            feasible=feasible,
            infeasible_reasons=tuple(reasons),
            stages=stages,
            max_concurrent_users=max_users,
            expected_output_tokens_per_step=expected_outputs,
            step_interval_s=interval,
            per_user_token_latency_s=(1.0 / per_user_tps if per_user_tps else math.inf),
            aggregate_tokens_s=aggregate_tps,
            per_user_tokens_s=per_user_tps,
            amortized_capex_per_million_tokens=amortized_capex_per_million,
            electricity_cost_per_million_tokens=electricity_cost_per_million,
            partial_tco_per_million_tokens=partial_tco_per_million,
            power_w=power,
            rho_one=rho_one(model, request.context_tokens),
            binding_constraint=(
                "capacity_C7_C8_C9"
                if reasons
                else _binding(component_times, thermal_scale)
            ),
            component_times_s=component_times,
            metrics=metrics,
        )
