import copy
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_kv_credit17_route_cuts as P
import verify_qwen_rom_kv_credit17_routes as V


@pytest.fixture(scope='module')
def model():return P.R.obj(P.OUT/'model-r1.json')


def test_cold_construct_and_independent_track_replay(model):
    assert json.loads(json.dumps(P.price()))==model
    receipt=V.verify(model)
    assert receipt['checks']=='PASS_TRACK_AND_COST_REPLAY_ONLY'
    assert receipt['hardware_admission']=='FAIL'
    assert receipt['fill_control_tracks']==7973 and receipt['boundary_bits']==43256
    assert receipt['remaining_before_unknowns_mm2']<.251


@pytest.mark.parametrize('mutation',['duplicate_channel_track','borrow_clock_lane','shore_delivery_overlap','drop_untyped_bits','ideal_PHY','admit_build'])
def test_independent_replay_rejects_capacity_and_admission_mutations(model,mutation):
    m=copy.deepcopy(model);c=m['credit17_route_cuts']
    if mutation=='duplicate_channel_track':
        rows=c['channel_bands'][0]['allocated_tracks']['fill'];rows[1]=rows[0]
    elif mutation=='borrow_clock_lane':
        rows=c['field_delivery_trunks'][0]['allocations'];rows[0]['x_centers_um']+=rows[2]['x_centers_um'];rows[2]['x_centers_um']=[]
    elif mutation=='shore_delivery_overlap':
        c['field_delivery_trunks'][0]['rectangle_um'][0:3:2]=m['shoreline_cuts'][0]['band_x_um']
    elif mutation=='drop_untyped_bits':c['untyped_parent_boundary_bits']=0
    elif mutation=='ideal_PHY':m['actual_sustained_PHY_Bps']=113135616000
    elif mutation=='admit_build':m['source_map_admission']=True
    with pytest.raises(ValueError):V.verify(m)
