"""Data-only checkpoint/scratch/lifecycle implementation with finite r30 journaling for06d91ed58.
No golden/Executor callback. Missing persistent input/home/view fails closed.
Software backing causality does not qualify RF, DRAM or physical completion.
"""
import collections,fcntl,gzip,hashlib,json,math,os,struct
from itertools import islice
from hbm_bound_event_journal_r30 import JournalBudget,BoundSectorProvider
from pathlib import Path
import numpy as np
from hbm_provider_microvm_r21 import SectorProvider,Storage,Tensor
CAP=33554432;WORKBASE=67108864;RF_SM=512*128*4;RF_BYTES=32*2*RF_SM
DTYPES={'F32':np.dtype('<f4'),'U32':np.dtype('<u4'),'I64':np.dtype('<i8')}

class LockedCheckpoint:
    def __init__(self,path,revision,index_sha256):
        self.path=Path(path).resolve()
        if self.path.name!=revision:raise ValueError('checkpoint revision directory')
        raw=(self.path/'model.safetensors.index.json').read_bytes()
        if hashlib.sha256(raw).hexdigest()!=index_sha256:raise ValueError('checkpoint index pin')
        self.index=json.loads(raw)['weight_map'];self.files={};self.receipts=[]
    def tensor(self,name,rows=None,cols=None):
        filename=self.index[name];p=(self.path/filename).resolve()
        if filename not in self.files:
            fd=os.open(p,os.O_RDONLY);fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
            n=struct.unpack('<Q',os.pread(fd,8,0))[0]
            if n>67108864:raise ValueError('safetensors header bound')
            raw=os.pread(fd,n,8);header=json.loads(raw)
            self.files[filename]=(fd,header,8+n,os.fstat(fd),hashlib.sha256(raw).hexdigest())
        fd,h,base,stamp,header_sha=self.files[filename];m=h[name];start,end=m['data_offsets'];shape=m['shape'];dtype=m['dtype']
        now=os.fstat(fd)
        if (now.st_dev,now.st_ino,now.st_size,now.st_mtime_ns,now.st_ctime_ns)!=(stamp.st_dev,stamp.st_ino,stamp.st_size,stamp.st_mtime_ns,stamp.st_ctime_ns):raise ValueError('locked payload changed')
        raw=np.memmap('/proc/self/fd/'+str(fd),mode='r',dtype=np.uint8,offset=base+start,shape=(end-start,))
        if dtype=='F32':a=raw.view('<f4').reshape(shape)
        elif dtype=='BF16':a=raw.view('<u2').reshape(shape)
        elif dtype in ('F8_E4M3','F8_E8M0','I8'):a=raw.reshape(shape)
        else:raise ValueError('unsupported checkpoint codec '+dtype)
        if rows is not None:a=a[slice(*rows)]
        if cols is not None:a=a[:,slice(*cols)]
        if dtype=='BF16':a=(np.asarray(a,dtype=np.uint32)<<16).view(np.float32)
        else:a=np.asarray(a).copy() # Immutable selected data view, never whole-checkpoint preload.
        after=os.fstat(fd)
        if (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)!=(stamp.st_dev,stamp.st_ino,stamp.st_size,stamp.st_mtime_ns,stamp.st_ctime_ns):raise ValueError('locked payload changed during copy')
        a.flags.writeable=False
        self.receipts.append(dict(tensor=name,filename=filename,header_sha256=header_sha,rows=rows,cols=cols,dtype=dtype,selected_payload_sha256=hashlib.sha256(a.tobytes()).hexdigest(),whole_shard_payload_hash_verified=False))
        return a,dtype

