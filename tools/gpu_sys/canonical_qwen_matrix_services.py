"""Finite MATRIX services over actual NC6/W4/scratch interfaces.

No arithmetic/provider emulation or persistent Python backing memory. Buffers
are one transport frame assembled ONLY from actual captured words. Source
ownership/publication/lifetime come from the enclosing hardware authority.
Attach before_edge/after_edge to ONE existing enclosing shared-clock owner.
"""
from collections import OrderedDict
from copy import deepcopy
from tools.gpu_sys.canonical_qwen_transport import W2PrimaryPort
from tools.gpu_sys import canonical_qwen_service_calendar as C




SCRATCH_ALIASES={name:'scratch_'+name for name in
    ('valid','write','ready','addr','wdata','done','done_ready','rdata')}


def scratch_component(shared_pins,execution_rank,execution_SM):
    """Explicit captured GO location in existing64SM portbook, no inference."""
    C.need(type(execution_rank) is int and 0<=execution_rank<2
        and type(execution_SM) is int and 0<=execution_SM<32,'actual captured execution rank/SM')
    return shared_pins.component('sm',execution_rank*32+execution_SM,aliases=SCRATCH_ALIASES)


def pack_GO(identity):
    """Euclid exact tuple239; owner55 remains separate, never packed as a tag."""
    value=0
    for name,width in (('session',64),('source_PC',11),('native_tag',64),('native_generation',64),
            ('rank',1),('SM',5),('output_version_id',11),('range_begin',9),('range_end',10)):
        field=identity.get(name)
        C.need(type(field) is int and 0<=field<2**width,'captured GO field '+name)
        value=(value<<width)|field
    return value



def range_key(rng):
    keys=('rank','SM','output_version_id','range_begin','range_end','owner55')
    widths=(1,5,11,9,10,55)
    C.need(all(type(rng.get(k)) is int and 0<=rng[k]<2**w for k,w in zip(keys,widths)),
           'actual complete bound output-range identity')
    n=rng['range_end']-rng['range_begin']
    C.need(0<n<=32 and rng['range_end']<=512 and rng.get('expected_ACK_bitmap')==(1<<n)-1,
           'all declared pages fit physical32bit ACK aggregation')
    return tuple(rng[k] for k in keys)


class W2ReadPump:
    """One actual outstanding read; each event observes a shared physical edge."""
    def __init__(self):self.phase='idle';self.result=None;self.route=None
    def start(self,route):
        C.need(self.phase=='idle','finite W2 read credit')
        C.need(type(route) is tuple and len(route)==6 and isinstance(route[1],W2PrimaryPort),
               'actual ranked W2 route (rank,port,client,addr34,tag32,gen4)')
        rank,port,client,addr,tag,gen=route
        C.need(type(rank) is int and rank in (0,1) and type(client) is int and 0<=client<6
            and type(addr) is int and 0<=addr<2**34 and addr%32==0
            and type(tag) is int and 0<=tag<2**32 and type(gen) is int and 0<=gen<16,'actual route bounds')
        C.need(port.pending is None and not port.stopped,'caller W2 port already owned/faulted')
        port.pending=(client,addr,tag,gen,False);self.route=route;self.phase='offer';self.result=None
    def before_edge(self):
        if self.phase in ('idle','complete'):return
        rank,w,c,a,t,g=self.route;p=w.ports
        C.need(not p.get('fault'),'actual W2 fault retains pending read')
        p.set_client(c,'c_req_v',int(self.phase=='offer'));p.set_client(c,'c_req_we',0)
        p.set_client(c,'c_req_addr',a);p.set_client(c,'c_req_tag',t);p.set_client(c,'c_req_gen',g)
        p.set_client(c,'c_req_data',0)
        ready=w.authority.completion_ready(c,t,g,False)
        C.need(type(ready) is bool,'actual capture permission')
        p.set_client(c,'c_rsp_rdy',int(ready and self.phase=='response'))
        p.settle();self.accept=self.phase=='offer' and bool(p.get('c_req_rdy')>>c&1)
        self.capture=None;valid=bool(p.get('c_rsp_v')>>c&1)
        if valid:
            C.need(self.phase=='response','response before accepted read')
            C.need((p.get('c_rsp_tag')>>(32*c)&0xffffffff,p.get('c_rsp_gen')>>(4*c)&15)==(t,g),
                   'physical W2 held tag/generation')
            if ready:self.capture=(p.get('c_rsp_data')>>(256*c)&(2**256-1)).to_bytes(32,'little')
        C.need(not p.get('repair_busy') or not (self.accept or self.capture is not None),'repair cannot advance normal read')
        self.reverse=False
        if self.phase=='reverse':
            self.reverse=w.authority.reverse_validated(c,t,g,False)
            C.need(type(self.reverse) is bool,'actual matching physical reverse')
    def after_edge(self):
        if self.phase in ('idle','complete'):return
        _,w,c,*_=self.route
        if self.accept:self.phase='response';w.ports.set_client(c,'c_req_v',0)
        if self.capture is not None:self.result=self.capture;self.phase='reverse';w.ports.set_client(c,'c_rsp_rdy',0)
        if self.reverse:w.pending=None;self.phase='complete'
    def take(self):
        if self.phase!='complete':return None
        result=self.result;self.result=None;self.route=None;self.phase='idle';return result


