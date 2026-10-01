from tools.w17_crom_slot_deadlines import build
from decimal import Decimal

def test_current_slot_rejects_all_credit_choices():
    r=build()
    assert len(r['proposed61macro_coordinates'])==61
    for c in r['candidates']:
        assert Decimal(c['exclusive_area_deficit_mm2'])>0
        assert c['placement_verdict']=='FAIL_EXISTING_SU_PLUS_CROM_EXCEEDS_SLOT'
    assert not r['hardware_admission']

def test_pc491_finite_gate_and_no_free_deadline():
    r=build()
    for c in r['candidates']:
        assert len(c['commands'])==491
        assert sum(x['coefficient_reads'] for x in c['commands'])==549760
        for x in c['commands']:
            assert x['cache_visible_and_credit_return_tick']-x['service_release_tick']>=3*x['selected_output_floor_fast_cycles']
            assert x['actual_program_absolute_release_tick'] is None
            if x['source_gamma']:assert x['selected_output_floor_fast_cycles']>=320
