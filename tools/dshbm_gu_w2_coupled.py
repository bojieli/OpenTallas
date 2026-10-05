#!/usr/bin/env python3
"""Opt-in exact GU -> weighted SwiGLU -> interleaved-service W2 coupled bench.

Reuse completed native GU outputs and the retained Opt4 service/paired-engine
archives. No producer, installer, owner RTL, checkpoint inference or new math.
The golden spec's existing routing/SwiGLU/FP4 arithmetic is called unchanged.
"""
import argparse
import json
import os
from pathlib import Path
import struct
import subprocess

os.environ.setdefault('HDC_V41_ARITH','chunk8')
import numpy as np
import hdc_golden as G
import hdc_golden_v41 as V
import dshbm_matched_sm_seq as M
from dshbm_sm_xmap_seq import parse_output
from dshbm_expert_workgroup_interleave import w2_exported_reader,w2_source_rows,w2_compact_stream

ROOT=Path(__file__).resolve().parents[1]


def export_router(checkpoint,out):
    """Lossless selected released gate/bias bytes only, no model construction."""
    checkpoint=Path(checkpoint);out=Path(out);out.mkdir(exist_ok=False)
    idx=json.loads((checkpoint/'model.safetensors.index.json').read_text())['weight_map']
    config=json.loads((checkpoint/'config.json').read_text())['text_config']
    (out/'config.json').write_text(json.dumps(config)+'\n')
    for layer in (3,20):
        d=out/f'L{layer}';d.mkdir()
        for field,shape,dtype,name in [('weight',[384,5120],'BF16','gate.bf16'),('bias',[384],'F32','bias.f32')]:
            key=f'layers.{layer}.ffn.gate.{field}'
            with (checkpoint/idx[key]).open('rb') as f:
                n=struct.unpack('<Q',f.read(8))[0];h=json.loads(f.read(n));m=h[key]
                if m['shape']!=shape or m['dtype']!=dtype:raise ValueError('released router geometry')
                a,b=m['data_offsets'];f.seek(8+n+a);raw=f.read(b-a)
                if len(raw)!=b-a:raise ValueError('short released router read')
            (d/name).write_bytes(raw)


def native_gu(root,ids):
    """Every original cold op row exactly once, map literal expert+matrix IDs."""
    rec=json.loads((root/'record.json').read_text())
    if rec['status']!='PASS_ACTUAL_SOURCE_ROUTED_GU_ALL_ROWS' or tuple(rec['router_ids'])!=ids:
        raise ValueError('require completed exact GU outputs for THESE source IDs')
    values={(e,m):np.empty(2304,np.uint32) for e in ids for m in ('w1','w3')}
    seen={k:set() for k in values}
    for c in rec['cases']:
        if not c['exact'] or c['mismatches'] or c['exit']:raise ValueError('failed GU case')
        got,_,_=parse_output(root/f"die{c['die']:02}_sm{c['sm']:02}"/'out.txt')
        key=(c['expert'],c['matrix']);a,b=c['rows']
        for row in range(a,b):
            if row in seen[key] or (0,row-a) not in got:raise ValueError('duplicate/missing native GU row')
            values[key][row]=got[0,row-a]&0xffffffff;seen[key].add(row)
    if any(rows!=set(range(2304)) for rows in seen.values()):raise ValueError('incomplete native GU vector')
    # linear_q's output BF16 rounding is part of the source expert contract.
    return {k:G.to_bf16(G.from_bits(v)) for k,v in values.items()}


def source_route(inputs,router,layer,ids):
    x=G.from_bits(np.fromfile(inputs/f'L{layer}/ffn_norm.u32',dtype='<u4'))
    gate=G.from_bits(np.fromfile(router/f'L{layer}/gate.bf16',dtype='<u2').astype(np.uint32)<<16).reshape(384,5120)
    bias=np.fromfile(router/f'L{layer}/bias.f32',dtype='<f4')
    if x.shape!=(5120,) or bias.shape!=(384,):raise ValueError('source router input length')
    scores=V.sqrt(V.softplus(V.mv(gate,x)))
    biased=V.add(scores,bias)
    capture=np.fromfile(inputs/f'L{layer}/router.u32',dtype='<u4')
    if not np.array_equal(G.bits(biased),capture):raise ValueError('source router recomputation differs from actual capture')
    chosen=tuple(sorted(map(int,V.topk_lowest_index(biased,6))))
    if chosen!=ids:raise ValueError('source-selected IDs differ')
    config=json.loads((router/'config.json').read_text())
    den=V.add(V.seqsum([scores[e] for e in ids]),np.float32(1e-20))
    weights={e:V.mul(V.div(scores[e],den),np.float32(config['routed_scaling_factor'])) for e in ids}
    return weights,np.float32(config['swiglu_limit'])


