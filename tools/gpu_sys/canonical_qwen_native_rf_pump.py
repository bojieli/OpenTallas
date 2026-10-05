"""RF-owned successor helpers; original native4/raw-stream ABI stays unchanged.

Positive page staging uses the actual RFPorts mirror ACK plus held range-owner
query. Staging release consumes the QUERY seat, not the published source lease.
The engine's source-owner/visibility/reverse pins must remain enclosing hardware
outputs. This driver never sets them from a host ACK counter.
"""
from dataclasses import dataclass
import hashlib
from tools.gpu_sys.canonical_qwen_native_factory import DTYPES, need, uint
from tools.gpu_sys.canonical_qwen_rf_ports import RFPorts
from tools.gpu_sys.canonical_qwen_range_owner_bindings import RangeOwnerPort
from tools.gpu_sys.canonical_qwen_transport import TransportError


@dataclass(frozen=True)
class OwnedPage:
    """Actual currently held query seat and ACK_ID1 RF endpoint."""
    RF: RFPorts
    query: RangeOwnerPort
    tuple239: int
    slot: int
    owner46: int


def check_page(page, root):
    need(isinstance(page, OwnedPage) and isinstance(page.RF, RFPorts)
         and isinstance(page.query, RangeOwnerPort), 'actual RF/query transactors required')
    p = page.query.physical
    need(p.root is root and page.RF.ports.root is root, 'one physical enclosing clock')
    t = uint(page.tuple239, 239, 'actual source tuple')
    slot = uint(page.slot, 9, 'actual RF slot')
    owner = uint(page.owner46, 46, 'actual RF owner')
    p.settle()
    need(not p.get('fault') and p.get('query_result_valid') and p.get('source_owner_retained')
         and (p.get('query_result_tuple'), p.get('query_result_slot'), p.get('query_result_owner'))
         == (t,slot,owner), 'page query identity/owner no longer physically held')
    return p


class PageInitializer:
    """Write input bytes under a genuine admitted page query, then release seat.

    Ownership validation executes before every shared RF edge through a scoped
    port proxy; a lease change during a stall cannot silently reach the write/ACK.
    Existing hooks are preserved. The initializer is not a new clock owner.
    No constructor writes/ticks, no free-slot inference, no ownership dictionary.
    """
    def __init__(self, root):
        self.root = root
        self.stopped = False
        self.busy = False

    def write(self, page, payload):
        need(not self.stopped and not self.busy, 'initializer debt/fault retained')
        need(type(payload) is bytes and len(payload)==512, 'complete admitted RF page required')
        check_page(page,self.root)
        self.busy=True
        actual_ports=page.RF.ports
        class CheckedPort:
            def __getattr__(_,name):return getattr(actual_ports,name)
            def tick(_):
                check_page(page,self.root)
                return actual_ports.tick()
        # Keep the same RF transactor's pending guard and the existing root's
        # sole SharedEdgeServices hook. Do not enroll another runtime hook.
        page.RF.ports=CheckedPort()
        try:
            ACK=page.RF.write(page.slot,page.owner46,payload)
            check_page(page,self.root)
            need(ACK==(page.slot,page.owner46), 'actual mirrored ACK identity')
            page.RF.ports=actual_ports
            need(page.query.complete_page(page.tuple239,page.slot,page.owner46) is True,
                 'actual query-seat release after mirror ACK')
            self.busy=False
            return dict(slot=page.slot,owner46=page.owner46,visible_copies=2,
                        payload_sha256=hashlib.sha256(payload).hexdigest(),query_seat_consumed=True)
        except BaseException:
            self.stopped=True
            raise
        finally:
            page.RF.ports=actual_ports


