"""Locked actual source-image join for a comparison-only golden trajectory.

No RNG, checkpoint activation injection into native providers, or executable
checkpoint restore. Maps the exact admitted entering images into golden state.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import numpy as np
from h4_c0_ds_whole_reference import MANIFEST,STATE,sha,load,verify_retained
from h4_c0_ds_reference_observers import observe_expert,ExpertFragments
import hdc_golden_v41 as V


class MappedRows:
    """Original ordered row-list semantics with an immutable mapped prefix."""
    def __init__(self,base):self.base=base;self.extra=[]
    def __len__(self):return len(self.base)+len(self.extra)
    def append(self,row):self.extra.append(np.asarray(row,dtype='<f4').copy())
    def __getitem__(self,key):
        if isinstance(key,slice):
            start,stop,step=key.indices(len(self))
            if step==1 and stop<=len(self.base):return self.base[start:stop]
            return [self[i] for i in range(start,stop,step)]
        if key<0:key+=len(self)
        if not 0<=key<len(self):raise IndexError(key)
        return self.base[key] if key<len(self.base) else self.extra[key-len(self.base)]


class ActualEnteringState:
    def __init__(self,manifest):
        if sha(manifest)!=MANIFEST:raise ValueError('exact admitted entering source manifest')
        self.manifest=load(manifest);self.locks={};self.arrays={};self.proofs=[]
    def __enter__(self):return self
    def __exit__(self,*args):
        for fd,_ in self.locks.values():os.close(fd)
    def image(self,path,file_sha,payload_sha,shape):
        path=Path(path).resolve()
        if str(path) in self.arrays:return self.arrays[str(path)]
        fd=os.open(path,os.O_RDONLY);fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
        before=os.fstat(fd);self.locks[str(path)]=(fd,before)
        h=hashlib.sha256();off=0
        while off<before.st_size:
            b=os.pread(fd,min(1<<20,before.st_size-off),off)
            if not b:raise ValueError('source image short read')
            h.update(b);off+=len(b)
        if h.hexdigest()!=file_sha:raise ValueError('actual source image file bytes')
        a=np.load(path,mmap_mode='r',allow_pickle=False)
        if list(a.shape)!=shape or a.dtype.str!='<f4':raise ValueError('actual source image shape/dtype')
        digest=self.array_sha(a)
        if payload_sha is not None and digest!=payload_sha:raise ValueError('actual source image payload bytes')
        self.check_locks();self.arrays[str(path)]=a
        self.proofs.append(dict(path=str(path),file_sha256=file_sha,payload_sha256=digest,shape=shape,bytes=a.nbytes))
        return a
    @staticmethod
    def update(h,a):
        view=memoryview(a).cast('B')
        for off in range(0,len(view),1<<20):h.update(view[off:off+(1<<20)])
    @classmethod
    def array_sha(cls,a):
        h=hashlib.sha256();cls.update(h,a);return h.hexdigest()
    def check_locks(self):
        for path,(fd,b) in self.locks.items():
            now=os.fstat(fd);p=os.stat(path)
            fields=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
            if fields(now)!=fields(b) or fields(p)!=fields(b):raise ValueError('source entering image changed under lock')
    def load_state(self,reference):
        ref=load(reference);m=self.manifest
        if ref['state']['state_sha256']!=STATE or m['history_source_receipt']['actual_state_sha256']!=STATE:
            raise ValueError('actual released reference entering-state identity')
        st=dict(tokens=list(ref['token_history']),win=[[] for _ in range(40)],ckv={},ik={},slots={},slotrec={})
        windows={}
        for row in m['initial_versions']:
            layer=row['layer']
            if layer in windows:
                if windows[layer]['sha256']!=row['sha256']:raise ValueError('rank aliases disagree on entering window')
            else:windows[layer]=row
        if set(windows)!=set(range(40)):raise ValueError('all forty actual entering windows required')
        h=hashlib.sha256()
        for layer in range(40):
            row=windows[layer];a=self.image(row['path'],row['sha256'],row['payload_sha256'],row['shape'])
            st['win'][layer]=list(a);self.update(h,a)
        histories={(i['layer'],i['kind']):i for i in m['history_images']}
        open_groups={}
        for key,row in m['view_bindings'].items():
            b=row.get('source_binding',{})
            if b.get('name')=='open_group':open_groups[b['layer']]=row
        for layer in sorted(int(k) for k in ref['state']['rows']):
            for kind,name in [(1,'ckv'),(2,'ik')]:
                row=histories[(layer,kind)]
                a=self.image(row['path'],row['file_sha256'],row['payload_sha256'],row['shape'])
                st[name][layer]=MappedRows(a);self.update(h,a)
            st['slots'][layer]=[];st['slotrec'][layer]={}
            count=ref['state']['rows'][str(layer)]['open_group_slots']
            if count:
                row=open_groups[layer];a=self.image(row['path'],row['sha256'],None,row['shape'])
                if a.shape!=(count,2,512):raise ValueError('exact persistent open group')
                for i,pair in enumerate(a):
                    kv,sc=pair;position=ref['position']-count+i
                    st['slots'][layer].append((kv,sc));st['slotrec'][layer][position]=(kv,sc)
                    self.update(h,kv);self.update(h,sc)
        self.check_locks()
        if h.hexdigest()!=STATE:raise ValueError('whole actual entering state differs from independent reference')
        return st,dict(status='PASS_ACTUAL_SOURCE_IMAGE_REFERENCE_STATE_JOIN',state_sha256=h.hexdigest(),
            images=self.proofs,images_locked=len(self.locks),total_payload_bytes=sum(i['bytes'] for i in self.proofs),
            RNG_used=False,native_checkpoint_restore=False,provider_operand_acquisition_qualified=False,hardware_qualified=False)


def observed_model(model,native,store,provenance):
    """Original Model.layer/moe trajectory with expert intermediate observers."""
    class Observer(V.Model):
        def expert(self,prefix,x,weight=None):
            capture=observe_expert(self,prefix,x,weight)
            self._captures.append(capture);return capture['d']
        def moe(self,L,x,trace):
            self._captures=[]
            y=V.Model.moe(self,L,x,trace)
            ExpertFragments(native,L,self._captures,store,provenance).emit()
            self._captures=[];return y
    result=Observer.__new__(Observer);result.__dict__.update(model.__dict__)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('fresh actual source join evidence required')
    with ActualEnteringState(a.manifest) as join:
        state,proof=join.load_state(a.reference)
        a.out.mkdir(parents=True);(a.out/'record.json').write_text(json.dumps(proof,sort_keys=True,indent=2)+'\n')
        print(json.dumps({k:v for k,v in proof.items() if k!='images'},sort_keys=True))
