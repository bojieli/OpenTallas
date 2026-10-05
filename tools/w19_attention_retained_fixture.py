#!/usr/bin/env python3
"""Bounded fixture extraction; no checkpoint-model load or runtime arithmetic.

128 uses retained L0/head0 query and127initialKV rows+retainednewwindowrow.
640 is a shape stress fixture, NOT actual L2 selection: retained L2/head0query,
the same initialwindow,512copies of a retained L2 compressed-row producer.
Forward RoPE coefficients/query construction are disclosed software fixture
generation, never production input providers or fulltoken qualification.
"""
import argparse
import json
import pickle
from pathlib import Path
import numpy as np
import hdc_golden_v41 as V
import w19_norm_opcode_proof as N
import rtl_v41_fullshape_layer_campaign as LC

ROOT=Path(__file__).resolve().parents[1]


def build(out):
    if out.exists() or out.with_suffix('.json').exists():raise ValueError('refuse overwrite fixture')
    dump=Path('/home/ubuntu/w19work/mtp/dump_mtp_L02.pkl')
    m0=Path('/home/ubuntu/w19work/mtp/mtp_L00.npz');m2=Path('/home/ubuntu/w19work/mtp/mtp_L02.npz')
    window=Path('/home/ubuntu/w17work/isa/scratch_s20260930/images/ctx1048576_L00_r0')
    cfg=ROOT/'compiler/models/deepseek-v4.1-flash/inference_config.json'
    paths=[dump,m0,m2,window/'kv.window.codes.bin',window/'kv.window.scale.bin',cfg]
    d=pickle.loads(dump.read_bytes())  # retained owner-generated local ISA dump
    config=json.loads(cfg.read_text());ck=LC.Checkpoint()
    code=np.fromfile(paths[3],np.uint8).reshape(127,512);exp=np.fromfile(paths[4],np.uint8).reshape(127,16)
    win=(V.E4M3[code].reshape(-1,32)*np.exp2(exp.reshape(-1).astype(np.int32)-127)[:,None]).astype(np.float32).reshape(127,512)
    with np.load(m0,allow_pickle=False) as z:win=np.concatenate([win,z['win0@0'][None,:]])
    N.bf16_memory(win)
    with np.load(m2,allow_pickle=False) as z:ckv=z['ckv2@0'].copy()
    arrays={'scale':np.asarray(config['head_dim']**-.5,np.float32)};checkpoint={}
    for n,layer,yarn in [(128,0,False),(640,2,True)]:
        entries=[v for k,v in d.items() if k.startswith(f'L{layer}.') and k.endswith('.p0') and v['tag'].startswith('wq_b ')]
        if len(entries)!=1 or entries[0]['rows']!=[0,512] or entries[0]['out'].shape!=(512,):raise ValueError('retained query binding')
        freqs=V.rope_freqs(config['rope_head_dim'],config['original_seq_len'] if yarn else 0,
                          config['compress_rope_theta'] if yarn else config['rope_theta'],
                          config['rope_factor'],config['beta_fast'],config['beta_slow'])
        cs=V.rope_cs(freqs,1048575);q=V.rope_tail(entries[0]['out'],cs)
        name=f'layers.{layer}.attn.attn_sink';raw,dt,shape=ck.raw(name)
        if dt!='F32' or shape!=[64]:raise ValueError('actual checkpoint sink dtype/shape')
        sink=np.frombuffer(raw,np.float32)[0].copy()
        meta,base,file=ck.meta(name);checkpoint[name]=dict(tensor_sha256=N.sha(bytes(raw)),dtype=dt,shape=shape,
                                                       shard_identity=str((ck.snap/file).resolve()),header_offsets=meta['data_offsets'])
        rows=win if n==128 else np.concatenate([win,np.broadcast_to(ckv,(512,512))])
        arrays.update({f'q{n}':q,f'rows{n}':rows,f'sink{n}':np.asarray(sink,np.float32),f'cos{n}':cs[0],f'sin{n}':cs[1]})
    out.parent.mkdir(parents=True,exist_ok=True);np.savez_compressed(out,**arrays)
    record=dict(schema='opentallas.w19.retained-attention-fixture.v1',
                fixture_sha256=N.sha(out.read_bytes()),source_files={str(p):N.sha(p.read_bytes()) for p in paths},
                checkpoint_revision='dba1be0a40aa45a94ad051997016db3960a90277',
                checkpoint_index_sha256=N.sha((ck.snap/'model.safetensors.index.json').read_bytes()),checkpoint_tensors=checkpoint,
                query='retained ISA rank0/head0 wq_b output; forwardRoPE software fixture generation at position1048575',
                initialKV='retained W17 raw127window rows+retainedcheckpointnewrow, BF16 verified',
                rows640='shape stress ONLY: L2query+L0initialwindow+512repeatedL2CKVrows; not actual selected512rows/modeltrajectory',
                coefficient_ports='COS/SIN fixture inputs from golden software; production service unresolved',
                production_runtime=False,full_token_qualified=False)
    out.with_suffix('.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({'fixture_bytes':out.stat().st_size,'source_files':len(paths),'runtime':False}))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();build(a.out)
