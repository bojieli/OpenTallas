import pytest
from tools.audit_v41_attention_placement import partition


def test_grouped_projection_is_block_diagonal_not_full_dense():
    p=partition()
    assert p['groups']*p['o_a_weights_per_group']==8192*4096
    assert p['groups']*p['q_b_weights_per_group']==32768*1280
    assert p['groups']*p['o_b_weights_per_group']==5120*8192


def test_k_partition_returns_partial_vectors_not_only_final_vector():
    p=partition()
    assert p['o_b_fp32_partials_to_central_merge_bytes']==163840
    assert p['o_b_central_merge_fp32_adds']==35840
    assert p['o_rank_bf16_allgather_source_bytes']==16384


def test_only_whole_heads_are_assigned():
    with pytest.raises(ValueError): partition(groups=7)
