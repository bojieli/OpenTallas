#!/usr/bin/env python3
"""Bound the macro and port cost of sharing one ME activation store per cluster.

This is a capacity/port lower bound, not a routed cluster or a token-rate model.
The selected 1R1W macro view is read directly and source-pinned in the output.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MACRO = ROOT / "physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.json"
ASSEMBLY = ROOT / "results/arch/v41_die_assembly.json"
OUTPUT = ROOT / "results/physical_abi3/asap7/chip/v41_me_shared_cluster_budget.json"


def derive() -> dict:
    raw = MACRO.read_bytes()
    m = json.loads(raw)
    assembly_raw = ASSEMBLY.read_bytes()
    assembly = json.loads(assembly_raw)
    area_um2 = m["area"]["macro_area_um2"]
    tt = m["timing"]["tt"]
    clock_hz = 1.087e9
    mac_lanes = 83_328
    lanes_per_adapter = 64
    adapters = math.ceil(mac_lanes / lanes_per_adapter)
    macros_per_store = 16  # two positions, eight 128-bit banks per position
    macro_bits_per_store = macros_per_store * m["capacity_bits"]
    useful_bits_per_store = 2 * 4096 * 16  # two K4096 BF16 activation groups
    read_macros_per_cycle = 16
    write_macros_per_preload_cycle = 8
    existing_layer_sram_mm2 = assembly["ledger"]["layer"]["by_group_mm2"]["sram"]
    existing_head_sram_mm2 = assembly["ledger"]["head"]["by_group_mm2"]["sram"]
    candidates = []
    for stores in (16, 32, 64):
        max_adapters_per_store = math.ceil(adapters / stores)
        added_macro_mm2 = stores * macros_per_store * area_um2 / 1e6
        candidates.append({
            "shared_stores": stores,
            "max_adapters_per_store": max_adapters_per_store,
            "macro_count": stores * macros_per_store,
            "allocated_macro_bits": stores * macro_bits_per_store,
            "useful_activation_bits": stores * useful_bits_per_store,
            "added_macro_only_area_mm2": round(added_macro_mm2, 6),
            "layer_existing_plus_added_macro_area_mm2": round(existing_layer_sram_mm2 + added_macro_mm2, 6),
            "head_existing_plus_added_macro_area_mm2": round(existing_head_sram_mm2 + added_macro_mm2, 6),
            "one_store_read_output_bits_per_cycle": 2048,
            "one_store_sink_bits_per_cycle_upper_bound": 2048 * max_adapters_per_store,
            "all_adapter_sink_bits_per_cycle": 2048 * adapters,
            "all_store_macro_read_energy_pj_per_active_cycle": round(
                stores * read_macros_per_cycle * tt["read_energy_fj"] / 1000, 6
            ),
            "all_store_macro_read_power_w_if_all_active_at_1p087ghz": round(
                stores * read_macros_per_cycle * tt["read_energy_fj"] * 1e-15 * clock_hz, 6
            ),
            "all_store_macro_leakage_w": round(
                stores * macros_per_store * tt["leakage_nw"] * 1e-9, 6
            ),
            "all_store_clock_input_cap_ff": round(
                stores * macros_per_store * tt["clk_cap_ff"], 6
            ),
        })
    return {
        "scope": "ME wo_a lockstep output-row clusters; macro/port lower bound, no multicast route or rate credit",
        "macro": {
            "path": str(MACRO.relative_to(ROOT)),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "type": m["spec"]["name"],
            "area_um2": area_um2,
            "tt_clk_to_q_ps": tt["clk_to_q_ps"],
            "tt_setup_ps": tt["setup_ps"],
            "tt_read_energy_fj": tt["read_energy_fj"],
            "tt_write_energy_fj": tt["write_energy_fj"],
            "tt_leakage_nw": tt["leakage_nw"],
        },
        "contract": {
            "mac_lanes": mac_lanes,
            "lanes_per_adapter": lanes_per_adapter,
            "adapters": adapters,
            "macros_per_store": macros_per_store,
            "allocated_macro_bits_per_store": macro_bits_per_store,
            "useful_activation_bits_per_store": useful_bits_per_store,
            "macro_depth_utilization": useful_bits_per_store / macro_bits_per_store,
            "read_macros_per_cycle": read_macros_per_cycle,
            "write_macros_per_preload_cycle": write_macros_per_preload_cycle,
            "read_ports": "one 128-bit read per macro per cycle, all 16 macros for two-position 2048-bit tile payload",
            "write_ports": "one 128-bit write per macro per cycle, eight macros for one-position 1024-bit preload payload",
            "read_write_overlap": "wo_a preload and tile-read phases are serialized in the exact single-user schedule; simultaneous users or dissimilar ME ops need arbitration, and same-address read-during-write semantics are not credited",
            "preload_issue_cycles_two_4096_element_groups": 128,
            "macro_write_energy_pj_per_preload_cycle": round(
                write_macros_per_preload_cycle * tt["write_energy_fj"] / 1000, 6
            ),
            "macro_read_energy_pj_per_tile_cycle": round(
                read_macros_per_cycle * tt["read_energy_fj"] / 1000, 6
            ),
            "minimum_clock_period_ps_macro": tt["min_period_ps"],
            "macro_clk_to_q_plus_next_setup_ps": tt["clk_to_q_ps"] + tt["setup_ps"],
            "time_left_at_0p92ns_ps_before_route_and_logic": 920 - tt["clk_to_q_ps"] - tt["setup_ps"],
        },
        "assembly": {
            "path": str(ASSEMBLY.relative_to(ROOT)),
            "sha256": hashlib.sha256(assembly_raw).hexdigest(),
            "existing_layer_sram_mm2": existing_layer_sram_mm2,
            "existing_head_sram_mm2": existing_head_sram_mm2,
        },
        "candidates": candidates,
        "not_included": [
            "multicast buffer and wire area/energy",
            "consumer registers, compute tiles and their clock trees",
            "FP32-to-BF16 RNE converter and four-bank VM read path",
            "SRAM placement channels, macro depth waste and row-select logic",
            "non-wo_a expert scheduling and simultaneous users",
        ],
    }


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(derive(), indent=2, sort_keys=True) + "\n")
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