class ScratchPump:
    """Actual64B scratch command/done, no SRAM-internal access."""
    def __init__(self,pins):self.p=pins;self.phase='idle';self.result=None
    def start(self,address,data=None):
        C.need(self.phase=='idle' and type(address) is int and 0<=address<1024,'scratch finite credit/aperture')
        C.need(data is None or type(data) is bytes and len(data)==64,'scratch64B write')
        self.address=address;self.data=data;self.phase='offer';self.result=None
    def before_edge(self):
        p=self.p;p.set('valid',int(self.phase=='offer'));p.set('done_ready',int(self.phase=='done'))
        if self.phase in ('idle','complete'):return
        p.set('write',int(self.data is not None));p.set('addr',self.address)
        p.set('wdata',0 if self.data is None else int.from_bytes(self.data,'little'))
        p.settle();self.accept=self.phase=='offer' and bool(p.get('ready'))
        self.done=self.phase=='done' and bool(p.get('done'))
        if self.done:self.result=b'' if self.data is not None else p.get('rdata').to_bytes(64,'little')
    def after_edge(self):
        if self.phase in ('idle','complete'):return
        if self.accept:self.phase='done';self.p.set('valid',0)
        if self.done:self.phase='complete';self.p.set('done_ready',0)
    def take(self):
        if self.phase!='complete':return None
        data=self.result;self.result=None;self.phase='idle';return data


class RFWritePump:
    """Actual two-mirror4096bit write and matching held commonACK."""
    def __init__(self,rf):
        from tools.gpu_sys.canonical_qwen_rf_ports import RFPorts
        C.need(isinstance(rf,RFPorts),'actual W4 ACK_ID1 transactor')
        self.rf=rf;self.phase='idle';self.done=False
    def start(self,slot,owner,data):
        C.need(self.phase=='idle' and type(data) is bytes and len(data)==512,'one RF page credit')
        self.rf._begin(slot,owner);self.slot=slot;self.owner=owner;self.data=data;self.phase='offer'
    def before_edge(self):
        p=self.rf.ports;p.set('wr_valid',int(self.phase=='offer'));p.set('ack_ready',int(self.phase=='ACK'))
        if self.phase in ('idle','complete'):return
        self.rf._fault();p.set('wr_addr',self.slot);p.set('wr_owner',self.owner)
        p.set('wr_data',int.from_bytes(self.data,'little'));p.settle()
        self.accept=self.phase=='offer' and bool(p.get('wr_ready'))
        self.ack=self.phase=='ACK' and bool(p.get('ack_valid'))
        if self.ack:C.need((p.get('ack_slot'),p.get('ack_owner'))==(self.slot,self.owner),'matching actual55commonACK')
    def after_edge(self):
        if self.phase in ('idle','complete'):return
        if self.accept:self.phase='ACK';self.rf.ports.set('wr_valid',0)
        if self.ack:self.done=True;self.phase='complete';self.rf.pending=None;self.rf.ports.set('ack_ready',0)
    def take(self):
        if self.phase!='complete':return False
        self.phase='idle';self.data=None;self.done=False;return True


