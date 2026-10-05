import json
from pathlib import Path
import subprocess
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import w17_conservative_geometry_search as G

@pytest.mark.parametrize('q',[128,512,768,1024,1536,2048,7168])
def test_q_and_bf_are_disjoint_and_bounded(q):
    qm,bm=G.field_masks(q)
    qset=set();bfset=set()
    for a,b in zip(qm,bm):
        region=a['region'];lo=region*64;hi=lo+64
        qa=set(range(a['first_pair'],a['first_pair']+a['pairs']))
        ba=set(range(b['first_pair'],b['first_pair']+b['pairs']))
        assert qa|ba<=set(range(lo,hi))
        qset.update(qa);bfset.update(ba)
    assert len(qset)==q and len(bfset)==1024 and not qset&bfset
    assert qset|bfset<=set(range(8192))

@pytest.mark.parametrize('q',[0,127,7169,8192,8193,True,1024.0,'1024'])
def test_invalid_choices_reject_before_allocator(q,monkeypatch):
    def forbidden():
        raise AssertionError('invalid mask reached source/allocator inputs')
    monkeypatch.setattr(G.residency,'inputs',forbidden)
    with pytest.raises(ValueError,match='combined Q/BF'):
        G.search([1024,q])

def test_optimized_python_cli_rejects_without_writing(tmp_path):
    out=tmp_path/'invalid.json'
    result=subprocess.run([sys.executable,'-O',str(ROOT/'tools/w17_conservative_geometry_search.py'),
        '--q-pairs','8192','--out',str(out)],cwd=ROOT,capture_output=True,text=True)
    assert result.returncode!=0 and 'combined Q/BF' in result.stderr
    assert not out.exists()

def test_meaningful_negative_original_mask_spills():
    # Frozen original construction: total q+BF counts alone did not validate NP.
    q=8192
    old=[dict(region=r,first_pair=r*64+q//128+int(r<q%128),pairs=8) for r in range(128)]
    assert sum(x['first_pair']+x['pairs']>(x['region']+1)*64 for x in old)==128
    assert old[-1]['first_pair']==8192
    with pytest.raises(ValueError):G.field_masks(q)
