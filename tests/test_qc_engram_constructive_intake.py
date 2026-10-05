import copy
import importlib.util
from pathlib import Path
import pytest
s=importlib.util.spec_from_file_location('review',Path(__file__).parents[1]/'tools/qc_engram_constructive_intake.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P)
@pytest.fixture(scope='module')
def source():return P.inputs()
def test_all_macro_coordinates_and_inverse(source):
 d,_,data,_=source;r=P.coverage(d,data['demand']);assert r['actual_macros']==1500067 and r['unpopulated_slots_total']==72797
@pytest.fixture(scope='module')
def trees(source):return P.tree_counts(source[0],source[2])
def test_full_FIFO_control_inventory(source,trees):
 d,i,_,_=source;r=P.state(d,i,trees);assert r['total_FF']==2073575326==r['feedback_MUX2'];assert r['response_MUX2']==452957184
def test_missing_macro_range_rejected(source):
 d,_,data,_=source;d=copy.deepcopy(d);d['homes'][1]['column_macro_end_exclusive']-=1
 with pytest.raises(ValueError,match='range identity'):P.coverage(d,data['demand'])
def test_coordinate_digest_rejected(source):
 d,_,data,_=source;d=copy.deepcopy(d);d['coordinate_inventory']['all1500067_home_macro_local_x_y_tuple_SHA256']='0'*64
 with pytest.raises(ValueError,match='coordinate digest'):P.coverage(d,data['demand'])
def test_missing_FIFO_headers_rejected(source,trees):
 d,i,_,_=source;i=copy.deepcopy(i);i['homes'][0]['double_packet_FIFO_FF_bits']=4608
 with pytest.raises(ValueError,match='FIFO/control'):P.state(d,i,trees)
def test_feedback_MUX_not_free(source,trees):
 d,i,_,_=source;i=copy.deepcopy(i);i['homes'][0]['held_state_feedback_MUX2_bits']=0
 with pytest.raises(ValueError,match='feedback MUX'):P.state(d,i,trees)
def test_no_idle_clock_credit(source,trees):
 d,i,_,_=source;i=copy.deepcopy(i);i['homes'][0]['idle_clock_credit']=True
 with pytest.raises(ValueError,match='idle clock'):P.state(d,i,trees)
def test_48FAIL_96unaccepted_L1NULL(source):
 d,i,data,_=source;r=P.admission(d,i,data);assert r['home48_status'].startswith('FAIL') and not r['home96_area_accepted'] and r['L1'] is None
@pytest.mark.parametrize('field,value,match',[('composed_admission',True,'NOT accepted'),('L1_generated_source',{},'L1 NULL')])
def test_no_admission_or_L1_promotion(source,field,value,match):
 d,i,data,_=source;d=copy.deepcopy(d);d[field]=value
 with pytest.raises(ValueError,match=match):P.admission(d,i,data)