class LockedArray:
    """An explicit source image, never a callback or regenerated context."""
    def __init__(self,record):
        self.record=record;self.fd=os.open(record['path'],os.O_RDONLY)
        fcntl.flock(self.fd,fcntl.LOCK_SH|fcntl.LOCK_NB);self.stamp=os.fstat(self.fd)
        digest=hashlib.sha256();off=0
        while True:
            chunk=os.pread(self.fd,1048576,off)
            if not chunk:break
            digest.update(chunk);off+=len(chunk)
        if digest.hexdigest()!=record['sha256']:raise ValueError('explicit source image payload pin')
        self.data=np.load('/proc/self/fd/'+str(self.fd),mmap_mode='r',allow_pickle=False)
        if not isinstance(self.data,np.ndarray):raise ValueError('single source NPY image required')
        self.data_sha256=self.digest_data();self.verification_bytes=0
        self.check();self.data.flags.writeable=False
    def digest_data(self):
        raw=self.data.view(np.uint8).reshape(-1);digest=hashlib.sha256()
        for start in range(0,len(raw),1048576):digest.update(raw[start:start+1048576])
        return digest.hexdigest()
    def check(self):
        now=os.fstat(self.fd)
        if (now.st_dev,now.st_ino,now.st_size,now.st_mtime_ns,now.st_ctime_ns)!=(self.stamp.st_dev,self.stamp.st_ino,self.stamp.st_size,self.stamp.st_mtime_ns,self.stamp.st_ctime_ns):raise ValueError('explicit source image mutated')
        if self.digest_data()!=self.data_sha256:raise ValueError('explicit source image payload mutated')
        self.verification_bytes+=self.data.nbytes
        return self.data

class AddressedScratch:
    """Implement the actual native memory keys in one finite AW27 allocation."""
    def __init__(self,owner,extent,journal_budget):
        if len(owner)!=5 or extent['base']!=WORKBASE or extent['AW']!=27 or extent['bytes']!=CAP:raise ValueError('owner/workspace binding')
        self.owner=owner;self.workspace_extent=extent;self.p=BoundSectorProvider({('DeepSeek',owner[2]):[dict(base=WORKBASE,bytes=CAP)]},journal_budget=journal_budget,allocation_identity={'address_class':'scratch','native_owner':owner})
        self.s=Storage(self.p,'DeepSeek',owner[2],WORKBASE,CAP);self.s.pc=owner[0];self.s.epoch=owner[4]
        self.values={};self.addresses={};self.cursor=0;self.events=collections.Counter();self.mode=None
    def slot(self,key,size):
        if key[1:6]!=self.owner:raise ValueError('scratch full owner mismatch')
        mode='arena' if key[0]=='arena' else 'named'
        if self.mode not in (None,mode):raise ValueError('mixed arena/named address domains')
        self.mode=mode
        if mode=='arena':off=key[-1]
        elif key in self.addresses:off=self.addresses[key]
        else:off=self.cursor;self.cursor+=512;self.addresses[key]=off
        if type(off) is not int or off<0 or off%32 or off+size>CAP:raise ValueError('finite workspace address')
        return WORKBASE+off
    def transact(self,key,*,write=False,payload=None):
        key=tuple(key)
        if write!=(payload is not None):raise ValueError('write payload/read request')
        if not write and key not in self.values:raise ValueError('unpublished scratch read')
        n=len(payload) if write else self.values[key]
        if not 0<n<=512:raise ValueError('explicit <=512B fragment')
        base=self.slot(key,n);t=Tensor('DeepSeek',self.owner[2],base,(n,),'U8')
        if write:
            for i in range(0,n,128):self.s.write(t,i,np.frombuffer(payload[i:i+128],np.uint8))
            self.values[key]=n;result=b''
        else:result=b''.join(self.s.read(t,np.arange(i,min(i+128,n))).tobytes() for i in range(0,n,128))
        self.events['write' if write else 'read']+=1;return result
    def preload(self,key,payload):
        if tuple(key) in self.values:raise ValueError('duplicate initial fragment')
        self.transact(key,write=True,payload=payload)
    def write_object(self,key,payload):
        for off in range(0,len(payload),512):self.transact((*key,'part',off),write=True,payload=payload[off:off+512])
        self.values[(*key,'length')]=str(len(payload)).encode()
    def read_object(self,key):
        n=int(self.values[(*key,'length')]);return b''.join(self.transact((*key,'part',off)) for off in range(0,n,512))
    def fence(self):
        if self.p.live or self.p.calendar or self.p.queue or self.p.resident:raise ValueError('scratch backing/reverse obligations retained')
    def summary(self):return dict(events=dict(self.events),addressed_sector_events=len(self.p.events),outstanding=len(self.p.live),workspace_extent=self.workspace_extent,peak_named_allocation_bytes=self.cursor,phase_costs=self.p.costs,calibration='provisional software ticks; not RF/HBM or clock measurements',physical_backend_bound=False,journal=self.p.events.summary())

