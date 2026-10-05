import sys,copy
from pathlib import Path
from unittest.mock import patch
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_native_workspace_provider_r20 as B

@pytest.fixture(scope='module')
def m():return B.model()

def test_complete_PC_home_scope_and_separate_charged_extents(m):
    assert m['coverage']['PCs']==1737 and m['coverage']['opcode_classes']==21
    assert m['coverage']['temporary_home_bindings']==19620
    for a in m['rank_allocation']:
        assert a['native_workspace_bytes']==2801511424
        assert a['I64_highword_sidecar_bytes']==1572864
        assert a['calendar_review_bytes']==6227469312
        for x,y in zip(a['extents'],a['extents'][1:]):assert x['base']+x['bytes']<=y['base']
        assert next(e for e in a['extents'] if e['name']=='activation_scratch')['bytes']==33554432
        assert next(e for e in a['extents'] if e['name']=='KV_provider_state')['bytes']==37504

def test_all_bound_native_homes_are_within_lease_and_extent(m):
    arenas={a['rank']:next(e for e in a['extents'] if e['name']=='native_workspace') for a in m['rank_allocation']}
    for h in m['temporary_homes']:
        assert h['lease']==f"PC{h['pc']}.workspace" and h['release_after']==f"PC{h['pc']}.retire"
        if h['class_']=='HBM_native_workspace':
            a=arenas[h['rank']];assert a['base']<=h['base']<h['end_exclusive']<=a['base']+a['bytes']
        else:assert min(h['slots'])>=3 and max(h['slots'])<32

def test_byte_and_sector_widths_are_distinct_and_decode_losslessly(m):
    for a in m['rank_allocation']:
        assert a['native_global_byte_address_bits']==33
        assert a['conservative_combined_global_byte_bits']==34
        assert a['system_sector_bits_used']==29 and a['maximum_local_sector_bits_used']==27
        assert max(a['prefix_allocation_bytes_per_stack'])<a['stack_capacity_bytes']
        for b in [a['old_allocated_end'],a['native_workspace_end']-1,a['conservative_combined_end']-1]:
            p=B.physical(b);local=32*p['local_sector31']+p['byte_in_sector']
            assert 512*(local//128)+128*p['stack']+local%128==b
        end=a['conservative_combined_end']
        assert sum(B.prefix_per_stack(end,s) for s in range(4))==end

def test_epoch_symbol_window_and_address_identity_do_not_truncate():
    base=4748333056
    old=B.packet(2**63+1,1730,0,0,base,9)
    window=B.packet(2**63+1,1730,0,2**31,base,9)
    assert old['producer']==2**63+1
    assert old['transport']==window['transport'] and old['caller']!=window['caller']
    assert old!=B.packet(2**63+2,1730,0,0,base,9)
    with pytest.raises(ValueError):B.packet(0,1730,2048,0,base,9)
    with pytest.raises(ValueError):B.packet(0,1730,0,-32,base,9)

def test_highword_codec_never_grants32bit_numeric_credit(m):
    wides=[h for h in m['temporary_homes'] if h.get('semantic_bits')==64]
    assert len(wides)==m['coverage']['explicit_I64_symbol_homes'] and len(wides)>0
    for h in wides:
        assert h['highword_bytes']==h['bytes']
        assert not h['codec_adapter_implemented']
    assert not m['hardware_or_rate_or_physical_admission']

def test_stale_calendar_cannot_admit_final_package(m):
    assert not m['final_native_calendar_source_match']
    assert m['source_native_sha256']!=m['source_calendar_consumed_native_sha256']
    assert all(not e['source_matched'] for a in m['rank_allocation'] for e in a['extents'] if e['name']=='calendar_padded_workspace_review_candidate')
    assert m['service_cost']['read_sector_compound_ticks']==106
    assert m['service_cost']['write_sector_compound_ticks']==126
    assert not m['service_cost']['measured']

def test_wrong_native_base_rejected():
    data=B.inputs()
    home=next(a['home'] for o in data[0]['operations'] for a in o['temporary_storage']['allocations'].values() if a['home']['class_']=='spill')
    home['base_by_rank']['0']=0
    with patch.object(B,'inputs',return_value=data),pytest.raises(AssertionError):B.model()

def test_zero_service_cost_rejected():
    data=B.inputs();data[1]['manifest']['endpoint_cycles']['values']['owner_lookup']=0
    with patch.object(B,'inputs',return_value=data),pytest.raises(AssertionError):B.model()
