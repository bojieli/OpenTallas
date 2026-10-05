"""Actual byte/lease transport for the unchanged released BoundKVStorage.

The original control methods still check bitmap, packed reader record, address
generation and SCORES/PV ordering. State reads and payload reads return only
RTL-service bytes. Local dictionaries are diagnostic/control indexes, never a
read fallback. All RPCs use the parent delivery's one sequence and fault debt.
"""
from collections.abc import Mapping
from functools import wraps
from types import MethodType
import numpy as np
if __package__:
    from .h4_qwen_released_provider_delivery import require, sha
else:
    from h4_qwen_released_provider_delivery import require, sha


def hold_fault(method):
    @wraps(method)
    def guarded(self, *args, **kwargs):
        try:
            require(not self.delivery.stopped, 'KV client stopped with retained debt')
            return method(self, *args, **kwargs)
        except BaseException:
            self.delivery.stopped = True
            self.delivery.pending = True
            raise
    return guarded


class PhysicalReadWindow(Mapping):
    """Lazy fetch: original control checks execute before payload port access."""
    def __init__(self, client, lease, addresses):
        self.client=client; self.lease=int(lease); self.addresses=np.asarray(addresses)
        self.data=None

    def fetch(self):
        if self.data is not None:
            return
        memory=self.client.memory
        key=memory.leases[self.lease]['key']; layer,rank,position=key
        indexes=[int(x) for x in self.addresses.flat]
        result={}
        # A real source tile of FP8 bytes, finite one-outstanding service.
        for start in range(0,len(indexes),128):
            window=indexes[start:start+128]
            reply=self.client.rpc('kv_payload_read', lease=self.lease, key=list(key),
                                  rank=rank, addresses=window)
            require(reply.get('lease')==self.lease and reply.get('key')==list(key)
                    and reply.get('addresses')==window and reply.get('captured') is True
                    and reply.get('owner_retained') is True, 'actual KV read lease/address capture')
            raw=reply.get('payload')
            require(type(raw) is bytes and len(raw)==len(window), 'actual FP8 byte response length')
            for address,byte in zip(window,raw):
                require((rank,address) not in result or result[rank,address]==byte,
                        'one held KV byte generation')
                result[rank,address]=byte
        self.data=result

    def __getitem__(self,key):
        self.fetch(); return self.data[key]

    def __iter__(self):
        self.fetch(); return iter(self.data)

    def __len__(self):
        self.fetch(); return len(self.data)


