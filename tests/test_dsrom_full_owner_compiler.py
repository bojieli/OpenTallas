import copy
import importlib.util
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_full_owner_compiler as C
import dsrom_full_owner_closure as V


def matrix(fmt='fp4',rows=16,K=512):
    return {'alias':'exp0.w1','tensor':'test.weight','layer':0,'expert':0,
            'format':fmt,'rows':rows,'K':K,'rank_slices':[{'rows':[r*rows,(r+1)*rows],'cols':[0,K]} for r in range(4)],
            'source_scale_tensor':'test.scale','conversion':'native','ECC':{'extra_sidecar_bits':8 if fmt=='fp4' else 0}}


def allocated(fmt='fp4',rows=16,K=512):
    p=C.Pool(1024,256);m=p.matrix(matrix(fmt,rows,K));m.update(stage=0,compiled_NP=1024)
    return p,m


def test_exact_compiled_BF_mask_and_padding():
    p=C.Pool(3375,724);f=p.compiled_field()
    assert f['BF_DUAL_site_IDs']==sorted({i*4096//724 for i in range(724)})
    assert len(f['Q_ONLY_site_IDs'])==4096-724
    assert len(f['weight_active_site_IDs'])==3375
    assert len(f['padding_site_IDs'])==721
    assert set(f['BF_DUAL_site_IDs'])<=set(f['weight_active_site_IDs'])
    # Independent old regional mask mutant must differ from actual RTL.
    old=set()
    for reg in range(128):
        ps=list(range(reg*32,reg*32+26+(reg<47)));k=5+(reg<84)
        old.update(ps[i*len(ps)//k] for i in range(k))
    assert old!=p.bf


def test_transactional_clone_and_finite_ECC():
    p,m=allocated();before=p.fill.copy();q=p.clone();q.matrix(matrix())
    assert p.fill==before and q.ecc_bits>p.ecc_bits
    assert len(C.Pool(3375,724).ecc_pairs)==103
    assert p.ecc_bits<=len(p.ecc_pairs)*4*4096*256
    assert all(x not in p.bf for x in p.ecc_pairs)


@pytest.mark.parametrize('fmt,K',[('fp4',2304),('fp8',1280),('bf16',5120)])
def test_rowtree_address_rank_and_physical_bound(fmt,K):
    p,m=allocated(fmt,K=K)
    assert C.check_matrix(m)
    a=C.Assignment([m]);seen=set()
    for row in range(m['rows']):
        for k in (0,31,32,K-1):
            x=a.address(0,m['alias'],3,row,k)
            assert x['tensor_row']==3*m['rows']+row and x['tensor_col']==k
            assert 0<=x['physical_row']<4096 and x['bit_range'][1]<=274
            if fmt=='bf16':assert x['pair'] in p.bf
            if fmt=='fp4':assert x['ECC_sidecar_linear_bit_offset'] is not None
    with pytest.raises(ValueError):a.address(0,m['alias'],4,0,0)


def test_no_overlap_and_mutant():
    p,m=allocated();n=p.matrix({**matrix(),'alias':'exp0.w3'});n.update(stage=0,compiled_NP=1024)
    assert C.check_global_overlap([m,n],[])['PASS']
    bad=copy.deepcopy(n);bad['plans']=copy.deepcopy(m['plans'])
    with pytest.raises(ValueError,match='overlap'):C.check_global_overlap([m,bad],[])


def test_omitted_row_wrong_root_and_tail_mutants():
    p,m=allocated(K=2304)
    bad=copy.deepcopy(m);bad['plans'].pop()
    with pytest.raises(ValueError,match='omitted'):C.check_matrix(bad)
    bad=copy.deepcopy(m);bad['plans'][0][1]+=p.per
    with pytest.raises(ValueError,match='region'):C.check_matrix(bad)
    bad=copy.deepcopy(m);e,el=bad['segments'][0];bad['segments'][0]=(e,el-32)
    with pytest.raises(ValueError):C.check_matrix(bad)


def test_provider_last_word_and_bounds():
    p={'banks':8,'words_per_bank':15360,'pairs':list(range(8))}
    x=C.provider_word_address(p,7,15359,224)
    assert x['pair']==7 and x['mb']==1 and x['physical_row']==3583
    with pytest.raises(ValueError):C.provider_word_address(p,8,0)


def test_tables_full_headers_and_exact_scale_address():
    h=C.load_headers(V.BASE/'inputs/tensor_headers.jsonl.gz');p=V.dedicated_providers(h)
    for t in p['tables']:
        a=V.dedicated_address(p,t['tensor'],t['rows']-1,255)
        b=V.dedicated_address(p,t['scale_tensor'],t['rows']-1,7,scale=True)
        assert {k:v for k,v in a.items() if k!='bit_range'}=={k:v for k,v in b.items() if k!='bit_range'}
        assert a['bit_range']==[248,256] and b['bit_range']==[256,264]
        assert a['die']<36 and a['physical_row']<4096
    assert p['tables'][0]['rows']==384006168
    assert p['tables'][1]['rows']==384016682


def test_all40_all384_declarations_without_payload():
    h=C.load_headers(V.BASE/'inputs/tensor_headers.jsonl.gz')
    for L in range(40):
        groups,cs,he,tables,covered=C.declarations(h,L)
        assert set(groups)=={None,*range(384)}
        assert all(len(groups[e])==3 for e in range(384))
        assert len(he)==2 and any(c['alias']=='gate.bias_vl' for c in cs)
        assert not {n for n in h if n.startswith(f'layers.{L}.')}-covered


def test_RTL_dualcompute_source_and_compiled_population():
    elem=C.gitread('rtl/v41rom/ot_v41_rom_elem_w10.sv').decode()
    field=C.gitread('rtl/v41die/ot_v41_field_w17w10.sv').decode()
    # Q lanes are outside the optional BF generate block; same pair includes both.
    assert elem.index('u_l0')<elem.index('if (BF16 != 0) begin : g_bf')
    assert 'g < NP' in field and '((i * NP) / NBF == p)' in field
    assert 4*4096!=4*3375 # active-only macrocharge negativecontrol


def test_unplaced_not_executable():
    m=matrix();m['stage']=None
    with pytest.raises(C.CapacityError):C.Assignment([m]).address(0,m['alias'],0,0,0)
