from types import SimpleNamespace
import pytest
import bind_position_bank as P


def bank(path='slg_EN_4', typ='kv3_pc', module='qkd_kvs_grp_h_r2c_r8pos'):
    cell=SimpleNamespace(path=path,module=module,ports={'x__tok':list(range(18)), 'x__tep':list(range(16)),
        'slg__cfg_stack':[0,1], 'slg__cfg_group':[0,1,2]})
    return SimpleNamespace(ab={'position_banks':P.ABI}, F=SimpleNamespace(cells=[cell]), cpart={0:'part'}, parts={'part':{'type':typ}},
                           plan={'partition_types':{}})


def test_physical_bank_reuses_one_shape_for_bypass_and_delayed_position():
    a=P.spec(bank(),0,'x__tok')
    b=P.spec(bank('slg_ES_4'),0,'x__tok')
    assert a['pad']==2 and b['pad']==0
    assert P.physical_key(a,2)==P.physical_key(b,0)


def test_wrong_arrival_is_rejected_despite_same_bank_name():
    meta=P.spec(bank(),0,'x__tok')
    with pytest.raises(ValueError,match='timing differs'):
        P.physical_key(meta,1)


def test_arbitrary_delay_selector_is_not_a_position_id():
    meta=P.spec(bank(),0,'x__tok')
    meta['selector']='external_phase_strap'
    with pytest.raises(ValueError,match='unknown position-bank'):
        P.physical_key(meta,2)


def test_position_must_match_template():
    with pytest.raises(ValueError,match='does not match'):
        P.spec(bank('slg_EN_2'),0,'x__tok')


def test_wrapper_cannot_hide_its_hardware_delay_by_omitting_declaration():
    b=bank();b.ab={}
    with pytest.raises(ValueError,match='without its timing declaration'):
        P.layout(b)


def test_unknown_timing_declaration_fails_closed():
    b=bank();b.ab['position_banks']='phase_selector_v0'
    with pytest.raises(ValueError,match='unknown position-bank declaration'):
        P.layout(b)


def test_v2_cland_epoch_depth_four_only_at_es1():
    """KV-BIND-R3: the landed plan's ABI keeps the tok decode and deepens only the ES_1 epoch chain to 4"""
    b=bank('slg_ES_1',typ='kv3_pc_v1',module='qkd_kvs_grp_r2c_r8pos');b.ab={'position_banks':P.ABI2}
    m=P.spec(b,0,'x__tep')
    assert m['pad']==4 and m['max_depth']==4
    assert P.physical_key(m,4)==(P.ABI2,'x__tep',4,16)
    o=bank('slg_EN_1',typ='kv3_pc_v1',module='qkd_kvs_grp_r2c_r8pos');o.ab={'position_banks':P.ABI2}
    assert P.spec(o,0,'x__tep')['pad']==0
    with pytest.raises(ValueError,match='timing differs'):
        P.physical_key(m,1)
