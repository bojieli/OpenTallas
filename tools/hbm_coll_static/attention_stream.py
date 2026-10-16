#!/usr/bin/env python3
"""Compile a finite, overlapped PV component using literal native resources.

Two real SRAM banks overlap next-batch ring delivery and current-batch local
pairwise reduction. No dynamic issue, credit, or ready occurs inside the die.
The canonical128-row nodes remain a declared component boundary.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
from attention_calendar import ROOT, P, RING_FIELDS, Slots, add, numeric_tree, pack

STREAM_FIELDS = [('scratch_read_v',1),('scratch_read_slot',5),('load_v',1),('load_tag',4),
                 ('add_read',1),('read_tag',4),('add_issue',1),('pub_read',1),('pub_tag',4),
                 ('pub_issue',1),('capture',1),('capture_slot',5),('clear_bank_v',1),
                 ('clear_bank',1),('final_pub',1),('batch',7),('destination',2)]
SOURCES = [P/n for n in ('ot_hgi_attn_pv_pkg.sv','ot_hgi_attn_pv_stream_pkg.sv',
                         'ot_hgi_attn_pv_stream.sv','ot_hgi_coll_pring_static.sv',
                         'ot_hgi_coll_reduce_static.sv')]
SOURCES += [Path('physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v')]


def float_bits(x):
    return struct.unpack('<I',struct.pack('<f',x))[0]


def bits_float(x):
    return struct.unpack('<f',struct.pack('<I',x))[0]


def term(k,lane,seed):
    return bits_float([
        0x60ad78ec+seed*31+lane,
        0x3f400000+seed*13+lane*53+k*17,
        0xe0ad78ec+seed*31+lane,
        0xbf200000+seed*19+lane*29+k*311,
        0x3f800000+seed*7+lane*31,
        0x40000000+seed*5+lane*37,
        0xbf000000+seed*3+lane*41,
        0x3e800000+seed*11+lane*43][k%8])


def block_node(k,lane,seed):
    chunks=[]
    for j in range(16):
        x=0.0
        for t in range(8):x=add(x,term(k,lane,seed+j*8+t))
        chunks.append(x)
    return numeric_tree(chunks)


def compile_stream(out, mutant=None, batches=128):
    if batches not in (4,128):raise ValueError('four debug batches or complete1024word Qwen output required')
    # At each batch start ring tags are free; local begin waits until the
    # worst destination's last quartet is in SRAM. Local stages are29/21/17/15.
    period=82;last=(batches-1)*period+167;size=last+1
    rings=[[{} for _ in range(size)] for _ in range(4)]
    inputs=[[0]*size for _ in range(4)]
    local=[{} for _ in range(size)];landing=[0]*size;dest=[0]*size
    expected=[0]*size;expected_v=[0]*size;expected_batch=[0]*size
    resources=Slots();lives={};read_lives={};timelines=[]
    def event(resource,c,op,**f):resources.put(resource,c,op,**f)
    def setring(q,c,**fields):
        for k,v in fields.items():
            if k in rings[q][c] and rings[q][c][k]!=v:raise ValueError(f'command conflict{q,c,k}')
            rings[q][c][k]=v
    def send(src,dst,c,tag,result=False,acc=False):
        order=[0,1,3,2];pos=order.index
        direction=0 if result or (pos(dst)-pos(src))%4!=3 else 1
        hops=3 if result else ((pos(src)-pos(dst))%4 if direction else (pos(dst)-pos(src))%4)
        if hops!=1 and not result:raise ValueError('candidate requires actual adjacent pair hops')
        event(f'q{src}.readtx',c-1,'read',tag=tag)
        event(f'q{src}.tx{direction}',c,'inject',tag=tag)
        setring(src,c-1,read_tx=1,read_tx_tag=tag,read_tx_acc=int(acc))
        setring(src,c,inject=1<<direction,tx_tag=tag,dst=dst,result=int(result),acc=int(acc))
        q=src
        for h in range(1,hops+1):
            q=order[(pos(q)+(-1 if direction else 1))%4];t=c+2*h
            event(f'q{q}.rx{direction}',t,'result' if result else 'carry',tag=tag,source=src)
            setring(q,t,rx=1<<direction,kind=(2 if result else 1)<<(2*direction),src=src<<(2*direction),tag=tag<<(3*direction))
            if h<hops:
                event(f'q{q}.tx{direction}',t,'forward',tag=tag)
                setring(q,t,fwd=1<<direction)
            if result:lives[(q,tag)]=t
        if result:
            event(f'q{src}.readrr',c-1,'read',tag=tag)
            setring(src,c-1,read_rr=1,read_rr_tag=tag)
            setring(src,c,rr=1,rr_tag=tag);lives[(src,tag)]=c
    def ringadd(q,c,tag,src,rhs):
        event(f'q{q}.readadd',c-1,'read',tag=tag)
        event(f'q{q}.add',c,'add',tag=tag)
        event(f'q{q}.writeback',c+8,'writeback',tag=tag)
        setring(q,c-1,read_add=1,read_add_tag=tag,read_add_src=src,read_rhs_acc=int(rhs))
        setring(q,c,add_v=1,add_tag=tag,add_src=src,rhs_acc=int(rhs))
    def loc(c,resource,**fields):
        event(resource,c,'local',**fields)
        for k,v in fields.items():
            if k in local[c] and local[c][k]!=v:raise ValueError(f'local control conflict{c,k}')
            local[c][k]=v
    for batch in range(batches):
        start=batch*period;bank=batch%2;destination=(batch//16)%4
        # Select the destination before this batch's first publication, after
        # all destinations of the previous batch's final multicast drained.
        for t in range(start+25,min(start+25+period,size)):dest[t]=destination
        nodes=[[block_node(k,l,batch) for l in range(8)] for k in range(64)]
        for group in range(16):
            # Tag lifetime alone permits37; the actual shared q0 CW port is
            # still forwarding the previous wave through41. Next TX>=42 makes
            # the resource-safe wave stride40. The compiler checks every hop.
            tag=group%8;b=start+(group//8)*40+tag
            for q in range(4):
                if (q,tag) in lives and b<=lives[(q,tag)]:raise ValueError('live ring tag reuse')
                event(f'q{q}.lp',b,'load',tag=tag)
                setring(q,b,lp_we=1,lp_tag=tag)
                k=4*group+q
                if mutant=='localfirst':k=4*(k%16)+k//16
                inputs[q][b]=sum(float_bits(nodes[k][l])<<(32*l) for l in range(8))
            send(0,1,b+2,tag);send(2,3,b+2,tag)
            ringadd(1,b+6,tag,0,False);ringadd(3,b+6,tag,2,False)
            send(1,3,b+16,tag,acc=True);ringadd(3,b+20,tag,1,True)
            send(3,3,b+30,tag,result=True,acc=True)
            store=b+{3:31,2:33,0:35,1:37}[destination]
            event(f'ram{bank}.write',store,'ring_store',slot=group)
            landing[store]=bank*16+group
        c=start+85;stages=[]
        for width in (16,8,4,2):
            n=width//2;stages.append(dict(width=width,start=c,pairs=n,edges=2*n+13))
            for p in range(n):
                # One SRAM read/edge, one reducer load-or-right-input/edge.
                left=c+p;right=c+n+p;load=left+1;read=right+1;issue=read+1
                wb=issue+8;pubread=wb+1;pub=pubread+1;capture=pub+1
                if p in read_lives and load<=read_lives[p]:raise ValueError('live reducer tag reuse')
                loc(left,f'ram{bank}.read',scratch_read_v=1,scratch_read_slot=bank*16+2*p)
                loc(load,'reduce.input',load_v=1,load_tag=p)
                loc(right,f'ram{bank}.read',scratch_read_v=1,scratch_read_slot=bank*16+2*p+1)
                loc(read,'reduce.input',add_read=1,read_tag=p)
                loc(issue,'reduce.issue',add_issue=1)
                event('reduce.wb',wb,'writeback',tag=p)
                loc(pubread,'reduce.pubread',pub_read=1,pub_tag=p)
                loc(pub,'reduce.publish',pub_issue=1)
                read_lives[p]=pub
                if width>2:loc(capture,f'ram{bank}.write',capture=1,capture_slot=bank*16+p)
                else:
                    local[pub].update(final_pub=1,batch=batch,destination=destination)
                    loc(capture,f'ram{bank}.clear',clear_bank_v=1,clear_bank=bank)
                    expected_v[pub]=1;expected_batch[pub]=batch
                    expected[pub]=sum(float_bits(numeric_tree([nodes[k][l] for k in range(64)]))<<(32*l) for l in range(8))
                    final=pub
            c+=2*n+13
        timelines.append(dict(batch=batch,bank=bank,destination=destination,ring_start=start,local_start=start+85,
                              final_output=final,release=final+1,local_stages=stages))
    # Last ring publication is earlier than the local drain; hold its selector.
    for t in range((batches-1)*period+25,size):dest[t]=((batches-1)//16)%4
    if mutant=='earlypub':
        # Move the first final publication read onto native WB, not a relaxed
        # gate: the actual reducer must report unavailable/pending at that edge.
        pub=timelines[0]['final_output'];local[pub-2]['pub_read']=1;local[pub-2]['pub_tag']=0
    out.mkdir(parents=True,exist_ok=True);files={}
    data=[(f'ring{q}.hex',[pack(RING_FIELDS,v) for v in rings[q]],sum(w for _,w in RING_FIELDS)) for q in range(4)]
    data += [(f'input{q}.hex',inputs[q],256) for q in range(4)]
    data += [('local.hex',[pack(STREAM_FIELDS,v) for v in local],sum(w for _,w in STREAM_FIELDS)),
             ('landing.hex',landing,5),('destination.hex',dest,2),('expected.hex',expected,256),
             ('expected_v.hex',expected_v,1),('expected_batch.hex',expected_batch,7)]
    for name,values,width in data:
        path=out/name;path.write_text(''.join(f'{x:0{(width+3)//4}x}\n' for x in values))
        files[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    (out/'cycles.hex').write_text(f'{last:08x}\n{batches:08x}\n')
    files['cycles.hex']=hashlib.sha256((out/'cycles.hex').read_bytes()).hexdigest()
    receipt=dict(schema='hcoll-attention-pv-overlap-v1',scope='Qwen canonical128row SM nodes component; native SM and physical/price separate',
                 batches=batches,output_words=8*batches,period=period,first_output=timelines[0]['final_output'],
                 final_output=timelines[-1]['final_output'],last=last,mutant=mutant,
                 ring_tag_count=8,reducer_tag_count=16,landing_native_sram_banks=2,bank_shape='64x512',
                 effective_payload='16x256 per bank',ring_wave_stride=40,
                 local_level_edges=[29,21,17,15],local_stream_bits=sum(w for _,w in STREAM_FIELDS),
                 events=len(resources.events),timelines=timelines,files=files,
                 source_binding={str(p):hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    (out/'manifest.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',required=True,type=Path)
    ap.add_argument('--mutant',choices=('localfirst','earlypub'))
    ap.add_argument('--debug-four',action='store_true')
    a=ap.parse_args();r=compile_stream(a.out,a.mutant,4 if a.debug_four else 128)
    print(json.dumps({k:v for k,v in r.items() if k not in ('timelines','files','source_binding')},indent=2))
