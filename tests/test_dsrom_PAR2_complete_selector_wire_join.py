import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'tools'))
import dsrom_PAR2_complete_selector_wire_join as J
import dsrom_noECC_complete_parent_map as P

@pytest.fixture(scope='module')
def model():return J.build()

def test_fullslot_replacement_once(model):
    old=P.build()[0]
    delta=model['selector']['reserved_rectangle_mm2']-old['selector']['reserved_rectangle_mm2']
    assert model['area']['combined_noncontainment_policy_screen_mm2']==pytest.approx(old['area']['combined_noncontainment_policy_screen_mm2']+delta)
    assert model['selector']['full_proxy_mm2']==pytest.approx(1.68241961736)
    assert model['selector']['state_bits']==698354

def test_compiled_inventory_and_BF_growth_unchanged(model):
    assert model['field']['all_compiled_pairs']==2048
    assert model['field']['BF_pairs']==362
    assert model['field']['macros']==8192 and model['field']['cfg_macros']==14336
    assert model['area']['BF_complete_frame_growth_charged_once_mm2']==pytest.approx(4.7050784928)

def test_full_iteration_not_free(model):
    l=model['selector_latency']
    assert l['added_stream_cycles_per_position']==9*142
    assert l['sixposition_verification_only_upper_no_overlap_cycles']==6*9*142
    assert l['drafter_and_commit_rollback_extra_unknown']
    assert not model['fulltoken_rate']

def test_geometry_not_physical_admission(model):
    assert model['geometry_G0']['reservation_no_overlap']
    assert not model['geometry_G0']['physical_build_admitted']
    assert model['selector']['single_full_slot_bbox_DBU'][3]<26000000
