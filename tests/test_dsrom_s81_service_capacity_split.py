import importlib.util
from pathlib import Path
s=importlib.util.spec_from_file_location('split',Path(__file__).resolve().parents[1]/'tools/dsrom_s81_service_capacity_split.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def test_preserves_l20_actual_field():
    assert [m.field_endpoint(s) for s in (37,38)]==[37,38]
    assert m.service_endpoint(20)==40

def test_l19_alternate_home_and_source_distance():
    assert m.service_endpoint(19)==100
    assert m.anchor(100)==38
    assert m.hops(100,38)==1
    assert m.hops(100,37)==2

def test_one_complete_stage_receiver_not_serial_id_distance():
    assert m.field_endpoint(40)==101
    assert m.hops(40,101)==1
    assert m.hops(37,101)==4
    assert m.hops(101,37)==4
    assert m.hops(101,101)==0

def test_no_two_sources_alias_one_physical_field_endpoint():
    endpoints=[m.field_endpoint(s) for s in range(81)]
    assert len(set(endpoints))==81
    assert not set(m.service_endpoint(l) for l in range(40))&set(endpoints)
