#!/usr/bin/env python3
"""Construct native producer/store/reload fragments for finite-VM phases.

Fragments are not a whole-programme image: producer dependencies, allocation of
all other live values and scratch ownership must be composed before installation.
"""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path


def extent(d):
    if d.space != 'VM' or any(getattr(d,k,0) for k in ('dyn_sel','indexed','n_sel','ibcast','lstride','l1stride')):
        raise ValueError('requires a static contiguous VM descriptor')
    if d.istride not in (0,1) or (d.m > 1 and d.stride != d.n):
        raise ValueError('requires contiguous rows')
    return d.base,d.base+d.n*max(1,d.m)


def producer(records, at, desired, IR):
    lo,hi=extent(desired)
    for i in range(at-1,-1,-1):
        _,r,rx,_=records[i]
        expanded=IR.expand(r,rx) if rx else [(r.slot,r)]
        for row in range(len(expanded)-1,-1,-1):
            _,one=expanded[row]
            for k in ('O','R'):
                if k not in one.desc or one.desc[k].space!='VM':
                    continue
                a,b=extent(one.desc[k])
                if max(a,lo)<min(b,hi):
                    if not a<=lo<hi<=b:
                        raise ValueError('partial latest writer requires value assembly')
                    return i,row,k
    raise ValueError('no actual source producer for operand')


def build(records, at, preparation, scratch_base, scratch_bytes, IR, RC):
    if scratch_base < 0 or scratch_base%32 or scratch_bytes<=0:
        raise ValueError('scratch must be nonnegative, 32-byte aligned and nonempty')
    _,source,rx,_=records[at]
    source_rows=IR.expand(source,rx)
    next_hbm=scratch_base
    out=[]
    for p in preparation['phases']:
        group=[]
        for pub in p['publication']:
            k=pub['operand'];n=p['rows'];start=p['start_row']
            homes=[]
            for row in range(start,start+n):
                homes.append(producer(records,at,source_rows[row][1].desc[k],IR))
            if len({h[0] for h in homes})!=1 or [h[1] for h in homes]!=list(range(start,start+n)):
                raise ValueError('producer grouping differs from consumer row identity')
            pi=homes[0][0];_,pr,px,_=records[pi]
            if px is None or px.rsel:
                raise ValueError('producer requires explicit independent row expansion')
            q=copy.deepcopy(pr);qx=copy.deepcopy(px)
            qx.n=n;qx.slot0=px.slot0+start;q.slot=qx.slot0&7
            for op,d in q.desc.items():
                d.base += start * (px.rs.get(op,0) << (px.hsh if d.space=='HBM' else 0))
            if q.unit=='SM':q.param=(q.param&3)|((n-1)<<2)
            IR.check(q,qx);IR.check_rows_independent(q,qx)
            before=IR.expand(pr,px)[start:start+n]
            after=IR.expand(q,qx)
            if [(s,vars(r)) for s,r in before] != [(s,vars(r)) for s,r in after]:
                raise ValueError('producer slicing changed an expanded row')
            d=copy.deepcopy(source_rows[start][1].desc[k]);lo,hi=extent(d);words=hi-lo
            md=RC.MDesc(space='VM',fmt=d.fmt,base=lo,n=words,m=1)
            hd=RC.MDesc(space='HBM',fmt=d.fmt,base=next_hbm,n=words,m=1)
            if next_hbm+n*words*4>scratch_base+scratch_bytes:
                raise ValueError('scratch interval too small')
            store=RC.Rec('DMA','STORE',wait=1<<RC.UNITS.index(q.unit),slot=qx.slot0&7,desc={'A':md,'O':hd})
            sx=IR.RowX(n=n,slot0=qx.slot0,rs={'A':rx.rs[k],'O':words*4})
            load=RC.Rec('DMA','LOAD',wait=1<<RC.UNITS.index('DMA'),slot=qx.slot0&7,
                        desc={'A':copy.deepcopy(hd),'O':RC.MDesc(space='VM',fmt=d.fmt,base=pub['reload_vm_base'],n=words,m=1)})
            lx=IR.RowX(n=n,slot0=qx.slot0,rs={'A':words*4,'O':words})
            for rec,xx in ((store,sx),(load,lx)):
                IR.check(rec,xx);IR.check_rows_independent(rec,xx)
            group.append(dict(operand=k,producer_record_index=pi,producer_output=homes[0][2],
                              source_vm_rows=pub['source_vm_rows'],scratch_range=[next_hbm,next_hbm+n*words*4],
                              words=n*words,producer_hex=IR.encode(q,qx).hex(),store_hex=IR.encode(store,sx).hex(),
                              reload_hex=IR.encode(load,lx).hex(),reload_vm_base=pub['reload_vm_base']))
            next_hbm+=n*words*4
        out.append(dict(start_row=p['start_row'],rows=p['rows'],publication=group,
                        consumer_hex=p['native_record_hex']))
    return dict(schema='opentallas.hbm.vm_native_publication.v1',status='FRAGMENTS_READY_COMPOSITION_REQUIRED',
                executable=False,full_programme_fits=None,scratch_ownership_confirmed=False,
                scratch_range=[scratch_base,next_hbm],transferred_bytes=2*(next_hbm-scratch_base),
                dma_records=2*sum(len(p['publication']) for p in out),phases=out,
                ordering='all producer/store fragments, DMA fence, then per phase: both reloads, DMA fence, consumer, drain',
                holds=['scratch interval must be reserved by programme allocator',
                       'relocate producer dependencies and all other live values into old VM before installation',
                       'retime consumers and drain DMA before workspace reuse',
                       'producer source addresses intentionally retain original ABI, including out-of-capacity addresses'])


