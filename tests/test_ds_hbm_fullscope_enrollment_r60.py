"""Source enrollment/refusal only; no checkpoint or production constructor GO."""
from pathlib import Path
import sys,inspect,copy
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import ds_hbm_fullscope_enrollment_r60 as R

def contract():
    return dict(first_PC=11,last_PC=19,native_program_sha256='c65a584c1b1cfafcd00391af216870136a44ec142b0d11106df570db7b8eb264',actual_payload_checkpoint_verified=True,sealed_journal_inventory_verified=True,source_class_transition_verified=True,constructor_GO=True,complete_resource_projection=dict(fresh_sector_journal_bytes=1,codec_publication_witness_bytes=1,checkpoint_metadata_bytes=1,old_plus_cold_RAM_bytes=1))

def test_default_off():
    with pytest.raises(ValueError,match='default off'):R.source_classes()

def test_actual_kernel_class_and_source_identity():
    p,d=R.source_classes(opt_in=True)
    from h3_ds_connected_provider_r37 import peer
    from h4_c0_ds_runtime_bindings import BufferPublicationMixin,TypedOperandViewsMixin
    from ds_hbm_registered_loader_r57 import registered_sagan
    assert d.run_buffer is BufferPublicationMixin.run_buffer
    assert d.__mro__[2] is registered_sagan().NativeExecution
    assert d.__mro__[2].run_buffer is peer('h3_deepseek_full_token_driver').TokenDriver.run_buffer
    assert p._read_one is TypedOperandViewsMixin._read_one
    for cls in (*p.__mro__,*R.composed_engine_class(opt_in=True).__mro__):
        if cls is not object:assert inspect.getsource(cls)


def test_actual_retained_constructor_dispatch_refusal(tmp_path):
    _,driver=R.source_classes(opt_in=True);p=tmp_path/'wrong';p.write_bytes(b'wrong')
    with pytest.raises(ValueError,match='exact corrected native dispatch'):
        driver({}, {}, None,'revision',1,[],native_artifact_path=p,dispatch_artifact_path=p)

@pytest.mark.parametrize('key,value',[('actual_payload_checkpoint_verified',False),('sealed_journal_inventory_verified',False),('source_class_transition_verified',False),('constructor_GO',False),('native_program_sha256','wrong'),('first_PC',10)])
def test_scope_refusal(key,value):
    c=contract();c[key]=value
    with pytest.raises(ValueError):R.validate_scope_request(c,list(range(11)))

@pytest.mark.parametrize('key',['fresh_sector_journal_bytes','codec_publication_witness_bytes','checkpoint_metadata_bytes','old_plus_cold_RAM_bytes'])
def test_component_price_or_unknown_never_constructor_GO(key):
    c=contract();c['complete_resource_projection'][key]=None
    with pytest.raises(ValueError,match='positive'):R.validate_scope_request(c,list(range(11)))

def test_noncontiguous_retirement_refuses():
    with pytest.raises(ValueError,match='contiguous'):R.validate_scope_request(contract(),list(range(10)))

def test_refusal_before_source_constructor(monkeypatch):
    called=[];monkeypatch.setattr(R,'source_classes',lambda **k:called.append(k))
    c=contract();c['source_class_transition_verified']=False
    with pytest.raises(ValueError):R.construct_scope_provider(c,list(range(11)),{}, {}, {}, [])
    assert not called
