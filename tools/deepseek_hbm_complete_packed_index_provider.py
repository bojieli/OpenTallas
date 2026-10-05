"""Opt-in actual produced index payload binding to finite SOFTWARE row service.

Historical executor/default sources remain untouched. This companion uses the
actual source compressor/query handlers with a private quantizer binding.
Initial KV remains an explicit decoded fixture; no resident initial image or
physical memory controller/WRACK/CDC qualification is implied.
"""
from types import FunctionType,SimpleNamespace
from dataclasses import dataclass
import struct
import numpy as np
import deepseek_hbm_complete_executor as E
import deepseek_hbm_complete_index_codec as C
from deepseek_hbm_complete_memory import Backpressure

@dataclass(frozen=True)
class RowLease:
    row:int
    epoch:int
    nonce:int
    format_tag:int
    payload_length:int


def descriptor(format_tag,length,epoch):
    if (format_tag,length) not in [(C.PACKED,68),(C.DECODED_F32,512)] or not 0<=epoch<2**64:
        raise ValueError('format/length/generation')
    return struct.pack('<4sBBHQ',b'IKD1',format_tag,0,length,epoch)+bytes(16)


def parse_descriptor(raw):
    if len(raw)!=32 or raw[16:]!=bytes(16):raise ValueError('initialized descriptor sector')
    magic,fmt,flags,length,epoch=struct.unpack('<4sBBHQ',raw[:16])
    if magic!=b'IKD1' or flags or (fmt,length) not in [(C.PACKED,68),(C.DECODED_F32,512)]:
        raise ValueError('tagged source row descriptor')
    return fmt,length,epoch


