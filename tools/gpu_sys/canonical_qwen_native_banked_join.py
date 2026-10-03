"""Additive source-derived movement command successor and INITIAL sizing.

Original1bb transport remains byte-identical. Movement maps are addresses,
never result bytes. An absent dynamic address generator is an explicit refusal.
"""
from math import prod
from tools.gpu_sys.canonical_qwen_native_layout import compile_layout
from tools.gpu_sys.canonical_qwen_native_opcode_abi import OPCODES
from tools.gpu_sys.canonical_qwen_native_rf_pump import compile_command as transport_command
from tools.gpu_sys.canonical_qwen_native_factory import need


def movement_map(request,result_shape):
    op=request['lowered_primitive']
    if op=='COPY':
        need(len(request['operands'])==1 and request['operands'][0]['shape']==list(result_shape),
             'COPY source shape')
        addresses=[(0,i) for i in range(prod(result_shape))]
    elif 26<=OPCODES[op]<=37:
        plan=compile_layout(op,[a['shape'] for a in request['operands']],request['attrs'],result_shape)
        need(plan['dynamic'] is None,'dynamic TAKE/SCATTER index generator not installed')
        # Current actual controller has no literal command storage. It would
        # select stale A for CONST with zero operands; do not send that command.
        need(op!='CONST','CONST literal RF aperture enrollment required')
        addresses=plan['addresses']
    else:
        return 0 # Arithmetic/bit op does not consume the movement map.
    need(len(addresses)==prod(result_shape) and len(addresses)<=128,'complete movement map extent')
    value=0
    for i,(select,index) in enumerate(addresses):
        need(0<=select<3 and 0<=index<128,'actual retained movement address')
        value|=(512|(select<<7)|index)<<(i*10)
    return value


def compile_command(request,row,**owned):
    fields=transport_command(request,row,**owned)
    fields['cmd_movement_map']=movement_map(request,owned['result_shape'])
    return fields


