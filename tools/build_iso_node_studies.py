#!/usr/bin/env python3
"""Derive the two iso-technology hardware studies from the evidence ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from opentallas.technology import (  # noqa: E402
    area_scaled_product_value,
    cim_weight_bandwidth_density_bytes_s_mm2,
    geometric_midpoint,
    hbm_package,
    raw_array_bandwidth_bytes_s,
    scaled_density_bytes_mm2,
    usable_array_capacity_bytes,
)


INPUT = ROOT / "configs" / "hardware" / "technology_inputs.json"
OUTPUTS = {
    "n7_architecture_attribution": (
        ROOT / "configs" / "hardware" / "n7_architecture_attribution.json"
    ),
    "leading_node_market": (
        ROOT / "configs" / "hardware" / "leading_node_market.json"
    ),
}


FORMATS = (
    "fp8_e4m3_x_fp8_e4m3",
    "mxfp4_e2m1_x_fp8_e4m3",
    "mxfp4_e2m1_x_mxfp8_e4m3",
    "bf16_x_bf16",
    "fp4_e2m1_x_fp4_e2m1",
    "fp32_x_fp32",
)


def _load() -> dict[str, Any]:
    return json.loads(INPUT.read_text(encoding="utf-8"))


def _noc(name: str, frequency_hz: float) -> dict[str, Any]:
    common: dict[str, Any] = {
        "frequency_hz": frequency_hz,
        "allreduce_events_per_layer": 2,
        "reduction_bytes_per_element": 4.0,
        "result_bytes_per_element": 2.0,
    }
    if name == "wse2_nearest_neighbor":
        return {
            **common,
            "topology": "nearest_neighbor_mesh",
            "rows": 922,
            "cols": 922,
            "link_payload_bytes_per_cycle": 2.0,
            "hop_cycles": 1.0,
            "bisection_links": 922,
            "endpoint_cycles": 4.0,
            "barrier_cycles": 16.0,
            "payload_efficiency": 0.5,
            "evidence": {
                "mesh_size": "derived:sqrt(850,000 WSE-2 cores)",
                "hop": "published feasibility anchor plus assumed 0.8GHz; not WSE-2 timing disclosure",
                "events": "derived:two FP32 all-reduces in official DeepSeek block",
            },
        }
    if name == "wse3_nearest_neighbor":
        return {
            **common,
            "topology": "nearest_neighbor_mesh",
            "rows": 950,
            "cols": 950,
            "link_payload_bytes_per_cycle": 2.0,
            "hop_cycles": 1.0,
            "bisection_links": 950,
            "endpoint_cycles": 4.0,
            "barrier_cycles": 16.0,
            "payload_efficiency": 0.5,
            "evidence": {
                "mesh_size": "derived:sqrt(900,000 WSE-3 cores)",
                "hop": "published:WSE-3 one-clock nearest-neighbor router hop; clock remains assumed",
                "events": "derived:two FP32 all-reduces in official DeepSeek block",
            },
        }
    if name == "hierarchical_64x64":
        return {
            **common,
            "topology": "hierarchical_mesh",
            "rows": 64,
            "cols": 64,
            "link_payload_bytes_per_cycle": 16.0,
            "hop_cycles": 2.0,
            "bisection_links": 64,
            "local_path_hops": 14,
            "local_hop_cycles": 2.0,
            "endpoint_cycles": 8.0,
            "barrier_cycles": 32.0,
            "payload_efficiency": 0.7,
            "evidence": {
                "topology": "assumed:4096 coarse spatial tiles with explicit global/local traversal",
                "status": "requires target-node floorplan and timing; not calibrated to throughput",
                "events": "derived:two FP32 all-reduces in official DeepSeek block",
            },
        }
    if name == "coarse_reticle_exchange":
        return {
            **common,
            "topology": "coarse_reticle_exchange",
            "rows": 8,
            "cols": 8,
            "link_payload_bytes_per_cycle": 256.0,
            "hop_cycles": 3.0,
            "bisection_links": 8,
            "local_path_hops": 6,
            "local_hop_cycles": 3.0,
            "endpoint_cycles": 8.0,
            "barrier_cycles": 32.0,
            "payload_efficiency": 0.75,
            "evidence": {
                "topology": "aggressive:reticle-granular exchange and reduction tree",
                "status": "implementation hypothesis gated by P&R, repeater, skew, and power evidence",
                "events": "derived:two FP32 all-reduces in official DeepSeek block",
            },
        }
    raise ValueError(f"unknown NoC policy {name!r}")


def _cluster_collective(count: int, generation: str) -> tuple[float, float, float]:
    """Return per-layer latency, payload bandwidth, and synchronization efficiency."""

    if count == 1:
        return 0.0, 1e30, 1.0
    if generation == "a100":
        latency = {2: 4e-6, 4: 6e-6, 8: 8e-6, 16: 12e-6, 32: 16e-6, 64: 22e-6}[count]
        bandwidth = 300e9 if count <= 8 else (150e9 if count <= 16 else 75e9)
    else:
        latency = {2: 2e-6, 4: 3e-6, 8: 4.5e-6, 16: 8e-6}[count]
        bandwidth = 1e12 if count <= 8 else 5e11
    return latency, bandwidth, 0.85 if count <= 8 else 0.80


def _a100_profiles(data: dict[str, Any]) -> list[dict[str, Any]]:
    fact = data["source_facts"]["a100_sxm_80gb"]
    runtime = data["runtime_and_cost_assumptions"]["a100"]
    profiles: list[dict[str, Any]] = []
    deployments = (
        {
            "suffix": "packed-HBM-BF16-execute",
            "policy": "a100_packed_hbm_bf16_execute",
            "conversion": (
                "lossless on-consumption expansion to BF16; released packed HBM "
                "bytes retained; unpack cost omitted"
            ),
            "deployment_evidence": (
                "derived GPU-favorable ceiling: packed values can be decoded before "
                "native BF16 execution, but exact A100 kernel throughput is unmeasured"
            ),
        },
        {
            "suffix": "BF16-resident",
            "policy": "a100_bf16_expanded",
            "conversion": "offline lossless value expansion to BF16; packed scales absorbed",
            "deployment_evidence": (
                "derived native-resident floor: exact tensor-role BF16 expansion in "
                "opentallas.deployment"
            ),
        },
    )
    for deployment in deployments:
        for count in data["n7_architecture_attribution"]["gpu_cluster_sizes"]:
            latency, collective_bw, sync = _cluster_collective(count, "a100")
            paths = {
                numeric_format: {
                    "execution_format": "bf16_x_bf16",
                    "native": False,
                    "operation_multiplier": 1.0,
                    "conversion_policy": deployment["conversion"],
                    "evidence": (
                        "derived:A100 has no native floating FP8/MXFP4/FP4 Tensor "
                        "Core path; conversion cost status is deployment-specific"
                    ),
                }
                for numeric_format in FORMATS[:3] + (FORMATS[4],)
            }
            profiles.append(
                {
                "name": f"NVIDIA-A100-SXM-80GB-{deployment['suffix']}-x{count}",
                "kind": "gpu",
                "device_count": count,
                "weight_capacity_bytes_per_device": fact["hbm_capacity_bytes"],
                "kv_capacity_bytes_per_device": fact["hbm_capacity_bytes"],
                "weight_bandwidth_bytes_s_per_device": fact["hbm_bandwidth_bytes_s"],
                "kv_bandwidth_bytes_s_per_device": fact["hbm_bandwidth_bytes_s"],
                "compute_roofs_ops_s_per_device": {
                    "bf16_x_bf16": fact["bf16_dense_ops_s"],
                    "fp32_x_fp32": fact["fp32_ops_s"],
                },
                "compute_paths": paths,
                "collective_latency_s_per_layer": latency,
                "collective_bandwidth_bytes_s": collective_bw,
                "cost_per_device": runtime["cost_per_gpu"],
                "power_w_per_device": fact["power_w"],
                "cooling_limit_w_per_device": fact["power_w"],
                "hbm_capacity_utilization": runtime["hbm_capacity_utilization"],
                "weight_bandwidth_efficiency": runtime["weight_bandwidth_efficiency"],
                "kv_bandwidth_efficiency": runtime["kv_bandwidth_efficiency"],
                "compute_efficiency": runtime["compute_efficiency"],
                "load_balance_efficiency": runtime["load_balance_efficiency"],
                "clock_efficiency": 0.95,
                "sync_efficiency": sync,
                "hbm_energy_j_per_byte": 5e-12,
                "weight_read_energy_j_per_byte": 5e-12,
                "mac_energy_j_per_op": 0.5e-12,
                "weight_storage_technology": "HBM2e",
                "kv_storage_technology": "HBM2e",
                "storage_capacity_policy": "shared_HBM_weights_plus_KV_no_double_counting",
                "storage_bandwidth_policy": "shared_HBM_weight_and_KV_bytes_add",
                "model_deployment_policy": deployment["policy"],
                "evidence": {
                    "node_memory_compute_power": fact["evidence"],
                    "deployment": deployment["deployment_evidence"],
                    "efficiencies_collective_cost": (
                        "assumed:configured latency is an aggregate per-layer floor "
                        "for both official DeepSeek all-reduces; both logical payloads "
                        "are serialized; no exact DeepSeek A100 measurement"
                    ),
                },
                }
            )
    return profiles


def _b300_profiles(data: dict[str, Any]) -> list[dict[str, Any]]:
    fact = data["source_facts"]["b300"]
    runtime = data["runtime_and_cost_assumptions"]["b300"]
    profiles: list[dict[str, Any]] = []
    for count in data["leading_node_market"]["gpu_cluster_sizes"]:
        latency, collective_bw, sync = _cluster_collective(count, "b300")
        roofs = {
            "fp8_e4m3_x_fp8_e4m3": fact["fp8_dense_ops_s"],
            "mxfp4_e2m1_x_fp8_e4m3": fact["fp8_dense_ops_s"],
            "mxfp4_e2m1_x_mxfp8_e4m3": fact["fp8_dense_ops_s"],
            "bf16_x_bf16": fact["bf16_dense_ops_s"],
            "fp4_e2m1_x_fp4_e2m1": fact["fp4_dense_ops_s"],
            "fp32_x_fp32": fact["fp32_ops_s"],
        }
        profiles.append(
            {
                "name": f"NVIDIA-B300-x{count}",
                "kind": "gpu",
                "device_count": count,
                "weight_capacity_bytes_per_device": fact["hbm_capacity_bytes"],
                "kv_capacity_bytes_per_device": fact["hbm_capacity_bytes"],
                "weight_bandwidth_bytes_s_per_device": fact["hbm_bandwidth_bytes_s"],
                "kv_bandwidth_bytes_s_per_device": fact["hbm_bandwidth_bytes_s"],
                "compute_roofs_ops_s_per_device": roofs,
                "collective_latency_s_per_layer": latency,
                "collective_bandwidth_bytes_s": collective_bw,
                "cost_per_device": runtime["cost_per_gpu"],
                "power_w_per_device": fact["system_allocated_power_w"],
                "cooling_limit_w_per_device": fact["system_allocated_power_w"],
                "hbm_capacity_utilization": runtime["hbm_capacity_utilization"],
                "weight_bandwidth_efficiency": runtime["weight_bandwidth_efficiency"],
                "kv_bandwidth_efficiency": runtime["kv_bandwidth_efficiency"],
                "compute_efficiency": runtime["compute_efficiency"],
                "load_balance_efficiency": runtime["load_balance_efficiency"],
                "clock_efficiency": 0.95,
                "sync_efficiency": sync,
                "hbm_energy_j_per_byte": 4e-12,
                "weight_read_energy_j_per_byte": 4e-12,
                "mac_energy_j_per_op": 0.2e-12,
                "weight_storage_technology": "HBM3e",
                "kv_storage_technology": "HBM3e",
                "storage_capacity_policy": "shared_HBM_weights_plus_KV_no_double_counting",
                "storage_bandwidth_policy": "shared_HBM_weight_and_KV_bytes_add",
                "model_deployment_policy": "official_packed",
                "evidence": {
                    "node_memory_compute_power": fact["evidence"],
                    "fp32_roof": fact["fp32_evidence"],
                    "mixed_expert_roof": "published:DeepSeek says FP4-weight x FP8-activation runs at FP8 peak on current hardware",
                    "efficiencies_collective_cost": (
                        "assumed:configured latency is an aggregate per-layer floor "
                        "for both official DeepSeek all-reduces; both logical payloads "
                        "are serialized; no exact DeepSeek B300 measurement"
                    ),
                },
            }
        )
    return profiles


def _rom_density(
    data: dict[str, Any], study: str, envelope: dict[str, Any]
) -> tuple[float, str]:
    anchor = data["source_facts"]["fabricated_rom_density_anchor"]
    target_nm = data[study]["target_process_nm"]
    if study == "n7_architecture_attribution":
        exponent = envelope["density_scaling_exponent"]
        return (
            scaled_density_bytes_mm2(
                anchor_density_mbit_mm2=anchor["density_mbit_mm2"],
                anchor_node_nm=anchor["process_nm"],
                target_node_nm=target_nm,
                scaling_exponent=exponent,
            ),
            f"derived:28nm fabricated macro scaled to N7 with explicit exponent {exponent}",
        )
    planar = scaled_density_bytes_mm2(
        anchor_density_mbit_mm2=anchor["density_mbit_mm2"],
        anchor_node_nm=anchor["process_nm"],
        target_node_nm=target_nm,
        scaling_exponent=1.0,
    )
    metal = data["source_facts"]["three_d_metal_rom"]["density_bytes_mm2"]
    policy = envelope["density_policy"]
    if policy == "linear_planar_scaling":
        return planar, "derived:linear planar scaling from fabricated 28nm anchor"
    if policy == "geometric_between_planar_and_3d_metal":
        return geometric_midpoint(planar, metal), (
            "derived:geometric midpoint between linear planar case and published "
            "3D-metal evaluation"
        )
    if policy == "published_3d_metal_evaluation":
        return metal, "simulated:published 3D-METRO architecture density; not silicon"
    raise ValueError(f"unknown density policy {policy!r}")


def _rom_compute_ceiling(
    data: dict[str, Any], study: str, envelope: dict[str, Any]
) -> tuple[float, float, str]:
    """Derive the format-neutral array compute ceiling from a public product.

    The returned rate is deliberately a fraction of a public whole-product roof,
    not an invented TOPS/mm2 constant.  It remains an architecture envelope: the
    source product has different arithmetic and floorplan composition, so target
    synthesis/P&R must replace it before any silicon claim.
    """

    fraction = float(envelope["compute_ceiling_fraction"])
    anchor = envelope["compute_anchor"]
    if anchor == "graphcore_gc200_area_scaled":
        gc200 = data["source_facts"]["graphcore_gc200"]
        wafer_area = data["source_facts"]["wafer_scale"]["area_mm2"]
        whole_wafer_ceiling = area_scaled_product_value(
            value=gc200["fp16_ops_s"],
            source_area_mm2=gc200["die_area_mm2"],
            target_area_mm2=wafer_area,
        )
        evidence = (
            "derived:same-node GC200 published FP16 rate area-scaled to WSE area, "
            f"then multiplied by explicit compute-equivalent fraction {fraction:g}; "
            "used as a format-neutral ceiling, not an FP8 silicon measurement"
        )
    elif anchor == "wse3_peak_ai_ops":
        whole_wafer_ceiling = data["source_facts"]["wse3"]["peak_ai_ops_s"]
        evidence = (
            "derived:published WSE-3 125-PFLOP/s marketing ceiling multiplied by "
            f"explicit compute-equivalent fraction {fraction:g}; source arithmetic "
            "is ambiguous and this is not ROM-wafer silicon evidence"
        )
    else:
        raise ValueError(f"unknown compute anchor {anchor!r}")
    return whole_wafer_ceiling * fraction, whole_wafer_ceiling, evidence


def _rom_profiles(data: dict[str, Any], study: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    facts = data["source_facts"]
    wafer = facts["wafer_scale"]
    bandwidth_anchor = facts["rom_bandwidth_anchor"]
    derived_anchor = cim_weight_bandwidth_density_bytes_s_mm2(
        operations_s=bandwidth_anchor["operations_s"],
        macro_area_mm2=bandwidth_anchor["macro_area_mm2"],
        operations_per_weight=bandwidth_anchor["operations_per_weight"],
        weight_bits=bandwidth_anchor["weight_bits"],
    )
    if abs(derived_anchor - bandwidth_anchor["derived_weight_bandwidth_density_bytes_s_mm2"]) > 1:
        raise ValueError("committed ROM bandwidth anchor does not reproduce")
    package_key = "hbm2e_stack" if study.startswith("n7") else "hbm3e_stack"
    hbm_stack = data["packaging_inputs"][package_key]
    pitch = data["packaging_inputs"]["stack_pitch_mm"]["value"]
    runtime_all = data["runtime_and_cost_assumptions"]
    profiles: list[dict[str, Any]] = []
    derivations: list[dict[str, Any]] = []
    for label, envelope in data[study]["rom_envelopes"].items():
        runtime = runtime_all["rom_by_envelope"][label]
        density, density_evidence = _rom_density(data, study, envelope)
        capacity = usable_array_capacity_bytes(
            wafer_area_mm2=wafer["area_mm2"],
            macro_density_bytes_mm2=density,
            array_area_fraction=envelope["rom_area_fraction"],
            usable_fraction=envelope["usable_rom_fraction"],
        )
        bandwidth_density = derived_anchor * envelope["bandwidth_density_scale"]
        weight_bw = raw_array_bandwidth_bytes_s(
            wafer_area_mm2=wafer["area_mm2"],
            array_area_fraction=envelope["rom_area_fraction"],
            bandwidth_density_bytes_s_mm2=bandwidth_density,
        )
        package = hbm_package(
            stacks=envelope["hbm_stacks"],
            stack_capacity_bytes=hbm_stack["capacity_bytes"],
            stack_bandwidth_bytes_s=hbm_stack["bandwidth_bytes_s"],
            wafer_perimeter_mm=wafer["perimeter_mm"],
            stack_pitch_mm=pitch,
        )
        fp8, compute_anchor_ceiling, compute_evidence = _rom_compute_ceiling(
            data, study, envelope
        )
        mixed_multiplier = {"conservative": 1.0, "central": 1.15, "aggressive": 4 / 3}[label]
        roofs = {
            "fp8_e4m3_x_fp8_e4m3": fp8,
            "mxfp4_e2m1_x_fp8_e4m3": fp8 * mixed_multiplier,
            "mxfp4_e2m1_x_mxfp8_e4m3": fp8 * mixed_multiplier,
            "bf16_x_bf16": fp8 / 2,
            "fp4_e2m1_x_fp4_e2m1": fp8 * 2,
            "fp32_x_fp32": fp8 / 16,
        }
        node_label = "N7" if study.startswith("n7") else "N4-class"
        hbm_label = "HBM2e" if study.startswith("n7") else "HBM3e"
        profile = {
            "name": f"ROM-wafer-{node_label}-{hbm_label}-{label}",
            "kind": "rom",
            "device_count": 64,
            "weight_capacity_bytes_per_device": capacity,
            "kv_capacity_bytes_per_device": package.capacity_bytes,
            "weight_bandwidth_bytes_s_per_device": weight_bw,
            "kv_bandwidth_bytes_s_per_device": package.bandwidth_bytes_s,
            "compute_roofs_ops_s_per_device": roofs,
            "collective_latency_s_per_layer": 0.0,
            "collective_bandwidth_bytes_s": 1e30,
            "cost_per_device": runtime_all["wafer_cost_per_device"],
            "power_w_per_device": runtime_all["wafer_power_w"],
            "cooling_limit_w_per_device": runtime_all["wafer_cooling_limit_w"],
            "hbm_capacity_utilization": 0.90,
            "weight_bandwidth_efficiency": runtime["weight_bandwidth_efficiency"],
            "kv_bandwidth_efficiency": runtime["kv_bandwidth_efficiency"],
            "compute_efficiency": runtime["compute_efficiency"],
            "load_balance_efficiency": runtime["load_balance_efficiency"],
            "defect_repair_efficiency": runtime["defect_repair_efficiency"],
            "clock_efficiency": runtime["clock_efficiency"],
            "sync_efficiency": runtime["sync_efficiency"],
            "pipeline_efficiency": runtime["pipeline_efficiency"],
            "hbm_energy_j_per_byte": 5e-12 if study.startswith("n7") else 4e-12,
            "weight_read_energy_j_per_byte": 0.35e-12,
            "mac_energy_j_per_op": 0.2e-12,
            "nre_cost": runtime_all["wafer_nre"],
            "production_units": runtime_all["production_units"],
            "cross_stage_latency_s": 0.25e-6,
            "cross_stage_bandwidth_bytes_s": 200e9 if study.startswith("n7") else 400e9,
            "wafer_communication": _noc(envelope["noc"], envelope["wafer_frequency_hz"]),
            "weight_storage_technology": f"mask_ROM_{node_label}",
            "kv_storage_technology": hbm_label,
            "storage_capacity_policy": "physically_separate_ROM_weights_and_mutable_HBM_KV",
            "storage_bandwidth_policy": "independent_ROM_weight_and_HBM_KV_service",
            "model_deployment_policy": "official_packed",
            "evidence": {
                "capacity_density": density_evidence,
                "read_bandwidth": "derived:YOLoC macro operation rate converted to encoded weight bytes and area-scaled; not wafer silicon",
                "compute": compute_evidence,
                "hbm": f"derived:same-generation {hbm_label} stack normalized from comparator; stack count and pitch are package hypotheses",
                "runtime_cost_power": "assumed:uncertainty inputs; not product evidence",
            },
        }
        profiles.append(profile)
        derivations.append(
            {
                "envelope": label,
                "macro_density_bytes_mm2": density,
                "rom_area_mm2": wafer["area_mm2"] * envelope["rom_area_fraction"],
                "usable_weight_capacity_bytes": capacity,
                "weight_bandwidth_density_bytes_s_mm2": bandwidth_density,
                "raw_weight_bandwidth_bytes_s": weight_bw,
                "hbm": package.to_dict(),
                "fp8_peak_ops_s": fp8,
                "compute_anchor_whole_product_ops_s": compute_anchor_ceiling,
                "compute_ceiling_fraction": envelope["compute_ceiling_fraction"],
                "compute_evidence": compute_evidence,
                "density_evidence": density_evidence,
            }
        )
    return profiles, derivations


def _sram_control(data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    wafer_area = data["source_facts"]["wafer_scale"]["area_mm2"]
    gc200 = data["source_facts"]["graphcore_gc200"]
    total_capacity = area_scaled_product_value(
        value=gc200["sram_bytes"],
        source_area_mm2=gc200["die_area_mm2"],
        target_area_mm2=wafer_area,
    )
    total_bw = area_scaled_product_value(
        value=gc200["sram_bandwidth_bytes_s"],
        source_area_mm2=gc200["die_area_mm2"],
        target_area_mm2=wafer_area,
    )
    weight_fraction = 0.70
    kv_fraction = 1 - weight_fraction
    base_compute = 3e15
    profile = {
        "name": "N7-SRAM-rich-Graphcore-style-derived-control",
        "kind": "sram",
        "device_count": 128,
        "weight_capacity_bytes_per_device": total_capacity * weight_fraction,
        "kv_capacity_bytes_per_device": total_capacity * kv_fraction,
        "weight_bandwidth_bytes_s_per_device": total_bw * weight_fraction,
        "kv_bandwidth_bytes_s_per_device": total_bw * kv_fraction,
        "compute_roofs_ops_s_per_device": {
            "fp8_e4m3_x_fp8_e4m3": base_compute,
            "mxfp4_e2m1_x_fp8_e4m3": base_compute * 1.15,
            "mxfp4_e2m1_x_mxfp8_e4m3": base_compute * 1.15,
            "bf16_x_bf16": base_compute / 2,
            "fp4_e2m1_x_fp4_e2m1": base_compute * 2,
            "fp32_x_fp32": base_compute / 16,
        },
        "collective_latency_s_per_layer": 0.0,
        "collective_bandwidth_bytes_s": 1e30,
        "cost_per_device": 100000.0,
        "power_w_per_device": 15000.0,
        "cooling_limit_w_per_device": 23000.0,
        "hbm_capacity_utilization": 0.90,
        "weight_bandwidth_efficiency": 0.65,
        "kv_bandwidth_efficiency": 0.70,
        "compute_efficiency": 0.60,
        "load_balance_efficiency": 0.85,
        "defect_repair_efficiency": 0.92,
        "clock_efficiency": 0.90,
        "sync_efficiency": 0.88,
        "pipeline_efficiency": 0.90,
        "hbm_energy_j_per_byte": 0.5e-12,
        "weight_read_energy_j_per_byte": 0.5e-12,
        "mac_energy_j_per_op": 0.2e-12,
        "cross_stage_latency_s": 0.25e-6,
        "cross_stage_bandwidth_bytes_s": 200e9,
        "wafer_communication": _noc("hierarchical_64x64", 0.9e9),
        "weight_storage_technology": "SRAM_N7",
        "kv_storage_technology": "SRAM_N7",
        "storage_capacity_policy": "static_70pct_weight_30pct_KV_partition_no_double_counting",
        "storage_bandwidth_policy": "static_partitioned_SRAM_banks",
        "model_deployment_policy": "official_packed",
        "evidence": {
            "capacity_bandwidth": "derived:GC200 N7 product values area-scaled to WSE area at fixed composition",
            "identity": "architectural storage-tier control only; not a Graphcore product/performance claim",
            "numerics_compute_noc": "assumed:held near N7 central ROM case to isolate storage density",
        },
    }
    derivation = {
        "source": gc200["evidence"],
        "area_scale": wafer_area / gc200["die_area_mm2"],
        "total_sram_capacity_bytes": total_capacity,
        "total_sram_bandwidth_bytes_s": total_bw,
        "weight_fraction": weight_fraction,
        "kv_fraction": kv_fraction,
    }
    return profile, derivation


def build() -> dict[str, dict[str, Any]]:
    data = _load()
    input_hash = hashlib.sha256(INPUT.read_bytes()).hexdigest()
    n7_rom, n7_derivations = _rom_profiles(data, "n7_architecture_attribution")
    leading_rom, leading_derivations = _rom_profiles(data, "leading_node_market")
    sram, sram_derivation = _sram_control(data)
    common = {
        "schema_version": 1,
        "generated_from": str(INPUT.relative_to(ROOT)),
        "generated_from_sha256": input_hash,
        "generation_command": "python3 tools/build_iso_node_studies.py --write",
        "methodology": "docs/METHODOLOGY.md",
    }
    return {
        "n7_architecture_attribution": {
            **common,
            "study_id": "n7_architecture_attribution",
            "comparison_contract": "N7 ROM/SRAM + HBM2e-era interfaces versus A100 80GB; WSE-2 only as wafer feasibility anchor",
            "gpu_architectures": _a100_profiles(data),
            "wafer_architectures": [*n7_rom, sram],
            "derivations": {
                "rom_envelopes": n7_derivations,
                "sram_control": sram_derivation,
            },
        },
        "leading_node_market": {
            **common,
            "study_id": "leading_node_market",
            "comparison_contract": "N4-class ROM + HBM3e versus B300 4NP/HBM3e; WSE-3 N5 only as wafer feasibility/physical ceiling anchor",
            "gpu_architectures": _b300_profiles(data),
            "wafer_architectures": leading_rom,
            "derivations": {"rom_envelopes": leading_derivations},
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write committed JSON studies")
    args = parser.parse_args(argv)
    studies = build()
    if args.write:
        for key, path in OUTPUTS.items():
            path.write_text(
                json.dumps(studies[key], indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            print(path.relative_to(ROOT))
    else:
        print(json.dumps(studies, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
