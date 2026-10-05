"""Hazard compression must have no false negatives, including its overflow tail."""
from random import Random
from types import SimpleNamespace

import pytest

from runtime.abi3.constants import NO_ID
from runtime.abi3.dependence import AccessRange as R, DependenceTable, compress_ranges, operator_whole_object_accesses
from runtime.abi3.descriptors import ExtendedDescriptorType as T


def test_fifth_mutable_object_is_protected_until_completion():
    table = DependenceTable()
    reads = [R(i, 0, 64, False) for i in range(4)]
    output = R(99, 0, 64, True)
    assert table.reserve(0, [*reads, output])
    assert table.live[0].wildcard
    assert not table.reserve(1, [R(99, 0, 64, False)])
    # Wildcard intentionally blocks unrelated work as well.
    assert not table.reserve(1, [R(500, 0, 64, False)])
    table.complete(0)
    assert table.reserve(1, [R(99, 0, 64, False)])


def test_overflow_candidate_checks_every_range_before_reservation():
    table = DependenceTable()
    assert table.reserve(0, [R(9, 0, 64, True)])
    assert not table.reserve(1, [*(R(i, 0, 64, False) for i in range(4)), R(9, 0, 64, False)])
    assert 1 not in table.live


def test_same_object_union_preserves_write_and_half_open_boundaries():
    f = compress_ranges([R(1, 0, 32, False), R(1, 64, 96, True)])
    assert len(f.ranges) == 1 and not f.wildcard
    assert f.conflicts([R(1, 0, 16, False)])
    assert not f.conflicts([R(1, 96, 128, True)])
    assert not f.conflicts([R(1, 16, 16, True)])
    assert not compress_ranges([R(1, 0, 32, False)]).conflicts([R(1, 0, 32, False)])


def test_seeded_compression_never_misses_an_exact_dependency():
    random = Random(20260905)
    for _ in range(2000):
        source = [R(random.randrange(12), start := random.randrange(64), start + random.randrange(32), bool(random.randrange(2)))
                  for _ in range(random.randrange(1, 15))]
        queries = [R(random.randrange(12), start := random.randrange(64), start + random.randrange(32), bool(random.randrange(2)))
                   for _ in range(6)]
        # Independent brute-force byte-set oracle, rather than calling conflicts().
        hazard = any(a.object_id == b.object_id and (a.write or b.write) and
                     bool(set(range(a.lo, a.hi)) & set(range(b.lo, b.hi))) for a in source for b in queries)
        if hazard:
            assert compress_ranges(source).conflicts(queries)


def test_scale_objects_and_all_six_views_are_collected():
    class Table(dict):
        def get(self, identifier, expected_type):
            result = self[identifier]
            assert result.descriptor_type == expected_type
            return result
    table = Table()
    payload = {}
    for i, role in enumerate([*(f"input_view_{i}" for i in range(4)), "output_view_0", "output_view_1"]):
        table[i] = SimpleNamespace(descriptor_type=T.MEMORY_OBJECT, descriptor_id=i, payload={"size_bytes": 256})
        table[20+i] = SimpleNamespace(descriptor_type=T.TENSOR_VIEW, primary_object_id=i,
                                      payload={"scale_object_id": 90 if i in (0, 4) else NO_ID})
        payload[role] = 20+i
    table[90] = SimpleNamespace(descriptor_type=T.MEMORY_OBJECT, descriptor_id=90, payload={"size_bytes": 8})
    op = SimpleNamespace(descriptor_type=T.OPERATOR, payload=payload)
    accesses = operator_whole_object_accesses(SimpleNamespace(table=table), op)
    assert {r.object_id for r in accesses} == {0, 1, 2, 3, 4, 5, 90}
    assert {r.object_id for r in accesses if r.write} == {4, 5, 90}
    assert compress_ranges(accesses).wildcard


def test_memory_only_collector_refuses_other_descriptor_families():
    with pytest.raises(ValueError, match="only OPERATOR"):
        operator_whole_object_accesses(None, SimpleNamespace(descriptor_type=T.COMMUNICATION))


@pytest.mark.parametrize("args", [(-1, 0, 1, False), (65536, 0, 1, False), (0, 9, 8, True), (0, 0, 1 << 40, True)])
def test_invalid_ranges_fail_before_issue(args):
    with pytest.raises(ValueError):
        R(*args)