class PackedIndexStateArray(E.StateArray):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.publications={};self.current_generation={};self.leases={};self.next_nonce=0;self.row_events=[]
    def key(self,idx):return ('KV',self.family,self.source,int(idx))
    def begin_publish(self,idx,value):
        if not isinstance(idx,(int,np.integer)) or not 0<=idx<len(self.base):
            raise ValueError('bounded produced index row')
        if not isinstance(value,C.ProducedRow) or not hasattr(value,'wire_payload'):
            raise ValueError('actual prequant producer payload required; no inverse packing')
        payload=value.wire_payload
        if value.shape!=self.base.shape[1:]:raise ValueError('source row128')
        decoded=C.decode_payload(value.format_tag,payload)
        if not np.array_equal(decoded.view(np.uint32),np.asarray(value).view(np.uint32)):
            raise ValueError('produced payload/value generation mismatch')
        if len(self.publications)+len(self.leases)>=4 or any(p['row']==idx for p in self.publications.values()):
            raise Backpressure('finite joint four row buffers; same row writer ownership')
        epoch=self.memory.next_epoch
        header=descriptor(value.format_tag,len(payload),epoch)
        # Whole initialized sectors: packed68->96, F32512->512. No unpriced
        # byte-mask/RMW claim. Physical fixed slots/controller mapping unbound.
        padded=payload+bytes((-len(payload))%32)
        ticket=self.memory.submit((*self.key(idx),'generation',epoch),write=True,payload=padded,sectors=len(padded)//32)
        self.publications[ticket]={'row':int(idx),'value':np.asarray(value).copy(),'header':header,'committed':False}
        self.row_events.append({'event':'row_payload_accepted','row':int(idx),'epoch':epoch,'format':value.format_tag,'length':len(payload),'hardware_cycle':None})
        return ticket
    def commit_payload(self,ticket):
        p=self.publications.get(ticket)
        if p is None or p['committed']:raise ValueError('stale/duplicate payload commit')
        self.memory.actual_backend_event(ticket);self.memory.consume(ticket);p['committed']=True
        self.row_events.append({'event':'software_row_payload_visible','row':p['row'],'epoch':ticket.epoch,'hardware_cycle':None})
    def publish_descriptor(self,ticket):
        p=self.publications.get(ticket)
        if p is None or not p['committed']:raise ValueError('payload not actually committed')
        idx=p['row']
        if any(lease.row==idx for lease in self.leases.values()):raise Backpressure('old generation consumers retain row lease')
        # transact returns only after this descriptor's actual backing commit
        # and consumption. Other independent rows may still own tickets; the
        # whole-operation fence belongs to the executor, not this row ACK.
        self.memory.transact((*self.key(idx),'descriptor'),write=True,payload=p['header'])
        old=self.current_generation.get(idx);self.current_generation[idx]=ticket.epoch
        self.base[idx]=p['value'];self.written.add(idx);del self.publications[ticket]
        if old is not None:
            oldkey=(*self.key(idx),'generation',old);del self.memory.values[oldkey];self.memory.epochs.pop(oldkey,None)
        self.row_events.append({'event':'software_descriptor_visible','row':idx,'epoch':ticket.epoch,'hardware_cycle':None})
    def __setitem__(self,idx,value):
        ticket=self.begin_publish(idx,value);self.commit_payload(ticket);self.publish_descriptor(ticket)
    def acquire(self,idx):
        if idx not in self.written:raise ValueError('produced row not published')
        if len(self.leases)+len(self.publications)>=4:raise Backpressure('finite joint four row buffers')
        fmt,length,epoch=parse_descriptor(self.memory.transact((*self.key(idx),'descriptor')))
        if self.current_generation[idx]!=epoch:raise ValueError('descriptor generation mismatch')
        payload=self.memory.transact((*self.key(idx),'generation',epoch))
        if len(payload)!=((length+31)//32)*32 or payload[length:]!=bytes(len(payload)-length):
            raise ValueError('actual returned row length/padding mismatch')
        lease=RowLease(int(idx),epoch,self.next_nonce,fmt,length);self.next_nonce+=1;self.leases[lease.nonce]=lease
        self.row_events.append({'event':'row_consumer_acquired','row':int(idx),'epoch':epoch,'hardware_cycle':None})
        return lease,payload[:length]
    def release(self,lease):
        if self.leases.get(lease.nonce)!=lease:raise ValueError('stale/duplicate row consumer')
        del self.leases[lease.nonce]
        self.row_events.append({'event':'row_consumer_done','row':lease.row,'epoch':lease.epoch,'hardware_cycle':None})
    def __getitem__(self,idx):
        if isinstance(idx,(int,np.integer)):
            if not 0<=idx<len(self.base):raise ValueError('bounded produced index row')
            if int(idx) in self.written:
                lease,payload=self.acquire(int(idx))
                try:return C.decode_payload(lease.format_tag,payload)
                finally:self.release(lease)
            return super().__getitem__(idx)
        ids=np.asarray(list(range(*idx.indices(len(self.base)))) if isinstance(idx,slice) else idx)
        if not np.issubdtype(ids.dtype,np.integer):raise ValueError('integer index IDs')
        return np.asarray([self[int(i)] for i in ids.reshape(-1)],np.float32).reshape(*ids.shape,128)


class PackedIndexExecutor(E.Executor):
    """Explicit opt-in subclass, no default activation or checkpoint launch."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.packed_index_producer=C.ProducerBinding()
        for source,old in list(self.st.ik.items()):
            if old.written:raise ValueError('bind before first source index producer')
            self.st.ik[source]=PackedIndexStateArray(old.base,self.memory,'ik',source)
        for name in ['f_compressor','f_index_q']:
            original=self.bound_handlers[name]
            v=SimpleNamespace(**vars(original.__globals__['V']))
            v.qdq_fp4_e8m0=self.packed_index_producer.qdq_fp4_e8m0
            self.bound_handlers[name]=FunctionType(original.__code__,{**original.__globals__,'V':v},
                                                   original.__name__,original.__defaults__,original.__closure__)
    def f_index_scores(self,rk,op):
        import deepseek_hbm_complete_index_consumer as Consumer
        n,source=op['n'],op['src']
        if self.st.n[source]<n:raise ValueError('index before row publication')
        ids=self.owned(rk,n);q=rk.get('iqf').reshape(32,128);w=rk.get('iw')
        # CPU source fallback must retain the source's full macro shape. Read
        # through finite row service, then cache produced copies in software.
        # This full-rank cache is not RF/shared memory or a GPU admission claim.
        tiles=[self.st.ik[source][ids[start:start+64]] for start in range(0,len(ids),64)]
        keys=np.concatenate(tiles) if tiles else np.empty((0,128),np.float32)
        scores,receipt=Consumer.route_scores(q,keys,w,self.warp_backend,ids)
        receipt.update(pc=None if self.current is None else self.current['pc'],rank=rk.r,rows=len(ids),
                       physical_provider_bound=False)
        self.index_receipts.append(receipt)
        rk.put('is_i',ids.astype(np.int64),n=len(ids));rk.put('is_v',scores,n=len(ids))
