import copy
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from tools.die_plan.parent_id_straps import validate_parent_id_straps
from tools.die_plan import schema, check

PORTS=['strap_corner','strap_hid','strap_bsel']

def desc(port='strap_corner',width=2,value="2'b11"):
    return {'inst':'core','straps':[dict(port=port,width=width,value=value)]}

@pytest.mark.parametrize('port',PORTS)
@pytest.mark.parametrize('value',range(4))
def test_only_identity_aliases_match_actual_inputs_and_physical_pins(port,value):
    for rep in [value,f"2'b{value:02b}"]:
        d=desc(port,value=rep)
        assert validate_parent_id_straps(d,{port:2},pins=[port+'[0]',port+'[1]'])=={port:dict(width=2,value=value)}

@pytest.mark.parametrize('port',['strap_mode','strap_fault','strap_data','strap_id','strap_corner2','HID'])
def test_no_generic_strap_permission(port):
    with pytest.raises(ValueError):validate_parent_id_straps(desc(port))

@pytest.mark.parametrize('width',[1,3,True])
def test_alias_width_is_exactly_two(width):
    with pytest.raises(ValueError):validate_parent_id_straps(desc(width=width))
    with pytest.raises(ValueError):validate_parent_id_straps({'parent_id_straps':{'strap_hid':dict(width=width,value=0)}})

@pytest.mark.parametrize('value',["2'bxx","2'd3","1'b1","2'b111","3'b001",4,-1,True])
def test_unknown_or_non_two_bit_value_rejected(value):
    with pytest.raises(ValueError):validate_parent_id_straps(desc(value=value))

def test_duplicate_or_unverified_pins_fail():
    d=desc();d['straps']*=2
    with pytest.raises(ValueError):validate_parent_id_straps(d)
    for pins in [['strap_corner[0]'],['strap_corner[0]','strap_corner[2]']]:
        with pytest.raises(ValueError):validate_parent_id_straps(desc(),pins=pins)
    with pytest.raises(ValueError):validate_parent_id_straps(desc(),inputs={})

def test_schema_and_g0_require_strict_identity_and_both_pin_bits():
    p=json.loads((Path(schema.__file__).parent/'examples/tiny_plan.json').read_text())
    tn=next(iter(p['partition_types']))
    h=dict(inst='core',module='astk',origin_um=[8.64,8.64],outline_um=[17.28,17.28],
           straps=[dict(port='strap_corner',width=2,value="2'b11")],
           pins=[dict(name='strap_corner[0]',layer='M1',xy=[0,0])])
    p['partition_types'][tn]['hard_cores']=[h]
    assert schema.validate_structure(p)==[]
    R=check.Report(completeness=True)
    check.check_taps_cores(schema.Plan(p),R)
    assert any('declared physical pins' in x['msg'] for x in R.errors())
    h['pins'].append(dict(name='strap_corner[1]',layer='M1',xy=[0,0]))
    R=check.Report(completeness=True)
    check.check_taps_cores(schema.Plan(p),R)
    assert not any('declared physical pins' in x['msg'] for x in R.errors())
    h['straps'][0]['port']='strap_mode'
    assert schema.validate_structure(p)
