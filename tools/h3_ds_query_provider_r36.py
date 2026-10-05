"""Native compound query fields through finite addressed software writer/read.
All field backing completes BEFORE parent iqf publication; no invented ACK.
Emitted U32 two's-complement exponents are explicitly sign-extended for
I64 consumers; capacity charged by actual emitted dtype.
"""
import hashlib
import math
import numpy as np
from hbm_bound_event_journal_r30 import BoundSectorProvider
from hbm_provider_microvm_r21 import Storage,Tensor
from h3_ds_checkpoint_provider_r30 import RF_BYTES
from h3_ds_history_provider_r36 import HistoryMixin
from h3_ds_checkpoint_provider_r34 import Provider as Base
from ds_hbm_history_codec_r36 import decode

class SizedSlice:
    """Count a retained disk range without materializing its events."""
    def __init__(self,source):self.source=source
    def __len__(self):return self.source.end-self.source.start
    def __iter__(self):return iter(self.source)

class SizedEvents:
    def __init__(self,source):self.source=source
    def __getattr__(self,name):return getattr(self.source,name)
    def __len__(self):return len(self.source)
    def __iter__(self):return iter(self.source)
    def __getitem__(self,index):
        value=self.source[index]
        return SizedSlice(value) if isinstance(index,slice) else value

class SizedRF(dict):
    def __init__(self,source):
        super().__init__()
        for rank,value in source.items():self[rank]=value
    def __setitem__(self,rank,value):
        if not isinstance(value.events,SizedEvents):value.events=SizedEvents(value.events)
        super().__setitem__(rank,value)

