import pytest
import lower_bk as B
from idxnet_tx_contract import score_store_contract as contract


def check(ranges, **kw):
    return contract(ranges, depth=8192, capture_end=100, lookup_begin=110,
                    lookup_end=200, next_capture_begin=220, **kw)


def test_actual_nonroot_shard_topology_fits_current_native_store():
    # Actual contiguous subtree construction, not a heap-tree assumption.
    for q4, kd in ((131072,3),(262144,6)):
        tree=B.shard_tree(kd)
        for rank in range(4):
            for d in range(1,kd):
                ranges=[]
                for child in B.subtree(tree,d):
                    lo,n=B.shard_range(q4,kd,child)
                    ranges.append((rank*q4+lo,rank*q4+lo+n))
                assert check(ranges)['allocation_changed'] is False


def test_global_bases_wrap_but_preserve_identity_when_domain_fits():
    check([(131073,262144)])


def test_actual_poison_probe_alias_is_refused():
    with pytest.raises(ValueError,match='positions 131072 and 0'):
        check([(0,16),(131072,131088)])


def test_new_l20_rank_root_role_cannot_reuse_nonroot_range_contract():
    with pytest.raises(ValueError,match='native TX alias'):
        check([(0,262144)])


def test_unknown_pair_producers_and_unbooked_or_overlapping_lifetimes_refused():
    with pytest.raises(ValueError,match='explicit reachable'):
        check([])
    for end in (None,109,220):
        with pytest.raises(ValueError):
            contract([(0,16)],depth=8192,capture_end=100,lookup_begin=110,
                     lookup_end=end,next_capture_begin=220)
