"""Compose owner implementations into the existing connected factory ABI.

This is port adaptation, not an issuer, allocator, arithmetic provider or
native handler. All producers remain mandatory caller-supplied source owners.
Binding constructs no clock hook and advances no edge; the existing runner
enrolls one SharedEdgeServices group after the actual factory returns.
"""
from dataclasses import dataclass
from tools.gpu_sys.canonical_qwen_transport import TransportError
from tools.gpu_sys.canonical_qwen_simulator import NATIVE_KINDS
from tools.gpu_sys.canonical_qwen_range_owner_bindings import build_RF_authority
from tools.gpu_sys.canonical_qwen_matrix_scratch_adapter import MatrixPhysicalServices, fields_for_book
from tools.gpu_sys.canonical_qwen_matrix_tc_pins import ConsumptionAuthority, bind_operator
from tools.gpu_sys.canonical_qwen_matrix_tc_factory import InstalledTCPins, SharedConsumption
from tools.gpu_sys.canonical_qwen_scratch_simulator import ScratchEnclosingPins, scratch_component


def require(condition, message):
    if not condition: raise TransportError(message)


class FactoryAuthority:
    """Use installed range-owner queries for RF; delegate actual KV/native ports.

    No source key, owner identity, fence or positive completion is rewritten.
    The RF callback consumes only its held query seat, not the source lease.
    """
    def __init__(self, physical_provider, RF):
        self.physical_provider, self.RF = physical_provider, RF

    def __getattr__(self, name): return getattr(self.physical_provider, name)
    def resolve_source(self, request, write): return self.RF.resolve_source(request, write)
    def source_owner_retained(self, request, owner46):
        return self.RF.source_owner_retained(request, owner46)


@dataclass(frozen=True)
class MatrixContext:
    root: object
    rank: int
    SM: int
    authority: ConsumptionAuthority
    services: MatrixPhysicalServices

    def bind_operator(self, native, source_PC, *, enabled=False):
        # Original all-290 controller and exact source PC; no substituted count.
        return bind_operator(self.root, self.authority, self.services, native,
                             source_PC, self.rank, self.SM, enabled=enabled)


def validate_installed_book(pins):
    require(isinstance(pins, ScratchEnclosingPins), 'actual scratch enclosing pins required')
    require(pins.book['inventory'].get('source_owner_count') == 64,
            'installed source_owner0..63 required, not a logical lease dictionary')
    # Constructors inspect the genuine emitted TC contract and all source fields.
    # Missing TC rejects before RF callbacks, native construction or pin writes.
    TC = tuple(InstalledTCPins(pins, i//32, i%32, enabled=True) for i in range(64))
    for name, (direction, width) in fields_for_book(pins.book).items():
        port = pins.book['pins'].get('scratch_'+name, {})
        require(port.get('direction') == direction and port.get('leaf_bits') == width
                and port.get('count') == 64 and port.get('bits') == width*64,
                'actual owned scratch mux field '+name)
    for i in range(64):
        owner = pins.component('source_owner', i)
        require(owner.root is pins and owner.parameter('SM_INDEX') == i,
                'source-owner physical SM binding')
    return TC


def compose(pins, *, physical_provider, placement, w2_ports, native_factory,
            enabled=False):
    """Return the real existing runner's factory(pins) result.

    The native owner supplies native_factory(authority, contexts), returning
    exactly four source handlers. The physical provider supplies the actual
    complete-input/workspace/output/terminal/reverse callbacks. There is no
    default handler, no constructor reset, no synthetic completion and no
    first-output-only publication. Its implementation remains owner work.
    """
    require(enabled, 'connected native factory adaptation default off')
    require(callable(native_factory), 'actual four-handler native factory required')
    require(set(w2_ports) == {(rank, pc) for rank in range(2) for pc in range(128)},
            'both actual128-PC physical banks required')
    required = set(MatrixPhysicalServices.REQUIRED) - {'matrix_weight_consumed'}
    require(all(callable(getattr(physical_provider, name, None)) for name in required),
            'actual complete MATRIX input/workspace/range/terminal/reverse provider required')
    before = (pins.edges, tuple(pins.hooks), pins.edge_open, pins.stopped)
    require(not pins.edge_open and not pins.stopped and not pins.hooks,
            'factory adaptation before sole shared-hook enrollment')
    TC = validate_installed_book(pins)
    if 'manifest_contract' in pins.book:
        require(pins.get('manifest_enabled') == 1,
                'actual compiled manifest opt-in is disabled')
        from tools.gpu_sys.canonical_qwen_manifest_owner_bindings import build_RF_authority as manifest_RF
        RF = manifest_RF(pins, placement)
    else:
        RF = build_RF_authority(pins, placement)
    authority = FactoryAuthority(physical_provider, RF)
    contexts = []
    for i, tc in enumerate(TC):
        consumed = SharedConsumption(authority, tc)
        services = MatrixPhysicalServices(consumed, scratch_component(pins, i//32, i%32), enabled=True)
        contexts.append(MatrixContext(pins, i//32, i%32, consumed, services))
    contexts = tuple(contexts)
    # Native constructors can inspect actual ports but cannot asynchronously
    # reset them, offer GO, drive READY/fences or clock before shared enrollment.
    original_rpc = pins._rpc
    original_tick, original_add_hook = pins.tick, pins.add_edge_hook
    binding_active = [True]
    def binding_rpc(command):
        require(not binding_active[0] or command.split(' ', 1)[0] not in ('SET', 'EDGE'),
                'native factory constructor cannot write or clock actual pins')
        return original_rpc(command)
    def binding_tick(*args, **kwargs):
        require(not binding_active[0], 'native factory constructor cannot write or clock actual pins')
        return original_tick(*args, **kwargs)
    def binding_hook(*args, **kwargs):
        require(not binding_active[0], 'native factory constructor cannot enroll a clock hook')
        return original_add_hook(*args, **kwargs)
    with pins.lock:
        pins._rpc, pins.tick, pins.add_edge_hook = binding_rpc, binding_tick, binding_hook
        try:
            handlers = native_factory(authority, contexts)
        finally:
            binding_active[0] = False
            pins._rpc = original_rpc
            pins.tick, pins.add_edge_hook = original_tick, original_add_hook
    require(isinstance(handlers, dict) and set(handlers) == set(NATIVE_KINDS)
            and all(callable(handler) for handler in handlers.values()),
            'exact four actual native/source handlers required')
    if (pins.edges, tuple(pins.hooks), pins.edge_open, pins.stopped) != before:
        pins.stopped = True
        raise TransportError('factory must not clock/reset/enroll an extra hook during binding')
    return dict(authority=authority, native_handlers=handlers, w2_ports=w2_ports,
                matrix_services=tuple(c.services for c in contexts), matrix_contexts=contexts)
