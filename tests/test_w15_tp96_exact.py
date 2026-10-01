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
    assert G.bits(ordered).item()!=G.bits(C.tree(packages)).item()

def test_negative_requires_specific_rejection():
    assert C.parse('reduce mismatch op=0 die=95','order')['passed']
    assert not C.parse('W15TIMEOUT','order')['passed']
    assert C.parse('tag mismatch op=0 die=0','tag')['passed']
    assert not C.parse('reduce mismatch','tag')['passed']

def test_isa_or_partial_rows_cannot_pass():
    with pytest.raises(AssertionError):C.parse('PASS 96 ISA endpoints W15DONE faults=0')

def test_full_fixture_bytes_and_group_tree(tmp_path):
    d=tmp_path/'vectors';m=C.fixture(d)
    assert m['ranks']==96
    assert len((d/'part.hex').read_text().splitlines())==3*96*512
    assert [(x['words'],x['bytes']) for x in m['ops']]==[(512,32768),(5,288),(64,4096)]
