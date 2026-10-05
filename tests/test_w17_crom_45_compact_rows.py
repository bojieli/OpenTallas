import pytest
from tools.w17_crom_45_compact_rows import build

@pytest.fixture(scope='module')
def record():return build()

def test_actual_rowmax_and_port_preservation(record):
    assert record['SS_route_basis']['stages_each_direction']==17
    assert not record['SS_route_basis']['actual1152bit_bus_capacity_and_reach_bound']
    assert record['max_regular_rows_per_bank']==250
    assert len(record['stages'])==41
    assert sum(s['all_address_roundtrip_checks'] for s in record['stages'])==549760
    assert len([c for s in record['stages'] for c in s['commands']])==491
    assert record['nominal_service_ports']['same_bank_conflict_structure_preserved']
    assert record['regular_catalog']['existing4096x274_catalog_macros']==4

def test_no_unavailable_shallow_macro_credit(record):
    choices=record['available_choices']
    assert choices[0]['depth']==4096 and not choices[0]['footprint_saved_by_logical_row_compaction']
    assert choices[1]['coefficient_macros']==135
    assert choices[1]['requires_explicit_model_contract_choice']
    assert choices[1]['actual3macro_bank_capture_route_power_SSFF_unbound']
    assert not record['hardware_admission']
