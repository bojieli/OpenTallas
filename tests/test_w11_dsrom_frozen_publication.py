import copy
import pytest
import w11_dsrom_frozen_publication as F

def test_all_rank_partial_relocation_and_missing_slots():
    r = F.build()
    assert len(r['ranks']) == 4
    for rank in r['ranks']:
        assert len(rank['changed_pcs']) == 1
        l1, l14 = rank['bindings']
        assert l1['logical_span'] == [508800,529280] and not l1['source_valid']
        assert l1['diagnostic_encoded_base'] == l1['original_encoded_base']
        assert l14['diagnostic_encoded_base'] == 529280 and l14['source_valid']
        assert all(b['published_base'] is None for b in rank['bindings'])
        assert not rank['runnable']
    assert not r['image_admission'] and not r['hardware_admission']

def test_incomplete_publication_rejected():
    layout, _ = F.authority()
    with pytest.raises(ValueError, match='L1 slots'):
        F.require_publication(layout)

@pytest.mark.parametrize('mutation', ['valid', 'complete', 'base', 'empty', 'service'])
def test_mutable_layout_cannot_authorize_publication(mutation):
    layout, _ = F.authority()
    x = copy.deepcopy(layout)
    if mutation == 'valid': x['ranks'][0]['bindings'][0]['source_valid'] = True
    if mutation == 'complete': x['ranks'][0]['complete'] = True
    if mutation == 'base': x['ranks'][0]['bindings'][1]['proposed_base'] += 1
    if mutation == 'empty': x['ranks'] = []
    if mutation == 'service': x['finite_service']['actual_routes_capture_mux_CDC_deadlines_and_power_bound'] = True
    with pytest.raises(ValueError, match='immutable'):
        F.build(x)
    with pytest.raises(ValueError, match='immutable'):
        F.require_publication(x)
