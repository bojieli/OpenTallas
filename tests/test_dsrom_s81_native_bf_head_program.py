import importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bf_head',ROOT/'tools/dsrom_s81_native_bf_head_program.py')
P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)

def test_full_k_source_exact_address_order():
    pairs=[P.address(g,a) for g in (0,1) for a in range(P.phase(g)['rom_words_per_macro'])]
    assert len(pairs)==320 and len(set(pairs))==320
    assert set(pairs)=={(h,b) for h in range(40) for b in range(8)}
    assert P.address(0,255)==(31,7) and P.address(1,0)==(32,0)

@pytest.mark.parametrize('grain', [0,1])
def test_bf_native_beat_demand_and_source_control(grain):
    p=P.phase(grain);word=p['phrom'][0]
    assert word&1 and (word>>1)&8191==5120 and (word>>46)&65535==2
    assert word>>62==3 and (word>>14)&65535==len(p['stream'])
    offered=[]
    for w in p['stream']:
        assert w<1<<48
        if w&1:
            for j in range(4):
                if w&(1<<(4+j)):offered.append(((w>>(8+8*j))&255,(w>>1)&7))
    assert len(offered)==p['rom_words_per_macro']
    assert set(offered)=={P.address(grain,a) for a in range(p['rom_words_per_macro'])}
    assert p['cfg'][0]>>42==1 and (p['cfg'][0]>>21)&31==1
    assert p['cfg'][17]==1  # second leaf local row1, no FP reorder

@pytest.mark.parametrize('grain,address',[(2,0),(0,256),(1,64),(0,-1)])
def test_invalid_native_requests_refused(grain,address):
    with pytest.raises(ValueError):P.address(grain,address)

def test_host_copy_requires_actual_current_source_router(tmp_path):
    src=tmp_path/'host.cpp'
    src.write_text('void dsrom_s81_minimum::bind_native_pair_source(\n'
                   'owner.source_rom(binding.second,unsigned(address))\n'
                   'owner.source_cfg(unsigned(address))\n')
    out=tmp_path/'copy.cpp';P.prepare_host(src,out)
    assert out.read_bytes()==src.read_bytes()
    src.write_text(src.read_text().replace('source_cfg','missing_cfg'))
    with pytest.raises(ValueError):P.prepare_host(src,tmp_path/'no.cpp')


def test_raw_bridge_uses_released_codec_and_refuses_wrong_coordinate():
    import struct
    spec=importlib.util.spec_from_file_location('bytes_bridge',ROOT/'tools/dsrom_s81_native_bf_head_bytes.py')
    b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
    class Provider:
        def native_bf_word(self,rank,row,h,step):
            assert (rank,row,h,step)==(3,32319,39,7)
            return dict(rank=rank,local_row=row,h=h,b=step,word274=(1<<273)|0x3f80)
    request=struct.pack('<4I',3,32319,39,7)
    reply=b.response(Provider(),request)
    assert len(reply)==56 and reply[:4]==bytes(4) and reply[4:20]==request
    assert int.from_bytes(reply[20:],'little')==(1<<273)|0x3f80
    bad=struct.pack('<4I',3,32320,39,7)
    assert b.response(Provider(),bad)[:4]==b'\x01\0\0\0'
    class Wrong(Provider):
        def native_bf_word(self,*_):return dict(rank=0,local_row=0,h=0,b=0,word274=0)
    assert b.response(Wrong(),request)[:4]==b'\x01\0\0\0'
