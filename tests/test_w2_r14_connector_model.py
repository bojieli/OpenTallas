"""Connector ABI/source-cost controls; not installed native caller evidence."""
import inspect
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import w2_r14_connector_model as c


def test_source_pins_and_costs():
    m = c.model()
    assert m['actual_W2_NC6']['table_rows'] == 96
    assert m['state_cost_inputs'] == dict(sidecar_logical_bits=1572864,
        sidecar_macro_capacity_bits=4194304, sidecar_macros=128,
        W10_protected_pipeline_increment_bits=1575936,
        RF_assembly_data_candidate_bits=131072, RF_assembly_mask_candidate_bits=512)
    assert m['write_contract']['p_wr_done_ready_required']
    assert not m['build_allowed']
    assert m['once_only']['net_area'] is None


def test_source_address_not_low7_guard():
    a = c.physical(32)
    assert a['physical_PC7'] == 0 and a['system_sector34'] == 1
    assert a['inverse_byte'] == 32
    for b in range(0, 512, 32):
        a = c.physical(b)
        assert a['inverse_byte'] == b
    assert {c.physical(b)['stack'] for b in range(0,512,32)} == set(range(4))


def test_meta_roundtrip_fullwidth():
    child = c.owner46(127, 5, 0xffffffff, 15)
    m = c.meta92(child,31,511,0xffffffff)
    assert c.decode_meta92(m) == dict(child=child, sm=31, rf_slot=511,parent_ref=0xffffffff)
    assert m.bit_length() == 92


def binding():
    child = c.owner46(0,5,0xffffffff,15)
    parent = c.owner46(7,5,123,2) << 9 | 123
    return dict(byte=32, child=child, source_meta=c.meta92(child,3,123,55),
                die=1,legacy_die=1,legacy_stack=0,length=1,beat=0,
                parent_ref=55,parent55=parent,sm=3)


def test_prebound_parent_is_not_last_child():
    b = binding()
    assert b['parent55'] >> 9 != b['child']
    assert c.validate_sector_binding(**b)['parent55'] == b['parent55']


@pytest.mark.parametrize('field,value', [('length',4),('beat',1),('byte',33),
    ('legacy_die',0),('legacy_stack',1),('sm',4),('parent_ref',56),
    ('child',c.owner46(1,5,0xffffffff,15)),('child',c.owner46(0,6,0xffffffff,15))])
def test_bad_binding_refused(field,value):
    b = binding(); b[field] = value
    with pytest.raises(ValueError): c.validate_sector_binding(**b)


def saved_return():
    return dict(die=1,stack=0,legacy192=(1<<191)+333,
        source_meta92=c.meta92(c.owner46(0,5,0xffffffff,15),3,123,55),
        backend16=c.backend16(11,0xabc),direction=0,beat=0)


def test_full16_echo():
    s = saved_return()
    assert c.validate_return(s,s.copy())
    assert s['backend16'] >> 12 == 11  # Independent of sourcegen15.
    o = s.copy(); o['backend16'] &= 4095
    with pytest.raises(ValueError): c.validate_return(s,o)


@pytest.mark.parametrize('field', list(saved_return()))
def test_wrong_stale_return_identity_refused(field):
    s = saved_return(); o = s.copy();o[field] ^= 1
    with pytest.raises(ValueError): c.validate_return(s,o)
    assert s == saved_return()  # No ownership mutation on malformed return.


def test_missing_identity_refused():
    s=saved_return();o=s.copy();del o['legacy192']
    with pytest.raises(ValueError):c.validate_return(s,o)


@pytest.mark.parametrize('missing', list(inspect.signature(c.release_predicate).parameters))
def test_each_causal_release_receipt_required(missing):
    r = {n:True for n in inspect.signature(c.release_predicate).parameters}
    assert c.release_predicate(**r)
    r[missing] = False
    assert not c.release_predicate(**r)


def test_rf_partial_or_codec_missing_refused():
    p=binding()['parent55']
    assert c.rf_publish(p,0xffff,True)==p
    with pytest.raises(ValueError):c.rf_publish(p,0x3,True)
    with pytest.raises(ValueError):c.rf_publish(p,0xffff,False)


def test_provider_class_not_client_cast():
    assert c.explicit_client(8,{8:1})==1
    assert c.explicit_client(1,{1:5})==5
    with pytest.raises(ValueError):c.explicit_client(8,{})
    with pytest.raises(ValueError):c.explicit_client(8,{8:6})


@pytest.mark.parametrize('missing', list(inspect.signature(c.generation_rearm).parameters))
def test_wrap_reset_requires_positive_fence(missing):
    r = {n:True for n in inspect.signature(c.generation_rearm).parameters}
    assert c.generation_rearm(**r)
    r[missing]=False
    assert not c.generation_rearm(**r)
