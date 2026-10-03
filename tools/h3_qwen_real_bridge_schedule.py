#!/usr/bin/env python3
"""Canonical Qwen1737 controller joined to hardware-only native/provider I/O.

The bounded controller supplies loops/addresses/recipes. Every numerical
primitive and RF/HBM/NoC/KV publication or retirement must return bridge
receipts. There is no numerical fallback, expected-token input or CPU clock.
"""
import collections
import hashlib
import importlib.util
import json
import base64
import socket
import sqlite3
import struct
import weakref
from pathlib import Path


def require(ok, why):
    if not ok: raise ValueError(why)


def wire_encode(value):
    if isinstance(value, bytes):
        return {'$bytes':base64.b64encode(value).decode('ascii')}
    if isinstance(value, dict):return {k:wire_encode(v)for k,v in value.items()}
    if isinstance(value, (list,tuple)):return [wire_encode(v)for v in value]
    # Control immediates can be NumPy scalars, never array arithmetic callbacks.
    if type(value).__module__.startswith('numpy') and hasattr(value,'item'):return value.item()
    return value


def wire_decode(value):
    if isinstance(value,dict):
        if set(value)=={'$bytes'}:return base64.b64decode(value['$bytes'],validate=True)
        return {k:wire_decode(v)for k,v in value.items()}
    if isinstance(value,list):return [wire_decode(v)for v in value]
    return value


