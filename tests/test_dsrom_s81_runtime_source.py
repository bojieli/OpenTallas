import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_s81_runtime_source as S


def test_real_host_uses_full_strict_graph(tmp_path):
    original=(ROOT/S.HOST).read_bytes()
    paths=S.prepare(tmp_path/'selected');s=paths[0].read_text()
    assert (ROOT/S.HOST).read_bytes()==original
    assert '#include "Vrd64.h"' in s and 'std::unique_ptr<Vrd64> rd64' in s
    assert 'Vretn' not in s and 'Vroot' not in s
    assert '__builtin_ctz' not in s and 'return_owner' not in s
    assert 'meta.np!=2417' in s and 'meta.bf.size()!=519' in s
    assert 'setb(rd64->lv,i,1,a.v)' in s
    assert 'setb(die.rom_fr,o+68,1,getb(rd64->rv,region,1))' in s
    assert 'uint64_t f=rd64->fault' in s and 'f|=m.fault' in s
    assert 'DSROM_C8_S81 0' in s and 'if(i!=act.size())' in s
    assert 'c8_observe' in s and 'c8_retired' in s
    assert S.prepare(tmp_path/'selected')==paths


def test_native_word_transport_bounds_no_padded_return(tmp_path):
    s=S.prepare(tmp_path)[1].read_text()
    assert 'stage>=81' in s and 'pair>=2417' in s
    assert '4*pair+2*bank+(logical&1)' in s and 'logical>>1' in s
    assert 'return_pair' not in s and 'std::mutex' in s
    assert 'reply' in s and 'result[8]>>18' in s
    assert 'DSROM_S81_ROM_SOCKET' in s


def test_changed_host_refuses():
    s=(ROOT/S.HOST).read_text().replace('    int NL, L, LR, LS;','    int changed;')
    with pytest.raises(ValueError):S.transform_host(s)
