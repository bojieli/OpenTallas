from tools.w17_crom_stage_admission import build

def test_exact_all12_closed_with_no_margin():
    r=build()
    assert len(r['cases'])==12
    assert {(c['parameter_banks'],c['credits']) for c in r['cases']}=={(b,c) for b in (6,9,16,45) for c in (2,4,128)}
    assert not any(c['hardware_admission'] for c in r['cases'])
    assert r['actual_whole_margin_W'] is None and r['selected_adopted_point'] is None
