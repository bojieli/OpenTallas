import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_s81_system_sources as S


def binding():
    paths=[ROOT/S.CORE, ROOT/S.TILE,
           ROOT/'rtl/dsrom_sys/c8/ot_chip_v41x_die_owner_safe_c8.sv',
           ROOT/'rtl/dsrom_sys/c8/ot_v41_rt_die_l20_c8.sv']
    return SimpleNamespace(stages=81,pairs=2417,inventory={'TP':4},
                           contract={'return_contract':{'RD':64}},
                           native_sources=lambda export:paths)


def test_actual_complete_source_chain_and_defaults(tmp_path):
    b=binding()
    before={p:p.read_bytes() for p in b.native_sources(None)}
    r=S.install(b,'unused-fixture-export',tmp_path/'selected')
    assert r['parameters']==dict(COLL_ACCEPTED_POP=0,IDX_DRAIN_LOOKAHEAD=0,S81_COMMAND_TRACE=0,S81_TRACE_STAGE=-1,S81_HOST_WORKSPACE=0)
    assert r['added_cycles']==0 and r['pairs_per_rank_die']==2417
    roles={p.name:p for p in r['sources']}
    assert '.DRAIN_LOOKAHEAD(IDX_DRAIN_LOOKAHEAD)' in roles['ot_hdc_core_v41x.sv'].read_text()
    assert '.IDX_DRAIN_LOOKAHEAD(IDX_DRAIN_LOOKAHEAD)' in roles['ot_chip_v41x_tile.sv'].read_text()
    for name in ('ot_v41_rt_die_l20_c8.sv','ot_chip_v41x_die_owner_safe_c8.sv'):
        s=roles[name].read_text()
        assert 'parameter integer IDX_DRAIN_LOOKAHEAD=0,' in s
        assert '.COLL_ACCEPTED_POP(COLL_ACCEPTED_POP)' in s or '.FIX_ACCEPTED_POP(COLL_ACCEPTED_POP)' in s
    assert not r['parent_clock_loaded']
    assert all(p.read_bytes()==v for p,v in before.items())
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==r['source_sha256'][str(p)] for p in r['sources'])
    again=S.install(b,'unused-fixture-export',tmp_path/'selected')
    assert r==again


def test_actual_identity_price_unknown_until_trace(tmp_path):
    r=S.install(binding(),'unused',tmp_path/'selected',drain=True,accepted_pop=True,trace=True,stage=20)
    assert r['added_cycles'] == 0
    assert r['parameters']==dict(COLL_ACCEPTED_POP=1,IDX_DRAIN_LOOKAHEAD=1,S81_COMMAND_TRACE=1,S81_TRACE_STAGE=20,S81_HOST_WORKSPACE=0,X_IDX=2,IDX_RING=1)
    p=next(p for p in r['sources'] if p.name=='ot_v41_rt_die_l20_c8.sv')
    s=p.read_text()
    assert 'if(dut.cmd_go)' in s and 'trace_identity=c8_engine_identity' in s
    assert '`ifndef SYNTHESIS' in s and 'command_ordinal=command_ordinal+1' in s
    r=S.install(binding(),'unused',tmp_path/'priced',accepted_pop=True,
                actual_collectives=['actual-position100:command0','actual-position101:command0'])
    assert r['added_cycles']==0 and not r['head_candidate_selected']


@pytest.mark.parametrize('field,value',[('stages',82),('TP',2),('RD',4)])
def test_refuses_other_allocation(tmp_path,field,value):
    b=binding()
    if field=='stages':b.stages=value
    elif field=='TP':b.inventory['TP']=value
    else:b.contract['return_contract']['RD']=value
    with pytest.raises(ValueError):S.install(b,'unused',tmp_path/'selected')


def test_refuses_historical_regular_core(tmp_path):
    b=binding();old=b.native_sources(None)
    b.native_sources=lambda export:[ROOT/'rtl/hdc/v41x/ckvsel/ot_hdc_core_v41x.sv',*old[1:]]
    with pytest.raises(ValueError,match='selected native role: core'):
        S.install(b,'unused',tmp_path/'selected')


