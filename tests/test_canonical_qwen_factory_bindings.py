"""Factory port adaptation checks only; no simulated arithmetic/token claim."""
import io
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from tools.gpu_sys import canonical_qwen_factory_bindings as F
from tools.gpu_sys.canonical_qwen_installed_services import installed_scratch_pins_class
from tools.gpu_sys.canonical_qwen_matrix_services import MatrixPhysicalServices
from tools.gpu_sys.canonical_qwen_matrix_tc_pins import PARAMS, FIELDS, SOURCE
from tools.gpu_sys.canonical_qwen_matrix_tc_factory import SharedConsumption
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


def TC_header(root, *, enabled=1):
    # Header-only protocol test. Does not emit/claim a real TC engine instance.
    digest=root.book['source_sha256'].get(SOURCE,'a'*64)
    root.book['source_sha256'][SOURCE]=digest
    root.book['matrix_TC_contract']=dict(module='ot_gpu_sm_q',parameters=PARAMS,
        source_sha256=digest,consume_tap='u_sm.w_valid && u_sm.w_ready')
    root.book['pins']['tc_enabled']=dict(direction='output',bits=1,count=1,leaf_bits=1)
    root.reader=io.StringIO(f'{enabled:x}\n')
    for name,(direction,width) in FIELDS.items():
        root.book['pins']['tc_'+name]=dict(direction=direction,leaf_bits=width,bits=64*width,count=64)


def test_adaptation_all64_real_component_indices_one_clock_and_no_native_defaults():
    root,writer=pins();TC_header(root)
    seen=[];RF=object()
    def native(authority,contexts):
        seen.extend((c.rank,c.SM,c.services.scratch.p.index,c.services.scratch.p.block) for c in contexts)
        assert all(c.root is root and c.services.a is c.authority for c in contexts)
        assert all(isinstance(c.authority,SharedConsumption) for c in contexts)
        assert len({id(c.services) for c in contexts})==64
        return {kind:lambda request:pytest.fail('not a runtime handler') for kind in F.NATIVE_KINDS}
    with patch.object(F,'build_RF_authority',return_value=RF):
        bound=F.compose(root,physical_provider=provider(),placement=None,w2_ports=ports(),
                        native_factory=native,enabled=True)
    assert seen==[(i//32,i%32,i,'scratch') for i in range(64)]
    assert bound['authority'].RF is RF
    assert len(bound['matrix_services'])==64 and len(bound['native_handlers'])==4
    assert root.edges==0 and root.hooks==[] and writer.getvalue()=='HELLO\nGET tc_enabled\n'


def test_native_factory_must_supply_all_four_handlers():
    root,writer=pins();TC_header(root)
    with patch.object(F,'build_RF_authority',return_value=object()):
        with pytest.raises(TransportError,match='exact four'):
            F.compose(root,physical_provider=provider(),placement=None,w2_ports=ports(),
                      native_factory=lambda *args:{},enabled=True)
    assert writer.getvalue()=='HELLO\nGET tc_enabled\n'


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
    assert writer.getvalue()=='HELLO\nGET tc_enabled\n'


def test_native_constructor_cannot_issue_real_clock_rpc():
    root,writer=pins();TC_header(root)
    def wrong_native(*args):
        root.tick()
    with patch.object(F,'build_RF_authority',return_value=object()):
        with pytest.raises(TransportError,match='constructor cannot write or clock'):
            F.compose(root,physical_provider=provider(),placement=None,w2_ports=ports(),
                      native_factory=wrong_native,enabled=True)
    assert writer.getvalue()=='HELLO\nGET tc_enabled\n' and root.edges==0


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
    assert root.edges==1 and writer.getvalue()=='HELLO\nGET tc_enabled\nEVAL\nEDGE\nEVAL\n'


def test_disabled_actual_TC_refused_before_RF_or_native_constructor():
    root,writer=pins();TC_header(root,enabled=0)
    with patch.object(F,'build_RF_authority') as RF:
        with pytest.raises(TransportError,match='actual compiled TC'):
            F.compose(root,physical_provider=provider(),placement=None,w2_ports=ports(),
                      native_factory=lambda *a:pytest.fail('disabled native must refuse'),enabled=True)
        RF.assert_not_called()
    assert root.edges==0 and root.hooks==[]
    assert writer.getvalue()=='HELLO\nGET tc_enabled\n'


def test_selected_context_settles_before_sampling_and_commits_after_edge():
    root,writer=pins();TC_header(root)
    with patch.object(F,'build_RF_authority',return_value=object()):
        bound=F.compose(root,physical_provider=provider(),placement=None,w2_ports=ports(),
            native_factory=lambda *a:{k:lambda request:None for k in F.NATIVE_KINDS},enabled=True)
    context=bound['matrix_contexts'][0];events=[]
    context.services.origin={'GO_tuple239':239}
    context.services.line={'phase':'consume','tag':7,'plan':{'line_address':9},'reservation':{'saved':1}}
    # Protocol fixture: tap becomes visible only after evaluation of offers.
    def settled():events.append('EVAL')
    def tap(name):
        assert events==['EVAL'];events.append('sample '+name);return 1
    with patch.object(root,'settle',side_effect=settled),patch.object(context.authority.TC,'get',side_effect=tap):
        context.authority.before_edge()
    assert events==['EVAL','sample consume_valid']
    assert context.authority.accepted is None
    context.authority.after_edge()
    assert context.authority.matrix_weight_consumed(7,9,{'saved':1}) is True
    assert context.authority.matrix_weight_consumed(7,9,{'saved':1}) is False
    assert root.edges==0 and root.hooks==[]


def test_Dewey_bind_delegates_original_controller_no_second_context_or_tick():
    root,writer=pins();TC_header(root)
    with patch.object(F,'build_RF_authority',return_value=object()):
        bound=F.compose(root,physical_provider=provider(),placement=None,w2_ports=ports(),
            native_factory=lambda *a:{k:lambda request:None for k in F.NATIVE_KINDS},enabled=True)
    context=bound['matrix_contexts'][56];native=object();controller=object()
    with patch.object(F,'bind_operator',return_value=controller) as bind:
        assert context.bind_operator(native,2,enabled=True) is controller
        bind.assert_called_once_with(root,context.authority,context.services,native,2,1,24,enabled=True)
    assert bound['matrix_services'][56] is context.services
    assert root.edges==0 and root.hooks==[]