class Provider:
    def __init__(self,manifest,native,dispatch,homes):
        self.journal_budget=JournalBudget(manifest['journal_root'],manifest['journal_capacity_bytes']);self.retired_journals=[]
        self.manifest=manifest;self.native=native;self.homes=homes;self.generation=manifest['generation'];self.revision=manifest['checkpoint_revision']
        self.checkpoint=LockedCheckpoint(manifest['checkpoint_path'],self.revision,manifest['checkpoint_index_sha256'])
        self.published={};self.views={};self.memories={};self.seq=0;self.trace=[];self.backing={};self.immutable_views=[];self.rf={};self.locations={};self.state={}
        self.bindings=manifest.get('view_bindings',{})
        # No generated KV, golden intermediates or silent context substitution.
        self.source_images={}
        for v in manifest.get('initial_versions',[]):
            image=LockedArray(v);self.source_images[v['version'],v['rank']]=image
            self.published[v['version'],v['rank']]=image.check()
        recipe=manifest.get('checkpoint_initial_embedding')
        if recipe is not None:
            source=Path(recipe['initializer_source']);raw=source.read_bytes()
            expected=native['source_sha256']['tools/w19_hbm_tp96_isa.py']
            if hashlib.sha256(raw).hexdigest()!=expected or recipe['initializer_sha256']!=expected:raise ValueError('embedding initializer source pin')
            history=Path(recipe['token_history_source']).read_bytes()
            if hashlib.sha256(history).hexdigest()!=recipe['token_history_sha256']:raise ValueError('embedding token history pin')
            tokens=json.loads(history)['token_history'];token=tokens[-1]
            if recipe['version']!='DeepSeek.-1.h.0' or recipe['planes']!=4:raise ValueError('initial embedding native source identity')
            a,dt=self.checkpoint.tensor('embed.weight',rows=[token,token+1])
            if dt!='BF16' or a.shape!=(1,5120):raise ValueError('source embedding shape/codec')
            a=np.repeat(a,4,axis=0);a.flags.writeable=False
            for rank in recipe['ranks']:self.published[recipe['version'],rank]=a
            if recipe.get('initial_pre_version') is not None:
                if recipe['initial_pre_version']!='DeepSeek.-1.pre.1' or 'pre = np.array([1, 0, 0, 0], dtype=F)' not in raw.decode():raise ValueError('source initial pre constant contract')
                pre=np.array([1,0,0,0],np.float32);pre.flags.writeable=False
                for rank in recipe['ranks']:self.published[recipe['initial_pre_version'],rank]=pre
    def workspace(self,rank):
        return dict(AW=27,base=WORKBASE,bytes=CAP,occupied_extents=[dict(base=0,bytes=RF_BYTES),dict(base=RF_BYTES,bytes=32*8192),dict(base=33554432,bytes=33554432)])
    def scratch_memory(self,owner,extent):
        if owner[4]!=self.generation:raise ValueError('scratch generation')
        m=AddressedScratch(owner,extent,self.journal_budget);self.memories[owner]=m;return m
    def weight_view(self,name,required,owned,spec):
        tensor=required['logical_tensor']
        if not isinstance(tensor,str):raise NotImplementedError('dynamic expert tensor requires accepted route descriptor')
        rank=owned['rank'];rows=required['row_intervals'][rank]
        if rows!=owned['row_interval']:raise ValueError('source rank row ownership')
        fmt=required['format']
        if name=='weight_codes':
            a,dt=self.checkpoint.tensor(tensor,rows=rows)
            expected={'fp8':'F8_E4M3','fp4':'I8'}.get(fmt)
            if dt!=expected:raise ValueError('source weight code dtype')
            # FP4 remains packed, low nibble first: native dot32 consumes16bytes.
            return a.astype(np.uint32)
        if name=='weight_scale_codes':
            scale=tensor.removesuffix('.weight')+'.scale'
            lo,hi=rows
            # FP8 scales share32 output rows; FP4 has one scale row per output.
            sr=[lo//32,(hi+31)//32] if fmt=='fp8' else rows
            a,dt=self.checkpoint.tensor(scale,rows=sr)
            if dt!='F8_E8M0':raise ValueError('raw UE8M0 scale dtype')
            if fmt=='fp8':a=a[np.arange(lo,hi)//32-sr[0]]
            elif fmt!='fp4':raise ValueError('source weight format')
            return a.astype(np.uint32) # Native requires biased byte, not byte-127.
        raise NotImplementedError('floating/wo_a weight source rounding and K ownership not yet bound')
    def _read_one(self,op,owned,key,bindings,generation,collective=None):
        rank=owned['rank'];specs=self.native['templates'][key]['providers'];result={}
        for name,required in bindings.items():
            spec=specs[name];kind=required['kind']
            if collective is not None and name in ('parts','ownership_mask'):
                version=collective['read_version']
                producer=[o for o in self.native['instructions'] if any(w['version']==version for w in o['writes'])]
                if len(producer)!=1 or 'rows' not in producer[0]['source_op']:raise NotImplementedError('collective source row directory absent')
                rows=producer[0]['source_op']['rows'];shape=specs['parts']['shape']
                if len(rows)!=shape[0] or shape[0]*shape[1]*8>CAP:raise ValueError('finite collective parts/mask workspace')
                mask=np.zeros(shape,np.uint32);parts=np.zeros(shape,np.float32)
                for r,(lo,hi) in enumerate(rows):
                    if hi==lo:continue
                    payload=self.restore(version,r)
                    if payload.dtype!=np.dtype('<f4') or payload.shape!=(hi-lo,):raise ValueError('collective source owned payload')
                    parts[r,lo:hi]=payload;mask[r,lo:hi]=1
                if not np.all(mask.sum(axis=0)==1):raise ValueError('collective complete nonoverlapping source coverage')
                a=parts if name=='parts' else mask
                value=dict(version=version,view_contract=required.get('native_address_view'),source_binding=required,leased_versions=[version],source_ranks=list(range(len(rows))))
            elif kind=='versioned_operand':
                a=self.restore(required['version'],rank)
                value=dict(version=required['version'],view_contract=required['native_address_view'],leased_versions=[required['version']])
            elif kind=='immutable_parameter_provider':
                a,dt=self.checkpoint.tensor(required['logical_tensor']);value=dict(logical_tensor=required['logical_tensor'],revision=self.revision)
                if dt not in ('F32','BF16'):raise ValueError('parameter requires source codec mapping')
            elif kind=='immutable_weight_provider':
                a=self.weight_view(name,required,owned,spec);value=dict(logical_tensor=required['logical_tensor'],revision=self.revision)
            elif kind=='explicit_auxiliary_provider':
                binding_key=str(op['pc'])+'/'+key+'/'+name
                record=self.bindings.get(binding_key)
                if record is None:raise NotImplementedError('actual auxiliary/CROM source image absent '+binding_key)
                if record['source_binding']!=required or record['generation']!=generation or record['checkpoint_revision']!=self.revision:raise ValueError('auxiliary source identity/revision/generation')
                image=LockedArray(record);self.immutable_views.append(image);a=image.check();value=dict(source_binding=required)
            else:raise NotImplementedError('source-bound view not yet implemented '+name+':'+kind)
            if list(a.shape)!=spec['shape'] or a.dtype!=DTYPES[spec['dtype']]:raise ValueError('source view shape/codec '+name)
            a=np.asarray(a).view();a.flags.writeable=False
            value.update(field=name,rank=rank,generation=generation,kind=kind,data=a,provenance_certified=True)
            result[name]=value
        self.views[op['pc'],rank,generation,id(result)]=result;return result
    def read_views(self,op,owned,generation):
        if generation!=self.generation:raise ValueError('generation')
        if owned.get('buffer_programs'):
            result={}
            for b in owned['buffer_programs']:
                bindings={name:dict(value) for name,value in op['provider_bindings'][b['template']].items()}
                for name,required in bindings.items():
                    if name=='parts':required.update(version=b['read_version'],additional_versions=[b['read_version']])
                    elif required['kind']=='explicit_auxiliary_provider':required['identity_from_versions']=[b['read_version']]
                result[b['write_version']]=self._read_one(op,owned,b['template'],bindings,generation,b)
            return result
        return self._read_one(op,owned,owned['template'],op['provider_bindings'][owned['template']],generation)
    def _leased(self,version):
        return any(version in v.get('leased_versions',[v.get('version')]) for vs in self.views.values() for v in vs.values())
    def publish(self,identity,fields,source_store_view):
        # Source home/version metadata validated by driver and repeated here.
        rank=identity['rank'];version=identity['version'];gen=identity['generation']
        if gen!=self.generation:raise ValueError('publication generation')
        if identity['home_indices'] and self.homes[identity['home_indices'][0]]['home']['class']=='HBM_NATIVE_STATE':return self.publish_state(identity,fields,source_store_view)
        for i in identity['home_indices']:
            h=self.homes[i]
            if h['version']!=version or rank not in h['rank_group'] or h['home']['class']!='RF':raise ValueError('source native home')
        if not identity['home_indices']:raise ValueError('persistent output needs concrete physical home directory')
        if set(fields)!={'data'}:raise NotImplementedError('compound persistent/code/scale field homes required')
        if self._leased(version):raise ValueError('write over leased version')
        proposed={(self.homes[i]['SM'],slot) for i in identity['home_indices'] for slot in range(self.homes[i]['home']['slot_first'],self.homes[i]['home']['slot_first']+self.homes[i]['home']['vectors'])}
        for (live_version,live_rank),loc in self.locations.items():
            if live_rank!=rank or live_version==version or loc.get('kind')=='state_fragment':continue
            occupied={(self.homes[i]['SM'],slot) for i in loc['indices'] for slot in range(self.homes[i]['home']['slot_first'],self.homes[i]['home']['slot_first']+self.homes[i]['home']['vectors'])}
            if proposed&occupied:raise ValueError('physical RF home aliases retained version')
        data=fields['data'];words=np.ascontiguousarray(data).view(np.uint32).reshape(-1)
        if rank not in self.rf:self.rf[rank]=BoundSectorProvider({('DeepSeek',rank):[dict(base=0,bytes=RF_BYTES)]},journal_budget=self.journal_budget,allocation_identity={'address_class':'RF','rank':rank})
        p=self.rf[rank];s=Storage(p,'DeepSeek',rank,0,RF_BYTES);s.pc=identity['PC'];s.epoch=gen
        begin=len(p.events);covered=set()
        for i in identity['home_indices']:
            h=self.homes[i];sm=h['SM'];idx=np.arange(len(words))
            block=(idx%5120)//256 if h['partition']=='HC_plane_dimension' else idx//256
            chosen=idx[block%32==sm]
            if len(chosen)!=h['word_count'] or len(chosen)>h['home']['vectors']*128:raise ValueError('native home word capacity')
            if covered.intersection(chosen.tolist()):raise ValueError('duplicate native source word home')
            covered.update(chosen.tolist())
            payload=words[chosen]
            for copy in range(2):
                base=(sm*2+copy)*RF_SM+h['home']['slot_first']*512
                t=Tensor('DeepSeek',rank,base,(len(payload),),'U32')
                for k in range(0,len(payload),128):s.write(t,k,payload[k:k+128])
        if covered!=set(range(len(words))):raise ValueError('unscattered native source words')
        # Exact data reconstructed by addressed reads from copy0, not a cached
        # whole-source arithmetic result shortcut.
        restored=np.empty_like(words)
        for i in identity['home_indices']:
            h=self.homes[i];sm=h['SM'];idx=np.arange(len(words));block=(idx%5120)//256 if h['partition']=='HC_plane_dimension' else idx//256;chosen=idx[block%32==sm]
            base=sm*2*RF_SM+h['home']['slot_first']*512;t=Tensor('DeepSeek',rank,base,(len(chosen),),'U32')
            for k in range(0,len(chosen),128):restored[chosen[k:k+128]]=s.read(t,np.arange(k,min(k+128,len(chosen))))
        if not np.array_equal(restored,words):raise ValueError('native addressed publication readback')
        restored=restored.view(data.dtype).reshape(data.shape);restored.flags.writeable=False;self.published[version,rank]=restored
        self.locations[version,rank]=dict(indices=identity['home_indices'],shape=data.shape,dtype=data.dtype,pc=identity['PC'])
        source=p.events[begin:];last_write=max(k for k,e in enumerate(source) if e['event']=='software_backing_visible')
        terminal=list(islice(((k,e) for k,e in enumerate(source) if k>=last_write and e['event'] in ['software_backing_visible','consumer_accept','validated_reverse_grant']),3))
        if [e['event'] for _,e in terminal]!=['software_backing_visible','consumer_accept','validated_reverse_grant']:raise ValueError('actual source write completion sequence')
        events=[]
        for k,e in terminal:
            events.append(dict(event='software_backing_visible' if e['event']=='software_backing_visible' else e['event'],identity=identity,sequence=self.seq+k+1,source_fragment_identity=e['identity'],source_tag=e['tag'],source_tag_generation=e['generation'],source_tick=e['tick']))
        self.seq+=len(source);self.trace.extend(events)
        return dict(identity=identity,payload_sha256={'data':hashlib.sha256(data.tobytes()).hexdigest()},events=events,pending_obligations=len(p.live),physical_qualified=False)
    def publish_state(self,identity,fields,source_store_view):
        if identity['generation']!=self.generation or set(fields)!={'data'} or len(identity['home_indices'])!=1:raise ValueError('exact finite state publication identity/fields')
        index=identity['home_indices'][0];h=self.homes[index];rank=identity['rank'];version=identity['version'];b=h['binding'];data=fields['data']
        if (b['PC'],b['version'],b['rank'])!=(identity['PC'],version,rank) or b['source_result']!=source_store_view['result']:raise ValueError('state source result/version/rank')
        if list(data.shape)!=b['shape'] or data.dtype!=DTYPES[b['dtype']]:raise ValueError('state exact source fragment shape/type')
        if self._leased(version):raise ValueError('write over state read lease')
        if not 33554432<=b['base'] or b['base']+b['reservation_bytes']>67108864:raise ValueError('state finite disjoint aperture')
        if rank not in self.state:self.state[rank]=BoundSectorProvider({('DeepSeek',rank):[dict(base=33554432,bytes=33554432)]},journal_budget=self.journal_budget,allocation_identity={'address_class':'native_state_fragment','rank':rank})
        p=self.state[rank];s=Storage(p,'DeepSeek',rank,33554432,33554432);s.pc=identity['PC'];s.epoch=self.generation
        begin=len(p.events);words=np.ascontiguousarray(data).view(np.uint32).reshape(-1);t=Tensor('DeepSeek',rank,b['base'],(len(words),),'U32')
        for off in range(0,len(words),128):s.write(t,off,words[off:off+128])
        terminal=list(p.events[-3:])
        if [e['event'] for e in terminal]!=['consumer_accept','reverse_credit_accept','validated_reverse_grant']:raise ValueError('actual state reverse terminal sequence')
        # Locate last actual backing mutation, preserving full fragment identity.
        source=p.events[begin:];last=max(k for k,e in enumerate(source) if e['event']=='software_backing_visible');events=list(islice(((k,e) for k,e in enumerate(source) if k>=last and e['event'] in ['software_backing_visible','consumer_accept','validated_reverse_grant']),3))
        if [e['event'] for _,e in events]!=['software_backing_visible','consumer_accept','validated_reverse_grant']:raise ValueError('actual state write completion sequence')
        receipt=[dict(event=e['event'],identity=identity,sequence=self.seq+k+1,source_fragment_identity=e['identity'],source_tag=e['tag'],source_tag_generation=e['generation'],source_tick=e['tick']) for k,e in events];self.seq+=len(p.events)-begin
        self.locations[version,rank]=dict(kind='state_fragment',binding=b,shape=data.shape,dtype=data.dtype,pc=identity['PC'])
        return dict(identity=identity,payload_sha256={'data':hashlib.sha256(data.tobytes()).hexdigest()},events=receipt,pending_obligations=len(p.live),physical_qualified=False)
    def restore(self,version,rank):
        if (version,rank) in self.source_images:return self.source_images[version,rank].check()
        if (version,rank) not in self.locations:return self.published[version,rank]
        loc=self.locations[version,rank]
        if loc.get('kind')=='state_fragment':
            p=self.state[rank];s=Storage(p,'DeepSeek',rank,33554432,33554432);s.pc=loc['pc'];s.epoch=self.generation;n=math.prod(loc['shape'])*np.dtype(loc['dtype']).itemsize//4;t=Tensor('DeepSeek',rank,loc['binding']['base'],(n,),'U32');out=np.empty(n,np.uint32)
            for off in range(0,n,128):out[off:off+128]=s.read(t,np.arange(off,min(off+128,n)))
            a=out.view(loc['dtype']).reshape(loc['shape']);a.flags.writeable=False;return a
        p=self.rf[rank];s=Storage(p,'DeepSeek',rank,0,RF_BYTES);s.pc=loc['pc'];s.epoch=self.generation
        n=math.prod(loc['shape'])*np.dtype(loc['dtype']).itemsize//4;out=np.empty(n,np.uint32);idx=np.arange(n)
        for i in loc['indices']:
            h=self.homes[i];sm=h['SM'];block=(idx%5120)//256 if h['partition']=='HC_plane_dimension' else idx//256;chosen=idx[block%32==sm]
            base=sm*2*RF_SM+h['home']['slot_first']*512;t=Tensor('DeepSeek',rank,base,(len(chosen),),'U32')
            for k in range(0,len(chosen),128):out[chosen[k:k+128]]=s.read(t,np.arange(k,min(k+128,len(chosen))))
        a=out.view(loc['dtype']).reshape(loc['shape']);a.flags.writeable=False;return a
    def release_views(self,pc,rank,generation,views):
        if self.views.pop((pc,rank,generation,id(views)),None) is not views:raise ValueError('stale views')
    def release_version(self,version,generation):
        if generation!=self.generation:raise ValueError('version generation')
        if self._leased(version):raise ValueError('version still leased')
        for key in list(self.locations):
            if key[0]==version:self.locations.pop(key)
        for key in list(self.published):
            if key[0]==version:del self.published[key];self.locations.pop(key,None)
    def retire_operation(self,pc,generation):
        if generation!=self.generation or any(k[0]==pc for k in self.views):raise ValueError('operation views retained')
        for owner,m in list(self.memories.items()):
            if owner[0]==pc:
                m.fence();self.retired_journals.append(dict(owner=owner,journal=m.p.events.summary()));m.p.events.close();del self.memories[owner]
        return dict(PC=pc,generation=generation,pending_obligations=0,source_consumers_released=True)
    def drain(self,generation):
        if generation!=self.generation or self.views:raise ValueError('live consumers')
        for m in self.memories.values():m.fence();m.p.events.flush()
        if any(p.live or p.calendar or p.queue or p.resident for p in list(self.rf.values())+list(self.state.values())):raise ValueError('RF source obligations retained')
        for p in list(self.rf.values())+list(self.state.values()):p.events.flush()
        return dict(generation=generation,pending_obligations=0,live_consumers=0)

def create_provider(manifest,native_program,bounded_dispatch,residence_homes):
    return Provider(manifest,native_program,bounded_dispatch,residence_homes)
