from tools.v41_fullshape_region_preflight import build


def test_fullshape_region_preflight_exposes_current_gaps_and_optimistic_capacity():
    rec = build()
    actual = rec["actual_instantiation"]
    assert not actual["die_tile_idx_sharded"]
    assert not actual["selected_ckv_mux_client_connected"]
    assert not actual["rope_guard_proves_ckv_and_weight_region_floor"]
    assert rec["contexts"]["1048576"]["optimistic_compact_sharded_users_bound"] == 859
    assert rec["contexts"]["200000"]["optimistic_compact_sharded_users_bound"] == 4449
    for case in rec["contexts"].values():
        assert not case["model_users_fit_optimistic_layout"]
    assert not rec["contexts"]["1048576"]["current_key_slice_fits_one_user"]
