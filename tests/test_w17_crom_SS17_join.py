from tools.w17_crom_SS17_join import build
from decimal import Decimal

def test_currentSS17_all12_and_no_old_service_credit():
    r=build()
    assert len(r['cases'])==12 and r['route_stages_each_direction']==17
    for c in r['cases']:
        assert c['FF_by_role']['payload_route']==17*1024
        assert Decimal(c['exclusive_SU_slot_area_deficit_mm2'])>0
        assert not c['hardware_admission']
    assert r['actual_whole_margin_W'] is None and not r['hardware_admission']
    assert r['small_macro_actual_service_calendar'] is None