class InitialSourcePages:
    """Typed INITIAL RF source body using the existing manifest authority.

    INITIAL is source_PC=-1 and hardware PC2047; it is never native PC0.
    GO must already be genuinely accepted. RFPageHandlers resolves that actual
    association, drives writes, accepts both-mirror ACK and consumes the query
    seat. Whole initial visibility/terminal/reverse are NOT fabricated here.
    """
    def __init__(self, authority):
        from tools.gpu_sys.canonical_qwen_rf_ports import RFPageHandlers
        self.authority=authority
        self.handler=RFPageHandlers(authority)

    def begin(self, index, version):
        """Accept the installed issuer INITIAL offer for this immutable home.

        READY is offered only against the exact held INITIAL239+owner55 and
        bound protected row. This starts the source producer; it is not
        publication, W6 visibility, terminal, reverse or a numerical result.
        """
        uint(index,6,'INITIAL physical source bank')
        root=self.authority.RF.pins
        home=self.authority.RF.placement.rf.get((version,index//32,index%32))
        need(home is not None and home.birth==-1,'INITIAL immutable source home')
        version_id=self.authority.RF.placement.version_ids[version]
        port=self.authority.RF.owners[index].physical
        with root.lock:
            while True:
                root.settle();need(not port.get('fault'),'INITIAL source-owner fault')
                if (root.get('issuer_initial_go_valid')>>index)&1:
                    t=(root.get('issuer_initial_go_tuple')>>(239*index))&((1<<239)-1)
                    owner=(root.get('issuer_initial_go_owner')>>(55*index))&((1<<55)-1)
                    need(((t>>164)&2047)==2047 and ((t>>19)&2047)==version_id
                         and ((t>>30)&63)==index and ((t>>10)&511)==home.first and (t&1023)==home.end,
                         'actual INITIAL offer source/version/span')
                    need(port.get('inputs_bound_valid') and port.get('inputs_bound_tuple')==t,
                         'INITIAL protected input/root association not bound')
                    before=root.get('issuer_initial_go_ready')
                    need(not before&(1<<index),'INITIAL caller already owns ready')
                    root.set('issuer_initial_go_ready',before|(1<<index))
                    try:
                        root.settle()
                        need((root.get('issuer_initial_go_valid')>>index)&1
                             and ((root.get('issuer_initial_go_tuple')>>(239*index))&((1<<239)-1))==t
                             and ((root.get('issuer_initial_go_owner')>>(55*index))&((1<<55)-1))==owner,
                             'INITIAL offer changed at actual acceptance')
                        root.tick()
                    finally:
                        root.set('issuer_initial_go_ready',before)
                    need(port.get('issued_input_live') and port.get('issued_input_started')
                         and port.get('inputs_bound_tuple')==t,'INITIAL actual GO not captured')
                    return dict(tuple239=t,owner55=owner)
                root.tick()

    def write(self, request):
        need(request.get('source_PC')==-1, 'explicit INITIAL source class required')
        key=request.get('source_key')
        need(isinstance(key,list) and len(key)==4 and key[0]=='RF', 'INITIAL RF source key')
        home=self.authority.RF.placement.rf.get((request.get('version'),key[1],key[2]))
        need(home is not None and home.birth==-1, 'INITIAL immutable home binding')
        return self.handler.source_page_write(request)


@dataclass(frozen=True)
class HeldRFCommand:
    """Source-compiled command offer to Pauli's actual held RF controller.

    `fields` are command input wires only, not flags that claim source ownership
    or visibility. The actual source-selected portbook must be supplied, so this
    helper cannot accidentally select the original raw operand-stream endpoint.
    """
    ports: object
    fields: tuple
    directions: object
    tuple239: int
    owner55: int
    result_shape: tuple
    dtype: str


class RFCommandPump:
    """Held command/result/reverse protocol with full source identity.

    No input-data stream: controller must read genuine admitted RF apertures.
    Portbook names deliberately explicit; owner ports never become input flags.
    """
    FORBIDDEN = frozenset(('RF_source_owner_held','RF_result_owner_held','output_visibility',
                           'source_owner_held','result_owner_held','reverse_fenced',
                           'provider_fenced','reset_fenced'))
    def __init__(self, root): self.root=root;self.stopped=False;self.busy=False

    def run(self, request, binding):
        from math import prod
        need(not self.stopped and not self.busy, 'RF native debt/fault retained')
        need(isinstance(binding,HeldRFCommand), 'source-selected held RF binding required')
        p=binding.ports
        need(p.root is self.root and p.parameter('ENABLE')==1
             and p.parameter('PROGRAM_SHA')==int(request['program_sha256'],16),
             'actual RF controller ABI; raw-stream engine refused')
        need(binding.dtype==request['source_result_dtype'] and binding.dtype in DTYPES,
             'source result dtype; no conversion in transport')
        shape=list(binding.result_shape)
        need(len(shape)<=8 and all(type(n) is int and n>=0 for n in shape) and prod(shape)<=128,
             'finite source result shape')
        need(request['explicit_shape'] is None or request['explicit_shape']==shape, 'explicit source result shape')
        t=uint(binding.tuple239,239,'captured tuple');owner=uint(binding.owner55,55,'captured owner55')
        PC=uint(request['source_PC'],11,'source PC');seq=uint(request['sequence'],64,'source sequence')
        need((t>>164)&2047==PC, 'source tuple PC')
        fields=dict(binding.fields)
        need(len(fields)==len(binding.fields) and all(k.startswith('cmd_')
             and k not in self.FORBIDDEN and (binding.directions.get(k).get('direction') if isinstance(binding.directions.get(k),dict)
                   else binding.directions.get(k))=='input' for k in fields),
             'only real source command INPUTS may be driven')
        expected=dict(cmd_PC=PC,cmd_sequence=seq,cmd_tuple=t,cmd_owner=owner)
        need(all(fields.get(k)==v for k,v in expected.items()), 'bound command full source identity')
        self.busy=True
        try:
            for k,v in fields.items(): p.set(k,v)
            p.set('cmd_valid',1)
            try:
                while True:
                    p.settle();need(not p.get('fault'),'RF command source fault')
                    need(not p.get('result_valid'),'RF result before actual command acceptance')
                    accepted=bool(p.get('cmd_ready'));self.root.tick()
                    if accepted:break
            finally:p.set('cmd_valid',0)
            size=prod(shape)*DTYPES[binding.dtype][1]
            p.set('result_ready',0)
            while True:
                p.settle();need(not p.get('fault'),'RF engine fault retains debt')
                if p.get('result_valid'):
                    result_id=(p.get('result_PC'),p.get('result_sequence'),p.get('result_tuple'),p.get('result_owner'))
                    need(result_id==(PC,seq,t,owner),'held RF result full identity')
                    need((p.get('result_dtype'),p.get('result_bytes'))==(DTYPES[binding.dtype][0],size),
                         'held result source dtype/extent')
                    bits=uint(p.get('result_data'),8192,'held raw result')
                    need(bits<1<<(size*8),'held result outside admitted extent')
                    p.set('result_ready',1)
                    try:
                        p.settle()
                        need(p.get('result_valid') and p.get('result_data')==bits
                             and (p.get('result_PC'),p.get('result_sequence'),p.get('result_tuple'),p.get('result_owner'))==result_id
                             and (p.get('result_dtype'),p.get('result_bytes'))==(DTYPES[binding.dtype][0],size),
                             'RF result changed on actual capture')
                        self.root.tick()
                    finally:p.set('result_ready',0)
                    payload=bits.to_bytes(size,'little');break
                self.root.tick()
            p.set('reverse_ready',0)
            while True:
                p.settle();need(not p.get('fault'),'RF reverse fault retains debt')
                if p.get('reverse_valid'):
                    reverse_id=(p.get('reverse_PC'),p.get('reverse_sequence'),p.get('reverse_tuple'),p.get('reverse_owner'))
                    need(reverse_id==(PC,seq,t,owner),'matched RF reverse full identity')
                    for name,value in dict(reverse_ack_PC=PC,reverse_ack_sequence=seq,
                                           reverse_ack_tuple=t,reverse_ack_owner=owner).items():p.set(name,value)
                    p.set('reverse_ready',1)
                    try:
                        p.settle()
                        need(p.get('reverse_valid') and (p.get('reverse_PC'),p.get('reverse_sequence'),p.get('reverse_tuple'),p.get('reverse_owner'))==reverse_id,
                             'RF reverse changed on acceptance')
                        self.root.tick()
                    finally:p.set('reverse_ready',0)
                    break
                self.root.tick()
            self.busy=False
            return dict(dtype=binding.dtype,shape=shape,payload=payload,
                        native_completion_accepted=True,reverse_validated=True,
                        template=request['template'],ordered_step=request['ordered_step'],
                        lowered_primitive=request['lowered_primitive'])
        except BaseException:
            self.stopped=True
            raise


class RFNativeHandlers:
    """Select four-handler successor without altering original native4 source.

    Lifecycle and immutable bodies stay the original physical transactors.
    Only primitive dispatch selects Pauli's RF controller, with one page query
    acquired/consumed at a time. Physical ownership must be supplied by Nash's
    installed allocator, never inferred from RF slot numbers or a Python pool.
    """
    def __init__(self, authority, contexts):
        from tools.gpu_sys.canonical_qwen_native_factory import NativeHandlers
        self.base=NativeHandlers(authority,contexts)
        self.authority=authority
        self.initializer=PageInitializer(self.base.root)
        self.pump=RFCommandPump(self.base.root)
        need(callable(getattr(authority,'native_input_page',None)),
             'physical RF operand-page resolver not installed')

    def handlers(self):
        handlers=self.base.handlers()
        # Keep the original exchange identity/fault barrier for all four RPCs.
        self.base.native_primitive=self.native_primitive
        return handlers

    def native_primitive(self,r):
        from math import prod
        code=self.base.native['microcode'].get(r['template']);step=r['ordered_step']
        need(type(step) is int and isinstance(code,list) and 0<=step<len(code)
             and code[step]==r['source_node']
             and r['template'] in self.base.native['operations'][r['source_PC']]['kernels'],
             'literal source PC/template/node')
        abi=self.base.native['tile_kernel_ABI'][r['template']]['steps'][step]
        need(r['lowered_primitive'] in abi['native_steps'],'source ordered primitive lowering')
        node_op=code[step]['op']
        attrs={'dtype':'I64'} if node_op in ('IADD64','SHL64') else (
              {'dtype':'U32'} if node_op in ('IADD','ISUB','SHR','AND','OR','SELECT') else {})
        if node_op=='NEG':attrs={'dtype':'U32'} if r['lowered_primitive']=='XOR' else {}
        need(r['attrs']==attrs,'source primitive exact rounding/type attributes')
        args=r['operands']
        need(isinstance(args,list) and len(args)<=4,'four actual operand seats')
        for a in args:
            need(a['dtype'] in DTYPES and isinstance(a['shape'],list) and len(a['shape'])<=8
                 and all(type(n) is int and n>=0 for n in a['shape'])
                 and prod(a['shape'])<=128 and type(a['payload']) is bytes
                 and len(a['payload'])==prod(a['shape'])*DTYPES[a['dtype']][1],
                 'actual operand source type/shape/bytes')
        binding=self.authority.native_binding('native_primitive_RF',r)
        need(isinstance(binding,HeldRFCommand),'real RF controller binding required')
        # Staging accepts only input bytes supplied by the source RPC. Padding
        # is legal only inside an actual complete page lease returned by the
        # physical resolver; each such query selects one full owned RF page.
        for index,a in enumerate(args):
            for offset in range(0,len(a['payload']),512):
                page=self.authority.native_input_page(r,index,offset//512)
                need(isinstance(page,OwnedPage) and ((page.tuple239>>164)&2047)==r['source_PC'],
                     'source-bound operand staging page')
                cmd=dict(binding.fields)
                need(page.slot==((cmd['cmd_source_slots']>>(18*index+9*(offset//512)))&511)
                     and page.owner46==((cmd['cmd_source_owners']>>(46*index))&((1<<46)-1))
                     and page.tuple239==binding.tuple239,
                     'queried operand page does not match actual controller aperture')
                self.initializer.write(page,a['payload'][offset:offset+512].ljust(512,b'\0'))
        # READY/visibility/lease checks are actual controller inputs provided
        # by the enclosing hardware; this pump never drives their positive values.
        return self.pump.run(r,binding)


def native_factory(authority,contexts):
    return RFNativeHandlers(authority,contexts).handlers()


def compile_command(request, row, *, tuple239, owner55, source_slots,
                    source_owners, result_slots, result_owner, result_shape):
    """Compile Pauli's real portbook fields from source descriptors/owned homes.

    Addresses/owners are supplied by installed physical bindings and compared
    again against authority_* in the RTL. This compiler creates no grants and
    reads no operand data values. It cannot override output_visible or fences.
    """
    from math import prod
    from tools.gpu_sys.canonical_qwen_native_factory import descriptor
    from tools.gpu_sys.canonical_qwen_native_opcode_abi import canonical_zero
    from tools.gpu_sys.canonical_qwen_service_calendar import canonical,sha,PROGRAM_SHA
    need(request.get('program_sha256')==PROGRAM_SHA,'canonical command program')
    need(row['template']==request['template'] and row['ordered_step']==request['ordered_step']
         and row['source_node']==request['source_node'] and row['lowered_primitive']==request['lowered_primitive']
         and row['attrs']==request['attrs'],'source-resolved controller ROM descriptor')
    operands=request['operands'];n=len(operands)
    need(0<=n<=4 and len(source_slots)==len(source_owners)==n,'all operand aperture bindings')
    types=counts=scalars=slots=owners=0
    for index,(a,pages,owner) in enumerate(zip(operands,source_slots,source_owners)):
        need(a['dtype'] in DTYPES and isinstance(a['shape'],list)
             and all(type(x) is int and x>=0 for x in a['shape']),'operand command type/shape')
        count=prod(a['shape']);need(1<=count<=128,'nonempty finite operand count')
        size=count*DTYPES[a['dtype']][1];pages_needed=(size+511)//512
        need(len(pages)==pages_needed and pages_needed<=2,'exact actual RF operand-page census')
        for j,slot in enumerate(pages):slots|=uint(slot,9,'RF source page')<<(index*18+j*9)
        owners|=uint(owner,46,'RF source owner')<<(index*46)
        types|=DTYPES[a['dtype']][0]<<(index*2)
        counts|=count<<(index*8);scalars|=int(count==1)<<index
    shape=list(result_shape)
    need(all(type(x) is int and x>=0 for x in shape),'result command shape')
    elements=prod(shape);need(1<=elements<=128,'nonempty finite result count')
    result_type=DTYPES[request['source_result_dtype']][0]
    pages_needed=(elements*DTYPES[request['source_result_dtype']][1]+511)//512
    need(len(result_slots)==pages_needed,'exact actual result-page census')
    need(len(set(result_slots))==len(result_slots)
         and not set(result_slots)&{slot for pages in source_slots for slot in pages},
         'result workspace may not overwrite live operand pages')
    rs=0
    for j,slot in enumerate(result_slots):rs|=uint(slot,9,'result RF page')<<(j*9)
    t=uint(tuple239,239,'command root');PC=uint(request['source_PC'],11,'command PC')
    need((t>>164)&2047==PC,'source-bound command root PC')
    dtype={'F32':0,'U32':1,'I64':2}.get(request['attrs'].get('dtype'),result_type)
    return dict(cmd_program_sha=int(PROGRAM_SHA,16),cmd_tuple=t,cmd_owner=uint(owner55,55,'command owner'),
                cmd_PC=PC,cmd_sequence=uint(request['sequence'],64,'source sequence'),
                cmd_descriptor=uint(row['id'],8,'descriptor id'),cmd_template=uint(row['template_id'],4,'template id'),
                cmd_step=uint(row['ordered_step'],6,'ordered step'),cmd_substep=uint(row['substep'],2,'source substep'),
                cmd_operands=n,cmd_elements=elements,cmd_types=types,cmd_dtype=dtype,cmd_result_type=result_type,
                cmd_canonical_zero=int(canonical_zero(request['lowered_primitive'],request['attrs'])),
                cmd_counts=counts,cmd_scalars=scalars,cmd_source_slots=slots,cmd_source_owners=owners,
                cmd_result_slots=rs,cmd_result_owner=uint(result_owner,46,'actual result RF owner'),
                cmd_shape_sha=int(sha(canonical(descriptor(request,shape))),16),cmd_movement_map=0)
