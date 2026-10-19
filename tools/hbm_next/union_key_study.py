#!/usr/bin/env python3
"""Source-derived union key sizing; architectural candidates, no adoption.

Reads the pinned torch-save router capture with a restricted NumPy-only tensor reader
(the fleet's Python 3.14 has no torch). Does not execute arbitrary pickled globals.
"""
import argparse,ast,collections,hashlib,io,json,pickle,zipfile
from pathlib import Path
import numpy as np

def load_capture(path):
    z=zipfile.ZipFile(path);name=next(x for x in z.namelist() if x.endswith('/data.pkl'));root=name[:-8]
    def rebuild(storage,offset,size,stride,*_):
        return np.ndarray(tuple(size),dtype=storage.dtype,buffer=storage,
            offset=int(offset)*storage.dtype.itemsize,strides=tuple(int(x)*storage.dtype.itemsize for x in stride))
    class Reader(pickle.Unpickler):
        def find_class(self,module,name):
            if module=='torch._utils' and name in ('_rebuild_tensor_v2','_rebuild_tensor'):return rebuild
            if module=='torch' and name.endswith('Storage'):
                return np.dtype({'ShortStorage':'<i2','LongStorage':'<i8','IntStorage':'<i4',
                    'ByteStorage':'u1','FloatStorage':'<f4','DoubleStorage':'<f8','BoolStorage':'?'}[name])
            if module=='collections' and name=='OrderedDict':return collections.OrderedDict
            raise pickle.UnpicklingError(f'unsupported capture global {module}.{name}')
        def persistent_load(self,pid):
            tag,dtype,key,device,n=pid
            assert tag=='storage' and device=='cpu'
            a=np.frombuffer(z.read(root+'data/'+str(key)),dtype=dtype)
            assert a.size==n
            return a
    return Reader(io.BytesIO(z.read(name))).load()

class Acc:
    def __init__(self,N):
        self.N=N;self.joint=collections.Counter();self.hist=collections.Counter();self.rowhist=collections.Counter()
    def add(self,rows):
        for layer,group in enumerate(rows):
            _,c=np.unique(group.ravel(),return_counts=True)
            assert c.sum()==6*self.N and c.max()<=self.N
            U=len(c);M=int(c.max());h=tuple(int((c==i).sum()) for i in range(1,self.N+1))
            self.joint[(U,M)]+=1;self.hist[h]+=1;self.rowhist.update(map(int,c))
    def out(self):
        samples=sum(self.joint.values());experts=sum(U*n for (U,M),n in self.joint.items())
        maxh=collections.Counter()
        for (U,M),n in self.joint.items():maxh[M]+=U*n
        return dict(samples=samples,mean_U=experts/samples,
            max_bucket_expert_weighted_hist={str(c):n/experts for c,n in sorted(maxh.items())},
            true_expert_hist={str(c):n/sum(self.rowhist.values()) for c,n in sorted(self.rowhist.items())},
            joint=[dict(U=U,max_rows=M,samples=n) for (U,M),n in sorted(self.joint.items())],
            observed_histogram_keys=len(self.hist),
            histogram_keys=[dict(counts=h,samples=n) for h,n in sorted(self.hist.items())])

def histograms(N):
    total=6*N
    def walk(c,left,used):
        if c==N:return int(left%c==0 and used+left//c>=6)
        return sum(walk(c+1,left-c*n,used+n) for n in range(left//c+1))
    return walk(1,total,0)

def main(a):
    R=load_capture(a.router)
    D={x['item']['prompt_id']:x for x in json.loads(a.drafts.read_text()) if x.get('mode')=='greedy'}
    tr=[]
    for x in R:
        it=x['item'] if isinstance(x['item'],dict) else ast.literal_eval(x['item'])
        d=D[it['prompt_id']];assert list(d['tokens'])==list(x['tokens'])
        tr.append(dict(L=int(x['L']),toks=x['tokens'],idx=x['router_idx'],drafts={int(p):v for p,v in d['drafts'].items()}))
    rng=np.random.default_rng(20261019);verify=Acc(6);mu=Acc(4)
    for t in tr:
        x,toks,L=t['idx'],t['toks'],t['L'];n=x.shape[1];acc={}
        for p,d in t['drafts'].items():
            if p+6>n-1:continue
            k=0
            while k<5 and d[k]==toks[p+2+k]:k+=1
            acc[p]=k
        p=L
        while p in acc:
            ac=acc[p];known=x[:,p+1:p+2+ac];unk=5-ac
            rows=np.concatenate([known,x[:,rng.integers(L,n,unk)]],axis=1) if unk else known
            verify.add(rows);p+=ac+1
    for _ in range(a.samples):
        chosen=rng.choice(len(tr),4,replace=False)
        mu.add(np.stack([tr[i]['idx'][:,rng.integers(tr[i]['L'],tr[i]['idx'].shape[1])] for i in chosen],axis=1))
    sizes={}
    for N in (4,6):
        legal_max=sum(1 for U in range(6,6*N+1) for C in range(1,N+1) if U<=6*N<=U*C and 6*N-U+1>=C)
        dp=[0]*37;dp[0]=1;ordered={}
        for u in range(1,37):
            dp=[sum(dp[s-c] for c in range(1,N+1) if s>=c) for s in range(37)]
            if u>=6 and u<=6*N:ordered[str(u)]=dp[6*N]
        sizes[str(N)]=dict(max_bucket_keys=legal_max,histogram_keys=histograms(N),
            ordered_cardinality_keys_by_U=ordered,ordered_keys=sum(ordered.values()))
    out=dict(schema='hnx.union-key-study.v1',seed=20261019,traces=len(tr),
        sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (a.router,a.drafts)},
        caveat='Unknown rejected verify lanes use decorrelated same-trace routing; expected rates remain estimates.',
        verify6=verify.out(),users4=mu.out(),capacity=sizes,
        per_SM_bound='global max expert row-table cardinality upper-bounds every SM row subset under rsel',
        hardware_status='candidate model only; max-cardinality key/histogram reorder not implemented')
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,indent=1)+'\n')
    print(json.dumps({k:dict(mean_U=out[k]['mean_U'],max_hist=out[k]['max_bucket_expert_weighted_hist']) for k in ('verify6','users4')}))
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--router',type=Path,required=True);ap.add_argument('--drafts',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--samples',type=int,default=6000);main(ap.parse_args())