class KVStorageDelivery:
    METHODS=('state_read','state_write','begin','write','commit','acquire','read','done')

    def __init__(self, delivery):
        self.delivery=delivery; self.memory=delivery.machine.memory
        require(type(self.memory) is delivery.native_module.BoundKVStorage,
                'exact original BoundKVStorage class, no subclass exception')
        require(not self.memory.pending and not self.memory.leases and not self.memory.published,
                'attach KV before live source transactions')
        self.original={name:getattr(self.memory,name) for name in self.METHODS}
        require(all(name not in self.memory.__dict__ for name in self.METHODS),
                'no predecessor KV byte/control hook')
        self.installed={}; self.attached=False
        self.held_writers={}; self.held_readers={}

    def rpc(self,kind,**request):
        return self.delivery.exchange(kind,**request)

    def state_range(self,rank,offset,count):
        require(rank in self.memory.state and type(offset) is int and type(count) is int,
                'actual state extent selector')
        extent=self.memory.state[rank]
        require(offset>=0 and count>=0 and offset+count<=extent['bytes'], 'physical state byte aperture')
        return extent

    @hold_fault
    def state_read(self,rank,offset,count):
        e=self.state_range(rank,offset,count)
        reply=self.rpc('kv_state_read',rank=rank,address=e['base']+offset,bytes=count)
        require(reply.get('rank')==rank and reply.get('address')==e['base']+offset
                and reply.get('captured') is True, 'matched actual state read')
        raw=reply.get('payload')
        require(type(raw) is bytes and len(raw)==count, 'real state bytes; no zero/local fallback')
        self.memory.counters['state_read_sectors32']+=len(set((e['base']+offset+i)//32 for i in range(count)))
        return raw

    @hold_fault
    def state_write(self,rank,offset,data):
        require(type(data) is bytes, 'source packed state bytes')
        e=self.state_range(rank,offset,len(data))
        reply=self.rpc('kv_state_write',rank=rank,address=e['base']+offset,payload=data)
        require(reply.get('rank')==rank and reply.get('address')==e['base']+offset
                and reply.get('payload_sha256')==sha(data) and reply.get('visible') is True,
                'actual state write/visibility ACK')
        self.original['state_write'](rank,offset,data)

    @hold_fault
    def begin(self,layer,die,position):
        tag=self.original['begin'](layer,die,position)
        key=list(self.memory.pending[tag]['key'])
        self.held_writers[int(tag)]=tuple(key)
        reply=self.rpc('kv_begin',tag=int(tag),key=key)
        require(reply.get('tag')==tag and reply.get('key')==key and reply.get('writer_retained') is True,
                'actual writer reservation')
        return tag

    @hold_fault
    def write(self,tag,addresses,codes):
        a=np.asarray(addresses); c=np.asarray(codes)
        require(a.dtype.kind in 'iu' and c.dtype==np.uint8 and a.shape==c.shape,
                'actual source addresses and packed FP8 codes')
        key=list(self.memory.pending[int(tag)]['key'])
        self.original['write'](tag,addresses,codes)
        require(len(self.memory.pending[int(tag)]['payload'])<=1024,'source shared1024B writer staging')
        raw=c.tobytes()
        reply=self.rpc('kv_stage_write',tag=int(tag),key=key,
                       addresses=[int(x) for x in a.flat],payload=raw)
        require(reply.get('tag')==int(tag) and reply.get('key')==key
                and reply.get('payload_sha256')==sha(raw) and reply.get('staged') is True
                and reply.get('writer_retained') is True,'actual staged KV bytes/held writer')

    @hold_fault
    def commit(self,tag):
        tag=int(tag); state=self.memory.pending[tag]; key=list(state['key'])
        c=self.memory.p['config']; expected=2*(c['num_key_value_heads']//2)*c['head_dim']
        require(len(state['payload'])==expected,'complete original source KV write')
        reply=self.rpc('kv_commit',tag=tag,key=key,bytes=expected)
        require(reply.get('tag')==tag and reply.get('key')==key
                and reply.get('all_writes_visible') is True and reply.get('writer_retained') is True,
                'physical payload commit before publication bitmap')
        fence=self.original['commit'](tag)
        reply=self.rpc('kv_publish',tag=tag,key=key,fence=dict(tag=tag,key=key))
        require(reply.get('tag')==tag and reply.get('key')==key and reply.get('published') is True
                and reply.get('state_visible') is True,'actual payload/state publication')
        del self.held_writers[tag]
        return fence

    @hold_fault
    def acquire(self,fence,layer,die,position):
        lease=self.original['acquire'](fence,layer,die,position)
        key=list(self.memory.leases[lease]['key'])
        self.held_readers[int(lease)]=tuple(key)
        reply=self.rpc('kv_acquire',lease=int(lease),key=key,
                       producer_tag=int(fence['tag']))
        require(reply.get('lease')==lease and reply.get('key')==key
                and reply.get('producer_tag')==int(fence['tag']) and reply.get('owner_retained') is True,
                'actual reader acquisition and producer epoch')
        return lease

    @hold_fault
    def read(self,lease,addresses):
        a=np.asarray(addresses)
        require(a.dtype.kind in 'iu','original typed KV byte addresses')
        require(int(lease) in self.memory.leases,'current source reader lease')
        shadow=self.memory.bytes
        self.memory.bytes=PhysicalReadWindow(self,lease,addresses)
        try:
            # Unchanged BoundKVStorage.read performs physical bitmap/record
            # checks first. Storage.read then sees only actual response bytes.
            return self.original['read'](lease,addresses)
        finally:
            self.memory.bytes=shadow

    @hold_fault
    def done(self,lease,stage):
        lease=int(lease); state=self.memory.leases[lease]; key=list(state['key'])
        require(stage in ('SCORES','PV') and stage not in state['done']
                and (stage!='PV' or 'SCORES' in state['done']), 'original two-consumer order')
        reply=self.rpc('kv_consumer_done',lease=lease,key=key,stage=stage)
        require(reply.get('lease')==lease and reply.get('key')==key and reply.get('stage')==stage
                and reply.get('consumer_accepted') is True and reply.get('reverse_validated') is True,
                'actual consumer completion and reverse')
        self.original['done'](lease,stage)
        if lease not in self.memory.leases:
            reply=self.rpc('kv_reader_release',lease=lease,key=key)
            require(reply.get('lease')==lease and reply.get('key')==key
                    and reply.get('all_consumers_accepted') is True
                    and reply.get('all_reverse_validated') is True
                    and reply.get('all_copies_drained') is True,'actual final reader release')
            del self.held_readers[lease]

    def attach(self):
        require(not self.attached,'attach actual KV byte/control client once')
        for name in self.METHODS:
            handler=getattr(self,name)
            def forward(instance,*args,_handler=handler,**kwargs):
                return _handler(*args,**kwargs)
            bound=MethodType(forward,self.memory)
            self.installed[name]=bound; setattr(self.memory,name,bound)
        self.attached=True
        return self

    def installed_on(self,memory,transport):
        return (self.attached and memory is self.memory and transport is self.delivery.transport
                and all(getattr(memory,name) is method for name,method in self.installed.items()))