class QueryMixin:
    def __init__(self,manifest,*args):
        super().__init__(manifest,*args);self.rf=SizedRF(self.rf);self.query_homes={};self.query_visible={}
        occupied={}
        for b in manifest['query_field_homes']['rows']:
            key=(b['version'],b['rank'],b['field']);lo=b['base'];hi=lo+b['reservation_bytes']
            if key in self.query_homes or b['generation']!=self.generation or lo<33554432+manifest['query_field_homes']['original_reserved_bytes_per_rank'][str(b['rank'])] or hi>67108864:raise ValueError('finite query home identity/bounds')
            if any(lo<end and start<hi for start,end in occupied.get(b['rank'],[])):raise ValueError('query home overlap')
            occupied.setdefault(b['rank'],[]).append((lo,hi));self.query_homes[key]=b

    def _query_access(self,identity,field,array=None):
        v=identity['version'];rank=identity['rank'];b=self.query_homes[v,rank,field]
        if rank not in self.state:self.state[rank]=BoundSectorProvider({('DeepSeek',rank):[dict(base=33554432,bytes=33554432)]},journal_budget=self.journal_budget,allocation_identity={'address_class':'native_state_and_query','rank':rank})
        p=self.state[rank];s=Storage(p,'DeepSeek',rank,33554432,33554432);s.pc=identity['PC'];s.epoch=identity['generation'];n=b['bytes']//4;t=Tensor('DeepSeek',rank,b['base'],(n,),'U32')
        if array is not None:
            words=np.ascontiguousarray(array).view(np.uint32).reshape(-1)
            for off in range(0,n,128):s.write(t,off,words[off:off+128])
            if p.live or p.queue or p.calendar or p.resident:raise ValueError('actual query backing/reverse terminal not drained')
        else:
            words=np.empty(n,np.uint32)
            for off in range(0,n,128):words[off:off+128]=s.read(t,np.arange(off,min(off+128,n)))
            out=words.view({'U32':np.uint32,'I64':np.int64}[b['dtype']]).reshape(b['shape']);out.flags.writeable=False;return out

    def publish(self,identity,fields,source_store_view):
        compound=set(fields)!={'data'}
        if not compound:return super().publish(identity,fields,source_store_view)
        ops=[o for o in self.native['instructions'] if o['pc']==identity['PC']]
        if len(ops)!=1 or ops[0]['family']!='index_q' or source_store_view['result']!='iqf' or set(fields)!={'data','query_codes','query_exp'}:raise ValueError('exact native query compound fields')
        if identity['generation']!=self.generation or self._leased(identity['version']) or (identity['version'],identity['rank']) in self.query_visible:raise ValueError('query generation/retained ownership')
        writes=[w for w in ops[0]['writes'] if w['version']==identity['version']]
        if len(writes)!=1 or writes[0]['native_result_binding']!=source_store_view:raise ValueError('query source writer identity')
        data=fields['data']
        if data.dtype!=np.float32 or data.shape!=(32,128):raise ValueError('source iqf shape/type')
        for field in ('query_codes','query_exp'):
            b=self.query_homes[identity['version'],identity['rank'],field];a=fields[field]
            if (b['PC'],b['generation'])!=(identity['PC'],identity['generation']) or list(a.shape)!=b['shape'] or a.dtype!={'U32':np.uint32,'I64':np.int64}[b['dtype']]:raise ValueError('source query field shape/dtype/identity')
        if not np.array_equal(decode(fields['query_codes'],fields['query_exp'].view(np.int32).astype(np.int64) if fields['query_exp'].dtype==np.uint32 else fields['query_exp'],'FP4E8').view(np.uint32),data.view(np.uint32)):raise ValueError('query codec/data bit identity')
        # Repeat the base's pre-write RF identity/alias/coverage checks before
        # private field writes, so malformed main admission has no side effect.
        proposed=set();covered=set();idx=np.arange(data.size);rank=identity['rank'];version=identity['version']
        if not identity['home_indices']:raise ValueError('query parent concrete home')
        for i in identity['home_indices']:
            h=self.homes[i]
            if h['version']!=version or rank not in h['rank_group'] or h['home']['class']!='RF':raise ValueError('query parent source RF identity')
            sm=h['SM'];proposed.update((sm,slot) for slot in range(h['home']['slot_first'],h['home']['slot_first']+h['home']['vectors']));block=(idx%5120)//256 if h['partition']=='HC_plane_dimension' else idx//256;chosen=idx[block%32==sm]
            if len(chosen)!=h['word_count'] or len(chosen)>h['home']['vectors']*128 or covered.intersection(chosen.tolist()):raise ValueError('query parent source scatter capacity/duplicate')
            covered.update(chosen.tolist())
        if covered!=set(range(data.size)):raise ValueError('query parent complete source scatter')
        for (lv,lr),loc in self.locations.items():
            if lr!=rank or lv==version or loc.get('kind')=='state_fragment':continue
            occupied={(self.homes[i]['SM'],slot) for i in loc['indices'] for slot in range(self.homes[i]['home']['slot_first'],self.homes[i]['home']['slot_first']+self.homes[i]['home']['vectors'])}
            if proposed&occupied:raise ValueError('query parent aliases retained RF version')
        for field in ('query_codes','query_exp'):self._query_access(identity,field,fields[field])
        if rank not in self.rf:
            self.rf[rank]=BoundSectorProvider({('DeepSeek',rank):[dict(base=0,bytes=RF_BYTES)]},journal_budget=self.journal_budget,allocation_identity={'address_class':'RF','rank':rank})
        if not isinstance(self.rf[rank].events,SizedEvents):self.rf[rank].events=SizedEvents(self.rf[rank].events)
        receipt=super().publish(identity,{'data':data},source_store_view)
        receipt['payload_sha256']={name:hashlib.sha256(a.tobytes()).hexdigest() for name,a in fields.items()}
        self.query_visible[version,rank]=dict(identity)
        receipt['query_field_home_bindings']={name:self.query_homes[version,rank,name] for name in ('query_codes','query_exp')}
        return receipt

    def _read_one(self,op,owned,key,bindings,generation,collective=None):
        query={name:b for name,b in bindings.items() if op['family']=='index_scores' and name in ('query_codes','query_exp')}
        if not query:return super()._read_one(op,owned,key,bindings,generation,collective)
        for name,b in query.items():
            if generation!=self.generation or (b['version'],owned['rank']) not in self.query_visible:raise ValueError('visible compound query source version required')
        result=super()._read_one(op,owned,key,{n:b for n,b in bindings.items() if n not in query},generation,collective)
        for name,b in query.items():
            identity=self.query_visible[b['version'],owned['rank']];a=self._query_access(identity,name)
            if name=='query_exp' and a.dtype==np.uint32:
                a=a.view(np.int32).astype(np.int64);a.flags.writeable=False
            spec=self.native['templates'][key]['providers'][name]
            if list(a.shape)!=spec['shape']:raise ValueError('exact query consumer LOAD shape')
            result[name]=dict(field=name,rank=owned['rank'],generation=generation,kind='versioned_operand',data=a,version=b['version'],view_contract=b['native_address_view'],leased_versions=[b['version']],provenance_certified=True)
        return result

    def drain(self,generation):
        super().drain(generation)
        if self.history.pending or self.history.leases:raise ValueError('retained history append/reader debt')
        for engine in list(self.state.values())+list(self.rf.values()):
            if engine.live or engine.queue or engine.calendar or engine.resident:raise ValueError('actual addressed completion debt')
            engine.events.flush()

    def release_version(self,version,generation):
        super().release_version(version,generation)
        for key in list(self.query_visible):
            if key[0]==version:del self.query_visible[key]

class Provider(QueryMixin,HistoryMixin,Base):pass

def create_provider(manifest,native,dispatch,homes):return Provider(manifest,native,dispatch,homes)
