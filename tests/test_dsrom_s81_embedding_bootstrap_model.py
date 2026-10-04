import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_s81_embedding_bootstrap_model as M


def test_all_token_endpoints_exact_source_inverse_and_capacity():
    crossed_homes = 0
    for token in range(129280):
        ends = [M.word_address(token,b) for b in (0,319)]
        crossed_homes += ends[0]['storage_home'] != ends[1]['storage_home']
        for b,a in zip((0,319),ends):
            reconstructed=a['global_pair']*16384+a['mb']*8192+2*a['physical_row']+a['side']
            assert reconstructed == token*320+b
            assert a['global_pair'] == a['storage_home']*632+a['local_pair']
            assert 0<=a['physical_row']<4096 and a['global_macro']<10100
    assert crossed_homes > 0


@pytest.mark.parametrize('token,beat',[(-1,0),(129280,0),(1,320),(1,-1),(True,0),(1,True)])
def test_bad_address_has_no_modulo_fallback(token,beat):
    with pytest.raises(ValueError): M.word_address(token,beat)


def test_all_h_commit_addresses_unique_and_bf16_exact_bits():
    patterns=[0,0x8000,0x3f80,0x7f80,0xff80,0x7fc1,0x0001,0xffff]*2
    addresses=[]
    for copy in range(4):
        for beat in range(320):
            c=M.vm_commit(beat,copy,patterns)
            addresses.extend(c['addresses'])
            assert c['fp32_bits'] == [x<<16 for x in patterns]
    assert addresses == list(range(20480))
    with pytest.raises(ValueError): M.vm_commit(0,4,patterns)
    with pytest.raises(ValueError): M.vm_commit(0,0,[65536]*16)


def test_serial_service_requires_all_actual_positive_costs():
    p=dict(rom_response_edges=2,delivery_edges=3,vm_beat_edges=1,release_edges=2,ssx_edges=100,period_ps=1000/1.2)
    assert M.serial_price(**p)['bootstrap_edges'] == 3620
    for key in list(p)[:-1]:
        with pytest.raises(ValueError): M.serial_price(**(p|{key:0}))
    with pytest.raises(ValueError): M.serial_price(**(p|{'ssx_edges':None}))


def test_storage_reuse_finite_costs_and_no_payload_or_performance_credit():
    m=M.build()
    assert m['storage']['embedding_macro_count']==10100
    assert m['storage']['new_macro_charge_mm2']==0
    assert m['storage']['embedding_home_pairs']==[632,632,632,629]
    assert m['finite_reader']['proposed_outstanding_words']==1
    assert m['finite_reader']['base_state_bits_excluding_owner']==319
    assert m['routing']['mux_bit_equivalents']==2766304
    assert m['routing']['constructive_3NAND2_per_bit_area_floor_mm2']>0
    assert m['latency']['cold_bootstrap_added_token_us'] is None
    assert 'SSX' in m['transfer']['mandatory_before_PC0']
    assert not m['actual_payload_read'] and not m['actual_reader_RTL_PASS']
    assert not m['adopted'] and not m['transfer']['nonstallable_SU_WROM_adapter_qualified']


def test_model_and_combined_record_replay():
    import rom_combined_source_pricing as C
    assert json.loads((M.ROOT/(M.BASE+'model.json')).read_text())==M.build()
    assert C.build()['DS_cold_embedding']==M.build()