def test_trace_refuses_unowned_stage(tmp_path):
    for stage in (None, -1, 81, True):
        with pytest.raises(ValueError,match='stage owner'):
            S.install(binding(),'unused',tmp_path/'selected',trace=True,stage=stage)


def test_abandoned_head_candidate_refused(tmp_path):
    with pytest.raises(ValueError,match='headreg candidate rejected'):
        S.install(binding(),'unused',tmp_path,head=True)


def test_workspace_abi_is_setup_only_and_failclosed(tmp_path):
    r=S.install(binding(),'unused',tmp_path,workspace=True)
    p=next(p for p in r['sources'] if p.name=='ot_v41_rt_die_l20_c8.sv')
    s=p.read_text();w=s[s.index('function int v41rt_c8_workspace_write'):s.index('endfunction',s.index('function int v41rt_c8_workspace_write'))]
    assert r['parameters']['S81_HOST_WORKSPACE']==1
    assert 'identity[46:0]==c8_context_identity' in w and 'address<(1<<19)' in w
    assert '!c8_context_restored' in w and '!c8_stage_active' in w
    assert 'c8_write_quarantine' in w and 'rom_we' in w
    assert 'context_restored=' not in w and 'retire_v=' not in w
    assert 'v41rt_c8_workspace_write=1' in w


def stride_binding():
    b=binding();old=b.native_sources(None)
    b.native_sources=lambda export:[*old,*(ROOT/'rtl/hdc/v41x'/n for n in
        ('ot_hdc_v41x_su_adapt.sv','ot_hdc_v41x_vec.sv','ot_hdc_v41x_vec_lane.sv'))]
    return b


def test_source_selected_kvt_stride_complete_chain(tmp_path):
    b=stride_binding();before={p:p.read_bytes() for p in b.native_sources(None)}
    r=S.install(b,'unused',tmp_path/'selected',kvt_source_stride=True)
    assert r['parameters']['SU_KVT_SOURCE_STRIDE']==1
    assert '-GSU_KVT_SOURCE_STRIDE=1' in r['verilator_args']
    assert r['kvt_source_stride']=={'128':11,'512':13}
    assert r['physical_admission'] is False and r['parent_clock_loaded'] is False
    roles={p.name:p for p in r['sources']}
    assert '.KVT_SOURCE_STRIDE(SU_KVT_SOURCE_STRIDE)' in roles['ot_hdc_core_v41x.sv'].read_text()
    for name in ('ot_chip_v41x_tile.sv','ot_chip_v41x_die_owner_safe_c8.sv','ot_v41_rt_die_l20_c8.sv'):
        assert '.SU_KVT_SOURCE_STRIDE(SU_KVT_SOURCE_STRIDE)' in roles[name].read_text()
    for name in ('ot_hdc_v41x_su_adapt.sv','ot_hdc_v41x_vec.sv','ot_hdc_v41x_vec_lane.sv'):
        assert roles[name]==ROOT/'rtl/hdc/v41x/s81_kvt_stride'/name
        assert ROOT/'rtl/hdc/v41x'/name not in r['sources']
    assert all(p.read_bytes()==data for p,data in before.items())
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==r['source_sha256'][str(p)] for p in r['sources'])


@pytest.mark.parametrize('case',['missing','duplicate','mismatch'])
def test_kvt_source_binding_refuses_unmatched_source(tmp_path,case):
    b=stride_binding();paths=b.native_sources(None)
    leaf=next(p for p in paths if p.name=='ot_hdc_v41x_vec_lane.sv')
    if case=='missing':paths.remove(leaf)
    elif case=='duplicate':
        duplicate=tmp_path/leaf.name;duplicate.write_bytes(leaf.read_bytes());paths.append(duplicate)
    else:
        wrong=tmp_path/leaf.name;wrong.write_text(leaf.read_text()+'\n// unmatched source\n')
        paths=[wrong if p==leaf else p for p in paths]
    b.native_sources=lambda export:paths
    with pytest.raises(ValueError,match='actual KVT source|original source mismatch'):
        S.install(b,'unused',tmp_path/'selected',kvt_source_stride=True)
