from types import SimpleNamespace
import pytest
import bind_position_bank as P


def bank(path='slg_EN_4', typ='kv3_pc', module='qkd_kvs_grp_h_r2c_r8pos'):
    cell=SimpleNamespace(path=path,module=module,ports={'x__tok':list(range(18)), 'x__tep':list(range(16)),
        'slg__cfg_stack':[0,1], 'slg__cfg_group':[0,1,2]})
    return SimpleNamespace(ab={'position_banks':P.ABI}, F=SimpleNamespace(cells=[cell]), cpart={0:'part'}, parts={'part':{'type':typ}})


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
