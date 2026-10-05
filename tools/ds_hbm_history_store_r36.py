"""Retained source images plus paired append visibility from real provider receipts.
No ACK generated here. Called with actual writer receipts after source publication.
Physical HBM qualification does not follow from software service events.
"""
import hashlib
import numpy as np
from h3_ds_checkpoint_provider_r34 import LockedArray

class History:
    def __init__(self,records,generation):
        self.generation=generation;self.images={};self.pending={};self.visible={};self.leases={};self.sequence=0
        for r in records:
            if r['kind'] not in (1,2):continue
            k=(r['layer'],r['kind']);record=dict(r,sha256=r['file_sha256']);image=LockedArray(record);a=image.check()
            width=512 if r['kind']==1 else 128
            if a.dtype!=np.float32 or a.shape!=(r['shape'][0],width) or k in self.images:raise ValueError('exact retained source image identity/type')
            self.images[k]=image
        for layer,kind in self.images:
            if (layer,3-kind) not in self.images or self.images[layer,1].data.shape[0]!=self.images[layer,2].data.shape[0]:raise ValueError('paired historical retained row counts')

    def prevalidate(self,layer,kind,group,version,generation,rank,row):
        # Validate before actual writer publication or bookkeeping changes.
        if generation!=self.generation or kind not in (1,2) or rank!=(group//8)%96:raise ValueError('source append generation/rank owner')
        n=self.images[layer,kind].data.shape[0];width=512 if kind==1 else 128
        if group!=n or row.dtype!=np.float32 or row.shape!=(width,):raise ValueError('exact next source row append')
        if (layer,kind) in self.pending or layer in self.visible:raise ValueError('duplicate source append ownership')
        if not np.all(np.isfinite(row)):raise ValueError('finite append source payload')

    def accept(self,layer,kind,group,version,generation,rank,row,receipt):
        self.prevalidate(layer,kind,group,version,generation,rank,row)
        identity=receipt['identity'];events=receipt['events'];suffix=f'{"compressed" if kind==1 else "index_keys"}.L{layer}.'
        if suffix not in version or (identity['version'],identity['rank'],identity['generation'])!=(version,rank,generation):raise ValueError('writer receipt full source identity')
        if receipt['pending_obligations']!=0 or receipt['payload_sha256']!={'data':hashlib.sha256(row.tobytes()).hexdigest()}:raise ValueError('writer data/reverse completion')
        if [e['event'] for e in events]!=['software_backing_visible','consumer_accept','validated_reverse_grant'] or any(e['identity']!=identity for e in events) or len(events)!=3:raise ValueError('native source visibility receipt required')
        if not events[0]['sequence']<events[1]['sequence']<events[2]['sequence']:raise ValueError('ordered actual provider service terminals')
        key=(layer,kind)
        if key in self.pending or layer in self.visible:raise ValueError('duplicate source append ownership')
        row=np.array(row,copy=True);row.flags.writeable=False
        candidate=dict(self.pending);candidate[key]=dict(version=version,group=group,rank=rank,generation=generation,row=row,receipt=receipt)
        if (layer,1) in candidate and (layer,2) in candidate:
            pair=[candidate[layer,k] for k in (1,2)]
            if any((r['group'],r['rank'],r['generation'])!=(group,rank,generation) for r in pair):raise ValueError('paired append ownership identity')
            self.visible[layer]={k:candidate[layer,k] for k in (1,2)}
            candidate.pop((layer,1));candidate.pop((layer,2))
        self.pending=candidate

    def read(self,layer,kind,ids,version,generation):
        if generation!=self.generation or layer not in self.visible or self.visible[layer][kind]['version']!=version:raise ValueError('exact paired visible history generation/version required')
        ids=np.asarray(ids)
        if ids.dtype!=np.int64 or ids.ndim!=1:raise ValueError('source ordered I64 row descriptors')
        image=self.images[layer,kind];old=image.check();n=old.shape[0]
        if np.any(ids<0) or np.any(ids>n):raise ValueError('source history bounds')
        out=np.empty((len(ids),old.shape[1]),np.float32);prior=ids<n;out[prior]=old[ids[prior]];out[~prior]=self.visible[layer][kind]['row'];out.flags.writeable=False
        self.sequence+=1;lease=self.sequence;self.leases[lease]=dict(layer=layer,kind=kind,version=version,generation=generation,ids=ids.copy())
        return out,lease

    def release(self,lease,version,generation):
        r=self.leases.get(lease)
        if r is None or (r['version'],r['generation'])!=(version,generation):raise ValueError('full history lease reverse identity')
        del self.leases[lease]
