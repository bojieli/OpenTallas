from copy import deepcopy
import importlib.util
from pathlib import Path
import pytest

P=Path(__file__).resolve().parents[2]/'physical/die_plan/qwen_compute/coll_ftm_clock.py'
spec=importlib.util.spec_from_file_location('coll_ftm_clock',P)
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)


def test_only_clock_topology_changes_and_is_idempotent():
    raw={'partition_types':{'coll_ftm':{'outline_um':[786.24,1468.8], 'ft_slots':[{'name':'data','width':512,'stations':4}], 'clock':{'tap_um':[388.8,734.4], 'taps':[{'name':'glue0'},{'name':'glue1'}], 'insertion_ps':250,'insertion_ff_ps':202.5}}, 'other':{'clock':{'taps':[1]}}}, 'lanes':[{'cycles':4}]}
    before=deepcopy(raw)
    assert M.apply(raw) is raw
    assert raw['partition_types']['other']==before['partition_types']['other']
    assert raw['lanes']==before['lanes']
    got=deepcopy(raw['partition_types']['coll_ftm']);got['clock']=before['partition_types']['coll_ftm']['clock']
    assert got==before['partition_types']['coll_ftm']
    c=raw['partition_types']['coll_ftm']['clock']
    assert 'taps' not in c and c['tap_mode']=='density'
    assert c['tap_max_sinks']==1000 and c['tap_target_sinks']<=1000
    assert c['tap_radius_um']<=200 and c['tap_min_sinks']==1
    assert(c['insertion_ps'],c['insertion_ff_ps'])==(250,202.5)
    once=deepcopy(raw);M.apply(raw);assert raw==once


def test_missing_production_type_fails_closed():
    with pytest.raises(ValueError,match='production type'):
        M.apply({'partition_types':{}})


def test_profile_fields_obey_production_clock_schema():
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    import schema
    clock_schema=schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]
    errors=[]
    schema._check(M.PROFILE,clock_schema,"clock",errors)
    assert errors==[]
