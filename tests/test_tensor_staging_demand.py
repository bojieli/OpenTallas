"""Capacity math must not confuse resident weight reuse with stream traffic."""

import pytest
from tools.audit_tensor_staging_demand import demand


def test_qwen_projection_exceeds_even_a_whole_staging_window():
    row = demand(1, 4096, 4096)
    assert row["unique_weight_bytes"] == 32 * 1024 * 1024
    assert row["weight_stream_words"] == 2097152
    assert row["minimum_512_word_bank_fills_with_perfect_row_reuse"] == 4096
    assert not row["one_output_group_depth_fits_whole_window"]
    assert not row["activation_row_fits_2k_window"]


def test_prefill_stream_repeats_do_not_imply_external_refetch():
    decode, prefill = demand(1, 4096, 4096), demand(8, 4096, 4096)
    assert decode["unique_weight_bytes"] == prefill["unique_weight_bytes"]
    assert prefill["weight_stream_read_bytes"] == 8 * decode["weight_stream_read_bytes"]
    assert (
        prefill["minimum_512_word_bank_fills_with_perfect_row_reuse"]
        == decode["minimum_512_word_bank_fills_with_perfect_row_reuse"]
    )


def test_bank_and_window_boundary():
    assert demand(1, 8, 512)["one_output_group_depth_fits_bank"]
    assert not demand(1, 8, 513)["one_output_group_depth_fits_bank"]
    assert demand(1, 8, 1024)["fits_current_preloaded_weight_window"]
    assert not demand(1, 8, 1025)["fits_current_preloaded_weight_window"]


@pytest.mark.parametrize("shape", [(0, 8, 1), (1, 7, 1), (1, 8, 0)])
def test_invalid_geometry_is_not_rounded_to_an_implementable_case(shape):
    with pytest.raises(ValueError):
        demand(*shape)
