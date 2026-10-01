import pytest
from tools.w17_crom_hybrid_topology import build,release_slot

def test_requires_owning_capture_not_readiness():
    for ready in (False,None,1):
        with pytest.raises(ValueError):release_slot(0,ready)
    assert release_slot(0,True)==117

def test_actual_topology_and_exclusive_slot_calendar():
    r=build()
    assert len(r['topology']['dense_cache_owners'])==160
    assert r['topology']['field_stage40']['dense_CROM_cache_words']==0
    assert r['topology']['head']['actual_norm_home_to_eight_heads_mapping'] is None
    assert r['area_bridge']['existing164_hub_reservation']=='6330.564'
    assert r['hybrid']['maximum_other_words']==2928
    for candidate in r['product_calendars']:
        for command in candidate['commands']:
            assert len(command['events'])==20
            prior=0
            for e in command['events']:
                assert e['start_tick']==prior
                assert e['fill_and_packet_credit_complete_tick']<=e['emit_tick']<e['read_capture_tick']<e['candidate_owning_slot_reverse_credit_tick']
                prior=e['candidate_owning_slot_reverse_credit_tick']
    assert not r['hardware_admission'] and r['full_token_cycles'] is None


def test_wrong_runtime_helper_fails_before_calendar(tmp_path):
    import types
    from tools.w17_crom_hybrid_topology import verify_imported_helper,HELPER_SHA256
    wrong=tmp_path/'old_prefetch.py'
    wrong.write_text('def credit_calendar(): return 7008\n')
    with pytest.raises(ValueError,match='runtime helper source mismatch'):
        verify_imported_helper(types.SimpleNamespace(__file__=str(wrong)))
    import hashlib
    assert hashlib.sha256(verify_imported_helper()).hexdigest()==HELPER_SHA256
