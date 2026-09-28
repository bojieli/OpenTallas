"""Check full-shape V4.1 HBM capacity against the RTL key placement.

This is a static preflight, not a full-shape RTL or throughput measurement.
It deliberately prices the key writer's four-stack replication separately
from a hypothetical striped placement so a model/RTL mismatch cannot hide.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "tools/arch_budget_v41.py",
    "configs/hardware/technology.json",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_pool_kwr.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_pool_adapt.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_pool_hbm_bridge.sv",
    "rtl/chip/ot_chip_v41x_die.sv",
    "rtl/rom/ot_rom_pkg_ctrl_x.sv",
)


def build() -> dict:
    source_text = {p: (ROOT / p).read_text() for p in SOURCES}
    writer = source_text[SOURCES[2]]
    scanner = source_text[SOURCES[3]]
    bridge = source_text[SOURCES[4]]
    budget = source_text[SOURCES[0]]
    controller = source_text[SOURCES[6]]
    die = source_text[SOURCES[5]]
    assert re.search(r"assign\s+w_stack_mask\s*=\s*4'b1111", writer)
    assert re.search(r"for\s*\(s=0;s<4;s=s\+1\)", bridge)
    assert "(rows * CKV_ROW_B + rows * IDX_KEY_B) / 4" in budget
    assert "IDX_KEY_B = 68" in budget and "CKV_ROW_B = 288" in budget
    assert "b0=((rbase>>4)-cfg_ik_base)/128*17" in writer
    assert "ik_off=wbase-cfg_ik_base" in scanner
    assert "user_base" not in writer and "user_base" not in scanner
    assert "HDR_USER = 32" in controller and "HDR_POS = 40, HDR_IDX = 56" in controller
    assert "localparam integer KV_SECTORS  = 2 * ((KV_USERS << KV_AW) / 4)" in die

    tech = json.loads(source_text[SOURCES[1]])
    stack_bytes = int(tech["hbm"]["hbm3e"]["stack_capacity_bytes"]["value"])
    reserve = float(tech["efficiencies"]["hbm_capacity"]["value"])
    context = 1 << 20
    tp_dies = 4
    stacks = 4
    rows_die = context // tp_dies
    key_b = 68
    ckv_b = 288
    window_b_die = 128 * 528 * 2

    # Each die owns one quarter of the keys; the existing writer stores that
    # quarter in every stack.  The code/scales split packs exactly 68 B/row:
    # 64 code bytes and 4 scale bytes, shared as a 32-B sector by eight rows.
    key_stack_replicated = rows_die * key_b
    key_stack_striped = key_stack_replicated // stacks
    ckv_stack_striped = rows_die * ckv_b // stacks
    window_stack = window_b_die // stacks
    usable_stack = int(stack_bytes * reserve)
    per_user_model = key_stack_striped + ckv_stack_striped + window_stack
    per_user_rtl = key_stack_replicated + ckv_stack_striped + window_stack
    users_model = usable_stack // per_user_model
    users_rtl = usable_stack // per_user_rtl

    # Keep physical sector counts distinct from bytes.  A 68-B key has no
    # per-row sector padding in the present code+scale planes.  Key user
    # slices are 136 sectors per 64-row group on each replicated stack.
    key_sectors_per_user = (rows_die // 64) * 136
    assert key_sectors_per_user * 32 == key_stack_replicated
    user_id_bits_model = (users_model - 1).bit_length()
    user_id_bits_rtl = (users_rtl - 1).bit_length()
    return {
        "schema": "v41_hbm_region_preflight_v1",
        "status": "capacity_mismatch",
        "scope": "1M ratio-1 layer-20 die; packed FP4 CKV striped across four stacks; current replicated index-key writer; no throughput claim",
        "source_sha256": {p: hashlib.sha256(source_text[p].encode()).hexdigest() for p in SOURCES},
        "inputs": {"context": context, "tp_dies": tp_dies, "stacks_per_die": stacks,
                   "stack_capacity_bytes": stack_bytes, "capacity_efficiency": reserve,
                   "key_bytes_per_row": key_b, "ckv_bytes_per_row": ckv_b,
                   "rows_per_die_per_user": rows_die, "window_bytes_per_die_per_user": window_b_die},
        "per_stack_per_user_bytes": {"model_striped_keys": per_user_model,
                                      "rtl_replicated_keys": per_user_rtl,
                                      "key_striped": key_stack_striped,
                                      "key_replicated": key_stack_replicated,
                                      "ckv_striped": ckv_stack_striped,
                                      "window": window_stack},
        "capacity": {"usable_bytes_per_stack": usable_stack,
                     "users_model_striped_keys": users_model,
                     "users_current_replicated_keys": users_rtl,
                     "model_users_fit_current_layout": users_model * per_user_rtl <= usable_stack,
                     "key_sectors_per_user_per_stack_replicated": key_sectors_per_user,
                     "key_sectors_for_model_users_per_stack": users_model * key_sectors_per_user,
                     "key_sectors_for_current_layout_users_per_stack": users_rtl * key_sectors_per_user,
                     "max_replicated_users_with_28_bit_key_window": (1 << 28) // key_sectors_per_user},
        "isolation": {"multiuser_key_address_isolation": False,
                      "reason": "writer and scanner derive sectors from layer-local bases with no user slice offset"},
        "region_arithmetic": {"current_kv_sector_formula_uses_32_bit_integer": True,
                              "unpacked_example_users": users_model,
                              "unpacked_example_kv_aw": 26,
                              "unpacked_example_words": users_model * (1 << 26),
                              "unpacked_example_exceeds_32_bit": users_model * (1 << 26) >= (1 << 32)},
        "widths": {"user_id_bits_for_model_users": user_id_bits_model,
                   "user_id_bits_for_current_layout_users": user_id_bits_rtl,
                   "current_controller_user_id_bits": 8,
                   "current_index_sector_address_bits": 28,
                   "index_sector_bits_for_current_layout_users": (users_rtl * key_sectors_per_user - 1).bit_length(),
                   "full_mode_header_pos_idx_overlap_bits": 5,
                   "full_mode_header_idx_val_overlap_bits": 5,
                   "full_mode_header_tok_addr_overlap_bits": 1},
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, sort_keys=True))
