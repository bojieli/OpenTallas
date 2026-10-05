import copy
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_full_owner_compiler as C
import dsrom_full_owner_closure as V
import dsrom_owner_provider_first as P
import dsrom_owner_provider_first_readback as B
import dsrom_owner_provider_contract as Q
import dsrom_owner_phase_debit as D


@pytest.fixture(scope='module')
def prepared():
    h=C.load_headers(P.INPUTS/'tensor_headers.jsonl.gz')
    ds=[C.declarations(h,L) for L in range(40)]
    ps=[C.Pool(3375,724) for _ in range(58)]
    providers,homes=P.reserve_providers(ps,ds)
    return h,ds,ps,providers,homes


def test_same_candidate_provider_homes_order_and_bound():
    homes=[P.provider_home(L) for L in range(40)]
    assert homes==[L*58//40 for L in range(40)]
    assert len(set(homes))==40 and homes[-1]==56
    with pytest.raises(ValueError):P.provider_home(40)
    with pytest.raises(ValueError):P.provider_home(0,39)


def test_all_providers_precede_matrix_and_single_storage_count(prepared):
    _,ds,ps,providers,homes=prepared
    assert all(p.phases==0 for p in ps)
    assert len(providers)==80
    assert sum(len(p['pairs']) for p in providers)==360
    assert sum(len(p.ecc_pairs) for p in ps)==58*103
    assert {p['layer'] for p in providers}==set(range(40))
    assert {p['kind'] for p in providers}=={'HE','CROM'}
    seen=set()
    for p in providers:
        assert p['stage']==homes[p['layer']]
        for q in p['pairs']:
            key=(p['stage'],q);assert key not in seen;seen.add(key)
            assert q not in ps[p['stage']].bf
            assert q not in ps[p['stage']].ecc_pairs
            assert ps[p['stage']].fill[q]==8192
    assert C.check_global_overlap([],providers)['PASS']


def test_native_HE_packing_addresses_not_acknowledged_as_transport(prepared):
    _,_,_,providers,_=prepared
    he=next(p for p in providers if p['layer']==0 and p['kind']=='HE')
    a=P.provider_tensor_address(he,'hc_attn_fn',23,20479)
    b=P.provider_tensor_address(he,'hc_ffn_fn',23,20479)
    assert (a['native_bank'],a['native_word'],a['bit_range'])==(7,7679,[224,256])
    assert (b['native_bank'],b['native_word'],b['bit_range'])==(7,15359,[224,256])
    assert not a['transport_ABI_qualified']
    assert a['mb']==0 and b['mb']==1
    with pytest.raises(ValueError):P.provider_tensor_address(he,'hc_attn_fn',24,0)


def test_all_CROM_expanded_FP32_addresses_and_immutable_provider(prepared):
    _,ds,ps,providers,_=prepared
    for p in providers:
        if p['kind']!='CROM':continue
        spans=set()
        for d in p['declarations']:
            for i in (0,d['elements']-1):
                x=P.provider_tensor_address(p,d['alias'],i)
                key=(x['pair'],x['mb'],x['parity'],x['physical_row'],tuple(x['bit_range']))
                assert key not in spans;spans.add(key)
                assert x['bit_range'][1]<=256 and x['physical_row']<4096
    p=ps[0];immutable=p.raw.copy();q=p.clone();m=ds[0][0][None][0];q.matrix(m)
    assert q.raw==immutable and p.phases==0


def test_largest_Engram_projection_fits_after_full_preallocation(prepared):
    _,ds,ps,providers,homes=prepared
    m=next(m for m in ds[1][0][None] if m['alias']=='engram.wkv')
    x=ps[homes[1]].clone().matrix(m);x.update(stage=homes[1],compiled_NP=4096)
    assert len(x['plans'])==3200 and C.check_matrix(x)
    assert sum(n*w*2 for si,p,first,n,stride,start,w in x['plans'])==P.matrix_words(m)


def test_duplicate_provider_negative_control(prepared):
    _,ds,ps,providers,_=prepared
    records=[{**m,'stage':None,'plans':[]} for g,*_ in ds for ms in g.values() for m in ms]
    with pytest.raises(ValueError,match='duplicate provider'):
        P.verify_records(records,providers+[providers[0]],ds,ps[0].compiled_field())


def test_omitted_matrix_negative_control(prepared):
    _,ds,ps,providers,_=prepared
    records=[{**m,'stage':None,'plans':[]} for g,*_ in ds for ms in g.values() for m in ms]
    records.pop()
    with pytest.raises(ValueError,match='omission'):
        P.verify_records(records,providers,ds,ps[0].compiled_field())


def test_source_config_debit_all_compiled_sites():
    ctrl=C.gitread('rtl/v41die/ot_v41_pair_w17w10.sv').decode()
    assert 'CW = 3 * NSEG + 1' in ctrl and 'DEPTH = CW << PHW' in ctrl
    assert 'reg [47:0] cm [0:DEPTH-1]' in ctrl
    assert 4096*25*48*1024==5033164800
    assert C.secded_bits(48)==7


def test_hash_membership_identical_to_original_finite_site_predicate(prepared):
    _,_,ps,_,_=prepared
    f=ps[0].compiled_field()
    for k in ('weight_active_site_IDs','BF_DUAL_site_IDs'):
        original=f[k];fast=set(original)
        assert all((p in original)==(p in fast) for p in range(-1,4097))


def test_uniform_config_padding_and_reject_changed_geometry():
    stats=[{'stage':s,'compiled_NP':4096,'NBF':724,'control':B.control_debit(874 if s==0 else 0)} for s in range(58)]
    x=Q.uniform_control_contract(stats)
    assert x['uniform_required_PHW']==10
    assert x['uniform_source_cfg_data_bits_per_TP_rank']==58*4096*25*48*1024
    assert x['uniform_source_cfg_data_bits_per_TP_rank']>x['per_stage_minimal_width_profile_bits_per_TP_rank']
    assert x['cfg_loader_parallel_local_read_bits_per_cycle_per_stage']==4096*48
    assert x['cfg_boundary_bits']==14 and x['loader_address_width']==15
    assert not x['physical_fit_qualified']
    with pytest.raises(ValueError):Q.uniform_control_contract(stats[:-1])
    bad=copy.deepcopy(stats);bad[0]['compiled_NP']=3375
    with pytest.raises(ValueError):Q.uniform_control_contract(bad)


def test_actual_constant_rank_slices_and_HE_replication(prepared):
    h,_,_,providers,_=prepared
    crom=next(p for p in providers if p['layer']==0 and p['kind']=='CROM')
    a=Q.tensor_provider_address(crom,h,'attn_sink',0,15)
    b=Q.tensor_provider_address(crom,h,'attn_sink',3,15)
    assert a['source_row']==15 and b['source_row']==63
    assert a['pair']==b['pair'] and a['rank']!=b['rank']
    with pytest.raises(ValueError):Q.tensor_provider_address(crom,h,'attn_sink',4,15)
    he=next(p for p in providers if p['layer']==0 and p['kind']=='HE')
    a=Q.tensor_provider_address(he,h,'hc_ffn_fn',3,23,20479)
    assert a['source_row']==23 and a['source_col']==20479
    assert a['packing_reference']=='pack_he_fp32 HHW8'
    assert not a['actual_native_consumer_provider_ABI_bound']


def test_phase_pages_distinct_from_uniform_compiled_template():
    stats=[{'stage':s,'compiled_NP':4096,'NBF':724,'control':B.control_debit(874 if s==0 else 0)} for s in range(58)]
    x=D.derive(stats)
    assert x['allocated_total_matrix_phase_count']==874
    assert x['allocated_unpadded_cfg_source_data_bits_per_TP_rank']==874*4096*25*48
    assert x['uniform_template_bits_per_TP_rank']==58*4096*25*48*1024
    assert x['uniform_template_bits_per_TP_rank']>x['conditional_per_stage_minimum_width_template_bits_per_TP_rank']
    assert x['source_current_PHW6_binding'].startswith('FAIL')
    assert not x['physical_fit_qualified']
    with pytest.raises(ValueError):D.derive(stats[:-1])
