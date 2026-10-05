from tools.w17_crom_gamma_lifetime import build,can_replace

def test_actual81_lifetimes_no_refill_credit():
    r=build()
    assert len(r['commands'])==81 and sum(c['cold_words'] for c in r['commands'])==414720
    assert r['proposed_base_staging_bits']==r['retained_non_gamma_base_bits']+r['cache_bits_per_home']
    assert not r['hardware_admission'] and r['complete_area_power_or_slot_fit'] is None

def test_no_premature_or_unknown_replacement():
    assert can_replace(True,True,True)
    for x in (False,None,1,'X'):
        assert not can_replace(x,True,True)
        assert not can_replace(True,x,True)
        assert not can_replace(True,True,x)