def replay(packet, preparation, IR):
    """Payload movement through actual DMA encodings, all stores before reload."""
    memory={};hbm={};checked=0
    def words(rec_hex):
        raw=bytes.fromhex(rec_hex);r,x,end=IR.decode_one(raw,0)
        if end!=len(raw):raise ValueError('trailing encoded data')
        return IR.expand(r,x)
    # The candidate work interval overlaps source rows from OTHER phases too.
    # Complete the entire producer publication epoch before workspace reuse.
    for phase in packet['phases']:
        for pub in phase['publication']:
            for _,store in words(pub['store_hex']):
                a=store.desc['A'];o=store.desc['O']
                for w in range(a.n):
                    value=((a.base+w)*2654435761)^0x9e3779b9
                    memory[a.base+w]=value&0xffffffff
                    hbm[o.base+4*w]=memory[a.base+w]
    for phase in packet['phases']:
        expected={}
        for pub in phase['publication']:
            for _,load in words(pub['reload_hex']):
                a=load.desc['A'];o=load.desc['O']
                for w in range(o.n):memory[o.base+w]=hbm[a.base+4*w]
            target=pub['reload_vm_base'];j=0
            for base,count in pub['source_vm_rows']:
                for w in range(count):
                    expected[target+j]=(((base+w)*2654435761)^0x9e3779b9)&0xffffffff;j+=1
            checked+=j
        for addr,value in expected.items():
            if memory.get(addr)!=value:raise ValueError('publication payload mismatch')
    return checked


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('image','compiler-tools','preparation','out'):ap.add_argument('--'+k,required=True)
    ap.add_argument('--scratch-base',type=lambda x:int(x,0),required=True)
    ap.add_argument('--scratch-bytes',type=lambda x:int(x,0),required=True)
    a=ap.parse_args();t=Path(a.compiler_tools);sys.path[:0]=[str(t/'hbm_next'),str(t)]
    import isa_rows as IR,image_check as IC
    from hgi_sim import records as RC
    raw=Path(a.image).read_bytes();prep=json.loads(Path(a.preparation).read_text())
    if prep['image_sha256']!=hashlib.sha256(raw).hexdigest():raise ValueError('source image differs')
    out=build(IC.decode_all(raw),prep['source_record_index'],prep,a.scratch_base,a.scratch_bytes,IR,RC)
    out['payload_words_checked']=replay(out,prep,IR)
    Path(a.out).write_text(json.dumps(out,indent=1)+'\n')
    print(json.dumps({k:out[k]for k in ('status','transferred_bytes','dma_records','payload_words_checked')}))

if __name__=='__main__':main()
