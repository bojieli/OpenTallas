"""r34 locked scalar source images and owned eight-group provider successor.
Source read branches retained from r30; source arrays never execute arithmetic.
"""
import hashlib
import numpy as np
from h3_ds_checkpoint_provider_r30 import LockedArray as OriginalArray, DTYPES, CAP
from ds_hbm_group_provider_r34 import Provider as Groups

class LockedArray(OriginalArray):
    def digest_data(self):
        raw=self.data.reshape(-1).view(np.uint8);digest=hashlib.sha256()
        for start in range(0,len(raw),1048576):digest.update(raw[start:start+1048576])
        return digest.hexdigest()

class Provider(Groups):
    def __init__(self,manifest,*args):
        seen=set();ranges={}
        for r in manifest.get('initial_versions',[]):
            if '.window.L' not in r['version']:continue
            h=r.get('home')
            if h is None or any(r.get(k)!=h.get(k) for k in ('version','rank','generation','shape','dtype')):
                raise ValueError('initial source window full home identity')
            if h['AW']!=27 or h['shape']!=[127,512] or h['bytes']!=260096 or h['generation']!=manifest['generation']:
                raise ValueError('initial source window shape/generation')
            identity=(r['version'],r['rank']);lo=h['base'];hi=lo+h['reservation_bytes']
            if identity in seen or lo<33554432 or hi>67108864 or hi-lo!=260096:
                raise ValueError('finite initial window extent')
            if any(lo<b and a<hi for a,b in ranges.get(r['rank'],[])):raise ValueError('source initial extent overlap')
            seen.add(identity);ranges.setdefault(r['rank'],[]).append((lo,hi))
        super().__init__(manifest,*args)
        self.auxiliary_images={}
    def _read_one(self,op,owned,key,bindings,generation,collective=None):
        if op['family']=='all_reduce':return super()._read_one(op,owned,key,bindings,generation,collective)
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
                image=self._locked_auxiliary(record);a=image.check();value=dict(source_binding=required)
            else:raise NotImplementedError('source-bound view not yet implemented '+name+':'+kind)
            if list(a.shape)!=spec['shape'] or a.dtype!=DTYPES[spec['dtype']]:raise ValueError('source view shape/codec '+name)
            a=np.asarray(a).view();a.flags.writeable=False
            value.update(field=name,rank=rank,generation=generation,kind=kind,data=a,provenance_certified=True)
            result[name]=value
        self.views[op['pc'],rank,generation,id(result)]=result;return result

    def _locked_auxiliary(self,record):
        identity=(record['path'],record['sha256'])
        if identity not in self.auxiliary_images:
            image=LockedArray(record)
            self.auxiliary_images[identity]=image;self.immutable_views.append(image)
        return self.auxiliary_images[identity]

    def release_version(self,version,generation):
        # Base checks generation and every live lease before changing ownership.
        super().release_version(version,generation)
        for key in list(self.source_images):
            if key[0]==version:
                image=self.source_images.pop(key)
                import os
                os.close(image.fd)

def create_provider(manifest,native,dispatch,homes):return Provider(manifest,native,dispatch,homes)
