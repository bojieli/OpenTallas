"""Candidate per-stack V4.1 200K/1M region ledger, pending architecture review.

All addresses are 32-byte sectors. This generator does not configure the die.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATHS = (
    "rtl/chip/ot_chip_v41x_die.sv",
    "rtl/chip/ot_chip_v41x_tile.sv",
    "rtl/chip/ot_chip_v41x_window_kv_prefetch.sv",
    "rtl/chip/ot_chip_v41x_ckv_selected_dma.sv",
    "rtl/chip/ot_chip_v41x_rope_region_guard.sv",
    "rtl/chip/ot_chip_v41x_rope_hbm_cache.sv",
    "rtl/chip/ot_chip_v41x_kv_rope_reqmux.sv",
    "rtl/chip/ot_chip_v41x_hbm_karb.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_shard_addr.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_pool_kwr.sv",
    "rtl/chip/ot_chip_v41x_hbm3e_phy.sv",
    "configs/hardware/technology.json",
    "results/arch/arch_budget_v41.json",
)


def check_sources(src: dict[str, bytes]) -> None:
    die, tile, win, ckv, guard, rope, mux, arb, idx, kwr, phy = (
        src[p].decode() for p in PATHS[:11]
    )
    assert "parameter integer IDX_SHARDED = 0" in tile
    assert ".IDX_SHARDED(" not in die
    assert "parameter integer W_HBM = 1" in tile
    assert ".W_HBM(" not in die
    assert "localparam integer WIN_SECTORS = KV_USERS * 128 * 17" in die
    assert ".c_v(4'b0)" in die and "assign kv_ok = 1'b0" in die
    assert "wire [23:0] wq_addr" in die
    assert "ot_hdc_qstream #(.BL(BL), .QLB(QLB), .AW(AW), .HAW(24)" in tile
    assert "parameter integer W_STACK = 0" in die
    assert ".W_PORT(s == W_STACK)" in die
    assert "ot_hdc_hbm_model #(.NPC(NPC_W), .AW(24)" in phy
    assert "wire [1:0] source_stack = source_id[7:6]" in ckv
    assert "wire [1:0] source_die = source_id[5:4]" in ckv
    assert "(SEC_W+5)'(active_local_source) * (SEC_W+5)'(9)" in ckv
    assert "localparam integer PITCH = 17" in win
    assert "MAX_POS=1048576" in guard and "TABLE_SECTORS=64'(MAX_POS)*2" in guard
    assert "A table is striped in 32-byte sectors" in rope
    assert "ot_chip_v41x_kv_reqmux" in mux and "wire choose_k=k_v[s]" in mux
    assert "Per pseudo-channel: when both present" in arb
    assert "sb_sec = (sb << 11) + (sb << 7)" in idx
    assert "w_stack_mask=SHARDED ? (4'b0001 << row[5:4]) : 4'b1111" in kwr
    assert re.search(r"parameter integer K_MEM\s*=\s*1\s*<<\s*19", die)


def _region(start: int, count: int, owner: str, status: str, service: str) -> dict:
    return {"start_sector": start, "count_sectors": count,
            "end_sector_exclusive": start + count, "owner": owner,
            "status": status, "service": service}


def _stack_regions(index_n: int, ckv_n: int, window_n: int, weight_n: int,
                   rope_n: int, comparator: bool) -> list[dict]:
    cursor = 0
    regions = []
    for count, owner, status, service in (
        (index_n, "index_keys", "candidate_requires_IDX_SHARDED", "B port, hashed among 32 PCs"),
        (window_n, "window_fp8", "connected_module_candidate_base", "K port, one request per stack"),
        (ckv_n, "selected_ckv_fp4", "standalone_dma_unconnected", "K port, one request per stack"),
        (weight_n, "comparator_weights", "unmapped_provisional_equal_stripe" if comparator else "absent_rom",
         "new shared physical weight service required" if comparator else "on_die_rom"),
        (rope_n, "rope_plain", "external_base_unbound", "K port, read-only"),
        (rope_n, "rope_yarn", "external_base_unbound", "K port, read-only"),
    ):
        if count == 0:
            continue
        regions.append(_region(cursor, count, owner, status, service))
        cursor += count
    return regions


def build() -> dict:
    src = {p: (ROOT / p).read_bytes() for p in PATHS}
    check_sources(src)
    tech = json.loads(src[PATHS[-2]])
    budget = json.loads(src[PATHS[-1]])
    stack_bytes = int(tech["hbm"]["hbm3e"]["stack_capacity_bytes"]["value"])
    usable_sectors = int(stack_bytes * float(tech["efficiencies"]["hbm_capacity"]["value"])) // 32
    physical_sectors = stack_bytes // 32
    rope_table_sectors = 1_048_576 * 2  # per stack, each theta
    weight_die_bytes = budget["hbm_comparator"]["weights_B"] / budget["hbm_comparator"]["dies"]
    provisional_weight_per_stack = math.ceil(weight_die_bytes / 4 / 32)
    cases = {}
    for context in (200_000, 1_048_576):
        rows_die = math.ceil(context / 4)
        local_rows = math.ceil(rows_die / 4)
        # Current sharded address module reserves 2,176 sectors for every
        # 1,024 local keys, including the final partial superblock.
        index_sectors = math.ceil(local_rows / 1024) * 2176
        last_key_exclusive = ((local_rows - 1) // 1024) * 2176 + 128 + 2 * ((local_rows - 1) % 1024) + 2
        ckv_sectors = local_rows * 9
        scenarios = {}
        for mode in ("rom", "hbm_comparator"):
            weight_sectors = provisional_weight_per_stack if mode == "hbm_comparator" else 0
            stacks = {}
            for stack in range(4):
                regions = _stack_regions(index_sectors, ckv_sectors, 128*17 if stack == 0 else 0,
                                         weight_sectors, rope_table_sectors,
                                         comparator=mode == "hbm_comparator")
                end = regions[-1]["end_sector_exclusive"]
                stacks[str(stack)] = {"regions": regions, "reserved_end_sector": end,
                                      "within_usable_stack": end <= usable_sectors,
                                      "within_physical_stack": end <= physical_sectors}
            scenarios[mode] = {"stacks": stacks, "placement_status": "candidate_unapproved_unwired"}
        cases[str(context)] = {
            "source_rows_per_die": rows_die,
            "source_rows_per_die_stack": local_rows,
            "index_superblock_reserved_sectors_per_stack": index_sectors,
            "index_highest_addressed_end_sector_from_region_base": last_key_exclusive,
            "selected_ckv_sectors_per_stack": ckv_sectors,
            "scenarios": scenarios,
            "placement_status": "candidate_unapproved_unwired",
        }
    return {
        "schema": "v41_single_user_region_candidate_v1",
        "source_sha256": {p: hashlib.sha256(src[p]).hexdigest() for p in PATHS},
        "units": {"address": "32-byte sector", "region_end": "exclusive", "stack_capacity": "physical HBM3E"},
        "physical_sectors_per_stack": physical_sectors,
        "usable_sectors_per_stack": usable_sectors,
        "comparator_weight_bytes_per_die_model": weight_die_bytes,
        "comparator_weight_sectors_per_stack_if_even_stripe": provisional_weight_per_stack,
        "contexts": cases,
        "placement_status": "candidate_for_root_review_not_configured_in_die",
        "service_gates": {
            "rom_weight_selection": "blocked: die does not forward W_HBM and tile defaults to W_HBM=1; ROM tile service must be integrated and die mode selectable",
            "index": "blocked: opt-in IDX_SHARDED is not set by die; writer/reader paired image and PC timing needed",
            "window": "partial: packed 17-sector client connected only on stack 0, prefetch/attention path incomplete",
            "selected_ckv": "blocked: standalone DMA source exists, die C mux client tied off; remote die row delivery absent",
            "rope": "partial: cache/mux connected; caller-supplied bases/reserved_end do not prove CKV/weight floor",
            "hbm_comparator_weights": "blocked: tile qstream HAW24 and die wq_addr[23:0] truncate AW30; only W_STACK has a separate W model, no four-stack physical service or shared arbitration",
            "simultaneous_traffic": "blocked: index B vs KV/RoPE K arbiter exists, but C client absent and W weight model is physically separate; exact multi-client backpressure/timing unmeasured",
        },
        "acceptance_checks": [
            "Bind one selected context and mode to K_MEM, index/window/CKV/weight/RoPE base+count registers; assert all [start,end) disjoint and end <= 0.9 physical sectors.",
            "Set IDX_SHARDED and replay writer+reader at first/last key, partial 200K superblock and four-stack PC hash; require exact keys and no out-of-region requests.",
            "Connect selected CKV DMA and remote-row path; test first/last source on each die and stack, nine sectors/row, window-vs-CKV isolation and kv_ok after full row.",
            "Load both full RoPE tables, bind reserved_end to actual state+weight end per stack, and test first/last position with index/window/CKV traffic active.",
            "Replace W_HBM's 24-bit, one-stack separate model with a source-pinned checkpoint weight image in the shared physical map; test an address above 2^24 sectors and concurrency with K and B clients.",
            "Run two-client and all-client sustained traces through one controller, account PC occupancy/refresh/queue stalls, then compare matched ROM/HBM token cycles.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-service", action="store_true")
    args = parser.parse_args()
    record = build()
    print(json.dumps(record, indent=2, sort_keys=True))
    if args.require_service and record["placement_status"] != "implemented_and_exact":
        raise SystemExit(2)
