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
    "rtl/hdc/v41x/ot_hdc_v41x_idx_shard_addr.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_shard_reader.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_pool_hbm_bridge.sv",
    "rtl/chip/ot_chip_v41x_die.sv",
    "rtl/rom/ot_rom_pkg_ctrl_x.sv",
)


def build() -> dict:
    source_text = {p: (ROOT / p).read_text() for p in SOURCES}
    writer = source_text[SOURCES[2]]
    scanner = source_text[SOURCES[3]]
    bridge = source_text[SOURCES[6]]
    budget = source_text[SOURCES[0]]
    controller = source_text[SOURCES[8]]
    die = source_text[SOURCES[7]]
    assert re.search(r"assign\s+w_stack_mask\s*=\s*SHARDED\s*\?.*:\s*4'b1111", writer)
    assert "parameter integer AW=24, NW=16, NL=8, HAW=28, SHARDED=0" in writer
    assert "parameter integer SHARDED=0" in scanner
    assert "ot_hdc_v41x_idx_shard_reader" in scanner
    assert re.search(r"for\s*\(s=0;s<4;s=s\+1\)", bridge)
    assert "(rows * CKV_ROW_B + rows * IDX_KEY_B) / 4" in budget
    assert "IDX_KEY_B = 68" in budget and "CKV_ROW_B = 288" in budget
    assert "b0=((rbase>>4)-cfg_ik_base)/128*17" in writer
    assert "ik_off=wbase-cfg_ik_base" in scanner
    assert "i_user_base_sec" in writer and "i_user_base_sec" in scanner
    assert "physical_csec" in writer and "key_base_sec" in scanner
    # The die still ties the tile's new per-user key base low.  This preflight
    # must not promote the standalone two-user gate to a full die claim.
    assert ".idx_user_base_sec('0)" in die
    assert re.search(r"HDR_USER\s*=\s*32,\s*HDR_POS\s*=\s*40,\s*HDR_IDX\s*=\s*HDR_POS\s*\+\s*NW", controller)
    assert "HDR_USER_HI = HDR_ADDR + 16" in controller
    assert "parameter integer USER_W       = 8" in controller
    assert "header[HDR_USER_HI +: UHIW]" in controller
    assert "output wire [USER_W-1:0]  core_user" in controller
    # The adopted die sizes the controller user width by FULL_SHAPE.
    assert ".MAXU(MAXU)" in die and ".USER_W(FULL_SHAPE ? 10 : 8)" in die
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
    striped_key_sectors_per_user = key_sectors_per_user // stacks
    assert key_sectors_per_user * 32 == key_stack_replicated
    assert striped_key_sectors_per_user * 32 == key_stack_striped
    user_id_bits_model = (users_model - 1).bit_length()
    user_id_bits_rtl = (users_rtl - 1).bit_length()
    return {
        "schema": "v41_hbm_region_preflight_v1",
        "status": "capacity_mismatch",
        "scope": "1M ratio-1 layer-20 die; packed FP4 CKV striped across four stacks; active default key writer/reader replicated; opt-in sharded writer/reader has exact two-user timed-HBM roundtrip but no controller namespace, full-token or throughput claim",
        "sharding": {"writer_opt_in_available": True, "read_address_mapper_available": True,
                     "correctness_reader_opt_in_available": True,
                     "read_scheduler_integrated": False, "multiuser_slice_integrated": False,
                     "two_user_physical_gate": True, "controller_namespace_integrated": False},
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
                     "key_sectors_per_user_per_stack_striped": striped_key_sectors_per_user,
                     "key_sectors_for_model_users_per_stack_if_striped": users_model * striped_key_sectors_per_user,
                     "max_striped_users_with_28_bit_key_window": (1 << 28) // striped_key_sectors_per_user,
                     "key_sectors_for_model_users_per_stack": users_model * key_sectors_per_user,
                     "key_sectors_for_current_layout_users_per_stack": users_rtl * key_sectors_per_user,
                     "max_replicated_users_with_28_bit_key_window": (1 << 28) // key_sectors_per_user},
        "isolation": {"multiuser_key_address_isolation": False,
                      "standalone_two_user_key_address_isolation": True,
                      "reason": "writer and scanner accept an early physical user base and a standalone two-user gate passes, but the die still ties that base low and no full-token namespace gate exists"},
        "region_arithmetic": {"current_kv_sector_formula_uses_32_bit_integer": True,
                              "unpacked_example_users": users_model,
                              "unpacked_example_kv_aw": 26,
                              "unpacked_example_words": users_model * (1 << 26),
                              "unpacked_example_exceeds_32_bit": users_model * (1 << 26) >= (1 << 32)},
        "widths": {"user_id_bits_for_model_users": user_id_bits_model,
                   "user_id_bits_for_current_layout_users": user_id_bits_rtl,
                   "current_controller_user_id_bits": 8,
                   "historical_reduced_controller_user_id_bits": 8,
                   "controller_full_profile_user_id_bits": 10,
                   "controller_full_profile_header_overlap_bits": 0,
                   "current_index_sector_address_bits": 28,
                   "index_sector_bits_for_current_layout_users": (users_rtl * key_sectors_per_user - 1).bit_length(),
                   "full_mode_header_pos_idx_overlap_bits": 0,
                   "full_mode_header_idx_val_overlap_bits": 0,
                   "full_mode_header_tok_addr_overlap_bits": 0},
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, sort_keys=True))
