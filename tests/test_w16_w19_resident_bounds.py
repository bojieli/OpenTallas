import copy
import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import w16_w19_resident_bounds as B


def test_actual_inventory_bounds():
    inv = B.read(B.INVENTORY)
    result = B.inventory_bounds(inv)
    assert result['selected_tensors'] == 542
    assert sum(result['stored_bytes_by_group'].values()) == 204240953808
    assert result['stored_bytes_by_group']['other_text_objects_unclassified'] == 159094208


@pytest.mark.parametrize('mutation', ['duplicate', 'size', 'shape', 'file_end', 'data_base', 'total', 'overlap'])
def test_inventory_refuses_inconsistent_bounds(mutation):
    inv = copy.deepcopy(B.read(B.INVENTORY))
    item = inv['items'][0]
    if mutation == 'duplicate':
        inv['items'].append(copy.deepcopy(item))
    elif mutation == 'size':
        item['stored_bytes'] -= 1
    elif mutation == 'shape':
        item['shape'][0] = 0
    elif mutation == 'file_end':
        inv['shards'][item['shard']]['bytes'] = 1
    elif mutation == 'data_base':
        item['header_data_base'] += 1
    elif mutation == 'total':
        inv['stored_bytes'] += 1
    else:
        alias = copy.deepcopy(item)
        alias['tensor'] = 'invented_overlap'
        inv['items'].append(alias)
    with pytest.raises(B.Refusal):
        B.inventory_bounds(inv)


def fixture():
    names = ['constants', 'embedding', 'Engram', 'KV', 'index']
    return {n: {'base_bytes': 256 + i * 256, 'bytes': 256} for i, n in enumerate(names)}, {n: 64 for n in names}


def test_local_stack_fixture_and_no_fullfit():
    regions, sizes = fixture()
    assert B.stack_bound(256, regions, sizes, 1536) == 1536
    actual = B.build()
    assert actual['actual_reservations_verdict'] == 'REFUSED'
    assert not actual['full_placement_qualified']
    assert not actual['headline_adoption']
    assert actual['model_composition']['logical_state_bytes'] == 935936000
    assert actual['model_composition']['program_replicated_window_state_bytes'] == 1192755200


@pytest.mark.parametrize('mutation', ['unknown', 'zero', 'missing', 'undersized', 'weight_overlap', 'overlap', 'aperture', 'alignment'])
def test_local_stack_refusal(mutation):
    regions, sizes = fixture()
    weight, aperture = 256, 1536
    if mutation == 'unknown':
        sizes['KV'] = None
    elif mutation == 'zero':
        sizes['KV'] = 0
    elif mutation == 'missing':
        regions['KV'] = None
    elif mutation == 'undersized':
        sizes['KV'] = 257
    elif mutation == 'weight_overlap':
        weight = 512
    elif mutation == 'overlap':
        regions['embedding']['base_bytes'] = 256
    elif mutation == 'aperture':
        aperture -= 1
    else:
        regions['KV']['bytes'] = 65
    with pytest.raises(B.Refusal):
        B.stack_bound(weight, regions, sizes, aperture)


def test_shard_tail_exact():
    for n in (1, 7, 8, 9, 767, 768, 769, 1048576):
        counts = B.rows_by_rank(n)
        assert sum(counts) == n
        if n < 1000:
            assert counts == [sum((i // 8) % 96 == r for i in range(n)) for r in range(96)]


def test_receipt_roundtrip_and_drift():
    result = json.loads(json.dumps(B.build()))
    B.check(result)
    result['pins'][B.INVENTORY] = '0' * 64
    with pytest.raises(B.Refusal, match='pin drift'):
        B.check(result)
