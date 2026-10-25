"""Do not release a zero-overflow prototype whose actual pin tails violate reach."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from proto_geometry import hop_stats
from proto_sweep import classify


def test_pin_window_tail_not_bundle_center(tmp_path):
    (tmp_path/'io.tcl').write_text('place_pin -pin_name {ft0_i[0]} -layer M6 -location {0 0}\nplace_pin -pin_name {ft0_o[0]} -layer M6 -location {800 100}\n')
    (tmp_path/'probe.tcl').write_text('place_inst -name st_ft0_0_0 -location {4 0}\nplace_inst -name st_ft0_0_1 -location {400 0}\n')
    g = hop_stats(tmp_path)
    assert g['over_reach'] == {'ft0': 500.0}
    r = {'exit':'EXIT 0', 'done':True, 'total_overflow':0, 'outline_um':[800,200], 'sta':{'tt_setup_wns':80,'ff_hold_wns':5}, 'ft_hops':g}
    assert classify(r,[])['cls']=='STRUCTURAL'
    # Mutant drops the physical pin-tail audit; the same apparently good route
    # would be misclassified CLEAN.  Keep this contrast explicit.
    del r['ft_hops']
    assert classify(r,[])['cls']=='CLEAN'


def test_zero_overflow_cannot_hide_station_in_core(tmp_path):
    (tmp_path/'io.tcl').write_text('place_pin -pin_name {ft0_i[0]} -layer M6 -location {0 0}\nplace_pin -pin_name {ft0_o[0]} -layer M6 -location {100 0}\n')
    (tmp_path/'probe.tcl').write_text('create_blockage -region {10 10 90 90}\nplace_inst -name st_ft0_0_0 -location {50 50}\n')
    g=hop_stats(tmp_path)
    assert g['st_in_core']==1
    r={'exit':'EXIT 0','done':True,'total_overflow':0,'outline_um':[100,100],'sta':{'tt_setup_wns':80,'ff_hold_wns':5},'ft_hops':g}
    assert classify(r,[])['cls']=='STRUCTURAL'
