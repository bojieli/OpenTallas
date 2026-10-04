import pytest
from tools.gpu_sys.canonical_qwen_ranked_source_placement import sector,RankedSector
from tools.gpu_sys.canonical_qwen_transport import TransportError

@pytest.mark.parametrize('rank',[0,1])
def test_exhaustive_first_4096_sectors(rank):
    seen=set()
    for b in range(0,4096*32,32):
        s=sector(rank,b)
        assert s.inverse()==b
        identity=(s.rank,s.PC,s.address)
        assert identity not in seen
        seen.add(identity)

@pytest.mark.parametrize('b',[0,128,512,4748295296,(1<<33),(1<<34)-32])
def test_high_address_and_rank_isolation(b):
    a=sector(0,b);c=sector(1,b)
    assert (a.PC,a.address)==(c.PC,c.address)
    assert (a.rank,a.PC,a.address)!=(c.rank,c.PC,c.address)

@pytest.mark.parametrize('rank,address',[(2,0),(True,0),(0,-32),(0,1<<34),(0,1)])
def test_no_truncation_or_misaligned_source(rank,address):
    with pytest.raises(TransportError):sector(rank,address)

def test_wrong_inner_bank_cannot_alias():
    s=sector(0,0)
    with pytest.raises(TransportError):RankedSector(s.rank,s.PC^1,s.address,s.source_address,s.bank)

def test_binds_exact_ranked_API_without_clock():
    calls=[]
    class Component:
        def parameter(self,n):return {'RANK_ID':1,'PC_ID':sector(1,128).PC}[n]
    class Pins:
        def component(self,block,index,*,rank):
            calls.append((block,index,rank));return Component()
    s=sector(1,128);s.component(Pins())
    assert calls==[('w2',s.PC,1)]
