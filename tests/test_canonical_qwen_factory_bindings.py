"""Factory port adaptation checks only; no simulated arithmetic/token claim."""
import io
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from tools.gpu_sys import canonical_qwen_factory_bindings as F
from tools.gpu_sys.canonical_qwen_installed_services import installed_scratch_pins_class
from tools.gpu_sys.canonical_qwen_matrix_services import MatrixPhysicalServices
from tools.gpu_sys.canonical_qwen_matrix_tc_pins import PARAMS, FIELDS, SOURCE
from tools.qwen_connected_service_install import ROOT
from tools.gpu_sys.canonical_qwen_transport import TransportError


def pins():
    writer=io.StringIO()
    hello='ot_gpu_qwen_hbm_integrated_scratch ENABLE=1 SM=64 W2=256 RANKS=2 PC_PER_RANK=128 SCRATCH_CLIENT=1\n'
    root=installed_scratch_pins_class()(io.StringIO(hello),writer,
        portbook=ROOT/'rtl/model/qwen_hbm_connected_factory_20261003/ports.json')
    return root,writer


def provider():
    # Protocol test methods are never executed and offer no completion/READY.
    return SimpleNamespace(**{name:lambda *args:pytest.fail('constructor invoked lifecycle callback')
        for name in MatrixPhysicalServices.REQUIRED if name!='matrix_weight_consumed'})


def ports():return {(r,p):object() for r in range(2) for p in range(128)}


def test_default_off_before_any_binding():
    with pytest.raises(TransportError,match='default off'):
        F.compose(None,physical_provider=None,placement=None,w2_ports={},native_factory=None)


def test_current_book_missing_real_TC_never_invokes_native_or_RF():
    root,writer=pins()
    with patch.object(F,'build_RF_authority') as RF:
        with pytest.raises((TransportError,ValueError),match='genuine ot_gpu_sm_q'):
            F.compose(root,physical_provider=provider(),placement=None,w2_ports=ports(),
                      native_factory=lambda *args:pytest.fail('must await emitted TC'),enabled=True)
        RF.assert_not_called()
    assert writer.getvalue()=='HELLO\n' and root.edges==0 and root.hooks==[]


def test_missing_physical_provider_callbacks_refused():
    root,writer=pins()
    with pytest.raises(TransportError,match='actual complete MATRIX'):
        F.compose(root,physical_provider=object(),placement=None,w2_ports=ports(),
                  native_factory=lambda *args:None,enabled=True)
    assert writer.getvalue()=='HELLO\n'


def test_missing_rank_never_becomes_flat128_port_binding():
    root,writer=pins()
    with pytest.raises(TransportError,match='both actual128'):
        F.compose(root,physical_provider=provider(),placement=None,w2_ports={p:object() for p in range(128)},
                  native_factory=lambda *args:None,enabled=True)
    assert writer.getvalue()=='HELLO\n'


def test_RF_query_callbacks_preserve_source_request_and_owner():
    calls=[];result=object();request=object();owner=2**45+7
    RF=SimpleNamespace(resolve_source=lambda r,w:calls.append(('resolve',r,w)) or result,
        source_owner_retained=lambda r,o:calls.append(('capture query',r,o)) or result)
    delegate=SimpleNamespace(matrix_workspace_release=object())
    authority=F.FactoryAuthority(delegate,RF)
    assert authority.resolve_source(request,True) is result
    assert authority.source_owner_retained(request,owner) is result
    assert authority.matrix_workspace_release is delegate.matrix_workspace_release
    assert calls==[('resolve',request,True),('capture query',request,owner)]


def TC_header(root):
    # Header-only protocol test. Does not emit/claim a real TC engine instance.
    digest=root.book['source_sha256'].get(SOURCE,'a'*64)
    root.book['source_sha256'][SOURCE]=digest
    root.book['matrix_TC_contract']=dict(module='ot_gpu_sm_q',parameters=PARAMS,
        source_sha256=digest,consume_tap='u_sm.w_valid && u_sm.w_ready')
    for name,(direction,width) in FIELDS.items():
        root.book['pins']['tc_'+name]=dict(direction=direction,leaf_bits=width,bits=64*width,count=64)
    root.get=lambda name:1 if name=='tc_enabled' else pytest.fail('unexpected runtime sampling '+name)


