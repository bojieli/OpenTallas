import copy
import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('review',Path(__file__).parents[1]/'tools/qc_engram_eight_scale_intake.py');P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)

@pytest.fixture(scope='module')
def source():return P.inputs()

def test_complete_retained_and_exhaustive_review(source):
    spec,parent,data,qc,owner,gold,_=source
    r=P.validate(spec,parent,data,qc,owner,gold)
    assert r['wire_beats']==384 and r['BF16_outputs']==12288 and r['old_beat0_mismatches']==4032 and r['code_scale_pairs']==65536

def test_wrong_beat_scale_association(source):
    spec,_,data,*_=source;data=copy.deepcopy(data);b=bytearray(data['actual_rows.wire_beats.bin']);b[32]^=1;data['actual_rows.wire_beats.bin']=bytes(b)
    with pytest.raises(ValueError,match='matching beat scale'):P.wire_check(spec,data)

def test_wrong_code_association(source):
    spec,_,data,*_=source;data=copy.deepcopy(data);b=bytearray(data['actual_rows.wire_beats.bin']);b[0]^=1;data['actual_rows.wire_beats.bin']=bytes(b)
    with pytest.raises(ValueError,match='code binding'):P.wire_check(spec,data)

def test_truncated_fixture(source):
    spec,_,data,*_=source;data=dict(data);data['actual_rows.scales.bin']=data['actual_rows.scales.bin'][:-1]
    with pytest.raises(ValueError,match='fixture sizes'):P.wire_check(spec,data)

def test_region_hash_drift(source):
    spec,_,data,*_=source;spec=copy.deepcopy(spec);spec['actual_rows'][0]['source_regions'][0]['raw_sha256']='0'*64
    with pytest.raises(ValueError,match='region hash'):P.wire_check(spec,data)

def test_full_column_coverage(source):
    spec,_,data,*_=source;spec=copy.deepcopy(spec);spec['actual_rows'][1]['column']=0
    with pytest.raises(ValueError,match='coverage'):P.wire_check(spec,data)

def test_incorrect_parent_failure_count(source):
    spec,parent,data,qc,owner,gold,_=source;parent=dict(parent);parent['old_beat0_scale_mismatches']=0
    with pytest.raises(ValueError,match='old failure'):P.validate(spec,parent,data,qc,owner,gold)

def test_no_physical_credit(source):
    spec,parent,data,qc,owner,gold,_=source;parent=dict(parent);parent['model_admission']=True
    with pytest.raises(ValueError,match='qualification refused'):P.validate(spec,parent,data,qc,owner,gold)
