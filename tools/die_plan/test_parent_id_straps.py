import pytest
from tools.die_plan.parent_id_straps import validate_parent_id_straps, type_parent_id_straps

@pytest.mark.parametrize('port,width,value', [('tile_id',16,23),('tile_tid',6,63),('map_lane_j',4,15),('lane_lane_id',5,0)])
def test_ids_only_input_contract(port,width,value):
    d={'parent_id_straps':{port:{'width':width,'value':value}}}
    assert validate_parent_id_straps(d,{port:width})==d['parent_id_straps']

@pytest.mark.parametrize('port', ['fault_i','valid','data','rst_n','sid','arbitrary_id'])
def test_non_id_is_rejected(port):
    with pytest.raises(ValueError):validate_parent_id_straps({'parent_id_straps':{port:{'width':1,'value':0}}},{port:1})

@pytest.mark.parametrize('width,value', [(0,0),(-1,0),(True,0),(4,-1),(4,16),(4,True)])
def test_invalid_width_value_is_rejected(width,value):
    with pytest.raises(ValueError):validate_parent_id_straps({'parent_id_straps':{'tile_id':{'width':width,'value':value}}})

def test_missing_output_or_wrong_width_is_rejected():
    d={'parent_id_straps':{'tile_id':{'width':16,'value':1}}}
    for inv in [{},{'tile_id':15}]:
        with pytest.raises(ValueError):validate_parent_id_straps(d,inv)

def test_duplicate_descriptors_must_agree():
    a={'inst':'u_tile','parent_id_straps':{'tile_id':{'width':16,'value':1}}}
    b={'inst':'u_tile','parent_id_straps':{'tile_id':{'width':16,'value':2}}}
    assert type_parent_id_straps({'contents':[a],'hard_cores':[a]})=={'u_tile':a['parent_id_straps']}
    with pytest.raises(ValueError):type_parent_id_straps({'contents':[a],'hard_cores':[b]})
