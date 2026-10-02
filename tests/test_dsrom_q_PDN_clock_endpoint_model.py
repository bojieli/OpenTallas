import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'tools'))
import dsrom_q_PDN_clock_endpoint_model as M

@pytest.fixture(scope='module')
def model():return M.build()

def test_actual_extension_and_via_shapes(model):
    q=model['q']
    assert q['outline_DBU']==[510840,151200]
    assert q['via_option']['landing_spacing_envelope_DBU']==[-47,-47,47,47]
    assert q['default_via_shapes']['VIA45']['M4']==[-23,-12,23,12]
    assert len(q['PDN_template'])>1065
    assert all(p['rect'][3]<=151200 and p['rect'][2]<=510840 for p in q['PDN_template'])
    assert [p['growth_strip_crossings'] for p in q['upper_PDN_connections']]==[758,192]

def test_growth_bound_does_not_hide_old_row_deficit(model):
    q=model['q']
    assert q['new_strip_policy_remaining_for_hold_um2']==pytest.approx(218.18159995471856)
    assert q['full_frame_row_blocking_policy_remaining_um2']==pytest.approx(-2135.2550400452815)
    assert q['via_exclusion']['metal_is_not_automatically_cell_blockage']
    assert q['full_frame_policy_nonfit_is_not_architectural_impossibility']

def test_eight_distinct_source_cuts_inside_strip(model):
    q=model['q'];cuts=q['branch_cuts'];assert len({c['net'] for c in cuts})==8
    for c in cuts:
        assert M.area(M.overlap(c['rect'],q['growth_strip_DBU']))==M.area(c['rect'])
    for i,a in enumerate(cuts):
        for b in cuts[i+1:]:assert not M.area(M.overlap(a['rect'],b['rect']))
    assert sum(c['BUF4_floor'] for c in cuts)==80 # root4 included in predecessor84
    assert len(q['macro_clock_reach'])==4
    assert all(c['actual_macro_clock_pin']['pin']=='clk' for c in q['macro_clock_reach'])

def test_selector_corridor_and_clock_reset_counted_once(model):
    assert model['selector']['cuts']['horizontal_escape']['remaining_for_unpriced_pin_escape']==30
    assert model['selector']['cuts']['vertical_escape']['remaining_for_unpriced_pin_escape']==40
    assert model['area']['screen_with_corridor_mm2']==pytest.approx(753.0303252141658)
    assert model['area']['all_compiled2048_sites_and8192_macros_unchanged']

def test_absolute_edges_and_narrow_hold_kept(model):
    io=model['parent_IO']
    assert (io['setup_uncertainty_ps'],io['hold_uncertainty_ps'])==(60,25)
    assert io['observed_source_edges']['adapter_retire']==422
    assert 'actual launch edge' in io['equations']['macro_capture']
    assert io['actual_driver_arrival_slew_and_output_load'] is None
    assert not model['admission']['installed_CTS_required_before_build']
    assert not model['admission']['PnR_admitted']
    assert model['latency']['new_clock_cut_pipeline_cycles']==0
    assert model['latency']['endpoint_transport_delta_cycles'] is None

def test_default_via_missing_rejected():
    with pytest.raises(ValueError):M.via_rects('','VIA45')

def test_union_boundary_and_duplicate():
    assert M.union_area([[0,0,10,10],[5,0,15,10],[0,0,10,10]])==150
    assert M.area(M.overlap([0,0,10,10],[10,0,20,10]))==0
