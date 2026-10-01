import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w15_tp96_exact as C
import hdc_golden as G

def test_order_witness():
    packages=[np.float32(2**24),np.float32(1),np.float32(-2**24),np.float32(1)]+[np.float32(0)]*44
    ordered=C.tree(packages)
    packages[1],packages[2]=packages[2],packages[1]
    assert G.bits(ordered).item()==0x3f800000
    assert G.bits(C.tree(packages)).item()==0x40000000

def negative_log(kind, ranks=range(96)):
    return '\n'.join([f'NEG_REJECT kind={kind} die={d} op=0 idx=0' for d in ranks]+[f'NEG_DONE kind={kind} endpoints=96',f'expected {kind} rejection across all96 endpoints'])

def test_negative_requires_all96_specific_rejections():
    for kind in ['order','tag']:
        assert C.parse(negative_log(kind),kind)['passed']
        assert not C.parse(negative_log(kind,range(95)),kind)['passed']
        assert not C.parse(negative_log(kind,[0]*96),kind)['passed']
        assert not C.parse(negative_log(kind)+'\nW15TIMEOUT',kind)['passed']
    assert not C.parse(negative_log('order'),'tag')['passed']
    assert not C.parse('reduce mismatch op=0 die=95','order')['passed']
    assert not C.parse('tag mismatch op=0 die=0','tag')['passed']

def test_isa_or_partial_rows_cannot_pass():
    with pytest.raises(AssertionError):C.parse('PASS 96 ISA endpoints W15DONE faults=0')

def test_full_fixture_bytes_and_group_tree(tmp_path):
    d=tmp_path/'vectors';m=C.fixture(d)
    assert m['ranks']==96
    assert len((d/'part.hex').read_text().splitlines())==3*96*512
    assert [(x['words'],x['bytes']) for x in m['ops']]==[(512,32768),(5,288),(64,4096)]
