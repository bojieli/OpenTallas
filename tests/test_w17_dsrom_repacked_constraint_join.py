import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w17_dsrom_repacked_constraint_join as J

def test_new_state_does_not_inherit_old_power_or_isolation():
    r=J.build()
    assert r['power_currency']['new_FF_bits_above_historical_200e']==195264
    assert not r['power_currency']['old_200e_power_applies_to_current_repack']
    assert not r['current_event_inventory']['actual_tree_data_isolation']
    assert r['geometry']['retained_channels']==16
    assert not r['physical_admission']

def test_fragment_ready_cannot_alias_stored_word_ack():
    r=J.build();s=r['serialized_candidate_requirements']
    assert s['total_proposed_tracks']==s['request_bits']+s['response_data_bits']+s['ready_control_tracks']+s['separate_stored_word_ACK_tracks']==310
    assert s['separate_stored_word_ACK_tracks']==1
    assert r['preserved_fullwidth_route_failure']['shortfall']==20
    assert not s['compiled_fragment_exactness_and_finite_calendar_bound']
