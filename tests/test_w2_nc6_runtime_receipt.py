"""Read-only receipt negative controls. No duplicate runtime/build."""
import copy
import importlib.util
import json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'results/rtl/w2_nc6_component_runtime_20261003/r1'
spec=importlib.util.spec_from_file_location('nc6_receipt',D/'verify.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)


def test_exact_terminal_scope():
    r=v.verify();assert r['case_count']==18 and r['fixture_cycles']==320
    assert not r['mutable_protection_qualified'] and not r['R14_connected_qualified']


@pytest.mark.parametrize('field,value',[('source_commit','badpin'),('runtime_returncode',1),
 ('runtime_launched',False),('worktree_clean',False),('verdict','PASS_PROTECTED')])
def test_bad_receipt_refused(field,value):
    r=json.loads((D/'record.json').read_text());r[field]=value
    with pytest.raises(AssertionError):v.verify(record=r)


def test_missing_and_duplicate_case_refused():
    t=(D/'runtime.log').read_text()
    with pytest.raises(AssertionError):v.verify(text=t.replace('CASE_PASS wronggeneration','MISSING wronggeneration'))
    with pytest.raises(AssertionError):v.verify(text=t+'\nCASE_PASS wronggeneration cycle=400\n')


def test_wrong_terminal_geometry_refused():
    t=(D/'runtime.log').read_text().replace('NC6 MAX16','NC5 MAX16')
    with pytest.raises(AssertionError):v.verify(text=t)


def test_still_live_and_binary_mismatch_refused():
    r=json.loads((D/'terminal.json').read_text());r['runner_proc_present']=True
    with pytest.raises(AssertionError):v.verify(terminal=r)
    r=json.loads((D/'terminal.json').read_text());r['binary_sha256']='wrong'
    with pytest.raises(AssertionError):v.verify(terminal=r)
