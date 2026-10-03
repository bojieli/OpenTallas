import collections
import hashlib
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_channel_release_trim as T


def test_channel_cuts_and_source_census_conservation():
    m=T.record('model-r3.json');b=T.allocation();g=b.g
    assert m['actual_reset_clock_leaf_groups']==7137
    assert m['total_clock_pins']==102352+14274+2
    assert m['total_reset_pins']==56683+14274+2
    assert len({n for q in g['local_release_groups'] for n in q['reset_targets']})==56683
    assert m['cuts']['1:700.0']['clock']==3
    assert m['cuts']['1:700.0']['reset_ACK']==6
    assert m['cuts']['1:796.768']['clock']==2
    assert m['cuts']['1:796.768']['reset_ACK']==7
    assert all(c['clock']<=64 and c['reset_ACK']<=64 for c in m['cuts'].values())


def test_raw_receivers_controlled_endpoints_and_hold_unchanged():
    m=T.record('model-r3.json')
    for c,t in m['timing'].items():
        assert len(t['raw_reset_checks'])==14276
        assert len(t['controlled_reset_checks'])==56683
        assert t['raw_reset_failures']==t['controlled_reset_failures']==0
        assert m['stage_and_ACK_audit'][c]['setup_failures']==m['stage_and_ACK_audit'][c]['hold_failures']==0
        assert m['stage_and_ACK_audit'][c]['minimum_hold_margin_ps']>0
    assert m['source_phase_trim']['SS_setup_uncertainty_ps']==60
    assert m['source_phase_trim']['FF_hold_uncertainty_ps']==25
    assert m['source_phase_trim']['no_raw_sync_FF_exception']


def test_original_phase_failure_and_clock_ACK_blockers_preserved():
    old=T.record('model-r2.json');m=T.record('model-r3.json')
    assert old['timing']['ss']['raw_reset_failures']==924
    assert m['source_phase_trim']['required_stage_trim']==1
    assert m['source_phase_trim']['remaining_stages']==36
    assert m['complete_reserved_cell_area_um2']<125000
    for c,t in m['timing'].items():
        assert max(q['skew_ps'] for q in t['nominal_same_source_clock_scenarios'])>20
        assert m['stage_and_ACK_audit'][c]['ACK_out_of_characterization']>0
    assert not any(m[k] for k in ('source_map_admission','contextual_SSFF','PnR','default_enabled'))