def test_adaptation_all64_real_component_indices_one_clock_and_no_native_defaults():
    root,writer=pins();TC_header(root)
    seen=[];RF=object()
    def native(authority,contexts):
        seen.extend((c.rank,c.SM,c.services.scratch.p.index,c.services.scratch.p.block) for c in contexts)
        assert all(c.root is root and c.services.a is c.authority for c in contexts)
        return {kind:lambda request:pytest.fail('not a runtime handler') for kind in F.NATIVE_KINDS}
    with patch.object(F,'build_RF_authority',return_value=RF):
        bound=F.compose(root,physical_provider=provider(),placement=None,w2_ports=ports(),
                        native_factory=native,enabled=True)
    assert seen==[(i//32,i%32,i,'scratch') for i in range(64)]
    assert bound['authority'].RF is RF
    assert len(bound['matrix_services'])==64 and len(bound['native_handlers'])==4
    assert root.edges==0 and root.hooks==[] and writer.getvalue()=='HELLO\n'


def test_native_factory_must_supply_all_four_handlers():
    root,writer=pins();TC_header(root)
    with patch.object(F,'build_RF_authority',return_value=object()):
        with pytest.raises(TransportError,match='exact four'):
            F.compose(root,physical_provider=provider(),placement=None,w2_ports=ports(),
                      native_factory=lambda *args:{},enabled=True)
    assert writer.getvalue()=='HELLO\n'


def test_native_constructor_cannot_take_over_clock():
    root,writer=pins();TC_header(root)
    def wrong_native(*args):
        root.edges+=1
        return {kind:lambda request:None for kind in F.NATIVE_KINDS}
    with patch.object(F,'build_RF_authority',return_value=object()):
        with pytest.raises(TransportError,match='must not clock'):
            F.compose(root,physical_provider=provider(),placement=None,w2_ports=ports(),
                      native_factory=wrong_native,enabled=True)
    assert root.stopped


def test_native_constructor_cannot_drive_async_reset_before_shared_enrollment():
    root,writer=pins();TC_header(root)
    def wrong_native(*args):
        root.set('state_rpc_por_n',0)
    with patch.object(F,'build_RF_authority',return_value=object()):
        with pytest.raises(TransportError,match='constructor cannot write'):
            F.compose(root,physical_provider=provider(),placement=None,w2_ports=ports(),
                      native_factory=wrong_native,enabled=True)
    assert writer.getvalue()=='HELLO\n'


def test_native_constructor_cannot_issue_real_clock_rpc():
    root,writer=pins();TC_header(root)
    def wrong_native(*args):
        root.tick()
    with patch.object(F,'build_RF_authority',return_value=object()):
        with pytest.raises(TransportError,match='constructor cannot write or clock'):
            F.compose(root,physical_provider=provider(),placement=None,w2_ports=ports(),
                      native_factory=wrong_native,enabled=True)
    assert writer.getvalue()=='HELLO\n' and root.edges==0


def test_captured_clock_reference_forwards_same_owner_after_constructor():
    root,writer=pins();TC_header(root);captured=[]
    def native(*args):
        captured.append(root.tick)
        return {kind:lambda request:None for kind in F.NATIVE_KINDS}
    with patch.object(F,'build_RF_authority',return_value=object()):
        F.compose(root,physical_provider=provider(),placement=None,w2_ports=ports(),
                  native_factory=native,enabled=True)
    # Pin-protocol test only: three driver acknowledgments, no RTL/arithmetic.
    root.reader=io.StringIO('OK\nOK\nOK\n')
    captured[0]()
    assert root.edges==1 and writer.getvalue()=='HELLO\nEVAL\nEDGE\nEVAL\n'


def test_TC_disabled_actual_status_refuses_before_RF_or_native():
    root,writer=pins();TC_header(root)
    root.get=lambda name:0 if name=='tc_enabled' else pytest.fail('unexpected sample')
    with patch.object(F,'build_RF_authority') as RF:
        with pytest.raises(ValueError,match='compiled TC opt-in'):
            F.compose(root,physical_provider=provider(),placement=None,w2_ports=ports(),
                      native_factory=lambda *args:pytest.fail('disabled actualTC'),enabled=True)
        RF.assert_not_called()
    assert root.edges==0 and writer.getvalue()=='HELLO\n'


def test_actual_consumption_observation_settles_current_offers_before_sampling():
    from tools.gpu_sys.canonical_qwen_matrix_tc_factory import SharedConsumption
    from tools.gpu_sys.canonical_qwen_matrix_tc_pins import TCPins
    events=[]
    tc=TCPins.__new__(TCPins)
    tc.root=SimpleNamespace(settle=lambda:events.append('settle current offers'))
    tc.get=lambda name:events.append('sample actual '+name) or 0
    observed=SharedConsumption(object(),tc)
    observed.before_edge()
    assert events==['settle current offers','sample actual consume_valid']


def manifest_header(root, *, enabled=1):
    TC_header(root)
    root.book['manifest_contract'] = dict(
        owner_module='ot_gpu_qwen_manifest_range_owner',
        issuer_module='ot_gpu_qwen_full_issuer_r3')
    from tools.gpu_sys.canonical_qwen_matrix_scratch_adapter import fields_for_book
    for name, (direction, _) in fields_for_book(root.book).items():
        root.book['pins']['scratch_'+name]['direction'] = direction
    root.get=lambda name: enabled if name=='manifest_enabled' else (
        1 if name=='tc_enabled' else pytest.fail('unexpected sampling '+name))


def test_manifest_selects_actual_authority_and_readonly_workspace_no_constructor_edges():
    root,writer=pins();manifest_header(root);RF=object()
    with patch.object(F,'build_RF_authority') as legacy, patch(
        'tools.gpu_sys.canonical_qwen_manifest_owner_bindings.build_RF_authority',
        return_value=RF) as manifest:
        bound=F.compose(root,physical_provider=provider(),placement=None,w2_ports=ports(),
            native_factory=lambda *args:{k:lambda request:None for k in F.NATIVE_KINDS},enabled=True)
    legacy.assert_not_called();manifest.assert_called_once_with(root,None)
    assert bound['authority'].RF is RF
    assert root.edges==0 and not root.hooks and writer.getvalue()=='HELLO\n'


def test_manifest_disabled_refuses_before_native_or_authority():
    root,writer=pins();manifest_header(root,enabled=0)
    with patch('tools.gpu_sys.canonical_qwen_manifest_owner_bindings.build_RF_authority') as RF:
        with pytest.raises(TransportError,match='manifest opt-in is disabled'):
            F.compose(root,physical_provider=provider(),placement=None,w2_ports=ports(),
                native_factory=lambda *args:pytest.fail('disabled manifest'),enabled=True)
    RF.assert_not_called()
    assert root.edges==0 and writer.getvalue()=='HELLO\n'


def test_manifest_cannot_retain_old_host_driven_workspace_namespace():
    root,_=pins();manifest_header(root)
    root.book['pins']['scratch_workspace_owner']['direction']='input'
    with pytest.raises(TransportError,match='scratch mux field workspace_owner'):
        F.validate_installed_book(root)


def banked_header(root):
    manifest_header(root)
    root.book['manifest_contract']['owner_module']='ot_gpu_qwen_banked_manifest_range_owner'
    for name in ('required_bank_mask64','required_input_bank_mask64','required_output_bank_mask64'):
        root.book['pins']['source_owner_'+name]=dict(direction='output',leaf_bits=64,
            count=64,bits=4096,block='source_owner',leaf=name)


@pytest.mark.parametrize('module',['ot_gpu_qwen_banked_manifest_range_owner',
    'ot_gpu_qwen_native_aperture_range_owner'])
def test_banked_manifest_uses_same_physical_RF_authority_without_synthetic_grants(module):
    root,writer=pins();banked_header(root);RF=object()
    root.book['manifest_contract']['owner_module']=module
    with patch('tools.gpu_sys.canonical_qwen_manifest_owner_bindings.build_RF_authority',return_value=RF) as factory:
        bound=F.compose(root,physical_provider=provider(),placement=None,w2_ports=ports(),
            native_factory=lambda *args:{k:lambda request:None for k in F.NATIVE_KINDS},enabled=True)
    factory.assert_called_once_with(root,None)
    assert bound['authority'].RF is RF and root.edges==0 and not root.hooks
    assert writer.getvalue()=='HELLO\n'


@pytest.mark.parametrize('field,value',[('direction','input'),('leaf_bits',7),('bits',64),
    ('count',1),('block','issuer'),('leaf','required_input_bank_mask64')])
@pytest.mark.parametrize('module',['ot_gpu_qwen_banked_manifest_range_owner',
    'ot_gpu_qwen_native_aperture_range_owner'])
def test_banked_mask_cannot_be_alias_or_undersized(field,value,module):
    root,_=pins();banked_header(root)
    root.book['manifest_contract']['owner_module']=module
    root.book['pins']['source_owner_required_bank_mask64'][field]=value
    with pytest.raises(TransportError,match='actual banked manifest mask64 port'):
        F.validate_installed_book(root)
