import copy
import schema
from test_schema import EX

def source_plan():
    p=copy.deepcopy(EX);t=next(iter(p['partition_types'].values()))
    t['landing_control_status_copy']=True
    t.setdefault('clock',{})['start_capture_um']=[12.,34.]
    t['reset_start_raw_exports']=[dict(port='rst_start_raw_0',instance='u_rrl_0',net='rst_rl_0',xy_um=[12.,34.])]
    return p,t

def test_native_source_fields_are_registered_without_weakening_unknown_keys():
    p,t=source_plan();assert schema.validate(p)==[]
    t['reset_start_raw_exports'][0]['invented']=True
    assert any("unknown key 'invented'" in e for e in schema.validate(p))

def test_source_shapes_and_boolean_are_checked():
    p,t=source_plan();t['landing_control_status_copy']='true'
    assert any('landing_control_status_copy' in e for e in schema.validate(p))
    p,t=source_plan();t['clock']['start_capture_um']=[12.]
    assert any('start_capture_um' in e for e in schema.validate(p))
    p,t=source_plan();del t['reset_start_raw_exports'][0]['net']
    assert any("missing 'net'" in e for e in schema.validate(p))