def initial_model():
    """Source-sized ONE global INITIAL endpoint for token/position banks0,32.

    Both are scalar input parameters, not checkpoint fetches or arithmetic.
    Initial copying is mandatory service, not an optional performance lever.
    """
    raw=239+55+32+2+2+1+3+1
    coded=((raw+63)//64)*72
    nand=5*(8192+3*239+3*55+4*46+4*9)+512
    return dict(default_enabled=False,endpoint_count=1,ranks=2,
                source_banks=[0,32],source_versions=['Qwen.-1.position.1','Qwen.-1.token.0'],
                source_version_ids=[0,1],source_slots=[32,33],source_words_each=1,
                payload_bytes_each_bank=512,MACs_per_cycle=0,
                RF_read_bytes_per_cycle=0,RF_write_bytes_per_accept_per_bank=512,
                RF_ACK_owner_bits_each=46,RF_ACK_slot_bits_each=9,
                boundary_write_bits=8192,query_boundary_bits=2*(239+46+9+2),
                root_event_bits=239+55,replicas=1,
                root_comparator_fanout=2,mux_inputs=2,
                protected_bits=coded,raw_bits=raw,seal_padding_bits=coded//72*64-raw,
                DFF_SS_body_um2=coded*.2916,logic_NAND2_budget=nand,
                body_area_um2_estimate=coded*.2916+nand*.08748,
                area_um2_at_50pct_estimate=2*(coded*.2916+nand*.08748),
                area_basis='SS cell proxy DFF.2916um2,NAND2.08748um2; excludes loaded buffers/clock/wires',
                tracks_required=8192+2*(239+46+9+2)+3*(239+55),
                channel_capacity=None,slot_fit=None,
                clean_calendar='accepted INITIAL; actual two bank page writes/ACKs + protected aggregate; CLOSE; query/RF drain; held visibility; terminal; reverse; actual frame retire',
                serial_min_control_edges=7,RF_ACK_wait_edges=None,loaded_timing=None,
                token_cost='two INITIAL values, four actual RF512B writes total plus control/ACK/drain waits; no CPUticks or zero unknown costs',
                HBM_initial_fetch_bytes=0,
                HBM_zero_reason='source-backed external token/position input scalars, not a checkpoint producer',
                physical_qualification=False,headline_credit=False)


class InitialProducer:
    """Drive the real INITIAL completion endpoint; never synthesize receipts.

    The endpoint itself taps actual accepted RF writes, matching SRAM ACKs,
    aggregate protected bank receipt and query/RF drainage. The caller offers
    only external input bits and an explicit CLOSE command, then waits for
    genuine issuer frame retirement. No terminal/visibility boolean is driven.
    """
    def __init__(self,authority,endpoint):
        from tools.gpu_sys.canonical_qwen_native_rf_pump import InitialSourcePages
        self.authority,self.endpoint=authority,endpoint
        self.root=authority.RF.pins
        need(endpoint.root is self.root and endpoint.parameter('ENABLE')==1,
             'actual enabled INITIAL endpoint required')
        for name in ('fault','busy','go_ready','close_ready','event_tuple','event_owner'):
            endpoint.get(name)
        self.pages=InitialSourcePages(authority)
        self.active=None
        self.stopped=False

    def begin(self,actor,version,input_bits):
        from tools.gpu_sys.canonical_qwen_native_factory import uint
        need(not self.stopped and self.active is None,'INITIAL retained/faulted context')
        uint(actor,6,'INITIAL actor');uint(input_bits,32,'external source input bits')
        need(version in ('Qwen.-1.position.1','Qwen.-1.token.0'),'literal INITIAL source version')
        homes={rank*32+sm:h for (v,rank,sm),h in self.authority.RF.placement.rf.items()
               if v==version and h.birth==-1}
        need(set(homes)=={0,32} and actor in homes,'actual scalar INITIAL source banks/actor')
        need(all(h.first==(32 if version=='Qwen.-1.position.1' else 33) and h.end==h.first+1 and h.words==1
                 for h in homes.values()),'literal INITIAL page allocation')
        vid=self.authority.RF.placement.version_ids[version]
        p=self.endpoint;root=self.root
        with root.lock:
            p.set('go_input_bits',input_bits)
            try:
                while True:
                    root.settle();need(not p.get('fault'),'INITIAL completion fault')
                    if ((root.get('issuer_initial_go_valid')>>actor)&1) and p.get('go_ready'):
                        t=(root.get('issuer_initial_go_tuple')>>(actor*239))&((1<<239)-1)
                        owner=(root.get('issuer_initial_go_owner')>>(actor*55))&((1<<55)-1)
                        need((t>>164)&2047==2047 and (t>>19)&2047==vid and (t>>30)&63==actor,
                             'actual INITIAL root execution identity')
                        for bank,h in homes.items():
                            bankp=self.authority.RF.owners[bank].physical
                            need(not bankp.get('fault') and bankp.get('inputs_bound_valid')
                                 and bankp.get('inputs_bound_tuple')==t,
                                 'all INITIAL physical bank roots must already be bound')
                        before=root.get('issuer_initial_go_ready')
                        need(before==0,'sole INITIAL endpoint ready already owned')
                        root.set('issuer_initial_go_ready',before|(1<<actor))
                        try:
                            root.settle()
                            need(p.get('go_ready') and ((root.get('issuer_initial_go_valid')>>actor)&1)
                                 and ((root.get('issuer_initial_go_tuple')>>(actor*239))&((1<<239)-1))==t,
                                 'INITIAL offer changed before actual capture')
                            root.tick()
                        finally:root.set('issuer_initial_go_ready',before)
                        need(p.get('busy') and p.get('event_tuple')==t and p.get('event_owner')==owner,
                             'INITIAL endpoint did not capture real GO')
                        for bank in homes:
                            bankp=self.authority.RF.owners[bank].physical
                            need(bankp.get('issued_input_live') and bankp.get('issued_input_started')
                                 and bankp.get('inputs_bound_tuple')==t,'all-bank INITIAL GO not actually accepted')
                        self.active=(t,owner,version,input_bits)
                        return dict(tuple239=t,owner55=owner)
                    root.tick()
            except BaseException:self.stopped=True;raise

    def write(self,request):
        need(self.active is not None and not self.stopped,'INITIAL not captured')
        t,owner,version,bits=self.active
        need(request.get('version')==version and request.get('source_PC')==-1,
             'actual INITIAL write version/class')
        need(type(request.get('payload')) is bytes and request['payload']==bits.to_bytes(4,'little')+bytes(508),
             'source input bits/immutable zero tail')
        return self.pages.write(request)

    def finish(self):
        need(self.active is not None and not self.stopped,'INITIAL no retained scope')
        p=self.endpoint;root=self.root;t,owner,version,bits=self.active
        try:
            p.set('close_tuple',t);p.set('close_owner',owner);p.set('close_valid',1)
            try:
                while True:
                    root.settle();need(not p.get('fault'),'INITIAL CLOSE source fault')
                    accepted=bool(p.get('close_ready'));root.tick()
                    if accepted:break
            finally:p.set('close_valid',0)
            # Hardware holds and delivers all three receipts through real issuer
            # READYs and waits actual frame_retire_accept. No host event pulse.
            while True:
                root.settle();need(not p.get('fault'),'INITIAL completion/drain fault')
                if not p.get('busy'):break
                need(p.get('event_tuple')==t and p.get('event_owner')==owner,
                     'INITIAL completion scope changed')
                root.tick()
            self.active=None
            return dict(version=version,tuple239=t,owner55=owner,frame_retired=True)
        except BaseException:self.stopped=True;raise
