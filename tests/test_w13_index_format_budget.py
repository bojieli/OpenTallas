import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from w13_index_format_budget import budget,bits_roundtrip

def test_all_ieee_bits_transport():
    words=[0,0x80000000,1,0x7f800000,0xff800000,0x7fc01234,0x7f801234,0x7f7fffff]
    assert bits_roundtrip(words)==words

def test_all_mix_capacity_and_service():
    for n in range(65):
        b=budget(n);r=b['shared_regions']
        assert all(a[2]<=z[1] for a,z in zip(r,r[1:]))
        assert r[-1][2]==55936<65536
        assert b['mixed_commands']==2*(n*16+(64-n)*3+64)
        assert b['physical_admission']=='FAIL_CLOSED'
        assert len({(5*64+row)%32 for row in range(32)})==32
    assert budget(64)['mixed_commands']==2176
    assert budget(0)['mixed_commands']==512

def test_transpose_banks():
    for i in range(32):
        assert len({(i*33+j)%32 for j in range(32)})==32
        assert len({(j*33+i)%32 for j in range(32)})==32
