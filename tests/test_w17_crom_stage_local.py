import pytest
from tools.w17_crom_stage_local import build

@pytest.fixture(scope='module')
def record():return build()

def test_actual_max_regular_capacity_and_catalog(record):
    assert record['SS_route_basis']['stages_each_direction']==17
    assert record['SS_route_basis']['reach_um']==504
    assert not record['SS_route_basis']['historical11_qualified']
    e=record['regular_element']
    assert e['maximum_stage_words']==33648 and e['max_stage_ids']==[14]
    assert e['storage_minimum_banks']==3 and e['readonly_banks_per_home']==6 and e['capacity_words_per_home']==73728
    assert e['regular_request_catalog_banks']==1 and e['regular_fill_catalog_banks']==1
    assert max(s['request_words'] for s in record['stages'])==1879
    assert max(s['fill_words'] for s in record['stages'])==3794
    assert all(s['unique_words']<=36864 for s in record['stages'])

def test_all_PC_routes_and_finite_service(record):
    commands=[c for s in record['stages'] for c in s['commands']]
    assert len(commands)==491 and len({c['PC'] for c in commands})==491
    assert sum(c['coefficient_reads'] for c in commands)==549760
    assert record['exact_address_route']['fill_destination_checks']==549760
    assert record['exact_address_route']['model_request_and_fill_catalog_bytes_roundtripped']
    for c in commands:
        for d in c['finite_services']:
            assert d['finite_fill_and_reverse_credit_ticks']>=c['selected16port_floor_fast_cycles']*3
            assert d['actual_absolute_PC_release'] is None

def test_source_invalidity_and_no_physical_admission(record):
    for rank in record['rank_values']:
        homes=rank['homes']
        assert len(homes)==41
        assert next(h for h in homes if h['layer']==1)['source_invalid_words']==20480
        assert all(h['source_invalid_words']==0 for h in homes if h['layer']!=1)
        assert next(h for h in homes if h['layer']==1)['complete_image_SHA256'] is None
        assert all(len(h['physical_bank_payload_SHA256'])==6 for h in homes)
    assert not record['hardware_admission'] and not record['fit']['actual_SU_nonoverlap_and_placed_catalog']
