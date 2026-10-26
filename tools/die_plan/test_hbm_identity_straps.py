import copy
import json
from pathlib import Path
import pytest
from tools.die_plan.parent_id_straps import validate_parent_id_straps
from tools.die_plan import schema, check

PORT = 'strap_tile_tid'

def desc(width=6, value=31):
    return {'inst':'tile', 'straps':[{'port':PORT,'width':width,'value':value}]}

@pytest.mark.parametrize('value', [0,1,31,63])
def test_hbm_identity_input_and_exact_six_physical_bits(value):
    pins=[f'{PORT}[{i}]' for i in range(6)]
    for encoded in [value, f"6'b{value:06b}"]:
        assert validate_parent_id_straps(desc(value=encoded),{PORT:6},pins)=={PORT:{'width':6,'value':value}}

@pytest.mark.parametrize('width,value', [(2,1),(5,1),(7,1),(True,0),(6,-1),(6,64),(6,True),(6,"6'bxxxxx1"),(6,"2'b11"),(6,"6'd31"),(6,"6'b1111111")])
def test_bad_hbm_shape_or_non_id_value_is_rejected(width,value):
    with pytest.raises(ValueError):validate_parent_id_straps(desc(width,value))

@pytest.mark.parametrize('port',['strap_mode','strap_fault','strap_tile_id','strap_tile_tid_extra','strap_data'])
def test_no_generic_strap_exception(port):
    d=desc();d['straps'][0]['port']=port
    with pytest.raises(ValueError):validate_parent_id_straps(d)

def test_input_direction_missing_bit_and_duplicate_contract_fail():
    with pytest.raises(ValueError):validate_parent_id_straps(desc(),{})
    with pytest.raises(ValueError):validate_parent_id_straps(desc(),{PORT:5})
    with pytest.raises(ValueError):validate_parent_id_straps(desc(),{PORT:6},[f'{PORT}[{i}]' for i in range(5)])
    d=desc();d['straps']*=2
    with pytest.raises(ValueError):validate_parent_id_straps(d)


def test_schema_and_g0_use_exact_hbm_physical_bits():
    p=json.loads((Path(schema.__file__).parent/'examples/tiny_plan.json').read_text())
    tn=next(iter(p['partition_types']))
    h=dict(inst='tile',module='common_tile',origin_um=[8.64,8.64],outline_um=[17.28,17.28],
           straps=desc()['straps'],pins=[dict(name=f'{PORT}[{i}]',layer='M5',xy=[0,0]) for i in range(6)])
    p['partition_types'][tn]['hard_cores']=[h]
    assert schema.validate_structure(p)==[]
    r=check.Report(completeness=True);check.check_taps_cores(schema.Plan(p),r)
    assert not any('declared physical pins' in e['msg'] for e in r.errors())
    h['pins'].pop();r=check.Report(completeness=True);check.check_taps_cores(schema.Plan(p),r)
    assert any('declared physical pins' in e['msg'] for e in r.errors())
    h['straps'][0]['width']=2
    assert schema.validate_structure(p)


def test_formal_schema_cross_fields_preserve_kv_and_hbm_widths():
    js=pytest.importorskip('jsonschema')
    item=schema._core_id_straps['items']
    js.validate({'port':PORT,'width':6,'value':"6'b011111"},item)
    js.validate({'port':'strap_hid','width':2,'value':"2'b11"},item)
    for d in [{'port':PORT,'width':2,'value':"2'b11"}, {'port':'strap_hid','width':6,'value':"6'b000011"}]:
        with pytest.raises(js.ValidationError):js.validate(d,item)
