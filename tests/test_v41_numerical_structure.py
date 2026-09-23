"""Independent native blocks retain the final ordered dependency."""
import pytest
from tools.audit_v41_numerical_structure import bound


def test_native_blocks_shorten_but_do_not_remove_k_dependency():
    assert bound(5120) == 192
    assert bound(2304) == 104
    assert bound(5120) > bound(2304)
    assert 40 * (bound(5120) + bound(2304)) == 11840


def test_partial_merge_latency_is_not_hidden_by_parallel_blocks():
    assert bound(5120, product_latency=1, merge_latency=3) == 512
    assert bound(5120, product_latency=3, merge_latency=1) == 256


def test_partial_blocks_require_explicit_tail_policy():
    with pytest.raises(ValueError):
        bound(5130)
