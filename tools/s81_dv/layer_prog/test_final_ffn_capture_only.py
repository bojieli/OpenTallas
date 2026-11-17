"""Current107/53 capture has bounded legal addresses; native RD alignment stays strict."""
import sys
from pathlib import Path
import pytest
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parents[1]/'s81_slice')]
import final_ffn as F
from cap_model import decode

COUNTS=[107,107,53,53,107,107,53,53,53,53,107,107,53,53,107,107]

def spans():
    result=[];start=0
    for count in COUNTS:result.append((start,count));start+=count
    assert start==1280
    return result

def test_actual_capture_encodings_and_expert_storage_bounds():
    owned=spans();all_addresses=set()
    for slot in range(7):
        for sid,(start,count)in enumerate(owned):
            cfg=F.capture(0,sid,slot,spans=owned,capture_only=True)
            assert cfg['obase']==512+64*slot and cfg['rbase']==start and cfg['rcnt']==count
            seen=set()
            for row in range(start,start+count):
                bad,leaf,port,address,data=decode(row<<13,0x3f800000,cfg)
                assert not bad and data==0x3f800000
                assert 0<=leaf<5 and 512+64*slot<=address<576+64*slot<=4096
                assert port==(address>>2)&1
                assert (leaf,address)not in seen
                seen.add((leaf,address))
                key=(sid,leaf,address)
                assert key not in all_addresses
                all_addresses.add(key)
            assert decode((start+count)<<13,0,cfg)[0]
            if start:assert decode((start-1)<<13,0,cfg)[0]

def test_read_and_transfer_apis_still_refuse_unaligned_current_shape():
    owned=spans()
    with pytest.raises(ValueError,match='eight-word'):F.capture(0,0,0,spans=owned)
    with pytest.raises(ValueError,match='eight-word'):list(F.word_transfers(0,spans=owned))

def test_default_capture_is_unchanged():
    for sid in range(16):
        assert F.capture(0,sid,6)==F.capture(0,sid,6,capture_only=True)

@pytest.mark.parametrize('bad',[[(0,80)]*16,[(0,321)]+spans()[1:],[(0,True)]+spans()[1:],spans()[:-1]])
def test_capture_rejects_overlap_bounds_and_incomplete_coverage(bad):
    with pytest.raises(ValueError):F.capture(0,0,0,spans=bad,capture_only=True)
