"""Executable resource accounting for the chip design, separate from rooflines.

This validates proposed geometry and returns service *lower bounds*. It never
turns an unimplemented schedule, assumed N5 clock, or block route into TPOT.
"""

from __future__ import annotations

from math import ceil, floor
from typing import Any, Mapping


class ArchitectureError(ValueError):
    """The proposed chip cannot provide a declared resource or behavior."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ArchitectureError(message)


def _positive(value: float, name: str) -> None:
    _require(value > 0, f"{name} must be positive")


def align_up(size: int, alignment: int) -> int:
    _require(size >= 0, "size must be nonnegative")
    _positive(alignment, "alignment")
    return ((size + alignment - 1) // alignment) * alignment


def path_rate(*rates: float) -> float:
    _require(bool(rates), "a path must name every service boundary")
    for rate in rates:
        _positive(rate, "path bandwidth")
    return min(rates)


def qwen_units(model: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Exact checkpoint accounting in execution order, including norm gains.

    The named 8B checkpoint has an untied embedding/head and 32/8 GQA heads.
    Changes to that model must update this placement derivation explicitly.
    """
    hidden = int(model["hidden_size"])
    meta = model["metadata"]
    dim = int(meta["head_dim"])
    q = int(meta["num_attention_heads"]) * dim
    kv = int(meta["num_key_value_heads"]) * dim
    embedding = int(model["resident_only_weight_bytes"])
    _require(not meta["tie_word_embeddings"], "placement requires untied head")
    units = [{"id": "embedding", "bytes": embedding, "kv_layers": 0}]
    for layer, layer_bytes in enumerate(model["layer_dense_weight_bytes"]):
        # q/k/v/o plus input RMSNorm and q/k head RMSNorm gains.
        attention = 2 * hidden * (2 * q + 2 * kv) + 2 * hidden + 4 * dim
        post_norm = 2 * hidden
        mlp = int(layer_bytes) - attention - post_norm
        _require(mlp > 0 and mlp % 3 == 0, "MLP matrices must have equal sizes")
        units.extend([
            {"id": f"layer.{layer}.attention", "bytes": attention, "kv_layers": 1},
            {"id": f"layer.{layer}.gate_up", "bytes": 2 * mlp // 3 + post_norm, "kv_layers": 0},
            {"id": f"layer.{layer}.down", "bytes": mlp // 3, "kv_layers": 0},
        ])
    units.append({"id": "head", "bytes": embedding + 2 * hidden, "kv_layers": 0})
    _require(len(model["layer_dense_weight_bytes"]) == model["num_layers"], "layer count mismatch")
    _require(sum(u["bytes"] for u in units) == model["checkpoint_bytes"], "placement does not cover the exact checkpoint")
    return units


def pipeline_stages(units: list[dict[str, Any]], last_units: list[str]) -> list[dict[str, Any]]:
    _require(len(set(last_units)) == len(last_units), "duplicate pipeline cut")
    result: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    for unit in units:
        pending.append(unit)
        if len(result) < len(last_units) and unit["id"] == last_units[len(result)]:
            result.append({"units": pending, "weight_bytes": sum(x["bytes"] for x in pending),
                           "kv_layers": sum(x["kv_layers"] for x in pending)})
            pending = []
    _require(not pending and len(result) == len(last_units), "pipeline cuts must cover every unit once in execution order")
    return result


def qwen_resource_plan(config: Mapping[str, Any], model: Mapping[str, Any]) -> dict[str, Any]:
    """Plan per-die capacity, mesh endpoints and the minimum KV service time."""
    for key in ("clock_hz", "die_area_mm2", "rom_bytes_per_mm2", "sram_bytes_per_mm2",
                "tensor_tile_mm2", "tiles_per_cluster", "assumed_cells_per_mm2"):
        _positive(config[key], key)
    reserve = config["rom_spare_fraction"] + config["rom_quarantine_fraction"]
    _require(0 <= reserve < 1, "ROM reserve fraction must be in [0, 1)")
    units = qwen_units(model)
    qcfg = config["qwen"]
    kv_per_position = 2 * int(model["metadata"]["num_key_value_heads"]) * int(model["metadata"]["head_dim"]) * 2
    capacity_positions = int(qcfg["capacity_positions"])
    _require(0 < qcfg["priced_context_positions"] <= capacity_positions, "priced context must fit capacity")
    profiles = []
    for profile in qcfg["profiles"]:
        dies = int(profile["dies"])
        _positive(dies, "dies")
        _require(profile["partition"] in ("pipeline", "tensor"), "unknown partition")
        _require(profile["kv_store"] in ("sram", "hbm"), "unknown KV store")
        if profile["partition"] == "pipeline":
            stages = pipeline_stages(units, qcfg["pipeline_stage_last_unit"])
            _require(len(stages) == dies, "one pipeline stage required per die")
        else:
            _require(model["metadata"]["num_key_value_heads"] % dies == 0, "tensor sharding must preserve whole KV heads")
            shards = [{**u, "bytes": ceil(u["bytes"] / dies), "kv_layers": u["kv_layers"] / dies} for u in units]
            stages = [{"units": shards, "weight_bytes": sum(x["bytes"] for x in shards),
                       "kv_layers": model["num_layers"] / dies} for _ in range(dies)]
        for stage in stages:
            stage["kv_bytes"] = int(stage["kv_layers"] * capacity_positions * kv_per_position)
            stage["priced_kv_bytes"] = int(stage["kv_layers"] * qcfg["priced_context_positions"] * kv_per_position)
            stage["aligned_weight_bytes"] = sum(align_up(x["bytes"], config["rom_alignment_bytes"]) for x in stage["units"])
            if profile["kv_store"] == "sram":
                _require(stage["kv_bytes"] <= profile["kv_capacity_bytes_per_die"],
                         f"{profile['id']}: KV {stage['kv_bytes']} exceeds per-die {profile['kv_capacity_bytes_per_die']}")
        rom_payload = max(s["aligned_weight_bytes"] for s in stages) + config["rom_misc_reserve_bytes_per_die"]
        rom_raw = ceil(rom_payload / (1 - reserve))
        rom_area = rom_raw / config["rom_bytes_per_mm2"]
        kv_area = profile["kv_capacity_bytes_per_die"] / config["sram_bytes_per_mm2"]
        hbm = profile["kv_store"] == "hbm"
        phy_area = config["hbm_phy_area_mm2"] if hbm else 0
        _require(0 < profile["mesh_x"] <= 2 ** config["coordinate_bits"] and
                 0 < profile["mesh_y"] <= 2 ** config["coordinate_bits"], "mesh exceeds coordinate width")
        mesh_positions = profile["mesh_x"] * profile["mesh_y"]
        router_count = mesh_positions * config["mesh_planes"]
        mesh_area = router_count * config["mesh_router_cells"] / config["assumed_cells_per_mm2"]
        fixed = config["fixed_area_excluding_mesh_mm2"] + mesh_area + config["other_engines_mm2"]
        tile_budget = config["die_area_mm2"] - fixed - rom_area - kv_area - phy_area
        tiles = floor(tile_budget / config["tensor_tile_mm2"])
        _require(tiles > 0, f"{profile['id']}: memory and fixed logic consume the die")
        clusters = ceil(tiles / config["tiles_per_cluster"])
        common_endpoints = (config["scratchpad_endpoints"] + config["dma_endpoints"] +
                            config["link_endpoints"] + config["management_endpoints"])
        # Dimension the shared mesh for the HBM twin as well as the ROM die.
        kv_endpoints = config["kv_group_endpoints"] if not hbm else 0
        rom_endpoints = common_endpoints + clusters + kv_endpoints + (config["hbm_controllers"] if hbm else 0)
        twin_endpoints = common_endpoints + clusters + kv_endpoints + config["hbm_controllers"]
        _require(max(rom_endpoints, twin_endpoints) <= mesh_positions,
                 f"{profile['id']}: {max(rom_endpoints, twin_endpoints)} endpoints exceed {mesh_positions} mesh positions")
        source_rate = config["hbm_bytes_per_cycle"] if hbm else (
            profile["kv_banks"] * config["kv_sram_bank_bytes_per_cycle"] * config["kv_sram_achievable_fraction"])
        delivered = path_rate(source_rate, config["sdn_bytes_per_cycle"], tiles * 128)
        stage_service = [s["priced_kv_bytes"] / delivered for s in stages]
        # Pipeline stages are traversed serially by one token; TP shards run concurrently.
        service = sum(stage_service) if profile["partition"] == "pipeline" else max(stage_service)
        twin_slot = rom_area - (0 if hbm else config["hbm_phy_area_mm2"])
        _require(twin_slot >= 0, "HBM PHY does not fit the replaced ROM slot")
        profiles.append({
            "id": profile["id"], "dies": dies, "partition": profile["partition"],
            "stages": [{**{k: v for k, v in s.items() if k != "units"},
                        "first_unit": s["units"][0]["id"], "last_unit": s["units"][-1]["id"],
                        "unit_count": len(s["units"])} for s in stages],
            "kv_capacity_bytes_per_die": profile["kv_capacity_bytes_per_die"],
            "rom_payload_budget_bytes": rom_payload, "rom_raw_capacity_bytes_per_die": rom_raw,
            "rom_area_mm2": rom_area, "kv_area_mm2": kv_area, "mesh_area_mm2": mesh_area,
            "fixed_and_other_area_mm2": fixed, "phy_area_mm2": phy_area,
            "tiles": tiles, "lanes": tiles * 64, "tile_area_mm2": tiles * config["tensor_tile_mm2"],
            "total_area_mm2": fixed + rom_area + kv_area + phy_area + tiles * config["tensor_tile_mm2"],
            "unused_area_mm2": tile_budget - tiles * config["tensor_tile_mm2"],
            "mesh_shape": [profile["mesh_x"], profile["mesh_y"]], "router_count": router_count,
            "rom_endpoints": rom_endpoints, "hbm_twin_endpoints": twin_endpoints,
            "hbm_twin_replacement_sram_area_mm2": twin_slot,
            "kv_source_bytes_per_cycle": source_rate, "kv_delivered_bytes_per_cycle": delivered,
            "stage_kv_service_cycles": stage_service, "kv_service_lower_bound_us": service / config["clock_hz"] * 1e6,
            "prefetch_overlap_credited": False, "qualified_tpot_us": None,
        })
    flit_bytes = config["link_flit_bits"] / 8
    _require(config["link_flit_bits"] > 0 and config["link_flit_bits"] % 8 == 0, "link flits must contain whole bytes")
    endpoint_rate = path_rate(flit_bytes, config["link_phy_bytes_per_cycle_per_endpoint"])
    return {"schema": "opentallas.chip-resource-check.v1", "grade": "derived_from_assumptions",
            "resource_checks_pass": True, "production_ready": False, "profiles": profiles,
            "link": {"bytes_per_cycle_per_endpoint": endpoint_rate,
                     "bytes_per_cycle_aggregate": endpoint_rate * config["link_endpoints"],
                     "expert_48k_payload_serialization_cycles": ceil(49152 / endpoint_rate)}}
