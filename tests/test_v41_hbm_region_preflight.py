from tools.v41_hbm_region_preflight import build


def test_replicated_keys_reduce_capacity_and_user_width_is_insufficient():
    rec = build()
    assert rec["capacity"]["users_model_striped_keys"] == 866
    assert rec["capacity"]["users_current_replicated_keys"] < 866
    assert not rec["capacity"]["model_users_fit_current_layout"]
    assert rec["per_stack_per_user_bytes"]["key_replicated"] == 4 * rec["per_stack_per_user_bytes"]["key_striped"]
    assert rec["widths"]["user_id_bits_for_current_layout_users"] > rec["widths"]["current_controller_user_id_bits"]
    assert rec["capacity"]["max_replicated_users_with_28_bit_key_window"] < rec["capacity"]["users_current_replicated_keys"]
