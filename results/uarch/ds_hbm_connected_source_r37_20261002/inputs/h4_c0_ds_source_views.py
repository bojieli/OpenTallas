"""Additive DS source views over the existing addressed provider.

Kepler owns the provider entrypoint and released images. This bridge reads
actual native-state/RF backing, validates its exact sector journals and keeps
source leases. No numerical operator, whole-token or hardware timing credit.
"""
import hashlib,json,math,pathlib
import numpy as np
from h3_ds_checkpoint_provider_r30 import Storage,Tensor,RF_BYTES,RF_SM,CAP,DTYPES
from h4_c0_producer_extents import collective_contract
from h4_c0_provider_movement import prove_sector_span
from hbm_bound_event_journal_r30 import DiskEvents

def digest(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()

class SourceViews:
    def __init__(self,provider,*,native_content_sha256,max_journal_events=8192):
        if digest(canonical(provider.native))!=native_content_sha256:raise ValueError('exact current native content binding required')
        if type(max_journal_events)!=int or not 1<=max_journal_events<=8192:raise ValueError('finite source journal span required')
        self.provider=provider;self.source_sha=native_content_sha256;self.max_events=max_journal_events
        self.receipts=DiskEvents(provider.journal_budget);self.failed=False
    def _check(self):
        if self.failed:raise ValueError('failed source bridge retains evidence; no retry')
        if digest(canonical(self.provider.native))!=self.source_sha:raise ValueError('native source changed after binding')
    def _read_words(self,version,rank,indices,*,field=None):
        p=self.provider;key=(version,rank)
        loc=p.locations.get(key) if field is None else getattr(p,'field_locations',{}).get((version,rank,field))
        if loc is None:raise ValueError('actual addressed source location absent; no cached/zero payload substitute')
        count=math.prod(loc['shape'])*np.dtype(loc['dtype']).itemsize//4
        indices=np.asarray(indices,dtype=np.int64)
        if not 0<len(indices)<=16384 or np.any(indices<0) or np.any(indices>=count):raise ValueError('finite exact owned source word extent')
        if loc.get('kind')=='state_fragment':
            binding=loc['binding']
            if (binding['PC'],binding['version'],binding['rank'])!=(loc['pc'],version,rank) or not 33554432<=binding['base'] or binding['base']+binding['reservation_bytes']>67108864 or count*4>binding['reservation_bytes']:raise ValueError('actual finite state source home identity/extent')
            backing=p.state[rank];storage=Storage(backing,'DeepSeek',rank,33554432,CAP)
            tensor=Tensor('DeepSeek',rank,loc['binding']['base'],(count,),'U32')
            mapped=[(tensor,indices,np.arange(len(indices)))]
        else:
            backing=p.rf[rank];storage=Storage(backing,'DeepSeek',rank,0,RF_BYTES);mapped=[];covered=set()
            all_indices=np.arange(count)
            for index in loc['indices']:
                h=p.homes[index]
                if h['version']!=version or rank not in h['rank_group']:raise ValueError('actual source RF home version/rank mismatch')
                if type(h['SM'])!=int or not 0<=h['SM']<32 or not 0<=h['home']['slot_first'] or h['home']['slot_first']+h['home']['vectors']>512:raise ValueError('actual finite RF source home geometry')
                block=(all_indices%5120)//256 if h['partition']=='HC_plane_dimension' else all_indices//256
                chosen=all_indices[block%32==h['SM']]
                if len(chosen)!=h['word_count']:raise ValueError('actual source RF scatter capacity mismatch')
                mask=np.isin(indices,chosen);dest=np.flatnonzero(mask);positions=np.searchsorted(chosen,indices[mask])
                if covered.intersection(dest.tolist()):raise ValueError('overlapping actual source RF homes')
                covered.update(dest.tolist())
                if len(dest):mapped.append((Tensor('DeepSeek',rank,h['SM']*2*RF_SM+h['home']['slot_first']*512,(len(chosen),),'U32'),positions,dest))
            if covered!=set(range(len(indices))):raise ValueError('source RF home leaves owned words uncovered')
        # Conservative16 events per addressed read sector; price before any
        # request, including repeated sectors at separate128-word batches.
        event_bound=sum(16*len(np.unique(source[first:first+128]//8)) for tensor,source,destination in mapped for first in range(0,len(source),128))
        if event_bound>self.max_events:raise ValueError('finite source journal preflight bound exceeded')
        storage.pc=loc['pc'];storage.epoch=p.generation;start=len(backing.events);output=np.empty(len(indices),np.uint32)
        try:
            for tensor,source,destination in mapped:
                for first in range(0,len(source),128):output[destination[first:first+128]]=storage.read(tensor,source[first:first+128])
            end=len(backing.events)
            if end-start>self.max_events:raise ValueError('finite source journal span exhausted')
            transactions=prove_sector_span(backing.events[start:end],model='DeepSeek',rank=rank,PC=loc['pc'],generation=p.generation)
            if any(row['direction']!='read' for row in transactions) or backing.live or backing.queue or backing.calendar or backing.resident:raise ValueError('actual source read/reverse obligations retained')
            event_digest=hashlib.sha256()
            for event in backing.events[start:end]:
                raw=canonical(event);event_digest.update(len(raw).to_bytes(8,'little')+raw)
            receipt=dict(event='C0_software_source_read_receipt',version=version,rank=rank,generation=p.generation,field=field,producer_PC=loc['pc'],
                journal_path=str(backing.events.path),journal_id=backing.events.id,start=start,end=end,
                event_digest=event_digest.hexdigest(),accepted_sectors=len(transactions),source_words=len(indices),
                payload_sha256=digest(output.tobytes()),source_content_sha256=self.source_sha,
                software_reverse_drained=True,hardware_qualified=False)
            self.receipts.append(receipt);return output,loc,receipt
        except Exception:
            self.failed=True;raise
    def owned_payload(self,contract,rank):
        self._check();return self._owned_payload(contract,rank)
    def _owned_payload(self,contract,rank):
        p=self.provider;loc=p.locations.get((contract['version'],rank))
        if loc is None:raise ValueError('published addressed producer location required')
        if np.dtype(loc['dtype'])!=np.dtype('float32'):raise ValueError('actual source producer F32 backing required')
        count=math.prod(loc['shape']);owned=contract['owner_elements'][rank]
        if count==owned:indices=np.arange(owned)
        elif count==contract['shape'][1]:indices=np.concatenate([np.arange(lo,hi) for lo,hi in contract['rank_intervals'][rank]])
        else:raise ValueError('actual local/full sparse producer extent mismatch')
        words,_,receipt=self._read_words(contract['version'],rank,indices)
        return words.view(np.float32),receipt
    def gather_views(self,op,owned,key,bindings,generation,collective):
        self._check();p=self.provider
        if generation!=p.generation or collective['read_version'] not in {v['version'] for v in op['reads']}:raise ValueError('actual collective source/generation binding')
        contract=collective_contract(p.native,op['pc'],native_sha256=self.source_sha)
        if contract['version']!=collective['read_version']:raise ValueError('independent collective buffer continuation required')
        specs=p.native['templates'][key]['providers'];shape=contract['shape']
        if set(bindings)!={'parts','ownership_mask'} or specs['parts']['shape']!=shape or specs['parts']['dtype']!='F32' or specs['ownership_mask']['shape']!=shape or specs['ownership_mask']['dtype']!='U32':raise ValueError('actual source parts/mask typed ABI')
        if math.prod(shape)*8+max(contract['owner_elements'])*4>CAP:raise ValueError('finite source view workspace exceeded')
        if any(k[:3]==(op['pc'],owned['rank'],generation) for k in p.views):raise ValueError('source view owner already live')
        # Lease source versions before the first actual backing request. A
        # failure leaves an unqualified placeholder and journals retained.
        result={name:dict(field=name,rank=owned['rank'],generation=generation,kind=b['kind'],
            version=contract['version'],leased_versions=[contract['version']],source_ranks=list(range(96)),
            provenance_certified=False,data=None) for name,b in bindings.items()}
        p.views[op['pc'],owned['rank'],generation,id(result)]=result
        # Nonowned holes are masked lanes, not fabricated producer values.
        parts=np.zeros(shape,np.float32);mask=np.zeros(shape,np.uint32);journals=[]
        for rank,intervals in enumerate(contract['rank_intervals']):
            values,receipt=self._owned_payload(contract,rank);journals.append(receipt);first=0
            for lo,hi in intervals:parts[rank,lo:hi]=values[first:first+hi-lo];mask[rank,lo:hi]=1;first+=hi-lo
        if not np.all(mask.sum(axis=0)==1):raise ValueError('actual complete nonoverlapping source ownership')
        for name,array in [('parts',parts),('ownership_mask',mask)]:
            array.flags.writeable=False;b=bindings[name]
            result[name]=dict(field=name,rank=owned['rank'],generation=generation,kind=b['kind'],data=array,
                provenance_certified=True,source_binding=b,version=contract['version'],view_contract=b.get('native_address_view'),
                leased_versions=[contract['version']],source_ranks=list(range(96)),source_journal_spans=journals,
                source_extent_contract=contract,hardware_qualified=False)
        p.views[op['pc'],owned['rank'],generation,id(result)]=result;return result
    def scalar_route_weight(self,op,rank,required,spec):
        self._check();slot=op['source_op']['slot']
        if required['native_address_view']!='route_w[slot]' or spec!={'dtype':'F32','role':'operand','shape':[]} or type(slot)!=int or not 0<=slot<6:raise ValueError('actual scalar route_w slot contract')
        words,loc,receipt=self._read_words(required['version'],rank,[slot])
        if loc['shape']!=[6] or np.dtype(loc['dtype'])!=np.dtype('float32'):raise ValueError('actual six ordered route weights required')
        return words.view(np.float32).reshape(()),receipt
    def expert_outputs(self,op,rank,required,spec):
        self._check();versions=required['additional_versions'];lo=5120*rank//96;hi=5120*(rank+1)//96
        if required['native_address_view']!='e0.d..e6.d[:,5120*rank//96:5120*(rank+1)//96]' or len(versions)!=7 or spec['shape']!=[7,hi-lo] or spec['dtype']!='F32':raise ValueError('source expert-output row ABI')
        result=[];receipts=[]
        for slot,version in enumerate(versions):
            producers=[(p,w) for p in self.provider.native['instructions'][:op['pc']] for w in p['writes'] if w['version']==version]
            if len(producers)!=1 or not any(row['version']==version and row['name']=='e'+str(slot)+'.d' for row in producers[0][0]['source_outputs']):raise ValueError('actual expert output source order')
            producer,write=producers[0]
            if write['producer_extent'][rank]!=[lo,hi]:raise ValueError('actual expert source local ownership')
            contract=dict(version=version,shape=[96,5120],owner_elements=[b-a for a,b in write['producer_extent']],rank_intervals=[[x] for x in write['producer_extent']])
            value,receipt=self._owned_payload(contract,rank);result.append(value);receipts.append(receipt)
        return np.stack(result),receipts
    def query_field(self,version,rank,field,spec):
        self._check()
        if field not in ('query_codes','query_exp'):raise ValueError('actual query compound source field required')
        loc=getattr(self.provider,'field_locations',{}).get((version,rank,field))
        if loc is None:raise ValueError('query compound field physical source homes absent')
        if loc['shape']!=spec['shape'] or np.dtype(loc['dtype'])!=DTYPES[spec['dtype']]:raise ValueError('query compound field shape/codec mismatch')
        size=math.prod(loc['shape'])*np.dtype(loc['dtype']).itemsize
        if size%4 or size>65536:raise ValueError('finite exact packed query field')
        words,_,receipt=self._read_words(version,rank,np.arange(size//4),field=field)
        return words.view(loc['dtype']).reshape(loc['shape']),receipt

def provider_class(previous,*,expected_provider_sha256):
    """Opt-in extension; caller keeps Kepler's provider entrypoint ownership."""
    source=pathlib.Path(previous._read_one.__code__.co_filename)
    if not source.is_file() or digest(source.read_bytes())!=expected_provider_sha256:raise ValueError('exact reviewed provider class source pin required')
    class Provider(previous):
        def enable_source_views(self,native_content_sha256):
            if hasattr(self,'C0_source_views'):raise ValueError('source bridge already enabled')
            self.C0_source_views=SourceViews(self,native_content_sha256=native_content_sha256)
        def _read_one(self,op,owned,key,bindings,generation,collective=None):
            if not hasattr(self,'C0_source_views'):return super()._read_one(op,owned,key,bindings,generation,collective)
            bridge=self.C0_source_views;specs=self.native['templates'][key]['providers'];rank=owned['rank']
            if generation!=self.generation:raise ValueError('source bridge generation')
            if collective is not None and op['family']=='all_gather':return bridge.gather_views(op,owned,key,bindings,generation,collective)
            targeted={name:b for name,b in bindings.items() if name in ('route_weight','expert_outputs','query_codes','query_exp')}
            result=super()._read_one(op,owned,key,{name:b for name,b in bindings.items() if name not in targeted},generation,collective)
            for name,b in targeted.items():
                result[name]=dict(field=name,rank=rank,generation=generation,kind=b['kind'],version=b['version'],
                    leased_versions=b.get('additional_versions',[b['version']]),provenance_certified=False,data=None)
                if name=='route_weight':data,receipt=bridge.scalar_route_weight(op,rank,b,specs[name])
                elif name=='expert_outputs':data,receipt=bridge.expert_outputs(op,rank,b,specs[name])
                else:data,receipt=bridge.query_field(b['version'],rank,name,specs[name])
                data.flags.writeable=False
                result[name]=dict(field=name,rank=rank,generation=generation,kind=b['kind'],version=b['version'],view_contract=b['native_address_view'],
                    data=data,provenance_certified=True,source_journal_spans=receipt,leased_versions=b.get('additional_versions',[b['version']]),hardware_qualified=False)
            return result
    return Provider