def coupled_inputs(gu,weights,limit,ids):
    return {e:G.to_bf16(V.mul(weights[e],V.mul(V.silu(np.minimum(gu[e,'w1'],limit).astype(np.float32)),
                    np.clip(gu[e,'w3'],-limit,limit).astype(np.float32)))) for e in ids}


def accepted_weights(service,views,ids):
    """Unpack ONLY actual preedge accepted W2 bytes; verify all released bytes."""
    result={}
    for m,v in enumerate(views):
        raw=(service/f'accepted_w2_sm{m}.bin').read_bytes()
        count=(len(v['rows'])*1224+127)//128
        if len(raw)!=6*count*128:raise ValueError('service count/tail mismatch')
        for k,e in enumerate(ids):
            r=raw[k*count*128:(k+1)*count*128]
            p,s=v['packed'][e],v['scale'][e]
            expected,_=w2_compact_stream(p,s)
            if r!=expected+bytes(count*128-len(expected)):raise ValueError('accepted W2 source byte mismatch')
            # Reverse the existing compaction in exactly the source issue order.
            decoded=np.empty_like(p);scales=np.empty_like(s);offset=0
            from rtl_gpu_sm_exact import issue_order
            for row,g,t in issue_order(len(p),2,8,True):
                lanes=8 if g==0 else 1
                w=int.from_bytes(r[offset:offset+16*lanes],'little')
                offset+=16*lanes;ss=r[offset:offset+lanes];offset+=lanes
                for lane in range(lanes):
                    block=(g*8+lane)*8+t
                    decoded[row,block*16:(block+1)*16]=np.frombuffer(((w>>(128*lane))&((1<<128)-1)).to_bytes(16,'little'),np.uint8)
                    scales[row,block]=ss[lane]
            if not np.array_equal(decoded,p) or not np.array_equal(scales,s):raise ValueError('W2 issue order decode mismatch')
            result[m,e]=(decoded,scales)
    return result


