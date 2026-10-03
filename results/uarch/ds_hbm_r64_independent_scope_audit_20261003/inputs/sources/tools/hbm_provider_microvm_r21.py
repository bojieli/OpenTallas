"""Opt-in bounded SSA micro-op VM and finite addressed SOFTWARE sector provider.

No source/golden operator callbacks, physical clock, PHY or rate admission.
Provider completion follows its real sparse backing mutation/capture in this
software simulator. Positive provisional ticks never purport to be RTL ACKs.
"""
from dataclasses import dataclass
import heapq,math,struct,itertools
import numpy as np

class Backpressure(RuntimeError):pass
class OwnershipFault(RuntimeError):pass

@dataclass(frozen=True)
class Identity:
    target:str
    rank:int
    epoch:int
    pc:int
    serial:int
    sector:int

@dataclass
class Transaction:
    identity:Identity
    tag:int
    generation:int
    write:bool
    payload:bytes
    state:str='queued'
    returned:bytes=b''
    cancelled:bool=False
    accepted_order:int=0

class SectorProvider:
    """Explicit finite ownership/event simulator; each request is one32Bsector."""
    def __init__(self,extents,*,tags=4,queue=64,write_residence=4,read_ticks=64,write_ticks=80,reverse_ticks=4):
        if min(tags,queue,write_residence,read_ticks,write_ticks,reverse_ticks)<=0:raise ValueError('positive finite capacities/costs')
        self.extents=extents;self.tags=tags;self.qd=queue;self.write_cap=write_residence
        self.read_ticks=read_ticks;self.write_ticks=write_ticks;self.reverse_ticks=reverse_ticks
        self.costs={'admission':2,'forward_CDC':4,'read_service':read_ticks,'write_service':write_ticks,'owner_lookup':12,'held_accept':1,'write_visibility':4,'consume':2,'reverse_CDC':4,'reverse_grant':reverse_ticks,'retire':2}
        self.cost_scope='Positive provisional abstract software ticks; no real DRAM timing or clock claim'
        self.accept_sequence=0;self.backing={};self.live={};self.generations=[0]*tags;self.queue=[];self.events=[];self.calendar=[];self.now=0;self.order=0;self.resident=0;self.faults=[]
        for key,es in extents.items():
            sorted_es=sorted(es,key=lambda e:e['base'])
            for e in sorted_es:
                if e['base']<0 or e['bytes']<=0 or e['base']+e['bytes']>81000000000:raise ValueError('aperture')
            for a,b in zip(sorted_es,sorted_es[1:]):
                if a['base']+a['bytes']>b['base']:raise ValueError('extent alias')
    def log(self,event,t,**kw):
        byte=t.identity.sector*32;local=(byte//512)*128+byte%128
        self.events.append(dict(event=event,tick=self.now,stack=byte//128%4,local_sector31=local//32,identity=t.identity.__dict__,tag=t.tag,generation=t.generation,**kw,hardware=False))
    def aperture(self,key,byte,size):
        if size<0 or not any(e['base']<=byte and byte+size<=e['base']+e['bytes'] for e in self.extents.get(key,[])):raise ValueError('unbound address extent')
    def seed(self,target,rank,byte,payload):
        """Explicit loader bytes only; no implicit initialized checkpoint."""
        if self.live:raise OwnershipFault('loader while owners live')
        self.aperture((target,rank),byte,len(payload))
        for i,v in enumerate(payload):
            sector,off=divmod(byte+i,32);key=(target,rank,sector)
            if key not in self.backing:self.backing[key]=[None]*32
            self.backing[key][off]=v
    def submit(self,identity,write=False,payload=b''):
        if not isinstance(identity,Identity) or not 0<=identity.epoch<2**64 or not 0<=identity.pc<2**32 or identity.serial<0:raise ValueError('identity width')
        if write and len(payload)!=32 or not write and payload:raise ValueError('sector payload')
        self.aperture((identity.target,identity.rank),identity.sector*32,32)
        if len(self.queue)>=self.qd:raise Backpressure('request queue full')
        tag=next((n for n in range(self.tags) if n not in self.live),None)
        if tag is None:raise Backpressure('owner credits retained')
        if any(t.identity==identity for t in self.live.values()):raise OwnershipFault('duplicate live identity')
        self.generations[tag]+=1;self.accept_sequence+=1;t=Transaction(identity,tag,self.generations[tag],write,bytes(payload),accepted_order=self.accept_sequence);self.live[tag]=t;self.queue.append(t)
        self.log('request_accept',t);return t
    def schedule(self,t,kind,delay):
        self.order+=1;heapq.heappush(self.calendar,(self.now+delay,self.order,kind,t))
    def issue(self):
        if not self.queue:return False
        t=self.queue[0]
        if t.write and self.resident==self.write_cap:return False
        key=(t.identity.target,t.identity.rank,t.identity.sector)
        if not t.write and any(x is not t and x.accepted_order<t.accepted_order and x.write and x.state in ('issued','queued') and (x.identity.target,x.identity.rank,x.identity.sector)==key for x in self.live.values()):
            return False # RAW wait; never read uncommitted predecessor bytes.
        if t.write and any(x is not t and x.accepted_order<t.accepted_order and not x.write and x.state in ('issued','queued') and (x.identity.target,x.identity.rank,x.identity.sector)==key for x in self.live.values()):return False
        # Reserve backend write residence BEFORE queue head is removed.
        if t.write:self.resident+=1;self.log('write_residence_reserved',t,resident=self.resident)
        self.queue.pop(0);t.state='issued';self.log('software_owned_issue',t)
        forward=self.costs['admission']+self.costs['forward_CDC']+self.costs['owner_lookup']+self.costs['held_accept']
        if t.write:forward+=self.costs['write_visibility']
        self.log('software_service_phases_reserved',t,phase_costs=dict(self.costs))
        self.schedule(t,'complete',forward+(self.write_ticks if t.write else self.read_ticks));return True
    def step(self):
        self.issue()
        if not self.calendar:
            if self.queue:raise Backpressure('RAW or reservation cannot progress')
            return False
        tick,_,kind,t=heapq.heappop(self.calendar);self.now=tick
        key=(t.identity.target,t.identity.rank,t.identity.sector)
        if kind=='complete':
            if t.write:
                self.backing[key]=list(t.payload);self.resident-=1;t.returned=b'';self.log('software_backing_visible',t)
            else:
                data=self.backing.get(key)
                if data is None or any(v is None for v in data):
                    t.state='quarantine';self.log('uninitialized_read_fault',t);raise OwnershipFault('uninitialized sector')
                t.returned=bytes(data);self.log('software_read_capture',t)
            t.state='held'
        elif kind=='grant':
            if t.state!='reverse':raise OwnershipFault('reverse phase changed')
            t.state='released';self.log('validated_reverse_grant',t);del self.live[t.tag]
        return True
    def wait(self,t):
        while t.state not in ('held','quarantine'):self.step()
        if t.state=='quarantine':raise OwnershipFault('quarantined transaction')
        return t.returned
    def consume(self,t):
        if self.live.get(t.tag) is not t or t.state!='held':raise OwnershipFault('consumer before held return')
        t.state='consumed';self.log('consumer_accept',t)
    def reverse(self,t,identity,tag,generation):
        if self.live.get(tag) is not t or t.state!='consumed' or (identity,tag,generation)!=(t.identity,t.tag,t.generation):
            t.state='quarantine';self.faults.append(t.identity);self.log('reverse_quarantine',t);raise OwnershipFault('wrong/stale reverse owner')
        t.state='reverse';self.log('reverse_credit_accept',t);self.schedule(t,'grant',sum(self.costs[k] for k in ('consume','reverse_CDC','owner_lookup','held_accept','reverse_grant','retire')))
    def cancel(self,t):
        if self.live.get(t.tag) is not t or t.state not in ('queued','issued'):raise OwnershipFault('cancel after immutable held completion')
        t.cancelled=True;self.log('cancel_accept',t)
        if t.state=='queued':
            self.queue.remove(t);t.state='held';t.returned=b'';self.log('cancelled_before_issue',t)
        # An issued write can commit; cancellation is reported, never rollback.
    def finish(self,t):
        self.consume(t);self.reverse(t,t.identity,t.tag,t.generation)
        while t.state!='released':self.step()
    def reset(self):
        if self.live or self.queue or self.calendar or self.resident:raise OwnershipFault('reset before drain')
        self.log_reset={'event':'coordinated_drained_reset','tick':self.now,'hardware':False}

DTYPE={'F32':np.dtype('<f4'),'U32':np.dtype('<u4'),'I64':np.dtype('<i8'),'U8':np.dtype('u1'),'I8':np.dtype('i1')}
@dataclass(frozen=True)
class Tensor:
    target:str
    rank:int
    base:int
    shape:tuple
    dtype:str
    highword_base:int|None=None
    @property
    def count(self):return math.prod(self.shape)

@dataclass(frozen=True)
class CodecLease:
    nonce:int
    key:tuple
    indices:tuple
    generations:tuple
    epoch:int
    pc:int

class Storage:
    def __init__(self,provider,target,rank,base,bytes_,tile=128):
        if not 1<=tile<=128:raise ValueError('finite128lane maximum')
        provider.aperture((target,rank),base,bytes_)
        if base%32 or bytes_%32:raise ValueError('arena sector alignment')
        self.provider=provider;self.target=target;self.rank=rank;self.base=base;self.end=base+bytes_;self.cursor=base;self.tile=tile;self.serial=0;self.epoch=0;self.pc=0;self.peak_lanes=0;self.codec_events=[];self.codec_locks=set();self.codec_versions={};self.codec_generation=0;self.codec_readers={};self.codec_leases={};self.lease_serial=0;self.free_blocks=[];self.allocations={};self.peak_live_bytes=0
    def allocate(self,shape,dtype):
        if any(not isinstance(d,int) or d<0 for d in shape):raise ValueError('nonnegative integer shape required')
        n=math.prod(shape);size=(n*DTYPE[dtype].itemsize+31)//32*32
        # Empty ownership does not allocate or alias the next live arena block.
        if not size:return Tensor(self.target,self.rank,self.end,tuple(shape),dtype)
        base=None
        for j,(address,room) in enumerate(self.free_blocks):
            if room>=size:
                base=address;self.free_blocks.pop(j)
                if room>size:self.free_blocks.append((address+size,room-size))
                break
        if base is None:
            if self.cursor+size>self.end:raise Backpressure('finite arena exhausted')
            base=self.cursor;self.cursor+=size
        t=Tensor(self.target,self.rank,base,tuple(shape),dtype);self.allocations[base]=size
        self.peak_live_bytes=max(self.peak_live_bytes,sum(self.allocations.values()));return t
    def free(self,t):
        if t.base not in self.allocations:return # Immutable external LOAD is not arena storage.
        if self.provider.live:raise OwnershipFault('reuse before all reverse grants')
        size=self.allocations.pop(t.base);self.free_blocks.append((t.base,size))
        merged=[]
        for address,room in sorted(self.free_blocks):
            if merged and merged[-1][0]+merged[-1][1]==address:merged[-1]=(merged[-1][0],merged[-1][1]+room)
            else:merged.append((address,room))
        self.free_blocks=merged
    def identity(self,sector):
        self.serial+=1;return Identity(self.target,self.rank,self.epoch,self.pc,self.serial,sector)
    def transaction(self,sector,write=False,payload=b''):
        t=self.provider.submit(self.identity(sector),write,payload);v=self.provider.wait(t);self.provider.finish(t);return v
    def acquire_split64(self,t,indices):
        ids=tuple(int(i) for i in indices);key=(t.target,t.rank,t.base,t.highword_base)
        if t.highword_base is None or key in self.codec_locks:raise Backpressure('split64 unpublished or writer-owned')
        if any((key,i) not in self.codec_versions for i in ids):raise OwnershipFault('split64 generation absent')
        self.lease_serial+=1;l=CodecLease(self.lease_serial,key,ids,tuple(self.codec_versions[key,i] for i in ids),self.epoch,self.pc)
        self.codec_leases[l.nonce]=l;self.codec_readers[key]=self.codec_readers.get(key,0)+1;return l
    def release_split64(self,lease):
        if self.codec_leases.get(lease.nonce) is not lease:raise OwnershipFault('stale or duplicate codec lease')
        del self.codec_leases[lease.nonce];self.codec_readers[lease.key]-=1
        self.codec_events.append({'event':'split64_actual_consumer_lease_release','tick':self.provider.now,'nonce':lease.nonce,'epoch':lease.epoch,'pc':lease.pc,'hardware':False})
    def read(self,t,indices,lease=None):
        ids=np.asarray(indices,np.int64)
        if len(ids)>self.tile:raise ValueError('tile overcapacity')
        if np.any(ids<0) or np.any(ids>=t.count):raise ValueError('tensor address')
        if (t.target,t.rank)!=(self.target,self.rank):raise ValueError('crossrank requires explicit transport')
        key=(t.target,t.rank,t.base,t.highword_base);own_lease=lease is None
        if key in self.codec_locks:raise Backpressure('split64 pair write lease retained')
        if t.highword_base is not None:
            if t.dtype!='I64':raise ValueError('split64 requires semanticI64')
            if lease is None:lease=self.acquire_split64(t,ids)
            if self.codec_leases.get(lease.nonce) is not lease or lease.key!=key or lease.indices!=tuple(int(i) for i in ids):raise OwnershipFault('wrong codec lease identity')
            if lease.generations!=tuple(self.codec_versions[key,int(i)] for i in ids):raise OwnershipFault('stale codec generation')
            self.codec_events.append({'event':'split64_read_lease_accept','tick':self.provider.now,'epoch':self.epoch,'pc':self.pc,'words':len(ids),'low_base':t.base,'high_base':t.highword_base,'hardware':False})
        self.peak_lanes=max(self.peak_lanes,len(ids));cache={};out=bytearray();width=DTYPE[t.dtype].itemsize
        for i in ids:
            locations=[(t.base+int(i)*width,width)] if t.highword_base is None else [(t.base+int(i)*4,4),(t.highword_base+int(i)*4,4)]
            for byte,partwidth in locations:
                sector,offset=divmod(byte,32)
                if sector not in cache:cache[sector]=self.transaction(sector)
                out.extend(cache[sector][offset:offset+partwidth])
        if t.highword_base is not None:
            self.provider.now+=32 # explicit provisional split/join per bounded tile.
            self.codec_events.append({'event':'split64_joined_consumer_capture','tick':self.provider.now,'epoch':self.epoch,'pc':self.pc,'words':len(ids),'low_base':t.base,'high_base':t.highword_base,'codec_ticks':32,'hardware':False})
        result=np.frombuffer(bytes(out),DTYPE[t.dtype]).copy()
        if t.highword_base is not None and own_lease:self.release_split64(lease)
        return result
    def write(self,t,start,values):
        if (t.target,t.rank)!=(self.target,self.rank):raise ValueError('crossrank requires explicit transport')
        a=np.asarray(values,dtype=DTYPE[t.dtype]).reshape(-1)
        if len(a)>self.tile or start<0 or start+len(a)>t.count:raise ValueError('write tile aperture')
        self.peak_lanes=max(self.peak_lanes,len(a));raw=a.tobytes();byte=t.base+start*DTYPE[t.dtype].itemsize;parts={};key=(t.target,t.rank,t.base,t.highword_base)
        if t.highword_base is not None:
            if t.dtype!='I64' or key in self.codec_locks or self.codec_readers.get(key,0):raise Backpressure('split64 write owner or retained reader')
            self.codec_locks.add(key);self.codec_generation+=1
            self.codec_events.append({'event':'split64_write_lease_accept','tick':self.provider.now,'epoch':self.epoch,'pc':self.pc,'words':len(a),'low_base':t.base,'high_base':t.highword_base,'generation':self.codec_generation,'hardware':False})
        for i,v in enumerate(raw):
            address=byte+i if t.highword_base is None else ((t.base if i%8<4 else t.highword_base)+(start+i//8)*4+i%4)
            sector,off=divmod(address,32);parts.setdefault(sector,{})[off]=v
        for sector,changes in parts.items():
            if len(changes)==32:data=bytearray(changes[i] for i in range(32))
            else:
                sector_key=(t.target,t.rank,sector)
                if sector_key not in self.provider.backing:
                    # Explicit initialized padded destination owned by this arena.
                    self.provider.seed(t.target,t.rank,sector*32,bytes(32))
                data=bytearray(self.transaction(sector)) # actual software RMW read/retire.
                for off,v in changes.items():data[off]=v
            self.transaction(sector,True,bytes(data))
        if t.highword_base is not None:
            self.provider.now+=32
            for i in range(start,start+len(a)):self.codec_versions[key,i]=self.codec_generation
            self.codec_events.append({'event':'split64_both_streams_visible_granted_publication','tick':self.provider.now,'epoch':self.epoch,'pc':self.pc,'words':len(a),'low_base':t.base,'high_base':t.highword_base,'generation':self.codec_generation,'codec_ticks':32,'hardware':False})
            self.codec_locks.remove(key)

class MicroVM:
    """Execute normalized sourceSSA; no macro arithmetic dispatch or reordering."""
    ALIASES={'BITS':'BITCAST_U','FLOAT_BITS':'BITCAST_F','ITOF':'I2F','FTOI':'F2I','CMP_GT':'FCMP_GT','CMP_LT':'FCMP_LT','CMP_EQ':'FCMP_EQ','CMP_NE':'FCMP_NE','MOV':'PACKET_COMMIT'}
    SUPPORTED=set('LOAD CONST RESHAPE SLICE TRANSPOSE CONCAT BROADCAST TAKE SCATTER FADD FMUL DIV SQRT FMAX FMIN FCMP_GT FCMP_LT FCMP_EQ SELECT BITCAST_U BITCAST_F SHR SHL AND OR XOR IADD ISUB IMUL IMOD I2F F2I LDEXP PACKET_COMMIT ASSERT IADD64 SHL64 NEG FCMP_NE FP8_PACK FP8_UNPACK'.split())|set(ALIASES)
    def __init__(self,storage):self.s=storage;self.journal=[];self.registers={};self.primitive_counts={};self.fault=False
    def indexed(self,t,outshape,flat):
        if t.shape==():return self.s.read(t,np.zeros(len(flat),dtype=np.int64))
        coords=np.unravel_index(flat,outshape);pad=len(outshape)-len(t.shape)
        if pad<0:raise ValueError('broadcast rank')
        chosen=[np.zeros(len(flat),np.int64) if dim==1 else coords[pad+j] for j,dim in enumerate(t.shape)]
        return self.s.read(t,np.ravel_multi_index(chosen,t.shape))
    def run(self,program,providers):
        self.registers={};self.s.epoch+=1;last={};outputs=set(program['outputs'].values())
        for n,ins in enumerate(program['code']):
            for ref in ins.get('src',[]):last[ref]=n
        for pc,i in enumerate(program['code']):
            self.s.pc=program.get('source_pc',0);source_op=i['op'];op=self.ALIASES.get(source_op,source_op);at=i.get('attrs',{});shape=tuple(i['shape']);a=[self.registers[r] for r in i.get('src',[])]
            if op not in self.SUPPORTED:raise NotImplementedError('unsupported normalized micro-op '+op)
            if op=='LOAD':
                t=providers[at['name']]
                if t.shape!=shape or t.dtype!=at['dtype']:raise ValueError('provider shape/codec')
                self.registers[i['dst']]=t;continue
            if op=='RESHAPE':
                if math.prod(shape)!=a[0].count:raise ValueError('reshape size')
                self.registers[i['dst']]=Tensor(a[0].target,a[0].rank,a[0].base,shape,a[0].dtype,a[0].highword_base);continue
            dtype=at.get('dtype') or ('U8' if op=='FP8_PACK' else 'U32' if op in ('BITCAST_U','FCMP_GT','FCMP_LT','FCMP_EQ','FCMP_NE') else 'F32' if op in ('BITCAST_F','FADD','FMUL','DIV','SQRT','FMAX','FMIN','I2F','LDEXP','NEG','FP8_UNPACK') else 'I64' if op in ('F2I','IADD64','SHL64') else (a[1].dtype if op=='SELECT' else a[0].dtype))
            t=program.get('destination_bindings',{}).get(i['dst'])
            if t is None:t=self.s.allocate(shape,dtype)
            elif t.shape!=shape or t.dtype!=dtype:raise ValueError('bound destination shape/codec')
            active_inputs=a[:1] if op in ('SLICE','TRANSPOSE','BROADCAST','CONCAT') else a
            bytes_per_lane=DTYPE[dtype].itemsize+sum(DTYPE[x.dtype].itemsize for x in active_inputs)
            tile_limit=min(self.s.tile,1<<max(0,(1536//bytes_per_lane).bit_length()-1)) # Three reserved512B staging vectors, serialized high/low RF reads.
            for start in range(0,t.count,tile_limit):
                flat=np.arange(start,min(start+tile_limit,t.count),dtype=np.int64)
                if op=='CONST':
                    value=at['bits'] if dtype=='F32' else at['value']
                    def leaves(v):
                        if isinstance(v,list):
                            for item in v:yield from leaves(item)
                        else:yield v
                    items=list(itertools.islice(leaves(value),start,start+len(flat)))
                    if not isinstance(value,list):items=[value]*len(flat)
                    out=np.asarray(items,np.uint32 if dtype=='F32' else DTYPE[dtype])
                    if dtype=='F32':out=out.view(np.float32)
                elif op in ('SLICE','TRANSPOSE','BROADCAST','CONCAT','TAKE','SCATTER'):
                    out=self.movement(op,a,shape,flat,at)
                else:
                    args=[self.indexed(x,shape,flat) for x in a];out=self.execute(op,args,at)
                self.s.write(t,start,out)
                self.primitive_counts[op]=self.primitive_counts.get(op,0)+1
                self.journal.append({'pc':pc,'op':op,'source_op':source_op,'start':start,'lanes':len(flat),'staging_payload_bytes':len(flat)*bytes_per_lane,'staging_capacity_bytes':1536,'tick':self.s.provider.now,'hardware':False})
            self.registers[i['dst']]=t
            dead=[ref for ref in self.registers if last.get(ref,-1)<=pc and ref not in outputs]
            released=[self.registers.pop(ref) for ref in dead]
            live_bases={v.base for v in self.registers.values()}
            for old in released:
                if old.base not in live_bases:self.s.free(old)
        return {k:self.registers[v] for k,v in program['outputs'].items()}
    def movement(self,op,a,shape,flat,at):
        coords=list(np.unravel_index(flat,shape));x=a[0]
        if op=='BROADCAST':return self.indexed(x,shape,flat)
        if op=='SLICE':
            ax=at['axis']%len(x.shape);start,stop,step=slice(at['start'],at['stop'],at['step']).indices(x.shape[ax]);coords[ax]=start+coords[ax]*step
            return self.s.read(x,np.ravel_multi_index(coords,x.shape))
        if op=='TRANSPOSE':
            source=[None]*len(coords)
            for axis,old in enumerate(at['axes']):source[old]=coords[axis]
            return self.s.read(x,np.ravel_multi_index(source,x.shape))
        if op=='CONCAT':
            ax=at['axis']%len(shape);out=np.empty(len(flat),DTYPE[x.dtype]);offset=0
            for src in a:
                mask=(coords[ax]>=offset)&(coords[ax]<offset+src.shape[ax]);sub=[c[mask] for c in coords];sub[ax]=sub[ax]-offset
                if np.any(mask):out[mask]=self.s.read(src,np.ravel_multi_index(sub,src.shape))
                offset+=src.shape[ax]
            return out
        if op=='TAKE':
            idx=a[1];ax=at['axis']%len(x.shape);ic=coords[ax:ax+len(idx.shape)];ids=self.s.read(idx,np.ravel_multi_index(ic,idx.shape) if idx.shape else np.zeros(len(flat),np.int64)).astype(np.int64)
            if np.any(ids<0) or np.any(ids>=x.shape[ax]):raise ValueError('take address')
            sc=coords[:ax]+[ids]+coords[ax+len(idx.shape):];return self.s.read(x,np.ravel_multi_index(sc,x.shape))
        if op=='SCATTER':
            ax=at['axis']%len(x.shape);idx=int(self.s.read(a[1],[0])[0])
            if not 0<=idx<x.shape[ax]:raise ValueError('scatter address')
            out=self.s.read(x,flat);mask=coords[ax]==idx
            if np.any(mask):sub=[c[mask] for j,c in enumerate(coords) if j!=ax];out[mask]=self.s.read(a[2],np.ravel_multi_index(sub,a[2].shape) if sub else np.zeros(np.count_nonzero(mask),np.int64))
            return out
        raise NotImplementedError(op)
    def execute(self,op,a,at):
        with np.errstate(all='ignore'):
            if op in ('FADD','FMUL','DIV','SQRT'):
                if op=='DIV':
                    if np.any(~np.isfinite(a[0])) or np.any(~np.isfinite(a[1])) or np.any(a[1]==0):raise OwnershipFault('DIV source fault')
                    bits=[]
                    for x,y in zip(a[0].astype(np.float32).view(np.uint32),a[1].astype(np.float32).view(np.uint32)):
                        q,fault=divide_bits(int(x),int(y))
                        if fault:raise OwnershipFault('DIV source fault/overflow')
                        bits.append(q)
                    v=np.asarray(bits,np.uint32).view(np.float32)
                else:v=a[0].astype(np.float32)+a[1].astype(np.float32) if op=='FADD' else a[0].astype(np.float32)*a[1].astype(np.float32) if op=='FMUL' else np.sqrt(a[0].astype(np.float32))
                v=v.astype(np.float32);self.fault|=bool(np.any(~np.isfinite(v)))
                if op=='DIV' and np.any(~np.isfinite(v)):raise OwnershipFault('DIV overflow')
                return np.where(v==0,np.float32(0),v) if at.get('canonical_zero',True) else v
            if op in ('FMAX','FMIN'):return (np.maximum if op=='FMAX' else np.minimum)(*a)
            if op.startswith('FCMP'):return {'FCMP_GT':np.greater,'FCMP_LT':np.less,'FCMP_EQ':np.equal,'FCMP_NE':np.not_equal}[op](*a).astype(np.uint32)
            if op=='SELECT':return np.where(a[0]!=0,a[1],a[2])
            if op=='BITCAST_U':return a[0].astype(np.float32).view(np.uint32)
            if op=='BITCAST_F':return a[0].astype(np.uint32).view(np.float32)
            if op=='FP8_PACK':
                value=a[0].astype(np.float32)
                if np.any(~np.isfinite(value)):raise OwnershipFault('nonfinite FP8 pack')
                magnitude=np.abs(value).astype(np.float64);_,ex=np.frexp(magnitude);quantum=np.ldexp(1.,np.maximum(ex-1,-6)-3)
                rounded=np.minimum(np.rint(magnitude/quantum)*quantum,448).astype(np.float32)
                table=fp8_values();code=np.searchsorted(table,rounded).astype(np.uint8)
                return code|np.where((value<0)&(rounded!=0),128,0).astype(np.uint8)
            if op=='FP8_UNPACK':
                codes=a[0].astype(np.uint8)
                if np.any((codes&127)==127):raise OwnershipFault('FP8 NaN backing')
                value=fp8_values()[codes&127]*np.where(codes&128,-1,1)
                return np.where(value==0,np.float32(0),value).astype(np.float32)
            if op=='NEG':return (a[0].astype(np.float32).view(np.uint32)^np.uint32(0x80000000)).view(np.float32)
            if op=='I2F':return a[0].astype(np.float32)
            if op=='F2I':return a[0].astype(np.int64)
            if op=='LDEXP':return np.ldexp(a[0].astype(np.float32),a[1].view(np.int32) if a[1].dtype==np.uint32 else a[1].astype(np.int32)).astype(np.float32)
            if op in ('ASSERT','PACKET_COMMIT'):
                if op=='ASSERT' and not np.all(a[0]):raise OwnershipFault('native assertion '+at.get('reason',''))
                return a[0].copy()
            wide=op in ('IADD64','SHL64') or any(x.dtype==np.int64 for x in a);dtype=np.int64 if wide else np.uint32;x,y=[v.astype(dtype) for v in a]
            if op in ('SHR','SHL','SHL64') and np.any((y<0)|(y>=(64 if wide else 32))):raise ValueError('shift aperture')
            if op=='IMOD' and np.any(y==0):raise OwnershipFault('integer modulo zero')
            return {'SHR':lambda:x>>y,'SHL':lambda:x<<y,'SHL64':lambda:x<<y,'AND':lambda:x&y,'OR':lambda:x|y,'XOR':lambda:x^y,'IADD':lambda:x+y,'IADD64':lambda:x+y,'ISUB':lambda:x-y,'IMUL':lambda:x*y,'IMOD':lambda:x%y}[op]().astype(dtype)


def divide_bits(a,b):
    def finite(x):return (x>>23)&255!=255
    if not finite(a) or not finite(b) or b&0x7fffffff==0:return 0,True
    if a&0x7fffffff==0:return 0,False
    def ratio(x):
        exp=(x>>23)&255;frac=x&0x7fffff
        sig=frac if exp==0 else frac|0x800000
        power=-149 if exp==0 else exp-150
        return (sig<<power,1) if power>=0 else (sig,1<<-power)
    an,ad=ratio(a);bn,bd=ratio(b);n=an*bd;d=ad*bn
    e=n.bit_length()-d.bit_length()
    if (n < d<<e) if e>=0 else (n<<-e < d):e-=1
    def rounded(shift):
        num,den=(n<<shift,d) if shift>=0 else (n,d<<-shift)
        q,r=divmod(num,den)
        return q+(2*r>den or (2*r==den and q&1))
    sign=(a^b)&0x80000000
    if e<-126:
        q=rounded(149)
        return (sign|q if q else 0),False
    q=rounded(23-e)
    if q==1<<24:q>>=1;e+=1
    if e>127:return 0,True
    return sign|((e+127)<<23)|(q&0x7fffff),False


def fp8_values():
    return np.array([np.float32(i/512) if i<8 else np.float32((1+(i%8)/8)*2**((i//8)-7)) for i in range(127)])


def tensor_from_native_binding(home,shape):
    if home.get('semantic_bits')!=64 or home.get('class_')!='HBM_native_workspace':raise ValueError('exact r20 split64 home required')
    if math.prod(shape)*4>home['bytes'] or home['highword_bytes']!=home['bytes']:raise ValueError('r20 word capacity')
    return Tensor('Qwen',home['rank'],home['base'],tuple(shape),'I64',home['highword_base'])
