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
    assert r['parameters']==dict(COLL_ACCEPTED_POP=0,IDX_DRAIN_LOOKAHEAD=0,S81_COMMAND_TRACE=0,S81_TRACE_STAGE=-1)
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
    assert r['parameters']==dict(COLL_ACCEPTED_POP=1,IDX_DRAIN_LOOKAHEAD=1,S81_COMMAND_TRACE=1,S81_TRACE_STAGE=20,X_IDX=2,IDX_RING=1)
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


def test_enabled_drain_elaborates_actual_reader_without_changing_defaults(tmp_path):
    default=S.install(binding(),'unused',tmp_path/'off')
    enabled=S.install(binding(),'unused',tmp_path/'on',drain=True)
    assert 'X_IDX' not in default['parameters'] and 'IDX_RING' not in default['parameters']
    assert '-GX_IDX=2' not in default['verilator_args']
    assert enabled['parameters']['X_IDX']==2 and enabled['parameters']['IDX_RING']==1
    assert '-GX_IDX=2' in enabled['verilator_args'] and '-GIDX_RING=1' in enabled['verilator_args']
    top=next(p for p in enabled['sources'] if p.name=='ot_v41_rt_die_l20_c8.sv')
    assert 'IDX_DRAIN_LOOKAHEAD && (X_IDX != 2 || IDX_RING != 1)' in top.read_text()
    core=next(p for p in enabled['sources'] if p.name=='ot_hdc_core_v41x.sv')
    assert 'ot_hdc_v41x_idx_pool_adapt_drain #(.DRAIN_LOOKAHEAD(IDX_DRAIN_LOOKAHEAD),' in core.read_text()
    assert enabled['added_cycles']==0 and not enabled['parent_clock_loaded']
