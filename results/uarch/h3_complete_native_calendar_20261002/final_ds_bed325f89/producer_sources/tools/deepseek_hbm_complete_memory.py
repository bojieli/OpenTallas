"""Finite persistent SOFTWARE memory interface, separate from physical WRACK.

Backend store updates are explicit commit events. They are not DRAM timings or
DUT completion. The same consumer API can bind Einstein's actual backend later.
Logical objects never alias to fit a bounded memory image.
"""
from collections import Counter
from dataclasses import dataclass

class Backpressure(RuntimeError):pass

@dataclass(frozen=True)
class Ticket:
    tag:int
    epoch:int
    key:tuple
    write:bool
    payload:bytes|None

class PersistentMemory:
    def __init__(self,credits=4,sector_limit=16):
        if not 1<=credits<=4 or sector_limit!=16:raise ValueError('frozen finite ingress contract')
        self.credits=credits;self.sector_limit=sector_limit;self.pending={};self.values={};self.epochs={};self.readers=Counter();self.completed={};self.next_epoch=0;self.events=Counter();self.trace=[]
    def event(self,name,t):
        self.events[name]+=1
        if len(self.trace)<256:self.trace.append({'event':name,'tag':t.tag,'epoch':t.epoch,'key':list(t.key)})
    def preload(self,key,payload):
        if key in self.values or self.pending:raise ValueError('initial fixture only, before issue')
        self.values[key]=bytes(payload);self.epochs[key]=-1
    def submit(self,key,*,write=False,payload=None,sectors=1):
        if not isinstance(sectors,int) or not 1<=sectors<=self.sector_limit:raise ValueError('LENMAX16, reject not truncate')
        if payload is not None and len(payload)>sectors*32:raise ValueError('payload exceeds safe command length')
        if write!=(payload is not None):raise ValueError('write payload required/read payload forbidden')
        if len(self.pending)>=self.credits:raise Backpressure('four reserved completion slots')
        if any(t.key==key for t in self.pending.values()) or (write and self.readers[key]):raise Backpressure('same object generation still owned')
        if not write and key not in self.values:raise ValueError('unwritten persistent read')
        tag=next(i for i in range(self.credits) if i not in self.pending)
        t=Ticket(tag,self.next_epoch,key,write,None if payload is None else bytes(payload));self.next_epoch+=1;self.pending[tag]=t;self.event('accepted',t);return t
    def actual_backend_event(self,t):
        if self.pending.get(t.tag)!=t or (t.tag,t.epoch) in self.completed:raise ValueError('stale/duplicate backend event')
        if t.write:
            self.values[t.key]=t.payload;self.epochs[t.key]=t.epoch;result=b'';self.event('software_backing_store_write_commit',t)
        else:
            result=self.values[t.key];self.readers[t.key]+=1;self.event('software_backing_store_read_return',t)
        self.completed[t.tag,t.epoch]=result
    def consume(self,t):
        if self.pending.get(t.tag)!=t or (t.tag,t.epoch) not in self.completed:raise ValueError('completion not committed or wrong generation')
        r=self.completed.pop((t.tag,t.epoch));self.event('consumer_done',t)
        if not t.write:
            self.readers[t.key]-=1
            if not self.readers[t.key]:del self.readers[t.key]
        del self.pending[t.tag];return r
    def transact(self,key,*,write=False,payload=None):
        # Synchronous software provider; finite slots still held through consume.
        n=len(payload) if payload is not None else len(self.values.get(key,b''))
        if n>512:raise ValueError('caller must explicitly chunk >16sectors')
        t=self.submit(key,write=write,payload=payload,sectors=max(1,(n+31)//32));self.actual_backend_event(t);return self.consume(t)
    def write_object(self,key,data):
        data=bytes(data)
        for off in range(0,len(data),512):self.transact((*key,'part',off),write=True,payload=data[off:off+512])
        self.values[(*key,'length')]=str(len(data)).encode()
    def read_object(self,key):
        if (*key,'length') not in self.values:raise ValueError('unpublished object')
        n=int(self.values[(*key,'length')]);return b''.join(self.transact((*key,'part',off)) for off in range(0,n,512))
    def fence(self):
        if self.pending or self.completed or any(self.readers.values()):raise Backpressure('actual commits and all consumers must drain')
        self.events['fence']+=1
    def summary(self):return {'events':dict(self.events),'outstanding':len(self.pending),'trace':self.trace,'timing_cycles':None,'physical_backend_bound':False}

class FiniteCollective:
    def __init__(self):self.memory=PersistentMemory();self.sequence=0;self.events=[]
    def publish(self,kind,segments,consumer):
        # Segment bytes are real produced values, never golden replacements.
        seq=self.sequence;self.sequence+=1
        for rank,data in segments:self.memory.write_object(('collective',seq,rank),data)
        self.memory.fence()
        produced=[(rank,self.memory.read_object(('collective',seq,rank))) for rank,_ in segments]
        result=consumer(produced);self.memory.fence()
        for key in list(self.memory.values):
            if key[:2]==('collective',seq):
                del self.memory.values[key]
                self.memory.epochs.pop(key,None)
        self.events.append({'sequence':seq,'kind':kind,'bytes':sum(len(x) for _,x in produced),'consumer_done':True,'cycles':None})
        return result
