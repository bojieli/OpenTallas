from tools.v41_hbm_region_preflight import build


def test_replicated_keys_reduce_capacity_and_user_width_is_insufficient():
    rec = build()
    assert rec["capacity"]["users_model_striped_keys"] == 866
    assert rec["capacity"]["users_current_replicated_keys"] < 866
    assert not rec["capacity"]["model_users_fit_current_layout"]
    assert rec["per_stack_per_user_bytes"]["key_replicated"] == 4 * rec["per_stack_per_user_bytes"]["key_striped"]
    assert rec["widths"]["user_id_bits_for_current_layout_users"] > rec["widths"]["current_controller_user_id_bits"]
    assert rec["capacity"]["max_replicated_users_with_28_bit_key_window"] < rec["capacity"]["users_current_replicated_keys"]
    assert not rec["isolation"]["multiuser_key_address_isolation"]
    assert rec["region_arithmetic"]["unpacked_example_exceeds_32_bit"]
    assert rec["sharding"]["writer_opt_in_available"]
    assert rec["sharding"]["read_address_mapper_available"]
    assert not rec["sharding"]["read_scheduler_integrated"]
    assert not rec["sharding"]["multiuser_slice_integrated"]
    assert rec["capacity"]["key_sectors_per_user_per_stack_striped"] == 139264
    assert rec["capacity"]["max_striped_users_with_28_bit_key_window"] >= 866