def fixture(out,m,rows,ids,weights,xs):
    """Use unchanged two-row pair ABI; a third literal row is ordinary FP4."""
    out.mkdir();lines=[];xwords=[];seq=[];gold={};labels={};opid=0
    def op(e,start,n,base):
        p,s=weights[m,e];p=p[start:start+n];s=s[start:start+n]
        g=M.gen_op('v41_fp4',n,2304,8,None,X=[xs[e]]+[np.zeros(2304,np.float32) for _ in range(7)],released_fp4=(p,s))
        for r,v in enumerate(g['gold'][0]):gold[opid,r]=int(G.bits(v));labels[opid,r]=(e,rows[start+r])
        return g
    for start in range(0,len(rows),2):
        n=min(2,len(rows)-start)
        for slot in range(0,6,2):
            e,f=ids[slot:slot+2]
            if n==2:
                ia=opid;a=op(e,start,n,0);opid+=1;ib=opid;b=op(f,start,n,16);opid+=1
                base=len(lines);lines+=a['lines']+b['lines'];xwords+=a['xw']+b['xw']
                seq.append([4,8,2,2,64,1,1,16,1,0,1,base+32,16,16,ia,ib])
            else:
                for e in (e,f):
                    ia=opid;a=op(e,start,n,0);opid+=1;lines+=a['lines'];xwords+=a['xw']
                    seq.append([1,8,2,2,16,1,1,16,1,0,0,0,0,0,ia,ia])
    for name,data,width in [('seq.hex',[x for s in seq for x in s],8),('lines.hex',lines,272),
                            ('x.hex',xwords,(8*M.XC+2048+3)//4)]:
        (out/name).write_text(''.join(f'{v:0{width}x}\n' for v in data))
    return seq,gold,labels


def run(a):
    V.set_arith('chunk8');a.out.mkdir(exist_ok=False,parents=True)
    records=[]
    for layer in (20,3):
        d=a.out/f'L{layer}';d.mkdir();inputs=a.inputs
        ids=tuple(map(int,np.fromfile(inputs/f'L{layer}/expert_ids.u32',dtype='<u4')))
        gu=native_gu(a.gu/f'L{layer}',ids)
        weights,limit=source_route(inputs,a.router,layer,ids);xs=coupled_inputs(gu,weights,limit,ids)
        # No cached weighted activation or inversion of rounded biased scores.
        service=d/'service';service.mkdir()
        for name in ('gu.hex','sm_expected.hex','w2.hex','cfg_lut.hex','cfg_lines.hex'):
            import shutil
            shutil.copy2(a.service/f'L{layer}'/name,service/name)
        cmd=[str(a.service_exe),f'+DIR={service.resolve()}','+notice_lead_ps=300000']+[f'+id{k}={e}' for k,e in enumerate(ids)]
        with (service/'runtime.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
        if 'ACCEPTED_W2_CAPTURE_PASS' not in (service/'runtime.log').read_text():raise ValueError('no actual accepted service result')
        reader=w2_exported_reader(a.w2/f'L{layer}',layer,ids)
        by_expert={e:w2_source_rows(reader,e,2,0) for e in ids}
        views=[dict(rows=by_expert[ids[0]][m]['rows'],packed={e:by_expert[e][m]['packed'] for e in ids},
                    scale={e:by_expert[e][m]['scale'] for e in ids}) for m in range(8)]
        decoded=accepted_weights(service,views,ids)
        results={};calls=[]
        for m,v in enumerate(views):
            if not v['rows']:continue
            case=d/f'sm{m}';seq,gold,labels=fixture(case,m,v['rows'],ids,decoded,xs)
            with (case/'runtime.log').open('w') as log:
                rc=subprocess.run([str(a.w2_exe),f'+DIR={case.resolve()}',f'+NOPS={len(seq)}'],stdout=log,stderr=subprocess.STDOUT).returncode
            got,meta,cycles=parse_output(case/'out.txt')
            if rc or set(got)!=set(gold):raise ValueError(f'W2 missing/extra rows sm{m}: rc={rc}')
            bad=[k for k in gold if got[k]&0xffffffff!=gold[k]]
            if bad:raise ValueError(f'W2 arithmetic mismatch sm{m}: {bad}')
            if len(meta)!=len(seq) or any(v['fault'] or v['results']!=s[0] or v['consumed']!=s[4] for v,s in zip([meta[k] for k in sorted(meta)],seq)):
                raise ValueError('W2 descriptor debt/count/fault mismatch')
            for k,owner in labels.items():
                if owner in results:raise ValueError('duplicate restored expert output')
                results[owner]=int(G.bits(G.to_bf16(G.from_bits(np.uint32(got[k]&0xffffffff)))))
            calls.append(dict(sm=m,rows=v['rows'],cycles=cycles,descriptors=len(seq),exact_outputs=len(gold)))
        expected={(e,r) for e in ids for v in views for r in v['rows']}
        if set(results)!=expected:raise ValueError('final weighted expert output ownership mismatch')
        (d/'weighted_expert_outputs.txt').write_text(''.join(f'{e} {r} {results[e,r]:08x}\n' for e,r in sorted(results)))
        records.append(dict(layer=layer,status='PASS_COUPLED_GU_SWIGLU_A8_SERVICE_PAIRED_W2',ids=ids,
                            outputs=len(results),calls=calls,die=2,stack=0,full_token=False,physical_closed=False))
        print(json.dumps(records[-1]),flush=True)
        (a.out/'result.json').write_text(json.dumps(records,indent=2)+'\n')
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='step',required=True)
    e=sub.add_parser('export-router');e.add_argument('--checkpoint',type=Path,required=True);e.add_argument('--out',type=Path,required=True)
    r=sub.add_parser('run')
    for name in ('out','inputs','router','gu','service','w2','service-exe','w2-exe'):r.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.step=='export-router':export_router(a.checkpoint,a.out);return 0
    return run(a)

if __name__=='__main__':raise SystemExit(main())
