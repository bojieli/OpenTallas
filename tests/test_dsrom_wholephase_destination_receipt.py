import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'tools'))
from dsrom_wholephase_destination_receipt import validate

P=dict(basis='ACTUAL_RUNTIME_SOURCE_OBSERVER',source_commit='test-fixture',binary_sha256='test-fixture')

def fixture():
    e=[dict(edge=0,kind='VM_destination_initial',a=32768+r,c=0xdeadbeef) for r in range(576)]
    e.append(dict(edge=10,kind='op_accept',a=10))
    for r in range(576):e.append(dict(edge=394,kind='root_row_accept',a=r%128,b=r,c=0))
    for r in range(576):e.append(dict(edge=395,kind='VM_write_accept',a=r%128,b=32768+r,c=0))
    for r in range(576):e.append(dict(edge=395,kind='VM_write_visible',a=32768+r,c=0,sampling='postNBA'))
    e.extend([dict(edge=396,kind='spine_idle'),dict(edge=412,kind='all_source_root_writer_drained',a=102400,b=576,c=576)])
    return e

def test_full_dependency_receipt():
    assert validate(fixture(),P)['acceptance_to_destination_edges']==385

def test_writer_offer_without_visible_destination_refused():
    with pytest.raises(ValueError):validate([e for e in fixture() if e['kind']!='VM_write_visible'],P)

def test_unchanged_zero_destination_not_proof():
    e=fixture();e[0]['c']=0
    with pytest.raises(ValueError):validate(e,P)

def test_wrong_final_value_refused():
    e=fixture();next(x for x in e if x['kind']=='VM_write_visible')['c']=1
    with pytest.raises(ValueError):validate(e,P)

def test_same_edge_root_writer_refused():
    e=fixture();next(x for x in e if x['kind']=='root_row_accept')['edge']=395
    with pytest.raises(ValueError):validate(e,P)

def test_offered_profile_not_runtime():
    with pytest.raises(ValueError):validate(fixture(),dict(P,basis='SEALED_PREDICTION'))

def test_duplicate_destination_refused():
    e=fixture();i=next(i for i,x in enumerate(e) if x['kind']=='VM_write_visible');e.insert(i,e[i].copy())
    with pytest.raises(ValueError):validate(e,P)
