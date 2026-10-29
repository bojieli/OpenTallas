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


def test_explicit_local_leaf_mapping_is_exact():
    d={'inst':'u_t00','parent_id_leaf':'u_t[0][0]',
       'parent_id_straps':{'tile_id':{'width':16,'value':5}}}
    assert set(type_parent_id_straps({'contents':[d]}))=={'u_t[0][0]'}
    d['parent_id_leaf']=''
    with pytest.raises(ValueError):type_parent_id_straps({'contents':[d]})


def test_partial_bound_id_preserves_internal_low_bits_and_rejects_unknown():
    from tools.die_plan.parent_id_straps import validate_bound_id_bits
    # Native CB: the upper twelve ID bits are literals; low four remain
    # connected to the original tile-local tie cells, not this parameter.
    bits={i:[str((0x180>>i)&1),str((0x2b0>>i)&1)] for i in range(4,16)}
    assert validate_bound_id_bits(bits,16,0x180)==0x180
    with pytest.raises(ValueError):validate_bound_id_bits(bits,16,0x181)
    bits[15][1]='x'
    with pytest.raises(ValueError):validate_bound_id_bits(bits,16,0x180)


def test_sidx_width_is_exact():
    assert validate_parent_id_straps({'parent_id_straps':{'sidx':dict(width=3,value=7)}},{'sidx':3})
    with pytest.raises(ValueError):validate_parent_id_straps({'parent_id_straps':{'sidx':dict(width=4,value=7)}})


@pytest.mark.parametrize('base,lane', [(b,l) for b in (0,4) for l in range(4)])
def test_exact_keybuf_lane_identity(base,lane):
    d = {'module':'ot_hnx_idxn_keybuf_slice',
         'position_id_contract':{'kind':'KEYBUF_LANE_ID','pbase':base,'lane':lane},
         'parent_id_straps':{'strap_lane_id':{'width':3,'value':base+lane}}}
    assert validate_parent_id_straps(d, {'strap_lane_id':3}, [f'strap_lane_id[{i}]' for i in range(3)]) == d['parent_id_straps']
    import copy
    for path, value in [('module','ot_other'), ('position_id_contract',None)]:
        bad = copy.deepcopy(d); bad[path] = value
        with pytest.raises(ValueError): validate_parent_id_straps(bad)
    for key,value in [('pbase',2),('pbase',True),('lane',4),('lane',True),('kind','OTHER')]:
        bad = copy.deepcopy(d); bad['position_id_contract'][key]=value
        with pytest.raises(ValueError): validate_parent_id_straps(bad)
    for key,value in [('width',4),('value',(base+lane+1)%8)]:
        bad = copy.deepcopy(d); bad['parent_id_straps']['strap_lane_id'][key]=value
        with pytest.raises(ValueError): validate_parent_id_straps(bad)
    with pytest.raises(ValueError): validate_parent_id_straps(d, {'strap_lane_id':3}, actual_module='ot_other')
    with pytest.raises(ValueError): validate_parent_id_straps(d, {})
    with pytest.raises(ValueError): validate_parent_id_straps(d, {'strap_lane_id':3}, ['strap_lane_id[0]'])