class SocketBridge:
    """Connect to an already-running bridge; never launch or emulate RTL.

    Frames are uint64 big-endian byte length followed by UTF-8 JSON. Binary
    captures are lossless base64. The endpoint serves capabilities then the
    exact ordered commands below. The receipt file retains rejected responses.
    No expected output/token/golden is sent to the endpoint.
    """
    def __init__(self,path,program_sha256,receipt_path):
        self.socket=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.journal=Path(receipt_path).open('xb')
        try:
            self.socket.connect(str(path))
            self.caps=self.exchange({'kind':'capabilities','program_sha256':program_sha256})
            require(self.caps.get('program_sha256')==program_sha256,'backend canonical program source pin')
        except BaseException:
            self.close();raise
    def receive(self,n):
        chunks=[]
        while n:
            part=self.socket.recv(min(n,65536))
            require(part,'bridge disconnected before complete frame')
            chunks.append(part);n-=len(part)
        return b''.join(chunks)
    def exchange(self,command):
        raw=json.dumps(wire_encode(command),sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        self.socket.sendall(struct.pack('!Q',len(raw))+raw)
        length=struct.unpack('!Q',self.receive(8))[0]
        raw=self.receive(length)
        # Persist before validation, including a malformed or rejected receipt.
        self.journal.write(struct.pack('!Q',length)+raw);self.journal.flush()
        return wire_decode(json.loads(raw))
    def capabilities(self):return self.caps
    def transact(self,command):return self.exchange(command)
    def close(self):
        self.socket.close();self.journal.close()


class EventIndex:
    """Disk index for complete receipts: no full-token event array in RAM."""
    def __init__(self,path):
        require(not Path(path).exists(),'event index exists; preserve prior execution')
        self.db=sqlite3.connect(path)
        self.db.execute('CREATE TABLE event (id TEXT PRIMARY KEY, body TEXT NOT NULL)')
        self.count=0
    def __contains__(self,key):
        return self.db.execute('SELECT 1 FROM event WHERE id=?',(key,)).fetchone()is not None
    def __getitem__(self,key):
        row=self.db.execute('SELECT body FROM event WHERE id=?',(key,)).fetchone()
        if row is None:raise KeyError(key)
        return wire_decode(json.loads(row[0]))
    def __setitem__(self,key,value):
        self.db.execute('INSERT INTO event VALUES (?,?)',(key,json.dumps(wire_encode(value),sort_keys=True,separators=(',',':'))));self.count+=1
        if self.count%4096==0:self.db.commit()
    def __len__(self):return self.count
    def close(self):self.db.commit();self.db.close()


REQUIRED_PHASES = {
 'pc_admit': ('owner_admit',), 'pc_retire': ('native_complete','consumer_complete','reverse_CDC'),
 'version_admit': ('lease_admit',), 'version_write': ('write_admit','write_ACK','W6_visible'),
 'version_read': ('read_admit','read_capture'), 'version_publish': ('all_writes_visible','metadata_fence'),
 'version_retire': ('all_consumers_complete','reverse_CDC','allcopies_drained'),
 'immutable_read': ('read_admit','read_capture','reverse_CDC'),
 'native': ('native_issue','native_result_capture'),
 'KV_begin': ('writer_admit',), 'KV_write': ('old_tail_capture','sector_write_ACK'),
 'KV_commit': ('bitmap_visible','metadata_visible'), 'KV_acquire': ('reader_admit',),
 'KV_read': ('read_admit','read_capture'), 'KV_done': ('consumer_complete',),
 'shared_stage': ('shared_admit','shared_capture'),
 'shared_release': ('all_native_consumers_complete','shared_reverse')
}


W2_PARAMETERS=dict(NC=6,MAX_OUT=16,AW=34,CTAGW=32,GENW=4,SIDW=3,PTAGW=35,sector_bits=256,PC_ID_bits=7)
W2_AUTHORITY_PORTS=('p_wr_done_ready','reverse_fenced','repair_busy','provider_fenced','reset_fenced')


def w2_source_files(primary_root,helper_root):
    """Read the supplied actual modules; no copy, modification or compile."""
    paths=dict(
        primary=Path(primary_root)/'rtl/experimental/w2_nc6_primary_20261003/ot_w2_nc6_protected_completion.sv',
        secondary=Path(primary_root)/'rtl/experimental/w2_nc6_secondary_20261003/ot_w2_nc6_coded_secondary.sv',
        codec=Path(primary_root)/'rtl/experimental/w2_nc6_protection_20261003/ot_w2_sealed_secded72.sv',
        correction=Path(helper_root)/'rtl/experimental/w2_nc6_correction_control_20261003/ot_w2_nc6_correction_control.sv')
    return {name:hashlib.sha256(path.read_bytes()).hexdigest()for name,path in paths.items()}


def hbm_sector_demands(kind,body):
    """Exact sector/mask requests from source addresses, never invented tags.

    HBM physical PC/customer32/gen4 allocation is the actual backend's job.
    Writes carry only changed bytes; the backend captures old bytes before
    merging and emits its full256-bit physical sector request. Pure RF has no
    W2 demand. KV metadata traffic is supplied by the installed state owner.
    """
    sectors={}
    def add(rank,address,data=None,count=None):
        for i in range(len(data)if data is not None else count):
            absolute=address+i;base=absolute//32*32;offset=absolute%32
            key=(rank,base);row=sectors.setdefault(key,dict(rank=rank,source_byte_address=base,sector_bytes=32,
                write=data is not None,byte_mask=0,patches=[]))
            row['byte_mask']|=1<<offset
            if data is not None:row['patches'].append([offset,data[i]])
    if kind in ('version_read','version_write'):
        for i,location in enumerate(body.get('locations',[])):
            home=location['home']
            if home[0]!='HBM':continue
            address=home[3]+4*location['lane']
            data=body['payload'][(i%(len(body['payload'])//4))*4:(i%(len(body['payload'])//4))*4+4]if kind=='version_write'else None
            add(home[1],address,data,4)
    elif kind=='immutable_read':
        rank=body.get('rank',body.get('die'))
        for span in body.get('byte_ranges',[]):add(rank,span['address'],count=span['bytes'])
    elif kind in ('KV_read','KV_write'):
        rank=body.get('rank')
        for i,address in enumerate(body.get('addresses',[])):
            add(rank,address,body['payload'][i:i+1]if kind=='KV_write'else None,1)
    return [sectors[key]for key in sorted(sectors,key=lambda k:(str(k[0]),k[1]))]


class BridgeCalendar:
    def __init__(self, backend, native, event_index=None):
        self.backend=backend;self.native=native;self.pc=-1;self.serial=0
        self.events={}if event_index is None else event_index
        self.port_end={};self.owner=None;self.commands=collections.Counter();self.pc_done=[];self.last_completion=None
        self.capabilities=backend.capabilities()
        required=set()
        for op in native['operations']:
            for kernel,n in op['calendar_export']['physical_primitives']['kernel_invocations'].items():
                if n:required.update(native['tile_kernel_ABI'][kernel]['native_counts_per_invocation'])
        require(len(native['operations'])==1737 and native['source_program']['config']['num_hidden_layers']==36,'canonical36layer1737 program required')
        cfg=native['source_program']['config']
        require(all(cfg.get(k)==v for k,v in dict(hidden_size=4096,intermediate_size=12288,
            num_attention_heads=32,num_key_value_heads=8,head_dim=128,vocab_size=151936).items())
            and native['source_program']['context_capacity']==8192,'canonical fullshape provider/compiler input required')
        require([o['pc'] for o in native['operations']]==list(range(1737)),'canonical PC order')
        require(len({o['opcode'] for o in native['operations']})==21,'all21 canonical families')
        require(self.capabilities.get('execution_kind')=='RTL_BRIDGE','actual RTL backend required; CPU primitive callbacks forbidden')
        require(self.capabilities.get('source_pins') and self.capabilities.get('clock_domains'),'source-bound backend and clock domains')
        missing=required-set(self.capabilities.get('native_primitives',[]))
        require(not missing,'unimplemented actual native commands: '+','.join(sorted(missing)))
        methods={'pc_admit','pc_retire','version_admit','version_write','version_read','version_publish','version_retire',
                 'immutable_read','native','KV_begin','KV_write','KV_commit','KV_acquire','KV_read','KV_done',
                 'shared_stage','shared_release'}
        require(methods<=set(self.capabilities.get('methods',[])),'missing actual provider/ACK/W6/KV method')
        require(self.capabilities.get('RF_mirrors')==2 and self.capabilities.get('SMs_per_rank')==32,'actual32SM/twoRF mirror inventory')
        require(self.capabilities.get('RF_slots_per_SM')==512,'actual512slot RF aperture')
        require(self.capabilities.get('max_native_outstanding')==1,'single retained native command credit')
        require(self.capabilities.get('shared_bytes_per_SM')==65536 and self.capabilities.get('shared_transaction_bytes')==64,
                'actual64KiB shared inventory /64B transactions')
    def call(self,kind,body):
        demands=hbm_sector_demands(kind,body)if kind in ('version_read','version_write','immutable_read','KV_read','KV_write')else []
        if demands:
            w2=self.capabilities.get('W2')
            require(w2 and w2.get('parameters')==W2_PARAMETERS,'actual selected NC6/customer32/PTAG35+gen4 W2 contract')
            require(all(w2.get('authority_ports',{}).get(p)=='CONNECTED_ACTUAL_OWNER'for p in W2_AUTHORITY_PORTS),
                    'actual W2 write-ready/reverse/repair/provider/reset authority required; no stubs')
            body=dict(body,W2_sector_demands=demands,W2_parameters=W2_PARAMETERS)
        command={'commandID':self.serial,'PC':self.pc,'kind':kind,'body':body,
                 'depends_on':[]if self.last_completion is None else [self.last_completion],
                 'owner_binding':self.owner};self.serial+=1
        response=self.backend.transact(command)
        require(isinstance(response,dict) and response.get('commandID')==command['commandID'] and response.get('PC')==self.pc,'matched command/PC completion')
        require(response.get('execution_kind')=='RTL_BRIDGE' and response.get('source_pins')==self.capabilities['source_pins'],'receipt actual source identity')
        if self.owner is not None and kind not in ('pc_admit','version_retire'):
            require(response.get('owner_binding')==self.owner,'wrong retained caller owner/completion generation/reset epoch')
        events=response.get('events')
        require(isinstance(events,list) and events,'no zero-service boundary or absent actual events')
        require(set(REQUIRED_PHASES[kind])<=set(e.get('phase')for e in events),'actual method phases missing: '+kind)
        if self.last_completion is not None:
            require(self.last_completion in events[0]['depends_on'],'command issued before preceding causal completion')
        for e in events:
            key=e['eventID'];domain=e['clock_domain'];resource=tuple(e['resource'])
            require(key not in self.events and e.get('accepted') is True,'unique accepted actual event')
            require(domain in self.capabilities['clock_domains'],'bound actual clock domain')
            require(type(e.get('reset_epoch'))is int and e['reset_epoch']==self.capabilities['clock_domains'][domain].get('reset_epoch'),
                    'event actual clock/reset epoch binding')
            require(type(e['start_edge'])is int and type(e['end_edge'])is int and 0<=e['start_edge']<e['end_edge'],'positive hardware edge interval')
            require(all(d in self.events for d in e['depends_on']),'causal producer event missing')
            require(e['start_edge']>=self.port_end.get((domain,resource),0),'physical port contention or premature reuse')
            for d in e['depends_on']:
                parent=self.events[d]
                if parent['clock_domain']==domain:
                    require(e['start_edge']>=parent['end_edge'],'consumer before producer completion')
                else:
                    match=e.get('CDC_match')
                    require(match and match.get('producer_event')==d and match.get('accepted') is True
                        and match.get('sender_domain')==parent['clock_domain'] and match.get('receiver_domain')==domain
                        and match.get('sender_reset_epoch')==parent['reset_epoch']and match.get('receiver_reset_epoch')==e['reset_epoch'],
                        'unmatched cross-clock producer/domain/reset epoch')
            self.events[key]=e;self.port_end[domain,resource]=e['end_edge']
        require(response.get('completion_event') in {e['eventID']for e in events},'causal completion receipt absent')
        for a,b in zip(REQUIRED_PHASES[kind],REQUIRED_PHASES[kind][1:]):
            parent=next(e for e in events if e['phase']==a)
            child=next(e for e in events if e['phase']==b)
            require(parent['eventID'] in child['depends_on'],'ordered actual method phase dependency')
        require(self.events[response['completion_event']]['phase']==REQUIRED_PHASES[kind][-1],'premature command completion phase')
        if 'version' in body:
            require(response.get('version')==body['version'],'wrong source version completion')
        if demands:
            require(response.get('W2_sector_demands')==demands,'W2 completion must cover every source sector/mask')
            transactions=response.get('W2_transactions')
            require(isinstance(transactions,list)and len(transactions)==len(demands),'all actual sector completions required')
            sector_events=set()
            credit_edges=collections.defaultdict(list)
            for demand,txn in zip(demands,transactions):
                require(txn.get('source_byte_address')==demand['source_byte_address']and txn.get('rank')==demand['rank'],
                        'physical translation must retain source sector/rank')
                require(all(type(txn.get(k))is int and 0<=txn[k]<2**width for k,width in
                    [('PC_ID',7),('client',3),('customer_tag',32),('generation',4),('physical_tag',35),('physical_address',34)])
                    and txn['client']<6,'actual physical tag/address/customer allocator widths')
                require(txn.get('accepted_event')in self.events and txn.get('completion_event')in self.events,
                        'W2 acceptance/completion must be actual calendar events')
                accepted=self.events[txn['accepted_event']];completed=self.events[txn['completion_event']]
                require(accepted['eventID']not in sector_events and completed['eventID']not in sector_events
                    and accepted['eventID']!=completed['eventID'],'one event cannot pay multiple W2 sectors/phases')
                sector_events.update((accepted['eventID'],completed['eventID']))
                require(accepted['phase']=='W2_p_req_accept'and completed['phase']==
                    ('W2_p_wr_done_accept'if demand['write']else'W2_p_rsp_accept')
                    and accepted['eventID']in completed['depends_on'],'source physical request/completion causal W2 service')
                require(accepted['clock_domain']==completed['clock_domain']and accepted['end_edge']<=completed['start_edge'],
                        'actual W2 primary-clock causal service interval')
                capture_phase='read_capture'if not demand['write']else'write_ACK'if kind=='version_write'else'sector_write_ACK'
                capture_event=next(e for e in events if e['phase']==capture_phase)
                require(completed['eventID']in capture_event['depends_on'],
                        'physical W2 completion before actual read/write capture')
                credit_edges[txn['PC_ID'],txn['client']].extend([(accepted['start_edge'],1),(completed['end_edge'],-1)])
                require(txn.get('generation_echo')==txn['generation']and txn.get('customer_echo')==txn['customer_tag'],
                        'full separate gen4/customer32 completion echo')
                require(txn.get('reverse_owner_retained')is True and txn.get('repair_authority_bound')is True,
                        'actual W2 repair/backpressure/reverse owner lifetime')
                if demand['write']:
                    require(txn.get('p_wr_done_v_and_ready_event')==txn['completion_event']
                        and txn.get('old_sector_capture_event')in self.events,
                        'old-sector capture and held p_wr_done_ready ACK required')
            for edges in credit_edges.values():
                live=0
                for _,delta in sorted(edges):
                    live+=delta
                    require(0<=live<=16,'actual NC6 MAX16 finite outstanding credit exhaustion')
                require(live==0,'unretired physical W2 transactions')
        self.commands[kind]+=1
        self.last_completion=response['completion_event']
        return response
    def enter_pc(self,op):
        require(op['pc']==len(self.pc_done) and set(op['dependencies'])<=set(self.pc_done),'actual emitted DAG admission')
        self.pc=op['pc']
        response=self.call('pc_admit',{'family':op['opcode'],'attributes':op['attributes'],'reads':op['reads'],'writes':op['writes'],
            'providers':op['provider_binding'],'dependencies':op['dependencies']})
        owner=response.get('owner_binding')
        require(owner and owner.get('retained') is True,'actual caller owner allocation required')
        require(all(type(owner.get(k))is int and 0<=owner[k]<2**w for k,w in [('owner46',46),('native_tag64',64),('generation64',64),('reset_epoch',64)]),'actual retained owner field widths')
        self.owner=owner
    def finish_pc(self,op):
        r=self.call('pc_retire',{'family':op['opcode'],'reads':op['reads'],'writes':op['writes']})
        require(r.get('native_complete') and r.get('consumer_complete') and r.get('reverse_CDC_complete'),'native/consumer/reverse completion before PC retirement')
        self.pc_done.append(op['pc']);self.owner=None


def attach(module, native, backend, event_index=None):
    """Construct actual-I/O subclasses without changing pinned source globals."""
    import numpy as np
    calendar=BridgeCalendar(backend,native,event_index)
    captured=[]
    immutable_receipt={}
    source_owners={}
    provider_ranks={e['provider_ref']:allocation['rank']for allocation in native['provider_binding']['allocation']
        for e in allocation['extents']}
    class CaptureWords(np.ndarray):
        """Keep physical capture identity when control extracts one word."""
        def __array_finalize__(self,parent):self.bridge_origin=getattr(parent,'bridge_origin',None)
        def __getitem__(self,key):
            value=super().__getitem__(key)
            if not isinstance(value,np.ndarray):value=np.asarray(value).view(CaptureWords)
            def index(k):
                if isinstance(k,slice):return dict(slice=[k.start,k.stop,k.step])
                if isinstance(k,tuple):return [index(v)for v in k]
                if isinstance(k,np.ndarray):return k.tolist()
                return k.item()if hasattr(k,'item')else k
            value.bridge_origin=dict(parent=self.bridge_origin,selection=index(key))
            return value
    def capture(value,response):
        # Keep identities while the bounded controller holds their words;
        # never retain every prior tile/primitive result for a whole PC.
        captured[:]=[(ref,event)for ref,event in captured if ref()is not None]
        value=np.asarray(value).view(CaptureWords)
        value.bridge_origin=dict(capture_event=response['completion_event'],dtype=value.dtype.str,shape=list(value.shape))
        captured.append((weakref.ref(value),response['completion_event']))
        return value
    def origins(value):
        if getattr(value,'bridge_origin',None)is not None:return value.bridge_origin
        a=np.asarray(value)
        for ref,event in reversed(captured):
            backing=ref()
            if backing is None:continue
            if np.shares_memory(a,backing):
                return dict(capture_event=event,byte_offset=a.ctypes.data-backing.ctypes.data,
                            dtype=a.dtype.str,shape=list(a.shape),strides=list(a.strides))
        # NumPy scalar extraction copies bits; match a source-captured scalar
        # by exact bytes, preserving the physical event as a source reference.
        if a.size==1:
            for ref,event in reversed(captured):
                backing=ref()
                if backing is None:continue
                if a.dtype==backing.dtype:
                    found=np.flatnonzero(backing.reshape(-1).view(np.uint8).reshape(-1,a.itemsize)
                        .__eq__(np.frombuffer(a.tobytes(),np.uint8)).all(axis=1))
                    if found.size:return dict(capture_event=event,scalar_word=int(found[0]),dtype=a.dtype.str)
        return dict(source_immediate=True,dtype=a.dtype.str,shape=list(a.shape))
    class Primitive(module.NativePrimitiveVM):
        def primitive(self,op,args,attrs=None,shape=None):
            at={}if attrs is None else attrs
            require(op in calendar.capabilities['native_primitives'],'actual primitive not implemented')
            arrays=[np.asarray(a)for a in args]
            require(all(a.size<=128 for a in arrays),'finite128word primitive spans')
            wire=[{'dtype':a.dtype.str,'shape':list(a.shape),'payload':a.tobytes(),'origin':origins(original)}
                for a,original in zip(arrays,args)]
            require(self.native_step<len(self.literal_steps),'native instruction exceeds source recipe')
            step=self.literal_steps[self.native_step]
            require(step['primitive']==op,'actual primitive differs from source instruction expansion')
            r=calendar.call('native',{'opcode':op,'operands':wire,'attrs':at,'shape':shape,
                'kernel':self.kernel_name,'kernel_call':self.kernel_call,
                'native_step':self.native_step,'source_family':native['operations'][calendar.pc]['opcode'],
                'recipe_source':'canonical microcode/'+self.kernel_name,'literal_source_step':step,
                'source_instruction':native['microcode'][self.kernel_name][step['code_index']],
                'recipe_sha256':hashlib.sha256(json.dumps(native['microcode'][self.kernel_name],sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                'route':'rank_collective'if native['operations'][calendar.pc]['opcode']=='ALL_REDUCE'and op=='FADD'else'native'})
            require(r.get('native_result_capture') and r.get('producer_retained'),'actual lane-local native result capture; no invented per-op RF/W6 roundtrip')
            require(r.get('source_operands_bound'),'native operands must resolve capture or source-literal provenance')
            require(isinstance(r.get('workspace_leases'),list),'actual native workspace lifetime response required')
            for lease in r['workspace_leases']:
                require(lease.get('retained') and type(lease.get('rank'))is int and 0<=lease['rank']<2
                    and type(lease.get('SM'))is int and 0<=lease['SM']<32,'actual workspace rank/SM retained lease')
                if lease.get('class')=='RF':
                    first=lease['slot_first'];count=lease['slots']
                    require(type(first)is int and type(count)is int and count>0 and 0<=first<first+count<=512,
                        'finite actual RF workspace aperture')
                    require(all(('RF',lease['rank'],lease['SM'],slot)not in source_owners
                        for slot in range(first,first+count)),'native workspace aliases entering live source version')
                elif lease.get('class')=='shared':
                    first=lease['byte_base'];size=lease['bytes']
                    require(type(first)is int and type(size)is int and size>0 and 0<=first<first+size<=65536,
                        'finite actual shared workspace aperture')
                else:require(lease.get('class')=='lane_local','bound actual workspace storage kind')
            require(r.get('literal_source_step')==step,'native completion must match ordered source instruction')
            source_op=native['operations'][calendar.pc]
            if source_op['opcode']=='ALL_REDUCE' and op=='FADD':
                rendezvous=[e for e in r['events']if e['phase']=='collective_rendezvous']
                issued=[e for e in r['events']if e['phase']=='native_issue']
                require(len(rendezvous)==1 and rendezvous[0]['eventID']in issued[0]['depends_on']
                    and r.get('collective_source_versions')==source_op['reads']
                    and r.get('collective_ranks_complete')==[0,1] and r.get('atomic_collective_commit'),
                    'actual rank resources/atomic collective rendezvous required')
            require(type(r.get('fault'))is bool,'actual arithmetic fault response required')
            self.fault|=r['fault']
            if r['fault']:self.error_events.append(dict(pc=calendar.pc,op=op,event=r['completion_event']))
            dtype=np.dtype(r['dtype'])
            expected=np.float32 if op in ('FADD','FMUL','DIV','SQRT','FMAX','FMIN','BITCAST_F','I2F','LDEXP')else np.uint32 if op in ('BITCAST_U','FCMP_GT','FCMP_LT','FCMP_EQ','FCMP_NE')else np.int64 if op=='F2I'else None
            require(expected is None or dtype==np.dtype(expected),'actual typed native result width')
            require(dtype in (np.dtype(np.float32),np.dtype(np.uint32),np.dtype(np.int64),np.dtype(np.uint8)),'bound source result word type')
            value=np.frombuffer(r['payload'],dtype=dtype).copy().reshape(r['shape'])
            require(value.size<=128 and (shape is None or list(value.shape)==list(shape)),'actual native result span')
            self.native_step+=1;self.counts[op]+=1;self.word_counts[op]+=value.size
            return capture(value,r)
    class Words(module.TileWords):
        def __init__(self,native):
            nonlocal source_owners
            super().__init__(native);self.actual_leases={};source_owners=self.owners
        def reserve(self,version,position,kind='F32'):
            r=calendar.call('version_admit',{'version':version,'position':position,'dtype':kind,'source_homes':self.values[version]['homes']})
            require(r.get('lease') and r.get('alias_free'),'physical version lease admission')
            super().reserve(version,position,kind)
            self.actual_leases[version]=r['lease']
        def write(self,version,start,values):
            a=np.asarray(values)
            require(a.size<=128 and version in self.live,'bounded reserved actual destination')
            require(a.dtype in (np.dtype(np.float32),np.dtype(np.uint32)),'source output words require actual F32/U32 codec')
            total=2 if self.shapes[version][1]=='winner'else int(np.prod(self.shapes[version][0]))
            require(0<=start and start+a.size<=total,'source destination span aperture')
            locations=[]
            for rank in sorted({h['rank']for h in self.values[version]['homes']}):
                for word in range(start,start+a.size):
                    home,lane=self.key(version,word,rank);locations.append({'home':home,'lane':lane,'word':word})
            r=calendar.call('version_write',{'version':version,'start':start,'dtype':a.dtype.str,'shape':list(a.shape),
                'payload':a.tobytes(),'origin':origins(a),'locations':locations,'lease':self.actual_leases[version],
                'partial_write_old_tail_required':True})
            classes={l['home'][0]for l in locations}
            require(('RF'not in classes or r.get('both_RF_mirrors_ACK'))and
                ('HBM'not in classes or r.get('HBM_sector_ACKs_complete'))and r.get('write_visibility_complete'),
                'actual kind-specific write ACK is not admission')
            require(r.get('lease')==self.actual_leases[version] and r.get('source_homes_bound'),
                    'write completion owner/home lease mismatch')
            # Source owners/shapes remain compiler metadata. Actual payload
            # storage belongs to the bridge, with no CPU activation shadow.
            self.cache=None
        def read_indices(self,version,indices):
            ix=np.asarray(indices,np.int64).reshape(-1)
            require(version in self.published and ix.size<=128,'visible actual source tile')
            total=2 if self.shapes[version][1]=='winner'else int(np.prod(self.shapes[version][0]))
            require(np.all(ix>=0)and np.all(ix<total),'actual source read span aperture')
            locations=[{'home':self.key(version,int(i),self.rank(version))[0],'lane':self.key(version,int(i),self.rank(version))[1],'word':int(i)}for i in ix]
            require(all(self.owners.get(tuple(l['home']))==version for l in locations),'physical source version/home owner')
            r=calendar.call('version_read',{'version':version,'lease':self.actual_leases[version],
                'locations':locations,'worker_rank':self.worker_rank,'worker_SM':self.worker_SM})
            require(r.get('lease')==self.actual_leases[version] and r.get('source_visible') and r.get('source_homes_bound')
                and r.get('mirrors_match'),'actual RF/HBM/NoC provider capture')
            value=np.frombuffer(r['payload'],dtype=np.uint32).copy()
            require(value.size==ix.size,'actual provider span size')
            return capture(value if self.shapes[version][1]in('U32','winner')else value.view(module.F),r)
        def publish(self,version,value=None):
            r=calendar.call('version_publish',{'version':version,'lease':self.actual_leases[version],
                'control_value':value,'source_homes':self.values[version]['homes']})
            require(r.get('lease')==self.actual_leases[version],'publication lease mismatch')
            require(r.get('all_writes_visible') and r.get('metadata_fence_complete'),'actual publication fence required')
            super().publish(version,value)
        def retire(self,pc):
            versions=[v for v in self.live if self.values[v]['retire_pc']==pc]
            for v in versions:
                r=calendar.call('version_retire',{'version':v,'lease':self.actual_leases[v],'source_homes':self.values[v]['homes']})
                require(r.get('lease')==self.actual_leases[v],'reverse owner lease mismatch')
                require(r.get('all_consumers_complete') and r.get('reverse_CDC_complete') and r.get('allcopies_drained'),'source version lease cannot retire early')
                self.actual_leases.pop(v)
            super().retire(pc)
    class KV:
        def __init__(self):self.pc=-1;self.leases={};self.pending={};self.counters=collections.Counter()
        def begin(self,layer,die,position):
            r=calendar.call('KV_begin',dict(layer=layer,die=die,position=position));tag=r['writer_lease'];require(tag not in self.pending,'KV writer alias');self.pending[tag]=dict(r,rank=die);return tag
        def write(self,tag,addresses,codes):
            require(tag in self.pending,'actual admitted KV writer')
            r=calendar.call('KV_write',{'writer_lease':tag,'rank':self.pending[tag]['rank'],
                'addresses':np.asarray(addresses,np.int64).tolist(),'payload':np.asarray(codes,np.uint8).tobytes()})
            require(r.get('old_tail_captured') and r.get('sector_ACKs_complete'),'actual partial KV capture/write ACK')
        def commit(self,tag):
            require(tag in self.pending,'actual KV writer before metadata fence')
            r=calendar.call('KV_commit',{'writer_lease':tag})
            require(r.get('bitmap_visible') and r.get('metadata_visible') and r.get('writer_lock_ordered'),'actual bitmap/metadata publication order')
            self.pending.pop(tag);return r['publication_lease']
        def acquire(self,publication,layer,die,position):
            r=calendar.call('KV_acquire',dict(publication_lease=publication,layer=layer,die=die,position=position));lease=r['reader_lease'];require(lease not in self.leases,'KV reader alias');self.leases[lease]=dict(r,rank=die);return lease
        def read(self,lease,addresses):
            require(lease in self.leases,'actual KV reader lease')
            r=calendar.call('KV_read',{'reader_lease':lease,'rank':self.leases[lease]['rank'],'addresses':np.asarray(addresses,np.int64).tolist()})
            require(r.get('source_visible') and r.get('consumer_lease_retained'),'actual causal KV visibility')
            return capture(np.frombuffer(r['payload'],np.uint8).copy(),r)
        def done(self,lease,stage):
            require(lease in self.leases and stage in('SCORES','PV'),'actual KV consumer phase')
            r=calendar.call('KV_done',{'reader_lease':lease,'stage':stage})
            require(r.get('consumer_complete'),'actual KV consumer completion')
            if r.get('reader_released'):
                require(r.get('both_consumers_complete') and r.get('reverse_CDC_complete'),'both KV consumers before reverse release');self.leases.pop(lease)
    class Immutable:
        def read_tile_bytes(self,record):
            require(record['provider_ref']in provider_ranks,'actual immutable provider rank ownership')
            r=calendar.call('immutable_read',dict(record,rank=provider_ranks[record['provider_ref']]))
            require(r.get('provider_ref')==record['provider_ref'] and r.get('lease')==record['lease'],'actual checkpoint provider identity')
            require(r.get('state')=='visible' and r.get('reverse_grant_ACK'),'actual immutable byte capture/reverse')
            immutable_receipt.clear();immutable_receipt.update(r)
            return r
    class Machine(module.TiledMachine):
        def __init__(self):
            super().__init__(native,module.HBMByteTileProvider(Immutable()))
            self.store=Words(native);self.memory=KV();self.vm=Primitive();self.kernel_calls=0
            self.shared_leases={}
        def provider(self,method,*args):
            value=super().provider(method,*args)
            if isinstance(value,tuple):return tuple(capture(v,immutable_receipt)for v in value)
            return capture(value,immutable_receipt)
        def kernel(self,name,**env):
            self.vm.kernel_name=name;self.vm.kernel_call=self.kernel_calls;self.vm.native_step=0;self.kernel_calls+=1
            self.vm.literal_steps=[dict(code_index=i,primitive_index=j,primitive=primitive)
                for i,step in enumerate(native['tile_kernel_ABI'][name]['steps'])for j,primitive in enumerate(step['native_steps'])]
            result=super().kernel(name,**env)
            require(self.vm.native_step==len(self.vm.literal_steps),'source kernel native expansion incomplete')
            return result
        def execute(self,op):
            calendar.enter_pc(op);self.vm.current_pc=op['pc'];super().execute(op)
            require(not self.shared_leases,'shared landing consumers before native command retirement')
            calendar.finish_pc(op);captured.clear()
        def dot(self,rows,K,S,xreader,wreader,output,output_start,bf16=False,codes=False):
            # Replace source counter-only shared landing with actual finite
            # admission/capture and deferred reverse after consumers complete.
            ticket=None
            def staged(*coordinates):
                nonlocal ticket
                if ticket is not None:release()
                first=calendar.serial
                data=wreader(*coordinates)
                r=calendar.call('shared_stage',dict(source_PC=calendar.pc,coordinates=list(coordinates),
                    source_commands=list(range(first,calendar.serial)),output_version=output,
                    source_shape=list(data.shape),dtype=data.dtype.str,payload=data.tobytes(),
                    useful_bytes=data.nbytes,reserved_double_buffer_bytes=2*data.nbytes,
                    mandatory_64B_write_beats=(data.nbytes+63)//64))
                require(r.get('lease') and r.get('captured_bytes')==data.nbytes and r.get('source_commands_bound'),
                    'actual shared source spans/capture/finite lease')
                beats=r.get('shared_write_events')
                require(isinstance(beats,list)and len(beats)==(data.nbytes+63)//64 and len(set(beats))==len(beats),
                    'each mandatory actual64B shared write transaction required')
                for i,event in enumerate(beats):
                    require(event in calendar.events,'actual shared transaction missing from calendar')
                    physical=calendar.events[event]
                    require(physical['phase']=='shared_write_accept'and physical.get('source_byte_offset')==64*i
                        and physical.get('transfer_bytes')==min(64,data.nbytes-64*i),
                        'shared capture must resolve every physical64B beat/span')
                tail=next(e for e in r['events']if e['phase']=='shared_capture')
                require(set(beats)<=set(tail['depends_on']),'shared capture before all physical write beats')
                ticket=r['lease'];require(ticket not in self.shared_leases,'shared lease alias')
                self.shared_leases[ticket]=r
                return capture(data,r)
            def release():
                nonlocal ticket
                r=calendar.call('shared_release',{'lease':ticket,'source_PC':calendar.pc})
                require(r.get('all_native_consumers_complete') and r.get('reverse_complete'),
                    'shared staging cannot release before actual consumers/reverse')
                self.shared_leases.pop(ticket);ticket=None
            super().dot(rows,K,S,xreader,staged,output,output_start,bf16,codes)
            if ticket is not None:release()
        def run(self,token,position,observer=None):
            require(observer is None,'no numerical oracle callback in bridge execution')
            result=super().run(token,position)
            require(calendar.pc_done==list(range(1737)) and not self.store.live and not self.memory.leases and not self.memory.pending,'complete canonical token retirement')
            result.update(status='PASS_CANONICAL1737_REAL_BRIDGE_TOKEN',actual_bridge_commands=dict(calendar.commands),
                actual_bridge_events=len(calendar.events),backend_source_pins=calendar.capabilities['source_pins'],
                numerical_reference_gate='NOT_RUN_BY_THIS_TRANSPORT',
                hardware_or_timing_credit=False,physical_or_rate_qualification=False)
            return result
    return Machine(),calendar


def load_controller(path, source_sha256):
    raw=Path(path).read_bytes();require(hashlib.sha256(raw).hexdigest()==source_sha256,'pinned bounded controller source')
    spec=importlib.util.spec_from_file_location('canonical_qwen_bridge_controller',path)
    import sys
    prior=list(sys.path)
    try:
        sys.path.insert(0,str(Path(path).resolve().parent))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
    finally:sys.path[:]=prior


def main():
    import argparse
    import gzip
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--native',type=Path,required=True)
    ap.add_argument('--native-sha256',required=True,help='SHA256 of the exact compressed canonical compiler artifact')
    ap.add_argument('--controller',type=Path,required=True)
    ap.add_argument('--controller-sha256',required=True)
    ap.add_argument('--socket',type=Path,required=True,help='Existing hardware bridge endpoint; this command does not build or launch it')
    ap.add_argument('--token',type=int,required=True)
    ap.add_argument('--position',type=int,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--w2-source-root',type=Path,default=Path('/home/ubuntu/w2-pc-exact-completion-model-20261003'))
    ap.add_argument('--w2-helper-root',type=Path,default=Path('/tmp/Hubble-W2-corrector-rescue-20261003'))
    a=ap.parse_args()
    # An exclusive run directory preserves all failed receipts and indices.
    a.out.mkdir(parents=True,exist_ok=False)
    backend=None;index=None
    terminal=dict(status='RUNNING_CANONICAL_BRIDGE_JOIN',PCs_retired=0,physical_or_rate_qualification=False)
    try:
        raw=a.native.read_bytes()
        require(hashlib.sha256(raw).hexdigest()==a.native_sha256,'canonical compiler artifact source pin')
        native=json.loads(gzip.decompress(raw));del raw
        module=load_controller(a.controller,a.controller_sha256)
        index=EventIndex(a.out/'events.sqlite')
        backend=SocketBridge(a.socket,a.native_sha256,a.out/'receipts.frames')
        require(backend.capabilities().get('W2',{}).get('source_sha256')==w2_source_files(a.w2_source_root,a.w2_helper_root),
                'loaded W2 primary/secondary/codec/correction source identity')
        machine,calendar=attach(module,native,backend,index)
        terminal.update(machine.run(a.token,a.position))
        terminal.update(native_sha256=a.native_sha256,controller_sha256=a.controller_sha256,
                        PCs_retired=len(calendar.pc_done),oracle_callbacks=0)
    except BaseException as error:
        terminal.update(status='FAIL_CANONICAL_BRIDGE_JOIN',error_type=type(error).__name__,error=str(error))
        if 'calendar'in locals():terminal.update(PCs_retired=len(calendar.pc_done),failed_PC=calendar.pc,commands=dict(calendar.commands))
        raise
    finally:
        if backend is not None:backend.close()
        if index is not None:index.close()
        (a.out/'terminal.json').write_text(json.dumps(terminal,sort_keys=True,indent=2)+'\n')
    print(json.dumps(terminal,sort_keys=True))


if __name__=='__main__':main()
