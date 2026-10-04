"""Preparation/independent reference controls; actual HDL runtime pending."""
import importlib.util
import json
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from w2_nc6_component_preparation import model
from w2_pc_exact_completion_model import Service
from w2_nc6_component_run import validate_runtime


def test_full_geometry_cost_clock_fence():
    m=model()
    assert m['geometry']==dict(NC=6,MAX_OUT=16,CTAGW=32,GENW=4,SIDW=3,PTAGW=35,scoped_tag_plus_generation=39,AW=34)
    assert m['state']['implemented_raw_bits']==4781
    assert m['state']['protected_bits']==9144
    assert m['state']['extra_guard_fence_body_mm2_ASSUMED']>0
    assert not m['clock']['SS_setup_hold_qualified']
    assert not m['reset']['rearm_erases_live_debt']
    assert not m['new_directory_client']


def test_sameedge_issue_response_is_not_valid_old_debt():
    s=Service(nc=6);s.rearm(1,True,True)
    r=dict(client=5,tag=0xffffffff,generation=15,write=0)
    s.tick(request=r,read=dict(r,data=42))
    out=s.tick()
    assert out['fault'] and out['outstanding'][5]==1
    assert out['read_delivery'] is None


def test_two_raw_invalid_flags_fit_query_padding():
    # Existing independently protected records, not two fresh72-bit words.
    assert (296+1+63)//64==(296+63)//64
    assert (40+1+63)//64==(40+63)//64


def test_fixture_contains_exact_frozen_terminal_set():
    expected=json.loads((ROOT/'results/uarch/w2_nc6_component_20261003/expected_cases.json').read_text())
    assert len(expected)==18
    text='\n'.join('CASE_PASS '+n+' cycle=10' for n in expected)+'\nCOMPONENT_PASS cases=18'
    assert validate_runtime(text)
    assert not validate_runtime(text.replace('CASE_PASS '+expected[0],'OMITTED '+expected[0]))
    assert not validate_runtime(text+'\nCASE_PASS '+expected[0]+' cycle=11')


def test_preparation_byteexact():
    saved=json.loads((ROOT/'results/uarch/w2_nc6_component_20261003/preparation.json').read_text())
    assert model()==saved