class MatrixPhysicalServices:
    """Actual ports + hardware authority, no positive default callbacks.

    BF16 frames must already be captured by the exact native BF16 recipe;
    this service never rounds values or routes by shape/rank modulo SM.
    The one live weight line remains occupied until real engine consumption.
    Its per-sector capture/reverse takes >=3edges; >=4sectors/line =>12edges,
    followed by actual consumption before next gather. Thus the exclusive
    scratch writer's two-edge cadence can accept the fixed-pipeline row stream.
    A real blocked scratch port faults/retains debt, never drops an engine row.
    """
    REQUIRED=('matrix_begin','matrix_input_binding','matrix_reserve','matrix_lease_live',
        'matrix_weight_route','matrix_x_capture','matrix_weight_consumed','matrix_output_page',
        'matrix_tile_completion','matrix_workspace_release','matrix_whole_completion',
        'matrix_output_ranges','matrix_issuer_workspace_retire')
    def __init__(self,authority,scratch_pins,*,enabled=False):
        C.need(enabled,'finite MATRIX services default off')
        C.need(all(callable(getattr(authority,k,None)) for k in self.REQUIRED),'all actual hardware MATRIX authority bindings required')
        self.a=authority;self.scratch=ScratchPump(scratch_pins);self.w2=W2ReadPump()
        self.line=None;self.returned=None;self.reservation=None;self.seen_rows=set()
        self.RF=None;self.rf_frame=bytearray();self.readrow=0;self.output_ACK=False;self.capture_pending=False
        self.faulted=False;self.origin=None;self.input_rows=None;self.expected_ranges=None
    def install(self,shared_clock_owner):
        C.need(callable(getattr(shared_clock_owner,'add_edge_hook',None)),'existing enclosing shared clock owner required')
        C.need(not getattr(self,'installed',False),'only one MATRIX service edge hook')
        shared_clock_owner.add_edge_hook(self);self.installed=True
        return self

    def before_edge(self):
        C.need(not self.faulted,'MATRIX physical service fault retains debt')
        if self.reservation is not None:C.need(self.a.matrix_lease_live(deepcopy(self.reservation)) is True,'actual retained matrix workspace/source lease')
        self.w2.before_edge();self.scratch.before_edge()
        if self.RF:self.RF.before_edge()
    def after_edge(self):
        self.w2.after_edge();self.scratch.after_edge()
        if self.RF:self.RF.after_edge()
    def begin_operator(self,d):
        # These are sampled hardware rows before backendGO acceptance, not a
        # mapping/ready dictionary synthesized from the source descriptor.
        binding=self.a.matrix_input_binding(deepcopy(d))
        if binding is not None:binding=deepcopy(binding)
        if binding is None:return None
        if binding.get('all_input_leases_bound') is False:return None
        C.need(binding.get('all_input_leases_bound') is True and binding.get('program_sha256')==d['program_sha256']
            and binding.get('source_PC')==d['source_PC'] and type(binding.get('input_rows')) is tuple and bool(binding['input_rows']),
            'actual all-input hardware barrier BEFORE GO')
        expected=binding.get('output_ranges')
        C.need(type(expected) is tuple and bool(expected),'all output-range bindings frozen BEFORE GO')
        C.need(len({range_key(rng) for rng in expected})==len(expected)
            and all(rng.get('source_version')==d['output_version'] for rng in expected),
            'actual full output version/page-range identities')
        origin=self.a.matrix_begin(deepcopy(d),deepcopy(binding))
        if origin is not None:
            C.need(type(origin.get('GO_tuple239')) is int
                and origin['GO_tuple239']==pack_GO(origin['identity']), 'captured239 whole GO equals retained fields')
            C.need(origin.get('input_rows')==binding['input_rows'],'GO retains bound input rows')
            self.origin=deepcopy(origin);self.input_rows=deepcopy(binding['input_rows']);self.expected_ranges=deepcopy(expected)
        return deepcopy(self.origin) if origin is not None else None
    def reserve_tile(self,d):
        C.need(self.reservation is None,'only one tile workspace')
        r=self.a.matrix_reserve(deepcopy(d),deepcopy(self.origin))
        if r is None:return None
        C.need(type(r.get('scratch_base')) is int and 0<=r['scratch_base']<=896
            and r.get('rows')==d['rows'] and r.get('scratch_exclusive') is True and r.get('input_rows')==self.input_rows,
            'actual exclusive128beat scratch reservation/input rows')
        r=deepcopy(r);self.reservation=deepcopy(r);self.seen_rows=set();self.readrow=0;self.rf_frame=bytearray();self.output_ACK=False
        return r
    def _reservation_matches(self,r):
        C.need(r==self.reservation,'captured matrix workspace/source metadata cannot change')

    def capture_x_fragment(self,p,r):
        self._reservation_matches(r)
        C.need(self.a.matrix_lease_live(deepcopy(r)) is True,'live source before x capture')
        frame=self.a.matrix_x_capture(deepcopy(p),deepcopy(r))
        if frame is None:return None
        data=frame['payload'];indices=p['source_K_indices']
        C.need(type(data) is bytes and len(data)==2*sum(k is not None for k in indices),'only actual active BF16 captures')
        active=iter(data[i:i+2] for i in range(0,len(data),2))
        # Explicit inactive source leaves only. No zero source fallback.
        frame=dict(frame,payload=b''.join(b'\x00\x00' if k is None else next(active) for k in indices))
        return frame
    def offer_weight_line(self,tag,p,r):
        self._reservation_matches(r)
        if self.line is not None:return False
        C.need(self.a.matrix_lease_live(deepcopy(r)) is True,'live original weight/provider source')
        groups=OrderedDict()
        for lane,offset in enumerate(p['source_code_byte_offsets']):
            if offset is not None:groups.setdefault(offset//32*32,[]).append((lane,offset%32))
        C.need(len(groups)>=4,'source gather cadence supports physical exclusive scratch capture')
        self.line=dict(tag=tag,plan=p,reservation=r,sectors=list(groups.items()),next=0,
            payload=bytearray(128),phase='read',delivered=False)
        return True
    def poll_weight_line(self,r):
        self._reservation_matches(r)
        line=self.line
        if line is None:return None
        if line['phase']=='consume':
            if self.a.matrix_weight_consumed(line['tag'],line['plan']['line_address'],deepcopy(r)) is True:self.line=None
            return None
        capture=self.w2.take()
        if capture is not None:
            _,positions=line['sectors'][line['next']]
            for lane,offset in positions:line['payload'][lane]=capture[offset]
            line['next']+=1
        if line['next']==len(line['sectors']):
            line['phase']='consume';p=line['plan']
            return dict(tag=line['tag'],line_address=p['line_address'],payload=bytes(line['payload']),
                captured=True,rank=p['rank'],weight_descriptor_sha256=r['weight_descriptor_sha256'])
        if self.w2.phase=='idle':
            sector,_=line['sectors'][line['next']]
            route=self.a.matrix_weight_route(deepcopy(line['plan']),sector,deepcopy(r))
            C.need(route[0]==line['plan']['rank'],'explicit original weight rank route')
            self.w2.start(route)
        return None
    def capture_result(self,row,bits,r):
        self._reservation_matches(r)
        C.need(type(bits) is int and 0<=bits<2**512 and row not in self.seen_rows,'actual result row/width')
        C.need(self.a.matrix_lease_live(deepcopy(r)) is True,'actual output workspace lease')
        self._consume_scratch_done()
        C.need(self.scratch.phase=='idle','real unbackpressured capture cannot use host queue')
        # This drives the actual SRAM write on the SAME shared edge as engine
        # rv. It does not return an SRAM ACK early; completion waits done.
        self.scratch.start(r['scratch_base']+row,bits.to_bytes(64,'little'))
        self.scratch.before_edge()
        C.need(self.scratch.accept,'actual scratch sink not ready; retain fault/debt')
        self.seen_rows.add(row);self.capture_pending=True
        return True
    def _consume_scratch_done(self):
        if self.capture_pending and self.scratch.phase=='complete':
            C.need(self.scratch.take()==b'','actual row write done');self.capture_pending=False
    def completion(self,r):
        self._reservation_matches(r)
        self._consume_scratch_done()
        if self.line is not None and self.line['phase']=='consume':
            self.poll_weight_line(r)
        if self.capture_pending or self.line is not None:return None
        if len(self.seen_rows)!=r['rows']:return None
        if self.readrow<r['rows']:
            data=self.scratch.take()
            if data is not None:
                # Select one existing identical column; compare all captured
                # copies rather than silently ignoring a divergent result.
                word=data[:4];C.need(all(data[i:i+4]==word for i in range(0,64,4)), 'actual duplicated column disagreement')
                self.rf_frame.extend(word);self.readrow+=1
            if self.readrow<r['rows'] and self.scratch.phase=='idle':self.scratch.start(r['scratch_base']+self.readrow)
            return None
        if not self.output_ACK:
            if self.RF is None:
                rf,slot,owner=self.a.matrix_output_page(deepcopy(r))
                C.need(owner<<9|slot==r['identity']['owner55'],'actual output page55 matches captured producer')
                self.RF=RFWritePump(rf)
                # Tail64 page upperwords are padding only in actually reserved
                # fullRFpage; publication bitmap/bounds exclude unused words.
                self.RF.start(slot,owner,bytes(self.rf_frame)+bytes(512-len(self.rf_frame)))
                return None
            if not self.RF.take():return None
            self.output_ACK=True
        receipt=self.a.matrix_tile_completion(deepcopy(r))
        if receipt is not None:C.need(receipt.get('input_rows')==self.input_rows,'tile reverse attributed to retained input rows')
        if receipt is not None:
            C.need(receipt.get('identity')==r['identity'],'tile completion captured producer identity')
            if not all(receipt.get(k) is True for k in ('RF_visible','W4_ACK','W6_retired','reverse_validated')):return None
        return deepcopy(receipt)
    @staticmethod
    def _workspace_only(receipt):
        if receipt is None:return False
        C.need(receipt.get('workspace_released') is True and receipt.get('source_leases_retired') is False,
               'workspace/issuer retirement MUST NOT retire any source RF lease')
        return True
    def release_tile(self,r,receipt):
        self._reservation_matches(r)
        if not self._workspace_only(self.a.matrix_workspace_release(deepcopy(r),deepcopy(receipt))):return False
        self.reservation=None;self.RF=None;self.rf_frame=bytearray();return True
    def whole_completion(self,origin):
        C.need(origin==self.origin,'saved whole GO cannot change')
        ranges=self.a.matrix_output_ranges(deepcopy(self.origin))
        if ranges is None:return None
        C.need(type(ranges) is tuple and bool(ranges),'actual bound output ranges')
        expected={range_key(r):r for r in self.expected_ranges}
        actual={range_key(r):r for r in ranges}
        C.need(len(actual)==len(ranges) and set(actual)<=set(expected),'wrong/duplicate actual output range')
        if set(actual)!=set(expected):return None
        for key,rng in actual.items():
            C.need(rng.get('expected_ACK_bitmap')==expected[key]['expected_ACK_bitmap']
                and rng.get('source_version')==expected[key]['source_version'],'frozen ALL-page publication mask/version')
            C.need(type(rng.get('owner55')) is int and 0<=rng['owner55']<2**55
                and type(rng.get('expected_ACK_bitmap')) is int and 0<rng['expected_ACK_bitmap']<2**32
                and type(rng.get('ACK_bitmap')) is int
                and rng['ACK_bitmap'] & ~rng['expected_ACK_bitmap']==0
                and rng.get('GO_tuple239')==self.origin['GO_tuple239']
                and rng.get('input_rows')==self.input_rows,
                'all actual range-page commonACKs55 + fullengine visible, never firstACK')
            if rng['ACK_bitmap']!=rng['expected_ACK_bitmap'] or rng.get('full_engine_visible') is not True:return None
        receipt=self.a.matrix_whole_completion(deepcopy(self.origin),deepcopy(ranges))
        if receipt is not None:C.need(receipt.get('input_rows')==self.input_rows
                and receipt.get('GO_tuple239')==self.origin['GO_tuple239']
                and receipt.get('identity')==origin['identity'],
                'whole terminal+reverse attributed to captured GO/input rows')
        if receipt is not None and not all(receipt.get(k) is True for k in
            ('all_output_RF_visible','all_W4_ACK','whole_terminal','whole_reverse_validated','source_publication')):return None
        return deepcopy(receipt)
    def release_operator(self,origin,receipt):
        C.need(origin==self.origin and receipt.get('identity')==self.origin['identity']
            and receipt.get('GO_tuple239')==self.origin['GO_tuple239']
            and receipt.get('input_rows')==self.input_rows,'exact whole issuer workspace retirement, no source lease release')
        return self._workspace_only(self.a.matrix_issuer_workspace_retire(deepcopy(self.origin),deepcopy(receipt)))


# Any identity/width/port failure retains all debt and prevents new work.
# No rearm/reset/release cleanup is issued here.
def _retaining_guard(method):
    def guarded(self,*args,**kwargs):
        C.need(not self.faulted,'MATRIX physical service fault retains debt')
        try:return method(self,*args,**kwargs)
        except BaseException:
            self.faulted=True
            raise
    return guarded

for _method in ('before_edge','after_edge','begin_operator','reserve_tile','capture_x_fragment',
    'offer_weight_line','poll_weight_line','capture_result','completion','release_tile',
    'whole_completion','release_operator'):
    setattr(MatrixPhysicalServices,_method,_retaining_guard(getattr(MatrixPhysicalServices,_method)))
