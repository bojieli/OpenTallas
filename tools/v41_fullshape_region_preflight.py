"""Source-pinned static V4.1 full-shape HBM region feasibility check.

The compact scenarios below are *necessary* capacity bounds, not an RTL
layout or a throughput claim. Unknown CKV and weight-HBM mapping stays blocked.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "rtl/chip/ot_chip_v41x_die.sv",
    "rtl/chip/ot_chip_v41x_tile.sv",
    "rtl/chip/ot_chip_v41x_window_kv_prefetch.sv",
    "rtl/chip/ot_chip_v41x_rope_region_guard.sv",
    "rtl/chip/ot_chip_v41x_rope_hbm_cache.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_pool_kwr.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_pool_adapt.sv",
    "rtl/chip/ot_chip_v41x_hbm3e_phy.sv",
    "rtl/test/tb_chip_v41x_die_smoke.sv",
    "configs/hardware/technology.json",
    "results/arch/arch_budget_v41.json",
)


def build() -> dict:
    src = {p: (ROOT / p).read_bytes() for p in SOURCES}
    die, tile, win, guard, rope, kwr, idx, phy, smoke_tb = (src[p].decode() for p in SOURCES[:9])
    tech = json.loads(src[SOURCES[9]])
    budget = json.loads(src[SOURCES[10]])
    assert "ot_chip_v41x_die #(.RANK(0))" in smoke_tb
    die_instantiations = []
    for path in (ROOT / "rtl").rglob("*.sv"):
        if path.name == "ot_chip_v41x_die.sv":
            continue
        body = path.read_text()
        for match in re.finditer(r"ot_chip_v41x_die\s*#\s*\(", body):
            params = body[match.end():match.end() + 400]
            die_instantiations.append({"path": str(path.relative_to(ROOT)),
                                       "full_shape_parameter": bool(re.search(r"\.FULL_SHAPE\s*\(\s*1\s*\)", params))})
    assert die_instantiations and all(not x["full_shape_parameter"] for x in die_instantiations)
    assert "parameter integer IDX_SHARDED = 0" in tile
    assert ".IDX_SHARDED(IDX_SHARDED)" in tile
    assert "ot_chip_v41x_tile #(.FULL_SHAPE(FULL_SHAPE), .PIKH_HAW(K_HAW)" in die
    assert "assign w_stack_mask=SHARDED ? (4'b0001 << row[5:4]) : 4'b1111" in kwr
    assert "cmd_base_sec(HAW'((ik_off>>7)*17))" in idx
    assert "localparam integer KEY_SECTORS = KEY_USERS * IKH_SLICE" in die
    assert "localparam integer WIN_SECTORS = KV_USERS * 128 * 17" in die
    assert "parameter integer IKH_SLICE = 1 << 18" in die
    assert ".c_v(4'b0)" in die and "assign kv_ok = 1'b0" in die
    assert re.search(r"parameter integer W_MEM\s*=\s*1\s*<<\s*20", die)
    assert re.search(r"parameter integer K_MEM\s*=\s*1\s*<<\s*19", die)
    assert "MAX_POS=1048576" in guard and "TABLE_SECTORS=64'(MAX_POS)*2" in guard
    assert "USABLE_SECTORS=64'(K_MEM)*9/10" in guard
    assert "PITCH = 17" in win and "WIN_STACK = 0" in win
    assert "ot_hdc_hbm_model #(.NPC(NPC_W), .AW(24)" in phy
    assert "reserved_end" in die and "rope_region_ok=region_valid && !(|floor_bad)" in die

    stack_b = int(tech["hbm"]["hbm3e"]["stack_capacity_bytes"]["value"])
    reserve = float(tech["efficiencies"]["hbm_capacity"]["value"])
    usable_sec = int(stack_b * reserve) // 32
    rope_sec = 2 * 1_048_576 * 2  # two thetas, two sectors/position/stack
    window_sec = 128 * 17  # physically on WIN_STACK only
    cases = {}
    for ctx in (200_000, 1_048_576):
        rows_die = math.ceil(ctx / 4)
        # Compact sharded key format: 16 keys per group per stack; 64 code
        # bytes and 4 shared scale bytes per key, 34 sectors/16-key group.
        key_sharded_sec = math.ceil(rows_die / 64) * 34
        key_replicated_sec = math.ceil(rows_die / 64) * 136
        # FP4 CKV is 288 B = 9 sectors/row, hypothetically striped over four
        # stacks. There is no connected full-shape CKV region/client yet.
        ckv_ideal_sec = math.ceil(rows_die / 4) * 9
        compact_per_user_winstack = key_sharded_sec + ckv_ideal_sec + window_sec
        compact_bound = (usable_sec - rope_sec) // compact_per_user_winstack
        model_users = budget["capacity"][str(ctx)]["rom_users"]
        cases[str(ctx)] = {
            "rows_per_die_per_user": rows_die,
            "model_rom_users": model_users,
            "index_key_sectors_per_user_per_stack": {
                "current_replicated": key_replicated_sec,
                "opt_in_sharded_compact": key_sharded_sec,
                "die_default_reserved_slice": 1 << 18,
            },
            "ideal_ckv_sectors_per_user_per_stack": ckv_ideal_sec,
            "window_sectors_per_user_on_win_stack": window_sec,
            "both_rope_tables_sectors_per_stack": rope_sec,
            "usable_sectors_per_stack": usable_sec,
            "optimistic_compact_sharded_users_bound": compact_bound,
            "model_users_fit_optimistic_layout":
                rope_sec + model_users * compact_per_user_winstack <= usable_sec,
            "optimistic_compact_sharded_sectors_at_model_users":
                rope_sec + model_users * compact_per_user_winstack,
            "minimum_key_slice_sectors_for_current_replication": key_replicated_sec,
            "current_key_slice_fits_one_user": key_replicated_sec <= (1 << 18),
        }
    return {
        "schema": "v41_fullshape_region_preflight_v1",
        "source_sha256": {p: hashlib.sha256(src[p]).hexdigest() for p in SOURCES},
        "scope": "Static necessary bounds for one ratio-1 layer die, four HBM stacks; no full-shape die/token/throughput verdict",
        "full_shape_region_gate": "blocked",
        "actual_instantiation": {
            "full_shape_die_instantiated_by_shipped_rtl_or_tb": False,
            "observed_die_instantiations": die_instantiations,
            "die_tile_idx_sharded": False,
            "die_window_stack": 0,
            "die_default_key_users": 1,
            "die_default_ikh_slice_sectors": 1 << 18,
            "die_default_k_mem_sectors": 1 << 19,
            "selected_ckv_mux_client_connected": False,
            "full_shape_kv_ok_producible": False,
            "full_shape_weight_hbm_uses_separate_dense_model": True,
            "rope_reserved_end_supplied_externally": True,
            "rope_guard_proves_ckv_and_weight_region_floor": False,
        },
        "contexts": cases,
        "blocked": [
            "No source-pinned full-shape die instantiation selects physical KEY_USERS, IKH_SLICE, K_MEM or IDX_SHARDED.",
            "Selected compressed-KV client is tied off; its HBM base, stride, per-user placement and reserved_end are unspecified.",
            "RoPE guard checks caller-provided reserved_end and known key/window floor only; CKV and comparator weight floors are unproven.",
            "QE weight HBM uses a separate W-port dense array on W_STACK; combined physical stack capacity/overlap is unproven.",
            "A compile-time 1M IKH_SLICE reserves that slice at 200K too unless a runtime compact user stride or remap is implemented.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-ready", action="store_true",
                        help="exit nonzero while the full-shape physical region gate is blocked")
    args = parser.parse_args()
    record = build()
    print(json.dumps(record, indent=2, sort_keys=True))
    if args.require_ready and record["full_shape_region_gate"] != "ready":
        raise SystemExit(2)
